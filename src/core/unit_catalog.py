"""Katalog jednostek — jawne tabele reguł (umiejscowienie, kody, asyncId).

Źródło prawdy klasyfikacji jednostek wg docs/RULES.md 2b/2c. Celowo NIE opiera się
na flagach ``isShip``/``isStructure`` z danych AsyncTI4 — są one błędne dla ``mech``
(oznaczony jako statek) i ``warsun`` (oznaczony jako nie-statek). Umiejscowienie
(przestrzeń vs planeta) oraz mapowania kodów trzymamy tutaj, w jawnej tabeli.
"""

from __future__ import annotations

from enum import StrEnum


class Placement(StrEnum):
    """Gdzie fizycznie stoi jednostka w systemie."""

    SPACE = "SPACE"  # statki w przestrzeni systemu
    PLANET = "PLANET"  # siły naziemne i struktury na planecie


# baseType -> umiejscowienie (wg RULES.md 2b, zweryfikowane w LRR/TI Wiki).
PLACEMENT_BY_BASE_TYPE: dict[str, Placement] = {
    "fighter": Placement.SPACE,
    "destroyer": Placement.SPACE,
    "cruiser": Placement.SPACE,
    "carrier": Placement.SPACE,
    "dreadnought": Placement.SPACE,
    "flagship": Placement.SPACE,
    "warsun": Placement.SPACE,
    "infantry": Placement.PLANET,
    "mech": Placement.PLANET,
    "pds": Placement.PLANET,
    "spacedock": Placement.PLANET,
}

# Oficjalne asyncId AsyncTI4 (zgodne z nazwami grafik assets/units/<kolor>_<asyncId>.png).
ASYNC_ID_BY_BASE_TYPE: dict[str, str] = {
    "fighter": "ff",
    "destroyer": "dd",
    "cruiser": "ca",
    "carrier": "cv",
    "dreadnought": "dn",
    "flagship": "fs",
    "warsun": "ws",
    "infantry": "gf",
    "mech": "mf",
    "pds": "pd",
    "spacedock": "sd",
}

# Kody używane w polu startingFleet frakcji (INNY zestaw niż asyncId!) -> baseType.
# Patrz RULES.md 2c. Dane AsyncTI4 są miejscami niespójne: większość frakcji używa
# "cr" dla cruisera, ale Keleres używa "ca" (asyncId cruisera) — akceptujemy oba.
FLEET_CODE_TO_BASE_TYPE: dict[str, str] = {
    "cr": "cruiser",
    "ca": "cruiser",  # alias (Keleres); normalnie "cr"
    "cv": "carrier",
    "dd": "destroyer",
    "dn": "dreadnought",
    "ff": "fighter",
    "fs": "flagship",
    "ws": "warsun",
    "inf": "infantry",
    "mech": "mech",
    "pds": "pds",
    "sd": "spacedock",
}


# Limity sztuk (supply/plastik) per typ jednostki — ile gracz ma w rezerwie.
# ŹRÓDŁO (nie z pamięci): AsyncTI4 bot, plik
# ``TI4_map_generator_bot/src/main/resources/positions/reinforcements.properties``
# — liczba par współrzędnych na danej jednostce = limit sztuk. Monument: 1
# (specjalny przypadek w Player.getUnitCap). Kluczowane przez ``asyncId``.
UNIT_CAP_BY_ASYNC_ID: dict[str, int] = {
    "gf": 12,  # infantry
    "ff": 10,  # fighter
    "mf": 4,  # mech
    "dd": 8,  # destroyer
    "ca": 8,  # cruiser
    "cv": 4,  # carrier
    "dn": 5,  # dreadnought
    "fs": 1,  # flagship
    "ws": 2,  # warsun
    "pd": 6,  # pds
    "sd": 3,  # spacedock
    "monument": 1,
}


def placement_of(base_type: str) -> Placement:
    """Umiejscowienie jednostki (przestrzeń/planeta) dla danego ``baseType``.

    Raises:
        KeyError: Gdy ``baseType`` jest nieznany.
    """
    return PLACEMENT_BY_BASE_TYPE[base_type]


def async_id_of(base_type: str) -> str:
    """Oficjalne ``asyncId`` (do grafik) dla danego ``baseType``.

    Raises:
        KeyError: Gdy ``baseType`` jest nieznany.
    """
    return ASYNC_ID_BY_BASE_TYPE[base_type]


def is_space_unit(base_type: str) -> bool:
    """Czy jednostka stoi w przestrzeni systemu (statek)."""
    return PLACEMENT_BY_BASE_TYPE.get(base_type) is Placement.SPACE
