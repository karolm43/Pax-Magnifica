"""Testy „Other points" i toru punktów w web-data (``api/web_points``)."""

from __future__ import annotations

from typing import Any

import pytest

from src.api import web_points
from src.core import objectives
from src.core.game_state import GameState, ObjectivesState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.map_string import MECATOL_SYSTEM_ID
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards.imperial import INITIATIVE as IMPERIAL


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(ships: int = 3) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        players={
            "p1": PlayerState(player_id="p1", color="red", strategy_cards=[IMPERIAL]),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems={
            "000": SystemState(position="000", system_id=MECATOL_SYSTEM_ID,
                               planet_owners={"mr": "p1"},
                               space_units={"p1": {"cruiser": ships}}),
        },
        objectives=ObjectivesState(revealed=["raise_fleet"], custom_points={"custodians": 1}),
    )


def _entries(state: GameState, registry: StaticDataRegistry, pid: str) -> list[dict[str, Any]]:
    keys = {p: p for p in state.players}
    entries: list[dict[str, Any]] = web_points.build_score_breakdowns(
        state, registry, HexGrid(), keys
    )[pid]["entries"]
    return entries


def test_award_points_records_source_and_nets_out(registry: StaticDataRegistry) -> None:
    del registry
    state = _state()
    objectives.award_points(state, "p1", 1, source="relics:shard")
    objectives.award_points(state, "p1", -1, source="relics:shard")
    objectives.award_points(state, "p2", 1, source="relics:shard")
    assert state.objectives.point_sources == {"relics:shard": {"p2": 1}}
    assert state.players["p2"].victory_points == 1


def test_other_points_lists_every_source_with_full_names(registry: StaticDataRegistry) -> None:
    state = _state()
    objectives.award_points(state, "p1", 1, source="relics:shard")
    objectives.award_points(state, "p2", 1, source="agendas:seed_empire")
    state.players["p2"].victory_points = 2
    objectives.award_points(state, "p2", -1, source="agendas:mutiny")
    state.players["p2"].relics = ["bookoflatvinia"]
    rows = {
        row["key"]: row
        for row in web_points.other_point_rows(state, registry, {"p1": "p1", "p2": "p2"})
    }
    assert rows["custodians"]["name"] == "Custodians Token"  # zawsze na stole
    assert objectives.SOURCE_IMPERIAL in rows
    assert rows["relics:bookoflatvinia"]["name"] == "Book of Latvinia"  # trzymany relikt z VP
    shard = rows["relics:shard"]
    assert (shard["name"], shard["losable"], shard["scoredFactions"]) == (
        "Shard of the Throne", True, ["p1"],
    )
    assert rows["agendas:seed_empire"]["name"] == "Seed of an Empire"
    assert not rows["agendas:seed_empire"]["losable"]
    mutiny = rows["agendas:mutiny"]
    assert mutiny["factionPoints"] == {"p2": -1} and mutiny["scoredFactions"] == []


def test_breakdown_states_and_losable_points(registry: StaticDataRegistry) -> None:
    state = _state(ships=3)
    objectives.award_points(state, "p1", 1, source="relics:shard")
    state.players["p1"].victory_points += 1  # edycja God-Mode bez źródła
    entries = _entries(state, registry, "p1")
    by_type = {(e["type"], e["state"]): e for e in entries}
    shard = by_type[("SHARD", "SCORED")]
    assert shard["losable"] and shard["description"] == "Shard of the Throne"
    assert ("OTHER", "SCORED") in by_type  # tor sumuje się do wyniku gracza
    scored = sum(e["pointValue"] for e in entries if e["state"] == "SCORED")
    assert scored == state.players["p1"].victory_points
    # Imperial w ręce + Mecatol Rex => punkt gotowy teraz; Custodians wciąż do wzięcia.
    assert ("IMPERIAL", "QUALIFIES") in by_type
    assert ("CUSTODIAN", "POTENTIAL") in by_type
    raise_fleet = by_type[("PO_1", "POTENTIAL")]
    assert (raise_fleet["currentProgress"], raise_fleet["totalProgress"]) == (3, 5)
    states = [e["state"] for e in entries]
    assert states == sorted(states, key=["SCORED", "QUALIFIES", "POTENTIAL"].index)


def test_breakdown_marks_ready_public_objective(registry: StaticDataRegistry) -> None:
    state = _state(ships=5)
    entries = _entries(state, registry, "p1")
    ready = [e for e in entries if e["state"] == "QUALIFIES" and e["type"] == "PO_1"]
    assert [e["objectiveKey"] for e in ready] == ["raise_fleet"]
    # Bez Imperial w ręce nie ma żetonu Imperial.
    assert not any(e["type"] == "IMPERIAL" for e in _entries(state, registry, "p2"))
