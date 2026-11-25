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

from collections.abc import Mapping
from dataclasses import dataclass, replace

from src.core import (
    active_effects,
    capture,
    control,
    economy,
    entropic_scar,
    exhaust,
    legendary_planets,
    rules_hooks,
    timing,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, ProductionGrant
from src.core.hex_grid import HexGrid
from src.core.payment import apply_payment, flex_spend, trade_good_value
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
_SYSTEM_PRODUCER = "system"  # producent-system (Magmus Reactor), nie jednostka


@dataclass(frozen=True)
class ProductionOrder:
    """Pojedyncza pozycja zamówienia produkcji: typ jednostki + liczba SZTUK."""

    base_type: str
    count: int
    # Strefa docelowa: "space" albo id planety. None = domyślnie (statek → przestrzeń).
    zone: str | None = None
    # Pusta rezerwa (R_component_limitations): skąd zdjąć jednostki tego typu - źródła
    # ``"<pozycja>|<strefa>"`` z ``core.board_reinforcements`` (wybiera gracz).
    sources: tuple[str, ...] = ()


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
    # Komponent dający tę zdolność, gdy producent nie jest jednostką ani planetą (Magmus Reactor:
    # ``HookSource`` technologii) - UI pokazuje wtedy jego ikonę i nazwę zamiast sprite'a.
    source: rules_hooks.HookSource | None = None


# Struktury nie są "produkowane" przez PRODUCTION (to Construction) — poza zamówieniami.
STRUCTURES = {"pds", "spacedock"}

def forbidden_types(state: GameState, player_id: str, producer_type: str) -> tuple[str, ...]:
    """Typy jednostek, których producent danego typu nie może produkować (hooki FORBID).

    Np. Arborec: wartość PRODUCTION doków nie służy do piechoty (``core/hooks/factions/arborec``).
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


def _check_idle_producer_zones(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
    orders: list[ProductionOrder],
    cumulative: dict[str, int],
) -> None:
    """Siły naziemne na planecie producenta, który ich sam nie może wyprodukować (dok Arborec +
    piechota Letani), tylko gdy ten producent produkuje w tej akcji co najmniej 1 jednostkę
    (F_arborec Mitosis/1, RULES.md 33).

    Na każdą taką planetę przypisujemy 1 sztukę typu, który tamtejszy producent dopuszcza, i
    sprawdzamy warunek Halla dla reszty. Producent w przestrzeni pozwala na każdą planetę gracza.

    Raises:
        ValueError: Producent na tej planecie nic by nie wyprodukował.
    """
    prods = producers(state, registry, player_id, position)
    if any(p.zone == "space" for p in prods):
        return
    placed = {zone: dict(by_type) for zone, by_type in state.production_placed.items()}
    for o in orders:
        if o.zone not in (None, "space") and not is_space_unit(o.base_type):
            by_type = placed.setdefault(o.zone, {})
            by_type[o.base_type] = by_type.get(o.base_type, 0) + o.count
    pool = list(prods)
    rest = dict(cumulative)
    for zone, by_type in sorted(placed.items()):
        ground = [t for t, n in by_type.items() if n > 0 and not is_space_unit(t)]
        here = [p for p in pool if p.zone == zone]
        if zone == "space" or not ground or not here:
            continue
        if any(t not in p.forbids for p in here for t in ground):
            continue  # producent na tej planecie sam robi te jednostki
        for unit_type, count in sorted(rest.items()):
            host = next((p for p in here if unit_type not in p.forbids and p.value > 0), None)
            if count <= 0 or host is None:
                continue
            trial_pool = [replace(p, value=p.value - 1) if p is host else p for p in pool]
            trial_rest = {**rest, unit_type: count - 1}
            if fits_producers(trial_pool, trial_rest):
                pool, rest = trial_pool, trial_rest
                break
        else:
            raise ValueError(
                f"Units cannot be placed on {zone}: the unit with PRODUCTION there must also "
                "produce at least 1 unit (e.g. an Arborec space dock with Letani Warrior infantry)."
            )


def _planet_resources(state: GameState, registry: StaticDataRegistry, planet_id: str) -> int:
    """Zasoby planety z attachmentami (0, gdy nieznana) — ``core/planet_stats``."""
    return resources_of(state, registry, planet_id)


# Znacznik: TG z „when your units use PRODUCTION” (Tungstantus) już wzięty w tym kroku produkcji.
COMMANDER_TG_USED = "production:commander_trade_good"


def commander_trade_good_problem(state: GameState, player_id: str) -> str | None:
    """Czy gracz może teraz wziąć 1 TG przy użyciu PRODUCTION (``None`` = może) - Tungstantus.

    Granty kart (Sling Relay, Freelancers…) „produce” bez PRODUCTION - nie (F_ul tungstantus 2);
    raz na krok produkcji (wszystkie jednostki używają PRODUCTION jednocześnie)."""
    if not rules_hooks.permits(rules_hooks.POINT_PRODUCTION_GAIN_TRADE_GOOD, state, player_id):
        return "You have no ability that gives a trade good when your units use PRODUCTION."
    if active_grant(state, player_id) is not None:
        return "This production does not use the PRODUCTION ability."
    if active_effects.has_effect(state, player_id, COMMANDER_TG_USED):
        return "You already gained a trade good for this use of PRODUCTION."
    return None


def active_grant(state: GameState, player_id: str) -> ProductionGrant | None:
    """Jednorazowa produkcja z efektu karty (Freelancers) dla gracza w aktywnym systemie.

    Granty ``standalone`` (karty strategii) NIE są tu zwracane - mają zwykłe reguły produkcji.
    """
    grant = state.production_grant
    if (
        grant is not None
        and not grant.standalone
        and grant.player_id == player_id
        and (grant.free or grant.position == state.active_system)
    ):
        return grant
    return None


def standalone_grant(state: GameState) -> ProductionGrant | None:
    """Trwająca produkcja z karty strategii (poza akcją taktyczną) lub None."""
    grant = state.production_grant
    return grant if grant is not None and grant.standalone else None


def _detached_grant(state: GameState) -> ProductionGrant | None:
    """Grant działający poza aktywnym systemem: ``standalone`` (karty strategii) albo ``free``."""
    grant = state.production_grant
    return grant if grant is not None and (grant.standalone or grant.free) else None


def production_system(state: GameState) -> str | None:
    """System, w którym toczy się produkcja: pozycja granta poza akcją albo aktywny."""
    grant = _detached_grant(state)
    return grant.position if grant is not None else state.active_system


def production_player(state: GameState) -> str | None:
    """Gracz, który teraz produkuje: właściciel granta poza akcją albo aktywny gracz."""
    grant = _detached_grant(state)
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
    if (grant is not None and grant.influence_as_resources) or flex_spend(
        state, player_id
    ):  # Freelancers / Archon's Gift (RULES.md 62.9): zasoby ALBO wpływ, nie oba
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
    total = system_production_value(state, grid, registry, player_id, active)
    if total <= 0:
        return total  # brak producentów: premia do SUMY nie tworzy produkcji z niczego
    # Hook MODIFY na sumie PRODUCTION (War Machine: „+4 to the total PRODUCTION value").
    return max(
        0, rules_hooks.modify(rules_hooks.POINT_PRODUCTION_TOTAL_VALUE, state, player_id, total)
    )


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
    *,
    ignore_scar: bool = False,
) -> list[Producer]:
    """Jednostki gracza z PRODUCTION > 0 w danym systemie (R_production).

    ``ignore_scar``: jednostka w bliźnie entropicznej nadal MA PRODUCTION, choć nie może go użyć
    (F_arborec dirzuga-rophal/6) - tylko dla warunków „units that have PRODUCTION”.

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
    # Entropic Scar (RULES.md 1.5): jednostki w bliźnie nie mają PRODUCTION - także tekst doku II
    # definiujący X przestaje działać (R_entropic_scars 2.2). Zdolności planet/systemu (Aerie
    # Hololattice, Magmus Reactor, Custodian's Favour) to zdolności tekstowe - zostają.
    scar = not ignore_scar and entropic_scar.unit_abilities_blocked(state, position, registry)
    for base_type, total in ({} if scar else system.space_units.get(player_id, {})).items():
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
        for base_type, total in ({} if scar else by_player.get(player_id, {})).items():
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
    # Planeta produkująca „jak jednostka” (Aerie Hololattice): osobna zdolność PRODUCTION planety
    # gracza; siły naziemne stawia się na niej samej (F_argent).
    for planet_id, owner in sorted(system.planet_owners.items()):
        if owner != player_id:
            continue
        value = rules_hooks.modify(
            rules_hooks.POINT_PRODUCTION_PLANET_VALUE, state, player_id, 0,
            {"planet": planet_id, "position": position},
        )
        if value > 0:
            result.append(
                Producer(
                    planet_id, planet_id, 1, value, value,
                    forbidden_types(state, player_id, planet_id),
                )
            )
    # System produkujący „jak jednostka” gracza (Magmus Reactor: supernowa z jego jednostką =
    # PRODUCTION 5) - producent w PRZESTRZENI systemu (RULES.md 62.13).
    # Każdy hook MODIFY to osobna zdolność PRODUCTION z własnym źródłem (ikona/nazwa w oknie).
    system_ctx = {"position": position}
    for hook in rules_hooks.hooks_at(rules_hooks.POINT_PRODUCTION_SYSTEM_VALUE, state, player_id):
        if hook.kind is not rules_hooks.HookKind.MODIFY:
            continue
        system_value = int(hook.fn(state, player_id, system_ctx))
        if system_value > 0:
            result.append(
                Producer(
                    "space", _SYSTEM_PRODUCER, 1, system_value, system_value,
                    forbidden_types(state, player_id, _SYSTEM_PRODUCER), hook.source,
                )
            )
    # Custodian's Favour (Custodia Vigilia): kontrolowany Mecatol Rex sam ma PRODUCTION - osobna
    # zdolność (planeta, nie jednostka), więc jest oddzielnym producentem z własną wartością.
    mecatol = legendary_planets.mecatol_grants_planet(state, player_id, position)
    favour = legendary_planets.favour_production(registry)
    if mecatol is not None and favour > 0:
        result.append(
            Producer(
                mecatol, mecatol, 1, favour, favour, forbidden_types(state, player_id, mecatol)
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
    if (
        grant is not None
        and grant.producer_types
        and grant.player_id == player_id
        and grant.position == position
    ):
        # Karty strategii: tylko doki - nie Hel-Titan na tej samej planecie (F_ul hel-titan 1).
        result = [p for p in result if p.base_type in grant.producer_types]
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
        grant = state.production_grant
        if grant is not None and grant.free and grant.zone is not None:
            owned = [p for p in owned if p == grant.zone]  # Integrated Economy: ta planeta
        # C_exploration_cards (Freelancers): planeta czekająca w kolejce eksploracji jest jeszcze
        # niezdobyta (gracz zdobywa i eksploruje planety po kolei) - nie stawiamy tam sił.
        # Planeta, której karta właśnie leży odkryta, też jest dopiero w trakcie zdobywania.
        ex = state.exploration
        waiting = [*ex.queue, *([ex.current.planet] if ex.current else [])] if ex else []
        owned = [p for p in owned if p not in waiting]
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
    # R_reinforcements: przechwycone jednostki nie są w niczyjej rezerwie (RULES.md 61.5).
    captured = capture.captured_from(state, player_id, base_type)
    return max(0, cap - deployed_count(state, player_id, base_type) - captured)


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
    return resources + economy.spendable_trade_goods(state, player_id) * trade_good_value(
        state, player_id
    )


def dual_production(state: GameState, player_id: str) -> bool:
    """Czy gracz produkuje 2 myśliwce/piechoty za jeden koszt (prawo Regulated Conscription: nie).

    Hook MODIFY ``production.units_per_cost`` (delta od 2; RULES.md 51.6).
    """
    return int(rules_hooks.modify(
        rules_hooks.POINT_PRODUCTION_UNITS_PER_COST, state, player_id, 2
    )) >= 2


def _order_cost(
    registry: StaticDataRegistry,
    faction_id: str | None,
    technologies: list[str],
    order: ProductionOrder,
    *,
    dual: bool = True,
) -> float:
    """Koszt pozycji zamówienia: koszt jednostki × liczba PAR (dual = 2 za koszt).

    ``dual=False`` (Regulated Conscription, RULES.md 51.6): 1 myśliwiec/piechota za koszt.
    """
    unit = resolve_unit_variant(registry, faction_id, technologies, order.base_type)
    cost = unit.cost if unit is not None and unit.cost is not None else 0.0
    if order.base_type in _DUAL and not dual:
        return cost * 2 * order.count
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
    *,
    dual: bool = True,
) -> float:
    """Koszt całego zamówienia; sztuki tego samego typu (np. piechota na dwóch planetach)
    łączą się w pary, bo para fighter/infantry to jeden koszt niezależnie od strefy."""
    merged: dict[str, int] = {}
    for o in orders:
        if o.count > 0:
            merged[o.base_type] = merged.get(o.base_type, 0) + o.count
    return sum(
        _order_cost(registry, faction_id, technologies, ProductionOrder(bt, n), dual=dual)
        for bt, n in merged.items()
    )


_CARGO_TYPES = ("fighter", "infantry", "mech")  # myśliwce i siły naziemne (R_capacity)


def has_free_cargo(state: GameState, player_id: str) -> bool:
    """Czy ładunek produkowanych statków omija limit PRODUCTION (hook ``production.free_cargo``)."""
    return rules_hooks.permits(rules_hooks.POINT_PRODUCTION_FREE_CARGO, state, player_id)


def free_cargo_units(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    orders: list[ProductionOrder],
) -> int:
    """Ile sztuk zamówienia NIE liczy się do limitu PRODUCTION (Bellum Gloriosum, RULES.md 62.4).

    ``min(łączna capacity produkowanych statków, liczba myśliwców i sił naziemnych)``; bez hooka 0.
    """
    if not has_free_cargo(state, player_id):
        return 0
    player = state.players.get(player_id)
    if player is None:
        return 0
    capacity = 0
    cargo = 0
    for o in orders:
        if o.count <= 0:
            continue
        if o.base_type in _CARGO_TYPES:
            cargo += o.count
            continue
        unit = resolve_unit_variant(
            registry, player.faction, player.technologies, o.base_type,
            player.breakthrough_unlocked, player.breakthrough_flipped,
        )
        if unit is not None and is_space_unit(o.base_type) and unit.capacity_value:
            capacity += int(unit.capacity_value) * o.count
    return min(capacity, cargo)


_SMALL = ("fighter", "infantry")


def free_small_units(
    state: GameState, player_id: str, orders: list[ProductionOrder]
) -> int:
    """Ile myśliwców/piechoty zamówienia nie liczy się do limitu PRODUCTION (That Which Molds
    Flesh: „Up to 2 of those units”, RULES.md 62.17). Liczone narastająco w kroku produkcji:
    sztuki, które już skorzystały w tej akcji, zmniejszają pulę."""
    allowance = int(rules_hooks.modify(
        rules_hooks.POINT_PRODUCTION_FREE_SMALL_UNITS, state, player_id, 0
    ))
    if allowance <= 0:
        return 0
    before = sum(
        n for zone in state.production_placed.values() for bt, n in zone.items() if bt in _SMALL
    )
    now = sum(o.count for o in orders if o.base_type in _SMALL and o.count > 0)
    return min(allowance, before + now) - min(allowance, before)


def free_small_left(state: GameState, player_id: str) -> int:
    """Ile myśliwców/piechoty w tym kroku jeszcze nie liczy się do limitu (widok produkcji)."""
    allowance = int(rules_hooks.modify(
        rules_hooks.POINT_PRODUCTION_FREE_SMALL_UNITS, state, player_id, 0
    ))
    before = sum(
        n for zone in state.production_placed.values() for bt, n in zone.items() if bt in _SMALL
    )
    return max(0, allowance - before)


def captured_view(state: GameState, player_id: str) -> list[dict[str, object]]:
    """Przechwycone jednostki do Amalgamation (widok produkcji): typ, właściciel, sztuki."""
    if not captured_free_allowed(state, player_id):
        return []
    player = state.players[player_id]
    rows: list[dict[str, object]] = []
    for owner, units in sorted(player.captured_units.items()):
        who = state.players.get(owner)
        for base_type, count in sorted(units.items()):
            rows.append({
                "baseType": base_type, "owner": owner, "count": count,
                "faction": who.faction if who is not None else None,
                "color": who.color if who is not None else None,
            })
    for base_type, count in sorted(player.captured_tokens.items()):
        rows.append({
            "baseType": base_type, "owner": capture.TOKEN, "count": count,
            "faction": player.faction, "color": player.color,
        })
    return rows


CapturedSpend = Mapping[str, Mapping[str, int]]  # {typ: {właściciel | "token": sztuki}}


def captured_free_allowed(state: GameState, player_id: str) -> bool:
    """Czy gracz produkuje, zwracając przechwycone jednostki (Amalgamation, RULES.md 62.17)."""
    return rules_hooks.permits(rules_hooks.POINT_PRODUCTION_CAPTURED_FREE, state, player_id)


def _captured_counts(captured: CapturedSpend | None) -> dict[str, int]:
    counts = {bt: sum(int(n) for n in owners.values()) for bt, owners in (captured or {}).items()}
    return {bt: n for bt, n in counts.items() if n > 0}


def validate_captured(
    state: GameState, player_id: str, orders: list[ProductionOrder], captured: CapturedSpend | None
) -> None:
    """Zwracane przechwycone jednostki: hook pozwala, typ jest w zamówieniu, sztuki są na arkuszu.

    Raises:
        ValueError: Przy złamaniu którejkolwiek zasady.
    """
    counts = _captured_counts(captured)
    if not counts:
        return
    if not captured_free_allowed(state, player_id):
        raise ValueError("You cannot produce units by returning captured units.")
    ordered: dict[str, int] = {}
    for o in orders:
        ordered[o.base_type] = ordered.get(o.base_type, 0) + max(o.count, 0)
    for base_type, owners in (captured or {}).items():
        if counts.get(base_type, 0) > ordered.get(base_type, 0):
            raise ValueError(f"Return at most 1 captured unit per produced {base_type}.")
        held = capture.held(state, player_id, base_type)
        for owner, count in owners.items():
            if int(count) < 0 or int(count) > held.get(owner, 0):
                raise ValueError(f"You have not captured that many {base_type} units.")


def _validate_captured_war_sun(
    state: GameState, registry: StaticDataRegistry, player_id: str, captured: CapturedSpend | None
) -> None:
    """F_vuilraith Amalgamation 7: no war sun from a captured one without the war sun upgrade."""
    if _captured_counts(captured).get("warsun", 0) <= 0:
        return
    player = state.players[player_id]
    unit = resolve_unit_variant(registry, player.faction, player.technologies, "warsun")
    if unit is None or unit.id == "nowarsun":
        raise ValueError("You cannot produce a war sun without owning the war sun unit upgrade.")


def paid_orders(
    orders: list[ProductionOrder], captured: CapturedSpend | None
) -> list[ProductionOrder]:
    """Zamówienie, za które gracz PŁACI: bez sztuk wyprodukowanych za przechwycone jednostki
    (F_vuilraith Amalgamation 3-4: koszt jednostek bez zmian, zmienia się tylko wydatek)."""
    free = _captured_counts(captured)
    out: list[ProductionOrder] = []
    for o in orders:
        take = min(free.get(o.base_type, 0), o.count)
        free[o.base_type] = free.get(o.base_type, 0) - take
        if o.count - take > 0:
            out.append(replace(o, count=o.count - take))
    return out


def return_captured(state: GameState, player_id: str, captured: CapturedSpend | None) -> None:
    """Zwraca przechwycone jednostki wydane na produkcję (MUTUJE klon). Własne wracają do rezerwy
    gracza, więc można je od razu wyprodukować (F_vuilraith Amalgamation 2)."""
    for base_type, owners in sorted((captured or {}).items()):
        for owner, count in sorted(owners.items()):
            if int(count) > 0:
                capture.return_unit(state, player_id, owner, base_type, int(count))


def validate_production(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    orders: list[ProductionOrder],
    *,
    exhaust_aida: bool = False,
    captured: CapturedSpend | None = None,
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

    # Granty „wolne” (Sling Relay, Integrated Economy) mają własne ograniczenia typu i kosztu.
    free_grant = active_grant(state, player_id)
    if free_grant is not None and free_grant.free:
        if free_grant.ships_only and any(not is_space_unit(o.base_type) for o in orders):
            raise ValueError(f"{free_grant.source or "This ability"} produces ships only.")
        allowed = set(free_grant.allowed_types)
        if allowed and any(o.base_type not in allowed for o in orders):
            raise ValueError(
                f"{free_grant.source or "This ability"} can produce only: "
                f"{", ".join(sorted(allowed))}."
            )
        if free_grant.max_unit_cost is not None:
            player = state.players[player_id]
            for o in orders:
                unit = resolve_unit_variant(registry, player.faction, player.technologies,
                                            o.base_type)
                unit_cost = unit.cost if unit is not None and unit.cost is not None else 0.0
                if unit_cost > free_grant.max_unit_cost:
                    raise ValueError(
                        f"{free_grant.source or "This ability"} produces only units that cost "
                        f"{free_grant.max_unit_cost:g} or less."
                    )
        if free_grant.max_cost is not None:
            cost = order_cost(state, registry, player_id, orders, exhaust_aida=exhaust_aida)
            if cost > free_grant.max_cost:
                raise ValueError(
                    f"The combined cost {cost:g} exceeds the limit of {free_grant.max_cost:g}."
                )

    # LIMIT: łączna liczba sztuk ≤ suma PRODUCTION w aktywnym systemie (bez ładunku z
    # Bellum Gloriosum - RULES.md 62.4).
    total_units = (
        sum(o.count for o in orders)
        - free_cargo_units(state, registry, player_id, orders)
        - free_small_units(state, player_id, orders)
    )
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
    # Ładunek Bellum Gloriosum nie zajmuje PRODUCTION żadnego producenta.
    free = free_cargo_units(state, registry, player_id, orders) + free_small_units(
        state, player_id, orders
    )
    for cargo_type in _CARGO_TYPES:
        take = min(free, cumulative.get(cargo_type, 0))
        if take:
            cumulative[cargo_type] -= take
            free -= take
    if active_grant(state, player_id) is None and not fits_producers(
        producers(state, registry, player_id, active), cumulative
    ):
        raise ValueError(
            "Production limit exceeded for these unit types: part of the PRODUCTION cannot "
            "produce them (e.g. Arborec space docks cannot produce infantry)."
        )

    if active_grant(state, player_id) is None:
        _check_idle_producer_zones(state, registry, player_id, active, orders, cumulative)

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

    # BUDŻET: łączny koszt ≤ dostępne zasoby (sprawdzenie, bez wydawania). Sztuki za przechwycone
    # jednostki (Amalgamation) nie kosztują zasobów.
    validate_captured(state, player_id, orders, captured)
    _validate_captured_war_sun(state, registry, player_id, captured)
    total_cost = order_cost(
        state, registry, player_id, paid_orders(orders, captured), exhaust_aida=exhaust_aida
    )
    budget = available_budget(state, registry, player_id)
    if total_cost > budget:
        raise ValueError(
            f"Not enough resources: cost {total_cost:g} > available {budget} "
            "(ready planets + trade goods)."
        )


AIDA = "aida"


def aida_discount(state: GameState, registry: StaticDataRegistry, player_id: str) -> int:
    """Ile kosztu zdejmie AI Development Algorithm: liczba posiadanych ulepszeń jednostek."""
    player = state.players.get(player_id)
    if player is None:
        return 0
    return sum(
        1
        for tech_id in player.technologies
        if (tech := registry.technologies.get(tech_id)) is not None and "UNITUPGRADE" in tech.types
    )


def aida_ready(state: GameState, player_id: str) -> bool:
    """Czy gracz może wyczerpać AI Development Algorithm (posiada i nie jest wyczerpana)."""
    player = state.players.get(player_id)
    return (
        player is not None
        and AIDA in player.technologies
        and AIDA not in player.exhausted_technologies
    )


def cost_reduction(state: GameState, player_id: str) -> float:
    """Zniżka łącznego kosztu z hooków (np. Sarween Tools) - do podglądu kosztu w UI."""
    return -float(rules_hooks.modify(rules_hooks.POINT_PRODUCTION_COST, state, player_id, 0.0))


def cost_reduction_sources(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, float]]:
    """Rozbicie ``cost_reduction`` na źródła ``(nazwa z assetów, zniżka)`` - podpis w UI.

    Tylko hooki MODIFY punktu kosztu produkcji, które TERAZ coś zdejmują (zniżka > 0).
    """
    from src.core.component_text import describe_component

    out: list[tuple[str, float]] = []
    for hook in rules_hooks.hooks_at(rules_hooks.POINT_PRODUCTION_COST, state, player_id):
        if hook.kind is not rules_hooks.HookKind.MODIFY:
            continue
        cut = -float(hook.fn(state, player_id, {}))
        if cut > 0:
            name = describe_component(registry, hook.covers)[0] or hook.source.component_id
            out.append((name, cut))
    return out


def commander_trade_good_name(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> str | None:
    """Nazwa (z assetów) komponentu, który TERAZ daje 1 TG przy użyciu PRODUCTION (Tungstantus),
    albo ``None`` - podpis przełącznika w oknie produkcji."""
    if commander_trade_good_problem(state, player_id) is not None:
        return None
    from src.core.component_text import describe_component

    for hook in rules_hooks.hooks_at(
        rules_hooks.POINT_PRODUCTION_GAIN_TRADE_GOOD, state, player_id
    ):
        return describe_component(registry, hook.covers)[0] or hook.source.component_id
    return None


def order_cost(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    orders: list[ProductionOrder],
    *,
    exhaust_aida: bool = False,
) -> float:
    """Łączny koszt zamówienia (para fighter/infantry = jeden koszt).

    ``exhaust_aida=True`` - gracz ŚWIADOMIE wyczerpuje AI Development Algorithm: łączny koszt
    spada o liczbę jego ulepszeń jednostek (RULES.md 57).
    """
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    base_cost = _total_cost(
        registry, faction_id, technologies, orders, dual=dual_production(state, player_id)
    )
    if exhaust_aida:
        if not aida_ready(state, player_id):
            raise ValueError("AI Development Algorithm is not ready.")
        base_cost = max(0.0, base_cost - aida_discount(state, registry, player_id))
    if rules_hooks.permits(rules_hooks.POINT_PRODUCTION_FREE, state, player_id):
        return 0.0  # Harrugh Gefhara: koszt 0, limity PRODUCTION zostają (F_hacan)
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
    worth = trade_good_value(state, player_id)
    return Spend(tuple(pid for pid, _ in chosen), min(tg, -(-missing // worth)))


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
        + spend.trade_goods * trade_good_value(state, player_id)
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
    *,
    exhaust_aida: bool = False,
    captured: CapturedSpend | None = None,
    commander_trade_good: bool = False,
) -> GameState:
    """Wykonuje produkcję w aktywnym systemie: walidacja → płatność → postawienie jednostek.

    ``commander_trade_good`` - gracz bierze 1 TG „when your units use PRODUCTION” (Tungstantus,
    PERMIT ``production.gain_trade_good``) PRZED zapłatą, więc może go wydać na te jednostki.

    Reguły (RULES.md 33.2–33.3, R_production / R_producing_units / R_component_limitations):
    limit PRODUCTION wspólny dla akcji; blokada statków; siły naziemne tylko na planetach z
    producentem (lub planetach gracza/przestrzeni, gdy produkuje jednostka w przestrzeni);
    rezerwa (poza fighter/infantry); koszt płacony zasobami gotowych planet (wyczerpywane)
    i TG, nadwyżka przepada. ``spend=None`` → automatyczna płatność (``auto_pay``).

    Raises:
        ValueError: Przy złamaniu którejkolwiek reguły (stan wejściowy bez zmian).
    """
    timing.require_no_limit_window(state)  # nadwyżka puli floty najpierw (RULES.md 42.1)
    active = production_system(state)
    orders = [o for o in orders if o.count > 0]
    if commander_trade_good and active is not None and orders:
        reason = commander_trade_good_problem(state, player_id)
        if reason is not None:
            raise ValueError(reason)
        state = state.clone()
        # F_ul tungstantus 1.1: TG zdobyty od razu (zdarzenie TG) - można nim zapłacić; bez
        # jednostek nic (1.2).
        economy.gain_trade_goods(state, player_id, 1)
        active_effects.add_effect(state, COMMANDER_TG_USED, Duration.TURN, owner=player_id)
    validate_production(
        state, grid, registry, player_id, orders, exhaust_aida=exhaust_aida, captured=captured
    )
    if active is None or not orders:
        return state.clone()
    if _captured_counts(captured):
        # Amalgamation: zwrot PRZED sprawdzeniem rezerwy - własna jednostka wraca do rezerwy.
        state = state.clone()
        return_captured(state, player_id, captured)

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
    board_takes: list[tuple[str, str]] = []  # (typ, źródło) - zdjęte z planszy przed postawieniem
    for base_type, count in wanted.items():
        left = reinforcements_left(state, player_id, base_type)
        if left is not None and count > left:
            # R_component_limitations: brakujące sztuki gracz może zdjąć z systemów bez swojego
            # żetonu (``core.board_reinforcements``) - tylko wskazane przez niego źródła.
            sources = [src for o in orders if o.base_type == base_type for src in o.sources]
            if len(sources) < count - left:
                raise ValueError(
                    f"Not enough {base_type} in reinforcements: {count} > {left} left "
                    "(choose units on the board to take, from systems without your command token)."
                )
            board_takes += [(base_type, src) for src in sources[: count - left]]

    cost = order_cost(
        state, registry, player_id, paid_orders(orders, captured), exhaust_aida=exhaust_aida
    )
    pay = spend if spend is not None else auto_pay(state, registry, player_id, cost)
    _validate_spend(state, registry, player_id, pay, cost)

    new_state = state.clone()
    placed_zones: dict[str, dict[str, int]] = {}
    for o, zone in placed:
        by_type = placed_zones.setdefault(zone, {})
        by_type[o.base_type] = by_type.get(o.base_type, 0) + o.count
    # ``zones`` = gdzie stanęły jednostki tego zamówienia (agent Argent przenosi siły naziemne).
    produced_ctx = {"player": player_id, "position": active, "units": dict(wanted),
                    "zones": placed_zones}
    # Granty z kart (Sling Relay, Integrated Economy, Freelancers) mówią „produce", a nie „use
    # PRODUCTION": nie odpalają zdarzenia PRODUCTION_USED (Self-Assembly, Sarween itd.).
    free_grant = active_grant(state, player_id)
    uses_production = free_grant is None
    if uses_production:
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
    from src.core import board_reinforcements  # lokalnie: moduł woła production

    for base_type, source in board_takes:
        board_reinforcements.take_from_board(new_state, player_id, base_type, source)
    system = new_state.systems[active]
    for o, zone in placed:
        unit_ops.place_units(
            new_state, system, zone, player_id, o.base_type, o.count, UnitCause.PLACED
        )
        # Siły naziemne/struktura na planecie mogą nadać kontrolę (RULES.md 23).
        if zone != "space":
            control.recompute_from_units(new_state, active, zone)
    apply_payment(new_state, player_id, list(pay.planets), pay.trade_goods)
    if exhaust_aida:
        exhaust.exhaust_technology(new_state, player_id, AIDA)
    if active_grant(state, player_id) is not None:
        # Jednorazowa produkcja z karty nie zużywa limitu PRODUCTION kroku — tylko znika
        # (albo przechodzi do kolejnego systemu z kolejki).
        new_state.production_grant = next_grant(state.production_grant)
        _grant_finished(new_state)
    else:
        new_state.production_used = (
            state.production_used
            + sum(o.count for o in orders)
            - free_cargo_units(state, registry, player_id, orders)
            - free_small_units(state, player_id, orders)
        )
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
    if uses_production:
        triggers.fire(
            new_state,
            GameEvent.PRODUCTION_USED,
            Moment.AFTER,
            subject=player_id,
            ctx=produced_ctx,
        )
    if free_grant is not None and free_grant.free:
        # Sling Relay / Integrated Economy działają poza krokiem PRODUCTION akcji taktycznej, więc
        # nikt nie sprawdzi limitów „przy wyjściu z kroku": capacity i fleet pool liczymy od razu
        # (okno usuwania nadwyżki otwiera się natychmiast po produkcji).
        from src.core import capacity, fleet_pool

        new_state = capacity.open_capacity_check(new_state, registry, active)
        new_state = fleet_pool.open_fleet_pool_check(new_state, active)
    return new_state


def skip_grant(state: GameState) -> GameState:
    """Rezygnacja z jednorazowej produkcji z karty (Freelancers: „you MAY produce")."""
    if state.production_grant is None:
        raise ValueError("There is no card-granted production to skip.")
    if state.production_grant.mandatory:
        raise ValueError(
            f"{state.production_grant.source or 'This card'} cannot be used without producing "
            "a unit - produce one."
        )
    new_state = state.clone()
    new_state.production_grant = next_grant(state.production_grant)
    _grant_finished(new_state)
    return new_state


def _grant_finished(state: GameState) -> None:
    """Grant z karty eksploracji (Freelancers) się skończył: eksploracja planety dobiega końca."""
    if state.production_grant is None and state.exploration is not None:
        from src.core import exploration  # lokalnie: exploration importuje ten moduł

        exploration.after_grant(state)


def foreign_grant_reason(state: GameState, player_id: str) -> str | None:
    """Powód wstrzymania gracza, gdy INNY gracz produkuje z grantu w tej akcji (np. Dirzuga
    Rophal: „The unit is produced before ships move” - F_arborec). ``None`` = można działać."""
    grant = state.production_grant
    if grant is None or grant.player_id == player_id or grant.standalone:
        return None
    who = grant.source or "Another player's production"
    return f"{who}: wait until {grant.player_id} finishes producing."


def next_grant(grant: ProductionGrant | None) -> ProductionGrant | None:
    """Grant dla następnego systemu z ``queue`` (``None``, gdy kolejka pusta)."""
    if grant is None or not grant.queue:
        return None
    return grant.model_copy(update={"position": grant.queue[0], "queue": list(grant.queue[1:])})
