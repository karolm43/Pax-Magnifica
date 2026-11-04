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

# Katalogi grafik używane przez frontend (D1); parametr ``dirs`` pozwala to zmienić.
DEFAULT_ASSET_DIRS: tuple[str, ...] = (
    "units",
    "command_token",
    "player_area",
    "factions",
    "planet_cards",
    "tokens",
    "extra",
    "general",
    "decals",
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
    assets_dir: Path = config.ASSETS_DIR, dirs: Iterable[str] = DEFAULT_ASSET_DIRS
) -> list[str]:
    """Ścieżki POSIX (względem ``assets_dir``) plików graficznych w podanych katalogach."""
    found: list[str] = []
    for name in dirs:
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
    assets_dir: Path = config.ASSETS_DIR, dirs: Iterable[str] = DEFAULT_ASSET_DIRS
) -> dict[str, list[dict[str, object]]]:
    """Buduje manifest ``{"files": [{path, size, sha256}, ...]}`` z dysku."""
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


def load_manifest_paths(path: Path = MANIFEST_PATH) -> list[str]:
    """Ścieżki z manifestu (brak pliku = pusta lista)."""
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    files = raw.get("files") if isinstance(raw, dict) else None
    if not isinstance(files, list):
        raise ValueError(f"{path} must contain an object with a 'files' list.")
    return [str(item["path"]) for item in files if isinstance(item, dict) and "path" in item]
