"""Podgląd wspomnień Kiro (``~/.kiro/memories/memories.db``) — TYLKO DO ODCZYTU.

Kiro zapisuje wiedzę o projekcie (gotchas, decyzje użytkownika, stan modułów) w lokalnej
bazie SQLite. Ten skrypt pozwala innym asystentom (np. Claude Code) z niej korzystać bez
kopiowania treści — baza zostaje jedynym źródłem, więc nic się nie rozjeżdża.

Użycie (z katalogu repo):
    uv run python scripts/kiro_memories.py list                 # tytuły + skróty
    uv run python scripts/kiro_memories.py search zegar turn    # wpisy z KAŻDYM słowem
    uv run python scripts/kiro_memories.py show <tytuł> [...]   # pełna treść wpisu
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB = Path.home() / ".kiro" / "memories" / "memories.db"
FIELDS = "title, memory_type, summary, content, why, how_to_apply"


def _connect() -> sqlite3.Connection:
    if not DB.exists():
        sys.exit(f"Brak bazy wspomnień Kiro: {DB}")
    return sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)


def _rows(where: str = "", params: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    with _connect() as conn:
        query = f"SELECT {FIELDS} FROM memories {where} ORDER BY memory_type, title"
        return list(conn.execute(query, params))


def main(argv: list[str]) -> None:
    # Konsola Windows (cp1250) nie zna wszystkich znaków z treści (→, ł w złym kodowaniu).
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    cmd, args = (argv[0], argv[1:]) if argv else ("list", [])
    if cmd == "list":
        for title, kind, summary, *_ in _rows():
            print(f"[{kind}] {title} — {summary}")
    elif cmd == "search" and args:
        words = [w.lower() for w in args]
        for title, kind, summary, content, *_ in _rows():
            text = f"{title} {summary} {content}".lower()
            if all(w in text for w in words):
                print(f"[{kind}] {title} — {summary}")
    elif cmd == "show" and args:
        for name in args:
            found = _rows("WHERE title = ?", (name,))
            if not found:
                print(f"(brak wpisu: {name})")
            for title, kind, summary, content, why, how in found:
                print(f"===== [{kind}] {title}\n{summary}\n\n{content}")
                if why:
                    print(f"\nWHY: {why}")
                if how:
                    print(f"HOW TO APPLY: {how}")
                print()
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
