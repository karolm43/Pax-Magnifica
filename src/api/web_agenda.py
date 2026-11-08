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
        "text1": getattr(definition, "text1", None),
        "text2": getattr(definition, "text2", None),
    }


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
