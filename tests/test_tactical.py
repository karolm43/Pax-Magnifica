"""Testy akcji taktycznej (Etap E3) — czyste funkcje ``tactical`` + God-Mode CC.

Aplikacja prowadzi kroki akcji taktycznej, ale NIE waliduje reguł TI4 — testy
sprawdzają mechaniczne operacje na stanie (aktywacja kładzie żeton i ustawia krok,
maszyna kroków przechodzi w sekwencji, zakończenie czyści), bez egzekwowania zasad.
"""

from __future__ import annotations

import pytest

from src.core import board_edit, tactical
from src.core.game_state import GameState, Phase, PlayerState, TacticalStep
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid(registry: StaticDataRegistry) -> HexGrid:
    """Mała, realna mapa: Mecatol + pierwszy pierścień (pozycje 101-106)."""
    from src.core.map_string import build_grid_from_map_string

    return build_grid_from_map_string("18 101 102 103 104 105 106", registry)


def _state() -> GameState:
    """Stan w fazie akcji z aktywnym graczem p1 (Sol)."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={"p1": PlayerState(player_id="p1", faction="sol", color="red")},
    )


def test_activate_system_places_token_and_sets_step(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid(registry)
    state = _state()
    result = tactical.activate_system(state, grid, "101")

    # Żeton dowodzenia aktywnego gracza w przestrzeni systemu.
    assert result.systems["101"].command_tokens == ["p1"]
    # Aktywny system ustawiony, maszyna kroków startuje od ruchu.
    assert result.active_system == "101"
    assert result.tactical_step is TacticalStep.MOVEMENT
    # Zużyty 1 żeton z puli taktycznej (3 -> 2).
    assert result.players["p1"].tactical_cc == 2
    # Wejście nie jest mutowane.
    assert state.active_system is None
    assert state.tactical_step is None
    assert state.players["p1"].tactical_cc == 3


def test_activate_without_active_player_raises(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = GameState(phase=Phase.ACTION)  # brak active_player_id
    with pytest.raises(ValueError, match="aktywnego gracza"):
        tactical.activate_system(state, grid, "101")


def test_activate_is_idempotent_on_token(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = _state()
    once = tactical.activate_system(state, grid, "101")
    twice = tactical.activate_system(once, grid, "101")
    # Powtórna aktywacja nie duplikuje żetonu (set-like lista).
    assert twice.systems["101"].command_tokens == ["p1"]


def test_next_step_follows_sequence(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = tactical.activate_system(_state(), grid, "101")
    assert state.tactical_step is TacticalStep.MOVEMENT
    state = tactical.next_step(state)
    assert state.tactical_step is TacticalStep.SPACE_CANNON
    state = tactical.next_step(state)
    assert state.tactical_step is TacticalStep.SPACE_COMBAT
    state = tactical.next_step(state)
    assert state.tactical_step is TacticalStep.INVASION
    state = tactical.next_step(state)
    assert state.tactical_step is TacticalStep.PRODUCTION


def test_next_step_after_production_ends_action(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = tactical.set_step(
        tactical.activate_system(_state(), grid, "101"), TacticalStep.PRODUCTION
    )
    ended = tactical.next_step(state)
    # Po produkcji akcja taktyczna się kończy (czyści krok i aktywny system).
    assert ended.tactical_step is None
    assert ended.active_system is None
    # Żeton dowodzenia ZOSTAJE na systemie (jak na stole).
    assert ended.systems["101"].command_tokens == ["p1"]


def test_next_step_noop_when_no_action(registry: StaticDataRegistry) -> None:
    state = _state()  # tactical_step is None
    result = tactical.next_step(state)
    assert result.tactical_step is None


def test_end_tactical_action_clears_active(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = tactical.activate_system(_state(), grid, "101")
    ended = tactical.end_tactical_action(state)
    assert ended.active_system is None
    assert ended.tactical_step is None
    # Żeton zostaje.
    assert ended.systems["101"].command_tokens == ["p1"]


def test_god_mode_place_and_remove_command_token(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid(registry)
    state = _state()
    # God-Mode nie zużywa puli taktycznej (ręczna korekta operatora).
    placed = board_edit.place_command_token(state, grid, "102", "sol")
    assert placed.systems["102"].command_tokens == ["p1"]
    assert placed.players["p1"].tactical_cc == 3  # pula nietknięta

    removed = board_edit.remove_command_token(placed, grid, "102", "sol")
    assert "p1" not in removed.systems.get("102", placed.systems["102"]).command_tokens
