"""Sardakk N'orr — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.1)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@covers("leaders:sardakkagent")
def test_tro_na_koniec_tury_gra_czeka_na_decyzje(registry: StaticDataRegistry) -> None:
    """End turn w trakcie akcji: oferta T'ro wyskakuje, tura czeka, decyzja stawia piechotę."""
    flow = Flow(registry, "sardakk")
    flow.activate(flow.home)
    flow.end_turn()
    assert flow.state()["active_player_id"] == flow.me
    flow.accept("T'ro")
    planet = flow.planets(flow.home)[0]
    before = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]["infantry"]
    decision = flow.offer("place 2 infantry")
    flow.accept(decision["label"], {"planet": planet})
    after = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]["infantry"]
    assert after == before + 2


@covers("leaders:sardakkhero")
def test_bohater_sam_wyskakuje_po_ruchu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sardakk")
    flow.player(lambda p: p["leader_states"].update(sardakkhero="unlocked"))
    source, target = flow.plain_pair()
    flow.space(source, flow.me, {"cruiser": 1})
    flow.activate(target)
    assert f"{flow.me}:sardakkhero" not in flow.available()
    flow.move(source, target, {"cruiser": 1})
    assert f"{flow.me}:sardakkhero" in flow.available()
    flow.use("leader", "sardakkhero")
    assert flow.state()["tactical_step"] == "INVASION"


@covers("leaders:sardakkcommander")
def test_ghom_sekkus_sam_wyskakuje_przy_ladowaniu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sardakk")
    flow.player(lambda p: p["leader_states"].update(sardakkcommander="unlocked"))
    target = flow.invade_own_home()
    assert flow.state()["invasion"]["phase"] == "COMMIT"
    assert f"{flow.me}:sardakkcommander" in flow.available()
    source = flow.planets(flow.home)[1]
    flow.use("leader", "sardakkcommander", {f"src:{flow.home}:{source}": f"infantry>{target}"})
    assert flow.state()["invasion"]["committed"]


@covers("promissory_notes:tekklar")
def test_tekklar_legion_na_poczatku_walki_naziemnej(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sardakk")
    note = flow.give_note("tekklar", flow.other)
    flow.ground_combat()
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note)


@covers("technologies:exo2")
def test_exotrireme_oferta_po_rundzie(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sardakk")
    flow.player(lambda p: p["technologies"].append("exo2"))
    source, _ = flow.plain_pair()
    flow.space(source, flow.me, {"dreadnought": 3})
    flow.space(source, flow.other, {"dreadnought": 3})
    flow.activate(source)
    flow.to_step("SPACE_COMBAT")
    flow.start_space_combat()
    flow.fight(stop=lambda: flow.has_offer("Exotrireme"))
    assert flow.has_offer("Exotrireme")


@covers("breakthroughs:sardakkbt")
def test_norr_supremacy_po_wygranej(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sardakk")
    flow.player(lambda p: p.update(breakthrough_unlocked=True))
    source, _ = flow.plain_pair()
    flow.space(source, flow.me, {"dreadnought": 3})
    flow.space(source, flow.other, {"destroyer": 1})
    flow.activate(source)
    flow.to_step("SPACE_COMBAT")
    flow.start_space_combat()
    flow.fight(stop=lambda: flow.has_offer("Supremacy"))
    assert flow.has_offer("Supremacy")
