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

from src.core.game_state import GameState, PlayerState
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


def _active_color(state: GameState) -> str | None:
    """Kolor aktywnego gracza (frontend dopasowuje ``activePlayer`` po KOLORZE)."""
    if state.active_player_id is None:
        return None
    player = state.players.get(state.active_player_id)
    return player.color if player else None


def _build_game_state(state: GameState) -> dict[str, Any]:
    """Buduje obiekt ``gameState`` — zasila panel faz + kolejność tur we froncie.

    Minimalny zestaw: faza, aktywny gracz (kolor), reszta pól null (walka/agenda/
    aktywny system dojdą wraz z logiką silnika). Kolejność tur i statusy siedzeń
    frontend wylicza z ``playerData`` (``active``/``passed``/``scs``).
    """
    return {
        "phase": _to_web_phase(state.phase),
        "activePlayer": _active_color(state),
        "turnStartedAt": None,
        "winner": None,
        "agenda": None,
        "activeSystem": None,
        "activeCombat": None,
    }


def _faction_key(player: PlayerState) -> str:
    """Klucz frakcji używany w ``tileUnitData`` (frakcja lub zastępczo id gracza)."""
    return player.faction or player.player_id


def _entities_from_counts(
    counts_by_player: dict[str, dict[str, int]],
    players: dict[str, PlayerState],
) -> dict[str, list[dict[str, Any]]]:
    """Buduje ``FactionUnits`` (``{frakcja: [EntityData]}``) z liczników stanu.

    ``EntityData`` dla jednostki: ``entityId`` = ``asyncId``, ``entityType`` =
    ``"unit"``, ``count`` = liczba. Pomija typy spoza katalogu i liczby <= 0.
    """
    result: dict[str, list[dict[str, Any]]] = {}
    for player_id, by_type in counts_by_player.items():
        player = players.get(player_id)
        faction = _faction_key(player) if player else player_id
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
            result[faction] = entities
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

        if sys_state is not None:
            space = _entities_from_counts(sys_state.space_units, state.players)
            for planet_id, by_player in sys_state.planet_units.items():
                planets[planet_id] = _build_planet_entry(
                    registry,
                    planet_id,
                    by_player,
                    sys_state.planet_owners.get(planet_id),
                    state,
                )

        # Planety systemu bez jednostek też muszą istnieć w słowniku (frontend
        # kluczuje render po nazwie planety ze statycznych danych — pusty wpis OK).
        if system is not None:
            for planet_id in system.planets:
                planets.setdefault(
                    planet_id, _empty_planet_entry(registry, planet_id, state, position)
                )

        tile_unit_data[position] = {
            "space": space,
            "planets": planets,
            "ccs": [],
            "anomaly": bool(grid.anomalies_at(position)),
            "production": {},
            "pds": None,
        }

    return tile_unit_data, tile_positions


def _planet_controller(owner_id: str | None, state: GameState) -> str | None:
    """Identyfikator frakcji kontrolującej planetę (lub None)."""
    if owner_id is None:
        return None
    owner = state.players.get(owner_id)
    return _faction_key(owner) if owner else owner_id


def _build_planet_entry(
    registry: StaticDataRegistry,
    planet_id: str,
    units_by_player: dict[str, dict[str, int]],
    owner_id: str | None,
    state: GameState,
) -> dict[str, Any]:
    """Buduje ``PlanetEntityData`` dla planety z jednostkami naziemnymi.

    Zasoby/wpływy pochodzą z rejestru (statyczne dane planety) — także dla planet
    kontrolowanych/zajętych, nie tylko pustych (bez tego panele graczy i tooltipy
    pokazywałyby zera).
    """
    entry = _planet_base(planet_id, owner_id, state)
    entry["entities"] = _entities_from_counts(units_by_player, state.players)
    _fill_planet_stats(entry, registry, planet_id)
    return entry


def _empty_planet_entry(
    registry: StaticDataRegistry,
    planet_id: str,
    state: GameState,
    position: str,
) -> dict[str, Any]:
    """Buduje pusty ``PlanetEntityData`` (planeta bez jednostek w stanie)."""
    owner_id = None
    sys_state = state.systems.get(position)
    if sys_state is not None:
        owner_id = sys_state.planet_owners.get(planet_id)
    entry = _planet_base(planet_id, owner_id, state)
    entry["entities"] = {}
    _fill_planet_stats(entry, registry, planet_id)
    return entry


def _planet_base(
    planet_id: str, owner_id: str | None, state: GameState
) -> dict[str, Any]:
    """Wspólne pola ``PlanetEntityData`` (kontrola, zasoby domyślne)."""
    return {
        "controlledBy": _planet_controller(owner_id, state),
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
    """Lista ID jednostek posiadanych przez gracza (baza generyczna + frakcyjna).

    Reguły (zgodne z AsyncTI4, nie z pamięci — potwierdzone na danych żywej gry):
    - Pomija warianty ULEPSZONE (``upgrades_from_unit_id``) — gracz startuje z bazowymi.
    - Pomija jednostki wymagające technologii, której gracz NIE ma (``required_tech_id``).
      Dzięki temu War Sun (wymaga tech ``ws``) nie liczy się jako posiadany, dopóki nie
      zostanie zbadany — chyba że frakcja ma go wrodzony (np. Muaat ``muaat_warsun``,
      bez wymaganej technologii).
    - Pomija placeholdery (``nowarsun``) i niestandardowe asyncId (cavalry itd.).
    - Jednostki frakcyjne mają ID z prefiksem ``<faction>_`` w danych AsyncTI4.
    """
    standard_async = set(ASYNC_ID_BY_BASE_TYPE.values())
    techs = {t.lower() for t in technologies}
    # Dla każdego asyncId wybieramy JEDNĄ jednostkę: wariant frakcyjny ma pierwszeństwo
    # przed generycznym. Posiadanie OBU (np. "mech" + "mentak_mech") psuje lookupUnit
    # frontendu — rozwiązuje wtedy niejednoznacznie (pokazuje złą flagę frakcji).
    generic_by_async: dict[str, str] = {}
    faction_by_async: dict[str, str] = {}
    for unit in registry.units.values():
        if unit.upgrades_from_unit_id is not None:
            continue
        if unit.async_id not in standard_async:
            continue  # pomija cavalry/placeholdery
        if unit.id == "nowarsun":
            continue
        if unit.required_tech_id and unit.required_tech_id.lower() not in techs:
            continue  # jednostka za technologią, której gracz nie ma
        if "_" not in unit.id:
            generic_by_async.setdefault(unit.async_id, unit.id)
        elif faction_id is not None and unit.id.startswith(f"{faction_id}_"):
            faction_by_async.setdefault(unit.async_id, unit.id)

    owned: list[str] = []
    for async_id in standard_async:
        chosen = faction_by_async.get(async_id) or generic_by_async.get(async_id)
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


def _player_leaders(faction_id: str | None, registry: StaticDataRegistry) -> list[dict[str, Any]]:
    """Buduje listę liderów gracza z danych frakcji (agent/commander/hero).

    Na starcie liderzy są zablokowani (``locked``) — odblokowują się przez warunki.
    Typ wyprowadzamy z sufiksu identyfikatora (``...agent``/``...commander``/``...hero``).
    """
    faction = registry.factions.get(faction_id) if faction_id else None
    if faction is None:
        return []
    leaders: list[dict[str, Any]] = []
    for leader_id in faction.leaders:
        lid = leader_id.lower()
        if lid.endswith("agent"):
            ltype = "agent"
        elif lid.endswith("commander"):
            ltype = "commander"
        elif lid.endswith("hero"):
            ltype = "hero"
        else:
            ltype = "agent"
        leaders.append(
            {
                "id": leader_id,
                "type": ltype,
                "tgCount": 0,
                "exhausted": False,
                # Agent startuje odblokowany (gotowy); commander/hero zablokowani.
                "locked": ltype != "agent",
                "active": False,
            }
        )
    return leaders


def _player_home_position(player_id: str, state: GameState) -> str | None:
    """Pozycja systemu domowego gracza (gdzie kontroluje planety)."""
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
    state: GameState, grid: HexGrid
) -> dict[str, list[str]]:
    """Buduje ``statTilePositions`` = ``{faction: [pivot, sąsiad, sąsiad]}``.

    Dla każdego gracza bierze jego slot domowy i trzy pobliskie puste pozycje
    (algorytm AsyncTI4, ``_three_nearby_stat_tiles``) — pivot pierwszy. Zajęte
    pozycje są współdzielone między graczami (``taken``), by heksy się nie nakładały.
    """
    result: dict[str, list[str]] = {}
    taken: set[str] = set()
    ring_count = _ring_count(grid)
    # Deterministyczna kolejność graczy (po id) — stabilny podział pozycji.
    for player_id, player in sorted(state.players.items()):
        home = _player_home_position(player_id, state)
        if home is None:
            continue
        positions = _three_nearby_stat_tiles(home, grid, taken, ring_count)
        if positions:
            taken.update(positions)
            result[_faction_key(player)] = positions
    return result


def _build_player_data(
    state: GameState, registry: StaticDataRegistry
) -> list[dict[str, Any]]:
    """Buduje listę ``PlayerData`` (minimalny, kompletny dla viewera zestaw pól)."""
    players: list[dict[str, Any]] = []
    deployed_by_player = _deployed_counts_by_player(state)
    for player_id, player in sorted(state.players.items()):
        faction = _faction_key(player)
        econ = _planet_economy(player.controlled_planets, registry)
        leaders = _player_leaders(player.faction, registry)
        units_owned = _units_owned_for_faction(
            player.faction, player.technologies, registry
        )
        unit_counts = _unit_counts(deployed_by_player.get(player_id, {}))
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
                "active": state.active_player_id == player_id,
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
                "factionTechs": [],
                "notResearchedFactionTechs": [],
                "planets": list(player.controlled_planets),
                "exhaustedPlanets": [],
                "exhaustedPlanetAbilities": [],
                "relics": [],
                "exhaustedRelics": [],
                "fragments": [],
                "leaders": leaders,
                "leaderIDs": [str(leader["id"]) for leader in leaders],
                "secretsScored": {},
                "knownUnscoredSecrets": {},
                "numUnscoredSecrets": 0,
                "numScoreableSecrets": 0,
                "promissoryNotesInPlayArea": [],
                "followedSCs": [],
                "unfollowedSCs": [],
                # Karty strategii gracza (numery inicjatywy) — kolejność tur w panelu faz.
                "scs": list(player.strategy_cards),
                "exhaustedSCs": [],
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
    tile_unit_data, tile_positions = _build_tile_unit_data(grid, registry, state)
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
        "playerData": _build_player_data(state, registry),
        "statTilePositions": _build_stat_tile_positions(state, grid),
        "gameState": _build_game_state(state),
        "lawsInPlay": [],
        "strategyCards": [],
        "objectives": _empty_objectives(),
        "cardPool": _empty_card_pool(),
        "expeditions": _empty_expeditions(),
    }


# Pomocniczo wyeksportowane dla testów/diagnostyki.
__all__ = ["build_web_data", "is_space_unit"]
