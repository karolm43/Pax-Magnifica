"""Testy Construction i Warfare w wersji Thunder's Edge (RULES.md 30.11, 30.12)."""

from __future__ import annotations

import pytest

from src.core import production, strategic_action, tactical
from src.core.game_state import GameState, Phase, PlayerState, SystemState, TacticalStep
from src.core.hex_grid import HexGrid
from src.core.production import ProductionOrder
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("101", "26")
    grid.place_system("102", "27")
    grid.build_edges()
    return grid


def _state(card: int) -> GameState:
    """p1 (sol) aktywny z kartą ``card``, dok na Jord (101); p2 (sol) ma dok na Arinam (102)."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        systems={
            "000": SystemState(position="000", system_id="18"),
            "101": SystemState(
                position="101",
                system_id="26",
                planet_owners={"jord": "p1"},
                planet_units={"jord": {"p1": {"spacedock": 1}}},
            ),
            "102": SystemState(
                position="102",
                system_id="27",
                planet_owners={"arinam": "p2"},
                planet_units={"arinam": {"p2": {"spacedock": 1}}},
            ),
        },
        players={
            "p1": PlayerState(
                player_id="p1", color="red", faction="sol", strategy_cards=[card],
                trade_goods=20,
            ),
            "p2": PlayerState(
                player_id="p2", color="green", faction="sol", home_position="102",
                trade_goods=20,
            ),
        },
    )


# --- Construction ---------------------------------------------------------------------------


def _units(state: GameState, pos: str, planet: str, pid: str) -> dict[str, int]:
    return state.systems[pos].planet_units.get(planet, {}).get(pid, {})


def test_construction_two_structures_then_secondary(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(4), registry, "p1", 4)
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"option": "structure"}
    )
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"planet": "jord", "structure": "pds"}
    )
    assert state.pending_strategy is not None and state.pending_strategy.step == "place_structure_2"
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"planet": "jord", "structure": "pds"}
    )
    assert _units(state, "101", "jord", "p1") == {"spacedock": 1, "pds": 2}
    assert state.pending_strategy is None and state.pending_window is not None
    state = strategic_action.resolve_secondary(
        state, registry, "p2", execute=True, payload={"planet": "arinam", "structure": "pds"}
    )
    assert _units(state, "102", "arinam", "p2") == {"spacedock": 1, "pds": 1}
    assert state.players["p2"].strategic_cc == 1  # żeton ze strategy pool wydany


def test_construction_structure_limits_and_dmz(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(4), registry, "p1", 4)
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"option": "structure"}
    )
    with pytest.raises(ValueError, match="maximum"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"planet": "jord", "structure": "spacedock"}
        )
    with pytest.raises(ValueError, match="do not control"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"planet": "arinam", "structure": "pds"}
        )
    state.planet_attachments["jord"] = ["dmz"]
    with pytest.raises(ValueError, match="Demilitarized"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"planet": "jord", "structure": "pds"}
        )


def test_construction_reinforcements_limit(registry: StaticDataRegistry) -> None:
    state = _state(4)
    state.systems["101"].planet_units["jord"]["p1"]["pds"] = 0
    # Wszystkie 6 PDS gracza na planszy (inne planety) - rezerwa pusta.
    state.systems["101"].planet_owners.update({"a": "p1", "b": "p1", "c": "p1"})
    for planet in ("a", "b", "c"):
        state.systems["101"].planet_units[planet] = {"p1": {"pds": 2}}
    state = strategic_action.play_strategy_card(state, registry, "p1", 4)
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"option": "structure"}
    )
    with pytest.raises(ValueError, match="reinforcements"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"planet": "jord", "structure": "pds"}
        )


def test_construction_empty_reinforcements_moves_structure_from_board(
    registry: StaticDataRegistry,
) -> None:
    """R_component_limitations: pusta rezerwa => gracz może zdjąć PDS z systemu bez swojego
    żetonu dowodzenia i postawić go od razu (RULES.md 30.12; to samo co Reclamation)."""
    state = _state(4)
    state.systems["101"].planet_owners.update({"a": "p1", "b": "p1", "c": "p1"})
    for planet in ("a", "b", "c"):
        state.systems["101"].planet_units[planet] = {"p1": {"pds": 2}}
    state = strategic_action.play_strategy_card(state, registry, "p1", 4)
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"option": "structure"}
    )
    prompt = strategic_action.step_options(state, registry, "p1")
    assert prompt is not None
    assert "pds" in prompt["options"]["placeable"]["jord"]
    assert prompt["options"]["board_sources"]["pds"] == ["a", "b", "c"]
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"planet": "jord", "structure": "pds", "source": "a"}
    )
    assert _units(state, "101", "jord", "p1") == {"spacedock": 1, "pds": 1}
    assert _units(state, "101", "a", "p1") == {"pds": 1}


def test_construction_board_source_blocked_by_own_command_token(
    registry: StaticDataRegistry,
) -> None:
    """Źródłem nie może być system z żetonem dowodzenia gracza - wtedy PDS nie ma skąd wziąć."""
    state = _state(4)
    state.systems["101"].planet_owners.update({"a": "p1", "b": "p1", "c": "p1"})
    for planet in ("a", "b", "c"):
        state.systems["101"].planet_units[planet] = {"p1": {"pds": 2}}
    state.systems["101"].command_tokens.append("p1")
    state = strategic_action.play_strategy_card(state, registry, "p1", 4)
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"option": "structure"}
    )
    prompt = strategic_action.step_options(state, registry, "p1")
    assert prompt is not None
    assert "pds" not in prompt["options"]["placeable"].get("jord", [])
    with pytest.raises(ValueError, match="reinforcements"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"planet": "jord", "structure": "pds", "source": "a"}
        )


def test_construction_production_option_uses_one_dock_then_places(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = strategic_action.play_strategy_card(_state(4), registry, "p1", 4)
    prompt = strategic_action.step_options(state, registry, "p1")
    assert prompt is not None and prompt["options"]["docks"][0]["planet"] == "jord"
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"option": "production"}
    )
    state = strategic_action.submit_primary_step(state, registry, "p1", {"planet": "jord"})
    assert state.pending_strategy is not None and state.pending_strategy.step == "production"
    assert production.production_system(state) == "101"
    with pytest.raises(ValueError, match="Finish the production"):
        strategic_action.submit_primary_step(state, registry, "p1", {})
    # Produkcja według zwykłych reguł (dok Jord: 4 zasoby + 2), poza akcją taktyczną.
    state = production.produce(
        state, grid, registry, "p1", [ProductionOrder("infantry", 2, zone="jord")]
    )
    assert _units(state, "101", "jord", "p1")["infantry"] == 2
    assert state.production_grant is not None  # produkcja trwa do "Finish"
    # Koniec produkcji wznawia primary - krok drugiej struktury.
    state = strategic_action.after_standalone_production(production.skip_grant(state))
    assert state.pending_strategy is not None and state.pending_strategy.step == "place_structure_2"
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"planet": "jord", "structure": "pds"}
    )
    assert state.pending_window is not None


def test_construction_production_requires_a_dock(registry: StaticDataRegistry) -> None:
    state = _state(4)
    state.systems["101"].planet_units = {}
    state = strategic_action.play_strategy_card(state, registry, "p1", 4)
    with pytest.raises(ValueError, match="no space dock"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"option": "production"}
        )


def test_standalone_production_is_restricted_to_chosen_dock(
    registry: StaticDataRegistry,
) -> None:
    state = _state(4)
    state.systems["101"].planet_owners["arinam2"] = "p1"
    state.systems["101"].planet_units["arinam2"] = {"p1": {"spacedock": 1}}
    state = strategic_action.play_strategy_card(state, registry, "p1", 4)
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"option": "production"}
    )
    state = strategic_action.submit_primary_step(state, registry, "p1", {"planet": "jord"})
    zones = {p.zone for p in production.producers(state, registry, "p1", "101")}
    assert zones == {"jord"}


# --- Warfare --------------------------------------------------------------------------------


def test_warfare_primary_free_tactical_action(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state(6)
    state.systems["102"].command_tokens = ["p1"]  # własny żeton - Warfare i tak aktywuje
    before = state.players["p1"].tactical_cc
    state = strategic_action.play_strategy_card(state, registry, "p1", 6, grid=grid)
    assert state.pending_strategy is not None
    assert state.pending_strategy.step == "redistribute_before"
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"tactical": 4, "fleet": 2, "strategic": 2}, grid=grid
    )
    assert state.players["p1"].tactical_cc == 4
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"system": "102"}, grid=grid
    )
    assert state.active_system == "102" and state.tactical_step is TacticalStep.MOVEMENT
    assert state.players["p1"].tactical_cc == 4  # pula nietknięta
    assert state.systems["102"].command_tokens == ["p1"]  # bez dodatkowego żetonu
    assert state.pending_strategy is not None and state.pending_strategy.step == "tactical_action"
    assert before == 3
    with pytest.raises(ValueError, match="Finish the tactical action"):
        strategic_action.submit_primary_step(state, registry, "p1", {}, grid=grid)
    # Koniec akcji taktycznej wznawia primary: redystrybucja po akcji.
    state = tactical.end_tactical_action(state)
    assert state.pending_strategy is not None
    assert state.pending_strategy.step == "redistribute_after"
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"tactical": 2, "fleet": 4, "strategic": 2}, grid=grid
    )
    assert state.players["p1"].fleet_cc == 4
    assert state.pending_strategy is None and state.pending_window is not None


def test_warfare_free_activation_places_no_token_on_clean_system(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = strategic_action.play_strategy_card(_state(6), registry, "p1", 6, grid=grid)
    state = strategic_action.submit_primary_step(state, registry, "p1", {}, grid=grid)
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"system": "101"}, grid=grid
    )
    assert "p1" not in state.systems["101"].command_tokens
    assert state.players["p1"].tactical_cc == 3


def test_warfare_rejects_bad_redistribution_and_bad_system(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = strategic_action.play_strategy_card(_state(6), registry, "p1", 6, grid=grid)
    with pytest.raises(ValueError, match="exactly 8"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"tactical": 9, "fleet": 0, "strategic": 0}, grid=grid
        )
    state = strategic_action.submit_primary_step(state, registry, "p1", {}, grid=grid)
    with pytest.raises(ValueError, match="Choose a system"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"system": "nope"}, grid=grid
        )
    with pytest.raises(ValueError, match="needs the map grid"):
        strategic_action.submit_primary_step(state, registry, "p1", {"system": "101"})


def test_tactical_activation_blocked_after_other_action(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state(6)
    state.players["p1"].took_action_this_turn = True
    with pytest.raises(ValueError, match="already took an action"):
        tactical.activate_system(state, grid, "101")


def _warfare_secondary(registry: StaticDataRegistry) -> tuple[GameState, HexGrid]:
    grid = _grid()
    state = strategic_action.play_strategy_card(_state(6), registry, "p1", 6, grid=grid)
    state = strategic_action.submit_primary_step(state, registry, "p1", {}, grid=grid)
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"system": "101"}, grid=grid
    )
    state = tactical.end_tactical_action(state)
    state = strategic_action.submit_primary_step(state, registry, "p1", {}, grid=grid)
    return state, grid


def test_warfare_secondary_produces_in_home_system(registry: StaticDataRegistry) -> None:
    state, grid = _warfare_secondary(registry)
    assert state.pending_window is not None
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    # Kolejka czeka na produkcję respondenta; żeton wydany, ale nie położony w systemie.
    assert state.pending_window is not None and state.pending_window.cursor == 0
    assert state.players["p2"].strategic_cc == 1
    assert state.systems["102"].command_tokens == []
    with pytest.raises(ValueError, match="Finish the production"):
        strategic_action.resolve_secondary(state, registry, "p2", execute=False)
    assert production.production_player(state) == "p2"
    state = production.produce(
        state, grid, registry, "p2", [ProductionOrder("infantry", 1, zone="arinam")]
    )
    assert _units(state, "102", "arinam", "p2")["infantry"] == 1
    state = strategic_action.after_standalone_production(production.skip_grant(state))
    assert state.pending_window is None  # jedyny respondent skończył -> okno zamknięte
    assert state.production_grant is None


def test_warfare_secondary_needs_production_in_home(registry: StaticDataRegistry) -> None:
    state, _grid_unused = _warfare_secondary(registry)
    state.systems["102"].planet_units = {}
    with pytest.raises(ValueError, match="no space dock with PRODUCTION"):
        strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    assert state.players["p2"].strategic_cc == 2  # stan wejściowy nietknięty
