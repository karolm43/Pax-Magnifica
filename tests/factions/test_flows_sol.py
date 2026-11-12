"""Federation of Sol — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.4).

Walki naziemne Sola: dom Sola ma jedną planetę, więc inwazję prowadzi Letnev na swój dom, a Sol
jest stroną broniącą (Evelyn DeLouis, Claire Gibson działają w każdej walce naziemnej).
"""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _sol_defends(registry: StaticDataRegistry, **leaders: str) -> Flow:
    """Letnev (``me``) najeżdża planetę swojego domu trzymaną przez Sol (``other``)."""
    flow = Flow(registry, "letnev", other="sol")
    if leaders:
        flow.player(lambda p: p["leader_states"].update(leaders), flow.other)
    return flow


@covers("abilities:orbital_drop", "units:sol_mech")
def test_orbital_drop_i_mech_deploy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sol")
    flow.player(lambda p: p.update(trade_goods=3))
    assert flow.playable()["orbital_drop"]["playable"], flow.playable()["orbital_drop"]["reason"]
    planet = flow.planets(flow.home)[0]
    flow.use("ability", "orbital_drop", {"planet": f"{flow.home}|{planet}"})
    assert flow.has_offer("Thunderbolt")  # DEPLOY mecha sam wyskakuje po Orbital Drop
    flow.accept("Thunderbolt", {"planets": [], "trade_goods": 3})
    units = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]
    assert units.get("mech") == 1


@covers("technologies:so2")
def test_spec_ops_ii_wraca_na_poczatku_tury(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sol")

    def card(p: Json) -> None:
        p["technologies"].append("so2")
        p["infantry_ii_on_card"] = 1

    flow.player(card)
    planet = flow.planets(flow.home)[0]
    before = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]["infantry"]
    flow.other_turn()
    flow.pass_and_end(flow.other)  # nowa tura Sola
    after = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]["infantry"]
    assert after == before + 1 or flow.has_offer("Infantry II")


@covers("leaders:solagent")
def test_evelyn_delouis_na_starcie_rundy_naziemnej(registry: StaticDataRegistry) -> None:
    flow = _sol_defends(registry)
    flow.ground_combat()
    assert flow.has_offer("Evelyn", flow.other)


@covers("leaders:solcommander")
def test_claire_gibson_przy_obronie(registry: StaticDataRegistry) -> None:
    flow = _sol_defends(registry, solcommander="unlocked")
    flow.ground_combat()
    assert flow.has_offer("Claire Gibson", flow.other)


@covers("leaders:solhero")
def test_jace_x_jako_akcja(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sol")
    flow.player(lambda p: p["leader_states"].update(solhero="unlocked"))
    assert flow.playable()["solhero"]["playable"], flow.playable()["solhero"]["reason"]
    flow.use("leader", "solhero")


@covers("promissory_notes:ms")
def test_military_support_na_poczatku_tury_sola(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sol")
    note = flow.give_note("ms", flow.other)
    flow.other_turn()
    flow.pass_and_end(flow.other)  # zaczyna się tura Sola
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
