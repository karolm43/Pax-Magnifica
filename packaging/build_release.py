"""Buduje paczkę do rozesłania: ``release/PaxMagnifica/`` + ``release/PaxMagnifica-<data>.zip``.

Użycie (w korzeniu repo):  ``uv run python packaging/build_release.py``
Opcje: ``--skip-frontend`` (użyj istniejącego ``frontend/dist``), ``--no-zip``, ``--out KATALOG``
(inny katalog wyjścia — np. gdy z ``release/`` działa właśnie uruchomiona gra).

Kroki:
1. ``npm run build`` → ``frontend/dist``.
2. PyInstaller (onedir) → ``PaxMagnifica.exe`` + ``_internal/`` (Python, zależności, kod ``src``).
3. Obok ``.exe``: ``assets/`` (BEZ katalogów nieużywanych przez grę — patrz ``ASSET_EXCLUDES``),
   ``docs/rules_tirules`` (przeglądarka zasad), ``frontend/dist``, ``JAK_GRAC.txt``.
4. Zip (media bez kompresji — mp3/png/webp i tak są skompresowane).

Odbiorca: rozpakowuje zip, klika ``PaxMagnifica.exe``. Nie instaluje ani Pythona, ani Node.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "release"
APP_NAME = "PaxMagnifica"

ASSET_EXCLUDES = {
    # Oryginały muzyki (.mkv, ~1,2 GB) — gra używa przekonwertowanych mp3 z ``assets/music``.
    "music_originals",
    # Nieużywane przez front ani backend (sprawdzone grepem po ``src``/``frontend/src``).
    "quick_reference",
    "stickers",
    "server_icons",
    "META-INF",
}
ASSET_FILE_EXCLUDES = {"logback.xml", "struktura_assetow.txt"}
STORED_SUFFIXES = {".mp3", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm", ".ogg"}


def _run(cmd: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}  (in {cwd})", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, shell=sys.platform == "win32")


def build_frontend() -> None:
    _run(["npm", "run", "build"], ROOT / "frontend")


def _running_from(folder: Path) -> bool:
    """Czy z ``folder`` działa ``PaxMagnifica.exe`` (Windows) — wtedy nie wolno go nadpisać."""
    exe = folder / f"{APP_NAME}.exe"
    if sys.platform != "win32" or not exe.exists():
        return False
    try:
        with exe.open("r+b"):  # uruchomiony .exe jest zablokowany do zapisu
            pass
    except OSError:
        return True
    return False


def build_exe() -> Path:
    saves = RELEASE / APP_NAME / "saves"
    if saves.is_dir() and any(saves.iterdir()):
        raise SystemExit(f"{saves} holds saved games - move them out or use --out <folder>.")
    if _running_from(RELEASE / APP_NAME):
        raise SystemExit(
            f"{RELEASE / APP_NAME} is running - close the game or use --out <folder>."
        )
    _run(
        [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--distpath", str(RELEASE), "--workpath", str(RELEASE / "_build"),
            str(ROOT / "packaging" / "pax_magnifica.spec"),
        ],
        ROOT,
    )
    return RELEASE / APP_NAME


def _ignore_assets(directory: str, names: list[str]) -> set[str]:
    if Path(directory).resolve() == (ROOT / "assets").resolve():
        return {n for n in names if n in ASSET_EXCLUDES or n in ASSET_FILE_EXCLUDES}
    return {n for n in names if n == "__pycache__"}


def copy_data(target: Path) -> None:
    print("Copying assets (this takes a moment)...", flush=True)
    shutil.copytree(ROOT / "assets", target / "assets", ignore=_ignore_assets, dirs_exist_ok=True)
    shutil.copytree(
        ROOT / "docs" / "rules_tirules", target / "docs" / "rules_tirules", dirs_exist_ok=True
    )
    dist = ROOT / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        raise SystemExit("frontend/dist/index.html missing - run without --skip-frontend.")
    shutil.copytree(dist, target / "frontend" / "dist", dirs_exist_ok=True)
    shutil.copy2(ROOT / "packaging" / "JAK_GRAC.txt", target / "JAK_GRAC.txt")


def make_zip(folder: Path) -> Path:
    archive = RELEASE / f"{APP_NAME}-{time.strftime('%Y%m%d')}.zip"
    print(f"Zipping -> {archive}", flush=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            arcname = Path(APP_NAME) / path.relative_to(folder)
            stored = path.suffix.lower() in STORED_SUFFIXES
            zf.write(path, arcname, compress_type=zipfile.ZIP_STORED if stored else None)
    return archive


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--no-zip", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.out is not None:
        global RELEASE
        RELEASE = args.out.resolve()
    if not args.skip_frontend:
        build_frontend()
    folder = build_exe()
    copy_data(folder)
    if not args.no_zip:
        archive = make_zip(folder)
        print(f"Done: {archive} ({archive.stat().st_size / 2**30:.2f} GB)")
    print(f"Folder: {folder}  ->  run {folder / (APP_NAME + '.exe')}")


if __name__ == "__main__":
    main()
