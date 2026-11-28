"""Wejścia decyzji gracza dla ofert (RULES.md 56): opis, wykrycie braku wyboru, walidacja.

Ten sam format opisu co formularz kart akcji (``hooks/action_card_inputs``): ``choice`` (jedna
opcja), ``multi`` (min..max opcji), ``number``. Frontend renderuje je wspólnym polem formularza,
a silnik NIGDY nie wybiera za gracza: jeśli wybór jest realny, powstaje oferta i gracz decyduje.
Auto-rozstrzygnięcie wolno tylko wtedy, gdy każde wejście ma dokładnie jedną legalną odpowiedź.

Moduł jest liściem (bez importów silnika), więc korzystają z niego ``triggers`` i ``hooks``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

Input = dict[str, Any]


def option(
    value: Any,
    label: str,
    option_id: str | None = None,
    meta: dict[str, Any] | None = None,
    ref: tuple[str, str | int] | None = None,
) -> dict[str, Any]:
    """Opcja wejścia: ``id`` unikalne w obrębie wejścia, ``value`` trafia do parametrów hooka.

    ``meta`` = dane strukturalne dla graficznych formularzy (np. Transit Diodes: system, strefa,
    typ i liczba jednostek); silnik ich nie waliduje, UI może je pokazać zamiast etykiety.
    ``ref`` = ``(rodzaj, id)`` komponentu gry, którego dotyczy opcja (``REF_KINDS``): UI pokazuje
    jego pełny tekst i kartę po kliknięciu - gdy ``value`` nie jest gołym id (prefiks, inicjatywa).
    """
    result: dict[str, Any] = {
        "id": str(value) if option_id is None else option_id, "value": value, "label": label
    }
    if meta is not None or ref is not None:
        result["meta"] = with_ref(meta, ref)
    return result


# Rodzaje odnośników zrozumiałe dla UI (``frontend/src/domains/offers/optionRefs.ts``).
REF_KINDS = frozenset({
    "strategy", "relic", "tech", "breakthrough", "agenda", "objective", "actionCard",
    "promissory", "leader", "planet", "explore",
})


def with_ref(meta: dict[str, Any] | None, ref: tuple[str, str | int] | None) -> dict[str, Any]:
    """Kopia ``meta`` z odnośnikiem ``ref`` do komponentu gry (``None`` = bez zmian)."""
    result = dict(meta or {})
    if ref is not None:
        kind, ref_id = ref
        if kind not in REF_KINDS:
            raise ValueError(f"Unknown option ref kind {kind!r}.")
        result["ref"] = {"kind": kind, "id": str(ref_id)}
    return result


def choice(
    key: str,
    label: str,
    options: list[dict[str, Any]],
    hint: str = "",
    *,
    always: bool = False,
    auto: Any = None,
    optional: bool = False,
) -> Input:
    """Wejście „wybierz jedną opcję”.

    ``optional=True`` - pole wolno pominąć (brak klucza w parametrach), np. cel dla 2. jednostki,
    gdy gracz wybrał tylko jedną; efekt sam sprawdza, czy potrzebna wartość jest podana.

    ``always=True`` - gracz widzi decyzję NAWET przy jednej legalnej opcji (efekt obowiązkowy,
    o którym ma wiedzieć, np. trafienie Magen Defense Grid), zamiast cichego zastosowania.
    ``auto`` = wartość opcji „Auto”: WYŁĄCZNIE dla decyzji w walce i przy wydawaniu/płatnościach
    (decyzja użytkownika 2026-11-27; każdy inny wybór - cel na mapie, karta, jednostka, gracz,
    żeton, kolejność, akcja - jest ręczny, bez „Auto”). UI pokazuje przycisk „Auto”, brak
    odpowiedzi (pominięte pole) = ta opcja. Musi być wśród opcji.
    """
    item: Input = {
        "key": key, "kind": "choice", "label": label, "options": options,
        "merge": False, "hint": hint, "always": always,
    }
    if auto is not None and any(o["value"] == auto for o in options):
        item["auto"] = auto
    if optional:
        item["optional"] = True
    return item


def multi(
    key: str, label: str, options: list[dict[str, Any]], minimum: int, maximum: int, hint: str = ""
) -> Input:
    """Wejście „wybierz od ``minimum`` do ``maximum`` opcji”."""
    return {
        "key": key, "kind": "multi", "label": label, "options": options,
        "min": minimum, "max": maximum, "hint": hint,
    }


def number(
    key: str,
    label: str,
    minimum: int,
    maximum: int,
    hint: str = "",
    meta: dict[str, Any] | None = None,
    *,
    auto: int | None = None,
) -> Input:
    """Wejście liczbowe. ``meta = route_meta(...)`` = ile jednostek przenieść z planety na planetę:
    UI zbiera takie wejścia w jeden wybór NA MAPIE (źródło, potem cel), nie listę stepperów.

    ``auto`` = sensowna wartość domyślna - WYŁĄCZNIE dla wydawania (trade goods, płatność) i walki
    (decyzja użytkownika 2026-11-27): UI wstawia ją od razu i pokazuje przycisk „Auto”; brak
    odpowiedzi (pominięte pole) = ta wartość. Bez ``auto`` pole startuje od ``minimum``."""
    item: Input = {"key": key, "kind": "number", "label": label, "min": minimum, "max": maximum,
                   "hint": hint}
    if meta is not None:
        item["meta"] = meta
    if auto is not None:
        item["auto"] = max(minimum, min(maximum, auto))
    return item


def route_meta(source: str, destination: str, base_type: str = "infantry") -> dict[str, Any]:
    """Wejście liczbowe = przeniesienie ``base_type`` z planety ``source`` na ``destination``."""
    return {"from": source, "to": destination, "unit": base_type}


MOVE_SEP = ">"  # wartość opcji ruchu: ``<id jednostki>><cel>``


def unit_moves(
    key: str,
    label: str,
    units: list[dict[str, Any]],
    destinations: list[str],
    hint: str = "",
) -> Input:
    """Ruch jednostek z efektu (bohater, przełom, karta) jako PRZECIĄGANIE NA MAPIE.

    ``units`` = opcje egzemplarzy (``option(id, nazwa, meta=unit_at(..., position=...))``),
    ``destinations`` = systemy, do których wolno je przenieść. Wejście to zwykłe ``multi``
    (walidacja, auto-rozstrzygnięcie bez zmian) z opcjami „jednostka -> cel”; UI
    (``frontend/src/domains/offers/UnitMovesField.tsx``) rysuje je jak ruch taktyczny: gracz
    przeciąga jednostki na świecący system, linia trasy na mapie, −/+ w oknie (decyzja
    użytkownika 2026-11-18: ruch zawsze jak ruch, nigdy sloty „Destination N”).
    Jedna jednostka może trafić tylko do jednego celu - pilnuje tego efekt przy parsowaniu.
    """
    options: list[dict[str, Any]] = []
    for unit in units:
        meta = dict(unit.get("meta") or {})
        source = str(meta.get("position") or "")
        for dest in destinations:
            if dest == source:
                continue
            options.append(option(
                f"{unit['value']}{MOVE_SEP}{dest}", f"{unit['label']} → {dest}",
                meta={**meta, "move": {"unit": str(unit["value"]), "from": source, "to": dest}},
            ))
    hint = hint or "Click a glowing system, choose units, then click the destination (or drag)."
    return multi(key, label, options, 0, len(units), hint)


def split_move(value: str) -> tuple[str, str]:
    """``"<id jednostki>><cel>"`` -> ``(id jednostki, cel)``."""
    unit, sep, dest = str(value).rpartition(MOVE_SEP)
    if not sep or not unit or not dest:
        raise ValueError(f"Invalid move {value!r}.")
    return unit, dest


def research(key: str, label: str, view: dict[str, Any], hint: str = "") -> Input:
    """Wejście „zbadaj technologię”: UI otwiera okno badania (drzewo + płatność) z ``view``
    (``strategy_cards.technology.research_view``). Odpowiedź to słownik ``{tech, skips, planets,
    trade_goods}`` (``tech: None`` = rezygnacja); waliduje ją efekt (``core/research_offer``)."""
    return {"key": key, "kind": "research", "label": label, "research": view, "hint": hint}


def info(
    key: str, label: str, options: list[dict[str, Any]], hint: str = "", *, show: bool = False
) -> Input:
    """Wejście INFORMACYJNE (bez wyboru): UI pokazuje tylko ``label``/``hint``. ``options`` to
    legalne cele dla bramki zagrywalności (pusta lista = komponentu nie da się teraz zagrać),
    np. technologie do zbadania, gdy wybór pada dopiero PO zagraniu (Focused Research).

    ``show=True``: the UI also shows ``options`` as read-only chips (description on click) - the
    cards a player looks at (So Ata, Kyver - RULES.md 62.22)."""
    item: Input = {"key": key, "kind": "info", "label": label, "options": options, "hint": hint}
    if show:
        item["show"] = True
    return item


def needs_player(inputs: list[Input]) -> bool:
    """Czy gracz ma realny wybór (więcej niż jedna legalna odpowiedź w którymkolwiek wejściu)."""
    for item in inputs:
        kind = item.get("kind")
        options = item.get("options", [])
        if kind == "choice" and (len(options) > 1 or (item.get("always") and options)):
            return True
        if kind == "multi" and len(options) > int(item.get("min", 0)):
            return True
        if kind == "research":
            return True
        if kind == "number" and int(item.get("max", 0)) > int(item.get("min", 0)):
            return True
    return False


def single_params(inputs: list[Input]) -> dict[str, Any]:
    """Parametry, gdy NIE ma wyboru (``needs_player`` = False): jedyna legalna odpowiedź."""
    params: dict[str, Any] = {}
    for item in inputs:
        kind = item.get("kind")
        options = item.get("options", [])
        if kind == "choice" and options:
            params[item["key"]] = options[0]["value"]
        elif kind == "multi":
            params[item["key"]] = [o["value"] for o in options[: int(item.get("min", 0))]]
        elif kind == "number":
            params[item["key"]] = int(item.get("auto") or item.get("min") or 0)
    return params


def validate_params(inputs: list[Input], params: Mapping[str, Any]) -> dict[str, Any]:
    """Sprawdza odpowiedź gracza względem legalnych opcji; zwraca oczyszczone parametry.

    Raises:
        ValueError: Brak wartości, wartość spoza opcji, zła liczba wyborów, liczba poza zakresem.
    """
    cleaned: dict[str, Any] = {}
    for item in inputs:
        key = str(item["key"])
        kind = item.get("kind")
        label = str(item.get("label", key))
        if kind == "choice":
            allowed = [o["value"] for o in item.get("options", [])]
            if key not in params and "auto" in item:
                params = {**params, key: item["auto"]}  # pominięte pole = wartość „Auto”
            if key not in params and item.get("optional"):
                continue  # pole opcjonalne pominięte
            if key not in params or params[key] not in allowed:
                raise ValueError(f"Choose a valid option for: {label}.")
            cleaned[key] = params[key]
        elif kind == "multi":
            raw = params.get(key)
            if raw is None and int(item.get("min", 0)) == 0:
                raw = []  # wybór opcjonalny pominięty = pusta lista
            if not isinstance(raw, list):
                raise ValueError(f"Choose the options for: {label}.")
            allowed = [o["value"] for o in item.get("options", [])]
            if any(value not in allowed for value in raw):
                raise ValueError(f"Invalid selection for: {label}.")
            if not int(item.get("min", 0)) <= len(raw) <= int(item.get("max", len(allowed))):
                raise ValueError(f"Wrong number of choices for: {label}.")
            cleaned[key] = raw
        elif kind == "research":
            value = params.get(key)
            if not isinstance(value, dict):
                raise ValueError(f"Choose a technology for: {label}.")
            cleaned[key] = value
        elif kind == "number":
            # Pominięte pole = wartość „Auto” (gdy jest), inaczej minimum - od niego startuje
            # stepper w UI (jak pominięty ``multi`` = pusta lista), to nie jest „Auto”.
            value = params.get(key, item.get("auto", item.get("min", 0)))
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"Enter a number for: {label}.")
            if not int(item.get("min", 0)) <= value <= int(item.get("max", 0)):
                raise ValueError(f"The number for {label} is out of range.")
            cleaned[key] = value
    return cleaned


def has_legal_answer(inputs: list[Input]) -> bool:
    """Czy każde wymagane wejście ma dość opcji, by dało się odpowiedzieć."""
    for item in inputs:
        options = item.get("options")
        if not isinstance(options, list):
            continue
        need = int(item.get("min", 0)) if item.get("kind") == "multi" else 1
        if len(options) < need:
            return False
    return True


# --- Metadane opcji dla graficznych formularzy ------------------------------------------------
#
# Silnik ich nie waliduje; UI rysuje z nich kafelki (sprite jednostki w kolorze gracza, planeta
# z wartością, kość z wynikiem) zamiast samej etykiety tekstowej.


def unit_meta(
    base_type: str, player_id: str, faction: str | None, color: str | None, count: int = 0
) -> dict[str, Any]:
    """Opcja = jednostka gracza (``base_type``), opcjonalnie z liczbą sztuk."""
    meta: dict[str, Any] = {
        "unit": base_type, "player": player_id, "faction": faction or "", "color": color or "",
    }
    if count:
        meta["count"] = count
    return meta


def unit_at(
    state: Any,
    player_id: str,
    base_type: str,
    *,
    position: str | None = None,
    planet: str | None = None,
) -> dict[str, Any]:
    """Opcja = jednostka gracza W MIEJSCU (planeta / system) - ``unit_meta`` + miejsce.

    UI grupuje takie opcje po miejscu (klik w planetę/system na mapie, potem wybór, co tam) i
    zwija jednakowe sztuki w licznik −/+ (``frontend/src/domains/offers/GroupedMapField.tsx``)
    zamiast długiej listy „X on Y #n” (decyzja użytkownika 2026-11-16).
    """
    player = state.players.get(player_id)
    meta = unit_meta(
        base_type, player_id, getattr(player, "faction", None), getattr(player, "color", None)
    )
    if position:
        meta["position"] = position
    if planet:
        meta["planet"] = planet
    return meta


def planet_meta(planet_id: str, value: int, value_kind: str) -> dict[str, Any]:
    """Opcja = planeta do wyczerpania; ``value`` w ``value_kind`` (resources / influence)."""
    return {"planet": planet_id, "value": value, "valueKind": value_kind}


def die_meta(value: int, hits_on: int, base_type: str) -> dict[str, Any]:
    """Opcja = kość rzutu walki: wynik, próg trafienia i rzucająca jednostka."""
    return {"die": value, "hitsOn": hits_on, "unit": base_type}


def payment_planets(
    planets: list[tuple[str, str, int]],
    value_kind: str,
    cost: int,
    *,
    trade_goods_key: str = "trade_goods",
    minimum: int = 0,
    hint: str = "",
) -> Input:
    """Wejście „planety do wyczerpania” jako część płatności ``cost`` (planety + TG).

    ``planets`` = ``[(id, nazwa, wartość)]``. Pole ``payment`` mówi UI, że to płatność: ile
    trzeba zapłacić, czym (resources / influence) i które pole liczbowe to trade goods — UI
    pokazuje wtedy kafelki planet z wartościami, licznik TG i pasek „zapłacono X / Y”.
    """
    options = [
        option(pid, f"{name} ({value})", meta=planet_meta(pid, value, value_kind))
        for pid, name, value in planets
        if value > 0
    ]
    item = multi(
        "planets", "Planets to exhaust", options, minimum, len(options),
        hint or f"Pay {cost} {value_kind} with planets and/or trade goods.",
    )
    item["payment"] = {"cost": cost, "valueKind": value_kind, "tradeGoods": trade_goods_key}
    return item


def as_payment(
    item: Input, ready: Mapping[str, int], value_kind: str, cost: int,
    trade_goods_key: str = "trade_goods",
) -> Input:
    """Oznacza istniejące wejście „planety do wyczerpania” jako płatność (jak ``payment_planets``).

    ``ready`` = wartości gotowych planet (``payment.ready_planet_values``); opcje dostają
    ``planet_meta``, a wejście pole ``payment`` — UI pokazuje widżet płatności z paskiem.
    """
    for opt in item.get("options", []):
        value = ready.get(str(opt.get("value")))
        if value is not None:
            meta = planet_meta(str(opt["value"]), value, value_kind)
            opt["meta"] = {**opt.get("meta", {}), **meta}
    item["payment"] = {"cost": cost, "valueKind": value_kind, "tradeGoods": trade_goods_key}
    return item
