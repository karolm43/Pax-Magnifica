"""The Yin Brotherhood — komplet komponentów frakcji (RULES.md 62.10).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("yin")``, ``units``,
``breakthroughs/te_breakthroughs.json``) — wersje Ω z Codexów. Rulingi:
``docs/rules_tirules/F_yin.md``. Punkty silnika dodane dla Yin: wymagany cel trafień i trafienia
po rundzie (``battle.add_start_hits`` z ``only``, ``battle.add_round_end_hits``), natychmiastowa
przegrana strony bez jednostek przed rzutem, inwazja komponentu poza akcją taktyczną
(``invasion.start_component_invasion``), symbole prerekwizytów z kart i zwrot piechoty przy
badaniu (``technology.virtual_prerequisites``, ``technology.infantry_skip``), commanderzy
z efektów trwałych (``rules_hooks``) i emisja ``OBJECTIVE_SCORED`` przy celu publicznym.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    battle,
    board_graph,
    custodians,
    economy,
    faction_components,
    invasion,
    leaders,
    payment,
    promissory_play,
    rules_hooks,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.dice import next_rng
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import ActiveCombat, CombatStep, GameState, Phase, TacticalStep
from src.core.hooks.card_helpers import controlled, place_from_reinforcements, system_of_planet
from src.core.production import reinforcements_left
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_TECHNOLOGY_INFANTRY_SKIP,
    POINT_TECHNOLOGY_VIRTUAL_PREREQUISITES,
    SOURCE_BREAKTHROUGH,
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
from src.core.system_planets import board_planets
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

FACTION = "yin"
AGENT = "yinagent"
COMMANDER = "yincommander"
HERO = "yinhero"
FLAGSHIP = "yin_flagship"
MECH = "yin_mech"
GREYFIRE = "greyfire"
SPINNER = "yso"
IMPULSE = "ic"
BREAKTHROUGH = "yinbt"

INDOCTRINATION = "indoctrination"
DEVOTION = "devotion"
ALLIANCES = f"breakthroughs:{BREAKTHROUGH}:alliances"  # efekt trwały: zdobyte frakcje i commanderzy
_INDOCTRINATION_COST = 2  # „spend 2 influence”
_MECH_EXTRA = 1  # Moyin's Ashes: „spend 1 additional influence”
_SACRIFICE = ("cruiser", "destroyer")  # Devotion / Impulse Core: „cruisers or destroyers”
_SPINNER_MAX = 2  # „up to 2 infantry”
_MILOR_UNITS = 2  # „place 2 fighters … or 2 infantry”
_HERO_INFANTRY = 3  # „Commit up to 3 infantry”
_GREEN = "BIOTIC"  # „satisfies a green technology prerequisite”
_NONE = "none"
_SPACE = "space"
_GROUND_FORCES = ("infantry", "mech")


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _planet_name(registry: Any, planet: str) -> str:
    info = registry.planets.get(planet)
    return info.name if info is not None and info.name else planet


def _yin_players(state: GameState) -> list[str]:
    return [pid for pid, p in state.players.items() if p.faction == FACTION]


def _opponent(combat: ActiveCombat, player_id: str) -> str:
    return combat.defender if player_id == combat.attacker else combat.attacker


def _my_combat(state: GameState, player_id: str, kind: str) -> ActiveCombat | None:
    combat = state.active_combat
    if combat is None or combat.kind != kind or player_id not in (combat.attacker, combat.defender):
        return None
    return combat


def _left(state: GameState, player_id: str, base_type: str) -> int:
    """Ile sztuk w rezerwie (``None`` z danych = bez limitu → liczymy jak dużo)."""
    left = reinforcements_left(state, player_id, base_type)
    return 99 if left is None else left


def _ground_units(state: GameState, combat: ActiveCombat, player_id: str) -> dict[str, int]:
    system = state.systems.get(combat.position)
    units = system.planet_units.get(combat.planet or "", {}).get(player_id, {}) if system else {}
    return {bt: n for bt, n in units.items() if n > 0 and bt in _GROUND_FORCES}


def _replace_infantry(
    state: GameState, combat: ActiveCombat, victim: str, player_id: str, base_type: str
) -> None:
    """Zastępuje 1 piechotę ``victim`` w walce naziemnej jednostką gracza z rezerwy (MUTUJE)."""
    system = state.systems[combat.position]
    planet = combat.planet or ""
    unit_ops.remove_units(state, system, planet, victim, "infantry", 1, UnitCause.REMOVED)
    place_from_reinforcements(state, system, planet, player_id, base_type, 1)


# ------------------------------------------------------------------------------ Indoctrination


def _indoctrination_types(state: GameState, player_id: str) -> list[str]:
    """Czym Yin zastąpi piechotę: piechota (2 wpływu) i/lub mech Moyin's Ashes (3 wpływu)."""
    funds = sum(
        payment.ready_planet_values(state, _registry(), player_id, "influence").values()
    ) + economy.spendable_trade_goods(state, player_id)
    found: list[str] = []
    if _left(state, player_id, "infantry") > 0 and funds >= _INDOCTRINATION_COST:
        found.append("infantry")
    if _left(state, player_id, "mech") > 0 and funds >= _INDOCTRINATION_COST + _MECH_EXTRA:
        found.append("mech")
    return found


def _indoctrination_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    combat = _my_combat(state, player_id, "ground")
    if ctx.get("kind") != "ground" or combat is None:
        return False
    victim = _opponent(combat, player_id)
    # F_yin: same mechy (albo myśliwce Naalu) przeciwnika = nie ma czego zastąpić.
    return _ground_units(state, combat, victim).get("infantry", 0) > 0 and bool(
        _indoctrination_types(state, player_id)
    )


def indoctrination_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Jednostka zastępcza (piechota / mech za +1 wpływu) i płatność wpływem."""
    player = state.players[player_id]
    labels = {
        "infantry": f"Infantry ({_INDOCTRINATION_COST} influence)",
        "mech": f"Moyin's Ashes - DEPLOY ({_INDOCTRINATION_COST + _MECH_EXTRA} influence)",
    }
    units = [
        oi.option(bt, labels[bt], meta=oi.unit_meta(bt, player_id, player.faction, player.color, 1))
        for bt in _indoctrination_types(state, player_id)
    ]
    ready = payment.ready_planet_values(state, registry, player_id, "influence")
    planets = [(p, _planet_name(registry, p), v) for p, v in sorted(ready.items())]
    spendable = economy.spendable_trade_goods(state, player_id)
    return [
        oi.choice("unit", "Replace 1 of your opponent's infantry with", units),
        oi.payment_planets(
            planets, "influence", _INDOCTRINATION_COST,
            hint=f"Pay {_INDOCTRINATION_COST} influence ({_INDOCTRINATION_COST + _MECH_EXTRA} "
                 "for a mech).",
        ),
        oi.number("trade_goods", "Trade goods to spend", 0,
                  min(spendable, _INDOCTRINATION_COST + _MECH_EXTRA)),
    ]


@on_event(
    GameEvent.COMBAT, Moment.START, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_indoctrination_ready, inputs=indoctrination_inputs,
    covers=f"abilities:{INDOCTRINATION}", label="Indoctrination",
)
def indoctrination(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Indoctrination: At the start of a ground combat: You may spend 2 influence to replace 1 of
    your opponent's participating infantry with 1 infantry from your reinforcements.

    Raz na walkę (jedna oferta na start walki - F_yin). Ostatnia siła przeciwnika usunięta =
    przegrana od razu (``battle._after_start``). Moyin's Ashes: opcja ``unit=mech`` za +1 wpływu.
    """
    combat = _my_combat(state, player_id, "ground")
    if combat is None:
        raise ValueError("Indoctrination is used at the start of a ground combat you fight in.")
    params = ctx.get("params", {})
    unit = str(params.get("unit") or "infantry")
    if unit not in _indoctrination_types(state, player_id):
        raise ValueError("You cannot replace the infantry with that unit.")
    victim = _opponent(combat, player_id)
    if _ground_units(state, combat, victim).get("infantry", 0) <= 0:
        raise ValueError("Your opponent has no infantry in this combat.")
    cost = _INDOCTRINATION_COST + (_MECH_EXTRA if unit == "mech" else 0)
    planets = [str(p) for p in params.get("planets") or []]
    trade_goods = int(params.get("trade_goods") or 0)
    registry = _registry()
    paid = payment.validate_payment(state, registry, player_id, "influence", planets, trade_goods)
    if paid < cost:
        raise ValueError(f"Spend at least {cost} influence (you chose {paid}).")
    payment.apply_payment(state, player_id, planets, trade_goods)
    _replace_infantry(state, combat, victim, player_id, unit)
    ability_notes.note(
        state, player_id, f"abilities:{INDOCTRINATION}",
        "replaced 1 infantry with a mech" if unit == "mech" else "replaced 1 infantry",
    )
    faction_components.ability_used(state, player_id, INDOCTRINATION, victim)


# Moyin's Ashes (DEPLOY) to jawna opcja ``unit=mech`` w formularzu Indoctrination (wyżej).
rules_hooks.declare_player_option(f"units:{MECH}")


# ------------------------------------------------------------------------------------ Devotion


def _sacrifice_types(state: GameState, player_id: str, combat: ActiveCombat | None) -> list[str]:
    system = state.systems.get(combat.position) if combat is not None else None
    own = system.space_units.get(player_id, {}) if system is not None else {}
    return [bt for bt in _SACRIFICE if own.get(bt, 0) > 0]


def _enemy_ships(state: GameState, combat: ActiveCombat, player_id: str) -> dict[str, int]:
    system = state.systems.get(combat.position)
    victim = _opponent(combat, player_id)
    units = system.space_units.get(victim, {}) if system is not None else {}
    return {bt: n for bt, n in units.items() if n > 0 and is_space_unit(bt)}


def _sacrifice_options(state: GameState, registry: Any, player_id: str) -> list[dict[str, Any]]:
    player = state.players[player_id]
    combat = state.active_combat
    return [
        oi.option(bt, unit_name(state, registry, player_id, bt),
                  meta=oi.unit_meta(bt, player_id, player.faction, player.color, 1))
        for bt in _sacrifice_types(state, player_id, combat)
    ]


def _devotion_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    combat = _my_combat(state, player_id, _SPACE)
    return (
        ctx.get("kind") == _SPACE
        and ctx.get("phase") == "combat"
        and combat is not None
        and bool(_sacrifice_types(state, player_id, combat))
        and bool(_enemy_ships(state, combat, player_id))
    )


def devotion_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Własny krążownik/niszczyciel do zniszczenia i typ statku przeciwnika (wybiera Yin)."""
    combat = state.active_combat
    if combat is None:
        return []
    victim = _opponent(combat, player_id)
    owner = state.players.get(victim)
    targets = [
        oi.option(
            bt, f"{unit_name(state, registry, victim, bt)} ({n})",
            meta=oi.unit_meta(bt, victim, owner.faction if owner else None,
                              owner.color if owner else None, n),
        )
        for bt, n in sorted(_enemy_ships(state, combat, player_id).items())
    ]
    return [
        oi.choice("ship", "Your ship to destroy", _sacrifice_options(state, registry, player_id)),
        oi.choice("target", "Opponent's ship that takes the hit", targets),
    ]


@on_event(
    GameEvent.COMBAT_ROUND, Moment.END, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_devotion_ready, inputs=devotion_inputs,
    covers=f"abilities:{DEVOTION}", label="Devotion",
)
def devotion(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Devotion: After each space combat round: You may destroy 1 of your cruisers or destroyers in
    the active system to produce 1 hit and assign it to 1 of your opponent's ships in that system.

    F_yin: statek wybiera Yin; trafiony statek może użyć Sustain Damage (przypisanie w kroku
    ASSIGN z wymaganym celem), Shields Holding działa.
    """
    combat = _my_combat(state, player_id, _SPACE)
    if combat is None:
        raise ValueError("Devotion is used after a round of a space combat you fight in.")
    params = ctx.get("params", {})
    ship, target = str(params.get("ship") or ""), str(params.get("target") or "")
    if ship not in _sacrifice_types(state, player_id, combat):
        raise ValueError("Choose 1 of your cruisers or destroyers in the active system.")
    if target not in _enemy_ships(state, combat, player_id):
        raise ValueError("Choose 1 of your opponent's ships in the active system.")
    victim = _opponent(combat, player_id)
    unit_ops.remove_units(
        state, state.systems[combat.position], _SPACE, player_id, ship, 1, UnitCause.DESTROYED
    )
    battle.add_round_end_hits(state, victim, 1, only=[target], label="Devotion")
    ability_notes.note(state, player_id, f"abilities:{DEVOTION}", "1 hit")
    faction_components.ability_used(state, player_id, DEVOTION, victim)


# ----------------------------------------------------------------------- Impulse Core (tech)


def _impulse_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    combat = _my_combat(state, player_id, _SPACE)
    return ctx.get("kind") == _SPACE and bool(_sacrifice_types(state, player_id, combat))


def impulse_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options = _sacrifice_options(state, registry, player_id)
    return [oi.choice("ship", "Your ship to destroy", options)]


@on_event(
    GameEvent.COMBAT, Moment.START, HookSource(SOURCE_TECHNOLOGY, IMPULSE),
    optional=True, condition=_impulse_ready, inputs=impulse_inputs,
    covers=f"technologies:{IMPULSE}", label="Impulse Core",
)
def impulse_core(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Impulse Core: At the start of a space combat, you may destroy 1 of your cruisers or
    destroyers in the active system to produce 1 hit against your opponent's ships; that hit must be
    assigned by your opponent to 1 of their non-fighters ships if able.

    Przypisuje przeciwnik przed AFB (Sustain Damage dozwolone - F_yin, C_technology).
    """
    combat = _my_combat(state, player_id, _SPACE)
    if combat is None:
        raise ValueError("Impulse Core is used at the start of a space combat you fight in.")
    ship = str(ctx.get("params", {}).get("ship") or "")
    if ship not in _sacrifice_types(state, player_id, combat):
        raise ValueError("Choose 1 of your cruisers or destroyers in the active system.")
    victim = _opponent(combat, player_id)
    unit_ops.remove_units(
        state, state.systems[combat.position], _SPACE, player_id, ship, 1, UnitCause.DESTROYED
    )
    non_fighters = [bt for bt in _enemy_ships(state, combat, player_id) if bt != "fighter"]
    battle.add_start_hits(state, victim, 1, only=non_fighters or None, label="Impulse Core")


# ------------------------------------------------------------------------ Yin Spinner Ω (tech)


def _spinner_places(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """``(pozycja, strefa)``: planety gracza i przestrzenie z jego statkami."""
    places: list[tuple[str, str]] = []
    for planet in controlled(state, player_id):
        places.append((system_of_planet(state, planet).position, planet))
    for position, system in sorted(state.systems.items()):
        own = system.space_units.get(player_id, {})
        if any(n > 0 and is_space_unit(bt) for bt, n in own.items()):
            places.append((position, _SPACE))
    return places


def _spinner_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("player") == player_id
        and _left(state, player_id, "infantry") > 0
        and bool(_spinner_places(state, player_id))
    )


def spinner_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options = [
        oi.option(
            f"{pos}|{zone}",
            f"Space area of system {pos}" if zone == _SPACE else _planet_name(registry, zone),
        )
        for pos, zone in _spinner_places(state, player_id)
    ]
    most = min(_SPINNER_MAX, _left(state, player_id, "infantry"))
    return [
        oi.choice("where", "Place the infantry together on/in", options),
        oi.number("count", "Infantry to place", 1, max(1, most)),
    ]


@on_event(
    GameEvent.UNITS_PRODUCED, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, SPINNER),
    optional=True, condition=_spinner_ready, inputs=spinner_inputs,
    covers=f"technologies:{SPINNER}", label="Yin Spinner",
)
def yin_spinner(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Yin Spinner Ω: After you produce units, place up to 2 infantry from your reinforcements on
    any planet you control or in any space area that contains 1 or more of your ships.

    F_yin Ω: obie piechoty razem; każda produkcja (także z kart) wyzwala zdolność.
    """
    params = ctx.get("params", {})
    position, _, zone = str(params.get("where") or "").partition("|")
    if (position, zone) not in _spinner_places(state, player_id):
        raise ValueError("Choose a planet you control or a space area with your ships.")
    count = int(params.get("count") or 1)
    if not 1 <= count <= _SPINNER_MAX:
        raise ValueError("Place 1 or 2 infantry.")
    place_from_reinforcements(state, state.systems[position], zone, player_id, "infantry", count)


# ------------------------------------------------------------- Greyfire Mutagen Ω (notka)


promissory_play.any_subject(GREYFIRE)


def _greyfire_victim(state: GameState, player_id: str) -> str | None:
    """Przeciwnik posiadacza w walce naziemnej, gdy notka jest zagrywalna (inaczej ``None``)."""
    combat = _my_combat(state, player_id, "ground")
    if combat is None:
        return None
    victim = _opponent(combat, player_id)
    forces = _ground_units(state, combat, victim)
    if victim in _yin_players(state) or sum(forces.values()) < 2 or not forces.get("infantry"):
        return None
    return victim


@promissory_play.condition(GREYFIRE)
def _greyfire_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> str | None:
    if window.event is not GameEvent.COMBAT or _greyfire_victim(state, player_id) is None:
        return (
            "Greyfire Mutagen is played at the start of your ground combat against 2 or more "
            "ground forces (with infantry) not controlled by the Yin player."
        )
    if _left(state, player_id, "infantry") <= 0:
        return "You have no infantry in your reinforcements."
    return None


@register_effect(f"promissory_notes:{GREYFIRE}")
def greyfire_mutagen(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Greyfire Mutagen Ω: At the start of a ground combat against 2 or more ground forces that are
    not controlled by the Yin player: Replace 1 of your opponent's infantry with 1 infantry from
    your reinforcements. Then, return this card to the Yin player (zwrot - ``promissory_play``)."""
    victim = _greyfire_victim(state, player_id)
    combat = state.active_combat
    if victim is None or combat is None:
        raise ValueError("Greyfire Mutagen cannot be played now.")
    _replace_infantry(state, combat, victim, player_id, "infantry")


# --------------------------------------------------------------------- Brother Milor Ω (agent)


def _destroyed_in_combat(state: GameState, ctx: Mapping[str, Any]) -> bool:
    """Zniszczenie w walce: trwająca walka w tym systemie albo ostrzał akcji (Space Cannon,
    bombardowanie, Space Cannon Defense - F_yin Ω)."""
    position = str(ctx.get("position") or "")
    combat = state.active_combat
    if combat is not None and combat.position == position and combat.step is not CombatStep.DONE:
        return True
    if state.invasion is not None and state.invasion.position == position:
        return True
    return state.tactical_step is TacticalStep.SPACE_CANNON and state.active_system == position


def _milor_unit(ctx: Mapping[str, Any]) -> str | None:
    """Co postawić: myśliwce za statek, piechota za siłę naziemną na planecie."""
    base_type, zone = str(ctx.get("base_type") or ""), str(ctx.get("zone") or "")
    if zone == _SPACE and is_space_unit(base_type):
        return "fighter"
    if zone != _SPACE and base_type in _GROUND_FORCES:
        return "infantry"
    return None


def _milor_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    owner = str(ctx.get("player") or "")
    unit = _milor_unit(ctx)
    return (
        state.phase is Phase.ACTION
        and owner in state.players
        and unit is not None
        and _left(state, owner, unit) > 0
        and _destroyed_in_combat(state, ctx)
        and leaders.is_ready(state, _registry(), player_id, AGENT)
    )


@on_event(
    GameEvent.UNIT_DESTROYED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_milor_ready, covers=f"leaders:{AGENT}",
    label="Brother Milor: place 2 units",
)
def brother_milor(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Brother Milor Ω: After a player's unit is destroyed during combat: You may exhaust this card
    to allow that player to place 2 fighters in the destroyed unit's system if it was a ship, or 2
    infantry on its planet if it was a ground force.

    Tylko w fazie akcji (F_yin Ω). Jednostki z rezerwy właściciela (ile jest, do 2); walka trwa,
    jeśli strona odzyskała jednostki (F_yin).
    """
    owner, unit = str(ctx.get("player") or ""), _milor_unit(ctx)
    if owner not in state.players or unit is None or not _destroyed_in_combat(state, ctx):
        raise ValueError("Brother Milor is used after a unit is destroyed during combat.")
    count = min(_MILOR_UNITS, _left(state, owner, unit))
    if count <= 0:
        raise ValueError("That player has no such units in reinforcements.")
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT, {"target": owner})
    zone = _SPACE if unit == "fighter" else str(ctx.get("zone"))
    place_from_reinforcements(
        state, state.systems[str(ctx.get("position"))], zone, owner, unit, count
    )


# ------------------------------------------------------------------- Brother Omar Ω (commander)


def _own_ability(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and ctx.get("ability") in (INDOCTRINATION, DEVOTION)


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    condition=_own_ability, covers=f"unlocks:{COMMANDER}", label="Brother Omar unlocked",
)
def omar_unlock(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Unlock: Use one of your faction abilities (Indoctrination albo Devotion - F_yin Ω)."""
    registry = _registry()
    if COMMANDER in leaders.leaders_of(registry, state.players[player_id]):
        leaders.unlock(state, registry, player_id, COMMANDER)


@register(
    POINT_TECHNOLOGY_VIRTUAL_PREREQUISITES, HookSource(SOURCE_LEADER, COMMANDER), HookKind.MODIFY,
    covers=f"leaders:{COMMANDER}",
)
def omar_green(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    """Brother Omar Ω: This card satisfies a green technology prerequisite."""
    return 1 if ctx.get("color") == _GREEN else 0


@register(
    POINT_TECHNOLOGY_INFANTRY_SKIP, HookSource(SOURCE_LEADER, COMMANDER), HookKind.PERMIT,
    covers=f"leaders:{COMMANDER}",
)
def omar_infantry_skip(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Brother Omar Ω: When you research a tech owned by another player, you may return 1 of your
    infantry to reinforcements to ignore its prerequisites (to samo id - F_yin Ω)."""
    tech = str(ctx.get("technology") or "")
    return any(
        tech in p.technologies for pid, p in state.players.items() if pid != player_id
    )


# ---------------------------------------------- Dannel of the Tenth Ω — Quantum Dissemination


def _home_planets(registry: Any) -> set[str]:
    return {p for faction in registry.factions.values() for p in (faction.home_planets or [])}


def dissemination_targets(state: GameState, registry: Any) -> list[tuple[str, str]]:
    """``(pozycja, planeta)`` spoza systemów domowych, na które wolno zaangażować piechotę."""
    home = _home_planets(registry)
    # Cała plansza, nie tylko systemy z wpisem w stanie (tam, gdzie już coś stoi).
    return [
        (position, planet)
        for position, planet in board_planets(state, registry)
        if planet not in home
        and planet not in custodians.landing_blocked(state, registry, position)
    ]


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Trzy wybory planety (każdy może pominąć; ta sama planeta kilka razy - F_yin Ω)."""
    options = [oi.option(_NONE, "No infantry")] + [
        oi.option(f"{pos}|{planet}", _planet_name(registry, planet), ref=("planet", planet))
        for pos, planet in dissemination_targets(state, registry)
    ]
    slots = min(_HERO_INFANTRY, _left(state, player_id, "infantry"))
    return [
        oi.choice(f"planet{i + 1}", f"Infantry {i + 1} commits to", options)
        for i in range(max(1, slots))
    ]


@register_effect(f"leaders:{HERO}")
def quantum_dissemination(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Dannel of the Tenth Ω — Quantum Dissemination: ACTION: Commit up to 3 infantry from your
    reinforcements to any non-home planets and resolve ground combats on those planets. Players
    cannot use SPACE CANNON against these units. Then, purge this card.

    Wszystkie piechoty lądują przed walkami; systemy rozstrzygane po kolei w oknie inwazji
    (Commit → Ground Combat → Establish Control), bez aktywacji systemów (F_yin Ω).
    """
    allowed = set(dissemination_targets(state, registry))
    commits: dict[str, dict[str, dict[str, int]]] = {}
    total = 0
    for index in range(_HERO_INFANTRY):
        value = str(params.get(f"planet{index + 1}") or _NONE)
        if value == _NONE:
            continue
        position, _, planet = value.partition("|")
        if (position, planet) not in allowed:
            raise ValueError("Commit infantry only to non-home planets (not to Mecatol Rex "
                             "while the Custodians token is on it).")
        landed = commits.setdefault(position, {}).setdefault(planet, {})
        landed["infantry"] = landed.get("infantry", 0) + 1
        total += 1
    if total == 0:
        raise ValueError("Commit at least 1 infantry.")
    if _left(state, player_id, "infantry") < total:
        raise ValueError("Not enough infantry in your reinforcements.")
    for position, by_planet in commits.items():
        for planet, by_type in by_planet.items():
            place_from_reinforcements(
                state, board_graph.ensure_system(state, position), planet, player_id, "infantry",
                by_type["infantry"],
            )
    invasion.start_component_invasion(state, player_id, f"leaders:{HERO}", commits)


# -------------------------------------------------------------------------- Van Hauge (flagowiec)


def _own_flagship_lost(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and ctx.get("zone") == _SPACE


@on_event(
    GameEvent.UNIT_DESTROYED, Moment.AFTER, HookSource(SOURCE_UNIT, FLAGSHIP),
    where={"base_type": "flagship"}, condition=_own_flagship_lost,
    covers=f"units:{FLAGSHIP}", label="Van Hauge: destroy all ships",
)
def van_hauge(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    """Van Hauge: When this ship is destroyed, destroy all ships in this system.

    Statki wszystkich graczy (także Yin); siły naziemne i struktury zostają (F_yin: Floating
    Factory Saar też). Walka bez statków = remis (``battle._finish_round``).
    """
    system = state.systems.get(str(ctx.get("position")))
    if system is None:
        return
    for owner in list(system.space_units):
        for base_type, count in list(system.space_units.get(owner, {}).items()):
            if count > 0 and is_space_unit(base_type):
                unit_ops.remove_units(
                    state, system, _SPACE, owner, base_type, count, UnitCause.DESTROYED
                )


# ------------------------------------------------------------------ Yin Ascendant (przełom)


def alliance_factions(state: GameState, player_id: str) -> list[str]:
    """Frakcje, których zdolność sojuszu (commander) gracz zdobył przez Yin Ascendant."""
    return [
        str(f)
        for e in state.active_effects
        if e.key == ALLIANCES and e.owner == player_id
        for f in e.data.get("factions") or ()
    ]


def _unused_factions(state: GameState, registry: Any, player_id: str) -> list[tuple[str, str]]:
    """``(frakcja, commander)`` grywalnych frakcji spoza gry i jeszcze niezdobytych (jedna na
    rodzinę, deterministyczna kolejność - losowanie RNG stanu)."""
    in_game = {
        registry.faction_family(registry.factions[p.faction])
        for p in state.players.values()
        if p.faction in registry.factions
    }
    gained = {
        registry.faction_family(registry.factions[f])
        for f in alliance_factions(state, player_id)
        if f in registry.factions
    }
    picks: dict[str, tuple[str, str]] = {}
    for fid, faction in sorted(registry.factions.items()):
        family = registry.faction_family(faction)
        if not faction.is_playable or family in in_game or family in gained or family in picks:
            continue
        commander = next(
            (lid for lid in faction.leaders
             if lid in registry.leaders and registry.leaders[lid].type == "commander"),
            None,
        )
        if commander is not None:
            picks[family] = (fid, commander)
    return [picks[f] for f in sorted(picks)]


def gain_alliance(state: GameState, player_id: str) -> str | None:
    """Losowa niewykorzystana frakcja → jej commander działa dla gracza (MUTUJE ``state``)."""
    registry = _registry()
    pool = _unused_factions(state, registry, player_id)
    if not pool:
        return None
    faction_id, commander = pool[next_rng(state).randrange(len(pool))]
    effect = next(
        (e for e in state.active_effects if e.key == ALLIANCES and e.owner == player_id), None
    )
    if effect is None:
        from src.core import active_effects  # lokalnie: unika cyklu przy ładowaniu hooków

        effect = active_effects.add_effect(state, ALLIANCES, Duration.GAME, owner=player_id)
    effect.data = {
        "factions": [*effect.data.get("factions", []), faction_id],
        "commanders": [*effect.data.get("commanders", []), commander],
    }
    leader = registry.leaders.get(commander)
    ability_notes.note(
        state, player_id, f"breakthroughs:{BREAKTHROUGH}",
        f"alliance: {registry.factions[faction_id].name}"
        + (f" ({leader.name})" if leader is not None else ""),
    )
    return faction_id


def _gained_yin_ascendant(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


@on_event(
    GameEvent.COMPONENT_GAINED, Moment.WHEN, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    where={"component": f"breakthroughs:{BREAKTHROUGH}"}, condition=_gained_yin_ascendant,
    covers=f"breakthroughs:{BREAKTHROUGH}", label="Yin Ascendant: gain an alliance",
)
def yin_ascendant_gained(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Yin Ascendant: When you gain this card ..., gain the alliance ability of a random, unused
    faction (commander „tak, jakby był odblokowany” - F_yin)."""
    gain_alliance(state, player_id)


def _scored_public(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and ctx.get("secret") != "true"


@on_event(
    GameEvent.OBJECTIVE_SCORED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    condition=_scored_public, covers=f"breakthroughs:{BREAKTHROUGH}",
    label="Yin Ascendant: gain an alliance",
)
def yin_ascendant_scored(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Yin Ascendant: ... or score a public objective, gain the alliance ability of a random,
    unused faction."""
    gain_alliance(state, player_id)
