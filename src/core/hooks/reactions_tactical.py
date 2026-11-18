"""Karty reakcji: aktywacja systemu, ruch, tury, transakcje (RULES.md 53.5).

Wzorzec dla kart reakcji (ten plik jest REFERENCJĄ dla pozostałych ``reactions_*``):

1. **Okno** - ``@window_provider`` zwraca ``OpenWindow`` WYLICZONE ze stanu (bez mutacji).
2. **Adres karty** - domyślnie z tekstu okna; ``declare_reaction`` nadpisuje punkty/relację/warunek.
3. **Efekt** - ``@register_effect("action_cards:<id>")``; okno w ``params["__window"]``.
4. **Efekt trwały** ("w tej akcji taktycznej") - ``active_effects.add_effect`` + hook o źródle
   ``card_effect_source(id)`` na istniejącym punkcie silnika (``rules_hooks.POINT_*``).
5. **Formularz** - ``@register_effect_inputs`` tylko gdy karta wymaga decyzji gracza.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    board_reinforcements,
    command_tokens,
    economy,
    exhaust,
    fleet_pool,
    production,
    reaction_cards,
    rules_hooks,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, SystemState, TacticalStep
from src.core.hooks.action_card_inputs import (
    _choice,
    _multi,
    _option,
    _others,
    _planet_label,
    _player_label,
    _system_label,
)
from src.core.hooks.card_helpers import (
    other_player_param,
    place_from_reinforcements,
    system_of_planet,
    system_param,
)
from src.core.reaction_cards import (
    SELF,
    WINDOW_KEY,
    OpenWindow,
    card_effect_source,
    declare_reaction,
    window_provider,
)
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_MOVEMENT_ALPHA_BETA_ADJACENT,
    POINT_MOVEMENT_IGNORE_ANOMALIES,
    POINT_MOVEMENT_MOVE_VALUE,
    POINT_MOVEMENT_PASS_FOREIGN_SHIPS,
    POINT_PRODUCTION_COST,
    POINT_PRODUCTION_TOTAL_VALUE,
    POINT_SPACE_CANNON_OFFENSE_IMMUNE,
    HookKind,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

_FLANK_SPEED = ("fs1", "fs2", "fs3", "fs4")
_FLANK_SPEED_BONUS = 1  # „Apply +1 to the move value of each of your ships”


@window_provider
def after_activation(state: GameState) -> list[OpenWindow]:
    """Okno "po aktywacji systemu": aktywny system, krok ruchu, nikt jeszcze nie ruszył statków."""
    active = state.active_player_id
    if (
        active is None
        or state.active_system is None
        or state.tactical_step is not TacticalStep.MOVEMENT
        or state.tactical_moved
    ):
        return []
    ctx: dict[str, Any] = {"player": active, "position": state.active_system}
    return [
        OpenWindow(GameEvent.SYSTEM_ACTIVATED, Moment.WHEN, dict(ctx)),
        OpenWindow(GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, dict(ctx)),
    ]


def _register_flank_speed(card_id: str) -> None:
    """Flank Speed: Apply +1 to the move value of each of your ships during this tactical action."""

    def effect(
        state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
    ) -> None:
        # Klucz efektu = id konkretnej kopii karty, więc dwie zagrane kopie sumują się (+2).
        active_effects.add_effect(
            state, f"action_cards:{card_id}", Duration.TACTICAL_ACTION, owner=player_id
        )

    register_effect(f"action_cards:{card_id}")(effect)

    def bonus(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
        return _FLANK_SPEED_BONUS

    register(POINT_MOVEMENT_MOVE_VALUE, card_effect_source(card_id), HookKind.MODIFY)(bonus)


for _card in _FLANK_SPEED:
    _register_flank_speed(_card)


# ---------------------------------------------------------------------------------------------
# Pozostałe karty reakcji akcji taktycznej (RULES.md 53.5.b)
# ---------------------------------------------------------------------------------------------

_STRUCTURES = ("pds", "spacedock")  # „each PDS and space dock" (Infiltrate), „structures" (Decoy)
_GROUND_FORCES = ("infantry", "mech")
_WAR_MACHINE = ("war_machine1", "war_machine2", "war_machine3", "war_machine4", "war_machinell")
_WAR_MACHINE_KEY = "action_cards:war_machine"  # wspólny efekt: druga kopia nie sumuje (ruling)
_WAR_MACHINE_TOTAL_BONUS = 4  # „Apply +4 to the total PRODUCTION value of your units"
_WAR_MACHINE_COST_CUT = 1  # „reduce the combined cost of the produced units by 1"
_RALLY_TOKENS = 2  # „Place 2 command tokens from your reinforcements in your fleet pool"
_DECOY_MAX = 2  # „Remove up to 2 of your ground forces"
_FSB_SELF_TG = 3  # „Gain 3 trade goods"
_FSB_OTHER_TG = 1  # „Then, choose another player to gain 1 trade good"


def _active_position(window: OpenWindow) -> str:
    return str(window.ctx.get("position", ""))


def _ships_in(system: SystemState | None, player_id: str) -> int:
    """Liczba statków gracza w przestrzeni systemu."""
    if system is None:
        return 0
    return sum(n for n in system.space_units.get(player_id, {}).values() if n > 0)


def _units_in(system: SystemState | None, player_id: str) -> int:
    """Liczba WSZYSTKICH jednostek gracza w systemie (przestrzeń + planety)."""
    if system is None:
        return 0
    total = _ships_in(system, player_id)
    for by_player in system.planet_units.values():
        total += sum(n for n in by_player.get(player_id, {}).values() if n > 0)
    return total


def _structures_in(system: SystemState | None, player_id: str) -> int:
    """Liczba struktur (PDS, space dock) gracza na planetach systemu."""
    if system is None:
        return 0
    return sum(
        by_player.get(player_id, {}).get(base_type, 0)
        for by_player in system.planet_units.values()
        for base_type in _STRUCTURES
    )


@window_provider
def after_ships_moved(state: GameState) -> list[OpenWindow]:
    """Okno „po ruchu statków do aktywnego systemu": krok ruchu, aktywny gracz już ruszył (Rescue).

    Wyliczane z ``tactical_moved`` (ustawianego przez ``movement``), więc trwa do końca kroku ruchu.
    """
    active = state.active_player_id
    if (
        active is None
        or state.active_system is None
        or state.tactical_step is not TacticalStep.MOVEMENT
        or not state.tactical_moved
    ):
        return []
    ctx: dict[str, Any] = {"player": active, "position": state.active_system}
    return [OpenWindow(GameEvent.SHIPS_MOVED, Moment.AFTER, ctx)]


@window_provider
def production_step(state: GameState) -> list[OpenWindow]:
    """Okno „gdy twoje jednostki używają PRODUCTION": krok produkcji, zanim cokolwiek wyprodukowano.

    ⚠ ZAŁOŻENIE: „when" = przed pierwszym zamówieniem w tej produkcji (``production_used == 0``).
    """
    player = production.production_player(state)
    position = production.production_system(state)
    if player is None or position is None or state.production_used > 0:
        return []
    detached = production.standalone_grant(state) is not None
    if not detached and state.tactical_step is not TacticalStep.PRODUCTION:
        return []
    ctx: dict[str, Any] = {"player": player, "position": position}
    return [OpenWindow(GameEvent.PRODUCTION_USED, Moment.WHEN, ctx)]


@window_provider
def control_gained(state: GameState) -> list[OpenWindow]:
    """Okna „zdobywasz kontrolę nad planetą" (when) i „po zdobyciu" (after) ze śladu akcji.

    Ślad (``GameState.control_changes``) zostawia ``control.set_planet_control``; okno trwa, dopóki
    planeta jest u zdobywcy i trwa akcja taktyczna.
    """
    windows: list[OpenWindow] = []
    for change in state.control_changes:
        player, planet, position = change["player"], change["planet"], change["position"]
        system = state.systems.get(position or "")
        if player is None or planet is None or system is None:
            continue
        if system.planet_owners.get(planet) != player:
            continue
        ctx: dict[str, Any] = {
            "player": player,
            "planet": planet,
            "position": position,
            "previous": change["previous"],
        }
        windows.append(OpenWindow(GameEvent.PLANET_CONTROL_GAINED, Moment.WHEN, dict(ctx)))
        windows.append(OpenWindow(GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, dict(ctx)))
    return windows


# --- warunki zagrywalności -------------------------------------------------------------------


def _active_system(state: GameState, window: OpenWindow) -> SystemState | None:
    return state.systems.get(_active_position(window))


def _cond_anomaly(
    state: GameState, registry: StaticDataRegistry, _player: str, window: OpenWindow
) -> bool:
    """Harness Energy: aktywowany system jest anomalią."""
    system = _active_system(state, window)
    definition = registry.systems.get(system.system_id) if system is not None else None
    return definition is not None and bool(definition.anomalies)


def _cond_foreign_ships(
    state: GameState, _registry: StaticDataRegistry, player: str, window: OpenWindow
) -> bool:
    """Rally: w aktywnym systemie są statki innego gracza, a w rezerwie jest żeton."""
    system = _active_system(state, window)
    if system is None or command_tokens.reinforcements(state, player) < 1:
        return False
    return any(_ships_in(system, other) > 0 for other in state.players if other != player)


def _cond_own_cruiser(
    state: GameState, _registry: StaticDataRegistry, player: str, window: OpenWindow
) -> bool:
    """Upgrade: w aktywnym systemie jest twój krążownik (i jest czym go zastąpić)."""
    system = _active_system(state, window)
    return unit_ops.count_in_zone(system, "space", player, "cruiser") > 0 and bool(
        _dreadnought_sources(state, player)
    )


def _cond_own_token(
    state: GameState, _registry: StaticDataRegistry, player: str, window: OpenWindow
) -> bool:
    """Counterstroke: w aktywnym systemie leży TWÓJ żeton dowodzenia."""
    system = _active_system(state, window)
    return system is not None and player in system.command_tokens


def _owned_planets_in(system: SystemState | None, player: str) -> list[str]:
    if system is None:
        return []
    return [planet for planet, owner in system.planet_owners.items() if owner == player]


def _cond_structures(
    state: GameState, _registry: StaticDataRegistry, player: str, window: OpenWindow
) -> bool:
    """Decoy Operation: w aktywnym systemie masz struktury i planetę, a na planszy siły naziemne."""
    system = _active_system(state, window)
    return (
        _structures_in(system, player) > 0
        and bool(_owned_planets_in(system, player))
        and bool(_ground_force_options(state, player))
    )


def _cond_own_units(
    state: GameState, _registry: StaticDataRegistry, player: str, window: OpenWindow
) -> bool:
    """Forward Supply Base: w aktywnym systemie stoją twoje jednostki."""
    return _units_in(_active_system(state, window), player) > 0


def _cond_rescue(
    state: GameState, _registry: StaticDataRegistry, player: str, window: OpenWindow
) -> bool:
    """Rescue: w aktywnym systemie stoją twoje statki i masz statek do przeniesienia."""
    system = _active_system(state, window)
    return _ships_in(system, player) > 0 and bool(_rescue_options(state, player, window))


def _cond_war_machine(
    state: GameState, registry: StaticDataRegistry, player: str, window: OpenWindow
) -> bool:
    """War Machine: gracz ma producenta w systemie, a ten efekt nie działa już w tej produkcji."""
    if active_effects.has_effect(state, player, _WAR_MACHINE_KEY):
        return False  # ruling: druga War Machine w tej samej produkcji nie sumuje się
    return bool(production.producers(state, registry, player, _active_position(window)))


def _cond_reparations(
    state: GameState, _registry: StaticDataRegistry, player: str, window: OpenWindow
) -> bool:
    """Reparations: planeta, którą ZDOBYŁ inny gracz, była TWOJA (kontrolowałeś ją)."""
    return window.ctx.get("previous") == player


declare_reaction("harness", condition=_cond_anomaly)
declare_reaction("rally", subject=SELF, condition=_cond_foreign_ships)
declare_reaction("upgrade", condition=_cond_own_cruiser)
declare_reaction("counterstroke", condition=_cond_own_token)
declare_reaction("decoy", condition=_cond_structures)
declare_reaction("fsb", condition=_cond_own_units)
declare_reaction("rescue", condition=_cond_rescue)
declare_reaction(*_WAR_MACHINE, condition=_cond_war_machine)
declare_reaction("reparations", condition=_cond_reparations)


# --- efekty trwałe: Lost Star Chart, Nav Suite, Silence of Space, Solar Flare -----------------


def _register_duration_effect(card_id: str) -> None:
    """Rejestruje efekt karty, który tylko zakłada efekt trwały na czas tej akcji taktycznej."""

    def effect(
        state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
    ) -> None:
        active_effects.add_effect(
            state, f"action_cards:{card_id}", Duration.TACTICAL_ACTION, owner=player_id
        )

    register_effect(f"action_cards:{card_id}")(effect)


def _always(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return True


# Lost Star Chart: „During this tactical action, systems that contain alpha and beta wormholes are
# adjacent to each other." Hook w logice ruchu (``movement._neighbors_for_move``).
_register_duration_effect("lost_star")
register(
    POINT_MOVEMENT_ALPHA_BETA_ADJACENT, card_effect_source("lost_star"), HookKind.PERMIT
)(_always)

# Nav Suite: „During the 'Movement' step of this tactical action, ignore the effect of anomalies."
_register_duration_effect("nav_suite")


def _movement_step_only(state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return state.tactical_step is TacticalStep.MOVEMENT


register(
    POINT_MOVEMENT_IGNORE_ANOMALIES, card_effect_source("nav_suite"), HookKind.PERMIT
)(_movement_step_only)

# Solar Flare: „During the 'Movement' step of this tactical action, other players cannot use SPACE
# CANNON against your ships." ⚠ Wg rulingu dotyczy Space Cannon OFFENSE (obrona w inwazji działa).
_register_duration_effect("solar_flare")
register(
    POINT_SPACE_CANNON_OFFENSE_IMMUNE, card_effect_source("solar_flare"), HookKind.PERMIT
)(_always)


@register_effect("action_cards:silence_space")
def silence_space(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """In The Silence Of Space: Choose 1 system. During this tactical action, your ships in the
    chosen system can move through systems that contain other players' ships.
    """
    system = system_param(state, params)
    if _ships_in(system, player_id) <= 0:
        raise ValueError("Choose a system that contains 1 or more of your ships ('position').")
    active_effects.add_effect(
        state,
        "action_cards:silence_space",
        Duration.TACTICAL_ACTION,
        owner=player_id,
        data={"position": system.position},
    )


def _silence_space_pass(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Przelot przez obce statki dotyczy tylko statków startujących z wybranego systemu."""
    source = ctx.get("from")
    return any(
        effect.data.get("position") == source
        for effect in active_effects.effects_for(state, player_id, "action_cards:silence_space")
    )


register(
    POINT_MOVEMENT_PASS_FOREIGN_SHIPS, card_effect_source("silence_space"), HookKind.PERMIT
)(_silence_space_pass)


@register_effect_inputs("action_cards:silence_space")
def silence_space_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    # ⚠ ZAŁOŻENIE: karta pozwala wskazać dowolny system; oferujemy tylko te z własnymi statkami.
    options = [
        _option(s.position, _system_label(registry, s))
        for s in state.systems.values()
        if _ships_in(s, player_id) > 0
    ]
    return [_choice("position", "System with your ships", options)]


# --- „po aktywacji": Harness Energy, Rally, Upgrade ------------------------------------------


@register_effect("action_cards:harness")
def harness_energy(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Harness Energy: Replenish your commodities."""
    economy.replenish_commodities(state, player_id)


@register_effect("action_cards:rally")
def rally(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Rally: Place 2 command tokens from your reinforcements in your fleet pool.

    ⚠ ZAŁOŻENIE: przy mniej niż 2 żetonach w rezerwie kładziemy tyle, ile jest (min. 1).
    """
    amount = min(_RALLY_TOKENS, command_tokens.reinforcements(state, player_id))
    if amount < 1:
        raise ValueError("You have no command tokens in your reinforcements.")
    command_tokens.gain_from_reinforcements(state, player_id, {"fleet": amount})


def _dreadnought_sources(state: GameState, player_id: str) -> list[str]:
    """Skąd można wziąć dreadnought dla Upgrade: ``""`` = rezerwa, inaczej pozycja na planszy.

    Ruling: gdy w rezerwie nie ma dreadnoughta, można zdjąć go z systemu BEZ własnego żetonu.
    """
    if production.reinforcements_left(state, player_id, "dreadnought") != 0:
        return [""]
    return [
        s.position
        for s in state.systems.values()
        if player_id not in s.command_tokens
        and unit_ops.count_in_zone(s, "space", player_id, "dreadnought") > 0
    ]


@register_effect("action_cards:upgrade")
def upgrade(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Upgrade: Replace 1 of your cruisers in that system with 1 dreadnought from your
    reinforcements.
    """
    window = params.get(WINDOW_KEY)
    position = str(window["ctx"]["position"]) if isinstance(window, Mapping) else ""
    system = state.systems.get(position)
    if unit_ops.count_in_zone(system, "space", player_id, "cruiser") < 1 or system is None:
        raise ValueError("You have no cruiser in the active system.")
    source = str(params.get("source", ""))
    if source not in _dreadnought_sources(state, player_id):
        raise ValueError("Choose where the dreadnought comes from ('source').")
    unit_ops.remove_units(state, system, "space", player_id, "cruiser", 1, UnitCause.REMOVED)
    if source:
        # Ruling: dreadnought zdjęty z planszy trafia do systemu NIEuszkodzony.
        unit_ops.remove_units(
            state, state.systems[source], "space", player_id, "dreadnought", 1, UnitCause.REMOVED
        )
        unit_ops.place_units(state, system, "space", player_id, "dreadnought", 1, UnitCause.PLACED)
    else:
        place_from_reinforcements(state, system, "space", player_id, "dreadnought", 1)


@register_effect_inputs("action_cards:upgrade")
def upgrade_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [
        _option(source, _system_label(registry, state.systems[source]))
        if source
        else _option("", "Reinforcements", option_id="reinforcements")
        for source in _dreadnought_sources(state, player_id)
    ]
    return [_choice("source", "Dreadnought from", options)]


# --- „po aktywacji przez innego gracza": Counterstroke, Decoy, Forward Supply Base ------------


def _window_system(state: GameState, params: Mapping[str, Any]) -> SystemState:
    window = params.get(WINDOW_KEY)
    position = str(window["ctx"]["position"]) if isinstance(window, Mapping) else ""
    system = state.systems.get(position)
    if system is None:
        raise ValueError("There is no active system.")
    return system


@register_effect("action_cards:counterstroke")
def counterstroke(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Counterstroke: Return that command token to your tactic pool."""
    system = _window_system(state, params)
    command_tokens.return_board_token_to_pool(state, system, player_id, "tactical")


def _ground_force_options(state: GameState, player_id: str) -> list[tuple[str, str, str, int]]:
    """Siły naziemne gracza na planszy: ``(pozycja, planeta, typ, liczba)``."""
    found: list[tuple[str, str, str, int]] = []
    for system in state.systems.values():
        for planet, by_player in system.planet_units.items():
            for base_type in _GROUND_FORCES:
                count = by_player.get(player_id, {}).get(base_type, 0)
                if count > 0:
                    found.append((system.position, planet, base_type, count))
    return found


@register_effect("action_cards:decoy")
def decoy_operation(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Decoy Operation: Remove up to 2 of your ground forces from the game board and place them on a
    planet you control in the active system.
    """
    active = _window_system(state, params)
    planet = params.get("planet")
    if not isinstance(planet, str) or planet not in _owned_planets_in(active, player_id):
        raise ValueError("Choose a planet you control in the active system ('planet').")
    units = params.get("units")
    if not isinstance(units, list) or not 1 <= len(units) <= _DECOY_MAX:
        raise ValueError("Choose 1 or 2 of your ground forces ('units').")
    chosen: list[tuple[str, str]] = []
    for item in units:
        source = item.get("planet") if isinstance(item, Mapping) else None
        base_type = item.get("base_type") if isinstance(item, Mapping) else None
        if not isinstance(source, str) or base_type not in _GROUND_FORCES:
            raise ValueError("Each unit needs 'planet' and a ground force 'base_type'.")
        chosen.append((source, str(base_type)))
    for source, base_type in set(chosen):
        have = unit_ops.count_in_zone(system_of_planet(state, source), source, player_id, base_type)
        if have < chosen.count((source, base_type)):
            raise ValueError(f"You do not have that many {base_type} on {source}.")
    for source, base_type in chosen:
        # Ruling: uszkodzony mech zostaje uszkodzony (transfer przenosi uszkodzenia).
        unit_ops.transfer_units(
            state, system_of_planet(state, source), source, active, planet, player_id, base_type, 1
        )


@register_effect_inputs("action_cards:decoy")
def decoy_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    window = reaction_cards.window_for(state, rules_hooks.bound_registry(), player_id, "decoy")
    active = state.systems.get(_active_position(window)) if window is not None else None
    planets = [
        _option(p, _planet_label(state, registry, p)) for p in _owned_planets_in(active, player_id)
    ]
    units = [
        _option(
            {"planet": planet, "base_type": base_type},
            f"{fleet_pool.unit_name(state, registry, player_id, base_type)} "
            f"on {_planet_label(state, registry, planet)} ({index + 1})",
            option_id=f"{planet}:{base_type}:{index}",
            meta=oi.unit_at(state, player_id, base_type, planet=planet),
        )
        for _position, planet, base_type, count in _ground_force_options(state, player_id)
        for index in range(min(count, _DECOY_MAX))
    ]
    return [
        _choice("planet", "Planet you control in the active system", planets),
        _multi("units", "Ground forces to move", units, 1, _DECOY_MAX),
    ]


@register_effect("action_cards:fsb")
def forward_supply_base(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Forward Supply Base: Gain 3 trade goods. Then, choose another player to gain 1 trade good."""
    other = other_player_param(state, player_id, params)
    economy.gain_trade_goods(state, player_id, _FSB_SELF_TG)
    economy.gain_trade_goods(state, other, _FSB_OTHER_TG)


@register_effect_inputs("action_cards:fsb")
def fsb_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [
        _option(pid, _player_label(state, registry, pid)) for pid in _others(state, player_id)
    ]
    return [_choice("player", "Player who gains 1 trade good", options)]


# --- Rescue -------------------------------------------------------------------------------


def _rescue_options(
    state: GameState, player_id: str, window: OpenWindow
) -> list[tuple[str, str]]:
    """Statki gracza do przeniesienia: ``(pozycja, typ)`` z systemów bez jego żetonu dowodzenia."""
    active = _active_position(window)
    return [
        (system.position, base_type)
        for system in state.systems.values()
        if system.position != active and player_id not in system.command_tokens
        for base_type, count in sorted(system.space_units.get(player_id, {}).items())
        if count > 0 and is_space_unit(base_type)
    ]


@register_effect("action_cards:rescue")
def rescue(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Rescue: You may move 1 of your ships into the active system from any system that does not
    contain one of your command tokens.

    ⚠ ZAŁOŻENIE: ruch nie sprawdza zasięgu ani przejezdności (karta nie jest „ruchem" o wartości
    ruchu); rzut usunięcia ze studni grawitacyjnej (ruling) nie jest jeszcze egzekwowany.
    """
    window_raw = params.get(WINDOW_KEY)
    window = OpenWindow(
        GameEvent.SHIPS_MOVED, Moment.AFTER, dict(window_raw["ctx"])
    ) if isinstance(window_raw, Mapping) else None
    if window is None:
        raise ValueError("There is no open window for this card right now.")
    source_pos, base_type = params.get("from"), params.get("base_type")
    if (source_pos, base_type) not in _rescue_options(state, player_id, window):
        raise ValueError("Choose one of your ships in a system without your command token.")
    active = state.systems[_active_position(window)]
    source = state.systems[str(source_pos)]
    unit_ops.transfer_units(state, source, "space", active, "space", player_id, str(base_type), 1)


@register_effect_inputs("action_cards:rescue")
def rescue_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    window = reaction_cards.window_for(state, rules_hooks.bound_registry(), player_id, "rescue")
    found = _rescue_options(state, player_id, window) if window is not None else []
    options = [
        _option(
            {"from": position, "base_type": base_type},
            f"{fleet_pool.unit_name(state, registry, player_id, base_type)} "
            f"from {_system_label(registry, state.systems[position])}",
            option_id=f"{position}:{base_type}",
        )
        for position, base_type in found
    ]
    return [_choice("ship", "Ship to move into the active system", options, merge=True)]


# --- War Machine -----------------------------------------------------------------------------


def _register_war_machine(card_id: str) -> None:
    """War Machine: Apply +4 to the total PRODUCTION value of your units and reduce the combined
    cost of the produced units by 1. (Każda kopia zakłada ten sam efekt - ruling: nie sumują się.)
    """

    def effect(
        state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
    ) -> None:
        if active_effects.has_effect(state, player_id, _WAR_MACHINE_KEY):
            raise ValueError("War Machine is already in effect for this use of PRODUCTION.")
        scope = Duration.TACTICAL_ACTION if state.tactical_step is not None else Duration.TURN
        active_effects.add_effect(state, _WAR_MACHINE_KEY, scope, owner=player_id)

    register_effect(f"action_cards:{card_id}")(effect)


for _card in _WAR_MACHINE:
    _register_war_machine(_card)


def _war_machine_total(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    return _WAR_MACHINE_TOTAL_BONUS


def _war_machine_cost(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    return -_WAR_MACHINE_COST_CUT


register(
    POINT_PRODUCTION_TOTAL_VALUE, card_effect_source("war_machine"), HookKind.MODIFY
)(_war_machine_total)
register(POINT_PRODUCTION_COST, card_effect_source("war_machine"), HookKind.MODIFY)(
    _war_machine_cost
)


# --- Infiltrate / Reparations ---------------------------------------------------------------


def _gained_planet(params: Mapping[str, Any], matching: list[OpenWindow]) -> OpenWindow:
    """Okno zdobycia planety wskazane parametrem ``planet`` (jedyne okno - domyślne)."""
    planet = params.get("planet")
    if planet is None and len(matching) == 1:
        return matching[0]
    for window in matching:
        if window.ctx.get("planet") == planet:
            return window
    raise ValueError("Choose the planet whose control was just gained ('planet').")


@register_effect("action_cards:infiltrate")
def infiltrate(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Infiltrate: Replace each PDS and space dock that is on that planet with a matching unit from
    your reinforcements.

    C_action_cards: gdy w rezerwie brakuje struktury, gracz może zdjąć strukturę tego typu z
    systemu bez swojego żetonu - wybór osobno dla każdej struktury (``sources:<typ>``,
    ``core.board_reinforcements``). Struktury własne gracza są pomijane.

    Inwazja niszczy cudze struktury w chwili przejęcia (R_invasion) - karta „when you gain
    control” wymienia też te zniszczone wtedy struktury (ślad ``control_changes[...]["destroyed"]``,
    zużywany raz: drugi Infiltrate / Assimilate wymieniają 0 - C_action_cards).
    """
    matching = reaction_cards.matching_windows(state, registry, player_id, "infiltrate")
    window = _gained_planet(params, matching)
    planet = str(window.ctx["planet"])
    system = system_of_planet(state, planet)
    replaced = _infiltrate_targets(state, player_id, planet)
    destroyed = _destroyed_on_capture(state, player_id, planet)
    takes: list[tuple[str, str]] = []
    for base_type, count in _infiltrate_totals(replaced + destroyed).items():
        short = _infiltrate_shortfall(state, player_id, base_type, count)
        picks = [str(p) for p in params.get(f"sources:{base_type}") or []]
        if len(picks) < short:
            raise ValueError(
                f"Not enough {base_type} in reinforcements - choose {short} on the board "
                "(in systems without your command token)."
            )
        takes += [(base_type, src) for src in picks[:short]]
    for base_type, source in takes:
        board_reinforcements.take_from_board(state, player_id, base_type, source)
    for owner, base_type, count in replaced:
        unit_ops.remove_units(state, system, planet, owner, base_type, count, UnitCause.REMOVED)
        place_from_reinforcements(state, system, planet, player_id, base_type, count)
    for _owner, base_type, count in destroyed:
        place_from_reinforcements(state, system, planet, player_id, base_type, count)
    for change in state.control_changes:
        if change.get("planet") == planet and change.get("player") == player_id:
            change["destroyed"] = {}


def _infiltrate_targets(
    state: GameState, player_id: str, planet: str
) -> list[tuple[str, str, int]]:
    """Cudze struktury na planecie: ``(właściciel, typ, ile)``."""
    system = system_of_planet(state, planet)
    replaced: list[tuple[str, str, int]] = []
    for owner in list(system.planet_units.get(planet, {})):
        if owner == player_id:
            continue
        for base_type in _STRUCTURES:
            count = unit_ops.count_in_zone(system, planet, owner, base_type)
            if count:
                replaced.append((owner, base_type, count))
    return replaced


def _destroyed_on_capture(
    state: GameState, player_id: str, planet: str
) -> list[tuple[str, str, int]]:
    """Cudze struktury zniszczone przy przejęciu planety w tej akcji (ślad inwazji)."""
    found: list[tuple[str, str, int]] = []
    for change in state.control_changes:
        if change.get("planet") != planet or change.get("player") != player_id:
            continue
        for owner, by_type in sorted(dict(change.get("destroyed") or {}).items()):
            for base_type in _STRUCTURES:
                if int(by_type.get(base_type, 0)) > 0:
                    found.append((owner, base_type, int(by_type[base_type])))
    return found


def _infiltrate_totals(replaced: list[tuple[str, str, int]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for _owner, base_type, count in replaced:
        totals[base_type] = totals.get(base_type, 0) + count
    return totals


def _infiltrate_shortfall(state: GameState, player_id: str, base_type: str, count: int) -> int:
    left = production.reinforcements_left(state, player_id, base_type)
    return 0 if left is None else max(0, count - left)


@register_effect_inputs("action_cards:infiltrate")
def infiltrate_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    matching = reaction_cards.matching_windows(
        state, rules_hooks.bound_registry(), player_id, "infiltrate"
    )
    options = [
        _option(w.ctx["planet"], _planet_label(state, registry, str(w.ctx["planet"])))
        for w in matching
    ]
    inputs = [
        _choice(
            "planet",
            "Planet you just gained control of",
            options,
            hint="Pick the planet you just took control of that the card applies to.",
        )
    ]
    # Pusta rezerwa (C_action_cards): skąd zdjąć brakujące struktury - osobno dla każdej.
    for base_type in _STRUCTURES:
        short = max(
            (
                _infiltrate_shortfall(state, player_id, base_type, total)
                for w in matching
                for bt, total in _infiltrate_totals(
                    _infiltrate_targets(state, player_id, str(w.ctx["planet"]))
                    + _destroyed_on_capture(state, player_id, str(w.ctx["planet"]))
                ).items()
                if bt == base_type
            ),
            default=0,
        )
        sources = board_reinforcements.source_options(state, registry, player_id, base_type)
        if short and sources:
            name = "PDS" if base_type == "pds" else "space dock"
            inputs.append(_multi(
                f"sources:{base_type}", f"No {name} left - take {short} from the board",
                [_option(v, label) for v, label in sources], 0, min(short, len(sources)),
            ))
    return inputs


@register_effect("action_cards:reparations")
def reparations(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Reparations: Exhaust 1 planet that player controls and ready 1 planet you control.

    Ruling: kartę można zagrać także bez wyczerpanej planety albo gdy zdobywca nie ma gotowej
    planety - wtedy odpowiedni człon pomijamy (pusty parametr).
    """
    matching = reaction_cards.matching_windows(state, registry, player_id, "reparations")
    window = _gained_planet(params, matching)
    taker = str(window.ctx["player"])
    to_exhaust = str(params.get("exhaust_planet") or "")
    to_ready = str(params.get("ready_planet") or "")
    if to_exhaust:
        if to_exhaust not in _ready_planets(state, taker):
            raise ValueError("Choose a ready planet controlled by that player ('exhaust_planet').")
    elif _ready_planets(state, taker):
        raise ValueError("Choose a ready planet controlled by that player ('exhaust_planet').")
    if to_ready:
        if to_ready not in _exhausted_planets(state, player_id):
            raise ValueError("Choose one of your exhausted planets ('ready_planet').")
    elif _exhausted_planets(state, player_id):
        raise ValueError("Choose one of your exhausted planets ('ready_planet').")
    if to_exhaust:
        exhaust.exhaust_planets(state, taker, [to_exhaust])
    if to_ready:
        exhaust.ready_planets(state, player_id, [to_ready])


def _controlled(state: GameState, player_id: str) -> list[str]:
    return [
        planet
        for system in state.systems.values()
        for planet, owner in system.planet_owners.items()
        if owner == player_id
    ]


def _ready_planets(state: GameState, player_id: str) -> list[str]:
    exhausted = set(state.players[player_id].exhausted_planets)
    return [p for p in _controlled(state, player_id) if p not in exhausted]


def _exhausted_planets(state: GameState, player_id: str) -> list[str]:
    exhausted = set(state.players[player_id].exhausted_planets)
    return [p for p in _controlled(state, player_id) if p in exhausted]


@register_effect_inputs("action_cards:reparations")
def reparations_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    matching = reaction_cards.matching_windows(
        state, rules_hooks.bound_registry(), player_id, "reparations"
    )
    changed = [
        _option(w.ctx["planet"], _planet_label(state, registry, str(w.ctx["planet"])))
        for w in matching
    ]
    takers = {str(w.ctx["player"]) for w in matching}
    theirs = [p for taker in sorted(takers) for p in _ready_planets(state, taker)]
    mine = _exhausted_planets(state, player_id)
    none = _option("", "None available", option_id="none")
    return [
        _choice("planet", "Planet that was taken from you", changed),
        _choice(
            "exhaust_planet",
            "Planet to exhaust (the taker's)",
            [_option(p, _planet_label(state, registry, p)) for p in theirs] or [none],
        ),
        _choice(
            "ready_planet",
            "Planet of yours to ready",
            [_option(p, _planet_label(state, registry, p)) for p in mine] or [none],
        ),
    ]
