"""Kontrola planet — JEDYNE miejsce zmiany właściciela planety (poza God-Mode).

RULES.md 43.1a (punkty centralne) i 12 (jedno źródło prawdy): kto kontroluje planetę, mówi
``SystemState.planet_owners``; ``PlayerState.controlled_planets`` to lustro zachowane dla
zgodności i utrzymujemy je w zgodzie TUTAJ. Każda zmiana ``planet_owners`` i
``controlled_planets`` w ``core/`` idzie przez ``set_planet_control`` (wyjątek: God-Mode
w ``core/board_edit.py``, który celowo omija reguły). Hook „gdy zdobywasz/tracisz kontrolę
nad planetą" dopisujemy tu raz.

Źródło reguł: ``docs/rules_tirules/R_control.md`` (planeta ma jednego kontrolera) oraz
RULES.md 21/23. Funkcja jest czystą mutacją przekazanego ``state`` (KLON roboczy wołającego);
nie ocenia legalności zdobycia — to robi wołający (inwazja, karta, eksploracja). Nie rusza
też wyczerpania zdobywanej planety: to decyzja wołającego (``core/exhaust.py``).
"""

from __future__ import annotations

from src.core import exhaust, relics
from src.core.game_state import GameState
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit


def set_planet_control(
    state: GameState,
    position: str,
    planet: str,
    new_owner: str | None,
    registry: StaticDataRegistry | None = None,
) -> None:
    """Ustawia kontrolera planety ``planet`` w systemie ``position`` (``None`` = nikt).

    Dotychczasowy kontroler traci planetę: znika z jego ``controlled_planets`` i przestaje być
    wyczerpana (znacznik wyczerpania należy do kontrolującego). Nowy kontroler dostaje ją
    w ``controlled_planets``. Ten sam kontroler -> brak zmian.

    Kontroler spoza ``state.players`` (np. w testach) jest dopuszczony: zmienia się tylko
    ``planet_owners``, lustro ``controlled_planets`` aktualizujemy dla znanych graczy.

    Planeta The Fracture (pozycja ``frac*``), którą gracz zdobywa BEZ poprzedniego kontrolera,
    daje mu relikt (R_fracture) - hook działa, gdy podano ``registry`` (potrzebny do talii).

    Raises:
        ValueError: Nieznany system.
    """
    system = state.systems.get(position)
    if system is None:
        raise ValueError(f"Unknown system position: {position}")
    previous = system.planet_owners.get(planet)
    if previous == new_owner:
        return
    if new_owner is None:
        del system.planet_owners[planet]
    else:
        system.planet_owners[planet] = new_owner
    if previous is not None and previous in state.players:
        prev_player = state.players[previous]
        prev_player.controlled_planets = [p for p in prev_player.controlled_planets if p != planet]
        exhaust.ready_planets(state, previous, [planet])
    if new_owner is not None and new_owner in state.players:
        new_player = state.players[new_owner]
        if planet not in new_player.controlled_planets:
            new_player.controlled_planets = [*new_player.controlled_planets, planet]
        # HOOK-CANDIDATE (RULES.md 50): relikt za pierwszą kontrolę planety w The Fracture.
        if previous is None and registry is not None and position.startswith("frac"):
            relics.draw_relic(state, registry, new_owner)


def recompute_from_units(state: GameState, position: str, planet: str) -> None:
    """Przelicza kontrolę planety po postawieniu jednostek (reguła AsyncTI4, RULES.md 23).

    Gdy na planecie stoją siły naziemne/struktury DOKŁADNIE JEDNEGO gracza, ten gracz przejmuje
    kontrolę. Brak jednostek albo ≥ 2 graczy (koegzystencja) -> bez zmian: kontrola jest „lepka".
    Statki i inne jednostki kosmiczne nie nadają kontroli.
    """
    system = state.systems.get(position)
    if system is None:
        return
    present = {
        player_id
        for player_id, by_type in system.planet_units.get(planet, {}).items()
        if player_id != NEUTRAL_PLAYER_ID  # neutralni nigdy nie kontrolują planet (RULES.md 50)
        and any(count > 0 and not is_space_unit(base_type) for base_type, count in by_type.items())
    }
    if len(present) == 1:
        set_planet_control(state, position, planet, next(iter(present)))
