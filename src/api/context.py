"""Wspólny kontekst aplikacji dla routerów (współdzielone zależności).

Routery (``api/routers/*``) nie mają dostępu do zmiennych domknięcia fabryki
``create_app``. Zamiast tego trzymamy współdzielone obiekty w jednym ``AppContext``
na ``app.state.ctx``; router pobiera go zależnością ``get_ctx``. ``current_grid`` to
bieżąca mapa (mutowalna — podmieniana przy ``/map/load`` i ``/game/new``), więc jest
własnością kontekstu, nie wartością kopiowaną.

Odczyt ``current_grid`` synchronizuje wormhole z ŻETONÓW położonych w grze (np. Gamma
Wormhole z eksploracji, ``SystemState.wormhole_tokens``) ze stanem — dzięki temu mapa
jest zawsze spójna ze stanem, także po Undo/Redo.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from fastapi import Request

from src.api.connection_manager import ConnectionManager
from src.api.saves import SaveManager
from src.api.seats import SeatRegistry
from src.api.serializers import build_map_view
from src.api.state_service import StateService
from src.core import board_graph, fracture, nexus, rules_hooks, variants
from src.core.event_store import EventStore
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

SEATS_META_KEY = "seats"
"""Klucz metadanej partii: miejsca, lobby i tokeny (``SeatRegistry.to_json``)."""

MAP_META_KEY = "map"
"""Klucz metadanej partii: rozstawione kafelki (``HexGrid.to_placements``)."""


class AppContext:
    """Współdzielone zależności warstwy API (jedna instancja na aplikację)."""

    def __init__(
        self,
        service: StateService,
        manager: ConnectionManager,
        registry: StaticDataRegistry,
        current_grid: HexGrid,
        seats: SeatRegistry | None = None,
        saves: SaveManager | None = None,
        restore_grid: Callable[[EventStore], HexGrid] | None = None,
        bug_reports_dir: Path | None = None,
    ) -> None:
        self.service = service
        # Miejsca przy stole / tokeny (RULES.md 44.2); tryb lokalny = rejestr bez tokenów.
        self.seats = seats if seats is not None else SeatRegistry()
        # Pliki zapisów (RULES.md 44.4); ``None`` = bez katalogu (testy, pamięć).
        self.saves = saves
        # Katalog zgłoszeń „Report bug" na dysku hosta; ``None`` = wyłączone (testy, pamięć).
        self.bug_reports_dir = bug_reports_dir
        self._restore_grid = restore_grid
        self.save_name: str | None = None
        self.manager = manager
        # Rejestr danych bez modułów wariantów + rejestry dla zestawów modułów (budowane
        # leniwie, raz na zestaw). ``registry`` zwraca rejestr BIEŻĄCEJ gry.
        self._base_registry = registry
        self._variant_registries: dict[tuple[str, ...], StaticDataRegistry] = {
            registry.variant_ids: registry
        }
        self._grid = current_grid
        # Efekty kart akcji (core) patrzą na całą planszę, ale nie dostają siatki w parametrach.
        board_graph.bind_grid_provider(lambda: self.current_grid)

    @property
    def registry(self) -> StaticDataRegistry:
        """Rejestr danych bieżącej gry: dane aktywnych źródeł + jej moduły wariantów.

        Moduły (``GameState.decks.variants``) nakładają erraty i nowe komponenty
        (``core/variants.py``). Hooki (``rules_hooks``) czytają ten sam rejestr - wiążemy go
        przy zmianie.
        """
        state = self.service.current_state()
        ids = variants.game_module_ids(state.decks.variants, state.decks.agenda_variant)
        registry = self.registry_for(ids)
        if rules_hooks.bound_registry() is not registry:
            rules_hooks.bind_registry(registry)
        return registry

    def registry_for(self, variant_ids: tuple[str, ...] | list[str]) -> StaticDataRegistry:
        """Rejestr dla zestawu modułów (cache). Raises: ``VariantConfigError``."""
        key = tuple(variant_ids)
        found = self._variant_registries.get(key)
        if found is None:
            found = StaticDataRegistry(
                enabled_sources=sorted(self._base_registry.enabled_sources),
                variant_ids=key,
            )
            self._variant_registries[key] = found
        return found

    @property
    def current_grid(self) -> HexGrid:
        """Bieżąca mapa, zsynchronizowana z żetonami wormhole ze stanu gry."""
        state = self.service.current_state()
        self._grid.sync_token_wormholes(
            {pos: s.token_wormholes() for pos, s in state.systems.items() if s.token_wormholes()}
        )
        # The Fracture (kafle frac1..7) i portale ingress/egress - też ze stanu (Undo/Redo).
        fracture.sync_grid(self._grid, state, self.registry)
        # Wormhole Nexus: strona kafelka (82a nieaktywna / 82b aktywna) wg stanu.
        nexus.sync_grid(self._grid, state, self.registry)
        return self._grid

    @current_grid.setter
    def current_grid(self, grid: HexGrid) -> None:
        self._grid = grid

    def start_new_save(self) -> None:
        """Nowa gra = nowy plik zapisu (stare partie zostają do wczytania). Bez katalogu — nic.

        Lobby (członkowie, tryb sieciowy) przechodzi do nowego pliku: zapis rejestru miejsc.
        """
        if self.saves is None:
            return
        path = self.saves.new_path()
        self.service.swap_store(EventStore(path)).close()
        self.save_name = path.name
        self.seats.persist_now()

    def load_save(self, name: str) -> None:
        """„Load game": przełącza na wskazany plik — stan, historia, mapa i miejsca graczy.

        Tryb sieciowy (lobby) zostaje taki, jaki jest teraz. Raises: ``ValueError``.
        """
        if self.saves is None:
            raise ValueError("Saves are not enabled on this server.")
        path = self.saves.path(name)
        store = EventStore(path)
        try:
            store.current()  # nieczytelny zapis → błąd, bieżąca partia zostaje
        except Exception as exc:
            store.close()
            raise ValueError(f"Cannot load {name}: {exc}") from exc
        network = self.seats.network
        self.service.swap_store(store).close()
        self.save_name = name
        if self._restore_grid is not None:
            self._grid = self._restore_grid(store)
        self.seats.load(store.get_meta(SEATS_META_KEY))
        if self.seats.network != network:
            self.seats.set_network(network)

    def set_map(self, grid: HexGrid) -> None:
        """Podmienia mapę i zapisuje ją w pliku partii (wznowienie po restarcie)."""
        self._grid = grid
        self.save_map()

    def save_map(self) -> None:
        """Zapisuje bieżące rozstawienie kafelków w pliku partii (RULES.md 44.4).

        Siatka heksów nie jest częścią ``GameState`` — bez tego zapisu restart serwera
        przywróciłby stan gry na mapie demonstracyjnej. Wołać po każdej zmianie siatki
        w miejscu (np. kafelek domowy dokładanego gracza).
        """
        self.service.set_meta(MAP_META_KEY, json.dumps(self._grid.to_placements()))

    async def broadcast_map(self) -> None:
        """Rozsyła świeży widok mapy (z jednostkami) do klientów WebSocket."""
        view = build_map_view(self.current_grid, self.registry, self.service.current_state())
        await self.manager.broadcast_json(
            {"type": "map", **view.model_dump(mode="json")}
        )


def get_ctx(request: Request) -> AppContext:
    """Zależność FastAPI: zwraca ``AppContext`` z ``app.state.ctx``."""
    ctx: AppContext = request.app.state.ctx
    return ctx
