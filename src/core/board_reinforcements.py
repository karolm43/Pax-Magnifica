"""Pusta rezerwa → jednostka zdjęta z planszy: JEDNO miejsce tej reguły (RULES.md 43.1a).

R_component_limitations: „When a player would place a unit, if there are none of that type left
in their reinforcements, that player can remove a unit from any system that does not contain one
of their command tokens and place that unit (…) any units that are removed must be placed
immediately. Abilities cannot force a player to remove and place a unit in this manner.”
Notes: zdjęta jednostka jest stawiana NIEUSZKODZONA; „replace” działa tak samo.

Rulingi, które z tego korzystają: C_agendas (Rearmament Agreement), F_mentak (Salvage Operations,
Sleeper Cell), F_arborec (Letani Ospha, Dirzuga Rophal), F_winnu (Reclamation, Reclaimer),
C_action_cards (Infiltrate). Decyzja zawsze należy do gracza: wołający daje mu wybór źródła
(albo rezygnację), ta funkcja nigdy nie wybiera za niego.

Źródło to napis ``"<pozycja>|<strefa>"`` (strefa = ``space`` albo id planety).
"""

from __future__ import annotations

from typing import Any

from src.core import unit_ops
from src.core.game_state import GameState, SystemState
from src.core.unit_ops import UnitCause


def needs_board_source(state: GameState, player_id: str, base_type: str) -> bool:
    """Czy w rezerwie zabrakło jednostek tego typu (żetony fighter/infantry - nigdy)."""
    from src.core import production  # lokalnie: production importuje unit_ops/ten poziom

    left = production.reinforcements_left(state, player_id, base_type)
    return left is not None and left <= 0


def board_sources(
    state: GameState, player_id: str, base_type: str, *, exclude: str | None = None
) -> list[str]:
    """Miejsca, z których gracz może zdjąć swoją jednostkę ``base_type`` (systemy bez jego żetonu).

    ``exclude`` - źródło pominięte (np. ta sama planeta, na którą jednostka ma trafić).
    """
    found: list[str] = []
    for position in sorted(state.systems):
        system = state.systems[position]
        if player_id in system.command_tokens:
            continue
        zones = ["space", *sorted(system.planet_units)]
        for zone in zones:
            source = f"{position}|{zone}"
            if source != exclude and unit_ops.count_in_zone(system, zone, player_id, base_type):
                found.append(source)
    return found


def can_place(
    state: GameState, player_id: str, base_type: str, *, exclude: str | None = None
) -> bool:
    """Czy gracz w ogóle może postawić 1 jednostkę (z rezerwy albo zdjętą z planszy)."""
    return not needs_board_source(state, player_id, base_type) or bool(
        board_sources(state, player_id, base_type, exclude=exclude)
    )


def take_from_board(state: GameState, player_id: str, base_type: str, source: str) -> None:
    """Zdejmuje 1 jednostkę ze źródła do rezerwy (od razu stawiana przez wołającego).

    Raises:
        ValueError: Źródło nie jest legalne (żeton gracza w systemie albo brak jednostki).
    """
    if source not in board_sources(state, player_id, base_type):
        raise ValueError(
            f"Choose your {base_type} on the board in a system without your command token."
        )
    position, _, zone = source.partition("|")
    system = state.systems[position]
    # Zdejmujemy najpierw NIEUSZKODZONĄ sztukę; postawiona i tak jest nieuszkodzona (Notes).
    unit_ops.remove_units(state, system, zone, player_id, base_type, 1, UnitCause.REMOVED)


def place_unit(
    state: GameState,
    system: SystemState,
    zone: str,
    player_id: str,
    base_type: str,
    *,
    source: str | None = None,
) -> None:
    """Stawia 1 jednostkę: z rezerwy, a gdy pusta - zdjętą ze wskazanego ``source``.

    Raises:
        ValueError: Rezerwa pusta i brak (legalnego) źródła na planszy.
    """
    if needs_board_source(state, player_id, base_type):
        if source is None:
            raise ValueError(
                f"No {base_type} left in your reinforcements - choose one on the board "
                "(in a system without your command token)."
            )
        take_from_board(state, player_id, base_type, source)
    unit_ops.place_units(state, system, zone, player_id, base_type, 1, UnitCause.PLACED)


def source_label(state: GameState, registry: Any, source: str) -> str:
    """Opis źródła do opcji formularza - pełne nazwy z danych („Mecatol Rex (space)”)."""
    position, _, zone = source.partition("|")
    system = state.systems.get(position)
    definition = registry.systems.get(system.system_id) if system is not None else None
    where = (definition.name if definition is not None and definition.name else None) or (
        f"system {system.system_id}" if system is not None else position
    )
    if zone == "space":
        return f"{where} (space)"
    planet = registry.planets.get(zone)
    return planet.name if planet is not None and planet.name else zone


def source_options(
    state: GameState, registry: Any, player_id: str, base_type: str, *,
    exclude: str | None = None,
) -> list[tuple[str, str]]:
    """``(źródło, opis)`` dla formularza wyboru, skąd zdjąć jednostkę."""
    return [
        (s, f"Take from {source_label(state, registry, s)}")
        for s in board_sources(state, player_id, base_type, exclude=exclude)
    ]
