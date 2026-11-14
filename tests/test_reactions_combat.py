"""Testy kart reakcji w walce (RULES.md 53.5.c): okna, zagrywalność i efekty na silniku."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    action_cards,
    battle,
    board_graph,
    command_tokens,
    damage,
    offers,
    reaction_cards,
    rules_hooks,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    CombatStep,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(scope="module")
def grid() -> HexGrid:
    """000 = aktywny; sąsiedzi: 101 (zwykły), 102 (mgławica), 103 (asteroidy), 104 (supernowa)."""
    g = HexGrid()
    g.place_system("000", "18", anomalies=set())
    g.place_system("101", "20", anomalies=set())
    g.place_system("102", "21", anomalies={"NEBULA"})
    g.place_system("103", "22", anomalies={"ASTEROID_FIELD"})
    g.place_system("104", "23", anomalies={"SUPERNOVA"})
    g.build_edges()
    return g


@pytest.fixture(autouse=True)
def _bound_grid(grid: HexGrid) -> Iterator[None]:
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield
    board_graph.bind_grid_provider(previous)


def _state(
    p1: dict[str, int],
    p2: dict[str, int],
    *,
    hand1: list[str] | None = None,
    hand2: list[str] | None = None,
    presence: dict[str, dict[str, dict[str, int]]] | None = None,
    ground: tuple[dict[str, int], dict[str, int]] | None = None,
    seed: int = 1,
) -> GameState:
    """Układ do walki w 000 (p1 atakuje). ``ground`` = piechota na planecie ``pl``."""
    center = SystemState(position="000", system_id="18")
    if ground is None:
        center.space_units = {"p1": dict(p1), "p2": dict(p2)}
    else:
        center.planet_units = {"pl": {"p1": dict(ground[0]), "p2": dict(ground[1])}}
        center.planet_owners = {"pl": "p2"}
    systems = {"000": center}
    for pos, sid in (("101", "20"), ("102", "21"), ("103", "22"), ("104", "23")):
        system = SystemState(position=pos, system_id=sid)
        for pid, by_type in (presence or {}).get(pos, {}).items():
            system.space_units[pid] = dict(by_type)
        systems[pos] = system
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=TacticalStep.SPACE_COMBAT if ground is None else TacticalStep.INVASION,
        seating_order=["p1", "p2"],
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2")},
        systems=systems,
        rng_seed=seed,
    )
    state.players["p1"].private.action_cards = list(hand1 or [])
    state.players["p2"].private.action_cards = list(hand2 or [])
    return state


def _start(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, planet: str | None = None
) -> GameState:
    return battle.start_combat(state, grid, registry, planet)


def _row(state: GameState, registry: StaticDataRegistry, player: str, card: str) -> dict[str, Any]:
    rows = action_cards.playability(state, registry, player)
    return next(row for row in rows if row["card_id"] == card)


def _can(state: GameState, registry: StaticDataRegistry, player: str, card: str) -> bool:
    return bool(_row(state, registry, player, card)["playable"])


def _play(
    state: GameState,
    registry: StaticDataRegistry,
    player: str,
    card: str,
    params: dict[str, Any] | None = None,
) -> GameState:
    new, implemented = action_cards.play_action_card(state, registry, player, card, params)
    assert implemented
    assert card not in new.players[player].private.action_cards
    return new


def _destroy_all_required(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, pid: str
) -> GameState:
    """Przypisuje straty graczowi: niszczy nieuszkodzone jednostki, ile trzeba (bez Sustain)."""
    required = battle.required_hits(state, grid, registry, pid)
    destroy: dict[str, int] = {}
    for unit in battle.side_units(state, grid, registry, pid):
        take = min(unit.count - unit.damaged, required)
        if take > 0:
            destroy[unit.base_type] = take
            required -= take
    return battle.assign_combat_hits(
        state, grid, registry, pid, sustain={}, destroy=destroy, destroy_damaged={}
    )


def _assign_state(
    grid: HexGrid, registry: StaticDataRegistry, hand1: list[str], hand2: list[str]
) -> GameState:
    """Walka dreadnoughtów 5 na 5 w kroku ASSIGN, obaj mają trafienia do pokrycia."""
    for seed in range(1, 200):
        state = _state(
            {"dreadnought": 5}, {"dreadnought": 5}, hand1=hand1, hand2=hand2, seed=seed
        )
        state = _start(state, grid, registry)
        assert state.active_combat is not None and state.active_combat.step is CombatStep.ROLL
        state = battle.roll_round(state, grid, registry)
        combat = state.active_combat
        assert combat is not None
        if (
            combat.step is CombatStep.ASSIGN
            and combat.pending_hits.get("p1", 0) > 0
            and combat.pending_hits.get("p2", 0) > 0
        ):
            return state
    raise AssertionError("no seed produced hits on both sides")


# ------------------------------------------------------------------------- okna


def test_okno_startu_rundy_tylko_w_kroku_rzutu(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _start(_state({"cruiser": 1}, {"cruiser": 1}), grid, registry)
    assert any(
        w.event is GameEvent.COMBAT_ROUND and w.moment is Moment.START
        for w in reaction_cards.open_windows(state)
    )
    assert state.active_combat is not None
    state.active_combat.step = CombatStep.DONE
    assert not any(
        w.event is GameEvent.COMBAT_ROUND for w in reaction_cards.open_windows(state)
    )
    outside = reaction_cards.open_windows(_state({"cruiser": 1}, {"cruiser": 1}))
    assert not any(w.event in (GameEvent.COMBAT, GameEvent.COMBAT_ROUND) for w in outside)


# ------------------------------------------------------------------------- Morale Boost


def test_morale_boost_dodaje_jeden_do_rzutow_i_wygasa(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(
        _state({"cruiser": 2}, {"cruiser": 2}, hand1=["mb1", "mb2"], hand2=["mb3"]), grid, registry
    )
    assert _can(state, registry, "p1", "mb1") and _can(state, registry, "p2", "mb3")
    new = _play(state, registry, "p1", "mb1")
    assert not _can(new, registry, "p1", "mb2")  # druga kopia nie daje +2
    mine = battle.side_units(new, grid, registry, "p1")[0]
    theirs = battle.side_units(new, grid, registry, "p2")[0]
    assert mine.modifier == 1 and mine.hits_on == mine.base_hits_on - 1
    assert theirs.modifier == 0
    rolled = battle.roll_round(new, grid, registry)
    assert rolled.active_combat is not None
    assert rolled.active_combat.rolls["p1"][0]["modifier"] == 1
    triggers.fire(new, GameEvent.COMBAT_ROUND, Moment.END)
    assert battle.side_units(new, grid, registry, "p1")[0].modifier == 0


def test_morale_boost_nie_dziala_na_afb_i_poza_walka(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(_state({"destroyer": 1}, {"fighter": 1}, hand1=["mb1"]), grid, registry)
    assert state.active_combat is not None and state.active_combat.step is CombatStep.AFB
    assert not _can(state, registry, "p1", "mb1")  # krok AFB to jeszcze nie start rundy rzutów
    outside = _state({"cruiser": 1}, {"cruiser": 1}, hand1=["mb1"])
    assert not _can(outside, registry, "p1", "mb1")
    with pytest.raises(ValueError, match="no open window"):
        action_cards.play_action_card(outside, registry, "p1", "mb1")


# ------------------------------------------------------------------------- Fighter Prototype


def test_fighter_prototype_daje_plus_dwa_tylko_myśliwcom_w_pierwszej_rundzie(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(
        _state({"fighter": 2, "cruiser": 1}, {"cruiser": 1}, hand1=["f_prototype"]), grid, registry
    )
    new = _play(state, registry, "p1", "f_prototype")
    by_type = {u.base_type: u for u in battle.side_units(new, grid, registry, "p1")}
    assert by_type["fighter"].modifier == 2
    assert by_type["cruiser"].modifier == 0
    # Druga runda: karta niezagrywalna („the FIRST round").
    assert state.active_combat is not None
    state.active_combat.round = 2
    assert not _can(state, registry, "p1", "f_prototype")


def test_fighter_prototype_wymaga_myśliwców(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _start(_state({"cruiser": 1}, {"cruiser": 1}, hand1=["f_prototype"]), grid, registry)
    assert not _can(state, registry, "p1", "f_prototype")


# ------------------------------------------------------------------------- Emergency Repairs


def test_emergency_repairs_naprawia_wszystkie_jednostki(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _state({"dreadnought": 3}, {"cruiser": 1}, hand1=["emergency"], hand2=["emergency"])
    damage.set_damaged(state.systems["000"], "space", "p1", "dreadnought", 2)
    state = _start(state, grid, registry)
    assert _can(state, registry, "p1", "emergency")
    assert not _can(state, registry, "p2", "emergency")  # p2 nie ma uszkodzeń
    new = _play(state, registry, "p1", "emergency")
    assert damage.damaged_count(new.systems["000"], "space", "p1", "dreadnought") == 0
    assert battle.side_units(new, grid, registry, "p1")[0].damaged == 0
    assert damage.damaged_count(state.systems["000"], "space", "p1", "dreadnought") == 2


# ------------------------------------------------------------------------- Skilled Retreat


def test_skilled_retreat_przenosi_statki_konczy_walke_remisem(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(
        _state({"cruiser": 2}, {"cruiser": 1}, hand1=["s_retreat1"], hand2=["s_retreat2"]),
        grid, registry,
    )
    assert _can(state, registry, "p1", "s_retreat1")
    implemented, inputs = action_cards.card_inputs(state, registry, "p1", "s_retreat1")
    assert implemented
    assert [o["value"] for o in inputs[0]["options"]] == ["101"]  # anomalie odpadają
    reinforcements = command_tokens.reinforcements(state, "p1")
    new = _play(state, registry, "p1", "s_retreat1", {"destination": "101"})
    combat = new.active_combat
    assert combat is not None
    assert combat.step is CombatStep.DONE and combat.outcome == "draw" and combat.winner is None
    assert new.systems["000"].space_units.get("p1", {}) == {}
    assert new.systems["101"].space_units["p1"] == {"cruiser": 2}
    assert "p1" in new.systems["101"].command_tokens
    assert new.systems["000"].space_units["p2"] == {"cruiser": 1}
    assert state.systems["000"].space_units["p1"] == {"cruiser": 2}  # wejściowy stan nietknięty
    assert command_tokens.reinforcements(new, "p1") == reinforcements - 1  # żeton z rezerwy
    assert new.chronicle.battles and new.chronicle.battles[-1]["winner"] is None


def test_skilled_retreat_bledy_i_blokady(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _start(
        _state(
            {"cruiser": 1}, {"cruiser": 1}, hand1=["s_retreat1"],
            presence={"101": {"p2": {"cruiser": 1}}},
        ),
        grid, registry,
    )
    # Jedyny legalny cel (101) zajmują statki przeciwnika - brak celu = niezagrywalna.
    row = _row(state, registry, "p1", "s_retreat1")
    assert not row["playable"]
    open_state = _start(
        _state({"cruiser": 1}, {"cruiser": 1}, hand1=["s_retreat1"]), grid, registry
    )
    with pytest.raises(ValueError, match="cannot move to system"):
        action_cards.play_action_card(
            open_state, registry, "p1", "s_retreat1", {"destination": "102"}
        )
    with pytest.raises(ValueError, match="Choose an adjacent system"):
        action_cards.play_action_card(open_state, registry, "p1", "s_retreat1", {})


# ------------------------------------------------------------------------- Reveal Prototype


def test_reveal_prototype_wydaje_zasoby_i_bada_ulepszenie(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _state(
        {"carrier": 1, "cruiser": 1}, {"cruiser": 1}, hand1=["reveal_prototype"],
        hand2=["reveal_prototype"],
    )
    state.players["p1"].technologies = ["amd", "gd"]  # dwa niebieskie symbole dla Carrier II
    state.players["p1"].trade_goods = 4
    state = _start(state, grid, registry)
    assert _can(state, registry, "p1", "reveal_prototype")
    assert not _can(state, registry, "p2", "reveal_prototype")  # brak zasobów i technologii
    implemented, inputs = action_cards.card_inputs(state, registry, "p1", "reveal_prototype")
    assert implemented
    assert [o["value"] for o in inputs[0]["options"]] == ["cv2"]  # tylko typ z walki (carrier)
    assert inputs[0]["kind"] == "info"
    played = _play(state, registry, "p1", "reveal_prototype", {})
    # Technologię i zapłatę wybiera się po zagraniu, w oknie badania (tylko pasujące ulepszenia).
    offer = next(o for o in played.pending_offers if "research_cost" in o.ctx)
    view = offers.offer_view(played, registry, offer)["inputs"][0]["research"]
    statuses = {row["id"]: row["status"] for row in view["tree"]}
    assert statuses["dd2"] == "locked" and view["cost"] == 4

    def answer(tech: str, trade_goods: int) -> GameState:
        payload = {"tech": tech, "skips": [], "planets": [], "trade_goods": trade_goods}
        return triggers.accept_offer(played, "p1", offer.id, {"research": payload})

    with pytest.raises(ValueError, match="Spend at least 4"):
        answer("cv2", 3)
    with pytest.raises(ValueError, match="cannot be researched"):
        answer("dd2", 4)
    new = answer("cv2", 4)
    assert "cv2" in new.players["p1"].technologies
    assert new.players["p1"].trade_goods == 0
    # Carrier II jest teraz używanym wariantem w walce.
    assert any(u.unit_id == "carrier2" for u in battle.side_units(new, grid, registry, "p1"))


def test_reveal_prototype_niezagrywalna_bez_czterech_zasobow(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _state({"carrier": 1}, {"cruiser": 1}, hand1=["reveal_prototype"])
    state.players["p1"].technologies = ["amd", "gd"]
    state.players["p1"].trade_goods = 3
    state = _start(state, grid, registry)
    assert not _can(state, registry, "p1", "reveal_prototype")


# ------------------------------------------------------------------------- Rout


def test_rout_wymusza_odwrot_atakujacego(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _start(
        _state(
            {"cruiser": 1}, {"cruiser": 1}, hand1=["rout"], hand2=["rout"],
            presence={"101": {"p1": {"destroyer": 1}}},
        ),
        grid, registry,
    )
    combat = state.active_combat
    assert combat is not None and combat.step is CombatStep.ANNOUNCE
    assert _can(state, registry, "p2", "rout")  # obrońca
    assert not _can(state, registry, "p1", "rout")  # „if you are the defender"
    new = _play(state, registry, "p2", "rout")
    assert new.active_combat is not None
    assert new.active_combat.retreating == ["p1"]
    assert new.active_combat.step is CombatStep.ROLL and new.pending_window is None
    rolled = battle.roll_round(new, grid, registry)  # walka toczy się dalej
    assert rolled.active_combat is not None and rolled.active_combat.rolls


def test_rout_bez_celu_odwrotu_niezagrywalny(grid: HexGrid, registry: StaticDataRegistry) -> None:
    # Atakujący nie ma obecności w sąsiednich systemach - nie ma gdzie się wycofać.
    state = _start(
        _state(
            {"cruiser": 1}, {"cruiser": 1}, hand2=["rout"],
            presence={"101": {"p2": {"destroyer": 1}}},
        ),
        grid, registry,
    )
    assert not _can(state, registry, "p2", "rout")


# ------------------------------------------------------------------------- Intercept


def test_intercept_anuluje_ogloszony_odwrot(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _start(
        _state(
            {"cruiser": 1}, {"cruiser": 1}, hand1=["intercept"], hand2=["intercept"],
            presence={"101": {"p1": {"destroyer": 1}}},
        ),
        grid, registry,
    )
    assert not _can(state, registry, "p2", "intercept")  # nikt jeszcze nie ogłosił odwrotu
    announced = battle.announce_retreat(state, grid, "p1", announce=True)
    combat = announced.active_combat
    assert combat is not None and combat.retreating == ["p1"] and combat.step is CombatStep.ROLL
    assert _can(announced, registry, "p2", "intercept")
    assert not _can(announced, registry, "p1", "intercept")  # „your opponent declares"
    new = _play(announced, registry, "p2", "intercept")
    assert new.active_combat is not None and new.active_combat.retreating == []
    assert not any(
        w.event is GameEvent.RETREAT_DECLARED for w in reaction_cards.open_windows(new)
    )


def test_intercept_w_kroku_wykonania_odwrotu_zaczyna_kolejna_runde(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(
        _state(
            {"cruiser": 1}, {"cruiser": 1}, hand2=["intercept"],
            presence={"101": {"p1": {"destroyer": 1}}},
        ),
        grid, registry,
    )
    state = battle.announce_retreat(state, grid, "p1", announce=True)
    state = battle.roll_round(state, grid, registry)
    combat = state.active_combat
    assert combat is not None
    # Obaj mogą mieć 0 trafień; wymuszamy sytuację „odwrót czeka na wykonanie".
    combat.step = CombatStep.RETREAT
    combat.pending_hits = {}
    state.pending_window = None
    assert _can(state, registry, "p2", "intercept")
    new = _play(state, registry, "p2", "intercept")
    assert new.active_combat is not None
    assert new.active_combat.retreating == []
    assert new.active_combat.round == combat.round + 1
    assert new.active_combat.step in (CombatStep.ANNOUNCE, CombatStep.ROLL)


def test_odwrot_emituje_zdarzenie_retreat_declared(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    from src.core.game_events import EVENT_INFO

    assert EVENT_INFO[GameEvent.RETREAT_DECLARED].emitted_by == "battle.announce_retreat"


# ------------------------------------------------------------------------- Shields Holding


def test_shields_holding_anuluje_do_dwoch_trafien(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _assign_state(grid, registry, ["sh1"], ["sh2"])
    combat = state.active_combat
    assert combat is not None
    before = combat.pending_hits["p2"]
    assert _can(state, registry, "p2", "sh2") and _can(state, registry, "p1", "sh1")
    new = _play(state, registry, "p2", "sh2", {"count": 2})
    assert new.active_combat is not None
    assert new.active_combat.pending_hits["p2"] == max(0, before - 2)
    assert new.active_combat.pending_hits["p1"] == combat.pending_hits["p1"]
    with pytest.raises(ValueError, match="at most 2"):
        action_cards.play_action_card(state, registry, "p2", "sh2", {"count": 3})
    # Prawdziwe przypisanie: tyle trafień do pokrycia, ile zostało.
    required = battle.required_hits(new, grid, registry, "p2")
    assert required == max(0, before - 2)
    assigned = _destroy_all_required(new, grid, registry, "p2")
    assert assigned.active_combat is not None
    assert assigned.active_combat.pending_hits["p2"] == 0


def test_shields_holding_tylko_przed_przypisaniem(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _assign_state(grid, registry, ["sh1"], ["sh2"])
    state = _destroy_all_required(state, grid, registry, "p2")  # p2 już przypisał
    assert not _can(state, registry, "p2", "sh2")
    ground = _start(
        _state({}, {}, hand1=["sh1"], ground=({"infantry": 3}, {"infantry": 3})),
        grid, registry, "pl",
    )
    assert not _can(ground, registry, "p1", "sh1")  # nie w walce naziemnej


# ------------------------------------------------------------------------- Courageous to the End


def test_courageous_niszczy_najtansze_statki_przeciwnika(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(
        _state(
            {"cruiser": 1},
            {"cruiser": 1, "carrier": 1, "dreadnought": 1},
            hand1=["courageous"],
        ),
        grid, registry,
    )
    assert not _can(state, registry, "p1", "courageous")  # żaden statek p1 nie został zniszczony
    combat = state.active_combat
    assert combat is not None
    combat.destroyed_ships = [{"player": "p1", "base_type": "cruiser", "hits_on": 1}]
    assert _can(state, registry, "p1", "courageous")
    implemented, inputs = action_cards.card_inputs(state, registry, "p1", "courageous")
    assert implemented and [o["value"] for o in inputs[0]["options"]] == ["cruiser"]
    new = _play(state, registry, "p1", "courageous", {"ship": "cruiser"})
    # Wartość bojowa 1: obie kości trafiają - giną krążownik i lotniskowiec (najtańsze).
    assert new.systems["000"].space_units["p2"] == {"dreadnought": 1}
    assert new.active_combat is not None and new.active_combat.destroyed_ships == []
    assert new.table_roll is not None and new.table_roll["kind"] == "courageous"
    assert len(new.table_roll["dice"]) == 2


def test_courageous_slad_zniszczenia_powstaje_w_prawdziwej_rundzie(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _assign_state(grid, registry, ["courageous"], [])
    assert not _can(state, registry, "p1", "courageous")
    state = _destroy_all_required(state, grid, registry, "p2")  # obrońca traci statki
    combat = state.active_combat
    assert combat is not None
    lost = [e for e in combat.destroyed_ships if e["player"] == "p2"]
    assert lost and lost[0]["hits_on"] == 5 and lost[0]["base_type"] == "dreadnought"
    # p2 stracił statki, ale to p1 ma kartę - Courageous dotyczy WŁASNYCH strat (SELF).
    assert not _can(state, registry, "p1", "courageous")


# ------------------------------------------------------------------------- Direct Hit


def _sustain_state(
    grid: HexGrid, registry: StaticDataRegistry, hand1: list[str], hand2: list[str]
) -> GameState:
    """Obrońca (p2) przypisał trafienia Sustain Damage; atakujący (p1) jeszcze przypisuje."""
    state = _assign_state(grid, registry, hand1, hand2)
    sustain = min(battle.required_hits(state, grid, registry, "p2"), 5)
    state = battle.assign_combat_hits(
        state, grid, registry, "p2", sustain={"dreadnought": sustain}, destroy={},
        destroy_damaged={},
    )
    assert state.active_combat is not None
    assert state.active_combat.step is CombatStep.ASSIGN
    return state


def test_direct_hit_niszczy_statek_ktory_uzyl_sustain(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _sustain_state(grid, registry, ["dh1"], [])
    combat = state.active_combat
    assert combat is not None and combat.sustained_ships
    used = int(combat.sustained_ships[0]["count"])
    count_before = state.systems["000"].space_units["p2"]["dreadnought"]
    damaged_before = damage.damaged_count(state.systems["000"], "space", "p2", "dreadnought")
    assert damaged_before == used
    assert _can(state, registry, "p1", "dh1")
    new = _play(state, registry, "p1", "dh1", {"ship": "dreadnought"})
    assert new.systems["000"].space_units["p2"]["dreadnought"] == count_before - 1
    assert damage.damaged_count(new.systems["000"], "space", "p2", "dreadnought") == (
        damaged_before - 1
    )
    assert new.active_combat is not None
    remaining = sum(int(e["count"]) for e in new.active_combat.sustained_ships)
    assert remaining == used - 1
    with pytest.raises(ValueError, match="no open window|did not use"):
        action_cards.play_action_card(
            _state({"cruiser": 1}, {"cruiser": 1}, hand1=["dh1"]), registry, "p1", "dh1",
            {"ship": "cruiser"},
        )


def test_direct_hit_niezagrywalny_na_wlasny_sustain(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _sustain_state(grid, registry, [], ["dh2"])
    assert not _can(state, registry, "p2", "dh2")  # „another player's ship"


# ------------------------------------------------------------------------- Reflective Shielding


def test_reflective_shielding_dodaje_dwa_trafienia_przeciwnikowi(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _sustain_state(grid, registry, [], ["reflective"])
    combat = state.active_combat
    assert combat is not None
    before = combat.pending_hits["p1"]
    assert _can(state, registry, "p2", "reflective")
    new = _play(state, registry, "p2", "reflective", {})
    assert new.active_combat is not None
    assert new.active_combat.pending_hits["p1"] == before + 2
    required = battle.required_hits(new, grid, registry, "p1")
    assert required == min(before + 2, 5)
    assigned = _destroy_all_required(new, grid, registry, "p1")  # prawdziwe przypisanie
    assert assigned.active_combat is not None
    assert assigned.active_combat.pending_hits.get("p1", 0) == 0


def test_reflective_niezagrywalny_gdy_przeciwnik_juz_przypisal(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _sustain_state(grid, registry, ["reflective"], [])
    assert not _can(state, registry, "p1", "reflective")  # p1 nie używał Sustain Damage


# ------------------------------------------------------------------------- Fire Team


def _ground_assign(
    grid: HexGrid, registry: StaticDataRegistry, hand1: list[str], hand2: list[str]
) -> GameState:
    for seed in range(1, 200):
        state = _state(
            {}, {}, hand1=hand1, hand2=hand2, ground=({"infantry": 6}, {"infantry": 6}),
            seed=seed,
        )
        state = _start(state, grid, registry, "pl")
        state = battle.roll_round(state, grid, registry)
        combat = state.active_combat
        if combat is not None and combat.step is CombatStep.ASSIGN and all(
            combat.pending_hits.get(p, 0) > 0 for p in ("p1", "p2")
        ):
            return state
    raise AssertionError("no seed produced ground hits")


def test_fire_team_przerzuca_kosci_i_przelicza_trafienia(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _ground_assign(grid, registry, ["fire_team"], ["fire_team"])
    combat = state.active_combat
    assert combat is not None
    assert _can(state, registry, "p1", "fire_team")
    implemented, inputs = action_cards.card_inputs(state, registry, "p1", "fire_team")
    assert implemented and len(inputs[0]["options"]) == 6
    all_dice = [o["value"] for o in inputs[0]["options"]]
    new = _play(state, registry, "p1", "fire_team", {"dice": all_dice})
    after = new.active_combat
    assert after is not None
    hits = sum(int(e["hits"]) for e in after.rolls["p1"])
    assert after.pending_hits["p2"] == hits
    assert after.log[-1]["hits"]["p1"] == hits
    assert after.rolls["p2"] == combat.rolls["p2"]  # kości przeciwnika nietknięte
    assert new.table_roll is not None and new.table_roll["kind"] == "fire_team"
    with pytest.raises(ValueError, match="Unknown die"):
        action_cards.play_action_card(state, registry, "p1", "fire_team", {"dice": ["9:9"]})
    # Prawdziwe przypisanie po przerzucie: p2 pokrywa tyle trafień, ile wypadło.
    assigned = _destroy_all_required(new, grid, registry, "p2")
    assert assigned.active_combat is not None


def test_fire_team_zablokowany_gdy_przeciwnik_przypisal_i_poza_ziemia(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _ground_assign(grid, registry, ["fire_team"], ["fire_team"])
    state = _destroy_all_required(state, grid, registry, "p2")
    assert not _can(state, registry, "p1", "fire_team")  # p2 już przypisał straty
    space = _assign_state(grid, registry, ["fire_team"], [])
    assert not _can(space, registry, "p1", "fire_team")


# ------------------------------------------------------------------------- Salvage


def test_salvage_zabiera_commodities_zwyciezcy(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(
        _state({"dreadnought": 8}, {"cruiser": 1}, hand1=["salvage"], hand2=["salvage"]),
        grid, registry,
    )
    state.players["p2"].commodities = 3
    state.players["p1"].trade_goods = 1
    assert not _can(state, registry, "p1", "salvage")  # walka jeszcze trwa
    for seed in range(1, 100):
        state.rng_seed = seed
        rolled = battle.roll_round(state, grid, registry)
        combat = rolled.active_combat
        assert combat is not None
        if combat.step is CombatStep.ASSIGN and combat.pending_hits.get("p2", 0) > 0:
            current = rolled
            while current.active_combat is not None and (
                current.active_combat.step is CombatStep.ASSIGN
            ):
                responder = current.pending_window.current_responder  # type: ignore[union-attr]
                assert responder is not None
                current = _destroy_all_required(current, grid, registry, responder)
            if current.active_combat is not None and current.active_combat.winner == "p1":
                state = current
                break
    assert state.active_combat is not None and state.active_combat.step is CombatStep.DONE
    assert _can(state, registry, "p1", "salvage")
    assert not _can(state, registry, "p2", "salvage")
    new = _play(state, registry, "p1", "salvage")
    assert new.players["p2"].commodities == 0
    assert new.players["p1"].trade_goods == 4  # oddane commodities stają się trade goods


def test_salvage_niezagrywalny_bez_commodities(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _start(_state({"cruiser": 1}, {"cruiser": 1}, hand1=["salvage"]), grid, registry)
    assert state.active_combat is not None
    state.active_combat.step = CombatStep.DONE
    state.active_combat.winner = "p1"
    state.active_combat.outcome = "winner"
    assert not _can(state, registry, "p1", "salvage")  # przeciwnik ma 0 commodities
    state.players["p2"].commodities = 2
    assert _can(state, registry, "p1", "salvage")


# ------------------------------------------------------------------------- Waylay


def _afb_state(grid: HexGrid, registry: StaticDataRegistry, hand1: list[str]) -> GameState:
    for seed in range(1, 200):
        state = _state(
            {"destroyer": 8},
            {"dreadnought": 6, "fighter": 1},
            hand1=hand1,
            seed=seed,
        )
        state = _start(state, grid, registry)
        assert state.active_combat is not None and state.active_combat.step is CombatStep.AFB
        probe = battle.resolve_afb(state, grid, registry)
        if probe.active_combat is not None and probe.active_combat.log[0]["hits"]["p1"] >= 2:
            return state
    raise AssertionError("no seed gave AFB hits")


def test_waylay_kieruje_trafienia_afb_przeciw_wszystkim_statkom(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _afb_state(grid, registry, ["waylay"])
    assert _can(state, registry, "p1", "waylay")
    new = _play(state, registry, "p1", "waylay")
    resolved = battle.resolve_afb(new, grid, registry)
    combat = resolved.active_combat
    assert combat is not None
    hits = combat.log[0]["hits"]["p1"]
    # Myśliwiec NIE ginie automatycznie - przeciwnik przypisuje trafienia w kroku ASSIGN.
    assert combat.step is CombatStep.ASSIGN and combat.afb_assign
    assert combat.pending_hits["p2"] == hits
    assert resolved.systems["000"].space_units["p2"].get("fighter") == 1
    assigned = _destroy_all_required(resolved, grid, registry, "p2")
    after = assigned.active_combat
    assert after is not None
    assert not after.afb_assign
    assert after.round == 1 and after.step in (CombatStep.ANNOUNCE, CombatStep.ROLL)
    left = assigned.systems["000"].space_units["p2"]
    assert sum(left.values()) == 7 - min(hits, 7)
    # Efekt wygasł wraz z krokiem AFB.
    assert not rules_hooks.permits(rules_hooks.POINT_COMBAT_AFB_ALL_SHIPS, assigned, "p1")


def test_bez_waylay_afb_niszczy_tylko_mysliwce_i_waylay_poza_afb_niezagrywalny(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _afb_state(grid, registry, ["waylay"])
    plain = battle.resolve_afb(state, grid, registry)
    assert plain.active_combat is not None
    assert plain.active_combat.step is not CombatStep.ASSIGN
    assert plain.systems["000"].space_units["p2"].get("fighter", 0) == 0
    assert plain.systems["000"].space_units["p2"]["dreadnought"] == 6
    assert plain.active_combat.destroyed_ships == [
        {"player": "p2", "base_type": "fighter", "hits_on": 9}
    ]
    assert not _can(plain, registry, "p1", "waylay")


def test_waylay_po_stronie_bez_afb_niezagrywalny(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(
        _state({"cruiser": 1}, {"destroyer": 1}, hand1=["waylay"], hand2=["waylay"]),
        grid, registry,
    )
    assert state.active_combat is not None and state.active_combat.step is CombatStep.AFB
    assert not _can(state, registry, "p1", "waylay")  # p1 nie ma AFB
