"""Dodatkowe kości przy rzutach zdolności jednostek — każde źródło osobno (RULES.md 62.11).

Plasma Scoring, commander Argent (Trrakan Aun Zulok) i Strike Wing Ambuscade mówią „1 z tych
jednostek rzuca 1 dodatkową kością”. ✅ Decyzja użytkownika (2026-11-18): KAŻDE źródło gracz
przypisuje osobno (może wskazać różne jednostki), a wybór „auto” daje kość najcelniejszej grupie.

Źródła = hooki MODIFY punktu (``space_cannon.extra_dice``, ``bombardment.extra_dice``,
``combat.afb_extra_dice``) należące do gracza. Klucz źródła = komponent (``covers``) albo, dla
efektu trwałego, komponent z klucza efektu (``promissory_notes:ambuscade:die`` -> notka).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.core import rules_hooks
from src.core.game_state import GameState
from src.core.rules_hooks import SOURCE_EFFECT, HookKind

AUTO = "auto"  # wybór „auto”: najcelniejsza grupa


@dataclass(frozen=True)
class ExtraDie:
    """Jedno źródło dodatkowych kości: klucz komponentu, nazwa i liczba kości."""

    key: str
    name: str
    dice: int


def _source_key(hook: rules_hooks.Hook) -> str:
    if hook.covers:
        return hook.covers
    if hook.source.kind == SOURCE_EFFECT:
        return ":".join(str(hook.source.component_id).split(":")[:2])
    return f"{hook.source.kind}:{hook.source.component_id}"


def sources(
    state: GameState, player_id: str, point: str, ctx: Mapping[str, Any] | None = None
) -> list[ExtraDie]:
    """Źródła dodatkowych kości gracza w punkcie (kolejność deterministyczna, bez zer)."""
    from src.core.component_text import describe_component  # lokalnie: unika cyklu

    registry = rules_hooks.bound_registry()
    found: dict[str, ExtraDie] = {}
    for hook in rules_hooks.hooks_at(point, state, player_id):
        if hook.kind is not HookKind.MODIFY:
            continue
        dice = int(hook.fn(state, player_id, dict(ctx or {})) or 0)
        if dice <= 0:
            continue
        key = _source_key(hook)
        name = describe_component(registry, key)[0] if registry is not None else ""
        prior = found.get(key)
        found[key] = ExtraDie(key, name or key, dice + (prior.dice if prior else 0))
    return list(found.values())


def assign(
    extra: Sequence[ExtraDie],
    groups: Mapping[str, int],
    picks: Mapping[str, str] | None,
) -> dict[str, int]:
    """Rozdział kości: ``{klucz grupy: dodatkowe kości}``.

    ``groups`` = ``{klucz grupy: próg trafienia}`` (rzucające grupy jednostek), ``picks`` =
    ``{klucz źródła: klucz grupy | "auto" | "none"}``. ``auto`` = najcelniejsza grupa; brak
    wyboru albo ``none`` = gracz nie bierze tej kości („may” - nigdy bez decyzji gracza).

    Raises:
        ValueError: Wybór wskazuje grupę, która nie rzuca, albo nieznane źródło.
    """
    chosen = dict(picks or {})
    known = {e.key for e in extra}
    unknown = [k for k in chosen if k not in known]
    if unknown:
        raise ValueError(f"No extra dice from: {', '.join(sorted(unknown))}.")
    result: dict[str, int] = {}
    if not groups:
        return result
    best = min(groups, key=lambda g: (groups[g], g))
    for source in extra:
        pick = chosen.get(source.key) or "none"
        if pick == "none":
            continue
        target = best if pick == AUTO else pick
        if target not in groups:
            raise ValueError(f"{source.name}: choose one of the units that roll.")
        result[target] = result.get(target, 0) + source.dice
    return result


def as_view(extra: Sequence[ExtraDie]) -> list[dict[str, Any]]:
    """Źródła dla UI: ``[{key, name, dice}]``."""
    return [{"key": e.key, "name": e.name, "dice": e.dice} for e in extra]
