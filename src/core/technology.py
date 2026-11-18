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
    have = owned_colors(state, registry, player_id) + virtual_prerequisites(state, player_id)
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


def virtual_prerequisites(state: GameState, player_id: str) -> Counter[str]:
    """Symbole prerekwizytów z kart, które je „spełniają” (Brother Omar: 1 zielony, RULES 62.10)."""
    point = rules_hooks.POINT_TECHNOLOGY_VIRTUAL_PREREQUISITES
    if not rules_hooks.hooks_at(point, state, player_id):
        return Counter()
    found: Counter[str] = Counter()
    for color in COLORS:
        extra = rules_hooks.modify(point, state, player_id, 0, {"color": color})
        if extra > 0:
            found[color] += extra
    return found


INFANTRY_SKIP_PREFIX = "infantry:"  # ``infantry:<pozycja>|<strefa>`` - zwrot piechoty (Omar)


def infantry_skip_allowed(state: GameState, player_id: str, tech_id: str) -> bool:
    """Czy zwrot 1 piechoty zignoruje prerekwizyty ``tech_id`` (``technology.infantry_skip``)."""
    return rules_hooks.permits(
        rules_hooks.POINT_TECHNOLOGY_INFANTRY_SKIP, state, player_id, {"technology": tech_id}
    )


def infantry_locations(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """Miejsca z piechotą gracza na planszy ``(pozycja, strefa)`` (strefa = planeta/``space``)."""
    found: list[tuple[str, str]] = []
    for position, system in sorted(state.systems.items()):
        if system.space_units.get(player_id, {}).get("infantry", 0) > 0:
            found.append((position, "space"))
        for planet, by_player in sorted(system.planet_units.items()):
            if by_player.get(player_id, {}).get("infantry", 0) > 0:
                found.append((position, planet))
    return found


def _infantry_skip_ready(state: GameState, player_id: str, tech: TechnologyDef) -> bool:
    return infantry_skip_allowed(state, player_id, tech.id) and bool(
        infantry_locations(state, player_id)
    )


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
    if _infantry_skip_ready(state, player_id, tech):
        return 0  # zwrot piechoty ignoruje wszystkie prerekwizyty (Brother Omar)
    registry = rules_hooks.bound_registry()
    if registry is not None and any(
        _can_afford(state, registry, player_id, cost)
        for cost in paid_ignore_cards(state, player_id).values()
    ):
        return 0  # Inheritance Systems: wyczerpanie + osobna zapłata ignoruje wszystko
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


PAID_SKIP_PREFIX = "paid:"  # ``paid:<karta>|<planeta,planeta>|<tg>`` (Inheritance Systems)


def paid_ignore_cards(state: GameState, player_id: str) -> dict[str, int]:
    """``{karta: koszt}`` gotowych kart gracza, które za wyczerpanie i OSOBNĄ zapłatę ignorują
    wszystkie prerekwizyty (FORBID ``technology.paid_ignore_all``, wartości ``"<karta>:<koszt>"``).
    """
    player = state.players[player_id]
    found: dict[str, int] = {}
    for value in rules_hooks.forbidden(
        rules_hooks.POINT_TECHNOLOGY_PAID_IGNORE_ALL, state, player_id
    ):
        card, _, cost = str(value).partition(":")
        if card in player.technologies and card not in player.exhausted_technologies:
            found[card] = int(cost or 0)
    return dict(sorted(found.items()))


def _can_afford(state: GameState, registry: StaticDataRegistry, player_id: str, cost: int) -> bool:
    from src.core import payment  # lokalnie: payment -> relic_planets -> ... (bez cyklu)

    values = payment.ready_planet_values(state, registry, player_id, "resources")
    total = sum(values.values()) + state.players[player_id].trade_goods * payment.trade_good_value(
        state, player_id
    )
    return total >= cost


def parse_paid_skip(skip: str) -> tuple[str, list[str], int]:
    """``paid:<karta>|<planety>|<tg>`` -> ``(karta, planety, tg)``.

    Raises:
        ValueError: Zły format skipu.
    """
    card, _, rest = skip[len(PAID_SKIP_PREFIX):].partition("|")
    planets_raw, _, tg_raw = rest.partition("|")
    if not card or (tg_raw and not tg_raw.isdigit()):
        raise ValueError("Paid prerequisite skip must be 'paid:<card>|<planets>|<trade goods>'.")
    planets = [p for p in planets_raw.split(",") if p]
    return card, planets, int(tg_raw or 0)


@dataclass(frozen=True)
class ResearchPlan:
    """Zweryfikowane badanie: co gracz dostaje i co wyczerpuje."""

    tech_id: str
    exhaust_planets: tuple[str, ...]
    exhaust_aida: bool
    exhaust_relics: tuple[str, ...] = ()
    # Ile symboli zignorowano bez kosztu (Analytical) - notatka w feedzie przy badaniu.
    free_ignores: int = 0
    # Piechota zwracana do rezerwy za zignorowanie prerekwizytów ``(pozycja, strefa)`` (Omar).
    return_infantry: tuple[str, str] | None = None
    # Karta wyczerpana za zignorowanie wszystkich prerekwizytów i jej OSOBNA zapłata
    # ``(karta, planety, tg)`` (Inheritance Systems, RULES.md 62.12).
    paid_ignore: tuple[str, tuple[str, ...], int] | None = None

    @property
    def reserved_planets(self) -> tuple[str, ...]:
        """Planety zużyte przez plan (specjalność, osobna zapłata) - nie płacą kosztu badania."""
        paid = self.paid_ignore[1] if self.paid_ignore is not None else ()
        return (*self.exhaust_planets, *paid)


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
    return_infantry: tuple[str, str] | None = None
    paid_ignore: tuple[str, tuple[str, ...], int] | None = None
    for skip in skips:
        if skip.startswith(PAID_SKIP_PREFIX):
            paid_ignore = _plan_paid_ignore(state, registry, player_id, skip, paid_ignore, missing)
            missing = Counter()
            continue
        if skip.startswith(INFANTRY_SKIP_PREFIX):
            position, _, zone = skip[len(INFANTRY_SKIP_PREFIX):].partition("|")
            if not infantry_skip_allowed(state, player_id, tech_id):
                raise ValueError(
                    "Returning infantry ignores prerequisites only of a technology another "
                    "player owns."
                )
            if (position, zone) not in infantry_locations(state, player_id):
                raise ValueError("You have no infantry there.")
            if return_infantry is not None or not +missing:
                raise ValueError("Returning infantry would ignore nothing.")
            missing = Counter()
            return_infantry = (position, zone)
            continue
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
    ignored = 0
    for _ in range(free_prerequisite_ignores(state, player_id, tech)):
        color = max(left, key=lambda c: left[c], default=None)
        if color is None:
            break
        left[color] -= 1
        ignored += 1
        if left[color] <= 0:
            del left[color]
    if left:
        text = ", ".join(f"{n}× {c.lower()}" for c, n in left.items())
        raise ValueError(f"Prerequisites not met for {tech.name}: missing {text}.")
    if paid_ignore is not None and set(paid_ignore[1]) & set(used_planets):
        raise ValueError("A planet exhausted for its technology specialty cannot also pay.")
    return ResearchPlan(
        tech_id, tuple(used_planets), use_aida, tuple(used_relics), free_ignores=ignored,
        return_infantry=return_infantry, paid_ignore=paid_ignore,
    )


def _plan_paid_ignore(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    skip: str,
    current: tuple[str, tuple[str, ...], int] | None,
    missing: Counter[str],
) -> tuple[str, tuple[str, ...], int]:
    """Walidacja skipu ``paid:`` (Inheritance Systems): karta gotowa, zapłata pokrywa koszt."""
    from src.core import payment  # lokalnie: payment -> relic_planets -> ... (bez cyklu)

    card, planets, trade_goods = parse_paid_skip(skip)
    cards = paid_ignore_cards(state, player_id)
    if card not in cards:
        raise ValueError("That card cannot ignore prerequisites right now.")
    if current is not None or not +missing:
        raise ValueError("Ignoring all prerequisites would ignore nothing.")
    paid = payment.validate_payment(state, registry, player_id, "resources", planets, trade_goods)
    if paid < cards[card]:
        raise ValueError(f"Spend {cards[card]} resources to ignore the prerequisites "
                         f"(you chose {paid}).")
    return card, tuple(planets), trade_goods


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


def plan_with_skips(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    tech_id: str,
    skips: list[str],
) -> ResearchPlan | None:
    """Plan badania z NAJMNIEJSZYM podzbiorem skipów, które gracz zgodził się wyczerpać.

    Dla badań poza oknem karty Technology (agendy, Technology Rider - C_agendas,
    C_action_cards): gracz wskazuje planety ze specjalnością / AI Development Algorithm raz,
    a silnik przypisuje je do technologii. ``None`` - nie da się zbadać nawet ze wszystkimi.
    """
    from itertools import combinations

    tech = registry.technologies.get(tech_id)
    # Więcej skipów niż symboli prerekwizytów nic nie da (zbędny skip = błąd planu).
    most = min(len(skips), sum(prerequisites(tech).values()) if tech is not None else 0)
    for size in range(most + 1):
        for subset in combinations(skips, size):
            try:
                return plan_research(state, registry, player_id, tech_id, list(subset))
            except ValueError:
                continue
    return None


def skip_choices(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str]]:
    """``(wartość, opis)`` skipów gracza: gotowe planety ze specjalnością i AIDA (jeśli gotowe)."""
    found: list[tuple[str, str]] = []
    for planet, colors in specialty_planets(state, registry, player_id).items():
        info = registry.planets.get(planet)
        name = info.name if info is not None and info.name else planet
        found.append((planet, f"{name} ({'/'.join(c.lower() for c in colors)})"))
    if aida_ready(state, player_id):
        found.append((AIDA_SKIP, "AI Development Algorithm (unit upgrades)"))
    if rules_hooks.hooks_at(rules_hooks.POINT_TECHNOLOGY_INFANTRY_SKIP, state, player_id):
        for position, zone in infantry_locations(state, player_id):
            info = registry.planets.get(zone)
            where = info.name if info is not None and info.name else f"space ({position})"
            found.append((
                f"{INFANTRY_SKIP_PREFIX}{position}|{zone}",
                f"Return 1 infantry from {where} (a technology another player owns)",
            ))
    return found


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
    if plan.free_ignores:
        from src.core import ability_notes  # lokalnie: unika cyklu importów

        tech = rules_hooks.bound_registry().technologies.get(plan.tech_id)
        name = tech.name if tech is not None else plan.tech_id
        ability_notes.note_point(
            state, player_id, rules_hooks.POINT_TECHNOLOGY_FREE_IGNORES,
            f"ignored {plan.free_ignores} prerequisite(s) of {name}",
        )
    # Psychoarchaeology: użycie specjalności nie wyczerpuje planet (hook PERMIT).
    if not rules_hooks.permits(rules_hooks.POINT_TECHNOLOGY_SPECIALTY_FREE, state, player_id):
        exhaust.exhaust_planets(state, player_id, plan.exhaust_planets)
    if plan.exhaust_aida:
        exhaust.exhaust_technology(state, player_id, AIDA)
    if plan.return_infantry is not None:
        from src.core import ability_notes, unit_ops  # lokalnie: unika cyklu importów

        position, zone = plan.return_infantry
        unit_ops.remove_units(state, state.systems[position], zone, player_id, "infantry", 1)
        ability_notes.note_point(
            state, player_id, rules_hooks.POINT_TECHNOLOGY_INFANTRY_SKIP,
            "returned 1 infantry to ignore prerequisites",
        )
    for relic_id in plan.exhaust_relics:
        exhaust.exhaust_relic(state, player_id, relic_id)
    if plan.paid_ignore is not None:
        from src.core import ability_notes, payment  # lokalnie: unika cyklu importów

        card, planets, trade_goods = plan.paid_ignore
        exhaust.exhaust_technology(state, player_id, card)
        payment.apply_payment(state, player_id, list(planets), trade_goods)
        ability_notes.note(state, player_id, f"technologies:{card}",
                           "ignored all prerequisites")
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
                # Brother Omar: zwrot piechoty ignoruje prerekwizyty tej technologii (RULES 62.10).
                "infantrySkip": status == "skippable" and _infantry_skip_ready(
                    state, player_id, tech
                ),
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
    if planet_id in plan.reserved_planets:
        raise ValueError("The same planet cannot both ignore a prerequisite and pay.")


def pay_research(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    cost: int,
    planets: list[str],
    trade_goods: int,
    *,
    skip_planets: tuple[str, ...] = (),
    trade_goods_only: bool = False,
) -> int:
    """JEDYNE miejsce zapłaty zasobami za badanie (RULES.md 43.1a; karta Technology, Reveal
    Prototype, Enigmatic Device, Focused Research). MUTUJE klon. Zwraca koszt po zniżkach.

    ``trade_goods_only`` (Focused Research: „Spend 4 trade goods”): płaci się wyłącznie TG, w
    kwocie kosztu po zniżce. TG wydane jak zasoby to wydawanie zasobów (R_trade_goods: „spend a
    trade good as if it were one resource”) - decyzja użytkownika 2026-11-12.

    Odejmuje zniżkę (Doctor Sucaban przed zapłatą), płaci i zostawia ślad
    ``GameState.last_research_payment`` - okno „when a player spends resources to research” dla
    zdolności użytych zaraz po zapłacie (zwrot, RULES.md 62.3).

    Raises:
        ValueError: Planeta skipu płaci jednocześnie albo za mało zasobów.
    """
    from src.core import payment  # lokalnie: payment -> relic_planets -> ... (bez cyklu)

    cost = max(0, cost - research_discount(state, player_id))
    consume_research_discount(state, player_id)
    if cost <= 0:
        return 0
    if trade_goods_only:
        planets, trade_goods = [], cost
    overlap = set(planets) & set(skip_planets)
    if overlap:
        raise ValueError(
            "A planet exhausted for its technology specialty cannot also pay resources: "
            + ", ".join(sorted(overlap))
        )
    paid = payment.validate_payment(state, registry, player_id, "resources", planets, trade_goods)
    if paid < cost:
        raise ValueError(f"Spend at least {cost} resources (you chose {paid}).")
    payment.apply_payment(state, player_id, planets, trade_goods)
    state.last_research_payment = {
        "player": player_id, "cost": cost, "planets": list(planets),
        "trade_goods": trade_goods, "reduced": False,
    }
    return cost
