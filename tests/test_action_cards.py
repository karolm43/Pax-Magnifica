"""Testy zagrywania kart akcji z oknem ACTION (RULES.md 53)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import action_cards, exploration, rules_hooks
from src.core.components import ComponentCategory
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _planets_with(registry: StaticDataRegistry, trait: str, n: int) -> list[str]:
    found = [
        pid
        for pid in sorted(registry.planets)
        if exploration.planet_traits(registry, pid) == [trait]
    ]
    assert len(found) >= n
    return found[:n]


def _state(
    registry: StaticDataRegistry, hand: list[str], planets: list[str], **player: object
) -> GameState:
    system = SystemState(position="000", system_id="18", planet_owners={p: "p1" for p in planets})
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", color="red", **player),  # type: ignore[arg-type]
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems={"000": system},
    )
    state.players["p1"].private.action_cards = list(hand)
    return state


def test_industrial_initiative_daje_tg_za_planety_przemyslowe(registry: StaticDataRegistry) -> None:
    industrial = _planets_with(registry, "industrial", 2)
    cultural = _planets_with(registry, "cultural", 1)
    state = _state(registry, ["industrial_initiative"], industrial + cultural, trade_goods=1)
    new, implemented = action_cards.play_action_card(
        state, registry, "p1", "industrial_initiative"
    )
    assert implemented
    assert new.players["p1"].trade_goods == 3  # 1 + 2 planety przemysłowe
    assert new.players["p1"].took_action_this_turn
    assert new.players["p1"].private.action_cards == []
    assert new.decks.action_card_discard == ["industrial_initiative"]
    assert state.players["p1"].trade_goods == 1  # wejście nietknięte (czysta funkcja)


def test_economic_initiative_odswieza_tylko_kulturowe(registry: StaticDataRegistry) -> None:
    cultural = _planets_with(registry, "cultural", 2)
    industrial = _planets_with(registry, "industrial", 1)
    state = _state(
        registry, ["economic_initiative"], cultural + industrial,
        exhausted_planets=cultural + industrial,
    )
    new, _ = action_cards.play_action_card(state, registry, "p1", "economic_initiative")
    assert new.players["p1"].exhausted_planets == industrial


def test_mining_initiative_wymaga_wlasnej_planety(registry: StaticDataRegistry) -> None:
    industrial = _planets_with(registry, "industrial", 1)
    state = _state(registry, ["mining_initiative"], industrial)
    with pytest.raises(ValueError, match="planet you control"):
        action_cards.play_action_card(state, registry, "p1", "mining_initiative", {"planet": "zzz"})
    new, _ = action_cards.play_action_card(
        state, registry, "p1", "mining_initiative", {"planet": industrial[0]}
    )
    assert new.players["p1"].trade_goods == registry.planets[industrial[0]].resources


def test_frontline_deployment_stawia_trzy_piechoty(registry: StaticDataRegistry) -> None:
    planet = _planets_with(registry, "cultural", 1)
    state = _state(registry, ["f_deployment"], planet)
    new, _ = action_cards.play_action_card(
        state, registry, "p1", "f_deployment", {"planet": planet[0]}
    )
    assert new.systems["000"].planet_units[planet[0]]["p1"]["infantry"] == 3


def test_messiah_po_jednej_piechocie_na_planete(registry: StaticDataRegistry) -> None:
    planets = _planets_with(registry, "hazardous", 2)
    state = _state(registry, ["messiah"], planets)
    new, _ = action_cards.play_action_card(state, registry, "p1", "messiah")
    for planet in planets:
        assert new.systems["000"].planet_units[planet]["p1"]["infantry"] == 1


def test_karta_bez_efektu_jest_zagrana_i_oznaczona_jako_reczna(
    registry: StaticDataRegistry,
) -> None:
    # Cripple Defenses: okno ACTION, brak efektu w silniku.
    state = _state(registry, ["cripple"], [])
    new, implemented = action_cards.play_action_card(state, registry, "p1", "cripple")
    assert not implemented
    assert new.decks.action_card_discard == ["cripple"]
    assert new.players["p1"].took_action_this_turn


def test_karta_reakcji_nie_jest_zagrywalna_jako_akcja(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["disgrace"], [])
    with pytest.raises(ValueError, match="reaction"):
        action_cards.play_action_card(state, registry, "p1", "disgrace")


def test_walidacje_reki_tury_i_actor_id(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["cripple"], [])
    with pytest.raises(ValueError, match="do not have"):
        action_cards.play_action_card(state, registry, "p1", "messiah")
    with pytest.raises(ValueError, match="cannot play a card for"):
        action_cards.play_action_card(state, registry, "p1", "cripple", actor_id="p2")
    state.players["p2"].private.action_cards = ["cripple"]
    with pytest.raises(ValueError, match="not p2's turn"):
        action_cards.play_action_card(state, registry, "p2", "cripple")
    done, _ = action_cards.play_action_card(state, registry, "p1", "cripple")
    done.players["p1"].private.action_cards = ["cripple"]
    with pytest.raises(ValueError, match="already took an action"):
        action_cards.play_action_card(done, registry, "p1", "cripple")


def test_blad_efektu_nie_zmienia_stanu_wejsciowego(registry: StaticDataRegistry) -> None:
    industrial = _planets_with(registry, "industrial", 1)
    state = _state(registry, ["mining_initiative"], industrial)
    with pytest.raises(ValueError):
        action_cards.play_action_card(state, registry, "p1", "mining_initiative", {})
    assert state.players["p1"].private.action_cards == ["mining_initiative"]
    assert not state.players["p1"].took_action_this_turn


def test_efekty_dodaja_status_implemented(registry: StaticDataRegistry) -> None:
    covered = rules_hooks.covered_components()
    for card_id in ("industrial_initiative", "economic_initiative", "mining_initiative",
                    "f_deployment", "messiah"):
        assert action_cards.effect_key(card_id) in covered
        assert registry.catalog.get(ComponentCategory.ACTION_CARD, card_id) is not None, card_id


def test_endpoint_odrzuca_karte_spoza_reki(registry: StaticDataRegistry) -> None:
    client = TestClient(create_app(registry=registry, store=EventStore(":memory:")))
    client.post("/game/new", json={"players": [{"faction_id": "sol"}, {"faction_id": "arborec"}]})
    player = next(iter(client.get("/state").json()["state"]["players"]))
    resp = client.post("/action-card/play", json={"player_id": player, "card_id": "messiah"})
    assert resp.status_code == 422
    assert "do not have" in resp.json()["detail"]
