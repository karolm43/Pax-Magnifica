"""Manifest lokalnych grafik (``audit/assets_manifest.json``) i jego różnica z dyskiem.

Manifest to lista ``{path, size, sha256}`` (ścieżki POSIX względem ``assets/``).
Służy do wykrywania brakujących i nieużywanych plików (R3.1, R3.2). Grafiki zostają
poza repo (D1), więc manifest jest jedynym wersjonowanym śladem ich istnienia.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from src import config

MANIFEST_PATH: Path = config.AUDIT_DIR / "assets_manifest.json"

# Kopia manifestu dla frontendu (tylko logiczne ścieżki). Jedyne źródło prawdy to
# ``audit/assets_manifest.json`` — ten plik jest ARTEFAKTEM generowanym z niego
# i sprawdzanym testem zgodności (R3.1; design.md, sekcja Resolver_Zasobów).
FRONTEND_MANIFEST_PATH: Path = (
    config.FRONTEND_DIR / "src" / "shared" / "assets" / "assetManifest.json"
)

# Domyślnie skanujemy CAŁE drzewo ``assets/`` pod kątem grafik (``dirs=None``).
# Wcześniej lista była zawężona do 9 katalogów i POMIJAŁA kluczowe grafiki planszy
# (``tiles``, ``emojis``, ``attachment_token`` i inne), przez co Resolver_Zasobów
# zwracał placeholder dla tilesów i tokenów. Skan całości jest odporny na przyszłe
# katalogi grafik (nowy katalog trafia do manifestu automatycznie). Jawna lista
# ``dirs`` nadal zawęża skan do podanych katalogów (wsteczna kompatybilność).
DEFAULT_ASSET_DIRS: None = None

# Katalogi pomijane przy skanie całości (``dirs=None``): dane/konfiguracja i surowe
# materiały, które NIE są grafikami serwowanymi frontowi. Grafiki poza tą listą
# (w tym nowe katalogi) trafiają do manifestu automatycznie. Nazwy to top-level
# katalogi względem ``assets/``.
EXCLUDED_ASSET_DIRS: frozenset[str] = frozenset(
    {
        "data",
        "config",
        "raw",
        "META-INF",
        "voices",
        "hover_images",
        "systems",
        "planets",
        "alias",
    }
)
IMAGE_SUFFIXES: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp", ".svg"})


@dataclass(frozen=True)
class ManifestDiff:
    """``missing`` = w manifeście, brak na dysku; ``unused`` = na dysku, brak w manifeście."""

    missing: frozenset[str]
    unused: frozenset[str]

    @property
    def is_empty(self) -> bool:
        return not self.missing and not self.unused


def diff_manifest(manifest_paths: Iterable[str], files_on_disk: Iterable[str]) -> ManifestDiff:
    """``missing = manifest \\ pliki``, ``unused = pliki \\ manifest``."""
    manifest = frozenset(manifest_paths)
    disk = frozenset(files_on_disk)
    return ManifestDiff(missing=manifest - disk, unused=disk - manifest)


def list_asset_files(
    assets_dir: Path = config.ASSETS_DIR, dirs: Iterable[str] | None = DEFAULT_ASSET_DIRS
) -> list[str]:
    """Ścieżki POSIX (względem ``assets_dir``) plików graficznych.

    Gdy ``dirs is None`` (domyślnie), skanuje CAŁE drzewo ``assets_dir`` pod kątem
    plików graficznych (``IMAGE_SUFFIXES``), pomijając wyłącznie top-level katalogi
    z ``EXCLUDED_ASSET_DIRS`` (dane/konfiguracja/surowce). Dzięki temu grafiki planszy
    (``tiles``, ``emojis``, ``attachment_token`` itd.) trafiają do manifestu, a nowe
    katalogi grafik są obejmowane automatycznie.

    Gdy ``dirs`` to jawna lista (nie None), zachowuje dotychczasowe zachowanie:
    iteruje tylko po podanych katalogach (wsteczna kompatybilność, wygodne w testach).
    """
    scan_dirs: Iterable[str]
    if dirs is None:
        # Skan całości: top-level katalogi grafik względem ``assets_dir``, bez wykluczonych.
        scan_dirs = sorted(
            entry.name
            for entry in assets_dir.iterdir()
            if entry.is_dir() and entry.name not in EXCLUDED_ASSET_DIRS
        )
    else:
        scan_dirs = dirs

    found: list[str] = []
    for name in scan_dirs:
        base = assets_dir / name
        if not base.is_dir():
            continue
        found.extend(
            path.relative_to(assets_dir).as_posix()
            for path in base.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
    return sorted(found)


def build_manifest(
    assets_dir: Path = config.ASSETS_DIR, dirs: Iterable[str] | None = DEFAULT_ASSET_DIRS
) -> dict[str, list[dict[str, object]]]:
    """Buduje manifest ``{"files": [{path, size, sha256}, ...]}`` z dysku.

    ``dirs=None`` (domyślnie) skanuje całe ``assets/`` poza ``EXCLUDED_ASSET_DIRS``;
    jawna lista ``dirs`` zawęża skan do podanych katalogów (patrz ``list_asset_files``).
    """
    files: list[dict[str, object]] = []
    for rel in list_asset_files(assets_dir, dirs):
        data = (assets_dir / rel).read_bytes()
        files.append({"path": rel, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {"files": files}


def write_manifest(
    manifest: dict[str, list[dict[str, object]]], path: Path = MANIFEST_PATH
) -> None:
    """Zapisuje manifest jako JSON (deterministycznie, z końcowym newline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def write_frontend_manifest(
    manifest: dict[str, list[dict[str, object]]], path: Path = FRONTEND_MANIFEST_PATH
) -> None:
    """Zapisuje kopię manifestu dla frontendu: tylko logiczne ścieżki (``{"paths": [...]}``).

    Resolver_Zasobów (`resolveAsset.ts`) czyta wyłącznie listę ścieżek, bez rozmiarów
    ani sum kontrolnych — te zostają w głównym manifeście w ``audit/``.
    """
    paths = sorted(
        str(item["path"])
        for item in manifest.get("files", [])
        if isinstance(item, dict) and "path" in item
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"paths": paths}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def load_manifest_paths(path: Path = MANIFEST_PATH) -> list[str]:
    """Ścieżki z manifestu (brak pliku = pusta lista)."""
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    files = raw.get("files") if isinstance(raw, dict) else None
    if not isinstance(files, list):
        raise ValueError(f"{path} must contain an object with a 'files' list.")
    return [str(item["path"]) for item in files if isinstance(item, dict) and "path" in item]
