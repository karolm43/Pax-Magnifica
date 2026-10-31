"""Walidacja produkcji jednostek w akcji taktycznej (Etap E8-T6).

Egzekwuje LIMIT produkcji (suma wartości PRODUCTION jednostek gracza w aktywnym
systemie), BUDŻET (koszt ≤ dostępne zasoby — SPRAWDZENIE bez realnego wydawania,
opcja „b") oraz BLOKADĘ statków (nie produkuj statków w systemie z obcymi statkami).
Reguły: RULES.md 33.2 (źródło LRR R_production / R_producing_units). Funkcje CZYSTE.

Zakres T6 (szkielet, „make it exist first"): sprawdzamy legalność zamówienia produkcji;
realne wyczerpywanie planet / zdejmowanie TG oraz component limitations (rezerwy) = TODO
z modelem wpływu. God-Mode (edit-units) nadal omija (wentyl bez reguł).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.combat import resolve_unit_variant
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

# Jednostki produkowane podwójnie (2 sztuki za koszt) — RULES.md 22/33.2.
_DUAL = {"fighter", "infantry"}


@dataclass(frozen=True)
class ProductionOrder:
    """Pojedyncza pozycja zamówienia produkcji: typ jednostki + liczba SZTUK."""

    base_type: str
    count: int


def _planet_resources(registry: StaticDataRegistry, planet_id: str) -> int:
    """Wartość ``resources`` planety z rejestru (0, gdy nieznana)."""
    planet = registry.planets.get(planet_id)
    return planet.resources if planet is not None else 0


def _unit_production_value(
    registry: StaticDataRegistry,
    faction_id: str | None,
    technologies: list[str],
    base_type: str,
    planet_id: str | None,
) -> int:
    """Wartość PRODUCTION jednej jednostki gracza (wariant wg technologii).

    Obsługuje wartość liczbową (np. Saar dok = 5) oraz modyfikator względny
    (string ``"+N"`` = zasoby planety + N — bazowy dok). Gdy modyfikator względny,
    a jednostka nie stoi na planecie, N liczymy od 0 (brak zasobów planety).
    """
    unit = resolve_unit_variant(registry, faction_id, technologies, base_type)
    if unit is None or unit.production_value is None:
        return 0
    pv = unit.production_value
    if isinstance(pv, int):
        return pv
    # String: modyfikator względem zasobów planety, np. "+2".
    text = str(pv).strip()
    try:
        modifier = int(text.replace("+", "")) if text else 0
    except ValueError:
        return 0
    base = _planet_resources(registry, planet_id) if planet_id is not None else 0
    return base + modifier


def production_limit(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
) -> int:
    """Suma wartości PRODUCTION jednostek gracza w AKTYWNYM systemie (RULES.md 33.2).

    Cienki wrapper na ``system_production_value`` dla aktywnego systemu (``active_system``).
    Zwraca 0, gdy brak aktywnego systemu.
    """
    active = state.active_system
    if active is None:
        return 0
    return system_production_value(state, grid, registry, player_id, active)


def system_production_value(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
) -> int:
    """Suma wartości PRODUCTION jednostek gracza w DANYM systemie (RULES.md 33.2).

    Liczy jednostki produkujące w przestrzeni (statki z PRODUCTION) oraz struktury na
    planetach (doki). Modyfikator względny doku ("+N") rozwiązywany względem planety,
    na której stoi. Gdy system/jednostek brak — 0. Używane też do wskaźnika produkcji
    na kafelku mapy (web-data ``tileUnitData[pos].production``).
    """
    system = state.systems.get(position)
    if system is None:
        return 0
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []

    total = 0
    # Przestrzeń: statki gracza z wartością PRODUCTION (np. warsun/flagship warianty).
    for base_type, count in system.space_units.get(player_id, {}).items():
        pv = _unit_production_value(registry, faction_id, technologies, base_type, None)
        total += pv * count
    # Planety: struktury gracza (doki) — modyfikator względny od zasobów planety.
    for planet_id, by_player in system.planet_units.items():
        for base_type, count in by_player.get(player_id, {}).items():
            pv = _unit_production_value(
                registry, faction_id, technologies, base_type, planet_id
            )
            total += pv * count
    return total


def available_budget(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> int:
    """Dostępny budżet gracza: suma zasobów GOTOWYCH planet + trade goods (RULES.md 33.2).

    SPRAWDZENIE (opcja „b"): nie wydajemy realnie. Gotowe planety = kontrolowane przez
    gracza (``planet_owners``) i NIE wyczerpane (``exhausted_planets``). Trade goods z
    ``PlayerState.trade_goods``.
    """
    player = state.players.get(player_id)
    if player is None:
        return 0
    exhausted = set(player.exhausted_planets)
    resources = 0
    for system in state.systems.values():
        for planet_id, owner in system.planet_owners.items():
            if owner != player_id or planet_id in exhausted:
                continue
            resources += _planet_resources(registry, planet_id)
    return resources + player.trade_goods


def _order_cost(
    registry: StaticDataRegistry,
    faction_id: str | None,
    technologies: list[str],
    order: ProductionOrder,
) -> float:
    """Koszt pozycji zamówienia: koszt jednostki × liczba PAR (dual = 2 za koszt)."""
    unit = resolve_unit_variant(registry, faction_id, technologies, order.base_type)
    cost = unit.cost if unit is not None and unit.cost is not None else 0.0
    if order.base_type in _DUAL:
        # Para za koszt: N sztuk = ceil(N/2) kosztów (1 sztuka też pełny koszt).
        pairs = (order.count + 1) // 2
        return cost * pairs
    return cost * order.count


def validate_production(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    orders: list[ProductionOrder],
) -> None:
    """Twardo waliduje zamówienie produkcji (RULES.md 33.2) — nie mutuje stanu.

    Sprawdza: aktywny system; LIMIT (łączna liczba sztuk ≤ suma PRODUCTION); BLOKADĘ
    statków (obce statki w aktywnym systemie → statków nie produkujemy); BUDŻET
    (łączny koszt ≤ gotowe planety + TG — sprawdzenie, bez wydawania).

    Raises:
        ValueError: Przy złamaniu którejkolwiek reguły.
    """
    active = state.active_system
    if active is None:
        raise ValueError("Brak aktywnego systemu — produkcja tylko w akcji taktycznej.")
    orders = [o for o in orders if o.count > 0]
    if not orders:
        return

    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []

    # LIMIT: łączna liczba sztuk ≤ suma PRODUCTION w aktywnym systemie.
    total_units = sum(o.count for o in orders)
    limit = production_limit(state, grid, registry, player_id)
    if total_units > limit:
        raise ValueError(
            f"Limit produkcji przekroczony: {total_units} sztuk > PRODUCTION {limit}."
        )

    # BLOKADA statków: obce statki w aktywnym systemie → statków nie produkujemy.
    system = state.systems.get(active)
    enemy_ships = False
    if system is not None:
        for owner, by_type in system.space_units.items():
            if owner != player_id and any(c > 0 for c in by_type.values()):
                enemy_ships = True
                break
    if enemy_ships:
        for o in orders:
            if is_space_unit(o.base_type):
                raise ValueError(
                    "Nie można produkować statków w systemie z obcymi statkami "
                    f"(blokada): {o.base_type}."
                )

    # BUDŻET: łączny koszt ≤ dostępne zasoby (sprawdzenie, bez wydawania).
    total_cost = sum(
        _order_cost(registry, faction_id, technologies, o) for o in orders
    )
    budget = available_budget(state, registry, player_id)
    if total_cost > budget:
        raise ValueError(
            f"Za mało zasobów: koszt {total_cost:g} > dostępne {budget} "
            "(planety gotowe + trade goods)."
        )
