"""Czyste modele i stałe treści reguł TI4 dla przeglądarki Zasad (Rules_Browser).

Warstwa ``core`` zgodna ze złotą zasadą architektury (ARCHITEKTURA_KODU.md §1):
całe parsowanie, grupowanie i mapowanie linków zrzutu ``docs/rules_tirules/`` to
CZYSTE funkcje bez importów FastAPI/HTTP. Ten moduł definiuje wyłącznie modele
danych (frozen dataclassy) i stałe modułu — czyste funkcje
(``load_index``/``load_topic``/``parse_title``/``map_link`` itd.) dochodzą w
kolejnych zadaniach planu (2.1, 2.3, 3.1, 4.1).

Modele są niemutowalne (``frozen=True``), bo treść reguł jest tylko do odczytu i
nie dotyka ``GameState`` — router API wyłącznie ją serwuje, nie commituje stanu.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# --- Stałe modułu -------------------------------------------------------

#: Prefiksy plików tematów w kolejności grup: Reguły, Frakcje, Komponenty.
#: ``R_`` → reguły, ``F_`` → noty frakcji, ``C_`` → noty komponentów (Req 2.2).
RULE_PREFIXES: tuple[str, ...] = ("R_", "F_", "C_")

#: Dopasowanie URL tirules2.com (z opcjonalnym ``www.`` i trailing slash) do slug
#: tematu. Grupa 1 to Topic_Slug, np. ``R_movement`` (Req 4.1). Klasa znaków slug
#: ograniczona do ``[A-Za-z0-9_]`` — bez separatorów ścieżki, więc odwzorowanie
#: nie wpuszcza prób path-traversal.
TIRULES_URL_RE: re.Pattern[str] = re.compile(
    r"^https?://(?:www\.)?tirules2\.com/([A-Za-z0-9_]+)/?$"
)

#: Marker pozycji noty będącej rulingiem Dane Beltramiego w zrzucie (Req 7.4).
DANE_MARKER: str = "_[Dane ruling]_"


# --- Modele danych (frozen dataclassy, bez zależności HTTP) -------------


@dataclass(frozen=True)
class TopicIndexEntry:
    """Pojedyncza pozycja indeksu tematów (Topic_Index).

    Attributes:
        slug: Topic_Slug — nazwa pliku bez ``.md`` (np. ``R_movement``).
        title: Tytuł z pierwszego nagłówka ``# `` albo slug jako fallback
            (Req 2.4/2.5).
        group: Klucz grupy: ``"rules"`` | ``"factions"`` | ``"components"``.
    """

    slug: str
    title: str
    group: str


@dataclass(frozen=True)
class TopicGroup:
    """Grupa tematów w indeksie (Reguły / Frakcje / Komponenty).

    Attributes:
        group: Klucz grupy (``"rules"`` | ``"factions"`` | ``"components"``).
        label: Etykieta po polsku: ``"Reguły"`` | ``"Frakcje"`` | ``"Komponenty"``.
        entries: Krotka pozycji należących do grupy (niemutowalna).
    """

    group: str
    label: str
    entries: tuple[TopicIndexEntry, ...]


@dataclass(frozen=True)
class TopicContent:
    """Treść pojedynczego tematu gotowa do renderowania na froncie.

    Attributes:
        slug: Topic_Slug (nazwa pliku bez ``.md``).
        title: Tytuł z pierwszego nagłówka ``# `` albo slug jako fallback.
        group: Klucz grupy (``"rules"`` | ``"factions"`` | ``"components"``).
        markdown: Surowa treść pliku ``.md`` do renderowania po stronie klienta.
        is_empty_note: ``True`` dla tematu F/C bez not poza nagłówkiem i blockquote
            źródła (Req 7.3); zawsze ``False`` dla grupy Reguły.
    """

    slug: str
    title: str
    group: str
    markdown: str
    is_empty_note: bool


@dataclass(frozen=True)
class LinkTarget:
    """Wynik Link_Mapper — cel hiperłącza z treści tematu.

    Rozróżnia odnośnik wewnętrzny (Internal_Link, nawigacja po lokalnych tematach)
    od zewnętrznego (External_Link, adres spoza lokalnego zrzutu). Dokładnie jedno
    z pól (``slug`` dla internal, ``url`` dla external) jest ustawione zależnie od
    ``kind`` — konstruuj przez fabryki ``internal`` / ``external``.

    Attributes:
        kind: ``"internal"`` albo ``"external"``.
        slug: Topic_Slug dla odnośnika wewnętrznego (``None`` dla zewnętrznego).
        url: Oryginalny URL dla odnośnika zewnętrznego (``None`` dla wewnętrznego).
    """

    kind: Literal["internal", "external"]
    slug: str | None = None
    url: str | None = None

    @classmethod
    def internal(cls, slug: str) -> LinkTarget:
        """Tworzy Internal_Link wskazujący lokalny temat o danym slug."""
        return cls(kind="internal", slug=slug, url=None)

    @classmethod
    def external(cls, url: str) -> LinkTarget:
        """Tworzy External_Link zachowujący oryginalny URL."""
        return cls(kind="external", slug=None, url=url)
