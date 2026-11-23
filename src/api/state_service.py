"""StateService — spina GameState, EventStore i rozsyłanie przez WebSocket.

Jest jedynym miejscem mutującym stan gry w warstwie API: każda zmiana (nadpisanie,
patch God-Mode, undo, redo) jest commitowana do ``EventStore`` i rozsyłana do
klientów WebSocket jako ``StateEnvelope``. Dzięki temu backend pozostaje źródłem
prawdy, a frontend tylko odzwierciedla rozesłany stan.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from src.api.connection_manager import ConnectionManager
from src.api.schemas import GodModePatch, HistoryInfo, StateEnvelope
from src.api.seats import Identity, current_author, current_identity
from src.core import activity, rules_hooks, step_settle
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.visibility import project_strict


class StateService:
    """Fasada operacji na stanie gry z historią i rozsyłaniem."""

    def __init__(
        self,
        store: EventStore,
        manager: ConnectionManager,
        initial_state: GameState | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._store = store
        self._manager = manager
        # Źródło czasu rzeczywistego dla zegara szachowego (RULES.md 58); testy podmieniają.
        self._now = now
        # Słuchacze rozesłania stanu (runner bota budzi się po każdej zmianie widocznej dla graczy).
        self._listeners: list[Callable[[], None]] = []
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

    def envelope(self, identity: Identity | None = None) -> StateEnvelope:
        """Koperta dla klienta: stan W JEGO PROJEKCJI + metadane historii (RULES.md 44.3).

        ``identity`` pominięte → tożsamość bieżącego żądania (``current_identity``). Tryb lokalny
        i host-operator dostają pełny stan; gracz sieciowy — ``project_strict`` ze swojego miejsca.
        Dzięki temu KAŻDA odpowiedź akcji (wszystkie zwracają kopertę) jest bezpieczna.
        """
        who = identity if identity is not None else current_identity.get()
        state = self.current_state()
        if not who.sees_everything:
            state = project_strict(state, who.player_id)
        return StateEnvelope(state=state, history=self.history_info())

    # --- Mutacje --------------------------------------------------------

    def recent_chain(self, limit: int) -> list[tuple[int, str, GameState]]:
        """Ostatnie ``limit`` migawek do bieżącej włącznie (hold-rewind): ``(seq, label, stan)``."""
        return self._store.recent_chain(limit)

    def recent_steps(self, limit: int) -> list[tuple[int, str, str | None, GameState]]:
        """Ostatnie ``limit`` migawek z autorami kroków (Undo gracza, RULES.md 44.7)."""
        return self._store.recent_steps(limit)

    def replace_state(
        self, state: GameState, label: str = "replace", *, branch_from: int | None = None
    ) -> StateEnvelope:
        """Nadpisuje cały stan (God-Mode) i commituje nową migawkę.

        ``branch_from`` (hold-rewind, RULES.md 53.7): migawka, od której historia się rozgałęzia
        (późniejsze kroki są odrzucane jednym atomowym zapisem, jak przy Undo + nowa akcja).
        """
        # Koniec gry po progu VP z DOWOLNEGO źródła (nie tylko punktowania celów).
        before = (
            self._store.load(branch_from) if branch_from is not None else self._store.current()
        )
        # Reguły „po każdym kroku” (koniec gry, Nexus, limity, liderzy, pauza reakcji, zegar
        # szachowy) leżą w core - ta sama ścieżka dla bota (RULES.md 65.1).
        after = step_settle.settle_step(
            state, rules_hooks.bound_registry(), self._now(), label, before=before
        )
        entry = activity.derive_activity(label, before, after)
        self._store.commit(
            after,
            label=label,
            activity_json=entry.model_dump_json() if entry else None,
            branch_from=branch_from,
            author=current_author.get(),
        )
        return self.envelope()

    def swap_store(self, store: EventStore) -> EventStore:
        """Przełącza bieżący plik partii (nowa gra / „Load game"); zwraca poprzedni magazyn."""
        previous, self._store = self._store, store
        if self._store.current() is None:
            self._store.commit(GameState(), label="initial")
        return previous

    def close(self) -> None:
        """Zamyka bieżący plik partii (koniec procesu)."""
        self._store.close()

    def get_meta(self, key: str) -> str | None:
        """Metadana partii z pliku zapisu (mapa, miejsca) — patrz ``EventStore.get_meta``."""
        return self._store.get_meta(key)

    def set_meta(self, key: str, value: str) -> None:
        """Trwały zapis metadanej partii (przeżywa restart serwera, RULES.md 44.4)."""
        self._store.set_meta(key, value)

    def now(self) -> float:
        """Bieżący czas (s UNIX) ze źródła serwisu — dla zegara szachowego."""
        return self._now()

    def current_seq(self) -> int | None:
        """Numer bieżącej migawki historii."""
        return self._store.current_seq()

    def activity_feed(self) -> list[tuple[int, str, bool, float | None, activity.Activity | None]]:
        """Feed aktywności: ``(seq, label, is_current, created_at, wpis)`` chronologicznie."""
        current = self._store.current_seq()
        return [
            (
                seq,
                label,
                seq == current,
                created_at,
                activity.Activity.model_validate_json(raw) if raw else None,
            )
            for seq, label, created_at, raw in self._store.activity_rows()
        ]

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

    def current_label(self) -> str | None:
        """Etykieta bieżącej migawki (``None``, gdy historia pusta)."""
        for _seq, label, is_current in self._store.history():
            if is_current:
                return label
        return None

    def redo(self) -> StateEnvelope:
        """Ponawia do następnej migawki (jeśli możliwe)."""
        self._store.redo()
        return self.envelope()

    # --- Rozsyłanie -----------------------------------------------------

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Rejestruje wywołanie po każdym ``broadcast`` (np. ``BotRunner.notify``)."""
        self._listeners.append(listener)

    async def broadcast(self) -> None:
        """Rozsyła kopertę stanu — każdemu klientowi WebSocket jego własną projekcję."""
        for listener in self._listeners:
            listener()
        await self._manager.broadcast_each(
            lambda identity: self.envelope(identity).model_dump(mode="json")
        )
