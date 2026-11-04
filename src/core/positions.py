"""Pozycje planszy AsyncTI4 — źródło prawdy współrzędnych z pliku alias.

Wczytuje ``assets/alias/position_alias.properties`` i buduje mapowanie pozycji
AsyncTI4 (``RPP``, np. ``"101"``) na współrzędne kubiczne ``(q, r, s)``. Plik alias
jest autorytatywnym źródłem AsyncTI4: podaje axial TTPG ``(a, b)`` dla każdej pozycji.

Przeliczenie axial → kubiczne (zweryfikowane, patrz docs/RULES.md 2a):

    q = a
    r = (b - a) / 2
    s = -q - r

W przeciwieństwie do samodzielnego generatora geometrycznego, ta tabela odwzorowuje
dokładną orientację i numerację AsyncTI4 (pozycja ``101`` nad centrum, numeracja
zgodnie z ruchem wskazówek zegara).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from src import config
from src.core.hex_grid import Hex

# Wiersz pliku alias: "<axial_a><axial_b>=<pozycja>", np. "+0+2=101".
_ALIAS_LINE = re.compile(r"^([+-]\d+)([+-]\d+)=(\w+)$")


def _axial_to_hex(a: int, b: int) -> Hex:
    """Przelicza axial TTPG ``(a, b)`` na współrzędną kubiczną."""
    q = a
    r = (b - a) // 2
    return Hex(q, r, -q - r)


def _parse_alias(text: str) -> dict[str, Hex]:
    """Parsuje zawartość ``position_alias.properties`` na mapę pozycja → Hex."""
    result: dict[str, Hex] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _ALIAS_LINE.match(line)
        if match is None:
            continue
        a, b, position = int(match.group(1)), int(match.group(2)), match.group(3)
        if (b - a) % 2 != 0:
            # Niespójny wpis (nie powinno wystąpić dla map heksagonalnych).
            raise ValueError(f"Inconsistent position in alias: {line!r} ((b-a) is odd)")
        result[position] = _axial_to_hex(a, b)
    return result


@lru_cache(maxsize=1)
def load_positions(path: str | Path | None = None) -> dict[str, Hex]:
    """Wczytuje tabelę pozycji AsyncTI4 (pozycja → współrzędna kubiczna).

    Wynik jest cache'owany (plik alias jest statyczny). Przy braku ``path`` używa
    ścieżki z konfiguracji.

    Args:
        path: Opcjonalna ścieżka do pliku alias (dla testów).

    Returns:
        Mapę ``{pozycja: Hex}`` dla wszystkich pozycji z pliku.

    Raises:
        FileNotFoundError: Gdy plik alias nie istnieje.
    """
    alias_path = Path(path) if path is not None else config.POSITION_ALIAS_PATH
    if not alias_path.is_file():
        raise FileNotFoundError(f"Position alias file missing: {alias_path}")
    return _parse_alias(alias_path.read_text(encoding="utf-8"))


def ordered_positions(path: str | Path | None = None) -> list[str]:
    """Zwraca pozycje w kolejności map stringa: pierścień po pierścieniu, rosnąco.

    Kolejność to ``101..106, 201..212, 301..318, ...`` — centrum ``000`` jest
    pomijane (Mecatol jest domyślny i nie występuje w map stringu). Pozycje są
    sortowane numerycznie, co odpowiada numeracji AsyncTI4 (zgodnie z ruchem
    wskazówek zegara wokół każdego pierścienia).
    """
    positions = [pos for pos in load_positions(path) if pos != "000"]
    return sorted(positions, key=int)
