"""Stół transakcji (RULES.md 47.1b) i umowy kroku 3 Trade (RULES.md 47.4).

Każda para graczy ma najwyżej jeden stół (``GameState.transaction_tables``). Każda strona kładzie
na nim WYŁĄCZNIE własne rzeczy (``TransactionSide``); rzeczy partnera widać dopiero, gdy je
położy. Obie strony dają Ready; każda zmiana zawartości zdejmuje oba Ready. Gdy obie są gotowe:

* zwykły stół — komponenty idą przez ``transaction.resolve_transaction`` (reguły 47.1), żetony
  długu przez ``debt.give_debt_tokens`` (pamięć stołu, bez sąsiedztwa i fazy);
* stół umowy Trade (posiadacz karty położył ``trade_secondary`` w kroku ``choose_free_players``) —
  gracz zostaje wskazany do darmowego secondary, dług przechodzi od razu, a komponenty i „wash”
  czekają w ``GameState.trade_deals`` na uzupełnienie commodities (umowa niewiążąca, R_trade):
  ``open_deal_table`` otwiera wtedy stół wstępnie wypełniony.

Funkcje CZYSTE (``state -> state`` na klonie), poza ``open_deal_table`` (mutuje klon wołającego).
"""

from __future__ import annotations

from src.core import debt, transaction
from src.core.game_state import ControlType, GameState, TradeDeal, TransactionTable
from src.core.hex_grid import HexGrid
from src.core.transaction import TransactionSide

# Krok primary Trade, w którym posiadacz wskazuje graczy z darmowym secondary (R_trade, krok 3).
TRADE_STEP = "choose_free_players"


def find_table(state: GameState, a: str, b: str) -> TransactionTable | None:
    """Stół pary ``a``-``b`` (kolejność bez znaczenia) albo None."""
    return next(
        (t for t in state.transaction_tables if {t.opener, t.partner} == {a, b}), None
    )


def tables_of(state: GameState, player_id: str) -> list[TransactionTable]:
    """Stoły, przy których siedzi ``player_id``."""
    return [t for t in state.transaction_tables if player_id in (t.opener, t.partner)]


def side_of(table: TransactionTable, player_id: str) -> TransactionSide:
    """To, co ``player_id`` położył na stole."""
    return TransactionSide.from_dict(table.sides.get(player_id, {}))


def other_of(table: TransactionTable, player_id: str) -> str:
    """Druga strona stołu."""
    return table.partner if table.opener == player_id else table.opener


def trade_holder(state: GameState) -> str | None:
    """Posiadacz Trade w kroku wskazywania graczy (R_trade krok 3) — wtedy działa umowa."""
    pending = state.pending_strategy
    if pending is None or pending.step != TRADE_STEP:
        return None
    return pending.owner_id


def deal_players(state: GameState) -> list[str]:
    """Gracze wskazani umową z kroku 3 Trade (zablokowani jako „free” w wyborze posiadacza)."""
    pending = state.pending_strategy
    if pending is None:
        return []
    return [str(p) for p in pending.draft.get("deal_players", [])]


def _require_pair(state: GameState, player_id: str, partner_id: str) -> None:
    for pid in (player_id, partner_id):
        if pid not in state.players:
            raise ValueError(f"Unknown player: {pid}")
    if player_id == partner_id:
        raise ValueError("You cannot sit at a table with yourself.")


def _require_table(state: GameState, player_id: str, partner_id: str) -> TransactionTable:
    _require_pair(state, player_id, partner_id)
    table = find_table(state, player_id, partner_id)
    if table is None:
        raise ValueError("There is no transaction table with this player.")
    return table


def open_table(state: GameState, player_id: str, partner_id: str) -> GameState:
    """Każda ze stron może usiąść do stołu (F_hacan: „either player may initiate”).

    Stół już istnieje => stan bez zmian (idempotentne).
    """
    _require_pair(state, player_id, partner_id)
    if find_table(state, player_id, partner_id) is not None:
        return state
    new_state = state.clone()
    new_state.transaction_tables.append(TransactionTable(opener=player_id, partner=partner_id))
    return new_state


def close_table(state: GameState, player_id: str, partner_id: str) -> GameState:
    """Strona wstaje od stołu — nic nie przechodzi."""
    table = _require_table(state, player_id, partner_id)
    new_state = state.clone()
    new_state.transaction_tables = [
        t for t in new_state.transaction_tables
        if {t.opener, t.partner} != {table.opener, table.partner}
    ]
    return new_state


def _validate_place(
    state: GameState, grid: HexGrid, player_id: str, partner_id: str, side: TransactionSide
) -> None:
    """Czy ``player_id`` może położyć ``side`` na stole z ``partner_id``."""
    if side.debt_tokens < 0:
        raise ValueError("The number of debt tokens cannot be negative.")
    holder = trade_holder(state)
    if side.trade_secondary and holder != player_id:
        raise ValueError(
            "Only the Trade holder choosing players for the free secondary can offer it."
        )
    if side.wash is not None:
        if holder != partner_id:
            raise ValueError("A wash can only be promised to the Trade holder during Trade.")
        if side.wash < 0:
            raise ValueError("The wash discount cannot be negative.")
    if not side.has_components() and side.wash is None:
        return
    if holder in (player_id, partner_id):
        # Umowa Trade: komponenty przejdą PO uzupełnieniu, więc tu tylko osiągalność (47.4);
        # posiadanie sprawdza stół otwarty po uzupełnieniu.
        if not transaction.reachable(state, grid, player_id, partner_id):
            raise ValueError(
                "With a player who is not your neighbor you can only agree on debt tokens."
            )
        return
    if side.wash is not None:
        raise ValueError("A wash can only be promised to the Trade holder during Trade.")
    if not transaction.components_allowed(state, grid, player_id, partner_id):
        raise ValueError(
            "You cannot make a transaction with this player now - only debt tokens "
            "can go on the table."
        )
    transaction.validate_side(state, player_id, partner_id, side.components(), "You")


def set_side(
    state: GameState, grid: HexGrid, player_id: str, partner_id: str, side: TransactionSide
) -> GameState:
    """Gracz kładzie na stół (zastępuje swoją stronę); zdejmuje oba Ready.

    Raises:
        ValueError: Brak stołu albo rzecz, której teraz nie wolno położyć.
    """
    _require_table(state, player_id, partner_id)
    _validate_place(state, grid, player_id, partner_id, side)
    new_state = state.clone()
    table = find_table(new_state, player_id, partner_id)
    assert table is not None
    table.sides[player_id] = side.to_dict()
    table.ready = []
    return new_state


def is_deal(state: GameState, table: TransactionTable) -> bool:
    """Stół umowy Trade: posiadacz w kroku 3 położył darmowe secondary."""
    holder = trade_holder(state)
    return (
        holder in (table.opener, table.partner)
        and holder is not None
        and side_of(table, holder).trade_secondary
    )


def set_ready(
    state: GameState, grid: HexGrid, player_id: str, partner_id: str, ready: bool
) -> GameState:
    """Gracz potwierdza (albo cofa) obecny stan stołu; dwa Ready => wymiana.

    Partner-bot ocenia stół od razu po Ready człowieka (``transaction.bot_accepts``).

    Raises:
        ValueError: Brak stołu albo wymiana nielegalna (wtedy stół zostaje, Ready zdjęte nie są).
    """
    _require_table(state, player_id, partner_id)
    new_state = state.clone()
    table = find_table(new_state, player_id, partner_id)
    assert table is not None
    if not ready:
        table.ready = [p for p in table.ready if p != player_id]
        return new_state
    if player_id not in table.ready:
        table.ready.append(player_id)
    other = other_of(table, player_id)
    if new_state.players[other].control_type is ControlType.BOT and other not in table.ready:
        if transaction.bot_accepts(side_of(table, player_id), side_of(table, other)):
            table.ready.append(other)
    if {table.opener, table.partner} <= set(table.ready):
        return _execute(new_state, grid, table)
    return new_state


def _without(state: GameState, table: TransactionTable) -> None:
    state.transaction_tables = [
        t for t in state.transaction_tables
        if {t.opener, t.partner} != {table.opener, table.partner}
    ]


def _give_debts(state: GameState, table: TransactionTable) -> GameState:
    for giver in (table.opener, table.partner):
        count = side_of(table, giver).debt_tokens
        if count > 0:
            state = debt.give_debt_tokens(state, giver, other_of(table, giver), count)
    return state


def _execute(state: GameState, grid: HexGrid, table: TransactionTable) -> GameState:
    """Wymiana po dwóch Ready (``state`` = klon; zwraca nowy stan)."""
    sides = {pid: side_of(table, pid) for pid in (table.opener, table.partner)}
    if all(s.is_empty() for s in sides.values()):
        raise ValueError("The table is empty - put something on it first.")
    if is_deal(state, table):
        return _execute_deal(state, grid, table)
    if any(s.trade_secondary or s.wash is not None for s in sides.values()):
        raise ValueError("The Trade deal can only be agreed while choosing players for Trade.")
    result = state
    if any(s.has_components() for s in sides.values()):
        # Faza agendy (RULES.md 47.5): stroną „aktywną” jest ten, kto otworzył stół.
        active = (
            table.opener
            if transaction.agenda_window(state)
            or transaction.granted_pair(state, table.opener, table.partner)
            else state.active_player_id
        )
        if active not in sides:
            raise ValueError("Transactions are resolved on the active player's turn.")
        other = other_of(table, active)
        result = transaction.resolve_transaction(
            state, grid, other, sides[active], sides[other], active
        )
    result = _give_debts(result, table)
    if result is state:
        result = state.clone()
    _without(result, table)
    return result


def _execute_deal(state: GameState, grid: HexGrid, table: TransactionTable) -> GameState:
    """Umowa Trade: wskazanie + dług teraz; komponenty i wash czekają na uzupełnienie (47.4)."""
    holder = trade_holder(state)
    assert holder is not None
    player = other_of(table, holder)
    holder_side, player_side = side_of(table, holder), side_of(table, player)
    deferred = (
        holder_side.has_components()
        or player_side.has_components()
        or player_side.wash is not None
    )
    if deferred and not transaction.reachable(state, grid, holder, player):
        raise ValueError(
            "With a player who is not your neighbor you can only agree on debt tokens."
        )
    result = _give_debts(state, table)
    if result is state:
        result = state.clone()
    pending = result.pending_strategy
    assert pending is not None
    chosen = [str(p) for p in pending.draft.get("deal_players", [])]
    if player not in chosen:
        pending.draft["deal_players"] = [*chosen, player]
    if deferred:
        result.trade_deals[player] = TradeDeal(
            holder=holder,
            holder_side=holder_side.components().to_dict(),
            player_side=player_side.components().to_dict(),
            wash=player_side.wash,
        )
    _without(result, table)
    return result


def open_deal_table(state: GameState, player_id: str) -> None:
    """Po uzupełnieniu commodities wskazanego: stół wstępnie wypełniony umową (MUTUJE ``state``).

    Wash −N: wskazany kładzie WSZYSTKIE swoje commodities, posiadacz tyle TG minus N (najwyżej
    tyle, ile ma). Obaj muszą dać Ready — umowa jest niewiążąca (R_trade).
    """
    deal = state.trade_deals.pop(player_id, None)
    if deal is None or deal.holder not in state.players or player_id not in state.players:
        return
    holder_side = TransactionSide.from_dict(deal.holder_side)
    player_side = TransactionSide.from_dict(deal.player_side)
    if deal.wash is not None:
        commodities = state.players[player_id].commodities
        player_side = TransactionSide.from_dict(
            {**player_side.to_dict(), "commodities": commodities}
        )
        holder_side = TransactionSide.from_dict(
            {
                **holder_side.to_dict(),
                "trade_goods": holder_side.trade_goods + max(0, commodities - deal.wash),
            }
        )
    holder_tg = state.players[deal.holder].trade_goods
    if holder_side.trade_goods > holder_tg:
        holder_side = TransactionSide.from_dict(
            {**holder_side.to_dict(), "trade_goods": holder_tg}
        )
    state.transaction_tables = [
        t for t in state.transaction_tables if {t.opener, t.partner} != {deal.holder, player_id}
    ]
    state.transaction_tables.append(
        TransactionTable(
            opener=deal.holder,
            partner=player_id,
            sides={deal.holder: holder_side.to_dict(), player_id: player_side.to_dict()},
            prefilled=True,
        )
    )
