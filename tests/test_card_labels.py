"""Czytelność formularzy kart: etykiety z zasobami/wpływem, niepuste hinty, podglądy skutku."""

from __future__ import annotations

from typing import Any

import pytest

from src.core import action_cards, planet_stats, rules_hooks
from src.core.components import ActionCardDef, ComponentCategory
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hooks import card_labels
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(registry: StaticDataRegistry, planets: tuple[str, ...]) -> GameState:
    """p1 w systemie 000 z podanymi planetami i okrętem, p2 w 101 (sąsiad, z okrętem)."""
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="sol"),
            "p2": PlayerState(player_id="p2", color="blue", faction="arborec"),
        },
        systems={
            "000": SystemState(
                position="000",
                system_id="18",
                planet_owners={p: "p1" for p in planets},
                space_units={"p1": {"destroyer": 1}},
            ),
            "101": SystemState(
                position="101", system_id="19", space_units={"p2": {"destroyer": 1}}
            ),
        },
    )
    return state


def test_opis_planety_ma_zasoby_wplyw_i_system(registry: StaticDataRegistry) -> None:
    planet = next(p for p in sorted(registry.planets) if registry.planets[p].influence > 0)
    state = _state(registry, (planet,))
    stats = planet_stats.planet_stats(state, registry, planet)
    assert stats is not None
    text = card_labels.describe_planet(state, registry, planet)
    assert registry.planets[planet].name in text
    assert f"{stats.resources} resource" in text
    assert f"{stats.influence} influence" in text
    assert "system 000" in text


def test_opis_planety_ze_skutkiem(registry: StaticDataRegistry) -> None:
    planet = next(iter(sorted(registry.planets)))
    state = _state(registry, (planet,))
    assert card_labels.describe_planet(state, registry, planet, effect="+2 trade goods").endswith(
        "→ +2 trade goods"
    )


def test_opis_gracza_to_frakcja_i_kolor(registry: StaticDataRegistry) -> None:
    state = _state(registry, ())
    text = card_labels.describe_player(state, registry, "p1")
    assert text.endswith("(red)")
    assert text != "p1 (red)"


def test_opis_systemu_ma_pozycje_i_planety(registry: StaticDataRegistry) -> None:
    state = _state(registry, ())
    text = card_labels.describe_system(state, registry, "000")
    assert text.startswith("System 000")
    definition = registry.systems["18"]
    for planet in definition.planets:
        assert registry.planets[planet].name in text


def test_mining_initiative_pokazuje_zasoby_i_skutek(registry: StaticDataRegistry) -> None:
    planet = next(
        p for p in sorted(registry.planets) if registry.planets[p].resources >= 2
    )
    state = _state(registry, (planet,))
    state.players["p1"].private.action_cards = ["mining_initiative"]
    implemented, inputs = action_cards.card_inputs(state, registry, "p1", "mining_initiative")
    assert implemented
    label = inputs[0]["options"][0]["label"]
    resources = registry.planets[planet].resources
    assert f"{resources} resources" in label
    assert f"+{resources} trade goods" in label
    assert inputs[0]["hint"]


def test_podglad_kart_bez_wyborow_ma_tekst(registry: StaticDataRegistry) -> None:
    state = _state(registry, ())
    state.players["p1"].commodity_value = 3
    keys = rules_hooks.all_previews()
    assert "action_cards:industrial_initiative" in keys
    assert "action_cards:messiah" in keys
    for key in keys:
        preview = rules_hooks.preview_for(key)
        assert preview is not None
        assert preview(state, registry, "p1").strip(), key
    summary = action_cards.card_summary(state, registry, "p1", "industrial_initiative")
    assert summary is not None and "+0 trade goods" in summary
    assert action_cards.card_summary(state, registry, "p1", "sabo1") is None


def test_kazdy_formularz_ma_hint_i_etykiety_opcji(registry: StaticDataRegistry) -> None:
    """Dla WSZYSTKICH zarejestrowanych formularzy kart akcji: hint niepusty, opcje mają label."""
    planets = tuple(
        p for p in sorted(registry.planets) if registry.systems["18"].planets.count(p)
    )
    state = _state(registry, planets)
    checked = 0
    for key in rules_hooks.all_input_keys():
        if not key.startswith("action_cards:"):
            continue
        card_id = key.split(":", 1)[1]
        card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
        if not isinstance(card, ActionCardDef):
            continue
        trial = state.model_copy(deep=True)
        trial.players["p1"].private.action_cards = [card_id]
        try:
            _implemented, inputs = action_cards.card_inputs(trial, registry, "p1", card_id)
        except Exception as exc:  # noqa: BLE001 - formularz nie może się wywracać na prostym stanie
            raise AssertionError(f"{key}: {exc!r}") from exc
        checked += 1
        for item in inputs:
            assert str(item.get("hint") or "").strip(), f"{key}/{item['key']}: pusty hint"
            options: list[dict[str, Any]] = item.get("options") or []
            for option in options:
                label = str(option.get("label") or "").strip()
                assert label, f"{key}/{item['key']}: pusta etykieta"
    assert checked >= 50


# ----------------------------------------------------------------- odnośniki do komponentów


@pytest.mark.parametrize(
    "component_key", ["action_cards:strategize1", "action_cards:overrule", "leaders:winnuhero"]
)
def test_karty_strategii_w_formularzach_maja_nazwe_i_odnosnik(
    registry: StaticDataRegistry, component_key: str
) -> None:
    """Strategize / Overrule / Imperial Seal: opcja = nazwa karty + inicjatywa + ``ref`` (UI
    pokazuje tekst primary/secondary i pełną kartę po kliknięciu), nigdy „Strategy card 3”."""
    state = _state(registry, ())
    inputs_fn = rules_hooks.inputs_for(component_key)
    assert inputs_fn is not None
    inputs = inputs_fn(state, registry, "p1")
    key = "card" if component_key.startswith("leaders:") else "initiative"
    item = next(i for i in inputs if i["key"] == key)
    assert item["options"]
    names = {card.initiative: card.name for card in registry.strategy_card_set()}
    for option in item["options"]:
        initiative = int(option["value"])
        assert option["meta"]["ref"] == {"kind": "strategy", "id": str(initiative)}
        assert option["label"].startswith(f"{names[initiative]} - initiative {initiative}")


def test_odnosnik_nieznanego_rodzaju_to_blad() -> None:
    from src.core import offer_inputs

    assert offer_inputs.option(1, "x", ref=("strategy", 1))["meta"]["ref"]["id"] == "1"
    with pytest.raises(ValueError):
        offer_inputs.option(1, "x", ref=("nonsense", 1))
