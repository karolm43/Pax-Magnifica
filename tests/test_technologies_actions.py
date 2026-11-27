"""Testy technologii z akcją, zdolności i ofert (RULES.md 57): gracz zawsze decyduje."""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    command_tokens,
    component_action,
    exploration,
    production,
    space_cannon,
    tactical,
    technology_abilities,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_technology import _specialty_planet


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(techs: list[str], **player_kwargs: Any) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        rng_seed=3,
        players={
            "p1": PlayerState(
                player_id="p1", color="red", technologies=techs, trade_goods=6, **player_kwargs
            ),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
    )


def _only(state: GameState):  # type: ignore[no-untyped-def]
    assert len(state.pending_offers) == 1
    return state.pending_offers[0]


# --- Sling Relay ---
def _dock_state(techs: list[str]) -> GameState:
    state = _state(techs)
    state.systems["101"] = SystemState(
        position="101",
        system_id="20",
        planet_owners={"pl": "p1"},
        planet_units={"pl": {"p1": {"spacedock": 1}}},
    )
    state.systems["102"] = SystemState(position="102", system_id="22")
    return state


@ruling("C_technology/sling-relay/1")
def test_sling_relay_to_akcja_z_wyborem_systemu_i_produkcja_1_statku(
    registry: StaticDataRegistry,
) -> None:
    state = _dock_state(["sr"])
    info = technology_abilities.form(state, registry, "p1", "sr")
    assert info["kind"] == "action" and info["implemented"]
    assert [o["value"] for o in info["inputs"][0]["options"]] == ["101"]
    with pytest.raises(ValueError, match="valid option"):
        component_action.play_component_action(state, "p1", "sr", params={})
    with pytest.raises(ValueError, match="valid option"):
        component_action.play_component_action(state, "p1", "sr", params={"system": "102"})

    done = component_action.play_component_action(state, "p1", "sr", params={"system": "101"})
    assert done.players["p1"].took_action_this_turn
    assert "sr" in done.players["p1"].exhausted_technologies
    grant = done.production_grant
    assert grant is not None and grant.free and grant.ships_only and grant.units == 1

    produced = production.produce(
        done, HexGrid(), registry, "p1", [production.ProductionOrder("cruiser", 1)]
    )
    assert produced.systems["101"].space_units["p1"] == {"cruiser": 1}
    assert produced.production_grant is None
    assert produced.players["p1"].trade_goods < 6  # statek trzeba opłacić


def test_sling_relay_produkuje_tylko_statki_i_tylko_jedna_jednostke(
    registry: StaticDataRegistry,
) -> None:
    done = component_action.play_component_action(
        _dock_state(["sr"]), "p1", "sr", params={"system": "101"}
    )
    with pytest.raises(ValueError, match="ships only"):
        production.produce(
            done, HexGrid(), registry, "p1", [production.ProductionOrder("infantry", 1, "pl")]
        )
    with pytest.raises(ValueError, match="limit"):
        production.produce(
            done, HexGrid(), registry, "p1", [production.ProductionOrder("cruiser", 2)]
        )


def test_produce_z_karty_nie_jest_uzyciem_production(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sling Relay mówi "produce", nie "use PRODUCTION": techy na "use PRODUCTION" nie działają."""
    from src.core import triggers
    from src.core.game_events import GameEvent

    done = component_action.play_component_action(
        _dock_state(["sr"]), "p1", "sr", params={"system": "101"}
    )
    fired: list[GameEvent] = []
    real_fire = triggers.fire

    def spy(state: GameState, event: GameEvent, *args: object, **kwargs: object) -> object:
        fired.append(event)
        return real_fire(state, event, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(triggers, "fire", spy)
    production.produce(done, HexGrid(), registry, "p1", [production.ProductionOrder("cruiser", 1)])
    assert GameEvent.UNITS_PRODUCED in fired
    assert GameEvent.PRODUCTION_USED not in fired


def test_sling_relay_natychmiast_egzekwuje_pule_floty(registry: StaticDataRegistry) -> None:
    from src.core.game_state import WindowType

    state = _dock_state(["sr"])
    state.players["p1"].fleet_cc = 0
    done = component_action.play_component_action(state, "p1", "sr", params={"system": "101"})
    produced = production.produce(
        done, HexGrid(), registry, "p1", [production.ProductionOrder("cruiser", 1)]
    )
    window = produced.pending_window
    assert window is not None and window.window_type is WindowType.FLEET_POOL
    assert window.context["position"] == "101"


def test_sling_relay_wyczerpana_karta_nie_dziala() -> None:
    state = _dock_state(["sr"])
    state.players["p1"].exhausted_technologies = ["sr"]
    with pytest.raises(ValueError, match="not ready"):
        component_action.play_component_action(state, "p1", "sr", params={"system": "101"})


# --- Psychoarchaeology ---
def test_psychoarchaeology_gracz_wybiera_planety_i_dostaje_po_1_tg(
    registry: StaticDataRegistry,
) -> None:
    planet = _specialty_planet(registry, "WARFARE")
    state = _state(["pa"], controlled_planets=[planet])
    abilities = technology_abilities.free_abilities(state, registry, "p1")
    assert [a["tech_id"] for a in abilities] == ["pa"] and abilities[0]["usable"]
    done = technology_abilities.use_free_ability(state, registry, "p1", "pa", {"planets": [planet]})
    assert done.players["p1"].trade_goods == 7
    assert done.players["p1"].exhausted_planets == [planet]
    assert not done.players["p1"].took_action_this_turn  # to nie jest akcja
    with pytest.raises(ValueError, match="Invalid selection|Wrong number"):
        technology_abilities.use_free_ability(state, registry, "p1", "pa", {"planets": ["x"]})


@ruling("C_technology/psychoarchaeology/1")
def test_psychoarchaeology_tylko_w_fazie_akcji_i_nie_w_trakcie_innej_zdolnosci(
    registry: StaticDataRegistry,
) -> None:
    planet = _specialty_planet(registry, "WARFARE")
    state = _state(["pa"], controlled_planets=[planet])
    state.exploration = None
    state.phase = Phase.STATUS
    with pytest.raises(ValueError, match="action phase"):
        technology_abilities.use_free_ability(state, registry, "p1", "pa", {"planets": [planet]})
    state.phase = Phase.ACTION
    state.pending_offers = [
        triggers.PendingOffer(  # type: ignore[attr-defined]
            id="o", player_id="p2", event="e", moment="m", hook_seq=0
        )
    ]
    with pytest.raises(ValueError, match="Finish resolving"):
        technology_abilities.use_free_ability(state, registry, "p1", "pa", {"planets": [planet]})


# --- Frontier + Dark Energy Tap ---
def _frontier_state(techs: list[str]) -> GameState:
    state = _state(techs)
    state.active_system = "101"
    state.systems["101"] = SystemState(
        position="101",
        system_id="20",
        frontier_token=True,
        space_units={"p1": {"cruiser": 1}},
    )
    return state


@ruling(
    "R_exploration/rules-reference/4",
    "R_exploration/rules-reference/5",
    "R_exploration/rules-reference/6",
    "R_frontier_tokens/notes/1",
    "C_technology/dark-energy-tap/1",
    "C_technology/dark-energy-tap/2",
    "C_technology/dark-energy-tap/3",
)
def test_dark_energy_tap_po_akcji_taktycznej_bada_zeton_frontier(
    registry: StaticDataRegistry,
) -> None:
    ended = tactical.end_tactical_action(_frontier_state(["det"]))
    assert ended.exploration is not None
    current = ended.exploration.current
    assert current is not None and current.deck == "frontier" and current.planet == ""
    assert not ended.systems["101"].frontier_token
    assert ended.active_system is None


def test_dark_energy_tap_bez_technologii_lub_statku_nic_nie_robi() -> None:
    assert tactical.end_tactical_action(_frontier_state([])).exploration is None
    no_ship = _frontier_state(["det"])
    no_ship.systems["101"].space_units = {}
    assert tactical.end_tactical_action(no_ship).exploration is None
    assert no_ship.systems["101"].frontier_token


def test_kazda_karta_frontier_da_sie_rozstrzygnac_w_oknie_eksploracji(
    registry: StaticDataRegistry,
) -> None:
    ids = exploration.deck_card_ids(registry, "frontier")
    assert len(ids) == 20
    for card_id in ids:
        state = _frontier_state(["det"])
        state.players["p1"].private.action_cards = []
        state.decks.action_card_deck = ["a1", "a2", "a3"]
        state.decks.secret_objective_deck = ["s1", "s2"]
        state.decks.exploration_deck["frontier"] = [card_id]
        state.decks.exploration_discard["frontier"] = []
        # Mirage chains a cultural exploration; pin a card without a follow-up window
        # (Freelancers opens a production_grant that must be resolved before finish()).
        state.decks.exploration_deck["cultural"] = ["crf1"]
        started = tactical.end_tactical_action(state)
        options = exploration.options_for(started, registry)
        option = (
            next(o for o in options if o.enabled and o.id != "skip")
            if any(o.enabled and o.id != "skip" for o in options)
            else next(o for o in options if o.id == "skip")
        )
        param = option.params[0][0] if option.params else None
        done = exploration.resolve(started, registry, option.id, param)
        if card_id == "mirage":
            # Mirage: zdobyta planeta jest od razu eksplorowana (talia cultural) - dokończ ją.
            assert done.exploration is not None and done.exploration.current is not None
            options = exploration.options_for(done, registry)
            pick = next((o for o in options if o.enabled and o.id != "skip"), options[-1])
            param = pick.params[0][0] if pick.params else None
            done = exploration.resolve(done, registry, pick.id, param)
        assert done.exploration is not None and done.exploration.current is None, card_id
        closed = exploration.finish(done)
        assert closed.exploration is None, card_id


def test_karty_frontier_naprawde_cos_daja(registry: StaticDataRegistry) -> None:
    def resolve(card: str, option: str | None = None, param: str | None = None) -> GameState:
        state = _frontier_state(["det"])
        state.decks.action_card_deck = ["a1", "a2", "a3"]
        state.decks.exploration_deck["frontier"] = [card]
        started = tactical.end_tactical_action(state)
        chosen = option or next(
            o.id for o in exploration.options_for(started, registry) if o.enabled
        )
        return exploration.resolve(started, registry, chosen, param)

    assert resolve("lc1").players["p1"].private.action_cards == ["a1", "a2"]
    major = resolve("majent", param="tactical")
    assert major.players["p1"].trade_goods == 9 and major.players["p1"].tactical_cc == 4
    assert resolve("urf1").players["p1"].relic_fragments == ["urf1"]
    assert "GAMMA" in resolve("gamma").systems["101"].wormhole_tokens


# --- Scanlink Drone Network ---
def _explorable_system(registry: StaticDataRegistry) -> tuple[str, str]:
    for system in registry.systems.values():
        for planet in system.planets:
            if exploration.explorable(registry, planet):
                return system.id, planet
    raise AssertionError("no explorable planet")


@ruling("C_technology/scanlink-drone-network/1")
def test_scanlink_oferuje_eksploracje_planety_z_jednostkami_gracz_wybiera(
    registry: StaticDataRegistry,
) -> None:
    system_id, planet = _explorable_system(registry)
    state = _state(["sdn"])
    state.systems["101"] = SystemState(
        position="101", system_id=system_id, planet_units={planet: {"p1": {"infantry": 1}}}
    )
    triggers.fire(
        state,
        GameEvent.SYSTEM_ACTIVATED,
        Moment.AFTER,
        subject="p1",
        ctx={"player": "p1", "position": "101"},
    )
    offer = _only(state)
    assert not offer.mandatory and state.exploration is None  # nic nie dzieje się samo
    done = triggers.accept_offer(state, "p1", offer.id, {"planet": planet})
    assert done.exploration is not None
    current = done.exploration.current
    assert planet in [*done.exploration.queue, current.planet if current else ""]


def test_scanlink_nie_oferuje_bez_jednostek_na_planecie(registry: StaticDataRegistry) -> None:
    system_id, _planet = _explorable_system(registry)
    state = _state(["sdn"])
    state.systems["101"] = SystemState(position="101", system_id=system_id)
    triggers.fire(
        state,
        GameEvent.SYSTEM_ACTIVATED,
        Moment.AFTER,
        subject="p1",
        ctx={"player": "p1", "position": "101"},
    )
    assert state.pending_offers == []


# --- Self-Assembly Routines: mech ---
def test_self_assembly_oferuje_mecha_po_produkcji_i_wyczerpuje_karte() -> None:
    state = _state(["sar"])
    state.systems["101"] = SystemState(position="101", system_id="20", planet_owners={"pl": "p1"})
    ctx = {"player": "p1", "position": "101", "units": {"cruiser": 1}}
    triggers.fire(state, GameEvent.PRODUCTION_USED, Moment.AFTER, subject="p1", ctx=ctx)
    offer = _only(state)
    done = triggers.accept_offer(state, "p1", offer.id, {"planet": "pl"})
    assert done.systems["101"].planet_units["pl"]["p1"] == {"mech": 1}
    assert "sar" in done.players["p1"].exhausted_technologies
    declined = triggers.decline_offer(state, "p1", offer.id)
    assert "101" not in declined.systems or not declined.systems["101"].planet_units


def test_self_assembly_nie_oferuje_gdy_karta_wyczerpana_lub_brak_planety() -> None:
    state = _state(["sar"])
    state.systems["101"] = SystemState(position="101", system_id="20")
    ctx = {"player": "p1", "position": "101", "units": {}}
    triggers.fire(state, GameEvent.PRODUCTION_USED, Moment.AFTER, subject="p1", ctx=ctx)
    assert state.pending_offers == []


# --- Integrated Economy: produkcja po zdobyciu planety ---
def test_integrated_economy_otwiera_produkcje_z_limitem_kosztu(
    registry: StaticDataRegistry,
) -> None:
    system_id, planet = next(
        (s.id, p)
        for s in registry.systems.values()
        for p in s.planets
        if (registry.planets[p].resources or 0) >= 2
    )
    state = _state(["ie"])
    state.systems["101"] = SystemState(
        position="101", system_id=system_id, planet_owners={planet: "p1"}
    )
    state.players["p1"].controlled_planets = [planet]
    ctx = {"player": "p1", "planet": planet, "position": "101", "previous": None}
    triggers.fire(state, GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, subject="p1", ctx=ctx)
    offer = _only(state)
    assert state.production_grant is None  # oferta, nie automat
    done = triggers.accept_offer(state, "p1", offer.id, {})
    grant = done.production_grant
    cap = float(registry.planets[planet].resources or 0)
    assert grant is not None and grant.free and grant.zone == planet and grant.max_cost == cap

    ok = production.produce(
        done, HexGrid(), registry, "p1", [production.ProductionOrder("infantry", 2, planet)]
    )
    assert ok.systems["101"].planet_units[planet]["p1"] == {"infantry": 2}
    with pytest.raises(ValueError, match="exceeds"):
        production.produce(
            done, HexGrid(), registry, "p1", [production.ProductionOrder("dreadnought", 3)]
        )


# --- Transit Diodes ---
def _td_state() -> GameState:
    state = _state(["td"])
    state.systems["101"] = SystemState(
        position="101",
        system_id="20",
        planet_owners={"a": "p1"},
        planet_units={"a": {"p1": {"infantry": 2}}},
    )
    state.systems["102"] = SystemState(position="102", system_id="22", planet_owners={"b": "p1"})
    return state


def _td_offer(state: GameState):  # type: ignore[no-untyped-def]
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    return _only(state)


def test_transit_diodes_gracz_wybiera_ktore_sily_i_dokad() -> None:
    state = _td_state()
    offer = _td_offer(state)
    params = {
        "unit1": "101|a|infantry",
        "to1": "102|b",
        "unit2": "101|a|infantry",
        "to2": "102|b",
        "unit3": "",
        "to3": "",
        "unit4": "",
        "to4": "",
    }
    done = triggers.accept_offer(state, "p1", offer.id, params)
    assert done.systems["101"].planet_units["a"].get("p1", {}) == {}
    assert done.systems["102"].planet_units["b"]["p1"] == {"infantry": 2}
    assert "td" in done.players["p1"].exhausted_technologies


def test_transit_diodes_opcje_niosa_dane_dla_graficznego_wyboru(
    registry: StaticDataRegistry,
) -> None:
    """Graficzny panel (podnieś → połóż) czyta strukturę opcji, a nie etykiety."""
    from src.core import offers

    state = _td_state()
    offer = _td_offer(state)
    view = offers.offer_view(state, registry, offer)
    by_key = {i["key"]: i for i in view["inputs"]}
    stack = next(o for o in by_key["unit1"]["options"] if o["id"] == "101|a|infantry")
    assert stack["meta"]["count"] == 2 and stack["meta"]["asyncId"] == "gf"
    assert stack["meta"]["position"] == "101" and stack["meta"]["zone"] == "a"
    target = next(o for o in by_key["to1"]["options"] if o["id"] == "102|b")
    assert target["meta"]["planet"] == "b" and target["meta"]["position"] == "102"
    # Opcja „nic" nie ma meta - pusty slot.
    assert "meta" not in next(o for o in by_key["unit1"]["options"] if o["id"] == "none")


def test_transit_diodes_waliduje_wybor() -> None:
    state = _td_state()
    offer = _td_offer(state)
    base = {
        "unit1": "",
        "to1": "",
        "unit2": "",
        "to2": "",
        "unit3": "",
        "to3": "",
        "unit4": "",
        "to4": "",
    }
    with pytest.raises(ValueError, match="both"):
        triggers.accept_offer(state, "p1", offer.id, {**base, "unit1": "101|a|infantry"})
    with pytest.raises(ValueError, match="at least one"):
        triggers.accept_offer(state, "p1", offer.id, base)
    too_many = {**base}
    for slot in (1, 2, 3):
        too_many[f"unit{slot}"], too_many[f"to{slot}"] = "101|a|infantry", "102|b"
    with pytest.raises(ValueError, match="more ground forces"):
        triggers.accept_offer(state, "p1", offer.id, too_many)


def test_transit_diodes_bez_sil_naziemnych_nie_oferuje() -> None:
    state = _td_state()
    state.systems["101"].planet_units = {}
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    assert state.pending_offers == []


# --- Predictive Intelligence ---
def test_predictive_intelligence_gracz_przerozdziela_zetony() -> None:
    state = _state(["pi"], tactical_cc=3, fleet_cc=3, strategic_cc=2)
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    offer = _only(state)
    with pytest.raises(ValueError, match="exactly"):
        triggers.accept_offer(state, "p1", offer.id, {"tactical": 8, "fleet": 8, "strategic": 8})
    done = triggers.accept_offer(state, "p1", offer.id, {"tactical": 1, "fleet": 2, "strategic": 5})
    player = done.players["p1"]
    assert (player.tactical_cc, player.fleet_cc, player.strategic_cc) == (1, 2, 5)
    assert "pi" in player.exhausted_technologies
    assert command_tokens.sheet_total(done, "p1") == 8


def test_pokrycie_technologii_po_tym_bloku() -> None:
    from src.core import rules_hooks

    covered = rules_hooks.covered_components()
    for tech in ("sr", "pa", "det", "sdn", "sar", "ie", "td"):
        assert f"technologies:{tech}" in covered, tech

# --- Graviton Laser System: świadomy wybór gracza ------------------------------------------------


def _gls_fire(seed: int, *, gls: bool, tech: bool = True) -> GameState:
    from tests.test_space_cannon import _grid, _state

    techs = {"p2": ["gls"]} if tech else {}
    state = _state(
        pds={"p2": 3}, ships={"p1": {"destroyer": 2, "fighter": 2}}, techs=techs, seed=seed
    )
    opened = space_cannon.open_offense(state, _grid(), StaticDataRegistry())
    return space_cannon.fire_offense(
        opened, _grid(), StaticDataRegistry(), "p2", "p1", exhaust_gls=gls
    )


def _seed_with_one_hit(gls: bool) -> GameState:
    for seed in range(1, 200):
        fired = _gls_fire(seed, gls=gls)
        pending = space_cannon.pending_hits(fired)
        if pending is not None and pending.hits == 1:
            return fired
    raise AssertionError("no seed with exactly one hit")


def test_gls_wyczerpany_na_zyczenie_gracza_kieruje_trafienia_w_statki_niemyslihwskie() -> None:
    fired = _seed_with_one_hit(gls=True)
    assert "gls" in fired.players["p2"].exhausted_technologies
    with pytest.raises(ValueError, match="non-fighter"):
        space_cannon.assign_hits(fired, "p1", {"fighter": 1})
    done = space_cannon.assign_hits(fired, "p1", {"destroyer": 1})
    assert done.systems["000"].space_units["p1"] == {"destroyer": 1, "fighter": 2}


def test_gls_bez_wyczerpania_ofiara_wybiera_dowolny_statek() -> None:
    fired = _seed_with_one_hit(gls=False)
    assert "gls" not in fired.players["p2"].exhausted_technologies
    done = space_cannon.assign_hits(fired, "p1", {"fighter": 1})
    assert done.systems["000"].space_units["p1"] == {"destroyer": 2, "fighter": 1}


def test_gls_nie_da_sie_wyczerpac_bez_technologii_ani_dwa_razy() -> None:
    with pytest.raises(ValueError, match="not ready"):
        _gls_fire(1, gls=True, tech=False)


# --- AI Development Algorithm: zniżka kosztu na życzenie gracza ----------------------------------


def test_aida_obniza_koszt_o_liczbe_ulepszen_tylko_gdy_gracz_ja_wyczerpie(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["aida", "cr2", "dd2"])
    state.active_system = "101"
    state.systems["101"] = SystemState(position="101", system_id="20")
    orders = [production.ProductionOrder("dreadnought", 1)]
    base = production.order_cost(state, registry, "p1", orders)
    assert production.order_cost(state, registry, "p1", orders, exhaust_aida=True) == base - 2
    assert production.aida_discount(state, registry, "p1") == 2
    state.players["p1"].exhausted_technologies = ["aida"]
    with pytest.raises(ValueError, match="not ready"):
        production.order_cost(state, registry, "p1", orders, exhaust_aida=True)


def test_aida_wyczerpuje_sie_przy_produkcji_na_zadanie() -> None:
    registry = StaticDataRegistry()
    state = _dock_state(["aida", "cr2"])
    done = component_action.play_component_action(
        _dock_state(["sr", "aida", "cr2"]), "p1", "sr", params={"system": "101"}
    )
    del state
    cost = production.order_cost(
        done, registry, "p1", [production.ProductionOrder("cruiser", 1)], exhaust_aida=True
    )
    produced = production.produce(
        done, HexGrid(), registry, "p1", [production.ProductionOrder("cruiser", 1)],
        exhaust_aida=True,
    )
    assert "aida" in produced.players["p1"].exhausted_technologies
    assert produced.players["p1"].trade_goods == 6 - cost
    plain = production.produce(
        done, HexGrid(), registry, "p1", [production.ProductionOrder("cruiser", 1)]
    )
    assert "aida" not in plain.players["p1"].exhausted_technologies


def test_sarween_tools_zniżka_widoczna_dla_ui() -> None:
    state = _state(["st"])
    state.active_system = "101"
    assert production.cost_reduction(state, "p1") == 1
    assert production.cost_reduction(_state([]), "p1") == 0


def test_sarween_tools_dziala_przy_produkcji_z_karty_strategii() -> None:
    """Warfare secondary / Minister of Industry = użycie PRODUCTION doku poza akcją: zniżka -1."""
    from src.core.game_state import ProductionGrant

    state = _state(["st"])
    state.production_grant = ProductionGrant(
        player_id="p1", position="101", standalone=True, source="Warfare"
    )
    assert state.active_system is None
    assert production.cost_reduction(state, "p1") == 1
    # Grant „produce N units" z karty (Freelancers) nie jest użyciem PRODUCTION - bez zniżki.
    state.production_grant = ProductionGrant(player_id="p1", position="101", source="Freelancers")
    state.active_system = "101"
    assert production.cost_reduction(state, "p1") == 0


def test_zrodla_zniżki_produkcji_maja_nazwe_z_danych() -> None:
    registry = StaticDataRegistry()
    state = _state(["st"])
    state.active_system = "101"
    assert production.cost_reduction_sources(state, registry, "p1") == [("Sarween Tools", 1.0)]
    state.production_used = 1  # zniżka już wykorzystana w tym użyciu PRODUCTION
    assert production.cost_reduction_sources(state, registry, "p1") == []
