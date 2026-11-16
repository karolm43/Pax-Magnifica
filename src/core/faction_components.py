"""Komponenty frakcji w akcji komponentu: liderzy, zdolności frakcji, przełom — RULES.md 61.3.

Odpowiednik ``relic_actions`` / ``planet_abilities`` dla komponentów frakcyjnych. Komponent z
nagłówkiem ``ACTION:`` zagrywa się przez ``component_action.play_component_action`` z id
``<rodzaj>:<id>`` (``leader:``, ``ability:``, ``breakthrough:``) — to akcja tury. Efekt rejestruje
moduł frakcji (``core/hooks/factions/<frakcja>.py``) przez ``rules_hooks.register_effect`` pod
kluczem kategorii (``leaders:<id>``, ``abilities:<id>``, ``breakthroughs:<id>``) +
``register_effect_inputs`` (formularz). Dodatkowy warunek zagrywalności: :func:`blocker`.

Koszt użycia płaci TEN moduł (jednolicie, po udanym efekcie): lider — wg tekstu karty
(``leaders.pay_usage``: wyczerpanie agenta, purge bohatera), przełom — wyczerpanie, gdy tekst
mówi „Exhaust this card". Zdolność frakcji nie ma kosztu ogólnego (np. żeton ze strategii płaci
efekt). Komponenty bez ``ACTION:`` działają przez hooki/oferty (``rules_hooks.on_event``).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from src.core import exhaust, leaders, offer_inputs, rules_hooks, triggers
from src.core.components import ComponentCategory
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

LEADER = "leader"
ABILITY = "ability"
BREAKTHROUGH = "breakthrough"
# Technologia frakcyjna z oknem użycia (``window_use``), np. Instinct Training (RULES.md 62.9):
# tylko takie trafiają do ``owned`` - zwykłe technologie działają przez hooki i oferty.
TECHNOLOGY = "technology"
KINDS: tuple[str, ...] = (LEADER, ABILITY, BREAKTHROUGH, TECHNOLOGY)
_CATEGORY = {
    LEADER: ComponentCategory.LEADER.value,
    ABILITY: ComponentCategory.ABILITY.value,
    BREAKTHROUGH: ComponentCategory.BREAKTHROUGH.value,
    TECHNOLOGY: ComponentCategory.TECHNOLOGY.value,
}
# Nagłówek akcji komponentu (dane piszą go WIELKIMI literami; „an action:" to nie nagłówek).
_ACTION = re.compile(r"(?:^|[\n.:]\s*)ACTION\s*:")
_EXHAUST_SELF = re.compile(r"\bexhaust this card\b", re.IGNORECASE)

BlockerFn = Callable[[GameState, StaticDataRegistry, str], str | None]
_BLOCKERS: dict[str, BlockerFn] = {}
# „During/After X: you may…" — komponent używany z inicjatywy gracza poza akcją tury (RULES.md
# 62.0): warunek okna zwraca powód odmowy albo None (= wolno teraz).
_WINDOW_USES: dict[str, BlockerFn] = {}
_STANDING_WINDOWS: set[str] = set()
"""Okna ``window_use`` trwające całą fazę (``standing=True``) - UI: znacznik, nie karta."""
_HOLD_RESPONSES: set[str] = set()
"""Okna ``window_use`` odpowiadające na kartę czekającą w ``held_play`` (``holds=True``)."""


def effect_key(kind: str, component: str) -> str:
    """Klucz komponentu w rejestrze efektów (``leaders:<id>`` itd.)."""
    if kind not in _CATEGORY:
        raise ValueError(f"Unknown faction component kind: {kind}")
    return f"{_CATEGORY[kind]}:{component}"


def component_id(kind: str, component: str) -> str:
    """Id przekazywane do akcji komponentu (``leader:<id>`` itd.)."""
    return f"{kind}:{component}"


def parse(component: str) -> tuple[str, str] | None:
    """``(rodzaj, id)`` z id akcji komponentu albo ``None`` (to nie komponent frakcji)."""
    kind, sep, rest = component.partition(":")
    if not sep or kind not in KINDS or not rest:
        return None
    return kind, rest


def blocker(kind: str, component: str) -> Callable[[BlockerFn], BlockerFn]:
    """Rejestruje dodatkowy warunek zagrywalności ACTION (zwraca powód odmowy albo ``None``)."""
    key = effect_key(kind, component)

    def decorate(fn: BlockerFn) -> BlockerFn:
        if key in _BLOCKERS:
            raise ValueError(f"Blocker already registered for {key}.")
        _BLOCKERS[key] = fn
        return fn

    return decorate


def window_use(
    kind: str, component: str, *, standing: bool = False, holds: bool = False
) -> Callable[[BlockerFn], BlockerFn]:
    """Rejestruje komponent bez ``ACTION:`` używany przez gracza w danym kroku (RULES.md 62.0).

    ``fn(state, registry, player_id)`` = powód, dla którego TERAZ nie wolno, albo ``None``. Efekt
    to zwykłe ``register_effect`` komponentu; użycie NIE zużywa akcji tury.

    ``standing=True``: okno trwa całą fazę (np. „During the action phase: you may…”, Carth of
    Golden Sands) - nie jest chwilą, którą łatwo przegapić, więc UI pokazuje je jako mały znacznik
    „gotowe do użycia”, a nie wyskakującą kartę.

    ``holds=True``: komponent odpowiada na kartę akcji czekającą w oknie hold (Instinct Training,
    RULES.md 62.9) - jedyne użycie dozwolone w trakcie tego okna.
    """
    key = effect_key(kind, component)

    def decorate(fn: BlockerFn) -> BlockerFn:
        if key in _WINDOW_USES:
            raise ValueError(f"Window use already registered for {key}.")
        _WINDOW_USES[key] = fn
        if standing:
            _STANDING_WINDOWS.add(key)
        if holds:
            _HOLD_RESPONSES.add(key)
        return fn

    return decorate


def _mode(kind: str, component: str, text: str) -> str:
    if _ACTION.search(text):
        return "action"
    rules_hooks.effect_for(effect_key(kind, component))  # ładuje pakiet hooków
    return "window" if effect_key(kind, component) in _WINDOW_USES else "passive"


# --- Dane ---------------------------------------------------------------------------------------


def _faction(registry: StaticDataRegistry, state: GameState, player_id: str) -> Any:
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    return registry.factions.get(player.faction or "")


def describe(registry: StaticDataRegistry, kind: str, component: str) -> tuple[str, str]:
    """``(nazwa, pełny tekst)`` komponentu z danych.

    Raises:
        ValueError: Nieznany komponent.
    """
    if kind == LEADER:
        leader = leaders.leader_def(registry, component)
        window = leader.ability_window or ""
        return leader.name, f"{window} {leader.ability_text or ''}".strip()
    if kind == ABILITY:
        ability = registry.abilities.get(component)
        if ability is None:
            raise ValueError(f"Unknown faction ability: {component}")
        parts = [ability.permanent_effect, ability.window, ability.window_effect]
        window = ability.window or ""
        if window.strip().upper().startswith("ACTION"):
            parts = [ability.permanent_effect, f"ACTION: {ability.window_effect or ''}"]
        return ability.name, " ".join(p for p in parts if p).strip()
    if kind == TECHNOLOGY:
        tech = registry.technologies.get(component)
        if tech is None:
            raise ValueError(f"Unknown technology: {component}")
        return tech.name, tech.text or ""
    breakthrough = registry.breakthroughs.get(component)
    if breakthrough is None:
        raise ValueError(f"Unknown breakthrough: {component}")
    return breakthrough.name, breakthrough.text or ""


def is_action(registry: StaticDataRegistry, kind: str, component: str) -> bool:
    """Czy komponent ma zdolność „ACTION:” (zagrywaną jako akcja komponentu)."""
    try:
        _, text = describe(registry, kind, component)
    except ValueError:
        return False
    return bool(_ACTION.search(text))


def owned(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[tuple[str, str]]:
    """Komponenty frakcji gracza: liderzy, zdolności, przełom (gdy zdobyty)."""
    faction = _faction(registry, state, player_id)
    if faction is None:
        return []
    rows: list[tuple[str, str]] = [(LEADER, lid) for lid in faction.leaders]
    rows += [(ABILITY, aid) for aid in faction.abilities if aid in registry.abilities]
    breakthrough = registry.breakthrough_for_faction(state.players[player_id].faction)
    if breakthrough is not None and state.players[player_id].breakthrough_unlocked:
        rows.append((BREAKTHROUGH, breakthrough.id))
    for tech in state.players[player_id].technologies:
        if _has_window_use(TECHNOLOGY, tech):
            rows.append((TECHNOLOGY, tech))
    return rows


def _has_window_use(kind: str, component: str) -> bool:
    key = effect_key(kind, component)
    rules_hooks.effect_for(key)  # ładuje pakiet hooków
    return key in _WINDOW_USES


def _owns(
    state: GameState, registry: StaticDataRegistry, player_id: str, kind: str, comp: str
) -> bool:
    return (kind, comp) in owned(state, registry, player_id)


# --- Zagrywalność -------------------------------------------------------------------------------


def block_reason(
    state: GameState, registry: StaticDataRegistry, player_id: str, kind: str, component: str
) -> str | None:
    """Powód, dla którego komponent nie może TERAZ wykonać ACTION (``None`` = może)."""
    key = effect_key(kind, component)
    rules_hooks.effect_for(key)  # wymusza załadowanie pakietu hooków
    if not _owns(state, registry, player_id, kind, component):
        return f"{component} is not your component."
    if kind == ABILITY:
        from src.core import promissory_play  # lokalnie: promissory_play importuje component_action

        if promissory_play.silenced(state, player_id):
            return "Political Secret: you cannot use faction abilities during this agenda."
    if kind == LEADER:
        reason = leaders.use_reason(state, registry, player_id, component)
        if reason is not None:
            return reason
    if kind == BREAKTHROUGH and _exhausts_self(registry, kind, component):
        if state.players[player_id].breakthrough_exhausted:
            return "Your breakthrough is exhausted."
    if kind == TECHNOLOGY and _exhausts_self(registry, kind, component):
        if component in state.players[player_id].exhausted_technologies:
            return "This technology is exhausted."
    fn = _BLOCKERS.get(key)
    return fn(state, registry, player_id) if fn is not None else None


def _exhausts_self(registry: StaticDataRegistry, kind: str, component: str) -> bool:
    _, text = describe(registry, kind, component)
    return bool(_EXHAUST_SELF.search(text))


def form(
    state: GameState, registry: StaticDataRegistry, player_id: str, kind: str, component: str
) -> dict[str, Any]:
    """Opis komponentu dla UI: tekst, rodzaj, czy silnik go automatyzuje, stan i formularz.

    Raises:
        ValueError: Nieznany komponent albo gracz go nie ma.
    """
    name, text = describe(registry, kind, component)
    if not _owns(state, registry, player_id, kind, component):
        raise ValueError(f"You do not have {name}.")
    key = effect_key(kind, component)
    mode = _mode(kind, component, text)
    action = mode != "passive"
    inputs: list[dict[str, Any]] = []
    if action and rules_hooks.effect_for(key) is not None:
        inputs_fn = rules_hooks.inputs_for(key)
        inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
        from src.core.hooks import card_labels  # lokalnie: pakiet hooks importuje ten moduł

        inputs = card_labels.with_default_hints(inputs, name, text)
    covered = key in rules_hooks.covered_components()
    implemented = rules_hooks.effect_for(key) is not None if action else covered
    status = ""
    if kind == LEADER:
        status = leaders.state_of(state, registry, player_id, component)
    elif kind == BREAKTHROUGH:
        status = "exhausted" if state.players[player_id].breakthrough_exhausted else "unlocked"
    elif kind == TECHNOLOGY:
        exhausted = component in state.players[player_id].exhausted_technologies
        status = "exhausted" if exhausted else "ready"
    leader = registry.leaders.get(component) if kind == LEADER else None
    return {
        "kind": kind,
        "component_id": component,
        "name": name,
        "text": text,
        "mode": mode,
        "implemented": implemented,
        "inputs": inputs,
        "status": status,
        "leader_type": leader.type if leader is not None else None,
        "unlock_condition": leader.unlock_condition if leader is not None else None,
        "can_claim_unlock": bool(
            leader is not None
            and status == leaders.LOCKED
            and leaders.unlock_predicate(registry, component) is None
            and not leaders.has_event_unlock(component)
        ),
    }


def playability(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Komponenty frakcji gracza i które ACTION można zagrać TERAZ. Nie mutuje stanu."""
    from src.core import component_action  # lokalnie: component_action importuje ten moduł

    rows: list[dict[str, Any]] = []
    for kind, component in owned(state, registry, player_id):
        info = form(state, registry, player_id, kind, component)
        row: dict[str, Any] = {
            "kind": kind,
            "component_id": component,
            "name": info["name"],
            "mode": info["mode"],
            "status": info["status"],
            "implemented": info["implemented"],
            "playable": False,
            "reason": None,
        }
        rows.append(row)
        if info["mode"] == "passive":
            row["reason"] = "Passive - it works on its own (offers appear at the right moment)."
            continue
        if info["mode"] == "window":
            reason = block_reason(state, registry, player_id, kind, component)
            if reason is None:
                reason = _WINDOW_USES[effect_key(kind, component)](state, registry, player_id)
            if reason is None and info["implemented"] and not offer_inputs.has_legal_answer(
                info["inputs"]
            ):
                reason = "No legal target for this ability right now."
            row["reason"] = reason
            row["playable"] = reason is None
            continue
        try:
            component_action.play_component_action(
                state, player_id, component_id(kind, component), fire_after=False, run_effect=False
            )
        except ValueError as exc:
            row["reason"] = str(exc)
            continue
        reason = block_reason(state, registry, player_id, kind, component)
        if reason is not None:
            row["reason"] = reason
        elif info["implemented"] and not offer_inputs.has_legal_answer(info["inputs"]):
            row["reason"] = "No legal target for this ability right now."
        else:
            row["playable"] = True
    return rows


def available_now(
    state: GameState, registry: StaticDataRegistry, player_ids: list[str]
) -> list[dict[str, Any]]:
    """Zdolności „During X: you may…” (RULES.md 62.0), których gracze mogą użyć TERAZ.

    UI pokazuje je same (karta „Available now”), żeby gracz nie musiał szukać ich w menu.
    Nie mutuje stanu.
    """
    found: list[dict[str, Any]] = []
    for player_id in player_ids:
        if player_id not in state.players:
            continue
        for row in playability(state, registry, player_id):
            if row["mode"] != "window" or not row["playable"]:
                continue
            _, text = describe(registry, row["kind"], row["component_id"])
            found.append({
                "player_id": player_id, "kind": row["kind"],
                "component_id": row["component_id"], "name": row["name"], "text": text,
                "standing": effect_key(row["kind"], row["component_id"]) in _STANDING_WINDOWS,
            })
    return found


def combat_dice_uses(state: GameState, registry: StaticDataRegistry) -> list[dict[str, Any]]:
    """Komponenty „During X: you may…” zmieniające kości rundy walki, dostępne TERAZ.

    Dla uczestników trwającej walki: zdolność/lider/przełom z oknem użycia (``window_use``),
    którego warunek jest spełniony i którego formularz to wybór kości (``dice``). Okno walki
    pokazuje je obok reliktów (np. Munitions Reserves po rzucie, przed przypisaniem strat).
    Zwraca ``[{player, kind, component, name, text, min, max}]``.
    """
    combat = state.active_combat
    if combat is None:
        return []
    uses: list[dict[str, Any]] = []
    for pid in (combat.attacker, combat.defender):
        if pid not in state.players:
            continue
        for kind, component in owned(state, registry, pid):
            key = effect_key(kind, component)
            rules_hooks.effect_for(key)  # ładuje pakiet hooków
            check = _WINDOW_USES.get(key)
            if check is None or check(state, registry, pid) is not None:
                continue
            if block_reason(state, registry, pid, kind, component) is not None:
                continue
            inputs_fn = rules_hooks.inputs_for(key)
            inputs = inputs_fn(state, registry, pid) if inputs_fn is not None else []
            dice = next((i for i in inputs if i.get("key") == "dice"), None)
            if dice is None or dice.get("kind") != "multi" or not dice.get("options"):
                continue
            name, text = describe(registry, kind, component)
            uses.append({
                "player": pid, "kind": kind, "component": component, "name": name,
                "text": text, "min": int(dice.get("min", 0)), "max": int(dice.get("max", 0)),
            })
    return uses


# --- Wykonanie ----------------------------------------------------------------------------------


def ability_used(state: GameState, player_id: str, ability: str, target: str) -> None:
    """Zdolność frakcji gracza została użyta przeciw ``target`` (MUTUJE klon wołającego).

    Jedyne miejsce emisji ``FACTION_ABILITY_USED/AFTER`` (ctx: player, ability, target): np.
    Pillage → agent Suffi An; S'ula Mentarion → wybór notki przez przeciwnika (RULES.md 62.8).
    """
    triggers.fire(
        state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "ability": ability, "target": target},
    )


def pay_cost(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    kind: str,
    component: str,
    ctx: Mapping[str, Any] | None = None,
) -> None:
    """Koszt użycia komponentu (MUTUJE ``state``): lider wg tekstu, przełom — wyczerpanie.

    Wołają go też hooki zdarzeń frakcji (oferty „you may exhaust this card"). Wyczerpanie emituje
    ``COMPONENT_EXHAUSTED/AFTER`` z ``component="<kategoria>:<id>"`` i ``ctx`` wołającego (np.
    gracz, któremu agent coś daje — decyzja tego gracza to osobny hook, RULES.md 62.1).
    """
    exhausted = False
    if kind == LEADER:
        exhausted = leaders.usage_cost(registry, component) == "exhaust"
        leaders.pay_usage(state, registry, player_id, component)
    elif kind == BREAKTHROUGH and _exhausts_self(registry, kind, component):
        if state.players[player_id].breakthrough_exhausted:
            raise ValueError("Your breakthrough is exhausted.")
        exhaust.exhaust_breakthrough(state, player_id)
        exhausted = True
    elif kind == TECHNOLOGY and _exhausts_self(registry, kind, component):
        exhaust.exhaust_technology(state, player_id, component)
        exhausted = True
    if exhausted:
        triggers.fire(
            state, GameEvent.COMPONENT_EXHAUSTED, Moment.AFTER, subject=player_id,
            ctx={**dict(ctx or {}), "player": player_id,
                 "component": effect_key(kind, component)},
        )


def run_action_effect(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    component: str,
    params: Mapping[str, Any] | None,
) -> bool:
    """Wykonuje ACTION komponentu frakcji na ``state`` (KLON wołającego) i płaci koszt.

    Returns:
        True, gdy ``component`` to komponent frakcji (efekt zastosowany albo — bez efektu w
        kodzie — tylko koszt zapłacony, skutek rozstrzyga operator); False dla innych id.

    Raises:
        ValueError: Komponent nie jest gotowy / nie ma ACTION / wybory spoza legalnych opcji.
    """
    parsed = parse(component)
    if parsed is None:
        return False
    kind, comp = parsed
    if not is_action(registry, kind, comp):
        raise ValueError(f"{comp} has no ACTION - it works on its own.")
    reason = block_reason(state, registry, player_id, kind, comp)
    if reason is not None:
        raise ValueError(reason)
    key = effect_key(kind, comp)
    effect = rules_hooks.effect_for(key)
    if effect is not None:
        inputs_fn = rules_hooks.inputs_for(key)
        inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
        effect(state, registry, player_id, offer_inputs.validate_params(inputs, params or {}))
    # Koszt po efekcie: efekt może sprawdzać gotowość komponentu (np. bohater) bez wyjątków.
    pay_cost(state, registry, player_id, kind, comp)
    return True


def _use_in_window(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    kind: str,
    component: str,
    params: Mapping[str, Any] | None,
    info: Mapping[str, Any],
) -> tuple[GameState, bool]:
    """Użycie „During X: you may…" (RULES.md 62.0): bez akcji tury, efekt + koszt na klonie."""
    key = effect_key(kind, component)
    if state.held_play is not None and key not in _HOLD_RESPONSES:
        from src.core import card_hold  # lokalnie: card_hold importuje moduły kart

        card_hold.require_no_hold(state)
    reason = _WINDOW_USES[key](state, registry, player_id)
    if reason is not None:
        raise ValueError(reason)
    new_state = state.clone()
    effect = rules_hooks.effect_for(key)
    if effect is not None:
        inputs_fn = rules_hooks.inputs_for(key)
        inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
        effect(new_state, registry, player_id, offer_inputs.validate_params(inputs, params or {}))
    pay_cost(new_state, registry, player_id, kind, component)
    return new_state, bool(info["implemented"])


def play(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    kind: str,
    component: str,
    params: Mapping[str, Any] | None = None,
    *,
    actor_id: str | None = None,
) -> tuple[GameState, bool]:
    """Aktywny gracz zagrywa ACTION komponentu frakcji (akcja komponentu tury).

    Błąd na dowolnym etapie = ``ValueError`` i ZERO zmian (praca na klonie).

    Returns:
        ``(nowy stan, implemented)``.
    """
    from src.core import component_action  # lokalnie: component_action importuje ten moduł

    if actor_id is not None and actor_id != player_id:
        raise ValueError(f"{actor_id} cannot use a component for {player_id}.")
    info = form(state, registry, player_id, kind, component)
    if info["mode"] == "passive":
        raise ValueError(f"{info['name']} has no ACTION - it works on its own.")
    reason = block_reason(state, registry, player_id, kind, component)
    if reason is not None:
        raise ValueError(reason)
    if info["mode"] == "window":
        return _use_in_window(state, registry, player_id, kind, component, params, info)
    new_state = component_action.play_component_action(
        state, player_id, component_id(kind, component), params=params
    )
    return new_state, bool(info["implemented"])
