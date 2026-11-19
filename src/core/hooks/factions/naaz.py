"""The Naaz-Rokha Alliance — komplet komponentów frakcji (RULES.md 62.15).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("naaz")``, ``units``,
``breakthroughs/te_breakthroughs.json``). Rulingi: ``docs/rules_tirules/F_naaz_rokha.md``
(krzyżowo ``C_technology`` - Assault Cannon, ``C_objectives`` - Demonstrate Your Power,
``F_saar`` - Scavenge).
Punkty silnika dodane dla Naaz-Rokha: dodatkowa karta eksploracji (``exploration.extra_draw``),
siły naziemne będące statkami (``core/ship_roles``: ``combat.space_ground_variant``,
``units.ground_moves_as_ship``), odporność na trafienia ze zdolności
(``combat.ability_hit_immune``),
zakaz stawiania (``units.place_forbidden``), łańcuch secondary z żetonem z rezerwy
(``strategic_action.begin_strategize_secondary``), odwrócenie przełomu (``breakthrough.flip``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    breakthrough,
    command_tokens,
    exhaust,
    exploration,
    faction_components,
    leaders,
    relic_forge,
    relic_fragments,
    relics,
    rules_hooks,
    strategic_action,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.components import ComponentCategory
from src.core.damage import set_damaged
from src.core.faction_units import count_in_system
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import CombatStep, GameState
from src.core.hooks import card_labels
from src.core.hooks.action_cards_board import strategy_cards_in_reach
from src.core.hooks.card_helpers import system_of_planet
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_COMBAT_ABILITY_HIT_IMMUNE,
    POINT_COMBAT_EXTRA_DICE,
    POINT_COMBAT_ROLL_MODIFIER,
    POINT_COMBAT_SPACE_GROUND_VARIANT,
    POINT_EXPLORATION_EXTRA_DRAW,
    POINT_PRODUCTION_FORBIDS,
    POINT_UNIT_GROUND_MOVES_AS_SHIP,
    POINT_UNIT_PLACE_FORBIDDEN,
    SOURCE_EFFECT,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_TECHNOLOGY,
    SOURCE_UNIT,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.strategy_cards import CARDS
from src.core.unit_ops import UnitCause

FACTION = "naaz"
DISTANT_SUNS = "distant_suns"
FABRICATION = "fabrication"
PREFAB = "pfa"
SUPERCHARGE = "sc"
FLAGSHIP = "naaz_flagship"
MECH = "naaz_mech"
ZGRAV = "naaz_mech_space"
MAXIMUM = "naaz_voltron"
AGENT = "naazagent"
COMMANDER = "naazcommander"
HERO = "naazhero"
FORGERY = "bmf"
BREAKTHROUGH = "naazbt"

SUPERCHARGED = f"technologies:{SUPERCHARGE}"  # efekt rundy walki: +1 do rzutów
GARV_GRANT = f"leaders:{AGENT}:explore"  # efekt gracza, któremu agent pozwolił eksplorować
GARV_ABILITY = "garv_explore"  # FACTION_ABILITY_USED: decyzja tego gracza
_MECH = "mech"
_FLAGSHIP = "flagship"
_SPACE = "space"
_COMMANDER_SYSTEMS = 3  # „Have mechs in 3 systems.”
_SYNERGY_MECHS = 4  # „When you have 4 mechs in the same system”
_SYNERGY_RETURN = 3  # „return 3 of those mechs to your reinforcements”
_FORGE_FRAGMENTS = 2  # „purge 2 of your relic fragments of the same type to gain 1 relic”
_TOKEN_FRAGMENTS = 1  # „purge 1 of your relic fragments to gain 1 command token”
_RELIC = "relic"
_NONE = 0
_POOLS = (("tactical", "tactic pool"), ("fleet", "fleet pool"), ("strategic", "strategy pool"))


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _own_event(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


def _participant(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return player_id in (ctx.get("attacker"), ctx.get("defender"))


def _planet_option(state: GameState, registry: StaticDataRegistry, planet: str) -> dict[str, Any]:
    return oi.option(planet, card_labels.describe_planet(state, registry, planet),
                     ref=("planet", planet))


def _mechs_on(state: GameState, player_id: str, planet: str) -> int:
    try:
        system = system_of_planet(state, planet)
    except ValueError:
        return 0
    return system.planet_units.get(planet, {}).get(player_id, {}).get(_MECH, 0)


def _explorable_planets(state: GameState, player_id: str) -> list[str]:
    """Planety gracza z cechą (talia eksploracji) - na planszy."""
    registry = _registry()
    player = state.players.get(player_id)
    if player is None:
        return []
    return sorted(
        p for p in player.controlled_planets
        if exploration.explorable(registry, p) and card_labels.system_position_of_planet(state, p)
    )


def _explore(state: GameState, player_id: str, planet: str) -> None:
    position = card_labels.system_position_of_planet(state, planet)
    if position is None:
        raise ValueError(f"Planet {planet} is not on the board.")
    exploration.start_exploration(state, _registry(), player_id, position, [planet])


# ------------------------------------------------------------------------------ Distant Suns


@register(POINT_EXPLORATION_EXTRA_DRAW, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers=f"abilities:{DISTANT_SUNS}")
def distant_suns(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Distant Suns: When you explore a planet that contains 1 of your mechs: You may draw 1
    additional card; choose 1 to resolve and discard the rest (``exploration.draw(extra=True)`` +
    ``exploration.choose``; jedna dodatkowa karta przy wielu mechach - F_naaz_rokha 1)."""
    return _mechs_on(state, player_id, str(ctx.get("planet") or "")) > 0


# ------------------------------------------------------- Fabrication / Black Market Forgery


def _fragment_kind(registry: StaticDataRegistry, card_id: str) -> str | None:
    """Typ fragmentu (``cultural``...), ``"*"`` = Unknown (dowolny typ), ``None`` = nie fragment."""
    rule = relic_forge.fragment_rule(registry, card_id)
    if rule.kind is not None:
        return rule.kind
    return "*" if rule.wildcard else None


def _fragments(state: GameState, player_id: str) -> list[str]:
    registry = _registry()
    return [c for c in state.players[player_id].relic_fragments
            if _fragment_kind(registry, c) is not None]


def _fragment_options(state: GameState, registry: StaticDataRegistry, player_id: str
                      ) -> list[dict[str, Any]]:
    """Fragmenty gracza jako chipy kart (każda sztuka osobno: ``id#n``)."""
    options: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for card_id in _fragments(state, player_id):
        seen[card_id] = seen.get(card_id, 0) + 1
        card = registry.catalog.get(ComponentCategory.EXPLORATION, card_id)
        name = card.name if card is not None and card.name else card_id
        options.append(oi.option(card_id, name, f"{card_id}#{seen[card_id]}",
                                 ref=("explore", card_id)))
    return options


def _same_type_pair(registry: StaticDataRegistry, cards: list[str]) -> bool:
    """2 fragmenty tego samego typu; Unknown liczy się jako dowolny (oba Unknown też - 3)."""
    kinds = {_fragment_kind(registry, c) for c in cards}
    if None in kinds:
        return False
    return len(kinds - {"*"}) <= 1


def _picked_fragments(state: GameState, player_id: str, params: Mapping[str, Any]) -> list[str]:
    picked = [str(c) for c in params.get("fragments") or []]
    owned = list(state.players[player_id].relic_fragments)
    for card_id in picked:
        if card_id not in owned:
            raise ValueError("Choose your own relic fragments.")
        owned.remove(card_id)
    return picked


def _forge_relic(state: GameState, registry: StaticDataRegistry, player_id: str,
                 cards: list[str], source: str) -> str | None:
    """Purge 2 fragmentów tego samego typu i 1 relikt (pusta talia - bez reliktu)."""
    if len(cards) != _FORGE_FRAGMENTS or not _same_type_pair(registry, cards):
        raise ValueError("Purge 2 relic fragments of the same type (Unknown counts as any type).")
    relic_fragments.purge_chosen(state, player_id, cards)
    return relics.draw_relic(state, registry, player_id, source=source,
                             detail={"fragments": list(cards)})


def _relic_deck_empty(state: GameState, registry: StaticDataRegistry) -> bool:
    probe = state.clone()  # talia powstaje leniwie - sprawdzamy na kopii
    relics.ensure_relic_deck(probe, registry)
    return not probe.decks.relic_deck and not probe.decks.relic_discard


@faction_components.blocker("ability", FABRICATION)
def _fabrication_blocker(state: GameState, _registry_: StaticDataRegistry, player_id: str
                         ) -> str | None:
    if not _fragments(state, player_id):
        return "You have no relic fragments."
    return None


@register_effect_inputs(f"abilities:{FABRICATION}")
def fabrication_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    modes = [
        oi.option(_RELIC, "Purge 2 relic fragments of the same type: gain 1 relic"),
        *(oi.option(pool, f"Purge 1 relic fragment: gain 1 command token ({label})")
          for pool, label in _POOLS),
    ]
    options = _fragment_options(state, registry, player_id)
    return [
        oi.choice("mode", "Fabrication", modes, always=True),
        oi.multi("fragments", "Relic fragments to purge", options, 1, min(2, len(options)),
                 hint="Unknown Relic Fragments count as any type."),
    ]


@register_effect(f"abilities:{FABRICATION}")
def fabrication(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Fabrication: ACTION: Either purge 2 of your relic fragments of the same type to gain 1
    relic; or purge 1 of your relic fragments to gain 1 command token.

    Pusta talia reliktów: purge bez reliktu (F_naaz_rokha 1); pusta rezerwa: bez żetonu (2)."""
    mode = str(params.get("mode") or "")
    cards = _picked_fragments(state, player_id, params)
    if mode == _RELIC:
        relic = _forge_relic(state, registry, player_id, cards, "fabrication")
        ability_notes.note(state, player_id, f"abilities:{FABRICATION}",
                           "gained a relic" if relic else "relic deck empty - no relic")
        return
    if mode not in {pool for pool, _ in _POOLS}:
        raise ValueError("Choose what Fabrication does.")
    if len(cards) != _TOKEN_FRAGMENTS:
        raise ValueError("Purge exactly 1 relic fragment to gain 1 command token.")
    relic_fragments.purge_chosen(state, player_id, cards)
    if state.players[player_id].cc_reinf >= 1:
        command_tokens.gain_from_reinforcements(state, player_id, {mode: 1})
        ability_notes.note(state, player_id, f"abilities:{FABRICATION}",
                           f"gained 1 command token ({mode})")
    else:
        ability_notes.note(state, player_id, f"abilities:{FABRICATION}",
                           "no command token in reinforcements - none gained")


def _forgery_owner(state: GameState, registry: StaticDataRegistry) -> str | None:
    from src.core import promissory_play  # lokalnie: promissory_play importuje hooki

    return promissory_play.resolve(state, registry, FORGERY)[1]


def _forgery_blocker(state: GameState, registry: StaticDataRegistry, player_id: str
                     ) -> str | None:
    if _relic_deck_empty(state, registry):
        return "The relic deck is empty - you cannot gain a relic."
    registry_ = _registry()
    frags = _fragments(state, player_id)
    if not any(_same_type_pair(registry_, [a, b])
               for i, a in enumerate(frags) for b in frags[i + 1:]):
        return "You need 2 relic fragments of the same type (Unknown counts as any type)."
    return None


def _register_forgery_blocker() -> None:
    from src.core import promissory_play  # lokalnie: promissory_play importuje hooki

    promissory_play.action_blocker(FORGERY)(_forgery_blocker)


_register_forgery_blocker()


@register_effect_inputs(f"promissory_notes:{FORGERY}")
def forgery_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = _fragment_options(state, registry, player_id)
    return [oi.multi("fragments", "2 relic fragments of the same type", options,
                     _FORGE_FRAGMENTS, _FORGE_FRAGMENTS,
                     hint="Unknown Relic Fragments count as any type.")]


@register_effect(f"promissory_notes:{FORGERY}")
def black_market_forgery(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Black Market Forgery: ACTION: Purge 2 of your relic fragments of the same type to gain 1
    relic. Then, return this card to the Naaz-Rokha player (zwrot - ``promissory_play``)."""
    cards = _picked_fragments(state, player_id, params)
    _forge_relic(state, registry, player_id, cards, "black_market_forgery")


# ------------------------------------------------------------------- Pre-Fab Arcologies


def _explored_own(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("player") == player_id
        and str(ctx.get("planet") or "") in state.players[player_id].controlled_planets
    )


@on_event(GameEvent.PLANET_EXPLORED, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, PREFAB),
          condition=_explored_own, covers=f"technologies:{PREFAB}", label="Pre-Fab Arcologies")
def prefab_arcologies(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Pre-Fab Arcologies: After you explore a planet, ready that planet (po produkcji
    Freelancers - ``exploration.after_grant``, F_naaz_rokha 1)."""
    planet = str(ctx.get("planet"))
    if planet in state.players[player_id].exhausted_planets:
        exhaust.ready_planets(state, player_id, [planet])
        ability_notes.note(state, player_id, f"technologies:{PREFAB}", f"readied {planet}")


# --------------------------------------------------------------------------- Supercharge


def _supercharge_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        _participant(state, player_id, ctx)
        and SUPERCHARGE not in state.players[player_id].exhausted_technologies
        and not active_effects.has_effect(state, player_id, SUPERCHARGED)
    )


@on_event(GameEvent.COMBAT_ROUND, Moment.START, HookSource(SOURCE_TECHNOLOGY, SUPERCHARGE),
          optional=True, condition=_supercharge_ready, covers=f"technologies:{SUPERCHARGE}",
          label="Supercharge: +1 to combat rolls this round")
def supercharge(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Supercharge: At the start of a combat round, you may exhaust this card to apply +1 to the
    result of each of your unit's combat rolls during this combat round."""
    exhaust.exhaust_technology(state, player_id, SUPERCHARGE)
    active_effects.add_effect(state, SUPERCHARGED, Duration.COMBAT_ROUND, owner=player_id)


@register(POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_EFFECT, SUPERCHARGED), HookKind.MODIFY)
def supercharged(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """+1 tylko do rzutów walki - AFB, bombardowanie i Space Cannon mają własne punkty (1)."""
    return 1


# ------------------------------------------------------------------------- Visz El Vir


@register(POINT_COMBAT_EXTRA_DICE, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.MODIFY,
          covers=f"units:{FLAGSHIP}")
def visz_el_vir(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Visz El Vir: Your mechs in this system roll 1 additional die during combat (każdy mech,
    także Z-Grav Eidolon i Eidolon Maximum - F_naaz_rokha 1, 2)."""
    if ctx.get("base_type") != _MECH:
        return 0
    system = state.systems.get(str(ctx.get("position") or ""))
    has_flagship = system is not None and system.space_units.get(player_id, {}).get(
        _FLAGSHIP, 0) > 0
    return 1 if has_flagship else 0


# ------------------------------------------------------------- Eidolon / Z-Grav Eidolon


def _space_combat_here(state: GameState, ctx: Mapping[str, Any]) -> bool:
    """Trwająca walka kosmiczna w AKTYWNYM systemie ``ctx["position"]`` (eidolon 1); z
    ``finished_combat`` także właśnie zakończona (cele na koniec walki - eidolon 5)."""
    combat = state.active_combat
    position = str(ctx.get("position") or "")
    return (
        combat is not None
        and combat.kind == _SPACE
        and combat.position == position
        and state.active_system == position
        and (combat.step is not CombatStep.DONE or bool(ctx.get("finished_combat")))
    )


@register(POINT_COMBAT_SPACE_GROUND_VARIANT, HookSource(SOURCE_UNIT, MECH), HookKind.FORBID,
          covers=f"units:{ZGRAV}")
def zgrav_eidolon(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> list[str]:
    """Z-Grav Eidolon: If this unit is in the space area of the active system, it is also a ship
    (tylko w kroku walki kosmicznej - F_naaz_rokha eidolon 1; ``core/ship_roles``)."""
    return [ZGRAV] if _space_combat_here(state, ctx) else []


def _mechs_in_space(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    system = state.systems.get(str(ctx.get("position") or ""))
    return (
        ctx.get("kind") == _SPACE
        and system is not None
        and system.space_units.get(player_id, {}).get(_MECH, 0) > 0
        and state.active_system == system.position
    )


@on_event(GameEvent.COMBAT, Moment.START, HookSource(SOURCE_UNIT, MECH),
          condition=_mechs_in_space, covers=f"units:{MECH}", label="Eidolon: flip")
def eidolon_flip(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Eidolon: If this unit is in the space area of the active system at the start of a space
    combat, flip this card (obowiązkowo - eidolon 2; stan liczy ``ship_roles``)."""
    ability_notes.note(state, player_id, f"units:{MECH}",
                       f"Z-Grav Eidolon in system {ctx.get('position')}")


@on_event(GameEvent.COMBAT, Moment.END, HookSource(SOURCE_UNIT, MECH),
          condition=_mechs_in_space, covers=f"units:{ZGRAV}", label="Z-Grav Eidolon: flip")
def zgrav_flip_back(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Z-Grav Eidolon: At the end of a space battle in the active system, flip this card (mechy
    wracają do pojemności - sprawdzenie po walce, eidolon 6)."""
    ability_notes.note(state, player_id, f"units:{ZGRAV}",
                       f"Eidolon again in system {ctx.get('position')}")


# ------------------------------------------------------------- Garv and Gunn (agent)


def _garv_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    target = str(ctx.get("player") or "")
    return (
        target in state.players
        and leaders.is_ready(state, _registry(), player_id, AGENT)
        and bool(_explorable_planets(state, target))
    )


@on_event(GameEvent.TURN, Moment.END, HookSource(SOURCE_LEADER, AGENT), optional=True,
          condition=_garv_ready, covers=f"leaders:{AGENT}",
          label="Garv and Gunn: let that player explore")
def garv_and_gunn(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Garv and Gunn: At the end of a player's turn: You may exhaust this card to allow that player
    to explore 1 of their planets (planetę wybiera ten gracz albo rezygnuje - RULES.md 62.15)."""
    target = str(ctx.get("player"))
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT,
                                {"target": target})
    active_effects.add_effect(state, GARV_GRANT, Duration.ROUND, owner=target,
                              data={"by": player_id})
    faction_components.ability_used(state, player_id, GARV_ABILITY, target)


def _garv_granted(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("target") == player_id and bool(_explorable_planets(state, player_id))


def garv_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [oi.choice("planet", "Planet to explore", [
        _planet_option(state, registry, p) for p in _explorable_planets(state, player_id)
    ], always=True)]


@on_event(GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_EFFECT, GARV_GRANT),
          where={"ability": GARV_ABILITY}, optional=True, condition=_garv_granted,
          inputs=garv_inputs, label="Garv and Gunn: explore 1 of your planets")
def garv_explore(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Gracz, któremu Garv and Gunn pozwolili, eksploruje 1 swoją planetę z cechą."""
    planet = str((ctx.get("params") or {}).get("planet") or "")
    if planet not in _explorable_planets(state, player_id):
        raise ValueError("Choose 1 of your planets that can be explored.")
    active_effects.remove_by_key(state, GARV_GRANT, owner=player_id)
    _explore(state, player_id, planet)


# --------------------------------------------------------------- Dart and Tai (commander)


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have mechs in 3 systems."""
    return sum(
        1 for system in state.systems.values() if count_in_system(system, player_id, _MECH) > 0
    ) >= _COMMANDER_SYSTEMS


def _taken_from_player(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    previous = ctx.get("previous")
    return (
        ctx.get("player") == player_id
        and previous is not None
        and previous != player_id
        and previous in state.players
        and exploration.explorable(_registry(), str(ctx.get("planet")))
    )


@on_event(GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
          optional=True, condition=_taken_from_player, covers=f"leaders:{COMMANDER}",
          label="Dart and Tai: explore that planet")
def dart_and_tai(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dart and Tai: After you gain control of a planet that was controlled by another player: You
    may explore that planet."""
    planet = str(ctx.get("planet"))
    position = str(ctx.get("position") or "") or card_labels.system_position_of_planet(
        state, planet) or ""
    exploration.start_exploration(state, _registry(), player_id, position, [planet])


# -------------------------------------------------- Hesh and Prit — Perfect Synthesis (hero)


def _card_options(state: GameState, registry: StaticDataRegistry) -> list[dict[str, Any]]:
    return [
        oi.option(i, card_labels.describe_strategy_card(registry, i), str(i),
                  ref=("strategy", i))
        for i in strategy_cards_in_reach(state, registry)
    ]


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, _player_id: str
) -> list[dict[str, Any]]:
    """Obie karty wybrane z góry (F_naaz_rokha hesh 2), w kolejności rozstrzygania (3)."""
    cards = _card_options(state, registry)
    skip = oi.option(_NONE, "None", "none")
    return [
        oi.choice("first", "First secondary ability", [*cards, skip], always=True),
        oi.choice("second", "Second secondary ability", [*cards, skip], always=True),
    ]


@register_effect(f"leaders:{HERO}")
def perfect_synthesis(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Hesh and Prit — Perfect Synthesis: ACTION: Gain 1 relic and perform the secondary ability of
    up to 2 readied or unchosen strategy cards. during this action, spend command tokens from your
    reinforcements instead of your strategy pool. Then, purge this card (purge -
    ``faction_components``).

    0-2 różne karty (1, 1.1), wybrane przed rozstrzyganiem (2); okna secondary po kolei (3)."""
    reach = set(strategy_cards_in_reach(state, registry))
    chosen: list[int] = []
    for key in ("first", "second"):
        value = int(params.get(key) or _NONE)
        if value == _NONE:
            continue
        if value not in reach or value not in CARDS:
            raise ValueError("Choose readied or unchosen strategy cards.")
        if value in chosen:
            raise ValueError("You cannot choose the same strategy card twice.")
        chosen.append(value)
    relics.draw_relic(state, registry, player_id, source="perfect_synthesis")
    if chosen:
        strategic_action.begin_strategize_secondary(
            state, player_id, chosen[0], then=chosen[1:], from_reinforcements=True
        )
    ability_notes.note(state, player_id, f"leaders:{HERO}",
                       f"secondary of {len(chosen)} strategy card(s)")


# ----------------------------------------------------------- Absolute Synergy (przełom)


def synergy_systems(state: GameState, player_id: str) -> list[str]:
    """Systemy z 4 mechami gracza (gdziekolwiek w systemie - F_naaz_rokha absolute-synergy 1)."""
    return sorted(
        position for position, system in state.systems.items()
        if count_in_system(system, player_id, _MECH) >= _SYNERGY_MECHS
    )


def _mech_places(state: GameState, player_id: str, position: str) -> list[str]:
    system = state.systems[position]
    zones = [_SPACE, *sorted(system.planet_units)]
    return [z for z in zones if unit_ops.count_in_zone(system, z, player_id, _MECH) > 0]


@faction_components.window_use("breakthrough", BREAKTHROUGH, standing=True)
def _synergy_window(state: GameState, _registry_: StaticDataRegistry, player_id: str
                    ) -> str | None:
    if state.players[player_id].breakthrough_flipped:
        return "Your breakthrough is already flipped."
    if not synergy_systems(state, player_id):
        return "You need 4 mechs in the same system."
    return None


@register_effect_inputs(f"breakthroughs:{BREAKTHROUGH}")
def synergy_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Mech, który zostaje (wybór na mapie); 3 pozostałe z tego systemu wracają do rezerwy."""
    options = [
        oi.option(f"{pos}|{zone}", unit_name(state, registry, player_id, _MECH),
                  meta=oi.unit_at(state, player_id, _MECH, position=pos,
                                  planet=None if zone == _SPACE else zone))
        for pos in synergy_systems(state, player_id)
        for zone in _mech_places(state, player_id, pos)
    ]
    return [oi.choice("keep", "Mech that becomes the Eidolon Maximum", options, always=True)]


@register_effect(f"breakthroughs:{BREAKTHROUGH}")
def absolute_synergy(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Absolute Synergy: When you have 4 mechs in the same system, you may return 3 of those mechs
    to your reinforcements to flip this card and place it on top of your mech card (w dowolnej
    chwili - także przed walką, F_naaz_rokha absolute-synergy 2)."""
    position, _, keep_zone = str(params.get("keep") or "").partition("|")
    if position not in synergy_systems(state, player_id) or keep_zone not in _mech_places(
        state, player_id, position
    ):
        raise ValueError("Choose 1 of your mechs in a system that contains 4 of your mechs.")
    system = state.systems[position]
    left = _SYNERGY_RETURN
    zones = [z for z in _mech_places(state, player_id, position) if z != keep_zone]
    for zone in [*zones, keep_zone]:  # zostaje mech we wskazanym miejscu
        here = unit_ops.count_in_zone(system, zone, player_id, _MECH)
        take = min(left, here - (1 if zone == keep_zone else 0))
        if take > 0:
            unit_ops.remove_units(state, system, zone, player_id, _MECH, take, UnitCause.REMOVED)
            left -= take
    breakthrough.flip(state, player_id)
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                       f"Eidolon Maximum in system {position}")


# ------------------------------------------------------------------- Eidolon Maximum


@register(POINT_COMBAT_SPACE_GROUND_VARIANT, HookSource(SOURCE_UNIT, MAXIMUM), HookKind.FORBID,
          covers=f"breakthroughs:{BREAKTHROUGH}")
def maximum_is_ship(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> list[str]:
    """Eidolon Maximum: This unit is both a ship and ground force (w przestrzeni - statek)."""
    return [MAXIMUM]


@register(POINT_UNIT_GROUND_MOVES_AS_SHIP, HookSource(SOURCE_UNIT, MAXIMUM), HookKind.PERMIT)
def maximum_moves(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Statek: rusza się sam (Move 3), liczy się do puli floty (eidolon-maximum 1)."""
    return ctx.get("base_type") == _MECH


@register(POINT_COMBAT_ABILITY_HIT_IMMUNE, HookSource(SOURCE_UNIT, MAXIMUM), HookKind.FORBID)
def maximum_immune(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> list[str]:
    """It cannot be assigned hits from unit abilities (trafienia na inne jednostki - 2)."""
    return [_MECH]


@register(POINT_PRODUCTION_FORBIDS, HookSource(SOURCE_UNIT, MAXIMUM), HookKind.FORBID)
def maximum_no_production(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]
                          ) -> list[str]:
    """Game effects cannot place or produce your mechs."""
    return [_MECH]


@register(POINT_UNIT_PLACE_FORBIDDEN, HookSource(SOURCE_UNIT, MAXIMUM), HookKind.FORBID)
def maximum_no_placing(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> list[str]:
    """Game effects cannot place or produce your mechs (nigdy dwa Eidolon Maximum - 4)."""
    return [_MECH]


def _combat_zone(ctx: Mapping[str, Any]) -> str:
    return _SPACE if ctx.get("kind") == _SPACE else str(ctx.get("planet") or "")


def _maximum_fights(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Eidolon Maximum walczy w tej walce (naprawa tylko wtedy - eidolon-maximum 3)."""
    system = state.systems.get(str(ctx.get("position") or ""))
    return _participant(state, player_id, ctx) and system is not None and unit_ops.count_in_zone(
        system, _combat_zone(ctx), player_id, _MECH) > 0


@on_event(GameEvent.COMBAT_ROUND, Moment.START, HookSource(SOURCE_UNIT, MAXIMUM),
          condition=_maximum_fights, label="Eidolon Maximum: repair")
def maximum_repair(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Repair it at the start of every combat round."""
    system = state.systems[str(ctx.get("position"))]
    set_damaged(system, _combat_zone(ctx), player_id, _MECH, 0)


def _maximum_gone(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("player") == player_id
        and ctx.get("base_type") == _MECH
        and state.players[player_id].breakthrough_flipped
    )


def _flip_back(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """When this unit is destroyed or removed, flip this card and return it to your play area."""
    breakthrough.flip_back(state, player_id)
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                       "Eidolon Maximum gone - card returned to the play area")


for _event in (GameEvent.UNIT_DESTROYED, GameEvent.UNIT_REMOVED):
    on_event(_event, Moment.AFTER, HookSource(SOURCE_UNIT, MAXIMUM), condition=_maximum_gone,
             label="Eidolon Maximum: flip back")(_flip_back)
