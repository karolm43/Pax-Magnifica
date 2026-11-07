"""Walka — pomoce liczbowe i wykrycie uczestników (czyste funkcje, bez mutacji stanu).

Etap E3. **Decyzja projektowa:** aplikacja NIE rozstrzyga walki (nie rzuca kośćmi,
nie przypisuje trafień) — gracze robią to fizycznie na stole. Ten moduł dostarcza
WYŁĄCZNIE pomoce liczbowe (ile kości rzuca gracz, na ile trafia, oczekiwana liczba
trafień) oraz wykrywa, kto i jakimi jednostkami bierze udział w walce w danym miejscu.
Faktyczne usunięcie zniszczonych jednostek robi operator przez God-Mode (``board_edit``).

Statystyki jednostek czytamy z ``UnitDef`` przez ``StaticDataRegistry`` (zero statystyk
z pamięci). Dobór wariantu jednostki gracza (ulepszony/frakcyjny) wg posiadanych
technologii i frakcji — reguła spisana w ``docs/RULES.md`` 20.

Funkcje są czyste i nie mutują stanu.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.game_state import GameState
from src.core.models import UnitDef
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit


@dataclass(frozen=True)
class UnitCombat:
    """Pomoc liczbowa dla jednego typu jednostki gracza w walce."""

    base_type: str
    unit_id: str  # konkretny wariant (np. "sol_flagship", "cruiser")
    name: str
    count: int
    combat_hits_on: int  # trafia na X+ (rzut kością X lub więcej)
    combat_die_count: int  # ile kości na jednostkę
    # Oczekiwana liczba trafień całej grupy: count * dice * (11 - hitsOn) / 10.
    expected_hits: float


@dataclass(frozen=True)
class PlayerCombat:
    """Siły jednego gracza w walce (lista typów + sumaryczne oczekiwane trafienia)."""

    player_id: str
    units: list[UnitCombat]
    total_dice: int
    expected_hits: float


def resolve_unit_variant(
    registry: StaticDataRegistry,
    faction_id: str | None,
    technologies: list[str],
    base_type: str,
) -> UnitDef | None:
    """Wybiera wariant jednostki gracza dla danego ``base_type`` (RULES.md 20).

    Priorytet (jak w ``web_data._units_owned_for_faction``): frakcyjny-ulepszony >
    frakcyjny-bazowy > generyczny-ulepszony > generyczny-bazowy. Ulepszenie liczy się
    tylko, gdy gracz ma wymaganą technologię (``required_tech_id``). Zwraca ``None``,
    gdy brak jednostki tego ``base_type`` w rejestrze.
    """
    techs = {t.lower() for t in technologies}
    faction = registry.factions.get(faction_id) if faction_id else None
    faction_unit_ids = set(faction.units) if faction is not None else set()

    def has_tech(unit: UnitDef) -> bool:
        req = unit.required_tech_id
        return req is None or req.lower() in techs

    def belongs(unit: UnitDef) -> bool:
        if unit.id in faction_unit_ids:
            return True
        if unit.upgrades_from_unit_id in faction_unit_ids:
            return True
        return unit.faction is not None and unit.faction == faction_id

    best: UnitDef | None = None
    best_rank = -1
    for unit in registry.units.values():
        if unit.base_type != base_type:
            continue
        if not has_tech(unit):
            continue
        is_faction = unit.faction is not None
        if is_faction and not belongs(unit):
            continue  # cudzy wariant frakcyjny
        is_upgrade = unit.upgrades_from_unit_id is not None
        mine = belongs(unit)
        # Ranking: frakcyjny-ulepszony(3) > frakcyjny-bazowy(2) >
        # generyczny-ulepszony(1) > generyczny-bazowy(0).
        rank = 2 * ((2 if mine else 0) + (1 if is_upgrade else 0))
        # Jednostka odblokowana technologią (np. War Sun, ``ws``) wygrywa z
        # placeholderem bez statystyk (``nowarsun``) o tym samym ranku.
        if unit.required_tech_id is not None:
            rank += 1
        if rank > best_rank:
            best_rank = rank
            best = unit
    return best


def _unit_combat(
    registry: StaticDataRegistry,
    faction_id: str | None,
    technologies: list[str],
    base_type: str,
    count: int,
) -> UnitCombat | None:
    """Buduje pomoc liczbową dla grupy jednostek (lub None, gdy nie walczy w space combat).

    Jednostki bez ``combat_hits_on``/``combat_die_count`` (np. PDS, dok — brak wartości
    walki kosmicznej) są pomijane (zwrot None). Space cannon PDS to osobna mechanika.
    """
    unit = resolve_unit_variant(registry, faction_id, technologies, base_type)
    if unit is None:
        return None
    hits_on = unit.combat_hits_on
    dice = unit.combat_die_count
    if hits_on is None or dice is None:
        return None
    expected = count * dice * (11 - hits_on) / 10
    return UnitCombat(
        base_type=base_type,
        unit_id=unit.id,
        name=unit.name,
        count=count,
        combat_hits_on=hits_on,
        combat_die_count=dice,
        expected_hits=round(expected, 2),
    )


def _player_combat(
    registry: StaticDataRegistry,
    state: GameState,
    player_id: str,
    units_by_type: dict[str, int],
) -> PlayerCombat:
    """Buduje ``PlayerCombat`` z liczników jednostek gracza (``{base_type: count}``)."""
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []

    units: list[UnitCombat] = []
    total_dice = 0
    total_expected = 0.0
    for base_type, count in sorted(units_by_type.items()):
        if count <= 0:
            continue
        uc = _unit_combat(registry, faction_id, technologies, base_type, count)
        if uc is None:
            continue
        units.append(uc)
        total_dice += uc.count * uc.combat_die_count
        total_expected += uc.expected_hits
    return PlayerCombat(
        player_id=player_id,
        units=units,
        total_dice=total_dice,
        expected_hits=round(total_expected, 2),
    )


def space_combat_participants(
    registry: StaticDataRegistry, state: GameState, position: str
) -> list[PlayerCombat]:
    """Uczestnicy walki KOSMICZNEJ w systemie: gracze mający statki w przestrzeni.

    Zwraca listę ``PlayerCombat`` (po jednym na gracza obecnego statkami), tylko gdy
    walczących jest ≥2 (inaczej pusta lista — nie ma walki). Uwzględnia wyłącznie
    jednostki kosmiczne (``is_space_unit``); naziemne/struktury pomija.
    """
    system = state.systems.get(position)
    if system is None:
        return []
    result: list[PlayerCombat] = []
    for player_id, by_type in sorted(system.space_units.items()):
        ships = {bt: c for bt, c in by_type.items() if is_space_unit(bt) and c > 0}
        if not ships:
            continue
        result.append(_player_combat(registry, state, player_id, ships))
    if len(result) < 2:
        return []
    return result


def ground_combat_participants(
    registry: StaticDataRegistry, state: GameState, position: str, planet: str
) -> list[PlayerCombat]:
    """Uczestnicy walki NAZIEMNEJ na planecie: gracze mający tam jednostki naziemne.

    Analogicznie do ``space_combat_participants``, ale dla jednostek na planecie
    (piechota, mechy). Zwraca listę tylko gdy walczących ≥2.
    """
    system = state.systems.get(position)
    if system is None:
        return []
    by_player = system.planet_units.get(planet, {})
    result: list[PlayerCombat] = []
    for player_id, by_type in sorted(by_player.items()):
        ground = {bt: c for bt, c in by_type.items() if not is_space_unit(bt) and c > 0}
        if not ground:
            continue
        result.append(_player_combat(registry, state, player_id, ground))
    if len(result) < 2:
        return []
    return result
