"""Okna reakcji o stałej długości + auto-pas silnika (RULES.md 54.11).

Wspólna mechanika pauzy ochronnej (54.10) i okna Sabotage (53.6): długość ustawia host, silnik
pasuje za graczy bez pasującej karty, za botów i za „Skip all reactions”, pasy są prywatne,
„More time” przedłuża okno raz na gracza. Kluczowy test w parach (43.4): z zewnątrz okno wygląda
identycznie, niezależnie od tego, czy ktoś ma kartę.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import activity, card_hold, reaction_pause, reaction_window, visibility
from src.core.event_store import EventStore
from src.core.game_state import ControlType, GameState
from src.core.registry import StaticDataRegistry
from tests.test_card_hold import NOW, _industrial, _own, _play, _state
from tests.test_reactions_agenda import DIRECTIVE, LAW, _revealed


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _agenda(registry: StaticDataRegistry, p3_hand: list[str]) -> GameState:
    """Ujawniona agenda: p1 ma ridera (może zareagować), p3 rękę z parametru."""
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["lead_rider"], "p3": p3_hand})
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    return state


# --- auto-pas ----------------------------------------------------------------------------------


def test_silnik_pasuje_tylko_za_graczy_bez_pasujacej_karty(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, ["salvage"])
    assert state.reaction_pause is not None
    assert state.reaction_pause.eligible == ["p1", "p3"]
    assert state.reaction_pause.passed == ["p3"]  # Salvage nie pasuje do ujawnionej agendy


def test_bot_i_skip_all_pasuja_mimo_karty(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["lead_rider"], "p3": ["imp_rider"]})
    state.players["p1"].control_type = ControlType.BOT
    state.players["p3"].private.auto_pass_reactions = True
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    assert state.reaction_pause.passed == ["p1", "p3"]


def test_wlaczenie_skip_all_w_trakcie_okna_pasuje_od_razu(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, ["salvage"])
    on = reaction_window.set_auto_pass(state, "p1", True)
    assert on.players["p1"].private.auto_pass_reactions
    assert on.reaction_pause is not None and on.reaction_pause.passed == ["p3", "p1"]
    off = reaction_window.set_auto_pass(on, "p1", False)
    assert not off.players["p1"].private.auto_pass_reactions
    assert off.reaction_pause is not None and "p1" in off.reaction_pause.passed  # pas zostaje
    with pytest.raises(ValueError, match="Unknown"):
        reaction_window.set_auto_pass(state, "zz", True)


def test_okno_sabotage_auto_pas_i_skip_all(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    state.players["p3"].private.action_cards = ["sabo2"]
    state.players["p3"].private.auto_pass_reactions = True
    held = _play(state, registry, card)
    assert held.held_play is not None
    assert held.held_play.eligible == ["p2", "p3"]
    assert held.held_play.passed == ["p3"]  # ma Sabotage, ale wybrał „Skip all reactions”


# --- stała długość i „More time” ---------------------------------------------------------------


def test_host_ustawia_dlugosc_w_zakresie(registry: StaticDataRegistry) -> None:
    state = reaction_window.configure(GameState(), 7)
    assert state.reaction_window_seconds == 7
    for bad in (1, reaction_window.MAX_SECONDS + 1):
        with pytest.raises(ValueError, match="between"):
            reaction_window.configure(state, bad)


def test_more_time_raz_na_gracza_takze_po_auto_pasie(registry: StaticDataRegistry) -> None:
    """Prośbę o czas może złożyć każdy uprawniony (p3 spasowany przez silnik) - blef dozwolony."""
    state = _agenda(registry, ["salvage"])
    longer = reaction_pause.ask_for_time(state, "p3")
    assert longer.reaction_pause is not None
    assert longer.reaction_pause.seconds == reaction_window.DEFAULT_SECONDS + 10
    with pytest.raises(ValueError, match="already asked"):
        reaction_pause.ask_for_time(longer, "p3")
    with pytest.raises(ValueError, match="not asked"):
        reaction_pause.ask_for_time(longer, "p2")
    with pytest.raises(ValueError, match="still open"):
        reaction_pause.release(longer, now=100.0 + reaction_window.DEFAULT_SECONDS)
    assert reaction_pause.release(
        longer, now=100.0 + reaction_window.DEFAULT_SECONDS + 10
    ).reaction_pause is None


def test_more_time_w_oknie_sabotage(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    held = card_hold.ask_for_time(_play(state, registry, card), "p2")
    assert held.held_play is not None and held.held_play.extended_by == ["p2"]
    with pytest.raises(ValueError, match="still open"):
        card_hold.release(held, registry, "p1", now=NOW + reaction_window.DEFAULT_SECONDS)
    later = NOW + reaction_window.DEFAULT_SECONDS + 10
    assert card_hold.release(held, registry, "p1", now=later).held_play is None


# --- nic nie wycieka (43.4) --------------------------------------------------------------------


def test_z_zewnatrz_okno_wyglada_tak_samo_z_karta_i_bez(registry: StaticDataRegistry) -> None:
    """Test w parach: p3 z ridrem i bez niego - p2 widzi identyczną pauzę (długość, pasy)."""
    without = _agenda(registry, ["salvage"])
    with_card = _agenda(registry, ["imp_rider"])
    assert without.reaction_pause is not None and with_card.reaction_pause is not None
    assert without.reaction_pause.passed != with_card.reaction_pause.passed  # silnik wie
    seen = [
        visibility.project_strict(s, "p2").reaction_pause for s in (without, with_card)
    ]
    assert seen[0] == seen[1]
    assert seen[0] is not None and seen[0].passed == []
    assert seen[0].seconds == reaction_window.DEFAULT_SECONDS


def test_projekcja_zostawia_tylko_wlasny_pas_i_liczbe_prosb(registry: StaticDataRegistry) -> None:
    state = reaction_pause.ask_for_time(_agenda(registry, ["salvage"]), "p1")
    mine = visibility.project_strict(state, "p3").reaction_pause
    other = visibility.project_strict(state, "p1").reaction_pause
    assert mine is not None and mine.passed == ["p3"] and mine.extended_by == [""]
    assert other is not None and other.passed == [] and other.extended_by == ["p1"]


# --- API, middleware, feed ---------------------------------------------------------------------


def _client(state: GameState, clock: list[float]) -> tuple[TestClient, object]:
    app = create_app(store=EventStore(), initial_state=state, now=lambda: clock[0])
    return TestClient(app), app.state.service


def test_api_okno_sabotage_zwalnia_sie_przy_kolejnym_post(registry: StaticDataRegistry) -> None:
    """Po upływie czasu dowolny POST wykonuje kartę (gra nie zależy od odliczania w UI)."""
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    clock = [NOW]
    client, service = _client(state, clock)
    body = {"actor_id": "p1", "player_id": "p1", "card_id": card}
    assert client.post("/action-card/play", json=body).json()["held"] is True
    assert client.post("/action-card/held/wait", json={"actor_id": "p2"}).status_code == 200
    clock[0] = NOW + reaction_window.DEFAULT_SECONDS + 1
    assert client.post("/turn/end", json={"player_id": "p1"}).status_code == 422  # +10 s trwa
    clock[0] = NOW + reaction_window.DEFAULT_SECONDS + reaction_window.WAIT_EXTENSION_SECONDS + 1
    client.post("/turn/end", json={"player_id": "p1"})
    current = service.current_state()  # type: ignore[attr-defined]
    assert current.held_play is None and current.players["p1"].trade_goods == 3


def test_api_ustawienia_i_feed(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, ["salvage"])
    clock = [100.0]
    client, service = _client(state, clock)
    resp = client.post("/reaction-settings/window", json={"seconds": 6})
    assert resp.status_code == 200, resp.text
    assert service.current_state().reaction_window_seconds == 6  # type: ignore[attr-defined]
    assert client.post("/reaction-settings/window", json={"seconds": 99}).status_code == 422
    resp = client.post("/reaction-settings/auto-pass", json={"actor_id": "p1", "enabled": True})
    assert resp.status_code == 200, resp.text
    assert service.current_state().players["p1"].private.auto_pass_reactions  # type: ignore[attr-defined]
    assert client.post("/reaction-pause/wait", json={"actor_id": "p3"}).status_code == 200
    window = activity.derive_activity("reaction-settings:window:6", state, state)
    assert window is not None and window.action == "reactions.window" and window.subject == "6"
    wait = activity.derive_activity("reaction-wait", state, state)
    assert wait is not None and wait.action == "reactions.wait" and wait.actor_id is None
    assert activity.derive_activity("reaction-settings:auto-pass", state, state) is None


def test_web_data_pasy_tylko_patrzacego(registry: StaticDataRegistry) -> None:
    from src.api.web_game import _reaction_pause

    state = reaction_pause.ask_for_time(_agenda(registry, ["salvage"]), "p1")
    payload = _reaction_pause(visibility.project_strict(state, "p3"))
    assert payload is not None
    assert payload["passed"] == ["p3"] and payload["askedForTime"] == []
    assert payload["extensions"] == 1
    assert payload["pauseSeconds"] == reaction_window.DEFAULT_SECONDS + 10


def test_nowa_gra_z_dlugoscia_okna(registry: StaticDataRegistry) -> None:
    client = TestClient(create_app(registry=registry, store=EventStore(":memory:")))
    resp = client.post(
        "/game/new",
        json={
            "players": [{"faction_id": "hacan"}, {"faction_id": "sol"}],
            "reaction_window_seconds": 5,
        },
    )
    assert resp.status_code == 200, resp.text
    assert client.get("/state").json()["state"]["reaction_window_seconds"] == 5
