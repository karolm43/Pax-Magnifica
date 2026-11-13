"""Projekcja fazy agendy do web-data (RULES.md 51) - klucz ``agendaPhase``.

Wszystko tu jest JAWNE: agenda, oddane głosy i stan planet są publiczne (głosy ogłasza się
na głos - R_agenda_phase). Klucze graczy to ``player_id`` (``discordId`` w ``playerData``).
"""

from __future__ import annotations

from typing import Any

from src.core import agenda_phase
from src.core.components import ComponentCategory
from src.core.game_state import AgendaStep, GameState, Phase
from src.core.registry import StaticDataRegistry

# Podfaza kontraktu frontendu (``GamePhase``) wg kroku fazy agendy.
_WEB_PHASE_BY_STEP: dict[AgendaStep, str] = {
    AgendaStep.REVEAL: "agenda.readyToFlip",
    AgendaStep.VOTE: "agenda.voting",
    AgendaStep.TIEBREAK: "agenda.resolving",
    AgendaStep.COUNTED: "agenda.resolving",
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


def build_predictions(state: GameState, registry: StaticDataRegistry) -> list[dict[str, Any]]:
    """Zagrane riders bieżącej agendy: kto, jaką kartą i NA JAKI WYNIK (przewidywanie jest jawne -
    „predict aloud", C_action_cards). Kolejność zagrania."""
    from src.core.hooks import reactions_agenda  # lokalnie: hooki ładują się leniwie

    agenda = state.agenda
    found: list[dict[str, Any]] = []
    for pid in state.players:
        for card, outcome in reactions_agenda.predictions(state, pid):
            definition = registry.catalog.get(ComponentCategory.ACTION_CARD, card)
            found.append(
                {
                    "playerId": pid,
                    "card": card,
                    "cardName": getattr(definition, "name", None) or card,
                    "outcome": outcome,
                    "outcomeLabel": _outcome_info(
                        state, registry, agenda.kind if agenda is not None else "", outcome
                    ),
                }
            )
    order = {e.key: i for i, e in enumerate(state.active_effects)}
    return sorted(found, key=lambda f: order.get(f"action_cards:{f['card']}", 0))


def covert_for_viewer(
    state: GameState, registry: StaticDataRegistry, viewer: str | None
) -> dict[str, Any] | None:
    """Ukryta agenda Covert Legislation - widzi ją tylko mówca (C_agendas)."""
    agenda = state.agenda
    if agenda is None or agenda.covert_card is None or viewer != state.speaker_id:
        return None
    return _card(registry, agenda.covert_card)


def revealed_secrets(state: GameState) -> dict[str, list[str]]:
    """Search Warrant: właściciel gra z JAWNYMI tajnymi celami (``{player_id: [cele]}``)."""
    from src.core.hooks import agendas_laws  # lokalnie: hooki ładują się leniwie

    found = {pid: agendas_laws.revealed_secrets(state, pid) for pid in state.players}
    return {pid: cards for pid, cards in found.items() if cards}


def with_revealed_secrets(
    players: list[dict[str, Any]], state: GameState
) -> list[dict[str, Any]]:
    """Search Warrant: niezdobyte tajne cele właściciela jawne w ``knownUnscoredSecrets``."""
    revealed = revealed_secrets(state)
    for entry in players:
        cards = revealed.get(str(entry.get("discordId")))
        if cards:
            entry["knownUnscoredSecrets"] = {sid: 1 for sid in cards}
            entry["numUnscoredSecrets"] = len(cards)
    return players


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
            # Representative Government: dokładnie 1 głos, bez planet i dodatkowych głosów.
            "singleVote": agenda_phase.single_vote(state, pid),
            # Predictive Intelligence: posiadana / gotowa (opcjonalne +3 głosy, decyzja gracza).
            "predictive": {
                "owned": agenda_phase.PREDICTIVE_INTELLIGENCE in state.players[pid].technologies,
                "ready": agenda_phase.predictive_ready(state, pid),
                "votes": agenda_phase.PREDICTIVE_VOTES,
            },
        }
    return {
        "step": agenda.step.value,
        "agendaNumber": agenda.agenda_number,
        "totalAgendas": agenda_phase.AGENDAS_PER_PHASE,
        "card": _card(registry, agenda.agenda_id),
        # Covert Legislation: głosuje się nad ukrytą agendą (treść widzi tylko mówca).
        "covert": agenda.covert_card is not None,
        # Riders zagrane na tę agendę (kto, czym i na jaki wynik) - jawne.
        "predictions": build_predictions(state, registry),
        # Miscount Disclosed: prawo, nad którym głosuje się ponownie po „dalej".
        "revoteLaw": agenda.revote_law,
        # Gracze bez prawa głosu do końca fazy (Public Execution).
        "phaseBlocked": list(agenda.phase_blocked),
        "kind": agenda.kind,
        "outcomes": list(agenda.outcomes),
        "unresolvable": agenda.unresolvable,
        "speakerId": state.speaker_id,
        # Przed ujawnieniem agendy kolejność jeszcze nie jest zapisana - pokaż podgląd, żeby
        # Senat od początku miał wszystkich (a nie samego mówcę).
        "voteOrder": list(agenda.vote_order) or agenda_phase.vote_order(state),
        "currentVoter": agenda_phase.current_voter(state),
        "votes": {
            pid: {
                "outcome": v.outcome,
                "votes": v.votes,
                "planets": list(v.planets),
                "techs": list(v.techs),
            }
            for pid, v in agenda.votes.items()
        },
        "abstained": list(agenda.abstained),
        "blocked": list(agenda.blocked),
        "tied": list(agenda.tied),
        "totals": agenda_phase.totals(agenda),
        "resolvedOutcome": agenda.resolved_outcome,
        "decidedBySpeaker": agenda.decided_by_speaker,
        # Krok COUNTED: wynik policzony, czeka na reakcje i potwierdzenie mówcy (/agenda/confirm).
        "pendingOutcome": agenda.pending_outcome,
        "lastVoteBy": agenda.last_vote_by,
        "voters": voters,
        "history": list(agenda.history),
        "lawsInPlay": dict(state.decks.agenda_laws),
        "deckSize": len(state.decks.agenda_deck),
        "deckSeeded": state.decks.agenda_deck_seeded,
        "discardSize": len(state.decks.agenda_discard),
    }
