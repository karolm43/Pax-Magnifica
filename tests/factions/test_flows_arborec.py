"""Arborec — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.5)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers

LODOR = "26"  # kafel z jedną planetą (Lodor) - rzadka mapa startowa nie ma planet poza domami


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@covers("abilities:mitosis")
def test_mitosis_decyzja_na_starcie_statusu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "arborec")
    planet = flow.planets(flow.home)[0]
    before = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]
    flow.to_status()
    # Mitosis albo (gdy jest piechota) zamiana na Letani Behemoth - wybór gracza.
    assert flow.has_offer("Mitosis")
    flow.accept("Mitosis", {"mitosis": f"inf|{flow.home}|{planet}"})
    after = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]
    assert after["infantry"] == before["infantry"] + 1


@covers("technologies:bio")
def test_bioplasmosis_na_koniec_statusu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "arborec")
    neighbor = flow.neighbor_of(flow.home)
    flow.set_tile(neighbor, LODOR)
    flow.ground(neighbor, "lodor", flow.me, {"infantry": 1})
    flow.player(lambda p: p["technologies"].append("bio"))
    flow.to_status()
    flow.decline_all()  # Mitosis na starcie statusu
    for offer in flow.offers():
        flow.accept(offer["name"], {"mitosis": f"inf|{flow.home}|{flow.planets(flow.home)[0]}"})
    flow.finish_status()
    assert flow.has_offer("Bioplasmosis"), flow.offers()


@covers("technologies:lw2")
def test_letani_warrior_ii_wraca_na_poczatku_tury(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "arborec")

    def card(p: Json) -> None:
        p["technologies"].append("lw2")
        p["infantry_ii_on_card"] = 1

    flow.player(card)
    planet = flow.planets(flow.home)[0]
    before = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]["infantry"]
    flow.other_turn()
    flow.pass_and_end(flow.other)
    after = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]["infantry"]
    assert after == before + 1 or flow.has_offer("Infantry II")


@covers("leaders:arborecagent")
def test_letani_ospha_akcja_i_decyzja_wlasciciela(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "arborec")
    position, _ = flow.plain_pair()
    flow.space(position, flow.other, {"destroyer": 1})
    assert flow.playable()["arborecagent"]["playable"]
    flow.use("leader", "arborecagent", {"ship": f"{flow.other}|{position}|destroyer"})
    assert flow.has_offer("Letani Ospha", flow.other)


@covers("leaders:arboreccommander")
def test_dirzuga_rophal_po_cudzej_aktywacji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "arborec")
    flow.player(lambda p: p["leader_states"].update(arboreccommander="unlocked"))
    flow.other_turn()
    flow.post("/tactical/activate", {"position": flow.home})
    assert flow.has_offer("Dirzuga")


@covers("leaders:arborechero")
def test_ultrasonic_emitter_jako_akcja(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "arborec")
    flow.player(lambda p: p["leader_states"].update(arborechero="unlocked"))
    assert flow.playable()["arborechero"]["playable"], flow.playable()["arborechero"]["reason"]
    flow.use("leader", "arborechero", {"systems": [flow.home]})
    assert flow.state()["production_grant"] is not None


@covers("units:arborec_flagship")
def test_duha_menaimon_po_aktywacji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "arborec")
    position, _ = flow.plain_pair()
    flow.space(position, flow.me, {"flagship": 1})
    flow.activate(position)
    assert flow.has_offer("Duha Menaimon")


@covers("promissory_notes:stymie")
def test_stymie_po_ruchu_do_systemu_posiadacza(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "arborec")
    note = flow.give_note("stymie", flow.other)
    source, target = flow.plain_pair()
    flow.space(source, flow.me, {"cruiser": 1})
    flow.space(target, flow.other, {"destroyer": 1})
    flow.activate(target)
    flow.move(source, target, {"cruiser": 1})
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]


@covers("breakthroughs:arborecbt")
def test_psychospore_jako_akcja(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "arborec")

    def setup(s: Json) -> None:
        s["players"][flow.me]["breakthrough_unlocked"] = True
        s["systems"][flow.home]["command_tokens"] = [flow.me]

    flow.edit(setup)
    assert flow.playable()["arborecbt"]["playable"], flow.playable()["arborecbt"]["reason"]
