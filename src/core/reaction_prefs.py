"""Deklaracje pasu, „tylko gdy dotyczy mnie” i wyciszenia okien reakcji (RULES.md 54.12). Czyste.

Preferencje są PRYWATNE (``PlayerPrivateState.reaction_prefs``): silnik używa ich tylko do auto-pasu
(``reaction_window.auto_passers``) i do pomijania wyciszonych ofert (``triggers.fire``). Okno trwa
tyle samo (54.11), więc z zewnątrz nic nie widać - chyba że host włączył „Quick windows”.

Kategorie okien: ``all`` (każde), ``strategy`` (ogłoszona akcja strategiczna), ``agenda`` (ujawniona
agenda), ``combat`` (wygrana walka, Sustain Damage), ``sabotage`` (karta akcji innego gracza).
Czas trwania deklaracji: ``turn``, ``round``, ``agenda`` (bieżąca agenda), ``always``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.core.game_events import GameEvent
from src.core.game_state import GameState, PassDeclaration, ReactionPrefs

ALL = "all"
STRATEGY = "strategy"
AGENDA = "agenda"
COMBAT = "combat"
SABOTAGE = "sabotage"
CATEGORIES: tuple[str, ...] = (ALL, STRATEGY, AGENDA, COMBAT, SABOTAGE)

UNTIL_TURN = "turn"
UNTIL_ROUND = "round"
UNTIL_AGENDA = "agenda"
UNTIL_ALWAYS = "always"
DURATIONS: tuple[str, ...] = (UNTIL_TURN, UNTIL_ROUND, UNTIL_AGENDA, UNTIL_ALWAYS)

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
    if until == UNTIL_AGENDA:
        agenda = state.agenda
        number = agenda.agenda_number if agenda is not None else 0
        return f"{state.round_number}|{number}"
    return ""


def is_live(state: GameState, declaration: PassDeclaration) -> bool:
    """Czy deklaracja nadal obowiązuje."""
    if declaration.until == UNTIL_ALWAYS:
        return True
    return stamp(state, declaration.until) == declaration.stamp


def declares_pass(state: GameState, player_id: str, category: str | None) -> bool:
    """Czy gracz zadeklarował pas obejmujący okno tej kategorii (``all`` lub sama kategoria)."""
    player = state.players.get(player_id)
    if player is None:
        return False
    passes = player.private.reaction_prefs.passes
    for key in (ALL, category):
        declaration = passes.get(key) if key else None
        if declaration is not None and is_live(state, declaration):
            return True
    return False


def prune(state: GameState) -> None:
    """Usuwa wygasłe deklaracje wszystkich graczy (MUTUJE; wołane po każdym kroku)."""
    for player in state.players.values():
        prefs = player.private.reaction_prefs
        if any(not is_live(state, d) for d in prefs.passes.values()):
            prefs.passes = {k: d for k, d in prefs.passes.items() if is_live(state, d)}


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


def update(
    state: GameState,
    player_id: str,
    *,
    declare: Mapping[str, str | None] | None = None,
    only_involved: bool | None = None,
    mute_cards: Mapping[str, bool] | None = None,
    mute_offers: Mapping[str, bool] | None = None,
) -> GameState:
    """Zmienia preferencje gracza (nowy stan; samo pasowanie w trwających oknach robi wołający).

    ``declare``: kategoria -> czas trwania (``None`` = odwołanie). ``mute_*``: klucz -> wł./wył.

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
            passes[category] = PassDeclaration(until=until, stamp=stamp(new_state, until))
        prefs.passes = passes
    if only_involved is not None:
        prefs.only_involved = bool(only_involved)
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
