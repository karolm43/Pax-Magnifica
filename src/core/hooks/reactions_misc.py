"""Karty reakcji: strategia, tury, transakcje i odrzucone karty akcji (RULES.md 53.5.e).

Karty (id): ``investments``, ``summit`` (start fazy strategii), ``crisis``, ``puppetsonastring``,
``extremeduress`` (pauza po końcu tury), ``master_plan`` (po akcji), ``blackmarketdealing``
(negocjowana transakcja), ``lieinwait`` (po transakcji sąsiadów), ``reverse_engineer`` (po
odrzuceniu karty akcji z akcją komponentu).

Okna liczone ze stanu (``@window_provider``), wzór: ``reactions_tactical``. Trwałe ślady, których
silnik wcześniej nie miał (``GameState.turn_end_window``, ``last_transaction``,
``last_action_discard``, ``bonus_turn``), są ustawiane przez ``turn_flow`` / ``transaction`` /
``card_draw`` i zerowane przy kolejnej akcji (``action_budget.register_action``).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from src.core import (
    action_budget,
    active_effects,
    card_draw,
    command_tokens,
    economy,
    rules_hooks,
    secret_objectives,
    strategy_phase,
    turn_flow,
)
from src.core.components import ComponentCategory, ComponentRef
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    BonusTurn,
    GameState,
    Phase,
)
from src.core.hooks.action_card_inputs import (
    Input,
    _choice,
    _multi,
    _number,
    _option,
    _player_label,
)
from src.core.hooks.card_targets_economy import neighbor_ids
from src.core.reaction_cards import (
    ANY,
    OTHER,
    OpenWindow,
    card_effect_source,
    declare_reaction,
    window_provider,
)
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_ACTION_STARTED,
    POINT_TRANSACTION_EXTRA_ITEMS,
    POINT_TURN_ACTIONS,
    HookKind,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.timing_spec import TriggerKind

# --------------------------------------------------------------------------- stałe z tekstów kart

_INVESTMENTS_TOTAL = 5  # „Place a total of 5 trade goods from the supply on strategy cards”
_INVESTMENTS_MIN_CARDS = 3  # „You must place these tokens on at least 3 different cards.”
_SUMMIT_TOKENS = 2  # „Gain 2 command tokens.”
_CRISIS_MIN_UNPASSED = 2  # „if there are at least 2 players who have not passed”
_MASTER_PLAN_BONUS = 1  # „Perform an additional action.”
_DURESS_MET = "met"  # Extreme Duress: następną akcją była strategiczna (do końca tury)
_LIE_IN_WAIT_PER_HAND = 1  # „choose and take 1 action card from each”

_KEY = "action_cards:{}"


def _key(card_id: str) -> str:
    return _KEY.format(card_id)


# --------------------------------------------------------------------------------------- okna


@window_provider
def strategy_phase_start(state: GameState) -> list[OpenWindow]:
    """„At the start of the strategy phase”: faza strategii, nikt jeszcze nie wybrał karty.

    "Picked" = a choice made this phase (``strategy_choices``), not "holds a card": a card kept
    through Political Stability does not close the window (C_action_cards/manipulate-investments/1).
    """
    if state.phase is not Phase.STRATEGY or state.setup is not None or not state.players:
        return []
    if any(state.strategy_choices.values()):
        return []
    subject = state.speaker_id or state.active_player_id
    if subject is None or subject not in state.players:
        return []
    return [OpenWindow(GameEvent.PHASE, Moment.START, {"player": subject, "phase": "strategy"})]


@window_provider
def strategy_phase_end(state: GameState) -> list[OpenWindow]:
    """„At the end of the strategy phase”: każdy ma komplet kart, mówca jeszcze nie przeszedł do
    fazy akcji (Gift of Prescience Naalu, RULES.md 62.16)."""
    if state.phase is not Phase.STRATEGY or state.setup is not None or not state.players:
        return []
    try:
        strategy_phase.ensure_strategy_complete(state)
    except ValueError:
        return []
    subject = state.speaker_id or state.active_player_id
    if subject is None or subject not in state.players:
        return []
    return [OpenWindow(GameEvent.PHASE, Moment.END, {"player": subject, "phase": "strategy"})]


@window_provider
def turn_boundary(state: GameState) -> list[OpenWindow]:
    """Pauza po końcu tury: „koniec tury gracza X” i (gdy ktoś jest następny) „początek tury Y”."""
    window = state.turn_end_window
    if window is None or state.phase is not Phase.ACTION or state.bonus_turn is not None:
        return []
    found: list[OpenWindow] = []
    if window.ended_player is not None:  # None = pierwsza tura fazy: nikt nie skończył tury
        found.append(
            OpenWindow(
                GameEvent.TURN,
                Moment.END,
                {"player": window.ended_player, "next_player": window.next_player or ""},
            )
        )
    if window.next_player is not None and window.next_player in state.players:
        found.append(OpenWindow(GameEvent.TURN, Moment.START, {"player": window.next_player}))
    return found


@window_provider
def after_action(state: GameState) -> list[OpenWindow]:
    """„After you perform an action”: aktywny gracz skończył akcję i nic się nie toczy."""
    active = state.active_player_id
    player = state.players.get(active) if active is not None else None
    if (
        active is None
        or player is None
        or state.phase is not Phase.ACTION
        or action_budget.blocked_by_pass(state, active)
        or not player.took_action_this_turn
        or state.active_system is not None
        or state.tactical_step is not None
        or state.pending_strategy is not None
        or state.pending_window is not None
        or state.exploration is not None
        or state.active_combat is not None
        or state.invasion is not None
    ):
        return []
    return [OpenWindow(GameEvent.COMPONENT_ACTION, Moment.AFTER, {"player": active})]


@window_provider
def transactions(state: GameState) -> list[OpenWindow]:
    """„When you are negotiating a transaction” (otwarty stół transakcji pary graczy - negocjacja,
    RULES.md 47.1b) i „after ... resolve” (ślad). Bez stołu nie ma negocjacji, więc nie ma okna
    (wcześniej okno trwało całą turę aktywnego i Black Market Dealings dało się zagrać bez
    żadnej transakcji)."""
    found: list[OpenWindow] = []
    for table in state.transaction_tables:
        if table.opener in state.players and table.partner in state.players:
            found.append(
                OpenWindow(
                    GameEvent.TRANSACTION, Moment.WHEN,
                    {"player": table.opener, "partner": table.partner},
                )
            )
    pair = state.last_transaction
    if len(pair) == 2:
        found.append(
            OpenWindow(
                GameEvent.TRANSACTION, Moment.AFTER, {"player": pair[0], "partner": pair[1]}
            )
        )
    return found


@window_provider
def action_card_discarded(state: GameState) -> list[OpenWindow]:
    """„After a player discards an action card”: ślad ostatniego odrzucenia."""
    trace = state.last_action_discard
    if trace is None:
        return []
    return [
        OpenWindow(
            GameEvent.ACTION_CARD_DISCARDED,
            Moment.AFTER,
            {"player": trace.player, "card": trace.card},
        )
    ]


# ------------------------------------------------------------------------------------ warunki


def _has_readied_strategy_card(state: GameState, player_id: str) -> bool:
    player = state.players.get(player_id)
    if player is None:
        return False
    return bool(set(player.strategy_cards) - set(player.exhausted_strategy_cards))


def _crisis_condition(
    state: GameState, _registry: StaticDataRegistry, _player: str, window: OpenWindow
) -> bool:
    """Co najmniej 2 niespasowanych graczy i ktoś, kto ma zacząć następną turę."""
    unpassed = sum(1 for p in state.players.values() if not p.passed)
    nxt = state.turn_end_window.next_player if state.turn_end_window else None
    return unpassed >= _CRISIS_MIN_UNPASSED and nxt is not None


def _puppets_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    player = state.players.get(player_id)
    return player is not None and player.passed


def _duress_condition(
    state: GameState, _registry: StaticDataRegistry, _player: str, window: OpenWindow
) -> bool:
    """Gracz, któremu zaczyna się tura, ma gotową (nie zagraną) kartę strategii."""
    target = window.subject
    return target is not None and _has_readied_strategy_card(state, target)


def _can_negotiate(
    state: GameState, registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    """Gracz jest stroną negocjacji tego okna (otwarty stół: ``player`` i ``partner``)."""
    return player_id in (window.ctx.get("player"), window.ctx.get("partner"))


def _lie_in_wait_condition(
    state: GameState, registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    """Dwóch sąsiadów gracza (obaj) właśnie rozstrzygnęło transakcję."""
    pair = state.last_transaction
    if len(pair) != 2 or player_id in pair:
        return False
    near = set(neighbor_ids(state, registry, player_id))
    return all(pid in near for pid in pair)


def _reverse_engineer_condition(
    state: GameState, registry: StaticDataRegistry, _player: str, window: OpenWindow
) -> bool:
    """Odrzucona karta ma akcję komponentu i leży jeszcze na stosie odrzuconych."""
    card_id = str(window.ctx.get("card", ""))
    if card_id not in state.decks.action_card_discard:
        return False
    spec = registry.catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, card_id))
    return spec is not None and spec.trigger is TriggerKind.ACTION


declare_reaction("investments", "summit", subject=ANY)
declare_reaction("crisis", subject=ANY, condition=_crisis_condition)
# „if you have passed” - dotyczy dowolnej tury (podmiot okna to gracz kończący turę).
declare_reaction("puppetsonastring", subject=ANY, condition=_puppets_condition)
declare_reaction("extremeduress", subject=OTHER, condition=_duress_condition)
declare_reaction("blackmarketdealing", subject=ANY, condition=_can_negotiate)
# „After 2 of your neighbors resolve a transaction” - gracz z ręki NIE jest podmiotem okna.
declare_reaction("lieinwait", subject=ANY, condition=_lie_in_wait_condition)
declare_reaction("reverse_engineer", subject=OTHER, condition=_reverse_engineer_condition)


# ---------------------------------------------------------------- Manipulate Investments


def _strategy_cards(registry: StaticDataRegistry) -> list[tuple[int, str]]:
    """Karty zestawu: (inicjatywa, nazwa) rosnąco."""
    return sorted(
        (card.initiative, card.name) for card in registry.strategy_card_set()
    )


@register_effect_inputs(_key("investments"))
def investments_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    hint = (
        f"Place exactly {_INVESTMENTS_TOTAL} trade goods in total, on at least "
        f"{_INVESTMENTS_MIN_CARDS} different cards."
    )
    # Auto (⚠️ ZAŁOŻENIE, RULES.md 53.5.e): po 1 TG na 5 kart o najniższej inicjatywie.
    return [
        _number(
            f"tg_{initiative}", f"{initiative}. {name}", 0, _INVESTMENTS_TOTAL, hint,
            auto=1 if index < _INVESTMENTS_TOTAL else 0,
        )
        for index, (initiative, name) in enumerate(_strategy_cards(registry))
    ]


@register_effect(_key("investments"))
def investments_effect(
    state: GameState, registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Manipulate Investments: Place a total of 5 trade goods from the supply on strategy cards of
    your choice. You must place these tokens on at least 3 different cards.

    Parametry: ``tg_<inicjatywa>`` = liczba TG na danej karcie. TG pochodzą z zasobów ogólnych
    (nie z puli gracza). ⚠ ZAŁOŻENIE: „na co najmniej 3 różnych kartach” = co najmniej 3 karty
    dostają po >= 1 TG.
    """
    placed: dict[int, int] = {}
    for initiative, _name in _strategy_cards(registry):
        raw = params.get(f"tg_{initiative}", 0)
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise ValueError(f"Invalid trade goods amount ('tg_{initiative}').")
        if raw:
            placed[initiative] = raw
    if sum(placed.values()) != _INVESTMENTS_TOTAL:
        raise ValueError(f"Place exactly {_INVESTMENTS_TOTAL} trade goods in total.")
    if len(placed) < _INVESTMENTS_MIN_CARDS:
        raise ValueError(
            f"Place the trade goods on at least {_INVESTMENTS_MIN_CARDS} different strategy cards."
        )
    for initiative, amount in placed.items():
        strategy_phase.add_trade_goods_to_card(state, initiative, amount)


# ------------------------------------------------------------------------------- Summit


def _summit_amount(state: GameState, player_id: str) -> int:
    return min(_SUMMIT_TOKENS, command_tokens.reinforcements(state, player_id))


@register_effect_inputs(_key("summit"))
def summit_inputs(state: GameState, _registry: StaticDataRegistry, player_id: str) -> list[Input]:
    amount = _summit_amount(state, player_id)
    names = {"tactical": "Tactic", "fleet": "Fleet", "strategic": "Strategy"}
    options = [
        _option(pool, f"{names[pool]} pool", f"{pool}#{index}")
        for pool in command_tokens.POOLS
        for index in range(amount)
    ]
    hint = "Choose the pool for each token (limited by your reinforcements)."
    # Brak żetonów w rezerwie = wymagany wybór bez opcji (karta bez skutku nie jest zagrywalna).
    need = max(amount, 1)
    return [_multi("pools", "Pools for the command tokens", options, need, need, hint)]


@register_effect(_key("summit"))
def summit_effect(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Summit: Gain 2 command tokens.

    Gracz wybiera pulę dla każdego żetonu (R_command_tokens); bierze je z rezerwy, a przy braku
    żetonów w rezerwie dostaje tyle, ile ma (R_command_tokens: nie można zyskać żetonu bez rezerwy).
    """
    amount = _summit_amount(state, player_id)
    if amount < 1:
        raise ValueError("You have no command tokens in your reinforcements.")
    pools = params.get("pools")
    if not isinstance(pools, list) or len(pools) != amount:
        raise ValueError(f"Choose a pool for each of the {amount} command tokens ('pools').")
    if any(pool not in command_tokens.POOLS for pool in pools):
        raise ValueError("Unknown command token pool.")
    command_tokens.gain_from_reinforcements(state, player_id, dict(Counter(pools)))


# ------------------------------------------------------------------------------- Crisis


@register_effect(_key("crisis"))
def crisis_effect(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """Crisis: Skip the next player's turn.

    Ruling (C_action_cards): pomijana jest tura następnego NIESPASOWANEGO gracza.
    """
    turn_flow.skip_next_turn(state)


# ---------------------------------------------------------------------- Puppets on a String


@register_effect(_key("puppetsonastring"))
def puppets_effect(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Puppets on a String: Perform 1 action.

    Dodatkowa akcja spasowanego gracza poza kolejką (``GameState.bonus_turn``): gracz zostaje
    aktywny, wykonuje JEDNĄ akcję i ``end_turn`` oddaje turę temu, kto miał ją zacząć. The
    player stays passed (``passed=True``) during the action and does not pass at its end
    (puppets-on-a-string/7; ``action_budget.blocked_by_pass`` lets them act). Fleet Logistics nie
    daje drugiej akcji (``fleet_logistics_actions``); akcja strategiczna niedostępna (karty
    gracza są już zagrane, bo spasował).
    """
    window = state.turn_end_window
    player = state.players[player_id]
    if window is None or not player.passed or state.bonus_turn is not None:
        raise ValueError("You can only perform the extra action right after a turn, if you passed.")
    state.bonus_turn = BonusTurn(
        player=player_id,
        resume_player=window.next_player,
        resume_window=window.model_copy(),
    )
    action_budget.reset_turn(state, player_id)  # zeruje też ślad pauzy (zapisany w bonus_turn)
    player.transacted_with = []
    state.active_player_id = player_id


# --------------------------------------------------------------------------- Extreme Duress


@register_effect(_key("extremeduress"))
def duress_effect(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Extreme Duress: If that player's next action is not a strategic action, they discard all of
    their action cards, give you all of their trade goods, and show you all of their secret
    objectives.

    Efekt trwały na CELU do jego następnej akcji (``Duration.ROUND``: przetrwa turę pominiętą
    przez Crisis albo urwaną bez akcji); rozstrzygany przez hook ``POINT_ACTION_STARTED``.
    Pokazanie tajnych celów = zapis w prywatnym polu zagrywającego
    (``private.revealed_secrets``).
    """
    window = state.turn_end_window
    target = window.next_player if window is not None else None
    if target is None or not _has_readied_strategy_card(state, target):
        raise ValueError("The next player has no readied strategy card.")
    active_effects.add_effect(
        state, _key("extremeduress"), Duration.ROUND, owner=target, data={"holder": player_id}
    )


@register(POINT_ACTION_STARTED, card_effect_source("extremeduress"), HookKind.PERSISTENT)
def _duress_resolve(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Pierwsza akcja celu: strategiczna = bez kary; inna = karty, TG i tajne cele dla gracza."""
    key = _key("extremeduress")
    mine = [
        e for e in state.active_effects
        if e.key == key and e.owner == player_id and not e.data.get(_DURESS_MET)
    ]
    if not mine:
        return
    if ctx.get("strategic"):
        # Warunek spełniony, ale Coup d'Etat może jeszcze cofnąć tę akcję: efekt czeka do końca
        # tury (``restore_duress``).
        for effect in mine:
            effect.data[_DURESS_MET] = True
            effect.scope = Duration.TURN.value
        return
    for effect in mine:
        active_effects.remove_effect(state, effect.id)
    # Grana właśnie karta akcji (akcja komponentu) nie jest już „w ręce” - zostaje do zagrania.
    played = str(ctx.get("component") or "")
    target = state.players[player_id]
    hand = list(target.private.action_cards)
    to_discard = list(hand)
    if played and played in to_discard:
        to_discard.remove(played)
    if to_discard:
        card_draw.discard_specific_action_cards(state, player_id, to_discard)
    for effect in mine:
        holder = str(effect.data.get("holder", ""))
        if holder not in state.players or holder == player_id:
            continue
        gold = target.trade_goods
        if gold:
            economy.give_to_player(state, player_id, holder, trade_goods=gold)
        secret_objectives.reveal_hand(state, holder, player_id)


def restore_duress(state: GameState, player_id: str) -> None:
    """Akcja strategiczna celu się nie odbyła (Coup d'Etat): Extreme Duress nadal czeka na jego
    następną akcję (C_action_cards). Mutuje ``state``."""
    for effect in state.active_effects:
        if effect.key == _key("extremeduress") and effect.owner == player_id:
            if effect.data.pop(_DURESS_MET, None):
                effect.scope = Duration.ROUND.value


# ------------------------------------------------------------------------------ Master Plan


@register_effect(_key("master_plan"))
def master_plan_effect(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Master Plan: Perform an additional action.

    +1 do limitu akcji w tej turze (``action_budget``, punkt ``turn.actions``) do końca tury.
    Ruling: nie służy do spasowania w turze, w której gracz już wykonał akcję (to nadal
    wymaga zwykłej ścieżki: pas jest alternatywą dla akcji).
    """
    player = state.players[player_id]
    if not player.took_action_this_turn or action_budget.blocked_by_pass(state, player_id):
        raise ValueError("Master Plan can only be played after you perform an action.")
    active_effects.add_effect(state, _key("master_plan"), Duration.TURN, owner=player_id)


@register(POINT_TURN_ACTIONS, card_effect_source("master_plan"), HookKind.MODIFY)
def _master_plan_bonus(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    return _MASTER_PLAN_BONUS


# ------------------------------------------------------------------- Black Market Dealings


@register_effect(_key("blackmarketdealing"))
def black_market_effect(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Black Market Dealings: You and the other player may include relics, action cards, and
    unscored secret objectives as part of the transaction. This card cannot be canceled.

    Efekt trwały do końca tury albo do rozstrzygnięcia transakcji (hook poniżej). ⚠ ZAŁOŻENIE:
    silnik nie ma etapu „negocjacji” - karta działa na kolejną transakcję w tej turze
    (``TransactionSide.relics/action_cards/secret_objectives``). „Nie może być anulowana” czeka
    na model cofania (osobny etap).
    """
    active_effects.add_effect(state, _key("blackmarketdealing"), Duration.TURN, owner=player_id)


@register(
    POINT_TRANSACTION_EXTRA_ITEMS, card_effect_source("blackmarketdealing"), HookKind.PERMIT
)
def _black_market_permit(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return True


@rules_hooks.on_event(
    GameEvent.TRANSACTION, Moment.AFTER, card_effect_source("blackmarketdealing")
)
def _black_market_consumed(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Karta dotyczy jednej transakcji: po jej rozstrzygnięciu efekt znika."""
    active_effects.remove_by_key(state, _key("blackmarketdealing"), owner=player_id)


# ---------------------------------------------------------------------------- Lie in Wait


def _lie_in_wait_pair(state: GameState) -> list[str]:
    return list(state.last_transaction)


@register_effect_inputs(_key("lieinwait"))
def lie_in_wait_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    """Podgląd rąk obu stron transakcji (widoczny tylko dla grającego) + wybór po 1 karcie."""
    inputs: list[Input] = []
    for other in _lie_in_wait_pair(state):
        hand = state.players[other].private.action_cards
        if not hand:
            continue
        options = []
        for card_id in dict.fromkeys(hand):
            card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
            options.append(_option(card_id, getattr(card, "name", card_id)))
        inputs.append(
            _choice(
                f"card_{other}",
                f"Action card to take from {_player_label(state, registry, other)}",
                options,
                hint="You can see this player's whole hand; take 1 card.",
            )
        )
    if not inputs:
        # Obie ręce puste: nie ma czego wziąć (wymagany wybór bez opcji blokuje kartę).
        inputs.append(_choice("card", "Action card to take", []))
    return inputs


@register_effect(_key("lieinwait"))
def lie_in_wait_effect(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Lie in Wait: Look at each of those players' hands of action cards, then choose and take 1
    action card from each.

    Parametry: ``card_<id gracza>`` dla każdej niepustej ręki. Gracz z pustą ręką jest pomijany.
    """
    pair = _lie_in_wait_pair(state)
    if len(pair) != 2:
        raise ValueError("There is no resolved transaction between two of your neighbors.")
    wanted: list[tuple[str, str]] = []
    for other in pair:
        if not state.players[other].private.action_cards:
            continue
        card = params.get(f"card_{other}")
        if not isinstance(card, str) or card not in state.players[other].private.action_cards:
            raise ValueError(f"Choose 1 action card from {other}'s hand ('card_{other}').")
        wanted.append((other, card))
    if not wanted:
        raise ValueError("Neither player has any action cards.")
    for other, card in wanted:
        for _ in range(_LIE_IN_WAIT_PER_HAND):
            card_draw.transfer_action_card(state, other, player_id, card)


# ------------------------------------------------------------------------ Reverse Engineer


@register_effect(_key("reverse_engineer"))
def reverse_engineer_effect(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Reverse Engineer: Take that action card from the discard pile.

    Karta pochodzi z okna (``__window``) - ostatnio odrzucona karta akcji innego gracza.
    """
    window = params.get("__window")
    ctx = window.get("ctx", {}) if isinstance(window, Mapping) else {}
    card_id = str(ctx.get("card", ""))
    if not card_id:
        raise ValueError("There is no discarded action card to take.")
    card_draw.take_from_discard(state, player_id, card_id)
