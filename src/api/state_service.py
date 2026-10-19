"""StateService — spina GameState, EventStore i rozsyłanie przez WebSocket.

Jest jedynym miejscem mutującym stan gry w warstwie API: każda zmiana (nadpisanie,
patch God-Mode, undo, redo) jest commitowana do ``EventStore`` i rozsyłana do
klientów WebSocket jako ``StateEnvelope``. Dzięki temu backend pozostaje źródłem
prawdy, a frontend tylko odzwierciedla rozesłany stan.
"""

from __future__ import annotations

from src.api.connection_manager import ConnectionManager
from src.api.schemas import GodModePatch, HistoryInfo, StateEnvelope
from src.core.event_store import EventStore
from src.core.game_state import GameState


class StateService:
    """Fasada operacji na stanie gry z historią i rozsyłaniem."""

    def __init__(
        self,
        store: EventStore,
        manager: ConnectionManager,
        initial_state: GameState | None = None,
    ) -> None:
        self._store = store
        self._manager = manager
        # Zapewnij, że historia ma co najmniej jedną migawkę (stan bazowy).
        if self._store.current() is None:
            self._store.commit(initial_state or GameState(), label="initial")

    # --- Odczyt ---------------------------------------------------------

    def current_state(self) -> GameState:
        """Zwraca bieżący stan gry (nigdy None — historia jest inicjalizowana)."""
        state = self._store.current()
        if state is None:  # pragma: no cover — niemożliwe po inicjalizacji
            state = GameState()
            self._store.commit(state, label="initial")
        return state

    def history_info(self) -> HistoryInfo:
        """Buduje informację o dostępności Undo/Redo i rozmiarze historii."""
        return HistoryInfo(
            can_undo=self._store.can_undo(),
            can_redo=self._store.can_redo(),
            history_size=self._store.history_size(),
        )

    def envelope(self) -> StateEnvelope:
        """Koperta rozsyłana klientom: bieżący stan + metadane historii."""
        return StateEnvelope(state=self.current_state(), history=self.history_info())

    # --- Mutacje --------------------------------------------------------

    def replace_state(self, state: GameState, label: str = "replace") -> StateEnvelope:
        """Nadpisuje cały stan (God-Mode) i commituje nową migawkę."""
        self._store.commit(state.clone(), label=label)
        return self.envelope()

    def apply_patch(self, patch: GodModePatch) -> StateEnvelope:
        """Nakłada częściowy patch God-Mode na bieżący stan.

        Pola ``None`` są pomijane; podane nadpisują odpowiednie sekcje. Wynik jest
        walidowany przez ``GameState`` (błędne dane → ``ValidationError``), a dopiero
        poprawny stan trafia do historii.
        """
        data = self.current_state().model_dump()
        patch_data = patch.model_dump(exclude_none=True)
        data.update(patch_data)
        new_state = GameState.model_validate(data)
        return self.replace_state(new_state, label="god-mode-patch")

    def history_entries(self) -> list[tuple[int, str, bool]]:
        """Lista migawek historii: ``(seq, label, is_current)``."""
        return self._store.history()

    def goto(self, seq: int) -> StateEnvelope:
        """Przeskakuje do wskazanej migawki historii (undo/redo do punktu)."""
        self._store.goto(seq)
        return self.envelope()

    def undo(self) -> StateEnvelope:
        """Cofa do poprzedniej migawki (jeśli możliwe)."""
        self._store.undo()
        return self.envelope()

    def redo(self) -> StateEnvelope:
        """Ponawia do następnej migawki (jeśli możliwe)."""
        self._store.redo()
        return self.envelope()

    # --- Rozsyłanie -----------------------------------------------------

    async def broadcast(self) -> None:
        """Rozsyła bieżącą kopertę stanu do wszystkich klientów WebSocket."""
        await self._manager.broadcast_json(self.envelope().model_dump(mode="json"))
