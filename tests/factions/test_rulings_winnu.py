"""The Winnu — rulingi ``docs/rules_tirules/F_winnu.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty rulingów / zdania kart, które sprawdza (strażnik
``tests/test_ruling_coverage.py``). Podstawowe testy komponentów są w ``test_winnu.py``,
``test_flows_winnu.py`` i ``test_rulings_audit.py`` (tam też część znaczników). Statusy bez
testu: ``tests/rulings_status.json`` (stara Acquiescence, Construction PoK, Nekro, Creuss).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    action_adjacency,
    active_effects,
    control,
    exhaust,
    invasion,
    leaders,
    planet_stats,
    production,
    rules_hooks,
    space_cannon,
    strategic_action,
    tactical,
    timing,
    triggers,
)
from src.core.game_events import Duration, GameEvent
from src.core.game_state import (
    ActiveCombat,
    GameState,
    InvasionPhase,
    InvasionState,
    PlayerState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import winnu
from src.core.production import ProductionOrder
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards import CARDS
from tests import test_custodians_invasion as custodians_tests
from tests.factions.test_winnu import _grid, _state
from tests.factions.test_winnu import registry as registry  # noqa: F401 - fixture modułu
from tests.rulings import ruling

assert _grid  # autouse: 000 = Mecatol, 301 = wormhole alfa, 101 = dom Winnu

_MR = "mr"


def _home_planet(registry: StaticDataRegistry) -> str:
    return str(registry.systems["20"].planets[0])


def _offers(state: GameState, player: str = "p1") -> list[str]:
    return [o.label for o in state.pending_offers if o.player_id == player]


def _accept(
    state: GameState, label: str, params: dict[str, Any], player: str = "p1"
) -> GameState:
    offer = next(o for o in state.pending_offers if o.player_id == player and label in o.label)
    return triggers.accept_offer(state, player, offer.id, params)


# =================================================================================== Blood Ties


@ruling("abilities:blood_ties#1")
def test_blood_ties_bez_wplywu_ale_z_silami_naziemnymi(registry: StaticDataRegistry) -> None:
    """Winnu zdejmuje żeton bez wpływu, ale nadal musi mieć siły naziemne i zlądować."""
    state = custodians_tests._state(trade_goods=0)
    state.players["p1"].faction = "winnu"
    claimed = invasion.claim_custodians(
        custodians_tests._begin(state, registry), registry, [], 0
    )
    assert claimed.custodians_removed and claimed.players["p1"].trade_goods == 0
    with pytest.raises(ValueError, match="Mecatol Rex"):
        invasion.advance(claimed, custodians_tests._grid(), registry)  # bez lądowania
    empty = custodians_tests._state(trade_goods=0, infantry=0)
    empty.players["p1"].faction = "winnu"
    empty.invasion = InvasionState(
        position="000", attacker="p1", phase=InvasionPhase.COMMIT
    )
    with pytest.raises(ValueError, match="ground forces"):
        invasion.claim_custodians(empty, registry, [], 0)


# ======================================================================= Reclamation, Reclaimer


def _gained_in_action(state: GameState, registry: StaticDataRegistry, position: str,
                      planet: str) -> None:
    """Winnu przejmuje planetę w trakcie akcji taktycznej (ślad ``control_changes``)."""
    state.active_system = position
    state.tactical_step = TacticalStep.PRODUCTION
    control.set_planet_control(state, position, planet, "p1", registry)


@ruling(
    "F_winnu/reclamation/1", "F_winnu/reclaimer/2", "abilities:reclamation#1", "units:winnu_mech#1",
)
def test_struktury_po_akcji_po_kroku_produkcji(registry: StaticDataRegistry) -> None:
    """Reclamation i Reclaimer: oferta dopiero PO akcji taktycznej (po kroku Production);
    postawiony dok nie produkuje w tej akcji (akcja już się skończyła)."""
    state = _state()
    state.systems["000"].planet_units = {_MR: {"p1": {"infantry": 1, "mech": 1}}}
    _gained_in_action(state, registry, "000", _MR)
    assert _offers(state) == []  # w kroku Production nic się nie dzieje
    ended = tactical.end_tactical_action(state)
    labels = _offers(ended)
    assert any("Reclamation" in label for label in labels)
    assert any("Reclaimer" in label for label in labels)
    after = _accept(ended, "Reclamation", {"place": "pds+spacedock"})
    assert after.systems["000"].planet_units[_MR]["p1"]["spacedock"] == 1
    assert after.tactical_step is None and after.active_system is None
    assert production.production_system(after) is None  # nowy dok nie ma już czego produkować


def test_reclaimer_pusta_rezerwa_struktura_z_planszy(registry: StaticDataRegistry) -> None:
    """Bez PDS w rezerwie Reclaimer bierze PDS z systemu bez własnego żetonu dowodzenia."""
    state = _state()
    home = _home_planet(registry)
    cap = production.reinforcements_left(state, "p1", "pds")
    assert cap is not None
    state.systems["101"].planet_owners = {home: "p1"}
    state.systems["101"].planet_units = {home: {"p1": {"pds": cap}}}
    state.systems["000"].planet_owners = {_MR: "p1"}
    state.systems["000"].planet_units = {_MR: {"p1": {"mech": 1}}}
    ctx = {"player": "p1", "gained": [_MR]}
    options = [o["value"] for o in winnu.reclaimer_inputs(state, registry, "p1", ctx)[0]["options"]]
    assert f"pds<{home}" in options and "pds" not in options
    winnu.reclaimer(state, "p1", {**ctx, "params": {f"place:{_MR}:0": f"pds<{home}"}})
    assert state.systems["000"].planet_units[_MR]["p1"]["pds"] == 1
    assert state.systems["101"].planet_units[home]["p1"]["pds"] == cap - 1
    state.systems["101"].command_tokens = ["p1"]  # system z własnym żetonem — nie wolno
    options = [o["value"] for o in winnu.reclaimer_inputs(state, registry, "p1", ctx)[0]["options"]]
    assert not any(str(v).startswith("pds") for v in options)


@ruling("F_winnu/reclaimer/4")
def test_reclaimer_wystarczy_na_koniec_akcji(registry: StaticDataRegistry) -> None:
    """Planeta przejęta bez Reclaimera (Infiltrate, eksploracja), mech stoi na niej dopiero na
    końcu akcji — zdolność i tak działa."""
    state = _state()
    planet = _home_planet(registry)
    _gained_in_action(state, registry, "101", planet)  # przejęcie bez mecha
    state.systems["101"].planet_units = {planet: {"p1": {"mech": 1}}}  # mech dochodzi później
    ended = tactical.end_tactical_action(state)
    assert any("Reclaimer" in label for label in _offers(ended))
    plain = _state()
    _gained_in_action(plain, registry, "101", planet)  # bez mecha na końcu — brak oferty
    assert not any("Reclaimer" in label for label in _offers(tactical.end_tactical_action(plain)))


# ==================================================================== Acquiescence (notka Ω)


def _secondary_window(state: GameState, initiative: int, **extra: str | int) -> GameState:
    spec = CARDS[initiative]
    return timing.open_window(
        state, WindowType.STRATEGY_SECONDARY, ["p2"],
        context={"initiative": initiative, "free": "",
                 "cost": 1 if spec.secondary_costs_token else 0, **extra},
    )


@ruling("promissory_notes:acq#1")
def test_acquiescence_construction_bez_zetonu(registry: StaticDataRegistry) -> None:
    """Construction z Acquiescence: struktura bez wydania żetonu i bez żetonu na planszy."""
    state = _secondary_window(_state(), 4)
    home = _home_planet(registry)
    state.systems["101"].planet_owners = {home: "p2"}
    state.players["p2"].strategic_cc = 0
    winnu.acquiescence(state, registry, "p2", {})
    after = strategic_action.resolve_secondary(
        state, registry, "p2", execute=True, payload={"planet": home, "structure": "pds"},
    )
    assert after.systems["101"].planet_units[home]["p2"]["pds"] == 1
    assert after.players["p2"].strategic_cc == 0
    assert all(not s.command_tokens for s in after.systems.values())


@ruling("F_winnu/acquiescence-omega/1")
def test_acquiescence_nie_wydaje_zetonu_strategii(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Brak wydania żetonu = brak zdarzenia STRATEGY_TOKEN_SPENT (na nim stoją efekty typu
    Magmus „after you spend a token from your strategy pool”)."""
    fired: list[GameEvent] = []
    original = triggers.fire

    def spy(state: GameState, event: GameEvent, *args: Any, **kwargs: Any) -> Any:
        fired.append(event)
        return original(state, event, *args, **kwargs)

    monkeypatch.setattr(triggers, "fire", spy)
    trade = _secondary_window(_state(), 5)
    trade.players["p2"].strategic_cc = 1
    paid = strategic_action.resolve_secondary(trade, registry, "p2", execute=True)
    assert GameEvent.STRATEGY_TOKEN_SPENT in fired and paid.players["p2"].strategic_cc == 0
    winnu.acquiescence(trade, registry, "p2", {})
    fired.clear()
    done = strategic_action.resolve_secondary(trade, registry, "p2", execute=True)
    assert GameEvent.STRATEGY_TOKEN_SPENT not in fired
    assert done.players["p2"].strategic_cc == 1


# ==================================================================== Hegemonic Trade Policy


def _dock_on_mecatol(registry: StaticDataRegistry) -> GameState:
    state = _state()
    state.systems["000"].planet_owners = {_MR: "p1"}
    state.systems["000"].planet_units = {_MR: {"p1": {"spacedock": 1}}}
    state.players["p1"].technologies = ["htp"]
    state.active_system = "000"
    state.tactical_step = TacticalStep.PRODUCTION
    return state


@ruling("F_winnu/hegemonic-trade-policy/2")
def test_htp_zmienia_production_doku(registry: StaticDataRegistry) -> None:
    state = _dock_on_mecatol(registry)
    stats = registry.planets[_MR]
    assert stats.resources != stats.influence
    before = production.system_production_value(state, HexGrid(), registry, "p1", "000")
    active_effects.add_effect(
        state, winnu.HTP_SWAP, Duration.TURN, owner="p1", data={"planet": _MR}
    )
    after = production.system_production_value(state, HexGrid(), registry, "p1", "000")
    assert after - before == stats.influence - stats.resources


@ruling("technologies:htp#1", "technologies:htp#2")
def test_htp_tylko_przy_produkcji_jedna_planeta(registry: StaticDataRegistry) -> None:
    state = _dock_on_mecatol(registry)
    winnu.hegemonic_trade_policy(state, registry, "p1", {"planet": _MR})
    assert "htp" in state.players["p1"].exhausted_technologies
    assert rules_hooks.forbidden(rules_hooks.POINT_PLANET_SWAP_VALUES, state, "p1") == {_MR}
    with pytest.raises(ValueError, match="exhausted"):
        winnu.hegemonic_trade_policy(state, registry, "p1", {"planet": _MR})
    idle = _dock_on_mecatol(registry)
    idle.tactical_step = TacticalStep.MOVEMENT
    with pytest.raises(ValueError, match="PRODUCTION"):
        winnu.hegemonic_trade_policy(idle, registry, "p1", {"planet": _MR})
    foreign = _dock_on_mecatol(registry)
    with pytest.raises(ValueError, match="control"):
        winnu.hegemonic_trade_policy(foreign, registry, "p1", {"planet": "jord"})


# ======================================================================== Lazax Gate Folding


def _lgf_state() -> GameState:
    state = _state()
    state.players["p1"].technologies = ["lgf"]
    state.active_system = "000"
    state.tactical_step = TacticalStep.SPACE_CANNON
    return state


@ruling("F_winnu/lazax-gate-folding/1", "technologies:lgf#1")
def test_lgf_wyczerpana_nadal_tunel(registry: StaticDataRegistry) -> None:
    state = _lgf_state()
    exhaust.exhaust_technology(state, "p1", "lgf")
    assert "301" in action_adjacency.extra_adjacent(state, "000")
    state.systems["000"].planet_owners = {_MR: "p1"}  # kontrola Mecatol wyłącza efekt
    assert action_adjacency.extra_adjacent(state, "000") == frozenset()


@ruling("F_winnu/lazax-gate-folding/2.2")
def test_lgf_deep_space_cannon_innych_graczy(
    registry: StaticDataRegistry, _grid: HexGrid
) -> None:
    """DSC p2 z systemu z wormhole strzela do Mecatol (aktywny) — i odwrotnie."""
    state = _lgf_state()
    planet301 = registry.systems["26"].planets[0]
    state.players["p2"].technologies = ["pds2"]  # PDS II: Deep Space Cannon
    state.systems["301"].planet_units = {planet301: {"p2": {"pds": 1}}}
    shooters = space_cannon.offense_shooters(state, _grid, registry, "p2")
    assert shooters and all(s.remote for s in shooters)
    state.active_system = "301"
    state.systems["301"].planet_units = {}
    state.systems["000"].planet_units = {_MR: {"p2": {"pds": 1}}}
    shooters = space_cannon.offense_shooters(state, _grid, registry, "p2")
    assert shooters and all(s.remote for s in shooters)
    state.tactical_step = None  # poza akcją taktyczną Winnu — brak sąsiedztwa
    assert space_cannon.offense_shooters(state, _grid, registry, "p2") == []


@ruling("F_winnu/lazax-gate-folding/3", "technologies:lgf#2")
def test_lgf_akcja_z_kontrola_i_bez(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["lgf"]
    winnu.lazax_gate_folding_action(state, registry, "p1", {})  # bez kontroli: tylko wyczerpanie
    assert "lgf" in state.players["p1"].exhausted_technologies
    assert state.systems["000"].planet_units.get(_MR, {}).get("p1") is None
    owned = _state()
    owned.players["p1"].technologies = ["lgf"]
    owned.systems["000"].planet_owners = {_MR: "p1"}
    winnu.lazax_gate_folding_action(owned, registry, "p1", {})
    assert owned.systems["000"].planet_units[_MR]["p1"] == {"infantry": 1}
    with pytest.raises(ValueError, match="exhausted"):
        winnu.lazax_gate_folding_action(owned, registry, "p1", {})


# ======================================================================= Berekar Berekon


@ruling("leaders:winnuagent#1")
def test_berekar_obniza_koszt_nie_limit(registry: StaticDataRegistry, _grid: HexGrid) -> None:
    state = _dock_on_mecatol(registry)
    state.players["p1"].trade_goods = 20
    orders = [ProductionOrder("cruiser", 2)]
    before = production.order_cost(state, registry, "p1", orders)
    limit = production.remaining_production(state, _grid, registry, "p1")
    winnu.berekar_berekon(state, registry, "p1", {})
    assert production.order_cost(state, registry, "p1", orders) == before - 2
    assert production.remaining_production(state, _grid, registry, "p1") == limit
    with pytest.raises(ValueError, match="Production limit"):
        production.validate_production(
            state, _grid, registry, "p1", [ProductionOrder("fighter", limit + 1)]
        )


@ruling("leaders:winnuagent#1")
def test_berekar_dla_produkcji_innego_gracza(registry: StaticDataRegistry) -> None:
    """„a player's units” — rabat dostaje produkujący gracz, nie Winnu."""
    state = _dock_on_mecatol(registry)
    state.active_player_id = "p2"
    winnu.berekar_berekon(state, registry, "p1", {})
    assert active_effects.has_effect(state, "p2", winnu.AGENT_CUT)
    assert not active_effects.has_effect(state, "p1", winnu.AGENT_CUT)


# ======================================================================= Rickar Rickani


def _commander_bonus(state: GameState, position: str) -> int:
    return int(rules_hooks.modify(
        rules_hooks.POINT_COMBAT_ROLL_MODIFIER, state, "p1", 0, {"position": position}
    ))


@ruling("F_winnu/rickar-rickani/1", "leaders:winnucommander#unlock")
def test_rickar_odblokowany_walka_na_mecatol_dziala_od_razu(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    assert leaders.refresh_unlocks(state, registry) == []
    assert _commander_bonus(state, "000") == 0  # zablokowany
    state.systems["000"].space_units = {"p1": {"cruiser": 1}, "p2": {"cruiser": 1}}
    state.active_combat = ActiveCombat(
        kind="space", position="000", planet=None, attacker="p1", defender="p2"
    )
    assert "winnucommander" in leaders.refresh_unlocks(state, registry)
    assert _commander_bonus(state, "000") == 2  # ta sama walka
    owner = _state()
    owner.systems["000"].planet_owners = {_MR: "p1"}  # albo kontrola Mecatol Rex
    assert "winnucommander" in leaders.refresh_unlocks(owner, registry)


@ruling("F_winnu/rickar-rickani/2", "leaders:winnucommander#1")
def test_rickar_raz_plus_dwa(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"winnucommander": "unlocked"}
    state.players["p1"].home_position = "000"  # Mecatol + dom w jednym systemie
    state.planet_attachments = {_MR: ["nanoforge"]}  # i legendarna (Nano-Forge)
    assert planet_stats.is_legendary(state, registry, _MR)
    assert _commander_bonus(state, "000") == 2
    state.players["p1"].home_position = "101"
    assert _commander_bonus(state, "101") == 2  # dom
    assert _commander_bonus(state, "301") == 0  # zwykły system


# ===================================================================== Mathis Mathinus (hero)


def _three_players() -> GameState:
    state = _state()
    state.players["p3"] = PlayerState(player_id="p3", color="red", faction="jolnar")
    state.seating_order = ["p1", "p2", "p3"]
    for pid in ("p2", "p3"):
        state.players[pid].strategic_cc = 0
    return state


@ruling(
    "F_winnu/mathis-mathinus-imperial-seal/1", "leaders:winnuhero#2", "leaders:winnuhero#3",
)
def test_mathis_wskazani_placa_zeton_poza_leadership(registry: StaticDataRegistry) -> None:
    state = _three_players()
    winnu.imperial_seal(state, registry, "p1", {"card": "5", "players": ["p2"]})
    opened = strategic_action.submit_primary_step(state, registry, "p1", {"players": []})
    window = opened.pending_window
    assert window is not None and window.queue == ["p2"]  # p3 niewskazany
    with pytest.raises(ValueError, match="command token"):
        strategic_action.resolve_secondary(opened, registry, "p2", execute=True)
    passed = strategic_action.resolve_secondary(opened, registry, "p2", execute=False)
    assert passed.pending_window is None  # „may” — wolno spasować
    assert CARDS[1].secondary_costs_token is False  # Leadership: bez żetonu


@ruling("F_winnu/mathis-mathinus-imperial-seal/1.1")
def test_mathis_trade_wskazany_primary_musi(registry: StaticDataRegistry) -> None:
    """Trade z bohatera: wskazany primary (p3) MUSI i nie płaci; wskazany bohaterem (p2) może,
    ale płaci żeton."""
    state = _three_players()
    winnu.imperial_seal(state, registry, "p1", {"card": "5", "players": ["p2"]})
    opened = strategic_action.submit_primary_step(state, registry, "p1", {"players": ["p3"]})
    window = opened.pending_window
    assert window is not None and window.queue == ["p2", "p3"]
    with pytest.raises(ValueError, match="command token"):
        strategic_action.resolve_secondary(opened, registry, "p2", execute=True)
    after_p2 = strategic_action.resolve_secondary(opened, registry, "p2", execute=False)
    # p3 „free”: secondary rozstrzyga się samo (obowiązkowe, bez żetonu) i okno się zamyka.
    assert after_p2.pending_window is None
    assert after_p2.players["p3"].strategic_cc == 0
    assert "p3" in after_p2.last_replenished and "p2" not in after_p2.last_replenished


@ruling("F_winnu/mathis-mathinus-imperial-seal/2")
def test_mathis_nie_wyzwala_acquiescence(registry: StaticDataRegistry) -> None:
    state = _three_players()
    state.players["p2"].private.promissory_notes = ["acq"]
    winnu.imperial_seal(state, registry, "p1", {"card": "5", "players": ["p2"]})
    opened = strategic_action.submit_primary_step(state, registry, "p1", {"players": []})
    assert winnu.acquiescence_window(opened) == []
    reason = winnu._acq_condition(opened, registry, "p2", None)  # type: ignore[arg-type]
    assert reason is not None
    normal = _secondary_window(_three_players(), 5)  # zwykła akcja strategiczna Winnu
    normal.players["p2"].private.promissory_notes = ["acq"]
    assert winnu.acquiescence_window(normal) != []
    assert winnu._acq_condition(normal, registry, "p2", None) is None  # type: ignore[arg-type]


@ruling("leaders:winnuhero#unlock")
def test_mathis_odblokowanie_trzy_cele(registry: StaticDataRegistry) -> None:
    predicate = leaders.unlock_predicate(registry, "winnuhero")
    assert predicate is not None
    state = _state()
    state.objectives.scored = {"corner": ["p1"], "develop": ["p1"]}
    assert not predicate(state, registry, "p1")
    state.objectives.scored["diversify"] = ["p1"]
    assert predicate(state, registry, "p1")


# ======================================================================= Imperator (przełom)


@ruling("F_winnu/imperator/1", "F_winnu/imperator/2", "breakthroughs:winnubt#1")
def test_imperator_wlasna_sftt_i_otrzymana_w_walce(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.active_combat = ActiveCombat(
        kind="space", position="301", planet=None, attacker="p1", defender="p2"
    )
    assert _commander_bonus(state, "301") == 0
    state.players["p2"].promissory_notes_in_play = ["green_sftt"]  # WŁASNA SftT Winnu (green)
    assert _commander_bonus(state, "301") == 1
    state.players["p2"].promissory_notes_in_play.append("blue_sftt")  # p2 dostaje w trakcie
    assert _commander_bonus(state, "301") == 2  # pozostałe rzuty tej walki


def test_imperator_tylko_w_walce_gracza(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.players["p2"].promissory_notes_in_play = ["green_sftt"]
    assert winnu.imperator_combat(state, "p1", {}) == 0  # brak walki

