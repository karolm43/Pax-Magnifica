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
import time
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
        try:
            self._init_schema()
        except sqlite3.DatabaseError:
            self._conn.close()  # plik nie jest bazą — nie trzymaj go otwartego (Windows: blokada)
            raise

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
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self._migrate_snapshots()
        self._conn.commit()

    def _migrate_snapshots(self) -> None:
        """Dokłada kolumny feedu aktywności do starszych baz (idempotentnie)."""
        columns = {
            str(row["name"])
            for row in self._conn.execute("PRAGMA table_info(snapshots)").fetchall()
        }
        if "created_at" not in columns:
            self._conn.execute("ALTER TABLE snapshots ADD COLUMN created_at REAL")
        if "activity_json" not in columns:
            self._conn.execute("ALTER TABLE snapshots ADD COLUMN activity_json TEXT")

    # --- Zapis / historia ----------------------------------------------

    def commit(
        self,
        state: GameState,
        label: str = "commit",
        activity_json: str | None = None,
        branch_from: int | None = None,
    ) -> int:
        """Zapisuje migawkę stanu jako nową pozycję bieżącą.

        Jeśli bieżąca pozycja nie jest ostatnią (po jednym lub wielu ``undo``),
        wszystkie migawki po niej są usuwane (obcięcie gałęzi redo).

        ``activity_json`` to opcjonalny wpis feedu aktywności (``core.activity``),
        zapisany razem z migawką, by feed przeżył restart i szedł za Undo/Redo.

        ``branch_from`` (hold-rewind, RULES.md 53.7): zamiast bieżącej pozycji historia jest
        obcinana PO wskazanej migawce, a nowa migawka staje się jej następnikiem - jeden
        atomowy zapis rozgałęziający historię (bez pośredniego ``goto``).

        Returns:
            Numer sekwencyjny (``seq``) zapisanej migawki.

        Raises:
            KeyError: ``branch_from`` nie istnieje.
        """
        with self._lock:
            current = self._current_seq()
            if branch_from is not None:
                if not self._exists(branch_from):
                    raise KeyError(f"No snapshot with seq={branch_from}")
                current = branch_from
            if current is not None:
                self._conn.execute("DELETE FROM snapshots WHERE seq > ?", (current,))

            cursor = self._conn.execute(
                "INSERT INTO snapshots (label, state_json, created_at, activity_json)"
                " VALUES (?, ?, ?, ?)",
                (label, state.model_dump_json(), time.time(), activity_json),
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

    def history(self) -> list[tuple[int, str, bool]]:
        """Lista migawek: ``(seq, label, is_current)`` w kolejności chronologicznej."""
        with self._lock:
            current = self._current_seq()
            rows = self._conn.execute(
                "SELECT seq, label FROM snapshots ORDER BY seq ASC"
            ).fetchall()
            return [
                (int(r["seq"]), str(r["label"]), int(r["seq"]) == current)
                for r in rows
            ]

    def activity_rows(self) -> list[tuple[int, str, float | None, str | None]]:
        """Migawki z danymi feedu: ``(seq, label, created_at, activity_json)``."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT seq, label, created_at, activity_json FROM snapshots ORDER BY seq ASC"
            ).fetchall()
            return [
                (
                    int(r["seq"]),
                    str(r["label"]),
                    None if r["created_at"] is None else float(r["created_at"]),
                    None if r["activity_json"] is None else str(r["activity_json"]),
                )
                for r in rows
            ]

    def current_seq(self) -> int | None:
        """Numer bieżącej migawki (None, gdy historia pusta)."""
        with self._lock:
            return self._current_seq()

    def goto(self, seq: int) -> GameState | None:
        """Przeskakuje wskaźnik na wskazaną migawkę (undo/redo do punktu).

        Nie obcina historii — pozwala wrócić i ponowić. Zwraca stan lub None,
        gdy ``seq`` nie istnieje.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT seq FROM snapshots WHERE seq = ?", (seq,)
            ).fetchone()
            if row is None:
                return None
            self._set_current(seq)
            self._conn.commit()
            return self._load(seq)

    def load(self, seq: int) -> GameState | None:
        """Odczyt stanu migawki ``seq`` BEZ zmiany wskaźnika (None, gdy nie istnieje)."""
        with self._lock:
            if not self._exists(seq):
                return None
            return self._load(seq)

    def recent_chain(self, limit: int) -> list[tuple[int, str, GameState]]:
        """Ostatnie ``limit`` migawek aż do bieżącej włącznie: ``(seq, label, stan)`` rosnąco.

        To liniowa droga od przeszłości do teraźniejszości (migawki za wskaźnikiem - gałąź
        "redo" - nie wchodzą). Odczyt bez zmiany wskaźnika.
        """
        with self._lock:
            current = self._current_seq()
            if current is None:
                return []
            rows = self._conn.execute(
                "SELECT seq, label, state_json FROM snapshots WHERE seq <= ?"
                " ORDER BY seq DESC LIMIT ?",
                (current, max(1, limit)),
            ).fetchall()
            return [
                (int(r["seq"]), str(r["label"]), GameState.model_validate_json(r["state_json"]))
                for r in reversed(rows)
            ]

    # --- Metadane partii (poza historią stanu, RULES.md 44.4) -----------

    def get_meta(self, key: str) -> str | None:
        """Wartość metadanej partii (np. mapa, miejsca przy stole) albo ``None``.

        Metadane NIE są migawkami: nie cofa ich Undo i nie trafiają do klientów — to dane
        procesu potrzebne do wznowienia partii z pliku po restarcie serwera.
        """
        with self._lock:
            row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
            return None if row is None else str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        """Zapisuje (nadpisuje) metadaną partii — trwale, od razu."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _exists(self, seq: int) -> bool:
        return (
            self._conn.execute("SELECT 1 FROM snapshots WHERE seq = ?", (seq,)).fetchone()
            is not None
        )

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
            raise KeyError(f"No snapshot with seq={seq}")
        return GameState.model_validate_json(row["state_json"])
