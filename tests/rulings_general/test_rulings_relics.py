"""Relikty — rulingi ``docs/rules_tirules/C_relics.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty, które sprawdza (strażnik
``tests/test_ruling_coverage.py``, kontrakt ogólny). Podstawowe testy reliktów są w
``tests/test_relics.py``; statusy bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    agenda_phase,
    battle,
    battle_rerolls,
    card_draw,
    command_tokens,
    control,
    economy,
    exhaust,
    exploration,
    objective_progress,
    payment,
    relic_cards,
    relics,
    rules_hooks,
    space_cannon,
    technology,
)
from src.core.game_state import CombatStep, GameState, Phase, PlayerState, SystemState
from src.core.hooks import relics_actions, relics_events, relics_passive
from src.core.planet_stats import is_legendary, planet_stats
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_relics import _combat_state, _first_planet, _fixed_dice, _rolled, _state
from tests.test_relics import _grid as _grid  # noqa: F401 - fixture autouse (siatka demo)
from tests.test_relics import registry as registry  # noqa: F401 - fixture modułu


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _give_mollprimus(state: GameState) -> tuple[str, str]:
    """p1 przejmuje Moll Primus (104): zwykła, nielegendarna, nie-domowa planeta."""
    state.systems["104"].planet_owners["mollprimus"] = "p1"
    state.systems["104"].planet_units["mollprimus"] = {"p1": {"infantry": 1}}
    state.players["p1"].controlled_planets.append("mollprimus")
    state.players["p2"].controlled_planets.remove("mollprimus")
    return "104", "mollprimus"


def _no_prereq(state: GameState, registry: StaticDataRegistry) -> list[str]:
    return [
        t.id for t in technology.tech_pool(state, registry, "p1").values()
        if not technology.prerequisites(t)
    ]


# ============================================================================ Book of Latvinia


@ruling("C_relics/book-of-latvinia/1", "C_relics/book-of-latvinia/1.1")
def test_book_researches_only_missing_no_prerequisite_techs(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["bookoflatvinia"])
    free = _no_prereq(state, registry)
    state.players["p1"].technologies = free[:-1]
    options = relics_passive.book_inputs(state, registry, "p1", {})[0]["options"]
    assert [o["value"] for o in options] == [free[-1]]  # wszystkie-oprócz-jednej: tylko ta jedna
    state.players["p1"].technologies = list(free)
    assert relics_passive.book_inputs(state, registry, "p1", {})[0]["options"] == []
    relics_passive.book_gained(state, "p1", {"params": {"technologies": []}})
    assert sorted(state.players["p1"].technologies) == sorted(free)


@ruling("C_relics/book-of-latvinia/2")
def test_book_cannot_research_a_tech_with_prerequisites(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["bookoflatvinia"])
    with_prereq = next(
        t.id for t in technology.tech_pool(state, registry, "p1").values()
        if technology.prerequisites(t) and not t.faction
    )
    with pytest.raises(ValueError, match="without prerequisites"):
        relics_passive.book_gained(state, "p1", {"params": {"technologies": [with_prereq]}})


@ruling("C_relics/book-of-latvinia/4", "C_relics/book-of-latvinia/5")
def test_book_action_purges_and_four_specialties_force_the_point(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(registry, ["bookoflatvinia"])
    state.speaker_id = "p2"
    relics_actions.book_of_latvinia(state, registry, "p1", {})
    assert state.speaker_id == "p1" and "bookoflatvinia" in state.decks.purged
    state = _state(registry, ["bookoflatvinia"])
    state.speaker_id = "p2"
    monkeypatch.setattr(relics_actions, "_all_specialties", lambda *_a: True)
    relics_actions.book_of_latvinia(state, registry, "p1", {"choice": "speaker"})
    assert state.players["p1"].victory_points == 1 and state.speaker_id == "p2"
    assert "bookoflatvinia" in state.decks.purged


# ============================================================================ Circlet of the Void


def _anomaly_line(anomaly: str) -> tuple[GameState, object, list[str]]:
    """Trasa 101 -> 000 (anomalia) -> 104; 101 i 104 nie sąsiadują (pierścień wokół centrum)."""
    from src.core.hex_grid import HexGrid

    grid = HexGrid()
    for position, system_id, anomalies in (
        ("000", "18", {anomaly}), ("101", "20", set()), ("104", "21", set()),
    ):
        grid.place_system(position, system_id, anomalies=anomalies)
    grid.build_edges()
    assert not grid.are_adjacent("101", "104")
    state = GameState(
        phase=Phase.ACTION, active_player_id="p1", active_system="104",
        players={"p1": PlayerState(player_id="p1", color="red", faction="sol")},
        systems={"101": SystemState(position="101", system_id="20",
                                    space_units={"p1": {"cruiser": 1}})},
    )
    return state, grid, ["101", "000", "104"]


@ruling(
    "C_relics/circlet-of-the-void/1",
    "C_relics/circlet-of-the-void/2",
    "C_relics/circlet-of-the-void/4",
)
@pytest.mark.parametrize("anomaly", ["SUPERNOVA", "ASTEROID_FIELD", "NEBULA"])
def test_circlet_moves_through_and_into_anomalies(
    registry: StaticDataRegistry, anomaly: str
) -> None:
    from src.core import movement

    state, grid, route = _anomaly_line(anomaly)
    assert movement.route_error(state, grid, route, "p1", "cruiser") is not None  # type: ignore[arg-type]
    state.players["p1"].relics = ["circletofthevoid"]
    state.players["p1"].exhausted_relics = ["circletofthevoid"]  # działa także wyczerpany
    assert movement.route_error(state, grid, route, "p1", "cruiser") is None  # type: ignore[arg-type]
    state.active_system = "000"  # wejście DO anomalii (aktywny system)
    assert movement.route_error(state, grid, route[:2], "p1", "cruiser") is None  # type: ignore[arg-type]
    ok, reason = movement.can_move(state, grid, registry, "101", "cruiser", "p1")  # type: ignore[arg-type]
    assert ok, reason


@ruling("C_relics/circlet-of-the-void/2")
def test_circlet_ships_leaving_a_nebula_keep_their_move_value(
    registry: StaticDataRegistry,
) -> None:
    from src.core import movement

    state, grid, _route = _anomaly_line("NEBULA")
    state.systems["000"] = SystemState(
        position="000", system_id="18", space_units={"p1": {"cruiser": 1}}
    )
    state.active_system = "104"
    ok, _ = movement.can_move(state, grid, registry, "000", "cruiser", "p1")  # type: ignore[arg-type]
    assert ok  # 1 krok - wystarcza nawet wartość 1
    state.players["p1"].relics = ["circletofthevoid"]
    value = movement._effective_move_value(
        state, grid, registry, "000", "cruiser", "p1", boost=False, tempesta=False,  # type: ignore[arg-type]
    )
    assert value is not None and value > 1


@ruling("C_relics/circlet-of-the-void/3", "C_relics/circlet-of-the-void/4")
def test_circlet_keeps_the_gravity_rift_bonus_without_rolling(registry: StaticDataRegistry) -> None:
    from src.core import movement

    state, grid, route = _anomaly_line("GRAVITY_RIFT")
    state.players["p1"].relics = ["circletofthevoid"]
    state.players["p1"].exhausted_relics = ["circletofthevoid"]
    assert movement.rift_nodes(state, grid, route, "p1") == ["000"]  # type: ignore[arg-type]
    assert not movement.rift_rolls(state, "p1")  # bez rzutu za szczelinę, premia +1 zostaje
    assert movement.roll_rift_exit(state, "p1", {"infantry": 3}) == {}


# ============================================================================ The Codex


@ruling("C_relics/the-codex/1")
def test_empty_action_deck_reshuffles_the_discard_before_the_codex(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["codex"])
    state.decks.action_card_deck = []
    state.decks.action_card_discard = ["sabotage1"]
    assert relics_actions.codex_inputs(state, registry, "p1")[0]["options"] == []
    with pytest.raises(ValueError, match="not in the action card discard pile"):
        relics_actions.codex(state, registry, "p1", {"cards": ["sabotage1"]})
    card_draw.reshuffle_action_deck_if_empty(state)
    assert state.decks.action_card_deck == ["sabotage1"] and state.decks.action_card_discard == []


@ruling("C_relics/the-codex/2")
def test_codex_cards_are_public(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["codex"])
    state.decks.action_card_deck = ["x"]
    state.decks.action_card_discard = ["sabotage1", "sabotage2"]
    options = relics_actions.codex_inputs(state, registry, "p2")[0]["options"]
    assert {o["value"] for o in options} == {"sabotage1", "sabotage2"}  # jawny stos dla każdego
    new_state, _ = relic_cards.play_relic(state, registry, "p1", "codex", {"cards": ["sabotage1"]})
    assert "sabotage1" in new_state.players["p1"].private.action_cards
    assert new_state.decks.action_card_discard == ["sabotage2"]  # wszyscy widzą, czego brakuje


# ============================================================================ The Crown of Thalnos


@ruling("C_relics/the-crown-of-thalnos/1")
def test_thalnos_rerolls_only_combat_rolls(registry: StaticDataRegistry) -> None:
    grid = build_demo_grid(registry)
    state = _combat_state(registry, ["thalnos"])
    state.active_combat.step = CombatStep.AFB  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="only after the roll"):
        battle_rerolls.reroll_with_relic(state, grid, registry, "p1", {0: [0]})


@ruling(
    "C_relics/the-crown-of-thalnos/2",
    "C_relics/the-crown-of-thalnos/4",
    "C_relics/the-crown-of-thalnos/5",
)
def test_thalnos_destroys_only_units_without_any_hit_before_assignment(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    grid = build_demo_grid(registry)
    monkeypatch.setattr(battle, "roll_dice", _fixed_dice(9))
    state = _combat_state(registry, [])
    state.systems["101"].space_units["p1"] = {"flagship": 1, "carrier": 1}
    state = battle.roll_round(state, grid, registry)
    state.players["p1"].relics = ["thalnos"]
    entries = state.active_combat.rolls["p1"]  # type: ignore[union-attr]
    warsun = next(i for i, e in enumerate(entries) if e["baseType"] == "flagship")
    dice = len(entries[warsun]["dice"])
    assert dice > 1  # War Sun rzuca kilkoma kośćmi - przerzut per jednostka (2.1)
    monkeypatch.setattr(battle_rerolls, "roll_dice", _fixed_dice(1))  # przerzut: 1 + 1 = 2, chybia
    after = battle_rerolls.reroll_with_relic(
        state, grid, registry, "p1", {warsun: list(range(1, dice))}
    )
    # War Sun zachował trafienie z NIEprzerzuconej kości: nie ginie (2).
    assert after.systems["101"].space_units["p1"].get("flagship", 0) == 1
    carrier = next(i for i, e in enumerate(entries) if e["baseType"] == "carrier")
    after = battle_rerolls.reroll_with_relic(after, grid, registry, "p1", {carrier: [0]})
    # Lotniskowiec bez trafienia ginie od razu - mimo Sustain Damage War Suna obok (5), jeszcze
    # w oknie rzutów, zanim ktokolwiek przypisze straty (4).
    assert after.systems["101"].space_units["p1"].get("carrier", 0) == 0
    assert after.active_combat.step is not CombatStep.ROLL  # type: ignore[union-attr]
    state.systems["101"].space_units["p1"] = {"dreadnought": 1}


@ruling("C_relics/the-crown-of-thalnos/5")
def test_thalnos_destroys_a_unit_with_sustain_damage(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    grid = build_demo_grid(registry)
    monkeypatch.setattr(battle, "roll_dice", _fixed_dice(9))
    state = _combat_state(registry, [])
    state.systems["101"].space_units["p1"] = {"dreadnought": 1}
    state = battle.roll_round(state, grid, registry)
    state.players["p1"].relics = ["thalnos"]
    monkeypatch.setattr(battle_rerolls, "roll_dice", _fixed_dice(1))
    after = battle_rerolls.reroll_with_relic(state, grid, registry, "p1", {0: [0]})
    assert after.systems["101"].space_units.get("p1", {}).get("dreadnought", 0) == 0


@ruling("C_relics/the-crown-of-thalnos/3")
def test_other_rerolls_do_not_destroy_units(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Zniszczenie za brak trafienia robi tylko ``reroll_with_relic`` (hook Thalnos); inne
    przerzuty (np. Heart of Ixth zmienia wynik, rzut bez trafień) nie usuwają jednostek."""
    grid = build_demo_grid(registry)
    state = _rolled(registry, ["heartofixth"], monkeypatch)
    after = battle_rerolls.adjust_die_with_relic(
        state, grid, registry, "p1", target="p1", entry_index=0, die_index=0, delta=-1
    )
    assert after.systems["101"].space_units["p1"]["carrier"] == 2


# ============================================================================ Dynamis Core


@ruling("C_relics/dynamis-core/1")
def test_dynamis_core_returns_commodities_over_the_printed_value(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["dynamiscore"])
    assert economy.commodity_value(state, "p1") == 5
    state.players["p1"].commodities = 5
    relics_actions.dynamis_core(state, registry, "p1", {})
    assert state.players["p1"].trade_goods == 5
    assert state.players["p1"].commodities == 3  # nadmiar ponad wartość z karty frakcji wraca



# ============================================================================ Dominus Orb


@ruling("C_relics/dominus-orb/1")
def test_dominus_orb_does_not_increase_the_move_distance(registry: StaticDataRegistry) -> None:
    from src.core import movement

    state, grid, _route = _anomaly_line("NONE")
    before = movement._effective_move_value(
        state, grid, registry, "101", "cruiser", "p1", boost=False, tempesta=False,  # type: ignore[arg-type]
    )
    state.players["p1"].relics = ["dominusorb"]
    relics_events.dominus_orb(state, "p1", {})
    after = movement._effective_move_value(
        state, grid, registry, "101", "cruiser", "p1", boost=False, tempesta=False,  # type: ignore[arg-type]
    )
    assert before is not None and after == before
    # 101 and 104 are not adjacent, so the route stays illegal.
    assert movement.route_error(state, grid, ["101", "104"], "p1", "cruiser") is not None  # type: ignore[arg-type]

# ============================================================================ Heart of Ixth


@ruling("C_relics/heart-of-ixth/1", "C_relics/the-silver-flame/3")
def test_d10_zero_is_ten_and_heart_turns_ten_into_nine_and_back(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    grid = build_demo_grid(registry)
    state = _rolled(registry, ["heartofixth"], monkeypatch, value=10)
    down = battle_rerolls.adjust_die_with_relic(
        state, grid, registry, "p1", target="p2", entry_index=0, die_index=0, delta=-1
    )
    assert down.active_combat.rolls["p2"][0]["dice"][0] == 9  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="between 1 and 10"):
        battle_rerolls.adjust_die_with_relic(
            state, grid, registry, "p1", target="p2", entry_index=0, die_index=0, delta=1
        )
    state = _rolled(registry, ["heartofixth"], monkeypatch, value=9)
    up = battle_rerolls.adjust_die_with_relic(
        state, grid, registry, "p1", target="p2", entry_index=0, die_index=0, delta=1
    )
    assert up.active_combat.rolls["p2"][0]["dice"][0] == 10  # type: ignore[union-attr]
    # The Silver Flame: wynik 10 (ściana „0”) daje punkt.
    flame = _state(registry, ["thesilverflame"])
    monkeypatch.setattr(relics_actions, "next_rng", lambda _s: _Fixed(10))
    relics_actions.the_silver_flame(flame, registry, "p1", {})
    assert flame.players["p1"].victory_points == 1


class _Fixed:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, _a: int, _b: int) -> int:
        return self.value


# ============================================================================ JR-XS455-O


@ruling("C_relics/jrxs455o/1")
def test_jr_is_an_agent_that_readies_in_the_status_phase(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["titanprototype"])
    new_state, _ = relic_cards.play_relic(
        state, registry, "p1", "titanprototype",
        {"player": "p1", "placement": "none", "planets": [], "trade_goods": 0},
    )
    assert new_state.players["p1"].exhausted_relics == ["titanprototype"]
    exhaust.ready_all_relics(new_state, "p1")  # jak w finalize_status (gotowość agentów)
    assert new_state.players["p1"].exhausted_relics == []


# ============================================================================ Lightrail Ordnance


@ruling("C_relics/lightrail-ordnance/1")
def test_lightrail_space_docks_fire_in_offense_and_defense(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["lightrailordnance"])
    position, planet = _first_planet(state)
    state.systems[position].planet_units[planet] = {"p1": {"spacedock": 1}}
    offense = space_cannon._system_shooters(state, registry, "p1", position)
    defense = space_cannon.zone_shooters(state, registry, "p1", position, planet)
    for shooters in (offense, defense):
        assert [s for s in shooters if s.base_type == "spacedock"]


# ============================================================================ Maw of Worlds


@ruling("C_relics/maw-of-worlds/1")
def test_maw_ignores_prerequisites(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["mawofworlds"])
    tech = next(
        t for t in technology.tech_pool(state, registry, "p1").values()
        if sum(technology.prerequisites(t).values()) >= 2 and not t.faction
    )
    relics_passive.maw_of_worlds(state, "p1", {"params": {"technology": tech.id}})
    assert tech.id in state.players["p1"].technologies


# ============================================================================ Metali Void Shielding


def _assign_with_granted_sustain(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> GameState:
    grid = build_demo_grid(registry)
    monkeypatch.setattr(battle, "roll_dice", _fixed_dice(9))
    state = _combat_state(registry, ["metalivoidshielding"])
    state = battle.roll_round(state, grid, registry)
    responder = state.pending_window.current_responder  # type: ignore[union-attr]
    if responder != "p1":
        state = battle.assign_combat_hits(
            state, grid, registry, "p2", sustain={}, destroy={"carrier": 2}, destroy_damaged={}
        )
    return battle.assign_combat_hits(
        state, grid, registry, "p1",
        sustain={"carrier": 1}, destroy={"carrier": 1}, destroy_damaged={},
    )


@ruling("C_relics/metali-void-shielding/1", "C_relics/metali-void-shielding/2")
def test_ship_using_granted_sustain_is_open_to_direct_hit_and_reflective_shielding(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _assign_with_granted_sustain(registry, monkeypatch)
    combat = state.active_combat
    sustained = combat.sustained_ships if combat is not None else []
    # Ten sam wpis co przy wrodzonym Sustain Damage: Direct Hit i Reflective Shielding go widzą.
    assert {"player": "p1", "base_type": "carrier", "count": 1} in sustained


@ruling("C_relics/metali-void-shielding/3")
def test_granted_sustain_is_counted_per_assignment(registry: StaticDataRegistry) -> None:
    """Limit „1 of those ships” liczy się w JEDNYM przypisaniu trafień - osobno dla AFB (Waylay)
    i dla rzutów walki tej samej rundy."""
    state = _combat_state(registry, ["metalivoidshielding"])
    grid = build_demo_grid(registry)
    carrier = next(u for u in battle.side_units(state, grid, registry, "p1"))
    for _assignment in ("afb", "combat"):
        assert battle.plan_losses({"carrier": carrier}, {"carrier": 1}, {}, {}, 1)


# ============================================================================ Nano-Forge


@ruling("C_relics/nanoforge/1", "C_relics/neuraloop/2")
def test_nano_forge_planet_is_legendary_for_objectives_and_converter(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["nanoforge", "neuraloop"])
    _position, planet = _give_mollprimus(state)
    grid = build_demo_grid(registry)
    before = objective_progress.progress(state, registry, grid, "p1", "make_history")
    relics_actions.nano_forge(state, registry, "p1", {"planet": planet})
    assert is_legendary(state, registry, planet)
    after_forge = objective_progress.progress(state, registry, grid, "p1", "make_history")
    assert before is not None and after_forge is not None and after_forge > before
    # Nie ma karty zdolności legendarnej (żadnego źródła hooków planety).
    assert rules_hooks.HookSource(rules_hooks.SOURCE_PLANET, planet) not in (
        rules_hooks.owned_sources(state, "p1")
    )
    # Stellar Converter nie celuje w (teraz) legendarną planetę.
    state.players["p2"].relics = ["stellarconverter"]
    assert planet not in [p for p, _ in relics_actions._converter_planets(state, registry, "p2")]
    # Neuraloop purge'uje przyczepione Nano-Forge: planeta traci premię i legendę.
    base = planet_stats(state, registry, planet)
    assert base is not None
    _reveal(state, registry)
    relics_events.neuraloop(state, "p1", _replace(state, f"attached:{planet}"))
    after = planet_stats(state, registry, planet)
    assert after is not None and after.resources == base.resources - 2
    assert not is_legendary(state, registry, planet)
    assert "nanoforge" in state.decks.purged


# ============================================================================ Neuraloop


def _deck(registry: StaticDataRegistry, kind: str) -> list[str]:
    from src.core.objectives import deck_card_ids

    return deck_card_ids(registry, kind)


def _reveal(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Odkryty prawdziwy cel etapu I, w talii etapu I jeden cel, reszta talii celów pusta."""
    old, s1a, s1b = _deck(registry, "public_stage_1_objective")[:3]
    state.objectives.revealed = [old]
    state.objectives.stage1_deck = [s1a]
    state.objectives.stage2_deck = []
    state.decks.secret_objective_deck = []
    return [old, s1a, s1b]


def _replace(state: GameState, relic: str) -> dict[str, object]:
    """Kontekst Neuraloop dla AKTUALNIE odkrytego celu i wybranego reliktu."""
    return {"objective": state.objectives.revealed[0], "params": {"relic": relic}}


def _neuraloop_state(registry: StaticDataRegistry, held: list[str]) -> GameState:
    state = _state(registry, ["neuraloop", *held])
    _reveal(state, registry)
    return state


@ruling("C_relics/neuraloop/1", "C_relics/neuraloop/3")
def test_neuraloop_purges_itself_without_resolving_purge_abilities(
    registry: StaticDataRegistry,
) -> None:
    state = _neuraloop_state(registry, ["dominusorb"])
    options = relics_events.neuraloop_inputs(state, registry, "p1", {})[0]["options"]
    assert "relic:neuraloop" in {o["value"] for o in options}
    relics_events.neuraloop(state, "p1", _replace(state, "relic:dominusorb"))
    # Dominus Orb wyrzucony, ale jego zdolność purge NIE działa.
    assert "dominusorb" in state.decks.purged
    assert not rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_OWN_CC, state, "p1")
    state.objectives.stage1_deck = [_deck(registry, "public_stage_1_objective")[2]]
    relics_events.neuraloop(state, "p1", _replace(state, "relic:neuraloop"))
    assert "neuraloop" in state.decks.purged


@ruling("C_relics/neuraloop/4")
def test_neuraloop_purging_circlet_ends_the_anomaly_immunity(registry: StaticDataRegistry) -> None:
    from src.core import movement

    state = _neuraloop_state(registry, ["circletofthevoid"])
    assert movement._ignores_anomalies(state, "p1")
    relics_events.neuraloop(state, "p1", _replace(state, "relic:circletofthevoid"))
    assert not movement._ignores_anomalies(state, "p1")


@ruling("C_relics/neuraloop/5", "C_relics/neuraloop/7")
def test_neuraloop_purging_dynamis_or_shard_applies_the_loss(registry: StaticDataRegistry) -> None:
    state = _neuraloop_state(registry, ["dynamiscore", "shard"])
    state.players["p1"].commodities = 5
    relics_events.neuraloop(state, "p1", _replace(state, "relic:dynamiscore"))
    assert state.players["p1"].commodities == 3
    relics_events.neuraloop(state, "p1", _replace(state, "relic:shard"))
    assert state.players["p1"].victory_points == -1


@ruling("C_relics/neuraloop/6")
def test_neuraloop_purging_obsidian_lowers_the_secret_limit(registry: StaticDataRegistry) -> None:
    from src.core import secret_objectives

    state = _neuraloop_state(registry, ["obsidian"])
    assert secret_objectives.secret_limit(state, "p1") == 4
    relics_events.neuraloop(state, "p1", _replace(state, "relic:obsidian"))
    assert secret_objectives.secret_limit(state, "p1") == 3


@ruling("C_relics/neuraloop/11", "C_relics/neuraloop/12", "C_relics/neuraloop/12.1")
def test_neuraloop_can_replace_the_replacement_and_bring_back_the_original(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["neuraloop", "codex", "dominusorb"])
    old, s1a, _ = _reveal(state, registry)
    relics_events.neuraloop(state, "p1", _replace(state, "relic:codex"))
    # Nowy cel odkryty z talii, odrzucony wraca do talii DOPIERO po odkryciu zastępnika.
    assert state.objectives.revealed == [s1a] and state.objectives.stage1_deck == [old]
    relics_events.neuraloop(state, "p1", _replace(state, "relic:dominusorb"))
    assert state.objectives.revealed == [old]  # oryginał może wrócić po kolejnym purge


@ruling("C_relics/neuraloop/9", "C_relics/neuraloop/8")
def test_secret_objective_revealed_by_neuraloop_is_public(registry: StaticDataRegistry) -> None:
    from src.core import secret_objectives

    state = _neuraloop_state(registry, ["codex"])
    state.objectives.stage1_deck = []
    secret = _deck(registry, "secret_objective")[0]
    state.decks.secret_objective_deck = [secret]
    relics_events.neuraloop(state, "p1", _replace(state, "relic:codex"))
    assert state.objectives.revealed == [secret]
    assert secret not in state.players["p1"].private.secret_objectives
    assert secret_objectives.secret_count(state, "p1") == 0  # nie liczy się do limitu tajnych


# ============================================================================ The Prophet's Tears


@ruling("C_relics/the-prophets-tears/1")
def test_prophets_tears_not_on_direct_gain(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core import triggers
    from src.core.game_events import GameEvent

    fired: list[object] = []
    original = triggers.fire

    def spy(state: GameState, event: object, *args: object, **kwargs: object) -> object:
        fired.append(event)
        return original(state, event, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(triggers, "fire", spy)
    state = _state(registry, ["prophetstears"])
    tech = next(iter(technology.tech_pool(state, registry, "p1")))
    technology.grant_technology(state, "p1", tech)  # bezpośrednie zdobycie
    assert GameEvent.TECHNOLOGY_RESEARCH not in fired  # okno Prophet's Tears się nie otwiera
    assert state.players["p1"].private.action_cards == []


# ============================================================================ Scepter of Emelpar


@ruling("C_relics/scepter-of-emelpar/2")
def test_scepter_without_reinforcements_means_spending_from_the_sheet(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["emelpar"])
    player = state.players["p1"]
    player.strategic_cc, player.cc_reinf = 2, 0
    with pytest.raises(ValueError, match="command sheet"):
        command_tokens.spend_strategy_token(state, "p1", source="scepter")
    command_tokens.spend_strategy_token(state, "p1")
    assert player.strategic_cc == 1


@ruling("C_relics/scepter-of-emelpar/1", "C_relics/scepter-of-emelpar/3")
def test_scepter_works_for_objectives_and_faction_abilities(registry: StaticDataRegistry) -> None:
    from src.core import objective_payment
    from src.core.hooks.factions import sol

    grid = build_demo_grid(registry)
    # Cel „Lead from the Front" (3 żetony): 2 z puli taktycznej + 1 strategiczny z rezerwy.
    state = _state(registry, ["emelpar"])
    player = state.players["p1"]
    player.tactical_cc, player.strategic_cc, player.cc_reinf = 2, 0, 3
    spec = objective_payment.spend_spec(state, registry, grid, "p1", "lead")
    assert spec is not None and spec["scepter"] is True
    assert spec["suggested"]["scepter"] is True
    paid = objective_payment.pay_for_objective(
        state, registry, grid, "p1", "lead",
        objective_payment.ObjectivePayment(tokens={"tactical": 2, "strategic": 1}, scepter=True),
    )
    after = paid.players["p1"]
    assert (after.tactical_cc, after.strategic_cc, after.cc_reinf) == (0, 0, 5)
    assert after.exhausted_relics == ["emelpar"]
    with pytest.raises(ValueError):  # bez Scepter puli strategicznej nie starcza
        objective_payment.pay_for_objective(
            state, registry, grid, "p1", "lead",
            objective_payment.ObjectivePayment(tokens={"tactical": 2, "strategic": 1}),
        )
    # Zdolność frakcji (Sol Orbital Drop): gracz wybiera źródło żetonu.
    state = _state(registry, ["emelpar"])
    player = state.players["p1"]
    player.strategic_cc, player.cc_reinf = 1, 2
    inputs = command_tokens.strategy_token_input(state, "p1")
    options = inputs[0]["options"]
    assert isinstance(options, list)
    assert [o["value"] for o in options] == ["pool", "scepter"]
    position, planet = next(
        (pos, pl) for pos, sys in sorted(state.systems.items())
        for pl, owner in sys.planet_owners.items() if owner == "p1"
    )
    sol.orbital_drop(
        state, registry, "p1", {"planet": f"{position}|{planet}", "token_source": "scepter"}
    )
    assert (player.strategic_cc, player.cc_reinf) == (1, 2)
    assert player.exhausted_relics == ["emelpar"]
    assert command_tokens.strategy_token_input(state, "p1") == []  # relikt wyczerpany


# ============================================================================ Shard of the Throne


@ruling("C_relics/shard-of-the-throne/1", "C_relics/shard-of-the-throne/2")
def test_shard_passes_only_with_legendary_or_home_planets(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["shard"])
    position, planet = _give_mollprimus(state)
    control.set_planet_control(state, position, planet, "p2", registry)
    assert state.players["p1"].relics == ["shard"]  # zwykła planeta: Shard zostaje
    home_planet = next(iter(state.systems["103"].planet_owners))
    control.set_planet_control(state, "103", home_planet, "p2", registry)
    assert state.players["p2"].relics == ["shard"]  # od razu, przed innymi zdolnościami
    assert state.players["p1"].victory_points == -1 and state.players["p2"].victory_points == 1


# ============================================================================ Stellar Converter


def _converter_setup(registry: StaticDataRegistry) -> tuple[GameState, str, str, str]:
    """p1 z dreadnoughtem (BOMBARDMENT) w systemie ``source``; zwraca (stan, źródło, sąsiad,
    planeta p2 w sąsiednim systemie)."""
    grid = build_demo_grid(registry)
    state = _state(registry, ["stellarconverter"])
    for position, system in sorted(state.systems.items()):
        for planet, owner in system.planet_owners.items():
            if owner != "p2" or position == "105" or is_legendary(state, registry, planet):
                continue
            source = next(
                (n for n in sorted(grid.neighbors(position)) if n in state.systems), None
            )
            if source is not None:
                state.systems[source].space_units["p1"] = {"dreadnought": 1}
                return state, source, position, planet
    pytest.skip("brak układu do testu Stellar Converter")
    raise AssertionError


@ruling("C_relics/stellar-converter/2")
def test_converter_targets_adjacent_systems_only_and_never_own_planets(
    registry: StaticDataRegistry,
) -> None:
    state, source, position, planet = _converter_setup(registry)
    targets = {p: pos for p, pos in relics_actions._converter_planets(state, registry, "p1")}
    assert targets.get(planet) == position
    assert all(pos != source for pos in targets.values())  # nie ten sam system co jednostka
    assert not any(state.systems[pos].planet_owners.get(p) == "p1" for p, pos in targets.items())


@ruling("C_relics/stellar-converter/1")
def test_system_with_only_a_destroyed_planet_has_no_planets(registry: StaticDataRegistry) -> None:
    from src.core.system_planets import planets_of_system

    state, _source, position, planet = _converter_setup(registry)
    relics_actions.stellar_converter(state, registry, "p1", {"planet": planet})
    assert planet not in planets_of_system(state, registry, position)
    assert planet in state.systems[position].destroyed_planets


# ============================================================================ The Triad


@ruling("C_relics/the-triad/3", "C_relics/the-triad/2.1")
def test_triad_votes_and_readies_at_the_end_of_the_agenda_phase(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["thetriad"])
    rows = {r["planet"]: r for r in agenda_phase.voting_planets(state, registry, "p1")}
    assert rows["relic:thetriad"]["influence"] == 3
    state.players["p1"].exhausted_relics = ["thetriad"]
    agenda_phase._ready_all_planets(state)
    assert state.players["p1"].exhausted_relics == []


@ruling(
    "C_relics/the-triad/1",
    "C_relics/the-triad/1.1",
    "C_relics/the-triad/1.2",
    "C_relics/the-triad/1.3",
    "C_relics/the-triad/1.4",
    "C_relics/the-triad/1.5",
    "C_relics/the-triad/1.6",
)
def test_triad_is_not_a_planet_for_other_effects(registry: StaticDataRegistry) -> None:
    from src.core.hooks import card_targets_economy

    state = _state(registry, ["thetriad", "nanoforge"])
    triad = "relic:thetriad"
    owned = [p for s in state.systems.values() for p in s.planet_owners]
    assert triad not in owned and triad not in state.players["p1"].controlled_planets
    assert not exploration.explorable(registry, triad)
    assert triad not in relics_actions._nanoforge_planets(state, registry, "p1")
    assert triad not in agenda_phase.candidate_outcomes(state, registry, "planet")
    uprising = card_targets_economy.uprising_targets(state, registry, "p2")
    assert triad not in str(uprising)
    grid = build_demo_grid(registry)
    view = objective_progress.View(state, registry, grid, "p1")
    assert triad not in view.owned
    assert payment.ready_planet_values(state, registry, "p1", "resources")[triad] == 3


# ============================================================================ Maw of Worlds (2)


@ruling("C_relics/maw-of-worlds/2")
def test_maw_exhausted_planets_ready_at_the_end_of_the_agenda_phase(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["mawofworlds"])
    tech_id = next(iter(technology.tech_pool(state, registry, "p1")))
    relics_passive.maw_of_worlds(state, "p1", {"params": {"technology": tech_id}})
    player = state.players["p1"]
    assert player.controlled_planets and set(player.controlled_planets) <= set(
        player.exhausted_planets
    )
    agenda_phase._ready_all_planets(state)
    assert player.exhausted_planets == []


@ruling("C_relics/the-triad/5")
def test_maw_does_not_exhaust_the_triad(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["mawofworlds", "thetriad"])
    tech_id = next(iter(technology.tech_pool(state, registry, "p1")))
    relics_passive.maw_of_worlds(state, "p1", {"params": {"technology": tech_id}})
    player = state.players["p1"]
    assert "relic:thetriad" not in player.exhausted_planets
    assert player.exhausted_relics == []  # The Triad stays ready


# ============================================================================ The Silver Flame


class _Rng:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, _low: int, _high: int) -> int:
        return self.value


@ruling("C_relics/the-silver-flame/1")
def test_silver_flame_saar_keeps_scoring_public_objectives(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core import objectives

    monkeypatch.setattr(relics_actions, "next_rng", lambda _s: _Rng(4))
    for faction, can_score in (("sol", False), ("saar", True)):
        state = _state(registry, ["thesilverflame"])
        state.players["p1"].faction = faction
        new_state, _ = relic_cards.play_relic(state, registry, "p1", "thesilverflame")
        assert not new_state.systems["103"].planet_owners  # the home system is purged
        assert objectives.controls_home_planets(new_state, registry, "p1") is can_score


@ruling("C_relics/the-silver-flame/2")
def test_silver_flame_puts_the_fracture_into_play_even_on_a_ten(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    for roll in (10, 4):
        monkeypatch.setattr(relics_actions, "next_rng", lambda _s, v=roll: _Rng(v))
        state = _state(registry, ["thesilverflame"])
        assert not state.fracture.in_play
        new_state, _ = relic_cards.play_relic(state, registry, "p1", "thesilverflame")
        assert new_state.fracture.in_play, f"roll {roll}"
        if roll == 10:
            assert new_state.systems["103"].planet_owners  # the home system is NOT purged


# ============================================================================ The Triad (2, 4, 6)


@ruling("C_relics/the-triad/2")
def test_triad_is_readied_by_effects_that_ready_planets(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["thetriad"])
    exhaust.exhaust_planets(state, "p1", ["relic:thetriad"])
    assert "relic:thetriad" not in payment.ready_planet_values(state, registry, "p1", "influence")
    exhaust.ready_planets(state, "p1", ["relic:thetriad"])  # e.g. Diplomacy
    assert "relic:thetriad" in payment.ready_planet_values(state, registry, "p1", "influence")


@ruling("C_relics/the-triad/4")
def test_triad_unknown_fragment_is_a_fourth_fragment_type(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["thetriad"])
    player = state.players["p1"]
    player.relic_fragments = ["crf1", "hrf1", "irf1"]
    three = payment.ready_planet_values(state, registry, "p1", "resources")["relic:thetriad"]
    player.relic_fragments = ["crf1", "hrf1", "irf1", "urf1"]
    four = payment.ready_planet_values(state, registry, "p1", "resources")["relic:thetriad"]
    assert (three, four) == (6, 7)


@ruling("C_relics/the-triad/6")
def test_saar_gaining_the_triad_gets_no_scavenge_trade_good(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    player = state.players["p1"]
    player.faction = "saar"
    state.decks.relic_deck, state.decks.relic_deck_seeded = ["thetriad"], True
    before = player.trade_goods
    assert relics.draw_relic(state, registry, "p1") == "thetriad"
    assert player.trade_goods == before
