"""Deklaracje pasu, „tylko gdy dotyczy mnie”, wyciszenia i „Quick windows” (RULES.md 54.12)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import (
    activity,
    card_hold,
    command_tokens,
    reaction_pause,
    reaction_prefs,
    reaction_window,
    rules_hooks,
    triggers,
    visibility,
)
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from tests.factions.test_muaat import _magmus_state, _offers
from tests.test_card_hold import NOW, _industrial, _own, _play, _state
from tests.test_reactions_agenda import DIRECTIVE, LAW, _revealed


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _agenda_with_rider(registry: StaticDataRegistry) -> GameState:
    """Ujawniona agenda (okno jeszcze bez pauzy): p1 ma ridera, p3 drugiego ridera."""
    return _revealed(registry, [LAW, DIRECTIVE], {"p1": ["lead_rider"], "p3": ["imp_rider"]})


def _sabotage_window(registry: StaticDataRegistry, **prefs: object) -> GameState:
    """p1 zagrywa Industrial Initiative; p2 i p3 mają Sabotage. ``prefs`` dla p2 przed zagraniem."""
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    state.players["p3"].private.action_cards = ["sabo2"]
    if prefs:
        state = reaction_prefs.update(state, "p2", **prefs)  # type: ignore[arg-type]
    return _play(state, registry, card)


# --- deklaracje pasu ---------------------------------------------------------------------------


def test_deklaracja_pasu_na_agende_pasuje_mimo_karty(registry: StaticDataRegistry) -> None:
    state = reaction_prefs.update(_agenda_with_rider(registry), "p1", declare={"agenda": "agenda"})
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    assert state.reaction_pause.passed == ["p1"]  # p3 nadal pytany (ma ridera)


def test_deklaracja_na_agende_wygasa_przy_kolejnej_agendzie(registry: StaticDataRegistry) -> None:
    state = reaction_prefs.update(_agenda_with_rider(registry), "p1", declare={"agenda": "agenda"})
    assert reaction_prefs.declares_pass(state, "p1", "agenda")
    assert state.agenda is not None
    state.agenda.agenda_number += 1
    assert not reaction_prefs.declares_pass(state, "p1", "agenda")
    reaction_prefs.prune(state)
    assert state.players["p1"].private.reaction_prefs.passes == {}


def test_deklaracja_do_konca_tury_wygasa_ze_zmiana_aktywnego(registry: StaticDataRegistry) -> None:
    card, _ = _industrial(registry)
    state = reaction_prefs.update(_state([card], ["sabo1"]), "p2", declare={"all": "turn"})
    assert reaction_prefs.declares_pass(state, "p2", "sabotage")
    state.active_player_id = "p3"
    reaction_prefs.prune(state)
    assert not reaction_prefs.declares_pass(state, "p2", "sabotage")


def test_deklaracja_do_konca_rundy(registry: StaticDataRegistry) -> None:
    card, _ = _industrial(registry)
    state = reaction_prefs.update(_state([card], ["sabo1"]), "p2", declare={"combat": "round"})
    state.active_player_id = "p3"
    assert reaction_prefs.declares_pass(state, "p2", "combat")
    assert not reaction_prefs.declares_pass(state, "p2", "agenda")  # inna kategoria
    state.round_number += 1
    assert not reaction_prefs.declares_pass(state, "p2", "combat")


def test_deklaracja_sabotage_pasuje_w_oknie_karty(registry: StaticDataRegistry) -> None:
    held = _sabotage_window(registry, declare={"sabotage": "always"})
    assert held.held_play is not None and held.held_play.passed == ["p2"]


def test_skip_all_always_to_pole_auto_pass(registry: StaticDataRegistry) -> None:
    card, _ = _industrial(registry)
    state = reaction_prefs.update(_state([card], ["sabo1"]), "p2", declare={"all": "always"})
    assert state.players["p2"].private.auto_pass_reactions
    off = reaction_prefs.update(state, "p2", declare={"all": None})
    assert not off.players["p2"].private.auto_pass_reactions


def test_nieznana_kategoria_i_czas(registry: StaticDataRegistry) -> None:
    card, _ = _industrial(registry)
    state = _state([card], ["sabo1"])
    with pytest.raises(ValueError, match="category"):
        reaction_prefs.update(state, "p2", declare={"xyz": "turn"})
    with pytest.raises(ValueError, match="duration"):
        reaction_prefs.update(state, "p2", declare={"all": "forever"})


def test_deklaracja_w_trakcie_okna_pasuje_od_razu(registry: StaticDataRegistry) -> None:
    held = _sabotage_window(registry)
    assert held.held_play is not None and held.held_play.passed == []
    after = reaction_prefs.update(held, "p2", declare={"sabotage": "turn"})
    reaction_window.pass_open_windows(after, "p2")
    assert after.held_play is not None and after.held_play.passed == ["p2"]


# --- „only when it concerns me” i wyciszenia --------------------------------------------------


def test_tylko_gdy_dotyczy_mnie_pasuje_w_cudzej_sprawie(registry: StaticDataRegistry) -> None:
    held = _sabotage_window(registry, only_involved=True)
    assert held.held_play is not None
    assert "p2" not in held.held_play.involved
    assert held.held_play.passed == ["p2"]


def test_okno_dotyczy_gracza_z_jednostkami_w_systemie(registry: StaticDataRegistry) -> None:
    card, _ = _industrial(registry)
    state = _state([card], ["sabo1"])
    state.systems["101"].space_units = {"p2": {"destroyer": 1}}
    assert reaction_prefs.involved_players(
        state, ["p2", "p3"], subject="p1", ctx={"position": "101"}, category="combat"
    ) == ["p2"]
    assert reaction_prefs.involved_players(
        state, ["p2", "p3"], subject="p1", ctx={"target": "p3"}, category="combat"
    ) == ["p3"]
    assert reaction_prefs.involved_players(
        state, ["p2", "p3"], subject="p1", ctx={}, category="agenda"
    ) == ["p2", "p3"]


def test_wyciszona_karta_nie_liczy_sie_jako_karta(registry: StaticDataRegistry) -> None:
    held = _sabotage_window(registry, mute_cards={"Sabotage": True})
    assert held.held_play is not None and held.held_play.passed == ["p2"]
    unmuted = reaction_prefs.update(held, "p2", mute_cards={"Sabotage": False})
    assert unmuted.players["p2"].private.reaction_prefs.muted_cards == []


def test_wyciszona_oferta_nie_powstaje(registry: StaticDataRegistry) -> None:
    state = _magmus_state()
    command_tokens.spend_strategy_token(state, "p1")
    offer = _offers(state, "p1", "Magmus")[0]
    hook = rules_hooks.hook_by_seq(offer.hook_seq)
    assert hook is not None and hook.covers
    muted = reaction_prefs.update(_magmus_state(), "p1", mute_offers={hook.covers: True})
    command_tokens.spend_strategy_token(muted, "p1")
    assert _offers(muted, "p1", "Magmus") == []
    assert triggers.offers_for(muted, "p1") == []


def test_preferencje_sa_prywatne(registry: StaticDataRegistry) -> None:
    card, _ = _industrial(registry)
    state = reaction_prefs.update(
        _state([card], ["sabo1"]), "p2", declare={"sabotage": "always"}, only_involved=True
    )
    seen_by_p1 = visibility.project_for_viewer(state, "p1")
    assert seen_by_p1.players["p2"].private.reaction_prefs.passes == {}
    assert not seen_by_p1.players["p2"].private.reaction_prefs.only_involved
    seen_by_p2 = visibility.project_for_viewer(state, "p2")
    assert "sabotage" in seen_by_p2.players["p2"].private.reaction_prefs.passes


# --- „Quick windows” ---------------------------------------------------------------------------


def test_quick_bez_reakcji_pauza_sie_nie_otwiera(registry: StaticDataRegistry) -> None:
    def revealed() -> GameState:
        hands = {"p1": ["lead_rider"], "p3": ["salvage"]}
        state = _revealed(registry, [LAW, DIRECTIVE], hands)
        return reaction_prefs.update(state, "p1", declare={"agenda": "agenda"})

    quick = revealed()
    quick.quick_reaction_windows = True
    reaction_pause.sync(quick, registry, now=100.0)
    assert quick.reaction_pause is None  # wszyscy pasują od razu
    slow = revealed()
    reaction_pause.sync(slow, registry, now=100.0)
    assert slow.reaction_pause is not None  # bez „Quick windows” okno trwa stały czas (54.11)


def test_quick_pauza_konczy_sie_po_ostatnim_pasie(registry: StaticDataRegistry) -> None:
    state = _agenda_with_rider(registry)
    state.quick_reaction_windows = True
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    state = reaction_pause.pass_pause(state, "p1")
    assert state.reaction_pause is not None
    assert reaction_pause.pass_pause(state, "p3").reaction_pause is None


def test_quick_karta_rozstrzyga_sie_po_pasach(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    state.quick_reaction_windows = True
    held = _play(state, registry, card)
    assert held.held_play is not None and held.held_play.eligible == ["p2"]
    done = card_hold.pass_hold(held, registry, "p2")
    assert done.held_play is None
    assert card in done.decks.action_card_discard


def test_quick_karta_bez_sabotage_u_innych_od_razu(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["salvage"])
    _own(state, planets)
    state.quick_reaction_windows = True
    assert _play(state, registry, card).held_play is None


# --- API ---------------------------------------------------------------------------------------


def test_api_prefs_i_quick(registry: StaticDataRegistry) -> None:
    from src.api.web_game import _reaction_prefs

    card, _ = _industrial(registry)
    app = create_app(store=EventStore(), initial_state=_state([card], ["sabo1"]), now=lambda: NOW)
    client, service = TestClient(app), app.state.service
    body = {"actor_id": "p2", "declare": {"agenda": "round"}, "only_involved": True,
            "mute_cards": {"Sabotage": True}}
    response = client.post("/reaction-settings/prefs", json=body)
    assert response.status_code == 200, response.text
    current = service.current_state()
    assert _reaction_prefs(current, current.players["p2"], registry) == {
        "passes": {"agenda": "round"}, "onlyInvolved": True,
        "mutedCards": ["Sabotage"], "mutedOffers": [],
    }
    bad = {"actor_id": "p2", "declare": {"x": "turn"}}
    assert client.post("/reaction-settings/prefs", json=bad).status_code == 422
    quick = client.post("/reaction-settings/quick", json={"enabled": True})
    assert quick.status_code == 200, quick.text
    assert service.current_state().quick_reaction_windows is True
    assert activity.derive_activity("reaction-settings:prefs", current, current) is None
    entry = activity.derive_activity("reaction-settings:quick:1", current, current)
    assert entry is not None and entry.action == "reactions.quick" and entry.subject == "on"


# --- „No whens” / „No afters” (połowiczne deklaracje agendy, 54.12) ---------------------------


def _pause_passed(state: GameState, registry: StaticDataRegistry) -> list[str]:
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    return state.reaction_pause.passed


def test_no_afters_pasuje_gracza_z_samym_riderem(registry: StaticDataRegistry) -> None:
    state = reaction_prefs.update(
        _agenda_with_rider(registry), "p1", declare={"agenda_after": "agenda"}
    )
    assert _pause_passed(state, registry) == ["p1"]


def test_no_whens_nie_pasuje_gracza_z_riderem(registry: StaticDataRegistry) -> None:
    state = reaction_prefs.update(
        _agenda_with_rider(registry), "p1", declare={"agenda_when": "agenda"}
    )
    assert _pause_passed(state, registry) == []


def test_no_whens_pasuje_gracza_z_samym_veto(registry: StaticDataRegistry) -> None:
    base = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["veto"], "p3": ["imp_rider"]})
    whens = reaction_prefs.update(base, "p1", declare={"agenda_when": "agenda"})
    assert _pause_passed(whens, registry) == ["p1"]
    afters = reaction_prefs.update(base, "p1", declare={"agenda_after": "agenda"})
    assert _pause_passed(afters, registry) == []


def test_obie_polowy_to_pas_na_cala_agende(registry: StaticDataRegistry) -> None:
    state = reaction_prefs.update(
        _agenda_with_rider(registry), "p1",
        declare={"agenda_when": "agenda", "agenda_after": "agenda"},
    )
    assert reaction_prefs.declares_pass(state, "p1", "agenda")
    assert not reaction_prefs.declares_pass(state, "p1", "combat")
    assert state.agenda is not None
    state.agenda.agenda_number += 1  # kolejna agenda - deklaracje wygasły
    assert not reaction_prefs.declares_pass(state, "p1", "agenda")


def test_no_afters_w_trakcie_okna_pasuje_od_razu(registry: StaticDataRegistry) -> None:
    state = _agenda_with_rider(registry)
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None and state.reaction_pause.passed == []
    after = reaction_prefs.update(state, "p1", declare={"agenda_after": "agenda"})
    reaction_window.pass_open_windows(after, "p1")  # bez rejestru: połowa nie wystarcza
    assert after.reaction_pause is not None and after.reaction_pause.passed == []
    reaction_window.pass_open_windows(after, "p1", registry)
    assert after.reaction_pause.passed == ["p1"]
