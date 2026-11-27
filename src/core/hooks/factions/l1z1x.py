"""The L1Z1X Mindnet — komplet komponentów frakcji (RULES.md 62.12).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("l1z1x")``, ``units``,
``breakthroughs/te_breakthroughs.json``). Rulingi: ``docs/rules_tirules/F_lizix.md`` (krzyżowo
``C_action_cards`` - Infiltrate / Direct Hit, ``R_invasion`` - struktury przy przejęciu,
``C_technology`` - X-89). Punkty silnika dodane dla L1Z1X: struktury wymieniane zamiast niszczenia
(``control.structures_replaced``), tarcza nie blokuje bombardowania
(``bombardment.ignores_planetary_shield``), siły naziemne bombardujące jak statki
(``bombardment.ground_units``), kierowanie trafień na statki niemyśliwskie
(``combat.hits_to_non_fighters``), płatne ignorowanie prerekwizytów
(``technology.paid_ignore_all``); bombardowanie po rundzie walki naziemnej
(``core/combat_bombardment``), ruch bohatera (``core/direct_move``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    battle,
    board_reinforcements,
    combat_bombardment,
    cooperative,
    direct_move,
    exploration,
    extra_dice,
    faction_components,
    leaders,
    production,
    rules_hooks,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, InvasionPhase, Phase, StatusStep
from src.core.hooks.card_helpers import system_of_planet
from src.core.movement_paths import _ignores_anomalies
from src.core.planet_stats import influence_of
from src.core.reaction_cards import OpenWindow, window_provider
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_BOMBARDMENT_GROUND_UNITS,
    POINT_BOMBARDMENT_IGNORES_SHIELD,
    POINT_COMBAT_HITS_TO_NON_FIGHTERS,
    POINT_CONTROL_STRUCTURES_REPLACED,
    POINT_TECHNOLOGY_PAID_IGNORE_ALL,
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
from src.core.unit_ops import UnitCause

FACTION = "l1z1x"
ASSIMILATE = "assimilate"
HARROW = "harrow"
INHERITANCE = "is"
SUPER_DREADNOUGHT = "sdn2"
AGENT = "l1z1xagent"
COMMANDER = "l1z1xcommander"
HERO = "l1z1xhero"
FLAGSHIP = "l1z1x_flagship"
MECH = "l1z1x_mech"
CYBERNETIC = "ce"
BREAKTHROUGH = "l1z1xbt"

AGENT_SWAP = "i48s_swap"  # decyzja aktywnego gracza po wyczerpaniu agenta
UPLINK_LATER = f"breakthroughs:{BREAKTHROUGH}:after_explore"  # efekt: piechota po eksploracji
_INHERITANCE_COST = 2  # „spend 2 resources”
_COMMANDER_DREADNOUGHTS = 4  # „Have 4 dreadnoughts on the game board.”
_STRUCTURES = ("pds", "spacedock")
_SPACE = "space"
_NONE = "none"
_NOW = "now"
_AFTER = "after_explore"
_HERO_SHIPS = ("flagship", "dreadnought")
_HERO_CARGO = ("fighter", "infantry", "mech")
# Dark Space Navigation: nie do supernowej (mgławica OK - R_nebula notes/2).
_NO_ENTRY = ("SUPERNOVA",)
_ASTEROID = "ASTEROID_FIELD"
_ANTIMASS = "amd"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _own_event(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


# ------------------------------------------------------------------------------- Assimilate


def _foreign_structures(
    state: GameState, player_id: str, planet: str
) -> dict[str, dict[str, int]]:
    """Cudze struktury na planecie: ``{typ: {właściciel: ile}}``."""
    system = system_of_planet(state, planet)
    found: dict[str, dict[str, int]] = {}
    for owner, units in system.planet_units.get(planet, {}).items():
        if owner == player_id:
            continue
        for bt in _STRUCTURES:
            if units.get(bt, 0) > 0:
                found.setdefault(bt, {})[owner] = units[bt]
    return found


def _shortfall(state: GameState, player_id: str, base_type: str, count: int) -> int:
    left = production.reinforcements_left(state, player_id, base_type)
    return 0 if left is None else max(0, count - left)


def _source_options(
    state: GameState, registry: Any, player_id: str, base_type: str
) -> list[dict[str, Any]]:
    """Własne struktury na planszy w systemach bez żetonu gracza (wybór na mapie)."""
    return board_reinforcements.map_source_options(state, registry, player_id, base_type)


@register(POINT_CONTROL_STRUCTURES_REPLACED, HookSource(SOURCE_FACTION, FACTION),
          HookKind.PERMIT, covers=f"abilities:{ASSIMILATE}")
def assimilate_keeps(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Assimilate: struktury na zdobytej planecie wymienia hook niżej (nie giną od razu)."""
    return True


def _assimilate_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and bool(
        _foreign_structures(state, player_id, str(ctx.get("planet")))
    )


def assimilate_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Pusta rezerwa (F_lizix 3): skąd zdjąć brakujące struktury - osobno dla każdego typu."""
    inputs: list[dict[str, Any]] = []
    for bt, by_owner in _foreign_structures(state, player_id, str(ctx.get("planet"))).items():
        short = _shortfall(state, player_id, bt, sum(by_owner.values()))
        options = _source_options(state, registry, player_id, bt) if short else []
        if options:
            name = unit_name(state, registry, player_id, bt)
            inputs.append(oi.multi(
                f"sources:{bt}", f"No {name} left in reinforcements - take from the board",
                options, 0, min(short, len(options)),
            ))
    return inputs


@on_event(
    GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    decide=True, condition=_assimilate_ready, inputs=assimilate_inputs,
    covers=f"abilities:{ASSIMILATE}", label="Assimilate",
)
def assimilate(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Assimilate: When you gain control of a planet: Replace each PDS and space dock that is on
    that planet with a matching unit from your reinforcements.

    F_lizix: wymiana obowiązkowa (4); brak w rezerwie - L1Z1X MOŻE zdjąć strukturę tego typu z
    systemu bez swojego żetonu (3), inaczej cudza struktura ginie jak przy zwykłym przejęciu
    (R_invasion). Postawiony dok produkuje w kroku Production tej akcji (1)."""
    planet = str(ctx.get("planet"))
    system = system_of_planet(state, planet)
    params = ctx.get("params") or {}
    replaced = 0
    for bt, by_owner in _foreign_structures(state, player_id, planet).items():
        total = sum(by_owner.values())
        left = production.reinforcements_left(state, player_id, bt)
        picks = [str(v) for v in params.get(f"sources:{bt}") or []]
        if len(picks) > _shortfall(state, player_id, bt, total):
            raise ValueError("Take from the board only the structures missing in reinforcements.")
        for source in picks:
            board_reinforcements.take_from_board(state, player_id, bt, source)
        swap = total if left is None else min(total, left + len(picks))
        for owner, n in sorted(by_owner.items()):
            take = min(n, swap)
            swap -= take
            if take:
                unit_ops.remove_units(state, system, planet, owner, bt, take, UnitCause.REMOVED)
            if n - take:
                unit_ops.remove_units(state, system, planet, owner, bt, n - take,
                                      UnitCause.DESTROYED)
            if take:
                unit_ops.place_units(state, system, planet, player_id, bt, take,
                                     UnitCause.PLACED)
                replaced += take
    ability_notes.note(state, player_id, f"abilities:{ASSIMILATE}",
                       f"replaced {replaced} structure(s)")


# ----------------------------------------------------------------------------------- Harrow


def _harrow_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Koniec rundy walki naziemnej (nie AFB), L1Z1X atakuje i jest aktywnym graczem (F_lizix 2),
    planeta bez działającej tarczy (1), są jednostki z Bombardment."""
    combat = combat_bombardment.ground_combat(state)
    registry = _registry()
    return (
        combat is not None
        and ctx.get("kind") == "ground"
        and ctx.get("phase") == "combat"
        and combat.attacker == player_id
        and state.active_player_id == player_id
        and combat_bombardment.target_open(state, registry, player_id)
        and bool(combat_bombardment.groups(state, registry, player_id))
    )


def harrow_inputs(
    state: GameState, _registry_: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Dodatkowe kości (Plasma Scoring, commander Argent…): każde źródło osobno, „Auto”/bez."""
    groups = combat_bombardment.groups(state, _registry(), player_id)
    inputs: list[dict[str, Any]] = []
    for source in combat_bombardment.extra_sources(state, player_id):
        options = [oi.option(extra_dice.AUTO, "Auto")] + [
            oi.option(g.base_type, g.name) for g in groups
        ] + [oi.option(_NONE, "No extra die")]
        inputs.append(oi.choice(f"extra:{source.key}", f"Extra die: {source.name}", options))
    return inputs


_HARROW_LABEL = "Harrow"
combat_bombardment.register_roll_offer(_HARROW_LABEL)  # okno Ambuscade przed rzutem


@on_event(
    GameEvent.COMBAT_ROUND, Moment.END, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_harrow_ready, inputs=harrow_inputs,
    covers=f"abilities:{HARROW}", label=_HARROW_LABEL,
)
def harrow(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Harrow: At the end of each round of ground combat: Your ships in the active system may use
    their BOMBARDMENT abilities against your opponent's ground forces on the planet.

    F_lizix: wszystkie jednostki z Bombardment w systemie strzelają w planetę walki (4), także
    Annihilatory spoza tej walki (4.1), działa X-89 (5); po rundzie, w której zginęły ostatnie siły
    L1Z1X - też (3, możliwy remis). Trafienia przypisuje obrońca (Sustain Damage działa)."""
    combat = combat_bombardment.ground_combat(state)
    if combat is None:
        raise ValueError("Harrow is used at the end of a round of ground combat.")
    params = ctx.get("params") or {}
    # Źródło bez pola w formularzu (Strike Wing Ambuscade zagrana w oknie przed rzutem) - „Auto”:
    # gracz sam zagrał notkę dla tego rzutu.
    picks = {e.key: extra_dice.AUTO for e in combat_bombardment.extra_sources(state, player_id)}
    picks.update({
        key.split(":", 1)[1]: str(value) for key, value in params.items()
        if key.startswith("extra:")
    })
    hits = combat_bombardment.roll(state, _registry(), player_id, picks, label=_HARROW_LABEL)
    victim = combat.defender
    planet = combat.planet or ""
    ground = [
        bt for bt in ("infantry", "mech")
        if state.systems[combat.position].planet_units.get(planet, {}).get(victim, {}).get(bt)
    ]
    battle.add_round_end_hits(state, victim, hits, only=ground, label="Harrow")
    ability_notes.note(state, player_id, f"abilities:{HARROW}", f"{hits} hit(s)")


# ---------------------------------------------------------------- Inheritance Systems (tech)


@register(POINT_TECHNOLOGY_PAID_IGNORE_ALL, HookSource(SOURCE_TECHNOLOGY, INHERITANCE),
          HookKind.FORBID, covers=f"technologies:{INHERITANCE}")
def inheritance_systems(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Inheritance Systems: You may exhaust this card and spend 2 resources when you research a
    technology; ignore all of that technology's prerequisites.

    Zapłata OSOBNO od kosztu badania (F_lizix: nadwyżka kosztu Technology przepada) - skip
    ``paid:is|<planety>|<tg>`` w ``technology.plan_research``."""
    return {f"{INHERITANCE}:{_INHERITANCE_COST}"}


# Super Dreadnought II: liczby z danych ``l1z1x_dreadnought2``; „cannot be destroyed by Direct Hit”
# czyta z tekstu danych ``reactions_combat._direct_hit_immune`` (jak Exotrireme II).
rules_hooks.declare_data_driven(f"technologies:{SUPER_DREADNOUGHT}")
rules_hooks.declare_data_driven("units:l1z1x_dreadnought2")


# ------------------------------------------------------------------------ [0.0.1] (flagowiec)


@register(POINT_COMBAT_HITS_TO_NON_FIGHTERS, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.FORBID,
          covers=f"units:{FLAGSHIP}")
def flagship_hits(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> set[str]:
    """[0.0.1]: During a space combat, hits produced by this ship and by your dreadnoughts in this
    system must be assigned to non-fighter ships if able."""
    system = state.systems.get(str(ctx.get("position") or ""))
    if system is None or system.space_units.get(player_id, {}).get("flagship", 0) <= 0:
        return set()
    return set(_HERO_SHIPS)


# ---------------------------------------------------------------------- Annihilator (mech)


@register(POINT_BOMBARDMENT_GROUND_UNITS, HookSource(SOURCE_UNIT, MECH), HookKind.FORBID,
          covers=f"units:{MECH}")
def annihilator(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Annihilator: While not participating in ground combat, this unit can use its BOMBARDMENT
    ability on planets in its system as if it were a ship (krok Bombardment: 1 planeta na
    jednostkę; Harrow: mechy spoza planety walki - F_lizix)."""
    return {"mech"}


# ------------------------------------------------------------------------------ I48S (agent)


def _infantry_zones(state: GameState, player_id: str, position: str) -> list[str]:
    system = state.systems.get(position)
    if system is None:
        return []
    zones = [_SPACE] if system.space_units.get(player_id, {}).get("infantry", 0) > 0 else []
    zones += [
        planet for planet, by_player in sorted(system.planet_units.items())
        if by_player.get(player_id, {}).get("infantry", 0) > 0
    ]
    return zones


def _agent_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    activator = str(ctx.get("player") or "")
    position = str(ctx.get("position") or "")
    return (
        activator in state.players
        and bool(_infantry_zones(state, activator, position))
        and board_reinforcements.can_place(state, activator, "mech")
        and leaders.is_ready(state, _registry(), player_id, AGENT)
    )


# Cooperative agent (RULES.md 54.15): helps "that player" - requested, not pushed.
cooperative.register_pull(f"leaders:{AGENT}")


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_agent_ready, covers=f"leaders:{AGENT}",
    label="I48S: replace infantry with a mech",
)
def i48s(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """I48S: After a player activates a system: You may exhaust this card to allow that player to
    replace 1 of their infantry in the active system with 1 mech from their reinforcements.

    Piechota musi być w systemie w chwili aktywacji (F_lizix 1) - zapamiętane miejsca; wymianę
    wybiera aktywny gracz (osobna decyzja)."""
    activator = str(ctx.get("player") or "")
    position = str(ctx.get("position") or "")
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT,
                                {"target": activator})
    effect = active_effects.add_effect(state, f"leaders:{AGENT}:swap", Duration.TURN,
                                       owner=activator)
    effect.data = {"position": position, "zones": _infantry_zones(state, activator, position)}
    faction_components.ability_used(state, player_id, AGENT_SWAP, activator)


def _swap(state: GameState, activator: str) -> Any:
    return next(
        (e for e in state.active_effects
         if e.key == f"leaders:{AGENT}:swap" and e.owner == activator),
        None,
    )


def agent_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Piechota do wymiany (na mapie) albo rezygnacja; brak mecha w rezerwie - skąd go zdjąć."""
    effect = _swap(state, decider)
    if effect is None:
        return []
    position = str(effect.data["position"])
    live = set(_infantry_zones(state, decider, position))
    name = unit_name(state, registry, decider, "infantry")
    options = [
        oi.option(zone, name, meta=oi.unit_at(state, decider, "infantry", position=position,
                                              planet=None if zone == _SPACE else zone))
        for zone in effect.data["zones"] if zone in live
    ]
    options.append(oi.option(_NONE, "Keep the infantry"))
    inputs = [oi.choice("infantry", "Infantry to replace with a mech", options)]
    if board_reinforcements.needs_board_source(state, decider, "mech"):
        sources = _source_options(state, registry, decider, "mech")
        inputs.append(oi.choice("source", "No mech left in reinforcements - take one from the "
                                "board", sources))
    return inputs


def _activator_decides(_state: GameState, _owner: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    where={"ability": AGENT_SWAP}, decide=True, decider=_activator_decides,
    inputs=agent_inputs, label="I48S: replace your infantry",
)
def i48s_swap(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Aktywny gracz wymienia 1 piechotę na mecha (mech zdjęty z planszy - nieuszkodzony, F_lizix
    2) albo zostawia piechotę."""
    if ctx.get("player") != player_id:
        return
    activator = str(ctx["target"])
    effect = _swap(state, activator)
    if effect is None:
        return
    params = ctx.get("params") or {}
    zone = str(params.get("infantry") or _NONE)
    active_effects.remove_effect(state, effect.id)
    if zone == _NONE:
        return
    position = str(effect.data["position"])
    if zone not in effect.data["zones"] or zone not in _infantry_zones(state, activator, position):
        raise ValueError("Choose your infantry that was in the active system when it was "
                         "activated.")
    system = state.systems[position]
    raw_source = params.get("source")
    source = str(raw_source) if raw_source else None
    unit_ops.remove_units(state, system, zone, activator, "infantry", 1, UnitCause.REMOVED)
    board_reinforcements.place_unit(state, system, zone, activator, "mech", source=source)
    ability_notes.note(state, activator, f"leaders:{AGENT}", "replaced 1 infantry with a mech")


# -------------------------------------------------------------------------- 2RAM (commander)


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 4 dreadnoughts on the game board."""
    total = sum(
        system.space_units.get(player_id, {}).get("dreadnought", 0)
        for system in state.systems.values()
    )
    return total >= _COMMANDER_DREADNOUGHTS


@register(POINT_BOMBARDMENT_IGNORES_SHIELD, HookSource(SOURCE_LEADER, COMMANDER),
          HookKind.PERMIT, covers=f"leaders:{COMMANDER}")
def two_ram(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """2RAM: At any time: Units that have PLANETARY SHIELD do not prevent you from using
    BOMBARDMENT (jednostki nadal mają tarczę - Magen Defense Grid działa, F_lizix)."""
    return True


# ------------------------------------------------- The Helmsman — Dark Space Navigation (hero)


def hero_destinations(state: GameState, player_id: str) -> list[str]:
    """Systems without other players' ships; never a supernova and an asteroid field only with
    Antimass Deflectors (F_lizix 5, 5.2) - unless the player ignores anomaly effects on movement
    (Circlet of the Void: supernova allowed, F_lizix 5.1). Nebula allowed (R_nebula notes/2)."""
    grid = grid_from_state(state, _registry())
    ignores = _ignores_anomalies(state, player_id)
    has_antimass = ignores or _ANTIMASS in state.players[player_id].technologies
    found: list[str] = []
    for position, system in sorted(state.systems.items()):
        if any(o != player_id and any(n > 0 and is_space_unit(bt) for bt, n in u.items())
               for o, u in system.space_units.items()):
            continue
        anomalies = grid.anomalies_at(position)
        if not ignores and any(a in anomalies for a in _NO_ENTRY):
            continue
        if _ASTEROID in anomalies and not has_antimass:
            continue
        found.append(position)
    return found


def _hero_sources(state: GameState, player_id: str) -> list[str]:
    return sorted(
        pos for pos, system in state.systems.items()
        if any(system.space_units.get(player_id, {}).get(bt, 0) > 0 for bt in _HERO_SHIPS)
    )


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    return direct_move.move_inputs(
        state, registry, player_id, _hero_sources(state, player_id),
        hero_destinations(state, player_id), only=(*_HERO_SHIPS, *_HERO_CARGO),
    )


@register_effect(f"leaders:{HERO}")
def dark_space_navigation(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """The Helmsman — Dark Space Navigation: ACTION: Choose 1 system that does not contain other
    players' ships; you may move your flagship and any number of your dreadnoughts from other
    systems into the chosen system. Then, purge this card.

    F_lizix: ruch prosto do celu, także z systemów z żetonem L1Z1X (1); ładunek tylko z systemu
    źródłowego (3) - także z systemu z żetonem (ruling FAQ 2.2); rzut szczeliny (4); Nexus
    aktywuje się sam (6). Myśliwce i siły naziemne lecą tylko z flagowcem / pancernikiem."""
    moves = direct_move.parse_moves(params)
    if len(moves) != 1:
        raise ValueError("Choose exactly 1 system and move your flagship or dreadnoughts there.")
    dest = next(iter(moves))
    if dest not in hero_destinations(state, player_id):
        raise ValueError("Choose a system that does not contain other players' ships.")
    if any(bt not in (*_HERO_SHIPS, *_HERO_CARGO) for by in moves[dest].values() for bt in by):
        raise ValueError("Only your flagship, dreadnoughts and the units they transport move.")
    direct_move.apply_moves(state, registry, player_id, moves, fighters_free=False,
                            carriers=_HERO_SHIPS)


# ---------------------------------------------------------- Cybernetic Enhancements (notka)


@window_provider
def status_gain_tokens(state: GameState) -> list[OpenWindow]:
    """Okno „When you gain command tokens during the status phase” (ogólne): krok REDISTRIBUTE,
    gracz zdobył żetony w kroku 5 i jeszcze nie zatwierdził ich rozdziału."""
    status = state.status
    if state.phase is not Phase.STATUS or status is None:
        return []
    if status.step is not StatusStep.REDISTRIBUTE:
        return []
    return [
        OpenWindow(GameEvent.STATUS_STEP, Moment.WHEN,
                   {"step": "gain_command_tokens", "player": pid})
        for pid in sorted(state.players) if pid not in status.done
    ]


@register_effect(f"promissory_notes:{CYBERNETIC}")
def cybernetic_enhancements(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Cybernetic Enhancements: When you gain command tokens during the status phase: Gain 1
    additional command token. Then, return this card to the L1Z1X player (zwrot -
    ``promissory_play``). Żeton z rezerwy trafia do nieprzydzielonych (pusta rezerwa - nic)."""
    from src.core import command_tokens  # lokalnie: lekki moduł, bez cyklu

    status = state.status
    if status is None or status.step is not StatusStep.REDISTRIBUTE or player_id in status.done:
        raise ValueError("Play this card while you distribute the command tokens you gained.")
    if state.players[player_id].cc_reinf <= 0:
        return
    command_tokens.take_from_reinforcements(state, player_id, 1)
    status.unassigned_cc[player_id] = status.unassigned_cc.get(player_id, 0) + 1


# --------------------------------------------------------------- Fealty Uplink (przełom)


def _will_explore(state: GameState, ctx: Mapping[str, Any]) -> bool:
    """Planeta bez poprzedniego kontrolera, zaraz eksplorowana (Establish Control inwazji)."""
    inv = state.invasion
    return (
        ctx.get("previous") is None
        and inv is not None
        and inv.phase is InvasionPhase.ESTABLISH
        and exploration.explorable(_registry(), str(ctx.get("planet")))
    )


def uplink_inputs(
    state: GameState, _registry_: Any, _player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """F_lizix 1: przy planecie niczyjej - piechota przed albo po eksploracji (wybór gracza)."""
    if not _will_explore(state, ctx):
        return []
    return [oi.choice("when", "Place the infantry", [
        oi.option(_NOW, "Before exploring the planet"),
        oi.option(_AFTER, "After exploring the planet"),
    ])]


def _place_uplink(state: GameState, player_id: str, planet: str, position: str) -> int:
    count = influence_of(state, _registry(), planet)
    system = state.systems.get(position)
    if count > 0 and system is not None:
        unit_ops.place_units(state, system, planet, player_id, "infantry", count,
                             UnitCause.PLACED)
        ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                           f"placed {count} infantry")
    return count


@on_event(
    GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    decide=True, condition=_own_event, inputs=uplink_inputs,
    covers=f"breakthroughs:{BREAKTHROUGH}", label="Fealty Uplink",
)
def fealty_uplink(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Fealty Uplink: When you gain control of a planet, place infantry from your reinforcements
    equal to that planet's influence value on that planet (obowiązkowo - F_lizix 2)."""
    planet = str(ctx.get("planet"))
    position = str(ctx.get("position") or "")
    if (ctx.get("params") or {}).get("when") == _AFTER:
        effect = active_effects.add_effect(state, UPLINK_LATER, Duration.TACTICAL_ACTION,
                                           owner=player_id)
        effect.data = {"planet": planet, "position": position}
        return
    _place_uplink(state, player_id, planet, position)


def _uplink_effects(state: GameState, player_id: str, planet: Any) -> list[Any]:
    return [
        e for e in state.active_effects
        if e.key == UPLINK_LATER and e.owner == player_id and e.data.get("planet") == planet
    ]


def _uplink_waiting(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return bool(_uplink_effects(state, player_id, ctx.get("planet")))


@on_event(
    GameEvent.PLANET_EXPLORED, Moment.AFTER, HookSource(SOURCE_EFFECT, UPLINK_LATER),
    condition=_uplink_waiting, label="Fealty Uplink: place infantry",
)
def fealty_uplink_after(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Piechota Fealty Uplink postawiona po eksploracji planety (wybór gracza, F_lizix 1)."""
    planet = str(ctx.get("planet"))
    for effect in _uplink_effects(state, player_id, planet):
        active_effects.remove_effect(state, effect.id)
        _place_uplink(state, player_id, planet, str(effect.data.get("position") or ""))
