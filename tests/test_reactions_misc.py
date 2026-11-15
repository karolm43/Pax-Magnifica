"""Testy kart reakcji z grupy „misc” (RULES.md 53.5.e): strategia, tury, transakcje, odrzucenia."""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    action_budget,
    action_cards,
    component_action,
    reaction_cards,
    transaction,
    turn_flow,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActionDiscardTrace,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TransactionTable,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide

_ACTION_CARD = "economic_initiative"  # karta z oknem ACTION bez wyborów gracza


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.build_edges()
    return grid


def _state(
    hands: dict[str, list[str]] | None = None, *, phase: Phase = Phase.ACTION
) -> GameState:
    """Trzech sąsiadów w jednym systemie; p1 aktywny, karty strategii 1/2/3 (kolejność tur)."""
    players = {
        pid: PlayerState(player_id=pid, color=color, strategy_cards=[index])
        for index, (pid, color) in enumerate((("p1", "red"), ("p2", "blue"), ("p3", "green")), 1)
    }
    for pid, hand in (hands or {}).items():
        players[pid].private.action_cards = list(hand)
    return GameState(
        phase=phase,
        active_player_id="p1",
        speaker_id="p1",
        seating_order=["p1", "p2", "p3"],
        players=players,
        systems={
            "000": SystemState(
                position="000",
                system_id="18",
                space_units={pid: {"cruiser": 1} for pid in ("p1", "p2", "p3")},
            )
        },
    )


def _playable(
    state: GameState, registry: StaticDataRegistry, player: str, card: str
) -> dict[str, Any]:
    rows = action_cards.playability(state, registry, player)
    found = next((row for row in rows if row["card_id"] == card), None)
    if found is not None:
        return found
    # Gracz nie trzyma karty: sprawdzamy samo okno/relację (czy KARTA byłaby dla niego zagrywalna).
    ok, reason, _window = reaction_cards.available(state, registry, player, card)
    return {"card_id": card, "playable": ok, "reason": reason}


def _play(
    state: GameState,
    registry: StaticDataRegistry,
    player: str,
    card: str,
    params: dict[str, Any] | None = None,
) -> GameState:
    new, implemented = action_cards.play_action_card(state, registry, player, card, params)
    assert implemented
    return new


def _after_p1_turn(state: GameState) -> GameState:
    """p1 wykonuje akcję komponentu i kończy turę (silnik ustawia pauzę po końcu tury)."""
    state = component_action.play_component_action(state, "p1")
    return turn_flow.end_turn(state, "p1")


# ------------------------------------------------------------------------ pauza po końcu tury


def test_pauza_po_koncu_tury_ustawiana_i_zerowana(registry: StaticDataRegistry) -> None:
    state = _after_p1_turn(_state())
    window = state.turn_end_window
    assert window is not None
    assert (window.ended_player, window.ended_passed, window.next_player) == ("p1", False, "p2")
    assert state.active_player_id == "p2"
    # Pierwsza akcja następnego gracza zamyka pauzę.
    after = component_action.play_component_action(state, "p2")
    assert after.turn_end_window is None
    # Pas też.
    passed = state.clone()
    passed.players["p2"].exhausted_strategy_cards = [2]
    assert turn_flow.pass_turn(passed, "p2").turn_end_window is None
    # Nowa faza zeruje.
    assert turn_flow.next_phase(state).turn_end_window is None


# ---------------------------------------------------------------------------- Crisis


def test_crisis_pomija_ture_nastepnego_gracza(registry: StaticDataRegistry) -> None:
    state = _after_p1_turn(_state({"p3": ["crisis"]}))
    assert _playable(state, registry, "p3", "crisis")["playable"]
    new = _play(state, registry, "p3", "crisis")
    assert new.active_player_id == "p3"  # tura p2 pominięta
    assert new.turn_end_window is not None and new.turn_end_window.next_player == "p3"
    assert new.decks.action_card_discard[-1] == "crisis"
    # Po turze p3 kolejka idzie normalnie dalej (p3 -> p1).
    done = turn_flow.end_turn(component_action.play_component_action(new, "p3"), "p3")
    assert done.active_player_id == "p1"


def test_crisis_wymaga_dwoch_niespasowanych_i_nastepnego(registry: StaticDataRegistry) -> None:
    state = _after_p1_turn(_state({"p3": ["crisis"]}))
    state.players["p2"].passed = True
    state.players["p1"].passed = True  # niespasowany tylko p3
    assert not _playable(state, registry, "p3", "crisis")["playable"]


def test_crisis_zamkniete_po_akcji_nastepnego(registry: StaticDataRegistry) -> None:
    state = _after_p1_turn(_state({"p3": ["crisis"]}))
    state = component_action.play_component_action(state, "p2")
    row = _playable(state, registry, "p3", "crisis")
    assert not row["playable"] and "no open window" in str(row["reason"]).lower()


def test_crisis_bez_pauzy_blad(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="no open window"):
        action_cards.play_action_card(_state({"p3": ["crisis"]}), registry, "p3", "crisis")


# ---------------------------------------------------------------- Puppets on a String


def test_puppets_dodatkowa_akcja_spasowanego(registry: StaticDataRegistry) -> None:
    state = _state({"p3": ["puppetsonastring"]})
    state.players["p3"].passed = True
    state.players["p3"].exhausted_strategy_cards = [3]
    state = _after_p1_turn(state)
    assert _playable(state, registry, "p3", "puppetsonastring")["playable"]
    new = _play(state, registry, "p3", "puppetsonastring")
    assert new.active_player_id == "p3"
    assert new.bonus_turn is not None and new.bonus_turn.resume_player == "p2"
    # p3 wykonuje JEDNĄ akcję (prawdziwa funkcja silnika) i kończy - tura wraca do p2.
    acted = component_action.play_component_action(new, "p3")
    with pytest.raises(ValueError, match="already took an action"):
        component_action.play_component_action(acted, "p3")
    back = turn_flow.end_turn(acted, "p3")
    assert back.active_player_id == "p2"
    assert back.players["p3"].passed
    assert back.bonus_turn is None
    assert back.turn_end_window is not None and back.turn_end_window.next_player == "p2"


def test_puppets_tylko_dla_spasowanego(registry: StaticDataRegistry) -> None:
    state = _after_p1_turn(_state({"p3": ["puppetsonastring"]}))
    row = _playable(state, registry, "p3", "puppetsonastring")
    assert not row["playable"]


# ----------------------------------------------------------------------- Extreme Duress


def _duress_state(target_hand: list[str]) -> GameState:
    state = _state({"p3": ["extremeduress"], "p2": target_hand})
    state.players["p2"].trade_goods = 4
    state.players["p2"].private.secret_objectives = ["s1", "s2"]
    state.players["p3"].trade_goods = 1
    return _after_p1_turn(state)


def test_duress_niestrategiczna_akcja_oddaje_wszystko(registry: StaticDataRegistry) -> None:
    state = _duress_state(["fs1", "fs2"])
    assert _playable(state, registry, "p3", "extremeduress")["playable"]
    assert not _playable(state, registry, "p2", "extremeduress")["playable"]  # „another player”
    state = _play(state, registry, "p3", "extremeduress")
    state = component_action.play_component_action(state, "p2")  # prawdziwa akcja niestrategiczna
    p2, p3 = state.players["p2"], state.players["p3"]
    assert p2.private.action_cards == []
    assert {"fs1", "fs2"} <= set(state.decks.action_card_discard)
    assert (p2.trade_goods, p3.trade_goods) == (0, 5)
    assert p3.private.revealed_secrets == {"p2": ["s1", "s2"]}
    assert not state.active_effects  # efekt rozstrzygnięty


def test_duress_akcja_strategiczna_bez_kary(registry: StaticDataRegistry) -> None:
    state = _play(_duress_state(["fs1"]), registry, "p3", "extremeduress")
    action_budget.register_action(state, "p2", strategic=True)
    assert state.players["p2"].private.action_cards == ["fs1"]
    assert state.players["p2"].trade_goods == 4
    assert not state.active_effects


def test_duress_grana_karta_akcji_zostaje_do_zagrania(registry: StaticDataRegistry) -> None:
    state = _duress_state([_ACTION_CARD, "fs1"])
    state = _play(state, registry, "p3", "extremeduress")
    state, _ = action_cards.play_action_card(state, registry, "p2", _ACTION_CARD)
    assert state.players["p2"].private.action_cards == []
    assert state.players["p2"].trade_goods == 0


def test_duress_wymaga_gotowej_karty_strategii(registry: StaticDataRegistry) -> None:
    state = _state({"p3": ["extremeduress"]})
    state.players["p2"].exhausted_strategy_cards = [2]
    state = _after_p1_turn(state)
    assert not _playable(state, registry, "p3", "extremeduress")["playable"]


# ----------------------------------------------------------------------------- Master Plan


def test_master_plan_dodaje_akcje(registry: StaticDataRegistry) -> None:
    state = _state({"p1": ["master_plan"]})
    assert not _playable(state, registry, "p1", "master_plan")["playable"]  # jeszcze bez akcji
    state = component_action.play_component_action(state, "p1")
    with pytest.raises(ValueError, match="already took an action"):
        component_action.play_component_action(state, "p1")
    assert _playable(state, registry, "p1", "master_plan")["playable"]
    state = _play(state, registry, "p1", "master_plan")
    assert action_budget.actions_left(state, "p1") == 1
    state = component_action.play_component_action(state, "p1")
    assert action_budget.actions_left(state, "p1") == 0
    # Efekt wygasa z końcem tury.
    state = turn_flow.end_turn(state, "p1")
    assert not state.active_effects


def test_master_plan_zamkniete_w_trakcie_akcji_taktycznej(registry: StaticDataRegistry) -> None:
    state = component_action.play_component_action(_state({"p1": ["master_plan"]}), "p1")
    state.active_system = "000"
    assert not _playable(state, registry, "p1", "master_plan")["playable"]


# ------------------------------------------------------------------------- Strategy start


def _strategy_state(hands: dict[str, list[str]]) -> GameState:
    state = _state(hands, phase=Phase.STRATEGY)
    for player in state.players.values():
        player.strategy_cards = []
    return state


def test_investments_rozklada_5_tg_na_3_kartach(registry: StaticDataRegistry) -> None:
    state = _strategy_state({"p2": ["investments"]})
    assert _playable(state, registry, "p2", "investments")["playable"]
    new = _play(state, registry, "p2", "investments", {"tg_1": 2, "tg_4": 2, "tg_7": 1})
    assert (new.strategy_card_tg[1], new.strategy_card_tg[4], new.strategy_card_tg[7]) == (2, 2, 1)
    assert new.players["p2"].trade_goods == 0  # TG z zasobów ogólnych, nie z puli gracza


def test_investments_walidacja(registry: StaticDataRegistry) -> None:
    state = _strategy_state({"p2": ["investments"]})
    for params in (
        {"tg_1": 5},  # za mało kart
        {"tg_1": 3, "tg_2": 1, "tg_3": 0},  # suma 4
        {"tg_1": 2, "tg_2": 2, "tg_3": 2},  # suma 6
        {"tg_1": 2, "tg_2": -1, "tg_3": 4},  # ujemna
    ):
        with pytest.raises(ValueError):
            action_cards.play_action_card(state, registry, "p2", "investments", params)
    assert not state.strategy_card_tg


def test_investments_tg_trafiaja_do_wybierajacego(registry: StaticDataRegistry) -> None:
    from src.core import strategy_phase

    state = _play(
        _strategy_state({"p2": ["investments"]}), registry, "p2", "investments",
        {"tg_1": 2, "tg_2": 2, "tg_3": 1},
    )
    state = strategy_phase.pick_strategy_card(state, registry, "p1", 1)
    assert state.players["p1"].trade_goods == 2


def test_okno_poczatku_fazy_strategii_zamyka_sie_po_pierwszym_wyborze(
    registry: StaticDataRegistry,
) -> None:
    from src.core import strategy_phase

    state = _strategy_state({"p2": ["summit"]})
    assert any(w.event is GameEvent.PHASE and w.moment is Moment.START
               for w in reaction_cards.open_windows(state))
    picked = strategy_phase.pick_strategy_card(state, registry, "p1", 5)
    assert not _playable(picked, registry, "p2", "summit")["playable"]
    assert not _playable(_state({"p2": ["summit"]}), registry, "p2", "summit")["playable"]


def test_summit_dwa_zetony_do_wybranych_pul(registry: StaticDataRegistry) -> None:
    state = _strategy_state({"p2": ["summit"]})
    state.players["p2"].cc_reinf = 5
    before = state.players["p2"]
    base = (before.tactical_cc, before.fleet_cc, before.strategic_cc)
    new = _play(state, registry, "p2", "summit", {"pools": ["fleet", "fleet"]})
    p2 = new.players["p2"]
    assert (p2.tactical_cc, p2.fleet_cc, p2.strategic_cc) == (base[0], base[1] + 2, base[2])
    assert p2.cc_reinf == 3
    with pytest.raises(ValueError):
        action_cards.play_action_card(state, registry, "p2", "summit", {"pools": ["fleet"]})
    with pytest.raises(ValueError, match="Unknown"):
        action_cards.play_action_card(state, registry, "p2", "summit", {"pools": ["x", "fleet"]})


def test_summit_ogranicony_rezerwa(registry: StaticDataRegistry) -> None:
    state = _strategy_state({"p2": ["summit"]})
    state.players["p2"].cc_reinf = 1
    new = _play(state, registry, "p2", "summit", {"pools": ["tactical"]})
    assert new.players["p2"].cc_reinf == 0
    state.players["p2"].cc_reinf = 0
    assert not _playable(state, registry, "p2", "summit")["playable"]


# ------------------------------------------------------------------ Black Market Dealings


def _market_state(hands: dict[str, list[str]]) -> GameState:
    state = _state(hands)
    state.players["p1"].relics = ["r1"]
    state.players["p1"].private.secret_objectives = ["s1"]
    state.players["p1"].private.action_cards = [*state.players["p1"].private.action_cards, "fs1"]
    state.players["p2"].relics = ["r2"]
    # Negocjacja = otwarty stół transakcji p1-p2 (RULES.md 47.1b, 54.9).
    state.transaction_tables = [TransactionTable(opener="p1", partner="p2")]
    return state


def test_black_market_bez_karty_nie_wymienia_dodatkow() -> None:
    with pytest.raises(ValueError, match="Black Market"):
        transaction.resolve_transaction(
            _market_state({}), _grid(), "p2", TransactionSide(relics=("r1",)), TransactionSide()
        )


def test_black_market_pozwala_na_relikty_karty_i_tajne_cele(registry: StaticDataRegistry) -> None:
    state = _market_state({"p1": ["blackmarketdealing"]})
    assert _playable(state, registry, "p1", "blackmarketdealing")["playable"]
    assert _playable(_market_state({"p2": ["blackmarketdealing"]}), registry, "p2",
                     "blackmarketdealing")["playable"]  # partner z karty też negocjuje
    state = _play(state, registry, "p1", "blackmarketdealing")
    new = transaction.resolve_transaction(
        state, _grid(), "p2",
        TransactionSide(relics=("r1",), action_cards=("fs1",), secret_objectives=("s1",)),
        TransactionSide(relics=("r2",)),
    )
    p1, p2 = new.players["p1"], new.players["p2"]
    assert p1.relics == ["r2"] and sorted(p2.relics) == ["r1"]
    assert "fs1" in p2.private.action_cards and "fs1" not in p1.private.action_cards
    assert p2.private.secret_objectives == ["s1"] and p1.private.secret_objectives == []
    assert not new.active_effects  # karta dotyczyła tej jednej transakcji


def test_black_market_nie_wymienia_cudzych_rzeczy(registry: StaticDataRegistry) -> None:
    state = _play(_market_state({"p1": ["blackmarketdealing"]}), registry, "p1",
                  "blackmarketdealing")
    with pytest.raises(ValueError, match="does not have the relic"):
        transaction.resolve_transaction(
            state, _grid(), "p2", TransactionSide(relics=("r9",)), TransactionSide()
        )


def test_black_market_tylko_w_trakcie_negocjacji(registry: StaticDataRegistry) -> None:
    """„When you are negotiating a transaction”: bez otwartego stołu karty nie da się zagrać
    (zgłoszenie 2026-11-15 - wcześniej okno trwało całą turę aktywnego gracza)."""
    state = _market_state({"p1": ["blackmarketdealing"], "p3": ["blackmarketdealing"]})
    assert not _playable(state, registry, "p3", "blackmarketdealing")["playable"]  # nie negocjuje
    state.transaction_tables = []
    assert not _playable(state, registry, "p1", "blackmarketdealing")["playable"]


# ---------------------------------------------------------------------------- Lie in Wait


def _resolved_transaction(hands: dict[str, list[str]]) -> GameState:
    state = _state(hands)
    state.players["p1"].trade_goods = 1
    return transaction.resolve_transaction(
        state, _grid(), "p2", TransactionSide(trade_goods=1), TransactionSide()
    )


def test_lie_in_wait_bierze_po_karcie_od_obu(registry: StaticDataRegistry) -> None:
    state = _resolved_transaction({"p3": ["lieinwait"], "p1": ["fs1", "fs2"], "p2": ["fs3"]})
    assert state.last_transaction == ["p1", "p2"]
    assert _playable(state, registry, "p3", "lieinwait")["playable"]
    assert not _playable(state, registry, "p1", "lieinwait")["playable"]  # strona transakcji
    _implemented, inputs = action_cards.card_inputs(state, registry, "p3", "lieinwait")
    assert [item["key"] for item in inputs] == ["card_p1", "card_p2"]
    assert [o["value"] for o in inputs[0]["options"]] == ["fs1", "fs2"]
    new = _play(state, registry, "p3", "lieinwait", {"card_p1": "fs2", "card_p2": "fs3"})
    assert sorted(new.players["p3"].private.action_cards) == ["fs2", "fs3"]
    assert new.players["p1"].private.action_cards == ["fs1"]
    assert new.players["p2"].private.action_cards == []


def test_lie_in_wait_pusta_reka_pomijana_i_walidacja(registry: StaticDataRegistry) -> None:
    state = _resolved_transaction({"p3": ["lieinwait"], "p1": ["fs1"]})
    new = _play(state, registry, "p3", "lieinwait", {"card_p1": "fs1"})
    assert new.players["p3"].private.action_cards == ["fs1"]
    with pytest.raises(ValueError, match="Choose 1 action card"):
        action_cards.play_action_card(state, registry, "p3", "lieinwait", {"card_p1": "fs9"})
    empty = _resolved_transaction({"p3": ["lieinwait"]})
    assert not _playable(empty, registry, "p3", "lieinwait")["playable"]


def test_lie_in_wait_wymaga_obu_sasiadow_i_zamyka_sie(registry: StaticDataRegistry) -> None:
    state = _resolved_transaction({"p3": ["lieinwait"], "p1": ["fs1"]})
    far = state.clone()
    far.systems["000"].space_units = {"p1": {"cruiser": 1}, "p2": {"cruiser": 1}}
    assert not _playable(far, registry, "p3", "lieinwait")["playable"]
    after_action = component_action.play_component_action(state, "p1")
    assert after_action.last_transaction == []
    assert not _playable(after_action, registry, "p3", "lieinwait")["playable"]


# ------------------------------------------------------------------------- Reverse Engineer


def test_reverse_engineer_bierze_karte_z_akcja_komponentu(registry: StaticDataRegistry) -> None:
    state = _state({"p1": [_ACTION_CARD], "p2": ["reverse_engineer"]})
    state, _ = action_cards.play_action_card(state, registry, "p1", _ACTION_CARD)
    assert state.last_action_discard == ActionDiscardTrace(player="p1", card=_ACTION_CARD)
    assert _playable(state, registry, "p2", "reverse_engineer")["playable"]
    assert not _playable(state, registry, "p1", "reverse_engineer")["playable"]  # „another player”
    new = _play(state, registry, "p2", "reverse_engineer")
    assert new.players["p2"].private.action_cards == [_ACTION_CARD]
    assert _ACTION_CARD not in new.decks.action_card_discard
    assert new.decks.action_card_discard == ["reverse_engineer"]


def test_reverse_engineer_ignoruje_karty_reakcji_i_zamyka_sie(
    registry: StaticDataRegistry,
) -> None:
    state = _state({"p2": ["reverse_engineer"]})
    state.decks.action_card_discard = ["fs1"]
    state.last_action_discard = ActionDiscardTrace(player="p1", card="fs1")  # karta reakcji
    assert not _playable(state, registry, "p2", "reverse_engineer")["playable"]
    state2 = _state({"p1": [_ACTION_CARD], "p2": ["reverse_engineer"]})
    state2, _ = action_cards.play_action_card(state2, registry, "p1", _ACTION_CARD)
    state2 = turn_flow.end_turn(state2, "p1")
    state2 = component_action.play_component_action(state2, "p2")
    assert not _playable(state2, registry, "p2", "reverse_engineer")["playable"]


def test_reverse_engineer_po_odrzuceniu_z_limitu_reki(registry: StaticDataRegistry) -> None:
    from src.core import card_draw

    state = _state({"p1": [_ACTION_CARD], "p2": ["reverse_engineer"]})
    card_draw.discard_action_cards(state, "p1", 1)  # odrzucenie „z innego efektu” (nie zagranie)
    assert state.last_action_discard == ActionDiscardTrace(player="p1", card=_ACTION_CARD)
    assert _playable(state, registry, "p2", "reverse_engineer")["playable"]
