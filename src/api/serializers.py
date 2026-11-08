"""Serializery widoku mapy (DTO ``MapView``) + stałe setupu.

Wydzielone z ``app.py`` przy refaktorze na routery (docs/ARCHITEKTURA_KODU.md §4),
żeby routery i fabryka aplikacji współdzieliły budowę ``MapView`` bez importu z ``app``.
To nadal warstwa ``api`` (serializacja do UI), nie reguły gry.
"""

from __future__ import annotations

from src import config
from src.api.schemas import MapEdge, MapTile, MapView, PlanetUnits, UnitStack
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.home_slots import HOME_SLOT_COLORS_6P, home_slot_color
from src.core.map_string import HOME_SLOT_SYSTEM_ID
from src.core.registry import StaticDataRegistry
from src.core.system_planets import planets_of_system
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

# Testowy map string (6-osobowa plansza) używany, gdy frontend nie poda własnego.
DEFAULT_MAP_STRING = (
    "23 49 77 66 71 39 64 31 35 76 50 37 73 46 34 75 47 65 "
    "0 59 79 0 25 28 0 26 42 0 40 41 0 45 69 0 62 44"
)

# Kolejność automatycznego przydziału kolorów/slotów domowych wg kolejności graczy
# (gracz 1 → red/301, 2 → green/304, ...). Źródło: HOME_SLOT_COLORS_6P.
AUTO_SLOT_ORDER: list[tuple[str, str]] = [
    (position, color) for position, color in sorted(HOME_SLOT_COLORS_6P.items())
]


def _unit_image_url(color: str | None, base_type: str) -> str | None:
    """URL grafiki jednostki: ``/static/units/<kolor>_<asyncId>.png`` (lub None)."""
    if not color:
        return None
    async_id = ASYNC_ID_BY_BASE_TYPE.get(base_type)
    if async_id is None:
        return None
    return f"{config.STATIC_URL_PREFIX}/units/{color}_{async_id}.png"


def _stacks_from_units(
    units_by_player: dict[str, dict[str, int]], state: GameState
) -> list[UnitStack]:
    """Buduje listę stosów jednostek (z kolorem i grafiką) z surowych liczników."""
    stacks: list[UnitStack] = []
    for player_id, counts in sorted(units_by_player.items()):
        player = state.players.get(player_id)
        color = player.color if player else None
        for base_type, count in sorted(counts.items()):
            if count <= 0:
                continue
            stacks.append(
                UnitStack(
                    player_id=player_id,
                    base_type=base_type,
                    count=count,
                    color=color,
                    image_url=_unit_image_url(color, base_type),
                )
            )
    return stacks


def build_map_view(
    grid: HexGrid, registry: StaticDataRegistry, state: GameState
) -> MapView:
    """Serializuje ``HexGrid`` + stan gry do reprezentacji mapy dla frontendu.

    Dane kafelka (nazwa, planety, anomalie, wormhole, grafika) z rejestru i grafu;
    jednostki (przestrzeń + planety) z ``GameState`` — bez reguł z pamięci.
    """
    tiles: list[MapTile] = []
    for position in sorted(grid.positions):
        q, r, s = grid.coordinates(position)
        system_id = grid.system_id_at(position)

        # Slot domowy gracza (kolorowy róg bez kafelka systemu).
        if system_id == HOME_SLOT_SYSTEM_ID:
            tiles.append(
                MapTile(
                    position=position,
                    system_id=system_id,
                    q=q,
                    r=r,
                    s=s,
                    is_home_slot=True,
                    home_color=home_slot_color(position),
                )
            )
            continue

        system = registry.systems.get(system_id)
        image_url: str | None = None
        if system is not None and system.image_path:
            image_url = f"{config.STATIC_URL_PREFIX}/tiles/{system.image_path}"

        sys_state = state.systems.get(position)
        space_stacks: list[UnitStack] = []
        planet_units: list[PlanetUnits] = []
        if sys_state is not None:
            space_stacks = _stacks_from_units(sys_state.space_units, state)
            for planet_id, by_player in sorted(sys_state.planet_units.items()):
                planet_units.append(
                    PlanetUnits(
                        planet_id=planet_id,
                        owner_id=sys_state.planet_owners.get(planet_id),
                        stacks=_stacks_from_units(by_player, state),
                    )
                )

        tiles.append(
            MapTile(
                position=position,
                system_id=system_id,
                q=q,
                r=r,
                s=s,
                wormholes=list(system.wormholes) if system else [],
                anomalies=sorted(grid.anomalies_at(position)),
                planets=planets_of_system(state, registry, position, grid) if system else [],
                name=system.name if system else None,
                image_url=image_url,
                space_units=space_stacks,
                planet_units=planet_units,
            )
        )
    edges = [
        MapEdge(a=a, b=b, kind=kind)  # type: ignore[arg-type]
        for a, b, kind in grid.edges()
    ]
    return MapView(tiles=tiles, edges=edges)
