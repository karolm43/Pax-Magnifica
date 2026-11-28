"""The Yssaril Tribes — every faction component (RULES.md 62.22) and the F_yssaril rulings.

Scenarios through the real API (offers, window uses, ACTIONs, notes): ``test_flows_yssaril.py``.
Statuses without a test: ``tests/rulings_status.json``.

Board (ring 1 + part of ring 2): 000 Mecatol Rex, 101 Yssaril home (15: Retillion, Shalloq), 102
empty (46), 103 empty (47), 104 the rival's home, 105 Lodor (26), 106 Tarmann (22), 201 empty (48).
Edges: 101-102-103-104-105-106 ring around 000; 201 touches 101 and 102.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    action_cards,
    active_effects,
    board_graph,
    card_draw,
    exhaust,
    faction_components,
    hand_limit,
    leaders,
    offers,
    promissory_play,
    rules_hooks,
    status_phase,
    transaction,
    triggers,
    visibility,
)
from src.core.components import ComponentCategory
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import BonusTurn, GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import mentak, nomad, yssaril
from src.core.movement_paths import shortest_legal_path
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.transaction import TransactionSide
from tests.factions.completeness import missing_components
from tests.rulings import ruling

MECATOL, HOME, EMPTY, EMPTY_B, RIVAL, LODOR, TARMANN, FAR = (
    "000", "101", "102", "103", "104", "105", "106", "201",
)
CARDS = ["sabotage1", "sabotage2", "skilled_retreat1", "rise_of_a_messiah1", "plague1"]


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


def _cards(registry: StaticDataRegistry, count: int, skip: int = 0) -> list[str]:
    """Real action card ids from the data (distinct copies)."""
    ids = sorted(registry.catalog.all(ComponentCategory.ACTION_CARD))
    return ids[skip:skip + count]


def _state(registry: StaticDataRegistry, other: str = "mentak", third: str | None = None
           ) -> GameState:
    """p1 = the Yssaril (active), p2 = ``other`` at 104 (+ optional p3 without a home)."""
    rival = registry.factions[other]
    p1 = PlayerState(player_id="p1", color="green", faction="yssaril", home_position=HOME,
                     controlled_planets=["retillion", "shalloq"])
    p2 = PlayerState(player_id="p2", color="red", faction=other, home_position=RIVAL,
                     controlled_planets=list(rival.home_planets))
    players = {"p1": p1, "p2": p2}
    if third is not None:
        players["p3"] = PlayerState(player_id="p3", color="blue", faction=third)
    systems = {
        MECATOL: SystemState(position=MECATOL, system_id="18"),
        HOME: SystemState(position=HOME, system_id="15",
                          planet_owners={"retillion": "p1", "shalloq": "p1"},
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
    deck = _cards(registry, 30, skip=10)
    state.decks.action_card_deck = deck
    for player in state.players.values():
        player.cc_reinf = 8
        player.tactical_cc = 3
        player.leader_states = {}
        player.commodity_value = registry.factions[player.faction or ""].commodities
    _bind(state, registry)
    return state


def _hand(state: GameState, pid: str) -> list[str]:
    return list(state.players[pid].private.action_cards)


def _give(state: GameState, pid: str, cards: list[str]) -> None:
    state.players[pid].private.action_cards = list(cards)


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


def test_yssaril_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "yssaril") == []


# ================================================================================ Stall Tactics


@ruling("abilities:stall_tactics#1", "F_yssaril/stall-tactics/1")
def test_stall_tactics_odrzuca_karte_bez_okna_sabotage(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    hand = _cards(registry, 3)
    _give(state, "p1", hand)
    _give(state, "p2", _cards(registry, 2, skip=3))  # the rival could play Sabotage
    after = _use(state, registry, "p1", "ability", yssaril.STALL, {"card": hand[1]})
    assert _hand(after, "p1") == [hand[0], hand[2]]
    assert hand[1] in after.decks.action_card_discard
    assert after.held_play is None  # not an action card: nothing can Sabotage it
    assert after.players["p1"].took_action_this_turn


def test_stall_tactics_bez_kart_niedostepne(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    reason = faction_components.block_reason(state, registry, "p1", "ability", yssaril.STALL)
    assert reason == "You have no action cards in your hand."


def test_stall_tactics_auto_pierwsza_karta(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    hand = _cards(registry, 2)
    _give(state, "p1", hand)
    inputs = yssaril.stall_inputs(state, registry, "p1")
    assert "auto" not in inputs[0]
    assert {o["meta"]["ref"]["kind"] for o in inputs[0]["options"]} == {"actionCard"}


# ======================================================================= Blackshade Infiltrator


@ruling("units:yssaril_mech#1")
def test_blackshade_po_stall_tactics_stawia_mecha(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _give(state, "p1", _cards(registry, 1))
    after = _use(state, registry, "p1", "ability", yssaril.STALL,
                 {"card": _hand(state, "p1")[0]})
    offer = _offers(after, "p1", "Blackshade")[0]
    assert not offer.mandatory  # "you may"
    planet = _inputs(after, registry, offer)[0]
    assert "auto" not in planet
    assert {o["value"] for o in planet["options"]} == {"retillion", "shalloq"}
    done = _accept(after, "p1", "Blackshade", {"planet": "shalloq"})
    assert done.systems[HOME].planet_units["shalloq"]["p1"]["mech"] == 1


# ===================================================================================== Scheming


@ruling("abilities:scheming#1", "abilities:scheming#2", "F_yssaril/scheming/1",
        "F_yssaril/scheming/3")
def test_scheming_dobiera_dodatkowa_i_odrzuca_dowolna(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    old = _cards(registry, 1)
    _give(state, "p1", old)
    card_draw.draw_action_cards(state, "p1", 2)
    assert len(_hand(state, "p1")) == 4  # 1 + 2 drawn + 1 Scheming
    offer = _offers(state, "p1", "Scheming")[0]
    assert offer.mandatory
    field = _inputs(state, registry, offer)[0]
    assert "auto" not in field
    # Any card of the hand - also one held before the draw (scheming 3).
    done = triggers.accept_offer(state, "p1", offer.id, {"card": old[0]})
    assert len(_hand(done, "p1")) == 3 and old[0] not in _hand(done, "p1")
    assert old[0] in done.decks.action_card_discard


@ruling("F_yssaril/scheming/2", "R_action_cards/notes/5.2")
def test_scheming_raz_na_dobranie_neural_motivator(registry: StaticDataRegistry) -> None:
    """Status-phase draw with Neural Motivator (2 cards) = ONE draw: 1 extra card only, and the
    Yssaril finishes Scheming before the next player draws."""
    state = _state(registry)
    state.phase = Phase.STATUS
    state.players["p1"].technologies.append("nm")
    drawn = status_phase._draw_action_cards(state, ["p1", "p2"])  # noqa: SLF001
    assert drawn["p1"] == 2
    assert len(_hand(state, "p1")) == 3  # 2 + 1 additional
    assert len(_offers(state, "p1", "Scheming")) == 1


@ruling("C_agendas/minister-of-policy/1.1")
def test_scheming_dwa_osobne_dobrania_minister_of_policy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    card_draw.draw_action_cards(state, "p1", 1)  # Draw Action Cards step
    state = _accept(state, "p1", "Scheming", {"card": _hand(state, "p1")[-1]})
    state.decks.agenda_laws["minister_policy"] = "p1"
    triggers.fire(state, GameEvent.PHASE, Moment.END, subject=None, ctx={"phase": "status"})
    assert len(_offers(state, "p1", "Scheming")) == 1  # Scheming again for Minister of Policy


@ruling("F_yssaril/scheming/4")
def test_scheming_blokuje_odblokowanie_so_ata(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _give(state, "p1", _cards(registry, 6))
    card_draw.draw_action_cards(state, "p1", 1)  # 6 + 1 + 1 = 8 cards, discard pending
    assert len(_hand(state, "p1")) == 8
    assert leaders.refresh_unlocks(state, registry) == []  # nothing resolves before the discard
    state = _accept(state, "p1", "Scheming", {"card": _hand(state, "p1")[-1]})
    assert leaders.refresh_unlocks(state, registry) == [yssaril.COMMANDER]


@ruling("F_yssaril/scheming/5", "F_yssaril/mageon-implants/1",
        "F_yssaril/kyver-blade-and-key-guild-of-spies/2")
def test_scheming_nie_przy_braniu_kart_bez_dobierania(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _give(state, "p2", _cards(registry, 2))
    state.decks.action_card_discard = _cards(registry, 1, skip=40)
    card_draw.take_from_discard(state, "p1", state.decks.action_card_discard[0])  # Codex / RE
    card_draw.transfer_action_card(state, "p2", "p1", _hand(state, "p2")[0])  # Mageon / Kyver
    assert _offers(state, "p1", "Scheming") == []


def test_scheming_nie_dla_innych_graczy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    card_draw.draw_action_cards(state, "p2", 2)
    assert len(_hand(state, "p2")) == 2
    assert triggers.offers_for(state, "p2") == []


# ======================================================================================= Crafty


@ruling("abilities:crafty#1", "abilities:crafty#2", "F_yssaril/crafty/1")
def test_crafty_bez_limitu_takze_executive_sanctions(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _give(state, "p1", _cards(registry, 12))
    _give(state, "p2", _cards(registry, 8, skip=12))
    assert hand_limit.action_card_limit(state, "p1") is None
    assert hand_limit.action_card_excess(state, "p1") == 0
    state.decks.agenda_laws["sanctions"] = "for"  # Executive Sanctions: max 3 cards
    assert hand_limit.action_card_excess(state, "p1") == 0
    assert hand_limit.action_card_excess(state, "p2") == 5
    # Political Secret forbids USING faction abilities; Crafty is never prevented.
    active_effects.add_effect(state, promissory_play.POLITICAL_SECRET_EFFECT, Duration.AGENDA,
                              owner="p1")
    assert hand_limit.action_card_limit(state, "p1") is None


@ruling("F_yssaril/crafty/2")
def test_crafty_nie_chroni_przed_public_execution(registry: StaticDataRegistry) -> None:
    from src.core.hooks import agendas_directives

    state = _state(registry)
    _give(state, "p1", _cards(registry, 9))
    agendas_directives._discard_hand(state, "p1")  # noqa: SLF001 - Public Execution's discard
    assert _hand(state, "p1") == []


# ======================================================================= Transparasteel Plating


def _passed_rival(registry: StaticDataRegistry) -> GameState:
    state = _state(registry)
    state.players["p1"].technologies.append(yssaril.TRANSPARASTEEL)
    state.players["p2"].passed = True
    _give(state, "p2", _cards(registry, 2))
    return state


@ruling("technologies:tp#1")
def test_transparasteel_spasowani_nie_graja_kart(registry: StaticDataRegistry) -> None:
    state = _passed_rival(registry)
    reason = action_cards.forbidden_reason(state, "p2")
    assert reason is not None and "Transparasteel Plating" in reason
    state.players["p2"].passed = False
    assert action_cards.forbidden_reason(state, "p2") is None  # only passed players
    state.players["p2"].passed = True
    state.active_player_id = "p2"  # another player's turn
    assert action_cards.forbidden_reason(state, "p2") is None
    state.active_player_id = "p1"
    state.phase = Phase.AGENDA
    assert action_cards.forbidden_reason(state, "p2") is None  # only in the action phase


@ruling("F_yssaril/transparasteel-plating/1")
def test_transparasteel_tylko_karty_akcji(registry: StaticDataRegistry) -> None:
    state = _passed_rival(registry)
    assert action_cards.forbidden_reason(state, "p2") is not None
    # Faction, leader and technology abilities stay usable: no other point is touched.
    assert rules_hooks.forbidden(rules_hooks.POINT_ACTION_CARDS_FORBIDDEN, state, "p1") == set()
    assert leaders.use_reason(state, registry, "p2", "mentakagent") is None


@ruling("C_action_cards/puppets-on-a-string/2.2")
def test_transparasteel_puppets_to_nie_tura_yssaril(registry: StaticDataRegistry) -> None:
    state = _passed_rival(registry)
    state.players["p1"].passed = True
    state.bonus_turn = BonusTurn(player="p1", not_a_turn=True)  # Puppets on a String
    assert action_cards.forbidden_reason(state, "p2") is None


# ============================================================================= Mageon Implants


@ruling("technologies:mi#1", "technologies:mi#2", "F_yssaril/mageon-implants/2")
def test_mageon_implants_patrzy_i_bierze(registry: StaticDataRegistry) -> None:
    state = _state(registry, third="sol")
    state.players["p1"].technologies.append(yssaril.MAGEON)
    theirs = _cards(registry, 3)
    _give(state, "p2", theirs)
    inputs = yssaril.mageon_inputs(state, registry, "p1")
    assert [o["value"] for o in inputs[0]["options"]] == ["p2"]  # p3 holds no cards
    assert "auto" not in inputs[0]
    work = state.clone()
    yssaril.mageon_implants(work, registry, "p1", {"player": "p2"})
    assert yssaril.MAGEON in work.players["p1"].exhausted_technologies
    offer = _offers(work, "p1", "Mageon")[0]
    assert offer.mandatory
    seen = _inputs(work, registry, offer)[0]
    assert {o["value"] for o in seen["options"]} == set(theirs)
    # Nobody else sees the decision's cards (mi 2): the projection hides its context.
    other_view = visibility.project_strict(work, "p3")
    assert all(o.ctx == {} for o in other_view.pending_offers if o.player_id == "p1")
    done = triggers.accept_offer(work, "p1", offer.id, {"card": theirs[2]})
    assert _hand(done, "p1") == [theirs[2]]
    assert _hand(done, "p2") == theirs[:2]
    assert _offers(done, "p1", "Scheming") == []  # not a draw (mi 1)


# ======================================================================================== Ssruu


def _with_suffi(registry: StaticDataRegistry) -> GameState:
    state = _state(registry, "mentak", third="sol")
    state.players["p2"].trade_goods = 4
    return state


@ruling("leaders:yssarilagent#1")
def test_ssruu_ma_teksty_cudzych_agentow(registry: StaticDataRegistry) -> None:
    state = _state(registry, "nomad", third="sol")
    proxies = rules_hooks.leader_proxies(state, "p1")
    assert proxies == {lid: yssaril.AGENT for lid in (
        "nomadagentmercer", "nomadagentthundarian", "nomadagentartuno", "solagent")}
    owned = rules_hooks.owned_sources(state, "p1")
    assert rules_hooks.HookSource(rules_hooks.SOURCE_LEADER, "solagent") in owned
    assert rules_hooks.leader_proxies(state, "p2") == {}  # only the Yssaril
    # Even if that agent is exhausted: the copy reads Ssruu's state.
    exhaust.exhaust_leader(state, "p3", "solagent")
    assert leaders.is_ready(state, registry, "p1", "solagent")
    leaders.exhaust(state, "p1", "solagent")
    assert state.players["p1"].leader_states[yssaril.AGENT] == leaders.EXHAUSTED
    assert "solagent" not in state.players["p1"].leader_states
    assert not leaders.is_ready(state, registry, "p1", "nomadagentmercer")  # Ssruu is spent
    exhaust.ready_leader(state, "p1", "solagent")
    assert leaders.is_ready(state, registry, "p1", yssaril.AGENT)


def test_ssruu_purge_wylacza_kopie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states[yssaril.AGENT] = leaders.PURGED
    assert rules_hooks.leader_proxies(state, "p1") == {}


@ruling("F_yssaril/ssruu/4")
def test_ssruu_kopiuje_suffi_an(registry: StaticDataRegistry) -> None:
    """The Mentak's Pillage against p3: the Yssaril copying Suffi An and p3 draw, not the
    Mentak."""
    state = _with_suffi(registry)
    state.players["p2"].leader_states[mentak.AGENT] = leaders.EXHAUSTED
    faction_components.ability_used(state, "p2", mentak.PILLAGE, "p3")
    assert _offers(state, "p2", "Suffi An") == []  # the Mentak's own agent is exhausted
    state = _accept(state, "p1", "Suffi An")
    assert len(_hand(state, "p3")) == 1
    assert len(_hand(state, "p2")) == 0
    assert len(_hand(state, "p1")) == 2  # 1 + Scheming (discard pending)
    assert state.players["p1"].leader_states[yssaril.AGENT] == leaders.EXHAUSTED
    assert state.players["p2"].leader_states[mentak.AGENT] == leaders.EXHAUSTED


def test_ssruu_kopia_ogloszona_jako_ssruu_tcs(registry: StaticDataRegistry) -> None:
    """A copy "becomes exhausted" as Ssruu: Temporal Command Suite readies Ssruu."""
    state = _state(registry, "nomad")
    state.players["p2"].technologies.append(nomad.TCS)
    state.players["p3"] = PlayerState(player_id="p3", color="blue", faction="sol")
    state.seating_order = ["p1", "p2", "p3"]
    faction_components.pay_cost(state, registry, "p1", "leader", "solagent")
    assert state.players["p1"].leader_states[yssaril.AGENT] == leaders.EXHAUSTED
    state = _accept(state, "p2", "Temporal Command Suite")
    assert leaders.is_ready(state, registry, "p1", yssaril.AGENT)


@ruling("F_yssaril/ssruu/6")
def test_ssruu_thundarian_nie_od_razu_ponownie(registry: StaticDataRegistry) -> None:
    """After a rewind the combat is back at Roll Dice: no window until dice are rolled again."""
    from src.core import battle
    from src.core.game_state import ActiveCombat, CombatStep

    state = _state(registry, "nomad")
    state.active_combat = ActiveCombat(position=HOME, kind="space", attacker="p2", defender="p1",
                                       step=CombatStep.ROLL)
    assert battle.roll_step_open(state) is False
    reason = faction_components.block_reason(state, registry, "p1", "leader",
                                             nomad.THUNDARIAN)
    assert reason is None  # the copy is owned; the window itself decides
    assert faction_components._WINDOW_USES[  # noqa: SLF001
        faction_components.effect_key("leader", nomad.THUNDARIAN)
    ](state, registry, "p1") is not None


@ruling("F_yssaril/ssruu/1")
def test_ssruu_dwie_dodatkowe_kosci_z_kopia(registry: StaticDataRegistry) -> None:
    """Evelyn DeLouis used by the Sol AND copied by the Yssaril on the same ground force: that
    unit rolls two additional dice."""
    from src.core.hooks.factions import sol

    state = _state(registry, "sol")
    planet = registry.factions["sol"].home_planets[0]
    state.systems[RIVAL].planet_units = {planet: {"p2": {"infantry": 2}, "p1": {"infantry": 1}}}
    ctx = {"kind": "ground", "position": RIVAL, "planet": planet,
           "params": {"unit": "p2|infantry"}}
    sol.evelyn_delouis(state, "p2", ctx)
    sol.evelyn_delouis(state, "p1", ctx)  # the copy: exhausts Ssruu
    assert state.players["p1"].leader_states[yssaril.AGENT] == leaders.EXHAUSTED
    extra = rules_hooks.modify(rules_hooks.POINT_COMBAT_BONUS_DICE, state, "p2", 0,
                               {"kind": "ground", "base_type": "infantry"})
    assert extra == 2


# ======================================================================================== So Ata


@ruling("leaders:yssarilcommander#unlock")
def test_so_ata_odblokowanie_7_kart(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _give(state, "p1", _cards(registry, 6))
    assert leaders.refresh_unlocks(state, registry) == []
    _give(state, "p1", _cards(registry, 7))
    assert leaders.refresh_unlocks(state, registry) == [yssaril.COMMANDER]


@ruling("leaders:yssarilcommander#1")
def test_so_ata_patrzy_po_aktywacji(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states[yssaril.COMMANDER] = leaders.UNLOCKED
    theirs = _cards(registry, 2)
    _give(state, "p2", theirs)
    state.players["p2"].private.secret_objectives = ["mine_rare_metals"]
    state.systems[EMPTY].space_units["p1"] = {"destroyer": 1}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": EMPTY})
    offer = _offers(state, "p1", "So Ata")[0]
    hand = _inputs(state, registry, offer)[0]
    assert "auto" not in hand
    assert {o["value"] for o in hand["options"]} == {"action_cards", "secret_objectives"}
    state = triggers.accept_offer(state, "p1", offer.id, {"hand": "action_cards"})
    look = _offers(state, "p1", "So Ata")[0]
    assert look.mandatory
    seen, done = _inputs(state, registry, look)
    assert seen["kind"] == "info" and {o["value"] for o in seen["options"]} == set(theirs)
    assert "auto" not in done
    state = triggers.accept_offer(state, "p1", look.id, {"done": "done"})
    assert _hand(state, "p2") == theirs  # looking changes nothing
    assert any("looks at" in n["detail"] for n in state.ability_notes)


def test_so_ata_nie_bez_jednostek_ani_wlasnej_aktywacji(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states[yssaril.COMMANDER] = leaders.UNLOCKED
    _give(state, "p2", _cards(registry, 2))
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": EMPTY})
    assert _offers(state, "p1", "So Ata") == []  # no Yssaril units there
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": HOME})
    assert _offers(state, "p1", "So Ata") == []  # "another player"


# ============================================================================== Kyver (hero)


@ruling("leaders:yssarilhero#unlock")
def test_kyver_odblokowanie_3_cele(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].scored_secrets = [
        "mine_rare_metals", "become_a_martyr", "fight_with_precision",
    ]
    assert yssaril.HERO in leaders.refresh_unlocks(state, registry)


@ruling("leaders:yssarilhero#1", "leaders:yssarilhero#2", "leaders:yssarilhero#3",
        "F_yssaril/kyver-blade-and-key-guild-of-spies/1")
def test_kyver_kazdy_pokazuje_bierze_albo_3_losowe(registry: StaticDataRegistry) -> None:
    state = _state(registry, third="sol")
    state.players["p1"].leader_states[yssaril.HERO] = leaders.UNLOCKED
    p2_cards, p3_cards = _cards(registry, 2), _cards(registry, 4, skip=2)
    _give(state, "p2", p2_cards)
    _give(state, "p3", p3_cards)
    state = _use(state, registry, "p1", "leader", yssaril.HERO)
    assert state.players["p1"].leader_states[yssaril.HERO] == leaders.PURGED
    effect = next(e for e in state.active_effects if e.key == yssaril.KYVER)
    assert set(effect.data["areas"]) == {RIVAL}  # every other player's home (p3 has none)
    # Each other player chooses the card they show (kyver 1).
    show = _offers(state, "p2", "show 1 action card")[0]
    assert show.mandatory and "auto" not in _inputs(state, registry, show)[0]
    state = triggers.accept_offer(state, "p2", show.id, {"card": p2_cards[1]})
    choose = _offers(state, "p1", "take the card")[0]
    shown, pick = _inputs(state, registry, choose)
    assert [o["value"] for o in shown["options"]] == [p2_cards[1]] and "auto" not in pick
    state = triggers.accept_offer(state, "p1", choose.id, {"choice": "take"})
    assert p2_cards[1] in _hand(state, "p1") and _hand(state, "p2") == [p2_cards[0]]
    show = _offers(state, "p3", "show 1 action card")[0]
    state = triggers.accept_offer(state, "p3", show.id, {"card": p3_cards[0]})
    choose = _offers(state, "p1", "take the card")[0]
    state = triggers.accept_offer(state, "p1", choose.id, {"choice": "discard"})
    assert len(_hand(state, "p3")) == 1  # 4 - 3 random
    assert _offers(state, "p1", "Scheming") == []  # taking is not drawing (kyver 2)


# ===================================================================================== Spy Net


def _spy_net(registry: StaticDataRegistry) -> tuple[GameState, str]:
    from src.core.game_state import TurnEndWindow

    state = _state(registry)
    note = yssaril.SPY_NET
    assert registry.catalog.get(ComponentCategory.PROMISSORY_NOTE, note) is not None
    state.players["p2"].private.promissory_notes = [note]
    _give(state, "p1", _cards(registry, 3))
    state.active_player_id = "p2"
    state.turn_end_window = TurnEndWindow(ended_player="p1", next_player="p2")
    return state, note


@ruling("promissory_notes:spynet#1", "promissory_notes:spynet#2", "promissory_notes:spynet#3",
        "F_yssaril/spy-net/1")
def test_spy_net_na_poczatku_tury(registry: StaticDataRegistry) -> None:
    state, note = _spy_net(registry)
    mine = _hand(state, "p1")
    state, _ = promissory_play.play(state, registry, "p2", note)
    assert note in state.players["p1"].private.promissory_notes  # returned to the Yssaril
    pick = _offers(state, "p2", "Spy Net")[0]
    assert pick.mandatory
    assert {o["value"] for o in _inputs(state, registry, pick)[0]["options"]} == set(mine)
    state = triggers.accept_offer(state, "p2", pick.id, {"card": mine[1]})
    assert _hand(state, "p2") == [mine[1]]
    assert _hand(state, "p1") == [mine[0], mine[2]]


@ruling("F_yssaril/spy-net/2", "F_yssaril/spy-net/3")
def test_spy_net_raz_w_oknie_i_tylko_na_swoja_ture(registry: StaticDataRegistry) -> None:
    state, note = _spy_net(registry)
    state, _ = promissory_play.play(state, registry, "p2", note)
    state = _accept(state, "p2", "Spy Net", {"card": _hand(state, "p1")[0]})
    # Received again in the same window: it cannot be played again (spy-net 3).
    state.players["p1"].private.promissory_notes.remove(note)
    state.players["p2"].private.promissory_notes.append(note)
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows[note]["reason"] == "Spy Net was already played in this timing window."
    # Not at the start of another player's turn.
    other, note = _spy_net(registry)
    other.turn_end_window.next_player = "p1"  # type: ignore[union-attr]
    rows = {r["note_id"]: r for r in promissory_play.playability(other, registry, "p2")}
    assert not rows[note]["playable"]


# ============================================================================== Y'sia Y'ssrila


def _path(state: GameState, grid: HexGrid, start: str, goal: str, base_type: str
          ) -> list[str] | None:
    return shortest_legal_path(grid, state, start, goal, "p1", can_enter_asteroids=False,
                               base_type=base_type)


@ruling("units:yssaril_flagship#1", "F_yssaril/ysia-yssrila/1")
def test_ysia_przechodzi_przez_cudze_statki(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[EMPTY].space_units["p2"] = {"destroyer": 1}
    state.systems[MECATOL].space_units["p2"] = {"destroyer": 1}
    grid = _bind(state, registry)
    path = _path(state, grid, HOME, EMPTY_B, "flagship")
    assert path is not None and len(path) == 3
    carrier = _path(state, grid, HOME, EMPTY_B, "carrier")
    assert carrier is not None and len(carrier) > 3  # other ships must go around
    state.players["p1"].technologies.append("lwd")  # Light/Wave Deflector: no extra effect
    assert _path(state, grid, HOME, EMPTY_B, "flagship") == path


@ruling("F_yssaril/ysia-yssrila/2")
def test_ysia_zablokowany_przez_aerie_hololattice(registry: StaticDataRegistry) -> None:
    state = _state(registry, "argent")
    for position, planet in ((MECATOL, "mr"), (TARMANN, "tarmann")):
        state.systems[position].space_units["p2"] = {"destroyer": 1}
        state.systems[position].planet_units = {planet: {"p2": {"pds": 1}}}
    grid = _bind(state, registry)
    direct = _path(state, grid, HOME, LODOR, "flagship")
    assert direct is not None and len(direct) == 3  # through the Argent's ships
    state.players["p2"].technologies.append("ah")  # structures block every ship's passage
    around = _path(state, grid, HOME, LODOR, "flagship")
    assert around is not None and len(around) > 3 and MECATOL not in around[1:-1]
    assert TARMANN not in around[1:-1]


# ======================================================================== Deepgloom Executable


@ruling("breakthroughs:yssarilbt#1", "breakthroughs:yssarilbt#2", "breakthroughs:yssarilbt#3",
        "F_yssaril/deepgloom-executable/1", "F_yssaril/deepgloom-executable/2",
        "F_yssaril/deepgloom-executable/3")
def test_deepgloom_scheming_dla_innego_z_transakcja(registry: StaticDataRegistry) -> None:
    state = _state(registry, third="sol")
    state.players["p1"].breakthrough_unlocked = True
    state.active_player_id = "p3"  # neither of the pair is the active player
    card_draw.draw_action_cards(state, "p2", 1)
    state = _accept(state, "p1", "Deepgloom Executable")
    use = _offers(state, "p2", "Scheming (Deepgloom")[0]
    assert "auto" not in _inputs(state, registry, use)[0]
    state = triggers.accept_offer(state, "p2", use.id, {"use": "use"})
    assert len(_hand(state, "p2")) == 2
    state = _accept(state, "p2", "Scheming: discard", {"card": _hand(state, "p2")[-1]})
    assert len(_hand(state, "p2")) == 1
    assert transaction.granted_pair(state, "p1", "p2")
    # The grant: no neighbours, the active player need not be either of them.
    state.players["p1"].trade_goods = 2
    grid = _bind(state, registry)
    after = transaction.resolve_transaction(
        state, grid, "p2", TransactionSide(trade_goods=1), TransactionSide(), player_id="p1")
    assert after.players["p2"].trade_goods == 1
    assert "p2" not in after.players["p1"].transacted_with  # not counted against the limit


def test_deepgloom_scheming_odmowa(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    card_draw.draw_action_cards(state, "p2", 1)
    state = _accept(state, "p1", "Deepgloom Executable")
    state = _accept(state, "p2", "Scheming (Deepgloom", {"use": "decline"})
    assert len(_hand(state, "p2")) == 1
    assert not transaction.granted_pair(state, "p1", "p2")


def test_deepgloom_pozycza_stall_tactics(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    inputs = yssaril.deepgloom_inputs(state, registry, "p1")
    assert "auto" not in inputs[0]
    state = _use(state, registry, "p1", "breakthrough", yssaril.BREAKTHROUGH, {"player": "p2"})
    assert faction_components.granted_abilities(state, "p2") == [yssaril.STALL]
    assert ("ability", yssaril.STALL) in faction_components.owned(state, registry, "p2")
    card = _cards(registry, 1)
    _give(state, "p2", card)
    state.active_player_id = "p2"
    state = _use(state, registry, "p2", "ability", yssaril.STALL, {"card": card[0]})
    assert _hand(state, "p2") == []
    assert faction_components.granted_abilities(state, "p2") == []  # used up
    assert transaction.granted_pair(state, "p1", "p2")
    assert _offers(state, "p1", "Blackshade") == []  # not the Yssaril's own use
