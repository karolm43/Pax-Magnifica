"""Pliki zapisów partii (RULES.md 44.4): katalog ``saves/``, jedna partia = jeden plik SQLite.

Nowa gra z kreatora zaczyna NOWY plik (``game-RRRRMMDD-GGMMSS.db``), więc stare partie
zostają nietknięte i można je wczytać z menu („Load game"). Plik to ``EventStore``: migawki
stanu + historia Undo + metadane (mapa, miejsca/lobby). Ten moduł tylko wylicza i opisuje
pliki — przełączanie bieżącej partii robi ``AppContext.switch_store``.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.core.event_store import EventStore

_NAME = re.compile(r"^[A-Za-z0-9._-]+\.db$")


@dataclass
class SaveInfo:
    """Opis pliku zapisu do listy „Load game"."""

    name: str
    modified: float
    round_number: int | None = None
    phase: str | None = None
    players: list[str] = field(default_factory=list)
    broken: bool = False


class SaveManager:
    """Katalog zapisów: lista, ścieżki, nowa nazwa."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def path(self, name: str) -> Path:
        """Ścieżka zapisu o nazwie z listy. Raises: ``ValueError`` (zła nazwa / brak pliku)."""
        if not _NAME.match(name):
            raise ValueError(f"Invalid save name: {name!r}")
        path = self.directory / name
        if not path.is_file():
            raise ValueError(f"Save not found: {name}")
        return path

    def new_path(self) -> Path:
        """Ścieżka na nową partię (unikalna, z datą)."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = self.directory / f"game-{stamp}.db"
        n = 2
        while path.exists():
            path = self.directory / f"game-{stamp}-{n}.db"
            n += 1
        return path

    def latest(self) -> Path | None:
        """Ostatnio zmieniany zapis (wznowienie po starcie serwera)."""
        files = sorted(self.directory.glob("*.db"), key=lambda p: p.stat().st_mtime)
        return files[-1] if files else None

    def list(self) -> list[SaveInfo]:
        """Zapisy od najnowszego, z rundą/fazą/graczami (nieczytelne oznaczone ``broken``)."""
        infos: list[SaveInfo] = []
        for path in self.directory.glob("*.db"):
            info = SaveInfo(name=path.name, modified=path.stat().st_mtime)
            try:
                store = EventStore(path)
                try:
                    state = store.current()
                finally:
                    store.close()
            except Exception:  # noqa: BLE001 — opis listy nie może wywrócić menu
                info.broken = True
            else:
                if state is not None:
                    info.round_number = state.round_number
                    info.phase = str(state.phase.value)
                    info.players = [
                        p.display_name or p.faction or pid for pid, p in state.players.items()
                    ]
            infos.append(info)
        return sorted(infos, key=lambda i: i.modified, reverse=True)
