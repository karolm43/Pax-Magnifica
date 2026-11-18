"""Emirates of Hacan — komplet komponentów frakcji (RULES.md 62.6).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("hacan")``, ``units``).
Rulingi: ``docs/rules_tirules/F_hacan.md``. Transakcje (Guild Ships, Arbiters, Trade Convoys,
Pride of Kenara) idą przez punkty ``transaction.*`` w ``core/transaction.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    battle,
    command_tokens,
    economy,
    exhaust,
    faction_components,
    leaders,
    production,
    promissory_notes,
    rules_hooks,
)
from src.core import offer_inputs as oi
from src.core.agenda_phase import VOTE_REFUND_KEY, current_voter
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, Phase, TacticalStep
from src.core.hooks import card_labels
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_AGENDA_VOTE_MODIFIER,
    POINT_PRODUCTION_FREE,
    POINT_STRATEGY_SECONDARY_FREE,
    POINT_TRANSACTION_ACTION_CARDS,
    POINT_TRANSACTION_ANY_PLAYER,
    POINT_TRANSACTION_PLANETS,
    SOURCE_BREAKTHROUGH,
    SOURCE_EFFECT,
    SOURCE_FACTION,
    SOURCE_PROMISSORY,
    SOURCE_TECHNOLOGY,
    SOURCE_UNIT,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.strategy_cards import trade
from src.core.unit_catalog import is_space_unit

FACTION = "hacan"
AGENT = "hacanagent"
COMMANDER = "hacancommander"
HERO = "hacanhero"
FLAGSHIP = "hacan_flagship"
MECH = "hacan_mech"
CONVOYS = "convoys"
BREAKTHROUGH = "hacanbt"
QDN = "qdn"
BIOMES = "pm"

HERO_FREE = f"leaders:{HERO}:free"  # efekt: koszt jednostek 0 w tym użyciu PRODUCTION
GILA_VOTES = f"leaders:{COMMANDER}:votes"  # efekt: dodatkowe głosy (data: votes)
_AGENT_COMMODITIES = 2  # „gain 2 commodities”
_COMMANDER_TG = 10  # „Have 10 trade goods.”
_VOTES_PER_TG = 2  # „cast 2 additional votes for each trade good spent”
_QDN_TG = 3  # „give another player 3 of your trade goods”
_BIOMES_GAIN, _BIOMES_OTHER = 4, 2  # „gain 4 trade goods … that player gains 2 trade goods”
_AUTO_FACTORIES_SHIPS = 3  # „3 or more non-fighter ships”
_SELF = "self"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _name(registry: Any, state: GameState, player_id: str) -> str:
    player = state.players.get(player_id)
    faction = registry.factions.get(player.faction or "") if player is not None else None
    return faction.name if faction is not None else player_id


def _hacan_players(state: GameState) -> list[str]:
    return [pid for pid, p in state.players.items() if p.faction == FACTION]


# ----------------------------------------------- Masters of Trade, Guild Ships, Arbiters


@register(
    POINT_STRATEGY_SECONDARY_FREE, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
    covers="abilities:master_of_trade",
)
def masters_of_trade(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Masters of Trade: You do not have to spend a command token to resolve the secondary
    ability of the "Trade" strategy card."""
    return int(ctx.get("initiative", 0)) == trade.INITIATIVE


@register(
    POINT_TRANSACTION_ANY_PLAYER, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
    covers="abilities:guild_ships",
)
def guild_ships(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Guild Ships: You can negotiate transactions with players who are not your neighbor."""
    return True


@register(
    POINT_TRANSACTION_ACTION_CARDS, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
    covers="abilities:arbiters",
)
def arbiters(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Arbiters: When you are negotiating a transaction, action cards can be exchanged as part of
    that transaction."""
    return True


# -------------------------------------------------------------- Trade Convoys (notka)


@register_effect(f"promissory_notes:{CONVOYS}")
def trade_convoys(
    _state: GameState, _registry: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """Trade Convoys: ACTION: Place this card faceup in your play area (położenie robi
    ``promissory_play``; skutek działa, póki karta leży w strefie)."""


@register(POINT_TRANSACTION_ANY_PLAYER, HookSource(SOURCE_PROMISSORY, CONVOYS), HookKind.PERMIT)
def convoys_any_player(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """While this card is in your play area, you may negotiate transactions with players who are
    not your neighbor."""
    return True


def _activated_hacan_system(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    system = state.systems.get(str(ctx.get("position")))
    if ctx.get("player") != player_id or system is None:
        return False
    owners = set(_hacan_players(state))
    present = set(system.space_units) | {
        pid for units in system.planet_units.values() for pid in units
    }
    return bool(owners & present) and CONVOYS in state.players[player_id].promissory_notes_in_play


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_PROMISSORY, CONVOYS),
    condition=_activated_hacan_system, covers=f"promissory_notes:{CONVOYS}",
    label="Trade Convoys returns to Hacan",
)
def convoys_return(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """If you activate a system that contains 1 or more of the Hacan player's units, return this
    card to the Hacan player (także gdy są tam tylko struktury — F_hacan)."""
    owner = next(iter(_hacan_players(state)), None)
    if owner is not None:
        promissory_notes.return_from_play(state, player_id, owner, CONVOYS)


# ------------------------------------------------------- Quantum Datahub Node (technologia)


def _qdn_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    player = state.players[player_id]
    return (
        ctx.get("phase") == "strategy"
        and command_tokens.can_spend_strategy_token(state, player_id)
        and player.trade_goods >= _QDN_TG
        and bool(player.strategy_cards)
        and any(p.strategy_cards for pid, p in state.players.items() if pid != player_id)
    )


def qdn_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    mine = [
        oi.option(str(i), card_labels.describe_strategy_card(registry, i), ref=("strategy", i))
        for i in state.players[player_id].strategy_cards
    ]
    theirs = [
        oi.option(
            f"{pid}|{i}",
            card_labels.describe_strategy_card(
                registry, i, f"held by {_name(registry, state, pid)}"
            ),
            ref=("strategy", i),
        )
        for pid, p in state.players.items()
        if pid != player_id
        for i in p.strategy_cards
    ]
    return [
        oi.choice("give", "Strategy card you give", mine),
        oi.choice("take", "Strategy card you take (that player gets 3 trade goods)", theirs),
        *command_tokens.strategy_token_input(state, player_id),  # Scepter of Emelpar
    ]


@on_event(
    GameEvent.PHASE, Moment.END, HookSource(SOURCE_TECHNOLOGY, QDN), where={"phase": "strategy"},
    optional=True, condition=_qdn_ready, inputs=qdn_inputs, covers=f"technologies:{QDN}",
    label="Quantum Datahub Node: swap strategy cards",
)
def quantum_datahub_node(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Quantum Datahub Node: At the end of the strategy phase, you may spend 1 token from your
    strategy pool and give another player 3 of your trade goods. If you do, give 1 of your
    strategy cards to that player and take 1 of their strategy cards."""
    params = ctx.get("params", {})
    give = int(params.get("give") or 0)
    other, _, raw = str(params.get("take") or "").partition("|")
    take = int(raw or 0)
    me = state.players[player_id]
    if give not in me.strategy_cards or other not in state.players or other == player_id:
        raise ValueError("Choose one of your strategy cards and one of another player's.")
    them = state.players[other]
    if take not in them.strategy_cards:
        raise ValueError("That player does not have this strategy card.")
    # F_hacan: 3 TG trzeba mieć PRZED wydaniem żetonu (nie dobiera się trzeciego po wydaniu).
    if me.trade_goods < _QDN_TG:
        raise ValueError("You need 3 trade goods before you spend the command token.")
    command_tokens.spend_strategy_token(state, player_id, source=params.get("token_source"))
    economy.give_to_player(state, player_id, other, trade_goods=_QDN_TG, commodities=0)
    me.strategy_cards = [take if c == give else c for c in me.strategy_cards]
    them.strategy_cards = [give if c == take else c for c in them.strategy_cards]


# ------------------------------------------------------------ Production Biomes (ACTION)


@register_effect_inputs(f"technologies:{BIOMES}")
def biomes_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [
        oi.option(pid, _name(registry, state, pid)) for pid in state.players if pid != player_id
    ]
    return [
        oi.choice("player", "Player who gains 2 trade goods", options),
        *command_tokens.strategy_token_input(state, player_id),  # Scepter of Emelpar
    ]


@register_effect(f"technologies:{BIOMES}")
def production_biomes(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Production Biomes: ACTION: Exhaust this card and spend 1 token from your strategy pool to
    gain 4 trade goods and choose 1 other player; that player gains 2 trade goods."""
    other = str(params.get("player") or "")
    if other not in state.players or other == player_id:
        raise ValueError("Choose another player.")
    player = state.players[player_id]
    if BIOMES in player.exhausted_technologies:
        raise ValueError("Production Biomes is exhausted.")
    if not command_tokens.can_spend_strategy_token(state, player_id):
        raise ValueError("Production Biomes needs 1 command token in your strategy pool.")
    exhaust.exhaust_technology(state, player_id, BIOMES)
    command_tokens.spend_strategy_token(state, player_id, source=params.get("token_source"))
    economy.gain_trade_goods(state, player_id, _BIOMES_GAIN)
    economy.gain_trade_goods(state, other, _BIOMES_OTHER)


# --------------------------------------------------------- Carth of Golden Sands (agent)


@faction_components.window_use("leader", AGENT, standing=True)
def _agent_window(state: GameState, _registry: StaticDataRegistry, _player_id: str) -> str | None:
    if state.phase is not Phase.ACTION:
        return "Carth of Golden Sands is used during the action phase."
    if state.exploration is not None and state.exploration.current is not None:
        # F_hacan: nie w trakcie rozstrzygania innej zdolności (ujawniona karta eksploracji).
        return "Resolve the current exploration card first."
    return None


@register_effect_inputs(f"leaders:{AGENT}")
def agent_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [oi.option(_SELF, f"Gain {_AGENT_COMMODITIES} commodities")] + [
        oi.option(pid, f"Replenish {_name(registry, state, pid)}'s commodities")
        for pid in state.players
        if pid != player_id
    ]
    return [oi.choice("target", "Carth of Golden Sands", options)]


@register_effect(f"leaders:{AGENT}")
def carth_of_golden_sands(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Carth of Golden Sands: During the action phase: You may exhaust this card to gain 2
    commodities or replenish another player's commodities."""
    target = str(params.get("target") or _SELF)
    if target == _SELF:
        economy.gain_commodities(state, player_id, _AGENT_COMMODITIES)
    elif target in state.players and target != player_id:
        economy.replenish_commodities(state, target)
    else:
        raise ValueError("Choose yourself or another player.")


# ------------------------------------------------------- Gila the Silvertongue (commander)


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 10 trade goods."""
    return state.players[player_id].trade_goods >= _COMMANDER_TG


@faction_components.window_use("leader", COMMANDER)
def _commander_window(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> str | None:
    if state.phase is not Phase.AGENDA or state.agenda is None:
        return "Gila the Silvertongue is used when you cast votes."
    try:
        voter = current_voter(state)
    except ValueError:
        voter = None
    if voter != player_id:
        return "Use Gila the Silvertongue on your turn to vote."
    if economy.spendable_trade_goods(state, player_id) < 1:
        return "You have no trade goods to spend."
    return None


@register_effect_inputs(f"leaders:{COMMANDER}")
def commander_inputs(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    most = economy.spendable_trade_goods(state, player_id)
    return [oi.number("trade_goods", "Trade goods to spend (2 votes each)", 1, max(1, most))]


@register_effect(f"leaders:{COMMANDER}")
def gila_the_silvertongue(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Gila the Silvertongue: When you cast votes: You may spend any number of trade goods: cast 2
    additional votes for each trade good spent (dla tego samego wyniku — F_hacan)."""
    spent = int(params.get("trade_goods") or 0)
    if spent < 1:
        raise ValueError("Spend at least 1 trade good.")
    economy.spend_trade_goods(state, player_id, spent)
    active_effects.add_effect(
        state, GILA_VOTES, Duration.AGENDA, owner=player_id,
        data={"votes": spent * _VOTES_PER_TG, VOTE_REFUND_KEY: spent},
    )


@register(POINT_AGENDA_VOTE_MODIFIER, HookSource(SOURCE_EFFECT, GILA_VOTES), HookKind.MODIFY)
def gila_votes(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """F_hacan: przy 0 zwykłych głosów (wstrzymanie się) dodatkowych głosów nie ma."""
    if int(ctx.get("base_votes", 0) or 0) <= 0:
        return 0
    return sum(
        int(e.data.get("votes", 0))
        for e in active_effects.effects_for(state, player_id, GILA_VOTES)
    )


# ------------------------------------------------- Harrugh Gefhara — Galactic Securities Net


def _producing_now(state: GameState, player_id: str) -> bool:
    """Gracz właśnie używa PRODUCTION i nic jeszcze nie wyprodukował (okno „when … use")."""
    if production.production_player(state) != player_id or state.production_used > 0:
        return False
    return (
        production.standalone_grant(state) is not None
        or state.tactical_step is TacticalStep.PRODUCTION
    )


@faction_components.window_use("leader", HERO)
def _hero_window(state: GameState, _registry: StaticDataRegistry, player_id: str) -> str | None:
    if not _producing_now(state, player_id):
        return "Use Harrugh Gefhara when your units use PRODUCTION, before you produce."
    if active_effects.has_effect(state, player_id, HERO_FREE):
        return "Galactic Securities Net is already in effect."
    return None


@register_effect(f"leaders:{HERO}")
def galactic_securities_net(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Harrugh Gefhara — Galactic Securities Net: When 1 or more of your units use PRODUCTION: You
    may reduce the cost of each of your units to 0 during this use of PRODUCTION. If you do, purge
    this card. (Limity PRODUCTION zostają — F_hacan.)"""
    scope = Duration.TACTICAL_ACTION if state.tactical_step is not None else Duration.TURN
    active_effects.add_effect(state, HERO_FREE, scope, owner=player_id)


@register(POINT_PRODUCTION_FREE, HookSource(SOURCE_EFFECT, HERO_FREE), HookKind.PERMIT)
def hero_free(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return True


# --------------------------------------------------------- Wrath of Kenara (flagowiec)


def _kenara_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    combat = state.active_combat
    if (
        combat is None
        or combat.kind != "space"
        or ctx.get("kind") != "combat"
        or ctx.get("player") != player_id
        or economy.spendable_trade_goods(state, player_id) < 1
    ):
        return False
    system = state.systems.get(combat.position)
    return system is not None and system.space_units.get(player_id, {}).get("flagship", 0) > 0


def kenara_inputs(
    state: GameState, _registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Kości własnego rzutu tej rundy, które jeszcze nie dostały +1 (1 TG za kość)."""
    combat = state.active_combat
    options: list[dict[str, Any]] = []
    if combat is not None:
        for index, entry in enumerate(combat.rolls.get(player_id, [])):
            done = set(entry.get("boosted", {}).get(FLAGSHIP, []))
            bonus = list(entry.get("bonus") or [0] * len(entry["dice"]))
            for die, value in enumerate(entry["dice"]):
                if die in done:
                    continue
                shown = int(value) + int(entry.get("modifier", 0)) + int(bonus[die])
                options.append(oi.option(
                    f"{index}:{die}", f"{entry.get('baseType', '')}: {shown} -> {shown + 1}",
                    meta=oi.die_meta(shown, int(entry["hitsOn"]), str(entry.get("baseType", ""))),
                ))
    most = min(len(options), economy.spendable_trade_goods(state, player_id))
    return [oi.multi("dice", "Dice to improve by +1 (1 trade good each)", options, 1, max(1, most))]


@on_event(
    GameEvent.COMBAT_ROLL, Moment.AFTER, HookSource(SOURCE_UNIT, FLAGSHIP),
    optional=True, condition=_kenara_ready, inputs=kenara_inputs,
    covers=f"units:{FLAGSHIP}", label="Wrath of Kenara: +1 for a trade good",
)
def wrath_of_kenara(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Wrath of Kenara: After you roll a die during a space combat in this system, you may spend 1
    trade good to apply +1 to the result (raz na kość, po 1 TG za każdą — F_hacan)."""
    raw = ctx.get("params", {}).get("dice") or []
    chosen: set[tuple[int, int]] = set()
    for item in raw:
        index, _, die = str(item).partition(":")
        chosen.add((int(index), int(die)))
    if not chosen:
        raise ValueError("Choose at least one die.")
    economy.spend_trade_goods(state, player_id, len(chosen))
    battle.boost_combat_dice(state, player_id, chosen, FLAGSHIP)


# ------------------------------------------------------------- Pride of Kenara (mech)


@register(
    POINT_TRANSACTION_PLANETS, HookSource(SOURCE_UNIT, MECH), HookKind.FORBID,
    covers=f"units:{MECH}",
)
def pride_of_kenara(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Pride of Kenara: This planet's card may be traded as part of a transaction; if you do, move
    all of your units from this planet to another planet you control."""
    planets: set[str] = set()
    for system in state.systems.values():
        for planet, owner in system.planet_owners.items():
            if owner == player_id and system.planet_units.get(planet, {}).get(
                player_id, {}
            ).get("mech", 0) > 0:
                planets.add(planet)
    return planets


# --------------------------------------------------------------- Auto-Factories (BT)


def _non_fighter_ships(units: Mapping[str, Any]) -> int:
    return sum(
        int(n) for bt, n in dict(units).items() if is_space_unit(str(bt)) and bt != "fighter"
    )


def _many_ships(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """✅ Decyzja użytkownika 2026-11-17: liczą się statki z CAŁEJ akcji (wszystkie zamówienia
    produkcji, ``production_placed``), a przełom działa raz na akcję - w chwili, gdy suma
    przekroczy próg (zamówienie, przed którym było mniej niż 3, a po którym jest 3+)."""
    if ctx.get("player") != player_id:
        return False
    total = sum(_non_fighter_ships(by_type) for by_type in state.production_placed.values())
    before = total - _non_fighter_ships(ctx.get("units") or {})
    return before < _AUTO_FACTORIES_SHIPS <= total


@on_event(
    GameEvent.UNITS_PRODUCED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    condition=_many_ships, covers=f"breakthroughs:{BREAKTHROUGH}",
    label="Auto-Factories: +1 fleet token",
)
def auto_factories(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Auto-Factories: When you produce 3 or more non-fighter ships, place 1 command token from your
    reinforcements into your fleet pool. (Suma z całej akcji, raz na akcję - ``_many_ships``.)"""
    if command_tokens.reinforcements(state, player_id) > 0:
        command_tokens.gain_from_reinforcements(state, player_id, {"fleet": 1})
