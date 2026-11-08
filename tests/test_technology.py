"""Testy badania technologii i karty Technology (RULES.md 49)."""

from __future__ import annotations

import pytest

from src.core import strategic_action, technology
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _specialty_planet(registry: StaticDataRegistry, color: str) -> str:
    """Planeta z danych z dokładnie jedną specjalnością ``color`` (zero hardkodowania)."""
    for planet in registry.planets.values():
        if [s.upper() for s in (planet.tech_specialties or [])] == [color]:
            return planet.id
    raise AssertionError(f"No planet with a {color} specialty")


def _state(registry: StaticDataRegistry, techs: list[str], planets: list[str]) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        systems={
            "101": SystemState(
                position="101", system_id="26", planet_owners={p: "p1" for p in planets}
            )
        },
        players={
            "p1": PlayerState(
                player_id="p1", color="red", faction="sol", technologies=list(techs),
                strategy_cards=[7], trade_goods=10,
            ),
            "p2": PlayerState(player_id="p2", color="green", faction="hacan", trade_goods=10),
        },
    )


def test_prereq_letters_match_generic_tech_colors(registry: StaticDataRegistry) -> None:
    """Mapa liter prerekwizytów zgadza się z danymi: kolorowa technologia generyczna wymaga
    wyłącznie symboli własnego koloru (np. Hyper Metabolism = GG = BIOTIC)."""
    for tech in technology.generic_pool(registry).values():
        color = technology.tech_color(tech)
        if color is None or not tech.requirements:
            continue
        assert set(technology.prerequisites(tech)) == {color}, tech.id


def test_generic_pool_keeps_one_version_per_card(registry: StaticDataRegistry) -> None:
    pool = technology.generic_pool(registry)
    names = [technology._base_name(t.name) for t in pool.values()]
    assert len(names) == len(set(names))
    x89 = [t for t in pool.values() if technology._base_name(t.name) == "X-89 Bacterial Weapon"]
    assert len(x89) == 1 and x89[0].source == "codex4"  # najnowsza errata


def test_faction_upgrade_replaces_generic(registry: StaticDataRegistry) -> None:
    state = _state(registry, [], [])
    pool = technology.tech_pool(state, registry, "p1")
    own = technology.faction_techs(state, registry, "p1")
    for tech in own.values():
        if tech.base_upgrade:
            assert tech.base_upgrade not in pool  # np. Sol: inf2 → so2
    other = technology.faction_techs(state, registry, "p2")
    for tech_id in other:
        assert tech_id not in pool  # cudza technologia frakcyjna niedostępna


def _first(registry: StaticDataRegistry, color: str, symbols: int) -> str:
    for tech in technology.generic_pool(registry).values():
        if technology.tech_color(tech) == color and sum(
            technology.prerequisites(tech).values()
        ) == symbols:
            return tech.id
    raise AssertionError((color, symbols))


def test_research_requires_prerequisites(registry: StaticDataRegistry) -> None:
    tier1 = _first(registry, "BIOTIC", 1)
    tier0 = _first(registry, "BIOTIC", 0)
    with pytest.raises(ValueError, match="missing 1× biotic"):
        technology.research(_state(registry, [], []), registry, "p1", tier1)
    done = technology.research(_state(registry, [tier0], []), registry, "p1", tier1)
    assert tier1 in done.players["p1"].technologies


def test_specialty_planet_skips_one_matching_symbol(registry: StaticDataRegistry) -> None:
    tier1 = _first(registry, "BIOTIC", 1)
    green = _specialty_planet(registry, "BIOTIC")
    red = _specialty_planet(registry, "WARFARE")
    state = _state(registry, [], [green, red])
    with pytest.raises(ValueError, match="does not match"):
        technology.research(state, registry, "p1", tier1, [red])
    done = technology.research(state, registry, "p1", tier1, [green])
    assert green in done.players["p1"].exhausted_planets
    state.players["p1"].exhausted_planets = [green]
    with pytest.raises(ValueError, match="not a ready planet"):
        technology.research(state, registry, "p1", tier1, [green])


def test_useless_skip_and_owned_tech_rejected(registry: StaticDataRegistry) -> None:
    tier0 = _first(registry, "BIOTIC", 0)
    green = _specialty_planet(registry, "BIOTIC")
    state = _state(registry, [], [green])
    with pytest.raises(ValueError, match="does not match"):
        technology.research(state, registry, "p1", tier0, [green])
    with pytest.raises(ValueError, match="already own"):
        technology.research(_state(registry, [tier0], []), registry, "p1", tier0)


def test_aida_ignores_one_prerequisite_of_unit_upgrade(registry: StaticDataRegistry) -> None:
    state = _state(registry, [technology.AIDA], [])
    upgrade = next(
        t.id
        for t in technology.tech_pool(state, registry, "p1").values()
        if technology.UNIT_UPGRADE in t.types
        and not t.faction
        and len(set(technology.prerequisites(t))) == 1
        and sum(technology.prerequisites(t).values()) == 2
    )
    upgrade_def = registry.technologies[upgrade]
    # dokładamy technologie tak, by brakował dokładnie jeden symbol
    need = list(technology.prerequisites(upgrade_def).elements())
    if technology.missing_prerequisites(state, registry, "p1", upgrade_def).total() > 1:
        state.players["p1"].technologies.append(_first(registry, need[0], 0))
    if technology.missing_prerequisites(state, registry, "p1", upgrade_def).total() != 1:
        pytest.skip("data layout changed")
    done = technology.research(state, registry, "p1", upgrade, [technology.AIDA_SKIP])
    assert technology.AIDA in done.players["p1"].exhausted_technologies
    with pytest.raises(ValueError, match="only helps with unit upgrades"):
        technology.research(state, registry, "p1", _first(registry, "WARFARE", 1),
                            [technology.AIDA_SKIP])


def test_tree_view_statuses(registry: StaticDataRegistry) -> None:
    tier0 = _first(registry, "BIOTIC", 0)
    tier1 = _first(registry, "BIOTIC", 1)
    green = _specialty_planet(registry, "BIOTIC")
    rows = {r["id"]: r for r in technology.tree_view(_state(registry, [tier0], []), registry, "p1")}
    assert rows[tier0]["status"] == "owned"
    assert rows[tier1]["status"] == "available"
    rows = {r["id"]: r for r in technology.tree_view(_state(registry, [], [green]), registry, "p1")}
    assert rows[tier1]["status"] == "skippable"
    assert rows[tier1]["missing"] == {"BIOTIC": 1}


# --- Karta Technology -----------------------------------------------------------------------


def test_card_primary_free_then_paid_second(registry: StaticDataRegistry) -> None:
    tier0 = _first(registry, "BIOTIC", 0)
    tier1 = _first(registry, "BIOTIC", 1)
    state = strategic_action.play_strategy_card(_state(registry, [], []), registry, "p1", 7)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"tech": tier0})
    assert state.players["p1"].trade_goods == 10  # pierwsza za darmo
    # druga korzysta z pierwszej jako prerekwizytu, kosztuje 6 zasobów
    with pytest.raises(ValueError, match="at least 6"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"tech": tier1, "trade_goods": 5}
        )
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"tech": tier1, "trade_goods": 6}
    )
    p1 = state.players["p1"]
    assert {tier0, tier1} <= set(p1.technologies) and p1.trade_goods == 4
    assert state.pending_window is not None  # secondary otwarte


def test_card_primary_both_optional(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(registry, [], []), registry, "p1", 7)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"tech": None})
    state = strategic_action.submit_primary_step(state, registry, "p1", {"tech": None})
    assert state.players["p1"].technologies == []


def test_card_skip_planet_cannot_also_pay(registry: StaticDataRegistry) -> None:
    tier0 = _first(registry, "BIOTIC", 0)
    tier2 = _first(registry, "BIOTIC", 2)
    green = _specialty_planet(registry, "BIOTIC")
    state = strategic_action.play_strategy_card(
        _state(registry, [], [green]), registry, "p1", 7
    )
    state = strategic_action.submit_primary_step(state, registry, "p1", {"tech": tier0})
    with pytest.raises(ValueError, match="cannot also pay"):
        strategic_action.submit_primary_step(
            state, registry, "p1",
            {"tech": tier2, "skips": [green], "planets": [green], "trade_goods": 6},
        )


def test_card_secondary_costs_token_and_four(registry: StaticDataRegistry) -> None:
    tier0 = _first(registry, "PROPULSION", 0)
    state = strategic_action.play_strategy_card(_state(registry, [], []), registry, "p1", 7)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"tech": None})
    state = strategic_action.submit_primary_step(state, registry, "p1", {"tech": None})
    prompt = strategic_action.step_options(state, registry, "p2")
    assert prompt is not None and prompt["options"]["cost"] == 4
    with pytest.raises(ValueError, match="at least 4"):
        strategic_action.resolve_secondary(
            state, registry, "p2", execute=True, payload={"tech": tier0, "trade_goods": 3}
        )
    state = strategic_action.resolve_secondary(
        state, registry, "p2", execute=True, payload={"tech": tier0, "trade_goods": 4}
    )
    p2 = state.players["p2"]
    assert tier0 in p2.technologies and p2.trade_goods == 6 and p2.strategic_cc == 1
