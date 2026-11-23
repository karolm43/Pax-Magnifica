"""The Barony of Letnev — rulingi ``docs/rules_tirules/F_letnev.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Podstawowe testy komponentów są w ``test_letnev.py`` i
``test_flows_letnev.py`` (tam też część znaczników). Statusy bez testu:
``tests/rulings_status.json`` (War Funding sprzed Codexu - nieaktywny wariant; Ul + Alliance).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    active_effects,
    battle,
    battle_rerolls,
    command_tokens,
    damage,
    fleet_pool,
    leaders,
    limits,
    promissory_play,
    space_cannon,
    transaction,
    triggers,
    turn_flow,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    Phase,
    PlayerState,
    TimingWindow,
    WindowType,
)
from src.core.hooks.factions import letnev
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide
from tests import test_space_cannon as sc
from tests.factions.test_letnev import _accept, _grid, _offers, _rolled, _round_start, _state
from tests.factions.test_letnev import registry as registry  # noqa: F401 - fixture modułu
from tests.rulings import ruling

assert _grid  # autouse: siatka demo dla board_graph


def _rolled_three() -> GameState:
    """p2 (Sol, aktywny) atakuje p3 (Hacan) w 102; p1 = Letnev poza walką, piechota na Industrex
    (ten sam system = sąsiedzi), notka War Funding w ręce p1."""
    state = _state()
    state.active_player_id = "p2"
    state.players["p3"] = PlayerState(player_id="p3", color="green", faction="hacan")
    state.seating_order = ["p1", "p2", "p3"]
    state.systems["102"].space_units = {"p2": {"cruiser": 1}, "p3": {"cruiser": 1}}
    state.systems["102"].planet_units["industrex"] = {"p1": {"infantry": 1}}
    state.players["p1"].private.promissory_notes = [letnev.WAR_FUNDING]
    combat = ActiveCombat(
        kind="space", position="102", attacker="p2", defender="p3", step=CombatStep.ASSIGN,
    )
    combat.rolls = {
        "p2": [{"baseType": "cruiser", "name": "Cruiser", "dice": [1], "hitsOn": 7,
                "modifier": 0, "hits": 0}],
        "p3": [{"baseType": "cruiser", "name": "Cruiser", "dice": [9], "hitsOn": 7,
                "modifier": 0, "hits": 1}],
    }
    combat.pending_hits = {"p2": 1, "p3": 0}
    combat.log = [{"round": 1, "phase": "COMBAT", "rolls": combat.rolls,
                   "hits": {"p2": 0, "p3": 1}, "losses": {}, "sustained": {}}]
    state.active_combat = combat
    state.pending_window = TimingWindow(window_type=WindowType.COMBAT_ASSIGN_HITS, queue=["p2"])
    return state


def _give_note(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Letnev (p1) oddaje War Funding aktywnemu p2 w transakcji."""
    return transaction.resolve_transaction(
        state, build_demo_grid(registry), "p1", TransactionSide(),
        TransactionSide(promissory_note=letnev.WAR_FUNDING),
    )


def _playable(state: GameState, registry: StaticDataRegistry, player: str) -> dict[str, Any]:
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, player)}
    return rows.get(letnev.WAR_FUNDING, {"playable": False, "reason": "not in hand"})


def _ground(state: GameState, hits: int, units: dict[str, int]) -> GameState:
    """Walka naziemna na Industrex po rzucie: p1 (Letnev) pokrywa ``hits`` trafień."""
    state.systems["102"].planet_units["industrex"] = {"p1": dict(units), "p2": {"infantry": 3}}
    combat = ActiveCombat(
        kind="ground", position="102", planet="industrex", attacker="p1", defender="p2",
        step=CombatStep.ASSIGN,
    )
    combat.pending_hits = {"p1": hits, "p2": 0}
    combat.log = [{"round": 1, "phase": "COMBAT", "rolls": {}, "hits": {"p2": hits},
                   "losses": {}, "sustained": {}}]
    state.active_combat = combat
    state.pending_window = TimingWindow(window_type=WindowType.COMBAT_ASSIGN_HITS, queue=["p1"])
    return state


# ========================================================================== Munitions Reserves


@ruling("F_letnev/munitions-reserves/1", "abilities:munitions#1")
def test_munitions_raz_na_runde_mimo_wielu_tg(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].trade_goods = 6
    _round_start(state)
    assert [label for label in _offers(state, "p1") if "Munitions" in label] == [
        "Munitions Reserves: spend 2 TG to reroll this round"
    ]  # jedna oferta, nie „2 TG za każdy przerzut”
    paid = _accept(state, "p1", "Munitions")
    assert paid.players["p1"].trade_goods == 4
    paid.pending_offers = []
    _round_start(paid)  # ponowne wywołanie w tej samej rundzie: już zapłacone
    assert not any("Munitions" in label for label in _offers(paid, "p1"))


# ===================================================================================== Armada


@ruling("F_letnev/armada/1", "abilities:armada#1")
def test_armada_przy_zerze_zetonow_floty(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].fleet_cc = 0
    state.systems["102"].space_units["p1"] = {"cruiser": 2}
    report = fleet_pool.fleet_report(state, "102", "p1", registry)
    assert (report.pool, report.excess) == (2, 0)  # 0 żetonów + 2 z Armady: statki zostają
    with pytest.raises(ValueError):  # efekt „usuń żeton z puli floty” nie ma czego zabrać
        command_tokens.spend_from_pool(state, "p1", "fleet")
    assert state.players["p1"].fleet_cc == 0
    state.systems["102"].space_units["p1"] = {"cruiser": 3}
    assert fleet_pool.fleet_report(state, "102", "p1", registry).excess == 1


# ============================================================================ War Funding Ω


@ruling("F_letnev/war-funding-omega/1")
def test_war_funding_otrzymana_po_rzucie_grana_od_razu(registry: StaticDataRegistry) -> None:
    state = _rolled_three()
    after = _give_note(state, registry)  # transakcja w trakcie walki, po rzutach
    assert letnev.WAR_FUNDING in after.players["p2"].private.promissory_notes
    row = _playable(after, registry, "p2")
    assert row["playable"] is True, row["reason"]


@ruling("F_letnev/war-funding-omega/1.1")
def test_war_funding_obronca_nie_dostanie_notki(registry: StaticDataRegistry) -> None:
    state = _rolled_three()
    grid = build_demo_grid(registry)
    assert not transaction.components_allowed(state, grid, "p1", "p3")
    with pytest.raises(ValueError):  # transakcja musi obejmować aktywnego gracza
        transaction.resolve_transaction(
            state, grid, "p1", TransactionSide(),
            TransactionSide(promissory_note=letnev.WAR_FUNDING), player_id="p3",
        )


@ruling("F_letnev/war-funding-omega/1.2")
def test_war_funding_jedna_transakcja_na_ture(registry: StaticDataRegistry) -> None:
    after = _give_note(_rolled_three(), registry)
    after.players["p2"].private.promissory_notes = []
    after.players["p1"].private.promissory_notes = [letnev.WAR_FUNDING]
    with pytest.raises(ValueError, match="already"):
        _give_note(after, registry)


@ruling("F_letnev/war-funding-omega/1.3")
def test_war_funding_odzyskana_nie_drugi_raz_w_rundzie(registry: StaticDataRegistry) -> None:
    state = _rolled_three()
    state.players["p1"].private.promissory_notes = []
    state.players["p2"].private.promissory_notes = [letnev.WAR_FUNDING]  # z poprzedniej tury
    played, _ = promissory_play.play(
        state, registry, "p2", letnev.WAR_FUNDING, {"opponent": "no", "dice": ["0:0"]}
    )
    assert letnev.WAR_FUNDING in played.players["p1"].private.promissory_notes
    regained = _give_note(played, registry)  # od razu transakcja z Letnevem
    row = _playable(regained, registry, "p2")
    assert row["playable"] is False and "already" in str(row["reason"])
    triggers.fire(regained, GameEvent.COMBAT_ROUND, Moment.END, ctx={"kind": "space"})
    assert _playable(regained, registry, "p2")["playable"] is True  # kolejna runda walki


@ruling("F_letnev/war-funding-omega/1.4")
def test_war_funding_po_obroncy_atakujacy_czeka(registry: StaticDataRegistry) -> None:
    state = _rolled_three()
    state.players["p1"].private.promissory_notes = []
    state.players["p3"].private.promissory_notes = [letnev.WAR_FUNDING]
    played, _ = promissory_play.play(
        state, registry, "p3", letnev.WAR_FUNDING, {"opponent": "yes", "dice": []}
    )
    received = _give_note(played, registry)
    assert letnev.WAR_FUNDING in received.players["p2"].private.promissory_notes
    assert _playable(received, registry, "p2")["playable"] is False


@ruling("F_letnev/war-funding-omega/2")
def test_war_funding_nie_dla_anti_fighter_barrage(registry: StaticDataRegistry) -> None:
    state = _state()
    combat = _rolled(state)
    state.players["p2"].private.promissory_notes = [letnev.WAR_FUNDING]
    combat.afb_assign = True  # okno strat po Anti-Fighter Barrage
    assert _playable(state, registry, "p2")["playable"] is False
    combat.afb_assign = False
    combat.log[-1]["phase"] = "AFB"
    assert _playable(state, registry, "p2")["playable"] is False


@ruling(
    "promissory_notes:war_funding#1", "promissory_notes:war_funding#2",
    "promissory_notes:war_funding#3",
)
def test_war_funding_przerzut_obu_stron_i_zwrot(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, set[tuple[int, int]]]] = []
    original = battle_rerolls.reroll_combat_dice

    def spy(state: GameState, owner: str, chosen: set[tuple[int, int]], *a: Any, **kw: Any) -> int:
        calls.append((owner, set(chosen)))
        return original(state, owner, chosen, *a, **kw)

    monkeypatch.setattr(battle_rerolls, "reroll_combat_dice", spy)
    state = _state()
    _rolled(state)
    state.players["p2"].private.promissory_notes = [letnev.WAR_FUNDING]
    after, _ = promissory_play.play(
        state, registry, "p2", letnev.WAR_FUNDING, {"opponent": "yes", "dice": ["0:0"]}
    )
    # Wszystkie kości przeciwnika (Letnev p1: 2 kości) + wybrane własne.
    assert calls == [("p1", {(0, 0), (0, 1)}), ("p2", {(0, 0)})]
    assert after.players["p1"].private.promissory_notes == [letnev.WAR_FUNDING]
    assert after.players["p2"].private.promissory_notes == []


# ============================================================================= L4 Disruptors


@ruling("F_letnev/l4-disruptors/1")
def test_l4_nie_chroni_przed_space_cannon_offense(registry: StaticDataRegistry) -> None:
    state = sc._state(pds={"p2": 1}, ships={"p1": {"destroyer": 1}}, techs={"p1": ["l4"]})
    state.players["p1"].faction = "letnev"
    opened = space_cannon.open_offense(state, sc._grid(), registry)
    assert opened.pending_window is not None
    assert opened.pending_window.window_type is WindowType.SPACE_CANNON
    assert opened.pending_window.queue == ["p2"]


# ==================================================================== Non-Euclidean Shielding


@ruling("F_letnev/noneuclidean-shielding/1", "F_letnev/rear-admiral-farran/2")
def test_nes_i_farran_przy_sustain_dunlain_reapera(registry: StaticDataRegistry) -> None:
    state = _ground(_state(), 2, {"mech": 1, "infantry": 1})
    state.players["p1"].technologies = ["nes"]
    state.players["p1"].leader_states = {letnev.COMMANDER: "unlocked"}
    grid = build_demo_grid(registry)
    after = battle.assign_combat_hits(
        state, grid, registry, "p1", sustain={"mech": 1}, destroy={}, destroy_damaged={},
    )
    assert after.systems["102"].planet_units["industrex"]["p1"] == {"mech": 1, "infantry": 1}
    assert any("Farran" in label for label in _offers(after, "p1"))


@ruling("F_letnev/noneuclidean-shielding/2")
def test_nes_przy_trafieniach_space_cannon(registry: StaticDataRegistry) -> None:
    base = sc._state(
        pds={"p2": 12}, ships={"p1": {"dreadnought": 1, "destroyer": 1}}, techs={"p1": ["nes"]}
    )
    opened = space_cannon.open_offense(base, sc._grid(), registry)
    fired = None
    for seed in range(1, 400):
        candidate = opened.clone()
        candidate.rng_seed = seed
        result = space_cannon.fire_offense(candidate, sc._grid(), registry, "p2", None)
        pending = space_cannon.pending_hits(result)
        if pending is not None and pending.hits == 2:
            fired = result
            break
    assert fired is not None
    after = space_cannon.assign_hits(fired, "p1", sustain={"dreadnought": 1}, registry=registry)
    assert after.systems["000"].space_units["p1"] == {"dreadnought": 1, "destroyer": 1}
    # Bombardowanie i Space Cannon Defense: ta sama walidacja z ``sustain_cancels`` obrońcy.
    assert battle.sustain_cancels(fired, "p1") == 2


@ruling("F_letnev/noneuclidean-shielding/3", "technologies:nes#1")
def test_nes_musi_anulowac_dwa(registry: StaticDataRegistry) -> None:
    state = _state()
    _rolled(state)
    state.players["p1"].technologies = ["nes"]
    state.systems["102"].space_units["p1"] = {"dreadnought": 2, "cruiser": 1}
    grid = build_demo_grid(registry)
    units = {u.base_type: u for u in battle.side_units(state, grid, registry, "p1")}
    cancels = battle.sustain_cancels(state, "p1")
    with pytest.raises(ValueError, match="exactly"):  # 2 trafienia: Sustain musi zjeść oba
        battle.plan_losses(units, {"dreadnought": 1}, {"cruiser": 1}, {}, 2, cancels)
    assert battle.plan_losses(units, {"dreadnought": 1}, {}, {}, 2, cancels) == {
        "dreadnought": (2, 1)
    }  # krążownik ocalał
    # 3 trafienia, dwa Sustainy: pierwszy anuluje 2, drugi ostatnie 1 (zostało jedno).
    plan = battle.plan_losses(units, {"dreadnought": 2}, {}, {}, 3, cancels)
    assert plan["dreadnought"] == (2, 2)
    with pytest.raises(ValueError):  # zniszczenie + Sustain anulujący 1 przy 3 trafieniach
        battle.plan_losses(units, {"dreadnought": 1}, {"cruiser": 1, "dreadnought": 1}, {}, 3,
                           cancels)


@ruling("F_letnev/noneuclidean-shielding/4")
def test_nes_bez_wstecznego_drugiego_anulowania(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["nes"]
    combat = _rolled(state)
    combat.pending_hits = {"p1": 1, "p2": 0}
    state.systems["102"].space_units["p1"] = {"dreadnought": 1, "cruiser": 1}
    grid = build_demo_grid(registry)
    after = battle.assign_combat_hits(
        state, grid, registry, "p1", sustain={"dreadnought": 1}, destroy={}, destroy_damaged={},
    )
    assert damage.damaged_count(after.systems["102"], "space", "p1", "dreadnought") == 1
    # Dodatkowe trafienie (np. Reflective Shielding): nowe przypisanie, „zapasowe” anulowanie
    # poprzedniego Sustain nie przepada na nie - dreadnought nie ma już Sustain do użycia.
    assert after.active_combat is not None
    after.active_combat.step = CombatStep.ASSIGN
    after.pending_window = TimingWindow(window_type=WindowType.COMBAT_ASSIGN_HITS, queue=["p1"])
    battle.add_combat_hits(after, "p1", 1)
    assert battle.required_hits(after, grid, registry, "p1") == 1
    with pytest.raises(ValueError):
        battle.assign_combat_hits(
            after, grid, registry, "p1", sustain={"dreadnought": 1}, destroy={},
            destroy_damaged={},
        )
    done = battle.assign_combat_hits(
        after, grid, registry, "p1", sustain={}, destroy={"cruiser": 1}, destroy_damaged={},
    )
    assert done.systems["102"].space_units["p1"] == {"dreadnought": 1}


# ============================================================================== Arc Secundus


@ruling("F_letnev/arc-secundus/1")
def test_arc_secundus_bez_naprawy_po_walce(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units["p1"] = {"flagship": 1}
    damage.set_damaged(state.systems["102"], "space", "p1", "flagship", 1)
    ctx = {"kind": "space", "position": "102", "attacker": "p1", "defender": "p2"}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=ctx)
    triggers.fire(state, GameEvent.COMBAT, Moment.END, ctx=ctx)
    assert damage.damaged_count(state.systems["102"], "space", "p1", "flagship") == 1


@ruling("F_letnev/arc-secundus/2", "units:letnev_flagship#2")
def test_arc_secundus_naprawa_tylko_w_swojej_walce_kosmicznej(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.systems["102"].space_units["p1"] = {"flagship": 1}
    damage.set_damaged(state.systems["102"], "space", "p1", "flagship", 1)
    _round_start(state, "ground")  # walka naziemna w tym systemie: flagowiec nie walczy
    assert damage.damaged_count(state.systems["102"], "space", "p1", "flagship") == 1
    other = {"kind": "space", "round": 1, "position": "103", "attacker": "p1", "defender": "p2"}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START, ctx=other)  # inny system
    assert damage.damaged_count(state.systems["102"], "space", "p1", "flagship") == 1
    _round_start(state)  # jego walka kosmiczna
    assert damage.damaged_count(state.systems["102"], "space", "p1", "flagship") == 0


@ruling("F_letnev/arc-secundus/3.1", "units:letnev_flagship#1")
def test_arc_secundus_nie_wylacza_magen_omega(registry: StaticDataRegistry) -> None:
    from src.core import invasion

    state = _state()
    state.players["p2"].technologies = ["md"]  # Magen Defense Grid ΩΩ
    state.systems["102"].space_units["p1"] = {"flagship": 1}
    state.systems["102"].planet_units["industrex"] = {"p1": {"infantry": 2}, "p2": {"pds": 1}}
    assert invasion.planet_shield(state, registry, "102", "industrex", "p1") == (True, False)
    ctx = {"kind": "ground", "position": "102", "planet": "industrex",
           "attacker": "p1", "defender": "p2"}
    triggers.fire(state, GameEvent.COMBAT, Moment.START, ctx=ctx)
    assert any("Magen" in label for label in _offers(state, "p2"))


# ============================================================================ Viscount Unlenn


@ruling(
    "F_letnev/viscount-unlenn/1",
    "F_letnev/viscount-unlenn/2",
    "leaders:letnevagent#1",
    "leaders:letnevagent#2",
)
def test_unlenn_kosc_tylko_do_rzutu_combat(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units["p1"] = {"destroyer": 1}
    state.systems["102"].space_units["p2"] = {"fighter": 2}
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1", defender="p2")
    grid = build_demo_grid(registry)
    plain = {u.base_type: u for u in battle.side_units(state, grid, registry, "p1")}
    _round_start(state)
    after = _accept(state, "p1", "Unlenn", {"ship": "p1|destroyer"})
    units = {u.base_type: u for u in battle.side_units(after, grid, registry, "p1")}
    # Obowiązkowa: wybrany statek rzuca o 1 kość więcej bez dalszych pytań.
    assert units["destroyer"].total_dice == plain["destroyer"].total_dice + 1
    assert units["destroyer"].afb_dice == plain["destroyer"].afb_dice  # AFB bez zmian


# ======================================================================= Rear Admiral Farran


@ruling("F_letnev/rear-admiral-farran/1", "leaders:letnevcommander#unlock")
def test_farran_najpierw_nadwyzka_floty(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].fleet_cc = 3  # pula 3 + Armada 2 = 5
    state.systems["102"].space_units["p1"] = {"cruiser": 6}
    state = limits.enforce_limits(state, registry)
    assert state.pending_window is not None
    assert state.pending_window.window_type is WindowType.FLEET_POOL
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", letnev.COMMANDER) == leaders.LOCKED
    removed = fleet_pool.resolve_fleet_pool(state, registry, "p1", {"cruiser": 1})
    leaders.refresh_unlocks(removed, registry)
    assert leaders.state_of(removed, registry, "p1", letnev.COMMANDER) == leaders.UNLOCKED


@ruling("F_letnev/rear-admiral-farran/3")
def test_farran_uszkodzenie_bez_sustain_nic_nie_daje(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {letnev.COMMANDER: "unlocked"}
    state.systems["102"].space_units["p1"] = {"dreadnought": 1}
    damage.set_damaged(state.systems["102"], "space", "p1", "dreadnought", 1)
    leaders.refresh_unlocks(state, registry)
    assert not any("Farran" in label for label in _offers(state, "p1"))


@ruling("F_letnev/rear-admiral-farran/4", "leaders:letnevcommander#1")
def test_farran_tg_po_jednym(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state()
    state.players["p1"].leader_states = {letnev.COMMANDER: "unlocked"}
    ctx = {"player": "p1", "base_type": "dreadnought", "count": 2}
    triggers.fire(state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject="p1", ctx=ctx)
    gains: list[int] = []
    original = triggers.fire

    def spy(s: GameState, event: GameEvent, moment: Moment, **kw: Any) -> Any:
        if event is GameEvent.TRADE_GOODS_GAINED:
            gains.append(int(kw["ctx"]["amount"]))
        return original(s, event, moment, **kw)

    monkeypatch.setattr(triggers, "fire", spy)
    after = _accept(state, "p1", "Farran")
    assert gains == [1, 1]
    assert after.players["p1"].trade_goods == 5


# ========================================================================= Darktalon Treilla


def _hero_played(registry: StaticDataRegistry) -> GameState:
    from src.core import faction_components

    state = _state()
    state.players["p1"].leader_states = {letnev.HERO: "unlocked"}
    after, _ = faction_components.play(state, registry, "p1", "leader", letnev.HERO)
    return after


@ruling("F_letnev/darktalon-treilla-dark-matter-affinity/1", "leaders:letnevhero#3")
def test_darktalon_do_konca_rundy_gry(registry: StaticDataRegistry) -> None:
    state = _hero_played(registry)
    for phase in ("action", "status", "agenda"):  # koniec faz to jeszcze nie koniec rundy
        triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": phase})
        assert active_effects.has_effect(state, "p1", letnev.HERO_EFFECT)
    nxt = turn_flow.next_round(state)  # po agendzie (albo po statusie bez zdjętych Custodians)
    assert not active_effects.has_effect(nxt, "p1", letnev.HERO_EFFECT)
    assert leaders.state_of(nxt, registry, "p1", letnev.HERO) == leaders.PURGED


@ruling("F_letnev/darktalon-treilla-dark-matter-affinity/2")
def test_darktalon_po_rundzie_nadwyzka_do_usuniecia(registry: StaticDataRegistry) -> None:
    state = _hero_played(registry)
    state.players["p1"].fleet_cc = 3
    state.systems["102"].space_units["p1"] = {"dreadnought": 8}
    assert fleet_pool.fleet_report(state, "102", "p1", registry).excess == 0
    nxt = turn_flow.next_round(state)
    assert fleet_pool.fleet_report(nxt, "102", "p1", registry).excess == 3
    nxt.phase = Phase.ACTION  # strategia nie rusza statków; limit wymusza pierwsza akcja
    enforced = limits.enforce_limits(nxt, registry)
    assert enforced.pending_window is not None
    assert enforced.pending_window.window_type is WindowType.FLEET_POOL


@ruling("leaders:letnevhero#unlock")
def test_darktalon_odblokowanie_3_cele(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].scored_secrets = ["a", "b"]
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", letnev.HERO) == leaders.LOCKED
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", letnev.HERO) == leaders.UNLOCKED


# ============================================================================ Dunlain Reaper


def _reaper_round(state: GameState, round_no: int) -> None:
    ctx = {"kind": "ground", "round": round_no, "position": "102", "planet": "industrex",
           "attacker": "p1", "defender": "p2"}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START, ctx=ctx)


@ruling("F_letnev/dunlain-reaper/1", "F_letnev/dunlain-reaper/1.1")
def test_reaper_jeden_na_runde_kolejne_pozniej(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].trade_goods = 6
    state.systems["102"].planet_units["industrex"] = {"p1": {"infantry": 3}, "p2": {"mech": 1}}
    _reaper_round(state, 1)
    assert sum("Dunlain" in label for label in _offers(state, "p1")) == 1
    after = _accept(state, "p1", "Dunlain", {"trade_goods": 2})
    assert not any("Dunlain" in label for label in _offers(after, "p1"))
    assert after.systems["102"].planet_units["industrex"]["p1"] == {"infantry": 2, "mech": 1}
    after.pending_offers = []
    after.pending_window = None  # okna reakcji po rozmieszczeniu - poza zakresem testu
    _reaper_round(after, 2)
    again = _accept(after, "p1", "Dunlain", {"trade_goods": 2})
    assert again.systems["102"].planet_units["industrex"]["p1"] == {"infantry": 1, "mech": 2}


@ruling("F_letnev/dunlain-reaper/2", "F_letnev/dunlain-reaper/2.1")
def test_reaper_tylko_z_rezerwy(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].planet_units["industrex"] = {"p1": {"infantry": 2}, "p2": {"mech": 1}}
    state.systems["102"].planet_units["lodor"] = {"p1": {"mech": 4}}  # wszystkie 4 na planszy
    _reaper_round(state, 1)
    assert not any("Dunlain" in label for label in _offers(state, "p1"))
    state.systems["102"].planet_units["lodor"] = {"p1": {"mech": 3}}  # jeden zniszczony
    _reaper_round(state, 2)
    assert any("Dunlain" in label for label in _offers(state, "p1"))


# ======================================================================= Gravleash Maneuvers


@ruling("F_letnev/gravleash-maneuvers/2")
def test_gravleash_wyrownanie_do_fighter_ii(registry: StaticDataRegistry) -> None:
    from src.core import movement

    grid = build_demo_grid(registry)
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    together = ["dreadnought", "fighter"]

    def value(s: GameState) -> int | None:
        return movement._effective_move_value(
            s, grid, registry, "000", "dreadnought", "p1",
            boost=False, tempesta=False, companions=together,
        )

    assert value(state) == 1  # Fighter I nie ma wartości ruchu
    state.players["p1"].technologies = ["ff2"]
    assert value(state) == 2  # = Fighter II ruszający z tego samego systemu


def test_war_funding_efekt_rundy_walki_globalny() -> None:
    """Znacznik „zagrana w tej rundzie” wygasa z końcem rundy walki (nie właściciela)."""
    state = _state()
    active_effects.add_effect(state, letnev.WAR_FUNDING_PLAYED, Duration.COMBAT_ROUND)
    assert active_effects.has_effect(state, "p2", letnev.WAR_FUNDING_PLAYED)
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx={"kind": "space"})
    assert not active_effects.has_effect(state, "p2", letnev.WAR_FUNDING_PLAYED)
