"""Testy API Katalogu_Komponentów (FastAPI TestClient).

Weryfikują router ``src/api/routers/components.py`` na REALNYM rejestrze
(``StaticDataRegistry`` z domyślnym manifestem aktywnych źródeł). Router jest
cienki i TYLKO-DO-ODCZYTU, więc testy budują klienta z osobnym magazynem w
pamięci (``EventStore(":memory:")``) i sprawdzają kontrakt HTTP, nie logikę gry.

Zakres (zad. 10.2):

* ``GET /components`` — lista kategorii z licznikami (R11.1),
* ``GET /components/{category}`` — słownik komponentów kategorii,
* ``GET /components/{category}/{id}`` — szczegół (R11.1),
* ``GET /components/factions/{faction_id}/bundle`` — paczka frakcji (R5.6),
* ``GET /timing-specs`` — zapytanie czasowe (R11.1),
* 404 dla nieznanej kategorii / id / frakcji (R11.3),
* 422 dla nieprawidłowego ``trigger`` (walidacja enum przez FastAPI),
* wszystkie zwrócone ``source`` należą do aktywnych (R11.2).

Wymagania: 11.1, 11.2, 11.3, 11.4.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.components import CATEGORY_SPECS, ComponentCategory
from src.core.event_store import EventStore
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    """Rejestr ładowany raz na moduł (odczyt assetów jest kosztowny)."""
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    """Klient testowy z osobnym magazynem w pamięci na każdy test."""
    app = create_app(registry=registry, store=EventStore(":memory:"))
    return TestClient(app)


def _nonempty_category(registry: StaticDataRegistry) -> ComponentCategory:
    """Zwraca dowolną niepustą kategorię katalogu (do testów szczegółu/listy)."""
    for category in CATEGORY_SPECS:
        if registry.catalog.all(category):
            return category
    raise AssertionError("Katalog nie ma żadnej niepustej kategorii")


# --- GET /components (lista kategorii) -----------------------------------


def test_get_categories_lists_counts(client: TestClient) -> None:
    """Lista kategorii zwraca liczniki zgodne z ``catalog.counts`` (R11.1)."""
    resp = client.get("/components")
    assert resp.status_code == 200
    body = resp.json()
    assert "categories" in body
    assert len(body["categories"]) > 0
    # Każdy wiersz: total równy sumie by_source, kategoria w enumie.
    valid = {c.value for c in ComponentCategory}
    for row in body["categories"]:
        assert row["category"] in valid
        assert row["total"] == sum(row["by_source"].values())
    # Kategorie są posortowane po nazwie (kontrakt ``from_counts``).
    names = [row["category"] for row in body["categories"]]
    assert names == sorted(names)


# --- GET /components/{category} (słownik kategorii) ----------------------


def test_get_category_components(
    client: TestClient, registry: StaticDataRegistry
) -> None:
    """Słownik ``id -> komponent`` kategorii; count zgodny z liczbą wpisów."""
    category = _nonempty_category(registry)
    resp = client.get(f"/components/{category.value}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == category.value
    assert body["count"] == len(body["components"])
    assert body["count"] > 0


def test_get_category_unknown_returns_404(client: TestClient) -> None:
    """Nieznana kategoria → 404 z komunikatem ``<kategoria>/`` (R11.3)."""
    resp = client.get("/components/not_a_category")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Component not found: not_a_category/"


# --- GET /components/{category}/{id} (szczegół) --------------------------


def test_get_component_detail(
    client: TestClient, registry: StaticDataRegistry
) -> None:
    """Szczegół komponentu niesie dane, status efektu i tematy reguł (R11.1)."""
    category = _nonempty_category(registry)
    component_id = next(iter(registry.catalog.all(category)))
    resp = client.get(f"/components/{category.value}/{component_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == category.value
    assert body["id"] == component_id
    assert isinstance(body["component"], dict)
    # Pola kontraktu zawsze obecne (timing_spec może być None).
    assert "timing_spec" in body
    assert isinstance(body["effect_status"], str)
    assert isinstance(body["rules_topics"], list)


def test_get_component_all_sources_are_enabled(
    client: TestClient, registry: StaticDataRegistry
) -> None:
    """Komponent zwrócony przez API ma źródło z aktywnego manifestu (R11.2)."""
    enabled = set(registry.report().enabled_sources)
    category = _nonempty_category(registry)
    component_id = next(iter(registry.catalog.all(category)))
    body = client.get(f"/components/{category.value}/{component_id}").json()
    assert body["component"]["source"] in enabled


def test_get_component_unknown_id_returns_404(
    client: TestClient, registry: StaticDataRegistry
) -> None:
    """Nieznany identyfikator w znanej kategorii → 404 z kategorią i id (R11.3)."""
    category = _nonempty_category(registry)
    resp = client.get(f"/components/{category.value}/__brak__")
    assert resp.status_code == 404
    assert (
        resp.json()["detail"]
        == f"Component not found: {category.value}/__brak__"
    )


# --- GET /components/factions/{faction_id}/bundle ------------------------


def test_get_faction_bundle(client: TestClient) -> None:
    """Paczka frakcji zawiera frakcję i listy komponentów (R5.6)."""
    # Frakcje nie są tabelą katalogu (kategoria adresowa) — bierzemy realny
    # identyfikator z endpointu ``/factions`` zamiast z ``catalog.all``.
    factions = client.get("/factions").json()
    assert factions, "Brak frakcji w rejestrze — nie można zbudować paczki"
    faction_id = factions[0]["id"]
    resp = client.get(f"/components/factions/{faction_id}/bundle")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["faction"], dict)
    for key in ("leaders", "abilities", "faction_tech", "promissory_notes", "units"):
        assert isinstance(body[key], list)
    assert "breakthrough" in body


def test_get_faction_bundle_unknown_returns_404(client: TestClient) -> None:
    """Nieznana frakcja → 404 z kategorią ``factions`` i identyfikatorem (R11.3)."""
    resp = client.get("/components/factions/__brak__/bundle")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Component not found: factions/__brak__"


# --- GET /timing-specs ---------------------------------------------------


def test_get_timing_specs_valid_trigger(client: TestClient) -> None:
    """Zapytanie czasowe z prawidłowym wyzwalaczem zwraca listę adresów (R11.1)."""
    resp = client.get("/timing-specs", params={"trigger": "when"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["trigger"] == "when"
    assert body["phase"] is None
    assert isinstance(body["refs"], list)
    # Adresy mają kategorię z enumu i identyfikator.
    valid = {c.value for c in ComponentCategory}
    for ref in body["refs"]:
        assert ref["category"] in valid
        assert isinstance(ref["id"], str)


def test_get_timing_specs_with_phase(client: TestClient) -> None:
    """Zapytanie z fazą propaguje ją do odpowiedzi."""
    resp = client.get(
        "/timing-specs", params={"trigger": "action", "phase": "ACTION"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trigger"] == "action"
    assert body["phase"] == "ACTION"


def test_get_timing_specs_invalid_trigger_returns_422(client: TestClient) -> None:
    """Nieprawidłowy ``trigger`` → 422 (walidacja enum przez FastAPI)."""
    resp = client.get("/timing-specs", params={"trigger": "nope"})
    assert resp.status_code == 422


def test_get_timing_specs_missing_trigger_returns_422(client: TestClient) -> None:
    """Brak wymaganego parametru ``trigger`` → 422."""
    resp = client.get("/timing-specs")
    assert resp.status_code == 422
