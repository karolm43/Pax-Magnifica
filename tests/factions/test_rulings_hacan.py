"""The Emirates of Hacan — rulingi ``docs/rules_tirules/F_hacan.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Podstawowe testy komponentów są w ``test_hacan.py`` i
``test_flows_hacan.py`` (tam też część znaczników). Statusy bez testu:
``tests/rulings_status.json`` (Hacan: brak - każdy punkt ma test).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    active_effects,
    board_graph,
    economy,
    faction_components,
    hand_limit,
    leaders,
    movement,
    transaction,
    triggers,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    ExplorationState,
    ExploreCurrent,
    GameState,
    Phase,
    PlayerState,
    SystemState,
)
from src.core.hooks import promissory_generic
from src.core.hooks.factions import hacan
from src.core.neighbors import neighbors_of
from src.core.promissory_play import POLITICAL_SECRET_EFFECT
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards import diplomacy
from src.core.transaction import TransactionSide
from tests.factions.flow_harness import Flow, Json
from tests.factions.test_hacan import _grid, _state
from tests.factions.test_hacan import registry as registry  # noqa: F401 - fixture modułu
from tests.rulings import ruling


def _cards(n: int, prefix: str = "ac") -> list[str]:
    return [f"{prefix}{i}" for i in range(n)]


def _convoys_state(holder_note: str = "play") -> GameState:
    """p1 = Letnev (aktywny, bez Guild Ships), p2 = Sol z Trade Convoys; p3 = Hacan (właściciel)."""
    state = _state("letnev")
    state.players["p3"] = PlayerState(player_id="p3", color="green", faction="hacan")
    state.seating_order = ["p1", "p2", "p3"]
    if holder_note == "play":
        state.players["p2"].promissory_notes_in_play = [hacan.CONVOYS]
    else:
        state.players["p2"].private.promissory_notes = [hacan.CONVOYS]
    return state


# ================================================================================ Masters of Trade


@ruling("F_hacan/masters-of-trade/1", "abilities:master_of_trade#1")
def test_masters_of_trade_bez_wydania_zetonu(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Follow Trade bez żetonu: nie ma zdarzenia „wydano żeton z puli strategii”, więc nic, co na
    nie czeka (commander Muaat przez Alliance), nie daje trade good."""
    fired: list[tuple[GameEvent, str | None]] = []
    original = triggers.fire

    def spy(state: GameState, event: GameEvent, moment: Moment, **kw: Any) -> Any:
        fired.append((event, kw.get("subject")))
        return original(state, event, moment, **kw)

    monkeypatch.setattr(triggers, "fire", spy)
    flow = Flow(registry, "hacan")
    flow.player(lambda p: p.update(strategy_cards=[5]), flow.other)
    flow.player(lambda p: p.update(strategic_cc=1))
    flow.edit(lambda s: None, active=flow.other)
    flow.post("/strategy/play", {"player_id": flow.other, "initiative": 5})
    if flow.state()["pending_strategy"] is not None:
        flow.post("/strategy/primary-step", {
            "player_id": flow.other, "payload": {"players": []},
        })
    fired.clear()
    flow.post("/strategy/secondary", {"player_id": flow.me, "execute": True})
    assert flow.state()["players"][flow.me]["strategic_cc"] == 1
    assert (GameEvent.STRATEGY_TOKEN_SPENT, flow.me) not in fired


# ===================================================================================== Guild Ships


@ruling("F_hacan/guild-ships/1", "abilities:guild_ships#1")
def test_guild_ships_nie_czyni_sasiadami(registry: StaticDataRegistry) -> None:
    state = _state()
    assert "p2" not in neighbors_of("p1", state, _grid())
    assert transaction.can_transact_with(state, _grid(), "p1", "p2")


@ruling("F_hacan/guild-ships/2")
def test_guild_ships_inicjuje_kazda_strona(registry: StaticDataRegistry) -> None:
    side = TransactionSide(trade_goods=1)
    state = _state()
    state.active_player_id = "p2"  # nie-sąsiad Hacan jest aktywny i sam zaczyna
    assert transaction.can_transact_with(state, _grid(), "p2", "p1")
    done = transaction.resolve_transaction(state, _grid(), "p1", TransactionSide(), side)
    assert done.players["p2"].trade_goods == 2


@ruling("F_hacan/guild-ships/3")
def test_guild_ships_jedna_transakcja_na_ture(registry: StaticDataRegistry) -> None:
    side = TransactionSide(trade_goods=1)
    done = transaction.resolve_transaction(_state(), _grid(), "p2", side, TransactionSide())
    assert not transaction.can_transact_with(done, _grid(), "p1", "p2")
    with pytest.raises(ValueError, match="one per"):
        transaction.validate_transaction(done, _grid(), "p2", side, TransactionSide())


# ======================================================================================== Arbiters


@ruling("F_hacan/arbiters/1", "abilities:arbiters#1")
def test_arbiters_dowolna_liczba_kart_akcji(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].private.action_cards = _cards(4)
    side = TransactionSide(action_cards=tuple(_cards(4)))
    done = transaction.resolve_transaction(state, _grid(), "p2", side, TransactionSide())
    assert done.players["p2"].private.action_cards == _cards(4)
    assert done.players["p1"].private.action_cards == []


@ruling("F_hacan/arbiters/2")
def test_arbiters_odbiorca_ponad_limit_odrzuca(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].private.action_cards = _cards(7, "x")
    side = TransactionSide(action_cards=("sabo1",))
    done = transaction.resolve_transaction(state, _grid(), "p2", side, TransactionSide())
    assert len(done.players["p2"].private.action_cards) == 8  # wolno przyjąć
    assert hand_limit.action_card_excess(done, "p2") == 1  # i od razu trzeba odrzucić
    assert hand_limit.over_limit_reason(done, "p2") is not None


@ruling("F_hacan/arbiters/3")
def test_arbiters_hacan_nie_oddaje_nadwyzki(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].private.action_cards = _cards(8)
    side = TransactionSide(action_cards=("ac0",))
    with pytest.raises(ValueError, match="discard"):
        transaction.validate_transaction(state, _grid(), "p2", side, TransactionSide())


@ruling("F_hacan/arbiters/4")
def test_arbiters_dziala_pod_political_secret(registry: StaticDataRegistry) -> None:
    state = _state()
    active_effects.add_effect(state, POLITICAL_SECRET_EFFECT, Duration.AGENDA, owner="p1")
    side = TransactionSide(action_cards=("sabo1",))
    done = transaction.resolve_transaction(state, _grid(), "p2", side, TransactionSide())
    assert done.players["p2"].private.action_cards == ["sabo1"]


# =================================================================================== Trade Convoys


@ruling(
    "F_hacan/trade-convoys/1", "F_hacan/trade-convoys/2", "promissory_notes:convoys#2",
)
def test_trade_convoys_bez_sasiedztwa_inicjuje_kazdy(registry: StaticDataRegistry) -> None:
    state = _convoys_state()
    assert "p1" not in neighbors_of("p2", state, _grid())
    assert transaction.can_transact_with(state, _grid(), "p1", "p2")  # inicjuje nie-posiadacz
    state.active_player_id = "p2"
    assert transaction.can_transact_with(state, _grid(), "p2", "p1")  # inicjuje posiadacz


@ruling("F_hacan/trade-convoys/3")
def test_trade_convoys_jedna_transakcja_na_ture(registry: StaticDataRegistry) -> None:
    side = TransactionSide(trade_goods=1)
    state = _convoys_state()
    done = transaction.resolve_transaction(state, _grid(), "p2", side, TransactionSide())
    assert not transaction.can_transact_with(done, _grid(), "p1", "p2")


@ruling("F_hacan/trade-convoys/4")
def test_trade_convoys_na_rece_bez_efektu(registry: StaticDataRegistry) -> None:
    state = _convoys_state(holder_note="hand")
    assert not transaction.can_transact_with(state, _grid(), "p1", "p2")


@ruling("F_hacan/trade-convoys/6", "promissory_notes:convoys#3")
def test_trade_convoys_wraca_przy_samych_strukturach(registry: StaticDataRegistry) -> None:
    state = _convoys_state()
    planet = registry.systems["20"].planets[0]
    state.systems["101"] = SystemState(
        position="101", system_id="20", planet_owners={planet: "p3"},
        planet_units={planet: {"p3": {"space_dock": 1}}},
    )
    triggers.fire(
        state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
        ctx={"player": "p2", "position": "101"},
    )
    assert hacan.CONVOYS not in state.players["p2"].promissory_notes_in_play
    assert hacan.CONVOYS in state.players["p3"].private.promissory_notes
    # System bez jednostek Hacan - notka zostaje.
    again = _convoys_state()
    triggers.fire(
        again, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
        ctx={"player": "p2", "position": "000"},
    )
    assert hacan.CONVOYS in again.players["p2"].promissory_notes_in_play


@ruling("F_hacan/trade-convoys/7")
def test_trade_convoys_zeton_z_diplomacy_nie_zwraca(registry: StaticDataRegistry) -> None:
    state = _convoys_state()
    state.systems["000"].space_units["p3"] = {"carrier": 1}  # jednostki Hacan w systemie
    diplomacy._primary(state, None, "p1", {"system": "000", "planets": []})  # type: ignore[arg-type]
    assert "p2" in state.systems["000"].command_tokens
    assert hacan.CONVOYS in state.players["p2"].promissory_notes_in_play


# ============================================================================ Quantum Datahub Node


def _qdn_state() -> GameState:
    state = _state()
    state.phase = Phase.STRATEGY
    state.players["p3"] = PlayerState(player_id="p3", color="green", faction="letnev")
    state.seating_order = ["p1", "p2", "p3"]
    state.players["p1"].technologies.append(hacan.QDN)
    state.players["p1"].strategic_cc = 1
    state.players["p1"].strategy_cards = [1]
    state.players["p2"].strategy_cards = [8]
    state.players["p3"].strategy_cards = [5]
    return state


@ruling(
    "F_hacan/quantum-datahub-node/1", "technologies:qdn#1", "technologies:qdn#2",
)
def test_qdn_wymiana_kart_tg_z_karty_zostaja(registry: StaticDataRegistry) -> None:
    state = _qdn_state()
    state.strategy_card_tg = {}  # TG z karty 8 zabrał p2 przy wyborze (faza strategii)
    state.players["p2"].trade_goods = 4
    assert hacan._qdn_ready(state, "p1", {"phase": "strategy"})
    hacan.quantum_datahub_node(state, "p1", {"params": {"give": 1, "take": "p2|8"}})
    assert state.players["p1"].strategy_cards == [8]
    assert state.players["p2"].strategy_cards == [1]
    assert state.players["p1"].trade_goods == 0 and state.players["p1"].strategic_cc == 0
    assert state.players["p2"].trade_goods == 7  # tylko 3 TG z QDN, nic z karty


@ruling("F_hacan/quantum-datahub-node/2")
def test_qdn_hacan_wybiera_karty_w_wiekszej_grze(registry: StaticDataRegistry) -> None:
    state = _qdn_state()
    inputs = hacan.qdn_inputs(state, registry, "p1", {})
    take = {o["value"] for o in inputs[1]["options"]}
    assert take == {"p2|8", "p3|5"}  # karty WSZYSTKICH innych graczy do wyboru
    hacan.quantum_datahub_node(state, "p1", {"params": {"give": 1, "take": "p3|5"}})
    assert state.players["p3"].strategy_cards == [1]
    assert state.players["p2"].strategy_cards == [8]


@ruling("F_hacan/quantum-datahub-node/3")
def test_qdn_trzy_tg_przed_wydaniem_zetonu(registry: StaticDataRegistry) -> None:
    state = _qdn_state()
    state.players["p1"].trade_goods = 2
    assert not hacan._qdn_ready(state, "p1", {"phase": "strategy"})
    with pytest.raises(ValueError, match="3 trade goods"):
        hacan.quantum_datahub_node(state, "p1", {"params": {"give": 1, "take": "p2|8"}})
    assert state.players["p1"].strategic_cc == 1  # żeton nie został wydany


# =============================================================================== Production Biomes


@ruling("technologies:pm#1", "technologies:pm#2")
def test_production_biomes(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies.append(hacan.BIOMES)
    state.players["p1"].strategic_cc = 1
    hacan.production_biomes(state, registry, "p1", {"player": "p2"})
    assert state.players["p1"].trade_goods == 7 and state.players["p2"].trade_goods == 3
    assert state.players["p1"].strategic_cc == 0
    assert hacan.BIOMES in state.players["p1"].exhausted_technologies
    with pytest.raises(ValueError, match="exhausted"):
        hacan.production_biomes(state, registry, "p1", {"player": "p2"})


# ================================================================================ Wrath of Kenara


@ruling("F_hacan/wrath-of-kenara/1")
def test_wrath_of_kenara_raz_na_kosc(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].trade_goods = 5
    state.systems["000"].space_units["p1"] = {"flagship": 1}
    state.active_combat = ActiveCombat(
        kind="space", position="000", attacker="p1", defender="p2",
        rolls={"p1": [{
            "baseType": "flagship", "dice": [3, 5], "hitsOn": 7, "modifier": 0,
            "boosted": {hacan.FLAGSHIP: [0]},
        }]},
    )
    inputs = hacan.kenara_inputs(state, registry, "p1", {})
    assert [o["value"] for o in inputs[0]["options"]] == ["0:1"]  # kość 0 już ma +1
    # Kilka kości naraz: po 1 TG na każdą (multi do liczby kości/TG).
    state.active_combat.rolls["p1"][0]["boosted"] = {}
    inputs = hacan.kenara_inputs(state, registry, "p1", {})
    assert [o["value"] for o in inputs[0]["options"]] == ["0:0", "0:1"]


# =========================================================================== Carth of Golden Sands


@ruling("F_hacan/carth-of-golden-sands/1", "leaders:hacanagent#1")
def test_carth_uzupelnia_pelne_commodities_i_otwiera_trade_agreement(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.players["p2"].commodity_value = registry.factions["sol"].commodities
    state.players["p2"].commodities = economy.commodity_value(state, "p2")
    assert state.players["p2"].commodities > 0
    full = state.players["p2"].commodities
    hacan.carth_of_golden_sands(state, registry, "p1", {"target": "p2"})
    assert state.players["p2"].commodities == full  # nic nie przybyło
    windows = promissory_generic.replenished(state)
    assert [w.ctx.get("player") for w in windows] == ["p2"]  # „when … replenishes” i tak


@ruling("F_hacan/carth-of-golden-sands/2")
def test_carth_hacan_maks_szesc_commodities(registry: StaticDataRegistry) -> None:
    state = _state()
    assert registry.factions["hacan"].commodities == 6
    state.players["p1"].commodity_value = registry.factions["hacan"].commodities
    state.players["p1"].commodities = 5
    hacan.carth_of_golden_sands(state, registry, "p1", {"target": "self"})
    assert state.players["p1"].commodities == 6


@ruling("F_hacan/carth-of-golden-sands/3")
def test_carth_nie_w_trakcie_innej_zdolnosci(registry: StaticDataRegistry) -> None:
    state = _state()
    assert hacan._agent_window(state, registry, "p1") is None
    state.exploration = ExplorationState(
        player_id="p1", position="000",
        current=ExploreCurrent(planet="mr", deck="industrial", card_id="x"),
    )
    assert hacan._agent_window(state, registry, "p1") is not None
    state.exploration.current = None  # karta rozstrzygnięta - znów wolno
    assert hacan._agent_window(state, registry, "p1") is None


# =========================================================================== Gila the Silvertongue


@ruling("F_hacan/gila-the-silvertongue/1", "F_hacan/gila-the-silvertongue/1.1")
def test_gila_glosy_do_tego_samego_wyniku(registry: StaticDataRegistry) -> None:
    """Dodatkowe głosy to modyfikator TEGO SAMEGO oddania głosów (jeden wynik); 0 głosów = 0."""
    state = _state()
    state.players["p1"].trade_goods = 3
    hacan.gila_the_silvertongue(state, registry, "p1", {"trade_goods": 2})
    assert hacan.gila_votes(state, "p1", {"base_votes": 3}) == 4
    assert hacan.gila_votes(state, "p1", {"base_votes": 0}) == 0


@ruling("leaders:hacancommander#unlock")
def test_gila_odblokowanie_dziesiec_tg(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].trade_goods = 9
    assert not hacan._commander_unlocked(state, registry, "p1")
    state.players["p1"].trade_goods = 10
    assert hacan._commander_unlocked(state, registry, "p1")


@ruling("F_hacan/gila-the-silvertongue/1.2")
def test_gila_przez_alliance(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")
    color = flow.state()["players"][flow.me]["color"]
    note = flow.give_note(f"{color}_an", flow.other)

    def alliance(s: Json) -> None:
        s["players"][flow.me]["leader_states"]["hacancommander"] = "unlocked"
        rival = s["players"][flow.other]
        rival["private"]["promissory_notes"].remove(note)
        rival["promissory_notes_in_play"].append(note)
        rival["trade_goods"] = 3

    flow.edit(alliance)
    _to_vote_keep_rival(flow)
    row = flow.playable(flow.other)["hacancommander"]
    assert row["playable"], row["reason"]
    flow.use("leader", "hacancommander", {"trade_goods": 1}, pid=flow.other)
    state = flow.state()
    assert state["players"][flow.other]["trade_goods"] == 2
    effect = next(e for e in state["active_effects"] if e["key"] == hacan.GILA_VOTES)
    assert effect["owner"] == flow.other  # głosy doliczane do oddania głosów posiadacza
    assert state["players"][flow.me]["leader_states"]["hacancommander"] == "unlocked"


def _to_vote_keep_rival(flow: Flow) -> None:
    """Jak ``_to_vote``, ale głos ma rywal (Hacan się wstrzymuje, gdy głosuje pierwszy)."""
    flow.post("/god-mode/patch", {"custodians_removed": True})
    flow.to_status()
    flow.finish_status()
    flow.post("/agenda/reveal", {"player_id": flow.state()["speaker_id"]})
    for _ in range(6):
        agenda = flow.state()["agenda"]
        speaker = {"player_id": flow.state()["speaker_id"]}
        if agenda["step"] == "VOTE" and agenda["unresolvable"]:
            flow.post("/agenda/discard", speaker)
            flow.post("/agenda/reveal", speaker)
            continue
        if agenda["step"] == "VOTE":
            break
        flow.post("/agenda/continue", speaker, ok=False)
    if flow.state()["active_player_id"] == flow.me:
        flow.post("/agenda/abstain", {"player_id": flow.me})
    assert flow.state()["active_player_id"] == flow.other


# ========================================================================= Harrugh Gefhara (hero)


@ruling(
    "F_hacan/harrugh-gefhara-galactic-securities-net/1",
    "leaders:hacanhero#1", "leaders:hacanhero#2",
)
def test_harrugh_gefhara_limity_produkcji_zostaja(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")
    flow.player(lambda p: p["leader_states"].update(hacanhero="unlocked"))
    flow.activate(flow.home)
    flow.to_step("PRODUCTION")
    flow.use("leader", "hacanhero")
    assert flow.state()["players"][flow.me]["leader_states"]["hacanhero"] == "purged"
    too_many = flow.post("/tactical/produce", {"faction": flow.me, "orders": [
        {"baseType": "fighter", "count": 40, "zone": "space"},
    ]}, ok=False)
    assert too_many.status_code == 422
    assert "limit" in too_many.text.lower()
    before = flow.state()["players"][flow.me]
    flow.post("/tactical/produce", {"faction": flow.me, "orders": [
        {"baseType": "cruiser", "count": 1, "zone": "space"},
    ]})
    after = flow.state()["players"][flow.me]
    assert after["trade_goods"] == before["trade_goods"]
    assert after["exhausted_planets"] == before["exhausted_planets"]


@ruling("leaders:hacanhero#unlock")
def test_harrugh_gefhara_odblokowanie(registry: StaticDataRegistry) -> None:
    fn = leaders.unlock_predicate(registry, hacan.HERO)
    assert fn is not None
    state = _state()
    state.players["p1"].scored_secrets = ["a", "b"]
    assert not fn(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert fn(state, registry, "p1")


# ================================================================================ Pride of Kenara


def _pride_state(registry: StaticDataRegistry) -> tuple[GameState, str]:
    state = _state()
    state.players["p1"].controlled_planets = ["mr"]
    state.systems["000"].planet_owners = {"mr": "p1"}
    state.systems["000"].planet_units = {"mr": {"p1": {"mech": 1, "pds": 1, "space_dock": 1}}}
    state.systems["101"] = SystemState(position="101", system_id="20")
    dest = registry.systems["20"].planets[0]
    state.systems["101"].planet_owners = {dest: "p1"}
    return state, dest


@ruling("F_hacan/pride-of-kenara/1", "units:hacan_mech#1", "units:hacan_mech#2")
def test_pride_of_kenara_struktury_tez(registry: StaticDataRegistry) -> None:
    state, dest = _pride_state(registry)
    side = TransactionSide(planets=(f"mr>{dest}",))
    done = transaction.resolve_transaction(state, _grid(), "p2", side, TransactionSide())
    assert done.systems["101"].planet_units[dest]["p1"] == {
        "mech": 1, "pds": 1, "space_dock": 1,
    }
    assert not done.systems["000"].planet_units.get("mr", {}).get("p1")


@ruling("F_hacan/pride-of-kenara/2")
def test_pride_of_kenara_nie_w_trakcie_walki(registry: StaticDataRegistry) -> None:
    state, dest = _pride_state(registry)
    state.active_combat = ActiveCombat(kind="space", position="301", attacker="p2", defender="p1")
    side = TransactionSide(planets=(f"mr>{dest}",))
    with pytest.raises(ValueError, match="during combat"):
        transaction.validate_transaction(state, _grid(), "p2", side, TransactionSide())


@ruling("F_hacan/pride-of-kenara/3")
def test_pride_of_kenara_w_gravity_rift_rzut(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, dest = _pride_state(registry)
    rolled: list[dict[str, int]] = []

    def roll(_s: GameState, _pid: str, units: dict[str, int]) -> dict[str, int]:
        rolled.append(dict(units))
        return {"mech": 1}

    monkeypatch.setattr(board_graph, "bound_grid", _grid)
    monkeypatch.setattr(movement, "is_gravity_rift", lambda _g, pos: pos == "000")
    monkeypatch.setattr(movement, "roll_rift_exit", roll)
    side = TransactionSide(planets=(f"mr>{dest}",))
    done = transaction.resolve_transaction(state, _grid(), "p2", side, TransactionSide())
    assert rolled == [{"mech": 1, "pds": 1, "space_dock": 1}]
    assert done.systems["101"].planet_units[dest]["p1"] == {"pds": 1, "space_dock": 1}


# ================================================================================== Auto-Factories


@ruling("breakthroughs:hacanbt#1")
def test_auto_factories_tylko_od_trzech_niemysliwcow(registry: StaticDataRegistry) -> None:
    state = _state()
    state.production_placed = {"space": {"cruiser": 2}}
    assert not hacan._many_ships(state, "p1", {"player": "p1", "units": {"cruiser": 2}})
    state.production_placed = {"space": {"cruiser": 3}}
    assert not hacan._many_ships(state, "p2", {"player": "p1", "units": {"cruiser": 3}})
    state.production_placed = {"space": {"carrier": 3}}
    assert hacan._many_ships(state, "p1", {"player": "p1", "units": {"carrier": 3}})


@ruling("breakthroughs:hacanbt#1")
def test_auto_factories_suma_z_calej_akcji_raz_na_akcje(registry: StaticDataRegistry) -> None:
    """Decyzja użytkownika 2026-11-17: statki z kilku zamówień w tej samej akcji sumują się;
    żeton przychodzi raz - przy zamówieniu, które przekracza próg 3."""
    state = _state()
    # 1. zamówienie: 2 krążowniki (+ myśliwce się nie liczą) - jeszcze nie.
    state.production_placed = {"space": {"cruiser": 2, "fighter": 2}}
    first = {"player": "p1", "units": {"cruiser": 2, "fighter": 2}}
    assert not hacan._many_ships(state, "p1", first)
    # 2. zamówienie: 1 niszczyciel - razem 3 => przełom działa.
    state.production_placed = {"space": {"cruiser": 2, "fighter": 2, "destroyer": 1}}
    assert hacan._many_ships(state, "p1", {"player": "p1", "units": {"destroyer": 1}})
    # 3. zamówienie w tej samej akcji: próg już przekroczony - drugi raz nie.
    state.production_placed = {"space": {"cruiser": 2, "fighter": 2, "destroyer": 3}}
    assert not hacan._many_ships(state, "p1", {"player": "p1", "units": {"destroyer": 2}})


def test_window_use_cudzego_commandera_nie_dla_zablokowanego(
    registry: StaticDataRegistry,
) -> None:
    """Alliance daje okno commandera tylko, gdy jest odblokowany u właściciela."""
    state = _state()
    state.players["p1"].leader_states = {"hacancommander": "locked"}
    state.players["p2"].promissory_notes_in_play = ["red_an"]
    assert "hacancommander" not in faction_components.borrowed_commanders(state, "p2")
    state.players["p1"].leader_states = {"hacancommander": "unlocked"}
    assert "hacancommander" in faction_components.borrowed_commanders(state, "p2")
