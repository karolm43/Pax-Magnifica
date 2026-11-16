"""The Yin Brotherhood — rulingi ``docs/rules_tirules/F_yin.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Podstawowe testy komponentów są w ``test_yin.py`` i
``test_flows_yin.py`` (tam też część znaczników). Statusy bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import battle, leaders, technology, transaction, triggers, unit_ops
from src.core.game_events import GameEvent, Moment
from src.core.game_state import ActiveCombat, CombatStep, GameState, ProductionGrant
from src.core.hooks.factions import yin
from src.core.production import ProductionOrder
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.transaction import TransactionSide
from src.core.unit_ops import UnitCause
from tests.factions.flow_harness import Flow
from tests.factions.test_flows_yin import _assign, _devotion_ready
from tests.factions.test_yin import _ground, _planet, _state
from tests.factions.test_yin import registry as registry  # noqa: F401 - fixture modułu
from tests.rulings import ruling

_TILE = "26"  # zwykły kafel z jedną planetą (Lodor)


def _labels(state: GameState, player: str) -> list[str]:
    return [o.label for o in state.pending_offers if o.player_id == player]


def _accept(
    state: GameState, player: str, label_part: str, params: dict[str, Any] | None = None
) -> GameState:
    offer = next(
        o for o in state.pending_offers if o.player_id == player and label_part in o.label
    )
    return triggers.accept_offer(state, player, offer.id, params)


def _combat_pending(flow: Flow) -> bool:
    return bool(flow.client.get("/tactical/invasion").json()["combatPlanets"])


def _combat_start(state: GameState) -> None:
    combat = state.active_combat
    assert combat is not None
    triggers.fire(
        state, GameEvent.COMBAT, Moment.START, subject=combat.attacker,
        ctx={"kind": combat.kind, "position": combat.position, "planet": combat.planet or "",
             "attacker": combat.attacker, "defender": combat.defender},
    )


# ================================================================================ Indoctrination


@ruling("F_yin/indoctrination/1", "F_yin/indoctrination/2", "abilities:indoctrination#1")
def test_indoctrination_raz_na_walke_i_na_kazdej_walce(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].trade_goods = 6
    _ground(state, registry, {"infantry": 2})
    _combat_start(state)
    assert _labels(state, "p1") == ["Indoctrination"]
    state = _accept(state, "p1", "Indoctrination", {"unit": "infantry", "trade_goods": 2})
    planet = _planet(registry, "21")
    here = state.systems["102"].planet_units[planet]
    assert here["p2"]["infantry"] == 1 and here["p1"]["infantry"] == 3  # zastąpienie, nie rzut
    assert state.players["p1"].trade_goods == 4
    assert "Indoctrination" not in _labels(state, "p1")  # raz na walkę: jedna oferta na start
    # Kolejna walka naziemna tej inwazji (inna planeta) - znów start walki, znów oferta.
    other = _planet(registry, "20")
    state.systems["101"].planet_units = {other: {"p1": {"infantry": 1}, "p2": {"infantry": 1}}}
    state.active_combat = ActiveCombat(
        kind="ground", position="101", planet=other, attacker="p1", defender="p2",
    )
    _combat_start(state)
    assert "Indoctrination" in _labels(state, "p1")


@ruling("F_yin/indoctrination/3", "F_yin/indoctrination/3.1")
def test_indoctrination_nie_bez_piechoty_przeciwnika(registry: StaticDataRegistry) -> None:
    """Same mechy albo same myśliwce (Matriarch Naalu) po stronie przeciwnika - brak celu."""
    state = _state(registry)
    state.players["p1"].trade_goods = 3
    _ground(state, registry, {"mech": 2})
    assert not yin._indoctrination_ready(state, "p1", {"kind": "ground"})
    _ground(state, registry, {"fighter": 2})
    assert not yin._indoctrination_ready(state, "p1", {"kind": "ground"})
    _ground(state, registry, {"fighter": 2, "infantry": 1})
    assert yin._indoctrination_ready(state, "p1", {"kind": "ground"})


@ruling("F_yin/indoctrination/4")
def test_indoctrination_ostatnia_sila_przeciwnika_przegrywa_od_razu(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry)
    state.players["p1"].trade_goods = 2
    _ground(state, registry, {"infantry": 1})
    yin.indoctrination(state, "p1", {"params": {"unit": "infantry", "trade_goods": 2}})
    after = battle.roll_round(state, grid_from_state(state, registry), registry)
    combat = after.active_combat
    assert combat is not None and combat.step is CombatStep.DONE
    assert combat.winner == "p1" and combat.log == []  # bez rzutu i bez zdolności „start”


# =============================================================================== Moyin's Ashes


@ruling("F_yin/moyins-ashes/1", "F_yin/moyins-ashes/2", "F_yin/moyins-ashes/3")
def test_moyins_ashes_z_rezerwy_za_piechote_i_trzy_wplywu(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _ground(state, registry, {"infantry": 1, "mech": 1})
    # Jedna planeta z wpływem >= 3 wystarcza na cały koszt (2 + 1).
    rich = next(
        p for p, d in registry.planets.items()
        if (d.influence or 0) >= 3 and p != "mr"
    )
    state.systems["101"].planet_owners[rich] = "p1"
    state.players["p1"].controlled_planets.append(rich)
    assert yin._indoctrination_types(state, "p1") == ["infantry", "mech"]
    state.players["p1"].trade_goods = 2
    with pytest.raises(ValueError, match="at least 3"):
        yin.indoctrination(state, "p1", {"params": {"unit": "mech", "trade_goods": 2}})
    yin.indoctrination(state, "p1", {"params": {"unit": "mech", "planets": [rich]}})
    planet = _planet(registry, "21")
    here = state.systems["102"].planet_units[planet]
    assert here["p2"].get("infantry", 0) == 0
    assert here["p2"].get("mech") == 1  # zastąpić można tylko piechotę - mech rywala zostaje
    assert here["p1"]["mech"] == 1
    # Wszystkie 4 mechy na planszy - DEPLOY niemożliwy (tylko z rezerwy).
    state.systems["101"].planet_units = {_planet(registry, "20"): {"p1": {"mech": 3}}}
    assert yin._indoctrination_types(state, "p1") == ["infantry"]


@ruling("F_yin/moyins-ashes/1.1")
def test_moyins_ashes_zniszczony_wraca_do_rezerwy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].trade_goods = 3
    planet = _planet(registry, "20")
    state.systems["101"].planet_units = {planet: {"p1": {"mech": 4}}}
    assert yin._indoctrination_types(state, "p1") == ["infantry"]
    unit_ops.remove_units(
        state, state.systems["101"], planet, "p1", "mech", 1, UnitCause.DESTROYED
    )
    assert "mech" in yin._indoctrination_types(state, "p1")  # kolejna walka tej inwazji


# ==================================================================================== Devotion


@ruling("F_yin/devotion/1.1", "F_yin/brother-omar-omega/1", "leaders:yincommander#unlock")
def test_devotion_cel_tylko_wrogi_i_odblokowuje_omara(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    _devotion_ready(flow, {"dreadnought": 1}, {})
    offer = flow.offer("Devotion")
    own = {o["value"] for o in offer["inputs"][0]["options"]}
    targets = {o["value"] for o in offer["inputs"][1]["options"]}
    assert own == {"cruiser"} and targets == {"dreadnought"}  # krążowniki Yin nie są celem
    assert flow.state()["players"][flow.me]["leader_states"].get("yincommander") != "unlocked"
    flow.accept("Devotion", {"ship": "cruiser", "target": "dreadnought"})
    assert flow.state()["players"][flow.me]["leader_states"]["yincommander"] == "unlocked"


@ruling("F_yin/devotion/2")
def test_devotion_trafienie_anuluje_shields_holding(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    position = _devotion_ready(flow, {"dreadnought": 2}, {})
    flow.player(lambda p: p["private"].update(action_cards=["sh1"]), flow.other)
    flow.accept("Devotion", {"ship": "cruiser", "target": "dreadnought"})
    flow.decline_all()
    assert flow.battle()["assigning"] == "sol"
    rows = flow.client.get("/action-card/playable", params={"player_id": flow.other}).json()
    row = next(r for r in rows["cards"] if r["card_id"] == "sh1")
    assert row["playable"], row["reason"]
    flow.post("/action-card/play", {
        "player_id": flow.other, "card_id": "sh1", "params": {"count": 1},
    })
    flow.finish_hold()
    assert flow.state()["systems"][position]["space_units"][flow.other]["dreadnought"] == 2


@ruling("F_yin/devotion/4")
def test_devotion_i_exotrireme_kolejnosc_od_atakujacego(registry: StaticDataRegistry) -> None:
    """Koniec rundy: Yin (atakujący) rozstrzyga przed N'orr (obrońca) - kolejka okna REACTION."""
    state = _state(registry)
    state.players["p2"].faction = "sardakk"
    state.players["p2"].technologies = ["exo2"]
    state.systems["102"].space_units = {
        "p1": {"cruiser": 2}, "p2": {"dreadnought": 2, "destroyer": 1},
    }
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1", defender="p2")
    triggers.fire(
        state, GameEvent.COMBAT_ROUND, Moment.END,
        ctx={"kind": "space", "round": 1, "position": "102", "planet": "", "attacker": "p1",
             "defender": "p2", "phase": "combat", "sustained": {}},
    )
    assert "Devotion" in _labels(state, "p1") and "Exotrireme II" in _labels(state, "p2")
    window = state.pending_window
    assert window is not None and window.queue == ["p1", "p2"]
    with pytest.raises(ValueError, match="turn to respond"):
        _accept(state, "p2", "Exotrireme II", {"ships": ["cruiser"]})


# ================================================================================ Impulse Core


@ruling("F_yin/impulse-core/1", "F_yin/impulse-core/2", "technologies:ic#2")
def test_impulse_core_przeciwnik_wybiera_i_moze_sustain(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    flow.player(lambda p: p["technologies"].append("ic"))
    position = flow.space_combat({"cruiser": 2}, {"dreadnought": 1, "destroyer": 1})
    flow.accept("Impulse Core", {"ship": "cruiser"})
    flow.decline_all()
    view = flow.battle()
    assert view["step"] == "ASSIGN" and view["assigning"] == "sol"
    _assign(flow, "sol", "sustain", "dreadnought")  # Sustain Damage anuluje trafienie
    theirs = flow.state()["systems"][position]["space_units"][flow.other]
    assert theirs == {"dreadnought": 1, "destroyer": 1}


@ruling("F_yin/impulse-core/3", "technologies:ic#1")
def test_impulse_core_przed_afb(registry: StaticDataRegistry) -> None:
    """Zniszczony Impulse Core niszczyciel nie rzuca anti-fighter barrage."""
    flow = Flow(registry, "yin")
    flow.player(lambda p: p["technologies"].append("ic"))
    flow.space_combat(
        {"cruiser": 2, "carrier": 1, "fighter": 3}, {"destroyer": 1, "carrier": 1, "fighter": 1}
    )
    assert flow.battle()["step"] != "AFB"  # oferta Impulse Core przed krokiem AFB
    flow.accept("Impulse Core", {"ship": "cruiser"})
    flow.decline_all()
    _assign(flow, "sol", "destroy", "destroyer")
    flow.decline_all()
    view = flow.battle()
    assert not (view.get("afb") or {}).get("sol")  # nikt po stronie Sol nie rzucał AFB


# ============================================================================= Greyfire Mutagen Ω


def _greyfire_combat(registry: StaticDataRegistry) -> GameState:
    """p2 (Sol, aktywny) atakuje planetę Letnev (p3) - Yin (p1) nie walczy."""
    from src.core.game_state import PlayerState

    state = _state(registry)
    state.players["p3"] = PlayerState(player_id="p3", color="red", faction="letnev")
    state.seating_order = ["p1", "p2", "p3"]
    state.active_player_id = "p2"
    planet = _planet(registry, "21")
    state.systems["102"].planet_units = {
        planet: {"p2": {"infantry": 2}, "p3": {"infantry": 2}},
    }
    state.active_combat = ActiveCombat(
        kind="ground", position="102", planet=planet, attacker="p2", defender="p3",
    )
    state.players["p1"].private.promissory_notes = ["greyfire"]
    return state


@ruling("F_yin/greyfire-mutagen-omega/1", "F_yin/greyfire-mutagen-omega/1.1",
        "F_yin/greyfire-mutagen-omega/1.2")
def test_greyfire_w_transakcji_w_trakcie_walki(registry: StaticDataRegistry) -> None:
    state = _greyfire_combat(registry)
    grid = grid_from_state(state, registry)
    window = OpenWindow(GameEvent.COMBAT, Moment.START, {})
    note = TransactionSide(promissory_note="greyfire")
    # Obrońca (nieaktywny) nie zawiera transakcji - nie dostanie notki.
    with pytest.raises(ValueError, match="turn"):
        transaction.validate_transaction(state, grid, "p1", TransactionSide(), note, "p3")
    state.systems["101"].space_units = {"p2": {"carrier": 1}}  # sąsiedztwo z Yin
    state.systems["103"].space_units = {"p1": {"carrier": 1}}
    after = transaction.resolve_transaction(state, grid, "p1", TransactionSide(), note, "p2")
    assert after.active_combat is not None  # transakcja w trakcie walki
    assert "greyfire" in after.players["p2"].private.promissory_notes
    assert yin._greyfire_condition(after, registry, "p2", window) is None  # od razu zagrywalna
    with pytest.raises(ValueError, match="already made a transaction"):
        transaction.validate_transaction(
            after, grid, "p1", TransactionSide(trade_goods=0), TransactionSide(trade_goods=0),
            "p2",
        )


@ruling("F_yin/greyfire-mutagen-omega/1.3", "F_yin/greyfire-mutagen-omega/1.4",
        "promissory_notes:greyfire#1")
def test_greyfire_nie_drugi_raz_w_tej_samej_walce(registry: StaticDataRegistry) -> None:
    state = _greyfire_combat(registry)
    window = OpenWindow(GameEvent.COMBAT, Moment.START, {})
    assert yin._greyfire_condition(state, registry, "p2", window) is None
    yin.greyfire_mutagen(state, registry, "p2", {})
    planet = _planet(registry, "21")
    assert state.systems["102"].planet_units[planet]["p3"]["infantry"] == 1
    state.systems["102"].planet_units[planet]["p3"]["infantry"] = 2  # nadal >= 2 siły
    # Odzyskana (transakcja) notka nie wraca do tej samej walki.
    assert yin._greyfire_condition(state, registry, "p2", window) is not None
    with pytest.raises(ValueError):
        yin.greyfire_mutagen(state, registry, "p2", {})
    # Kolejna walka naziemna tej inwazji: znów wolno.
    other = _planet(registry, "20")
    state.systems["101"].planet_units = {other: {"p2": {"infantry": 1}, "p3": {"infantry": 2}}}
    state.active_combat = ActiveCombat(
        kind="ground", position="101", planet=other, attacker="p2", defender="p3",
    )
    assert yin._greyfire_condition(state, registry, "p2", window) is None


# ============================================================================== Yin Spinner Ω


@ruling("F_yin/yin-spinner-omega/2")
def test_spinner_po_produkcji_z_karty(registry: StaticDataRegistry) -> None:
    """Produkcja z efektu (bez PRODUCTION jednostek) też wyzwala Yin Spinner Ω."""
    from src.core import production

    state = _state(registry)
    state.players["p1"].technologies = ["yso"]
    state.players["p1"].trade_goods = 5
    state.active_system = "101"
    state.production_grant = ProductionGrant(
        player_id="p1", position="101", units=1, free=True, source="test",
    )
    after = production.produce(
        state, grid_from_state(state, registry), registry, "p1",
        [ProductionOrder(base_type="infantry", count=1, zone=_planet(registry, "20"))],
    )
    assert "Yin Spinner" in _labels(after, "p1")


@ruling("F_yin/yin-spinner-omega/1", "technologies:yso#1")
def test_spinner_obie_piechoty_razem(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies = ["yso"]
    planet = _planet(registry, "20")
    inputs = yin.spinner_inputs(state, registry, "p1", {})
    assert [i["key"] for i in inputs] == ["where", "count"]  # jedno miejsce na obie
    yin.yin_spinner(state, "p1", {"player": "p1", "params": {"where": f"101|{planet}",
                                                               "count": 2}})
    assert state.systems["101"].planet_units[planet]["p1"]["infantry"] == 2
    with pytest.raises(ValueError):
        yin.yin_spinner(state, "p1", {"params": {"where": "102|space", "count": 1}})


# ================================================================================== Van Hauge


@ruling("F_yin/van-hauge/1")
def test_van_hauge_nie_niszczy_floating_factory(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p2"].faction = "saar"
    system = state.systems["102"]
    system.space_units = {"p1": {"flagship": 1}, "p2": {"carrier": 1, "spacedock": 1}}
    unit_ops.remove_units(state, system, "space", "p1", "flagship", 1, UnitCause.DESTROYED)
    assert system.space_units["p2"].get("carrier", 0) == 0
    assert system.space_units["p2"]["spacedock"] == 1


@ruling("F_yin/van-hauge/3")
def test_van_hauge_walka_konczy_sie_remisem(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    system = state.systems["102"]
    system.space_units = {"p1": {"flagship": 1}, "p2": {"destroyer": 2}}
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1", defender="p2")
    unit_ops.remove_units(state, system, "space", "p1", "flagship", 1, UnitCause.DESTROYED)
    triggers.drop_all_offers(state)  # Brother Milor nie gotowy (brak agenta) - bez ofert
    grid = grid_from_state(state, registry)
    after = battle._finish_round(state, grid, registry)
    combat = after.active_combat
    assert combat is not None and combat.step is CombatStep.DONE
    assert combat.outcome == "draw" and combat.winner is None


# ============================================================================= Brother Milor Ω


def _milor_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry)
    state.players["p1"].leader_states = {"yinagent": "unlocked"}
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1", defender="p2")
    return state


@ruling("F_yin/brother-milor-omega/4", "F_yin/brother-milor-omega/2",
        "F_yin/brother-milor-omega/2.1", "leaders:yinagent#1")
def test_milor_po_van_hauge_yin_wygrywa(registry: StaticDataRegistry) -> None:
    state = _milor_state(registry)
    system = state.systems["102"]
    system.space_units = {"p1": {"flagship": 1}, "p2": {"destroyer": 1}}
    unit_ops.remove_units(state, system, "space", "p1", "flagship", 1, UnitCause.DESTROYED)
    assert not system.space_units.get("p2", {}).get("destroyer")
    flagship = next(
        o for o in state.pending_offers
        if o.player_id == "p1" and o.ctx.get("base_type") == "flagship"
    )
    state = triggers.accept_offer(state, "p1", flagship.id, {})
    triggers.drop_all_offers(state)
    assert state.systems["102"].space_units["p1"]["fighter"] == 2
    after = battle._finish_round(state, grid_from_state(state, registry), registry)
    combat = after.active_combat
    assert combat is not None and combat.step is CombatStep.DONE and combat.winner == "p1"


@ruling("F_yin/brother-milor-omega/3")
def test_milor_mysliwce_bez_wolnej_pojemnosci(registry: StaticDataRegistry) -> None:
    state = _milor_state(registry)
    system = state.systems["102"]
    system.space_units = {"p1": {"cruiser": 1}, "p2": {"destroyer": 1, "fighter": 0}}
    yin.brother_milor(state, "p1", {
        "player": "p2", "base_type": "destroyer", "zone": "space", "position": "102",
    })
    # Pojemność nie jest sprawdzana w walce (sprawdza ją koniec walki - reguła ogólna).
    assert system.space_units["p2"]["fighter"] == 2


@ruling("F_yin/brother-milor-omega/5", "F_yin/brother-milor-omega/5.1")
def test_milor_nadwyzka_trafien_przepada(registry: StaticDataRegistry) -> None:
    """Trafienia ponad liczbę jednostek nie przechodzą na nowo postawione myśliwce: wymagane
    trafienia liczy się z jednostek strony w chwili przypisania."""
    state = _milor_state(registry)
    system = state.systems["102"]
    system.space_units = {"p1": {"cruiser": 3}, "p2": {"destroyer": 1}}
    combat = state.active_combat
    assert combat is not None
    combat.step = CombatStep.ASSIGN
    combat.pending_hits = {"p2": 3}
    grid = grid_from_state(state, registry)
    assert battle.required_hits(state, grid, registry, "p2") == 1
    yin.brother_milor(state, "p1", {
        "player": "p2", "base_type": "destroyer", "zone": "space", "position": "102",
    })
    unit_ops.remove_units(state, system, "space", "p2", "destroyer", 1, UnitCause.DESTROYED)
    combat.pending_hits = {}  # przypisanie zamknięte - nadwyżka przepadła
    assert system.space_units["p2"]["fighter"] == 2


@ruling("F_yin/brother-milor-omega/6")
def test_milor_turn_their_fleets_to_dust_przed_mysliwcami(registry: StaticDataRegistry) -> None:
    from src.core.game_state import TacticalStep, TimingWindow, WindowType

    state = _milor_state(registry)
    state.active_combat = None
    state.active_system = "102"
    state.tactical_step = TacticalStep.SPACE_CANNON
    state.pending_window = TimingWindow(
        window_type=WindowType.SPACE_CANNON, queue=["p1"], context={"roller": "p1"},
    )
    state.players["p1"].private.secret_objectives = ["ttfd"]
    system = state.systems["102"]
    system.space_units = {"p2": {"destroyer": 1}}
    unit_ops.remove_units(state, system, "space", "p2", "destroyer", 1, UnitCause.DESTROYED)
    assert "ttfd" in state.players["p1"].scored_secrets  # przed postawieniem myśliwców
    assert yin._milor_ready(state, "p1", {
        "player": "p2", "base_type": "destroyer", "zone": "space", "position": "102",
    })


@ruling("F_yin/brother-milor-omega/7")
def test_milor_make_an_example_przed_piechota(registry: StaticDataRegistry) -> None:
    from src.core.game_state import InvasionPhase, InvasionState

    state = _milor_state(registry)
    state.active_combat = None
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.BOMBARDMENT)
    state.players["p1"].private.secret_objectives = ["mew"]
    planet = _planet(registry, "21")
    system = state.systems["102"]
    system.planet_units = {planet: {"p2": {"infantry": 1}}}
    unit_ops.remove_units(state, system, planet, "p2", "infantry", 1, UnitCause.DESTROYED)
    assert "mew" in state.players["p1"].scored_secrets
    assert yin._milor_ready(state, "p1", {
        "player": "p2", "base_type": "infantry", "zone": planet, "position": "102",
    })


# ============================================================================= Brother Omar Ω


@ruling("F_yin/brother-omar-omega/2", "F_yin/brother-omar-omega/2.1")
def test_omar_nie_daje_ulepszenia_frakcyjnego_ani_ogolnego_przez_nie(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry)
    planet = _planet(registry, "20")
    state.systems["101"].planet_units = {planet: {"p1": {"infantry": 2}}}
    state.players["p1"].leader_states = {"yincommander": "unlocked"}
    sol_upgrade = next(
        t for t, d in registry.technologies.items()
        if d.faction == "sol" and (d.base_upgrade or "") == "inf2"
    )
    state.players["p2"].technologies = [sol_upgrade]
    skip = f"{technology.INFANTRY_SKIP_PREFIX}101|{planet}"
    # Ulepszenie frakcyjne Sol nie otwiera ogólnego Infantry II (to inna technologia).
    with pytest.raises(ValueError, match="another player owns"):
        technology.plan_research(state, registry, "p1", "inf2", [skip])
    # Samej technologii frakcyjnej innej frakcji nie bada nikt (także z notką Alliance).
    with pytest.raises(ValueError):
        technology.plan_research(state, registry, "p1", sol_upgrade, [skip])


@ruling("leaders:yincommander#1")
def test_omar_zielony_prerekwizyt_zawsze(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states = {"yincommander": "unlocked"}
    tech = registry.technologies["dxa"]
    assert not technology.missing_prerequisites(state, registry, "p1", tech)


# ===================================================================== Quantum Dissemination Ω


@ruling("leaders:yinhero#unlock")
def test_dannel_odblokowanie_trzy_cele(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states = {"yinhero": "locked"}
    state.players["p1"].scored_secrets = ["a", "b"]
    leaders.refresh_unlocks(state, registry)
    assert state.players["p1"].leader_states["yinhero"] == "locked"
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    leaders.refresh_unlocks(state, registry)
    assert state.players["p1"].leader_states["yinhero"] == "unlocked"


@ruling("F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/4.1")
def test_dissemination_bez_sil_z_orbity(registry: StaticDataRegistry) -> None:
    from src.core import invasion

    state = _state(registry)
    planet = _planet(registry, "21")
    state.systems["102"].space_units = {"p1": {"carrier": 1, "infantry": 2}}
    yin.quantum_dissemination(
        state, registry, "p1", {"planet1": f"102|{planet}", "planet2": "none", "planet3": "none"},
    )
    with pytest.raises(ValueError, match="cannot be committed"):
        invasion.commit_ground_forces(state, registry, {planet: {"infantry": 1}})


@ruling("leaders:yinhero#1", "leaders:yinhero#2", "leaders:yinhero#3",
        "F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/1",
        "F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/3",
        "F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/5",
        "F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/6")
def test_dissemination_przejmuje_kontrole_przez_api(registry: StaticDataRegistry) -> None:
    """Błąd zgłoszony przez użytkownika: po bohaterze nie działało przejęcie kontroli. Planeta
    bez obrońców była „prostą” inwazją (panel kroku INVASION, którego bez akcji taktycznej nie
    ma) - teraz inwazja komponentu zawsze idzie pełnym oknem aż do Establish Control."""
    flow = Flow(registry, "yin")
    empty, defended = flow.plain_pair()
    flow.set_tile(empty, _TILE)
    flow.set_tile(defended, "25")
    free_planet, enemy_planet = flow.planets(empty)[0], flow.planets(defended)[0]
    flow.ground(defended, enemy_planet, flow.other, {"infantry": 1, "pds": 1})
    flow.ground(empty, free_planet, flow.other, {})  # planeta rywala bez obrońców: bez eksploracji
    flow.player(lambda p: p["leader_states"].update(yinhero="unlocked"))
    flow.player(lambda p: p.update(trade_goods=4))
    tokens = flow.state()["players"][flow.me]["tactical_cc"]
    flow.use("leader", "yinhero", {
        "planet1": f"{empty}|{free_planet}", "planet2": f"{defended}|{enemy_planet}",
        "planet3": f"{defended}|{enemy_planet}",
    })
    state = flow.state()
    assert state["players"][flow.me]["leader_states"]["yinhero"] == "purged"
    assert state["players"][flow.me]["tactical_cc"] == tokens  # bez aktywacji systemów
    assert state["active_system"] is None
    view = flow.client.get("/tactical/invasion").json()
    assert view["simple"] is False and view["source"] == "leaders:yinhero"
    assert view["cargo"] == []
    first = state["invasion"]["position"]
    for _ in range(12):
        state = flow.state()
        inv = state["invasion"]
        if inv is None:
            break
        if inv["phase"] == "GROUND_COMBAT" and _combat_pending(flow):
            assert not flow.client.get("/tactical/invasion").json()["defense"]  # bez SCD
            flow.post("/tactical/battle/start", {"planet": enemy_planet})
            if flow.has_offer("Indoctrination"):
                flow.accept("Indoctrination", {"unit": "infantry", "trade_goods": 2})
            flow.fight()
            flow.post("/tactical/battle/close")
            continue
        flow.post("/tactical/invasion/next")
    state = flow.state()
    assert first == min(empty, defended) and state["invasion"] is None
    assert state["systems"][empty]["planet_owners"][free_planet] == flow.me
    assert state["systems"][defended]["planet_owners"][enemy_planet] == flow.me
    assert state["systems"][defended]["planet_units"][enemy_planet][flow.me]["infantry"] >= 1


@ruling("F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/2")
def test_dissemination_mallice_przed_odwroceniem(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    position, _ = flow.plain_pair()
    flow.set_tile(position, "82a")
    flow.player(lambda p: p["leader_states"].update(yinhero="unlocked"))
    flow.use("leader", "yinhero", {
        "planet1": f"{position}|lockedmallice", "planet2": "none", "planet3": "none",
    })
    state = flow.state()
    assert state["systems"][position]["system_id"] == "82b"  # nexus odwrócony
    assert state["invasion"]["committed"] == {"mallice": {"infantry": 1}}
    for _ in range(4):
        if flow.state()["invasion"] is None:
            break
        if flow.state()["exploration"] is not None:  # karta eksploracji nieistotna
            flow.client.post("/god-mode/patch", json={"exploration": None})
            continue
        flow.post("/tactical/invasion/next")
    assert flow.state()["systems"][position]["planet_owners"]["mallice"] == flow.me


@ruling("F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/4")
def test_dissemination_wszystkie_ladowania_przed_walkami(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    a, b = _planet(registry, "20"), _planet(registry, "21")
    state.systems["102"].planet_units = {b: {"p2": {"infantry": 1}}}
    state.systems["102"].planet_owners = {b: "p2"}
    yin.quantum_dissemination(
        state, registry, "p1", {"planet1": f"101|{a}", "planet2": f"102|{b}", "planet3": "none"},
    )
    assert state.invasion is not None and state.invasion.position == "101"
    # Drugi system jeszcze czeka w kolejce, a piechota już tam stoi (przed walką).
    assert state.systems["102"].planet_units[b]["p1"]["infantry"] == 1
    assert state.active_combat is None


@ruling("F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/7",
        "F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/7.1",
        "F_yin/dannel-of-the-tenth-omega-quantum-dissemination-omega/7.2")
def test_dissemination_parley(registry: StaticDataRegistry) -> None:
    from src.core.hooks import reactions_invasion

    planet = _planet(registry, "21")
    for ships, expected_space in (({}, 0), ({"carrier": 1}, 2)):
        state = _state(registry)
        state.systems["102"].planet_owners = {planet: "p2"}
        state.systems["102"].planet_units = {planet: {"p2": {"infantry": 1}}}
        state.systems["102"].space_units = {"p1": dict(ships)} if ships else {}
        state.players["p2"].private.action_cards = ["parley"]
        yin.quantum_dissemination(
            state, registry, "p1",
            {"planet1": f"102|{planet}", "planet2": f"102|{planet}", "planet3": "none"},
        )
        options = reactions_invasion.parley_inputs(state, registry, "p2")[0]["options"]
        assert [o["value"] for o in options] == [planet]
        reactions_invasion.parley(state, registry, "p2", {"planet": planet})
        system = state.systems["102"]
        assert system.planet_units[planet].get("p1", {}).get("infantry", 0) == 0
        assert system.space_units.get("p1", {}).get("infantry", 0) == expected_space


# ===================================================================================== Mecatol


@ruling("leaders:yinhero#1")
def test_dissemination_mecatol_z_zetonem_niedostepny_przez_api(
    registry: StaticDataRegistry,
) -> None:
    """Decyzja użytkownika (RULES.md 62.10): bohater nie zdejmuje żetonu Custodians - Mecatol
    Rex z żetonem nie jest celem, a ręcznie podany cel odrzuca silnik (422)."""
    flow = Flow(registry, "yin")
    mecatol, _ = flow.plain_pair()
    flow.set_tile(mecatol, "18")  # Mecatol Rex z żetonem Custodians (stan po setupie)
    assert "mr" not in {
        o["value"].partition("|")[2]
        for o in flow.playable()["yinhero"].get("inputs", [{}])[0].get("options", [])
    }
    flow.player(lambda p: p["leader_states"].update(yinhero="unlocked"))
    resp = flow.client.post("/faction-component/play", json={
        "player_id": flow.me, "kind": "leader", "component_id": "yinhero",
        "params": {"planet1": f"{mecatol}|mr", "planet2": "none", "planet3": "none"},
    })
    assert resp.status_code == 422
    assert flow.state()["players"][flow.me]["leader_states"]["yinhero"] == "unlocked"
