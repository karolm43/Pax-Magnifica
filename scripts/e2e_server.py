"""Backend dla testów E2E (Playwright): ``uv run python scripts/e2e_server.py [--port 8100]``.

Celowo ODIZOLOWANY od gry użytkownika (``python -m src.api``):
- inny port (domyślnie 8100, nie 8000) i NIE zabija procesów trzymających port,
- historia w SQLite w pamięci (``EventStore()``), katalog zapisów tymczasowy —
  ``saves/`` z partiami użytkownika nie jest czytany ani zapisywany,
- każdy start = pusty stan, więc testy są powtarzalne.

Uruchamiany automatycznie przez ``frontend/playwright.config.ts`` (``webServer``).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import uvicorn

# Skrypt odpalany ścieżką (nie ``-m``): katalog repo na ``sys.path``, żeby działało ``src.*``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.app import create_app  # noqa: E402


def main() -> None:
    """Startuje świeży backend (pusty stan, zapis w pamięci) na wskazanym porcie."""
    parser = argparse.ArgumentParser(prog="scripts/e2e_server.py")
    parser.add_argument("--port", type=int, default=8100)
    args = parser.parse_args()
    saves_dir = Path(tempfile.mkdtemp(prefix="custodian-e2e-"))
    app = create_app(saves_dir=saves_dir)
    print(f"[e2e] Fresh backend on 127.0.0.1:{args.port} (saves: {saves_dir})")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
