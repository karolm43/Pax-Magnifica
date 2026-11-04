"""Testy przykładowe paczki frakcji i spójności referencji na REALNYCH danych.

Weryfikują dwie rzeczy na pełnym ``StaticDataRegistry`` (domyślny manifest:
base, pok, codex1-4, Thunder's Edge):

* ``ComponentCatalog.faction_bundle`` dla prawdziwych frakcji zwraca komplet
  rozwiązanych komponentów (liderzy, zdolności, technologie frakcyjne, promissory
  notes, jednostki, przełom), a każdy identyfikator z paczki istnieje w katalogu
  lub w słownikach rejestru;
* ``find_unresolved_references`` na pełnym rejestrze zwraca LISTĘ, a jej zawartość
  ogranicza się do UDOKUMENTOWANYCH, znanych luk homebrew (talia ``explores_cpti``
  oraz referencje attachmentów ``mirage``/``gamma``/``ion``). Są to referencje do
  treści spoza aktywnych źródeł kanonicznych — oczekiwane, więc test ich NIE traktuje
  jako błędu, tylko asertuje STRUKTURĘ wyniku (zgodnie z zadaniem 4.4).

Wymagania: 5.6, 7.1, 7.4.
"""

from __future__ import annotations

import pytest

from src.core.components import ComponentCategory
from src.core.references import UnresolvedReference
from src.core.registry import StaticDataRegistry

# Reprezentatywne frakcje z każdego aktywnego źródła (base, pok, codex3, TE).
# Identyfikatory są kluczami w słowniku frakcji rejestru.
REAL_FACTIONS: tuple[str, ...] = (
    "arborec",  # base
    "sol",  # base
    "titans",  # pok
    "keleresm",  # codex3 (Keleres — Mentak flavor)
    "bastion",  # thunders_edge
)

# Znane, oczekiwane luki referencyjne pochodzące z treści homebrew (spoza aktywnych
# źródeł kanonicznych). NIE są traktowane jako błąd — asertujemy tylko, że żadna
# nierozwiązana referencja nie wychodzi poza ten zbiór właścicieli.
#
# * ``explores_cpti`` — homebrew talia eksploracji (``cpti``) wskazująca karty spoza
#   aktywnych źródeł; wszystkie wpisy są „przeciekami" niekanonicznymi (R7.6).
# * ``mirage``/``gamma``/``gw``/``ion`` — karty eksploracji wskazujące attachmenty
#   (``mirage``, ``gamma``, ``ionalpha``), których nie ma wśród aktywnych wpisów.
KNOWN_UNRESOLVED_OWNERS: frozenset[str] = frozenset(
    {"explores_cpti", "mirage", "gamma", "gw", "ion"}
)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    """Rejestr z domyślnym manifestem aktywnych źródeł (base, pok, codex1-4, TE)."""
    return StaticDataRegistry()


@pytest.mark.parametrize("faction_id", REAL_FACTIONS)
def test_faction_bundle_ma_lidera_i_przelom(
    registry: StaticDataRegistry, faction_id: str
) -> None:
    """Paczka realnej frakcji zawiera właściwych liderów i przełom (R5.6).

    Każda z aktywnych frakcji ma trzech liderów (agent/commander/hero) oraz
    przełom (breakthrough — Thunder's Edge dowiązuje go po polu ``faction``).
    Sprawdzamy, że ``faction_bundle`` rozwiązuje je z realnych list ``FactionDef``.

    _Requirements: 5.6_
    """
    bundle = registry.catalog.faction_bundle(faction_id)

    assert bundle.faction is registry.factions[faction_id]
    # Realne frakcje mają zawsze co najmniej jednego lidera i przełom.
    assert bundle.leaders, f"Frakcja {faction_id} nie ma rozwiązanych liderów"
    assert bundle.breakthrough is not None, f"Frakcja {faction_id} nie ma przełomu"


@pytest.mark.parametrize("faction_id", REAL_FACTIONS)
def test_faction_bundle_identyfikatory_istnieja(
    registry: StaticDataRegistry, faction_id: str
) -> None:
    """Każdy identyfikator rozwiązany w paczce istnieje w słowniku źródłowym (R5.6).

    Modele w paczce muszą być TYMI SAMYMI obiektami, co w słownikach rejestru /
    katalogu — czyli identyfikatory z paczki istnieją i mapują się 1:1.

    _Requirements: 5.6_
    """
    bundle = registry.catalog.faction_bundle(faction_id)

    for leader in bundle.leaders:
        assert registry.leaders[leader.id] is leader
    for ability in bundle.abilities:
        assert registry.abilities[ability.id] is ability
    for tech in bundle.faction_tech:
        assert registry.technologies[tech.id] is tech
    for unit in bundle.units:
        assert registry.units[unit.id] is unit
    promissory = registry.catalog.all(ComponentCategory.PROMISSORY_NOTE)
    for note in bundle.promissory_notes:
        assert promissory[note.id] is note


def test_faction_bundle_nieznana_frakcja_podnosi_keyerror(
    registry: StaticDataRegistry,
) -> None:
    """Paczka dla nieistniejącej frakcji podnosi ``KeyError`` (kontrakt metody)."""
    with pytest.raises(KeyError):
        registry.catalog.faction_bundle("nie_ma_takiej_frakcji")


def test_unresolved_references_jest_lista(registry: StaticDataRegistry) -> None:
    """``find_unresolved_references`` zwraca listę obiektów ``UnresolvedReference``.

    Nierozwiązane referencje NIE blokują startu rejestru (dane są lokalne); to
    Audytor_Danych zgłasza je i ustawia niezerowy kod wyjścia. Tu asertujemy wyłącznie
    strukturę wyniku.

    _Requirements: 7.1_
    """
    unresolved = registry.unresolved_references()

    assert isinstance(unresolved, list)
    assert all(isinstance(ref, UnresolvedReference) for ref in unresolved)


def test_unresolved_references_tylko_znane_luki_homebrew(
    registry: StaticDataRegistry,
) -> None:
    """Wszystkie nierozwiązane referencje należą do znanych, oczekiwanych luk.

    Na realnych danych jedyne nierozwiązane referencje pochodzą z treści homebrew
    (talia ``explores_cpti`` i attachmenty ``mirage``/``gamma``/``ion``). Są to
    oczekiwane referencje spoza aktywnych źródeł kanonicznych — test dokumentuje je
    jako znane i upewnia się, że nie pojawia się ŻADNA nowa, nieoczekiwana luka
    (np. zerwana referencja w kanonicznych danych).

    _Requirements: 7.1, 7.4_
    """
    unresolved = registry.unresolved_references()

    unexpected = [
        ref for ref in unresolved if ref.owner_id not in KNOWN_UNRESOLVED_OWNERS
    ]
    assert unexpected == [], (
        "Nieoczekiwane nierozwiązane referencje (poza znanymi lukami homebrew): "
        f"{[(r.kind, r.owner_id, r.missing_id) for r in unexpected]}"
    )


def test_unresolved_references_brak_zerwanych_referencji_frakcji(
    registry: StaticDataRegistry,
) -> None:
    """Żadna frakcja ani referencja systemu do planety nie jest zerwana (R7.1, R7.4).

    Znane luki dotyczą wyłącznie talii i attachmentów homebrew; referencje frakcji
    (``faction.*``) oraz systemów do planet (``system.planets``) muszą być spójne.

    _Requirements: 7.1, 7.4_
    """
    unresolved = registry.unresolved_references()

    faction_or_planet = [
        ref
        for ref in unresolved
        if ref.kind.startswith("faction.") or ref.kind == "system.planets"
    ]
    assert faction_or_planet == [], (
        "Zerwane referencje frakcji lub systemów do planet: "
        f"{[(r.kind, r.owner_id, r.missing_id) for r in faction_or_planet]}"
    )
