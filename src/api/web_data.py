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
    faction_id: str | None, registry: StaticDataRegistry
) -> list[str]:
    """Lista ID jednostek posiadanych przez frakcję (baza generyczna + frakcyjna).

    Pomija warianty ulepszone (``upgrades_from_unit_id``) i placeholdery (``nowarsun``,
    ``cavalry*``). Dzięki temu ``lookupUnit`` frontendu rozwiązuje jednostki BAZOWE
    (nie pokazuje błędnie wszystkiego jako „Upgraded"). Jednostki frakcyjne mają ID
    z prefiksem ``<faction>_`` w danych AsyncTI4.
    """
    owned: list[str] = []
    standard_async = set(ASYNC_ID_BY_BASE_TYPE.values())
    for unit in registry.units.values():
        if unit.upgrades_from_unit_id is not None:
            continue
        if unit.async_id not in standard_async:
            continue  # pomija cavalry/placeholdery
        if unit.id == "nowarsun":
            continue
        is_generic = "_" not in unit.id
        is_faction = faction_id is not None and unit.id.startswith(f"{faction_id}_")
        if is_generic or is_faction:
            owned.append(unit.id)
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


def _planet_economy(
    controlled_planets: list[str], registry: StaticDataRegistry
) -> tuple[int, int]:
    """Sumuje (zasoby, wpływy) kontrolowanych planet z danych rejestru."""
    resources = 0
    influence = 0
    for planet_id in controlled_planets:
        planet = registry.planets.get(planet_id)
        if planet is not None:
            resources += planet.resources
            influence += planet.influence
    return resources, influence


def _player_home_position(player_id: str, state: GameState) -> str | None:
    """Pozycja systemu domowego gracza (gdzie kontroluje planety)."""
    for position, system in state.systems.items():
        if any(owner == player_id for owner in system.planet_owners.values()):
            return position
    return None


def _nearest_ring4(home_position: str) -> list[str]:
    """Trzy najbliższe pozycje pierścienia 4 do slotu domowego (stat-area heksy).

    Zweryfikowane geometrycznie: pokrywa się 1:1 z układem ``statTilePositions``
    AsyncTI4 (np. ``301 → 401,402,424``). Puste, gdy brak pozycji w aliasie.
    """
    coords = load_positions()
    home = coords.get(home_position)
    if home is None:
        return []
    ring4 = [p for p in coords if p.startswith("4") and len(p) == 3 and p.isdigit()]

    def dist(pos_id: str) -> int:
        h = coords[pos_id]
        return (abs(h.q - home.q) + abs(h.r - home.r) + abs(h.s - home.s)) // 2

    return sorted(sorted(ring4, key=dist)[:3], key=int)


def _build_stat_tile_positions(state: GameState) -> dict[str, list[str]]:
    """Buduje ``statTilePositions`` = ``{faction: [3 pozycje pierścienia 4]}``.

    Dla każdego gracza bierze jego slot domowy i trzy najbliższe pozycje pierścienia 4
    (geometrycznie, zgodnie z układem AsyncTI4). To zasila kolorowe heksy „player
    stats" przy planszy (``PlayerStatsHex``).
    """
    result: dict[str, list[str]] = {}
    for player_id, player in state.players.items():
        home = _player_home_position(player_id, state)
        if home is None:
            continue
        positions = _nearest_ring4(home)
        if positions:
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
        total_res, total_inf = _planet_economy(
            player.controlled_planets, registry
        )
        units_owned = _units_owned_for_faction(player.faction, registry)
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
                "passed": False,
                "eliminated": False,
                "active": state.active_player_id == player_id,
                # Zasoby / liczniki (viewer czyta je w panelach gracza).
                "tg": player.trade_goods,
                "commodities": player.commodities,
                "commoditiesTotal": player.commodities,
                "tacticalCC": 0,
                "fleetCC": 0,
                "strategicCC": 0,
                "ccReinf": 0,
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
                "leaders": [],
                "leaderIDs": [],
                "secretsScored": {},
                "knownUnscoredSecrets": {},
                "numUnscoredSecrets": 0,
                "numScoreableSecrets": 0,
                "promissoryNotesInPlayArea": [],
                "followedSCs": [],
                "unfollowedSCs": [],
                "scs": [],
                "exhaustedSCs": [],
                "neighbors": [],
                "soCount": 0,
                "pnCount": 0,
                "acCount": 0,
                "unitCounts": unit_counts,
                # Ekonomia planet: suma zasobów/wpływów kontrolowanych planet
                # (z rejestru). Optymalne/flex liczymy dopiero w fazie strategicznej.
                "resources": total_res,
                "influence": total_inf,
                "totResources": total_res,
                "totInfluence": total_inf,
                "optimalResources": 0,
                "optimalInfluence": 0,
                "flexValue": 0,
                "totOptimalResources": 0,
                "totOptimalInfluence": 0,
                "totFlexValue": 0,
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
        "statTilePositions": _build_stat_tile_positions(state),
        "lawsInPlay": [],
        "strategyCards": [],
        "objectives": _empty_objectives(),
        "cardPool": _empty_card_pool(),
        "expeditions": _empty_expeditions(),
    }


# Pomocniczo wyeksportowane dla testów/diagnostyki.
__all__ = ["build_web_data", "is_space_unit"]
