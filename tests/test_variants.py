"""Moduły wariantów gry (``assets/config/variants.json``, ``core/variants.py``).

Erraty w miejscu (komponent zachowuje oficjalne id, dostaje treść wariantu), nowe komponenty,
całe talie, parametry reguł oraz kierowanie hooków do wersji wariantu (``rules_hooks``).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.core import fracture, relics, rules_hooks, variants
from src.core.components import ComponentCategory
from src.core.exploration import deck_card_ids as explore_ids
from src.core.game_state import GameState
from src.core.objectives import deck_card_ids
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import SOURCE_RELIC, SOURCE_TECHNOLOGY, Hook, HookKind, HookSource


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(scope="module")
def bsp() -> StaticDataRegistry:
    return StaticDataRegistry(variant_ids=["bsp_factions", "bsp_cards", "absol_tech"])


@pytest.fixture
def bound(registry: StaticDataRegistry) -> Iterator[None]:
    """Przywraca rejestr bez modułów jako źródło danych hooków po teście."""
    yield
    rules_hooks.bind_registry(registry)


# --- Manifest ---------------------------------------------------------------------------------


def test_manifest_lists_fan_modules() -> None:
    mods = variants.modules()
    assert {"absol_agendas", "absol_relics", "absol_tech", "bsp_factions"} <= set(mods)
    assert mods["absol_relics"].decks == {"relic": "relics_absol"}
    assert ComponentCategory.TECHNOLOGY in mods["bsp_factions"].replaces


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"modules": [{"id": "x", "name": "X"}]}, "non-empty id, name and source"),
        ({"modules": [{"id": "x", "name": "X", "source": "s", "decks": {"tech": "t"}}]},
         "unknown deck types"),
        ({"modules": [{"id": "x", "name": "X", "source": "s", "replaces": ["nope"]}]},
         "unknown category"),
        ({"modules": [{"id": "x", "name": "X", "source": "s", "adds": ["decks"]}]},
         "use 'decks'"),
        ({"modules": [{"id": "x", "name": "X", "source": "s"},
                      {"id": "x", "name": "Y", "source": "s"}]}, "Duplicate"),
    ],
)
def test_manifest_validation(raw: object, message: str) -> None:
    with pytest.raises(variants.VariantConfigError, match=message):
        variants.parse_modules(raw)


def test_all_categories_shortcut() -> None:
    mods = variants.parse_modules(
        {"modules": [{"id": "x", "name": "X", "source": "s", "replaces": "all"}]}
    )
    assert mods["x"].replaces == variants.VARIANT_CATEGORIES


# --- Nakładanie (czyste) ----------------------------------------------------------------------


def _plan(*modules: dict[str, object]) -> variants.VariantLoadPlan:
    mods = variants.parse_modules({"modules": list(modules)}).values()
    return variants.load_plan(mods)


def test_overlay_keeps_official_id_and_remaps_references() -> None:
    plan = variants.VariantLoadPlan(
        replacements={ComponentCategory.UNIT: frozenset({"fan"})},
        adds={ComponentCategory.UNIT: frozenset({"fan"})},
        id_map={"fan_inf2": "inf2"},
    )
    entries = [
        (0, {"id": "infantry2", "source": "base", "cost": 1, "imageURL": "old.png"}),
        (1, {"id": "fan_infantry2", "source": "fan", "homebrewReplacesID": "infantry2",
             "cost": 0.5, "requiredTechId": "fan_inf2"}),
        (2, {"id": "fan_new", "source": "fan", "requiredTechId": "fan_inf2"}),
        (3, {"id": "other", "source": "elsewhere"}),
    ]
    replaced: dict[str, str] = {}
    emitted: dict[str, object] = {}
    out = dict(
        (origin, entry)
        for origin, entry in plan.overlay(
            ComponentCategory.UNIT, entries, {"base"}, replaced, emitted  # type: ignore[arg-type]
        )
    )
    assert out[0]["id"] == "infantry2" and out[0]["source"] == "base"
    assert out[0]["cost"] == 0.5 and out[0]["requiredTechId"] == "inf2"
    assert "imageURL" not in out[0]  # obrazek pokazywałby stary tekst
    assert out[0][variants.VARIANT_ID_FIELD] == "fan_infantry2"
    assert out[2]["requiredTechId"] == "inf2"  # nowy komponent też przemapowany
    assert 1 not in out and 3 in out
    assert replaced == {"units:infantry2": "fan"}
    assert set(emitted) == {"units:infantry2", "units:fan_new"}


def test_earlier_module_wins_when_two_patch_the_same_component() -> None:
    plan = variants.VariantLoadPlan(
        replacements={ComponentCategory.RELIC: frozenset({"a", "b"})},
        source_order=("b", "a"),
    )
    entries = [
        (0, {"alias": "codex", "source": "base", "text": "official"}),
        (1, {"alias": "a_codex", "source": "a", "homebrewReplacesID": "codex", "text": "A"}),
        (2, {"alias": "b_codex", "source": "b", "homebrewReplacesID": "codex", "text": "B"}),
    ]
    out = [e for _, e in plan.overlay(ComponentCategory.RELIC, entries, {"base"})]
    assert [e["text"] for e in out] == ["B"]


def test_load_plan_routes_categories() -> None:
    plan = _plan({"id": "a", "name": "A", "source": "fan", "decks": {"relic": "relics_fan"},
                  "replaces": ["action_cards"], "adds": ["technologies"]})
    assert plan.admits(ComponentCategory.RELIC, {"source": "fan", "alias": "r"})
    assert plan.admits(ComponentCategory.TECHNOLOGY, {"source": "fan", "alias": "t"})
    assert not plan.admits(ComponentCategory.ACTION_CARD, {"source": "fan", "alias": "c"})
    assert plan.is_replacement(
        ComponentCategory.ACTION_CARD, {"source": "fan", "homebrewReplacesID": "sabotage"}
    )
    assert plan.admits(ComponentCategory.DECK, {"source": "fan", "type": "relic"})
    assert not plan.admits(ComponentCategory.DECK, {"source": "fan", "type": "agenda"})


# --- Rejestr gry z modułami ---------------------------------------------------------------------


def test_default_registry_has_no_variant_data(registry: StaticDataRegistry) -> None:
    assert registry.variant_replaced == {} and registry.variant_entries == {}
    for category in (ComponentCategory.AGENDA, ComponentCategory.RELIC):
        assert not [
            c for c in registry.catalog.all(category).values()
            if c.source in variants.variant_sources()
        ]


def test_errata_change_text_stats_and_references(
    registry: StaticDataRegistry, bsp: StaticDataRegistry
) -> None:
    # Technologia: ta sama, oficjalna tożsamość, tekst Black Spectrum.
    assert bsp.technologies["st"].id == "st"
    assert "home system" in (bsp.technologies["st"].text or "")
    assert bsp.technologies["st"].text != registry.technologies["st"].text
    assert bsp.variant_replaced["technologies:st"] == "black_spectrum"
    # Jednostka: nowe liczby/zdolność, wymaganie przemapowane z ``bsp_inf2`` na ``inf2``.
    infantry = bsp.units["infantry2"]
    assert infantry.required_tech_id == "inf2"
    assert infantry.ability != registry.units["infantry2"].ability
    # Lider frakcji (Yin hero) i przełom (Obsidian/Firmament) - też w miejscu.
    assert bsp.variant_replaced["leaders:yinhero"] == "black_spectrum"
    assert bsp.breakthroughs["obsidianbt"].name == "The Reaping"
    # Karty frakcji wskazują na te same id - lista technologii frakcji bez zmian.
    assert bsp.factions["sol"].faction_tech == registry.factions["sol"].faction_tech


def test_whole_deck_modules(bsp: StaticDataRegistry) -> None:
    variants.check_decks(bsp)
    state = GameState()
    actions = deck_card_ids(bsp, "action_card", state)
    assert "bsp_direct_hit1" in actions and len(actions) == 140
    for card_id in actions:
        assert bsp.catalog.get(ComponentCategory.ACTION_CARD, card_id) is not None
    cultural = explore_ids(bsp, "cultural", state)
    assert cultural and all(
        bsp.catalog.get(ComponentCategory.EXPLORATION, c) is not None for c in cultural
    )


def test_relic_module_replaces_whole_relic_deck() -> None:
    absol = StaticDataRegistry(variant_ids=["absol_relics"])
    state = GameState()
    deck = deck_card_ids(absol, "relic", state)
    assert len(deck) == 20 and all(r.startswith("absol_") for r in deck)
    relics.ensure_relic_deck(state, absol)
    assert sorted(state.decks.relic_deck) == sorted(deck)


def test_official_decks_unchanged_without_modules(registry: StaticDataRegistry) -> None:
    state = GameState()
    for deck_type in ("action_card", "relic", "agenda", "secret_objective"):
        assert deck_card_ids(registry, deck_type, state) == deck_card_ids(registry, deck_type)


def test_ui_payload_carries_texts(bsp: StaticDataRegistry) -> None:
    payload = variants.ui_payload(bsp)
    assert payload["badges"] == {"black_spectrum": "BSP", "absol": "ABS"}
    entries, decks = payload["entries"], payload["decks"]
    assert isinstance(entries, dict) and isinstance(decks, dict)
    assert entries["technologies"]["st"]["variantSource"] == "black_spectrum"
    assert "bsp_direct_hit1" in entries["action_cards"]
    assert "bsp_direct_hit1" in decks["actionCard"] and len(decks["actionCard"]) <= 140


# --- Parametry reguł (setup Fracture) ---------------------------------------------------------


def test_rule_values_override_fracture_setup(registry: StaticDataRegistry) -> None:
    assert fracture.roll_success(registry) == frozenset({1, 10})
    custom = StaticDataRegistry(variant_ids=["absol_relics"])
    custom.variant_rules[fracture.RULE_ROLL_SUCCESS] = [1, 2, 10]
    custom.variant_rules[fracture.RULE_NEUTRAL_SETUP] = {"fracture1": {"space": {"cruiser": 1}}}
    assert fracture.roll_success(custom) == frozenset({1, 2, 10})
    assert fracture.neutral_setup(custom) == {"fracture1": {"space": {"cruiser": 1}}}


# --- Mechanika: hooki wersji wariantu --------------------------------------------------------


def _hook(source: HookSource, covers: str | None, variant: str | None) -> Hook:
    return Hook(
        "point", source, HookKind.MODIFY, lambda *_: 0, 0, covers, variant=variant
    )


def test_hook_routing_follows_component_version(
    registry: StaticDataRegistry, bsp: StaticDataRegistry, bound: None
) -> None:
    official = _hook(HookSource(SOURCE_TECHNOLOGY, "st"), None, None)
    fan = _hook(HookSource(SOURCE_TECHNOLOGY, "st"), None, "black_spectrum")
    other = _hook(HookSource(SOURCE_RELIC, "codex"), "relics:codex", None)
    rules_hooks.bind_registry(registry)
    assert rules_hooks.variant_active(official) and not rules_hooks.variant_active(fan)
    rules_hooks.bind_registry(bsp)
    assert not rules_hooks.variant_active(official) and rules_hooks.variant_active(fan)
    assert rules_hooks.variant_active(other)  # komponent bez erraty - oficjalny hook działa


def test_effects_route_to_variant_version(
    bsp: StaticDataRegistry, bound: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = "technologies:st"
    official, fan = object(), object()
    monkeypatch.setitem(rules_hooks._EFFECTS, key, official)
    rules_hooks.bind_registry(bsp)
    assert rules_hooks.effect_for(key) is None  # brak hooka wariantu = ręczna ewidencja
    monkeypatch.setitem(rules_hooks._VARIANT_EFFECTS, ("black_spectrum", key), fan)
    assert rules_hooks.effect_for(key) is fan


# --- Wybór modułów i API ------------------------------------------------------------------------


def test_selection_rules() -> None:
    assert variants.validate_selection(["absol_relics", "absol_relics"]) == ["absol_relics"]
    with pytest.raises(variants.VariantConfigError, match="Unknown game variant"):
        variants.validate_selection(["nope"])
    with pytest.raises(variants.VariantConfigError, match="both replace the relic deck"):
        variants.validate_selection(["absol_relics", "bsp_cards"])
    assert variants.resolve_new_game([], "absol") == (["absol_agendas"], "absol")
    assert variants.resolve_new_game(None) == (variants.default_module_ids(), "standard")


def test_old_games_map_agenda_variant_to_module() -> None:
    assert variants.game_module_ids([], "absol") == ("absol_agendas",)
    assert variants.game_module_ids(["gone", "absol_relics"]) == ("absol_relics",)


def test_new_game_uses_variant_registry(registry: StaticDataRegistry, bound: None) -> None:
    from fastapi.testclient import TestClient

    from src.api.app import create_app

    app = create_app(registry=registry)
    client = TestClient(app)
    players = [{"faction_id": "sol"}, {"faction_id": "hacan"}, {"faction_id": "xxcha"}]
    bad = client.post("/game/new", json={"players": players, "variants": ["nope"]})
    assert bad.status_code == 422
    created = client.post(
        "/game/new", json={"players": players, "variants": ["bsp_factions", "absol_agendas"]}
    )
    assert created.status_code == 200
    ctx = app.state.ctx
    state = ctx.service.current_state()
    assert state.decks.variants == ["bsp_factions", "absol_agendas"]
    assert ctx.registry.variant_ids == ("bsp_factions", "absol_agendas")
    assert "home system" in ctx.registry.technologies["st"].text
    pool = client.get("/api/public/game/test/web-data").json()["cardPool"]
    assert pool["variants"] == ["bsp_factions", "absol_agendas"]
    data = client.get("/api/public/game/test/variant-data").json()
    assert data["entries"]["technologies"]["st"]["variantSource"] == "black_spectrum"
