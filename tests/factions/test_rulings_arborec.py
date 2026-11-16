"""The Arborec — rulingi ``docs/rules_tirules/F_arborec.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Podstawowe testy komponentów są w ``test_arborec.py``
(tam też część znaczników). Statusy bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    faction_components,
    production,
    promissory_play,
    rules_hooks,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count, set_damaged
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import arborec
from src.core.production import ProductionOrder
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause
from tests.factions.test_arborec import _accept, _ground, _labels, _moved_into, _state
from tests.factions.test_arborec import _grid as _grid  # noqa: F401 - fixture autouse (mapa demo)
from tests.rulings import ruling
from tests.test_technologies_passive import _infantry_state

TWO_PLANETS = "104"  # pozycja na mapie demo; kafel "10" = Arc Prime + Wren Terra
DOCK_PLANET = "arcprime"
OTHER_PLANET = "wrenterra"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(scope="module")
def grid(registry: StaticDataRegistry) -> HexGrid:
    return build_demo_grid(registry)


def _two_planet_state(
    units: dict[str, dict[str, int]], *, active: str = "p1", trade_goods: int = 20
) -> GameState:
    """Arborec kontroluje obie planety kafla ``10`` (pozycja 104), to aktywny system."""
    state = _state()
    state.active_player_id = active
    state.active_system = TWO_PLANETS
    state.players["p1"].trade_goods = trade_goods
    state.systems[TWO_PLANETS] = SystemState(
        position=TWO_PLANETS, system_id="10",
        planet_owners={DOCK_PLANET: "p1", OTHER_PLANET: "p1"},
        planet_units={planet: {"p1": dict(by_type)} for planet, by_type in units.items()},
    )
    return state


def _budget_drop(
    registry: StaticDataRegistry, before: GameState, after: GameState
) -> int:
    return production.available_budget(before, registry, "p1") - production.available_budget(
        after, registry, "p1"
    )


# ===================================================================================== Mitosis


@ruling("F_arborec/mitosis/1")
def test_piechota_letani_na_planete_doku_bez_letani(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _two_planet_state({DOCK_PLANET: {"spacedock": 1}, OTHER_PLANET: {"infantry": 2}})
    after = production.produce(state, grid, registry, "p1", [
        ProductionOrder("destroyer", 1),
        ProductionOrder("infantry", 2, zone=DOCK_PLANET),  # PRODUCTION piechoty z Wren Terra
    ])
    assert _ground(after, TWO_PLANETS, DOCK_PLANET) == {"spacedock": 1, "infantry": 2}
    assert _ground(after, TWO_PLANETS, OTHER_PLANET) == {"infantry": 2}


@ruling("F_arborec/mitosis/2", "F_arborec/letani-behemoth/1")
def test_doki_produkuja_letani_behemoth_ale_nie_piechote(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _two_planet_state({DOCK_PLANET: {"spacedock": 1}})
    after = production.produce(
        state, grid, registry, "p1", [ProductionOrder("mech", 1, zone=DOCK_PLANET)]
    )
    assert _ground(after, TWO_PLANETS, DOCK_PLANET) == {"spacedock": 1, "mech": 1}
    with pytest.raises(ValueError, match="cannot produce them"):
        production.validate_production(
            state, grid, registry, "p1", [ProductionOrder("infantry", 1, zone=DOCK_PLANET)]
        )


@ruling("F_arborec/mitosis/3", "abilities:mitosis#1")
def test_mitosis_obowiazkowa_nie_da_sie_odrzucic() -> None:
    state = _state()
    state.systems["103"].planet_owners = {"meer": "p1"}  # dwie planety = prawdziwy wybór
    triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "status"})
    offer = next(o for o in state.pending_offers if o.player_id == "p1")
    assert offer.mandatory
    with pytest.raises(ValueError, match="mandatory"):
        triggers.decline_offer(state, "p1", offer.id)


# ===================================================================================== Stymie Ω


def _stymie_state() -> GameState:
    """p2 rusza się do systemu z piechotą p1 (Letnev, trzyma Stymie); p3 = Arborec."""
    state = _state()
    _moved_into(state)
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 1}}}
    state.players["p1"].faction = "letnev"
    state.players["p3"] = PlayerState(player_id="p3", color="red", faction="arborec")
    state.players["p1"].private.promissory_notes = ["stymie"]
    return state


@ruling("F_arborec/stymie-omega/2")
def test_stymie_nie_w_systemie_domowym_gracza_bez_jednostek(
    registry: StaticDataRegistry,
) -> None:
    """Dom gracza przy stole pozostaje domem, nawet gdy nie ma w nim nic (eliminacja nie zdejmuje
    gracza ze stołu - jego system domowy nadal jest wyłączony z celów Stymie)."""
    state = _stymie_state()
    sol_home = registry.factions["sol"].home_system or ""
    state.systems["105"] = SystemState(position="105", system_id=sol_home)  # pusty dom p2
    options = [o["value"] for o in arborec.stymie_inputs(state, registry, "p1")[0]["options"]]
    assert "105" not in options and "103" in options
    with pytest.raises(ValueError, match="(?i)non-home"):
        promissory_play.play(state, registry, "p1", "stymie", {"system": "105"})


# =============================================================================== Bioplasmosis


A, B, C = "101", "102", "103"  # A-B-C: A i C nie sąsiadują (mapa demo)
PLANET = {A: "lodor", B: "industrex", C: "meer"}


def _chain(infantry: dict[str, int], mech_on_a: int = 0) -> GameState:
    state = _state()
    state.players["p1"].technologies = ["bio"]
    state.systems[A] = SystemState(position=A, system_id="26")
    for position, planet in PLANET.items():
        system = state.systems[position]
        system.planet_owners = {planet: "p1"}
        units = {"infantry": infantry.get(position, 0)} if infantry.get(position) else {}
        if position == A and mech_on_a:
            units["mech"] = mech_on_a
        system.planet_units = {planet: {"p1": units}} if units else {}
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    return state


def _key(src: str, dst: str) -> str:
    return f"bio:{src}:{PLANET[src]}:{dst}:{PLANET[dst]}"


def _bio(state: GameState, registry: StaticDataRegistry, moves: dict[str, int]) -> GameState:
    inputs = arborec.bio_inputs(state, registry, "p1", {})
    params: dict[str, Any] = {item["key"]: 0 for item in inputs}
    for key, count in moves.items():
        assert key in params, key
        params[key] = count
    return _accept(state, "p1", "Bioplasmosis", params)


def _inf(state: GameState, position: str) -> int:
    return _ground(state, position, PLANET[position]).get("infantry", 0)


@ruling("F_arborec/bioplasmosis/1", "F_arborec/bioplasmosis/1.1")
def test_bioplasmosis_bez_ruchu_przez_dwa_systemy(registry: StaticDataRegistry) -> None:
    state = _chain({A: 1})
    keys = {item["key"] for item in arborec.bio_inputs(state, registry, "p1", {})}
    assert _key(A, C) not in keys  # tylko ten sam albo sąsiedni system
    assert not any(k.startswith(f"bio:{B}:") for k in keys)  # B nie ma piechoty PRZED ruchem
    after = _bio(state, registry, {_key(A, B): 1})
    assert (_inf(after, A), _inf(after, B), _inf(after, C)) == (0, 1, 0)


@ruling("F_arborec/bioplasmosis/1", "F_arborec/bioplasmosis/1.2")
def test_bioplasmosis_a_do_b_i_b_do_c(registry: StaticDataRegistry) -> None:
    after = _bio(_chain({A: 1, B: 1}), registry, {_key(A, B): 1, _key(B, C): 1})
    assert (_inf(after, A), _inf(after, B), _inf(after, C)) == (0, 1, 1)


@ruling("F_arborec/bioplasmosis/1.3")
def test_bioplasmosis_a_i_c_do_b(registry: StaticDataRegistry) -> None:
    after = _bio(_chain({A: 1, C: 1}), registry, {_key(A, B): 1, _key(C, B): 1})
    assert (_inf(after, A), _inf(after, B), _inf(after, C)) == (0, 2, 0)


@ruling("F_arborec/bioplasmosis/1.4")
def test_bioplasmosis_b_do_a_i_c(registry: StaticDataRegistry) -> None:
    after = _bio(_chain({B: 2}), registry, {_key(B, A): 1, _key(B, C): 1})
    assert (_inf(after, A), _inf(after, B), _inf(after, C)) == (1, 0, 1)


@ruling("F_arborec/bioplasmosis/1.5")
def test_bioplasmosis_zamiana_bez_skutku(registry: StaticDataRegistry) -> None:
    after = _bio(_chain({A: 1, B: 1}), registry, {_key(A, B): 1, _key(B, A): 1})
    assert (_inf(after, A), _inf(after, B), _inf(after, C)) == (1, 1, 0)


@ruling("F_arborec/bioplasmosis/2")
def test_bioplasmosis_nie_rusza_letani_behemoth(registry: StaticDataRegistry) -> None:
    state = _chain({A: 1}, mech_on_a=1)
    route = next(
        i for i in arborec.bio_inputs(state, registry, "p1", {}) if i["key"] == _key(A, B)
    )
    assert route["max"] == 1  # liczy się tylko piechota
    after = _bio(state, registry, {_key(A, B): 1})
    assert _ground(after, A, PLANET[A]) == {"mech": 1}


# =========================================================================== Letani Warrior


@ruling("technologies:lw2#1", "technologies:lw2#2")
def test_letani_warrior_ii_statystyki_z_karty(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "arborec", ["lw2"], "infantry")
    assert unit is not None
    assert (unit.cost, unit.combat_hits_on, unit.production_value) == (0.5, 7, 2)


@ruling("F_arborec/letani-warrior/2")
def test_produkcja_letani_sumuje_sie(registry: StaticDataRegistry, grid: HexGrid) -> None:
    state = _two_planet_state({OTHER_PLANET: {"infantry": 2}})
    assert production.production_limit(state, grid, registry, "p1") == 2
    orders = [ProductionOrder("infantry", 2, zone=OTHER_PLANET)]
    assert production.order_cost(state, registry, "p1", orders) == 1  # 2 sztuki za 1 zasób
    after = production.produce(state, grid, registry, "p1", orders)
    assert _ground(after, TWO_PLANETS, OTHER_PLANET) == {"infantry": 4}


@ruling("F_arborec/letani-warrior/3")
def test_produkcja_letani_dowolny_podzial_miedzy_planety(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _two_planet_state({DOCK_PLANET: {"infantry": 1}, OTHER_PLANET: {"infantry": 1}})
    after = production.produce(
        state, grid, registry, "p1", [ProductionOrder("infantry", 2, zone=DOCK_PLANET)]
    )
    assert _ground(after, TWO_PLANETS, DOCK_PLANET) == {"infantry": 3}


@ruling("technologies:lw2#3", "technologies:lw2#4")
def test_letani_warrior_ii_rzut_po_zniszczeniu() -> None:
    state = _infantry_state(["lw2"])
    state.players["p1"].faction = "arborec"
    unit_ops.remove_units(
        state, state.systems["101"], "pl", "p1", "infantry", 12, UnitCause.DESTROYED
    )
    roll = state.table_roll
    assert roll is not None and len(roll["dice"]) == 12 and roll["hitsOn"] == 6
    revived = sum(1 for d in roll["dice"] if d >= 6)
    assert state.players["p1"].infantry_ii_on_card == revived > 0


@ruling("technologies:lw2#5")
def test_letani_warrior_ii_wraca_na_poczatku_tury() -> None:
    state = _infantry_state(["lw2"])
    state.players["p1"].faction = "arborec"
    state.players["p1"].infantry_ii_on_card = 2
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    assert state.players["p1"].infantry_ii_on_card == 0
    assert state.systems["000"].planet_units["hp"]["p1"] == {"infantry": 2}


# ======================================================== granty: flagowiec, commander, bohater


def _flagship_grant(state: GameState) -> GameState:
    state.systems[state.active_system or ""].space_units = {"p1": {"flagship": 1}}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": state.active_system})
    return _accept(state, "p1", "Duha Menaimon")


def _commander_grant(state: GameState) -> GameState:
    state.players["p1"].leader_states = {"arboreccommander": "unlocked"}
    state.active_player_id = "p2"
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": state.active_system})
    return _accept(state, "p1", "Dirzuga")


def _hero_grant(state: GameState, registry: StaticDataRegistry) -> GameState:
    state.players["p1"].leader_states = {"arborechero": "unlocked"}
    after, _ = faction_components.play(
        state, registry, "p1", "leader", "arborechero", {"systems": [state.active_system]}
    )
    return after


def _grant(kind: str, state: GameState, registry: StaticDataRegistry) -> GameState:
    if kind == "flagship":
        return _flagship_grant(state)
    if kind == "commander":
        return _commander_grant(state)
    return _hero_grant(state, registry)


_GRANT_RULINGS = {
    "flagship": ("F_arborec/duha-menaimon/1", "F_arborec/duha-menaimon/2"),
    "commander": ("F_arborec/dirzuga-rophal/1", "F_arborec/dirzuga-rophal/3"),
    "hero": (
        "F_arborec/letani-miasmiala-ultrasonic-emitter/1",
        "F_arborec/letani-miasmiala-ultrasonic-emitter/3",
    ),
}


@ruling(*(rid for ids in _GRANT_RULINGS.values() for rid in ids))
@pytest.mark.parametrize("kind", sorted(_GRANT_RULINGS))
def test_produkcja_z_efektu_platna_bez_sarween(
    kind: str, registry: StaticDataRegistry, grid: HexGrid
) -> None:
    """Jednostki płatne; to nie jest użycie PRODUCTION, więc Sarween Tools nie obniża kosztu."""
    state = _two_planet_state({DOCK_PLANET: {"spacedock": 1, "infantry": 1}})
    state.players["p1"].technologies = ["st"]
    orders = [ProductionOrder("destroyer", 1)]
    assert production.order_cost(state, registry, "p1", orders) == 0  # kontrola: zwykła produkcja
    granted = _grant(kind, state, registry)
    assert granted.production_grant is not None
    assert production.order_cost(granted, registry, "p1", orders) == 1
    after = production.produce(granted, grid, registry, "p1", orders)
    assert _budget_drop(registry, granted, after) >= 1
    assert after.systems[TWO_PLANETS].space_units["p1"]["destroyer"] == 1


@ruling("F_arborec/duha-menaimon/2")
def test_duha_menaimon_nie_ma_production(registry: StaticDataRegistry) -> None:
    """Sam flagowiec nie jest producentem (także dla eliminacji - R_elimination)."""
    state = _state()
    state.systems["102"].space_units = {"p1": {"flagship": 1}}
    assert production.producers(state, registry, "p1", "102") == []


@ruling("F_arborec/duha-menaimon/3")
def test_duha_menaimon_wprowadzony_pozniej_nie_dziala() -> None:
    state = _state()
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "102"})
    unit_ops.place_units(state, state.systems["102"], "space", "p1", "flagship", 1,
                         UnitCause.MOVED)
    triggers.fire(state, GameEvent.SHIPS_MOVED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "102"})
    assert not any("Duha" in label for label in _labels(state, "p1"))


# ---------------------------------------------------------------------- ruch / blokada statków


@ruling("F_arborec/dirzuga-rophal/2")
def test_dirzuga_rophal_statek_gdy_obcych_statkow_jeszcze_nie_ma(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _two_planet_state({DOCK_PLANET: {"spacedock": 1}})
    state.systems["103"].space_units = {"p2": {"cruiser": 1}}  # p2 jeszcze się nie ruszył
    granted = _commander_grant(state)
    after = production.produce(granted, grid, registry, "p1", [ProductionOrder("destroyer", 1)])
    assert after.systems[TWO_PLANETS].space_units["p1"] == {"destroyer": 1}
    blocked = _two_planet_state({DOCK_PLANET: {"spacedock": 1}})
    blocked.systems[TWO_PLANETS].space_units = {"p2": {"cruiser": 1}}
    granted = _commander_grant(blocked)
    with pytest.raises(ValueError, match="enemy ships"):
        production.validate_production(
            granted, grid, registry, "p1", [ProductionOrder("destroyer", 1)]
        )


@ruling("F_arborec/letani-miasmiala-ultrasonic-emitter/2")
def test_ultrasonic_emitter_statki_tylko_bez_obcych_statkow(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _two_planet_state({DOCK_PLANET: {"infantry": 1}})
    state.systems[TWO_PLANETS].space_units = {"p2": {"cruiser": 1}}
    granted = _hero_grant(state, registry)
    with pytest.raises(ValueError, match="enemy ships"):
        production.validate_production(
            granted, grid, registry, "p1", [ProductionOrder("destroyer", 1)]
        )
    production.validate_production(  # siły naziemne nadal wolno
        granted, grid, registry, "p1", [ProductionOrder("infantry", 1, zone=DOCK_PLANET)]
    )


# ------------------------------------------------------------------ typy i miejsca postawienia


@ruling("F_arborec/dirzuga-rophal/4")
def test_dirzuga_rophal_piechota_gdy_produkuje_tylko_dok(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _two_planet_state({DOCK_PLANET: {"spacedock": 1}})
    granted = _commander_grant(state)
    after = production.produce(
        granted, grid, registry, "p1", [ProductionOrder("infantry", 1, zone=DOCK_PLANET)]
    )
    assert _ground(after, TWO_PLANETS, DOCK_PLANET) == {"spacedock": 1, "infantry": 1}


@ruling("F_arborec/dirzuga-rophal/5", "F_arborec/letani-miasmiala-ultrasonic-emitter/4")
@pytest.mark.parametrize("kind", ["commander", "hero"])
@pytest.mark.parametrize("zone", [OTHER_PLANET, "space"])
def test_sily_naziemne_na_dowolna_planete_albo_w_przestrzen(
    kind: str, zone: str, registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _two_planet_state({DOCK_PLANET: {"spacedock": 1, "infantry": 1}})
    granted = _grant(kind, state, registry)
    after = production.produce(
        granted, grid, registry, "p1", [ProductionOrder("infantry", 1, zone=zone)]
    )
    units = (
        after.systems[TWO_PLANETS].space_units["p1"]
        if zone == "space"
        else _ground(after, TWO_PLANETS, zone)
    )
    assert units == {"infantry": 1}


@ruling("F_arborec/dirzuga-rophal/6")
def test_dirzuga_rophal_jednostka_z_planszy_nieuszkodzona(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _two_planet_state({DOCK_PLANET: {"spacedock": 1}})
    cap = production.reinforcements_left(state, "p1", "destroyer")
    assert cap is not None and cap > 0
    source = state.systems["103"]
    source.space_units = {"p1": {"destroyer": cap}}  # cała rezerwa na planszy, uszkodzona
    set_damaged(source, "space", "p1", "destroyer", cap)
    granted = _commander_grant(state)
    with pytest.raises(ValueError, match="reinforcements"):
        production.produce(granted, grid, registry, "p1", [ProductionOrder("destroyer", 1)])
    after = production.produce(
        granted, grid, registry, "p1", [ProductionOrder("destroyer", 1, sources=("103|space",))]
    )
    target = after.systems[TWO_PLANETS]
    assert target.space_units["p1"] == {"destroyer": 1}
    assert damaged_count(target, "space", "p1", "destroyer") == 0
    assert after.systems["103"].space_units["p1"]["destroyer"] == cap - 1
    granted.systems["103"].command_tokens = ["p1"]  # system z własnym żetonem odpada
    with pytest.raises(ValueError):
        production.produce(
            granted, grid, registry, "p1",
            [ProductionOrder("destroyer", 1, sources=("103|space",))],
        )


# ============================================================================== Letani Ospha


def _ospha(state: GameState, registry: StaticDataRegistry) -> GameState:
    used, _ = faction_components.play(
        state, registry, "p1", "leader", "arborecagent", {"ship": "p2|102|destroyer"}
    )
    return used


@ruling("F_arborec/letani-ospha/1")
def test_letani_ospha_bez_zniszczenia_i_produkcji(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state()
    state.systems["102"].space_units = {"p2": {"destroyer": 1}}
    used = _ospha(state, registry)
    seen: list[GameEvent] = []
    fire = triggers.fire

    def spy(st: GameState, event: GameEvent, moment: Moment, *args: Any, **kwargs: Any) -> Any:
        seen.append(event)
        return fire(st, event, moment, *args, **kwargs)

    monkeypatch.setattr(triggers, "fire", spy)
    after = _accept(used, "p2", "Letani Ospha", {"replacement": "cruiser"})
    assert after.systems["102"].space_units["p2"] == {"cruiser": 1}
    banned = {GameEvent.UNIT_DESTROYED, GameEvent.UNITS_PRODUCED, GameEvent.PRODUCTION_USED}
    assert not banned & set(seen)


@ruling("F_arborec/letani-ospha/1.1")
def test_letani_ospha_sarween_nie_podnosi_limitu(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].technologies = ["st"]
    state.systems["102"].space_units = {"p2": {"destroyer": 1}}
    used = _ospha(state, registry)
    with pytest.raises(ValueError):  # niszczyciel 1 + 2 < pancernik 4, Sarween nic nie zmienia
        _accept(used, "p2", "Letani Ospha", {"replacement": "dreadnought"})


@ruling("F_arborec/letani-ospha/2")
def test_letani_ospha_statek_z_planszy_nieuszkodzony(registry: StaticDataRegistry) -> None:
    state = _state()
    cap = production.reinforcements_left(state, "p2", "cruiser")
    assert cap is not None and cap > 0
    state.systems["102"].space_units = {"p2": {"destroyer": 1}}
    source = state.systems["103"]
    source.space_units = {"p2": {"cruiser": cap}}
    set_damaged(source, "space", "p2", "cruiser", cap)
    used = _ospha(state, registry)
    after = _accept(used, "p2", "Letani Ospha", {"replacement": "cruiser@103"})
    assert after.systems["102"].space_units["p2"] == {"cruiser": 1}
    assert damaged_count(after.systems["102"], "space", "p2", "cruiser") == 0
    used.systems["103"].command_tokens = ["p2"]  # z systemu z żetonem właściciela - nie
    options = arborec.ospha_inputs(
        used, registry, "p2", {"base_type": "destroyer", "position": "102"}
    )[0]["options"]
    assert "cruiser@103" not in [o["value"] for o in options]


@ruling("F_arborec/letani-ospha/3")
def test_letani_ospha_mysliwiec_jako_zamiennik(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units = {"p2": {"destroyer": 1}}
    used = _ospha(state, registry)
    after = _accept(used, "p2", "Letani Ospha", {"replacement": "fighter"})
    assert after.systems["102"].space_units["p2"] == {"fighter": 1}


# ============================================================ poprawki po audycie (2026-11-16)


@ruling("F_arborec/mitosis/1")
def test_piechota_letani_nie_na_planete_bezczynnego_doku(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    """Dok nic nie produkuje → jego planeta nie przyjmuje piechoty z Letani Warrior."""
    state = _two_planet_state({DOCK_PLANET: {"spacedock": 1}, OTHER_PLANET: {"infantry": 2}})
    with pytest.raises(ValueError, match="must also produce"):
        production.produce(
            state, grid, registry, "p1", [ProductionOrder("infantry", 2, zone=DOCK_PLANET)]
        )
    after = production.produce(  # na planetę z Letani Warrior - zawsze wolno
        state, grid, registry, "p1", [ProductionOrder("infantry", 2, zone=OTHER_PLANET)]
    )
    assert _ground(after, TWO_PLANETS, OTHER_PLANET) == {"infantry": 4}
    # Dok produkuje w tej samej akcji (wcześniejsze zamówienie) → piechota może stanąć przy nim.
    docked = production.produce(state, grid, registry, "p1", [ProductionOrder("destroyer", 1)])
    final = production.produce(
        docked, grid, registry, "p1", [ProductionOrder("infantry", 2, zone=DOCK_PLANET)]
    )
    assert _ground(final, TWO_PLANETS, DOCK_PLANET) == {"spacedock": 1, "infantry": 2}


@ruling("units:arborec_mech#1")
def test_letani_behemoth_zastepuje_piechote_w_przestrzeni(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["103"].space_units = {"p1": {"infantry": 1, "carrier": 1}}
    triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "status"})
    offer = next(o for o in state.pending_offers if o.player_id == "p1")
    values = [o["value"] for o in arborec.mitosis_inputs(state, registry, "p1", {})[0]["options"]]
    assert "mech|103|space" in values
    after = triggers.accept_offer(state, "p1", offer.id, {"mitosis": "mech|103|space"})
    assert after.systems["103"].space_units["p1"] == {"carrier": 1, "mech": 1}


@ruling("technologies:lw2#5")
def test_letani_warrior_ii_kazda_sztuka_na_wybrana_planete(registry: StaticDataRegistry) -> None:
    state = _infantry_state(["lw2"])
    state.players["p1"].faction = "arborec"
    state.players["p1"].controlled_planets = []
    state.systems["000"].planet_owners = {"hp": "p1", "hq": "p1"}
    state.players["p1"].infantry_ii_on_card = 3
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    offer = next(o for o in state.pending_offers if o.player_id == "p1")
    after = triggers.accept_offer(
        state, "p1", offer.id, {"planet_1": "hp", "planet_2": "hq", "planet_3": "hq"}
    )
    assert after.systems["000"].planet_units["hp"]["p1"] == {"infantry": 1}
    assert after.systems["000"].planet_units["hq"]["p1"] == {"infantry": 2}
