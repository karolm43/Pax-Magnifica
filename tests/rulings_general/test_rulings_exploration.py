"""Eksploracja, fragmenty reliktów, żetony frontier, attach i purge — rulingi
``C_exploration_cards.md``, ``R_exploration.md``, ``R_relics.md``, ``R_frontier_tokens.md``,
``R_attach.md`` i ``R_purge.md`` punkt po punkcie.

Część punktów sprawdzają istniejące testy (``tests/test_exploration.py``, ``test_relic_forge.py``,
``test_frontier_cards.py`` …) oznaczone ``@ruling``; tu są brakujące. Statusy bez testu:
``tests/rulings_status.json``.
"""

from __future__ import annotations

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    control,
    economy,
    exploration,
    game_setup,
    ion_storm,
    production,
    relic_forge,
    relics,
    retreat,
    rules_hooks,
    transaction,
    visibility,
)
from src.core.game_state import (
    ExplorationState,
    ExploreCurrent,
    GameState,
    SystemState,
)
from src.core.hex_grid import Hex, HexGrid
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide
from tests.rulings import ruling
from tests.test_exploration import _CULT, _IND, _card_id, _state, _with_card
from tests.test_exploration import registry as registry  # noqa: F401 - fixture modułu


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


# ============================================================================ commodities


@ruling(
    "C_exploration_cards/functioning-base/1", "C_exploration_cards/local-fabricators/1"
)
@pytest.mark.parametrize("name", ["Functioning Base", "Local Fabricators"])
def test_gain_commodity_is_blocked_at_the_commodity_value(
    registry: StaticDataRegistry, name: str
) -> None:
    state = _with_card(_state(), registry, name, _IND)
    player = state.players["p1"]
    player.commodity_value, player.commodities = 2, 2
    options = {o.id: o for o in exploration.options_for(state, registry)}
    assert not options["gain"].enabled
    player.commodities = 1
    done = exploration.resolve(state, registry, "gain")
    assert done.players["p1"].commodities == 2


# ============================================================================ fragmenty


@ruling(
    "C_exploration_cards/cultural-relic-fragment/1",
    "C_exploration_cards/hazardous-relic-fragment/1",
    "C_exploration_cards/industrial-relic-fragment/1",
)
@pytest.mark.parametrize("prefix", ["crf", "hrf", "irf"])
def test_each_fragment_type_purges_with_an_empty_relic_deck(
    registry: StaticDataRegistry, prefix: str
) -> None:
    from tests.test_relic_forge import _with_fragments

    fragments = [f"{prefix}{n}" for n in (1, 2, 3)]
    state = _with_fragments(registry, fragments)
    relics.ensure_relic_deck(state, registry)
    state.decks.relic_deck, state.decks.relic_discard = [], []
    done = relic_forge.forge(state, registry, "p1", fragments)
    assert done.players["p1"].relic_fragments == [] and done.players["p1"].relics == []
    assert set(fragments) <= set(done.decks.purged)


@ruling("R_relics/rules-reference/2.1")
def test_dead_world_with_an_empty_relic_deck_has_no_effect(registry: StaticDataRegistry) -> None:
    from tests.test_frontier_cards import _state as frontier_state

    state = frontier_state(registry, "dw")
    relics.ensure_relic_deck(state, registry)
    state.decks.relic_deck, state.decks.relic_discard = [], []
    done = exploration.resolve(state, registry, "draw")
    assert done.players["p1"].relics == []
    assert "dw" in done.decks.exploration_discard["frontier"]


@ruling("R_exploration/rules-reference/9.2", "R_relics/rules-reference/1.1")
def test_relic_fragments_change_hands_in_a_transaction(registry: StaticDataRegistry) -> None:
    from tests.test_relics import _state as relic_state

    state = relic_state(registry, [])
    state.players["p1"].relic_fragments = ["crf1"]
    grid = build_demo_grid(registry)
    done = transaction.resolve_transaction(
        state, grid, "p2", TransactionSide(relic_fragments=("crf1",)), TransactionSide()
    )
    assert done.players["p2"].relic_fragments == ["crf1"]
    assert done.players["p1"].relic_fragments == []


@ruling("R_relics/rules-reference/4")
def test_relics_cannot_be_traded(registry: StaticDataRegistry) -> None:
    from tests.test_relics import _state as relic_state

    state = relic_state(registry, ["codex"])
    grid = build_demo_grid(registry)
    with pytest.raises(ValueError, match="Black Market Dealings"):
        transaction.resolve_transaction(
            state, grid, "p2", TransactionSide(relics=("codex",)), TransactionSide()
        )


# ============================================================================ karty planet


def test_dmz_ground_forces_without_capacity_open_the_capacity_check(
    registry: StaticDataRegistry,
) -> None:
    state = _with_card(_state(planets={_CULT: {"infantry": 2}}), registry, "Demilitarized Zone")
    done = exploration.resolve(state, registry, "attach")
    # Zero pojemności = jedyne legalne usunięcie: piechota wraca do rezerwy od razu (39.6 C5).
    assert "p1" not in done.systems["000"].space_units
    assert done.pending_window is None


@ruling("C_exploration_cards/freelancers/1")
def test_freelancers_cannot_place_on_a_planet_still_waiting_for_exploration(
    registry: StaticDataRegistry,
) -> None:
    state = _with_card(_state(planets={_CULT: {"infantry": 1}}), registry, "Freelancers")
    system = state.systems["000"]
    system.planet_owners = {_CULT: "p1", _IND: "p1"}
    state.players["p1"].controlled_planets = [_CULT, _IND]
    assert state.exploration is not None
    state.exploration.queue = [_IND]  # druga planeta jeszcze niezdobyta (eksploracja po kolei)
    opened = exploration.resolve(state, registry, "produce")
    zones = production.allowed_ground_zones(opened, registry, "p1", "000")
    assert _CULT in zones and _IND not in zones


@ruling("C_exploration_cards/freelancers/2", "C_exploration_cards/local-fabricators/2")
def test_empty_reinforcements_take_a_unit_from_the_board_undamaged(
    registry: StaticDataRegistry,
) -> None:
    from src.core import damage

    state = _with_card(_state(), registry, "Local Fabricators", _IND)
    state.players["p1"].commodities = 1
    far = SystemState(position="101", system_id="19")
    far.space_units = {}
    far.planet_units = {"wellon": {"p1": {"mech": 4}}}
    state.systems["101"] = far
    damage.set_damaged(far, "wellon", "p1", "mech", 4)
    options = {o.id: o for o in exploration.options_for(state, registry)}
    sources = [value for value, _label in options["mech_commodity"].params]
    assert sources == ["101|wellon"]
    done = exploration.resolve(state, registry, "mech_commodity", sources[0])
    assert done.systems["000"].planet_units[_IND]["p1"]["mech"] == 1
    assert damage.damaged_count(done.systems["000"], _IND, "p1", "mech") == 0  # nieuszkodzony
    assert done.systems["101"].planet_units["wellon"]["p1"]["mech"] == 3
    # Z systemu z własnym żetonem dowodzenia zdjąć nie wolno.
    state.systems["101"].command_tokens = ["p1"]
    options = {o.id: o for o in exploration.options_for(state, registry)}
    assert not options["mech_commodity"].enabled


# ============================================================================ frontier


@ruling("C_exploration_cards/derelict-vessel/1")
def test_derelict_vessel_with_three_scored_secrets_draws_and_shuffles_back(
    registry: StaticDataRegistry,
) -> None:
    from src.core import secret_objectives
    from tests.test_frontier_cards import _state as frontier_state

    state = frontier_state(registry, "dv1")
    state.decks.secret_objective_deck = ["a", "b"]
    state.players["p1"].scored_secrets = ["s1", "s2", "s3"]
    assert secret_objectives.secret_count(state, "p1") == 3
    option = exploration.options_for(state, registry)[0]
    assert option.enabled
    assert secret_objectives.DRAWN in {value for value, _label in option.params}
    done = exploration.resolve(state, registry, "draw", secret_objectives.DRAWN)
    assert done.players["p1"].private.secret_objectives == []
    assert sorted(done.decks.secret_objective_deck) == ["a", "b"]


# ============================================================================ Ion Storm


def _storm_grid(
    registry: StaticDataRegistry, native: bool = False
) -> tuple[GameState, HexGrid]:
    """System "a" z Ion Storm (strona ALPHA) i niesąsiadujący "b" z wormholem alpha.

    ``native=True``: kafelek "a" ma też WŁASNY wormhole alpha (wybór wormholu, ruling 3)."""
    alpha = [s.id for s in registry.systems.values() if "ALPHA" in [w.upper() for w in s.wormholes]]
    storm_tile = alpha[0] if native else "19"  # Wellon: bez wormholi
    grid = HexGrid()
    grid.place_system("a", alpha[0], wormholes=["ALPHA"], hex_override=Hex(0, 0, 0))
    grid.place_system("b", alpha[1], wormholes=["ALPHA"], hex_override=Hex(3, -3, 0))
    grid.build_edges()
    state = _state()
    state.systems = {
        "a": SystemState(position="a", system_id=storm_tile, ion_storm="ALPHA"),
        "b": SystemState(position="b", system_id=alpha[1], space_units={"p1": {"cruiser": 2}}),
    }
    return state, grid


@ruling("C_exploration_cards/ion-storm/2")
def test_ion_storm_flips_once_after_the_whole_move(registry: StaticDataRegistry) -> None:
    state, grid = _storm_grid(registry)
    ion_storm.note_move(state, grid, registry, "b", "a")
    ion_storm.note_move(state, grid, registry, "b", "a")  # dwa statki - ruch jednoczesny
    assert state.systems["a"].ion_storm == "ALPHA"  # w trakcie kroku żeton się nie obraca
    assert ion_storm.flip_used(state) == ["a"]
    assert state.systems["a"].ion_storm == "BETA"


@ruling("C_exploration_cards/ion-storm/3")
def test_player_chooses_ion_storm_or_the_systems_own_wormhole(
    registry: StaticDataRegistry,
) -> None:
    state, grid = _storm_grid(registry)
    assert ion_storm.choice_needed(state, grid, registry, "b", "a") is None  # tylko żeton
    state, grid = _storm_grid(registry, native=True)
    assert ion_storm.choice_needed(state, grid, registry, "b", "a") == "a"
    with pytest.raises(ValueError, match="choose which wormhole"):
        ion_storm.note_move(state, grid, registry, "b", "a")  # silnik nie wybiera za gracza
    ion_storm.note_move(state, grid, registry, "b", "a", use_token=False)
    assert ion_storm.flip_used(state) == [] and state.systems["a"].ion_storm == "ALPHA"
    ion_storm.note_move(state, grid, registry, "b", "a", use_token=True)
    assert ion_storm.flip_used(state) == ["a"] and state.systems["a"].ion_storm == "BETA"


def test_a_system_is_never_adjacent_to_itself(registry: StaticDataRegistry) -> None:
    state, grid = _storm_grid(registry)
    assert not grid.are_adjacent("a", "a")
    assert ion_storm.uses_ion_storm(state, grid, registry, "a", "a") is None


@ruling("C_exploration_cards/ion-storm/4")
def test_moving_outside_move_or_retreat_does_not_flip_the_storm(
    registry: StaticDataRegistry,
) -> None:
    """Skilled Retreat przenosi statki ``retreat_in_place`` - bez notowania Ion Storm."""
    state, grid = _storm_grid(registry)
    state.systems["a"].space_units = {"p1": {"cruiser": 1}}
    state.systems["b"].space_units = {}
    retreat.retreat_in_place(
        state, grid, registry, "a", "p1", "b", destinations=["b"], token_pools=False
    )
    assert state.ion_storm_used == [] and state.systems["a"].ion_storm == "ALPHA"


# ============================================================================ R_exploration


@ruling("R_exploration/rules-reference/3")
def test_a_planet_can_be_explored_again_by_an_ability(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["000"].planet_owners[_CULT] = "p1"
    state.players["p1"].controlled_planets = [_CULT]
    first = exploration.begin_exploration(state, registry, "p1", "000", [_CULT])
    option = next(o for o in exploration.options_for(first, registry) if o.enabled)
    first = exploration.finish(exploration.resolve(first, registry, option.id, None))
    again = exploration.begin_exploration(first, registry, "p1", "000", [_CULT])
    assert again.exploration is not None and again.exploration.current is not None


@ruling("R_exploration/notes/3")
def test_transactions_are_allowed_while_a_card_is_revealed(registry: StaticDataRegistry) -> None:
    from tests.test_relics import _state as relic_state

    state = relic_state(registry, [])
    state.exploration = ExplorationState(
        player_id="p1", position="102",
        current=ExploreCurrent(planet="industrex", deck="industrial", card_id="ds"),
    )
    state.players["p1"].trade_goods = 2
    done = transaction.resolve_transaction(
        state, build_demo_grid(registry), "p2", TransactionSide(trade_goods=1), TransactionSide()
    )
    assert done.players["p2"].trade_goods == 1 and done.exploration is not None


@ruling("R_exploration/notes/2")
def test_revealed_exploration_card_is_public(registry: StaticDataRegistry) -> None:
    state = _with_card(_state(), registry, "Dyson Sphere")
    seen = visibility.project_strict(state, "p2")
    assert seen.exploration is not None and seen.exploration.current is not None
    assert seen.exploration.current.card_id == _card_id(registry, "Dyson Sphere")


# ============================================================================ R_frontier_tokens


@ruling("R_frontier_tokens/rules-reference/1.2", "R_frontier_tokens/rules-reference/1.3")
def test_frontier_tokens_in_planetless_anomalies_and_at_most_one(
    registry: StaticDataRegistry,
) -> None:
    anomaly = next(
        s.id for s in sorted(registry.systems.values(), key=lambda s: s.id)
        if not s.planets and s.anomalies
    )
    grid = HexGrid()
    grid.place_system("101", anomaly, anomalies=set(registry.systems[anomaly].anomalies))
    grid.build_edges()
    state = game_setup.place_frontier_tokens(_state(), grid, registry)
    assert state.systems["101"].frontier_token is True
    again = game_setup.place_frontier_tokens(state, grid, registry)
    assert again.systems["101"].frontier_token is True  # bool - nie da się położyć drugiego


# ============================================================================ R_attach


@ruling("R_attach/rules-reference/2")
def test_attachment_stays_with_the_planet_when_control_changes(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.systems["000"].planet_owners[_CULT] = "p1"
    state.players["p1"].controlled_planets = [_CULT]
    exploration.attach_to_planet(state, _CULT, "ds")
    control.set_planet_control(state, "000", _CULT, "p2", registry)
    assert state.planet_attachments[_CULT] == ["ds"]
    assert state.systems["000"].planet_owners[_CULT] == "p2"


@ruling("R_attach/rules-reference/2.2")
def test_purged_planet_purges_its_attachments(registry: StaticDataRegistry) -> None:
    state = _state()
    state.planet_attachments = {_CULT: ["ds", "mw"]}
    assert exploration.purge_planet_attachments(state, _CULT) == ["ds", "mw"]
    assert _CULT not in state.planet_attachments
    assert {"ds", "mw"} <= set(state.decks.purged)


@ruling("R_attach/notes/1")
def test_a_planet_has_no_attachment_limit(registry: StaticDataRegistry) -> None:
    state = _state()
    for card in ("ds", "mw", "rw", "lc"):
        exploration.attach_to_planet(state, _CULT, card)
    assert state.planet_attachments[_CULT] == ["ds", "mw", "rw", "lc"]


@ruling("R_attach/notes/2")
def test_custodians_token_is_not_an_attachment(registry: StaticDataRegistry) -> None:
    """Żeton Custodians to flaga gry (``custodians_removed``), nie karta przy planecie Mecatol."""
    from src.core import custodians

    state = _state()
    state.systems["000"] = SystemState(position="000", system_id="18")
    assert custodians.on_board(state) and custodians.is_mecatol_position(state, "000")
    assert state.planet_attachments == {}


# ============================================================================ R_purge


@ruling("R_purge/rules-reference/3")
def test_component_is_purged_even_if_partially_resolved(registry: StaticDataRegistry) -> None:
    """The Codex purge'uje się także, gdy gracz nie bierze żadnej karty (zero z „up to 3”)."""
    from tests.test_relics import _state as relic_state

    state = relic_state(registry, ["codex"])
    state.decks.action_card_deck = ["x"]
    from src.core.hooks import relics_actions

    relics_actions.codex(state, registry, "p1", {"cards": []})
    assert "codex" in state.decks.purged
    assert economy is not None
