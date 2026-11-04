"""Synchronizacja lokalnych grafik z katalogu referencyjnego wskazanego przez ``--from``.

Grafiki zostają poza repo (D1), a jedynym wersjonowanym śladem ich istnienia jest
manifest ``audit/assets_manifest.json`` (patrz ``assets_manifest.py``). Ten moduł
kopiuje do ``assets/`` tylko te pliki z manifestu, których brakuje na dysku, pobierając
je z katalogu podanego w argumencie CLI ``--from``.

Zasady (R3.3, R12.8, decyzja D1):

- Ścieżka źródła jest WYŁĄCZNIE argumentem CLI ``--from <katalog>`` — nigdy stałą w
  kodzie (zgodność z R1.1: kod nie zawiera ścieżek do Źródeł_Referencyjnych).
- Kopiowane są tylko pliki brakujące na dysku; pliki już obecne są pomijane.
- Plik z manifestu, którego nie ma w katalogu ``--from``, trafia na listę
  „niezsynchronizowane", a program kończy się niezerowym kodem wyjścia.
- Katalog źródłowy NIGDY nie jest modyfikowany (R12.8) — wykonujemy tylko odczyty
  i kopiowanie w stronę ``assets/``.
- Brak argumentu ``--from`` = komunikat o użyciu i kod wyjścia 2; nic nie jest kopiowane.
"""

from __future__ import annotations

import argparse
import shutil
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from src import config
from src.audit.assets_manifest import MANIFEST_PATH, load_manifest_paths


@dataclass(frozen=True)
class SyncResult:
    """Wynik synchronizacji grafik z katalogu ``--from``.

    Attributes:
        copied: Ścieżki POSIX (względem ``assets/``) plików skopiowanych ze źródła.
        already_present: Ścieżki pominięte, bo już istnieją na dysku w ``assets/``.
        unsynced: Ścieżki z manifestu nieobecne w katalogu źródłowym („niezsynchronizowane").
    """

    copied: tuple[str, ...] = ()
    already_present: tuple[str, ...] = ()
    unsynced: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_unsynced(self) -> bool:
        """``True``, gdy choć jeden plik z manifestu nie mógł zostać zsynchronizowany."""
        return bool(self.unsynced)


def sync_assets(
    source_dir: Path,
    *,
    manifest_paths: Sequence[str],
    assets_dir: Path = config.ASSETS_DIR,
) -> SyncResult:
    """Kopiuje brakujące pliki z manifestu z ``source_dir`` do ``assets_dir``.

    Dla każdej ścieżki ``rel`` z manifestu (POSIX, względem ``assets/``):

    - jeśli plik istnieje już w ``assets_dir`` — pomijany (``already_present``);
    - w przeciwnym razie szukany w ``source_dir / rel``; gdy istnieje — kopiowany do
      ``assets_dir / rel`` (``copied``), gdy brak — trafia do ``unsynced``.

    Katalog ``source_dir`` jest wyłącznie czytany; żaden plik w nim nie jest zmieniany
    ani usuwany (R12.8). Wynik jest deterministyczny (ścieżki posortowane).

    Args:
        source_dir: Katalog referencyjny wskazany przez ``--from``.
        manifest_paths: Ścieżki POSIX (względem ``assets/``) z manifestu.
        assets_dir: Katalog docelowy (domyślnie ``config.ASSETS_DIR``).

    Returns:
        :class:`SyncResult` z listami skopiowanych, pominiętych i niezsynchronizowanych.
    """
    copied: list[str] = []
    already_present: list[str] = []
    unsynced: list[str] = []

    for rel in sorted(dict.fromkeys(manifest_paths)):
        target = assets_dir / rel
        if target.is_file():
            already_present.append(rel)
            continue
        source = source_dir / rel
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            # copy2 zachowuje metadane; czyta ze źródła, zapisuje tylko do assets_dir.
            shutil.copy2(source, target)
            copied.append(rel)
        else:
            unsynced.append(rel)

    return SyncResult(
        copied=tuple(copied),
        already_present=tuple(already_present),
        unsynced=tuple(unsynced),
    )


def render_result(result: SyncResult) -> str:
    """Zwraca czytelny raport tekstowy z wyniku synchronizacji."""
    lines = [
        f"Skopiowano: {len(result.copied)}",
        f"Już obecne: {len(result.already_present)}",
        f"Niezsynchronizowane: {len(result.unsynced)}",
    ]
    if result.unsynced:
        lines.append("Brakujące w katalogu źródłowym (niezsynchronizowane):")
        lines.extend(f"  - {rel}" for rel in result.unsynced)
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.audit.sync_assets",
        description=(
            "Kopiuje brakujące grafiki z manifestu z katalogu referencyjnego do assets/. "
            "Katalog źródłowy nie jest modyfikowany."
        ),
    )
    parser.add_argument(
        "--from",
        dest="source",
        required=True,
        metavar="KATALOG",
        help="Katalog referencyjny, z którego kopiowane są brakujące pliki z manifestu.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Punkt wejścia CLI. Zwraca kod wyjścia (0 = sukces, 2 = brak ``--from``, 1 = braki).

    ``argparse`` sam kończy proces kodem 2 i komunikatem o użyciu, gdy brakuje
    wymaganego ``--from`` — zgodnie z wymaganiem (brak argumentu = komunikat i kod 2).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    source_dir = Path(args.source)
    if not source_dir.is_dir():
        parser.error(f"Katalog --from nie istnieje lub nie jest katalogiem: {source_dir}")

    manifest_paths = load_manifest_paths(MANIFEST_PATH)
    result = sync_assets(
        source_dir, manifest_paths=manifest_paths, assets_dir=config.ASSETS_DIR
    )
    print(render_result(result))

    # Niezsynchronizowane pliki = błąd krytyczny: brak kompletu grafik offline.
    return 1 if result.has_unsynced else 0


if __name__ == "__main__":  # pragma: no cover - cienki punkt wejścia
    raise SystemExit(main())
