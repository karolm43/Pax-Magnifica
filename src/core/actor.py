"""Uprawnienia aktora (RULES.md 44.1, 44.1a): KTO może wykonać akcję w bieżącym stanie.

Moduł jest nieświadomy sieci: zna wyłącznie ``player_id`` aktora (ustalony przez ``api/``
z nagłówka, a w etapie N1 z tokenu miejsca). ``actor_id=None`` oznacza tryb zaufany
(lokalny, jedno okno) i przepuszcza każdą kontrolę — tak działa dotychczasowe UI.

Błąd autoryzacji to ``ActorError`` (``PermissionError``, NIE ``ValueError``), żeby
``api/`` mapowało go na 403, a nie na 422 jak błędy reguł.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import overload

from src.core import game_setup
from src.core.game_state import (
    AgendaStep,
    CombatStep,
    GameState,
    InvasionPhase,
    Phase,
    SetupStage,
    StatusStep,
    WindowType,
)
from src.core.registry import StaticDataRegistry


class ActorError(PermissionError):
    """Aktor nie jest uprawniony do tej akcji (``api/`` → HTTP 403)."""


def resolve_player(state: GameState, key: str) -> str:
    """Mapuje ``player_id`` albo jednoznaczną frakcję na ``player_id`` (bez zgadywania)."""
    if key in state.players:
        return key
    matches = [pid for pid, p in state.players.items() if p.faction == key]
    return matches[0] if len(matches) == 1 else key


@overload
def merge_claimed(actor_id: str | None, claimed: str) -> str: ...
@overload
def merge_claimed(actor_id: str | None, claimed: None) -> str | None: ...
@overload
def merge_claimed(actor_id: str | None, claimed: str | None) -> str | None: ...


def merge_claimed(actor_id: str | None, claimed: str | None) -> str | None:
    """Łączy aktora z nagłówka z polem ``actor_id`` w treści (stare endpointy, RULES.md 44.1a).

    Gdy oba podane i różne — ``ActorError`` (treść nie może podszywać się pod inny podmiot).
    """
    if actor_id is not None and claimed is not None and actor_id != claimed:
        raise ActorError(
            f"Request body names actor {claimed!r}, but the request comes from {actor_id!r}."
        )
    return actor_id if actor_id is not None else claimed


def require_seated(state: GameState, actor_id: str | None) -> None:
    """Akcja stołu: aktor musi być graczem tej partii (tryb zaufany przepuszcza)."""
    if actor_id is not None and actor_id not in state.players:
        raise ActorError(f"{actor_id!r} is not a player in this game.")


def require(
    state: GameState,
    actor_id: str | None,
    allowed: Iterable[str | None],
    what: str,
) -> None:
    """Wymaga, by aktor był jednym z ``allowed`` (``None`` w liście jest pomijane).

    Pusta lista uprawnionych przy podanym aktorze = nikt nie może teraz tego zrobić → ``ActorError``
    (np. brak trwającej walki). Tryb zaufany (``actor_id=None``) przepuszcza zawsze.
    """
    if actor_id is None:
        return
    require_seated(state, actor_id)
    entitled = sorted({resolve_player(state, a) for a in allowed if a})
    if actor_id not in entitled:
        who = ", ".join(entitled) if entitled else "nobody right now"
        raise ActorError(f"{what}: {actor_id!r} may not do this (allowed: {who}).")


def subject(
    state: GameState, actor_id: str | None, claimed: str | None, what: str = "Action"
) -> str | None:
    """Podmiot akcji z pola ``player_id``/``faction`` w treści, uzgodniony z aktorem.

    - ``claimed`` pominięte → zwraca aktora (aktor trafia do ``core/`` jako ``player_id``);
    - aktor pominięty (tryb zaufany) → zwraca ``claimed`` bez zmian;
    - oba podane → muszą wskazywać tego samego gracza (frakcja → gracz), inaczej ``ActorError``.
    """
    if claimed is None:
        return actor_id
    if actor_id is None:
        return claimed
    require_seated(state, actor_id)
    if resolve_player(state, claimed) != actor_id:
        raise ActorError(f"{what}: {actor_id!r} cannot act for {claimed!r}.")
    return claimed


Entitled = Callable[[GameState], list[str | None]]
"""Funkcja stanu zwracająca uprawnionych (np. ``turn_player``)."""


def check(
    state: GameState,
    actor_id: str | None,
    claimed: str | None = None,
    fallback: Entitled | None = None,
    what: str = "Action",
) -> None:
    """Jedna kontrola na endpoint (RULES.md 44.1a).

    ``claimed`` (podmiot z treści: ``player_id``/``faction``) musi być aktorem; gdy treść go
    nie podaje, aktor musi być na liście ``fallback(state)`` (np. gracz aktywny, strony walki).
    """
    if claimed is not None:
        subject(state, actor_id, claimed, what)
    elif fallback is not None:
        require(state, actor_id, fallback(state), what)


# --- Kto jest uprawniony w bieżącym stanie (listy dla ``require``) -------------------------


def turn_player(state: GameState) -> list[str | None]:
    """Gracz aktywny (tura, akcja taktyczna, kroki fazy)."""
    return [state.active_player_id]


def speaker(state: GameState) -> list[str | None]:
    """Mówca (kroki faz prowadzone przez mówcę, np. ujawnianie agend)."""
    return [state.speaker_id]


def window_respondent(state: GameState) -> list[str | None]:
    """Bieżący respondent okna czasowego (RULES.md 29.2)."""
    window = state.pending_window
    return [window.current_responder] if window is not None else []


def combat_sides(state: GameState) -> list[str | None]:
    """Obie strony trwającej walki (rzut / zamknięcie rundy dotyczą obu)."""
    combat = state.active_combat
    return [combat.attacker, combat.defender] if combat is not None else []


def invasion_attacker(state: GameState) -> list[str | None]:
    """Najeźdźca trwającej inwazji (kroki inwazji prowadzi atakujący)."""
    invasion = state.invasion
    return [invasion.attacker] if invasion is not None else turn_player(state)


def invasion_parties(state: GameState) -> list[str | None]:
    """Najeźdźca + właściciele jednostek na planetach systemu inwazji (Space Cannon Defense)."""
    invasion = state.invasion
    if invasion is None:
        return turn_player(state)
    parties: list[str | None] = [invasion.attacker]
    system = state.systems.get(invasion.position)
    if system is not None:
        for by_player in system.planet_units.values():
            parties.extend(pid for pid, units in by_player.items() if any(units.values()))
    return parties


def exploring_player(state: GameState) -> list[str | None]:
    """Gracz rozpatrujący bieżącą eksplorację (gdy brak — gracz aktywny)."""
    exploration = state.exploration
    return [exploration.player_id] if exploration is not None else turn_player(state)


def strategy_owner(state: GameState) -> list[str | None]:
    """Właściciel rozpatrywanej karty strategii (kroki primary)."""
    pending = state.pending_strategy
    return [pending.owner_id] if pending is not None else turn_player(state)


def production_grantee(state: GameState) -> list[str | None]:
    """Właściciel jednorazowej produkcji z karty (np. Freelancers); gdy brak — gracz aktywny."""
    grant = state.production_grant
    return [grant.player_id] if grant is not None else turn_player(state)


# --- Who the game is waiting for, and why (RULES.md 44.5) -----------------------------------
#
# PUBLIC information, identical for every viewer: it is computed from the full state, so it must
# never read anything private - card ids, ``passed`` / ``auto_pass_at`` / ``extended_by`` of
# reaction windows, queued secondary decisions, offer labels or contexts. Hand SIZES are public.


@dataclass(frozen=True)
class WaitReason:
    """One thing the game expects from one player.

    ``reason_code`` is a stable machine code (bot / fuzzer diagnostics), ``summary`` a safe public
    English text. ``blocking=False`` = the player answers later (e.g. a strategy card secondary
    after the players before them); the game is not stopped on them yet.
    """

    player_id: str
    reason_code: str
    summary: str
    blocking: bool = True


class _Waits:
    """Collects reasons in urgency order, one per ``(player, code)``; unknown players skipped."""

    def __init__(self, state: GameState, registry: StaticDataRegistry | None) -> None:
        self.state = state
        self.registry = registry
        self.found: list[WaitReason] = []

    def add(self, player_id: str | None, code: str, summary: str, *, blocking: bool = True) -> None:
        if not player_id or player_id not in self.state.players or self.has(player_id, code):
            return
        self.found.append(WaitReason(player_id, code, summary, blocking))

    def has(self, player_id: str, code: str) -> bool:
        return any(r.player_id == player_id and r.reason_code == code for r in self.found)

    @property
    def blocked(self) -> bool:
        return any(r.blocking for r in self.found)

    def card(self, initiative: object) -> str:
        """``Strategy Card 7 (Technology)``; the name needs the registry."""
        number = int(str(initiative or 0))
        if not number:
            return "a strategy card"
        if self.registry is not None:
            for card in self.registry.strategy_card_set():
                if card.initiative == number:
                    return f"Strategy Card {number} ({card.name})"
        return f"Strategy Card {number}"


def _hits(count: int, kind: str) -> str:
    return f"assigning {count} {kind} hit{'' if count == 1 else 's'}"


def describe_wait_reasons(
    state: GameState, registry: StaticDataRegistry | None = None
) -> list[WaitReason]:
    """Who the game is waiting for and why, most urgent first (empty once the game is over).

    The order of checks mirrors ``engine/legal.legal_actions``. ``registry`` adds strategy card
    names and finds the Space Cannon Defense shooters; without it the texts are more generic.
    """
    if state.winner_id is not None:
        return []
    waits = _Waits(state, registry)
    if state.setup is not None:
        _setup_waits(state, waits)
        return waits.found
    _window_hold_waits(state, waits)
    if waits.found:
        return waits.found
    # Over the hand limit blocks only that player's own moves (``legal_actions``): listed first,
    # but the others still get their reasons below.
    discards = _Waits(state, registry)
    _discard_waits(state, discards)
    if state.production_grant is not None:
        waits.add(state.production_grant.player_id, "produce", "producing units")
    if state.pending_window is not None:
        _timing_window_waits(state, waits)
        _offer_waits(state, waits)
    elif state.pending_offers:
        _offer_waits(state, waits)
    elif state.active_combat is not None:
        _combat_waits(state, waits)
    elif state.exploration is not None:
        waits.add(state.exploration.player_id, "explore", "resolving exploration")
    elif state.invasion is not None:
        _invasion_waits(state, waits)
    elif state.pending_strategy is not None:
        pending = state.pending_strategy
        if not waits.has(pending.owner_id, "produce"):
            card = waits.card(pending.initiative)
            waits.add(pending.owner_id, "strategy", f"resolving the primary ability of {card}")
    if not waits.blocked:
        _phase_waits(state, waits)
    if not waits.blocked:
        waits.add(state.speaker_id, "speaker", "advancing the game (speaker)")
    return discards.found + waits.found


def _setup_waits(state: GameState, waits: _Waits) -> None:
    """Starting setup (RULES.md 45): all pick secret objectives at once, then the speaker."""
    assert state.setup is not None
    for player_id in game_setup.pending_choosers(state):
        waits.add(player_id, "secret", "choosing a secret objective")
    if waits.found:
        return
    step = {
        SetupStage.CUSTODIANS: "placing the Custodians token",
        SetupStage.OBJECTIVES: "revealing the first public objectives",
    }.get(state.setup.stage, "finishing the game setup")
    waits.add(state.speaker_id, "setup", f"{step} (speaker)")


def _window_hold_waits(state: GameState, waits: _Waits) -> None:
    """Fixed-length reaction windows (RULES.md 54.11). EVERY eligible player is listed: who has
    already passed is private, so ``passed`` is deliberately not read."""
    if state.held_play is not None:
        for player_id in state.held_play.eligible:
            waits.add(player_id, "react", "may respond to an action card")
    if state.reaction_pause is not None:
        for player_id in state.reaction_pause.eligible:
            waits.add(player_id, "react", f"may react: {state.reaction_pause.label}")


def _discard_waits(state: GameState, waits: _Waits) -> None:
    from src.core import hand_limit  # local: hand_limit pulls in the hooks

    for player_id, excess in hand_limit.players_over_limit(state).items():
        cards = "card" if excess == 1 else "cards"
        waits.add(player_id, "discard", f"discarding {excess} action {cards} over the hand limit")


def _offer_waits(state: GameState, waits: _Waits) -> None:
    for offer in state.pending_offers:  # never the label / context: they are the decider's own
        text = "deciding whether to use an ability"
        if offer.mandatory:
            text = "making a required choice"
        waits.add(offer.player_id, "decide", text)


def _timing_window_waits(state: GameState, waits: _Waits) -> None:
    window = state.pending_window
    assert window is not None
    kind = window.window_type
    responder = window.current_responder
    if kind is WindowType.STRATEGY_SECONDARY:
        _secondary_waits(state, waits)
    elif kind is WindowType.SPACE_CANNON:
        from src.core import space_cannon  # local: space_cannon pulls in the combat modules

        pending = space_cannon.pending_hits(state)
        if pending is not None:  # the target assigns, not the window's current shooter
            hits = space_cannon.required_hits(state, pending.target, waits.registry)
            waits.add(pending.target, "assign_hits", _hits(hits, "Space Cannon"))
        else:
            waits.add(responder, "space_cannon", "deciding on Space Cannon Offense")
    elif kind is WindowType.COMBAT_ASSIGN_HITS:
        combat = state.active_combat
        pending_hits = combat.pending_hits if combat is not None else {}
        if responder is not None:
            count = pending_hits.get(responder, 0)
            text = _hits(count, "combat") if count else "assigning combat hits"
            waits.add(responder, "assign_hits", text)
        for player_id, count in pending_hits.items():
            if count > 0:
                waits.add(player_id, "assign_hits", _hits(count, "combat"), blocking=False)
    elif kind is WindowType.COMBAT_RETREAT:
        waits.add(responder, "retreat", "deciding whether to announce a retreat")
    elif kind is WindowType.FLEET_POOL:
        waits.add(responder, "remove_excess", "removing ships over the fleet pool")
    elif kind is WindowType.CAPACITY:
        waits.add(responder, "remove_excess", "removing units over capacity")
    elif not any(offer.player_id == responder for offer in state.pending_offers):
        waits.add(responder, "respond", "deciding on a timing window reaction")


def _secondary_waits(state: GameState, waits: _Waits) -> None:
    """The current respondent blocks; later players are listed as not blocking yet. THAT a player
    has queued a decision is public (RULES.md 30.12), WHAT they queued is never read."""
    window = state.pending_window
    assert window is not None
    responder = window.current_responder
    card = waits.card(window.context.get("initiative"))
    if responder is not None and not waits.has(responder, "produce"):
        waits.add(responder, "secondary", f"following {card}")
    for player_id in window.queue[window.cursor + 1 :]:
        if player_id not in state.secondary_queue:
            waits.add(player_id, "secondary", f"yet to answer {card}", blocking=False)


def _combat_waits(state: GameState, waits: _Waits) -> None:
    combat = state.active_combat
    assert combat is not None
    for player_id, count in combat.pending_hits.items():
        if count > 0:
            waits.add(player_id, "assign_hits", _hits(count, "combat"))
    if waits.blocked:
        return
    sides = [combat.attacker, combat.defender]
    summary = "resolving combat"
    if combat.step is CombatStep.ROLL:
        sides = [pid for pid in sides if pid not in combat.side_rolls]
        summary = "rolling combat dice"
    elif combat.step is CombatStep.AFB:
        summary = "resolving Anti-Fighter Barrage"
    elif combat.step is CombatStep.RETREAT:
        sides = list(combat.retreating) or sides
        summary = "retreating from combat"
    elif combat.step is CombatStep.DONE:
        sides = [combat.attacker]
        summary = "closing the combat"
    for player_id in sides:
        waits.add(player_id, "combat", summary)


def _invasion_waits(state: GameState, waits: _Waits) -> None:
    from src.core import invasion  # local: invasion pulls in the combat modules

    inv = state.invasion
    assert inv is not None
    for key, count in inv.bombard_pending.items():
        if count > 0:
            with contextlib.suppress(ValueError):  # God-Mode state without the bombardment log
                defender = invasion.bombard_defender(inv, key)
                waits.add(defender, "assign_hits", _hits(count, "bombardment"))
    if waits.blocked:
        return
    if inv.phase is InvasionPhase.SPACE_CANNON_DEFENSE:
        defense = sum(max(0, n) for n in inv.defense_pending.values())
        if defense:
            waits.add(inv.attacker, "assign_hits", _hits(defense, "Space Cannon"))
            return
        if waits.registry is not None:
            for planet in invasion.undefended_open(state, waits.registry):
                shooters = invasion.defense_shooters(state, waits.registry, planet)
                for shooter in shooters:
                    waits.add(shooter.player_id, "space_cannon", "deciding on Space Cannon Defense")
                if shooters:
                    return
    step = {
        InvasionPhase.BOMBARDMENT: "bombardment",
        InvasionPhase.COMMIT: "committing ground forces",
        InvasionPhase.SPACE_CANNON_DEFENSE: "Space Cannon Defense",
        InvasionPhase.GROUND_COMBAT: "ground combat",
        InvasionPhase.ESTABLISH: "establishing control",
    }[inv.phase]
    waits.add(inv.attacker, "invasion", f"invasion: {step}")


def _phase_waits(state: GameState, waits: _Waits) -> None:
    """Nothing special pending: whose move it is, named by phase (in status/agenda not a "turn")."""
    from src.core import turn_flow  # local: turn_flow / agenda_phase pull in the hooks
    from src.core.agenda_phase import current_voter

    active = state.active_player_id
    if turn_flow.can_advance_phase(state):
        # Everyone passed; the last passer still holds the turn (a pass does not hand it on) and
        # MAY end it, but the speaker can advance without that - so it is not blocking.
        last = state.players.get(active) if active else None
        if (
            state.phase is Phase.ACTION
            and last is not None
            and last.passed
            and state.turn_end_window is None
        ):
            waits.add(active, "turn", "may still end the turn", blocking=False)
        waits.add(state.speaker_id, "speaker", "advancing to the next phase (speaker)")
        return
    if state.phase is Phase.STATUS and state.status is not None:
        if state.status.step is StatusStep.SCORE_OBJECTIVES:
            waits.add(active, "score", "status phase scoring")
            for player_id in state.players:
                if player_id != active and player_id not in state.status.done:
                    waits.add(player_id, "score", "yet to score objectives", blocking=False)
        elif state.status.step is StatusStep.REDISTRIBUTE:
            for player_id in state.players:
                if player_id not in state.status.done:
                    waits.add(player_id, "redistribute", "placing command tokens")
        return
    if state.phase is Phase.AGENDA:
        voter = current_voter(state)
        if voter is not None:
            waits.add(voter, "vote", "voting on the agenda")
            return
        step = state.agenda.step if state.agenda is not None else None
        texts = {
            AgendaStep.REVEAL: "revealing the next agenda",
            AgendaStep.TIEBREAK: "breaking the agenda tie",
            AgendaStep.COUNTED: "confirming the vote result",
            AgendaStep.RESOLVED: "continuing past the resolved agenda",
        }
        text = texts.get(step, "running the agenda phase") if step else "running the agenda phase"
        waits.add(state.speaker_id, "speaker", f"{text} (speaker)")
        return
    summary = "taking a turn"
    player = state.players.get(active) if active else None
    if state.phase is Phase.STRATEGY:
        summary = "picking a strategy card"
    elif state.tactical_step is not None:
        summary = f"tactical action: {state.tactical_step.value.lower().replace('_', ' ')}"
    elif player is not None and player.took_action_this_turn:
        summary = "ending the turn"
    waits.add(active, "turn", summary)


def format_wait_reasons(state: GameState, registry: StaticDataRegistry | None = None) -> str:
    """One diagnostic line for stall / timeout logs (bot runner, fuzzer)."""
    entries = []
    for reason in describe_wait_reasons(state, registry):
        faction = state.players[reason.player_id].faction or "?"
        later = "" if reason.blocking else ", not blocking"
        entries.append(
            f"{reason.player_id} ({faction}) {reason.reason_code}: {reason.summary}{later}"
        )
    pending = "; ".join(entries) if entries else "nothing pending"
    return f"phase {state.phase.value}, round {state.round_number}; {pending}"


def awaiting(state: GameState) -> list[tuple[str, str]]:
    """Players whose decision the game is stopped on: ``[(player_id, reason_code)]``, one entry
    per player, most urgent first - the blocking part of :func:`describe_wait_reasons`."""
    found: dict[str, str] = {}
    for reason in describe_wait_reasons(state):
        if reason.blocking:
            found.setdefault(reason.player_id, reason.reason_code)
    return list(found.items())
