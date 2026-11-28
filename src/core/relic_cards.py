"""Relikty gracza w UI: zagrywalność (zakładka Relics na ręce) i zagranie ACTION (RULES.md 59).

Odpowiednik ``action_cards`` dla reliktów. Relikt leży jawnie przed graczem
(``PlayerState.relics``), więc zakładka pokazuje WSZYSTKIE jego relikty: z ``ACTION:`` - do
przeciągnięcia na strefę akcji (jeśli legalne teraz), pasywne - tylko do obejrzenia (działają
same, patrz hooki). Funkcje są CZYSTE (``state -> state``); zagranie to akcja komponentu tury
(``component_action``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import component_action, offer_inputs, relic_actions
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry


def playability(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Relikty gracza z informacją, które można zagrać TERAZ jako akcję komponentu.

    Wiersz: ``relic_id``, ``kind`` (``action``/``passive``), ``playable``, ``reason`` (gdy nie),
    ``implemented``, ``exhausted``. ACTION jest zagrywalne, gdy tura/faza/okno pozwalają na akcję
    komponentu (te same walidacje co zagranie), warunek reliktu jest spełniony, a każde wymagane
    wejście formularza ma legalne opcje. Nie mutuje stanu.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    rows: list[dict[str, Any]] = []
    # Own relics, then other players' relic agents copied through a proxy (Ssruu: JR-XS455-O -
    # C_relics jrxs455o 1.2), so the copy shows up in the Relics tab by itself.
    copied = list(relic_actions.relic_proxies(state, player_id))
    for relic_id in dict.fromkeys([*player.relics, *copied]):
        info = relic_actions.form(state, registry, player_id, relic_id)
        row: dict[str, Any] = {
            "relic_id": relic_id,
            "kind": info["kind"],
            "playable": False,
            "reason": None,
            "implemented": info["implemented"],
            "exhausted": info["exhausted"],
            "copied_by": info["copied_by"],
        }
        rows.append(row)
        if info["kind"] != "action":
            row["reason"] = "Passive - it works on its own."
            continue
        try:
            component_action.play_component_action(
                state, player_id, relic_id, fire_after=False, run_effect=False
            )
        except ValueError as exc:
            row["reason"] = str(exc)
            continue
        reason = relic_actions.block_reason(state, registry, player_id, relic_id)
        if reason is not None:
            row["reason"] = reason
        elif info["implemented"] and not offer_inputs.has_legal_answer(info["inputs"]):
            row["reason"] = "No legal target for this relic right now."
        else:
            row["playable"] = True
    return rows


def play_relic(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    relic_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    actor_id: str | None = None,
) -> tuple[GameState, bool]:
    """Aktywny gracz zagrywa ACTION swojego reliktu (jego akcja w turze).

    Walidacje (czyja tura, faza, okno, jedna akcja - przez ``component_action``; relikt przed
    graczem; warunek reliktu) -> efekt na klonie. Błąd na dowolnym etapie = ``ValueError`` i ZERO
    zmian. Relikt BEZ zakodowanego efektu jest zagrany jako akcja, a wynik ma
    ``implemented=False`` (skutek rozstrzyga operator, God-Mode).

    Returns:
        ``(nowy stan, implemented)``.

    Raises:
        ValueError: Relikt nieznany / nie ma ACTION / nie należy do gracza / nie ta tura / złe
            parametry.
    """
    if actor_id is not None and actor_id != player_id:
        raise ValueError(f"{actor_id} cannot play a relic for {player_id}.")
    info = relic_actions.form(state, registry, player_id, relic_id)
    if info["kind"] != "action":
        raise ValueError(f"{info['name']} has no ACTION - it works on its own.")
    reason = relic_actions.block_reason(state, registry, player_id, relic_id)
    if reason is not None:
        raise ValueError(reason)
    new_state = component_action.play_component_action(
        state, player_id, relic_id, params=params
    )
    return new_state, bool(info["implemented"])
