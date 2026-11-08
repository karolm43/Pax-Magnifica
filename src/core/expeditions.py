"""Ekspedycje Thunder's Edge — plastry żetonu, przełom, wejście The Fracture i Thunder's Edge.

Reguły: ``docs/rules_tirules/R_expedition.md``, ``R_breakthroughs.md``, ``R_fracture.md``
(RULES.md 50). Zakres: KOSZTY i skutki układowe (zajęcie plastra, zdobycie przełomu, rzut na
Fracture, położenie Thunder's Edge). Zdolności przełomów i legendarna zdolność Thunder's Edge
NIE są kodowane — to osobny etap.

Funkcje zwracają NOWY ``GameState`` (klon) albo rzucają ``ValueError`` (HTTP 422).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core import (
    card_draw,
    control,
    economy,
    exhaust,
    fracture,
    payment,
    secret_objectives,
    unit_ops,
)
from src.core import technology as tech
from src.core.breakthrough import unlock_breakthrough
from src.core.expedition_state import EXPEDITION_SLICES, ThundersEdgePlacement
from src.core.game_state import GameState, Phase, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.system_planets import planets_of_system

THUNDERS_EDGE_PLANET = "thundersedge"

# Koszty plastrów wyrażone liczbą (R_expedition): zasoby/wpływ/TG/karty akcji.
RESOURCES_COST = 5
INFLUENCE_COST = 5
TRADE_GOODS_COST = 3
ACTION_CARDS_COST = 2


@dataclass
class ExpeditionPayment:
    """Czym gracz płaci za plaster (używane pola zależą od plastra)."""

    planets: list[str] = field(default_factory=list)  # fiveRes / fiveInf
    trade_goods: int = 0  # fiveRes / fiveInf (TG zastępują zasób/wpływ)
    action_cards: list[str] = field(default_factory=list)  # actionCards (dokładnie 2)
    secret: str | None = None  # secret
    tech_planet: str | None = None  # techSkip


def free_slices(state: GameState) -> list[str]:
    """Wolne plastry w kolejności zegarowej od góry."""
    return [s for s in EXPEDITION_SLICES if s not in state.expeditions.claims]


def expedition_block_reason(state: GameState, actor_id: str | None) -> str:
    """Powód, dla którego gracz NIE może teraz wykonać ekspedycji (pusty = może).

    Ekspedycję wykonuje się NA KONIEC własnej tury (R_expedition), w fazie akcji.
    """
    if not free_slices(state):
        return "All expedition slices have been claimed."
    if state.phase is not Phase.ACTION:
        return "An expedition can only be performed in the action phase."
    if actor_id is None or state.active_player_id != actor_id:
        return f"It is not {actor_id}'s turn (active: {state.active_player_id})."
    player = state.players.get(actor_id)
    if player is None:
        return f"Unknown player: {actor_id}"
    if not (player.took_action_this_turn or player.passed):
        return "An expedition is performed at the END of your turn - take an action or pass first."
    blockers = {
        "a timing window is open": state.pending_window is not None,
        "a strategy card is still being resolved": state.pending_strategy is not None,
        "a combat is in progress": state.active_combat is not None,
        "an invasion is in progress": state.invasion is not None,
        "an exploration is in progress": state.exploration is not None,
        "ingress tokens are waiting to be placed": bool(state.fracture.pending),
        "Thunder's Edge is waiting to be placed": state.expeditions.pending_placement is not None,
    }
    for reason, blocked in blockers.items():
        if blocked:
            return f"Cannot perform an expedition: {reason}."
    if state.expeditions.performed_by == actor_id:
        return "You already performed an expedition this turn."
    return ""


def _require_expedition_moment(state: GameState, actor_id: str) -> None:
    reason = expedition_block_reason(state, actor_id)
    if reason:
        raise ValueError(reason)


def _pay(
    state: GameState,
    registry: StaticDataRegistry,
    actor_id: str,
    slice_id: str,
    pay: ExpeditionPayment,
) -> None:
    """Pobiera koszt plastra z gracza — MUTUJE ``state`` (klon). Waliduje przed zmianą."""
    if slice_id == "fiveRes":
        _pay_value(state, registry, actor_id, "resources", RESOURCES_COST, pay)
    elif slice_id == "fiveInf":
        _pay_value(state, registry, actor_id, "influence", INFLUENCE_COST, pay)
    elif slice_id == "tradeGoods":
        if economy.spendable_trade_goods(state, actor_id) < TRADE_GOODS_COST:
            raise ValueError(f"You need {TRADE_GOODS_COST} trade goods.")
        economy.spend_as_trade_goods(state, actor_id, TRADE_GOODS_COST)
    elif slice_id == "actionCards":
        if len(pay.action_cards) != ACTION_CARDS_COST:
            raise ValueError(f"Choose exactly {ACTION_CARDS_COST} action cards to discard.")
        card_draw.discard_specific_action_cards(state, actor_id, pay.action_cards)
    elif slice_id == "secret":
        if pay.secret is None:
            raise ValueError("Choose an unscored secret objective to discard.")
        secret_objectives.discard_unscored(state, actor_id, pay.secret)
    elif slice_id == "techSkip":
        ready = tech.specialty_planets(state, registry, actor_id)
        if pay.tech_planet is None or pay.tech_planet not in ready:
            raise ValueError(
                "Choose a ready planet of yours that has a technology specialty to exhaust."
            )
        exhaust.exhaust_planets(state, actor_id, [pay.tech_planet])
    else:  # pragma: no cover - slice_id jest walidowany wcześniej
        raise ValueError(f"Unknown expedition slice: {slice_id}")


def _pay_value(
    state: GameState,
    registry: StaticDataRegistry,
    actor_id: str,
    kind: payment.Kind,
    needed: int,
    pay: ExpeditionPayment,
) -> None:
    spent = payment.validate_payment(state, registry, actor_id, kind, pay.planets, pay.trade_goods)
    if spent < needed:
        raise ValueError(f"You must spend at least {needed} {kind} (selected {spent}).")
    payment.apply_payment(state, actor_id, pay.planets, pay.trade_goods)


def gain_breakthrough(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
) -> None:
    """Gracz zdobywa przełom swojej frakcji i robi rzut na The Fracture — MUTUJE ``state``.

    Nic nie robi, gdy frakcja nie ma przełomu w danych albo gracz już go ma. Zdolności
    przełomu NIE są wykonywane (tylko odblokowanie i rzut — R_breakthroughs).
    """
    breakthrough = unlock_breakthrough(state, registry, player_id)
    if breakthrough is None:
        return
    fracture.roll_for_fracture(state, registry, grid, player_id, breakthrough.id)


def perform_expedition(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    actor_id: str,
    slice_id: str,
    pay: ExpeditionPayment,
) -> GameState:
    """Gracz wykonuje ekspedycję: płaci, zajmuje plaster, zdobywa przełom (+ rzut na Fracture).

    Sześć plastrów: pięć zasobów, 2 karty akcji, pięć wpływu, 1 niepunktowany tajny cel,
    wyczerpanie planety ze specjalnością, trzy trade goods. Maks. jeden plaster na turę;
    plaster raz zajęty nie wraca. Szósty plaster wprowadza Thunder's Edge (oczekujące
    położenie — :func:`place_thunders_edge`).

    Raises:
        ValueError: Zły moment, plaster zajęty / nieznany, niewystarczający koszt.
    """
    if slice_id not in EXPEDITION_SLICES:
        raise ValueError(f"Unknown expedition slice: {slice_id}")
    _require_expedition_moment(state, actor_id)
    if slice_id in state.expeditions.claims:
        raise ValueError("That expedition slice has already been claimed.")

    new_state = state.clone()
    _pay(new_state, registry, actor_id, slice_id, pay)
    new_state.expeditions.claims[slice_id] = actor_id
    new_state.expeditions.performed_by = actor_id
    gain_breakthrough(new_state, registry, grid, actor_id)

    if not free_slices(new_state):
        counts: dict[str, int] = {}
        for owner in new_state.expeditions.claims.values():
            counts[owner] = counts.get(owner, 0) + 1
        most = max(counts.values())
        new_state.expeditions.pending_placement = ThundersEdgePlacement(
            player_id=actor_id,
            counts=counts,
            leaders=sorted(p for p, n in counts.items() if n == most),
        )
    return new_state


# ------------------------------------------------------------------------------ Thunder's Edge


def thunders_edge_targets(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid
) -> list[str]:
    """Systemy, w których wolno położyć Thunder's Edge.

    R_expedition: system bez planety, bez supernovy i bez wydrukowanego wormhole, poza The
    Fracture. Żeton frontier nie przeszkadza (zostaje w systemie).
    """
    result: list[str] = []
    for position in sorted(grid.positions):
        if fracture.is_fracture_position(position):
            continue
        definition = registry.systems.get(grid.system_id_at(position))
        if definition is None or "hyperlane" in (definition.name or "").lower():
            continue
        if definition.wormholes or "SUPERNOVA" in definition.anomalies:
            continue
        if planets_of_system(state, registry, position, grid):
            continue
        result.append(position)
    return result


def place_thunders_edge(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    actor_id: str,
    position: str,
    infantry_player_id: str | None = None,
) -> GameState:
    """Kładzie Thunder's Edge w systemie ``position`` i stawia na nim piechotę.

    Piechotę (tyle sztuk, ile plastrów) stawia gracz z NAJWIĘKSZĄ liczbą plastrów; przy remisie
    wybiera go gracz kładący Thunder's Edge (``infantry_player_id``, może wskazać siebie).
    Stawiający piechotę przejmuje kontrolę nad Thunder's Edge. Zdolność legendarna — poza zakresem.

    Raises:
        ValueError: Brak oczekującego położenia, zły gracz, zły system, zły wybór przy remisie.
    """
    placement = state.expeditions.pending_placement
    if placement is None:
        raise ValueError("Thunder's Edge is not waiting to be placed.")
    if actor_id != placement.player_id:
        raise ValueError(f"Only {placement.player_id} places Thunder's Edge.")
    if position not in thunders_edge_targets(state, registry, grid):
        raise ValueError(
            f"System {position} cannot hold Thunder's Edge (it needs an empty system with no "
            "planet, supernova or printed wormhole, outside The Fracture)."
        )
    if len(placement.leaders) == 1:
        infantry_player = placement.leaders[0]
    elif infantry_player_id in placement.leaders:
        infantry_player = str(infantry_player_id)
    else:
        raise ValueError(f"Tie for the most slices - choose one of: {placement.leaders}.")

    new_state = state.clone()
    system = new_state.systems.get(position)
    if system is None:
        system = SystemState(position=position, system_id=grid.system_id_at(position))
        new_state.systems[position] = system
    system.added_planets = [*system.added_planets, THUNDERS_EDGE_PLANET]
    unit_ops.place_units(
        new_state,
        system,
        THUNDERS_EDGE_PLANET,
        infantry_player,
        "infantry",
        placement.counts[infantry_player],
        unit_ops.UnitCause.PLACED,
    )
    control.set_planet_control(new_state, position, THUNDERS_EDGE_PLANET, infantry_player)
    new_state.expeditions.thunders_edge_position = position
    new_state.expeditions.pending_placement = None
    return new_state
