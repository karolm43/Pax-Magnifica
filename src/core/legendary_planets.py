"""Legendarne planety — karty zdolności, ich gotowość i dary dla Mecatol Rex (RULES.md 60).

Karta zdolności legendarnej to osobny komponent gracza, który kontroluje planetę. Wyczerpuje się
i odświeża NIEZALEŻNIE od karty planety (``PlayerState.exhausted_legendaries`` przez
``core/exhaust.py``), a przechodzi razem z kontrolą planety (``core/control.py``). Same zdolności
siedzą w hookach (``core/hooks/planets_legendary.py``); ten moduł trzyma wspólne zapytania o stan
i dary Custodia Vigilia dla Mecatol Rex (Space Cannon / PRODUCTION), z których korzystają
``space_cannon`` i ``production``. Dane liczbowe tylko z assetów (``PlanetDef``), nic z pamięci.
"""

from __future__ import annotations

import re

from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

# Planeta, której zdolność nadaje Mecatol Rex SPACE CANNON i PRODUCTION (Keleres, Codex III).
CUSTODIAN_FAVOUR_PLANET = "custodiavigilia"
# Karty planety Mecatol Rex (wersja bazowa i Thunder's Edge).
MECATOL_PLANETS: tuple[str, ...] = ("mr", "mrte")

_PRODUCTION_RE = re.compile(r"PRODUCTION\s+(\d+)")


def legendary_planets_of(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[str]:
    """Planety z kartą zdolności legendarnej, które gracz kontroluje (w kolejności kontroli)."""
    player = state.players.get(player_id)
    if player is None:
        return []
    return [
        planet_id
        for planet_id in player.controlled_planets
        if (planet := registry.planets.get(planet_id)) is not None
        and planet.legendary_ability_name
    ]


def is_ready(state: GameState, player_id: str, planet_id: str) -> bool:
    """Czy gracz ma gotową kartę zdolności tej planety (kontroluje ją i nie jest wyczerpana)."""
    player = state.players.get(player_id)
    return (
        player is not None
        and planet_id in player.controlled_planets
        and planet_id not in player.exhausted_legendaries
    )


def mecatol_planet_in(
    state: GameState, player_id: str, position: str
) -> str | None:
    """Karta Mecatol Rex w systemie ``position``, którą kontroluje gracz (``None`` = brak)."""
    system = state.systems.get(position)
    if system is None:
        return None
    for planet_id in MECATOL_PLANETS:
        if system.planet_owners.get(planet_id) == player_id:
            return planet_id
    return None


def has_custodian_favour(state: GameState, player_id: str) -> bool:
    """Czy gracz kontroluje Custodia Vigilia (jego zdolność nadaje Mecatol Rex dary)."""
    player = state.players.get(player_id)
    return player is not None and CUSTODIAN_FAVOUR_PLANET in player.controlled_planets


def mecatol_grants_planet(state: GameState, player_id: str, position: str) -> str | None:
    """Mecatol Rex gracza w ``position``, jeśli zdolność Custodia Vigilia nadaje mu dary.

    „While you control Mecatol Rex, it gains SPACE CANNON 5 and PRODUCTION 3." - warunek: gracz
    kontroluje Custodia Vigilia ORAZ Mecatol Rex w tym systemie.
    """
    if not has_custodian_favour(state, player_id):
        return None
    return mecatol_planet_in(state, player_id, position)


def favour_space_cannon(registry: StaticDataRegistry) -> tuple[int, int] | None:
    """Space Cannon nadany Mecatol Rex: ``(próg trafienia, kości)`` z danych planety."""
    planet = registry.planets.get(CUSTODIAN_FAVOUR_PLANET)
    if planet is None or not planet.space_cannon_hits_on:
        return None
    return planet.space_cannon_hits_on, planet.space_cannon_die_count or 1


def favour_production(registry: StaticDataRegistry) -> int:
    """Wartość PRODUCTION nadana Mecatol Rex (z tekstu zdolności w assetach); 0 = brak."""
    planet = registry.planets.get(CUSTODIAN_FAVOUR_PLANET)
    match = _PRODUCTION_RE.search(planet.legendary_ability_text or "") if planet else None
    return int(match.group(1)) if match else 0
