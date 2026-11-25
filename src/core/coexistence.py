"""Coexistence (block I4) — R_coexistence, RULES.md 40.1 (I7b).

Coexistence is DERIVED from the board: one player controls a planet (``planet_owners``) and every
other player with ground forces or structures on it is coexisting there (R_coexistence notes 2).
Control is sticky (RULES.md 23), so units of several players can share a planet.

On top of that, ``SystemState.coexisting`` lists the players who coexist BY CHOICE of an effect
(Slumberstate Computing: "you may choose for your units to coexist instead"). Only they are
exempt from the forced ground combat of RULES.md 40.1 I7a; units that merely share a planet
(Crash Landing, Exchange Program) still fight when the planet's system is invaded.

Low layer: depends only on the game state (used by ``battle``, ``invasion``, hooks).
"""

from __future__ import annotations

from collections.abc import Iterable

from src.core.game_state import GameState, SystemState
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.unit_catalog import is_space_unit


def players_on(system: SystemState | None, planet: str) -> set[str]:
    """Players (not the neutral units) with ground forces or structures on ``planet``."""
    if system is None:
        return set()
    return {
        pid
        for pid, by_type in system.planet_units.get(planet, {}).items()
        if pid != NEUTRAL_PLAYER_ID
        and any(n > 0 and not is_space_unit(bt) for bt, n in by_type.items())
    }


def coexisting_players(state: GameState, position: str, planet: str) -> list[str]:
    """Players coexisting on ``planet``: units on it, but not its controller (notes 2)."""
    system = state.systems.get(position)
    owner = system.planet_owners.get(planet) if system is not None else None
    return sorted(players_on(system, planet) - {owner} if owner else set())


def is_coexisting(state: GameState, position: str, planet: str, player_id: str) -> bool:
    return player_id in coexisting_players(state, position, planet)


def partners(state: GameState, player_id: str) -> set[str]:
    """Players ``player_id`` is coexisting with: they share a planet and one of the two does not
    control it (Slumberstate Computing: "for each player you are coexisting with")."""
    found: set[str] = set()
    for position, system in state.systems.items():
        for planet in system.planet_units:
            present = players_on(system, planet)
            if player_id not in present or len(present) < 2:
                continue
            owner = system.planet_owners.get(planet)
            for other in present - {player_id}:
                if owner != player_id or other in coexisting_players(state, position, planet):
                    found.add(other)
    return {pid for pid in found if pid in state.players}


def peaceful(state: GameState, position: str, planet: str) -> set[str]:
    """Players who CHOSE to coexist on ``planet`` and still do (units there, not controller)."""
    system = state.systems.get(position)
    if system is None:
        return set()
    chosen = set(system.coexisting.get(planet, []))
    return chosen & set(coexisting_players(state, position, planet))


def choose(state: GameState, position: str, planet: str, player_id: str) -> None:
    """``player_id`` coexists on ``planet`` by choice (MUTATES ``state``).

    The controller keeps the planet (notes 2.1). ⚠️ ASSUMPTION (RULES.md 40.1 I7b): only a
    player that does not control the planet is marked - nothing in the engine asks the
    controller to coexist on its own planet (notes 2.2).
    """
    system = state.systems[position]
    if system.planet_owners.get(planet) == player_id:
        return
    listed = system.coexisting.setdefault(planet, [])
    if player_id not in listed:
        listed.append(player_id)
        listed.sort()


def end(state: GameState, position: str, planets: Iterable[str], player_id: str) -> None:
    """``player_id`` stops coexisting by choice on ``planets`` (starts a ground combat - notes 16;
    MUTATES ``state``). Also drops entries left by players who are gone."""
    system = state.systems.get(position)
    if system is None:
        return
    for planet in planets:
        listed = [
            pid for pid in system.coexisting.get(planet, [])
            if pid != player_id and pid in peaceful(state, position, planet)
        ]
        if listed:
            system.coexisting[planet] = listed
        else:
            system.coexisting.pop(planet, None)


def fighting(
    state: GameState,
    position: str,
    planet: str,
    attacker: str,
    candidates: Iterable[str],
    *,
    committed: bool,
) -> list[str]:
    """Which of ``candidates`` (other players with ground forces on ``planet``) the attacker
    fights in the Invasion step (RULES.md 40.1 I7b).

    - The attacker coexists by choice and committed nothing to the planet: no combat at all.
    - The attacker controls the planet and committed ground forces to it: it starts a combat
      against every coexisting player (notes 12; ⚠️ ASSUMPTION: committing = starting it).
    - Otherwise players coexisting by choice stay out of the combat and remain coexisting
      (notes 14-15: an invader fights the controller; ⚠️ ASSUMPTION "Auto": no further combat).
    """
    others = sorted(set(candidates) - {attacker})
    calm = peaceful(state, position, planet)
    if attacker in calm and not committed:
        return []
    system = state.systems.get(position)
    owner = system.planet_owners.get(planet) if system is not None else None
    if committed and owner == attacker:
        return others
    return [pid for pid in others if pid not in calm]
