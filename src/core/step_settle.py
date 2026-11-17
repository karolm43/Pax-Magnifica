"""Rozliczenie po każdym kroku gry — reguły stosowane do WYNIKU dowolnej akcji. Czyste.

Wcześniej ta sekwencja leżała w ``api/state_service.replace_state``. Przeniesiona do ``core/``,
żeby bot (``src/engine``) symulował dokładnie to, co dzieje się po commicie na serwerze
(RULES.md 65.1): koniec gry po progu VP z dowolnego źródła, Wormhole Nexus, limity
pojemności/puli floty (RULES.md 42), odblokowania liderów (61.1), pauza ochronna (54.10)
i zegar szachowy (58).
"""

from __future__ import annotations

from src.core import battle, game_clock, game_end, leaders, limits, nexus, reaction_pause
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

# Etykiety kroków, po których NIE wymuszamy limitów: God-Mode (celowo omija walidację),
# ręczna edycja planszy, zegar, setup i techniczne nadpisania stanu.
LIMITS_EXEMPT_LABELS = (
    "god-mode",
    "initial",
    "replace",
    "player-undo",  # Undo gracza przywraca migawkę, która już przeszła te kontrole
    "setup:",
    "clock:",
    "space:",
    "planet:",
    "edit:",
    "move-units",
    "cc:",
    "capture:",
)


def settle_step(
    state: GameState, registry: StaticDataRegistry, now: float, label: str
) -> GameState:
    """Zwraca stan po regułach „po każdym kroku” (wejście nie jest mutowane).

    ``label`` = etykieta kroku (jak w historii); etykiety z ``LIMITS_EXEMPT_LABELS`` pomijają
    limity, liderów i pauzę reakcji. ``now`` = zegar serwera (wstrzykiwany, nigdy ``time``).
    """
    # Wormhole Nexus odwraca się na stronę aktywną, gdy pojawi się w nim jednostka/kontrola.
    after = game_end.apply_victory(nexus.activate_nexus(state.clone()))
    if not label.startswith(LIMITS_EXEMPT_LABELS):
        # Nadwyżka po DOWOLNYM efekcie otwiera okno usunięcia (RULES.md 42).
        after = limits.enforce_limits(after, registry)
        leaders.refresh_unlocks(after, registry)
        reaction_pause.sync(after, registry, now)
        # Walka wstrzymana po Sustain Damage rusza, gdy nie ma pauzy (RULES.md 54.10); dalszy
        # przebieg (koniec walki, Salvage) może otworzyć kolejną pauzę i zmienić limity.
        resumed = battle.release_sustain_hold(after, registry)
        if resumed is not after:
            after = limits.enforce_limits(resumed, registry)
            leaders.refresh_unlocks(after, registry)
            reaction_pause.sync(after, registry, now)
    return game_clock.settle(after, now)
