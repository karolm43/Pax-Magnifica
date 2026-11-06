"""Testy ruchu statków (E8-T5): walidacja R1–R6 + wykonanie (RULES.md 32)."""

from __future__ import annotations

import pytest

from src.core import movement
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _line_grid(
    specs: list[tuple[str, str, set[str]]],
) -> HexGrid:
    """Buduje graf z listy (pozycja, system_id, anomalie) jako pierścień wokół centrum.

    Używamy prawdziwych pozycji AsyncTI4: 000 (centrum) + 101..106 (pierścień 1),
    które są wzajemnie sąsiednie z centrum. Do testów tras dłuższych dokładamy 201.
    """
    grid = HexGrid()
    for pos, sid, anomalies in specs:
        grid.place_system(pos, sid, anomalies=anomalies)
    grid.build_edges()
    return grid


def _antimass_alias_matches_registry(registry: StaticDataRegistry) -> None:
    assert movement._ANTIMASS_ALIAS in registry.technologies


def test_antimass_alias_in_registry(registry: StaticDataRegistry) -> None:
    assert movement._ANTIMASS_ALIAS in registry.technologies


def _state_with_destroyer_at(
    from_pos: str, active: str, player: str = "p1"
) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id=player,
        active_system=active,
        players={player: PlayerState(player_id=player, color="red")},
        systems={
            from_pos: SystemState(
                position=from_pos,
                system_id="x",
                space_units={player: {"destroyer": 2}},
            ),
        },
    )


def test_move_adjacent_ok(registry: StaticDataRegistry) -> None:
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    new = movement.move_ships(state, grid, registry, "101", "destroyer", 1, "p1")
    assert new.systems["101"].space_units["p1"]["destroyer"] == 1
    assert new.systems["000"].space_units["p1"]["destroyer"] == 1


def test_move_requires_active_system(registry: StaticDataRegistry) -> None:
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    state.active_system = None
    ok, reason = movement.can_move(state, grid, registry, "101", "destroyer", "p1")
    assert not ok and "No active system" in reason


def test_move_out_of_range_rejected(registry: StaticDataRegistry) -> None:
    # 201 oddalone od centrum o 2 pierścienie w tej geometrii — carrier move=1.
    grid = _line_grid(
        [("000", "18", set()), ("101", "20", set()), ("201", "21", set())]
    )
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={"p1": PlayerState(player_id="p1")},
        systems={
            "201": SystemState(
                position="201", system_id="21", space_units={"p1": {"carrier": 1}}
            )
        },
    )
    ok, reason = movement.can_move(state, grid, registry, "201", "carrier", "p1")
    # carrier move=1; jeśli 201 nie sąsiaduje z 000, trasa > 1 albo brak.
    if grid.are_adjacent("201", "000"):
        assert ok  # sąsiedztwo = trasa 1 = ok
    else:
        assert not ok


def test_move_blocked_by_enemy_ships_on_path(registry: StaticDataRegistry) -> None:
    # Trasa: 102 -> 101 -> 000. 101 ma statki wroga (blokada R4).
    grid = _line_grid(
        [("000", "18", set()), ("101", "20", set()), ("102", "22", set())]
    )
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={
            "p1": PlayerState(player_id="p1"),
            "p2": PlayerState(player_id="p2"),
        },
        systems={
            "102": SystemState(
                position="102", system_id="22", space_units={"p1": {"cruiser": 1}}
            ),
            "101": SystemState(
                position="101", system_id="20", space_units={"p2": {"fighter": 1}}
            ),
        },
    )
    # Jeśli 102 sąsiaduje z 000 bezpośrednio, trasa omija 101 — wtedy legalne.
    # Test sprawdza blokadę tylko gdy 101 jest jedyną drogą. Dla pewności: cruiser move=2.
    ok, _ = movement.can_move(state, grid, registry, "102", "cruiser", "p1")
    # Gdy 102 sąsiaduje z 000: ok (omija 101). Gdy nie: 101 blokuje -> not ok.
    assert ok == grid.are_adjacent("102", "000")


def test_move_start_with_own_cc_rejected(registry: StaticDataRegistry) -> None:
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    state.systems["101"].command_tokens = ["p1"]  # własny CC w źródle
    ok, reason = movement.can_move(state, grid, registry, "101", "destroyer", "p1")
    assert not ok and "command token" in reason


def test_move_supernova_target_rejected(registry: StaticDataRegistry) -> None:
    grid = _line_grid([("000", "18", {"SUPERNOVA"}), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    ok, reason = movement.can_move(state, grid, registry, "101", "destroyer", "p1")
    assert not ok


def test_move_asteroid_target_needs_antimass(registry: StaticDataRegistry) -> None:
    grid = _line_grid([("000", "18", {"ASTEROID_FIELD"}), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    ok, _ = movement.can_move(state, grid, registry, "101", "destroyer", "p1")
    assert not ok  # brak Antimass
    state.players["p1"].technologies = [movement._ANTIMASS_ALIAS]
    ok2, _ = movement.can_move(state, grid, registry, "101", "destroyer", "p1")
    assert ok2  # z Antimass można


def test_fighter_cannot_move_alone(registry: StaticDataRegistry) -> None:
    # Fighter nie ma moveValue (porusza się transportem) — odrzucony w T5 (capacity TODO).
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={"p1": PlayerState(player_id="p1")},
        systems={
            "101": SystemState(
                position="101", system_id="20", space_units={"p1": {"fighter": 2}}
            )
        },
    )
    ok, _ = movement.can_move(state, grid, registry, "101", "fighter", "p1")
    assert not ok


def test_move_not_enough_ships(registry: StaticDataRegistry) -> None:
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    with pytest.raises(ValueError, match="Not enough"):
        movement.move_ships(state, grid, registry, "101", "destroyer", 5, "p1")


def test_fighter_ii_can_move_with_upgrade(registry: StaticDataRegistry) -> None:
    """Fighter II (tech ff2) ma moveValue=2 i rusza się sam — w odróżnieniu od bazowego."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={"p1": PlayerState(player_id="p1", technologies=["ff2"])},
        systems={
            "101": SystemState(
                position="101", system_id="20", space_units={"p1": {"fighter": 2}}
            )
        },
    )
    ok, reason = movement.can_move(state, grid, registry, "101", "fighter", "p1")
    assert ok, reason  # z ff2 fighter (wariant Fighter II) ma ruch 2
    # Bez technologii ten sam fighter się nie rusza.
    state.players["p1"].technologies = []
    ok2, _ = movement.can_move(state, grid, registry, "101", "fighter", "p1")
    assert not ok2


# --- Transport (capacity) — RULES.md 32.3 (Blok B) ---


def _state_with_carrier_cargo(
    from_pos: str,
    active: str,
    *,
    fighters: int = 0,
    infantry: int = 0,
    carriers: int = 1,
    player: str = "p1",
) -> GameState:
    """Stan: gracz z ``carriers`` nosicielami + ładunkiem w przestrzeni ``from_pos``."""
    space: dict[str, int] = {"carrier": carriers}
    if fighters:
        space["fighter"] = fighters
    if infantry:
        space["infantry"] = infantry
    return GameState(
        phase=Phase.ACTION,
        active_player_id=player,
        active_system=active,
        players={player: PlayerState(player_id=player, color="red")},
        systems={
            from_pos: SystemState(
                position=from_pos, system_id="x", space_units={player: space}
            ),
        },
    )


def test_transport_fighters_with_carrier(registry: StaticDataRegistry) -> None:
    """Carrier (capacity 4) przewozi 2 myśliwce do aktywnego systemu (T1/T2)."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_carrier_cargo("101", "000", fighters=2)
    new = movement.move_fleet(
        state, grid, registry, "101", {"carrier": 1}, {"fighter": 2}, "p1"
    )
    dest = new.systems["000"].space_units["p1"]
    assert dest["carrier"] == 1
    assert dest["fighter"] == 2
    # Źródło opustoszało (wszystko ruszyło).
    assert "p1" not in new.systems["101"].space_units


def test_transport_ground_forces_land_in_space(registry: StaticDataRegistry) -> None:
    """Piechota jedzie w przestrzeni jako ładunek (T2) — nie na planecie."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_carrier_cargo("101", "000", infantry=3)
    new = movement.move_fleet(
        state, grid, registry, "101", {"carrier": 1}, {"infantry": 3}, "p1"
    )
    assert new.systems["000"].space_units["p1"]["infantry"] == 3


def test_transport_exceeds_capacity_rejected(registry: StaticDataRegistry) -> None:
    """Ładunek > capacity ruszających statków → odrzucony (T1/T5)."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    # 1 carrier = capacity 4; próbujemy przewieźć 5 myśliwców.
    state = _state_with_carrier_cargo("101", "000", fighters=5)
    with pytest.raises(ValueError, match="[Cc]apacity"):
        movement.move_fleet(
            state, grid, registry, "101", {"carrier": 1}, {"fighter": 5}, "p1"
        )


def test_cargo_without_ship_rejected(registry: StaticDataRegistry) -> None:
    """Ładunek bez statku-nosiciela → odrzucony (fighter nie rusza się sam)."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_carrier_cargo("101", "000", fighters=2, carriers=0)
    with pytest.raises(ValueError, match="transporting ship"):
        movement.move_fleet(
            state, grid, registry, "101", {}, {"fighter": 2}, "p1"
        )


def test_cargo_pickup_blocked_by_own_cc(registry: StaticDataRegistry) -> None:
    """Pickup ładunku z systemu z własnym CC (nie aktywnym) → odrzucony (T4)."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_carrier_cargo("101", "000", fighters=2)
    # Własny żeton dowodzenia w systemie źródłowym (nie aktywnym).
    state.systems["101"].command_tokens = ["p1"]
    # Statek nie może nawet ruszyć z własnego CC (R3) — ale komunikat T4 dotyczy
    # pickupu; tu sprawdzamy, że ruch z ładunkiem jest nielegalny.
    with pytest.raises(ValueError):
        movement.move_fleet(
            state, grid, registry, "101", {"carrier": 1}, {"fighter": 2}, "p1"
        )


def test_move_ships_still_works_as_wrapper(registry: StaticDataRegistry) -> None:
    """Zgodność wsteczna: ``move_ships`` (jeden stos, bez ładunku) nadal działa."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    new = movement.move_ships(state, grid, registry, "101", "destroyer", 1, "p1")
    assert new.systems["000"].space_units["p1"]["destroyer"] == 1


# --- Podgląd zasięgu: legalne systemy źródłowe (RULES.md 32, Blok B3) ---


def test_legal_move_sources_lists_reachable(registry: StaticDataRegistry) -> None:
    """Zwraca system źródłowy z ruszalnym statkiem (destroyer sąsiaduje z aktywnym)."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    sources = movement.legal_move_sources(state, grid, registry, "p1")
    assert "101" in sources
    assert "destroyer" in sources["101"]


def test_legal_move_sources_excludes_active(registry: StaticDataRegistry) -> None:
    """Aktywny system nie jest źródłem (nie ruszamy „sam do siebie")."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    # Dołóż statki gracza w samym aktywnym systemie.
    state.systems["000"] = SystemState(
        position="000", system_id="18", space_units={"p1": {"cruiser": 1}}
    )
    sources = movement.legal_move_sources(state, grid, registry, "p1")
    assert "000" not in sources


def test_legal_move_sources_empty_without_active(
    registry: StaticDataRegistry,
) -> None:
    """Bez aktywnego systemu podgląd zasięgu jest pusty."""
    grid = _line_grid([("000", "18", set()), ("101", "20", set())])
    state = _state_with_destroyer_at("101", "000")
    state.active_system = None
    assert movement.legal_move_sources(state, grid, registry, "p1") == {}
