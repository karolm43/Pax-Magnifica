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
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE, is_space_unit

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


def _build_player_data(
    state: GameState, registry: StaticDataRegistry
) -> list[dict[str, Any]]:
    """Buduje listę ``PlayerData`` (minimalny, kompletny dla viewera zestaw pól)."""
    players: list[dict[str, Any]] = []
    for player_id, player in sorted(state.players.items()):
        faction = _faction_key(player)
        total_res, total_inf = _planet_economy(
            player.controlled_planets, registry
        )
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
                # UWAGA: NIE wysyłamy "unitsOwned" jako [] — pusta lista psuje
                # lookupUnit frontendu ([].includes(id) zawsze False → filtr
                # odrzuca wszystkie jednostki → brak jednostek w panelu/dossier).
                # Pomijamy pole: wtedy frontend rozwiązuje jednostki generycznie
                # i frakcyjnie poprawnie. (Patrz docs/RULES bloka F6.)
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
                "unitCounts": {},
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
        "statTilePositions": {},
        "lawsInPlay": [],
        "strategyCards": [],
        "objectives": _empty_objectives(),
        "cardPool": _empty_card_pool(),
        "expeditions": _empty_expeditions(),
    }


# Pomocniczo wyeksportowane dla testów/diagnostyki.
__all__ = ["build_web_data", "is_space_unit"]
