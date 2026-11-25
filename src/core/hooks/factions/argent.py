"""The Argent Flight — komplet komponentów frakcji (RULES.md 62.11).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("argent")``, ``units``,
``breakthroughs/te_breakthroughs.json``). Rulingi: ``docs/rules_tirules/F_argent.md`` (krzyżowo
``C_action_cards`` - Bribery / Hack Election, ``C_relics`` - Metali Void Shielding,
``R_diplomacy`` - Helix Protocol). Punkty silnika dodane dla Argent: głos pierwszy
(``agenda.vote_first``), kości AFB i ich skutki (``combat.afb_extra_dice``, ``combat.afb_raid``,
``combat.afb_infantry_kill``), blokada przelotu (``movement.passage_blocked``), PRODUCTION planety
(``production.planet_value``), okna „przed rzutem zdolności jednostki” (Ambuscade).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    battle,
    command_tokens,
    direct_move,
    faction_components,
    leaders,
    promissory_play,
    rules_hooks,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, SystemState
from src.core.hooks.card_helpers import controlled, system_of_planet
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_AGENDA_VOTE_FIRST,
    POINT_AGENDA_VOTE_MODIFIER,
    POINT_BOMBARDMENT_EXTRA_DICE,
    POINT_BOMBARDMENT_GRANTED,
    POINT_COMBAT_AFB_EXTRA_DICE,
    POINT_COMBAT_AFB_INFANTRY_KILL,
    POINT_COMBAT_AFB_RAID,
    POINT_MOVEMENT_PASSAGE_BLOCKED,
    POINT_PRODUCTION_PLANET_VALUE,
    POINT_SPACE_CANNON_EXTRA_DICE,
    POINT_SPACE_CANNON_GRANTED,
    POINT_SPACE_CANNON_OFFENSE_IMMUNE,
    SOURCE_BREAKTHROUGH,
    SOURCE_EFFECT,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_TECHNOLOGY,
    SOURCE_UNIT,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.state_grid import grid_from_state
from src.core.unit_catalog import is_space_unit

FACTION = "argent"
AGENT = "argentagent"
COMMANDER = "argentcommander"
HERO = "argenthero"
FLAGSHIP = "argent_flagship"
MECH = "argent_mech"
AMBUSCADE = "ambuscade"
HOLOLATTICE = "ah"
STRIKE_WING = "swa2"
BREAKTHROUGH = "argentbt"

ZEAL = "zeal"
RAID_FORMATION = battle.AFB_RAID  # „raid_formation” - id zdolności w danych
AGENT_PLACE = "trilossa_place"  # decyzja gracza produkującego (agent Argent)
AMBUSCADE_DIE = f"promissory_notes:{AMBUSCADE}:die"  # efekt: +1 kość przy najbliższym rzucie
WING_TRANSFER = f"breakthroughs:{BREAKTHROUGH}:transfer"  # efekt: akcja z Wing Transfer
_STRUCTURES = ("pds", "spacedock")
_GROUND_FORCES = ("infantry", "mech")
_SWA_KILL_FROM = 9  # „each result of 9 or 10”
_COMMANDER_UNITS = 6  # „Have 6 units that have ANTI-FIGHTER BARRAGE, SPACE CANNON, or BOMBARDMENT”
_SPACE = "space"
_NO_ENTRY = ("SUPERNOVA",)  # Helix Protocol: nie do supernowej (mgławica OK - R_nebula notes/2)
_ASTEROID = "ASTEROID_FIELD"
_ANTIMASS = "amd"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _has_structure(state: GameState, player_id: str, system: SystemState | None) -> bool:
    if system is None:
        return False
    return any(
        by_player.get(player_id, {}).get(bt, 0) > 0
        for by_player in system.planet_units.values()
        for bt in _STRUCTURES
    )


def _only_mine(system: SystemState | None, player_id: str) -> bool:
    """System zawiera jednostki TYLKO gracza (co najmniej jedną)."""
    if system is None:
        return False
    owners = {o for o, units in system.space_units.items() if any(n > 0 for n in units.values())}
    owners |= {
        o for by_player in system.planet_units.values()
        for o, units in by_player.items() if any(n > 0 for n in units.values())
    }
    return owners == {player_id}


# ------------------------------------------------------------------------------------- Zeal


@register(POINT_AGENDA_VOTE_FIRST, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers=f"abilities:{ZEAL}")
def zeal_first(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Zeal: You always vote first during the agenda phase (także jako mówca - F_argent)."""
    return True


@register(POINT_AGENDA_VOTE_MODIFIER, HookSource(SOURCE_FACTION, FACTION), HookKind.MODIFY,
          covers=f"abilities:{ZEAL}")
def zeal_votes(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    """Zeal: When you cast at least 1 vote: cast 1 additional vote for each player in the game
    including you. Bez własnych głosów (wstrzymanie) - nic (F_argent); dodatkowe głosy idą na ten
    sam wynik (``agenda_phase.cast_vote`` liczy je w jednym głosie)."""
    return len(state.players) if int(ctx.get("base_votes") or 0) > 0 else 0


# ---------------------------------------------------------------------------- Raid Formation


@register(POINT_COMBAT_AFB_RAID, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers=f"abilities:{RAID_FORMATION}")
def raid_formation(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Raid Formation: When 1 or more of your units uses ANTI-FIGHTER BARRAGE: for each hit
    produced in excess of your opponent's fighters, choose 1 of your opponent's ships that has
    SUSTAIN DAMAGE to become damaged (rozstrzyganie: ``battle._raid_formation``)."""
    return True


def _raid_entry(state: GameState, player_id: str) -> dict[str, Any] | None:
    combat = state.active_combat
    if combat is None:
        return None
    return next(
        (e for e in combat.effects
         if e.get("kind") == RAID_FORMATION and e.get("player") == player_id and e.get("pending")),
        None,
    )


def raid_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Statki przeciwnika z Sustain Damage - każdy egzemplarz osobno (uszkodzony też, F_argent)."""
    entry = _raid_entry(state, player_id)
    combat = state.active_combat
    if entry is None or combat is None:
        return []
    victim = str(entry["target"])
    grid = grid_from_state(state, registry)
    fresh, hurt = battle.raid_targets(state, grid, registry, victim)
    options: list[dict[str, Any]] = []
    for pool, damaged in ((fresh, False), (hurt, True)):
        for bt, n in sorted(pool.items()):
            name = unit_name(state, registry, victim, bt)
            for i in range(n):
                meta = oi.unit_at(state, victim, bt, position=combat.position)
                meta["damaged"] = damaged
                value = f"{bt}:damaged#{i}" if damaged else f"{bt}#{i}"
                options.append(oi.option(value, f"{name} (damaged)" if damaged else name,
                                         meta=meta))
    count = int(entry["count"])
    return [oi.multi("ships", f"Choose {count} ship(s) to become damaged", options, count, count)]


def _raid_decides(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and _raid_entry(state, player_id) is not None


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": RAID_FORMATION}, decide=True, condition=_raid_decides,
    inputs=raid_inputs, covers=f"abilities:{RAID_FORMATION}",
    label="Raid Formation: damage ships",
)
def raid_formation_choice(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Argent wybiera statki do uszkodzenia (wybrany uszkodzony statek - bez skutku, F_argent)."""
    entry = _raid_entry(state, player_id)
    if entry is None:
        return
    victim = str(entry["target"])
    chosen = [str(v) for v in ctx.get("params", {}).get("ships") or []]
    if len(chosen) != int(entry["count"]):
        raise ValueError(f"Choose exactly {entry['count']} ship(s).")
    grid = grid_from_state(state, _registry())
    fresh, _hurt = battle.raid_targets(state, grid, _registry(), victim)
    damage: dict[str, int] = {}
    for value in chosen:
        base_type = value.split("#", 1)[0]
        if base_type.endswith(":damaged"):
            continue  # F_argent: wybrany uszkodzony statek - bez efektu
        damage[base_type] = damage.get(base_type, 0) + 1
    if any(n > fresh.get(bt, 0) for bt, n in damage.items()):
        raise ValueError("Choose only your opponent's ships that have SUSTAIN DAMAGE.")
    battle.raid_damage(state, victim, damage)
    entry["pending"] = False
    entry["damaged"] = damage
    ability_notes.note(state, player_id, f"abilities:{RAID_FORMATION}",
                       f"{sum(damage.values())} ship(s) damaged")


# ---------------------------------------------------------------- Aerie Hololattice (tech)


@register(POINT_MOVEMENT_PASSAGE_BLOCKED, HookSource(SOURCE_TECHNOLOGY, HOLOLATTICE),
          HookKind.PERMIT, covers=f"technologies:{HOLOLATTICE}")
def hololattice_blocks(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Aerie Hololattice: Other players cannot move ships through systems that contain your
    structures (także z Light/Wave Deflector - F_argent)."""
    if ctx.get("mover") == player_id:
        return False
    return _has_structure(state, player_id, state.systems.get(str(ctx.get("position"))))


@register(POINT_PRODUCTION_PLANET_VALUE, HookSource(SOURCE_TECHNOLOGY, HOLOLATTICE),
          HookKind.MODIFY, covers=f"technologies:{HOLOLATTICE}")
def hololattice_production(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Aerie Hololattice: Each planet that contains 1 or more of your structures gains the
    PRODUCTION 1 ability as if it were a unit (siły naziemne na tej planecie - F_argent)."""
    system = state.systems.get(str(ctx.get("position")))
    planet = str(ctx.get("planet"))
    units = system.planet_units.get(planet, {}).get(player_id, {}) if system else {}
    return 1 if any(units.get(bt, 0) > 0 for bt in _STRUCTURES) else 0


# ------------------------------------------------------------- Strike Wing Alpha II (tech)


@register(POINT_COMBAT_AFB_INFANTRY_KILL, HookSource(SOURCE_TECHNOLOGY, STRIKE_WING),
          HookKind.FORBID, covers=f"technologies:{STRIKE_WING}")
def strike_wing_infantry(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Strike Wing Alpha II: When this unit uses ANTI-FIGHTER BARRAGE, each result of 9 or 10 also
    destroys 1 of your opponent's infantry in the space area of the active system.

    Liczby (koszt, walka, ruch, AFB 6x3) z danych wariantu ``argent_destroyer2``."""
    return {f"destroyer:{_SWA_KILL_FROM}"}


# Wariant jednostki ``argent_destroyer2`` (ten sam tekst zdolności) działa przez hook wyżej - gracz
# ma go tylko z technologią ``swa2``.
rules_hooks.declare_core_rule("units:argent_destroyer2")


# ------------------------------------------------------------------- Quetzecoatl (flagowiec)


@register(POINT_SPACE_CANNON_OFFENSE_IMMUNE, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.PERMIT,
          covers=f"units:{FLAGSHIP}")
def quetzecoatl(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Quetzecoatl: Other players cannot use space cannon against your ships in this system.

    Space Cannon Offense celuje tylko w statki aktywnego systemu; Space Cannon Defense przeciw
    siłom naziemnym Argent nadal wolno (F_argent)."""
    system = state.systems.get(state.active_system or "")
    return bool(system and system.space_units.get(player_id, {}).get("flagship", 0) > 0)


# Aerie Sentinel: capacityUsed 0 w danych; silnik liczy 1, gdy w przestrzeni nie ma statku gracza
# z pojemnością (``capacity.capacity_report``), a transport wymaga statku z pojemnością (movement).
rules_hooks.declare_data_driven(f"units:{MECH}")


# ------------------------------------------------------------- Trilossa Aun Mirik (agent)


def _produced_ground(ctx: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    """Siły naziemne z tego zamówienia na PLANETACH: ``{planeta: {typ: n}}``."""
    zones = ctx.get("zones") or {}
    return {
        str(zone): {bt: int(n) for bt, n in by_type.items() if bt in _GROUND_FORCES and n > 0}
        for zone, by_type in zones.items()
        if zone != _SPACE and any(bt in _GROUND_FORCES and n > 0 for bt, n in by_type.items())
    }


def _agent_destinations(state: GameState, producer: str, position: str) -> list[str]:
    """Planety producenta w systemie produkcji i w systemach sąsiednich."""
    grid = grid_from_state(state, _registry())
    allowed = {position, *grid.neighbors(position)}
    return [
        planet for planet in controlled(state, producer)
        if system_of_planet(state, planet).position in allowed
    ]


def _agent_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    producer = str(ctx.get("player") or "")
    return (
        producer in state.players
        and bool(_produced_ground(ctx))
        and len(_agent_destinations(state, producer, str(ctx.get("position")))) > 1
        and leaders.is_ready(state, _registry(), player_id, AGENT)
    )


@on_event(
    GameEvent.UNITS_PRODUCED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_agent_ready, covers=f"leaders:{AGENT}",
    label="Trilossa Aun Mirik: place ground forces",
)
def trilossa_aun_mirik(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Trilossa Aun Mirik: When a player produces ground forces in a system: You may exhaust this
    card; that player may place those units on any planets they control in that system and any
    adjacent systems. Rozmieszcza gracz produkujący (osobna decyzja)."""
    producer = str(ctx.get("player") or "")
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT,
                                {"target": producer})
    effect = active_effects.add_effect(state, f"leaders:{AGENT}:place", Duration.TURN,
                                       owner=producer)
    effect.data = {"position": str(ctx.get("position")), "units": _produced_ground(ctx)}
    faction_components.ability_used(state, player_id, AGENT_PLACE, producer)


def _placement(state: GameState, producer: str) -> Any:
    return next(
        (e for e in state.active_effects
         if e.key == f"leaders:{AGENT}:place" and e.owner == producer),
        None,
    )


def agent_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Przeniesienia wyprodukowanych sił naziemnych planeta -> planeta (wybór na mapie)."""
    effect = _placement(state, decider)
    if effect is None:
        return []
    dests = _agent_destinations(state, decider, str(effect.data["position"]))
    inputs: list[dict[str, Any]] = []
    for source, by_type in sorted(effect.data["units"].items()):
        for bt, n in sorted(by_type.items()):
            for dest in dests:
                if dest != source:
                    inputs.append(oi.number(
                        f"{source}|{dest}|{bt}", f"{bt} to {dest}", 0, int(n),
                        meta=oi.route_meta(source, dest, bt),
                    ))
    return inputs


def _producer_decides(_state: GameState, _owner: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    where={"ability": AGENT_PLACE}, decide=True, decider=_producer_decides,
    inputs=agent_inputs, label="Trilossa Aun Mirik: place your ground forces",
)
def trilossa_place(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Gracz produkujący przenosi wyprodukowane siły naziemne na swoje planety (0 = zostają)."""
    if ctx.get("player") != player_id:
        return
    producer = str(ctx["target"])
    effect = _placement(state, producer)
    if effect is None:
        return
    dests = set(_agent_destinations(state, producer, str(effect.data["position"])))
    sent: dict[tuple[str, str], int] = {}
    moves: list[tuple[str, str, str, int]] = []
    for key, raw in (ctx.get("params") or {}).items():
        count = int(raw or 0)
        if count <= 0:
            continue
        source, dest, bt = str(key).split("|")
        if dest not in dests or bt not in effect.data["units"].get(source, {}):
            raise ValueError("Place the units only on planets you control in that system or "
                             "adjacent systems.")
        sent[(source, bt)] = sent.get((source, bt), 0) + count
        moves.append((source, dest, bt, count))
    for (source, bt), count in sent.items():
        if count > int(effect.data["units"][source][bt]):
            raise ValueError("You can place only the units you just produced.")
    for source, dest, bt, count in moves:
        unit_ops.transfer_units(
            state, system_of_planet(state, source), source, system_of_planet(state, dest), dest,
            producer, bt, count,
        )
    if moves:
        ability_notes.note(state, producer, f"leaders:{AGENT}",
                           f"placed {sum(m[3] for m in moves)} ground force(s)")
    active_effects.remove_effect(state, effect.id)


# --------------------------------------------------------- Trrakan Aun Zulok (commander)


def _ability_units(state: GameState, registry: StaticDataRegistry, player_id: str) -> int:
    """Jednostki gracza na planszy z AFB, SPACE CANNON albo BOMBARDMENT (także nadanymi:
    Blitz - F_argent; Experimental Battlestation tylko UŻYWA zdolności - nie liczy się)."""
    player = state.players[player_id]
    granted_bombard = bool(rules_hooks.forbidden(POINT_BOMBARDMENT_GRANTED, state, player_id))
    granted_cannon = {
        g.split(":", 1)[0] for g in rules_hooks.forbidden(POINT_SPACE_CANNON_GRANTED, state,
                                                          player_id)
    }
    total = 0
    for position, system in state.systems.items():
        zones = [system.space_units.get(player_id, {})]
        zones += [by_player.get(player_id, {}) for by_player in system.planet_units.values()]
        for units in zones:
            for bt, n in units.items():
                if n <= 0:
                    continue
                unit = resolve_unit_variant(registry, player.faction, player.technologies, bt)
                if unit is None:
                    continue
                has = bool(
                    unit.afb_hits_on
                    or unit.space_cannon_hits_on
                    or (unit.bombard_hits_on or 0) > 0
                    or bt in granted_cannon
                    or (
                        granted_bombard
                        and position == state.active_system
                        and is_space_unit(bt)
                        and bt != "fighter"
                    )
                )
                total += n if has else 0
    return total


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 6 units that have ANTI-FIGHTER BARRAGE, SPACE CANNON, or BOMBARDMENT on the
    game board („Combat” to atrybut, nie zdolność - F_argent)."""
    return _ability_units(state, registry, player_id) >= _COMMANDER_UNITS


def _one_more_die(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    return 1


for _point in (POINT_SPACE_CANNON_EXTRA_DICE, POINT_BOMBARDMENT_EXTRA_DICE,
               POINT_COMBAT_AFB_EXTRA_DICE):
    # Trrakan Aun Zulok: When 1 or more of your units make a roll for a unit ability: You may
    # choose 1 of those units to roll 1 additional die. Tylko AFB, Space Cannon, Bombardment -
    # nie rzuty walki (F_argent). Kość dostaje grupa wskazana przez gracza (Space Cannon,
    # Bombardment) albo najcelniejsza grupa AFB (``battle._afb_bonus_unit``).
    register(_point, HookSource(SOURCE_LEADER, COMMANDER), HookKind.MODIFY,
             covers=f"leaders:{COMMANDER}")(_one_more_die)
    # Strike Wing Ambuscade (zagrana notka): ta sama premia przy najbliższym rzucie posiadacza.
    register(_point, HookSource(SOURCE_EFFECT, AMBUSCADE_DIE), HookKind.MODIFY)(_one_more_die)


# ---------------------------------------------------------- Strike Wing Ambuscade (notka)


@promissory_play.condition(AMBUSCADE)
def _ambuscade_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> str | None:
    if window.subject != player_id:
        return "Strike Wing Ambuscade is played when your units make a roll for a unit ability."
    if active_effects.has_effect(state, player_id, AMBUSCADE_DIE):
        return "Strike Wing Ambuscade is already in effect for this roll."
    return None


@register_effect(f"promissory_notes:{AMBUSCADE}")
def strike_wing_ambuscade(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Strike Wing Ambuscade: When 1 or more of your units make a roll for a unit ability: Choose
    1 of those units to roll 1 additional die. Then, return this card to the Argent player
    (zwrot - ``promissory_play``). Premia czeka na najbliższy rzut AFB / Space Cannon /
    Bombardment posiadacza (w tej akcji taktycznej)."""
    active_effects.add_effect(state, AMBUSCADE_DIE, Duration.TACTICAL_ACTION, owner=player_id)


def _rolled(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


@on_event(GameEvent.UNIT_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_EFFECT, AMBUSCADE_DIE),
          condition=_rolled, label="Strike Wing Ambuscade: used")
def ambuscade_spent(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Po rzucie zdolności jednostki premia z notki przepada (jedna kość, jeden rzut)."""
    for effect in list(state.active_effects):
        if effect.key == AMBUSCADE_DIE and effect.owner == player_id:
            active_effects.remove_effect(state, effect.id)


# ------------------------------------------------- Mirik Aun Sissiri — Helix Protocol (hero)


def helix_destinations(state: GameState, player_id: str) -> list[str]:
    """Systemy z żetonem Argent i bez cudzych statków; nie mgławica / supernowa, pole asteroid
    tylko z Antimass Deflectors (F_argent). Żeton Diplomacy liczy się jak żeton (R_diplomacy)."""
    grid = grid_from_state(state, _registry())
    has_antimass = _ANTIMASS in state.players[player_id].technologies
    found: list[str] = []
    for position, system in sorted(state.systems.items()):
        if player_id not in system.command_tokens:
            continue
        if any(o != player_id and any(n > 0 and is_space_unit(bt) for bt, n in u.items())
               for o, u in system.space_units.items()):
            continue
        anomalies = grid.anomalies_at(position)
        if any(a in anomalies for a in _NO_ENTRY):
            continue
        if _ASTEROID in anomalies and not has_antimass:
            continue
        found.append(position)
    return found


def _own_space(state: GameState, player_id: str) -> list[str]:
    return sorted(
        pos for pos, system in state.systems.items()
        if any(n > 0 for n in system.space_units.get(player_id, {}).values())
    )


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    return direct_move.move_inputs(state, registry, player_id, _own_space(state, player_id),
                        helix_destinations(state, player_id))


@register_effect(f"leaders:{HERO}")
def helix_protocol(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Mirik Aun Sissiri — Helix Protocol: ACTION: Move any number of your ships from any systems
    to any number of other systems that contain 1 of your command tokens and no other players'
    ships. Then, purge this card.

    F_argent: ruch prosto do celu (bez trasy), także z systemów z żetonem Argent; myśliwce bez
    transportu; siły naziemne tylko ze statkami z tego samego systemu - także z systemu z żetonem
    Argent (ruling użytkownika 2026-11-18: ruch zdolnością bohatera, F_argent helix/3.2); rzut
    szczeliny przy wyjściu; Wormhole Nexus odwraca się sam (``step_settle``)."""
    dests = helix_destinations(state, player_id)
    moves = direct_move.parse_moves(params)
    if not moves:
        raise ValueError("Move at least 1 ship.")
    if any(d not in dests for d in moves):
        raise ValueError("Ships can move only to systems with your command token and no other "
                         "players' ships.")
    direct_move.apply_moves(state, registry, player_id, moves, fighters_free=True)


# --------------------------------------------------------------- Wing Transfer (przełom)


def _token_targets(state: GameState, player_id: str, position: str) -> list[str]:
    grid = grid_from_state(state, _registry())
    return sorted(
        pos for pos in grid.neighbors(position)
        if _only_mine(state.systems.get(pos), player_id)
        and player_id not in state.systems[pos].command_tokens
    )


def _transfer_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    position = str(ctx.get("position") or "")
    return (
        ctx.get("player") == player_id
        and _only_mine(state.systems.get(position), player_id)
        and command_tokens.reinforcements(state, player_id) > 0
        and bool(_token_targets(state, player_id, position))
    )


def transfer_token_inputs(
    state: GameState, _registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    targets = _token_targets(state, player_id, str(ctx.get("position") or ""))
    most = min(len(targets), command_tokens.reinforcements(state, player_id))
    options = [oi.option(pos, f"System {pos}", meta={"position": pos}) for pos in targets]
    return [oi.multi("systems", "Place command tokens in", options, 1, most)]


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    optional=True, condition=_transfer_ready, inputs=transfer_token_inputs,
    covers=f"breakthroughs:{BREAKTHROUGH}", label="Wing Transfer: place command tokens",
)
def wing_transfer_tokens(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Wing Transfer: When you activate a system that contains only your units, you may place
    command tokens from your reinforcements into any systems adjacent to that system that contain
    only your units; …"""
    position = str(ctx.get("position") or "")
    allowed = set(_token_targets(state, player_id, position))
    chosen = [str(v) for v in ctx.get("params", {}).get("systems") or []]
    if not chosen or any(c not in allowed for c in chosen):
        raise ValueError("Choose adjacent systems that contain only your units.")
    for pos in chosen:
        command_tokens.place_on_board_from_reinforcements(state, state.systems[pos], player_id)
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                       f"placed {len(chosen)} command token(s)")
    effect = active_effects.add_effect(state, WING_TRANSFER, Duration.TACTICAL_ACTION,
                                       owner=player_id)
    effect.data = {"position": position}


def _transfer_systems(state: GameState, player_id: str, position: str) -> list[str]:
    grid = grid_from_state(state, _registry())
    return [position] + sorted(
        pos for pos in grid.neighbors(position)
        if pos in state.systems and player_id in state.systems[pos].command_tokens
        and not _has_foreign_ships(state, player_id, pos)  # F_argent Wing Transfer 1
    )


def _has_foreign_ships(state: GameState, player_id: str, position: str) -> bool:
    return any(
        owner != player_id and any(n > 0 for n in by_type.values())
        for owner, by_type in state.systems[position].space_units.items()
    )


def _move_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    position = str(ctx.get("position") or "")
    systems = _transfer_systems(state, player_id, position)
    return (
        ctx.get("player") == player_id
        and active_effects.has_effect(state, player_id, WING_TRANSFER)
        and len(systems) > 1
        and any(state.systems[p].space_units.get(player_id) for p in systems)
    )


def transfer_move_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    systems = _transfer_systems(state, player_id, str(ctx.get("position") or ""))
    return direct_move.move_inputs(state, registry, player_id, systems, systems)


@on_event(
    GameEvent.TACTICAL_ACTION, Moment.END, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    optional=True, condition=_move_ready, inputs=transfer_move_inputs,
    covers=f"breakthroughs:{BREAKTHROUGH}", label="Wing Transfer: move ships",
)
def wing_transfer_move(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Wing Transfer: … at the end of this action, you may move ships among the active system and
    systems adjacent to it that contain your command tokens (pojemność obowiązuje - F_argent)."""
    systems = _transfer_systems(state, player_id, str(ctx.get("position") or ""))
    moves = direct_move.parse_moves(ctx.get("params", {}))
    if any(d not in systems or any(s not in systems for s in by) for d, by in moves.items()):
        raise ValueError("Move ships only among the active system and adjacent systems with "
                         "your command tokens.")
    direct_move.apply_moves(state, _registry(), player_id, moves, fighters_free=False)
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}", "moved ships")
