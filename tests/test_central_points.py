"""Strażnik punktów centralnych (RULES.md 43.1a): pola stanu zmienia tylko ich funkcja centralna.

Skanuje drzewo ``src/`` (AST) i pada, gdy ktoś ZMIENIA chronione pole stanu poza modułem, który
jest jego jedynym właścicielem. Wykrywane formy zmiany:

* przypisanie ``x.pole = ...`` / ``x.pole += ...`` (także w krotce: ``a.p1, a.p2 = ...``),
* zapis/usunięcie po kluczu: ``x.pole[k] = ...`` / ``del x.pole[k]``,
* mutacja kolekcji: ``x.pole.append(...)`` / ``.remove`` / ``.extend`` / ``.pop`` / ``.update``...,
* to samo przez ALIAS: ``units = system.space_units.get(p, {}); units[bt] = n`` albo pętla
  ``for pid, by_type in system.space_units.items(): by_type[bt] = n`` (prosta analiza aliasów
  w obrębie funkcji; kopie ``dict(...)``/``list(...)`` aliasami nie są),
* ``setattr(...)`` poza krótką listą modułów, które używają go ogólnie (kopiowanie stanu).

Dzięki temu hook (np. „commodities jak trade goods") dopisany w funkcji centralnej obejmuje
wszystkie miejsca, a rozproszenie nie wraca. Wyjątek: God-Mode (``core/board_edit.py``) — wentyl.

Dodając kolejny punkt centralny (technologie, VP…), dopisz wiersz do ``OWNERS``.
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
    "exhausted_planets": frozenset({"core/exhaust.py", "core/nexus.py", _GOD_MODE}),
    "exhausted_technologies": frozenset({"core/exhaust.py", _GOD_MODE}),
    "exhausted_strategy_cards": frozenset({"core/exhaust.py", _GOD_MODE}),
    "leader_states": frozenset({"core/exhaust.py", _GOD_MODE}),
    "breakthrough_exhausted": frozenset({"core/exhaust.py", _GOD_MODE}),
    "planet_owners": frozenset({"core/control.py", _GOD_MODE}),
    "controlled_planets": frozenset({"core/control.py", "core/nexus.py", _GOD_MODE}),
    # Jednostki: ``faction_setup.py`` buduje LOKALNY ``SetupPlan`` (dataclass z polami o tych
    # samych nazwach, nie ``SystemState``); do stanu gry jednostki trafiają przez ``unit_ops``.
    "space_units": frozenset({"core/unit_ops.py", "core/faction_setup.py", _GOD_MODE}),
    "planet_units": frozenset({"core/unit_ops.py", "core/faction_setup.py", _GOD_MODE}),
    "damaged_units": frozenset({"core/damage.py", _GOD_MODE}),
    # Technologie: ``registry.py`` ma KATALOG technologii (słownik definicji), nie listę gracza.
    "technologies": frozenset({"core/technology.py", "core/registry.py", _GOD_MODE}),
    "victory_points": frozenset({"core/objectives.py", _GOD_MODE}),
    "speaker_id": frozenset({"core/strategy_phase.py", _GOD_MODE}),
    # Karty akcji: ręka i talie. ``deck_piles.py`` to narzędzie DEBUG (God-Mode, RULES.md 46.4).
    "action_cards": frozenset({"core/card_draw.py", _GOD_MODE}),
    "action_card_deck": frozenset({"core/card_draw.py", "core/deck_piles.py", _GOD_MODE}),
    "action_card_discard": frozenset({"core/card_draw.py", "core/deck_piles.py", _GOD_MODE}),
    # --- C9: reszta kart i zasobów ---
    # Talia agend: zasiew i układanie wierzchu (Politics) w ``card_draw``.
    "agenda_deck": frozenset({"core/card_draw.py", _GOD_MODE}),
    "agenda_discard": frozenset({"core/card_draw.py", _GOD_MODE}),
    # Tajne cele: talia, ręka, kandydaci z setupu i zdobyte.
    "secret_objective_deck": frozenset({"core/secret_objectives.py", _GOD_MODE}),
    "secret_objectives": frozenset({"core/secret_objectives.py", _GOD_MODE}),
    "secret_candidates": frozenset({"core/secret_objectives.py", _GOD_MODE}),
    "scored_secrets": frozenset({"core/secret_objectives.py", _GOD_MODE}),
    # Promissory notes: ręka i strefa gry.
    "promissory_notes": frozenset({"core/promissory_notes.py", _GOD_MODE}),
    "promissory_notes_in_play": frozenset({"core/promissory_notes.py", _GOD_MODE}),
    # Fragmenty reliktów w strefie gracza.
    "relic_fragments": frozenset({"core/relic_fragments.py", _GOD_MODE}),
    # Eksploracja: talie, odrzucone, purge i attachmenty planet należą do ``exploration``;
    # ``deck_piles.py`` to narzędzie DEBUG (God-Mode, RULES.md 46.4).
    "exploration_deck": frozenset({"core/exploration.py", "core/deck_piles.py", _GOD_MODE}),
    "exploration_discard": frozenset({"core/exploration.py", "core/deck_piles.py", _GOD_MODE}),
    "purged": frozenset({"core/exploration.py", "core/deck_piles.py", _GOD_MODE}),
    "planet_attachments": frozenset({"core/exploration.py", _GOD_MODE}),
    # Przełom frakcji: odblokowanie idzie przez core/breakthrough.py (ekspedycje, RULES.md 50);
    # odłożenie TG dojdzie z hookami.
    "breakthrough_unlocked": frozenset({"core/breakthrough.py", _GOD_MODE}),
    "breakthrough_tg": frozenset({_GOD_MODE}),
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
# Metody zwracające widok/element tej samej kolekcji (alias), a nie kopię.
_ALIAS_METHODS = frozenset({"get", "setdefault", "pop", "items", "values", "keys"})


def _names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Tuple | ast.List):
        return [name for item in target.elts for name in _names(item)]
    if isinstance(target, ast.Starred):
        return _names(target.value)
    return []


def _flatten(target: ast.expr) -> list[ast.expr]:
    if isinstance(target, ast.Tuple | ast.List):
        return [leaf for item in target.elts for leaf in _flatten(item)]
    if isinstance(target, ast.Starred):
        return _flatten(target.value)
    return [target]


class _Scan(ast.NodeVisitor):
    """Przechodzi kod w kolejności źródła, śledząc aliasy chronionych pól w obrębie funkcji."""

    def __init__(self, fields: set[str], tainted: dict[str, set[str]] | None = None) -> None:
        self.fields = fields
        self.tainted: dict[str, set[str]] = dict(tainted or {})
        self.found: list[tuple[int, str]] = []

    # --- aliasy ---------------------------------------------------------------------------

    def alias(self, expr: ast.expr | None) -> set[str]:
        """Które chronione pola mogą być (żywym) widokiem wartości ``expr``."""
        if expr is None:
            return set()
        if isinstance(expr, ast.Attribute):
            if expr.attr in self.fields:
                return {expr.attr}
            return self.alias(expr.value)
        if isinstance(expr, ast.Subscript):
            return self.alias(expr.value)
        if isinstance(expr, ast.Name):
            return set(self.tainted.get(expr.id, set()))
        if isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Attribute) and expr.func.attr in _ALIAS_METHODS:
                return self.alias(expr.func.value)
            return set()
        if isinstance(expr, ast.BoolOp):
            return set().union(*(self.alias(v) for v in expr.values))
        if isinstance(expr, ast.IfExp):
            return self.alias(expr.body) | self.alias(expr.orelse)
        return set()

    def _bind(self, targets: list[ast.expr], value: ast.expr | None) -> None:
        fields = self.alias(value)
        for target in targets:
            for name in _names(target):
                if fields:
                    self.tainted[name] = set(fields)
                else:
                    self.tainted.pop(name, None)

    # --- mutacje --------------------------------------------------------------------------

    def _flag(self, lineno: int, fields: set[str]) -> None:
        for field in sorted(fields & self.fields):
            self.found.append((lineno, field))

    def _mutation_target(self, target: ast.expr, lineno: int) -> None:
        """Zapis do ``target`` (Attribute = samo pole; Subscript = element kolekcji)."""
        if isinstance(target, ast.Attribute):
            if target.attr in self.fields:
                self._flag(lineno, {target.attr})
            return
        if isinstance(target, ast.Subscript):
            self._flag(lineno, self.alias(target))

    # --- węzły ----------------------------------------------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        leaves = [leaf for t in node.targets for leaf in _flatten(t)]
        for leaf in leaves:
            self._mutation_target(leaf, node.lineno)
        self._bind(leaves, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
            for leaf in _flatten(node.target):
                self._mutation_target(leaf, node.lineno)
            self._bind(_flatten(node.target), node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        for leaf in _flatten(node.target):
            self._mutation_target(leaf, node.lineno)

    def visit_Delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            for leaf in _flatten(target):
                self._mutation_target(leaf, node.lineno)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._bind(_flatten(node.target), node.iter)
        for stmt in node.body + node.orelse:
            self.visit(stmt)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _MUTATORS:
            self._flag(node.lineno, self.alias(func.value))
        self.generic_visit(node)

    def _scope(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        inner = _Scan(self.fields, self.tainted)
        for stmt in node.body:
            inner.visit(stmt)
        self.found.extend(inner.found)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scope(node)


def _writes_in_source(source: str, fields: set[str]) -> list[tuple[int, str]]:
    scan = _Scan(fields)
    scan.visit(ast.parse(source))
    return sorted(set(scan.found))


def _writes(path: Path, fields: set[str]) -> list[tuple[int, str]]:
    return _writes_in_source(path.read_text(encoding="utf-8-sig"), fields)  # -sig: BOM


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


# --- test samego strażnika: musi łapać wszystkie formy zmiany i nie krzyczeć na kopie/odczyty ----

_FIELDS = {"space_units", "trade_goods"}


def _hits(source: str) -> list[str]:
    return [field for _, field in _writes_in_source(source, _FIELDS)]


def test_straznik_lapie_przypisania_krotki_i_mutacje() -> None:
    assert _hits("def f(p):\n    p.trade_goods -= 1\n") == ["trade_goods"]
    assert _hits("def f(p):\n    p.a, p.trade_goods = 1, 2\n") == ["trade_goods"]
    assert _hits("def f(s):\n    s.space_units['p'] = {}\n") == ["space_units"]
    assert _hits("def f(s):\n    del s.space_units['p']\n") == ["space_units"]
    assert _hits("def f(s):\n    s.space_units.pop('p', None)\n") == ["space_units"]


def test_straznik_lapie_aliasy() -> None:
    alias_get = "def f(s):\n    u = s.space_units.get('p', {})\n    u['x'] = 1\n"
    assert _hits(alias_get) == ["space_units"]
    alias_loop = (
        "def f(s):\n    for pid, by in s.space_units.items():\n        by['x'] -= 1\n"
    )
    assert _hits(alias_loop) == ["space_units"]
    alias_chain = "def f(s):\n    a = s.space_units['p']\n    b = a\n    b.pop('x', None)\n"
    assert _hits(alias_chain) == ["space_units"]
    call_receiver = "def f(s):\n    s.space_units.get('p', {}).pop('x', None)\n"
    assert _hits(call_receiver) == ["space_units"]


def test_straznik_nie_krzyczy_na_odczyty_i_kopie() -> None:
    assert _hits("def f(s):\n    return s.space_units.get('p', {}).get('x', 0)\n") == []
    copy = "def f(s):\n    u = dict(s.space_units.get('p', {}))\n    u['x'] = 1\n"
    assert _hits(copy) == []
    rebound = (
        "def f(s):\n    u = s.space_units.get('p', {})\n    u = []\n    u.append(1)\n"
    )
    assert _hits(rebound) == []
    assert _hits("def f(s):\n    n = len(s.space_units)\n    n += 1\n") == []
