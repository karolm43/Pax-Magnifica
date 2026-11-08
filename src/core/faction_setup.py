"""Setup frakcji — parser ``startingFleet`` i rozstawienie jednostek startowych.

Przekłada definicję frakcji (``FactionDef``) na konkretny stan: kafelek domowy na
slocie koloru gracza, flotę startową (statki w przestrzeni, siły naziemne/struktury
na planetach domowych) oraz kontrolę planet domowych. Format ``startingFleet`` i
reguła sufiksu planety: patrz docs/RULES.md 2c.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.core import control, unit_ops
from src.core.game_state import GameState, PlayerState, SystemState
from src.core.models import FactionDef
from src.core.unit_catalog import FLEET_CODE_TO_BASE_TYPE, Placement, placement_of

# Frakcje z systemem domowym POZA planszą (RULES.md 17). Brama (``home_system``
# frakcji) stoi na slocie; prawdziwy dom (``real_home_system`` z planetą) ląduje
# w rogu obszaru gry. Źródło: AsyncTI4 PlayerSetupService (mapowanie 17→51, 94→118).
OFF_BOARD_HOME: dict[str, str] = {
    "ghost": "51",  # brama 17 (Creuss Gate) -> dom 51 (Creuss)
    "crimson": "118",  # brama 94 (The Sorrow) -> dom 118
}

# Róg off-board wg slotu domowego gracza (RULES.md 17; z PlayerSetupService).
_OFF_BOARD_CORNER_BY_SLOT: dict[str, str] = {
    "301": "tr",
    "304": "tr",
    "307": "br",
    "310": "br",
    "313": "bl",
    "316": "bl",
}


def off_board_corner(home_slot: str, taken: set[str]) -> str:
    """Róg off-board (``tr``/``br``/``bl``) dla slotu domowego, z obsługą kolizji.

    Reguła z bota: slot → róg (tabela); gdy róg zajęty (``taken``), zamień tr↔br.
    Domyślnie ``tr`` dla nieznanych slotów.
    """
    corner = _OFF_BOARD_CORNER_BY_SLOT.get(home_slot, "tr")
    if corner in taken:
        corner = "br" if corner == "tr" else "tr"
    return corner

# Token startingFleet: opcjonalna liczba, kod jednostki, opcjonalny sufiks planety.
_FLEET_TOKEN = re.compile(r"^(?:(\d+)\s+)?([a-z]+)(?:\s+([a-z0-9.]+))?$", re.IGNORECASE)


@dataclass(frozen=True)
class FleetEntry:
    """Pojedynczy wpis floty startowej po sparsowaniu."""

    base_type: str
    count: int
    placement: Placement
    # Prefiks planety (sufiks z tokenu) — tylko dla jednostek naziemnych/struktur.
    planet_prefix: str | None = None


@dataclass(frozen=True)
class SetupPlan:
    """Pełny plan rozstawienia startowego frakcji dla jednego gracza."""

    faction_id: str
    home_system: str | None
    home_planets: list[str]
    starting_tech: list[str]
    commodities: int
    # Statki w przestrzeni: {base_type: liczba}.
    space_units: dict[str, int] = field(default_factory=dict)
    # Naziemne/struktury: {planet_id: {base_type: liczba}}.
    planet_units: dict[str, dict[str, int]] = field(default_factory=dict)


def _resolve_planet(suffix: str, home_planets: list[str]) -> str | None:
    """Dopasowuje sufiks z ``startingFleet`` do planety domowej (patrz RULES.md 2c).

    Reguła dopasowania (dwustopniowa, zweryfikowana na base+pok):
    1. **Prefiks** — sufiks jest początkiem nazwy planety (np. ``n`` → ``nestphar``,
       ``h`` → ``hercant``). Pokrywa niemal wszystkie frakcje.
    2. **Pierwsza litera + litera różnicująca** — gdy planety domowe mają wspólny
       prefiks, AsyncTI4 używa skrótu "pierwsza litera + pierwsza litera, w której
       nazwy się różnią". Przykład Xxcha: ``archonren``/``archontau`` → ``ar``/``at``
       (wspólne ``archon``, różnica na pozycji 6: ``r`` vs ``t``).

    Zwraca id planety lub None, gdy nie da się jednoznacznie dopasować.
    """
    suffix = suffix.lower()
    planets_lower = [(p, p.lower()) for p in home_planets]

    # 1) Dopasowanie prefiksowe (najczęstszy przypadek).
    prefix_matches = [orig for orig, low in planets_lower if low.startswith(suffix)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    exact = [orig for orig, low in planets_lower if low == suffix]
    if len(exact) == 1:
        return exact[0]

    # 2) Skrót "pierwsza litera + litera na pierwszej pozycji różnicującej".
    #    Gdy planety mają wspólny prefiks (np. "archon"), AsyncTI4 bierze pierwszą
    #    literę + literę z pierwszej pozycji, w której nazwy się różnią.
    if len(suffix) == 2 and len(home_planets) >= 2:
        diff_idx = _first_differing_index([low for _, low in planets_lower])
        if diff_idx is not None:
            key_matches = [
                orig
                for orig, low in planets_lower
                if len(low) > diff_idx
                and low[0] == suffix[0]
                and low[diff_idx] == suffix[1]
            ]
            if len(key_matches) == 1:
                return key_matches[0]

    return None


def _first_differing_index(names: list[str]) -> int | None:
    """Pierwszy indeks, na którym nazwy planet się różnią (lub None, gdy brak)."""
    if len(names) < 2:
        return None
    shortest = min(len(n) for n in names)
    for i in range(shortest):
        if len({n[i] for n in names}) > 1:
            return i
    return None


def resolve_starting_tech(
    faction: FactionDef, chosen_tech: list[str] | None
) -> list[str]:
    """Ustala technologie startowe gracza (stała lista albo wybór z opcji).

    - Frakcja ze STAŁĄ listą (``starting_tech``) i bez opcji: zwraca tę listę
      (``chosen_tech`` ignorowane).
    - Frakcja z WYBOREM (``starting_tech_amount > 0``): wymaga ``chosen_tech`` o
      dokładnej liczności, złożonego wyłącznie z dozwolonych ``starting_tech_options``.

    Raises:
        ValueError: Gdy wybór jest wymagany a nieprawidłowy (zła liczność/opcje).
    """
    if faction.starting_tech_amount <= 0:
        return list(faction.starting_tech)
    # Frakcja z ODROCZONYM wyborem technologii: ``starting_tech_amount > 0``, ale PUSTA
    # lista opcji (np. The Deepwrought Scholarate — „research technology twice"; podobnie
    # Keleres zależny od technologii innych graczy). Taka frakcja wybiera technologie
    # dopiero w grze, po pozostałych graczach (docs/rules_tirules/F_deepwrought.md,
    # F_keleres.md; docs/RULES.md 16), więc przy setupie startuje BEZ technologii.
    # UI nie pokazuje jej panelu wyboru — zwracamy pustą listę zamiast błędu/fallbacku.
    if not faction.starting_tech_options:
        return []
    # Brak wyboru od gracza → domyślnie pierwsze N opcji (żeby szybka gra nie padła).
    # UI pokazuje menu wyboru; to tylko bezpieczny fallback dla quick-startu.
    if chosen_tech is None:
        return list(faction.starting_tech_options[: faction.starting_tech_amount])
    chosen = chosen_tech
    options = set(faction.starting_tech_options)
    if len(chosen) != faction.starting_tech_amount:
        raise ValueError(
            f"Faction {faction.id} chooses {faction.starting_tech_amount} starting technologies "
            f"- {len(chosen)} given."
        )
    invalid = [t for t in chosen if t not in options]
    if invalid:
        raise ValueError(
            f"Invalid starting technologies for {faction.id}: {invalid}. "
            f"Allowed: {sorted(options)}."
        )
    if len(set(chosen)) != len(chosen):
        raise ValueError(f"Duplicate starting technologies: {chosen}.")
    return list(chosen)


def apply_setup_to_state(
    state: GameState,
    *,
    player_id: str,
    color: str,
    faction: FactionDef,
    home_position: str,
    chosen_tech: list[str] | None = None,
    unit_position: str | None = None,
    unit_system_id: str | None = None,
) -> GameState:
    """Nanosi setup frakcji gracza na stan gry i zwraca nowy ``GameState``.

    Tworzy/aktualizuje gracza (frakcja, kolor, technologie, towary), rozstawia flotę
    startową — statki w przestrzeni, siły naziemne/struktury na planetach — i ustawia
    kontrolę planet domowych.

    Args:
        state: Bieżący stan (kopiowany; wejście nie jest mutowane).
        player_id: Identyfikator gracza (np. kolor lub nazwa).
        color: Kolor gracza (3-literowy kod, np. ``"red"`` — do grafik jednostek).
        faction: Definicja frakcji.
        home_position: Pozycja ``RPP`` slotu domowego (kotwica heksa stat-area).
        chosen_tech: Wybrane technologie startowe (dla frakcji z wyborem).
        unit_position: Pozycja, na której rozkładamy flotę/planety. Domyślnie
            ``home_position``; dla Ghost/Crimson to róg off-board (RULES.md 17), bo
            prawdziwy dom leży poza planszą.
        unit_system_id: System_id kafelka z jednostkami. Domyślnie ``faction.home_system``;
            dla Ghost/Crimson to prawdziwy dom (``OFF_BOARD_HOME``), nie brama.

    Returns:
        Nowy ``GameState`` z naniesionym setupem.

    Raises:
        ValueError: Gdy frakcja wymaga wyboru technologii a ``chosen_tech`` jest zły.
    """
    plan = build_setup_plan(faction)
    starting_tech = resolve_starting_tech(faction, chosen_tech)
    new_state = state.clone()

    # Gdzie realnie stoją jednostki/planety (off-board dla Ghost/Crimson).
    unit_pos = unit_position or home_position
    system_id = unit_system_id or faction.home_system or ""

    # Gracz (home_position = slot domowy / kotwica stat-area; nawet dla off-board
    # frakcji heks tożsamości jest przy slocie bramy).
    new_state.players[player_id] = PlayerState(
        player_id=player_id,
        faction=faction.id,
        color=color,
        home_position=home_position,
        # Start gry = ZERO commodities (tirules R_commodities: „A player starts the
        # game with zero commodities"). ``plan.commodities`` to commodity VALUE z karty
        # frakcji = MAKSIMUM, nie ilość startowa — zapisujemy je jako ``commodity_value``.
        commodities=0,
        commodity_value=plan.commodities,
        technologies=list(starting_tech),
        controlled_planets=list(plan.home_planets),
    )

    # System z jednostkami + kontrolą planet domowych.
    system = new_state.systems.get(unit_pos)
    if system is None:
        system = SystemState(position=unit_pos, system_id=system_id)
    else:
        system.system_id = system_id

    if plan.space_units:
        unit_ops.replace_zone_units(new_state, system, "space", player_id, plan.space_units)
    for planet_id, units in plan.planet_units.items():
        unit_ops.replace_zone_units(new_state, system, planet_id, player_id, units)
    new_state.systems[unit_pos] = system
    for planet_id in plan.home_planets:
        control.set_planet_control(new_state, unit_pos, planet_id, player_id)
    return new_state


def parse_starting_fleet(
    fleet: str, home_planets: list[str]
) -> list[FleetEntry]:
    """Parsuje ``startingFleet`` na listę wpisów (patrz docs/RULES.md 2c).

    Args:
        fleet: Napis floty startowej, np. ``"cv,2 dd,2 ff,4 inf c,sd c"``.
        home_planets: Planety domowe frakcji (do rozwiązania sufiksu planety).

    Returns:
        Lista ``FleetEntry``. Jednostki naziemne/struktury mają ``planet_prefix``.

    Raises:
        ValueError: Gdy token jest niepoprawny lub kod jednostki nieznany.
    """
    entries: list[FleetEntry] = []
    for raw in fleet.split(","):
        token = raw.strip()
        if not token:
            continue
        match = _FLEET_TOKEN.match(token)
        if match is None:
            raise ValueError(f"Invalid startingFleet token: {token!r}")
        count_str, code, suffix = match.groups()
        base_type = FLEET_CODE_TO_BASE_TYPE.get(code.lower())
        if base_type is None:
            raise ValueError(f"Unknown unit code in startingFleet: {code!r}")
        count = int(count_str) if count_str else 1
        placement = placement_of(base_type)
        prefix = suffix if placement is Placement.PLANET else None
        entries.append(
            FleetEntry(
                base_type=base_type,
                count=count,
                placement=placement,
                planet_prefix=prefix,
            )
        )
    return entries


def build_setup_plan(faction: FactionDef) -> SetupPlan:
    """Buduje plan rozstawienia startowego dla frakcji.

    Statki trafiają do ``space_units``; siły naziemne i struktury na planetę wskazaną
    sufiksem (lub pierwszą planetę domową, gdy sufiks nierozwiązywalny — awaryjnie).
    """
    plan = SetupPlan(
        faction_id=faction.id,
        home_system=faction.home_system,
        home_planets=list(faction.home_planets),
        starting_tech=list(faction.starting_tech),
        commodities=faction.commodities,
    )

    if not faction.starting_fleet:
        return plan

    for entry in parse_starting_fleet(faction.starting_fleet, faction.home_planets):
        if entry.placement is Placement.SPACE:
            plan.space_units[entry.base_type] = (
                plan.space_units.get(entry.base_type, 0) + entry.count
            )
            continue

        # Naziemne/struktury: ustal planetę.
        planet = None
        if entry.planet_prefix is not None:
            planet = _resolve_planet(entry.planet_prefix, faction.home_planets)
        if planet is None and faction.home_planets:
            planet = faction.home_planets[0]  # awaryjnie pierwsza planeta domowa
        if planet is None:
            continue  # brak planet domowych — pomijamy (nie powinno wystąpić)
        per_planet = plan.planet_units.setdefault(planet, {})
        per_planet[entry.base_type] = per_planet.get(entry.base_type, 0) + entry.count

    return plan
