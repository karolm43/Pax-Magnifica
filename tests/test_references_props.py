"""Testy właściwościowe spójności referencji (``core/references.py``).

Property 6 sprawdza, że ``find_unresolved_references`` / ``build_reference_report``
klasyfikują każdą referencję DOKŁADNIE: istniejący cel → brak zgłoszenia, cel
tylko wśród wpisów niekanonicznych → ``leaks_noncanonical=True``, cel nieznany →
zwykła nierozwiązana referencja, a szablon ``<color>`` → osobna lista ``templates``
(NIGDY nie jako nierozwiązana).

Testy nie dotykają dysku ani pełnego ``StaticDataRegistry`` — budują lekki
„mini-rejestr” (obiekt spełniający protokół ``RegistryLike``) z ręcznie złożonym
``ComponentCatalog`` i prostym ``LoadReport``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.components import (
    AttachmentDef,
    ComponentBase,
    ComponentCatalog,
    ComponentCategory,
    DeckDef,
    ExplorationDef,
    PromissoryNoteDef,
    TokenDef,
)
from src.core.models import FactionDef
from src.core.references import (
    COLOR_PLACEHOLDER,
    build_reference_report,
    find_unresolved_references,
)

# ---------------------------------------------------------------------------
# Mini-rejestr: minimalny obiekt spełniający protokół RegistryLike z references.py
# ---------------------------------------------------------------------------


@dataclass
class _MiniLoadReport:
    """Namiastka ``LoadReport``: tylko indeks pominiętych (niekanonicznych) wpisów."""

    skipped_index: dict[ComponentCategory, dict[str, str]] = field(default_factory=dict)


@dataclass
class _MiniRegistry:
    """Lekki rejestr do testów referencji (bez I/O, bez StaticDataRegistry)."""

    factions: Mapping[str, FactionDef]
    catalog: ComponentCatalog
    technologies: Mapping[str, object] = field(default_factory=dict)
    leaders: Mapping[str, object] = field(default_factory=dict)
    abilities: Mapping[str, object] = field(default_factory=dict)
    units: Mapping[str, object] = field(default_factory=dict)
    load_report: _MiniLoadReport = field(default_factory=_MiniLoadReport)

    def missing_planet_references(self) -> dict[str, list[str]]:
        """Brak sprawdzania planet w tych testach (R7.4 testowane osobno)."""
        return {}


def _promissory(note_id: str) -> PromissoryNoteDef:
    return PromissoryNoteDef(id=note_id, source="base", name=note_id)


def _attachment(att_id: str) -> AttachmentDef:
    return AttachmentDef(id=att_id, source="base", name=att_id)


def _make_catalog(
    promissory_ids: set[str],
    attachment_ids: set[str],
    deck: DeckDef | None = None,
    explores: Mapping[str, ExplorationDef] | None = None,
    tokens: Mapping[str, TokenDef] | None = None,
) -> ComponentCatalog:
    """Składa katalog z wybranych kategorii potrzebnych w teście."""
    tables: dict[ComponentCategory, Mapping[str, ComponentBase]] = {
        ComponentCategory.PROMISSORY_NOTE: {p: _promissory(p) for p in promissory_ids},
        ComponentCategory.ATTACHMENT: {a: _attachment(a) for a in attachment_ids},
    }
    if deck is not None:
        tables[ComponentCategory.DECK] = {deck.id: deck}
    if explores is not None:
        tables[ComponentCategory.EXPLORATION] = dict(explores)
    if tokens is not None:
        tables[ComponentCategory.TOKEN] = dict(tokens)
    return ComponentCatalog(tables)


# ---------------------------------------------------------------------------
# Generatory
# ---------------------------------------------------------------------------

# Identyfikatory zwykłe (bez placeholdera koloru) — mała pula wymusza kolizje.
_plain_ids = st.sampled_from(["p1", "p2", "p3", "p4", "p5", "p6"])
# Identyfikatory szablonowe zawierające ``<color>``.
_template_ids = st.sampled_from(
    [f"{COLOR_PLACEHOLDER}_alliance", f"ceasefire_{COLOR_PLACEHOLDER}", COLOR_PLACEHOLDER]
)


# Feature: local-ti4-data-foundation, Property 6: Spójność referencji jest wykrywana dokładnie
@settings(max_examples=200)
@given(
    existing=st.sets(_plain_ids),
    skipped=st.sets(_plain_ids),
    referenced=st.lists(_plain_ids, max_size=12),
    templates=st.lists(_template_ids, max_size=4),
)
def test_referencje_promissory_frakcji_klasyfikowane_dokladnie(
    existing: set[str],
    skipped: set[str],
    referenced: list[str],
    templates: list[str],
) -> None:
    """Promissory notes frakcji: istniejące OK, szablony osobno, brak → nierozwiązane.

    Cel istniejący w katalogu → brak zgłoszenia. Cel wyłącznie wśród wpisów
    niekanonicznych (``skipped_index``) → ``leaks_noncanonical=True``. Cel nieznany
    nigdzie → ``leaks_noncanonical=False``. Każdy ``<color>`` → tylko ``templates``.

    **Validates: Requirements 7.1, 7.6**
    """
    # Wpisy niekanoniczne liczą się jako „przeciek” tylko, gdy NIE istnieją kanonicznie.
    skipped_only = skipped - existing
    catalog = _make_catalog(promissory_ids=existing, attachment_ids=set())
    faction = FactionDef(
        alias="arborec",
        factionName="Arborec",
        source="base",
        promissoryNotes=referenced + templates,
    )
    report_source = _MiniLoadReport(
        skipped_index={
            ComponentCategory.PROMISSORY_NOTE: {sid: "ds" for sid in skipped_only}
        }
    )
    registry = _MiniRegistry(
        factions={"arborec": faction},
        catalog=catalog,
        load_report=report_source,
    )

    report = build_reference_report(registry)

    # Szablony nigdy nie są nierozwiązane — trafiają wyłącznie do ``templates``.
    assert {t.template_id for t in report.templates} == set(templates)
    assert all(COLOR_PLACEHOLDER not in ref.missing_id for ref in report.unresolved)

    # Oczekiwane nierozwiązane = referencje spoza katalogu (bez szablonów).
    expected_missing = {r for r in referenced if r not in existing}
    actual_missing = {ref.missing_id for ref in report.unresolved}
    assert actual_missing == expected_missing

    # Flaga przecieku ustawiona dokładnie dla celów obecnych tylko niekanonicznie.
    for ref in report.unresolved:
        assert ref.kind == "faction.promissoryNotes"
        assert ref.owner_id == "arborec"
        assert ref.leaks_noncanonical == (ref.missing_id in skipped_only)


# Feature: local-ti4-data-foundation, Property 6: Spójność referencji jest wykrywana dokładnie
@settings(max_examples=200)
@given(
    existing=st.sets(_plain_ids),
    card_ids=st.lists(_plain_ids, max_size=10),
    templates=st.lists(_template_ids, max_size=3),
)
def test_referencje_cardids_talii_promissory_klasyfikowane_dokladnie(
    existing: set[str], card_ids: list[str], templates: list[str]
) -> None:
    """``cardIDs`` talii promissory: brakujące → nierozwiązane, ``<color>`` → szablon.

    Talia typu ``promissory_note`` kieruje do kategorii PROMISSORY_NOTE, więc każdy
    ``cardID`` sprawdzany jest względem istniejących promissory notes.

    **Validates: Requirements 7.2**
    """
    catalog = _make_catalog(
        promissory_ids=existing,
        attachment_ids=set(),
        deck=DeckDef(
            id="pn_deck",
            source="base",
            type="promissory_note",
            cardIDs=card_ids + templates,
        ),
    )
    registry = _MiniRegistry(factions={}, catalog=catalog)

    report = build_reference_report(registry)

    assert {t.template_id for t in report.templates} == set(templates)
    expected_missing = {c for c in card_ids if c not in existing}
    actual_missing = {ref.missing_id for ref in report.unresolved}
    assert actual_missing == expected_missing
    assert all(ref.kind == "deck.cardIDs" for ref in report.unresolved)


# Feature: local-ti4-data-foundation, Property 6: Spójność referencji jest wykrywana dokładnie
@settings(max_examples=200)
@given(
    existing_attachments=st.sets(_plain_ids),
    explore_att=st.lists(st.tuples(_plain_ids, _plain_ids), max_size=6, unique_by=lambda t: t[0]),
    token_att=st.lists(st.tuples(_plain_ids, _plain_ids), max_size=6, unique_by=lambda t: t[0]),
)
def test_referencje_attachment_eksploracji_i_zetonow(
    existing_attachments: set[str],
    explore_att: list[tuple[str, str]],
    token_att: list[tuple[str, str]],
) -> None:
    """``attachmentId`` eksploracji i ``attachmentID`` żetonów wskazują attachment.

    Brakujący attachment → nierozwiązana referencja o właściwym ``kind`` i właścicielu;
    istniejący → brak zgłoszenia.

    **Validates: Requirements 7.3**
    """
    explores = {
        ex_id: ExplorationDef(id=ex_id, source="base", attachmentId=att)
        for ex_id, att in explore_att
    }
    tokens = {
        tok_id: TokenDef(id=tok_id, source="base", attachmentID=att)
        for tok_id, att in token_att
    }
    catalog = _make_catalog(
        promissory_ids=set(),
        attachment_ids=existing_attachments,
        explores=explores,
        tokens=tokens,
    )
    registry = _MiniRegistry(factions={}, catalog=catalog)

    report = build_reference_report(registry)

    unresolved = {(ref.kind, ref.owner_id, ref.missing_id) for ref in report.unresolved}

    expected: set[tuple[str, str, str]] = set()
    for ex_id, att in explore_att:
        if att not in existing_attachments:
            expected.add(("exploration.attachmentId", ex_id, att))
    for tok_id, att in token_att:
        if att not in existing_attachments:
            expected.add(("token.attachmentID", tok_id, att))

    assert unresolved == expected


# Feature: local-ti4-data-foundation, Property 6: Spójność referencji jest wykrywana dokładnie
@settings(max_examples=100)
@given(referenced=st.lists(_plain_ids, min_size=1, max_size=8))
def test_find_unresolved_pomija_szablony_i_zwraca_tylko_nierozwiazane(
    referenced: list[str],
) -> None:
    """``find_unresolved_references`` nie zawiera szablonów i równa się ``report.unresolved``.

    Każdy identyfikator jest tu brakujący (katalog pusty), więc wszystkie zwykłe
    referencje są nierozwiązane, a szablony ``<color>`` nie pojawiają się nigdy.

    **Validates: Requirements 7.5, 7.6**
    """
    template = f"{COLOR_PLACEHOLDER}_x"
    catalog = _make_catalog(promissory_ids=set(), attachment_ids=set())
    faction = FactionDef(
        alias="f",
        factionName="F",
        source="base",
        promissoryNotes=referenced + [template],
    )
    registry = _MiniRegistry(factions={"f": faction}, catalog=catalog)

    unresolved = find_unresolved_references(registry)
    full = build_reference_report(registry)

    assert unresolved == full.unresolved
    assert all(COLOR_PLACEHOLDER not in ref.missing_id for ref in unresolved)
    assert {ref.missing_id for ref in unresolved} == set(referenced)
