"""Badanie technologii (RULES.md 49, R_technology) — czyste funkcje nad ``GameState``.

Reguły (tirules R_technology, C_technology):
- Badać można technologię z SWOJEJ talii technologii: generyczną albo frakcyjną własnej
  frakcji. Frakcja z frakcyjnym ulepszeniem jednostki nie może badać jego wersji generycznej.
- Prerekwizyty: za każdy symbol koloru trzeba POSIADAĆ jedną technologię tego koloru.
  Ulepszenia jednostek nie mają koloru i nie spełniają prerekwizytów.
- Specjalność technologiczna planety: wyczerpanie GOTOWEJ, własnej planety ze specjalnością
  ignoruje JEDEN symbol pasującego koloru (jedna planeta = jeden symbol).
- AI Development Algorithm (``aida``, tekst z assetów): przy badaniu ulepszenia jednostki można
  wyczerpać kartę, by zignorować dowolny 1 prerekwizyt. ⚠️ Pierwszy „hook" technologii -
  docelowo przeniesiony do ``core/rules_hooks.py`` (E7).
- „Gain" technologii (bez badania) ignoruje prerekwizyty - ``gain_technology``.

Talia generyczna = technologie bez frakcji z talii typu ``technology`` w assetach, z JEDNĄ
wersją każdej karty: przy kilku wersjach (np. X-89 base / Ω / ΩΩ) wygrywa źródło o najwyższym
priorytecie (Codexy to oficjalne erraty — RULES.md 14). Zero list technologii w kodzie.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from src.core import exhaust, rules_hooks, triggers
from src.core.components import ComponentCategory, DeckDef
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.models import TechnologyDef
from src.core.planet_stats import planet_stats
from src.core.registry import StaticDataRegistry
from src.core.sources import source_rank

# Litera prerekwizytu w ``requirements`` → kolor technologii (konwencja danych AsyncTI4,
# sprawdzana testem względem kolorów technologii generycznych).
PREREQ_COLOR: dict[str, str] = {
    "G": "BIOTIC",
    "Y": "CYBERNETIC",
    "B": "PROPULSION",
    "R": "WARFARE",
}
COLORS: tuple[str, ...] = ("BIOTIC", "CYBERNETIC", "PROPULSION", "WARFARE")
UNIT_UPGRADE = "UNITUPGRADE"
# Technologia z możliwością zignorowania prerekwizytu ulepszenia jednostki (patrz moduł).
AIDA = "aida"
# Wartość w liście ``skips`` oznaczająca użycie AI Development Algorithm.
AIDA_SKIP = "aida"
_TECH_DECK_TYPE = "technology"


def _base_name(name: str) -> str:
    """Nazwa karty bez znaczników erraty („X-89 Bacterial Weapon ΩΩ" → „X-89 Bacterial Weapon")."""
    return name.replace("Ω", "").strip()


def generic_pool(registry: StaticDataRegistry) -> dict[str, TechnologyDef]:
    """Technologie generyczne (bez frakcji) z talii technologii, po jednej wersji karty."""
    deck_ids: set[str] = set()
    for deck in registry.catalog.all(ComponentCategory.DECK).values():
        if isinstance(deck, DeckDef) and deck.deck_type == _TECH_DECK_TYPE:
            deck_ids.update(deck.card_ids)
    best: dict[str, TechnologyDef] = {}
    for tech_id in sorted(deck_ids):
        tech = registry.technologies.get(tech_id)
        if tech is None or tech.faction:
            continue
        key = _base_name(tech.name)
        current = best.get(key)
        if current is None or source_rank(tech.source) < source_rank(current.source):
            best[key] = tech
    return {t.id: t for t in best.values()}


def faction_techs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> dict[str, TechnologyDef]:
    """Technologie frakcyjne gracza (lista frakcji z rejestru, z podmianami TE)."""
    player = state.players[player_id]
    faction = registry.factions.get(player.faction or "")
    if faction is None:
        return {}
    return {
        t: registry.technologies[t] for t in faction.faction_tech if t in registry.technologies
    }


def tech_pool(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> dict[str, TechnologyDef]:
    """Talia technologii gracza (generyczne + frakcyjne), bez generycznych ulepszeń
    zastąpionych frakcyjnymi - kolejność: generyczne, potem frakcyjne."""
    own = faction_techs(state, registry, player_id)
    replaced = {t.base_upgrade for t in own.values() if t.base_upgrade}
    pool = {k: v for k, v in generic_pool(registry).items() if k not in replaced}
    pool.update(own)
    return pool


def prerequisites(tech: TechnologyDef) -> Counter[str]:
    """Wymagane kolory (kolor → liczba symboli) z pola ``requirements``."""
    return Counter(
        PREREQ_COLOR[ch] for ch in (tech.requirements or "") if ch in PREREQ_COLOR
    )


def tech_color(tech: TechnologyDef) -> str | None:
    """Kolor technologii (BIOTIC/…) albo None dla ulepszeń jednostek / bez koloru."""
    return next((t for t in tech.types if t in COLORS), None)


def owned_colors(state: GameState, registry: StaticDataRegistry, player_id: str) -> Counter[str]:
    """Ile technologii każdego koloru gracz posiada (ulepszenia jednostek się nie liczą)."""
    counts: Counter[str] = Counter()
    for tech_id in state.players[player_id].technologies:
        tech = registry.technologies.get(tech_id)
        color = tech_color(tech) if tech is not None else None
        if color is not None:
            counts[color] += 1
    return counts


def synergy(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> tuple[str, ...] | None:
    """Kolory synergii (R_synergy): para z ODBLOKOWANEGO przełomu frakcji albo wszystkie cztery.

    Hook PERMIT ``technology.synergy_all`` (The Quantumcore: „SYNERGY for all technology types")
    daje synergię dla wszystkich czterech kolorów, niezależnie od przełomu.

    Przełom zablokowany (``breakthrough_unlocked`` = False) nie daje synergii. Przełom bez
    pary kolorów (np. Nekro: ``NONE``) też nie. Synergia działa także, gdy przełom jest
    wyczerpany (nota R_breakthroughs: „the synergy ability always remains in effect").
    """
    if rules_hooks.permits(rules_hooks.POINT_TECHNOLOGY_SYNERGY_ALL, state, player_id):
        return tuple(COLORS)
    player = state.players[player_id]
    if not player.breakthrough_unlocked:
        return None
    breakthrough = registry.breakthrough_for_faction(player.faction)
    if breakthrough is None:
        return None
    colors = [c for c in breakthrough.synergy if c in COLORS]
    if len(colors) != 2 or colors[0] == colors[1]:
        return None
    return colors[0], colors[1]


def _with_synergy(colors: list[str], pair: tuple[str, ...] | None) -> list[str]:
    """Kolory, jakie może „udawać" technologia / specjalność przy synergii (R_synergy)."""
    if pair is None or not any(c in pair for c in colors):
        return colors
    return list(dict.fromkeys([*colors, *pair]))


def missing_prerequisites(
    state: GameState, registry: StaticDataRegistry, player_id: str, tech: TechnologyDef
) -> Counter[str]:
    """Brakujące symbole prerekwizytów (przed użyciem specjalności planet).

    Z synergią (R_synergy) każda posiadana technologia jednego z dwóch kolorów pary może liczyć
    się jako dowolny kolor pary (każda osobno, ale tylko jako jeden kolor naraz) - nadwyżka
    jednego koloru pary pokrywa niedobór drugiego.
    """
    have = owned_colors(state, registry, player_id)
    need = prerequisites(tech)
    missing = Counter({c: n - have[c] for c, n in need.items() if n > have[c]})
    pair = synergy(state, registry, player_id)
    if pair is not None:
        # Nadwyżka każdego koloru synergii pokrywa niedobory pozostałych kolorów synergii.
        spare = {c: max(0, have[c] - need[c]) for c in pair}
        for short in pair:
            for donor in pair:
                if donor == short or missing[short] <= 0:
                    continue
                moved = min(spare[donor], missing[short])
                missing[short] -= moved
                spare[donor] -= moved
        missing = Counter({c: n for c, n in missing.items() if n > 0})
    return missing


def specialty_planets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> dict[str, list[str]]:
    """Gotowe planety gracza ze specjalnością → kolory, które mogą pominąć (np. ``BIOTIC``).

    Z synergią specjalność jednego koloru pary może pominąć symbol dowolnego koloru pary
    (R_synergy: „each technology speciality … as any color of that synergy").
    """
    player = state.players[player_id]
    # Hook PERMIT (Psychoarchaeology): specjalności działają także na wyczerpanych planetach.
    exhausted = (
        set()
        if rules_hooks.permits(rules_hooks.POINT_TECHNOLOGY_SPECIALTY_FREE, state, player_id)
        else set(player.exhausted_planets)
    )
    pair = synergy(state, registry, player_id)
    result: dict[str, list[str]] = {}
    for system in state.systems.values():
        for planet_id, owner in system.planet_owners.items():
            if owner != player_id or planet_id in exhausted:
                continue
            stats = planet_stats(state, registry, planet_id)
            if stats is not None and stats.tech_specialties:
                result[planet_id] = _with_synergy(
                    [s.upper() for s in stats.tech_specialties], pair
                )
    return result


def breakthrough_view(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> dict[str, Any] | None:
    """Przełom frakcji gracza dla UI: nazwa, para synergii i czy działa (None = brak przełomu)."""
    player = state.players[player_id]
    breakthrough = registry.breakthrough_for_faction(player.faction)
    if breakthrough is None:
        return None
    pair = [c for c in breakthrough.synergy if c in COLORS]
    return {
        "id": breakthrough.id,
        "name": breakthrough.name,
        "synergy": pair,
        "unlocked": player.breakthrough_unlocked,
        "exhausted": player.breakthrough_exhausted,
        "active": synergy(state, registry, player_id) is not None,
    }


def _remaining_after_skips(
    state: GameState,
    player_id: str,
    tech: TechnologyDef,
    missing: Counter[str],
    planets: dict[str, list[str]],
) -> int:
    """Ile symboli prerekwizytów zostanie po zachłannym użyciu skipów (planety + AIDA)."""
    left = Counter(missing)
    for colors in planets.values():
        color = next((c for c in colors if left[c] > 0), None)
        if color is not None:
            left[color] -= 1
    remaining = sum(n for n in left.values() if n > 0)
    if UNIT_UPGRADE in tech.types and aida_ready(state, player_id):
        remaining -= 1
    # Reliktowe „ignore 1 prerequisite" (Prophet's Tears): każdy gotowy relikt pokrywa 1 symbol.
    remaining -= len(ignore_prerequisite_relics(state, player_id))
    return remaining - free_prerequisite_ignores(state, player_id, tech)


def _after_free_ignores(
    state: GameState,
    player_id: str,
    tech: TechnologyDef,
    missing: Counter[str],
    planets: dict[str, list[str]],
) -> Counter[str]:
    """Brakujące symbole po darmowym ignorowaniu (Analytical) - dla UI drzewa.

    Ignorowane są najpierw symbole, których NIE pokryją gotowe planety ze specjalnością, żeby
    reszta dała się dobrać skipami w oknie badania (silnik i tak liczy ignorowanie po skipach).
    """
    free = free_prerequisite_ignores(state, player_id, tech)
    left = Counter({c: n for c, n in missing.items() if n > 0})
    if free <= 0:
        return left
    uncovered = Counter(left)
    for colors in planets.values():
        color = next((c for c in colors if uncovered[c] > 0), None)
        if color is not None:
            uncovered[color] -= 1
    order = [c for c in uncovered if uncovered[c] > 0] + list(left)
    for color in order:
        if free <= 0:
            break
        take = min(free, left[color], uncovered[color] if uncovered[color] > 0 else left[color])
        left[color] -= take
        free -= take
    return Counter({c: n for c, n in left.items() if n > 0})


def free_prerequisite_ignores(state: GameState, player_id: str, tech: TechnologyDef) -> int:
    """Ile brakujących symboli badanie ``tech`` ignoruje bez kosztu (Analytical, RULES.md 62.3).

    Hook MODIFY ``technology.free_prerequisite_ignores`` (ctx: ``unit_upgrade``). Stosowane po
    skipach (planety, AIDA, relikty) - nic nie kosztuje, więc gracz zawsze na tym zyskuje.
    """
    unit_upgrade = "true" if UNIT_UPGRADE in tech.types else "false"
    return max(
        0,
        rules_hooks.modify(
            rules_hooks.POINT_TECHNOLOGY_FREE_IGNORES, state, player_id, 0,
            {"unit_upgrade": unit_upgrade, "technology": tech.id},
        ),
    )


def researchable_techs(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    *,
    without: str | None = None,
) -> list[TechnologyDef]:
    """Technologie z talii gracza, które może zbadać TERAZ (bezpośrednio albo po skipach).

    To samo kryterium co statusy ``available`` / ``skippable`` w :func:`tree_view`. Z ``without``
    liczy tak, jakby gracz NIE posiadał technologii ``without`` (Divert Funding: zwrócona
    technologia nie spełnia prerekwizytów, C_action_cards). Nie mutuje ``state``.
    """
    sim = state
    if without is not None:
        player = state.players[player_id]
        trimmed = player.model_copy(
            update={"technologies": [t for t in player.technologies if t != without]}
        )
        sim = state.model_copy(update={"players": {**state.players, player_id: trimmed}})
    owned = set(sim.players[player_id].technologies)
    planets = specialty_planets(sim, registry, player_id)
    result: list[TechnologyDef] = []
    for tech in tech_pool(sim, registry, player_id).values():
        if tech.id in owned:
            continue
        missing = missing_prerequisites(sim, registry, player_id, tech)
        if not missing or _remaining_after_skips(sim, player_id, tech, missing, planets) <= 0:
            result.append(tech)
    return result


def aida_ready(state: GameState, player_id: str) -> bool:
    """Czy gracz może wyczerpać AI Development Algorithm (posiada i nie jest wyczerpana)."""
    player = state.players[player_id]
    return AIDA in player.technologies and AIDA not in player.exhausted_technologies


RELIC_SKIP_PREFIX = "relic:"  # skip z reliktu: ``relic:<id>`` (np. ``relic:prophetstears``)


def ignore_prerequisite_relics(state: GameState, player_id: str) -> list[str]:
    """Gotowe relikty gracza, które pozwalają zignorować 1 prerekwizyt przy badaniu.

    Hook FORBID punktu ``technology.ignore_prerequisite`` (zbiór id reliktów).
    """
    return sorted(
        rules_hooks.forbidden(rules_hooks.POINT_TECHNOLOGY_IGNORE_PREREQUISITE, state, player_id)
    )


@dataclass(frozen=True)
class ResearchPlan:
    """Zweryfikowane badanie: co gracz dostaje i co wyczerpuje."""

    tech_id: str
    exhaust_planets: tuple[str, ...]
    exhaust_aida: bool
    exhaust_relics: tuple[str, ...] = ()


def plan_research(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    tech_id: str,
    skips: list[str],
) -> ResearchPlan:
    """Sprawdza legalność badania i wylicza, co trzeba wyczerpać (bez mutacji stanu).

    ``skips`` = planety ze specjalnością do wyczerpania (każda ignoruje 1 symbol swojego
    koloru) i opcjonalnie ``"aida"`` (dowolny 1 symbol, tylko dla ulepszeń jednostek).
    Zbędny skip (niczego nie pokrywa) jest błędem - gracz nie wyczerpuje planet na darmo.

    Raises:
        ValueError: Technologia spoza talii gracza / już posiadana, zły skip albo
            niespełnione prerekwizyty.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    pool = tech_pool(state, registry, player_id)
    tech = pool.get(tech_id)
    if tech is None:
        if tech_id in registry.technologies:
            raise ValueError("This technology is not in your technology deck.")
        raise ValueError(f"Unknown technology: {tech_id}")
    if tech_id in player.technologies:
        raise ValueError(f"You already own {tech.name}.")
    if len(set(skips)) != len(skips):
        raise ValueError("The same skip was selected twice.")

    missing = missing_prerequisites(state, registry, player_id, tech)
    planets = specialty_planets(state, registry, player_id)
    used_planets: list[str] = []
    used_relics: list[str] = []
    use_aida = False
    for skip in skips:
        if skip.startswith(RELIC_SKIP_PREFIX):
            relic_id = skip[len(RELIC_SKIP_PREFIX):]
            if relic_id not in ignore_prerequisite_relics(state, player_id):
                raise ValueError("That relic cannot ignore a prerequisite right now.")
            color = max(missing, key=lambda c: missing[c], default=None)
            if color is None or missing[color] <= 0:
                raise ValueError("The relic would ignore nothing.")
            missing[color] -= 1
            used_relics.append(relic_id)
            continue
        if skip == AIDA_SKIP:
            if UNIT_UPGRADE not in tech.types:
                raise ValueError("AI Development Algorithm only helps with unit upgrades.")
            if not aida_ready(state, player_id):
                raise ValueError("You cannot exhaust AI Development Algorithm.")
            color = max(missing, key=lambda c: missing[c], default=None)
            if color is None or missing[color] <= 0:
                raise ValueError("AI Development Algorithm would ignore nothing.")
            missing[color] -= 1
            use_aida = True
            continue
        if skip not in planets:
            raise ValueError(
                f"{skip} is not a ready planet of yours with a technology specialty."
            )
        color = next((c for c in planets[skip] if missing[c] > 0), None)
        if color is None:
            raise ValueError(
                f"{skip}'s technology specialty does not match a missing prerequisite."
            )
        missing[color] -= 1
        used_planets.append(skip)
    left = {c: n for c, n in missing.items() if n > 0}
    for _ in range(free_prerequisite_ignores(state, player_id, tech)):
        color = max(left, key=lambda c: left[c], default=None)
        if color is None:
            break
        left[color] -= 1
        if left[color] <= 0:
            del left[color]
    if left:
        text = ", ".join(f"{n}× {c.lower()}" for c, n in left.items())
        raise ValueError(f"Prerequisites not met for {tech.name}: missing {text}.")
    return ResearchPlan(tech_id, tuple(used_planets), use_aida, tuple(used_relics))


def grant_technology(state: GameState, player_id: str, tech_id: str) -> None:
    """Dodaje technologię graczowi — JEDYNE miejsce zmiany ``PlayerState.technologies``.

    RULES.md 43.1a: badanie i „gain" przechodzą tędy, więc hook „gdy zdobywasz technologię"
    (np. dodatkowa technologia, zwrot kosztu) dopisujemy tu raz. Idempotentne (nie dubluje).
    Mutuje przekazany ``state`` (KLON roboczy wołającego); legalność sprawdza wołający.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if tech_id not in player.technologies:
        tech_ctx = {"player": player_id, "technology": tech_id}
        triggers.fire(
            state,
            GameEvent.TECHNOLOGY_GAINED,
            Moment.WHEN,
            subject=player_id,
            ctx=tech_ctx,
        )
        player.technologies = [*player.technologies, tech_id]
        triggers.fire(
            state,
            GameEvent.TECHNOLOGY_GAINED,
            Moment.AFTER,
            subject=player_id,
            ctx=tech_ctx,
        )


def return_technology(state: GameState, player_id: str, tech_id: str) -> None:
    """Zwraca technologię do talii gracza (Divert Funding) - JEDYNE miejsce jej utraty.

    Karta wraca do talii, więc zniknie też z wyczerpanych: ponowne zdobycie daje ją gotową
    (C_action_cards, Divert Funding: „gain it readied"). Mutuje KLON roboczy wołającego.

    Raises:
        ValueError: Nieznany gracz albo gracz nie posiada tej technologii.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if tech_id not in player.technologies:
        raise ValueError(f"You do not own the technology {tech_id}.")
    player.technologies = [t for t in player.technologies if t != tech_id]
    exhaust.ready_technology(state, player_id, tech_id)


def _unit_upgrade_flag(tech_id: str) -> str:
    """``"true"`` dla ulepszenia jednostki (technologia bez koloru) - filtr ``where`` hooków."""
    registry = rules_hooks.bound_registry()
    tech = registry.technologies.get(tech_id) if registry is not None else None
    return "true" if tech is not None and not tech.types else "false"


def apply_research(state: GameState, player_id: str, plan: ResearchPlan) -> None:
    """Dodaje technologię i wyczerpuje planety/AIDA z planu (mutuje KLON stanu)."""
    research_ctx = {
        "player": player_id,
        "technology": plan.tech_id,
        "unit_upgrade": _unit_upgrade_flag(plan.tech_id),
    }
    triggers.fire(
        state,
        GameEvent.TECHNOLOGY_RESEARCH,
        Moment.WHEN,
        subject=player_id,
        ctx=research_ctx,
    )
    grant_technology(state, player_id, plan.tech_id)
    # Psychoarchaeology: użycie specjalności nie wyczerpuje planet (hook PERMIT).
    if not rules_hooks.permits(rules_hooks.POINT_TECHNOLOGY_SPECIALTY_FREE, state, player_id):
        exhaust.exhaust_planets(state, player_id, plan.exhaust_planets)
    if plan.exhaust_aida:
        exhaust.exhaust_technology(state, player_id, AIDA)
    for relic_id in plan.exhaust_relics:
        exhaust.exhaust_relic(state, player_id, relic_id)
    # Ślad dla okien „after <gracz> researches a technology" (Research Agreement, RULES.md 62.3);
    # zeruje go ``action_budget.clear_reaction_traces`` przy następnej akcji.
    state.last_research = [*state.last_research, {"player": player_id, "technology": plan.tech_id}]
    triggers.fire(
        state,
        GameEvent.TECHNOLOGY_RESEARCH,
        Moment.AFTER,
        subject=player_id,
        ctx=research_ctx,
    )


def research(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    tech_id: str,
    skips: list[str] | None = None,
) -> GameState:
    """Czyste badanie technologii: walidacja + nowy stan (bez kosztu zasobów - to karta)."""
    plan = plan_research(state, registry, player_id, tech_id, list(skips or []))
    new_state = state.clone()
    apply_research(new_state, player_id, plan)
    return new_state


def gain_technology(state: GameState, registry: StaticDataRegistry, player_id: str,
                    tech_id: str) -> GameState:
    """„Gain" technologii: z talii gracza, IGNORUJĄC prerekwizyty (R_technology)."""
    if tech_id not in tech_pool(state, registry, player_id):
        raise ValueError("This technology is not in your technology deck.")
    if tech_id in state.players[player_id].technologies:
        raise ValueError("You already own this technology.")
    new_state = state.clone()
    grant_technology(new_state, player_id, tech_id)
    return new_state


def tree_view(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Talia technologii gracza jako dane dla drzewa w UI (kolumny = kolory + ulepszenia).

    Status kafla: ``owned`` / ``exhausted`` (posiadana i wyczerpana) / ``available`` (spełnia
    prerekwizyty bez skipów) / ``skippable`` (brakuje symboli, które pokryją gotowe planety ze
    specjalnością lub AIDA) / ``locked``. ``missing`` = brakujące kolory przed skipami.
    """
    player = state.players[player_id]
    planets = specialty_planets(state, registry, player_id)
    rows: list[dict[str, Any]] = []
    for tech in tech_pool(state, registry, player_id).values():
        missing = missing_prerequisites(state, registry, player_id, tech)
        if tech.id in player.technologies:
            status = "exhausted" if tech.id in player.exhausted_technologies else "owned"
        elif not missing:
            status = "available"
        elif not (shown := _after_free_ignores(state, player_id, tech, missing, planets)):
            status = "available"  # darmowe ignorowanie pokrywa wszystko (Analytical)
            missing = shown
        else:
            # Każda planeta pokrywa najwyżej 1 symbol (zachłannie po kolorach planety).
            remaining = _remaining_after_skips(state, player_id, tech, missing, planets)
            status = "skippable" if remaining <= 0 else "locked"
            missing = shown
        rows.append(
            {
                "id": tech.id,
                "name": tech.name,
                "color": tech_color(tech),
                "unitUpgrade": UNIT_UPGRADE in tech.types,
                "faction": tech.faction,
                "baseUpgrade": tech.base_upgrade,
                "prerequisites": [
                    PREREQ_COLOR[ch] for ch in (tech.requirements or "") if ch in PREREQ_COLOR
                ],
                "missing": dict(missing),
                "status": status,
            }
        )
    return rows


# ------------------------------------------------- koszt badania: zniżki i płatność planetą

# Efekt zniżki kosztu NASTĘPNEGO płatnego badania gracza (data: ``amount``); Doctor Sucaban.
RESEARCH_DISCOUNT = "technology:research_discount"


def research_discount(state: GameState, player_id: str) -> int:
    """Suma zniżek kosztu najbliższego płatnego badania gracza (efekty ``RESEARCH_DISCOUNT``)."""
    return sum(
        int(e.data.get("amount", 0)) for e in state.active_effects
        if e.key == RESEARCH_DISCOUNT and e.owner == player_id
    )


def consume_research_discount(state: GameState, player_id: str) -> None:
    """Zniżka zużyta przy zapłacie badania (MUTUJE klon)."""
    from src.core import active_effects  # lokalnie: unika cyklu importów

    active_effects.remove_by_key(state, RESEARCH_DISCOUNT, owner=player_id)


def specialty_payment_planets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> dict[str, list[str]]:
    """Gotowe planety, którymi wolno ZAPŁACIĆ za badanie z karty Technology (Specialist Compounds).

    Hook PERMIT ``technology.specialty_pays``; kolory = WŁASNE specjalności planety (bez
    rozszerzenia synergią - F_jol_nar). Pusty słownik, gdy gracz nie ma tej zdolności.
    """
    if not rules_hooks.permits(rules_hooks.POINT_TECHNOLOGY_SPECIALTY_PAYS, state, player_id):
        return {}
    exhausted = set(state.players[player_id].exhausted_planets)
    result: dict[str, list[str]] = {}
    for system in state.systems.values():
        for planet_id, owner in system.planet_owners.items():
            if owner != player_id or planet_id in exhausted:
                continue
            stats = planet_stats(state, registry, planet_id)
            if stats is not None and stats.tech_specialties:
                result[planet_id] = [s.upper() for s in stats.tech_specialties]
    return result


def validate_specialty_payment(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    plan: ResearchPlan,
    planet_id: str,
) -> None:
    """Sprawdza płatność planetą ze specjalnością (Specialist Compounds, RULES.md 62.3).

    Raises:
        ValueError: Brak zdolności, ulepszenie jednostki, zły kolor albo planeta użyta jako skip.
    """
    planets = specialty_payment_planets(state, registry, player_id)
    if planet_id not in planets:
        raise ValueError("That planet cannot pay for this research with its technology specialty.")
    tech = registry.technologies.get(plan.tech_id)
    if tech is None or UNIT_UPGRADE in tech.types:
        raise ValueError("A technology specialty cannot pay for a unit upgrade.")
    if tech_color(tech) not in planets[planet_id]:
        raise ValueError("The planet's technology specialty must match the technology's color.")
    if planet_id in plan.exhaust_planets:
        raise ValueError("The same planet cannot both ignore a prerequisite and pay.")
