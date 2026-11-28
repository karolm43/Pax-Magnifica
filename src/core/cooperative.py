"""Cooperative ("pull") effects and atomic binding deals - RULES.md 54.15. Pure functions.

Two kinds of out-of-turn effects:

* **Push** (hostile / interrupting): Sabotage, Direct Hit, Cabal's agent... Unchanged: they open
  the timed reaction window with the engine's (bluff) auto-pass (RULES.md 54.11-54.13).
* **Pull** (cooperative): an agent / ability whose "you may" helps ANOTHER player ("that player
  may...", "increase the move value of 1 of that player's ships"). Faction modules register them
  (:func:`register_pull`, :func:`register_pull_component`) with a beneficiary function. When such
  a hook fires on someone else's event the engine does NOT ask the owner - no offer, no window. It
  records a :class:`BoostOffer` the beneficiary may request (``state.boosts``) instead.

The owner decides how the effect is offered (private ``ReactionPrefs.boosts``):

* ``ask`` (default) - the beneficiary requests it, optionally with a payment, and the owner
  accepts or declines (a normal offer to the owner, timed like a reaction window);
* ``standing`` - a request paying at least ``price`` (free for ``free_for``) is accepted at once:
  the offer goes to the requester, who picks the details (e.g. which ship) or cancels;
* ``self`` - only for the owner's own events, never listed for others.

A deal is binding because it resolves immediately (R_deals): accepting runs the payment (a normal
transaction, ``transaction.resolve_transaction`` - neighbours, one per turn) and the effect on ONE
state in ONE step (:func:`accept`). Declined, withdrawn or expired = nothing is transferred.

"Watch / Hold" (:func:`set_watch`): until the end of this combat / turn the owner is offered their
pull effects unprompted, exactly as before this split.

Registration options (:class:`PullSpec`, RULES.md 54.15 e):

* ``mutual`` - the effect also serves the owner (Suffi An's draw, Carth's own commodities, an
  ``ACTION:`` the owner plays on their own units): the owner keeps the normal offer / prompt AND
  the beneficiaries may request it. ``ACTION:`` components are requestable only during the
  owner's turn and use the owner's action (RULES.md 31.8) when the deal is accepted;
* ``target`` / ``target_of`` - the input whose option names the player the effect is used on: a
  deal shows only the requester's options and is accepted only for the requester;
* ``owner_picks`` - the owner chooses the details even under a standing offer (their hand, their
  planets, their capture choice): the accepted request goes to the owner, not the requester.

CONVENTION (every faction module, user decision 2026-11-27): a component that helps, targets or
can be sold to another player ("that player may", "another player", "any player", ACTION used on
someone else) is checked against ``docs/faction_components_checklist.md`` and registered here with
:func:`register_pull` / :func:`register_pull_component` in the same block that implements it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.core import offer_inputs, reaction_prefs, rules_hooks
from src.core.game_state import (
    BoostOffer,
    BoostSetting,
    ControlType,
    GameState,
    PassDeclaration,
    PendingOffer,
    Phase,
)

if TYPE_CHECKING:
    from src.core.game_events import GameEvent, Moment
    from src.core.hex_grid import HexGrid
    from src.core.registry import StaticDataRegistry
    from src.core.rules_hooks import Hook

ASK = "ask"
STANDING = "standing"
SELF = "self"
MODES: tuple[str, ...] = (ASK, STANDING, SELF)
WATCH_DURATIONS: tuple[str, ...] = (reaction_prefs.UNTIL_COMBAT, reaction_prefs.UNTIL_TURN)
MAX_PRICE = 20
# ⚠️ ASSUMPTION (54.15 c): a bot owner with ``ask`` accepts any request paying at least this much.
BOT_MIN_PAYMENT = 1
# Context key of a deal offer (``PendingOffer.ctx``).
DEAL = "__deal"
# ``PendingOffer.hook_seq`` of a deal for a window-use component (no event hook behind it).
COMPONENT_HOOK = -1
# Steps that do not move the game on: boosts recorded before them stay available.
_KEEP_LABELS = (
    "boost:", "offer:", "reaction-settings", "reaction-pause", "reaction-wait", "transaction",
    "chat", "presence", "player-undo",
)
# The bot engine labels a step ``bot:<action kind>`` (``engine.actions.step_label``): the same
# moves as the HTTP labels above keep boosts too (engine and server must settle identically).
_KEEP_BOT_KINDS = ("bot:offer_accept", "bot:offer_decline", "bot:reaction_pause_release")

BeneficiaryFn = Callable[[GameState, str, Mapping[str, Any]], list[str]]
ComponentBeneficiaryFn = Callable[[GameState, str], list[str]]
# ``(state, owner, option value) -> player the option uses the effect on`` (None = nobody).
TargetFn = Callable[[GameState, str, str], "str | None"]


def option_is_player(_state: GameState, _owner: str, value: str) -> str | None:
    """Default ``target_of``: the option's value is the player id."""
    return value or None


@dataclass(frozen=True)
class PullSpec:
    """How a cooperative effect is offered (module docstring, RULES.md 54.15 e)."""

    beneficiaries: Callable[..., list[str]]
    mutual: bool = False
    target: str | None = None
    target_of: TargetFn = option_is_player
    owner_picks: bool = False


_PULL_HOOKS: dict[str, PullSpec] = {}
_PULL_COMPONENTS: dict[str, PullSpec] = {}


def spec_for(covers: str, *, component: bool | None = None) -> PullSpec | None:
    """The registration of a cooperative effect (``None`` = not cooperative).

    ``component``: ``True`` = the window-use / ``ACTION:`` registration, ``False`` = the event
    hook one, ``None`` = either. One key may have both (Deepgloom Executable: the Scheming
    allowance is a hook, lending Stall Tactics a window use).
    """
    if component is None:
        return _PULL_HOOKS.get(covers) or _PULL_COMPONENTS.get(covers)
    return (_PULL_COMPONENTS if component else _PULL_HOOKS).get(covers)


# --- Registration (faction modules) ------------------------------------------------------------


def that_player(_state: GameState, _owner: str, ctx: Mapping[str, Any]) -> list[str]:
    """Default beneficiary: the player of the event (``ctx["player"]``)."""
    player = ctx.get("player")
    return [player] if isinstance(player, str) and player else []


def combatants(state: GameState, _owner: str, _ctx: Mapping[str, Any]) -> list[str]:
    """Both sides of the active combat ("choose 1 ship / ground force in the active system")."""
    combat = state.active_combat
    return [] if combat is None else [combat.attacker, combat.defender]


def register_pull(
    covers: str,
    beneficiaries: BeneficiaryFn = that_player,
    *,
    mutual: bool = False,
    target: str | None = None,
    target_of: TargetFn = option_is_player,
    owner_picks: bool = False,
) -> None:
    """Marks the optional event hooks covering ``covers`` as cooperative (RULES.md 54.15)."""
    _PULL_HOOKS[covers] = PullSpec(beneficiaries, mutual, target, target_of, owner_picks)


def register_pull_component(
    kind: str,
    component: str,
    beneficiaries: ComponentBeneficiaryFn,
    *,
    mutual: bool = False,
    target: str | None = None,
    target_of: TargetFn = option_is_player,
    owner_picks: bool = False,
) -> None:
    """Marks a window-use or ``ACTION:`` component as cooperative (RULES.md 54.15)."""
    from src.core import faction_components  # local: imports the window modules

    _PULL_COMPONENTS[faction_components.effect_key(kind, component)] = PullSpec(
        beneficiaries, mutual, target, target_of, owner_picks
    )


def _component_targets(state: GameState, owner: str, key: str) -> list[str]:
    spec = _PULL_COMPONENTS.get(key)
    if spec is None:
        return []
    return [p for p in dict.fromkeys(spec.beneficiaries(state, owner)) if p in state.players]


def is_pull(covers: str | None) -> bool:
    """Is the component cooperative (pull)? Loads the hook packages first."""
    if not covers:
        return False
    rules_hooks.effect_for(covers)
    return covers in _PULL_HOOKS or covers in _PULL_COMPONENTS


# --- Owner settings ----------------------------------------------------------------------------


def setting(state: GameState, owner: str, covers: str) -> BoostSetting:
    """The owner's terms for ``covers`` (default ``ask``)."""
    player = state.players.get(owner)
    if player is None:
        return BoostSetting()
    return player.private.reaction_prefs.boosts.get(covers) or BoostSetting()


def watching(state: GameState, owner: str) -> bool:
    """Is the owner watching (54.15 d): pull effects are offered to them unprompted."""
    player = state.players.get(owner)
    if player is None or player.control_type is ControlType.BOT:
        return False
    watch = player.private.reaction_prefs.watch
    return watch is not None and reaction_prefs.is_live(state, watch)


def configure(
    state: GameState,
    player_id: str,
    covers: str,
    *,
    mode: str,
    price: int = 0,
    free_for: Iterable[str] = (),
) -> GameState:
    """Owner sets how a cooperative effect is offered (new state).

    Raises:
        ValueError: Unknown player / not a cooperative effect / bad mode or price.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    if not is_pull(covers):
        raise ValueError(f"{covers} is not a cooperative effect.")
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")
    if not 0 <= int(price) <= MAX_PRICE:
        raise ValueError(f"The price must be between 0 and {MAX_PRICE}.")
    allies = [p for p in dict.fromkeys(free_for) if p in state.players and p != player_id]
    new_state = state.clone()
    prefs = new_state.players[player_id].private.reaction_prefs
    prefs.boosts = {
        **prefs.boosts,
        covers: BoostSetting(mode=mode, price=int(price), free_for=allies),
    }
    return new_state


def set_watch(state: GameState, player_id: str, until: str | None) -> GameState:
    """"Watch / Hold" on (``combat`` / ``turn``) or off (``None``) - new state.

    Raises:
        ValueError: Unknown player or duration.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    if until is not None and until not in WATCH_DURATIONS:
        raise ValueError(f"Unknown watch duration: {until}")
    new_state = state.clone()
    prefs = new_state.players[player_id].private.reaction_prefs
    prefs.watch = (
        None if until is None
        else PassDeclaration(until=until, stamp=reaction_prefs.stamp(new_state, until))
    )
    return new_state


def prune_watch(state: GameState) -> None:
    """Drops lapsed "Watch" declarations (MUTATES; after every step)."""
    for player in state.players.values():
        watch = player.private.reaction_prefs.watch
        if watch is not None and not reaction_prefs.is_live(state, watch):
            player.private.reaction_prefs.watch = None


# --- Interception (triggers.fire) ---------------------------------------------------------------


def _beneficiaries_of(
    state: GameState, owner: str, covers: str, ctx: Mapping[str, Any]
) -> list[str]:
    spec = _PULL_HOOKS.get(covers)
    if spec is None:
        return []
    return [p for p in dict.fromkeys(spec.beneficiaries(state, owner, ctx)) if p in state.players]


def intercept(
    state: GameState,
    owner: str,
    hook: Hook,
    event: GameEvent,
    moment: Moment,
    ctx: dict[str, Any],
) -> bool:
    """A pull hook fired on another player's event: record a boost instead of an offer (MUTATES).

    Returns ``True`` when the caller must NOT create an offer. The owner's own use (they are a
    beneficiary) and "Watch" keep the normal offer. A ``mutual`` effect records the boost AND
    keeps the owner's offer (returns ``False``).
    """
    covers = hook.covers or ""
    spec = _PULL_HOOKS.get(covers)
    if spec is None:
        return False
    targets = _beneficiaries_of(state, owner, covers, ctx)
    if spec.mutual:
        targets = [p for p in targets if p != owner]
        if not targets:
            return False
    elif not targets or owner in targets or watching(state, owner):
        return False
    if setting(state, owner, covers).mode != SELF:
        from src.core import active_effects  # local: import cycle via triggers

        state.boosts = [*state.boosts, BoostOffer(
            id=active_effects.next_id(state, "bo"),
            owner=owner,
            covers=covers,
            beneficiaries=targets,
            hook_seq=hook.seq,
            event=event.value,
            moment=moment.value,
            ctx=ctx,
            label=hook.label,
        )]
    return not spec.mutual


def component_for_others(state: GameState, owner: str, key: str) -> bool:
    """A pull window-use component that right now helps only others and the owner is not watching:
    the engine does not prompt the owner nor keep reaction windows open for it (54.15). A
    ``mutual`` component is always offered to its owner too."""
    spec = _PULL_COMPONENTS.get(key)
    if spec is None or spec.mutual:
        return False
    targets = _component_targets(state, owner, key)
    return bool(targets) and owner not in targets and not watching(state, owner)


def prune(before: GameState | None, after: GameState, label: str) -> None:
    """Boosts recorded before a step that moved the game on are gone (MUTATES ``after``)."""
    if before is None or label.startswith(_KEEP_LABELS) or label in _KEEP_BOT_KINDS:
        return
    old = {b.id for b in before.boosts}
    if old:
        after.boosts = [b for b in after.boosts if b.id not in old]


# --- Availability --------------------------------------------------------------------------------


def _component_key(key: str) -> tuple[str, str]:
    from src.core import faction_components

    category, _, component = key.partition(":")
    for kind in faction_components.KINDS:
        if faction_components.effect_key(kind, "x").split(":")[0] == category:
            return kind, component
    raise ValueError(f"Unknown component: {key}")


def _hook_live(state: GameState, boost: BoostOffer) -> bool:
    hook = rules_hooks.hook_by_seq(boost.hook_seq)
    if hook is None or hook.source not in rules_hooks.owned_sources(state, boost.owner):
        return False
    return hook.condition is None or bool(hook.condition(state, boost.owner, boost.ctx))


def _owner_components(
    state: GameState, registry: StaticDataRegistry, owner: str
) -> list[tuple[str, str]]:
    """The owner's faction components plus their cooperative ``ACTION:`` technologies (a
    technology is a faction component only with a window use - Wormhole Generator is not)."""
    from src.core import faction_components

    rows = faction_components.owned(state, registry, owner)
    player = state.players.get(owner)
    rows += [
        (faction_components.TECHNOLOGY, tech) for tech in (player.technologies if player else [])
        if faction_components.effect_key(faction_components.TECHNOLOGY, tech) in _PULL_COMPONENTS
        and (faction_components.TECHNOLOGY, tech) not in rows
    ]
    return rows


def _action_tech(state: GameState, registry: StaticDataRegistry, owner: str, kind: str,
                 component: str) -> bool:
    """A cooperative ``ACTION:`` technology played through the component action itself."""
    from src.core import faction_components

    return kind == faction_components.TECHNOLOGY and (kind, component) not in (
        faction_components.owned(state, registry, owner)
    )


def _tech_live(state: GameState, registry: StaticDataRegistry, owner: str, tech: str) -> bool:
    from src.core import component_action

    player = state.players.get(owner)
    if player is None or tech not in player.technologies or tech in player.exhausted_technologies:
        return False
    try:
        component_action.play_component_action(
            state, owner, tech, fire_after=False, run_effect=False
        )
    except ValueError:
        return False
    inputs_fn = rules_hooks.inputs_for(f"technologies:{tech}")
    return offer_inputs.has_legal_answer(
        inputs_fn(state, registry, owner) if inputs_fn is not None else []
    )


def _component_live(
    state: GameState, registry: StaticDataRegistry, owner: str, key: str
) -> bool:
    from src.core import faction_components

    kind, component = _component_key(key)
    if _action_tech(state, registry, owner, kind, component):
        return _tech_live(state, registry, owner, component)
    # ``ACTION:`` components: only while the owner could play them now (their turn, RULES.md 31.8).
    return any(
        row["mode"] in ("window", "action") and row["playable"]
        and row["kind"] == kind and row["component_id"] == component
        for row in faction_components.playability(state, registry, owner)
    )


def _deal_terms(offer: PendingOffer) -> tuple[PullSpec | None, str, str]:
    deal = _deal(offer) or {}
    source = str(deal.get("source") or "")
    return spec_for(source, component=offer.hook_seq == COMPONENT_HOOK), str(
        deal.get("owner")
    ), str(deal.get("requester"))


def _for_requester(
    state: GameState, spec: PullSpec, owner: str, requester: str, inputs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The ``target`` choice keeps only the options using the effect on the requester."""
    if spec.target is None:
        return inputs
    shaped: list[dict[str, Any]] = []
    for item in inputs:
        if item.get("key") != spec.target or item.get("kind") != "choice":
            shaped.append(item)
            continue
        options = [
            o for o in item.get("options", [])
            if spec.target_of(state, owner, str(o.get("value"))) == requester
        ]
        new = {**item, "options": options}
        values = [o["value"] for o in options]
        # An existing "Auto" (combat / spending only) survives only if still legal - never added.
        if "auto" in item and item["auto"] not in values:
            new.pop("auto", None)
        shaped.append(new)
    return shaped


def deal_inputs(
    state: GameState, offer: PendingOffer, inputs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The effect's form for a deal offer: options limited to the requester (``target``)."""
    spec, owner, requester = _deal_terms(offer)
    if spec is None:
        return inputs
    return _for_requester(state, spec, owner, requester, inputs)


def _deal_params(
    state: GameState,
    spec: PullSpec | None,
    owner: str,
    requester: str,
    inputs: list[dict[str, Any]],
    params: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """The answer checked against the requester-limited form (a deal is only for the requester).

    Raises:
        ValueError: An option outside the deal / a ``target`` multi-choice without the requester.
    """
    raw = dict(params or {})
    if spec is None or spec.target is None:
        return raw
    cleaned = {**raw, **offer_inputs.validate_params(
        _for_requester(state, spec, owner, requester, inputs), raw
    )}
    item = next((i for i in inputs if i.get("key") == spec.target), None)
    if item is not None and item.get("kind") == "multi":
        chosen = [str(v) for v in cleaned.get(spec.target) or []]
        if not any(spec.target_of(state, owner, v) == requester for v in chosen):
            raise ValueError("This deal is for the requesting player: include them.")
    return cleaned


def _deal(offer: PendingOffer) -> dict[str, Any] | None:
    deal = offer.ctx.get(DEAL)
    return deal if isinstance(deal, dict) else None


def is_deal(offer: PendingOffer) -> bool:
    """Is the offer a requested cooperative effect (a deal)?"""
    return _deal(offer) is not None


def deals(state: GameState) -> list[tuple[PendingOffer, dict[str, Any]]]:
    """Every open deal offer with its terms."""
    return [(o, d) for o in state.pending_offers if (d := _deal(o)) is not None]


def payable(state: GameState, grid: HexGrid, payer: str, owner: str) -> bool:
    """Can ``payer`` pay ``owner`` now - a transaction is legal between them (R_deals)."""
    from src.core import transaction

    return transaction.components_allowed(state, grid, payer, owner)


def _row(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    requester: str,
    boost_id: str,
    owner: str,
    covers: str,
) -> dict[str, Any] | None:
    from src.core.component_text import describe_component

    terms = setting(state, owner, covers)
    if terms.mode == SELF:
        return None
    name, text, kind = describe_component(registry, covers)
    pending = next(
        (o.id for o, d in deals(state) if d.get("boost") == boost_id
         and d.get("requester") == requester),
        None,
    )
    return {
        "id": boost_id,
        "owner": owner,
        "source": covers,
        "name": name or covers,
        "text": text,
        "kind": kind,
        "mode": terms.mode,
        "price": terms.price if terms.mode == STANDING else None,
        "free": terms.mode == STANDING and requester in terms.free_for,
        "payable": payable(state, grid, requester, owner),
        "pending": pending,
    }


def available(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid, requester: str
) -> list[dict[str, Any]]:
    """Cooperative effects ``requester`` may request right now (UI "Available boosts")."""
    from src.core import faction_components

    rows: list[dict[str, Any]] = []
    for boost in state.boosts:
        if requester in boost.beneficiaries and _hook_live(state, boost):
            row = _row(state, registry, grid, requester, boost.id, boost.owner, boost.covers)
            if row is not None:
                rows.append(row)
    for owner in state.players:
        if owner == requester:
            continue
        for kind, component in _owner_components(state, registry, owner):
            key = faction_components.effect_key(kind, component)
            spec = _PULL_COMPONENTS.get(key)
            if spec is None:
                continue
            targets = _component_targets(state, owner, key)
            if requester not in targets or (owner in targets and not spec.mutual):
                continue
            if not _component_live(state, registry, owner, key):
                continue
            row = _row(state, registry, grid, requester, f"w:{owner}:{key}", owner, key)
            if row is not None:
                rows.append(row)
    return rows


def owned(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[dict[str, Any]]:
    """The player's cooperative effects with their terms (owner's settings panel)."""
    from src.core import faction_components, leaders
    from src.core.component_text import describe_component

    player = state.players.get(player_id)
    if player is None:
        return []
    keys = [f"leaders:{lid}" for lid in leaders.leaders_of(registry, player)]
    keys += [
        faction_components.effect_key(kind, component)
        for kind, component in _owner_components(state, registry, player_id)
    ]
    rows: list[dict[str, Any]] = []
    for key in dict.fromkeys(keys):
        if not is_pull(key):
            continue
        name, text, kind = describe_component(registry, key)
        terms = setting(state, player_id, key)
        rows.append({
            "source": key, "name": name or key, "text": text, "kind": kind,
            "mode": terms.mode, "price": terms.price, "freeFor": list(terms.free_for),
        })
    return rows


# --- Requests and deals ---------------------------------------------------------------------


def _find(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid, requester: str, boost_id: str
) -> dict[str, Any]:
    rows = available(state, registry, grid, requester)
    row = next((r for r in rows if r["id"] == boost_id), None)
    if row is None:
        raise ValueError("That boost is no longer available.")
    return row


def _check_payment(
    state: GameState, grid: HexGrid, payer: str, owner: str, trade_goods: int, commodities: int
) -> None:
    if trade_goods < 0 or commodities < 0:
        raise ValueError("A payment cannot be negative.")
    if trade_goods + commodities == 0:
        return
    player = state.players[payer]
    if player.trade_goods < trade_goods:
        raise ValueError(f"You have only {player.trade_goods} trade goods.")
    if player.commodities < commodities:
        raise ValueError(f"You have only {player.commodities} commodities.")
    if not payable(state, grid, payer, owner):
        raise ValueError(
            "A paid deal is a transaction: you can't transact with that player now "
            "(neighbours, one transaction per turn)."
        )


def request(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    requester: str,
    boost_id: str,
    *,
    trade_goods: int = 0,
    commodities: int = 0,
    now: float,
) -> GameState:
    """``requester`` asks for a boost, offering a payment (new state).

    A standing offer the payment covers (or free for the requester) and a bot owner who accepts
    give the offer to the REQUESTER (pick the details or cancel) - unless the effect is
    ``owner_picks`` (then the accepted offer goes to the owner). Otherwise the owner gets the
    offer and decides. In both cases a REACTION window opens when nothing else is open.

    Raises:
        ValueError: Not available / already requested / payment not possible / bot declined.
    """
    row = _find(state, registry, grid, requester, boost_id)
    if row["pending"] is not None:
        raise ValueError("You already asked for this boost.")
    owner = str(row["owner"])
    _check_payment(state, grid, requester, owner, trade_goods, commodities)
    paid = trade_goods + commodities
    terms = setting(state, owner, row["source"])
    accepted = terms.mode == STANDING and (requester in terms.free_for or paid >= terms.price)
    boost = next((b for b in state.boosts if b.id == boost_id), None)
    owner_player = state.players[owner]
    if not accepted and owner_player.control_type is ControlType.BOT:
        if paid < BOT_MIN_PAYMENT:
            raise ValueError(f"{row['name']}: the owner declines - offer a payment.")
        accepted = True
    spec = spec_for(str(row["source"]), component=boost is None)
    decider = requester if accepted and not (spec is not None and spec.owner_picks) else owner
    new_state = state.clone()
    from src.core import active_effects

    deal = {
        "boost": boost_id, "requester": requester, "owner": owner, "source": row["source"],
        "trade_goods": int(trade_goods), "commodities": int(commodities),
        "accepted": accepted, "at": float(now),
    }
    offer = PendingOffer(
        id=active_effects.next_id(new_state, "of"),
        player_id=decider,
        event=boost.event if boost is not None else "boost",
        moment=boost.moment if boost is not None else "request",
        hook_seq=boost.hook_seq if boost is not None else COMPONENT_HOOK,
        label=str(row["name"]),
        ctx={**(boost.ctx if boost is not None else {}), "decider": decider, DEAL: deal},
        owner_id=None if decider == owner else owner,
    )
    from src.core import triggers  # local: triggers imports this module

    triggers.add_offer(new_state, offer)
    return new_state


def _pay(
    state: GameState, grid: HexGrid, payer: str, owner: str, trade_goods: int, commodities: int
) -> GameState:
    """The payment as a normal transaction (RULES.md 47, R_deals): new state or the same one."""
    from src.core import transaction

    if trade_goods + commodities == 0:
        return state
    side = transaction.TransactionSide(trade_goods=trade_goods, commodities=commodities)
    empty = transaction.TransactionSide()
    active = state.active_player_id
    if state.phase is Phase.AGENDA or payer == active:
        return transaction.resolve_transaction(state, grid, owner, side, empty, payer)
    if owner == active:
        return transaction.resolve_transaction(state, grid, payer, empty, side, owner)
    raise ValueError("A paid deal is a transaction: one side must be the active player.")


def accept(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    actor_id: str,
    offer_id: str,
    params: dict[str, Any] | None = None,
) -> GameState:
    """Accepts a deal: payment AND effect in one step (new state; binding - R_deals).

    Any failure (the effect is no longer possible, the payment is not) raises and changes nothing.

    Raises:
        ValueError: Unknown offer / not the decider / effect or payment not possible.
    """
    from src.core import triggers

    offer = next((o for o in state.pending_offers if o.id == offer_id), None)
    deal = _deal(offer) if offer is not None else None
    if offer is None or deal is None:
        raise ValueError(f"Unknown deal: {offer_id}")
    if offer.player_id != actor_id:
        raise ValueError(f"The deal {offer_id} is decided by {offer.player_id}.")
    owner, requester = str(deal["owner"]), str(deal["requester"])
    source = str(deal["source"])
    spec = spec_for(source, component=offer.hook_seq == COMPONENT_HOOK)
    tg, comm = int(deal["trade_goods"]), int(deal["commodities"])
    if offer.hook_seq == COMPONENT_HOOK:
        result = _accept_component(
            state, registry, grid, actor_id, offer_id, spec, owner, requester, source, tg, comm,
            params,
        )
    else:
        base = {k: v for k, v in offer.ctx.items() if k not in (DEAL, "decider")}
        probe = BoostOffer(id="", owner=owner, covers=source, hook_seq=offer.hook_seq,
                           event=offer.event, moment=offer.moment, ctx=base)
        if not _hook_live(state, probe):
            raise ValueError("That effect can no longer be used.")
        hook = rules_hooks.hook_by_seq(offer.hook_seq)
        inputs = (
            hook.inputs(state, registry, owner, offer.ctx)
            if hook is not None and hook.inputs is not None else []
        )
        cleaned = _deal_params(state, spec, owner, requester, inputs, params)
        paid = _pay(state, grid, requester, owner, tg, comm)
        result = triggers.accept_offer(paid, actor_id, offer_id, cleaned, inputs_player=owner)
    result.boosts = [b for b in result.boosts if b.id != deal["boost"]]
    return result


def _accept_component(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    actor_id: str,
    offer_id: str,
    spec: PullSpec | None,
    owner: str,
    requester: str,
    source: str,
    trade_goods: int,
    commodities: int,
    params: Mapping[str, Any] | None,
) -> GameState:
    """A requested window-use / ``ACTION:`` component: payment + the owner's use, one step.

    An ``ACTION:`` component is the owner's component action (RULES.md 31.8): the deal's REACTION
    window closes first (a component action needs no open window) and the owner's action is used.
    """
    from src.core import component_action, faction_components, triggers

    kind, component = _component_key(source)
    tech = _action_tech(state, registry, owner, kind, component)
    action = tech or faction_components.is_action(registry, kind, component)
    work = state.clone()
    triggers.take_offer(work, actor_id, offer_id)
    if action:
        triggers.advance_window(work, actor_id)
    if not _component_live(work, registry, owner, source):
        raise ValueError("That effect can no longer be used.")
    inputs_fn = rules_hooks.inputs_for(source)
    inputs = inputs_fn(work, registry, owner) if inputs_fn is not None else []
    cleaned = _deal_params(work, spec, owner, requester, inputs, params)
    paid = _pay(work, grid, requester, owner, trade_goods, commodities)
    if tech:  # an ``ACTION:`` technology = the owner's component action (RULES.md 31.8)
        result = component_action.play_component_action(paid, owner, component, params=cleaned)
        reaction_prefs.note_change(result, owner, f"used {source}")
    else:
        result, _ = faction_components.play(paid, registry, owner, kind, component, cleaned)
    if not action:
        triggers.advance_window(result, actor_id)
    return result


def decline(state: GameState, actor_id: str, offer_id: str) -> GameState:
    """The owner declines a request, or the requester cancels / withdraws it (new state)."""
    from src.core import triggers

    offer = next((o for o in state.pending_offers if o.id == offer_id), None)
    deal = _deal(offer) if offer is not None else None
    if offer is None or deal is None:
        raise ValueError(f"Unknown deal: {offer_id}")
    if actor_id not in (offer.player_id, deal["requester"]):
        raise ValueError(f"{actor_id} is not part of this deal.")
    if actor_id == offer.player_id:
        return triggers.decline_offer(state, actor_id, offer_id)
    new_state = state.clone()  # the requester withdraws a request waiting for the owner
    triggers.take_offer(new_state, offer.player_id, offer_id)
    triggers.advance_window(new_state, offer.player_id)
    return new_state


def expire(state: GameState, now: float) -> GameState:
    """Requests the owner did not answer within the reaction window length lapse (no payment)."""
    from src.core import reaction_window

    limit = float(reaction_window.window_seconds(state))
    result = state
    for offer, deal in deals(state):
        if deal.get("accepted") or now - float(deal.get("at", now)) < limit:
            continue
        result = decline(result, offer.player_id, offer.id)
    return result


def deal_view(offer: PendingOffer) -> dict[str, Any] | None:
    """The deal's terms for the offer card (who asks, what they pay, already accepted?)."""
    deal = _deal(offer)
    if deal is None:
        return None
    return {
        "requester": deal["requester"], "owner": deal["owner"],
        "tradeGoods": int(deal["trade_goods"]), "commodities": int(deal["commodities"]),
        "accepted": bool(deal.get("accepted")), "at": float(deal.get("at", 0.0)),
    }
