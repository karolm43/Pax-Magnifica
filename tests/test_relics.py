"""Relikty (RULES.md 59): formularze, zagrywalność ACTION, efekty pasywne i zdarzeniowe.

Odpowiednik smoke testu kart akcji: dla WSZYSTKICH reliktów aktywnej talii sprawdza formularz i
zagrywalność, a dla zakodowanych efektów - skutek na stanie (relikt zostaje, wyczerpuje się albo
jest purge'owany).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.demo_map import build_demo_grid
from src.core import (
    battle,
    board_graph,
    control,
    economy,
    exhaust,
    payment,
    planet_stats,
    relic_actions,
    relic_cards,
    relics,
    rules_hooks,
    secret_objectives,
    space_cannon,
    technology,
)
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState, SystemState, TacticalStep
from src.core.objectives import deck_card_ids
from src.core.registry import StaticDataRegistry

# Relikty z nagłówkiem „ACTION:” w tekście karty (assets/data/relics, aktywne źródła).
ACTION_RELICS = {
    "codex", "dynamiscore", "nanoforge", "stellarconverter", "titanprototype",
    "bookoflatvinia", "circletofthevoid", "thesilverflame",
}


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(autouse=True, scope="module")
def _grid(registry: StaticDataRegistry) -> Iterator[None]:
    grid = build_demo_grid(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield
    board_graph.bind_grid_provider(previous)


def _state(registry: StaticDataRegistry, held: list[str]) -> GameState:
    """p1 (aktywny, z relikwiami ``held``) i p2 na mapie demo, każdy z 3 systemami i planetami."""
    grid = build_demo_grid(registry)
    systems = {
        pos: SystemState(position=pos, system_id=grid.system_id_at(pos))
        for pos in sorted(grid.positions)
    }
    for owner, positions in (("p1", ("101", "102", "103")), ("p2", ("104", "105", "106"))):
        for position in positions:
            system = systems[position]
            for planet in registry.systems[system.system_id].planets:
                system.planet_owners[planet] = owner
                system.planet_units[planet] = {owner: {"infantry": 1}}
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(
                player_id="p1", color="red", faction="sol", home_position="103",
                commodity_value=3, relics=list(held),
            ),
            "p2": PlayerState(
                player_id="p2", color="blue", faction="arborec", home_position="105",
                commodity_value=2,
            ),
        },
        systems=systems,
    )
    for pid, player in state.players.items():
        player.controlled_planets = [
            p for s in systems.values() for p, o in s.planet_owners.items() if o == pid
        ]
    return state


def _first_planet(state: GameState) -> tuple[str, str]:
    """Pierwsza pozycja systemu z planetą p1 i jej id."""
    for position, system in state.systems.items():
        for planet, owner in system.planet_owners.items():
            if owner == "p1":
                return position, planet
    raise AssertionError("brak planety p1")


def _pick(inputs: list[dict[str, Any]], key: str) -> Any:
    item = next(i for i in inputs if i["key"] == key)
    return item["options"][0]["value"]


# ------------------------------------------------------------------------------ wszystkie relikty


def test_every_relic_has_form_and_playability(registry: StaticDataRegistry) -> None:
    ids = deck_card_ids(registry, "relic")
    assert ids, "talia reliktów jest pusta"
    state = _state(registry, ids)
    rows = {row["relic_id"]: row for row in relic_cards.playability(state, registry, "p1")}
    assert set(rows) == set(ids)
    for relic_id in ids:
        info = relic_actions.form(state, registry, "p1", relic_id)
        assert info["kind"] == ("action" if relic_id in ACTION_RELICS else "passive"), relic_id
        assert info["name"] and info["text"]
        row = rows[relic_id]
        assert row["kind"] == info["kind"]
        if info["kind"] == "passive":
            assert row["playable"] is False and row["reason"]


def test_action_relic_set_matches_card_text(registry: StaticDataRegistry) -> None:
    found = {
        r for r in deck_card_ids(registry, "relic") if relic_actions.is_action_relic(registry, r)
    }
    assert found == ACTION_RELICS


def test_playing_unowned_or_passive_relic_is_rejected(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["shard"])
    with pytest.raises(ValueError):
        relic_cards.play_relic(state, registry, "p1", "codex")  # nie ma go
    with pytest.raises(ValueError):
        relic_cards.play_relic(state, registry, "p1", "shard")  # pasywny


def test_relic_action_only_on_own_turn(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["dynamiscore"])
    state.active_player_id = "p2"
    row = relic_cards.playability(state, registry, "p1")[0]
    assert row["playable"] is False and row["reason"]


# ------------------------------------------------------------------------------ efekty ACTION


def test_dynamis_core_passive_and_action(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["dynamiscore"])
    assert economy.commodity_value(state, "p1") == 5  # 3 + 2 z karty
    state.players["p1"].commodities = 5
    new_state, implemented = relic_cards.play_relic(state, registry, "p1", "dynamiscore")
    assert implemented
    player = new_state.players["p1"]
    assert player.trade_goods == 5  # TG równe commodity value Z bonusem (liczone przed purge)
    assert "dynamiscore" not in player.relics and "dynamiscore" in new_state.decks.purged
    assert player.commodities == 3  # nadmiar wraca do puli po utracie karty
    assert player.took_action_this_turn
    assert state.players["p1"].trade_goods == 0  # wejście nie zmutowane


def test_codex_takes_cards_from_discard(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["codex"])
    discard = deck_card_ids(registry, "action_card")[:5]
    state.decks.action_card_discard = list(discard)
    new_state, _ = relic_cards.play_relic(
        state, registry, "p1", "codex", {"cards": [discard[0], discard[3]]}
    )
    assert sorted(new_state.players["p1"].private.action_cards) == sorted([discard[0], discard[3]])
    assert len(new_state.decks.action_card_discard) == 3
    assert "codex" not in new_state.players["p1"].relics
    with pytest.raises(ValueError):
        relic_cards.play_relic(state, registry, "p1", "codex", {"cards": ["no_such_card"]})
    with pytest.raises(ValueError):
        relic_cards.play_relic(state, registry, "p1", "codex", {"cards": discard[:4]})


def test_book_of_latvinia_gives_speaker_without_all_specialties(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["bookoflatvinia"])
    state.speaker_id = "p2"
    new_state, implemented = relic_cards.play_relic(state, registry, "p1", "bookoflatvinia")
    assert implemented
    assert new_state.speaker_id == "p1"
    assert new_state.players["p1"].victory_points == 0
    assert "bookoflatvinia" in new_state.decks.purged


def test_book_of_latvinia_gives_vp_with_all_four_specialties(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["bookoflatvinia"])
    by_color: dict[str, str] = {}
    for planet_id, planet in registry.planets.items():
        for spec in planet.tech_specialties or []:
            by_color.setdefault(spec.upper(), planet_id)
    assert {"BIOTIC", "CYBERNETIC", "PROPULSION", "WARFARE"} <= set(by_color)
    system = state.systems["101"]
    for planet_id in by_color.values():
        system.planet_owners[planet_id] = "p1"
    new_state, _ = relic_cards.play_relic(state, registry, "p1", "bookoflatvinia")
    assert new_state.players["p1"].victory_points == 1


def test_nano_forge_attaches_and_makes_planet_legendary(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["nanoforge"])
    # Własna planeta nielegendarna i nie-domowa (planety demo p1 to dom i legenda).
    plain = next(
        p for p in state.systems["104"].planet_owners
        if not registry.planets[p].legendary_ability_name
        and p not in {"jord", "nestphar"}
    )
    state.systems["104"].planet_owners[plain] = "p1"
    form = relic_actions.form(state, registry, "p1", "nanoforge")
    planet = _pick(form["inputs"], "planet")
    assert planet == plain
    before = planet_stats.planet_stats(state, registry, planet)
    assert before is not None
    new_state, _ = relic_cards.play_relic(state, registry, "p1", "nanoforge", {"planet": planet})
    after = planet_stats.planet_stats(new_state, registry, planet)
    assert after is not None
    assert after.resources == before.resources + 2 and after.influence == before.influence + 2
    assert planet_stats.is_legendary(new_state, registry, planet)
    assert "nanoforge" not in new_state.players["p1"].relics
    assert new_state.planet_attachments[planet] == ["nanoforge"]
    # Po przyczepieniu akcji nie da się powtórzyć (karty nie ma już przed graczem).
    with pytest.raises(ValueError):
        relic_cards.play_relic(
            new_state.model_copy(update={"players": new_state.players}), registry, "p1",
            "nanoforge", {"planet": planet},
        )


def test_circlet_exhausts_and_blocks_when_exhausted(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["circletofthevoid"])
    state.systems["102"].frontier_token = True
    row = relic_cards.playability(state, registry, "p1")[0]
    assert row["playable"] is True
    new_state, _ = relic_cards.play_relic(
        state, registry, "p1", "circletofthevoid", {"position": "102"}
    )
    assert "circletofthevoid" in new_state.players["p1"].exhausted_relics
    assert "circletofthevoid" in new_state.players["p1"].relics
    blocked = relic_cards.playability(
        new_state.model_copy(update={"active_player_id": "p1"}), registry, "p1"
    )[0]
    assert blocked["playable"] is False


def test_circlet_rejects_frontier_with_foreign_ships(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["circletofthevoid"])
    state.systems["102"].frontier_token = True
    state.systems["102"].space_units = {"p2": {"destroyer": 1}}
    with pytest.raises(ValueError):
        relic_cards.play_relic(state, registry, "p1", "circletofthevoid", {"position": "102"})


def test_stellar_converter_destroys_adjacent_planet(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["stellarconverter"])
    grid = build_demo_grid(registry)
    source = "101"
    state.systems[source].space_units = {"p1": {"dreadnought": 1}}
    target_pos = next(
        pos for pos in sorted(grid.neighbors(source))
        if pos in ("104", "105", "106")
        and any(
            registry.planets[p].legendary_ability_name is None
            for p in registry.systems[state.systems[pos].system_id].planets
        )
    ) if any(p in ("104", "105", "106") for p in grid.neighbors(source)) else None
    if target_pos is None:
        pytest.skip("mapa demo: system 101 nie sąsiaduje z żadnym systemem p2")
    form = relic_actions.form(state, registry, "p1", "stellarconverter")
    options = form["inputs"][0]["options"]
    assert options, "brak legalnego celu mimo okrętu z Bombardment obok"
    planet = options[0]["value"]
    new_state, _ = relic_cards.play_relic(
        state, registry, "p1", "stellarconverter", {"planet": planet}
    )
    destroyed = [s for s in new_state.systems.values() if planet in s.destroyed_planets]
    assert len(destroyed) == 1
    assert planet not in destroyed[0].planet_owners
    assert planet not in destroyed[0].planet_units
    assert "stellarconverter" in new_state.decks.purged


# ------------------------------------------------------------------------------ Silver Flame


class _Rng:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, _low: int, _high: int) -> int:
        return self.value


def test_silver_flame_roll_ten_gives_vp(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core.hooks import relics_actions

    monkeypatch.setattr(relics_actions, "next_rng", lambda _s: _Rng(10))
    state = _state(registry, ["thesilverflame"])
    new_state, implemented = relic_cards.play_relic(state, registry, "p1", "thesilverflame")
    assert implemented
    assert new_state.players["p1"].victory_points == 1
    assert "thesilverflame" in new_state.decks.purged
    assert new_state.table_roll is not None and new_state.table_roll["dice"] == [10]


def test_silver_flame_failure_purges_home_system(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core.hooks import relics_actions

    monkeypatch.setattr(relics_actions, "next_rng", lambda _s: _Rng(4))
    state = _state(registry, ["thesilverflame"])
    home = state.systems["103"]
    home.space_units = {"p1": {"destroyer": 1}}
    new_state, _ = relic_cards.play_relic(state, registry, "p1", "thesilverflame")
    new_home = new_state.systems["103"]
    assert new_state.players["p1"].victory_points == 0
    assert not new_home.space_units.get("p1")
    assert not new_home.planet_owners
    assert new_home.destroyed_planets
    assert new_state.fracture.in_play


# ------------------------------------------------------------------------------ pasywne


def test_shard_vp_on_gain_and_loss(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    state.players["p2"].relics = ["shard"]
    relics.transfer(state, "p2", "p1", "shard")
    assert state.players["p1"].victory_points == 1  # „when you gain this card”
    assert state.players["p2"].victory_points == -1  # „when you lose this card”
    assert state.players["p1"].relics == ["shard"] and not state.players["p2"].relics


def test_shard_passes_with_legendary_planet(registry: StaticDataRegistry) -> None:
    legendary = next(
        pid for pid, p in registry.planets.items() if p.legendary_ability_name
    )
    state = _state(registry, [])
    state.players["p2"].relics = ["shard"]
    state.systems["104"].planet_owners[legendary] = "p2"
    control.set_planet_control(state, "104", legendary, "p1", registry)
    assert state.players["p1"].relics == ["shard"]
    assert state.players["p1"].victory_points == 1
    assert state.players["p2"].victory_points == -1


def test_shard_passes_with_planet_in_home_system(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    state.players["p2"].relics = ["shard"]
    home_planet = next(iter(state.systems["105"].planet_owners))
    control.set_planet_control(state, "105", home_planet, "p1", registry)
    assert state.players["p1"].relics == ["shard"]


def test_obsidian_raises_secret_limit(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    assert secret_objectives.secret_limit(state, "p1") == 3
    state.players["p1"].relics = ["obsidian"]
    assert secret_objectives.secret_limit(state, "p1") == 4


def test_relics_ready_in_status_phase_helper(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["circletofthevoid", "heartofixth"])
    exhaust.exhaust_relic(state, "p1", "circletofthevoid")
    exhaust.exhaust_relic(state, "p1", "circletofthevoid")  # idempotentne
    assert state.players["p1"].exhausted_relics == ["circletofthevoid"]
    assert not relics.is_ready(state, "p1", "circletofthevoid")
    exhaust.ready_all_relics(state, "p1")
    assert relics.is_ready(state, "p1", "circletofthevoid")


def test_purged_relic_is_not_returned_to_deck(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["codex"])
    relics.purge_relic(state, "p1", "codex")
    assert "codex" not in state.decks.relic_deck and "codex" not in state.decks.relic_discard
    assert "codex" in state.decks.purged


# ------------------------------------------------------------------------------ API


def _client(registry: StaticDataRegistry, held: list[str]) -> TestClient:
    return TestClient(
        create_app(
            registry=registry, store=EventStore(":memory:"), initial_state=_state(registry, held)
        )
    )


def test_relic_endpoints_playable_inputs_and_play(registry: StaticDataRegistry) -> None:
    client = _client(registry, ["dynamiscore", "shard"])
    playable = client.get("/relic/playable", params={"player_id": "p1"}).json()["relics"]
    by_id = {row["relic_id"]: row for row in playable}
    assert by_id["dynamiscore"]["kind"] == "action" and by_id["dynamiscore"]["playable"] is True
    assert by_id["shard"]["kind"] == "passive" and by_id["shard"]["playable"] is False

    form = client.get("/relic/dynamiscore/inputs", params={"player_id": "p1"}).json()
    assert form["kind"] == "action" and form["implemented"] is True and form["inputs"] == []

    resp = client.post(
        "/relic/play", json={"player_id": "p1", "relic_id": "dynamiscore"},
        headers={"X-Actor-Id": "p1"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["implemented"] is True
    me = client.get("/state").json()["state"]["players"]["p1"]
    assert me["trade_goods"] == 5 and "dynamiscore" not in me["relics"]


def test_relic_endpoint_rejects_unowned_and_passive(registry: StaticDataRegistry) -> None:
    client = _client(registry, ["shard"])
    missing = client.post("/relic/play", json={"player_id": "p1", "relic_id": "codex"})
    assert missing.status_code == 422
    passive = client.post("/relic/play", json={"player_id": "p1", "relic_id": "shard"})
    assert passive.status_code == 422
    assert client.get("/relic/codex/inputs", params={"player_id": "p1"}).status_code == 422


# ------------------------------------------------------------------------------ walka i kości


def _fixed_dice(value: int) -> object:
    def roll(state: GameState, count: int, sides: int = 10) -> tuple[GameState, list[int]]:
        return state, [value] * count

    return roll


def _combat_state(registry: StaticDataRegistry, held: list[str]) -> GameState:
    """Dwa lotniskowce na stronę w systemie 101, walka kosmiczna w kroku rzutów.

    Relikty ``held`` dostaje p1 PO starcie walki (oferty z hooków startu nie wstrzymują testu).
    """
    state = _state(registry, [])
    state.active_system = "101"
    state.tactical_step = TacticalStep.SPACE_COMBAT
    state.systems["101"].space_units = {"p1": {"carrier": 2}, "p2": {"carrier": 2}}
    grid = build_demo_grid(registry)
    state = battle.start_combat(state, grid, registry)
    state = battle.announce_retreat(state, grid, "p2", announce=False)
    state.players["p1"].relics = list(held)
    return state


def _rolled(
    registry: StaticDataRegistry, held: list[str], monkeypatch: pytest.MonkeyPatch, value: int = 9
) -> GameState:
    """Stan po rzucie rundy ze STAŁYMI kośćmi (próg trafienia lotniskowca = 9)."""
    monkeypatch.setattr(battle, "roll_dice", _fixed_dice(value))
    return battle.roll_round(_combat_state(registry, held), build_demo_grid(registry), registry)


def test_adjust_die_with_heart_of_ixth(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    grid = build_demo_grid(registry)
    state = _rolled(registry, ["heartofixth"], monkeypatch)
    assert {"player": "p1", "tool": "adjust"} in battle.dice_relic_tools(state)
    before = state.active_combat.rolls["p2"][0]["dice"][0]  # type: ignore[union-attr]
    delta = -1 if before > 1 else 1
    new_state = battle.adjust_die_with_relic(
        state, grid, registry, "p1", target="p2", entry_index=0, die_index=0, delta=delta
    )
    assert new_state.active_combat.rolls["p2"][0]["dice"][0] == before + delta  # type: ignore[union-attr]
    assert new_state.players["p1"].exhausted_relics == ["heartofixth"]
    # Wyczerpany relikt nie pozwala na kolejną zmianę.
    with pytest.raises(ValueError):
        battle.adjust_die_with_relic(
            new_state, grid, registry, "p1", target="p2", entry_index=0, die_index=0, delta=delta
        )


def test_thalnos_reroll_destroys_units_without_hits(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    grid = build_demo_grid(registry)
    state = _rolled(registry, ["thalnos"], monkeypatch)
    monkeypatch.setattr(battle, "roll_dice", _fixed_dice(2))  # przerzut: 2 + 1 = 3, bez trafień
    new_state = battle.reroll_with_relic(state, grid, registry, "p1", {0: [0, 1]})
    entry = new_state.active_combat.rolls["p1"][0]  # type: ignore[union-attr]
    assert entry["bonus"] == [1, 1] and entry["rerolled"] == [0, 1]
    survivors = new_state.systems["101"].space_units.get("p1", {}).get("carrier", 0)
    hits_after = sum(
        1 for d, b in zip(entry["dice"], entry["bonus"], strict=True) if d + b >= entry["hitsOn"]
    )
    assert survivors == hits_after == 0  # jednostki bez trafienia po przerzucie giną
    # Bez Crown of Thalnos przerzut jest zabroniony.
    plain = _rolled(registry, [], monkeypatch)
    with pytest.raises(ValueError):
        battle.reroll_with_relic(plain, grid, registry, "p1", {0: [0]})


def test_void_shielding_grants_at_most_one_sustain(registry: StaticDataRegistry) -> None:
    state = _combat_state(registry, ["metalivoidshielding"])
    grid = build_demo_grid(registry)
    carrier = next(u for u in battle.side_units(state, grid, registry, "p1"))
    assert carrier.granted == 1 and not carrier.sustain
    state.active_combat.pending_hits = {"p1": 3}  # type: ignore[union-attr]
    assert battle.required_hits(state, grid, registry, "p1") == 3  # 2 statki + 1 nadany Sustain
    ok = battle.plan_losses({"carrier": carrier}, {"carrier": 1}, {"carrier": 1}, {}, 2)
    assert ok["carrier"] == (1, 1)
    with pytest.raises(ValueError):
        battle.plan_losses({"carrier": carrier}, {"carrier": 2}, {}, {}, 2)


def test_armaments_offer_adds_afb_for_the_owner(registry: StaticDataRegistry) -> None:
    from src.core.hooks import relics_combat

    state = _combat_state(registry, ["metalivoidarmaments"])
    relics_combat.metali_void_armaments(state, "p1", {})
    assert state.active_combat.afb_extra == ["p1"]  # type: ignore[union-attr]
    assert rules_hooks.forbidden(rules_hooks.POINT_COMBAT_AFB_GRANTED, state, "p1") == {"6:3"}
    assert rules_hooks.forbidden(rules_hooks.POINT_COMBAT_AFB_GRANTED, state, "p2") == set()


def test_lightrail_gives_space_cannon_to_space_docks(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["lightrailordnance"])
    position, planet = _first_planet(state)
    state.systems[position].planet_units[planet] = {"p1": {"spacedock": 1}}
    shooters = [s for s in space_cannon._system_shooters(state, registry, "p1", position)
                if s.base_type == "spacedock"]
    assert len(shooters) == 1
    assert (shooters[0].hits_on, shooters[0].dice_per_unit, shooters[0].deep) == (5, 2, True)
    state.players["p1"].relics = []
    assert not [s for s in space_cannon._system_shooters(state, registry, "p1", position)
                if s.base_type == "spacedock"]


# ------------------------------------------------------------------------------ ekonomia i badania


def test_triad_is_a_spendable_pseudo_planet(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["thetriad"])
    state.players["p1"].relic_fragments = ["crf1", "crf2", "hrf1"]
    ready = payment.ready_planet_values(state, registry, "p1", "influence")
    assert ready["relic:thetriad"] == 5  # 3 + dwa różne typy fragmentów
    paid = payment.validate_payment(state, registry, "p1", "resources", ["relic:thetriad"], 0)
    assert paid == 5
    payment.apply_payment(state, "p1", ["relic:thetriad"], 0)
    assert state.players["p1"].exhausted_relics == ["thetriad"]
    assert "relic:thetriad" not in payment.ready_planet_values(state, registry, "p1", "influence")
    exhaust.ready_planets(state, "p1", ["relic:thetriad"])  # np. Diplomacy
    assert "relic:thetriad" in payment.ready_planet_values(state, registry, "p1", "influence")
    exhaust.exhaust_planets(state, "p1", ["relic:thetriad"])
    exhaust.ready_all_planets(state, "p1")
    assert state.players["p1"].exhausted_relics == []


def test_emelpar_spends_from_reinforcements(registry: StaticDataRegistry) -> None:
    from src.core import command_tokens

    state = _state(registry, ["emelpar"])
    player = state.players["p1"]
    player.strategic_cc, player.cc_reinf = 2, 1
    assert rules_hooks.forbidden(
        rules_hooks.POINT_STRATEGY_TOKEN_FROM_REINFORCEMENTS, state, "p1"
    ) == {"emelpar"}
    command_tokens.spend_strategy_token(state, "p1", via_reinforcements=True)
    assert (player.strategic_cc, player.cc_reinf) == (2, 1)
    player.cc_reinf = 0
    with pytest.raises(ValueError):
        command_tokens.spend_strategy_token(state, "p1", via_reinforcements=True)
    command_tokens.spend_strategy_token(state, "p1")
    assert player.strategic_cc == 1


def test_prophets_tears_ignores_one_prerequisite(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["prophetstears"])
    pool = technology.tech_pool(state, registry, "p1")
    tech = next(
        t for t in pool.values()
        if sum(technology.prerequisites(t).values()) == 1 and not t.faction
    )
    with pytest.raises(ValueError):
        technology.plan_research(state, registry, "p1", tech.id, [])
    plan = technology.plan_research(state, registry, "p1", tech.id, ["relic:prophetstears"])
    assert plan.exhaust_relics == ("prophetstears",)
    technology.apply_research(state, "p1", plan)
    assert tech.id in state.players["p1"].technologies
    assert state.players["p1"].exhausted_relics == ["prophetstears"]
    with pytest.raises(ValueError):  # wyczerpany relikt nie ignoruje prerekwizytu
        other = next(
            t for t in technology.tech_pool(state, registry, "p1").values()
            if t.id not in state.players["p1"].technologies
            and sum(technology.missing_prerequisites(state, registry, "p1", t).values()) == 1
        )
        technology.plan_research(state, registry, "p1", other.id, ["relic:prophetstears"])


def test_quantumcore_gives_synergy_for_all_colors(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    assert technology.synergy(state, registry, "p1") is None
    state.players["p1"].relics = ["quantumcore"]
    assert set(technology.synergy(state, registry, "p1") or ()) == set(technology.COLORS)


# ------------------------------------------------------------------------------ zdarzenia


def test_dominus_orb_lets_units_leave_systems_with_own_command_token(
    registry: StaticDataRegistry,
) -> None:
    from src.core.hooks import relics_events

    state = _state(registry, ["dominusorb"])
    assert not rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_OWN_CC, state, "p1")
    relics_events.dominus_orb(state, "p1", {})
    assert "dominusorb" in state.decks.purged
    assert rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_OWN_CC, state, "p1")
    assert not rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_OWN_CC, state, "p2")


def test_emphidia_purges_for_a_point_with_the_tomb(registry: StaticDataRegistry) -> None:
    from src.core.hooks import relics_events

    state = _state(registry, ["emphidia"])
    assert not relics_events._controls_tomb(state, "p1", {})
    _position, planet = _first_planet(state)
    state.systems[_position].planet_owners[planet] = "p1"
    state.planet_attachments[planet] = ["toe"]  # karta eksploracji „Tomb of Emphidia”
    assert relics_events._controls_tomb(state, "p1", {})
    relics_events.emphidia_tomb(state, "p1", {})
    assert state.players["p1"].victory_points == 1 and "emphidia" in state.decks.purged


def test_neuraloop_replaces_the_revealed_objective(registry: StaticDataRegistry) -> None:
    from src.core.hooks import relics_events

    state = _state(registry, ["neuraloop", "shard"])
    state.objectives.revealed = ["old"]
    state.objectives.stage1_deck = ["s1a", "s1b"]
    state.objectives.stage2_deck = ["s2a"]
    state.decks.secret_objective_deck = ["sec1"]
    relics_events.neuraloop(
        state, "p1", {"objective": "old", "params": {"relic": "relic:shard"}}
    )
    assert "shard" in state.decks.purged and state.players["p1"].victory_points == -1
    assert state.objectives.revealed != ["old"] and len(state.objectives.revealed) == 1
    pool = [*state.objectives.stage1_deck, *state.objectives.stage2_deck,
            *state.decks.secret_objective_deck]
    assert len(pool) == 4 and len(set(pool)) == 4  # wylosowany zdjęty z talii, "old" wraca do talii
    with pytest.raises(ValueError):
        relics_events.neuraloop(
            state, "p1", {"objective": "x", "params": {"relic": "relic:codex"}}
        )


def test_titan_prototype_gives_trade_good_or_structure(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["titanprototype"])
    new_state, implemented = relic_cards.play_relic(
        state, registry, "p1", "titanprototype",
        {"player": "p2", "placement": "none", "planets": [], "trade_goods": 0},
    )
    assert implemented
    assert new_state.players["p2"].trade_goods == 1
    assert new_state.players["p1"].exhausted_relics == ["titanprototype"]
    row = relic_cards.playability(new_state, registry, "p1")[0]
    assert row["playable"] is False  # agent wyczerpany
