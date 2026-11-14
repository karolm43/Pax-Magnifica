"""Smoke test WSZYSTKICH kart akcji aktywnej talii (RULES.md 53).

Dla każdej z 140 kart, na jednym bogatym stanie testowym (mapa demo, dwóch graczy, jednostki,
planety, technologie, talie), sprawdza łańcuch, który przechodzi UI przy zagraniu karty:

1. ``playability`` nie rzuca wyjątku i podaje powód, gdy karta nie jest zagrywalna;
2. ``card_inputs`` buduje formularz (typy wejść zgodne z kontraktem UI);
3. gdy karta jest zagrywalna: ``play_action_card`` z parametrami z PIERWSZEJ i OSTATNIEJ opcji
   formularza (jak klik w UI) nie rzuca wyjątku, nie mutuje wejścia, zdejmuje kartę z ręki,
   odkłada ją na stos odrzuconych (ACTION: zużywa akcję tury) i daje stan, który przechodzi
   serializację JSON w obie strony.

Wynik per karta: OK / NO_EFFECT (brak efektu w silniku) / NOT_PLAYABLE (brak legalnego celu
albo okna w tym scenariuszu - do sprawdzenia ręcznie) / PARAMS_REJECTED (silnik odrzucił
parametry "pierwsza/ostatnia opcja", np. za mało wpływu - do sprawdzenia ręcznie) /
FAIL (błąd kontraktu) / CRASH (wyjątek niespodziewanego typu). FAIL i CRASH oblewają test;
resztę pokazuje raport (pomijane testy).

Raport zbiorczy: wypisywany na końcu przebiegu i zapisywany do
``.pytest_cache/karty_akcji_smoke.md``.
Uruchomienie: ``uv run pytest tests/test_action_cards_smoke.py -q -rs``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import action_cards, board_graph
from src.core.components import ActionCardDef, ComponentCategory, ComponentRef
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.objectives import deck_card_ids
from src.core.registry import StaticDataRegistry
from src.core.timing_spec import TriggerKind

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / ".pytest_cache" / "karty_akcji_smoke.md"

OK = "OK"
NO_EFFECT = "NO_EFFECT"
NOT_PLAYABLE = "NOT_PLAYABLE"
PARAMS_REJECTED = "PARAMS_REJECTED"
FAIL = "FAIL"
CRASH = "CRASH"

P1_POSITIONS = ("101", "102", "103")
P2_POSITIONS = ("104", "105", "106")
INPUT_KINDS = {"choice", "multi", "number", "info", "research"}


@dataclass
class Row:
    """Wynik smoke testu jednej karty."""

    card_id: str
    name: str
    kind: str  # ACTION / REACTION
    status: str
    detail: str = ""


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(scope="module")
def card_ids(registry: StaticDataRegistry) -> list[str]:
    return deck_card_ids(registry, "action_card")


@pytest.fixture(autouse=True, scope="module")
def _grid(registry: StaticDataRegistry) -> Iterator[None]:
    """Podpina mapę demo dla efektów kart (jak robi to ``AppContext``) i przywraca poprzednią."""
    grid = build_demo_grid(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield
    board_graph.bind_grid_provider(previous)


_ROWS: dict[str, Row] = {}


@pytest.fixture(autouse=True, scope="module")
def _report(request: pytest.FixtureRequest) -> Iterator[None]:
    """Na końcu modułu składa raport zbiorczy (terminal + plik)."""
    yield
    if not _ROWS:
        return
    text = _render_report(sorted(_ROWS.values(), key=lambda r: (r.status, r.card_id)))
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text, encoding="utf-8")
    reporter = request.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line("")
        reporter.write_line(text.split("\n\n", 1)[0])
        reporter.write_line(f"Pełny raport: {REPORT_PATH}")


def _render_report(rows: list[Row]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    summary = "Karty akcji (smoke): " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    lines = [summary, "", "| Status | Typ | Karta | Szczegóły |", "|---|---|---|---|"]
    for row in rows:
        detail = row.detail.replace("|", "/").replace("\n", " ")
        lines.append(f"| {row.status} | {row.kind} | {row.name} (`{row.card_id}`) | {detail} |")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- stan testowy


def _build_state(registry: StaticDataRegistry, card_id: str, all_ids: list[str]) -> GameState:
    """Bogaty stan: p1 (aktywny, ma kartę) i p2 z jednostkami, planetami, technologiami, taliami."""
    grid = build_demo_grid(registry)
    systems: dict[str, SystemState] = {}
    for position in sorted(grid.positions):
        systems[position] = SystemState(position=position, system_id=grid.system_id_at(position))
    owned: dict[str, list[str]] = {"p1": [], "p2": []}
    for owner, positions in (("p1", P1_POSITIONS), ("p2", P2_POSITIONS)):
        for position in positions:
            system = systems[position]
            system.space_units = {owner: {"carrier": 1, "destroyer": 1, "fighter": 2}}
            for index, planet in enumerate(registry.systems[system.system_id].planets):
                system.planet_owners[planet] = owner
                units = {"infantry": 2}
                if index == 0:
                    units.update({"spacedock": 1, "pds": 1})
                system.planet_units[planet] = {owner: units}
                owned[owner].append(planet)

    generic_techs = [
        tid for tid in sorted(registry.technologies) if registry.technologies[tid].faction is None
    ]
    others = [c for c in all_ids if c != card_id]
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(
                player_id="p1", color="red", faction="sol", home_position="103",
                trade_goods=5, commodities=2, technologies=generic_techs[:2],
                exhausted_planets=owned["p1"][:1],
            ),
            "p2": PlayerState(
                player_id="p2", color="blue", faction="arborec", home_position="105",
                trade_goods=3, commodities=1, technologies=generic_techs[2:6],
            ),
        },
        systems=systems,
    )
    state.players["p1"].private.action_cards = [card_id]
    state.players["p2"].private.action_cards = others[20:23]
    state.decks.action_card_deck = others[:20]
    state.decks.action_card_discard = others[23:26]
    return state


# ----------------------------------------------------------------------------- parametry z UI


def _params_from_inputs(inputs: list[dict[str, Any]], *, last: bool) -> dict[str, Any]:
    """Parametry jak w UI: pierwsza (``last=False``) albo ostatnia opcja każdego wyboru."""
    params: dict[str, Any] = {}
    for item in inputs:
        kind = item["kind"]
        if kind == "number":
            params[item["key"]] = item["max"] if last else item["min"]
            continue
        options = item["options"]
        if kind == "choice":
            if not options:
                continue
            value = options[-1]["value"] if last else options[0]["value"]
            if item.get("merge"):
                params.update(value)
            else:
                params[item["key"]] = value
        elif kind == "multi":
            size = max(int(item["max"]), int(item["min"]))
            chosen = options[-size:] if last else options[:size]
            params[item["key"]] = [o["value"] for o in chosen]
    return params


def _check_inputs_contract(inputs: list[dict[str, Any]]) -> str | None:
    """Kontrakt formularza z frontem: znane ``kind`` i wymagane pola. Błąd albo None."""
    for item in inputs:
        kind = item.get("kind")
        if kind not in INPUT_KINDS:
            return f"nieznany typ wejścia {kind!r}"
        required = {"key", "label"} | ({"min", "max"} if kind in {"multi", "number"} else set())
        if kind in {"choice", "multi", "info"}:
            required.add("options")
        if kind == "research":
            required.add("research")
        missing = required - set(item)
        if missing:
            return f"wejście {item.get('key')!r} bez pól {sorted(missing)}"
    return None


# ----------------------------------------------------------------------------- sprawdzenie karty


def _check_card(registry: StaticDataRegistry, card_id: str, all_ids: list[str]) -> Row:
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
    name = card.name if isinstance(card, ActionCardDef) and card.name else card_id
    spec = registry.catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, card_id))
    is_action = spec is not None and spec.trigger is TriggerKind.ACTION
    row = Row(card_id, name, "ACTION" if is_action else "REACTION", OK)
    state = _build_state(registry, card_id, all_ids)

    try:
        rows = action_cards.playability(state, registry, "p1")
        entry = next(r for r in rows if r["card_id"] == card_id)
        implemented, inputs = action_cards.card_inputs(state, registry, "p1", card_id)
    except Exception as exc:  # noqa: BLE001 - smoke test: każdy wyjątek to CRASH
        row.status, row.detail = CRASH, f"playability/inputs: {type(exc).__name__}: {exc}"
        return row

    if not implemented:
        row.status, row.detail = NO_EFFECT, "brak efektu w silniku (ręczne rozstrzygnięcie)"
        return row
    problem = _check_inputs_contract(inputs)
    if problem is not None:
        row.status, row.detail = FAIL, f"formularz: {problem}"
        return row
    if not entry["playable"]:
        row.status, row.detail = NOT_PLAYABLE, str(entry["reason"])
        return row

    for last in (False, True):
        label = "ostatnia opcja" if last else "pierwsza opcja"
        failure = _try_play(registry, state, card_id, inputs, is_action, last=last)
        if failure is not None:
            row.status, row.detail = failure[0], f"{label}: {failure[1]}"
            return row
    return row


def _try_play(
    registry: StaticDataRegistry,
    state: GameState,
    card_id: str,
    inputs: list[dict[str, Any]],
    is_action: bool,
    *,
    last: bool,
) -> tuple[str, str] | None:
    """Zagrywa kartę i sprawdza niezmienniki. Przy błędzie ``(status, opis)``, inaczej None."""
    params = _params_from_inputs(inputs, last=last)
    before = state.model_dump()
    try:
        new, _implemented = action_cards.play_action_card(state, registry, "p1", card_id, params)
    except ValueError as exc:
        # Naiwne parametry (pierwsza/ostatnia opcja) mogą być nielegalne jako zestaw, np. za mało
        # wpływu na zapłatę - to nie błąd silnika, tylko karta do sprawdzenia ręcznie.
        return PARAMS_REJECTED, f"silnik odrzucił naiwne parametry: {exc} (params={params})"
    except Exception as exc:  # noqa: BLE001
        return CRASH, f"{type(exc).__name__}: {exc} (params={params})"

    if state.model_dump() != before:
        return FAIL, "play_action_card zmutowało stan wejściowy (nie jest czystą funkcją)"
    if card_id in new.players["p1"].private.action_cards:
        return FAIL, "karta nadal w ręce po zagraniu"
    if card_id not in new.decks.action_card_discard:
        return FAIL, "karta nie trafiła na stos odrzuconych"
    if is_action and not new.players["p1"].took_action_this_turn:
        return FAIL, "karta ACTION nie zużyła akcji tury"
    try:
        GameState.model_validate_json(new.model_dump_json())
    except Exception as exc:  # noqa: BLE001
        return FAIL, f"stan po zagraniu nie przechodzi serializacji: {exc}"
    return None


# ----------------------------------------------------------------------------- testy


def test_talia_ma_140_kart(card_ids: list[str]) -> None:
    assert len(card_ids) == 140


def _all_ids() -> list[str]:
    return deck_card_ids(StaticDataRegistry(), "action_card")


@pytest.mark.parametrize("card_id", _all_ids())
def test_karta_akcji_smoke(
    registry: StaticDataRegistry, card_ids: list[str], card_id: str
) -> None:
    row = _check_card(registry, card_id, card_ids)
    _ROWS[card_id] = row
    if row.status in {FAIL, CRASH}:
        pytest.fail(f"{row.name} ({card_id}): {row.status} - {row.detail}")
    if row.status != OK:
        pytest.skip(f"{row.name} ({card_id}): {row.status} - {row.detail}")
