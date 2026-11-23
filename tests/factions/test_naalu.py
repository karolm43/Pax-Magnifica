"""The Naalu Collective — komplet komponentów frakcji (RULES.md 62.16) i rulingi F_naalu.

Scenariusze przez prawdziwe API (oferty, notka, okno secondary): ``test_flows_naalu.py``.
Statusy bez testu (nieaktywne warianty liderów i mecha): ``tests/rulings_status.json``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    battle,
    board_graph,
    capacity,
    command_tokens,
    faction_components,
    fleet_pool,
    initiative_zero,
    invasion,
    leaders,
    limits,
    movement,
    peek,
    promissory_play,
    reaction_pause,
    rules_hooks,
    status_phase,
    strategic_action,
    tactical,
    timing,
    triggers,
    turn_flow,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
    Phase,
    PlayerState,
    StatusPhaseState,
    StatusStep,
    StrategyResolution,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hooks import reactions_misc
from src.core.hooks.factions import naalu
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.strategy_cards import politics
from tests.factions.completeness import missing_components
from tests.rulings import ruling

# 101 = dom Naalu (09: Maaluuk, Druaa), 102 = Wellon (19), 103 = Vefutii (20), 104 = Thibah
# (21, p2), 105 = Tarmann (22), 106 = Quann (25); 000 = Mecatol. Pierścień 1: sąsiedzi kolejno.
HOME, ARENA, EAST, RIVAL, FAR, WEST = "101", "102", "103", "104", "105", "106"
MAALUUK, WELLON, VEFUTII, THIBAH = "maaluuk", "wellon", "vefutii", "thibah"
_SCEPTER = "emelpar"  # Scepter of Emelpar


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    """Rejestr podpięty, siatka gry odpięta (wcześniejszy test API zostawia swoją mapę) -
    efekty liczą sąsiedztwo z systemów stanu testu."""
    rules_hooks.bind_registry(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(None)
    yield
    board_graph.bind_grid_provider(previous)


def _state(other: str = "sol") -> GameState:
    """p1 = Naalu (karty 5, 6), p2 = rywal (aktywny w fazie akcji; karty 2, 7)."""
    p1 = PlayerState(player_id="p1", color="green", faction="naalu", home_position=HOME,
                     strategy_cards=[5, 6])
    p2 = PlayerState(player_id="p2", color="blue", faction=other, home_position=RIVAL,
                     strategy_cards=[2, 7])
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p2",
        speaker_id="p2",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            HOME: SystemState(position=HOME, system_id="09", planet_owners={MAALUUK: "p1"}),
            ARENA: SystemState(position=ARENA, system_id="19"),
            EAST: SystemState(position=EAST, system_id="20"),
            RIVAL: SystemState(position=RIVAL, system_id="21", planet_owners={THIBAH: "p2"}),
            FAR: SystemState(position=FAR, system_id="22"),
            WEST: SystemState(position=WEST, system_id="25"),
        },
    )
    p1.controlled_planets = [MAALUUK]
    p2.controlled_planets = [THIBAH]
    for p in state.players.values():
        p.cc_reinf = 8
        p.tactical_cc = 3
        p.fleet_cc = 3
        p.strategic_cc = 2
    return state


def _offers(state: GameState, pid: str, label: str) -> list[Any]:
    return [o for o in triggers.offers_for(state, pid) if label in o.label]


def _accept(state: GameState, pid: str, label: str, params: dict[str, Any] | None = None
            ) -> GameState:
    offer = _offers(state, pid, label)[0]
    return triggers.accept_offer(state, pid, offer.id, params)


def test_kompletnosc_naalu(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "naalu") == []


# ------------------------------------------------------------- Telepathic / żeton „0”


def _end_strategy(state: GameState) -> GameState:
    work = state.clone()
    work.phase = Phase.STRATEGY
    return turn_flow.next_phase(work)


@ruling("abilities:telepathic#1", "abilities:telepathic#2",
        "R_initiative_order/rules-reference/1.1")
def test_telepathic_zeton_zero_pierwszy_w_inicjatywie() -> None:
    state = _state()
    assert turn_flow.turn_order(state) == ["p2", "p1"]  # karta 2 przed 5
    after = _end_strategy(state)
    assert initiative_zero.holder(after) == "p1"
    assert initiative_zero.initiative(after, "p1") == 0
    assert turn_flow.strict_initiative_order(after) == ["p1", "p2"]
    assert after.active_player_id == "p1"  # pierwszy w fazie akcji


@ruling("F_naalu/telepathic/1")
def test_telepathic_zeton_zostaje_po_zamianie_kart() -> None:
    """Imperial Arbiter zabiera kartę - żeton „0” zostaje u Naalu (nie leży na karcie)."""
    after = _end_strategy(_state())
    after.players["p1"].strategy_cards, after.players["p2"].strategy_cards = [2, 7], [5, 6]
    assert initiative_zero.holder(after) == "p1"
    assert turn_flow.turn_order(after) == ["p1", "p2"]


@ruling("R_elimination/rules-reference/10.3")
def test_zeton_zero_znika_na_koncu_statusu(registry: StaticDataRegistry) -> None:
    after = _end_strategy(_state())
    assert initiative_zero.holder(after) == "p1"
    work = after.clone()
    work.phase = Phase.STATUS
    work.status = StatusPhaseState(step=StatusStep.COMPLETE)
    finished = status_phase.finish_status(work, registry)
    assert initiative_zero.holder(finished) is None


# ------------------------------------------------------------------ Gift of Prescience


def _gift_window_state() -> GameState:
    """Faza strategii z kompletem kart (okno „koniec fazy strategii”), Gift w ręce p2."""
    state = _state()
    state.phase = Phase.STRATEGY
    state.active_player_id = None
    state.players["p2"].private.promissory_notes = [naalu.GIFT]
    return state


@ruling("promissory_notes:gift#1", "promissory_notes:gift#2", "F_naalu/gift-of-prescience/1")
def test_gift_of_prescience_zeton_zero_dla_grajacego(registry: StaticDataRegistry) -> None:
    state = _gift_window_state()
    assert reactions_misc.strategy_phase_end(state)  # okno istnieje: komplet kart
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows[naalu.GIFT]["playable"], rows[naalu.GIFT]["reason"]
    played, _ = promissory_play.play(state, registry, "p2", naalu.GIFT, {})
    assert naalu.GIFT in played.players["p2"].promissory_notes_in_play
    assert initiative_zero.holder(played) == "p2"
    # Telepathic nie działa w tej rundzie - żeton zostaje u grającego.
    after = turn_flow.next_phase(played)
    assert initiative_zero.holder(after) == "p2"
    assert after.active_player_id == "p2"
    # Zamiana kart nie zabiera żetonu (gift 1).
    after.players["p1"].strategy_cards, after.players["p2"].strategy_cards = [1, 7], [5, 6]
    assert turn_flow.turn_order(after)[0] == "p2"


def test_gift_pauza_przed_przejsciem_do_fazy_akcji(registry: StaticDataRegistry) -> None:
    """Koniec fazy strategii = kluczowe okno pauzy (decyzja użytkownika 2026-11-22): „Next phase”
    czeka stały czas, uprawniony jest każdy poza Naalu, kto ma notkę w ręce."""
    state = _gift_window_state()
    reaction_pause.sync(state, registry, now=100.0)
    pause = state.reaction_pause
    assert pause is not None and pause.eligible == ["p2"]
    with pytest.raises(ValueError):
        turn_flow.next_phase(state)
    released = reaction_pause.release(state, now=100.0 + pause.seconds + 1)
    assert turn_flow.next_phase(released).phase is Phase.ACTION


def test_bez_naalu_brak_pauzy_na_koncu_fazy_strategii(registry: StaticDataRegistry) -> None:
    state = _gift_window_state()
    state.players["p1"].faction = "letnev"
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is None


def test_gift_poza_koncem_fazy_strategii_niezagrywalny(registry: StaticDataRegistry) -> None:
    state = _gift_window_state()
    state.players["p1"].strategy_cards = []  # wybór kart niekompletny - okna nie ma
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert not rows[naalu.GIFT]["playable"]


@ruling("promissory_notes:gift#3", "promissory_notes:gift#4")
def test_gift_wraca_do_naalu_na_koncu_statusu(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].promissory_notes_in_play = [naalu.GIFT]
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    assert naalu.GIFT not in state.players["p2"].promissory_notes_in_play
    assert naalu.GIFT in state.players["p1"].private.promissory_notes


# ---------------------------------------------------------------------------- Foresight


def _foresight_state() -> GameState:
    """Naalu w ARENA (krążownik, transportowiec, 2 myśliwce, 1 piechota, 1 mech); p2 wlatuje."""
    state = _state()
    state.systems[ARENA].space_units = {
        "p1": {"cruiser": 1, "carrier": 1, "fighter": 2, "infantry": 1, "mech": 1},
        "p2": {"destroyer": 1},
    }
    state.active_system = ARENA
    state.tactical_step = TacticalStep.MOVEMENT
    return state


def _p2_moved(state: GameState, position: str = ARENA) -> GameState:
    work = state.clone()
    movement.fire_ships_moved(work, "p2", position, RIVAL, {"destroyer": 1})
    return work


@ruling("abilities:foresight#1", "abilities:foresight#2", "F_naalu/foresight/3",
        "F_naalu/foresight/8")
def test_foresight_przenosi_statki_i_kladzie_zeton() -> None:
    state = _p2_moved(_foresight_state())
    assert _offers(state, "p1", "Foresight")
    after = _accept(state, "p1", "Foresight", {"destination": EAST})
    moved = after.systems[EAST].space_units["p1"]
    # Wszystkie statki (myśliwce bez transportu) + siły naziemne do pojemności (carrier = 4).
    assert moved == {"cruiser": 1, "carrier": 1, "fighter": 2, "infantry": 1, "mech": 1}
    assert "p1" not in after.systems[ARENA].space_units or not any(
        after.systems[ARENA].space_units["p1"].values()
    )  # w aktywnym systemie nie ma już statków Naalu (Space Cannon Offense - 8)
    assert "p1" in after.systems[EAST].command_tokens
    assert after.players["p1"].strategic_cc == 1


def test_foresight_wybor_ladunku_z_auto(registry: StaticDataRegistry) -> None:
    """Gracz wybiera, ile sił naziemnych zabrać; „Auto” = do pojemności, najpierw mechy."""
    state = _foresight_state()
    state.systems[ARENA].space_units["p1"]["infantry"] = 5  # 1 mech + 5 piechoty, pojemność 4
    moved = _p2_moved(state)
    offer = _offers(moved, "p1", "Foresight")[0]
    hook = rules_hooks.hook_by_seq(offer.hook_seq)
    assert hook is not None and hook.inputs is not None
    fields = {i["key"]: i for i in hook.inputs(moved, registry, "p1", offer.ctx)}
    assert (fields["carry_mech"]["auto"], fields["carry_infantry"]["auto"]) == (1, 3)
    auto = _accept(moved, "p1", "Foresight", {"destination": EAST})  # pola pominięte = Auto
    assert auto.systems[EAST].space_units["p1"]["infantry"] == 3
    own = _accept(moved, "p1", "Foresight",
                  {"destination": EAST, "carry_mech": 0, "carry_infantry": 4})
    assert own.systems[EAST].space_units["p1"]["infantry"] == 4
    assert "mech" not in own.systems[EAST].space_units["p1"]
    assert own.systems[ARENA].space_units["p1"] == {"infantry": 1, "mech": 1}
    with pytest.raises(ValueError, match="can carry"):
        _accept(moved, "p1", "Foresight",
                {"destination": EAST, "carry_mech": 1, "carry_infantry": 4})


def test_foresight_nie_dla_wlasnego_ruchu() -> None:
    state = _foresight_state()
    movement.fire_ships_moved(state, "p1", ARENA, HOME, {"cruiser": 1})
    assert not _offers(state, "p1", "Foresight")


@ruling("F_naalu/foresight/1", "C_action_cards/intercept/2")
def test_foresight_to_nie_odwrot() -> None:
    """Bez ogłoszenia odwrotu i bez walki - Intercept nie ma czego anulować."""
    state = _p2_moved(_foresight_state())
    after = _accept(state, "p1", "Foresight", {"destination": EAST})
    assert after.active_combat is None
    assert after.pending_window is None or after.pending_window.window_type is not (
        WindowType.COMBAT_RETREAT
    )


@ruling("F_naalu/foresight/2")
def test_foresight_zeton_nie_jest_wydany_scepter_nie_dziala() -> None:
    state = _p2_moved(_foresight_state())
    state.players["p1"].relics = [_SCEPTER]
    reinf = state.players["p1"].cc_reinf
    after = _accept(state, "p1", "Foresight", {"destination": EAST})
    me = after.players["p1"]
    assert me.strategic_cc == 1 and me.cc_reinf == reinf  # żeton z puli strategii na planszę
    assert _SCEPTER not in me.exhausted_relics  # Scepter nie zastępuje żetonu


@ruling("F_naalu/foresight/4", "F_naalu/foresight/4.1")
def test_foresight_cele_bez_mglawicy_supernowej_i_asteroid() -> None:
    state = _foresight_state()
    state.systems[EAST].system_id = "42"  # mgławica
    state.systems[WEST].system_id = "43"  # supernowa
    assert naalu.foresight_destinations(state, "p1", ARENA) == ["000", HOME]
    state.systems["000"].system_id = "44"  # pole asteroid
    assert naalu.foresight_destinations(state, "p1", ARENA) == [HOME]
    state.players["p1"].technologies = ["amd"]  # Antimass Deflectors
    assert naalu.foresight_destinations(state, "p1", ARENA) == ["000", HOME]


def test_foresight_cel_bez_cudzych_statkow() -> None:
    state = _foresight_state()
    state.systems[EAST].space_units = {"p2": {"destroyer": 1}}
    assert EAST not in naalu.foresight_destinations(state, "p1", ARENA)


@ruling("F_naalu/foresight/5", "F_naalu/foresight/5.1", "C_action_cards/nav-suite/7.1")
def test_foresight_z_gravity_rift_rzut_a_zeton_i_tak_w_celu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _foresight_state()
    state.systems[ARENA].system_id = "41"  # gravity rift
    calls: list[dict[str, int]] = []

    def all_lost(_state: GameState, _pid: str, units: dict[str, int]) -> dict[str, int]:
        calls.append(dict(units))
        return dict(units)

    monkeypatch.setattr(movement, "roll_rift_exit", all_lost)
    after = _accept(_p2_moved(state), "p1", "Foresight", {"destination": EAST})
    assert calls  # Naalu rzuca na usunięcie (anomalia działa także przy Nav Suite innego gracza)
    assert not any(after.systems[EAST].space_units.get("p1", {}).values())
    assert "p1" in after.systems[EAST].command_tokens  # 5.1


@ruling("F_naalu/foresight/6")
def test_foresight_limity_w_celu(registry: StaticDataRegistry) -> None:
    state = _foresight_state()
    state.systems[EAST].space_units = {"p1": {"dreadnought": 2}}
    after = _accept(_p2_moved(state), "p1", "Foresight", {"destination": EAST})
    checked = limits.enforce_limits(after, registry)  # pula floty 3, statków 4
    window = checked.pending_window
    assert window is not None and window.window_type is WindowType.FLEET_POOL
    assert window.context["position"] == EAST


@ruling("F_naalu/foresight/7")
def test_foresight_zeton_juz_w_celu_wraca_do_rezerwy() -> None:
    state = _foresight_state()
    state.systems[EAST].command_tokens = ["p1"]
    reinf = state.players["p1"].cc_reinf
    after = _accept(_p2_moved(state), "p1", "Foresight", {"destination": EAST})
    assert after.systems[EAST].command_tokens == ["p1"]
    assert after.players["p1"].cc_reinf == reinf + 1
    assert after.players["p1"].strategic_cc == 1


def test_foresight_bez_zetonu_w_puli_strategii() -> None:
    state = _foresight_state()
    state.players["p1"].strategic_cc = 0
    assert not _offers(_p2_moved(state), "p1", "Foresight")


# --------------------------------------------------------------------------- Neuroglaive


def _activate(state: GameState, registry: StaticDataRegistry, position: str) -> GameState:
    work = state.clone()
    work.active_system = None
    work.tactical_step = None
    return tactical.activate_system(work, grid_from_state(work, registry), position)


@ruling("technologies:ng#1")
def test_neuroglaive_aktywujacy_traci_zeton_puli_floty(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = [naalu.NEUROGLAIVE]
    state.systems[ARENA].space_units = {"p1": {"cruiser": 1}}
    after = _activate(state, registry, ARENA)
    assert after.players["p2"].fleet_cc == 2
    assert after.players["p2"].cc_reinf == 9
    empty = _activate(state, registry, EAST)  # bez statków Naalu - bez skutku
    assert empty.players["p2"].fleet_cc == 3


@ruling("F_naalu/neuroglaive/1")
def test_neuroglaive_limit_puli_floty_przed_ruchem(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = [naalu.NEUROGLAIVE]
    state.systems[ARENA].space_units = {"p1": {"cruiser": 1}}
    state.systems[FAR].space_units = {"p2": {"destroyer": 3}}  # inny system aktywującego
    after = limits.enforce_limits(_activate(state, registry, ARENA), registry)
    window = after.pending_window
    assert window is not None and window.window_type is WindowType.FLEET_POOL
    assert window.context["position"] == FAR
    with pytest.raises(ValueError, match="fleet pool"):
        timing.require_no_limit_window(after)  # ruch czeka na usunięcie nadwyżki


# ------------------------------------------------------------- Hybrid Crystal Fighter II


@ruling("technologies:hcf2#1", "technologies:hcf2#2")
def test_hcf2_statystyki_i_ruch_bez_transportu(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "naalu", [naalu.HCF2], "fighter")
    assert unit is not None and unit.id == "naalu_fighter2"
    assert (unit.cost, unit.combat_hits_on, unit.move_value) == (0.5, 7, 2)  # 1 za 2 sztuki


@ruling("technologies:hcf2#3")
def test_hcf2_myśliwce_ponad_pojemnosc_jako_pol_statku(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = [naalu.HCF2]
    state.players["p1"].fleet_cc = 2
    state.systems[ARENA].space_units = {"p1": {"cruiser": 1, "fighter": 3}}
    report = fleet_pool.fleet_report(state, ARENA, "p1", registry)
    assert report.ships == {"cruiser": 1, "fighter": 3}
    assert report.total == 3 and report.excess == 1  # 3 myśliwce = 2 statki (w górę)
    assert capacity.capacity_report(state, registry, ARENA, "p1").excess == 0
    fleet_pool.check_removal(report, {"fighter": 1})  # 2 myśliwce = 1 statek
    with pytest.raises(ValueError, match="more ships than"):
        fleet_pool.check_removal(report, {"fighter": 2})
    with pytest.raises(ValueError, match="Still over"):
        fleet_pool.check_removal(report, {})
    assert fleet_pool.auto_removal(state, registry, "p1", report) == {"fighter": 1}


def test_bez_hcf2_myśliwce_ponad_pojemnosc_przepadaja(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[ARENA].space_units = {"p1": {"cruiser": 1, "fighter": 3}}
    assert fleet_pool.fleet_report(state, ARENA, "p1", registry).ships == {"cruiser": 1}
    assert capacity.capacity_report(state, registry, ARENA, "p1").excess == 3


# ------------------------------------------------------------------------------ Matriarch


def _invasion_state(registry: StaticDataRegistry, *, infantry: int = 0) -> GameState:
    """Naalu (aktywny) z Matriarch nad Wellon (ARENA); na Wellon PDS i piechota p2."""
    state = _state()
    state.active_player_id = "p1"
    state.active_system = ARENA
    state.tactical_step = TacticalStep.INVASION
    space: dict[str, int] = {"flagship": 1, "fighter": 3}
    if infantry:
        space["infantry"] = infantry
    state.systems[ARENA].space_units = {"p1": space}
    state.systems[ARENA].planet_units = {WELLON: {"p2": {"pds": 1, "infantry": 1}}}
    state.systems[ARENA].planet_owners = {WELLON: "p2"}
    state.players["p2"].controlled_planets = [THIBAH, WELLON]
    state.invasion = InvasionState(position=ARENA, attacker="p1", phase=InvasionPhase.COMMIT)
    return state


@ruling("units:naalu_flagship#1", "F_naalu/matriarch/4")
def test_matriarch_mysliwce_laduja_i_walcza(registry: StaticDataRegistry) -> None:
    state = _invasion_state(registry)
    after = invasion.commit_ground_forces(state, registry, {WELLON: {"fighter": 2}})
    assert after.systems[ARENA].planet_units[WELLON]["p1"] == {"fighter": 2}
    units = battle.combat_units(after, None, registry, kind="ground", position=ARENA,
                                planet=WELLON, player_id="p1")
    assert [(u.base_type, u.count) for u in units] == [("fighter", 2)]
    assert WELLON in invasion.combat_planets(after, registry)
    assert WELLON in invasion.defense_planets(after, registry)  # Space Cannon Defense (4)


def test_bez_matriarch_mysliwce_nie_laduja(registry: StaticDataRegistry) -> None:
    state = _invasion_state(registry)
    state.systems[ARENA].space_units["p1"] = {"carrier": 1, "fighter": 3, "infantry": 1}
    with pytest.raises(ValueError, match="not a ground force"):
        invasion.commit_ground_forces(state, registry, {WELLON: {"fighter": 1}})


@ruling("units:naalu_flagship#2", "F_naalu/matriarch/1", "F_naalu/matriarch/2")
def test_matriarch_mysliwce_wracaja_i_nie_daja_kontroli(registry: StaticDataRegistry) -> None:
    state = _invasion_state(registry)
    state.systems[ARENA].planet_units = {WELLON: {"p2": {"pds": 1}}}  # bez sił naziemnych p2
    after = invasion.commit_ground_forces(state, registry, {WELLON: {"fighter": 2}})
    assert after.invasion is not None
    after.invasion.phase = InvasionPhase.GROUND_COMBAT
    done = invasion._enter(after, grid_from_state(after, registry), registry,
                           InvasionPhase.ESTABLISH)
    assert done.systems[ARENA].space_units["p1"]["fighter"] == 3  # wróciły do przestrzeni
    assert "p1" not in done.systems[ARENA].planet_units[WELLON]
    assert done.systems[ARENA].planet_owners[WELLON] == "p2"  # bez kontroli (1)
    assert done.systems[ARENA].planet_units[WELLON]["p2"] == {"pds": 1}  # struktury zostają (2)


def test_matriarch_z_piechota_przejmuje_planete(registry: StaticDataRegistry) -> None:
    state = _invasion_state(registry, infantry=1)
    state.systems[ARENA].planet_units = {WELLON: {"p2": {"pds": 1}}}
    after = invasion.commit_ground_forces(
        state, registry, {WELLON: {"fighter": 2, "infantry": 1}}
    )
    done = invasion._enter(after, grid_from_state(after, registry), registry,
                           InvasionPhase.ESTABLISH)
    assert done.systems[ARENA].planet_owners[WELLON] == "p1"
    assert done.systems[ARENA].planet_units[WELLON]["p1"] == {"infantry": 1}
    assert done.systems[ARENA].space_units["p1"]["fighter"] == 3


def test_matriarch_powrot_po_walce_tylko_z_tej_planety(registry: StaticDataRegistry) -> None:
    state = _invasion_state(registry)
    after = invasion.commit_ground_forces(state, registry, {WELLON: {"fighter": 2}})
    triggers.fire(after, GameEvent.COMBAT, Moment.END, ctx={
        "kind": "ground", "position": ARENA, "planet": WELLON, "winner": "p1",
        "attacker": "p1", "defender": "p2",
    })
    assert after.systems[ARENA].space_units["p1"]["fighter"] == 3


@ruling("F_naalu/matriarch/3")
def test_matriarch_dacxive_bez_sil_naziemnych_nie_daje_planety(
    registry: StaticDataRegistry,
) -> None:
    state = _invasion_state(registry)
    state.players["p1"].technologies = ["dxa"]
    after = invasion.commit_ground_forces(state, registry, {WELLON: {"fighter": 2}})
    after.systems[ARENA].planet_units[WELLON].pop("p2")  # walka wygrana samymi myśliwcami
    triggers.fire(after, GameEvent.COMBAT_WON, Moment.AFTER, subject="p1", ctx={
        "kind": "ground", "position": ARENA, "planet": WELLON, "winner": "p1",
    })
    assert not _offers(after, "p1", "Dacxive")


# ---------------------------------------------------------------------------- Iconoclast TE


@ruling("units:naalu_mech_te#1", "F_naalu/iconoclast-omega-omega/1")
def test_iconoclast_mech_gdy_inny_gracz_zdobywa_relikt(registry: StaticDataRegistry) -> None:
    state = _state()
    triggers.fire(state, GameEvent.COMPONENT_GAINED, Moment.WHEN, subject="p2",
                  ctx={"player": "p2", "component": "relics:shard"})
    offer = _offers(state, "p1", "Iconoclast")
    assert offer and offer[0].mandatory  # obowiązkowo (ΩΩ 1)
    after = _accept(state, "p1", "Iconoclast", {"planet": MAALUUK})
    assert after.systems[HOME].planet_units[MAALUUK]["p1"] == {"mech": 1}


def test_iconoclast_nie_dla_wlasnego_reliktu() -> None:
    state = _state()
    triggers.fire(state, GameEvent.COMPONENT_GAINED, Moment.WHEN, subject="p1",
                  ctx={"player": "p1", "component": "relics:shard"})
    assert not _offers(state, "p1", "Iconoclast")


# -------------------------------------------------------------------------- Z'eu (agent)


@ruling("leaders:naaluagent-te#1", "F_naalu/zeu-omega-omega/1")
def test_zeu_zwraca_zeton_z_aktywacji_i_signal_jamming(registry: StaticDataRegistry) -> None:
    state = _state()
    after = _activate(state, registry, ARENA)  # aktywacja kładzie żeton p2
    assert _offers(after, "p1", "Z'eu")
    used = _accept(after, "p1", "Z'eu")
    assert "p2" not in used.systems[ARENA].command_tokens
    assert used.players["p2"].cc_reinf == 9
    assert used.active_system == ARENA  # system pozostaje aktywowany
    assert leaders.state_of(used, registry, "p1", naalu.AGENT) == leaders.EXHAUSTED
    # Inne położenie żetonu (Signal Jamming: z rezerwy) też otwiera ofertę.
    jam = _state()
    command_tokens.place_on_board_from_reinforcements(jam, jam.systems[EAST], "p2")
    assert _offers(jam, "p1", "Z'eu")


def test_zeu_w_trakcie_primary_diplomacy_nie_otwiera_okna() -> None:
    """Diplomacy kładzie żetony w trakcie primary: oferta Z'eu czeka (okno secondary musi się
    jeszcze otworzyć - regresja fuzz seed 11)."""
    state = _state()
    state.pending_strategy = StrategyResolution(initiative=2, owner_id="p2", step="system")
    command_tokens.place_on_board_from_reinforcements(state, state.systems[EAST], "p2")
    assert _offers(state, "p1", "Z'eu")
    assert state.pending_window is None


# ---------------------------------------------------------------------- M'aban (commander)


@ruling("leaders:naalucommander#unlock")
def test_maban_odblokowanie_przy_mecatol(registry: StaticDataRegistry) -> None:
    state = _state()
    assert not naalu._commander_unlocked(state, registry, "p1")
    state.systems[ARENA].space_units = {"p1": {"carrier": 1, "infantry": 1}}  # obok Mecatol
    assert naalu._commander_unlocked(state, registry, "p1")
    state.systems[ARENA].space_units = {"p1": {"carrier": 1}}
    state.systems[FAR].planet_units = {}
    assert not naalu._commander_unlocked(state, registry, "p1")


@ruling("leaders:naalucommander#1", "F_naalu/maban-omega/2")
def test_maban_podglad_notek_sasiadow_i_talii_agend(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].private.promissory_notes = ["blue_sftt"]
    state.systems[ARENA].space_units = {"p1": {"cruiser": 1}, "p2": {"destroyer": 1}}
    assert peek.view(state, grid_from_state(state, registry), "p1") is None  # zablokowany
    leaders.unlock(state, registry, "p1", naalu.COMMANDER)  # zasiewa talię agend
    deck = state.decks.agenda_deck
    assert deck
    seen = peek.view(state, grid_from_state(state, registry), "p1")
    assert seen == {"neighbors": {"p2": ["blue_sftt"]}, "agendaTop": deck[0],
                    "agendaBottom": deck[-1]}
    assert peek.view(state, grid_from_state(state, registry), "p2") is None
    # Covert Legislation: ukryta agenda jest już poza talią - wierzchnia to następna (Ω 2).
    state.decks.agenda_deck = deck[1:]
    seen = peek.view(state, grid_from_state(state, registry), "p1")
    assert seen is not None and seen["agendaTop"] == deck[1]


@ruling("F_naalu/maban-omega/1")
def test_maban_bez_talii_agend_w_trakcie_politics(registry: StaticDataRegistry) -> None:
    state = _state()
    leaders.unlock(state, registry, "p1", naalu.COMMANDER)
    state.pending_strategy = StrategyResolution(
        initiative=politics.INITIATIVE, owner_id="p2", step="speaker"
    )
    seen = peek.view(state, grid_from_state(state, registry), "p1")
    assert seen is not None and seen["agendaTop"] is None and seen["agendaBottom"] is None


# ----------------------------------------------------------------------- The Oracle (hero)


@ruling("leaders:naaluhero#1", "leaders:naaluhero#2", "F_naalu/the-oracle-cradium-geometry/1")
def test_oracle_kazdy_gracz_sam_wybiera_notke(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {naalu.HERO: leaders.UNLOCKED}
    state.players["p2"].private.promissory_notes = ["blue_sftt", "blue_cf"]
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    after = _accept(state, "p1", "The Oracle")
    assert leaders.state_of(after, registry, "p1", naalu.HERO) == leaders.PURGED
    choice = _offers(after, "p2", "give a promissory note")
    assert choice and choice[0].mandatory  # decyzja gracza oddającego (1)
    done = _accept(after, "p2", "give a promissory note", {"note": "blue_cf"})
    assert done.players["p2"].private.promissory_notes == ["blue_sftt"]
    assert "blue_cf" in done.players["p1"].private.promissory_notes


@ruling("leaders:naaluhero#unlock")
def test_oracle_odblokowanie_trzy_cele(registry: StaticDataRegistry) -> None:
    predicate = leaders.unlock_predicate(registry, naalu.HERO)
    assert predicate is not None
    state = _state()
    assert not predicate(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert predicate(state, registry, "p1")


# --------------------------------------------------------------------- Mindsieve (przełom)


def _secondary_state() -> GameState:
    """p2 rozgrywa kartę 2 (Diplomacy); okno secondary dla Naalu, notka w ręce Naalu."""
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.players["p1"].private.promissory_notes = ["green_cf"]
    state.players["p1"].promissory_notes_in_play = ["blue_sftt"]
    return timing.open_window(
        state, WindowType.STRATEGY_SECONDARY, ["p1"], context={"initiative": 2, "cost": 1}
    )


@ruling("breakthroughs:naalubt#1", "F_naalu/mindsieve/1", "F_naalu/mindsieve/2")
def test_mindsieve_notka_z_reki_zamiast_zetonu(registry: StaticDataRegistry) -> None:
    state = _secondary_state()
    assert naalu._mindsieve_window(state, registry, "p1") is None
    inputs = naalu.mindsieve_inputs(state, registry, "p1")
    assert [o["value"] for o in inputs[0]["options"]] == ["green_cf"]  # nie ze strefy gry (1)
    after, _ = faction_components.play(state, registry, "p1", "breakthrough", naalu.BREAKTHROUGH,
                                       {"note": "green_cf"})
    assert "green_cf" in after.players["p2"].private.promissory_notes
    assert strategic_action.secondary_without_token(after, "p1", 2)
    assert after.players["p1"].transacted_with == []  # to nie transakcja (2)


def test_mindsieve_nie_na_wlasnej_karcie(registry: StaticDataRegistry) -> None:
    state = _secondary_state()
    state.active_player_id = "p1"
    assert naalu._mindsieve_window(state, registry, "p1") is not None
    empty = _secondary_state()
    empty.players["p1"].private.promissory_notes = []
    assert naalu._mindsieve_window(empty, registry, "p1") is not None
