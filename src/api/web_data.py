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

from src.core import production, strategy_phase
from src.core.game_state import GameState, PlayerState
from src.core.hex_grid import HexGrid
from src.core.map_string import HOME_SLOT_SYSTEM_ID
from src.core.neighbors import neighbors_by_player
from src.core.positions import load_positions
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import (
    ASYNC_ID_BY_BASE_TYPE,
    UNIT_CAP_BY_ASYNC_ID,
    is_space_unit,
)
from src.core.visibility import project_all_redacted, project_for_viewer

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


def _color_of(state: GameState, player_id: str | None) -> str | None:
    """Kolor gracza o danym id (lub None), gdy jednoznaczny.

    Frontend dopasowuje graczy w ``gameState`` po KOLORZE, więc kolor musi być
    jednoznaczny — przy kolizji kolorów (niepoprawny stan God-Mode) zwracamy None,
    by nie wskazać przypadkowego gracza (spójne z ``_active_color``).
    """
    if player_id is None:
        return None
    player = state.players.get(player_id)
    if player is None or player.color is None:
        return None
    same_color = sum(1 for p in state.players.values() if p.color == player.color)
    return player.color if same_color == 1 else None


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


def _pending_window(state: GameState) -> dict[str, Any] | None:
    """Buduje reprezentację otwartego okna czasowego dla frontendu (lub None).

    Tłumaczy ``GameState.pending_window`` na kształt panelu okna: typ okna,
    bieżący respondent i kolejka jako KOLORY graczy (frontend dopasowuje po
    kolorze, spójnie z ``activePlayer``), ile osób zostało oraz kontekst okna.
    Gdy kolor gracza jest niejednoznaczny (kolizja — niepoprawny stan God-Mode),
    wpada ``player_id`` jako fallback, by panel miał czym zaadresować odpowiedź.
    """
    window = state.pending_window
    if window is None:
        return None

    def ident(player_id: str) -> str:
        # Kolor, gdy jednoznaczny; inaczej player_id (żeby panel miał adres).
        color = _color_of(state, player_id)
        return color if color is not None else player_id

    responder = window.current_responder
    return {
        "windowType": window.window_type.value,
        "currentResponder": ident(responder) if responder is not None else None,
        # player_id bieżącego respondenta — panel adresuje nim odpowiedź (stabilne,
        # niezależne od kolizji kolorów).
        "currentResponderId": responder,
        "queue": [ident(pid) for pid in window.queue],
        "cursor": window.cursor,
        "remaining": max(len(window.queue) - window.cursor, 0),
        "responded": [ident(pid) for pid in window.responded],
        "context": dict(window.context),
        "isComplete": window.is_complete,
    }

def _safe_pick_count(state: GameState) -> int | None:
    """Liczba kart strategii na gracza (``Pick_Count``) lub None, gdy nieobsługiwana.

    Woła czystą regułę ``strategy_phase.pick_count`` (2 przy 3–4 graczach, 1 przy
    5–8). Web-data serializuje DOWOLNY stan — także niepełny/God-Mode z liczbą
    graczy spoza 3..8 — więc NIE może rzucać: w takim przypadku łapiemy
    ``ValueError`` i zwracamy None (pole addytywne, frontend AsyncTI4 je ignoruje,
    nasz StrategyCardTable/StrategyCardPicker odczyta). RULES.md 13.
    """
    try:
        return strategy_phase.pick_count(state)
    except ValueError:
        return None


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
        # Mówca (kolor) — otwiera wybór kart w fazie strategii (speaker order,
        # RULES.md 24). Nasze rozszerzenie kontraktu; panel tury je odczyta.
        "speaker": _color_of(state, state.speaker_id),
        # Liczba kart strategii na gracza (Pick_Count) — int lub None, gdy liczba
        # graczy spoza 3..8 (web-data nie rzuca). Pole ADDYTYWNE: panel/stół
        # strategii odczyta, frontend AsyncTI4 je ignoruje. RULES.md 13.
        "strategyPickCount": _safe_pick_count(state),
        # Kolejność miejsc przy stole jako KOLORY (speaker order wyznacza panel
        # tury rotacją od mówcy). Puste, gdy seating nieustalony.
        "seatingOrder": [
            color
            for pid in state.seating_order
            if (color := _color_of(state, pid)) is not None
        ],
        "turnStartedAt": None,
        "winner": None,
        "agenda": None,
        "activeSystem": state.active_system,
        "tacticalStep": (
            state.tactical_step.value if state.tactical_step is not None else None
        ),
        "activeCombat": None,
        # Okno czasowe (timing window) — None, gdy żadne nie trwa. Nasze rozszerzenie
        # kontraktu (frontend AsyncTI4 je ignoruje, nasz panel okna odczyta). RULES.md 29.2.
        "pendingWindow": _pending_window(state),
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


def _tile_production(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    position: str,
) -> dict[str, int]:
    """Wartości PRODUCTION w systemie per KOLOR gracza (wskaźnik na kafelku mapy).

    Frontend (``tileUnitData[pos].production``) renderuje koło zębate z najwyższą
    wartością (``Math.max(Object.values(production))`` — RULES.md 33.2). Kluczujemy
    po KOLORZE gracza (jak reszta sygnałów mapy). Pomijamy wartości ≤ 0 i graczy bez
    jednoznacznego koloru. Źródło wartości: ``production.system_production_value``.
    """
    sys_state = state.systems.get(position)
    if sys_state is None:
        return {}
    # Gracze obecni w systemie (statki lub jednostki na planetach).
    present: set[str] = set(sys_state.space_units)
    for by_player in sys_state.planet_units.values():
        present.update(by_player)

    result: dict[str, int] = {}
    for player_id in present:
        value = production.system_production_value(
            state, grid, registry, player_id, position
        )
        if value <= 0:
            continue
        color = _color_of(state, player_id)
        key = color if color is not None else player_id
        result[key] = value
    return result


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
                owner_id = sys_state.planet_owners.get(planet_id)
                planets[planet_id] = _build_planet_entry(
                    registry,
                    planet_id,
                    by_player,
                    owner_id,
                    entity_keys,
                    _planet_is_exhausted(planet_id, owner_id, state),
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
            "production": _tile_production(state, grid, registry, position),
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


def _planet_is_exhausted(
    planet_id: str, owner_id: str | None, state: GameState
) -> bool:
    """Czy planeta jest wyczerpana (wg listy ``exhausted_planets`` jej właściciela)."""
    if owner_id is None:
        return False
    owner = state.players.get(owner_id)
    return owner is not None and planet_id in owner.exhausted_planets


def _build_planet_entry(
    registry: StaticDataRegistry,
    planet_id: str,
    units_by_player: dict[str, dict[str, int]],
    owner_id: str | None,
    entity_keys: dict[str, str],
    exhausted: bool = False,
) -> dict[str, Any]:
    """Buduje ``PlanetEntityData`` dla planety z jednostkami naziemnymi.

    Zasoby/wpływy pochodzą z rejestru (statyczne dane planety) — także dla planet
    kontrolowanych/zajętych, nie tylko pustych (bez tego panele graczy i tooltipy
    pokazywałyby zera).
    """
    entry = _planet_base(planet_id, owner_id, entity_keys, exhausted)
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
    entry = _planet_base(
        planet_id,
        owner_id,
        entity_keys,
        _planet_is_exhausted(planet_id, owner_id, state),
    )
    entry["entities"] = {}
    _fill_planet_stats(entry, registry, planet_id)
    return entry


def _planet_base(
    planet_id: str,
    owner_id: str | None,
    entity_keys: dict[str, str],
    exhausted: bool = False,
) -> dict[str, Any]:
    """Wspólne pola ``PlanetEntityData`` (kontrola, zasoby domyślne, wyczerpanie)."""
    return {
        "controlledBy": _planet_controller(owner_id, entity_keys),
        "entities": {},
        "commodities": 0,
        "planetaryShield": False,
        "exhausted": exhausted,
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
    breakthrough = registry.breakthrough_for_faction(faction_id)
    if breakthrough is None:
        return None
    return {
        "breakthroughId": breakthrough.id,
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


def _hand_count(player: PlayerState, key: str) -> int:
    """Liczebność prywatnej ręki gracza ``key`` w dokumencie web-data (R6.5, R4.4).

    Dokument buduje się z PROJEKCJI (``project_for_viewer``): ręce viewera pozostają
    pełnymi listami, a ręce pozostałych graczy są zredagowane (listy puste, liczebność
    w ``hidden_card_counts``). Dlatego:

    * gdy prywatna lista jest niepusta → to viewer, zwracamy jej realną długość;
    * w przeciwnym razie (gracz ≠ viewer po redakcji ALBO pusta ręka viewera) →
      liczebność z ``hidden_card_counts`` (0, gdy brak wpisu — pusta ręka, R5.3).

    Dzięki temu web-data nigdy nie ujawnia cudzych identyfikatorów kart (R6.1, R6.5),
    a liczniki są realne (dawne stałe 0 zastąpione faktyczną liczebnością).
    """
    hand = getattr(player.private, key)
    if hand:
        return len(hand)
    return player.hidden_card_counts.get(key, 0)


def _build_player_data(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    entity_keys: dict[str, str],
) -> list[dict[str, Any]]:
    """Buduje listę ``PlayerData`` (minimalny, kompletny dla viewera zestaw pól)."""
    players: list[dict[str, Any]] = []
    deployed_by_player = _deployed_counts_by_player(state)
    active_id = _effective_active_id(state)  # spójny z activePlayer (Bug 7)
    # Sąsiedzi (Neighbors) policzeni raz dla wszystkich graczy (RULES.md 2,
    # R_neighbors). Wynik to player_id; na kolory mapujemy przy serializacji
    # (``Neighbors.tsx`` czyta kolory i odwzorowuje je na frakcje).
    neighbor_ids_by_player = neighbors_by_player(state, grid)
    for player_id, player in sorted(state.players.items()):
        faction = entity_keys.get(player_id, player_id)
        # Pełna nazwa frakcji do WYŚWIETLANIA (displayName/flexibleDisplayName).
        # Czytamy ją z rejestru (pole ``FactionDef.name`` = ``factionName`` z assetów),
        # nigdy z pamięci. Lookup po realnym aliasie ``player.faction`` (nie po kluczu
        # tożsamości, który przy kolizji frakcji bywa ``player_id``). Fallback na klucz
        # ``faction``, gdy frakcja nieznana w rejestrze lub bez nazwy (null/neutral/
        # placeholder) — ścieżka bezpieczna, NIE rzuca. Pole ``faction`` (alias) zostaje
        # bez zmian: frontend używa go jako klucza i do grafiki ``/factions/{alias}.png``.
        faction_def = (
            registry.factions.get(player.faction) if player.faction else None
        )
        faction_display = (
            faction_def.name if faction_def is not None and faction_def.name else faction
        )
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
        # Sąsiedzi jako KOLORY (kontrakt viewera): z player_id na kolor przez
        # ``_color_of``; gracze bez jednoznacznego koloru są pomijani (viewer i tak
        # mapuje kolor→frakcja). Sortujemy dla stabilności dokumentu.
        neighbor_colors = sorted(
            color
            for neighbor_id in neighbor_ids_by_player.get(player_id, set())
            if (color := _color_of(state, neighbor_id)) is not None
        )
        players.append(
            {
                "discordId": player_id,
                "userName": player_id,
                "faction": faction,
                "color": player.color or "gray",
                "displayName": faction_display,
                "flexibleDisplayName": faction_display,
                # Model per-gracz (R6.2/R6.3/R6.4): nazwa wyświetlana gracza,
                # typ sterowania (HUMAN/BOT) i poziom trudności (str dla BOT,
                # None dla HUMAN). Pola addytywne — frontend AsyncTI4 je ignoruje,
                # nasze panele odczytają.
                "playerName": player.display_name,
                "controlType": player.control_type.value,
                "difficulty": player.difficulty,
                "personality": player.personality,
                "isSpeaker": state.speaker_id == player_id,
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
                # Wyczerpane technologie — tylko te, które gracz faktycznie posiada.
                "exhaustedTechs": [
                    t
                    for t in player.exhausted_technologies
                    if t in player.technologies
                ],
                # Zdolności frakcji + technologie frakcyjne (sekcja abilities karty
                # gracza). notResearchedFactionTechs frontend wyszarza; zbadane
                # frakcyjne są w ``techs`` (trafiają do racka techów).
                "abilities": abilities,
                "factionTechs": faction_techs,
                "notResearchedFactionTechs": not_researched_ft,
                "planets": controlled,
                # Wyczerpane planety — tylko te, które gracz faktycznie kontroluje
                # (utrata planety czyści stan wyczerpania w widoku).
                "exhaustedPlanets": [
                    p for p in player.exhausted_planets if p in controlled
                ],
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
                # Promissory notes w strefie gracza (jawne — RULES.md 2d). ODRĘBNE
                # od licznika ręki ``pnCount`` (ręka tajna). Puste do czasu logiki
                # zagrywania notek; dziś zasilane przez God-Mode.
                "promissoryNotesInPlayArea": list(player.promissory_notes_in_play),
                "followedSCs": [],
                "unfollowedSCs": [],
                # Karty strategii gracza (numery inicjatywy) — kolejność tur w panelu faz.
                "scs": list(player.strategy_cards),
                "exhaustedSCs": list(player.exhausted_strategy_cards),
                # Sąsiedzi (Neighbors) jako kolory — RULES.md 2 / R_neighbors.
                "neighbors": neighbor_colors,
                # Realne liczebności prywatnych rąk (R6.5, R4.4). Dla viewera —
                # długości jego list; dla innych — z hidden_card_counts wypełnionego
                # przez projekcję. Nigdy nie ujawniamy cudzych identyfikatorów kart.
                "soCount": _hand_count(player, "secret_objectives"),
                "pnCount": _hand_count(player, "promissory_notes"),
                "acCount": _hand_count(player, "action_cards"),
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
    viewing_player: str | None = None,
) -> dict[str, Any]:
    """Serializuje stan gry do dokumentu ``PlayerDataResponse`` dla frontendu ti4_web.

    Dokument budowany jest z PROJEKCJI stanu do perspektywy jednego „gracza
    patrzącego" (``project_for_viewer``): ręce viewera są pełne, a prywatne ręce
    pozostałych graczy zredagowane do samych liczebności (R6.1, R6.5).

    Args:
        grid: Bieżąca mapa (źródło pozycji, systemów, anomalii).
        registry: Statyczne dane (planety — zasoby/wpływy).
        state: Bieżący stan gry (gracze, jednostki).
        game_name: Identyfikator gry wyświetlany/używany przez frontend.
        vps_to_win: Próg punktów zwycięstwa.
        viewing_player: Gracz, z którego perspektywy rzutujemy dokument (R6.6).
            ``None`` → używamy aktywnego gracza (``state.active_player_id``).

    Returns:
        Słownik gotowy do serializacji JSON zgodny z ``PlayerDataResponse``.

    Perspektywa dokumentu (R6.6/R6.7):

    * jawny ``viewing_player`` → projekcja z jego perspektywy (pełna ręka viewera,
      reszta zredagowana);
    * brak ``viewing_player``, ale jest aktywny gracz → perspektywa aktywnego;
    * brak OBU (``active_player_id is None`` — normalny stan: między turami, po
      komplecie wyboru kart strategii, fazy bez aktywnego gracza) → dokument z
      rękami WSZYSTKICH graczy zredagowanymi (``project_all_redacted``). To NIE
      jest błąd — po prostu nikt nie ma w tym momencie wglądu w pełną rękę, więc
      pokazujemy same liczniki. Dokument buduje się normalnie.
    """
    # R6.6: brak jawnego viewera → aktywny gracz jako perspektywa domyślna.
    viewer = viewing_player or state.active_player_id
    # R6.1: projekcja PRZED serializacją. Gdy znamy viewera → jego perspektywa.
    # Gdy viewera brak (jawnego i aktywnego), a stan niepusty → redagujemy ręce
    # wszystkich (perspektywa „nikt nie patrzy"), zamiast rzucać — ``None`` to
    # poprawny stan gry. Pusty stan serializujemy wprost (brak rąk do redakcji).
    if viewer is not None:
        projected = project_for_viewer(state, viewer)
    elif state.players:
        projected = project_all_redacted(state)
    else:
        projected = state

    # Jedna mapa klucz-tożsamości dla CAŁEGO dokumentu (jednostki, planety, heksy,
    # playerData). Spójny klucz eliminuje desync panel↔mapa (Bug 1/2).
    entity_keys = _entity_key_map(projected)
    tile_unit_data, tile_positions = _build_tile_unit_data(
        grid, registry, projected, entity_keys
    )
    return {
        "gameName": game_name,
        "gameRound": projected.round_number,
        "ringCount": _ring_count(grid),
        "vpsToWin": vps_to_win,
        # Wersja schematu danych oczekiwana przez frontend (ti4_web). Poniżej tej
        # wartości frontend blokuje render ekranem "Update Needed". Trzymamy stałą
        # zgodną z REQUIRED_VERSION_SCHEMA w GameMapPage.tsx.
        "versionSchema": WEB_DATA_SCHEMA_VERSION,
        "tilePositions": tile_positions,
        "tileUnitData": tile_unit_data,
        "playerData": _build_player_data(projected, registry, grid, entity_keys),
        "statTilePositions": _build_stat_tile_positions(projected, grid, entity_keys),
        "gameState": _build_game_state(projected),
        "lawsInPlay": [],
        "strategyCards": _build_strategy_cards(projected, registry, entity_keys),
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
