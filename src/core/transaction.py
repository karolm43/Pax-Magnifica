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

Zgoda (RULES.md 47.1a): aktywny gracz SKŁADA propozycję (``propose_transaction``), a wymiana
następuje dopiero, gdy partner ją przyjmie (``respond_to_offer``). Bot odpowiada od razu
(``bot_accepts`` — ⚠️ ZAŁOŻENIE do czasu warstwy AI).

Asymetria frakcji przez hooki: transakcja bez sąsiedztwa (``POINT_TRANSACTION_ANY_PLAYER`` —
Guild Ships, Trade Convoys), karty akcji w transakcji (``POINT_TRANSACTION_ACTION_CARDS`` —
Arbiters; ``POINT_TRANSACTION_EXTRA_ITEMS`` — Black Market Dealings). Funkcje są CZYSTE.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from src.core import (
    card_draw,
    chronicle,
    control,
    economy,
    promissory_notes,
    relic_fragments,
    relics,
    rules_hooks,
    secret_objectives,
    triggers,
    unit_ops,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import ControlType, GameState, Phase, TransactionOffer
from src.core.hex_grid import HexGrid
from src.core.neighbors import neighbors_of


@dataclass(frozen=True)
class TransactionSide:
    """Jedna strona transakcji: to, co dany gracz ODDAJE partnerowi."""

    trade_goods: int = 0
    commodities: int = 0
    promissory_note: str | None = None
    relic_fragments: tuple[str, ...] = field(default_factory=tuple)
    # Karty akcji: Arbiters (Hacan) albo Black Market Dealings. Relikty i NIEZDOBYTE tajne cele —
    # tylko Black Market Dealings. Bez tych efektów pola muszą być puste (``_validate_extras``).
    relics: tuple[str, ...] = field(default_factory=tuple)
    action_cards: tuple[str, ...] = field(default_factory=tuple)
    secret_objectives: tuple[str, ...] = field(default_factory=tuple)
    # Karty planet (Pride of Kenara): wpisy ``"<planeta>><planeta docelowa>"`` - jednostki
    # oddającego przechodzą z planety na docelową (jego), kontrolę dostaje partner.
    planets: tuple[str, ...] = field(default_factory=tuple)

    def has_extras(self) -> bool:
        """Czy strona oddaje coś spoza standardowej listy (relikty / karty akcji / tajne cele)."""
        return bool(self.relics or self.action_cards or self.secret_objectives)

    def is_empty(self) -> bool:
        """Czy strona nic nie oddaje."""
        return (
            self.trade_goods == 0
            and self.commodities == 0
            and self.promissory_note is None
            and not self.relic_fragments
            and not self.planets
            and not self.has_extras()
        )

    def to_dict(self) -> dict[str, Any]:
        """Postać zapisywana w ``TransactionOffer`` (JSON-owalna)."""
        raw = asdict(self)
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in raw.items()}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> TransactionSide:
        """Odtwarza stronę zapisaną w ``TransactionOffer``."""
        note = raw.get("promissory_note")
        return cls(
            trade_goods=int(raw.get("trade_goods", 0)),
            commodities=int(raw.get("commodities", 0)),
            promissory_note=str(note) if note else None,
            relic_fragments=tuple(str(x) for x in raw.get("relic_fragments", ())),
            relics=tuple(str(x) for x in raw.get("relics", ())),
            action_cards=tuple(str(x) for x in raw.get("action_cards", ())),
            secret_objectives=tuple(str(x) for x in raw.get("secret_objectives", ())),
            planets=tuple(str(x) for x in raw.get("planets", ())),
        )


def _either_permits(state: GameState, point: str, a: str, b: str) -> bool:
    """Czy efekt którejkolwiek ze stron transakcji zezwala (``ctx.partner`` = druga strona)."""
    return any(
        rules_hooks.permits(point, state, who, {"partner": other})
        for who, other in ((a, b), (b, a))
    )


def action_cards_allowed(state: GameState, a: str, b: str) -> bool:
    """Czy ta para graczy może wymieniać karty akcji (Arbiters albo Black Market Dealings)."""
    return _either_permits(
        state, rules_hooks.POINT_TRANSACTION_ACTION_CARDS, a, b
    ) or _either_permits(state, rules_hooks.POINT_TRANSACTION_EXTRA_ITEMS, a, b)


def _reachable(state: GameState, grid: HexGrid, a: str, b: str) -> bool:
    """Sąsiedzi albo efekt pozwalający na transakcję bez sąsiedztwa (Guild Ships, Trade Convoys)."""
    return b in neighbors_of(a, state, grid) or _either_permits(
        state, rules_hooks.POINT_TRANSACTION_ANY_PLAYER, a, b
    )


def _validate_extras(
    state: GameState,
    giver_id: str,
    side: TransactionSide,
    who: str,
    *,
    allowed: bool,
    cards_allowed: bool,
) -> None:
    """Sprawdza relikty / karty akcji / tajne cele strony (Black Market Dealings, Arbiters)."""
    if side.action_cards and not (allowed or cards_allowed):
        raise ValueError(
            "Action cards can only be traded with the Hacan Arbiters ability "
            "or Black Market Dealings."
        )
    if (side.relics or side.secret_objectives) and not allowed:
        raise ValueError(
            "Relics and secret objectives can only be traded with Black Market Dealings."
        )
    giver = state.players[giver_id]
    for relic, count in Counter(side.relics).items():
        if count > Counter(giver.relics)[relic]:
            raise ValueError(f"{who} does not have the relic '{relic}'.")
    for card, count in Counter(side.action_cards).items():
        if count > Counter(giver.private.action_cards)[card]:
            raise ValueError(f"{who} does not have the action card '{card}'.")
    for objective, count in Counter(side.secret_objectives).items():
        if count > Counter(giver.private.secret_objectives)[objective]:
            raise ValueError(
                f"{who} does not hold the unscored secret objective '{objective}'."
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


def tradable_planets(state: GameState, player_id: str) -> list[str]:
    """Planety, których kartę gracz może teraz oddać (hook ``transaction.planets``)."""
    return sorted(
        rules_hooks.forbidden(rules_hooks.POINT_TRANSACTION_PLANETS, state, player_id)
    )


def _planet_position(state: GameState, planet: str) -> str | None:
    return next(
        (pos for pos, sys in state.systems.items() if planet in sys.planet_owners), None
    )


def _validate_planets(state: GameState, giver_id: str, side: TransactionSide, who: str) -> None:
    """Pride of Kenara: planeta z hooka, cel = inna planeta oddającego, nie w trakcie walki."""
    if not side.planets:
        return
    if state.active_combat is not None:
        raise ValueError("A planet cannot be traded during combat.")
    allowed = set(tradable_planets(state, giver_id))
    seen: set[str] = set()
    for entry in side.planets:
        planet, _, dest = entry.partition(">")
        if planet not in allowed:
            raise ValueError(f"{who} cannot trade the planet '{planet}'.")
        if planet in seen:
            raise ValueError(f"The planet '{planet}' is listed twice.")
        seen.add(planet)
        dest_pos = _planet_position(state, dest)
        if (
            not dest
            or dest == planet
            or dest_pos is None
            or state.systems[dest_pos].planet_owners.get(dest) != giver_id
        ):
            raise ValueError(f"Choose another planet {who.lower()} control(s) for the units.")


def _apply_planets(
    state: GameState, giver_id: str, receiver_id: str, side: TransactionSide
) -> None:
    for entry in side.planets:
        planet, _, dest = entry.partition(">")
        position = _planet_position(state, planet)
        dest_pos = _planet_position(state, dest)
        if position is None or dest_pos is None:
            continue
        src_sys, dest_sys = state.systems[position], state.systems[dest_pos]
        for base_type, count in dict(
            src_sys.planet_units.get(planet, {}).get(giver_id, {})
        ).items():
            if count > 0:
                unit_ops.transfer_units(
                    state, src_sys, planet, dest_sys, dest, giver_id, base_type, count
                )
        control.set_planet_control(state, position, planet, receiver_id)


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
    for relic in side.relics:
        relics.transfer(state, giver_id, receiver_id, relic)
    for card in side.action_cards:
        card_draw.transfer_action_card(state, giver_id, receiver_id, card)
    for objective in side.secret_objectives:
        secret_objectives.transfer(state, giver_id, receiver_id, objective)
    _apply_planets(state, giver_id, receiver_id, side)


def can_transact_with(
    state: GameState, grid: HexGrid, player_id: str, partner_id: str
) -> bool:
    """Czy ``player_id`` może TERAZ zacząć transakcję z ``partner_id`` (sąsiad, bez limitu)."""
    player = state.players.get(player_id)
    if player is None or partner_id == player_id or partner_id not in state.players:
        return False
    if partner_id in player.transacted_with:
        return False
    return _reachable(state, grid, player_id, partner_id)


def trade_partners(state: GameState, grid: HexGrid, player_id: str) -> list[str]:
    """Gracze, z którymi ``player_id`` może negocjować (sąsiedzi + efekty bez sąsiedztwa)."""
    return [
        pid for pid in state.players
        if pid != player_id and _reachable(state, grid, player_id, pid)
    ]


def validate_transaction(
    state: GameState,
    grid: HexGrid,
    partner_id: str,
    give: TransactionSide,
    receive: TransactionSide,
    player_id: str | None = None,
) -> str:
    """Sprawdza legalność transakcji aktywnego gracza z ``partner_id``; zwraca id aktywnego.

    Faza AKCJI, tura ``player_id`` (gdy podany), partner osiągalny (sąsiad albo efekt), pierwsza
    transakcja z nim w tej turze, obie strony mają to, co oddają, transakcja niepusta. Okno
    czasowe NIE blokuje (transakcja możliwa w trakcie walki).

    Raises:
        ValueError: Przy naruszeniu któregokolwiek z warunków.
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
    if not _reachable(state, grid, active_id, partner_id):
        raise ValueError("You can only make a transaction with a neighbor.")
    if give.is_empty() and receive.is_empty():
        raise ValueError("An empty transaction - add something to exchange.")
    _validate_side(state, active_id, give, "You")
    _validate_side(state, partner_id, receive, "The partner")
    _validate_planets(state, active_id, give, "You")
    _validate_planets(state, partner_id, receive, "The partner")
    # Black Market Dealings: ktokolwiek z dwóch stron ma efekt, obie mogą włączyć dodatkowe rzeczy.
    extras_ok = _either_permits(
        state, rules_hooks.POINT_TRANSACTION_EXTRA_ITEMS, active_id, partner_id
    )
    cards_ok = _either_permits(
        state, rules_hooks.POINT_TRANSACTION_ACTION_CARDS, active_id, partner_id
    )
    _validate_extras(
        state, active_id, give, "You", allowed=extras_ok, cards_allowed=cards_ok
    )
    _validate_extras(
        state, partner_id, receive, "The partner", allowed=extras_ok, cards_allowed=cards_ok
    )
    return active_id


def resolve_transaction(
    state: GameState,
    grid: HexGrid,
    partner_id: str,
    give: TransactionSide,
    receive: TransactionSide,
    player_id: str | None = None,
) -> GameState:
    """Wykonuje transakcję aktywnego gracza z ``partner_id`` (po zgodzie obu stron) — RULES.md 47.

    ``give`` = co oddaje aktywny gracz, ``receive`` = co dostaje od partnera. Walidacja:
    ``validate_transaction``. Nie pyta o zgodę — robi to ``propose_transaction`` /
    ``respond_to_offer`` (RULES.md 47.1a).

    Raises:
        ValueError: Transakcja nielegalna (``validate_transaction``).
    """
    active_id = validate_transaction(state, grid, partner_id, give, receive, player_id)
    new_state = state.clone()
    new_state.transaction_offer = None
    _apply_side(new_state, active_id, partner_id, give)
    _apply_side(new_state, partner_id, active_id, receive)
    new_state.players[active_id].transacted_with.append(partner_id)
    new_state.last_transaction = [active_id, partner_id]
    chronicle.record_deal(
        new_state,
        active_id,
        partner_id,
        give.trade_goods + give.commodities,
        receive.trade_goods + receive.commodities,
    )
    triggers.fire(
        new_state, GameEvent.TRANSACTION, Moment.AFTER, subject=active_id,
        ctx={"player": active_id, "partner": partner_id},
    )
    return new_state


# ------------------------------------------------------------------ zgoda partnera (47.1a)


def _value(side: TransactionSide) -> int:
    """Prosta wartość strony dla bota: TG/commodity = 1, notka / fragment / karta / relikt = 2."""
    return (
        side.trade_goods
        + side.commodities
        + 2 * (side.promissory_note is not None)
        + 2 * (len(side.relic_fragments) + len(side.action_cards) + len(side.relics))
        + 2 * len(side.secret_objectives)
    )


def bot_accepts(give: TransactionSide, receive: TransactionSide) -> bool:
    """⚠️ ZAŁOŻENIE (RULES.md 47.1a): bot przyjmuje, gdy dostaje co najmniej tyle, ile oddaje.

    ``give`` = co bot DOSTAJE (strona proponującego), ``receive`` = co bot ODDAJE. Placeholder do
    czasu warstwy AI — deterministyczny, bez losowania.
    """
    return _value(give) >= _value(receive)


def pending_offer(state: GameState) -> TransactionOffer | None:
    """Propozycja transakcji czekająca na odpowiedź (None, gdy brak)."""
    return state.transaction_offer


def offer_sides(offer: TransactionOffer) -> tuple[TransactionSide, TransactionSide]:
    """``(give, receive)`` propozycji z punktu widzenia proponującego."""
    return TransactionSide.from_dict(offer.give), TransactionSide.from_dict(offer.receive)


def propose_transaction(
    state: GameState,
    grid: HexGrid,
    partner_id: str,
    give: TransactionSide,
    receive: TransactionSide,
    player_id: str | None = None,
) -> GameState:
    """Aktywny gracz proponuje transakcję; wymiana czeka na zgodę partnera (RULES.md 47.1a).

    Ta sama walidacja co przy wymianie. Naraz czeka najwyżej jedna propozycja. Partner-bot
    odpowiada od razu (``bot_accepts``) — wynik: wymiana albo odrzucenie (ślad w ``chronicle``
    przez etykietę commitu routera).

    Raises:
        ValueError: Transakcja nielegalna albo inna propozycja już czeka.
    """
    if state.transaction_offer is not None:
        raise ValueError(
            "Another transaction offer is waiting for an answer - wait or cancel it first."
        )
    active_id = validate_transaction(state, grid, partner_id, give, receive, player_id)
    new_state = state.clone()
    new_state.transaction_offer = TransactionOffer(
        proposer=active_id, partner=partner_id, give=give.to_dict(), receive=receive.to_dict()
    )
    partner = new_state.players[partner_id]
    if partner.control_type is ControlType.BOT:
        return respond_to_offer(new_state, grid, partner_id, accept=bot_accepts(give, receive))
    return new_state


def respond_to_offer(
    state: GameState, grid: HexGrid, responder_id: str, *, accept: bool
) -> GameState:
    """Partner przyjmuje (wymiana — ponowna walidacja) albo odrzuca propozycję.

    Raises:
        ValueError: Brak propozycji, odpowiada nie partner albo transakcja przestała być legalna.
    """
    offer = state.transaction_offer
    if offer is None:
        raise ValueError("There is no transaction offer to answer.")
    if responder_id != offer.partner:
        raise ValueError("Only the player the offer was made to can answer it.")
    if not accept:
        new_state = state.clone()
        new_state.transaction_offer = None
        return new_state
    give, receive = offer_sides(offer)
    return resolve_transaction(state, grid, offer.partner, give, receive, offer.proposer)


def cancel_offer(state: GameState, player_id: str) -> GameState:
    """Proponujący wycofuje swoją propozycję przed odpowiedzią partnera.

    Raises:
        ValueError: Brak propozycji albo wycofuje ktoś inny niż proponujący.
    """
    offer = state.transaction_offer
    if offer is None:
        raise ValueError("There is no transaction offer to cancel.")
    if player_id != offer.proposer:
        raise ValueError("Only the player who made the offer can withdraw it.")
    new_state = state.clone()
    new_state.transaction_offer = None
    return new_state
