"""Cele i stan fazy statusu w dokumencie web-data (kontrakt viewera).

Port struktury AsyncTI4 ``WebObjectives`` (tabele celów I/II etapu + „inne punkty" z
``web_points``; tam też tor punktów ``WebScoreBreakdown``). Nasze rozszerzenie kontraktu:
``gameState.status`` — stan kroków fazy statusu dla panelu (RULES.md 41).

Wejściem jest PROJEKCJA stanu (``project_for_viewer``): cudze tajne cele są już
zredagowane do liczników, więc nic nie ujawniamy. Zakryte cele publiczne występują tylko
jako anonimowe wpisy ``UNREVEALED_*`` (bez id karty).
"""

from __future__ import annotations

from typing import Any

from src.api import web_points
from src.core import deck_piles, fleet_pool, objective_payment, objective_progress
from src.core import objectives as obj
from src.core.game_state import GameState, PlayerState, StatusStep
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

# Limit tajnych celów (zdobytych + niezdobytych) — R_objective_cards: „up to three total".
SECRET_LIMIT = 3


def _name_of(registry: StaticDataRegistry, objective_id: str) -> str:
    definition = obj.objective_def(registry, objective_id)
    return (definition.name if definition and definition.name else None) or objective_id


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
    grid: HexGrid,
    objective_id: str,
    entity_keys: dict[str, str],
) -> dict[str, Any]:
    definition = obj.objective_def(registry, objective_id)
    goal = objective_progress.threshold(objective_id, state)
    progress: dict[str, int] = {}
    if goal > 0:
        for pid in state.players:
            value = objective_progress.progress(state, registry, grid, pid, objective_id)
            if value is None:
                progress = {}
                goal = 0  # warunek niemodelowany — bez miernika postępu
                break
            progress[entity_keys.get(pid, pid)] = value
    return {
        "key": objective_id,
        "name": _name_of(registry, objective_id),
        "pointValue": (definition.points if definition and definition.points else 1),
        "revealed": True,
        "scoredFactions": _scored_factions(state, objective_id, entity_keys),
        "peekingFactions": [],
        "multiScoring": False,
        "hasRedTape": False,
        "progressThreshold": goal,
        "factionProgress": progress,
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
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    entity_keys: dict[str, str],
) -> dict[str, Any]:
    """Struktura ``Objectives``: odkryte cele z podziałem na etapy + zakryte placeholdery."""
    state_obj = state.objectives
    stage1 = [
        _objective_entry(state, registry, grid, oid, entity_keys)
        for oid in state_obj.revealed
        if obj.objective_stage(registry, oid) == 1
    ]
    stage2 = [
        _objective_entry(state, registry, grid, oid, entity_keys)
        for oid in state_obj.revealed
        if obj.objective_stage(registry, oid) == 2
    ]
    stage1 += [_hidden_entry(1, i, 1) for i, _ in enumerate(state_obj.stage1_deck)]
    stage2 += [_hidden_entry(2, i, 2) for i, _ in enumerate(state_obj.stage2_deck)]
    # „Inne punkty": każde źródło VP spoza kart celów (RULES.md 41; web_points).
    custom = web_points.other_point_rows(state, registry, entity_keys)
    return {
        "stage1Objectives": stage1,
        "stage2Objectives": stage2,
        "customObjectives": custom,
        "allObjectives": [*stage1, *stage2, *custom],
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
    state: GameState, registry: StaticDataRegistry, grid: HexGrid
) -> dict[str, Any] | None:
    """Stan kroków fazy statusu dla panelu (``None`` poza zainicjowaną fazą statusu).

    Klucze graczy to ``player_id`` (``discordId`` w ``playerData``) — adresują wywołania API.
    ``scoreablePublic`` liczymy dla wszystkich; ``scoreableSecret`` zawiera tylko tajne cele
    widoczne w projekcji (czyli ręki viewera), cudze są puste.
    """
    status = state.status
    if status is None:
        return None

    def option(pid: str, oid: str) -> dict[str, Any]:
        value, goal, ok = objective_progress.evaluate(state, registry, grid, pid, oid)
        return {
            "key": oid,
            "progress": value,
            "threshold": goal,
            # Cel publiczny wymaga też kontroli planet domowych (R_status_phase, Notes).
            "ready": ok
            and (
                oid not in state.objectives.revealed
                or obj.controls_home_planets(state, registry, pid)
            ),
            "manual": value is None,
            # Koszt celów „Spend…" (co można wydać + podpowiedź silnika) dla okna płatności.
            "spend": objective_payment.spend_spec(state, registry, grid, pid, oid),
        }

    def public_options(pid: str) -> list[dict[str, Any]]:
        return [
            option(pid, oid)
            for oid in state.objectives.revealed
            if not obj.has_scored_public(state, pid, oid)
            and (d := obj.objective_def(registry, oid)) is not None
            and d.phase == obj.STATUS_PHASE_LABEL
        ]

    def secret_options(pid: str) -> list[dict[str, Any]]:
        return [
            option(pid, oid)
            for oid in state.players[pid].private.secret_objectives
            if (d := obj.objective_def(registry, oid)) is not None
            and d.phase == obj.STATUS_PHASE_LABEL
        ]

    return {
        "publicOptions": {pid: public_options(pid) for pid in state.players},
        "secretOptions": {pid: secret_options(pid) for pid in state.players},
        "homeControlled": {
            pid: obj.controls_home_planets(state, registry, pid) for pid in state.players
        },
        "step": status.step.value,
        "scoredPublic": list(status.scored_public),
        "scoredSecret": list(status.scored_secret),
        "done": list(status.done),
        "unassignedCc": dict(status.unassigned_cc),
        "fleetExcess": {pid: dict(v) for pid, v in status.fleet_excess.items()},
        # Statki liczone do fleet pool per system — podgląd przy zmianie puli floty (RULES.md 42).
        "fleetShips": {pid: fleet_pool.ships_by_system(state, pid) for pid in state.players},
        "scoreablePublic": {
            pid: obj.scoreable_public_objectives(state, registry, grid, pid)
            for pid in state.players
        },
        "scoreableSecret": {
            pid: obj.scoreable_secret_objectives(state, registry, grid, pid)
            for pid in state.players
        },
        "log": list(status.log),
        "isComplete": status.step is StatusStep.COMPLETE,
        "custodiansRemoved": state.custodians_removed,
    }


def card_pool_counts(state: GameState, registry: StaticDataRegistry) -> dict[str, Any]:
    """Stan talii do ``cardPool``: rozmiary oraz zawartość talii, odrzuconych i purge.

    Listy kart w talii są SORTOWANE (nie ujawniają kolejności); wierzch talii eksploracji
    idzie osobno w ``exploreTop`` (używa go tylko tryb debug). Talia eksploracji jeszcze
    niezasiana = pełna pula.
    """
    explore_keys = {
        "cultural": "culturalExplore",
        "hazardous": "hazardousExplore",
        "industrial": "industrialExplore",
        "frontier": "frontierExplore",
    }
    pool: dict[str, Any] = {
        "secretObjectiveDeckSize": len(state.decks.secret_objective_deck),
        "actionCardDeckSize": len(state.decks.action_card_deck),
        "actionCardDiscardSize": len(state.decks.action_card_discard),
        "actionCardDeck": sorted(state.decks.action_card_deck),
        "actionCardDiscard": list(state.decks.action_card_discard),
        "purgedCards": list(state.decks.purged),
        # FAN-AGENDAS: wariant talii agend ("standard" / "absol") - front pokazuje właściwą pulę.
        "agendaVariant": state.decks.agenda_variant,
    }
    top: dict[str, str] = {}
    for deck, prefix in explore_keys.items():
        piles = deck_piles.explore_piles(state, registry, deck)
        pool[f"{prefix}Deck"] = sorted(piles.deck)
        pool[f"{prefix}Discard"] = list(piles.discard)
        if piles.deck:
            top[deck] = piles.deck[0]
    pool["exploreTop"] = top
    return pool
