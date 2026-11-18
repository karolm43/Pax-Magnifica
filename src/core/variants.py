"""Moduły wariantów gry: fanowskie zestawy, erraty komponentów, własne komponenty, parametry reguł.

Jedno miejsce prawdy to DANE: ``assets/config/variants.json`` (lista modułów). Kod nie zna
żadnego konkretnego zestawu fanowskiego. Instrukcja krok po kroku: ``docs/WARIANTY.md``.

Model (moduł ma ``source`` = pole ``source`` wpisów w plikach ``assets/data/<kategoria>/``;
źródło NIE musi być w ``enabled_sources.json``):

- ``replaces`` = [kategoria]: ERRATA W MIEJSCU. Wpis źródła z ``homebrewReplacesID`` nadpisuje
  treść oficjalnego komponentu (tekst, liczby, wymagania…), a komponent ZACHOWUJE oficjalne id.
  Dzięki temu cały silnik (listy frakcji, talie, wymagania technologii, statystyki jednostek)
  od razu widzi nową wersję. Odwołania wewnątrz danych wariantu (``bsp_inf2``) są
  przemapowane na id oficjalne (``inf2``). Rejestr zapisuje podmienione komponenty
  (``registry.variant_replaced``), a ``rules_hooks`` wyłącza ich OFICJALNE hooki i włącza hooki
  zarejestrowane z ``variant=<źródło>`` (brak = ręczna ewidencja, jak każda nieoprogramowana
  karta). Kategorie: wartości ``ComponentCategory`` (``technologies``, ``units``, ``leaders``,
  ``factions``, ``abilities``, ``breakthroughs``, ``relics``, ``action_cards``, ``agendas``,
  ``explores``, ``promissory_notes``, ``public_objectives``, ``secret_objectives``,
  ``genericcards`` (np. ploty Firmament), ``strategy_cards``…) albo ``"all"``.
- ``adds`` = [kategoria]: NOWE komponenty źródła (bez ``homebrewReplacesID``) pod własnymi id.
- ``decks`` = {typ talii: alias}: CAŁA talia danego typu w grze to talia wariantu.
- ``rules`` = {klucz: wartość}: parametry reguł/setupu nadpisywane w grze (``rule_value``),
  np. ``fracture.roll_success``.

Rejestr danych jest budowany PER ZESTAW MODUŁÓW (``StaticDataRegistry(variant_ids=...)``);
``AppContext.registry`` zwraca rejestr bieżącej gry (``GameState.decks.variants``).
"""

from __future__ import annotations

import json
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

from src import config
from src.core.components import ComponentCategory, DeckDef, ExplorationDef
from src.core.sources import AGENDA_STANDARD, source_rank

if TYPE_CHECKING:
    from src.core.registry import StaticDataRegistry

# Pole surowego wpisu: id oficjalnego komponentu, który ten wpis zastępuje (dane AsyncTI4).
REPLACES_FIELD = "homebrewReplacesID"
# Pola dopisywane do nadpisanego wpisu (ślad dla UI i raportów).
VARIANT_SOURCE_FIELD = "variantSource"
VARIANT_ID_FIELD = "variantId"
# Pola tożsamości - nie są kopiowane z wpisu wariantu na komponent oficjalny.
_IDENTITY_FIELDS = frozenset({"id", "alias", "source", REPLACES_FIELD})
# Pola oficjalnego wpisu, które errata unieważnia (obrazek karty pokazywałby stary tekst).
_STALE_FIELDS = frozenset({"imageURL", "image", "imageUrl"})
ALL = "all"
EXPLORE = "explore"

# Typ talii (``DeckDef.deck_type`` / klucze ``decks``) -> kategoria kart w katalogu.
DECK_TYPE_CATEGORY: Mapping[str, ComponentCategory] = {
    "agenda": ComponentCategory.AGENDA,
    "action_card": ComponentCategory.ACTION_CARD,
    "relic": ComponentCategory.RELIC,
    EXPLORE: ComponentCategory.EXPLORATION,
    "secret_objective": ComponentCategory.SECRET_OBJECTIVE,
    "public_stage_1_objective": ComponentCategory.PUBLIC_OBJECTIVE,
    "public_stage_2_objective": ComponentCategory.PUBLIC_OBJECTIVE,
}
# Kategorie, które moduł może podmieniać/dodawać (bez ``decks`` - talie to osobny klucz).
VARIANT_CATEGORIES: frozenset[ComponentCategory] = frozenset(ComponentCategory) - {
    ComponentCategory.DECK
}


class VariantConfigError(ValueError):
    """Błędny manifest wariantów albo wybór modułów (nieznany / kolidujący)."""


@dataclass(frozen=True)
class VariantModule:
    """Jeden moduł wariantu z ``variants.json``."""

    id: str
    name: str
    source: str
    description: str = ""
    badge: str | None = None
    decks: Mapping[str, str] = field(default_factory=dict)
    replaces: frozenset[ComponentCategory] = frozenset()
    adds: frozenset[ComponentCategory] = frozenset()
    rules: Mapping[str, Any] = field(default_factory=dict)
    default: bool = False

    def deck_types(self) -> frozenset[str]:
        """Typy talii zastępowanych w całości."""
        return frozenset(self.decks)


def _categories(module_id: str, key: str, raw: object) -> frozenset[ComponentCategory]:
    """``replaces``/``adds``: lista kategorii (wartości ``ComponentCategory``) albo ``"all"``."""
    if raw is None:
        return frozenset()
    if raw == ALL:
        return VARIANT_CATEGORIES
    if not isinstance(raw, list) or not all(isinstance(v, str) for v in raw):
        raise VariantConfigError(f"Variant {module_id!r}: {key!r} must be a list or 'all'.")
    found: set[ComponentCategory] = set()
    for value in raw:
        if value == ALL:
            return VARIANT_CATEGORIES
        try:
            category = ComponentCategory(value)
        except ValueError:
            raise VariantConfigError(
                f"Variant {module_id!r}: unknown category {value!r} in {key!r}."
            ) from None
        if category is ComponentCategory.DECK:
            raise VariantConfigError(f"Variant {module_id!r}: use 'decks' for whole decks.")
        found.add(category)
    return frozenset(found)


def _parse_module(raw: object, index: int) -> VariantModule:
    if not isinstance(raw, dict):
        raise VariantConfigError(f"Variant module #{index} must be an object.")
    module_id, name, source = raw.get("id"), raw.get("name"), raw.get("source")
    if not (
        isinstance(module_id, str) and module_id
        and isinstance(name, str) and name
        and isinstance(source, str) and source
    ):
        raise VariantConfigError(f"Variant module #{index} needs non-empty id, name and source.")
    decks = raw.get("decks") or {}
    if not isinstance(decks, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in decks.items()
    ):
        raise VariantConfigError(f"Variant {module_id!r}: 'decks' must map deck type -> alias.")
    unknown = sorted(set(decks) - set(DECK_TYPE_CATEGORY))
    if unknown:
        raise VariantConfigError(f"Variant {module_id!r}: unknown deck types {unknown}.")
    rules = raw.get("rules") or {}
    if not isinstance(rules, dict):
        raise VariantConfigError(f"Variant {module_id!r}: 'rules' must be an object.")
    badge = raw.get("badge")
    return VariantModule(
        id=module_id,
        name=name,
        source=source,
        description=str(raw.get("description") or ""),
        badge=badge if isinstance(badge, str) and badge else None,
        decks=dict(decks),
        replaces=_categories(module_id, "replaces", raw.get("replaces")),
        adds=_categories(module_id, "adds", raw.get("adds")),
        rules=dict(rules),
        default=raw.get("default") is True,
    )


def parse_modules(raw: object) -> dict[str, VariantModule]:
    """Parsuje treść manifestu (``{"modules": [...]}``); kolejność modułów zachowana."""
    entries = raw.get("modules", []) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise VariantConfigError("variants.json: 'modules' must be a list.")
    result: dict[str, VariantModule] = {}
    for index, entry in enumerate(entries):
        module = _parse_module(entry, index)
        if module.id in result:
            raise VariantConfigError(f"Duplicate variant module id {module.id!r}.")
        result[module.id] = module
    return result


@cache
def load_modules(path: Path = config.VARIANTS_PATH) -> Mapping[str, VariantModule]:
    """Moduły z manifestu (brak pliku = brak wariantów). Wynik buforowany."""
    if not path.is_file():
        return {}
    return parse_modules(json.loads(path.read_text(encoding="utf-8")))


def modules() -> Mapping[str, VariantModule]:
    """Moduły domyślnego manifestu ``assets/config/variants.json``."""
    return load_modules(config.VARIANTS_PATH)


def variant_sources(mods: Iterable[VariantModule] | None = None) -> frozenset[str]:
    """Źródła modułów - ich talie nie biorą udziału w wyborze talii oficjalnej."""
    return frozenset(m.source for m in (modules().values() if mods is None else mods))


def default_module_ids() -> list[str]:
    """Moduły włączone domyślnie (``"default": true``)."""
    return [m.id for m in modules().values() if m.default]


# --- Plan ładowania i nakładanie wpisów (loader i rejestr) -----------------------------------

E = TypeVar("E")


@dataclass(frozen=True)
class VariantLoadPlan:
    """Co rejestr bierze ze źródeł modułów gry (spoza ``enabled_sources.json``).

    ``full``: kategoria -> źródła ładowane w całości (karty talii zastępowanych w całości);
    ``adds``: kategoria -> źródła, których NOWE komponenty (bez ``homebrewReplacesID``)
    wchodzą pod własnymi id; ``replacements``: kategoria -> źródła, których wpisy z
    ``homebrewReplacesID`` nadpisują komponenty oficjalne; ``decks``: źródło -> typy talii.
    """

    full: Mapping[ComponentCategory, frozenset[str]] = field(default_factory=dict)
    adds: Mapping[ComponentCategory, frozenset[str]] = field(default_factory=dict)
    replacements: Mapping[ComponentCategory, frozenset[str]] = field(default_factory=dict)
    decks: Mapping[str, frozenset[str]] = field(default_factory=dict)
    # Odwołania w danych wariantu: id wpisu wariantu -> id oficjalne (``bsp_inf2`` -> ``inf2``).
    id_map: Mapping[str, str] = field(default_factory=dict)
    # Kolejność źródeł wg wyboru modułów: gdy dwa moduły poprawiają ten sam komponent,
    # wygrywa moduł wybrany WCZEŚNIEJ.
    source_order: tuple[str, ...] = ()

    def sources_for(self, category: ComponentCategory) -> frozenset[str]:
        """Źródła modułów, które mają wpisy w danej kategorii."""
        if category is ComponentCategory.DECK:
            return frozenset(self.decks)
        return (
            self.full.get(category, frozenset())
            | self.adds.get(category, frozenset())
            | self.replacements.get(category, frozenset())
        )

    def own_sources_for(self, category: ComponentCategory) -> frozenset[str]:
        """Źródła, których wpisy wchodzą POD WŁASNYM id (całe talie i nowe komponenty)."""
        if category is ComponentCategory.DECK:
            return frozenset(self.decks)
        return self.full.get(category, frozenset()) | self.adds.get(category, frozenset())

    def is_replacement(self, category: ComponentCategory, entry: Mapping[str, object]) -> bool:
        """Czy wpis to errata komponentu oficjalnego (nadpisanie w miejscu)."""
        source = entry.get("source")
        return (
            isinstance(source, str)
            and source in self.replacements.get(category, frozenset())
            and isinstance(entry.get(REPLACES_FIELD), str)
        )

    def admits(self, category: ComponentCategory, entry: Mapping[str, object]) -> bool:
        """Czy wpis źródła modułu wchodzi do rejestru pod WŁASNYM id."""
        source = entry.get("source")
        if not isinstance(source, str):
            return False
        if category is ComponentCategory.DECK:
            return entry.get("type") in self.decks.get(source, frozenset())
        if source in self.full.get(category, frozenset()):
            return True
        return source in self.adds.get(category, frozenset()) and not isinstance(
            entry.get(REPLACES_FIELD), str
        )

    def overlay(
        self,
        category: ComponentCategory,
        entries: Iterable[tuple[E, Mapping[str, object]]],
        enabled: Collection[str],
        replaced: dict[str, str] | None = None,
        emitted: dict[str, Mapping[str, object]] | None = None,
    ) -> Iterator[tuple[E, Mapping[str, object]]]:
        """Nakłada moduły na wpisy kategorii (czysto, bez plików).

        Wpisy źródeł modułów spoza ``enabled``: erraty nadpisują wpis oficjalny o id/alias =
        ``homebrewReplacesID`` (wpis zachowuje oficjalne id i źródło), wpisy ``admits``
        przechodzą bez zmian, reszta odpada. ``replaced`` (opcjonalnie) dostaje
        ``"<kategoria>:<id oficjalne>" -> źródło`` każdej nałożonej erraty, a ``emitted``
        - surowe wpisy, które moduły zmieniły lub dodały (``"<kategoria>:<id>" -> wpis``, dla UI).
        """
        sources = self.sources_for(category)
        items = list(entries)
        if not sources:
            yield from items
            return
        errata: dict[str, Mapping[str, object]] = {}
        kept: list[tuple[E, Mapping[str, object]]] = []
        for origin, entry in items:
            source = entry.get("source")
            if not isinstance(source, str) or source not in sources or source in enabled:
                kept.append((origin, entry))
            elif self.is_replacement(category, entry):
                target = entry.get(REPLACES_FIELD)
                assert isinstance(target, str)
                known = errata.get(target)
                if known is None or self._rank(entry) < self._rank(known):
                    errata[target] = entry
            elif self.admits(category, entry):
                kept.append((origin, entry))
        for origin, entry in kept:
            source = entry.get("source")
            official_id = _entry_id(entry)
            patch = errata.get(official_id) if official_id is not None else None
            own = isinstance(source, str) and source in sources and source not in enabled
            if own:
                entry = self._remapped(entry)
                if emitted is not None and official_id is not None:
                    emitted[f"{category.value}:{official_id}"] = entry
                yield origin, entry
                continue
            if patch is None or source not in enabled:
                yield origin, entry
                continue
            assert official_id is not None
            merged = self.merge(entry, patch)
            if replaced is not None:
                replaced[f"{category.value}:{official_id}"] = str(patch.get("source"))
            if emitted is not None:
                emitted[f"{category.value}:{official_id}"] = merged
            yield origin, merged

    def _rank(self, entry: Mapping[str, object]) -> int:
        source = entry.get("source")
        order = self.source_order
        return order.index(source) if source in order else len(order)

    def merge(self, official: Mapping[str, object], patch: Mapping[str, object]) -> dict[str, Any]:
        """Wpis oficjalny z treścią erraty (tożsamość oficjalna, odwołania przemapowane)."""
        merged: dict[str, Any] = {
            k: v for k, v in official.items() if k not in _STALE_FIELDS or k in patch
        }
        for key, value in patch.items():
            if key not in _IDENTITY_FIELDS:
                merged[key] = _remap(value, self.id_map)
        merged[VARIANT_SOURCE_FIELD] = patch.get("source")
        merged[VARIANT_ID_FIELD] = _entry_id(patch)
        return merged

    def _remapped(self, entry: Mapping[str, object]) -> Mapping[str, object]:
        """Nowy komponent wariantu: jego odwołania do podmienionych wpisów -> id oficjalne."""
        if not self.id_map:
            return entry
        return {
            key: (value if key in _IDENTITY_FIELDS else _remap(value, self.id_map))
            for key, value in entry.items()
        }


def _entry_id(entry: Mapping[str, object]) -> str | None:
    for key in ("id", "alias"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _remap(value: Any, id_map: Mapping[str, str]) -> Any:
    """Zamienia napisy równe id wariantu na id oficjalne (rekurencyjnie w listach/słownikach)."""
    if isinstance(value, str):
        return id_map.get(value, value)
    if isinstance(value, list):
        return [_remap(v, id_map) for v in value]
    if isinstance(value, dict):
        return {k: _remap(v, id_map) for k, v in value.items()}
    return value


def _scan_id_map(sources: Collection[str], data_dir: Path) -> dict[str, str]:
    """Id wpisów-errat źródeł ``sources`` -> id oficjalne (ze wszystkich plików danych)."""
    if not sources:
        return {}
    id_map: dict[str, str] = {}
    for path in sorted(data_dir.rglob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for entry in raw if isinstance(raw, list) else [raw]:
            if not isinstance(entry, dict) or entry.get("source") not in sources:
                continue
            target, own = entry.get(REPLACES_FIELD), _entry_id(entry)
            if isinstance(target, str) and own is not None and own != target:
                id_map.setdefault(own, target)
    return id_map


def load_plan(
    mods: Iterable[VariantModule], data_dir: Path = config.DATA_DIR
) -> VariantLoadPlan:
    """Plan ładowania dla zestawu modułów gry."""
    full: dict[ComponentCategory, set[str]] = {}
    adds: dict[ComponentCategory, set[str]] = {}
    replacements: dict[ComponentCategory, set[str]] = {}
    decks: dict[str, set[str]] = {}
    mods = list(mods)
    for module in mods:
        for deck_type in module.decks:
            full.setdefault(DECK_TYPE_CATEGORY[deck_type], set()).add(module.source)
            decks.setdefault(module.source, set()).add(deck_type)
        for category in module.adds:
            adds.setdefault(category, set()).add(module.source)
        for category in module.replaces:
            replacements.setdefault(category, set()).add(module.source)
    replacing = {s for found in replacements.values() for s in found}
    return VariantLoadPlan(
        full={k: frozenset(v) for k, v in full.items()},
        adds={k: frozenset(v) for k, v in adds.items()},
        replacements={k: frozenset(v) for k, v in replacements.items()},
        decks={k: frozenset(v) for k, v in decks.items()},
        id_map=_scan_id_map(replacing, data_dir),
        source_order=tuple(dict.fromkeys(m.source for m in mods)),
    )


# --- Wybór modułów w grze ---------------------------------------------------------------------


def validate_selection(module_ids: Iterable[str]) -> list[str]:
    """Sprawdza wybór modułów gry: znane id, bez dwóch całych talii tego samego typu.

    Zwraca listę bez duplikatów (kolejność zachowana). Raises: ``VariantConfigError``.
    """
    known = modules()
    chosen: list[str] = []
    for module_id in module_ids:
        if module_id not in known:
            raise VariantConfigError(f"Unknown game variant: {module_id!r}.")
        if module_id not in chosen:
            chosen.append(module_id)
    owners: dict[str, str] = {}
    for module_id in chosen:
        for deck_type in known[module_id].decks:
            if deck_type in owners:
                raise VariantConfigError(
                    f"Variants {owners[deck_type]!r} and {module_id!r} both replace the "
                    f"{deck_type} deck."
                )
            owners[deck_type] = module_id
    return chosen


def module_for_agenda_variant(agenda_variant: str) -> VariantModule | None:
    """Moduł odpowiadający staremu polu ``agenda_variant`` (np. "absol"); "standard" -> None.

    Raises: ``VariantConfigError`` dla nieznanego wariantu.
    """
    if agenda_variant == AGENDA_STANDARD:
        return None
    for module in modules().values():
        if module.source == agenda_variant and "agenda" in module.decks:
            return module
    raise VariantConfigError(f"Unknown agenda deck variant: {agenda_variant!r}.")


def game_module_ids(
    variant_ids: Iterable[str], agenda_variant: str = AGENDA_STANDARD
) -> tuple[str, ...]:
    """Id modułów gry: ``decks.variants`` + zgodność wstecz z ``decks.agenda_variant``.

    Nieznane id (moduł usunięty z manifestu po zapisaniu gry) są pomijane.
    """
    known = modules()
    result = [i for i in dict.fromkeys(variant_ids) if i in known]
    try:
        legacy = module_for_agenda_variant(agenda_variant)
    except VariantConfigError:
        legacy = None
    if legacy is not None and legacy.id not in result:
        result.append(legacy.id)
    return tuple(result)


def game_modules(
    variant_ids: Iterable[str], agenda_variant: str = AGENDA_STANDARD
) -> list[VariantModule]:
    """Moduły gry (patrz ``game_module_ids``)."""
    known = modules()
    return [known[i] for i in game_module_ids(variant_ids, agenda_variant)]


def resolve_new_game(
    variant_ids: Iterable[str] | None, agenda_deck: str = AGENDA_STANDARD
) -> tuple[list[str], str]:
    """Wybór modułów nowej gry -> (``decks.variants``, ``decks.agenda_variant``).

    ``variant_ids=None`` = moduły domyślne z manifestu. ``agenda_deck`` (stare pole API,
    np. "absol") dokłada moduł talii agend tego źródła. Raises: ``VariantConfigError``.
    """
    ids = list(default_module_ids() if variant_ids is None else variant_ids)
    legacy = module_for_agenda_variant(agenda_deck)
    if legacy is not None:
        ids.append(legacy.id)
    chosen = validate_selection(ids)
    known = modules()
    agenda_owner = next((known[i] for i in chosen if "agenda" in known[i].decks), None)
    return chosen, agenda_owner.source if agenda_owner is not None else AGENDA_STANDARD


def check_decks(registry: StaticDataRegistry) -> None:
    """Sprawdza, że talie modułów rejestru istnieją w katalogu. Raises: ``VariantConfigError``."""
    for module in registry.variant_modules:
        for deck_type in module.decks:
            variant_deck_ids(registry, module, deck_type)


def rule_value[T](registry: StaticDataRegistry, key: str, default: T) -> T:
    """Parametr reguły/setupu: wartość z modułów gry (``rules``) albo ``default``.

    Wartość z manifestu ma typ JSON; wołający podaje domyślną wartość tego samego kształtu.
    """
    if key not in registry.variant_rules:
        return default
    return cast("T", registry.variant_rules[key])


# --- Skład talii --------------------------------------------------------------------------------


def official_deck_ids(registry: StaticDataRegistry, deck_type: str) -> list[str]:
    """Karty NAJWIĘKSZEJ talii danego typu z aktywnych źródeł (talie modułów pominięte).

    Remis rozmiaru rozstrzyga priorytet źródła (RULES.md 14), potem alias.
    """
    fan = variant_sources()
    best: DeckDef | None = None
    decks = registry.catalog.all(ComponentCategory.DECK)
    for deck_id in sorted(decks):
        deck = decks[deck_id]
        if not isinstance(deck, DeckDef) or deck.deck_type != deck_type:
            continue
        if deck.source in fan:
            continue
        if best is None or (-len(deck.card_ids), source_rank(deck.source)) < (
            -len(best.card_ids),
            source_rank(best.source),
        ):
            best = deck
    return list(best.card_ids) if best is not None else []


def variant_deck_ids(
    registry: StaticDataRegistry, module: VariantModule, deck_type: str
) -> list[str]:
    """Karty talii modułu (``decks[deck_type]``). Brak talii w katalogu -> błąd."""
    alias = module.decks[deck_type]
    deck = registry.catalog.get(ComponentCategory.DECK, alias)
    if not isinstance(deck, DeckDef) or not deck.card_ids:
        raise VariantConfigError(
            f"Variant {module.id!r}: deck {alias!r} is not available in the catalog."
        )
    return list(deck.card_ids)


def game_deck_ids(registry: StaticDataRegistry, deck_type: str) -> list[str]:
    """Skład talii ``deck_type`` w grze rejestru: talia modułu albo oficjalna.

    Erraty pojedynczych kart są już w rejestrze (te same id), więc nie zmieniają listy.
    """
    override = next((m for m in registry.variant_modules if deck_type in m.decks), None)
    if override is not None:
        return variant_deck_ids(registry, override, deck_type)
    return official_deck_ids(registry, deck_type)


def explore_deck_ids(registry: StaticDataRegistry, trait: str) -> list[str]:
    """Karty talii eksploracji danej cechy (posortowane) w grze rejestru."""
    cards = registry.catalog.all(ComponentCategory.EXPLORATION)

    def of_trait(card_id: str) -> bool:
        card = cards.get(card_id)
        return isinstance(card, ExplorationDef) and (card.type or "").lower() == trait

    override = next((m for m in registry.variant_modules if EXPLORE in m.decks), None)
    if override is not None:
        return sorted(c for c in variant_deck_ids(registry, override, EXPLORE) if of_trait(c))
    fan = variant_sources()
    return sorted(c for c in cards if of_trait(c) and cards[c].source not in fan)


# --- Widok dla UI -------------------------------------------------------------------------------


def source_badges(mods: Iterable[VariantModule] | None = None) -> dict[str, str]:
    """{źródło: plakietka} dla komponentów modułów (UI)."""
    return {
        m.source: m.badge
        for m in (modules().values() if mods is None else mods)
        if m.badge is not None
    }


def describe(mods: Sequence[VariantModule] | None = None) -> list[dict[str, object]]:
    """Lista modułów do API/generatora frontu."""
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "source": m.source,
            "badge": m.badge,
            "deckTypes": sorted(m.deck_types()),
            "replaces": sorted(c.value for c in m.replaces),
            "adds": sorted(c.value for c in m.adds),
            "default": m.default,
        }
        for m in (modules().values() if mods is None else mods)
    ]


# Typ talii -> klucz talii we froncie (``ActiveDeckKind`` + ``explore``).
UI_DECK_KEYS: Mapping[str, str] = {
    "agenda": "agenda",
    "action_card": "actionCard",
    "relic": "relic",
    "secret_objective": "secretObjective",
    "public_stage_1_objective": "stage1Objective",
    "public_stage_2_objective": "stage2Objective",
    EXPLORE: EXPLORE,
}


def ui_payload(registry: StaticDataRegistry) -> dict[str, object]:
    """Dane dla UI gry z modułami: plakietki, wpisy zmienione/dodane i talie zastąpione w całości.

    ``entries``: {kategoria: {id: surowy wpis}}; ``decks``: {klucz talii frontu: [id kart]}.
    """
    entries: dict[str, dict[str, Mapping[str, object]]] = {}
    for key, entry in sorted(registry.variant_entries.items()):
        category, _, component_id = key.partition(":")
        entries.setdefault(category, {})[component_id] = entry
    decks: dict[str, list[str]] = {}
    for module in registry.variant_modules:
        for deck_type in module.decks:
            decks[UI_DECK_KEYS[deck_type]] = sorted(
                set(variant_deck_ids(registry, module, deck_type))
            )
    return {
        "variants": list(registry.variant_ids),
        "badges": source_badges(registry.variant_modules),
        "entries": entries,
        "decks": decks,
    }
