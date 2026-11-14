"""Legalne cele kart ACTION z grupy „ekonomia" (technologie, relikty, planety) - RULES.md 53.

Jedno liczenie celów dla obu stron: efekt (``action_cards_economy``) WALIDUJE wybór gracza
względem tych samych list, które formularz (``action_card_inputs_economy``) pokazuje jako opcje.
Funkcje są czyste (nie mutują stanu). Reguły i przypadki brzegowe:
``docs/rules_tirules/C_action_cards.md``.
"""

from __future__ import annotations

from src.core import exploration, neighbors, research_offer, technology
from src.core.combat import resolve_unit_variant
from src.core.game_state import GameState, SystemState
from src.core.hooks.card_helpers import controlled
from src.core.models import TechnologyDef
from src.core.planet_stats import planet_stats
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.unit_catalog import is_space_unit

FOCUSED_COST = 4  # Focused Research: „Spend 4 trade goods”

SPACE_DOCK = "spacedock"


def home_planet_ids(state: GameState, registry: StaticDataRegistry) -> set[str]:
    """Planety domowe wszystkich graczy (z arkuszy frakcji; zdobyta planeta domowa nią zostaje)."""
    planets: set[str] = set()
    for player in state.players.values():
        faction = registry.factions.get(player.faction or "")
        if faction is not None:
            planets.update(faction.home_planets)
    return planets


def home_positions(state: GameState, registry: StaticDataRegistry) -> set[str]:
    """Pozycje systemów domowych graczy (system z ich planetą domową).

    ⚠ ZAŁOŻENIE: system domowy rozpoznajemy po planetach domowych z arkusza frakcji (kafel +
    stan), nie po ``home_slot``; systemy minor factions NIE są domowe (C_events).
    """
    homes = home_planet_ids(state, registry)
    positions: set[str] = set()
    for position, system in state.systems.items():
        definition = registry.systems.get(system.system_id)
        on_tile = set(definition.planets) if definition is not None else set()
        if (on_tile | set(system.planet_owners) | set(system.planet_units)) & homes:
            positions.add(position)
    return positions


def neighbor_ids(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    """Sąsiedzi gracza (R_neighbors) w kolejności zasiadania."""
    near = neighbors.neighbors_of(player_id, state, grid_from_state(state, registry))
    return [pid for pid in state.players if pid in near]


# ---------------------------------------------------------------------------- eksploracja


def matching_decks(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    """Talie eksploracji pasujące do cech kontrolowanych planet (bez powtórzeń)."""
    decks: list[str] = []
    for planet in controlled(state, player_id):
        for trait in exploration.planet_traits(registry, planet):
            if trait not in decks:
                decks.append(trait)
    return decks


def probe_systems(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    """Pozycje z żetonem frontier, które są w systemie ze statkiem gracza albo obok niego."""
    ships = {
        position
        for position, system in state.systems.items()
        if any(
            count > 0 and is_space_unit(base_type)
            for base_type, count in system.space_units.get(player_id, {}).items()
        )
    }
    if not ships:
        return []
    grid = grid_from_state(state, registry)
    return [
        position
        for position, system in state.systems.items()
        if system.frontier_token
        and (position in ships or any(grid.are_adjacent(position, near) for near in ships))
    ]


# ------------------------------------------------------------------------------ technologie


def returnable_techs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[TechnologyDef]:
    """Posiadane technologie nie-frakcyjne i nie-ulepszenia jednostek (Divert Funding)."""
    result: list[TechnologyDef] = []
    for tech_id in state.players[player_id].technologies:
        tech = registry.technologies.get(tech_id)
        if tech is not None and not tech.faction and technology.UNIT_UPGRADE not in tech.types:
            result.append(tech)
    return result


def divert_research_options(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[TechnologyDef]:
    """Technologie do zbadania po zwrocie JAKIEJKOLWIEK dozwolonej technologii (suma opcji)."""
    found: dict[str, TechnologyDef] = {}
    for returned in returnable_techs(state, registry, player_id):
        for tech in technology.researchable_techs(state, registry, player_id, without=returned.id):
            if tech.id != returned.id:
                found.setdefault(tech.id, tech)
    return list(found.values())


def focused_research_options(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[TechnologyDef]:
    """Focused Research: technologie do zbadania, gdy gracz pokryje 4 TG (z możliwą zniżką
    Doctor Sucaban przed zapłatą - ``research_offer.potential_discount``); inaczej pusto."""
    if not research_offer.can_afford_trade_goods(state, registry, player_id, FOCUSED_COST):
        return []
    return technology.researchable_techs(state, registry, player_id)


def plagiarize_options(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> dict[str, list[str]]:
    """Technologie do skopiowania: ``{tech_id: [sąsiedzi, którzy ją mają]}``.

    Tylko nie-frakcyjne technologie z talii gracza, których jeszcze nie ma (C_action_cards:
    frakcyjnego ulepszenia nie wolno wziąć w wersji generycznej, a wersja generyczna zastąpiona
    frakcyjną nie leży w talii gracza).
    """
    player = state.players[player_id]
    pool = technology.tech_pool(state, registry, player_id)
    result: dict[str, list[str]] = {}
    for neighbor in neighbor_ids(state, registry, player_id):
        for tech_id in state.players[neighbor].technologies:
            tech = registry.technologies.get(tech_id)
            if tech is None or tech.faction or tech_id in player.technologies:
                continue
            if tech_id not in pool:
                continue
            result.setdefault(tech_id, []).append(neighbor)
    return result


# ------------------------------------------------------------------------------- planety


def specialty_planets_owned(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[str]:
    """Własne planety (gotowe lub nie) ze specjalnością technologiczną."""
    result: list[str] = []
    for planet in controlled(state, player_id):
        stats = planet_stats(state, registry, planet)
        if stats is not None and stats.tech_specialties:
            result.append(planet)
    return result


def breakthrough_targets(
    state: GameState, registry: StaticDataRegistry
) -> list[str]:
    """Gracze (także sam kartę grający), którzy mogą jeszcze zdobyć swój przełom."""
    return [
        pid
        for pid, player in state.players.items()
        if registry.breakthrough_for_faction(player.faction) is not None
        and not player.breakthrough_unlocked
    ]


def uprising_targets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str]]:
    """Planety do wyczerpania: ``(planeta, właściciel)`` - cudze, nie-domowe i gotowe."""
    homes = home_planet_ids(state, registry)
    result: list[tuple[str, str]] = []
    for system in state.systems.values():
        for planet, owner in system.planet_owners.items():
            player = state.players.get(owner)
            if player is None or owner == player_id or planet in homes:
                continue
            if planet not in player.exhausted_planets:
                result.append((planet, owner))
    return result


def hazardous_planets(state: GameState, registry: StaticDataRegistry) -> list[tuple[str, str]]:
    """Planety hazardous kontrolowane przez gracza: ``(planeta, kontroler)``.

    ⚠ ZAŁOŻENIE: wyczerpać można tylko planetę z kontrolerem (stan „exhausted" trzyma gracz),
    więc niczyja planeta nie jest celem; cechy z attachmentów nie są uwzględniane.
    """
    result: list[tuple[str, str]] = []
    for system in state.systems.values():
        for planet, owner in system.planet_owners.items():
            traits = exploration.planet_traits(registry, planet)
            if owner in state.players and "hazardous" in traits:
                result.append((planet, owner))
    return result


# --------------------------------------------------------------------------------- system


def bombardment_systems(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[SystemState]:
    """Systemy z jednostką gracza z BOMBARDMENT (wariant jednostki z danych, nie lista w kodzie)."""
    player = state.players[player_id]
    result: list[SystemState] = []
    for system in state.systems.values():
        types = {bt for bt, n in system.space_units.get(player_id, {}).items() if n > 0}
        for by_player in system.planet_units.values():
            types.update(bt for bt, n in by_player.get(player_id, {}).items() if n > 0)
        for base_type in types:
            unit = resolve_unit_variant(registry, player.faction, player.technologies, base_type)
            if unit is not None and unit.bombard_hits_on:
                result.append(system)
                break
    return result


def meltdown_targets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str]]:
    """Cudze doki poza systemami domowymi: ``(planeta, właściciel)``."""
    homes = home_positions(state, registry)
    result: list[tuple[str, str]] = []
    for position, system in state.systems.items():
        if position in homes:
            continue
        for planet, by_player in system.planet_units.items():
            for owner, units in by_player.items():
                if owner != player_id and owner in state.players and units.get(SPACE_DOCK, 0) > 0:
                    result.append((planet, owner))
    return result
