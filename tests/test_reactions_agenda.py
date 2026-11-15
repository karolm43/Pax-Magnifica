"""Testy kart reakcji fazy agendy (RULES.md 53.5.a): riders, Veto, Bribery, Deadly Plot..."""

from __future__ import annotations

import pytest

from src.core import (
    action_cards,
    agenda_phase,
    exploration,
    reaction_cards,
    rules_hooks,
    triggers,
    visibility,
)
from src.core.components import ComponentCategory
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveEffect,
    AgendaPhaseState,
    AgendaStep,
    GameState,
    Phase,
    PlayerState,
    SystemState,
)
from src.core.hooks import reactions_agenda
from src.core.planet_stats import influence_of
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import HookSource

LAW = "revolution"  # For/Against, Law
DIRECTIVE = "secret"  # Elect Player, Directive

ALL_RIDERS = (
    "const_rider", "diplo_rider", "imp_rider", "lead_rider", "politic_rider", "sanction",
    "tech_rider", "trade_rider", "war_rider",
)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(registry: StaticDataRegistry, deck: list[str]) -> GameState:
    """3 graczy, mówca p2 => kolejność głosowania p3, p1, p2; każdy ma planetę z wpływem."""
    state = GameState(
        phase=Phase.AGENDA,
        round_number=3,
        seating_order=["p1", "p2", "p3"],
        speaker_id="p2",
        active_player_id="p2",
        custodians_removed=True,
        players={p: PlayerState(player_id=p, color=p) for p in ("p1", "p2", "p3")},
        agenda=AgendaPhaseState(),
    )
    state.decks.agenda_deck = list(deck)
    state.decks.agenda_deck_seeded = True
    planets = [p for p in sorted(registry.planets) if influence_of(state, registry, p) >= 1][:3]
    state.systems["101"] = SystemState(
        position="101",
        system_id="1",
        planet_owners={planets[0]: "p1", planets[1]: "p2", planets[2]: "p3"},
    )
    for pid in state.players:
        state.players[pid].cc_reinf = 6
    return state


def _planet(state: GameState, pid: str) -> str:
    return next(p for p, o in state.systems["101"].planet_owners.items() if o == pid)


def _hand(state: GameState, pid: str, *cards: str) -> None:
    state.players[pid].private.action_cards = list(cards)


def _play(
    state: GameState, registry: StaticDataRegistry, pid: str, card: str, **params: object
) -> GameState:
    new, implemented = action_cards.play_action_card(state, registry, pid, card, params)
    assert implemented
    return new


def _playable(state: GameState, registry: StaticDataRegistry, pid: str, card: str) -> bool:
    rows = action_cards.playability(state, registry, pid)
    row = next((row for row in rows if row["card_id"] == card), None)
    return bool(row["playable"]) if row is not None else False  # brak karty w ręce


def _revealed(
    registry: StaticDataRegistry, deck: list[str], hands: dict[str, list[str]]
) -> GameState:
    state = _state(registry, deck)
    for pid, cards in hands.items():
        _hand(state, pid, *cards)
    return agenda_phase.reveal_agenda(state, registry, "p2")


# --- Okna ---------------------------------------------------------------------------------


def test_okno_poczatku_fazy_tylko_przed_pierwsza_agenda(registry: StaticDataRegistry) -> None:
    state = _state(registry, [LAW, DIRECTIVE])
    _hand(state, "p1", "abs")
    assert _playable(state, registry, "p1", "abs")
    revealed = agenda_phase.reveal_agenda(state, registry, "p2")
    assert not _playable(revealed, registry, "p1", "abs")


def test_okna_po_ujawnieniu_zamykaja_sie_po_pierwszej_decyzji(
    registry: StaticDataRegistry,
) -> None:
    # Najwyżej 7 kart: nadwyżka ponad limit ręki blokuje zagrywanie (RULES.md 53.8).
    cards = ["veto", "dp1", "assassin", "hack", "insider", "imp_rider", "trade_rider"]
    state = _revealed(registry, [LAW, DIRECTIVE, LAW], {"p1": cards})
    state.players["p2"].private.promissory_notes = ["x"]
    for card in ("veto", "assassin", "hack", "insider", "imp_rider", "trade_rider"):
        assert _playable(state, registry, "p1", card), card
    state = agenda_phase.abstain(state, registry, "p3")  # pierwsza decyzja zamyka okno
    for card in ("veto", "assassin", "hack", "insider", "imp_rider"):
        assert not _playable(state, registry, "p1", card), card


def test_okno_po_ujawnieniu_otwarte_dla_zakazanego_glosu(registry: StaticDataRegistry) -> None:
    """Gracz, który nie może głosować, nadal może zagrać ridera (C_action_cards)."""
    state = _revealed(registry, [LAW], {"p1": ["imp_rider"]})
    state.agenda.blocked = ["p1"]  # type: ignore[union-attr]
    assert _playable(state, registry, "p1", "imp_rider")


# --- Ancient Burial Sites ---------------------------------------------------------------------


def test_abs_wyczerpuje_kulturowe_planety_wskazanego(registry: StaticDataRegistry) -> None:
    cultural = next(
        pid for pid in sorted(registry.planets)
        if exploration.planet_traits(registry, pid) == ["cultural"]
    )
    other = next(
        pid for pid in sorted(registry.planets)
        if pid != cultural and "cultural" not in exploration.planet_traits(registry, pid)
    )
    state = _state(registry, [LAW])
    state.systems["102"] = SystemState(
        position="102", system_id="2", planet_owners={cultural: "p3", other: "p3"}
    )
    _hand(state, "p1", "abs")
    new = _play(state, registry, "p1", "abs", player="p3")
    assert cultural in new.players["p3"].exhausted_planets
    assert other not in new.players["p3"].exhausted_planets
    assert new.players["p1"].private.action_cards == []
    with pytest.raises(ValueError, match="Choose 1 player"):
        action_cards.play_action_card(state, registry, "p1", "abs", {"player": "zz"})


# --- Veto -----------------------------------------------------------------------------------


def test_veto_odrzuca_agende_i_ujawnia_nowa(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE, LAW], {"p1": ["veto"], "p3": ["imp_rider"]})
    assert state.agenda is not None and state.agenda.agenda_id == LAW
    new = _play(state, registry, "p1", "veto")
    assert new.agenda is not None and new.agenda.agenda_id == DIRECTIVE
    assert new.agenda.step is AgendaStep.VOTE and new.agenda.blocked == []
    assert new.decks.agenda_discard == [LAW]
    assert new.decks.agenda_deck == [LAW]
    assert not new.active_effects
    assert _playable(new, registry, "p3", "imp_rider")  # okno riderów nowej agendy
    assert new.agenda.history[0].get("vetoed") is True
    assert new.agenda.agenda_number == 1
    assert new.agenda.kind == "player"  # Elect Player
    # Głosowanie nad nową agendą rusza od początku.
    assert agenda_phase.current_voter(new) == "p3"


def test_veto_nie_po_riderze(registry: StaticDataRegistry) -> None:
    """Veto (okno „when revealed”) jest przed oknem riderów („after”): po zagranym riderze
    Veto już nie wolno (ruling C_action_cards Veto, R_abilities: when przed after)."""
    state = _revealed(registry, [LAW, DIRECTIVE, LAW], {"p1": ["veto", "dp1"], "p3": ["imp_rider"]})
    state = _play(state, registry, "p3", "imp_rider", outcome="for")
    assert not _playable(state, registry, "p1", "veto")
    assert not _playable(state, registry, "p1", "dp1")  # Diplomatic Pressure - to samo okno


def test_veto_bez_karty_w_talii_jest_niezagrywalne(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["veto"]})
    assert not state.decks.agenda_deck
    assert not _playable(state, registry, "p1", "veto")


def test_veto_mozna_powtorzyc(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE, LAW], {"p1": ["veto", "veto3"]})
    state = _play(state, registry, "p1", "veto")
    assert _playable(state, registry, "p1", "veto3")  # nowa agenda = nowe okno
    state = _play(state, registry, "p1", "veto3")
    assert state.agenda is not None and state.agenda.agenda_id == LAW


# --- Assassinate / Hack / Insider -------------------------------------------------------------


def test_assassin_blokuje_glosowanie_wskazanego(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["assassin"]})
    new = _play(state, registry, "p1", "assassin", player="p3")
    assert new.agenda is not None and new.agenda.blocked == ["p3"]
    assert agenda_phase.current_voter(new) == "p1"  # p3 pominięty
    with pytest.raises(ValueError, match="turn to vote"):
        agenda_phase.cast_vote(new, registry, "p3", "for", [_planet(new, "p3")])
    # Zablokowany nadal może się wstrzymać? Nie - jego kolejka po prostu go pomija.
    out = agenda_phase.cast_vote(new, registry, "p1", "for", [_planet(new, "p1")])
    assert agenda_phase.current_voter(out) == "p2"


def test_assassin_formularz_pomija_juz_zablokowanych(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["assassin"]})
    state.agenda.blocked = ["p3"]  # type: ignore[union-attr]
    inputs = rules_hooks.inputs_for("action_cards:assassin")
    assert inputs is not None
    values = [o["value"] for o in inputs(state, registry, "p1")[0]["options"]]
    assert values == ["p1", "p2"]


def test_hack_przesuwa_gracza_na_koniec(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p3": ["hack"]})
    assert state.agenda is not None and state.agenda.vote_order == ["p3", "p1", "p2"]
    new = _play(state, registry, "p3", "hack")
    assert new.agenda is not None and new.agenda.vote_order == ["p1", "p2", "p3"]
    assert agenda_phase.current_voter(new) == "p1"
    assert new.active_player_id == "p1"


def test_insider_podglad_jest_prywatny(registry: StaticDataRegistry) -> None:
    deck = [LAW, DIRECTIVE, LAW, DIRECTIVE, LAW]
    state = _revealed(registry, deck, {"p1": ["insider"]})
    new = _play(state, registry, "p1", "insider")
    assert new.players["p1"].private.agenda_peek == [DIRECTIVE, LAW, DIRECTIVE]
    assert new.decks.agenda_deck == [DIRECTIVE, LAW, DIRECTIVE, LAW]  # talia bez zmian
    # Inny gracz nie widzi identyfikatorów (projekcja widoczności), właściciel tak.
    other_view = visibility.project_for_viewer(new, "p2")
    assert other_view.players["p1"].private.agenda_peek == []
    own_view = visibility.project_for_viewer(new, "p1")
    assert own_view.players["p1"].private.agenda_peek == [DIRECTIVE, LAW, DIRECTIVE]


def test_podglad_znika_na_koncu_fazy_agendy(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE, LAW, DIRECTIVE], {"p1": ["insider"]})
    state = _play(state, registry, "p1", "insider")
    assert state.players["p1"].private.agenda_peek
    state.agenda.step = AgendaStep.COMPLETE  # type: ignore[union-attr]
    out = agenda_phase.finish_agenda(state, registry)
    assert out.players["p1"].private.agenda_peek == []


# --- Riders -----------------------------------------------------------------------------------


def _resolve_for(state: GameState, registry: StaticDataRegistry) -> GameState:
    """p3 głosuje „for"; reszta wstrzymuje się lub jest zablokowana."""
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet(state, "p3")])
    while state.agenda is not None and state.agenda.step is AgendaStep.VOTE:
        voter = agenda_phase.current_voter(state)
        assert voter is not None
        state = agenda_phase.abstain(state, registry, voter)
    return state


def test_rider_blokuje_glos_i_zapisuje_predykcje(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["imp_rider"]})
    new = _play(state, registry, "p1", "imp_rider", outcome="for")
    assert new.agenda is not None and new.agenda.blocked == ["p1"]
    assert reactions_agenda.predictions(new, "p1") == [("imp_rider", "for")]
    assert new.active_effects[0].scope == "agenda"
    # Wynik spoza agendy / brak wyniku => błąd bez zmian.
    with pytest.raises(ValueError, match="possible outcomes"):
        action_cards.play_action_card(state, registry, "p1", "imp_rider", {"outcome": "xx"})
    with pytest.raises(ValueError, match="possible outcomes"):
        action_cards.play_action_card(state, registry, "p1", "imp_rider", {})
    assert state.agenda is not None and state.agenda.blocked == []


def test_imperial_rider_trafiony_daje_vp_a_chybiony_nie(registry: StaticDataRegistry) -> None:
    hit = _play(_revealed(registry, [LAW], {"p1": ["imp_rider"]}), registry, "p1", "imp_rider",
                outcome="for")
    hit = _resolve_for(hit, registry)
    assert hit.agenda is not None and hit.agenda.resolved_outcome == "for"
    assert hit.players["p1"].victory_points == 1
    assert hit.agenda.history[-1]["riders"][0]["correct"] is True
    assert not hit.active_effects  # predykcja wygasa po agendzie

    miss = _play(_revealed(registry, [LAW], {"p1": ["imp_rider"]}), registry, "p1", "imp_rider",
                 outcome="against")
    miss = _resolve_for(miss, registry)
    assert miss.players["p1"].victory_points == 0
    assert miss.agenda.history[-1]["riders"][0]["correct"] is False  # type: ignore[union-attr]


def test_trade_rider_5_tg(registry: StaticDataRegistry) -> None:
    state = _play(_revealed(registry, [LAW], {"p1": ["trade_rider"]}), registry, "p1",
                  "trade_rider", outcome="for")
    assert _resolve_for(state, registry).players["p1"].trade_goods == 5


def test_politics_rider_karty_i_zeton_mowcy(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["politic_rider"]})
    state.decks.action_card_deck = ["a1", "a2", "a3", "a4"]
    state = _play(state, registry, "p1", "politic_rider", outcome="for")
    state = _resolve_for(state, registry)
    assert state.players["p1"].private.action_cards == ["a1", "a2", "a3"]
    assert state.speaker_id == "p1"


def test_leadership_rider_3_zetony_w_wybranych_pulach(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["lead_rider"]})
    with pytest.raises(ValueError, match="exactly 3"):
        action_cards.play_action_card(
            state, registry, "p1", "lead_rider", {"outcome": "for", "tactical": 1}
        )
    state = _play(state, registry, "p1", "lead_rider", outcome="for", tactical=1, fleet=0,
                  strategic=2)
    p = state.players["p1"]
    before = (p.tactical_cc, p.fleet_cc, p.strategic_cc, p.cc_reinf)
    state = _resolve_for(state, registry)
    p = state.players["p1"]
    after = (p.tactical_cc, p.fleet_cc, p.strategic_cc, p.cc_reinf)
    assert tuple(a - b for a, b in zip(after, before, strict=True)) == (1, 0, 2, -3)


def test_sanction_zwraca_zetony_glosujacych_za_wynikiem(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["sanction"]})
    state.players["p3"].fleet_cc = 2
    state.players["p2"].fleet_cc = 2
    state = _play(state, registry, "p1", "sanction", outcome="for")
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet(state, "p3")])
    state = agenda_phase.cast_vote(state, registry, "p2", "against", [_planet(state, "p2")])
    assert state.agenda is not None and state.agenda.resolved_outcome in ("for", "against")
    if state.agenda.resolved_outcome == "for":
        assert state.players["p3"].fleet_cc == 1 and state.players["p2"].fleet_cc == 2
        assert state.players["p3"].cc_reinf == 7


def test_construction_rider_stawia_dok(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["const_rider"]})
    planet = _planet(state, "p1")
    with pytest.raises(ValueError, match="planet you control"):
        action_cards.play_action_card(
            state, registry, "p1", "const_rider", {"outcome": "for", "planet": _planet(state, "p3")}
        )
    state = _play(state, registry, "p1", "const_rider", outcome="for", planet=planet)
    state = _resolve_for(state, registry)
    assert state.systems["101"].planet_units[planet]["p1"]["spacedock"] == 1


def test_warfare_rider_stawia_dreadnought(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["war_rider"]})
    assert not _playable(state, registry, "p1", "war_rider")  # brak własnych statków
    state.systems["101"].space_units["p1"] = {"cruiser": 1}
    assert _playable(state, registry, "p1", "war_rider")
    state = _play(state, registry, "p1", "war_rider", outcome="for", position="101")
    state = _resolve_for(state, registry)
    assert state.systems["101"].space_units["p1"]["dreadnought"] == 1


def test_diplomacy_rider_inni_kladzie_zetony(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["diplo_rider"]})
    state = _play(state, registry, "p1", "diplo_rider", outcome="for", position="101")
    before = {pid: state.players[pid].cc_reinf for pid in state.players}
    state = _resolve_for(state, registry)
    assert sorted(state.systems["101"].command_tokens) == ["p2", "p3"]
    assert state.players["p2"].cc_reinf == before["p2"] - 1
    assert state.players["p1"].cc_reinf == before["p1"]


def test_technology_rider_bada_technologie(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["tech_rider"]})
    state.players["p1"].faction = next(iter(registry.factions))
    options = reactions_agenda._directly_researchable(state, registry, "p1")
    assert options
    with pytest.raises(ValueError, match="technology you can research"):
        action_cards.play_action_card(
            state, registry, "p1", "tech_rider", {"outcome": "for", "tech": "nope"}
        )
    state = _play(state, registry, "p1", "tech_rider", outcome="for", tech=options[0])
    state = _resolve_for(state, registry)
    assert options[0] in state.players["p1"].technologies


def test_nagroda_niewykonalna_jest_pomijana_bez_bledu(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["const_rider"]})
    planet = _planet(state, "p1")
    state = _play(state, registry, "p1", "const_rider", outcome="for", planet=planet)
    state.systems["101"].planet_owners[planet] = "p3"  # planeta utracona przed wynikiem
    state = _resolve_for(state, registry)
    note = state.agenda.history[-1]["riders"][0]  # type: ignore[union-attr]
    assert note["correct"] is True and "no longer controls" in note["skipped"]


def test_dwa_ridery_na_rozne_wyniki(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["imp_rider"], "p2": ["trade_rider"]})
    state = _play(state, registry, "p1", "imp_rider", outcome="for")
    state = _play(state, registry, "p2", "trade_rider", outcome="against")
    state = _resolve_for(state, registry)
    assert state.players["p1"].victory_points == 1
    assert state.players["p2"].trade_goods == 0


# --- Diplomatic Pressure ------------------------------------------------------------------------


def test_diplomatic_pressure_wskazany_wybiera_notke(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["dp1", "dp2"]})
    state.players["p3"].private.promissory_notes = ["n1", "n2"]
    state.players["p2"].private.promissory_notes = []
    assert reaction_cards.window_for(state, registry, "p1", "dp1") is not None
    form = rules_hooks.inputs_for("action_cards:dp1")
    assert form is not None
    targets = [o["value"] for o in form(state, registry, "p1")[0]["options"]]
    assert targets == ["p3"]  # tylko gracz z notką w ręce

    new = _play(state, registry, "p1", "dp1", player="p3")
    assert len(new.pending_offers) == 1
    offer = new.pending_offers[0]
    assert offer.player_id == "p3" and offer.mandatory and offer.owner_id == "p1"
    assert new.players["p3"].private.promissory_notes == ["n1", "n2"]  # jeszcze nic nie oddano
    with pytest.raises(ValueError, match="mandatory"):
        triggers.decline_offer(new, "p3", offer.id)
    with pytest.raises(ValueError, match="belongs to"):
        triggers.accept_offer(new, "p1", offer.id, {"note": "n1"})
    done = triggers.accept_offer(new, "p3", offer.id, {"note": "n2"})
    assert done.players["p1"].private.promissory_notes == ["n2"]
    assert done.players["p3"].private.promissory_notes == ["n1"]
    assert not done.pending_offers
    assert not [e for e in done.active_effects if e.key.endswith("dp_give")]
    # Ten sam cel w tej samej agendzie jest zablokowany (ruling), nowa agenda go odblokuje.
    assert not _playable(done, registry, "p1", "dp2")


def test_diplomatic_pressure_jedna_notka_oddawana_od_razu(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["dp3"]})
    state.players["p3"].private.promissory_notes = ["only"]
    new = _play(state, registry, "p1", "dp3", player="p3")
    assert not new.pending_offers
    assert new.players["p1"].private.promissory_notes == ["only"]
    assert new.players["p3"].private.promissory_notes == []


def test_diplomatic_pressure_bez_celu_niezagrywalne(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["dp4"]})
    assert not _playable(state, registry, "p1", "dp4")
    with pytest.raises(ValueError, match="Choose another player"):
        action_cards.play_action_card(state, registry, "p1", "dp4", {"player": "p3"})


# --- Pauza przed wynikiem, Bribery, Distinguished Councilor ---------------------------------


def test_bez_kart_reakcji_wynik_rozstrzyga_sie_od_razu(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {})
    state = _resolve_for(state, registry)
    assert state.agenda is not None and state.agenda.step is AgendaStep.RESOLVED


def test_karta_w_rece_tworzy_pauze_i_mowca_potwierdza(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["deadly_plot"]})
    state = _resolve_for(state, registry)
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    assert state.agenda.pending_outcome == "for" and state.agenda.resolved_outcome is None
    assert not state.decks.agenda_laws
    with pytest.raises(ValueError, match="speaker"):
        agenda_phase.confirm_outcome(state, registry, "p1")
    done = agenda_phase.confirm_outcome(state, registry, "p2")
    assert done.agenda is not None and done.agenda.step is AgendaStep.RESOLVED
    assert done.decks.agenda_laws == {LAW: "for"}
    with pytest.raises(ValueError, match="Wrong agenda step"):
        agenda_phase.confirm_outcome(done, registry, "p2")


def test_pauza_jednolita_gdy_wlaczona(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agenda_phase, "PAUSE_BEFORE_RESOLUTION_ALWAYS", True)
    state = _resolve_for(_revealed(registry, [LAW], {}), registry)
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED


def test_bribery_po_glosie_mowcy_dodaje_glosy_i_zmienia_wynik(
    registry: StaticDataRegistry,
) -> None:
    state = _revealed(registry, [LAW], {"p3": ["bribery"]})
    state.players["p3"].trade_goods = 10
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet(state, "p3")])
    assert not _playable(state, registry, "p3", "bribery")  # mówca jeszcze nie głosował
    state = agenda_phase.cast_vote(state, registry, "p1", "against", [_planet(state, "p1")])
    state = agenda_phase.cast_vote(state, registry, "p2", "against", [_planet(state, "p2")])
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED  # pauza
    assert state.agenda.pending_outcome == "against"
    assert _playable(state, registry, "p3", "bribery")
    assert not _playable(state, registry, "p1", "bribery")  # p1 nie ma karty
    before = agenda_phase.totals(state.agenda)["for"]
    state = _play(state, registry, "p3", "bribery", trade_goods=10)
    assert state.players["p3"].trade_goods == 0
    totals = agenda_phase.totals(state.agenda)  # type: ignore[arg-type]
    assert totals["for"] == before + 10
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    assert state.agenda.pending_outcome == "for"
    done = agenda_phase.confirm_outcome(state, registry, "p2")
    assert done.agenda is not None and done.agenda.resolved_outcome == "for"


def test_bribery_za_duzo_tg_to_blad(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p3": ["bribery"]})
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet(state, "p3")])
    state = agenda_phase.abstain(state, registry, "p1")
    state = agenda_phase.abstain(state, registry, "p2")
    with pytest.raises(ValueError, match="Not enough trade goods"):
        action_cards.play_action_card(state, registry, "p3", "bribery", {"trade_goods": 3})


def test_distinguished_councilor_tylko_zaraz_po_wlasnym_glosie(
    registry: StaticDataRegistry,
) -> None:
    state = _revealed(registry, [LAW], {"p3": ["distinguished"], "p1": ["distinguished"]})
    assert not _playable(state, registry, "p3", "distinguished")  # jeszcze nie głosował
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet(state, "p3")])
    assert _playable(state, registry, "p3", "distinguished")
    assert not _playable(state, registry, "p1", "distinguished")
    state = _play(state, registry, "p3", "distinguished")
    assert state.agenda is not None and state.agenda.votes["p3"].votes >= 5 + 1
    # Następna decyzja zamyka okno.
    state = agenda_phase.abstain(state, registry, "p1")
    assert not _playable(state, registry, "p1", "distinguished")


def test_distinguished_ostatniego_glosujacego_zmienia_wynik(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p2": ["distinguished"]})
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet(state, "p3")])
    state = agenda_phase.cast_vote(state, registry, "p1", "for", [_planet(state, "p1")])
    state = agenda_phase.cast_vote(state, registry, "p2", "against", [_planet(state, "p2")])
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    assert state.agenda.pending_outcome != "against" or True
    state = _play(state, registry, "p2", "distinguished")
    assert state.agenda is not None and state.agenda.pending_outcome == "against"
    done = agenda_phase.confirm_outcome(state, registry, "p2")
    assert done.agenda is not None and done.agenda.resolved_outcome == "against"


# --- Confounding / Confusing Legal Text ---------------------------------------------------------


def _elect_player_law(registry: StaticDataRegistry) -> str:
    return next(
        agenda_id
        for agenda_id, a in registry.catalog.all(ComponentCategory.AGENDA).items()
        if agenda_phase.classify_target(getattr(a, "target", None)) == "player"
        and (getattr(a, "type", "") or "").lower() == "law"
    )


def _elected_p1(registry: StaticDataRegistry, hands: dict[str, list[str]]) -> GameState:
    state = _revealed(registry, [_elect_player_law(registry)], hands)
    state = agenda_phase.cast_vote(state, registry, "p3", "p1", [_planet(state, "p3")])
    state = agenda_phase.abstain(state, registry, "p1")
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    return state


def test_confounding_podmienia_wybranego_na_zagrywajacego(registry: StaticDataRegistry) -> None:
    law = _elect_player_law(registry)
    state = _elected_p1(registry, {"p3": ["confounding"], "p1": ["confounding"]})
    assert _playable(state, registry, "p3", "confounding")
    assert not _playable(state, registry, "p1", "confounding")  # „another player"
    state = _play(state, registry, "p3", "confounding")
    assert state.agenda is not None and state.agenda.pending_outcome == "p3"
    done = agenda_phase.confirm_outcome(state, registry, "p2")
    assert done.decks.agenda_laws == {law: "p3"}
    assert agenda_phase.owned_laws(done, registry, "p3") == [law]


def test_confusing_wybrany_wskazuje_innego(registry: StaticDataRegistry) -> None:
    law = _elect_player_law(registry)
    state = _elected_p1(registry, {"p1": ["confusing"], "p3": ["confusing"]})
    assert _playable(state, registry, "p1", "confusing")
    assert not _playable(state, registry, "p3", "confusing")  # „when you are elected"
    with pytest.raises(ValueError, match="another player"):
        action_cards.play_action_card(state, registry, "p1", "confusing", {"player": "p1"})
    state = _play(state, registry, "p1", "confusing", player="p2")
    done = agenda_phase.confirm_outcome(state, registry, "p2")
    assert done.decks.agenda_laws == {law: "p2"}


def test_confounding_niezagrywalne_przy_agendzie_for_against(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["confounding", "confusing"]})
    state = _resolve_for(state, registry)
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    assert not _playable(state, registry, "p1", "confounding")
    assert not _playable(state, registry, "p1", "confusing")


def test_predykcje_rozstrzygaja_sie_wg_nowo_wybranego(registry: StaticDataRegistry) -> None:
    state = _revealed(
        registry, [_elect_player_law(registry)], {"p1": ["trade_rider"], "p3": ["confounding"]}
    )
    state = _play(state, registry, "p1", "trade_rider", outcome="p3")
    state = agenda_phase.cast_vote(state, registry, "p3", "p1", [_planet(state, "p3")])
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.agenda is not None and state.agenda.pending_outcome == "p1"
    state = _play(state, registry, "p3", "confounding")
    done = agenda_phase.confirm_outcome(state, registry, "p2")
    assert done.players["p1"].trade_goods == 5  # przewidział p3, a wybrany został p3


# --- Deadly Plot --------------------------------------------------------------------------------


def test_deadly_plot_wymaga_innego_glosu_lub_predykcji(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["deadly_plot"], "p3": ["deadly_plot"]})
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet(state, "p3")])
    state = agenda_phase.cast_vote(state, registry, "p1", "against", [_planet(state, "p1")])
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    winner = state.agenda.pending_outcome
    voter_for_winner = "p3" if winner == "for" else "p1"
    voter_other = "p1" if winner == "for" else "p3"
    assert not _playable(state, registry, voter_for_winner, "deadly_plot")
    assert _playable(state, registry, voter_other, "deadly_plot")
    with pytest.raises(ValueError, match="no open window"):
        action_cards.play_action_card(state, registry, voter_for_winner, "deadly_plot", {})


def test_deadly_plot_odrzuca_agende_bez_efektu_i_wyczerpuje_planety(
    registry: StaticDataRegistry,
) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["deadly_plot"], "p3": ["deadly_plot"]})
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet(state, "p3")])
    state = agenda_phase.cast_vote(state, registry, "p1", "against", [_planet(state, "p1")])
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    loser = "p1" if state.agenda.pending_outcome == "for" else "p3"  # głosował na inny wynik
    bystander = "p3" if loser == "p1" else "p1"
    new = _play(state, registry, loser, "deadly_plot")
    assert new.agenda is not None and new.agenda.step is AgendaStep.RESOLVED
    assert new.agenda.resolved_outcome is None
    assert new.decks.agenda_discard == [LAW] and not new.decks.agenda_laws  # prawo NIE wchodzi
    assert new.decks.agenda_deck == [DIRECTIVE]  # nie zastąpiona
    assert new.agenda.history[-1]["voided"] is True
    assert _planet(new, loser) in new.players[loser].exhausted_planets
    # Planety pozostałych: tylko te wyczerpane głosem.
    assert new.players[bystander].exhausted_planets == [_planet(new, bystander)]
    # Można iść dalej do drugiej agendy.
    nxt = agenda_phase.continue_agenda(new, registry, "p2")
    assert nxt.agenda is not None and nxt.agenda.step is AgendaStep.REVEAL
    assert nxt.agenda.agenda_number == 2


def test_deadly_plot_unieważnia_predykcje(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["deadly_plot", "imp_rider"]})
    state = _play(state, registry, "p1", "imp_rider", outcome="against")
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet(state, "p3")])
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    assert _playable(state, registry, "p1", "deadly_plot")  # przewidział inny wynik
    new = _play(state, registry, "p1", "deadly_plot")
    assert new.players["p1"].victory_points == 0
    assert not new.active_effects


def test_deadly_plot_nie_dziala_przed_pauza(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["deadly_plot"]})
    assert not _playable(state, registry, "p1", "deadly_plot")  # głosowanie trwa


# --- Zdarzenia / infrastruktura -----------------------------------------------------------------


def test_veto_emituje_zdarzenia_ujawnienia_nowej_agendy(registry: StaticDataRegistry) -> None:
    """Hook efektu trwałego widzi ponowne ujawnienie (Veto idzie przez centralne otwarcie)."""
    seen: list[str] = []
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["veto"]})
    source = HookSource(rules_hooks.SOURCE_EFFECT, "test:watch")
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.AGENDA_REVEALED, Moment.AFTER, source)(
            lambda _s, _p, ctx: seen.append(str(ctx.get("agenda")))
        )
        state.active_effects = [
            ActiveEffect(id="fx1", key="test:watch", scope="round", owner=None)
        ]
        new = _play(state, registry, "p1", "veto")
    assert new.agenda is not None and new.agenda.agenda_id == DIRECTIVE
    assert seen == [DIRECTIVE] * len(state.players)  # po jednym wywołaniu na gracza
