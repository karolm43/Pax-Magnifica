"""Żeton Custodians na Mecatol Rex (RULES.md 52; tirules: R_custodians_token).

Żeton leży na Mecatol Rex od setupu. Dopóki leży, nie wolno lądować tam siłami naziemnymi.
Przed krokiem Commit Ground Forces aktywny gracz może go zdjąć, wydając 6 wpływu; wtedy MUSI
zlądować co najmniej jedną siłę naziemną na Mecatol Rex. Zdjęcie daje 1 VP i dodaje fazę agendy
do wszystkich następnych rund (także bieżącej) — flaga ``GameState.custodians_removed``.

Funkcje CZYSTE (``state -> state``) albo predykaty; ``ValueError`` → HTTP 422. Zmiana VP idzie
przez ``objectives.award_points``, wydatek przez ``payment`` (punkty centralne, RULES.md 43.1a).
"""

from __future__ import annotations

from src.core import objectives, payment, rules_hooks
from src.core.game_state import GameState
from src.core.map_string import MECATOL_SYSTEM_ID
from src.core.registry import StaticDataRegistry

# Koszt zdjęcia żetonu (wpływ) i klucz „innych punktów" w stanie celów.
INFLUENCE_COST = 6
SCORE_KEY = "custodians"


def on_board(state: GameState) -> bool:
    """Czy żeton Custodians leży na Mecatol Rex.

    Leży od położenia w setupie aż do zdjęcia. Stany bez setupu (testy, God-Mode, starsze
    migawki) traktujemy jak gotowe — żeton jest na planszy.
    """
    if state.custodians_removed:
        return False
    return state.setup is None or state.setup.custodians_placed


def is_mecatol_position(state: GameState, position: str) -> bool:
    """Czy na pozycji ``position`` leży system Mecatol Rex."""
    system = state.systems.get(position)
    return system is not None and system.system_id == MECATOL_SYSTEM_ID


def mecatol_planets(
    state: GameState, registry: StaticDataRegistry, position: str
) -> list[str]:
    """Planety systemu Mecatol Rex na ``position`` (zwykle jedna: sam Mecatol Rex)."""
    if not is_mecatol_position(state, position):
        return []
    definition = registry.systems.get(MECATOL_SYSTEM_ID)
    return list(definition.planets) if definition is not None else []


def landing_blocked(
    state: GameState, registry: StaticDataRegistry, position: str
) -> set[str]:
    """Planety, na których nie wolno teraz lądować (żeton Custodians stoi na Mecatol Rex)."""
    if not on_board(state):
        return set()
    return set(mecatol_planets(state, registry, position))


def influence_options(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> dict[str, int]:
    """Gotowe planety gracza → ich wpływ (do wyboru płatności za zdjęcie żetonu)."""
    return payment.ready_planet_values(state, registry, player_id, "influence")


def removal_cost(state: GameState, player_id: str) -> int:
    """Koszt zdjęcia żetonu w punktach wpływu (Blood Ties: 0, RULES.md 62.7)."""
    if rules_hooks.permits(rules_hooks.POINT_CUSTODIANS_FREE, state, player_id):
        return 0
    return INFLUENCE_COST


def remove_token(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    planets: list[str],
    trade_goods: int,
) -> GameState:
    """Gracz zdejmuje żeton, płacąc ``INFLUENCE_COST`` wpływu; dostaje 1 VP.

    Nie sprawdza momentu ani sił naziemnych w orbicie — to robi wołający (``core/invasion``).

    Raises:
        ValueError: Żeton już zdjęty, zła/niewystarczająca płatność.
    """
    if not on_board(state):
        raise ValueError("The Custodians token is not on Mecatol Rex.")
    paid = payment.validate_payment(state, registry, player_id, "influence", planets, trade_goods)
    cost = removal_cost(state, player_id)
    if paid < cost:
        raise ValueError(
            f"Removing the Custodians token costs {cost} influence (selected {paid})."
        )
    new_state = state.clone()
    payment.apply_payment(new_state, player_id, planets, trade_goods)
    new_state.custodians_removed = True
    objectives_state = new_state.objectives
    objectives_state.custom_points.setdefault(SCORE_KEY, 1)
    objectives_state.scored.setdefault(SCORE_KEY, []).append(player_id)
    objectives.award_points(
        new_state, player_id, objectives_state.custom_points[SCORE_KEY],
        source=objectives.SOURCE_CUSTODIANS,
    )
    return new_state
