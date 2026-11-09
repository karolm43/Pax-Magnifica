"""Silnik zdarzeń: ``fire`` uruchamia hooki TRIGGER/REPLACE na (zdarzenie, moment) — RULES.md 54.

Reguła bazowa woła ``fire(state, ZDARZENIE, MOMENT, ...)`` w miejscu, gdzie coś może zareagować;
hooki rejestrują się przez ``rules_hooks.on_event``. Pusty rejestr = brak skutków (wywołanie jest
tanie), więc emisję można dopinąć do reguł bez zmiany ich zachowania.

Reguły czasu (``docs/rules_tirules/R_abilities.md``, sekcja Timing):
* zdarzenia „when” rozstrzygają się przed „after” (wołający emituje je w tej kolejności);
* ta sama chwila w FAZIE AKCJI: kolejność inicjatywy, od gracza aktywnego; w fazie strategii i
  agendy: od mówcy zgodnie z zegarem;
* zdolność z komponentu w grze jest OBOWIĄZKOWA, chyba że ma „may” — wtedy powstaje OFERTA
  (``PendingOffer``) i okno REACTION dla graczy z publicznym źródłem. Karty z ręki ofert nie tworzą
  (STOP, RULES.md 43.4), bo samo pytanie zdradzałoby posiadanie karty.
* REPLACE („instead of”) ma pierwszeństwo przed wszystkimi TRIGGER-ami tej chwili; pierwszy hook,
  który zwróci prawdę, zastępuje zdarzenie (``FireResult.replaced``) i kończy rozstrzyganie —
  wołający POMIJA wtedy swój krok.

Uproszczenia (⚠ RULES.md 54): okno REACTION obsługuje gracza po kolei (nie ma przeplatania
„po jednej zdolności na gracza” z R_abilities), jedno okno naraz.

Funkcje MUTUJĄ przekazany stan — wołający pracuje na klonie roboczym.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core import active_effects, offer_inputs, rules_hooks
from src.core.game_events import Duration, GameEvent, Moment, event_point
from src.core.game_state import (
    GameState,
    PendingOffer,
    Phase,
    TimingWindow,
    WindowType,
)
from src.core.rules_hooks import Hook, HookKind

# Zdarzenia kończące zakres efektu trwałego -> zakres, który wygasa (RULES.md 54).
EXPIRY: dict[tuple[GameEvent, Moment], Duration] = {
    (GameEvent.TURN, Moment.END): Duration.TURN,
    (GameEvent.TACTICAL_ACTION, Moment.END): Duration.TACTICAL_ACTION,
    (GameEvent.COMBAT, Moment.END): Duration.COMBAT,
    (GameEvent.COMBAT_ROUND, Moment.END): Duration.COMBAT_ROUND,
    (GameEvent.INVASION, Moment.END): Duration.INVASION,
    (GameEvent.PHASE, Moment.END): Duration.PHASE,
    (GameEvent.ROUND, Moment.END): Duration.ROUND,
    (GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER): Duration.AGENDA,
}

_MAX_DEPTH = 12  # ochrona przed nieskończoną rekurencją (hook emitujący to samo zdarzenie)
_depth = 0


@dataclass
class FireResult:
    """Wynik emisji zdarzenia."""

    replaced: bool = False  # hook REPLACE zastąpił zdarzenie - wołający pomija swój krok
    ran: list[str] = field(default_factory=list)  # etykiety uruchomionych hooków (kolejność)
    offers: list[PendingOffer] = field(default_factory=list)  # oferty opcjonalnych reakcji


def resolution_order(state: GameState) -> list[str]:
    """Kolejność rozstrzygania zdolności o tym samym czasie (R_abilities).

    Faza akcji: inicjatywa, zaczynając od gracza aktywnego. Pozostałe fazy: od mówcy zgodnie z
    zegarem (``seating_order``). Zwraca tylko istniejących graczy.
    """
    if not state.players:
        return []
    if state.phase is Phase.ACTION and state.active_player_id in state.players:
        from src.core import turn_flow  # lokalnie: turn_flow importuje ten moduł

        base = turn_flow.turn_order(state)
        start = base.index(state.active_player_id) if state.active_player_id in base else 0
        return base[start:] + base[:start]
    seats = [pid for pid in state.seating_order if pid in state.players] or sorted(state.players)
    speaker = state.speaker_id
    start = seats.index(speaker) if speaker in seats else 0
    return seats[start:] + seats[:start]


def _jsonable(value: Any) -> Any:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list | tuple | set | frozenset):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return str(value)


def _matches(hook: Hook, ctx: dict[str, Any]) -> bool:
    return all(str(ctx.get(key)) == value for key, value in hook.where)


def _label(hook: Hook) -> str:
    return hook.label or hook.covers or f"{hook.source.kind}:{hook.source.component_id}"


def fire(
    state: GameState,
    event: GameEvent,
    moment: Moment,
    *,
    subject: str | None = None,
    ctx: dict[str, Any] | None = None,
    open_window: bool = True,
) -> FireResult:
    """Emituje zdarzenie: uruchamia hooki posiadaczy źródeł w kolejności rozstrzygania.

    Args:
        state: Stan roboczy (klon) — hooki go mutują.
        subject: Gracz, którego dotyczy zdarzenie (``ctx["subject"]``).
        ctx: Dane zdarzenia dla hooków i filtrów ``where`` (np. ``{"phase": "strategy"}``).
        open_window: Czy oferty opcjonalnych reakcji mają otworzyć okno REACTION.

    Returns:
        ``FireResult``; ``replaced=True`` oznacza, że wołający ma pominąć swój krok.
    """
    global _depth
    if _depth >= _MAX_DEPTH:
        raise ValueError(f"Event recursion too deep at {event.value}/{moment.value}.")
    context: dict[str, Any] = dict(ctx or {})
    context["event"] = event.value
    context["moment"] = moment.value
    if subject is not None:
        context["subject"] = subject
    point = event_point(event, moment)
    result = FireResult()
    order = resolution_order(state)
    _depth += 1
    try:
        for kind in (HookKind.REPLACE, HookKind.TRIGGER):
            for pid in order:
                for hook in rules_hooks.hooks_at(point, state, pid):
                    if hook.kind is not kind or not _matches(hook, context):
                        continue
                    if hook.condition is not None and not hook.condition(state, pid, context):
                        continue
                    if hook.decide:
                        _decide(state, pid, hook, event, moment, context, result)
                        continue
                    if hook.optional:
                        result.offers.append(_new_offer(state, pid, hook, event, moment, context))
                        continue
                    outcome = hook.fn(state, pid, context)
                    result.ran.append(_label(hook))
                    if kind is HookKind.REPLACE and outcome:
                        result.replaced = True
                        _publish_offers(state, result, order, event, moment, open_window)
                        return result
    finally:
        _depth -= 1
    _publish_offers(state, result, order, event, moment, open_window)
    scope = EXPIRY.get((event, moment))
    if scope is not None:
        active_effects.expire(state, scope)
    return result


def _new_offer(
    state: GameState,
    pid: str,
    hook: Hook,
    event: GameEvent,
    moment: Moment,
    ctx: dict[str, Any],
    *,
    decider: str | None = None,
    mandatory: bool = False,
) -> PendingOffer:
    """Nowa oferta: ``pid`` = właściciel źródła, ``decider`` = kto odpowiada (domyślnie on)."""
    who = decider or pid
    return PendingOffer(
        id=active_effects.next_id(state, "of"),
        player_id=who,
        event=event.value,
        moment=moment.value,
        hook_seq=hook.seq,
        label=_label(hook),
        ctx=_jsonable({**ctx, "decider": who}),
        owner_id=None if who == pid else pid,
        mandatory=mandatory,
    )


def _decide(
    state: GameState,
    pid: str,
    hook: Hook,
    event: GameEvent,
    moment: Moment,
    context: dict[str, Any],
    result: FireResult,
) -> None:
    """Decyzja obowiązkowa hooka (``decide``): silnik NIE wybiera za gracza.

    Realny wybór (więcej niż jedna legalna odpowiedź) -> oferta obowiązkowa dla decydenta.
    Dokładnie jedna legalna odpowiedź -> stosujemy ją od razu (nie ma czego decydować);
    brak legalnej odpowiedzi -> efekt się nie odbywa.
    """
    decider = hook.decider(state, pid, context) if hook.decider is not None else pid
    registry = rules_hooks.bound_registry()
    inputs = hook.inputs(state, registry, decider, context) if hook.inputs is not None else []
    if offer_inputs.needs_player(inputs):
        result.offers.append(
            _new_offer(state, pid, hook, event, moment, context, decider=decider, mandatory=True)
        )
        return
    if not offer_inputs.has_legal_answer(inputs):
        return
    params = offer_inputs.single_params(inputs)
    hook.fn(state, pid, {**context, "decider": decider, "params": params, "accepted": True})
    result.ran.append(_label(hook))


def _publish_offers(
    state: GameState,
    result: FireResult,
    order: list[str],
    event: GameEvent,
    moment: Moment,
    open_window: bool,
) -> None:
    """Zapisuje oferty w stanie i otwiera okno REACTION (o ile nic innego nie trwa)."""
    if not result.offers:
        return
    state.pending_offers = [*state.pending_offers, *result.offers]
    if not open_window or state.pending_window is not None:
        return  # jedno okno naraz: oferty czekają w stanie na swoją kolej
    offered = {offer.player_id for offer in result.offers}
    queue = [pid for pid in order if pid in offered]
    state.pending_window = TimingWindow(
        window_type=WindowType.REACTION,
        queue=queue,
        context={"event": event.value, "moment": moment.value},
    )


def offers_for(state: GameState, player_id: str) -> list[PendingOffer]:
    """Oferty czekające na decyzję gracza."""
    return [o for o in state.pending_offers if o.player_id == player_id]


def _advance_window(state: GameState, player_id: str) -> None:
    """Po odpowiedzi: gdy gracz nie ma ofert, kolejka REACTION idzie dalej; koniec zamyka okno."""
    window = state.pending_window
    if window is None or window.window_type is not WindowType.REACTION:
        return
    if window.current_responder != player_id or offers_for(state, player_id):
        return
    window.responded = [*window.responded, player_id]
    window.cursor += 1
    if window.is_complete:
        state.pending_window = None


def _take_offer(state: GameState, player_id: str, offer_id: str) -> PendingOffer:
    offer = next((o for o in state.pending_offers if o.id == offer_id), None)
    if offer is None:
        raise ValueError(f"Unknown offer: {offer_id}")
    if offer.player_id != player_id:
        raise ValueError(f"The offer {offer_id} belongs to {offer.player_id}, not {player_id}.")
    window = state.pending_window
    if (
        window is not None
        and window.window_type is WindowType.REACTION
        and window.current_responder not in (None, player_id)
    ):
        raise ValueError(f"It is now {window.current_responder}'s turn to respond.")
    state.pending_offers = [o for o in state.pending_offers if o.id != offer_id]
    return offer


def accept_offer(
    state: GameState, player_id: str, offer_id: str, params: dict[str, Any] | None = None
) -> GameState:
    """Gracz przyjmuje ofertę: uruchamia jej hook (``ctx['params']`` = wybory gracza).

    Raises:
        ValueError: Oferta nieznana / cudza / nie ta kolej, albo gracz nie ma już źródła hooka.
    """
    work = state.clone()
    offer = _take_offer(work, player_id, offer_id)
    owner = offer.owner_id or offer.player_id
    hook = rules_hooks.hook_by_seq(offer.hook_seq)
    if hook is None or hook.source not in rules_hooks.owned_sources(work, owner):
        raise ValueError("The source of this ability is no longer in play.")
    # Odpowiedź gracza sprawdzamy względem legalnych opcji liczonych TERAZ przez silnik.
    inputs = (
        hook.inputs(work, rules_hooks.bound_registry(), player_id, offer.ctx)
        if hook.inputs is not None
        else []
    )
    cleaned = offer_inputs.validate_params(inputs, dict(params or {}))
    context = {**offer.ctx, "decider": player_id, "params": cleaned, "accepted": True}
    hook.fn(work, owner, context)
    _advance_window(work, player_id)
    return work


def decline_offer(state: GameState, player_id: str, offer_id: str) -> GameState:
    """Gracz odrzuca ofertę (zdolność z „may” można pominąć; decyzji obowiązkowej nie)."""
    work = state.clone()
    pending = next((o for o in work.pending_offers if o.id == offer_id), None)
    if pending is not None and pending.mandatory:
        raise ValueError("This decision is mandatory - choose one of the options.")
    _take_offer(work, player_id, offer_id)
    _advance_window(work, player_id)
    return work
