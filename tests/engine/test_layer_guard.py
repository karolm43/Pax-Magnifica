"""Strażnik warstwy bota (RULES.md 65.1, 65.5): ``src/engine`` nie zna ``api/`` ani zegara.

Zależności idą tylko w dół (``api/`` → ``engine/`` → ``core/``), a czas i losowość przychodzą
z zewnątrz (wstrzykiwany ``now``, ziarno), więc decyzje bota są powtarzalne.
"""

from __future__ import annotations

import ast
from pathlib import Path

from src import config

ENGINE = config.PROJECT_ROOT / "src" / "engine"
FORBIDDEN_MODULES = ("src.api", "fastapi", "time", "secrets")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_engine_does_not_import_api_clock_or_entropy() -> None:
    offenders = {
        str(path.relative_to(ENGINE)): sorted(
            name for name in _imports(path)
            if any(name == m or name.startswith(f"{m}.") for m in FORBIDDEN_MODULES)
        )
        for path in ENGINE.rglob("*.py")
    }
    assert {k: v for k, v in offenders.items() if v} == {}


def test_engine_has_modules_to_guard() -> None:
    assert (ENGINE / "actions.py").is_file() and (ENGINE / "legal.py").is_file()
