"""Dziennik aktywności graczy — „kto co zrobił" (feed powiadomień).

Każdy commit stanu ma etykietę techniczną (``strategy:pick:p2:3``, ``turn:pass``…).
Etykieta nie mówi, KTO działał ani CO się zmieniło, więc sama nie nadaje się do
czytelnego feedu. Ten moduł to CZYSTA funkcja ``derive_activity(label, before, after)``,
która tłumaczy parę migawek na ustrukturyzowany wpis :class:`Activity`:

- ``actor_id`` / ``target_id`` — kto działał i (opcjonalnie) kogo dotyczy akcja,
- ``kind`` / ``action`` — kategoria (do filtrów) i klucz akcji (do opisu we froncie),
- ``subject`` / ``detail`` — o czym mowa (planeta, system, karta, cel…),
- ``facts`` — skutki wyliczone z RÓŻNICY stanów (VP, technologie, planety, TG).

Nazwy do wyświetlenia (planety, technologie, karty) rozwiązuje frontend z własnych
lookupów — backend przekazuje wyłącznie identyfikatory. Moduł nie zna HTTP ani rejestru
danych; zależy tylko od ``GameState`` (warstwa ``core``).

Etykiety czysto wewnętrzne (krok maszyny stanów, otwarcie okna czasowego…) nie tworzą
wpisu, chyba że niosą widoczny skutek (``facts``) — wtedy trafiają do feedu jako
``misc/update``. Dzięki temu np. zbadanie technologii nie ginie, nawet jeśli commituje je
etykieta „krok".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.core.game_state import ActiveCombat, GameState, Phase, SystemState

# Kategorie wpisów (do filtrów w UI).
ActivityKind = Literal[
    "turn",  # tura, pas, zmiana fazy/rundy, mówca
    "strategy",  # karty strategii
    "tactical",  # aktywacja, ruch, produkcja, akcje komponentów
    "combat",  # walka, inwazja, space cannon
    "economy",  # transakcje, długi
    "scoring",  # cele, punkty
    "exploration",  # eksploracja planet
    "misc",  # skutki widoczne tylko w różnicy stanów
    "godmode",  # ręczne korekty operatora
]


class ActivityFact(BaseModel):
    """Skutek akcji wyliczony z różnicy stanów przed/po."""

    model_config = ConfigDict(extra="forbid")

    # "vp" | "tech" | "tech_lost" | "ability_used" | "planet_gained" | "planet_lost" | "tg"
    # oraz JAWNE karty/cele:
    # "action_card" (zagrana), "action_card_discarded" (odrzucona bez zagrania),
    # "agenda" (zużyta), "explore_card" (ujawniona),
    # "relic_fragment", "promissory_in_play", "objective_revealed", "secret_scored".
    # Zasoby/komponenty: "commodities", "cc" (value = pula), "hand" (value = ręka, tylko liczba),
    # "relic", "frontier_card", "leader", "breakthrough_unlocked", "strategy_card_gained".
    # Plansza: "units" (value = typ, delta = zmiana liczby), "system_token", "law_enacted",
    # "law_repealed", "attached", "objective_scored", "effect", "speaker", "custodians_removed",
    # "fracture_entered" (player_id = kto wprowadził The Fracture),
    # "eliminated" (player_id = wyeliminowany, value = frakcja, detail = nazwa gracza),
    # "winner", "battle_result" (player_id = zwycięzca walki, detail = "winner"/"draw",
    # delta = liczba rund), "rider" (value = karta, detail = przewidziany wynik agendy),
    # "tile_replaced" (value = pozycja, detail = "<stary kafel>><nowy kafel>"; Nova Seed),
    # "faction_token" / "faction_token_removed" (value = rodzaj żetonu, detail = planeta / space),
    # "moved" (ruch floty: player_id, value = typ jednostki, delta = liczba, detail = pozycja celu —
    # ruch sam się znosi w sumach, więc dopisujemy go osobno), "landed" (desant: value = typ,
    # delta = liczba, detail = id planety).
    # "area" (TYLKO we wpisie z użyciem bohatera: value = pozycja systemu, detail = "gain" / "loss"
    # jednostek gracza albo "token_removed" jego żetonu dowodzenia — miejsce efektu na planszy,
    # RULES.md 64.4; feed go nie wypisuje).
    # NOWY skutek gry => dopisz tu fakt i jego opis w ``describeActivity.tsx``.
    type: str
    # Czyj skutek; None dla zdarzeń talii/stołu bez jednego właściciela.
    player_id: str | None = None
    # Identyfikator techn./planety/karty (dla faktów nieliczbowych); None dla liczbowych.
    value: str | None = None
    # Dodatkowy kontekst (np. talia eksploracji); None, gdy zbędny.
    detail: str | None = None
    # Zmiana liczbowa (dla "vp"/"tg"); None dla identyfikatorów.
    delta: int | None = None


class Activity(BaseModel):
    """Jeden wpis feedu aktywności (powiązany z migawką historii)."""

    model_config = ConfigDict(extra="forbid")

    kind: ActivityKind
    action: str
    actor_id: str | None = None
    target_id: str | None = None
    subject: str | None = None
    detail: str | None = None
    round: int = 1
    phase: str = ""
    facts: list[ActivityFact] = Field(default_factory=list)


# Wynik rozbioru etykiety: (kind, action, actor, target, subject, detail).
_Parsed = tuple[ActivityKind, str, str | None, str | None, str | None, str | None]

# Etykiety bez własnej treści — wpis powstaje tylko, gdy zmieniły się fakty.
_QUIET_PREFIXES = (
    "tactical:step",
    "tactical:set-step",
    "turn:phase-step",
    "strategy:primary-step",
    "window:",
    "battle:afb",
    "battle:roll",
    "battle:assign",
    "invasion:bombard",
    "invasion:defense",
    "invasion:next",
    "space-cannon:pass",
    "space-cannon:assign",
    "cc:",
    "planet-exhaust:",
    "hand:",
    "decks:",
    "capacity:",
    "fleet-pool:",
    "production:skip-grant",
    "setup:secret",
    "setup:custodians",
    "setup:skip",
    "setup:reveal-objectives",
    "epilogue:",
    "exploration:finish",
)

_GODMODE_PREFIXES = (
    "god-mode-patch",
    "replace",
    "move-units",
    "edit:",
    "space:",
    "planet:",
    "player:",
)


def _is_quiet(label: str) -> bool:
    return any(label == p or label.startswith(p) for p in _QUIET_PREFIXES)


def _is_godmode(label: str) -> bool:
    return any(label == p or label.startswith(p) for p in _GODMODE_PREFIXES)


def _active(before: GameState | None, after: GameState) -> str | None:
    if before is not None and before.active_player_id is not None:
        return before.active_player_id
    return after.active_player_id


def _combat_pair(before: GameState | None, after: GameState) -> tuple[str | None, str | None]:
    combat = after.active_combat or (before.active_combat if before else None)
    if combat is None:
        return None, None
    return combat.attacker, combat.defender


def _parse_flow(
    label: str, parts: list[str], active: str | None, after: GameState
) -> _Parsed | None:
    """Tury, fazy, rundy, mówca, początek gry."""
    if label in ("initial", "game:new"):
        return "turn", "game.start", None, None, None, None
    if parts[0] == "player-undo" and len(parts) > 1:
        # Undo gracza (RULES.md 44.7): ``player-undo:<gracz>:<etykieta cofniętego kroku>``.
        return "turn", "turn.undo", parts[1], None, ":".join(parts[2:]) or None, None
    if label == "turn:end":
        return "turn", "turn.end", active, after.active_player_id, None, None
    if label == "turn:pass":
        return "turn", "turn.pass", active, after.active_player_id, None, None
    if label in ("turn:next-player", "turn:skip-player"):
        return "turn", "turn.next", active, after.active_player_id, None, None
    if label in ("phase:next", "phase:skip"):
        return "turn", "phase.start", None, None, after.phase.value, None
    if label == "round:next":
        return "turn", "round.start", None, None, str(after.round_number), None
    # Okna reakcji (RULES.md 54.11): prośba o czas jest anonimowa, długość okna ustawia host.
    if label == "reaction-wait":
        return "turn", "reactions.wait", None, None, None, None
    if parts[0] == "reaction-settings" and len(parts) > 2 and parts[1] == "window":
        return "turn", "reactions.window", None, None, parts[2], None
    if parts[0] == "reaction-settings" and len(parts) > 2 and parts[1] == "quick":
        # „Quick windows” (RULES.md 54.12) - ustawienie hosta jest jawne.
        return "turn", "reactions.quick", None, None, "on" if parts[2] == "1" else "off", None
    if parts[0] == "speaker" and len(parts) > 1:
        return "turn", "speaker.set", None, parts[1], None, None
    if parts[0] == "setup" and len(parts) == 2 and parts[1] not in ("custodians", "skip"):
        return "turn", "setup.faction", None, None, parts[1], None
    return None


def _parse_strategy(parts: list[str]) -> _Parsed | None:
    if parts[0] != "strategy" or len(parts) < 3:
        return None
    verb, pid = parts[1], parts[2]
    initiative = parts[3] if len(parts) > 3 else None
    if verb == "pick":
        return "strategy", "strategy.pick", pid, None, initiative, None
    if verb == "play":
        return "strategy", "strategy.play", pid, None, initiative, None
    if verb == "secondary":
        return "strategy", "strategy.secondary", pid, None, None, initiative
    return None


def _parse_tactical(parts: list[str], active: str | None) -> _Parsed | None:
    head = parts[0]
    arg = parts[1] if len(parts) > 1 else None
    if head == "tactical" and arg is not None:
        pos = parts[2] if len(parts) > 2 else None
        if arg in ("activate", "move", "produce"):
            return "tactical", f"tactical.{arg}", active, None, pos, None
        if arg == "end":
            return "tactical", "tactical.end", active, None, None, None
    if head == "capture" and len(parts) > 2:
        return "tactical", "tactical.capture", active, None, parts[2], parts[1]
    if head == "component-action":
        return "tactical", "tactical.component", active, None, arg, None
    if head == "tech-exhaust" and arg:
        return "tactical", "tech.exhaust", active, None, arg, None
    if head == "leader" and len(parts) > 2:
        return "tactical", "leader.state", active, None, arg, parts[2]
    if head == "component-use" and len(parts) > 2:
        # Lider / zdolność frakcji / przełom / technologia z oknem użycia (RULES.md 61.3, 62.9);
        # czwarta część = gracz, który użył komponentu (także nieaktywny - Quash).
        user = parts[3] if len(parts) > 3 and parts[3] else active
        return "tactical", "component.use", user, None, parts[2], arg
    if head == "promissory" and len(parts) > 2:
        # Zagrana notka (jawna od chwili zagrania; ręka zostaje ukryta) — RULES.md 61.2.
        return "tactical", "promissory.play", arg, None, parts[2], None
    return None


def _parse_combat(
    label: str, parts: list[str], active: str | None, before: GameState | None, after: GameState
) -> _Parsed | None:
    head = parts[0]
    att, dfn = _combat_pair(before, after)
    if label.startswith("battle:start"):
        where = parts[2] if len(parts) > 2 else "space"
        combat = after.active_combat
        position = combat.position if combat is not None else after.active_system
        return "combat", "combat.start", att or active, dfn, where, position
    if label == "battle:close":
        return "combat", "combat.end", att or active, dfn, None, None
    if parts[:2] == ["battle", "retreat-announce"] and len(parts) > 2:
        return "combat", "combat.retreat_announce", parts[2], None, None, None
    if parts[:2] == ["battle", "retreat"] and len(parts) > 3:
        return "combat", "combat.retreat", parts[2], None, parts[3], None
    if label == "invasion:begin":
        return "combat", "invasion.begin", active, None, after.active_system, None
    if label == "invasion:commit":
        return "combat", "invasion.commit", active, None, after.active_system, None
    if head == "space-cannon" and len(parts) > 2 and parts[1] == "fire":
        return "combat", "spacecannon.fire", parts[2], None, None, None
    return None


def _battle_where(combat: ActiveCombat) -> str:
    """Miejsce walki do opisu: id planety (walka naziemna) albo ``"space"``."""
    return combat.planet or "space"


def _battle_summary(combat: ActiveCombat) -> list[ActivityFact]:
    """Podsumowanie zakończonej walki: łączne straty stron z całego logu rund (``units`` < 0)."""
    totals: dict[str, dict[str, int]] = {}
    for entry in combat.log:
        for pid, by_type in dict(entry.get("losses") or {}).items():
            side = totals.setdefault(str(pid), {})
            for base_type, count in dict(by_type).items():
                side[str(base_type)] = side.get(str(base_type), 0) + int(count)
    # Wynik: zwycięzca (player_id; None przy remisie), "winner"/"draw" i liczba rund (delta).
    facts: list[ActivityFact] = [
        ActivityFact(
            type="battle_result", player_id=combat.winner,
            detail=combat.outcome or "draw", delta=combat.round,
        )
    ]
    for pid in (combat.attacker, combat.defender):
        for base_type, count in sorted(totals.get(pid, {}).items()):
            if count > 0:
                facts.append(
                    ActivityFact(type="units", player_id=pid, value=base_type, delta=-count)
                )
    return facts


def _combat_named(
    label: str, parts: list[str], before: GameState | None, after: GameState,
    facts: list[ActivityFact],
) -> Activity | None:
    """Wpisy walki/inwazji z NAZWĄ zdarzenia zamiast anonimowego „misc/update".

    Kroki techniczne walki (rzut, przypisanie strat, AFB, bombardowanie, Space Cannon Defense,
    Establish Control) są ciche, dopóki nic nie zmieniły; gdy niosą skutki (straty, przejęte
    planety), wpis dostaje nazwę bitwy/kroku. ``battle:close`` = podsumowanie całej walki.
    """
    base = {"round": after.round_number, "phase": after.phase.value}
    combat = (before.active_combat if before is not None else None) or after.active_combat
    invasion = (before.invasion if before is not None else None) or after.invasion
    head = parts[0]
    if label == "battle:close" and combat is not None:
        return Activity(
            kind="combat", action="combat.end", actor_id=combat.attacker,
            target_id=combat.defender, subject=_battle_where(combat), detail=combat.position,
            facts=[*_battle_summary(combat), *facts],
            **base,  # type: ignore[arg-type]
        )
    if not facts:
        return None
    if head == "battle" and combat is not None and len(parts) > 1 and parts[1] in (
        "afb", "assign", "roll"
    ):
        actor = parts[2] if parts[1] == "assign" and len(parts) > 2 else combat.attacker
        return Activity(
            kind="combat", action="combat.losses", actor_id=actor,
            target_id=combat.defender if actor == combat.attacker else combat.attacker,
            subject=_battle_where(combat), detail=combat.position, facts=facts,
            **base,  # type: ignore[arg-type]
        )
    if head == "invasion" and invasion is not None and len(parts) > 1:
        verb = parts[1]
        planet = parts[2] if len(parts) > 2 else None
        if verb in ("bombard", "bombard-assign"):
            action = "invasion.bombard"
        elif verb.startswith("defense"):
            action = "invasion.defense"
        elif verb == "next":
            action = "invasion.establish"
        else:
            return None
        return Activity(
            kind="combat", action=action, actor_id=invasion.attacker, subject=planet,
            detail=invasion.position, facts=facts,
            **base,  # type: ignore[arg-type]
        )
    if head == "space-cannon" and len(parts) > 2 and parts[1] == "assign":
        return Activity(
            kind="combat", action="spacecannon.losses", actor_id=parts[2],
            detail=after.active_system, facts=facts,
            **base,  # type: ignore[arg-type]
        )
    return None


_TABLE_STEPS = frozenset({"opened", "agreed", "closed"})


def _parse_economy_scoring(parts: list[str], active: str | None) -> _Parsed | None:
    head = parts[0]
    if head == "transaction" and len(parts) > 1:
        # ``transaction:<partner>[:<gracz>]`` - w fazie agendy stroną nie jest aktywny (47.5).
        actor = parts[2] if len(parts) > 2 else active
        return "economy", "transaction", actor, parts[1], None, None
    if head == "transaction-table" and len(parts) > 3 and parts[1] in _TABLE_STEPS:
        # Stół transakcji (RULES.md 47.1b): usiadł / umowa bez transakcji (dług, Trade) / wstał.
        # Kładzenie rzeczy i Ready to szczegóły negocjacji - poza feedem.
        return "economy", f"transaction.{parts[1]}", parts[2], parts[3], None, None
    if head == "debt" and len(parts) > 2 and "->" in parts[2]:
        left, right = parts[2].split("->", 1)
        action = "debt.give" if parts[1] == "give" else "debt.return"
        return "economy", action, left, right, None, None
    if label_is(parts, "status", "score") and len(parts) > 2:
        return "scoring", "objective.score", active, None, parts[2], None
    if label_is(parts, "status", "finish-scoring"):
        return "scoring", "scoring.finish", None, None, None, None
    if label_is(parts, "status", "redistribute") and len(parts) > 2:
        return "scoring", "scoring.redistribute", parts[2], None, None, None
    if head == "exploration" and len(parts) > 2:
        if parts[1] == "draw":
            return "exploration", "explore.draw", active, None, parts[2], None
        if parts[1] == "resolve":
            return "exploration", "explore.resolve", active, None, None, parts[2]
    return None


def _parse_agenda(parts: list[str], before: GameState | None, after: GameState) -> _Parsed | None:
    """Faza agendy (RULES.md 51): ujawnienie, głos, wstrzymanie, wynik mówcy, kolejny krok."""
    if parts[0] != "agenda" or len(parts) < 2:
        return None
    verb = parts[1]
    pid = parts[2] if len(parts) > 2 else None
    card = after.agenda.agenda_id if after.agenda is not None else None
    if verb == "reveal":
        return "scoring", "agenda.reveal", after.speaker_id, None, card, None
    if verb == "vote" and pid is not None and after.agenda is not None:
        cast = after.agenda.votes.get(pid)
        votes = str(cast.votes) if cast is not None else None
        return "scoring", "agenda.vote", pid, None, cast.outcome if cast else None, votes
    if verb == "abstain" and pid is not None:
        return "scoring", "agenda.abstain", pid, None, None, None
    if verb == "decide" and pid is not None:
        outcome = after.agenda.resolved_outcome if after.agenda is not None else None
        return "scoring", "agenda.decide", pid, None, outcome, None
    if verb == "discard":
        return "scoring", "agenda.discard", after.speaker_id, None, None, None
    if verb == "continue":
        step = after.agenda.step.value if after.agenda is not None else ""
        return "scoring", "agenda.next", after.speaker_id, None, step, None
    del before
    return None


def label_is(parts: list[str], head: str, verb: str) -> bool:
    return len(parts) > 1 and parts[0] == head and parts[1] == verb


def _parse(label: str, before: GameState | None, after: GameState) -> _Parsed | None:
    parts = label.split(":")
    active = _active(before, after)
    for parsed in (
        _parse_flow(label, parts, active, after),
        _parse_strategy(parts),
        _parse_tactical(parts, active),
        _parse_combat(label, parts, active, before, after),
        _parse_economy_scoring(parts, active),
        _parse_agenda(parts, before, after),
    ):
        if parsed is not None:
            return parsed
    return None


def _facts(before: GameState | None, after: GameState) -> list[ActivityFact]:
    """Skutki widoczne w różnicy stanów (VP, technologie, planety, TG)."""
    if before is None:
        return []
    facts: list[ActivityFact] = []
    for pid, new in after.players.items():
        old = before.players.get(pid)
        if old is None:
            continue
        if new.victory_points != old.victory_points:
            facts.append(
                ActivityFact(
                    type="vp",
                    player_id=pid,
                    delta=new.victory_points - old.victory_points,
                )
            )
        if new.trade_goods != old.trade_goods:
            facts.append(
                ActivityFact(type="tg", player_id=pid, delta=new.trade_goods - old.trade_goods)
            )
        for tech in new.technologies:
            if tech not in old.technologies:
                facts.append(ActivityFact(type="tech", player_id=pid, value=tech))
        for tech in old.technologies:
            if tech not in new.technologies:  # zwrot do talii (Genetic Memory, Divert Funding)
                facts.append(ActivityFact(type="tech_lost", player_id=pid, value=tech))
        for planet in new.controlled_planets:
            if planet not in old.controlled_planets:
                facts.append(ActivityFact(type="planet_gained", player_id=pid, value=planet))
        for planet in old.controlled_planets:
            if planet not in new.controlled_planets:
                facts.append(ActivityFact(type="planet_lost", player_id=pid, value=planet))
    facts.extend(_public_card_facts(before, after))
    facts.extend(_resource_facts(before, after))
    facts.extend(_unit_facts(before, after))
    facts.extend(_table_facts(before, after))
    facts.extend(_hero_area_facts(before, after, facts))
    return facts


def _is_hero_card(card: str | None) -> bool:
    """Karta bohatera (``<frakcja>hero``, ``xxchahero-te``) - po samym id, bez rejestru."""
    return bool(card) and "hero" in str(card)


def _hero_area_facts(
    before: GameState, after: GameState, facts: list[ActivityFact]
) -> list[ActivityFact]:
    """Gdzie na planszy zadziałał bohater (RULES.md 64.4): systemy, w których zmieniła się liczba
    jednostek graczy albo zniknął żeton dowodzenia - tylko we wpisie z purge / dołączeniem
    bohatera, żeby efekt animacji trafił w miejsce zdolności (Sol, Argent, L1Z1X, Saar...)."""
    used = any(
        (f.type == "leader" and f.detail == "purged" and _is_hero_card(f.value))
        or (f.type == "attached" and _is_hero_card(f.value))
        for f in facts
    )
    if not used:
        return []
    out: list[ActivityFact] = []
    for position in sorted(set(before.systems) | set(after.systems)):
        old, new = before.systems.get(position), after.systems.get(position)
        for pid in sorted(after.players):
            diff = _units_in(new, pid) - _units_in(old, pid)
            if diff:
                detail = "gain" if diff > 0 else "loss"
                out.append(ActivityFact(type="area", player_id=pid, value=position, detail=detail))
            old_tokens = old.command_tokens.count(pid) if old else 0
            new_tokens = new.command_tokens.count(pid) if new else 0
            if new_tokens < old_tokens:
                out.append(
                    ActivityFact(type="area", player_id=pid, value=position, detail="token_removed")
                )
    return out


def _units_in(system: SystemState | None, pid: str) -> int:
    """Liczba jednostek gracza w systemie (kosmos + planety)."""
    if system is None:
        return 0
    total = sum(system.space_units.get(pid, {}).values())
    for owners in system.planet_units.values():
        total += sum(owners.get(pid, {}).values())
    return total


def _resource_facts(before: GameState, after: GameState) -> list[ActivityFact]:
    """Zasoby i komponenty graczy: commodities, żetony dowodzenia, ręce (tylko LICZBY), liderzy.

    Ręce są prywatne, więc ujawniamy wyłącznie zmianę liczby kart (kto dobrał/oddał), nigdy
    ich zawartość. Spadek liczby kart akcji pomijamy, gdy ten gracz właśnie zagrał kartę
    (to pokazuje już fakt ``action_card``).
    """
    facts: list[ActivityFact] = []
    played = {f.player_id for f in _public_card_facts(before, after) if f.type == "action_card"}
    for pid, new in after.players.items():
        old = before.players.get(pid)
        if old is None:
            continue
        if new.commodities != old.commodities:
            facts.append(
                ActivityFact(
                    type="commodities", player_id=pid, delta=new.commodities - old.commodities
                )
            )
        for pool in ("tactical_cc", "fleet_cc", "strategic_cc"):
            diff = getattr(new, pool) - getattr(old, pool)
            if diff:
                facts.append(ActivityFact(type="cc", player_id=pid, value=pool, delta=diff))
        for hand in ("action_cards", "promissory_notes", "secret_objectives"):
            diff = len(getattr(new.private, hand)) - len(getattr(old.private, hand))
            if diff == 0 or (diff < 0 and hand == "action_cards" and pid in played):
                continue
            facts.append(ActivityFact(type="hand", player_id=pid, value=hand, delta=diff))
        for relic in new.relics:
            if relic not in old.relics:
                facts.append(
                    ActivityFact(type="relic", player_id=pid, value=relic, detail="gained")
                )
        for relic in old.relics:
            if relic not in new.relics:
                facts.append(ActivityFact(type="relic", player_id=pid, value=relic, detail="lost"))
        for card in new.frontier_cards:
            if card not in old.frontier_cards:
                facts.append(ActivityFact(type="frontier_card", player_id=pid, value=card))
        for leader, state in new.leader_states.items():
            if old.leader_states.get(leader) != state:
                facts.append(ActivityFact(type="leader", player_id=pid, value=leader, detail=state))
        if new.breakthrough_unlocked and not old.breakthrough_unlocked:
            facts.append(ActivityFact(type="breakthrough_unlocked", player_id=pid))
        for number in new.strategy_cards:
            if number not in old.strategy_cards:
                facts.append(
                    ActivityFact(type="strategy_card_gained", player_id=pid, value=str(number))
                )
    return facts


def _totals(state: GameState, pid: str) -> dict[str, int]:
    """Suma jednostek gracza na całej planszy wg typu bazowego (kosmos + planety)."""
    totals: dict[str, int] = {}
    for system in state.systems.values():
        for unit, count in system.space_units.get(pid, {}).items():
            totals[unit] = totals.get(unit, 0) + count
        for owners in system.planet_units.values():
            for unit, count in owners.get(pid, {}).items():
                totals[unit] = totals.get(unit, 0) + count
    return totals


def _unit_facts(before: GameState, after: GameState) -> list[ActivityFact]:
    """Zmiana liczby jednostek gracza na planszy (produkcja, straty). Ruch sam się znosi."""
    facts: list[ActivityFact] = []
    for pid in after.players:
        if pid not in before.players:
            continue
        old, new = _totals(before, pid), _totals(after, pid)
        for unit in sorted(set(old) | set(new)):
            diff = new.get(unit, 0) - old.get(unit, 0)
            if diff:
                facts.append(ActivityFact(type="units", player_id=pid, value=unit, delta=diff))
    return facts


def _movement_facts(
    action: str, subject: str | None, actor: str | None, before: GameState | None, after: GameState
) -> list[ActivityFact]:
    """Ruch i desant: jednostki zmieniają miejsce, więc sumy na planszy (``_unit_facts``) są równe.

    ``tactical.move`` (subject = system źródłowy): ubytek statków aktora w źródle ->
    ``moved`` z celem = aktywny system. ``invasion.commit``: przyrost jednostek aktora na
    planetach aktywnego systemu -> ``landed``.
    """
    if before is None or actor is None:
        return []
    facts: list[ActivityFact] = []
    if action == "tactical.move" and subject:
        old = before.systems.get(subject)
        new = after.systems.get(subject)
        old_ships = old.space_units.get(actor, {}) if old else {}
        new_ships = new.space_units.get(actor, {}) if new else {}
        for unit in sorted(old_ships):
            gone = old_ships[unit] - new_ships.get(unit, 0)
            if gone > 0:
                facts.append(
                    ActivityFact(
                        type="moved", player_id=actor, value=unit, delta=gone,
                        detail=after.active_system,
                    )
                )
    elif action == "invasion.commit":
        old = before.systems.get(after.active_system or "")
        new = after.systems.get(after.active_system or "")
        if old is not None and new is not None:
            for planet, owners in sorted(new.planet_units.items()):
                before_units = old.planet_units.get(planet, {}).get(actor, {})
                for unit, count in sorted(owners.get(actor, {}).items()):
                    gain = count - before_units.get(unit, 0)
                    if gain > 0:
                        facts.append(
                            ActivityFact(
                                type="landed", player_id=actor, value=unit, delta=gain,
                                detail=planet,
                            )
                        )
    return facts


def _table_facts(before: GameState, after: GameState) -> list[ActivityFact]:
    """Skutki wspólne dla stołu: prawa, przyczepione karty, cele publiczne, żetony, mówca."""
    facts: list[ActivityFact] = []
    for law, outcome in after.decks.agenda_laws.items():
        if before.decks.agenda_laws.get(law) != outcome:
            facts.append(ActivityFact(type="law_enacted", value=law, detail=outcome))
    for law in before.decks.agenda_laws:
        if law not in after.decks.agenda_laws:
            facts.append(ActivityFact(type="law_repealed", value=law))
    # Rider zagrany: przewidywanie jest jawne („predict aloud") - na co gracz postawił.
    old_effects = {e.id for e in before.active_effects}
    for effect in after.active_effects:
        card = effect.key.removeprefix("action_cards:")
        if (
            effect.id not in old_effects
            and effect.key.startswith("action_cards:")
            and "outcome" in effect.data
            and after.phase is Phase.AGENDA
        ):
            facts.append(
                ActivityFact(
                    type="rider", player_id=effect.owner, value=card,
                    detail=str(effect.data["outcome"]),
                )
            )
    for planet, cards in after.planet_attachments.items():
        old_cards = before.planet_attachments.get(planet, [])
        for card in cards:
            if card not in old_cards:
                facts.append(ActivityFact(type="attached", value=card, detail=planet))
    facts.extend(_faction_token_facts(before, after))
    for objective, scorers in after.objectives.scored.items():
        old_scorers = before.objectives.scored.get(objective, [])
        for pid in set(scorers):
            gained = scorers.count(pid) - old_scorers.count(pid)
            if gained > 0:
                facts.append(ActivityFact(type="objective_scored", player_id=pid, value=objective))
    for position, system in after.systems.items():
        old_system = before.systems.get(position)
        old_tokens = old_system.command_tokens if old_system else []
        for pid in system.command_tokens:
            if system.command_tokens.count(pid) > old_tokens.count(pid):
                facts.append(ActivityFact(type="system_token", player_id=pid, value=position))
    known = {effect.id for effect in before.active_effects}
    for effect in after.active_effects:
        if effect.id not in known:
            facts.append(
                ActivityFact(
                    type="effect", player_id=effect.owner, value=effect.key, detail=effect.scope
                )
            )
    for entry in after.ability_notes:  # zdolności zastosowane automatycznie (ability_notes)
        if int(entry.get("seq", 0)) > before.ability_note_seq:
            facts.append(
                ActivityFact(
                    type="ability_used", player_id=entry.get("player"),
                    value=entry.get("component"), detail=entry.get("detail") or None,
                )
            )
    if after.speaker_id != before.speaker_id and after.speaker_id:
        facts.append(ActivityFact(type="speaker", player_id=after.speaker_id))
    if after.custodians_removed and not before.custodians_removed:
        facts.append(ActivityFact(type="custodians_removed"))
    if after.fracture.in_play and not before.fracture.in_play:
        # The Fracture weszła do gry (rzut po przełomie, efekt karty, God-Mode) — RULES.md 64.
        facts.append(ActivityFact(type="fracture_entered", player_id=after.fracture.entered_by))
    for position, tile in sorted(after.replaced_tiles.items()):
        if before.replaced_tiles.get(position) != tile:  # Nova Seed: kafel -> supernowa
            old_system = before.systems.get(position)
            old_tile = old_system.system_id if old_system is not None else ""
            facts.append(
                ActivityFact(type="tile_replaced", value=position, detail=f"{old_tile}>{tile}")
            )
    if after.winner_id and not before.winner_id:
        facts.append(ActivityFact(type="winner", player_id=after.winner_id))
    known = {e.player_id for e in before.eliminated_players}
    for gone in after.eliminated_players:
        if gone.player_id not in known:  # R_elimination: gracz odpada z gry
            facts.append(
                ActivityFact(
                    type="eliminated", player_id=gone.player_id, value=gone.faction,
                    detail=gone.display_name or None,
                )
            )
    return facts


def _faction_token_facts(before: GameState, after: GameState) -> list[ActivityFact]:
    """Żetony frakcji położone / zdjęte (sleeper Titans, RULES.md 61.6): strefa = planeta/space."""
    def tokens(state: GameState) -> dict[tuple[str, str, str], str]:
        return {
            (position, zone, kind): owner
            for position, system in state.systems.items()
            for zone, kinds in system.faction_tokens.items()
            for kind, owner in kinds.items()
        }

    old, new = tokens(before), tokens(after)
    facts = [
        ActivityFact(type="faction_token", player_id=owner, value=key[2], detail=key[1])
        for key, owner in sorted(new.items()) if old.get(key) != owner
    ]
    facts += [
        ActivityFact(type="faction_token_removed", player_id=owner, value=key[2], detail=key[1])
        for key, owner in sorted(old.items()) if key not in new
    ]
    return facts


def _public_card_facts(before: GameState, after: GameState) -> list[ActivityFact]:
    """Karty i cele JAWNE, które zmieniły się między migawkami.

    Czytamy WYŁĄCZNIE miejsca publiczne (stosy odrzuconych, strefa gracza, odkryte cele,
    ujawniona karta eksploracji). Zawartość rąk (prywatna) nigdy nie trafia do wpisu — ręka
    służy tylko do ustalenia, KTO zagrał kartę, która właśnie leży odkryta na stosie.
    """
    facts: list[ActivityFact] = []

    # Karty akcji zagrane/odrzucone: nowe wpisy na stosie odrzuconych (leży odkryty).
    old_discard = list(before.decks.action_card_discard)
    new_discard = list(after.decks.action_card_discard)
    if len(new_discard) > len(old_discard) and new_discard[: len(old_discard)] == old_discard:
        added = new_discard[len(old_discard) :]
        # Odrzucenie bez zagrania (limit ręki, koszt celu) zostawia ślad ``last_action_discard``
        # (``card_draw``); zagranie idzie przez ``deck_piles`` bez tego śladu.
        trace = after.last_action_discard
        discarded = (
            trace is not None and trace != before.last_action_discard and trace.card in added
        )
        for card in added:
            owner = next(
                (
                    pid
                    for pid, old_player in before.players.items()
                    if pid in after.players
                    and card in old_player.private.action_cards
                    and card not in after.players[pid].private.action_cards
                ),
                None,
            )
            kind = "action_card_discarded" if discarded else "action_card"
            facts.append(ActivityFact(type=kind, player_id=owner, value=card))

    # Agendy zużyte (ujawnione na stole).
    for card in after.decks.agenda_discard[len(before.decks.agenda_discard) :]:
        facts.append(ActivityFact(type="agenda", value=card))

    # Karta eksploracji właśnie ujawniona (jawna dla wszystkich).
    exploring = after.exploration
    cur = exploring.current if exploring else None
    prev = before.exploration.current if before.exploration else None
    if exploring is not None and cur is not None and cur != prev:
        facts.append(
            ActivityFact(
                type="explore_card",
                player_id=exploring.player_id,
                value=cur.card_id,
                detail=cur.deck,
            )
        )

    for pid, new in after.players.items():
        old = before.players.get(pid)
        if old is None:
            continue
        for card in new.relic_fragments:
            if card not in old.relic_fragments:
                facts.append(ActivityFact(type="relic_fragment", player_id=pid, value=card))
        for card in new.promissory_notes_in_play:
            if card not in old.promissory_notes_in_play:
                facts.append(ActivityFact(type="promissory_in_play", player_id=pid, value=card))
        for card in new.scored_secrets:
            if card not in old.scored_secrets:
                facts.append(ActivityFact(type="secret_scored", player_id=pid, value=card))

    for objective in after.objectives.revealed:
        if objective not in before.objectives.revealed:
            facts.append(ActivityFact(type="objective_revealed", value=objective))
    return facts


def derive_activity(label: str, before: GameState | None, after: GameState) -> Activity | None:
    """Tłumaczy commit (etykieta + stany przed/po) na wpis feedu albo ``None``.

    ``None`` = zmiana czysto techniczna bez widocznego skutku (nie trafia do feedu).
    """
    facts = _facts(before, after)
    base = {"round": after.round_number, "phase": after.phase.value}

    if _is_godmode(label):
        # Korekta operatora: pokazujemy tylko, gdy realnie coś zmieniła u graczy.
        if not facts:
            return None
        return Activity(kind="godmode", action="godmode.edit", facts=facts, **base)  # type: ignore[arg-type]

    named = _combat_named(label, label.split(":"), before, after, facts)
    if named is not None:
        return named

    if _is_quiet(label):
        if not facts:
            return None
        return Activity(
            kind="misc",
            action="update",
            actor_id=_active(before, after),
            facts=facts,
            **base,  # type: ignore[arg-type]
        )

    parsed = _parse(label, before, after)
    if parsed is None:
        if not facts:
            return None
        return Activity(
            kind="misc",
            action="update",
            actor_id=_active(before, after),
            facts=facts,
            **base,  # type: ignore[arg-type]
        )
    kind, action, actor, target, subject, detail = parsed
    facts = [*facts, *_movement_facts(action, subject, actor, before, after)]
    if action == "strategy.secondary" and subject is None:
        # Numer karty (inicjatywa) siedzi w kontekście okna secondary — do nazwy w feedzie.
        window = (before.pending_window if before is not None else None) or after.pending_window
        if window is not None and window.context.get("initiative") is not None:
            subject = str(window.context["initiative"])
    if action == "explore.resolve" and after.exploration and after.exploration.log:
        # Rozstrzygnięta karta eksploracji jest jawna: id karty + skrót skutku z logu okna.
        last = after.exploration.log[-1]
        subject = str(last.get("cardId") or "") or subject
        detail = str(last.get("summary") or "") or detail
        actor = after.exploration.player_id
    return Activity(
        kind=kind,
        action=action,
        actor_id=actor,
        target_id=target,
        subject=subject,
        detail=detail,
        facts=facts,
        **base,  # type: ignore[arg-type]
    )
