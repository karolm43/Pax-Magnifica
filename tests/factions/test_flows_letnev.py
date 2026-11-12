"""Barony of Letnev — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.2)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@covers("abilities:munitions")
def test_munitions_oferta_i_przerzut_sam_wyskakuje(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "letnev")
    flow.player(lambda p: p.update(trade_goods=4))
    flow.space_combat({"dreadnought": 2}, {"cruiser": 2})
    assert flow.has_offer("Munitions")
    flow.accept("Munitions")
    flow.decline_all()
    flow.fight(stop=lambda: f"{flow.me}:munitions" in flow.available())
    assert f"{flow.me}:munitions" in flow.available()


@covers("leaders:letnevagent")
def test_viscount_unlenn_na_starcie_rundy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "letnev")
    flow.space_combat({"dreadnought": 2}, {"cruiser": 2})
    assert flow.has_offer("Viscount")
    flow.accept("Viscount", {"ship": f"{flow.me}|dreadnought"})


@covers("leaders:letnevcommander")
def test_rear_admiral_farran_po_sustain(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "letnev")
    flow.player(lambda p: p["leader_states"].update(letnevcommander="unlocked"))
    flow.space_combat({"dreadnought": 3}, {"dreadnought": 3})
    flow.fight(stop=lambda: flow.has_offer("Farran"))
    assert flow.has_offer("Farran")


@covers("leaders:letnevhero")
def test_darktalon_treilla_jako_akcja(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "letnev")
    flow.player(lambda p: p["leader_states"].update(letnevhero="unlocked"))
    assert flow.playable()["letnevhero"]["playable"]
    flow.use("leader", "letnevhero")


@covers("promissory_notes:war_funding")
def test_war_funding_po_rzutach(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "letnev")
    note = flow.give_note("war_funding", flow.other)
    flow.space_combat({"dreadnought": 2}, {"cruiser": 3})
    flow.decline_all()
    flow.fight(stop=lambda: flow.battle().get("step") == "ASSIGN")
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]


@covers("units:letnev_mech")
def test_dunlain_reaper_na_starcie_rundy_naziemnej(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "letnev")
    flow.player(lambda p: p.update(trade_goods=3))
    flow.ground_combat()
    assert flow.has_offer("Dunlain")


@covers("breakthroughs:letnevbt")
def test_gravleash_decyzja_na_starcie_rundy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "letnev")

    def unlock(p: Json) -> None:
        p["breakthrough_unlocked"] = True

    flow.player(unlock)
    flow.space_combat({"dreadnought": 1, "cruiser": 1}, {"cruiser": 2})
    assert flow.has_offer("Gravleash")
