"""Wspólne pomocnicze funkcje kart strategii (żetony dowodzenia, parsowanie payloadu)."""

from __future__ import annotations

from typing import Any

from src.core import command_tokens, exhaust, unit_ops
from src.core.command_tokens import POOLS
from src.core.game_state import GameState
from src.core.unit_ops import UnitCause


def str_list(payload: dict[str, Any], key: str) -> list[str]:
    """Pobiera z payloadu listę napisów (brak klucza = pusta lista)."""
    raw = payload.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        raise ValueError(f"'{key}' must be a list of strings.")
    return list(raw)


def owned_planets(state: GameState, player_id: str) -> list[str]:
    """Planety kontrolowane przez gracza (z ``planet_owners`` systemów)."""
    return [
        planet_id
        for system in state.systems.values()
        for planet_id, owner in system.planet_owners.items()
        if owner == player_id
    ]


def exhausted_owned_planets(state: GameState, player_id: str) -> list[str]:
    """Planety gracza, które są WYCZERPANE (kandydaci do odnowienia)."""
    exhausted = set(state.players[player_id].exhausted_planets)
    return [p for p in owned_planets(state, player_id) if p in exhausted]


def ready_planets_by_choice(
    state: GameState, player_id: str, chosen: list[str], limit: int
) -> None:
    """Odnawia wskazane planety (mutuje klon): max ``limit``, własne i wyczerpane.

    Raises:
        ValueError: Za dużo planet, duplikat, cudza planeta albo planeta nie wyczerpana.
    """
    if len(chosen) > limit:
        raise ValueError(f"You can ready at most {limit} planet(s).")
    if len(set(chosen)) != len(chosen):
        raise ValueError("The same planet was selected twice.")
    allowed = set(exhausted_owned_planets(state, player_id))
    for planet_id in chosen:
        if planet_id not in allowed:
            raise ValueError(f"Planet {planet_id} is not yours or is not exhausted.")
    exhaust.ready_planets(state, player_id, chosen)


def parse_pools(payload: dict[str, Any]) -> dict[str, int]:
    """Rozkład żetonów po pulach: ``tactical``/``fleet``/``strategic`` (liczby ≥ 0)."""
    result: dict[str, int] = {}
    for pool in POOLS:
        value = payload.get(pool, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"'{pool}' must be a non-negative integer.")
        result[pool] = value
    return result


def gainable_tokens(state: GameState, player_id: str, wanted: int) -> int:
    """Ile żetonów gracz realnie zdobędzie: nie więcej niż ma w rezerwie."""
    return max(0, min(wanted, state.players[player_id].cc_reinf))


def gain_tokens(state: GameState, player_id: str, pools: dict[str, int]) -> None:
    """Dodaje żetony do wybranych pul, zabierając je z rezerwy (mutuje klon)."""
    command_tokens.gain_from_reinforcements(state, player_id, pools)


def check_distribution(pools: dict[str, int], expected: int) -> None:
    """Suma rozkładu musi równać się liczbie zdobywanych żetonów."""
    if sum(pools.values()) != expected:
        raise ValueError(f"Distribute exactly {expected} command token(s) between your pools.")


# --- Struktury (Construction) ----------------------------------------------------------------

# Limity struktur na planetę (R_construction): 1 dok, 2 PDS. Typy struktur z kodu jednostek.
STRUCTURE_LIMIT_PER_PLANET = {"spacedock": 1, "pds": 2}
# Id karty eksploracji Demilitarized Zone: na takiej planecie nie wolno kłaść struktur.
DMZ_ATTACHMENT = "dmz"


def planet_position(state: GameState, planet_id: str) -> str | None:
    """Pozycja systemu, w którym leży planeta (None, gdy nieznana)."""
    for position, system in state.systems.items():
        if planet_id in system.planet_owners:
            return position
    return None


def _structure_count(state: GameState, player_id: str, planet_id: str, structure: str) -> int:
    position = planet_position(state, planet_id)
    if position is None:
        return 0
    by_player = state.systems[position].planet_units.get(planet_id, {})
    return by_player.get(player_id, {}).get(structure, 0)


def structure_problem(
    state: GameState, player_id: str, planet_id: str, structure: str
) -> str | None:
    """Powód, dla którego nie wolno położyć struktury (None = wolno)."""
    from src.core import production  # lokalnie: unika cyklu importów przy starcie pakietu

    if structure not in STRUCTURE_LIMIT_PER_PLANET:
        return f"Unknown structure: {structure}."
    position = planet_position(state, planet_id)
    if position is None or state.systems[position].planet_owners.get(planet_id) != player_id:
        return f"You do not control {planet_id}."
    if DMZ_ATTACHMENT in state.planet_attachments.get(planet_id, []):
        return "Structures cannot be placed on a planet with the Demilitarized Zone."
    if _structure_count(state, player_id, planet_id, structure) >= STRUCTURE_LIMIT_PER_PLANET[
        structure
    ]:
        return f"{planet_id} already has the maximum number of {structure}."
    left = production.reinforcements_left(state, player_id, structure)
    if left is not None and left <= 0:
        # ⚠️ ZAŁOŻENIE: reguła zastępcza (zdjęcie jednostki z systemu bez własnego żetonu)
        # nie jest jeszcze modelowana - gracz musi wybrać inną strukturę.
        return f"No {structure} left in your reinforcements."
    return None


def placeable_structures(state: GameState, player_id: str) -> dict[str, list[str]]:
    """Planeta → struktury, które gracz może tam teraz położyć."""
    result: dict[str, list[str]] = {}
    for planet_id in owned_planets(state, player_id):
        options = [
            s for s in STRUCTURE_LIMIT_PER_PLANET
            if structure_problem(state, player_id, planet_id, s) is None
        ]
        if options:
            result[planet_id] = options
    return result


def place_structure(state: GameState, player_id: str, planet_id: str, structure: str) -> None:
    """Kładzie strukturę na planecie gracza (mutuje klon).

    Raises:
        ValueError: Z powodem z ``structure_problem``.
    """
    problem = structure_problem(state, player_id, planet_id, structure)
    if problem is not None:
        raise ValueError(problem)
    position = planet_position(state, planet_id)
    assert position is not None
    unit_ops.place_units(
        state, state.systems[position], planet_id, player_id, structure, 1, UnitCause.PLACED
    )


# --- Produkcja z karty strategii -------------------------------------------------------------


def start_standalone_production(
    state: GameState, player_id: str, position: str, source: str, zone: str | None = None
) -> None:
    """Otwiera produkcję POZA akcją taktyczną (mutuje klon): zwykłe reguły, system ``position``.

    ``zone`` zawęża do jednego doku (Construction). Licznik produkcji startuje od zera.
    Kończy ją ``production.skip_grant`` („Finish production") - patrz hook w strategic_action.
    """
    from src.core.game_state import ProductionGrant

    state.production_grant = ProductionGrant(
        player_id=player_id,
        position=position,
        standalone=True,
        zone=zone,
        source=source,
    )
    state.production_used = 0
    state.production_placed = {}
