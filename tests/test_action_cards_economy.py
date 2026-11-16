"""Testy kart akcji (okno ACTION) z grupy ekonomia: technologie, relikty, planety (RULES.md 53)."""

from __future__ import annotations

from typing import Any

import pytest

from src.core import action_cards, exploration, triggers
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.offers import offer_view
from src.core.registry import StaticDataRegistry

_HAZARDOUS = "abyz"  # planeta hazardous, 3 zasoby, nie jest domowa
_SPECIALTY_BIOTIC = "faunus"  # planeta ze specjalnością BIOTIC
_SPECIALTY_PROPULSION = "andeara"
_HOME_ARBOREC = "nestphar"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(
    hand: list[str],
    *,
    mine: tuple[str, ...] = (),
    theirs: tuple[str, ...] = (),
    far: bool = False,
    **p1: Any,
) -> GameState:
    """p1 (sol) w systemie 000, p2 (arborec) w sąsiednim 101 (``far`` = daleko, 301)."""
    p2_position = "301" if far else "101"
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="sol", **p1),
            "p2": PlayerState(player_id="p2", color="blue", faction="arborec"),
        },
        systems={
            # Obecność obu graczy (okręt) jest warunkiem sąsiedztwa (R_neighbors).
            "000": SystemState(
                position="000", system_id="18", planet_owners={p: "p1" for p in mine},
                space_units={"p1": {"destroyer": 1}},
            ),
            p2_position: SystemState(
                position=p2_position, system_id="19", planet_owners={p: "p2" for p in theirs},
                space_units={"p2": {"destroyer": 1}},
            ),
        },
    )
    state.players["p1"].private.action_cards = list(hand)
    return state


def _play(
    state: GameState, registry: StaticDataRegistry, card: str, params: dict[str, Any] | None = None
) -> GameState:
    new, implemented = action_cards.play_action_card(state, registry, "p1", card, params)
    assert implemented
    return new


def _inputs(state: GameState, registry: StaticDataRegistry, card: str) -> list[dict[str, Any]]:
    implemented, inputs = action_cards.card_inputs(state, registry, "p1", card)
    assert implemented
    return inputs


def _option_values(inputs: list[dict[str, Any]], key: str) -> list[Any]:
    item = next(i for i in inputs if i["key"] == key)
    return [o["value"] for o in item["options"]]


def _playable(state: GameState, registry: StaticDataRegistry, card: str) -> dict[str, object]:
    rows = action_cards.playability(state, registry, "p1")
    return next(r for r in rows if r["card_id"] == card)


# ---------------------------------------------------------------- Archaeological Expedition


def _cultural_planet(registry: StaticDataRegistry) -> str:
    return next(
        p
        for p in sorted(registry.planets)
        if exploration.planet_traits(registry, p) == ["cultural"]
    )


def _cultural_filler(registry: StaticDataRegistry, n: int) -> list[str]:
    ids = [c for c in exploration.deck_card_ids(registry, "cultural") if not c.startswith("crf")]
    return ids[:n]


def test_arch_expedition_bierze_fragmenty_a_reszte_odrzuca(registry: StaticDataRegistry) -> None:
    cultural = _cultural_planet(registry)
    filler = _cultural_filler(registry, 3)
    state = _state(["arch_expedition"], mine=(cultural,))
    state.decks.exploration_deck["cultural"] = ["crf1", filler[0], "crf2", filler[1], filler[2]]
    new = _play(state, registry, "arch_expedition", {"deck": "cultural"})
    assert new.players["p1"].relic_fragments == ["crf1", "crf2"]
    assert new.decks.exploration_discard["cultural"] == [filler[0]]
    assert new.decks.exploration_deck["cultural"] == [filler[1], filler[2]]
    assert state.players["p1"].relic_fragments == []  # wejście nietknięte


def test_arch_expedition_wymaga_talii_pasujacej_do_planety(registry: StaticDataRegistry) -> None:
    state = _state(["arch_expedition"], mine=(_HAZARDOUS,))
    with pytest.raises(ValueError, match="matches a planet you control"):
        action_cards.play_action_card(
            state, registry, "p1", "arch_expedition", {"deck": "cultural"}
        )
    inputs = _inputs(state, registry, "arch_expedition")
    assert _option_values(inputs, "deck") == ["hazardous"]


def test_arch_expedition_bez_planet_z_cecha_jest_niezagrywalna(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["arch_expedition"])
    row = _playable(state, registry, "arch_expedition")
    assert row["implemented"] and not row["playable"]
    assert "No legal target" in str(row["reason"])


# ------------------------------------------------------------------------------- Brilliance


def test_brilliance_odswieza_planete_ze_specjalnoscia(registry: StaticDataRegistry) -> None:
    state = _state(
        ["brilliance"], mine=(_SPECIALTY_BIOTIC, _HAZARDOUS),
        exhausted_planets=[_SPECIALTY_BIOTIC, _HAZARDOUS],
    )
    params = {"mode": "ready_planet", "planet": _SPECIALTY_BIOTIC}
    new = _play(state, registry, "brilliance", params)
    assert new.players["p1"].exhausted_planets == [_HAZARDOUS]
    with pytest.raises(ValueError, match="technology specialty"):
        action_cards.play_action_card(
            state, registry, "p1", "brilliance", {"mode": "ready_planet", "planet": _HAZARDOUS}
        )


def test_brilliance_daje_przelom_wskazanemu_graczowi_takze_sobie(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["brilliance"])
    state.fracture.in_play = True  # bez rzutu na The Fracture (wynik testu nie zależy od losu)
    new = _play(state, registry, "brilliance", {"mode": "breakthrough", "player": "p2"})
    assert new.players["p2"].breakthrough_unlocked and not new.players["p1"].breakthrough_unlocked
    own = _play(state, registry, "brilliance", {"mode": "breakthrough", "player": "p1"})
    assert own.players["p1"].breakthrough_unlocked


def test_brilliance_przelom_robi_rzut_na_fracture_dla_kazdego_ziarna(
    registry: StaticDataRegistry,
) -> None:
    entered = 0
    for seed in range(1, 41):
        state = _state(["brilliance"], mine=(_SPECIALTY_BIOTIC,))
        state.rng_seed = seed
        new = _play(state, registry, "brilliance", {"mode": "breakthrough", "player": "p1"})
        assert new.players["p1"].breakthrough_unlocked
        assert new.fracture.last_roll is not None  # rzut wykonany (UI animuje kość)
        entered += int(new.fracture.in_play)
    assert entered > 0  # przy 40 ziarnach co najmniej raz wypadło 1 albo 10


def test_brilliance_odrzuca_przelom_juz_zdobyty_i_zly_tryb(registry: StaticDataRegistry) -> None:
    state = _state(["brilliance"])
    state.fracture.in_play = True
    state.players["p2"].breakthrough_unlocked = True
    with pytest.raises(ValueError, match="breakthrough"):
        action_cards.play_action_card(
            state, registry, "p1", "brilliance", {"mode": "breakthrough", "player": "p2"}
        )
    with pytest.raises(ValueError, match="mode"):
        action_cards.play_action_card(state, registry, "p1", "brilliance", {"mode": "x"})


def test_brilliance_formularz_i_zagrywalnosc(registry: StaticDataRegistry) -> None:
    state = _state(["brilliance"], mine=(_SPECIALTY_BIOTIC,))
    values = _option_values(_inputs(state, registry, "brilliance"), "effect")
    assert {"mode": "ready_planet", "planet": _SPECIALTY_BIOTIC} in values
    assert {"mode": "breakthrough", "player": "p2"} in values
    empty = _state(["brilliance"])
    empty.players["p1"].faction = None
    empty.players["p2"].breakthrough_unlocked = True
    assert not _playable(empty, registry, "brilliance")["playable"]


# ------------------------------------------------------------------------- Focused Research


def _research(
    state: GameState, tech: str, skips: list[str] | None = None, player: str = "p1"
) -> GameState:
    """Odpowiedź w oknie badania (decyzja ``research`` po zagraniu karty)."""
    offer = next(
        o for o in state.pending_offers if o.player_id == player and "research_cost" in o.ctx
    )
    payload = {"tech": tech, "skips": skips or [], "planets": [], "trade_goods": 0}
    return triggers.accept_offer(state, player, offer.id, {"research": payload})


def test_focused_research_kosztuje_cztery_tg(registry: StaticDataRegistry) -> None:
    state = _state(["f_researched"], trade_goods=5)
    played = _play(state, registry, "f_researched")
    # Technologię wybiera się PO zagraniu, w oknie badania (decyzja obowiązkowa gracza).
    assert played.players["p1"].trade_goods == 5
    offer = next(o for o in played.pending_offers if "research_cost" in o.ctx)
    assert offer.mandatory
    new = _research(played, "nm")
    assert "nm" in new.players["p1"].technologies
    assert new.players["p1"].trade_goods == 1
    assert not new.pending_offers


def test_focused_research_rezygnacja(registry: StaticDataRegistry) -> None:
    played = _play(_state(["f_researched"], trade_goods=5), registry, "f_researched")
    offer = next(o for o in played.pending_offers if "research_cost" in o.ctx)
    new = triggers.accept_offer(played, "p1", offer.id, {"research": {"tech": None}})
    assert new.players["p1"].trade_goods == 5 and not new.pending_offers


def test_focused_research_wymaga_tg_i_prerekwizytow(registry: StaticDataRegistry) -> None:
    poor = _state(["f_researched"], trade_goods=3)
    with pytest.raises(ValueError, match="You need 4 trade goods"):
        action_cards.play_action_card(poor, registry, "p1", "f_researched")
    row = _playable(poor, registry, "f_researched")
    assert not row["playable"] and "No legal target" in str(row["reason"])
    rich = _play(_state(["f_researched"], trade_goods=4), registry, "f_researched")
    with pytest.raises(ValueError, match="Prerequisites"):
        _research(rich, "dxa")
    assert rich.players["p1"].trade_goods == 4  # nieudana odpowiedź nic nie kosztuje


def test_focused_research_uzywa_specjalnosci_planety(registry: StaticDataRegistry) -> None:
    state = _state(["f_researched"], mine=(_SPECIALTY_BIOTIC,), trade_goods=4)
    inputs = _inputs(state, registry, "f_researched")
    assert inputs[0]["kind"] == "info"
    assert "dxa" in _option_values(inputs, "research_after")  # G pokryje planeta BIOTIC
    played = _play(state, registry, "f_researched")
    offer = next(o for o in played.pending_offers if "research_cost" in o.ctx)
    view = offer_view(played, registry, offer)["inputs"][0]
    assert view["kind"] == "research" and view["research"]["trade_goods_only"] is True
    assert view["research"]["cost"] == 4 and view["research"]["planets"] == {}
    new = _research(played, "dxa", [_SPECIALTY_BIOTIC])
    assert "dxa" in new.players["p1"].technologies
    assert _SPECIALTY_BIOTIC in new.players["p1"].exhausted_planets


# ------------------------------------------------------------------------- Divert Funding


def test_divert_funding_zwraca_i_bada_inna(registry: StaticDataRegistry) -> None:
    """Badaną technologię wybiera się PO zagraniu, w oknie badania (F_xxcha, Instinct Training)."""
    state = _state(["divert_funding"], technologies=["nm", "st"], exhausted_technologies=["nm"])
    played = _play(state, registry, "divert_funding", {"return_technology": "nm"})
    assert sorted(played.players["p1"].technologies) == ["st"]
    assert played.players["p1"].exhausted_technologies == []  # zwrócona wróci gotowa
    offer = next(o for o in played.pending_offers if "research_cost" in o.ctx)
    assert offer.ctx["research_cost"] == 0 and "nm" not in offer.ctx["research_allowed"]
    new = _research(played, "gls")
    assert sorted(new.players["p1"].technologies) == ["gls", "st"]


def test_divert_funding_odrzuca_nielegalne_wybory(registry: StaticDataRegistry) -> None:
    state = _state(["divert_funding"], technologies=["nm", "st", "inf2"])

    def play(**params: str) -> None:
        action_cards.play_action_card(state, registry, "p1", "divert_funding", dict(params))

    with pytest.raises(ValueError, match="non-unit upgrade"):
        play(return_technology="inf2")
    with pytest.raises(ValueError, match="non-unit upgrade"):
        play(return_technology="zzz")
    played = _play(state, registry, "divert_funding", {"return_technology": "nm"})
    with pytest.raises(ValueError, match="cannot be researched"):
        _research(played, "nm")  # zwrócona - nie wolno jej zbadać ponownie
    # Zwrócona technologia nie liczy się do prerekwizytów: dxa (G) bez nm się nie uda.
    with pytest.raises(ValueError):
        _research(played, "dxa")
    assert sorted(state.players["p1"].technologies) == ["inf2", "nm", "st"]


def test_divert_funding_formularz_i_zagrywalnosc(registry: StaticDataRegistry) -> None:
    state = _state(["divert_funding"], technologies=["nm", "st", "inf2"])
    inputs = _inputs(state, registry, "divert_funding")
    assert sorted(_option_values(inputs, "return_technology")) == ["nm", "st"]
    research = _option_values(inputs, "research_after")
    assert "gls" in research and "st" not in research and "inf2" not in research
    assert _playable(state, registry, "divert_funding")["playable"]
    only_upgrade = _state(["divert_funding"], technologies=["inf2"])
    assert not _playable(only_upgrade, registry, "divert_funding")["playable"]


# ----------------------------------------------------------------------------- Plagiarize


def test_plagiarize_kopiuje_technologie_sasiada(registry: StaticDataRegistry) -> None:
    state = _state(["plagiarize"], trade_goods=5)
    state.players["p2"].technologies = ["nm"]
    inputs = _inputs(state, registry, "plagiarize")
    assert _option_values(inputs, "technology") == ["nm"]
    new = _play(state, registry, "plagiarize", {"technology": "nm", "trade_goods": 5})
    assert "nm" in new.players["p1"].technologies and new.players["p1"].trade_goods == 0
    assert "nm" in new.players["p2"].technologies  # sąsiad nie traci technologii


def test_plagiarize_platnosc_wplywem_z_planet(registry: StaticDataRegistry) -> None:
    influence = {p: registry.planets[p].influence for p in sorted(registry.planets)}
    pair = [p for p, v in influence.items() if v >= 2][:3]
    paid = sum(influence[p] for p in pair)
    assert paid >= 5 or len(pair) < 3
    state = _state(["plagiarize"], mine=tuple(pair), trade_goods=max(0, 5 - paid))
    state.players["p2"].technologies = ["nm"]
    new = _play(
        state, registry, "plagiarize",
        {"technology": "nm", "planets": pair, "trade_goods": max(0, 5 - paid)},
    )
    assert set(pair) <= set(new.players["p1"].exhausted_planets)


def test_plagiarize_odrzuca_za_malo_wplywu_nie_sasiada_i_techy_frakcyjne(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["plagiarize"], trade_goods=4)
    state.players["p2"].technologies = ["nm"]
    with pytest.raises(ValueError, match="at least 5 influence"):
        action_cards.play_action_card(
            state, registry, "p1", "plagiarize", {"technology": "nm", "trade_goods": 4}
        )
    assert not _playable(state, registry, "plagiarize")["playable"]  # 4 < 5 dostępnego wpływu
    faction_tech = registry.factions["arborec"].faction_tech[0]
    state.players["p1"].trade_goods = 5
    state.players["p2"].technologies = [faction_tech]
    with pytest.raises(ValueError, match="non-faction"):
        action_cards.play_action_card(
            state, registry, "p1", "plagiarize", {"technology": faction_tech, "trade_goods": 5}
        )
    far = _state(["plagiarize"], far=True, trade_goods=5)
    far.players["p2"].technologies = ["nm"]
    with pytest.raises(ValueError, match="neighbors"):
        action_cards.play_action_card(
            far, registry, "p1", "plagiarize", {"technology": "nm", "trade_goods": 5}
        )
    assert not _playable(far, registry, "plagiarize")["playable"]


# ------------------------------------------------------------------------ Seize Artifact


def test_seize_artifact_zabiera_wybrany_fragment(registry: StaticDataRegistry) -> None:
    state = _state(["seize"])
    state.players["p2"].relic_fragments = ["crf1", "hrf1"]
    inputs = _inputs(state, registry, "seize")
    assert {"player": "p2", "fragment": "hrf1"} in _option_values(inputs, "target")
    new = _play(state, registry, "seize", {"player": "p2", "fragment": "hrf1"})
    assert new.players["p1"].relic_fragments == ["hrf1"]
    assert new.players["p2"].relic_fragments == ["crf1"]


def test_seize_artifact_wymaga_sasiada_z_fragmentem(registry: StaticDataRegistry) -> None:
    state = _state(["seize"])
    state.players["p2"].relic_fragments = ["crf1"]
    with pytest.raises(ValueError, match="does not have the relic fragment"):
        action_cards.play_action_card(
            state, registry, "p1", "seize", {"player": "p2", "fragment": "hrf1"}
        )
    far = _state(["seize"], far=True)
    far.players["p2"].relic_fragments = ["crf1"]
    with pytest.raises(ValueError, match="neighbors"):
        action_cards.play_action_card(
            far, registry, "p1", "seize", {"player": "p2", "fragment": "crf1"}
        )
    assert not _playable(far, registry, "seize")["playable"]
    assert not _playable(_state(["seize"]), registry, "seize")["playable"]  # sąsiad bez fragmentów


# --------------------------------------------------------------------------------- Uprising


def test_uprising_wyczerpuje_cudza_planete_i_daje_tg(registry: StaticDataRegistry) -> None:
    state = _state(["uprising"], theirs=(_HAZARDOUS,))
    new = _play(state, registry, "uprising", {"planet": _HAZARDOUS})
    assert new.players["p2"].exhausted_planets == [_HAZARDOUS]
    assert new.players["p1"].trade_goods == registry.planets[_HAZARDOUS].resources


def test_uprising_odrzuca_wlasna_domowa_i_wyczerpana(registry: StaticDataRegistry) -> None:
    state = _state(
        ["uprising"], mine=(_SPECIALTY_BIOTIC,), theirs=(_HOME_ARBOREC, _HAZARDOUS)
    )
    for planet in (_SPECIALTY_BIOTIC, _HOME_ARBOREC):
        with pytest.raises(ValueError, match="non-home planet controlled by another player"):
            action_cards.play_action_card(state, registry, "p1", "uprising", {"planet": planet})
    state.players["p2"].exhausted_planets = [_HAZARDOUS]
    with pytest.raises(ValueError, match="ready"):
        action_cards.play_action_card(state, registry, "p1", "uprising", {"planet": _HAZARDOUS})
    assert _option_values(_inputs(state, registry, "uprising"), "planet") == []
    assert not _playable(state, registry, "uprising")["playable"]


# ------------------------------------------------------------------------ Exploration Probe


def _probe_state(far_token: bool = False) -> GameState:
    state = _state(["probe"])
    state.systems["000"].space_units = {"p1": {"cruiser": 1}}
    token_at = "201" if far_token else "101"
    state.systems[token_at] = SystemState(position=token_at, system_id="41", frontier_token=True)
    return state


def test_probe_bada_frontier_obok_wlasnego_statku(registry: StaticDataRegistry) -> None:
    state = _probe_state()
    assert _option_values(_inputs(state, registry, "probe"), "position") == ["101"]
    new = _play(state, registry, "probe", {"position": "101"})
    assert not new.systems["101"].frontier_token
    assert new.exploration is not None
    assert new.exploration.current is not None and new.exploration.current.deck == "frontier"


def test_probe_w_systemie_ze_statkiem(registry: StaticDataRegistry) -> None:
    state = _probe_state()
    state.systems["000"].frontier_token = True
    state.systems["101"].frontier_token = False
    new = _play(state, registry, "probe", {"position": "000"})
    assert new.exploration is not None


def test_probe_odrzuca_zeton_poza_zasiegiem(registry: StaticDataRegistry) -> None:
    state = _probe_state(far_token=True)
    with pytest.raises(ValueError, match="adjacent"):
        action_cards.play_action_card(state, registry, "p1", "probe", {"position": "201"})
    assert not _playable(state, registry, "probe")["playable"]


# ---------------------------------------------------------------------------- Unstable Planet


def _unstable_state(infantry: int) -> GameState:
    state = _state(["unstable"], theirs=(_HAZARDOUS, _SPECIALTY_BIOTIC))
    state.systems["101"].planet_units = {_HAZARDOUS: {"p2": {"infantry": infantry}}}
    return state


def test_unstable_planet_wyczerpuje_i_niszczy_wybrana_liczbe(registry: StaticDataRegistry) -> None:
    new = _play(_unstable_state(4), registry, "unstable", {"planet": _HAZARDOUS, "count": 2})
    assert new.systems["101"].planet_units[_HAZARDOUS]["p2"]["infantry"] == 2
    assert new.players["p2"].exhausted_planets == [_HAZARDOUS]
    zero = _play(_unstable_state(4), registry, "unstable", {"planet": _HAZARDOUS, "count": 0})
    assert zero.systems["101"].planet_units[_HAZARDOUS]["p2"]["infantry"] == 4
    assert zero.players["p2"].exhausted_planets == [_HAZARDOUS]


def test_unstable_planet_odrzuca_zle_wybory(registry: StaticDataRegistry) -> None:
    state = _unstable_state(2)
    for params in (
        {"planet": _SPECIALTY_BIOTIC, "count": 1},  # nie hazardous
        {"planet": _HAZARDOUS, "count": 4},  # ponad limit 3
        {"planet": _HAZARDOUS, "count": 3},  # więcej niż stoi na planecie
        {"planet": _HAZARDOUS, "count": -1},
    ):
        with pytest.raises(ValueError):  # noqa: PT011 - różne komunikaty
            action_cards.play_action_card(state, registry, "p1", "unstable", params)
    inputs = _inputs(state, registry, "unstable")
    assert _option_values(inputs, "planet") == [_HAZARDOUS]
    assert next(i for i in inputs if i["key"] == "count")["max"] == 2
    assert not _playable(_state(["unstable"]), registry, "unstable")["playable"]


# ------------------------------------------------------------------- Tactical Bombardment


def test_tactical_bombardment_wyczerpuje_cudze_planety_w_systemie(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["tactical"], theirs=(_HAZARDOUS, _SPECIALTY_BIOTIC))
    state.systems["101"].space_units = {"p1": {"dreadnought": 1}}
    state.systems["101"].planet_owners["mine"] = "p1"
    assert _option_values(_inputs(state, registry, "tactical"), "position") == ["101"]
    new = _play(state, registry, "tactical", {"position": "101"})
    assert sorted(new.players["p2"].exhausted_planets) == sorted([_HAZARDOUS, _SPECIALTY_BIOTIC])
    assert new.players["p1"].exhausted_planets == []  # własnych planet nie rusza


def test_tactical_bombardment_wymaga_jednostki_z_bombardment(registry: StaticDataRegistry) -> None:
    state = _state(["tactical"], theirs=(_HAZARDOUS,))
    state.systems["101"].space_units = {"p1": {"cruiser": 1}}  # krążownik nie bombarduje
    with pytest.raises(ValueError, match="Bombardment"):
        action_cards.play_action_card(state, registry, "p1", "tactical", {"position": "101"})
    assert not _playable(state, registry, "tactical")["playable"]
    state.systems["101"].space_units = {"p1": {"dreadnought": 1}}
    state.systems["101"].planet_owners = {}  # system bez cudzych planet też jest legalny
    done = _play(state, registry, "tactical", {"position": "101"})
    assert done.players["p1"].took_action_this_turn


# ---------------------------------------------------------------------- Reactor Meltdown


def _meltdown_state(planet: str, owner: str = "p2", position: str = "101") -> GameState:
    state = _state(["meltdown"], theirs=(planet,))
    state.systems[position].planet_units = {planet: {owner: {"spacedock": 1}}}
    return state


def test_reactor_meltdown_niszczy_cudzy_dok_poza_domem(registry: StaticDataRegistry) -> None:
    state = _meltdown_state(_HAZARDOUS)
    target = {"planet": _HAZARDOUS, "owner": "p2"}
    assert target in _option_values(_inputs(state, registry, "meltdown"), "target")
    new = _play(state, registry, "meltdown", target)
    assert new.systems["101"].planet_units[_HAZARDOUS].get("p2", {}).get("spacedock", 0) == 0


def test_reactor_meltdown_nie_rusza_wlasnych_ani_domowych_dokow(
    registry: StaticDataRegistry,
) -> None:
    home = _meltdown_state(_HOME_ARBOREC)  # dok w systemie domowym arborec
    with pytest.raises(ValueError, match="non-home"):
        action_cards.play_action_card(
            home, registry, "p1", "meltdown", {"planet": _HOME_ARBOREC, "owner": "p2"}
        )
    assert not _playable(home, registry, "meltdown")["playable"]
    own = _state(["meltdown"], mine=(_SPECIALTY_BIOTIC,))
    own.systems["000"].planet_units = {_SPECIALTY_BIOTIC: {"p1": {"spacedock": 1}}}
    with pytest.raises(ValueError, match="another player"):
        action_cards.play_action_card(
            own, registry, "p1", "meltdown", {"planet": _SPECIALTY_BIOTIC, "owner": "p1"}
        )
    assert not _playable(own, registry, "meltdown")["playable"]


# ------------------------------------------------------------ spójność formularzy z efektami


@pytest.mark.parametrize(
    "card", ["arch_expedition", "uprising", "seize", "tactical", "meltdown", "unstable"]
)
def test_formularz_daje_parametry_przyjmowane_przez_efekt(
    registry: StaticDataRegistry, card: str
) -> None:
    """Parametry zbudowane jak w UI (pierwsza opcja) przechodzą walidację efektu."""
    cultural = _cultural_planet(registry)
    state = _state([card], mine=(cultural,), theirs=(_HAZARDOUS,))
    state.systems["101"].planet_units = {
        _HAZARDOUS: {"p2": {"infantry": 2, "spacedock": 1}}
    }
    state.systems["101"].space_units = {"p1": {"dreadnought": 1}}
    state.players["p2"].relic_fragments = ["crf1"]
    inputs = _inputs(state, registry, card)
    params: dict[str, Any] = {}
    for item in inputs:
        if item["kind"] == "choice":
            value = item["options"][0]["value"]
            if item.get("merge"):
                params.update(value)
            else:
                params[item["key"]] = value
        else:
            params[item["key"]] = item["min"]
    assert _playable(state, registry, card)["playable"]
    assert action_cards.play_action_card(state, registry, "p1", card, params)[1]
