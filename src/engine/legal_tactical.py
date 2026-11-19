"""Legalne ruchy B5: akcja taktyczna, walka, Space Cannon, inwazja, eksploracja, karty akcji.

Ta sama umowa co ``legal``: kandydaci z obserwacji gracza (ścisła projekcja), PIERWSZY =
bezpieczny ruch domyślny (koniec kroku / pas / odmowa), dalsze = warianty, z których bot losowy
wybiera. Generator nie zna reguł: korzysta z enumeratorów ``core/`` (``legal_move_sources``,
``combat_planets``, ``offense_targets``, ``retreat_destinations``, ``playability``…), a ostateczną
legalność sprawdza Sędzia (odrzucony kandydat => runner próbuje kolejnego).

Warianty są celowo PROSTE (⚠️ ZAŁOŻENIE projektowe, RULES.md 65.3): ruch całej floty ze źródła
z ładunkiem do pełnej pojemności albo bez, produkcja jednej pozycji naraz, lądowanie wszystkich
sił na jedną planetę, bombardowanie wszystkiego w jedną planetę, straty od Sustain Damage i
najsłabszych jednostek. Zdolności „may” w trakcie tych kroków (Gravity Drive, Plasma Scoring,
AFB extra) bot pomija.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.core import (
    action_cards,
    battle,
    capacity,
    exploration,
    invasion,
    movement,
    production,
    retreat,
    space_cannon,
    tactical,
)
from src.core.game_state import (
    CombatStep,
    GameState,
    InvasionPhase,
    TacticalStep,
    WindowType,
)
from src.core.unit_catalog import is_space_unit
from src.engine import actions as act
from src.engine import actions_tactical as tac
from src.engine.actions import Action, EngineContext
from src.engine.observation import Observation

_CARGO = ("infantry", "mech", "fighter")
_MAX_CARD_VARIANTS = 4


# --- Straty: wspólny plan dla walki, Space Cannon, bombardowania i obrony ----------------------


def loss_plans(
    units: Iterable[battle.CombatUnit], required: int, cancels: int, targets: set[str] | None = None
) -> list[tuple[dict[str, int], dict[str, int], dict[str, int]]]:
    """Plany ``(sustain, destroy, destroy_damaged)`` pokrywające ``required`` trafień.

    Dwa warianty: najpierw Sustain Damage, potem bez niego; giną najsłabsze jednostki (najwyższy
    próg trafienia). ``targets`` = typy, które muszą przyjąć trafienia pierwsze (RULES.md 62.10).
    """
    wanted = targets or set()
    ordered = sorted(units, key=lambda u: (u.base_type not in wanted, -u.hits_on, u.base_type))
    plans: list[tuple[dict[str, int], dict[str, int], dict[str, int]]] = []
    for use_sustain in (True, False):
        left = required
        sustain: dict[str, int] = {}
        destroy: dict[str, int] = {}
        destroy_damaged: dict[str, int] = {}
        if use_sustain and cancels > 0:
            for unit in ordered:
                if left <= 0:
                    break
                if unit.sustain and unit.sustainable > 0:
                    uses = min(unit.sustainable, -(-left // cancels))
                    sustain[unit.base_type] = uses
                    left -= uses * cancels
        for unit in ordered:
            if left <= 0:
                break
            damaged = unit.damaged + sustain.get(unit.base_type, 0)
            take = min(unit.count - damaged, left)
            if take > 0:
                destroy[unit.base_type] = take
                left -= take
            take = min(damaged, left)
            if take > 0:
                destroy_damaged[unit.base_type] = take
                left -= take
        plan = (sustain, destroy, destroy_damaged)
        if plan not in plans:
            plans.append(plan)
    return plans


# --- Faza akcji: aktywacje i karty akcji -----------------------------------------------------


def action_phase_extras(obs: Observation, ctx: EngineContext) -> list[Action]:
    """Dodatkowe akcje tury (po strategicznej / pasie): aktywacje systemów i karty akcji."""
    s = obs.view
    pid = obs.player_id
    player = s.players[pid]
    result: list[Action] = []
    if player.tactical_cc > 0:
        result.extend(
            tac.TacticalActivate(player_id=pid, position=p) for p in _targets(s, ctx, pid)
        )
    result.extend(action_card_plays(obs, ctx))
    return result


def _targets(s: GameState, ctx: EngineContext, pid: str) -> list[str]:
    """Systemy warte aktywacji: dokąd dolecą własne statki albo gdzie gracz już ma jednostki."""
    result: list[str] = []
    for position in sorted(ctx.grid.positions):
        system = s.systems.get(position)
        if system is not None and pid in system.command_tokens:
            continue
        if ctx.grid.is_impassable(position):
            continue
        own = system is not None and (
            any(n > 0 for n in system.space_units.get(pid, {}).values())
            or any(
                any(n > 0 for n in by_player.get(pid, {}).values())
                for by_player in system.planet_units.values()
            )
        )
        if own:
            result.append(position)
            continue
        probe = s.model_copy(update={"active_system": position})
        if movement.legal_move_sources(probe, ctx.grid, ctx.registry, pid):
            result.append(position)
    return result


def action_card_plays(obs: Observation, ctx: EngineContext) -> list[Action]:
    """Zagrywalne TERAZ karty akcji z oknem ACTION, z silnikowym efektem (warianty wyborów)."""
    s = obs.view
    pid = obs.player_id
    try:
        rows = action_cards.playability(s, ctx.registry, pid)
    except ValueError:
        return []
    result: list[Action] = []
    for row in rows:
        if not row["playable"] or row["reaction"] or not row["implemented"]:
            continue
        card_id = str(row["card_id"])
        try:
            _implemented, inputs = action_cards.card_inputs(s, ctx.registry, pid, card_id)
        except ValueError:
            continue
        result.extend(
            tac.ActionCardPlay(player_id=pid, card_id=card_id, params=params)
            for params in param_variants(inputs)
        )
    return result


def param_variants(
    inputs: list[dict[str, Any]], limit: int = _MAX_CARD_VARIANTS
) -> list[dict[str, Any]]:
    """Kilka poprawnych odpowiedzi formularza: każda opcja pierwszego wyboru, reszta minimalna."""
    base: dict[str, Any] = {}
    first_choice: tuple[str, list[Any]] | None = None
    for spec in inputs:
        kind = spec.get("kind")
        key = str(spec.get("key", ""))
        options = [o["value"] for o in spec.get("options", [])]
        if kind == "choice" and options:
            base[key] = options[0]
            if first_choice is None:
                first_choice = (key, options)
        elif kind == "multi":
            base[key] = options[: max(int(spec.get("min", 0) or 0), 1 if options else 0)]
        elif kind == "number":
            base[key] = spec.get("min", 0)
    if first_choice is None:
        return [base]
    key, options = first_choice
    return [{**base, key: value} for value in options[:limit]]


# --- Kroki akcji taktycznej ------------------------------------------------------------------


def tactical_step(obs: Observation, ctx: EngineContext) -> list[Action]:
    """Aktywny gracz w trakcie akcji taktycznej (bez trwającej walki / inwazji / eksploracji)."""
    s = obs.view
    pid = obs.player_id
    step = s.tactical_step
    end = act.TacticalEnd(player_id=pid)
    nxt = tac.TacticalNext(player_id=pid)
    if step is TacticalStep.MOVEMENT:
        return [end, nxt, *_moves(s, ctx, pid)]
    if step is TacticalStep.SPACE_COMBAT and battle.space_combat_required(s):
        return [tac.BattleStart(player_id=pid)]
    if step is TacticalStep.INVASION and s.invasion is None:
        return [nxt, tac.InvasionBegin(player_id=pid)]
    if step is TacticalStep.PRODUCTION:
        return [nxt, *production_orders(s, ctx, pid)]
    return [nxt, end]


def _moves(s: GameState, ctx: EngineContext, pid: str) -> list[Action]:
    result: list[Action] = []
    sources = movement.legal_move_sources(s, ctx.grid, ctx.registry, pid)
    for source, movable in sorted(sources.items()):
        system = s.systems[source]
        ships = {bt: system.space_units[pid][bt] for bt in movable}
        result.append(tac.TacticalMove(player_id=pid, from_position=source, ships=ships))
        cargo = _cargo(s, ctx, pid, source, ships)
        if cargo:
            result.append(
                tac.TacticalMove(player_id=pid, from_position=source, ships=ships, cargo=cargo)
            )
    return result


def _cargo(
    s: GameState, ctx: EngineContext, pid: str, source: str, ships: dict[str, int]
) -> tuple[tac.CargoItem, ...]:
    """Ładunek do pełnej pojemności: siły z przestrzeni i z własnych planet systemu źródłowego."""
    room = 0
    for bt, n in ships.items():
        unit = invasion.unit_variant(s, ctx.registry, pid, bt)
        room += n * int((unit.capacity_value if unit is not None else 0) or 0)
    if room <= 0:
        return ()
    system = s.systems[source]
    zones: list[tuple[str, dict[str, int]]] = [("space", system.space_units.get(pid, {}))]
    zones += [(planet, units.get(pid, {})) for planet, units in sorted(system.planet_units.items())]
    items: list[tac.CargoItem] = []
    for zone, units in zones:
        for bt in _CARGO:
            if zone != "space" and bt == "fighter":
                continue
            take = min(units.get(bt, 0), room)
            if take > 0:
                items.append(tac.CargoItem(base_type=bt, count=take, from_zone=zone))
                room -= take
    return tuple(items)


def production_orders(s: GameState, ctx: EngineContext, pid: str) -> list[Action]:
    position = production.production_system(s)
    if position is None or production.remaining_production(s, ctx.grid, ctx.registry, pid) <= 0:
        return []
    ground = production.allowed_ground_zones(s, ctx.registry, pid, position)
    result: list[Action] = []
    for unit in tactical.production_help(s, ctx.registry, pid).units:
        if unit.base_type in production.STRUCTURES:
            continue
        zone = "space" if is_space_unit(unit.base_type) else (ground[0] if ground else None)
        if zone is None:
            continue
        item = tac.ProduceItem(
            base_type=unit.base_type, count=max(1, int(unit.units_per_cost or 1)), zone=zone
        )
        result.append(tac.TacticalProduce(player_id=pid, orders=(item,)))
    return result


# --- Walka -----------------------------------------------------------------------------------


def combat(obs: Observation, ctx: EngineContext) -> list[Action]:
    """Prowadzenie walki bez trafień do pokrycia: rzuty atakującego, odwrót, zamknięcie."""
    s = obs.view
    pid = obs.player_id
    fight = s.active_combat
    assert fight is not None
    if fight.step is CombatStep.RETREAT:
        if pid not in fight.retreating:
            return []
        return [
            tac.BattleRetreat(player_id=pid, destination=d)
            for d in retreat.retreat_destinations(s, ctx.grid, fight.position, pid)
        ]
    if pid != fight.attacker:
        return []
    if fight.step is CombatStep.AFB:
        return [tac.BattleAfb(player_id=pid)]
    if fight.step is CombatStep.ROLL:
        return [tac.BattleRoll(player_id=pid)]
    if fight.step is CombatStep.DONE:
        return [tac.BattleClose(player_id=pid)]
    return []  # TRIGGERS (oferty), ASSIGN / ANNOUNCE (okna)


def retreat_window(obs: Observation) -> list[Action]:
    pid = obs.player_id
    return [
        tac.BattleAnnounceRetreat(player_id=pid, announce=False),
        tac.BattleAnnounceRetreat(player_id=pid, announce=True),
    ]


def capacity_window(obs: Observation, ctx: EngineContext) -> list[Action]:
    window = obs.view.pending_window
    assert window is not None
    position = str(window.context.get("position", ""))
    report = capacity.capacity_report(obs.view, ctx.registry, position, obs.player_id)
    return [tac.CapacityResolve(player_id=obs.player_id, remove=capacity.auto_removal(report))]


def space_cannon_window(obs: Observation, ctx: EngineContext) -> list[Action]:
    """Okno Space Cannon Offense: cel przypisuje straty, bieżący strzelec strzela albo pasuje."""
    s = obs.view
    pid = obs.player_id
    pending = space_cannon.pending_hits(s)
    if pending is not None:
        if pending.target != pid:
            return []
        units = space_cannon.combat_view(s, pid, ctx.registry).values()
        required = space_cannon.required_hits(s, pid, ctx.registry)
        return [
            tac.SpaceCannonAssign(player_id=pid, sustain=a, destroy=b, destroy_damaged=c)
            for a, b, c in loss_plans(units, required, battle.sustain_cancels(s, pid))
        ]
    window = s.pending_window
    if window is None or window.current_responder != pid:
        return []
    fire = [
        tac.SpaceCannonFire(player_id=pid, target=t)
        for t in space_cannon.offense_targets(s, pid)
    ]
    return [tac.SpaceCannonPass(player_id=pid), *fire]


# --- Inwazja ---------------------------------------------------------------------------------


def invasion_step(obs: Observation, ctx: EngineContext) -> list[Action]:
    s = obs.view
    pid = obs.player_id
    inv = s.invasion
    assert inv is not None
    nxt = tac.InvasionNext(player_id=pid)
    # Trafienia czekające na obrońców planet (bombardowanie) albo atakującego (obrona).
    for planet in sorted(inv.bombard_pending):
        if inv.bombard_pending[planet] > 0 and invasion.bombard_defender(inv, planet) == pid:
            return _planet_losses(s, ctx, pid, planet, tac.InvasionBombardAssign, bombard=True)
    if inv.phase is InvasionPhase.SPACE_CANNON_DEFENSE:
        for planet in sorted(inv.defense_pending):
            if inv.defense_pending[planet] > 0:
                if pid != inv.attacker:
                    return []
                return _planet_losses(s, ctx, pid, planet, tac.InvasionDefenseAssign, bombard=False)
        for planet in invasion.undefended_open(s, ctx.registry):
            owners = {sh.player_id for sh in invasion.defense_shooters(s, ctx.registry, planet)}
            if pid in owners:
                return [
                    tac.InvasionDefensePass(player_id=pid, planet=planet),
                    tac.InvasionDefenseFire(player_id=pid, planet=planet),
                ]
            if owners:
                return []  # czekamy na obrońcę tej planety
    if pid != inv.attacker or inv.bombard_pending:
        return []
    if inv.phase is InvasionPhase.BOMBARDMENT:
        return [nxt, *_bombards(s, ctx, pid)]
    if inv.phase is InvasionPhase.COMMIT:
        return [nxt, *_commits(s, ctx, pid)]
    if inv.phase is InvasionPhase.GROUND_COMBAT:
        planets = invasion.combat_planets(s, ctx.registry)
        if planets:
            return [tac.BattleStart(player_id=pid, planet=p) for p in planets]
    return [nxt]


def _planet_losses(
    s: GameState,
    ctx: EngineContext,
    pid: str,
    planet: str,
    cls: type[tac.InvasionBombardAssign] | type[tac.InvasionDefenseAssign],
    *,
    bombard: bool,
) -> list[Action]:
    inv = s.invasion
    assert inv is not None
    units = battle.combat_units(
        s, ctx.grid, ctx.registry, kind="ground", position=inv.position, planet=planet,
        player_id=pid,
    )
    required = (
        invasion.required_bombard_hits(s, ctx.grid, ctx.registry, planet)
        if bombard
        else invasion.required_defense_hits(s, ctx.grid, ctx.registry, planet)
    )
    return [
        cls(player_id=pid, planet=planet, sustain=a, destroy=b, destroy_damaged=c)
        for a, b, c in loss_plans(units, required, battle.sustain_cancels(s, pid))
    ]


def _bombards(s: GameState, ctx: EngineContext, pid: str) -> list[Action]:
    groups = invasion.bombard_groups(s, ctx.registry)
    if not groups:
        return []
    return [
        tac.InvasionBombard(
            player_id=pid, assignments=tuple((g.base_type, planet, g.count) for g in groups)
        )
        for planet in invasion.bombard_targets(s, ctx.registry)
    ]


def _commits(s: GameState, ctx: EngineContext, pid: str) -> list[Action]:
    inv = s.invasion
    assert inv is not None
    system = s.systems.get(inv.position)
    if system is None:
        return []
    in_space = system.space_units.get(pid, {})
    forces = {bt: n for bt, n in in_space.items() if bt in ("infantry", "mech") and n > 0}
    result: list[Action] = []
    if forces:
        result.extend(
            tac.InvasionCommit(player_id=pid, commits={planet: dict(forces)})
            for planet in invasion.system_planets(s, ctx.registry, inv.position)
        )
    if invasion.custodians_block_reason(s, ctx.registry) is None:
        player = s.players[pid]
        ready = [
            planet
            for sys in s.systems.values()
            for planet, owner in sys.planet_owners.items()
            if owner == pid and planet not in player.exhausted_planets
        ]
        result.append(
            tac.InvasionCustodians(player_id=pid, planets=tuple(sorted(ready)), trade_goods=0)
        )
    return result


# --- Eksploracja -----------------------------------------------------------------------------


def exploration_step(obs: Observation, ctx: EngineContext) -> list[Action]:
    s = obs.view
    pid = obs.player_id
    ex = s.exploration
    assert ex is not None
    if ex.player_id != pid:
        return []
    if ex.current is not None:
        result: list[Action] = []
        for option in exploration.options_for(s, ctx.registry):
            if not option.enabled:
                continue
            if option.params:
                result.extend(
                    tac.ExplorationResolve(player_id=pid, option=option.id, param=p)
                    for p, _label in option.params
                )
            else:
                result.append(tac.ExplorationResolve(player_id=pid, option=option.id))
        return result
    if not ex.queue:
        return [tac.ExplorationFinish(player_id=pid)]
    draws: list[Action] = []
    for planet in ex.queue:
        traits = exploration.planet_traits(ctx.registry, planet)
        if len(traits) == 1:
            draws.append(tac.ExplorationDraw(player_id=pid, planet=planet))
        else:
            draws.extend(tac.ExplorationDraw(player_id=pid, planet=planet, deck=t) for t in traits)
    return draws


# Okna obsługiwane przez ten moduł (``legal._window``).
WINDOW_HANDLERS = {
    WindowType.SPACE_CANNON,
    WindowType.COMBAT_RETREAT,
    WindowType.CAPACITY,
}
