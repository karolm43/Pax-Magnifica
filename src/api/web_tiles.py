"""web-data: kafelki mapy (``tileUnitData``: jednostki, planety, produkcja, osłona PDS)."""

from __future__ import annotations

from typing import Any

from src.api import web_setup
from src.api.web_game import _color_of
from src.core import invasion as invasion_core
from src.core import (
    production,
    space_cannon,
)
from src.core.fracture import is_fracture_position
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.map_string import HOME_SLOT_SYSTEM_ID, MECATOL_SYSTEM_ID
from src.core.planet_stats import attachment_defs
from src.core.registry import StaticDataRegistry
from src.core.system_planets import planets_of_system
from src.core.unit_catalog import (
    ASYNC_ID_BY_BASE_TYPE,
)


def _planet_attachment_ids(
    state: GameState, registry: StaticDataRegistry, planet_id: str
) -> list[str]:
    """Id attachmentów (z kart eksploracji) przyczepionych do planety — do żetonów na mapie."""
    # Karty eksploracji i relikty przyczepione do planety (Nano-Forge) - jedno źródło prawdy.
    return [attachment.id for attachment in attachment_defs(state, registry, planet_id)]


def _entities_from_counts(
    counts_by_player: dict[str, dict[str, int]],
    entity_keys: dict[str, str],
    damaged_by_player: dict[str, dict[str, int]] | None = None,
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
            entity: dict[str, Any] = {
                "entityId": async_id,
                "entityType": "unit",
                "count": count,
            }
            # Uszkodzone (Sustain Damage, RULES.md 39): front AsyncTI4 rysuje znacznik.
            damaged = min(
                count, (damaged_by_player or {}).get(player_id, {}).get(base_type, 0)
            )
            if damaged > 0:
                entity["sustained"] = damaged
            entities.append(entity)
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


def _pds_coverage_entry(
    covering: dict[str, tuple[int, float]] | None,
    entity_keys: dict[str, str],
) -> dict[str, dict[str, float | int]] | None:
    """Kształt ``tileUnitData[pos].pds`` ({klucz gracza: {count, expected}}) lub None.

    ``covering`` = ``{player_id: (liczba jednostek, oczekiwane trafienia)}`` z
    ``space_cannon.coverage``. Klucz tożsamości gracza jak w reszcie web-data.
    """
    if not covering:
        return None
    return {
        entity_keys.get(player_id, player_id): {"count": count, "expected": expected}
        for player_id, (count, expected) in covering.items()
    }


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
    # Pokrycie ostrzałem Space Cannon (soczewka „Space Cannon range", RULES.md 38.2) liczone
    # RAZ dla całej mapy; per kafelek mapowane niżej na klucze tożsamości graczy.
    sc_coverage = space_cannon.coverage(state, grid, registry)

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
            space = _entities_from_counts(
                sys_state.space_units,
                entity_keys,
                sys_state.damaged_units.get("space"),
            )
            for planet_id, by_player in sys_state.planet_units.items():
                owner_id = sys_state.planet_owners.get(planet_id)
                planets[planet_id] = _build_planet_entry(
                    registry,
                    planet_id,
                    by_player,
                    owner_id,
                    entity_keys,
                    _planet_is_exhausted(planet_id, owner_id, state),
                    sys_state.damaged_units.get(planet_id),
                )
                # Planetary Shield: jednostka z tarczą, której nikt nie odebrał (Arc Secundus).
                planets[planet_id]["planetaryShield"] = invasion_core.planet_shield(
                    state, registry, position, planet_id
                )[1]
            # Żetony dowodzenia w przestrzeni (aktywacja) — klucz tożsamości gracza,
            # spójny z grupowaniem jednostek (frontend porównuje ccs z faction).
            ccs = [
                entity_keys.get(pid, pid) for pid in sys_state.command_tokens
            ]

        # Planety systemu bez jednostek też muszą istnieć w słowniku (frontend
        # kluczuje render po nazwie planety ze statycznych danych — pusty wpis OK).
        if system is not None:
            for planet_id in planets_of_system(state, registry, position, grid):
                planets.setdefault(
                    planet_id,
                    _empty_planet_entry(
                        registry, planet_id, state, position, entity_keys
                    ),
                )

        # Żeton frontier (systemy bez planet) — neutralny token w przestrzeni systemu.
        if sys_state is not None and sys_state.frontier_token:
            space.setdefault("neutral", []).append(
                {"entityId": "frontier", "entityType": "token", "count": 1}
            )

        # Żeton ingress (The Fracture, RULES.md 50): neutralny token w przestrzeni systemu.
        if sys_state is not None and sys_state.ingress_token:
            space.setdefault("neutral", []).append(
                {"entityId": "ingress", "entityType": "token", "count": 1}
            )

        # Thunder's Edge (RULES.md 50): token planety w przestrzeni systemu, w którym leży.
        if position == state.expeditions.thunders_edge_position:
            space.setdefault("neutral", []).append(
                {"entityId": "thundersedge", "entityType": "token", "count": 1}
            )

        # Planety The Fracture bez kontrolera: żeton reliktu (kto je zdobędzie, dobiera relikt).
        if is_fracture_position(position) and system is not None:
            for planet_id in system.planets:
                if sys_state is None or planet_id not in sys_state.planet_owners:
                    planets.setdefault(
                        planet_id,
                        _empty_planet_entry(registry, planet_id, state, position, entity_keys),
                    ).setdefault("entities", {}).setdefault("neutral", []).append(
                        {"entityId": "relictoken", "entityType": "token", "count": 1}
                    )

        # Żeton Custodians na Mecatol Rex: neutralny token planety (klucz "neutral" — nie jest
        # żadnym graczem), rysowany jak inne tokeny z `entityType: "token"`.
        if system_id == MECATOL_SYSTEM_ID and web_setup.custodian_on_board(state):
            for planet_id in system.planets if system is not None else []:
                planets[planet_id].setdefault("entities", {}).setdefault(
                    "neutral", []
                ).append({"entityId": "custodian", "entityType": "token", "count": 1})
                break

        # Żetony wormhole z kart (np. Gamma Wormhole, RULES.md 46): neutralny token w przestrzeni
        # (id tokenu = typ małymi literami, np. "gamma" — z katalogu żetonów frontendu).
        if sys_state is not None:
            for wormhole in sys_state.wormhole_tokens:
                space.setdefault("neutral", []).append(
                    {"entityId": wormhole.lower(), "entityType": "token", "count": 1}
                )

        # Ion Storm (karta frontier): żeton ze stroną aktywną (id katalogu: ionalpha / ionbeta).
        if sys_state is not None and sys_state.ion_storm:
            space.setdefault("neutral", []).append(
                {"entityId": f"ion{sys_state.ion_storm.lower()}", "entityType": "token", "count": 1}
            )
        # Planety-żetony (Mirage z karty frontier, Avernus ze Stellar Genesis Muaat): żeton
        # planety leży w przestrzeni systemu, jak Thunder's Edge (id = token katalogu frontu).
        if sys_state is not None:
            for planet_id in sys_state.added_planets:
                if planet_id in PLANET_TOKENS:
                    space.setdefault("neutral", []).append(
                        {"entityId": planet_id, "entityType": "token", "count": 1}
                    )
        # Żetony frakcji na planetach (sleeper Titans, RULES.md 61.6): token katalogu frontu.
        if sys_state is not None:
            for zone, kinds in sorted(sys_state.faction_tokens.items()):
                for kind in sorted(kinds):
                    token = {"entityId": kind, "entityType": "token", "count": 1}
                    if zone == "space":
                        space.setdefault("neutral", []).append(token)
                    elif zone in planets:
                        planets[zone].setdefault("entities", {}).setdefault(
                            "neutral", []
                        ).append(token)
        # Attachmenty z eksploracji (RULES.md 46): żeton przy planecie, rysowany przez front
        # jak inne wpisy `entityType: "attachment"` (id = `attachmentId` karty, np. "dysonsphere").
        for planet_id, entry in planets.items():
            for attachment_id in _planet_attachment_ids(state, registry, planet_id):
                entry.setdefault("entities", {}).setdefault("neutral", []).append(
                    {"entityId": attachment_id, "entityType": "attachment", "count": 1}
                )

        tile_unit_data[position] = {
            "space": space,
            "planets": planets,
            "ccs": ccs,
            "anomaly": bool(grid.anomalies_at(position)),
            "production": _tile_production(state, grid, registry, position),
            "pds": _pds_coverage_entry(sc_coverage.get(position), entity_keys),
        }

    return tile_unit_data, tile_positions


# Planety dodawane do systemu jako żeton w przestrzeni (``SystemState.added_planets``).
PLANET_TOKENS = frozenset({"mirage", "avernus"})


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
    damaged_by_player: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Buduje ``PlanetEntityData`` dla planety z jednostkami naziemnymi.

    Zasoby/wpływy pochodzą z rejestru (statyczne dane planety) — także dla planet
    kontrolowanych/zajętych, nie tylko pustych (bez tego panele graczy i tooltipy
    pokazywałyby zera). ``damaged_by_player`` = uszkodzenia na tej planecie (mechy).
    """
    entry = _planet_base(planet_id, owner_id, entity_keys, exhausted)
    entry["entities"] = _entities_from_counts(
        units_by_player, entity_keys, damaged_by_player
    )
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
