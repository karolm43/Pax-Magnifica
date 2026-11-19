"""Schematy DTO warstwy API (Pydantic v2).

Oddzielają kontrakt sieciowy od wewnętrznych modeli domenowych. Mapa jest
serializowana jako lista pozycji ze współrzędnymi kubicznymi (dla renderera SVG)
oraz lista krawędzi sąsiedztwa. God-Mode używa generycznego patcha w tym bloku;
typowane kreatory (wizards) dojdą w kolejnych blokach.

Pakiet: moduły tematyczne (``common``, ``setup``, ``tactical``, ``combat``, ``cards``);
import zawsze przez ``src.api.schemas``.
"""

from src.api.schemas.cards import *  # noqa: F403
from src.api.schemas.combat import *  # noqa: F403
from src.api.schemas.common import *  # noqa: F403
from src.api.schemas.setup import *  # noqa: F403
from src.api.schemas.tactical import *  # noqa: F403
