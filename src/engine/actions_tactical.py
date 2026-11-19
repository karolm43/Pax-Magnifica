"""Katalog akcji bota B5: akcja taktyczna, walka, Space Cannon, inwazja, eksploracja, karty akcji.

Każda akcja woła DOKŁADNIE tę funkcję ``core/`` i tę samą kontrolę aktora, co odpowiadający
endpoint (``api/routers/tactical|battle|space_cannon|capacity|invasion|exploration|action_cards``).
Mapa HTTP: ``api/bot_http``; zgodność katalog ↔ HTTP sprawdza fuzzer (``tests/engine``).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.core import (
    action_cards,
    battle,
    capacity,
    exploration,
    invasion,
    movement,
    production,
    space_cannon,
    tactical,
)
from src.core import actor as actor_rules
from src.core.game_state import GameState
from src.engine.action_base import (
    ActionBase,
    Apply,
    EngineContext,
    Guard,
    checked,
    claimed,
)

# --- Akcja taktyczna (RULES.md 31-33) --------------------------------------------------------


class TacticalActivate(ActionBase):
    kind: Literal["tactical_activate"] = "tactical_activate"
    position: str


class _Item(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CargoItem(_Item):
    """Ładunek ruchu: typ, liczba i strefa w systemie źródłowym (``space`` albo planeta)."""

    base_type: str
    count: int
    from_zone: str = "space"


class TacticalMove(ActionBase):
    kind: Literal["tactical_move"] = "tactical_move"
    from_position: str
    ships: dict[str, int]
    cargo: tuple[CargoItem, ...] = ()


class TacticalNext(ActionBase):
    kind: Literal["tactical_next"] = "tactical_next"


class ProduceItem(_Item):
    """Pozycja produkcji: typ, liczba sztuk i strefa (``space`` albo planeta)."""

    base_type: str
    count: int
    zone: str


class TacticalProduce(ActionBase):
    """Produkcja z płatnością automatyczną (``spend`` pominięty — jak przycisk „Auto”)."""

    kind: Literal["tactical_produce"] = "tactical_produce"
    orders: tuple[ProduceItem, ...]


class CapacityResolve(ActionBase):
    kind: Literal["capacity_resolve"] = "capacity_resolve"
    remove: dict[str, int] = Field(default_factory=dict)


# --- Walka (RULES.md 39) ---------------------------------------------------------------------


class BattleStart(ActionBase):
    kind: Literal["battle_start"] = "battle_start"
    planet: str | None = None


class BattleAfb(ActionBase):
    kind: Literal["battle_afb"] = "battle_afb"


class BattleRoll(ActionBase):
    kind: Literal["battle_roll"] = "battle_roll"


class BattleClose(ActionBase):
    kind: Literal["battle_close"] = "battle_close"


class BattleAnnounceRetreat(ActionBase):
    kind: Literal["battle_announce_retreat"] = "battle_announce_retreat"
    announce: bool = False


class BattleRetreat(ActionBase):
    kind: Literal["battle_retreat"] = "battle_retreat"
    destination: str


# --- Space Cannon Offense (RULES.md 38) ------------------------------------------------------


class SpaceCannonFire(ActionBase):
    kind: Literal["space_cannon_fire"] = "space_cannon_fire"
    target: str | None = None


class SpaceCannonPass(ActionBase):
    kind: Literal["space_cannon_pass"] = "space_cannon_pass"


class SpaceCannonAssign(ActionBase):
    kind: Literal["space_cannon_assign"] = "space_cannon_assign"
    sustain: dict[str, int] = Field(default_factory=dict)
    destroy: dict[str, int] = Field(default_factory=dict)
    destroy_damaged: dict[str, int] = Field(default_factory=dict)


# --- Inwazja (RULES.md 40) -------------------------------------------------------------------


class InvasionBegin(ActionBase):
    kind: Literal["invasion_begin"] = "invasion_begin"


class InvasionBombard(ActionBase):
    kind: Literal["invasion_bombard"] = "invasion_bombard"
    # (base_type, planeta, liczba) - każda jednostka z Bombardment musi dostać planetę.
    assignments: tuple[tuple[str, str, int], ...]


class InvasionBombardAssign(ActionBase):
    kind: Literal["invasion_bombard_assign"] = "invasion_bombard_assign"
    planet: str
    sustain: dict[str, int] = Field(default_factory=dict)
    destroy: dict[str, int] = Field(default_factory=dict)
    destroy_damaged: dict[str, int] = Field(default_factory=dict)


class InvasionCommit(ActionBase):
    kind: Literal["invasion_commit"] = "invasion_commit"
    commits: dict[str, dict[str, int]]


class InvasionCustodians(ActionBase):
    kind: Literal["invasion_custodians"] = "invasion_custodians"
    planets: tuple[str, ...]
    trade_goods: int = 0


class InvasionDefenseFire(ActionBase):
    kind: Literal["invasion_defense_fire"] = "invasion_defense_fire"
    planet: str


class InvasionDefensePass(ActionBase):
    kind: Literal["invasion_defense_pass"] = "invasion_defense_pass"
    planet: str


class InvasionDefenseAssign(ActionBase):
    kind: Literal["invasion_defense_assign"] = "invasion_defense_assign"
    planet: str
    sustain: dict[str, int] = Field(default_factory=dict)
    destroy: dict[str, int] = Field(default_factory=dict)
    destroy_damaged: dict[str, int] = Field(default_factory=dict)


class InvasionNext(ActionBase):
    kind: Literal["invasion_next"] = "invasion_next"


# --- Eksploracja (RULES.md 46) ---------------------------------------------------------------


class ExplorationDraw(ActionBase):
    kind: Literal["exploration_draw"] = "exploration_draw"
    planet: str
    deck: str | None = None


class ExplorationResolve(ActionBase):
    kind: Literal["exploration_resolve"] = "exploration_resolve"
    option: str
    param: str | None = None


class ExplorationFinish(ActionBase):
    kind: Literal["exploration_finish"] = "exploration_finish"


# --- Karty akcji (RULES.md 53) ---------------------------------------------------------------


class ActionCardPlay(ActionBase):
    kind: Literal["action_card_play"] = "action_card_play"
    card_id: str
    params: dict[str, Any] = Field(default_factory=dict)


TacticalAction = Annotated[
    TacticalActivate
    | TacticalMove
    | TacticalNext
    | TacticalProduce
    | CapacityResolve
    | BattleStart
    | BattleAfb
    | BattleRoll
    | BattleClose
    | BattleAnnounceRetreat
    | BattleRetreat
    | SpaceCannonFire
    | SpaceCannonPass
    | SpaceCannonAssign
    | InvasionBegin
    | InvasionBombard
    | InvasionBombardAssign
    | InvasionCommit
    | InvasionCustodians
    | InvasionDefenseFire
    | InvasionDefensePass
    | InvasionDefenseAssign
    | InvasionNext
    | ExplorationDraw
    | ExplorationResolve
    | ExplorationFinish
    | ActionCardPlay,
    Field(discriminator="kind"),
]


# --- Zastosowanie ----------------------------------------------------------------------------


def _move(s: GameState, c: EngineContext, a: TacticalMove) -> GameState:
    cargo = [
        movement.CargoPickup(base_type=i.base_type, count=i.count, from_zone=i.from_zone)
        for i in a.cargo
        if i.count > 0
    ]
    return movement.move_fleet(
        s, c.grid, c.registry, a.from_position, dict(a.ships), cargo, a.player_id
    )


def _produce(s: GameState, c: EngineContext, a: TacticalProduce) -> GameState:
    orders = [
        production.ProductionOrder(base_type=o.base_type, count=o.count, zone=o.zone)
        for o in a.orders
    ]
    return production.produce(s, c.grid, c.registry, a.player_id, orders, None)


def _activate(s: GameState, c: EngineContext, a: TacticalActivate) -> GameState:
    return tactical.activate_system(s, c.grid, a.position)


def _sc_fire(s: GameState, c: EngineContext, a: SpaceCannonFire) -> GameState:
    return space_cannon.fire_offense(s, c.grid, c.registry, a.player_id, a.target)


def _sc_assign(s: GameState, c: EngineContext, a: SpaceCannonAssign) -> GameState:
    return space_cannon.assign_hits(
        s, a.player_id, dict(a.destroy), sustain=dict(a.sustain),
        destroy_damaged=dict(a.destroy_damaged), registry=c.registry,
    )


def _bombard(s: GameState, c: EngineContext, a: InvasionBombard) -> GameState:
    return invasion.bombard(
        s, c.grid, c.registry,
        [invasion.BombardAssignment(bt, planet, n) for bt, planet, n in a.assignments],
        None, None,
    )


def _bombard_assign(s: GameState, c: EngineContext, a: InvasionBombardAssign) -> GameState:
    return invasion.assign_bombard_hits(
        s, c.grid, c.registry, a.planet, a.player_id, sustain=dict(a.sustain),
        destroy=dict(a.destroy), destroy_damaged=dict(a.destroy_damaged),
    )


def _defense_assign(s: GameState, c: EngineContext, a: InvasionDefenseAssign) -> GameState:
    return invasion.assign_defense_hits(
        s, c.grid, c.registry, a.planet, sustain=dict(a.sustain), destroy=dict(a.destroy),
        destroy_damaged=dict(a.destroy_damaged),
    )


def _play_card(s: GameState, c: EngineContext, a: ActionCardPlay) -> GameState:
    new_state, _implemented = action_cards.play_action_card(
        s, c.registry, a.player_id, a.card_id, dict(a.params), actor_id=a.player_id, now=c.now
    )
    return new_state


_TURN = actor_rules.turn_player
_SIDES = actor_rules.combat_sides
_ATTACKER = actor_rules.invasion_attacker
_PARTIES = actor_rules.invasion_parties
_EXPLORER = actor_rules.exploring_player

HANDLERS: dict[str, tuple[Guard | None, Apply]] = {
    "tactical_activate": (checked(_TURN, "Activate system"), _activate),
    "tactical_move": (claimed("Move ships"), _move),
    "tactical_next": (
        checked(_TURN, "Next tactical step"),
        lambda s, c, a: tactical.advance_skipping_empty(s, c.grid, c.registry),
    ),
    "tactical_produce": (claimed("Produce"), _produce),
    "capacity_resolve": (
        claimed("Resolve capacity"),
        lambda s, c, a: capacity.resolve_capacity(s, c.registry, a.player_id, dict(a.remove)),
    ),
    "battle_start": (
        checked(_TURN, "Start combat"),
        lambda s, c, a: battle.start_combat(s, c.grid, c.registry, a.planet),
    ),
    "battle_afb": (
        checked(_SIDES, "Anti-Fighter Barrage"),
        lambda s, c, a: battle.resolve_afb(s, c.grid, c.registry),
    ),
    "battle_roll": (
        checked(_SIDES, "Combat roll"),
        lambda s, c, a: battle.roll_round(s, c.grid, c.registry),
    ),
    "battle_close": (checked(_SIDES, "Close combat"), lambda s, c, a: battle.close_combat(s)),
    "battle_announce_retreat": (
        claimed("Announce retreat"),
        lambda s, c, a: battle.announce_retreat(s, c.grid, a.player_id, announce=a.announce),
    ),
    "battle_retreat": (
        claimed("Retreat"),
        lambda s, c, a: battle.retreat_from_combat(
            s, c.grid, c.registry, a.player_id, a.destination
        ),
    ),
    "space_cannon_fire": (claimed("Space Cannon fire"), _sc_fire),
    "space_cannon_pass": (
        claimed("Space Cannon pass"),
        lambda s, c, a: space_cannon.pass_offense(s, a.player_id),
    ),
    "space_cannon_assign": (claimed("Assign Space Cannon hits"), _sc_assign),
    "invasion_begin": (
        checked(_ATTACKER, "Begin invasion"),
        lambda s, c, a: _begin_invasion(s, c),
    ),
    "invasion_bombard": (checked(_ATTACKER, "Bombardment"), _bombard),
    "invasion_bombard_assign": (claimed("Assign bombardment hits"), _bombard_assign),
    "invasion_commit": (
        checked(_ATTACKER, "Commit ground forces"),
        lambda s, c, a: invasion.commit_ground_forces(
            s, c.registry, {p: dict(u) for p, u in a.commits.items()}
        ),
    ),
    "invasion_custodians": (
        checked(_ATTACKER, "Remove Custodians"),
        lambda s, c, a: invasion.claim_custodians(
            s, c.registry, list(a.planets), a.trade_goods
        ),
    ),
    "invasion_defense_fire": (
        checked(_PARTIES, "Space Cannon Defense"),
        lambda s, c, a: invasion.defense_fire(s, c.grid, c.registry, a.planet, None, None),
    ),
    "invasion_defense_pass": (
        checked(_PARTIES, "Space Cannon Defense"),
        lambda s, c, a: invasion.defense_pass(s, c.registry, a.planet),
    ),
    "invasion_defense_assign": (claimed("Assign defense hits"), _defense_assign),
    "invasion_next": (
        checked(_ATTACKER, "Next invasion step"),
        lambda s, c, a: invasion.advance(s, c.grid, c.registry),
    ),
    "exploration_draw": (
        checked(_EXPLORER, "Explore"),
        lambda s, c, a: exploration.draw(s, c.registry, a.planet, a.deck),
    ),
    "exploration_resolve": (
        checked(_EXPLORER, "Resolve exploration"),
        lambda s, c, a: exploration.resolve(s, c.registry, a.option, a.param),
    ),
    "exploration_finish": (
        checked(_EXPLORER, "Finish exploration"),
        lambda s, c, a: exploration.finish(s),
    ),
    # Router uzgadnia aktora z treścią (merge_claimed); tożsamość waliduje core.
    "action_card_play": (None, _play_card),
}


def _begin_invasion(s: GameState, c: EngineContext) -> GameState:
    """Jak router: ``begin_invasion`` bez okna inwazji (nic do zrobienia) = 422."""
    new_state = invasion.begin_invasion(s, c.grid, c.registry)
    if new_state.invasion is None:
        raise ValueError("Nothing to bombard or land - no ground forces in orbit.")
    return new_state
