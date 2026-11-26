"""Testy kart akcji (okno ACTION): plansza, neutralni, żetony, karty strategii (RULES.md 53).

Karty: Fighter Conscription, Ghost Ship, Signal Jamming, Mercenary Contract, Pirate Contract
(4 kopie), Pirate Fleet, Exchange Program, Overrule, Strategize (4 kopie).
Mapa testowa to demo (``build_demo_grid``): 000 Mecatol, 101 pusty system z wormholem BETA,
102 planeta industrex, 103..106 systemy z planetami. Dom p1 = 103, dom p2 = 105.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import action_cards, board_graph, command_tokens, strategic_action
from src.core.game_state import GameState, Phase, PlayerState, SystemState, WindowType
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(autouse=True)
def _grid(registry: StaticDataRegistry) -> Iterator[None]:
    """Podpina mapę demo dla efektów kart (jak robi to ``AppContext``) i przywraca poprzednią."""
    grid = build_demo_grid(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield
    board_graph.bind_grid_provider(previous)


def _state(
    hand: list[str], systems: list[SystemState] | None = None, **player: Any
) -> GameState:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", color="red", home_position="103", **player),
            "p2": PlayerState(player_id="p2", color="blue", home_position="105"),
        },
        systems={s.position: s for s in systems or []},
    )
    state.players["p1"].private.action_cards = list(hand)
    return state


def _system(position: str, system_id: str, **fields: Any) -> SystemState:
    return SystemState(position=position, system_id=system_id, **fields)


def _play(
    registry: StaticDataRegistry, state: GameState, card: str, params: dict[str, Any] | None = None
) -> GameState:
    new, implemented = action_cards.play_action_card(state, registry, "p1", card, params)
    assert implemented
    return new


def _inputs(registry: StaticDataRegistry, state: GameState, card: str) -> list[dict[str, Any]]:
    implemented, inputs = action_cards.card_inputs(state, registry, "p1", card)
    assert implemented
    return inputs


def _playable(registry: StaticDataRegistry, state: GameState, card: str) -> bool:
    rows = action_cards.playability(state, registry, "p1")
    return bool(next(row for row in rows if row["card_id"] == card)["playable"])


def _first_params(inputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Parametry zbudowane tak jak w UI: pierwsza opcja każdego wyboru (``merge`` = scalenie)."""
    params: dict[str, Any] = {}
    for item in inputs:
        if item["kind"] == "choice":
            value = item["options"][0]["value"]
            if item["merge"]:
                params.update(value)
            else:
                params[item["key"]] = value
        elif item["kind"] == "multi":
            params[item["key"]] = [o["value"] for o in item["options"][: item["max"]]]
    return params


# ----------------------------------------------------------------------- Fighter Conscription


def _conscription_state(extra: list[SystemState] | None = None) -> GameState:
    systems = [
        _system("101", "113", space_units={"p1": {"carrier": 1}}),
        _system(
            "102",
            "115",
            planet_owners={"industrex": "p1"},
            planet_units={"industrex": {"p1": {"spacedock": 1}}},
        ),
        *(extra or []),
    ]
    return _state(["f_conscription"], systems)


def test_fighter_conscription_stawia_mysliwca_w_kazdym_systemie_z_dokiem_lub_capacity(
    registry: StaticDataRegistry,
) -> None:
    state = _conscription_state()
    inputs = _inputs(registry, state, "f_conscription")
    assert [o["value"] for o in inputs[0]["options"]] == ["101", "102"]
    new = _play(registry, state, "f_conscription", _first_params(inputs))
    assert new.systems["101"].space_units["p1"]["fighter"] == 1
    assert new.systems["102"].space_units["p1"]["fighter"] == 1
    assert "fighter" not in state.systems["101"].space_units["p1"]  # wejście nietknięte
    assert new.pending_window is None  # w limicie capacity


def test_fighter_conscription_bez_parametru_stawia_we_wszystkich(
    registry: StaticDataRegistry,
) -> None:
    new = _play(registry, _conscription_state(), "f_conscription")
    assert new.systems["101"].space_units["p1"]["fighter"] == 1
    assert new.systems["102"].space_units["p1"]["fighter"] == 1


def test_fighter_conscription_pomija_systemy_ze_statkami_innych_graczy(
    registry: StaticDataRegistry,
) -> None:
    state = _conscription_state([_system("103", "01", space_units={"p2": {"cruiser": 1}})])
    state.systems["101"].space_units["neutral"] = {"destroyer": 1}  # neutralni to „inny gracz”
    options = _inputs(registry, state, "f_conscription")[0]["options"]
    assert [o["value"] for o in options] == ["102"]
    with pytest.raises(ValueError, match="eligible systems"):
        _play(registry, state, "f_conscription", {"positions": ["101", "102"]})


def test_fighter_conscription_ponad_capacity_otwiera_okno_capacity(
    registry: StaticDataRegistry,
) -> None:
    state = _conscription_state()
    state.systems["101"].space_units["p1"]["fighter"] = 3  # carrier ma pojemność 4
    state.systems["101"].space_units["p1"]["infantry"] = 1  # wybór: myśliwiec albo piechota
    new = _play(registry, state, "f_conscription")
    assert new.systems["101"].space_units["p1"]["fighter"] == 4
    assert new.pending_window is not None
    assert new.pending_window.window_type is WindowType.CAPACITY


def test_fighter_conscription_bez_celow_jest_zagrywalna_bez_skutku(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["f_conscription"], [_system("101", "113", space_units={"p1": {"fighter": 1}})])
    assert _playable(registry, state, "f_conscription")
    new = _play(registry, state, "f_conscription")
    assert new.systems["101"].space_units == state.systems["101"].space_units


# ------------------------------------------------------------------------------ Ghost Ship


def test_ghost_ship_stawia_niszczyciel_w_systemie_z_wormholem(registry: StaticDataRegistry) -> None:
    state = _state(["ghost_ship"])
    inputs = _inputs(registry, state, "ghost_ship")
    assert [o["value"] for o in inputs[0]["options"]] == ["101"]  # tylko BETA, nie Mecatol
    new = _play(registry, state, "ghost_ship", _first_params(inputs))
    assert new.systems["101"].space_units["p1"] == {"destroyer": 1}
    assert not state.systems  # wejście nietknięte


def test_ghost_ship_odrzuca_system_bez_wormholea_domowy_i_ze_statkami_innych(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["ghost_ship"])
    with pytest.raises(ValueError, match="wormhole"):
        _play(registry, state, "ghost_ship", {"position": "000"})
    with pytest.raises(ValueError, match="wormhole"):
        _play(registry, state, "ghost_ship", {})
    state.players["p2"].home_position = "101"  # wormhole w cudzym domu
    assert not _playable(registry, state, "ghost_ship")
    with pytest.raises(ValueError, match="wormhole"):
        _play(registry, state, "ghost_ship", {"position": "101"})


def test_ghost_ship_niezagrywalna_gdy_w_systemie_sa_cudze_statki(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["ghost_ship"], [_system("101", "113", space_units={"neutral": {"fighter": 1}})])
    assert not _playable(registry, state, "ghost_ship")
    assert _playable(registry, _state(["ghost_ship"]), "ghost_ship")


# ----------------------------------------------------------------------------- Signal Jamming


def test_jamming_kladzie_zeton_z_rezerwy_innego_gracza(registry: StaticDataRegistry) -> None:
    state = _state(["jamming"], [_system("000", "18", space_units={"p1": {"cruiser": 1}})])
    inputs = _inputs(registry, state, "jamming")
    values = [o["value"] for o in inputs[0]["options"]]
    # własny statek w 000 (Mecatol) i sąsiedzi; domy p1 (103) i p2 (105) odpadają
    assert {v["position"] for v in values} == {"000", "101", "102", "104", "106"}
    assert all(v["player"] == "p2" for v in values)
    before = state.players["p2"].cc_reinf
    new = _play(registry, state, "jamming", {"position": "101", "player": "p2"})
    assert new.systems["101"].command_tokens == ["p2"]
    assert new.players["p2"].cc_reinf == before - 1
    assert state.players["p2"].cc_reinf == before


def test_jamming_wymaga_wlasnego_statku_w_systemie_lub_obok(registry: StaticDataRegistry) -> None:
    state = _state(["jamming"], [_system("101", "113", space_units={"p1": {"cruiser": 1}})])
    # 101 sąsiaduje z 000, 102, 106 - ale nie z 104
    with pytest.raises(ValueError, match="non-home system"):
        _play(registry, state, "jamming", {"position": "104", "player": "p2"})
    _play(registry, state, "jamming", {"position": "106", "player": "p2"})
    assert not _playable(registry, _state(["jamming"]), "jamming")  # brak własnych statków


def test_jamming_odrzuca_system_domowy_siebie_i_pusta_rezerwe(registry: StaticDataRegistry) -> None:
    state = _state(["jamming"], [_system("000", "18", space_units={"p1": {"cruiser": 1}})])
    with pytest.raises(ValueError, match="non-home system"):
        _play(registry, state, "jamming", {"position": "103", "player": "p2"})  # dom p1
    with pytest.raises(ValueError, match="another player"):
        _play(registry, state, "jamming", {"position": "101", "player": "p1"})
    state.players["p2"].cc_reinf = 0
    assert not _playable(registry, state, "jamming")  # nikt nie ma żetonu w rezerwie


def test_jamming_nie_dubluje_zetonu_gracza_w_systemie(registry: StaticDataRegistry) -> None:
    state = _state(
        ["jamming"],
        [
            _system("000", "18", space_units={"p1": {"cruiser": 1}}),
            _system("101", "113", command_tokens=["p2"]),
        ],
    )
    with pytest.raises(ValueError, match="non-home system"):
        _play(registry, state, "jamming", {"position": "101", "player": "p2"})


def test_place_on_board_from_reinforcements_jest_centralna_i_sprawdza_rezerwe() -> None:
    state = _state([])
    system = _system("101", "113")
    command_tokens.place_on_board_from_reinforcements(state, system, "p2")
    assert system.command_tokens == ["p2"]
    with pytest.raises(ValueError, match="already has"):
        command_tokens.place_on_board_from_reinforcements(state, system, "p2")
    state.players["p1"].cc_reinf = 0
    with pytest.raises(ValueError, match="reinforcements"):
        command_tokens.place_on_board_from_reinforcements(state, system, "p1")


# ------------------------------------------------------------------------ Mercenary Contract


def test_mercenary_contract_stawia_dwoch_neutralnych_i_zabiera_2_tg(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["mercenarycontract"], trade_goods=3)
    inputs = _inputs(registry, state, "mercenarycontract")
    values = [o["value"] for o in inputs[0]["options"]]
    assert {"position": "102", "planet": "industrex"} in values
    # planety domowe (103 Jord, 105 Darien) są poza zasięgiem
    assert all(v["position"] not in ("103", "105") for v in values)
    new = _play(registry, state, "mercenarycontract", {"position": "102", "planet": "industrex"})
    assert new.systems["102"].planet_units["industrex"][NEUTRAL_PLAYER_ID] == {"infantry": 2}
    assert new.players["p1"].trade_goods == 1
    assert "industrex" not in new.systems["102"].planet_owners  # neutralni nie przejmują kontroli


def test_mercenary_contract_odbiera_planete_innemu_graczowi(registry: StaticDataRegistry) -> None:
    state = _state(
        ["mercenarycontract"],
        [_system("102", "115", planet_owners={"industrex": "p2"})],
        trade_goods=2,
    )
    state.players["p2"].controlled_planets = ["industrex"]
    state.players["p2"].exhausted_planets = ["industrex"]
    new = _play(registry, state, "mercenarycontract", {"position": "102", "planet": "industrex"})
    assert "industrex" not in new.systems["102"].planet_owners
    assert new.players["p2"].controlled_planets == []
    assert new.players["p2"].exhausted_planets == []
    assert new.players["p1"].trade_goods == 0


def test_mercenary_contract_odrzuca_planety_niedozwolone(registry: StaticDataRegistry) -> None:
    bad: list[tuple[GameState, dict[str, str]]] = [
        # własna planeta
        (
            _state(
                ["mercenarycontract"],
                [_system("102", "115", planet_owners={"industrex": "p1"})],
                trade_goods=2,
            ),
            {"position": "102", "planet": "industrex"},
        ),
        # planeta z jednostkami (także cudzymi)
        (
            _state(
                ["mercenarycontract"],
                [_system("102", "115", planet_units={"industrex": {"p2": {"pds": 1}}})],
                trade_goods=2,
            ),
            {"position": "102", "planet": "industrex"},
        ),
        # planeta w systemie domowym
        (_state(["mercenarycontract"], trade_goods=2), {"position": "103", "planet": "jord"}),
        # DMZ
        (_state(["mercenarycontract"], trade_goods=2), {"position": "102", "planet": "industrex"}),
        # za mało TG
        (_state(["mercenarycontract"], trade_goods=1), {"position": "102", "planet": "industrex"}),
    ]
    bad[3][0].planet_attachments["industrex"] = ["dmz"]
    for state, params in bad:
        with pytest.raises(ValueError, match="Choose a non-home planet"):
            _play(registry, state, "mercenarycontract", params)
    assert not _playable(registry, bad[4][0], "mercenarycontract")


# ---------------------------------------------------------------------------- Pirate Contract


@pytest.mark.parametrize("card", ["piratecontract1", "piratecontract2", "piratecontract3",
                                  "piratecontract4"])
def test_pirate_contract_stawia_neutralnego_niszczyciela(
    registry: StaticDataRegistry, card: str
) -> None:
    state = _state([card])
    inputs = _inputs(registry, state, card)
    options = [o["value"] for o in inputs[0]["options"]]
    assert "000" in options and "103" not in options and "105" not in options
    new = _play(registry, state, card, {"position": "104"})
    assert new.systems["104"].space_units[NEUTRAL_PLAYER_ID] == {"destroyer": 1}


def test_pirate_contract_odrzuca_systemy_ze_statkami_graczy_i_domowe(
    registry: StaticDataRegistry,
) -> None:
    state = _state(
        ["piratecontract1"],
        [
            _system("101", "113", space_units={"p2": {"cruiser": 1}}),
            _system("102", "115", space_units={"p1": {"destroyer": 1}}),  # także własne
            _system("104", "02", space_units={NEUTRAL_PLAYER_ID: {"fighter": 1}}),  # neutralni OK
        ],
    )
    for position in ("101", "102", "103", "105"):
        with pytest.raises(ValueError, match="non-neutral ships"):
            _play(registry, state, "piratecontract1", {"position": position})
    new = _play(registry, state, "piratecontract1", {"position": "104"})
    assert new.systems["104"].space_units[NEUTRAL_PLAYER_ID] == {"fighter": 1, "destroyer": 1}


def test_pirate_contract_niezagrywalna_bez_celow(registry: StaticDataRegistry) -> None:
    systems = [
        _system(pos, sid, space_units={"p2": {"cruiser": 1}})
        for pos, sid in (("000", "18"), ("101", "113"), ("102", "115"), ("104", "02"),
                         ("106", "04"))
    ]
    assert not _playable(registry, _state(["piratecontract1"], systems), "piratecontract1")


# ------------------------------------------------------------------------------ Pirate Fleet


def test_pirate_fleet_za_3_zasoby_stawia_flote_neutralnych(registry: StaticDataRegistry) -> None:
    state = _state(["piratefleet"], trade_goods=4)
    inputs = _inputs(registry, state, "piratefleet")
    assert [item["key"] for item in inputs] == ["position", "planets", "trade_goods"]
    new = _play(registry, state, "piratefleet", {"position": "101", "trade_goods": 3})
    assert new.systems["101"].space_units[NEUTRAL_PLAYER_ID] == {
        "carrier": 1, "cruiser": 1, "destroyer": 1, "fighter": 2,
    }
    assert new.players["p1"].trade_goods == 1


def test_pirate_fleet_placi_zasobami_planet(registry: StaticDataRegistry) -> None:
    state = _state(["piratefleet"], [_system("104", "02", planet_owners={"mollprimus": "p1"})])
    assert registry.planets["mollprimus"].resources >= 3  # dane, nie pamięć: planeta wystarcza
    inputs = _inputs(registry, state, "piratefleet")
    assert [o["value"] for o in inputs[1]["options"]] == ["mollprimus"]
    new = _play(registry, state, "piratefleet", {"position": "101", "planets": ["mollprimus"]})
    assert "mollprimus" in new.players["p1"].exhausted_planets
    assert new.systems["101"].space_units[NEUTRAL_PLAYER_ID]["fighter"] == 2


def test_pirate_fleet_odrzuca_za_malo_zasobow_i_zly_system(registry: StaticDataRegistry) -> None:
    state = _state(["piratefleet"], trade_goods=2)
    with pytest.raises(ValueError, match="at least 3 resources"):
        _play(registry, state, "piratefleet", {"position": "101", "trade_goods": 2})
    state.players["p1"].trade_goods = 5
    with pytest.raises(ValueError, match="non-home system"):
        _play(registry, state, "piratefleet", {"position": "103", "trade_goods": 3})
    assert not _playable(registry, _state(["piratefleet"], trade_goods=2), "piratefleet")


# ------------------------------------------------------------------------- Exchange Program


def _exchange_state() -> GameState:
    return _state(
        ["exchangeprogram"],
        [
            _system(
                "103", "01",
                planet_owners={"jord": "p1"},
                planet_units={"jord": {"p1": {"infantry": 2}}},
            ),
            _system(
                "105", "03",
                planet_owners={"darien": "p2"},
                planet_units={"darien": {"p2": {"mech": 1}}},
            ),
        ],
    )


def test_exchange_program_za_zgoda_obaj_stawiaja_piechote_w_koegzystencji(
    registry: StaticDataRegistry,
) -> None:
    state = _exchange_state()
    inputs = _inputs(registry, state, "exchangeprogram")
    values = [o["value"] for o in inputs[0]["options"]]
    assert {"player": "p2", "agreed": False} in values
    agreed = {"player": "p2", "agreed": True, "their_planet": "darien", "my_planet": "jord"}
    assert agreed in values
    new = _play(registry, state, "exchangeprogram", agreed)
    assert new.systems["105"].planet_units["darien"]["p1"] == {"infantry": 1}
    assert new.systems["103"].planet_units["jord"]["p2"] == {"infantry": 1}
    # kontrola się nie zmienia (R_coexistence)
    assert new.systems["105"].planet_owners["darien"] == "p2"
    assert new.systems["103"].planet_owners["jord"] == "p1"


def test_exchange_program_bez_zgody_obaj_odrzucaja_zeton_z_fleet_pool(
    registry: StaticDataRegistry,
) -> None:
    state = _exchange_state()
    new = _play(registry, state, "exchangeprogram", {"player": "p2", "agreed": False})
    for pid in ("p1", "p2"):
        assert new.players[pid].fleet_cc == 2
        assert new.players[pid].cc_reinf == 9
    assert "p1" not in new.systems["105"].planet_units["darien"]


def test_exchange_program_bez_zgody_pomija_gracza_bez_zetonow_w_fleet_pool(
    registry: StaticDataRegistry,
) -> None:
    state = _exchange_state()
    state.players["p2"].fleet_cc = 0
    new = _play(registry, state, "exchangeprogram", {"player": "p2", "agreed": False})
    assert (new.players["p1"].fleet_cc, new.players["p2"].fleet_cc) == (2, 0)
    assert new.players["p2"].cc_reinf == 8


def test_exchange_program_odrzuca_zle_planety_i_brak_decyzji(registry: StaticDataRegistry) -> None:
    state = _exchange_state()
    with pytest.raises(ValueError, match="agreement"):
        _play(registry, state, "exchangeprogram", {"player": "p2"})
    with pytest.raises(ValueError, match="another player"):
        _play(registry, state, "exchangeprogram", {"player": "p1", "agreed": False})
    swapped = {"player": "p2", "agreed": True, "their_planet": "jord", "my_planet": "darien"}
    with pytest.raises(ValueError, match="Choose a planet"):
        _play(registry, state, "exchangeprogram", swapped)
    state.systems["105"].planet_units["darien"] = {}  # partner bez sił naziemnych
    options = _inputs(registry, state, "exchangeprogram")[0]["options"]
    assert all(not o["value"]["agreed"] for o in options)
    assert _playable(registry, state, "exchangeprogram")  # opcja „bez zgody” zostaje


# ------------------------------------------------------------------------------- Overrule


def test_overrule_wykonuje_primary_bez_wyczerpania_karty_i_bez_okna_secondary(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["overrule"])
    inputs = _inputs(registry, state, "overrule")
    assert [o["value"] for o in inputs[0]["options"]] == [1, 2, 3, 4, 5, 6, 7, 8]
    new = _play(registry, state, "overrule", {"initiative": 1})
    assert new.pending_strategy is not None
    assert (new.pending_strategy.initiative, new.pending_strategy.owner_id) == (1, "p1")
    assert new.pending_strategy.no_secondary
    new = strategic_action.submit_primary_step(new, registry, "p1", {})
    new = strategic_action.submit_primary_step(new, registry, "p1", {"tactical": 3})
    assert new.players["p1"].tactical_cc == 6  # Leadership: +3 żetony
    assert new.pending_strategy is None
    assert new.pending_window is None  # bez secondary dla pozostałych
    assert new.players["p1"].exhausted_strategy_cards == []


def test_overrule_tylko_karty_readied_lub_unchosen(registry: StaticDataRegistry) -> None:
    state = _state(["overrule"])
    state.players["p2"].strategy_cards = [5, 6]
    state.players["p2"].exhausted_strategy_cards = [5]  # wyczerpana (już zagrana)
    options = [o["value"] for o in _inputs(registry, state, "overrule")[0]["options"]]
    assert 5 not in options and 6 in options and 1 in options
    with pytest.raises(ValueError, match="readied or unchosen"):
        _play(registry, state, "overrule", {"initiative": 5})
    with pytest.raises(ValueError, match="readied or unchosen"):
        _play(registry, state, "overrule", {"initiative": 99})
    with pytest.raises(ValueError, match="readied or unchosen"):
        _play(registry, state, "overrule", {})


def test_overrule_niezagrywalna_gdy_karty_wyczerpane(registry: StaticDataRegistry) -> None:
    state = _state(["overrule"])
    state.players["p2"].strategy_cards = list(range(1, 9))
    state.players["p2"].exhausted_strategy_cards = list(range(1, 9))
    assert not _playable(registry, state, "overrule")


# ------------------------------------------------------------------------------- Strategize


@pytest.mark.parametrize("card", ["strategize1", "strategize2", "strategize3", "strategize4"])
def test_strategize_otwiera_secondary_dla_zagrywajacego(
    registry: StaticDataRegistry, card: str
) -> None:
    state = _state([card])
    inputs = _inputs(registry, state, card)
    assert len(inputs[0]["options"]) == 8
    new = _play(registry, state, card, {"initiative": 1})
    window = new.pending_window
    assert window is not None
    assert window.window_type is WindowType.STRATEGY_SECONDARY
    assert window.current_responder == "p1"
    assert window.context["initiative"] == 1
    assert window.context["cost"] == 0  # Leadership: bez żetonu
    done = strategic_action.resolve_secondary(new, registry, "p1", execute=True, payload={})
    assert done.pending_window is None
    assert done.players["p1"].strategic_cc == 2  # Leadership nie kosztuje


def test_strategize_secondary_kosztuje_zeton_ze_strategy_pool_poza_leadership(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["strategize1"], strategic_cc=0)
    new = _play(registry, state, "strategize1", {"initiative": 4})
    assert new.pending_window is not None and new.pending_window.context["cost"] == 1
    with pytest.raises(ValueError, match="strategy pool"):
        strategic_action.resolve_secondary(new, registry, "p1", execute=True, payload={})


def test_strategize_odrzuca_wyczerpana_karte(registry: StaticDataRegistry) -> None:
    state = _state(["strategize1"])
    state.players["p2"].strategy_cards = [3]
    state.players["p2"].exhausted_strategy_cards = [3]
    with pytest.raises(ValueError, match="readied or unchosen"):
        _play(registry, state, "strategize1", {"initiative": 3})
    options = [o["value"] for o in _inputs(registry, state, "strategize1")[0]["options"]]
    assert 3 not in options
