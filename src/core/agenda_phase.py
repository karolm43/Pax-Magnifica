"""Faza agendy - głosowanie Rady Galaktycznej wg R_agenda_phase (RULES.md 51).

Czyste funkcje ``state -> state``. Zakres: SAMA FAZA i jej zasady. Efekty konkretnych agend to
hooki źródła ``agenda`` (``core/hooks/agendas_*.py``, RULES.md 51.6): rozstrzygana karta
(``agenda.resolving``) obowiązuje każdego gracza w zdarzeniu ``AGENDA_OUTCOME_RESOLVED``/DURING,
prawa w grze - przez punkty zaczepienia reguł bazowych. Riders rozstrzygają się PO efekcie (AFTER).

Przebieg fazy (R_agenda_phase):

1. First Agenda - ``reveal_agenda`` (mówca) → ``cast_vote`` / ``abstain`` (gracze po kolei,
   zaczynając od LEWEJ mówcy zegarowo; mówca ostatni) → wynik: największa liczba głosów,
   a przy remisie albo braku głosów wybiera MÓWCA (``decide_tie``, to nie jest głos).
2. Second Agenda - to samo (``continue_agenda`` po wyniku pierwszej).
3. Ready Planets - ``continue_agenda`` po drugiej agendzie odświeża planety wszystkich;
   potem mówca ogłasza ``Next phase`` (``finish_agenda`` → nowa runda).

Głosowanie: gracz wyczerpuje dowolną liczbę GOTOWYCH planet i wybiera JEDEN wynik;
liczba głosów = suma wpływów wyczerpanych planet (pełna wartość planety). Trade goods nie
dają głosów. Zero głosów = wstrzymanie się.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    card_draw,
    economy,
    exhaust,
    objective_events,
    objectives,
    relic_planets,
    rules_hooks,
    strategy_phase,
    timing,
    triggers,
    turn_flow,
)
from src.core.components import AgendaDef, ComponentCategory
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    ActiveEffect,
    AgendaPhaseState,
    AgendaStep,
    AgendaVote,
    GameState,
    Phase,
)
from src.core.planet_stats import influence_of
from src.core.registry import StaticDataRegistry

# Liczba agend rozstrzyganych w jednej fazie agendy (R_agenda_phase, kroki 1-2).
AGENDAS_PER_PHASE = 2
# Maksymalna długość wyniku wpisywanego ręcznie (rodzaje wyników bez modelu - ``manual``).
_MANUAL_MAX = 80

# Rodzaje wyników wyliczane z ``target`` karty. Kolejność ma znaczenie (dłuższe prefiksy
# przed krótszymi). ``(prefiks, rodzaj, dokładne_dopasowanie)``.
_TARGET_KINDS: tuple[tuple[str, str, bool], ...] = (
    ("for/against", "for_against", False),
    ("elect player or against", "player_or_against", False),
    ("elect player who owns at least 2 technologies", "player_techs", False),
    ("elect player", "player", True),
    ("elect a player", "player", True),
    ("elect non-home planet other than mecatol rex", "planet_non_home_not_mecatol", True),
    ("elect non-home planet", "planet_non_home", True),
    ("elect planet trait", "planet_trait", True),
    ("elect planet", "planet", True),
    ("elect strategy card", "strategy_card", False),
    ("elect law", "law", False),
    ("elect scored secret objective", "secret_objective", False),
    ("elect public objective", "public_objective", False),
    ("elect technology group", "tech_group", False),
    ("elect command token pool", "command_pool", False),
)

# Pauza przed rozstrzygnięciem wyniku (krok ``COUNTED``) - miejsce na karty reakcji grane PO
# głosach, a PRZED wynikiem (RULES.md 53.5.a, 43.4). Pauza powstaje, gdy ktokolwiek ma w ręce
# jakąkolwiek kartę akcji (liczba kart jest jawna), więc nie zdradza posiadacza konkretnej karty.
# ``True`` = pauza zawsze (np. do testów jednolitego rytmu).
PAUSE_BEFORE_RESOLUTION_ALWAYS = False

# Wartości wyborów bez własnych danych w assetach (grupy technologii i pule żetonów to
# nazwy z reguł, nie liczby). Cechy planet: R_planets.
_TECH_GROUPS = ("propulsion", "biotic", "cybernetic", "warfare")
_COMMAND_POOLS = ("tactic", "fleet", "strategy")
_PLANET_TRAITS = ("cultural", "hazardous", "industrial")

# Covert Legislation: mówca dobiera ukrytą agendę, gracze głosują nad JEJ wynikami (C_agendas).
COVERT_LEGISLATION = "covert"
# Zwrot z tekstu kart „When this agenda is revealed, if there are no laws in play, discard this
# card and reveal another agenda" (Judicial Abolishment, Miscount Disclosed, New Constitution).
_NEEDS_LAWS_TEXT = "if there are no laws in play"
_REVEAL_ANOTHER_TEXT = "discard this card and reveal another"


# --- Klasyfikacja agendy ------------------------------------------------------------------



def note_reaction_played(state: GameState, window: Mapping[str, Any]) -> None:
    """Zagrano kartę w oknie ``window``: „after an agenda is revealed” zamyka okno „when revealed”
    (wszystkie „when” przed „after”, R_abilities; ruling Veto: przed oknem riderów). MUTUJE."""
    agenda = state.agenda
    if (
        agenda is not None
        and window.get("event") == GameEvent.AGENDA_REVEALED.value
        and window.get("moment") == Moment.AFTER.value
    ):
        agenda.after_reveal_played = agenda.agenda_id

def agenda_def(registry: StaticDataRegistry, agenda_id: str) -> AgendaDef | None:
    """Definicja karty agendy z Katalogu_Komponentów (``None`` dla nieznanego id)."""
    definition = registry.catalog.get(ComponentCategory.AGENDA, agenda_id)
    return definition if isinstance(definition, AgendaDef) else None


def effective_card(agenda: AgendaPhaseState) -> str | None:
    """Karta, której wyniki i efekt się rozstrzyga (ukryta przy Covert Legislation)."""
    return agenda.covert_card or agenda.agenda_id


def _card_text(definition: AgendaDef) -> str:
    texts = [definition.target or "", *(str(v) for v in (definition.texts or {}).values())]
    return " ".join(texts).lower()


def discarded_on_reveal(
    state: GameState, registry: StaticDataRegistry, definition: AgendaDef | None
) -> bool:
    """„When this agenda is revealed, if there are no <X>, discard this card and reveal another".

    Judicial Abolishment / Miscount Disclosed / New Constitution (brak praw w grze) i Classified
    Document Leaks (brak zdobytych tajnych celów) - warunek z tekstu karty: brak praw albo brak
    kandydatów do wyboru.
    """
    if definition is None:
        return False
    text = _card_text(definition)
    if _REVEAL_ANOTHER_TEXT not in text:
        return False
    if _NEEDS_LAWS_TEXT in text and not state.decks.agenda_laws:
        return True
    kind = classify_target(definition.target)
    return kind != "manual" and not candidate_outcomes(state, registry, kind)


def classify_target(target: str | None) -> str:
    """Rodzaj wyniku agendy z pola ``target`` (``for_against``, ``player``, ``planet``…).

    Dopiski w nawiasie (warunki i skutki) są pomijane. Rodzaje bez modelu zwracają
    ``manual`` - wynik wpisuje wtedy operator, a silnik tylko liczy głosy.
    """
    head = (target or "").split("(")[0].strip().lower()
    for prefix, kind, exact in _TARGET_KINDS:
        if (head == prefix) if exact else head.startswith(prefix):
            return kind
    return "manual"


def _home_planets(state: GameState, registry: StaticDataRegistry) -> set[str]:
    homes: set[str] = set()
    for player in state.players.values():
        faction = registry.factions.get(player.faction) if player.faction else None
        if faction is not None:
            homes.update(faction.home_planets)
    return homes


def _is_mecatol(registry: StaticDataRegistry, planet_id: str) -> bool:
    definition = registry.planets.get(planet_id)
    return definition is not None and definition.name.strip().lower() == "mecatol rex"


def candidate_outcomes(state: GameState, registry: StaticDataRegistry, kind: str) -> list[str]:
    """Dopuszczalne wyniki głosowania dla rodzaju ``kind`` (stan w chwili ujawnienia)."""
    seats = list(strategy_phase.speaker_order(state))
    if kind == "for_against":
        return ["for", "against"]
    if kind == "player":
        return seats
    if kind == "player_or_against":
        return [*seats, "against"]
    if kind == "player_techs":
        return [p for p in seats if len(state.players[p].technologies) >= 2]
    if kind in ("planet", "planet_non_home", "planet_non_home_not_mecatol"):
        owned = objectives.planet_owners(state)
        homes = _home_planets(state, registry) if "non_home" in kind else set()
        return sorted(
            planet
            for planet in owned
            if planet not in homes
            and not (kind.endswith("not_mecatol") and _is_mecatol(registry, planet))
        )
    if kind == "planet_trait":
        return list(_PLANET_TRAITS)
    if kind == "strategy_card":
        return [str(n) for n in strategy_phase.available_initiatives(registry)]
    if kind == "law":
        return sorted(state.decks.agenda_laws)
    if kind == "secret_objective":
        return sorted({s for p in state.players.values() for s in p.scored_secrets})
    if kind == "public_objective":
        return list(state.objectives.revealed)
    if kind == "tech_group":
        return list(_TECH_GROUPS)
    if kind == "command_pool":
        return list(_COMMAND_POOLS)
    return []  # manual


# --- Dostęp / walidacja -------------------------------------------------------------------


def _require_agenda(state: GameState, *steps: AgendaStep) -> AgendaPhaseState:
    """Waliduje: gra trwa, faza AGENDA, stan zainicjowany i bieżący krok ∈ ``steps``."""
    if state.winner_id is not None:
        raise ValueError("The game has ended.")
    if state.phase is not Phase.AGENDA:
        raise ValueError("This action is only available in the agenda phase.")
    if state.agenda is None:
        raise ValueError("The agenda phase has not been initialised.")
    if state.agenda.step not in steps:
        wanted = "/".join(s.value for s in steps)
        raise ValueError(
            f"Wrong agenda step (now: {state.agenda.step.value}, expected: {wanted})."
        )
    return state.agenda


def _require_votable(state: GameState, player_id: str) -> None:
    """Waliduje, że agendę da się rozstrzygnąć i to kolej ``player_id`` na głos."""
    assert state.agenda is not None
    if state.agenda.unresolvable:
        raise ValueError("This agenda has no valid outcome - the speaker must discard it.")
    if player_id != current_voter(state):
        raise ValueError(f"It is not {player_id}'s turn to vote (now: {current_voter(state)}).")
    require_no_agenda_decisions(state)


def require_no_agenda_decisions(state: GameState) -> None:
    """Głosowanie czeka, aż gracze rozstrzygną decyzje z kart agendy (np. Committee Formation)."""
    waiting = [o for o in state.pending_offers if o.event.startswith("agenda.")]
    if waiting:
        raise ValueError(
            f"Waiting for {waiting[0].player_id} to decide on {waiting[0].label} first."
        )


def single_vote(state: GameState, player_id: str) -> bool:
    """Representative Government: 1 głos bez wyczerpywania planet i bez dodatkowych głosów."""
    return rules_hooks.permits(rules_hooks.POINT_AGENDA_SINGLE_VOTE, state, player_id)


def _require_speaker(state: GameState, player_id: str) -> None:
    if player_id != state.speaker_id:
        raise ValueError(f"Only the speaker can do this (speaker: {state.speaker_id}).")


def vote_order(state: GameState) -> list[str]:
    """Kolejność głosowania: od gracza po LEWEJ mówcy zegarowo, mówca OSTATNI (R_agenda_phase)."""
    order = strategy_phase.speaker_order(state)  # mówca pierwszy, zegarowo
    return [*order[1:], *order[:1]] if order else []


def current_voter(state: GameState) -> str | None:
    """Gracz, który teraz głosuje (pierwszy z kolejki bez głosu/wstrzymania/blokady)."""
    agenda = state.agenda
    if agenda is None or agenda.step is not AgendaStep.VOTE:
        return None
    for pid in agenda.vote_order:
        if pid in agenda.votes or pid in agenda.abstained or pid in agenda.blocked:
            continue
        return pid
    return None


def _point_to_voter(state: GameState) -> None:
    """Aktywny gracz = kto teraz głosuje; poza głosowaniem = mówca (zasada 31.4)."""
    voter = current_voter(state)
    state.active_player_id = voter or state.speaker_id or state.active_player_id


# --- Głosy ---------------------------------------------------------------------------------


def extra_votes(
    state: GameState, registry: StaticDataRegistry, player_id: str, base_votes: int = 0
) -> int:
    """Dodatkowe głosy z efektów gry - hook MODIFY ``agenda.vote_modifier`` (RULES.md 43).

    ``base_votes`` = głosy z planet i kart, zanim doliczy się efekty (ctx hooka). Efekt
    „cast N additional votes" bez zwykłych głosów nie działa (F_hacan: Gila przy 0 głosach).
    """
    del registry
    agenda_id = state.agenda.agenda_id if state.agenda is not None else None
    return rules_hooks.modify(
        rules_hooks.POINT_AGENDA_VOTE_MODIFIER,
        state,
        player_id,
        0,
        {"agenda_id": agenda_id, "base_votes": base_votes},
    )


VOTE_REFUND_KEY = "refund_trade_goods_on_abstain"  # data efektu: TG zwracane przy wstrzymaniu


def _refund_vote_effects(state: GameState, player_id: str) -> None:
    """Wstrzymanie się: efekty „wydaj TG -> dodatkowe głosy" przepadają, TG wracają.

    Efekt zapisuje w ``data[VOTE_REFUND_KEY]`` wydane TG (F_hacan: gracz, który się wstrzymał,
    nie oddaje dodatkowych głosów - więc nie mógł też za nie zapłacić).
    """
    for effect in list(active_effects.effects_for(state, player_id)):
        spent = int(effect.data.get(VOTE_REFUND_KEY, 0) or 0)
        if spent <= 0:
            continue
        economy.refund_trade_goods(state, player_id, spent)
        active_effects.remove_effect(state, effect.id)


PREDICTIVE_INTELLIGENCE = "pi"  # alias z technologies/pok.json
PREDICTIVE_VOTES = 3  # „you may cast 3 additional votes" (tekst karty)


def predictive_ready(state: GameState, player_id: str) -> bool:
    """Predictive Intelligence w posiadaniu i niewyczerpane (obie zdolności wymagają gotowej)."""
    player = state.players.get(player_id)
    return (
        player is not None
        and PREDICTIVE_INTELLIGENCE in player.technologies
        and PREDICTIVE_INTELLIGENCE not in player.exhausted_technologies
    )


def voting_planets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Planety gracza dające głosy: ``{planet, influence, exhausted}`` (wpływ > 0).

    Wpływ liczony z danych po attachmentach (``planet_stats``). Stacje kosmiczne, The Triad
    i Oceany (ruling Dane) wchodzą tu, gdy silnik trzyma je jako kontrolowane planety.
    """
    player = state.players.get(player_id)
    if player is None:
        return []
    exhausted = set(player.exhausted_planets)
    result: list[dict[str, Any]] = []
    for planet, owner in objectives.planet_owners(state).items():
        if owner != player_id:
            continue
        value = influence_of(state, registry, planet)
        if value > 0:
            result.append(
                {"planet": planet, "influence": value, "exhausted": planet in exhausted}
            )
    for pseudo, value in relic_planets.values(state, registry, player_id).items():
        if value > 0:  # relikt działający jak planeta (The Triad) daje głosy
            result.append(
                {
                    "planet": pseudo,
                    "influence": value,
                    "exhausted": relic_planets.relic_of(pseudo) in player.exhausted_relics,
                }
            )
    return sorted(result, key=lambda r: (-int(r["influence"]), str(r["planet"])))


def totals(agenda: AgendaPhaseState) -> dict[str, int]:
    """Suma głosów per wynik (każdy dopuszczalny wynik ma wpis, także z zerem)."""
    result = {outcome: 0 for outcome in agenda.outcomes}
    for vote in agenda.votes.values():
        result[vote.outcome] = result.get(vote.outcome, 0) + vote.votes
    return result


def _normalise_outcome(agenda: AgendaPhaseState, outcome: str) -> str:
    """Zwraca wynik w postaci kanonicznej albo ``ValueError`` (ręczne wyniki są rozszerzalne)."""
    text = outcome.strip()
    if agenda.kind == "manual":
        if not text or len(text) > _MANUAL_MAX:
            raise ValueError(f"Describe the outcome in 1-{_MANUAL_MAX} characters.")
        for known in agenda.outcomes:
            if known.lower() == text.lower():
                return known
        return text
    if text not in agenda.outcomes:
        raise ValueError(f"{outcome!r} is not a possible outcome of this agenda.")
    return text


def _after_vote(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Po głosie/wstrzymaniu: kolejny głosujący albo zliczenie wyników."""
    assert state.agenda is not None
    if current_voter(state) is not None:
        _point_to_voter(state)
        return state
    return _close_count(state, registry)


def _count_reaction_held(state: GameState, registry: StaticDataRegistry) -> bool:
    """Filtr jawny (RULES.md 43.4 pkt 5): pauza, gdy KTOKOLWIEK ma jakąkolwiek kartę akcji.

    Liczba kart akcji w ręce jest informacją publiczną, więc brak pauzy przy pustych rękach nie
    zdradza niczego. Treść ręki NIGDY nie wpływa na decyzję (gdyby wpływała, pauza ujawniałaby
    posiadacza np. Deadly Plot) - dlatego ``registry`` nie jest tu używany.
    """
    del registry
    if PAUSE_BEFORE_RESOLUTION_ALWAYS:
        return True
    return any(player.private.action_cards for player in state.players.values())


def _close_count(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Głosowanie skończone: zliczenie -> wynik (``_conclude``) albo remis (``TIEBREAK``)."""
    assert state.agenda is not None
    agenda = state.agenda
    sums = totals(agenda)
    best = max(sums.values(), default=0)
    leaders = [o for o, n in sums.items() if n == best]
    if best > 0 and len(leaders) == 1:
        return _conclude(state, registry, leaders[0], by_speaker=False)
    # Remis albo brak głosów: wybiera mówca spośród remisujących (przy 0 głosów - wszystkich).
    agenda.tied = leaders if best > 0 else list(agenda.outcomes)
    agenda.pending_outcome = None
    agenda.step = AgendaStep.TIEBREAK
    _point_to_voter(state)
    return state


def _conclude(
    state: GameState, registry: StaticDataRegistry, outcome: str, *, by_speaker: bool
) -> GameState:
    """Wynik ustalony: pauza na reakcje (``COUNTED``), gdy ktoś może zareagować, inaczej od razu."""
    assert state.agenda is not None
    agenda = state.agenda
    if agenda.step is AgendaStep.COUNTED or _count_reaction_held(state, registry):
        agenda.tied = []
        agenda.pending_outcome = outcome
        agenda.pending_by_speaker = by_speaker
        agenda.step = AgendaStep.COUNTED
        state.active_player_id = state.speaker_id or state.active_player_id
        return state
    return _resolve(state, registry, outcome, by_speaker=by_speaker)


def cast_vote(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    outcome: str,
    planets: list[str],
    *,
    use_predictive: bool = False,
) -> GameState:
    """Gracz, którego kolej, wyczerpuje ``planets`` i oddaje głosy na ``outcome``.

    ``use_predictive`` - Predictive Intelligence: +3 głosy (decyzja gracza, "may"). Karta
    wyczerpuje się dopiero, gdy wybrany wynik NIE zostanie rozstrzygnięty (``_resolve``).

    Raises:
        ValueError: Zły krok/kolejność, wynik spoza agendy, planeta nie gracza / wyczerpana /
            zdublowana / bez wpływu, gracz zablokowany albo zero głosów (to wstrzymanie się).
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    agenda = _require_agenda(state, AgendaStep.VOTE)
    _require_votable(state, player_id)
    lone_vote = single_vote(state, player_id)
    if lone_vote and (planets or use_predictive):
        raise ValueError(
            "Representative Government: you cannot exhaust planets or cast additional votes - "
            "you cast exactly 1 vote."
        )
    if use_predictive and not predictive_ready(state, player_id):
        raise ValueError("Predictive Intelligence is not ready (not owned or exhausted).")
    if len(set(planets)) != len(planets):
        raise ValueError("The same planet was selected twice.")
    usable = {
        row["planet"]: int(row["influence"])
        for row in voting_planets(state, registry, player_id)
        if not row["exhausted"]
    }
    for planet in planets:
        if planet not in usable:
            raise ValueError(
                f"Planet {planet} cannot give votes (not yours, exhausted or 0 influence)."
            )
    votes = sum(usable[p] for p in planets)
    if use_predictive:
        votes += PREDICTIVE_VOTES
    if lone_vote:
        votes = 1
    else:
        votes += extra_votes(state, registry, player_id, base_votes=votes)
    if votes <= 0:
        raise ValueError("Casting zero votes is the same as abstaining - abstain instead.")
    chosen = _normalise_outcome(agenda, outcome)
    work = state.clone()
    assert work.agenda is not None
    vote_ctx = {
        "player": player_id,
        "outcome": chosen,
        "votes": votes,
        "agenda": agenda.agenda_id or "",
    }
    triggers.fire(work, GameEvent.AGENDA_VOTES_CAST, Moment.WHEN, subject=player_id, ctx=vote_ctx)
    if chosen not in work.agenda.outcomes:
        work.agenda.outcomes = [*work.agenda.outcomes, chosen]
    work.agenda.votes[player_id] = AgendaVote(
        outcome=chosen,
        votes=votes,
        planets=list(planets),
        techs=[PREDICTIVE_INTELLIGENCE] if use_predictive else [],
    )
    work.agenda.last_vote_by = player_id
    exhaust.exhaust_planets(work, player_id, planets)  # R_agenda_phase: wyczerpanie = głos
    work.players[player_id].passed = True
    triggers.fire(work, GameEvent.AGENDA_VOTES_CAST, Moment.AFTER, subject=player_id, ctx=vote_ctx)
    return _after_vote(work, registry)


def abstain(state: GameState, registry: StaticDataRegistry, player_id: str) -> GameState:
    """Gracz, którego kolej, wstrzymuje się od głosu (nic nie wyczerpuje)."""
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    _require_agenda(state, AgendaStep.VOTE)
    _require_votable(state, player_id)
    work = state.clone()
    assert work.agenda is not None
    work.agenda.abstained.append(player_id)
    _refund_vote_effects(work, player_id)
    work.agenda.last_vote_by = None  # okno „po głosach poprzednika" zamknięte
    work.players[player_id].passed = True
    return _after_vote(work, registry)


# --- Wynik ---------------------------------------------------------------------------------


def _resolve(
    state: GameState, registry: StaticDataRegistry, outcome: str, *, by_speaker: bool
) -> GameState:
    """Rozstrzyga wynik: zapis prawa / odrzucenie karty, EFEKT agendy (hooki), potem riders.

    R_agenda_card: jeśli rozstrzygnięto „For" albo wybory prawa, karta zostaje w grze;
    dyrektywa i „Against" trafiają na stos odrzuconych. Efekt karty to hooki źródła ``agenda``
    w zdarzeniu ``AGENDA_OUTCOME_RESOLVED``/DURING (RULES.md 51.6): karta ``agenda.resolving``
    obowiązuje każdego gracza aż do „dalej" mówcy (decyzje graczy z jej efektu). Riders - AFTER
    (C_action_cards: „effect of a successful rider will be resolved after the effect of the
    agenda").
    """
    assert state.agenda is not None
    agenda = state.agenda
    shown = agenda.agenda_id
    card = effective_card(agenda)
    assert card is not None and shown is not None
    resolve_ctx = {
        "agenda": card, "outcome": outcome, "kind": agenda.kind,
        "speaker": state.speaker_id or "",
    }
    triggers.fire(state, GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.WHEN, ctx=resolve_ctx)
    objective_events.on_agenda_resolving(state, agenda.kind, outcome)  # Drive the Debate
    definition = agenda_def(registry, card)
    is_law = definition is not None and (definition.type or "").strip().lower() == "law"
    stays = is_law and outcome != "against"
    previous = state.decks.agenda_laws.get(card)
    if stays:
        state.decks.agenda_laws[card] = outcome
        objective_events.on_laws_changed(state)  # Dictate Policy (3 prawa w grze)
    elif previous is not None:
        remove_law(state, card)  # Miscount Disclosed: prawo przegłosowane „Against"
    else:
        card_draw.discard_agenda(state, card)
    if shown != card:
        card_draw.discard_agenda(state, shown)  # Covert Legislation idzie na stos odrzuconych
    agenda.resolved_outcome = outcome
    agenda.decided_by_speaker = by_speaker
    agenda.pending_outcome = None
    agenda.pending_by_speaker = False
    agenda.last_vote_by = None
    # Predictive Intelligence: głos z +3, którego wynik nie przeszedł, wyczerpuje kartę.
    for voter_id, vote in agenda.votes.items():
        if PREDICTIVE_INTELLIGENCE in vote.techs and vote.outcome != outcome:
            exhaust.exhaust_technology(state, voter_id, PREDICTIVE_INTELLIGENCE)
    agenda.tied = []
    agenda.step = AgendaStep.RESOLVED
    agenda.history.append(
        {
            "number": agenda.agenda_number,
            "agenda": card,
            "covert": shown if shown != card else None,
            "kind": agenda.kind,
            "outcome": outcome,
            "bySpeaker": by_speaker,
            "stays": stays,
            "totals": totals(agenda),
            "votes": {
                pid: {"outcome": v.outcome, "votes": v.votes} for pid, v in agenda.votes.items()
            },
        }
    )
    state.active_player_id = state.speaker_id or state.active_player_id
    agenda.resolving = card
    effect_ctx = {**resolve_ctx, "previous": previous or ""}
    triggers.fire(state, GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.DURING, ctx=effect_ctx)
    triggers.fire(state, GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER, ctx=resolve_ctx)
    return state


def voters_for(state: GameState, outcome: str) -> list[str]:
    """Gracze, którzy głosowali na ``outcome`` w bieżącej agendzie (kolejność głosowania)."""
    agenda = state.agenda
    if agenda is None:
        return []
    return [
        pid for pid in agenda.vote_order
        if (vote := agenda.votes.get(pid)) is not None and vote.outcome == outcome
    ]


def decide_tie(
    state: GameState, registry: StaticDataRegistry, player_id: str, outcome: str
) -> GameState:
    """Mówca rozstrzyga remis / brak głosów (to NIE jest głos - R_agenda_phase)."""
    agenda = _require_agenda(state, AgendaStep.TIEBREAK)
    _require_speaker(state, player_id)
    chosen = _normalise_outcome(agenda, outcome)
    if agenda.tied and chosen not in agenda.tied:
        raise ValueError("The speaker must pick one of the tied outcomes.")
    work = state.clone()
    assert work.agenda is not None
    if chosen not in work.agenda.outcomes:
        work.agenda.outcomes = [*work.agenda.outcomes, chosen]
    return _conclude(work, registry, chosen, by_speaker=True)


def confirm_outcome(state: GameState, registry: StaticDataRegistry, player_id: str) -> GameState:
    """Mówca potwierdza wynik czekający w kroku ``COUNTED`` (po oknie na reakcje) i go rozstrzyga.

    Raises:
        ValueError: Zły krok albo ``player_id`` nie jest mówcą.
    """
    agenda = _require_agenda(state, AgendaStep.COUNTED)
    _require_speaker(state, player_id)
    if agenda.pending_outcome is None:
        raise ValueError("There is no outcome waiting to be resolved.")
    work = state.clone()
    assert work.agenda is not None and work.agenda.pending_outcome is not None
    return _resolve(
        work, registry, work.agenda.pending_outcome, by_speaker=work.agenda.pending_by_speaker
    )


# --- Przebieg fazy -------------------------------------------------------------------------


def _clear_round_of_voting(work: GameState) -> None:
    """Czyści dane BIEŻĄCEJ agendy; nowa agenda = nowy zestaw transakcji (R_agenda_phase)."""
    assert work.agenda is not None
    agenda = work.agenda
    agenda.agenda_id = None
    agenda.kind = ""
    agenda.outcomes = []
    agenda.unresolvable = False
    agenda.vote_order = []
    agenda.votes = {}
    agenda.abstained = []
    agenda.blocked = []
    agenda.tied = []
    agenda.resolved_outcome = None
    agenda.decided_by_speaker = False
    agenda.last_vote_by = None
    agenda.pending_outcome = None
    agenda.pending_by_speaker = False
    agenda.covert_card = None
    agenda.resolving = None
    for player in work.players.values():
        player.passed = False
        # Każda para graczy może zawrzeć jedną transakcję w trakcie każdej agendy.
        player.transacted_with = []


def reveal_agenda(state: GameState, registry: StaticDataRegistry, player_id: str) -> GameState:
    """Mówca ujawnia wierzchnią agendę; zaczyna się głosowanie od lewej mówcy.

    Raises:
        ValueError: Gdy to nie krok ujawniania, ``player_id`` to nie mówca albo talia jest pusta.
    """
    _require_agenda(state, AgendaStep.REVEAL)
    _require_speaker(state, player_id)
    return _open_top_agenda(state.clone(), registry, player_id)


def _open_top_agenda(work: GameState, registry: StaticDataRegistry, player_id: str) -> GameState:
    """Ujawnia wierzchnią agendę z talii na KLONIE ``work`` i otwiera głosowanie (mutuje ``work``).

    Wspólne dla ``reveal_agenda`` i Veto (ponowne ujawnienie po odrzuceniu agendy). Karta
    wymagająca praw (Judicial Abolishment, Miscount Disclosed, New Constitution) przy braku praw
    w grze idzie na stos odrzuconych i ujawnia się kolejna (tekst karty). Covert Legislation:
    mówca dobiera ukrytą agendę, a głosuje się nad JEJ wynikami (C_agendas).

    Raises:
        ValueError: Gdy talia agend jest pusta.
    """
    objective_events.on_laws_changed(work)  # 3 prawa już w grze na starcie agendy: dp
    assert work.agenda is not None
    while True:
        card = card_draw.draw_agenda(work, registry)
        if card is None:
            raise ValueError("The agenda deck is empty.")
        hidden: str | None = None
        if card == COVERT_LEGISLATION:
            hidden = card_draw.draw_agenda(work, registry)
            if hidden is None:
                raise ValueError("The agenda deck is empty.")
        if discarded_on_reveal(work, registry, agenda_def(registry, hidden or card)):
            # „...discard this card and reveal another agenda" (przy Covert - obie karty).
            for discarded in (card, hidden):
                if discarded is not None:
                    card_draw.discard_agenda(work, discarded)
                    work.agenda.history.append(
                        {"number": work.agenda.agenda_number, "agenda": discarded,
                         "discarded": True}
                    )
            continue
        return _open_card(work, registry, player_id, card, hidden=hidden)


def _open_card(
    work: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card: str,
    *,
    hidden: str | None = None,
) -> GameState:
    """Otwiera głosowanie nad ``card`` (ujawnioną z talii albo prawem z Miscount Disclosed)."""
    assert work.agenda is not None
    _clear_round_of_voting(work)
    agenda = work.agenda
    agenda.agenda_id = card
    agenda.covert_card = hidden
    definition = agenda_def(registry, hidden or card)
    agenda.kind = classify_target(definition.target if definition is not None else None)
    agenda.outcomes = candidate_outcomes(work, registry, agenda.kind)
    if card in work.decks.agenda_laws and agenda.kind == "secret_objective":
        # Miscount na Classified Document Leaks: wybrany cel jest już publiczny (C_agendas).
        agenda.outcomes = [o for o in agenda.outcomes if o != work.decks.agenda_laws[card]]
    agenda.unresolvable = agenda.kind != "manual" and not agenda.outcomes
    agenda.vote_order = vote_order(work)
    agenda.blocked = [p for p in agenda.phase_blocked if p in work.players]
    agenda.step = AgendaStep.VOTE
    reveal_ctx = {"agenda": hidden or card, "kind": agenda.kind}
    triggers.fire(work, GameEvent.AGENDA_REVEALED, Moment.WHEN, subject=player_id, ctx=reveal_ctx)
    triggers.fire(work, GameEvent.AGENDA_REVEALED, Moment.AFTER, subject=player_id, ctx=reveal_ctx)
    if not agenda.unresolvable and current_voter(work) is None and not work.pending_offers:
        return _after_vote(work, registry)
    _point_to_voter(work)
    return work


def discard_unresolvable(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> GameState:
    """Mówca odrzuca agendę bez możliwych wyników i ujawnia kolejną (numer agendy bez zmian)."""
    del registry
    agenda = _require_agenda(state, AgendaStep.VOTE)
    _require_speaker(state, player_id)
    if not agenda.unresolvable:
        raise ValueError("This agenda has valid outcomes - players must vote on it.")
    work = state.clone()
    assert work.agenda is not None and work.agenda.agenda_id is not None
    for card in (work.agenda.agenda_id, work.agenda.covert_card):
        if card is None:
            continue
        if card in work.decks.agenda_laws:
            # Miscount na Classified Document Leaks bez innych celów: prawo odrzucone (C_agendas).
            remove_law(work, card)
        else:  # Covert Legislation: odrzucana razem z ukrytą agendą
            card_draw.discard_agenda(work, card)
        work.agenda.history.append(
            {"number": work.agenda.agenda_number, "agenda": card, "discarded": True}
        )
    _clear_round_of_voting(work)
    work.agenda.step = AgendaStep.REVEAL
    work.active_player_id = work.speaker_id or work.active_player_id
    return work


def _ready_all_planets(work: GameState) -> None:
    """Krok 3 fazy: każdy gracz odświeża wszystkie swoje wyczerpane planety.

    Limit z hooka FORBID ``agenda.planets_ready_limit`` (Checks and Balances „Against": tylko 3
    planety): gracz z większą liczbą wyczerpanych planet wybiera je w decyzji zdarzenia
    ``COMPONENT_READIED``/WHEN (``component = planets``, ``limit``).
    """
    for pid in list(work.players):
        caps = rules_hooks.forbidden(rules_hooks.POINT_PLANETS_READY_LIMIT, work, pid)
        limit = min(int(c) for c in caps) if caps else None
        if limit is None or len(work.players[pid].exhausted_planets) <= limit:
            exhaust.ready_all_planets(work, pid)
            continue
        ctx = {"player": pid, "component": "planets", "phase": "agenda", "limit": limit}
        triggers.fire(work, GameEvent.COMPONENT_READIED, Moment.WHEN, subject=pid, ctx=ctx)


def continue_agenda(state: GameState, registry: StaticDataRegistry, player_id: str) -> GameState:
    """Po wyniku: ponowne głosowanie (Miscount Disclosed), druga agenda albo odświeżenie planet.

    Raises:
        ValueError: Zły krok, nie mówca albo gracze mają jeszcze decyzje z efektu agendy.
    """
    agenda = _require_agenda(state, AgendaStep.RESOLVED)
    _require_speaker(state, player_id)
    turn_flow.require_no_open_decisions(state)
    work = state.clone()
    assert work.agenda is not None
    revote = agenda.revote_law
    work.agenda.revote_law = None
    if revote is not None and revote in work.decks.agenda_laws:
        # Miscount Disclosed: głosowanie nad prawem „jak gdyby ujawnionym" (numer agendy bez zmian).
        return _open_card(work, registry, player_id, revote)
    if agenda.agenda_number < AGENDAS_PER_PHASE:
        work.agenda.agenda_number += 1
        _clear_round_of_voting(work)
        work.agenda.step = AgendaStep.REVEAL
    else:
        work.agenda.resolving = None  # efekt drugiej agendy skończony (karta zostaje na podglądzie)
        _ready_all_planets(work)
        work.agenda.step = AgendaStep.COMPLETE
        for player in work.players.values():
            player.passed = True
    work.active_player_id = work.speaker_id or work.active_player_id
    return work


def finish_agenda(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Mówca ogłasza koniec fazy agendy: nowa runda od fazy strategii."""
    del registry
    _require_agenda(state, AgendaStep.COMPLETE)
    turn_flow.require_no_open_decisions(state)
    work = state.clone()
    card_draw.clear_agenda_peek(work)  # podgląd Insider Information nie żyje do następnej rundy
    return turn_flow.next_round(work)


def skip_agenda(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Tryb testowy (God-Mode ``/phase/skip``): pomija głosowania, odświeża planety, nowa runda."""
    del registry
    work = state.clone()
    _ready_all_planets(work)
    card_draw.clear_agenda_peek(work)
    return turn_flow.next_round(work)


_PLAYER_KINDS = ("player", "player_techs", "player_or_against")


def repeal_law(state: GameState, law_id: str) -> None:
    """Zdejmuje prawo z gry i kładzie jego kartę na stosie odrzuconych agend (Repeal Law).

    Raises:
        ValueError: Gdy takiego prawa nie ma w grze.
    """
    remove_law(state, law_id)


def remove_law(state: GameState, law_id: str) -> None:
    """JEDYNE miejsce zdejmowania prawa z gry (RULES.md 51.6): stos odrzuconych + zdarzenie.

    ``LAW_DISCARDED``/WHEN pada, gdy prawo jeszcze leży w grze (hooki „gdy właściciel traci tę
    kartę" - Political Censure - wciąż działają); AFTER - po zdjęciu.

    Raises:
        ValueError: Gdy takiego prawa nie ma w grze.
    """
    if law_id not in state.decks.agenda_laws:
        raise ValueError(f"{law_id} is not a law in play.")
    ctx = {"law": law_id, "outcome": state.decks.agenda_laws[law_id]}
    triggers.fire(state, GameEvent.LAW_DISCARDED, Moment.WHEN, ctx=ctx)
    del state.decks.agenda_laws[law_id]
    card_draw.discard_agenda(state, law_id)
    triggers.fire(state, GameEvent.LAW_DISCARDED, Moment.AFTER, ctx=ctx)


def law_outcome(state: GameState, law_id: str) -> str | None:
    """Wynik prawa w grze (``for``, id gracza, planety...) albo ``None``, gdy go nie ma."""
    return state.decks.agenda_laws.get(law_id)


def block_voter_for_phase(state: GameState, player_id: str) -> None:
    """Gracz nie może głosować nad ŻADNĄ agendą do końca tej fazy (Public Execution)."""
    agenda = state.agenda
    if agenda is None or player_id not in state.players:
        return
    if player_id not in agenda.phase_blocked:
        agenda.phase_blocked = [*agenda.phase_blocked, player_id]


def schedule_revote(state: GameState, law_id: str) -> None:
    """Miscount Disclosed: po „dalej" mówcy głosuje się ponownie nad prawem ``law_id``."""
    if state.agenda is not None and law_id in state.decks.agenda_laws:
        state.agenda.revote_law = law_id


def elect_without_vote(
    state: GameState, registry: StaticDataRegistry, outcome: str
) -> GameState:
    """Committee Formation: wynik wybrany bez głosowania (riders zagrane wcześniej działają).

    Raises:
        ValueError: Poza głosowaniem albo ``outcome`` spoza wyników agendy.
    """
    agenda = _require_agenda(state, AgendaStep.VOTE)
    if outcome not in agenda.outcomes:
        raise ValueError(f"{outcome!r} is not a possible outcome of this agenda.")
    agenda.blocked = list(agenda.vote_order)  # nikt już nie głosuje nad tą agendą
    return _conclude(state, registry, outcome, by_speaker=False)


def effects_of(state: GameState, key: str) -> list[ActiveEffect]:
    """Efekty trwałe o kluczu ``key`` (np. odroczone „at the start of the next strategy phase")."""
    return [e for e in state.active_effects if e.key == key]


def law_owner(state: GameState, registry: StaticDataRegistry, agenda_id: str) -> str | None:
    """Gracz, który POSIADA prawo w grze (wygrał wybory „Elect Player"), albo ``None``.

    R_agenda_card: prawo leżące w strefie gracza należy do niego. Wynik wyborów gracza jest
    zapisany w ``decks.agenda_laws`` jako jego ``player_id`` - to jedyne źródło prawdy.
    """
    outcome = state.decks.agenda_laws.get(agenda_id)
    definition = agenda_def(registry, agenda_id)
    if outcome is None or definition is None or outcome not in state.players:
        return None
    return outcome if classify_target(definition.target) in _PLAYER_KINDS else None


def owned_laws(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    """Prawa leżące w strefie gracza (jawne, kolejność wejścia w życie)."""
    return [
        card for card in state.decks.agenda_laws if law_owner(state, registry, card) == player_id
    ]


def is_agenda_phase(state: GameState) -> bool:
    """Czy trwa zainicjowana faza agendy (steruje bramą ``Next phase`` i oknem UI)."""
    return state.phase is Phase.AGENDA and state.agenda is not None


# --- Efekty kart grywanych w trakcie agendy (RULES.md 53.5.a) ------------------------------
# Funkcje MUTUJĄ przekazany stan (KLON roboczy wołającego, jak efekty kart akcji) i zwracają go.
# Karty (``core/hooks/reactions_agenda.py``) zmieniają stan agendy WYŁĄCZNIE tędy.

_ELECTION_KINDS = ("player", "player_techs", "player_or_against")


def is_player_election(state: GameState) -> bool:
    """Czy bieżąca agenda wybiera GRACZA (Elect Player i pokrewne)."""
    return state.agenda is not None and state.agenda.kind in _ELECTION_KINDS


def elected_player(state: GameState) -> str | None:
    """Gracz, który zostanie wybrany wynikiem czekającym w kroku ``COUNTED`` (albo ``None``)."""
    agenda = state.agenda
    if (
        agenda is None
        or agenda.step is not AgendaStep.COUNTED
        or not is_player_election(state)
        or agenda.pending_outcome not in state.players
    ):
        return None
    return agenda.pending_outcome


def block_voter(state: GameState, registry: StaticDataRegistry, player_id: str) -> GameState:
    """Gracz NIE może głosować w tej agendzie (riders, Assassinate Representative).

    Raises:
        ValueError: Poza krokiem głosowania albo nieznany gracz.
    """
    agenda = _require_agenda(state, AgendaStep.VOTE)
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    if player_id not in agenda.blocked:
        agenda.blocked = [*agenda.blocked, player_id]
    if player_id in agenda.votes or player_id in agenda.abstained:
        return state  # już zagłosował - zakaz dotyczy kolejnych głosowań (nic do zmiany)
    return _after_vote(state, registry)


def vote_last(state: GameState, player_id: str) -> GameState:
    """Hack Election: ``player_id`` głosuje w tej agendzie jako OSTATNI (przesuwa go na koniec).

    Raises:
        ValueError: Poza krokiem głosowania, nieznany gracz albo gracz już zagłosował.
    """
    agenda = _require_agenda(state, AgendaStep.VOTE)
    if player_id not in agenda.vote_order:
        raise ValueError(f"{player_id} is not in the voting order.")
    if player_id in agenda.votes or player_id in agenda.abstained:
        raise ValueError("That player has already voted on this agenda.")
    agenda.vote_order = [*(p for p in agenda.vote_order if p != player_id), player_id]
    _point_to_voter(state)
    return state


def veto_agenda(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Veto: odrzuca ujawnioną agendę i ujawnia kolejną z wierzchu talii (gracze głosują nad nią).

    Predykcje i zakazy głosowania z odrzuconej agendy znikają razem z nią. Numer agendy
    (pierwsza/druga) się nie zmienia.

    Raises:
        ValueError: Poza krokiem głosowania albo talia agend jest pusta.
    """
    agenda = _require_agenda(state, AgendaStep.VOTE)
    if not state.decks.agenda_deck:
        raise ValueError("The agenda deck is empty.")
    vetoed = agenda.agenda_id
    assert vetoed is not None
    for card in (vetoed, agenda.covert_card):
        if card is None:
            continue
        if card in state.decks.agenda_laws:
            remove_law(state, card)  # Miscount: Veto na prawie „ujawnionym" - odrzucone (C_agendas)
        else:  # Covert Legislation: odrzucana razem z ukrytą agendą (C_agendas)
            card_draw.discard_agenda(state, card)
        agenda.history.append({"number": agenda.agenda_number, "agenda": card, "vetoed": True})
    active_effects.expire(state, Duration.AGENDA)
    return _open_top_agenda(state, registry, state.speaker_id or "")


def add_votes(
    state: GameState, registry: StaticDataRegistry, player_id: str, amount: int
) -> GameState:
    """Dodatkowe głosy na wynik, na który gracz już głosował (Bribery, Distinguished Councilor).

    Po zmianie sum wynik jest liczony od nowa (remis może powstać albo zniknąć); wybór mówcy
    przy remisie unieważnia dodanie głosów po nim.

    Raises:
        ValueError: Ujemna liczba, krok inny niż głosowanie/remis/pauza albo brak oddanych głosów.
    """
    agenda = _require_agenda(
        state, AgendaStep.VOTE, AgendaStep.TIEBREAK, AgendaStep.COUNTED
    )
    if amount < 0:
        raise ValueError("The number of additional votes cannot be negative.")
    if amount > 0 and single_vote(state, player_id):
        raise ValueError("Representative Government: players cannot cast additional votes.")
    vote = agenda.votes.get(player_id)
    if vote is None:
        raise ValueError("You must have cast votes on this agenda to cast additional votes.")
    agenda.votes[player_id] = vote.model_copy(update={"votes": vote.votes + amount})
    if agenda.step is not AgendaStep.VOTE and amount > 0:
        agenda.pending_outcome = None
        return _close_count(state, registry)
    return state


def replace_elected(state: GameState, player_id: str) -> GameState:
    """Confounding/Confusing Legal Text: wybranym graczem zostaje ``player_id`` (w kroku COUNTED).

    Predykcje rozstrzygają się wg NOWO wybranego gracza (C_action_cards).

    Raises:
        ValueError: Gdy nie ma wybranego gracza do podmiany albo ``player_id`` jest nieznany.
    """
    agenda = _require_agenda(state, AgendaStep.COUNTED)
    if elected_player(state) is None:
        raise ValueError("No player is being elected by this agenda.")
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    if player_id not in agenda.outcomes:
        agenda.outcomes = [*agenda.outcomes, player_id]
    agenda.pending_outcome = player_id
    return state


def void_agenda(state: GameState) -> GameState:
    """Deadly Plot: agenda zostaje odrzucona BEZ efektu i bez zastąpienia; predykcje nie działają.

    Raises:
        ValueError: Poza krokiem ``COUNTED`` (wynik miałby być właśnie rozstrzygnięty).
    """
    agenda = _require_agenda(state, AgendaStep.COUNTED)
    card = agenda.agenda_id
    assert card is not None
    for discarded in (card, agenda.covert_card):
        if discarded is None:
            continue
        if discarded in state.decks.agenda_laws:
            remove_law(state, discarded)  # Miscount: Deadly Plot przy ponownym głosowaniu
        else:
            card_draw.discard_agenda(state, discarded)
    agenda.history.append(
        {
            "number": agenda.agenda_number,
            "agenda": card,
            "kind": agenda.kind,
            "outcome": None,
            "voided": True,
            "totals": totals(agenda),
            "votes": {
                pid: {"outcome": v.outcome, "votes": v.votes} for pid, v in agenda.votes.items()
            },
        }
    )
    active_effects.expire(state, Duration.AGENDA)  # predykcje i zakazy tej agendy znikają
    agenda.resolved_outcome = None
    agenda.decided_by_speaker = False
    agenda.pending_outcome = None
    agenda.pending_by_speaker = False
    agenda.last_vote_by = None
    agenda.tied = []
    agenda.step = AgendaStep.RESOLVED
    state.active_player_id = state.speaker_id or state.active_player_id
    return state
