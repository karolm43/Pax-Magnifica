"""Faza agendy - głosowanie Rady Galaktycznej wg R_agenda_phase (RULES.md 51).

Czyste funkcje ``state -> state``. Zakres: SAMA FAZA i jej zasady; efekty konkretnych agend
(skutki wyniku, riders, predykcje, karty zmieniające głosowanie) NIE są jeszcze kodowane -
wynik jest tylko ZAPISYWANY (prawa zostają w grze, dyrektywy idą na stos odrzuconych).

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

from typing import Any

from src.core import card_draw, exhaust, objectives, strategy_phase, turn_flow
from src.core.components import AgendaDef, ComponentCategory
from src.core.game_state import (
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

# Wartości wyborów bez własnych danych w assetach (grupy technologii i pule żetonów to
# nazwy z reguł, nie liczby). Cechy planet: R_planets.
_TECH_GROUPS = ("propulsion", "biotic", "cybernetic", "warfare")
_COMMAND_POOLS = ("tactic", "fleet", "strategy")
_PLANET_TRAITS = ("cultural", "hazardous", "industrial")


# --- Klasyfikacja agendy ------------------------------------------------------------------


def agenda_def(registry: StaticDataRegistry, agenda_id: str) -> AgendaDef | None:
    """Definicja karty agendy z Katalogu_Komponentów (``None`` dla nieznanego id)."""
    definition = registry.catalog.get(ComponentCategory.AGENDA, agenda_id)
    return definition if isinstance(definition, AgendaDef) else None


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


def extra_votes(state: GameState, registry: StaticDataRegistry, player_id: str) -> int:
    """Dodatkowe głosy z efektów gry (HOOK-CANDIDATE: karty/zdolności wejdą tutaj)."""
    del state, registry, player_id
    return 0


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
    agenda = state.agenda
    sums = totals(agenda)
    best = max(sums.values(), default=0)
    leaders = [o for o, n in sums.items() if n == best]
    if best > 0 and len(leaders) == 1:
        return _resolve(state, registry, leaders[0], by_speaker=False)
    # Remis albo brak głosów: wybiera mówca spośród remisujących (przy 0 głosów - wszystkich).
    agenda.tied = leaders if best > 0 else list(agenda.outcomes)
    agenda.step = AgendaStep.TIEBREAK
    _point_to_voter(state)
    return state


def cast_vote(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    outcome: str,
    planets: list[str],
) -> GameState:
    """Gracz, którego kolej, wyczerpuje ``planets`` i oddaje głosy na ``outcome``.

    Raises:
        ValueError: Zły krok/kolejność, wynik spoza agendy, planeta nie gracza / wyczerpana /
            zdublowana / bez wpływu, gracz zablokowany albo zero głosów (to wstrzymanie się).
    """
    agenda = _require_agenda(state, AgendaStep.VOTE)
    _require_votable(state, player_id)
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
    votes = sum(usable[p] for p in planets) + extra_votes(state, registry, player_id)
    if votes <= 0:
        raise ValueError("Casting zero votes is the same as abstaining - abstain instead.")
    chosen = _normalise_outcome(agenda, outcome)
    work = state.clone()
    assert work.agenda is not None
    if chosen not in work.agenda.outcomes:
        work.agenda.outcomes = [*work.agenda.outcomes, chosen]
    work.agenda.votes[player_id] = AgendaVote(outcome=chosen, votes=votes, planets=list(planets))
    exhaust.exhaust_planets(work, player_id, planets)  # R_agenda_phase: wyczerpanie = głos
    work.players[player_id].passed = True
    return _after_vote(work, registry)


def abstain(state: GameState, registry: StaticDataRegistry, player_id: str) -> GameState:
    """Gracz, którego kolej, wstrzymuje się od głosu (nic nie wyczerpuje)."""
    _require_agenda(state, AgendaStep.VOTE)
    _require_votable(state, player_id)
    work = state.clone()
    assert work.agenda is not None
    work.agenda.abstained.append(player_id)
    work.players[player_id].passed = True
    return _after_vote(work, registry)


# --- Wynik ---------------------------------------------------------------------------------


def _resolve(
    state: GameState, registry: StaticDataRegistry, outcome: str, *, by_speaker: bool
) -> GameState:
    """Zapisuje wynik: prawo zostaje w grze (For/Elect), reszta idzie na stos odrzuconych.

    R_agenda_card: jeśli rozstrzygnięto „For" albo wybory prawa, karta zostaje w grze;
    dyrektywa i „Against" trafiają na stos odrzuconych. Samych skutków NIE stosujemy.
    """
    assert state.agenda is not None
    agenda = state.agenda
    card = agenda.agenda_id
    assert card is not None
    definition = agenda_def(registry, card)
    is_law = definition is not None and (definition.type or "").strip().lower() == "law"
    stays = is_law and outcome != "against"
    if stays:
        state.decks.agenda_laws[card] = outcome
    else:
        card_draw.discard_agenda(state, card)
    agenda.resolved_outcome = outcome
    agenda.decided_by_speaker = by_speaker
    agenda.tied = []
    agenda.step = AgendaStep.RESOLVED
    agenda.history.append(
        {
            "number": agenda.agenda_number,
            "agenda": card,
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
    return state


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
    return _resolve(work, registry, chosen, by_speaker=True)


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
    work = state.clone()
    card = card_draw.draw_agenda(work, registry)
    if card is None:
        raise ValueError("The agenda deck is empty.")
    assert work.agenda is not None
    _clear_round_of_voting(work)
    agenda = work.agenda
    definition = agenda_def(registry, card)
    agenda.agenda_id = card
    agenda.kind = classify_target(definition.target if definition is not None else None)
    agenda.outcomes = candidate_outcomes(work, registry, agenda.kind)
    agenda.unresolvable = agenda.kind != "manual" and not agenda.outcomes
    agenda.vote_order = vote_order(work)
    agenda.step = AgendaStep.VOTE
    if not agenda.unresolvable and current_voter(work) is None:
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
    card_draw.discard_agenda(work, work.agenda.agenda_id)
    work.agenda.history.append(
        {"number": work.agenda.agenda_number, "agenda": work.agenda.agenda_id, "discarded": True}
    )
    _clear_round_of_voting(work)
    work.agenda.step = AgendaStep.REVEAL
    work.active_player_id = work.speaker_id or work.active_player_id
    return work


def _ready_all_planets(work: GameState) -> None:
    """Krok 3 fazy: każdy gracz odświeża wszystkie swoje wyczerpane planety."""
    for pid in work.players:
        exhaust.ready_all_planets(work, pid)


def continue_agenda(state: GameState, registry: StaticDataRegistry, player_id: str) -> GameState:
    """Po wyniku: druga agenda (krok 2) albo - po drugiej - odświeżenie planet (krok 3)."""
    del registry
    agenda = _require_agenda(state, AgendaStep.RESOLVED)
    _require_speaker(state, player_id)
    work = state.clone()
    assert work.agenda is not None
    if agenda.agenda_number < AGENDAS_PER_PHASE:
        work.agenda.agenda_number += 1
        _clear_round_of_voting(work)
        work.agenda.step = AgendaStep.REVEAL
    else:
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
    return turn_flow.next_round(state)


def skip_agenda(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Tryb testowy (God-Mode ``/phase/skip``): pomija głosowania, odświeża planety, nowa runda."""
    del registry
    work = state.clone()
    _ready_all_planets(work)
    return turn_flow.next_round(work)


_PLAYER_KINDS = ("player", "player_techs", "player_or_against")


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
