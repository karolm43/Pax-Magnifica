"""web-data: planety i jednostki gracza (kontrola, rozstawione i posiadane jednostki, ekonomia).

Wydzielone z ``web_data.py``.
"""

from __future__ import annotations

from typing import Any

from src.core.combat import (
    BREAKTHROUGH_UNIT_IDS,
    FLIP_SIDE_UNIT_IDS,
    FLIPPED_BREAKTHROUGH_UNIT_IDS,
)
from src.core.game_state import GameState
from src.core.planet_stats import planet_stats
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import (
    ASYNC_ID_BY_BASE_TYPE,
    UNIT_CAP_BY_ASYNC_ID,
)


def _controlled_planets_from_systems(player_id: str, state: GameState) -> list[str]:
    """Lista planet kontrolowanych przez gracza wg ``planet_owners`` w systemach.

    Opcja A (jedno źródło prawdy): kontrola planety mieszka w systemie
    (``SystemState.planet_owners``), a lista planet gracza jest z niego WYLICZANA.
    Dzięki temu panel gracza (``playerData.planets``/ekonomia) i mapa pokazują to
    samo — koniec desyncu z Bug 3. Sortujemy dla stabilności dokumentu.
    """
    owned = [
        planet_id
        for system in state.systems.values()
        for planet_id, owner in system.planet_owners.items()
        if owner == player_id
    ]
    return sorted(owned)


def _deployed_counts_by_player(state: GameState) -> dict[str, dict[str, int]]:
    """Liczy jednostki na planszy per gracz i ``asyncId`` (przestrzeń + planety).

    Zwraca ``{player_id: {asyncId: liczba}}``. Używane do ``unitCounts.deployedCount``
    (ile sztuk danego typu stoi na mapie — reszta to rezerwa).
    """
    result: dict[str, dict[str, int]] = {}

    def add(player_id: str, base_type: str, count: int) -> None:
        async_id = ASYNC_ID_BY_BASE_TYPE.get(base_type)
        if async_id is None or count <= 0:
            return
        bucket = result.setdefault(player_id, {})
        bucket[async_id] = bucket.get(async_id, 0) + count

    for system in state.systems.values():
        for player_id, by_type in system.space_units.items():
            for base_type, count in by_type.items():
                add(player_id, base_type, count)
        for by_player in system.planet_units.values():
            for player_id, by_type in by_player.items():
                for base_type, count in by_type.items():
                    add(player_id, base_type, count)
    return result


def _units_owned_for_faction(
    faction_id: str | None,
    technologies: list[str],
    registry: StaticDataRegistry,
    breakthrough_unlocked: bool = False,
    breakthrough_flipped: bool = False,
) -> list[str]:
    """Lista ID jednostek posiadanych przez gracza (baza/ulepszenie, generyczne/frakcyjne).

    Reguły (zgodne z AsyncTI4, nie z pamięci — potwierdzone na danych żywej gry,
    patrz docs/RULES.md 10):
    - Dla każdego ``asyncId`` wybieramy DOKŁADNIE JEDNĄ jednostkę. Posiadanie dwóch
      jednostek o tym samym asyncId (np. bazowa + frakcyjna) psuło ``lookupUnit``.
    - Wariant ULEPSZONY (``upgrades_from_unit_id``) wygrywa z bazowym TYLKO gdy gracz
      zbadał jego wymaganą technologię (``required_tech_id``). W przeciwnym razie
      gracz ma wariant bazowy (Bug 11: dawniej upgrade był zawsze pomijany, więc
      panel i mapa pokazywały statystyki bazowe nawet po zbadaniu technologii).
    - Jednostki za technologią (np. War Sun, ``required_tech_id="ws"``) nie są
      posiadane, dopóki gracz jej nie zbada — chyba że frakcja ma wariant wrodzony
      bez wymaganej technologii (np. Muaat ``muaat_warsun``).
    - Wariant frakcyjny gracza = jednostka z listy ``FactionDef.units`` ALBO z pasującym
      polem ``faction``. Lista ``units`` frakcji jest AUTORYTATYWNA: Keleres dzieli
      ``keleres_flagship``/``keleres_mech`` między 3 warianty, ale pole ``faction``
      jednostki wskazuje tylko jeden z nich — bez listy ``units`` dwa warianty gubiły
      swój flagship/mech (RULES.md 10).
    - Pomija placeholdery (``nowarsun``) i niestandardowe asyncId (cavalry itd.).
    """
    standard_async = set(ASYNC_ID_BY_BASE_TYPE.values())
    techs = {t.lower() for t in technologies}
    faction = registry.factions.get(faction_id) if faction_id else None
    faction_unit_ids = set(faction.units) if faction is not None else set()

    def has_tech(unit: Any) -> bool:
        """Czy gracz spełnia wymóg technologiczny jednostki (brak wymogu = tak)."""
        req = unit.required_tech_id
        return req is None or req.lower() in techs

    def is_faction_unit(unit: Any) -> bool:
        """Czy jednostka należy do frakcji gracza (lista units frakcji lub pole faction).

        Ulepszenie dziedziczy przynależność po bazie (``upgrades_from_unit_id``), bo
        lista ``units`` frakcji wymienia tylko warianty bazowe (np. ``keleres_flagship``),
        nie ulepszone.
        """
        if unit.id in faction_unit_ids:
            return True
        if unit.upgrades_from_unit_id in faction_unit_ids:
            return True
        return unit.faction is not None and unit.faction == faction_id

    # Dla każdego asyncId zbieramy kandydatów w 4 kubełkach wg (frakcja?, ulepszenie?).
    # Wybór: frakcyjny-ulepszony > generyczny-ulepszony > frakcyjny-bazowy >
    # generyczny-bazowy. Ulepszenie liczy się tylko, gdy gracz ma wymaganą technologię
    # (God-Mode może dać generyczne ulepszenie także frakcji z własnym wariantem bazowym).
    faction_upgraded: dict[str, str] = {}
    faction_base: dict[str, str] = {}
    generic_upgraded: dict[str, str] = {}
    generic_base: dict[str, str] = {}
    for unit in registry.units.values():
        if unit.async_id is None or unit.async_id not in standard_async:
            continue  # pomija cavalry/placeholdery/nietypowe asyncId
        if unit.id == "nowarsun":
            continue
        if unit.id in BREAKTHROUGH_UNIT_IDS and not breakthrough_unlocked:
            continue  # Corsair/Eidolon Maximum dopiero po odblokowaniu przełomu
        if unit.id in FLIP_SIDE_UNIT_IDS or (
            unit.id in FLIPPED_BREAKTHROUGH_UNIT_IDS and not breakthrough_flipped
        ):
            continue  # rewers karty (Z-Grav) / Eidolon Maximum przed odwróceniem przełomu
        is_upgrade = unit.upgrades_from_unit_id is not None
        if not has_tech(unit):
            continue  # jednostka/ulepszenie za technologią, której gracz nie ma
        is_faction = unit.faction is not None
        belongs = is_faction_unit(unit)
        if is_faction and not belongs:
            continue  # cudzy wariant frakcyjny — pomijamy
        if unit.id in FLIPPED_BREAKTHROUGH_UNIT_IDS:
            faction_upgraded[unit.async_id] = unit.id  # leży NA karcie mecha (RULES.md 62.15)
        elif unit.id in BREAKTHROUGH_UNIT_IDS and is_upgrade:
            # Corsair leży NA Cruiser II (RULES.md 62.8): tylko z jego technologią, wtedy wygrywa
            # (jak ``combat.resolve_unit_variant``).
            below = registry.units.get(unit.upgrades_from_unit_id or "")
            if below is not None and not has_tech(below):
                continue
            faction_upgraded[unit.async_id] = unit.id
        elif belongs and is_upgrade:
            faction_upgraded.setdefault(unit.async_id, unit.id)
        elif belongs:
            faction_base.setdefault(unit.async_id, unit.id)
        elif is_upgrade:
            generic_upgraded.setdefault(unit.async_id, unit.id)
        else:
            generic_base.setdefault(unit.async_id, unit.id)

    owned: list[str] = []
    for async_id in standard_async:
        chosen = (
            faction_upgraded.get(async_id)
            or generic_upgraded.get(async_id)
            or faction_base.get(async_id)
            or generic_base.get(async_id)
        )
        if chosen is not None:
            owned.append(chosen)
    return sorted(owned)


def _unit_counts(deployed: dict[str, int]) -> dict[str, dict[str, int]]:
    """Buduje ``unitCounts`` = ``{asyncId: {unitCap, deployedCount}}`` dla gracza.

    ``unitCap`` z limitów supply (``UNIT_CAP_BY_ASYNC_ID``, źródło: AsyncTI4),
    ``deployedCount`` z liczby jednostek na planszy. Panel rezerwy pokazuje
    ``unitCap - deployedCount``.
    """
    return {
        async_id: {"unitCap": cap, "deployedCount": deployed.get(async_id, 0)}
        for async_id, cap in UNIT_CAP_BY_ASYNC_ID.items()
    }


class _Economy:
    """Rozbicie ekonomii planet gracza (reguła AsyncTI4, RULES.md 7)."""

    __slots__ = ("resources", "influence", "opt_res", "opt_inf", "flex")

    def __init__(self) -> None:
        self.resources = 0
        self.influence = 0
        self.opt_res = 0
        self.opt_inf = 0
        self.flex = 0


def _planet_economy(
    controlled_planets: list[str], registry: StaticDataRegistry, state: GameState
) -> _Economy:
    """Liczy ekonomię kontrolowanych planet: sumy + optimal/flex.

    Reguła per planeta (źródło: AsyncTI4 ``Planet.getOptimal*``, RULES.md 7):
    - optimalResources = resources, gdy resources > influence, inaczej 0;
    - optimalInfluence = influence, gdy influence > resources, inaczej 0;
    - flex = wartość, gdy resources == influence, inaczej 0.
    """
    econ = _Economy()
    for planet_id in controlled_planets:
        stats = planet_stats(state, registry, planet_id)
        if stats is None:
            continue
        res, inf = stats.resources, stats.influence
        econ.resources += res
        econ.influence += inf
        if res > inf:
            econ.opt_res += res
        elif inf > res:
            econ.opt_inf += inf
        else:
            econ.flex += res
    return econ
