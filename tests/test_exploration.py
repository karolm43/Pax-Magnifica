"""Testy eksploracji planet po Establish Control (RULES.md 46)."""

from __future__ import annotations

import pytest

from src.core import exploration, invasion, production, tactical
from src.core.components import ComponentCategory, ExplorationDef
from src.core.game_state import (
    ExplorationState,
    ExploreCurrent,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.planet_stats import PlanetStats, effective_planets, planet_stats
from src.core.registry import StaticDataRegistry

# Kafelek 107: tiamat (cultural) i hercalor (industrial). Planeta dwucechowa: lazulrex.
_TILE = "107"
_CULT = "tiamat"
_IND = "hercalor"
_DUAL = "lazulrex"
_PLAIN = "abaddon"  # planeta z cechą, bez specjalności technologicznej


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", _TILE, anomalies=set())
    grid.build_edges()
    return grid


def _state(
    space: dict[str, int] | None = None,
    planets: dict[str, dict[str, int]] | None = None,
    *,
    seed: int = 7,
) -> GameState:
    """Aktywny p1 w INVASION; ``planets`` = jednostki p1 na planetach."""
    system = SystemState(position="000", system_id=_TILE)
    if space:
        system.space_units["p1"] = dict(space)
    for planet, units in (planets or {}).items():
        system.planet_units[planet] = {"p1": dict(units)}
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=TacticalStep.INVASION,
        seating_order=["p1", "p2"],
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2")},
        systems={"000": system},
        rng_seed=seed,
    )


def _cards(registry: StaticDataRegistry) -> dict[str, ExplorationDef]:
    cards = registry.catalog.all(ComponentCategory.EXPLORATION)
    return {cid: c for cid, c in cards.items() if isinstance(c, ExplorationDef)}


def _card_id(registry: StaticDataRegistry, name: str) -> str:
    return next(cid for cid, c in _cards(registry).items() if c.name == name)


def _with_card(
    state: GameState, registry: StaticDataRegistry, name: str, planet: str = _CULT
) -> GameState:
    """Stan z ujawnioną kartą ``name`` (kolejka pusta) — do testów pojedynczych skutków."""
    deck = next(
        (c.type or "").lower() for c in _cards(registry).values() if c.name == name
    )
    new_state = state.clone()
    new_state.exploration = ExplorationState(
        player_id="p1",
        position="000",
        current=ExploreCurrent(planet=planet, deck=deck, card_id=_card_id(registry, name)),
    )
    return new_state


# ----------------------------------------------------------------------------- cechy planet


def test_planet_traits_and_explorable(registry: StaticDataRegistry) -> None:
    assert exploration.planet_traits(registry, _CULT) == ["cultural"]
    assert exploration.planet_traits(registry, _DUAL) == ["industrial", "cultural"]
    # Mecatol Rex i planety domowe nie mają cech → nie podlegają eksploracji.
    assert not exploration.explorable(registry, "mr")
    assert not exploration.explorable(registry, "maaluuk")


# ------------------------------------------------------------------------------- przepływ


def test_single_planet_draws_card_automatically(registry: StaticDataRegistry) -> None:
    state = exploration.begin_exploration(_state(), registry, "p1", "000", [_CULT])
    ex = state.exploration
    assert ex is not None
    assert ex.queue == [] and ex.current is not None
    assert ex.current.planet == _CULT and ex.current.deck == "cultural"
    card = exploration.card_def(registry, ex.current.card_id)
    assert card.type == "Cultural"
    # Talia jest zasiana leniwie i ubyła jej jedna karta.
    assert len(state.decks.exploration_deck["cultural"]) == 19


def test_planets_without_traits_are_not_explored(registry: StaticDataRegistry) -> None:
    state = exploration.begin_exploration(_state(), registry, "p1", "000", ["mr", "maaluuk"])
    assert state.exploration is None


def test_multiple_planets_player_chooses_order(registry: StaticDataRegistry) -> None:
    state = exploration.begin_exploration(_state(), registry, "p1", "000", [_CULT, _IND])
    ex = state.exploration
    assert ex is not None and ex.current is None
    assert ex.queue == [_CULT, _IND]
    with pytest.raises(ValueError, match="not waiting"):
        exploration.draw(state, registry, "mr")

    state = exploration.draw(state, registry, _IND)  # gracz zaczyna od drugiej planety
    assert state.exploration is not None
    assert state.exploration.current is not None
    assert state.exploration.current.planet == _IND
    with pytest.raises(ValueError, match="Resolve the revealed"):
        exploration.draw(state, registry, _CULT)

    # Po rozstrzygnięciu ostatnia planeta w kolejce ujawnia kartę sama.
    option = next(o for o in exploration.options_for(state, registry) if o.enabled)
    state = exploration.resolve(state, registry, option.id, _first_param(option))
    ex = state.exploration
    assert ex is not None and ex.current is not None
    assert ex.current.planet == _CULT and ex.queue == []


def test_multi_trait_planet_needs_deck_choice(registry: StaticDataRegistry) -> None:
    state = exploration.begin_exploration(_state(), registry, "p1", "000", [_DUAL])
    ex = state.exploration
    assert ex is not None and ex.current is None  # brak automatu — trzeba wybrać talię
    with pytest.raises(ValueError, match="Choose which"):
        exploration.draw(state, registry, _DUAL)
    with pytest.raises(ValueError, match="no hazardous"):
        exploration.draw(state, registry, _DUAL, "hazardous")
    drawn = exploration.draw(state, registry, _DUAL, "cultural")
    assert drawn.exploration is not None and drawn.exploration.current is not None
    assert drawn.exploration.current.deck == "cultural"


def test_finish_requires_everything_resolved(registry: StaticDataRegistry) -> None:
    state = exploration.begin_exploration(_state(), registry, "p1", "000", [_CULT])
    with pytest.raises(ValueError, match="Finish exploring"):
        exploration.finish(state)
    option = next(o for o in exploration.options_for(state, registry) if o.enabled)
    state = exploration.resolve(state, registry, option.id, _first_param(option))
    assert exploration.finish(state).exploration is None


def _first_param(option: exploration.ExploreOption) -> str | None:
    return option.params[0][0] if option.params else None


def test_every_planet_card_can_be_resolved(registry: StaticDataRegistry) -> None:
    """Każda karta talii planetarnej ma co najmniej jedną dostępną opcję i da się ją zamknąć."""
    for card_id, card in _cards(registry).items():
        if (card.type or "").lower() not in exploration.PLANET_DECKS:
            continue
        state = _state(planets={_CULT: {"mech": 1, "infantry": 1}})
        state.players["p1"].commodity_value = 3
        state.players["p1"].trade_goods = 1
        state.players["p1"].cc_reinf = 2
        state.players["p1"].exhausted_planets = [_CULT]
        state.exploration = ExplorationState(
            player_id="p1",
            position="000",
            current=ExploreCurrent(
                planet=_CULT, deck=(card.type or "").lower(), card_id=card_id
            ),
        )
        option = next(o for o in exploration.options_for(state, registry) if o.enabled)
        done = exploration.resolve(state, registry, option.id, _first_param(option))
        assert done.exploration is not None and done.exploration.current is None, card.name


# --------------------------------------------------------------------- odkładanie kart


def test_instant_card_goes_to_discard_and_fragment_to_player(
    registry: StaticDataRegistry,
) -> None:
    state = _with_card(_state(planets={_CULT: {"infantry": 1}}), registry, "Mercenary Outfit")
    done = exploration.resolve(state, registry, "place_infantry")
    assert done.exploration is not None
    assert done.exploration.log[-1]["fate"] == "discarded"
    assert done.decks.exploration_discard["cultural"] == [_card_id(registry, "Mercenary Outfit")]
    assert done.systems["000"].planet_units[_CULT]["p1"]["infantry"] == 2

    frag = _with_card(_state(), registry, "Cultural Relic Fragment")
    kept = exploration.resolve(frag, registry, "keep")
    assert kept.players["p1"].relic_fragments == [_card_id(registry, "Cultural Relic Fragment")]
    assert kept.decks.exploration_discard.get("cultural", []) == []


def test_attach_stays_with_planet(registry: StaticDataRegistry) -> None:
    state = _with_card(_state(), registry, "Dyson Sphere")
    done = exploration.resolve(state, registry, "attach")
    assert done.planet_attachments == {_CULT: [_card_id(registry, "Dyson Sphere")]}
    assert done.decks.exploration_discard.get("cultural", []) == []


def test_demilitarized_zone_clears_the_planet(registry: StaticDataRegistry) -> None:
    state = _with_card(
        _state(planets={_CULT: {"infantry": 2, "pds": 1}}), registry, "Demilitarized Zone"
    )
    done = exploration.resolve(state, registry, "attach")
    system = done.systems["000"]
    assert system.planet_units.get(_CULT, {}) == {}
    assert system.space_units["p1"] == {"infantry": 2}


def test_token_card_is_purged(registry: StaticDataRegistry) -> None:
    state = _with_card(_state(), registry, "Gamma Wormhole")
    done = exploration.resolve(state, registry, "place")
    assert done.decks.exploration_discard.get("cultural", []) == []
    assert done.exploration is not None and done.exploration.log[-1]["fate"] == "purged"
    assert done.systems["000"].wormhole_tokens == ["GAMMA"]


def test_gamma_token_links_systems_through_the_grid() -> None:
    grid = HexGrid()
    grid.place_system("000", _TILE, anomalies=set())
    grid.place_system("301", "27", anomalies=set())  # daleko od 000 — brak sąsiedztwa
    grid.build_edges()
    assert not grid.are_adjacent("000", "301")
    grid.sync_token_wormholes({"000": ["GAMMA"], "301": ["GAMMA"]})
    assert grid.are_adjacent("000", "301")
    grid.sync_token_wormholes({})  # np. po Undo — żetony znikają, mapa wraca
    assert not grid.are_adjacent("000", "301")


# ---------------------------------------------------------- statystyki z attachmentów


def test_attachments_change_planet_stats(registry: StaticDataRegistry) -> None:
    base = registry.planets[_PLAIN]
    state = _state()
    assert planet_stats(state, registry, _PLAIN) == PlanetStats(
        base.resources, base.influence, ()
    )
    state.planet_attachments = {_PLAIN: [_card_id(registry, "Dyson Sphere")]}
    stats = planet_stats(state, registry, _PLAIN)
    assert stats is not None
    assert (stats.resources, stats.influence) == (base.resources + 2, base.influence + 1)
    # Wspólny widok „efektywnych planet" dla kodu liczącego po rejestrze.
    assert effective_planets(state, registry).planets[_PLAIN].resources == stats.resources


def test_research_facility_gives_specialty_then_bonus_instead(
    registry: StaticDataRegistry,
) -> None:
    base = registry.planets[_PLAIN]
    state = _state()
    biotic, cyber = _card_id(registry, "Biotic Research Facility"), _card_id(
        registry, "Cybernetic Research Facility"
    )
    state.planet_attachments = {_PLAIN: [biotic]}
    first = planet_stats(state, registry, _PLAIN)
    assert first is not None and first.tech_specialties == ("biotic",)
    assert (first.resources, first.influence) == (base.resources, base.influence)
    # Druga fabryka: planeta ma już specjalność → +1/+1 ZAMIAST kolejnej.
    state.planet_attachments = {_PLAIN: [biotic, cyber]}
    second = planet_stats(state, registry, _PLAIN)
    assert second is not None and second.tech_specialties == ("biotic",)
    assert (second.resources, second.influence) == (base.resources + 1, base.influence + 1)


def test_attachments_feed_production_budget(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["000"].planet_owners[_CULT] = "p1"
    before = production.available_budget(state, registry, "p1")
    state.planet_attachments = {_CULT: [_card_id(registry, "Mining World")]}  # +2 zasoby
    assert production.available_budget(state, registry, "p1") == before + 2


# ------------------------------------------------------------------------- Freelancers


def test_freelancers_opens_one_unit_production_paid_with_influence(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = _with_card(
        _state(planets={_CULT: {"infantry": 1}}), registry, "Freelancers"
    )
    state.systems["000"].planet_owners[_CULT] = "p1"
    state.players["p1"].controlled_planets = [_CULT]
    planet = registry.planets[_CULT]
    opened = exploration.resolve(state, registry, "produce")
    grant = opened.production_grant
    assert grant is not None and grant.units == 1 and grant.influence_as_resources
    # Okno eksploracji czeka na produkcję.
    with pytest.raises(ValueError, match="production first"):
        exploration.finish(opened)

    # Wpływ liczy się jak zasoby: planeta płaci max(zasoby, wpływ); limit = 1 sztuka.
    assert production.pay_value(opened, registry, _CULT, "p1") == max(
        planet.resources, planet.influence
    )
    with pytest.raises(ValueError, match="limit exceeded"):
        production.produce(
            opened, grid, registry, "p1",
            [production.ProductionOrder("infantry", 3, _CULT)],
        )
    opened.players["p1"].trade_goods = 5
    done = production.produce(
        opened, grid, registry, "p1",
        [production.ProductionOrder("infantry", 1, _CULT)],
        production.Spend(planets=(), trade_goods=1),
    )
    assert done.production_grant is None
    assert done.production_used == 0  # nie zużywa limitu kroku PRODUCTION
    assert done.systems["000"].planet_units[_CULT]["p1"]["infantry"] == 2
    # Po produkcji eksplorację można zamknąć.
    assert exploration.finish(done).exploration is None


def test_freelancers_can_be_skipped(registry: StaticDataRegistry) -> None:
    state = _with_card(_state(), registry, "Freelancers")
    opened = exploration.resolve(state, registry, "produce")
    assert production.skip_grant(opened).production_grant is None
    with pytest.raises(ValueError, match="no card-granted"):
        production.skip_grant(_state())


# ---------------------------------------------------------------------- skutki kart


def test_core_mine_needs_mech_or_infantry(registry: StaticDataRegistry) -> None:
    bare = _with_card(_state(planets={_CULT: {"mech": 1}}), registry, "Core Mine")
    options = {o.id: o for o in exploration.options_for(bare, registry)}
    assert options["mech"].enabled and not options["infantry"].enabled
    with pytest.raises(ValueError, match="No infantry"):
        exploration.resolve(bare, registry, "infantry")
    assert exploration.resolve(bare, registry, "mech").players["p1"].trade_goods == 1

    grunts = _with_card(_state(planets={_CULT: {"infantry": 2}}), registry, "Core Mine")
    paid = exploration.resolve(grunts, registry, "infantry")
    assert paid.players["p1"].trade_goods == 1
    assert paid.systems["000"].planet_units[_CULT]["p1"]["infantry"] == 1


def test_volatile_fuel_source_gives_command_token_to_chosen_pool(
    registry: StaticDataRegistry,
) -> None:
    state = _with_card(_state(planets={_CULT: {"mech": 1}}), registry, "Volatile Fuel Source")
    state.players["p1"].cc_reinf = 2
    with pytest.raises(ValueError, match="Choose a value"):
        exploration.resolve(state, registry, "mech")
    done = exploration.resolve(state, registry, "mech", "fleet")
    player = done.players["p1"]
    assert (player.fleet_cc, player.cc_reinf) == (4, 1)

    empty = state.clone()
    empty.players["p1"].cc_reinf = 0
    with pytest.raises(ValueError, match="reinforcements"):
        exploration.resolve(empty, registry, "mech", "fleet")


def test_expedition_readies_the_planet(registry: StaticDataRegistry) -> None:
    state = _with_card(_state(planets={_CULT: {"mech": 1}}), registry, "Expedition")
    state.players["p1"].exhausted_planets = [_CULT]
    done = exploration.resolve(state, registry, "mech")
    assert done.players["p1"].exhausted_planets == []


def test_commodities_are_capped_by_commodity_value(registry: StaticDataRegistry) -> None:
    state = _with_card(_state(), registry, "Abandoned Warehouses", _IND)
    player = state.players["p1"]
    player.commodity_value, player.commodities = 3, 2
    gained = exploration.resolve(state, registry, "gain")
    assert gained.players["p1"].commodities == 3

    player.commodities = 3
    options = {o.id: o for o in exploration.options_for(state, registry)}
    assert not options["gain"].enabled
    converted = exploration.resolve(state, registry, "convert", "2")
    assert (converted.players["p1"].commodities, converted.players["p1"].trade_goods) == (1, 2)


def test_functioning_base_spends_to_draw_action_card(registry: StaticDataRegistry) -> None:
    state = _with_card(_state(), registry, "Functioning Base", _IND)
    state.decks.action_card_deck = ["ac1", "ac2"]
    state.players["p1"].trade_goods = 1
    with pytest.raises(ValueError, match="no commodities"):
        exploration.resolve(state, registry, "draw_commodity")
    done = exploration.resolve(state, registry, "draw_tg")
    assert done.players["p1"].private.action_cards == ["ac1"]
    assert done.players["p1"].trade_goods == 0


def test_local_fabricators_places_mech(registry: StaticDataRegistry) -> None:
    state = _with_card(_state(), registry, "Local Fabricators", _IND)
    state.players["p1"].commodities = 1
    done = exploration.resolve(state, registry, "mech_commodity")
    assert done.systems["000"].planet_units[_IND]["p1"]["mech"] == 1
    assert done.players["p1"].commodities == 0


# -------------------------------------------------------------------------------- talie


def test_empty_deck_is_reshuffled_from_discard(registry: StaticDataRegistry) -> None:
    state = _state()
    state.decks.exploration_deck["cultural"] = []
    state.decks.exploration_discard["cultural"] = ["frln1", "frln2"]
    drawn = exploration.begin_exploration(state, registry, "p1", "000", [_CULT])
    assert drawn.exploration is not None and drawn.exploration.current is not None
    assert drawn.exploration.current.card_id in {"frln1", "frln2"}
    assert len(drawn.decks.exploration_deck["cultural"]) == 1
    assert drawn.decks.exploration_discard["cultural"] == []


def test_deck_is_seedable(registry: StaticDataRegistry) -> None:
    def first(seed: int) -> str:
        state = exploration.begin_exploration(_state(seed=seed), registry, "p1", "000", [_CULT])
        assert state.exploration is not None and state.exploration.current is not None
        return state.exploration.current.card_id

    assert first(3) == first(3)


# ------------------------------------------------------------------ podpięcie do inwazji


def test_capturing_unowned_planets_opens_exploration(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = invasion.begin_invasion(_state({"infantry": 2}), grid, registry)
    state = invasion.commit_ground_forces(
        state, registry, {_CULT: {"infantry": 1}, _IND: {"infantry": 1}}
    )
    state = invasion.advance(state, grid, registry)  # → Establish Control
    ex = state.exploration
    assert ex is not None and ex.player_id == "p1" and ex.position == "000"
    assert sorted(ex.queue) == sorted([_CULT, _IND])  # dwie planety → gracz wybiera kolejność

    # Dopóki eksploracja trwa, nie można zamknąć inwazji ani opuścić kroku.
    with pytest.raises(ValueError, match="Finish exploring"):
        invasion.advance(state, grid, registry)
    with pytest.raises(ValueError, match="Exploration is in progress"):
        tactical.next_step(state)
    with pytest.raises(ValueError, match="Exploration is in progress"):
        tactical.end_action(state)

    for _ in range(2):
        if state.exploration is not None and state.exploration.current is None:
            state = exploration.draw(state, registry, state.exploration.queue[0])
        option = next(o for o in exploration.options_for(state, registry) if o.enabled)
        state = exploration.resolve(state, registry, option.id, _first_param(option))
    assert state.exploration is not None and len(state.exploration.log) == 2
    state = exploration.finish(state)
    assert invasion.advance(state, grid, registry).invasion is None


def test_owned_or_traitless_planets_are_not_explored(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state({"infantry": 1})
    state.systems["000"].planet_owners[_CULT] = "p2"  # kontrolowana przez innego gracza
    state.players["p2"].controlled_planets = [_CULT]
    state = invasion.begin_invasion(state, grid, registry)
    state = invasion.commit_ground_forces(state, registry, {_CULT: {"infantry": 1}})
    state = invasion.advance(state, grid, registry)
    # (Atakujący nie wygrał walki — nie ma obrońcy, więc przejmuje planetę, ale NIE eksploruje.)
    assert state.invasion is not None
    assert state.exploration is None
