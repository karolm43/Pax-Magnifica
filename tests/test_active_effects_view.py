"""Panel efektów przy planszy: czytelne nazwy/teksty, bez surowych kluczy i znaczników silnika."""

from __future__ import annotations

import pytest

from src.core import active_effects, component_text, initiative_zero
from src.core.game_events import Duration
from src.core.game_state import GameState, PlayerState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    return GameState(
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="naalu"),
            "p2": PlayerState(player_id="p2", color="blue", faction="sol"),
        }
    )


def test_zeton_zero_naalu_ma_czytelna_nazwe_i_opis(registry: StaticDataRegistry) -> None:
    state = _state()
    initiative_zero.place(state, "p1")
    (row,) = component_text.active_effects_view(state, registry)
    assert row["name"] == '"0" Token' and row["kind"] == "Naalu token"
    assert "initiative number is 0" in row["text"]
    assert row["until"] == "this game round" and row["owner"] == "p1"


def test_znaczniki_silnika_nie_trafiaja_na_tace(registry: StaticDataRegistry) -> None:
    state = _state()
    for key in (
        "research:enigmatic_device",
        "action_cards:dp_give",
        "production:commander_trade_good",
    ):
        active_effects.add_effect(state, key, Duration.TURN, owner="p1")
    assert component_text.active_effects_view(state, registry) == []


def test_kopie_kart_i_notki_z_kolorem_maja_nazwy(registry: StaticDataRegistry) -> None:
    state = _state()
    for key in (
        "action_cards:war_machine",
        "promissory_notes:ceasefire",
        "promissory_notes:political_secret",
        "promissory_notes:tekklar:penalty",
        "technology:research_discount",
    ):
        active_effects.add_effect(state, key, Duration.TURN, owner="p1", data={"amount": 2})
    rows = component_text.active_effects_view(state, registry)
    assert [r["name"] for r in rows] == [
        "War Machine", "Ceasefire", "Political Secret", "Tekklar Legion", "Research discount",
    ]
    assert all(r["text"] and r["kind"] for r in rows)
    assert rows[-1]["detail"] == "next research costs 2 less"
