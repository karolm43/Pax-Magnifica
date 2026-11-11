"""Testy kart reakcji akcji taktycznej (RULES.md 53.5.b): okna, efekty, hooki w silniku."""
from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    action_cards,
    control,
    movement,
    production,
    reaction_cards,
    space_cannon,
    tactical,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, SystemState, TacticalStep
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

ACTIVE = "101"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(
    hands: dict[str, list[str]] | None = None,
    *,
    step: TacticalStep | None = TacticalStep.MOVEMENT,
    system_id: str = "18",
) -> GameState:
    """Trzech graczy; p1 aktywuje system ACTIVE (żeton już leży), nikt jeszcze nie ruszył."""
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system=ACTIVE if step is not None else None,
        tactical_step=step,
        players={
            pid: PlayerState(player_id=pid, color=color)
            for pid, color in (("p1", "red"), ("p2", "blue"), ("p3", "green"))
        },
        systems={
            ACTIVE: SystemState(position=ACTIVE, system_id=system_id, command_tokens=["p1"]),
        },
    )
    for pid, cards in (hands or {}).items():
        state.players[pid].private.action_cards = list(cards)
    return state


def _playable(state: GameState, registry: StaticDataRegistry, player: str, card: str) -> bool:
    rows = action_cards.playability(state, registry, player)
    return bool(next(row for row in rows if row["card_id"] == card)["playable"])


def _play(
    state: GameState,
    registry: StaticDataRegistry,
    player: str,
    card: str,
    params: dict[str, Any] | None = None,
) -> GameState:
    new, implemented = action_cards.play_action_card(state, registry, player, card, params)
    assert implemented
    return new


def _grid(*specs: tuple[str, str, set[str], list[str]]) -> HexGrid:
    grid = HexGrid()
    for position, system_id, anomalies, wormholes in specs:
        grid.place_system(position, system_id, anomalies=anomalies, wormholes=wormholes)
    grid.build_edges()
    return grid


def _end_action(state: GameState) -> GameState:
    return tactical.end_tactical_action(state)


# --------------------------------------------------------------------------- Lost Star Chart


def test_lost_star_alpha_beta_sasiaduja_tylko_w_tej_akcji(registry: StaticDataRegistry) -> None:
    grid = _grid(("000", "18", set(), ["BETA"]), ("301", "20", set(), ["ALPHA"]))
    state = _state({"p1": ["lost_star"]})
    state.active_system = "000"
    state.systems["301"] = SystemState(
        position="301", system_id="20", space_units={"p1": {"destroyer": 1}}
    )
    ok, _ = movement.can_move(state, grid, registry, "301", "destroyer", "p1")
    assert not ok  # bez karty: brak trasy (kafelki daleko od siebie)
    assert _playable(state, registry, "p1", "lost_star")
    new = _play(state, registry, "p1", "lost_star")
    ok, reason = movement.can_move(new, grid, registry, "301", "destroyer", "p1")
    assert ok, reason
    moved = movement.move_ships(new, grid, registry, "301", "destroyer", 1, "p1")
    assert moved.systems["000"].space_units["p1"]["destroyer"] == 1
    after = _end_action(new)
    ok, _ = movement.can_move(after, grid, registry, "301", "destroyer", "p1")
    assert not ok  # efekt wygasł z końcem akcji
    # czyste sąsiedztwo grafu nietknięte (adjacency != traversability)
    assert not grid.are_adjacent("000", "301")


# --------------------------------------------------------------------------------- Nav Suite


def test_nav_suite_ignoruje_anomalie_w_kroku_ruchu(registry: StaticDataRegistry) -> None:
    grid = _grid(("000", "18", {"SUPERNOVA"}, []), ("101", "20", set(), []))
    state = _state({"p1": ["nav_suite"]})
    state.active_system = "000"
    state.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p1": {"destroyer": 1}}
    )
    assert not movement.can_move(state, grid, registry, "101", "destroyer", "p1")[0]
    new = _play(state, registry, "p1", "nav_suite")
    ok, reason = movement.can_move(new, grid, registry, "101", "destroyer", "p1")
    assert ok, reason
    # tylko krok Movement: w innym kroku efekt nie działa
    new.tactical_step = TacticalStep.INVASION
    assert not movement.can_move(new, grid, registry, "101", "destroyer", "p1")[0]


# ---------------------------------------------------------------------- In The Silence Of Space


def test_silence_space_przelot_przez_obce_statki_tylko_z_wybranego_systemu(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid(
        ("000", "18", set(), []), ("101", "20", set(), []),
        ("201", "21", set(), []), ("202", "22", set(), []),
    )
    state = _state({"p1": ["silence_space"]})
    state.active_system = "000"
    state.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p2": {"cruiser": 1}}
    )
    state.systems["201"] = SystemState(
        position="201", system_id="21", space_units={"p1": {"destroyer": 1}}
    )
    assert not movement.can_move(state, grid, registry, "201", "destroyer", "p1")[0]
    with pytest.raises(ValueError, match="contains 1 or more of your ships"):
        _play(state, registry, "p1", "silence_space", {"position": "101"})
    new = _play(state, registry, "p1", "silence_space", {"position": "201"})
    ok, reason = movement.can_move(new, grid, registry, "201", "destroyer", "p1")
    assert ok, reason
    # statki z INNEGO systemu nie dostają przywileju
    new.systems["202"] = SystemState(
        position="202", system_id="22", space_units={"p1": {"destroyer": 1}}
    )
    assert not movement.can_move(new, grid, registry, "202", "destroyer", "p1")[0]
    inputs = action_cards.card_inputs(state, registry, "p1", "silence_space")[1]
    assert [o["value"] for o in inputs[0]["options"]] == ["201"]


# -------------------------------------------------------------------------------- Solar Flare


def test_solar_flare_blokuje_space_cannon_offense_innych(registry: StaticDataRegistry) -> None:
    state = _state({"p1": ["solar_flare"]})
    state.systems[ACTIVE].space_units = {"p1": {"destroyer": 1}, "p2": {"destroyer": 1}}
    assert space_cannon.offense_targets(state, "p2") == ["p1"]
    new = _play(state, registry, "p1", "solar_flare")
    assert space_cannon.offense_targets(new, "p2") == []
    assert space_cannon.offense_targets(new, "p1") == ["p2"]  # aktywny gracz nadal strzela
    assert space_cannon.offense_targets(_end_action(new), "p2") == []  # brak aktywnego systemu
    expired = new.clone()
    triggers.fire(expired, GameEvent.TACTICAL_ACTION, Moment.END, subject="p1")
    assert space_cannon.offense_targets(expired, "p2") == ["p1"]


# ---------------------------------------------------------------------------- Harness Energy


def test_harness_tylko_dla_anomalii(registry: StaticDataRegistry) -> None:
    anomaly = next(s.id for s in registry.systems.values() if s.is_nebula)
    state = _state({"p1": ["harness"]}, system_id=anomaly)
    state.players["p1"].commodity_value = 3
    assert _playable(state, registry, "p1", "harness")
    new = _play(state, registry, "p1", "harness")
    assert new.players["p1"].commodities == 3
    plain = _state({"p1": ["harness"]})
    assert not _playable(plain, registry, "p1", "harness")
    with pytest.raises(ValueError, match="no open window"):
        _play(plain, registry, "p1", "harness")


# ---------------------------------------------------------------------------------------- Rally


def test_rally_wymaga_obcych_statkow_i_zamyka_sie_z_pierwszym_ruchem(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid(("000", "18", set(), []), ("101", "20", set(), []))
    state = _state({"p1": ["rally"], "p2": ["rally"]})
    state.active_system = "000"
    state.systems["000"] = SystemState(position="000", system_id="18", command_tokens=["p1"])
    state.players["p1"].cc_reinf = 5
    assert not _playable(state, registry, "p1", "rally")  # brak cudzych statków
    state.systems["000"].space_units = {"p2": {"cruiser": 1}}
    assert _playable(state, registry, "p1", "rally")
    assert not _playable(state, registry, "p2", "rally")  # „After YOU activate”
    new = _play(state, registry, "p1", "rally")
    assert new.players["p1"].fleet_cc == state.players["p1"].fleet_cc + 2
    assert new.players["p1"].cc_reinf == 3
    # prawdziwy ruch zamyka okno
    state.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p1": {"destroyer": 1}}
    )
    moved = movement.move_fleet(state, grid, registry, "101", {"destroyer": 1}, {}, "p1")
    assert moved.tactical_moved
    assert not _playable(moved, registry, "p1", "rally")


# -------------------------------------------------------------------------------------- Upgrade


def test_upgrade_zamienia_krazownik_na_dreadnought(registry: StaticDataRegistry) -> None:
    state = _state({"p1": ["upgrade"]})
    assert not _playable(state, registry, "p1", "upgrade")  # brak krążownika
    state.systems[ACTIVE].space_units = {"p1": {"cruiser": 2}}
    assert _playable(state, registry, "p1", "upgrade")
    new = _play(state, registry, "p1", "upgrade", {"source": ""})
    assert new.systems[ACTIVE].space_units["p1"] == {"cruiser": 1, "dreadnought": 1}
    with pytest.raises(ValueError, match="where the dreadnought comes from"):
        _play(state, registry, "p1", "upgrade", {"source": "999"})


def test_upgrade_bez_dreadnoughta_w_rezerwie_zdejmuje_z_planszy(
    registry: StaticDataRegistry,
) -> None:
    state = _state({"p1": ["upgrade"]})
    state.systems[ACTIVE].space_units = {"p1": {"cruiser": 1}}
    state.systems["102"] = SystemState(
        position="102", system_id="20", space_units={"p1": {"dreadnought": 5}}
    )
    assert _playable(state, registry, "p1", "upgrade")
    inputs = action_cards.card_inputs(state, registry, "p1", "upgrade")[1]
    assert [o["value"] for o in inputs[0]["options"]] == ["102"]
    new = _play(state, registry, "p1", "upgrade", {"source": "102"})
    assert new.systems["102"].space_units["p1"]["dreadnought"] == 4
    assert new.systems[ACTIVE].space_units["p1"] == {"dreadnought": 1}
    state.systems["102"].command_tokens = ["p1"]  # system z własnym żetonem odpada
    assert not _playable(state, registry, "p1", "upgrade")


# --------------------------------------------------------------------------------- Counterstroke


def test_counterstroke_zwraca_zeton_do_puli_taktycznej(registry: StaticDataRegistry) -> None:
    state = _state({"p1": ["counterstroke"], "p2": ["counterstroke"], "p3": ["counterstroke"]})
    state.systems[ACTIVE].command_tokens = ["p1", "p2"]
    assert _playable(state, registry, "p2", "counterstroke")
    assert not _playable(state, registry, "p1", "counterstroke")  # „another player activates”
    assert not _playable(state, registry, "p3", "counterstroke")  # brak żetonu p3
    before = state.players["p2"].tactical_cc
    new = _play(state, registry, "p2", "counterstroke")
    assert new.systems[ACTIVE].command_tokens == ["p1"]
    assert new.players["p2"].tactical_cc == before + 1
    state.tactical_moved = True
    assert not _playable(state, registry, "p2", "counterstroke")


# --------------------------------------------------------------------------- Decoy Operation


def test_decoy_przenosi_sily_naziemne_na_planete_w_aktywnym_systemie(
    registry: StaticDataRegistry,
) -> None:
    state = _state({"p2": ["decoy"]})
    system = state.systems[ACTIVE]
    system.planet_owners = {"mr": "p2"}
    system.planet_units = {"mr": {"p2": {"pds": 1}}}
    assert not _playable(state, registry, "p2", "decoy")  # brak sił naziemnych do przeniesienia
    state.systems["102"] = SystemState(
        position="102",
        system_id="19",
        planet_owners={"wellon": "p2"},
        planet_units={"wellon": {"p2": {"infantry": 3}}},
    )
    assert _playable(state, registry, "p2", "decoy")
    units = [{"planet": "wellon", "base_type": "infantry"}] * 2
    new = _play(state, registry, "p2", "decoy", {"planet": "mr", "units": units})
    assert new.systems["102"].planet_units["wellon"]["p2"]["infantry"] == 1
    assert new.systems[ACTIVE].planet_units["mr"]["p2"] == {"pds": 1, "infantry": 2}
    with pytest.raises(ValueError, match="planet you control in the active system"):
        _play(state, registry, "p2", "decoy", {"planet": "wellon", "units": units})
    with pytest.raises(ValueError, match="1 or 2"):
        _play(state, registry, "p2", "decoy", {"planet": "mr", "units": units * 2})


# -------------------------------------------------------------------------- Forward Supply Base


def test_fsb_daje_3_tg_i_1_tg_wskazanemu_graczowi(registry: StaticDataRegistry) -> None:
    state = _state({"p2": ["fsb"], "p3": ["fsb"]})
    state.systems[ACTIVE].space_units = {"p2": {"destroyer": 1}}
    assert _playable(state, registry, "p2", "fsb")
    assert not _playable(state, registry, "p3", "fsb")  # brak jednostek p3 w systemie
    new = _play(state, registry, "p2", "fsb", {"player": "p3"})
    assert new.players["p2"].trade_goods == state.players["p2"].trade_goods + 3
    assert new.players["p3"].trade_goods == state.players["p3"].trade_goods + 1
    with pytest.raises(ValueError, match="another player"):
        _play(state, registry, "p2", "fsb", {"player": "p2"})


# ------------------------------------------------------------------------------------- Rescue


def test_rescue_po_ruchu_przenosi_statek_do_aktywnego_systemu(registry: StaticDataRegistry) -> None:
    grid = _grid(("000", "18", set(), []), ("101", "20", set(), []), ("104", "21", set(), []))
    state = _state({"p1": ["rescue"], "p2": ["rescue"]})
    state.active_system = "000"
    state.systems["000"] = SystemState(
        position="000", system_id="18", command_tokens=["p1"], space_units={"p2": {"cruiser": 1}}
    )
    state.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p1": {"destroyer": 1}}
    )
    state.systems["104"] = SystemState(
        position="104", system_id="21", space_units={"p2": {"destroyer": 1}}
    )
    assert not _playable(state, registry, "p2", "rescue")  # nikt jeszcze nie ruszył
    moved = movement.move_fleet(state, grid, registry, "101", {"destroyer": 1}, {}, "p1")
    assert _playable(moved, registry, "p2", "rescue")
    windows = reaction_cards.open_windows(moved)
    assert any(w.event is GameEvent.SHIPS_MOVED and w.moment is Moment.AFTER for w in windows)
    inputs = action_cards.card_inputs(moved, registry, "p2", "rescue")[1]
    assert [o["value"] for o in inputs[0]["options"]] == [
        {"from": "104", "base_type": "destroyer"}
    ]
    new = _play(moved, registry, "p2", "rescue", {"from": "104", "base_type": "destroyer"})
    assert new.systems["000"].space_units["p2"] == {"cruiser": 1, "destroyer": 1}
    assert "104" not in new.systems or not new.systems["104"].space_units.get("p2")
    with pytest.raises(ValueError, match="without your command token"):
        _play(moved, registry, "p2", "rescue", {"from": "000", "base_type": "cruiser"})
    # system ze STRZEGĄCYM żetonem p2 odpada z opcji
    moved.systems["104"].command_tokens = ["p2"]
    assert not _playable(moved, registry, "p2", "rescue")
    # p1 (ruszający) nie może zagrać „another player moves”
    assert not _playable(moved, registry, "p1", "rescue")


# ---------------------------------------------------------------------------------- War Machine


def _production_state(registry: StaticDataRegistry) -> tuple[GameState, HexGrid]:
    state = _state({"p1": ["war_machine1", "war_machine2"]}, step=TacticalStep.PRODUCTION)
    state.active_system = "000"
    state.systems.pop(ACTIVE)
    state.systems["000"] = SystemState(
        position="000",
        system_id="20",
        command_tokens=["p1"],
        planet_owners={"vefutii": "p1"},
        planet_units={"vefutii": {"p1": {"spacedock": 1}}},
    )
    return state, _grid(("000", "20", set(), []))


def test_war_machine_dodaje_4_do_sumy_production_i_obniza_koszt(
    registry: StaticDataRegistry,
) -> None:
    state, grid = _production_state(registry)
    base = production.production_limit(state, grid, registry, "p1")
    assert base > 0
    assert _playable(state, registry, "p1", "war_machine1")
    new = _play(state, registry, "p1", "war_machine1")
    assert production.production_limit(new, grid, registry, "p1") == base + 4
    assert production.cost_reduction(new, "p1") == 1
    assert production.cost_reduction(state, "p1") == 0
    # ruling: druga War Machine w tej samej produkcji nie sumuje się
    assert not _playable(new, registry, "p1", "war_machine2")
    # efekt wygasa z akcją taktyczną
    expired = new.clone()
    triggers.fire(expired, GameEvent.TACTICAL_ACTION, Moment.END, subject="p1")
    assert production.production_limit(expired, grid, registry, "p1") == base


def test_war_machine_okno_tylko_przed_produkcja_i_dla_producenta(
    registry: StaticDataRegistry,
) -> None:
    state, _grid_ = _production_state(registry)
    state.production_used = 1  # produkcja już trwa - „when" minęło
    assert not _playable(state, registry, "p1", "war_machine1")
    state.production_used = 0
    state.tactical_step = TacticalStep.MOVEMENT
    assert not _playable(state, registry, "p1", "war_machine1")
    state.tactical_step = TacticalStep.PRODUCTION
    state.systems["000"].planet_units = {}
    assert not _playable(state, registry, "p1", "war_machine1")  # brak jednostki z PRODUCTION


def test_premia_do_sumy_nie_tworzy_produkcji_bez_producenta(registry: StaticDataRegistry) -> None:
    state, grid = _production_state(registry)
    state.systems["000"].planet_units = {}
    new = state.clone()
    from src.core import active_effects
    from src.core.game_events import Duration

    active_effects.add_effect(new, "action_cards:war_machine", Duration.TURN, owner="p1")
    assert production.production_limit(new, grid, registry, "p1") == 0


# ------------------------------------------------------------------------ Infiltrate / Reparations


def _capture_state() -> GameState:
    """p1 zdobywa planetę mr po p2, który ma tam PDS i space dock; p2 miał też inną, wyczerpaną."""
    state = _state(
        {
            "p1": ["infiltrate", "reparations"],
            "p2": ["reparations"],
            "p3": ["infiltrate", "reparations"],
        }
    )
    system = state.systems[ACTIVE]
    system.planet_owners = {"mr": "p2"}
    system.planet_units = {"mr": {"p2": {"pds": 1, "spacedock": 1}}}
    state.players["p2"].controlled_planets = ["mr"]
    state.systems["103"] = SystemState(
        position="103", system_id="25", planet_owners={"quann": "p2"}
    )
    state.systems["102"] = SystemState(
        position="102", system_id="19", planet_owners={"wellon": "p1"}
    )
    state.players["p2"].exhausted_planets = ["quann"]
    return state


def test_zmiana_kontroli_zostawia_slad_czyszczony_z_akcja() -> None:
    state = _capture_state()
    control.set_planet_control(state, ACTIVE, "mr", "p1")
    assert state.control_changes == [
        {"planet": "mr", "position": ACTIVE, "player": "p1", "previous": "p2"}
    ]
    ended = _end_action(state)
    assert ended.control_changes == []


def test_infiltrate_zamienia_struktury_na_swoje_z_rezerwy(registry: StaticDataRegistry) -> None:
    state = _capture_state()
    assert not _playable(state, registry, "p1", "infiltrate")  # nic jeszcze nie zdobyto
    control.set_planet_control(state, ACTIVE, "mr", "p1")
    assert _playable(state, registry, "p1", "infiltrate")
    assert not _playable(state, registry, "p3", "infiltrate")
    new = _play(state, registry, "p1", "infiltrate", {"planet": "mr"})
    units = new.systems[ACTIVE].planet_units["mr"]
    assert units["p1"] == {"pds": 1, "spacedock": 1}
    assert not units.get("p2")
    with pytest.raises(ValueError, match="planet whose control was just gained"):
        _play(state, registry, "p1", "infiltrate", {"planet": "wellon"})
    # po zakończeniu akcji okno znika
    assert not _playable(_end_action(state), registry, "p1", "infiltrate")


def test_infiltrate_bez_struktur_w_rezerwie_to_blad_bez_zmian(
    registry: StaticDataRegistry,
) -> None:
    state = _capture_state()
    # cała rezerwa PDS p1 stoi już na planszy
    state.systems["102"].planet_units = {"wellon": {"p1": {"pds": 6}}}
    control.set_planet_control(state, ACTIVE, "mr", "p1")
    with pytest.raises(ValueError, match="reinforcements"):
        _play(state, registry, "p1", "infiltrate", {"planet": "mr"})
    assert state.systems[ACTIVE].planet_units["mr"]["p2"] == {"pds": 1, "spacedock": 1}


def test_reparations_wyczerpuje_planete_zdobywcy_i_odswieza_wlasna(
    registry: StaticDataRegistry,
) -> None:
    state = _capture_state()
    assert not _playable(state, registry, "p2", "reparations")
    control.set_planet_control(state, ACTIVE, "mr", "p1")
    assert _playable(state, registry, "p2", "reparations")
    assert not _playable(state, registry, "p3", "reparations")  # to nie jego planeta
    assert not _playable(state, registry, "p1", "reparations")  # „another player gains control”
    params = {"planet": "mr", "exhaust_planet": "wellon", "ready_planet": "quann"}
    new = _play(state, registry, "p2", "reparations", params)
    assert "wellon" in new.players["p1"].exhausted_planets
    assert "quann" not in new.players["p2"].exhausted_planets
    with pytest.raises(ValueError, match="ready planet controlled by that player"):
        _play(state, registry, "p2", "reparations", {**params, "exhaust_planet": ""})
    with pytest.raises(ValueError, match="exhausted planets"):
        _play(state, registry, "p2", "reparations", {**params, "ready_planet": "mr"})


def test_reparations_bez_celow_jest_dozwolone(registry: StaticDataRegistry) -> None:
    """Ruling: można zagrać bez wyczerpanej planety / gdy zdobywca nie ma gotowej planety."""
    state = _capture_state()
    state.players["p2"].exhausted_planets = []
    state.systems["102"].planet_owners = {}  # zdobywca nie ma innej planety do wyczerpania
    control.set_planet_control(state, ACTIVE, "mr", "p1")
    state.players["p1"].exhausted_planets = ["mr"]  # świeżo zdobyta jest już wyczerpana
    assert _playable(state, registry, "p2", "reparations")
    params = {"planet": "mr", "exhaust_planet": "", "ready_planet": ""}
    new = _play(state, registry, "p2", "reparations", params)
    assert new.players["p2"].private.action_cards == []


# ---------------------------------------------------------------------- okna po aktywacji


def test_okna_po_aktywacji_zamykaja_sie_z_pierwszym_ruchem(registry: StaticDataRegistry) -> None:
    state = _state({"p1": ["lost_star", "nav_suite"]})
    assert _playable(state, registry, "p1", "lost_star")
    state.tactical_moved = True
    assert not _playable(state, registry, "p1", "lost_star")
    assert not _playable(state, registry, "p1", "nav_suite")
