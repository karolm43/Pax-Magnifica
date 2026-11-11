"""Zgłoszenia błędów z UI („Report bug") — zapis na dysk HOSTA.

Każdy gracz (także gość w grze sieciowej) wysyła z przeglądarki zrzut ekranu + opis; backend
odkłada je w katalogu raportów na komputerze, na którym działa serwer. Jeden raport = jeden
podkatalog ``<data>_<czas>_<gracz>/`` z plikami:

- ``report.md``    — opis gracza + kontekst (kto, runda, faza, zapis partii, przeglądarka),
- ``screenshot.png`` — zrzut widoku gracza (gdy przeglądarka go zrobiła),
- ``client.json``  — surowe dane klienta (adres, rozmiar okna, ostatnie błędy konsoli),
- ``state.json``   — PEŁNY ``GameState`` z chwili zgłoszenia (do odtworzenia sytuacji).

To warstwa I/O ``api/`` (jak ``saves.py``), nie reguła gry — ``core/`` zostaje nietknięte.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.game_state import GameState

_PNG_PREFIX = "data:image/png;base64,"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_SCREENSHOT_BYTES = 25 * 1024 * 1024
"""Górny limit zdekodowanego zrzutu (duży monitor 4K z DPR 2 to kilka–kilkanaście MB)."""


@dataclass(frozen=True)
class BugReportInput:
    """Dane zgłoszenia z przeglądarki (po walidacji schematu)."""

    description: str
    screenshot: str | None
    client: dict[str, Any]


def _slug(text: str) -> str:
    """Bezpieczny fragment nazwy katalogu (litery, cyfry, ``-``)."""
    cleaned = re.sub(r"[^A-Za-z0-9-]+", "-", text).strip("-")
    return cleaned[:40] or "anon"


def decode_png(data_url: str) -> bytes:
    """Dekoduje ``data:image/png;base64,...``; zły format => ``ValueError``."""
    if not data_url.startswith(_PNG_PREFIX):
        raise ValueError("Screenshot must be a PNG data URL.")
    try:
        raw = base64.b64decode(data_url[len(_PNG_PREFIX) :], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Screenshot is not valid base64.") from exc
    if not raw.startswith(_PNG_MAGIC):
        raise ValueError("Screenshot is not a PNG image.")
    if len(raw) > MAX_SCREENSHOT_BYTES:
        raise ValueError("Screenshot is too large.")
    return raw


def _reporter_label(state: GameState, actor: str | None) -> str:
    """Kto zgłasza: ``p1 (The Federation of Sol)`` / ``host``."""
    if actor is None:
        return "host"
    player = state.players.get(actor)
    faction = player.faction if player is not None else None
    return f"{actor} ({faction})" if faction else actor


def _report_markdown(
    *,
    created: datetime,
    reporter: str,
    state: GameState,
    save_name: str | None,
    report: BugReportInput,
) -> str:
    client = report.client
    viewport = client.get("viewport") or {}
    errors = client.get("consoleErrors") or []
    lines = [
        f"# Bug report — {created:%Y-%m-%d %H:%M:%S} UTC",
        "",
        f"- **Reporter:** {reporter}",
        f"- **Round / phase:** {state.round_number} / {state.phase}",
        f"- **Save file:** {save_name or '—'}",
        f"- **Page:** {client.get('url', '—')}",
        f"- **Window:** {viewport.get('width', '?')}×{viewport.get('height', '?')}"
        f" (DPR {viewport.get('dpr', '?')})",
        f"- **Browser:** {client.get('userAgent', '—')}",
        f"- **Screenshot:** {'screenshot.png' if report.screenshot else 'none (capture failed)'}",
        "",
        "## Description",
        "",
        report.description.strip() or "_(empty)_",
    ]
    if errors:
        lines += ["", "## Recent console errors", "", "```"]
        lines += [str(e) for e in errors]
        lines += ["```"]
    lines.append("")
    return "\n".join(lines)


def write_bug_report(
    root: Path,
    *,
    state: GameState,
    actor: str | None,
    report: BugReportInput,
    now: float,
    save_name: str | None = None,
) -> Path:
    """Zapisuje zgłoszenie w nowym podkatalogu ``root``; zwraca jego ścieżkę.

    Zrzut jest dekodowany PRZED utworzeniem katalogu — zły zrzut => ``ValueError`` i nic
    nie zostaje na dysku.
    """
    png = decode_png(report.screenshot) if report.screenshot else None
    created = datetime.fromtimestamp(now, tz=UTC)
    base = f"{created:%Y-%m-%d_%H-%M-%S}_{_slug(actor or 'host')}"
    root.mkdir(parents=True, exist_ok=True)
    folder = root / base
    suffix = 2
    while folder.exists():
        folder = root / f"{base}_{suffix}"
        suffix += 1
    folder.mkdir()

    reporter = _reporter_label(state, actor)
    (folder / "report.md").write_text(
        _report_markdown(
            created=created, reporter=reporter, state=state, save_name=save_name, report=report
        ),
        encoding="utf-8",
    )
    if png is not None:
        (folder / "screenshot.png").write_bytes(png)
    (folder / "client.json").write_text(
        json.dumps({"reporter": reporter, **report.client}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (folder / "state.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return folder
