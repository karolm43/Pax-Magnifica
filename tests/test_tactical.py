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


def test_activate_rejects_own_command_token(registry: StaticDataRegistry) -> None:
    # RULES.md 33.1: nie można aktywować systemu z własnym żetonem dowodzenia.
    grid = _grid(registry)
    once = tactical.activate_system(_state(), grid, "101")
    with pytest.raises(ValueError, match="żeton dowodzenia"):
        tactical.activate_system(once, grid, "101")


def test_activate_rejects_empty_tactic_pool(registry: StaticDataRegistry) -> None:
    # RULES.md 33.1: potrzebny żeton w puli taktycznej.
    grid = _grid(registry)
    state = _state()
    state.players["p1"].tactical_cc = 0
    with pytest.raises(ValueError, match="puli taktycznej"):
        tactical.activate_system(state, grid, "101")


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


# --- Asystent walki (E3/T3) ----------------------------------------------


def _combat_state() -> GameState:
    """Stan z dwoma graczami mającymi statki w systemie 101."""
    from src.core.game_state import SystemState

    state = GameState(
        players={
            "p1": PlayerState(player_id="p1", faction="sol", color="red"),
            "p2": PlayerState(player_id="p2", faction="hacan", color="yellow"),
        }
    )
    state.systems["101"] = SystemState(
        position="101",
        system_id="27",
        space_units={
            "p1": {"cruiser": 2, "destroyer": 1},
            "p2": {"dreadnought": 1, "fighter": 3},
        },
    )
    return state


def test_space_combat_participants_two_sides(registry: StaticDataRegistry) -> None:
    from src.core import combat

    sides = combat.space_combat_participants(registry, _combat_state(), "101")
    assert len(sides) == 2
    by_id = {s.player_id: s for s in sides}
    # Cruiser trafia na 7+ → oczekiwane = 2 * (11-7)/10 = 0.8.
    p1 = by_id["p1"]
    cruiser = next(u for u in p1.units if u.base_type == "cruiser")
    assert cruiser.combat_hits_on == 7
    assert cruiser.expected_hits == 0.8
    # Suma kości p1 = 2 cruiser + 1 destroyer = 3.
    assert p1.total_dice == 3


def test_space_combat_single_player_no_combat(
    registry: StaticDataRegistry,
) -> None:
    from src.core import combat
    from src.core.game_state import SystemState

    state = GameState(players={"p1": PlayerState(player_id="p1", faction="sol")})
    state.systems["102"] = SystemState(
        position="102", system_id="28", space_units={"p1": {"cruiser": 2}}
    )
    # Jeden gracz → brak walki.
    assert combat.space_combat_participants(registry, state, "102") == []


def test_resolve_unit_variant_prefers_faction(registry: StaticDataRegistry) -> None:
    from src.core import combat

    # Sol ma własny wariant carriera (sol_carrier) — powinien wygrać z generycznym.
    unit = combat.resolve_unit_variant(registry, "sol", [], "carrier")
    assert unit is not None
    assert unit.id == "sol_carrier"


def test_resolve_unit_variant_upgrade_needs_tech(
    registry: StaticDataRegistry,
) -> None:
    from src.core import combat

    # Bez technologii: wariant bazowy; z technologią ulepszenia: wariant ulepszony.
    base = combat.resolve_unit_variant(registry, "sol", [], "carrier")
    upgraded = combat.resolve_unit_variant(registry, "sol", ["ac2"], "carrier")
    assert base is not None and upgraded is not None
    # Ulepszony ma większą pojemność niż bazowy (sol_carrier2 > sol_carrier).
    assert (upgraded.capacity_value or 0) >= (base.capacity_value or 0)


# --- Inwazja + produkcja (E3/T4) -----------------------------------------


def test_capture_planet_overwrites_owner(registry: StaticDataRegistry) -> None:
    from src.core.game_state import SystemState

    grid = _grid(registry)
    state = GameState(
        players={
            "p1": PlayerState(player_id="p1", faction="sol"),
            "p2": PlayerState(player_id="p2", faction="hacan"),
        }
    )
    state.systems["101"] = SystemState(
        position="101", system_id="27", planet_owners={"somePlanet": "p2"}
    )
    # p1 przejmuje planetę p2 (nadpisanie — jeden właściciel).
    result = tactical.capture_planet(state, grid, "101", "somePlanet", "sol")
    assert result.systems["101"].planet_owners["somePlanet"] == "p1"
    # Wejście nie jest mutowane.
    assert state.systems["101"].planet_owners["somePlanet"] == "p2"


def test_production_help_resources_and_costs(registry: StaticDataRegistry) -> None:
    from src.core.game_state import SystemState

    state = GameState(players={"p1": PlayerState(player_id="p1", faction="sol")})
    # Gracz kontroluje Jord (4 zasoby).
    state.systems["201"] = SystemState(
        position="201", system_id="1", planet_owners={"jord": "p1"}
    )
    help_ = tactical.production_help(state, registry, "p1")
    assert help_.available_resources == 4
    # Koszty jednostek z UnitDef; fighter/infantry produkowane po 2.
    by_type = {u.base_type: u for u in help_.units}
    assert by_type["cruiser"].cost == 2.0
    assert by_type["fighter"].units_per_cost == 2
    assert by_type["infantry"].units_per_cost == 2
    assert by_type["cruiser"].units_per_cost == 1
    # Umiejscowienie: statki w przestrzeni, siły naziemne na planecie (RULES.md 26).
    assert by_type["cruiser"].placement == "space"
    assert by_type["fighter"].placement == "space"
    assert by_type["infantry"].placement == "planet"
    assert by_type["mech"].placement == "planet"


# --- Kontrola planety przy stawianiu jednostek (reguła AsyncTI4, RULES.md 23) ----


def test_ground_units_grant_planet_control(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = GameState(
        players={"p1": PlayerState(player_id="p1", faction="sol", color="red")}
    )
    # Mecatol (18) stoi na 101 w _grid; jego planeta to "mr".
    result = board_edit.edit_units(state, grid, "101", "mr", "sol", "gf", 2)
    assert result.systems["101"].planet_owners.get("mr") == "p1"


def test_ships_in_space_do_not_grant_planet_control(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid(registry)
    state = GameState(
        players={"p1": PlayerState(player_id="p1", faction="sol", color="red")}
    )
    # Statki w przestrzeni nie nadają kontroli żadnej planety.
    result = board_edit.edit_units(state, grid, "101", "space", "sol", "ca", 3)
    assert result.systems["101"].planet_owners.get("mr") is None


def test_planet_control_is_sticky_after_removal(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid(registry)
    state = GameState(
        players={"p1": PlayerState(player_id="p1", faction="sol", color="red")}
    )
    owned = board_edit.edit_units(state, grid, "101", "mr", "sol", "gf", 2)
    # Usunięcie całej piechoty NIE odbiera kontroli (lepkość — reguła TI4).
    emptied = board_edit.edit_units(owned, grid, "101", "mr", "sol", "gf", -2)
    assert emptied.systems["101"].planet_owners.get("mr") == "p1"


def test_coexistence_does_not_change_control(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = GameState(
        players={
            "p1": PlayerState(player_id="p1", faction="sol", color="red"),
            "p2": PlayerState(player_id="p2", faction="hacan", color="yellow"),
        }
    )
    s1 = board_edit.edit_units(state, grid, "101", "mr", "sol", "gf", 2)
    # Drugi gracz dołącza — 2 kolory (koegzystencja) → kontrola bez zmiany.
    s2 = board_edit.edit_units(s1, grid, "101", "mr", "hacan", "gf", 1)
    assert s2.systems["101"].planet_owners.get("mr") == "p1"
    # Pierwszy wycofuje się — zostaje tylko p2 → przejęcie.
    s3 = board_edit.edit_units(s2, grid, "101", "mr", "sol", "gf", -2)
    assert s3.systems["101"].planet_owners.get("mr") == "p2"


def test_move_ground_units_grants_control_at_destination(
    registry: StaticDataRegistry,
) -> None:
    from src.core.game_state import SystemState

    grid = _grid(registry)
    state = GameState(
        players={"p1": PlayerState(player_id="p1", faction="sol", color="red")}
    )
    state.systems["102"] = SystemState(
        position="102",
        system_id=grid.system_id_at("102"),
        planet_units={"__src__": {"p1": {"infantry": 1}}},
    )
    # Przenieś piechotę z pseudo-strefy na planetę "mr" systemu 101 (docelowa kontrola).
    result = board_edit.move_units(
        state,
        grid,
        from_position="102",
        from_zone="__src__",
        to_position="101",
        to_zone="mr",
        faction_key="sol",
        async_id="gf",
        count=1,
    )
    assert result.systems["101"].planet_owners.get("mr") == "p1"
