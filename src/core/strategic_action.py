"""Akcja strategiczna: primary + okno secondary kart strategii (Etap E8-T3).

Rozstrzyga PRIMARY karty aktywnego gracza i otwiera OKNO CZASOWE ``STRATEGY_SECONDARY``
dla pozostałych graczy (kolejka od gracza po aktywnym, zgodnie z zegarem — RULES.md 30.1).
Każdy respondent okna wykonuje secondary albo pasuje; po zamknięciu okna karta jest
wyczerpana (exhaust).

Architektura pod rozbudowę (motto: „make it exist first, make it good later", ale zawsze
z myślą o rozbudowie): efekty primary/secondary to osobny DISPATCH po numerze inicjatywy
karty (``_PRIMARY_EFFECTS`` / ``_SECONDARY_EFFECTS``). Dokładanie kolejnej karty = nowa
gałąź dispatchu + wpis reguły w ``docs/RULES.md`` ze źródłem. Model okna niesie kontekst
(``initiative``), więc ``resolve_secondary`` wie, którą kartę rozstrzygać, bez zmiany
kształtu okna. Funkcje są CZYSTE (``state -> state``, operują na klonie).

ZAKRES T3 (świadomy szkielet, RULES.md 30.2): zaimplementowana jest realnie tylko
Leadership (initiative 1) — primary +3 żetony dowodzenia; secondary to mechanika okna
(wykonaj/pas) BEZ kupowania żetonów za wpływ (odłożone do modelu wpływu — oznaczone TODO).
Pozostałe karty mają domyślny efekt „brak" (szkielet okna i tak działa).
"""

from __future__ import annotations

from collections.abc import Callable

from src.core import timing
from src.core.game_state import GameState, WindowType
from src.core.registry import StaticDataRegistry

# Numer inicjatywy Leadership (z danych, nie z pamięci: assets/.../pok.json → "Leadership"=1).
# Trzymany jako stała lokalna dla czytelności dispatchu; weryfikowany testem względem rejestru.
_LEADERSHIP_INITIATIVE = 1

# Ile żetonów dowodzenia daje primary Leadership (RULES.md 30.2; LRR R_leadership).
_LEADERSHIP_PRIMARY_TOKENS = 3

# Typ funkcji efektu: (state_klon, registry, player_id) -> None (mutuje klon w miejscu).
EffectFn = Callable[[GameState, StaticDataRegistry, str], None]


def _leadership_primary(state: GameState, _registry: StaticDataRegistry, player_id: str) -> None:
    """Primary Leadership: +3 żetony dowodzenia (RULES.md 30.2).

    ⚠️ ZAŁOŻENIE (do rozbudowy): żetony trafiają do puli TAKTYCZNEJ. Docelowo gracz
    wybiera pulę (taktyczna/floty/strategiczna). TODO: kupno dodatkowych żetonów za
    wpływ (nadwyżka primary) — wymaga modelu wydawania wpływu.
    """
    player = state.players.get(player_id)
    if player is None:
        return
    player.tactical_cc += _LEADERSHIP_PRIMARY_TOKENS


def _leadership_secondary(state: GameState, _registry: StaticDataRegistry, player_id: str) -> None:
    """Secondary Leadership: kupno żetonów za wpływ (RULES.md 30.2).

    TODO (odłożone w T3 — „make it exist first"): wydanie wpływu → 1 żeton za 3 wpływu,
    bez żetonu strategicznego (wyjątek Leadership). Wymaga modelu wydawania wpływu
    (wyczerpywanie planet + sumowanie influence). Na razie NO-OP: respondent „wykonuje"
    secondary, ale efekt liczbowy dojdzie z modelem wpływu. Mechanika okna działa.
    """
    # Celowo puste — patrz docstring. Zostawione jako jawny punkt rozbudowy.
    return


# Dispatch efektów primary po inicjatywie karty. Brak wpisu = „brak efektu" (szkielet
# okna i tak zadziała; efekt dokładamy kartą po karcie).
_PRIMARY_EFFECTS: dict[int, EffectFn] = {
    _LEADERSHIP_INITIATIVE: _leadership_primary,
}

# Dispatch efektów secondary po inicjatywie karty.
_SECONDARY_EFFECTS: dict[int, EffectFn] = {
    _LEADERSHIP_INITIATIVE: _leadership_secondary,
}


def _card_initiative_of_player(state: GameState, player_id: str) -> int | None:
    """Najniższy numer karty strategii gracza (jego karta do zagrania), lub None."""
    player = state.players.get(player_id)
    if player is None or not player.strategy_cards:
        return None
    return min(player.strategy_cards)


def play_strategy_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    initiative: int,
) -> GameState:
    """Akcja strategiczna: rozstrzyga PRIMARY i otwiera okno SECONDARY (RULES.md 30.1).

    Kroki:
    1. Walidacja: gracz istnieje i POSIADA kartę o danej inicjatywie.
    2. Rozstrzygnięcie primary (dispatch po inicjatywie; brak efektu = szkielet).
    3. Oznaczenie karty jako ZAGRANEJ (exhausted_strategy_cards) — jak dotąd.
    4. Otwarcie okna ``STRATEGY_SECONDARY`` z kolejką pozostałych graczy (od gracza po
       aktywnym, zgodnie z zegarem), kontekst = {"initiative": n}.

    Raises:
        ValueError: Gdy gracz nie istnieje, nie posiada karty, albo inne okno już trwa.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    player = state.players[player_id]
    if initiative not in player.strategy_cards:
        raise ValueError(f"Player does not hold the initiative card {initiative}.")
    if state.pending_window is not None:
        raise ValueError(
            "Another timing window is already open - resolve it before the strategic action."
        )

    new_state = state.clone()
    target = new_state.players[player_id]

    # 2. Primary (dispatch; brak wpisu = brak efektu liczbowego, szkielet).
    effect = _PRIMARY_EFFECTS.get(initiative)
    if effect is not None:
        effect(new_state, registry, player_id)

    # 3. Oznacz kartę jako zagraną (idempotentnie) + akcja strategiczna = akcja tury.
    if initiative not in target.exhausted_strategy_cards:
        target.exhausted_strategy_cards = [*target.exhausted_strategy_cards, initiative]
    # RULES.md 31.7: akcja strategiczna liczy się jako AKCJA tury — gracz może teraz
    # zakończyć turę (End turn przestaje być zablokowany „brakiem akcji").
    target.took_action_this_turn = True

    # 4. Otwórz okno secondary z kolejką pozostałych graczy (inicjator pominięty).
    #    Gdy NIE MA kogo pytać (gra solo / tylko bieżący gracz / pozostali poza stołem),
    #    NIE otwieramy okna — puste okno byłoby od razu „zakończone", ale nikt by go nie
    #    zamknął, więc ``pending_window`` zostawałby ustawiony i blokował End turn na stałe
    #    (bug: zagranie karty → End turn szary na zawsze). Brak respondentów = brak okna.
    queue = timing.build_response_queue(new_state, player_id)
    if not queue:
        return new_state
    new_state = timing.open_window(
        new_state,
        WindowType.STRATEGY_SECONDARY,
        queue,
        context={"initiative": initiative},
    )
    return new_state


def resolve_secondary(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    *,
    execute: bool,
) -> GameState:
    """Rozstrzyga odpowiedź bieżącego respondenta w oknie secondary (RULES.md 30.1).

    ``execute=True`` → respondent WYKONUJE secondary (dispatch efektu po inicjatywie
    z kontekstu okna). ``execute=False`` → PAS (brak efektu). W obu przypadkach kolejka
    okna przesuwa się o jeden (``timing.respond_current``). Gdy okno się dopełni, jest
    ZAMYKANE automatycznie (karta już oznaczona jako zagrana w ``play_strategy_card``).

    Raises:
        ValueError: Gdy brak okna secondary, zły respondent (poza kolejnością) lub
            okno nie jest typu ``STRATEGY_SECONDARY``.
    """
    window = state.pending_window
    if window is None or window.window_type is not WindowType.STRATEGY_SECONDARY:
        raise ValueError("No open strategy card secondary window.")

    # Wykonanie efektu PRZED przesunięciem kolejki (gdy gracz wybrał „wykonaj").
    new_state = state.clone()
    if execute:
        initiative = int(window.context.get("initiative", 0))
        effect = _SECONDARY_EFFECTS.get(initiative)
        if effect is not None:
            effect(new_state, registry, player_id)

    # Przesunięcie kolejki (waliduje, że player_id to bieżący respondent).
    new_state = timing.respond_current(new_state, player_id)

    # Auto-zamknięcie po dopełnieniu okna (wszyscy mieli okazję na secondary).
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
    return new_state
