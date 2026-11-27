"""The Titans of Ul — komplet komponentów frakcji (RULES.md 62.18).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("titans")``, ``units``).
Rulingi: ``docs/rules_tirules/F_ul.md``. Żetony sleeper: ``core/faction_tokens.py`` (RULES.md
61.6). Hel-Titan jako siła naziemna: ``ship_roles.structure_ground_forces``. Gracz decyduje sam
(RULES.md 56).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    board_reinforcements,
    coexistence,
    control,
    cooperative,
    exhaust,
    exploration,
    faction_components,
    faction_tokens,
    invasion,
    invasion_common,
    leaders,
    planet_stats,
    production,
    promissory_play,
    rules_hooks,
    space_cannon,
    triggers,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import CombatStep, GameState, Phase, SystemState
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_PRODUCTION_GAIN_TRADE_GOOD,
    POINT_STATUS_ACTION_CARDS,
    POINT_STRUCTURE_PDS_AS_MECH,
    POINT_UNIT_STRUCTURE_GROUND_FORCES,
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

FACTION = "titans"
AGENT = "titansagent"
COMMANDER = "titanscommander"
HERO = "titanshero"
FLAGSHIP = "titans_flagship"
MECH = "titans_mech"
HEL_TITAN = "titans_pds"
HEL_TITAN_II = "titans_pds2"
HT2 = "ht2"
SE2 = "se2"
TERRAFORM = "terraform"
BREAKTHROUGH = "titansbt"
ELYSIUM = "elysium"
MECATOL = "mr"

SLEEPER = faction_tokens.SLEEPER
SNAPSHOT = "abilities:awaken:snapshot"  # żetony i PDS w chwili aktywacji (Duration.TACTICAL_ACTION)
CONSENT = f"breakthroughs:{BREAKTHROUGH}"  # prośba Slumberstate do kontrolera planety
_PDS = "pds"
_SPACE = "space"
_STRUCTURES = ("pds", "spacedock")
_PDS_PER_PLANET = 2  # F_ul mech 3: „cannot place a PDS on a planet that already has two”
_STRUCTURES_TO_UNLOCK = 5  # „Have 5 structures on the game board.”
_SUPPLY = "supply"
_KEEP, _AS_PDS, _AS_MECH = "keep", "pds", "mech"
_TOKEN = "sleeper:"  # pole Awaken: co zrobić z żetonem na planecie
_COEXIST = "coexist:"  # pole Awaken: Slumberstate - koegzystencja zamiast walki (zdanie 1)
_YES, _NO = "coexist", "combat"
_FROM = "from:"  # pole Awaken: skąd PDS przy pustej rezerwie
_ALLOW, _REFUSE = "allow", "refuse"

rules_hooks.declare_data_driven(f"technologies:{SE2}")  # Saturn Engine II: statystyki z danych
# Coalescence: walkę wywołuje reguła bazowa - statki w aktywnym systemie (walka kosmiczna) i
# sporna planeta bez lądowania (``invasion._contested`` + Hel-Titan jako siła naziemna).
rules_hooks.declare_core_rule("abilities:coalescence")


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _planet_name(planet: str) -> str:
    definition = _registry().planets.get(planet)
    return definition.name if definition is not None and definition.name else planet


def _faction_name(state: GameState, player_id: str) -> str:
    player = state.players.get(player_id)
    faction = _registry().factions.get(player.faction or "") if player is not None else None
    return faction.name if faction is not None else player_id


def _own_pds(system: SystemState | None, player_id: str, planet: str) -> int:
    return unit_ops.count_in_zone(system, planet, player_id, _PDS)


# ------------------------------------------------------------ Hel-Titan (PDS), Hecatoncheires


@register(POINT_UNIT_STRUCTURE_GROUND_FORCES, HookSource(SOURCE_UNIT, HEL_TITAN), HookKind.FORBID,
          covers=f"units:{HEL_TITAN}")
@register(POINT_UNIT_STRUCTURE_GROUND_FORCES, HookSource(SOURCE_UNIT, HEL_TITAN_II),
          HookKind.FORBID, covers=f"technologies:{HT2}")
def hel_titan(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Hel-Titan I/II: This unit is treated as both a structure and a ground force. It cannot be
    transported. (Wartości i SPACE CANNON na sąsiednie systemy - dane jednostki.)"""
    return {_PDS}


@register(POINT_STRUCTURE_PDS_AS_MECH, HookSource(SOURCE_UNIT, MECH), HookKind.PERMIT,
          covers=f"units:{MECH}")
def hecatoncheires(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Hecatoncheires: DEPLOY: When you would place a PDS on a planet, you may place 1 mech and
    1 infantry on that planet instead.

    Warunki: ``strategy_cards.common._mech_instead_problem``."""
    return True


def _mech_possible(state: GameState, player_id: str) -> bool:
    """Mech w rezerwie i aktywny DEPLOY (F_ul mech 2)."""
    left = production.reinforcements_left(state, player_id, "mech")
    return rules_hooks.permits(POINT_STRUCTURE_PDS_AS_MECH, state, player_id) and (
        left is None or left > 0
    )


# ------------------------------------------------------------------------------ Terragenesis


def _terragenesis_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    planet = str(ctx.get("planet") or "")
    return (
        ctx.get("player") == player_id
        and bool(planet)
        and faction_tokens.on_planet(state, planet, SLEEPER) is None
        and bool(_terragenesis_sources(state, player_id))
    )


def _token_sources(state: GameState, player_id: str) -> list[dict[str, Any]]:
    """Skąd wziąć żeton: pula albo leżący żeton gracza (wartość = planeta - klik na mapie)."""
    options: list[dict[str, Any]] = []
    if faction_tokens.supply_left(state, player_id, SLEEPER) > 0:
        options.append(oi.option(_SUPPLY, "From your reinforcements"))
    for _position, zone in faction_tokens.tokens_of(state, player_id, SLEEPER):
        if zone != _SPACE:
            options.append(oi.option(zone, f"Move the sleeper from {_planet_name(zone)}",
                                     ref=("planet", zone)))
    return options


def _terragenesis_sources(state: GameState, player_id: str) -> list[dict[str, Any]]:
    """Terragenesis sources: the pool while it has tokens; moving a placed token only once all
    sleeper tokens are on the board (F_ul terragenesis 2)."""
    options = _token_sources(state, player_id)
    if faction_tokens.supply_left(state, player_id, SLEEPER) > 0:
        return [o for o in options if o["value"] == _SUPPLY]
    return options


def terragenesis_inputs(
    state: GameState, _registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options = _terragenesis_sources(state, player_id)
    return [oi.choice("source", "Sleeper token to place", options, auto=_auto_source(options))]


def _auto_source(options: list[dict[str, Any]]) -> Any:
    """„Auto” źródła żetonu: pula, a bez niej pierwszy leżący żeton."""
    return options[0]["value"] if options else None


def _put_sleeper(state: GameState, player_id: str, planet: str, source: str) -> None:
    """Kładzie żeton z puli (``source="supply"``) albo przenosi leżący z planety ``source``."""
    position = faction_tokens.planet_position(state, planet)
    if position is None:
        raise ValueError(f"Unknown planet {planet}.")
    if source == _SUPPLY:
        faction_tokens.place(state, player_id, SLEEPER, position, planet)
        return
    origin = faction_tokens.planet_position(state, source)
    if origin is None:
        raise ValueError(f"Unknown planet {source}.")
    faction_tokens.move(state, player_id, SLEEPER, (origin, source), position, planet)


@on_event(
    GameEvent.PLANET_EXPLORED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_terragenesis_ready, inputs=terragenesis_inputs,
    covers="abilities:terragenesis", label="Terragenesis: place a sleeper token",
)
def terragenesis(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Terragenesis: After you explore a planet that does not have a sleeper token: You may place
    or move 1 sleeper token onto that planet."""
    allowed = [o["value"] for o in _terragenesis_sources(state, player_id)]
    source = str(ctx.get("params", {}).get("source") or (allowed[0] if allowed else _SUPPLY))
    if source not in allowed:
        raise ValueError(
            "You may move a sleeper token only once all your sleeper tokens are on the board."
        )
    _put_sleeper(state, player_id, str(ctx["planet"]), source)


# ------------------------------------------------------------------- Awaken / Ouranos (DEPLOY)


def _activating_self(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


@on_event(GameEvent.SYSTEM_ACTIVATED, Moment.WHEN, HookSource(SOURCE_FACTION, FACTION),
          condition=_activating_self, label="Awaken: tokens at activation")
def activation_snapshot(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Migawka chwili aktywacji: żetony sleeper i PDS gracza w systemie. Awaken i Ouranos
    widzą tylko je (R_abilities; F_ul awaken 1-2, ouranos 1-2)."""
    position = str(ctx["position"])
    system = state.systems.get(position)
    if system is None:
        return
    sleepers = sorted(
        zone for zone, kinds in system.faction_tokens.items()
        if zone != _SPACE and kinds.get(SLEEPER) == player_id
    )
    pds = sorted(p for p in system.planet_units if _own_pds(system, player_id, p) > 0)
    if sleepers or pds:
        active_effects.add_effect(
            state, SNAPSHOT, Duration.TACTICAL_ACTION, owner=player_id,
            data={"position": position, "sleepers": sleepers, "pds": pds},
        )


def _snapshot(state: GameState, player_id: str, position: str) -> dict[str, Any]:
    for effect in active_effects.effects_for(state, player_id, SNAPSHOT):
        if effect.owner == player_id and effect.data.get("position") == position:
            return dict(effect.data)
    return {}


def awaken_sleepers(state: GameState, player_id: str, position: str) -> list[str]:
    """Planety z żetonem gracza, który leżał już w chwili aktywacji i nadal leży."""
    return [
        planet for planet in _snapshot(state, player_id, position).get("sleepers", [])
        if faction_tokens.owner_at(state, position, planet, SLEEPER) == player_id
    ]


def _awaken_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and bool(
        awaken_sleepers(state, player_id, str(ctx.get("position")))
    )


def _pds_open(state: GameState, player_id: str, position: str, planet: str) -> bool:
    """Czy na planetę może trafić PDS gracza (limit 2, Demilitarized Zone, rezerwa lub plansza)."""
    system = state.systems.get(position)
    if _own_pds(system, player_id, planet) >= _PDS_PER_PLANET:
        return False
    if planet_stats.is_demilitarized(state, planet):
        return False
    return board_reinforcements.can_place(state, player_id, _PDS)


def awaken_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Dla każdego żetonu: PDS / mech i piechota / zostaw; przy pustej rezerwie - skąd PDS."""
    position = str(ctx.get("position"))
    sleepers = awaken_sleepers(state, player_id, position)
    inputs: list[dict[str, Any]] = []
    mech = _mech_possible(state, player_id)
    for planet in sleepers:
        options = []
        if _pds_open(state, player_id, position, planet):
            options.append(oi.option(_AS_PDS, "Replace with a Hel-Titan (PDS)"))
            if mech:
                options.append(oi.option(_AS_MECH, "Hecatoncheires and 1 infantry instead"))
        options.append(oi.option(_KEEP, "Keep the sleeper token"))
        inputs.append(oi.choice(f"{_TOKEN}{planet}", f"Sleeper on {_planet_name(planet)}",
                                options, always=True, auto=options[0]["value"]))
        if _slumber_coexist_possible(state, player_id, position, planet):
            inputs.append(oi.choice(
                f"{_COEXIST}{planet}", f"Ground combat on {_planet_name(planet)}", [
                    oi.option(_YES, "Coexist instead (Slumberstate Computing)"),
                    oi.option(_NO, "Fight the ground combat"),
                ], hint="Slumberstate Computing: only if you commit no other units to this "
                "planet.", always=True, auto=_YES,  # ⚠️ ZAŁOŻENIE 62.18: „Auto” = koegzystencja
            ))
    left = production.reinforcements_left(state, player_id, _PDS)
    if left is not None and left < len(sleepers):
        for planet in sleepers:
            sources = [oi.option(_SUPPLY, "From your reinforcements")] + [
                oi.option(src, label)
                for src, label in board_reinforcements.source_options(
                    state, registry, player_id, _PDS, exclude=f"{position}|{planet}"
                )
            ]
            inputs.append(oi.choice(
                f"{_FROM}{planet}", f"PDS for {_planet_name(planet)} if reinforcements run out",
                sources, hint="R_component_limitations: a PDS from a system without your command "
                "token is moved instead.", auto=_SUPPLY,
            ))
    return inputs


def _has_slumberstate(state: GameState, player_id: str) -> bool:
    source = HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH)
    return source in rules_hooks.owned_sources(state, player_id)


def _rival_ground_forces(state: GameState, player_id: str, position: str, planet: str) -> bool:
    """Czy na planecie stoją siły naziemne innego gracza (Coalescence wywoła walkę naziemną)."""
    system = state.systems.get(position)
    if system is None:
        return False
    return any(
        invasion_common._ground_in_zone(
            system, planet, pid, invasion_common.structure_ground_types(state, pid)
        )
        for pid in system.planet_units.get(planet, {})
        if pid != player_id
    )


def _slumber_coexist_possible(
    state: GameState, player_id: str, position: str, planet: str
) -> bool:
    """Slumberstate zdanie 1: Awaken na planecie z cudzymi siłami naziemnymi = walka z
    Coalescence, którą Titans mogą zamienić na koegzystencję (planeta nie jest ich)."""
    system = state.systems.get(position)
    return (
        _has_slumberstate(state, player_id)
        and system is not None
        and system.planet_owners.get(planet) != player_id
        and _rival_ground_forces(state, player_id, position, planet)
    )


def _settle_planet(state: GameState, player_id: str, position: str, planet: str) -> None:
    """Jednostki Titans na planecie po Awaken (F_ul awaken 4): przeciwnik bez sił naziemnych traci
    struktury i planetę; z siłami naziemnymi - walka w kroku Invasion (Coalescence)."""
    system = state.systems[position]
    others = [
        pid for pid, units in system.planet_units.get(planet, {}).items()
        if pid != player_id and any(n > 0 for n in units.values())
    ]
    if any(
        invasion_common._ground_in_zone(
            system, planet, pid, invasion_common.structure_ground_types(state, pid)
        )
        for pid in others
    ):
        return
    for pid in others:
        for base_type, count in list(system.planet_units.get(planet, {}).get(pid, {}).items()):
            if count > 0 and base_type in _STRUCTURES:
                unit_ops.remove_units(state, system, planet, pid, base_type, count,
                                      UnitCause.DESTROYED)
    if system.planet_owners.get(planet) != player_id:
        control.set_planet_control(state, position, planet, player_id, _registry())


def _place_pds(
    state: GameState, player_id: str, position: str, planet: str, source: str | None
) -> None:
    system = state.systems[position]
    if not _pds_open(state, player_id, position, planet):
        raise ValueError(f"You cannot place a PDS on {_planet_name(planet)}.")
    board_reinforcements.place_unit(state, system, planet, player_id, _PDS, source=source)


def _place_mech(
    state: GameState, player_id: str, position: str, planet: str, source: str | None
) -> None:
    """Hecatoncheires zamiast PDS: PDS musi dać się postawić (F_ul mech 3-4) - przy pustej
    rezerwie wraca z planszy do rezerwy i tam zostaje."""
    if not _pds_open(state, player_id, position, planet) or not _mech_possible(state, player_id):
        raise ValueError(f"You cannot deploy a mech on {_planet_name(planet)}.")
    if board_reinforcements.needs_board_source(state, player_id, _PDS):
        if source is None:
            raise ValueError("Choose a PDS on the board to return to your reinforcements.")
        board_reinforcements.take_from_board(state, player_id, _PDS, source)
    system = state.systems[position]
    unit_ops.place_units(state, system, planet, player_id, "mech", 1, UnitCause.PLACED)
    unit_ops.place_units(state, system, planet, player_id, "infantry", 1, UnitCause.PLACED)


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_awaken_ready, inputs=awaken_inputs, covers="abilities:awaken",
    label="Awaken: replace sleeper tokens",
)
def awaken(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Awaken: After you activate a system that contains 1 or more of your sleeper tokens: You may
    replace each of those tokens with 1 PDS from your reinforcements. (⚠️ ZAŁOŻENIE 62.18: każdy
    żeton osobno; „Auto” = PDS.)

    Slumberstate Computing (zdanie 1): When COALESCENCE results in a ground combat, if you commit
    no other units, you may choose for your units to coexist instead. Wybór pada w tym oknie
    (pole ``coexist:<planeta>``); zaangażowanie sił na tę planetę w kroku Commit go unieważnia
    (``coexistence.fighting``, RULES.md 40.1 I7b)."""
    position = str(ctx["position"])
    params = ctx.get("params", {})
    for planet in awaken_sleepers(state, player_id, position):
        choice = str(params.get(f"{_TOKEN}{planet}") or _AS_PDS)
        if choice == _KEEP:
            continue
        raw_source = params.get(f"{_FROM}{planet}")
        source = str(raw_source) if raw_source and raw_source != _SUPPLY else None
        if choice == _AS_MECH:
            _place_mech(state, player_id, position, planet, source)
        else:
            _place_pds(state, player_id, position, planet, source)
        faction_tokens.remove(state, position, planet, SLEEPER)
        _settle_planet(state, player_id, position, planet)
        if (
            str(params.get(f"{_COEXIST}{planet}") or _YES) == _YES
            and _slumber_coexist_possible(state, player_id, position, planet)
        ):
            coexistence.choose(state, position, planet, player_id)


def _ouranos_pds(state: GameState, player_id: str, position: str) -> list[str]:
    """PDS gracza z chwili aktywacji, które nadal stoją (F_ul ouranos 1-2)."""
    system = state.systems.get(position)
    return [
        planet for planet in _snapshot(state, player_id, position).get("pds", [])
        if _own_pds(system, player_id, planet) > 0
    ]


def _ouranos_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    left = production.reinforcements_left(state, player_id, "flagship")
    return (
        ctx.get("player") == player_id
        and (left is None or left > 0)
        and not unit_ops.place_forbidden(state, player_id, "flagship")
        and bool(_ouranos_pds(state, player_id, str(ctx.get("position"))))
    )


def ouranos_inputs(
    state: GameState, _registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    position = str(ctx.get("position"))
    options = [
        oi.option(planet, f"PDS on {_planet_name(planet)}", ref=("planet", planet))
        for planet in _ouranos_pds(state, player_id, position)
    ]
    return [oi.choice("pds", "PDS to replace with Ouranos", options,
                      auto=options[0]["value"] if options else None)]


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_UNIT, FLAGSHIP),
    optional=True, condition=_ouranos_ready, inputs=ouranos_inputs, covers=f"units:{FLAGSHIP}",
    label="Ouranos: replace a PDS",
)
def ouranos(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Ouranos: DEPLOY: After you activate a system that contains 1 or more of your PDS, you may
    replace 1 of those PDS with this unit."""
    position = str(ctx["position"])
    planet = str(ctx.get("params", {}).get("pds") or "")
    if planet not in _ouranos_pds(state, player_id, position):
        raise ValueError("Choose one of your PDS that was in the system when you activated it.")
    system = state.systems[position]
    unit_ops.remove_units(state, system, planet, player_id, _PDS, 1, UnitCause.REMOVED)
    unit_ops.place_units(state, system, _SPACE, player_id, "flagship", 1, UnitCause.PLACED)


# ---------------------------------------------------------------------------- Tellurian


def pending_hit_targets(state: GameState) -> list[tuple[str, str, str]]:
    """Trafienia czekające na przypisanie: ``[(klucz, gracz-cel, opis)]`` (RULES.md 62.18)."""
    found: list[tuple[str, str, str]] = []
    combat = state.active_combat
    if combat is not None and combat.step is CombatStep.ASSIGN:
        for pid in sorted(combat.pending_hits):
            if combat.pending_hits[pid] > 0 and pid in state.players:
                found.append((f"combat:{pid}", pid, f"{combat.kind} combat"))
    shot = space_cannon.pending_hits(state)
    if shot is not None and shot.hits > 0:
        found.append(("cannon", shot.target, "Space Cannon Offense"))
    inv = state.invasion
    if inv is not None:
        for planet in sorted(inv.defense_pending):
            found.append((f"defense:{planet}", inv.attacker,
                          f"Space Cannon Defense on {_planet_name(planet)}"))
        for key in sorted(inv.bombard_pending):
            # Klucz „planeta@gracz” przy koegzystencji - trafienia czekają na tego gracza.
            planet, chosen = invasion.split_bombard_key(key)
            system = state.systems.get(inv.position)
            owners = sorted(
                pid for pid in (system.planet_units.get(planet, {}) if system else {})
                if pid != inv.attacker
            )
            target = chosen or (owners[0] if owners else inv.attacker)
            found.append((f"bombard:{key}", target, f"Bombardment of {_planet_name(planet)}"))
    return found


def _tellurian_helps(state: GameState, _owner: str) -> list[str]:
    return list(dict.fromkeys(target for _key, target, _what in pending_hit_targets(state)))


# Cooperative agent (RULES.md 54.15): cancels a hit on the hit player's units - requested.
cooperative.register_pull_component("leader", AGENT, _tellurian_helps)


@faction_components.window_use("leader", AGENT)
def _agent_window(state: GameState, _registry: StaticDataRegistry, _player_id: str) -> str | None:
    if not pending_hit_targets(state):
        return "Use Tellurian before hits are assigned."
    return None


@register_effect_inputs(f"leaders:{AGENT}")
def agent_inputs(
    state: GameState, _registry: StaticDataRegistry, _player_id: str
) -> list[dict[str, Any]]:
    """Które trafienie anulować (chipy); „Auto” - patrz niżej."""
    targets = pending_hit_targets(state)
    options = [
        oi.option(key, f"{_faction_name(state, target)}: 1 hit from {what}")
        for key, target, what in targets
    ]
    # „Auto”: trafienie we własne jednostki Titans, a bez niego pierwsze z listy.
    auto = next((key for key, target, _what in targets if target == _player_id), None)
    if auto is None and targets:
        auto = targets[0][0]
    return [oi.choice("hit", "Hit to cancel", options, auto=auto)]


@register_effect(f"leaders:{AGENT}")
def tellurian(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Tellurian: Before a hit would be assigned: You may exhaust this card to cancel that hit."""
    targets = {key for key, _target, _what in pending_hit_targets(state)}
    key = str(params.get("hit") or "")
    if key not in targets:
        raise ValueError("Choose a hit that is waiting to be assigned.")
    kind, _, rest = key.partition(":")
    if kind == "combat":
        combat = state.active_combat
        assert combat is not None
        combat.pending_hits[rest] = combat.pending_hits[rest] - 1
    elif kind == "cannon":
        space_cannon.cancel_pending_hits(state, 1)
    elif kind == "defense":
        invasion.cancel_defense_hits(state, rest, 1)
    else:
        invasion.cancel_bombardment_hits(state, rest, 1)


# ---------------------------------------------------------------------------- Tungstantus


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 5 structures on the game board (PDS i doki, także w przestrzeni)."""
    total = 0
    for system in state.systems.values():
        zones = [system.space_units, *(units for units in system.planet_units.values())]
        for zone in zones:
            by_type = zone.get(player_id, {})
            total += sum(by_type.get(bt, 0) for bt in _STRUCTURES)
    return total >= _STRUCTURES_TO_UNLOCK


@register(POINT_PRODUCTION_GAIN_TRADE_GOOD, HookSource(SOURCE_LEADER, COMMANDER),
          HookKind.PERMIT, covers=f"leaders:{COMMANDER}")
def tungstantus(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Tungstantus: When 1 or more of your units use PRODUCTION: You may gain 1 trade good.
    (Przełącznik w oknie produkcji - ``production.produce(commander_trade_good=True)``.)"""
    return True


# ---------------------------------------------------------------- Ul the Progenitor — Geoform


def _elysium_position(state: GameState) -> str | None:
    return faction_tokens.planet_position(state, ELYSIUM)


@faction_components.blocker("leader", HERO)
def _hero_blocked(state: GameState, _registry: StaticDataRegistry, _player_id: str) -> str | None:
    if any(HERO in cards for cards in state.planet_attachments.values()):
        # R_leaders: karta dołączona do planety nie jest purge'owana (RULES.md 61.1) - leży przy
        # Elysium, więc nie da się jej użyć ponownie.
        return "Ul the Progenitor is already attached to Elysium."
    position = _elysium_position(state)
    system = state.systems.get(position) if position is not None else None
    if system is None or ELYSIUM in system.destroyed_planets:
        return "Elysium is not on the game board."
    return None


@register_effect(f"leaders:{HERO}")
def geoform(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """Ul the Progenitor — Geoform: ACTION: Ready Elysium and attach this card to it. Its resource
    and influence values are each increased by 3, and it gains the SPACE CANNON 5(x3) ability as
    if it were a unit. (Wartości i SPACE CANNON - attachment ``titanshero`` z danych.)"""
    position = _elysium_position(state)
    if position is None:
        raise ValueError("Elysium is not on the game board.")
    controller = state.systems[position].planet_owners.get(ELYSIUM)
    if controller in state.players:
        exhaust.ready_planets(state, controller, [ELYSIUM])
    exploration.attach_to_planet(state, ELYSIUM, HERO)


# -------------------------------------------------------------------------------- Terraform


def terraform_targets(state: GameState, player_id: str) -> list[str]:
    """Planety gracza: nie domowe (dowolnego gracza), nie Mecatol Rex."""
    from src.core.hooks.card_targets_economy import home_planet_ids  # lokalnie: moduł kart

    homes = home_planet_ids(state, _registry())
    return sorted(
        planet for planet in state.players[player_id].controlled_planets
        if planet not in homes and planet != MECATOL
    )


@promissory_play.action_blocker(TERRAFORM)
def _terraform_blocked(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> str | None:
    if not terraform_targets(state, player_id):
        return "You control no non-home planet other than Mecatol Rex."
    return None


@register_effect_inputs(f"promissory_notes:{TERRAFORM}")
def terraform_inputs(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [
        oi.option(planet, _planet_name(planet), ref=("planet", planet))
        for planet in terraform_targets(state, player_id)
    ]
    # „Auto”: planeta o najwyższej sumie zasobów i wpływów.
    best = max(
        terraform_targets(state, player_id),
        key=lambda p: planet_stats.resources_of(state, _registry, p)
        + planet_stats.influence_of(state, _registry, p),
        default=None,
    )
    return [oi.choice("planet", "Planet to terraform", options, auto=best)]


@register_effect(f"promissory_notes:{TERRAFORM}")
def terraform(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Terraform: ACTION: Attach this card to a non-home planet you control other than Mecatol
    Rex. Its resource and influence values are each increased by 1, and it is treated as having
    all 3 planet traits (cultural, hazardous, and industrial). (Leży przy planecie - nie wraca,
    F_ul terraform 1-2; ``promissory_play._dispose``.)"""
    planet = str(params.get("planet") or "")
    if planet not in terraform_targets(state, player_id):
        raise ValueError("Choose a non-home planet you control other than Mecatol Rex.")
    exploration.attach_to_planet(state, planet, TERRAFORM)


# --------------------------------------------------------------------- Slumberstate Computing


def consent_targets(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """``[(planeta, kontroler)]`` cudzych planet bez żetonu sleeper (zdanie 3 przełomu)."""
    found: list[tuple[str, str]] = []
    for system in state.systems.values():
        for planet, owner in system.planet_owners.items():
            if owner == player_id or owner not in state.players:
                continue
            if SLEEPER in system.faction_tokens.get(planet, {}):
                continue
            found.append((planet, owner))
    return sorted(found)


def _slumber_helps(state: GameState, owner: str) -> list[str]:
    return sorted({controller for _planet, controller in consent_targets(state, owner)})


def _planet_holder(state: GameState, owner: str, value: str) -> str | None:
    return dict(consent_targets(state, owner)).get(value)


# Cooperative (RULES.md 54.15): a planet's controller may invite / pay the Titans to place a
# sleeper token there; the Titans keep asking on their own (mutual) and pick the token.
cooperative.register_pull_component(
    "breakthrough", BREAKTHROUGH, _slumber_helps, mutual=True, target="planet",
    target_of=_planet_holder, owner_picks=True,
)


@faction_components.window_use("breakthrough", BREAKTHROUGH, standing=True)
def _slumber_window(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> str | None:
    if state.phase is not Phase.ACTION:
        return "Ask other players during the action phase."
    if not _token_sources(state, player_id):
        return "You have no sleeper token to place."
    if not consent_targets(state, player_id):
        return "No other player controls a planet without a sleeper token."
    return None


@register_effect_inputs(f"breakthroughs:{BREAKTHROUGH}")
def slumber_inputs(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    planets = [
        oi.option(planet, f"{_planet_name(planet)} ({_faction_name(state, owner)})",
                  ref=("planet", planet))
        for planet, owner in consent_targets(state, player_id)
    ]
    return [
        oi.choice("planet", "Planet for a sleeper token (its controller decides)", planets,
                  auto=planets[0]["value"] if planets else None),
        oi.choice("source", "Sleeper token to place", _token_sources(state, player_id),
                  auto=_auto_source(_token_sources(state, player_id))),
    ]


@register_effect(f"breakthroughs:{BREAKTHROUGH}")
def slumberstate_request(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Slumberstate Computing: Other players may allow you to place a sleeper token on a planet
    they control. (Prośba - decyzję podejmuje kontroler planety.)"""
    owners = dict(consent_targets(state, player_id))
    planet = str(params.get("planet") or "")
    source = str(params.get("source") or _SUPPLY)
    if planet not in owners:
        raise ValueError("Choose a planet another player controls that has no sleeper token.")
    if source not in {o["value"] for o in _token_sources(state, player_id)}:
        raise ValueError("Choose a sleeper token you can place.")
    triggers.fire(
        state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "ability": CONSENT, "target": owners[planet],
             "planet": planet, "source": source},
    )


def _consent_decider(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def consent_inputs(
    state: GameState, _registry: Any, _decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    who = _faction_name(state, str(ctx.get("player")))
    planet = _planet_name(str(ctx.get("planet")))
    return [oi.choice("answer", f"{who} asks to place a sleeper token on {planet}", [
        oi.option(_ALLOW, "Allow"), oi.option(_REFUSE, "Refuse"),
    ], always=True, auto=_REFUSE)]  # ⚠️ ZAŁOŻENIE 62.18: „Auto” = odmowa (zgoda to wybór)


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    where={"ability": CONSENT}, decide=True, decider=_consent_decider, inputs=consent_inputs,
    covers=f"breakthroughs:{BREAKTHROUGH}", label="Slumberstate Computing: sleeper token",
)
def slumberstate_consent(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    if str(ctx.get("params", {}).get("answer") or _REFUSE) != _ALLOW:
        return
    planet, source = str(ctx["planet"]), str(ctx["source"])
    if faction_tokens.on_planet(state, planet, SLEEPER) is not None:
        return  # w międzyczasie ktoś położył żeton - nic do zrobienia
    _put_sleeper(state, player_id, planet, source)


# Zdanie 2 dotyczy też gracza BEZ przełomu („you and that player”) - źródło posiada każdy gracz,
# hook sam szuka właściciela Slumberstate.
_COEXIST_CARDS = rules_hooks.declare_rule_source(f"breakthroughs:{BREAKTHROUGH}:coexistence")


@register(
    POINT_STATUS_ACTION_CARDS, _COEXIST_CARDS, HookKind.MODIFY,
    covers=f"breakthroughs:{BREAKTHROUGH}",
)
def slumberstate_cards(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Slumberstate Computing: During the status phase, for each player you are coexisting with,
    you and that player each draw 1 additional action card. (Tylko krok Draw Action Cards -
    jedyny odczyt ``POINT_STATUS_ACTION_CARDS``; F_ul slumberstate-computing 5.)"""
    extra = 0
    for holder in state.players:
        if not _has_slumberstate(state, holder):
            continue
        partners = coexistence.partners(state, holder)
        if holder == player_id:
            extra += len(partners)
        elif player_id in partners:
            extra += 1
    return extra
