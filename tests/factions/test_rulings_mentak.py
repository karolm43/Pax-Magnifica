"""The Mentak Coalition — rulingi ``docs/rules_tirules/F_mentak.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Podstawowe testy komponentów są w ``test_mentak.py`` i
``test_flows_mentak.py``. Statusy bez testu: ``tests/rulings_status.json`` (umowy niewiążące,
Creuss, Nekro).
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from src.core import (
    active_effects,
    battle,
    battle_rerolls,
    board_graph,
    economy,
    leaders,
    objective_events,
    objective_payment,
    rules_hooks,
    transaction,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.dice import DIE_SIDES
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    InvasionPhase,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import mentak
from src.core.production import ProductionOrder, produce
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards import diplomacy
from src.core.transaction import TransactionSide
from src.core.unit_ops import UnitCause
from tests.factions.flow_harness import Flow
from tests.factions.test_mentak import _grid, _state
from tests.factions.test_mentak import registry as registry  # noqa: F401 - fixture modułu
from tests.rulings import ruling


def _labels(state: GameState, player: str = "p1") -> list[str]:
    return [o.label for o in state.pending_offers if o.player_id == player]


def _accept(
    state: GameState, player: str, label_part: str, params: dict[str, Any] | None = None
) -> GameState:
    offer = next(
        o for o in state.pending_offers if o.player_id == player and label_part in o.label
    )
    return triggers.accept_offer(state, player, offer.id, params)


def _three() -> GameState:
    """``_state`` + p3 (Letnev, 3 TG) w 101 - sąsiad Mentaka i p2."""
    state = _state()
    state.players["p3"] = PlayerState(
        player_id="p3", color="green", faction="letnev", trade_goods=3
    )
    state.seating_order = ["p1", "p2", "p3"]
    state.systems["101"].space_units["p3"] = {"cruiser": 1}
    return state


def _combat(state: GameState, mine: dict[str, int], theirs: dict[str, int]) -> ActiveCombat:
    state.systems["000"].space_units = {"p1": dict(mine), "p2": dict(theirs)}
    state.active_system = "000"
    state.active_combat = ActiveCombat(kind="space", position="000", attacker="p1", defender="p2")
    return state.active_combat


def _sleeper(state: GameState, seen: int = 0) -> None:
    active_effects.add_effect(
        state, mentak.SLEEPER, Duration.COMBAT, owner="p1", data={"seen": seen}
    )


def _lost(combat: ActiveCombat, player: str, base_type: str) -> None:
    combat.destroyed_all = [*combat.destroyed_all, {"player": player, "base_type": base_type}]


# ========================================================================================== Ambush


def _ambush_hits_on(registry: StaticDataRegistry) -> int:
    unit = resolve_unit_variant(registry, "mentak", [], "cruiser", False)
    assert unit is not None and unit.combat_hits_on is not None
    return unit.combat_hits_on


@ruling("F_mentak/ambush/1", "abilities:ambush#1", "abilities:ambush#2")
def test_ambush_bez_modyfikatorow_i_przerzutow(registry: StaticDataRegistry) -> None:
    """Kości Ambush: bez modyfikatorów (Morale Boost w grze) i poza oknem przerzutów walki."""
    state = _state()
    _combat(state, {"cruiser": 2, "destroyer": 1}, {"carrier": 3})
    active_effects.add_effect(state, "action_cards:mb1", Duration.ROUND, owner="p1")
    state.rng_seed = 3
    mentak.ambush(state, "p1", {"params": {"ships": ["cruiser:0", "destroyer:0"]}})
    assert state.active_combat is not None
    entry = state.active_combat.log[-1]
    assert entry["phase"] == "AMBUSH"
    for roll in entry["rolls"]["p1"]:
        assert roll["modifier"] == 0
        assert roll["hits"] == sum(1 for d in roll["dice"] if d >= roll["hitsOn"])
    assert sum(len(r["dice"]) for r in entry["rolls"]["p1"]) == 2  # „up to 2”
    state.active_combat.step = CombatStep.ASSIGN
    with pytest.raises(ValueError, match="only after the roll"):
        battle_rerolls._require_dice_window(state)
    with pytest.raises(ValueError, match="1 or 2"):
        mentak.ambush(state.clone(), "p1", {"params": {"ships": ["cruiser:0", "cruiser:1",
                                                                  "destroyer:0"]}})


@ruling("F_mentak/ambush/2")
def test_ambush_tylko_statki_obecne_w_chwili_uzycia(registry: StaticDataRegistry) -> None:
    state = _state()
    _combat(state, {"cruiser": 2}, {"carrier": 1})
    unit_ops.remove_units(
        state, state.systems["000"], "space", "p1", "cruiser", 1, UnitCause.DESTROYED
    )
    offered = mentak.ambush_inputs(state, registry, "p1", {})[0]["options"]
    assert [o["value"] for o in offered] == ["cruiser:0"]
    with pytest.raises(ValueError, match="not in the combat"):
        mentak.ambush(state, "p1", {"params": {"ships": ["cruiser:0", "cruiser:1"]}})


def _ambush_flow(registry: StaticDataRegistry, theirs: dict[str, int]) -> Flow:
    """Mentak (2 krążowniki) atakuje; ziarno dobrane tak, by Ambush trafił 2 razy."""
    flow = Flow(registry, "mentak")
    flow.space_combat({"cruiser": 2}, theirs)
    counter = int(flow.state()["rng_counter"])
    hits_on = _ambush_hits_on(registry)
    seed = next(
        s for s in range(1, 2000)
        if all(d >= hits_on for d in _dice(s, counter, 2))
    )
    resp = flow.client.post("/god-mode/patch", json={"rng_seed": seed})
    assert resp.status_code == 200, resp.text
    flow.accept("Ambush", {"ships": ["cruiser:0", "cruiser:1"]})
    flow.decline_all()
    return flow


def _dice(seed: int, counter: int, count: int) -> list[int]:
    rng = random.Random(f"{seed}:{counter}")
    return [rng.randint(1, DIE_SIDES) for _ in range(count)]


@ruling("F_mentak/ambush/3", "abilities:ambush#3")
def test_ambush_shields_holding_anuluje(registry: StaticDataRegistry) -> None:
    flow = _ambush_flow(registry, {"carrier": 2})
    view = flow.battle()
    assert view["step"] == "ASSIGN" and view["assigning"] == view["defender"]["faction"]
    flow.player(lambda p: p["private"].update(action_cards=["sh1"]), flow.other)
    rows = flow.client.get("/action-card/playable", params={"player_id": flow.other}).json()
    row = next(r for r in rows["cards"] if r["card_id"] == "sh1")
    assert row["playable"], row["reason"]
    flow.post("/action-card/play", {
        "player_id": flow.other, "card_id": "sh1", "params": {"count": 2},
    })
    flow.finish_hold()
    state = flow.state()
    combat = state["active_combat"]
    assert combat["pending_hits"].get(flow.other, 0) == 0
    assert state["systems"][combat["position"]]["space_units"][flow.other]["carrier"] == 2


@ruling("F_mentak/ambush/4", "F_mentak/ambush/4.1")
def test_ambush_sustain_direct_hit_reflective(registry: StaticDataRegistry) -> None:
    """Trafienie Ambush anuluje Sustain Damage; potem Direct Hit (Mentak) i Reflective
    Shielding (przeciwnik) są zagrywalne."""
    flow = _ambush_flow(registry, {"dreadnought": 2})
    flow.player(lambda p: p["private"].update(action_cards=["dh1"]))
    flow.player(lambda p: p["private"].update(action_cards=["reflective"]), flow.other)
    view = flow.battle()
    assert view["assigning"] == flow.state()["players"][flow.other]["faction"]
    faction = view["assigning"]
    flow.post("/tactical/battle/assign", {
        "faction": faction, "sustain": [{"baseType": "dreadnought", "count": 2}],
        "destroy": [], "destroyDamaged": [],
    })
    position = flow.state()["active_combat"]["position"]
    assert flow.state()["systems"][position]["space_units"][flow.other]["dreadnought"] == 2

    def playable(pid: str, card: str) -> bool:
        rows = flow.client.get("/action-card/playable", params={"player_id": pid}).json()
        return any(r["card_id"] == card and r["playable"] for r in rows["cards"])

    assert playable(flow.me, "dh1")
    assert playable(flow.other, "reflective")
    flow.post("/action-card/play", {
        "player_id": flow.me, "card_id": "dh1", "params": {"ship": "dreadnought"},
    })
    flow.finish_hold()
    assert flow.state()["systems"][position]["space_units"][flow.other]["dreadnought"] == 1
    flow.pass_reactions()  # pauza mija - walka sama idzie dalej (AFB / runda)
    combat = flow.state()["active_combat"]
    assert not combat["sustain_hold"] and combat["step"] != "ASSIGN"


# ========================================================================================= Pillage


@ruling("F_mentak/pillage/1")
def test_pillage_trade_convoys_i_faza_agend_nie_czynia_sasiadami(
    registry: StaticDataRegistry,
) -> None:
    """Mentak z Trade Convoys handluje z dalekim p2 - bez Pillage; faza agend też nie czyni
    sąsiadami (Pillage liczy samo sąsiedztwo, ``neighbors_of``)."""
    state = _state()
    state.players["p3"] = PlayerState(player_id="p3", color="yellow", faction="hacan")
    state.seating_order = ["p1", "p2", "p3"]
    state.players["p1"].promissory_notes_in_play = ["convoys"]
    state.systems["101"].space_units = {}
    state.systems["301"].space_units = {"p2": {"cruiser": 1}}  # daleko od Mentaka
    done = transaction.resolve_transaction(
        state, _grid(), "p2", TransactionSide(trade_goods=1), TransactionSide()
    )
    assert done.players["p2"].trade_goods == 4
    assert not [label for label in _labels(done) if "Pillage" in label]
    done.phase = Phase.AGENDA
    assert "neighbors" in str(mentak.pillage_reason(done, "p1", "p2"))


@ruling("F_mentak/pillage/7", "F_mentak/pillage/7.1")
def test_pillage_trade_agreement_na_posiadacza_nie_na_wystawce(
    registry: StaticDataRegistry,
) -> None:
    """Bob (p3) uzupełnia commodities, Trade Agreement oddaje je Alice (p2) jako TG: Pillage na
    Alice (zdobyła TG), nie na Bobie (wymuszone oddanie to nie transakcja)."""
    from src.core.hooks import promissory_generic

    state = _three()
    state.players["p3"].commodities = 2
    promissory_generic.trade_agreement(state, registry, "p2", {"__owner": "p3"})
    labels = _labels(state)
    assert labels == ["Pillage"]
    offer = next(o for o in state.pending_offers if o.player_id == "p1")
    assert offer.ctx.get("player") == "p2"


@ruling("F_mentak/pillage/3")
def test_pillage_lazax_gate_folding_w_akcji_winnu(registry: StaticDataRegistry) -> None:
    """W akcji taktycznej Winnu z Lazax Gate Folding Mentak w systemie z wormhole alfa jest
    sąsiadem Winnu na Mecatol - może użyć Pillage."""
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("301", "26", wormholes=["alpha"])
    grid.place_system("101", "20")
    grid.build_edges()
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    try:
        state = _state()
        state.players["p2"].faction = "winnu"
        state.players["p2"].technologies = ["lgf"]
        state.active_player_id = "p2"
        state.systems = {
            "000": SystemState(position="000", system_id="18", space_units={"p2": {"carrier": 1}}),
            "101": SystemState(position="101", system_id="20"),
            "301": SystemState(position="301", system_id="26", space_units={"p1": {"cruiser": 1}}),
        }
        state.systems["000"].planet_owners = {}
        assert "neighbors" in str(mentak.pillage_reason(state, "p1", "p2"))
        state.tactical_step = TacticalStep.MOVEMENT
        assert mentak.pillage_reason(state, "p1", "p2") is None
    finally:
        board_graph.bind_grid_provider(previous)


@ruling("F_mentak/pillage/8", "abilities:pillage#1")
def test_pillage_za_kazde_zdobycie_tg(registry: StaticDataRegistry) -> None:
    state = _state()
    economy.gain_trade_goods(state, "p2", 1)
    state = _accept(state, "p1", "Pillage", {"take": "trade_good"})
    assert state.players["p2"].trade_goods == 3 and state.players["p1"].trade_goods == 2
    economy.gain_trade_goods(state, "p2", 1)
    assert [label for label in _labels(state) if "Pillage" in label] == ["Pillage"]


@ruling("F_mentak/pillage/10")
def test_pillage_nie_po_zamianie_commodities(registry: StaticDataRegistry) -> None:
    state = _state()
    economy.convert_commodities_to_trade_goods(state, "p2", 1)
    assert state.players["p2"].trade_goods == 4
    assert _labels(state) == []


@ruling("F_mentak/pillage/4", "F_mentak/promise-of-protection/2")
def test_pillage_transakcja_bez_tg_i_notka_w_rece(registry: StaticDataRegistry) -> None:
    """Mentak oddaje Promise of Protection (sama notka, bez TG): w ręce notka nie chroni."""
    state = _state()
    state.players["p1"].private.promissory_notes = ["pop"]
    done = transaction.resolve_transaction(
        state, _grid(), "p2", TransactionSide(promissory_note="pop"), TransactionSide()
    )
    assert "pop" in done.players["p2"].private.promissory_notes
    assert done.players["p2"].trade_goods == 3
    assert _labels(done) == ["Pillage (transaction partner)"]


@ruling("F_mentak/pillage/5")
def test_pillage_obie_strony_cudzej_transakcji(registry: StaticDataRegistry) -> None:
    state = _three()
    state.active_player_id = "p2"
    done = transaction.resolve_transaction(
        state, _grid(), "p3", TransactionSide(commodities=1), TransactionSide()
    )
    assert sorted(_labels(done)) == ["Pillage (transaction partner)", "Pillage (transaction)"]
    done = _accept(done, "p1", "Pillage (transaction)", {"take": "trade_good"})
    done = _accept(done, "p1", "Pillage (transaction partner)", {"take": "trade_good"})
    assert done.players["p1"].trade_goods == 3


@ruling("F_mentak/pillage/6")
def test_pillage_po_wlasnej_transakcji(registry: StaticDataRegistry) -> None:
    state = _state()
    done = transaction.resolve_transaction(
        state, _grid(), "p2", TransactionSide(trade_goods=1), TransactionSide()
    )
    assert _labels(done) == ["Pillage (transaction partner)"]
    done = _accept(done, "p1", "Pillage", {"take": "trade_good"})
    assert done.players["p1"].trade_goods == 1  # oddał 1, zabrał 1


# =========================================================================== Promise of Protection


@ruling("F_mentak/promise-of-protection/1", "promissory_notes:pop#2")
def test_promise_chroni_tylko_posiadacza(registry: StaticDataRegistry) -> None:
    """p2 (z Promise w strefie gry) handluje z p3: Pillage na p3 tak, na p2 nie."""
    state = _three()
    state.players["p2"].promissory_notes_in_play = ["pop"]
    state.active_player_id = "p2"
    done = transaction.resolve_transaction(
        state, _grid(), "p3", TransactionSide(commodities=1), TransactionSide()
    )
    assert _labels(done) == ["Pillage (transaction partner)"]
    assert "Promise of Protection" in str(mentak.pillage_reason(done, "p1", "p2"))


def _activate(state: GameState, player: str, position: str) -> GameState:
    state.active_player_id = player
    state.active_system = position
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject=player,
                  ctx={"player": player, "position": position})
    return state


@ruling("F_mentak/promise-of-protection/3", "promissory_notes:pop#3")
def test_promise_wraca_przy_aktywacji_bez_wrogich_dzialan(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].promissory_notes_in_play = ["pop"]
    state.systems["000"].space_units = {"p1": {"cruiser": 1}}
    _activate(state, "p2", "000")
    assert "pop" not in state.players["p2"].promissory_notes_in_play
    assert "pop" in state.players["p1"].private.promissory_notes


@ruling("F_mentak/promise-of-protection/4")
def test_promise_wraca_przy_samych_strukturach(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].promissory_notes_in_play = ["pop"]
    state.systems["000"].space_units = {}
    state.systems["000"].planet_units = {"mr": {"p1": {"pds": 1}}}
    _activate(state, "p2", "000")
    assert "pop" in state.players["p1"].private.promissory_notes


@ruling("F_mentak/promise-of-protection/5")
def test_promise_zostaje_przy_zetonie_z_diplomacy(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].promissory_notes_in_play = ["pop"]
    state.systems["000"].planet_owners = {"mr": "p1"}
    diplomacy._primary(state, None, "p1", {"system": "000", "planets": []})  # type: ignore[arg-type]
    assert "p2" in state.systems["000"].command_tokens
    assert state.players["p2"].promissory_notes_in_play == ["pop"]


@ruling("promissory_notes:pop#1")
def test_promise_zagrana_trafia_do_strefy_gry(registry: StaticDataRegistry) -> None:
    from src.core import promissory_play

    state = _state()
    state.active_player_id = "p2"
    state.players["p2"].private.promissory_notes = ["pop"]
    done, _ = promissory_play.play(state, registry, "p2", "pop", {})
    assert done.players["p2"].promissory_notes_in_play == ["pop"]


# ================================================================================ Mirror Computing


@ruling("F_mentak/mirror-computing/1", "technologies:mc#1")
def test_mirror_computing_nie_dla_celu_wydaj_tg(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["mc"]
    state.players["p1"].trade_goods = 5
    pay = objective_payment.auto_payment(state, registry, _grid(), "p1", "trade_routes")
    assert pay.trade_goods == 5
    done = objective_payment.pay_for_objective(state, registry, _grid(), "p1", "trade_routes")
    assert done.players["p1"].trade_goods == 0


# ============================================================================== Salvage Operations


def _salvage_grant(registry: StaticDataRegistry, trade_goods: int) -> GameState:
    state = _state()
    state.players["p1"].technologies = ["so"]
    state.players["p1"].trade_goods = trade_goods
    combat = _combat(state, {"cruiser": 1}, {})
    _lost(combat, "p2", "destroyer")
    mentak.salvage_produce(state, "p1", {"position": "000"})
    state.active_combat = None
    return state


@ruling("F_mentak/salvage-operations/5", "technologies:so#2")
def test_salvage_produkcja_platna(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "mentak", [], "destroyer", False)
    assert unit is not None and unit.cost is not None
    poor = _salvage_grant(registry, 0)
    with pytest.raises(ValueError):
        produce(poor, _grid(), registry, "p1", [ProductionOrder("destroyer", 1)])
    rich = _salvage_grant(registry, 3)
    done = produce(rich, _grid(), registry, "p1", [ProductionOrder("destroyer", 1)])
    assert done.systems["000"].space_units["p1"]["destroyer"] == 1
    assert done.players["p1"].trade_goods == 3 - int(unit.cost)


@ruling("F_mentak/salvage-operations/1", "technologies:so#1")
def test_salvage_remis_bez_skutku(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["so"]
    ctx = {"kind": "space", "winner": "", "attacker": "p1", "defender": "p2", "position": "000"}
    assert not mentak._fought_and_decided(state, "p1", ctx)
    assert not mentak._salvage_ready(state, "p1", ctx)
    triggers.fire(state, GameEvent.COMBAT, Moment.END, ctx=ctx)
    assert state.players["p1"].trade_goods == 1
    lost = {**ctx, "winner": "p2"}
    triggers.fire(state, GameEvent.COMBAT, Moment.END, ctx=lost)
    assert state.players["p1"].trade_goods == 2  # przegrana też daje TG


@ruling("F_mentak/salvage-operations/6")
def test_salvage_pusta_rezerwa_zdjecie_z_planszy(registry: StaticDataRegistry) -> None:
    from src.core import board_reinforcements
    from src.core.production import reinforcements_left

    state = _state()
    combat = _combat(state, {"cruiser": 1}, {})
    _lost(combat, "p2", "destroyer")
    left = reinforcements_left(state, "p1", "destroyer")
    assert left is not None
    state.systems["101"].space_units["p1"] = {"destroyer": left}  # cała rezerwa na planszy
    assert board_reinforcements.needs_board_source(state, "p1", "destroyer")
    assert mentak.salvage_types(state, "p1") == ["destroyer"]
    state.systems["101"].command_tokens = ["p1"]  # jedyne źródło ma żeton Mentaka
    assert mentak.salvage_types(state, "p1") == []


@ruling("F_mentak/salvage-operations/2", "F_mentak/salvage-operations/3",
        "F_mentak/salvage-operations/4")
def test_salvage_flagowiec_przeciwnika_i_bez_sil_naziemnych(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    combat = _combat(state, {"cruiser": 1}, {})
    for base_type in ("flagship", "infantry", "mech", "warsun"):
        _lost(combat, "p2", base_type)
    assert mentak.salvage_types(state, "p1") == ["flagship"]  # Fourth Moon Mentaka
    flagship = resolve_unit_variant(registry, "mentak", [], "flagship", False)
    assert flagship is not None and flagship.id == mentak.FLAGSHIP
    state.players["p1"].technologies = ["ws"]
    assert mentak.salvage_types(state, "p1") == ["flagship", "warsun"]


# ================================================================================= S'ula Mentarion


@ruling("F_mentak/sula-mentarion/1", "F_mentak/sula-mentarion/2",
        "leaders:mentakcommander#1")
def test_mentarion_wybiera_przeciwnik_bez_transakcji(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {mentak.COMMANDER: "unlocked"}
    state.players["p2"].private.promissory_notes = ["blue_sftt", "blue_ac"]
    state.players["p2"].trade_goods = 5
    ctx = {"kind": "space", "winner": "p1", "attacker": "p1", "defender": "p2",
           "position": "000"}
    triggers.fire(state, GameEvent.COMBAT_WON, Moment.AFTER, subject="p1", ctx=ctx)
    state = _accept(state, "p1", "Mentarion")
    give = next(o for o in state.pending_offers if o.player_id == "p2")
    assert give.mandatory
    state = triggers.accept_offer(state, "p2", give.id, {"note": "blue_ac"})
    assert "blue_ac" in state.players["p1"].private.promissory_notes
    assert not [label for label in _labels(state) if "Pillage" in label]  # to nie transakcja


@ruling("F_mentak/sula-mentarion/3", "leaders:mentakcommander#unlock")
def test_mentarion_czwarty_krazownik_z_salvage_za_pozno(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["so"]
    state.players["p1"].trade_goods = 5
    state.players["p2"].private.promissory_notes = ["blue_ac"]
    combat = _combat(state, {"cruiser": 3}, {})
    _lost(combat, "p2", "cruiser")
    ctx = {"kind": "space", "winner": "p1", "attacker": "p1", "defender": "p2",
           "position": "000"}
    triggers.fire(state, GameEvent.COMBAT_WON, Moment.AFTER, subject="p1", ctx=ctx)
    assert not any("Mentarion" in label for label in _labels(state))
    state = _accept(state, "p1", "Salvage")
    state.active_combat = None
    state = produce(state, _grid(), registry, "p1", [ProductionOrder("cruiser", 1)])
    assert leaders.refresh_unlocks(state, registry) == [mentak.COMMANDER]
    assert not any("Mentarion" in label for label in _labels(state))


@ruling("F_mentak/sula-mentarion/4", "F_mentak/sula-mentarion/4.1")
def test_mentarion_czwarty_krazownik_ze_sleeper_cell(registry: StaticDataRegistry) -> None:
    """Sleeper Cell stawia 4. krążownik w walce: commander odblokowany przed końcem walki
    (nawet gdy krążowniki potem giną) - po wygranej oferta S'ula Mentarion."""
    state = _state()
    state.players["p2"].private.promissory_notes = ["blue_ac"]
    combat = _combat(state, {"cruiser": 3}, {"cruiser": 1})
    _sleeper(state)
    unit_ops.remove_units(
        state, state.systems["000"], "space", "p2", "cruiser", 1, UnitCause.DESTROYED
    )
    mentak._place_sleepers(state, "p1")
    assert leaders.refresh_unlocks(state, registry) == [mentak.COMMANDER]
    unit_ops.remove_units(
        state, state.systems["000"], "space", "p1", "cruiser", 2, UnitCause.DESTROYED
    )
    assert combat is not None
    ctx = {"kind": "space", "winner": "p1", "attacker": "p1", "defender": "p2",
           "position": "000"}
    triggers.fire(state, GameEvent.COMBAT_WON, Moment.AFTER, subject="p1", ctx=ctx)
    assert any("Mentarion" in label for label in _labels(state))


# =================================================================================== Sleeper Cell


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/1", "leaders:mentakhero#1")
def test_sleeper_i_ambush_w_dowolnej_kolejnosci(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {mentak.HERO: "unlocked"}
    _combat(state, {"cruiser": 2}, {"carrier": 1})
    triggers.fire(state, GameEvent.COMBAT, Moment.START,
                  ctx={"kind": "space", "position": "000", "attacker": "p1", "defender": "p2"})
    labels = _labels(state)
    assert "Ambush" in labels and "Ipswitch: Sleeper Cell" in labels
    state = _accept(state, "p1", "Ambush", {"ships": ["cruiser:0"]})
    state = _accept(state, "p1", "Sleeper Cell")
    assert state.players["p1"].leader_states[mentak.HERO] == "purged"


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/2")
def test_sleeper_nie_za_statki_zniszczone_wczesniej(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {mentak.HERO: "unlocked"}
    combat = _combat(state, {"cruiser": 1}, {"carrier": 1})
    _lost(combat, "p2", "destroyer")
    mentak.sleeper_cell(state, "p1", {})
    assert not mentak._sleeper_pending(state, "p1", {})


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/3",
        "F_mentak/ipswitch-loose-cannon-sleeper-cell/6", "leaders:mentakhero#2")
def test_sleeper_mysliwce_bez_pojemnosci_i_bez_kosztu(registry: StaticDataRegistry) -> None:
    state = _state()
    combat = _combat(state, {"cruiser": 1}, {"carrier": 1, "fighter": 5})
    _sleeper(state)
    unit_ops.remove_units(
        state, state.systems["000"], "space", "p2", "fighter", 5, UnitCause.DESTROYED
    )
    mentak._place_sleepers(state, "p1")
    assert state.systems["000"].space_units["p1"] == {"cruiser": 1, "fighter": 5}
    assert state.players["p1"].trade_goods == 1  # bez kosztu
    assert state.pending_window is None  # pojemność nie jest sprawdzana w walce
    assert combat.step is not CombatStep.DONE


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/5")
def test_sleeper_walka_trwa_po_utracie_wszystkich_statkow(registry: StaticDataRegistry) -> None:
    state = _state()
    combat = _combat(state, {"cruiser": 1}, {"carrier": 2})
    _sleeper(state)
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p1", "cruiser", 1, UnitCause.DESTROYED)
    unit_ops.remove_units(state, system, "space", "p2", "carrier", 1, UnitCause.DESTROYED)
    combat.step = CombatStep.ASSIGN
    combat.log = [{"round": 1, "phase": "COMBAT", "rolls": {}, "hits": {}, "losses": {},
                   "sustained": {}}]
    after = battle._after_losses(state, _grid(), registry)
    assert after.systems["000"].space_units["p1"] == {"carrier": 1}
    assert after.active_combat is not None and after.active_combat.step is not CombatStep.DONE


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/7")
def test_sleeper_statek_zniszczony_w_tej_rundzie_wraca(registry: StaticDataRegistry) -> None:
    """Pełna rezerwa krążowników na planszy; Mentak traci 1, przeciwnik 1 w tej samej rundzie -
    po stratach obu stron krążownik wraca z rezerwy."""
    from src.core.production import reinforcements_left

    state = _state()
    left = reinforcements_left(state, "p1", "cruiser")
    assert left is not None
    combat = _combat(state, {"cruiser": left + 1}, {"cruiser": 1})
    _sleeper(state)
    system = state.systems["000"]
    assert reinforcements_left(state, "p1", "cruiser") == 0
    unit_ops.remove_units(state, system, "space", "p1", "cruiser", 1, UnitCause.DESTROYED)
    unit_ops.remove_units(state, system, "space", "p2", "cruiser", 1, UnitCause.DESTROYED)
    mentak._place_sleepers(state, "p1")
    assert system.space_units["p1"]["cruiser"] == left + 1
    assert combat is not None


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/7.1")
def test_sleeper_direct_hit_od_razu(registry: StaticDataRegistry) -> None:
    """Direct Hit Mentaka: zastępczy statek staje od razu (przed Sustain Damage Mentaka w tej
    rundzie), zwykłe straty przeciwnika z tej rundy - dopiero na koniec rundy."""
    from src.core import action_cards

    state = _state()
    combat = _combat(state, {"cruiser": 1}, {"dreadnought": 1, "destroyer": 1})
    _sleeper(state)
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p2", "destroyer", 1, UnitCause.DESTROYED)
    system.damaged_units = {"space": {"p2": {"dreadnought": 1}}}
    combat.sustained_ships = [{"player": "p2", "base_type": "dreadnought", "count": 1}]
    combat.step = CombatStep.ASSIGN
    state.players["p1"].private.action_cards = ["dh1"]
    action_cards.run_reaction(state, registry, "p1", "dh1", {"ship": "dreadnought"}, {})
    assert "dreadnought" not in state.systems["000"].space_units.get("p2", {})
    assert state.systems["000"].space_units["p1"] == {"cruiser": 1, "dreadnought": 1}
    mentak._place_sleepers(state, "p1")  # koniec rundy: tylko niszczyciel
    assert state.systems["000"].space_units["p1"] == {
        "cruiser": 1, "dreadnought": 1, "destroyer": 1,
    }


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/8")
def test_sleeper_pusta_rezerwa_z_planszy_nieuszkodzony(registry: StaticDataRegistry) -> None:
    from src.core import damage
    from src.core.production import reinforcements_left

    state = _state()
    combat = _combat(state, {"cruiser": 1}, {"dreadnought": 1})
    left = reinforcements_left(state, "p1", "dreadnought")
    assert left is not None
    state.systems["101"].space_units["p1"] = {"dreadnought": left}
    state.systems["101"].damaged_units = {"space": {"p1": {"dreadnought": 1}}}
    _sleeper(state)
    unit_ops.remove_units(
        state, state.systems["000"], "space", "p2", "dreadnought", 1, UnitCause.DESTROYED
    )
    inputs = mentak.sleeper_inputs(state, registry, "p1", {})
    assert len(inputs) == 1
    source = next(o["value"] for o in inputs[0]["options"] if o["value"] != "none")
    mentak._place_sleepers(state, "p1", {"params": {inputs[0]["key"]: source}})
    assert state.systems["000"].space_units["p1"]["dreadnought"] == 1
    assert damage.damaged_count(state.systems["000"], "space", "p1", "dreadnought") == 0
    assert combat is not None


@ruling("F_mentak/salvage-operations/2",
        "F_mentak/ipswitch-loose-cannon-sleeper-cell/10",
        "F_mentak/ipswitch-loose-cannon-sleeper-cell/11")
def test_sleeper_typy_statkow(registry: StaticDataRegistry) -> None:
    state = _state()
    combat = _combat(state, {"cruiser": 1}, {})
    _sleeper(state)
    for base_type in ("flagship", "infantry", "pds", "warsun", "cruiser"):
        _lost(combat, "p2", base_type)
    assert mentak._fresh_sleepers(state, "p1") == ["flagship", "cruiser"]
    state.players["p1"].technologies = ["ws"]
    assert mentak._fresh_sleepers(state, "p1") == ["flagship", "warsun", "cruiser"]
    mentak._place_sleepers(state, "p1")
    assert state.systems["000"].space_units["p1"]["flagship"] == 1  # Fourth Moon


def _uf_state(registry: StaticDataRegistry) -> GameState:
    state = _state()
    state.players["p1"].private.secret_objectives = ["uf"]
    return state


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/9")
def test_sleeper_fourth_moon_zniszczony_i_postawiony_bez_unveil(
    registry: StaticDataRegistry,
) -> None:
    state = _uf_state(registry)
    combat = _combat(state, {"flagship": 1, "cruiser": 1}, {"flagship": 1})
    _sleeper(state)
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p1", "flagship", 1, UnitCause.DESTROYED)
    unit_ops.remove_units(state, system, "space", "p2", "flagship", 1, UnitCause.DESTROYED)
    mentak._place_sleepers(state, "p1")
    assert system.space_units["p1"]["flagship"] == 1
    objective_events.on_combat_end(state, _grid(), combat, "p1")
    assert "uf" not in state.players["p1"].scored_secrets


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/9.1")
def test_sleeper_fourth_moon_postawiony_w_walce_daje_unveil(
    registry: StaticDataRegistry,
) -> None:
    state = _uf_state(registry)
    combat = _combat(state, {"cruiser": 1}, {"flagship": 1})
    _sleeper(state)
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p2", "flagship", 1, UnitCause.DESTROYED)
    mentak._place_sleepers(state, "p1")
    objective_events.on_combat_end(state, _grid(), combat, "p1")
    assert "uf" in state.players["p1"].scored_secrets


@ruling("F_mentak/ipswitch-loose-cannon-sleeper-cell/12")
def test_sleeper_przeciwnik_moze_sie_wycofac(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mentak")
    flow.player(lambda p: p["leader_states"].update(mentakhero="unlocked"))
    a, b = flow.plain_pair()
    flow.space(b, flow.other, {"destroyer": 1})  # cel odwrotu przeciwnika
    flow.space(a, flow.me, {"dreadnought": 2})
    flow.space(a, flow.other, {"destroyer": 2})
    flow.activate(a)
    flow.to_step("SPACE_COMBAT")
    flow.post("/tactical/battle/start", {})
    flow.accept("Sleeper Cell")
    flow.decline_all()
    flow.fight(stop=lambda: flow.battle().get("step") == "ANNOUNCE")
    assert flow.battle()["step"] == "ANNOUNCE"
    flow.post("/tactical/battle/announce-retreat", {"faction": flow.other, "announce": True})
    assert flow.other in flow.state()["active_combat"]["retreating"]


@ruling("leaders:mentakhero#unlock")
def test_ipswitch_odblokowanie(registry: StaticDataRegistry) -> None:
    fn = leaders.unlock_predicate(registry, mentak.HERO)
    assert fn is not None
    state = _state()
    state.players["p1"].scored_secrets = ["a", "b"]
    assert not fn(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert fn(state, registry, "p1")


# ================================================================================== Moll Terminus


@ruling("F_mentak/moll-terminus/1", "units:mentak_mech#1")
def test_moll_terminus_mech_bez_sustain_przeciw_space_cannon_defense(
    registry: StaticDataRegistry,
) -> None:
    from src.core import invasion

    state = _state()
    state.active_player_id = "p2"
    state.active_system = "000"
    state.tactical_step = TacticalStep.INVASION
    system = state.systems["000"]
    system.space_units = {"p2": {"carrier": 1}}
    system.planet_units = {"mr": {"p1": {"mech": 1, "pds": 1}, "p2": {"mech": 1}}}
    system.planet_owners = {"mr": "p1"}
    state = invasion.begin_invasion(state, _grid(), registry)
    assert state.invasion is not None
    state.invasion.phase = InvasionPhase.SPACE_CANNON_DEFENSE
    state.invasion.defense_pending = {"mr": 1}
    units = invasion._ground_units(state, _grid(), registry, "mr", "p2")
    assert not units["mech"].sustain
    assert invasion.required_defense_hits(state, _grid(), registry, "mr") == 1
    with pytest.raises(ValueError):
        invasion.assign_defense_hits(
            state, _grid(), registry, "mr", sustain={"mech": 1}, destroy={},
            destroy_damaged={},
        )


@ruling("units:mentak_flagship#1")
def test_fourth_moon_tylko_cudze_statki(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = []
    state.systems["000"].space_units = {"p1": {"flagship": 1, "dreadnought": 1},
                                        "p2": {"dreadnought": 1}}
    for pid, expected in (("p1", True), ("p2", False)):
        units = battle.combat_units(
            state, _grid(), registry, kind="space", position="000", planet=None, player_id=pid
        )
        assert next(u for u in units if u.base_type == "dreadnought").sustain is expected


# ========================================================================================= Corsair


def _corsair_state() -> GameState:
    state = _three()
    state.players["p1"].breakthrough_unlocked = True
    state.players["p1"].technologies = ["cr2"]
    return state


@ruling("F_mentak/corsair/1", "breakthroughs:mentakbt#2")
def test_corsair_przez_statki_dowolnego_gracza(registry: StaticDataRegistry) -> None:
    """Aktywny system ma statki p2; po drodze statki p3 - Corsair też przelatuje."""
    state = _corsair_state()
    state.active_system = "301"
    state.systems["301"].space_units = {"p2": {"destroyer": 1}}
    ctx = {"position": "101", "base_type": "cruiser"}  # 101: statki p2 i p3
    state.systems["101"].space_units = {"p3": {"cruiser": 1}}
    assert rules_hooks.permits(rules_hooks.POINT_MOVEMENT_PASS_FOREIGN_SHIPS, state, "p1", ctx)


@ruling("F_mentak/corsair/2")
def test_corsair_z_wlasnymi_jednostkami_w_aktywnym(registry: StaticDataRegistry) -> None:
    state = _corsair_state()
    state.active_system = "301"
    state.systems["301"].space_units = {"p1": {"carrier": 1}, "p2": {"destroyer": 1}}
    ctx = {"position": "101", "base_type": "cruiser"}
    assert mentak.corsair_passage(state, "p1", ctx)


@ruling("breakthroughs:mentakbt#1")
def test_corsair_karta_na_cruiser_ii(registry: StaticDataRegistry) -> None:
    corsair = resolve_unit_variant(registry, "mentak", ["cr2"], "cruiser", True)
    assert corsair is not None and corsair.id == mentak.CORSAIR
    assert resolve_unit_variant(registry, "mentak", [], "cruiser", True).id != mentak.CORSAIR  # type: ignore[union-attr]


# ======================================================================================= Suffi An


@ruling("leaders:mentakagent#1", "leaders:mentakagent#2")
def test_suffi_an_po_pillage(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {mentak.AGENT: "unlocked"}
    state.decks.action_card_deck = ["sh1", "sh2", "sh3"]
    hands = {pid: len(state.players[pid].private.action_cards) for pid in ("p1", "p2")}
    economy.gain_trade_goods(state, "p2", 1)
    state = _accept(state, "p1", "Pillage", {"take": "trade_good"})
    state = _accept(state, "p1", "Suffi An")
    for pid in ("p1", "p2"):
        assert len(state.players[pid].private.action_cards) == hands[pid] + 1
    assert state.players["p1"].leader_states[mentak.AGENT] == "exhausted"



@ruling("F_mentak/ambush/5")
def test_ambush_statki_rzucaja_tez_w_pierwszej_rundzie(registry: StaticDataRegistry) -> None:
    state = _state()
    _combat(state, {"cruiser": 2}, {"carrier": 3})
    state.rng_seed = 3
    mentak.ambush(state, "p1", {"params": {"ships": ["cruiser:0", "cruiser:1"]}})
    assert state.active_combat is not None
    assert state.active_combat.step is CombatStep.ROLL and state.active_combat.round == 1
    after = battle.roll_round(state, _grid(), registry)
    assert after.active_combat is not None
    entry = next(e for e in after.active_combat.log if e["phase"] != "AMBUSH")
    assert sum(len(r["dice"]) for r in entry["rolls"]["p1"]) == 2  # cruisers roll again
    assert entry["round"] == 1


@ruling("F_mentak/pillage/9")
def test_pillage_za_kazde_tg_ze_scavenge_saar(registry: StaticDataRegistry) -> None:
    """Saar (sąsiad Mentaka) zdobywa dwie planety w jednej turze - Pillage przy każdym TG."""
    from src.core import control

    state = _state()
    state.players["p2"].faction = "saar"
    state.players["p2"].trade_goods = 2
    control.set_planet_control(state, "101", "vefutii", "p2", registry)
    assert state.players["p2"].trade_goods == 3
    assert [x for x in _labels(state) if "Pillage" in x] == ["Pillage"]
    state = _accept(state, "p1", "Pillage", {"take": "trade_good"})
    assert state.players["p2"].trade_goods == 2
    control.set_planet_control(state, "301", "thibah", "p2", registry)
    assert state.players["p2"].trade_goods == 3
    assert [x for x in _labels(state) if "Pillage" in x] == ["Pillage"]


@ruling("F_mentak/fourth-moon/1")
def test_fourth_moon_sustain_zakazany_w_rundzie_jej_zniszczenia(
    registry: StaticDataRegistry,
) -> None:
    """Mentak (obrońca) przypisuje pierwszy i traci Fourth Moon; atakujący, przypisując
    potem w TEJ SAMEJ rundzie, nadal nie może użyć Sustain Damage."""
    state = _state()
    state.players["p1"].technologies = []
    state.systems["000"].space_units = {"p1": {"flagship": 1}, "p2": {"dreadnought": 1}}
    state.active_system = "000"
    combat = ActiveCombat(kind="space", position="000", attacker="p2", defender="p1")
    combat.step = CombatStep.ROLL
    combat.pending_hits = {"p1": 1, "p2": 1}
    state.active_combat = combat
    state = battle._open_assign(state, _grid(), registry)
    assert state.pending_window is not None and state.pending_window.current_responder == "p1"
    state = battle.assign_combat_hits(
        state, _grid(), registry, "p1", sustain={}, destroy={"flagship": 1}, destroy_damaged={}
    )
    assert "flagship" not in state.systems["000"].space_units.get("p1", {})
    assert state.pending_window is not None and state.pending_window.current_responder == "p2"
    with pytest.raises(ValueError):
        battle.assign_combat_hits(
            state.clone(), _grid(), registry, "p2",
            sustain={"dreadnought": 1}, destroy={}, destroy_damaged={},
        )


@ruling("F_mentak/pillage/11")
def test_pillage_blokuje_wydawanie_tg_do_rozstrzygniecia(registry: StaticDataRegistry) -> None:
    state = _state()
    economy.gain_trade_goods(state, "p2", 1)
    assert "Pillage" in _labels(state)
    with pytest.raises(ValueError, match="Pillage"):
        economy.spend_trade_goods(state, "p2", 1)
    state = _accept(state, "p1", "Pillage", {"take": "trade_good"})
    economy.spend_trade_goods(state, "p2", 1)
