"""The Federation of Sol — rulingi ``docs/rules_tirules/F_sol.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Podstawowe testy komponentów są w ``test_sol.py`` i
``test_flows_sol.py``. Statusy bez testu: ``tests/rulings_status.json`` (Harrow L1Z1X).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    battle,
    faction_components,
    leaders,
    production,
    promissory_play,
    rules_hooks,
    transaction,
    triggers,
    turn_flow,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, SystemState, TurnEndWindow
from src.core.hooks.factions import sol
from src.core.production import ProductionOrder
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide
from src.core.unit_ops import UnitCause
from tests.factions.flow_harness import Flow, Json
from tests.factions.test_sol import _accept, _grid, _infantry, _labels, _state
from tests.factions.test_sol import registry as registry  # noqa: F401 - fixture modułu
from tests.rulings import ruling

__all__ = ["_grid"]  # fixture autouse modułu (siatka demo)

MS = sol.MILITARY_SUPPORT


def _sol_turn_starts(state: GameState) -> GameState:
    """Pauza „początek tury Sola” (p1): p2 skończył turę, p1 jeszcze nic nie zrobił.

    p2 ma krążownik w systemie Sola (sąsiad do transakcji), notka MS jest u Sola.
    """
    state.active_player_id = "p1"
    state.turn_end_window = TurnEndWindow(ended_player="p2", next_player="p1")
    state.systems["102"].space_units = {"p1": {"carrier": 1}, "p2": {"cruiser": 1}}
    state.players["p1"].private.promissory_notes = [MS]
    return state


def _give_support(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Sol (aktywny p1) oddaje Military Support graczowi p2 w transakcji."""
    return transaction.resolve_transaction(
        state, build_demo_grid(registry), "p2", TransactionSide(promissory_note=MS),
        TransactionSide(),
    )


def _support_row(state: GameState, registry: StaticDataRegistry, player: str) -> dict[str, Any]:
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, player)}
    return rows.get(MS, {"playable": False, "reason": "not in hand"})


def _p2_holds_support(registry: StaticDataRegistry) -> GameState:
    """p2 dostał Military Support w poprzedniej turze; zaczyna się tura Sola."""
    state = _sol_turn_starts(_state())
    state.players["p1"].private.promissory_notes = []
    state.players["p2"].private.promissory_notes = [MS]
    state.systems["102"].planet_owners = {"industrex": "p2"}
    return state


# ======================================================================== Orbital Drop + mech


@ruling("abilities:orbital_drop#1")
def test_orbital_drop_tylko_wlasna_planeta_i_zeton_strategii(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].strategic_cc = 2
    tactical = state.players["p1"].tactical_cc
    after, _ = faction_components.play(
        state, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
    )
    assert _infantry(after, "p1") == 2
    assert after.players["p1"].strategic_cc == 1  # żeton z puli strategii, nie taktycznej
    assert after.players["p1"].tactical_cc == tactical
    state.systems["102"].planet_owners = {"industrex": "p2"}
    with pytest.raises(ValueError):  # „1 planet you control”
        faction_components.play(
            state, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
        )


@ruling("F_sol/orbital-drop/1")
def test_orbital_drop_wiele_razy_po_zetonie_na_uzycie(registry: StaticDataRegistry) -> None:
    """Każde użycie to osobna akcja kosztująca 1 żeton z puli strategii."""
    state = _state()
    state.players["p1"].strategic_cc = 2
    first, _ = faction_components.play(
        state, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
    )
    for offer in [o for o in first.pending_offers if o.player_id == "p1"]:
        first = triggers.decline_offer(first, "p1", offer.id)  # DEPLOY mecha - odmowa
    with pytest.raises(ValueError, match="already took an action"):  # osobna akcja każde użycie
        faction_components.play(
            first, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
        )
    first.players["p1"].took_action_this_turn = False  # kolejna tura Sola
    first.players["p1"].actions_this_turn = 0
    second, _ = faction_components.play(
        first, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
    )
    assert _infantry(second, "p1") == 4
    assert second.players["p1"].strategic_cc == 0
    with pytest.raises(ValueError):  # trzeci raz - brak żetonu
        faction_components.play(
            second, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
        )


@ruling("units:sol_mech#1")
def test_thunderbolt_mech_na_planecie_orbital_drop(registry: StaticDataRegistry) -> None:
    state = _state()
    after, _ = faction_components.play(
        state, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
    )
    with pytest.raises(ValueError):  # mniej niż 3 zasoby
        _accept(after, "p1", "Thunderbolt", {"planets": [], "trade_goods": 2})
    deployed = _accept(after, "p1", "Thunderbolt", {"planets": [], "trade_goods": 3})
    assert deployed.systems["102"].planet_units["industrex"]["p1"] == {"infantry": 2, "mech": 1}
    assert deployed.players["p1"].trade_goods == 1
    # Bez Orbital Drop (zwykłe postawienie piechoty) DEPLOY nie wyskakuje.
    plain = _state()
    unit_ops.place_units(
        plain, plain.systems["102"], "industrex", "p1", "infantry", 2, UnitCause.PLACED
    )
    assert not any("Thunderbolt" in label for label in _labels(plain, "p1"))


# ================================================================================== Versatile


@ruling("abilities:versatile#1")
def test_versatile_dodatkowy_zeton_tylko_sol() -> None:
    state = _state()
    point = rules_hooks.POINT_STATUS_COMMAND_TOKENS
    assert rules_hooks.modify(point, state, "p1", 2) == 3
    assert rules_hooks.modify(point, state, "p2", 2) == 2


@ruling("F_sol/versatile/1")
def test_versatile_z_hyper_metabolism_cztery_zetony(registry: StaticDataRegistry) -> None:
    """Hyper Metabolism (+1) i Versatile (+1) na bazowe 2 żetony = 4."""
    state = _state()
    state.players["p1"].technologies = ["hm"]
    point = rules_hooks.POINT_STATUS_COMMAND_TOKENS
    assert rules_hooks.modify(point, state, "p1", 2) == 4
    state.players["p2"].technologies = ["hm"]
    assert rules_hooks.modify(point, state, "p2", 2) == 3  # bez Versatile


# =========================================================================== Military Support


@ruling("promissory_notes:ms#1", "promissory_notes:ms#2", "promissory_notes:ms#3")
def test_military_support_zeton_sola_piechota_i_zwrot(registry: StaticDataRegistry) -> None:
    state = _p2_holds_support(registry)
    state.players["p1"].strategic_cc = 2
    reinforcements = state.players["p1"].cc_reinf
    after, _ = promissory_play.play(state, registry, "p2", MS, {"planet": "102|industrex"})
    assert after.players["p1"].strategic_cc == 1
    assert after.players["p1"].cc_reinf == reinforcements + 1  # „return it to their reinforcements”
    assert _infantry(after, "p2") == 2
    assert MS in after.players["p1"].private.promissory_notes
    assert MS not in after.players["p2"].private.promissory_notes
    # „you may place” - można zrezygnować z piechoty; żeton i tak zdjęty, karta wraca.
    skipped, _ = promissory_play.play(state, registry, "p2", MS, {"planet": "none"})
    assert skipped.players["p1"].strategic_cc == 1
    assert _infantry(skipped, "p2") == 0
    assert MS in skipped.players["p1"].private.promissory_notes


@ruling("F_sol/military-support/2")
def test_military_support_przed_orbital_drop(registry: StaticDataRegistry) -> None:
    state = _p2_holds_support(registry)
    state.systems["102"].planet_owners = {"industrex": "p1"}
    assert _support_row(state, registry, "p2")["playable"] is True
    dropped, _ = faction_components.play(
        state, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
    )
    # Orbital Drop to akcja Sola - pauza „początek tury” minęła, notki już się nie zagra.
    assert _support_row(dropped, registry, "p2")["playable"] is False


@ruling("F_sol/military-support/3")
def test_military_support_w_turze_pasu_sola(registry: StaticDataRegistry) -> None:
    state = _p2_holds_support(registry)
    state.players["p1"].strategy_cards = [1]
    state.players["p1"].exhausted_strategy_cards = [1]  # Sol w tej turze tylko spasuje
    row = _support_row(state, registry, "p2")
    assert row["playable"] is True, row["reason"]
    played, _ = promissory_play.play(state, registry, "p2", MS, {"planet": "none"})
    passed = turn_flow.pass_turn(played, "p1")
    assert passed.players["p1"].passed is True


@ruling("F_sol/military-support/4")
def test_military_support_bez_zetonow_strategii(registry: StaticDataRegistry) -> None:
    state = _p2_holds_support(registry)
    state.players["p1"].strategic_cc = 0
    reinforcements = state.players["p1"].cc_reinf
    row = _support_row(state, registry, "p2")
    assert row["playable"] is True, row["reason"]
    after, _ = promissory_play.play(state, registry, "p2", MS, {"planet": "102|industrex"})
    assert after.players["p1"].strategic_cc == 0
    assert after.players["p1"].cc_reinf == reinforcements  # „if able”
    assert _infantry(after, "p2") == 2


@ruling("F_sol/military-support/1")
def test_military_support_z_transakcji_na_poczatku_tury(registry: StaticDataRegistry) -> None:
    state = _sol_turn_starts(_state())
    received = _give_support(state, registry)  # transakcja nie zamyka pauzy „początek tury”
    assert MS in received.players["p2"].private.promissory_notes
    row = _support_row(received, registry, "p2")
    assert row["playable"] is True, row["reason"]


@ruling("R_transactions/rules-reference/1")
def test_military_support_jedna_transakcja_na_ture(registry: StaticDataRegistry) -> None:
    received = _give_support(_sol_turn_starts(_state()), registry)
    received.players["p2"].private.promissory_notes = []
    received.players["p1"].private.promissory_notes = [MS]
    with pytest.raises(ValueError, match="already"):
        _give_support(received, registry)


@ruling("F_sol/military-support/1.1")
def test_military_support_odzyskana_nie_drugi_raz_w_oknie(registry: StaticDataRegistry) -> None:
    state = _p2_holds_support(registry)
    played, _ = promissory_play.play(state, registry, "p2", MS, {"planet": "none"})
    assert MS in played.players["p1"].private.promissory_notes
    regained = _give_support(played, registry)  # Sol od razu oddaje notkę w transakcji
    row = _support_row(regained, registry, "p2")
    assert row["playable"] is False and "already" in str(row["reason"])
    # Następna tura Sola: znacznik wygasł z końcem tury, notka znów grywalna.
    triggers.fire(regained, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    assert _support_row(regained, registry, "p2")["playable"] is True


# ======================================================================= Spec Ops, Adv. Carrier


@ruling("technologies:so2#1")
def test_spec_ops_ii_statystyki_z_karty(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "sol", ["so2"], "infantry")
    assert unit is not None
    assert (unit.cost, unit.combat_hits_on) == (0.5, 6)  # „Cost 1(x2)” = 2 sztuki za 1


@ruling("technologies:so2#2", "technologies:so2#3")
def test_spec_ops_ii_rzut_po_zniszczeniu_prog_5() -> None:
    state = _state()
    state.players["p1"].technologies = ["so2"]
    state.players["p1"].home_position = "102"
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 10}}}
    unit_ops.remove_units(
        state, state.systems["102"], "industrex", "p1", "infantry", 10, UnitCause.DESTROYED
    )
    roll = state.table_roll
    assert roll is not None and len(roll["dice"]) == 10 and roll["hitsOn"] == 5
    revived = sum(1 for d in roll["dice"] if d >= 5)
    assert state.players["p1"].infantry_ii_on_card == revived


@ruling("technologies:so2#4")
def test_spec_ops_ii_wraca_na_planete_domu_na_poczatku_tury() -> None:
    state = _state()
    state.players["p1"].technologies = ["so2"]
    state.players["p1"].home_position = "102"
    state.players["p1"].infantry_ii_on_card = 2
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    assert state.players["p1"].infantry_ii_on_card == 0
    assert _infantry(state, "p1") == 2


@ruling("technologies:ac2#1", "technologies:ac2#2")
def test_advanced_carrier_ii_statystyki_z_karty(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "sol", ["ac2"], "carrier")
    assert unit is not None
    assert (unit.cost, unit.combat_hits_on, unit.move_value, unit.capacity_value) == (3, 9, 2, 8)
    assert unit.sustain_damage is True


# ===================================================================== Genesis (flagowiec)


@ruling("units:sol_flagship#1", "F_sol/genesis/1")
def test_genesis_obowiazkowo_potem_nadwyzka_pojemnosci(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sol")
    capacity = registry.units[sol.FLAGSHIP].capacity_value or 0

    def full(s: Json) -> None:
        s["systems"][flow.home]["space_units"][flow.me] = {
            "flagship": 1, "infantry": capacity,
        }

    flow.edit(full)
    flow.to_status()
    flow.finish_status()
    state = flow.state()
    space = state["systems"][flow.home]["space_units"][flow.me]
    assert not flow.has_offer("Genesis")  # bez pytania - postawienie obowiązkowe
    # Od razu potem limit pojemności - także w fazie strategii (RULES.md 42.x). Sama piechota
    # ponad pojemność = jedyne legalne usunięcie, więc znika bez okna (RULES.md 39.6 C5).
    assert state["phase"] == "STRATEGY"
    assert space["infantry"] == capacity
    assert not (state.get("pending_window") or {})


# ============================================================================= Evelyn DeLouis


def _evelyn_round(registry: StaticDataRegistry, choice: str) -> GameState:
    state = _state()
    state.systems["102"].planet_units = {
        "industrex": {"p1": {"infantry": 2, "mech": 1}, "p2": {"infantry": 3}}
    }
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START, ctx={
        "kind": "ground", "round": 1, "position": "102", "planet": "industrex",
        "attacker": "p2", "defender": "p1",
    })
    return _accept(state, "p1", "Evelyn", {"unit": choice})


def _dice(state: GameState, registry: StaticDataRegistry, player: str) -> dict[str, int]:
    units = battle.combat_units(
        state, build_demo_grid(registry), registry, kind="ground", position="102",
        planet="industrex", player_id=player,
    )
    return {u.base_type: u.total_dice for u in units}


@ruling("leaders:solagent#1", "leaders:solagent#2")
def test_evelyn_jedna_kosc_dla_jednej_sily_naziemnej(registry: StaticDataRegistry) -> None:
    after = _evelyn_round(registry, "p1|infantry")
    assert leaders.state_of(after, registry, "p1", sol.AGENT) == leaders.EXHAUSTED
    assert _dice(after, registry, "p1") == {"infantry": 3, "mech": 1}  # +1 dla grupy, nie na sztukę
    assert _dice(after, registry, "p2") == {"infantry": 3}
    # Cudza siła naziemna też („1 ground force in the active system”).
    enemy = _evelyn_round(registry, "p2|infantry")
    assert _dice(enemy, registry, "p2") == {"infantry": 4}
    # „during this combat round” - po końcu rundy premia znika.
    triggers.fire(after, GameEvent.COMBAT_ROUND, Moment.END, ctx={"kind": "ground"})
    assert _dice(after, registry, "p1") == {"infantry": 2, "mech": 1}


@ruling("F_sol/evelyn-delouis/1")
def test_evelyn_tylko_rzuty_walki(registry: StaticDataRegistry) -> None:
    after = _evelyn_round(registry, "p1|infantry")
    ctx = {"kind": "ground", "base_type": "infantry", "position": "102", "planet": "industrex"}
    assert rules_hooks.modify(rules_hooks.POINT_COMBAT_BONUS_DICE, after, "p1", 0, ctx) == 1
    # Inne rzuty (bombardowanie, Space Cannon) mają własne punkty kości - Evelyn ich nie dotyka.
    for point in (rules_hooks.POINT_BOMBARDMENT_EXTRA_DICE, rules_hooks.POINT_COMBAT_EXTRA_DICE):
        assert rules_hooks.modify(point, after, "p1", 0, ctx) == 0


# ============================================================================== Claire Gibson


def _two_planet_invasion(
    registry: StaticDataRegistry, sol_forces: tuple[int, int], letnev_commit: tuple[int, int]
) -> tuple[Flow, list[str]]:
    """Letnev (``me``) najeżdża obie planety swojego domu trzymane przez Sol (``other``).

    ``sol_forces`` / ``letnev_commit`` = piechota na planetę (kolejno 1. i 2. planeta domu).
    Zwraca flow po kroku Commit i listę planet.
    """
    flow = Flow(registry, "letnev", other="sol")
    flow.player(lambda p: p["leader_states"].update(solcommander="unlocked"), flow.other)
    planets = flow.planets(flow.home)[:2]

    def setup(s: Json) -> None:
        system = s["systems"][flow.home]
        system["planet_units"] = {
            planet: ({flow.other: {"infantry": n}} if n else {})
            for planet, n in zip(planets, sol_forces, strict=True)
        }
        system["planet_owners"] = {planet: flow.other for planet in planets}
        system["space_units"] = {flow.me: {"carrier": 1, "infantry": 4}}

    flow.edit(setup)
    flow.activate(flow.home)
    flow.to_step("INVASION")
    if flow.state()["invasion"] is None:
        flow.post("/tactical/invasion/begin")
    flow.post("/tactical/invasion/commit", {"commits": [
        {"planet": p, "baseType": "infantry", "count": n}
        for p, n in zip(planets, letnev_commit, strict=True) if n
    ]})
    return flow, planets


def _to_ground_combat(flow: Flow) -> None:
    for _ in range(4):
        if flow.state()["invasion"]["phase"] in ("GROUND_COMBAT", "ESTABLISH"):
            return
        flow.post("/tactical/invasion/next")


@ruling("leaders:solcommander#1", "F_sol/claire-gibson/1")
def test_claire_gibson_na_kazdej_planecie_walki(registry: StaticDataRegistry) -> None:
    flow, (a, b) = _two_planet_invasion(registry, (1, 1), (2, 2))
    _to_ground_combat(flow)
    for planet in (a, b):
        flow.post("/tactical/battle/start", {"planet": planet})
        assert flow.has_offer("Claire Gibson", flow.other), planet
        before = flow.state()["systems"][flow.home]["planet_units"][planet][flow.other]
        flow.accept("Claire Gibson", pid=flow.other)
        after = flow.state()["systems"][flow.home]["planet_units"][planet][flow.other]
        assert after["infantry"] == before["infantry"] + 1
        flow.fight()


@ruling("F_sol/claire-gibson/2")
def test_claire_gibson_bez_sil_naziemnych_brak_walki(registry: StaticDataRegistry) -> None:
    flow, (a, b) = _two_planet_invasion(registry, (1, 0), (2, 2))
    # Ostatnia piechota Sola na ``a`` ginie przed walką (jak w Bombardment) - też bez walki.
    flow.edit(lambda s: s["systems"][flow.home]["planet_units"][a].pop(flow.other))
    _to_ground_combat(flow)
    for planet in (a, b):
        flow.post("/tactical/battle/start", {"planet": planet}, ok=False)
        assert not flow.has_offer("Claire Gibson", flow.other), planet
    assert flow.battle().get("active") is not True


@ruling("R_invasion/rules-reference/4")
def test_claire_gibson_atak_zniszczony_przed_walka(registry: StaticDataRegistry) -> None:
    flow, (a, b) = _two_planet_invasion(registry, (1, 1), (2, 2))
    # Space Cannon Defense niszczy wszystkie siły zlądowane na ``b`` - walki tam nie ma.
    flow.edit(lambda s: s["systems"][flow.home]["planet_units"][b].pop(flow.me))
    _to_ground_combat(flow)
    flow.post("/tactical/battle/start", {"planet": b}, ok=False)
    assert not flow.has_offer("Claire Gibson", flow.other)
    flow.post("/tactical/battle/start", {"planet": a})
    assert flow.has_offer("Claire Gibson", flow.other)


@ruling("leaders:solcommander#unlock")
def test_claire_gibson_odblokowanie_dokladnie_12(registry: StaticDataRegistry) -> None:
    state = _state()
    planets = sorted(
        (p for p in registry.planets.values() if p.resources), key=lambda p: (-p.resources, p.id)
    )
    owned: dict[str, str] = {}
    total = 0
    for planet in planets:
        if total + (planet.resources or 0) <= 12:
            owned[planet.id] = "p1"
            total += planet.resources or 0
        if total == 12:
            break
    assert total == 12
    state.systems["102"].planet_owners = owned
    assert sol._commander_unlocked(state, registry, "p1") is True
    owned.pop(next(iter(owned)))
    assert sol._commander_unlocked(state, registry, "p1") is False


# =========================================================================== Jace X (bohater)


@ruling("leaders:solhero#1", "leaders:solhero#2")
def test_helio_command_array_wszystkie_zetony_i_purge(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {sol.HERO: "unlocked"}
    state.systems["105"] = SystemState(position="105", system_id="19", command_tokens=["p1"])
    state.systems["102"].command_tokens = ["p1", "p2"]
    pools = (state.players["p1"].tactical_cc, state.players["p1"].strategic_cc)
    reinforcements = state.players["p1"].cc_reinf
    after, _ = faction_components.play(state, registry, "p1", "leader", sol.HERO)
    assert after.systems["102"].command_tokens == ["p2"]  # cudze żetony zostają
    assert after.systems["105"].command_tokens == []
    assert after.players["p1"].cc_reinf == reinforcements + 2
    # Żetony z arkusza dowodzenia nie są „na planszy” - zostają w pulach.
    assert (after.players["p1"].tactical_cc, after.players["p1"].strategic_cc) == pools
    assert leaders.state_of(after, registry, "p1", sol.HERO) == leaders.PURGED
    with pytest.raises(ValueError):
        faction_components.play(after, registry, "p1", "leader", sol.HERO)


@ruling("leaders:solhero#unlock")
def test_jace_x_odblokowanie_3_cele(registry: StaticDataRegistry) -> None:
    fn = leaders.unlock_predicate(registry, sol.HERO)
    assert fn is not None
    state = _state()
    state.players["p1"].scored_secrets = ["a", "b"]
    assert not fn(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert fn(state, registry, "p1")


# ===================================================================== Bellum Gloriosum (BT)


def _bellum(registry: StaticDataRegistry) -> GameState:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    return state


@ruling("breakthroughs:solbt#1", "breakthroughs:solbt#2")
def test_bellum_gloriosum_ladunek_do_pojemnosci_poza_limitem(
    registry: StaticDataRegistry,
) -> None:
    state = _bellum(registry)
    capacity = int(registry.units["sol_carrier"].capacity_value or 0)
    orders = [ProductionOrder("carrier", 1), ProductionOrder("fighter", 1),
              ProductionOrder("infantry", capacity + 2)]
    assert production.free_cargo_units(state, registry, "p1", orders) == capacity
    # Statek bez capacity (niszczyciel) nic nie zwalnia.
    plain = [ProductionOrder("destroyer", 1), ProductionOrder("infantry", 2)]
    assert production.free_cargo_units(state, registry, "p1", plain) == 0


@ruling("F_sol/bellum-gloriosum/1")
def test_bellum_gloriosum_laczna_pojemnosc_wielu_statkow(registry: StaticDataRegistry) -> None:
    state = _bellum(registry)
    capacity = int(registry.units["sol_carrier"].capacity_value or 0)
    orders = [ProductionOrder("carrier", 2), ProductionOrder("infantry", 2 * capacity)]
    assert production.free_cargo_units(state, registry, "p1", orders) == 2 * capacity


@ruling("F_sol/bellum-gloriosum/2", "F_sol/bellum-gloriosum/2.1")
def test_bellum_gloriosum_koszt_laczny_z_para_piechoty(registry: StaticDataRegistry) -> None:
    state = _bellum(registry)
    orders = [ProductionOrder("dreadnought", 1), ProductionOrder("infantry", 2)]
    free = production.free_cargo_units(state, registry, "p1", orders)
    assert sum(o.count for o in orders) - free <= 2  # mieści się w PRODUCTION 2
    assert production.order_cost(state, registry, "p1", orders) == 5  # 4 + para piechoty za 1


@ruling("F_sol/bellum-gloriosum/3")
def test_bellum_gloriosum_nadwyzka_floty_nie_zmniejsza_darmowego_ladunku(
    registry: StaticDataRegistry,
) -> None:
    """Statek ponad fleet pool i tak podnosi limit ładunku; potem trzeba go usunąć."""
    from src.core import fleet_pool

    state = _bellum(registry)
    state.players["p1"].fleet_cc = 1
    state.systems["102"].space_units = {"p1": {"carrier": 1}}
    capacity = int(registry.units["sol_carrier"].capacity_value or 0)
    orders = [ProductionOrder("carrier", 1), ProductionOrder("infantry", capacity)]
    assert production.free_cargo_units(state, registry, "p1", orders) == capacity
    unit_ops.place_units(state, state.systems["102"], "space", "p1", "carrier", 1,
                         UnitCause.PLACED)
    assert fleet_pool.fleet_report(state, "102", "p1", registry).excess == 1  # do usunięcia
    assert production.free_cargo_units(state, registry, "p1", orders) == capacity


@ruling("F_sol/military-support/1")
def test_military_support_sol_nie_gra_wlasnej(registry: StaticDataRegistry) -> None:
    """Notka działa tylko u innego gracza - Sol musi ją oddać w transakcji."""
    state = _sol_turn_starts(_state())
    assert _support_row(state, registry, "p1")["playable"] is False
