"""Universities of Jol-Nar — rulingi ``docs/rules_tirules/F_jol_nar.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Podstawowe testy komponentów są w ``test_jolnar.py`` i
``test_flows_jolnar.py`` (tam też część znaczników). Statusy bez testu:
``tests/rulings_status.json`` (umowy niewiążące, Nekro).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    battle,
    faction_components,
    leaders,
    movement,
    promissory_play,
    rules_hooks,
    technology,
    transaction,
    triggers,
    unit_ops,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    PlayerState,
    SystemState,
)
from src.core.hex_grid import HexGrid
from src.core.hooks import action_cards_economy, agendas_directives
from src.core.hooks.factions import jolnar
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards import diplomacy
from src.core.strategy_cards import technology as technology_card
from src.core.strategy_cards.base import CardContext
from src.core.transaction import TransactionSide
from src.core.unit_ops import UnitCause
from tests.factions.test_jolnar import _accept, _secondary_window, _state
from tests.factions.test_jolnar import _grid as _grid  # noqa: F401 - fixture modułu
from tests.factions.test_jolnar import grid as grid  # noqa: F401 - fixture modułu
from tests.factions.test_jolnar import registry as registry  # noqa: F401 - fixture modułu
from tests.rulings import ruling


def _ra_playable(state: GameState, registry: StaticDataRegistry, player: str) -> bool:
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, player)}
    return bool(rows[jolnar.RESEARCH_AGREEMENT]["playable"])


def _neighbors(state: GameState) -> None:
    """p1 i p2 są sąsiadami (statki w tym samym systemie) - transakcje są możliwe."""
    state.systems["102"].space_units = {"p1": {"cruiser": 1}, "p2": {"cruiser": 1}}


# ========================================================================================= Fragile


@ruling("F_jol_nar/fragile/1")
def test_fragile_nie_dotyczy_afb_bombardowania_space_cannon(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    """AFB, Space Cannon i bombardowanie mają własne punkty modyfikatora - bez −1 z Fragile;
    wpis rzutu AFB nie niesie modyfikatora combat (przerzut Agnlan Oln liczy bez −1)."""
    state = _state()
    state.systems["102"].space_units = {"p1": {"destroyer": 2}, "p2": {"fighter": 3}}
    state.active_combat = ActiveCombat(
        kind="space", position="102", attacker="p1", defender="p2", step=CombatStep.AFB
    )
    after = battle.resolve_afb(state, grid, registry)
    assert after.active_combat is not None
    entries = after.active_combat.afb["p1"]
    assert entries and all(e["modifier"] == 0 for e in entries)
    ctx = {"shooter": "p1", "base_type": "pds"}
    assert rules_hooks.modify(
        rules_hooks.POINT_SPACE_CANNON_ROLL_MODIFIER, state, "p2", 0, ctx) == 0
    assert rules_hooks.modify(
        rules_hooks.POINT_BOMBARDMENT_ROLL_MODIFIER, state, "p2", 0,
        {"planet": "industrex", "attacker": "p1"}) == 0


@ruling("F_jol_nar/fragile/1", "leaders:jolnarcommander#1")
def test_agnlan_przerzut_afb_bez_fragile(registry: StaticDataRegistry, grid: HexGrid) -> None:
    """Po przerzucie AFB trafienia liczą się bez −1 (Destroyer: AFB 9; kość 9 trafia)."""
    from src.core import space_cannon

    state = _state()
    entries = [{"baseType": "destroyer", "dice": [9, 1], "hitsOn": 9, "modifier": 0}]
    fresh, _ = space_cannon.reroll_entries(
        state, entries, roller="p1", picks={(0, 1)}, source=("agnlan_oln", "Agnlan Oln")
    )
    assert fresh[0]["dice"][0] == 9
    assert fresh[0]["hits"] >= 1


@ruling("F_jol_nar/fragile/2", "abilities:fragile#1")
def test_fragile_obowiazkowe(registry: StaticDataRegistry, grid: HexGrid) -> None:
    """Fragile to MODIFY bez oferty: zawsze −1, gracz nie może z niego zrezygnować."""
    state = _state()
    state.systems["102"].space_units = {"p1": {"cruiser": 1, "flagship": 1}}
    units = battle.combat_units(
        state, grid, registry, kind="space", position="102", planet=None, player_id="p1"
    )
    assert {u.base_type: u.modifier for u in units} == {"cruiser": -1, "flagship": -1}
    assert not state.pending_offers


# =================================================================================== Shield Paling


@ruling("F_jol_nar/shield-paling/1", "units:jolnar_mech#1")
def test_shield_paling_mech_nadal_fragile(registry: StaticDataRegistry, grid: HexGrid) -> None:
    state = _state()
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 1, "mech": 1}}}
    units = battle.combat_units(
        state, grid, registry, kind="ground", position="102", planet="industrex", player_id="p1"
    )
    assert {u.base_type: u.modifier for u in units} == {"infantry": 0, "mech": -1}


# ======================================================================================== Flagowiec


@ruling("units:jolnar_flagship#1")
def test_hylarim_naturalny_wynik_przed_fragile() -> None:
    """9 przed modyfikatorami (po Fragile 8) nadal daje 2 dodatkowe trafienia."""
    state = _state()
    assert battle.natural_extra_hits(state, "p1", "space", "flagship", [9]) == 2
    assert battle.natural_extra_hits(state, "p1", "space", "flagship", [8]) == 0


# =================================================================================== E-Res Siphons


@ruling("F_jol_nar/eres-siphons/1", "technologies:ers#1")
def test_ers_bez_wrogich_dzialan() -> None:
    """Aktywacja przez innego gracza bez ruchu/walki - nadal 4 TG."""
    state = _state()
    state.players["p1"].technologies = ["ers"]
    state.systems["105"].space_units = {"p1": {"carrier": 1}}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": "105"})
    assert state.players["p1"].trade_goods == 7


@ruling("F_jol_nar/eres-siphons/2")
def test_ers_nie_przy_diplomacy(registry: StaticDataRegistry) -> None:
    """Primary Diplomacy kładzie żeton Jol-Nar w systemie, ale to nie aktywacja - bez TG."""
    state = _state()
    state.players["p1"].technologies = ["ers"]
    state.systems["102"].space_units = {"p1": {"cruiser": 1}}
    state.systems["102"].planet_owners = {"industrex": "p2"}
    diplomacy._primary(state, None, "p2", {"system": "102", "planets": []})  # type: ignore[arg-type]
    assert "p1" in state.systems["102"].command_tokens
    assert state.players["p1"].trade_goods == 3


# ======================================================================== Spatial Conduit Cylinder


def _conduit(state: GameState, active: str) -> GameState:
    state.players["p1"].technologies = ["scc"]
    state.active_system = active
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": active})
    return _accept(state, "p1", "Spatial Conduit")


@ruling("R_gravity_rift/rules-reference/2")
def test_scc_wyjscie_z_gravity_rift_wymaga_rzutu(grid: HexGrid) -> None:
    """101 (gravity rift) nie sąsiaduje ze 105; trasa 101 → 105 przez SCC nadal rzuca
    za szczelinę."""
    state = _state()
    state.systems["101"] = SystemState(position="101", system_id="41")
    state.systems["101"].space_units = {"p1": {"cruiser": 1}}
    state.systems["105"].space_units = {"p1": {"carrier": 1}}
    assert "105" not in grid.neighbors("101")
    after = _conduit(state, "105")
    path = movement.shortest_legal_path(
        grid, after, "101", "105", "p1", can_enter_asteroids=False
    )
    assert path == ["101", "105"]
    assert movement.rift_nodes(after, grid, path, "p1") == ["101"]


@ruling("technologies:scc#2")
def test_scc_statek_leci_przez_inne_systemy(grid: HexGrid) -> None:
    """Krążownik ze 104 leci przez 103 (piechota Jol-Nar; 103 nie sąsiaduje ze 105) do aktywnego
    105 w 2 ruchach - może tam zabrać ładunek. Bez SCC ta trasa jest dłuższa."""
    state = _state()
    for position, system_id in (("103", "20"), ("104", "24")):
        state.systems[position] = SystemState(position=position, system_id=system_id)
    state.systems["103"].space_units = {"p1": {"infantry": 1}}
    state.systems["104"].space_units = {"p1": {"cruiser": 1}}
    state.systems["105"].space_units = {"p1": {"carrier": 1}}
    assert "105" not in grid.neighbors("103")
    state.active_system = "105"
    plain = movement.route_through(state, grid, "104", ["103"], "p1")
    assert plain is None or len(plain) > 3
    after = _conduit(state, "105")
    assert movement.route_through(after, grid, "104", ["103"], "p1") == ["104", "103", "105"]


@ruling("technologies:scc#1")
def test_scc_opcjonalne_i_wyczerpuje() -> None:
    state = _state()
    state.players["p1"].technologies = ["scc"]
    state.systems["102"].space_units = {"p1": {"cruiser": 1}}
    state.systems["105"].space_units = {"p1": {"carrier": 1}}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "102"})
    offer = next(o for o in state.pending_offers if "Spatial" in o.label)
    declined = triggers.decline_offer(state, "p1", offer.id)
    assert "scc" not in declined.players["p1"].exhausted_technologies
    accepted = _accept(state, "p1", "Spatial Conduit")
    assert "scc" in accepted.players["p1"].exhausted_technologies
    again = accepted.clone()
    triggers.fire(again, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "105"})
    assert not any("Spatial" in o.label for o in again.pending_offers)  # wyczerpana


# ============================================================================== Research Agreement


@ruling("F_jol_nar/research-agreement/1")
def test_ra_kilka_badan_wybor_kazdego(registry: StaticDataRegistry) -> None:
    """Dwa badania Jol-Nar z rzędu: posiadacz może wziąć każdą z nich (po każdym okno)."""
    state = _state()
    state.players["p1"].technologies = ["nm", "sdn"]
    state.last_research = [
        {"player": "p1", "technology": "nm"}, {"player": "p1", "technology": "sdn"},
    ]
    options = jolnar.agreement_inputs(state, registry, "p2")[0]["options"]
    assert {o["value"] for o in options} == {"nm", "sdn"}


@ruling("F_jol_nar/research-agreement/2")
def test_ra_z_transakcji_tuz_po_badaniu(registry: StaticDataRegistry, grid: HexGrid) -> None:
    state = _state()
    _neighbors(state)
    state.players["p1"].private.promissory_notes = ["ra"]
    plan = technology.plan_research(state, registry, "p1", "nm", [])
    technology.apply_research(state, "p1", plan)
    give = TransactionSide(promissory_note="ra")
    traded = transaction.resolve_transaction(state, grid, "p2", give, TransactionSide())
    assert _ra_playable(traded, registry, "p2")  # transakcja to nie akcja - ślad badania trwa
    after, _ = promissory_play.play(traded, registry, "p2", "ra", {"technology": "nm"})
    assert "nm" in after.players["p2"].technologies
    # Druga transakcja z tym samym graczem w tej turze - niemożliwa.
    with pytest.raises(ValueError):
        transaction.validate_transaction(after, grid, "p2", give, TransactionSide())


@ruling("F_jol_nar/research-agreement/2.1", "promissory_notes:ra#2")
def test_ra_raz_na_jedno_badanie(registry: StaticDataRegistry, grid: HexGrid) -> None:
    """Notka wraca do Jol-Nar; przekazana trzeciemu graczowi nie da tej samej technologii."""
    state = _state()
    state.players["p3"] = PlayerState(player_id="p3", color="green", faction="hacan")
    state.seating_order = ["p1", "p2", "p3"]
    state.players["p1"].technologies = ["nm"]
    state.last_research = [{"player": "p1", "technology": "nm"}]
    state.players["p2"].private.promissory_notes = ["ra"]
    after, _ = promissory_play.play(state, registry, "p2", "ra", {"technology": "nm"})
    assert "ra" in after.players["p1"].private.promissory_notes
    after.players["p1"].private.promissory_notes = []
    after.players["p3"].private.promissory_notes = ["ra"]
    assert not _ra_playable(after, registry, "p3")
    with pytest.raises(ValueError):
        promissory_play.play(after, registry, "p3", "ra", {"technology": "nm"})


@ruling("F_jol_nar/research-agreement/2.2")
def test_ra_odzyskana_transakcja_dziala_przy_kolejnym_badaniu(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _state()
    _neighbors(state)
    state.active_player_id = "p2"
    state.players["p1"].technologies = ["nm"]
    state.last_research = [{"player": "p1", "technology": "nm"}]
    state.players["p2"].private.promissory_notes = ["ra"]
    played, _ = promissory_play.play(state, registry, "p2", "ra", {"technology": "nm"})
    back = transaction.resolve_transaction(
        played, grid, "p1", TransactionSide(), TransactionSide(promissory_note="ra"),
    )
    assert back.players["p2"].private.promissory_notes == ["ra"]
    plan = technology.plan_research(back, registry, "p1", "sdn", [])
    technology.apply_research(back, "p1", plan)
    assert _ra_playable(back, registry, "p2")
    final, _ = promissory_play.play(back, registry, "p2", "ra", {"technology": "sdn"})
    assert {"nm", "sdn"} <= set(final.players["p2"].technologies)


@ruling("F_jol_nar/research-agreement/4")
def test_ra_bez_generycznego_ulepszenia_gdy_wersja_frakcyjna(registry: StaticDataRegistry) -> None:
    """Sol ma Advanced Carrier II - nie dostaje Carrier II zbadanego przez Jol-Nar."""
    state = _state()
    state.players["p1"].technologies = ["cv2"]
    state.last_research = [{"player": "p1", "technology": "cv2"}]
    state.players["p2"].private.promissory_notes = ["ra"]
    assert not _ra_playable(state, registry, "p2")
    with pytest.raises(ValueError):
        promissory_play.play(state, registry, "p2", "ra", {"technology": "cv2"})


@ruling("F_jol_nar/research-agreement/5")
def test_ra_po_badaniu_spoza_karty_technology(registry: StaticDataRegistry) -> None:
    """Badanie z komponentu (okno badania: Divert Funding, Focused Research, Reveal Prototype,
    Wormhole Research, Enigmatic Device) i z agendy (Ixthian Artifact) zostawia ślad badania."""
    from src.core import research_offer

    state = _state()
    state.players["p2"].private.promissory_notes = ["ra"]
    payload = {"tech": "nm", "skips": [], "planets": [], "trade_goods": 0}
    research_offer.resolve(state, registry, "p1", {"params": {"research": payload}})
    assert _ra_playable(state, registry, "p2")
    rider = _state()
    rider.players["p2"].private.promissory_notes = ["ra"]
    agendas_directives.research_chosen(rider, "p1", ["sdn"])
    assert _ra_playable(rider, registry, "p2")


@ruling("F_jol_nar/research-agreement/5.1", "promissory_notes:ra#1")
def test_ra_nie_po_zdobyciu_bez_badania(registry: StaticDataRegistry) -> None:
    """„Gain” (Plagiarize, Research Grant Reallocation, Maw of Worlds, Fire of the Gashlai -
    wszystkie przez ``grant_technology``) nie jest badaniem."""
    state = _state()
    _neighbors(state)
    state.players["p1"].trade_goods = 5
    state.players["p2"].technologies = ["sdn"]
    state.players["p2"].private.promissory_notes = ["ra"]
    action_cards_economy.plagiarize(
        state, registry, "p1", {"technology": "sdn", "planets": [], "trade_goods": 5}
    )
    gained = technology.gain_technology(state, registry, "p1", "nm")
    assert {"sdn", "nm"} <= set(gained.players["p1"].technologies)
    assert gained.last_research == []
    assert not _ra_playable(gained, registry, "p2")


@ruling("F_jol_nar/research-agreement/5.2", "F_jol_nar/rin-the-masters-legacy-genetic-memory/1")
def test_genetic_memory_bez_prerekwizytow_i_bez_ra(registry: StaticDataRegistry) -> None:
    """Zamiana na X-89 ΩΩ (GGG) bez spełnienia prerekwizytów; to nie badanie - notka nieaktywna."""
    state = _state()
    state.players["p1"].technologies = ["nm"]
    state.players["p1"].leader_states = {"jolnarhero": "unlocked"}
    state.players["p2"].private.promissory_notes = ["ra"]
    after, _ = faction_components.play(
        state, registry, "p1", "leader", "jolnarhero", {"tech:nm": "x89c4"}
    )
    assert after.players["p1"].technologies == ["x89c4"]
    assert after.last_research == []
    assert not _ra_playable(after, registry, "p2")


# ================================================================================== Doctor Sucaban


@ruling("F_jol_nar/doctor-sucaban/1", "leaders:jolnaragent#1", "leaders:jolnaragent#2")
def test_sucaban_piechota_bez_infantry_ii(registry: StaticDataRegistry) -> None:
    """Zdjęta piechota Jol-Nar z Infantry II nie rzuca na odrodzenie (usunięta, nie zniszczona)."""
    state = _state()
    state.players["p1"].technologies = ["inf2"]
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 2}}}
    _secondary_window(state, "p1")
    used, _ = faction_components.play(state, registry, "p1", "leader", "jolnaragent")
    after = _accept(used, "p1", "Sucaban", {"inf:102:industrex": 2})
    assert "p1" not in after.systems["102"].planet_units.get("industrex", {}) or not (
        after.systems["102"].planet_units["industrex"]["p1"].get("infantry")
    )
    assert after.players["p1"].infantry_ii_on_card == 0
    assert technology.research_discount(after, "p1") == 2


# ===================================================================================== Agnlan Oln


@ruling("F_jol_nar/ta-zern-agnlan-oln/3")
def test_agnlan_nie_dla_rzutow_combat(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"jolnarcommander": "unlocked"}
    state.systems["102"].space_units = {"p1": {"cruiser": 1}, "p2": {"cruiser": 1}}
    state.active_combat = ActiveCombat(
        kind="space", position="102", attacker="p1", defender="p2", step=CombatStep.ASSIGN,
        rolls={"p1": [{"baseType": "cruiser", "dice": [3], "hitsOn": 7, "modifier": -1}]},
    )
    assert jolnar.pending_unit_roll(state, "p1") is None
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p1")}
    assert rows["jolnarcommander"]["playable"] is False


@ruling("F_jol_nar/ta-zern-agnlan-oln/4")
def test_agnlan_nie_dla_infantry_ii(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"jolnarcommander": "unlocked"}
    state.players["p1"].technologies = ["inf2"]
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 3}}}
    unit_ops.remove_units(
        state, state.systems["102"], "industrex", "p1", "infantry", 3, UnitCause.DESTROYED
    )
    assert not any("Agnlan" in o.label for o in state.pending_offers)
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p1")}
    assert rows["jolnarcommander"]["playable"] is False


# ================================================================================ Genetic Memory


@ruling("F_jol_nar/rin-the-masters-legacy-genetic-memory/2", "leaders:jolnarhero#1")
def test_genetic_memory_zamiany_jednoczesne(registry: StaticDataRegistry) -> None:
    """Zwracana ani inna posiadana technologia nie jest celem zamiany; bez ulepszeń jednostek."""
    state = _state()
    state.players["p1"].technologies = ["nm", "hm", "cv2"]
    inputs = {i["key"]: i for i in jolnar.hero_inputs(state, registry, "p1")}
    assert set(inputs) == {"tech:nm", "tech:hm"}
    targets = {o["value"] for o in inputs["tech:nm"]["options"]}
    assert "nm" not in targets and "hm" not in targets and "keep" in targets
    state.players["p1"].leader_states = {"jolnarhero": "unlocked"}
    with pytest.raises(ValueError):  # ta sama technologia nie zastąpi dwóch
        faction_components.play(
            state, registry, "p1", "leader", "jolnarhero", {"tech:nm": "x89c4", "tech:hm": "x89c4"}
        )


@ruling("F_jol_nar/rin-the-masters-legacy-genetic-memory/3", "leaders:jolnarhero#2")
def test_genetic_memory_zwrocona_wraca_gotowa(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["sdn"]
    state.players["p1"].exhausted_technologies = ["sdn"]
    state.players["p1"].leader_states = {"jolnarhero": "unlocked"}
    after, _ = faction_components.play(
        state, registry, "p1", "leader", "jolnarhero", {"tech:sdn": "st"}
    )
    assert leaders.state_of(after, registry, "p1", "jolnarhero") == leaders.PURGED
    assert "sdn" not in after.players["p1"].exhausted_technologies
    regained = technology.gain_technology(after, registry, "p1", "sdn")
    assert "sdn" in regained.players["p1"].technologies
    assert "sdn" not in regained.players["p1"].exhausted_technologies


@ruling("leaders:jolnarhero#unlock")
def test_rin_odblokowanie(registry: StaticDataRegistry) -> None:
    fn = leaders.unlock_predicate(registry, jolnar.HERO)
    assert fn is not None
    state = _state()
    state.players["p1"].scored_secrets = ["a", "b"]
    assert not fn(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert fn(state, registry, "p1")


# =========================================================================== Specialist Compounds


def _compound(state: GameState, registry: StaticDataRegistry, payload: dict[str, Any]) -> str:
    return technology_card._research_with_cost(
        state, CardContext(registry, None), "p1", payload, technology_card.SECOND_RESEARCH_COST
    )


def _compound_state() -> GameState:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.systems["102"].planet_owners = {"industrex": "p1"}  # WARFARE
    state.systems["105"].planet_owners = {"wellon": "p1"}  # CYBERNETIC
    return state


@ruling("F_jol_nar/specialized-compounds/3")
def test_compounds_nie_dla_ulepszen(registry: StaticDataRegistry) -> None:
    state = _compound_state()
    state.players["p1"].technologies = ["ps", "asc"]  # dd2 wymaga RR
    with pytest.raises(ValueError, match="unit upgrade"):
        _compound(state, registry, {"tech": "dd2", "compound_planet": "industrex"})


@ruling("F_jol_nar/specialized-compounds/2", "breakthroughs:jolnarbt#2")
def test_compounds_kolor_nawet_bez_prerekwizytow(registry: StaticDataRegistry) -> None:
    """Plasma Scoring (bez prerekwizytów) i GLS (jedyny Y zignorowany Analytical) - kolor musi
    się zgadzać z planetą."""
    state = _compound_state()
    with pytest.raises(ValueError, match="color"):
        _compound(state, registry, {"tech": "gls", "compound_planet": "industrex"})
    with pytest.raises(ValueError, match="color"):
        _compound(state, registry, {"tech": "sdn", "compound_planet": "industrex"})
    assert _compound(state, registry, {"tech": "ps", "compound_planet": "industrex"}) == "ps"


@ruling("F_jol_nar/specialized-compounds/5")
def test_compounds_ta_sama_planeta_nie_placi_i_nie_pomija(registry: StaticDataRegistry) -> None:
    """Assault Cannon (RRR): Plasma Scoring + Analytical + Industrex jako skip - nie zapłaci nią."""
    state = _compound_state()
    state.players["p1"].technologies = ["ps"]
    with pytest.raises(ValueError, match="both"):
        _compound(state, registry, {
            "tech": "asc", "skips": ["industrex"], "compound_planet": "industrex",
        })


@ruling("breakthroughs:jolnarbt#1", "F_jol_nar/specialized-compounds/1")
def test_compounds_synergia_zolty_zielony(registry: StaticDataRegistry) -> None:
    """Wyczerpana planeta wiąże kolor badania z jej specjalnością („you must research a technology
    of that color”), a synergia przełomu (zielony/żółty) czyni oba kolory wymiennymi (ruling 1,
    zrzut 2026-11-22 - wcześniej zakazane): Wellon (żółta) płaci za zieloną i za żółtą
    technologię; Industrex (czerwona, poza parą synergii) za żółtą - nie."""
    state = _compound_state()
    assert "BIOTIC" in technology.specialty_payment_planets(state, registry, "p1")["wellon"]
    with pytest.raises(ValueError, match="color"):
        _compound(state, registry, {"tech": "sdn", "compound_planet": "industrex"})
    assert _compound(state, registry, {"tech": "nm", "compound_planet": "wellon"}) == "nm"
    state.players["p1"].exhausted_planets.remove("wellon")
    assert _compound(state, registry, {"tech": "sdn", "compound_planet": "wellon"}) == "sdn"
    assert "wellon" in state.players["p1"].exhausted_planets
    assert state.players["p1"].trade_goods == 3
    with pytest.raises(ValueError):  # gracz bez przełomu Jol-Nar nie płaci planetą
        technology.validate_specialty_payment(
            state, registry, "p2", technology.ResearchPlan("ps", (), False), "industrex"
        )
