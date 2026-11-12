"""Testy silnika zdarzeń: fire, kolejność, oferty, REPLACE, efekty trwałe i podpięcie do reguł."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from src.core import (
    active_effects,
    agenda_phase,
    battle,
    card_draw,
    control,
    economy,
    rules_hooks,
    strategy_phase,
    technology,
    triggers,
    turn_flow,
    unit_ops,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    CombatStep,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TimingWindow,
    WindowType,
)
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import HookKind, HookSource
from src.core.unit_ops import UnitCause

LAW = HookSource(rules_hooks.SOURCE_AGENDA, "spy_law")  # prawo obowiązuje KAŻDEGO gracza


def _state(**kwargs: Any) -> GameState:
    players = {
        "p1": PlayerState(player_id="p1", color="red", faction="sol"),
        "p2": PlayerState(player_id="p2", color="blue", faction="arborec"),
        "p3": PlayerState(player_id="p3", color="green", faction="hacan"),
    }
    state = GameState(players=players, seating_order=["p1", "p2", "p3"], **kwargs)
    state.decks.agenda_laws["spy_law"] = "for"
    return state


def _spy(
    log: list[tuple[str, str, str | None]], event: GameEvent, moment: Moment, **kwargs: Any
) -> None:
    """Hook-szpieg na prawie: loguje (zdarzenie, moment, podmiot) RAZ na emisję."""

    def fn(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
        if pid == sorted(state.players)[0]:
            log.append((ctx["event"], ctx["moment"], ctx.get("subject")))

    rules_hooks.on_event(event, moment, LAW, **kwargs)(fn)


# ------------------------------------------------------------------------------ fire: podstawy


def test_fire_bez_hookow_nic_nie_zmienia() -> None:
    state = _state()
    before = state.model_dump_json()
    result = triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1")
    assert (result.replaced, result.ran, result.offers) == (False, [], [])
    assert state.model_dump_json() == before


def test_hook_dziala_tylko_dla_posiadacza_zrodla() -> None:
    state = _state()
    seen: list[str] = []
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(
            GameEvent.TURN, Moment.START, HookSource(rules_hooks.SOURCE_FACTION, "arborec")
        )(lambda _s, pid, _c: seen.append(pid))
        triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1")
    assert seen == ["p2"]


def test_where_i_condition_filtruja_zdarzenia() -> None:
    state = _state()
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _spy(log, GameEvent.PHASE, Moment.START, where={"phase": "strategy"})
        triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "action"})
        assert log == []
        triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "strategy"})
        assert len(log) == 1
        log.clear()
    with rules_hooks.temporary_hooks():
        _spy(log, GameEvent.TURN, Moment.END, condition=lambda _s, _p, c: c.get("subject") == "p2")
        triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1")
        triggers.fire(state, GameEvent.TURN, Moment.END, subject="p2")
    assert log == [("turn", "end", "p2")]


def test_kolejnosc_rozstrzygania_faza_akcji_i_pozostale() -> None:
    state = _state(phase=Phase.ACTION, active_player_id="p3")
    for pid, card in (("p1", 5), ("p2", 1), ("p3", 3)):
        state.players[pid].strategy_cards = [card]
    # Inicjatywa: p2(1), p3(3), p1(5); aktywny p3 -> p3, p1, p2.
    assert triggers.resolution_order(state) == ["p3", "p1", "p2"]
    other = _state(phase=Phase.STRATEGY, speaker_id="p2")
    assert triggers.resolution_order(other) == ["p2", "p3", "p1"]  # od mówcy zgodnie z zegarem


def _replace_hook(ran: list[str]) -> rules_hooks.HookFn:
    def hook(_s: GameState, pid: str, _c: Mapping[str, Any]) -> bool:
        ran.append(f"replace-{pid}")
        return True

    return hook


def test_replace_ma_pierwszenstwo_i_konczy_rozstrzyganie() -> None:
    state = _state()
    ran: list[str] = []
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW)(
            lambda _s, _p, _c: ran.append("trigger")
        )
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW, kind=HookKind.REPLACE)(
            _replace_hook(ran)
        )
        result = triggers.fire(state, GameEvent.TURN, Moment.START)
    assert result.replaced and ran == ["replace-p1"]  # pierwszy REPLACE, bez TRIGGER-ów


def test_replace_ktory_zwraca_falsz_nie_zastepuje() -> None:
    state = _state()
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW, kind=HookKind.REPLACE)(
            lambda _s, _p, _c: False
        )
        result = triggers.fire(state, GameEvent.TURN, Moment.START)
    assert not result.replaced


def test_rekurencja_jest_ograniczona() -> None:
    state = _state()
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW)(
            lambda s, _p, _c: triggers.fire(s, GameEvent.TURN, Moment.START)
        )
        with pytest.raises(ValueError, match="recursion"):
            triggers.fire(state, GameEvent.TURN, Moment.START)


def test_on_event_odrzuca_zle_rodzaje() -> None:
    with pytest.raises(ValueError, match="TRIGGER or REPLACE"):
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW, kind=HookKind.MODIFY)


# ------------------------------------------------------------------------------ oferty (may)


def test_opcjonalna_zdolnosc_tworzy_oferte_i_okno_reaction() -> None:
    state = _state(speaker_id="p1", phase=Phase.STRATEGY)
    done: list[str] = []
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.END, LAW, optional=True, label="Test may")(
            lambda _s, pid, ctx: done.append(f"{pid}:{ctx['accepted']}")
        )
        result = triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1")
        assert [o.player_id for o in result.offers] == ["p1", "p2", "p3"]
        assert [o.label for o in state.pending_offers] == ["Test may"] * 3
        window = state.pending_window
        assert window is not None and window.window_type is WindowType.REACTION
        assert window.queue == ["p1", "p2", "p3"] and window.current_responder == "p1"
        offer_p1 = triggers.offers_for(state, "p1")[0]
        with pytest.raises(ValueError, match="belongs to"):
            triggers.accept_offer(state, "p2", offer_p1.id)
        after = triggers.accept_offer(state, "p1", offer_p1.id, {"x": 1})
        assert done == ["p1:True"] and len(after.pending_offers) == 2
        assert after.pending_window is not None and after.pending_window.current_responder == "p2"
        offer_p2 = triggers.offers_for(after, "p2")[0]
        with pytest.raises(ValueError, match="turn to respond"):
            triggers.decline_offer(after, "p3", triggers.offers_for(after, "p3")[0].id)
        mid = triggers.decline_offer(after, "p2", offer_p2.id)
        assert done == ["p1:True"]  # odrzucenie nie uruchamia hooka
        last = triggers.accept_offer(mid, "p3", triggers.offers_for(mid, "p3")[0].id)
        assert last.pending_offers == [] and last.pending_window is None  # okno zamknięte


def test_oferta_przy_otwartym_oknie_czeka_w_stanie() -> None:
    state = _state()
    state.pending_window = TimingWindow(window_type=WindowType.SPACE_CANNON, queue=["p1"])
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.END, LAW, optional=True)(lambda *_a: None)
        triggers.fire(state, GameEvent.TURN, Moment.END)
    assert len(state.pending_offers) == 3
    assert state.pending_window is not None
    assert state.pending_window.window_type is WindowType.SPACE_CANNON  # cudze okno nietknięte


def test_oferta_wymaga_wciaz_posiadanego_zrodla() -> None:
    state = _state()
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.END, LAW, optional=True)(lambda *_a: None)
        triggers.fire(state, GameEvent.TURN, Moment.END)
        offer = triggers.offers_for(state, "p1")[0]
        state.decks.agenda_laws.clear()  # prawo zniesione, zanim gracz odpowiedział
        with pytest.raises(ValueError, match="no longer in play"):
            triggers.accept_offer(state, "p1", offer.id)


# ------------------------------------------------------------------------------ efekty trwałe


def test_efekt_trwaly_jest_zrodlem_hooka_do_wygasniecia() -> None:
    state = _state()
    seen: list[str] = []
    effect_source = HookSource(rules_hooks.SOURCE_EFFECT, "boost")
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.COMBAT_ROUND, Moment.START, effect_source)(
            lambda _s, pid, _c: seen.append(pid)
        )
        triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START)
        assert seen == []  # efektu jeszcze nie ma
        active_effects.add_effect(state, "boost", Duration.COMBAT, owner="p2")
        triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START)
        assert seen == ["p2"]  # tylko właściciel efektu
        triggers.fire(state, GameEvent.COMBAT, Moment.END)  # koniec zakresu COMBAT
        assert state.active_effects == []
        triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START)
        assert seen == ["p2"]


def test_efekt_globalny_dotyczy_wszystkich_a_zakresy_wygasaja_osobno() -> None:
    state = _state()
    active_effects.add_effect(state, "global", Duration.PHASE)
    active_effects.add_effect(state, "mine", Duration.TURN, owner="p1")
    active_effects.add_effect(state, "round", Duration.ROUND)
    assert {e.key for e in active_effects.effects_for(state, "p3")} == {"global", "round"}
    assert active_effects.has_effect(state, "p1", "mine")
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1")
    assert {e.key for e in state.active_effects} == {"global", "round"}
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "action"})
    assert {e.key for e in state.active_effects} == {"round"}
    triggers.fire(state, GameEvent.ROUND, Moment.END)
    assert state.active_effects == []


def test_wygasanie_pomija_zastapione_zdarzenie() -> None:
    state = _state()
    active_effects.add_effect(state, "k", Duration.TURN)
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.END, LAW, kind=HookKind.REPLACE)(
            lambda *_a: True
        )
        triggers.fire(state, GameEvent.TURN, Moment.END)
    assert len(state.active_effects) == 1  # tura się NIE zakończyła


def test_efekty_dodawanie_zdejmowanie_i_walidacja() -> None:
    state = _state()
    first = active_effects.add_effect(state, "a", Duration.GAME, data={"n": 1})
    second = active_effects.add_effect(state, "a", Duration.GAME, owner="p2")
    assert first.id != second.id and first.data == {"n": 1}
    assert active_effects.remove_by_key(state, "a", owner="p2") == 1
    assert active_effects.remove_effect(state, first.id) and not active_effects.remove_effect(
        state, first.id
    )
    with pytest.raises(ValueError, match="Unknown player"):
        active_effects.add_effect(state, "x", Duration.TURN, owner="zzz")


# ------------------------------------------------------------------------------ źródła


def test_zrodla_relikty_liderzy_przelom_efekty_i_rodzina_frakcji() -> None:
    registry = StaticDataRegistry()  # wiąże rejestr dla hooków
    assert rules_hooks.bound_registry() is registry
    state = GameState(
        players={
            "p1": PlayerState(player_id="p1", faction="sol", relics=["shard"]),
            "p2": PlayerState(player_id="p2", faction="keleresm"),
        }
    )
    sol = rules_hooks.owned_sources(state, "p1")
    assert HookSource(rules_hooks.SOURCE_RELIC, "shard") in sol
    sol_leaders = {s.component_id for s in sol if s.kind == rules_hooks.SOURCE_LEADER}
    assert sol_leaders == {"solagent"}  # agent domyślnie odblokowany, commander/hero zablokowani
    state.players["p1"].leader_states = {"solhero": "unlocked", "solagent": "locked"}
    changed = {
        s.component_id
        for s in rules_hooks.owned_sources(state, "p1")
        if s.kind == rules_hooks.SOURCE_LEADER
    }
    assert changed == {"solhero"}
    assert not any(
        s.kind == rules_hooks.SOURCE_BREAKTHROUGH for s in rules_hooks.owned_sources(state, "p1")
    )
    state.players["p1"].breakthrough_unlocked = True
    assert any(
        s.kind == rules_hooks.SOURCE_BREAKTHROUGH for s in rules_hooks.owned_sources(state, "p1")
    )
    keleres = rules_hooks.owned_sources(state, "p2")
    assert HookSource(rules_hooks.SOURCE_FACTION, "keleresm") in keleres
    assert HookSource(rules_hooks.SOURCE_FACTION, "keleres") in keleres  # rodzina wariantów
    active_effects.add_effect(state, "fx", Duration.GAME, owner="p1")
    assert HookSource(rules_hooks.SOURCE_EFFECT, "fx") in rules_hooks.owned_sources(state, "p1")
    assert HookSource(rules_hooks.SOURCE_EFFECT, "fx") not in rules_hooks.owned_sources(state, "p2")


def test_karty_z_reki_nie_sa_zrodlami() -> None:
    state = _state()
    state.players["p1"].private.action_cards = ["disgrace"]
    state.players["p1"].private.promissory_notes = ["alliance"]
    kinds = {s.kind for s in rules_hooks.owned_sources(state, "p1")}
    assert kinds <= {
        rules_hooks.SOURCE_FACTION,
        rules_hooks.SOURCE_AGENDA,
        rules_hooks.SOURCE_LEADER,
        rules_hooks.SOURCE_UNIT,  # jednostki frakcji są jawne (RULES.md 61.3)
    }


# ------------------------------------------------------------------------------ podpięcie do reguł


def _log_all(log: list[tuple[str, str, str | None]], *events: tuple[GameEvent, Moment]) -> None:
    for event, moment in events:
        _spy(log, event, moment)


def test_turn_flow_tura_pas_faza_i_runda() -> None:
    state = _state(phase=Phase.ACTION, active_player_id="p1", round_number=2)
    for pid, card in (("p1", 1), ("p2", 2), ("p3", 3)):
        state.players[pid].strategy_cards = [card]
        state.players[pid].exhausted_strategy_cards = [card]
    state.players["p1"].took_action_this_turn = True
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _log_all(
            log,
            (GameEvent.TURN, Moment.END),
            (GameEvent.TURN, Moment.START),
            (GameEvent.PLAYER_PASSED, Moment.WHEN),
            (GameEvent.PLAYER_PASSED, Moment.AFTER),
            (GameEvent.LAST_PLAYER_PASSED, Moment.AFTER),
            (GameEvent.PHASE, Moment.END),
            (GameEvent.PHASE, Moment.START),
            (GameEvent.ROUND, Moment.END),
            (GameEvent.ROUND, Moment.START),
        )
        nxt = turn_flow.end_turn(state, "p1")
        assert log == [("turn", "end", "p1"), ("turn", "start", "p2")]
        log.clear()
        for pid in ("p1", "p2"):
            nxt.players[pid].passed = True
        nxt.active_player_id = "p3"
        passed = turn_flow.pass_turn(nxt, "p3")
        assert [e[:2] for e in log] == [
            ("player.passed", "when"),
            ("player.passed", "after"),
            ("player.last_passed", "after"),
        ]
        log.clear()
        status = turn_flow.next_phase(passed)
        assert status.phase is Phase.STATUS
        assert log == [("phase", "end", None), ("phase", "start", None)]
        log.clear()
        turn_flow.next_round(status)
        assert [e[:2] for e in log] == [
            ("phase", "end"),
            ("round", "end"),
            ("round", "start"),
            ("phase", "start"),
        ]


def test_phase_start_filtr_where_na_nowej_rundzie() -> None:
    state = _state(phase=Phase.STATUS)
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _spy(log, GameEvent.PHASE, Moment.START, where={"phase": "strategy"})
        turn_flow.next_round(state)
    assert log == [("phase", "start", None)]


def test_ekonomia_karty_i_jednostki_emituja_zdarzenia() -> None:
    state = _state()
    state.players["p1"].commodity_value = 3
    state.decks.action_card_deck = ["a1"]
    system = SystemState(position="101", system_id="1")
    state.systems["101"] = system
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _log_all(
            log,
            (GameEvent.TRADE_GOODS_GAINED, Moment.AFTER),
            (GameEvent.COMMODITIES_REPLENISHED, Moment.AFTER),
            (GameEvent.ACTION_CARDS_DRAWN, Moment.WHEN),
            (GameEvent.ACTION_CARDS_DRAWN, Moment.AFTER),
            (GameEvent.UNIT_PLACED, Moment.AFTER),
            (GameEvent.UNIT_DESTROYED, Moment.AFTER),
            (GameEvent.TECHNOLOGY_GAINED, Moment.WHEN),
            (GameEvent.TECHNOLOGY_GAINED, Moment.AFTER),
            (GameEvent.SPEAKER_CHANGED, Moment.AFTER),
        )
        economy.gain_trade_goods(state, "p1", 2)
        economy.gain_trade_goods(state, "p1", 0)  # zero: bez zdarzenia
        economy.replenish_commodities(state, "p1")
        assert card_draw.draw_action_card(state, "p1")
        assert [e[:2] for e in log] == [
            ("economy.trade_goods_gained", "after"),
            ("economy.commodities_replenished", "after"),
            ("cards.action_drawn", "when"),
            ("cards.action_drawn", "after"),
        ]
        log.clear()
        unit_ops.place_units(state, system, "space", "p1", "cruiser", 2, UnitCause.PLACED)
        unit_ops.place_units(state, system, "space", "p1", "cruiser", 1, UnitCause.SETUP)
        unit_ops.remove_units(state, system, "space", "p1", "cruiser", 1, UnitCause.REMOVED)
        unit_ops.remove_units(state, system, "space", "p1", "cruiser", 1, UnitCause.DESTROYED)
        assert [e[0] for e in log] == ["unit.placed", "unit.destroyed"]
        log.clear()
        technology.grant_technology(state, "p1", "ws")
        technology.grant_technology(state, "p1", "ws")  # idempotentne: bez drugiego zdarzenia
        strategy_phase.set_speaker(state, "p2")
        assert [e[:2] for e in log] == [
            ("technology.gained", "when"),
            ("technology.gained", "after"),
            ("speaker.changed", "after"),
        ]


def test_kontrola_planety_wlasciciele_when_przed_after() -> None:
    state = _state()
    state.systems["000"] = SystemState(position="000", system_id="18", planet_owners={"jord": "p2"})
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _log_all(
            log,
            (GameEvent.PLANET_CONTROL_LOST, Moment.WHEN),
            (GameEvent.PLANET_CONTROL_LOST, Moment.AFTER),
            (GameEvent.PLANET_CONTROL_GAINED, Moment.WHEN),
            (GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER),
        )
        control.set_planet_control(state, "000", "jord", "p1")
        control.set_planet_control(state, "000", "jord", "p1")  # bez zmiany: bez zdarzeń
    assert log == [
        ("planet.control_lost", "when", "p2"),
        ("planet.control_gained", "when", "p1"),
        ("planet.control_lost", "after", "p2"),
        ("planet.control_gained", "after", "p1"),
    ]
    assert state.systems["000"].planet_owners["jord"] == "p1"


def test_wybor_karty_strategii_mozna_zastapic() -> None:
    """Public Disgrace: „that player must choose a different strategy card instead”."""
    registry = StaticDataRegistry()
    state = GameState(
        phase=Phase.STRATEGY,
        speaker_id="p1",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red"),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
    )
    state.strategy_card_tg = {1: 2}
    plain = strategy_phase.pick_strategy_card(state, registry, "p1", 1)
    assert plain.players["p1"].strategy_cards == [1] and plain.players["p1"].trade_goods == 2
    state.decks.agenda_laws["spy_law"] = "for"
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(
            GameEvent.STRATEGY_CARD_CHOSEN, Moment.WHEN, LAW, kind=HookKind.REPLACE
        )(lambda _s, _p, ctx: ctx["subject"] == "p1")
        blocked = strategy_phase.pick_strategy_card(state, registry, "p1", 1)
    assert blocked.players["p1"].strategy_cards == []  # wybór nie nastąpił
    assert blocked.players["p1"].trade_goods == 0 and blocked.strategy_card_tg[1] == 2
    assert blocked.players["p1"].passed is False


def test_agenda_ujawnienie_glosy_wynik_i_prawo() -> None:
    from tests.test_agenda_phase import LAW as LAW_AGENDA
    from tests.test_agenda_phase import _planet_of
    from tests.test_agenda_phase import _state as agenda_state

    registry = StaticDataRegistry()
    state = agenda_state(registry, [LAW_AGENDA])
    state.decks.agenda_laws["spy_law"] = "for"
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _log_all(
            log,
            (GameEvent.AGENDA_REVEALED, Moment.WHEN),
            (GameEvent.AGENDA_REVEALED, Moment.AFTER),
            (GameEvent.AGENDA_VOTES_CAST, Moment.WHEN),
            (GameEvent.AGENDA_VOTES_CAST, Moment.AFTER),
            (GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.WHEN),
            (GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER),
            (GameEvent.LAW_DISCARDED, Moment.AFTER),
        )
        work = agenda_phase.reveal_agenda(state, registry, "p2")
        assert [e[:2] for e in log] == [
            ("agenda.revealed", "when"),
            ("agenda.revealed", "after"),
        ]
        log.clear()
        work = agenda_phase.cast_vote(work, registry, "p3", "for", [_planet_of(work, "p3")])
        work = agenda_phase.abstain(work, registry, "p1")
        work = agenda_phase.abstain(work, registry, "p2")
        names = [e[:2] for e in log]
        assert names[:2] == [("agenda.votes_cast", "when"), ("agenda.votes_cast", "after")]
        assert names[2:] == [
            ("agenda.outcome_resolved", "when"),
            ("agenda.outcome_resolved", "after"),
        ]
        log.clear()
        agenda_phase.repeal_law(work, LAW_AGENDA)
        assert log == [("agenda.law_discarded", "after", None)]


def test_walka_start_rundy_koniec_i_zwyciezca() -> None:
    from tests.test_battle import _grid
    from tests.test_battle import _state as battle_state

    registry = StaticDataRegistry()
    grid = _grid()
    state = battle_state({"p1": {"dreadnought": 3}, "p2": {"fighter": 1}})
    state.decks.agenda_laws["spy_law"] = "for"
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _log_all(
            log,
            (GameEvent.COMBAT, Moment.START),
            (GameEvent.COMBAT, Moment.END),
            (GameEvent.COMBAT_ROUND, Moment.START),
            (GameEvent.COMBAT_ROUND, Moment.END),
            (GameEvent.COMBAT_WON, Moment.AFTER),
            (GameEvent.UNIT_DESTROYED, Moment.AFTER),
        )
        active_effects.add_effect(state, "round-boost", Duration.COMBAT_ROUND)
        active_effects.add_effect(state, "combat-boost", Duration.COMBAT)
        state = battle.start_combat(state, grid, registry)
        for _ in range(60):
            combat = state.active_combat
            assert combat is not None
            if combat.step is CombatStep.DONE:
                break
            if combat.step is CombatStep.AFB:
                state = battle.resolve_afb(state, grid, registry)
            elif combat.step is CombatStep.ROLL:
                state = battle.roll_round(state, grid, registry)
            else:
                pid = state.pending_window.current_responder  # type: ignore[union-attr]
                assert pid is not None
                need = battle.required_hits(state, grid, registry, pid)
                units = battle.side_units(state, grid, registry, pid)
                destroy: dict[str, int] = {}
                left = need
                for unit in units:
                    take = min(unit.count, left)
                    if take:
                        destroy[unit.base_type] = take
                        left -= take
                state = battle.assign_combat_hits(
                    state, grid, registry, pid, sustain={}, destroy=destroy, destroy_damaged={}
                )
    kinds = [e[0] for e in log]
    assert kinds[0] == "combat" and log[0][1] == "start"
    assert "combat.round" in kinds and ("combat", "end", None) in log
    assert ("combat.won", "after", "p1") in log
    assert "unit.destroyed" in kinds
    assert state.active_effects == []  # efekty COMBAT_ROUND i COMBAT wygasły
