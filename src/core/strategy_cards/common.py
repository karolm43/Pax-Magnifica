"""Wspólne pomocnicze funkcje kart strategii (żetony dowodzenia, parsowanie payloadu)."""

from __future__ import annotations

from typing import Any

from src.core import command_tokens, exhaust, rules_hooks, unit_ops
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


def board_structure_sources(
    state: GameState, player_id: str, structure: str, target_planet: str
) -> list[str]:
    """Planety, z których gracz może ZDJĄĆ swoją strukturę, by postawić ją gdzie indziej.

    R_component_limitations / R_reinforcements: gdy w rezerwie nie ma jednostki tego typu, gracz
    może zdjąć ją z systemu BEZ swojego żetonu dowodzenia i od razu postawić. Bez planety docelowej.
    Reguła żyje w ``core.board_reinforcements`` (jedno miejsce); tu tylko widok „planety”.
    """
    from src.core import board_reinforcements  # lokalnie: unika cyklu importów

    zones = [
        s.partition("|")[2] for s in board_reinforcements.board_sources(state, player_id, structure)
    ]
    return sorted(z for z in zones if z not in ("space", target_planet))


def structure_board_sources(state: GameState, player_id: str) -> dict[str, list[str]]:
    """Struktura → planety, z których trzeba ją zdjąć, bo rezerwa jest pusta (dla UI na mapie).

    Bez wykluczenia planety docelowej — wołający pomija planetę, na którą stawia.
    """
    return {
        structure: board_structure_sources(state, player_id, structure, "")
        for structure in STRUCTURE_LIMIT_PER_PLANET
        if needs_board_source(state, player_id, structure)
    }


def needs_board_source(state: GameState, player_id: str, structure: str) -> bool:
    """Czy postawienie struktury wymaga zdjęcia jej z planszy (rezerwa pusta)."""
    from src.core import board_reinforcements  # lokalnie: unika cyklu importów

    return board_reinforcements.needs_board_source(state, player_id, structure)


def structure_problem(
    state: GameState,
    player_id: str,
    planet_id: str,
    structure: str,
    *,
    allow_board: bool = False,
) -> str | None:
    """Powód, dla którego nie wolno położyć struktury (None = wolno).

    ``allow_board`` — przy pustej rezerwie wolno wziąć strukturę z planszy
    (``board_structure_sources``); wołający musi wtedy podać źródło w ``place_structure``.
    """
    from src.core import production  # lokalnie: unika cyklu importów przy starcie pakietu

    if structure == MECH_INSTEAD:
        return _mech_instead_problem(state, player_id, planet_id, allow_board=allow_board)
    if structure not in STRUCTURE_LIMIT_PER_PLANET:
        return f"Unknown structure: {structure}."
    position = planet_position(state, planet_id)
    if position is None or state.systems[position].planet_owners.get(planet_id) != player_id:
        return f"You do not control {planet_id}."
    if DMZ_ATTACHMENT in state.planet_attachments.get(planet_id, []):
        return "Structures cannot be placed on a planet with the Demilitarized Zone."
    unlimited = structure == "pds" and rules_hooks.permits(
        rules_hooks.POINT_PDS_UNLIMITED, state, player_id
    )  # Homeland Defense Act (RULES.md 51.6)
    if not unlimited and _structure_count(
        state, player_id, planet_id, structure
    ) >= STRUCTURE_LIMIT_PER_PLANET[structure]:
        return f"{planet_id} already has the maximum number of {structure}."
    left = production.reinforcements_left(state, player_id, structure)
    if left is not None and left <= 0:
        if allow_board and board_structure_sources(state, player_id, structure, planet_id):
            return None
        return f"No {structure} left in your reinforcements."
    return None


# Pseudo-struktura „mech i piechota zamiast PDS” (Hecatoncheires, RULES.md 62.18).
MECH_INSTEAD = "mech"


def _mech_instead_problem(
    state: GameState, player_id: str, planet_id: str, *, allow_board: bool
) -> str | None:
    """Czy wolno postawić 1 mecha i 1 piechotę ZAMIAST PDS (DEPLOY Hecatoncheires).

    F_ul mech: tylko gdy PDS dałoby się postawić (limit 2 na planetę - 3; PDS z rezerwy albo
    zdjęty z planszy - 4) i mech jest w rezerwie (2).
    """
    from src.core import production  # lokalnie: unika cyklu importów przy starcie pakietu

    if not rules_hooks.permits(
        rules_hooks.POINT_STRUCTURE_PDS_AS_MECH, state, player_id, {"planet": planet_id}
    ):
        return "You cannot place a mech instead of a PDS."
    problem = structure_problem(state, player_id, planet_id, "pds", allow_board=allow_board)
    if problem is not None:
        return problem
    mechs = production.reinforcements_left(state, player_id, "mech")
    if mechs is not None and mechs <= 0:
        return "No mech left in your reinforcements."
    return None


def placeable_structures(
    state: GameState, player_id: str, *, allow_board: bool = False
) -> dict[str, list[str]]:
    """Planeta → struktury, które gracz może tam teraz położyć.

    ``allow_board`` — przy pustej rezerwie liczy się też struktura zdjęta z planszy
    (R_component_limitations; źródła: ``structure_board_sources``).
    """
    result: dict[str, list[str]] = {}
    for planet_id in owned_planets(state, player_id):
        options = [
            s for s in (*STRUCTURE_LIMIT_PER_PLANET, MECH_INSTEAD)
            if structure_problem(state, player_id, planet_id, s, allow_board=allow_board) is None
        ]
        if options:
            result[planet_id] = options
    return result


def place_structure(
    state: GameState,
    player_id: str,
    planet_id: str,
    structure: str,
    *,
    source: str | None = None,
) -> None:
    """Kładzie strukturę na planecie gracza (mutuje klon).

    ``source`` — planeta, z której gracz zdejmuje tę strukturę, gdy rezerwa jest pusta
    (R_component_limitations, ``board_structure_sources``).

    Raises:
        ValueError: Z powodem z ``structure_problem`` albo złe źródło.
    """
    problem = structure_problem(
        state, player_id, planet_id, structure, allow_board=source is not None
    )
    if problem is not None:
        raise ValueError(problem)
    if structure == MECH_INSTEAD:
        _place_mech_instead(state, player_id, planet_id, source)
        return
    if needs_board_source(state, player_id, structure):
        if source not in board_structure_sources(state, player_id, structure, planet_id):
            raise ValueError(
                f"No {structure} in your reinforcements - choose one on the board to move "
                "(from a system without your command token)."
            )
        assert source is not None
        source_position = planet_position(state, source)
        assert source_position is not None
        unit_ops.remove_units(
            state, state.systems[source_position], source, player_id, structure, 1,
            UnitCause.REMOVED,
        )
    position = planet_position(state, planet_id)
    assert position is not None
    unit_ops.place_units(
        state, state.systems[position], planet_id, player_id, structure, 1, UnitCause.PLACED
    )


def _place_mech_instead(
    state: GameState, player_id: str, planet_id: str, source: str | None
) -> None:
    """1 mech i 1 piechota zamiast PDS (Hecatoncheires). Przy pustej rezerwie PDS gracz najpierw
    zdejmuje PDS z planszy do rezerwy (F_ul mech 4) - tam zostaje."""
    if needs_board_source(state, player_id, "pds"):
        if source not in board_structure_sources(state, player_id, "pds", planet_id):
            raise ValueError(
                "No PDS in your reinforcements - choose one on the board to return first "
                "(from a system without your command token)."
            )
        assert source is not None
        source_position = planet_position(state, source)
        assert source_position is not None
        unit_ops.remove_units(
            state, state.systems[source_position], source, player_id, "pds", 1, UnitCause.REMOVED
        )
    position = planet_position(state, planet_id)
    assert position is not None
    system = state.systems[position]
    unit_ops.place_units(state, system, planet_id, player_id, "mech", 1, UnitCause.PLACED)
    unit_ops.place_units(state, system, planet_id, player_id, "infantry", 1, UnitCause.PLACED)


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
        # Construction / Warfare: „PRODUCTION ability of 1 of your space docks” (F_ul hel-titan 1).
        producer_types=["spacedock"],
    )
    state.production_used = 0
    state.production_placed = {}
