"""Testy fazy strategii (Etap E2) — czyste funkcje ``strategy_phase``.

Reguły: RULES.md 13 (wybór karty = transfer TG z karty do gracza; akumulacja +1 TG
na niewybranych kartach; oznaczenie zagranej). Dane kart z rejestru (zestaw PoK, 8 kart).
"""

from __future__ import annotations

import pytest

from src.core import strategy_phase
from src.core.game_state import GameState, PlayerState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    return GameState(
        players={
            "p1": PlayerState(player_id="p1"),
            "p2": PlayerState(player_id="p2"),
        }
    )


def test_available_initiatives_pok_set(registry: StaticDataRegistry) -> None:
    # Domyślny zestaw PoK ma 8 kart o inicjatywach 1..8.
    assert strategy_phase.available_initiatives(registry) == [1, 2, 3, 4, 5, 6, 7, 8]


def test_pick_assigns_card_and_sets_initiative(
    registry: StaticDataRegistry,
) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 1)
    assert state.players["p1"].strategy_cards == [1]
    assert 1 in strategy_phase.picked_initiatives(state)


def test_pick_transfers_trade_goods_from_card(
    registry: StaticDataRegistry,
) -> None:
    # Na karcie inicjatywy 5 leżą 2 TG — po wyborze gracz je dostaje, karta → 0.
    base = _state()
    base.strategy_card_tg = {5: 2}
    base.players["p1"].trade_goods = 1
    state = strategy_phase.pick_strategy_card(base, registry, "p1", 5)
    assert state.players["p1"].trade_goods == 3  # 1 + 2 z karty
    assert state.strategy_card_tg[5] == 0


def test_pick_rejects_already_picked(registry: StaticDataRegistry) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 3)
    with pytest.raises(ValueError, match="już wybrana"):
        strategy_phase.pick_strategy_card(state, registry, "p2", 3)


def test_pick_rejects_card_outside_set(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="nie jest w zestawie"):
        strategy_phase.pick_strategy_card(_state(), registry, "p1", 9)


def test_pick_rejects_unknown_player(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="Nieznany gracz"):
        strategy_phase.pick_strategy_card(_state(), registry, "ghost", 1)


def test_play_marks_exhausted(registry: StaticDataRegistry) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 2)
    played = strategy_phase.play_strategy_card(state, "p1", 2)
    assert 2 in played.players["p1"].exhausted_strategy_cards


def test_play_is_idempotent(registry: StaticDataRegistry) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 2)
    once = strategy_phase.play_strategy_card(state, "p1", 2)
    twice = strategy_phase.play_strategy_card(once, "p1", 2)
    assert twice.players["p1"].exhausted_strategy_cards == [2]


def test_play_rejects_card_not_owned(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="nie posiada karty"):
        strategy_phase.play_strategy_card(_state(), "p1", 4)


def test_accumulate_adds_one_tg_to_unpicked(
    registry: StaticDataRegistry,
) -> None:
    # p1 wybiera kartę 1; akumulacja dokłada +1 TG na pozostałych 7 kartach.
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 1)
    acc = strategy_phase.accumulate_unpicked_tg(state, registry)
    assert 1 not in acc.strategy_card_tg or acc.strategy_card_tg.get(1, 0) == 0
    for init in [2, 3, 4, 5, 6, 7, 8]:
        assert acc.strategy_card_tg[init] == 1
    # Powtórna akumulacja (bez wyboru) rośnie dalej.
    acc2 = strategy_phase.accumulate_unpicked_tg(acc, registry)
    assert acc2.strategy_card_tg[2] == 2


def test_reset_returns_cards_to_pool_keeps_tg(
    registry: StaticDataRegistry,
) -> None:
    state = strategy_phase.pick_strategy_card(_state(), registry, "p1", 1)
    state = strategy_phase.play_strategy_card(state, "p1", 1)
    state.strategy_card_tg = {4: 3}
    reset = strategy_phase.reset_strategy_cards(state)
    assert reset.players["p1"].strategy_cards == []
    assert reset.players["p1"].exhausted_strategy_cards == []
    # Trade goods na kartach NIE są czyszczone (akumulują się między rundami).
    assert reset.strategy_card_tg == {4: 3}


def test_pick_does_not_mutate_input(registry: StaticDataRegistry) -> None:
    base = _state()
    strategy_phase.pick_strategy_card(base, registry, "p1", 1)
    assert base.players["p1"].strategy_cards == []  # wejście nietknięte
