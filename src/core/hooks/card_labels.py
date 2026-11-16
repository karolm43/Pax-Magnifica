"""Czytelne etykiety formularzy kart (planeta, system, gracz, technologia) + domyślne podpowiedzi.

Zasada czytelności: formularz karty ZAWSZE mówi, czego dotyczy wybór. Planeta = nazwa + zasoby /
wpływ + cechy + system, system = pozycja + planety, gracz = frakcja (kolor), technologia = nazwa
+ typ. Liczby pochodzą z ``planet_stats`` (z attachmentami) i rejestru, nigdy z pamięci.
"""

from __future__ import annotations

from typing import Any

from src.core import exploration, planet_stats
from src.core.game_state import GameState, SystemState
from src.core.models import TechnologyDef
from src.core.registry import StaticDataRegistry

_MAX_HINT = 260  # krótko: jedno zdanie, nie cały tekst karty


def planet_name(registry: StaticDataRegistry, planet_id: str) -> str:
    """Nazwa planety z rejestru (id, gdy nieznana)."""
    planet = registry.planets.get(planet_id)
    return planet.name if planet is not None else planet_id


def system_position_of_planet(state: GameState, planet_id: str) -> str | None:
    """Pozycja systemu, w którym leży planeta (``None``, gdy jej nie ma na planszy)."""
    for system in state.systems.values():
        if planet_id in system.planet_owners or planet_id in system.planet_units:
            return system.position
    return None


def planet_stats_text(state: GameState, registry: StaticDataRegistry, planet_id: str) -> str:
    """``"1 resource / 6 influence"`` (po attachmentach); pusty tekst dla planety spoza rejestru."""
    stats = planet_stats.planet_stats(state, registry, planet_id)
    if stats is None:
        return ""
    plural = "" if stats.resources == 1 else "s"
    return f"{stats.resources} resource{plural} / {stats.influence} influence"


def describe_planet(
    state: GameState,
    registry: StaticDataRegistry,
    planet_id: str,
    *,
    effect: str = "",
    with_system: bool = True,
) -> str:
    """Planeta: ``Nazwa · 1 resource / 6 influence · cechy · system 000 [→ skutek]``."""
    parts = [planet_name(registry, planet_id)]
    stats_text = planet_stats_text(state, registry, planet_id)
    if stats_text:
        parts.append(stats_text)
    traits = exploration.planet_traits(registry, planet_id)
    stats = planet_stats.planet_stats(state, registry, planet_id)
    features = list(traits)
    if stats is not None:
        features += [f"{s} specialty" for s in stats.tech_specialties]
    if features:
        parts.append(", ".join(features))
    if with_system:
        position = system_position_of_planet(state, planet_id)
        if position is not None:
            parts.append(f"system {position}")
    text = " · ".join(parts)
    return f"{text} → {effect}" if effect else text


def describe_system(state: GameState, registry: StaticDataRegistry, position: str) -> str:
    """System: ``System 101 · Nazwa A (2/1), Nazwa B (0/3)`` (zasoby/wpływ) albo „empty space”."""
    system = state.systems.get(position)
    if system is None:
        return f"System {position}"
    return describe_system_state(registry, system, state)


def describe_system_state(
    registry: StaticDataRegistry, system: SystemState, state: GameState | None = None
) -> str:
    """Jak ``describe_system``, ale z samego ``SystemState`` (bez ``state`` = statystyki bazowe)."""
    definition = registry.systems.get(system.system_id)
    planets = []
    for planet_id in definition.planets if definition is not None else []:
        if state is not None:
            stats = planet_stats.planet_stats(state, registry, planet_id)
            numbers = (stats.resources, stats.influence) if stats is not None else None
        else:
            base = registry.planets.get(planet_id)
            numbers = (base.resources, base.influence) if base is not None else None
        values = f" ({numbers[0]}/{numbers[1]})" if numbers is not None else ""
        planets.append(f"{planet_name(registry, planet_id)}{values}")
    body = ", ".join(planets) if planets else "no planets"
    return f"System {system.position} · {body}"


def describe_player(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    """Gracz: ``Frakcja (kolor)``."""
    player = state.players.get(player_id)
    if player is None:
        return player_id
    faction = registry.factions.get(player.faction) if player.faction else None
    name = faction.name if faction is not None else player_id
    return f"{name} ({player.color})" if player.color else name


def describe_technology(tech: TechnologyDef) -> str:
    """Technologia: ``Nazwa · typ`` (kolor/rodzaj z danych)."""
    label = "/".join(t.lower() for t in tech.types) or "unit upgrade"
    return f"{tech.name or tech.id} · {label}"


def relic_name(registry: StaticDataRegistry, relic_id: str) -> str:
    """Pełna nazwa reliktu z danych (nigdy surowe id)."""
    from src.core import relic_actions  # leniwie: relic_actions importuje moduły hooków

    return relic_actions.relic_def(registry, relic_id).name or relic_id


def strategy_card_name(registry: StaticDataRegistry, initiative: int) -> str:
    """Nazwa karty strategii o danej inicjatywie z kanonicznego zestawu (RULES.md 14)."""
    for card in registry.strategy_card_set():
        if card.initiative == initiative and card.name:
            return str(card.name)
    return f"Strategy card {initiative}"


def describe_strategy_card(registry: StaticDataRegistry, initiative: int, extra: str = "") -> str:
    """Karta strategii: ``Nazwa - initiative N`` (+ `` · dopisek``). Pełny tekst primary /
    secondary UI dokłada z odnośnika ``ref=("strategy", N)`` opcji (``offer_inputs.option``)."""
    label = f"{strategy_card_name(registry, initiative)} - initiative {initiative}"
    return f"{label} · {extra}" if extra else label


def with_default_hints(
    inputs: list[dict[str, Any]], card_name: str, card_text: str
) -> list[dict[str, Any]]:
    """Uzupełnia puste ``hint`` wejść (własnych nie nadpisuje): czego dotyczy wybór + skutek."""
    sentence = " ".join(card_text.split())
    if len(sentence) > _MAX_HINT:
        sentence = sentence[: _MAX_HINT - 1].rstrip() + "…"
    for item in inputs:
        if not str(item.get("hint") or "").strip():
            label = str(item.get("label") or item.get("key") or "choice")
            item["hint"] = f"{card_name}: {label}. {sentence}".strip()
    return inputs
