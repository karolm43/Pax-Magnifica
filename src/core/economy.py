"""Ekonomia gracza: trade goods i commodities — JEDYNE miejsce zmiany tych liczników.

RULES.md 43.1a (punkty centralne): każda zmiana ``PlayerState.trade_goods`` i
``PlayerState.commodities`` w ``core/`` idzie przez funkcje tego modułu (wyjątek: God-Mode
w ``core/board_edit.py``). Dzięki temu efekt kart/zdolności wpływający na ekonomię (np. „wydawaj
commodities jak trade goods", zmiana liczby zdobywanych TG) dopisujemy w JEDNYM miejscu, a nie
w każdym wydarzeniu, w którym gracz wydaje albo zdobywa trade goods.

Źródło reguł: ``docs/rules_tirules/R_trade_goods.md``, ``R_commodities.md``,
``R_transactions.md``. Wartości liczbowe (np. commodity value) pochodzą ze stanu gracza
(``commodity_value`` ustawione z danych frakcji w setupie), nie z kodu.

Wszystkie funkcje są małymi operacjami na STANIE przekazanym przez wołającego (``state`` to
KLON roboczy — tak samo jak ``payment.apply_payment``); nie klonują go same.
"""

from __future__ import annotations

from src.core import rules_hooks, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, PlayerState


def _player(state: GameState, player_id: str) -> PlayerState:
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    return player


def gain_trade_goods(state: GameState, player_id: str, amount: int) -> None:
    """Gracz zdobywa ``amount`` trade goods (R_trade_goods)."""
    if amount < 0:
        raise ValueError("The amount of trade goods to gain cannot be negative.")
    _player(state, player_id).trade_goods += amount
    if amount > 0:
        triggers.fire(
            state, GameEvent.TRADE_GOODS_GAINED, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "amount": amount},
        )


def spend_trade_goods(state: GameState, player_id: str, amount: int) -> None:
    """Gracz traci ``amount`` trade goods (wydaje je); za mało → ``ValueError``."""
    if amount < 0:
        raise ValueError("The amount of trade goods to spend cannot be negative.")
    player = _player(state, player_id)
    if amount > player.trade_goods:
        raise ValueError(f"Not enough trade goods: {amount} > {player.trade_goods}.")
    player.trade_goods -= amount


def spendable_trade_goods(state: GameState, player_id: str) -> int:
    """Ile TG-ekwiwalentów gracz może wydać: trade goods (+ commodities, gdy hook zezwala).

    Punkt zaczepienia ``payment.commodities_as_trade_goods`` (PERMIT): efekt typu „wydawaj
    commodities jak trade goods" dopisujemy jako hook, a nie w każdej płatności osobno.
    """
    player = _player(state, player_id)
    if rules_hooks.permits(rules_hooks.POINT_PAYMENT_COMMODITIES_AS_TG, state, player_id):
        return player.trade_goods + player.commodities
    return player.trade_goods


def spend_as_trade_goods(state: GameState, player_id: str, amount: int) -> None:
    """Wydaje ``amount`` TG-ekwiwalentów: najpierw trade goods, resztę commodities (hook).

    Raises:
        ValueError: Gdy ``amount`` przekracza ``spendable_trade_goods``.
    """
    if amount < 0:
        raise ValueError("The amount of trade goods to spend cannot be negative.")
    if amount > spendable_trade_goods(state, player_id):
        raise ValueError(
            f"Not enough trade goods: {amount} > {spendable_trade_goods(state, player_id)}."
        )
    from_trade_goods = min(amount, _player(state, player_id).trade_goods)
    spend_trade_goods(state, player_id, from_trade_goods)
    spend_commodities(state, player_id, amount - from_trade_goods)


def commodity_gap(state: GameState, player_id: str) -> int:
    """Ile commodities brakuje graczowi do commodity value (nie można mieć więcej)."""
    player = _player(state, player_id)
    return max(0, player.commodity_value - player.commodities)


def gain_commodities(state: GameState, player_id: str, amount: int) -> int:
    """Gracz zdobywa do ``amount`` commodities, nie przekraczając commodity value.

    Returns:
        Ile commodities faktycznie przybyło (0, gdy gracz jest już na maksimum).
    """
    if amount < 0:
        raise ValueError("The amount of commodities to gain cannot be negative.")
    gained = min(amount, commodity_gap(state, player_id))
    _player(state, player_id).commodities += gained
    return gained


def replenish_commodities(state: GameState, player_id: str) -> None:
    """Uzupełnia commodities gracza do wartości z jego arkusza frakcji (nie więcej)."""
    player = _player(state, player_id)
    player.commodities = max(player.commodities, player.commodity_value)
    triggers.fire(
        state, GameEvent.COMMODITIES_REPLENISHED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id},
    )


def spend_commodities(state: GameState, player_id: str, amount: int) -> None:
    """Gracz traci ``amount`` commodities (wydaje je); za mało → ``ValueError``."""
    if amount < 0:
        raise ValueError("The amount of commodities to spend cannot be negative.")
    player = _player(state, player_id)
    if amount > player.commodities:
        raise ValueError(f"Not enough commodities: {amount} > {player.commodities}.")
    player.commodities -= amount


def convert_commodities_to_trade_goods(state: GameState, player_id: str, amount: int) -> None:
    """Zamienia ``amount`` własnych commodities na tyle samo trade goods (R_commodities)."""
    spend_commodities(state, player_id, amount)
    gain_trade_goods(state, player_id, amount)


def give_to_player(
    state: GameState,
    giver_id: str,
    receiver_id: str,
    *,
    trade_goods: int = 0,
    commodities: int = 0,
) -> None:
    """Przekazuje trade goods i commodities innemu graczowi (transakcja, R_transactions).

    R_commodities: commodity oddana innemu graczowi staje się u odbiorcy trade good.
    """
    spend_trade_goods(state, giver_id, trade_goods)
    spend_commodities(state, giver_id, commodities)
    gain_trade_goods(state, receiver_id, trade_goods + commodities)
