"""Moduły wariantów gry: fanowskie talie, erraty pojedynczych kart, własne komponenty.

Jedno miejsce prawdy to DANE: ``assets/config/variants.json`` (lista modułów). Kod nie zna
żadnej konkretnej talii fanowskiej - dodanie wariantu = wpis w manifeście (+ ewentualnie
hooki efektów nowych kart). Instrukcja krok po kroku: ``docs/WARIANTY.md``.

Model:

- Moduł ma ``source`` (pole ``source`` kart w plikach ``assets/data/<kategoria>/``).
  Źródło NIE musi być w ``enabled_sources.json``: loader dociąga z niego WYŁĄCZNIE to, czego moduł potrzebuje
  (``load_plan``) - reszta danych źródła (jednostki, technologie…) pozostaje nieaktywna.
- ``decks`` = {typ talii: alias talii}: cała talia tego typu w grze to talia wariantu.
- ``replaces`` = [typ talii]: karty źródła z ``homebrewReplacesID`` podmieniają oficjalne
  karty w talii gry (errata pojedynczej karty; jedna karta może zastąpić kilka kopii -
  np. 3× Shard of the Throne Absol za 1× ``shard``). ``promissory_note`` = podmiana
  wspólnych notek przy rozdawaniu (``game_setup.common_promissory_note_ids``).
- Gra zapisuje wybrane moduły w ``GameState.decks.variants`` (``/game/new``). Starsze gry
  mają tylko ``decks.agenda_variant`` (np. "absol") - ``game_modules`` mapuje je na moduł.

Karta wariantu ma WŁASNE id (np. ``absol_obsidian``), więc jej efekt to osobny hook
(``core/hooks/``, ``covers="relics:absol_obsidian"``); brak hooka = ręczna ewidencja.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from src import config
from src.core.components import ComponentCategory, DeckDef, ExplorationDef
from src.core.sources import AGENDA_STANDARD, source_rank

if TYPE_CHECKING:
    from src.core.registry import StaticDataRegistry

# Pole surowego wpisu: id oficjalnej karty, którą ta karta zastępuje (dane AsyncTI4).
REPLACES_FIELD = "homebrewReplacesID"
PROMISSORY_NOTE = "promissory_note"
EXPLORE = "explore"

# Typ talii (``DeckDef.deck_type`` / klucze manifestu) -> kategoria kart w katalogu.
DECK_TYPE_CATEGORY: Mapping[str, ComponentCategory] = {
    "agenda": ComponentCategory.AGENDA,
    "action_card": ComponentCategory.ACTION_CARD,
    "relic": ComponentCategory.RELIC,
    EXPLORE: ComponentCategory.EXPLORATION,
    "secret_objective": ComponentCategory.SECRET_OBJECTIVE,
    "public_stage_1_objective": ComponentCategory.PUBLIC_OBJECTIVE,
    "public_stage_2_objective": ComponentCategory.PUBLIC_OBJECTIVE,
    PROMISSORY_NOTE: ComponentCategory.PROMISSORY_NOTE,
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
    replaces: frozenset[str] = frozenset()
    default: bool = False

    def deck_types(self) -> frozenset[str]:
        """Typy talii, które moduł zmienia (całą talią albo podmianą kart)."""
        return frozenset(self.decks) | self.replaces


def _parse_module(raw: object, index: int) -> VariantModule:
    if not isinstance(raw, dict):
        raise VariantConfigError(f"Variant module #{index} must be an object.")
    module_id, name, source = raw.get("id"), raw.get("name"), raw.get("source")
    if not all(isinstance(v, str) and v for v in (module_id, name, source)):
        raise VariantConfigError(f"Variant module #{index} needs non-empty id, name and source.")
    assert isinstance(module_id, str) and isinstance(name, str) and isinstance(source, str)
    decks = raw.get("decks") or {}
    replaces = raw.get("replaces") or []
    if not isinstance(decks, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in decks.items()
    ):
        raise VariantConfigError(f"Variant {module_id!r}: 'decks' must map deck type -> alias.")
    if not isinstance(replaces, list) or not all(isinstance(t, str) for t in replaces):
        raise VariantConfigError(f"Variant {module_id!r}: 'replaces' must be a list of types.")
    unknown = sorted({*decks, *replaces} - set(DECK_TYPE_CATEGORY))
    if unknown:
        raise VariantConfigError(f"Variant {module_id!r}: unknown deck types {unknown}.")
    if PROMISSORY_NOTE in decks:
        raise VariantConfigError(
            f"Variant {module_id!r}: promissory notes can only be replaced ('replaces')."
        )
    badge = raw.get("badge")
    return VariantModule(
        id=module_id,
        name=name,
        source=source,
        description=str(raw.get("description") or ""),
        badge=badge if isinstance(badge, str) and badge else None,
        decks=dict(decks),
        replaces=frozenset(replaces),
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
    """Źródła wszystkich modułów - ich talie nie biorą udziału w wyborze talii oficjalnej."""
    return frozenset(m.source for m in (modules().values() if mods is None else mods))


def default_module_ids() -> list[str]:
    """Moduły włączone domyślnie (``"default": true``)."""
    return [m.id for m in modules().values() if m.default]


# --- Plan ładowania (dla component_loader) --------------------------------------------------


@dataclass(frozen=True)
class VariantLoadPlan:
    """Co loader dociąga ze źródeł wariantów spoza ``enabled_sources.json``.

    ``full``: kategoria -> źródła ładowane w całości (karty talii zastępowanej w całości);
    ``replacements``: kategoria -> źródła, z których bierzemy tylko wpisy z
    ``homebrewReplacesID``; ``decks``: źródło -> typy talii, których definicje ładujemy.
    """

    full: Mapping[ComponentCategory, frozenset[str]] = field(default_factory=dict)
    replacements: Mapping[ComponentCategory, frozenset[str]] = field(default_factory=dict)
    decks: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def sources_for(self, category: ComponentCategory) -> frozenset[str]:
        """Wszystkie źródła wariantów, które mają wpisy w danej kategorii."""
        if category is ComponentCategory.DECK:
            return frozenset(self.decks)
        return self.full.get(category, frozenset()) | self.replacements.get(
            category, frozenset()
        )

    def admits(self, category: ComponentCategory, entry: Mapping[str, object]) -> bool:
        """Czy wpis źródła wariantu (spoza manifestu źródeł) ma zostać załadowany."""
        source = entry.get("source")
        if not isinstance(source, str):
            return False
        if category is ComponentCategory.DECK:
            return entry.get("type") in self.decks.get(source, frozenset())
        if source in self.full.get(category, frozenset()):
            return True
        return source in self.replacements.get(category, frozenset()) and isinstance(
            entry.get(REPLACES_FIELD), str
        )


def load_plan(mods: Iterable[VariantModule] | None = None) -> VariantLoadPlan:
    """Plan ładowania wyliczony z modułów (domyślnie: cały manifest)."""
    full: dict[ComponentCategory, set[str]] = {}
    replacements: dict[ComponentCategory, set[str]] = {}
    decks: dict[str, set[str]] = {}
    for module in modules().values() if mods is None else mods:
        for deck_type in module.decks:
            full.setdefault(DECK_TYPE_CATEGORY[deck_type], set()).add(module.source)
            decks.setdefault(module.source, set()).add(deck_type)
        for deck_type in module.replaces:
            replacements.setdefault(DECK_TYPE_CATEGORY[deck_type], set()).add(module.source)
    return VariantLoadPlan(
        full={k: frozenset(v) for k, v in full.items()},
        replacements={k: frozenset(v) for k, v in replacements.items()},
        decks={k: frozenset(v) for k, v in decks.items()},
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


def game_modules(
    variant_ids: Iterable[str], agenda_variant: str = AGENDA_STANDARD
) -> list[VariantModule]:
    """Moduły gry: ``decks.variants`` + zgodność wstecz z ``decks.agenda_variant``.

    Nieznane id (np. moduł usunięty z manifestu po zapisaniu gry) są pomijane.
    """
    known = modules()
    result = [known[i] for i in dict.fromkeys(variant_ids) if i in known]
    legacy = module_for_agenda_variant(agenda_variant)
    if legacy is not None and legacy not in result:
        result.append(legacy)
    return result


# --- Skład talii --------------------------------------------------------------------------------


def official_deck_ids(registry: StaticDataRegistry, deck_type: str) -> list[str]:
    """Karty NAJWIĘKSZEJ talii danego typu z aktywnych źródeł (talie wariantów pominięte).

    Remis rozmiaru rozstrzyga priorytet źródła (RULES.md 14), potem alias - patrz
    ``objectives.deck_card_ids``.
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
    """Karty talii wariantu (``decks[deck_type]``). Brak talii w katalogu -> ``ValueError``."""
    alias = module.decks[deck_type]
    deck = registry.catalog.get(ComponentCategory.DECK, alias)
    if not isinstance(deck, DeckDef) or not deck.card_ids:
        raise VariantConfigError(
            f"Variant {module.id!r}: deck {alias!r} is not available in the catalog."
        )
    return list(deck.card_ids)


def replacement_map(
    registry: StaticDataRegistry, deck_type: str, mods: Iterable[VariantModule]
) -> dict[str, list[str]]:
    """{id oficjalnej karty: [zamienniki]} z modułów, które mają ``deck_type`` w ``replaces``."""
    category = DECK_TYPE_CATEGORY[deck_type]
    sources = {m.source for m in mods if deck_type in m.replaces}
    mapping: dict[str, list[str]] = {}
    if not sources:
        return mapping
    cards = registry.catalog.all(category)
    for card_id in sorted(cards):
        card = cards[card_id]
        replaced = card.raw.get(REPLACES_FIELD)
        if card.source in sources and isinstance(replaced, str) and replaced != card_id:
            mapping.setdefault(replaced, []).append(card_id)
    return mapping


def apply_replacements(card_ids: Iterable[str], mapping: Mapping[str, list[str]]) -> list[str]:
    """Podmienia karty wg ``replacement_map`` (jedna karta może dać kilka zamienników)."""
    result: list[str] = []
    for card_id in card_ids:
        result.extend(mapping.get(card_id, [card_id]))
    return result


def game_deck_ids(
    registry: StaticDataRegistry, deck_type: str, mods: Sequence[VariantModule]
) -> list[str]:
    """Skład talii ``deck_type`` w grze z modułami ``mods`` (cała talia / erraty / oficjalna)."""
    override = next((m for m in mods if deck_type in m.decks), None)
    ids = (
        variant_deck_ids(registry, override, deck_type)
        if override is not None
        else official_deck_ids(registry, deck_type)
    )
    return apply_replacements(ids, replacement_map(registry, deck_type, mods))


def explore_deck_ids(
    registry: StaticDataRegistry, trait: str, mods: Sequence[VariantModule] = ()
) -> list[str]:
    """Karty talii eksploracji danej cechy (posortowane) w grze z modułami ``mods``.

    Eksploracje nie mają jednej talii oficjalnej w katalogu - talia cechy to wszystkie karty
    aktywnych źródeł o tym typie. Moduł z ``decks["explore"]`` zastępuje je kartami swojej
    talii (filtrowanymi po cesze).
    """
    cards = registry.catalog.all(ComponentCategory.EXPLORATION)

    def of_trait(card_id: str) -> bool:
        card = cards.get(card_id)
        return isinstance(card, ExplorationDef) and (card.type or "").lower() == trait

    override = next((m for m in mods if EXPLORE in m.decks), None)
    if override is not None:
        ids = [c for c in variant_deck_ids(registry, override, EXPLORE) if of_trait(c)]
    else:
        fan = variant_sources()
        ids = sorted(c for c in cards if of_trait(c) and cards[c].source not in fan)
    return sorted(apply_replacements(ids, replacement_map(registry, EXPLORE, mods)))


def promissory_replacements(
    registry: StaticDataRegistry, mods: Iterable[VariantModule]
) -> dict[str, str]:
    """{szablon oficjalnej notki: zamiennik} (np. ``<color>_ps`` -> ``absol_<color>_ps``)."""
    return {
        official: found[0]
        for official, found in replacement_map(registry, PROMISSORY_NOTE, mods).items()
    }


def source_badges(mods: Iterable[VariantModule] | None = None) -> dict[str, str]:
    """{źródło: plakietka} dla kart wariantów (UI)."""
    return {
        m.source: m.badge
        for m in (modules().values() if mods is None else mods)
        if m.badge is not None
    }


def describe(mods: Collection[VariantModule] | None = None) -> list[dict[str, object]]:
    """Lista modułów do API/generatora frontu (id, nazwa, opis, źródło, plakietka, typy talii)."""
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "source": m.source,
            "badge": m.badge,
            "deckTypes": sorted(m.deck_types()),
            "default": m.default,
        }
        for m in (modules().values() if mods is None else mods)
    ]


def resolve_new_game(
    registry: StaticDataRegistry,
    variant_ids: Iterable[str] | None,
    agenda_deck: str = AGENDA_STANDARD,
) -> tuple[list[str], str]:
    """Wybór modułów nowej gry -> (``decks.variants``, ``decks.agenda_variant``).

    ``variant_ids=None`` = moduły domyślne z manifestu. ``agenda_deck`` (stare pole API,
    np. "absol") dokłada moduł talii agend tego źródła. Sprawdza, że każda talia modułów
    istnieje w katalogu. Raises: ``VariantConfigError`` (-> HTTP 422).
    """
    ids = list(default_module_ids() if variant_ids is None else variant_ids)
    legacy = module_for_agenda_variant(agenda_deck)
    if legacy is not None:
        ids.append(legacy.id)
    chosen = validate_selection(ids)
    known = modules()
    for module_id in chosen:
        for deck_type in known[module_id].decks:
            variant_deck_ids(registry, known[module_id], deck_type)
    agenda_owner = next((known[i] for i in chosen if "agenda" in known[i].decks), None)
    return chosen, agenda_owner.source if agenda_owner is not None else AGENDA_STANDARD
