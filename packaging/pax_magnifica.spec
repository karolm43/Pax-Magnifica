# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: PaxMagnifica.exe (onedir). Budowanie: ``uv run python packaging/build_release.py``.
# Assety, zasady i frontend NIE są w ``_internal`` — build_release kopiuje je obok .exe.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent

# Hooki frakcji/kart są wykrywane dynamicznie (pkgutil) — dołączamy CAŁY pakiet ``src``.
hidden = collect_submodules("src", filter=lambda name: not name.startswith("src.audit"))
hidden += collect_submodules("uvicorn")

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "hypothesis", "mypy", "tkinter", "matplotlib", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PaxMagnifica",
    console=True,
    icon=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PaxMagnifica")
