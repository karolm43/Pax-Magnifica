"""The Naalu Collective — komplet komponentów frakcji (RULES.md 62.16).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("naalu")``, ``units``,
``breakthroughs/te_breakthroughs.json``). Rulingi: ``docs/rules_tirules/F_naalu.md`` (krzyżowo
``R_initiative_order``, ``R_elimination``, ``C_action_cards`` - Intercept, ``F_yin`` -
Indoctrination). Aktywne warianty: Z'eu z Thunder's Edge (rulingi „Z'eu ΩΩ”), M'aban z Codexu
(„M'aban Ω”), Iconoclast TE („Iconoclast ΩΩ”).
Punkty silnika dodane dla Naalu: żeton „0” (``core/initiative_zero``), okno „koniec fazy strategii”
(``reactions_misc.strategy_phase_end``), położenie żetonu dowodzenia
(``command_tokens.place_token`` -> ``COMMAND_TOKEN_PLACED``), myśliwce w puli floty
(``fleet_pool.fighters_overflow`` / ``fighters_per_ship``), statki jako siły naziemne w inwazji
(``ship_roles.ground_force_types``), stały podgląd ukrytych kart (``core/peek``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    board_graph,
    card_draw,
    command_tokens,
    cooperative,
    entropic_scar,
    faction_components,
    initiative_zero,
    invasion,
    leaders,
    movement,
    peek,
    promissory_notes,
    promissory_play,
    rules_hooks,
    strategic_action,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.custodians import is_mecatol_position
from src.core.fleet_pool import unit_name
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, SystemState, WindowType
from src.core.hex_grid import HexGrid
from src.core.hooks import card_labels
from src.core.production import reinforcements_left
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.retreat import ships_move_destinations
from src.core.rules_hooks import (
    POINT_FLEET_POOL_FIGHTERS_OVERFLOW,
    POINT_FLEET_POOL_FIGHTERS_PER_SHIP,
    POINT_INFO_PEEK,
    POINT_INVASION_GROUND_FORCE_TYPES,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_PROMISSORY,
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
from src.core.unit_ops import UnitCause

FACTION = "naalu"
TELEPATHIC = "telepathic"
FORESIGHT = "foresight"
NEUROGLAIVE = "ng"
HCF2 = "hcf2"
FIGHTER2 = "naalu_fighter2"  # karta jednostki Hybrid Crystal Fighter II (ten sam tekst co hcf2)
GIFT = "gift"
FLAGSHIP = "naalu_flagship"
MECH = "naalu_mech_te"
AGENT = "naaluagent-te"
COMMANDER = "naalucommander"
HERO = "naaluhero"
BREAKTHROUGH = "naalubt"

_SPACE = "space"
_FIGHTER = "fighter"
_MECH = "mech"
_GROUND_CARGO = ("mech", "infantry")  # ⚠️ ZAŁOŻENIE (62.16): kolejność „Auto” przy Foresight
_CARRY = "carry_"  # pole Foresight: ile sił naziemnych danego typu zabrać
_GROUND_FORCES = frozenset(_GROUND_CARGO)
_SUPERNOVA = "SUPERNOVA"
_HCF_FIGHTERS_PER_SHIP = 1  # „count as 1/2 of a ship” = +1 myśliwiec na statek (baza 1)


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _grid(state: GameState) -> HexGrid:
    """Siatka gry z API; w testach jednostkowych - z systemów stanu."""
    return board_graph.bound_grid() or grid_from_state(state, _registry())


def _naalu_player(state: GameState) -> str | None:
    """Gracz Naalu (właściciel notki Gift of Prescience) - ``None`` po eliminacji."""
    _template, owner = promissory_play.resolve(state, _registry(), GIFT)
    return owner


def _note_option(state: GameState, registry: StaticDataRegistry, note_id: str) -> dict[str, Any]:
    name, _text = promissory_play.note_text(state, registry, note_id)
    return oi.option(note_id, name, ref=("promissory", note_id))


def _ships(system: SystemState | None, player_id: str) -> dict[str, int]:
    """Statki gracza w przestrzeni systemu (myśliwce też) - bez sił naziemnych."""
    if system is None:
        return {}
    return {
        bt: n for bt, n in system.space_units.get(player_id, {}).items()
        if n > 0 and is_space_unit(bt)
    }


# ------------------------------------------------------------- Telepathic / Gift of Prescience


def _gift_in_play(state: GameState) -> bool:
    return any(GIFT in p.promissory_notes_in_play for p in state.players.values())


def _telepathic_ready(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Gift of Prescience w czyjejś strefie = Telepathic w tej rundzie nie działa."""
    return bool(state.players[player_id].strategy_cards) and not _gift_in_play(state)


@on_event(
    GameEvent.PHASE, Moment.END, HookSource(SOURCE_FACTION, FACTION), where={"phase": "strategy"},
    condition=_telepathic_ready, covers=f"abilities:{TELEPATHIC}", label="Telepathic",
)
def telepathic(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Telepathic: At the end of the strategy phase: Place the Naalu "0" token on your strategy
    card; you are first in initiative order (``initiative_zero`` - inicjatywa 0)."""
    initiative_zero.place(state, player_id)


@promissory_play.condition(GIFT)
def _gift_condition(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, window: OpenWindow
) -> str | None:
    if window.ctx.get("phase") != "strategy":
        return "Gift of Prescience is played at the end of the strategy phase."
    if not state.players[player_id].strategy_cards:
        return "You need a strategy card to place the Naalu \"0\" token on."
    return None


@register_effect(f"promissory_notes:{GIFT}")
def gift_of_prescience(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Gift of Prescience: At the end of the Strategy Phase: Place this card faceup in your play
    area and place the Naalu '0' token on your strategy card, you are the first in initiative
    order. The Naalu player cannot use their Telepathic faction ability during this game round.

    Strefę gry załatwia ``promissory_play`` (``playArea``); Telepathic sprawdza notkę w strefie."""
    initiative_zero.place(state, player_id)


@on_event(
    GameEvent.PHASE, Moment.END, HookSource(SOURCE_PROMISSORY, GIFT), where={"phase": "status"},
    covers=f"promissory_notes:{GIFT}", label="Gift of Prescience: return",
)
def gift_returns(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Return this card to the Naalu player at the end of the status phase."""
    owner = _naalu_player(state)
    if owner is None or owner == player_id:  # Naalu wyeliminowany: notka znika ze strefy
        promissory_notes.remove_from_play(state, player_id, GIFT)
        return
    promissory_notes.return_from_play(state, player_id, owner, GIFT)


# ---------------------------------------------------------------------------- Foresight


def foresight_destinations(state: GameState, player_id: str, position: str) -> list[str]:
    """Sąsiednie systemy bez statków innych graczy; nigdy supernowa, pole asteroid tylko z
    Antimass Deflectors (``ships_move_destinations``). Mgławica dozwolona (R_nebula notes/2,
    decyzja użytkownika 2026-11-24)."""
    grid = _grid(state)
    return [
        pos for pos in ships_move_destinations(state, grid, position, player_id)
        if _SUPERNOVA not in grid.anomalies_at(pos)
    ]


def _foresight_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    position = str(ctx.get("position") or "")
    mover = ctx.get("player")
    return (
        mover is not None and mover != player_id
        and state.players[player_id].strategic_cc > 0
        and bool(_ships(state.systems.get(position), player_id))
        and bool(foresight_destinations(state, player_id, position))
    )


def foresight_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Cel - system na mapie (pozycja jako wartość opcji); siły naziemne z przestrzeni - ile
    zabrać (wybór gracza z wartością „Auto” = ``_auto_cargo``)."""
    position = str(ctx.get("position") or "")
    options = [
        oi.option(pos, card_labels.describe_system(state, registry, pos))
        for pos in foresight_destinations(state, player_id, position)
    ]
    inputs = [oi.choice("destination", "Adjacent system to move your ships to", options)]
    origin = state.systems.get(position)
    if origin is None:
        return inputs
    free = _capacity(state, registry, player_id, _ships(origin, player_id))
    auto = _auto_cargo(state, registry, player_id, origin, free)
    for base_type in _GROUND_CARGO:
        have = origin.space_units.get(player_id, {}).get(base_type, 0)
        if have > 0:
            inputs.append(oi.number(
                f"{_CARRY}{base_type}", f"{unit_name(state, registry, player_id, base_type)}"
                " to take along", 0, have,
                hint=f"Your moving ships have capacity {free}; the rest stays in the system.",
                auto=auto.get(base_type, 0),
            ))
    return inputs


def _capacity(
    state: GameState, registry: StaticDataRegistry, player_id: str, ships: Mapping[str, int]
) -> int:
    """Pojemność ruszających statków (myśliwce nie zajmują miejsca - F_naalu foresight 3)."""
    player = state.players[player_id]
    return sum(
        movement._capacity_provided(registry, player.faction, player.technologies, bt) * n
        for bt, n in ships.items()
    )


def _cargo_cost(state: GameState, registry: StaticDataRegistry, player_id: str,
                base_type: str) -> int:
    player = state.players[player_id]
    return max(1, movement._capacity_used(registry, player.faction, player.technologies,
                                          base_type))


def _auto_cargo(
    state: GameState, registry: StaticDataRegistry, player_id: str, system: SystemState, free: int
) -> dict[str, int]:
    """„Auto”: siły naziemne do pojemności, najpierw mechy, potem piechota (⚠️ ZAŁOŻENIE)."""
    cargo: dict[str, int] = {}
    for base_type in _GROUND_CARGO:
        have = system.space_units.get(player_id, {}).get(base_type, 0)
        per_unit = _cargo_cost(state, registry, player_id, base_type)
        take = min(have, free // per_unit)
        if take > 0:
            cargo[base_type] = take
            free -= take * per_unit
    return cargo


def _chosen_cargo(
    state: GameState, registry: StaticDataRegistry, player_id: str, system: SystemState,
    ships: Mapping[str, int], params: Mapping[str, Any],
) -> dict[str, int]:
    """Ładunek wybrany przez gracza (brak pola = „Auto”); nie więcej niż pojemność floty."""
    free = _capacity(state, registry, player_id, ships)
    auto = _auto_cargo(state, registry, player_id, system, free)
    cargo: dict[str, int] = {}
    for base_type in _GROUND_CARGO:
        have = system.space_units.get(player_id, {}).get(base_type, 0)
        count = int(params.get(f"{_CARRY}{base_type}", auto.get(base_type, 0)))
        if not 0 <= count <= have:
            raise ValueError(f"You have only {have} {base_type} in the space area.")
        if count:
            cargo[base_type] = count
    used = sum(_cargo_cost(state, registry, player_id, bt) * n for bt, n in cargo.items())
    if used > free:
        raise ValueError(f"Your moving ships can carry {free}, but the ground forces need {used}.")
    return cargo


@on_event(
    GameEvent.SHIPS_MOVED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION), optional=True,
    condition=_foresight_ready, inputs=foresight_inputs, covers=f"abilities:{FORESIGHT}",
    label="Foresight",
)
def foresight(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Foresight: After another player moves ships into a system that contains 1 or more of your
    ships: You may place 1 token from your strategy pool in an adjacent system that does not
    contain another player's ships; move your ships from the active system into that system.

    To nie odwrót (bez ``RETREAT_DECLARED`` - 1) i żeton nie jest „wydany” (bez Scepter i Alliance
    Muaat - 2); żeton już w celu = żeton z puli do rezerwy (7); gravity rift - rzut (5, 5.1)."""
    registry = _registry()
    position = str(ctx.get("position") or "")
    destination = str(ctx.get("params", {}).get("destination") or "")
    if destination not in foresight_destinations(state, player_id, position):
        raise ValueError("Choose an adjacent system that does not contain another player's ships.")
    grid = _grid(state)
    origin = state.systems[position]
    ships = _ships(origin, player_id)
    cargo = _chosen_cargo(state, registry, player_id, origin, ships, ctx.get("params", {}))
    target = state.systems.get(destination)
    if target is None:
        system_id = grid.system_id_at(destination) if destination in grid.positions else ""
        target = SystemState(position=destination, system_id=system_id)
        state.systems[destination] = target
    command_tokens.spend_from_pool(state, player_id, "strategic")
    if player_id in target.command_tokens:
        command_tokens.return_to_reinforcements(state, player_id)
    else:
        command_tokens.place_token(state, target, player_id)
    moving = {**ships, **cargo}
    if movement.is_gravity_rift(grid, position):
        for base_type, lost in movement.roll_rift_exit(state, player_id, moving).items():
            unit_ops.remove_units(state, origin, _SPACE, player_id, base_type, lost,
                                  UnitCause.REMOVED)
            moving[base_type] -= lost
    moved = {bt: n for bt, n in moving.items() if n > 0}
    for base_type, count in moved.items():
        unit_ops.transfer_units(state, origin, _SPACE, target, _SPACE, player_id, base_type, count)
    ability_notes.note(state, player_id, f"abilities:{FORESIGHT}",
                       f"ships moved from system {position} to {destination}")
    movement.fire_ships_moved(
        state, player_id, destination, position,
        {bt: n for bt, n in moved.items() if bt not in _GROUND_FORCES}, kind="direct",
    )


# --------------------------------------------------------------------------- Neuroglaive


def _neuroglaive_applies(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    activator = ctx.get("player")
    return (
        activator is not None and activator != player_id and activator in state.players
        and bool(_ships(state.systems.get(str(ctx.get("position") or "")), player_id))
        and state.players[str(activator)].fleet_cc > 0
    )


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, NEUROGLAIVE),
    condition=_neuroglaive_applies, covers=f"technologies:{NEUROGLAIVE}", label="Neuroglaive",
)
def neuroglaive(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    """Neuroglaive: After another player activates a system that contains 1 or more of your ships,
    that player removes 1 token from their fleet pool and returns it to their reinforcements.

    Nadwyżkę puli floty w każdym systemie otwiera ``limits.enforce_limits``, a ruch czeka na jej
    usunięcie (F_naalu neuroglaive 1)."""
    activator = str(ctx["player"])
    command_tokens.spend_to_reinforcements(state, activator, "fleet")
    ability_notes.note(state, activator, f"technologies:{NEUROGLAIVE}",
                       "1 token removed from the fleet pool")


# ------------------------------------------------------------- Hybrid Crystal Fighter II


@register(POINT_FLEET_POOL_FIGHTERS_OVERFLOW, HookSource(SOURCE_TECHNOLOGY, HCF2), HookKind.PERMIT,
          covers=f"technologies:{HCF2}")
def hcf2_overflow(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Hybrid Crystal Fighter II: This unit may move without being transported (Move z wariantu
    ``naalu_fighter2``). Fighters in excess of your ships' capacity count as 1/2 of a ship against
    your fleet pool."""
    return True


@register(POINT_FLEET_POOL_FIGHTERS_PER_SHIP, HookSource(SOURCE_TECHNOLOGY, HCF2), HookKind.MODIFY,
          covers=f"units:{FIGHTER2}")
def hcf2_half_ship(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """„count as 1/2 of a ship” - 2 myśliwce ponad pojemność = 1 statek puli floty."""
    return _HCF_FIGHTERS_PER_SHIP


# ------------------------------------------------------------------------------ Matriarch


def _flagship_in(state: GameState, player_id: str, position: str) -> bool:
    system = state.systems.get(position)
    return system is not None and system.space_units.get(player_id, {}).get("flagship", 0) > 0


@register(POINT_INVASION_GROUND_FORCE_TYPES, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.FORBID,
          covers=f"units:{FLAGSHIP}")
def matriarch(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> tuple[str, ...]:
    """Matriarch: During an invasion in this system, you may commit fighters to planets as if they
    were ground forces (lądowanie, walka naziemna, Space Cannon Defense - F_naalu 4)."""
    position = str(ctx.get("position") or "")
    inv = state.invasion
    if inv is None or inv.position != position or inv.attacker != player_id:
        return ()
    return (_FIGHTER,) if _flagship_in(state, player_id, position) else ()


def _ground_combat_of_attacker(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    inv = state.invasion
    return (
        ctx.get("kind") == "ground" and bool(ctx.get("planet"))
        and inv is not None and inv.attacker == player_id
    )


@on_event(
    GameEvent.COMBAT, Moment.END, HookSource(SOURCE_UNIT, FLAGSHIP),
    condition=_ground_combat_of_attacker, label="Matriarch: fighters return",
)
def matriarch_return(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    """After combat, return those units to the space area (tylko z planety tej walki; reszta -
    najpóźniej przed Establish Control: nie dają kontroli - F_naalu matriarch 1)."""
    invasion.return_ships_to_space(state, str(ctx["planet"]))


# ---------------------------------------------------------------------------- Iconoclast TE


def _mech_planets(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """Kontrolowane planety na planszy (poza blizną entropiczną - DEPLOY, RULES.md 1.5)."""
    registry = _registry()
    found: list[tuple[str, str]] = []
    for planet in sorted(state.players[player_id].controlled_planets):
        position = card_labels.system_position_of_planet(state, planet)
        if position is None or entropic_scar.unit_abilities_blocked(state, position, registry):
            continue
        found.append((position, planet))
    return found


def _iconoclast_applies(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    left = reinforcements_left(state, player_id, _MECH)
    return (
        str(ctx.get("component") or "").startswith("relics:")
        and ctx.get("player") not in (None, player_id)
        and (left is None or left > 0)
        and bool(_mech_planets(state, player_id))
    )


def iconoclast_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options = [
        oi.option(planet, card_labels.describe_planet(state, registry, planet),
                  ref=("planet", planet))
        for _pos, planet in _mech_planets(state, decider)
    ]
    return [oi.choice("planet", "Planet for 1 mech (Iconoclast)", options, always=True)]


@on_event(
    GameEvent.COMPONENT_GAINED, Moment.WHEN, HookSource(SOURCE_UNIT, MECH), decide=True,
    condition=_iconoclast_applies, inputs=iconoclast_inputs, covers=f"units:{MECH}",
    label="Iconoclast: DEPLOY",
)
def iconoclast(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Iconoclast TE: DEPLOY: When another player gains a relic, place 1 mech on any planet you
    control (obowiązkowo, gdy mech jest w rezerwie - F_naalu iconoclast ΩΩ 1)."""
    planet = str(ctx.get("params", {}).get("planet") or "")
    places = dict((p, pos) for pos, p in _mech_planets(state, player_id))
    if planet not in places:
        raise ValueError("Choose a planet you control.")
    unit_ops.place_units(state, state.systems[places[planet]], planet, player_id, _MECH, 1,
                         UnitCause.PLACED)


# -------------------------------------------------------------------------- Z'eu (agent)


def _zeu_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    owner = ctx.get("player")
    system = state.systems.get(str(ctx.get("position") or ""))
    return (
        owner in state.players and system is not None and owner in system.command_tokens
        and leaders.is_ready(state, _registry(), player_id, AGENT)
    )


# Cooperative agent (RULES.md 54.15): helps "that player" - requested, not pushed.
cooperative.register_pull(f"leaders:{AGENT}")


@on_event(
    GameEvent.COMMAND_TOKEN_PLACED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT), optional=True,
    condition=_zeu_ready, covers=f"leaders:{AGENT}", label="Z'eu: return the command token",
)
def zeu(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Z'eu: After any player's command token is placed in a system: You may exhaust this card to
    return that token to that player's reinforcements (każde położenie żetonu - aktywacja,
    Diplomacy, Signal Jamming... - F_naalu Z'eu ΩΩ 1; system pozostaje aktywowany)."""
    owner = str(ctx["player"])
    system = state.systems.get(str(ctx.get("position") or ""))
    if system is None or owner not in system.command_tokens:
        raise ValueError("That command token is no longer in the system.")
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT)
    command_tokens.remove_from_board(state, system, owner)


# ---------------------------------------------------------------------- M'aban (commander)


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have ground forces in or adjacent to the Mecatol Rex system (przestrzeń albo
    planeta)."""
    grid = board_graph.bound_grid() or grid_from_state(state, registry)
    mecatol = [pos for pos in state.systems if is_mecatol_position(state, pos)]
    near = {pos for m in mecatol for pos in (m, *grid.neighbors(m))}
    for position in near:
        system = state.systems.get(position)
        if system is None:
            continue
        zones = [system.space_units.get(player_id, {}),
                 *(by.get(player_id, {}) for by in system.planet_units.values())]
        if any(units.get(bt, 0) > 0 for units in zones for bt in _GROUND_FORCES):
            return True
    return False


@register(POINT_INFO_PEEK, HookSource(SOURCE_LEADER, COMMANDER), HookKind.FORBID,
          covers=f"leaders:{COMMANDER}")
def maban(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> tuple[str, ...]:
    """M'aban: At any time: You may look at your neighbors' hands of promissory notes and the top
    and bottom card of the agenda deck (podgląd stały - ``core/peek``; źródło lidera = odblokowany
    commander, także cudzy z Alliance)."""
    return (peek.NEIGHBORS_PROMISSORY, peek.AGENDA_TOP, peek.AGENDA_BOTTOM)


@on_event(
    GameEvent.COMPONENT_GAINED, Moment.WHEN, HookSource(SOURCE_LEADER, COMMANDER),
    where={"component": f"leaders:{COMMANDER}"}, label="M'aban: agenda deck",
)
def maban_unlocked(state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Talia agend powstaje leniwie - przy odblokowaniu M'aban zasiewamy ją, żeby podgląd
    pokazywał prawdziwą wierzchnią i spodnią kartę."""
    card_draw.ensure_agenda_deck(state, _registry())


# ----------------------------------------------------------------------- The Oracle (hero)


def _holders(state: GameState, player_id: str) -> list[str]:
    """Inni gracze z co najmniej 1 notką w ręce (w kolejności rozstrzygania)."""
    order = [p for p in state.seating_order if p in state.players] or sorted(state.players)
    return [p for p in order if p != player_id and state.players[p].private.promissory_notes]


def _oracle_ready(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return leaders.is_ready(state, _registry(), player_id, HERO) and bool(
        _holders(state, player_id)
    )


@on_event(
    GameEvent.PHASE, Moment.END, HookSource(SOURCE_LEADER, HERO), where={"phase": "status"},
    optional=True, condition=_oracle_ready, covers=f"leaders:{HERO}",
    label="The Oracle: C-Radium Geometry",
)
def oracle(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """The Oracle — C-Radium Geometry: At the end of the status phase: You may force each other
    player to give you 1 promissory note from their hand. If you do, purge this card.

    Każdy gracz sam wybiera, którą notkę oddaje (F_naalu the-oracle 1) - decyzja tego gracza."""
    from src.core import triggers  # lokalnie: hooki ładują się przed triggers

    holders = _holders(state, player_id)
    faction_components.pay_cost(state, _registry(), player_id, "leader", HERO)
    for target in holders:
        triggers.fire(
            state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "ability": f"leaders:{HERO}", "target": target},
        )


def _oracle_target(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def oracle_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options = [
        _note_option(state, registry, note)
        for note in dict.fromkeys(state.players[decider].private.promissory_notes)
    ]
    return [oi.choice("note", "Promissory note you give the Naalu player", options, always=True)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": f"leaders:{HERO}"}, decide=True, decider=_oracle_target,
    inputs=oracle_inputs, label="The Oracle: give a promissory note",
)
def oracle_give(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    giver = str(ctx["decider"])
    note = str(ctx.get("params", {}).get("note") or "")
    if note not in state.players[giver].private.promissory_notes:
        raise ValueError("Choose a promissory note from your hand.")
    promissory_notes.transfer(state, giver, player_id, note)


# --------------------------------------------------------------------- Mindsieve (przełom)


def _secondary_owner(state: GameState) -> str | None:
    window = state.pending_window
    if window is None or window.window_type is not WindowType.STRATEGY_SECONDARY:
        return None
    if window.context.get(strategic_action.HERO_KEY):  # bohater to nie akcja strategiczna
        return None
    return state.active_player_id


@faction_components.window_use("breakthrough", BREAKTHROUGH)
def _mindsieve_window(state: GameState, _registry_: StaticDataRegistry, player_id: str
                      ) -> str | None:
    window = state.pending_window
    owner = _secondary_owner(state)
    if window is None or owner is None:
        return "Mindsieve is used when you would resolve the secondary ability of a strategy card."
    if owner == player_id:
        return "Mindsieve works only on another player's strategy card."
    if player_id not in window.queue or player_id in window.responded:
        return "You already answered this strategy card."
    initiative = int(window.context.get("initiative") or 0)
    if strategic_action.secondary_without_token(state, player_id, initiative):
        return "You already resolve this secondary ability without a command token."
    if not state.players[player_id].private.promissory_notes:
        return "You have no promissory notes in your hand."
    return None


@register_effect_inputs(f"breakthroughs:{BREAKTHROUGH}")
def mindsieve_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Notka z RĘKI (nie ze strefy gry - F_naalu mindsieve 1)."""
    options = [
        _note_option(state, registry, note)
        for note in dict.fromkeys(state.players[player_id].private.promissory_notes)
    ]
    return [oi.choice("note", "Promissory note you give the strategy card's owner", options,
                      always=True)]


@register_effect(f"breakthroughs:{BREAKTHROUGH}")
def mindsieve(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Mindsieve: When you would resolve the secondary ability of another player's strategy card,
    you may give them a promissory note to resolve it without spending a command token.

    Oddanie notki to nie transakcja (F_naalu mindsieve 2)."""
    owner = _secondary_owner(state)
    note = str(params.get("note") or "")
    if owner is None or owner == player_id:
        raise ValueError("Mindsieve works only on another player's strategy card.")
    if note not in state.players[player_id].private.promissory_notes:
        raise ValueError("Choose a promissory note from your hand.")
    promissory_notes.transfer(state, player_id, owner, note)
    strategic_action.grant_no_cost(state, player_id, f"breakthroughs:{BREAKTHROUGH}")
