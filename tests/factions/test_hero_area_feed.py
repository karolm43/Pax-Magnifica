"""Miejsce działania bohatera w feedzie Activity (fakty ``area``, RULES.md 64.4) przez API.

Animacja bohatera na planszy (``HERO_BOARD_FX``) celuje w systemy z faktów ``area``: Sol w systemy,
z których zniknęły jego żetony; Saar w system, gdzie rywal stracił myśliwce; L1Z1X w system
docelowy pancerników.
"""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _areas(flow: Flow) -> set[tuple[str, str, str]]:
    entries = flow.client.get("/history/activity").json()["entries"]
    facts = entries[-1]["activity"]["facts"]
    return {(f["player_id"], f["value"], f["detail"]) for f in facts if f["type"] == "area"}


def test_sol_zetony_wracaja_z_planszy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sol")
    position, _ = flow.plain_pair()

    def token(s: Json) -> None:
        s["systems"][position]["command_tokens"] = [flow.me]

    flow.edit(token)
    flow.player(lambda p: p["leader_states"].update(solhero="unlocked"))
    flow.use("leader", "solhero")
    assert (flow.me, position, "token_removed") in _areas(flow)


def test_saar_system_strat_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "saar")
    flow.player(lambda p: p["leader_states"].update(saarhero="unlocked"))
    target = sorted(flow.grid().neighbors(flow.home))[0]
    flow.space(target, flow.other, {"fighter": 2, "destroyer": 1})
    flow.use("leader", "saarhero", {"position": target})
    assert (flow.other, target, "loss") in _areas(flow)


def test_l1z1x_system_docelowy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "l1z1x")
    flow.player(lambda p: p["leader_states"].update(l1z1xhero="unlocked"))
    position, _ = flow.plain_pair()
    flow.space(flow.home, flow.me, {"dreadnought": 2})
    flow.use("leader", "l1z1xhero", {"moves": [
        f"{flow.home}|dreadnought|0>{position}", f"{flow.home}|dreadnought|1>{position}",
    ]})
    areas = _areas(flow)
    assert (flow.me, position, "gain") in areas
    assert (flow.me, flow.home, "loss") in areas


def test_mahact_benediction_zrodlo_i_walka(registry: StaticDataRegistry) -> None:
    """Benediction names its origin and its combat system (RULES.md 62.23) - the board FX draws
    the chain between them."""
    flow = Flow(registry, "mahact")
    source, dest = flow.plain_pair()
    flow.space(source, flow.me, {"cruiser": 2})
    flow.space(dest, flow.other, {"destroyer": 1})
    flow.player(lambda p: p["leader_states"].update(mahacthero="unlocked"))
    flow.use("leader", "mahacthero", {"source": source, "destination": dest})
    areas = _areas(flow)
    assert (flow.me, source, "benediction_origin") in areas
    assert (flow.me, dest, "benediction") in areas
