"""Zagrywanie promissory notes z ręki, strefa gry i zwrot do właściciela — RULES.md 61.2.

Źródło reguł: ``docs/rules_tirules/R_promissory_notes.md``, ``C_promissory_notes.md``.

* **Id w ręce a dane.** Notki ogólne mają w danych szablon z kolorem (``<color>_cf``); w ręce
  leży konkretna kopia (``red_cf``). :func:`resolve` zwraca ``(szablon, właściciel)``: właściciel
  notki koloru = gracz tego koloru, notki frakcyjnej = gracz tej frakcji (rodzina).
* **Zakaz własnej notki** (R_promissory_notes: „A player cannot play their color's or faction's
  promissory notes").
* **Okno.** Notka z ``ACTION:`` = akcja komponentu tury. Pozostałe są REAKCJAMI w modelu okien
  kart akcji (RULES.md 53.5): zagrywalne, gdy silnik ma TERAZ otwarte okno z tekstu notki
  (``reaction_cards.open_windows``). „The <color> player" w oknie = właściciel notki jest podmiotem
  zdarzenia. Ręka zostaje ukryta (silnik nigdy nie pyta „czy masz notkę").
* **Po efekcie** (R_promissory_notes: zwrot PO pełnym rozstrzygnięciu): notka ze strefą gry
  (``playArea``) ląduje odkryta w strefie gracza; z „purge this card" znika z gry; pozostałe wracają
  do ręki właściciela.
* **„When you receive this card… must place it faceup"** (``playImmediately``: Alliance, Support
  for the Throne…) — :func:`on_received` kładzie notkę do strefy od razu przy otrzymaniu.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from src.core import (
    agenda_phase,
    component_action,
    offer_inputs,
    promissory_notes,
    reaction_cards,
    rules_hooks,
    triggers,
)
from src.core.components import ComponentCategory, PromissoryNoteDef
from src.core.game_events import GameEvent, Moment, classify_window
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

COLOR = "<color>"
CEASEFIRE_EFFECT = "promissory_notes:ceasefire"  # efekt trwały na właścicielu (akcja taktyczna)
POLITICAL_SECRET_EFFECT = "promissory_notes:political_secret"  # efekt na właścicielu (agenda)
_ACTION = re.compile(r"^\s*ACTION\s*:")
_PURGE_SELF = re.compile(r"\bpurge this card\b", re.IGNORECASE)

# Warunek dodatkowy zagrania reakcji: (stan, rejestr, gracz, okno) -> powód odmowy albo None.
# Notki, których okno nie ma relacji „you"/„the <color> player" do podmiotu (np. „After you and
# your opponent roll dice" — dotyczy obu stron walki); warunek notki sprawdza resztę.
_ANY_SUBJECT: set[str] = set()


def any_subject(template: str) -> None:
    """Okno notki pasuje niezależnie od podmiotu zdarzenia (warunek notki pilnuje reszty)."""
    _ANY_SUBJECT.add(template)


NoteCondition = Callable[
    [GameState, StaticDataRegistry, str, reaction_cards.OpenWindow], str | None
]
_CONDITIONS: dict[str, NoteCondition] = {}


def condition(template: str) -> Callable[[NoteCondition], NoteCondition]:
    """Rejestruje warunek zagrania notki-reakcji (np. „system zawiera Twoje jednostki")."""

    def decorate(fn: NoteCondition) -> NoteCondition:
        if template in _CONDITIONS:
            raise ValueError(f"Condition already registered for {template}.")
        _CONDITIONS[template] = fn
        return fn

    return decorate


ActionBlocker = Callable[[GameState, StaticDataRegistry, str], str | None]
_ACTION_BLOCKERS: dict[str, ActionBlocker] = {}


def action_blocker(template: str) -> Callable[[ActionBlocker], ActionBlocker]:
    """Rejestruje warunek zagrania notki ACTION (powód odmowy albo None) - np. Fires of the
    Gashlai: nie dla gracza, który ma już technologię war suna (F_muaat)."""

    def decorate(fn: ActionBlocker) -> ActionBlocker:
        if template in _ACTION_BLOCKERS:
            raise ValueError(f"Action blocker already registered for {template}.")
        _ACTION_BLOCKERS[template] = fn
        return fn

    return decorate


def silenced(state: GameState, player_id: str) -> bool:
    """Political Secret: gracz nie może grać kart akcji ani używać zdolności frakcji."""
    return any(
        e.key == POLITICAL_SECRET_EFFECT and e.owner == player_id for e in state.active_effects
    )


def ceasefire_blocks(state: GameState, player_id: str) -> bool:
    """Ceasefire: gracz nie może ruszać jednostek do aktywnego systemu."""
    return any(e.key == CEASEFIRE_EFFECT and e.owner == player_id for e in state.active_effects)


def effect_key(template: str) -> str:
    """Klucz notki w rejestrze efektów (``promissory_notes:<szablon>``)."""
    return f"{ComponentCategory.PROMISSORY_NOTE.value}:{template}"


# --- Dane i właściciel -------------------------------------------------------------------------


def _templates(registry: StaticDataRegistry) -> Mapping[str, Any]:
    return registry.catalog.all(ComponentCategory.PROMISSORY_NOTE)


def note_def(registry: StaticDataRegistry, template: str) -> PromissoryNoteDef:
    """Definicja notki (po szablonie).

    Raises:
        ValueError: Nieznana notka.
    """
    card = _templates(registry).get(template)
    if not isinstance(card, PromissoryNoteDef):
        raise ValueError(f"Unknown promissory note: {template}")
    return card


def resolve(
    state: GameState, registry: StaticDataRegistry, note_id: str
) -> tuple[str, str | None]:
    """``(szablon, właściciel)`` notki z ręki/strefy (właściciel ``None``, gdy nie gra).

    Raises:
        ValueError: Id nie pasuje do żadnej notki w danych.
    """
    templates = _templates(registry)
    if note_id in templates:
        card = templates[note_id]
        faction = getattr(card, "faction", None)
        return note_id, _faction_owner(state, registry, faction)
    for template in templates:
        if COLOR not in template:
            continue
        pattern = re.escape(template).replace(re.escape(COLOR), "(?P<color>[a-z0-9]+)")
        match = re.fullmatch(pattern, note_id)
        if match is None:
            continue
        color = match.group("color")
        owner = next((pid for pid, p in state.players.items() if p.color == color), None)
        return template, owner
    raise ValueError(f"Unknown promissory note: {note_id}")


def _faction_owner(
    state: GameState, registry: StaticDataRegistry, faction: str | None
) -> str | None:
    if not faction:
        return None
    for pid, player in state.players.items():
        own = registry.factions.get(player.faction or "")
        family = registry.faction_family(own) if own is not None else None
        if faction in (player.faction, family):
            return pid
    return None


def note_text(state: GameState, registry: StaticDataRegistry, note_id: str) -> tuple[str, str]:
    """``(nazwa, tekst)`` notki z kolorem właściciela w miejscu ``<color>``."""
    template, owner = resolve(state, registry, note_id)
    card = note_def(registry, template)
    text = " ".join(card.texts.values())
    color = state.players[owner].color if owner is not None else None
    return card.name or template, text.replace(COLOR, color or "owner")


def _window_text(text: str) -> str:
    return text.split(":", 1)[0] if ":" in text else ""


def is_action(registry: StaticDataRegistry, template: str) -> bool:
    """Czy notka jest zagrywana jako akcja komponentu („ACTION:")."""
    text = " ".join(str(t) for t in note_def(registry, template).texts.values())
    return _ACTION.search(text) is not None


def _points(registry: StaticDataRegistry, template: str) -> list[tuple[Any, Moment]]:
    card = note_def(registry, template)
    ref = classify_window(_window_text(" ".join(card.texts.values())))
    return [(ref.event, ref.moment)] if ref is not None else []


def reaction_points(registry: StaticDataRegistry, template: str) -> list[tuple[Any, Moment]]:
    """Okna (zdarzenie, moment), w których notka reaguje (pusto = akcja albo okno nieznane)."""
    return [] if is_action(registry, template) else _points(registry, template)


def reaction_moments(registry: StaticDataRegistry, template: str) -> set[str]:
    """Momenty (``when``/``after``…) okien, w których gra się notkę-reakcję (puste dla ACTION)."""
    return {moment.value for _event, moment in reaction_points(registry, template)}


def _subject_ok(
    window_text: str, owner: str | None, player_id: str, window: reaction_cards.OpenWindow
) -> bool:
    """„The <color> player …" = podmiotem okna jest właściciel; „you …" = sam grający."""
    lowered = window_text.lower()
    subject: str | None = window.subject
    if f"the {COLOR} player" in lowered:
        return subject is not None and subject == owner
    if re.search(r"\b(you|your)\b", lowered):
        return subject == player_id
    return True


# --- Zagrywalność ------------------------------------------------------------------------------


def _reaction_window(
    state: GameState, registry: StaticDataRegistry, player_id: str, template: str, owner: str | None
) -> tuple[reaction_cards.OpenWindow | None, str | None]:
    card = note_def(registry, template)
    window_text = _window_text(" ".join(card.texts.values()))
    points = _points(registry, template)
    if not points:
        return None, "The engine does not recognise this note's timing yet - resolve it by hand."
    reason: str | None = "There is no open window for this note right now."
    for window in reaction_cards.open_windows(state):
        if (window.event, window.moment) not in points:
            continue
        if template not in _ANY_SUBJECT and not _subject_ok(
            window_text, owner, player_id, window
        ):
            continue
        fn = _CONDITIONS.get(template)
        refusal = fn(state, registry, player_id, window) if fn is not None else None
        if refusal is not None:
            reason = refusal
            continue
        return window, None
    return None, reason


def _inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, template: str
) -> list[dict[str, Any]]:
    fn = rules_hooks.inputs_for(effect_key(template))
    return fn(state, registry, player_id) if fn is not None else []


def playability(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Notki z ręki gracza: czy można je zagrać TERAZ (do przeciągania z ręki). Nie mutuje."""
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    rows: list[dict[str, Any]] = []
    for note_id in dict.fromkeys(player.private.promissory_notes):
        template, owner = resolve(state, registry, note_id)
        key = effect_key(template)
        implemented = rules_hooks.effect_for(key) is not None
        row: dict[str, Any] = {
            "note_id": note_id,
            "template": template,
            "owner_id": owner,
            "playable": False,
            "reason": None,
            "implemented": implemented,
            # Notka grana w odpowiedzi na okno (nie ACTION) - UI sygnalizuje ją przy zwiniętej ręce.
            "reaction": not is_action(registry, template),
        }
        rows.append(row)
        row["reason"] = _block_reason(state, registry, player_id, note_id, template, owner)
        if row["reason"] is None and implemented and not offer_inputs.has_legal_answer(
            _inputs(state, registry, player_id, template)
        ):
            row["reason"] = "No legal target for this note right now."
        row["playable"] = row["reason"] is None
    return rows


def _block_reason(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    note_id: str,
    template: str,
    owner: str | None,
) -> str | None:
    if owner == player_id:
        return "You cannot play your own promissory note - give it to another player."
    if owner is None:
        return "The owner of this note is not in the game."
    card = note_def(registry, template)
    if card.play_immediately:
        return "This note is placed in your play area automatically when you receive it."
    if is_action(registry, template):
        try:
            component_action.play_component_action(
                state, player_id, note_id, fire_after=False, run_effect=False
            )
        except ValueError as exc:
            return str(exc)
        rules_hooks.effect_for(effect_key(template))  # ładuje pakiet hooków (rejestr blokad)
        blocker = _ACTION_BLOCKERS.get(template)
        return blocker(state, registry, player_id) if blocker is not None else None
    _window, reason = _reaction_window(state, registry, player_id, template, owner)
    return reason


# --- Zagranie ----------------------------------------------------------------------------------


def play(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    note_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    actor_id: str | None = None,
) -> tuple[GameState, bool]:
    """Gracz zagrywa notkę z ręki. Błąd = ``ValueError`` i ZERO zmian (klon).

    Returns:
        ``(nowy stan, implemented)``; bez efektu w kodzie notka jest zagrana (i zwrócona/położona
        wg tekstu), a skutek rozstrzyga operator.
    """
    if actor_id is not None and actor_id != player_id:
        raise ValueError(f"{actor_id} cannot play a promissory note for {player_id}.")
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if note_id not in player.private.promissory_notes:
        raise ValueError(f"You do not hold the promissory note {note_id}.")
    template, owner = resolve(state, registry, note_id)
    reason = _block_reason(state, registry, player_id, note_id, template, owner)
    if reason is not None:
        raise ValueError(reason)
    key = effect_key(template)
    effect = rules_hooks.effect_for(key)
    values = offer_inputs.validate_params(
        _inputs(state, registry, player_id, template), dict(params or {})
    ) if effect is not None else dict(params or {})
    if is_action(registry, template):
        new_state = component_action.play_component_action(
            state, player_id, note_id, fire_after=False, run_effect=False
        )
    else:
        new_state = state.clone()
        window, _ = _reaction_window(state, registry, player_id, template, owner)
        if window is not None:
            values[reaction_cards.WINDOW_KEY] = window.as_dict()
            agenda_phase.note_reaction_played(new_state, window.as_dict())
    values["__note"] = note_id
    values["__owner"] = owner
    if effect is not None:
        effect(new_state, registry, player_id, values)
    _dispose(new_state, registry, player_id, note_id, template, owner)
    if is_action(registry, template):
        triggers.fire(
            new_state, GameEvent.COMPONENT_ACTION, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "component": note_id},
        )
    return new_state, effect is not None


def _dispose(
    state: GameState,
    registry: StaticDataRegistry,
    holder: str,
    note_id: str,
    template: str,
    owner: str | None,
) -> None:
    """Po efekcie: strefa gry / purge / zwrot do właściciela (R_promissory_notes)."""
    card = note_def(registry, template)
    text = " ".join(card.texts.values())
    if card.play_area:
        promissory_notes.place_in_play(state, holder, note_id)
    elif _PURGE_SELF.search(text) or owner is None:
        promissory_notes.discard_from_hand(state, holder, note_id)
    else:
        promissory_notes.return_from_hand(state, holder, owner, note_id)


def on_received(state: GameState, receiver_id: str, note_id: str) -> None:
    """„When you receive this card… place it faceup in your play area" (MUTUJE ``state``).

    Wołane centralnie przez ``promissory_notes.transfer``. Efekt przy położeniu (np. +1 VP) to
    efekt notki ``register_effect`` z ``params["__received"] = True``.
    """
    registry = rules_hooks.bound_registry()
    if registry is None:
        return
    try:
        template, owner = resolve(state, registry, note_id)
    except ValueError:
        return
    card = note_def(registry, template)
    if not card.play_immediately or owner == receiver_id or owner is None:
        return
    promissory_notes.place_in_play(state, receiver_id, note_id)
    effect = rules_hooks.effect_for(effect_key(template))
    if effect is not None:
        params = {"__received": True, "__note": note_id, "__owner": owner}
        effect(state, registry, receiver_id, params)


def notes_in_play(
    state: GameState, registry: StaticDataRegistry, holder: str, template: str
) -> list[tuple[str, str | None]]:
    """Notki danego szablonu w strefie gracza: ``[(id kopii, właściciel)]``."""
    found: list[tuple[str, str | None]] = []
    for note_id in state.players[holder].promissory_notes_in_play:
        try:
            note_template, owner = resolve(state, registry, note_id)
        except ValueError:
            continue
        if note_template == template:
            found.append((note_id, owner))
    return found


def form(
    state: GameState, registry: StaticDataRegistry, player_id: str, note_id: str
) -> dict[str, Any]:
    """Opis notki dla UI: tekst z kolorem, właściciel, czy silnik ją automatyzuje i formularz."""
    template, owner = resolve(state, registry, note_id)
    name, text = note_text(state, registry, note_id)
    key = effect_key(template)
    inputs = _inputs(state, registry, player_id, template) if rules_hooks.effect_for(key) else []
    return {
        "note_id": note_id,
        "template": template,
        "owner_id": owner,
        "name": name,
        "text": text,
        "action": is_action(registry, template),
        "implemented": rules_hooks.effect_for(key) is not None,
        "inputs": inputs,
    }
