"""Moduły wariantów gry (``assets/config/variants.json``, ``core/variants.py``).

Fanowskie talie (Absol: agendy, relikty), erraty pojedynczych kart (``homebrewReplacesID``)
i własne komponenty - wybierane per gra w ``/game/new`` (``variants``).
"""

from __future__ import annotations

import pytest

from src.core import relics, variants
from src.core.components import ComponentCategory
from src.core.exploration import deck_card_ids as explore_ids
from src.core.game_state import GameState
from src.core.objectives import deck_card_ids
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


# --- Manifest ---------------------------------------------------------------------------------


def test_manifest_parses_and_lists_absol_modules() -> None:
    mods = variants.modules()
    assert {"absol_agendas", "absol_relics"} <= set(mods)
    assert mods["absol_relics"].decks == {"relic": "relics_absol"}
    assert mods["absol_agendas"].replaces == frozenset({"promissory_note"})


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"modules": [{"id": "x", "name": "X"}]}, "non-empty id, name and source"),
        ({"modules": [{"id": "x", "name": "X", "source": "s", "decks": {"tech": "t"}}]},
         "unknown deck types"),
        ({"modules": [{"id": "x", "name": "X", "source": "s",
                       "decks": {"promissory_note": "p"}}]}, "only be replaced"),
        ({"modules": [{"id": "x", "name": "X", "source": "s"},
                      {"id": "x", "name": "Y", "source": "s"}]}, "Duplicate"),
    ],
)
def test_manifest_validation(raw: object, message: str) -> None:
    with pytest.raises(variants.VariantConfigError, match=message):
        variants.parse_modules(raw)


def test_load_plan_admits_only_what_modules_need() -> None:
    plan = variants.load_plan(variants.parse_modules({"modules": [
        {"id": "a", "name": "A", "source": "fan", "decks": {"relic": "relics_fan"},
         "replaces": ["action_card"]},
    ]}).values())
    relic = {"source": "fan", "alias": "r"}
    assert plan.admits(ComponentCategory.RELIC, relic)
    assert not plan.admits(ComponentCategory.ACTION_CARD, {"source": "fan", "alias": "c"})
    assert plan.admits(
        ComponentCategory.ACTION_CARD, {"source": "fan", "homebrewReplacesID": "sabotage"}
    )
    assert plan.admits(ComponentCategory.DECK, {"source": "fan", "type": "relic"})
    assert not plan.admits(ComponentCategory.DECK, {"source": "fan", "type": "agenda"})
    assert not plan.admits(ComponentCategory.AGENDA, {"source": "fan"})


# --- Wybór modułów ------------------------------------------------------------------------------


def test_selection_rejects_unknown_and_conflicting_decks() -> None:
    assert variants.validate_selection(["absol_relics", "absol_relics"]) == ["absol_relics"]
    with pytest.raises(variants.VariantConfigError, match="Unknown game variant"):
        variants.validate_selection(["nope"])


def test_resolve_new_game_maps_legacy_agenda_deck(registry: StaticDataRegistry) -> None:
    assert variants.resolve_new_game(registry, None) == (variants.default_module_ids(), "standard")
    assert variants.resolve_new_game(registry, [], "absol") == (["absol_agendas"], "absol")
    assert variants.resolve_new_game(registry, ["absol_relics"]) == (["absol_relics"], "standard")
    with pytest.raises(variants.VariantConfigError):
        variants.resolve_new_game(registry, [], "nope")


def test_game_modules_keep_old_games_working() -> None:
    """Gra sprzed modułów ma tylko ``agenda_variant`` - moduł agend Absol i tak działa."""
    assert [m.id for m in variants.game_modules([], "absol")] == ["absol_agendas"]
    assert [m.id for m in variants.game_modules(["gone", "absol_relics"])] == ["absol_relics"]


# --- Skład talii ----------------------------------------------------------------------------------


def test_relic_module_replaces_whole_relic_deck(registry: StaticDataRegistry) -> None:
    official = deck_card_ids(registry, "relic")
    state = GameState()
    assert deck_card_ids(registry, "relic", state) == official
    assert not [r for r in official if r.startswith("absol_")]
    state.decks.variants = ["absol_relics"]
    absol = deck_card_ids(registry, "relic", state)
    assert len(absol) == 20 and all(r.startswith("absol_") for r in absol)
    for relic_id in absol:
        assert registry.catalog.get(ComponentCategory.RELIC, relic_id) is not None
    relics.ensure_relic_deck(state, registry)
    assert sorted(state.decks.relic_deck) == sorted(absol)


def test_errata_replacements_swap_single_cards(registry: StaticDataRegistry) -> None:
    """Errata: karta z ``homebrewReplacesID`` zastępuje oficjalną (1 karta -> N kopii)."""
    errata = variants.VariantModule(
        id="errata", name="Errata", source="absol", replaces=frozenset({"relic"})
    )
    mapping = variants.replacement_map(registry, "relic", [errata])
    assert mapping["codex"] == ["absol_codex"]
    assert mapping["shard"] == [
        "absol_shardofthethrone1", "absol_shardofthethrone2", "absol_shardofthethrone3"
    ]
    deck = variants.game_deck_ids(registry, "relic", [errata])
    official = variants.official_deck_ids(registry, "relic")
    assert "codex" not in deck and "absol_codex" in deck
    assert len(deck) == len(official) + 2  # shard -> 3 kopie
    # Karty bez odpowiednika w oficjalnej talii (np. Luxarch Treatise) NIE wchodzą przez erratę.
    assert "absol_luxarchtreatise" not in deck


def test_apply_replacements_is_pure() -> None:
    assert variants.apply_replacements(["a", "b"], {"a": ["x", "y"]}) == ["x", "y", "b"]


def test_official_decks_ignore_variant_sources(registry: StaticDataRegistry) -> None:
    state = GameState()
    state.decks.variants = ["absol_relics"]
    for trait in ("cultural", "hazardous", "industrial", "frontier"):
        assert explore_ids(registry, trait, state) == explore_ids(registry, trait)
    for deck_type in ("action_card", "secret_objective", "public_stage_1_objective"):
        assert deck_card_ids(registry, deck_type, state) == deck_card_ids(registry, deck_type)


# --- API ------------------------------------------------------------------------------------------


def test_new_game_stores_variants_and_web_data_exposes_them() -> None:
    from fastapi.testclient import TestClient

    from src.api.app import create_app

    app = create_app()
    client = TestClient(app)
    players = [{"faction_id": "sol"}, {"faction_id": "hacan"}, {"faction_id": "xxcha"}]
    bad = client.post("/game/new", json={"players": players, "variants": ["nope"]})
    assert bad.status_code == 422
    created = client.post(
        "/game/new", json={"players": players, "variants": ["absol_relics", "absol_agendas"]}
    )
    assert created.status_code == 200
    state = app.state.ctx.service.current_state()
    assert state.decks.variants == ["absol_relics", "absol_agendas"]
    assert state.decks.agenda_variant == "absol"
    pool = client.get("/api/public/game/test/web-data").json()["cardPool"]
    assert pool["variants"] == ["absol_relics", "absol_agendas"]
    assert pool["agendaVariant"] == "absol"
