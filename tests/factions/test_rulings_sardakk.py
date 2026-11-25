"""Sardakk N'orr — rulingi ``docs/rules_tirules/F_norr.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Podstawowe testy komponentów są w ``test_sardakk.py``,
``test_flows_sardakk.py`` i ``test_rulings_audit.py`` (tam też część znaczników). Statusy bez
testu: ``tests/rulings_status.json`` (Harrow L1Z1X, Magmus Reactor Muaat).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    active_effects,
    battle,
    battle_rerolls,
    capacity,
    damage,
    faction_components,
    invasion,
    leaders,
    promissory_play,
    reaction_cards,
    rules_hooks,
    triggers,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    InvasionPhase,
    InvasionState,
    TacticalStep,
)
from src.core.hooks import reactions_invasion
from src.core.hooks.factions import sardakk
from src.core.registry import StaticDataRegistry
from tests.factions.test_sardakk import _accept, _combat, _ghom_state, _grid, _round_end_ctx, _state
from tests.factions.test_sardakk import registry as registry  # noqa: F401 - fixture modułu
from tests.rulings import ruling

assert _grid  # autouse: siatka demo dla board_graph

_DOMINUS_EFFECT = "relics:dominusorb"  # efekt Dominus Orb (core/hooks/relics_events.py)


def _dice(*rolls: list[int]) -> Callable[..., tuple[GameState, list[int]]]:
    """Kolejne wywołania ``roll_dice`` zwracają kolejne listy kości (grupy po kolei)."""
    queue: Iterator[list[int]] = iter(rolls)

    def roll(state: GameState, count: int, sides: int = 10) -> tuple[GameState, list[int]]:
        values = next(queue)
        assert len(values) == count
        return state, list(values)

    return roll


def _ground_rolled(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch,
    attacker_dice: list[int], defender_dice: list[int], *, defender_units: dict[str, int],
) -> GameState:
    """p2 (Sol, aktywny) atakuje Sardakk (p1, VPW) na Industrex; po rzucie rundy."""
    state = _state(sardakk_active=False)
    state.players["p1"].technologies = ["vpw"]
    state.systems["102"].planet_units["industrex"] = {
        "p2": {"infantry": len(attacker_dice)}, "p1": dict(defender_units),
    }
    state.active_combat = ActiveCombat(
        kind="ground", position="102", planet="industrex", attacker="p2", defender="p1",
        step=CombatStep.ROLL,
    )
    monkeypatch.setattr(battle, "roll_dice", _dice(attacker_dice, defender_dice))
    return battle.roll_round(state, build_demo_grid(registry), registry)


# ============================================================ Unrelenting, Tekklar, flagowiec


@ruling(
    "F_norr/unrelenting/1", "F_norr/tekklar-legion/1", "F_norr/cmorran-norr/1",
)
def test_premie_walki_nie_dotycza_afb_bombardowania_space_cannon(
    registry: StaticDataRegistry,
) -> None:
    """Unrelenting, flagowiec i Tekklar to ``combat.roll_modifier``; AFB, Bombardment i Space
    Cannon mają własne punkty, na których Sardakk nie ma hooków; rzut AFB bez modyfikatora."""
    state = _state()
    state.systems["102"].space_units = {"p1": {"destroyer": 2, "flagship": 1}, "p2": {"fighter": 3}}
    active_effects.add_effect(state, sardakk.TEKKLAR_BONUS, Duration.COMBAT, owner="p1")
    for point in (
        rules_hooks.POINT_SPACE_CANNON_ROLL_MODIFIER, rules_hooks.POINT_BOMBARDMENT_ROLL_MODIFIER,
    ):
        assert rules_hooks.hooks_at(point, state, "p1") == []
    _combat(state, "space", CombatStep.AFB)
    rolled = battle.resolve_afb(state, build_demo_grid(registry), registry)
    combat = rolled.active_combat
    assert combat is not None
    entry = combat.afb["p1"][0]
    assert entry["baseType"] == "destroyer" and entry["modifier"] == 0
    assert entry["hits"] == sum(1 for d in entry["dice"] if d >= entry["hitsOn"])


# ============================================================== Valkyrie Particle Weave + mech


@ruling(
    "F_norr/valkyrie-particle-weave/1", "F_norr/valkyrie-particle-weave/1.1",
    "F_norr/valkyrie-exoskeleton/1", "F_norr/valkyrie-exoskeleton/2",
)
def test_vpw_trafienie_przed_anulowaniem_i_mech_po_sustain(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Trafienie VPW dochodzi do rzutu; Sustain mecha anuluje trafienie przeciwnika, a VPW zostaje
    i mech dokłada swoje trafienie."""
    state = _ground_rolled(registry, monkeypatch, [10, 1, 1], [10], defender_units={"mech": 1})
    combat = state.active_combat
    assert combat is not None
    assert combat.pending_hits == {"p2": 2, "p1": 1}  # 1 z kości + 1 VPW przeciw p2
    after = battle.assign_combat_hits(
        state, build_demo_grid(registry), registry, "p1",
        sustain={"mech": 1}, destroy={}, destroy_damaged={},
    )
    assert after.active_combat is not None
    assert after.active_combat.pending_hits["p2"] == 3  # VPW nie przepada, + Valkyrie Exoskeleton


@ruling("F_norr/valkyrie-particle-weave/2")
def test_vpw_przy_zerze_wlasnych_trafien(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _ground_rolled(registry, monkeypatch, [10], [1], defender_units={"infantry": 1})
    assert state.active_combat is not None
    assert state.active_combat.pending_hits["p2"] == 1


@ruling("F_norr/valkyrie-particle-weave/1")
def test_vpw_nie_przepada_przy_przerzucie(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Przerzut własnych kości (Fire Team) liczy trafienia od nowa - razem z trafieniem VPW
    (wcześniej przepadało)."""
    state = _ground_rolled(registry, monkeypatch, [10], [1, 1], defender_units={"infantry": 2})
    work = state.clone()
    total = battle_rerolls.reroll_combat_dice(
        work, "p1", {(0, 0), (0, 1)}, "fire_team", "Fire Team"
    )
    combat = work.active_combat
    assert combat is not None
    dice_hits = combat.rolls["p1"][0]["hits"]
    assert total == dice_hits + 1 and combat.pending_hits["p2"] == dice_hits + 1


@ruling("F_norr/valkyrie-particle-weave/3")
def test_vpw_gdy_przeciwnik_trafia_po_zmianie_kosci(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Decyzja użytkownika 2026-11-17 (RULES.md 62.1): VPW liczy trafienia przeciwnika po
    przerzutach i premiach do kości, przed przypisaniem strat - premia zamieniająca pudło
    w trafienie daje obowiązkowe trafienie VPW."""
    state = _ground_rolled(registry, monkeypatch, [1], [10], defender_units={"infantry": 1})
    combat = state.active_combat
    assert combat is not None and combat.pending_hits == {"p2": 1, "p1": 0}
    battle_rerolls.boost_combat_dice(state, "p2", {(0, 0)}, "test", amount=9)
    assert combat.pending_hits == {"p2": 2, "p1": 1}
    assert state.pending_window is not None and "p1" in state.pending_window.queue


# ================================================================================ Exotrireme II


@ruling("technologies:exo2#1", "technologies:exo2#2")
def test_exotrireme_statystyki(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "sardakk", ["exo2"], "dreadnought", False)
    assert unit is not None and unit.id == sardakk.EXOTRIREME_UNIT
    assert (unit.cost, unit.combat_hits_on, unit.move_value, unit.capacity_value) == (4, 5, 2, 1)
    assert unit.sustain_damage and (unit.bombard_hits_on, unit.bombard_die_count) == (4, 2)


@ruling("F_norr/exotrireme/1.1", "F_norr/exotrireme/2")
def test_exotrireme_tylko_cudze_i_sustain_nie_chroni(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["exo2"]
    state.systems["102"].space_units["p1"] = {"dreadnought": 1, "cruiser": 1}
    state.systems["102"].space_units["p2"] = {"dreadnought": 1, "carrier": 1}
    inputs = sardakk.exotrireme_inputs(state, registry, "p1", _round_end_ctx())
    assert [o["value"] for o in inputs[0]["options"]] == ["carrier#1", "dreadnought#1"]
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=_round_end_ctx())
    after = _accept(state, "p1", {"ships": ["dreadnought#1"]})
    assert after.systems["102"].space_units["p2"] == {"carrier": 1}  # zniszczony, nie uszkodzony
    assert after.systems["102"].space_units["p1"] == {"cruiser": 1}


@ruling("F_norr/exotrireme/5")
def test_exotrireme_uszkodzony_po_sustain_nadal_moze_sie_zniszczyc(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.players["p1"].technologies = ["exo2"]
    system = state.systems["102"]
    system.space_units["p1"] = {"dreadnought": 1}
    system.space_units["p2"] = {"cruiser": 2}
    damage.set_damaged(system, "space", "p1", "dreadnought", 1)  # użył Sustain Damage w rundzie
    ctx = {**_round_end_ctx(), "sustained": {"dreadnought": 1}}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=ctx)
    after = _accept(state, "p1", {"ships": ["cruiser#1", "cruiser#2"]})
    assert after.systems["102"].space_units.get("p1", {}) == {}
    assert after.systems["102"].space_units.get("p2", {}) == {}


@ruling("technologies:exo2#4")
def test_kazdy_exotrireme_osobno(registry: StaticDataRegistry) -> None:
    """„destroy THIS unit”: dwa Exotrireme II w jednej rundzie - po ofercie na każdy."""
    state = _state()
    state.players["p1"].technologies = ["exo2"]
    state.systems["102"].space_units["p1"] = {"dreadnought": 2}
    state.systems["102"].space_units["p2"] = {"cruiser": 4}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=_round_end_ctx())
    first = _accept(state, "p1", {"ships": ["cruiser#1", "cruiser#2"]})
    assert [o.label for o in first.pending_offers] == ["Exotrireme II"]
    second = _accept(first, "p1", {"ships": ["cruiser#1", "cruiser#2"]})
    assert second.pending_offers == [] and second.pending_window is None
    assert second.systems["102"].space_units.get("p2", {}) == {}
    assert second.systems["102"].space_units.get("p1", {}) == {}


@ruling("F_norr/exotrireme/4")
def test_exotrireme_i_devotion_na_zmiane_od_atakujacego(registry: StaticDataRegistry) -> None:
    """N'orr (atakujący, 2× Exotrireme II) i Yin (Devotion): N'orr, Yin, N'orr."""
    state = _state()
    state.players["p2"].faction = "yin"
    state.players["p1"].technologies = ["exo2"]
    state.systems["102"].space_units = {
        "p1": {"dreadnought": 2}, "p2": {"cruiser": 2, "carrier": 2},
    }
    _combat(state, "space")
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=_round_end_ctx())
    window = state.pending_window
    assert window is not None and window.queue == ["p1", "p2"]
    first = _accept(state, "p1", {"ships": ["carrier#1"]})
    assert first.pending_window is not None
    assert first.pending_window.current_responder == "p2"  # Yin przed drugim Exotrireme
    exo = next(o for o in first.pending_offers if o.player_id == "p1")
    with pytest.raises(ValueError, match="turn to respond"):
        triggers.accept_offer(first, "p1", exo.id, {"ships": ["carrier#1"]})
    passed = first
    for offer in [o for o in first.pending_offers if o.player_id == "p2"]:  # Devotion (+ agent Yin)
        passed = triggers.decline_offer(passed, "p2", offer.id)
    assert passed.pending_window is not None and passed.pending_window.current_responder == "p1"
    done = _accept(passed, "p1", {"ships": ["carrier#1"]})
    assert done.pending_window is None
    assert done.systems["102"].space_units["p2"] == {"cruiser": 2}


# =============================================================================== G'hom Sek'kus


def _sources(state: GameState, registry: StaticDataRegistry) -> list[str]:
    return [pos for pos, _, _ in sardakk._commander_sources(state, registry, "p1")]


def _targets(state: GameState, registry: StaticDataRegistry) -> set[str]:
    form = sardakk.commander_inputs(state, registry, "p1")
    return {
        str(o["value"]).split(">", 1)[1]
        for field in form for o in field["options"] if ">" in str(o["value"])
    }


@ruling("F_norr/ghom-sekkus/1")
def test_ghom_dom_wyeliminowanego_sie_nie_liczy(registry: StaticDataRegistry) -> None:
    """Dom gracza bez jednostek i planet (wyeliminowanego) nadal jest systemem domowym."""
    state = _state()
    assert not any(state.systems[p].space_units or state.systems[p].planet_units
                   for p in state.systems)  # p2 (Sol) nie ma niczego na planszy
    for i in range(5):
        state.systems["103"].planet_owners[f"jord{i}"] = "p1"  # dom Sol
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", sardakk.COMMANDER) == leaders.LOCKED


@ruling("F_norr/ghom-sekkus/2")
def test_ghom_bez_statkow_w_aktywnym_systemie(registry: StaticDataRegistry) -> None:
    state = _ghom_state()
    state.invasion = None
    state.players["p1"].technologies = ["amd"]  # 102 w siatce demo to pole asteroid
    grid = build_demo_grid(registry)
    started = invasion.begin_invasion(state, grid, registry)
    assert started.invasion is not None and started.invasion.phase is InvasionPhase.COMMIT
    after, _ = faction_components.play(
        started, registry, "p1", "leader", sardakk.COMMANDER, {"src:000:mr": "infantry>industrex"},
    )
    assert after.systems["102"].planet_units["industrex"]["p1"] == {"infantry": 1}
    locked = state.model_copy(deep=True)
    locked.players["p1"].leader_states = {}
    assert invasion.begin_invasion(locked, grid, registry).invasion is None  # bez commandera


def _ghom_committed(registry: StaticDataRegistry) -> GameState:
    """G'hom Sek'kus: piechota z Mecatol na Industrex kontrolowany przez p2; p1 bez statków."""
    state = _ghom_state()
    state.players["p1"].technologies = ["amd"]
    state.systems["102"].planet_owners["industrex"] = "p2"
    after, _ = faction_components.play(
        state, registry, "p1", "leader", sardakk.COMMANDER, {"src:000:mr": "infantry>industrex"},
    )
    return after


@ruling("F_norr/ghom-sekkus/8")
def test_ghom_parley_do_przestrzeni_bez_pojemnosci(registry: StaticDataRegistry) -> None:
    state = _ghom_committed(registry)
    reactions_invasion.parley(state, registry, "p2", {"planet": "industrex"})
    assert state.systems["102"].space_units["p1"] == {"infantry": 1}  # aktywny system, nie źródło
    assert capacity.players_with_excess(state, registry, "102") == ["p1"]


@ruling("F_norr/ghom-sekkus/5", "F_norr/ghom-sekkus/3")
def test_ghom_po_jednej_z_planety_na_dowolna_planete(registry: StaticDataRegistry) -> None:
    state = _ghom_state()
    state.players["p1"].technologies = ["amd"]
    state.systems["000"].planet_units["mr"] = {"p1": {"infantry": 3, "mech": 1}}
    form = sardakk.commander_inputs(state, registry, "p1")
    assert [f["key"] for f in form] == ["src:000:mr"]  # 1 wybór = najwyżej 1 jednostka z planety
    for owner in (None, "p1", "p2"):
        if owner is None:
            state.systems["102"].planet_owners.pop("industrex", None)
        else:
            state.systems["102"].planet_owners["industrex"] = owner
        assert _targets(state, registry) == {"industrex"}


@ruling("F_norr/ghom-sekkus/4")
def test_ghom_tylko_jako_aktywny_gracz(registry: StaticDataRegistry) -> None:
    state = _ghom_state()
    state.invasion = InvasionState(position="102", attacker="p2", phase=InvasionPhase.COMMIT)
    reason = sardakk._commander_window(state, registry, "p1")
    assert reason is not None and "your Commit Ground Forces" in reason


@ruling("F_norr/ghom-sekkus/9")
def test_bombarduje_tylko_aktywny_gracz(registry: StaticDataRegistry) -> None:
    state = _ghom_state()
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.BOMBARDMENT)
    state.systems["102"].planet_units["industrex"] = {"p2": {"infantry": 1}}
    state.systems["102"].space_units = {"p2": {"dreadnought": 1}}  # statek nieaktywnego gracza
    assert invasion.bombard_groups(state, registry) == []
    state.systems["102"].space_units["p1"] = {"dreadnought": 1}
    assert [g.base_type for g in invasion.bombard_groups(state, registry)] == ["dreadnought"]


@ruling("R_invasion/rules-reference/3")
def test_ghom_space_cannon_defense_strzela(registry: StaticDataRegistry) -> None:
    state = _ghom_committed(registry)
    state.systems["102"].planet_units["industrex"]["p2"] = {"pds": 1}
    after = invasion.advance(state, build_demo_grid(registry), registry)
    assert after.invasion is not None
    assert after.invasion.phase is InvasionPhase.SPACE_CANNON_DEFENSE
    assert invasion.defense_planets(after, registry) == ["industrex"]


@ruling("F_norr/ghom-sekkus/6.1")
def test_ghom_ceasefire_tylko_z_aktywnego_systemu(registry: StaticDataRegistry) -> None:
    state = _ghom_state()
    state.players["p1"].technologies = ["amd"]
    state.systems["102"].planet_units["industrex"] = {"p1": {"infantry": 1}}
    assert _sources(state, registry) == ["102", "000"]
    active_effects.add_effect(
        state, promissory_play.CEASEFIRE_EFFECT, Duration.TACTICAL_ACTION, owner="p1"
    )
    assert _sources(state, registry) == ["102"]


@ruling("F_norr/ghom-sekkus/7")
def test_ghom_dominus_orb_nie_otwiera_systemu_z_zetonem(registry: StaticDataRegistry) -> None:
    """Purging Dominus Orb does not let G'hom Sek'kus commit from systems with own token."""
    state = _ghom_state()
    state.players["p1"].technologies = ["amd"]
    state.systems["000"].command_tokens = ["p1"]
    assert _sources(state, registry) == []
    active_effects.add_effect(state, _DOMINUS_EFFECT, Duration.TACTICAL_ACTION, owner="p1")
    assert _sources(state, registry) == []


@ruling("leaders:sardakkcommander#1")
def test_ghom_odblokowany_przy_establish_control_za_pozno(registry: StaticDataRegistry) -> None:
    state = _ghom_state()
    state.players["p1"].technologies = ["amd"]
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.ESTABLISH)
    reason = sardakk._commander_window(state, registry, "p1")
    assert reason is not None and "Commit Ground Forces" in reason


@ruling("C_exploration_cards/demilitarized-zone/2")
def test_ghom_nie_na_demilitarized_zone(registry: StaticDataRegistry) -> None:
    state = _ghom_state()
    state.players["p1"].technologies = ["amd"]
    state.planet_attachments["industrex"] = ["dmz"]
    assert _targets(state, registry) == set()
    with pytest.raises(ValueError, match="Demilitarized"):
        invasion.commit_from_planets(state, registry, [("000", "mr", "infantry", "industrex")])
    state.systems["102"].space_units["p1"] = {"carrier": 1, "infantry": 1}
    with pytest.raises(ValueError, match="Demilitarized"):
        invasion.commit_ground_forces(state, registry, {"industrex": {"infantry": 1}})


# ======================================================================= Sh'val, Harbinger


def _hero_landed(registry: StaticDataRegistry, *, pds: bool = False) -> GameState:
    """Tekklar Conditioning: lotniskowiec z 2 piechotami w 102, lądowanie na Industrex p2."""
    state = _state()
    state.players["p1"].leader_states = {sardakk.HERO: "unlocked"}
    state.tactical_step = TacticalStep.MOVEMENT
    state.tactical_moved = True
    state.systems["102"].space_units["p1"] = {"carrier": 1, "infantry": 2}
    state.systems["102"].planet_owners["industrex"] = "p2"
    if pds:
        state.systems["102"].planet_units["industrex"] = {"p2": {"pds": 1}}
    after, _ = faction_components.play(state, registry, "p1", "leader", sardakk.HERO)
    started = invasion.begin_invasion(after, build_demo_grid(registry), registry)
    return invasion.commit_ground_forces(started, registry, {"industrex": {"infantry": 2}})


@ruling("F_norr/shval-harbinger-tekklar-conditioning/4")
def test_hero_parley_usuwa_piechote_bez_statkow(registry: StaticDataRegistry) -> None:
    state = _hero_landed(registry)
    assert "carrier" not in state.systems["102"].space_units.get("p1", {})
    reactions_invasion.parley(state, registry, "p2", {"planet": "industrex"})
    assert state.systems["102"].space_units["p1"] == {"infantry": 2}
    assert capacity.players_with_excess(state, registry, "102") == ["p1"]


@ruling("F_norr/shval-harbinger-tekklar-conditioning/2")
def test_hero_statki_wracaja_do_rezerwy_nie_sa_niszczone(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core import capture, production

    destroyed: list[str] = []
    real = capture.on_destroyed

    def spy(s: GameState, *args: Any) -> None:
        destroyed.append(str(args[3]))
        real(s, *args)

    monkeypatch.setattr(capture, "on_destroyed", spy)
    before = production.reinforcements_left(_state(), "p1", "carrier")
    state = _hero_landed(registry)
    assert "carrier" not in state.systems["102"].space_units.get("p1", {})
    assert production.reinforcements_left(state, "p1", "carrier") == before  # wróciły do rezerwy
    assert destroyed == []  # zdolności „gdy zniszczony” nie mają czego wyzwolić
    assert not (state.active_combat and state.active_combat.destroyed_ships)


@ruling("R_invasion/rules-reference/3")
def test_hero_space_cannon_defense_zostaje(registry: StaticDataRegistry) -> None:
    state = _hero_landed(registry, pds=True)
    after = invasion.advance(state, build_demo_grid(registry), registry)
    assert after.invasion is not None
    assert after.invasion.phase is InvasionPhase.SPACE_CANNON_DEFENSE
    assert invasion.defense_planets(after, registry) == ["industrex"]


@ruling("F_norr/shval-harbinger-tekklar-conditioning/3")
def test_hero_zamyka_okno_po_ruchu(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {sardakk.HERO: "unlocked"}
    state.tactical_step = TacticalStep.MOVEMENT
    state.tactical_moved = True
    state.systems["102"].space_units["p1"] = {"carrier": 1}

    def after_move(s: GameState) -> list[Any]:
        return [w for w in reaction_cards.open_windows(s)
                if (w.event, w.moment) == (GameEvent.SHIPS_MOVED, Moment.AFTER)]

    assert after_move(state)
    after, _ = faction_components.play(state, registry, "p1", "leader", sardakk.HERO)
    assert after_move(after) == []


@ruling("leaders:sardakkhero#unlock")
def test_hero_odblokowanie_3_cele(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].scored_secrets = ["a", "b"]
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", sardakk.HERO) == leaders.LOCKED
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", sardakk.HERO) == leaders.UNLOCKED
