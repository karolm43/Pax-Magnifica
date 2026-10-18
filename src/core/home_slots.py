"""Sloty domowe graczy (home systems) na rogach pierścienia 3.

Przy 6 graczach systemy domowe stoją na 6 rogach pierścienia 3 (patrz
docs/RULES.md 2a). W map stringu te pozycje są zwykle ``0`` (puste), bo kafelek
domowy zależy od wybranej frakcji i nie jest częścią losowanej mapy. Zamiast
pomijać te pozycje, renderujemy je jako kolorowe sloty graczy.

⚠️ ZAŁOŻENIE: przypisanie kolorów do rogów to konwencja wyświetlania, nie reguła
TI4 (patrz docs/RULES.md 2a). Do potwierdzenia przez użytkownika.
"""

from __future__ import annotations

# Rogi pierścienia 3 → kolor gracza (układ 6-osobowy, flat-top, góra = 301,
# zgodnie z ruchem wskazówek zegara). Odwzorowuje przykładowy render użytkownika.
HOME_SLOT_COLORS_6P: dict[str, str] = {
    "301": "red",
    "304": "green",
    "307": "white",
    "310": "blue",
    "313": "purple",
    "316": "yellow",
}


def home_slot_color(position: str) -> str | None:
    """Zwraca kolor slotu domowego dla pozycji lub None, gdy to nie róg domowy."""
    return HOME_SLOT_COLORS_6P.get(position)


def is_home_slot(position: str) -> bool:
    """Czy pozycja jest slotem domowym (rogiem pierścienia 3, układ 6-osobowy)."""
    return position in HOME_SLOT_COLORS_6P
