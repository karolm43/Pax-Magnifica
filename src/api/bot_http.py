"""Akcja z katalogu bota → to samo żądanie HTTP, które wysyła UI.

Używa go runner bota (``api/bot_runner``: bot gra tą samą trasą co człowiek - etykiety historii,
Activity, middleware i broadcast są identyczne) i test zgodności katalog ↔ HTTP. Leży w ``api/``,
bo warstwa bota nie zna ``api/`` (RULES.md 65.1). Każdy rodzaj z ``ACTION_KINDS`` MUSI mieć tu
wpis (strażnik w ``tests/engine/test_actions_parity.py``).
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


def _planet_losses(a: Any) -> Body:
    return {
        "planet": a.planet,
        "faction": a.player_id,
        "sustain": _losses(a.sustain),
        "destroy": _losses(a.destroy),
        "destroyDamaged": _losses(a.destroy_damaged),
    }


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
    "production_skip": ("/tactical/production/skip-grant", lambda a: None),
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
    "fleet_pool_resolve": (
        "/tactical/fleet-pool/resolve",
        lambda a: {"faction": a.player_id, "remove": _losses(a.remove)},
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
    # --- B5: akcja taktyczna, walka, Space Cannon, inwazja, eksploracja, karty akcji ---
    "tactical_activate": ("/tactical/activate", lambda a: {"position": a.position}),
    "tactical_move": (
        "/tactical/move",
        lambda a: {
            "fromPosition": a.from_position,
            "faction": a.player_id,
            "ships": [{"baseType": bt, "count": n} for bt, n in a.ships.items()],
            "cargo": [
                {"baseType": c.base_type, "count": c.count, "fromZone": c.from_zone}
                for c in a.cargo
            ],
        },
    ),
    "tactical_next": ("/tactical/step/next", lambda a: None),
    "tactical_produce": (
        "/tactical/produce",
        lambda a: {
            "faction": a.player_id,
            "orders": [
                {"baseType": o.base_type, "count": o.count, "zone": o.zone} for o in a.orders
            ],
        },
    ),
    "capacity_resolve": (
        "/tactical/capacity/resolve",
        lambda a: {"faction": a.player_id, "remove": _losses(a.remove)},
    ),
    "battle_start": ("/tactical/battle/start", lambda a: {"planet": a.planet}),
    "battle_afb": ("/tactical/battle/afb", lambda a: None),
    "battle_roll": ("/tactical/battle/roll", lambda a: None),
    "battle_close": ("/tactical/battle/close", lambda a: None),
    "battle_announce_retreat": (
        "/tactical/battle/announce-retreat",
        lambda a: {"faction": a.player_id, "announce": a.announce},
    ),
    "battle_retreat": (
        "/tactical/battle/retreat",
        lambda a: {"faction": a.player_id, "destination": a.destination},
    ),
    "space_cannon_fire": (
        "/tactical/space-cannon/fire", lambda a: {"faction": a.player_id, "target": a.target}
    ),
    "space_cannon_pass": ("/tactical/space-cannon/pass", lambda a: {"faction": a.player_id}),
    "space_cannon_assign": (
        "/tactical/space-cannon/assign",
        lambda a: {
            "faction": a.player_id,
            "losses": _losses(a.destroy),
            "sustain": _losses(a.sustain),
            "destroyDamaged": _losses(a.destroy_damaged),
        },
    ),
    "invasion_begin": ("/tactical/invasion/begin", lambda a: None),
    "invasion_bombard": (
        "/tactical/invasion/bombard",
        lambda a: {
            "assignments": [
                {"baseType": bt, "planet": planet, "count": n} for bt, planet, n in a.assignments
            ]
        },
    ),
    "invasion_bombard_assign": (
        "/tactical/invasion/bombard/assign", lambda a: _planet_losses(a)
    ),
    "invasion_commit": (
        "/tactical/invasion/commit",
        lambda a: {
            "commits": [
                {"planet": planet, "baseType": bt, "count": n}
                for planet, units in a.commits.items()
                for bt, n in units.items()
            ]
        },
    ),
    "invasion_custodians": (
        "/tactical/invasion/custodians",
        lambda a: {"planets": list(a.planets), "trade_goods": a.trade_goods},
    ),
    "invasion_defense_fire": ("/tactical/invasion/defense/fire", lambda a: {"planet": a.planet}),
    "invasion_defense_pass": ("/tactical/invasion/defense/pass", lambda a: {"planet": a.planet}),
    "invasion_defense_assign": (
        "/tactical/invasion/defense/assign", lambda a: _planet_losses(a)
    ),
    "invasion_next": ("/tactical/invasion/next", lambda a: None),
    "exploration_draw": (
        "/exploration/draw", lambda a: {"planet": a.planet, "deck": a.deck}
    ),
    "exploration_resolve": (
        "/exploration/resolve", lambda a: {"option": a.option, "param": a.param}
    ),
    "exploration_finish": ("/exploration/finish", lambda a: None),
    "action_card_play": (
        "/action-card/play",
        lambda a: {
            "player_id": a.player_id, "actor_id": a.player_id, "card_id": a.card_id,
            "params": a.params,
        },
    ),
}


def request_for(action: act.Action) -> tuple[str, Body]:
    """Ścieżka i treść żądania HTTP odpowiadającego akcji."""
    path, body = HTTP[action.kind]
    return path, body(action)
