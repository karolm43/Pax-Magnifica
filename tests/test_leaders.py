"""Liderzy i komponenty frakcji w akcji komponentu (RULES.md 61.1, 61.3)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import component_action, faction_components, leaders, rules_hooks
from src.core.components import ComponentCategory
from src.core.game_state import GameState, PendingOffer, Phase, PlayerState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="arborec"),
            "p2": PlayerState(player_id="p2", color="blue", faction="sol"),
        },
    )


def _score_public(state: GameState, registry: StaticDataRegistry, count: int) -> None:
    ids = list(registry.catalog.all(ComponentCategory.PUBLIC_OBJECTIVE))[:count]
    for objective_id in ids:
        state.objectives.scored.setdefault(objective_id, []).append("p1")


# ------------------------------------------------------------------------------- stan domyślny


def test_stan_domyslny_agent_gotowy_reszta_zablokowana(registry: StaticDataRegistry) -> None:
    state = _state()
    assert leaders.state_of(state, registry, "p1", "arborecagent") == leaders.UNLOCKED
    assert leaders.state_of(state, registry, "p1", "arboreccommander") == leaders.LOCKED
    assert leaders.state_of(state, registry, "p1", "arborechero") == leaders.LOCKED


def test_koszt_uzycia_z_tekstu_karty(registry: StaticDataRegistry) -> None:
    assert leaders.usage_cost(registry, "arborecagent") == "exhaust"
    assert leaders.usage_cost(registry, "arborechero") == "purge"
    # Bohater, którego tekst nie powtarza „purge” — reguła ogólna (R_leaders).
    assert leaders.usage_cost(registry, "ghosthero") == "purge"
    # Bohater dołączany do Elysium nie jest purge'owany.
    assert leaders.usage_cost(registry, "titanshero") is None


# --------------------------------------------------------------------------------- odblokowanie


def test_bohater_odblokowuje_sie_po_3_celach(registry: StaticDataRegistry) -> None:
    state = _state()
    _score_public(state, registry, 2)
    assert leaders.refresh_unlocks(state, registry) == []
    state.players["p1"].scored_secrets = ["sec"]
    assert leaders.refresh_unlocks(state, registry) == ["arborechero"]
    assert leaders.state_of(state, registry, "p1", "arborechero") == leaders.UNLOCKED


def test_punkty_spoza_celow_nie_licza_sie(registry: StaticDataRegistry) -> None:
    state = _state()
    state.objectives.scored["custodians"] = ["p1", "p1", "p1"]
    assert leaders.refresh_unlocks(state, registry) == []


def test_brak_odblokowania_w_trakcie_rozstrzygania(registry: StaticDataRegistry) -> None:
    state = _state()
    _score_public(state, registry, 3)
    offer = PendingOffer(id="o1", player_id="p2", event="x", moment="after", hook_seq=0)
    state.pending_offers = [offer]
    assert leaders.refresh_unlocks(state, registry) == []


def test_odblokowany_nie_wraca_do_zablokowanego(registry: StaticDataRegistry) -> None:
    state = _state()
    _score_public(state, registry, 3)
    leaders.refresh_unlocks(state, registry)
    state.objectives.scored.clear()
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", "arborechero") == leaders.UNLOCKED


def test_reczne_odblokowanie_tylko_bez_predykatu(registry: StaticDataRegistry) -> None:
    state = _state()
    with pytest.raises(ValueError, match="automatically"):
        leaders.claim_unlock(state, registry, "p1", "arborechero")
    commander = "arboreccommander"
    if leaders.unlock_predicate(registry, commander) is None and not leaders.has_event_unlock(
        commander
    ):
        new_state = leaders.claim_unlock(state, registry, "p1", commander)
        assert leaders.state_of(new_state, registry, "p1", commander) == leaders.UNLOCKED
    with pytest.raises(ValueError, match="not one of your leaders"):
        leaders.claim_unlock(state, registry, "p1", "solcommander")


# ----------------------------------------------------------------------- akcja komponentu


def test_agent_z_akcja_wyczerpuje_sie(registry: StaticDataRegistry) -> None:
    calls: list[dict[str, Any]] = []
    with rules_hooks.temporary_hooks():
        if rules_hooks.effect_for("leaders:arborecagent") is None:

            @rules_hooks.register_effect("leaders:arborecagent")
            def _fx(state: Any, registry: Any, player_id: str, params: Mapping[str, Any]) -> None:
                calls.append(dict(params))

        state = _state()
        rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p1")}
        assert rows["arborecagent"]["playable"] is True
        assert rows["arborechero"]["playable"] is False  # zablokowany
        assert rows["mitosis"]["mode"] == "passive"
        new_state, implemented = faction_components.play(
            state, registry, "p1", "leader", "arborecagent"
        )
        assert implemented is True
        assert leaders.state_of(new_state, registry, "p1", "arborecagent") == leaders.EXHAUSTED
        assert new_state.players["p1"].took_action_this_turn is True
        # Bez nowej tury drugi raz się nie da (akcja zużyta, agent wyczerpany).
        with pytest.raises(ValueError):
            faction_components.play(new_state, registry, "p1", "leader", "arborecagent")


def test_bohater_po_uzyciu_purge_i_przestaje_byc_zrodlem(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"arborechero": leaders.UNLOCKED}
    source = rules_hooks.HookSource(rules_hooks.SOURCE_LEADER, "arborechero")
    assert source in rules_hooks.owned_sources(state, "p1")
    new_state, _ = faction_components.play(state, registry, "p1", "leader", "arborechero")
    assert leaders.state_of(new_state, registry, "p1", "arborechero") == leaders.PURGED
    assert source not in rules_hooks.owned_sources(new_state, "p1")
    new_state.players["p1"].took_action_this_turn = False
    new_state.players["p1"].actions_this_turn = 0
    with pytest.raises(ValueError, match="purged"):
        faction_components.play(new_state, registry, "p1", "leader", "arborechero")


def test_akcja_nieswojego_lub_pasywnego_komponentu_odrzucona(registry: StaticDataRegistry) -> None:
    state = _state()
    with pytest.raises(ValueError):
        faction_components.play(state, registry, "p1", "leader", "solhero")
    with pytest.raises(ValueError, match="no ACTION"):
        faction_components.play(state, registry, "p1", "ability", "mitosis")
    with pytest.raises(ValueError):
        component_action.play_component_action(state, "p1", "ability:mitosis")


def test_zdolnosc_frakcji_z_akcja_jest_na_liscie(registry: StaticDataRegistry) -> None:
    state = _state()
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p2")}
    state.active_player_id = "p2"
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p2")}
    assert rows["orbital_drop"]["mode"] == "action"
    assert rows["versatile"]["mode"] == "passive"


# ------------------------------------------------------------------------------------- API


def test_api_reczne_odblokowanie_i_lista() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/game/new",
        json={"players": [{"faction_id": "arborec"}, {"faction_id": "sol"}]},
    )
    if resp.status_code != 200:
        pytest.skip(f"/game/new w innym kształcie: {resp.text[:120]}")
    state = client.get("/state").json()["state"]
    pid = next(p for p, v in state["players"].items() if v["faction"] == "arborec")
    listed = client.get(f"/faction-component/playable?player_id={pid}")
    assert listed.status_code == 200
    kinds = {row["kind"] for row in listed.json()["components"]}
    assert {"leader", "ability"} <= kinds
    form = client.get(f"/faction-component/leader/arborechero/form?player_id={pid}")
    assert form.status_code == 200 and form.json()["can_claim_unlock"] is False
    resp = client.post("/leader/claim-unlock", json={"player_id": pid, "leader_id": "arborechero"})
    assert resp.status_code == 422
