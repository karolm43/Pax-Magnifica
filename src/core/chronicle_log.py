"""Zapisy kroniki partii poza bitwami/podbojami: agendy, ostrzał spoza walki, kroki gry.

Warstwa PREZENTACYJNA (osiągnięcia ekranu końcowego) — niczego nie rozstrzyga w regułach.
Moduł zależy tylko od ``game_state`` i ``activity``, więc mogą go wołać moduły silnika
(agendy, Space Cannon, inwazja) bez cykli importów.

- ``record_agenda`` / ``record_fire`` — wołane w miejscu rozstrzygnięcia (agenda, przydział
  trafień Space Cannon / bombardowania),
- ``record_step`` — po KAŻDYM kroku gry (``step_settle.settle_step``: ta sama ścieżka dla
  serwera i symulacji bota), z różnicy stanów: pasy, mówca, zagrane karty, eksploracje,
  Mecatol, War Suny.
"""

from __future__ import annotations

from typing import Any

from src.core import activity
from src.core.game_state import GameState, Phase

MECATOL_PLANETS = ("mr", "mrte")


def record_agenda(state: GameState, outcome: str, votes: dict[str, dict[str, Any]]) -> None:
    """Zapisuje wynik agendy i głosy graczy (``{pid: {"outcome", "votes"}}``). Mutuje stan."""
    state.chronicle.agendas.append(
        {
            "round": state.round_number,
            "outcome": outcome,
            "votes": {pid: dict(v) for pid, v in votes.items()},
        }
    )


def record_fire(
    state: GameState, by: str | None, victim: str, kind: str, losses: dict[str, int]
) -> None:
    """Zapisuje jednostki zniszczone ogniem spoza walki (``kind``: space_cannon / bombardment
    / defense). Mutuje stan; bez strzelca albo bez strat nic nie zapisuje."""
    units = sum(int(n) for n in losses.values())
    if by is None or by == victim or units <= 0:
        return
    state.chronicle.fire.append(
        {"round": state.round_number, "by": by, "victim": victim, "kind": kind, "units": units}
    )


def _warsuns(state: GameState) -> dict[str, int]:
    """War Suny na planszy per gracz."""
    out: dict[str, int] = {}
    for system in state.systems.values():
        for pid, units in system.space_units.items():
            if units.get("warsun"):
                out[pid] = out.get(pid, 0) + units["warsun"]
        for per_player in system.planet_units.values():
            for pid, units in per_player.items():
                if units.get("warsun"):
                    out[pid] = out.get(pid, 0) + units["warsun"]
    return out


def record_step(before: GameState, after: GameState, label: str) -> None:
    """Dopisuje do kroniki ``after`` skutki jednego kroku gry. Mutuje ``after``.

    Korekty God-Mode nie trafiają do kroniki (to nie są zagrania).
    """
    if activity.is_godmode(label):
        return
    chron = after.chronicle
    rnd = after.round_number

    if after.phase is Phase.STRATEGY and after.speaker_id:
        chron.speakers[str(rnd)] = after.speaker_id

    for pid, player in after.players.items():
        old = before.players.get(pid)
        if old is None:
            continue
        if after.phase is Phase.ACTION and player.passed and not old.passed:
            chron.passes.append({"round": rnd, "player": pid})
        for planet in MECATOL_PLANETS:
            had, has = planet in old.controlled_planets, planet in player.controlled_planets
            if had != has:
                chron.mecatol.append({"round": rnd, "player": pid, "gained": has})

    for fact in activity.public_card_facts(before, after):
        actor = fact.player_id
        if fact.type == "action_card" and actor and fact.value:
            chron.cards_played.setdefault(actor, []).append(fact.value)
        elif fact.type == "explore_card" and actor:
            chron.explorations[actor] = chron.explorations.get(actor, 0) + 1

    for pid, n in _warsuns(after).items():
        if n > chron.peak_warsuns.get(pid, 0):
            chron.peak_warsuns[pid] = n
