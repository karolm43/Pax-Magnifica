"""Strażnik anty-hardkodowania danych gry (część backendowa).

Zestaw testów pilnujących, by przyszłe moduły FAKTYCZNIE korzystały z lejka danych
(``StaticDataRegistry`` → ``ComponentCatalog`` → ``load_components``) oraz z jedynego
źródła listy źródeł kanonicznych (``src/core/sources.py`` → ``SOURCE_PRIORITY``),
zamiast obchodzić je własnymi loaderami albo przeklejoną listą danych „na sztywno".

Dwa niezależne testy:

1. :func:`test_zrodla_kanoniczne_tylko_w_sources_py` — lista identyfikatorów źródeł
   kanonicznych (``base``, ``pok``, ``codex1..4``, ``thunders_edge``) jako jedna
   KOLEKCJA literałów (krotka/lista/zbiór) NIE pojawia się w ``src/core/`` ani
   ``src/api/`` poza ``src/core/sources.py``. Pojedyncze napisy (porównanie
   ``source == "pok"``, komentarz, docstring) są DOZWOLONE — łapiemy tylko
   ZDUPLIKOWANĄ definicję całej listy (sygnatura: kolekcja literałów zawierająca
   co najmniej 3 z tych nazw). To ma wykryć „ktoś przekleił listę źródeł zamiast
   zaimportować ``SOURCE_PRIORITY``".

2. :func:`test_dane_gry_czytane_tylko_przez_rejestr_i_loader` — żaden plik w
   ``src/core/`` (poza ``registry.py``, ``component_loader.py``, ``references.py``,
   ``components.py``) ani w ``src/api/`` NIE czyta bezpośrednio z katalogów danych
   kategorii (odwołanie do ``config.<KATEGORIA>_DATA_DIR`` POŁĄCZONE z operacją
   odczytu dysku, albo ``glob`` po ``assets/data/<kategoria>``). Dane kategorii
   mają iść przez ``registry.catalog`` / ``load_components``.

Nazwy źródeł kanonicznych i lista dozwolonych loaderów są STAŁĄ W TEŚCIE (nie w
kodzie produkcyjnym), wzorem ``tests/test_locality_guard.py``. Skanery operują na
AST (literały napisowe poza docstringami, odwołania ``config.*`` i wywołania
odczytu), więc są odporne na fałszywe alarmy z komentarzy i docstringów.
"""

from __future__ import annotations

import ast
from pathlib import Path

from src import config
from src.audit.locality import collect_sources

# Identyfikatory źródeł kanonicznych TI4 (RULES.md 14). Celowo trzymane w teście —
# jedyną definicją całej listy w kodzie produkcyjnym jest SOURCE_PRIORITY.
CANONICAL_SOURCE_NAMES: frozenset[str] = frozenset(
    {"base", "pok", "codex1", "codex2", "codex3", "codex4", "thunders_edge"}
)

# Próg sygnatury „zduplikowanej listy": tyle różnych nazw źródeł w JEDNEJ kolekcji
# literałów wystarcza, by uznać to za przeklejoną listę (a nie pojedyncze porównanie).
_DUPLICATE_LIST_THRESHOLD = 3

# Wzorce glob kodu backendu skanowanego przez oba testy.
_CORE_PATTERN = "core/**/*.py"
_API_PATTERN = "api/**/*.py"

# Plik, który JEST jedynym źródłem SOURCE_PRIORITY — wyłączony z testu źródeł.
_SOURCES_FILE = "core/sources.py"

# Loadery, których ROLĄ jest czytanie danych kategorii z dysku — dozwolone w teście
# bezpośredniego odczytu. ``components.py`` trzyma tabelę CATEGORY_SPECS (mapowanie
# kategoria → katalog config), ale sam z dysku NIE czyta; mimo to go wyłączamy jako
# miejsce definicji specyfikacji, by test nie zależał od tego szczegółu.
_DATA_LOADER_FILES: frozenset[str] = frozenset(
    {
        "core/registry.py",
        "core/component_loader.py",
        "core/references.py",
        "core/components.py",
    }
)

# Nazwy stałych w ``src/config`` wskazujących katalogi danych KATEGORII
# Katalogu_Komponentów (czytane wyłącznie przez loader). Wyliczane z modułu config,
# by test nie rozjechał się z rzeczywistością przy dodaniu nowej kategorii.
_COMPONENT_DATA_DIR_CONSTS: frozenset[str] = frozenset(
    name
    for name in dir(config)
    if name.endswith("_DATA_DIR") and isinstance(getattr(config, name), Path)
) - {
    # Kategorie „starsze" żyjące w StaticDataRegistry (nie w Katalogu_Komponentów):
    # ich czytanie w registry.py jest zamierzone i dozwolone. Wykluczamy je, by test
    # pilnował wyłącznie katalogów kategorii Katalogu_Komponentów.
    "UNITS_DATA_DIR",
    "TECHNOLOGIES_DATA_DIR",
    "FACTIONS_DATA_DIR",
    "LEADERS_DATA_DIR",
    "ABILITIES_DATA_DIR",
    "BREAKTHROUGHS_DATA_DIR",
}

# Metody/funkcje uznawane za „odczyt z dysku".
_READ_CALL_NAMES: frozenset[str] = frozenset(
    {"glob", "iterdir", "rglob", "read_text", "read_bytes", "open"}
)


# --- Pomocnicze: parsowanie AST -----------------------------------------


def _backend_sources() -> dict[str, str]:
    """Wczytuje pliki ``*.py`` z ``src/core`` i ``src/api`` (klucz = ścieżka POSIX)."""
    root = config.PROJECT_ROOT / "src"
    return collect_sources(root, (_CORE_PATTERN, _API_PATTERN))


def _parse(path: str, text: str) -> ast.Module | None:
    """Parsuje źródło; ``None`` gdy plik się nie kompiluje (pomijamy go)."""
    try:
        return ast.parse(text, filename=path)
    except SyntaxError:
        return None


# --- Test 1: lista źródeł kanonicznych tylko w sources.py ---------------


def _collection_literal_source_names(node: ast.AST) -> set[str]:
    """Zwraca nazwy źródeł kanonicznych w JEDNEJ kolekcji literałów napisowych.

    ``node`` to kolekcja (``Tuple``/``List``/``Set``); liczymy wyłącznie elementy
    będące stałymi napisowymi należącymi do zbioru nazw kanonicznych.
    """
    if not isinstance(node, ast.Tuple | ast.List | ast.Set):
        return set()
    return {
        element.value
        for element in node.elts
        if isinstance(element, ast.Constant)
        and isinstance(element.value, str)
        and element.value in CANONICAL_SOURCE_NAMES
    }


def _find_duplicated_source_lists(path: str, tree: ast.Module) -> list[tuple[int, int]]:
    """Znajduje kolekcje literałów z ≥ progu nazw źródeł (linia, liczba nazw)."""
    findings: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        names = _collection_literal_source_names(node)
        if len(names) >= _DUPLICATE_LIST_THRESHOLD:
            findings.append((getattr(node, "lineno", 0), len(names)))
    return findings


def test_zrodla_kanoniczne_tylko_w_sources_py() -> None:
    """Lista źródeł kanonicznych jako kolekcja literałów żyje tylko w ``sources.py``.

    Wykrywamy przeklejoną listę (krotka/lista/zbiór z ≥3 nazwami źródeł). Pojedyncze
    porównania napisów, komentarze i docstringi są dozwolone. Jeśli ten test zapala
    się na nowym kodzie — zamiast tłumić, zaimportuj ``SOURCE_PRIORITY`` z
    ``src/core/sources.py`` zamiast przepisywać listę.
    """
    offenders: list[str] = []
    for path, text in sorted(_backend_sources().items()):
        if path == _SOURCES_FILE:
            continue
        tree = _parse(path, text)
        if tree is None:
            continue
        for line, count in _find_duplicated_source_lists(path, tree):
            offenders.append(f"{path}:{line} (kolekcja z {count} nazwami źródeł)")
    assert offenders == [], (
        "Zduplikowana lista źródeł kanonicznych poza src/core/sources.py "
        "(zaimportuj SOURCE_PRIORITY zamiast przepisywać listę): "
        + ", ".join(offenders)
    )


# --- Test 2: dane kategorii czytane tylko przez rejestr/loader ----------


def _config_dir_names_used(tree: ast.Module) -> set[str]:
    """Nazwy stałych katalogów kategorii użyte jako ``config.<NAZWA>`` lub ``<NAZWA>``.

    Obejmuje zarówno dostęp przez atrybut modułu (``config.ACTION_CARDS_DATA_DIR``),
    jak i bezpośrednie użycie zaimportowanej nazwy (``ACTION_CARDS_DATA_DIR``).
    """
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _COMPONENT_DATA_DIR_CONSTS:
            used.add(node.attr)
        elif isinstance(node, ast.Name) and node.id in _COMPONENT_DATA_DIR_CONSTS:
            used.add(node.id)
    return used


def _has_filesystem_read(tree: ast.Module) -> bool:
    """Czy w pliku występuje wywołanie odczytu z dysku (``glob``/``open``/``read_*``)."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _READ_CALL_NAMES:
            return True
        if isinstance(func, ast.Name) and func.id in _READ_CALL_NAMES:
            return True
    return False


def _globs_assets_data_category(tree: ast.Module) -> list[int]:
    """Linie literałów napisowych wyglądających na glob po ``assets/data/<kategoria>``.

    Łapiemy ścieżki z segmentem ``data`` pod ``assets`` zawierające wieloznacznik
    (``*``) — czyli próbę iterowania po surowych plikach danych z pominięciem loadera.
    """
    lines: list[int] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        value = node.value.replace("\\", "/")
        if "*" in value and "assets/data/" in value:
            lines.append(getattr(node, "lineno", 0))
    return lines


def test_dane_gry_czytane_tylko_przez_rejestr_i_loader() -> None:
    """Dane kategorii czyta wyłącznie rejestr/loader, reszta idzie przez katalog.

    Naruszenie = plik spoza listy loaderów, który ODWOŁUJE się do katalogu danych
    kategorii (``config.<KATEGORIA>_DATA_DIR``) i zarazem CZYTA z dysku, albo który
    globuje ``assets/data/<kategoria>``. Reszta modułów ma czytać dane przez
    ``registry.catalog`` / ``load_components`` — nie własnym parserem JSON.

    Jeśli test zapala się na nowym kodzie — nie tłum go: zamień bezpośredni odczyt
    na ``registry.catalog.all(kategoria)`` / ``load_components(...)``.
    """
    offenders: list[str] = []
    for path, text in sorted(_backend_sources().items()):
        if path in _DATA_LOADER_FILES:
            continue
        tree = _parse(path, text)
        if tree is None:
            continue
        dir_consts = _config_dir_names_used(tree)
        if dir_consts and _has_filesystem_read(tree):
            offenders.append(
                f"{path} (odwołanie do {sorted(dir_consts)} + odczyt z dysku)"
            )
        for line in _globs_assets_data_category(tree):
            offenders.append(f"{path}:{line} (glob po assets/data/<kategoria>)")
    assert offenders == [], (
        "Bezpośredni odczyt danych kategorii z pominięciem rejestru/loadera "
        "(czytaj przez registry.catalog / load_components): " + ", ".join(offenders)
    )
