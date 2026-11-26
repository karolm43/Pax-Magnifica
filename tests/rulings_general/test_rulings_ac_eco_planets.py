"""Action card rulings - economy, technology and planets (``C_action_cards.md``).

Basic card behaviour lives in ``tests/test_action_cards_*.py`` / ``tests/test_reactions_*.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    action_cards,
    card_draw,
    card_hold,
    control,
    custodians,
    hand_limit,
    invasion,
    movement,
    rules_hooks,
    status_phase,
    strategy_phase,
    technology,
)
from src.core.game_state import (
    ActionDiscardTrace,
    EliminatedPlayer,
    GameState,
    InvasionPhase,
    InvasionState,
    Phase,
    PlayerState,
    SystemState,
)
from src.core.hooks import agendas_laws
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry
from tests import test_action_cards_economy as eco
from tests import test_reactions_agenda as agenda_h
from tests import test_reactions_combat as combat_h
from tests import test_reactions_misc as misc_h
from tests import test_reactions_tactical as tactical_h
from tests import test_status_phase as status_h
from tests.rulings import ruling
from tests.test_reactions_combat import _bound_grid as _bound_grid  # noqa: F401 - autouse fixture
from tests.test_reactions_combat import grid as grid  # noqa: F401 - fixture

_CARDS = "C_action_cards"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _playable(state: GameState, registry: StaticDataRegistry, card: str) -> bool:
    return bool(eco._playable(state, registry, card)["playable"])


# ===================================================================== Ancient Burial Sites


@ruling(f"{_CARDS}/ancient-burial-sites/1")
def test_burial_sites_only_before_the_first_agenda(registry: StaticDataRegistry) -> None:
    from src.core import agenda_phase

    state = agenda_h._state(registry, [agenda_h.LAW, agenda_h.DIRECTIVE])
    agenda_h._hand(state, "p1", "abs")
    assert agenda_h._playable(state, registry, "p1", "abs")
    revealed = agenda_phase.reveal_agenda(state, registry, "p2")
    assert not agenda_h._playable(revealed, registry, "p1", "abs")


@ruling(f"{_CARDS}/ancient-burial-sites/2")
def test_burial_sites_may_choose_a_player_without_cultural_planets(
    registry: StaticDataRegistry,
) -> None:
    state = agenda_h._state(registry, [agenda_h.LAW])
    agenda_h._hand(state, "p1", "abs")
    state.systems["101"].planet_owners = {"wellon": "p3"}  # industrial only
    new = agenda_h._play(state, registry, "p1", "abs", player="p3")
    assert new.players["p3"].exhausted_planets == []


# ================================================================= Archaeological Expedition


@ruling(f"{_CARDS}/archaeological-expedition/1")
def test_expedition_needs_a_planet_with_a_trait(registry: StaticDataRegistry) -> None:
    assert not _playable(eco._state(["arch_expedition"], mine=("mr",)), registry, "arch_expedition")
    assert _playable(eco._state(["arch_expedition"], mine=("abyz",)), registry, "arch_expedition")


# ============================================================================ Divert Funding


def _diverted(
    registry: StaticDataRegistry, techs: list[str], returned: str, **kwargs: Any
) -> tuple[GameState, list[str]]:
    state = eco._state(["divert_funding"], technologies=techs, **kwargs)
    played = eco._play(state, registry, "divert_funding", {"return_technology": returned})
    offer = next(o for o in played.pending_offers if "research_cost" in o.ctx)
    return played, list(offer.ctx["research_allowed"])


@ruling(f"{_CARDS}/divert-funding/1", f"{_CARDS}/divert-funding/1.1",
        f"{_CARDS}/divert-funding/3")
def test_divert_funding_prerequisites_without_the_returned_one(
    registry: StaticDataRegistry,
) -> None:
    # Dacxive needs 1 green; Neural Motivator (returned) was the only green one.
    played, allowed = _diverted(registry, ["nm", "st"], "nm")
    assert "dxa" not in allowed and "nm" not in allowed
    for tech in ("dxa", "nm"):
        with pytest.raises(ValueError):
            eco._research(played, tech)


@ruling(f"{_CARDS}/divert-funding/2")
def test_divert_funding_may_research_unit_upgrades_and_faction_technology(
    registry: StaticDataRegistry,
) -> None:
    owned = ["nm", "amd", "gd", "sar", "st"]
    played, allowed = _diverted(registry, owned, "st")
    upgrades = [t for t in allowed if technology.UNIT_UPGRADE in registry.technologies[t].types
                or not registry.technologies[t].types]
    assert upgrades and any(registry.technologies[t].faction for t in allowed)
    new = eco._research(played, upgrades[0])
    assert upgrades[0] in new.players["p1"].technologies


@ruling(f"{_CARDS}/divert-funding/4")
def test_divert_funding_returned_technology_comes_back_readied(
    registry: StaticDataRegistry,
) -> None:
    played, _ = _diverted(registry, ["nm", "st"], "st", exhausted_technologies=["st"])
    technology.grant_technology(played, "p1", "st")
    assert "st" in played.players["p1"].technologies
    assert "st" not in played.players["p1"].exhausted_technologies


@ruling(f"{_CARDS}/divert-funding/5")
def test_divert_funding_without_antimass_ships_only_leave_the_asteroid_field(
    registry: StaticDataRegistry,
) -> None:
    grid = tactical_h._grid(
        ("000", "44", {"ASTEROID_FIELD"}, []), ("101", "20", set(), []),
    )
    state = eco._state(["divert_funding"], technologies=["amd", "st"])
    state.systems = {
        "000": SystemState(position="000", system_id="44", space_units={"p1": {"destroyer": 1}}),
        "101": SystemState(position="101", system_id="20", space_units={"p1": {"destroyer": 1}}),
    }
    assert movement.entry_blocked(grid, state, "000", "p1") is None
    new = eco._play(state, registry, "divert_funding", {"return_technology": "amd"})
    assert new.systems["000"].space_units["p1"] == {"destroyer": 1}  # they remain
    new.tactical_step = None
    assert movement.entry_blocked(grid, new, "000", "p1") is not None  # no more units into it
    new.active_system = "101"
    ok, reason = movement.can_move(new, grid, registry, "000", "destroyer", "p1")
    assert ok, reason  # and they may move out
    new.active_system = "000"
    assert not movement.can_move(new, grid, registry, "101", "destroyer", "p1")[0]


# ======================================================================= Economic Initiative


@ruling(f"{_CARDS}/economic-initiative/1")
def test_economic_initiative_without_cultural_planets(registry: StaticDataRegistry) -> None:
    state = eco._state(["economic_initiative"], mine=("abyz",))
    assert _playable(state, registry, "economic_initiative")
    new = eco._play(state, registry, "economic_initiative")
    assert new.players["p1"].private.action_cards == []


# ========================================================================== Exchange Program


def _exchange_state() -> GameState:
    state = eco._state(["exchangeprogram"], mine=("wellon",), theirs=("abyz",))
    state.systems["000"].planet_units = {"wellon": {"p1": {"infantry": 1}}}
    state.systems["101"].planet_units = {"abyz": {"p2": {"infantry": 1}}}
    for player in state.players.values():
        player.fleet_cc = 3
    return state


@ruling(f"{_CARDS}/exchange-program/1")
def test_exchange_program_player_need_not_agree(registry: StaticDataRegistry) -> None:
    state = _exchange_state()
    new = eco._play(state, registry, "exchangeprogram", {"player": "p2", "agreed": False})
    assert new.systems["101"].planet_units == state.systems["101"].planet_units
    assert new.players["p1"].fleet_cc == 2 and new.players["p2"].fleet_cc == 2


@ruling(f"{_CARDS}/exchange-program/2")
def test_exchange_program_agreement_names_the_planets(registry: StaticDataRegistry) -> None:
    state = _exchange_state()
    with pytest.raises(ValueError, match="their_planet"):
        action_cards.play_action_card(
            state, registry, "p1", "exchangeprogram", {"player": "p2", "agreed": True}
        )
    new = eco._play(
        state, registry, "exchangeprogram",
        {"player": "p2", "agreed": True, "their_planet": "abyz", "my_planet": "wellon"},
    )
    assert new.systems["101"].planet_units["abyz"]["p1"] == {"infantry": 1}
    assert new.systems["000"].planet_units["wellon"]["p2"] == {"infantry": 1}


# =========================================================================== Focused Research


@ruling(f"{_CARDS}/focused-research/1")
def test_focused_research_needs_four_trade_goods(registry: StaticDataRegistry) -> None:
    assert not _playable(eco._state(["f_researched"], trade_goods=3), registry, "f_researched")
    assert _playable(eco._state(["f_researched"], trade_goods=4), registry, "f_researched")


@ruling(f"{_CARDS}/focused-research/2")
def test_focused_research_needs_prerequisites(registry: StaticDataRegistry) -> None:
    played = eco._play(eco._state(["f_researched"], trade_goods=4), registry, "f_researched")
    with pytest.raises(ValueError, match="Prerequisites"):
        eco._research(played, "dxa")


@ruling(f"{_CARDS}/focused-research/3")
def test_focused_research_names_no_technology_before_sabotage(
    registry: StaticDataRegistry,
) -> None:
    state = eco._state(["f_researched"], trade_goods=4)
    state.players["p2"].private.action_cards = ["sabo1"]
    state.decks.action_card_deck = ["filler"]
    held, _ = action_cards.play_action_card(
        state, registry, "p1", "f_researched", {}, now=100.0
    )
    assert held.held_play is not None and held.held_play.params == {}
    assert not held.pending_offers  # the research choice does not exist yet
    released = card_hold.resolve(held, registry)
    assert any("research_cost" in o.ctx for o in released.pending_offers)


# ====================================================================== Frontline Deployment


@ruling(f"{_CARDS}/frontline-deployment/1")
def test_frontline_deployment_puts_all_three_on_one_planet(
    registry: StaticDataRegistry,
) -> None:
    state = eco._state(["f_deployment"], mine=("wellon", "faunus"))
    new = eco._play(state, registry, "f_deployment", {"planet": "wellon"})
    assert new.systems["000"].planet_units == {"wellon": {"p1": {"infantry": 3}}}
    inputs = eco._inputs(state, registry, "f_deployment")
    assert [(i["key"], i["kind"]) for i in inputs] == [("planet", "choice")]


# ============================================================================= Harness Energy


@ruling(f"{_CARDS}/harness-energy/1")
def test_harness_energy_at_maximum_commodities_still_replenishes(
    registry: StaticDataRegistry,
) -> None:
    anomaly = next(s.id for s in registry.systems.values() if s.is_nebula)
    state = tactical_h._state({"p1": ["harness"]}, system_id=anomaly)
    state.players["p1"].commodity_value = 3
    state.players["p1"].commodities = 3
    state.players["p2"].private.promissory_notes = ["red_ta"]  # p1 is red
    assert tactical_h._playable(state, registry, "p1", "harness")
    new = tactical_h._play(state, registry, "p1", "harness")
    assert new.players["p1"].commodities == 3 and "p1" in new.last_replenished
    from src.core import promissory_play

    rows = promissory_play.playability(new, registry, "p2")
    assert next(r for r in rows if r["note_id"] == "red_ta")["playable"]


# ============================================================================== Impersonation


@ruling(f"{_CARDS}/impersonation/1")
def test_impersonation_needs_three_available_influence(registry: StaticDataRegistry) -> None:
    poor = eco._state(["impersonation"], trade_goods=2)
    poor.decks.secret_objective_deck = ["s1"]
    assert not _playable(poor, registry, "impersonation")
    rich = eco._state(["impersonation"], trade_goods=3)
    rich.decks.secret_objective_deck = ["s1"]
    assert _playable(rich, registry, "impersonation")
    from_planets = eco._state(["impersonation"], mine=("mr",))  # 6 influence
    assert _playable(from_planets, registry, "impersonation")
    from_planets.players["p1"].exhausted_planets = ["mr"]
    assert not _playable(from_planets, registry, "impersonation")


@ruling(f"{_CARDS}/impersonation/2")
def test_impersonation_fourth_secret_then_returns_an_unscored_one(
    registry: StaticDataRegistry,
) -> None:
    state = eco._state(["impersonation"], trade_goods=3)
    state.players["p1"].private.secret_objectives = ["a", "b", "c"]
    state.decks.secret_objective_deck = ["d"]
    new = eco._play(state, registry, "impersonation", {"trade_goods": 3, "return": "a"})
    assert sorted(new.players["p1"].private.secret_objectives) == ["b", "c", "d"]
    assert new.decks.secret_objective_deck == ["a"]


def test_impersonation_return_options_use_full_objective_names(
    registry: StaticDataRegistry,
) -> None:
    from src.core import objectives
    from src.core.components import ComponentCategory

    secrets = sorted(registry.catalog.all(ComponentCategory.SECRET_OBJECTIVE))[:3]
    state = eco._state(["impersonation"], trade_goods=3)
    state.players["p1"].private.secret_objectives = list(secrets)
    state.decks.secret_objective_deck = ["d"]
    field = next(i for i in eco._inputs(state, registry, "impersonation") if i["key"] == "return")
    named = [o for o in field["options"] if o["value"] in secrets]
    assert len(named) == 3
    for option in named:
        definition = objectives.objective_def(registry, option["value"])
        assert definition is not None and definition.name
        assert option["label"] == f"Return {definition.name}"  # never the raw id
        assert option["meta"]["ref"] == {"kind": "objective", "id": option["value"]}


@ruling(f"{_CARDS}/impersonation/2.1")
def test_impersonation_with_three_scored_secrets_shuffles_the_draw_back(
    registry: StaticDataRegistry,
) -> None:
    state = eco._state(["impersonation"], trade_goods=3, scored_secrets=["a", "b", "c"])
    state.decks.secret_objective_deck = ["d"]
    assert _playable(state, registry, "impersonation")
    new = eco._play(state, registry, "impersonation", {"trade_goods": 3, "return": "drawn"})
    assert new.players["p1"].private.secret_objectives == []
    assert new.decks.secret_objective_deck == ["d"]


# ====================================================================== Manipulate Investments


@ruling(f"{_CARDS}/manipulate-investments/1")
def test_investments_playable_while_a_card_is_kept_through_political_stability(
    registry: StaticDataRegistry,
) -> None:
    state = misc_h._strategy_state({"p2": ["investments"]})
    state.players["p1"].strategy_cards = [1]  # kept through Political Stability, not picked
    assert misc_h._playable(state, registry, "p2", "investments")["playable"]
    new = misc_h._play(state, registry, "p2", "investments", {"tg_1": 2, "tg_4": 2, "tg_7": 1})
    assert new.strategy_card_tg[1] == 2  # trade goods may sit on the kept card
    picker = strategy_phase.next_strategy_picker(new)
    assert picker is not None and picker != "p1"
    picked = strategy_phase.pick_strategy_card(new, registry, picker, 4)
    assert not misc_h._playable(picked, registry, "p2", "investments")["playable"]


@ruling(f"{_CARDS}/manipulate-investments/1.1")
def test_investments_stay_on_a_card_taken_with_imperial_arbiter(
    registry: StaticDataRegistry,
) -> None:
    state = misc_h._strategy_state({})
    state.players["p1"].strategy_cards = [1]  # kept through Political Stability
    state.players["p2"].strategy_cards = [5]
    strategy_phase.add_trade_goods_to_card(state, 1, 3)  # placed by Manipulate Investments
    state.decks.agenda_laws = {"arbiter": "p2"}
    agendas_laws._arbiter(state, "p2", {"params": {"swap": "5|p1|1"}})
    assert state.players["p2"].strategy_cards == [1]
    assert state.strategy_card_tg[1] == 3 and state.players["p2"].trade_goods == 0


# ========================================================================= Mercenary Contract


def _mercenary(
    registry: StaticDataRegistry, planet: str, position: str, system_id: str
) -> GameState:
    """p2's ``planet`` is taken away by p1's Mercenary Contract."""
    state = eco._state(["mercenarycontract"], trade_goods=2)
    state.systems[position] = SystemState(
        position=position, system_id=system_id, planet_owners={planet: "p2"}
    )
    state.players["p2"].controlled_planets = [planet]
    return state


def _play_mercenary(
    registry: StaticDataRegistry, state: GameState, planet: str, position: str
) -> GameState:
    return eco._play(
        state, registry, "mercenarycontract", {"position": position, "planet": planet}
    )


def _land(state: GameState, registry: StaticDataRegistry, planet: str, position: str) -> None:
    """p1 wins the planet from the neutral infantry and establishes control (mutates)."""
    system = state.systems[position]
    system.planet_units[planet] = {"p1": {"infantry": 1}}
    state.active_system = position
    state.invasion = InvasionState(
        position=position, attacker="p1", phase=InvasionPhase.ESTABLISH,
        committed={planet: {"infantry": 1}},
    )
    invasion._establish_control(state, registry)


@ruling(f"{_CARDS}/mercenary-contract/1")
def test_mercenary_cannot_target_own_planet(registry: StaticDataRegistry) -> None:
    state = _mercenary(registry, "wellon", "201", "19")
    state.systems["201"].planet_owners = {"wellon": "p1"}
    with pytest.raises(ValueError, match="not yours"):
        _play_mercenary(registry, state, "wellon", "201")


@ruling(f"{_CARDS}/mercenary-contract/2", f"{_CARDS}/mercenary-contract/3")
def test_mercenary_returned_planet_loses_its_owner_and_is_explored_again(
    registry: StaticDataRegistry,
) -> None:
    new = _play_mercenary(registry, _mercenary(registry, "wellon", "201", "19"), "wellon", "201")
    assert "wellon" not in new.systems["201"].planet_owners
    assert new.players["p2"].controlled_planets == []
    _land(new, registry, "wellon", "201")
    assert new.systems["201"].planet_owners["wellon"] == "p1"
    assert new.exploration is not None


@ruling("R_elimination/notes/2", "R_elimination/notes/2.1")
@pytest.mark.parametrize("recorded", [True, False])
def test_mercenary_spares_an_eliminated_players_home_planet(
    registry: StaticDataRegistry, recorded: bool
) -> None:
    """Same home-system rule as Reactor Meltdown / Uprising, with or without ``home_position``."""
    from src.core import board_graph
    from src.core.hooks.action_cards_board import mercenary_targets
    from src.core.hooks.card_targets_economy import home_planet_ids

    home = registry.factions["hacan"]
    planet = home.home_planets[0]
    state = eco._state(["mercenarycontract"], trade_goods=2)
    state.systems["301"] = SystemState(position="301", system_id=str(home.home_system))
    state.eliminated_players = [EliminatedPlayer(
        player_id="p3", faction="hacan", color="green", round_number=1,
        home_position="301" if recorded else None,
    )]
    assert planet in home_planet_ids(state, registry)  # Meltdown / Uprising view
    assert "301" not in board_graph.non_home_systems(state, registry)  # Mercenary view
    assert all(p != planet for _pos, p in mercenary_targets(state, registry, "p1"))
    with pytest.raises(ValueError, match="non-home"):
        _play_mercenary(registry, state, planet, "301")


@ruling(f"{_CARDS}/mercenary-contract/3.1")
def test_mercenary_traitless_planet_is_not_explored_but_fracture_gives_a_relic(
    registry: StaticDataRegistry,
) -> None:
    new = _play_mercenary(registry, _mercenary(registry, "mr", "201", "18"), "mr", "201")
    new.custodians_removed = True
    _land(new, registry, "mr", "201")
    assert new.exploration is None

    fracture = _mercenary(registry, "styx", "frac4", "fracture4")
    control.set_planet_control(fracture, "frac4", "styx", None, registry)  # card returned
    before = len(fracture.players["p1"].relics)
    control.set_planet_control(fracture, "frac4", "styx", "p1", registry)
    assert len(fracture.players["p1"].relics) == before + 1


@ruling(f"{_CARDS}/mercenary-contract/4")
def test_mercenary_on_mecatol_does_not_put_the_custodians_token_back(
    registry: StaticDataRegistry,
) -> None:
    state = _mercenary(registry, "mr", "201", "18")
    state.custodians_removed = True
    new = _play_mercenary(registry, state, "mr", "201")
    assert new.custodians_removed and not custodians.on_board(new)
    assert custodians.landing_blocked(new, registry, "201") == set()
    _land(new, registry, "mr", "201")  # no influence paid, no point
    assert new.systems["201"].planet_owners["mr"] == "p1"
    assert not new.objectives.scored.get(custodians.SCORE_KEY)
    assert new.players["p1"].trade_goods == 0


@ruling(f"{_CARDS}/mercenary-contract/4.1")
def test_agenda_phase_still_happens_after_mercenary_on_mecatol(
    registry: StaticDataRegistry,
) -> None:
    state = status_h._state(registry)
    state.custodians_removed = True
    state.systems["201"] = SystemState(
        position="201", system_id="18", planet_owners={"mr": "p2"}
    )
    state.players["p1"].trade_goods = 2
    effect = rules_hooks.effect_for("action_cards:mercenarycontract")
    assert effect is not None
    effect(state, registry, "p1", {"position": "201", "planet": "mr"})
    state = status_h._finish_all_scoring(status_h._enter_status(state), registry)
    for pid in ("p1", "p2", "p3"):
        player = state.players[pid]
        state = status_phase.redistribute(
            state, registry, pid, player.tactical_cc + 2, player.fleet_cc, player.strategic_cc
        )
    assert status_phase.finish_status(state, registry).phase is Phase.AGENDA


@ruling(f"{_CARDS}/mercenary-contract/5", f"{_CARDS}/mercenary-contract/5.1")
def test_mercenary_legendary_card_is_lost_and_comes_back_readied(
    registry: StaticDataRegistry,
) -> None:
    state = _mercenary(registry, "primor", "201", "65")
    state.players["p2"].exhausted_legendaries = ["primor"]
    new = _play_mercenary(registry, state, "primor", "201")
    assert "primor" not in new.players["p2"].controlled_planets
    assert "primor" not in new.players["p2"].exhausted_legendaries
    control.set_planet_control(new, "201", "primor", "p1", registry)
    assert "primor" in new.players["p1"].controlled_planets
    assert "primor" not in new.players["p1"].exhausted_legendaries


@ruling(f"{_CARDS}/mercenary-contract/6")
def test_mercenary_purges_attachments_of_the_returned_planet(
    registry: StaticDataRegistry,
) -> None:
    state = _mercenary(registry, "wellon", "201", "19")
    state.planet_attachments = {"wellon": ["attach1", "attach2"]}
    new = _play_mercenary(registry, state, "wellon", "201")
    assert "wellon" not in new.planet_attachments
    assert {"attach1", "attach2"} <= set(new.decks.purged)


# ============================================================================ Mining Initiative


@ruling(f"{_CARDS}/mining-initiative/1")
def test_mining_initiative_does_not_exhaust(registry: StaticDataRegistry) -> None:
    state = eco._state(["mining_initiative"], mine=("abyz",))
    new = eco._play(state, registry, "mining_initiative", {"planet": "abyz"})
    assert new.players["p1"].trade_goods == registry.planets["abyz"].resources
    assert new.players["p1"].exhausted_planets == []


# ================================================================================= Plagiarize


@ruling(f"{_CARDS}/plagiarize/1")
def test_plagiarize_needs_five_available_influence(registry: StaticDataRegistry) -> None:
    state = eco._state(["plagiarize"], trade_goods=4)
    state.players["p2"].technologies = ["nm"]
    assert not _playable(state, registry, "plagiarize")
    state.players["p1"].trade_goods = 5
    assert _playable(state, registry, "plagiarize")


@ruling(f"{_CARDS}/plagiarize/2")
def test_plagiarize_ignores_prerequisites(registry: StaticDataRegistry) -> None:
    state = eco._state(["plagiarize"], trade_goods=5)
    state.players["p2"].technologies = ["dxa"]  # needs a green technology p1 lacks
    new = eco._play(state, registry, "plagiarize", {"technology": "dxa", "trade_goods": 5})
    assert "dxa" in new.players["p1"].technologies


@ruling(f"{_CARDS}/plagiarize/4")
def test_plagiarize_faction_upgrade_does_not_give_the_generic_one(
    registry: StaticDataRegistry,
) -> None:
    state = eco._state(["plagiarize"], trade_goods=5)
    faction_upgrade = next(
        t for t in registry.technologies.values() if t.faction == "sol" and t.base_upgrade
    )
    state.players["p1"].faction = "arborec"
    state.players["p2"].faction = "sol"
    state.players["p2"].technologies = [faction_upgrade.id]
    assert faction_upgrade.base_upgrade is not None
    for tech_id in (faction_upgrade.id, faction_upgrade.base_upgrade):
        with pytest.raises(ValueError, match="non-faction"):
            action_cards.play_action_card(
                state, registry, "p1", "plagiarize",
                {"technology": tech_id, "trade_goods": 5},
            )


# ===================================================================================== Plague


@ruling(f"{_CARDS}/plague/1")
def test_plague_may_target_a_planet_without_infantry(registry: StaticDataRegistry) -> None:
    state = eco._state(["plague"], theirs=("abyz",))
    assert _playable(state, registry, "plague")
    assert eco._option_values(eco._inputs(state, registry, "plague"), "planet") == ["abyz"]
    new = eco._play(state, registry, "plague", {"planet": "abyz"})
    assert new.players["p1"].private.action_cards == []


@ruling(f"{_CARDS}/plague/2")
def test_plague_cannot_target_neutral_infantry(registry: StaticDataRegistry) -> None:
    state = eco._state(["plague"])
    state.systems["101"].planet_units = {"abyz": {NEUTRAL_PLAYER_ID: {"infantry": 2}}}
    assert not _playable(state, registry, "plague")
    with pytest.raises(ValueError, match="controlled by another player"):
        action_cards.play_action_card(state, registry, "p1", "plague", {"planet": "abyz"})


# ============================================================================ Reactor Meltdown


@ruling(f"{_CARDS}/reactor-meltdown/1")
def test_meltdown_cannot_destroy_own_dock(registry: StaticDataRegistry) -> None:
    state = eco._state(["meltdown"], mine=("wellon",))
    state.systems["000"].planet_units = {"wellon": {"p1": {"spacedock": 1}}}
    assert not _playable(state, registry, "meltdown")


@ruling(f"{_CARDS}/reactor-meltdown/2")
def test_meltdown_spares_a_dock_in_somebody_elses_home_system(
    registry: StaticDataRegistry,
) -> None:
    state = eco._state(["meltdown"])
    state.players["p3"] = PlayerState(player_id="p3", color="green", faction="hacan")
    state.systems["101"] = SystemState(
        position="101", system_id="05", planet_units={"nestphar": {"p3": {"spacedock": 1}}}
    )  # p3's dock in the Arborec (p2) home system
    assert not _playable(state, registry, "meltdown")
    with pytest.raises(ValueError, match="non-home"):
        action_cards.play_action_card(
            state, registry, "p1", "meltdown", {"planet": "nestphar", "owner": "p3"}
        )


@ruling(f"{_CARDS}/reactor-meltdown/2.1")
def test_meltdown_spares_a_dock_in_an_eliminated_players_home_system(
    registry: StaticDataRegistry,
) -> None:
    state = eco._state(["meltdown"])
    state.eliminated_players = [
        EliminatedPlayer(player_id="p3", faction="hacan", color="green", round_number=1)
    ]
    home = registry.factions["hacan"]
    planet = home.home_planets[0]
    state.systems["101"] = SystemState(
        position="101", system_id=str(home.home_system),
        planet_units={planet: {"p2": {"spacedock": 1}}},
    )
    assert not _playable(state, registry, "meltdown")


# ================================================================================ Refit Troops


def _refit_state(mechs_elsewhere: int) -> GameState:
    state = eco._state(["refit"], mine=("wellon",))
    state.systems["000"].planet_units = {"wellon": {"p1": {"infantry": 2}}}
    state.systems["101"].space_units = {"p1": {"mech": mechs_elsewhere}}
    state.systems["101"].damaged_units = {"space": {"p1": {"mech": mechs_elsewhere}}}
    return state


@ruling(f"{_CARDS}/refit-troops/1")
def test_refit_takes_mechs_from_the_board_when_reinforcements_are_empty(
    registry: StaticDataRegistry,
) -> None:
    state = _refit_state(4)  # all 4 mechs are on the board, damaged
    assert _playable(state, registry, "refit")
    inputs = eco._inputs(state, registry, "refit")
    assert eco._option_values(inputs, "sources") == ["101|space"]
    source = next(i for i in inputs if i["key"] == "sources")["options"][0]
    assert source["meta"]["unit"] == "mech" and source["meta"]["position"] == "101"  # map pick
    params: dict[str, Any] = {"planets": ["wellon"]}
    # Auto (no source picked) = "Do not place": no mech leaves the board, infantry stays.
    kept = eco._play(state, registry, "refit", params)
    assert kept.systems["000"].planet_units["wellon"]["p1"] == {"infantry": 2}
    assert kept.systems["101"].space_units["p1"] == {"mech": 4}
    with pytest.raises(ValueError, match="sources"):
        action_cards.play_action_card(
            state, registry, "p1", "refit", {**params, "sources": ["101|space", "101|space"]}
        )
    new = eco._play(state, registry, "refit", {**params, "sources": ["101|space"]})
    assert new.systems["101"].space_units["p1"] == {"mech": 3}
    assert new.systems["000"].planet_units["wellon"]["p1"] == {"infantry": 1, "mech": 1}
    assert "wellon" not in new.systems["000"].damaged_units  # placed undamaged
    # A system with the player's own command token is not a legal source.
    state.systems["101"].command_tokens = ["p1"]
    assert not _playable(state, registry, "refit")


# ================================================================================ Reparations


def _reparations(mine_exhausted: bool, taker_ready: bool) -> GameState:
    """p2 lost ``mr`` to p1; p2 keeps ``quann``, p1 may also hold ``wellon``."""
    state = tactical_h._capture_state()
    state.players["p2"].exhausted_planets = ["quann"] if mine_exhausted else []
    control.set_planet_control(state, tactical_h.ACTIVE, "mr", "p1")
    state.players["p1"].exhausted_planets = ["mr"]
    if not taker_ready:
        state.systems["102"].planet_owners = {}
    return state


@ruling(f"{_CARDS}/reparations/1", f"{_CARDS}/reparations/1.1")
def test_reparations_needs_at_least_one_of_the_two_effects(
    registry: StaticDataRegistry,
) -> None:
    only_exhaust = _reparations(mine_exhausted=False, taker_ready=True)
    new = tactical_h._play(
        only_exhaust, registry, "p2", "reparations",
        {"planet": "mr", "exhaust_planet": "wellon", "ready_planet": ""},
    )
    assert "wellon" in new.players["p1"].exhausted_planets
    only_ready = _reparations(mine_exhausted=True, taker_ready=False)
    new = tactical_h._play(
        only_ready, registry, "p2", "reparations",
        {"planet": "mr", "exhaust_planet": "", "ready_planet": "quann"},
    )
    assert new.players["p2"].exhausted_planets == []
    neither = _reparations(mine_exhausted=False, taker_ready=False)
    assert not tactical_h._playable(neither, registry, "p2", "reparations")
    with pytest.raises(ValueError):
        tactical_h._play(
            neither, registry, "p2", "reparations",
            {"planet": "mr", "exhaust_planet": "", "ready_planet": ""},
        )


# ============================================================================ Reveal Prototype


def _prototype(
    grid: Any, registry: StaticDataRegistry, techs: list[str], trade_goods: int
) -> GameState:
    state = combat_h._state({"carrier": 1}, {"cruiser": 1}, hand1=["reveal_prototype"])
    state.players["p1"].technologies = list(techs)
    state.players["p1"].trade_goods = trade_goods
    return combat_h._start(state, grid, registry)


@ruling(f"{_CARDS}/reveal-prototype/1")
def test_reveal_prototype_needs_prerequisites(
    grid: Any, registry: StaticDataRegistry
) -> None:
    assert not combat_h._can(_prototype(grid, registry, [], 4), registry, "p1", "reveal_prototype")
    ready = _prototype(grid, registry, ["amd", "gd"], 4)
    assert combat_h._can(ready, registry, "p1", "reveal_prototype")


@ruling(f"{_CARDS}/reveal-prototype/2")
def test_reveal_prototype_needs_four_resources(
    grid: Any, registry: StaticDataRegistry
) -> None:
    state = _prototype(grid, registry, ["amd", "gd"], 3)
    assert not combat_h._can(state, registry, "p1", "reveal_prototype")


@ruling(f"{_CARDS}/reveal-prototype/3")
def test_reveal_prototype_needs_an_upgrade_the_player_does_not_own(
    grid: Any, registry: StaticDataRegistry
) -> None:
    state = _prototype(grid, registry, ["amd", "gd", "cv2"], 4)
    assert not combat_h._can(state, registry, "p1", "reveal_prototype")


# ============================================================================ Reverse Engineer


@ruling(f"{_CARDS}/reverse-engineer/1")
def test_reverse_engineer_after_play_cancel_hand_limit_or_other_discard(
    registry: StaticDataRegistry,
) -> None:
    card = misc_h._ACTION_CARD
    base = misc_h._state({"p1": [card], "p2": ["reverse_engineer"]})
    base.decks.action_card_deck = ["filler"]  # Sabotage is possible

    def takes(state: GameState) -> None:
        assert state.last_action_discard == ActionDiscardTrace(player="p1", card=card)
        new = misc_h._play(state, registry, "p2", "reverse_engineer")
        assert new.players["p2"].private.action_cards == [card]

    played, _ = action_cards.play_action_card(base, registry, "p1", card)
    takes(played)
    held, _ = action_cards.play_action_card(base, registry, "p1", card, now=100.0)
    assert held.held_play is not None
    card_hold.cancel_in_place(held)  # Sabotaged
    takes(held)
    other = base.clone()
    card_draw.discard_action_cards(other, "p1", 1)  # another game effect
    takes(other)
    over = base.clone()
    rules_hooks.bind_registry(registry)
    limit = hand_limit.action_card_limit(over, "p1")
    assert limit is not None
    over.players["p1"].private.action_cards = [card] * (limit + 1)
    takes(hand_limit.discard_excess(over, "p1", card))


@ruling(f"{_CARDS}/reverse-engineer/2")
def test_reverse_engineer_taken_card_is_public_in_the_activity_feed(
    registry: StaticDataRegistry,
) -> None:
    from src.core.activity import derive_activity

    card = misc_h._ACTION_CARD
    state = misc_h._state({"p1": [card], "p2": ["reverse_engineer", "sabotage"]})
    state.decks.action_card_deck = ["filler"]
    played, _ = action_cards.play_action_card(state, registry, "p1", card)
    taken = misc_h._play(played, registry, "p2", "reverse_engineer")
    entry = derive_activity("action-card:play:reverse_engineer", played, taken)
    assert entry is not None
    facts = [(f.type, f.player_id, f.value) for f in entry.facts if "action_card" in f.type]
    assert ("action_card_taken", "p2", card) in facts
    assert "sabotage" not in entry.model_dump_json()  # the rest of the hand stays hidden


# ============================================================================ Rise of a Messiah


@ruling(f"{_CARDS}/rise-of-a-messiah/1")
def test_messiah_without_planets(registry: StaticDataRegistry) -> None:
    state = eco._state(["messiah"])
    assert _playable(state, registry, "messiah")
    new = eco._play(state, registry, "messiah")
    assert new.players["p1"].private.action_cards == []


# ============================================================================= Unstable Planet


@ruling(f"{_CARDS}/unstable-planet/1", f"{_CARDS}/unstable-planet/2",
        f"{_CARDS}/unstable-planet/3")
def test_unstable_planet_new_text_few_infantry_and_exhausted_planet(
    registry: StaticDataRegistry,
) -> None:
    for infantry in (0, 2):
        state = eco._unstable_state(infantry)
        state.players["p2"].exhausted_planets = ["abyz"]
        assert _playable(state, registry, "unstable")
        new = eco._play(state, registry, "unstable", {"planet": "abyz", "count": infantry})
        assert new.players["p2"].exhausted_planets == ["abyz"]
        left = new.systems["101"].planet_units.get("abyz", {}).get("p2", {})
        assert left.get("infantry", 0) == 0


# ==================================================================================== Upgrade


@ruling(f"{_CARDS}/upgrade/1")
def test_upgrade_needs_a_cruiser_in_the_active_system(registry: StaticDataRegistry) -> None:
    state = tactical_h._state({"p1": ["upgrade"]})
    assert not tactical_h._playable(state, registry, "p1", "upgrade")
    state.systems[tactical_h.ACTIVE].space_units = {"p1": {"cruiser": 1}}
    assert tactical_h._playable(state, registry, "p1", "upgrade")


@ruling(f"{_CARDS}/upgrade/2")
def test_upgrade_not_for_a_cruiser_that_moved_in_later(registry: StaticDataRegistry) -> None:
    grid = tactical_h._grid(("101", "18", set(), []), ("102", "20", set(), []))
    state = tactical_h._state({"p1": ["upgrade"]})
    state.systems["102"] = SystemState(
        position="102", system_id="20", space_units={"p1": {"cruiser": 1}}
    )
    moved = movement.move_ships(state, grid, registry, "102", "cruiser", 1, "p1")
    assert moved.systems[tactical_h.ACTIVE].space_units["p1"] == {"cruiser": 1}
    assert not tactical_h._playable(moved, registry, "p1", "upgrade")


@ruling(f"{_CARDS}/upgrade/3")
def test_upgrade_places_a_board_dreadnought_undamaged(registry: StaticDataRegistry) -> None:
    state = tactical_h._state({"p1": ["upgrade"]})
    state.systems[tactical_h.ACTIVE].space_units = {"p1": {"cruiser": 1}}
    state.systems["102"] = SystemState(
        position="102", system_id="20", space_units={"p1": {"dreadnought": 5}},
        damaged_units={"space": {"p1": {"dreadnought": 5}}},
    )
    new = tactical_h._play(state, registry, "p1", "upgrade", {"source": "102"})
    assert new.systems["102"].space_units["p1"] == {"dreadnought": 4}
    assert new.systems[tactical_h.ACTIVE].space_units["p1"] == {"dreadnought": 1}
    assert not new.systems[tactical_h.ACTIVE].damaged_units


# ===================================================================================== Uprising


@ruling(f"{_CARDS}/uprising/1", f"{_CARDS}/uprising/2")
def test_uprising_ignores_exhausted_planets(registry: StaticDataRegistry) -> None:
    state = eco._state(["uprising"], theirs=("abyz",))
    state.players["p2"].exhausted_planets = ["abyz"]
    assert not _playable(state, registry, "uprising")
    with pytest.raises(ValueError, match="ready"):
        action_cards.play_action_card(state, registry, "p1", "uprising", {"planet": "abyz"})


@ruling(f"{_CARDS}/uprising/3")
def test_uprising_cannot_target_neutral_infantry(registry: StaticDataRegistry) -> None:
    state = eco._state(["uprising"])
    state.systems["101"].planet_units = {"abyz": {NEUTRAL_PLAYER_ID: {"infantry": 2}}}
    assert not _playable(state, registry, "uprising")
