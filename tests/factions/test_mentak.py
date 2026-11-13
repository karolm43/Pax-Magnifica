"""The Mentak Coalition — komplet komponentów frakcji (RULES.md 62.8), konwencja par."""

from __future__ import annotations

import pytest

from src.core import active_effects, battle, economy, leaders, payment, rules_hooks, transaction
from src.core.combat import resolve_unit_variant
from src.core.game_events import Duration
from src.core.game_state import ActiveCombat, GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import mentak
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide
from tests.factions.completeness import missing_components


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("101", "20")
    grid.place_system("301", "21")
    grid.build_edges()
    return grid


def _state() -> GameState:
    """p1 = Mentak (aktywny) w 000; p2 = Sol w sąsiednim 101 z 3 TG (sąsiedzi)."""
    p1 = PlayerState(player_id="p1", color="red", faction="mentak", trade_goods=1)
    p2 = PlayerState(player_id="p2", color="blue", faction="sol", trade_goods=3, commodities=1)
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18", space_units={"p1": {"cruiser": 1}}),
            "101": SystemState(position="101", system_id="20", space_units={"p2": {"cruiser": 1}}),
            "301": SystemState(position="301", system_id="21"),
        },
    )


def _pillage_offers(state: GameState) -> list[str]:
    return [o.label for o in state.pending_offers if o.player_id == "p1" and "Pillage" in o.label]


def test_kompletnosc_mentak(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "mentak") == []


def test_pillage_tylko_sasiad_z_trzema_tg_bez_promise(registry: StaticDataRegistry) -> None:
    state = _state()
    assert mentak.pillage_reason(state, "p1", "p2") is None
    state.players["p2"].trade_goods = 2
    assert "fewer than 3" in str(mentak.pillage_reason(state, "p1", "p2"))
    state.players["p2"].trade_goods = 3
    state.players["p2"].promissory_notes_in_play = ["pop"]
    assert "Promise of Protection" in str(mentak.pillage_reason(state, "p1", "p2"))
    far = _state()
    far.systems["101"].space_units = {}
    far.systems["301"].space_units = {"p2": {"cruiser": 1}}
    assert "neighbors" in str(mentak.pillage_reason(far, "p1", "p2"))


def test_pillage_po_zdobyciu_tg_ale_nie_po_zamianie_commodities(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    economy.gain_trade_goods(state, "p2", 1)
    assert _pillage_offers(state) == ["Pillage"]
    converted = _state()
    economy.convert_commodities_to_trade_goods(converted, "p2", 1)  # F_mentak / F_vuilraith
    assert converted.players["p2"].trade_goods == 4
    assert _pillage_offers(converted) == []


def test_pillage_raz_na_strone_transakcji(registry: StaticDataRegistry) -> None:
    """⚠️ P1: TG z transakcji nie dają osobnego Pillage - jedna oferta przeciw partnerowi."""
    state = _state()
    done = transaction.resolve_transaction(
        state, _grid(), "p2", TransactionSide(trade_goods=1), TransactionSide()
    )
    assert done.players["p2"].trade_goods == 4
    assert _pillage_offers(done) == ["Pillage (transaction partner)"]


def test_pillage_zabiera_tg_albo_commodity_jako_tg(registry: StaticDataRegistry) -> None:
    state = _state()
    mentak.pillage_on_gain(state, "p1", {"player": "p2", "params": {"take": "commodity"}})
    assert state.players["p2"].commodities == 0
    assert state.players["p1"].trade_goods == 2  # ⚠️ P2: commodity u Mentaka = trade good
    state.players["p2"].trade_goods = 2
    with pytest.raises(ValueError, match="fewer than 3"):
        mentak.pillage_on_gain(state, "p1", {"player": "p2", "params": {"take": "trade_good"}})


def test_mirror_computing_tg_warte_dwa(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].trade_goods = 3
    assert payment.trade_good_value(state, "p1") == 1
    assert payment.validate_payment(state, registry, "p1", "resources", [], 3) == 3
    state.players["p1"].technologies = ["mc"]
    assert payment.trade_good_value(state, "p1") == 2
    assert payment.validate_payment(state, registry, "p1", "resources", [], 3) == 6


def test_fourth_moon_odbiera_sustain_statkom_w_systemie(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["000"].space_units = {"p1": {"cruiser": 1}, "p2": {"dreadnought": 1}}

    def sustain() -> bool:
        units = battle.combat_units(
            state, _grid(), registry, kind="space", position="000", planet=None, player_id="p2"
        )
        return next(u for u in units if u.base_type == "dreadnought").sustain

    assert sustain()
    state.systems["000"].space_units["p1"]["flagship"] = 1
    assert not sustain()


def test_moll_terminus_odbiera_sustain_na_planecie(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["000"].planet_units = {"mr": {"p2": {"mech": 1}, "p1": {"infantry": 1}}}

    def sustain() -> bool:
        units = battle.combat_units(
            state, _grid(), registry, kind="ground", position="000", planet="mr", player_id="p2"
        )
        return next(u for u in units if u.base_type == "mech").sustain

    assert sustain()
    state.systems["000"].planet_units["mr"]["p1"]["mech"] = 1
    assert not sustain()


def test_corsair_tylko_z_cruiser_ii(registry: StaticDataRegistry) -> None:
    without = resolve_unit_variant(registry, "mentak", [], "cruiser", True)
    assert without is not None and without.id != mentak.CORSAIR
    corsair = resolve_unit_variant(registry, "mentak", ["cr2"], "cruiser", True)
    assert corsair is not None and corsair.id == mentak.CORSAIR
    locked = resolve_unit_variant(registry, "mentak", ["cr2"], "cruiser", False)
    assert locked is not None and locked.id != mentak.CORSAIR


def test_corsair_przelatuje_przez_obce_statki(registry: StaticDataRegistry) -> None:
    state = _state()
    state.active_system = "101"
    state.players["p1"].breakthrough_unlocked = True
    ctx = {"position": "301", "base_type": "cruiser"}
    point = rules_hooks.POINT_MOVEMENT_PASS_FOREIGN_SHIPS
    assert not rules_hooks.permits(point, state, "p1", ctx)  # bez Cruiser II: zwykły krążownik
    state.players["p1"].technologies = ["cr2"]
    assert rules_hooks.permits(point, state, "p1", ctx)
    assert mentak.corsair_passage(state, "p1", ctx)
    assert not mentak.corsair_passage(state, "p1", {**ctx, "base_type": "destroyer"})
    state.systems["101"].space_units = {"p2": {"fighter": 2}}  # same myśliwce w aktywnym
    assert not mentak.corsair_passage(state, "p1", ctx)


def test_sula_mentarion_odblokowanie_czterema_krazownikami(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["000"].space_units["p1"] = {"cruiser": 3}
    unlock = leaders.unlock_predicate(registry, mentak.COMMANDER)
    assert unlock is not None and not unlock(state, registry, "p1")
    state.systems["301"].space_units["p1"] = {"cruiser": 1}
    assert unlock(state, registry, "p1")


def test_salvage_operations_tg_po_walce_nie_po_remisie(registry: StaticDataRegistry) -> None:
    state = _state()
    ctx = {"kind": "space", "winner": "p2", "attacker": "p1", "defender": "p2"}
    assert mentak._fought_and_decided(state, "p1", ctx)
    assert not mentak._fought_and_decided(state, "p1", {**ctx, "winner": ""})
    mentak.salvage_trade_good(state, "p1", ctx)
    assert state.players["p1"].trade_goods == 2


def test_salvage_operations_typy_zniszczone_w_walce(registry: StaticDataRegistry) -> None:
    state = _state()
    state.active_combat = ActiveCombat(kind="space", position="000", attacker="p1", defender="p2")
    state.active_combat.destroyed_all = [
        {"player": "p2", "base_type": "destroyer"},
        {"player": "p2", "base_type": "warsun"},  # bez technologii War Sun - nie
    ]
    assert mentak.salvage_types(state, "p1") == ["destroyer"]
    mentak.salvage_produce(state, "p1", {"position": "000"})
    grant = state.production_grant
    assert grant is not None and grant.allowed_types == ["destroyer"] and grant.units == 1


def test_sleeper_cell_stawia_statki_tylko_za_straty_przeciwnika(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.active_combat = ActiveCombat(kind="space", position="000", attacker="p1", defender="p2")
    state.active_combat.destroyed_all = [{"player": "p2", "base_type": "cruiser"}]
    active_effects.add_effect(state, mentak.SLEEPER, Duration.COMBAT, owner="p1", data={"seen": 1})
    assert not mentak._sleeper_pending(state, "p1", {})  # zniszczone przed użyciem się nie liczą
    state.active_combat.destroyed_all += [
        {"player": "p2", "base_type": "destroyer"},
        {"player": "p1", "base_type": "cruiser"},
    ]
    assert mentak._sleeper_pending(state, "p1", {})
    mentak._place_sleepers(state, "p1")
    assert state.systems["000"].space_units["p1"] == {"cruiser": 1, "destroyer": 1}
    assert not mentak._sleeper_pending(state, "p1", {})


def test_ambush_trafienia_przypisuje_przeciwnik(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["000"].space_units = {"p1": {"cruiser": 2}, "p2": {"carrier": 3}}
    state.active_combat = ActiveCombat(kind="space", position="000", attacker="p1", defender="p2")
    for seed in range(1, 40):  # ziarno, przy którym pada co najmniej jedno trafienie
        state.rng_seed, state.rng_counter = seed, 0
        trial = state.clone()
        mentak.ambush(trial, "p1", {"params": {"ships": ["cruiser:0", "cruiser:1"]}})
        assert trial.active_combat is not None
        entry = trial.active_combat.log[0]
        assert entry["phase"] == "AMBUSH" and entry["rolls"]["p1"][0]["modifier"] == 0
        if entry["hits"]["p1"]:
            assert trial.active_combat.start_hits == {"p2": entry["hits"]["p1"]}
            break
    else:
        pytest.fail("No seed produced an Ambush hit.")
    with pytest.raises(ValueError, match="1 or 2"):
        mentak.ambush(state.clone(), "p1", {"params": {"ships": []}})
