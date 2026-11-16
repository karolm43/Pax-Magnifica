"""The Xxcha Kingdom — rulingi ``docs/rules_tirules/F_xxcha.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Testy komponentów bez rulingów są w ``test_xxcha.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    action_cards,
    agenda_phase,
    capacity,
    card_hold,
    faction_components,
    invasion,
    leaders,
    objective_payment,
    objective_progress,
    payment,
    production,
    promissory_play,
    rules_hooks,
    space_cannon,
    triggers,
    turn_flow,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    AgendaStep,
    GameState,
    InvasionPhase,
    InvasionState,
    PendingOffer,
    SystemState,
)
from src.core.hooks import action_cards as ac_hooks
from src.core.hooks import action_cards_economy, technologies_actions
from src.core.hooks.factions import xxcha
from src.core.planet_stats import influence_of, resources_of
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from tests.factions.test_xxcha import _activation, _agenda_state, _hold_state, _planet, _state
from tests.rulings import ruling
from tests.test_space_cannon import _fire_until_hit, _grid, _open
from tests.test_space_cannon import _state as _cannon_state

NOW = 1000.0


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _playable(rows: list[dict[str, Any]], key: str, value: str) -> bool:
    return any(r.get(key) == value and r["playable"] for r in rows)


def _planets_where(registry: StaticDataRegistry, test: Any, count: int) -> list[str]:
    found = [pid for pid, p in sorted(registry.planets.items()) if test(p)]
    assert len(found) >= count
    return found[:count]


def _own(state: GameState, planets: list[str], owner: str = "p1") -> None:
    """Planety w osobnych systemach-atrapach (bez sąsiedztwa z resztą mapy)."""
    for i, planet in enumerate(planets):
        state.systems[f"9{i}"] = SystemState(
            position=f"9{i}", system_id="18", planet_owners={planet: owner}
        )
        state.players[owner].controlled_planets.append(planet)


# =============================================================================== Peace Accords


@ruling("F_xxcha/peace-accords/1", "abilities:peace_accords#1")
def test_peace_accords_planeta_w_tym_samym_systemie(registry: StaticDataRegistry) -> None:
    """„A planet is adjacent to both the system it is in” - druga planeta systemu też jest celem."""
    state = _state(registry)
    system_id = next(
        sid for sid, d in sorted(registry.systems.items())
        if len(d.planets or []) == 2 and sid.isdigit() and int(sid) < 50
    )
    first, second = registry.systems[system_id].planets
    state.systems["101"] = SystemState(
        position="101", system_id=system_id, planet_owners={first: "p1"}
    )
    assert ("101", second) in xxcha.peace_targets(state, "p1")


# ======================================================================= Quash / Political Favor


@ruling("F_xxcha/quash/1", "F_xxcha/political-favor/1")
def test_quash_favor_secret_i_veto_w_jednym_oknie_przed_riderami(
    registry: StaticDataRegistry,
) -> None:
    """Quash, Political Favor, Political Secret i Veto - to samo okno „when revealed”; zagranie
    ridera („after”) je zamyka."""
    state = _agenda_state(registry)
    state.players["p2"].private.promissory_notes = ["favor", "green_ps"]
    state.players["p2"].private.action_cards = ["veto", "trade_rider"]
    assert xxcha._quash_window(state, registry, "p1") is None
    notes = promissory_play.playability(state, registry, "p2")
    assert _playable(notes, "note_id", "favor") and _playable(notes, "note_id", "green_ps")
    cards = action_cards.playability(state, registry, "p2")
    assert _playable(cards, "card_id", "veto") and _playable(cards, "card_id", "trade_rider")
    after, _ = action_cards.play_action_card(
        state, registry, "p2", "trade_rider", {"outcome": "for"}
    )
    assert xxcha._quash_window(after, registry, "p1") is not None
    assert not _playable(action_cards.playability(after, registry, "p2"), "card_id", "veto")
    assert not _playable(promissory_play.playability(after, registry, "p2"), "note_id", "favor")


@ruling("F_xxcha/quash/1.1", "abilities:quash#1", "abilities:quash#2")
def test_quash_po_political_secret_notka_wraca_bez_efektu(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    state.players["p1"].private.promissory_notes = ["blue_ps"]  # Political Secret gracza p2
    played, _ = promissory_play.play(state, registry, "p1", "blue_ps")
    assert promissory_play.silenced(played, "p2") and "p2" in played.agenda.blocked  # type: ignore[union-attr]
    assert "blue_ps" in played.players["p2"].private.promissory_notes  # „return this card”
    old = played.agenda.agenda_id  # type: ignore[union-attr]
    quashed, _ = faction_components.play(played, registry, "p1", "ability", "quash")
    agenda = quashed.agenda
    assert agenda is not None and agenda.agenda_id != old  # nowa agenda, głosujemy nad nią
    assert agenda.step is AgendaStep.VOTE
    assert old in quashed.decks.agenda_discard
    assert quashed.players["p1"].strategic_cc == 1  # żeton ze strategy pool
    assert not promissory_play.silenced(quashed, "p2") and "p2" not in agenda.blocked


@ruling(
    "F_xxcha/political-favor/1.1", "F_xxcha/political-favor/3",
    "promissory_notes:favor#1", "promissory_notes:favor#2", "promissory_notes:favor#3",
    "promissory_notes:favor#4",
)
def test_political_favor_po_political_secret(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    state.players["p2"].private.promissory_notes = ["favor", "green_ps"]
    state.players["p2"].transacted_with = ["p1"]
    secret, _ = promissory_play.play(state, registry, "p2", "green_ps")
    assert promissory_play.silenced(secret, "p1")
    old = secret.agenda.agenda_id  # type: ignore[union-attr]
    reinforcements = secret.players["p1"].strategic_cc
    favored, _ = promissory_play.play(secret, registry, "p2", "favor")
    agenda = favored.agenda
    assert favored.players["p1"].strategic_cc == reinforcements - 1  # żeton Xxcha do rezerwy
    assert agenda is not None and agenda.agenda_id != old and old in favored.decks.agenda_discard
    assert agenda.step is AgendaStep.VOTE  # głosujemy nad nową agendą
    assert "favor" in favored.players["p1"].private.promissory_notes  # wraca do Xxcha
    assert not promissory_play.silenced(favored, "p1")  # Political Secret bez efektu
    assert favored.players["p2"].transacted_with == []  # nowa agenda = nowa transakcja


# =========================================================================== Instinct Training


@ruling("F_xxcha/instinct-training/2", "technologies:it#1", "technologies:it#2")
def test_instinct_training_druga_kopia_po_anulowaniu(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    state.players["p1"].technologies = ["it"]
    state.players["p2"].private.action_cards = ["veto", "veto3"]
    state.decks.action_card_deck = ["filler"]
    state.decks.action_card_discard = list(card_hold.SABOTAGE_IDS)
    held, _ = action_cards.play_action_card(state, registry, "p2", "veto", {}, now=NOW)
    assert held.held_play is not None and held.held_play.eligible == ["p1"]
    cancelled, _ = faction_components.play(held, registry, "p1", "technology", "it")
    assert cancelled.held_play is None and "veto" in cancelled.decks.action_card_discard
    assert cancelled.agenda.agenda_id == state.agenda.agenda_id  # type: ignore[union-attr]
    again, _ = action_cards.play_action_card(cancelled, registry, "p2", "veto3", {})
    assert again.agenda.agenda_id != state.agenda.agenda_id  # type: ignore[union-attr]


@ruling(
    "F_xxcha/instinct-training/3", "F_xxcha/instinct-training/4",
    "F_xxcha/instinct-training/4.2",
)
def test_instinct_training_zmienny_koszt_ogloszony_i_niezaplacony(
    registry: StaticDataRegistry,
) -> None:
    """Bribery: liczba TG (zmienny koszt) jest ogłoszona przy zagraniu, a po anulowaniu nic nie
    jest płacone."""
    state = _agenda_state(registry)
    state.players["p1"].technologies = ["it"]
    state.players["p2"].trade_goods = 5
    state.players["p2"].private.action_cards = ["bribery"]
    state.decks.action_card_deck = ["filler"]
    state.decks.action_card_discard = list(card_hold.SABOTAGE_IDS)
    rich = _planets_where(registry, lambda p: (p.influence or 0) >= 1, 1)
    _own(state, rich, owner="p2")
    state = agenda_phase.abstain(state, registry, "p1")
    state = agenda_phase.cast_vote(state, registry, "p2", "for", rich)
    held, _ = action_cards.play_action_card(
        state, registry, "p2", "bribery", {"trade_goods": 3}, now=NOW
    )
    assert held.held_play is not None and held.held_play.params == {"trade_goods": 3}
    assert held.players["p2"].trade_goods == 5  # nic nie zapłacone przed odpowiedzią
    cancelled, _ = faction_components.play(held, registry, "p1", "technology", "it")
    assert cancelled.players["p2"].trade_goods == 5  # „no costs are paid”
    assert cancelled.agenda.votes["p2"].votes == state.agenda.votes["p2"].votes  # type: ignore[union-attr]


@ruling("F_xxcha/instinct-training/4.1", "F_xxcha/instinct-training/5")
def test_instinct_training_cel_ogloszony_kosci_po_odpowiedzi(registry: StaticDataRegistry) -> None:
    """Plague: planeta-cel jest ogłoszona i sprawdzona przy zagraniu; kości rzuca się dopiero,
    gdy nikt nie anulował karty."""
    state = _hold_state(registry)
    state.players["p2"].private.action_cards = ["plague"]
    target = _planet(registry, "20")  # planeta Xxcha z piechotą
    state.systems["101"].planet_units = {target: {"p1": {"infantry": 3}}}
    with pytest.raises(ValueError):
        action_cards.play_action_card(state, registry, "p2", "plague", {"planet": "x"}, now=NOW)
    held, _ = action_cards.play_action_card(
        state, registry, "p2", "plague", {"planet": target}, now=NOW
    )
    assert held.held_play is not None and held.held_play.params == {"planet": target}
    assert held.rng_counter == state.rng_counter  # kości jeszcze nie rzucone
    cancelled, _ = faction_components.play(held, registry, "p1", "technology", "it")
    assert cancelled.rng_counter == state.rng_counter
    assert cancelled.systems["101"].planet_units[target]["p1"]["infantry"] == 3
    resolved = card_hold.resolve(held, registry)
    assert resolved.rng_counter > state.rng_counter  # rzut dopiero przy wykonaniu


@ruling("F_xxcha/instinct-training/6")
def test_instinct_training_badana_technologia_ogloszona_pozniej(
    registry: StaticDataRegistry,
) -> None:
    """Divert Funding: przy zagraniu tylko zwracana technologia; badaną wybiera się w oknie
    badania po rozstrzygnięciu karty."""
    state = _hold_state(registry)
    state.players["p2"].private.action_cards = ["divert_funding"]
    state.players["p2"].technologies = ["nm", "st"]
    held, _ = action_cards.play_action_card(
        state, registry, "p2", "divert_funding", {"return_technology": "nm"}, now=NOW
    )
    assert held.held_play is not None and held.held_play.params == {"return_technology": "nm"}
    resolved = card_hold.resolve(held, registry)
    assert any("research_cost" in o.ctx for o in resolved.pending_offers if o.player_id == "p2")
    assert action_cards_economy._DIVERT_RESEARCH == "divert_funding"


@ruling("F_xxcha/instinct-training/7")
def test_instinct_training_rider_tylko_przy_zagraniu(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    state.players["p1"].technologies = ["it"]
    state.players["p2"].private.action_cards = ["trade_rider"]
    state.decks.action_card_deck = ["filler"]
    state.decks.action_card_discard = list(card_hold.SABOTAGE_IDS)
    held, _ = action_cards.play_action_card(
        state, registry, "p2", "trade_rider", {"outcome": "for"}, now=NOW
    )
    assert xxcha._instinct_window(held, registry, "p1") is None  # przy zagraniu - wolno
    resolved = card_hold.resolve(held, registry)
    assert any(e.owner == "p2" for e in resolved.active_effects)  # rider czeka na wynik
    assert xxcha._instinct_window(resolved, registry, "p1") is not None  # później - nie


@ruling("F_xxcha/instinct-training/8.1")
def test_instinct_training_druga_akcja_fleet_logistics(registry: StaticDataRegistry) -> None:
    """Anulowana karta ACTION jako druga akcja (Fleet Logistics): gracz kończy turę bez drugiej
    akcji i bez pasowania."""
    state = _hold_state(registry)
    p2 = state.players["p2"]
    p2.technologies = ["fl"]
    p2.took_action_this_turn, p2.actions_this_turn = True, 1
    held, _ = action_cards.play_action_card(state, registry, "p2", "industrial_initiative",
                                            {}, now=NOW)
    assert held.players["p2"].actions_this_turn == 2
    cancelled, _ = faction_components.play(held, registry, "p1", "technology", "it")
    assert cancelled.players["p2"].actions_this_turn == 1
    ended = turn_flow.end_turn(cancelled, "p2", registry=registry)
    assert ended.active_player_id == "p1" and not ended.players["p2"].passed


# ========================================================================= Nullification Field


@ruling(
    "F_xxcha/nullification-field/1", "F_xxcha/nullification-field/1.1",
    "F_xxcha/nullification-field/2", "technologies:nf#1", "technologies:nf#2",
)
def test_nullification_field_kasuje_after_aktywacji_i_zostawia_koniec_tury(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _activation(registry)
    state.players["p2"].took_action_this_turn = True
    activated = (GameEvent.SYSTEM_ACTIVATED.value, Moment.AFTER.value)
    state.pending_offers = [
        PendingOffer(id=f"o{pid}", player_id=pid, event=activated[0], moment=activated[1],
                     hook_seq=0)
        for pid in ("p2", "p1")  # aktywny i sam Xxcha
    ]
    fired: list[tuple[GameEvent, Moment, str | None]] = []
    original = triggers.fire

    def spy(st: GameState, event: GameEvent, moment: Moment, **kw: Any) -> Any:
        fired.append((event, moment, kw.get("subject")))
        return original(st, event, moment, **kw)

    monkeypatch.setattr(triggers, "fire", spy)
    xxcha.nullification_field(state, "p1", {"player": "p2", "position": "102"})
    assert state.pending_offers == []  # nikt nie użyje „after … activates a system”
    assert (GameEvent.TURN, Moment.END, "p2") in fired  # „at the end of your turn” działa
    assert state.active_player_id == "p1"  # tura p2 skończona natychmiast


# ======================================================= Loncara Ssodu / Indomitus (Space Cannon)


@ruling("F_xxcha/loncara-ssodu/1")
def test_flagowiec_zniszczony_przez_aktywnego_nie_strzela(registry: StaticDataRegistry) -> None:
    state = _cannon_state(
        active="p2", seating=("p1", "p2"), pds={"p2": 12},
        ships={"p1": {"flagship": 1}, "p2": {"cruiser": 1}},
    )
    state.players["p1"].faction = "xxcha"
    assert space_cannon.offense_queue(state, _grid(), registry) == ["p2", "p1"]  # aktywny 1.
    fired = _fire_until_hit(_open(state, registry), registry, "p2", "p1")
    after = space_cannon.assign_hits(
        fired, "p1", sustain={"flagship": 1}, destroy_damaged={"flagship": 1}, registry=registry
    )
    assert not after.systems["000"].space_units.get("p1", {}).get("flagship")
    assert not space_cannon.offense_shooters(after, _grid(), registry, "p1")


@ruling("F_xxcha/indomitus/1", "units:xxcha_mech#1")
def test_mech_usuniety_przez_pojemnosc_nie_strzela(registry: StaticDataRegistry) -> None:
    """Statki Xxcha zestrzelone przez Space Cannon aktywnego: nadwyżkę usuwa się NATYCHMIAST
    (okno CAPACITY zawiesza Space Cannon), a usunięty mech nie strzela."""
    state = _cannon_state(
        active="p2", seating=("p1", "p2"), pds={"p2": 12},
        ships={"p1": {"carrier": 1, "mech": 1}, "p2": {"cruiser": 1}},
    )
    state.players["p1"].faction = "xxcha"
    fired = _fire_until_hit(_open(state, registry), registry, "p2", "p1")
    after = space_cannon.assign_hits(fired, "p1", {"carrier": 1}, registry=registry)
    assert after.pending_window is not None
    assert after.pending_window.window_type.value == "CAPACITY"
    assert after.suspended_window is not None  # Space Cannon czeka
    with pytest.raises(ValueError):
        space_cannon.fire_offense(after, _grid(), registry, "p1", "p2")
    cleared = capacity.resolve_capacity(after, registry, "p1", {"mech": 1})
    assert cleared.pending_window is not None
    assert cleared.pending_window.current_responder == "p1"
    assert not space_cannon.offense_shooters(cleared, _grid(), registry, "p1")


@ruling("F_xxcha/indomitus/2")
def test_space_cannon_defense_tylko_nieaktywni(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    planet = _planet(registry, "21")
    state.systems["102"].planet_owners = {planet: "p2"}
    state.systems["102"].planet_units = {planet: {"p1": {"mech": 2}, "p2": {"pds": 1}}}
    state.active_system = "102"
    state.invasion = InvasionState(
        position="102", attacker="p1", phase=InvasionPhase.SPACE_CANNON_DEFENSE,
        committed={planet: {"mech": 2}},
    )
    owners = {s.player_id for s in invasion.defense_shooters(state, registry, planet)}
    assert owners == {"p2"}  # mechy Xxcha (aktywnego) nie strzelają w obronie


# ===================================================================== Elder Qanoj (commander)


def _commander(state: GameState) -> GameState:
    state.players["p1"].leader_states = {"xxchacommander": "unlocked"}
    return state


@ruling("F_xxcha/elder-qanoj/2")
def test_elder_qanoj_rider_i_glos(registry: StaticDataRegistry) -> None:
    state = _commander(_agenda_state(registry))
    state.players["p1"].private.action_cards = ["trade_rider"]
    after, _ = action_cards.play_action_card(
        state, registry, "p1", "trade_rider", {"outcome": "for"}
    )
    assert "p1" not in after.agenda.blocked  # type: ignore[union-attr]
    assert agenda_phase.current_voter(after) == "p1"


@ruling("F_xxcha/elder-qanoj/3")
def test_elder_qanoj_political_secret_blokuje_karty_i_quash_nie_glos(
    registry: StaticDataRegistry,
) -> None:
    state = _commander(_agenda_state(registry))
    state.players["p1"].private.action_cards = ["veto"]
    state.players["p2"].private.promissory_notes = ["green_ps"]
    secret, _ = promissory_play.play(state, registry, "p2", "green_ps")
    rows = action_cards.playability(secret, registry, "p1")
    assert all("Political Secret" in (r["reason"] or "") for r in rows)
    reason = faction_components.block_reason(secret, registry, "p1", "ability", "quash")
    assert reason is not None and "Political Secret" in reason
    assert "p1" not in secret.agenda.blocked  # type: ignore[union-attr]
    assert agenda_phase.current_voter(secret) == "p1"


@ruling("F_xxcha/elder-qanoj/5")
def test_elder_qanoj_representative_government_jeden_glos(registry: StaticDataRegistry) -> None:
    state = _commander(_agenda_state(registry))
    state.decks.agenda_laws = {"rep_govt": "for"}
    mine = _planet(registry, "20")
    with pytest.raises(ValueError, match="Representative Government"):
        agenda_phase.cast_vote(state, registry, "p1", "for", [mine])
    voted = agenda_phase.cast_vote(state, registry, "p1", "for", [])
    assert voted.agenda.votes["p1"].votes == 1  # type: ignore[union-attr]


# ============================================================================ Xxekir Grom (hero)


@ruling("leaders:xxchahero-te#unlock")
def test_xxekir_grom_odblokowanie_trzy_cele(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    unlock = leaders.unlock_predicate(registry, "xxchahero-te")
    assert unlock is not None
    state.players["p1"].scored_secrets = ["a", "b"]
    assert not unlock(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert unlock(state, registry, "p1")


# ======================================================================= Archon's Gift (BT)


def _gift(state: GameState) -> GameState:
    state.players["p1"].breakthrough_unlocked = True
    return state


@ruling("F_xxcha/archons-gift/1", "F_xxcha/archons-gift/1.1")
def test_archons_gift_archon_tau_daje_jedno(registry: StaticDataRegistry) -> None:
    state = _gift(_state(registry))
    _own(state, ["archontau"])
    kinds: tuple[payment.Kind, ...] = ("resources", "influence")
    for kind in kinds:
        assert payment.ready_planet_values(state, registry, "p1", kind)["archontau"] == 1


def _amass_state(registry: StaticDataRegistry) -> GameState:
    """Same planety „wpływowe” (0 zasobów) + 3 TG: Amass Wealth tylko z Archon's Gift."""
    state = _state(registry)
    state.systems["101"].planet_owners = {}
    state.players["p1"].controlled_planets = []
    rich = _planets_where(
        registry, lambda p: (p.resources or 0) == 0 and (p.influence or 0) >= 3, 2
    )
    _own(state, rich)
    state.players["p1"].trade_goods = 3
    return state


@ruling("F_xxcha/archons-gift/2", "F_xxcha/archons-gift/2.1", "F_xxcha/archons-gift/3")
def test_archons_gift_amass_wealth_planeta_na_jedno(registry: StaticDataRegistry) -> None:
    state = _amass_state(registry)
    grid = grid_from_state(state, registry)
    assert not objective_progress.evaluate(state, registry, grid, "p1", "amass_wealth")[2]
    _gift(state)
    assert objective_progress.evaluate(state, registry, grid, "p1", "amass_wealth")[2]
    plan = objective_payment.auto_payment(state, registry, grid, "p1", "amass_wealth")
    assert len(plan.resource_planets) == 1 and len(plan.influence_planets) == 1
    both = objective_payment.ObjectivePayment(
        resource_planets=plan.resource_planets, influence_planets=plan.resource_planets,
        trade_goods=3,
    )
    with pytest.raises(ValueError, match="both"):
        objective_payment.pay_for_objective(state, registry, grid, "p1", "amass_wealth", both)
    paid = objective_payment.pay_for_objective(state, registry, grid, "p1", "amass_wealth", plan)
    assert paid.players["p1"].trade_goods == 0


@ruling("F_xxcha/archons-gift/3", "F_xxcha/archons-gift/3.1")
def test_archons_gift_nie_zmienia_production_doku(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    mine = _planet(registry, "20")
    state.systems["101"].planet_units = {mine: {"p1": {"spacedock": 1}}}
    state.active_system = "101"
    grid = grid_from_state(state, registry)
    plain = production.production_limit(state, grid, registry, "p1")
    assert plain == resources_of(state, registry, mine) + 2
    assert production.production_limit(_gift(state), grid, registry, "p1") == plain


@ruling("F_xxcha/archons-gift/3.2")
def test_archons_gift_nie_zmienia_integrated_economy(registry: StaticDataRegistry) -> None:
    state = _gift(_state(registry))
    planet = _planets_where(
        registry, lambda p: (p.influence or 0) > (p.resources or 0) > 0, 1
    )[0]
    _own(state, [planet])
    technologies_actions.integrated_economy(state, "p1", {"planet": planet, "position": "90"})
    assert state.production_grant is not None
    assert state.production_grant.max_cost == resources_of(state, registry, planet)


@ruling("F_xxcha/archons-gift/3.3", "leaders:xxchacommander#unlock")
def test_archons_gift_nie_odblokowuje_elder_qanoj(registry: StaticDataRegistry) -> None:
    state = _gift(_state(registry))
    state.systems["101"].planet_owners = {}
    state.players["p1"].controlled_planets = []
    _own(state, _planets_where(
        registry, lambda p: (p.resources or 0) >= 4 and (p.influence or 0) <= 1, 4
    ))
    owned = state.players["p1"].controlled_planets
    assert sum(resources_of(state, registry, p) for p in owned) >= 12
    assert not xxcha._commander_unlocked(state, registry, "p1")


@ruling("F_xxcha/archons-gift/3.4")
def test_archons_gift_nie_dotyczy_establish_hegemony_i_hoard(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    grid = grid_from_state(state, registry)
    plain = {
        o: objective_progress.evaluate(state, registry, grid, "p1", o)[0] for o in ("eh", "hrm")
    }
    _gift(state)
    for objective, value in plain.items():
        assert objective_progress.evaluate(state, registry, grid, "p1", objective)[0] == value


@ruling("F_xxcha/archons-gift/3.5")
def test_archons_gift_mining_initiative_i_uprising_wg_zasobow(registry: StaticDataRegistry) -> None:
    state = _gift(_state(registry))
    planet = _planets_where(
        registry, lambda p: (p.influence or 0) > (p.resources or 0) > 0 and not p.faction_homeworld,
        1,
    )[0]
    _own(state, [planet])
    before = state.players["p1"].trade_goods
    ac_hooks.mining_initiative(state, registry, "p1", {"planet": planet})
    gained = state.players["p1"].trade_goods - before
    assert gained == resources_of(state, registry, planet) < influence_of(state, registry, planet)
    # Uprising gracza p2 na planecie Xxcha: TG równe zasobom, nie wpływowi.
    other = state.players["p2"]
    before = other.trade_goods
    action_cards_economy.uprising(state, registry, "p2", {"planet": planet})
    assert other.trade_goods - before == resources_of(state, registry, planet)
