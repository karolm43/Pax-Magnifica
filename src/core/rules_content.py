"""Czyste modele i stałe treści reguł TI4 dla przeglądarki Zasad (Rules_Browser).

Warstwa ``core`` zgodna ze złotą zasadą architektury (ARCHITEKTURA_KODU.md §1):
całe parsowanie, grupowanie i mapowanie linków zrzutu ``docs/rules_tirules/`` to
CZYSTE funkcje bez importów FastAPI/HTTP. Ten moduł definiuje modele danych
(frozen dataclassy), stałe modułu oraz czyste funkcje: skanowanie i parsowanie
tematów (``list_topic_slugs``/``parse_title``/``group_of``), mapowanie linków
(``map_link``/``is_dane_ruling``), budowę indeksu i odczyt treści tematu
(``load_index``/``load_topic``) oraz filtrowanie i wyznaczanie aktywnej pozycji
(``filter_entries``/``active_slugs``).

Modele są niemutowalne (``frozen=True``), bo treść reguł jest tylko do odczytu i
nie dotyka ``GameState`` — router API wyłącznie ją serwuje, nie commituje stanu.
"""

from __future__ import annotations

import re
from collections.abc import Container, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

#: Mapowanie prefiksu pliku na klucz grupy indeksu (Req 2.2). Kolejność grup
#: w indeksie wynika z ``RULE_PREFIXES`` (Reguły → Frakcje → Komponenty).
_PREFIX_TO_GROUP: dict[str, str] = {
    "R_": "rules",
    "F_": "factions",
    "C_": "components",
}

#: Dopasowanie nagłówka poziomu 1 (jedno ``#`` + co najmniej jedna spacja/tab,
#: dalej tekst tytułu w grupie 1). Flaga ``MULTILINE`` pozwala wyłapać nagłówek
#: nie na pierwszej linii pliku; wymóg braku kolejnego ``#`` bezpośrednio po
#: pierwszym (``[ \t]``) odrzuca ``##``..``######`` (tylko poziom ``# ``).
_H1_RE: re.Pattern[str] = re.compile(r"^#[ \t]+(.+?)[ \t]*$", re.MULTILINE)

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


# --- Czyste funkcje: skanowanie i parsowanie tematów -------------------


def list_topic_slugs(rules_dir: Path) -> list[str]:
    """Zwraca slugi wszystkich plików tematów, posortowane deterministycznie.

    Skanuje katalog ``rules_dir`` w poszukiwaniu plików ``.md`` o prefiksach
    ``R_``/``F_``/``C_`` (patrz ``RULE_PREFIXES``) i zwraca ich slugi — nazwy bez
    rozszerzenia ``.md`` (np. ``R_movement``). Pliki pomocnicze zrzutu
    (``INDEX.md``, ``SOURCE.md``) nie mają tych prefiksów, więc są pomijane.

    Funkcja jest czysta: jedynym efektem ubocznym jest odczyt listy plików z
    przekazanego katalogu; nie czyta stanu globalnego ani nie importuje HTTP.

    Args:
        rules_dir: Katalog zrzutu reguł (``config.RULES_DIR``).

    Returns:
        Posortowana alfabetycznie (deterministycznie) lista slugów tematów.
        Pusta lista, gdy katalog nie istnieje lub nie zawiera plików tematów.
    """
    if not rules_dir.is_dir():
        return []
    slugs = [
        path.stem
        for path in rules_dir.glob("*.md")
        if path.name.startswith(RULE_PREFIXES)
    ]
    return sorted(slugs)


def parse_title(markdown: str, slug: str) -> str:
    """Wyznacza tytuł tematu z treści Markdown albo z fallbackiem na slug.

    Tytuł to tekst pierwszego nagłówka poziomu ``# `` (jedno ``#`` + spacja).
    Gdy treść nie zawiera takiego nagłówka, tytułem jest sam ``slug``
    (Req 2.4/2.5, 3.3).

    Args:
        markdown: Surowa treść pliku tematu.
        slug: Topic_Slug tematu — fallback przy braku nagłówka ``# ``.

    Returns:
        Tekst pierwszego nagłówka ``# `` (przycięty z białych znaków) albo slug.
    """
    match = _H1_RE.search(markdown)
    if match is None:
        return slug
    return match.group(1).strip()


def group_of(slug: str) -> str:
    """Mapuje prefiks slug na klucz grupy indeksu.

    ``R_`` → ``"rules"``, ``F_`` → ``"factions"``, ``C_`` → ``"components"``
    (Req 2.2).

    Args:
        slug: Topic_Slug tematu (np. ``R_movement``, ``F_arborec``).

    Returns:
        Klucz grupy: ``"rules"`` | ``"factions"`` | ``"components"``.

    Raises:
        ValueError: Gdy slug nie zaczyna się od żadnego ze znanych prefiksów
            ``RULE_PREFIXES`` — sygnał, że temat nie należy do zrzutu reguł.
    """
    for prefix, group in _PREFIX_TO_GROUP.items():
        if slug.startswith(prefix):
            return group
    raise ValueError(f"Slug spoza zrzutu reguł (nieznany prefiks): {slug!r}")


# --- Czyste funkcje: mapowanie linków i klasyfikacja rulingu Dane -------


def map_link(url: str, known_slugs: Container[str]) -> LinkTarget:
    """Odwzorowuje URL z treści tematu na cel nawigacji (Link_Mapper).

    URL postaci ``https://www.tirules2.com/<slug>`` (z opcjonalnym ``www.`` i
    opcjonalnym trailing slash — oba obsługuje ``TIRULES_URL_RE``) jest mapowany na
    Internal_Link wskazujący lokalny temat WTEDY i TYLKO WTEDY, gdy wydobyty slug
    należy do ``known_slugs`` (Req 4.1). W każdym innym przypadku — URL spoza
    tirules2.com albo tirules2.com ze slug nieznanym lokalnie — zwracany jest
    External_Link zachowujący oryginalny ``url`` bez zmian (Req 4.3).

    Funkcja jest czysta: nie czyta dysku ani stanu globalnego; zbiór znanych slugów
    przekazywany jest jawnie jako ``known_slugs`` (np. z ``list_topic_slugs``).

    Args:
        url: Oryginalny URL hiperłącza z treści tematu.
        known_slugs: Kontener znanych lokalnych slugów (sprawdzenie przez ``in``);
            typowo zbiór zwrócony przez ``list_topic_slugs``.

    Returns:
        ``LinkTarget.internal(slug)`` gdy URL pasuje do tirules2.com, a slug jest
        znany lokalnie; w przeciwnym razie ``LinkTarget.external(url)`` z oryginalnym
        adresem.
    """
    match = TIRULES_URL_RE.match(url)
    if match is not None:
        slug = match.group(1)
        if slug in known_slugs:
            return LinkTarget.internal(slug)
    return LinkTarget.external(url)


def is_dane_ruling(line: str) -> bool:
    """Rozstrzyga, czy pozycja noty jest rulingiem Dane Beltramiego (Req 7.4).

    Zwraca prawdę wtedy i tylko wtedy, gdy ``line`` zawiera marker ``DANE_MARKER``
    (``_[Dane ruling]_``) jako podciąg — zgodnie ze sposobem oznaczania rulingów Dane
    w zrzucie ``docs/rules_tirules/``. Marker bywa dodany na końcu pozycji listy, więc
    sprawdzamy przynależność podciągu, nie równość.

    Args:
        line: Pojedyncza pozycja noty (linia Markdown) do sklasyfikowania.

    Returns:
        ``True`` gdy pozycja zawiera ``DANE_MARKER``, inaczej ``False``.
    """
    return DANE_MARKER in line


# --- Czyste funkcje: filtrowanie indeksu i wyznaczanie aktywnej pozycji -

# Uwaga: poniższe funkcje są WZORCEM REFERENCYJNYM dla frontendowych
# odpowiedników (`useRulesSearch` — filtrowanie; oznaczanie aktywnego tematu w
# `TopicIndexPanel`). Trzymanie reguły w czystej funkcji rdzenia gwarantuje jedno
# źródło prawdy spójne między backendem a frontem (Req 5.2/5.4/5.6, 9.4).


def filter_entries(
    entries: Sequence[TopicIndexEntry], query: str
) -> list[TopicIndexEntry]:
    """Filtruje pozycje indeksu po podciągu w tytule lub slug (bez wielkości liter).

    Zapytanie jest najpierw przycinane z wiodących i końcowych białych znaków, a
    następnie sprowadzane do małych liter. Pozycja pasuje wtedy i tylko wtedy, gdy
    przetworzone zapytanie jest podciągiem tytułu LUB slug pozycji (oba także
    sprowadzone do małych liter) — dopasowanie jest case-insensitive (Req 5.2).

    Gdy zapytanie po przycięciu jest puste (pusty łańcuch albo same białe znaki),
    zwracany jest PEŁNY zbiór pozycji w PIERWOTNEJ kolejności — bez filtrowania
    (Req 5.4/5.6).

    Funkcja jest czysta: nie modyfikuje wejścia ani stanu globalnego; zwraca nową
    listę zachowującą kolejność wejścia (pozycje pasujące w tej samej kolejności,
    w jakiej występują w ``entries``).

    Args:
        entries: Sekwencja pozycji indeksu do przefiltrowania (kolejność istotna).
        query: Surowy tekst zapytania z pola wyszukiwania (0–200 znaków).

    Returns:
        Nowa lista pozycji pasujących do zapytania, w kolejności z ``entries``; dla
        zapytania pustego po trim — pełny zbiór w pierwotnej kolejności.
    """
    needle = query.strip().lower()
    if not needle:
        # Puste zapytanie po trim → pełny indeks w pierwotnej kolejności (Req 5.4/5.6).
        return list(entries)
    return [
        entry
        for entry in entries
        if needle in entry.title.lower() or needle in entry.slug.lower()
    ]


def active_slugs(
    entries: Sequence[TopicIndexEntry], open_slug: str | None
) -> dict[str, bool]:
    """Wyznacza flagę aktywności dla każdej pozycji indeksu (Req 9.4).

    Zwraca mapowanie ``slug -> bool``, w którym wartość ``True`` ma DOKŁADNIE jedna
    pozycja — ta, której slug równa się ``open_slug`` — o ile ``open_slug`` występuje
    w ``entries``. Wszystkie pozostałe pozycje mają ``False``. Gdy ``open_slug`` jest
    ``None`` albo nie odpowiada żadnej pozycji, wszystkie wartości są ``False`` (brak
    otwartego tematu → brak aktywnej pozycji).

    Mapowanie (zamiast pojedynczego slug) jest wygodnym wzorcem dla warstwy UI:
    panel indeksu odczytuje ``aktywne[slug]`` dla każdej renderowanej pozycji, a
    niezmiennik „dokładnie jedna aktywna" (Property 13) jest tu wprost sprawdzalny.

    Funkcja jest czysta: nie modyfikuje wejścia; dla powtórzonych slugów ostatnia
    pozycja nadpisuje wcześniejsze wpisy w mapie (indeks z założenia ma unikalne
    slugi — jedna pozycja na plik).

    Args:
        entries: Sekwencja pozycji indeksu.
        open_slug: Slug aktualnie otwartego tematu albo ``None``, gdy żaden nie jest
            otwarty.

    Returns:
        Mapowanie ``slug -> bool`` z dokładnie jedną wartością ``True`` dla
        ``open_slug`` obecnego w ``entries``; w przeciwnym razie same ``False``.
    """
    return {entry.slug: entry.slug == open_slug for entry in entries}


# --- Czyste funkcje: budowa indeksu i odczyt treści tematu --------------

#: Etykiety grup po polsku dla indeksu (Req 2.2). Klucz → etykieta widoczna w UI.
_GROUP_LABELS: dict[str, str] = {
    "rules": "Reguły",
    "factions": "Frakcje",
    "components": "Komponenty",
}

#: Kolejność grup w indeksie (Req 2.3): Reguły → Frakcje → Komponenty. Wynika
#: wprost z kolejności prefiksów w ``RULE_PREFIXES`` zmapowanych przez ``group_of``.
_GROUP_ORDER: tuple[str, ...] = tuple(_PREFIX_TO_GROUP.values())


def _topic_path(rules_dir: Path, slug: str) -> Path:
    """Buduje ścieżkę pliku tematu z katalogu zrzutu i slug.

    Pomocnicza, wewnętrzna funkcja — sam slug jest wcześniej walidowany względem
    ``list_topic_slugs`` (patrz ``load_topic``), więc nie zawiera separatorów
    ścieżki ani ``..`` i nie wyprowadza poza ``rules_dir``.
    """
    return rules_dir / f"{slug}.md"


def load_index(rules_dir: Path) -> list[TopicGroup]:
    """Buduje Topic_Index: pełną, rozłączną partycję plików tematów po grupach.

    Skanuje ``rules_dir`` (przez ``list_topic_slugs``), dla każdego slug czyta tytuł
    z pierwszego nagłówka ``# `` (``parse_title`` nad treścią pliku; fallback na slug)
    i przypisuje grupę po prefiksie (``group_of``). Zwraca listę grup w stałej
    kolejności Reguły → Frakcje → Komponenty (``_GROUP_ORDER``), każda z etykietą po
    polsku i krotką pozycji w deterministycznej kolejności slugów (Req 2.1–2.5, 2.3).

    Grupy bez pozycji są pomijane — w realnym zrzucie wszystkie trzy są niepuste, ale
    pominięcie pustej grupy zachowuje niezmiennik „każda pozycja indeksu ma swój plik"
    bez sztucznych, pustych nagłówków grup.

    Funkcja jest czysta: jedyny efekt uboczny to odczyt katalogu i plików tematów z
    przekazanego ``rules_dir``; nie czyta stanu globalnego ani nie importuje HTTP.

    Args:
        rules_dir: Katalog zrzutu reguł (``config.RULES_DIR``).

    Returns:
        Lista ``TopicGroup`` w kolejności Reguły → Frakcje → Komponenty; każda grupa
        zawiera pozycje posortowane jak ``list_topic_slugs``. Pusta lista, gdy katalog
        nie zawiera żadnych plików tematów.
    """
    # Grupujemy slugi według klucza grupy, zachowując deterministyczną kolejność
    # z list_topic_slugs (posortowaną alfabetycznie).
    by_group: dict[str, list[TopicIndexEntry]] = {key: [] for key in _GROUP_ORDER}
    for slug in list_topic_slugs(rules_dir):
        group = group_of(slug)
        markdown = _topic_path(rules_dir, slug).read_text(encoding="utf-8")
        title = parse_title(markdown, slug)
        by_group[group].append(TopicIndexEntry(slug=slug, title=title, group=group))

    # Budujemy grupy w stałej kolejności Reguły → Frakcje → Komponenty; pomijamy puste.
    return [
        TopicGroup(
            group=key,
            label=_GROUP_LABELS[key],
            entries=tuple(by_group[key]),
        )
        for key in _GROUP_ORDER
        if by_group[key]
    ]


def _is_empty_note(markdown: str) -> bool:
    """Rozstrzyga, czy treść tematu F/C nie zawiera żadnej pozycji noty (Req 7.3).

    Zwraca ``True`` wtedy i tylko wtedy, gdy po usunięciu wiersza nagłówka ``# ``,
    wierszy blockquote źródła (zaczynających się od ``>``), nagłówków sekcji
    (``##``..``######`` — struktura, nie treść noty) oraz pustych wierszy nie pozostaje
    żaden wiersz treści. Dodanie dowolnej pozycji noty (pozycji listy lub akapitu)
    sprawia, że funkcja zwraca ``False`` (Property 10).

    Uwaga: wywoływana wyłącznie dla grup F/C — klasyfikację „zawsze fałsz dla Reguł"
    wymusza ``load_topic`` (grupa ``rules`` nigdy nie trafia tutaj).
    """
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue  # pusty wiersz — pomijamy
        if line.startswith("#"):
            continue  # nagłówek H1 lub sekcja (##..######) — struktura, nie nota
        if line.startswith(">"):
            continue  # blockquote źródła — zachowywany, nie jest notą
        return False  # dowolny inny niepusty wiersz = pozycja noty
    return True


def load_topic(rules_dir: Path, slug: str) -> TopicContent:
    """Czyta treść pojedynczego tematu i waliduje slug (ochrona przed path traversal).

    Slug jest akceptowany wyłącznie, gdy należy do zbioru realnych slugów zwróconych
    przez ``list_topic_slugs`` — to odrzuca próby path-traversal (``..``, separatory
    ścieżki) oraz nazwy spoza zrzutu, bo tylko istniejące pliki ``R_``/``F_``/``C_``
    trafiają do tej listy. Dla nieznanego slug podnosi ``FileNotFoundError`` (Req 6.3,
    Property 9) — router API mapuje go na HTTP 404.

    Tytuł wyznacza ``parse_title`` (pierwszy nagłówek ``# `` lub slug jako fallback),
    grupę — ``group_of`` (prefiks). ``is_empty_note`` jest ustawiane tylko dla grup
    Frakcje/Komponenty (``_is_empty_note``); dla grupy Reguły zawsze ``False`` (Req 7.3).

    Funkcja jest czysta: jedyny efekt uboczny to odczyt listy plików i treści z
    przekazanego ``rules_dir``; nie importuje FastAPI/HTTP.

    Args:
        rules_dir: Katalog zrzutu reguł (``config.RULES_DIR``).
        slug: Topic_Slug żądanego tematu (nazwa pliku bez ``.md``).

    Returns:
        ``TopicContent`` z surowym ``markdown``, tytułem, grupą i flagą
        ``is_empty_note``.

    Raises:
        FileNotFoundError: Gdy ``slug`` nie odpowiada żadnemu realnemu tematowi w
            ``rules_dir`` (nieznany slug albo próba path-traversal).
    """
    if slug not in list_topic_slugs(rules_dir):
        raise FileNotFoundError(f"Brak tematu o slug: {slug!r}")

    markdown = _topic_path(rules_dir, slug).read_text(encoding="utf-8")
    title = parse_title(markdown, slug)
    group = group_of(slug)
    # Pusta nota dotyczy wyłącznie grup F/C; grupa Reguły zawsze ma is_empty_note=False.
    is_empty_note = group != "rules" and _is_empty_note(markdown)

    return TopicContent(
        slug=slug,
        title=title,
        group=group,
        markdown=markdown,
        is_empty_note=is_empty_note,
    )
