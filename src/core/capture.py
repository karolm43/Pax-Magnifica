"""Przechwytywanie jednostek (capture) — JEDYNE miejsce zmiany ich stanu (RULES.md 61.5).

Źródło: ``docs/rules_tirules/R_capture.md``, ``R_blockaded.md``. Stan leży w ``PlayerState``:

- ``captured_units`` = ``{pierwotny właściciel: {typ bazowy: sztuki}}`` — statki inne niż myśliwce
  i mechy na arkuszu frakcji przechwytującego (także jego WŁASNE jednostki);
- ``captured_tokens`` = ``{"fighter" | "infantry": sztuki}`` — R_capture: przechwycony
  myśliwiec / piechota wraca do rezerwy właściciela, a przechwytujący kładzie żeton z puli (nie
  należy do nikogo).

Kto i kiedy przechwytuje zniszczoną jednostkę, mówią komponenty przez hook PERMIT
``capture.destroyed`` (Devour, The Terror Between, Reanimator). Funkcje MUTUJĄ przekazany ``state``
(klon wołającego), poza :func:`release_blockaded` (czysta, zwraca nowy stan albo ten sam).
"""

from __future__ import annotations

from typing import Any

from src.core import rules_hooks
from src.core.game_state import GameState, SystemState
from src.core.unit_catalog import is_space_unit

TOKEN_TYPES = ("fighter", "infantry")  # żetony zastępcze: przechwytywane jako żeton z puli
STRUCTURES = ("pds", "spacedock")
TOKEN = "token"  # „właściciel” żetonu przy zwrocie / wydaniu (parametry API)


def capturable(base_type: str) -> bool:
    """R_capture: przechwytuje się jednostki inne niż struktury."""
    return base_type not in STRUCTURES


def is_token(base_type: str) -> bool:
    return base_type in TOKEN_TYPES


def captured_from(state: GameState, owner: str, base_type: str) -> int:
    """Ile statków/mechów ``owner`` typu ``base_type`` leży na arkuszach WSZYSTKICH graczy.

    Te sztuki są poza rezerwą właściciela (``production.reinforcements_left``).
    """
    if is_token(base_type):
        return 0
    return sum(
        p.captured_units.get(owner, {}).get(base_type, 0) for p in state.players.values()
    )


def held(state: GameState, capturer: str, base_type: str) -> dict[str, int]:
    """``{właściciel | "token": sztuki}`` jednostek ``base_type`` na arkuszu ``capturer``."""
    player = state.players.get(capturer)
    if player is None:
        return {}
    if is_token(base_type):
        count = player.captured_tokens.get(base_type, 0)
        return {TOKEN: count} if count > 0 else {}
    return {
        owner: units[base_type]
        for owner, units in sorted(player.captured_units.items())
        if units.get(base_type, 0) > 0
    }


def total_held(state: GameState, capturer: str) -> int:
    player = state.players.get(capturer)
    if player is None:
        return 0
    return sum(player.captured_tokens.values()) + sum(
        n for units in player.captured_units.values() for n in units.values()
    )


def _space_docks(state: GameState, player_id: str) -> list[str]:
    """Pozycje systemów z dokiem gracza (na planecie albo w przestrzeni — Floating Factory)."""
    found: list[str] = []
    for position, system in state.systems.items():
        if system.space_units.get(player_id, {}).get("spacedock", 0) > 0 or any(
            by_player.get(player_id, {}).get("spacedock", 0) > 0
            for by_player in system.planet_units.values()
        ):
            found.append(position)
    return sorted(found)


def _has_ships(system: SystemState, player_id: str) -> bool:
    return any(
        n > 0 and is_space_unit(bt) and bt not in STRUCTURES
        for bt, n in system.space_units.get(player_id, {}).items()
    )


def blockaders(state: GameState, player_id: str) -> set[str]:
    """Gracze blokujący KTÓRYKOLWIEK dok ``player_id`` (R_blockaded: ich statki w systemie doku,
    statków gracza brak)."""
    found: set[str] = set()
    for position in _space_docks(state, player_id):
        system = state.systems[position]
        if _has_ships(system, player_id):
            continue
        found |= {other for other in system.space_units if other != player_id
                  and _has_ships(system, other)}
    return found


def may_capture_from(state: GameState, capturer: str, owner: str) -> bool:
    """R_capture: gracz z blokowanym dokiem nie przechwytuje jednostek blokujących (ani żetonów)."""
    return owner == capturer or owner not in blockaders(state, capturer)


def _add(state: GameState, capturer: str, owner: str, base_type: str, count: int) -> int:
    if count <= 0 or not capturable(base_type) or capturer not in state.players:
        return 0
    if not may_capture_from(state, capturer, owner):
        return 0
    player = state.players[capturer]
    if is_token(base_type):
        tokens = dict(player.captured_tokens)
        tokens[base_type] = tokens.get(base_type, 0) + count
        player.captured_tokens = tokens
    else:
        units = {o: dict(u) for o, u in player.captured_units.items()}
        bucket = units.setdefault(owner, {})
        bucket[base_type] = bucket.get(base_type, 0) + count
        player.captured_units = units
    return count


def capture_removed(
    state: GameState, capturer: str, owner: str, base_type: str, count: int = 1
) -> int:
    """Kładzie na arkusz ``capturer`` jednostki JUŻ zdjęte z planszy (zniszczone/usunięte).

    Returns:
        Ile sztuk przechwycono (0: struktura albo zakaz z blokady).
    """
    return _add(state, capturer, owner, base_type, count)


def unit_label(state: GameState, owner: str, base_type: str, count: int) -> str:
    """„2 Destroyer II (Sol)” - pełna nazwa wariantu z danych (feed Activity)."""
    registry = rules_hooks.bound_registry()
    player = state.players.get(owner)
    name = base_type
    who = owner
    if registry is not None and player is not None:
        from src.core.combat import resolve_unit_variant  # lokalnie: combat jest wyżej

        unit = resolve_unit_variant(registry, player.faction, player.technologies, base_type)
        name = unit.name if unit is not None else base_type
        faction = registry.factions.get(player.faction or "")
        who = faction.name if faction is not None else owner
    return f"{count} {name} ({who})"


def note_capture(
    state: GameState, capturer: str, component: str, owner: str, base_type: str, count: int
) -> None:
    """Widoczny skutek w feedzie Activity (``ability_notes``): kto, czym, co przechwycił."""
    if count <= 0:
        return
    from src.core import ability_notes  # lokalnie: unika cyklu importów

    ability_notes.note(
        state, capturer, component, f"captured {unit_label(state, owner, base_type, count)}"
    )


def on_destroyed(
    state: GameState, position: str, zone: str, owner: str, base_type: str, count: int
) -> None:
    """Zniszczona jednostka: pierwszy gracz, którego komponent pozwala (PERMIT
    ``capture.destroyed``), przechwytuje ją (raz). Woła ``unit_ops.remove_units`` po zdjęciu
    z planszy."""
    if not capturable(base_type) or count <= 0:
        return
    ctx: dict[str, Any] = {
        "player": owner, "base_type": base_type, "position": position, "zone": zone,
    }
    for capturer in sorted(state.players):
        for hook in rules_hooks.hooks_at(rules_hooks.POINT_CAPTURE_DESTROYED, state, capturer):
            if hook.kind is not rules_hooks.HookKind.PERMIT or not hook.fn(state, capturer, ctx):
                continue
            taken = capture_removed(state, capturer, owner, base_type, count)
            note_capture(state, capturer, hook.covers or "", owner, base_type, taken)
            return


def can_capture_from_reinforcements(
    state: GameState, capturer: str, owner: str, base_type: str
) -> bool:
    """Czy w rezerwie ``owner`` jest sztuka do przechwycenia (myśliwce/piechota: zawsze)."""
    if not capturable(base_type) or not may_capture_from(state, capturer, owner):
        return False
    if is_token(base_type):
        return True
    from src.core import production  # lokalnie: production importuje ten moduł

    left = production.reinforcements_left(state, owner, base_type)
    return left is None or left > 0


def from_reinforcements(state: GameState, capturer: str, owner: str, base_type: str) -> None:
    """Przechwytuje 1 jednostkę z rezerwy ``owner`` (Vortex, The Stillness of Stars).

    Raises:
        ValueError: Brak sztuki w rezerwie, struktura albo zakaz z blokady.
    """
    if not can_capture_from_reinforcements(state, capturer, owner, base_type):
        raise ValueError("That player has no such unit in reinforcements that can be captured.")
    _add(state, capturer, owner, base_type, 1)


def from_board(
    state: GameState, capturer: str, owner: str, position: str, zone: str, base_type: str,
    count: int = 1,
) -> int:
    """Zdejmuje jednostki z planszy BEZ zniszczenia i przechwytuje je (Dimensional Anchor)."""
    from src.core import unit_ops  # lokalnie: unit_ops woła ``on_destroyed``

    system = state.systems[position]
    have = unit_ops.count_in_zone(system, zone, owner, base_type)
    take = min(count, have)
    if take <= 0 or not capturable(base_type) or not may_capture_from(state, capturer, owner):
        return 0
    unit_ops.remove_units(state, system, zone, owner, base_type, take, unit_ops.UnitCause.REMOVED)
    return _add(state, capturer, owner, base_type, take)


def return_unit(
    state: GameState, capturer: str, owner: str, base_type: str, count: int = 1
) -> None:
    """Zwraca przechwycone jednostki: statek/mech → rezerwa pierwotnego właściciela (wyeliminowany:
    pudełko), żeton → pula. ``owner`` = ``"token"`` dla myśliwców/piechoty.

    Raises:
        ValueError: Na arkuszu nie ma tylu takich jednostek.
    """
    player = state.players.get(capturer)
    if player is None or count <= 0:
        raise ValueError("Nothing to return.")
    if is_token(base_type):
        have = player.captured_tokens.get(base_type, 0)
        if count > have:
            raise ValueError("You have not captured that many of these units.")
        tokens = dict(player.captured_tokens)
        tokens[base_type] = have - count
        player.captured_tokens = {k: v for k, v in tokens.items() if v > 0}
        return
    units = {o: dict(u) for o, u in player.captured_units.items()}
    have = units.get(owner, {}).get(base_type, 0)
    if count > have:
        raise ValueError("You have not captured that many of these units.")
    units[owner][base_type] = have - count
    units[owner] = {k: v for k, v in units[owner].items() if v > 0}
    player.captured_units = {o: u for o, u in units.items() if u}


def spend_captured(state: GameState, capturer: str, base_type: str, owner: str) -> None:
    """Koszt komponentu „return 1 captured unit of that type” (Amalgamation, Riftmeld)."""
    return_unit(state, capturer, TOKEN if is_token(base_type) else owner, base_type, 1)


def release_blockaded(state: GameState) -> GameState:
    """R_blockaded: właściciel blokujący dok przechwytującego odzyskuje swoje statki/mechy.

    Czysta: zwraca nowy stan, gdy coś wróciło, inaczej ten sam obiekt. Wołana po KAŻDYM kroku
    (``step_settle``), więc zwrot następuje od razu (np. po kroku walki kosmicznej, przed inwazją).
    """
    pending = [
        (capturer, owner)
        for capturer, player in state.players.items()
        if player.captured_units
        for owner in blockaders(state, capturer)
        if player.captured_units.get(owner)
    ]
    if not pending:
        return state
    new_state = state.clone()
    for capturer, owner in pending:
        player = new_state.players[capturer]
        player.captured_units = {
            o: u for o, u in player.captured_units.items() if o != owner
        }
    return new_state


def nombox(state: GameState, capturer: str) -> dict[str, list[str]]:
    """Widok dla web-data: ``{frakcja właściciela: ["<typ>,<sztuki>"]}`` (żetony pod frakcją
    przechwytującego)."""
    player = state.players.get(capturer)
    if player is None:
        return {}
    out: dict[str, list[str]] = {}
    for owner, units in sorted(player.captured_units.items()):
        owner_state = state.players.get(owner)
        key = (owner_state.faction if owner_state is not None else None) or owner
        out.setdefault(key, []).extend(f"{bt},{n}" for bt, n in sorted(units.items()) if n > 0)
    if player.captured_tokens:
        key = player.faction or capturer
        out.setdefault(key, []).extend(
            f"{bt},{n}" for bt, n in sorted(player.captured_tokens.items()) if n > 0
        )
    return {k: v for k, v in out.items() if v}
