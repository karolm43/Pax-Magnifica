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


def option(value: Any, label: str, option_id: str | None = None) -> dict[str, Any]:
    """Opcja wejścia: ``id`` unikalne w obrębie wejścia, ``value`` trafia do parametrów hooka."""
    return {"id": str(value) if option_id is None else option_id, "value": value, "label": label}


def choice(
    key: str,
    label: str,
    options: list[dict[str, Any]],
    hint: str = "",
    *,
    always: bool = False,
) -> Input:
    """Wejście „wybierz jedną opcję”.

    ``always=True`` - gracz widzi decyzję NAWET przy jednej legalnej opcji (efekt obowiązkowy,
    o którym ma wiedzieć, np. trafienie Magen Defense Grid), zamiast cichego zastosowania.
    """
    return {
        "key": key, "kind": "choice", "label": label, "options": options,
        "merge": False, "hint": hint, "always": always,
    }


def multi(
    key: str, label: str, options: list[dict[str, Any]], minimum: int, maximum: int, hint: str = ""
) -> Input:
    """Wejście „wybierz od ``minimum`` do ``maximum`` opcji”."""
    return {
        "key": key, "kind": "multi", "label": label, "options": options,
        "min": minimum, "max": maximum, "hint": hint,
    }


def number(key: str, label: str, minimum: int, maximum: int, hint: str = "") -> Input:
    """Wejście liczbowe."""
    return {"key": key, "kind": "number", "label": label, "min": minimum, "max": maximum,
            "hint": hint}


def needs_player(inputs: list[Input]) -> bool:
    """Czy gracz ma realny wybór (więcej niż jedna legalna odpowiedź w którymkolwiek wejściu)."""
    for item in inputs:
        kind = item.get("kind")
        options = item.get("options", [])
        if kind == "choice" and (len(options) > 1 or (item.get("always") and options)):
            return True
        if kind == "multi" and len(options) > int(item.get("min", 0)):
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
            params[item["key"]] = int(item.get("min", 0))
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
            if key not in params or params[key] not in allowed:
                raise ValueError(f"Choose a valid option for: {label}.")
            cleaned[key] = params[key]
        elif kind == "multi":
            raw = params.get(key)
            if not isinstance(raw, list):
                raise ValueError(f"Choose the options for: {label}.")
            allowed = [o["value"] for o in item.get("options", [])]
            if any(value not in allowed for value in raw):
                raise ValueError(f"Invalid selection for: {label}.")
            if not int(item.get("min", 0)) <= len(raw) <= int(item.get("max", len(allowed))):
                raise ValueError(f"Wrong number of choices for: {label}.")
            cleaned[key] = raw
        elif kind == "number":
            value = params.get(key)
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
