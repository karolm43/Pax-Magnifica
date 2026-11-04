"""Spójność referencji między danymi TI4 (R7).

Sprawdza, że identyfikatory wskazywane przez frakcje, talie kanoniczne, karty
eksploracji i żetony wskazują ISTNIEJĄCY komponent w Katalogu_Komponentów (albo
w słownikach rejestru dla kategorii starszych, jak technologie). Zachowuje też
istniejące sprawdzenie referencji systemów do planet (``missing_planet_references``,
R7.4).

Moduł jest CZYSTY: nie czyta plików, operuje wyłącznie na danych już załadowanego
rejestru. Dzięki temu ``find_unresolved_references`` da się testować na „mini-rejestrze”
(dowolnym obiekcie spełniającym :class:`RegistryLike`), bez pełnego
``StaticDataRegistry``.

Placeholder ``<color>`` (promissory notes z pliku ``color.json``) jest SZABLONEM,
nie konkretną kartą — każdy identyfikator zawierający ``<color>`` jest raportowany
osobno (``templates``) i NIE liczony jako nierozwiązana referencja. To zachowanie
jest ⚠️ ZAŁOŻENIEM (patrz docs/RULES.md) do potwierdzenia po pierwszym raporcie.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from src.core.components import ComponentCatalog, ComponentCategory
from src.core.models import FactionDef

# Placeholder koloru w identyfikatorach promissory notes (plik color.json).
COLOR_PLACEHOLDER = "<color>"

# Pola list frakcji sprawdzane pod kątem istnienia celu oraz kategoria docelowa.
# ``None`` jako kategoria oznacza słownik rejestru (starsza kategoria), nie katalog.
_FACTION_LIST_FIELDS: tuple[tuple[str, str, ComponentCategory | None], ...] = (
    # leaders/abilities/technologie/jednostki żyją w słownikach rejestru (None),
    # a nie w Katalogu_Komponentów. Promissory notes są w katalogu.
    ("leaders", "leaders", None),
    ("abilities", "abilities", None),
    ("promissory_notes", "promissoryNotes", ComponentCategory.PROMISSORY_NOTE),
    ("faction_tech", "factionTech", None),
    ("units", "units", None),
    ("starting_tech", "startingTech", None),
    ("starting_tech_options", "startingTechOptions", None),
)

# Typ talii -> kategoria komponentu w katalogu (albo ``None`` = słownik rejestru).
_DECK_TYPE_TO_CATEGORY: Mapping[str, ComponentCategory | None] = {
    "agenda": ComponentCategory.AGENDA,
    "action_card": ComponentCategory.ACTION_CARD,
    "secret_objective": ComponentCategory.SECRET_OBJECTIVE,
    "public_stage_1_objective": ComponentCategory.PUBLIC_OBJECTIVE,
    "public_stage_2_objective": ComponentCategory.PUBLIC_OBJECTIVE,
    "public_objective": ComponentCategory.PUBLIC_OBJECTIVE,
    "relic": ComponentCategory.RELIC,
    "explore": ComponentCategory.EXPLORATION,
    "promissory_note": ComponentCategory.PROMISSORY_NOTE,
    "technology": None,
}


@dataclass(frozen=True)
class UnresolvedReference:
    """Pojedyncza nierozwiązana (lub „przeciekająca”) referencja.

    Attributes:
        kind: Rodzaj powiązania, np. ``"faction.leaders"``, ``"deck.cardIDs"``,
            ``"exploration.attachmentId"``, ``"token.attachmentID"``,
            ``"system.planets"``.
        owner_id: Identyfikator właściciela referencji (frakcji, talii, systemu…).
        missing_id: Brakujący lub niekanoniczny identyfikator celu.
        leaks_noncanonical: ``True``, gdy cel ISTNIEJE, ale pochodzi ze źródła
            niekanonicznego (przeciek treści homebrew, R7.6).
    """

    kind: str
    owner_id: str
    missing_id: str
    leaks_noncanonical: bool = False


@dataclass(frozen=True)
class TemplateReference:
    """Referencja do szablonu z placeholderem ``<color>`` (nie jest błędem)."""

    kind: str
    owner_id: str
    template_id: str


@dataclass
class ReferenceReport:
    """Wynik sprawdzenia spójności referencji."""

    unresolved: list[UnresolvedReference] = field(default_factory=list)
    templates: list[TemplateReference] = field(default_factory=list)


class RegistryLike(Protocol):
    """Minimalny interfejs rejestru wymagany przez sprawdzanie referencji.

    Spełnia go zarówno ``StaticDataRegistry``, jak i lekki „mini-rejestr” w testach.
    Atrybuty są deklarowane jako właściwości tylko-do-odczytu (kowariantne), aby
    ``dict[str, FactionDef]`` rejestru pasował do ``Mapping[str, FactionDef]``.
    """

    @property
    def factions(self) -> Mapping[str, FactionDef]: ...

    @property
    def technologies(self) -> Mapping[str, object]: ...

    @property
    def leaders(self) -> Mapping[str, object]: ...

    @property
    def abilities(self) -> Mapping[str, object]: ...

    @property
    def catalog(self) -> ComponentCatalog: ...

    def missing_planet_references(self) -> dict[str, list[str]]: ...


def _is_template(identifier: str) -> bool:
    """Czy identyfikator jest szablonem koloru (zawiera ``<color>``)."""
    return COLOR_PLACEHOLDER in identifier


def _skipped_index_for(
    registry: RegistryLike, category: ComponentCategory
) -> Mapping[str, str]:
    """Indeks ``id -> źródło`` wpisów pominiętych (niekanonicznych) danej kategorii.

    Pozwala wykryć „przeciek homebrew” (R7.6): cel nie istnieje w katalogu, ale
    figuruje wśród wpisów odrzuconych jako niekanoniczne.
    """
    report = getattr(registry, "load_report", None)
    if report is None:
        return {}
    skipped_index = getattr(report, "skipped_index", None)
    if not isinstance(skipped_index, Mapping):
        return {}
    per_category = skipped_index.get(category)
    return per_category if isinstance(per_category, Mapping) else {}


def _exists(
    registry: RegistryLike, category: ComponentCategory | None, identifier: str
) -> bool:
    """Czy identyfikator istnieje w katalogu (lub słowniku rejestru dla kategorii starszej)."""
    if category is None:
        # Kategorie starsze (technologie, jednostki) żyją w słownikach rejestru.
        for mapping_name in ("technologies", "units", "leaders", "abilities"):
            mapping = getattr(registry, mapping_name, None)
            if isinstance(mapping, Mapping) and identifier in mapping:
                return True
        return False
    return registry.catalog.get(category, identifier) is not None


def _check_identifier(
    registry: RegistryLike,
    kind: str,
    owner_id: str,
    category: ComponentCategory | None,
    identifier: str,
    report: ReferenceReport,
) -> None:
    """Rozstrzyga pojedynczą referencję: szablon, OK, przeciek albo brak."""
    if _is_template(identifier):
        report.templates.append(TemplateReference(kind, owner_id, identifier))
        return
    if _exists(registry, category, identifier):
        return
    leaks = False
    if category is not None:
        leaks = identifier in _skipped_index_for(registry, category)
    report.unresolved.append(
        UnresolvedReference(kind, owner_id, identifier, leaks_noncanonical=leaks)
    )


def _check_factions(registry: RegistryLike, report: ReferenceReport) -> None:
    """Sprawdza wszystkie listy identyfikatorów na frakcjach (R7.1)."""
    for faction_id, faction in registry.factions.items():
        for attr, label, category in _FACTION_LIST_FIELDS:
            for identifier in getattr(faction, attr, []):
                if not isinstance(identifier, str) or not identifier:
                    continue
                _check_identifier(
                    registry,
                    f"faction.{label}",
                    faction_id,
                    category,
                    identifier,
                    report,
                )


def _check_decks(registry: RegistryLike, report: ReferenceReport) -> None:
    """Sprawdza ``cardIDs`` talii ze źródła kanonicznego (R7.2)."""
    decks = registry.catalog.all(ComponentCategory.DECK)
    for deck_id, deck in decks.items():
        deck_type = getattr(deck, "deck_type", None)
        category = (
            _DECK_TYPE_TO_CATEGORY.get(deck_type) if isinstance(deck_type, str) else None
        )
        if deck_type is not None and deck_type not in _DECK_TYPE_TO_CATEGORY:
            # Typ talii spoza znanej mapy — nie zgadujemy kategorii celu.
            continue
        for card_id in getattr(deck, "card_ids", []):
            if not isinstance(card_id, str) or not card_id:
                continue
            _check_identifier(
                registry, "deck.cardIDs", deck_id, category, card_id, report
            )


def _check_attachments(registry: RegistryLike, report: ReferenceReport) -> None:
    """Sprawdza ``attachmentId`` eksploracji i ``attachmentID`` żetonów (R7.3)."""
    explores = registry.catalog.all(ComponentCategory.EXPLORATION)
    for explore_id, explore in explores.items():
        attachment = getattr(explore, "attachment_id", None)
        if isinstance(attachment, str) and attachment:
            _check_identifier(
                registry,
                "exploration.attachmentId",
                explore_id,
                ComponentCategory.ATTACHMENT,
                attachment,
                report,
            )
    tokens = registry.catalog.all(ComponentCategory.TOKEN)
    for token_id, token in tokens.items():
        attachment = getattr(token, "attachment_id", None)
        if isinstance(attachment, str) and attachment:
            _check_identifier(
                registry,
                "token.attachmentID",
                token_id,
                ComponentCategory.ATTACHMENT,
                attachment,
                report,
            )


def _check_planets(registry: RegistryLike, report: ReferenceReport) -> None:
    """Zachowuje istniejące sprawdzenie referencji systemów do planet (R7.4)."""
    for system_id, planets in registry.missing_planet_references().items():
        for planet_id in planets:
            report.unresolved.append(
                UnresolvedReference("system.planets", system_id, planet_id)
            )


def build_reference_report(registry: RegistryLike) -> ReferenceReport:
    """Buduje pełny raport referencji (nierozwiązane + szablony)."""
    report = ReferenceReport()
    _check_factions(registry, report)
    _check_decks(registry, report)
    _check_attachments(registry, report)
    _check_planets(registry, report)
    report.unresolved.sort(key=lambda ref: (ref.kind, ref.owner_id, ref.missing_id))
    report.templates.sort(
        key=lambda ref: (ref.kind, ref.owner_id, ref.template_id)
    )
    return report


def find_unresolved_references(registry: RegistryLike) -> list[UnresolvedReference]:
    """Zwraca listę nierozwiązanych (i przeciekających) referencji (R7.1-7.6).

    Szablony ``<color>`` NIE są tu uwzględniane — pełny raport (w tym szablony)
    daje :func:`build_reference_report`.
    """
    return build_reference_report(registry).unresolved
