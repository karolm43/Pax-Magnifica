"""Politics (inicjatywa 3, base) — RULES.md 30.9, R_politics.

Primary (w tej kolejności): wskaż nowego mówcę (dowolny gracz BEZ żetonu mówcy, także ty),
dobierz 2 karty akcji, obejrzyj 2 górne karty talii agend i połóż każdą na górze lub na
spodzie talii (obie na jednej stronie → dowolna kolejność). Secondary (1 żeton ze strategy
pool): dobierz 2 karty akcji. Podgląd agend jest PRYWATNY - widzi go tylko właściciel karty
(opcje kroku zwracane są wyłącznie adresatowi monitu, a szkic ich nie zawiera).
"""

from __future__ import annotations

from typing import Any

from src.core import strategy_phase
from src.core.card_draw import draw_action_card, ensure_agenda_deck
from src.core.game_state import GameState
from src.core.strategy_cards.base import CardContext, CardSpec, Draft
from src.core.strategy_cards.common import str_list

INITIATIVE = 3
ACTION_CARDS_DRAWN = 2  # „draws two action cards" (primary i secondary)
AGENDA_PEEK = 2  # „top two cards of the agenda deck"
# Klucz szkicu z dobranymi kartami akcji - prywatny (prefiks „_" nie wychodzi do web-data).
PRIVATE_DRAWN_KEY = "_drawn"


def _peek(state: GameState) -> list[str]:
    return list(state.decks.agenda_deck[:AGENDA_PEEK])


def _on_step(
    state: GameState,
    ctx: CardContext,
    owner_id: str,
    step: str,
    draft: Draft,
    payload: dict[str, Any],
) -> None:
    if step == "choose_speaker":
        chosen = payload.get("player")
        if not isinstance(chosen, str) or chosen not in state.players:
            raise ValueError("Choose a player to become the speaker.")
        if chosen == state.speaker_id:
            raise ValueError("The chosen player already has the speaker token.")
        # Efekty „od góry do dołu" (R_strategic_action): mówca, potem 2 karty akcji - od razu,
        # żeby gracz widział dobrane karty przed decyzją o agendach.
        strategy_phase.set_speaker(state, chosen)
        drawn_before = len(state.players[owner_id].private.action_cards)
        for _ in range(ACTION_CARDS_DRAWN):
            draw_action_card(state, owner_id)
        hand = state.players[owner_id].private.action_cards
        # Klucz z „_" jest PRYWATNY: nie trafia do publicznego ``pendingStrategy`` (web-data),
        # widzi go tylko właściciel przez opcje kroku.
        draft[PRIVATE_DRAWN_KEY] = list(hand[drawn_before:])
        draft["speaker"] = chosen
        # Talia agend musi istnieć przed podglądem (zasiew trafia do klonu stanu).
        ensure_agenda_deck(state, ctx.registry)
    elif step == "agenda_order":
        top = str_list(payload, "top")
        bottom = str_list(payload, "bottom")
        peeked = _peek(state)
        if sorted(top + bottom) != sorted(peeked):
            raise ValueError("Place each of the viewed agenda cards on the top or the bottom.")
        draft["top"] = top
        draft["bottom"] = bottom
    else:
        raise ValueError(f"Unknown Politics step: {step}")


def _primary(
    state: GameState, ctx: CardContext, owner_id: str, draft: Draft
) -> None:
    # Mówca i karty akcji rozstrzygnięte już w kroku ``choose_speaker``; tu tylko agendy.
    ensure_agenda_deck(state, ctx.registry)
    decks = state.decks
    peeked = _peek(state)
    rest = decks.agenda_deck[len(peeked) :]
    decks.agenda_deck = [*draft.get("top", []), *rest, *draft.get("bottom", [])]


def _secondary(
    state: GameState, _ctx: CardContext, player_id: str, _payload: dict[str, Any]
) -> None:
    for _ in range(ACTION_CARDS_DRAWN):
        draw_action_card(state, player_id)


def _options(
    state: GameState,
    ctx: CardContext,
    player_id: str,
    step: str | None,
    _draft: Draft,
) -> dict[str, Any]:
    if step == "choose_speaker":
        return {"players": [p for p in state.players if p != state.speaker_id]}
    if step == "agenda_order":
        # Odczyt bez mutacji oryginału: zasiew na kopii (talia i tak powstała w kroku 1).
        view = state.clone()
        ensure_agenda_deck(view, ctx.registry)
        return {"cards": _peek(view), "drawn": list(_draft.get(PRIVATE_DRAWN_KEY, []))}
    return {"needs_input": False}


SPEC = CardSpec(
    primary_steps=("choose_speaker", "agenda_order"),
    on_step=_on_step,
    primary=_primary,
    secondary=_secondary,
    secondary_costs_token=True,
    options=_options,
)
