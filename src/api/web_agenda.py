"""Projekcja fazy agendy do web-data (RULES.md 51) - klucz ``agendaPhase``.

Wszystko tu jest JAWNE: agenda, oddane głosy i stan planet są publiczne (głosy ogłasza się
na głos - R_agenda_phase). Klucze graczy to ``player_id`` (``discordId`` w ``playerData``).
"""

from __future__ import annotations

from typing import Any

from src.core import agenda_phase
from src.core.game_state import AgendaStep, GameState, Phase
from src.core.registry import StaticDataRegistry

# Podfaza kontraktu frontendu (``GamePhase``) wg kroku fazy agendy.
_WEB_PHASE_BY_STEP: dict[AgendaStep, str] = {
    AgendaStep.REVEAL: "agenda.readyToFlip",
    AgendaStep.VOTE: "agenda.voting",
    AgendaStep.TIEBREAK: "agenda.resolving",
    AgendaStep.RESOLVED: "agenda.resolving",
    AgendaStep.COMPLETE: "agenda.resolving",
}


def web_phase(state: GameState) -> str | None:
    """Podfaza agendy dla frontendu albo ``None`` poza zainicjowaną fazą agendy."""
    if state.phase is not Phase.AGENDA or state.agenda is None:
        return None
    return _WEB_PHASE_BY_STEP[state.agenda.step]


def _card(registry: StaticDataRegistry, agenda_id: str | None) -> dict[str, Any] | None:
    if agenda_id is None:
        return None
    definition = agenda_phase.agenda_def(registry, agenda_id)
    return {
        "id": agenda_id,
        "name": getattr(definition, "name", agenda_id),
        "type": getattr(definition, "type", None),
        "target": getattr(definition, "target", None),
        "text1": _text(definition, "text1"),
        "text2": _text(definition, "text2"),
    }


def _text(definition: object, key: str) -> str | None:
    """Tekst karty z ``texts`` (alias/text1/text2/mapText są tam, nie jako pola modelu)."""
    texts = getattr(definition, "texts", None) or {}
    value = texts.get(key)
    return value if isinstance(value, str) and value.strip() else None


def _outcome_info(
    state: GameState, registry: StaticDataRegistry, kind: str, outcome: str
) -> str:
    """Czytelny opis wyniku dla listy praw (gracz/planeta/karta strategii/prawo)."""
    if outcome == "for":
        return "For"
    if outcome == "against":
        return "Against"
    if kind in ("planet", "planet_non_home", "planet_non_home_not_mecatol"):
        planet = registry.planets.get(outcome)
        return planet.name if planet is not None else outcome
    if kind == "law":
        other = agenda_phase.agenda_def(registry, outcome)
        return other.name or outcome if other is not None else outcome
    return outcome.replace("_", " ").title() if outcome not in state.players else outcome


def build_laws_in_play(
    state: GameState, registry: StaticDataRegistry, entity_keys: dict[str, str]
) -> list[dict[str, Any]]:
    """Prawa w grze w kontrakcie ``LawInPlay`` (panel General, `LawCard`)."""
    laws: list[dict[str, Any]] = []
    for index, (card, outcome) in enumerate(state.decks.agenda_laws.items()):
        definition = agenda_phase.agenda_def(registry, card)
        target = (definition.target if definition is not None else None) or ""
        kind = agenda_phase.classify_target(target)
        owner = agenda_phase.law_owner(state, registry, card)
        laws.append(
            {
                "id": card,
                "name": (definition.name if definition is not None else None) or card,
                "uniqueId": index + 1,
                "type": (definition.type if definition is not None else None) or "Law",
                "target": target,
                "text1": _text(definition, "text1") or "",
                "text2": _text(definition, "text2") or "",
                "mapText": _text(definition, "mapText") or "",
                "electedInfo": None if owner is not None else _outcome_info(
                    state, registry, kind, outcome
                ),
                "electedFaction": entity_keys.get(owner, owner) if owner is not None else None,
                "electedType": "player" if owner is not None else kind,
                "controlTokens": [],
                "displaysElectedFaction": owner is not None,
            }
        )
    return laws


def build_agenda_payload(state: GameState, registry: StaticDataRegistry) -> dict[str, Any] | None:
    """Stan fazy agendy dla panelu (``None`` poza zainicjowaną fazą agendy)."""
    agenda = state.agenda
    if agenda is None or state.phase is not Phase.AGENDA:
        return None
    voters: dict[str, dict[str, Any]] = {}
    for pid in state.players:
        planets = agenda_phase.voting_planets(state, registry, pid)
        ready = sum(int(p["influence"]) for p in planets if not p["exhausted"])
        voters[pid] = {
            "planets": planets,
            "available": ready,
            "total": sum(int(p["influence"]) for p in planets),
            "extra": agenda_phase.extra_votes(state, registry, pid),
        }
    return {
        "step": agenda.step.value,
        "agendaNumber": agenda.agenda_number,
        "totalAgendas": agenda_phase.AGENDAS_PER_PHASE,
        "card": _card(registry, agenda.agenda_id),
        "kind": agenda.kind,
        "outcomes": list(agenda.outcomes),
        "unresolvable": agenda.unresolvable,
        "speakerId": state.speaker_id,
        "voteOrder": list(agenda.vote_order),
        "currentVoter": agenda_phase.current_voter(state),
        "votes": {
            pid: {"outcome": v.outcome, "votes": v.votes, "planets": list(v.planets)}
            for pid, v in agenda.votes.items()
        },
        "abstained": list(agenda.abstained),
        "blocked": list(agenda.blocked),
        "tied": list(agenda.tied),
        "totals": agenda_phase.totals(agenda),
        "resolvedOutcome": agenda.resolved_outcome,
        "decidedBySpeaker": agenda.decided_by_speaker,
        "voters": voters,
        "history": list(agenda.history),
        "lawsInPlay": dict(state.decks.agenda_laws),
        "deckSize": len(state.decks.agenda_deck),
        "deckSeeded": state.decks.agenda_deck_seeded,
        "discardSize": len(state.decks.agenda_discard),
    }
