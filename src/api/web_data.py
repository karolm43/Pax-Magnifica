"""Serializacja stanu gry do formatu ``web-data`` frontendu (ti4_web).

Frontend ``ti4_web`` renderuje planszę z JEDNEGO dokumentu HTTP
(``GET /api/public/game/{gameId}/web-data``) o kształcie ``PlayerDataResponse``.
Ten moduł buduje ten dokument z naszego ``GameState`` + ``HexGrid`` + rejestru,
emitując wyłącznie STAN (pozycje, jednostki, gracze) — statyczne katalogi
(definicje jednostek/planet/systemów) frontend ma wbudowane i rozwiązuje po ID.

Reguły mapowania (zweryfikowane w kodzie frontendu, nie z pamięci):

- Pozycje: ``tilePositions`` to lista napisów ``"<pozycja>:<systemId>"``. Frontend
  liczy piksele sam z ``tileCoordinates`` po kluczu pozycji AsyncTI4 — nasze pozycje
  używają tych samych identyfikatorów (``000``, ``101``…), więc nie wysyłamy ``(q,r,s)``.
- Jednostki: w ``tileUnitData`` jednostki są kluczowane przez ``entityId = asyncId``
  (``ff``, ``gf``, ``mf``, ``sd``, ``ca``…), zgrupowane per frakcja. Kod rozmieszczania
  frontendu rozpoznaje ``gf``/``mf``/``ff``/``sd`` po ``asyncId`` — nie po ID rejestru.
- Planety: ``tileUnitData[pos].planets`` kluczowane nazwą/ID planety zgodną ze
  statycznymi danymi systemu frontendu (to te same ID AsyncTI4 co w naszym rejestrze).
- Frakcja jednostek w ``space``/``planets`` to identyfikator frakcji gracza; gdy gracz
  nie ma przypisanej frakcji, używamy jego ``player_id`` jako klucza zastępczego.

Frontend oczekuje wielu pól opcjonalnych (cele, prawa, karty strategii, pula kart);
emitujemy je puste/domyślne, by viewer działał bez pełnej logiki rundy.
"""

from __future__ import annotations

from typing import Any

from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.map_string import HOME_SLOT_SYSTEM_ID
from src.core.positions import load_positions
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import (
    ASYNC_ID_BY_BASE_TYPE,
    UNIT_CAP_BY_ASYNC_ID,
    is_space_unit,
)

# Wersja schematu dokumentu web-data wymagana przez frontend ti4_web
# (``REQUIRED_VERSION_SCHEMA`` w ``GameMapPage.tsx``). Dokument ze starszą/brakującą
# wersją powoduje ekran "Update Needed" zamiast renderu planszy.
WEB_DATA_SCHEMA_VERSION = 5


# Mapowanie naszej 4-wartościowej fazy na string ``GamePhase`` frontendu
# (małe litery, z podfazami). Frontend indeksuje PHASE_CONFIGS dokładnie po tych
# wartościach — casing i granularność muszą się zgadzać (patrz GameStatePanel.tsx).
_PHASE_TO_WEB: dict[str, str] = {
    "STRATEGY": "strategy",
    "ACTION": "action",
    "STATUS": "status.scoring",
    "AGENDA": "agenda.voting",
}


def _to_web_phase(phase: object) -> str:
    """Zwraca string fazy w formacie frontendu (``GamePhase``)."""
    return _PHASE_TO_WEB.get(str(phase), "unknown")


def _effective_active_id(state: GameState) -> str | None:
    """Spójny identyfikator aktywnego gracza (Bug 7).

    Gracz nie może być jednocześnie aktywny i spasowany — to sprzeczny stan, który
    może powstać tylko przez ręczną edycję God-Mode (silnik tur go nie tworzy).
    W takim przypadku traktujemy, że nie ma aktywnego gracza (null), zamiast
    wysyłać do frontendu sprzeczne sygnały ``active`` + ``passed``.
    """
    active_id = state.active_player_id
    if active_id is None:
        return None
    player = state.players.get(active_id)
    if player is None or player.passed:
        return None
    return active_id


def _active_color(state: GameState) -> str | None:
    """Kolor aktywnego gracza (frontend dopasowuje ``activePlayer`` po KOLORZE).

    Zwraca kolor TYLKO gdy jest jednoznaczny — gdy dwóch graczy dzieli ten sam
    kolor (niepoprawny stan God-Mode), dopasowanie po kolorze trafiłoby w obu, więc
    nie wskazujemy aktywnego (null) zamiast podświetlać przypadkowego gracza (Bug 7).
    """
    active_id = _effective_active_id(state)
    if active_id is None:
        return None
    player = state.players.get(active_id)
    if player is None or player.color is None:
        return None
    same_color = sum(
        1 for other in state.players.values() if other.color == player.color
    )
    if same_color != 1:
        return None
    return player.color


def _build_game_state(state: GameState) -> dict[str, Any]:
    """Buduje obiekt ``gameState`` — zasila panel faz + kolejność tur we froncie.

    Faza, aktywny gracz (kolor) oraz akcja taktyczna (E3): ``activeSystem`` =
    aktualnie aktywowany system, ``tacticalStep`` = bieżący krok (nasze rozszerzenie
    kontraktu — frontend AsyncTI4 je ignoruje, nasz panel taktyczny odczyta). Walka/
    agenda pozostają null do czasu ich logiki. Kolejność tur frontend wylicza z
    ``playerData`` (``active``/``passed``/``scs``).
    """
    return {
        "phase": _to_web_phase(state.phase),
        "activePlayer": _active_color(state),
        "turnStartedAt": None,
        "winner": None,
        "agenda": None,
        "activeSystem": state.active_system,
        "tacticalStep": (
            state.tactical_step.value if state.tactical_step is not None else None
        ),
        "activeCombat": None,
    }


def _entity_key_map(state: GameState) -> dict[str, str]:
    """Buduje mapę ``player_id -> klucz tożsamości`` używany w całym web-data.

    Frontend grupuje jednostki w ``tileUnitData``/``statTilePositions`` po stringu,
    który traktuje jak ``faction`` i dopasowuje do ``playerData[].faction`` w
    ``lookupUnit``. Dlatego klucz MUSI być ten sam we wszystkich miejscach i MUSI
    jednoznacznie wskazywać gracza — inaczej jednostki dwóch graczy dzielących tę
    samą frakcję (lub brak frakcji) scalają się w jeden wpis i znikają z mapy
    (Bug 1: ``faction OR None`` kolidowało w ``_entities_from_counts`` /
    ``_build_stat_tile_positions`` / ``_planet_controller``).

    Reguła: użyj ``faction``, gdy jest UNIKALNA w całej grze; w przeciwnym razie
    (kolizja frakcji albo brak frakcji) użyj stabilnego ``player_id``. Dzięki temu
    każdy gracz ma własny, niekolidujący klucz, a frontend i tak go znajdzie
    (ten sam klucz trafia do ``playerData[].faction``).
    """
    faction_counts: dict[str, int] = {}
    for player in state.players.values():
        if player.faction is not None:
            faction_counts[player.faction] = faction_counts.get(player.faction, 0) + 1
    result: dict[str, str] = {}
    for player_id, player in state.players.items():
        if player.faction is not None and faction_counts[player.faction] == 1:
            result[player_id] = player.faction
        else:
            result[player_id] = player_id
    return result


def _entities_from_counts(
    counts_by_player: dict[str, dict[str, int]],
    entity_keys: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    """Buduje ``FactionUnits`` (``{klucz: [EntityData]}``) z liczników stanu.

    ``EntityData`` dla jednostki: ``entityId`` = ``asyncId``, ``entityType`` =
    ``"unit"``, ``count`` = liczba. Pomija typy spoza katalogu i liczby <= 0.

    Klucz grupujący to stabilny klucz tożsamości gracza (``entity_keys``, patrz
    ``_entity_key_map``), nie surowa frakcja — dzięki temu gracze dzielący frakcję
    nie scalają się w jeden wpis. Nieznany ``player_id`` (brak w ``entity_keys``)
    używa własnego id jako klucza zastępczego (dawny Bug 4 — phantom bucket:
    jednostki są teraz widoczne pod własnym kluczem zamiast znikać).
    """
    result: dict[str, list[dict[str, Any]]] = {}
    for player_id, by_type in counts_by_player.items():
        key = entity_keys.get(player_id, player_id)
        entities: list[dict[str, Any]] = []
        for base_type, count in by_type.items():
            if count <= 0:
                continue
            async_id = ASYNC_ID_BY_BASE_TYPE.get(base_type)
            if async_id is None:
                continue
            entities.append(
                {"entityId": async_id, "entityType": "unit", "count": count}
            )
        if entities:
            result[key] = entities
    return result


def _ring_count(grid: HexGrid) -> int:
    """Liczba pierścieni planszy wyliczona z pozycji (min 3, zgodnie z frontendem).

    Pozycja AsyncTI4 ``RPP`` — pierwsza cyfra to numer pierścienia. Frontend
    normalizuje ringCount do zakresu 3..8; zwracamy maksymalny użyty pierścień.
    """
    max_ring = 0
    for position in grid.positions:
        if position.isdigit() and len(position) == 3:
            max_ring = max(max_ring, int(position[0]))
    return max(max_ring, 3)


def _build_tile_unit_data(
    grid: HexGrid,
    registry: StaticDataRegistry,
    state: GameState,
    entity_keys: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Buduje ``tileUnitData`` oraz ``tilePositions`` dla rzeczywistych systemów.

    Sloty domowe bez przypisanego kafelka (``__home__``) są pomijane — nie mają
    ``systemId`` rozpoznawanego przez statyczne dane frontendu.
    """
    tile_unit_data: dict[str, dict[str, Any]] = {}
    tile_positions: list[str] = []

    for position in sorted(grid.positions):
        system_id = grid.system_id_at(position)
        if system_id == HOME_SLOT_SYSTEM_ID:
            continue  # pusty slot domowy — brak kafelka systemu

        tile_positions.append(f"{position}:{system_id}")

        system = registry.systems.get(system_id)
        sys_state = state.systems.get(position)

        space: dict[str, list[dict[str, Any]]] = {}
        planets: dict[str, dict[str, Any]] = {}

        ccs: list[str] = []
        if sys_state is not None:
            space = _entities_from_counts(sys_state.space_units, entity_keys)
            for planet_id, by_player in sys_state.planet_units.items():
                planets[planet_id] = _build_planet_entry(
                    registry,
                    planet_id,
                    by_player,
                    sys_state.planet_owners.get(planet_id),
                    entity_keys,
                )
            # Żetony dowodzenia w przestrzeni (aktywacja) — klucz tożsamości gracza,
            # spójny z grupowaniem jednostek (frontend porównuje ccs z faction).
            ccs = [
                entity_keys.get(pid, pid) for pid in sys_state.command_tokens
            ]

        # Planety systemu bez jednostek też muszą istnieć w słowniku (frontend
        # kluczuje render po nazwie planety ze statycznych danych — pusty wpis OK).
        if system is not None:
            for planet_id in system.planets:
                planets.setdefault(
                    planet_id,
                    _empty_planet_entry(
                        registry, planet_id, state, position, entity_keys
                    ),
                )

        tile_unit_data[position] = {
            "space": space,
            "planets": planets,
            "ccs": ccs,
            "anomaly": bool(grid.anomalies_at(position)),
            "production": {},
            "pds": None,
        }

    return tile_unit_data, tile_positions


def _planet_controller(
    owner_id: str | None, entity_keys: dict[str, str]
) -> str | None:
    """Klucz tożsamości gracza kontrolującego planetę (lub None).

    Używa tej samej mapy co jednostki (``entity_keys``), żeby ``controlledBy``
    zgadzało się z kluczem w ``playerData[].faction`` i grupowaniem jednostek.
    """
    if owner_id is None:
        return None
    return entity_keys.get(owner_id, owner_id)


def _build_planet_entry(
    registry: StaticDataRegistry,
    planet_id: str,
    units_by_player: dict[str, dict[str, int]],
    owner_id: str | None,
    entity_keys: dict[str, str],
) -> dict[str, Any]:
    """Buduje ``PlanetEntityData`` dla planety z jednostkami naziemnymi.

    Zasoby/wpływy pochodzą z rejestru (statyczne dane planety) — także dla planet
    kontrolowanych/zajętych, nie tylko pustych (bez tego panele graczy i tooltipy
    pokazywałyby zera).
    """
    entry = _planet_base(planet_id, owner_id, entity_keys)
    entry["entities"] = _entities_from_counts(units_by_player, entity_keys)
    _fill_planet_stats(entry, registry, planet_id)
    return entry


def _empty_planet_entry(
    registry: StaticDataRegistry,
    planet_id: str,
    state: GameState,
    position: str,
    entity_keys: dict[str, str],
) -> dict[str, Any]:
    """Buduje pusty ``PlanetEntityData`` (planeta bez jednostek w stanie)."""
    owner_id = None
    sys_state = state.systems.get(position)
    if sys_state is not None:
        owner_id = sys_state.planet_owners.get(planet_id)
    entry = _planet_base(planet_id, owner_id, entity_keys)
    entry["entities"] = {}
    _fill_planet_stats(entry, registry, planet_id)
    return entry


def _planet_base(
    planet_id: str, owner_id: str | None, entity_keys: dict[str, str]
) -> dict[str, Any]:
    """Wspólne pola ``PlanetEntityData`` (kontrola, zasoby domyślne)."""
    return {
        "controlledBy": _planet_controller(owner_id, entity_keys),
        "entities": {},
        "commodities": 0,
        "planetaryShield": False,
        "resources": 0,
        "influence": 0,
    }


def _fill_planet_stats(
    entry: dict[str, Any], registry: StaticDataRegistry, planet_id: str
) -> None:
    """Uzupełnia zasoby/wpływy planety z rejestru (gdy dostępne)."""
    planet = registry.planets.get(planet_id)
    if planet is not None:
        entry["resources"] = planet.resources
        entry["influence"] = planet.influence


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
    # Wybór: frakcyjny-ulepszony > frakcyjny-bazowy > generyczny-ulepszony >
    # generyczny-bazowy. Ulepszenie liczy się tylko, gdy gracz ma wymaganą technologię.
    faction_upgraded: dict[str, str] = {}
    faction_base: dict[str, str] = {}
    generic_upgraded: dict[str, str] = {}
    generic_base: dict[str, str] = {}
    for unit in registry.units.values():
        if unit.async_id is None or unit.async_id not in standard_async:
            continue  # pomija cavalry/placeholdery/nietypowe asyncId
        if unit.id == "nowarsun":
            continue
        is_upgrade = unit.upgrades_from_unit_id is not None
        if not has_tech(unit):
            continue  # jednostka/ulepszenie za technologią, której gracz nie ma
        is_faction = unit.faction is not None
        belongs = is_faction_unit(unit)
        if is_faction and not belongs:
            continue  # cudzy wariant frakcyjny — pomijamy
        if belongs and is_upgrade:
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
            or faction_base.get(async_id)
            or generic_upgraded.get(async_id)
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
    controlled_planets: list[str], registry: StaticDataRegistry
) -> _Economy:
    """Liczy ekonomię kontrolowanych planet: sumy + optimal/flex.

    Reguła per planeta (źródło: AsyncTI4 ``Planet.getOptimal*``, RULES.md 7):
    - optimalResources = resources, gdy resources > influence, inaczej 0;
    - optimalInfluence = influence, gdy influence > resources, inaczej 0;
    - flex = wartość, gdy resources == influence, inaczej 0.
    """
    econ = _Economy()
    for planet_id in controlled_planets:
        planet = registry.planets.get(planet_id)
        if planet is None:
            continue
        res, inf = planet.resources, planet.influence
        econ.resources += res
        econ.influence += inf
        if res > inf:
            econ.opt_res += res
        elif inf > res:
            econ.opt_inf += inf
        else:
            econ.flex += res
    return econ


def _leader_type(leader_id: str, registry: StaticDataRegistry) -> str:
    """Typ lidera (``agent``/``commander``/``hero``) z POLA ``type`` danych.

    Czytamy typ z rejestru liderów, nie z końcówki id — id jak ``keleresherokuuasi``
    nie kończy się nazwą typu, więc zgadywanie po sufiksie je błędnie klasyfikowało
    (Keleres hero → „agent"). Awaryjnie (lider spoza rejestru) próbujemy sufiksu.
    """
    leader = registry.leaders.get(leader_id)
    if leader is not None:
        return leader.type
    lid = leader_id.lower()
    for ltype in ("commander", "hero", "agent"):
        if lid.endswith(ltype):
            return ltype
    return "agent"


def _player_leaders(
    faction_id: str | None,
    registry: StaticDataRegistry,
    states: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Buduje listę liderów gracza z danych frakcji (agent/commander/hero).

    Stan domyślny: agent gotowy, commander/hero zablokowani. ``states`` nadpisuje
    stan per lider (``"locked"``/``"unlocked"``/``"exhausted"``) — edycja God-Mode.
    Typ lidera czytamy z danych lidera (``LeaderDef.type``), nie z końcówki id.
    """
    faction = registry.factions.get(faction_id) if faction_id else None
    if faction is None:
        return []
    states = states or {}
    leaders: list[dict[str, Any]] = []
    for leader_id in faction.leaders:
        ltype = _leader_type(leader_id, registry)
        # Stan: override z leader_states albo domyślny (agent gotowy, reszta locked).
        default_state = "unlocked" if ltype == "agent" else "locked"
        state = states.get(leader_id, default_state)
        leaders.append(
            {
                "id": leader_id,
                "type": ltype,
                "tgCount": 0,
                "exhausted": state == "exhausted",
                "locked": state == "locked",
                "active": False,
            }
        )
    return leaders


def _faction_abilities(
    faction_id: str | None, registry: StaticDataRegistry
) -> list[str]:
    """Lista ID zdolności frakcji gracza (pole ``abilities`` danych frakcji).

    Frontend renderuje je jako inskrypcje na karcie gracza (komponent ``Ability``),
    rozwiązując ID po swoich statycznych danych. Zdolności są STANOWE pasywnie:
    nie mają stanu locked/exhausted w stylu liderów — ich okno/efekt wynika z danych
    (``permanentEffect``/``window``), więc wysyłamy tylko identyfikatory. Sortujemy
    dla stabilności dokumentu.
    """
    faction = registry.factions.get(faction_id) if faction_id else None
    if faction is None:
        return []
    return sorted(faction.abilities)


def _faction_techs(
    faction_id: str | None,
    technologies: list[str],
    registry: StaticDataRegistry,
) -> tuple[list[str], list[str]]:
    """Technologie frakcyjne gracza: (wszystkie, niezbadane).

    Źródło listy: pole ``factionTech`` danych frakcji (``FactionDef.faction_tech``).
    "Niezbadane" = technologie frakcyjne, których gracza nie ma na liście
    ``technologies`` (zbadane trafiają do zwykłego racka techów przez ``techs``).
    Frontend wyszarza niezbadane (prop ``unresearched`` komponentu ``Tech``).
    Sortujemy obie listy dla stabilności dokumentu.
    """
    faction = registry.factions.get(faction_id) if faction_id else None
    if faction is None:
        return [], []
    all_techs = sorted(faction.faction_tech)
    researched = {t.lower() for t in technologies}
    not_researched = sorted(t for t in all_techs if t.lower() not in researched)
    return all_techs, not_researched


def _player_breakthrough(
    faction_id: str | None,
    player: Any,
    registry: StaticDataRegistry,
) -> dict[str, Any] | None:
    """Buduje obiekt ``breakthrough`` dla gracza (lub None, gdy frakcja go nie ma).

    Przełom jest przypisany do frakcji przez pole ``faction`` w danych
    (``BreakthroughDef``). Mechanika Thunder's Edge: frakcje spoza tego dodatku nie
    mają przełomu → None (frontend chowa slot, gdy nikt nie ma przełomu). Stan
    (``unlocked``/``exhausted``/``tradeGoodsStored``) pochodzi z ``PlayerState``.

    Kształt pól zgodny z typem frontendu ``BreakthroughData``:
    ``breakthroughId``, ``unlocked``, ``exhausted``, ``tradeGoodsStored``.
    """
    if faction_id is None:
        return None
    breakthrough_id = next(
        (bt.id for bt in registry.breakthroughs.values() if bt.faction == faction_id),
        None,
    )
    if breakthrough_id is None:
        return None
    return {
        "breakthroughId": breakthrough_id,
        "unlocked": player.breakthrough_unlocked,
        "exhausted": player.breakthrough_exhausted,
        "tradeGoodsStored": player.breakthrough_tg,
    }


def _player_home_position(player_id: str, state: GameState) -> str | None:
    """Pozycja slotu domowego gracza (kotwica heksa stat-area).

    Priorytet (Bug 9): jawny ``PlayerState.home_position`` z setupu — stabilny
    niezależnie od podbojów. Dopiero gdy go brak (np. gracz utworzony ręcznie
    w God-Mode bez setupu), awaryjnie szukamy pierwszego systemu, w którym gracz
    kontroluje planetę (dawne, niestabilne zachowanie).
    """
    player = state.players.get(player_id)
    if player is not None and player.home_position is not None:
        return player.home_position
    for position, system in state.systems.items():
        if any(owner == player_id for owner in system.planet_owners.values()):
            return position
    return None


def _tile_ring(position: str) -> int:
    """Numer pierścienia pozycji (pierwsza cyfra ``RPP``; ``000`` = 0)."""
    if position.isdigit() and len(position) == 3:
        return int(position[0])
    return 99  # pozycje nienumeryczne (hyperlane/frac) — poza pierścieniami


def _three_nearby_stat_tiles(
    home_position: str,
    grid: HexGrid,
    taken: set[str],
    ring_count: int,
) -> list[str]:
    """Port algorytmu ``PlayerStatsHelper.findThreeNearbyStatTiles`` z AsyncTI4.

    Źródło (nie z pamięci): ``TI4_map_generator_bot`` →
    ``PlayerStatsHelper.findThreeNearbyStatTiles``. Algorytm:
    1. Kandydaci = PUSTE pozycje (brak systemu na mapie), pierścień ≤ ``ring_count+1``,
       nie zajęte przez innego gracza (``taken``).
    2. Kolejka priorytetowa wg odległości do slotu domowego + kara za pierścień.
    3. Dobieramy najbliższe aż powstanie zwarta trójka (jeden kafelek sąsiaduje
       z dwoma pozostałymi) i zwracamy ``[pivot, sąsiad, sąsiad]`` — pivot (środkowy)
       jest PIERWSZY, bo frontend kładzie na nim heks tożsamości frakcji (VP).

    Odległość liczymy w metryce kubicznej (proxy pikseli z oryginału) + ``ring*0.5``
    jako kara pierścienia — wystarczające, by odwzorować wybór i kolejność AsyncTI4.
    """
    coords = load_positions()
    home = coords.get(home_position)
    if home is None:
        return []
    occupied = grid.positions

    def cube_dist(pos_id: str) -> int:
        h = coords[pos_id]
        return (abs(h.q - home.q) + abs(h.r - home.r) + abs(h.s - home.s)) // 2

    candidates = [
        pos
        for pos in coords
        if pos not in occupied
        and pos not in taken
        and _tile_ring(pos) <= ring_count + 1
    ]
    # Sortuj wg odległości + lekka kara za dalszy pierścień (jak w oryginale).
    candidates.sort(key=lambda p: cube_dist(p) * 2 + _tile_ring(p))

    def adjacent(a: str, b: str) -> bool:
        ha, hb = coords[a], coords[b]
        return (abs(ha.q - hb.q) + abs(ha.r - hb.r) + abs(ha.s - hb.s)) // 2 == 1

    chosen: list[str] = []
    for nxt in candidates:
        chosen.append(nxt)
        # Czy któryś z wybranych sąsiaduje z dokładnie dwoma innymi (pivot)?
        for pivot in chosen:
            neighbors = [p for p in chosen if p != pivot and adjacent(pivot, p)]
            if len(neighbors) >= 2:
                return [pivot, neighbors[0], neighbors[1]]
    return []


def _build_stat_tile_positions(
    state: GameState, grid: HexGrid, entity_keys: dict[str, str]
) -> dict[str, list[str]]:
    """Buduje ``statTilePositions`` = ``{klucz: [pivot, sąsiad, sąsiad]}``.

    Dla każdego gracza bierze jego slot domowy i trzy pobliskie puste pozycje
    (algorytm AsyncTI4, ``_three_nearby_stat_tiles``) — pivot pierwszy. Zajęte
    pozycje są współdzielone między graczami (``taken``), by heksy się nie nakładały.
    Klucz wpisu to stabilny klucz tożsamości (``entity_keys``), spójny z grupowaniem
    jednostek i ``playerData[].faction`` (Bug 1: dawniej kolizja frakcji scalała heksy).
    """
    result: dict[str, list[str]] = {}
    taken: set[str] = set()
    ring_count = _ring_count(grid)
    # Deterministyczna kolejność graczy (po id) — stabilny podział pozycji.
    for player_id in sorted(state.players):
        home = _player_home_position(player_id, state)
        if home is None:
            continue
        positions = _three_nearby_stat_tiles(home, grid, taken, ring_count)
        if positions:
            taken.update(positions)
            result[entity_keys.get(player_id, player_id)] = positions
    return result


def _build_player_data(
    state: GameState, registry: StaticDataRegistry, entity_keys: dict[str, str]
) -> list[dict[str, Any]]:
    """Buduje listę ``PlayerData`` (minimalny, kompletny dla viewera zestaw pól)."""
    players: list[dict[str, Any]] = []
    deployed_by_player = _deployed_counts_by_player(state)
    active_id = _effective_active_id(state)  # spójny z activePlayer (Bug 7)
    for player_id, player in sorted(state.players.items()):
        faction = entity_keys.get(player_id, player_id)
        # Opcja A: planety gracza WYLICZANE z planet_owners systemów (jedno źródło
        # prawdy), nie z player.controlled_planets — eliminuje desync panel↔mapa (Bug 3).
        controlled = _controlled_planets_from_systems(player_id, state)
        econ = _planet_economy(controlled, registry)
        leaders = _player_leaders(player.faction, registry, player.leader_states)
        units_owned = _units_owned_for_faction(
            player.faction, player.technologies, registry
        )
        unit_counts = _unit_counts(deployed_by_player.get(player_id, {}))
        abilities = _faction_abilities(player.faction, registry)
        faction_techs, not_researched_ft = _faction_techs(
            player.faction, player.technologies, registry
        )
        breakthrough = _player_breakthrough(player.faction, player, registry)
        players.append(
            {
                "discordId": player_id,
                "userName": player_id,
                "faction": faction,
                "color": player.color or "gray",
                "displayName": faction,
                "flexibleDisplayName": faction,
                "isSpeaker": False,
                "isTyrant": False,
                "passed": player.passed,
                "eliminated": False,
                "active": active_id == player_id,
                # Zasoby / liczniki (viewer czyta je w panelach gracza).
                "tg": player.trade_goods,
                "commodities": player.commodities,
                "commoditiesTotal": player.commodities,
                # Żetony dowodzenia (CC) — panele gracza + heks stat-area.
                "tacticalCC": player.tactical_cc,
                "fleetCC": player.fleet_cc,
                "strategicCC": player.strategic_cc,
                "ccReinf": player.cc_reinf,
                "totalVps": player.victory_points,
                # unitsOwned: realne ID posiadanych jednostek (baza generyczna +
                # frakcyjna, bez ulepszeń). NIGDY []! Pusta lista psuje lookupUnit
                # ([].includes zawsze False). Lista steruje też stanem "Upgraded":
                # skoro gracz ma tylko bazowe, panel nie pokazuje ich jako ulepszone.
                "unitsOwned": units_owned,
                "techs": list(player.technologies),
                "exhaustedTechs": [],
                # Zdolności frakcji + technologie frakcyjne (sekcja abilities karty
                # gracza). notResearchedFactionTechs frontend wyszarza; zbadane
                # frakcyjne są w ``techs`` (trafiają do racka techów).
                "abilities": abilities,
                "factionTechs": faction_techs,
                "notResearchedFactionTechs": not_researched_ft,
                "planets": controlled,
                "exhaustedPlanets": [],
                "exhaustedPlanetAbilities": [],
                "relics": [],
                "exhaustedRelics": [],
                "fragments": [],
                "leaders": leaders,
                "leaderIDs": [str(leader["id"]) for leader in leaders],
                # Przełom frakcji (Thunder's Edge). Pole opcjonalne we froncie —
                # emitujemy tylko gdy frakcja go ma (inaczej None i slot się chowa).
                "breakthrough": breakthrough,
                "secretsScored": {},
                "knownUnscoredSecrets": {},
                "numUnscoredSecrets": 0,
                "numScoreableSecrets": 0,
                "promissoryNotesInPlayArea": [],
                "followedSCs": [],
                "unfollowedSCs": [],
                # Karty strategii gracza (numery inicjatywy) — kolejność tur w panelu faz.
                "scs": list(player.strategy_cards),
                "exhaustedSCs": list(player.exhausted_strategy_cards),
                "neighbors": [],
                "soCount": 0,
                "pnCount": 0,
                "acCount": 0,
                "unitCounts": unit_counts,
                # Ekonomia planet z rejestru (reguła AsyncTI4, RULES.md 7).
                # resources/influence = dostępne (zakładamy wszystkie gotowe);
                # tot* = sumy łączne; optimal/flex per reguła getOptimal*.
                "resources": econ.resources,
                "influence": econ.influence,
                "totResources": econ.resources,
                "totInfluence": econ.influence,
                "optimalResources": econ.opt_res,
                "optimalInfluence": econ.opt_inf,
                "flexValue": econ.flex,
                "totOptimalResources": econ.opt_res,
                "totOptimalInfluence": econ.opt_inf,
                "totFlexValue": econ.flex,
                "crf": 0,
                "hrf": 0,
                "irf": 0,
                "urf": 0,
                "stasisInfantry": 0,
                "actualHits": 0,
                "expectedHitsTimes10": 0,
                "spaceArmyRes": 0,
                "groundArmyRes": 0,
                "spaceArmyHealth": 0,
                "groundArmyHealth": 0,
                "spaceArmyCombat": 0,
                "groundArmyCombat": 0,
            }
        )
    return players


def _build_strategy_cards(
    state: GameState, registry: StaticDataRegistry, entity_keys: dict[str, str]
) -> list[dict[str, Any]]:
    """Buduje ``strategyCards`` dla web-data z aktywnego zestawu + stanu gry.

    Pola zgodne z typem frontendu (``StrategyCard``): ``initiative``, ``name``, ``id``,
    ``picked``, ``played``, ``exhausted``, ``tradeGoods``, ``pickedByFaction``.
    ``pickedByFaction`` używa klucza tożsamości (spójnie z ``playerData[].faction``).
    """
    owner_by_init: dict[int, str] = {}
    exhausted_by_init: dict[int, bool] = {}
    for player_id, player in state.players.items():
        for init in player.strategy_cards:
            owner_by_init[init] = player_id
            exhausted_by_init[init] = init in player.exhausted_strategy_cards
    cards: list[dict[str, Any]] = []
    for card in registry.strategy_card_set():
        owner_id = owner_by_init.get(card.initiative)
        exhausted = exhausted_by_init.get(card.initiative, False)
        cards.append(
            {
                "initiative": card.initiative,
                "name": card.name,
                "id": card.id,
                "picked": owner_id is not None,
                "played": exhausted,
                "exhausted": exhausted,
                "tradeGoods": state.strategy_card_tg.get(card.initiative, 0),
                "pickedByFaction": (
                    entity_keys.get(owner_id, owner_id) if owner_id else None
                ),
            }
        )
    return cards


def _empty_objectives() -> dict[str, Any]:
    """Pusta struktura ``Objectives`` (viewer wymaga obecności pól)."""
    return {
        "stage1Objectives": [],
        "stage2Objectives": [],
        "customObjectives": [],
        "allObjectives": [],
    }


def _empty_card_pool() -> dict[str, Any]:
    """Pusta struktura ``CardPoolData`` (viewer wymaga obecności pól)."""
    return {
        "secretObjectiveDeckSize": 0,
        "secretObjectiveFullDeckSize": 0,
        "secretObjectiveDeck": [],
        "secretObjectiveDiscard": [],
        "actionCardDeckSize": 0,
        "actionCardFullDeckSize": 0,
        "actionCardDiscardSize": 0,
        "actionCardPurgedSize": 0,
        "culturalExploreDeck": [],
        "culturalExploreDiscard": [],
        "industrialExploreDeck": [],
        "industrialExploreDiscard": [],
        "hazardousExploreDeck": [],
        "hazardousExploreDiscard": [],
        "frontierExploreDeck": [],
        "frontierExploreDiscard": [],
        "relicDeckSize": 0,
        "relicFullDeckSize": 0,
        "relicDeck": [],
        "relicDiscard": [],
        "agendaDeckSize": 0,
        "agendaFullDeckSize": 0,
        "agendaDiscardSize": 0,
        "technologyDeck": [],
    }


def _empty_expeditions() -> dict[str, Any]:
    """Pusta struktura ``Expeditions`` (pola wymagane przez typ frontendu)."""
    none = {"completedBy": None}
    return {
        "techSkip": dict(none),
        "tradeGoods": dict(none),
        "fiveRes": dict(none),
        "fiveInf": dict(none),
        "secret": dict(none),
        "actionCards": dict(none),
    }


def build_web_data(
    grid: HexGrid,
    registry: StaticDataRegistry,
    state: GameState,
    *,
    game_name: str,
    vps_to_win: int = 10,
) -> dict[str, Any]:
    """Serializuje stan gry do dokumentu ``PlayerDataResponse`` dla frontendu ti4_web.

    Args:
        grid: Bieżąca mapa (źródło pozycji, systemów, anomalii).
        registry: Statyczne dane (planety — zasoby/wpływy).
        state: Bieżący stan gry (gracze, jednostki).
        game_name: Identyfikator gry wyświetlany/używany przez frontend.
        vps_to_win: Próg punktów zwycięstwa.

    Returns:
        Słownik gotowy do serializacji JSON zgodny z ``PlayerDataResponse``.
    """
    # Jedna mapa klucz-tożsamości dla CAŁEGO dokumentu (jednostki, planety, heksy,
    # playerData). Spójny klucz eliminuje desync panel↔mapa (Bug 1/2).
    entity_keys = _entity_key_map(state)
    tile_unit_data, tile_positions = _build_tile_unit_data(
        grid, registry, state, entity_keys
    )
    return {
        "gameName": game_name,
        "gameRound": state.round_number,
        "ringCount": _ring_count(grid),
        "vpsToWin": vps_to_win,
        # Wersja schematu danych oczekiwana przez frontend (ti4_web). Poniżej tej
        # wartości frontend blokuje render ekranem "Update Needed". Trzymamy stałą
        # zgodną z REQUIRED_VERSION_SCHEMA w GameMapPage.tsx.
        "versionSchema": WEB_DATA_SCHEMA_VERSION,
        "tilePositions": tile_positions,
        "tileUnitData": tile_unit_data,
        "playerData": _build_player_data(state, registry, entity_keys),
        "statTilePositions": _build_stat_tile_positions(state, grid, entity_keys),
        "gameState": _build_game_state(state),
        "lawsInPlay": [],
        "strategyCards": _build_strategy_cards(state, registry, entity_keys),
        "objectives": _empty_objectives(),
        "cardPool": _empty_card_pool(),
        "expeditions": _empty_expeditions(),
    }


def entity_key_map(state: GameState) -> dict[str, str]:
    """Publiczny alias ``_entity_key_map`` — mapa ``player_id -> klucz tożsamości``.

    Używany poza modułem (np. router walki), by klucze stron walki były spójne z
    grupowaniem jednostek i ``playerData[].faction`` w web-data.
    """
    return _entity_key_map(state)


# Pomocniczo wyeksportowane dla testów/diagnostyki.
__all__ = ["build_web_data", "entity_key_map", "is_space_unit"]
