"""Relikty pasywne i zdarzeniowe (RULES.md 59): działają same albo reagują na zdarzenia.

Źródłem hooka jest relikt LEŻĄCY przed graczem (``SOURCE_RELIC``), więc efekt obowiązuje tylko
jego właściciela i znika wraz z kartą. Decyzje „you may” trafiają do okna ofert (RULES.md 56) -
gracz zawsze decyduje sam. Teksty w docstringach to dosłowne cytaty z ``assets/data/relics``;
przypadki brzegowe: ``docs/rules_tirules/C_relics.md``.

Zrealizowane tu: Shard of the Throne, The Obsidian, Dynamis Core (pasywna część), Circlet of the
Void (pasywna część), Book of Latvinia (przy zdobyciu), The Quantumcore (breakthrough przy
zdobyciu), Maw of Worlds.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    economy,
    exhaust,
    expeditions,
    objectives,
    relics,
    rules_hooks,
    secret_objectives,
    technology,
)
from src.core import offer_inputs as oi
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.hooks import card_labels
from src.core.hooks.card_helpers import controlled
from src.core.planet_stats import is_legendary
from src.core.rules_hooks import (
    POINT_COMMODITY_VALUE,
    POINT_MOVEMENT_ENTER_ASTEROIDS,
    POINT_MOVEMENT_IGNORE_ANOMALIES_KEEP_RIFT,
    POINT_SECRET_OBJECTIVE_LIMIT,
    POINT_TECHNOLOGY_SYNERGY_ALL,
    SOURCE_RELIC,
    HookKind,
    HookSource,
    on_event,
    register,
)
from src.core.state_grid import grid_from_state

_DYNAMIS_BONUS = 2  # „your commodity value is increased by 2”
_OBSIDIAN_BONUS = 1  # „You can have 1 additional scored or unscored secret objective”
_BOOK_MAX = 2  # „research up to 2 technologies”


def _src(relic_id: str) -> HookSource:
    return HookSource(SOURCE_RELIC, relic_id)


def _own_event(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


def _gained(relic_id: str) -> dict[str, str]:
    """Filtr ``where``: zdarzenie „zdobyto TEN relikt” (inne relikty gracza nie reagują)."""
    return {"component": f"relics:{relic_id}"}


# --- Shard of the Throne ---------------------------------------------------------------------


@on_event(
    GameEvent.COMPONENT_GAINED,
    Moment.WHEN,
    _src("shard"),
    where=_gained("shard"),
    condition=_own_event,
    label="Shard of the Throne: gain 1 victory point",
)
def shard_gained(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Shard of the Throne: When you gain this card, gain 1 victory point."""
    del ctx
    objectives.award_points(state, player_id, 1, source="relics:shard")


@relics.on_lost("shard")
def shard_lost(state: GameState, player_id: str) -> None:
    """Shard of the Throne: when you lose this card, lose 1 victory point."""
    objectives.award_points(state, player_id, -1, source="relics:shard")


def _shard_planet_taken(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Ktoś inny przejął legendarną planetę właściciela albo jego planetę w systemie domowym."""
    new_owner = ctx.get("player")
    if ctx.get("previous") != player_id or new_owner == player_id or new_owner not in state.players:
        return False
    registry = rules_hooks.bound_registry()
    planet = str(ctx.get("planet", ""))
    home = state.players[player_id].home_position
    return (registry is not None and is_legendary(state, registry, planet)) or (
        home is not None and ctx.get("position") == home
    )


@on_event(
    GameEvent.PLANET_CONTROL_GAINED,
    Moment.AFTER,
    _src("shard"),
    condition=_shard_planet_taken,
    covers="relics:shard",
    label="Shard of the Throne: passes to the new controller",
)
def shard_passes(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Shard of the Throne: When a player gains control of a legendary planet you control or a
    planet you control in your home system, that player gains this card.

    Natychmiast, bez okna na inne zdolności (C_relics): karta przechodzi, zanim cokolwiek się
    rozstrzygnie.
    """
    relics.transfer(state, player_id, str(ctx["player"]), "shard")


# --- The Obsidian ----------------------------------------------------------------------------


@register(
    POINT_SECRET_OBJECTIVE_LIMIT, _src("obsidian"), HookKind.MODIFY, covers="relics:obsidian"
)
def obsidian_limit(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """The Obsidian: You can have 1 additional scored or unscored secret objective."""
    return _OBSIDIAN_BONUS


def obsidian_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Wybór potrzebny tylko, gdy po dobraniu gracz przekroczy limit: co oddać do talii."""
    if not secret_objectives.over_limit_after_draw(state, decider):
        return []
    options = [oi.option(secret_objectives.DRAWN, "The secret objective you are about to draw")]
    for objective_id in state.players[decider].private.secret_objectives:
        definition = objectives.objective_def(registry, objective_id)
        name = definition.name if definition is not None else objective_id
        options.append(oi.option(objective_id, f"Return {name}"))
    return [oi.choice("give_back", "Return one unscored secret objective", options)]


@on_event(
    GameEvent.COMPONENT_GAINED,
    Moment.WHEN,
    _src("obsidian"),
    where=_gained("obsidian"),
    condition=_own_event,
    covers="relics:obsidian",
    label="The Obsidian: draw 1 secret objective",
    inputs=obsidian_inputs,
    decide=True,
)
def obsidian_gained(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The Obsidian: When you gain this card, draw 1 secret objective."""
    give_back = ctx.get("params", {}).get("give_back")
    secret_objectives.draw(state, player_id, give_back)


# --- Dynamis Core (część pasywna; ACTION w relics_actions) -----------------------------------


@register(POINT_COMMODITY_VALUE, _src("dynamiscore"), HookKind.MODIFY, covers="relics:dynamiscore")
def dynamis_bonus(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Dynamis Core: While this card is in your play area, your commodity value is +2."""
    return _DYNAMIS_BONUS


@relics.on_lost("dynamiscore")
def dynamis_lost(state: GameState, player_id: str) -> None:
    """Po utracie karty nadmiar commodities wraca do puli (C_relics)."""
    economy.cap_commodities(state, player_id)


# --- Circlet of the Void (część pasywna; ACTION w relics_actions) ----------------------------


@register(
    POINT_MOVEMENT_IGNORE_ANOMALIES_KEEP_RIFT,
    _src("circletofthevoid"),
    HookKind.PERMIT,
    covers="relics:circletofthevoid",
)
def circlet_ignores_anomalies(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> bool:
    """Circlet of the Void: Your units do not roll for gravity rifts, and you ignore the effects
    of all other anomalies on movement.

    Działa także, gdy karta jest wyczerpana (C_relics). Szczelina nadal daje +1 do ruchu (C_relics:
    „still applies the movement bonus”) - inaczej niż Nav Suite.
    """
    return True


@register(POINT_MOVEMENT_ENTER_ASTEROIDS, _src("circletofthevoid"), HookKind.PERMIT)
def circlet_enters_asteroids(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> bool:
    """Circlet of the Void: ruch przez/do pól asteroid (ignorowanie efektów anomalii)."""
    return True


# --- Book of Latvinia (przy zdobyciu; ACTION w relics_actions) -------------------------------


def _no_prerequisite_techs(
    state: GameState, registry: Any, player_id: str
) -> list[Any]:
    """Technologie z talii gracza bez prerekwizytów, których jeszcze nie ma."""
    owned = set(state.players[player_id].technologies)
    return [
        tech
        for tech in technology.tech_pool(state, registry, player_id).values()
        if tech.id not in owned and not technology.prerequisites(tech)
    ]


def book_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Do dwóch technologii bez prerekwizytów (liczy silnik; gracz wybiera ile i które)."""
    options = [
        oi.option(tech.id, card_labels.describe_technology(tech))
        for tech in _no_prerequisite_techs(state, registry, decider)
    ]
    return [
        oi.multi(
            "technologies", "Technologies to research (no prerequisites)", options,
            0, min(_BOOK_MAX, len(options)), "Up to 2 technologies that have no prerequisites.",
        )
    ]


@on_event(
    GameEvent.COMPONENT_GAINED,
    Moment.WHEN,
    _src("bookoflatvinia"),
    where=_gained("bookoflatvinia"),
    condition=_own_event,
    label="Book of Latvinia: research up to 2 technologies",
    inputs=book_inputs,
    decide=True,
)
def book_gained(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Book of Latvinia: When you gain this card, research up to 2 technologies that have no
    prerequisites.

    ⚠ ZAŁOŻENIE: wyjątek Nekro (sześć żetonów dowodzenia zamiast technologii) nie jest jeszcze
    kodowany - to osobny etap zdolności frakcji.
    """
    registry = rules_hooks.bound_registry()
    chosen = list(ctx.get("params", {}).get("technologies", []))
    if len(chosen) > _BOOK_MAX or len(set(chosen)) != len(chosen):
        raise ValueError("Choose up to 2 different technologies.")
    # C_relics: technologii z prerekwizytem nie da się zdobyć przez pominięcie prerekwizytu
    # (specjalność planety, Analytical) - tylko technologie BEZ prerekwizytów.
    allowed = {tech.id for tech in _no_prerequisite_techs(state, registry, player_id)}
    if any(tech_id not in allowed for tech_id in chosen):
        raise ValueError("Book of Latvinia researches only technologies without prerequisites.")
    for tech_id in chosen:
        plan = technology.plan_research(state, registry, player_id, tech_id, [])
        technology.apply_research(state, player_id, plan)


# --- The Quantumcore -------------------------------------------------------------------------


@on_event(
    GameEvent.COMPONENT_GAINED,
    Moment.WHEN,
    _src("quantumcore"),
    where=_gained("quantumcore"),
    condition=_own_event,
    covers="relics:quantumcore",
    label="The Quantumcore: gain your breakthrough",
)
def quantumcore_gained(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The Quantumcore: When you gain this card, gain your breakthrough.

    Druga część („You have SYNERGY for all technology types") to hook PERMIT niżej.
    """
    del ctx
    registry = rules_hooks.bound_registry()
    expeditions.gain_breakthrough(state, registry, grid_from_state(state, registry), player_id)


@register(POINT_TECHNOLOGY_SYNERGY_ALL, _src("quantumcore"), HookKind.PERMIT)
def quantumcore_synergy(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """The Quantumcore: You have SYNERGY for all technology types."""
    return True


# --- Maw of Worlds ---------------------------------------------------------------------------


def _maw_options(state: GameState, registry: Any, player_id: str) -> list[dict[str, Any]]:
    """Dowolna technologia z talii gracza, której nie ma (prerekwizyty nie obowiązują)."""
    owned = set(state.players[player_id].technologies)
    return [
        oi.option(tech.id, card_labels.describe_technology(tech))
        for tech in technology.tech_pool(state, registry, player_id).values()
        if tech.id not in owned
    ]


def maw_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [oi.choice("technology", "Technology to gain", _maw_options(state, registry, decider))]


def _agenda_phase_start(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("phase") == "agenda"


@on_event(
    GameEvent.PHASE,
    Moment.START,
    _src("mawofworlds"),
    optional=True,
    where={"phase": "agenda"},
    condition=_agenda_phase_start,
    covers="relics:mawofworlds",
    label="Maw of Worlds: purge and exhaust all planets to gain any technology",
    inputs=maw_inputs,
)
def maw_of_worlds(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Maw of Worlds: At the start of the agenda phase, you may purge this card and exhaust all of
    your planets to gain any 1 technology.

    Technologia przychodzi bez prerekwizytów (C_relics).
    """
    tech_id = str(ctx.get("params", {}).get("technology", ""))
    registry = rules_hooks.bound_registry()
    if tech_id not in {o["value"] for o in _maw_options(state, registry, player_id)}:
        raise ValueError("Choose a technology you do not own ('technology').")
    relics.purge_relic(state, player_id, "mawofworlds")
    exhaust.exhaust_planets(state, player_id, controlled(state, player_id))
    technology.grant_technology(state, player_id, tech_id)
