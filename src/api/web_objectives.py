"""Cele, rozbicie punktów i stan fazy statusu w dokumencie web-data (kontrakt viewera).

Porty struktur AsyncTI4: ``WebObjectives`` (tabele celów I/II etapu + „inne punkty") i
``WebScoreBreakdown`` (żetony punktów na torze, wg gracza). Nasze rozszerzenie kontraktu:
``gameState.status`` — stan kroków fazy statusu dla panelu (RULES.md 41).

Wejściem jest PROJEKCJA stanu (``project_for_viewer``): cudze tajne cele są już
zredagowane do liczników, więc nic nie ujawniamy. Zakryte cele publiczne występują tylko
jako anonimowe wpisy ``UNREVEALED_*`` (bez id karty).
"""

from __future__ import annotations

from typing import Any

from src.core import objectives as obj
from src.core.game_state import GameState, PlayerState, StatusStep
from src.core.registry import StaticDataRegistry

# Limit tajnych celów (zdobytych + niezdobytych) — R_objective_cards: „up to three total".
SECRET_LIMIT = 3
# Etykiety „innych punktów" (poza kartami celów). Klucz → wyświetlana nazwa.
_CUSTOM_LABELS: dict[str, str] = {"custodians": "Custodians Token"}


def _name_of(registry: StaticDataRegistry, objective_id: str) -> str:
    definition = obj.objective_def(registry, objective_id)
    return (definition.name if definition and definition.name else None) or objective_id


def _points(registry: StaticDataRegistry, objective_id: str) -> int:
    definition = obj.objective_def(registry, objective_id)
    return definition.points if definition and definition.points else 1


def _scored_factions(
    state: GameState, objective_id: str, entity_keys: dict[str, str]
) -> list[str]:
    return [
        entity_keys.get(pid, pid)
        for pid in state.objectives.scored.get(objective_id, [])
        if pid in state.players
    ]


def _objective_entry(
    state: GameState,
    registry: StaticDataRegistry,
    objective_id: str,
    entity_keys: dict[str, str],
) -> dict[str, Any]:
    definition = obj.objective_def(registry, objective_id)
    return {
        "key": objective_id,
        "name": _name_of(registry, objective_id),
        "pointValue": (definition.points if definition and definition.points else 1),
        "revealed": True,
        "scoredFactions": _scored_factions(state, objective_id, entity_keys),
        "peekingFactions": [],
        "multiScoring": False,
        "hasRedTape": False,
        # Postęp względem wymagań karty nie jest jeszcze liczony (RULES.md 41.4).
        "progressThreshold": 0,
        "factionProgress": {},
    }


def _hidden_entry(stage: int, index: int, points: int) -> dict[str, Any]:
    return {
        "key": f"UNREVEALED_{stage}_{index}",
        "name": "UNREVEALED",
        "pointValue": points,
        "revealed": False,
        "scoredFactions": [],
        "peekingFactions": [],
        "multiScoring": False,
        "hasRedTape": False,
        "progressThreshold": 0,
        "factionProgress": {},
    }


def build_objectives(
    state: GameState, registry: StaticDataRegistry, entity_keys: dict[str, str]
) -> dict[str, Any]:
    """Struktura ``Objectives``: odkryte cele z podziałem na etapy + zakryte placeholdery."""
    state_obj = state.objectives
    stage1 = [
        _objective_entry(state, registry, oid, entity_keys)
        for oid in state_obj.revealed
        if obj.objective_stage(registry, oid) == 1
    ]
    stage2 = [
        _objective_entry(state, registry, oid, entity_keys)
        for oid in state_obj.revealed
        if obj.objective_stage(registry, oid) == 2
    ]
    stage1 += [_hidden_entry(1, i, 1) for i, _ in enumerate(state_obj.stage1_deck)]
    stage2 += [_hidden_entry(2, i, 2) for i, _ in enumerate(state_obj.stage2_deck)]
    custom = [
        {
            "key": key,
            "name": _CUSTOM_LABELS.get(key, key),
            "pointValue": points,
            "revealed": True,
            "scoredFactions": _scored_factions(state, key, entity_keys),
            "peekingFactions": [],
            "multiScoring": True,
            "hasRedTape": False,
            "progressThreshold": 0,
            "factionProgress": {},
        }
        for key, points in state_obj.custom_points.items()
    ]
    return {
        "stage1Objectives": stage1,
        "stage2Objectives": stage2,
        "customObjectives": custom,
        "allObjectives": [*stage1, *stage2, *custom],
    }


def _entry(
    entry_type: str,
    state_label: str,
    points: int,
    description: str,
    objective_key: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "type": entry_type,
        "description": description,
        "state": state_label,
        "losable": False,
        "pointValue": points,
    }
    if objective_key is not None:
        entry["objectiveKey"] = objective_key
    return entry


def _player_breakdown(
    state: GameState, registry: StaticDataRegistry, player_id: str, player: PlayerState
) -> dict[str, Any]:
    """Wpisy toru punktów jednego gracza: zdobyte, potem możliwe (jak ``WebScoreBreakdown``)."""
    entries: list[dict[str, Any]] = []
    scored_public = [
        oid
        for oid in state.objectives.revealed
        if player_id in state.objectives.scored.get(oid, [])
    ]
    for oid in scored_public:
        stage = obj.objective_stage(registry, oid)
        definition = obj.objective_def(registry, oid)
        points = definition.points if definition and definition.points else 1
        entries.append(
            _entry("PO_2" if stage == 2 else "PO_1", "SCORED", points,
                   _name_of(registry, oid), oid)
        )
    for oid in player.scored_secrets:
        definition = obj.objective_def(registry, oid)
        points = definition.points if definition and definition.points else 1
        entries.append(_entry("SECRET", "SCORED", points, _name_of(registry, oid), oid))
    for key, points in state.objectives.custom_points.items():
        times = state.objectives.scored.get(key, []).count(player_id)
        for _ in range(times):
            entries.append(
                _entry("CUSTODIAN" if key == "custodians" else "AGENDA", "SCORED",
                       points, _CUSTOM_LABELS.get(key, key))
            )

    # Możliwe punkty: jeden cel publiczny na fazę statusu (najwyżej punktowany) …
    candidates = obj.scoreable_public_objectives(state, registry, player_id)
    if candidates:
        best = max(
            candidates,
            key=lambda oid: (
                _points(registry, oid),
                -state.objectives.revealed.index(oid),
            ),
        )
        points = _points(registry, best)
        stage = obj.objective_stage(registry, best)
        entries.append(
            _entry("PO_2" if stage == 2 else "PO_1", "POTENTIAL", points,
                   _name_of(registry, best), best)
        )
    # … oraz tajne cele z ręki (treść ukryta do zdobycia — żadnego wycieku id).
    hidden = len(player.private.secret_objectives) or player.hidden_card_counts.get(
        "secret_objectives", 0
    )
    for _ in range(hidden):
        entries.append(_entry("SECRET", "POTENTIAL", 1, "Drawn Secret"))
    return {"entries": entries}


def build_score_breakdowns(
    state: GameState, registry: StaticDataRegistry, entity_keys: dict[str, str]
) -> dict[str, Any]:
    """Rozbicie punktów per gracz (klucz = tożsamość frakcji jak w ``playerData``)."""
    return {
        entity_keys.get(pid, pid): _player_breakdown(state, registry, pid, player)
        for pid, player in sorted(state.players.items())
    }


def secret_fields(player: PlayerState, registry: StaticDataRegistry) -> dict[str, Any]:
    """Pola tajnych celów w ``playerData``: zdobyte (jawne) i znane niezdobyte (viewer)."""
    del registry
    scored = {sid: index + 1 for index, sid in enumerate(player.scored_secrets)}
    known = {sid: 1 for sid in player.private.secret_objectives}
    return {
        "secretsScored": scored,
        "knownUnscoredSecrets": known,
        "numUnscoredSecrets": len(known) or player.hidden_card_counts.get(
            "secret_objectives", 0
        ),
        "numScoreableSecrets": SECRET_LIMIT,
    }


def build_status_payload(
    state: GameState, registry: StaticDataRegistry
) -> dict[str, Any] | None:
    """Stan kroków fazy statusu dla panelu (``None`` poza zainicjowaną fazą statusu).

    Klucze graczy to ``player_id`` (``discordId`` w ``playerData``) — adresują wywołania API.
    ``scoreablePublic`` liczymy dla wszystkich; ``scoreableSecret`` zawiera tylko tajne cele
    widoczne w projekcji (czyli ręki viewera), cudze są puste.
    """
    status = state.status
    if status is None:
        return None
    return {
        "step": status.step.value,
        "scoredPublic": list(status.scored_public),
        "scoredSecret": list(status.scored_secret),
        "done": list(status.done),
        "unassignedCc": dict(status.unassigned_cc),
        "fleetExcess": {pid: dict(v) for pid, v in status.fleet_excess.items()},
        "scoreablePublic": {
            pid: obj.scoreable_public_objectives(state, registry, pid)
            for pid in state.players
        },
        "scoreableSecret": {
            pid: obj.scoreable_secret_objectives(state, registry, pid)
            for pid in state.players
        },
        "log": list(status.log),
        "isComplete": status.step is StatusStep.COMPLETE,
        "custodiansRemoved": state.custodians_removed,
    }


def card_pool_counts(state: GameState) -> dict[str, int]:
    """Rozmiary talii (bez ujawniania zawartości) do ``cardPool``."""
    return {
        "secretObjectiveDeckSize": len(state.decks.secret_objective_deck),
        "actionCardDeckSize": len(state.decks.action_card_deck),
        "actionCardDiscardSize": len(state.decks.action_card_discard),
    }
