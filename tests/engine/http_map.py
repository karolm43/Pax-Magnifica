"""Akcja z katalogu bota → to samo żądanie HTTP, które wysyła UI (do testu zgodności).

Trzymane w testach, nie w ``src/engine/``: warstwa bota nie zna ``api/`` (RULES.md 65.1).
Każdy rodzaj z ``ACTION_KINDS`` MUSI mieć tu wpis (strażnik w ``test_actions_parity.py``).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.engine import actions as act

Body = dict[str, Any] | None


def _pid(a: Any) -> Body:
    return {"player_id": a.player_id}


def _losses(items: dict[str, int]) -> list[dict[str, Any]]:
    return [{"baseType": base, "count": n} for base, n in items.items()]


HTTP: dict[str, tuple[str, Callable[[Any], Body]]] = {
    "setup_secret": (
        "/setup/secret", lambda a: {"player_id": a.player_id, "objective_id": a.objective_id}
    ),
    "setup_custodians": ("/setup/custodians", _pid),
    "setup_reveal": ("/setup/reveal-objectives", _pid),
    "strategy_pick": (
        "/strategy/pick",
        lambda a: {"player_id": a.player_id, "initiative": a.initiative, "recipient": a.recipient},
    ),
    "strategy_play": (
        "/strategy/play", lambda a: {"player_id": a.player_id, "initiative": a.initiative}
    ),
    "strategy_primary_step": (
        "/strategy/primary-step", lambda a: {"player_id": a.player_id, "payload": a.payload}
    ),
    "strategy_secondary": (
        "/strategy/secondary",
        lambda a: {"player_id": a.player_id, "execute": a.execute, "payload": a.payload},
    ),
    "turn_pass": ("/turn/pass", _pid),
    "turn_end": ("/turn/end", _pid),
    "tactical_end": ("/tactical/end", lambda a: None),
    "phase_step": ("/turn/phase-step", _pid),
    "phase_next": ("/phase/next", _pid),
    "round_next": ("/round/next", lambda a: None),
    "offer_accept": (
        "/offers/accept",
        lambda a: {"actor_id": a.player_id, "offer_id": a.offer_id, "params": a.params},
    ),
    "offer_decline": (
        "/offers/decline", lambda a: {"actor_id": a.player_id, "offer_id": a.offer_id}
    ),
    "held_pass": ("/action-card/held/pass", lambda a: {"actor_id": a.player_id}),
    "held_release": ("/action-card/held/release", lambda a: {"actor_id": a.player_id}),
    "reaction_pause_release": ("/reaction-pause/release", lambda a: {"actor_id": a.player_id}),
    "discard_excess": (
        "/action-card/discard-excess", lambda a: {"actor_id": a.player_id, "card_id": a.card_id}
    ),
    "battle_assign": (
        "/tactical/battle/assign",
        lambda a: {
            "faction": a.player_id,
            "sustain": _losses(a.sustain),
            "destroy": _losses(a.destroy),
            "destroyDamaged": _losses(a.destroy_damaged),
        },
    ),
    "status_finish_scoring": ("/status/finish-scoring", _pid),
    "status_redistribute": (
        "/status/redistribute",
        lambda a: {
            "player_id": a.player_id, "tactical": a.tactical, "fleet": a.fleet,
            "strategic": a.strategic,
        },
    ),
    "agenda_reveal": ("/agenda/reveal", _pid),
    "agenda_vote": (
        "/agenda/vote",
        lambda a: {
            "player_id": a.player_id, "outcome": a.outcome, "planets": a.planets,
            "use_predictive": a.use_predictive,
        },
    ),
    "agenda_abstain": ("/agenda/abstain", _pid),
    "agenda_decide": ("/agenda/decide", lambda a: {"player_id": a.player_id, "outcome": a.outcome}),
    "agenda_confirm": ("/agenda/confirm", _pid),
    "agenda_discard": ("/agenda/discard", _pid),
    "agenda_continue": ("/agenda/continue", _pid),
}


def request_for(action: act.Action) -> tuple[str, Body]:
    """Ścieżka i treść żądania HTTP odpowiadającego akcji."""
    path, body = HTTP[action.kind]
    return path, body(action)
