"""The Winnu — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.7)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers
from tests.rulings import ruling

_MECATOL_TILE = "18"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _take_mecatol(flow: Flow, ground: dict[str, int]) -> str:
    """Mecatol Rex na zwykłej pozycji, Winnu ląduje na pustej planecie; koniec akcji taktycznej."""
    position, _ = flow.plain_pair()
    flow.set_tile(position, _MECATOL_TILE)
    flow.post("/god-mode/patch", {"custodians_removed": True})
    cargo = {"carrier": 1, **ground}
    flow.space(position, flow.me, cargo)
    flow.activate(position)
    flow.to_step("INVASION")
    if flow.state()["invasion"] is None:
        flow.post("/tactical/invasion/begin")
    planet = flow.planets(position)[0]
    flow.post("/tactical/invasion/commit", {"commits": [
        {"planet": planet, "baseType": bt, "count": n} for bt, n in ground.items()
    ]})
    for _ in range(6):
        if flow.state()["invasion"] is None:
            break
        flow.post("/tactical/invasion/next", ok=False)
    assert flow.state()["systems"][position]["planet_owners"].get(planet) == flow.me
    flow.post("/tactical/end")
    return planet


@covers("abilities:reclamation", "units:winnu_mech")
def test_reclamation_i_reclaimer_po_zdobyciu_mecatol(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "winnu")
    _take_mecatol(flow, {"infantry": 1, "mech": 1})
    assert flow.has_offer("Reclamation")
    assert flow.has_offer("Reclaimer")
    flow.accept("Reclamation", {"place": "pds+spacedock"})


@covers("leaders:winnuagent")
def test_berekar_berekon_przy_produkcji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "winnu")
    flow.activate(flow.home)
    flow.to_step("PRODUCTION")
    assert f"{flow.me}:winnuagent" in flow.available()
    flow.use("leader", "winnuagent")


@covers("leaders:winnuhero")
@ruling("leaders:winnuhero#1", "leaders:winnuhero#4")
def test_mathis_mathinus_primary_i_secondary_innych(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "winnu")
    flow.player(lambda p: p["leader_states"].update(winnuhero="unlocked"))
    assert flow.playable()["winnuhero"]["playable"], flow.playable()["winnuhero"]["reason"]
    flow.use("leader", "winnuhero", {"card": "5", "players": [flow.other]})
    state = flow.state()
    assert state["players"][flow.me]["leader_states"]["winnuhero"] == "purged"
    if state["pending_strategy"] is not None:
        flow.post("/strategy/primary-step", {
            "player_id": flow.me, "payload": {"players": []},
        })
        state = flow.state()
    window = state["pending_window"]
    assert window is not None and window["queue"] == [flow.other]


@covers("promissory_notes:acq")
@ruling("promissory_notes:acq#2")
def test_acquiescence_w_oknie_secondary_winnu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "winnu")
    note = flow.give_note("acq", flow.other)

    def trade(p: Json) -> None:
        p["strategy_cards"] = [5]

    flow.player(trade)
    flow.post("/strategy/play", {"player_id": flow.me, "initiative": 5})
    if flow.state()["pending_strategy"] is not None:
        flow.post("/strategy/primary-step", {
            "player_id": flow.me, "payload": {"players": []},
        })
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note)
    window = flow.state()["pending_window"]
    assert flow.other in window["context"]["no_cost"].split(",")
    assert f"{flow.other}=promissory_notes:acq" in window["context"]["no_cost_why"]
    players = flow.state()["players"]
    assert "acq" in players[flow.me]["private"]["promissory_notes"]  # wraca do Winnu
    assert "acq" not in players[flow.other]["private"]["promissory_notes"]
