"""Legalne ruchy gracza w bieżącej chwili (RULES.md 65.4; plan ``docs/bot/PLAN.md`` B1).

``legal_actions(obs, ctx)`` zwraca kandydatów dla gracza z obserwacji (nigdy z pełnego stanu),
uporządkowanych tak, że PIERWSZY jest bezpiecznym ruchem domyślnym: pas w oknie, odmowa „may”,
pominięcie secondary, pas w turze, wstrzymanie się od głosu, minimalny wybór w kroku primary.
Pusta lista = gracz nie ma teraz nic do zrobienia (czeka na innych).

Zakres B1 (bez własnej akcji taktycznej): setup, faza strategii, zagranie karty strategii z
krokami primary wszystkich kart, secondary, pas / koniec tury, okna czasowe, oferty, pokrycie
trafień, faza statusu, faza agendy, ogłoszenia mówcy, limit ręki, okno hold-play. Inwazja i
eksploracja prowadzone przez bota — B5.

Generator nie zna reguł: korzysta z enumeratorów ``core/`` (``available_initiatives``,
``next_strategy_picker``, ``side_units``, ``current_voter``…) i z monitów obserwacji. Ostateczną
legalność i tak sprawdza ``apply_action`` (Sędzia).
"""

from __future__ import annotations

from typing import Any

from src.core import (
    agenda_phase,
    battle,
    card_hold,
    hand_limit,
    reaction_pause,
    strategy_phase,
    turn_flow,
)
from src.core.game_state import (
    AgendaStep,
    GameState,
    Phase,
    SetupStage,
    StatusStep,
    WindowType,
)
from src.engine import actions as act
from src.engine.actions import Action, EngineContext
from src.engine.observation import Observation


def legal_actions(obs: Observation, ctx: EngineContext) -> list[Action]:
    """Kandydaci dla ``obs.player_id``; pierwszy = bezpieczny ruch domyślny."""
    s = obs.view
    pid = obs.player_id
    if pid not in s.players:
        return []
    if s.setup is not None:
        return _setup(s, pid)
    # Okna o stałej długości (RULES.md 54.11): po czasie każdy może je zamknąć; przed - pas
    # (boty i tak pasuje silnik przy otwarciu), poza tym czekamy.
    if s.held_play is not None:
        if card_hold.expired(s.held_play, obs.now):
            return [act.HeldRelease(player_id=pid)]
        return [act.HeldPass(player_id=pid)] if card_hold.can_respond(s.held_play, pid) else []
    if s.reaction_pause is not None:
        if reaction_pause.expired(s.reaction_pause, obs.now):
            return [act.ReactionPauseRelease(player_id=pid)]
        return []
    if hand_limit.action_card_excess(s, pid) > 0:
        hand = s.players[pid].private.action_cards
        return [act.DiscardExcess(player_id=pid, card_id=card) for card in hand]
    window = s.pending_window
    if window is not None:
        if window.current_responder != pid:
            return []
        if window.window_type is WindowType.REACTION:
            # Okno REACTION niesie oferty: przesuwa się po przyjęciu/odmowie (core/triggers).
            return _offers(obs, pid)
        return _window(obs, ctx, pid)
    if obs.offers:
        return _offers(obs, pid)
    if s.pending_offers:
        return []  # czekamy na cudze decyzje
    combat = s.active_combat
    if combat is not None:
        if combat.pending_hits.get(pid, 0) > 0:
            return _assign_hits(s, ctx, pid)
        return []  # walkę prowadzi atakujący (B5)
    if s.invasion is not None or s.exploration is not None:
        return []  # B5
    pending = s.pending_strategy
    if pending is not None:
        return _primary_step(obs, ctx, pid) if pending.owner_id == pid else []
    if s.phase is Phase.STRATEGY:
        return _strategy_phase(s, ctx, pid)
    if s.phase is Phase.ACTION:
        return _action_phase(s, pid)
    if s.phase is Phase.STATUS:
        return _status_phase(s, pid)
    if s.phase is Phase.AGENDA:
        return _agenda_phase(s, pid)
    return []


# --- Setup ------------------------------------------------------------------------------------


def _setup(s: GameState, pid: str) -> list[Action]:
    setup = s.setup
    assert setup is not None
    if setup.stage is SetupStage.SECRETS:
        if pid in setup.secrets_chosen:
            return []
        candidates = s.players[pid].private.secret_candidates
        return [act.SetupSecret(player_id=pid, objective_id=c) for c in candidates]
    if pid != s.speaker_id:
        return []
    if setup.stage is SetupStage.CUSTODIANS:
        return [act.SetupCustodians(player_id=pid)]
    return [act.SetupReveal(player_id=pid)]


# --- Okna, oferty, walka ----------------------------------------------------------------------


def _window(obs: Observation, ctx: EngineContext, pid: str) -> list[Action]:
    window = obs.view.pending_window
    assert window is not None
    if window.window_type is WindowType.STRATEGY_SECONDARY:
        # Pas pierwszy; gracz „free” (Trade) nie może spasować - wtedy wykonanie bez wyborów.
        return [
            act.StrategySecondary(player_id=pid, execute=False),
            act.StrategySecondary(player_id=pid, execute=True),
        ]
    if window.window_type is WindowType.COMBAT_ASSIGN_HITS:
        return _assign_hits(obs.view, ctx, pid)
    # SPACE_CANNON / COMBAT_RETREAT / CAPACITY / FLEET_POOL: decyzje mają własne funkcje w core,
    # akcje bota dla nich dochodzą w B5 (ruch i walka). Ogólnej odpowiedzi w oknie nie ma.
    return []


def _offers(obs: Observation, pid: str) -> list[Action]:
    result: list[Action] = []
    for offer in obs.offers:
        accept = act.OfferAccept(
            player_id=pid, offer_id=offer["id"], params=_minimal_params(offer["inputs"])
        )
        if offer.get("mandatory"):
            result.append(accept)
        else:
            result.extend([act.OfferDecline(player_id=pid, offer_id=offer["id"]), accept])
    return result


def _minimal_params(inputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Najprostsza poprawna odpowiedź formularza (``core/offer_inputs``): pierwsze opcje."""
    params: dict[str, Any] = {}
    for spec in inputs:
        kind = spec.get("kind")
        key = str(spec.get("key", ""))
        options = [o["value"] for o in spec.get("options", [])]
        if kind == "choice" and options:
            params[key] = options[0]
        elif kind == "multi":
            params[key] = options[: int(spec.get("min", 0) or 0)]
        elif kind == "number":
            params[key] = spec.get("min", 0)
    return params


def _assign_hits(s: GameState, ctx: EngineContext, pid: str) -> list[Action]:
    """Pokrycie trafień: najpierw Sustain Damage, potem najsłabsze jednostki (⚠️ ZAŁOŻENIE)."""
    units = battle.side_units(s, ctx.grid, ctx.registry, pid)
    required = battle.required_hits(s, ctx.grid, ctx.registry, pid)
    cancels = battle.sustain_cancels(s, pid)
    candidates: list[Action] = []
    for use_sustain in (True, False):
        left = required
        sustain: dict[str, int] = {}
        destroy: dict[str, int] = {}
        destroy_damaged: dict[str, int] = {}
        if use_sustain:
            for unit in units:
                if left <= 0:
                    break
                if unit.sustain and unit.sustainable > 0:
                    uses = min(unit.sustainable, -(-left // cancels))
                    sustain[unit.base_type] = uses
                    left -= uses * cancels
        # Najgorszy próg trafienia (wyższa liczba) ginie pierwszy.
        for unit in sorted(units, key=lambda u: -u.hits_on):
            if left <= 0:
                break
            damaged = unit.damaged + sustain.get(unit.base_type, 0)
            healthy = unit.count - damaged
            take = min(healthy, left)
            if take:
                destroy[unit.base_type] = take
                left -= take
            take = min(damaged, left)
            if take:
                destroy_damaged[unit.base_type] = take
                left -= take
        candidates.append(
            act.BattleAssign(
                player_id=pid, sustain=sustain, destroy=destroy, destroy_damaged=destroy_damaged
            )
        )
    return candidates


# --- Karta strategii: kroki primary (minimalny wybór) -----------------------------------------


def _primary_step(obs: Observation, ctx: EngineContext, pid: str) -> list[Action]:
    s = obs.view
    pending = s.pending_strategy
    assert pending is not None
    if pending.step == "tactical_action":
        # Warfare: akcja taktyczna w trakcie primary - bot jej nie prowadzi (B5), kończy ją.
        return [act.TacticalEnd(player_id=pid)]
    if pending.step == "production":
        return []  # Construction z produkcją - bot wybiera strukturę, więc tu nie trafia
    options = (obs.strategy_prompt or {}).get("options", {})
    payloads = _step_payloads(s, pid, pending.step, options)
    return [act.StrategyPrimaryStep(player_id=pid, payload=p) for p in payloads]


def _step_payloads(
    s: GameState, pid: str, step: str, options: dict[str, Any]
) -> list[dict[str, Any]]:
    """Minimalne odpowiedzi kroków kart (formaty z ``core/strategy_cards/*._on_step``)."""
    player = s.players[pid]
    if step == "spend_influence":  # Leadership
        return [{"planets": [], "trade_goods": 0}]
    if step == "distribute":
        return [{"tactical": int(options.get("gain", 0)), "fleet": 0, "strategic": 0}]
    if step == "choose_system":  # Diplomacy
        systems = list(options.get("systems", []))
        return [{"system": systems[0] if systems else None}]
    if step == "ready_planets":
        return [{"planets": []}]
    if step == "choose_speaker":  # Politics
        return [{"player": p} for p in options.get("players", [])]
    if step == "agenda_order":
        return [{"top": list(options.get("cards", [])), "bottom": []}]
    if step == "choose_free_players":  # Trade
        return [{"players": []}]
    if step == "choose_option":  # Construction: struktura (produkcja to akcja taktyczna, B5)
        return [{"option": "structure"}, {"option": "production"}]
    if step in ("place_structure", "place_structure_2"):
        placeable: dict[str, list[str]] = options.get("placeable", {})
        result = [
            {"planet": planet, "structure": structure}
            for planet, structures in placeable.items()
            for structure in structures
        ]
        return result or [{"planet": None}]
    if step in ("redistribute_before", "redistribute_after"):  # Warfare: bez zmian
        return [{}]
    if step == "activate_system":
        home = player.home_position
        systems = list(options.get("systems", []))
        ordered = ([home] if home in systems else []) + [p for p in systems if p != home]
        return [{"system": p} for p in ordered[:1]]
    if step in ("research", "research_paid"):  # Technology: „can research” - rezygnacja
        return [{"tech": None}]
    if step == "score_and_draw":  # Imperial
        payload: dict[str, Any] = {"objective": None}
        if options.get("over_limit") and not options.get("mecatol"):
            payload["return"] = "drawn"
        return [payload]
    return []


# --- Fazy ------------------------------------------------------------------------------------


def _strategy_phase(s: GameState, ctx: EngineContext, pid: str) -> list[Action]:
    if strategy_phase.next_strategy_picker(s) == pid:
        taken = strategy_phase.picked_initiatives(s) | strategy_phase.forbidden_picks(s, pid)
        free = [i for i in strategy_phase.available_initiatives(ctx.registry) if i not in taken]
        recipient = None
        if strategy_phase.gives_chosen_cards(s):
            recipients = strategy_phase.card_recipients(s, pid)
            recipient = recipients[0] if recipients else None
        return [act.StrategyPick(player_id=pid, initiative=i, recipient=recipient) for i in free]
    if pid == s.speaker_id and turn_flow.can_advance_phase(s):
        return [act.PhaseNext(player_id=pid)]
    return []


def _action_phase(s: GameState, pid: str) -> list[Action]:
    if pid == s.speaker_id and turn_flow.can_advance_phase(s):
        return [act.PhaseNext(player_id=pid)]
    if s.active_player_id != pid:
        return []
    player = s.players[pid]
    if s.tactical_step is not None:
        return [act.TacticalEnd(player_id=pid)]
    if player.passed or player.took_action_this_turn:
        return [act.TurnEnd(player_id=pid)]
    unplayed = [i for i in player.strategy_cards if i not in player.exhausted_strategy_cards]
    if unplayed:
        return [act.StrategyPlay(player_id=pid, initiative=i) for i in unplayed]
    return [act.TurnPass(player_id=pid)]


def _status_phase(s: GameState, pid: str) -> list[Action]:
    status = s.status
    if status is None:  # faza statusu bez kroków (stan z God-Mode)
        if pid == s.speaker_id and turn_flow.can_advance_phase(s):
            return [act.PhaseNext(player_id=pid)]
        return [act.PhaseStep(player_id=pid)] if s.active_player_id == pid else []
    if status.step is StatusStep.SCORE_OBJECTIVES:
        if s.active_player_id == pid and pid not in status.done:
            return [act.StatusFinishScoring(player_id=pid)]
        return []
    if status.step is StatusStep.REDISTRIBUTE:
        if pid in status.done:
            return []
        player = s.players[pid]
        gained = status.unassigned_cc.get(pid, 0)
        return [
            act.StatusRedistribute(
                player_id=pid,
                tactical=player.tactical_cc + gained,
                fleet=player.fleet_cc,
                strategic=player.strategic_cc,
            )
        ]
    if pid == s.speaker_id and turn_flow.can_advance_phase(s):
        return [act.PhaseNext(player_id=pid)]
    return []


def _agenda_phase(s: GameState, pid: str) -> list[Action]:
    agenda = s.agenda
    speaker = pid == s.speaker_id
    if agenda is None:  # agenda bez kroków (God-Mode): UI ogłasza nową rundę
        return [act.RoundNext(player_id=pid)] if speaker else []
    step = agenda.step
    if step is AgendaStep.VOTE:
        if speaker and agenda.unresolvable:
            return [act.AgendaDiscard(player_id=pid)]
        return [act.AgendaAbstain(player_id=pid)] if agenda_phase.current_voter(s) == pid else []
    if not speaker:
        return []
    if step is AgendaStep.REVEAL:
        return [act.AgendaReveal(player_id=pid), act.AgendaDiscard(player_id=pid)]
    if step is AgendaStep.TIEBREAK:
        outcomes = agenda.tied or agenda.outcomes
        return [act.AgendaDecide(player_id=pid, outcome=o) for o in outcomes]
    if step is AgendaStep.COUNTED:
        return [act.AgendaConfirm(player_id=pid)]
    if step is AgendaStep.RESOLVED:
        return [act.AgendaContinue(player_id=pid)]
    if turn_flow.can_advance_phase(s):
        return [act.PhaseNext(player_id=pid)]
    return []
