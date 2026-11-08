"""Strażnik punktów centralnych (RULES.md 43.1a): pola stanu zmienia tylko ich funkcja centralna.

Skanuje drzewo ``src/`` (AST) i pada, gdy ktoś ZAPISUJE chronione pole stanu (przypisanie
``x.pole = ...`` / ``x.pole += ...``) poza modułem, który jest jego jedynym właścicielem.
Dzięki temu hook (np. „commodities jak trade goods") dopisany w funkcji centralnej obejmuje
wszystkie miejsca, a rozproszenie nie wraca. Wyjątek: God-Mode (``core/board_edit.py``) — wentyl.

Dodając kolejny punkt centralny (żetony, exhaust, kontrola planet…), dopisz wiersz do ``OWNERS``.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

# pole stanu -> moduły (ścieżki względem ``src/``, POSIX), którym wolno je zapisywać.
OWNERS: dict[str, frozenset[str]] = {
    "trade_goods": frozenset({"core/economy.py", "core/board_edit.py"}),
    "commodities": frozenset({"core/economy.py", "core/board_edit.py"}),
}


def _writes(path: Path, fields: set[str]) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))  # -sig: część plików ma BOM
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
        elif isinstance(node, ast.AugAssign | ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Attribute) and target.attr in fields:
                found.append((node.lineno, target.attr))
    return found


def test_pola_stanu_zapisuje_tylko_modul_wlasciciel() -> None:
    violations: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        for lineno, field in _writes(path, set(OWNERS)):
            if rel not in OWNERS[field]:
                violations.append(f"{rel}:{lineno} zapisuje '{field}' poza {sorted(OWNERS[field])}")
    assert not violations, "Naruszenie punktu centralnego:\n" + "\n".join(violations)
