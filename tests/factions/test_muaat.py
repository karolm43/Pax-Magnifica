"""The Embers of Muaat — komplet komponentów frakcji (RULES.md 62.13) i rulingi F_muaat.

Scenariusze przez prawdziwe API (ACTION, oferty, notka): ``test_flows_muaat.py``. Statusy bez
testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    breakthrough,
    command_tokens,
    elimination,
    faction_components,
    leaders,
    movement,
    production,
    promissory_play,
    retreat,
    rules_hooks,
    strategic_action,
    tile_swap,
    timing,
    triggers,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    EliminatedPlayer,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.hooks import planets_legendary
from src.core.hooks.factions import muaat
from src.core.production import ProductionOrder
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.strategy_cards import CARDS
from tests.factions.completeness import missing_components
from tests.rulings import ruling

# Pierścień 1: 101 = dom Muaat (04), 102 = Vefutii, 103 = Thibah (p2), 104 = supernowa (43),
# 105 = Tarmann, 000 = Mecatol. Sąsiedzi w pierścieniu: 101-102-103-104-105.
MUAAT_PLANET, VEFUTII, THIBAH, TARMANN = "muaat", "vefutii", "thibah", "tarmann"
HOME, PLAIN, RIVAL, NOVA, FAR = "101", "102", "103", "104", "105"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _state(other: str = "sol") -> GameState:
    """p1 = Muaat (aktywny, war sun w domu), p2 = rywal z planetą Thibah."""
    p1 = PlayerState(player_id="p1", color="red", faction="muaat", home_position=HOME)
    p2 = PlayerState(player_id="p2", color="blue", faction=other)
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            HOME: SystemState(position=HOME, system_id="04", planet_owners={MUAAT_PLANET: "p1"},
                              space_units={"p1": {"warsun": 1}}),
            PLAIN: SystemState(position=PLAIN, system_id="20"),
            RIVAL: SystemState(position=RIVAL, system_id="21", planet_owners={THIBAH: "p2"}),
            NOVA: SystemState(position=NOVA, system_id="43"),
            FAR: SystemState(position=FAR, system_id="22"),
        },
    )
    state.players["p1"].controlled_planets = [MUAAT_PLANET]
    state.players["p2"].controlled_planets = [THIBAH]
    for p in state.players.values():
        p.cc_reinf = 8
        p.strategic_cc = 2
    return state


def _offers(state: GameState, pid: str, label: str) -> list[Any]:
    return [o for o in triggers.offers_for(state, pid) if label in o.label]


def _accept(state: GameState, pid: str, label: str, params: dict[str, Any] | None = None
            ) -> GameState:
    offer = _offers(state, pid, label)[0]
    return triggers.accept_offer(state, pid, offer.id, params)


def _play(state: GameState, registry: StaticDataRegistry, kind: str, comp: str,
          params: dict[str, Any] | None = None, pid: str = "p1") -> GameState:
    after, _ = faction_components.play(state, registry, pid, kind, comp, params or {})
    return after


def test_muaat_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "muaat") == []


# ============================================================================== Star Forge


@ruling("abilities:star_forge#1")
def test_star_forge_niszczyciel_przy_war_sunie(registry: StaticDataRegistry) -> None:
    after = _play(_state(), registry, "ability", "star_forge",
                  {"position": HOME, "unit": "destroyer"})
    assert after.systems[HOME].space_units["p1"] == {"warsun": 1, "destroyer": 1}
    assert after.players["p1"].strategic_cc == 1
    fighters = _play(_state(), registry, "ability", "star_forge",
                     {"position": HOME, "unit": "fighters"})
    assert fighters.systems[HOME].space_units["p1"]["fighter"] == 2


@ruling("F_muaat/star-forge/1")
def test_star_forge_bez_war_suna_niedostepna(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[HOME].space_units = {}
    reason = faction_components.block_reason(state, registry, "p1", "ability", "star_forge")
    assert reason is not None and "war sun" in reason
    with pytest.raises(ValueError):
        _play(_state(), registry, "ability", "star_forge", {"position": PLAIN, "unit": "destroyer"})


# ================================================================ Gashlai / Magmus Reactor


def _grid(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    return grid_from_state(state, registry)


@ruling("abilities:gashlai_physiology#1")
def test_gashlai_przelot_przez_supernowe(registry: StaticDataRegistry) -> None:
    state = _state()
    grid = _grid(state, registry)
    passable = movement._node_passable_intermediate  # noqa: SLF001 - reguła R4/R6 wprost
    assert passable(grid, state, NOVA, "p1", can_enter_asteroids=False)
    assert not passable(grid, state, NOVA, "p2", can_enter_asteroids=False)
    # Przelot to nie wejście: supernowa jako cel nadal zamknięta bez Magmus Reactor.
    assert not movement.can_enter_supernova(state, "p1")


@ruling("technologies:mr#1", "R_space_combat/notes/3")
def test_magmus_reactor_wejscie_i_odwrot_do_supernowej(registry: StaticDataRegistry) -> None:
    state = _state()
    grid = _grid(state, registry)
    assert NOVA not in retreat.retreat_destinations(state, grid, RIVAL, "p1")
    state.players["p1"].technologies = ["mr"]
    assert movement.can_enter_supernova(state, "p1")
    assert movement.entry_blocked(grid, state, NOVA, "p1") is None
    state.systems[NOVA].space_units = {"p1": {"destroyer": 1}}  # obecność - cel odwrotu
    assert NOVA in retreat.retreat_destinations(state, grid, RIVAL, "p1")


@ruling("F_norr/ghom-sekkus/8.3")
def test_magmus_reactor_wejscie_sil_do_supernowej(registry: StaticDataRegistry) -> None:
    """Wejście jednostek spoza ruchu (G'hom Sek'kus) do supernowej - tylko z Magmus Reactor."""
    state = _state("sardakk")
    grid = _grid(state, registry)
    assert movement.entry_blocked(grid, state, NOVA, "p2") is not None
    state.players["p2"].technologies = ["mr"]
    assert movement.entry_blocked(grid, state, NOVA, "p2") is None


@ruling("technologies:mr#2")
def test_magmus_reactor_supernowa_produkuje_5(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["mr"]
    assert production.producers(state, registry, "p1", NOVA) == []  # bez jednostek w supernowej
    state.systems[NOVA].space_units = {"p1": {"destroyer": 1}}
    found = production.producers(state, registry, "p1", NOVA)
    assert [(p.zone, p.value) for p in found] == [("space", 5)]
    # Źródło zdolności = technologia (okno produkcji pokazuje jej ikonę, nie sprite jednostki).
    assert found[0].source is not None and found[0].source.component_id == "mr"


@ruling("F_muaat/magmus-reactor-omega/1")
def test_magmus_reactor_jednostka_w_supernowej_chroni_przed_eliminacja(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.systems[HOME].planet_owners = {}
    state.systems[HOME].space_units = {}
    state.players["p1"].controlled_planets = []
    state.systems[NOVA].space_units = {"p1": {"destroyer": 1}}
    assert elimination.meets_conditions(state, registry, "p1")
    state.players["p1"].technologies = ["mr"]
    assert not elimination.meets_conditions(state, registry, "p1")


# ========================================================================= Prototype War Sun


@ruling("technologies:pws2#1", "technologies:pws2#2", "technologies:pws2#3",
        "units:muaat_warsun#1", "C_units/war-sun/1.1")
def test_prototype_war_sun_dane(registry: StaticDataRegistry) -> None:
    base = resolve_unit_variant(registry, "muaat", [], "warsun")
    assert base is not None and base.id == "muaat_warsun"  # bez technologii (C_units 1.1)
    assert base.disables_planetary_shield
    upgraded = resolve_unit_variant(registry, "muaat", ["pws2"], "warsun")
    assert upgraded is not None
    assert (upgraded.cost, upgraded.combat_hits_on, upgraded.combat_die_count) == (10, 3, 3)
    assert (upgraded.move_value, upgraded.capacity_value) == (3, 6)
    assert upgraded.sustain_damage and (upgraded.bombard_hits_on, upgraded.bombard_die_count) == (
        3, 3)
    assert upgraded.disables_planetary_shield
    assert resolve_unit_variant(registry, "sol", [], "warsun") is None or (
        resolve_unit_variant(registry, "sol", [], "warsun").id != "muaat_warsun"  # type: ignore[union-attr]
    )


# ============================================================================ The Inferno


@ruling("units:muaat_flagship#1")
def test_the_inferno_krazownik_w_systemie_flagowca(registry: StaticDataRegistry) -> None:
    state = _state()
    reason = faction_components.block_reason(state, registry, "p1", "unit", "muaat_flagship")
    assert reason is not None  # flagowca nie ma na planszy - komponent nieposiadany
    state.systems[PLAIN].space_units = {"p1": {"flagship": 1}}
    assert ("unit", "muaat_flagship") in faction_components.owned(state, registry, "p1")
    after = _play(state, registry, "unit", "muaat_flagship")
    assert after.systems[PLAIN].space_units["p1"] == {"flagship": 1, "cruiser": 1}
    assert after.players["p1"].strategic_cc == 1


# =========================================================================== Ember Colossus


@ruling("units:muaat_mech#1")
def test_ember_colossus_piechota_przy_mechu_obok(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[PLAIN].planet_units = {VEFUTII: {"p1": {"mech": 1}}}
    state.systems[FAR].planet_units = {TARMANN: {"p1": {"mech": 1}}}  # za daleko od domu
    after = _play(state, registry, "ability", "star_forge", {"position": HOME, "unit": "destroyer"})
    offer = _offers(after, "p1", "Ember Colossus")[0]
    inputs = muaat.colossus_inputs(after, registry, "p1", offer.ctx)
    values = [o["value"] for o in inputs[0]["options"]]
    assert values == [f"{PLAIN}|{VEFUTII}|0"]
    done = _accept(after, "p1", "Ember Colossus", {"mechs": values})
    assert done.systems[PLAIN].planet_units[VEFUTII]["p1"] == {"mech": 1, "infantry": 1}


@ruling("F_muaat/avernus-the-nucleus/1", "F_muaat/avernus-the-nucleus/2")
def test_nucleus_to_star_forge_bez_zetonu(registry: StaticDataRegistry) -> None:
    """The Nucleus: Star Forge bez żetonu - mech dokłada piechotę, Magmus nie daje TG."""
    state = _state()
    state.players["p1"].leader_states[muaat.COMMANDER] = "unlocked"
    state.systems[HOME].planet_units = {MUAAT_PLANET: {"p1": {"mech": 1}}}
    planets_legendary.nucleus(state, registry, "p1", {"position": HOME, "unit": "destroyer"})
    assert state.players["p1"].strategic_cc == 2
    assert _offers(state, "p1", "Ember Colossus")
    assert not _offers(state, "p1", "Magmus")


@ruling("F_muaat/avernus-the-nucleus/3")
def test_nucleus_inny_kontroler_tylko_z_war_sunem(registry: StaticDataRegistry) -> None:
    state = _state()
    assert planets_legendary._nucleus_blocker(state, registry, "p2") is not None  # noqa: SLF001
    state.systems[PLAIN].space_units = {"p2": {"warsun": 1}}
    assert planets_legendary._nucleus_blocker(state, registry, "p2") is None  # noqa: SLF001


# ==================================================================================== Umbat


def _umbat(registry: StaticDataRegistry, target: str = "p2") -> GameState:
    state = _state()
    state.systems[RIVAL].space_units = {"p2": {"flagship": 1}}
    state.players["p2"].trade_goods = 10
    after = _play(state, registry, "leader", muaat.AGENT, {"player": target})
    assert after.players["p1"].leader_states[muaat.AGENT] == "exhausted"
    return _accept(after, target, "Umbat", {"position": RIVAL})


@ruling("leaders:muaatagent#1", "F_muaat/umbat/2")
def test_umbat_wybrany_gracz_produkuje_2_tanie_jednostki(registry: StaticDataRegistry) -> None:
    state = _umbat(registry)
    grant = state.production_grant
    assert grant is not None and grant.player_id == "p2" and grant.position == RIVAL
    assert grant.free and grant.units == 2 and grant.max_unit_cost == 4
    grid = _grid(state, registry)
    production.validate_production(state, grid, registry, "p2", [
        ProductionOrder(base_type="dreadnought", count=1, zone="space"),
        ProductionOrder(base_type="cruiser", count=1, zone="space"),
    ])
    state.players["p2"].technologies = ["ws"]  # war sun (koszt 12) dostępny, ale za drogi
    with pytest.raises(ValueError, match="cost 4 or less"):
        production.validate_production(state, grid, registry, "p2", [
            ProductionOrder(base_type="warsun", count=1, zone="space"),
        ])
    with pytest.raises(ValueError):
        production.validate_production(state, grid, registry, "p2", [
            ProductionOrder(base_type="cruiser", count=3, zone="space"),
        ])


@ruling("F_muaat/umbat/1", "F_muaat/umbat/3")
def test_umbat_platne_i_sily_naziemne_na_planecie(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _umbat(registry)
    state.players["p2"].trade_goods = 5
    state.players["p2"].exhausted_planets = [THIBAH]  # płaci tylko TG
    zones = production.allowed_ground_zones(state, registry, "p2", RIVAL)
    assert set(zones) == {THIBAH, "space"}
    fired: list[GameEvent] = []
    original = triggers.fire

    def spy(st: GameState, event: GameEvent, *args: Any, **kwargs: Any) -> Any:
        fired.append(event)
        return original(st, event, *args, **kwargs)

    monkeypatch.setattr(triggers, "fire", spy)
    after = production.produce(state, _grid(state, registry), registry, "p2", [
        ProductionOrder(base_type="infantry", count=1, zone=THIBAH),
        ProductionOrder(base_type="cruiser", count=1, zone="space"),
    ])
    assert after.systems[RIVAL].planet_units[THIBAH]["p2"]["infantry"] == 1
    assert after.players["p2"].trade_goods == 5 - 3  # zapłacone (umbat 1)
    assert GameEvent.PRODUCTION_USED not in fired  # bez użycia PRODUCTION (umbat 2)


# ==================================================================================== Magmus


@ruling("leaders:muaatcommander#unlock")
def test_magmus_odblokowany_po_produkcji_war_suna(registry: StaticDataRegistry) -> None:
    state = _state()
    assert leaders.state_of(state, registry, "p1", muaat.COMMANDER) == "locked"
    triggers.fire(state, GameEvent.UNITS_PRODUCED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": HOME, "units": {"cruiser": 1}})
    assert leaders.state_of(state, registry, "p1", muaat.COMMANDER) == "locked"
    triggers.fire(state, GameEvent.UNITS_PRODUCED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": HOME, "units": {"warsun": 1}})
    assert leaders.state_of(state, registry, "p1", muaat.COMMANDER) == "unlocked"


def _magmus_state() -> GameState:
    state = _state()
    state.players["p1"].leader_states[muaat.COMMANDER] = "unlocked"
    return state


@ruling("leaders:muaatcommander#1", "F_muaat/magmus/2", "C_objectives/lead-from-the-front/2",
        "C_objectives/galvanize-the-people/2")
def test_magmus_tg_za_kazdy_zeton(registry: StaticDataRegistry) -> None:
    state = _magmus_state()
    command_tokens.spend_strategy_token(state, "p1")
    command_tokens.spend_strategy_token(state, "p1")
    assert len(_offers(state, "p1", "Magmus")) == 2  # dwa żetony = dwie oferty, po jednej
    state = _accept(state, "p1", "Magmus")
    state = _accept(state, "p1", "Magmus")
    assert state.players["p1"].trade_goods == 2


@ruling("F_muaat/magmus/3", "C_relics/scepter-of-emelpar/3")
def test_magmus_bez_tg_przy_scepter(registry: StaticDataRegistry) -> None:
    state = _magmus_state()
    state.players["p1"].relics = ["emelpar"]
    command_tokens.spend_strategy_token(state, "p1", source=command_tokens.SOURCE_SCEPTER)
    assert not _offers(state, "p1", "Magmus")


@ruling("F_muaat/magmus/4", "F_muaat/magmus/4.1")
def test_magmus_musi_byc_odblokowany_przed_wydaniem(registry: StaticDataRegistry) -> None:
    """Żeton wydany przy zablokowanym Magmusie (np. Warfare, który produkuje war suna) - bez TG,
    nawet gdy odblokowanie przyjdzie zaraz potem."""
    state = _state()
    command_tokens.spend_strategy_token(state, "p1")
    triggers.fire(state, GameEvent.UNITS_PRODUCED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": HOME, "units": {"warsun": 1}})
    assert leaders.state_of(state, registry, "p1", muaat.COMMANDER) == "unlocked"
    assert not _offers(state, "p1", "Magmus")


@ruling("F_muaat/magmus/1")
def test_magmus_tg_po_rozstrzygnieciu_secondary(registry: StaticDataRegistry) -> None:
    """Secondary Trade: TG z Magmusa przychodzi po secondary (oferta czeka) - nie płaci kosztów."""
    state = _magmus_state()
    state.players["p2"].strategy_cards = [5]
    state = timing.open_window(
        state, WindowType.STRATEGY_SECONDARY, ["p1"],
        context={"initiative": 5, "free": "", "cost": 1 if CARDS[5].secondary_costs_token else 0},
    )
    after = strategic_action.resolve_secondary(state, registry, "p1", execute=True)
    assert after.players["p1"].trade_goods == 0
    assert len(_offers(after, "p1", "Magmus")) == 1
    assert _accept(after, "p1", "Magmus").players["p1"].trade_goods == 1


@ruling("F_muaat/magmus/2.1")
def test_magmus_tg_moze_wywolac_pillage(registry: StaticDataRegistry) -> None:
    state = _magmus_state()
    state.players["p2"].faction = "mentak"
    state.players["p1"].trade_goods = 2
    state.systems[PLAIN].space_units = {"p1": {"destroyer": 1}}
    state.systems[RIVAL].space_units = {"p2": {"cruiser": 1}}  # sąsiedzi (102-103)
    command_tokens.spend_strategy_token(state, "p1")
    state = _accept(state, "p1", "Magmus")
    assert state.players["p1"].trade_goods == 3
    assert any("Pillage" in o.label for o in triggers.offers_for(state, "p2"))


# ================================================================================ Nova Seed


def _hero_state() -> GameState:
    state = _state()
    state.players["p1"].leader_states[muaat.HERO] = "unlocked"
    return state


def _arrive(state: GameState, position: str, source: str = HOME, kind: str = "tactical") -> None:
    """War sun Muaat wlatuje do ``position`` (ruch już wykonany) - zdarzenie po ruchu."""
    state.systems[source].space_units["p1"].pop("warsun", None)
    state.systems[position].space_units.setdefault("p1", {})["warsun"] = 1
    movement.fire_ships_moved(state, "p1", position, source, {"warsun": 1}, kind=kind)


@ruling("leaders:muaathero#1", "leaders:muaathero#2", "F_muaat/adjudicator-baal-nova-seed/3")
def test_nova_seed_niszczy_i_zamienia_kafel(registry: StaticDataRegistry) -> None:
    state = _hero_state()
    rival = state.systems[RIVAL]
    rival.space_units = {"p2": {"carrier": 1, "fighter": 2}}
    rival.planet_units = {THIBAH: {"p2": {"infantry": 2, "pds": 1}}}
    rival.command_tokens = ["p2", "p1"]
    rival.frontier_token = True
    rival.wormhole_tokens = ["GAMMA"]
    _arrive(state, RIVAL)
    after = _accept(state, "p1", "Nova Seed")
    system = after.systems[RIVAL]
    assert system.system_id == muaat.NOVA_SEED_TILE and after.replaced_tiles == {RIVAL: "81"}
    assert system.space_units.get("p2") in (None, {})
    assert THIBAH not in system.planet_units and THIBAH not in system.planet_owners
    assert THIBAH not in after.players["p2"].controlled_planets  # karta planety purge
    assert system.space_units["p1"] == {"warsun": 1}
    assert system.command_tokens == ["p2", "p1"] and system.frontier_token  # żetony zostają
    assert system.wormhole_tokens == []  # pozostałe żetony przepadają
    assert after.players["p1"].leader_states[muaat.HERO] == "purged"
    assert "SUPERNOVA" in _grid(after, registry).anomalies_at(RIVAL)


def test_nova_seed_sily_muaat_z_planety_do_przestrzeni(registry: StaticDataRegistry) -> None:
    """⚠️ ZAŁOŻENIE (RULES.md 62.13): siły naziemne Muaat -> przestrzeń, struktury -> rezerwa."""
    state = _hero_state()
    state.systems[PLAIN].planet_units = {VEFUTII: {"p1": {"infantry": 2, "pds": 1}}}
    state.systems[PLAIN].planet_owners = {VEFUTII: "p1"}
    state.players["p1"].controlled_planets.append(VEFUTII)
    _arrive(state, PLAIN)
    after = _accept(state, "p1", "Nova Seed")
    assert after.systems[PLAIN].space_units["p1"] == {"warsun": 1, "infantry": 2}
    assert VEFUTII not in after.players["p1"].controlled_planets


@ruling("F_muaat/adjudicator-baal-nova-seed/1")
def test_nova_seed_po_odwrocie(registry: StaticDataRegistry) -> None:
    state = _hero_state()
    state.systems[HOME].space_units = {}
    state.systems[PLAIN].space_units = {"p1": {"warsun": 1}, "p2": {"dreadnought": 1}}
    state.systems[RIVAL].space_units = {"p1": {"destroyer": 1}}
    grid = _grid(state, registry)
    after, _ = retreat.perform_retreat(state, grid, registry, PLAIN, "p1", RIVAL)
    assert after.systems[RIVAL].space_units["p1"]["warsun"] == 1
    assert _offers(after, "p1", "Nova Seed")


@ruling("F_muaat/adjudicator-baal-nova-seed/2")
def test_nova_seed_war_sun_musi_przyleciec_z_innego_systemu(registry: StaticDataRegistry) -> None:
    state = _hero_state()
    state.systems[PLAIN].space_units = {"p1": {"warsun": 1}}
    movement.fire_ships_moved(state, "p1", PLAIN, PLAIN, {"warsun": 1})
    assert not _offers(state, "p1", "Nova Seed")
    movement.fire_ships_moved(state, "p1", PLAIN, HOME, {"destroyer": 1})  # bez war suna
    assert not _offers(state, "p1", "Nova Seed")


@ruling("F_muaat/adjudicator-baal-nova-seed/6", "leaders:muaathero#1")
def test_nova_seed_nie_w_dom_mecatol_ani_dom_wyeliminowanego(registry: StaticDataRegistry) -> None:
    state = _hero_state()
    state.systems["000"].space_units = {}
    _arrive(state, "000")
    assert not _offers(state, "p1", "Nova Seed")  # Mecatol Rex
    state = _hero_state()
    state.eliminated_players = [EliminatedPlayer(player_id="p3", faction="hacan",
                                                 home_position=FAR)]
    _arrive(state, FAR)
    assert not _offers(state, "p1", "Nova Seed")
    state = _hero_state()
    state.players["p2"].home_position = RIVAL
    _arrive(state, RIVAL)
    assert not _offers(state, "p1", "Nova Seed")


@ruling("F_muaat/adjudicator-baal-nova-seed/7")
def test_nova_seed_na_creuss_gate(registry: StaticDataRegistry) -> None:
    state = _hero_state()
    state.systems[FAR].system_id = "17"  # Creuss Gate (nie system domowy)
    _arrive(state, FAR)
    assert _offers(state, "p1", "Nova Seed")


@ruling("F_muaat/adjudicator-baal-nova-seed/4")
def test_jednostki_muaat_wylatuja_z_supernowej_bez_reaktora(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[NOVA].space_units = {"p1": {"destroyer": 1}}
    state.active_system = FAR
    grid = _grid(state, registry)
    assert movement.shortest_legal_path(
        grid, state, NOVA, FAR, "p1", can_enter_asteroids=False
    ) == [NOVA, FAR]


@ruling("F_muaat/adjudicator-baal-nova-seed/5")
def test_nova_seed_z_reaktorem_produkcja_w_nowej_supernowej(registry: StaticDataRegistry) -> None:
    state = _hero_state()
    state.players["p1"].technologies = ["mr"]
    state.active_system = PLAIN
    _arrive(state, PLAIN)
    after = _accept(state, "p1", "Nova Seed")
    found = production.producers(after, registry, "p1", PLAIN)
    assert any(p.value == 5 for p in found)


def test_wymiana_kafla_cofa_sie_na_mapie_przy_undo(registry: StaticDataRegistry) -> None:
    """Mapa aplikacji (HexGrid) idzie za ``replaced_tiles`` - także po cofnięciu stanu."""
    state = _state()
    grid = _grid(state, registry)
    swapped = state.clone()
    tile_swap.replace_tile(swapped, registry, PLAIN, "81")
    tile_swap.sync_grid(grid, swapped, registry)
    assert grid.system_id_at(PLAIN) == "81" and "SUPERNOVA" in grid.anomalies_at(PLAIN)
    tile_swap.sync_grid(grid, state, registry)  # Undo
    assert grid.system_id_at(PLAIN) == "20" and grid.tile_originals == {}


# ===================================================================== Fires of the Gashlai


def _fires_state() -> GameState:
    state = _state()
    state.active_player_id = "p2"
    state.players["p2"].private.promissory_notes = ["fires"]
    state.players["p1"].fleet_cc = 3
    return state


@ruling("promissory_notes:fires#1", "promissory_notes:fires#2", "promissory_notes:fires#3")
def test_fires_of_the_gashlai(registry: StaticDataRegistry) -> None:
    state = _fires_state()
    after, implemented = promissory_play.play(state, registry, "p2", "fires")
    assert implemented
    assert "ws" in after.players["p2"].technologies
    assert after.players["p1"].fleet_cc == 2 and after.players["p1"].cc_reinf == 9
    assert "fires" in after.players["p1"].private.promissory_notes
    assert "fires" not in after.players["p2"].private.promissory_notes


@ruling("F_muaat/fires-of-the-gashlai/1")
def test_fires_niedostepna_z_technologia_war_suna(registry: StaticDataRegistry) -> None:
    state = _fires_state()
    state.players["p2"].technologies = ["ws"]
    with pytest.raises(ValueError, match="already own"):
        promissory_play.play(state, registry, "p2", "fires")


# ========================================================================= Stellar Genesis


@ruling("breakthroughs:muaatbt#1", "breakthroughs:muaatbt#2", "F_muaat/stellar-genesis/1")
def test_stellar_genesis_kladzie_avernus(registry: StaticDataRegistry) -> None:
    state = _state()
    breakthrough.unlock_breakthrough(state, registry, "p1")
    options = muaat.genesis_systems(state, registry, "p1")
    assert HOME not in options and PLAIN in options  # obok planety Muaat, nie dom
    state = _accept(state, "p1", "Stellar Genesis", {"position": PLAIN})
    system = state.systems[PLAIN]
    assert "avernus" in system.added_planets and system.planet_owners["avernus"] == "p1"
    assert "avernus" in state.players["p1"].controlled_planets
    assert "avernus" not in state.players["p1"].exhausted_planets
    ex = state.exploration
    assert ex is not None and ex.player_id == "p1"  # eksploracja Avernus (stellar-genesis 1)


@ruling("breakthroughs:muaatbt#1")
def test_stellar_genesis_wybor_zawsze_na_mapie(registry: StaticDataRegistry) -> None:
    """Jedna legalna opcja też jest decyzją gracza (klik na mapie, nic po cichu)."""
    state = _state()
    inputs = muaat.genesis_inputs(state, registry, "p1", {})
    assert inputs[0]["always"] is True


def _avernus_state(owner: str = "p1") -> GameState:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.systems[PLAIN].added_planets = ["avernus"]
    state.systems[PLAIN].planet_owners = {"avernus": owner}
    state.players[owner].controlled_planets.append("avernus")
    state.systems[PLAIN].space_units = {"p1": {"warsun": 1}}
    state.systems[HOME].space_units = {}
    return state


@ruling("breakthroughs:muaatbt#3", "F_muaat/stellar-genesis/2", "F_muaat/stellar-genesis/3",
        "F_muaat/stellar-genesis/4")
def test_avernus_leci_z_war_sunem(registry: StaticDataRegistry) -> None:
    state = _avernus_state(owner="p2")
    state.systems[PLAIN].planet_units = {"avernus": {"p2": {"pds": 1, "infantry": 1}}}
    state.systems[RIVAL].space_units = {"p2": {"carrier": 1}}  # cudze jednostki w celu (3)
    state.systems[PLAIN].space_units["p1"].pop("warsun")
    state.systems[RIVAL].space_units["p1"] = {"warsun": 1}
    movement.fire_ships_moved(state, "p1", RIVAL, PLAIN, {"warsun": 1})
    after = _accept(state, "p1", "move Avernus")
    assert "avernus" in after.systems[RIVAL].added_planets
    assert "avernus" not in after.systems[PLAIN].added_planets
    assert after.systems[RIVAL].planet_owners["avernus"] == "p2"  # kontroler bez zmian (2)
    assert after.systems[RIVAL].planet_units["avernus"]["p2"] == {"pds": 1, "infantry": 1}


@ruling("F_muaat/stellar-genesis/4.1", "F_muaat/stellar-genesis/4.2")
def test_struktury_na_avernus_dzialaja_po_przelocie(registry: StaticDataRegistry) -> None:
    """Przelot przez system Avernus: PDS strzela w Space Cannon Offense, dok produkuje w celu."""
    from src.core import space_cannon

    state = _avernus_state()
    state.systems[PLAIN].planet_units = {"avernus": {"p1": {"pds": 1, "spacedock": 1}}}
    state.systems[PLAIN].space_units = {}
    state.systems[RIVAL].space_units = {"p1": {"warsun": 1}}
    state.active_system = RIVAL
    movement.fire_ships_moved(state, "p1", RIVAL, HOME, {"warsun": 1}, route=[HOME, PLAIN, RIVAL])
    after = _accept(state, "p1", "move Avernus")
    shooters = space_cannon.offense_shooters(after, _grid(after, registry), registry, "p1")
    assert any(s.zone == "avernus" for s in shooters)
    assert any(p.zone == "avernus" for p in production.producers(after, registry, "p1", RIVAL))


def test_avernus_nie_do_systemu_domowego(registry: StaticDataRegistry) -> None:
    state = _avernus_state()
    state.systems[PLAIN].space_units = {}
    state.systems[HOME].space_units = {"p1": {"warsun": 1}}
    movement.fire_ships_moved(state, "p1", HOME, PLAIN, {"warsun": 1})
    assert not _offers(state, "p1", "move Avernus")


@ruling("leaders:muaathero#unlock")
def test_bohater_odblokowanie_3_cele(registry: StaticDataRegistry) -> None:
    """Bohater: „Have 3 scored objectives.” (predykat ogólny z ``leaders``)."""
    unlock = leaders.unlock_predicate(registry, muaat.HERO)
    assert unlock is not None
    state = _state()
    state.players["p1"].scored_secrets = ["a", "b"]
    assert not unlock(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert unlock(state, registry, "p1")
