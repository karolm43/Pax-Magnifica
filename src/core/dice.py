"""Rzuty kośćmi silnika (d10) — seedowalne, deterministyczne, trzymane w stanie gry.

Wspólna podstawa dla Space Cannon (RULES.md 38), walki, bombardmentu i AFB. Funkcje CZYSTE
względem ``GameState`` (zwracają nowy stan z przesuniętym licznikiem), więc Undo/Redo/Replay
dają te same wyniki: ziarno i licznik leżą w stanie (``rng_seed`` / ``rng_counter``).

Jedyny „efekt uboczny": gdy stan nie ma jeszcze ziarna (``rng_seed == 0``), PIERWSZY rzut losuje
je z ``secrets`` i zapisuje w zwróconym stanie. Dopiero potem wszystko jest deterministyczne.
Testy podają ziarno wprost (``GameState(rng_seed=…)``).
"""

from __future__ import annotations

import random
import secrets

from src.core.game_state import GameState

# Liczba ścianek kości TI4 (d10; „0" na kości = 10 — RULES.md 38, S4).
DIE_SIDES = 10


def roll_dice(state: GameState, count: int, sides: int = DIE_SIDES) -> tuple[GameState, list[int]]:
    """Rzuca ``count`` kości ``sides``-ściennych i zwraca (nowy stan, wyniki 1..sides).

    Każde wywołanie bierze osobny strumień ``Random(f"{seed}:{counter}")`` i zwiększa
    ``rng_counter`` o 1 — wynik zależy tylko od (ziarno, licznik), nie od liczby wcześniejszych
    rzutów w innym miejscu kodu.

    Raises:
        ValueError: Gdy ``count`` jest ujemne albo ``sides`` < 2.
    """
    if count < 0:
        raise ValueError("The number of dice must not be negative.")
    if sides < 2:
        raise ValueError("A die needs at least 2 sides.")
    new_state = state.clone()
    if new_state.rng_seed == 0:
        new_state.rng_seed = secrets.randbelow(2**31 - 1) + 1
    rng = random.Random(f"{new_state.rng_seed}:{new_state.rng_counter}")
    results = [rng.randint(1, sides) for _ in range(count)]
    new_state.rng_counter += 1
    return new_state, results


def next_rng(state: GameState) -> random.Random:
    """Zwraca seedowalny generator i przesuwa licznik w PRZEKAZANYM stanie (mutuje!).

    Dla tasowania talii i innych losowań poza kośćmi. Wołający pracuje na własnym klonie
    (jak w ``roll_dice``). Strumień zależy tylko od (ziarno, licznik) — Undo/Redo bezpieczne.
    """
    if state.rng_seed == 0:
        state.rng_seed = secrets.randbelow(2**31 - 1) + 1
    rng = random.Random(f"{state.rng_seed}:{state.rng_counter}")
    state.rng_counter += 1
    return rng


def record_table_roll(
    state: GameState,
    player_id: str,
    kind: str,
    label: str,
    results: list[int],
    *,
    hits_on: int | None = None,
    hit_values: list[int] | None = None,
    summary: str = "",
) -> None:
    """Zapisuje rzut „na stół" poza walką (MUTUJE ``state`` — klon wołającego).

    UI animuje go fizycznymi kośćmi (``frontend/src/domains/dice``): wynik jest już rozstrzygnięty
    tutaj, a ``table_roll_seq`` pozwala klientowi odróżnić NOWY rzut od starego. KAŻDY nowy rzut
    kośćmi spoza walki/Space Cannon/inwazji (karta akcji, relikt, przełom…) wołaj tę funkcję.

    ``hits_on`` = próg trafienia (wynik ≥ próg), ``hit_values`` = dokładne „trafiające" wyniki
    (np. Fracture: 1 i 10); brak obu = rzut bez trafień (sam wynik).
    """
    state.table_roll_seq += 1
    state.table_roll = {
        "seq": state.table_roll_seq,
        "kind": kind,
        "playerId": player_id,
        "label": label,
        "dice": list(results),
        "hitsOn": hits_on,
        "hitValues": hit_values,
        "summary": summary,
    }


def count_hits(results: list[int], hits_on: int) -> int:
    """Liczba trafień: wyniki równe lub większe od ``hits_on`` (RULES.md 38, S4)."""
    return sum(1 for value in results if value >= hits_on)
