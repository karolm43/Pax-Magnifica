"""Liderzy frakcji: cykl życia (odblokowanie, wyczerpanie, purge) — RULES.md 61.1.

JEDYNE miejsce zmiany stanu lidera w logice gry (RULES.md 43.1a; wyjątek: God-Mode w
``core/board_edit.py``). Stan lidera leży w ``PlayerState.leader_states`` (brak wpisu = stan
domyślny z danych: agent gotowy, commander/hero zablokowany).

Źródło reguł: ``docs/rules_tirules/R_leaders.md``, ``R_purge.md``.

* **Odblokowanie** — predykat warunku ``Unlock`` z danych (``LeaderDef.unlock_condition``)
  rejestrowany przez :func:`register_unlock` (po id lidera) albo :func:`register_unlock_condition`
  (po tekście warunku — wspólny dla wielu liderów, np. „Have 3 scored objectives." wszystkich
  bohaterów). :func:`refresh_unlocks` sprawdza je po KAŻDYM commicie stanu (``StateService``),
  poza chwilą, gdy rozstrzyga się zdolność (otwarte oferty — R_leaders: „unlock conditions cannot
  be met while an ability … is being resolved"). Warunki ZDARZENIOWE („Resolve a combat…”) mają
  hook zdarzenia w module frakcji, który woła :func:`unlock`.
* **Lider bez predykatu** (warunek jeszcze niezakodowany) — gracz odblokowuje go sam
  (:func:`claim_unlock`), żeby gra się nie blokowała (status MANUAL).
* **Koszt użycia** — z tekstu karty: „exhaust this card" => wyczerpanie, „purge this card" =>
  purge (bohaterowie). Odblokowany lider nigdy nie wraca do stanu zablokowanego.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from src.core import triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, PlayerState
from src.core.models import LeaderDef
from src.core.registry import StaticDataRegistry

LOCKED = "locked"
UNLOCKED = "unlocked"
EXHAUSTED = "exhausted"
PURGED = "purged"
STATES: frozenset[str] = frozenset({LOCKED, UNLOCKED, EXHAUSTED, PURGED})

# Predykat warunku odblokowania: czy gracz TERAZ spełnia warunek z karty.
UnlockFn = Callable[[GameState, StaticDataRegistry, str], bool]
_BY_LEADER: dict[str, UnlockFn] = {}
_BY_CONDITION: dict[str, UnlockFn] = {}

_EXHAUST_SELF = re.compile(r"\bexhaust this card\b", re.IGNORECASE)
_PURGE_SELF = re.compile(r"\bpurge this card\b", re.IGNORECASE)
_ATTACH_SELF = re.compile(r"\battach this card\b", re.IGNORECASE)
_ACTION = re.compile(r"\bACTION\s*:", re.IGNORECASE)


def _norm(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(".")


def register_unlock(leader_id: str) -> Callable[[UnlockFn], UnlockFn]:
    """Rejestruje predykat odblokowania KONKRETNEGO lidera (``leaders:<id>``)."""

    def decorate(fn: UnlockFn) -> UnlockFn:
        if leader_id in _BY_LEADER:
            raise ValueError(f"Unlock condition already registered for {leader_id}.")
        _BY_LEADER[leader_id] = fn
        return fn

    return decorate


def register_unlock_condition(condition_text: str) -> Callable[[UnlockFn], UnlockFn]:
    """Rejestruje predykat dla TEKSTU warunku (wszyscy liderzy z tym warunkiem w danych)."""

    def decorate(fn: UnlockFn) -> UnlockFn:
        key = _norm(condition_text)
        if key in _BY_CONDITION:
            raise ValueError(f"Unlock condition already registered: {condition_text}")
        _BY_CONDITION[key] = fn
        return fn

    return decorate


def leader_def(registry: StaticDataRegistry, leader_id: str) -> LeaderDef:
    """Definicja lidera z danych.

    Raises:
        ValueError: Nieznany lider.
    """
    leader = registry.leaders.get(leader_id)
    if leader is None:
        raise ValueError(f"Unknown leader: {leader_id}")
    return leader


def leaders_of(registry: StaticDataRegistry, player: PlayerState) -> list[str]:
    """Liderzy gracza wg danych frakcji (w kolejności z arkusza)."""
    faction = registry.factions.get(player.faction or "")
    return list(faction.leaders) if faction is not None else []


def default_state(registry: StaticDataRegistry, leader_id: str) -> str:
    """Stan początkowy z reguły: agent gotowy, commander i hero zablokowani (R_leaders)."""
    leader = registry.leaders.get(leader_id)
    return UNLOCKED if leader is not None and leader.type == "agent" else LOCKED


def _proxy(state: GameState, player_id: str, leader_id: str) -> str:
    """The leader whose state stands for ``leader_id`` for this player: a borrowed leader resolves
    to its proxy (Ssruu for every other player's agent, RULES.md 62.22), any other to itself."""
    from src.core import rules_hooks  # local: rules_hooks does not import this module

    return rules_hooks.leader_proxy(state, player_id, leader_id)


def state_of(
    state: GameState, registry: StaticDataRegistry, player_id: str, leader_id: str
) -> str:
    """Bieżący stan lidera gracza (``locked``/``unlocked``/``exhausted``/``purged``).

    A borrowed leader (``rules_hooks.leader_proxy``) has the state of its proxy (RULES.md 62.22).
    """
    player = state.players[player_id]
    leader_id = _proxy(state, player_id, leader_id)
    return player.leader_states.get(leader_id, default_state(registry, leader_id))


def is_ready(
    state: GameState, registry: StaticDataRegistry, player_id: str, leader_id: str
) -> bool:
    """Czy lider jest odblokowany i gotowy (można użyć jego zdolności)."""
    return state_of(state, registry, player_id, leader_id) == UNLOCKED


def unlock_predicate(registry: StaticDataRegistry, leader_id: str) -> UnlockFn | None:
    """Zakodowany predykat odblokowania lidera (po id, potem po tekście warunku) albo ``None``."""
    _ensure_loaded()
    fn = _BY_LEADER.get(leader_id)
    if fn is not None:
        return fn
    leader = registry.leaders.get(leader_id)
    if leader is None or not leader.unlock_condition:
        return None
    return _BY_CONDITION.get(_norm(leader.unlock_condition))


def has_event_unlock(leader_id: str) -> bool:
    """Czy warunek lidera jest ZDARZENIOWY i zakodowany hookiem frakcji (``unlocks:<id>``)."""
    from src.core import rules_hooks  # lokalnie: rules_hooks nie importuje tego modułu

    return f"unlocks:{leader_id}" in rules_hooks.covered_components()


def unlock(
    state: GameState, registry: StaticDataRegistry, player_id: str, leader_id: str
) -> bool:
    """Odblokowuje lidera (``locked`` -> ``unlocked``). MUTUJE ``state`` (klon wołającego).

    Returns:
        True, gdy lider został właśnie odblokowany; False, gdy już był odblokowany (no-op).

    Raises:
        ValueError: Nieznany gracz / lider spoza frakcji gracza.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if leader_id not in leaders_of(registry, player):
        raise ValueError(f"{leader_id} is not one of your leaders.")
    if state_of(state, registry, player_id, leader_id) != LOCKED:
        return False
    player.leader_states = {**player.leader_states, leader_id: UNLOCKED}
    triggers.fire(
        state, GameEvent.COMPONENT_GAINED, Moment.WHEN, subject=player_id,
        ctx={"player": player_id, "component": f"leaders:{leader_id}"},
    )
    return True


def refresh_unlocks(state: GameState, registry: StaticDataRegistry | None) -> list[str]:
    """Odblokowuje liderów, których warunek z karty jest TERAZ spełniony. MUTUJE ``state``.

    Nic nie robi, gdy rozstrzyga się zdolność (otwarte oferty) — R_leaders. Zwraca odblokowane id.
    """
    if registry is None or state.pending_offers:
        return []
    unlocked: list[str] = []
    for player_id, player in list(state.players.items()):
        if player.faction is None:
            continue
        for leader_id in leaders_of(registry, player):
            if state_of(state, registry, player_id, leader_id) != LOCKED:
                continue
            predicate = unlock_predicate(registry, leader_id)
            if predicate is not None and predicate(state, registry, player_id):
                unlock(state, registry, player_id, leader_id)
                unlocked.append(leader_id)
    return unlocked


def claim_unlock(
    state: GameState, registry: StaticDataRegistry, player_id: str, leader_id: str
) -> GameState:
    """Gracz sam odblokowuje lidera, którego warunku silnik jeszcze nie sprawdza (MANUAL).

    Lider z zakodowanym warunkiem odblokowuje się wyłącznie sam (silnik-sędzia).

    Raises:
        ValueError: Lider ma zakodowany warunek / już odblokowany / nie należy do gracza.
    """
    leader = leader_def(registry, leader_id)
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if leader_id not in leaders_of(registry, player):
        raise ValueError(f"{leader_id} is not one of your leaders.")
    if unlock_predicate(registry, leader_id) is not None or has_event_unlock(leader_id):
        raise ValueError(
            f"{leader.name} unlocks automatically when its condition is met: "
            f"{leader.unlock_condition}"
        )
    new_state = state.clone()
    if not unlock(new_state, registry, player_id, leader_id):
        raise ValueError(f"{leader.name} is already unlocked.")
    return new_state


def usage_cost(registry: StaticDataRegistry, leader_id: str) -> str | None:
    """Koszt użycia z tekstu karty: ``exhaust``, ``purge`` albo ``None`` (pasywny commander)."""
    leader = leader_def(registry, leader_id)
    text = f"{leader.ability_window or ''} {leader.ability_text or ''}"
    if _PURGE_SELF.search(text):
        return "purge"
    if _EXHAUST_SELF.search(text):
        return "exhaust"
    # R_leaders: „A hero is purged after its abilities are resolved" (także gdy tekst z danych
    # tego nie powtarza, np. ``ghosthero``). Wyjątek: bohater dołączany do planety (Titans) —
    # ⚠️ ZAŁOŻENIE RULES.md 61.1.
    if leader.type == "hero" and _ATTACH_SELF.search(text) is None and _ACTION.search(text):
        return "purge"
    return None


def use_reason(
    state: GameState, registry: StaticDataRegistry, player_id: str, leader_id: str
) -> str | None:
    """Powód, dla którego gracz nie może teraz użyć lidera (``None`` = może)."""
    player = state.players.get(player_id)
    if player is None:
        return f"Unknown player: {player_id}"
    leader = registry.leaders.get(leader_id)
    proxied = _proxy(state, player_id, leader_id) != leader_id
    if leader is None or (leader_id not in leaders_of(registry, player) and not proxied):
        return f"{leader_id} is not one of your leaders."
    if proxied:  # copied through another card (Ssruu): that card must be ready
        leader = registry.leaders.get(_proxy(state, player_id, leader_id)) or leader
    current = state_of(state, registry, player_id, leader_id)
    if current == LOCKED:
        return f"{leader.name} is locked. Unlock: {leader.unlock_condition}"
    if current == EXHAUSTED:
        return f"{leader.name} is exhausted."
    if current == PURGED:
        return f"{leader.name} has been purged."
    return None


def pay_usage(
    state: GameState, registry: StaticDataRegistry, player_id: str, leader_id: str
) -> None:
    """Płaci koszt użycia lidera wg tekstu (wyczerpanie / purge). MUTUJE ``state``.

    Raises:
        ValueError: Lider nie jest gotowy (zablokowany, wyczerpany, purge'owany).
    """
    reason = use_reason(state, registry, player_id, leader_id)
    if reason is not None:
        raise ValueError(reason)
    cost = usage_cost(registry, leader_id)
    if cost == "exhaust":
        exhaust(state, player_id, leader_id)
    elif cost == "purge":
        purge(state, player_id, leader_id)


def exhaust(state: GameState, player_id: str, leader_id: str) -> None:
    """Wyczerpuje lidera (stan ``exhausted``); odświeża go status (``ready_all``). A borrowed leader
    exhausts its proxy (Ssruu, RULES.md 62.22)."""
    player = state.players[player_id]
    leader_id = _proxy(state, player_id, leader_id)
    player.leader_states = {**player.leader_states, leader_id: EXHAUSTED}


def exhaust_announced(
    state: GameState, player_id: str, leader_id: str, ctx: dict[str, object] | None = None
) -> None:
    """Exhausts a leader WITHOUT using its ability and announces it like a use does
    (``COMPONENT_EXHAUSTED/AFTER``): "exhaust 1 of your agents" (Thunder's Paradox) makes an agent
    "become exhausted" (Temporal Command Suite, RULES.md 62.21). MUTATES ``state``.

    Raises:
        ValueError: The leader is not ready.
    """
    own = _proxy(state, player_id, leader_id)
    if state.players[player_id].leader_states.get(own, "") in (LOCKED, EXHAUSTED, PURGED):
        raise ValueError(f"{leader_id} is not ready.")
    exhaust(state, player_id, leader_id)
    triggers.fire(
        state, GameEvent.COMPONENT_EXHAUSTED, Moment.AFTER, subject=player_id,
        ctx={**dict(ctx or {}), "player": player_id, "component": f"leaders:{leader_id}"},
    )


def purge(state: GameState, player_id: str, leader_id: str) -> None:
    """Usuwa lidera z gry (stan ``purged``) — R_purge: nie wraca do gry (proxy: RULES.md 62.22)."""
    player = state.players[player_id]
    leader_id = _proxy(state, player_id, leader_id)
    player.leader_states = {**player.leader_states, leader_id: PURGED}


def _ensure_loaded() -> None:
    """Ładuje pakiet hooków (rejestruje predykaty warunków z modułów frakcji)."""
    from src.core import rules_hooks

    rules_hooks.effect_for("leaders:__load__")


# --- Warunki wspólne (tekst z danych) ----------------------------------------------------------


def scored_objectives_count(state: GameState, registry: StaticDataRegistry, player_id: str) -> int:
    """Zdobyte cele gracza: publiczne + tajne (R_leaders: punkty VP spoza celów się nie liczą)."""
    from src.core.objectives import objective_def  # lokalnie: objectives jest ciężkim modułem

    public = sum(
        scorers.count(player_id)
        for objective_id, scorers in state.objectives.scored.items()
        if objective_def(registry, objective_id) is not None
    )
    return public + len(state.players[player_id].scored_secrets)


@register_unlock_condition("Have 3 scored objectives.")
def _three_scored_objectives(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> bool:
    """Bohaterowie: 3 zdobyte cele (dowolna kombinacja publicznych i tajnych) — R_leaders."""
    return scored_objectives_count(state, registry, player_id) >= 3
