"""The Yssaril Tribes — every faction component (RULES.md 62.22).

Texts in docstrings are quotes from the assets (``catalog.faction_bundle("yssaril")``, units
``yssaril_flagship`` / ``yssaril_mech``, breakthrough ``yssarilbt``). Rulings:
``docs/rules_tirules/F_yssaril.md`` (cross-checked: ``R_action_cards``, ``R_leaders``,
``R_transactions``, ``C_agendas``, ``C_action_cards``, ``C_relics``, ``F_naalu``, ``F_nomad``,
``F_mentak``).
Engine points used/added for the Yssaril: draw batches (``card_draw.draw_action_cards`` - one
``ACTION_CARDS_DRAWN`` per draw, Scheming), ``hand_limit.unlimited`` (Crafty), the leader proxy
(``rules_hooks.register_leader_proxy`` - Ssruu), ``faction_components.granted_abilities``
(Deepgloom lends Stall Tactics), ``movement.pass_foreign_ships`` (Y'sia Y'ssrila) and
``transaction.grant_pair`` (Deepgloom Executable).

Every "look at a hand" is a decision of the player who looks: offer inputs are projected only to
their decider (``visibility.project_strict``), so nobody else sees the cards.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    action_budget,
    active_effects,
    board_graph,
    card_draw,
    cooperative,
    entropic_scar,
    faction_components,
    leaders,
    promissory_play,
    relic_actions,
    rules_hooks,
    transaction,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.components import ComponentCategory
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, Phase
from src.core.hooks import card_labels
from src.core.production import reinforcements_left
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_ACTION_CARDS_FORBIDDEN,
    POINT_HAND_LIMIT_UNLIMITED,
    POINT_MOVEMENT_PASS_FOREIGN_SHIPS,
    SOURCE_BREAKTHROUGH,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_UNIT,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.unit_ops import UnitCause

FACTION = "yssaril"
STALL = "stall_tactics"
SCHEMING = "scheming"
CRAFTY = "crafty"
TRANSPARASTEEL = "tp"
MAGEON = "mi"
AGENT = "yssarilagent"
COMMANDER = "yssarilcommander"
HERO = "yssarilhero"
SPY_NET = "spynet"
FLAGSHIP = "yssaril_flagship"
MECH = "yssaril_mech"
BREAKTHROUGH = "yssarilbt"

STALL_KEY = f"abilities:{STALL}"
SCHEMING_KEY = f"abilities:{SCHEMING}"
# ``FACTION_ABILITY_USED`` abilities of the follow-up decisions (ctx ``ability``):
MAGEON_PICK = f"technologies:{MAGEON}:pick"  # the Yssaril takes 1 card of the looked-at hand
SO_ATA_LOOK = f"leaders:{COMMANDER}:look"  # the Yssaril looks at the chosen hand
KYVER_SHOW = f"leaders:{HERO}:show"  # another player shows 1 action card
KYVER_CHOOSE = f"leaders:{HERO}:choose"  # the Yssaril takes it or forces 3 random discards
SPY_NET_PICK = f"promissory_notes:{SPY_NET}:pick"  # the holder takes 1 of the Yssaril's cards
DEEPGLOOM_SCHEMING = f"breakthroughs:{BREAKTHROUGH}:scheming"  # the drawer may use Scheming
# Active effects:
KYVER = f"leaders:{HERO}:guild_of_spies"  # the shown cards + the KeyMoment areas
SPY_NET_PLAYED = f"promissory_notes:{SPY_NET}:played"  # once per timing window (spy-net 3)
DEEPGLOOM_STALL = f"breakthroughs:{BREAKTHROUGH}:stall_tactics"  # Stall Tactics lent to a player

_MECH = "mech"
_FLAGSHIP = "flagship"
_KYVER_DISCARDS = 3  # "discard 3 random action cards"
_COMMANDER_HAND = 7  # "Have 7 action cards."
_TAKE, _DISCARD, _DONE, _USE, _DECLINE = "take", "discard", "done", "use", "decline"
_HANDS = {  # So Ata: what may be looked at -> (label, ref kind)
    "action_cards": ("action cards", "actionCard"),
    "promissory_notes": ("promissory notes", "promissory"),
    "secret_objectives": ("secret objectives", "objective"),
}


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _fire(state: GameState, player_id: str, ctx: dict[str, Any]) -> None:
    from src.core import triggers  # local: the hooks package loads before triggers

    triggers.fire(state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
                  ctx={"player": player_id, **ctx})


def yssaril_player(state: GameState) -> str | None:
    """The Yssaril player at the table (owner of Spy Net and Deepgloom Executable), or None."""
    return next((pid for pid, p in sorted(state.players.items()) if p.faction == FACTION), None)


def _name(state: GameState, player_id: str) -> str:
    return card_labels.describe_player(state, _registry(), player_id)


def _order_from(state: GameState, player_id: str) -> list[str]:
    """Players in seating order starting after ``player_id`` (``player_id`` itself excluded)."""
    seats = [p for p in state.seating_order if p in state.players] or sorted(state.players)
    if player_id not in seats:
        return [p for p in seats if p != player_id]
    at = seats.index(player_id)
    return seats[at + 1:] + seats[:at]


def _hand(state: GameState, player_id: str) -> list[str]:
    return list(state.players[player_id].private.action_cards)


def card_name(registry: StaticDataRegistry, card_id: str) -> str:
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
    return str(getattr(card, "name", None) or card_id)


def _card_options(state: GameState, registry: StaticDataRegistry, player_id: str
                  ) -> list[dict[str, Any]]:
    """The player's action cards as card chips (description on click)."""
    return [
        oi.option(card, card_name(registry, card), ref=("actionCard", card))
        for card in dict.fromkeys(_hand(state, player_id))
    ]


def _player_options(state: GameState, players: list[str]) -> list[dict[str, Any]]:
    return [oi.option(pid, _name(state, pid)) for pid in players]


def _target(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def _drawer(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["player"])


# ================================================================================ Stall Tactics


@faction_components.blocker("ability", STALL)
def _stall_blocker(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> str | None:
    return None if _hand(state, player_id) else "You have no action cards in your hand."


@register_effect_inputs(STALL_KEY)
def stall_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """No "Auto" (user decision 2026-11-27)."""
    options = _card_options(state, registry, player_id)
    return [oi.choice("card", "Action card to discard", options, always=True)]


@register_effect(STALL_KEY)
def stall_tactics(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Stall Tactics: ACTION: Discard 1 action card from your hand (a faction ability, not an
    action card - Sabotage cannot cancel it, stall-tactics 1).

    Used by another player through Deepgloom Executable: the loan is consumed and that player may
    make a transaction with the Yssaril (RULES.md 62.22)."""
    hand = _hand(state, player_id)
    card = str(params.get("card") or (hand[0] if hand else ""))
    if card not in hand:
        raise ValueError("Choose an action card from your hand.")
    card_draw.discard_specific_action_cards(state, player_id, [card])
    owner = yssaril_player(state)
    if owner is not None and owner != player_id:
        lent = [e for e in state.active_effects
                if e.key == DEEPGLOOM_STALL and e.owner == player_id]
        for effect in lent[:1]:
            active_effects.remove_effect(state, effect.id)
        transaction.grant_pair(state, owner, player_id, source=f"breakthroughs:{BREAKTHROUGH}")
        ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                           f"Stall Tactics used; may make a transaction with {_name(state, owner)}")
    _fire(state, player_id, {"ability": STALL_KEY})


# ===================================================================== Blackshade Infiltrator


def _mech_planets(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """Controlled planets on the board, outside an entropic scar (DEPLOY - RULES.md 1.5)."""
    registry = _registry()
    found: list[tuple[str, str]] = []
    for planet in sorted(state.players[player_id].controlled_planets):
        position = card_labels.system_position_of_planet(state, planet)
        if position is None or entropic_scar.unit_abilities_blocked(state, position, registry):
            continue
        found.append((position, planet))
    return found


def _deploy_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    left = reinforcements_left(state, player_id, _MECH)
    return (
        ctx.get("player") == player_id and (left is None or left > 0)
        and bool(_mech_planets(state, player_id))
    )


def deploy_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """No "Auto" (user decision 2026-11-27)."""
    options = [
        oi.option(planet, card_labels.describe_planet(state, registry, planet),
                  ref=("planet", planet))
        for _pos, planet in _mech_planets(state, decider)
    ]
    return [oi.choice("planet", "Planet for 1 mech (Blackshade Infiltrator)", options,
                      always=True)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_UNIT, MECH),
    where={"ability": STALL_KEY}, optional=True, condition=_deploy_ready, inputs=deploy_inputs,
    covers=f"units:{MECH}", label="Blackshade Infiltrator: DEPLOY",
)
def blackshade_infiltrator(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Blackshade Infiltrator: DEPLOY: After you use your Stall Tactics faction ability, you may
    place 1 mech on a planet you control."""
    params = ctx.get("params") or {}
    places = {planet: pos for pos, planet in _mech_planets(state, player_id)}
    planet = str(params.get("planet") or next(iter(places), ""))
    if planet not in places:
        raise ValueError("Choose a planet you control.")
    unit_ops.place_units(state, state.systems[places[planet]], planet, player_id, _MECH, 1,
                         UnitCause.PLACED)


# ===================================================================================== Scheming


def _scheme(state: GameState, player_id: str) -> None:
    """Draw 1 additional action card (no new draw event - scheming 2), then the drawer's
    mandatory discard (decision below)."""
    card_draw.draw_without_event(state, player_id)
    _fire(state, player_id, {"ability": SCHEMING_KEY})


def _own_draw(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and not promissory_play.silenced(state, player_id)


@on_event(
    GameEvent.ACTION_CARDS_DRAWN, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    condition=_own_draw, covers=SCHEMING_KEY, label="Scheming",
)
def scheming(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Scheming: When you draw 1 or more action cards: Draw 1 additional action card. Then, choose
    and discard 1 action card from your hand (one extra card per draw - scheming 1, 2)."""
    _scheme(state, player_id)


def _has_cards(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    drawer = str(ctx.get("player") or "")
    return drawer in state.players and bool(_hand(state, drawer))


def scheming_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Any card of the hand (scheming 3). No "Auto" (user decision 2026-11-27)."""
    return [oi.choice("card", "Scheming: action card to discard",
                      _card_options(state, registry, decider), always=True)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": SCHEMING_KEY}, condition=_has_cards, decide=True, decider=_drawer,
    inputs=scheming_inputs, label="Scheming: discard 1 action card",
)
def scheming_discard(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    """The mandatory discard - nothing else resolves until it is made (scheming 4)."""
    drawer = str(ctx["decider"])
    hand = _hand(state, drawer)
    card = str((ctx.get("params") or {}).get("card") or (hand[-1] if hand else ""))
    if card not in hand:
        raise ValueError("Choose an action card from your hand.")
    card_draw.discard_specific_action_cards(state, drawer, [card])


# ======================================================================================= Crafty


@register(POINT_HAND_LIMIT_UNLIMITED, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers=f"abilities:{CRAFTY}")
def crafty(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Crafty: You can have any number of action cards in your hand. Game effects cannot prevent
    you from using this ability (read before any limit change - Executive Sanctions, crafty 1)."""
    return True


# ======================================================================= Transparasteel Plating

_PLATING = rules_hooks.declare_rule_source(f"technologies:{TRANSPARASTEEL}:passed_players")


@register(POINT_ACTION_CARDS_FORBIDDEN, _PLATING, HookKind.FORBID,
          covers=f"technologies:{TRANSPARASTEEL}")
def transparasteel_plating(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Transparasteel Plating: During your turn of the action phase, players that have passed
    cannot play action cards (only action cards - tp 1; Puppets on a String is not the Yssaril's
    turn - C_action_cards puppets 2.1)."""
    active = state.active_player_id
    owner = state.players.get(active or "")
    player = state.players.get(player_id)
    if (
        state.phase is not Phase.ACTION or owner is None or player is None or not player.passed
        or active == player_id or TRANSPARASTEEL not in owner.technologies
        or action_budget.outside_turn(state, str(active))
    ):
        return set()
    return {"Transparasteel Plating: players that have passed cannot play action cards "
            "during this player's turn."}


# ============================================================================= Mageon Implants


def _mageon_targets(state: GameState, player_id: str) -> list[str]:
    return [p for p in _order_from(state, player_id) if _hand(state, p)]


@register_effect_inputs(f"technologies:{MAGEON}")
def mageon_inputs(
    state: GameState, _registry_: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.22): only players with action cards. No "Auto" (user
    decision 2026-11-27)."""
    targets = _mageon_targets(state, player_id)
    return [oi.choice("player", "Player whose action cards you look at",
                      _player_options(state, targets), always=True)]


@register_effect(f"technologies:{MAGEON}")
def mageon_implants(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Mageon Implants: ACTION: Exhaust this card to look at another player's hand of action
    cards. Choose 1 of those cards and add it to your hand (not a draw - mi 1)."""
    from src.core import exhaust  # local: exhaust is imported by the hooks package

    target = str(params.get("player") or "")
    if target not in _mageon_targets(state, player_id):
        raise ValueError("Choose another player who holds action cards.")
    if MAGEON in state.players[player_id].exhausted_technologies:
        raise ValueError("Mageon Implants is exhausted.")
    exhaust.exhaust_technology(state, player_id, MAGEON)
    ability_notes.note(state, player_id, f"technologies:{MAGEON}",
                       f"looks at {_name(state, target)}'s action cards")
    _fire(state, player_id, {"ability": MAGEON_PICK, "target": target})


def _target_has_cards(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    target = str(ctx.get("target") or "")
    return target in state.players and bool(_hand(state, target))


def mageon_pick_inputs(
    state: GameState, registry: StaticDataRegistry, _decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """No "Auto" (user decision 2026-11-27)."""
    target = str(ctx["target"])
    options = _card_options(state, registry, target)
    return [oi.choice("card", f"{_name(state, target)}'s action cards: take 1", options,
                      always=True)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": MAGEON_PICK}, condition=_target_has_cards, decide=True,
    inputs=mageon_pick_inputs, label="Mageon Implants: take 1 action card",
)
def mageon_pick(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The Yssaril takes the chosen card (they may not show the hand to anyone - mi 2)."""
    target = str(ctx["target"])
    hand = _hand(state, target)
    card = str((ctx.get("params") or {}).get("card") or (hand[0] if hand else ""))
    if card not in hand:
        raise ValueError("Choose one of that player's action cards.")
    card_draw.transfer_action_card(state, target, player_id, card)


# ======================================================================================== Ssruu


def _ssruu_usable(state: GameState, player_id: str) -> bool:
    """The player has Ssruu on their faction sheet and it is not purged or locked."""
    registry = rules_hooks.bound_registry()
    player = state.players.get(player_id)
    if registry is None or player is None:
        return False
    faction = registry.factions.get(player.faction or "")
    if faction is None or AGENT not in faction.leaders:
        return False
    return player.leader_states.get(AGENT) not in (leaders.PURGED, leaders.LOCKED)


@rules_hooks.register_leader_proxy
def ssruu(state: GameState, player_id: str) -> dict[str, str]:
    """Ssruu: At any time: This card has the text ability of each other player's agent, even if
    that agent is exhausted - every other player's agent resolves to Ssruu for its owner (state,
    exhaustion and sources - RULES.md 62.22). Reads the state directly (no hooks)."""
    if not _ssruu_usable(state, player_id):
        return {}
    registry = rules_hooks.bound_registry()
    found: dict[str, str] = {}
    for pid, other in state.players.items():
        theirs = registry.factions.get(other.faction or "") if pid != player_id else None
        for leader_id in theirs.leaders if theirs is not None else ():
            leader = registry.leaders.get(leader_id)
            if leader is not None and leader.type == "agent" and leader_id != AGENT:
                found[leader_id] = AGENT
    return found


@relic_actions.register_relic_proxy
def ssruu_relics(state: GameState, player_id: str) -> dict[str, str]:
    """Ssruu also has the text of another player's relic that is an agent, even if exhausted
    (JR-XS455-O - C_relics jrxs455o 1.2): using it exhausts Ssruu (RULES.md 62.22)."""
    if not _ssruu_usable(state, player_id):
        return {}
    return {
        relic: AGENT
        for pid, other in state.players.items() if pid != player_id
        for relic in other.relics if relic_actions.is_agent_relic(relic)
    }


# Ssruu's own text has no effect - the proxy above is the whole ability.
rules_hooks.declare_core_rule(f"leaders:{AGENT}")


# ======================================================================================== So Ata


@leaders.register_unlock(COMMANDER)
def _so_ata_unlocked(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 7 action cards (checked only while no decision is open - a pending Scheming
    discard stops it, scheming 4)."""
    return len(_hand(state, player_id)) >= _COMMANDER_HAND


def _hand_of(state: GameState, player_id: str, kind: str) -> list[str]:
    return list(getattr(state.players[player_id].private, kind))


def _system_has_units(state: GameState, player_id: str, position: str) -> bool:
    system = state.systems.get(position)
    if system is None:
        return False
    if any(n > 0 for n in system.space_units.get(player_id, {}).values()):
        return True
    return any(
        n > 0 for by in system.planet_units.values() for n in by.get(player_id, {}).values()
    )


def _so_ata_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    other = str(ctx.get("player") or "")
    return (
        other in state.players and other != player_id
        and leaders.is_ready(state, _registry(), player_id, COMMANDER)
        and _system_has_units(state, player_id, str(ctx.get("position") or ""))
        and any(_hand_of(state, other, kind) for kind in _HANDS)
    )


def so_ata_inputs(
    state: GameState, _registry_: StaticDataRegistry, _decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Only non-empty hands. No "Auto" (user decision 2026-11-27)."""
    other = str(ctx["player"])
    options = [
        oi.option(kind, f"{label.capitalize()} ({len(_hand_of(state, other, kind))})")
        for kind, (label, _ref) in _HANDS.items() if _hand_of(state, other, kind)
    ]
    return [oi.choice("hand", f"Look at {_name(state, other)}'s", options, always=True)]


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_so_ata_ready, inputs=so_ata_inputs,
    covers=f"leaders:{COMMANDER}", label="So Ata: look at that player's cards",
)
def so_ata(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """So Ata: After another player activates a system that contains your units: You may look at
    that player's action cards, promissory notes, or secret objectives."""
    other = str(ctx["player"])
    kind = str((ctx.get("params") or {}).get("hand") or "action_cards")
    if kind not in _HANDS or not _hand_of(state, other, kind):
        raise ValueError("Choose a hand that player holds cards in.")
    ability_notes.note(state, player_id, f"leaders:{COMMANDER}",
                       f"looks at {_name(state, other)}'s {_HANDS[kind][0]}")
    _fire(state, player_id, {"ability": SO_ATA_LOOK, "target": other, "hand": kind})


def _look_option(state: GameState, registry: StaticDataRegistry, kind: str, card: str
                 ) -> dict[str, Any]:
    ref = _HANDS[kind][1]
    if ref == "actionCard":
        return oi.option(card, card_name(registry, card), ref=(ref, card))
    if ref == "promissory":
        name, _text = promissory_play.note_text(state, registry, card)
        return oi.option(card, name, ref=(ref, card))
    objective = registry.catalog.get(ComponentCategory.SECRET_OBJECTIVE, card)
    return oi.option(card, str(getattr(objective, "name", None) or card), ref=(ref, card))


def look_inputs(
    state: GameState, registry: StaticDataRegistry, _decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The looked-at cards as read-only chips + "Done"."""
    target, kind = str(ctx["target"]), str(ctx["hand"])
    cards = [_look_option(state, registry, kind, c)
             for c in dict.fromkeys(_hand_of(state, target, kind))]
    return [
        oi.info("seen", f"{_name(state, target)}'s {_HANDS[kind][0]}", cards,
                hint="Only you see these cards.", show=True),
        oi.choice("done", "When you have seen them", [oi.option(_DONE, "Done")], always=True),
    ]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    where={"ability": SO_ATA_LOOK}, decide=True, inputs=look_inputs,
    label="So Ata: the cards you look at",
)
def so_ata_look(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Looking changes nothing; the decision only shows the cards to the Yssaril."""


# ============================================================ Kyver, Blade and Key — Guild of Spies


@register_effect(f"leaders:{HERO}")
def kyver(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Kyver, Blade and Key — Guild of Spies: ACTION: Each other player shows you 1 action card
    from their hand. For each player, you may either take that card or force that player to
    discard 3 random action cards from their hand. Then, purge this card (purge = the leader's
    cost, paid after this effect).

    ⚠️ ASSUMPTION (RULES.md 62.22): the players show their cards in seating order from the Yssaril;
    each shown card is decided before the next player's."""
    targets = [p for p in _order_from(state, player_id) if _hand(state, p)]
    homes = board_graph.home_positions_by_player(state, registry)
    areas = {pos: "kyver" for pid in _order_from(state, player_id) for pos in homes.get(pid, [])}
    active_effects.add_effect(state, KYVER, Duration.TURN, owner=player_id,
                              data={"areas": areas, "shown": {}})
    ability_notes.note(state, player_id, f"leaders:{HERO}",
                       "each other player shows 1 action card")
    for target in targets:
        _fire(state, player_id, {"ability": KYVER_SHOW, "target": target})


def show_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The shower chooses the card (kyver 1). No "Auto" (user decision 2026-11-27)."""
    options = _card_options(state, registry, decider)
    return [oi.choice("card", "Action card you show the Yssaril player", options, always=True)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": KYVER_SHOW}, condition=_target_has_cards, decide=True, decider=_target,
    inputs=show_inputs, label="Kyver, Blade and Key: show 1 action card",
)
def kyver_show(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    shower = str(ctx["decider"])
    hand = _hand(state, shower)
    card = str((ctx.get("params") or {}).get("card") or (hand[0] if hand else ""))
    if card not in hand:
        raise ValueError("Choose an action card from your hand.")
    for effect in state.active_effects:
        if effect.key == KYVER and effect.owner == player_id:
            effect.data = {**effect.data, "shown": {**dict(effect.data.get("shown") or {}),
                                                    shower: card}}
    _fire(state, player_id, {"ability": KYVER_CHOOSE, "target": shower, "card": card})


def choose_inputs(
    state: GameState, registry: StaticDataRegistry, _decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """No "Auto" (user decision 2026-11-27)."""
    target, card = str(ctx["target"]), str(ctx["card"])
    name = card_name(registry, card)
    options = []
    if card in _hand(state, target):
        options.append(oi.option(_TAKE, f"Take {name}", ref=("actionCard", card)))
    left = min(_KYVER_DISCARDS, len(_hand(state, target)))
    options.append(oi.option(_DISCARD, f"{_name(state, target)} discards {left} random "
                                       "action card(s)"))
    return [
        oi.info("shown", f"{_name(state, target)} shows you", [
            oi.option(card, name, ref=("actionCard", card))], show=True),
        oi.choice("choice", "Take that card or force the discard", options, always=True),
    ]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": KYVER_CHOOSE}, decide=True, inputs=choose_inputs,
    label="Kyver, Blade and Key: take the card or force 3 discards",
)
def kyver_choose(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    target, card = str(ctx["target"]), str(ctx["card"])
    choice = str((ctx.get("params") or {}).get("choice") or _TAKE)
    if choice == _TAKE and card in _hand(state, target):
        card_draw.transfer_action_card(state, target, player_id, card)  # not a draw - kyver 2
        detail = f"took an action card from {_name(state, target)}"
    elif choice in (_TAKE, _DISCARD):
        gone = card_draw.discard_random_action_cards(state, target, _KYVER_DISCARDS)
        detail = f"{_name(state, target)} discarded {len(gone)} random action card(s)"
    else:
        raise ValueError("Take the card or force the discard.")
    ability_notes.note(state, player_id, f"leaders:{HERO}", detail)


# ===================================================================================== Spy Net


@promissory_play.condition(SPY_NET)
def _spy_net_condition(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, window: OpenWindow
) -> str | None:
    owner = yssaril_player(state)
    if window.subject != player_id:
        return "Spy Net is played at the start of your turn."
    if active_effects.has_effect(state, player_id, SPY_NET_PLAYED):
        return "Spy Net was already played in this timing window."  # spy-net 3
    if owner is None or not _hand(state, owner):
        return "The Yssaril player has no action cards."
    return None


@register_effect(f"promissory_notes:{SPY_NET}")
def spy_net(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Spy Net: At the start of your turn: Look at the Yssaril player's hand of action cards.
    Choose 1 of those cards and add it to your hand. Then, return this card to the Yssaril player
    (return - ``promissory_play``)."""
    owner = str(params.get("__owner") or yssaril_player(state) or "")
    if owner not in state.players:
        raise ValueError("The Yssaril player is not in the game.")
    active_effects.add_effect(state, SPY_NET_PLAYED, Duration.TURN, owner=player_id)
    ability_notes.note(state, player_id, f"promissory_notes:{SPY_NET}",
                       f"looks at {_name(state, owner)}'s action cards")
    _fire(state, player_id, {"ability": SPY_NET_PICK, "target": owner})


def spy_pick_inputs(
    state: GameState, registry: StaticDataRegistry, _decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """No "Auto" (user decision 2026-11-27)."""
    owner = str(ctx["target"])
    options = _card_options(state, registry, owner)
    return [oi.choice("card", f"{_name(state, owner)}'s action cards: take 1", options,
                      always=True)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": SPY_NET_PICK}, condition=_target_has_cards, decide=True, decider=_drawer,
    inputs=spy_pick_inputs, label="Spy Net: take 1 action card",
)
def spy_net_pick(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    holder, owner = str(ctx["decider"]), str(ctx["target"])
    hand = _hand(state, owner)
    card = str((ctx.get("params") or {}).get("card") or (hand[0] if hand else ""))
    if card not in hand:
        raise ValueError("Choose one of the Yssaril player's action cards.")
    card_draw.transfer_action_card(state, owner, holder, card)


# ============================================================================== Y'sia Y'ssrila


@register(POINT_MOVEMENT_PASS_FOREIGN_SHIPS, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.PERMIT,
          covers=f"units:{FLAGSHIP}")
def ysia_yssrila(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Y'sia Y'ssrila: This ship can move through systems that contain other player's ships
    (Aerie Hololattice still blocks it - a separate point, ysia 2)."""
    return ctx.get("base_type") == _FLAGSHIP


# ======================================================================== Deepgloom Executable


def _deepgloom_scheming_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    drawer = str(ctx.get("player") or "")
    return drawer in state.players and drawer != player_id


# Cooperative (RULES.md 54.15 e): the drawing player may ask / pay to use Scheming; the Yssaril
# is still offered the allowance (mutual - it gains the transaction).
cooperative.register_pull(f"breakthroughs:{BREAKTHROUGH}", mutual=True)


@on_event(
    GameEvent.ACTION_CARDS_DRAWN, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    optional=True, condition=_deepgloom_scheming_ready, covers=f"breakthroughs:{BREAKTHROUGH}",
    label="Deepgloom Executable: allow that player to use Scheming",
)
def deepgloom_allow_scheming(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Deepgloom Executable: You can allow other players to use your ... SCHEMING faction
    ability (whenever it would be used - deepgloom 3); that player decides below."""
    _fire(state, player_id, {"ability": DEEPGLOOM_SCHEMING, "target": str(ctx["player"])})


def allowed_inputs(
    _state: GameState, _registry_: StaticDataRegistry, _decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """No "Auto" (user decision 2026-11-27)."""
    return [oi.choice("use", "Scheming (allowed by the Yssaril player)", [
        oi.option(_USE, "Draw 1 additional action card, then discard 1"),
        oi.option(_DECLINE, "Do not use Scheming"),
    ], always=True)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    where={"ability": DEEPGLOOM_SCHEMING}, decide=True, decider=_target, inputs=allowed_inputs,
    label="Scheming (Deepgloom Executable)",
)
def deepgloom_scheming(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The allowed player uses Scheming; when they do, they may make a transaction with the
    Yssaril (no neighbours, any player's turn, not counted - deepgloom 1, 2)."""
    other = str(ctx["decider"])
    if str((ctx.get("params") or {}).get("use") or _USE) != _USE:
        return
    transaction.grant_pair(state, player_id, other, source=f"breakthroughs:{BREAKTHROUGH}")
    ability_notes.note(state, other, f"breakthroughs:{BREAKTHROUGH}",
                       f"Scheming used; may make a transaction with {_name(state, player_id)}")
    _scheme(state, other)


@faction_components.window_use("breakthrough", BREAKTHROUGH, standing=True)
def _deepgloom_window(state: GameState, _registry_: StaticDataRegistry, player_id: str
                      ) -> str | None:
    if state.phase is not Phase.ACTION:
        return "Stall Tactics is lent to another player during the action phase."
    if not _lend_targets(state, player_id):
        return "Every other player may already use your Stall Tactics."
    return None


def _lend_targets(state: GameState, player_id: str) -> list[str]:
    lent = {e.owner for e in state.active_effects if e.key == DEEPGLOOM_STALL}
    return [p for p in _order_from(state, player_id) if p not in lent]


# Cooperative (RULES.md 54.15 e): another player may ask / pay to be lent Stall Tactics (the
# deal is for the requester: ``player`` must be them); the Yssaril keeps its own window.
cooperative.register_pull_component(
    "breakthrough", BREAKTHROUGH, _lend_targets, mutual=True, target="player"
)


@register_effect_inputs(f"breakthroughs:{BREAKTHROUGH}")
def deepgloom_inputs(
    state: GameState, _registry_: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """No "Auto" (user decision 2026-11-27)."""
    targets = _lend_targets(state, player_id)
    return [oi.choice("player", "Player you allow to use Stall Tactics",
                      _player_options(state, targets), always=True)]


@register_effect(f"breakthroughs:{BREAKTHROUGH}")
def deepgloom_lend_stall(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Deepgloom Executable: You can allow other players to use your STALL TACTICS ... faction
    ability: that player owns it as a component action until they use it or the action phase
    ends (⚠️ ASSUMPTION RULES.md 62.22); using it grants the transaction (``stall_tactics``)."""
    other = str(params.get("player") or "")
    if other not in _lend_targets(state, player_id):
        raise ValueError("Choose another player.")
    active_effects.add_effect(state, DEEPGLOOM_STALL, Duration.PHASE, owner=other,
                              data={"abilities": [STALL], "yssaril": player_id})
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                       f"{_name(state, other)} may use Stall Tactics")
