"""The Embers of Muaat — komplet komponentów frakcji (RULES.md 62.13).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("muaat")``, ``units``,
``breakthroughs/te_breakthroughs.json``, ``planets/avernus``). Rulingi: ``docs/rules_tirules/
F_muaat.md`` (krzyżowo ``C_relics`` - Scepter, ``C_objectives`` - kilka żetonów naraz,
``R_space_combat`` - odwrót do supernowej, ``C_units`` - war sun Muaat, ``F_norr`` - G'hom Sek'kus).
Punkty silnika dodane dla Muaat: przelot przez supernowe (``movement.through_supernova``), wejście
do supernowej (``movement.into_supernova``), PRODUCTION systemu (``production.system_value``),
eliminacja (``elimination.has_production``), akcja jednostki (``faction_components.UNIT``),
wymiana kafla (``core/tile_swap``), emisja ``STRATEGY_TOKEN_SPENT`` w ``spend_strategy_token``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    board_graph,
    command_tokens,
    control,
    cooperative,
    economy,
    exhaust,
    exploration,
    faction_components,
    fracture,
    leaders,
    promissory_play,
    rules_hooks,
    technology,
    tile_swap,
    triggers,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.custodians import is_mecatol_position
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, ProductionGrant
from src.core.hex_grid import HexGrid
from src.core.hooks import card_labels
from src.core.hooks.card_helpers import place_from_reinforcements
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_ELIMINATION_HAS_PRODUCTION,
    POINT_MOVEMENT_INTO_SUPERNOVA,
    POINT_MOVEMENT_THROUGH_SUPERNOVA,
    POINT_PRODUCTION_SYSTEM_VALUE,
    SOURCE_BREAKTHROUGH,
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
from src.core.state_grid import grid_from_state
from src.core.unit_ops import UnitCause

FACTION = "muaat"
STAR_FORGE = "star_forge"
GASHLAI = "gashlai_physiology"
PROTOTYPE_WAR_SUN = "pws2"
MAGMUS_REACTOR = "mr"
AGENT = "muaatagent"
COMMANDER = "muaatcommander"
HERO = "muaathero"
FLAGSHIP = "muaat_flagship"
MECH = "muaat_mech"
FIRES = "fires"
BREAKTHROUGH = "muaatbt"
AVERNUS = "avernus"

STAR_FORGE_KEY = f"abilities:{STAR_FORGE}"  # ``FACTION_ABILITY_USED`` (ctx ``ability``)
UMBAT_PRODUCE = "umbat_produce"  # decyzja wybranego gracza po wyczerpaniu Umbata
NOVA_SEED_TILE = "81"  # kafel „Nova Seed” (assets/systems/81.json: supernowa Muaat)
WAR_SUN_TECH = "ws"  # ogólne ulepszenie war suna (Fires of the Gashlai: „your war sun ... card”)
_FORGE_FIGHTERS = 2  # „either 2 fighters or 1 destroyer”
_UMBAT_UNITS = 2  # „up to 2 units”
_UMBAT_MAX_COST = 4.0  # „that each have a cost of 4 or less”
_WARSUN = "warsun"
_SUPERNOVA = "SUPERNOVA"
_SPACE = "space"
_NONE = "none"
_FIGHTERS = "fighters"
_DESTROYER = "destroyer"
_PRODUCTION_VALUE = re.compile(r"PRODUCTION\s+(\d+)")


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _grid(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    """Siatka mapy gry (podpięta przez API - wszystkie kafle, hyperlane, wormhole); bez niej
    (testy jednostkowe) - siatka z systemów stanu. ``grid_from_state`` widzi TYLKO systemy z
    wpisem stanu, więc systemy z planetami bez jednostek by znikały."""
    return board_graph.bound_grid() or grid_from_state(state, registry)


def _own_event(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


def war_sun_positions(state: GameState, player_id: str) -> list[str]:
    """Systemy z war sunem gracza (w przestrzeni)."""
    return sorted(
        position for position, system in state.systems.items()
        if system.space_units.get(player_id, {}).get(_WARSUN, 0) > 0
    )


def _system_option(state: GameState, registry: StaticDataRegistry, position: str) -> dict[str, Any]:
    return oi.option(position, card_labels.describe_system(state, registry, position))


def _is_supernova(state: GameState, registry: StaticDataRegistry, position: str) -> bool:
    system = state.systems.get(position)
    definition = registry.systems.get(system.system_id) if system is not None else None
    return definition is not None and _SUPERNOVA in definition.anomalies


def _has_units(state: GameState, player_id: str, position: str) -> bool:
    system = state.systems.get(position)
    if system is None:
        return False
    if any(n > 0 for n in system.space_units.get(player_id, {}).values()):
        return True
    return any(
        n > 0 for by in system.planet_units.values() for n in by.get(player_id, {}).values()
    )


def _home_positions(state: GameState, registry: StaticDataRegistry) -> set[str]:
    """Systemy domowe graczy przy stole i wyeliminowanych (F_muaat Nova Seed 6)."""
    homes = board_graph.home_positions(state, registry)
    homes |= {e.home_position for e in state.eliminated_players if e.home_position}
    return homes


# ------------------------------------------------------------------------------ Star Forge


def forge_unit_options(state: GameState, player_id: str) -> list[dict[str, Any]]:
    """2 myśliwce albo 1 niszczyciel - tylko to, co jest w rezerwie."""
    units: list[dict[str, Any]] = []
    fighters = reinforcements_left(state, player_id, "fighter")  # None = żetony zastępcze
    if fighters is None or fighters >= _FORGE_FIGHTERS:
        units.append(oi.option(_FIGHTERS, f"Place {_FORGE_FIGHTERS} fighters"))
    if reinforcements_left(state, player_id, _DESTROYER) != 0:
        units.append(oi.option(_DESTROYER, "Place 1 destroyer"))
    return units


def forge_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """System z war sunem (mapa) + co postawić. Wspólne ze zdolnością The Nucleus (Avernus)."""
    return [
        oi.choice("position", "System that contains one of your war suns", [
            _system_option(state, registry, pos) for pos in war_sun_positions(state, player_id)
        ]),
        oi.choice("unit", "Units to place", forge_unit_options(state, player_id)),
    ]


def resolve_star_forge(
    state: GameState, player_id: str, params: Mapping[str, Any], *, source: str
) -> None:
    """Skutek Star Forge (MUTUJE): jednostki w systemie z war sunem, potem
    ``FACTION_ABILITY_USED/AFTER`` (mech Ember Colossus). ``source`` = ``abilities:star_forge``
    albo ``planets:avernus`` (The Nucleus - to też Star Forge, F_muaat Avernus 2)."""
    position = str(params.get("position") or "")
    unit = str(params.get("unit") or "")
    if position not in war_sun_positions(state, player_id):
        raise ValueError("Choose a system that contains one of your war suns ('position').")
    system = state.systems[position]
    if unit == _FIGHTERS:
        place_from_reinforcements(state, system, _SPACE, player_id, "fighter", _FORGE_FIGHTERS)
    elif unit == _DESTROYER:
        place_from_reinforcements(state, system, _SPACE, player_id, _DESTROYER, 1)
    else:
        raise ValueError("Choose 2 fighters or 1 destroyer ('unit').")
    triggers.fire(
        state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "ability": STAR_FORGE_KEY, "position": position,
             "source": source},
    )


@faction_components.blocker("ability", STAR_FORGE)
def _forge_blocker(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> str | None:
    if not war_sun_positions(state, player_id):  # F_muaat star-forge 1
        return "You need a war sun on the game board to use Star Forge."
    if not command_tokens.can_spend_strategy_token(state, player_id):
        return "Star Forge needs 1 command token in your strategy pool."
    if not forge_unit_options(state, player_id):
        return "You have no 2 fighters or 1 destroyer in your reinforcements."
    return None


@register_effect_inputs(STAR_FORGE_KEY)
def star_forge_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    return [
        *forge_inputs(state, registry, player_id),
        *command_tokens.strategy_token_input(state, player_id),  # Scepter of Emelpar
    ]


@register_effect(STAR_FORGE_KEY)
def star_forge(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Star Forge: ACTION: Spend 1 token from your strategy pool to place either 2 fighters or 1
    destroyer from your reinforcements in a system that contains 1 or more of your war suns."""
    command_tokens.spend_strategy_token(state, player_id, source=params.get("token_source"))
    resolve_star_forge(state, player_id, params, source=STAR_FORGE_KEY)


# ---------------------------------------------------------------------- Gashlai Physiology


@register(POINT_MOVEMENT_THROUGH_SUPERNOVA, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers=f"abilities:{GASHLAI}")
def gashlai_physiology(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Gashlai Physiology: Your ships can move through supernovas (węzeł pośredni trasy)."""
    return True


# ------------------------------------------------------------------- Magmus Reactor (tech)


@register(POINT_MOVEMENT_INTO_SUPERNOVA, HookSource(SOURCE_TECHNOLOGY, MAGMUS_REACTOR),
          HookKind.PERMIT, covers=f"technologies:{MAGMUS_REACTOR}")
def magmus_reactor_move(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Magmus Reactor: Your ships can move into supernovas (cel ruchu i odwrót - R_space_combat)."""
    return True


def _reactor_value(registry: StaticDataRegistry) -> int:
    """Wartość PRODUCTION supernowej z tekstu karty („gains the PRODUCTION 5 ability”)."""
    tech = registry.technologies.get(MAGMUS_REACTOR)
    found = _PRODUCTION_VALUE.search(tech.text or "") if tech is not None else None
    return int(found.group(1)) if found else 0


@register(POINT_PRODUCTION_SYSTEM_VALUE, HookSource(SOURCE_TECHNOLOGY, MAGMUS_REACTOR),
          HookKind.MODIFY, covers=f"technologies:{MAGMUS_REACTOR}")
def magmus_reactor_production(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Each supernova that contains 1 or more of your units gains the PRODUCTION 5 ability as if
    it were 1 of your units."""
    registry = _registry()
    position = str(ctx.get("position") or "")
    if not _is_supernova(state, registry, position) or not _has_units(state, player_id, position):
        return 0
    return _reactor_value(registry)


@register(POINT_ELIMINATION_HAS_PRODUCTION, HookSource(SOURCE_TECHNOLOGY, MAGMUS_REACTOR),
          HookKind.PERMIT, covers=f"technologies:{MAGMUS_REACTOR}")
def magmus_reactor_survives(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """F_muaat Magmus Reactor Ω 1: jednostka w supernowej = PRODUCTION, gracz nie odpada."""
    registry = _registry()
    return any(
        _is_supernova(state, registry, pos) and _has_units(state, player_id, pos)
        for pos in state.systems
    )


# Prototype War Sun I/II: liczby i „lose PLANETARY SHIELD” z danych (``disablesPlanetaryShield`` -
# ``invasion._attacker_ignores_shield``, jak war sun ogólny); war sun Muaat bez technologii.
rules_hooks.declare_data_driven(f"technologies:{PROTOTYPE_WAR_SUN}")
rules_hooks.declare_data_driven("units:muaat_warsun")
rules_hooks.declare_data_driven("units:muaat_warsun2")


# ------------------------------------------------------------------ The Inferno (flagowiec)


def _flagship_position(state: GameState, player_id: str) -> str | None:
    return next(
        (pos for pos, system in sorted(state.systems.items())
         if system.space_units.get(player_id, {}).get("flagship", 0) > 0),
        None,
    )


@faction_components.blocker("unit", FLAGSHIP)
def _inferno_blocker(
    state: GameState, _registry_: StaticDataRegistry, player_id: str
) -> str | None:
    if _flagship_position(state, player_id) is None:
        return "The Inferno is not on the game board."
    if not command_tokens.can_spend_strategy_token(state, player_id):
        return "The Inferno needs 1 command token in your strategy pool."
    if reinforcements_left(state, player_id, "cruiser") == 0:
        return "You have no cruiser in your reinforcements."
    return None


@register_effect_inputs(f"units:{FLAGSHIP}")
def inferno_inputs(
    state: GameState, _registry_: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    return command_tokens.strategy_token_input(state, player_id)


@register_effect(f"units:{FLAGSHIP}")
def the_inferno(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """The Inferno: ACTION: Spend 1 token from your strategy pool to place 1 cruiser in this
    system."""
    position = _flagship_position(state, player_id)
    if position is None:
        raise ValueError("The Inferno is not on the game board.")
    command_tokens.spend_strategy_token(state, player_id, source=params.get("token_source"))
    place_from_reinforcements(state, state.systems[position], _SPACE, player_id, "cruiser", 1)


# ------------------------------------------------------------------ Ember Colossus (mech)


def _colossi(state: GameState, player_id: str, position: str) -> list[tuple[str, str, int]]:
    """``(pozycja, strefa, sztuki)`` mechów gracza w systemie Star Forge albo sąsiednim."""
    grid = _grid(state, _registry())
    found: list[tuple[str, str, int]] = []
    for pos, system in sorted(state.systems.items()):
        if pos != position and not grid.are_adjacent(pos, position):
            continue
        if (n := system.space_units.get(player_id, {}).get("mech", 0)) > 0:
            found.append((pos, _SPACE, n))
        for planet, by in sorted(system.planet_units.items()):
            if (n := by.get(player_id, {}).get("mech", 0)) > 0:
                found.append((pos, planet, n))
    return found


def _colossus_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("player") == player_id
        and reinforcements_left(state, player_id, "infantry") != 0
        and bool(_colossi(state, player_id, str(ctx.get("position") or "")))
    )


def colossus_inputs(
    state: GameState, _registry_: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Mechy na mapie (każdy mech = osobna sztuka, licznik −/+ przy kilku w jednym miejscu)."""
    options = [
        oi.option(f"{pos}|{zone}|{i}", f"{zone} #{i + 1}", meta=oi.unit_at(
            state, player_id, "mech", position=pos, planet=None if zone == _SPACE else zone))
        for pos, zone, n in _colossi(state, player_id, str(ctx.get("position") or ""))
        for i in range(n)
    ]
    left = reinforcements_left(state, player_id, "infantry")
    most = len(options) if left is None else min(left, len(options))
    return [oi.multi("mechs", "Place 1 infantry with each chosen mech", options, 1, most)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_UNIT, MECH),
    where={"ability": STAR_FORGE_KEY}, optional=True, condition=_colossus_ready,
    inputs=colossus_inputs, covers=f"units:{MECH}", label="Ember Colossus: place infantry",
)
def ember_colossus(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Ember Colossus: When you use your Star Forge faction ability in this system or an adjacent
    system, you may place 1 infantry from your reinforcements with this unit (także przy The
    Nucleus - F_muaat Avernus 2)."""
    picks = [str(v) for v in (ctx.get("params") or {}).get("mechs") or []]
    live = {(pos, zone): n for pos, zone, n in _colossi(state, player_id, str(ctx["position"]))}
    used: dict[tuple[str, str], int] = {}
    for pick in picks:
        pos, zone, _ = pick.split("|", 2)
        used[(pos, zone)] = used.get((pos, zone), 0) + 1
        if used[(pos, zone)] > live.get((pos, zone), 0):
            raise ValueError("Choose your mechs in the Star Forge system or an adjacent system.")
    for (pos, zone), count in sorted(used.items()):
        place_from_reinforcements(state, state.systems[pos], zone, player_id, "infantry", count)
    ability_notes.note(state, player_id, f"units:{MECH}", f"placed {len(picks)} infantry")


# ------------------------------------------------------------------------------ Umbat (agent)


def _umbat_systems(state: GameState, player_id: str) -> list[str]:
    """Systemy z war sunem albo flagowcem gracza."""
    return sorted(
        pos for pos, system in state.systems.items()
        if any(system.space_units.get(player_id, {}).get(bt, 0) > 0 for bt in (_WARSUN, "flagship"))
    )


def _umbat_helps(state: GameState, owner: str) -> list[str]:
    return [pid for pid in sorted(state.players) if pid != owner and _umbat_systems(state, pid)]


# Cooperative agent (RULES.md 54.15): a player with a war sun / flagship may ask / pay for the
# production. ACTION: requested only during the Muaat's turn; uses the Muaat's component action.
cooperative.register_pull_component("leader", AGENT, _umbat_helps, mutual=True, target="player")


@register_effect_inputs(f"leaders:{AGENT}")
def umbat_inputs(
    state: GameState, registry: StaticDataRegistry, _player_id: str
) -> list[dict[str, Any]]:
    options = [
        oi.option(pid, card_labels.describe_player(state, registry, pid))
        for pid in sorted(state.players) if _umbat_systems(state, pid)
    ]
    return [oi.choice("player", "Player who may produce 2 units", options)]


@faction_components.blocker("leader", AGENT)
def _umbat_blocker(state: GameState, _registry_: StaticDataRegistry, _player_id: str) -> str | None:
    if state.production_grant is not None:
        return "Another production is still open - finish it first."
    if not any(_umbat_systems(state, pid) for pid in state.players):
        return "No player has a war sun or flagship on the game board."
    return None


@register_effect(f"leaders:{AGENT}")
def umbat(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Umbat: ACTION: Exhaust this card to choose a player: that player may produce up to 2 units
    that each have a cost of 4 or less in a system that contains one of their war suns or their
    flagship (koszt - wyczerpanie - płaci ``faction_components``; decyzja wybranego gracza)."""
    target = str(params.get("player") or "")
    if target not in state.players or not _umbat_systems(state, target):
        raise ValueError("Choose a player with a war sun or flagship on the game board.")
    faction_components.ability_used(state, player_id, UMBAT_PRODUCE, target)


def _target_decides(_state: GameState, _owner: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def umbat_system_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options = [_system_option(state, registry, pos) for pos in _umbat_systems(state, decider)]
    options.append(oi.option(_NONE, "Do not produce"))
    return [oi.choice("position", "System with your war sun or flagship", options)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    where={"ability": UMBAT_PRODUCE}, decide=True, decider=_target_decides,
    inputs=umbat_system_inputs, label="Umbat: produce up to 2 units",
)
def umbat_produce(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Wybrany gracz otwiera produkcję: grant ``free`` (bez PRODUCTION jednostek - F_muaat umbat
    2), 2 sztuki, każda kosztu ≤ 4, płatne (1); siły naziemne w przestrzeni albo na jego planecie
    w tym systemie (3)."""
    if ctx.get("player") != player_id:
        return
    target = str(ctx["target"])
    position = str((ctx.get("params") or {}).get("position") or _NONE)
    if position == _NONE:
        return
    if position not in _umbat_systems(state, target):
        raise ValueError("Choose a system that contains your war sun or flagship.")
    state.production_grant = ProductionGrant(
        player_id=target, position=position, units=_UMBAT_UNITS, free=True,
        max_unit_cost=_UMBAT_MAX_COST, source="Umbat",
    )


# --------------------------------------------------------------------- Magmus (commander)


def _produced_war_sun(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    units = ctx.get("units") or {}
    return ctx.get("player") == player_id and int(units.get(_WARSUN, 0)) > 0


@on_event(
    GameEvent.UNITS_PRODUCED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    condition=_produced_war_sun, covers=f"unlocks:{COMMANDER}", label="Magmus unlocked",
)
def magmus_unlock(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Unlock: Produce a war sun."""
    registry = _registry()
    if COMMANDER in leaders.leaders_of(registry, state.players[player_id]):
        leaders.unlock(state, registry, player_id, COMMANDER)


@on_event(
    GameEvent.STRATEGY_TOKEN_SPENT, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_own_event, covers=f"leaders:{COMMANDER}",
    label="Magmus: gain 1 trade good",
)
def magmus(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Magmus: After you spend a token from your strategy pool: You may gain 1 trade good.

    Oferta powstaje w chwili wydania (odblokowany wcześniej - F_muaat magmus 4), a gracz odpowiada
    po rozstrzygnięciu secondary (1); każdy żeton osobno (2, C_objectives)."""
    economy.gain_trade_goods(state, player_id, 1, cause=f"leaders:{COMMANDER}")


# --------------------------------------------------- Adjudicator Ba'al — Nova Seed (hero)


def nova_seed_target(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> str | None:
    """Cel Nova Seed albo None: ruch war suna Muaat z INNEGO systemu (F_muaat 2) do systemu
    spoza domów (także wyeliminowanych - 6) innego niż Mecatol Rex."""
    registry = _registry()
    position = str(ctx.get("position") or "")
    ships = ctx.get("ships") or {}
    if (
        ctx.get("player") != player_id
        or int(ships.get(_WARSUN, 0)) <= 0
        or ctx.get("from") == position
        or position not in state.systems
        or state.systems[position].space_units.get(player_id, {}).get(_WARSUN, 0) <= 0
        or is_mecatol_position(state, position)
        or position in _home_positions(state, registry)
        or fracture.is_fracture_position(position)  # F_muaat nova-seed 9
        or state.systems[position].system_id == NOVA_SEED_TILE
    ):
        return None
    return position


def _hero_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("mover", player_id) == player_id  # "after YOU move" (F_mahact benediction 7)
        and nova_seed_target(state, player_id, ctx) is not None
        and leaders.is_ready(state, _registry(), player_id, HERO)
    )


@on_event(
    GameEvent.SHIPS_MOVED, Moment.AFTER, HookSource(SOURCE_LEADER, HERO),
    optional=True, condition=_hero_ready, covers=f"leaders:{HERO}",
    label="Adjudicator Ba'al: Nova Seed",
)
def nova_seed(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Adjudicator Ba'al — Nova Seed: After you move a war sun into a non-home system other than
    Mecatol Rex: You may destroy all other players' units in that system and replace that system
    tile with the Muaat supernova tile. If you do, purge this card and each planet card that
    corresponds to the replaced system tile.

    Każdy rodzaj ruchu (F_muaat 1: także odwrót). Żetony i jednostki Muaat zostają (3) -
    ``core/tile_swap``."""
    registry = _registry()
    position = nova_seed_target(state, player_id, ctx)
    if position is None:
        raise ValueError("Nova Seed is used after you move a war sun into a non-home system "
                         "other than Mecatol Rex.")
    system = state.systems[position]
    for owner, units in list(system.space_units.items()):
        if owner == player_id:
            continue
        for base_type, count in list(units.items()):
            if count > 0:
                unit_ops.remove_units(state, system, _SPACE, owner, base_type, count,
                                      UnitCause.DESTROYED)
    for planet, by_player in list(system.planet_units.items()):
        for owner, units in list(by_player.items()):
            if owner == player_id:
                continue
            for base_type, count in list(units.items()):
                if count > 0:
                    unit_ops.remove_units(state, system, planet, owner, base_type, count,
                                          UnitCause.DESTROYED)
    purged = tile_swap.replace_tile(state, registry, position, NOVA_SEED_TILE)
    faction_components.pay_cost(state, registry, player_id, "leader", HERO)
    ability_notes.note(state, player_id, f"leaders:{HERO}",
                       f"system {position} became a supernova; purged {len(purged)} planet(s)")


# ------------------------------------------------------------ Fires of the Gashlai (notka)


def _owns_war_sun_tech(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Technologia war suna gracza: ``ws`` albo ulepszenie frakcyjne war suna (Prototype War Sun II
    - C_agendas: Muaat bez PWS II nie ma technologii war suna)."""
    for tech_id in state.players[player_id].technologies:
        tech = registry.technologies.get(tech_id)
        if tech_id == WAR_SUN_TECH or (tech is not None and tech.base_upgrade == WAR_SUN_TECH):
            return True
    return False


@promissory_play.action_blocker(FIRES)
def _fires_blocker(state: GameState, registry: StaticDataRegistry, player_id: str) -> str | None:
    if _owns_war_sun_tech(state, registry, player_id):  # F_muaat fires 1
        return "You already own your war sun unit upgrade technology."
    muaat_players = [pid for pid, p in state.players.items() if p.faction == FACTION]
    if muaat_players and all(
        command_tokens.pool_count(state, pid, "fleet") <= 0 for pid in muaat_players
    ):  # F_muaat fires 2
        return "The Muaat player has no command tokens in their fleet pool."
    return None


@register_effect(f"promissory_notes:{FIRES}")
def fires_of_the_gashlai(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Fires of the Gashlai: ACTION: Remove 1 token from the Muaat player's fleet pool and return
    it to their reinforcements. Then, gain your war sun unit upgrade technology card. Then, return
    this card to the Muaat Player (zwrot - ``promissory_play``).

    „Gain” bez badania (F_jol_nar: nie odpala Research Agreement)."""
    if _owns_war_sun_tech(state, registry, player_id):
        raise ValueError("You already own your war sun unit upgrade technology.")
    owner = str(params.get("__owner") or "")
    if owner in state.players:
        if command_tokens.pool_count(state, owner, "fleet") <= 0:  # F_muaat fires 2
            raise ValueError("The Muaat player has no command tokens in their fleet pool.")
        command_tokens.spend_to_reinforcements(state, owner, "fleet")
    technology.grant_technology(state, player_id, WAR_SUN_TECH)


# ------------------------------------------------------------- Stellar Genesis (przełom)


def avernus_position(state: GameState) -> str | None:
    """System z żetonem planety Avernus (``added_planets``) albo None."""
    return next(
        (pos for pos, system in sorted(state.systems.items()) if AVERNUS in system.added_planets),
        None,
    )


def genesis_systems(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    """Systemy spoza domów sąsiadujące z planetą gracza (system planety i systemy obok niego -
    R_adjacency). Kandydaci z MAPY (``grid.positions``), nie z ``state.systems``: wpis stanu
    mają tylko systemy, w których coś się już działo (np. żeton frontier w pustych), więc
    systemy z planetami bez jednostek by znikały."""
    grid = _grid(state, registry)
    homes = _home_positions(state, registry)  # także domy wyeliminowanych
    owned = {pos for pos, system in state.systems.items() if player_id in
             system.planet_owners.values()}
    return sorted(
        pos for pos in board_graph.non_home_systems(state, registry)  # bez hyperlane
        if pos not in homes and pos in grid.positions
        and any(pos == src or grid.are_adjacent(pos, src) for src in owned)
    )


def genesis_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    # ``always``: gracz klika system na mapie także przy jednej legalnej opcji („gain” przełomu
    # widać na planszy, decyzja nie dzieje się po cichu).
    return [oi.choice("position", "System for the Avernus planet token", [
        _system_option(state, registry, pos) for pos in genesis_systems(state, registry, player_id)
    ], always=True)]


def _gains_genesis(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and avernus_position(state) is None


@on_event(
    GameEvent.COMPONENT_GAINED, Moment.WHEN, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    where={"component": f"breakthroughs:{BREAKTHROUGH}"}, decide=True,
    condition=_gains_genesis, inputs=genesis_inputs, covers=f"breakthroughs:{BREAKTHROUGH}",
    label="Stellar Genesis: place Avernus",
)
def stellar_genesis(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Stellar Genesis: When you gain this card, place the Avernus planet token into a non-home
    system that is adjacent to a planet you control; gain the Avernus planet card and ready it.

    Gracz eksploruje Avernus (F_muaat stellar-genesis 1)."""
    registry = _registry()
    position = str((ctx.get("params") or {}).get("position") or "")
    if position not in genesis_systems(state, registry, player_id):
        raise ValueError("Choose a non-home system adjacent to a planet you control.")
    system = board_graph.ensure_system(state, position)  # system bez wpisu stanu też
    system.added_planets = [*system.added_planets, AVERNUS]
    control.set_planet_control(state, position, AVERNUS, player_id, registry)
    exhaust.ready_planets(state, player_id, [AVERNUS])  # „ready it”
    exploration.start_exploration(state, registry, player_id, position, [AVERNUS])


def _carries_avernus(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """War sun wyleciał z systemu Avernus albo przeleciał przez niego, cel spoza domów.

    "After you move one of your war suns": the owner moved it - not when the Mahact moved it with
    Benediction (F_mahact airo-shir-aur-benediction 2.3)."""
    source = avernus_position(state)
    ships = ctx.get("ships") or {}
    route = [str(p) for p in ctx.get("route") or []]
    dest = str(ctx.get("position") or "")
    return (
        ctx.get("player") == player_id
        and ctx.get("mover", player_id) == player_id
        and source is not None
        and int(ships.get(_WARSUN, 0)) > 0
        and source in route[:-1]
        and dest != source
        and dest in state.systems
        and dest not in _home_positions(state, _registry())
    )


@on_event(
    GameEvent.SHIPS_MOVED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    optional=True, condition=_carries_avernus, covers=f"breakthroughs:{BREAKTHROUGH}",
    label="Stellar Genesis: move Avernus",
)
def move_avernus(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """After you move one of your war suns out of or through Avernus's system and into a non-home
    system, you may move the Avernus token with it.

    Żeton z jednostkami, kontrolą i uszkodzeniami (także gdy kontroluje go inny gracz - F_muaat
    2; do systemu z cudzymi jednostkami - 3)."""
    source = avernus_position(state)
    dest = str(ctx.get("position") or "")
    if source is None or not _carries_avernus(state, player_id, ctx):
        raise ValueError("Avernus moves with a war sun that left or passed through its system.")
    origin, target = state.systems[source], state.systems[dest]
    origin.added_planets = [p for p in origin.added_planets if p != AVERNUS]
    target.added_planets = [*target.added_planets, AVERNUS]
    for owner, units in sorted(origin.planet_units.get(AVERNUS, {}).items()):
        for base_type, count in sorted(units.items()):
            if count > 0:  # uszkodzenia jadą z jednostkami (unit_ops)
                unit_ops.transfer_units(state, origin, AVERNUS, target, AVERNUS, owner,
                                        base_type, count)
    unit_ops.clear_planet(origin, AVERNUS)
    control.relocate_planet(state, AVERNUS, source, dest)
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                       f"Avernus moved to system {dest}")
