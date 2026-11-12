"""Audyt okien czasowych: komponenty dochodzą do gracza w swojej chwili (RULES.md 54.8).

* strażnik statyczny (``src/audit/timing_reach.py``): każdy hook zdarzenia jest emitowany, każda
  karta/notka z ręki ma dostawcę okna, każdy efekt z oknem ma kanał do gracza;
* pierwsza tura fazy akcji ma „początek tury” (hooki + okno kart z ręki);
* faza nie kończy się nad otwartymi decyzjami graczy;
* zdolność obowiązkowa, która zadziałała sama, zostawia ślad w feedzie (``ability_notes``).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.audit import timing_catalog, timing_reach
from src.core import action_cards, reaction_cards, triggers, turn_flow
from src.core.game_events import GameEvent, Moment, event_point
from src.core.game_state import GameState, PendingOffer, Phase, PlayerState
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import Hook, HookKind, HookSource


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(scope="module")
def reach(registry: StaticDataRegistry) -> timing_reach.Reach:
    entries = timing_catalog.collect(registry)
    return timing_reach.analyse(registry, {e.key for e in entries if e.kind in ("timed", "gain")})


# --------------------------------------------------------------------------- strażnik statyczny


def test_kazdy_hook_zdarzenia_jest_emitowany(reach: timing_reach.Reach) -> None:
    assert reach.dead_hooks == []


def test_kazda_karta_z_reki_ma_dostawce_okna(reach: timing_reach.Reach) -> None:
    assert reach.dead_hand == []


def test_kazdy_efekt_z_oknem_ma_kanal_do_gracza(reach: timing_reach.Reach) -> None:
    assert reach.dead_effects == []


def test_audyt_widzi_poczatek_tury_i_jego_dostawce(reach: timing_reach.Reach) -> None:
    assert ("turn", "start") in reach.fired
    assert ("turn", "start") in reach.provided


# ----------------------------------------------------------------- pierwsza tura fazy akcji


def _strategy_done() -> GameState:
    """Pięciu graczy (po jednej karcie), wybór kart zakończony; p3 ma najniższą inicjatywę."""
    seats = ["p1", "p2", "p3", "p4", "p5"]
    cards = {"p1": 4, "p2": 5, "p3": 1, "p4": 2, "p5": 3}
    colors = ["red", "blue", "green", "yellow", "purple"]
    return GameState(
        phase=Phase.STRATEGY,
        active_player_id="p1",
        speaker_id="p1",
        seating_order=seats,
        players={
            pid: PlayerState(player_id=pid, color=color, strategy_cards=[cards[pid]])
            for pid, color in zip(seats, colors, strict=True)
        },
    )


def test_pierwsza_tura_fazy_akcji_emituje_poczatek_tury(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[GameEvent, Moment, str | None]] = []
    original = triggers.fire

    def spy(state: GameState, event: GameEvent, moment: Moment, **kw: Any) -> Any:
        seen.append((event, moment, kw.get("subject")))
        return original(state, event, moment, **kw)

    monkeypatch.setattr(triggers, "fire", spy)  # turn_flow woła ``triggers.fire`` przez moduł
    state = turn_flow.next_phase(_strategy_done())
    assert state.phase is Phase.ACTION and state.active_player_id == "p3"
    assert (GameEvent.TURN, Moment.START, "p3") in seen
    # Początek tury po początku fazy (R_abilities: kolejność zdarzeń).
    assert seen.index((GameEvent.PHASE, Moment.START, None)) < seen.index(
        (GameEvent.TURN, Moment.START, "p3")
    )


def test_pierwsza_tura_otwiera_okno_poczatku_tury_bez_konca_tury() -> None:
    state = turn_flow.next_phase(_strategy_done())
    windows = {(w.event, w.moment, w.subject) for w in reaction_cards.open_windows(state)}
    assert (GameEvent.TURN, Moment.START, "p3") in windows
    assert not any(event is GameEvent.TURN and moment is Moment.END for event, moment, _ in windows)


def test_extreme_duress_zagrywalna_w_pierwszej_turze(registry: StaticDataRegistry) -> None:
    """„At the start of another player's turn” działa też dla pierwszego gracza fazy akcji."""
    base = _strategy_done()
    base.players["p1"].private.action_cards = ["extremeduress"]
    state = turn_flow.next_phase(base)
    rows = action_cards.playability(state, registry, "p1")
    row = next(r for r in rows if r["card_id"] == "extremeduress")
    assert row["reaction"] is True
    assert row["playable"], row["reason"]


# ------------------------------------------------------------- faza nad otwartymi decyzjami


def test_faza_nie_konczy_sie_nad_oczekujaca_oferta() -> None:
    state = turn_flow.next_phase(_strategy_done())
    for player in state.players.values():
        player.passed = True
    assert turn_flow.can_advance_phase(state)
    state.pending_offers = [
        PendingOffer(id="of1", player_id="p2", event="turn", moment="end", hook_seq=0)
    ]
    assert not turn_flow.can_advance_phase(state)
    with pytest.raises(ValueError, match="decisions"):
        turn_flow.next_phase(state)


# ------------------------------------------------------------------- widoczność automatu


def _hook(fn: Any) -> Hook:
    return Hook(
        point=event_point(GameEvent.TURN, Moment.END),
        source=HookSource("technology", "audit_test"),
        kind=HookKind.TRIGGER,
        fn=fn,
        seq=-1,
        covers="technologies:audit_test",
    )


def test_zdolnosc_ktora_zadzialala_sama_trafia_do_feedu() -> None:
    state = _strategy_done()

    def gain(s: GameState, pid: str, _ctx: Any) -> None:
        s.players[pid].trade_goods += 1

    triggers._run_visible(state, "p2", _hook(gain), {})
    assert state.ability_notes[-1]["component"] == "technologies:audit_test"
    assert state.ability_notes[-1]["player"] == "p2"


def test_zdolnosc_bez_skutku_nie_zostawia_sladu() -> None:
    state = _strategy_done()
    triggers._run_visible(state, "p2", _hook(lambda s, p, c: None), {})
    assert state.ability_notes == []
