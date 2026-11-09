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
) -> tuple[str, str] | None:
    """Para kolorów synergii z ODBLOKOWANEGO przełomu frakcji (R_synergy) albo None.

    Przełom zablokowany (``breakthrough_unlocked`` = False) nie daje synergii. Przełom bez
    pary kolorów (np. Nekro: ``NONE``) też nie. Synergia działa także, gdy przełom jest
    wyczerpany (nota R_breakthroughs: „the synergy ability always remains in effect").
    """
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


def _with_synergy(colors: list[str], pair: tuple[str, str] | None) -> list[str]:
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
        a, b = pair
        spare_a = max(0, have[a] - need[a])
        spare_b = max(0, have[b] - need[b])
        moved = min(spare_a, missing[b])
        missing[b] -= moved
        moved = min(spare_b, missing[a])
        missing[a] -= moved
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
    exhausted = set(player.exhausted_planets)
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


def aida_ready(state: GameState, player_id: str) -> bool:
    """Czy gracz może wyczerpać AI Development Algorithm (posiada i nie jest wyczerpana)."""
    player = state.players[player_id]
    return AIDA in player.technologies and AIDA not in player.exhausted_technologies


@dataclass(frozen=True)
class ResearchPlan:
    """Zweryfikowane badanie: co gracz dostaje i co wyczerpuje."""

    tech_id: str
    exhaust_planets: tuple[str, ...]
    exhaust_aida: bool


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
    use_aida = False
    for skip in skips:
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
    if left:
        text = ", ".join(f"{n}× {c.lower()}" for c, n in left.items())
        raise ValueError(f"Prerequisites not met for {tech.name}: missing {text}.")
    return ResearchPlan(tech_id, tuple(used_planets), use_aida)


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
    exhaust.exhaust_planets(state, player_id, plan.exhaust_planets)
    if plan.exhaust_aida:
        exhaust.exhaust_technology(state, player_id, AIDA)
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
        else:
            # Każda planeta pokrywa najwyżej 1 symbol (zachłannie po kolorach planety).
            left = Counter(missing)
            for colors in planets.values():
                color = next((c for c in colors if left[c] > 0), None)
                if color is not None:
                    left[color] -= 1
            remaining = sum(n for n in left.values() if n > 0)
            if UNIT_UPGRADE in tech.types and aida_ready(state, player_id):
                remaining -= 1
            status = "skippable" if remaining <= 0 else "locked"
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
