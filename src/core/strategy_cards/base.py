"""Wspólne typy kart strategii: ``CardSpec`` i sygnatury efektów (RULES.md 30.5).

Każda karta strategii to moduł w tym pakiecie eksportujący ``SPEC`` (+ numer inicjatywy
``INITIATIVE``). ``core/strategic_action.py`` robi dispatch po inicjatywie. Efekty operują
na KLONIE stanu (mutują w miejscu) i rzucają ``ValueError`` przy złamaniu reguły — wtedy
wywołujący odrzuca klon, a stan wejściowy zostaje nietknięty.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@dataclass(frozen=True)
class CardContext:
    """Zależności efektów kart: dane statyczne i (opcjonalnie) siatka mapy.

    Siatka jest potrzebna kartom, które patrzą na geometrię (cele punktowe, produkcja,
    akcja taktyczna); testy czysto-stanowe mogą ją pominąć (``require_grid`` rzuca wtedy
    czytelny błąd tylko tam, gdzie jest faktycznie niezbędna).
    """

    registry: StaticDataRegistry
    grid: HexGrid | None = None

    def require_grid(self) -> HexGrid:
        if self.grid is None:
            raise ValueError("This strategy card effect needs the map grid.")
        return self.grid


# Szkic wyborów primary: dowolne wartości JSON (listy id, napisy, liczby).
Draft = dict[str, Any]
# Efekt primary: (klon_stanu, ctx, owner_id, szkic) -> None.
PrimaryFn = Callable[[GameState, CardContext, str, Draft], None]
# Efekt secondary: (klon_stanu, ctx, respondent_id, payload) -> None.
SecondaryFn = Callable[[GameState, CardContext, str, dict[str, Any]], None]
# Obsługa kroku primary: (klon, ctx, owner_id, krok, szkic, payload) -> None; waliduje
# payload (ValueError przy błędzie) i dopisuje wybór do szkicu.
StepFn = Callable[[GameState, CardContext, str, str, Draft, dict[str, Any]], None]
# Opcje dla UI: (stan, ctx, player_id, krok|None, szkic) -> słownik z dozwolonymi
# wyborami (planety, systemy, limity...). ``krok=None`` = secondary. Funkcja CZYSTA, tylko
# odczyt; informacje prywatne (np. podgląd agendy) zwraca wyłącznie dla ``player_id``.
OptionsFn = Callable[[GameState, CardContext, str, str | None, Draft], dict[str, Any]]


@dataclass(frozen=True)
class CardSpec:
    """Definicja zachowania karty strategii (po numerze inicjatywy).

    Attributes:
        primary_steps: Kolejne kroki wymagające wyboru aktywnego gracza (puste = primary
            stosowane od razu).
        on_step: Walidacja i zapis wyboru dla kroku (wymagane, gdy są kroki).
        primary: Efekt primary stosowany po ostatnim kroku.
        secondary: Efekt secondary respondenta, który „follow".
        secondary_costs_token: Czy follow wydaje 1 żeton ze strategy pool.
        options: Dozwolone wybory dla UI (kroki primary i secondary).
        next_step: Opcjonalny wybór KOLEJNEGO kroku po zapisaniu bieżącego (kroki
            warunkowe); zwraca nazwę kroku albo ``None`` (koniec primary). Brak = liniowo
            wg ``primary_steps``.
    """

    primary_steps: tuple[str, ...] = ()
    on_step: StepFn | None = None
    primary: PrimaryFn | None = None
    secondary: SecondaryFn | None = None
    secondary_costs_token: bool = False
    options: OptionsFn | None = None
    # Pierwszy krok, gdy trzeba go wybrać dynamicznie (np. gdy część kroków jest
    # warunkowa). ``None`` = ``primary_steps[0]``.
    next_step: Callable[[str, Draft], str | None] | None = None
