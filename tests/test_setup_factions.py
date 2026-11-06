"""Testy doboru frakcji w setupie (``resolve_players`` / ``_resolve_factions``).

Pokrywają regułę „max 1 wariant z rodziny frakcji": Keleres to jedna frakcja
z trzema wariantami mentora (keleresm/keleresx/keleresa), więc w jednej grze może
wystąpić najwyżej jeden — zarówno przy losowaniu, jak i przy jawnym wyborze
(RULES.md 10, docs/rules_tirules/F_keleres.md).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import pytest

from src.core.registry import StaticDataRegistry
from src.core.setup_service import resolve_players

_KELERES_VARIANTS = frozenset({"keleresm", "keleresx", "keleresa"})
# Kolory i trudności wystarczające na pełny stół — dobór frakcji nas interesuje,
# nie walidacja kolorów/trudności (te mają własne testy).
_COLORS = ("red", "blue", "green", "yellow", "purple", "orange", "pink", "black")


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@dataclass
class _Player:
    """Minimalny gracz spełniający strukturalnie ``PlayerSetupInput``."""

    faction_id: str | None = None
    player_id: str | None = None
    name: str | None = None
    color: str | None = None
    control_type: str = "HUMAN"
    difficulty: str | None = None
    personality: str | None = None
    home_position: str | None = None
    starting_tech: list[str] | None = None


def _resolve(
    registry: StaticDataRegistry,
    players: list[_Player],
    *,
    seed: int,
) -> list[str]:
    resolved = resolve_players(
        players,
        registry,
        available_colors=_COLORS,
        max_players=len(_COLORS),
        valid_difficulties=registry.valid_difficulties(),
        valid_personalities=registry.valid_personalities(),
        rng=random.Random(seed),
    )
    return [player.faction_id for player in resolved]


def test_random_assignment_never_picks_two_keleres_variants(
    registry: StaticDataRegistry,
) -> None:
    """Pełny stół samych losowań: żaden seed nie daje dwóch wariantów Keleres."""
    players = [_Player() for _ in range(len(_COLORS))]
    for seed in range(200):
        factions = _resolve(registry, players, seed=seed)
        keleres = [fid for fid in factions if fid in _KELERES_VARIANTS]
        assert len(keleres) <= 1, (
            f"seed={seed}: wylosowano wiele wariantów Keleres: {keleres}"
        )
        # Sanity: brak jakichkolwiek duplikatów id przy losowaniu.
        assert len(factions) == len(set(factions))


def test_random_fills_around_explicit_keleres(
    registry: StaticDataRegistry,
) -> None:
    """Jawny Keleres u jednego gracza blokuje wylosowanie innego wariantu Keleres."""
    players = [_Player(faction_id="keleresm")] + [_Player() for _ in range(5)]
    for seed in range(200):
        factions = _resolve(registry, players, seed=seed)
        assert factions[0] == "keleresm"
        keleres = [fid for fid in factions if fid in _KELERES_VARIANTS]
        assert keleres == ["keleresm"], (
            f"seed={seed}: oprócz jawnego keleresm pojawił się inny wariant: {keleres}"
        )


def test_two_explicit_keleres_variants_rejected(
    registry: StaticDataRegistry,
) -> None:
    """Dwaj gracze z różnymi wariantami Keleres → ValueError (jedna rodzina)."""
    players = [
        _Player(faction_id="keleresm", player_id="a"),
        _Player(faction_id="keleresx", player_id="b"),
    ]
    with pytest.raises(ValueError, match="faction family"):
        _resolve(registry, players, seed=0)


def test_duplicate_same_faction_id_still_rejected(
    registry: StaticDataRegistry,
) -> None:
    """Niezmieniony kontrakt: dwa razy ten sam id frakcji → ValueError (R8.8)."""
    players = [
        _Player(faction_id="sol", player_id="a"),
        _Player(faction_id="sol", player_id="b"),
    ]
    with pytest.raises(ValueError, match="Duplicate faction"):
        _resolve(registry, players, seed=0)
