"""Akcja komponentu: trzeci typ akcji fazy akcji (RULES.md 31.8).

W fazie akcji gracz w swojej turze wykonuje JEDNĄ z trzech akcji (RULES.md 31.7,
R_action_phase): strategiczną, taktyczną ALBO KOMPONENTU. Akcja komponentu to zagranie
zdolności oznaczonej nagłówkiem „Action" — na karcie akcji, technologii, liderze, relikcie,
karcie eksploracji, promissory note albo arkuszu frakcji (R_component_action).

ZAKRES (świadomy szkielet, motto „make it exist first, make it good later"): ta funkcja
NIE wykonuje żadnej mechaniki konkretnego komponentu — rejestruje jedynie, że gracz wykonał
akcję komponentu w tej turze (``took_action_this_turn = True``), tak samo jak akcja
strategiczna/taktyczna. Dzięki temu gracz ma w UI opcję „zagrałem coś z komponentem" i może
oddać turę, a konkretne efekty (dispatch po ``component_id``) dołożymy komponent po komponencie
— z regułą/źródłem w ``docs/RULES.md`` — bez zmiany kształtu tej warstwy.

Funkcja jest CZYSTA (``state -> state``, operuje na klonie), spójna z Event Sourcingiem.
``component_id`` jest wyłącznie ADNOTACJĄ (trafia do etykiety eventu, „co zagrano"); nie steruje
jeszcze żadnym efektem liczbowym i jest opcjonalny.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import action_budget, rules_hooks, technology_abilities, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase


def play_component_action(
    state: GameState,
    player_id: str | None = None,
    component_id: str | None = None,
    *,
    fire_after: bool = True,
    params: Mapping[str, Any] | None = None,
) -> GameState:
    """Wykonuje akcję komponentu aktywnego gracza — RULES.md 31.8 (R_component_action).

    Waliduje jak pozostałe akcje tury (silnik-sędzia, RULES.md 31.2/31.7):
    - jesteśmy w fazie AKCJI i jest aktywny gracz;
    - gdy podano ``player_id``, musi to być aktywny gracz (jego tura);
    - nie trwa otwarte OKNO czasowe (``pending_window``) — najpierw je rozstrzygnij;
    - gracz NIE wykonał już akcji w tej turze (jedna akcja na turę, „a single action");
    - gracz NIE spasował w tej turze (pas kończy jego akcje w tej fazie — R_action_phase).

    Przy sukcesie ustawia ``took_action_this_turn = True`` (jak akcja strategiczna/taktyczna),
    więc ``End turn`` staje się dostępny. Efekt konkretnego komponentu NIE jest wykonywany
    (szkielet) — ``component_id`` zostaje jako adnotacja dla etykiety eventu.

    Raises:
        ValueError: Gdy faza != ACTION, brak aktywnego gracza, nie jest to tura
            ``player_id``, trwa otwarte okno, albo gracz już wykonał akcję / spasował.
    """
    if state.phase is not Phase.ACTION:
        raise ValueError("A component action can only be performed during the action phase.")
    if state.active_player_id is None:
        raise ValueError("No active player in the action phase.")
    if player_id is not None and player_id != state.active_player_id:
        raise ValueError(
            f"It is not {player_id}'s turn (active: {state.active_player_id})."
        )
    if state.pending_window is not None:
        raise ValueError(
            "Cannot perform a component action while a timing window is open - "
            "resolve it first."
        )

    active_id = state.active_player_id
    player = state.players.get(active_id)
    if player is None:
        raise ValueError(f"Unknown active player: {active_id}")
    if player.passed:
        raise ValueError(
            "You have passed - you cannot perform a component action this action phase."
        )
    action_budget.require_free_action(state, active_id)

    new_state = state.clone()
    # RULES.md 31.7: akcja komponentu liczy się jako AKCJA tury (jak strategiczna/taktyczna).
    # Efekt konkretnego komponentu dojdzie dispatchem po component_id (szkielet — patrz moduł).
    action_budget.register_action(new_state, active_id)
    # Efekt technologii z „ACTION:" (np. Sling Relay): gracz podał wybory, silnik je sprawdza i
    # stosuje. Błąd cofa całą akcję (klon), więc nic się nie zużywa.
    registry = rules_hooks.bound_registry()
    if component_id and registry is not None:
        technology_abilities.run_action_effect(
            new_state, registry, active_id, component_id, dict(params or {})
        )
    if fire_after:
        triggers.fire(
            new_state, GameEvent.COMPONENT_ACTION, Moment.AFTER, subject=active_id,
            ctx={"player": active_id, "component": component_id or ""},
        )
    return new_state
