"""Hooki technologii ogólnych. Aliasy technologii pochodzą z danych (``assets/.../technologies``).

Tekst i parametry technologii czytamy z assetów (RULES.md 55, ``docs/rules_tirules/``); tu żyje
wyłącznie logika wyjątku podpięta pod punkty zaczepienia reguł bazowych (RULES.md 43.1).
Technologie interaktywne (wybory gracza, „may") są w ``technologies_choices.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import rules_hooks
from src.core.game_state import GameState
from src.core.rules_hooks import (
    POINT_BOMBARDMENT_EXTRA_DICE,
    POINT_MOVEMENT_ENTER_ASTEROIDS,
    POINT_MOVEMENT_PASS_FOREIGN_SHIPS,
    POINT_PRODUCTION_COST,
    POINT_SPACE_CANNON_EXTRA_DICE,
    POINT_SPACE_CANNON_ROLL_MODIFIER,
    POINT_STATUS_ACTION_CARDS,
    POINT_STATUS_COMMAND_TOKENS,
    POINT_TURN_ACTIONS,
    SOURCE_TECHNOLOGY,
    HookKind,
    HookSource,
    register,
)

# Aliasy z danych (technologies/pok.json; nie z pamięci). Weryfikowane testem względem rejestru.
ANTIMASS_ALIAS = "amd"
LIGHT_WAVE_ALIAS = "lwd"
SARWEEN_ALIAS = "st"
PLASMA_SCORING_ALIAS = "ps"
NEURAL_MOTIVATOR_ALIAS = "nm"
HYPER_METABOLISM_ALIAS = "hm"
FLEET_LOGISTICS_ALIAS = "fl"

# Ulepszenia jednostek: liczby (koszt, walka, ruch, pojemność, Space Cannon, Bombardment,
# Planetary Shield...) czyta silnik z WARIANTU jednostki (``combat.resolve_unit_variant``).
UNIT_UPGRADE_ALIASES: tuple[str, ...] = ("ws", "cr2", "dd2", "cv2", "pds2", "dn2")
rules_hooks.declare_data_driven(*(f"technologies:{alias}" for alias in UNIT_UPGRADE_ALIASES))


def _source(alias: str) -> HookSource:
    return HookSource(SOURCE_TECHNOLOGY, alias)


# --- Propulsion --------------------------------------------------------------------------


@register(
    POINT_MOVEMENT_ENTER_ASTEROIDS,
    _source(ANTIMASS_ALIAS),
    HookKind.PERMIT,
    covers=f"technologies:{ANTIMASS_ALIAS}",
)
def antimass_enter_asteroids(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> bool:
    """Antimass Deflectors: statki mogą wchodzić do pól asteroid i przez nie przechodzić."""
    return True


@register(
    POINT_SPACE_CANNON_ROLL_MODIFIER,
    _source(ANTIMASS_ALIAS),
    HookKind.MODIFY,
    covers=f"technologies:{ANTIMASS_ALIAS}",
)
def antimass_space_cannon(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> int:
    """Antimass Deflectors: -1 do wyniku kości Space Cannon rzucanych przeciw jego jednostkom."""
    return -1


@register(
    POINT_MOVEMENT_PASS_FOREIGN_SHIPS,
    _source(LIGHT_WAVE_ALIAS),
    HookKind.PERMIT,
    covers=f"technologies:{LIGHT_WAVE_ALIAS}",
)
def light_wave_pass_foreign_ships(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> bool:
    """Light/Wave Deflector: statki mogą przechodzić przez systemy z cudzymi statkami."""
    return True


@register(
    POINT_TURN_ACTIONS,
    _source(FLEET_LOGISTICS_ALIAS),
    HookKind.MODIFY,
    covers=f"technologies:{FLEET_LOGISTICS_ALIAS}",
)
def fleet_logistics_actions(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> int:
    """Fleet Logistics: w swojej turze fazy akcji gracz wykonuje 2 akcje zamiast 1."""
    return 1


# --- Biotic -----------------------------------------------------------------------------


@register(
    POINT_STATUS_ACTION_CARDS,
    _source(NEURAL_MOTIVATOR_ALIAS),
    HookKind.MODIFY,
    covers=f"technologies:{NEURAL_MOTIVATOR_ALIAS}",
)
def neural_motivator_cards(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> int:
    """Neural Motivator: w fazie statusu gracz dobiera 2 karty akcji zamiast 1."""
    return 1


@register(
    POINT_STATUS_COMMAND_TOKENS,
    _source(HYPER_METABOLISM_ALIAS),
    HookKind.MODIFY,
    covers=f"technologies:{HYPER_METABOLISM_ALIAS}",
)
def hyper_metabolism_tokens(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> int:
    """Hyper Metabolism: w fazie statusu gracz zdobywa 3 żetony dowodzenia zamiast 2."""
    return 1


# --- Warfare ----------------------------------------------------------------------------


@register(
    POINT_SPACE_CANNON_EXTRA_DICE,
    _source(PLASMA_SCORING_ALIAS),
    HookKind.MODIFY,
    covers=f"technologies:{PLASMA_SCORING_ALIAS}",
)
def plasma_scoring_space_cannon(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> int:
    """Plasma Scoring: 1 z jednostek używających SPACE CANNON rzuca 1 dodatkową kością."""
    return 1


@register(
    POINT_BOMBARDMENT_EXTRA_DICE,
    _source(PLASMA_SCORING_ALIAS),
    HookKind.MODIFY,
    covers=f"technologies:{PLASMA_SCORING_ALIAS}",
)
def plasma_scoring_bombardment(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> int:
    """Plasma Scoring: 1 z jednostek używających BOMBARDMENT rzuca 1 dodatkową kością."""
    return 1


# --- Cybernetic -------------------------------------------------------------------------


@register(
    POINT_PRODUCTION_COST,
    _source(SARWEEN_ALIAS),
    HookKind.MODIFY,
    covers=f"technologies:{SARWEEN_ALIAS}",
)
def sarween_tools_cost(state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Sarween Tools: gdy jednostki używają PRODUCTION, łączny koszt jest niższy o 1.

    Zniżka dotyczy PIERWSZEGO zamówienia w danej akcji (``production_used == 0``): kolejne
    zamówienia w tym samym użyciu PRODUCTION nie dostają jej drugi raz.
    """
    if state.production_grant is not None or state.active_system is None:
        return 0  # darmowe/przyznane produkcje (karty) nie są użyciem PRODUCTION jednostek
    return -1 if state.production_used == 0 else 0
