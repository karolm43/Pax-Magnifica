"""Sprawdzanie celów (objectives): postęp gracza względem wymagań karty (RULES.md 41.4).

Port logiki AsyncTI4 ``ListPlayerInfoService.getPlayerProgressOnObjective`` /
``getObjectiveThreshold`` na nasz ``GameState`` + ``HexGrid`` + ``StaticDataRegistry``.
Czyste funkcje (bez mutacji). Wynik ``progress`` to liczba porównywana z ``threshold``;
cel jest spełniony, gdy ``progress >= threshold``.

``progress`` zwraca ``None``, gdy stan gry NIE modeluje potrzebnych danych (załączniki
planet, fragmenty reliktów, prawa w grze) — wtedy cel jest „do ręcznego potwierdzenia"
i silnik go nie blokuje (⚠ ZAŁOŻENIE, RULES.md 41.4).

Cele „wydaj X" (Spend…) sprawdzają, czy gracz MA wystarczająco zasobów; samo wydanie
robi ``objective_payment`` przy zdobywaniu celu.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from src.core import coexistence, command_tokens, payment, production
from src.core.game_state import GameState, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.neighbors import neighbors_by_player
from src.core.planet_stats import (
    EffectivePlanets,
    PlanetLookup,
    effective_planets,
    is_legendary,
    planet_stats,
)
from src.core.planet_stats import (
    traits as planet_traits_with_attachments,
)
from src.core.registry import StaticDataRegistry
from src.core.system_planets import planets_of_system

# Progi z AsyncTI4 (``getObjectiveThreshold``); zgodne z tekstami kart w katalogu.
THRESHOLDS: dict[str, int] = {
    # etap I
    "push_boundaries": 2, "outer_rim": 3, "ancient_monuments": 3, "revolutionize": 3,
    "deep_space": 3, "lead": 3, "research_outposts": 3, "infrastructure": 3,
    "make_history": 2, "corner": 4, "become_legend": 4, "master_science": 4,
    "build_defenses": 4, "develop": 2, "diversify": 2, "monument": 8,
    "command_armada": 8, "sway_council": 8, "expand_borders": 6, "intimidate": 2,
    "trade_routes": 5, "amass_wealth": 9, "lost_outposts": 2, "engineer_marvel": 1,
    "raise_fleet": 5,
    # etap II
    "centralize_trade": 10, "conquer": 1, "brain_trust": 5, "golden_age": 16,
    "galvanize": 6, "manipulate_law": 16, "subdue": 11, "unify_colonies": 6,
    "supremacy": 1, "massive_cities": 7, "control_borderlands": 5, "vast_reserves": 18,
    "vast_territories": 5, "protect_border": 5, "distant_lands": 2,
    # tajne (faza statusu)
    "pem": 8, "sai": 1, "syc": 1, "sb": 1, "otf": 9, "mtm": 4, "hrm": 12, "eh": 12,
    "dp": 3, "dhw": 2, "dfat": 1, "te": 1, "ose": 3, "mrm": 4, "mlp": 4, "mp": 4,
    "lsc": 3, "fwm": 3, "fsn": 5, "gamf": 5, "ans": 2, "btgk": 2, "ctr": 6, "csl": 1,
    "eap": 4, "faa": 4,
}

_MAIN_TECH_COLORS = ("BIOTIC", "PROPULSION", "CYBERNETIC", "WARFARE")
_STRUCTURES = ("spacedock", "pds")
_GROUND = ("infantry", "mech")
_TRAITS = ("CULTURAL", "HAZARDOUS", "INDUSTRIAL")
# Cele, w których wydaje się żetony/zasoby (patrz ``objective_payment``).
SPEND_OBJECTIVES = frozenset({
    "trade_routes", "centralize_trade", "lead", "galvanize", "monument", "golden_age",
    "sway_council", "manipulate_law", "amass_wealth", "vast_reserves", "fsn", "dhw",
})


def threshold(objective_id: str, state: GameState) -> int:
    """Próg celu (0 = nieznany cel — brak automatycznego sprawdzania)."""
    if objective_id == "fc":
        return max(len(state.players) - 1, 1)
    return THRESHOLDS.get(objective_id, 0)


# --- Widok pomocniczy ----------------------------------------------------------------------


@dataclass
class View:
    state: GameState
    registry: StaticDataRegistry
    grid: HexGrid
    pid: str
    player: PlayerState = field(init=False)
    homes: dict[str, str] = field(init=False)  # player_id -> pozycja systemu domowego
    # Planety punktowane (bez stacji kosmicznych): kontrolowane + te, na których gracz koegzystuje
    # (R_coexistence 17: koegzystujący uważa planetę za kontrolowaną przy punktowaniu celów).
    owned: list[str] = field(init=False)
    controlled: list[str] = field(init=False)  # tylko kontrolowane (wydawanie - cele „Spend…”)
    planet_pos: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        self.player = self.state.players[self.pid]
        self.homes = {}
        # R_elimination (Notes): dom wyeliminowanego gracza nadal jest systemem domowym.
        seats = [
            *((pid, p.faction) for pid, p in self.state.players.items()),
            *((e.player_id, e.faction) for e in self.state.eliminated_players),
        ]
        for other_id, other_faction in seats:
            faction = self.registry.factions.get(other_faction or "")
            if faction is None or not faction.home_system:
                continue
            for position, system in self.state.systems.items():
                if system.system_id == faction.home_system:
                    self.homes[other_id] = position
                    break
        self.planet_pos = {}
        self.owned = []
        self.controlled = []
        for position, system in self.state.systems.items():
            for planet_id, owner in system.planet_owners.items():
                self.planet_pos[planet_id] = position
                if not self._counts_as_planet(planet_id):
                    continue
                if owner == self.pid:
                    self.controlled.append(planet_id)
                    self.owned.append(planet_id)
                elif coexistence.is_coexisting(self.state, position, planet_id, self.pid):
                    self.owned.append(planet_id)

    def _counts_as_planet(self, planet_id: str) -> bool:
        # R_space_stations: stacje kosmiczne nie są planetami dla celów.
        planet = self.registry.planets.get(planet_id)
        return planet is None or planet.planet_type != "SPACESTATION"

    # -- mapa --
    def my_home(self) -> str | None:
        return self.homes.get(self.pid)

    def other_homes(self) -> list[str]:
        return [pos for pid, pos in self.homes.items() if pid != self.pid]

    def all_homes(self) -> set[str]:
        return set(self.homes.values())

    def planets_of_system(self, position: str) -> list[str]:
        return planets_of_system(self.state, self.registry, position)

    def mecatol(self) -> str | None:
        for position in self.state.systems:
            for planet_id in self.planets_of_system(position):
                planet = self.registry.planets.get(planet_id)
                if planet is not None and planet.planet_type == "MR" and planet_id == "mr":
                    return position
        return None

    def wormholes(self, position: str) -> set[str]:
        system = self.state.systems.get(position)
        definition = self.registry.systems.get(system.system_id) if system else None
        from src.core import board_graph  # lokalnie: lekki moduł, unikamy cyklu

        found = {w.upper() for w in definition.wormholes} if definition else set()
        # Żetony wormhole z kart (np. Gamma Wormhole z eksploracji) liczą się jak wbudowane; tak
        # samo wormhole jednostek (Hil Colish, RULES.md 62.19).
        found |= set(board_graph.unit_wormholes(self.state).get(position, []))
        return found | {w.upper() for w in system.token_wormholes()} if system else found

    def is_anomaly(self, position: str) -> bool:
        return bool(self.grid.anomalies_at(position))

    # -- jednostki --
    def units_in(self, position: str, pid: str | None = None) -> int:
        system = self.state.systems.get(position)
        return _unit_total(system, pid or self.pid) if system else 0

    def ships_in(self, position: str, pid: str | None = None) -> int:
        system = self.state.systems.get(position)
        if system is None:
            return 0
        return sum(system.space_units.get(pid or self.pid, {}).values())

    def non_fighter_ships_in(self, position: str) -> int:
        system = self.state.systems.get(position)
        if system is None:
            return 0
        return sum(
            n for t, n in system.space_units.get(self.pid, {}).items() if t != "fighter"
        )

    def count_units(self, *base_types: str) -> int:
        """Liczba jednostek danych typów gracza na całej planszy (przestrzeń + planety)."""
        total = 0
        for system in self.state.systems.values():
            for base_type in base_types:
                total += system.space_units.get(self.pid, {}).get(base_type, 0)
                for by_player in system.planet_units.values():
                    total += by_player.get(self.pid, {}).get(base_type, 0)
        return total

    def unit_on(self, planet_id: str, base_types: tuple[str, ...]) -> int:
        total = 0
        for system in self.state.systems.values():
            by_type = system.planet_units.get(planet_id, {}).get(self.pid, {})
            total += sum(by_type.get(t, 0) for t in base_types)
        return total
    # -- planety --
    def trait_count(self, trait: str) -> int:
        count = 0
        for planet_id in self.owned:
            # Cechy z danych + z attachmentów (Terraform: wszystkie 3 - RULES.md 62.18).
            traits = set(planet_traits_with_attachments(self.state, self.registry, planet_id))
            if trait.lower() in traits:
                count += 1
        return count

    def planets_with(self, predicate: Callable[[str], bool]) -> int:
        return sum(1 for planet_id in self.owned if predicate(planet_id))

    def in_non_home(self, planet_id: str) -> bool:
        return self.planet_pos.get(planet_id) not in self.all_homes()

    # -- technologie --
    def tech_types(self, tech_id: str) -> list[str]:
        tech = self.registry.technologies.get(tech_id)
        return list(tech.types) if tech is not None else []

    def synergy(self) -> tuple[str, ...] | None:
        """Para kolorów synergii odblokowanego przełomu (R_synergy: działa też przy celach)."""
        from src.core.technology import synergy  # lokalnie: technology nie zna celów

        return synergy(self.state, self.registry, self.pid)

    def color_counts(self) -> dict[str, int]:
        counts = dict.fromkeys(_MAIN_TECH_COLORS, 0)
        for tech_id in self.player.technologies:
            for color in self.tech_types(tech_id):
                if color in counts:
                    counts[color] += 1
        return counts

    # -- ekonomia --
    def ready_planets(self) -> list[str]:
        exhausted = set(self.player.exhausted_planets)
        return [p for p in self.controlled if p not in exhausted]

    def planet_value(self, planet_id: str, kind: str) -> int:
        stats = planet_stats(self.state, self.registry, planet_id)
        if stats is None:
            return 0
        return stats.resources if kind == "res" else stats.influence

    def spend_value(self, planet_id: str, kind: str) -> int:
        """Wartość planety przy WYDAWANIU (cele „Spend…”): Archon's Gift - jedna albo druga."""
        if payment.flex_spend(self.state, self.pid):
            return max(self.planet_value(planet_id, "res"), self.planet_value(planet_id, "inf"))
        return self.planet_value(planet_id, kind)

    def available(self, kind: str) -> int:
        """Suma do wydania z gotowych planet (cele „Spend…”; NIE cele „Control…”, F_xxcha)."""
        return sum(self.spend_value(p, kind) for p in self.ready_planets())


def _unit_total(system: SystemState, pid: str) -> int:
    total = sum(system.space_units.get(pid, {}).values())
    for by_player in system.planet_units.values():
        total += sum(by_player.get(pid, {}).values())
    return total


# --- Funkcje postępu ----------------------------------------------------------------------


def _systems_with_units(v: View, predicate: Callable[[str], bool]) -> int:
    return sum(1 for pos in v.state.systems if v.units_in(pos) > 0 and predicate(pos))


def _p_push_boundaries(v: View) -> int:
    mine = len(v.owned)
    neighbours = neighbors_by_player(v.state, v.grid).get(v.pid, set())
    above = 0
    for other_id in neighbours:
        other = View(v.state, v.registry, v.grid, other_id)
        # R_coexistence 17: I do not count a neighbour coexisting on my planet as controlling it.
        if mine > len(other.controlled):
            above += 1
    return above


def _p_edge(v: View) -> int:
    return _systems_with_units(v, lambda pos: v.grid.is_edge(pos) and pos != v.my_home())


def _p_legendary_or_anomaly(v: View) -> int:
    mecatol = v.mecatol()

    def counts(pos: str) -> bool:
        # Legendarna także planeta z Nano-Forge (C_relics: „legendary for … Make History”).
        legendary = any(
            is_legendary(v.state, v.registry, pid) for pid in v.planets_of_system(pos)
        )
        return pos == mecatol or v.is_anomaly(pos) or legendary

    return _systems_with_units(v, counts)


def _p_structures_outside_home(v: View) -> int:
    return sum(
        1
        for pid in v.owned
        if v.planet_pos.get(pid) != v.my_home() and v.unit_on(pid, _STRUCTURES) > 0
    )


def _p_same_trait(v: View) -> int:
    return max(v.trait_count(t) for t in _TRAITS)


def _p_unit_upgrades(v: View) -> int:
    return sum("UNITUPGRADE" in v.tech_types(t) for t in v.player.technologies)


def _p_diversify(v: View) -> int:
    counts = v.color_counts()
    pair = v.synergy()
    if pair is None:
        return sum(1 for n in counts.values() if n >= 2)
    # R_synergy: technologie pary można rozdzielić między oba kolory pary dowolnie.
    pooled = sum(counts[c] for c in pair)
    others = sum(1 for c, n in counts.items() if c not in pair and n >= 2)
    return others + min(len(pair), pooled // 2)


def _p_non_home_planets(v: View) -> int:
    return v.planets_with(v.in_non_home)


def _p_tech_skips(v: View) -> int:
    def has_skip(pid: str) -> bool:
        stats = planet_stats(v.state, v.registry, pid)
        return bool(stats and stats.tech_specialties)

    return v.planets_with(has_skip)


def _p_intimidate(v: View) -> int:
    mecatol = v.mecatol()
    if mecatol is None:
        return 0
    return sum(1 for pos in v.grid.neighbors(mecatol) if v.ships_in(pos) > 0)


def _p_command_tokens(v: View) -> int:
    # Scepter of Emelpar (C_relics): 1 żeton „z puli strategicznej" może zejść z rezerwy.
    scepter = command_tokens.SOURCE_SCEPTER in command_tokens.strategy_token_sources(
        v.state, v.pid
    )
    return v.player.tactical_cc + v.player.strategic_cc + (1 if scepter else 0)


def _p_trade_goods(v: View) -> int:
    return v.player.trade_goods


def _p_spend_both(goal: int) -> Callable[[View], int]:
    def progress(v: View) -> int:
        return threshold_progress_for_mixed(v, goal)

    return progress


def threshold_progress_for_mixed(v: View, goal: int) -> int:
    """Postęp celów „X influence + X resources + X trade goods" (amass/vast)."""
    values = spend_planets(v.state, v.registry, v.pid)
    plan = mixed_spend_plan(v.ready_planets(), values, v.player.trade_goods, goal)
    if plan is not None:
        return goal * 3
    best = 0
    for res, inf in _reachable_pairs(v.ready_planets(), values, goal):
        total = min(res, goal) + min(inf, goal) + min(v.player.trade_goods, goal)
        best = max(best, total)
    return min(best, goal * 3 - 1)


def _reachable_pairs(
    planets: list[str], registry: PlanetLookup, goal: int
) -> set[tuple[int, int]]:
    states: set[tuple[int, int]] = {(0, 0)}
    for planet_id in planets:
        planet = registry.planets.get(planet_id)
        if planet is None:
            continue
        new_states = set(states)
        for res, inf in states:
            new_states.add((min(res + planet.resources, goal), inf))
            new_states.add((res, min(inf + planet.influence, goal)))
        states = new_states
    return states


def spend_planets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> EffectivePlanets:
    """Planety z wartościami do WYDANIA przez gracza (cele „Spend…”).

    Archon's Gift (``payment.flex_spend``): planeta daje swoją większą wartość jako zasoby ALBO
    wpływ - „each planet they exhaust will contribute to either the resource requirement or the
    influence requirement, but cannot partially contribute to both” (F_xxcha, Amass Wealth).
    """
    values = effective_planets(state, registry)
    if not payment.flex_spend(state, player_id):
        return values
    flexed = {
        pid: planet.model_copy(update={
            "resources": max(planet.resources, planet.influence),
            "influence": max(planet.resources, planet.influence),
        })
        for pid, planet in values.planets.items()
    }
    return EffectivePlanets(flexed)


def mixed_spend_plan(
    planets: list[str], registry: PlanetLookup, trade_goods: int, goal: int
) -> tuple[list[str], list[str], int] | None:
    """Plan wydania „goal res + goal inf + goal TG": (planety→res, planety→inf, TG).

    Planeta zasila ALBO zasoby ALBO wpływy (R_resources/R_influence). Brakujące punkty
    dopłacają trade goods (TG liczą się jako zasoby/wpływy — R_trade_goods). Wybiera plan
    o najmniejszej liczbie wydanych TG. ``None`` gdy niewykonalne.
    """
    states: dict[tuple[int, int], tuple[list[str], list[str]]] = {(0, 0): ([], [])}
    for planet_id in planets:
        planet = registry.planets.get(planet_id)
        if planet is None:
            continue
        updated = dict(states)
        for (res, inf), (res_list, inf_list) in states.items():
            key_r = (min(res + planet.resources, goal), inf)
            key_i = (res, min(inf + planet.influence, goal))
            if planet.resources > 0 and key_r not in updated:
                updated[key_r] = ([*res_list, planet_id], inf_list)
            if planet.influence > 0 and key_i not in updated:
                updated[key_i] = (res_list, [*inf_list, planet_id])
        states = updated
    best: tuple[int, list[str], list[str]] | None = None
    for (res, inf), (res_list, inf_list) in states.items():
        extra = max(0, goal - res) + max(0, goal - inf)
        need_tg = goal + extra
        if need_tg > trade_goods:
            continue
        cost = (extra, len(res_list) + len(inf_list))
        if best is None or cost < (best[0], len(best[1]) + len(best[2])):
            best = (extra, res_list, inf_list)
    if best is None:
        return None
    return best[1], best[2], goal + best[0]


def _p_resources(v: View) -> int:
    return v.available("res") + v.player.trade_goods


def _p_influence(v: View) -> int:
    return v.available("inf") + v.player.trade_goods


def _p_structures(v: View) -> int:
    return v.count_units(*_STRUCTURES)


def _p_engineer(v: View) -> int:
    return v.count_units("flagship", "warsun")


def _p_no_planet_systems(v: View) -> int:
    return _systems_with_units(v, lambda pos: not v.planets_of_system(pos))


def _p_max_fleet(v: View) -> int:
    return max((v.non_fighter_ships_in(pos) for pos in v.state.systems), default=0)


def _p_conquer(v: View) -> int:
    homes = set(v.other_homes())
    return v.planets_with(lambda pid: v.planet_pos.get(pid) in homes)


def _p_supremacy(v: View) -> int:
    targets = {*v.other_homes()}
    mecatol = v.mecatol()
    if mecatol is not None:
        targets.add(mecatol)
    return sum(
        1
        for pos in targets
        if (system := v.state.systems.get(pos)) is not None
        and any(
            system.space_units.get(v.pid, {}).get(t, 0) > 0 for t in ("flagship", "warsun")
        )
    )


def _p_distant_lands(v: View) -> int:
    planets: set[str] = set()
    homes_touched: set[str] = set()
    for home in v.other_homes():
        zone = {home, *v.grid.neighbors(home)}
        for planet_id in v.owned:
            if v.planet_pos.get(planet_id) in zone:
                planets.add(planet_id)
                homes_touched.add(home)
    return min(len(planets), len(homes_touched))


def _p_production(v: View) -> int:
    return max(
        (
            production.system_production_value(v.state, v.grid, v.registry, v.pid, pos)
            for pos in v.state.systems
        ),
        default=0,
    )


def _p_legendary_planet(v: View) -> int:
    return v.planets_with(lambda pid: is_legendary(v.state, v.registry, pid))


def _p_shared_system(v: View) -> int:
    count = 0
    for planet_id in v.owned:
        position = v.planet_pos.get(planet_id)
        system = v.state.systems.get(position or "")
        if system is None:
            continue
        if any(owner != v.pid for owner in system.planet_owners.values()):
            count += 1
    return count


def _p_notes_in_play(v: View) -> int:
    return len(v.player.promissory_notes_in_play)


def _p_big_ground_stack(v: View) -> int:
    best = 0
    for system in v.state.systems.values():
        for by_player in system.planet_units.values():
            mine = by_player.get(v.pid, {})
            if mine.get("spacedock", 0) > 0:
                continue
            best = max(best, sum(mine.get(t, 0) for t in _GROUND))
    return best


def _p_mechs(v: View) -> int:
    return sum(
        1
        for system in v.state.systems.values()
        for by_player in system.planet_units.values()
        if by_player.get(v.pid, {}).get("mech", 0) > 0
    )

def _p_resource_sum(v: View) -> int:
    return sum(v.planet_value(p, "res") for p in v.owned)


def _p_influence_sum(v: View) -> int:
    return sum(v.planet_value(p, "inf") for p in v.owned)


def _p_nexus(v: View) -> int:
    for position in v.state.systems:
        if "mallice" in v.planets_of_system(position) and v.units_in(position) > 0:
            return 1
    return 0


def _p_next_to_home(v: View) -> int:
    return sum(
        1 for home in v.other_homes() for pos in v.grid.neighbors(home) if v.ships_in(pos) > 0
    )


def _p_seat_of_empire(v: View) -> int:
    mecatol = v.mecatol()
    if mecatol is None or "mr" not in v.owned:
        return 0
    return v.ships_in(mecatol)


def _p_attachments(v: View) -> int:
    """Kontrolowane planety z attachmentem (karta attach z eksploracji, RULES.md 46).

    Liczą się wyłącznie karty w ``GameState.planet_attachments``. Żeton wormhole (np. Gamma
    Wormhole) leży w systemie, nie na planecie, i attachmentem NIE jest.
    """
    return v.planets_with(lambda p: bool(v.state.planet_attachments.get(p)))


def _p_hazardous(v: View) -> int:
    return v.trait_count("HAZARDOUS")


def _p_industrial(v: View) -> int:
    return v.trait_count("INDUSTRIAL")


def _p_cultural(v: View) -> int:
    return v.trait_count("CULTURAL")


def _p_same_color_techs(v: View) -> int:
    counts = v.color_counts()
    pair = v.synergy()
    if pair is not None:
        # R_synergy: wszystkie technologie pary mogą liczyć się jako jeden kolor.
        return max(max(counts.values()), sum(counts[c] for c in pair))
    return max(counts.values())


def _p_adjacent_to_anomaly(v: View) -> int:
    return sum(
        1
        for pos in v.state.systems
        if v.ships_in(pos) > 0 and any(v.is_anomaly(n) for n in v.grid.neighbors(pos))
    )


def _p_space_docks(v: View) -> int:
    return v.count_units("spacedock")


def _p_pds(v: View) -> int:
    return v.count_units("pds")


def _p_dreadnoughts(v: View) -> int:
    return v.count_units("dreadnought")


def _p_action_cards(v: View) -> int:
    return len(v.player.private.action_cards) or v.player.hidden_card_counts.get(
        "action_cards", 0
    )


def _p_faction_techs(v: View) -> int:
    count = 0
    for tech_id in v.player.technologies:
        tech = v.registry.technologies.get(tech_id)
        if tech is not None and tech.faction and tech_id not in ("vax", "vay"):
            count += 1
    return count


def _p_both_wormholes(v: View) -> int:
    alpha = any(v.ships_in(p) > 0 and "ALPHA" in v.wormholes(p) for p in v.state.systems)
    beta = any(v.ships_in(p) > 0 and "BETA" in v.wormholes(p) for p in v.state.systems)
    return int(alpha) + int(beta)


def _p_ship_systems(v: View) -> int:
    return sum(1 for pos in v.state.systems if v.ships_in(pos) > 0)


def _p_blockade_dock(v: View) -> int:
    count = 0
    for other_id in v.state.players:
        if other_id == v.pid:
            continue
        for pos, system in v.state.systems.items():
            has_dock = any(
                by_player.get(other_id, {}).get("spacedock", 0) > 0
                for by_player in system.planet_units.values()
            )
            if has_dock and v.ships_in(pos) > 0:
                count += 1
    return count


def _p_relic_fragments(v: View) -> int:
    """Destroy Heretical Works: fragmenty reliktów w strefie gracza (każdego typu)."""
    return len(v.player.relic_fragments)


def _p_laws_in_play(v: View) -> int:
    """Dictate Policy: prawa (laws) aktualnie w grze."""
    return len(v.state.decks.agenda_laws)


def _p_neighbours(v: View) -> int:
    return len(neighbors_by_player(v.state, v.grid).get(v.pid, set()))


_PROGRESS: dict[str, Callable[[View], int]] = {
    "push_boundaries": _p_push_boundaries,
    "outer_rim": _p_edge, "control_borderlands": _p_edge,
    "make_history": _p_legendary_or_anomaly, "become_legend": _p_legendary_or_anomaly,
    "infrastructure": _p_structures_outside_home, "protect_border": _p_structures_outside_home,
    "corner": _p_same_trait, "unify_colonies": _p_same_trait,
    "develop": _p_unit_upgrades, "revolutionize": _p_unit_upgrades,
    "diversify": _p_diversify, "master_science": _p_diversify,
    "monument": _p_resources, "golden_age": _p_resources,
    "sway_council": _p_influence, "manipulate_law": _p_influence,
    "expand_borders": _p_non_home_planets, "subdue": _p_non_home_planets,
    "research_outposts": _p_tech_skips, "brain_trust": _p_tech_skips,
    "intimidate": _p_intimidate,
    "lead": _p_command_tokens, "galvanize": _p_command_tokens,
    "trade_routes": _p_trade_goods, "centralize_trade": _p_trade_goods,
    "amass_wealth": _p_spend_both(3), "vast_reserves": _p_spend_both(6),
    "build_defenses": _p_structures, "massive_cities": _p_structures,
    "engineer_marvel": _p_engineer,
    "deep_space": _p_no_planet_systems, "vast_territories": _p_no_planet_systems,
    "raise_fleet": _p_max_fleet, "command_armada": _p_max_fleet,
    "conquer": _p_conquer, "supremacy": _p_supremacy, "distant_lands": _p_distant_lands,
    "pem": _p_production, "sai": _p_legendary_planet, "syc": _p_shared_system,
    "ancient_monuments": _p_attachments, "lost_outposts": _p_attachments,
    "sb": _p_notes_in_play, "otf": _p_big_ground_stack, "mtm": _p_mechs,
    "hrm": _p_resource_sum, "eh": _p_influence_sum, "dfat": _p_nexus,
    "te": _p_next_to_home, "ose": _p_seat_of_empire, "mrm": _p_hazardous,
    "mlp": _p_same_color_techs, "mp": _p_industrial, "lsc": _p_adjacent_to_anomaly,
    "fwm": _p_space_docks, "fsn": _p_action_cards, "gamf": _p_dreadnoughts,
    "ans": _p_faction_techs, "btgk": _p_both_wormholes, "ctr": _p_ship_systems,
    "csl": _p_blockade_dock, "eap": _p_pds, "faa": _p_cultural, "fc": _p_neighbours,
    "dhw": _p_relic_fragments, "dp": _p_laws_in_play,
}

# Cele, których warunku stan gry nie modeluje. Pusty zbiór: wszystkie cele katalogu są liczone
# automatycznie (fazy Action/Agenda przez ``core/objective_events``).
MANUAL_OBJECTIVES: frozenset[str] = frozenset()


def progress(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    objective_id: str,
) -> int | None:
    """Postęp gracza względem celu; ``None`` = warunek niemodelowany (potwierdza operator)."""
    if objective_id in MANUAL_OBJECTIVES or objective_id not in _PROGRESS:
        return None
    if player_id not in state.players:
        return 0
    return _PROGRESS[objective_id](View(state, registry, grid, player_id))


def evaluate(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    objective_id: str,
) -> tuple[int | None, int, bool]:
    """(postęp, próg, czy można zdobyć). Cel niemodelowany → można (potwierdza operator)."""
    value = progress(state, registry, grid, player_id, objective_id)
    goal = threshold(objective_id, state)
    if value is None or goal <= 0:
        return value, goal, True
    return value, goal, value >= goal
