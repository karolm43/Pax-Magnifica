"""God-Mode: fragmenty reliktów w strefie gracza (``board_edit.edit_player``, RULES.md 46)."""

from __future__ import annotations

import pytest

from src.core import board_edit, exploration
from src.core.game_state import GameState, PlayerState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    return GameState(
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2")},
    )


def _edit(state: GameState, registry: StaticDataRegistry, fragments: list[str]) -> GameState:
    return board_edit.edit_player(
        state, HexGrid(), registry, "p1", {"relic_fragments": fragments}
    )


def test_dodany_fragment_znika_z_talii_i_od_innych(registry: StaticDataRegistry) -> None:
    """Dodany fragment trafia do strefy gracza (bez duplikatów) i znika z talii, purge i od p2."""
    state = _state()
    exploration.seed_deck(state, registry, "cultural")
    state.players["p2"].relic_fragments = ["crf2"]
    state.decks.purged = ["hrf1"]
    new = _edit(state, registry, ["crf1", "crf1", "crf2", "hrf1"])
    assert new.players["p1"].relic_fragments == ["crf1", "crf2", "hrf1"]
    assert new.players["p2"].relic_fragments == []
    assert "crf1" not in new.decks.exploration_deck["cultural"]
    assert "hrf1" not in new.decks.purged
    # Niezasiana talia hazardous została zasiana bez fragmentu gracza (zero duplikatu później).
    assert "hrf1" not in new.decks.exploration_deck["hazardous"]
    assert len(new.decks.exploration_deck["hazardous"]) == len(
        exploration.deck_card_ids(registry, "hazardous")
    ) - 1
    # Stan wejściowy nietknięty (clone).
    assert state.players["p1"].relic_fragments == []


def test_zdjety_fragment_wraca_na_spod_talii(registry: StaticDataRegistry) -> None:
    state = _edit(_state(), registry, ["irf1", "irf2"])
    new = _edit(state, registry, ["irf2"])
    assert new.players["p1"].relic_fragments == ["irf2"]
    assert new.decks.exploration_deck["industrial"][-1] == "irf1"
    assert "irf2" not in new.decks.exploration_deck["industrial"]
