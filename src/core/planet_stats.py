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


_STAT_SUFFIX = "stat"
# Demilitarized Zone: „Units cannot be committed to, produced on, or placed on this planet.”
DMZ_ATTACHMENT = "dmz"


def is_demilitarized(state: GameState, planet_id: str) -> bool:
    """Czy na planecie leży Demilitarized Zone (nie wolno na nią lądować ani stawiać jednostek)."""
    return DMZ_ATTACHMENT in state.planet_attachments.get(planet_id, [])


def is_space_station(registry: StaticDataRegistry, planet_id: str) -> bool:
    """Czy to stacja kosmiczna (R_space_stations: nie planeta; bez sił naziemnych i struktur)."""
    planet = registry.planets.get(planet_id)
    if planet is None:
        return False
    return planet.planet_type == "SPACESTATION" or "SPACESTATION" in (planet.planet_types or [])


def attachment_defs(
    state: GameState, registry: StaticDataRegistry, planet_id: str
) -> list[AttachmentDef]:
    """Definicje attachmentów przyczepionych do planety (kolejność przyczepienia).

    Reguła Research Facility jak w AsyncTI4: attachment ze specjalnością na planecie, która JUŻ
    ma specjalność (z danych albo z wcześniejszego attachmentu), staje się wariantem ``<id>stat``
    z assetów (grafika i modyfikatory +1/+1), np. ``warfare`` -> ``warfarestat``. Brak wariantu
    w danych: zostaje oryginał, a +1/+1 dolicza ``planet_stats``.
    """
    planet = registry.planets.get(planet_id)
    has_specialty = bool(planet is not None and planet.tech_specialties)
    result: list[AttachmentDef] = []
    for attachment in _raw_attachment_defs(state, registry, planet_id):
        if attachment.tech_speciality:
            if has_specialty:
                stat = registry.catalog.get(
                    ComponentCategory.ATTACHMENT, attachment.id + _STAT_SUFFIX
                )
                if isinstance(stat, AttachmentDef):
                    attachment = stat
            has_specialty = True
        result.append(attachment)
    return result


def _raw_attachment_defs(
    state: GameState, registry: StaticDataRegistry, planet_id: str
) -> list[AttachmentDef]:
    """Definicje attachmentów wprost z kart (bez podmiany na wariant ``stat``)."""
    result: list[AttachmentDef] = []
    for card_id in state.planet_attachments.get(planet_id, []):
        card = registry.catalog.get(ComponentCategory.EXPLORATION, card_id)
        attachment_id = card.attachment_id if isinstance(card, ExplorationDef) else None
        if (
            attachment_id is None
            and registry.catalog.get(ComponentCategory.RELIC, card_id) is not None
        ):
            # Relikt przyczepiony do planety (Nano-Forge): id relktu = id attachmentu z danych.
            attachment_id = card_id
        if attachment_id is None:
            attachment_id = _card_attachment(registry, card_id)
        if not attachment_id:
            continue
        attachment = registry.catalog.get(ComponentCategory.ATTACHMENT, attachment_id)
        if isinstance(attachment, AttachmentDef):
            result.append(attachment)
    return result


def _card_attachment(registry: StaticDataRegistry, card_id: str) -> str | None:
    """Attachment z notki (pole ``attachment`` danych - Terraform) albo z lidera o tym samym id
    co attachment (Geoform bohatera Titans) - RULES.md 62.18."""
    note = registry.catalog.get(ComponentCategory.PROMISSORY_NOTE, card_id)
    raw = getattr(note, "raw", None)
    if isinstance(raw, dict) and isinstance(raw.get("attachment"), str):
        return str(raw["attachment"])
    if card_id in registry.leaders:
        return card_id
    return None


def traits(state: GameState, registry: StaticDataRegistry, planet_id: str) -> list[str]:
    """Cechy planety (małe litery, kolejność danych) + cechy z attachmentów (Terraform)."""
    planet = registry.planets.get(planet_id)
    if planet is None:
        return []
    raw = [*(planet.planet_types or []), *([planet.planet_type] if planet.planet_type else [])]
    for attachment in attachment_defs(state, registry, planet_id):
        raw.extend(attachment.planet_types)
    return list(dict.fromkeys(item.lower() for item in raw))


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
        if not attachment.tech_speciality:
            continue  # w tym wariant ``stat`` - jego +1/+1 są już w modyfikatorach wyżej
        # Jedna karta daje JEDNĄ specjalność (karty wielokolorowe: „dowolnego koloru”), więc
        # warunek „już ma specjalność” sprawdzamy raz na attachment, nie na każdy kolor.
        # Tu trafia tylko attachment BEZ wariantu ``stat`` w danych - +1/+1 liczymy ręcznie.
        if specialties:
            resources += 1
            influence += 1
        else:
            specialties.extend(s.lower() for s in attachment.tech_speciality)
    if state.active_effects and _swapped(state, planet_id):
        resources, influence = influence, resources  # Hegemonic Trade Policy (RULES.md 62.7)
    return PlanetStats(resources, influence, tuple(specialties))


def _swapped(state: GameState, planet_id: str) -> bool:
    """Czy efekt kontrolującego zamienia zasoby i wpływ planety (punkt ``planet.swap_values``)."""
    from src.core import rules_hooks  # lokalnie: rules_hooks ładuje hooki korzystające z modułu

    owner = next(
        (s.planet_owners[planet_id] for s in state.systems.values()
         if planet_id in s.planet_owners),
        None,
    )
    return owner is not None and planet_id in rules_hooks.forbidden(
        rules_hooks.POINT_PLANET_SWAP_VALUES, state, owner
    )


def is_legendary(state: GameState, registry: StaticDataRegistry, planet_id: str) -> bool:
    """Czy planeta jest legendarna: własna legenda z danych albo attachment (Nano-Forge)."""
    planet = registry.planets.get(planet_id)
    if planet is not None and planet.legendary_ability_name:
        return True
    return any(a.is_legendary for a in attachment_defs(state, registry, planet_id))


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
