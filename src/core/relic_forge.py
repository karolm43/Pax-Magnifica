"""Fragmenty reliktów -> relikt: ACTION karty fragmentu (RULES.md 59.7).

Tekst karty (asset ``explores.json``): „ACTION: Purge 3 of your cultural relic fragments to gain
1 relic.” — liczbę, typ i nagrodę czytamy z tekstu karty (zero hardkodowania). Fragment
„counts as a relic fragment of any type” (Unknown) jest dżokerem, ale zestaw musi mieć co
najmniej jeden fragment z własną ACTION (C_exploration_cards: nie da się purge'ować trzech
Unknown). Pusta talia reliktów nie blokuje akcji — fragmenty idą do purge, reliktu nie ma
(R_relics, Notes).

To akcja komponentu: zużywa akcję tury (``component_action``, ``component_id="fragments:<typ>"``).
Funkcje są czyste (``state -> state``); błąd = ``ValueError`` i zero zmian.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from src.core import component_action, relic_fragments, relics, triggers
from src.core.components import ComponentCategory, ExplorationDef
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

_ACTION = re.compile(
    r"ACTION:\s*Purge\s+(\d+)\s+of\s+your\s+(\w+)\s+relic\s+fragments?\s+to\s+gain\s+(\d+)\s+relic",
    re.IGNORECASE,
)
_WILDCARD = re.compile(r"relic\s+fragment\s+of\s+any\s+type", re.IGNORECASE)


@dataclass(frozen=True)
class FragmentRule:
    """Co fragment potrafi: własna ACTION (typ, ile purge, ile reliktów) albo bycie dżokerem."""

    kind: str | None = None
    needed: int = 0
    relics: int = 0
    wildcard: bool = False


def fragment_rule(registry: StaticDataRegistry, card_id: str) -> FragmentRule:
    """Reguła fragmentu z tekstu karty eksploracji (pusta, gdy to nie fragment)."""
    card = registry.catalog.get(ComponentCategory.EXPLORATION, card_id)
    if not isinstance(card, ExplorationDef):
        return FragmentRule()
    text = " ".join(card.texts.values())
    match = _ACTION.search(text)
    if match is not None:
        return FragmentRule(
            kind=match.group(2).lower(), needed=int(match.group(1)), relics=int(match.group(3))
        )
    return FragmentRule(wildcard=bool(_WILDCARD.search(text)))


def _pick(
    registry: StaticDataRegistry, zone: list[str], kind: str, needed: int
) -> list[str]:
    """Automatyczny dobór: najpierw fragmenty typu ``kind``, dżokery na końcu."""
    own = [c for c in zone if fragment_rule(registry, c).kind == kind]
    wild = [c for c in zone if fragment_rule(registry, c).wildcard]
    return [*own, *wild][:needed] if own else []


def options(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Typy fragmentów gracza z ACTION i czy zestaw da się TERAZ połączyć w relikt.

    Każdy wiersz: ``kind``, ``needed``, ``owned`` (fragmenty typu), ``wildcards``,
    ``fragments`` (proponowany zestaw, gdy kompletny), ``reason`` (powód blokady albo ``None``)
    i ``deckEmpty`` (purge bez reliktu).
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    zone = list(player.relic_fragments)
    wildcards = sum(1 for c in zone if fragment_rule(registry, c).wildcard)
    rules: dict[str, FragmentRule] = {}
    for card_id in zone:
        rule = fragment_rule(registry, card_id)
        if rule.kind is not None:
            rules.setdefault(rule.kind, rule)
    probe = state.clone()  # talia powstaje leniwie - sprawdzamy ją na kopii, bez mutacji
    relics.ensure_relic_deck(probe, registry)
    deck_empty = not probe.decks.relic_deck and not probe.decks.relic_discard
    turn_reason = _turn_reason(state, player_id)
    rows: list[dict[str, Any]] = []
    for kind, rule in rules.items():
        owned = sum(1 for c in zone if fragment_rule(registry, c).kind == kind)
        chosen = _pick(registry, zone, kind, rule.needed)
        reason = turn_reason
        if len(chosen) < rule.needed:
            reason = f"You need {rule.needed} {kind} relic fragments (Unknown ones count)."
        rows.append(
            {
                "kind": kind,
                "needed": rule.needed,
                "owned": owned,
                "wildcards": wildcards,
                "fragments": chosen if len(chosen) == rule.needed else [],
                "reason": reason,
                "deckEmpty": deck_empty,
            }
        )
    return rows


def _turn_reason(state: GameState, player_id: str) -> str | None:
    """Powód, dla którego gracz nie może TERAZ wykonać akcji komponentu (próba sucha)."""
    try:
        component_action.play_component_action(
            state, player_id, "fragments", fire_after=False, run_effect=False
        )
    except ValueError as exc:
        return str(exc)
    return None


def validate(
    state: GameState, registry: StaticDataRegistry, player_id: str, fragment_ids: list[str]
) -> FragmentRule:
    """Sprawdza zestaw fragmentów do purge i zwraca regułę, wg której łączymy.

    Raises:
        ValueError: Gracz nie ma tych fragmentów, zła liczba, mieszane typy, same dżokery.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    owned = Counter(player.relic_fragments)
    for card_id, count in Counter(fragment_ids).items():
        if owned[card_id] < count:
            raise ValueError(f"You do not have the relic fragment '{card_id}'.")
    typed = [fragment_rule(registry, c) for c in fragment_ids]
    kinds = {r.kind for r in typed if r.kind is not None}
    if not kinds:
        raise ValueError(
            "At least one cultural, hazardous or industrial relic fragment must be purged."
        )
    if len(kinds) > 1:
        raise ValueError("All purged relic fragments must be of the same type.")
    if any(r.kind is None and not r.wildcard for r in typed):
        raise ValueError("Only relic fragments can be purged for a relic.")
    rule = next(r for r in typed if r.kind is not None)
    if len(fragment_ids) != rule.needed:
        raise ValueError(f"You must purge exactly {rule.needed} {rule.kind} relic fragments.")
    return rule


def forge(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    fragment_ids: list[str],
    *,
    actor_id: str | None = None,
) -> GameState:
    """Gracz purge'uje zestaw fragmentów i dobiera relikt(y) — jego akcja w turze.

    Raises:
        ValueError: Nie jego tura / nie może wykonać akcji / zły zestaw fragmentów.
    """
    if actor_id is not None and actor_id != player_id:
        raise ValueError(f"{actor_id} cannot purge relic fragments for {player_id}.")
    rule = validate(state, registry, player_id, fragment_ids)
    component = f"fragments:{rule.kind}"
    new_state = component_action.play_component_action(
        state, player_id, component, fire_after=False, run_effect=False
    )
    relic_fragments.purge_chosen(new_state, player_id, list(fragment_ids))
    for _ in range(rule.relics):
        relics.draw_relic(
            new_state, registry, player_id,
            source="fragments", detail={"fragments": list(fragment_ids), "kind": rule.kind},
        )
    triggers.fire(
        new_state, GameEvent.COMPONENT_ACTION, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "component": component},
    )
    return new_state
