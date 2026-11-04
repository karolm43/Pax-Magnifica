"""Skanery lokalności: odwołania do folderów referencyjnych, odczyty spoza korzenia
projektu i zewnętrzne adresy URL.

Funkcje ``find_*`` są CZYSTE nad tekstem (mapa ``ścieżka -> treść``), więc da się je
testować bez dysku. Cienkie otoczki ``collect_sources`` / ``scan_*`` tylko wczytują
pliki i wołają funkcje czyste.

Nazwy folderów referencyjnych NIE są stałą w tym module — przekazuje je wołający
(test Strażnika_Lokalności), dzięki czemu kod produkcyjny sam ich nie zawiera.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from src import config

ALLOWLIST_PATH: Path = config.AUDIT_DIR / "external_url_allowlist.json"
UNUSED_ASSET_DIRS_PATH: Path = config.AUDIT_DIR / "unused_asset_dirs.json"

# Hosty lokalne — zawsze dozwolone (adres własnego Backendu i dev-serwera).
LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1"})

_URL_RE = re.compile(r"https?://[^\s\"'`<>()\[\]{}\\]+", re.IGNORECASE)
_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:[\\/]")
_PARENT_RE = re.compile(r"^(\.\.|~)([\\/]|$)")
_POSIX_ROOTS = ("home", "Users", "etc", "usr", "var", "tmp", "mnt", "opt", "root")


@dataclass(frozen=True)
class LocalityFinding:
    """Pojedyncze znalezisko skanera (plik, numer linii, dopasowany tekst)."""

    file: str
    line: int
    text: str


# --- Pomocnicze ---------------------------------------------------------


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Zwraca ``id`` węzłów ``Constant`` będących docstringami."""
    result: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                result.add(id(first.value))
    return result


def _python_string_literals(source: str) -> list[tuple[int, str]] | None:
    """Literały napisowe z KODU (bez docstringów); ``None`` gdy plik się nie parsuje."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    skip = _docstring_nodes(tree)
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skip
    ]


def _is_python(path: str) -> bool:
    return path.endswith(".py")


# --- Odwołania do folderów referencyjnych -------------------------------


def find_reference_path_usage(
    sources: Mapping[str, str], names: Sequence[str]
) -> list[LocalityFinding]:
    """Wykrywa nazwy folderów referencyjnych w kodzie wykonywalnym.

    Dla plików ``*.py`` sprawdzane są wyłącznie literały napisowe poza docstringami
    (komentarze i docstringi z cytowaniem źródła są dozwolone). Dla pozostałych
    plików (TS, HTML, konfiguracja) sprawdzany jest cały tekst linia po linii.
    """
    findings: list[LocalityFinding] = []
    for path, text in sorted(sources.items()):
        literals = _python_string_literals(text) if _is_python(path) else None
        if literals is not None:
            for line, value in literals:
                findings.extend(
                    LocalityFinding(path, line, name) for name in names if name in value
                )
            continue
        for number, line_text in enumerate(text.splitlines(), start=1):
            findings.extend(
                LocalityFinding(path, number, name) for name in names if name in line_text
            )
    return findings


# --- Odczyty spoza korzenia projektu ------------------------------------


def _outside_root(value: str, project_root: str | None) -> bool:
    """Czy literał wygląda na ścieżkę wskazującą poza korzeń projektu."""
    if project_root is not None:
        normalized = value.replace("\\", "/")
        root = project_root.replace("\\", "/").rstrip("/")
        if normalized == root or normalized.startswith(root + "/"):
            return False
    if _WINDOWS_ABS_RE.match(value) or _PARENT_RE.match(value):
        return True
    parts = PurePosixPath(value).parts
    return len(parts) >= 3 and parts[0] == "/" and parts[1] in _POSIX_ROOTS


def find_outside_root_reads(
    sources: Mapping[str, str], project_root: str | None = None
) -> list[LocalityFinding]:
    """Wykrywa literały ścieżek wychodzących poza korzeń projektu (R1.5).

    Heurystyka statyczna nad literałami kodu ``*.py``: ścieżki absolutne (dysk
    Windows, ``~``, typowe korzenie POSIX) oraz zaczynające się od ``..``.
    Ścieżki leżące pod ``project_root`` są dozwolone.
    """
    findings: list[LocalityFinding] = []
    for path, text in sorted(sources.items()):
        if not _is_python(path):
            continue
        literals = _python_string_literals(text) or []
        findings.extend(
            LocalityFinding(path, line, value)
            for line, value in literals
            if _outside_root(value, project_root)
        )
    return findings


# --- Zewnętrzne adresy URL ----------------------------------------------


def _allowed_by_prefix(url: str, prefixes: Iterable[str]) -> bool:
    """Prefiks pasuje, gdy kończy się na granicy segmentu (nie w środku hosta)."""
    lowered = url.lower()
    for prefix in prefixes:
        base = prefix.lower().rstrip("/")
        if lowered == base:
            return True
        if lowered.startswith(base) and lowered[len(base)] in "/?#:":
            return True
    return False


def find_external_urls(
    text: str, allowlist: Collection[str], file: str = ""
) -> list[LocalityFinding]:
    """Zwraca adresy ``http(s)://`` spoza hostów lokalnych i listy dozwolonej (R2.5).

    ``allowlist`` to prefiksy adresów (np. ``https://www.tirules2.com``).
    """
    findings: list[LocalityFinding] = []
    for number, line_text in enumerate(text.splitlines(), start=1):
        for match in _URL_RE.finditer(line_text):
            url = match.group(0).rstrip(".,;:")
            try:
                host = (urlsplit(url).hostname or "").lower()
            except ValueError:
                host = ""
            if host in LOCAL_HOSTS or _allowed_by_prefix(url, allowlist):
                continue
            findings.append(LocalityFinding(file, number, url))
    return findings


# --- Cienka otoczka: pliki ----------------------------------------------


def collect_sources(root: Path, patterns: Iterable[str]) -> dict[str, str]:
    """Wczytuje pliki pasujące do wzorców glob, klucz = ścieżka względna (POSIX)."""
    result: dict[str, str] = {}
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                key = path.relative_to(root).as_posix()
                # utf-8-sig: część plików ma BOM, który psuje ``ast.parse``.
                result[key] = path.read_text(encoding="utf-8-sig", errors="replace")
    return result


def load_allowlist(path: Path = ALLOWLIST_PATH) -> list[str]:
    """Wczytuje prefiksy z ``external_url_allowlist.json`` (brak pliku = pusta lista)."""
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path} must contain a list of {{prefix, note}} objects.")
    return [str(item["prefix"]) for item in raw if isinstance(item, dict) and "prefix" in item]


def load_unused_asset_dirs(path: Path = UNUSED_ASSET_DIRS_PATH) -> list[str]:
    """Lista katalogów ``assets/`` oznaczonych jako nieużywane (tylko raport, R3.5)."""
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(f"{path} must contain a list of directory names.")
    return list(raw)


def scan_external_urls(
    root: Path, patterns: Iterable[str], allowlist: Collection[str]
) -> list[LocalityFinding]:
    """Skanuje pliki (pomijając ``*.test.ts(x)``) pod kątem zewnętrznych URL."""
    findings: list[LocalityFinding] = []
    for key, text in collect_sources(root, patterns).items():
        if re.search(r"\.test\.tsx?$", key):
            continue
        findings.extend(find_external_urls(text, allowlist, file=key))
    return findings
