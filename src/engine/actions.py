"""Katalog akcji gracza dla bota (RULES.md 65.1, plan: ``docs/bot/PLAN.md`` B1).

``Action`` = jedna decyzja gracza jako dane (Pydantic, rozróżniane polem ``kind``), a
``apply_action`` stosuje ją przez DOKŁADNIE te funkcje ``core/`` (i tę samą kontrolę aktora
``core/actor``), które wołają routery ``api/``. Test zgodności (``tests/engine``) pilnuje, że
akcja z katalogu i to samo żądanie HTTP dają identyczny stan.

Zakres B1: decyzje, bez których gra z botem by stanęła (setup, wybór i zagranie karty strategii
z krokami primary, secondary, pas / koniec tury, okna, oferty, przypisanie trafień, status,
agenda, ogłoszenia mówcy, limit ręki, okno hold-play). B5 (``actions_tactical``): aktywacja,
ruch, produkcja, walka, Space Cannon, inwazja, eksploracja, pojemność, karty akcji.

Warstwa nie importuje ``api/``. Nielegalna akcja = ``ValueError`` (HTTP 422) albo
``ActorError`` (HTTP 403) z ``core/``.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter

from src.core import actor as actor_rules
from src.core import (
    agenda_phase,
    battle,
    card_hold,
    fleet_pool,
    game_setup,
    hand_limit,
    offers,
    phase_flow,
    production,
    reaction_pause,
    status_phase,
    step_settle,
    strategic_action,
    strategy_phase,
    tactical,
    turn_flow,
)
from src.core.game_state import GameState
from src.engine import actions_tactical as tac
from src.engine.action_base import (
    ActionBase,
    Apply,
    Guard,
)
from src.engine.action_base import EngineContext as EngineContext
from src.engine.action_base import claimed as _claimed
from src.engine.action_base import entitled as _entitled

_Base = ActionBase


# --- Setup startowy (RULES.md 45) ------------------------------------------------------------


class SetupSecret(_Base):
    kind: Literal["setup_secret"] = "setup_secret"
    objective_id: str


class SetupCustodians(_Base):
    kind: Literal["setup_custodians"] = "setup_custodians"


class SetupReveal(_Base):
    kind: Literal["setup_reveal"] = "setup_reveal"


# --- Karty strategii (RULES.md 13, 30) -------------------------------------------------------


class StrategyPick(_Base):
    kind: Literal["strategy_pick"] = "strategy_pick"
    initiative: int
    recipient: str | None = None


class StrategyPlay(_Base):
    kind: Literal["strategy_play"] = "strategy_play"
    initiative: int


class StrategyPrimaryStep(_Base):
    kind: Literal["strategy_primary_step"] = "strategy_primary_step"
    payload: dict[str, Any] = Field(default_factory=dict)


class StrategySecondary(_Base):
    kind: Literal["strategy_secondary"] = "strategy_secondary"
    execute: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


# --- Tura i ogłoszenia mówcy (RULES.md 31) ---------------------------------------------------


class TurnPass(_Base):
    kind: Literal["turn_pass"] = "turn_pass"


class TurnEnd(_Base):
    kind: Literal["turn_end"] = "turn_end"


class TacticalEnd(_Base):
    kind: Literal["tactical_end"] = "tactical_end"


class ProductionSkip(_Base):
    """„Finish production”: koniec/rezygnacja z produkcji z karty (Construction, Warfare TE)."""

    kind: Literal["production_skip"] = "production_skip"


class PhaseStep(_Base):
    kind: Literal["phase_step"] = "phase_step"


class PhaseNext(_Base):
    kind: Literal["phase_next"] = "phase_next"


class RoundNext(_Base):
    kind: Literal["round_next"] = "round_next"


# --- Okna czasowe, oferty, hold-play (RULES.md 29, 54, 56) -----------------------------------


class OfferAccept(_Base):
    kind: Literal["offer_accept"] = "offer_accept"
    offer_id: str
    params: dict[str, Any] = Field(default_factory=dict)


class OfferDecline(_Base):
    kind: Literal["offer_decline"] = "offer_decline"
    offer_id: str


class HeldPass(_Base):
    kind: Literal["held_pass"] = "held_pass"


class HeldRelease(_Base):
    """Zamknięcie okna hold-play po jego stałym czasie (zegar serwera, RULES.md 54.11)."""

    kind: Literal["held_release"] = "held_release"


class ReactionPauseRelease(_Base):
    """Zamknięcie pauzy ochronnej po jej stałym czasie (RULES.md 54.10-54.11)."""

    kind: Literal["reaction_pause_release"] = "reaction_pause_release"


class DiscardExcess(_Base):
    kind: Literal["discard_excess"] = "discard_excess"
    card_id: str


# --- Walka (RULES.md 39) ---------------------------------------------------------------------


class BattleAssign(_Base):
    kind: Literal["battle_assign"] = "battle_assign"
    sustain: dict[str, int] = Field(default_factory=dict)
    destroy: dict[str, int] = Field(default_factory=dict)
    destroy_damaged: dict[str, int] = Field(default_factory=dict)


class FleetPoolResolve(_Base):
    """Okno FLEET_POOL: statki ponad pulę floty wracają do rezerwy (RULES.md 42)."""

    kind: Literal["fleet_pool_resolve"] = "fleet_pool_resolve"
    remove: dict[str, int] = Field(default_factory=dict)


# --- Faza statusu (RULES.md 32) --------------------------------------------------------------


class StatusFinishScoring(_Base):
    kind: Literal["status_finish_scoring"] = "status_finish_scoring"


class StatusRedistribute(_Base):
    kind: Literal["status_redistribute"] = "status_redistribute"
    tactical: int
    fleet: int
    strategic: int


# --- Faza agendy (RULES.md 51) ---------------------------------------------------------------


class AgendaReveal(_Base):
    kind: Literal["agenda_reveal"] = "agenda_reveal"


class AgendaVote(_Base):
    kind: Literal["agenda_vote"] = "agenda_vote"
    outcome: str
    planets: list[str]
    use_predictive: bool = False


class AgendaAbstain(_Base):
    kind: Literal["agenda_abstain"] = "agenda_abstain"


class AgendaDecide(_Base):
    kind: Literal["agenda_decide"] = "agenda_decide"
    outcome: str


class AgendaConfirm(_Base):
    kind: Literal["agenda_confirm"] = "agenda_confirm"


class AgendaDiscard(_Base):
    kind: Literal["agenda_discard"] = "agenda_discard"


class AgendaContinue(_Base):
    kind: Literal["agenda_continue"] = "agenda_continue"


Action = Annotated[
    SetupSecret
    | SetupCustodians
    | SetupReveal
    | StrategyPick
    | StrategyPlay
    | StrategyPrimaryStep
    | StrategySecondary
    | TurnPass
    | TurnEnd
    | TacticalEnd
    | ProductionSkip
    | PhaseStep
    | PhaseNext
    | RoundNext
    | OfferAccept
    | OfferDecline
    | HeldPass
    | HeldRelease
    | ReactionPauseRelease
    | DiscardExcess
    | BattleAssign
    | FleetPoolResolve
    | StatusFinishScoring
    | StatusRedistribute
    | AgendaReveal
    | AgendaVote
    | AgendaAbstain
    | AgendaDecide
    | AgendaConfirm
    | AgendaDiscard
    | AgendaContinue
    | tac.TacticalAction,
    Field(discriminator="kind"),
]
"""Dowolna akcja z katalogu (serializowalna: przechodzi do procesu roboczego i z powrotem)."""

ACTION_ADAPTER: TypeAdapter[Action] = TypeAdapter(Action)


# --- Zastosowanie: te same funkcje core/ i ta sama kontrola aktora co routery ------------------

def _apply_battle_assign(state: GameState, ctx: EngineContext, a: BattleAssign) -> GameState:
    return battle.assign_combat_hits(
        state, ctx.grid, ctx.registry, a.player_id,
        sustain=dict(a.sustain), destroy=dict(a.destroy),
        destroy_damaged=dict(a.destroy_damaged),
    )


_HANDLERS: dict[str, tuple[Guard | None, Apply]] = {
    **tac.HANDLERS,
    "setup_secret": (
        _claimed("Choose secret objective"),
        lambda s, c, a: game_setup.choose_secret(s, a.player_id, a.objective_id),
    ),
    "setup_custodians": (
        _claimed("Place Custodians"),
        lambda s, c, a: game_setup.place_custodians(s, a.player_id),
    ),
    "setup_reveal": (
        _claimed("Reveal objectives"),
        lambda s, c, a: game_setup.reveal_objectives(s, a.player_id),
    ),
    "strategy_pick": (
        _claimed("Pick strategy card"),
        lambda s, c, a: strategy_phase.pick_strategy_card(
            s, c.registry, a.player_id, a.initiative, recipient=a.recipient
        ),
    ),
    "strategy_play": (
        _claimed("Play strategy card"),
        lambda s, c, a: strategic_action.play_strategy_card(
            s, c.registry, a.player_id, a.initiative, grid=c.grid
        ),
    ),
    "strategy_primary_step": (
        _claimed("Primary ability"),
        lambda s, c, a: strategic_action.submit_primary_step(
            s, c.registry, a.player_id, dict(a.payload), grid=c.grid
        ),
    ),
    "strategy_secondary": (
        _claimed("Secondary ability"),
        lambda s, c, a: strategic_action.resolve_secondary(
            s, c.registry, a.player_id, execute=a.execute, payload=dict(a.payload), grid=c.grid
        ),
    ),
    "turn_pass": (
        _entitled(actor_rules.turn_player, "Turn"),
        lambda s, c, a: turn_flow.pass_turn(s, a.player_id),
    ),
    "turn_end": (
        _entitled(actor_rules.turn_player, "Turn"),
        lambda s, c, a: turn_flow.end_turn(s, a.player_id, registry=c.registry),
    ),
    "tactical_end": (
        _entitled(actor_rules.turn_player, "End tactical action"),
        lambda s, c, a: tactical.end_action(s, c.registry),
    ),
    "production_skip": (
        _entitled(actor_rules.production_grantee, "Skip production"),
        lambda s, c, a: strategic_action.after_standalone_production(
            production.skip_grant(s)
        ),
    ),
    "phase_step": (
        _entitled(actor_rules.turn_player, "Turn"),
        lambda s, c, a: turn_flow.advance_active_player(s, a.player_id, mark_passed=True),
    ),
    "phase_next": (
        _entitled(actor_rules.speaker, "Next phase"),
        lambda s, c, a: phase_flow.announce_next_phase(s, c.registry, a.player_id),
    ),
    "round_next": (
        _entitled(actor_rules.speaker, "New round"),
        lambda s, c, a: phase_flow.announce_next_round(s, c.registry),
    ),
    # Oferty, hold-play i limit ręki: router tylko uzgadnia aktora z treścią (merge_claimed),
    # tożsamość decydenta waliduje core.
    "offer_accept": (
        None,
        lambda s, c, a: offers.accept(
            s, c.grid, c.registry, a.player_id, a.offer_id, dict(a.params)
        ),
    ),
    "offer_decline": (
        None,
        lambda s, c, a: offers.decline(s, c.grid, c.registry, a.player_id, a.offer_id),
    ),
    "held_pass": (None, lambda s, c, a: card_hold.pass_hold(s, c.registry, a.player_id)),
    "held_release": (
        None, lambda s, c, a: card_hold.release(s, c.registry, a.player_id, now=c.now)
    ),
    "reaction_pause_release": (None, lambda s, c, a: reaction_pause.release(s, c.now)),
    "discard_excess": (
        None,
        lambda s, c, a: hand_limit.discard_excess(s, a.player_id, a.card_id),
    ),
    "battle_assign": (_claimed("Assign hits"), _apply_battle_assign),
    "fleet_pool_resolve": (
        _claimed("Resolve fleet pool"),
        lambda s, c, a: fleet_pool.resolve_fleet_pool(
            s, c.registry, a.player_id, dict(a.remove)
        ),
    ),
    "status_finish_scoring": (
        _claimed("Finish scoring"),
        lambda s, c, a: status_phase.finish_scoring(s, c.registry, a.player_id),
    ),
    "status_redistribute": (
        _claimed("Redistribute tokens"),
        lambda s, c, a: status_phase.redistribute(
            s, c.registry, a.player_id, a.tactical, a.fleet, a.strategic
        ),
    ),
    "agenda_reveal": (
        _claimed("Reveal agenda"),
        lambda s, c, a: agenda_phase.reveal_agenda(s, c.registry, a.player_id),
    ),
    "agenda_vote": (
        _claimed("Vote"),
        lambda s, c, a: agenda_phase.cast_vote(
            s, c.registry, a.player_id, a.outcome, list(a.planets),
            use_predictive=a.use_predictive,
        ),
    ),
    "agenda_abstain": (
        _claimed("Abstain"),
        lambda s, c, a: agenda_phase.abstain(s, c.registry, a.player_id),
    ),
    "agenda_decide": (
        _claimed("Decide outcome"),
        lambda s, c, a: agenda_phase.decide_tie(s, c.registry, a.player_id, a.outcome),
    ),
    "agenda_confirm": (
        _claimed("Confirm outcome"),
        lambda s, c, a: agenda_phase.confirm_outcome(s, c.registry, a.player_id),
    ),
    "agenda_discard": (
        _claimed("Discard agenda"),
        lambda s, c, a: agenda_phase.discard_unresolvable(s, c.registry, a.player_id),
    ),
    "agenda_continue": (
        _claimed("Continue agenda"),
        lambda s, c, a: agenda_phase.continue_agenda(s, c.registry, a.player_id),
    ),
}

ACTION_KINDS: frozenset[str] = frozenset(_HANDLERS)
"""Wszystkie rodzaje akcji katalogu (strażnik: każdy ma test zgodności z HTTP)."""


def apply_action(state: GameState, ctx: EngineContext, action: Action) -> GameState:
    """Stosuje akcję gracza ``action.player_id`` do PEŁNEGO stanu gry i zwraca nowy stan.

    Aktor = ``action.player_id`` (bot gra jako swój gracz). Stan wejściowy nie jest mutowany
    (funkcje ``core/`` pracują na klonie).

    Raises:
        ActorError: Gracz nie jest uprawniony do tej akcji teraz (HTTP 403).
        ValueError: Akcja łamie reguły (HTTP 422).
    """
    guard, handler = _HANDLERS[action.kind]
    if guard is not None:
        guard(state, action.player_id)
    return handler(state, ctx, action)


def step_label(action: Action) -> str:
    """Etykieta kroku jak w historii serwera (prefiks decyduje o zwolnieniach z limitów)."""
    if action.kind.startswith("setup_"):
        return f"setup:bot:{action.kind}"  # setup jest zwolniony z limitów, jak w routerach
    return f"bot:{action.kind}"


def apply_and_settle(state: GameState, ctx: EngineContext, action: Action) -> GameState:
    """``apply_action`` + rozliczenie po kroku (``core/step_settle``) — dokładnie jak commit.

    To jest pełny skutek ruchu, który zobaczy serwer: koniec gry, limity, pauza reakcji,
    odblokowania liderów, zegar. Symulacje bota używają TEJ funkcji, nie samego ``apply``.
    """
    return step_settle.settle_step(
        apply_action(state, ctx, action), ctx.registry, ctx.now, step_label(action), before=state
    )
