"""Eksploracja planet po przejęciu kontroli (RULES.md 46).

Gdy gracz przejmie planetę, która nie była kontrolowana przez nikogo, EKSPLORUJE ją: dobiera
kartę z talii odpowiadającej cesze planety (cultural / hazardous / industrial) i rozstrzyga
ją w całości, zanim zacznie następną. Wiele planet naraz → gracz wybiera kolejność; planeta
z kilkoma cechami → gracz wybiera talię.

Funkcje CZYSTE (``state -> state``), tasowanie przez ``core/dice.next_rng`` (seedowalne).
Twarda walidacja: ``ValueError`` → HTTP 422. Treść i typ kart wyłącznie z katalogu
komponentów (``registry.catalog``); tu modelujemy tylko ich skutki. Zakres: talie planetarne
(frontier / Dark Energy Tap — poza zakresem, patrz RULES.md 46.3).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from src.core import command_tokens, economy, exhaust, unit_ops
from src.core.card_draw import draw_action_card
from src.core.components import ComponentCategory, ExplorationDef
from src.core.damage import clear_zone_damage
from src.core.dice import next_rng
from src.core.game_state import (
    ExplorationState,
    ExploreCurrent,
    GameState,
    ProductionGrant,
    SystemState,
)
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

# Talie planetarne = cechy planet (R_exploration). Planeta bez żadnej z nich (Mecatol Rex,
# planety domowe, stacje kosmiczne) nie podlega eksploracji.
PLANET_DECKS: tuple[str, ...] = ("cultural", "hazardous", "industrial")

# Siły naziemne (mogą stać na planecie); reszta jednostek na planecie to struktury.
_GROUND = frozenset({"infantry", "mech"})
# Pule żetonów dowodzenia, do których można dobrać żeton (Volatile Fuel Source).
_CC_POOLS: tuple[tuple[str, str], ...] = (
    ("tactical", "Tactic"),
    ("fleet", "Fleet"),
    ("strategic", "Strategy"),
)


@dataclass(frozen=True)
class ExploreOption:
    """Wybór dostępny przy rozstrzyganiu karty (``params`` = dodatkowy wybór, np. pula)."""

    id: str
    label: str
    enabled: bool = True
    reason: str = ""
    params: tuple[tuple[str, str], ...] = field(default=())


# ------------------------------------------------------------------------------ pomocnicze


def _exp(state: GameState) -> ExplorationState:
    if state.exploration is None:
        raise ValueError("No exploration is in progress.")
    return state.exploration


def _card_def(registry: StaticDataRegistry, card_id: str) -> ExplorationDef:
    card = registry.catalog.get(ComponentCategory.EXPLORATION, card_id)
    if not isinstance(card, ExplorationDef):
        raise ValueError(f"Unknown exploration card: {card_id}.")
    return card


def card_def(registry: StaticDataRegistry, card_id: str) -> ExplorationDef:
    """Definicja karty eksploracji z katalogu (``ValueError``, gdy nieznana)."""
    return _card_def(registry, card_id)


def planet_traits(registry: StaticDataRegistry, planet_id: str) -> list[str]:
    """Talie, z których można eksplorować planetę (kolejność jak w danych); pusta = nie można."""
    planet = registry.planets.get(planet_id)
    if planet is None:
        return []
    raw = [*(planet.planet_types or []), *([planet.planet_type] if planet.planet_type else [])]
    traits: list[str] = []
    for item in raw:
        trait = item.lower()
        if trait in PLANET_DECKS and trait not in traits:
            traits.append(trait)
    return traits


def explorable(registry: StaticDataRegistry, planet_id: str) -> bool:
    """Czy planeta ma cechę, a więc podlega eksploracji."""
    return bool(planet_traits(registry, planet_id))


def _system(state: GameState, ex: ExplorationState) -> SystemState:
    system = state.systems.get(ex.position)
    if system is None:
        raise ValueError("The explored system has no units.")
    return system


def _count(system: SystemState, planet: str, player_id: str, base_type: str) -> int:
    return system.planet_units.get(planet, {}).get(player_id, {}).get(base_type, 0)


def _remove_unit(
    state: GameState, system: SystemState, planet: str, player_id: str, base_type: str
) -> None:
    unit_ops.remove_units(state, system, planet, player_id, base_type, 1, UnitCause.REMOVED)


def _add_unit(
    state: GameState, system: SystemState, planet: str, player_id: str, base_type: str
) -> None:
    unit_ops.place_units(state, system, planet, player_id, base_type, 1, UnitCause.PLACED)


def deck_card_ids(registry: StaticDataRegistry, deck: str) -> list[str]:
    """Wszystkie karty talii eksploracji (posortowane) wg typu karty w katalogu."""
    return sorted(
        card_id
        for card_id, card in registry.catalog.all(ComponentCategory.EXPLORATION).items()
        if isinstance(card, ExplorationDef) and (card.type or "").lower() == deck
    )


def seed_deck(state: GameState, registry: StaticDataRegistry, deck: str) -> None:
    """Zasiewa (tasuje) talię eksploracji, jeśli jeszcze nie istnieje — MUTUJE ``state``."""
    decks = state.decks
    if deck not in decks.exploration_deck:
        ids = deck_card_ids(registry, deck)
        next_rng(state).shuffle(ids)
        decks.exploration_deck[deck] = ids
        decks.exploration_discard.setdefault(deck, [])


def _draw_card(state: GameState, registry: StaticDataRegistry, deck: str) -> str:
    """Dobiera wierzchnią kartę talii (leniwy setup; pusta talia → tasowanie odrzuconych)."""
    decks = state.decks
    seed_deck(state, registry, deck)
    if not decks.exploration_deck[deck]:
        discard = list(decks.exploration_discard.get(deck, []))
        if not discard:
            raise ValueError(f"The {deck} exploration deck is empty.")
        next_rng(state).shuffle(discard)
        decks.exploration_deck[deck] = discard
        decks.exploration_discard[deck] = []
    return decks.exploration_deck[deck].pop(0)


def _draw_action_card(state: GameState, player_id: str) -> bool:
    """Dobiera kartę akcji (pusta talia → tasuje odrzucone); False, gdy nie ma żadnej."""
    return draw_action_card(state, player_id)


# ------------------------------------------------------------------------- opcje kart (Instant)

_Options = Callable[[GameState, ExplorationState, ExploreCurrent], list[ExploreOption]]
_Apply = Callable[[GameState, ExplorationState, ExploreCurrent, str, str | None], str]

_SKIP = ExploreOption("skip", "Decline")


def _gap(state: GameState, player_id: str) -> int:
    """Ile commodities brakuje graczowi do commodity value (nie można mieć więcej)."""
    return economy.commodity_gap(state, player_id)


def _opts_mercenary(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[ExploreOption]:
    left = reinforcements_left(state, ex.player_id, "infantry")
    ok = left is None or left > 0
    return [
        ExploreOption(
            "place_infantry",
            "Place 1 infantry on this planet",
            ok,
            "" if ok else "No infantry in reinforcements.",
        ),
        _SKIP,
    ]


def _apply_mercenary(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    if option == "skip":
        return "Declined."
    _add_unit(state, _system(state, ex), cur.planet, ex.player_id, "infantry")
    return "Placed 1 infantry on the planet."


def _opts_freelancers(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[ExploreOption]:
    here = state.active_system == ex.position
    return [
        ExploreOption(
            "produce",
            "Produce 1 unit in this system (influence counts as resources)",
            here,
            "" if here else "The explored system is not the active system.",
        ),
        _SKIP,
    ]


def _apply_freelancers(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    if option == "skip":
        return "Declined."
    state.production_grant = ProductionGrant(
        player_id=ex.player_id,
        position=ex.position,
        units=1,
        influence_as_resources=True,
        source="Freelancers",
    )
    return "Production opened: 1 unit in this system, influence counts as resources."


def _apply_manual(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    return "Declined." if option == "skip" else "Resolved by hand."


def _hazard_options(
    state: GameState,
    ex: ExplorationState,
    cur: ExploreCurrent,
    *,
    needs_pool: bool,
) -> list[ExploreOption]:
    system = _system(state, ex)
    mechs = _count(system, cur.planet, ex.player_id, "mech")
    infantry = _count(system, cur.planet, ex.player_id, "infantry")
    pools: tuple[tuple[str, str], ...] = ()
    reason_pool = ""
    if needs_pool:
        pools = _CC_POOLS
        if state.players[ex.player_id].cc_reinf <= 0:
            reason_pool = "No command tokens in reinforcements."
    return [
        ExploreOption(
            "mech",
            "You have a mech here",
            mechs > 0 and not reason_pool,
            reason_pool or ("" if mechs > 0 else "No mech on this planet."),
            pools,
        ),
        ExploreOption(
            "infantry",
            "Remove 1 infantry from this planet",
            infantry > 0 and not reason_pool,
            reason_pool or ("" if infantry > 0 else "No infantry on this planet."),
            pools,
        ),
        _SKIP,
    ]


def _opts_volatile(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[ExploreOption]:
    return _hazard_options(state, ex, cur, needs_pool=True)


def _opts_hazard_plain(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[ExploreOption]:
    return _hazard_options(state, ex, cur, needs_pool=False)


def _hazard_apply(
    state: GameState,
    ex: ExplorationState,
    cur: ExploreCurrent,
    option: str,
    param: str | None,
    reward: Callable[[GameState, ExplorationState, ExploreCurrent, str | None], str],
) -> str:
    if option == "skip":
        return "Declined."
    if option == "infantry":
        _remove_unit(state, _system(state, ex), cur.planet, ex.player_id, "infantry")
        paid = "Removed 1 infantry. "
    else:
        paid = "Has a mech here. "
    return paid + reward(state, ex, cur, param)


def _reward_command_token(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, param: str | None
) -> str:
    command_tokens.gain_from_reinforcements(state, ex.player_id, {param or "": 1})
    return f"Gained 1 command token ({dict(_CC_POOLS)[param or '']} pool)."


def _reward_ready(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, param: str | None
) -> str:
    exhaust.ready_planets(state, ex.player_id, [cur.planet])
    return "The planet is ready."


def _reward_trade_good(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, param: str | None
) -> str:
    economy.gain_trade_goods(state, ex.player_id, 1)
    return "Gained 1 trade good."


def _apply_volatile(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    return _hazard_apply(state, ex, cur, option, param, _reward_command_token)


def _apply_expedition(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    return _hazard_apply(state, ex, cur, option, param, _reward_ready)


def _apply_core_mine(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    return _hazard_apply(state, ex, cur, option, param, _reward_trade_good)


def _opts_warehouses(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[ExploreOption]:
    player = state.players[ex.player_id]
    gap = _gap(state, ex.player_id)
    convertible = min(2, player.commodities)
    return [
        ExploreOption(
            "gain",
            "Gain 2 commodities",
            gap > 0,
            "" if gap > 0 else "Commodities are already at the maximum.",
        ),
        ExploreOption(
            "convert",
            "Convert up to 2 commodities to trade goods",
            convertible > 0,
            "" if convertible > 0 else "You have no commodities.",
            tuple((str(n), f"{n}") for n in range(1, convertible + 1)),
        ),
        _SKIP,
    ]


def _apply_warehouses(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    if option == "gain":
        gained = economy.gain_commodities(state, ex.player_id, 2)
        return f"Gained {gained} commodities."
    if option == "convert":
        amount = int(param or "0")
        economy.convert_commodities_to_trade_goods(state, ex.player_id, amount)
        return f"Converted {amount} commodities to trade goods."
    return "Declined."


def _pay_options(
    state: GameState, ex: ExplorationState, *, prefix: str, label: str, extra_ok: bool,
    extra_reason: str,
) -> list[ExploreOption]:
    player = state.players[ex.player_id]
    return [
        ExploreOption(
            f"{prefix}_tg",
            f"Spend 1 trade good: {label}",
            player.trade_goods > 0 and extra_ok,
            extra_reason or ("" if player.trade_goods > 0 else "You have no trade goods."),
        ),
        ExploreOption(
            f"{prefix}_commodity",
            f"Spend 1 commodity: {label}",
            player.commodities > 0 and extra_ok,
            extra_reason or ("" if player.commodities > 0 else "You have no commodities."),
        ),
    ]


def _gain_commodity_option(state: GameState, ex: ExplorationState) -> ExploreOption:
    ok = _gap(state, ex.player_id) > 0
    return ExploreOption(
        "gain", "Gain 1 commodity", ok, "" if ok else "Commodities are already at the maximum."
    )


def _opts_functioning_base(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[ExploreOption]:
    deck_ok = bool(state.decks.action_card_deck or state.decks.action_card_discard)
    return [
        _gain_commodity_option(state, ex),
        *_pay_options(
            state, ex, prefix="draw", label="draw 1 action card", extra_ok=deck_ok,
            extra_reason="" if deck_ok else "The action card deck is empty.",
        ),
        _SKIP,
    ]


def _opts_fabricators(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent
) -> list[ExploreOption]:
    left = reinforcements_left(state, ex.player_id, "mech")
    ok = left is None or left > 0
    return [
        _gain_commodity_option(state, ex),
        *_pay_options(
            state, ex, prefix="mech", label="place 1 mech on this planet", extra_ok=ok,
            extra_reason="" if ok else "No mech in reinforcements.",
        ),
        _SKIP,
    ]


def _apply_pay(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, option: str, param: str | None
) -> str:
    """Wspólne: gain / <akcja>_tg / <akcja>_commodity / skip dla Functioning Base i Fabricators."""
    if option == "skip":
        return "Declined."
    if option == "gain":
        economy.gain_commodities(state, ex.player_id, 1)
        return "Gained 1 commodity."
    action, _, currency = option.partition("_")
    if currency == "tg":
        economy.spend_trade_goods(state, ex.player_id, 1)
        paid = "1 trade good"
    else:
        economy.spend_commodities(state, ex.player_id, 1)
        paid = "1 commodity"
    if action == "draw":
        _draw_action_card(state, ex.player_id)
        return f"Spent {paid} and drew 1 action card."
    _add_unit(state, _system(state, ex), cur.planet, ex.player_id, "mech")
    return f"Spent {paid} and placed 1 mech on the planet."


_INSTANT_OPTIONS: dict[str, _Options] = {
    "mercenary outfit": _opts_mercenary,
    "freelancers": _opts_freelancers,
    "volatile fuel source": _opts_volatile,
    "expedition": _opts_hazard_plain,
    "core mine": _opts_hazard_plain,
    "abandoned warehouses": _opts_warehouses,
    "functioning base": _opts_functioning_base,
    "local fabricators": _opts_fabricators,
}
_INSTANT_APPLY: dict[str, _Apply] = {
    "mercenary outfit": _apply_mercenary,
    "freelancers": _apply_freelancers,
    "volatile fuel source": _apply_volatile,
    "expedition": _apply_expedition,
    "core mine": _apply_core_mine,
    "abandoned warehouses": _apply_warehouses,
    "functioning base": _apply_pay,
    "local fabricators": _apply_pay,
}


# --------------------------------------------------------------------------- skutki per rodzaj


def _apply_attach(
    state: GameState, ex: ExplorationState, cur: ExploreCurrent, card: ExplorationDef
) -> str:
    """Attach: karta zostaje przy planecie. Demilitarized Zone dodatkowo czyści planetę."""
    state.planet_attachments.setdefault(cur.planet, []).append(cur.card_id)
    if card.attachment_id != "dmz":
        return "Attached to the planet."
    system = _system(state, ex)
    for player_id in list(system.planet_units.get(cur.planet, {})):
        units = system.planet_units[cur.planet][player_id]
        for base_type, count in list(units.items()):
            if count > 0 and base_type in _GROUND:
                # Siły naziemne wychodzą na orbitę; uszkodzenia planety i tak kasujemy niżej.
                unit_ops.take_units(
                    state, system, cur.planet, player_id, base_type, count, UnitCause.MOVED
                )
                unit_ops.place_units(
                    state, system, "space", player_id, base_type, count, UnitCause.MOVED
                )
            elif base_type in _GROUND or not is_space_unit(base_type):
                unit_ops.take_units(
                    state, system, cur.planet, player_id, base_type, count, UnitCause.REMOVED
                )
    clear_zone_damage(system, cur.planet)
    return "Attached. Structures returned to reinforcements, ground forces moved to orbit."


def options_for(
    state: GameState, registry: StaticDataRegistry
) -> list[ExploreOption]:
    """Opcje rozstrzygnięcia ujawnionej karty (puste, gdy żadnej nie odkryto)."""
    ex = _exp(state)
    cur = ex.current
    if cur is None:
        return []
    card = _card_def(registry, cur.card_id)
    kind = (card.resolution or "").lower()
    if kind == "attach":
        return [ExploreOption("attach", "Attach to the planet")]
    if kind == "fragment":
        return [ExploreOption("keep", "Place in your play area")]
    if kind == "token":
        if card.attachment_id == "gamma":
            return [ExploreOption("place", "Place a gamma wormhole token in this system")]
        return [
            ExploreOption("manual", "Place the token by hand (God-Mode); the card is purged")
        ]
    handler = _INSTANT_OPTIONS.get((card.name or "").lower())
    if handler is None:
        return [ExploreOption("manual", "Resolve by hand"), _SKIP]
    return handler(state, ex, cur)


# ------------------------------------------------------------------------------- przepływ


def _auto(state: GameState, registry: StaticDataRegistry) -> None:
    """Dobiera kartę sama, gdy nie ma żadnego wyboru (jedna planeta, jedna cecha)."""
    ex = _exp(state)
    if ex.current is None and len(ex.queue) == 1:
        traits = planet_traits(registry, ex.queue[0])
        if len(traits) == 1:
            _draw_for(state, registry, ex.queue[0], traits[0])


def _require_no_grant(state: GameState) -> None:
    """Karta z produkcją (Freelancers) jest rozstrzygnięta dopiero po produkcji / rezygnacji."""
    if state.production_grant is not None:
        source = state.production_grant.source or "card"
        raise ValueError(f"Finish the {source} production first (or skip it).")


def _draw_for(state: GameState, registry: StaticDataRegistry, planet: str, deck: str) -> None:
    ex = _exp(state)
    card_id = _draw_card(state, registry, deck)
    ex.queue = [p for p in ex.queue if p != planet]
    ex.current = ExploreCurrent(planet=planet, deck=deck, card_id=card_id)


def begin_exploration(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
    planets: list[str],
) -> GameState:
    """Otwiera eksplorację dla ``planets`` (pomija planety bez cech); gracz = eksplorujący."""
    new_state = state.clone()
    start_exploration(new_state, registry, player_id, position, planets)
    return new_state


def start_exploration(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
    planets: list[str],
) -> None:
    """Jak ``begin_exploration``, ale MUTUJE ``state`` (dla kodu pracującego na swoim klonie)."""
    targets = [p for p in planets if explorable(registry, p)]
    if not targets:
        return
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}.")
    if state.exploration is None:
        state.exploration = ExplorationState(player_id=player_id, position=position)
    elif state.exploration.player_id != player_id:
        raise ValueError("Another player's exploration is still in progress.")
    ex = state.exploration
    ex.queue = [*ex.queue, *(p for p in targets if p not in ex.queue)]
    _auto(state, registry)


def draw(
    state: GameState, registry: StaticDataRegistry, planet: str, deck: str | None = None
) -> GameState:
    """Gracz wybiera planetę (kolejność) i — przy kilku cechach — talię; ujawnia kartę."""
    ex = _exp(state)
    _require_no_grant(state)
    if ex.current is not None:
        raise ValueError("Resolve the revealed exploration card first.")
    if planet not in ex.queue:
        raise ValueError("This planet is not waiting to be explored.")
    traits = planet_traits(registry, planet)
    if deck is None:
        if len(traits) != 1:
            raise ValueError("Choose which exploration deck to draw from.")
        deck = traits[0]
    if deck not in traits:
        raise ValueError(f"The planet has no {deck} trait.")
    new_state = state.clone()
    _draw_for(new_state, registry, planet, deck)
    return new_state


def resolve(
    state: GameState, registry: StaticDataRegistry, option_id: str, param: str | None = None
) -> GameState:
    """Rozstrzyga ujawnioną kartę wybraną opcją; kartę odkłada wg jej rodzaju."""
    ex = _exp(state)
    cur = ex.current
    if cur is None:
        raise ValueError("No exploration card has been revealed.")
    chosen = next((o for o in options_for(state, registry) if o.id == option_id), None)
    if chosen is None:
        raise ValueError(f"Unknown option: {option_id}.")
    if not chosen.enabled:
        raise ValueError(chosen.reason or "This option is not available.")
    if chosen.params and param not in {pid for pid, _ in chosen.params}:
        raise ValueError("Choose a value for this option.")

    new_state = state.clone()
    new_ex = _exp(new_state)
    new_cur = new_ex.current
    assert new_cur is not None
    card = _card_def(registry, new_cur.card_id)
    kind = (card.resolution or "").lower()
    player = new_state.players[new_ex.player_id]

    if kind == "attach":
        summary = _apply_attach(new_state, new_ex, new_cur, card)
        fate = "attached"
    elif kind == "fragment":
        player.relic_fragments.append(new_cur.card_id)
        summary = "Placed face-up in the play area."
        fate = "kept"
    elif kind == "token":
        new_state.decks.purged.append(new_cur.card_id)  # purge ≠ odrzucenie (RULES.md 46 X3)
        if card.attachment_id == "gamma":
            tokens = _system(new_state, new_ex).wormhole_tokens
            if "GAMMA" not in tokens:
                tokens.append("GAMMA")
            summary = "Gamma wormhole token placed in the system; the card is purged."
        else:
            summary = "Place the token by hand; the card is purged."
        fate = "purged"
    else:
        handler = _INSTANT_APPLY.get((card.name or "").lower(), _apply_manual)
        summary = handler(new_state, new_ex, new_cur, option_id, param)
        new_state.decks.exploration_discard.setdefault(new_cur.deck, []).append(new_cur.card_id)
        fate = "discarded"

    new_ex.log.append(
        {
            "planet": new_cur.planet,
            "deck": new_cur.deck,
            "cardId": new_cur.card_id,
            "name": card.name,
            "option": option_id,
            "summary": summary,
            "fate": fate,
        }
    )
    new_ex.current = None
    _auto(new_state, registry)
    return new_state


def finish(state: GameState) -> GameState:
    """Zamyka okno eksploracji (dozwolone dopiero, gdy wszystko rozstrzygnięto)."""
    ex = _exp(state)
    _require_no_grant(state)
    if ex.current is not None or ex.queue:
        raise ValueError("Finish exploring every planet first.")
    new_state = state.clone()
    new_state.exploration = None
    return new_state
