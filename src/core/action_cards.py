"""Zagrywanie kart akcji w fazie akcji (RULES.md 53): ręka -> walidacja -> efekt -> odrzucone.

Zakres: karty z oknem ``ACTION`` (zagrywane JAKO akcja komponentu, R_component_action). Karty
reakcji (when/after/before/instead) wymagają modelu STOP i predykatów zagrywalności
(RULES.md 43.4) - tu odrzucane z jasnym komunikatem. Funkcja jest CZYSTA (``state -> state``).

Efekt karty to funkcja zarejestrowana przez ``rules_hooks.register_effect("action_cards:<id>")``
(pakiet ``core/hooks/action_cards.py``). Karta BEZ efektu nie blokuje gry (RULES.md 43.1 pkt 7,
43.3): idzie na stos odrzuconych, liczy się jako akcja, a wynik zwraca ``implemented=False`` -
operator rozstrzyga skutek ręcznie (God-Mode).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    agenda_phase,
    card_draw,
    card_hold,
    component_action,
    hand_limit,
    promissory_play,
    reaction_cards,
    rules_hooks,
    triggers,
)
from src.core.components import ActionCardDef, ComponentCategory, ComponentRef
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, HeldPlay
from src.core.registry import StaticDataRegistry
from src.core.timing_spec import TriggerKind


def effect_key(card_id: str) -> str:
    """Klucz komponentu karty akcji w rejestrze efektów (``kategoria:id``)."""
    return f"{ComponentCategory.ACTION_CARD.value}:{card_id}"


def card_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, card_id: str
) -> tuple[bool, list[dict[str, Any]]]:
    """Opis wyborów do formularza zagrania karty: ``(implemented, wejścia)``.

    ``implemented=False`` = karta bez efektu w silniku (zagranie = ręczne rozstrzygnięcie).

    Raises:
        ValueError: Karta nieznana albo nie ma jej w ręce gracza.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if card_id not in player.private.action_cards:
        raise ValueError(f"You do not have the action card {card_id}.")
    if not isinstance(registry.catalog.get(ComponentCategory.ACTION_CARD, card_id), ActionCardDef):
        raise ValueError(f"Unknown action card: {card_id}")
    key = effect_key(card_id)
    if rules_hooks.effect_for(key) is None:
        return False, []
    inputs_fn = rules_hooks.inputs_for(key)
    inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    # Bez domyślnych podpowiedzi z tekstem karty: okno pokazuje tekst karty raz, nad formularzem
    # (decyzja użytkownika 2026-11-16 - tekst się nie dubluje); ``hint`` to tylko porada hooka.
    return True, inputs


def card_summary(
    state: GameState, registry: StaticDataRegistry, player_id: str, card_id: str
) -> str | None:
    """Krótki opis „dotyczy: …" z bieżącego stanu gracza (``None`` = brak podglądu dla karty)."""
    preview = rules_hooks.preview_for(effect_key(card_id))
    return preview(state, registry, player_id) if preview is not None else None


def _has_legal_choices(inputs: list[dict[str, Any]]) -> bool:
    """Czy każde wymagane wejście formularza ma dość opcji (inaczej: nie do rozstrzygnięcia)."""
    for item in inputs:
        options = item.get("options")
        if not isinstance(options, list):
            continue  # wejście liczbowe - zawsze do spełnienia
        need = int(item["min"]) if item.get("kind") == "multi" else 1
        if len(options) < need:
            return False
    return True


def forbidden_reason(state: GameState, player_id: str) -> str | None:
    """Powód zakazu zagrywania kart akcji przez efekt gry (hook FORBID; Political Censure)."""
    reasons = rules_hooks.forbidden(rules_hooks.POINT_ACTION_CARDS_FORBIDDEN, state, player_id)
    return sorted(reasons)[0] if reasons else None


def playability(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Które karty z ręki gracza można zagrać TERAZ jako akcję (do przeciągania z ręki w UI).

    Dla każdej unikalnej karty: ``card_id``, ``playable``, ``reason`` (gdy nie), ``implemented``,
    ``reaction`` (karta reakcji, nie ACTION).
    Karta jest zagrywalna, gdy: ma okno ACTION, tura/faza/okno pozwalają na akcję komponentu
    (te same walidacje co ``play_action_card``) i - gdy silnik ją automatyzuje - istnieją
    legalne cele dla każdego wymaganego wyboru (R_action_cards: nie można zagrać karty,
    której nie da się w pełni rozstrzygnąć). Nie mutuje stanu.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    result: list[dict[str, Any]] = []
    for card_id in dict.fromkeys(player.private.action_cards):
        spec = registry.catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, card_id))
        # ``reaction`` = karta grana w odpowiedzi na okno (nie ACTION): UI sygnalizuje ją także
        # przy zwiniętej ręce, bo okno reakcji mija z następnym krokiem gry (RULES.md 54.8).
        entry: dict[str, Any] = {
            "card_id": card_id, "playable": False, "reason": None, "implemented": False,
            "reaction": spec is None or spec.trigger is not TriggerKind.ACTION,
        }
        result.append(entry)
        over = hand_limit.over_limit_reason(state, player_id)
        if over is not None:  # R_action_cards: nadwyżki nie wolno „zagrać do siedmiu”
            entry["reason"] = over
            continue
        if promissory_play.silenced(state, player_id):
            entry["reason"] = "Political Secret: you cannot play action cards during this agenda."
            continue
        banned = forbidden_reason(state, player_id)
        if banned is not None:
            entry["reason"] = banned
            continue
        if spec is None or spec.trigger is not TriggerKind.ACTION:
            # Karta reakcji: zagrywalna, gdy silnik ma TERAZ otwarte pasujące okno (RULES.md 53.5).
            ok, reason, _window = reaction_cards.available(state, registry, player_id, card_id)
            implemented, inputs = card_inputs(state, registry, player_id, card_id)
            entry["implemented"] = implemented
            if state.held_play is not None and not card_hold.is_sabotage(card_id):
                entry["reason"] = "A played card is waiting for a possible Sabotage."
            elif state.held_play is not None and not card_hold.can_respond(
                state.held_play, player_id
            ):
                entry["reason"] = "You can no longer respond to this card."
            elif not ok:
                entry["reason"] = reason
            elif implemented and not _has_legal_choices(inputs):
                entry["reason"] = "No legal target for this card right now."
            else:
                entry["playable"] = True
            continue
        try:
            component_action.play_component_action(
                state, player_id, card_id, fire_after=False
            )
        except ValueError as exc:
            entry["reason"] = str(exc)
            continue
        implemented, inputs = card_inputs(state, registry, player_id, card_id)
        entry["implemented"] = implemented
        if implemented and not _has_legal_choices(inputs):
            entry["reason"] = "No legal target for this card right now."
            continue
        entry["playable"] = True
    return result


def _play_reaction_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any],
    now: float | None = None,
) -> tuple[GameState, bool]:
    """Zagranie karty REAKCJI (when/after/before/at start/at end) w otwartym oknie.

    To NIE jest akcja tury: nie zużywa akcji i może ją zagrać każdy gracz, któremu pasuje okno
    (``reaction_cards.available``). Efekt dostaje okno w ``params["__window"]``. Praca na klonie:
    błąd = zero zmian.
    """
    ok, reason, window = reaction_cards.available(state, registry, player_id, card_id)
    if not ok or window is None:
        raise ValueError(reason or "There is no open window for this card right now.")
    new_state = state.clone()
    window_dict = window.as_dict()
    eligible = card_hold.eligible_players(new_state, player_id, card_id) if now is not None else []
    if now is not None and eligible:
        # Walidacja parametrów na kopii (błąd = zero zmian); efekt dopiero przy zwolnieniu.
        probe = new_state.clone()
        run_reaction(probe, registry, player_id, card_id, params, window_dict)
        if new_state.held_play is not None and card_hold.is_sabotage(card_id):
            # Sabotage na czekającą kartę czeka na Instinct Training (F_xxcha, RULES.md 62.9).
            countered = card_hold.begin_counter(
                new_state, registry, player_id, card_id, params, eligible, now=now,
                window=window_dict,
            )
            return countered, True
        held = card_hold.begin(
            new_state, registry, player_id, card_id, params, eligible, now=now, is_action=False,
            window=window_dict,
        )
        return held, rules_hooks.effect_for(effect_key(card_id)) is not None
    implemented = run_reaction(new_state, registry, player_id, card_id, params, window_dict)
    return new_state, implemented


def run_reaction(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any],
    window: Mapping[str, Any],
) -> bool:
    """Wykonuje zagranie karty reakcji (mutuje ``state``): zdarzenie, efekt, odrzucenie."""
    triggers.fire(
        state, GameEvent.ACTION_CARD_PLAYED, Moment.WHEN, subject=player_id,
        ctx={"player": player_id, "card": card_id},
    )
    effect = rules_hooks.effect_for(effect_key(card_id))
    if effect is not None:
        with_window = {**params, reaction_cards.WINDOW_KEY: dict(window)}
        effect(state, registry, player_id, with_window)
    agenda_phase.note_reaction_played(state, window)
    card_draw.discard_specific_action_cards(state, player_id, [card_id])
    return effect is not None


def _run_action(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any],
) -> bool:
    """Wykonuje efekt karty ACTION (mutuje ``state``; akcję tury zużył wołający)."""
    triggers.fire(
        state, GameEvent.ACTION_CARD_PLAYED, Moment.WHEN, subject=player_id,
        ctx={"player": player_id, "card": card_id},
    )
    effect = rules_hooks.effect_for(effect_key(card_id))
    if effect is not None:
        effect(state, registry, player_id, params)
    card_draw.discard_specific_action_cards(state, player_id, [card_id])
    triggers.fire(
        state, GameEvent.COMPONENT_ACTION, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "component": card_id},
    )
    return effect is not None


def execute_played(state: GameState, registry: StaticDataRegistry, held: HeldPlay) -> bool:
    """Wykonuje efekt karty z ``held_play`` (wołane przez ``card_hold.resolve``; mutuje ``state``).

    Karta musi być już z powrotem w ręce zagrywającego. Dla karty ACTION akcja tury była zużyta
    przy zagraniu, więc tu nie jest zużywana ponownie.
    """
    if held.is_action:
        return _run_action(state, registry, held.player_id, held.card_id, held.params)
    return run_reaction(
        state, registry, held.player_id, held.card_id, held.params, held.window or {}
    )


def play_action_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    actor_id: str | None = None,
    now: float | None = None,
) -> tuple[GameState, bool]:
    """Aktywny gracz zagrywa kartę akcji z oknem ``ACTION`` (jego akcja w turze).

    Kolejność: walidacje (czyja tura, faza, okno, jedna akcja - przez ``component_action``;
    karta w ręce; okno karty) -> efekt na klonie -> odrzucenie karty. Błąd na dowolnym etapie
    = ``ValueError`` i ZERO zmian (praca na klonie).

    Returns:
        ``(nowy stan, implemented)``; ``implemented=False`` = karta nie ma jeszcze efektu w silniku
        (zagrana i odrzucona, skutek rozstrzyga operator).

    Raises:
        ValueError: Karta nieznana / spoza ręki / nie ma okna ACTION, nie ta tura, złe parametry.

    ``now`` (s epoch z zegara serwera) włącza okno hold-play (``core/card_hold.py``): gdy ktoś inny
    mógłby odpowiedzieć Sabotage, efekt czeka w ``state.held_play`` (wynik: stan z ``held_play``).
    Bez ``now`` karta wykonuje się natychmiast, jak dotąd.
    """
    if actor_id is not None and actor_id != player_id:
        raise ValueError(f"{actor_id} cannot play a card for {player_id}.")
    if state.held_play is not None and not card_hold.is_sabotage(card_id):
        card_hold.require_no_hold(state)  # w trakcie okna wolno tylko Sabotage
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if card_id not in player.private.action_cards:
        raise ValueError(f"You do not have the action card {card_id}.")
    if promissory_play.silenced(state, player_id):
        raise ValueError("Political Secret: you cannot play action cards during this agenda.")
    banned = forbidden_reason(state, player_id)
    if banned is not None:
        raise ValueError(banned)
    over = hand_limit.over_limit_reason(state, player_id)
    if over is not None:
        raise ValueError(over)
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
    if not isinstance(card, ActionCardDef):
        raise ValueError(f"Unknown action card: {card_id}")
    spec = registry.catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, card_id))
    if spec is None or spec.trigger is not TriggerKind.ACTION:
        return _play_reaction_card(state, registry, player_id, card_id, params or {}, now)

    new_state = component_action.play_component_action(
        state, player_id, card_id, fire_after=False
    )
    eligible = card_hold.eligible_players(new_state, player_id, card_id) if now is not None else []
    if now is not None and eligible:
        # Walidacja parametrów na kopii (błąd = zero zmian); efekt dopiero przy zwolnieniu.
        probe = new_state.clone()
        _run_action(probe, registry, player_id, card_id, params or {})
        held = card_hold.begin(
            new_state, registry, player_id, card_id, params or {}, eligible, now=now, is_action=True
        )
        return held, rules_hooks.effect_for(effect_key(card_id)) is not None
    implemented = _run_action(new_state, registry, player_id, card_id, params or {})
    return new_state, implemented
