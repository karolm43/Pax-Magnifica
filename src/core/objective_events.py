"""Automatyczne zdobywanie tajnych celów odpalanych ZDARZENIAMI (faza Action / Agenda).

Cele fazy statusu liczy ``objective_progress`` (stan planszy). Pozostałe tajne cele opisują
moment w grze („wygraj walkę w anomalii", „zniszcz ostatnie myśliwce w kroku AFB"...). Te hooki
są wołane z punktów centralnych (koniec walki, ``unit_ops.remove_units``, pas, utrata planety,
wynik agendy) i zdobywają cel od razu, gdy gracz trzyma go w ręce (⚠ ZAŁOŻENIE: cel jest zawsze
ujawniany - nie ma decyzji „nie punktuję"; limit „jeden tajny cel na walkę" nie jest egzekwowany).

Źródło reguł: ``docs/rules_tirules/C_objectives.md``. Funkcje MUTUJĄ przekazany stan (klon).
Pokryte cele: baf, bam, btv, dtd, dtgs, dts, dyp, fwp, mew, pe, sar, ttfd, uf (+ dp w agendzie).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core import rules_hooks
from src.core.components import ComponentCategory, PromissoryNoteDef
from src.core.game_state import (
    AgendaStep,
    CombatStep,
    GameState,
    InvasionPhase,
    TacticalStep,
    WindowType,
)
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.unit_catalog import PLACEMENT_BY_BASE_TYPE, Placement

if TYPE_CHECKING:
    from src.core.game_state import ActiveCombat
    from src.core.hex_grid import HexGrid
    from src.core.registry import StaticDataRegistry

# Cele zdobywane zdarzeniem (fazy Action/Agenda); test pokrycia pilnuje, że żaden cel katalogu
# nie zostaje bez sprawdzania (``objective_progress`` albo ten zbiór).
EVENT_OBJECTIVES = frozenset({
    "baf", "bam", "btv", "dtd", "dtgs", "dts", "dyp", "fwp", "mew", "pe", "sar", "ttfd",
    "uf", "dp",
})

_FIGHTER = "fighter"
_GROUND = ("infantry", "mech")
_BIG_SHIPS = ("warsun", "flagship")
_DYP_SHIPS = 3
_DICTATE_LAWS = 3
_ELECT_PLAYER_KINDS = ("player", "player_techs")
_ELECT_PLANET_KINDS = ("planet", "planet_non_home", "planet_non_home_not_mecatol")


def _registry() -> StaticDataRegistry | None:
    registry: StaticDataRegistry | None = rules_hooks.bound_registry()
    return registry


def score_secret_if_held(state: GameState, player_id: str, objective_id: str) -> bool:
    """Gracz trzyma tajny cel w ręce -> zdobywa go (punkty + wpis do ``auto_scored``)."""
    from src.core import objectives, secret_objectives  # lokalnie: unika cyklu importów

    registry = _registry()
    player = state.players.get(player_id)
    if registry is None or player is None or player_id == NEUTRAL_PLAYER_ID:
        return False
    if objective_id not in player.private.secret_objectives:
        return False
    definition = objectives.objective_def(registry, objective_id)
    if definition is None:
        return False
    secret_objectives.score(state, player_id, objective_id)
    objectives.award_points(state, player_id, definition.points or 1)
    state.auto_scored = [
        *state.auto_scored,
        {"player": player_id, "objective": objective_id, "round": state.round_number},
    ]
    return True


# --- ślad do „betray a friend" ------------------------------------------------------------


def _note_owner(state: GameState, registry: StaticDataRegistry, note_id: str) -> str | None:
    """Właściciel (twórca) notki leżącej w strefie gry: po kolorze w id albo po frakcji."""
    for pid, player in state.players.items():
        if player.color and (note_id.endswith(f"_{player.color}") or note_id == player.color):
            return pid
    card = registry.catalog.get(ComponentCategory.PROMISSORY_NOTE, note_id)
    faction = card.faction if isinstance(card, PromissoryNoteDef) else None
    for pid, player in state.players.items():
        if faction and player.faction == faction:
            return pid
    return None


def snapshot_tactical_start(state: GameState) -> None:
    """Początek akcji taktycznej: czyje notki leżą w strefie gry aktywnego gracza."""
    registry = _registry()
    active = state.players.get(state.active_player_id or "")
    state.tactical_pn_owners = []
    if registry is None or active is None:
        return
    owners = {
        owner
        for note_id in active.promissory_notes_in_play
        if (owner := _note_owner(state, registry, note_id)) is not None
        and owner != active.player_id
    }
    state.tactical_pn_owners = sorted(owners)


# --- walka --------------------------------------------------------------------------------


def _is_ship(base_type: str) -> bool:
    return PLACEMENT_BY_BASE_TYPE.get(base_type) is Placement.SPACE


def _non_fighter_ships(state: GameState, position: str, player_id: str) -> int:
    system = state.systems.get(position)
    if system is None:
        return 0
    return sum(
        n for bt, n in system.space_units.get(player_id, {}).items()
        if n > 0 and bt != _FIGHTER and _is_ship(bt)
    )


def on_combat_end(
    state: GameState, grid: HexGrid | None, combat: ActiveCombat, winner: str | None
) -> None:
    """Koniec walki (zwycięzca albo remis): btv, dts, baf, sar, uf, dyp."""
    sides = [combat.attacker, combat.defender]
    if combat.kind == "space":
        for pid in sides:
            if _non_fighter_ships(state, combat.position, pid) >= _DYP_SHIPS:
                score_secret_if_held(state, pid, "dyp")  # nie trzeba wygrywać
    if winner is None:
        return
    loser = combat.defender if winner == combat.attacker else combat.attacker
    if grid is not None and grid.anomalies_at(combat.position):
        score_secret_if_held(state, winner, "btv")
    homes = {
        pid: p.home_position for pid, p in state.players.items() if p.home_position
    }
    if any(pos == combat.position and pid != winner for pid, pos in homes.items()):
        score_secret_if_held(state, winner, "dts")
    if winner == combat.attacker and loser in state.tactical_pn_owners:
        score_secret_if_held(state, winner, "baf")  # obrońca nie może zdobyć tego celu
    vps = {pid: p.victory_points for pid, p in state.players.items()}
    if loser in vps and vps[loser] == max(vps.values()) and loser != winner:
        score_secret_if_held(state, winner, "sar")
    system = state.systems.get(combat.position)
    if (
        combat.kind == "space"
        and system is not None
        and system.space_units.get(winner, {}).get("flagship", 0) > 0
        and winner not in combat.flagships_destroyed
    ):
        score_secret_if_held(state, winner, "uf")


# --- zniszczenie jednostek ----------------------------------------------------------------


def _killer(state: GameState, owner: str) -> str | None:
    """Kto zniszczył jednostki gracza ``owner`` (kontekst: walka, Space Cannon, bombardowanie)."""
    if state.destroyed_by is not None:
        return state.destroyed_by  # efekt niszczący własne jednostki (np. Crown of Thalnos)
    combat = state.active_combat
    if combat is not None and combat.step is not CombatStep.DONE:
        if owner == combat.attacker:
            return combat.defender
        if owner == combat.defender:
            return combat.attacker
        return None
    window = state.pending_window
    if window is not None and window.window_type is WindowType.SPACE_CANNON:
        roller = window.context.get("roller")
        return str(roller) if roller and roller != owner else None
    invasion = state.invasion
    if invasion is not None and invasion.phase is InvasionPhase.BOMBARDMENT:
        return invasion.attacker if owner != invasion.attacker else None
    return None


def on_unit_destroyed(
    state: GameState, position: str, zone: str, owner: str, base_type: str
) -> None:
    """Po zniszczeniu jednostek (``unit_ops.remove_units``): dtgs, fwp, ttfd, mew (+ ślad uf)."""
    combat = state.active_combat
    if base_type == "flagship" and combat is not None and combat.step is not CombatStep.DONE:
        # Unveil Flagship: zniszczony w walce flagowiec przekreśla cel do końca TEJ walki,
        # nawet jeśli efekt później postawi go z powrotem (C_objectives).
        if owner not in combat.flagships_destroyed:
            combat.flagships_destroyed = [*combat.flagships_destroyed, owner]
    killer = _killer(state, owner)
    if killer is None or killer == owner or owner == NEUTRAL_PLAYER_ID:
        return
    system = state.systems.get(position)
    if system is None:
        return
    if base_type in _BIG_SHIPS:
        score_secret_if_held(state, killer, "dtgs")
    in_afb = combat is not None and (combat.step is CombatStep.AFB or combat.afb_assign)
    left_ships = system.space_units.get(owner, {})
    if base_type == _FIGHTER and in_afb and left_ships.get(_FIGHTER, 0) == 0:
        score_secret_if_held(state, killer, "fwp")
    if (
        _is_ship(base_type)
        and base_type != _FIGHTER
        and state.tactical_step is TacticalStep.SPACE_CANNON
        and state.invasion is None
        and _non_fighter_ships(state, position, owner) == 0
    ):
        score_secret_if_held(state, killer, "ttfd")
    invasion = state.invasion
    if (
        zone != "space"
        and base_type in _GROUND
        and invasion is not None
        and invasion.phase is InvasionPhase.BOMBARDMENT
    ):
        left = system.planet_units.get(zone, {}).get(owner, {})
        if sum(left.get(bt, 0) for bt in _GROUND) == 0:
            score_secret_if_held(state, killer, "mew")


# --- pozostałe zdarzenia ------------------------------------------------------------------


def on_planet_lost(state: GameState, player_id: str, position: str) -> None:
    """Utrata kontroli nad planetą w systemie domowym (czyimkolwiek): bam."""
    if any(p.home_position == position for p in state.players.values()):
        score_secret_if_held(state, player_id, "bam")


def on_last_pass(state: GameState, player_id: str) -> None:
    """Ostatni gracz, który spasował w rundzie: pe."""
    score_secret_if_held(state, player_id, "pe")


def on_agenda_resolving(
    state: GameState, kind: str, outcome: str
) -> None:
    """Tuż przed rozstrzygnięciem wyboru agendy: wybrany gracz albo właściciel planety - dtd."""
    elected: str | None = None
    if kind in _ELECT_PLAYER_KINDS and outcome in state.players:
        elected = outcome
    elif kind in _ELECT_PLANET_KINDS:
        for system in state.systems.values():
            if outcome in system.planet_owners:
                elected = system.planet_owners[outcome]
                break
    if elected is not None:
        score_secret_if_held(state, elected, "dtd")


def on_laws_changed(state: GameState) -> None:
    """Co najmniej 3 prawa w grze (po rozstrzygnięciu trzeciego / na starcie agendy): dp."""
    if len(state.decks.agenda_laws) < _DICTATE_LAWS:
        return
    if state.agenda is not None and state.agenda.step is AgendaStep.COMPLETE:
        return
    for pid in list(state.players):
        score_secret_if_held(state, pid, "dp")
