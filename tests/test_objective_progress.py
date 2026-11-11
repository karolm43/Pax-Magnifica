"""Testy mechanizmu sprawdzania celów (``core/objective_progress`` + ``objective_payment``)."""

from __future__ import annotations

import pytest

from src.core import objective_payment, objective_progress
from src.core.components import ComponentCategory
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import Hex, HexGrid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(**systems: SystemState) -> GameState:
    return GameState(
        phase=Phase.STATUS,
        players={
            "p1": PlayerState(player_id="p1", color="red"),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems=dict(systems),
    )


def _progress(
    state: GameState, registry: StaticDataRegistry, objective: str, grid: HexGrid | None = None
) -> int | None:
    return objective_progress.progress(state, registry, grid or HexGrid(), "p1", objective)


# ------------------------------------------------------------------ pokrycie wszystkich kart


def test_every_status_objective_is_covered(registry: StaticDataRegistry) -> None:
    """Każdy cel fazy statusu z katalogu ma próg i ewaluator albo jawny wpis 'ręczny'."""
    missing: list[str] = []
    for category in (ComponentCategory.PUBLIC_OBJECTIVE, ComponentCategory.SECRET_OBJECTIVE):
        for objective_id, card in registry.catalog.all(category).items():
            if getattr(card, "phase", None) != "Status":
                continue
            has_rule = objective_id in objective_progress.MANUAL_OBJECTIVES or (
                objective_id in objective_progress._PROGRESS
            )
            has_goal = objective_id in objective_progress.THRESHOLDS or objective_id == "fc"
            if not (has_rule and has_goal):
                missing.append(objective_id)
    assert missing == []


# ------------------------------------------------------------------ ewaluatory


def test_spend_objectives_count_trade_goods_and_ready_planets(
    registry: StaticDataRegistry,
) -> None:
    state = _state(
        a=SystemState(position="a", system_id="x", planet_owners={"abyz": "p1", "fria": "p1"})
    )
    state.players["p1"].trade_goods = 2
    planets = registry.planets
    expected_res = planets["abyz"].resources + planets["fria"].resources
    assert _progress(state, registry, "monument") == expected_res + 2
    state.players["p1"].exhausted_planets = ["abyz"]  # wyczerpana nie liczy się do wydania
    assert _progress(state, registry, "monument") == planets["fria"].resources + 2
    assert _progress(state, registry, "trade_routes") == 2
    assert _progress(state, registry, "lead") == 5  # 3 taktyczne + 2 strategiczne


def test_trait_and_structure_counting(registry: StaticDataRegistry) -> None:
    cultural = [
        pid for pid, p in registry.planets.items() if p.planet_type == "CULTURAL"
    ][:4]
    state = _state(
        a=SystemState(
            position="a",
            system_id="x",
            planet_owners=dict.fromkeys(cultural, "p1"),
            planet_units={
                cultural[0]: {"p1": {"spacedock": 1}},
                cultural[1]: {"p1": {"pds": 2}},
            },
        )
    )
    assert _progress(state, registry, "corner") == 4
    assert _progress(state, registry, "faa") == 4
    assert _progress(state, registry, "build_defenses") == 3  # dok + 2 PDS


def test_fleet_and_edge_progress(registry: StaticDataRegistry) -> None:
    grid = HexGrid()
    grid.place_system("000", "18", hex_override=Hex(0, 0, 0))
    for index, neighbour in enumerate(Hex(0, 0, 0).neighbors()):
        grid.place_system(f"1{index:02d}", "19", hex_override=neighbour)
    grid.build_edges()
    state = _state(
        **{
            "000": SystemState(position="000", system_id="18",
                               space_units={"p1": {"cruiser": 3, "fighter": 5}}),
            "100": SystemState(position="100", system_id="19",
                               space_units={"p1": {"carrier": 1}}),
        }
    )
    assert _progress(state, registry, "raise_fleet", grid) == 3  # myśliwce się nie liczą
    assert not grid.is_edge("000")
    assert grid.is_edge("100")
    assert _progress(state, registry, "outer_rim", grid) == 1
    assert _progress(state, registry, "ctr", grid) == 2


def test_every_catalog_objective_is_checked_automatically(registry: StaticDataRegistry) -> None:
    """Żaden cel (publiczny/tajny, każda faza) nie wymaga ręcznego potwierdzenia."""
    from src.core.objective_events import EVENT_OBJECTIVES

    unchecked: list[str] = []
    for category in (ComponentCategory.PUBLIC_OBJECTIVE, ComponentCategory.SECRET_OBJECTIVE):
        for objective_id in registry.catalog.all(category):
            if objective_id not in objective_progress._PROGRESS and (
                objective_id not in EVENT_OBJECTIVES
            ):
                unchecked.append(objective_id)
    assert unchecked == []
    assert objective_progress.MANUAL_OBJECTIVES == frozenset()


def test_destroy_heretical_works_and_dictate_policy_are_computed(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    assert _progress(state, registry, "dhw") == 0 and _progress(state, registry, "dp") == 0
    state.players["p1"].relic_fragments = ["crf1", "hrf1"]
    state.decks.agenda_laws = {"a": "for", "b": "for", "c": "for"}
    value, goal, ok = objective_progress.evaluate(state, registry, HexGrid(), "p1", "dhw")
    assert (value, goal, ok) == (2, 2, True)
    assert objective_progress.evaluate(state, registry, HexGrid(), "p1", "dp")[2]


def test_destroy_heretical_works_purges_two_fragments(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].relic_fragments = ["crf1", "hrf1", "irf1"]
    paid = objective_payment.pay_for_objective(state, registry, HexGrid(), "p1", "dhw")
    assert paid.players["p1"].relic_fragments == ["irf1"]
    assert paid.decks.purged[-2:] == ["crf1", "hrf1"]


def test_evaluate_blocks_unmet_requirement(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].trade_goods = 4
    assert objective_progress.evaluate(state, registry, HexGrid(), "p1", "trade_routes") == (
        4, 5, False,
    )
    state.players["p1"].trade_goods = 5
    assert objective_progress.evaluate(state, registry, HexGrid(), "p1", "trade_routes")[2]


# ------------------------------------------------------------------ płatności


def test_mixed_spend_plan_uses_planets_then_trade_goods(registry: StaticDataRegistry) -> None:
    res_planet = next(p.id for p in registry.planets.values() if p.resources >= 3 > p.influence)
    inf_planet = next(p.id for p in registry.planets.values() if p.influence >= 3 > p.resources)
    plan = objective_progress.mixed_spend_plan([res_planet, inf_planet], registry, 3, 3)
    assert plan is not None
    res_list, inf_list, tg = plan
    assert res_list == [res_planet] and inf_list == [inf_planet] and tg == 3
    # Bez planet: 3 TG + 3 res z TG + 3 inf z TG = 9 TG.
    assert objective_progress.mixed_spend_plan([], registry, 8, 3) is None
    assert objective_progress.mixed_spend_plan([], registry, 9, 3) == ([], [], 9)


def test_pay_for_resource_objective_exhausts_planets(registry: StaticDataRegistry) -> None:
    big = [pid for pid, p in registry.planets.items() if p.resources >= 2][:5]
    state = _state(a=SystemState(position="a", system_id="x",
                                 planet_owners=dict.fromkeys(big, "p1")))
    state.players["p1"].trade_goods = 8
    paid = objective_payment.pay_for_objective(state, registry, HexGrid(), "p1", "monument")
    exhausted = paid.players["p1"].exhausted_planets
    spent = sum(registry.planets[p].resources for p in exhausted)
    assert exhausted and spent + (8 - paid.players["p1"].trade_goods) >= 8
