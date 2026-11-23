"""Uprawnienia aktora (RULES.md 44.1, 44.1a): KTO może wykonać akcję w bieżącym stanie.

Moduł jest nieświadomy sieci: zna wyłącznie ``player_id`` aktora (ustalony przez ``api/``
z nagłówka, a w etapie N1 z tokenu miejsca). ``actor_id=None`` oznacza tryb zaufany
(lokalny, jedno okno) i przepuszcza każdą kontrolę — tak działa dotychczasowe UI.

Błąd autoryzacji to ``ActorError`` (``PermissionError``, NIE ``ValueError``), żeby
``api/`` mapowało go na 403, a nie na 422 jak błędy reguł.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import overload

from src.core import game_setup
from src.core.game_state import GameState


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


# --- Na kogo czeka gra (UI „czekamy na gracza X", RULES.md 44.5) ---------------------------


def awaiting(state: GameState) -> list[tuple[str, str]]:
    """Gracze, od których decyzji gra teraz zależy: ``[(player_id, powód)]``, pilne pierwsze.

    Jawna informacja stołu (kto ma ruch), wyliczana z tych samych pól co uprawnienia aktora:
    okno czasowe → jego respondent; oferty → ich decydenci; walka (przypisanie trafień) → strony
    z trafieniami do pokrycia; inwazja / eksploracja / karta strategii → ich prowadzący;
    w przeciwnym razie gracz z turą (faza akcji/strategii) albo mówca (status/agenda).
    Powody to stałe kody dla UI: ``respond``, ``decide``, ``assign_hits``, ``combat``,
    ``invasion``, ``explore``, ``strategy``, ``turn``, ``speaker``, w fazie statusu ``score``
    (punktowanie celów) i ``redistribute`` (rozdział żetonów), w agendzie ``vote``; w setupie
    startowym ``secret`` (wybór tajnego celu) i ``setup`` (mówca: Custodians / odkrycie celów).
    """
    found: list[tuple[str, str]] = []

    def add(player_id: str | None, reason: str) -> None:
        if player_id and player_id in state.players and all(p != player_id for p, _ in found):
            found.append((player_id, reason))

    setup = state.setup
    if setup is not None:
        # Setup startowy (RULES.md 45): tajne cele wybierają wszyscy naraz, potem mówca.
        for player_id in game_setup.pending_choosers(state):
            add(player_id, "secret")
        if not found:
            add(state.speaker_id, "setup")
        return found
    window = state.pending_window
    if window is not None:
        add(window.current_responder, "respond")
    for offer in state.pending_offers:
        add(offer.player_id, "decide")
    combat = state.active_combat
    if combat is not None:
        pending = [pid for pid, hits in combat.pending_hits.items() if hits > 0]
        for pid in pending:
            add(pid, "assign_hits")
        if not pending:
            add(combat.attacker, "combat")
            add(combat.defender, "combat")
    if state.invasion is not None:
        add(state.invasion.attacker, "invasion")
    if state.exploration is not None:
        add(state.exploration.player_id, "explore")
    if state.pending_strategy is not None:
        add(state.pending_strategy.owner_id, "strategy")
    if not found:
        _phase_turn(state, add)
    if not found:
        add(state.speaker_id, "speaker")
    return found


def _phase_turn(state: GameState, add: Callable[[str | None, str], None]) -> None:
    """Kolej gracza nazwana wg fazy (plan U5/Z13): w statusie/agendzie to nie „tura”."""
    from src.core.agenda_phase import current_voter  # lokalnie: agenda_phase ciągnie hooki
    from src.core.game_state import Phase, StatusStep

    if state.phase is Phase.STATUS and state.status is not None:
        if state.status.step is StatusStep.SCORE_OBJECTIVES:
            add(state.active_player_id, "score")
        elif state.status.step is StatusStep.REDISTRIBUTE:
            for player_id in state.players:
                if player_id not in state.status.done:
                    add(player_id, "redistribute")
        return
    if state.phase is Phase.AGENDA:
        add(current_voter(state), "vote")
        return
    add(state.active_player_id, "turn")
