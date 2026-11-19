"""Mapa demonstracyjna — tymczasowy loader planszy do czasu map stringów (Blok 4).

Pełna inicjalizacja mapy z map stringów AsyncTI4 jest zaplanowana na Blok 4.
Do czasu jej powstania frontend potrzebuje *jakiejś* planszy do wyrenderowania.
Ten moduł buduje niewielką, deterministyczną mapę z PRAWDZIWYCH systemów z
``StaticDataRegistry`` (żadnych statystyk ani reguł z pamięci — tylko identyfikatory
systemów i ich dane z assetów), rozmieszczając je na pozycjach AsyncTI4 ``RPP``.

Układ (Mecatol Rex w centrum + pierwszy pierścień) jest wyłącznie poglądowy —
służy do wizualnej weryfikacji renderowania heksów, sąsiedztwa i anomalii.
"""

from __future__ import annotations

from src.core.hex_grid import HexGrid
from src.core.models import SystemDef
from src.core.registry import StaticDataRegistry

# Identyfikator systemu Mecatol Rex w danych AsyncTI4 (centrum każdej mapy).
_MECATOL_SYSTEM_ID = "18"


def _pick_demo_system_ids(registry: StaticDataRegistry) -> list[str]:
    """Wybiera deterministycznie kilka systemów z rejestru na pierwszy pierścień.

    Preferuje systemy z anomaliami (żeby zademonstrować ich render), uzupełniając
    pozostałe miejsca pierwszymi systemami wg porządku identyfikatorów. Dzięki temu
    mapa demonstracyjna pokazuje różnorodność kafelków bez hardkodowania konkretnych
    nazw spoza rejestru.

    Returns:
        Lista 6 identyfikatorów systemów (bez Mecatol Rex), stabilnie uporządkowana.
    """
    all_ids = sorted(sid for sid in registry.systems if sid != _MECATOL_SYSTEM_ID)

    def has_anomaly(sid: str) -> bool:
        # Entropic Scar (RULES.md 1.5) bez wpływu na ruch - nie zmienia stałego układu mapy demo.
        return bool(registry.systems[sid].anomalies - {"ENTROPIC_SCAR"})

    with_anomaly = [sid for sid in all_ids if has_anomaly(sid)]
    without_anomaly = [sid for sid in all_ids if not has_anomaly(sid)]

    # Najpierw kilka anomalii (max 2), potem zwykłe systemy — łącznie 6.
    chosen = with_anomaly[:2] + without_anomaly
    return chosen[:6]


def build_demo_grid(registry: StaticDataRegistry) -> HexGrid:
    """Buduje ``HexGrid`` mapy demonstracyjnej z systemów rejestru.

    Mecatol Rex trafia na pozycję ``000`` (centrum), a wybrane systemy na sześć
    pozycji pierwszego pierścienia (``101``..``106``). Krawędzie (sąsiedztwo +
    wormhole) są budowane na końcu.

    Args:
        registry: Rejestr statycznych danych (źródło identyfikatorów i anomalii).

    Returns:
        Zbudowany graf mapy demonstracyjnej z policzonymi krawędziami.
    """
    grid = HexGrid()

    def place(position: str, system: SystemDef) -> None:
        grid.place_system(
            position=position,
            system_id=system.id,
            wormholes=list(system.wormholes),
            anomalies=set(system.anomalies),
        )

    # Centrum: Mecatol Rex (jeśli obecny w rejestrze), inaczej pierwszy system.
    center_id = (
        _MECATOL_SYSTEM_ID
        if _MECATOL_SYSTEM_ID in registry.systems
        else sorted(registry.systems)[0]
    )
    place("000", registry.systems[center_id])

    # Pierwszy pierścień: pozycje 101..106.
    for offset, sid in enumerate(_pick_demo_system_ids(registry), start=1):
        place(f"10{offset}", registry.systems[sid])

    grid.build_edges()
    return grid
