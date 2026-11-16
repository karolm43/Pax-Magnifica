"""Sardakk N'orr — komplet komponentów frakcji (RULES.md 62.1).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("sardakk")``, ``units``).
Rulingi: ``docs/rules_tirules/F_norr.md``. Gracz decyduje sam (RULES.md 56): „you may” = oferta,
wybory celów liczy silnik.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    battle,
    board_graph,
    command_tokens,
    faction_components,
    faction_units,
    invasion,
    ion_storm,
    leaders,
    movement,
    promissory_play,
    retreat,
    rules_hooks,
    technology,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, InvasionPhase, Phase, TacticalStep
from src.core.hex_grid import HexGrid
from src.core.hooks import card_labels
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_COMBAT_EXTRA_HITS,
    POINT_COMBAT_ROLL_MODIFIER,
    POINT_INVASION_SKIP_BOMBARDMENT,
    SOURCE_BREAKTHROUGH,
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
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

FACTION = "sardakk"
AGENT = "sardakkagent"
COMMANDER = "sardakkcommander"
HERO = "sardakkhero"
FLAGSHIP = "sardakk_flagship"
MECH = "sardakk_mech"
EXOTRIREME_TECH = "exo2"
EXOTRIREME_UNIT = "sardakk_dreadnought2"
VPW = "vpw"
TEKKLAR = "tekklar"
BREAKTHROUGH = "sardakkbt"

HERO_EFFECT = f"leaders:{HERO}"  # Tekklar Conditioning w toku (do końca akcji taktycznej)
COMMANDER_USED = f"leaders:{COMMANDER}:used"  # jedno użycie G'hom Sek'kus na inwazję
TEKKLAR_BONUS = f"promissory_notes:{TEKKLAR}"
TEKKLAR_PENALTY = f"promissory_notes:{TEKKLAR}:penalty"
_AGENT_INFANTRY = 2  # „place 2 infantry”
_COMMANDER_PLANETS = 5  # „Control 5 planets in non-home systems.”
_EXO_TARGETS = 2  # „destroy up to 2 ships”
_GROUND = ("infantry", "mech")
_NONE = "none"

rules_hooks.declare_data_driven(f"units:{EXOTRIREME_UNIT}")  # zdolność = efekt techu exo2 niżej


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _opponent(player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["defender"] if ctx.get("attacker") == player_id else ctx["attacker"])


def _combat_opponent(state: GameState, player_id: str) -> str | None:
    combat = state.active_combat
    if combat is None or player_id not in (combat.attacker, combat.defender):
        return None
    return combat.defender if combat.attacker == player_id else combat.attacker


# ------------------------------------------------------------------- Unrelenting, flagowiec


@register(
    POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_FACTION, FACTION), HookKind.MODIFY,
    covers="abilities:unrelenting",
)
def unrelenting(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Unrelenting: Apply +1 to the result of each of your unit's combat rolls."""
    return 1


@register(
    POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.MODIFY,
    covers=f"units:{FLAGSHIP}",
)
def cmorran_norr(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """C'morran N'orr: Apply +1 to the result of each of your other ship's combat rolls in this
    system."""
    if ctx.get("kind") != "space" or ctx.get("base_type") == "flagship":
        return 0
    position = str(ctx.get("position"))
    return 1 if faction_units.has_unit_in(state, _registry(), player_id, FLAGSHIP, position) else 0


# --------------------------------------------------------------------- Valkyrie: mech i VPW


def _mech_sustained(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    combat = state.active_combat
    return (
        ctx.get("player") == player_id
        and ctx.get("base_type") == "mech"
        and combat is not None
        and combat.kind == "ground"
    )


@on_event(
    GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, HookSource(SOURCE_UNIT, MECH),
    condition=_mech_sustained, covers=f"units:{MECH}", label="Valkyrie Exoskeleton",
)
def valkyrie_exoskeleton(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Valkyrie Exoskeleton: After this unit uses its SUSTAIN DAMAGE ability during ground combat,
    it produces 1 hit against your opponent's ground forces on this planet (obowiązkowo)."""
    opponent = _combat_opponent(state, player_id)
    if opponent is not None:
        battle.add_combat_hits(state, opponent, int(ctx.get("count", 1)))


@register(
    POINT_COMBAT_EXTRA_HITS, HookSource(SOURCE_TECHNOLOGY, VPW), HookKind.MODIFY,
    covers=f"technologies:{VPW}",
)
def valkyrie_particle_weave(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    """Valkyrie Particle Weave: After making combat rolls during a round of ground combat, if your
    opponent produced 1 or more hits, you produce 1 additional hit."""
    return 1 if ctx.get("kind") == "ground" and int(ctx.get("opponent_hits", 0)) > 0 else 0


# ------------------------------------------------------------------------------ Exotrireme II


def _enemy_ships(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> dict[str, int]:
    system = state.systems.get(str(ctx.get("position")))
    if system is None:
        return {}
    enemy = _opponent(player_id, ctx)
    return {
        bt: n for bt, n in system.space_units.get(enemy, {}).items() if n > 0 and is_space_unit(bt)
    }


def _opponent_retreats(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Przeciwnik ogłosił odwrót, który się odbędzie (jest dozwolony cel — O3/O4)."""
    combat = state.active_combat
    enemy = _opponent(player_id, ctx)
    if combat is None or enemy not in combat.retreating:
        return False
    grid = board_graph.bound_grid() or HexGrid()
    return bool(retreat.retreat_destinations(state, grid, str(ctx.get("position")), enemy))


def _exotrireme_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("kind") != "space" or player_id not in (ctx.get("attacker"), ctx.get("defender")):
        return False
    if _opponent_retreats(state, player_id, ctx):
        return False  # F_norr: po odwrocie przeciwnika zdolności nie da się użyć
    position = str(ctx.get("position"))
    return faction_units.has_unit_in(
        state, _registry(), player_id, EXOTRIREME_UNIT, position
    ) and bool(_enemy_ships(state, player_id, ctx))


def exotrireme_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """1–2 statki przeciwnika (każdy egzemplarz osobno; F_norr: tylko cudze)."""
    enemy = _opponent(player_id, ctx)
    options = [
        oi.option(f"{bt}#{i}", f"{unit_name(state, registry, enemy, bt)} ({i})")
        for bt, n in sorted(_enemy_ships(state, player_id, ctx).items())
        for i in range(1, n + 1)
    ]
    most = min(_EXO_TARGETS, len(options))
    return [oi.multi("ships", "Enemy ships to destroy", options, 1, most)]


@on_event(
    GameEvent.COMBAT_ROUND, Moment.END, HookSource(SOURCE_TECHNOLOGY, EXOTRIREME_TECH),
    where={"phase": "combat"}, optional=True, condition=_exotrireme_ready,
    covers=f"technologies:{EXOTRIREME_TECH}", label="Exotrireme II",
    inputs=exotrireme_inputs,
)
def exotrireme(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Exotrireme II: After a round of space combat, you may destroy this unit to destroy up to 2
    ships in this system. (Sustain Damage tego nie anuluje — F_norr.)"""
    system = state.systems[str(ctx["position"])]
    enemy = _opponent(player_id, ctx)
    chosen = ctx.get("params", {}).get("ships") or []
    unit_ops.remove_units(state, system, "space", player_id, "dreadnought", 1, UnitCause.DESTROYED)
    counts: dict[str, int] = {}
    for value in chosen:
        base_type = str(value).split("#", 1)[0]
        counts[base_type] = counts.get(base_type, 0) + 1
    for base_type, count in counts.items():
        unit_ops.remove_units(state, system, "space", enemy, base_type, count, UnitCause.DESTROYED)


# ------------------------------------------------------------------------- Tekklar Legion


@promissory_play.condition(TEKKLAR)
def _tekklar_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> str | None:
    combat = state.active_combat
    if combat is None or combat.kind != "ground":
        return "Tekklar Legion is played at the start of an invasion (ground) combat."
    if player_id not in (combat.attacker, combat.defender):
        return "You are not in this ground combat."
    return None


@register_effect(f"promissory_notes:{TEKKLAR}")
def tekklar_legion(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Tekklar Legion: At the start of an invasion combat: Apply +1 to the result of each of your
    unit's combat rolls during this combat. If your opponent is the N'orr player, apply -1 to the
    result of each of their unit's combat rolls during this combat. Then, return this card."""
    active_effects.add_effect(state, TEKKLAR_BONUS, Duration.COMBAT, owner=player_id)
    owner = params.get("__owner")
    if isinstance(owner, str) and _combat_opponent(state, player_id) == owner:
        active_effects.add_effect(state, TEKKLAR_PENALTY, Duration.COMBAT, owner=owner)


@register(POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_EFFECT, TEKKLAR_BONUS), HookKind.MODIFY)
def tekklar_bonus(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    return 1


@register(POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_EFFECT, TEKKLAR_PENALTY), HookKind.MODIFY)
def tekklar_penalty(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    return -1


# ----------------------------------------------------------------------------------- T'ro


def _agent_planets(state: GameState, target: str, position: str) -> list[str]:
    system = state.systems.get(position)
    if system is None:
        return []
    return sorted(p for p, owner in system.planet_owners.items() if owner == target)


def _agent_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    target = ctx.get("player")
    position = ctx.get("position")
    return (
        isinstance(target, str)
        and isinstance(position, str)
        and leaders.is_ready(state, _registry(), player_id, AGENT)
        and bool(_agent_planets(state, target, position))
    )


@on_event(
    GameEvent.TACTICAL_ACTION, Moment.END, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_agent_ready, covers=f"leaders:{AGENT}",
    label="T'ro: exhaust to let the active player place 2 infantry",
)
def tro_exhaust(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """T'ro: At the end of a player's tactical action: You may exhaust this card: if you do, that
    player may place 2 infantry from their reinforcements on a planet they control in the active
    system. Decyzję o planecie podejmuje TEN gracz (osobna oferta)."""
    faction_components.pay_cost(
        state, _registry(), player_id, "leader", AGENT,
        {"target": ctx["player"], "position": ctx["position"]},
    )


def _agent_target(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def _agent_granted(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Tylko wyczerpanie z oferty końca akcji taktycznej (ma gracza-odbiorcę i system)."""
    return "target" in ctx and "position" in ctx


def tro_inputs(
    state: GameState, registry: Any, decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    planets = _agent_planets(state, decider, str(ctx["position"]))
    options = [oi.option(_NONE, "Do not place")] + [
        oi.option(p, registry.planets[p].name if p in registry.planets else p) for p in planets
    ]
    return [oi.choice("planet", "Place 2 infantry on", options)]


@on_event(
    GameEvent.COMPONENT_EXHAUSTED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    where={"component": f"leaders:{AGENT}"}, condition=_agent_granted, decide=True,
    decider=_agent_target,
    inputs=tro_inputs, label="T'ro: place 2 infantry",
)
def tro_place(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    planet = ctx.get("params", {}).get("planet")
    target = str(ctx["decider"])
    if not planet or planet == _NONE:
        return
    system = state.systems[str(ctx["position"])]
    if system.planet_owners.get(str(planet)) != target:
        raise ValueError("Choose a planet you control in the active system.")
    unit_ops.place_units(state, system, str(planet), target, "infantry", _AGENT_INFANTRY,
                         UnitCause.PLACED)


# --------------------------------------------------------------------------- G'hom Sek'kus


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Control 5 planets in non-home systems (domy wszystkich graczy się nie liczą)."""
    count = 0
    for position, system in state.systems.items():
        if board_graph.is_home_system(state, registry, position):
            continue
        count += sum(1 for owner in system.planet_owners.values() if owner == player_id)
    return count >= _COMMANDER_PLANETS


def _commander_sources(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str, list[str]]]:
    """Planety-źródła: ``(pozycja, planeta, typy sił naziemnych gracza)``."""
    inv = state.invasion
    if inv is None:
        return []
    positions = [inv.position]
    grid = board_graph.bound_grid() or HexGrid()
    # F_norr: siły muszą móc legalnie wejść do aktywnego systemu (supernowa, asteroidy), nie
    # przy Ceasefire i nie przez wormhole przy Enforced Travel Ban / Nexus Sovereignty
    # („cannot commit ground forces through a wormhole if the Enforced Travel Ban law is in play").
    blocked = movement.entry_blocked(grid, state, inv.position, player_id) is not None
    if not blocked and not promissory_play.ceasefire_blocks(state, player_id):
        for position in sorted(board_graph.adjacent_positions(inv.position)):
            system = state.systems.get(position)
            if system is None or player_id in system.command_tokens:
                continue
            if movement.wormhole_link_blocked(grid, state, player_id, position, inv.position):
                continue
            positions.append(position)
    sources: list[tuple[str, str, list[str]]] = []
    for position in positions:
        system = state.systems.get(position)
        if system is None:
            continue
        for planet, by_player in sorted(system.planet_units.items()):
            types = [bt for bt in _GROUND if by_player.get(player_id, {}).get(bt, 0) > 0]
            if types:
                sources.append((position, planet, types))
    return sources


@faction_components.window_use("leader", COMMANDER)
def _commander_window(state: GameState, registry: StaticDataRegistry, player_id: str) -> str | None:
    inv = state.invasion
    if inv is None or inv.phase is not InvasionPhase.COMMIT or inv.attacker != player_id:
        return "Use G'hom Sek'kus during your Commit Ground Forces step."
    if active_effects.has_effect(state, player_id, COMMANDER_USED):
        return "G'hom Sek'kus was already used in this invasion."
    if not _commander_sources(state, registry, player_id):
        return "You have no ground forces on eligible planets."
    return None


@register_effect_inputs(f"leaders:{COMMANDER}")
def commander_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Dla każdej planety-źródła: „typ → planeta celu” albo „none” (najwyżej 1 jednostka)."""
    inv = state.invasion
    if inv is None:
        return []
    targets = invasion.system_planets(state, registry, inv.position)
    inputs: list[dict[str, Any]] = []
    for position, planet, types in _commander_sources(state, registry, player_id):
        options = [oi.option(_NONE, "None")]
        for base_type in types:
            for dest in targets:
                if position == inv.position and dest == planet:
                    continue
                name = registry.planets[dest].name if dest in registry.planets else dest
                options.append(oi.option(
                    f"{base_type}>{dest}",
                    f"{unit_name(state, registry, player_id, base_type)} -> {name}",
                    meta=oi.unit_at(state, player_id, base_type, planet=dest),
                ))
        source_name = registry.planets[planet].name if planet in registry.planets else planet
        inputs.append(oi.choice(f"src:{position}:{planet}", f"From {source_name}", options))
    return inputs


def _rift_survivors(
    state: GameState, player_id: str, moves: list[tuple[str, str, str, str]]
) -> list[tuple[str, str, str, str]]:
    """F_norr: siły wychodzące z systemu z gravity rift rzucają; usunięte nie lądują."""
    inv = state.invasion
    grid = board_graph.bound_grid() or HexGrid()
    leaving = [
        m for m in moves
        if inv is not None and m[0] != inv.position and movement.is_gravity_rift(grid, m[0])
    ]
    if not leaving:
        return moves
    units: dict[str, int] = {}
    for _pos, _planet, base_type, _dest in leaving:
        units[base_type] = units.get(base_type, 0) + 1
    lost = movement.roll_rift_exit(state, player_id, units)
    kept: list[tuple[str, str, str, str]] = []
    for move in moves:
        position, planet, base_type, _dest = move
        if move in leaving and lost.get(base_type, 0) > 0:
            lost[base_type] -= 1
            unit_ops.remove_units(
                state, state.systems[position], planet, player_id, base_type, 1,
                UnitCause.REMOVED,
            )
            continue
        kept.append(move)
    return kept


@register_effect(f"leaders:{COMMANDER}")
def ghom_sekkus(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """G'hom Sek'kus: During the "Commit Ground Forces" step: You can commit (move) up to 1 ground
    force from each planet in the active system and each planet in adjacent systems that do not
    contain 1 of your command tokens."""
    moves: list[tuple[str, str, str, str]] = []
    for key, value in params.items():
        if not key.startswith("src:") or value in (None, _NONE):
            continue
        _, position, planet = key.split(":", 2)
        base_type, dest = str(value).split(">", 1)
        moves.append((position, planet, base_type, dest))
    if not moves:
        raise ValueError("Choose at least 1 ground force to commit.")
    moves = _rift_survivors(state, player_id, moves)
    if moves:
        invasion.apply_commit_from_planets(state, registry, moves)
    active_effects.add_effect(state, COMMANDER_USED, Duration.INVASION, owner=player_id)


# ----------------------------------------------------------------- Sh'val, Harbinger (hero)


@faction_components.window_use("leader", HERO)
def _hero_window(state: GameState, _registry: StaticDataRegistry, player_id: str) -> str | None:
    if (
        state.phase is not Phase.ACTION
        or state.active_player_id != player_id
        or state.tactical_step is not TacticalStep.MOVEMENT
        or not state.tactical_moved
    ):
        return "Use Tekklar Conditioning right after you move ships into the active system."
    return None


@register_effect(f"leaders:{HERO}")
def tekklar_conditioning(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Sh'val, Harbinger: After you move ships into the active system: You may skip directly to the
    "Commit Ground Forces" step. If you do, after you commit ground forces to land on planets, purge
    this card and return each of your ships in the active system to your reinforcements."""
    active_effects.add_effect(state, HERO_EFFECT, Duration.TACTICAL_ACTION, owner=player_id)
    ion_storm.flip_used(state)  # koniec kroku Move Ships (jak tactical.set_step)
    state.tactical_step = TacticalStep.INVASION
    state.active_combat = None
    state.invasion = None
    state.exploration = None


@register(
    POINT_INVASION_SKIP_BOMBARDMENT, HookSource(SOURCE_EFFECT, HERO_EFFECT), HookKind.PERMIT
)
def hero_skips_bombardment(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return True


@on_event(
    GameEvent.UNITS_COMMITTED, Moment.AFTER, HookSource(SOURCE_EFFECT, HERO_EFFECT),
    label="Tekklar Conditioning: ships return",
)
def hero_return_ships(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    if ctx.get("player") != player_id:
        return
    system = state.systems.get(str(ctx.get("position")))
    if system is not None:
        for base_type, count in sorted(system.space_units.get(player_id, {}).items()):
            if count > 0 and is_space_unit(base_type):
                unit_ops.remove_units(
                    state, system, "space", player_id, base_type, count, UnitCause.REMOVED
                )
    active_effects.remove_by_key(state, HERO_EFFECT, owner=player_id)


# ------------------------------------------------------------------ N'orr Supremacy (BT)


def _won(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("winner") == player_id


def supremacy_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """1 żeton (pula do wyboru) albo badanie ulepszenia jednostki z prerekwizytami (F_norr).

    Prerekwizyty można pominąć zwykłymi skipami (planety ze specjalnością, AIDA, relikty) —
    decyzja użytkownika 2026-11-13 (RULES.md 62.1).
    """
    options: list[dict[str, Any]] = []
    if command_tokens.reinforcements(state, player_id) > 0:
        options += [
            oi.option(f"cc:{pool}", f"Gain 1 command token ({pool} pool)")
            for pool in ("tactical", "fleet", "strategic")
        ]
    for tech in sorted(
        technology.researchable_techs(state, registry, player_id), key=lambda t: t.id
    ):
        if "UNITUPGRADE" in tech.types:
            options.append(oi.option(
                f"tech:{tech.id}", f"{tech.name} - research", ref=("tech", tech.id)
            ))
    inputs = [oi.choice("reward", "N'orr Supremacy", options, always=True)]
    skips = [
        oi.option(planet, card_labels.describe_planet(
            state, registry, planet, effect="skips 1 prerequisite"
        ))
        for planet in technology.specialty_planets(state, registry, player_id)
    ]
    if technology.aida_ready(state, player_id):
        skips.append(oi.option(technology.AIDA_SKIP, "AI Development Algorithm (unit upgrades)"))
    skips += [
        oi.option(
            f"{technology.RELIC_SKIP_PREFIX}{relic}",
            f"{card_labels.relic_name(registry, relic)} - ignore 1 prerequisite",
            ref=("relic", relic),
        )
        for relic in technology.ignore_prerequisite_relics(state, player_id)
    ]
    if skips and any(o["value"].startswith("tech:") for o in options):
        inputs.append(oi.multi(
            "skips", "Skips: exhaust to ignore a prerequisite (research only)",
            skips, 0, len(skips),
        ))
    return inputs


@on_event(
    GameEvent.COMBAT_WON, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    condition=_won, decide=True, inputs=supremacy_inputs,
    covers=f"breakthroughs:{BREAKTHROUGH}", label="N'orr Supremacy",
)
def norr_supremacy(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """N'orr Supremacy: After you win a combat, either gain 1 command token or research a unit
    upgrade technology."""
    reward = str(ctx.get("params", {}).get("reward") or "")
    if reward.startswith("cc:"):
        if ctx.get("params", {}).get("skips"):
            raise ValueError("Skips only apply when you research a technology.")
        command_tokens.gain_from_reinforcements(state, player_id, {reward[3:]: 1})
    elif reward.startswith("tech:"):
        registry = _registry()
        raw = ctx.get("params", {}).get("skips") or []
        skips = [str(skip) for skip in raw] if isinstance(raw, list) else []
        plan = technology.plan_research(state, registry, player_id, reward[5:], skips)
        technology.apply_research(state, player_id, plan)
