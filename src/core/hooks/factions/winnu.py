"""The Winnu — komplet komponentów frakcji (RULES.md 62.7).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("winnu")``, ``units``).
Rulingi: ``docs/rules_tirules/F_winnu.md``. Struktury stawia
``strategy_cards.common.place_structure`` (limity planety, rezerwa); planety zdobyte w akcji
niesie ``TACTICAL_ACTION/END`` (``gained``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    board_graph,
    cooperative,
    exhaust,
    faction_components,
    leaders,
    production,
    promissory_play,
    rules_hooks,
    strategic_action,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, TacticalStep, WindowType
from src.core.hooks import card_labels
from src.core.legendary_planets import MECATOL_PLANETS
from src.core.planet_stats import is_legendary
from src.core.reaction_cards import OpenWindow, window_provider
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_COMBAT_EXTRA_DICE,
    POINT_COMBAT_ROLL_MODIFIER,
    POINT_CUSTODIANS_FREE,
    POINT_MOVEMENT_EXTRA_ADJACENT,
    POINT_MOVEMENT_MOVE_VALUE,
    POINT_PLANET_SWAP_VALUES,
    POINT_PRODUCTION_COST,
    POINT_SYSTEM_ACTION_WORMHOLES,
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
    register_ability,
    register_ability_inputs,
    register_effect,
    register_effect_inputs,
)
from src.core.strategy_cards import CARDS
from src.core.strategy_cards.common import (
    board_structure_sources,
    needs_board_source,
    place_structure,
    structure_problem,
)
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

FACTION = "winnu"
AGENT = "winnuagent"
COMMANDER = "winnucommander"
HERO = "winnuhero"
FLAGSHIP = "winnu_flagship"
MECH = "winnu_mech"
ACQUIESCENCE = "acq"
BREAKTHROUGH = "winnubt"
LGF = "lgf"
HTP = "htp"

AGENT_CUT = f"leaders:{AGENT}:cut"  # efekt: −2 do łącznego kosztu tej produkcji
HTP_SWAP = f"technologies:{HTP}:swap"  # efekt: zamiana zasobów/wpływu planety (data: planet)
_AGENT_DISCOUNT = 2  # „reduce the combined cost of the produced units by 2”
_COMMANDER_BONUS = 2  # „Apply +2 to the result of each of your unit's combat rolls”
_STRUCTURES = ("pds", "spacedock")
_BOTH = "both"
_NONE = "none"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _name(registry: Any, state: GameState, player_id: str) -> str:
    player = state.players.get(player_id)
    faction = registry.factions.get(player.faction or "") if player is not None else None
    return faction.name if faction is not None else player_id


def _planet_name(registry: Any, planet: str) -> str:
    return registry.planets[planet].name if planet in registry.planets else planet


def _mecatol(state: GameState) -> tuple[str, str] | None:
    """``(pozycja, planeta)`` Mecatol Rex na planszy."""
    for position, system in state.systems.items():
        for planet in MECATOL_PLANETS:
            if planet in system.planet_owners or planet in system.planet_units:
                return position, planet
    registry = rules_hooks.bound_registry()
    if registry is None:
        return None
    for position, system in state.systems.items():
        definition = registry.systems.get(system.system_id)
        for planet in getattr(definition, "planets", None) or []:
            if planet in MECATOL_PLANETS:
                return position, planet
    return None


def _controls_mecatol(state: GameState, player_id: str) -> bool:
    found = _mecatol(state)
    return found is not None and state.systems[found[0]].planet_owners.get(found[1]) == player_id


def _system_planets(state: GameState, position: str) -> list[str]:
    registry = rules_hooks.bound_registry()
    system = state.systems.get(position)
    if system is None:
        return []
    planets = set(system.planet_owners) | set(system.planet_units)
    if registry is not None:
        definition = registry.systems.get(system.system_id)
        planets.update(getattr(definition, "planets", None) or [])
    return sorted(planets)


# ------------------------------------------------------------------------- Blood Ties


@register(
    POINT_CUSTODIANS_FREE, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
    covers="abilities:blood_ties",
)
def blood_ties(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Blood Ties: You do not have to spend influence to remove the custodians token from Mecatol
    Rex. (Siły naziemne i tak trzeba zadeklarować — F_winnu.)"""
    return True


# -------------------------------------------------------------- Reclamation + Reclaimer


def _structure_options(state: GameState, player_id: str, planet: str) -> list[str]:
    return [
        s for s in _STRUCTURES
        if structure_problem(state, player_id, planet, s, allow_board=True) is None
    ]


_STRUCTURE_NAME = {"pds": "PDS", "spacedock": "space dock"}


def _variants(
    state: GameState, registry: Any, player_id: str, planet: str, structure: str
) -> list[tuple[str, str]]:
    """Warianty postawienia struktury: z rezerwy albo — gdy pusta — zdjęta z planszy
    (R_component_limitations; F_winnu: „may remove a unit from any system that does not contain
    one of their command tokens”). Wartość ``<typ>`` albo ``<typ><<planeta-źródło>``."""
    name = _STRUCTURE_NAME[structure]
    if not needs_board_source(state, player_id, structure):
        return [(structure, f"1 {name}")]
    return [
        (f"{structure}<{src}", f"1 {name} moved from {_planet_name(registry, src)}")
        for src in board_structure_sources(state, player_id, structure, planet)
    ]


def _place_parts(state: GameState, player_id: str, planet: str, value: str) -> None:
    """Kładzie struktury z wartości opcji (``pds``, ``spacedock<źródło>``, połączone ``+``)."""
    for part in value.split("+"):
        structure, _, source = part.partition("<")
        if structure not in _STRUCTURES:
            raise ValueError(f"Unknown structure: {structure}.")
        place_structure(state, player_id, planet, structure, source=source or None)


def _gained_mecatol(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    planet = next((p for p in ctx.get("gained") or [] if p in MECATOL_PLANETS), None)
    return (
        ctx.get("player") == player_id
        and planet is not None
        and bool(_structure_options(state, player_id, planet))
    )


def reclamation_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    planet = next(p for p in ctx.get("gained") or [] if p in MECATOL_PLANETS)
    able = _structure_options(state, player_id, planet)
    per = {s: _variants(state, registry, player_id, planet, s) for s in able}
    options: list[dict[str, Any]] = []
    if len(able) == len(_STRUCTURES):
        options += [
            oi.option(f"{pv}+{dv}", f"{pl} and {dl}")
            for pv, pl in per["pds"]
            for dv, dl in per["spacedock"]
        ]
    options += [oi.option(v, label) for s in able for v, label in per[s]]
    return [oi.choice("place", "Place on Mecatol Rex", options, always=True)]


@on_event(
    GameEvent.TACTICAL_ACTION, Moment.END, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_gained_mecatol, inputs=reclamation_inputs,
    covers="abilities:reclamation", label="Reclamation: structures on Mecatol Rex",
)
def reclamation(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Reclamation: After you resolve a tactical action during which you gained control of Mecatol
    Rex: You may place 1 PDS and 1 space dock from your reinforcements on Mecatol Rex.
    (Pusta rezerwa: struktura zdjęta z systemu bez własnego żetonu — F_winnu.)"""
    planet = next(p for p in ctx.get("gained") or [] if p in MECATOL_PLANETS)
    value = str(ctx.get("params", {}).get("place") or f"{_STRUCTURES[0]}+{_STRUCTURES[1]}")
    _place_parts(state, player_id, planet, value)


def _reclaimers_on(state: GameState, player_id: str, planet: str) -> int:
    for system in state.systems.values():
        count = system.planet_units.get(planet, {}).get(player_id, {}).get("mech", 0)
        if count:
            return int(count)
    return 0


def _reclaimer_planets(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> list[str]:
    return [
        planet for planet in ctx.get("gained") or []
        if _reclaimers_on(state, player_id, planet) and _structure_options(state, player_id, planet)
    ]


def _reclaimer_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and bool(_reclaimer_planets(state, player_id, ctx))


_SKIP = "skip"


def reclaimer_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Po jednym wyborze na KAŻDEGO Reclaimera na zdobytej planecie (F_winnu: „may place a
    structure for each one", w limicie struktur na planecie - sprawdza ``place_structure``)."""
    inputs: list[dict[str, Any]] = []
    for planet in _reclaimer_planets(state, player_id, ctx):
        options = [oi.option(_SKIP, "Place nothing")] + [
            oi.option(value, label)
            for s in _structure_options(state, player_id, planet)
            for value, label in _variants(state, registry, player_id, planet, s)
        ]
        name = _planet_name(registry, planet)
        for index in range(_reclaimers_on(state, player_id, planet)):
            inputs.append(oi.choice(
                f"place:{planet}:{index}", f"Reclaimer {index + 1} on {name}", options,
                always=True,
            ))
    return inputs


@on_event(
    GameEvent.TACTICAL_ACTION, Moment.END, HookSource(SOURCE_UNIT, MECH),
    optional=True, condition=_reclaimer_ready, inputs=reclaimer_inputs,
    covers=f"units:{MECH}", label="Reclaimer: PDS or space dock",
)
def reclaimer(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Reclaimer: After you resolve a tactical action where you gained control of this planet, you
    may place 1 PDS or 1 Space Dock from your reinforcements on this planet.
    (Każdy Reclaimer osobno; pusta rezerwa: struktura zdjęta z systemu bez żetonu — F_winnu.)"""
    params = ctx.get("params", {})
    planets = set(_reclaimer_planets(state, player_id, ctx))
    picks = [
        (key.split(":")[1], str(value)) for key, value in sorted(params.items())
        if key.startswith("place:") and value and value != _SKIP
    ]
    if any(planet not in planets or "+" in value for planet, value in picks):
        raise ValueError("Choose a planet you gained with a Reclaimer on it.")
    for planet, value in picks:
        _place_parts(state, player_id, planet, value)


# ------------------------------------------------------------- Lazax Gate Folding


@register(
    POINT_MOVEMENT_EXTRA_ADJACENT, HookSource(SOURCE_TECHNOLOGY, LGF), HookKind.FORBID,
    covers=f"technologies:{LGF}",
)
def lazax_gate_folding(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> set[str]:
    """Lazax Gate Folding: During your tactical actions, if you do not control Mecatol Rex, treat
    its system as if it has both an α and β wormhole. (Ruch Winnu + ``action_adjacency``:
    Deep Space Cannon, odwroty i sąsiedztwo graczy w tej akcji — F_winnu.)"""
    found = _mecatol(state)
    grid = board_graph.bound_grid()
    if found is None or grid is None or _controls_mecatol(state, player_id):
        return set()
    mecatol = found[0]
    gates = grid.wormhole_positions("alpha") | grid.wormhole_positions("beta")
    position = str(ctx.get("position"))
    if position == mecatol:
        return {p for p in gates if p != mecatol}
    return {mecatol} if position in gates else set()


@register(
    POINT_SYSTEM_ACTION_WORMHOLES, HookSource(SOURCE_TECHNOLOGY, LGF), HookKind.FORBID,
    covers=f"technologies:{LGF}",
)
def lazax_gate_wormholes(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> set[str]:
    """"treat its system as if it has both an α and β wormhole" - the system counts as containing
    those wormholes during the Winnu tactical action (F_winnu 2.4: Dimensional Splicer there)."""
    found = _mecatol(state)
    if found is None or ctx.get("position") != found[0] or _controls_mecatol(state, player_id):
        return set()
    return {"ALPHA", "BETA"}


@register_effect(f"technologies:{LGF}")
def lazax_gate_folding_action(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """ACTION: If you control Mecatol Rex, exhaust this card to place 1 infantry from your
    reinforcements on Mecatol Rex. (Bez kontroli wolno wyczerpać bez skutku — F_winnu.)"""
    if LGF in state.players[player_id].exhausted_technologies:
        raise ValueError("Lazax Gate Folding is exhausted.")
    exhaust.exhaust_technology(state, player_id, LGF)
    found = _mecatol(state)
    if found is None or not _controls_mecatol(state, player_id):
        return
    left = production.reinforcements_left(state, player_id, "infantry")
    if left is None or left > 0:
        unit_ops.place_units(
            state, state.systems[found[0]], found[1], player_id, "infantry", 1, UnitCause.PLACED
        )


# ---------------------------------------------------------- Hegemonic Trade Policy


def _producing(state: GameState, player_id: str | None = None) -> str | None:
    """Gracz używający TERAZ PRODUCTION (przed pierwszym zamówieniem) albo None."""
    producer = production.production_player(state)
    if producer is None or state.production_used > 0:
        return None
    if production.standalone_grant(state) is None and (
        state.tactical_step is not TacticalStep.PRODUCTION
    ):
        return None
    return producer if player_id is None or producer == player_id else None


def _controlled(state: GameState, player_id: str) -> list[str]:
    return sorted(
        planet
        for system in state.systems.values()
        for planet, owner in system.planet_owners.items()
        if owner == player_id
    )


@register_ability_inputs(HTP)
def htp_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [
        oi.option(p, _planet_name(registry, p), meta={"planet": p})
        for p in _controlled(state, player_id)
    ]
    return [oi.choice("planet", "Planet whose resources and influence swap", options)]


@register_ability(HTP)
def hegemonic_trade_policy(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Hegemonic Trade Policy: Exhaust this card when 1 or more of your units use PRODUCTION; swap
    the resource and influence values of 1 planet you control during that use of Production."""
    if _producing(state, player_id) is None:
        raise ValueError("Use Hegemonic Trade Policy when your units use PRODUCTION.")
    if HTP in state.players[player_id].exhausted_technologies:
        raise ValueError("Hegemonic Trade Policy is exhausted.")
    planet = str(params.get("planet") or "")
    if planet not in _controlled(state, player_id):
        raise ValueError("Choose a planet you control.")
    exhaust.exhaust_technology(state, player_id, HTP)
    scope = Duration.TACTICAL_ACTION if state.tactical_step is not None else Duration.TURN
    active_effects.add_effect(state, HTP_SWAP, scope, owner=player_id, data={"planet": planet})


@register(POINT_PLANET_SWAP_VALUES, HookSource(SOURCE_EFFECT, HTP_SWAP), HookKind.FORBID)
def htp_swapped(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    effects = active_effects.effects_for(state, player_id, HTP_SWAP)
    return {str(e.data.get("planet")) for e in effects}


# ----------------------------------------------------------- Berekar Berekon (agent)


def _berekar_helps(state: GameState, _owner: str) -> list[str]:
    producer = _producing(state)
    return [producer] if producer is not None else []


# Cooperative agent (RULES.md 54.15): the producing player's discount - requested, not pushed.
cooperative.register_pull_component("leader", AGENT, _berekar_helps)


@faction_components.window_use("leader", AGENT)
def _agent_window(state: GameState, _registry: StaticDataRegistry, _player_id: str) -> str | None:
    producer = _producing(state)
    if producer is None:
        return "Use Berekar Berekon when a player's units use PRODUCTION, before they produce."
    if active_effects.has_effect(state, producer, AGENT_CUT):
        return "Berekar Berekon already reduces this production."
    return None


@register_effect(f"leaders:{AGENT}")
def berekar_berekon(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """Berekar Berekon: When 1 or more of a player's units use PRODUCTION: You may exhaust this card
    to reduce the combined cost of the produced units by 2."""
    producer = _producing(state)
    if producer is None:
        raise ValueError("Nobody is using PRODUCTION right now.")
    scope = Duration.TACTICAL_ACTION if state.tactical_step is not None else Duration.TURN
    active_effects.add_effect(state, AGENT_CUT, scope, owner=producer)


@register(POINT_PRODUCTION_COST, HookSource(SOURCE_EFFECT, AGENT_CUT), HookKind.MODIFY)
def agent_cut(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    return -_AGENT_DISCOUNT


# ---------------------------------------------------------- Rickar Rickani (commander)


def _combat_at_mecatol(state: GameState, player_id: str) -> bool:
    combat = state.active_combat
    found = _mecatol(state)
    return (
        combat is not None
        and found is not None
        and combat.position == found[0]
        and player_id in (combat.attacker, combat.defender)
    )


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Control Mecatol Rex or enter into a combat in the Mecatol Rex system."""
    return _controls_mecatol(state, player_id) or _combat_at_mecatol(state, player_id)


@register(
    POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_LEADER, COMMANDER), HookKind.MODIFY,
    covers=f"leaders:{COMMANDER}",
)
def rickar_rickani(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Rickar Rickani: Apply +2 to the result of each of your unit's combat rolls in the Mecatol Rex
    system, your home system, and each system that contains a legendary planet.
    (Raz +2 — F_winnu.)"""
    position = str(ctx.get("position") or "")
    found = _mecatol(state)
    registry = rules_hooks.bound_registry()
    special = (
        (found is not None and position == found[0])
        or position == state.players[player_id].home_position
        or (
            registry is not None
            and any(is_legendary(state, registry, p) for p in _system_planets(state, position))
        )
    )
    return _COMMANDER_BONUS if special else 0


# ------------------------------------------------- Mathis Mathinus — Imperial Seal (hero)


def _mathis_helps(state: GameState, owner: str) -> list[str]:
    return [pid for pid in state.players if pid != owner]


# Cooperative hero (RULES.md 54.15): another player may ask / pay to be among "those players".
# ACTION: requested only during the Winnu's turn; the Winnu picks the card (owner_picks) and the
# chosen players must include the requester.
cooperative.register_pull_component(
    "leader", HERO, _mathis_helps, mutual=True, target="players", owner_picks=True
)


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    cards = [
        oi.option(str(i), card_labels.describe_strategy_card(registry, i), ref=("strategy", i))
        for i in sorted(CARDS)
    ]
    others = [
        oi.option(pid, _name(registry, state, pid)) for pid in state.players if pid != player_id
    ]
    return [
        oi.choice("card", "Primary ability of", cards),
        oi.multi("players", "Players who may perform the secondary", others, 0, len(others)),
    ]


@register_effect(f"leaders:{HERO}")
def imperial_seal(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Mathis Mathinus — Imperial Seal: ACTION: Perform the primary ability of any strategy card.
    Then, choose any number of other players. Those players may perform the secondary ability of
    that strategy card. Then, purge this card. (Wybrani płacą żeton jak zwykle — F_winnu.)"""
    initiative = int(params.get("card") or 0)
    if initiative not in CARDS:
        raise ValueError("Choose a strategy card.")
    chosen = [str(p) for p in params.get("players") or [] if p in state.players and p != player_id]
    strategic_action.begin_hero_primary(
        state, registry, player_id, initiative, chosen, grid=board_graph.bound_grid()
    )


# ------------------------------------------------------------- Acquiescence (notka)


@window_provider
def acquiescence_window(state: GameState) -> list[OpenWindow]:
    """Okno „gdy Winnu rozstrzyga akcję strategiczną” na czas secondary jego karty (tylko gdy
    ktoś trzyma Acquiescence — inne karty tego zdarzenia nie dostają nowego okna)."""
    window = state.pending_window
    active = state.active_player_id
    if (
        window is None
        or window.window_type is not WindowType.STRATEGY_SECONDARY
        or window.context.get(strategic_action.HERO_KEY)  # bohater to nie akcja strategiczna
        or active is None
        or state.players[active].faction != FACTION
        or not any(
            ACQUIESCENCE in p.private.promissory_notes for pid, p in state.players.items()
            if pid != active
        )
    ):
        return []
    # Niejawne: okno istnieje tylko, gdy ktoś trzyma notkę (ręka) - pasek okien go nie pokazuje.
    return [OpenWindow(GameEvent.STRATEGIC_ACTION, Moment.WHEN, {"player": active}, public=False)]


@promissory_play.condition(ACQUIESCENCE)
def _acq_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> str | None:
    window = state.pending_window
    if (
        window is None
        or window.window_type is not WindowType.STRATEGY_SECONDARY
        or window.context.get(strategic_action.HERO_KEY)
    ):
        # Mathis Mathinus nie jest akcją strategiczną (F_winnu/mathis-mathinus-imperial-seal/3).
        return "Acquiescence is played while the Winnu player's strategy card is resolved."
    if player_id not in window.queue or player_id in window.responded:
        return "You already answered this strategy card."
    return None


@register_effect(f"promissory_notes:{ACQUIESCENCE}")
def acquiescence(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Acquiescence: When the Winnu player resolves a strategic action: You do not have to spend or
    place a command token to resolve the secondary ability of that strategy card. Then, return this
    card to the Winnu player. (Construction TE nie kładzie żetonu w systemie.)"""
    strategic_action.grant_no_cost(state, player_id, f"promissory_notes:{ACQUIESCENCE}")


# ------------------------------------------------------ Salai Sai Corian (flagowiec)


@register(
    POINT_COMBAT_EXTRA_DICE, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.MODIFY,
    covers=f"units:{FLAGSHIP}",
)
def salai_sai_corian(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Salai Sai Corian: When this unit makes a combat roll, it rolls a number of dice (hit on a 7)
    equal to the number of your opponent's non-fighter ships in this system. (Same myśliwce
    przeciwnika = 0 kości — F_winnu.)"""
    combat = state.active_combat
    if ctx.get("base_type") != "flagship" or ctx.get("kind") != "space" or combat is None:
        return 0
    opponent = combat.defender if player_id == combat.attacker else combat.attacker
    system = state.systems.get(combat.position)
    ships = sum(
        n for bt, n in (system.space_units.get(opponent, {}) if system else {}).items()
        if is_space_unit(bt) and bt != "fighter"
    )
    registry = _registry()
    unit = registry.units.get(FLAGSHIP)
    base = (unit.combat_die_count or 1) if unit is not None else 1
    return ships - base


# ---------------------------------------------------------------- Imperator (BT)


def _sftt_count(state: GameState, player_id: str) -> int:
    registry = _registry()
    count = 0
    for note in state.players[player_id].promissory_notes_in_play:
        try:
            template, _owner = promissory_play.resolve(state, registry, note)
        except ValueError:
            continue
        if template.endswith("sftt"):
            count += 1
    return count


@register(
    POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH), HookKind.MODIFY,
    covers=f"breakthroughs:{BREAKTHROUGH}",
)
def imperator_combat(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Imperator: Apply +1 to the results of each of your unit's combat rolls for each "Support for
    the Throne" in your opponent's play area (także Twoja własna — F_winnu)."""
    combat = state.active_combat
    if combat is None or player_id not in (combat.attacker, combat.defender):
        return 0
    opponent = combat.defender if player_id == combat.attacker else combat.attacker
    return _sftt_count(state, opponent) if opponent in state.players else 0


@register(POINT_MOVEMENT_MOVE_VALUE, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH), HookKind.MODIFY)
def imperator_move(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    """After you activate a system that contains a legendary planet, apply +1 to the move value of 1
    of your ships during this tactical action. Własny przełącznik (``imperator`` w kontekście)
    i flaga ``GameState.imperator_used`` — niezależne od Gravity Drive (decyzja użytkownika:
    obie premie mogą trafić na różne statki albo na ten sam)."""
    registry = rules_hooks.bound_registry()
    active = state.active_system
    if not ctx.get("imperator") or registry is None or active is None:
        return 0
    return 1 if any(is_legendary(state, registry, p) for p in _system_planets(state, active)) else 0

