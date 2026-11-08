"""Testy zagrywania kart akcji z oknem ACTION (RULES.md 53)."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import action_cards, exploration, rules_hooks
from src.core.components import ComponentCategory
from src.core.dice import DIE_SIDES, next_rng
from src.core.event_store import EventStore
from src.core.fleet_pool import unit_cost
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
    # Reactor Meltdown: okno ACTION, brak efektu w silniku.
    state = _state(registry, ["meltdown"], [])
    new, implemented = action_cards.play_action_card(state, registry, "p1", "meltdown")
    assert not implemented
    assert new.decks.action_card_discard == ["meltdown"]
    assert new.players["p1"].took_action_this_turn


def test_karta_reakcji_nie_jest_zagrywalna_jako_akcja(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["disgrace"], [])
    with pytest.raises(ValueError, match="reaction"):
        action_cards.play_action_card(state, registry, "p1", "disgrace")


def test_walidacje_reki_tury_i_actor_id(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["meltdown"], [])
    with pytest.raises(ValueError, match="do not have"):
        action_cards.play_action_card(state, registry, "p1", "messiah")
    with pytest.raises(ValueError, match="cannot play a card for"):
        action_cards.play_action_card(state, registry, "p1", "meltdown", actor_id="p2")
    state.players["p2"].private.action_cards = ["meltdown"]
    with pytest.raises(ValueError, match="not p2's turn"):
        action_cards.play_action_card(state, registry, "p2", "meltdown")
    done, _ = action_cards.play_action_card(state, registry, "p1", "meltdown")
    done.players["p1"].private.action_cards = ["meltdown"]
    with pytest.raises(ValueError, match="already took an action"):
        action_cards.play_action_card(done, registry, "p1", "meltdown")


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


# --------------------------------------------------------------------------- druga paczka kart

CARD_IDS_BATCH2 = (
    "unexpected", "insub", "spy", "repeal", "impersonation",
    "war_effort", "lucky", "cripple", "plague", "refit", "scuttle",
)


def _play(
    state: GameState,
    registry: StaticDataRegistry,
    card: str,
    params: Mapping[str, object] | None = None,
) -> GameState:
    state.players["p1"].private.action_cards = [card]
    new, implemented = action_cards.play_action_card(state, registry, "p1", card, params)
    assert implemented
    return new


def test_druga_paczka_ma_status_implemented(registry: StaticDataRegistry) -> None:
    covered = rules_hooks.covered_components()
    for card_id in CARD_IDS_BATCH2:
        assert action_cards.effect_key(card_id) in covered, card_id
        assert registry.catalog.get(ComponentCategory.ACTION_CARD, card_id) is not None, card_id


def test_unexpected_action_zdejmuje_wlasny_zeton_do_rezerwy(registry: StaticDataRegistry) -> None:
    state = _state(registry, [], [], cc_reinf=1)
    state.systems["000"].command_tokens = ["p1", "p2"]
    new = _play(state, registry, "unexpected", {"position": "000"})
    assert new.systems["000"].command_tokens == ["p2"]
    assert new.players["p1"].cc_reinf == 2
    new.players["p1"].took_action_this_turn = False
    with pytest.raises(ValueError, match="no command token"):
        _play(new, registry, "unexpected", {"position": "000"})


def test_insubordination_zabiera_zeton_z_puli_taktycznej_innego_gracza(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, [], [])
    state.players["p2"].tactical_cc = 3
    state.players["p2"].cc_reinf = 0
    new = _play(state, registry, "insub", {"player": "p2"})
    assert (new.players["p2"].tactical_cc, new.players["p2"].cc_reinf) == (2, 1)
    with pytest.raises(ValueError, match="another player"):
        _play(state, registry, "insub", {"player": "p1"})  # nie można celować w siebie


def test_spy_przenosi_losowa_karte_i_wymaga_kart_celu(registry: StaticDataRegistry) -> None:
    state = _state(registry, [], [])
    state.players["p2"].private.action_cards = ["a", "b"]
    new = _play(state, registry, "spy", {"player": "p2"})
    stolen = new.players["p1"].private.action_cards
    assert len(stolen) == 1 and stolen[0] in {"a", "b"}
    assert len(new.players["p2"].private.action_cards) == 1
    state.players["p2"].private.action_cards = []
    with pytest.raises(ValueError, match="no action cards"):
        _play(state, registry, "spy", {"player": "p2"})


def test_repeal_law_zdejmuje_prawo_do_odrzuconych(registry: StaticDataRegistry) -> None:
    state = _state(registry, [], [])
    state.decks.agenda_laws["some_law"] = "for"
    with pytest.raises(ValueError, match="not a law in play"):
        _play(state, registry, "repeal", {"law": "other"})
    new = _play(state, registry, "repeal", {"law": "some_law"})
    assert "some_law" not in new.decks.agenda_laws
    assert new.decks.agenda_discard[-1] == "some_law"


def test_impersonation_wymaga_trzech_wplywow_i_dobiera_tajny_cel(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, [], [], trade_goods=3)
    state.decks.secret_objective_deck = ["s1", "s2"]
    with pytest.raises(ValueError, match="at least 3 influence"):
        _play(state, registry, "impersonation", {"trade_goods": 2})
    new = _play(state, registry, "impersonation", {"trade_goods": 3})
    assert new.players["p1"].private.secret_objectives == ["s1"]
    assert new.players["p1"].trade_goods == 0
    with pytest.raises(ValueError, match="Not enough trade goods"):
        _play(state, registry, "impersonation", {"trade_goods": 4})


def test_war_effort_stawia_krazownik_w_systemie_z_wlasnymi_statkami(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, [], [])
    with pytest.raises(ValueError, match="your ships"):
        _play(state, registry, "war_effort", {"position": "000"})
    state.systems["000"].space_units = {"p1": {"destroyer": 1}}
    new = _play(state, registry, "war_effort", {"position": "000"})
    assert new.systems["000"].space_units["p1"] == {"destroyer": 1, "cruiser": 1}


def test_lucky_shot_niszczy_wybrany_statek_innego_gracza(registry: StaticDataRegistry) -> None:
    planet = _planets_with(registry, "cultural", 1)
    state = _state(registry, [], planet)
    state.systems["000"].space_units = {"p2": {"cruiser": 2, "carrier": 1}}
    new = _play(
        state, registry, "lucky", {"position": "000", "owner": "p2", "base_type": "cruiser"}
    )
    assert new.systems["000"].space_units["p2"] == {"cruiser": 1, "carrier": 1}
    for bad in ({"base_type": "carrier"}, {"base_type": "warsun"}, {"owner": "p1"}):
        params = {"position": "000", "owner": "p2", "base_type": "cruiser", **bad}
        with pytest.raises(ValueError):
            _play(state, registry, "lucky", params)


def test_cripple_defenses_niszczy_pds_wszystkich_graczy_na_planecie(
    registry: StaticDataRegistry,
) -> None:
    planet = _planets_with(registry, "hazardous", 1)[0]
    state = _state(registry, [], [])
    state.systems["000"].planet_owners = {planet: "p2"}
    state.systems["000"].planet_units = {
        planet: {"p1": {"pds": 1, "infantry": 1}, "p2": {"pds": 2}}
    }
    new = _play(state, registry, "cripple", {"planet": planet})
    assert new.systems["000"].planet_units[planet].get("p2", {}).get("pds", 0) == 0
    assert new.systems["000"].planet_units[planet]["p1"] == {"infantry": 1}


def test_plague_jest_deterministyczny_i_celuje_tylko_w_cudze_planety(
    registry: StaticDataRegistry,
) -> None:
    planet = _planets_with(registry, "hazardous", 1)[0]
    state = _state(registry, [], [])
    state.rng_seed = 7
    state.systems["000"].planet_owners = {planet: "p2"}
    state.systems["000"].planet_units = {planet: {"p2": {"infantry": 12}}}
    rng = next_rng(state.clone())
    hits = sum(1 for _ in range(12) if rng.randint(1, DIE_SIDES) >= 6)
    new = _play(state, registry, "plague", {"planet": planet})
    assert new.systems["000"].planet_units[planet]["p2"].get("infantry", 0) == 12 - hits
    state.systems["000"].planet_owners = {planet: "p1"}
    with pytest.raises(ValueError, match="another player"):
        _play(state, registry, "plague", {"planet": planet})


def test_refit_troops_zamienia_piechote_na_mechy(registry: StaticDataRegistry) -> None:
    planet = _planets_with(registry, "cultural", 1)[0]
    state = _state(registry, [], [planet])
    state.systems["000"].planet_units = {planet: {"p1": {"infantry": 2}}}
    new = _play(state, registry, "refit", {"planets": [planet, planet]})
    assert new.systems["000"].planet_units[planet]["p1"] == {"mech": 2}
    for bad in ([], [planet] * 3, [planet, "zzz"]):
        with pytest.raises(ValueError):
            _play(state, registry, "refit", {"planets": bad})


def test_scuttle_zwraca_statki_i_daje_tg_rowne_kosztowi(registry: StaticDataRegistry) -> None:
    state = _state(registry, [], [], trade_goods=0)
    state.systems["000"].space_units = {"p1": {"destroyer": 1, "cruiser": 1, "fighter": 3}}
    expected = int(
        unit_cost(state, registry, "p1", "destroyer") + unit_cost(state, registry, "p1", "cruiser")
    )
    ships = [
        {"position": "000", "base_type": "destroyer"},
        {"position": "000", "base_type": "cruiser"},
    ]
    new = _play(state, registry, "scuttle", {"ships": ships})
    assert new.players["p1"].trade_goods == expected > 0
    assert new.systems["000"].space_units["p1"] == {"fighter": 3}
    with pytest.raises(ValueError, match="non-fighter"):
        _play(state, registry, "scuttle", {"ships": [{"position": "000", "base_type": "fighter"}]})
