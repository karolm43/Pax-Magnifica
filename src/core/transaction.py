"""Transakcje między graczami (Transactions) — RULES.md 47 (R_transactions).

Reguła TI4 (źródło: tirules2.com → ``docs/rules_tirules/R_transactions.md``,
``R_commodities.md``, ``R_promissory_notes.md``):

* W swojej turze aktywny gracz może rozstrzygnąć DO JEDNEJ transakcji z KAŻDYM ze swoich
  sąsiadów — w dowolnym momencie tury, także w trakcie walki.
* Gracz oddaje dowolną liczbę trade goods i commodities oraz maks. JEDNĄ promissory note
  (z ręki), a w zamian dostaje dowolną liczbę trade goods, commodities i fragmentów reliktów
  oraz maks. JEDNĄ promissory note. Transakcja NIE musi być równa — można dawać za darmo.
* Commodity przekazana innemu graczowi zamienia się u odbiorcy w trade good.
* Promissory notes leżące w strefie gracza (play area) nie podlegają wymianie; same relikty
  też nie — tylko ich FRAGMENTY.
* Warunki uzgadniają gracze; po wymianie transakcji nie da się cofnąć (tu: Undo silnika).

Zakres (świadomy, ⚠️ patrz RULES.md 47): bez wymiany kart akcji (Hacan — hook E7), bez
zwrotu pojmanych jednostek. Funkcja jest CZYSTA (``state -> state``, operuje na klonie).
Agenda (transakcja z każdym graczem bez sąsiedztwa) jest poza zakresem tego bloku.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from src.core import chronicle, economy, promissory_notes, relic_fragments
from src.core.game_state import GameState, Phase
from src.core.hex_grid import HexGrid
from src.core.neighbors import neighbors_of


@dataclass(frozen=True)
class TransactionSide:
    """Jedna strona transakcji: to, co dany gracz ODDAJE partnerowi."""

    trade_goods: int = 0
    commodities: int = 0
    promissory_note: str | None = None
    relic_fragments: tuple[str, ...] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        """Czy strona nic nie oddaje."""
        return (
            self.trade_goods == 0
            and self.commodities == 0
            and self.promissory_note is None
            and not self.relic_fragments
        )


def _validate_side(state: GameState, giver_id: str, side: TransactionSide, who: str) -> None:
    """Sprawdza, czy ``giver_id`` faktycznie posiada to, co ma oddać (``who`` = etykieta)."""
    giver = state.players[giver_id]
    if side.trade_goods < 0 or side.commodities < 0:
        raise ValueError("Amounts in a transaction cannot be negative.")
    if side.trade_goods > giver.trade_goods:
        raise ValueError(
            f"{who} cannot give {side.trade_goods} trade goods - has only {giver.trade_goods}."
        )
    if side.commodities > giver.commodities:
        raise ValueError(
            f"{who} cannot give {side.commodities} commodities - has only {giver.commodities}."
        )
    note = side.promissory_note
    if note is not None and note not in giver.private.promissory_notes:
        raise ValueError(
            f"{who} does not hold the promissory note '{note}' in hand "
            "(notes in the play area cannot be traded)."
        )
    owned = Counter(giver.relic_fragments)
    for fragment, count in Counter(side.relic_fragments).items():
        if count > owned[fragment]:
            raise ValueError(f"{who} does not have the relic fragment '{fragment}'.")


def _apply_side(state: GameState, giver_id: str, receiver_id: str, side: TransactionSide) -> None:
    """Przenosi komponenty ``side`` od ``giver_id`` do ``receiver_id`` (mutuje ``state``)."""
    # R_commodities: commodity oddana innemu graczowi staje się u odbiorcy trade good.
    economy.give_to_player(
        state, giver_id, receiver_id,
        trade_goods=side.trade_goods, commodities=side.commodities,
    )
    if side.promissory_note is not None:
        promissory_notes.transfer(state, giver_id, receiver_id, side.promissory_note)
    for fragment in side.relic_fragments:
        relic_fragments.transfer(state, giver_id, receiver_id, fragment)


def can_transact_with(
    state: GameState, grid: HexGrid, player_id: str, partner_id: str
) -> bool:
    """Czy ``player_id`` może TERAZ zacząć transakcję z ``partner_id`` (sąsiad, bez limitu)."""
    player = state.players.get(player_id)
    if player is None or partner_id == player_id or partner_id not in state.players:
        return False
    if partner_id in player.transacted_with:
        return False
    return partner_id in neighbors_of(player_id, state, grid)


def resolve_transaction(
    state: GameState,
    grid: HexGrid,
    partner_id: str,
    give: TransactionSide,
    receive: TransactionSide,
    player_id: str | None = None,
) -> GameState:
    """Rozstrzyga transakcję aktywnego gracza z sąsiadem ``partner_id`` — RULES.md 47.

    ``give`` = co oddaje aktywny gracz, ``receive`` = co dostaje od partnera. Walidacja
    (silnik-sędzia): faza AKCJI, to tura ``player_id`` (gdy podany), partner jest sąsiadem,
    pierwsza transakcja z tym partnerem w tej turze, obie strony mają to, co oddają, a sama
    transakcja nie jest pusta. Okno czasowe NIE blokuje (transakcja możliwa w trakcie walki).

    Raises:
        ValueError: Przy naruszeniu któregokolwiek z powyższych warunków.
    """
    if state.phase is not Phase.ACTION:
        raise ValueError("Transactions are resolved during the action phase.")
    active_id = state.active_player_id
    if active_id is None:
        raise ValueError("No active player in the action phase.")
    if player_id is not None and player_id != active_id:
        raise ValueError(f"It is not {player_id}'s turn (active: {active_id}).")
    if partner_id == active_id:
        raise ValueError("You cannot make a transaction with yourself.")
    if partner_id not in state.players:
        raise ValueError(f"Unknown player: {partner_id}")
    player = state.players[active_id]
    if partner_id in player.transacted_with:
        raise ValueError(
            "You already made a transaction with this player this turn "
            "(one per neighbor per turn)."
        )
    if partner_id not in neighbors_of(active_id, state, grid):
        raise ValueError("You can only make a transaction with a neighbor.")
    if give.is_empty() and receive.is_empty():
        raise ValueError("An empty transaction - add something to exchange.")
    _validate_side(state, active_id, give, "You")
    _validate_side(state, partner_id, receive, "The partner")

    new_state = state.clone()
    _apply_side(new_state, active_id, partner_id, give)
    _apply_side(new_state, partner_id, active_id, receive)
    new_state.players[active_id].transacted_with.append(partner_id)
    chronicle.record_deal(
        new_state,
        active_id,
        partner_id,
        give.trade_goods + give.commodities,
        receive.trade_goods + receive.commodities,
    )
    return new_state
