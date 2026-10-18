"""EventStore — Snapshot Stack (Memento) w SQLite z obsługą Undo/Redo.

Każda zatwierdzona zmiana stanu zapisuje pełną, lekką migawkę ``GameState``
(serializowaną do JSON) wraz z metadanymi akcji. Wskaźnik ``current`` wskazuje
aktywną migawkę; ``undo``/``redo`` przesuwają go po stosie. Nowy ``commit`` po
cofnięciu obcina gałąź "redo" (klasyczna semantyka historii edycji).

Model ten gwarantuje bezbłędne cofanie dowolnej zmiany, w tym ręcznych korekt
w trybie God-Mode.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from src.core.game_state import GameState


class EventStore:
    """Stos migawek stanu gry oparty na SQLite.

    Backend API (FastAPI/Uvicorn) obsługuje żądania w wielu wątkach (synchroniczne
    endpointy trafiają do threadpoola). Dlatego połączenie SQLite tworzymy z
    ``check_same_thread=False`` i serializujemy dostęp blokadą — pojedynczy
    ``EventStore`` jest bezpieczny do użycia współbieżnego.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                seq        INTEGER PRIMARY KEY AUTOINCREMENT,
                label      TEXT NOT NULL,
                state_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pointer (
                id      INTEGER PRIMARY KEY CHECK (id = 0),
                current INTEGER
            );
            INSERT OR IGNORE INTO pointer (id, current) VALUES (0, NULL);
            """
        )
        self._conn.commit()

    # --- Zapis / historia ----------------------------------------------

    def commit(self, state: GameState, label: str = "commit") -> int:
        """Zapisuje migawkę stanu jako nową pozycję bieżącą.

        Jeśli bieżąca pozycja nie jest ostatnią (po jednym lub wielu ``undo``),
        wszystkie migawki po niej są usuwane (obcięcie gałęzi redo).

        Returns:
            Numer sekwencyjny (``seq``) zapisanej migawki.
        """
        with self._lock:
            current = self._current_seq()
            if current is not None:
                self._conn.execute("DELETE FROM snapshots WHERE seq > ?", (current,))

            cursor = self._conn.execute(
                "INSERT INTO snapshots (label, state_json) VALUES (?, ?)",
                (label, state.model_dump_json()),
            )
            new_seq = int(cursor.lastrowid or 0)
            self._set_current(new_seq)
            self._conn.commit()
            return new_seq

    def current(self) -> GameState | None:
        """Zwraca stan na bieżącej pozycji wskaźnika (lub None, gdy pusty)."""
        with self._lock:
            seq = self._current_seq()
            if seq is None:
                return None
            return self._load(seq)

    def undo(self) -> GameState | None:
        """Cofa do poprzedniej migawki. Zwraca nowy stan bieżący lub None."""
        with self._lock:
            seq = self._current_seq()
            if seq is None:
                return None
            prev = self._conn.execute(
                "SELECT seq FROM snapshots WHERE seq < ? ORDER BY seq DESC LIMIT 1",
                (seq,),
            ).fetchone()
            if prev is None:
                return None  # Jesteśmy na najstarszej migawce — brak cofania.
            self._set_current(int(prev["seq"]))
            self._conn.commit()
            return self._load(int(prev["seq"]))

    def redo(self) -> GameState | None:
        """Ponawia do następnej migawki. Zwraca nowy stan bieżący lub None."""
        with self._lock:
            seq = self._current_seq()
            if seq is None:
                return None
            nxt = self._conn.execute(
                "SELECT seq FROM snapshots WHERE seq > ? ORDER BY seq ASC LIMIT 1",
                (seq,),
            ).fetchone()
            if nxt is None:
                return None  # Jesteśmy na najnowszej migawce — brak ponawiania.
            self._set_current(int(nxt["seq"]))
            self._conn.commit()
            return self._load(int(nxt["seq"]))

    def can_undo(self) -> bool:
        with self._lock:
            seq = self._current_seq()
            if seq is None:
                return False
            row = self._conn.execute(
                "SELECT 1 FROM snapshots WHERE seq < ? LIMIT 1", (seq,)
            ).fetchone()
            return row is not None

    def can_redo(self) -> bool:
        with self._lock:
            seq = self._current_seq()
            if seq is None:
                return False
            row = self._conn.execute(
                "SELECT 1 FROM snapshots WHERE seq > ? LIMIT 1", (seq,)
            ).fetchone()
            return row is not None

    def history_size(self) -> int:
        """Łączna liczba migawek w historii."""
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM snapshots"
            ).fetchone()
            return int(row["n"])

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- Wewnętrzne -----------------------------------------------------

    def _current_seq(self) -> int | None:
        row = self._conn.execute(
            "SELECT current FROM pointer WHERE id = 0"
        ).fetchone()
        if row is None or row["current"] is None:
            return None
        return int(row["current"])

    def _set_current(self, seq: int) -> None:
        self._conn.execute(
            "UPDATE pointer SET current = ? WHERE id = 0", (seq,)
        )

    def _load(self, seq: int) -> GameState:
        row = self._conn.execute(
            "SELECT state_json FROM snapshots WHERE seq = ?", (seq,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Brak migawki o seq={seq}")
        return GameState.model_validate_json(row["state_json"])
