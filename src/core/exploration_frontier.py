"""Eksploracja żetonu FRONTIER (R_frontier_tokens, R_exploration) - RULES.md 57.

Żeton leży w systemie bez planet (``SystemState.frontier_token``). Eksplorujący dobiera kartę
z talii ``frontier`` i rozstrzyga ją w TYM SAMYM oknie eksploracji co planety
(``core/exploration``, bez planety: ``ExploreCurrent.planet == ""``). Karty natychmiastowe mają
tu opcje i skutki; fragmenty i żeton wormhole obsługuje wspólny kod eksploracji, a Mirage,
Ion Storm i Enigmatic Device obsługuje ``core/exploration`` (token/instant); bez handlera zostaje
tryb ręczny (``manual``).

Funkcje MUTUJĄ przekazany ``state`` (KLON roboczy wołającego).
"""

from __future__ import annotations

from src.core import command_tokens, economy, exploration, secret_objectives
from src.core.card_draw import draw_action_card
from src.core.game_state import ExplorationState, ExploreCurrent, GameState
from src.core.registry import StaticDataRegistry
from src.core.relics import draw_relic
from src.core.unit_catalog import is_space_unit

FRONTIER_DECK = "frontier"
_POOLS: tuple[tuple[str, str], ...] = (
    ("tactical", "Tactic"),
    ("fleet", "Fleet"),
    ("strategic", "Strategy"),
)


def can_explore_frontier(state: GameState, player_id: str, position: str) -> bool:
    """Czy gracz ma w systemie żeton frontier i statek (warunek Dark Energy Tap)."""
    system = state.systems.get(position)
    if system is None or not system.frontier_token:
        return False
    ships = system.space_units.get(player_id, {})
    return any(count > 0 and is_space_unit(base_type) for base_type, count in ships.items())


def start_frontier(
    state: GameState, registry: StaticDataRegistry, player_id: str, position: str
) -> None:
    """Zdejmuje żeton frontier z systemu i ujawnia kartę z talii frontier (okno eksploracji).

    Raises:
        ValueError: Brak żetonu w systemie, trwa inna eksploracja albo talia jest pusta.
    """
    system = state.systems.get(position)
    if system is None or not system.frontier_token:
        raise ValueError("There is no frontier token in this system.")
    ex = state.exploration
    if ex is not None and (ex.player_id != player_id or ex.current is not None):
        raise ValueError(
            "Finish the exploration in progress before starting a frontier exploration."
        )
    card_id = exploration.draw_card(state, registry, FRONTIER_DECK)
    system.frontier_token = False
    if ex is None:
        ex = ExplorationState(player_id=player_id, position=position)
        state.exploration = ex
    ex.current = ExploreCurrent(planet="", deck=FRONTIER_DECK, card_id=card_id)


# --------------------------------------------------------------------------- karty natychmiastowe

_Opt = exploration.ExploreOption
_SKIP = _Opt("skip", "Decline")


def _tokens_options(state: GameState, ex: ExplorationState, amount: int) -> list[_Opt]:
    left = state.players[ex.player_id].cc_reinf
    ok = left >= amount
    return [
        _Opt(
            "take",
            f"Gain {amount} command token{'s' if amount > 1 else ''}",
            ok,
            "" if ok else "Not enough command tokens in reinforcements.",
            _POOLS,
        )
    ]


def _gain_tokens(state: GameState, ex: ExplorationState, amount: int, pool: str | None) -> str:
    if pool not in dict(_POOLS):
        raise ValueError("Choose the pool for the command token.")
    command_tokens.gain_from_reinforcements(state, ex.player_id, {pool: amount})
    return f"Gained {amount} command token(s) ({dict(_POOLS)[pool]} pool)"


def _entropic(
    amount_tokens: int, trade_goods: int
) -> tuple[exploration.Options, exploration.Apply]:
    def options(state: GameState, ex: ExplorationState, cur: ExploreCurrent) -> list[_Opt]:
        return _tokens_options(state, ex, amount_tokens)

    def apply(
        state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
    ) -> str:
        summary = _gain_tokens(state, ex, amount_tokens, param)
        economy.gain_trade_goods(state, ex.player_id, trade_goods)
        return f"{summary}, {trade_goods} trade good(s)."

    return options, apply


def _keleres_options(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[_Opt]:
    return _tokens_options(state, ex, 2)


def _keleres_apply(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    return _gain_tokens(state, ex, 2, param) + "."


def _lost_crew_options(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[_Opt]:
    return [_Opt("draw", "Draw 2 action cards")]


def _lost_crew_apply(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    drawn = sum(1 for _ in range(2) if draw_action_card(state, ex.player_id))
    return f"Drew {drawn} action card(s)."


def _dead_world_options(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[_Opt]:
    return [_Opt("draw", "Draw 1 relic")]


def _dead_world_apply(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    registry = exploration.bound_registry()
    relic = draw_relic(
        state, registry, ex.player_id, source="explore", detail={"card": cur.card_id}
    )
    return f"Drew the relic {relic}." if relic else "The relic deck is empty."


def _derelict_options(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[_Opt]:
    if not state.decks.secret_objective_deck:
        return [
            _Opt("draw", "Draw 1 secret objective", False, "The secret objective deck is empty.")
        ]
    if secret_objectives.over_limit_after_draw(state, ex.player_id):
        hand = state.players[ex.player_id].private.secret_objectives
        return [
            _Opt(
                "draw",
                "Draw 1 secret objective (you must return an unscored one)",
                bool(hand),
                "" if hand else "You have no unscored secret objective to return.",
                tuple((oid, oid) for oid in hand),
            )
        ]
    return [_Opt("draw", "Draw 1 secret objective")]


def _derelict_apply(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    secret_objectives.draw(state, ex.player_id, param)
    return "Drew 1 secret objective."


def _merchant_options(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[_Opt]:
    player = state.players[ex.player_id]
    gap = economy.commodity_gap(state, ex.player_id)
    return [
        _Opt("replenish", "Replenish your commodities", gap > 0,
             "" if gap > 0 else "Commodities are already full."),
        _Opt("convert", "Convert your commodities to trade goods", player.commodities > 0,
             "" if player.commodities > 0 else "You have no commodities."),
        _SKIP,
    ]


def _merchant_apply(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    if option == "replenish":
        economy.replenish_commodities(state, ex.player_id)
        return "Replenished commodities."
    if option == "convert":
        amount = state.players[ex.player_id].commodities
        economy.convert_commodities_to_trade_goods(state, ex.player_id, amount)
        return f"Converted {amount} commodities to trade goods."
    return "Declined."


def _register() -> None:
    entropic = {
        "entropic field": _entropic(1, 2),
        "major entropic field": _entropic(1, 3),
        "minor entropic field": _entropic(1, 1),
    }
    for name, (options, apply) in entropic.items():
        exploration.register_instant(name, options, apply)
    exploration.register_instant("keleres ship", _keleres_options, _keleres_apply)
    exploration.register_instant("lost crew", _lost_crew_options, _lost_crew_apply)
    exploration.register_instant("dead world", _dead_world_options, _dead_world_apply)
    exploration.register_instant("derelict vessel", _derelict_options, _derelict_apply)
    exploration.register_instant("merchant station", _merchant_options, _merchant_apply)


_register()
