"""The Nekro Virus — scenarios through the real API (availability, RULES.md 62.24)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _me(flow: Flow, pid: str | None = None) -> Json:
    return flow.state()["players"][pid or flow.me]  # type: ignore[no-any-return]


def test_nekro_zaczyna_z_asymilatorami(registry: StaticDataRegistry) -> None:
    """⚠️ ASSUMPTION RULES.md 62.24: both Valefar Assimilators from the start."""
    flow = Flow(registry, "nekro")
    assert {"vax", "vay"} <= set(_me(flow)["technologies"])


@covers("abilities:technological_singularity", "leaders:nekrocommander")
def test_osobliwosc_w_walce_i_acidos(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nekro")
    flow.player(lambda p: p["leader_states"].__setitem__("nekrocommander", "unlocked"))
    rival_techs = set(_me(flow, flow.other)["technologies"])
    flow.space_combat({"dreadnought": 3}, {"cruiser": 2})
    flow.fight(stop=lambda: flow.has_offer("Technological Singularity"))
    offer = flow.offer("Technological Singularity")
    picks = [o["value"] for o in offer["inputs"][0]["options"]]
    gained = next(t for t in picks if t in rival_techs)
    flow.accept("Technological Singularity", {"technology": gained})
    assert gained in _me(flow)["technologies"]
    assert flow.has_offer("Nekro Acidos")  # "After you gain a technology"
    hand = len(_me(flow)["private"]["action_cards"])
    flow.accept("Nekro Acidos")
    assert len(_me(flow)["private"]["action_cards"]) == hand + 1


@covers("units:nekro_flagship")
def test_alastor_piechota_walczy_jak_statki(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nekro")
    flow.space_combat({"flagship": 1, "infantry": 2}, {"destroyer": 2})
    offer = flow.offer("The Alastor")
    assert {f["key"] for f in offer["inputs"]} == {"infantry"}
    flow.accept("The Alastor", {"infantry": 2})
    combat = flow.state()["active_combat"]
    assert combat["ground_as_ships"][flow.me] == {"infantry": 2}
    flow.fight()
    assert flow.battle().get("step") in (None, "DONE")


@covers("abilities:galactic_threat")
def test_galactic_threat_przepowiednia_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nekro")
    flow.post("/god-mode/patch", {"custodians_removed": True})
    flow.to_status()
    flow.finish_status()
    service = flow.client.app.state.ctx.service  # type: ignore[attr-defined]
    state = service.current_state().clone()
    assert state.phase.value == "AGENDA"
    state.decks.agenda_deck = ["regulations"]
    state.decks.agenda_deck_seeded = True
    service.replace_state(state, label="test")
    flow.post("/agenda/reveal", {"player_id": state.speaker_id})
    agenda = flow.state()["agenda"]
    assert flow.me in agenda["blocked"]  # "You cannot vote on agendas"
    offer = flow.offer("Galactic Threat")
    outcome = offer["inputs"][0]["options"][0]["value"]
    flow.accept("Galactic Threat", {"outcome": outcome})
    assert not flow.has_offer("Galactic Threat")
    resp = flow.post("/agenda/vote", {"player_id": flow.me, "outcome": outcome, "planets": []},
                     ok=False)
    assert resp.status_code == 422


@covers("leaders:nekroagent")
def test_malleon_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nekro")
    assert flow.playable()["nekroagent"]["playable"]
    tg = _me(flow, flow.other)["trade_goods"]
    flow.use("leader", "nekroagent", {"target": flow.other})
    decision = flow.offer("Nekro Malleon", flow.other)
    assert "auto" not in decision["inputs"][0]
    pool = next(o["value"] for o in decision["inputs"][0]["options"]
                if str(o["value"]).startswith("pool|"))
    flow.accept("Nekro Malleon", {"choice": pool}, pid=flow.other)
    assert _me(flow, flow.other)["trade_goods"] == tg + 2
    assert _me(flow)["leader_states"]["nekroagent"] == "exhausted"


WELLON_TILE, WELLON = "19", "wellon"  # Wellon: CYBERNETIC specialty


def _specialty_system(flow: Flow) -> tuple[str, str]:
    """A plain system turned into Wellon (God-Mode tile swap) - (position, planet)."""
    position, _ = flow.plain_pair()

    def put(s: Json) -> None:
        system = s["systems"][position]
        system["system_id"] = WELLON_TILE
        system["planet_owners"] = {}
        system["planet_units"] = {}

    flow.edit(put)
    return position, WELLON


@covers("leaders:nekrohero")
def test_flayesh_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nekro")
    position, planet = _specialty_system(flow)
    flow.space(position, flow.me, {"cruiser": 1})
    flow.ground(position, planet, flow.other, {"infantry": 1})
    flow.player(lambda p: p["leader_states"].__setitem__("nekrohero", "unlocked"))
    assert flow.playable()["nekrohero"]["playable"]
    form = flow.client.get("/faction-component/leader/nekrohero/form",
                           params={"player_id": flow.me}).json()
    tech = form["inputs"][1]["options"][0]["value"]
    tg = _me(flow)["trade_goods"]
    flow.use("leader", "nekrohero", {"planet": planet, "technology": tech})
    me = _me(flow)
    stats = registry.planets[planet]
    assert me["trade_goods"] == tg + stats.resources + stats.influence
    assert me["leader_states"]["nekrohero"] == "purged"
    units = flow.state()["systems"][position]["planet_units"].get(planet, {})
    assert flow.other not in units or not units[flow.other]


@covers("promissory_notes:antivirus")
def test_antivirus_na_poczatku_walki(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nekro")
    note = flow.give_note("antivirus", flow.other)
    flow.space_combat({"dreadnought": 3}, {"cruiser": 2})
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note)
    assert note in _me(flow, flow.other)["promissory_notes_in_play"]
    flow.fight(stop=lambda: flow.has_offer("Technological Singularity"))
    assert not flow.has_offer("Technological Singularity")
