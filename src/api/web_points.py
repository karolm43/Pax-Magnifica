"""Punkty zwycięstwa w web-data: „Other points" i tor punktów gracza (``WebScoreBreakdown``).

Źródłem są zapisy silnika: cele publiczne (``objectives.scored``), tajne
(``scored_secrets``), żeton Custodians (``scored["custodians"]``) i rejestr VP spoza kart
(``objectives.point_sources`` - relikty, agendy, Styx, Support for the Throne, Imperial...).
Różnica między ``victory_points`` a sumą znanych źródeł (np. edycja God-Mode) idzie jako
wpis „OTHER", żeby tor zawsze sumował się do wyniku gracza.

Stany wpisów (kontrakt viewera): ``SCORED`` (zdobyte), ``QUALIFIES`` (można zdobyć teraz),
``POTENTIAL`` (możliwe później). ``losable`` = punkt, który można jeszcze stracić.
"""

from __future__ import annotations

from typing import Any

from src.core import objective_progress
from src.core import objectives as obj
from src.core.custodians import SCORE_KEY as CUSTODIANS_KEY
from src.core.game_state import GameState, PlayerState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards.imperial import INITIATIVE as IMPERIAL_INITIATIVE
from src.core.strategy_cards.imperial import controls_mecatol
from src.core.system_planets import planets_of_system

# Typ żetonu na torze (``EntryType`` frontu) wg źródła; reszta: agendy/karty => AGENDA.
_ENTRY_TYPES: dict[str, str] = {
    CUSTODIANS_KEY: "CUSTODIAN",
    obj.SOURCE_IMPERIAL: "IMPERIAL",
    obj.SOURCE_SFTT: "SFTT",
    "relics:emphidia": "CROWN",
    "relics:bookoflatvinia": "LATVINIA",
    "relics:shard": "SHARD",
    "relics:thesilverflame": "RELIC",
    "planets:styx": "STYX",
}
_FIXED_NAMES: dict[str, str] = {
    CUSTODIANS_KEY: "Custodians Token",
    obj.SOURCE_IMPERIAL: "Imperial (Mecatol Rex)",
    obj.SOURCE_SFTT: "Support for the Throne",
}
# Relikty dające VP (zdobyte/trzymane = źródło widoczne w „Other points").
_VP_RELICS = ("shard", "emphidia", "bookoflatvinia", "thesilverflame")
_STYX = "styx"


def source_name(registry: StaticDataRegistry, source: str) -> str:
    """Pełna nazwa źródła punktu z danych (nigdy surowe id)."""
    if source in _FIXED_NAMES:
        return _FIXED_NAMES[source]
    category, _, component_id = source.partition(":")
    if category == "planets":
        planet = registry.planets.get(component_id)
        return planet.name if planet is not None and planet.name else component_id
    from src.core.components import ComponentCategory  # lokalnie: lekki import

    try:
        card = registry.catalog.get(ComponentCategory(category), component_id)
    except ValueError:
        card = None
    name = getattr(card, "name", None)
    return str(name) if name else component_id


def _entry_type(source: str) -> str:
    if source in _ENTRY_TYPES:
        return _ENTRY_TYPES[source]
    return "RELIC" if source.startswith("relics:") else "AGENDA"


def _ledger(state: GameState) -> dict[str, dict[str, int]]:
    """Rejestr źródeł VP z żetonem Custodians (zapisywanym listą w ``scored``)."""
    ledger = {
        source: dict(points)
        for source, points in state.objectives.point_sources.items()
        if source != CUSTODIANS_KEY
    }
    custodians: dict[str, int] = {}
    worth = state.objectives.custom_points.get(CUSTODIANS_KEY, 1)
    for pid in state.objectives.scored.get(CUSTODIANS_KEY, []):
        custodians[pid] = custodians.get(pid, 0) + worth
    return {CUSTODIANS_KEY: custodians, **ledger}


def _styx_on_map(state: GameState, registry: StaticDataRegistry) -> bool:
    return any(
        _STYX in planets_of_system(state, registry, position) for position in state.systems
    )


def _visible_sources(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Źródła VP na stole: zawsze Custodians i Imperial, Styx na mapie, relikty z VP u graczy,
    plus wszystko, co już dało komuś punkt (rejestr)."""
    sources = [CUSTODIANS_KEY, obj.SOURCE_IMPERIAL]
    if _styx_on_map(state, registry):
        sources.append(f"planets:{_STYX}")
    held = {relic for player in state.players.values() for relic in player.relics}
    sources += [f"relics:{relic}" for relic in _VP_RELICS if relic in held]
    sources += list(state.objectives.point_sources)
    return list(dict.fromkeys(sources))


def other_point_rows(
    state: GameState, registry: StaticDataRegistry, entity_keys: dict[str, str]
) -> list[dict[str, Any]]:
    """Wiersze „Other points": każde źródło VP spoza kart celów i kto ile z niego ma."""
    ledger = _ledger(state)
    rows: list[dict[str, Any]] = []
    for source in _visible_sources(state, registry):
        points = {
            entity_keys.get(pid, pid): net
            for pid, net in ledger.get(source, {}).items()
            if pid in state.players and net
        }
        scored = [faction for faction, net in points.items() for _ in range(max(net, 0))]
        rows.append({
            "key": source,
            "name": source_name(registry, source),
            "pointValue": state.objectives.custom_points.get(source, 1),
            "revealed": True,
            "scoredFactions": scored,
            "factionPoints": points,
            "losable": source in obj.LOSABLE_POINT_SOURCES,
            "peekingFactions": [],
            "multiScoring": True,
            "hasRedTape": False,
            "progressThreshold": 0,
            "factionProgress": {},
        })
    return rows


def _entry(
    entry_type: str,
    state_label: str,
    points: int,
    description: str,
    *,
    objective_key: str | None = None,
    losable: bool = False,
    progress: tuple[int, int] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "type": entry_type,
        "description": description,
        "state": state_label,
        "losable": losable,
        "pointValue": points,
    }
    if objective_key is not None:
        entry["objectiveKey"] = objective_key
        if entry_type == "AGENDA":
            entry["agendaKey"] = objective_key
    if progress is not None:
        entry["currentProgress"], entry["totalProgress"] = progress
    return entry


def _objective_type(registry: StaticDataRegistry, objective_id: str) -> str:
    return "PO_2" if obj.objective_stage(registry, objective_id) == 2 else "PO_1"


def _points(registry: StaticDataRegistry, objective_id: str) -> int:
    definition = obj.objective_def(registry, objective_id)
    return definition.points if definition and definition.points else 1


def _name(registry: StaticDataRegistry, objective_id: str) -> str:
    definition = obj.objective_def(registry, objective_id)
    return (definition.name if definition and definition.name else None) or objective_id


def _scored_entries(
    state: GameState, registry: StaticDataRegistry, player_id: str, player: PlayerState
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for oid in state.objectives.revealed:
        if player_id in state.objectives.scored.get(oid, []):
            entries.append(_entry(_objective_type(registry, oid), "SCORED",
                                  _points(registry, oid), _name(registry, oid), objective_key=oid))
    for oid in player.scored_secrets:
        entries.append(_entry("SECRET", "SCORED", _points(registry, oid),
                              _name(registry, oid), objective_key=oid))
    for source, points in _ledger(state).items():
        net = points.get(player_id, 0)
        key = source.partition(":")[2] or source
        for _ in range(max(net, 0)):
            entries.append(_entry(
                _entry_type(source), "SCORED", 1, source_name(registry, source),
                objective_key=key if _entry_type(source) == "AGENDA" else None,
                losable=source in obj.LOSABLE_POINT_SOURCES,
            ))
    # Punkty bez znanego źródła (edycja God-Mode) - tor sumuje się do wyniku gracza.
    unexplained = player.victory_points - sum(e["pointValue"] for e in entries)
    for _ in range(max(unexplained, 0)):
        entries.append(_entry("OTHER", "SCORED", 1, "Points without a recorded source"))
    return entries


def _objective_chances(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid, player_id: str,
    player: PlayerState,
) -> list[dict[str, Any]]:
    """Cele, których gracz jeszcze nie zdobył: gotowe teraz albo możliwe (z postępem)."""
    entries: list[dict[str, Any]] = []
    ready_public = set(obj.scoreable_public_objectives(state, registry, grid, player_id))
    for oid in state.objectives.revealed:
        if obj.has_scored_public(state, player_id, oid) or obj.is_retired(state, oid):
            continue
        if obj.objective_def(registry, oid) is None:
            continue
        value, goal, _ok = objective_progress.evaluate(state, registry, grid, player_id, oid)
        progress = (value, goal) if value is not None and goal > 0 else None
        entries.append(_entry(
            _objective_type(registry, oid),
            "QUALIFIES" if oid in ready_public else "POTENTIAL",
            _points(registry, oid), _name(registry, oid), objective_key=oid, progress=progress,
        ))
    # Tajne cele: własne (projekcja viewera) z nazwą, cudze tylko jako liczba.
    ready_secret = set(obj.scoreable_secret_objectives(state, registry, grid, player_id))
    for oid in player.private.secret_objectives:
        entries.append(_entry(
            "SECRET", "QUALIFIES" if oid in ready_secret else "POTENTIAL",
            _points(registry, oid), _name(registry, oid), objective_key=oid,
        ))
    if not player.private.secret_objectives:
        hidden = player.hidden_card_counts.get("secret_objectives", 0)
        entries += [_entry("SECRET", "POTENTIAL", 1, "Drawn Secret") for _ in range(hidden)]
    return entries


def _other_chances(
    state: GameState, registry: StaticDataRegistry, player_id: str, player: PlayerState
) -> list[dict[str, Any]]:
    """Punkty spoza celów, które gracz może jeszcze zdobyć (Custodians, Imperial, relikty)."""
    entries: list[dict[str, Any]] = []
    if not state.custodians_removed:
        entries.append(_entry("CUSTODIAN", "POTENTIAL", 1, "Custodians Token"))
    holds_imperial = (
        IMPERIAL_INITIATIVE in player.strategy_cards
        and IMPERIAL_INITIATIVE not in player.exhausted_strategy_cards
    )
    if holds_imperial:
        entries.append(_entry(
            "IMPERIAL", "QUALIFIES" if controls_mecatol(state, player_id) else "POTENTIAL", 1,
            source_name(registry, obj.SOURCE_IMPERIAL),
        ))
    for relic in ("emphidia", "bookoflatvinia", "thesilverflame"):
        if relic in player.relics:
            source = f"relics:{relic}"
            entries.append(
                _entry(_entry_type(source), "POTENTIAL", 1, source_name(registry, source))
            )
    return entries


def _player_breakdown(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid, player_id: str,
    player: PlayerState,
) -> dict[str, Any]:
    """Wpisy toru punktów jednego gracza: zdobyte, potem gotowe, potem możliwe."""
    chances = [
        *_objective_chances(state, registry, grid, player_id, player),
        *_other_chances(state, registry, player_id, player),
    ]
    ready = [e for e in chances if e["state"] == "QUALIFIES"]
    later = [e for e in chances if e["state"] != "QUALIFIES"]
    return {"entries": [*_scored_entries(state, registry, player_id, player), *ready, *later]}


def build_score_breakdowns(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    entity_keys: dict[str, str],
) -> dict[str, Any]:
    """Rozbicie punktów per gracz (klucz = tożsamość frakcji jak w ``playerData``)."""
    return {
        entity_keys.get(pid, pid): _player_breakdown(state, registry, grid, pid, player)
        for pid, player in sorted(state.players.items())
    }
