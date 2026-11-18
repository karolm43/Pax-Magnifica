"""Karty reakcji: inwazja, Space Cannon, Bombardment (RULES.md 53.5.d).

Okna (WYLICZANE ze stanu, bez mutacji):

* **Początek inwazji** (``INVASION`` / ``START``) - inwazja przed rozstrzygnięciem Bombardment
  i przed jakimkolwiek zaangażowaniem sił (podkrok BOMBARDMENT albo świeży COMMIT, gdy silnik
  pominął Bombardment): Blitz, Bunker, Disable.
* **Po zaangażowaniu** (``UNITS_COMMITTED`` / ``AFTER``) - podkrok COMMIT z ``last_commit``:
  Ghost Squad, Parley.
* **Przed przypisaniem trafień Space Cannon** (``HITS_ASSIGNED`` / ``BEFORE``) - trafienia
  Space Cannon Offense (okno ``SPACE_CANNON``) albo Defense (``defense_pending``) czekają na
  przypisanie: Maneuvering Jets.
* **Po rzucie** (``UNIT_ABILITY_USED`` / ``AFTER``) - rzut Bombardment / Space Cannon, którego
  trafienia wciąż czekają na przypisanie: Scramble Frequency.
* **Po ruchu statków** (``SHIPS_MOVED`` / ``AFTER``) - okno z ``reactions_tactical`` (krok
  MOVEMENT po pierwszym ruchu): Experimental Battlestation.

Efekty „do końca inwazji” to ``active_effects`` z ``Duration.INVASION`` (wygasają na
``INVASION`` / ``END`` emitowanym przez ``invasion.clear_invasion`` i koniec akcji taktycznej).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    board_graph,
    invasion,
    rules_hooks,
    space_cannon,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.components import ComponentCategory
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
    SystemState,
)
from src.core.hooks.action_card_inputs import (
    Input,
    _choice,
    _multi,
    _option,
    _planet_label,
)
from src.core.reaction_cards import (
    OTHER,
    SELF,
    OpenWindow,
    ReactionCondition,
    card_effect_source,
    declare_reaction,
    window_for,
    window_provider,
)
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_BOMBARDMENT_GRANTED,
    POINT_BOMBARDMENT_ROLL_MODIFIER,
    POINT_PDS_DISABLED,
    HookKind,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.state_grid import grid_from_state
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

_MJETS = ("mjets1", "mjets2", "mjets3", "mjets4")

# Rodzaje rzutów w kontekście okien (``ctx["kind"]`` / ``ctx["scramble"]``).
KIND_OFFENSE = "offense"
KIND_DEFENSE = "defense"
KIND_BOMBARDMENT = "bombardment"


# ----------------------------------------------------------------------------- pomocnicze


def _card_text(card_id: str) -> str:
    """Tekst karty akcji z assetów (liczby kart czytamy stąd, nie z pamięci)."""
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("The static data registry is not bound.")
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
    if card is None:
        raise ValueError(f"Unknown action card: {card_id}")
    return " ".join(card.texts.values())


def _number(card_id: str, pattern: str, group: int = 1) -> int:
    """Liczba z tekstu karty (regex z grupą); brak dopasowania = błąd danych."""
    match = re.search(pattern, _card_text(card_id), flags=re.IGNORECASE)
    if match is None:
        raise ValueError(f"Cannot read the value of {card_id} from the card text.")
    return int(match.group(group))


def _controlled_in(system: SystemState | None, player_id: str) -> list[str]:
    """Planety systemu kontrolowane przez gracza (w kolejności zapisu)."""
    if system is None:
        return []
    return [p for p, owner in system.planet_owners.items() if owner == player_id]


def _ground(system: SystemState, planet: str, player_id: str) -> dict[str, int]:
    units = system.planet_units.get(planet, {}).get(player_id, {})
    return {bt: n for bt, n in units.items() if n > 0 and bt in invasion.GROUND_FORCES}


def _adjacent(state: GameState, registry: StaticDataRegistry, position: str) -> set[str]:
    """Pozycje sąsiadujące z ``position``: z podpiętej siatki, a bez niej z siatki ze stanu."""
    near = board_graph.adjacent_positions(position)
    if near:
        return near
    return set(grid_from_state(state, registry).neighbors(position))


def _reopen_bombardment(state: GameState, registry: StaticDataRegistry) -> None:
    """Przywraca podkrok BOMBARDMENT, gdy efekt karty DOPIERO umożliwił bombardowanie.

    Silnik pomija Bombardment, gdy nikt nie może bombardować (nowy podkrok to COMMIT). Karta
    zagrana na początku inwazji (Blitz, Disable) może to zmienić - wtedy wracamy, o ile nic
    jeszcze nie wylądowało ani nie zbombardowało.
    """
    inv = state.invasion
    if inv is None or inv.phase is not InvasionPhase.COMMIT:
        return
    if inv.committed or inv.bombarded or inv.log:
        return
    if invasion.bombard_groups(state, registry):
        inv.phase = InvasionPhase.BOMBARDMENT


# --------------------------------------------------------------------------- dostawcy okien


def _start_open(state: GameState) -> bool:
    inv = state.invasion
    if inv is None or inv.bombarded or inv.log or inv.bombard_pending or inv.committed:
        return False
    return inv.phase in (InvasionPhase.BOMBARDMENT, InvasionPhase.COMMIT)


@window_provider
def invasion_windows(state: GameState) -> list[OpenWindow]:
    """Okna inwazji: początek, po zaangażowaniu, trafienia Space Cannon/Bombardment po rzucie."""
    inv = state.invasion
    if inv is None:
        return []
    base: dict[str, Any] = {"player": inv.attacker, "position": inv.position}
    windows: list[OpenWindow] = []
    if _start_open(state):
        windows.append(OpenWindow(GameEvent.INVASION, Moment.START, dict(base)))
    if inv.phase is InvasionPhase.COMMIT and inv.last_commit:
        ctx = {**base, "planets": sorted(inv.last_commit)}
        windows.append(OpenWindow(GameEvent.UNITS_COMMITTED, Moment.AFTER, ctx))
    if inv.phase is InvasionPhase.BOMBARDMENT and inv.bombard_pending:
        windows.append(
            OpenWindow(
                GameEvent.UNIT_ABILITY_USED, Moment.AFTER,
                {**base, "ability": "bombardment", "scramble": KIND_BOMBARDMENT},
            )
        )
    if inv.phase is InvasionPhase.SPACE_CANNON_DEFENSE and inv.defense_pending:
        windows.extend(_defense_windows(state))
    return windows


def _defense_windows(state: GameState) -> list[OpenWindow]:
    inv = state.invasion
    assert inv is not None
    windows: list[OpenWindow] = []
    rollers: list[str] = []
    for planet in sorted(inv.defense_pending):
        try:
            roller = invasion.defense_roller(state, planet)
        except (ValueError, KeyError):
            continue
        rollers.append(roller)
        windows.append(
            OpenWindow(
                GameEvent.HITS_ASSIGNED, Moment.BEFORE,
                {
                    "player": roller, "target": inv.attacker, "planet": planet,
                    "position": inv.position, "ability": "space_cannon", "kind": KIND_DEFENSE,
                },
            )
        )
    if rollers:
        windows.append(
            OpenWindow(
                GameEvent.UNIT_ABILITY_USED, Moment.AFTER,
                {
                    "player": rollers[0], "position": inv.position, "ability": "space_cannon",
                    "scramble": KIND_DEFENSE,
                },
            )
        )
    return windows


@window_provider
def unit_ability_roll_windows(state: GameState) -> list[OpenWindow]:
    """Okna „when … units make a roll for a unit ability” PRZED rzutem Space Cannon (Offense,
    Defense) i Bombardment (Strike Wing Ambuscade, RULES.md 62.11). AFB: ``reactions_combat``."""
    windows: list[OpenWindow] = []
    position = state.active_system or ""
    window = state.pending_window
    if (
        space_cannon.is_open(state)
        and space_cannon.pending_hits(state) is None
        and window is not None
        and window.current_responder
    ):
        windows.append(
            OpenWindow(
                GameEvent.UNIT_ABILITY_USED, Moment.WHEN,
                {"player": window.current_responder, "position": position,
                 "ability": "space_cannon", "kind": KIND_OFFENSE},
            )
        )
    inv = state.invasion
    if inv is None:
        return windows
    base = {"position": inv.position}
    if inv.phase is InvasionPhase.BOMBARDMENT and not inv.bombarded:
        windows.append(
            OpenWindow(
                GameEvent.UNIT_ABILITY_USED, Moment.WHEN,
                {**base, "player": inv.attacker, "ability": "bombardment"},
            )
        )
    registry = rules_hooks.bound_registry()
    if inv.phase is InvasionPhase.SPACE_CANNON_DEFENSE and registry is not None:
        system = state.systems.get(inv.position)
        try:
            open_planets = invasion.undefended_open(state, registry)
        except (ValueError, KeyError):
            open_planets = []
        rollers = sorted({
            pid
            for planet in open_planets
            for pid in (system.planet_units.get(planet, {}) if system else {})
            if pid != inv.attacker
        })
        for roller in rollers:
            windows.append(
                OpenWindow(
                    GameEvent.UNIT_ABILITY_USED, Moment.WHEN,
                    {**base, "player": roller, "ability": "space_cannon", "kind": KIND_DEFENSE},
                )
            )
    return windows


@window_provider
def offense_windows(state: GameState) -> list[OpenWindow]:
    """Okna Space Cannon Offense: trafienia po rzucie czekają na przypisanie strat."""
    pending = space_cannon.pending_hits(state)
    if pending is None:
        return []
    position = state.active_system or ""
    return [
        OpenWindow(
            GameEvent.HITS_ASSIGNED, Moment.BEFORE,
            {
                "player": pending.roller, "target": pending.target, "position": position,
                "ability": "space_cannon", "kind": KIND_OFFENSE,
            },
        ),
        OpenWindow(
            GameEvent.UNIT_ABILITY_USED, Moment.AFTER,
            {
                "player": pending.roller, "position": position, "ability": "space_cannon",
                "scramble": KIND_OFFENSE,
            },
        ),
    ]


# Okno „po ruchu statków” (SHIPS_MOVED / AFTER) dostarcza ``reactions_tactical.after_ships_moved``.


# -------------------------------------------------------------------------------- warunki


def _blitz_ready(
    state: GameState, registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    """Atakujący ma w aktywnym systemie niefighterowy statek bez własnego Bombardment."""
    inv = state.invasion
    system = state.systems.get(inv.position) if inv is not None else None
    if inv is None or system is None:
        return False
    for base_type, count in system.space_units.get(player_id, {}).items():
        if count <= 0 or base_type == "fighter" or not is_space_unit(base_type):
            continue
        unit = invasion.unit_variant(state, registry, player_id, base_type)
        if unit is not None and not (unit.bombard_hits_on and unit.bombard_hits_on > 0):
            return True
    return False


def _bunker_ready(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    """Gracz kontroluje planetę aktywnego systemu (cel Bombardment)."""
    inv = state.invasion
    return inv is not None and bool(_controlled_in(state.systems.get(inv.position), player_id))


def _disable_ready(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    """W systemie stoi PDS przeciwnika (gracza innego niż zagrywający)."""
    inv = state.invasion
    system = state.systems.get(inv.position) if inv is not None else None
    if system is None:
        return False
    return any(
        pid != player_id and units.get("pds", 0) > 0
        for by_player in system.planet_units.values()
        for pid, units in by_player.items()
    )


def _ghost_ready(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    """Gracz kontroluje planetę z zaangażowaniem i jeszcze jedną w aktywnym systemie."""
    system = state.systems.get(str(window.ctx.get("position")))
    mine = _controlled_in(system, player_id)
    committed = set(window.ctx.get("planets", []))
    return len(mine) >= 2 and bool(committed & set(mine))


def _parley_ready(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    system = state.systems.get(str(window.ctx.get("position")))
    committed = set(window.ctx.get("planets", []))
    return bool(committed & set(_controlled_in(system, player_id)))


def _mjets_ready(
    _state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    """Hity Space Cannon czekają na przypisanie przez TEGO gracza."""
    return window.ctx.get("ability") == "space_cannon" and window.ctx.get("target") == player_id


def _scramble_ready(
    _state: GameState, _registry: StaticDataRegistry, _player_id: str, window: OpenWindow
) -> bool:
    return bool(window.ctx.get("scramble"))


def docks_for_experimental(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str]]:
    """Doki gracza (``(pozycja, strefa)``) w aktywnym systemie albo w systemie sąsiednim."""
    active = state.active_system
    if active is None:
        return []
    near = {active, *_adjacent(state, registry, active)}
    docks: list[tuple[str, str]] = []
    for position in sorted(near):
        system = state.systems.get(position)
        if system is None:
            continue
        if system.space_units.get(player_id, {}).get("spacedock", 0) > 0:
            docks.append((position, "space"))
        for planet, by_player in sorted(system.planet_units.items()):
            if by_player.get(player_id, {}).get("spacedock", 0) > 0:
                docks.append((position, planet))
    return docks


def _experimental_ready(
    state: GameState, registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    active = state.active_player_id
    return (
        state.pending_window is None
        and active is not None
        and bool(space_cannon.target_ships(state, active))
        and bool(docks_for_experimental(state, registry, player_id))
    )


def _both(*conditions: ReactionCondition) -> ReactionCondition:
    def combined(
        state: GameState, registry: StaticDataRegistry, player_id: str, window: OpenWindow
    ) -> bool:
        return all(c(state, registry, player_id, window) for c in conditions)

    return combined


_START = ((GameEvent.INVASION, Moment.START),)
_COMMITTED = ((GameEvent.UNITS_COMMITTED, Moment.AFTER),)
_HITS = ((GameEvent.HITS_ASSIGNED, Moment.BEFORE),)
_ROLLED = ((GameEvent.UNIT_ABILITY_USED, Moment.AFTER),)

# Blitz / Disable: zagrywa ATAKUJĄCY („Your/Each of your ...”, „your opponents' PDS”).
declare_reaction("blitz", points=_START, subject=SELF, condition=_blitz_ready)
declare_reaction("disable", points=_START, subject=SELF, condition=_disable_ready)
# Bunker: broni się gracz kontrolujący planetę w systemie.
declare_reaction("bunker", points=_START, subject=OTHER, condition=_bunker_ready)
declare_reaction("ghost_squad", points=_COMMITTED, subject=OTHER, condition=_ghost_ready)
declare_reaction("parley", points=_COMMITTED, subject=OTHER, condition=_parley_ready)
declare_reaction(*_MJETS, points=_HITS, subject=OTHER, condition=_mjets_ready)
declare_reaction("scramble", points=_ROLLED, subject=OTHER, condition=_scramble_ready)
declare_reaction(
    "experimental",
    points=((GameEvent.SHIPS_MOVED, Moment.AFTER),),
    subject=OTHER,
    condition=_experimental_ready,
)


# ------------------------------------------------------------------ początek inwazji (efekty)


def _window_or_none(
    state: GameState, registry: StaticDataRegistry, player_id: str, card_id: str
) -> OpenWindow | None:
    """Okno, w którym gracz może teraz zagrać kartę (do formularzy)."""
    return window_for(state, registry, player_id, card_id)


def _require_invasion(state: GameState) -> InvasionState:
    if state.invasion is None:
        raise ValueError("No invasion is in progress.")
    return state.invasion


@register_effect("action_cards:blitz")
def blitz(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Blitz: Each of your non-fighter ships in the active system that do not have BOMBARDMENT
    gain BOMBARDMENT 6 until the end of the invasion.
    """
    inv = _require_invasion(state)
    if inv.attacker != player_id:
        raise ValueError("Blitz can be played only by the player resolving the invasion.")
    active_effects.add_effect(state, "action_cards:blitz", Duration.INVASION, owner=player_id)
    _reopen_bombardment(state, registry)


def _blitz_grant(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> frozenset[str]:
    return frozenset({str(_number("blitz", r"BOMBARDMENT\s+(\d+)"))})


register(POINT_BOMBARDMENT_GRANTED, card_effect_source("blitz"), HookKind.FORBID)(_blitz_grant)


@register_effect("action_cards:bunker")
def bunker(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Bunker: During this invasion, apply -4 to the result of each BOMBARDMENT roll against
    planets you control.
    """
    inv = _require_invasion(state)
    if not _controlled_in(state.systems.get(inv.position), player_id):
        raise ValueError("You control no planet in the active system.")
    active_effects.add_effect(state, "action_cards:bunker", Duration.INVASION, owner=player_id)


def _bunker_modifier(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    return _number("bunker", r"apply\s+(-?\d+)")


register(POINT_BOMBARDMENT_ROLL_MODIFIER, card_effect_source("bunker"), HookKind.MODIFY)(
    _bunker_modifier
)


@register_effect("action_cards:disable")
def disable(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Disable: Your opponents' PDS units lose PLANETARY SHIELD and SPACE CANNON during this
    invasion.
    """
    inv = _require_invasion(state)
    if inv.attacker != player_id:
        raise ValueError("Disable can be played only by the player resolving the invasion.")
    active_effects.add_effect(state, "action_cards:disable", Duration.INVASION, owner=player_id)
    _reopen_bombardment(state, registry)


def _disable_permit(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return str(ctx.get("victim")) != player_id


register(POINT_PDS_DISABLED, card_effect_source("disable"), HookKind.PERMIT)(_disable_permit)


# ---------------------------------------------------------- po zaangażowaniu (efekty, formularze)


@register_effect_inputs("action_cards:ghost_squad")
def ghost_squad_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    """Cel i siły do przeniesienia (tylko z planet, które gracz kontroluje w aktywnym systemie)."""
    window = _window_or_none(state, registry, player_id, "ghost_squad")
    system = state.systems.get(str(window.ctx.get("position"))) if window else None
    mine = _controlled_in(system, player_id)
    destinations = (
        [_option(p, _planet_label(state, registry, p)) for p in mine] if len(mine) >= 2 else []
    )
    units: list[dict[str, Any]] = []
    if system is not None and len(mine) >= 2:
        for planet in mine:
            for base_type, count in sorted(_ground(system, planet, player_id).items()):
                for index in range(count):
                    label = (
                        f"{_planet_label(state, registry, planet)}: "
                        f"{unit_name(state, registry, player_id, base_type)} {index + 1}"
                    )
                    value = {"planet": planet, "base_type": base_type}
                    meta = oi.unit_at(state, player_id, base_type, planet=planet)
                    units.append(_option(value, label, f"{planet}:{base_type}#{index}", meta=meta))
    return [
        _choice("to_planet", "Destination planet you control", destinations),
        _multi(
            "units", "Ground forces to move (all from one planet)", units, 0, len(units),
            "You may move zero ground forces.",
        ),
    ]


@register_effect("action_cards:ghost_squad")
def ghost_squad(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Ghost Squad: Move any number of your ground forces from any planet you control in the
    active system to any other planet you control in the active system.

    Źródło: C_action_cards (Ghost Squad) - można przenieść zero sił. ⚠ ZAŁOŻENIE: „from any
    planet ... to any other planet” czytamy w liczbie pojedynczej: wszystkie siły z JEDNEJ
    planety na JEDNĄ inną (obie kontrolowane, w aktywnym systemie).
    """
    inv = _require_invasion(state)
    system = state.systems.get(inv.position)
    mine = _controlled_in(system, player_id)
    picked = params.get("units", [])
    if not isinstance(picked, list):
        raise ValueError("'units' must be a list of {planet, base_type}.")
    if not picked:
        return
    destination = params.get("to_planet")
    if not isinstance(destination, str) or destination not in mine:
        raise ValueError("Choose a destination planet you control in the active system.")
    wanted: dict[tuple[str, str], int] = {}
    for item in picked:
        planet = item.get("planet") if isinstance(item, dict) else None
        base_type = item.get("base_type") if isinstance(item, dict) else None
        if not isinstance(planet, str) or not isinstance(base_type, str):
            raise ValueError("Each unit needs 'planet' and 'base_type'.")
        wanted[(planet, base_type)] = wanted.get((planet, base_type), 0) + 1
    sources = {planet for planet, _ in wanted}
    if len(sources) != 1:
        raise ValueError("Move ground forces from one planet only.")
    source = next(iter(sources))
    if source not in mine or source == destination:
        raise ValueError("Move from a planet you control to a different planet you control.")
    assert system is not None
    for (planet, base_type), count in wanted.items():
        if _ground(system, planet, player_id).get(base_type, 0) < count:
            raise ValueError(f"You do not have {count} {base_type} on {planet}.")
    for (planet, base_type), count in wanted.items():
        unit_ops.transfer_units(
            state, system, planet, system, destination, player_id, base_type, count,
            UnitCause.MOVED,
        )


@register_effect_inputs("action_cards:parley")
def parley_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    """Planety gracza, na które właśnie wylądowały cudze siły (Parley dotyczy JEDNEJ planety)."""
    window = _window_or_none(state, registry, player_id, "parley")
    options: list[dict[str, Any]] = []
    if window is not None:
        system = state.systems.get(str(window.ctx.get("position")))
        mine = set(_controlled_in(system, player_id))
        options = [
            _option(p, _planet_label(state, registry, p))
            for p in window.ctx.get("planets", [])
            if p in mine
        ]
    return [_choice("planet", "Planet you control that was landed on", options)]


@register_effect("action_cards:parley")
def parley(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Parley: Return the committed units to the space area.

    Źródło: C_action_cards (Parley) - dotyczy sił tylko JEDNEJ planety; zwrócone siły nie mogą
    w tej akcji lądować na inną planetę. ⚠ ZAŁOŻENIE: „committed units” = ostatnie zaangażowanie
    na wskazaną planetę; limit pojemności po powrocie do przestrzeni sprawdza krok akcji.
    """
    inv = _require_invasion(state)
    planet = params.get("planet")
    system = state.systems.get(inv.position)
    if not isinstance(planet, str) or planet not in _controlled_in(system, player_id):
        raise ValueError("Choose 1 planet you control that was landed on ('planet').")
    invasion.parley_return(state, planet)


# ------------------------------------------------------- trafienia i rzuty (Space Cannon)


def _register_maneuvering_jets(card_id: str) -> None:
    def effect(
        state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
    ) -> None:
        """Maneuvering Jets: Cancel 1 hit (przed przypisaniem trafień cudzego Space Cannon)."""
        ctx = _window_ctx(params)
        if ctx.get("target") != player_id:
            raise ValueError("You are not assigning these hits.")
        count = _number(card_id, r"Cancel\s+(\d+)\s+hit")
        if ctx.get("kind") == KIND_DEFENSE:
            invasion.cancel_defense_hits(state, str(ctx["planet"]), count)
        else:
            space_cannon.cancel_pending_hits(state, count)

    register_effect(f"action_cards:{card_id}")(effect)


def _window_ctx(params: Mapping[str, Any]) -> dict[str, Any]:
    window = params.get("__window")
    if not isinstance(window, Mapping) or not isinstance(window.get("ctx"), Mapping):
        raise ValueError("This card needs an open window.")
    return dict(window["ctx"])


for _card in _MJETS:
    _register_maneuvering_jets(_card)


@register_effect("action_cards:scramble")
def scramble(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Scramble Frequency: That player rerolls all of their dice (po rzucie Bombardment,
    Space Cannon albo Anti-Fighter Barrage).

    Okno trwa, dopóki trafienia rzutu czekają na przypisanie strat (po przypisaniu rzut jest
    rozstrzygnięty). ⚠ BRAK: Anti-Fighter Barrage rozstrzyga się w silniku bez pauzy (straty od
    razu), więc nie ma kiedy go przerzucić; rzut bez trafień też nie zatrzymuje silnika.
    """
    kind = _window_ctx(params).get("scramble")
    if kind == KIND_OFFENSE:
        space_cannon.reroll_pending(state)
    elif kind == KIND_DEFENSE:
        invasion.reroll_pending_defense(state)
    elif kind == KIND_BOMBARDMENT:
        invasion.reroll_pending_bombardment(state)
    else:
        raise ValueError("There is no roll to reroll right now.")


# ----------------------------------------------------------------- Experimental Battlestation


@register_effect_inputs("action_cards:experimental")
def experimental_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    """Doki gracza w aktywnym systemie albo w sąsiednim (źródło ostrzału)."""
    options: list[dict[str, Any]] = []
    for position, zone in docks_for_experimental(state, registry, player_id):
        where = "in orbit" if zone == "space" else f"on {_planet_label(state, registry, zone)}"
        label = f"Space dock {where} (system {position})"
        options.append(_option({"position": position, "zone": zone}, label, f"{position}:{zone}"))
    return [_choice("dock", "Space dock that fires", options)]


@register_effect("action_cards:experimental")
def experimental(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Experimental Battlestation: Choose 1 of your space docks that is either in or adjacent to
    that system. That space dock uses SPACE CANNON 5(x3) against the active player's ships in
    the active system.

    Liczby (5, x3) czytamy z tekstu karty. Trafienia czekają w oknie ``SPACE_CANNON`` na
    przypisanie przez aktywnego gracza (``space_cannon.assign_hits``). ⚠ ZAŁOŻENIE: PLASMA
    SCORING i inne modyfikatory kości wynikają z hooków ``roll_cannon`` (cel: aktywny gracz).
    """
    active = state.active_player_id
    if active is None or active == player_id:
        raise ValueError("Choose a space dock to shoot at the active player's ships.")
    dock = params.get("dock")
    chosen = (
        (str(dock.get("position")), str(dock.get("zone"))) if isinstance(dock, dict) else None
    )
    if chosen is None or chosen not in docks_for_experimental(state, registry, player_id):
        raise ValueError("Choose a space dock in or adjacent to the active system ('dock').")
    hits_on = _number("experimental", r"SPACE CANNON\s+(\d+)")
    dice_count = _number("experimental", r"SPACE CANNON\s+\d+\(x(\d+)\)")
    position, zone = chosen
    unit = invasion.unit_variant(state, registry, player_id, "spacedock")
    shooter = space_cannon.SpaceCannonShooter(
        player_id=player_id,
        base_type="spacedock",
        unit_id=unit.id if unit is not None else "spacedock",
        name=unit_name(state, registry, player_id, "spacedock"),
        count=1,
        hits_on=hits_on,
        dice_per_unit=dice_count,
        position=position,
        zone=zone,
        deep=False,
        remote=position != state.active_system,
    )
    space_cannon.open_remote_shot(state, shooter, active)
