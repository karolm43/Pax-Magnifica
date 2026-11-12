"""Osiągalność okien: czy komponent z oknem ma KANAŁ, który pokaże go graczowi (RULES.md 54.8).

Katalog okien (``timing_catalog``) mówi, KIEDY komponent działa. Ten moduł sprawdza, czy silnik
faktycznie do niego dociera w tej chwili i czy gracz to widzi. Kanały:

* ``auto``   - hook obowiązkowy na emitowanym zdarzeniu (ślad w feedzie: ``triggers._run_visible``);
* ``offer``  - hook z „may” / decyzją: oferta w panelu decyzji;
* ``hand``   - karta akcji / notka z ręki: zagrywalna, gdy dostawca okna (``@window_provider``)
  otwiera jej (zdarzenie, moment); UI sygnalizuje ją także przy zwiniętej ręce;
* ``now``    - „During X: you may…” komponentu frakcji: karta „Available now” (``window_use``);
* ``button`` - zdolność technologii poza akcją (``register_ability``);
* ``mod``    - modyfikator wbudowany w regułę bazową (punkt ``POINT_*``), działa w środku kroku;
* ``rule``   - efekt z danych, jawny wybór gracza w akcji (``declare_player_option``) albo wersja
  karty zastąpiona erratą (``declare_superseded``) - bez osobnego hooka.

Wykrywane luki (strażnik: ``tests/test_timing_reach.py``):

* hook na (zdarzenie, moment), którego żaden ``triggers.fire`` nie emituje - nigdy nie zadziała;
* karta/notka z ręki z efektem, której okna nie otwiera żaden dostawca - nigdy nie zagrywalna;
* komponent z efektem (``register_effect``) i oknem czasowym bez żadnego kanału - efekt martwy.

Analiza źródeł jest STATYCZNA (AST): ``fire(state, GameEvent.X, Moment.Y, ...)`` w ``src/`` oraz
``OpenWindow(GameEvent.X, Moment.Y, ...)`` w funkcjach ``@window_provider``.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from src.core import faction_components, promissory_play, reaction_cards, rules_hooks
from src.core.components import ComponentCategory
from src.core.game_events import GameEvent, Moment, event_point
from src.core.registry import StaticDataRegistry

SRC = Path(__file__).resolve().parent.parent
HOOKS_DIR = SRC / "core" / "hooks"

# Rodzaj źródła hooka -> kategoria klucza komponentu („<kategoria>:<id>”).
_SOURCE_CATEGORY = {
    rules_hooks.SOURCE_FACTION: "abilities",
    rules_hooks.SOURCE_TECHNOLOGY: "technologies",
    rules_hooks.SOURCE_PROMISSORY: "promissory_notes",
    rules_hooks.SOURCE_RELIC: "relics",
    rules_hooks.SOURCE_LEADER: "leaders",
    rules_hooks.SOURCE_BREAKTHROUGH: "breakthroughs",
    rules_hooks.SOURCE_AGENDA: "agendas",
}

Pair = tuple[str, str]  # (zdarzenie, moment) jako wartości enumów, np. ("turn", "start")


@dataclass
class Reach:
    """Wynik audytu: kanały komponentów i luki."""

    fired: set[Pair] = field(default_factory=set)
    provided: set[Pair] = field(default_factory=set)
    channels: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    dead_hooks: list[str] = field(default_factory=list)
    dead_hand: list[str] = field(default_factory=list)
    dead_effects: list[str] = field(default_factory=list)


def _read(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _enum_pair(event: ast.expr, moment: ast.expr) -> Pair | None:
    if not (isinstance(event, ast.Attribute) and isinstance(moment, ast.Attribute)):
        return None
    if getattr(event.value, "id", "") != "GameEvent" or getattr(moment.value, "id", "") != "Moment":
        return None
    try:
        return GameEvent[event.attr].value, Moment[moment.attr].value
    except KeyError:
        return None


def fired_pairs(root: Path = SRC) -> set[Pair]:
    """Pary emitowane przez ``fire(state, GameEvent.X, Moment.Y, ...)`` w kodzie (bez ``audit``)."""
    found: set[Pair] = set()
    for path in root.rglob("*.py"):
        if "audit" in path.parts:
            continue
        for node in ast.walk(_read(path)):
            if not isinstance(node, ast.Call) or len(node.args) < 3:
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name == "fire":
                pair = _enum_pair(node.args[1], node.args[2])
                if pair is not None:
                    found.add(pair)
    return found


def provided_pairs(root: Path = HOOKS_DIR) -> set[Pair]:
    """Pary okien otwieranych przez dostawców ``@window_provider`` (karty i notki z ręki)."""
    found: set[Pair] = set()
    for path in root.rglob("*.py"):
        for fn in ast.walk(_read(path)):
            if not isinstance(fn, ast.FunctionDef):
                continue
            if not any(getattr(d, "id", "") == "window_provider" for d in fn.decorator_list):
                continue
            for node in ast.walk(fn):
                pair: Pair | None = None
                if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "OpenWindow":
                    if len(node.args) >= 2:
                        pair = _enum_pair(node.args[0], node.args[1])
                elif isinstance(node, ast.Tuple) and len(node.elts) == 2:
                    pair = _enum_pair(node.elts[0], node.elts[1])
                if pair is not None:
                    found.add(pair)
    return found


def _hook_key(hook: rules_hooks.Hook) -> str | None:
    if hook.covers:
        return hook.covers
    category = _SOURCE_CATEGORY.get(hook.source.kind)
    return f"{category}:{hook.source.component_id}" if category else None


def _hand_points(registry: StaticDataRegistry) -> dict[str, list[Pair]]:
    """Punkty okien kart akcji i notek grane z ręki (bez ACTION i notek „place faceup”)."""
    points: dict[str, list[Pair]] = {}
    for card_id in registry.catalog.all(ComponentCategory.ACTION_CARD):
        spec = reaction_cards.spec_for(registry, card_id)
        if spec is not None:
            points[f"action_cards:{card_id}"] = [(e.value, m.value) for e, m in spec.points]
    for template, note in promissory_play._templates(registry).items():
        immediate = getattr(note, "play_immediately", False)
        if promissory_play.is_action(registry, template) or immediate:
            continue
        points[f"promissory_notes:{template}"] = [
            (e.value, m.value) for e, m in promissory_play._points(registry, template)
        ]
    return points


def analyse(registry: StaticDataRegistry, timed_keys: set[str]) -> Reach:
    """Buduje mapę kanałów i listy luk.

    Args:
        timed_keys: Klucze komponentów, które katalog okien uznał za „reakcję w oknie” albo
            „przy zdobyciu” (``timing_catalog.Entry.kind in {"timed", "gain"}``).
    """
    rules_hooks.bind_registry(registry)
    reach = Reach(fired=fired_pairs(), provided=provided_pairs())
    events = {event_point(e, m): (e.value, m.value) for e in GameEvent for m in Moment}
    for hook in rules_hooks.all_hooks():
        key = _hook_key(hook)
        pair = events.get(hook.point)
        if pair is None:
            if key:
                reach.channels[key].append(f"mod@{hook.point}")
            continue
        if pair not in reach.fired:
            name = key or hook.label or hook.fn.__name__
            reach.dead_hooks.append(f"{name} @ {pair[0]}/{pair[1]}")
        if key:
            kind = "offer" if hook.optional or hook.decide else "auto"
            reach.channels[key].append(f"{kind}@{pair[0]}/{pair[1]}")
    for key in faction_components._WINDOW_USES:
        reach.channels[key].append("now")
    for tech_id in rules_hooks.all_abilities():
        reach.channels[f"technologies:{tech_id}"].append("button")
    for key in rules_hooks._DATA_DRIVEN:  # dane / jawny parametr akcji / wersja zastąpiona erratą
        reach.channels[key].append("rule")
    effects = set(rules_hooks._EFFECTS)
    for key, points in _hand_points(registry).items():
        for pair in points:
            reach.channels[key].append(f"hand@{pair[0]}/{pair[1]}")
        if key not in effects:
            continue
        if not points or not any(pair in reach.provided for pair in points):
            reach.dead_hand.append(f"{key} @ {points or 'unrecognised window'}")
    for key in sorted(effects & timed_keys):
        if not reach.channels.get(key):
            reach.dead_effects.append(key)
    reach.dead_hooks.sort()
    reach.dead_hand.sort()
    return reach
