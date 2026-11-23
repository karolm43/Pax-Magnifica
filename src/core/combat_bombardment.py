"""BOMBARDMENT w trakcie walki naziemnej (Harrow, RULES.md 62.12).

„At the end of each round of ground combat: Your ships in the active system may use their
BOMBARDMENT abilities against your opponent's ground forces on the planet.” Rdzeń bez wiedzy o
frakcji: kto bombarduje i kiedy, decyduje hook; tu są grupy jednostek, cel i rzut.

Rulingi (F_lizix, R_bombardment): Planetary Shield blokuje (chyba że war sun / 2RAM -
``invasion.planet_infos``); w walce naziemnej KAŻDA jednostka z Bombardment w systemie może
strzelać w planetę walki; Annihilator spoza tej walki też (``invasion.ground_bombarders``);
modyfikatory jak w kroku Bombardment (Bunker, mnożnik X-89, okno ``UNIT_ABILITY_USED/AFTER``).

Rzut trafia do dziennika walki (wpis ``phase="BOMBARDMENT"``): okno walki naziemnej zostaje
otwarte, a front pokazuje go fizycznymi kośćmi i salwą z orbity (``BattleOverlay``). Przed
rzutem trwa okno „when … units make a roll for a unit ability” (Strike Wing Ambuscade):
oferta zdolności zarejestrowana przez :func:`register_roll_offer` czeka na decyzję gracza.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import entropic_scar, extra_dice, invasion, rules_hooks, triggers
from src.core.dice import DIE_SIDES, count_hits, next_rng
from src.core.game_events import GameEvent, Moment
from src.core.game_state import ActiveCombat, GameState
from src.core.invasion import BombardGroup
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

ABILITY = "bombardment"
LOG_PHASE = "BOMBARDMENT"  # wpis dziennika walki (okno bitwy animuje go jak salwę z orbity)
_ROLL_OFFERS: set[str] = set()  # etykiety ofert, które rzucają Bombardment w walce


def register_roll_offer(label: str) -> None:
    """Oferta o tej etykiecie (np. „Harrow”) = zapowiedziany rzut Bombardment w walce."""
    _ROLL_OFFERS.add(label)


def pending_roller(state: GameState) -> str | None:
    """Gracz, którego oferta rzutu Bombardment w walce czeka teraz na decyzję (albo ``None``)."""
    if ground_combat(state) is None:
        return None
    return next(
        (o.player_id for o in state.pending_offers if o.label in _ROLL_OFFERS), None
    )


def ground_combat(state: GameState) -> ActiveCombat | None:
    """Trwająca walka naziemna w inwazji (albo ``None``)."""
    combat = state.active_combat
    if combat is None or combat.kind != "ground" or not combat.planet:
        return None
    if state.invasion is None or state.invasion.position != combat.position:
        return None
    return combat


def groups(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[BombardGroup]:
    """Jednostki gracza z Bombardment w aktywnym systemie walki: statki + siły naziemne
    bombardujące „jak statek”, które nie walczą na planecie tej walki."""
    combat = ground_combat(state)
    if combat is None or entropic_scar.unit_abilities_blocked(state, combat.position, registry):
        return []  # Entropic Scar: brak BOMBARDMENT w bliźnie (RULES.md 1.5)
    system = state.systems[combat.position]
    units = {
        bt: n for bt, n in system.space_units.get(player_id, {}).items()
        if n > 0 and is_space_unit(bt)
    }
    units.update(invasion.ground_bombarders(state, player_id, combat.position,
                                            exclude_planet=combat.planet))
    found: list[BombardGroup] = []
    for bt, count in sorted(units.items()):
        unit = invasion.unit_variant(state, registry, player_id, bt)
        if unit is None or not unit.bombard_hits_on or unit.bombard_hits_on <= 0:
            continue
        found.append(BombardGroup(
            base_type=bt, unit_id=unit.id, name=unit.name, count=count,
            hits_on=unit.bombard_hits_on, dice_per_unit=unit.bombard_die_count or 1,
        ))
    return found


def target_open(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Planeta walki jest celem: przeciwnik ma tam siły naziemne, tarcza nie blokuje."""
    combat = ground_combat(state)
    if combat is None:
        return False
    info = next(
        (i for i in invasion.planet_infos(state, registry) if i.planet == combat.planet), None
    )
    opponent = combat.defender if combat.attacker == player_id else combat.attacker
    system = state.systems[combat.position]
    # Hel-Titan (struktura i siła naziemna) jest celem, gdy tarcza nie blokuje (F_ul hel-titan 5).
    targets = ("infantry", "mech", *sorted(invasion.structure_ground_types(state, opponent)))
    has_ground = any(
        system.planet_units.get(combat.planet or "", {}).get(opponent, {}).get(bt, 0) > 0
        for bt in targets
    )
    return info is not None and not info.shielded and has_ground


def extra_sources(state: GameState, player_id: str) -> list[extra_dice.ExtraDie]:
    """Źródła dodatkowych kości bombardowania gracza (Plasma Scoring, commander Argent…)."""
    combat = ground_combat(state)
    position = combat.position if combat is not None else ""
    return extra_dice.sources(
        state, player_id, rules_hooks.POINT_BOMBARDMENT_EXTRA_DICE, {"position": position}
    )


def roll(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    picks: Mapping[str, str] | None = None,
    *,
    label: str = "Bombardment",
) -> int:
    """Rzut wszystkich grup na planetę walki (MUTUJE klon). Zwraca liczbę trafień.

    ``picks`` = ``{źródło dodatkowej kości: grupa | "auto" | "none"}`` (``extra_dice.assign``).

    Raises:
        ValueError: Brak walki naziemnej, celu albo jednostek z Bombardment.
    """
    combat = ground_combat(state)
    if combat is None or not combat.planet:
        raise ValueError("Bombardment during combat needs an ongoing ground combat.")
    if not target_open(state, registry, player_id):
        raise ValueError("The planet cannot be bombarded.")
    rolling = groups(state, registry, player_id)
    if not rolling:
        raise ValueError("No unit can bombard the planet.")
    planet = combat.planet
    bonus = extra_dice.assign(
        extra_sources(state, player_id), {g.base_type: g.hits_on for g in rolling}, picks
    )
    modifier = invasion.bombard_modifier(state, planet)
    multiplier = rules_hooks.modify(
        rules_hooks.POINT_COMBAT_HIT_MULTIPLIER, state, player_id, 1, {"kind": ABILITY},
    )
    rng = next_rng(state)
    entries: list[dict[str, Any]] = []
    hits = 0
    for group in rolling:
        extra = bonus.get(group.base_type, 0)
        dice = [rng.randint(1, DIE_SIDES) for _ in range(group.total_dice + extra)]
        group_hits = count_hits([d + modifier for d in dice], group.hits_on) * multiplier
        hits += group_hits
        entry: dict[str, Any] = {
            "baseType": group.base_type, "name": group.name, "hitsOn": group.hits_on,
            "modifier": modifier, "dice": dice, "hits": group_hits,
        }
        if extra:
            entry["extraDice"] = extra
        entries.append(entry)
    opponent = combat.defender if combat.attacker == player_id else combat.attacker
    combat.log = [*combat.log, {
        "round": combat.round, "phase": LOG_PHASE, "label": label,
        "rolls": {player_id: entries, opponent: []},
        "hits": {player_id: hits, opponent: 0},
        "losses": {}, "sustained": {},
    }]
    triggers.fire(
        state, GameEvent.UNIT_ABILITY_USED, Moment.AFTER, subject=player_id,
        ctx={"ability": ABILITY, "player": player_id, "position": combat.position,
             "planets": [planet]},
    )
    return hits
