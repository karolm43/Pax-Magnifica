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

Zgoda (RULES.md 47.1b): strony negocjują przy STOLE (``core.transaction_table``) — każda kładzie
własne rzeczy, wymiana następuje, gdy obie dadzą Ready. Ten moduł to walidacja i sama wymiana;
bot ocenia stół ``bot_accepts`` (⚠️ ZAŁOŻENIE do czasu warstwy AI).

Asymetria frakcji przez hooki: transakcja bez sąsiedztwa (``POINT_TRANSACTION_ANY_PLAYER`` —
Guild Ships, Trade Convoys), karty akcji w transakcji (``POINT_TRANSACTION_ACTION_CARDS`` —
Arbiters; ``POINT_TRANSACTION_EXTRA_ITEMS`` — Black Market Dealings). Funkcje są CZYSTE.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from src.core import (
    action_budget,
    capture,
    card_draw,
    chronicle,
    control,
    economy,
    hand_limit,
    promissory_notes,
    relic_fragments,
    relics,
    rules_hooks,
    secret_objectives,
    triggers,
    unit_ops,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import AgendaStep, GameState, Phase
from src.core.hex_grid import HexGrid
from src.core.neighbors import neighbors_of


@dataclass(frozen=True)
class TransactionSide:
    """Jedna strona stołu: to, co dany gracz ODDAJE partnerowi (kładzie na stół)."""

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
    # Przechwycone statki/mechy PARTNERA zwracane mu do rezerwy (typy bazowe, R_capture /
    # R_transactions: tylko pierwotnemu właścicielowi, bez żetonów myśliwców/piechoty).
    captured_units: tuple[str, ...] = field(default_factory=tuple)
    # Poza transakcją (RULES.md 47.1b, 47.4): ile SWOICH żetonów długu kładę (pamięć stołu),
    # „darmowe secondary Trade” (tylko posiadacz karty w kroku 3) i obietnica „wash −N”.
    debt_tokens: int = 0
    trade_secondary: bool = False
    wash: int | None = None

    def has_extras(self) -> bool:
        """Czy strona oddaje coś spoza standardowej listy (relikty / karty akcji / tajne cele)."""
        return bool(self.relics or self.action_cards or self.secret_objectives)

    def has_components(self) -> bool:
        """Czy strona oddaje komponenty gry (to, co wymaga prawdziwej transakcji 47.1)."""
        return not (
            self.trade_goods == 0
            and self.commodities == 0
            and self.promissory_note is None
            and not self.relic_fragments
            and not self.planets
            and not self.captured_units
            and not self.has_extras()
        )

    def is_empty(self) -> bool:
        """Czy strona nic nie kładzie na stół (ani komponentów, ani długu, ani umowy Trade)."""
        return (
            not self.has_components()
            and self.debt_tokens == 0
            and not self.trade_secondary
            and self.wash is None
        )

    def components(self) -> TransactionSide:
        """Sama część transakcyjna strony (bez długu i umowy Trade)."""
        return replace(self, debt_tokens=0, trade_secondary=False, wash=None)

    def to_dict(self) -> dict[str, Any]:
        """Postać zapisywana w ``TransactionTable`` (JSON-owalna)."""
        raw = asdict(self)
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in raw.items()}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> TransactionSide:
        """Odtwarza stronę zapisaną w ``TransactionTable``."""
        note = raw.get("promissory_note")
        wash = raw.get("wash")
        return cls(
            trade_goods=int(raw.get("trade_goods", 0)),
            commodities=int(raw.get("commodities", 0)),
            promissory_note=str(note) if note else None,
            relic_fragments=tuple(str(x) for x in raw.get("relic_fragments", ())),
            relics=tuple(str(x) for x in raw.get("relics", ())),
            action_cards=tuple(str(x) for x in raw.get("action_cards", ())),
            secret_objectives=tuple(str(x) for x in raw.get("secret_objectives", ())),
            planets=tuple(str(x) for x in raw.get("planets", ())),
            captured_units=tuple(str(x) for x in raw.get("captured_units", ())),
            debt_tokens=int(raw.get("debt_tokens", 0)),
            trade_secondary=bool(raw.get("trade_secondary", False)),
            wash=None if wash is None else int(wash),
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


def extras_allowed(state: GameState, a: str, b: str) -> bool:
    """Czy ta para może wymieniać relikty i tajne cele (Black Market Dealings)."""
    return _either_permits(state, rules_hooks.POINT_TRANSACTION_EXTRA_ITEMS, a, b)


def tradable_relics(state: GameState, giver: str, partner: str) -> list[str]:
    """Relikty ``giver``, które może teraz położyć na stole: wszystkie przy Black Market Dealings,
    inaczej tylko te z tekstem „may be exchanged as part of a transaction” (The Silver Flame)."""
    held = list(state.players[giver].relics)
    if extras_allowed(state, giver, partner):
        return held
    own_rule = rules_hooks.forbidden(rules_hooks.POINT_TRANSACTION_TRADABLE_RELICS, state, giver)
    return [r for r in held if r in own_rule]


def reachable(state: GameState, grid: HexGrid, a: str, b: str) -> bool:
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
    # Relikt z tekstem „may be exchanged as part of a transaction” (The Silver Flame) - zawsze.
    own_rule = rules_hooks.forbidden(
        rules_hooks.POINT_TRANSACTION_TRADABLE_RELICS, state, giver_id
    )
    restricted = [r for r in side.relics if r not in own_rule]
    if (restricted or side.secret_objectives) and not allowed:
        raise ValueError(
            "Relics and secret objectives can only be traded with Black Market Dealings."
        )
    giver = state.players[giver_id]
    for relic, count in Counter(side.relics).items():
        if count > Counter(giver.relics)[relic]:
            raise ValueError(f"{who} does not have the relic '{relic}'.")
    if side.action_cards and hand_limit.action_card_excess(state, giver_id) > 0:
        # R_action_cards: nadwyżkę trzeba odrzucić — nie wolno jej oddać w transakcji.
        raise ValueError(f"{who} must first discard down to the action card hand limit.")
    for card, count in Counter(side.action_cards).items():
        if count > Counter(giver.private.action_cards)[card]:
            raise ValueError(f"{who} does not have the action card '{card}'.")
    for objective, count in Counter(side.secret_objectives).items():
        if count > Counter(giver.private.secret_objectives)[objective]:
            raise ValueError(
                f"{who} does not hold the unscored secret objective '{objective}'."
            )


def validate_own_side(state: GameState, giver_id: str, side: TransactionSide, who: str) -> None:
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
    """Pride of Kenara: planeta z hooka, cel = inna planeta oddającego, nie w trakcie walki.

    Cel jednostek zawsze wybiera ODDAJĄCY planetę (decyzja użytkownika 2026-11-13, RULES.md
    62.6) — kładąc planetę na stół (RULES.md 47.1b), od razu wskazuje cel swoich jednostek.
    """
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
        moving = {
            bt: n for bt, n in src_sys.planet_units.get(planet, {}).get(giver_id, {}).items()
            if n > 0
        }
        # F_hacan pride-of-kenara 4: najpierw zmiana kontroli, potem ruch jednostek - zyskujący
        # planetę ma okno „po zdobyciu” (Integrated Economy), zanim koegzystencja się skończy;
        # cudze jednostki koegzystujące na planecie zostają (R_coexistence 2.1).
        control.set_planet_control(state, position, planet, receiver_id)
        # F_hacan: Pride of Kenara na planecie w gravity rift - przenoszone jednostki rzucają
        # na usunięcie (R_gravity_rift; jeden rzut „na stół").
        lost = _rift_losses(state, position, giver_id, moving)
        for base_type, count in moving.items():
            gone = min(count, lost.get(base_type, 0))
            if gone:
                unit_ops.remove_units(
                    state, src_sys, planet, giver_id, base_type, gone, unit_ops.UnitCause.REMOVED
                )
            if count - gone > 0:
                unit_ops.transfer_units(
                    state, src_sys, planet, dest_sys, dest, giver_id, base_type, count - gone
                )


def _rift_losses(
    state: GameState, position: str, player_id: str, units: dict[str, int]
) -> dict[str, int]:
    """Straty od gravity rift przy przeniesieniu jednostek z planety w szczelinie (F_hacan)."""
    from src.core import board_graph, movement  # lokalnie: movement jest wyżej w zależnościach

    grid = board_graph.bound_grid()
    if grid is None or not units or not movement.is_gravity_rift(grid, position):
        return {}
    return movement.roll_rift_exit(state, player_id, units, position)


def _apply_side(state: GameState, giver_id: str, receiver_id: str, side: TransactionSide) -> None:
    """Przenosi komponenty ``side`` od ``giver_id`` do ``receiver_id`` (mutuje ``state``)."""
    # R_commodities: commodity oddana innemu graczowi staje się u odbiorcy trade good.
    economy.give_to_player(
        state, giver_id, receiver_id,
        trade_goods=side.trade_goods, commodities=side.commodities,
        cause="transaction",
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
    for base_type, count in sorted(Counter(side.captured_units).items()):
        capture.return_unit(state, giver_id, receiver_id, base_type, count)


def can_transact_with(
    state: GameState, grid: HexGrid, player_id: str, partner_id: str
) -> bool:
    """Czy ``player_id`` (aktywny) może TERAZ zrobić transakcję z ``partner_id``."""
    player = state.players.get(player_id)
    if player is None or partner_id == player_id or partner_id not in state.players:
        return False
    if partner_id in player.transacted_with:
        return False
    return reachable(state, grid, player_id, partner_id)


def agenda_window(state: GameState) -> bool:
    """Czy trwa rozstrzyganie agendy — okno transakcji fazy agendy (RULES.md 47.5).

    R_transactions: „While resolving each agenda during the agenda phase, a player may perform
    one transaction with each other player” — od ujawnienia agendy do „dalej” mówcy po wyniku.
    Między agendami (krok ujawniania) i po obu agendach okna nie ma.
    """
    agenda = state.agenda
    return (
        state.phase is Phase.AGENDA
        and agenda is not None
        and agenda.agenda_id is not None
        and agenda.step is not AgendaStep.COMPLETE
    )


def agenda_pair_free(state: GameState, a: str, b: str) -> bool:
    """Para ``a``-``b`` może zawrzeć transakcję przy bieżącej agendzie (bez sąsiedztwa, 47.5)."""
    if a == b or a not in state.players or b not in state.players:
        return False
    return (
        b not in state.players[a].transacted_with
        and a not in state.players[b].transacted_with
    )


def components_allowed(state: GameState, grid: HexGrid, a: str, b: str) -> bool:
    """Czy para ``a``-``b`` może teraz wymieniać KOMPONENTY (RULES.md 47.1b, 47.5).

    Faza akcji: jedna ze stron aktywna, druga osiągalna i bez transakcji w tej turze. Faza
    agendy (w trakcie agendy): KAŻDA para, jedna transakcja na agendę. Inaczej stół dopuszcza
    wyłącznie żetony długu.
    """
    if agenda_window(state):
        return agenda_pair_free(state, a, b)
    if state.phase is not Phase.ACTION:
        return False
    active = state.active_player_id
    if active not in (a, b) or action_budget.outside_turn(state, active):
        return False  # Puppets on a String: not a turn - only debt tokens (puppets-on-a-string/3)
    other = b if active == a else a
    return can_transact_with(state, grid, active, other)


def trade_partners(state: GameState, grid: HexGrid, player_id: str) -> list[str]:
    """Gracze, z którymi ``player_id`` może negocjować (sąsiedzi + efekty bez sąsiedztwa)."""
    return [
        pid for pid in state.players
        if pid != player_id and reachable(state, grid, player_id, pid)
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

    Faza agendy (RULES.md 47.5): ``player_id`` = gracz zaczynający, partner dowolny (bez
    sąsiedztwa), jedna transakcja pary na agendę.

    Raises:
        ValueError: Przy naruszeniu któregokolwiek z warunków.
    """
    if state.phase is Phase.AGENDA:
        return _validate_agenda_transaction(state, partner_id, give, receive, player_id)
    if state.phase is not Phase.ACTION:
        raise ValueError(
            "Transactions are resolved during the action phase or while an agenda is resolved."
        )
    active_id = state.active_player_id
    if active_id is None:
        raise ValueError("No active player in the action phase.")
    if player_id is not None and player_id != active_id:
        raise ValueError(f"It is not {player_id}'s turn (active: {active_id}).")
    if action_budget.outside_turn(state, active_id):
        # C_action_cards/puppets-on-a-string/3: the extra action is not that player's turn.
        raise ValueError(
            "Transactions are resolved on a player's turn - the extra action from Puppets on a "
            "String is not your turn."
        )
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
    if not reachable(state, grid, active_id, partner_id):
        raise ValueError("You can only make a transaction with a neighbor.")
    if not give.has_components() and not receive.has_components():
        raise ValueError("An empty transaction - add something to exchange.")
    validate_side(state, active_id, partner_id, give, "You")
    validate_side(state, partner_id, active_id, receive, "The partner")
    return active_id


def _validate_agenda_transaction(
    state: GameState,
    partner_id: str,
    give: TransactionSide,
    receive: TransactionSide,
    player_id: str | None,
) -> str:
    """Transakcja w fazie agendy (RULES.md 47.5): każda para raz na agendę, bez sąsiedztwa."""
    if not agenda_window(state):
        raise ValueError("Transactions in the agenda phase happen while an agenda is resolved.")
    if player_id is None or player_id not in state.players:
        raise ValueError("Name the player making the transaction.")
    if partner_id == player_id:
        raise ValueError("You cannot make a transaction with yourself.")
    if partner_id not in state.players:
        raise ValueError(f"Unknown player: {partner_id}")
    if not agenda_pair_free(state, player_id, partner_id):
        raise ValueError(
            "You already made a transaction with this player during this agenda "
            "(one per pair of players each agenda)."
        )
    if not give.has_components() and not receive.has_components():
        raise ValueError("An empty transaction - add something to exchange.")
    validate_side(state, player_id, partner_id, give, "You")
    validate_side(state, partner_id, player_id, receive, "The partner")
    return player_id


def validate_side(
    state: GameState, giver_id: str, partner_id: str, side: TransactionSide, who: str
) -> None:
    """Pełna walidacja jednej strony: posiadanie, planety (Pride of Kenara), karty akcji /
    relikty / cele (Arbiters, Black Market Dealings — efekt którejkolwiek strony wystarcza)."""
    validate_own_side(state, giver_id, side, who)
    _validate_planets(state, giver_id, side, who)
    _validate_captured(state, giver_id, partner_id, side, who)
    _validate_extras(
        state, giver_id, side, who,
        allowed=extras_allowed(state, giver_id, partner_id),
        cards_allowed=_either_permits(
            state, rules_hooks.POINT_TRANSACTION_ACTION_CARDS, giver_id, partner_id
        ),
    )


def _validate_captured(
    state: GameState, giver_id: str, partner_id: str, side: TransactionSide, who: str
) -> None:
    """Zwrot przechwyconych jednostek: tylko statki/mechy partnera z arkusza oddającego."""
    wanted = Counter(side.captured_units)
    for base_type, count in wanted.items():
        if capture.is_token(base_type):
            raise ValueError("Captured fighters and infantry cannot be returned in a transaction.")
        if capture.held(state, giver_id, base_type).get(partner_id, 0) < count:
            raise ValueError(f"{who} has not captured that many of the partner's {base_type}.")


def _receives_first(state: GameState, active_id: str, partner_id: str) -> str:
    """Kto pierwszy dostaje swoją część transakcji: aktywny gracz; w agendzie - od mówcy."""
    if state.phase is not Phase.AGENDA:
        return active_id
    order = [p for p in state.seating_order if p in state.players]
    if state.speaker_id in order:
        start = order.index(state.speaker_id)
        order = order[start:] + order[:start]
    ranked = {pid: i for i, pid in enumerate(order)}
    return min((active_id, partner_id), key=lambda pid: ranked.get(pid, len(ranked)))


def resolve_transaction(
    state: GameState,
    grid: HexGrid,
    partner_id: str,
    give: TransactionSide,
    receive: TransactionSide,
    player_id: str | None = None,
) -> GameState:
    """Wykonuje transakcję aktywnego gracza z ``partner_id`` (po zgodzie obu stron) — RULES.md 47.

    W fazie agendy ``player_id`` to gracz zaczynający (RULES.md 47.5).

    ``give`` = co oddaje aktywny gracz, ``receive`` = co dostaje od partnera. Walidacja:
    ``validate_transaction``. Nie pyta o zgodę — robi to stół (``core.transaction_table``,
    RULES.md 47.1b). Dług i umowa Trade z ``give``/``receive`` są pomijane (obsługuje je stół).

    Raises:
        ValueError: Transakcja nielegalna (``validate_transaction``).
    """
    give, receive = give.components(), receive.components()
    active_id = validate_transaction(state, grid, partner_id, give, receive, player_id)
    new_state = state.clone()
    # C_promissory_notes (Support for the Throne): przy jednoczesnej wymianie pierwszy zyskuje
    # (np. punkt) aktywny gracz, a w fazie agendy - pierwszy w kolejności od mówcy.
    if _receives_first(state, active_id, partner_id) == active_id:
        _apply_side(new_state, partner_id, active_id, receive)
        _apply_side(new_state, active_id, partner_id, give)
    else:
        _apply_side(new_state, active_id, partner_id, give)
        _apply_side(new_state, partner_id, active_id, receive)
    new_state.players[active_id].transacted_with.append(partner_id)
    if new_state.phase is Phase.AGENDA:
        # 47.5: limit dotyczy PARY graczy - odnotowany po obu stronach (zerowany z nową agendą).
        new_state.players[partner_id].transacted_with.append(active_id)
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


# ------------------------------------------------------------------ bot przy stole (47.1b)


def _value(side: TransactionSide) -> int:
    """Prosta wartość strony dla bota: TG/commodity/żeton długu = 1, notka / fragment / karta /
    relikt / cel / darmowe secondary Trade = 2."""
    return (
        side.trade_goods
        + side.commodities
        + side.debt_tokens
        + 2 * (side.promissory_note is not None)
        + 2 * (len(side.relic_fragments) + len(side.action_cards) + len(side.relics))
        + 2 * len(side.secret_objectives)
        + 2 * side.trade_secondary
    )


def bot_accepts(give: TransactionSide, receive: TransactionSide) -> bool:
    """⚠️ ZAŁOŻENIE (RULES.md 47.1b): bot przyjmuje, gdy dostaje co najmniej tyle, ile oddaje.

    ``give`` = co bot DOSTAJE (strona człowieka), ``receive`` = co bot ODDAJE (jego strona stołu).
    Placeholder do czasu warstwy AI — deterministyczny, bez losowania.
    """
    return _value(give) >= _value(receive)
