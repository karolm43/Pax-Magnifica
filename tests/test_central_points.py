"""Strażnik punktów centralnych (RULES.md 43.1a): pola stanu zmienia tylko ich funkcja centralna.

Skanuje drzewo ``src/`` (AST) i pada, gdy ktoś ZMIENIA chronione pole stanu poza modułem, który
jest jego jedynym właścicielem. Wykrywane formy zmiany:

* przypisanie ``x.pole = ...`` / ``x.pole += ...`` (także w krotce: ``a.p1, a.p2 = ...``),
* zapis/usunięcie po kluczu: ``x.pole[k] = ...`` / ``del x.pole[k]``,
* mutacja kolekcji: ``x.pole.append(...)`` / ``.remove`` / ``.extend`` / ``.pop`` / ``.update``...
* ``setattr(...)`` poza krótką listą modułów, które używają go ogólnie (kopiowanie stanu).

Dzięki temu hook (np. „commodities jak trade goods") dopisany w funkcji centralnej obejmuje
wszystkie miejsca, a rozproszenie nie wraca. Wyjątek: God-Mode (``core/board_edit.py``) — wentyl.

Dodając kolejny punkt centralny (kontrola planet, jednostki…), dopisz wiersz do ``OWNERS``.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

_GOD_MODE = "core/board_edit.py"

# pole stanu -> moduły (ścieżki względem ``src/``, POSIX), którym wolno je zmieniać.
OWNERS: dict[str, frozenset[str]] = {
    "trade_goods": frozenset({"core/economy.py", _GOD_MODE}),
    "commodities": frozenset({"core/economy.py", _GOD_MODE}),
    "cc_reinf": frozenset({"core/command_tokens.py", _GOD_MODE}),
    "tactical_cc": frozenset({"core/command_tokens.py", _GOD_MODE}),
    "fleet_cc": frozenset({"core/command_tokens.py", _GOD_MODE}),
    "strategic_cc": frozenset({"core/command_tokens.py", _GOD_MODE}),
    "exhausted_planets": frozenset({"core/exhaust.py", _GOD_MODE}),
    "exhausted_technologies": frozenset({"core/exhaust.py", _GOD_MODE}),
    "exhausted_strategy_cards": frozenset({"core/exhaust.py", _GOD_MODE}),
    "leader_states": frozenset({"core/exhaust.py", _GOD_MODE}),
    "breakthrough_exhausted": frozenset({"core/exhaust.py", _GOD_MODE}),
    "planet_owners": frozenset({"core/control.py", _GOD_MODE}),
    "controlled_planets": frozenset({"core/control.py", _GOD_MODE}),
}

# ``setattr`` ogólnego przeznaczenia (nazwa pola zmienna): moduły dozwolone poza właścicielami pól.
# command_tokens.py używa go na pulach; reszta kopiuje/projektuje cały stan (nie konkretne pole).
_SETATTR_ALLOWED = frozenset(
    {
        "core/command_tokens.py",
        _GOD_MODE,
        "core/visibility.py",
        "core/strategy_cards/imperial.py",
        "core/strategy_cards/warfare.py",
    }
)

_MUTATORS = frozenset(
    {
        "append", "remove", "extend", "pop", "clear", "insert", "sort", "reverse",
        "update", "setdefault", "popitem",
    }
)


def _protected(target: ast.expr) -> ast.expr:
    """Dla ``x.pole[klucz]`` zwraca ``x.pole`` (zapis do słownika/listy w polu stanu)."""
    return target.value if isinstance(target, ast.Subscript) else target


def _flatten(target: ast.expr) -> list[ast.expr]:
    if isinstance(target, ast.Tuple | ast.List):
        return [leaf for item in target.elts for leaf in _flatten(item)]
    if isinstance(target, ast.Starred):
        return _flatten(target.value)
    return [target]


def _writes(path: Path, fields: set[str]) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))  # -sig: część plików ma BOM
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [leaf for t in node.targets for leaf in _flatten(t)]
        elif isinstance(node, ast.AugAssign | ast.AnnAssign):
            targets = _flatten(node.target)
        elif isinstance(node, ast.Delete):
            targets = [leaf for t in node.targets for leaf in _flatten(t)]
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _MUTATORS
            and isinstance(node.func.value, ast.Attribute)
        ):
            targets = [node.func.value]
        else:
            continue
        for raw in targets:
            target = _protected(raw)
            if isinstance(target, ast.Attribute) and target.attr in fields:
                found.append((node.lineno, target.attr))
    return found


def _setattr_calls(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "setattr"
    ]


def test_pola_stanu_zmienia_tylko_modul_wlasciciel() -> None:
    violations: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        for lineno, field in _writes(path, set(OWNERS)):
            if rel not in OWNERS[field]:
                violations.append(f"{rel}:{lineno} zmienia '{field}' poza {sorted(OWNERS[field])}")
    assert not violations, "Naruszenie punktu centralnego:\n" + "\n".join(violations)


def test_setattr_tylko_w_dozwolonych_modulach() -> None:
    violations = [
        f"{path.relative_to(SRC).as_posix()}:{lineno} używa setattr()"
        for path in sorted(SRC.rglob("*.py"))
        if path.relative_to(SRC).as_posix() not in _SETATTR_ALLOWED
        for lineno in _setattr_calls(path)
    ]
    assert not violations, (
        "setattr() może obejść punkt centralny (nazwa pola jest zmienna):\n" + "\n".join(violations)
    )
