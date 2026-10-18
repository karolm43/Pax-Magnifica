"""Punkt wejścia serwera API: ``uv run python -m src.api``.

Uruchamia aplikację FastAPI na Uvicornie (domyślnie ``127.0.0.1:8000``).
Przeznaczone do ręcznego uruchamiania w terminalu podczas developmentu — nie
jest odpalane automatycznie przez agenta.
"""

from __future__ import annotations

import uvicorn

from src.api.app import create_app

app = create_app()


def main() -> None:
    """Startuje serwer deweloperski Uvicorn."""
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
