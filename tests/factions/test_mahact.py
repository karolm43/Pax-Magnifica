"""The Mahact Gene-Sorcerers — every faction component (RULES.md 62.23) and the F_mahact rulings.

Scenarios through the real API (offers, window uses, ACTIONs, notes): ``test_flows_mahact.py``.
Statuses without a test: ``tests/rulings_status.json``.

Board (ring 1 + part of ring 2): 000 Mecatol Rex, 101 Mahact home (52: Ixth), 102 empty (46),
103 empty (47), 104 the rival's home, 105 Lodor (26), 106 Tarmann (22), 201 empty (48).
Edges: 101-102-103-104-105-106 ring around 000; 201 touches 101 and 102.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    agenda_phase,
    battle,
    board_graph,
    command_tokens,
    faction_components,
    fleet_pool,
    leaders,
    offers,
    promissory_notes,
    promissory_play,
    retreat,
    rules_hooks,
    strategic_action,
    tactical,
    technology,
    timing,
    transaction,
    triggers,
    unit_ops,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    AgendaPhaseState,
    AgendaStep,
    CombatStep,
    EliminatedPlayer,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.hooks import agendas_directives
from src.core.hooks.factions import mahact, mentak
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.transaction import TransactionSide
from src.core.unit_ops import UnitCause
from tests.factions.completeness import missing_components
from tests.rulings import ruling

MECATOL, HOME, EMPTY, EMPTY_B, RIVAL, LODOR, TARMANN, FAR = (
    "000", "101", "102", "103", "104", "105", "106", "201",
)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    yield
    board_graph.bind_grid_provider(None)


def _bind(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    board_graph.bind_grid_provider(lambda: grid_from_state(state, registry))
    return grid_from_state(state, registry)


def _state(registry: StaticDataRegistry, other: str = "mentak", third: str | None = None
           ) -> GameState:
    """p1 = the Mahact (active), p2 = ``other`` at 104 (+ optional p3 without a home)."""
    rival = registry.factions[other]
    p1 = PlayerState(player_id="p1", color="purple", faction="mahact", home_position=HOME,
                     controlled_planets=["ixth"])
    p2 = PlayerState(player_id="p2", color="red", faction=other, home_position=RIVAL,
                     controlled_planets=list(rival.home_planets))
    players = {"p1": p1, "p2": p2}
    if third is not None:
        players["p3"] = PlayerState(player_id="p3", color="blue", faction=third)
    systems = {
        MECATOL: SystemState(position=MECATOL, system_id="18"),
        HOME: SystemState(position=HOME, system_id="52", planet_owners={"ixth": "p1"},
                          space_units={"p1": {"flagship": 1, "carrier": 1}}),
        EMPTY: SystemState(position=EMPTY, system_id="46"),
        EMPTY_B: SystemState(position=EMPTY_B, system_id="47"),
        RIVAL: SystemState(position=RIVAL, system_id=str(rival.home_system),
                           planet_owners={p: "p2" for p in rival.home_planets}),
        LODOR: SystemState(position=LODOR, system_id="26"),
        TARMANN: SystemState(position=TARMANN, system_id="22"),
        FAR: SystemState(position=FAR, system_id="48"),
    }
    state = GameState(phase=Phase.ACTION, active_player_id="p1",
                      seating_order=list(players), players=players, systems=systems, rng_seed=3)
    for player in state.players.values():
        player.cc_reinf = 8
        player.tactical_cc = 3
        player.leader_states = {}
        player.commodity_value = registry.factions[player.faction or ""].commodities
    _bind(state, registry)
    return state


def _offers(state: GameState, pid: str, label: str) -> list[Any]:
    return [o for o in triggers.offers_for(state, pid) if label in o.label]


def _inputs(state: GameState, registry: StaticDataRegistry, offer: Any) -> list[dict[str, Any]]:
    return offers.offer_view(state, registry, offer)["inputs"]  # type: ignore[no-any-return]


def _accept(state: GameState, pid: str, label: str, params: dict[str, Any] | None = None
            ) -> GameState:
    offer = _offers(state, pid, label)[0]
    return triggers.accept_offer(state, pid, offer.id, params or {})


def _use(state: GameState, registry: StaticDataRegistry, pid: str, kind: str, comp: str,
         params: dict[str, Any] | None = None) -> GameState:
    new_state, _implemented = faction_components.play(state, registry, pid, kind, comp, params)
    return new_state


def _won(state: GameState, winner: str, loser: str, kind: str = "space") -> GameState:
    work = state.clone()
    triggers.fire(work, GameEvent.COMBAT_WON, Moment.AFTER, subject=winner, ctx={
        "kind": kind, "position": EMPTY, "winner": winner, "planet": "",
        "attacker": winner, "defender": loser,
    })
    return work


def test_mahact_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "mahact") == []


# ======================================================================================== Edict


@ruling("abilities:edict#1", "F_mahact/edict/1")
def test_edict_token_przeciwnika_w_puli_floty(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    before = fleet_pool.fleet_report(state, HOME, "p1").pool
    after = _won(state, "p1", "p2")
    assert after.players["p1"].foreign_fleet_tokens == ["p2"]
    assert after.players["p2"].cc_reinf == 7
    # Counted at once - the fleet pool check after that combat already sees it (edict 1).
    assert fleet_pool.fleet_report(after, HOME, "p1").pool == before + 1
    again = _won(after, "p1", "p2", kind="ground")  # ground combat too; never a second token
    assert again.players["p1"].foreign_fleet_tokens == ["p2"]
    assert again.players["p2"].cc_reinf == 7


def test_edict_nie_dziala_dla_przegranego(registry: StaticDataRegistry) -> None:
    after = _won(_state(registry), "p2", "p1")
    assert after.players["p2"].foreign_fleet_tokens == []
    assert after.players["p1"].foreign_fleet_tokens == []


@ruling("abilities:edict#2")
def test_edict_obce_zetony_zwiekszaja_limit_ale_nie_do_rozdzialu(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, third="hacan")
    state.players["p1"].foreign_fleet_tokens = ["p2", "p3"]
    assert command_tokens.fleet_pool_count(state, "p1") == 5
    assert fleet_pool.fleet_report(state, HOME, "p1").pool == 5
    # Redistribution: only the own 3 fleet tokens are on the table.
    command_tokens.set_pools(state, "p1", {"tactical": 6, "fleet": 0, "strategic": 2})
    assert state.players["p1"].foreign_fleet_tokens == ["p2", "p3"]
    assert command_tokens.fleet_pool_count(state, "p1") == 2


@ruling("F_mahact/edict/2")
def test_edict_usuniecie_zetonu_floty_najpierw_wlasny(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].foreign_fleet_tokens = ["p2"]
    state.players["p1"].fleet_cc = 1
    assert command_tokens.remove_fleet_token(state, "p1") == "p1"
    assert state.players["p1"].foreign_fleet_tokens == ["p2"]
    reinf = state.players["p2"].cc_reinf
    assert command_tokens.remove_fleet_token(state, "p1") == "p2"  # only foreign left
    assert state.players["p1"].foreign_fleet_tokens == []
    assert state.players["p2"].cc_reinf == reinf + 1  # back to its OWNER's reinforcements
    assert command_tokens.remove_fleet_token(state, "p1") is None


@ruling("F_mahact/edict/2")
def test_edict_usuniecie_zetonu_floty_wybor_mahact(registry: StaticDataRegistry) -> None:
    """A rule removes a fleet pool token: with own AND other players' tokens the Mahact picks
    (no "Auto"); a foreign token goes back to its owner's reinforcements."""
    state = _state(registry, third="hacan")
    state.players["p1"].fleet_cc = 1
    state.players["p1"].foreign_fleet_tokens = ["p2"]
    command_tokens.remove_fleet_tokens(state, "p1", 1, "Sanction")
    assert state.players["p1"].fleet_cc == 1  # nothing removed yet - the Mahact decides
    offer = _offers(state, "p1", "fleet pool token")[0]
    (field,) = _inputs(state, registry, offer)
    assert [o["value"] for o in field["options"]] == ["own", "p2"] and "auto" not in field
    with pytest.raises(ValueError):
        triggers.accept_offer(state, "p1", offer.id, {})
    reinf = state.players["p2"].cc_reinf
    done = triggers.accept_offer(state, "p1", offer.id, {"token": "p2"})
    assert done.players["p1"].foreign_fleet_tokens == [] and done.players["p1"].fleet_cc == 1
    assert done.players["p2"].cc_reinf == reinf + 1
    # Several tokens at once (Fleet Regulations excess): own count + other players' tokens.
    many = _state(registry, third="hacan")
    many.players["p1"].fleet_cc = 4
    many.players["p1"].foreign_fleet_tokens = ["p2", "p3"]
    many.decks.agenda_laws = {}
    agendas_directives._regulations(many, "p1", {"outcome": "for"})
    offer = _offers(many, "p1", "fleet pool token")[0]
    fields = {f["key"]: f for f in _inputs(many, registry, offer)}
    assert (fields["own"]["min"], fields["own"]["max"]) == (0, 2)
    assert (fields["foreign"]["min"], fields["foreign"]["max"]) == (0, 2)
    with pytest.raises(ValueError, match="exactly 2"):
        triggers.accept_offer(many, "p1", offer.id, {"own": 1, "foreign": []})
    after = triggers.accept_offer(many, "p1", offer.id, {"own": 1, "foreign": ["p3"]})
    assert after.players["p1"].fleet_cc == 3 and after.players["p1"].foreign_fleet_tokens == ["p2"]
    assert command_tokens.fleet_pool_count(after, "p1") == 4
    # No choice (one owner only / the whole pool leaves): removed at once, no decision.
    own_only = _state(registry)
    own_only.players["p1"].fleet_cc = 2
    command_tokens.remove_fleet_tokens(own_only, "p1", 1, "Neuroglaive")
    assert own_only.players["p1"].fleet_cc == 1 and not _offers(own_only, "p1", "fleet pool")
    everything = _state(registry)
    everything.players["p1"].fleet_cc = 1
    everything.players["p1"].foreign_fleet_tokens = ["p2"]
    command_tokens.remove_fleet_tokens(everything, "p1", 3, "Research Grant Reallocation")
    assert command_tokens.fleet_pool_count(everything, "p1") == 0
    assert not _offers(everything, "p1", "fleet pool")


@ruling("F_mahact/edict/3", "C_agendas/fleet-regulations/3")
def test_edict_fleet_regulations_dodaje_i_zwraca(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.decks.agenda_laws = {"regulations": "for"}
    state.players["p1"].fleet_cc = 4
    after = _won(state, "p1", "p2")
    assert after.players["p1"].foreign_fleet_tokens == ["p2"]  # added despite the cap
    offer = _offers(after, "p1", "Fleet Regulations")[0]
    inputs = _inputs(after, registry, offer)
    assert "auto" not in inputs[0]
    done = _accept(after, "p1", "Fleet Regulations", {"token": "p2"})
    assert done.players["p1"].foreign_fleet_tokens == []
    assert done.players["p2"].cc_reinf == 8


@ruling("F_mahact/edict/4")
def test_edict_pusta_rezerwa_przeciwnik_wybiera_pule(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    rival = state.players["p2"]
    rival.cc_reinf, rival.tactical_cc, rival.fleet_cc, rival.strategic_cc = 0, 1, 3, 2
    after = _won(state, "p1", "p2")
    offer = _offers(after, "p2", "Edict")[0]
    assert "auto" not in _inputs(after, registry, offer)[0]
    done = _accept(after, "p2", "Edict", {"pool": "tactical"})
    assert done.players["p2"].tactical_cc == 0
    assert done.players["p1"].foreign_fleet_tokens == ["p2"]


@ruling("F_mahact/edict/4.1")
def test_edict_bez_zetonow_nic(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    rival = state.players["p2"]
    rival.cc_reinf = rival.tactical_cc = rival.fleet_cc = rival.strategic_cc = 0
    after = _won(state, "p1", "p2")
    assert after.players["p1"].foreign_fleet_tokens == []
    assert not after.pending_offers


@ruling("F_mahact/edict/5")
def test_edict_zeton_na_plansze_z_wlasnej_puli_nie_obcej(registry: StaticDataRegistry) -> None:
    """Placing a token from reinforcements with none left takes an OWN sheet token: the foreign
    tokens are not in any pool the engine places from."""
    state = _state(registry)
    p1 = state.players["p1"]
    p1.cc_reinf, p1.foreign_fleet_tokens = 0, ["p2"]
    command_tokens.place_on_board_from_pool(state, state.systems[EMPTY], "p1", "fleet")
    assert state.systems[EMPTY].command_tokens == ["p1"]
    assert p1.fleet_cc == 2 and p1.foreign_fleet_tokens == ["p2"]


@ruling("F_mahact/edict/6")
def test_edict_zeton_z_tej_walki_nie_daje_commandera(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p2"].leader_states = {mentak.COMMANDER: leaders.UNLOCKED}
    state.active_combat = ActiveCombat(kind="space", position=EMPTY, attacker="p1",
                                              defender="p2")
    after = _won(state, "p1", "p2")
    assert after.players["p1"].foreign_fleet_tokens == ["p2"]
    assert mentak.COMMANDER not in faction_components.borrowed_commanders(after, "p1")
    assert not _offers(after, "p1", "S'ula")
    after.active_combat = None
    after.active_effects = [e for e in after.active_effects if e.key != mahact.EDICT_FRESH]
    assert mentak.COMMANDER in faction_components.borrowed_commanders(after, "p1")


# ======================================================================================= Imperia


@ruling("abilities:imperia#1")
def test_imperia_commander_wlasciciela_zetonu(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].foreign_fleet_tokens = ["p2"]
    assert mentak.COMMANDER not in faction_components.borrowed_commanders(state, "p1")  # locked
    state.players["p2"].leader_states = {mentak.COMMANDER: leaders.UNLOCKED}
    assert mentak.COMMANDER in faction_components.borrowed_commanders(state, "p1")
    sources = rules_hooks.owned_sources(state, "p1")
    assert rules_hooks.HookSource(rules_hooks.SOURCE_LEADER, mentak.COMMANDER) in sources
    state.players["p1"].foreign_fleet_tokens = []
    assert mentak.COMMANDER not in faction_components.borrowed_commanders(state, "p1")


# ======================================================================================== Hubris


def _alliance(state: GameState, pid: str) -> str:
    return f"{state.players[pid].color}_an"


@ruling("abilities:hubris#1")
def test_hubris_setup_purge_alliance(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    own = _alliance(state, "p1")
    promissory_notes.set_hand(state, "p1", [own, "purple_ps"])
    triggers.fire(state, GameEvent.SETUP, Moment.DURING)
    assert state.players["p1"].private.promissory_notes == ["purple_ps"]
    assert own in state.decks.purged


@ruling("abilities:hubris#2")
def test_hubris_nikt_nie_daje_alliance(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    theirs = _alliance(state, "p2")
    promissory_notes.set_hand(state, "p2", [theirs, "red_ps"])
    with pytest.raises(ValueError, match="Alliance"):
        promissory_notes.transfer(state, "p2", "p1", theirs)
    with pytest.raises(ValueError, match="Alliance"):
        transaction.validate_side(state, "p2", "p1", TransactionSide(promissory_note=theirs),
                                  "The partner")
    promissory_notes.transfer(state, "p2", "p1", "red_ps")  # other notes are fine
    assert "red_ps" in state.players["p1"].private.promissory_notes


@ruling("F_mahact/hubris/1")
def test_hubris_wymuszone_oddanie_tylko_alliance_nic(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    promissory_notes.set_hand(state, "p2", [_alliance(state, "p2")])
    assert promissory_notes.giveable(state, "p2", "p1") == []
    # Mentak's S'ula Mentarion (via Imperia) would offer nothing to take.
    ctx = {"kind": "space", "winner": "p1", "attacker": "p1", "defender": "p2"}
    assert not mentak._commander_ready(state, "p1", ctx)


# =========================================================================== Crimson Legionnaire


def _kill_infantry(state: GameState, count: int) -> GameState:
    work = state.clone()
    system = work.systems[HOME]
    unit_ops.place_units(work, system, "ixth", "p1", "infantry", count)
    unit_ops.remove_units(work, system, "ixth", "p1", "infantry", count, UnitCause.DESTROYED)
    return work


@ruling("units:mahact_infantry#1", "F_mahact/crimson-legionnaire/1")
def test_legionnaire_jedna_decyzja_na_jednostke(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].commodities = 1
    after = _kill_infantry(state, 2)
    picks = _offers(after, "p1", "Crimson Legionnaire")
    assert len(picks) == 2
    assert "auto" not in _inputs(after, registry, picks[0])[0]
    after = _accept(after, "p1", "Crimson Legionnaire", {"pick": "convert"})
    assert after.players["p1"].commodities == 0
    tg = after.players["p1"].trade_goods
    assert len(_offers(after, "p1", "Crimson Legionnaire")) == 1
    after = _accept(after, "p1", "Crimson Legionnaire", {"pick": "gain"})
    assert after.players["p1"].commodities == 1 and after.players["p1"].trade_goods == tg


@ruling("F_mahact/crimson-legionnaire/1.1")
def test_legionnaire_zdobyc_potem_zamienic(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    after = _kill_infantry(state, 2)
    # First unit: nothing to convert yet - the only legal answer ("gain") resolves itself.
    assert after.players["p1"].commodities == 1
    second = _offers(after, "p1", "Crimson Legionnaire")
    assert len(second) == 1
    options = _inputs(after, registry, second[0])[0]["options"]
    assert [o["value"] for o in options] == ["gain", "convert"]
    after = _accept(after, "p1", "Crimson Legionnaire", {"pick": "convert"})
    assert after.players["p1"].commodities == 0 and after.players["p1"].trade_goods == 1


@ruling("technologies:cl2#1")
def test_legionnaire_ii_dane(registry: StaticDataRegistry) -> None:
    unit = registry.units["mahact_infantry2"]
    assert (unit.cost, unit.combat_hits_on, unit.required_tech_id) == (0.5, 7, "cl2")


@ruling("technologies:cl2#2", "technologies:cl2#3", "technologies:cl2#4")
def test_legionnaire_ii_karta_i_powrot_na_poczatku_tury(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies = ["cl2"]
    after = _kill_infantry(state, 2)
    assert mahact._card_count(after, "p1") == 2
    while _offers(after, "p1", "Crimson Legionnaire"):
        after = _accept(after, "p1", "Crimson Legionnaire", {"pick": "gain"})
    assert after.players["p1"].commodities == 2
    triggers.fire(after, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    if _offers(after, "p1", "home planet"):
        after = _accept(after, "p1", "home planet", {"planet": "ixth"})
    assert after.systems[HOME].planet_units["ixth"]["p1"]["infantry"] == 2
    assert mahact._card_count(after, "p1") == 0


# ========================================================================= Genetic Recombination


def _agenda(state: GameState) -> GameState:
    state.phase = Phase.AGENDA
    state.speaker_id = "p1"
    state.players["p1"].technologies = ["gr"]
    state.agenda = AgendaPhaseState(step=AgendaStep.VOTE, agenda_id="regulations", kind="for",
                                    outcomes=["for", "against"], vote_order=["p2", "p1"])
    return state


@ruling("technologies:gr#1", "technologies:gr#2")
def test_genetic_recombination_wymusza_glos(registry: StaticDataRegistry) -> None:
    state = _agenda(_state(registry))
    assert mahact.gr_target(state, "p1") == "p2"
    after = _use(state, registry, "p1", "technology", "gr", {"outcome": "against"})
    assert "gr" in after.players["p1"].exhausted_technologies
    offer = _offers(after, "p2", "Genetic Recombination")[0]
    assert "auto" not in _inputs(after, registry, offer)[0]
    with pytest.raises(ValueError, match="Waiting"):  # the vote waits for the decision
        agenda_phase.cast_vote(after, registry, "p2", "for", list(registry.factions["mentak"]
                                                                  .home_planets))
    bound = _accept(after, "p2", "Genetic Recombination", {"choice": "vote"})
    planets = list(registry.factions["mentak"].home_planets)
    with pytest.raises(ValueError, match="Genetic Recombination"):
        agenda_phase.cast_vote(bound, registry, "p2", "for", planets)
    with pytest.raises(ValueError, match="Genetic Recombination"):
        agenda_phase.abstain(bound, registry, "p2")
    voted = agenda_phase.cast_vote(bound, registry, "p2", "against", planets)
    assert voted.agenda is not None and voted.agenda.votes["p2"].outcome == "against"


def test_genetic_recombination_albo_zeton_floty(registry: StaticDataRegistry) -> None:
    state = _agenda(_state(registry))
    after = _use(state, registry, "p1", "technology", "gr", {"outcome": "against"})
    done = _accept(after, "p2", "Genetic Recombination", {"choice": "remove"})
    assert done.players["p2"].fleet_cc == 2
    assert agenda_phase.required_outcomes(done, "p2") == frozenset()


@ruling("F_mahact/genetic-recombination/1", "F_mahact/genetic-recombination/1.1")
def test_genetic_recombination_tylko_gracz_ktory_moze_glosowac(
    registry: StaticDataRegistry,
) -> None:
    state = _agenda(_state(registry))
    state.players["p2"].exhausted_planets = list(registry.factions["mentak"].home_planets)
    assert mahact.gr_target(state, "p1") is None
    assert mahact._gr_window(state, registry, "p1") is not None
    state.players["p2"].exhausted_planets = []  # readied again -> may be targeted (1.1)
    assert mahact.gr_target(state, "p1") == "p2"


# ================================================================================ Jae Mir Kan


def _secondary(state: GameState) -> GameState:
    state.active_player_id = "p2"
    state.systems[LODOR].command_tokens = ["p2"]
    opened = timing.open_window(state, WindowType.STRATEGY_SECONDARY, ["p1"],
                                context={"initiative": 5, "cost": 1, "free": ""})
    return opened


@ruling("leaders:mahactagent#1", "F_mahact/jae-mir-kan/1", "F_mahact/jae-mir-kan/2")
def test_jae_mir_kan_zeton_aktywnego_gracza(registry: StaticDataRegistry) -> None:
    state = _secondary(_state(registry, other="muaat"))
    state.players["p1"].strategic_cc = 0  # usable with an empty strategy pool (1)
    alternatives = command_tokens.secondary_token_alternatives(state, "p1")
    assert alternatives and alternatives[0]["systems"] == [LODOR]
    reinf = state.players["p2"].cc_reinf
    after = strategic_action.resolve_secondary(
        state, registry, "p1", execute=True,
        payload={"token_alt": "leaders:mahactagent", "token_alt_system": LODOR},
    )
    assert after.systems[LODOR].command_tokens == []
    assert after.players["p2"].cc_reinf == reinf + 1
    assert after.players["p1"].strategic_cc == 0
    assert after.players["p1"].leader_states.get(mahact.AGENT) == leaders.EXHAUSTED
    # No strategy-pool spend: the Muaat commander (Alliance) gains nothing (2).
    assert after.players["p1"].trade_goods == state.players["p1"].trade_goods


# ============================================================================== Il Na Viroset


@ruling("leaders:mahactcommander#unlock")
def test_il_na_viroset_odblokowanie(registry: StaticDataRegistry) -> None:
    state = _state(registry, third="hacan")
    fn = leaders._BY_LEADER[mahact.COMMANDER]
    state.players["p1"].foreign_fleet_tokens = ["p2"]
    assert not fn(state, registry, "p1")
    state.players["p1"].foreign_fleet_tokens = ["p2", "p3"]
    assert fn(state, registry, "p1")


@ruling("leaders:mahactcommander#1", "leaders:mahactcommander#2", "F_mahact/il-na-viroset/1",
        "F_mahact/il-na-viroset/2", "F_mahact/il-na-viroset/3", "F_mahact/il-na-viroset/4")
def test_il_na_viroset_aktywacja_wlasnego_zetonu(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    grid = _bind(state, registry)
    state.systems[EMPTY].command_tokens = ["p1"]
    state.systems[EMPTY].space_units = {"p1": {"cruiser": 1}}
    with pytest.raises(ValueError, match="already contains"):
        tactical.activate_system(state, grid, EMPTY)
    state.players["p1"].leader_states = {mahact.COMMANDER: leaders.UNLOCKED}
    state.players["p1"].technologies = ["det"]  # Dark Energy Tap does not trigger (4)
    reinf = state.players["p1"].cc_reinf
    after = tactical.activate_system(state, grid, EMPTY)
    assert after.systems[EMPTY].command_tokens == []
    assert after.players["p1"].tactical_cc == 2 and after.players["p1"].cc_reinf == reinf + 2
    assert after.active_player_id == "p2"  # the turn ended
    assert after.active_system is None and not after.pending_offers


@ruling("F_mahact/il-na-viroset/1.1", "F_mahact/il-na-viroset/1.2")
def test_il_na_viroset_tylko_warunki_zwrotu_notek(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    grid = _bind(state, registry)
    state.systems[RIVAL].command_tokens = ["p1"]
    state.systems[RIVAL].space_units = {"p2": {"cruiser": 1}}
    state.players["p1"].leader_states = {mahact.COMMANDER: leaders.UNLOCKED}
    note = "red_sftt"
    state.players["p1"].promissory_notes_in_play = [note]
    state.players["p1"].victory_points = 1
    after = tactical.activate_system(state, grid, RIVAL)
    assert note not in after.players["p1"].promissory_notes_in_play  # returned (1.2)
    assert note in after.players["p2"].private.promissory_notes
    assert not after.pending_offers  # no "after another player activates" window (1.1)


# ======================================================================= Airo Shir Aur (hero)


def _benediction_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry, other="hacan")
    state.systems[EMPTY].space_units = {"p1": {"cruiser": 2, "fighter": 1}}
    state.systems[EMPTY].planet_units = {}
    state.systems[EMPTY_B].space_units = {"p2": {"destroyer": 1}}
    state.players["p1"].leader_states = {mahact.HERO: leaders.UNLOCKED}
    return state


@ruling("leaders:mahacthero#1", "leaders:mahacthero#2", "leaders:mahacthero#3",
        "leaders:mahacthero#4", "F_mahact/airo-shir-aur-benediction/8",
        "F_mahact/airo-shir-aur-benediction/9", "F_mahact/airo-shir-aur-benediction/11",
        "F_mahact/airo-shir-aur-benediction/11.2", "C_action_cards/rout/2")
def test_benediction_ruch_i_walka_bez_odwrotu(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    assert (EMPTY, EMPTY_B, "p1") in mahact.benediction_pairs(state, "p1")
    after = _use(state, registry, "p1", "leader", mahact.HERO,
                 {"source": EMPTY, "destination": EMPTY_B})
    assert after.systems[EMPTY].space_units.get("p1", {}) in ({}, {"cruiser": 0, "fighter": 0})
    assert after.systems[EMPTY_B].space_units["p1"]["cruiser"] == 2
    combat = after.active_combat
    assert combat is not None and combat.position == EMPTY_B and combat.no_retreat
    assert (combat.attacker, combat.defender) == ("p1", "p2")  # the moved player attacks (9)
    assert after.active_system == EMPTY_B  # the active system during the combat (8)
    assert after.tactical_step is None  # not a tactical action (11)
    assert after.players["p1"].leader_states[mahact.HERO] == leaders.PURGED
    grid = grid_from_state(after, registry)
    assert retreat.retreat_destinations(after, grid, EMPTY_B, "p1") == []
    assert retreat.retreat_destinations(after, grid, EMPTY_B, "p2") == []


@ruling("F_mahact/airo-shir-aur-benediction/9")
def test_benediction_cudze_statki_atakuja(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    state.systems[EMPTY].space_units = {"p2": {"carrier": 1, "infantry": 1}}
    state.systems[EMPTY_B].space_units = {"p1": {"dreadnought": 1}}
    after = _use(state, registry, "p1", "leader", mahact.HERO,
                 {"source": EMPTY, "destination": EMPTY_B})
    combat = after.active_combat
    assert combat is not None and (combat.attacker, combat.defender) == ("p2", "p1")
    assert after.systems[EMPTY_B].space_units["p2"]["infantry"] == 1  # space-area cargo moves


@ruling("F_mahact/airo-shir-aur-benediction/1")
def test_benediction_sily_na_planetach_zostaja(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    state.systems[LODOR].space_units = {"p2": {"carrier": 1}}
    state.systems[LODOR].planet_units = {"lodor": {"p2": {"infantry": 2}}}
    state.systems[TARMANN].space_units = {"p1": {"cruiser": 1}}
    after = _use(state, registry, "p1", "leader", mahact.HERO,
                 {"source": LODOR, "destination": TARMANN})
    assert after.systems[LODOR].planet_units["lodor"]["p2"]["infantry"] == 2


@ruling("F_mahact/airo-shir-aur-benediction/1.1")
def test_benediction_wlasne_statki_zabieraja_sily(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    state.systems[EMPTY].space_units = {}
    state.systems[HOME].space_units = {"p1": {"carrier": 1}}
    state.systems[HOME].planet_units = {"ixth": {"p1": {"infantry": 3}}}
    state.systems[EMPTY].space_units = {"p2": {"destroyer": 1}}
    state.systems[EMPTY_B].space_units = {}
    form = mahact.hero_inputs(state, registry, "p1")
    take = next(f for f in form if f["key"] == f"take|{HOME}|ixth|infantry")
    assert "auto" not in take and take["max"] == 3
    with pytest.raises(ValueError, match="carry"):  # a carrier holds 4 (benediction 1.1)
        state.systems[HOME].planet_units["ixth"]["p1"]["infantry"] = 5
        _use(state, registry, "p1", "leader", mahact.HERO,
             {"source": HOME, "destination": EMPTY, f"take|{HOME}|ixth|infantry": 5})
    state.systems[HOME].planet_units["ixth"]["p1"]["infantry"] = 3
    done = _use(state, registry, "p1", "leader", mahact.HERO,
                {"source": HOME, "destination": EMPTY, f"take|{HOME}|ixth|infantry": 2})
    assert done.systems[EMPTY].space_units["p1"]["infantry"] == 2
    assert done.systems[HOME].planet_units["ixth"]["p1"]["infantry"] == 1
    assert done.active_combat is not None


@ruling("F_mahact/airo-shir-aur-benediction/3", "F_mahact/airo-shir-aur-benediction/4")
def test_benediction_anomalie_wlasciciela(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    state.systems[EMPTY_B].system_id = "44"  # asteroid field
    _bind(state, registry)
    assert (EMPTY, EMPTY_B, "p1") not in mahact.benediction_pairs(state, "p1")
    state.players["p1"].technologies = ["amd"]
    assert (EMPTY, EMPTY_B, "p1") in mahact.benediction_pairs(state, "p1")
    state.systems[EMPTY_B].system_id = "43"  # supernova
    _bind(state, registry)
    assert (EMPTY, EMPTY_B, "p1") not in mahact.benediction_pairs(state, "p1")


@ruling("F_mahact/airo-shir-aur-benediction/10")
def test_benediction_pojemnosc_przed_walka(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    state.systems[EMPTY].space_units = {"p1": {"cruiser": 1, "fighter": 3}}  # no capacity
    after = _use(state, registry, "p1", "leader", mahact.HERO,
                 {"source": EMPTY, "destination": EMPTY_B})
    assert after.systems[EMPTY_B].space_units["p1"].get("fighter", 0) == 0
    assert after.active_combat is not None


@ruling("F_mahact/airo-shir-aur-benediction/2", "F_mahact/airo-shir-aur-benediction/2.2",
        "F_mahact/airo-shir-aur-benediction/11.1")
def test_benediction_ruch_z_perspektywy_wlasciciela(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _benediction_state(registry)
    state.systems[EMPTY].space_units = {"p2": {"carrier": 1}}
    state.systems[EMPTY_B].space_units = {"p1": {"cruiser": 1}}
    seen: list[tuple[str, Any]] = []
    real = triggers.fire

    def spy(st: GameState, event: GameEvent, moment: Moment, **kw: Any) -> Any:
        seen.append((event.value, dict(kw.get("ctx") or {})))
        return real(st, event, moment, **kw)

    monkeypatch.setattr(triggers, "fire", spy)
    _use(state, registry, "p1", "leader", mahact.HERO, {"source": EMPTY, "destination": EMPTY_B})
    moved = [c for e, c in seen if e == GameEvent.SHIPS_MOVED.value]
    assert moved and moved[0]["player"] == "p2" and moved[0]["mover"] == "p1"  # 2.2 / mover
    assert GameEvent.SYSTEM_ACTIVATED.value not in [e for e, _c in seen]  # 11.1


@ruling("F_mahact/airo-shir-aur-benediction/2.1")
def test_benediction_voidwatch_daje_ten_kto_ruszyl(registry: StaticDataRegistry) -> None:
    from src.core.hooks.factions import empyrean

    assert empyrean._voidwatch_mover(GameState(), "px", {"player": "p2", "mover": "p1"}) == "p1"


@ruling("F_mahact/airo-shir-aur-benediction/2.3", "F_mahact/airo-shir-aur-benediction/7",
        "F_muaat/adjudicator-baal-nova-seed/1.1")
def test_benediction_nova_seed_nie_dla_przesunietego(registry: StaticDataRegistry) -> None:
    from src.core.hooks.factions import muaat

    ctx = {"player": "p2", "mover": "p1", "position": EMPTY_B, "ships": {"warsun": 1}}
    assert not muaat._hero_ready(_state(registry, other="muaat"), "p2", ctx)


@ruling("F_mahact/airo-shir-aur-benediction/2.3")
def test_benediction_stellar_genesis_nie_dla_przesunietego(registry: StaticDataRegistry) -> None:
    """"After you move one of your war suns" (Stellar Genesis) - not when the Mahact moved it."""
    from src.core.hooks.factions import muaat

    state = _state(registry, other="muaat")
    state.systems[EMPTY].added_planets = [muaat.AVERNUS]
    ctx = {"player": "p2", "mover": "p1", "position": EMPTY_B, "from": EMPTY,
           "route": [EMPTY, EMPTY_B], "ships": {"warsun": 1}}
    assert not muaat._carries_avernus(state, "p2", ctx)
    assert muaat._carries_avernus(state, "p2", {**ctx, "mover": "p2"})


@ruling("F_mahact/airo-shir-aur-benediction/2.1")
def test_benediction_another_player_moves_to_mahact(registry: StaticDataRegistry) -> None:
    """"After another player moves ships" (Xuange, Foresight) reads the Mahact as the mover: it
    triggers even for the owner's own ships the Mahact moved, and not for the owner's own move."""
    from src.core.hooks.factions import empyrean, naalu

    state = _state(registry, other="empyrean")
    state.systems[EMPTY_B].command_tokens = ["p2"]
    moved = {"player": "p2", "mover": "p1", "position": EMPTY_B, "from": EMPTY,
             "ships": {"destroyer": 1}}
    assert empyrean._xuange_ready(state, "p2", moved)
    assert not empyrean._xuange_ready(state, "p2", {**moved, "mover": "p2"})

    state = _state(registry, other="naalu")
    state.players["p2"].strategic_cc = 1
    state.systems[EMPTY_B].space_units = {"p2": {"destroyer": 2}}
    assert naalu._foresight_ready(state, "p2", moved)
    assert not naalu._foresight_ready(state, "p2", {**moved, "mover": "p2"})


@ruling("F_mahact/airo-shir-aur-benediction/2.1")
def test_benediction_acamar_daje_zeton_mahactowi(registry: StaticDataRegistry) -> None:
    """Acamar: "After a player moves ships ... that player gains 1 command token" - the Mahact."""
    from src.core.hooks.factions import empyrean

    state = _state(registry, other="empyrean")
    moved = {"player": "p2", "mover": "p1", "position": EMPTY_B, "from": EMPTY,
             "ships": {"destroyer": 1}}
    assert empyrean._acamar_ready(state, "p2", moved)
    empyrean.acamar(state, "p2", moved)
    assert [o.label for o in triggers.offers_for(state, "p1")
            if "Acamar" in o.label] == ["Acamar: place your command token"]
    assert not any("Acamar" in o.label for o in triggers.offers_for(state, "p2"))


@ruling("F_mahact/airo-shir-aur-benediction/5")
def test_benediction_wyjscie_ze_szczeliny_rzut(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core import movement

    state = _benediction_state(registry)
    state.systems[EMPTY].system_id = "41"  # gravity rift
    _bind(state, registry)
    calls: list[str] = []

    def fake_roll(_st: GameState, pid: str, _units: Any, position: str | None = None
                  ) -> dict[str, int]:
        calls.append(pid)
        return {}

    monkeypatch.setattr(movement, "roll_rift_exit", fake_roll)
    _use(state, registry, "p1", "leader", mahact.HERO, {"source": EMPTY, "destination": EMPTY_B})
    assert calls == ["p1"]


@ruling("F_mahact/airo-shir-aur-benediction/1.2")
def test_benediction_plywajace_fabryki_saar(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    state.players["p2"].faction = "saar"
    state.systems[EMPTY].space_units = {"p2": {"carrier": 1, "spacedock": 1}}
    state.systems[EMPTY_B].space_units = {"p1": {"cruiser": 1}}
    after = _use(state, registry, "p1", "leader", mahact.HERO,
                 {"source": EMPTY, "destination": EMPTY_B})
    assert after.systems[EMPTY_B].space_units["p2"].get("spacedock") == 1


@ruling("F_mahact/airo-shir-aur-benediction/6")
def test_benediction_bez_splatania_creuss(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    state.players["p2"].faction = "ghost"
    state.systems[EMPTY].space_units = {}
    state.systems[EMPTY_B].space_units = {}
    state.systems[LODOR].space_units = {"p2": {"cruiser": 1}}  # Lodor: alpha wormhole
    state.systems[FAR].system_id = "25"  # Quann: beta wormhole, not adjacent to 105
    state.systems[FAR].space_units = {"p1": {"cruiser": 1}}
    grid = _bind(state, registry)
    assert FAR in board_graph.neighbors_for_player(state, grid, "p2", LODOR)  # Creuss's own
    assert (LODOR, FAR, "p2") not in mahact.benediction_pairs(state, "p1")


@ruling("F_mahact/airo-shir-aur-benediction/12.2")
def test_benediction_bez_betray_a_friend(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    state.tactical_pn_owners = ["p2"]  # left over from an earlier tactical action
    after = _use(state, registry, "p1", "leader", mahact.HERO,
                 {"source": EMPTY, "destination": EMPTY_B})
    assert after.tactical_pn_owners == []


@ruling("leaders:mahacthero#unlock")
def test_benediction_odblokowanie_trzy_cele(registry: StaticDataRegistry) -> None:
    leader = registry.leaders[mahact.HERO]
    assert leader.unlock_condition == "Have 3 scored objectives."
    assert leaders._norm(leader.unlock_condition) in leaders._BY_CONDITION


def test_benediction_zamkniecie_walki_czysci_aktywny_system(registry: StaticDataRegistry) -> None:
    state = _benediction_state(registry)
    after = _use(state, registry, "p1", "leader", mahact.HERO,
                 {"source": EMPTY, "destination": EMPTY_B})
    assert after.active_combat is not None
    after.active_combat.step = CombatStep.DONE
    closed = battle.close_combat(after)
    assert closed.active_system is None and closed.active_combat is None


# ======================================================================== Scepter of Dominion


def _scepter_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry, third="hacan")
    state.phase = Phase.STRATEGY
    state.speaker_id = "p1"
    state.players["p1"].foreign_fleet_tokens = ["p3"]
    state.systems[LODOR].space_units = {"p2": {"cruiser": 1}}
    note = "scepter"
    promissory_notes.set_hand(state, "p2", [note])
    return state


@ruling("promissory_notes:scepter#1", "promissory_notes:scepter#2", "promissory_notes:scepter#3",
        "F_mahact/scepter-of-dominion/3")
def test_scepter_zetony_w_systemie(registry: StaticDataRegistry) -> None:
    state = _scepter_state(registry)
    assert mahact.scepter_systems(state, "p2") == [LODOR]
    assert mahact.scepter_placers(state, "p2") == ["p1", "p3"]  # the Mahact too (3)
    after, _ok = promissory_play.play(state, registry, "p2", "scepter", {"system": LODOR})
    assert sorted(after.systems[LODOR].command_tokens) == ["p1", "p3"]
    assert "scepter" in after.players["p1"].private.promissory_notes  # returned


@ruling("F_mahact/scepter-of-dominion/1", "F_mahact/scepter-of-dominion/2")
def test_scepter_istniejacy_zeton_i_pusta_rezerwa(registry: StaticDataRegistry) -> None:
    state = _scepter_state(registry)
    state.systems[LODOR].command_tokens = ["p1"]
    state.players["p3"].cc_reinf = 0
    after, _ok = promissory_play.play(state, registry, "p2", "scepter", {"system": LODOR})
    assert after.systems[LODOR].command_tokens == ["p1"]  # no second token (1)
    done = _accept(after, "p3", "Scepter", {"pool": "tactical"})
    assert sorted(done.systems[LODOR].command_tokens) == ["p1", "p3"]
    assert done.players["p3"].tactical_cc == 2


@ruling("F_mahact/scepter-of-dominion/4")
def test_scepter_nie_w_domu_wyeliminowanego(registry: StaticDataRegistry) -> None:
    state = _scepter_state(registry)
    state.systems[FAR].space_units = {"p2": {"cruiser": 1}}
    state.eliminated_players = [EliminatedPlayer(player_id="px", home_position=FAR)]
    assert FAR not in mahact.scepter_systems(state, "p2")


# ============================================================================== Arvicon Rex


@ruling("units:mahact_flagship#1")
def test_arvicon_rex_plus_dwa(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.active_combat = ActiveCombat(kind="space", position=HOME, attacker="p2",
                                              defender="p1")
    ctx = {"base_type": "flagship"}
    assert mahact.arvicon_rex(state, "p1", ctx) == 2
    assert mahact.arvicon_rex(state, "p1", {"base_type": "carrier"}) == 0
    state.players["p1"].foreign_fleet_tokens = ["p2"]
    assert mahact.arvicon_rex(state, "p1", ctx) == 0


# ================================================================================ Starlancer


def _starlancer_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry)
    state.systems[LODOR].planet_units = {"lodor": {"p1": {"mech": 1}}}
    state.systems[LODOR].planet_owners = {"lodor": "p1"}
    state.players["p1"].foreign_fleet_tokens = ["p2"]
    state.active_player_id = "p2"
    return state


@ruling("units:mahact_mech#1", "units:mahact_mech#2", "F_mahact/starlancer/1",
        "F_mahact/starlancer/2", "F_mahact/starlancer/2.1", "F_mahact/starlancer/3")
def test_starlancer_konczy_ture(registry: StaticDataRegistry) -> None:
    state = _starlancer_state(registry)
    grid = _bind(state, registry)
    after = tactical.activate_system(state, grid, LODOR)
    assert _offers(after, "p1", "Starlancer")
    done = _accept(after, "p1", "Starlancer")
    assert done.players["p1"].foreign_fleet_tokens == []
    assert not [o for o in done.pending_offers if o.event == GameEvent.SYSTEM_ACTIVATED.value]
    gain = _offers(done, "p2", "Starlancer")[0]
    assert "auto" not in _inputs(done, registry, gain)[0]
    tactic = done.players["p2"].tactical_cc
    done = _accept(done, "p2", "Starlancer", {"pool": "strategic"})
    assert done.players["p2"].strategic_cc == state.players["p2"].strategic_cc + 1
    assert done.players["p2"].tactical_cc == tactic
    assert done.active_player_id != "p2"  # their turn ended


@ruling("F_mahact/starlancer/4")
def test_starlancer_wlasna_tura_wlasny_zeton(registry: StaticDataRegistry) -> None:
    state = _starlancer_state(registry)
    state.active_player_id = "p1"
    grid = _bind(state, registry)
    after = tactical.activate_system(state, grid, LODOR)
    assert _offers(after, "p1", "Starlancer")
    done = _accept(after, "p1", "Starlancer")
    assert done.players["p1"].fleet_cc == 2


# ========================================================================== Vaults of the Heir


@ruling("breakthroughs:mahactbt#1", "F_mahact/vaults-of-the-heir/1",
        "F_mahact/vaults-of-the-heir/1.1", "F_mahact/vaults-of-the-heir/2")
def test_vaults_purge_i_relikt(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    p1 = state.players["p1"]
    p1.breakthrough_unlocked = True
    p1.technologies = ["amd", "gr"]
    p1.exhausted_technologies = ["gr"]  # exhausted may be purged (1.1)
    after = _use(state, registry, "p1", "breakthrough", mahact.BREAKTHROUGH, {"technology": "gr"})
    assert after.players["p1"].technologies == ["amd"]
    assert after.players["p1"].purged_technologies == ["gr"]
    assert len(after.players["p1"].relics) == 1
    assert after.players["p1"].breakthrough_exhausted
    with pytest.raises(ValueError, match="purged"):
        technology.grant_technology(after, "p1", "gr")
    pool = technology.tech_pool(after, registry, "p1")
    assert "gr" not in pool  # never researchable again (2)


@ruling("F_mahact/vaults-of-the-heir/3")
def test_vaults_purge_antimass(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies = ["amd"]
    technology.purge_technology(state, "p1", "amd")
    assert not rules_hooks.permits(rules_hooks.POINT_MOVEMENT_ENTER_ASTEROIDS, state, "p1")


@ruling("F_mahact/vaults-of-the-heir/4")
def test_vaults_purge_war_sun(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies = ["ws"]
    state.systems[EMPTY].space_units = {"p1": {"warsun": 1}}
    technology.purge_technology(state, "p1", "ws")
    assert state.systems[EMPTY].space_units.get("p1", {}).get("warsun", 0) == 0



# ============================================================= Cross-faction rulings (Mahact)


@ruling("F_naalu/neuroglaive/1")
def test_neuroglaive_zwraca_obcy_zeton_wlascicielowi(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="naalu", third="hacan")
    state.players["p2"].technologies = ["ng"]
    state.systems[EMPTY].space_units = {"p2": {"cruiser": 1}}
    p1 = state.players["p1"]
    p1.fleet_cc, p1.foreign_fleet_tokens = 0, ["p3"]
    grid = _bind(state, registry)
    reinf = state.players["p3"].cc_reinf
    after = tactical.activate_system(state, grid, EMPTY)
    assert after.players["p1"].foreign_fleet_tokens == []
    assert after.players["p3"].cc_reinf == reinf + 1


@ruling("F_yin/yin-ascendant/1.1")
def test_yin_z_alliance_mahact_ma_il_na_viroset(registry: StaticDataRegistry) -> None:
    from src.core import active_effects
    from src.core.game_events import Duration

    state = _state(registry, other="yin")
    assert not tactical.can_activate_own_token(state, "p2", EMPTY)
    active_effects.add_effect(state, "yin:test", Duration.GAME, owner="p2",
                              data={"commanders": [mahact.COMMANDER]})
    assert tactical.can_activate_own_token(state, "p2", EMPTY)


@ruling("C_agendas/armed-forces-standardization/1")
def test_standaryzacja_mahact_wybiera_zetony(registry: StaticDataRegistry) -> None:
    from src.core.hooks import agendas_directives

    state = _state(registry, third="hacan")
    p1 = state.players["p1"]
    p1.fleet_cc, p1.foreign_fleet_tokens = 1, ["p2", "p3"]
    agendas_directives._standardization(state, "p1", {})
    assert command_tokens.fleet_pool_count(state, "p1") == 3
    assert (p1.fleet_cc, p1.tactical_cc, p1.strategic_cc) == (1, 3, 2)
    offer = _offers(state, "p1", "Armed Forces Standardization")[0]
    assert all("auto" not in f for f in _inputs(state, registry, offer))
    reinf = state.players["p2"].cc_reinf
    done = _accept(state, "p1", "Armed Forces Standardization",
                   {"token|p2": "return", "token|p3": "keep"})
    assert done.players["p1"].foreign_fleet_tokens == ["p3"]
    assert done.players["p2"].cc_reinf == reinf + 1  # back to its owner
    assert command_tokens.fleet_pool_count(done, "p1") == 3


@ruling("F_creuss/sai-seravus/2.2")
def test_benediction_sai_seravus_dla_creuss(registry: StaticDataRegistry) -> None:
    from src.core.hooks.factions import ghost

    state = _benediction_state(registry)
    state.players["p2"].faction = "ghost"
    state.players["p2"].leader_states = {ghost.COMMANDER: leaders.UNLOCKED}
    state.systems[EMPTY].space_units = {}
    state.systems[EMPTY_B].space_units = {}
    state.systems[LODOR].space_units = {"p2": {"carrier": 1}}  # alpha wormhole
    state.systems[FAR].system_id = "39"  # alpha wormhole, not on the ring next to 105
    state.systems[FAR].space_units = {"p1": {"cruiser": 1}}
    _bind(state, registry)
    assert (LODOR, FAR, "p2") in mahact.benediction_pairs(state, "p1")
    after = _use(state, registry, "p1", "leader", mahact.HERO,
                 {"source": LODOR, "destination": FAR})
    assert _offers(after, "p2", "Sai Seravus")
    assert after.active_combat is not None
    assert after.active_combat.step is CombatStep.TRIGGERS  # waits for the offer
