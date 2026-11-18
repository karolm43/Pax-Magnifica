"""Setup startowy gry po rozstawieniu graczy (RULES.md 45).

Czyste funkcje ``state -> state``. Kolejność etapów (``SetupStage``):

1. ``SECRETS`` — każdy gracz dobiera 2 tajne cele i zatrzymuje 1 (wybór równoczesny; jeden ekran
   pokazuje ich po kolei zasiadania), drugi wraca do talii i talia jest tasowana. Boty wybierają
   automatycznie.
2. ``CUSTODIANS`` — mówca kładzie żeton Custodians na Mecatol Rex.
3. ``OBJECTIVES`` — mówca odkrywa dwa cele publiczne I etapu (pozostałe 8 leży zakryte).

Dodatkowo ``begin_setup`` rozdaje każdemu graczowi rękę promissory notes: komplet wspólnych
notek jego koloru + notkę frakcyjną. Po ostatnim etapie ``state.setup`` wraca do ``None`` i
zaczyna się faza strategii. Dane (które notki są wspólne, które cele) pochodzą z katalogu
komponentów — zero hardkodowania.
"""

from __future__ import annotations

import random

from src.core import (
    objectives,
    promissory_notes,
    secret_objectives,
    strategy_phase,
    triggers,
    variants,
)
from src.core.components import ComponentCategory
from src.core.dice import next_rng
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ControlType,
    GameState,
    SetupStage,
    SetupState,
    SystemState,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

# Placeholder koloru w identyfikatorach wspólnych promissory notes (plik color.json).
_COLOR_PLACEHOLDER = "<color>"


def common_promissory_note_ids(registry: StaticDataRegistry, color: str) -> list[str]:
    """Identyfikatory wspólnych promissory notes dla danego koloru (np. ``red_cf``).

    Szablony ``<color>_*`` z aktywnych (oficjalnych) źródeł katalogu; kolejność
    deterministyczna (alias). Erraty modułów wariantów (np. Absol's Political Secret) są
    nałożone w rejestrze gry pod oficjalnym id szablonu (``<color>_ps``).
    """
    notes = registry.catalog.all(ComponentCategory.PROMISSORY_NOTE)
    fan = variants.variant_sources()
    templates = sorted(
        note_id
        for note_id, note in notes.items()
        if note_id.startswith(f"{_COLOR_PLACEHOLDER}_") and note.source not in fan
    )
    return [note_id.replace(_COLOR_PLACEHOLDER, color, 1) for note_id in templates]


def deal_promissory_notes(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Rozdaje każdemu graczowi wspólne notki jego koloru + notkę frakcyjną (do ręki)."""
    new_state = state.clone()
    for player_id, player in new_state.players.items():
        hand: list[str] = []
        if player.color is not None:
            hand.extend(
                common_promissory_note_ids(registry, player.color)
            )
        faction = registry.factions.get(player.faction) if player.faction else None
        if faction is not None:
            hand.extend(n for n in faction.promissory_notes if n not in hand)
        promissory_notes.set_hand(new_state, player_id, hand)
    return new_state


def place_frontier_tokens(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Kładzie żeton frontier w każdym systemie bez planet (R_frontier_tokens).

    Dotyczy pustej przestrzeni, anomalii bez planet, wormholi oraz bram Creuss Gate i The
    Sorrow (systemy bez planet). Pomija kafelki hyperlane i puste sloty domowe. Idempotentne:
    max jeden żeton na system.
    """
    new_state = state.clone()
    for position in grid.positions:
        system_id = grid.system_id_at(position)
        system = registry.systems.get(system_id)
        if system is None or system.planets or _is_hyperlane(system.name):
            continue
        sys_state = new_state.systems.get(position)
        if sys_state is None:
            sys_state = SystemState(position=position, system_id=system_id)
            new_state.systems[position] = sys_state
        sys_state.frontier_token = True
    return new_state


def _is_hyperlane(name: str | None) -> bool:
    return (name or "").strip().lower() == "hyperlane"


def current_chooser(state: GameState) -> str | None:
    """Gracz, który teraz wybiera tajny cel (pierwszy w kolejności zasiadania), albo ``None``."""
    if state.setup is None or state.setup.stage is not SetupStage.SECRETS:
        return None
    for player_id in state.seating_order:
        player = state.players.get(player_id)
        if (
            player is not None
            and player_id not in state.setup.secrets_chosen
            and player.private.secret_candidates
        ):
            return player_id
    return None


def pending_choosers(state: GameState) -> list[str]:
    """Gracze, którzy jeszcze nie zatrzymali tajnego celu (kolejność zasiadania); jawne."""
    if state.setup is None or state.setup.stage is not SetupStage.SECRETS:
        return []
    return [
        player_id
        for player_id in state.seating_order
        if (player := state.players.get(player_id)) is not None
        and player_id not in state.setup.secrets_chosen
        and player.private.secret_candidates
    ]


def begin_setup(
    state: GameState, registry: StaticDataRegistry, rng: random.Random | None = None
) -> GameState:
    """Przygotowuje cele/talie (tryb interaktywny), rozdaje notki i otwiera setup."""
    chooser = rng if rng is not None else random.Random()
    new_state = objectives.setup_objectives(state, registry, chooser, interactive=True)
    new_state = deal_promissory_notes(new_state, registry)
    new_state.setup = SetupState()
    # Boty nie czekają na człowieka — wybierają losowo od razu.
    for player_id in list(new_state.seating_order):
        player = new_state.players.get(player_id)
        if (
            player is not None
            and player.control_type is ControlType.BOT
            and player.private.secret_candidates
        ):
            _apply_secret_choice(
                new_state, player_id, chooser.choice(player.private.secret_candidates), chooser
            )
    return _advance(new_state)


def choose_secret(
    state: GameState,
    player_id: str,
    objective_id: str,
    rng: random.Random | None = None,
) -> GameState:
    """Gracz zatrzymuje jeden z dwóch dobranych tajnych celów; drugi wraca do talii.

    Raises:
        ValueError: setup nie jest na etapie wyboru, gracz już wybrał (albo nie ma kandydatów)
            lub cel nie jest jednym z jego kandydatów.

    Wybór jest RÓWNOCZESNY (RULES.md 45.3): każdy gracz z kandydatami może wybrać w dowolnej
    chwili — w grze sieciowej wszyscy wybierają naraz. Kolejność zasiadania
    (``current_chooser``) służy tylko widokowi jednego ekranu (bramka „przekaż ekran").
    """
    if state.setup is None or state.setup.stage is not SetupStage.SECRETS:
        raise ValueError("Secret objectives are not being chosen right now.")
    if player_id not in pending_choosers(state):
        raise ValueError(f"{player_id} has no secret objective left to choose.")
    if objective_id not in state.players[player_id].private.secret_candidates:
        raise ValueError(f"{objective_id} is not one of the dealt secret objectives.")
    new_state = state.clone()
    # Tasowanie odrzuconego celu z seedowalnego RNG stanu (RULES.md 38): Undo/Replay i symulacje
    # bota dają ten sam wynik (wcześniej niezasiany ``random.Random()``).
    _apply_secret_choice(
        new_state, player_id, objective_id, rng if rng is not None else next_rng(new_state)
    )
    return _advance(new_state)


def place_custodians(state: GameState, player_id: str) -> GameState:
    """Mówca kładzie żeton Custodians na Mecatol Rex (etap ``CUSTODIANS``)."""
    _require_speaker_stage(state, player_id, SetupStage.CUSTODIANS)
    new_state = state.clone()
    assert new_state.setup is not None
    new_state.setup.custodians_placed = True
    new_state.setup.stage = SetupStage.OBJECTIVES
    return _advance(new_state)


def reveal_objectives(state: GameState, player_id: str) -> GameState:
    """Mówca odkrywa dwa cele I etapu (etap ``OBJECTIVES``) — kończy setup."""
    _require_speaker_stage(state, player_id, SetupStage.OBJECTIVES)
    new_state = state.clone()
    for _ in range(objectives.REVEALED_AT_SETUP):
        new_state, _revealed = objectives.reveal_next_public(new_state)
    new_state.setup = None
    new_state.active_player_id = (
        strategy_phase.next_strategy_picker(new_state) or new_state.speaker_id
    )
    # Koniec przygotowania gry: moment „during setup" / „when you create the game board".
    triggers.fire(new_state, GameEvent.SETUP, Moment.DURING)
    triggers.fire(new_state, GameEvent.SETUP, Moment.WHEN)
    return new_state


def skip_setup(state: GameState, rng: random.Random | None = None) -> GameState:
    """Pomija resztę setupu: losuje brakujące tajne cele, kładzie Custodians, odkrywa cele.

    Skrót dla operatora (bez sprawdzania, kto jest mówcą) — działa z dowolnego etapu.

    Raises:
        ValueError: setup nie jest w toku.
    """
    if state.setup is None:
        raise ValueError("Setup is not in progress.")
    new_state = state.clone()
    chooser = rng if rng is not None else next_rng(new_state)  # seedowalnie (RULES.md 38)
    if new_state.setup is not None and new_state.setup.stage is SetupStage.SECRETS:
        for player_id in list(new_state.seating_order):
            player = new_state.players.get(player_id)
            if (
                player is not None
                and player_id not in new_state.setup.secrets_chosen
                and player.private.secret_candidates
            ):
                _apply_secret_choice(
                    new_state, player_id, chooser.choice(player.private.secret_candidates), chooser
                )
        new_state = _advance(new_state)
    speaker = new_state.speaker_id
    if speaker is None:
        raise ValueError("There is no speaker.")
    if new_state.setup is not None and new_state.setup.stage is SetupStage.CUSTODIANS:
        new_state = place_custodians(new_state, speaker)
    return reveal_objectives(new_state, speaker)


def _require_speaker_stage(state: GameState, player_id: str, stage: SetupStage) -> None:
    if state.setup is None or state.setup.stage is not stage:
        raise ValueError(f"Setup is not at the {stage.value} stage.")
    if player_id != state.speaker_id:
        raise ValueError("Only the speaker can do this.")


def _apply_secret_choice(
    state: GameState, player_id: str, objective_id: str, rng: random.Random
) -> None:
    """Mutuje stan: wybrany cel do ręki, odrzucone do talii (tasowanie), gracz odhaczony."""
    assert state.setup is not None
    secret_objectives.choose_candidate(state, player_id, objective_id, rng)
    state.setup.secrets_chosen = [*state.setup.secrets_chosen, player_id]


def _advance(state: GameState) -> GameState:
    """Przechodzi do kolejnego etapu, gdy bieżący jest zamknięty, i ustawia aktywnego gracza."""
    setup = state.setup
    if setup is None:
        return state
    if setup.stage is SetupStage.SECRETS:
        chooser = current_chooser(state)
        if chooser is not None:
            state.active_player_id = chooser
            return state
        setup.stage = SetupStage.CUSTODIANS
    state.active_player_id = state.speaker_id
    return state
