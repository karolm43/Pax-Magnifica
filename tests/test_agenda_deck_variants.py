"""Fanowskie warianty talii agend (Absol) wybierane w Ustawieniach."""

from __future__ import annotations

import pytest

from src.core.card_draw import ensure_agenda_deck
from src.core.components import ComponentCategory
from src.core.game_state import GameState
from src.core.objectives import agenda_deck_ids, deck_card_ids
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def test_standard_deck_unchanged_by_fan_decks(registry: StaticDataRegistry) -> None:
    assert len(agenda_deck_ids(registry, "standard")) == 50
    assert agenda_deck_ids(registry) == deck_card_ids(registry, "agenda")


@pytest.mark.parametrize(("variant", "size"), [("absol", 60)])
def test_fan_deck_cards_exist_in_catalog(
    registry: StaticDataRegistry, variant: str, size: int
) -> None:
    ids = agenda_deck_ids(registry, variant)
    assert len(ids) == size and len(set(ids)) == size
    for card_id in ids:
        assert registry.catalog.get(ComponentCategory.AGENDA, card_id) is not None


def test_fan_sources_load_only_agendas_and_agenda_decks(registry: StaticDataRegistry) -> None:
    action_cards = registry.catalog.all(ComponentCategory.ACTION_CARD)
    assert not [c for c in action_cards.values() if c.source in ("absol",)]
    decks = registry.catalog.all(ComponentCategory.DECK)
    fan = [d for d in decks.values() if d.source in ("absol",)]
    assert fan and all(d.id.startswith("agendas_") for d in fan)


def test_unknown_variant_rejected(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError):
        agenda_deck_ids(registry, "nope")


@pytest.mark.parametrize("variant", ["standard", "absol"])
def test_ensure_agenda_deck_uses_selected_variant(
    registry: StaticDataRegistry, variant: str
) -> None:
    state = GameState()
    state.decks.agenda_variant = variant
    ensure_agenda_deck(state, registry)
    assert sorted(state.decks.agenda_deck) == sorted(agenda_deck_ids(registry, variant))




def test_card_pool_exposes_agenda_variant(registry: StaticDataRegistry) -> None:
    from src.api.web_objectives import card_pool_counts

    state = GameState()
    assert card_pool_counts(state, registry)["agendaVariant"] == "standard"
    state.decks.agenda_variant = "absol"
    assert card_pool_counts(state, registry)["agendaVariant"] == "absol"


def test_absol_laws_reach_laws_in_play_and_player_area() -> None:
    """FAN-AGENDAS (Absol): prawa Absol (Elect Player i For/Against) trafiają do web-data."""
    from fastapi.testclient import TestClient

    from src.api.app import create_app
    from src.core import agenda_phase
    from src.core.game_state import AgendaPhaseState, Phase

    app = create_app()
    client = TestClient(app)
    created = client.post(
        "/game/new",
        json={
            "players": [{"faction_id": "sol"}, {"faction_id": "hacan"}, {"faction_id": "xxcha"}],
            "agenda_deck": "absol",
        },
    )
    assert created.status_code == 200
    ctx = app.state.ctx
    state = ctx.service.current_state().clone()
    assert state.decks.agenda_variant == "absol"
    state.phase = Phase.AGENDA
    state.agenda = AgendaPhaseState()
    state.custodians_removed = True
    state.decks.agenda_deck = ["absol_minscomm", "absol_regulations"]
    state.decks.agenda_deck_seeded = True
    speaker = state.speaker_id
    assert speaker is not None
    elected = state.seating_order[1]
    for outcome in (elected, "for"):
        state = agenda_phase.reveal_agenda(state, ctx.registry, speaker)
        assert state.agenda is not None
        for pid in list(state.agenda.vote_order):
            state = agenda_phase.abstain(state, ctx.registry, pid)
        state = agenda_phase.decide_tie(state, ctx.registry, speaker, outcome)
        state = agenda_phase.continue_agenda(state, ctx.registry, speaker)
    ctx.service.replace_state(state, label="test")

    data = client.get("/api/public/game/test/web-data").json()
    assert [law["id"] for law in data["lawsInPlay"]] == ["absol_minscomm", "absol_regulations"]
    owners = {p["faction"]: p["lawsOwned"] for p in data["playerData"]}
    assert owners[state.players[elected].faction] == ["absol_minscomm"]
