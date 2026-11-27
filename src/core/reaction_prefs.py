"""Deklaracje pasu, „tylko gdy dotyczy mnie” i wyciszenia okien reakcji (RULES.md 54.12). Czyste.

Preferencje są PRYWATNE (``PlayerPrivateState.reaction_prefs``): silnik używa ich tylko do auto-pasu
(``reaction_window.auto_passers``) i do pomijania wyciszonych ofert (``triggers.fire``). Okno trwa
tyle samo (54.11), więc z zewnątrz nic nie widać - chyba że host włączył „Quick windows”.

Kategorie okien: ``all`` (każde), ``strategy`` (ogłoszona akcja strategiczna), ``agenda`` (ujawniona
agenda), ``combat`` (wygrana walka, Sustain Damage), ``sabotage`` (karta akcji innego gracza).
Agendę można też odpuścić połowicznie - ``agenda_when`` („No whens”) i ``agenda_after``
(„No afters”): gracz pasuje tylko na karty z tym momentem, karty drugiego momentu dalej go pytają.
Czas trwania deklaracji: ``combat`` (bieżąca walka), ``turn``, ``round``, ``agenda`` (bieżąca
agenda), ``always``.

Komponenty frakcji/agenci z oknem użycia (Naalu, Saar, agenci walki...) wycisza się osobno
(``muted_components``, klucz = ``faction_components.effect_key``) z tym samym zasięgiem.
AFK: okno zakończone upływem czasu bez żadnej reakcji uprawnionego to „strajk”
(``record_timeout``); po ``AFK_STRIKES`` silnik pasuje za gracza, dopóki nie zrobi czegokolwiek
w UI (``mark_active``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.core.game_events import GameEvent
from src.core.game_state import (
    ControlType,
    GameState,
    PassDeclaration,
    PrePassNotice,
    ReactionPrefs,
    SituationChange,
)

# History label of the "I'm back" bookkeeping snapshot (HTTP middleware). Transparent to
# player undo and undo move: it only records presence, never a game step.
PRESENCE_LABEL = "reaction-settings:presence"

ALL = "all"
STRATEGY = "strategy"
AGENDA = "agenda"
COMBAT = "combat"
SABOTAGE = "sabotage"
AGENDA_WHEN = "agenda_when"
AGENDA_AFTER = "agenda_after"
CATEGORIES: tuple[str, ...] = (ALL, STRATEGY, AGENDA, COMBAT, SABOTAGE, AGENDA_WHEN, AGENDA_AFTER)

# Deklaracje połowiczne: kategoria okna -> {kategoria deklaracji: moment pomijanych kart}.
_MOMENT_DECLARATIONS: dict[str, dict[str, str]] = {
    AGENDA: {AGENDA_WHEN: "when", AGENDA_AFTER: "after"},
}

UNTIL_TURN = "turn"
UNTIL_ROUND = "round"
UNTIL_AGENDA = "agenda"
UNTIL_COMBAT = "combat"
UNTIL_ALWAYS = "always"
DURATIONS: tuple[str, ...] = (UNTIL_COMBAT, UNTIL_TURN, UNTIL_ROUND, UNTIL_AGENDA, UNTIL_ALWAYS)
COMPONENT_DURATIONS: tuple[str, ...] = (UNTIL_COMBAT, UNTIL_TURN, UNTIL_ROUND, UNTIL_ALWAYS)

# ⚠️ ZAŁOŻENIE (54.12 e): tyle kolejnych okien bez żadnej reakcji = gracz jest AFK.
AFK_STRIKES = 2

# "Unless something changes" (RULES.md 54.13): how many notable moves the state remembers and how
# many cancelled pre-pass notices a player keeps.
_SITUATION_KEPT = 24
_NOTICES_KEPT = 4

# Auto-assign combat hits (RULES.md 54.14).
AUTO_HITS_OFF = "off"
AUTO_HITS_SUSTAIN = "sustain"
AUTO_HITS_CHEAP = "cheap"
AUTO_HITS_POLICIES: tuple[str, ...] = (AUTO_HITS_OFF, AUTO_HITS_SUSTAIN, AUTO_HITS_CHEAP)

# Zdarzenie kluczowego okna pauzy (``reaction_pause.PAUSE_POINTS``) -> kategoria deklaracji.
_EVENT_CATEGORY: dict[str, str] = {
    GameEvent.STRATEGIC_ACTION.value: STRATEGY,
    GameEvent.AGENDA_REVEALED.value: AGENDA,
    GameEvent.COMBAT_WON.value: COMBAT,
    GameEvent.UNIT_SUSTAIN_DAMAGE.value: COMBAT,
}


def category_of_event(event: str) -> str | None:
    """Kategoria deklaracji dla zdarzenia pauzy (``None`` = tylko ``all``)."""
    return _EVENT_CATEGORY.get(event)


def stamp(state: GameState, until: str) -> str:
    """Znacznik bieżącej chwili dla danego czasu trwania (zmiana znacznika = deklaracja wygasła).

    ⚠️ ZAŁOŻENIE (54.12 a): tura = (runda, faza, aktywny gracz).
    """
    if until == UNTIL_TURN:
        return f"{state.round_number}|{state.phase.value}|{state.active_player_id or ''}"
    if until == UNTIL_ROUND:
        return str(state.round_number)
    if until == UNTIL_COMBAT:
        combat = state.active_combat
        if combat is None:
            return ""
        return (
            f"{state.round_number}|{combat.kind}|{combat.position}|{combat.planet or ''}"
            f"|{combat.attacker}|{combat.defender}"
        )
    if until == UNTIL_AGENDA:
        agenda = state.agenda
        number = agenda.agenda_number if agenda is not None else 0
        return f"{state.round_number}|{number}"
    return ""


def note_change(state: GameState, actor: str, reason: str) -> None:
    """A notable public move by ``actor`` (RULES.md 54.13) - MUTATES ``state``.

    Called at the central points: an action card or promissory note played, an agent / faction
    component used, a retreat announced, extra hits produced in combat. Every "unless something
    changes" pre-pass of ANOTHER player declared before this move lapses (:func:`is_live`).
    """
    state.situation_seq += 1
    state.situation_log = [
        *state.situation_log, SituationChange(seq=state.situation_seq, actor=actor, reason=reason)
    ][-_SITUATION_KEPT:]


def change_since(state: GameState, declaration: PassDeclaration) -> SituationChange | None:
    """The first move by someone other than the declaring player after the declaration."""
    if not declaration.unless_changes:
        return None
    for change in state.situation_log:
        if change.seq > declaration.since and change.actor != declaration.owner:
            return change
    if state.situation_log and state.situation_log[0].seq > declaration.since + 1:
        # Older than the remembered log: something happened that we no longer list.
        return SituationChange(seq=declaration.since + 1, actor="", reason="the situation changed")
    return None


def is_live(state: GameState, declaration: PassDeclaration) -> bool:
    """Czy deklaracja nadal obowiązuje (54.12; „unless something changes” - 54.13)."""
    if change_since(state, declaration) is not None:
        return False
    if declaration.until == UNTIL_ALWAYS:
        return True
    if declaration.until == UNTIL_COMBAT and state.active_combat is None:
        return False  # deklaracja „ta walka” nie przeżywa walki (pusty znacznik = brak walki)
    return stamp(state, declaration.until) == declaration.stamp


def _declared(state: GameState, player_id: str, key: str) -> bool:
    player = state.players.get(player_id)
    if player is None:
        return False
    declaration = player.private.reaction_prefs.passes.get(key)
    return declaration is not None and is_live(state, declaration)


def skipped_moments(state: GameState, player_id: str, category: str | None) -> frozenset[str]:
    """Momenty kart (``when``/``after``), na które gracz z góry spasował w oknie tej kategorii.

    „No whens” / „No afters” przy agendzie: karta z pominiętym momentem nie liczy się jako
    „ma kartę” (``reaction_window.has_playable_reaction``).
    """
    halves = _MOMENT_DECLARATIONS.get(category or "", {})
    return frozenset(m for key, m in halves.items() if _declared(state, player_id, key))


def declares_pass(state: GameState, player_id: str, category: str | None) -> bool:
    """Czy gracz zadeklarował pas obejmujący CAŁE okno tej kategorii (``all``, sama kategoria
    albo wszystkie jej połowy - „No whens” i „No afters” razem)."""
    if _declared(state, player_id, ALL) or (category and _declared(state, player_id, category)):
        return True
    halves = _MOMENT_DECLARATIONS.get(category or "", {})
    return bool(halves) and all(_declared(state, player_id, key) for key in halves)


def prune(state: GameState) -> None:
    """Usuwa wygasłe deklaracje wszystkich graczy (MUTUJE; wołane po każdym kroku).

    A pre-pass cancelled because something changed (54.13) leaves a notice for its owner, so the
    UI can say why the game is asking again.
    """
    for player in state.players.values():
        prefs = player.private.reaction_prefs
        for category, declaration in prefs.passes.items():
            change = change_since(state, declaration)
            if change is not None:
                notice = PrePassNotice(
                    category=category, actor=change.actor, reason=change.reason
                )
                prefs.notices = [*prefs.notices, notice][-_NOTICES_KEPT:]
        if any(not is_live(state, d) for d in prefs.passes.values()):
            prefs.passes = {k: d for k, d in prefs.passes.items() if is_live(state, d)}
        if any(not is_live(state, d) for d in prefs.muted_components.values()):
            prefs.muted_components = {
                k: d for k, d in prefs.muted_components.items() if is_live(state, d)
            }


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _strings(item)


def _present(state: GameState, player_id: str, token: str) -> bool:
    """Czy ``token`` (pozycja systemu albo planeta) to miejsce z jednostkami/planetą gracza."""
    system = state.systems.get(token)
    if system is not None:
        if system.space_units.get(player_id):
            return True
        if any(units.get(player_id) for units in system.planet_units.values()):
            return True
        return player_id in system.planet_owners.values()
    for system in state.systems.values():
        if system.planet_owners.get(token) == player_id:
            return True
        if system.planet_units.get(token, {}).get(player_id):
            return True
    return False


def involved_players(
    state: GameState,
    candidates: Iterable[str],
    *,
    subject: str | None,
    ctx: Mapping[str, Any] | None,
    category: str | None,
) -> list[str]:
    """Kogo z ``candidates`` okno DOTYCZY wg informacji jawnej (RULES.md 54.12).

    Agenda dotyczy wszystkich. Poza tym: gracz jest stroną zdarzenia (``subject``), jest wymieniony
    w kontekście/parametrach albo ma jednostki/planety w systemie lub na planecie z kontekstu.
    """
    ids = list(candidates)
    if category == AGENDA:
        return ids
    tokens = set(_strings(ctx or {}))
    return [
        pid for pid in ids
        if pid == subject or pid in tokens or any(_present(state, pid, t) for t in tokens)
    ]


def skips_uninvolved(state: GameState, player_id: str, involved: Iterable[str]) -> bool:
    """„Ask me only when it concerns me”: czy pasować, bo okno gracza nie dotyczy."""
    player = state.players.get(player_id)
    return (
        player is not None
        and player.private.reaction_prefs.only_involved
        and player_id not in set(involved)
    )


def is_card_muted(prefs: ReactionPrefs, card_name: str) -> bool:
    """Czy karta reakcji o tej nazwie jest wyciszona (wszystkie kopie)."""
    return card_name in prefs.muted_cards


def is_offer_muted(state: GameState, player_id: str, covers: str | None) -> bool:
    """Czy oferta „you may” komponentu ``covers`` jest wyciszona przez gracza."""
    player = state.players.get(player_id)
    return bool(covers) and player is not None and (
        covers in player.private.reaction_prefs.muted_offers
    )


def is_component_muted(state: GameState, player_id: str, component_key: str) -> bool:
    """Czy komponent frakcji/agent (``effect_key``) jest teraz wyciszony przez gracza."""
    player = state.players.get(player_id)
    if player is None:
        return False
    declaration = player.private.reaction_prefs.muted_components.get(component_key)
    return declaration is not None and is_live(state, declaration)


def is_afk(state: GameState, player_id: str) -> bool:
    """Czy gracz jest AFK (``AFK_STRIKES`` okien z rzędu bez reakcji) - silnik pasuje za niego."""
    player = state.players.get(player_id)
    return player is not None and player.private.reaction_prefs.afk_strikes >= AFK_STRIKES


def window_opened(state: GameState, asked: Iterable[str]) -> None:
    """Otwarto okno reakcji: pytani gracze zaczynają „nieobecni” w tym oknie (MUTUJE)."""
    for pid in asked:
        player = state.players.get(pid)
        if player is not None:
            player.private.reaction_prefs.responded = False


def record_timeout(state: GameState, silent: Iterable[str]) -> None:
    """Okno zakończone upływem czasu: każdy z ``silent``, który nic nie zrobił w UI, dostaje
    strajk AFK (MUTUJE).

    ``silent`` = uprawnieni, którzy nie spasowali (ręcznie ani auto-pasem) i nie prosili o czas.
    Gracze pasowani przez silnik nie są „cisi” - ich nikt nie pytał.
    """
    for pid in silent:
        player = state.players.get(pid)
        if player is None or player.control_type is ControlType.BOT:
            continue
        prefs = player.private.reaction_prefs
        if not prefs.responded:
            prefs.afk_strikes += 1


def mark_active(state: GameState, player_id: str) -> bool:
    """Gracz zrobił coś w UI („I'm back”): zeruje strajki AFK i odnotowuje obecność w trwającym
    oknie (MUTUJE). Zwraca, czy coś zmieniono (wołający zapisuje stan tylko wtedy)."""
    player = state.players.get(player_id)
    if player is None or player.control_type is ControlType.BOT:
        return False
    prefs = player.private.reaction_prefs
    if prefs.afk_strikes == 0 and prefs.responded:
        return False
    prefs.afk_strikes = 0
    prefs.responded = True
    return True


def carry_presence(target: GameState, source: GameState) -> bool:
    """Copies every player's presence (AFK strikes, ``responded``) from ``source`` (MUTATES).

    Presence is a real-time fact like the chess clock: rewinding history (player undo, undo
    move) must not erase an "I'm back" recorded after the undone step. Returns whether anything
    changed.
    """
    changed = False
    for pid, player in target.players.items():
        other = source.players.get(pid)
        if other is None:
            continue
        prefs, now = player.private.reaction_prefs, other.private.reaction_prefs
        if (prefs.afk_strikes, prefs.responded) != (now.afk_strikes, now.responded):
            prefs.afk_strikes, prefs.responded = now.afk_strikes, now.responded
            changed = True
    return changed


def with_presence(state: GameState, player_id: str) -> GameState:
    """``state`` po odnotowaniu obecności gracza (nowy stan) albo ten sam, gdy nic się nie zmienia.

    Wspólne dla commitu HTTP i symulacji silnika (``engine.actions.apply_and_settle``), żeby oba
    dawały ten sam stan.
    """
    player = state.players.get(player_id)
    if player is None or player.control_type is ControlType.BOT:
        return state
    prefs = player.private.reaction_prefs
    if prefs.afk_strikes == 0 and prefs.responded:
        return state
    new_state = state.clone()
    mark_active(new_state, player_id)
    return new_state


def update(
    state: GameState,
    player_id: str,
    *,
    declare: Mapping[str, str | None] | None = None,
    only_involved: bool | None = None,
    mute_cards: Mapping[str, bool] | None = None,
    mute_offers: Mapping[str, bool] | None = None,
    mute_components: Mapping[str, str | None] | None = None,
    unless_changes: bool = False,
    auto_hits: str | None = None,
    clear_notices: bool = False,
) -> GameState:
    """Zmienia preferencje gracza (nowy stan; samo pasowanie w trwających oknach robi wołający).

    ``declare``: kategoria -> czas trwania (``None`` = odwołanie). ``mute_cards``/``mute_offers``:
    klucz -> wł./wył. ``mute_components``: ``effect_key`` -> zasięg (``None`` = odwołanie).
    ``unless_changes``: the new declarations lapse when another player makes a notable move
    (54.13). ``auto_hits``: combat hit assignment policy (54.14). ``clear_notices``: the player
    read the "pre-pass cancelled" notices.

    Raises:
        ValueError: Nieznany gracz, kategoria albo czas trwania.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    new_state = state.clone()
    player = new_state.players[player_id]
    prefs = player.private.reaction_prefs
    for category, until in (declare or {}).items():
        if category not in CATEGORIES:
            raise ValueError(f"Unknown reaction category: {category}")
        if until is not None and until not in DURATIONS:
            raise ValueError(f"Unknown duration: {until}")
        if category == ALL and until in (UNTIL_ALWAYS, None):
            # „Skip all reactions” (54.11) zostaje jednym ustawieniem: all/always = to pole.
            player.private.auto_pass_reactions = until == UNTIL_ALWAYS
        passes = {k: d for k, d in prefs.passes.items() if k != category}
        if until is not None and not (category == ALL and until == UNTIL_ALWAYS):
            passes[category] = PassDeclaration(
                until=until,
                stamp=stamp(new_state, until),
                unless_changes=bool(unless_changes) and until != UNTIL_ALWAYS,
                since=new_state.situation_seq,
                owner=player_id,
            )
        prefs.passes = passes
    if only_involved is not None:
        prefs.only_involved = bool(only_involved)
    for key, until in (mute_components or {}).items():
        if until is not None and until not in COMPONENT_DURATIONS:
            raise ValueError(f"Unknown mute scope: {until}")
        components = {k: d for k, d in prefs.muted_components.items() if k != key}
        if until is not None:
            components[key] = PassDeclaration(until=until, stamp=stamp(new_state, until))
        prefs.muted_components = components
    if mute_components:
        prefs.afk_strikes = 0  # świadoma zmiana ustawień = obecność
    if auto_hits is not None:
        if auto_hits not in AUTO_HITS_POLICIES:
            raise ValueError(f"Unknown hit assignment policy: {auto_hits}")
        prefs.auto_hits = auto_hits
    if clear_notices:
        prefs.notices = []
    prefs.muted_cards = _toggle(prefs.muted_cards, mute_cards)
    prefs.muted_offers = _toggle(prefs.muted_offers, mute_offers)
    return new_state


def _toggle(current: list[str], changes: Mapping[str, bool] | None) -> list[str]:
    result = list(current)
    for key, on in (changes or {}).items():
        if on and key not in result:
            result.append(key)
        elif not on and key in result:
            result.remove(key)
    return result
