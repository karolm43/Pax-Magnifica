"""The Xxcha Kingdom — komplet komponentów frakcji (RULES.md 62.9) i rulingi F_xxcha."""

from __future__ import annotations

import pytest

from src.core import (
    action_cards,
    active_effects,
    agenda_phase,
    card_hold,
    faction_components,
    payment,
    production,
    reaction_cards,
    rules_hooks,
    space_cannon,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    AgendaPhaseState,
    AgendaStep,
    GameState,
    PendingOffer,
    Phase,
    PlayerState,
    SystemState,
)
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import xxcha
from src.core.planet_stats import influence_of, resources_of
from src.core.registry import StaticDataRegistry
from tests.factions.completeness import missing_components
from tests.rulings import ruling

NOW = 1000.0
_CARD = "industrial_initiative"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _planet(registry: StaticDataRegistry, system_id: str) -> str:
    return registry.systems[system_id].planets[0]


def _state(registry: StaticDataRegistry) -> GameState:
    """p1 = Xxcha (aktywny) z planetą w 101; 000 = Mecatol; 102 sąsiad 101 z wolną planetą."""
    p1 = PlayerState(player_id="p1", color="green", faction="xxcha", strategic_cc=2)
    p2 = PlayerState(player_id="p2", color="blue", faction="sol", strategic_cc=2)
    mine, free = _planet(registry, "20"), _planet(registry, "21")
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            "101": SystemState(position="101", system_id="20", planet_owners={mine: "p1"}),
            "102": SystemState(position="102", system_id="21"),
            "104": SystemState(position="104", system_id="25"),
        },
    )
    state.players["p1"].controlled_planets = [mine]
    assert free
    return state


def test_kompletnosc_xxcha(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "xxcha") == []


def test_bohater_thunders_edge_zastepuje_codex(registry: StaticDataRegistry) -> None:
    """Decyzja użytkownika 2026-11-16: najnowsza wersja lidera (``homebrewReplacesID``)."""
    assert registry.factions["xxcha"].leaders[-1] == "xxchahero-te"
    assert "xxchahero" not in registry.factions["xxcha"].leaders
    assert registry.factions["naalu"].leaders[0] == "naaluagent-te"
    bundle = registry.catalog.faction_bundle("xxcha")
    assert {leader.id for leader in bundle.leaders} == {
        "xxchaagent", "xxchacommander", "xxchahero-te"
    }


# ------------------------------------------------------------------------- Peace Accords


@ruling("F_xxcha/peace-accords/1", "abilities:peace_accords#1")
def test_peace_accords_cele(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    targets = xxcha.peace_targets(state, "p1")
    free = _planet(registry, "21")
    assert ("102", free) in targets
    assert all(pos != "000" for pos, _ in targets)  # nie Mecatol Rex
    assert all(pos != "101" or p != _planet(registry, "20") for pos, p in targets)  # nie własna
    with_units = _state(registry)
    with_units.systems["102"].planet_units = {free: {"p2": {"infantry": 1}}}
    assert ("102", free) not in xxcha.peace_targets(with_units, "p1")  # planeta z jednostkami


@ruling("abilities:peace_accords#1")
def test_peace_accords_cudza_planeta_i_wyczerpana(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    free = _planet(registry, "21")
    state.systems["102"].planet_owners = {free: "p2"}  # cudza, bez jednostek - też wolno
    state.players["p2"].controlled_planets = [free]
    ctx = {"player": "p1", "initiative": 2, "params": {"planet": f"102|{free}"}}
    xxcha.peace_accords(state, "p1", ctx)
    assert state.systems["102"].planet_owners[free] == "p1"
    assert free in state.players["p1"].exhausted_planets
    assert state.exploration is None  # kontrolowana wcześniej - bez eksploracji (F_xxcha)


def test_peace_accords_niekontrolowana_eksploracja(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    free = _planet(registry, "21")
    xxcha.peace_accords(state, "p1", {"params": {"planet": f"102|{free}"}})
    assert state.systems["102"].planet_owners[free] == "p1"
    assert state.exploration is not None  # F_xxcha: Xxcha ją eksploruje


@ruling("abilities:peace_accords#1")
def test_peace_accords_tylko_po_wlasnej_diplomacy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    assert xxcha._after_own_diplomacy(state, "p1", {"player": "p1", "initiative": 2})
    assert not xxcha._after_own_diplomacy(state, "p1", {"player": "p2", "initiative": 2})
    assert not xxcha._after_own_diplomacy(state, "p1", {"player": "p1", "initiative": 3})


# ------------------------------------------------------------------- Quash, Political Favor


def _agenda_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry)
    state.phase = Phase.AGENDA
    state.speaker_id = "p2"
    state.agenda = AgendaPhaseState(step=AgendaStep.REVEAL)
    state.decks.agenda_deck = ["mutiny", "minister_peace", "minister_war"]
    state.decks.agenda_deck_seeded = True
    return agenda_phase.reveal_agenda(state, registry, "p2")


@ruling("abilities:quash#1")
def test_quash_okno_i_zeton(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    assert xxcha._quash_window(state, registry, "p1") is None
    state.players["p1"].strategic_cc = 0
    assert "strategy pool" in str(xxcha._quash_window(state, registry, "p1"))
    outside = _state(registry)
    assert "agenda is revealed" in str(xxcha._quash_window(outside, registry, "p1"))


@ruling("F_xxcha/quash/5", "F_xxcha/quash/3", "abilities:quash#2")
def test_quash_podmiana_political_secret_i_transakcje(registry: StaticDataRegistry) -> None:
    """F_xxcha: Political Secret wraca bez efektu na nowej agendzie; każda agenda = nowa
    transakcja; Quash wolno użyć na agendzie zastępczej."""
    state = _agenda_state(registry)
    agenda_phase.block_voter(state, registry, "p2")  # skutek Political Secret / ridera
    state.players["p1"].transacted_with = ["p2"]
    new_state, _ = faction_components.play(state, registry, "p1", "ability", "quash")
    assert new_state.agenda is not None
    assert new_state.agenda.agenda_id == "minister_peace"
    assert "p2" not in new_state.agenda.blocked
    assert new_state.players["p1"].transacted_with == []
    assert new_state.players["p1"].strategic_cc == 1
    assert xxcha._quash_window(new_state, registry, "p1") is None  # znów na zastępczej


def test_political_secret_blokuje_quash(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    state.active_effects = []
    active_effects.add_effect(
        state, "promissory_notes:political_secret", Duration.AGENDA, owner="p1"
    )
    reason = faction_components.block_reason(state, registry, "p1", "ability", "quash")
    assert reason is not None and "Political Secret" in reason


@ruling("F_xxcha/political-favor/3")
def test_political_favor_bez_zetonu_xxcha(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    window = next(
        w for w in reaction_cards.open_windows(state)
        if (w.event, w.moment) == (GameEvent.AGENDA_REVEALED, Moment.WHEN)
    )
    assert xxcha._favor_condition(state, registry, "p2", window) is None
    state.players["p1"].strategic_cc = 0
    assert "strategy pool" in str(xxcha._favor_condition(state, registry, "p2", window))


# ------------------------------------------------------------------------ Instinct Training


def _hold_state(registry: StaticDataRegistry, *, sabotage_left: bool = True) -> GameState:
    state = _state(registry)
    state.active_player_id = "p2"
    state.players["p1"].technologies = ["it"]
    state.players["p2"].private.action_cards = [_CARD]
    state.decks.action_card_deck = ["filler"]
    if not sabotage_left:
        state.decks.action_card_discard = list(card_hold.SABOTAGE_IDS)
    return state


@ruling("technologies:it#1")
def test_instinct_training_okno_bez_kart_w_rece(registry: StaticDataRegistry) -> None:
    state = _hold_state(registry, sabotage_left=False)
    assert card_hold.eligible_players(state, "p2", _CARD) == ["p1"]  # jawne: tech + żeton
    state.players["p1"].strategic_cc = 0
    assert card_hold.eligible_players(state, "p2", _CARD) == []  # bez żetonu - od razu


@ruling(
    "F_xxcha/instinct-training/3",
    "F_xxcha/instinct-training/8",
    "technologies:it#1",
    "technologies:it#2",
)
def test_instinct_training_anuluje_akcje_bez_kosztu(registry: StaticDataRegistry) -> None:
    state = _hold_state(registry)
    held, _ = action_cards.play_action_card(state, registry, "p2", _CARD, {}, now=NOW)
    assert held.held_play is not None
    assert held.players["p2"].took_action_this_turn
    assert xxcha._instinct_window(held, registry, "p1") is None
    after, _ = faction_components.play(held, registry, "p1", "technology", "it")
    assert after.held_play is None
    assert _CARD in after.decks.action_card_discard
    assert not after.players["p2"].took_action_this_turn  # F_xxcha: inna akcja albo pas
    assert "it" in after.players["p1"].exhausted_technologies
    assert after.players["p1"].strategic_cc == 1


@ruling("technologies:it#1")
def test_instinct_training_nie_na_wlasna_karte(registry: StaticDataRegistry) -> None:
    state = _hold_state(registry)
    state.active_player_id = "p1"
    state.players["p1"].private.action_cards = [_CARD]
    state.players["p2"].private.action_cards = ["sabo1"]
    held, _ = action_cards.play_action_card(state, registry, "p1", _CARD, {}, now=NOW)
    assert "own action card" in str(xxcha._instinct_window(held, registry, "p1"))


@ruling("F_xxcha/instinct-training/1")
def test_instinct_training_anuluje_sabotage(registry: StaticDataRegistry) -> None:
    """F_xxcha: Sabotage na kartę Xxcha czeka na Instinct Training; po anulowaniu wraca okno
    karty, a bez anulowania Sabotage anuluje kartę jak dotąd."""
    state = _hold_state(registry)
    state.active_player_id = "p1"
    state.players["p1"].private.action_cards = [_CARD]
    state.players["p2"].private.action_cards = ["sabo1", "sabo2"]
    held, _ = action_cards.play_action_card(state, registry, "p1", _CARD, {}, now=NOW)
    countered, _ = action_cards.play_action_card(held, registry, "p2", "sabo1", {}, now=NOW)
    assert countered.held_play is not None and countered.held_play.counter is not None
    assert countered.held_play.eligible == ["p1"]
    # bez Instinct Training: Sabotage wykonuje się po czasie okna
    resolved = card_hold.resolve(countered, registry)
    assert resolved.held_play is None
    assert {_CARD, "sabo1"} <= set(resolved.decks.action_card_discard)
    # z Instinct Training: Sabotage odrzucone, karta Xxcha nadal czeka
    after, _ = faction_components.play(countered, registry, "p1", "technology", "it")
    assert after.held_play is not None and after.held_play.counter is None
    assert after.held_play.card_id == _CARD and "p2" in after.held_play.eligible
    assert "sabo1" in after.decks.action_card_discard


def test_inne_komponenty_okna_nie_dzialaja_w_hold(registry: StaticDataRegistry) -> None:
    state = _hold_state(registry)
    held, _ = action_cards.play_action_card(state, registry, "p2", _CARD, {}, now=NOW)
    held.phase = Phase.AGENDA
    with pytest.raises(ValueError):
        faction_components.play(held, registry, "p1", "ability", "quash")


# ---------------------------------------------------------------------- Nullification Field


def _activation(registry: StaticDataRegistry) -> GameState:
    state = _state(registry)
    state.active_player_id = "p2"
    state.active_system = "102"
    state.players["p1"].technologies = ["nf"]
    state.systems["102"].space_units = {"p1": {"cruiser": 1}}
    return state


@ruling("technologies:nf#1")
def test_nullification_field_warunek(registry: StaticDataRegistry) -> None:
    state = _activation(registry)
    ctx = {"player": "p2", "position": "102"}
    assert xxcha._nullification_ready(state, "p1", ctx)
    state.systems["102"].space_units = {"p1": {}}
    assert not xxcha._nullification_ready(state, "p1", ctx)  # bez statków Xxcha
    own = _activation(registry)
    own.active_player_id = "p1"
    assert not xxcha._nullification_ready(own, "p1", {"player": "p1", "position": "102"})
    empty = _activation(registry)
    empty.players["p1"].strategic_cc = 0
    assert not xxcha._nullification_ready(empty, "p1", ctx)


@ruling("F_xxcha/nullification-field/1", "technologies:nf#2")
def test_nullification_field_kasuje_oferty_after_aktywacji(registry: StaticDataRegistry) -> None:
    state = _activation(registry)
    state.players["p2"].took_action_this_turn = True
    state.pending_offers = [PendingOffer(
        id="x", player_id="p2", event=GameEvent.SYSTEM_ACTIVATED.value,
        moment=Moment.AFTER.value, hook_seq=0,
    )]
    xxcha.nullification_field(state, "p1", {"player": "p2", "position": "102"})
    assert state.pending_offers == []
    assert state.active_system is None
    assert state.active_player_id == "p1"
    assert "nf" in state.players["p1"].exhausted_technologies
    assert state.players["p1"].strategic_cc == 1


# --------------------------------------------------------------------- Ggrocuto Rinn (agent)


@ruling(
    "F_xxcha/ggrocuto-rinn/1",
    "F_xxcha/ggrocuto-rinn/2",
    "leaders:xxchaagent#1",
    "leaders:xxchaagent#2",
)
def test_ggrocuto_rinn_tylko_wyczerpana_i_piechota_obok(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states = {"xxchaagent": "unlocked"}
    reason = faction_components.block_reason(state, registry, "p1", "leader", "xxchaagent")
    assert reason is not None and "exhausted" in reason  # F_xxcha: musi być wyczerpana
    far = _planet(registry, "25")
    near = _planet(registry, "21")
    for pos, planet in (("102", near), ("104", far)):
        state.systems[pos].planet_owners = {planet: "p2"}
        state.systems[pos].planet_units = {planet: {"p2": {"infantry": 2}}}
        state.players["p2"].exhausted_planets.append(planet)
    values = [o["value"] for o in xxcha.agent_inputs(state, registry, "p1")[0]["options"]]
    assert f"102|{near}|p2" in values  # obok planety Xxcha - wolno usunąć piechotę
    assert f"104|{far}|none" in values and f"104|{far}|p2" not in values
    xxcha.ggrocuto_rinn(state, registry, "p1", {"planet": f"102|{near}|p2"})
    assert near not in state.players["p2"].exhausted_planets
    assert state.systems["102"].planet_units[near]["p2"]["infantry"] == 1


# ------------------------------------------------------------------ Elder Qanoj (commander)


@ruling("leaders:xxchacommander#unlock")
def test_elder_qanoj_odblokowanie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    unlock = xxcha._commander_unlocked
    total = sum(influence_of(state, registry, p) for p in state.players["p1"].controlled_planets)
    assert unlock(state, registry, "p1") is (total >= 12)
    rich = [p for p, d in sorted(registry.planets.items()) if (d.influence or 0) >= 4][:3]
    for i, planet in enumerate(rich):
        state.systems[f"9{i}"] = SystemState(position=f"9{i}", system_id="18",
                                              planet_owners={planet: "p1"})
    assert unlock(state, registry, "p1")


@ruling("F_xxcha/elder-qanoj/1", "leaders:xxchacommander#1", "leaders:xxchacommander#2")
def test_elder_qanoj_glos_za_planete_i_bez_blokady(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    zero = next(p for p, d in sorted(registry.planets.items()) if (d.influence or 0) == 0)
    state.systems["99"] = SystemState(position="99", system_id="18", planet_owners={zero: "p1"})
    plain = {r["planet"]: r["influence"] for r in agenda_phase.voting_planets(state, registry,
                                                                               "p1")}
    assert zero not in plain
    state.players["p1"].leader_states = {"xxchacommander": "unlocked"}
    with_bonus = agenda_phase.voting_planets(state, registry, "p1")
    rows = {r["planet"]: r["influence"] for r in with_bonus}
    assert rows[zero] == 1  # F_xxcha: planeta z 0 wpływu daje 1 głos
    for planet, votes in plain.items():
        assert rows[planet] == votes + 1
    agenda_phase.block_voter(state, registry, "p1")  # rider / Political Secret
    assert "p1" not in state.agenda.blocked  # type: ignore[union-attr]
    agenda_phase.block_voter_for_phase(state, "p1")  # Public Execution
    assert "p1" not in state.agenda.phase_blocked  # type: ignore[union-attr]


# ---------------------------------------------------- Xxekir Grom — Planetary Defense Nexus


@ruling(
    "F_xxcha/xxekir-grom-planetary-defense-nexus-omega-omega/1",
    "F_xxcha/xxekir-grom-planetary-defense-nexus-omega-omega/2",
    "leaders:xxchahero-te#1",
)
def test_xxekir_grom_pds_i_mech_na_gotowej_planecie(registry: StaticDataRegistry) -> None:
    """F_xxcha (ΩΩ): wolno stawiać na gotowej planecie i kilka jednostek na jednej planecie."""
    state = _state(registry)
    mine = _planet(registry, "20")
    state.players["p1"].leader_states = {"xxchahero-te": "unlocked"}
    options = [o["value"] for o in xxcha.hero_inputs(state, registry, "p1")[0]["options"]]
    pds = [v for v in options if v.startswith(f"pds|{mine}|")]
    mechs = [v for v in options if v.startswith(f"mech|{mine}|")]
    assert len(pds) == 2 and len(mechs) == 4  # limit 2 PDS na planecie
    new_state = state.clone()
    xxcha.planetary_defense_nexus(new_state, registry, "p1", {"units": pds + mechs[:2]})
    units = new_state.systems["101"].planet_units[mine]["p1"]
    assert units["pds"] == 2 and units["mech"] == 2
    with pytest.raises(ValueError):
        xxcha.planetary_defense_nexus(state.clone(), registry, "p1", {"units": mechs + pds})


@ruling("leaders:xxchahero-te#2", "leaders:xxchahero-te#3")
def test_xxekir_grom_odnawia_i_purge(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    mine = _planet(registry, "20")
    state.players["p1"].leader_states = {"xxchahero-te": "unlocked"}
    state.players["p1"].exhausted_planets = [mine]
    new_state, _ = faction_components.play(
        state, registry, "p1", "leader", "xxchahero-te", {"units": [f"mech|{mine}|0"]}
    )
    assert mine not in new_state.players["p1"].exhausted_planets
    assert new_state.players["p1"].leader_states["xxchahero-te"] == "purged"


# ----------------------------------------------------------- Loncara Ssodu, Indomitus


@ruling("units:xxcha_flagship#1", "units:xxcha_mech#1")
def test_space_cannon_na_sasiedni_system(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    mine = _planet(registry, "20")
    state.active_player_id = "p2"
    state.active_system = "102"
    state.systems["101"].space_units = {"p1": {"flagship": 1}}
    state.systems["101"].planet_units = {mine: {"p1": {"mech": 1}}}
    grid = HexGrid()
    for pos, sid in (("101", "20"), ("102", "21")):
        grid.place_system(pos, sid)
    grid.build_edges()
    remote = {s.base_type for s in space_cannon.offense_shooters(state, grid, registry, "p1")
              if s.remote}
    assert {"flagship", "mech"} <= remote
    plain = _state(registry)
    plain.players["p1"].faction = "sol"  # zwykły flagowiec/mech bez Deep Space Cannon
    plain.active_system = "102"
    plain.systems["101"].space_units = {"p1": {"flagship": 1}}
    assert not [s for s in space_cannon.offense_shooters(plain, grid, registry, "p1") if s.remote]


# ------------------------------------------------------------------- Archon's Gift (BT)


@ruling("F_xxcha/archons-gift/2", "breakthroughs:xxchabt#1", "breakthroughs:xxchabt#2")
def test_archons_gift_tylko_wydawanie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    mine = _planet(registry, "20")
    res, inf = resources_of(state, registry, mine), influence_of(state, registry, mine)
    assert payment.ready_planet_values(state, registry, "p1", "influence")[mine] == inf
    state.players["p1"].breakthrough_unlocked = True
    best = max(res, inf)
    assert payment.ready_planet_values(state, registry, "p1", "influence")[mine] == best
    assert payment.ready_planet_values(state, registry, "p1", "resources")[mine] == best
    assert production.pay_value(state, registry, mine, "p1") == best
    # F_xxcha: inne efekty bez zmian (głosy, wartość planety)
    assert influence_of(state, registry, mine) == inf
    agenda = _agenda_state(registry)
    agenda.players["p1"].breakthrough_unlocked = True
    votes = {r["planet"]: r["influence"] for r in agenda_phase.voting_planets(agenda, registry,
                                                                               "p1")}
    assert votes.get(mine, 0) == inf

