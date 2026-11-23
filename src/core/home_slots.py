"""Sloty domowe graczy (home systems) na rogach pierścienia 3.

Przy 6 graczach systemy domowe stoją na 6 rogach pierścienia 3 (patrz
docs/RULES.md 2a). W map stringu te pozycje są zwykle ``0`` (puste), bo kafelek
domowy zależy od wybranej frakcji i nie jest częścią losowanej mapy. Zamiast
pomijać te pozycje, renderujemy je jako kolorowe sloty graczy.

⚠️ ZAŁOŻENIE: przypisanie kolorów do rogów to konwencja wyświetlania, nie reguła
TI4 (patrz docs/RULES.md 2a). Do potwierdzenia przez użytkownika.
"""

from __future__ import annotations

from src.core.positions import ordered_positions

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


def seating_by_seats(player_ids: list[str], home_positions: dict[str, str]) -> list[str]:
    """Kolejność przy stole wg miejsc: zgodnie z ruchem zegara, od pierwszego gracza.

    Gracz 1 (mówca na start) otwiera kolejkę, dalej siedzą gracze na kolejnych miejscach
    zgodnie z ruchem zegara — jak przy fizycznym stole (docs/RULES.md 24). Pozycje
    porządkuje tabela pozycji AsyncTI4 (pierścień po pierścieniu, zgodnie z zegarem);
    pozycje spoza tabeli zostają na końcu w kolejności graczy.
    """
    if not player_ids:
        return []
    rank = {position: i for i, position in enumerate(ordered_positions())}
    by_seat = sorted(
        player_ids,
        key=lambda pid: (rank.get(home_positions.get(pid, ""), len(rank)), player_ids.index(pid)),
    )
    start = by_seat.index(player_ids[0])
    return by_seat[start:] + by_seat[:start]
