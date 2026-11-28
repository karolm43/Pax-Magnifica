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


def gain_trade_goods(
    state: GameState, player_id: str, amount: int, *, cause: str = "", from_supply: bool = True
) -> None:
    """Gracz zdobywa ``amount`` trade goods (R_trade_goods).

    ``cause`` trafia do zdarzenia ``TRADE_GOODS_GAINED``: ``"transaction"`` (TG z transakcji -
    Pillage reaguje raz na samą transakcję), ``"convert"`` (zamiana commodities - to nie jest
    „zdobycie” dla Pillage, F_mentak), ``"pillage"`` (RULES.md 62.8).
    ``from_supply=False``: the trade goods come from another player, a strategy card or a leader
    card - not from the supply (Artuno the Betrayer reacts only to the supply, RULES.md 62.21).
    """
    if amount < 0:
        raise ValueError("The amount of trade goods to gain cannot be negative.")
    _player(state, player_id).trade_goods += amount
    if amount > 0:
        triggers.fire(
            state, GameEvent.TRADE_GOODS_GAINED, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "amount": amount, "cause": cause,
                 "from_supply": from_supply and cause != "convert"},
        )


def stash_on_leader(state: GameState, player_id: str, leader_id: str, amount: int) -> None:
    """Moves ``amount`` of the player's trade goods onto their leader card (Artuno the Betrayer:
    "place an equal number of trade goods on this card", RULES.md 62.21). Not a spend."""
    if amount < 0:
        raise ValueError("The amount of trade goods to place cannot be negative.")
    player = _player(state, player_id)
    if amount > player.trade_goods:
        raise ValueError(f"Not enough trade goods: {amount} > {player.trade_goods}.")
    player.trade_goods -= amount
    player.leader_trade_goods = {
        **player.leader_trade_goods,
        leader_id: player.leader_trade_goods.get(leader_id, 0) + amount,
    }


def release_from_leader(state: GameState, player_id: str, leader_id: str) -> int:
    """The player gains every trade good lying on their leader card (not from the supply -
    F_nomad artuno 3). Returns the amount."""
    player = _player(state, player_id)
    amount = player.leader_trade_goods.get(leader_id, 0)
    if amount <= 0:
        return 0
    player.leader_trade_goods = {
        k: v for k, v in player.leader_trade_goods.items() if k != leader_id
    }
    gain_trade_goods(state, player_id, amount, cause="leader_card", from_supply=False)
    return amount


def spend_trade_goods(
    state: GameState, player_id: str, amount: int, *, taken: bool = False
) -> None:
    """Gracz traci ``amount`` trade goods (wydaje je); za mało → ``ValueError``.

    ``taken=True``: another player's effect takes them (Pillage) - not the player spending, so a
    pending Pillage decision does not block it (F_mentak pillage: one Pillage per trade good
    gained one at a time)."""
    if amount < 0:
        raise ValueError("The amount of trade goods to spend cannot be negative.")
    player = _player(state, player_id)
    if amount > 0 and not taken and any(
        o.event == GameEvent.TRADE_GOODS_GAINED.value and o.label == "Pillage"
        and o.ctx.get("player") == player_id
        for o in state.pending_offers
    ):  # F_mentak pillage 11: no spending between the Pillage conditions and its resolution
        raise ValueError("Trade goods cannot be spent while a Pillage decision is pending.")
    if amount > player.trade_goods:
        raise ValueError(f"Not enough trade goods: {amount} > {player.trade_goods}.")
    player.trade_goods -= amount


def refund_trade_goods(state: GameState, player_id: str, amount: int) -> None:
    """Zwrot WYDANYCH trade goods (cofnięcie części zapłaty, np. Doctor Sucaban po zapłacie).

    To nie jest „zdobycie" TG (R_trade_goods) - bez zdarzenia ``TRADE_GOODS_GAINED``.
    """
    if amount < 0:
        raise ValueError("The amount of trade goods to refund cannot be negative.")
    _player(state, player_id).trade_goods += amount


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


def commodity_value(state: GameState, player_id: str) -> int:
    """Commodity value gracza = wartość z arkusza frakcji + modyfikatory (Dynamis Core: +2).

    JEDYNE miejsce odczytu commodity value w regułach (RULES.md 43.1a); modyfikatory to hooki
    MODIFY punktu ``economy.commodity_value``.
    """
    base = _player(state, player_id).commodity_value
    return max(0, rules_hooks.modify(rules_hooks.POINT_COMMODITY_VALUE, state, player_id, base))


def cap_commodities(state: GameState, player_id: str) -> None:
    """Zwraca do puli commodities ponad commodity value (po utracie modyfikatora; mutuje)."""
    player = _player(state, player_id)
    player.commodities = min(player.commodities, commodity_value(state, player_id))


def commodity_gap(state: GameState, player_id: str) -> int:
    """Ile commodities brakuje graczowi do commodity value (nie można mieć więcej)."""
    player = _player(state, player_id)
    return max(0, commodity_value(state, player_id) - player.commodities)


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


def replenish_commodities(state: GameState, player_id: str, *, open_window: bool = True) -> None:
    """Uzupełnia commodities gracza do wartości z jego arkusza frakcji (nie więcej).

    ``open_window=False``: oferty „after replenishes” (The Stillness of Stars) nie otwierają
    własnego okna - czekają w oknie secondary karty strategii (primary Trade, RULES.md 62.9).
    """
    player = _player(state, player_id)
    player.commodities = max(player.commodities, commodity_value(state, player_id))
    if player_id not in state.last_replenished:
        state.last_replenished = [*state.last_replenished, player_id]
    triggers.fire(
        state, GameEvent.COMMODITIES_REPLENISHED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id}, open_window=open_window,
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
    gain_trade_goods(state, player_id, amount, cause="convert")


def give_to_player(
    state: GameState,
    giver_id: str,
    receiver_id: str,
    *,
    trade_goods: int = 0,
    commodities: int = 0,
    cause: str = "",
    taken: bool = False,
) -> None:
    """Przekazuje trade goods i commodities innemu graczowi (transakcja, R_transactions).

    R_commodities: commodity oddana innemu graczowi staje się u odbiorcy trade good.
    ``taken=True``: the receiver takes them (Pillage - see ``spend_trade_goods``).
    """
    spend_trade_goods(state, giver_id, trade_goods, taken=taken)
    spend_commodities(state, giver_id, commodities)
    gain_trade_goods(
        state, receiver_id, trade_goods + commodities, cause=cause, from_supply=False
    )
    if commodities > 0:
        # "When you give a number of commodities to ..." (Dark Pact, RULES.md 62.20): the ONE
        # place every commodity hand-over goes through (transactions, Trade Agreement).
        triggers.fire(
            state, GameEvent.COMMODITIES_GIVEN, Moment.AFTER, subject=giver_id,
            ctx={"player": giver_id, "to": receiver_id, "commodities": commodities,
                 "cause": cause},
        )
