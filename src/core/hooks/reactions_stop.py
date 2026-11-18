"""Karty reakcji z cofnięciem kroku (hold-rewind).

Public Disgrace, Coup d'Etat, Political Stability, Crash Landing.

Wzorzec jak ``reactions_tactical``, ale okna są WYLICZANE ze stanu MIGAWKI sprzed kroku (``core/
hold_rewind.py`` ocenia je na stanie z przeszłości). Każdą kartę da się też zagrać zwykłym
przeciągnięciem, gdy jej okno jest otwarte TERAZ (poza Public Disgrace - patrz niżej).

* **Public Disgrace** (``disgrace``) - „When another player chooses a strategy card during the
  strategy phase": okno = wybierający jeszcze nie wybrał. Efekt zakazuje mu karty, którą wybrał w
  cofniętym kroku (wiedza z "hindsight": ``register_hindsight``), więc w zwykłej ścieżce (bez
  przyszłości) karta NIE jest oferowana. ``strategy_phase.pick_strategy_card`` egzekwuje zakaz.
* **Coup d'Etat** (``coup``) - „When another player would perform a strategic action": okno =
  inny gracz OGŁOSIŁ akcję strategiczną (zagrał kartę strategii), a primary jeszcze się nie
  rozstrzyga (pierwszy krok, pusty szkic). Efekt anuluje primary, odświeża kartę strategii i kończy
  jego turę (``turn_flow.end_turn(forced=True)``). Po pierwszym wyborze gracza - tylko przez HOLD.
* **Political Stability** (``stability``) - „When you would return your strategy card(s) during
  the status phase": okno = status, krok 8 (przed zwrotem). Efekt trwały do końca rundy; egzekwuje
  go ``strategy_phase.reset_strategy_cards``.
* **Crash Landing** (``crashlanding``) - „When your last ship in the active system is destroyed":
  okno = walka kosmiczna, krok przypisania strat, trafienia zniszczą wszystkie Twoje statki.
  Efekt stawia 1 siłę naziemną z przestrzeni na planetę systemu (nie Mecatol Rex).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    action_budget,
    active_effects,
    battle,
    board_graph,
    exhaust,
    fleet_pool,
    reaction_cards,
    rules_hooks,
    strategic_action,
    strategy_phase,
    turn_flow,
    unit_ops,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import CombatStep, GameState, Phase, StatusStep, SystemState
from src.core.hex_grid import HexGrid
from src.core.hooks import card_labels
from src.core.hooks.action_card_inputs import _choice, _option, _system_label
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.reaction_cards import (
    OpenWindow,
    declare_reaction,
    declare_rewindable,
    register_hindsight,
    window_provider,
)
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect, register_effect_inputs
from src.core.unit_catalog import is_space_unit

declare_rewindable("disgrace", "coup", "stability", "crashlanding")

_MECATOL_NAME = "mecatol rex"


def _window_ctx(params: Mapping[str, Any]) -> Mapping[str, Any]:
    window = params.get(reaction_cards.WINDOW_KEY)
    ctx = window.get("ctx") if isinstance(window, Mapping) else None
    if not isinstance(ctx, Mapping):
        raise ValueError("There is no open window for this card right now.")
    return ctx


def _adopt(dst: GameState, src: GameState) -> None:
    """Przenosi zawartość ``src`` do ``dst`` w miejscu (efekt zwrócony jako nowy stan)."""
    dst.__dict__.update(src.__dict__)


# ------------------------------------------------------------------ Public Disgrace


@window_provider
def strategy_pick_window(state: GameState) -> list[OpenWindow]:
    """Okno „gracz wybiera kartę strategii": faza strategii, wyznaczony gracz jeszcze nie wybrał."""
    if state.phase is not Phase.STRATEGY or state.setup is not None or state.winner_id:
        return []
    picker = strategy_phase.next_strategy_picker(state)
    if picker is None:
        return []
    return [OpenWindow(GameEvent.STRATEGY_CARD_CHOSEN, Moment.WHEN, {"player": picker})]


def _disgrace_hindsight(
    state: GameState, future: GameState, window: OpenWindow
) -> dict[str, Any]:
    """Którą kartę strategii wybrał wybierający w kroku tuż PO tym oknie (``chosen``).

    Karta mogła trafić do INNEGO gracza (Checks and Balances: wybierający oddaje wybraną kartę),
    więc liczy się każda karta, która w tym kroku przestała być wolna (C_agendas).
    """
    picker = window.subject
    if picker not in state.players or picker not in future.players:
        return {}
    taken = strategy_phase.picked_initiatives(state)
    new = sorted(i for i in strategy_phase.picked_initiatives(future) if i not in taken)
    return {"chosen": new[0]} if len(new) == 1 else {}


register_hindsight("disgrace", _disgrace_hindsight)


def _cond_disgrace(
    state: GameState, registry: StaticDataRegistry, _player: str, window: OpenWindow
) -> bool:
    """Znany jest cofany wybór, a wybierający ma inną dostępną kartę (zakaz „if able")."""
    chosen = window.ctx.get("chosen")
    if chosen is None:
        return False
    taken = strategy_phase.picked_initiatives(state)
    return any(
        i not in taken and i != chosen for i in strategy_phase.available_initiatives(registry)
    )


declare_reaction("disgrace", condition=_cond_disgrace)


@register_effect("action_cards:disgrace")
def public_disgrace(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Public Disgrace: That player must choose a different strategy card, if able.

    ⚠ ZAŁOŻENIE: „cofnięty wybór" to karta, którą gracz wziął w kroku tuż po oknie; zakaz trwa do
    jego następnego wyboru albo końca fazy strategii (druga karta z rundy wyboru jest wolna).
    """
    ctx = _window_ctx(params)
    picker, chosen = ctx.get("player"), ctx.get("chosen")
    if not isinstance(picker, str) or chosen is None:
        raise ValueError("Public Disgrace needs a strategy card choice to undo.")
    active_effects.add_effect(
        state, strategy_phase.DISGRACE_KEY, Duration.PHASE, owner=picker,
        data={"forbidden": [int(chosen)]},
    )


# ------------------------------------------------------------------ Coup d'Etat


def declared_strategic_action(state: GameState) -> str | None:
    """Gracz, który OGŁOSIŁ akcję strategiczną, a jej primary jeszcze się nie rozstrzyga.

    ``play_strategy_card`` wyczerpuje kartę i ustawia ``pending_strategy`` na pierwszym kroku
    (wybory to szkic, efekt stosuje się na końcu). Dopóki gracz nie złożył pierwszego wyboru,
    akcja strategiczna „would be performed” (Coup d'Etat). Overrule (``no_secondary``) i primary
    bohatera Winnu (``secondary_players``) to nie akcje strategiczne gracza z jego karty.
    """
    pending = state.pending_strategy
    if pending is None or state.phase is not Phase.ACTION or state.winner_id:
        return None
    owner = state.players.get(pending.owner_id)
    if (
        owner is None
        or state.active_player_id != pending.owner_id
        or pending.no_secondary
        or pending.secondary_players is not None
        or pending.initiative not in owner.strategy_cards
        or pending.initiative not in owner.exhausted_strategy_cards
        or pending.draft
        or pending.step != strategic_action.first_primary_step(pending.initiative)
    ):
        return None
    return pending.owner_id


@window_provider
def strategic_action_declared(state: GameState) -> list[OpenWindow]:
    """Okno „gracz wykona akcję strategiczną”: karta strategii zagrana, primary nierozpoczęte.

    Zgłoszenie użytkownika 2026-11-15: wcześniej okno trwało od początku cudzej tury (gracz z wolną
    kartą strategii), więc Coup d'Etat grano „na zapas”, choć gracz wcale nie musiał wykonać akcji
    strategicznej. Teraz okno istnieje dopiero po jej ogłoszeniu (RULES.md 53.7).
    """
    owner = declared_strategic_action(state)
    if owner is None:
        return []
    initiative = state.pending_strategy.initiative if state.pending_strategy else 0
    return [
        OpenWindow(
            GameEvent.STRATEGIC_ACTION, Moment.WHEN,
            {"player": owner, "initiative": initiative, "declared": True},
        )
    ]


def _cond_coup(
    state: GameState, _registry: StaticDataRegistry, _player: str, window: OpenWindow
) -> bool:
    """Tylko okno ogłoszonej akcji strategicznej (nie np. okno Acquiescence w trakcie secondary)."""
    return bool(window.ctx.get("declared")) and declared_strategic_action(state) == window.subject


declare_reaction("coup", condition=_cond_coup)


@register_effect("action_cards:coup")
def coup_detat(
    state: GameState, registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Coup d'Etat: End that player's turn; the strategic action is not resolved and the strategy
    card is not exhausted.

    Primary nie rozstrzyga się (``pending_strategy`` znika), karta strategii wraca do gotowych,
    zużyta akcja tury jest oddana, a tura się kończy (zdolności „at the end of your turn” działają -
    ruling C_action_cards).
    """
    target = _window_ctx(params).get("player")
    if not isinstance(target, str) or declared_strategic_action(state) != target:
        raise ValueError("That player is no longer about to perform a strategic action.")
    pending = state.pending_strategy
    assert pending is not None  # zagwarantowane przez declared_strategic_action
    state.pending_strategy = None
    exhaust.ready_strategy_card(state, target, pending.initiative)
    action_budget.unregister_action(state, target)
    _adopt(state, turn_flow.end_turn(state, target, registry=registry, forced=True))


# ------------------------------------------------------------------ Political Stability


@window_provider
def before_strategy_return(state: GameState) -> list[OpenWindow]:
    """Okno „zwrot kart strategii": status, krok 8 (wszystko przed zwrotem gotowe)."""
    status = state.status
    if state.phase is not Phase.STATUS or status is None or state.winner_id:
        return []
    if status.step is not StatusStep.COMPLETE:
        return []
    return [
        OpenWindow(GameEvent.STRATEGY_CARDS_RETURNED, Moment.WHEN, {"player": pid})
        for pid, player in state.players.items()
        if player.strategy_cards
    ]


def _cond_stability(
    state: GameState, _registry: StaticDataRegistry, player: str, _window: OpenWindow
) -> bool:
    return not strategy_phase.retains_strategy_cards(state, player)


declare_reaction("stability", condition=_cond_stability)


@register_effect("action_cards:stability")
def political_stability(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Political Stability: Do not return your strategy card(s). You do not choose strategy cards
    during the next strategy phase.

    Efekt trwa do końca rundy (agenda w tej rundzie nie zwraca kart); egzekwuje go
    ``strategy_phase.reset_strategy_cards`` / ``close_round_cards``.
    """
    if not state.players[player_id].strategy_cards:
        raise ValueError("You have no strategy cards to keep.")
    active_effects.add_effect(state, strategy_phase.STABILITY_KEY, Duration.ROUND, owner=player_id)


# ------------------------------------------------------------------ Crash Landing


def _grid() -> HexGrid:
    return board_graph.bound_grid() or HexGrid()


def _is_mecatol(registry: StaticDataRegistry, planet_id: str) -> bool:
    planet = registry.planets.get(planet_id)
    return planet is not None and planet.name.strip().lower() == _MECATOL_NAME


def _ground_in_orbit(system: SystemState, player_id: str) -> dict[str, int]:
    """Siły naziemne gracza w przestrzeni systemu (typ -> liczba)."""
    return {
        bt: n
        for bt, n in system.space_units.get(player_id, {}).items()
        if n > 0 and not is_space_unit(bt)
    }


def _landing_planets(registry: StaticDataRegistry, system: SystemState) -> list[str]:
    """Planety systemu poza Mecatol Rex."""
    definition = registry.systems.get(system.system_id)
    planets = list(definition.planets) if definition is not None else []
    return [p for p in planets if not _is_mecatol(registry, p)]


def _all_ships_hit(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Czy oczekujące trafienia zniszczą WSZYSTKIE statki gracza (z Sustain Damage włącznie)."""
    combat = state.active_combat
    if combat is None:
        return False
    units = battle.side_units(state, _grid(), registry, player_id)
    absorbable = sum(u.count + u.sustainable for u in units)
    return absorbable > 0 and combat.pending_hits.get(player_id, 0) >= absorbable


@window_provider
def last_ship_destroyed(state: GameState) -> list[OpenWindow]:
    """Okno „Twój ostatni statek w aktywnym systemie zostanie zniszczony" (przypisanie strat)."""
    combat = state.active_combat
    registry = rules_hooks.bound_registry()
    if (
        combat is None
        or registry is None
        or combat.kind != "space"
        or combat.step is not CombatStep.ASSIGN
        or combat.position != state.active_system
    ):
        return []
    windows: list[OpenWindow] = []
    for pid in (combat.defender, combat.attacker):
        if pid == NEUTRAL_PLAYER_ID or pid not in state.players:
            continue
        if _all_ships_hit(state, registry, pid):
            windows.append(
                OpenWindow(
                    GameEvent.UNIT_DESTROYED, Moment.WHEN,
                    {"player": pid, "position": combat.position, "round": combat.round},
                )
            )
    return windows


def _cond_crash(
    state: GameState, registry: StaticDataRegistry, player: str, window: OpenWindow
) -> bool:
    """Masz siły naziemne w przestrzeni systemu i jest planeta inna niż Mecatol Rex."""
    system = state.systems.get(str(window.ctx.get("position", "")))
    return (
        system is not None
        and bool(_ground_in_orbit(system, player))
        and bool(_landing_planets(registry, system))
    )


declare_reaction("crashlanding", condition=_cond_crash)


def _occupants(state: GameState, system: SystemState, planet: str, player_id: str) -> str:
    """Cudze jednostki na planecie (koegzystencja) jako tekst pomocniczy do formularza."""
    others = [
        card_labels.describe_player(state, rules_hooks.bound_registry(), pid)
        for pid, units in system.planet_units.get(planet, {}).items()
        if pid != player_id and any(n > 0 for n in units.values())
    ]
    return f" · units of {', '.join(others)} (coexistence)" if others else ""


@register_effect("action_cards:crashlanding")
def crash_landing(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Crash Landing: Place 1 of your ground forces from the space area of the active system onto a
    planet in that system other than Mecatol Rex; if the planet contains other players' units,
    place your ground force into coexistence.

    ⚠ ZAŁOŻENIE: silnik nie ma osobnego modelu koegzystencji - jednostka trafia do
    ``planet_units`` obok cudzych (jak Exchange Program), kontrola planety się nie zmienia; walka
    naziemna wybucha w kroku Invasion, także bez lądowania (RULES.md 40.1 I7a).
    """
    system = state.systems.get(str(_window_ctx(params).get("position", "")))
    if system is None:
        raise ValueError("There is no active system.")
    base_type, planet = params.get("unit"), params.get("planet")
    if not isinstance(base_type, str) or base_type not in _ground_in_orbit(system, player_id):
        raise ValueError("Choose one of your ground forces in the space area ('unit').")
    if not isinstance(planet, str) or planet not in _landing_planets(registry, system):
        raise ValueError("Choose a planet in the active system other than Mecatol Rex ('planet').")
    unit_ops.transfer_units(state, system, "space", system, planet, player_id, base_type, 1)


@register_effect_inputs("action_cards:crashlanding")
def crash_landing_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    window = reaction_cards.window_for(state, registry, player_id, "crashlanding")
    system = state.systems.get(str(window.ctx.get("position", ""))) if window is not None else None
    if system is None:
        return [_choice("unit", "Ground force in orbit", []), _choice("planet", "Planet", [])]
    where = _system_label(registry, system)
    units = [
        _option(
            bt,
            f"{fleet_pool.unit_name(state, registry, player_id, bt)} ×{n} in orbit · {where}",
        )
        for bt, n in sorted(_ground_in_orbit(system, player_id).items())
    ]
    planets = [
        _option(
            p,
            card_labels.describe_planet(state, registry, p)
            + _occupants(state, system, p, player_id),
        )
        for p in _landing_planets(registry, system)
    ]
    return [
        _choice("unit", "Ground force to land", units),
        _choice("planet", "Planet to crash onto (not Mecatol Rex)", planets),
    ]
