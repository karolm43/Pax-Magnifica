"""Agendy — rulingi ``docs/rules_tirules/C_agendas.md`` punkt po punkcie (karty A–I).

Każdy test oznacza ``@ruling(...)`` punkty, które sprawdza (strażnik
``tests/test_ruling_coverage.py``, kontrakt ogólny). Podstawowe testy efektów agend są w
``tests/test_agenda_effects.py``; karty z głosowaniem „w pętli” (Miscount Disclosed, Covert
Legislation, Committee Formation…) - ``test_rulings_agendas_voting.py``; karty J–Z -
``test_rulings_agendas_2.py``. Statusy bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    agenda_phase,
    board_graph,
    command_tokens,
    economy,
    exhaust,
    hand_limit,
    objectives,
    offers,
    rules_hooks,
    secret_objectives,
    strategy_phase,
    technology,
    triggers,
)
from src.core.game_state import AgendaStep, GameState, Phase, SystemState, WindowType
from src.core.hex_grid import HexGrid
from src.core.hooks import agendas_directives, agendas_laws
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_agenda_effects import _planet
from tests.test_agenda_effects import _resolve as _resolve  # reeksport dla innych plików
from tests.test_agenda_effects import _state as _agenda_state
from tests.test_agenda_effects import registry as registry  # noqa: F401 - fixture modułu
from tests.test_reactions_agenda import _play, _playable


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    previous = board_graph._PROVIDER
    yield
    board_graph.bind_grid_provider(previous)


def _state(registry: StaticDataRegistry, deck: list[str], *, cards: int = 0) -> GameState:
    """3 graczy (mówca p2, głosują p3, p1, p2); ``cards`` = karty akcji w ręce p3 (pauza)."""
    state = _agenda_state(registry, deck)
    for pid in state.players:
        state.players[pid].cc_reinf = 8
    if cards:
        state.players["p3"].private.action_cards = ["sabo"] * cards
    return state


def _reveal(state: GameState, registry: StaticDataRegistry) -> GameState:
    return agenda_phase.reveal_agenda(state, registry, "p2")


def _abstain_all(state: GameState, registry: StaticDataRegistry) -> GameState:
    while (voter := agenda_phase.current_voter(state)) is not None:
        state = agenda_phase.abstain(state, registry, voter)
    return state


def _offer(state: GameState, pid: str) -> Any:
    return next(o for o in state.pending_offers if o.player_id == pid)


def _accept(state: GameState, pid: str, params: dict[str, Any] | None = None) -> GameState:
    return triggers.accept_offer(state, pid, _offer(state, pid).id, params or {})


def _inputs(state: GameState, registry: StaticDataRegistry, pid: str) -> list[dict[str, Any]]:
    """Pola formularza oferty gracza (jak widzi je UI)."""
    return list(offers.offer_view(state, registry, _offer(state, pid))["inputs"])


def _extra_planets(registry: StaticDataRegistry, state: GameState, n: int) -> list[str]:
    taken = {p for s in state.systems.values() for p in s.planet_owners}
    return [p for p in sorted(registry.planets) if p not in taken][:n]


def _tech(registry: StaticDataRegistry, state: GameState, prereqs: int, *, unit: bool = False
          ) -> technology.TechnologyDef:  # type: ignore[name-defined]
    """Ogólna technologia z dokładnie ``prereqs`` prerekwizytami (``unit`` = ulepszenie)."""
    return next(
        t for t in sorted(technology.tech_pool(state, registry, "p1").values(), key=lambda t: t.id)
        if sum(technology.prerequisites(t).values()) == prereqs and not t.faction
        and (not t.types) == unit
    )


# ===================================================================== Anti-Intellectual Revolution


def _ship_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry, [])
    state.phase = Phase.ACTION
    state.agenda = None
    state.decks.agenda_laws = {"revolution": "for"}
    return state


@ruling("C_agendas/antiintellectual-revolution/1")
def test_revolution_does_not_touch_a_gained_technology(registry: StaticDataRegistry) -> None:
    state = _ship_state(registry)
    state.systems["101"].space_units = {"p1": {"cruiser": 2}}
    tech = _tech(registry, state, 0)
    technology.grant_technology(state, "p1", tech.id)  # „gain”, nie „research”
    assert tech.id in state.players["p1"].technologies
    assert not state.pending_offers and state.systems["101"].space_units["p1"] == {"cruiser": 2}
    other = next(
        t.id for t in technology.tech_pool(state, registry, "p1").values()
        if not technology.prerequisites(t) and t.id not in state.players["p1"].technologies
    )
    researched = technology.research(state, registry, "p1", other)
    researched = _accept(researched, "p1") if researched.pending_offers else researched
    assert researched.systems["101"].space_units["p1"] == {"cruiser": 1}  # badanie: tak


@ruling("C_agendas/antiintellectual-revolution/3")
def test_revolution_player_without_ships_still_researches(registry: StaticDataRegistry) -> None:
    state = _ship_state(registry)
    state.systems["101"].space_units = {"p1": {"fighter": 3}}  # same myśliwce
    tech = _tech(registry, state, 0)
    out = technology.research(state, registry, "p1", tech.id)
    assert tech.id in out.players["p1"].technologies
    assert out.systems["101"].space_units["p1"] == {"fighter": 3} and not out.pending_offers


@ruling("C_agendas/antiintellectual-revolution/4")
def test_revolution_against_exhausts_only_controlled_planets(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["revolution"])
    state.players["p1"].technologies = ["t1", "t2", "t3"]
    out = _resolve(registry, state, "against")
    out.phase, out.agenda = Phase.STRATEGY, None
    ready, count = agendas_directives._revolution_targets(out, "p1")
    assert ready == [_planet(out, "p1")] and count == 1  # 3 technologie, ale 1 własna planeta
    assert agendas_directives._revolution_inputs(out, registry, "p1", {}) == []
    agendas_directives._revolution_apply(out, "p1", {})
    assert out.players["p1"].exhausted_planets == [_planet(out, "p1")]
    assert not out.players["p2"].exhausted_planets  # cudzych planet nie wyczerpuje


# ================================================================= Archived Secret / Search Warrant


def _three_scored(state: GameState, pid: str) -> None:
    state.players[pid].scored_secrets = ["s1", "s2", "s3"]
    state.decks.secret_objective_deck = ["dtd", "x1", "x2"]


@ruling("C_agendas/archived-secret/1")
def test_archived_secret_fourth_secret_goes_back_to_the_deck(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["secret"])
    _three_scored(state, "p1")
    out = _resolve(registry, state, "p1")
    # Dobrał czwarty i - bez wyboru (jedyna karta w ręce) - od razu wtasował go do talii.
    assert out.players["p1"].private.secret_objectives == []
    assert out.players["p1"].scored_secrets == ["s1", "s2", "s3"]
    assert sorted(out.decks.secret_objective_deck) == ["dtd", "x1", "x2"]  # wtasowany z powrotem


@ruling("C_agendas/archived-secret/2", "C_agendas/search-warrant/3")
@pytest.mark.parametrize("card", ["secret", "warrant"])
def test_drive_the_debate_drawn_by_the_agenda_is_not_scored(
    registry: StaticDataRegistry, card: str
) -> None:
    state = _state(registry, [card])
    state.decks.secret_objective_deck = ["dtd", "x1"]
    out = _resolve(registry, state, "p1")
    assert "dtd" in out.players["p1"].private.secret_objectives
    assert "dtd" not in out.players["p1"].scored_secrets
    assert out.players["p1"].victory_points == 0


@ruling("C_agendas/search-warrant/1")
def test_search_warrant_fourth_secret_goes_back(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["warrant"])
    _three_scored(state, "p1")
    out = _resolve(registry, state, "p1")
    assert out.players["p1"].private.secret_objectives == []  # oba dobrane wróciły
    assert sorted(out.decks.secret_objective_deck) == ["dtd", "x1", "x2"]


@ruling("C_agendas/search-warrant/2")
def test_search_warrant_drawn_secrets_are_public_before_the_return(
    registry: StaticDataRegistry,
) -> None:
    from src.api import web_agenda

    state = _state(registry, ["warrant"])
    state.players["p1"].private.secret_objectives = ["s1", "s2", "s3"]
    state.decks.secret_objective_deck = ["x1", "x2", "x3"]
    out = _resolve(registry, state, "p1")
    # Decyzja o zwrocie czeka, a dobrane karty już są jawne dla wszystkich.
    assert _offer(out, "p1").mandatory
    assert web_agenda.revealed_secrets(out) == {"p1": ["s1", "s2", "s3", "x1", "x2"]}
    # Później dobrany cel (inny efekt) też jest jawny, zanim gracz coś odda.
    out = _accept(out, "p1", {"objectives": ["x1", "x2"]})
    drawn = secret_objectives.draw_to_hand(out, "p1")
    assert web_agenda.revealed_secrets(out)["p1"] == ["s1", "s2", "s3", drawn]


# ======================================================================= Checks and Balances


def _strategy_with_checks(registry: StaticDataRegistry) -> GameState:
    state = _state(registry, [])
    state.phase, state.agenda = Phase.STRATEGY, None
    state.active_player_id = "p2"
    state.decks.agenda_laws = {"checks": "for"}
    return state


@ruling("R_strategy_phase/rules-reference/1.1")
def test_checks_trade_goods_go_to_the_chooser(registry: StaticDataRegistry) -> None:
    state = _strategy_with_checks(registry)
    state.strategy_card_tg = {1: 2}
    out = strategy_phase.pick_strategy_card(state, registry, "p2", 1, recipient="p3")
    assert out.players["p2"].trade_goods == 2 and out.players["p3"].trade_goods == 0
    assert out.players["p3"].strategy_cards == [1]


@ruling("C_agendas/checks-and-balances/4")
def test_public_disgrace_after_checks_choice(registry: StaticDataRegistry) -> None:
    from src.core import hold_rewind
    from src.core.hold_rewind import Snapshot

    before = _strategy_with_checks(registry)
    before.players["p1"].private.action_cards = ["disgrace"]
    after = strategy_phase.pick_strategy_card(before, registry, "p2", 1, recipient="p3")
    chain = [Snapshot(1, "pick", before), Snapshot(2, "after", after)]
    steps, _limit = hold_rewind.candidates(chain, registry, "p1")
    assert steps and steps[0]["cards"][0]["card_id"] == "disgrace"  # po ogłoszeniu odbiorcy
    out, implemented = hold_rewind.play_at(chain, registry, "p1", "disgrace", 1)
    assert implemented
    assert 1 not in out.players["p3"].strategy_cards and 1 not in out.players["p2"].strategy_cards
    assert strategy_phase.next_strategy_picker(out) == "p2"  # wybiera ponownie wybierający
    with pytest.raises(ValueError, match="different strategy card"):
        strategy_phase.pick_strategy_card(out, registry, "p2", 1, recipient="p3")
    out = strategy_phase.pick_strategy_card(out, registry, "p2", 2, recipient="p3")
    assert out.players["p3"].strategy_cards == [2]  # inna karta, ten sam albo inny odbiorca


# ======================================================================= Clandestine Operations


@ruling("C_agendas/clandestine-operations/1")
def test_clandestine_removes_tokens_from_any_pools(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["cladenstine"])
    player = state.players["p1"]
    player.tactical_cc, player.fleet_cc, player.strategic_cc = 1, 1, 1
    out = _resolve(registry, state, "for")
    assert {f["key"] for f in _inputs(out, registry, "p1")} == set(command_tokens.POOLS)
    for other in ("p2", "p3"):  # decyzje w kolejności od mówcy
        out = _accept(out, other, {"tactical": 2, "fleet": 0, "strategic": 0})
    out = _accept(out, "p1", {"tactical": 1, "fleet": 0, "strategic": 1})
    pools = {p: command_tokens.pool_count(out, "p1", p) for p in command_tokens.POOLS}
    assert pools == {"tactical": 0, "fleet": 1, "strategic": 0}


# ======================================================================= Classified Document Leaks


def _classified(registry: StaticDataRegistry, scored: dict[str, list[str]]) -> GameState:
    state = _state(registry, ["classified", "mutiny"])
    for pid, secrets in scored.items():
        state.players[pid].scored_secrets = list(secrets)
    return state


@ruling("C_agendas/classified-document-leaks/1")
def test_classified_single_secret_is_the_only_outcome(registry: StaticDataRegistry) -> None:
    out = _reveal(_classified(registry, {"p1": ["dp"]}), registry)
    assert out.agenda is not None and out.agenda.outcomes == ["dp"]
    with pytest.raises(ValueError):
        agenda_phase.cast_vote(out, registry, "p3", "against", [_planet(out, "p3")])
    out = _abstain_all(out, registry)
    assert out.agenda is not None and out.agenda.step is AgendaStep.TIEBREAK
    assert out.agenda.tied == ["dp"]  # mówca musi wybrać ten cel
    with pytest.raises(ValueError):
        agenda_phase.decide_tie(out, registry, "p2", "x")


@ruling("C_agendas/classified-document-leaks/1.1")
def test_classified_single_secret_riders_still_playable(registry: StaticDataRegistry) -> None:
    state = _classified(registry, {"p1": ["dp"]})
    state.players["p3"].private.action_cards = ["trade_rider"]
    out = _reveal(state, registry)
    assert _playable(out, registry, "p3", "trade_rider")
    out = _play(out, registry, "p3", "trade_rider", outcome="dp")
    out = _abstain_all(out, registry)
    out = agenda_phase.decide_tie(out, registry, "p2", "dp")
    if out.agenda is not None and out.agenda.step is AgendaStep.COUNTED:
        out = agenda_phase.confirm_outcome(out, registry, "p2")
    assert out.players["p3"].trade_goods == 5


@ruling(
    "C_agendas/classified-document-leaks/3",
    "C_agendas/classified-document-leaks/4",
    "C_agendas/classified-document-leaks/2",
)
def test_classified_secret_becomes_public_for_good(registry: StaticDataRegistry) -> None:
    state = _classified(registry, {"p1": ["dp", "s2", "s3"]})
    out = _resolve(registry, state, "dp")
    assert "dp" in out.objectives.revealed  # cel publiczny…
    assert "dp" not in out.players["p1"].scored_secrets  # …a nie tajny
    assert secret_objectives.secret_count(out, "p1") == 2  # nie liczy się do limitu 3
    assert out.objectives.scored["dp"] == ["p1"]  # właściciel ma go już zdobytego…
    with pytest.raises(ValueError, match="already scored"):
        objectives.score_public(out, registry, HexGrid(), "p1", "dp")  # …i drugi raz nie


@ruling("C_agendas/classified-document-leaks/6")
def test_classified_discarded_objective_stays_but_is_not_scorable(
    registry: StaticDataRegistry,
) -> None:
    state = _classified(registry, {"p1": ["dp"]})
    out = _resolve(registry, state, "dp")
    agenda_phase.remove_law(out, "classified")
    assert "dp" not in out.players["p1"].scored_secrets  # nie wraca do gracza
    assert "dp" not in out.decks.secret_objective_deck  # nie jest odrzucony
    assert "dp" in out.objectives.revealed  # zostaje w grze…
    with pytest.raises(ValueError, match="can no longer be scored"):
        objectives.score_public(out, registry, HexGrid(), "p2", "dp")  # …ale nikt go nie zdobędzie


@ruling("C_agendas/miscount-disclosed/3.1", "C_agendas/classified-document-leaks/2")
def test_miscount_on_classified_cannot_reelect_the_public_objective(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["miscount"])
    state.players["p1"].scored_secrets = ["s9"]
    state.players["p3"].scored_secrets = ["dp"]
    state.decks.agenda_laws = {"classified": "s8"}
    state.objectives.revealed = ["s8"]
    out = _resolve(registry, state, "classified")
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert out.agenda is not None and out.agenda.agenda_id == "classified"
    assert "s8" not in out.agenda.outcomes and sorted(out.agenda.outcomes) == ["dp", "s9"]
    assert "s8" in out.objectives.revealed  # wciąż publiczny w trakcie głosowania


@ruling("C_agendas/classified-document-leaks/2.1", "C_agendas/miscount-disclosed/3.1")
def test_miscount_on_classified_without_candidates_discards_and_replaces(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["miscount", "mutiny"])
    state.decks.agenda_laws = {"classified": "s8"}
    state.objectives.revealed = ["s8"]
    out = _resolve(registry, state, "classified")
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert out.agenda is not None and out.agenda.unresolvable
    out = agenda_phase.discard_unresolvable(out, registry, "p2")
    assert "classified" not in out.decks.agenda_laws and "classified" in out.decks.agenda_discard
    out = _reveal(out, registry)  # ujawnia się i głosuje kolejna agenda
    assert out.agenda is not None and out.agenda.agenda_id == "mutiny"
    assert out.agenda.agenda_number == 1


# ======================================================================= Colonial Redistribution


def _redistribution(registry: StaticDataRegistry) -> tuple[GameState, str]:
    state = _state(registry, ["redistribution"])
    planet = _planet(state, "p1")
    state.systems["101"].planet_units = {planet: {"p1": {"infantry": 2}}}
    state.players["p2"].victory_points = 3
    state.players["p3"].victory_points = 3
    return state, planet


@ruling("C_agendas/colonial-redistribution/1")
def test_redistribution_controller_may_choose_themselves(registry: StaticDataRegistry) -> None:
    state, planet = _redistribution(registry)
    out = _resolve(registry, state, planet)
    assert out.systems["101"].planet_units.get(planet, {}).get("p1", {}) == {}
    (field,) = agendas_directives._redistribution_inputs(out, registry, "p1", {})
    assert [o["value"] for o in field["options"]] == ["p1"]  # najmniej VP: on sam
    # Jedyny kandydat wybrany bez pytania; teraz oferta „may place 1 infantry” dla niego.
    assert _offer(out, "p1").label.endswith("place 1 infantry")
    out = _accept(out, "p1")
    assert out.systems["101"].planet_units[planet]["p1"] == {"infantry": 1}
    assert out.systems["101"].planet_owners[planet] == "p1"


@ruling("C_agendas/colonial-redistribution/2")
def test_redistribution_dmz_planet_gets_no_infantry(registry: StaticDataRegistry) -> None:
    state, planet = _redistribution(registry)
    state.planet_attachments = {planet: ["dmz"]}
    out = _resolve(registry, state, planet)
    assert not out.pending_offers  # nikt nie wybiera gracza ani nie stawia piechoty
    assert out.systems["101"].planet_units.get(planet, {}).get("p1", {}).get("infantry", 0) == 0
    assert out.systems["101"].planet_owners[planet] == "p1"  # kontrola bez zmian


# ======================================================================= Compensated Disarmament


def _disarmament(registry: StaticDataRegistry) -> tuple[GameState, str]:
    state = _state(registry, ["disarmament"])
    planet = _planet(state, "p1")
    state.systems["101"].planet_units = {
        planet: {"p1": {"infantry": 2, "mech": 1, "pds": 1, "spacedock": 1}, "p3": {"infantry": 1}}
    }
    return state, planet


@ruling(
    "C_agendas/compensated-disarmament/1",
    "C_agendas/compensated-disarmament/2",
    "C_agendas/compensated-disarmament/4",
)
def test_disarmament_ground_forces_pay_out_together(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, planet = _disarmament(registry)
    gains: list[tuple[str, int]] = []
    real = economy.gain_trade_goods

    def spy(st: GameState, pid: str, amount: int, *, cause: str = "") -> None:
        gains.append((pid, amount))
        real(st, pid, amount, cause=cause)

    monkeypatch.setattr(economy, "gain_trade_goods", spy)
    out = _resolve(registry, state, planet)
    assert gains == [("p1", 4)]  # 2 piechoty + mech + cudza piechota, jednym zyskiem
    assert out.systems["101"].planet_units[planet]["p1"] == {"pds": 1, "spacedock": 1}


@ruling("C_agendas/compensated-disarmament/3")
def test_disarmament_empty_planet_can_be_elected(registry: StaticDataRegistry) -> None:
    out = _reveal(_state(registry, ["disarmament"]), registry)
    assert out.agenda is not None and _planet(out, "p2") in out.agenda.outcomes  # bez jednostek


# ======================================================================= Conventions of War


@ruling("C_agendas/conventions-of-war/1")
def test_conventions_do_not_stop_tactical_bombardment_or_stellar_converter(
    registry: StaticDataRegistry,
) -> None:
    """Tactical Bombardment i Stellar Converter nie używają BOMBARDMENT, więc działają na planecie
    kulturowej. X-89 ΩΩ (codex4, jedyna aktywna wersja) działa wyłącznie przez BOMBARDMENT."""
    from src.core.exploration import planet_traits
    from src.core.hooks import action_cards_economy, relics_actions
    from src.core.planet_stats import is_legendary

    probe = _state(registry, [])
    system_id, cultural = next(
        (sid, p) for sid, d in sorted(registry.systems.items()) for p in d.planets
        if p in registry.planets and "cultural" in planet_traits(registry, p)
        and not is_legendary(probe, registry, p) and sid.isdigit() and int(sid) < 80
    )
    grid = HexGrid()
    grid.place_system("101", system_id)
    grid.place_system("102", "19")
    grid.build_edges()
    board_graph.bind_grid_provider(lambda: grid)
    position, other = "101", "102"
    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.decks.agenda_laws = {"conventions": "for"}
    state.systems[position] = SystemState(
        position=position, system_id=system_id,
        planet_owners={cultural: "p2"}, space_units={"p1": {"dreadnought": 1}},
    )
    state.systems[other] = SystemState(
        position=other, system_id="19", space_units={"p1": {"dreadnought": 1}}
    )
    assert "cultural" in rules_hooks.forbidden(
        rules_hooks.POINT_BOMBARDMENT_FORBIDDEN_TRAITS, state, "p1"
    )
    action_cards_economy.tactical_bombardment(state, registry, "p1", {"position": position})
    assert cultural in state.players["p2"].exhausted_planets
    assert cultural in {p for p, _ in relics_actions._converter_planets(state, registry, "p1")}


# ======================================================================= Economic Equality


@ruling("C_agendas/economic-equality/1")
def test_economic_equality_lets_mentak_pillage_each_neighbor(registry: StaticDataRegistry) -> None:
    grid = HexGrid()
    for position, system_id in (("000", "18"), ("101", "19"), ("102", "20"), ("106", "21")):
        grid.place_system(position, system_id)
    grid.build_edges()
    board_graph.bind_grid_provider(lambda: grid)
    state = _state(registry, ["economic_equality"])
    state.players["p1"].faction = "mentak"
    state.systems = {
        "101": SystemState(position="101", system_id="19", space_units={"p1": {"cruiser": 1}}),
        "102": SystemState(position="102", system_id="20", space_units={"p2": {"cruiser": 1}}),
        "106": SystemState(position="106", system_id="21", space_units={"p3": {"cruiser": 1}}),
    }
    out = _resolve(registry, state, "for")
    pillage = sorted(
        str(o.ctx.get("target") or o.ctx.get("player")) for o in out.pending_offers
        if o.player_id == "p1"
    )
    assert pillage == ["p2", "p3"]  # po 5 TG u każdego sąsiada: Pillage na każdego


# ======================================================================= Executive Sanctions


@ruling("C_agendas/executive-sanctions/1")
def test_executive_sanctions_skip_yssaril(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    state.decks.agenda_laws = {"sanctions": "for"}
    state.players["p1"].faction = "yssaril"
    state.players["p3"].faction = "sol"
    assert hand_limit.action_card_limit(state, "p3") == 3
    assert hand_limit.action_card_limit(state, "p1") != 3


# ======================================================================= Fleet Regulations


@ruling("C_agendas/fleet-regulations/2")
def test_fleet_regulations_letnev_armada_six_ships(registry: StaticDataRegistry) -> None:
    from src.core import fleet_pool

    state = _state(registry, [])
    state.decks.agenda_laws = {"regulations": "for"}
    state.players["p1"].faction = "letnev"
    state.players["p1"].fleet_cc = 4
    state.systems["101"].space_units = {"p1": {"dreadnought": 6}}
    assert command_tokens.pool_count(state, "p1", "fleet") == 4
    report = fleet_pool.fleet_report(state, "101", "p1", registry)
    assert report.pool == 6 and not fleet_pool.players_with_excess(state, "101")  # Armada: +2


# ======================================================================= Galactic Crisis Pact


@ruling("C_agendas/galactic-crisis-pact/2", "R_agenda_phase/notes/7")
def test_crisis_pact_secondary_now_in_speaker_order(registry: StaticDataRegistry) -> None:
    out = _resolve(registry, _state(registry, ["crisis"]), "5")
    assert out.phase is Phase.AGENDA  # w trakcie fazy agendy
    window = out.pending_window
    assert window is not None and window.window_type is WindowType.STRATEGY_SECONDARY
    assert window.queue == ["p2", "p3", "p1"]  # od mówcy


@ruling("C_agendas/galactic-crisis-pact/3", "C_agendas/galactic-crisis-pact/4")
def test_crisis_pact_costs_paid_and_planets_ready_after_phase(registry: StaticDataRegistry) -> None:
    from src.core import strategic_action

    state = _state(registry, ["crisis"])
    out = _resolve(registry, state, "7")  # Technology
    window = out.pending_window
    assert window is not None
    assert window.context["free"] == ""  # bez żetonu, ale koszt zasobów zostaje
    assert "p1" in str(window.context.get(strategic_action.NO_COST_KEY, ""))
    # Planety zapłacone / wyczerpane dla prerekwizytu wracają na końcu fazy agendy.
    out.pending_window = None
    out.players["p1"].exhausted_planets = [_planet(out, "p1")]
    out = agenda_phase.continue_agenda(out, registry, "p2")
    out.agenda.agenda_number = 2  # type: ignore[union-attr]
    out.agenda.step = AgendaStep.RESOLVED  # type: ignore[union-attr]
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert out.players["p1"].exhausted_planets == []


@ruling("C_agendas/galactic-crisis-pact/4.1", "C_agendas/ixthian-artifact/1.3",
        "C_agendas/wormhole-research/4.2")
def test_aida_exhausted_for_agenda_research_stays_exhausted(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    state.agenda.agenda_number = 2  # type: ignore[union-attr]
    state.agenda.step = AgendaStep.RESOLVED  # type: ignore[union-attr]
    state.players["p1"].technologies = [technology.AIDA]
    state.players["p1"].exhausted_technologies = [technology.AIDA]
    state.players["p1"].exhausted_planets = [_planet(state, "p1")]
    out = agenda_phase.continue_agenda(state, registry, "p2")
    assert out.players["p1"].exhausted_planets == []
    assert out.players["p1"].exhausted_technologies == [technology.AIDA]


@ruling("C_agendas/galactic-crisis-pact/5")
def test_crisis_pact_any_strategy_card_is_eligible(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["crisis"])
    state.players["p1"].strategy_cards = [1]  # np. zatrzymana Political Stability
    out = _reveal(state, registry)
    assert out.agenda is not None and "1" in out.agenda.outcomes


# ======================================================================= Homeland Defense Act


@ruling("C_agendas/homeland-defense-act/1")
def test_defense_act_discarded_removes_pds_above_two(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    planet = _planet(state, "p1")
    state.systems["101"].planet_units = {planet: {"p1": {"pds": 4, "infantry": 1}}}
    state.decks.agenda_laws = {"defense_act": "for"}
    agenda_phase.remove_law(state, "defense_act")
    assert state.systems["101"].planet_units[planet]["p1"] == {"pds": 2, "infantry": 1}


# ======================================================================= Imperial Arbiter


def _arbiter_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry, [])
    state.phase, state.agenda = Phase.STRATEGY, None
    state.decks.agenda_laws = {"arbiter": "p1"}
    state.players["p1"].strategy_cards = [3]
    state.players["p2"].strategy_cards = [5]
    state.players["p3"].strategy_cards = [8]
    return state


@ruling("R_strategy_phase/notes/1")
def test_arbiter_swap_leaves_trade_goods_with_the_chooser(registry: StaticDataRegistry) -> None:
    state = _arbiter_state(registry)
    state.players["p2"].trade_goods = 2  # TG z karty 5 wziął p2 przy wyborze
    agendas_laws._arbiter(state, "p1", {"params": {"swap": "3|p2|5"}})
    assert state.players["p1"].strategy_cards == [5] and state.players["p2"].strategy_cards == [3]
    assert state.players["p2"].trade_goods == 2 and state.players["p1"].trade_goods == 0


@ruling("C_agendas/imperial-arbiter/1")
def test_arbiter_owner_picks_which_cards_swap(registry: StaticDataRegistry) -> None:
    state = _arbiter_state(registry)
    state.players["p1"].strategy_cards = [3, 4]  # 3-4 graczy: dwie karty
    (field,) = agendas_laws._arbiter_inputs(state, registry, "p1", {})
    values = {o["value"] for o in field["options"]}
    assert values == {"3|p2|5", "3|p3|8", "4|p2|5", "4|p3|8"}


# ======================================================================= Ixthian Artifact


@ruling("C_agendas/ixthian-artifact/1", "C_agendas/ixthian-artifact/1.1")
def test_artifact_research_needs_prerequisites_first_tech_counts(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, [])
    first = _tech(registry, state, 0)
    color = next(iter(first.types))
    second = next(
        t for t in sorted(technology.tech_pool(state, registry, "p1").values(), key=lambda t: t.id)
        if technology.prerequisites(t) == {color: 1} and not t.faction
    )
    with pytest.raises(ValueError, match="prerequisites"):
        agendas_directives.research_chosen(state, "p1", [second.id])
    agendas_directives.research_chosen(state, "p1", [second.id, first.id])  # dowolna kolejność
    assert {first.id, second.id} <= set(state.players["p1"].technologies)


@ruling("C_agendas/ixthian-artifact/1.2", "C_agendas/wormhole-research/4.1",
        "C_agendas/galactic-crisis-pact/4")
def test_agenda_research_specialty_planet_ignores_a_prerequisite(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, [])
    planet, colors = next(
        (p, d.tech_specialties) for p, d in sorted(registry.planets.items()) if d.tech_specialties
    )
    state.systems["102"] = SystemState(position="102", system_id="2", planet_owners={planet: "p1"})
    color = colors[0].upper()
    tech = next(
        t for t in sorted(technology.tech_pool(state, registry, "p1").values(), key=lambda t: t.id)
        if technology.prerequisites(t) == {color: 1} and not t.faction
    )
    agendas_directives.research_chosen(state, "p1", [tech.id], [planet])
    assert tech.id in state.players["p1"].technologies
    assert planet in state.players["p1"].exhausted_planets
    exhaust.ready_all_planets(state, "p1")  # krok 3 fazy agendy
    assert planet not in state.players["p1"].exhausted_planets


@ruling("C_agendas/ixthian-artifact/2", "C_agendas/ixthian-artifact/3")
def test_artifact_disaster_three_or_fewer_units_all_destroyed(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.api.demo_map import build_demo_grid

    grid = build_demo_grid(registry)
    board_graph.bind_grid_provider(lambda: grid)
    state = _state(registry, ["artifact"])
    state.systems = {
        "000": SystemState(position="000", system_id=grid.system_id_at("000"),
                           space_units={"p3": {"dreadnought": 1}}),
        "101": SystemState(position="101", system_id=grid.system_id_at("101"),
                           space_units={"p1": {"cruiser": 2, "destroyer": 1}}),
        "102": SystemState(position="102", system_id=grid.system_id_at("102"),
                           space_units={"p1": {"cruiser": 3, "carrier": 2}}),
    }
    monkeypatch.setattr(agendas_directives, "_artifact_roll", lambda _s, _p: 1)
    out = _resolve(registry, state, "for")
    assert out.systems["000"].space_units.get("p3", {}) == {}  # Mecatol: wszystko
    (field,) = _inputs(out, registry, "p1")  # wybór tylko tam, gdzie ma więcej niż 3 jednostki
    assert field["key"] == "units_102"
    picks = [o["value"] for o in field["options"] if o["value"].split("|")[2] == "cruiser"]
    out = _accept(out, "p1", {"units_102": picks})
    assert out.systems["101"].space_units.get("p1", {}) == {}  # ≤3: wszystkie naraz
    assert out.systems["102"].space_units["p1"] == {"carrier": 2}
