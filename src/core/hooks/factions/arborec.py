"""Arborec — komplet komponentów frakcji (RULES.md 62.5).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("arborec")``, ``units``).
Rulingi: ``docs/rules_tirules/F_arborec.md``. Letani Warrior II korzysta z mechanizmu Infantry II
(``hooks/technologies_passive.py``). Produkcja poza krokiem PRODUCTION (flagowiec, commander,
bohater) = grant ``free`` (``ProductionGrant``): jednostki płatne, bez zdolności PRODUCTION.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    board_graph,
    command_tokens,
    faction_components,
    faction_units,
    leaders,
    production,
    promissory_play,
    rules_hooks,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.fleet_pool import unit_name
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, ProductionGrant
from src.core.production import reinforcements_left
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_PRODUCTION_FORBIDS,
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
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

FACTION = "arborec"
AGENT = "arborecagent"
COMMANDER = "arboreccommander"
HERO = "arborechero"
FLAGSHIP = "arborec_flagship"
MECH = "arborec_mech"
BIOPLASMOSIS = "bio"
STYMIE = "stymie"
BREAKTHROUGH = "arborecbt"

_FLAGSHIP_UNITS = 5  # „produce up to 5 units in this system”
_COMMANDER_UNITS = 1  # „produce 1 unit in that system”
_COMMANDER_GROUND = 12  # „Have 12 ground forces on planets you control.”
_AGENT_EXTRA_COST = 2  # „costs up to 2 more than the replaced ship”
_GROUND = ("infantry", "mech")
_KEEP = "keep"
_SPACE = "space"
_NONE = "none"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _planet_name(registry: Any, planet: str) -> str:
    return registry.planets[planet].name if planet in registry.planets else planet


def _controlled(state: GameState, player_id: str) -> list[tuple[str, str]]:
    return sorted(
        (position, planet)
        for position, system in state.systems.items()
        for planet, owner in system.planet_owners.items()
        if owner == player_id
    )


def _infantry_left(state: GameState, player_id: str) -> bool:
    left = reinforcements_left(state, player_id, "infantry")
    return left is None or left > 0


# --------------------------------------------------------------------- Mitosis + mech


@register(
    POINT_PRODUCTION_FORBIDS, HookSource(SOURCE_FACTION, FACTION), HookKind.FORBID,
)
def arborec_dock_no_infantry(
    _state: GameState, _player_id: str, ctx: Mapping[str, Any]
) -> tuple[str, ...]:
    """Mitosis: Your space docks cannot produce infantry (R_production).

    Piechota Arborec ma własne PRODUCTION i nadal może produkować (RULES.md 33).
    """
    return ("infantry",) if ctx.get("producer_type") == "spacedock" else ()


def _has_mech_option(state: GameState, player_id: str) -> bool:
    if faction_units.variant_of(state, _registry(), player_id, "mech") != MECH:
        return False
    left = reinforcements_left(state, player_id, "mech")
    return left is None or left > 0


def _mitosis_ready(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """F_arborec: obowiązkowe, chyba że gracz nie kontroluje żadnej planety."""
    return bool(_controlled(state, player_id)) and (
        _infantry_left(state, player_id) or _has_mech_option(state, player_id)
    )


def mitosis_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """1 piechota na kontrolowaną planetę ALBO (Letani Behemoth) zamiana piechoty na mecha."""
    options: list[dict[str, Any]] = []
    if _infantry_left(state, player_id):
        options += [
            oi.option(f"inf|{position}|{planet}", f"1 infantry on {_planet_name(registry, planet)}")
            for position, planet in _controlled(state, player_id)
        ]
    if _has_mech_option(state, player_id):
        for position, system in sorted(state.systems.items()):
            # „replace 1 of your infantry” - każda piechota: na planecie albo w przestrzeni.
            for zone in [_SPACE, *sorted(system.planet_units)]:
                if unit_ops.count_in_zone(system, zone, player_id, "infantry") <= 0:
                    continue
                where = (
                    f"in the space area of system {position}" if zone == _SPACE
                    else f"on {_planet_name(registry, zone)}"
                )
                options.append(oi.option(
                    f"mech|{position}|{zone}", f"Letani Behemoth: replace 1 infantry {where}",
                ))
    return [oi.choice("mitosis", "Mitosis", options)]


@on_event(
    GameEvent.PHASE, Moment.START, HookSource(SOURCE_FACTION, FACTION), where={"phase": "status"},
    decide=True, condition=_mitosis_ready, inputs=mitosis_inputs,
    covers="abilities:mitosis", label="Mitosis",
)
def mitosis(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Mitosis: At the start of the status phase: Place 1 infantry from your reinforcements on any
    planet you control. Letani Behemoth — DEPLOY: When you would use your Mitosis faction ability
    you may replace 1 of your infantry with 1 mech from your reinforcements instead."""
    kind, _, rest = str(ctx.get("params", {}).get("mitosis") or "").partition("|")
    position, _, planet = rest.partition("|")
    system = state.systems.get(position)
    if system is None or not planet:
        raise ValueError("Choose where Mitosis places the unit.")
    if kind == "mech":
        if unit_ops.count_in_zone(system, planet, player_id, "infantry") <= 0:
            raise ValueError("Choose your infantry (on a planet or in a space area).")
        unit_ops.remove_units(state, system, planet, player_id, "infantry", 1, UnitCause.REMOVED)
        unit_ops.place_units(state, system, planet, player_id, "mech", 1, UnitCause.PLACED)
        return
    if system.planet_owners.get(planet) != player_id:
        raise ValueError("Choose a planet you control.")
    unit_ops.place_units(state, system, planet, player_id, "infantry", 1, UnitCause.PLACED)


rules_hooks.declare_player_option(f"units:{MECH}")  # DEPLOY = opcja w decyzji Mitosis


# ----------------------------------------------------------------------- Bioplasmosis


def _bio_routes(state: GameState, player_id: str) -> list[tuple[str, str, str, str, int]]:
    """``(pozycja źródła, planeta źródła, pozycja celu, planeta celu, piechota źródła)``."""
    controlled = _controlled(state, player_id)
    routes: list[tuple[str, str, str, str, int]] = []
    for position, planet in controlled:
        count = state.systems[position].planet_units.get(planet, {}).get(player_id, {}).get(
            "infantry", 0
        )
        if count <= 0:
            continue
        near = {position, *board_graph.adjacent_positions(position)}
        for dest_pos, dest in controlled:
            if dest_pos in near and (dest_pos, dest) != (position, planet):
                routes.append((position, planet, dest_pos, dest, count))
    return routes


def _bio_ready(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return bool(_bio_routes(state, player_id))


def bio_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Dla każdej pary planet (ta sama lub sąsiednia): ile piechoty przenieść (jednocześnie)."""
    return [
        oi.number(
            f"bio:{src_pos}:{src}:{dst_pos}:{dst}",
            f"{_planet_name(registry, src)} -> {_planet_name(registry, dst)}", 0, count,
            meta=oi.route_meta(src, dst),
        )
        for src_pos, src, dst_pos, dst, count in _bio_routes(state, player_id)
    ]


@on_event(
    GameEvent.PHASE, Moment.END, HookSource(SOURCE_TECHNOLOGY, BIOPLASMOSIS),
    where={"phase": "status"}, optional=True, condition=_bio_ready, inputs=bio_inputs,
    covers=f"technologies:{BIOPLASMOSIS}", label="Bioplasmosis",
)
def bioplasmosis(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Bioplasmosis: At the end of the status phase, you may remove any number of infantry from
    planets you control and place them on 1 or more planets you control in the same or adjacent
    systems. (Ruch jednoczesny, najwyżej o 1 system - F_arborec.)"""
    moves: list[tuple[str, str, str, str, int]] = []
    taken: dict[tuple[str, str], int] = {}
    for key, value in ctx.get("params", {}).items():
        if not key.startswith("bio:") or not value:
            continue
        _, src_pos, src, dst_pos, dst = key.split(":", 4)
        moves.append((src_pos, src, dst_pos, dst, int(value)))
        taken[(src_pos, src)] = taken.get((src_pos, src), 0) + int(value)
    for (src_pos, src), count in taken.items():
        have = state.systems[src_pos].planet_units.get(src, {}).get(player_id, {}).get(
            "infantry", 0
        )
        if count > have:
            raise ValueError("You cannot move more infantry than a planet holds.")
    for src_pos, src, _, _, count in moves:  # najpierw zdejmij wszystko (jednocześnie)
        unit_ops.remove_units(
            state, state.systems[src_pos], src, player_id, "infantry", count, UnitCause.MOVED
        )
    for _, _, dst_pos, dst, count in moves:
        unit_ops.place_units(
            state, state.systems[dst_pos], dst, player_id, "infantry", count, UnitCause.MOVED
        )


# -------------------------------------------------------------------- Letani Ospha (agent)


def _ship_cost(state: GameState, registry: Any, player_id: str, base_type: str) -> float | None:
    player = state.players[player_id]
    unit = resolve_unit_variant(
        registry, player.faction, player.technologies, base_type, player.breakthrough_unlocked
    )
    return unit.cost if unit is not None else None


@register_effect_inputs(f"leaders:{AGENT}")
def agent_inputs(
    state: GameState, registry: StaticDataRegistry, _player_id: str
) -> list[dict[str, Any]]:
    """Statek niemyśliwski dowolnego gracza na planszy."""
    options: list[dict[str, Any]] = []
    for position, system in sorted(state.systems.items()):
        for owner, units in sorted(system.space_units.items()):
            player = state.players.get(owner)
            if player is None:
                continue
            for base_type, count in sorted(units.items()):
                if count > 0 and is_space_unit(base_type) and base_type != "fighter":
                    meta = oi.unit_at(state, owner, base_type, position=position)
                    meta["count"] = count
                    options.append(oi.option(
                        f"{owner}|{position}|{base_type}",
                        f"{unit_name(state, registry, owner, base_type)} ({position})", meta=meta,
                    ))
    return [oi.choice("ship", "Non-fighter ship to replace", options)]


@register_effect(f"leaders:{AGENT}")
def letani_ospha(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Letani Ospha: ACTION: Exhaust this card and choose a player's non-fighter ship: that player
    may replace that ship with one from their reinforcements that costs up to 2 more than the
    replaced ship. (Decyzję o zamianie podejmuje właściciel statku.)"""
    owner, position, base_type = (str(params.get("ship") or "").split("|") + ["", "", ""])[:3]
    system = state.systems.get(position)
    if owner not in state.players or system is None or (
        system.space_units.get(owner, {}).get(base_type, 0) <= 0
    ):
        raise ValueError("Choose a non-fighter ship on the game board.")
    from src.core import triggers  # lokalnie: hooki ładują się przed triggers w części ścieżek

    triggers.fire(
        state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "ability": f"leaders:{AGENT}", "target": owner,
             "position": position, "base_type": base_type},
    )


def _agent_target(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


_SHIP_TYPES = ("fighter", "destroyer", "cruiser", "carrier", "dreadnought", "flagship", "warsun")


def _replacements(
    state: GameState, registry: Any, owner: str, base_type: str, position: str
) -> list[str]:
    """Zamienniki: ``typ`` (z rezerwy) albo ``typ@pozycja`` (z planszy, gdy rezerwa pusta).

    Typy statków właściciela kosztujące najwyżej o 2 więcej (myśliwiec też). F_arborec: gdy
    danego typu nie ma w rezerwie, wolno zdjąć taki statek z systemu bez żetonu tego gracza.
    """
    limit = _ship_cost(state, registry, owner, base_type)
    if limit is None:
        return []
    found: list[str] = []
    for candidate in _SHIP_TYPES:
        if candidate == base_type:
            continue
        cost = _ship_cost(state, registry, owner, candidate)
        if cost is None or cost > limit + _AGENT_EXTRA_COST:
            continue
        left = reinforcements_left(state, owner, candidate)
        if left is None or left > 0:
            found.append(candidate)
            continue
        for source, system in sorted(state.systems.items()):
            if source == position or owner in system.command_tokens:
                continue
            if system.space_units.get(owner, {}).get(candidate, 0) > 0:
                found.append(f"{candidate}@{source}")
    return found


def ospha_inputs(
    state: GameState, registry: Any, decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    base_type = str(ctx["base_type"])
    options = [oi.option(_KEEP, "Keep the ship")]
    for value in _replacements(state, registry, decider, base_type, str(ctx["position"])):
        unit, _, source = value.partition("@")
        name = unit_name(state, registry, decider, unit)
        options.append(oi.option(value, f"{name} (from system {source})" if source else name))
    return [oi.choice("replacement", "Replace the ship with", options)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    where={"ability": f"leaders:{AGENT}"}, decide=True, decider=_agent_target,
    inputs=ospha_inputs, covers=f"leaders:{AGENT}", label="Letani Ospha: replace a ship",
)
def ospha_replace(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    """Zamieniany statek nie jest niszczony, nowy nie jest produkowany (F_arborec)."""
    choice = str(ctx.get("params", {}).get("replacement") or _KEEP)
    if choice == _KEEP:
        return
    owner = str(ctx["decider"])
    base_type = str(ctx["base_type"])
    position = str(ctx["position"])
    if choice not in _replacements(state, _registry(), owner, base_type, position):
        raise ValueError("That ship costs too much or is not available.")
    unit, _, source = choice.partition("@")
    if source:  # z planszy: zdjęty stamtąd, postawiony nieuszkodzony (F_arborec)
        unit_ops.remove_units(
            state, state.systems[source], "space", owner, unit, 1, UnitCause.REMOVED
        )
    system = state.systems[position]
    unit_ops.remove_units(state, system, "space", owner, base_type, 1, UnitCause.REMOVED)
    unit_ops.place_units(state, system, "space", owner, unit, 1, UnitCause.PLACED)


# ------------------------------------------------------------------- Dirzuga Rophal


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 12 ground forces on planets you control."""
    total = 0
    for system in state.systems.values():
        for planet, by_player in system.planet_units.items():
            if system.planet_owners.get(planet) == player_id:
                units = by_player.get(player_id, {})
                total += sum(units.get(bt, 0) for bt in _GROUND)
    return total >= _COMMANDER_GROUND


def _commander_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    position = str(ctx.get("position"))
    return (
        ctx.get("player") != player_id
        and state.production_grant is None
        and bool(production.producers(state, _registry(), player_id, position))
    )


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_commander_ready, covers=f"leaders:{COMMANDER}",
    label="Dirzuga Rophal: produce 1 unit",
)
def dirzuga_rophal(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dirzuga Rophal: After another player activates a system that contains 1 or more of your
    units that have PRODUCTION: You may produce 1 unit in that system (płatne, bez PRODUCTION)."""
    state.production_grant = ProductionGrant(
        player_id=player_id, position=str(ctx["position"]), units=_COMMANDER_UNITS, free=True,
        source="Dirzuga Rophal",
    )


# ----------------------------------------------------------------- Duha Menaimon (flagowiec)


def _flagship_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("player") == player_id
        and state.production_grant is None
        and faction_units.has_unit_in(state, _registry(), player_id, FLAGSHIP,
                                      str(ctx.get("position")))
    )


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_UNIT, FLAGSHIP),
    optional=True, condition=_flagship_ready, covers=f"units:{FLAGSHIP}",
    label="Duha Menaimon: produce up to 5 units",
)
def duha_menaimon(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Duha Menaimon: After you activate this system, you may produce up to 5 units in this
    system. (Płatne; flagowiec nie ma PRODUCTION, więc Sarween Tools nie działa - F_arborec.)"""
    state.production_grant = ProductionGrant(
        player_id=player_id, position=str(ctx["position"]), units=_FLAGSHIP_UNITS, free=True,
        source="Duha Menaimon",
    )


# ------------------------------------------------------- Letani Miasmiala (hero)


def _ground_systems(state: GameState, player_id: str) -> list[str]:
    return sorted(
        position
        for position, system in state.systems.items()
        if any(
            by_player.get(player_id, {}).get(bt, 0) > 0
            for by_player in system.planet_units.values()
            for bt in _GROUND
        )
        or any(system.space_units.get(player_id, {}).get(bt, 0) > 0 for bt in _GROUND)
    )


@faction_components.blocker("leader", HERO)
def _hero_blocker(state: GameState, _registry: StaticDataRegistry, player_id: str) -> str | None:
    if state.production_grant is not None:
        return "Another production is still open - finish it first."
    if not _ground_systems(state, player_id):
        return "You have no ground forces on the game board."
    return None


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [oi.option(p, f"System {p}") for p in _ground_systems(state, player_id)]
    return [oi.multi("systems", "Systems to produce in (one after another)", options, 1,
                     len(options))]


@register_effect(f"leaders:{HERO}")
def ultrasonic_emitter(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Letani Miasmiala — Ultrasonic Emitter: ACTION: Produce any number of units in any number of
    systems that contain 1 or more of your ground forces. Then, purge this card.

    Grant ``free`` z kolejką systemów; limit sztuk = najwięcej, ile gracz może opłacić (2 sztuki
    za 1 zasób - najtańsze jednostki), więc to realna granica, nie sztuczna liczba."""
    systems = [str(s) for s in params.get("systems") or []]
    allowed = set(_ground_systems(state, player_id))
    if not systems or any(s not in allowed for s in systems):
        raise ValueError("Choose systems that contain your ground forces.")
    budget = production.available_budget(state, registry, player_id)
    state.production_grant = ProductionGrant(
        player_id=player_id, position=systems[0], units=max(1, 2 * budget), free=True,
        source="Ultrasonic Emitter", queue=systems[1:],
    )


# ---------------------------------------------------------------------------- Stymie


@promissory_play.condition(STYMIE)
def _stymie_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> str | None:
    mover = window.ctx.get("player")
    system = state.systems.get(str(window.ctx.get("position")))
    if mover == player_id or system is None:
        return "Stymie is played after ANOTHER player moves ships into your system."
    has_units = any(n > 0 for n in system.space_units.get(player_id, {}).values()) or any(
        n > 0 for by_player in system.planet_units.values()
        for n in by_player.get(player_id, {}).values()
    )
    if not has_units:
        return "The active system does not contain your units."
    if command_tokens.reinforcements(state, str(mover)) <= 0 and not _sheet_pools(
        state, str(mover)
    ):
        return "That player has no command token to place."
    return None


_POOLS = ("tactical", "fleet", "strategic")


def _sheet_pools(state: GameState, player_id: str) -> list[str]:
    return [p for p in _POOLS if command_tokens.pool_count(state, player_id, p) > 0]


promissory_play.any_subject(STYMIE)


@register_effect_inputs(f"promissory_notes:{STYMIE}")
def stymie_inputs(
    state: GameState, registry: StaticDataRegistry, _player_id: str
) -> list[dict[str, Any]]:
    mover = state.active_player_id or ""
    options = [oi.option(_NONE, "Do not place")] + [
        oi.option(p, f"System {p}")
        for p in board_graph.non_home_systems(state, registry)
        if p in state.systems and mover not in state.systems[p].command_tokens
    ]
    return [oi.choice("system", "Non-home system for their command token", options)]


@register_effect(f"promissory_notes:{STYMIE}")
def stymie(
    state: GameState, registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Stymie: After another player moves ships into a system that contains 1 or more of your
    units: You may place 1 command token from that player's reinforcements in any non-home
    system. Then, return this card to the Arborec player."""
    choice = str(params.get("system") or _NONE)
    mover = state.active_player_id
    if choice == _NONE or mover is None:
        return
    system = state.systems.get(choice)
    if system is None or choice not in board_graph.non_home_systems(state, registry):
        raise ValueError("Choose a non-home system.")
    if mover in system.command_tokens:
        raise ValueError("That player already has a command token in that system.")
    if command_tokens.reinforcements(state, mover) > 0:
        command_tokens.place_on_board_from_reinforcements(state, system, mover)
        return
    # Stymie Ω (F_arborec): pusta rezerwa -> ten gracz sam wybiera żeton z arkusza.
    from src.core import triggers

    triggers.fire(
        state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=mover,
        ctx={"player": mover, "ability": f"promissory_notes:{STYMIE}", "target": mover,
             "position": choice},
    )


def stymie_pool_inputs(
    state: GameState, _registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options = [oi.option(p, f"From your {p} pool") for p in _sheet_pools(state, decider)]
    return [oi.choice("pool", "Stymie: command token from your command sheet", options)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": f"promissory_notes:{STYMIE}"}, decide=True, decider=_agent_target,
    inputs=stymie_pool_inputs, label="Stymie: token from your command sheet",
)
def stymie_from_sheet(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    mover = str(ctx["decider"])
    pool = str(ctx.get("params", {}).get("pool") or "")
    if pool not in _sheet_pools(state, mover):
        raise ValueError("Choose a pool that has a command token.")
    command_tokens.place_on_board_from_pool(state, state.systems[str(ctx["position"])], mover, pool)


# ------------------------------------------------------------------ Psychospore (BT)


def _bt_systems(state: GameState, player_id: str) -> list[str]:
    return sorted(
        p for p, system in state.systems.items()
        if player_id in system.command_tokens and (
            system.space_units.get(player_id, {}).get("infantry", 0) > 0
            or any(
                by_player.get(player_id, {}).get("infantry", 0) > 0
                for by_player in system.planet_units.values()
            )
        )
    )


@faction_components.blocker("breakthrough", BREAKTHROUGH)
def _bt_blocker(state: GameState, _registry: StaticDataRegistry, player_id: str) -> str | None:
    if not _bt_systems(state, player_id):
        return "No system with your command token contains your infantry."
    return None


@register_effect_inputs(f"breakthroughs:{BREAKTHROUGH}")
def bt_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """System z Twoim żetonem i piechotą + gdzie postawić nową piechotę (strefa z piechotą)."""
    options: list[dict[str, Any]] = []
    for position in _bt_systems(state, player_id):
        system = state.systems[position]
        if system.space_units.get(player_id, {}).get("infantry", 0) > 0:
            options.append(oi.option(f"{position}|space", f"System {position}: space area"))
        for planet, by_player in sorted(system.planet_units.items()):
            if by_player.get(player_id, {}).get("infantry", 0) > 0:
                options.append(oi.option(
                    f"{position}|{planet}", f"System {position}: {_planet_name(registry, planet)}"
                ))
    return [oi.choice("target", "Remove your token and place 1 infantry", options)]


@register_effect(f"breakthroughs:{BREAKTHROUGH}")
def psychospore(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Psychospore: ACTION: Exhaust this card to remove a command token from a system that contains
    1 or more of your infantry and return it to your reinforcements. Then, place 1 infantry in
    that system. (Żeton wraca do TWOJEJ rezerwy, więc to Twój żeton - RULES.md 62.5.)"""
    position, _, zone = str(params.get("target") or "").partition("|")
    if position not in _bt_systems(state, player_id) or not zone:
        raise ValueError("Choose a system with your command token and your infantry.")
    system = state.systems[position]
    command_tokens.remove_from_board(state, system, player_id)
    if _infantry_left(state, player_id):
        unit_ops.place_units(state, system, zone, player_id, "infantry", 1, UnitCause.PLACED)
