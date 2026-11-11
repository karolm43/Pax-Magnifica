"""Testy kart reakcji grupy „invasion” (RULES.md 53.5.d): inwazja, Bombardment, Space Cannon."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from src.core import (
    action_cards,
    active_effects,
    board_graph,
    invasion,
    reaction_cards,
    rules_hooks,
    space_cannon,
    tactical,
    timing,
)
from src.core.components import ComponentCategory
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    InvasionPhase,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.invasion import BombardAssignment
from src.core.registry import StaticDataRegistry

_TILE = "09"  # dwie planety: maaluuk i druaa
_PL1 = "maaluuk"
_PL2 = "druaa"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", _TILE, anomalies=set())
    grid.place_system("101", "20", anomalies=set())
    grid.build_edges()
    return grid


@pytest.fixture
def grid() -> Iterator[HexGrid]:
    built = _grid()
    board_graph.bind_grid_provider(lambda: built)
    yield built
    board_graph.bind_grid_provider(None)


def _state(
    space: dict[str, dict[str, int]] | None = None,
    planets: dict[str, dict[str, dict[str, int]]] | None = None,
    owners: dict[str, str] | None = None,
    *,
    seed: int = 1,
    step: TacticalStep = TacticalStep.INVASION,
) -> GameState:
    """Aktywny p1 (atakujący) w kroku ``step``; ``planets`` = ``{planeta: {gracz: {typ: n}}}``."""
    system = SystemState(position="000", system_id=_TILE)
    for pid, by_type in (space or {}).items():
        system.space_units[pid] = dict(by_type)
    for planet, by_player in (planets or {}).items():
        for pid, by_type in by_player.items():
            system.planet_units.setdefault(planet, {})[pid] = dict(by_type)
    system.planet_owners = dict(owners or {})
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=step,
        seating_order=["p1", "p2"],
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2")},
        systems={"000": system},
        rng_seed=seed,
    )


def _hand(state: GameState, player: str, *cards: str) -> None:
    state.players[player].private.action_cards = list(cards)


def _row(
    state: GameState, registry: StaticDataRegistry, player: str, card: str
) -> dict[str, Any]:
    rows = action_cards.playability(state, registry, player)
    return next(row for row in rows if row["card_id"] == card)


def _play(
    state: GameState,
    registry: StaticDataRegistry,
    player: str,
    card: str,
    params: dict[str, Any] | None = None,
) -> GameState:
    new, implemented = action_cards.play_action_card(state, registry, player, card, params or {})
    assert implemented
    return new


def _begin(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    started = invasion.begin_invasion(state, grid, registry)
    assert started.invasion is not None
    return started


def _seek(
    make: Callable[[int], GameState], ok: Callable[[GameState], bool], limit: int = 400
) -> GameState:
    """Szuka ziarna, przy którym przebieg daje oczekiwany wynik (rzuty są deterministyczne)."""
    for seed in range(1, limit):
        try:
            candidate = make(seed)
        except ValueError:
            continue
        if ok(candidate):
            return candidate
    raise AssertionError("no seed produced the expected outcome")


def _no_window(state: GameState, registry: StaticDataRegistry, player: str, card: str) -> None:
    row = _row(state, registry, player, card)
    assert not row["playable"]
    assert "no open window" in str(row["reason"]).lower()


# ---------------------------------------------------------------------- początek inwazji


def _blitz_state(grid: HexGrid, registry: StaticDataRegistry, ships: dict[str, int]) -> GameState:
    state = _state(
        {"p1": {**ships, "infantry": 2}},
        {_PL1: {"p2": {"infantry": 2}}},
        {_PL1: "p2"},
    )
    _hand(state, "p1", "blitz")
    _hand(state, "p2", "blitz")
    return _begin(state, grid, registry)


def test_blitz_okno_i_adresat(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _blitz_state(grid, registry, {"cruiser": 1})
    assert state.invasion is not None and state.invasion.phase is InvasionPhase.COMMIT
    assert _row(state, registry, "p1", "blitz")["playable"]
    assert not _row(state, registry, "p2", "blitz")["playable"]  # „Your ships” - tylko atakujący
    # Po zaangażowaniu sił „początek inwazji” minął.
    landed = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 1}})
    _no_window(landed, registry, "p1", "blitz")


def test_blitz_niezagrywalny_bez_niefighterowego_statku(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _blitz_state(grid, registry, {"fighter": 2})
    row = _row(state, registry, "p1", "blitz")
    assert not row["playable"]
    assert "no open window" in str(row["reason"]).lower()


def test_blitz_nadaje_bombardment_statkom_bez_niego(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _blitz_state(grid, registry, {"cruiser": 2, "fighter": 3})
    assert not invasion.bombard_groups(state, registry)
    played = _play(state, registry, "p1", "blitz")
    assert played.invasion is not None
    assert played.invasion.phase is InvasionPhase.BOMBARDMENT  # silnik wraca do Bombardment
    groups = invasion.bombard_groups(played, registry)
    assert [(g.base_type, g.count, g.hits_on) for g in groups] == [("cruiser", 2, 6)]

    def run(seed: int) -> GameState:
        copy = played.clone()
        copy.rng_seed = seed
        return invasion.bombard(copy, grid, registry, [BombardAssignment("cruiser", _PL1, 2)])

    after = run(5)
    assert after.invasion is not None and after.invasion.bombarded
    assert after.invasion.log[0]["rolls"][0]["hitsOn"] == 6
    assert len(after.invasion.log[0]["rolls"][0]["dice"]) == 2  # 1 kość na statek


def test_blitz_nie_zmienia_wlasnego_bombardment_i_wygasa_z_inwazja(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _begin(
        _state(
            {"p1": {"dreadnought": 1, "cruiser": 1, "infantry": 1}},
            {_PL1: {"p2": {"infantry": 2}}},
            {_PL1: "p2"},
        ),
        grid,
        registry,
    )
    _hand(state, "p1", "blitz")
    assert state.invasion is not None and state.invasion.phase is InvasionPhase.BOMBARDMENT
    base = {g.base_type: g.hits_on for g in invasion.bombard_groups(state, registry)}
    assert base == {"dreadnought": base["dreadnought"]}  # krążownik jeszcze nie bombarduje
    played = _play(state, registry, "p1", "blitz")
    boosted = {g.base_type: g.hits_on for g in invasion.bombard_groups(played, registry)}
    assert boosted["dreadnought"] == base["dreadnought"]  # własne Bombardment bez zmian
    assert boosted["cruiser"] == 6
    assert active_effects.has_effect(played, "p1", "action_cards:blitz")
    closed = invasion.clear_invasion(played)  # INVASION / END
    assert closed.invasion is None
    assert not active_effects.has_effect(closed, "p1", "action_cards:blitz")


def test_bunker_odejmuje_4_od_wyniku_bombardowania(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _begin(
        _state(
            {"p1": {"dreadnought": 3, "infantry": 1}},
            {_PL1: {"p2": {"infantry": 4}}},
            {_PL1: "p2"},
        ),
        grid,
        registry,
    )
    _hand(state, "p1", "bunker")
    _hand(state, "p2", "bunker")
    assert not _row(state, registry, "p1", "bunker")["playable"]  # atakujący nie broni planet
    assert _row(state, registry, "p2", "bunker")["playable"]
    played = _play(state, registry, "p2", "bunker")
    assert rules_hooks.modify(
        rules_hooks.POINT_BOMBARDMENT_ROLL_MODIFIER, played, "p2", 0, {"planet": _PL1}
    ) == -4
    assert rules_hooks.modify(
        rules_hooks.POINT_BOMBARDMENT_ROLL_MODIFIER, played, "p1", 0, {"planet": _PL1}
    ) == 0

    def sample(base: GameState) -> Callable[[int], GameState]:
        def make(seed: int) -> GameState:
            copy = base.clone()
            copy.rng_seed = seed
            plan = [BombardAssignment("dreadnought", _PL1, 3)]
            return invasion.bombard(copy, grid, registry, plan)

        return make

    plain, shielded = sample(state), sample(played)
    for seed in range(1, 40):
        free = plain(seed).invasion
        covered = shielded(seed).invasion
        assert free is not None and covered is not None
        roll = covered.log[0]["rolls"][0]
        assert roll["modifier"] == -4
        hits_on = roll["hitsOn"]
        assert covered.log[0]["hits"] == sum(1 for d in roll["dice"] if d - 4 >= hits_on)
        assert covered.log[0]["hits"] <= free.log[0]["hits"]  # te same kości, mniej trafień


def test_bunker_wygasa_z_inwazja(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _begin(
        _state(
            {"p1": {"dreadnought": 1, "infantry": 1}},
            {_PL1: {"p2": {"infantry": 2}}},
            {_PL1: "p2"},
        ),
        grid,
        registry,
    )
    _hand(state, "p2", "bunker")
    played = _play(state, registry, "p2", "bunker")
    closed = invasion.clear_invasion(played)
    assert rules_hooks.modify(
        rules_hooks.POINT_BOMBARDMENT_ROLL_MODIFIER, closed, "p2", 0, {"planet": _PL1}
    ) == 0


def test_bunker_wymaga_planety_w_systemie(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _begin(
        _state(
            {"p1": {"dreadnought": 1, "infantry": 1}},
            {_PL1: {"p2": {"infantry": 2}}},
            {},  # nikt nie kontroluje planety
        ),
        grid,
        registry,
    )
    _hand(state, "p2", "bunker")
    _no_window(state, registry, "p2", "bunker")


def _pds_state(grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    state = _state(
        {"p1": {"dreadnought": 1, "infantry": 2}},
        {_PL1: {"p2": {"infantry": 2, "pds": 1}}},
        {_PL1: "p2"},
    )
    _hand(state, "p1", "disable")
    _hand(state, "p2", "disable")
    return _begin(state, grid, registry)


def test_disable_zdejmuje_tarcze_i_space_cannon_pds(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _pds_state(grid, registry)
    assert state.invasion is not None and state.invasion.phase is InvasionPhase.COMMIT
    assert next(i for i in invasion.planet_infos(state, registry) if i.planet == _PL1).shielded
    assert space_cannon.zone_shooters(state, registry, "p2", "000", _PL1)
    assert not _row(state, registry, "p2", "disable")["playable"]  # „your opponents' PDS”
    played = _play(state, registry, "p1", "disable")
    info = next(i for i in invasion.planet_infos(played, registry) if i.planet == _PL1)
    assert not info.shielded and not info.has_shield and not info.has_space_cannon
    assert not space_cannon.zone_shooters(played, registry, "p2", "000", _PL1)
    # Bez tarczy można bombardować, więc silnik wraca do kroku Bombardment.
    assert played.invasion is not None and played.invasion.phase is InvasionPhase.BOMBARDMENT
    assert invasion.bombard_groups(played, registry)
    # Efekt dotyczy wyłącznie PDS (nie innych jednostek) i znika z końcem inwazji.
    closed = invasion.clear_invasion(played)
    assert space_cannon.zone_shooters(closed, registry, "p2", "000", _PL1)


def test_disable_wymaga_pds_przeciwnika(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _state(
        {"p1": {"dreadnought": 1, "infantry": 2}},
        {_PL1: {"p2": {"infantry": 2}}},
        {_PL1: "p2"},
    )
    _hand(state, "p1", "disable")
    started = _begin(state, grid, registry)
    _no_window(started, registry, "p1", "disable")


def test_disable_wylacza_space_cannon_defense(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _pds_state(grid, registry)
    played = _play(state, registry, "p1", "disable")
    moved = invasion.advance(played, grid, registry)  # Bombardment -> Commit
    moved = invasion.commit_ground_forces(moved, registry, {_PL1: {"infantry": 2}})
    assert not invasion.defense_planets(moved, registry)


# ----------------------------------------------------------- po zaangażowaniu: Ghost, Parley


def _commit_state(grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    state = _state(
        {"p1": {"infantry": 3}},
        {
            _PL1: {"p2": {"infantry": 2}},
            _PL2: {"p2": {"infantry": 3, "mech": 1}},
        },
        {_PL1: "p2", _PL2: "p2"},
    )
    _hand(state, "p1", "ghost_squad", "parley")
    _hand(state, "p2", "ghost_squad", "parley")
    return _begin(state, grid, registry)


def test_okno_po_zaangazowaniu_otwarte_tylko_po_ladowaniu(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _commit_state(grid, registry)
    for card in ("ghost_squad", "parley"):
        _no_window(state, registry, "p2", card)
    landed = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 2}})
    for card in ("ghost_squad", "parley"):
        assert _row(landed, registry, "p2", card)["playable"]
        assert not _row(landed, registry, "p1", card)["playable"]  # „another player”
    moved = invasion.advance(landed, grid, registry)
    for card in ("ghost_squad", "parley"):
        _no_window(moved, registry, "p2", card)


def test_ghost_squad_wymaga_wladania_planeta_z_ladowaniem(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _commit_state(grid, registry)
    state.systems["000"].planet_owners[_PL1] = "p1"  # p2 nie kontroluje planety z lądowaniem
    landed = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 1}})
    _no_window(landed, registry, "p2", "ghost_squad")
    _no_window(landed, registry, "p2", "parley")


def test_ghost_squad_przenosi_sily_miedzy_swoimi_planetami(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = invasion.commit_ground_forces(
        _commit_state(grid, registry), registry, {_PL1: {"infantry": 2}}
    )
    inputs = action_cards.card_inputs(state, registry, "p2", "ghost_squad")[1]
    keys = {item["key"] for item in inputs}
    assert keys == {"to_planet", "units"}
    units = next(item for item in inputs if item["key"] == "units")
    assert len(units["options"]) == 2 + 3 + 1  # 2 piechoty na maaluuk + 3 piechoty i mech na druaa
    params = {
        "to_planet": _PL1,
        "units": [
            {"planet": _PL2, "base_type": "infantry"},
            {"planet": _PL2, "base_type": "infantry"},
            {"planet": _PL2, "base_type": "mech"},
        ],
    }
    new = _play(state, registry, "p2", "ghost_squad", params)
    system = new.systems["000"]
    assert system.planet_units[_PL1]["p2"] == {"infantry": 4, "mech": 1}
    assert system.planet_units[_PL2]["p2"]["infantry"] == 1
    assert system.planet_units[_PL1]["p1"] == {"infantry": 2}  # zaangażowanie atakującego bez zmian
    assert new.players["p2"].private.action_cards == ["parley"]


def test_ghost_squad_zero_sil_i_bledy(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = invasion.commit_ground_forces(
        _commit_state(grid, registry), registry, {_PL1: {"infantry": 2}}
    )
    nothing = _play(state, registry, "p2", "ghost_squad", {"units": []})
    assert nothing.systems["000"].planet_units == state.systems["000"].planet_units
    bad: list[dict[str, Any]] = [
        {"to_planet": _PL1, "units": [{"planet": _PL1, "base_type": "infantry"}]},  # ta sama
        {
            "to_planet": _PL1,
            "units": [
                {"planet": _PL2, "base_type": "infantry"},
                {"planet": _PL1, "base_type": "infantry"},
            ],
        },  # dwie planety źródłowe
        {"to_planet": _PL2, "units": [{"planet": _PL1, "base_type": "mech"}]},  # brak mecha
        {"to_planet": "nowhere", "units": [{"planet": _PL1, "base_type": "infantry"}]},
        {"to_planet": _PL1, "units": [{"planet": _PL2, "base_type": "pds"}]},  # nie siła naziemna
    ]
    for params in bad:
        with pytest.raises(ValueError):
            action_cards.play_action_card(state, registry, "p2", "ghost_squad", params)
    assert state.players["p2"].private.action_cards == ["ghost_squad", "parley"]


def test_parley_zwraca_zaangazowane_do_przestrzeni(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = invasion.commit_ground_forces(
        _commit_state(grid, registry), registry, {_PL1: {"infantry": 2}}
    )
    new = _play(state, registry, "p2", "parley", {"planet": _PL1})
    system = new.systems["000"]
    assert system.space_units["p1"]["infantry"] == 3
    assert not system.planet_units[_PL1].get("p1")
    assert new.invasion is not None
    assert new.invasion.committed == {}
    assert new.invasion.parley_locked == {"infantry": 2}
    # Zwrócone siły nie mogą lądować na inną planetę w tej akcji; reszta może.
    with pytest.raises(ValueError, match="Only 1 infantry"):
        invasion.commit_ground_forces(new, registry, {_PL2: {"infantry": 2}})
    again = invasion.commit_ground_forces(new, registry, {_PL2: {"infantry": 1}})
    assert again.invasion is not None and again.invasion.committed == {_PL2: {"infantry": 1}}


def test_parley_dotyczy_tylko_jednej_planety(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _commit_state(grid, registry)
    state = invasion.commit_ground_forces(
        state, registry, {_PL1: {"infantry": 1}, _PL2: {"infantry": 2}}
    )
    options = action_cards.card_inputs(state, registry, "p2", "parley")[1][0]["options"]
    assert {o["value"] for o in options} == {_PL1, _PL2}
    new = _play(state, registry, "p2", "parley", {"planet": _PL2})
    assert new.invasion is not None
    assert new.invasion.committed == {_PL1: {"infantry": 1}}
    assert new.invasion.last_commit == {_PL1: {"infantry": 1}}  # druga planeta wciąż w oknie
    for params in ({}, {"planet": "nowhere"}):
        with pytest.raises(ValueError):
            action_cards.play_action_card(state, registry, "p2", "parley", params)


# -------------------------------------------------------------------- Maneuvering Jets


def _sc_state(seed: int, pds: int = 3, ships: int = 4) -> GameState:
    """Space Cannon Offense: p2 ma PDS na planecie aktywnego systemu, p1 statki."""
    state = _state(
        {"p1": {"destroyer": ships}},
        {_PL1: {"p2": {"pds": pds}}},
        {_PL1: "p2"},
        seed=seed,
        step=TacticalStep.SPACE_CANNON,
    )
    _hand(state, "p1", "mjets1", "scramble")
    _hand(state, "p2", "mjets1", "scramble")
    return space_cannon.open_offense(state, _grid(), StaticDataRegistry())


def _fired(seed: int, registry: StaticDataRegistry, pds: int = 3, ships: int = 4) -> GameState:
    return space_cannon.fire_offense(_sc_state(seed, pds, ships), _grid(), registry, "p2", "p1")


def _pending_hits(state: GameState) -> int:
    pending = space_cannon.pending_hits(state)
    return pending.hits if pending is not None else 0


def test_mjets_offense_okno_tylko_dla_celu(registry: StaticDataRegistry) -> None:
    open_state = _sc_state(1)
    for player in ("p1", "p2"):
        for card in ("mjets1", "scramble"):
            _no_window(open_state, registry, player, card)  # nikt jeszcze nie rzucił
    fired = _seek(lambda s: _fired(s, registry), lambda st: _pending_hits(st) >= 1)
    assert _row(fired, registry, "p1", "mjets1")["playable"]
    assert not _row(fired, registry, "p2", "mjets1")["playable"]  # to jego własne trafienia


def test_mjets_offense_anuluje_jedno_trafienie(registry: StaticDataRegistry) -> None:
    many = _seek(lambda s: _fired(s, registry), lambda st: _pending_hits(st) >= 2)
    before = _pending_hits(many)
    new = _play(many, registry, "p1", "mjets1")
    assert _pending_hits(new) == before - 1
    assert space_cannon.read_log(new)[-1]["hits"] == before - 1
    assert space_cannon.read_log(new)[-1]["cancelled"] == 1
    assert new.players["p1"].private.action_cards == ["scramble"]
    # Pozostałe trafienia przypisuje się normalnie.
    done = space_cannon.assign_hits(new, "p1", {"destroyer": before - 1})
    assert done.pending_window is None
    assert done.systems["000"].space_units["p1"]["destroyer"] == 4 - (before - 1)


def test_mjets_offense_ostatnie_trafienie_konczy_tury_strzelca(
    registry: StaticDataRegistry,
) -> None:
    single = _seek(lambda s: _fired(s, registry, pds=1), lambda st: _pending_hits(st) == 1)
    new = _play(single, registry, "p1", "mjets1")
    assert new.pending_window is None  # nie ma co przypisywać, okno przeszło dalej
    assert new.systems["000"].space_units["p1"]["destroyer"] == 4
    assert space_cannon.read_log(new)[-1]["hits"] == 0


def test_mjets_nie_dziala_na_cudzych_trafieniach_walki(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"destroyer": 1}}, step=TacticalStep.MOVEMENT)
    _hand(state, "p1", "mjets1")
    _no_window(state, registry, "p1", "mjets1")


def _defense_state(seed: int, registry: StaticDataRegistry, grid: HexGrid) -> GameState:
    state = _state(
        {"p1": {"infantry": 6}},
        {_PL1: {"p2": {"infantry": 1, "pds": 3}}},
        {_PL1: "p2"},
        seed=seed,
    )
    _hand(state, "p1", "mjets2", "scramble")
    _hand(state, "p2", "mjets2", "scramble")
    started = _begin(state, grid, registry)
    landed = invasion.commit_ground_forces(started, registry, {_PL1: {"infantry": 6}})
    entered = invasion.advance(landed, grid, registry)
    assert entered.invasion is not None
    assert entered.invasion.phase is InvasionPhase.SPACE_CANNON_DEFENSE
    return invasion.defense_fire(entered, grid, registry, _PL1)


def _defense_hits(state: GameState) -> int:
    return state.invasion.defense_pending.get(_PL1, 0) if state.invasion else 0


def test_mjets_defense_anuluje_trafienie(grid: HexGrid, registry: StaticDataRegistry) -> None:
    fired = _seek(lambda s: _defense_state(s, registry, grid), lambda st: _defense_hits(st) >= 2)
    hits = _defense_hits(fired)
    assert _row(fired, registry, "p1", "mjets2")["playable"]
    assert not _row(fired, registry, "p2", "mjets2")["playable"]
    new = _play(fired, registry, "p1", "mjets2")
    assert _defense_hits(new) == hits - 1
    assert new.invasion is not None and new.invasion.log[-1]["cancelled"] == 1
    assert invasion.required_defense_hits(new, grid, registry, _PL1) == hits - 1


def test_mjets_defense_ostatnie_trafienie_rozstrzyga_planete(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    single = _seek(lambda s: _defense_state(s, registry, grid), lambda st: _defense_hits(st) == 1)
    new = _play(single, registry, "p1", "mjets2")
    assert new.invasion is not None
    assert new.invasion.defense_pending == {}
    assert _PL1 in new.invasion.defense_resolved
    assert invasion.advance(new, grid, registry).invasion is not None  # można iść dalej


# -------------------------------------------------------------------- Scramble Frequency


def test_scramble_offense_przerzuca_wszystkie_kosci(registry: StaticDataRegistry) -> None:
    fired = _seek(lambda s: _fired(s, registry), lambda st: _pending_hits(st) >= 1)
    pending = space_cannon.pending_hits(fired)
    assert pending is not None
    before = [d for roll in pending.rolls for d in roll["dice"]]
    assert _row(fired, registry, "p1", "scramble")["playable"]
    assert not _row(fired, registry, "p2", "scramble")["playable"]  # „another player”
    new = _play(fired, registry, "p1", "scramble")
    assert new.rng_counter == fired.rng_counter + 1  # jeden przerzut z tego samego RNG
    assert new.table_roll_seq == fired.table_roll_seq + 1
    assert new.table_roll is not None and new.table_roll["kind"] == "scramble_frequency"
    log = space_cannon.read_log(new)[-1]
    assert log["rerolled"] is True
    fresh_dice = log["rolls"][0]["dice"]
    assert len(fresh_dice) == len(before)
    assert new.table_roll["dice"] == fresh_dice
    expected = sum(1 for d in fresh_dice if d >= log["rolls"][0]["hitsOn"])
    assert log["hits"] == expected
    if expected:
        assert _pending_hits(new) == expected
    else:
        assert new.pending_window is None  # po przerzucie bez trafień nic do przypisania


def test_scramble_offense_zamyka_okno_przy_zerze_trafien(registry: StaticDataRegistry) -> None:
    def zero(st: GameState) -> bool:
        try:
            log = space_cannon.read_log(_play(st, registry, "p1", "scramble"))
            return int(log[-1]["hits"]) == 0
        except ValueError:
            return False

    fired = _seek(lambda s: _fired(s, registry), lambda st: _pending_hits(st) >= 1 and zero(st))
    new = _play(fired, registry, "p1", "scramble")
    assert new.pending_window is None
    assert new.systems["000"].space_units["p1"]["destroyer"] == 4


def test_scramble_nie_ma_okna_po_przypisaniu_strat(registry: StaticDataRegistry) -> None:
    fired = _seek(lambda s: _fired(s, registry), lambda st: _pending_hits(st) >= 1)
    hits = _pending_hits(fired)
    done = space_cannon.assign_hits(fired, "p1", {"destroyer": min(hits, 4)})
    _no_window(done, registry, "p1", "scramble")


def test_scramble_bombardowanie(grid: HexGrid, registry: StaticDataRegistry) -> None:
    def make(seed: int) -> GameState:
        state = _state(
            {"p1": {"dreadnought": 3, "infantry": 1}},
            {_PL1: {"p2": {"infantry": 5}}},
            {_PL1: "p2"},
            seed=seed,
        )
        _hand(state, "p1", "scramble")
        _hand(state, "p2", "scramble", "scramble")  # druga kopia: sprawdzamy okno po przypisaniu
        started = _begin(state, grid, registry)
        plan = [BombardAssignment("dreadnought", _PL1, 3)]
        return invasion.bombard(started, grid, registry, plan)

    rolled = _seek(make, lambda st: bool(st.invasion and st.invasion.bombard_pending))
    assert not _row(rolled, registry, "p1", "scramble")["playable"]  # własny rzut
    new = _play(rolled, registry, "p2", "scramble")
    assert new.invasion is not None
    entry = new.invasion.log[0]
    assert entry["rerolled"] is True
    roll = entry["rolls"][0]
    assert entry["hits"] == sum(1 for d in roll["dice"] if d >= roll["hitsOn"])
    assert new.invasion.bombard_pending.get(_PL1, 0) == entry["hits"]
    # Po przypisaniu strat okno znika.
    if entry["hits"]:
        required = invasion.required_bombard_hits(new, grid, registry, _PL1)
        assigned = invasion.assign_bombard_hits(
            new, grid, registry, _PL1, "p2",
            sustain={}, destroy={"infantry": required}, destroy_damaged={},
        )
        _no_window(assigned, registry, "p2", "scramble")


def test_scramble_space_cannon_defense(grid: HexGrid, registry: StaticDataRegistry) -> None:
    fired = _seek(lambda s: _defense_state(s, registry, grid), lambda st: _defense_hits(st) >= 1)
    assert _row(fired, registry, "p1", "scramble")["playable"]
    assert not _row(fired, registry, "p2", "scramble")["playable"]
    new = _play(fired, registry, "p1", "scramble")
    assert new.invasion is not None
    entry = new.invasion.log[-1]
    assert entry["rerolled"] is True
    assert _defense_hits(new) == entry["hits"]
    if not entry["hits"]:
        assert _PL1 in new.invasion.defense_resolved


# ------------------------------------------------------------ Experimental Battlestation


def _move_state(
    *, dock_at: str = "000", seed: int = 1, moved: bool = True, ships: int = 4
) -> GameState:
    state = _state({"p1": {"destroyer": ships}}, step=TacticalStep.MOVEMENT, seed=seed)
    state.tactical_moved = moved
    if dock_at == "000":
        state.systems["000"].planet_units[_PL1] = {"p2": {"spacedock": 1}}
    else:
        state.systems[dock_at] = SystemState(position=dock_at, system_id="20")
        state.systems[dock_at].planet_units["pa"] = {"p2": {"spacedock": 1}}
    _hand(state, "p1", "experimental")
    _hand(state, "p2", "experimental")
    return state


def test_experimental_okno_po_ruchu_dla_innego_gracza_z_dokiem(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _move_state()
    assert _row(state, registry, "p2", "experimental")["playable"]
    # Aktywny gracz nie strzela do własnych statków.
    assert not _row(state, registry, "p1", "experimental")["playable"]
    _no_window(_move_state(moved=False), registry, "p2", "experimental")
    # Poza krokiem MOVEMENT okno się zamyka.
    later = _move_state()
    later.tactical_step = TacticalStep.SPACE_COMBAT
    _no_window(later, registry, "p2", "experimental")


def test_experimental_wymaga_doku_i_statkow(grid: HexGrid, registry: StaticDataRegistry) -> None:
    no_dock = _move_state()
    no_dock.systems["000"].planet_units = {}
    assert not _row(no_dock, registry, "p2", "experimental")["playable"]
    no_ships = _move_state(ships=0)
    no_ships.systems["000"].space_units = {}
    assert not _row(no_ships, registry, "p2", "experimental")["playable"]
    far = _move_state(dock_at="101")
    far.systems["101"].planet_units["pa"] = {"p2": {"spacedock": 1}}
    assert _row(far, registry, "p2", "experimental")["playable"]  # sąsiedni system
    blocked = _move_state()
    blocked = timing.open_window(blocked, WindowType.REACTION, ["p2"])
    assert not _row(blocked, registry, "p2", "experimental")["playable"]


def test_experimental_formularz_wymienia_doki(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _move_state()
    state.systems["101"] = SystemState(position="101", system_id="20")
    state.systems["101"].planet_units["pa"] = {"p2": {"spacedock": 1}}
    form = action_cards.card_inputs(state, registry, "p2", "experimental")[1]
    options = form[0]["options"]
    assert {(o["value"]["position"], o["value"]["zone"]) for o in options} == {
        ("000", _PL1), ("101", "pa"),
    }


def _shot(seed: int, registry: StaticDataRegistry, dock_at: str = "000") -> GameState:
    state = _move_state(dock_at=dock_at, seed=seed)
    zone = _PL1 if dock_at == "000" else "pa"
    params = {"dock": {"position": dock_at, "zone": zone}}
    return _play(state, registry, "p2", "experimental", params)


def test_experimental_strzela_5_x3_i_trafienia_przypisuje_aktywny(
    registry: StaticDataRegistry,
) -> None:
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, "experimental")
    assert card is not None and "SPACE CANNON 5(x3)" in " ".join(card.texts.values())
    hit = _seek(lambda s: _shot(s, registry), lambda st: st.pending_window is not None)
    window = hit.pending_window
    assert window is not None and window.window_type is WindowType.SPACE_CANNON
    pending = space_cannon.pending_hits(hit)
    assert pending is not None and pending.roller == "p2" and pending.target == "p1"
    roll = pending.rolls[0]
    assert roll["hitsOn"] == 5 and len(roll["dice"]) == 3
    assert pending.hits == sum(1 for d in roll["dice"] if d >= 5)
    assert hit.players["p2"].private.action_cards == []
    # Aktywny gracz przypisuje straty istniejącą funkcją okna Space Cannon.
    with pytest.raises(ValueError):
        space_cannon.assign_hits(hit, "p2", {"destroyer": pending.hits})  # nie cel
    done = space_cannon.assign_hits(hit, "p1", {"destroyer": pending.hits})
    assert done.pending_window is None
    assert done.systems["000"].space_units["p1"]["destroyer"] == 4 - pending.hits
    assert space_cannon.read_log(done)[-1]["destroyed"] == {"destroyer": pending.hits}


def test_experimental_bez_trafien_nie_otwiera_okna_i_dok_z_sasiedztwa(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    miss = _seek(
        lambda s: _shot(s, registry, "101"),
        lambda st: st.pending_window is None and space_cannon.read_log(st)[0]["hits"] == 0,
    )
    entry = space_cannon.read_log(miss)[0]
    assert entry["roller"] == "p2" and entry["target"] == "p1"
    assert entry["rolls"][0]["position"] == "101"
    assert miss.systems["000"].space_units["p1"]["destroyer"] == 4
    hit = _seek(lambda s: _shot(s, registry, "101"), lambda st: st.pending_window is not None)
    assert space_cannon.pending_hits(hit) is not None


def test_experimental_bledy_bez_zmian(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _move_state()
    for params in (
        {},
        {"dock": {"position": "000", "zone": "nowhere"}},
        {"dock": {"position": "999", "zone": _PL1}},
    ):
        with pytest.raises(ValueError):
            action_cards.play_action_card(state, registry, "p2", "experimental", params)
    assert state.players["p2"].private.action_cards == ["experimental"]


def test_experimental_integracja_z_krokiem_space_cannon(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    """Po przypisaniu strat okno znika i zwykły krok Space Cannon może się otworzyć."""
    hit = _seek(lambda s: _shot(s, registry), lambda st: st.pending_window is not None)
    pending = space_cannon.pending_hits(hit)
    assert pending is not None
    done = space_cannon.assign_hits(hit, "p1", {"destroyer": pending.hits})
    done.tactical_step = TacticalStep.SPACE_CANNON
    reopened = space_cannon.open_offense(done, grid, registry)
    assert reopened.space_cannon_log == "[]"


# ------------------------------------------------------------------- koniec inwazji / akcji


def test_koniec_akcji_taktycznej_gasi_efekty_inwazji(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _blitz_state(grid, registry, {"cruiser": 1})
    played = _play(state, registry, "p1", "blitz")
    assert active_effects.has_effect(played, "p1", "action_cards:blitz")
    ended = tactical.end_tactical_action(played)
    assert ended.invasion is None
    assert not active_effects.has_effect(ended, "p1", "action_cards:blitz")


def test_zdarzenie_koniec_inwazji_jest_emitowane(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    seen: list[str] = []
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(
            GameEvent.INVASION, Moment.END,
            rules_hooks.HookSource(rules_hooks.SOURCE_FACTION, "p1_faction"),
        )(lambda *_a: seen.append("end"))
        state = _blitz_state(grid, registry, {"cruiser": 1})
        state.players["p1"].faction = "p1_faction"
        invasion.clear_invasion(state)
    assert seen == ["end"]


def test_okna_pochodza_ze_stanu_bez_mutacji(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _commit_state(grid, registry)
    snapshot = state.model_dump()
    reaction_cards.open_windows(state)
    assert state.model_dump() == snapshot
