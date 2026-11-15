"""Jawny widok okien czasowych otwartych TERAZ (RULES.md 54.9) — dla paska „Timing windows” w UI.

Okna kart z ręki (``reaction_cards.open_windows``) są funkcją stanu gry: istnieją, dopóki gra stoi w
danym kroku, i znikają bez śladu, gdy ktoś wykona następny krok. Ten moduł opisuje je po angielsku
(teksty widoczne w UI), żeby KAŻDY gracz widział, jakie okno jest otwarte i co je zamknie.

Widok NIE zależy od ręki (RULES.md 43.4): pokazuje tylko okna jawne (``OpenWindow.public``)
i nie mówi, kto ma kartę. Pomija okna, na które NIC w grze nie może już zareagować: liczymy to
z informacji jawnej - karty akcji poza stosem odrzuconych (talia + wszystkie ręce RAZEM, czyli
„wszystko, czego nie odrzucono”) i notki na rękach (zbiorczo), tylko z efektem w silniku.
Czy gracz ma coś do zagrania, wie tylko on (``/action-card/playable``).
Moduł jest czysty: ``state -> dane``, bez mutacji.
"""

from __future__ import annotations

import json
from typing import Any

from src.core import promissory_play, reaction_cards, rules_hooks
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

_E = GameEvent

# Zdanie zdarzenia dla momentów when/after/before („After <clause>”).
_CLAUSE: dict[GameEvent, str] = {
    _E.UNIT_ABILITY_USED: "a unit ability is used",
    _E.HITS_ASSIGNED: "hits are assigned",
    _E.STRATEGIC_ACTION: "a strategic action would be performed",
    _E.SHIPS_MOVED: "ships move into the active system",
    _E.AGENDA_VOTES_CAST: "votes are cast",
    _E.UNIT_SUSTAIN_DAMAGE: "a unit uses Sustain Damage",
    _E.UNIT_DESTROYED: "a unit is destroyed",
    _E.UNITS_COMMITTED: "ground forces are committed",
    _E.TRANSACTION: "a transaction is resolved",
    _E.TECHNOLOGY_RESEARCH: "a technology is researched",
    _E.SYSTEM_ACTIVATED: "a system is activated",
    _E.STRATEGY_CARD_CHOSEN: "a strategy card is chosen",
    _E.STRATEGY_CARDS_RETURNED: "strategy cards are returned",
    _E.RETREAT_DECLARED: "a retreat is announced",
    _E.PRODUCTION_USED: "units use PRODUCTION",
    _E.PLANET_CONTROL_GAINED: "control of a planet is gained",
    # Okno „After you perform an action” (reactions_misc.after_action) - DOWOLNA akcja, także
    # taktyczna/strategiczna; zdarzenie nosi nazwę COMPONENT_ACTION z przyczyn historycznych.
    _E.COMPONENT_ACTION: "an action is performed",
    _E.COMMODITIES_REPLENISHED: "commodities are replenished",
    _E.COMBAT_WON: "a combat is won",
    _E.COMBAT_ROLL: "combat dice are rolled",
    _E.AGENDA_REVEALED: "an agenda is revealed",
    _E.AGENDA_ELECTED: "a player is elected",
    _E.ACTION_CARD_PLAYED: "an action card is played",
    _E.ACTION_CARD_DISCARDED: "an action card is discarded",
}

# Rzeczownik dla momentów start/end/during („At the start of <noun>”).
_NOUN: dict[GameEvent, str] = {
    _E.COMBAT: "combat",
    _E.COMBAT_ROUND: "a combat round",
    _E.COMBAT_STEP: "a combat step",
    _E.INVASION: "an invasion",
    _E.TURN: "a turn",
    _E.PHASE: "a phase",
    _E.TACTICAL_ACTION: "a tactical action",
    _E.AGENDA_OUTCOME_RESOLVED: "the agenda outcome resolution",
}

_PREFIX: dict[Moment, str] = {
    Moment.WHEN: "When",
    Moment.AFTER: "After",
    Moment.BEFORE: "Before",
    Moment.START: "At the start of",
    Moment.END: "At the end of",
    Moment.DURING: "During",
    Moment.INSTEAD: "Instead of",
}

_STEP_NAMES = {
    "announce_retreats": "the Announce Retreats step",
    "space_cannon_offense": "the Space Cannon Offense step",
}
_ROLL_KINDS = {
    "afb": "Anti-Fighter Barrage dice are rolled",
    "bombardment": "Bombardment dice are rolled",
    "space_cannon": "Space Cannon dice are rolled",
}

# Co zamyka okno — tylko tam, gdzie wynika to wprost z dostawcy okna (reszta: następny krok gry).
_CLOSES: dict[tuple[GameEvent, Moment], str] = {
    (_E.COMBAT_WON, Moment.AFTER): "Ends when the battle is closed",
    (_E.AGENDA_REVEALED, Moment.WHEN): "Ends with the first vote or abstention",
    (_E.AGENDA_REVEALED, Moment.AFTER): "Ends with the first vote or abstention",
    (_E.AGENDA_VOTES_CAST, Moment.AFTER): "Ends with the next vote",
    (_E.HITS_ASSIGNED, Moment.BEFORE): "Ends when the losses are confirmed",
    (_E.COMBAT_ROUND, Moment.START): "Ends when the combat dice are rolled",
    (_E.STRATEGIC_ACTION, Moment.WHEN): "Ends with the first choice of the primary ability",
}
DEFAULT_CLOSES = "Ends with the next game step"

# Okna wspólne dla stołu: podmiot (mówca) jest techniczny, nie pokazujemy go jako „czyje” okno.
_NO_SUBJECT = {_E.AGENDA_REVEALED, _E.PHASE, _E.AGENDA_OUTCOME_RESOLVED}


def _noun(event: GameEvent, ctx: dict[str, Any]) -> str:
    if event is GameEvent.PHASE and ctx.get("phase"):
        return f"the {ctx['phase']} phase"
    if event is GameEvent.COMBAT and ctx.get("kind") in ("space", "ground"):
        return f"{ctx['kind']} combat"
    if event is GameEvent.COMBAT_STEP and ctx.get("step"):
        return _STEP_NAMES.get(str(ctx["step"]), f"the {ctx['step']} step")
    return _NOUN.get(event, event.value)


def _clause(event: GameEvent, ctx: dict[str, Any], moment: Moment) -> str:
    if event is GameEvent.TRANSACTION and moment is Moment.WHEN:
        return "a transaction is being negotiated"
    if event is GameEvent.COMBAT_ROLL and str(ctx.get("kind")) in _ROLL_KINDS:
        return _ROLL_KINDS[str(ctx["kind"])]
    if event is GameEvent.COMBAT_WON and ctx.get("kind") in ("space", "ground"):
        return f"a {ctx['kind']} combat is won"
    return _CLAUSE.get(event, event.value)


def label(event: GameEvent, moment: Moment, ctx: dict[str, Any]) -> str:
    """Angielska etykieta okna („After a space combat is won”, „At the start of a combat round”)."""
    prefix = _PREFIX.get(moment, moment.value.capitalize())
    if moment in (Moment.START, Moment.END, Moment.DURING):
        return f"{prefix} {_noun(event, ctx)}"
    return f"{prefix} {_clause(event, ctx, moment)}"


def window_key(window: reaction_cards.OpenWindow) -> str:
    """Stały klucz okna (UI porównuje klucze między odświeżeniami, żeby pokazać „zamknięte”)."""
    ctx = {k: v for k, v in window.ctx.items() if k != "round" or window.event is _E.COMBAT_ROUND}
    data = json.dumps(ctx, sort_keys=True, default=str)
    return f"{window.event.value}|{window.moment.value}|{data}"


Point = tuple[GameEvent, Moment]


def live_relations(state: GameState, registry: StaticDataRegistry) -> dict[Point, set[str]]:
    """Okna, na które coś w grze może jeszcze zareagować z ręki, z relacją gracza do podmiotu
    (``reaction_cards.SELF`` / ``OTHER`` / ``ANY``) - z informacji jawnej.

    Karty akcji: talia + ręce wszystkich graczy razem = każda karta spoza stosu odrzuconych, więc
    zbiór nie mówi, kto ją ma. Notki: suma rąk (które notki są w grze, wiadomo z frakcji);
    relacja notek = ``ANY`` (ich podmiot zależy od właściciela).
    """
    found: dict[Point, set[str]] = {}
    cards = set(state.decks.action_card_deck)
    for player in state.players.values():
        cards.update(player.private.action_cards)
    for card_id in cards:
        if rules_hooks.effect_for(f"action_cards:{card_id}") is None:
            continue
        spec = reaction_cards.spec_for(registry, card_id)
        if spec is None:
            continue
        for point in spec.points:
            found.setdefault(point, set()).add(spec.subject or reaction_cards.ANY)
    for player in state.players.values():
        for note_id in player.private.promissory_notes:
            try:
                template, _owner = promissory_play.resolve(state, registry, note_id)
            except (KeyError, ValueError):
                continue
            if rules_hooks.effect_for(promissory_play.effect_key(template)) is None:
                continue
            for point in promissory_play.reaction_points(registry, template):
                found.setdefault(point, set()).add(reaction_cards.ANY)
    return found


def live_points(state: GameState, registry: StaticDataRegistry) -> set[Point]:
    """Okna, na które coś w grze może jeszcze zareagować z ręki (klucze ``live_relations``)."""
    return set(live_relations(state, registry))


def describe_open_windows(
    state: GameState, registry: StaticDataRegistry | None = None
) -> list[dict[str, Any]]:
    """Jawne okna otwarte teraz: klucz, zdarzenie, moment, etykieta, podmiot, co je zamyka.

    Duplikaty (to samo okno od dwóch dostawców) są scalane; pomijamy okna niejawne i te, na
    które nic w grze nie może już zareagować (``live_points``).
    """
    live = live_points(state, registry or rules_hooks.bound_registry())
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for window in reaction_cards.open_windows(state):
        if not window.public or (window.event, window.moment) not in live:
            continue
        key = window_key(window)
        if key in seen:
            continue
        seen.add(key)
        position = window.ctx.get("position")
        out.append(
            {
                "key": key,
                "event": window.event.value,
                "moment": window.moment.value,
                "label": label(window.event, window.moment, window.ctx),
                "subject": None if window.event in _NO_SUBJECT else window.subject,
                "position": str(position) if position is not None else None,
                "closes": _CLOSES.get((window.event, window.moment), DEFAULT_CLOSES),
            }
        )
    return out
