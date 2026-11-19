"""Jednostki neutralne (R_neutral_units, RULES.md 50).

Neutralnych NIE prowadzi żaden gracz: „Neutral units are considered to be another player's
ships ... However, there is no neutral player". Silnik trzyma je w ``space_units`` /
``planet_units`` pod stałym kluczem :data:`NEUTRAL_PLAYER_ID`, a nie w ``state.players``.
Walka widzi w nich zwykłego przeciwnika (statki / siły naziemne innego „gracza"), ale
neutralni nigdy nie przejmują kontroli nad planetą (patrz ``control.recompute_from_units``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # tylko typy - neutral jest liściem zależności
    from src.core.game_state import GameState
    from src.core.registry import StaticDataRegistry

NEUTRAL_PLAYER_ID = "neutral"
NEUTRAL_FACTION_ID = "neutral"  # „frakcja” z assets/data/factions/other.json (lista jednostek)


def neutral_technologies(registry: StaticDataRegistry) -> list[str]:
    """Technologie ulepszeń jednostek, których „używają” neutralni (RULES.md 50.3).

    Decyzja użytkownika 2026-11-18: karta referencyjna neutralnych = jednostki ULEPSZONE
    (Destroyer II, Cruiser II…). Neutralni nie mają technologii (R_neutral_units), więc to nie
    stan gry, tylko klucz wyboru wariantu: ``required_tech_id`` generycznych ulepszeń typów z
    listy jednostek frakcji ``neutral`` (dane, zero liczb z pamięci).
    """
    faction = registry.factions.get(NEUTRAL_FACTION_ID)
    base_types = set(faction.units) if faction is not None else set()
    return sorted({
        unit.required_tech_id
        for unit in registry.units.values()
        if unit.faction is None
        and unit.upgrades_from_unit_id is not None
        and unit.base_type in base_types
        and unit.required_tech_id
    })


def variant_key(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> tuple[str | None, list[str], bool, bool]:
    """``(frakcja, technologie, przełom, przełom odwrócony)`` do ``combat.resolve_unit_variant`` -
    gracz albo neutralni (ulepszone jednostki, ``neutral_technologies``)."""
    player = state.players.get(player_id)
    if player is not None:
        return (player.faction, list(player.technologies), player.breakthrough_unlocked,
                player.breakthrough_flipped)
    if player_id == NEUTRAL_PLAYER_ID:
        return NEUTRAL_FACTION_ID, neutral_technologies(registry), False, False
    return None, [], False, False
