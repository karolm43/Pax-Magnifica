"""Efektywne statystyki planet: dane planety + przyczepione attachmenty (RULES.md 46).

JEDYNE miejsce, które liczy zasoby, wpływy i specjalności technologiczne planety z
uwzględnieniem kart attach (Dyson Sphere, Mining World, Research Facility…). Ekonomia,
produkcja i cele czytają stąd — nie z ``registry.planets`` wprost.

Reguła Research Facility (karty Biotic / Cybernetic / Propulsion / Warfare): planeta
dostaje specjalność technologiczną; jeśli JUŻ jakąś ma, wartości zasobów i wpływów rosną
o 1 (każda) ZAMIAST tego. Attachmenty stosujemy w kolejności przyczepienia.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from src.core.components import AttachmentDef, ComponentCategory, ExplorationDef
from src.core.game_state import GameState
from src.core.models import PlanetDef
from src.core.registry import StaticDataRegistry


class PlanetLookup(Protocol):
    """Cokolwiek, co udostępnia ``planets`` (rejestr albo ``EffectivePlanets``)."""

    @property
    def planets(self) -> Mapping[str, PlanetDef]: ...


@dataclass(frozen=True)
class PlanetStats:
    """Zasoby, wpływy i specjalności technologiczne planety z attachmentami."""

    resources: int
    influence: int
    tech_specialties: tuple[str, ...]


@dataclass(frozen=True)
class EffectivePlanets:
    """Widok ``planets`` z podmienionymi wartościami planet z attachmentami."""

    planets: Mapping[str, PlanetDef]


def attachment_defs(
    state: GameState, registry: StaticDataRegistry, planet_id: str
) -> list[AttachmentDef]:
    """Definicje attachmentów przyczepionych do planety (kolejność przyczepienia)."""
    result: list[AttachmentDef] = []
    for card_id in state.planet_attachments.get(planet_id, []):
        card = registry.catalog.get(ComponentCategory.EXPLORATION, card_id)
        attachment_id = card.attachment_id if isinstance(card, ExplorationDef) else None
        if not attachment_id:
            continue
        attachment = registry.catalog.get(ComponentCategory.ATTACHMENT, attachment_id)
        if isinstance(attachment, AttachmentDef):
            result.append(attachment)
    return result


def planet_stats(
    state: GameState, registry: StaticDataRegistry, planet_id: str
) -> PlanetStats | None:
    """Statystyki planety z attachmentami; ``None`` dla planety spoza rejestru."""
    planet = registry.planets.get(planet_id)
    if planet is None:
        return None
    resources, influence = planet.resources, planet.influence
    # Dane potrafią powtarzać specjalność (np. tiamat) — liczy się jedna.
    specialties = list(dict.fromkeys(s.lower() for s in (planet.tech_specialties or [])))
    for attachment in attachment_defs(state, registry, planet_id):
        resources += attachment.resources_modifier
        influence += attachment.influence_modifier
        for specialty in attachment.tech_speciality:
            if specialties:
                resources += 1
                influence += 1
            else:
                specialties.append(specialty.lower())
    return PlanetStats(resources, influence, tuple(specialties))


def resources_of(state: GameState, registry: StaticDataRegistry, planet_id: str) -> int:
    """Zasoby planety (0, gdy nieznana)."""
    stats = planet_stats(state, registry, planet_id)
    return stats.resources if stats is not None else 0


def influence_of(state: GameState, registry: StaticDataRegistry, planet_id: str) -> int:
    """Wpływy planety (0, gdy nieznana)."""
    stats = planet_stats(state, registry, planet_id)
    return stats.influence if stats is not None else 0


def effective_planets(state: GameState, registry: StaticDataRegistry) -> EffectivePlanets:
    """Mapa planet jak ``registry.planets``, ale z wartościami po attachmentach."""
    planets: dict[str, PlanetDef] = dict(registry.planets)
    for planet_id in state.planet_attachments:
        stats = planet_stats(state, registry, planet_id)
        if stats is None:
            continue
        planets[planet_id] = registry.planets[planet_id].model_copy(
            update={
                "resources": stats.resources,
                "influence": stats.influence,
                "tech_specialties": [s.upper() for s in stats.tech_specialties],
            }
        )
    return EffectivePlanets(planets)
