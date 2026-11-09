"""Walidacja produkcji jednostek w akcji taktycznej (Etap E8-T6).

Egzekwuje LIMIT produkcji (suma wartości PRODUCTION jednostek gracza w aktywnym
systemie), BUDŻET (koszt ≤ dostępne zasoby — SPRAWDZENIE bez realnego wydawania,
opcja „b") oraz BLOKADĘ statków (nie produkuj statków w systemie z obcymi statkami).
Reguły: RULES.md 33.2 (źródło LRR R_production / R_producing_units). Funkcje CZYSTE.

``produce`` (RULES.md 33.3) domyka krok: waliduje całość (limit WSPÓLNY dla akcji, blokada,
strefy umieszczenia, rezerwa), REALNIE płaci (wyczerpuje planety, zdejmuje TG) i stawia
jednostki. God-Mode (edit-units) nadal omija (wentyl bez reguł).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core import control, economy, rules_hooks, triggers, unit_ops
from src.core.combat import resolve_unit_variant
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, ProductionGrant
from src.core.hex_grid import HexGrid
from src.core.payment import apply_payment
from src.core.planet_stats import influence_of, resources_of
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import (
    ASYNC_ID_BY_BASE_TYPE,
    UNIT_CAP_BY_ASYNC_ID,
    is_space_unit,
)
from src.core.unit_ops import UnitCause

# Jednostki produkowane podwójnie (2 sztuki za koszt) — RULES.md 22/33.2.
_DUAL = {"fighter", "infantry"}


@dataclass(frozen=True)
class ProductionOrder:
    """Pojedyncza pozycja zamówienia produkcji: typ jednostki + liczba SZTUK."""

    base_type: str
    count: int
    # Strefa docelowa: "space" albo id planety. None = domyślnie (statek → przestrzeń).
    zone: str | None = None


@dataclass(frozen=True)
class Spend:
    """Czym płacimy za produkcję: wyczerpywane planety + trade goods (R_producing_units)."""

    planets: tuple[str, ...] = ()
    trade_goods: int = 0


@dataclass(frozen=True)
class Producer:
    """Jednostka(i) z PRODUCTION w aktywnym systemie: gdzie stoją i ile dają łącznie.

    Każdy producent to OSOBNA zdolność PRODUCTION (R_production): wartości się sumują do
    limitu, ale mogą mieć własne ograniczenia (``forbids``) — np. dok Arborec nie produkuje
    piechoty, a piechota Arborec (PRODUCTION 1 za sztukę) to osobne źródło. Dlatego nie
    wolno traktować ich jak „jednej produkcji × N".
    """

    zone: str  # "space" albo id planety
    base_type: str
    count: int
    value: int  # łączna wartość PRODUCTION tej grupy (wartość jednostki × liczba)
    per_unit: int = 0  # wartość PRODUCTION jednej sztuki (value = per_unit × count)
    # Typy jednostek, których TA zdolność PRODUCTION nie może produkować (hook frakcji).
    forbids: tuple[str, ...] = ()


# Struktury nie są "produkowane" przez PRODUCTION (to Construction) — poza zamówieniami.
STRUCTURES = {"pds", "spacedock"}

def forbidden_types(state: GameState, player_id: str, producer_type: str) -> tuple[str, ...]:
    """Typy jednostek, których producent danego typu nie może produkować (hooki FORBID).

    Np. Arborec: wartość PRODUCTION doków nie służy do piechoty (``core/hooks/factions_base``).
    """
    banned = rules_hooks.forbidden(
        rules_hooks.POINT_PRODUCTION_FORBIDS,
        state,
        player_id,
        {"producer_type": producer_type},
    )
    return tuple(sorted(banned))


def fits_producers(producers: list[Producer], counts: dict[str, int]) -> bool:
    """Czy da się rozdzielić ``counts`` (typ → sztuki) między producentów (warunek Halla).

    Każda sztuka zajmuje 1 z wartości PRODUCTION producenta, który może ją wyprodukować
    (nie jest w jego ``forbids``). Dla każdego podzbioru typów suma sztuk nie może
    przekraczać łącznej wartości producentów dopuszczających choć jeden typ z podzbioru.
    Typów jest kilka, więc pełne wyliczenie podzbiorów jest tanie.
    """
    types = [t for t, n in counts.items() if n > 0]
    for mask in range(1, 1 << len(types)):
        chosen = [types[i] for i in range(len(types)) if mask >> i & 1]
        need = sum(counts[t] for t in chosen)
        have = sum(p.value for p in producers if any(t not in p.forbids for t in chosen))
        if need > have:
            return False
    return True


def _planet_resources(state: GameState, registry: StaticDataRegistry, planet_id: str) -> int:
    """Zasoby planety z attachmentami (0, gdy nieznana) — ``core/planet_stats``."""
    return resources_of(state, registry, planet_id)


def active_grant(state: GameState, player_id: str) -> ProductionGrant | None:
    """Jednorazowa produkcja z efektu karty (Freelancers) dla gracza w aktywnym systemie.

    Granty ``standalone`` (karty strategii) NIE są tu zwracane - mają zwykłe reguły produkcji.
    """
    grant = state.production_grant
    if (
        grant is not None
        and not grant.standalone
        and grant.player_id == player_id
        and grant.position == state.active_system
    ):
        return grant
    return None


def standalone_grant(state: GameState) -> ProductionGrant | None:
    """Trwająca produkcja z karty strategii (poza akcją taktyczną) lub None."""
    grant = state.production_grant
    return grant if grant is not None and grant.standalone else None


def production_system(state: GameState) -> str | None:
    """System, w którym toczy się produkcja: pozycja granta ``standalone`` albo aktywny."""
    grant = standalone_grant(state)
    return grant.position if grant is not None else state.active_system


def production_player(state: GameState) -> str | None:
    """Gracz, który teraz produkuje: właściciel granta ``standalone`` albo aktywny gracz."""
    grant = standalone_grant(state)
    return grant.player_id if grant is not None else state.active_player_id


def pay_value(
    state: GameState, registry: StaticDataRegistry, planet_id: str, player_id: str
) -> int:
    """Ile planeta wnosi do płatności za produkcję.

    Zwykle jej zasoby; przy ``ProductionGrant.influence_as_resources`` (Freelancers) wpływ
    liczy się jak zasoby — planetę wyczerpuje się na zasoby ALBO wpływ, nie oba (nota
    Freelancers), więc wartość to większa z dwóch.
    """
    resources = resources_of(state, registry, planet_id)
    grant = active_grant(state, player_id)
    if grant is not None and grant.influence_as_resources:
        return max(resources, influence_of(state, registry, planet_id))
    return resources


def _unit_production_value(
    state: GameState,
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
    base = _planet_resources(state, registry, planet_id) if planet_id is not None else 0
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
    active = production_system(state)
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
    return sum(p.value for p in producers(state, registry, player_id, position))


def _hooked_production_value(
    state: GameState, player_id: str, base_type: str, zone: str, value: int
) -> int:
    """Wartość PRODUCTION jednostki po hookach MODIFY (tylko jednostki, które produkują)."""
    if value <= 0:
        return value
    return max(
        0,
        rules_hooks.modify(
            rules_hooks.POINT_PRODUCTION_VALUE, state, player_id, value,
            {"base_type": base_type, "zone": zone},
        ),
    )


def producers(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
) -> list[Producer]:
    """Jednostki gracza z PRODUCTION > 0 w danym systemie (R_production).

    Przestrzeń: statki z PRODUCTION (np. warianty flagowca/war suna). Planety: struktury
    (doki) — modyfikator względny ("+N") liczony od zasobów planety, na której stoją.
    """
    system = state.systems.get(position)
    if system is None:
        return []
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []

    # Jednostki wyprodukowane w TEJ akcji nie dokładają PRODUCTION (producent = stan sprzed
    # kroku), więc odejmujemy je od liczby sztuk w strefie.
    fresh = state.production_placed if position == production_system(state) else {}

    result: list[Producer] = []
    for base_type, total in system.space_units.get(player_id, {}).items():
        count = total - fresh.get("space", {}).get(base_type, 0)
        pv = _hooked_production_value(
            state, player_id, base_type, "space",
            _unit_production_value(state, registry, faction_id, technologies, base_type, None),
        )
        if pv > 0 and count > 0:
            result.append(
                Producer(
                    "space", base_type, count, pv * count, pv,
                    forbidden_types(state, player_id, base_type),
                )
            )
    for planet_id, by_player in system.planet_units.items():
        for base_type, total in by_player.get(player_id, {}).items():
            count = total - fresh.get(planet_id, {}).get(base_type, 0)
            pv = _hooked_production_value(
                state, player_id, base_type, planet_id,
                _unit_production_value(
                    state, registry, faction_id, technologies, base_type, planet_id
                ),
            )
            if pv > 0 and count > 0:
                result.append(
                    Producer(
                        planet_id, base_type, count, pv * count, pv,
                        forbidden_types(state, player_id, base_type),
                    )
                )
    grant = standalone_grant(state)
    if (
        grant is not None
        and grant.zone is not None
        and grant.player_id == player_id
        and grant.position == position
    ):
        # Construction: do produkcji wolno użyć JEDNEGO doku - tylko producent z tej planety.
        result = [p for p in result if p.zone == grant.zone]
    return result


def used_by_type(state: GameState) -> dict[str, int]:
    """Ile sztuk każdego typu wyprodukowano w tej akcji (suma po strefach)."""
    totals: dict[str, int] = {}
    for by_type in state.production_placed.values():
        for base_type, n in by_type.items():
            totals[base_type] = totals.get(base_type, 0) + n
    return totals


def remaining_production(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
) -> int:
    """Ile jednostek można jeszcze wyprodukować w tej akcji (limit − już wyprodukowane)."""
    grant = active_grant(state, player_id)
    if grant is not None:
        return grant.units  # Freelancers itp.: własny limit, niezależny od wartości PRODUCTION
    return max(0, production_limit(state, grid, registry, player_id) - state.production_used)


def is_blockaded(state: GameState, player_id: str, position: str) -> bool:
    """Czy w systemie stoją OBCE statki (R_producing_units: wtedy statków nie produkujemy)."""
    system = state.systems.get(position)
    if system is None:
        return False
    return any(
        owner != player_id and any(c > 0 for c in by_type.values())
        for owner, by_type in system.space_units.items()
    )


def allowed_ground_zones(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
) -> list[str]:
    """Gdzie wolno postawić wyprodukowane SIŁY NAZIEMNE (R_production).

    Planety, na których stoi jednostka z PRODUCTION (dok). Jeśli produkuje jednostka w
    przestrzeni — dodatkowo każda planeta gracza w systemie albo sama przestrzeń.
    """
    if active_grant(state, player_id) is not None:
        # Efekt „produce w tym systemie" (Freelancers): bez doków — siły naziemne na planety
        # gracza w systemie albo do przestrzeni (jak przy produkcji statkiem).
        system = state.systems.get(position)
        owned = (
            [p for p, owner in system.planet_owners.items() if owner == player_id]
            if system is not None
            else []
        )
        return [*owned, "space"]
    prods = producers(state, registry, player_id, position)
    zones: list[str] = []
    for p in prods:
        if p.zone != "space" and p.zone not in zones:
            zones.append(p.zone)
    if any(p.zone == "space" for p in prods):
        system = state.systems.get(position)
        if system is not None:
            for planet_id, owner in system.planet_owners.items():
                if owner == player_id and planet_id not in zones:
                    zones.append(planet_id)
        zones.append("space")
    return zones


def deployed_count(state: GameState, player_id: str, base_type: str) -> int:
    """Ile jednostek danego typu gracz ma na planszy (przestrzeń + planety, wszystkie systemy)."""
    total = 0
    for system in state.systems.values():
        total += system.space_units.get(player_id, {}).get(base_type, 0)
        for by_player in system.planet_units.values():
            total += by_player.get(player_id, {}).get(base_type, 0)
    return total


def reinforcements_left(
    state: GameState, player_id: str, base_type: str
) -> int | None:
    """Ile sztuk zostało w rezerwie; ``None`` = bez limitu (żetony fighter/infantry).

    R_component_limitations: myśliwce i siły naziemne mają żetony zastępcze, reszta jest
    ograniczona plastikiem (limity z ``UNIT_CAP_BY_ASYNC_ID``).
    """
    if base_type in _DUAL:
        return None
    cap = UNIT_CAP_BY_ASYNC_ID.get(ASYNC_ID_BY_BASE_TYPE.get(base_type, ""))
    if cap is None:
        return None
    return max(0, cap - deployed_count(state, player_id, base_type))


def ready_planets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str]]:
    """Planety gracza gotowe do wydania (id, pozycja systemu) — kontrolowane, nie wyczerpane."""
    player = state.players.get(player_id)
    exhausted = set(player.exhausted_planets) if player is not None else set()
    result: list[tuple[str, str]] = []
    for position, system in state.systems.items():
        for planet_id, owner in system.planet_owners.items():
            if owner == player_id and planet_id not in exhausted:
                result.append((planet_id, position))
    return result


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
            resources += pay_value(state, registry, planet_id, player_id)
    return resources + economy.spendable_trade_goods(state, player_id)


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
        # Dane AsyncTI4 trzymają koszt PER SZTUKA (piechota/myśliwiec = 0.5); karta mówi
        # „1 za dwie". Para = 2 × koszt sztuki; N sztuk = ceil(N/2) par (1 sztuka też pełna para).
        pairs = (order.count + 1) // 2
        return cost * 2 * pairs
    return cost * order.count


def _total_cost(
    registry: StaticDataRegistry,
    faction_id: str | None,
    technologies: list[str],
    orders: list[ProductionOrder],
) -> float:
    """Koszt całego zamówienia; sztuki tego samego typu (np. piechota na dwóch planetach)
    łączą się w pary, bo para fighter/infantry to jeden koszt niezależnie od strefy."""
    merged: dict[str, int] = {}
    for o in orders:
        if o.count > 0:
            merged[o.base_type] = merged.get(o.base_type, 0) + o.count
    return sum(
        _order_cost(registry, faction_id, technologies, ProductionOrder(bt, n))
        for bt, n in merged.items()
    )


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
    active = production_system(state)
    if active is None:
        raise ValueError("No active system - production is only allowed during a tactical action.")
    orders = [o for o in orders if o.count > 0]
    if not orders:
        return

    # LIMIT: łączna liczba sztuk ≤ suma PRODUCTION w aktywnym systemie.
    total_units = sum(o.count for o in orders)
    limit = remaining_production(state, grid, registry, player_id)
    if total_units > limit:
        raise ValueError(
            f"Production limit exceeded: {total_units} units > PRODUCTION {limit} left."
        )

    # Osobne zdolności PRODUCTION: niektóre nie mogą produkować każdego typu (np. dok
    # Arborec nie produkuje piechoty). Liczymy łącznie z tym, co już powstało w tej akcji.
    cumulative = used_by_type(state)
    for o in orders:
        cumulative[o.base_type] = cumulative.get(o.base_type, 0) + o.count
    if active_grant(state, player_id) is None and not fits_producers(
        producers(state, registry, player_id, active), cumulative
    ):
        raise ValueError(
            "Production limit exceeded for these unit types: part of the PRODUCTION cannot "
            "produce them (e.g. Arborec space docks cannot produce infantry)."
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
                    "Cannot produce ships in a system containing enemy ships "
                    f"(blockade): {o.base_type}."
                )

    # BUDŻET: łączny koszt ≤ dostępne zasoby (sprawdzenie, bez wydawania).
    total_cost = order_cost(state, registry, player_id, orders)
    budget = available_budget(state, registry, player_id)
    if total_cost > budget:
        raise ValueError(
            f"Not enough resources: cost {total_cost:g} > available {budget} "
            "(ready planets + trade goods)."
        )


def order_cost(
    state: GameState, registry: StaticDataRegistry, player_id: str, orders: list[ProductionOrder]
) -> float:
    """Łączny koszt zamówienia (para fighter/infantry = jeden koszt)."""
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    base_cost = _total_cost(registry, faction_id, technologies, orders)
    return max(
        0.0,
        rules_hooks.modify(rules_hooks.POINT_PRODUCTION_COST, state, player_id, base_cost),
    )


def auto_pay(
    state: GameState, registry: StaticDataRegistry, player_id: str, cost: float
) -> Spend:
    """Wybiera czym zapłacić z minimalną nadwyżką: najpierw planety, TG tylko na resztę.

    Zachłannie: planety od największych zasobów do pokrycia kosztu, potem zdejmuje
    zbędne (od najmniejszych), jeśli suma nadal wystarcza. Brakującą część dopłaca TG.
    Gdy zasobów brak — zwraca wszystko, co jest (walidacja odrzuci niedobór).
    """
    need = int(-(-cost // 1))  # ceil bez importu math
    if need <= 0:
        return Spend()
    player = state.players.get(player_id)
    tg = economy.spendable_trade_goods(state, player_id) if player is not None else 0
    ready = [pid for pid, _ in ready_planets(state, registry, player_id)]
    ranked = sorted(
        ((pid, pay_value(state, registry, pid, player_id)) for pid in ready),
        key=lambda item: (-item[1], item[0]),
    )
    chosen: list[tuple[str, int]] = []
    total = 0
    for pid, res in ranked:
        if total >= need:
            break
        if res <= 0:
            continue
        chosen.append((pid, res))
        total += res
    for item in sorted(chosen, key=lambda i: i[1]):
        if total - item[1] >= need:
            chosen.remove(item)
            total -= item[1]
    missing = max(0, need - total)
    return Spend(tuple(pid for pid, _ in chosen), min(tg, missing))


def _validate_spend(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    spend: Spend,
    cost: float,
) -> None:
    """Sprawdza, że płatność jest legalna i pokrywa koszt (nadwyżka przepada)."""
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}.")
    if len(set(spend.planets)) != len(spend.planets):
        raise ValueError("The same planet was selected to pay twice.")
    ready = {pid for pid, _ in ready_planets(state, registry, player_id)}
    for pid in spend.planets:
        if pid not in ready:
            raise ValueError(f"Planet {pid} is not controlled or is already exhausted.")
    spendable = economy.spendable_trade_goods(state, player_id)
    if spend.trade_goods < 0 or spend.trade_goods > spendable:
        raise ValueError(f"Not enough trade goods: {spend.trade_goods} > {spendable}.")
    paid = (
        sum(pay_value(state, registry, pid, player_id) for pid in spend.planets)
        + spend.trade_goods
    )
    if paid < cost:
        raise ValueError(f"Payment too low: {paid} spent < cost {cost:g}.")


def produce(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    orders: list[ProductionOrder],
    spend: Spend | None = None,
) -> GameState:
    """Wykonuje produkcję w aktywnym systemie: walidacja → płatność → postawienie jednostek.

    Reguły (RULES.md 33.2–33.3, R_production / R_producing_units / R_component_limitations):
    limit PRODUCTION wspólny dla akcji; blokada statków; siły naziemne tylko na planetach z
    producentem (lub planetach gracza/przestrzeni, gdy produkuje jednostka w przestrzeni);
    rezerwa (poza fighter/infantry); koszt płacony zasobami gotowych planet (wyczerpywane)
    i TG, nadwyżka przepada. ``spend=None`` → automatyczna płatność (``auto_pay``).

    Raises:
        ValueError: Przy złamaniu którejkolwiek reguły (stan wejściowy bez zmian).
    """
    active = production_system(state)
    orders = [o for o in orders if o.count > 0]
    validate_production(state, grid, registry, player_id, orders)
    if active is None or not orders:
        return state.clone()

    zones = allowed_ground_zones(state, registry, player_id, active)
    wanted: dict[str, int] = {}
    placed: list[tuple[ProductionOrder, str]] = []
    for o in orders:
        if o.base_type in STRUCTURES or o.base_type not in ASYNC_ID_BY_BASE_TYPE:
            raise ValueError(f"Unit {o.base_type} cannot be produced.")
        if is_space_unit(o.base_type):
            if o.zone not in (None, "space"):
                raise ValueError(f"Ship {o.base_type} can only be placed in space.")
            zone = "space"
        else:
            if o.zone is None:
                raise ValueError(f"Ground force {o.base_type} requires a planet.")
            if o.zone not in zones:
                raise ValueError(
                    f"Cannot place {o.base_type} on {o.zone}: needs a planet with your "
                    "producing unit (or your planet / space when a ship produces)."
                )
            zone = o.zone
        wanted[o.base_type] = wanted.get(o.base_type, 0) + o.count
        placed.append((o, zone))
    for base_type, count in wanted.items():
        left = reinforcements_left(state, player_id, base_type)
        if left is not None and count > left:
            raise ValueError(
                f"Not enough {base_type} in reinforcements: {count} > {left} left."
            )

    cost = order_cost(state, registry, player_id, orders)
    pay = spend if spend is not None else auto_pay(state, registry, player_id, cost)
    _validate_spend(state, registry, player_id, pay, cost)

    new_state = state.clone()
    produced_ctx = {"player": player_id, "position": active, "units": dict(wanted)}
    triggers.fire(
        new_state,
        GameEvent.PRODUCTION_USED,
        Moment.WHEN,
        subject=player_id,
        ctx=produced_ctx,
    )
    triggers.fire(
        new_state,
        GameEvent.UNITS_PRODUCED,
        Moment.WHEN,
        subject=player_id,
        ctx=produced_ctx,
    )
    system = new_state.systems[active]
    for o, zone in placed:
        unit_ops.place_units(
            new_state, system, zone, player_id, o.base_type, o.count, UnitCause.PLACED
        )
        # Siły naziemne/struktura na planecie mogą nadać kontrolę (RULES.md 23).
        if zone != "space":
            control.recompute_from_units(new_state, active, zone)
    apply_payment(new_state, player_id, list(pay.planets), pay.trade_goods)
    if active_grant(state, player_id) is not None:
        # Jednorazowa produkcja z karty nie zużywa limitu PRODUCTION kroku — tylko znika.
        new_state.production_grant = None
    else:
        new_state.production_used = state.production_used + sum(o.count for o in orders)
    placed_now = {zone: dict(by_type) for zone, by_type in state.production_placed.items()}
    for o, zone in placed:
        by_type = placed_now.setdefault(zone, {})
        by_type[o.base_type] = by_type.get(o.base_type, 0) + o.count
    new_state.production_placed = placed_now
    triggers.fire(
        new_state,
        GameEvent.UNITS_PRODUCED,
        Moment.AFTER,
        subject=player_id,
        ctx=produced_ctx,
    )
    triggers.fire(
        new_state,
        GameEvent.PRODUCTION_USED,
        Moment.AFTER,
        subject=player_id,
        ctx=produced_ctx,
    )
    return new_state


def skip_grant(state: GameState) -> GameState:
    """Rezygnacja z jednorazowej produkcji z karty (Freelancers: „you MAY produce")."""
    if state.production_grant is None:
        raise ValueError("There is no card-granted production to skip.")
    new_state = state.clone()
    new_state.production_grant = None
    return new_state
