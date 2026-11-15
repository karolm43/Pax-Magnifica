"""Audyt rulingów C_agendas / F_* / C_action_cards (2026-11-15): poprawki z przeglądu kodu.

Każdy test cytuje ruling z ``docs/rules_tirules/`` (CLAUDE.md: każdy ruling = kod albo test).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    agenda_phase,
    board_graph,
    board_reinforcements,
    movement,
    objectives,
    production,
    transaction,
    triggers,
)
from src.core.game_events import Duration
from src.core.game_state import (
    ActiveCombat,
    GameState,
    InvasionPhase,
    InvasionState,
    ProductionGrant,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.hooks import agendas_directives
from src.core.hooks.factions import mentak, sardakk, winnu
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide
from tests.factions import test_hacan, test_mentak, test_sardakk
from tests.test_agenda_effects import _resolve
from tests.test_agenda_effects import _state as _agenda_state
from tests.test_reactions_tactical import ACTIVE, _capture_state, _play


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _offer(state: GameState, player: str, label: str) -> Any:
    return next(o for o in state.pending_offers if o.player_id == player and label in o.label)


# --- Wspólna reguła: pusta rezerwa -> jednostka z planszy (R_component_limitations) ---------


def test_board_sources_tylko_z_systemow_bez_zetonu() -> None:
    state = GameState(
        systems={
            "101": SystemState(position="101", system_id="19",
                               space_units={"p1": {"cruiser": 1}}),
            "102": SystemState(position="102", system_id="20",
                               space_units={"p1": {"cruiser": 1}}, command_tokens=["p1"]),
        }
    )
    assert board_reinforcements.board_sources(state, "p1", "cruiser") == ["101|space"]
    with pytest.raises(ValueError, match="without your command token"):
        board_reinforcements.take_from_board(state, "p1", "cruiser", "102|space")


# --- C_agendas ------------------------------------------------------------------------------


def test_rearmament_pusta_rezerwa_mech_z_planszy(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C_agendas: brak mecha w rezerwie - gracz może zdjąć mecha z systemu bez swojego żetonu."""
    state = _agenda_state(registry, ["rearmament"])
    home = next(p for p, o in state.systems["101"].planet_owners.items() if o == "p1")
    monkeypatch.setattr(
        agendas_directives, "_home_planets",
        lambda s, r, pid: [home] if pid == "p1" else [],
    )
    planet = registry.systems["19"].planets[0]
    state.systems["102"] = SystemState(
        position="102", system_id="19", planet_owners={planet: "p1"},
        planet_units={planet: {"p1": {"mech": 4}}},  # cała pula mechów na planszy
    )
    out = _resolve(registry, state, "for")
    offer = _offer(out, "p1", "Rearmament")
    out = triggers.accept_offer(out, "p1", offer.id, {"planet": home, "source": f"102|{planet}"})
    assert out.systems["101"].planet_units[home]["p1"]["mech"] == 1
    assert out.systems["102"].planet_units[planet]["p1"]["mech"] == 3


def test_wormhole_research_nie_niszczy_struktur_w_przestrzeni(
    registry: StaticDataRegistry,
) -> None:
    """C_agendas: Floating Factory (dok w przestrzeni) przetrwa Wormhole Research."""
    state = _agenda_state(registry, ["wormhole_research"])
    state.systems["201"] = SystemState(
        position="201", system_id="39",
        space_units={"p3": {"cruiser": 1, "infantry": 1, "spacedock": 1}},
    )
    out = _resolve(registry, state, "for")
    for offer in [o for o in out.pending_offers if o.player_id == "p3"]:
        out = triggers.decline_offer(out, "p3", offer.id)
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert out.systems["201"].space_units.get("p3") == {"spacedock": 1}


def test_search_warrant_wybor_zwrotu_po_dobraniu(registry: StaticDataRegistry) -> None:
    """C_agendas: dobrane cele są odkryte, ZANIM gracz wybierze, które oddać ponad limit."""
    state = _agenda_state(registry, ["warrant"])
    state.players["p1"].private.secret_objectives = ["s1", "s2", "s3"]
    state.decks.secret_objective_deck = ["n1", "n2", "n3"]
    out = _resolve(registry, state, "p1")
    assert out.players["p1"].private.secret_objectives == ["s1", "s2", "s3", "n1", "n2"]
    offer = _offer(out, "p1", "Search Warrant")
    out = triggers.accept_offer(out, "p1", offer.id, {"objectives": ["s1", "n2"]})
    assert out.players["p1"].private.secret_objectives == ["s2", "s3", "n1"]
    assert {"s1", "n2"} <= set(out.decks.secret_objective_deck)


def test_archived_secret_przy_trzech_zdobytych_wraca_do_talii(
    registry: StaticDataRegistry,
) -> None:
    """C_agendas: gracz z 3 zdobytymi dobiera czwarty i od razu tasuje go do talii."""
    state = _agenda_state(registry, ["secret"])
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    state.decks.secret_objective_deck = ["n1"]
    out = _resolve(registry, state, "p1")
    assert out.players["p1"].private.secret_objectives == []
    assert "n1" in out.decks.secret_objective_deck


def test_colonial_redistribution_wybrany_gracz_moze_odmowic(
    registry: StaticDataRegistry,
) -> None:
    """Karta: „that player MAY place 1 infantry” - oferta dla wybranego gracza."""
    state = _agenda_state(registry, ["redistribution"])
    planet = registry.systems["19"].planets[0]
    state.systems["102"] = SystemState(
        position="102", system_id="19", planet_owners={planet: "p1"},
        planet_units={planet: {"p1": {"infantry": 2}}},
    )
    state.players["p1"].victory_points = 3
    state.players["p2"].victory_points = 1  # najmniej punktów: tylko p3
    out = _resolve(registry, state, planet)
    assert not out.systems["102"].planet_units[planet].get("p1")  # jednostki zniszczone
    offer = _offer(out, "p3", "Colonial Redistribution")
    assert not offer.mandatory
    placed = triggers.accept_offer(out, "p3", offer.id, {})
    assert placed.systems["102"].planet_units[planet]["p3"] == {"infantry": 1}
    assert placed.systems["102"].planet_owners[planet] == "p3"
    declined = triggers.decline_offer(out, "p3", offer.id)
    assert not declined.systems["102"].planet_units[planet].get("p3")


def test_classified_po_odrzuceniu_prawa_cel_nie_do_zdobycia(registry: StaticDataRegistry) -> None:
    """C_agendas: odrzucone prawo - cel zostaje w grze, ale nie da się go już zdobyć."""
    state = _agenda_state(registry, [])
    state.decks.agenda_laws = {"classified": "dp"}
    state.objectives.revealed = ["dp"]
    agenda_phase.remove_law(state, "classified")
    assert "dp" in state.objectives.revealed and objectives.is_retired(state, "dp")
    with pytest.raises(ValueError, match="no longer be scored"):
        objectives.score_public(state, registry, HexGrid(), "p3", "dp", ignore_phase=True)


# --- F_mentak -------------------------------------------------------------------------------


def _mentak_without_cruisers() -> GameState:
    """p1 = Mentak; wszystkie 8 krążowników na planszy (7 w 301 bez żetonu, 1 w walce)."""
    state = test_mentak._state()
    state.systems["301"].space_units = {"p1": {"cruiser": 7}}
    state.active_combat = ActiveCombat(kind="space", position="000", attacker="p1", defender="p2")
    return state


def test_sleeper_cell_pusta_rezerwa_statek_z_planszy(registry: StaticDataRegistry) -> None:
    """F_mentak: brak statku w rezerwie - może zdjąć go z systemu bez swojego żetonu."""
    state = _mentak_without_cruisers()
    assert state.active_combat is not None
    state.active_combat.destroyed_all = [{"player": "p2", "base_type": "cruiser"}]
    from src.core import active_effects

    active_effects.add_effect(state, mentak.SLEEPER, Duration.COMBAT, owner="p1", data={"seen": 0})
    inputs = mentak.sleeper_inputs(state, registry, "p1", {})
    assert [i["key"] for i in inputs] == ["source:0"]
    mentak._place_sleepers(state, "p1", {"params": {"source:0": "301|space"}})
    assert state.systems["000"].space_units["p1"]["cruiser"] == 2
    assert state.systems["301"].space_units["p1"]["cruiser"] == 6


def test_salvage_i_produkcja_z_planszy_przy_pustej_rezerwie(registry: StaticDataRegistry) -> None:
    """F_mentak (Salvage Operations) + R_component_limitations: produkcja ze zdjęciem z planszy."""
    state = _mentak_without_cruisers()
    assert state.active_combat is not None
    state.active_combat.destroyed_all = [{"player": "p2", "base_type": "cruiser"}]
    assert mentak.salvage_types(state, "p1") == ["cruiser"]
    state.systems["301"].space_units = {}
    state.systems["000"].space_units = {"p1": {"cruiser": 8}}
    state.systems["000"].command_tokens = ["p1"]
    assert mentak.salvage_types(state, "p1") == []  # nic do zdjęcia poza systemem z żetonem


def test_produkcja_wymaga_wskazania_zrodla_przy_pustej_rezerwie(
    registry: StaticDataRegistry,
) -> None:
    state = _mentak_without_cruisers()
    state.active_combat = None
    state.active_system = "000"
    state.systems["000"].command_tokens = ["p1"]
    state.production_grant = ProductionGrant(
        player_id="p1", position="000", units=1, free=True, ships_only=True,
        source="Salvage Operations",
    )
    state.players["p1"].trade_goods = 5
    grid = HexGrid()
    order = production.ProductionOrder("cruiser", 1)
    with pytest.raises(ValueError, match="choose units on the board"):
        production.produce(state, grid, registry, "p1", [order])
    order = production.ProductionOrder("cruiser", 1, sources=("301|space",))
    out = production.produce(state, grid, registry, "p1", [order])
    assert out.systems["000"].space_units["p1"]["cruiser"] == 2
    assert out.systems["301"].space_units["p1"]["cruiser"] == 6


# --- F_norr ---------------------------------------------------------------------------------


def test_ghom_sekkus_nie_przez_wormhole_przy_travel_ban(registry: StaticDataRegistry) -> None:
    """F_norr: „cannot commit ground forces through a wormhole if Enforced Travel Ban…”."""
    grid = HexGrid()
    grid.place_system("102", "115", wormholes=["ALPHA"])
    grid.place_system("301", "26", wormholes=["ALPHA"])
    grid.build_edges()
    state = test_sardakk._state()
    state.players["p1"].leader_states = {"sardakkcommander": "unlocked"}
    state.tactical_step = TacticalStep.INVASION
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.COMMIT)
    state.systems["301"] = SystemState(
        position="301", system_id="26", planet_units={"lodor": {"p1": {"infantry": 1}}}
    )
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    try:
        assert "301" in [p for p, _, _ in sardakk._commander_sources(state, registry, "p1")]
        state.decks.agenda_laws = {"travel_ban": "for"}
        assert "301" not in [p for p, _, _ in sardakk._commander_sources(state, registry, "p1")]
    finally:
        board_graph.bind_grid_provider(previous)


# --- F_winnu --------------------------------------------------------------------------------


def test_reclaimer_struktura_za_kazdego_reclaimera(registry: StaticDataRegistry) -> None:
    """F_winnu: kilka Reclaimerów - po strukturze na każdego (w limicie planety)."""
    planet = registry.systems["19"].planets[0]
    state = GameState(
        players={"p1": test_mentak._state().players["p1"].model_copy(update={"faction": "winnu"})},
        systems={"102": SystemState(
            position="102", system_id="19", planet_owners={planet: "p1"},
            planet_units={planet: {"p1": {"mech": 2}}},
        )},
    )
    ctx = {"player": "p1", "gained": [planet]}
    keys = [i["key"] for i in winnu.reclaimer_inputs(state, registry, "p1", ctx)]
    assert keys == [f"place:{planet}:0", f"place:{planet}:1"]
    winnu.reclaimer(state, "p1", {**ctx, "params": {
        f"place:{planet}:0": "pds", f"place:{planet}:1": "spacedock",
    }})
    assert state.systems["102"].planet_units[planet]["p1"] == {"mech": 2, "pds": 1, "spacedock": 1}


# --- F_hacan --------------------------------------------------------------------------------


def test_pride_of_kenara_z_gravity_rift_rzut(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F_hacan: jednostki przenoszone z planety w gravity rift rzucają na usunięcie."""
    state = test_hacan._state()
    state.players["p1"].controlled_planets = ["mr"]
    state.systems["000"].planet_owners = {"mr": "p1"}
    state.systems["000"].planet_units = {"mr": {"p1": {"mech": 1, "infantry": 2}}}
    planet20 = registry.systems["20"].planets[0]
    state.systems["101"] = SystemState(
        position="101", system_id="20", planet_owners={planet20: "p1"}
    )
    grid = test_hacan._grid()
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    monkeypatch.setattr(movement, "is_gravity_rift", lambda g, pos: pos == "000")
    monkeypatch.setattr(movement, "roll_rift_exit", lambda s, pid, units: {"infantry": 1})
    try:
        side = TransactionSide(planets=(f"mr>{planet20}",))
        done = transaction.resolve_transaction(state, grid, "p2", side, TransactionSide())
    finally:
        board_graph.bind_grid_provider(previous)
    assert done.systems["101"].planet_units[planet20]["p1"] == {"mech": 1, "infantry": 1}


# --- C_action_cards -------------------------------------------------------------------------


def test_infiltrate_pusta_rezerwa_struktura_z_planszy(registry: StaticDataRegistry) -> None:
    """C_action_cards: brak PDS w rezerwie - gracz zdejmuje PDS z systemu bez swojego żetonu."""
    from src.core import control

    state = _capture_state()
    state.systems["102"].planet_units = {"wellon": {"p1": {"pds": 6}}}
    control.set_planet_control(state, ACTIVE, "mr", "p1")
    new = _play(state, registry, "p1", "infiltrate",
                {"planet": "mr", "sources:pds": ["102|wellon"]})
    assert new.systems[ACTIVE].planet_units["mr"]["p1"] == {"pds": 1, "spacedock": 1}
    assert new.systems["102"].planet_units["wellon"]["p1"] == {"pds": 5}


# --- C_exploration_cards / C_relics ---------------------------------------------------------


def test_local_fabricators_pusta_rezerwa_mech_z_planszy(registry: StaticDataRegistry) -> None:
    """C_exploration_cards: brak mecha w rezerwie - mech zdjęty z systemu bez żetonu gracza."""
    from src.core import exploration
    from tests import test_exploration as tx

    state = tx._with_card(tx._state(), registry, "Local Fabricators", tx._IND)
    state.players["p1"].commodities = 1
    planet = registry.systems["19"].planets[0]
    state.systems["200"] = SystemState(
        position="200", system_id="19", planet_owners={planet: "p1"},
        planet_units={planet: {"p1": {"mech": 4}}},
    )
    option = next(o for o in exploration.options_for(state, registry) if o.id == "mech_commodity")
    assert option.enabled and [v for v, _ in option.params] == [f"200|{planet}"]
    done = exploration.resolve(state, registry, "mech_commodity", f"200|{planet}")
    assert done.systems["000"].planet_units[tx._IND]["p1"]["mech"] == 1
    assert done.systems["200"].planet_units[planet]["p1"]["mech"] == 3


def test_demilitarized_zone_otwiera_kontrole_capacity(registry: StaticDataRegistry) -> None:
    """C_exploration_cards: siły zawrócone na orbitę bez capacity trzeba usunąć."""
    from src.core import exploration
    from src.core.game_state import WindowType
    from tests import test_exploration as tx

    state = tx._with_card(
        tx._state(planets={tx._CULT: {"infantry": 2}}), registry, "Demilitarized Zone"
    )
    done = exploration.resolve(state, registry, "attach")
    assert done.pending_window is not None
    assert done.pending_window.window_type is WindowType.CAPACITY


def test_book_of_latvinia_tylko_bez_prerekwizytow(registry: StaticDataRegistry) -> None:
    """C_relics: technologii z prerekwizytem nie da się zdobyć przez pominięcie prerekwizytu."""
    from src.core import technology
    from src.core.hooks import relics_passive
    from tests import test_relics as tr

    state = tr._state(registry, ["bookoflatvinia"])
    with_prereq = next(
        t.id for t in technology.tech_pool(state, registry, "p1").values()
        if technology.prerequisites(t) and t.id not in state.players["p1"].technologies
    )
    with pytest.raises(ValueError, match="without prerequisites"):
        relics_passive.book_gained(
            state, "p1", {"params": {"technologies": [with_prereq]}}
        )


def test_homeland_defense_act_odrzucone_zdejmuje_nadmiar_pds(registry: StaticDataRegistry) -> None:
    """C_agendas: po odrzuceniu prawa najwyżej 2 PDS na planecie."""
    state = _agenda_state(registry, [])
    planet = next(iter(state.systems["101"].planet_owners))
    state.systems["101"].planet_units = {planet: {"p1": {"pds": 4, "infantry": 1}}}
    state.decks.agenda_laws = {"defense_act": "for"}
    agenda_phase.remove_law(state, "defense_act")
    assert state.systems["101"].planet_units[planet]["p1"] == {"pds": 2, "infantry": 1}


def test_wormhole_research_badanie_ze_specjalnoscia_planety(registry: StaticDataRegistry) -> None:
    """C_agendas: wolno wyczerpać planetę ze specjalnością, by zignorować prerekwizyt."""
    from src.core import technology

    state = _agenda_state(registry, [])
    planet, color = next(
        (p, d.tech_specialties[0]) for p, d in sorted(registry.planets.items())
        if d.tech_specialties
    )
    state.systems["301"] = SystemState(position="301", system_id="19", planet_owners={planet: "p1"})
    tech = next(
        t for t in technology.tech_pool(state, registry, "p1").values()
        if technology.prerequisites(t) == {color.upper(): 1}
        and technology.UNIT_UPGRADE not in t.types
    )
    with pytest.raises(ValueError, match="prerequisites"):
        agendas_directives.research_chosen(state, "p1", [tech.id])
    agendas_directives.research_chosen(state, "p1", [tech.id], [planet])
    assert tech.id in state.players["p1"].technologies
    assert planet in state.players["p1"].exhausted_planets
