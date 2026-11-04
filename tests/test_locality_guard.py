"""Strażnik_Lokalności (część backendowa).

Zestaw testów pilnujących, by:

1. żaden plik ``*.py`` w ``src/`` ani ``scripts/`` nie odwoływał się w KODZIE
   wykonywalnym do folderów referencyjnych AsyncTI4 (komentarze i docstringi
   z cytowaniem źródła są dozwolone) — R1.1;
2. żaden plik w ``frontend/src``, ``frontend/index.html`` i
   ``frontend/vite.config.ts`` nie importował ani nie proxy'ował folderów
   referencyjnych — R1.2;
3. budowa ``StaticDataRegistry()`` oraz ``create_app()`` nie czytała żadnego
   pliku spoza ``PROJECT_ROOT`` (ani z folderów referencyjnych) — R1.3, R1.5.

Nazwy folderów referencyjnych są STAŁĄ W TEŚCIE (nie w kodzie produkcyjnym),
zgodnie z designem (sekcja „Strażnik_Lokalności”).
"""

from __future__ import annotations

import builtins
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

from src import config
from src.audit.locality import (
    collect_sources,
    find_reference_path_usage,
    load_allowlist,
    scan_external_urls,
)

# Nazwy folderów referencyjnych AsyncTI4 (źródła tylko do czytania przez człowieka).
# Celowo trzymane w teście — kod produkcyjny nie może ich zawierać (R1.1).
REFERENCE_DIR_NAMES: tuple[str, ...] = ("TI4_map_generator_bot", "ti4_web_new")

# Wzorce glob dla kodu backendu skanowanego pod kątem odwołań do folderów.
_BACKEND_PATTERNS: tuple[str, ...] = ("src/**/*.py", "scripts/**/*.py")


# --- R1.1: kod backendu nie odwołuje się do folderów referencyjnych -----


def test_backend_code_has_no_reference_folder_usage() -> None:
    """Literały napisowe w ``src/`` i ``scripts/`` nie zawierają nazw folderów."""
    sources = collect_sources(config.PROJECT_ROOT, _BACKEND_PATTERNS)
    # Nie skanujemy samego Strażnika (ta stała jest tu celowo).
    sources.pop("tests/test_locality_guard.py", None)
    findings = find_reference_path_usage(sources, REFERENCE_DIR_NAMES)
    assert findings == [], (
        "Kod backendu odwołuje się do folderu referencyjnego w literale napisowym: "
        + ", ".join(f"{f.file}:{f.line} -> {f.text}" for f in findings)
    )


# --- R1.2: frontend nie importuje/proxy'uje folderów referencyjnych -----

# Linie wskazujące na IMPORT lub PROXY (modułu/zasobu), a nie na komentarz czy
# osadzony ciąg danych. R1.2 pilnuje wyłącznie importów i proxy do folderów
# referencyjnych; osadzone URL-e CDN pokrywa osobny skaner URL (zadanie 11.7),
# a usuwanie danych homebrew — zadanie 11.3.
_IMPORT_OR_PROXY_RE = re.compile(
    r"\b(?:import|export|require|from)\b|['\"]?(?:proxy|target|rewrite|base|publicDir)['\"]?\s*[:=]",
    re.IGNORECASE,
)


def _import_or_proxy_lines(sources: Mapping[str, str]) -> dict[str, str]:
    """Zostawia tylko linie wyglądające na import/proxy (reszta → puste linie).

    Numeracja linii jest zachowana: linie nie-importowe zamieniamy na pusty tekst,
    więc ``find_reference_path_usage`` nadal raportuje poprawny numer wiersza.
    """
    filtered: dict[str, str] = {}
    for path, text in sources.items():
        kept = [
            line if _IMPORT_OR_PROXY_RE.search(line) else ""
            for line in text.splitlines()
        ]
        filtered[path] = "\n".join(kept)
    return filtered


def test_frontend_sources_have_no_reference_folder_usage() -> None:
    """``frontend/src``, ``index.html`` i ``vite.config.ts`` nie importują folderów."""
    frontend = config.FRONTEND_DIR
    sources = collect_sources(
        frontend,
        ("src/**/*.ts", "src/**/*.tsx", "src/**/*.js", "src/**/*.jsx", "src/**/*.css"),
    )
    for single in ("index.html", "vite.config.ts"):
        path = frontend / single
        if path.is_file():
            sources[single] = path.read_text(encoding="utf-8-sig", errors="replace")

    findings = find_reference_path_usage(
        _import_or_proxy_lines(sources), REFERENCE_DIR_NAMES
    )
    assert findings == [], (
        "Frontend importuje/proxy'uje folder referencyjny: "
        + ", ".join(f"{f.file}:{f.line} -> {f.text}" for f in findings)
    )


# --- R2.5 / R2.6 / R12.2: brak zewnętrznych URL spoza listy dozwolonej ---

# Wzorce glob frontendu skanowane pod kątem zewnętrznych ``http(s)://`` URL.
# ``index.html`` i ``vite.config.ts`` dokładane są osobno (leżą w korzeniu frontu).
_FRONTEND_URL_PATTERNS: tuple[str, ...] = (
    "src/**/*.ts",
    "src/**/*.tsx",
    "src/**/*.js",
    "src/**/*.jsx",
    "src/**/*.css",
    "index.html",
    "vite.config.ts",
)


def test_frontend_has_no_external_urls_outside_allowlist() -> None:
    """``frontend/src`` i ``index.html`` nie zawierają URL spoza listy dozwolonej.

    Skaner (``scan_external_urls``) pomija pliki ``*.test.ts(x)`` oraz hosty
    lokalne (``localhost``/``127.0.0.1``). Pozostałe adresy muszą pasować do
    prefiksu z ``audit/external_url_allowlist.json`` (adresy nawigacyjne,
    atrybucyjne i identyfikator przestrzeni nazw SVG) — R2.5, R2.6, R12.2.
    """
    allowlist = load_allowlist()
    findings = scan_external_urls(
        config.FRONTEND_DIR, _FRONTEND_URL_PATTERNS, allowlist
    )
    assert findings == [], (
        "Zewnętrzny URL spoza listy dozwolonej w froncie "
        "(dodaj do audit/external_url_allowlist.json z notą, jeśli jest zasadny): "
        + ", ".join(f"{f.file}:{f.line} -> {f.text}" for f in findings)
    )


# --- R1.3 / R1.5: brak odczytów spoza PROJECT_ROOT ----------------------


class _ReadRecorder:
    """Rejestruje ścieżki czytane przez ``Path.read_text``/``read_bytes`` i ``open``.

    Opakowuje oryginalne funkcje, przepuszcza wywołanie i zapisuje ścieżkę. Dzięki
    temu po zbudowaniu rejestru i aplikacji można sprawdzić, że żaden odczyt nie
    wyszedł poza korzeń projektu.
    """

    def __init__(self) -> None:
        self.paths: list[Path] = []

    def record(self, raw: Any) -> None:
        # ``open`` bywa wołane z deskryptorem całkowitym — takich nie śledzimy.
        if isinstance(raw, int):
            return
        self.paths.append(Path(raw))


@pytest.fixture
def read_recorder(monkeypatch: pytest.MonkeyPatch) -> Iterator[_ReadRecorder]:
    """Fixture opakowujący ``Path.read_text``, ``Path.read_bytes`` i ``open``."""
    recorder = _ReadRecorder()

    orig_read_text = Path.read_text
    orig_read_bytes = Path.read_bytes
    orig_open = builtins.open

    def wrapped_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        recorder.record(self)
        return orig_read_text(self, *args, **kwargs)

    def wrapped_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        recorder.record(self)
        return orig_read_bytes(self, *args, **kwargs)

    def wrapped_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        recorder.record(file)
        return orig_open(file, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", wrapped_read_text)
    monkeypatch.setattr(Path, "read_bytes", wrapped_read_bytes)
    monkeypatch.setattr(builtins, "open", wrapped_open)
    yield recorder


def _is_inside_root(path: Path, root: Path) -> bool:
    """Czy ``path`` leży pod ``root`` (po rozwinięciu do ścieżki bezwzględnej)."""
    try:
        resolved = path if path.is_absolute() else (root / path)
        resolved.resolve().relative_to(root)
    except (ValueError, OSError):
        return False
    return True


def _assert_reads_local(recorder: _ReadRecorder) -> None:
    root = config.PROJECT_ROOT.resolve()
    outside = sorted(
        {str(p) for p in recorder.paths if not _is_inside_root(p, root)}
    )
    assert outside == [], "Odczyt spoza PROJECT_ROOT: " + ", ".join(outside)

    # Dodatkowo: żadna ścieżka nie może trafić do folderu referencyjnego.
    reference_hits = sorted(
        {
            str(p)
            for p in recorder.paths
            if any(name in str(p) for name in REFERENCE_DIR_NAMES)
        }
    )
    assert reference_hits == [], (
        "Odczyt z folderu referencyjnego: " + ", ".join(reference_hits)
    )


def test_registry_reads_only_inside_project_root(
    read_recorder: _ReadRecorder,
) -> None:
    """Budowa ``StaticDataRegistry`` nie czyta plików spoza korzenia projektu."""
    from src.core.registry import StaticDataRegistry

    StaticDataRegistry()
    assert read_recorder.paths, "Oczekiwano odczytów assetów podczas budowy rejestru."
    _assert_reads_local(read_recorder)


def test_create_app_reads_only_inside_project_root(
    read_recorder: _ReadRecorder,
) -> None:
    """Budowa aplikacji FastAPI nie czyta plików spoza korzenia projektu."""
    from src.api.app import create_app
    from src.core.event_store import EventStore

    create_app(store=EventStore(":memory:"))
    assert read_recorder.paths, "Oczekiwano odczytów assetów podczas budowy aplikacji."
    _assert_reads_local(read_recorder)
