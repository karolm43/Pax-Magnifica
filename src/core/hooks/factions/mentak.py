"""The Mentak Coalition — komplet komponentów frakcji (RULES.md 62.8).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("mentak")``, ``units``).
Rulingi: ``docs/rules_tirules/F_mentak.md``. Punkty silnika dodane dla Mentaka: trafienia startu
walki (``battle.add_start_hits``), utrata Sustain Damage (``combat.sustain_denied``), wartość TG w
płatności (``payment.trade_good_value``), przyczyna zdobycia TG (``economy.gain_trade_goods``),
ślad strat całej walki (``ActiveCombat.destroyed_all``) i typ statku w przelocie przez obce statki.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    battle,
    board_reinforcements,
    card_draw,
    economy,
    faction_components,
    leaders,
    promissory_notes,
    rules_hooks,
)
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.dice import DIE_SIDES, next_rng
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import ActiveCombat, GameState, ProductionGrant
from src.core.hooks.reactions_combat import DIRECT_HIT
from src.core.neighbors import neighbors_of
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_COMBAT_SUSTAIN_DENIED,
    POINT_MOVEMENT_PASS_FOREIGN_SHIPS,
    POINT_PAYMENT_TRADE_GOOD_VALUE,
    SOURCE_EFFECT,
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
)
from src.core.state_grid import grid_from_state
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause, place_units

FACTION = "mentak"
AGENT = "mentakagent"
COMMANDER = "mentakcommander"
HERO = "mentakhero"
FLAGSHIP = "mentak_flagship"
MECH = "mentak_mech"
PROMISE = "pop"
MIRROR = "mc"
SALVAGE = "so"
BREAKTHROUGH = "mentakbt"
CORSAIR = "mentak_cruiser3"

PILLAGE = "pillage"
SMENTARION = "smentarion"  # ``FACTION_ABILITY_USED``: przeciwnik wybiera notkę dla S'ula Mentarion
SLEEPER = f"leaders:{HERO}:sleeper"  # efekt Sleeper Cell na czas walki (data: seen)
_AMBUSH_SHIPS = ("cruiser", "destroyer")  # „up to 2 of your cruisers or destroyers”
_AMBUSH_MAX = 2
_PILLAGE_MIN_TG = 3  # „If they have 3 or more trade goods”
_COMMANDER_CRUISERS = 4  # „Have 4 cruisers on the game board.”
_TAKE_TG, _TAKE_COMMODITY = "trade_good", "commodity"
_FIGHTER = "fighter"
_SPACE = "space"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _name(registry: Any, state: GameState, player_id: str) -> str:
    player = state.players.get(player_id)
    faction = registry.factions.get(player.faction or "") if player is not None else None
    return faction.name if faction is not None else player_id


def _mentak_players(state: GameState) -> list[str]:
    return [pid for pid, p in state.players.items() if p.faction == FACTION]


def _my_space_combat(state: GameState, player_id: str) -> ActiveCombat | None:
    """Trwająca walka kosmiczna, w której gracz walczy (albo ``None``)."""
    combat = state.active_combat
    if combat is None or combat.kind != _SPACE:
        return None
    if player_id not in (combat.attacker, combat.defender):
        return None
    return combat


def _opponent(combat: ActiveCombat, player_id: str) -> str:
    return combat.defender if player_id == combat.attacker else combat.attacker


# ------------------------------------------------------------------------------------ Ambush


def _ambush_ships(state: GameState, player_id: str) -> dict[str, int]:
    combat = _my_space_combat(state, player_id)
    system = state.systems.get(combat.position) if combat is not None else None
    if system is None:
        return {}
    own = system.space_units.get(player_id, {})
    return {bt: own.get(bt, 0) for bt in _AMBUSH_SHIPS if own.get(bt, 0) > 0}


def _ambush_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("kind") == _SPACE and bool(_ambush_ships(state, player_id))


def ambush_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Krążowniki i niszczyciele Mentaka w systemie walki - po jednej opcji na statek."""
    player = state.players[player_id]
    options: list[dict[str, Any]] = []
    for base_type, count in _ambush_ships(state, player_id).items():
        unit = resolve_unit_variant(
            registry, player.faction, player.technologies, base_type, player.breakthrough_unlocked,
        player.breakthrough_flipped,
        )
        hits_on = unit.combat_hits_on if unit is not None else None
        name = unit_name(state, registry, player_id, base_type)
        for index in range(count):
            label = f"{name} {index + 1}" + (f" (hits on {hits_on})" if hits_on else "")
            meta = oi.unit_meta(base_type, player_id, player.faction, player.color, 1)
            options.append(oi.option(f"{base_type}:{index}", label, meta=meta))
    most = min(_AMBUSH_MAX, len(options))
    return [oi.multi("ships", "Ships that roll (up to 2)", options, 1, max(1, most))]


@on_event(
    GameEvent.COMBAT, Moment.START, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_ambush_ready, inputs=ambush_inputs,
    covers="abilities:ambush", label="Ambush",
)
def ambush(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Ambush: At the start of a space combat: You may roll 1 die for each of up to 2 of your
    cruisers or destroyers in the system. For each result equal to or greater than that ship's
    combat value, produce 1 hit; your opponent must assign it to 1 of their ships.

    Rzut bez modyfikatorów i przerzutów (F_mentak); trafienia przypisuje przeciwnik w kroku ASSIGN
    (Sustain Damage dozwolone). Kości animuje okno bitwy (wpis ``AMBUSH`` w logu walki).
    """
    combat = _my_space_combat(state, player_id)
    if combat is None:
        raise ValueError("Ambush is used at the start of a space combat you fight in.")
    chosen: dict[str, int] = {}
    for item in ctx.get("params", {}).get("ships") or []:
        base_type = str(item).partition(":")[0]
        chosen[base_type] = chosen.get(base_type, 0) + 1
    available = _ambush_ships(state, player_id)
    if not chosen or sum(chosen.values()) > _AMBUSH_MAX:
        raise ValueError("Choose 1 or 2 of your cruisers or destroyers.")
    if any(n > available.get(bt, 0) for bt, n in chosen.items()):
        raise ValueError("Those ships are not in the combat.")
    registry = _registry()
    player = state.players[player_id]
    rng = next_rng(state)
    entries: list[dict[str, Any]] = []
    total = 0
    for base_type, count in sorted(chosen.items()):
        unit = resolve_unit_variant(
            registry, player.faction, player.technologies, base_type, player.breakthrough_unlocked,
        player.breakthrough_flipped,
        )
        if unit is None or unit.combat_hits_on is None:
            continue
        dice = [rng.randint(1, DIE_SIDES) for _ in range(count)]
        hits = sum(1 for d in dice if d >= unit.combat_hits_on)
        total += hits
        entries.append({
            "baseType": base_type, "name": unit.name, "hitsOn": unit.combat_hits_on,
            "modifier": 0, "dice": dice, "hits": hits,
        })
    opponent = _opponent(combat, player_id)
    combat.log = [*combat.log, {
        "round": combat.round, "phase": "AMBUSH",
        "rolls": {player_id: entries, opponent: []},
        "hits": {player_id: total, opponent: 0},
        "losses": {}, "sustained": {},
    }]
    battle.add_start_hits(state, opponent, total)
    ability_notes.note(state, player_id, "abilities:ambush", f"{total} hit(s)")


# ----------------------------------------------------------------------------------- Pillage


def pillage_reason(state: GameState, player_id: str, target: str) -> str | None:
    """Powód, dla którego Mentak ``player_id`` NIE może teraz użyć Pillage na ``target``."""
    victim = state.players.get(target)
    if victim is None or target == player_id:
        return "Pillage is used against another player."
    if target not in neighbors_of(player_id, state, grid_from_state(state, _registry())):
        return "Pillage is used only against your neighbors."
    if victim.trade_goods < _PILLAGE_MIN_TG:
        return "That player has fewer than 3 trade goods."
    if PROMISE in victim.promissory_notes_in_play:
        return "That player has Promise of Protection in their play area."
    return None


def _pillage_target(ctx: Mapping[str, Any]) -> str:
    return str(ctx.get("target") or ctx.get("player") or "")


def pillage_inputs(
    state: GameState, registry: Any, _player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    target = _pillage_target(ctx)
    victim = state.players.get(target)
    if victim is None:
        return [oi.choice("take", "Take", [])]
    who = _name(registry, state, target)
    options = []
    if victim.trade_goods >= 1:
        options.append(oi.option(_TAKE_TG, f"1 trade good from {who}"))
    if victim.commodities >= 1:
        options.append(oi.option(_TAKE_COMMODITY, f"1 commodity from {who} (becomes a trade good)"))
    return [oi.choice("take", f"Pillage {who}", options, always=True)]


def _pillage(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Pillage: If they have 3 or more trade goods, you may take 1 of their trade goods or
    commodities (P2 ✅: commodity trafia do Mentaka jako trade good - R_commodities)."""
    target = _pillage_target(ctx)
    reason = pillage_reason(state, player_id, target)
    if reason is not None:
        raise ValueError(reason)
    take = str(ctx.get("params", {}).get("take") or _TAKE_TG)
    if take == _TAKE_COMMODITY:
        economy.give_to_player(state, target, player_id, commodities=1, cause=PILLAGE)
    else:
        economy.give_to_player(state, target, player_id, trade_goods=1, cause=PILLAGE)
    ability_notes.note(
        state, player_id, "abilities:pillage", f"against {_name(_registry(), state, target)}"
    )
    faction_components.ability_used(state, player_id, PILLAGE, target)


def _gain_pillageable(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    # P1 ✅: TG z transakcji dają jedno Pillage na samą transakcję; zamiana commodities to nie
    # „zdobycie” (F_mentak, F_vuilraith).
    if ctx.get("cause") in ("transaction", "convert", PILLAGE):
        return False
    return pillage_reason(state, player_id, str(ctx.get("player") or "")) is None


@on_event(
    GameEvent.TRADE_GOODS_GAINED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_gain_pillageable, inputs=pillage_inputs,
    covers=f"abilities:{PILLAGE}", label="Pillage",
)
def pillage_on_gain(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Pillage: After 1 of your neighbors gains trade goods ..."""
    _pillage(state, player_id, ctx)


def _side_inputs(key: str) -> Any:
    def inputs(
        state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        return pillage_inputs(state, registry, player_id, {**ctx, "target": ctx.get(key)})

    return inputs


def _side_ready(key: str) -> Any:
    def condition(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
        return pillage_reason(state, player_id, str(ctx.get(key) or "")) is None

    return condition


@on_event(
    GameEvent.TRANSACTION, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_side_ready("player"), inputs=_side_inputs("player"),
    covers=f"abilities:{PILLAGE}", label="Pillage (transaction)",
)
def pillage_active_side(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Pillage: After 1 of your neighbors ... resolves a transaction (strona aktywna)."""
    _pillage(state, player_id, {**ctx, "target": ctx.get("player")})


@on_event(
    GameEvent.TRANSACTION, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_side_ready("partner"), inputs=_side_inputs("partner"),
    covers=f"abilities:{PILLAGE}", label="Pillage (transaction partner)",
)
def pillage_partner_side(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Pillage przeciw partnerowi transakcji (F_mentak: także przeciw obu stronom i przeciw
    partnerowi własnej transakcji Mentaka)."""
    _pillage(state, player_id, {**ctx, "target": ctx.get("partner")})


# ---------------------------------------------------------------- Promise of Protection (notka)


@register_effect(f"promissory_notes:{PROMISE}")
def promise_of_protection(
    _state: GameState, _registry: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """Promise of Protection: ACTION: Place this card faceup in your play area. While this card is
    in your play area, the Mentak player cannot use their Pillage faction ability against you
    (warunek w ``pillage_reason``; położenie robi ``promissory_play``)."""


def _activated_mentak_system(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    system = state.systems.get(str(ctx.get("position")))
    if ctx.get("player") != player_id or system is None:
        return False
    present = set(system.space_units) | {
        pid for units in system.planet_units.values() for pid in units
    }
    return bool(set(_mentak_players(state)) & present) and (
        PROMISE in state.players[player_id].promissory_notes_in_play
    )


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_PROMISSORY, PROMISE),
    condition=_activated_mentak_system, covers=f"promissory_notes:{PROMISE}",
    label="Promise of Protection returns to Mentak",
)
def promise_return(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """If you activate a system that contains 1 or more of the Mentak player's units, return this
    card to the Mentak player (także same struktury - F_mentak)."""
    owner = next(iter(_mentak_players(state)), None)
    if owner is not None:
        promissory_notes.return_from_play(state, player_id, owner, PROMISE)


# ------------------------------------------------------------------- Mirror Computing (tech)


@register(
    POINT_PAYMENT_TRADE_GOOD_VALUE, HookSource(SOURCE_TECHNOLOGY, MIRROR), HookKind.MODIFY,
    covers=f"technologies:{MIRROR}",
)
def mirror_computing(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Mirror Computing: When you spend trade goods, each trade good is worth 2 resources or
    influence instead of 1."""
    return 1


# ----------------------------------------------------------------- Salvage Operations (tech)


def _fought_and_decided(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("kind") == _SPACE
        and bool(ctx.get("winner"))
        and player_id in (ctx.get("attacker"), ctx.get("defender"))
    )


@on_event(
    GameEvent.COMBAT, Moment.END, HookSource(SOURCE_TECHNOLOGY, SALVAGE),
    condition=_fought_and_decided, covers=f"technologies:{SALVAGE}",
    label="Salvage Operations: +1 trade good",
)
def salvage_trade_good(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Salvage Operations: After you win or lose a space combat, gain 1 trade good (remis = nic,
    F_mentak)."""
    economy.gain_trade_goods(state, player_id, 1)


def salvage_types(state: GameState, player_id: str) -> list[str]:
    """Typy statków zniszczonych w walce, które Mentak może wyprodukować (z kosztem w danych)."""
    combat = state.active_combat
    if combat is None:
        return []
    registry = _registry()
    player = state.players[player_id]
    types: list[str] = []
    for base_type in sorted({str(e.get("base_type")) for e in combat.destroyed_all}):
        unit = resolve_unit_variant(
            registry, player.faction, player.technologies, base_type, player.breakthrough_unlocked,
        player.breakthrough_flipped,
        )
        if unit is None or unit.cost is None or not is_space_unit(base_type):
            continue  # np. War Sun bez technologii (F_mentak)
        if not board_reinforcements.can_place(state, player_id, base_type):
            continue  # pusta rezerwa i nic do zdjęcia z planszy (F_mentak)
        types.append(base_type)
    return types


def _salvage_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("kind") == _SPACE
        and ctx.get("winner") == player_id
        and state.production_grant is None
        and bool(salvage_types(state, player_id))
    )


@on_event(
    GameEvent.COMBAT_WON, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, SALVAGE),
    optional=True, condition=_salvage_ready, covers=f"technologies:{SALVAGE}",
    label="Salvage Operations: produce 1 ship",
)
def salvage_produce(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Salvage Operations: ... if you won the combat, you may also produce 1 ship in that system of
    any ship type that was destroyed during the combat (płatny - F_mentak; okno produkcji).
    Pusta rezerwa: okno produkcji pozwala zdjąć statek z systemu bez żetonu (F_mentak)."""
    types = salvage_types(state, player_id)
    if not types or state.production_grant is not None:
        raise ValueError("There is nothing to salvage right now.")
    state.production_grant = ProductionGrant(
        player_id=player_id, position=str(ctx.get("position")), units=1, free=True,
        ships_only=True, allowed_types=types, source="Salvage Operations",
    )


# ------------------------------------------------------------------------- Suffi An (agent)


def _agent_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Any player's Pillage against another player: the Yssaril copying Suffi An with Ssruu
    answers the Mentak's Pillage (F_yssaril ssruu 4, RULES.md 62.22)."""
    target = ctx.get("target")
    return (
        target in state.players and target != player_id
        and leaders.is_ready(state, _registry(), player_id, AGENT)
    )


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    where={"ability": PILLAGE}, optional=True, condition=_agent_ready,
    covers=f"leaders:{AGENT}", label="Suffi An: both draw 1 action card",
)
def suffi_an(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Suffi An: After the Pillage faction ability is used against another player: You may exhaust
    this card: if you do, you and that player each draw 1 action card."""
    target = str(ctx.get("target") or "")
    if target not in state.players:
        raise ValueError("Unknown Pillage target.")
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT)
    card_draw.draw_action_card(state, player_id)
    card_draw.draw_action_card(state, target)


# ------------------------------------------------------------------ S'ula Mentarion (commander)


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 4 cruisers on the game board."""
    cruisers = sum(
        s.space_units.get(player_id, {}).get("cruiser", 0) for s in state.systems.values()
    )
    return cruisers >= _COMMANDER_CRUISERS


def _commander_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("kind") != _SPACE or ctx.get("winner") != player_id:
        return False
    other = ctx.get("defender") if ctx.get("attacker") == player_id else ctx.get("attacker")
    victim = state.players.get(str(other))
    return victim is not None and bool(victim.private.promissory_notes)


@on_event(
    GameEvent.COMBAT_WON, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_commander_ready, covers=f"leaders:{COMMANDER}",
    label="S'ula Mentarion: take a promissory note",
)
def sula_mentarion(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """S'ula Mentarion: After you win a space combat: You may force your opponent to give you 1
    promissory note from their hand (wybiera przeciwnik; to nie jest transakcja - F_mentak)."""
    other = ctx.get("defender") if ctx.get("attacker") == player_id else ctx.get("attacker")
    faction_components.ability_used(state, player_id, SMENTARION, str(other))


def _note_label(state: GameState, registry: Any, note_id: str) -> str:
    """Pełna nazwa notki (jak w panelu gracza) zamiast id z kolorem (``grn_an``)."""
    from src.core import promissory_play  # lokalnie: promissory_play importuje hooki

    try:
        return promissory_play.note_text(state, registry, note_id)[0]
    except ValueError:
        return note_id


def note_choice_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    hand = state.players[decider].private.promissory_notes
    options = [
        oi.option(n, _note_label(state, registry, n), f"{n}#{i}") for i, n in enumerate(hand)
    ]
    return [oi.choice("note", "Promissory note you give to the Mentak player", options)]


def _target_decides(_state: GameState, _owner: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    where={"ability": SMENTARION}, decide=True, decider=_target_decides,
    inputs=note_choice_inputs, label="S'ula Mentarion: give a promissory note",
)
def sula_mentarion_give(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Przeciwnik oddaje wybraną notkę z ręki (decyzja obowiązkowa przeciwnika)."""
    if ctx.get("player") != player_id:
        return
    note = str(ctx.get("params", {}).get("note") or "")
    promissory_notes.transfer(state, str(ctx["target"]), player_id, note)


# --------------------------------------------------- Ipswitch, Loose Cannon — Sleeper Cell (hero)


def _hero_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("kind") == _SPACE
        and _my_space_combat(state, player_id) is not None
        and leaders.is_ready(state, _registry(), player_id, HERO)
    )


@on_event(
    GameEvent.COMBAT, Moment.START, HookSource(SOURCE_LEADER, HERO),
    optional=True, condition=_hero_ready, covers=f"leaders:{HERO}",
    label="Ipswitch: Sleeper Cell",
)
def sleeper_cell(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Ipswitch, Loose Cannon — Sleeper Cell: At the start of a space combat that you are
    participating in: You may purge this card; if you do, for each other player's ship that is
    destroyed during this combat, place 1 ship of that type from your reinforcements in the active
    system. (Statki zniszczone przed użyciem się nie liczą - F_mentak.)"""
    combat = _my_space_combat(state, player_id)
    if combat is None:
        raise ValueError("Sleeper Cell is used at the start of a space combat you fight in.")
    faction_components.pay_cost(state, _registry(), player_id, "leader", HERO)
    active_effects.add_effect(
        state, SLEEPER, Duration.COMBAT, owner=player_id,
        data={"seen": len(combat.destroyed_all)},
    )


def _sleeper_pending(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    combat = _my_space_combat(state, player_id)
    effect = next(iter(active_effects.effects_for(state, player_id, SLEEPER)), None)
    return (
        combat is not None
        and effect is not None
        and len(combat.destroyed_all) > int(effect.data.get("seen", 0))
    )


_NO_SOURCE = "none"


def _fresh_sleepers(state: GameState, player_id: str) -> list[str]:
    """Typy statków do postawienia: statki przeciwnika zniszczone od ostatniego sprawdzenia."""
    combat = _my_space_combat(state, player_id)
    effect = next(iter(active_effects.effects_for(state, player_id, SLEEPER)), None)
    if combat is None or effect is None:
        return []
    seen = int(effect.data.get("seen", 0))
    early = {int(i) for i in effect.data.get("early") or ()}
    found: list[str] = []
    for index, entry in enumerate(combat.destroyed_all):
        if index < seen or index in early or entry.get("player") == player_id:
            continue
        base_type = str(entry.get("base_type"))
        if _sleeper_type_ok(state, player_id, base_type):
            found.append(base_type)
    return found


def _sleeper_type_ok(state: GameState, player_id: str, base_type: str) -> bool:
    """Statek, który Mentak może postawić: jest w jego talii jednostek (War Sun tylko z
    technologią) i jest statkiem - nie siła naziemna/struktura „jako statek" (F_mentak)."""
    player = state.players[player_id]
    unit = resolve_unit_variant(
        _registry(), player.faction, player.technologies, base_type, player.breakthrough_unlocked,
        player.breakthrough_flipped,
    )
    return unit is not None and unit.cost is not None and is_space_unit(base_type)


def sleeper_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Pusta rezerwa: skąd zdjąć statek (F_mentak) - albo go nie stawiać (wybór gracza)."""
    inputs: list[dict[str, Any]] = []
    left: dict[str, int | None] = {}
    for index, base_type in enumerate(_fresh_sleepers(state, player_id)):
        if base_type not in left:
            left[base_type] = reinforcements_left(state, player_id, base_type)
        stock = left[base_type]
        if stock is None or stock > 0:
            left[base_type] = None if stock is None else stock - 1
            continue
        sources = board_reinforcements.source_options(state, registry, player_id, base_type)
        if sources:
            name = unit_name(state, registry, player_id, base_type)
            inputs.append(oi.choice(
                f"source:{index}", f"No {name} in your reinforcements - take one from the board?",
                [oi.option(_NO_SOURCE, "Do not place it")]
                + [oi.option(value, label) for value, label in sources],
            ))
    return inputs


def _place_sleepers(
    state: GameState, player_id: str, ctx: Mapping[str, Any] | None = None
) -> None:
    """Stawia statki za statki przeciwnika zniszczone od ostatniego sprawdzenia (bez kosztu).

    Pusta rezerwa: statek zdjęty z systemu bez żetonu Mentaka, gdy gracz tak wybrał
    (F_mentak, R_component_limitations - ``core.board_reinforcements``)."""
    combat = _my_space_combat(state, player_id)
    effect = next(iter(active_effects.effects_for(state, player_id, SLEEPER)), None)
    if combat is None or effect is None:
        return
    fresh = _fresh_sleepers(state, player_id)
    effect.data = {**effect.data, "seen": len(combat.destroyed_all)}
    system = state.systems[combat.position]
    params = (ctx or {}).get("params") or {}
    for index, base_type in enumerate(fresh):
        if not board_reinforcements.needs_board_source(state, player_id, base_type):
            place_units(state, system, _SPACE, player_id, base_type, 1, UnitCause.PLACED)
            continue
        source = str(params.get(f"source:{index}") or _NO_SOURCE)
        if source != _NO_SOURCE:
            board_reinforcements.place_unit(
                state, system, _SPACE, player_id, base_type, source=source
            )


@on_event(
    GameEvent.COMBAT_ROUND, Moment.END, HookSource(SOURCE_EFFECT, SLEEPER),
    condition=_sleeper_pending, decide=True, inputs=sleeper_inputs, covers=f"leaders:{HERO}",
    label="Sleeper Cell: place ships",
)
def sleeper_after_losses(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Po przypisaniu strat obu stron (F_mentak: „before the Mentak player places")."""
    _place_sleepers(state, player_id, ctx)


@on_event(
    GameEvent.COMBAT_ROUND, Moment.START, HookSource(SOURCE_EFFECT, SLEEPER),
    condition=_sleeper_pending, decide=True, inputs=sleeper_inputs, covers=f"leaders:{HERO}",
    label="Sleeper Cell: place ships",
)
def sleeper_before_round(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Straty z Ambush (przed 1. rundą) - statki przed rzutami rundy."""
    _place_sleepers(state, player_id, ctx)


def _own_direct_hit(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("player") == player_id
        and ctx.get("card") in DIRECT_HIT
        and _my_space_combat(state, player_id) is not None
    )


@on_event(
    GameEvent.ACTION_CARD_PLAYED, Moment.WHEN, HookSource(SOURCE_EFFECT, SLEEPER),
    condition=_own_direct_hit, covers=f"leaders:{HERO}", label="Sleeper Cell: Direct Hit",
)
def sleeper_direct_hit(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Mentak zagrywa Direct Hit: statek zniszczony tą kartą zastępuje się OD RAZU, zanim inne
    statki użyją Sustain Damage (F_mentak 7.1) - znacznik dla ``sleeper_on_direct_hit``."""
    for effect in active_effects.effects_for(state, player_id, SLEEPER):
        effect.data = {**effect.data, "direct_hit": True}


def _direct_hit_loss(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    effect = next(iter(active_effects.effects_for(state, player_id, SLEEPER)), None)
    return (
        effect is not None
        and bool(effect.data.get("direct_hit"))
        and ctx.get("player") != player_id
        and ctx.get("zone") == _SPACE
        and _my_space_combat(state, player_id) is not None
    )


@on_event(
    GameEvent.UNIT_DESTROYED, Moment.AFTER, HookSource(SOURCE_EFFECT, SLEEPER),
    condition=_direct_hit_loss, covers=f"leaders:{HERO}", label="Sleeper Cell: place ship",
)
def sleeper_on_direct_hit(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """F_mentak 7.1: po Direct Hit Mentaka statek tego typu staje od razu (może jeszcze w tej
    rundzie użyć Sustain Damage). Pusta rezerwa: wybór źródła z planszy zostaje na koniec rundy
    (zwykła decyzja Sleeper Cell)."""
    combat = _my_space_combat(state, player_id)
    effect = next(iter(active_effects.effects_for(state, player_id, SLEEPER)), None)
    if combat is None or effect is None:
        return
    data = {k: v for k, v in effect.data.items() if k != "direct_hit"}
    base_type = str(ctx.get("base_type"))
    index = len(combat.destroyed_all) - 1
    if (
        index >= int(data.get("seen", 0))
        and _sleeper_type_ok(state, player_id, base_type)
        and not board_reinforcements.needs_board_source(state, player_id, base_type)
    ):
        place_units(
            state, state.systems[combat.position], _SPACE, player_id, base_type, 1,
            UnitCause.PLACED,
        )
        data["early"] = [*(data.get("early") or []), index]
    effect.data = data


# ------------------------------------------------------------------- Fourth Moon, Moll Terminus


@register(
    POINT_COMBAT_SUSTAIN_DENIED, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.PERMIT,
    covers=f"units:{FLAGSHIP}",
)
def fourth_moon(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Fourth Moon: Other player's ships in this system cannot use SUSTAIN DAMAGE."""
    system = state.systems.get(str(ctx.get("position")))
    if ctx.get("zone") != _SPACE or system is None:
        return False
    if system.space_units.get(player_id, {}).get("flagship", 0) > 0:
        return True
    # F_mentak fourth-moon 1: Sustain Damage is used before the Fourth Moon is removed, so the
    # denial still holds for the rest of the round in which it was destroyed.
    combat = state.active_combat
    return (
        combat is not None
        and combat.kind == _SPACE
        and combat.position == system.position
        and any(
            e.get("player") == player_id and e.get("base_type") == "flagship"
            for e in combat.destroyed_ships
        )
    )


@register(
    POINT_COMBAT_SUSTAIN_DENIED, HookSource(SOURCE_UNIT, MECH), HookKind.PERMIT,
    covers=f"units:{MECH}",
)
def moll_terminus(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Moll Terminus: Other player's ground forces on this planet cannot use SUSTAIN DAMAGE."""
    zone = str(ctx.get("zone") or _SPACE)
    system = state.systems.get(str(ctx.get("position")))
    return (
        zone != _SPACE
        and system is not None
        and system.planet_units.get(zone, {}).get(player_id, {}).get("mech", 0) > 0
    )


# ------------------------------------------------------------------- The Table's Grace (Corsair)


# Przełom = karta z Corsairem kładziona na Cruiser II: statystyki z danych (wariant
# ``mentak_cruiser3`` w ``combat.resolve_unit_variant``), zdolność ruchu - hook jednostki niżej.
rules_hooks.declare_data_driven(f"breakthroughs:{BREAKTHROUGH}")


@register(
    POINT_MOVEMENT_PASS_FOREIGN_SHIPS, HookSource(SOURCE_UNIT, CORSAIR), HookKind.PERMIT,
    covers=f"units:{CORSAIR}",
)
def corsair_passage(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Corsair: If the active system contains another player's non-fighter ships, this unit can
    move through systems that contain other players' ships (źródło = wariant Corsair w grze:
    przełom odblokowany + Cruiser II)."""
    if ctx.get("base_type") != "cruiser":
        return False
    active = state.systems.get(state.active_system or "")
    if active is None:
        return False
    return any(
        n > 0 and bt != _FIGHTER
        for pid, units in active.space_units.items()
        if pid != player_id
        for bt, n in units.items()
    )
