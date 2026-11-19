"""SetupService (core) — walidacja i normalizacja konfiguracji nowej gry.

Czysta logika domenowa setupu wydzielona z routera (R7–R11), żeby endpoint
pozostał cienki, a reguły były testowalne bez HTTP. Moduł należy do warstwy
``core/`` — nie importuje FastAPI ani niczego z ``api/``.

**Decyzja architektoniczna (kierunek zależności).** Projekt wymusza zależności
tylko w dół: ``api/`` → ``core/``, nigdy odwrotnie (steering + design, sekcja
„Architecture"). Design pokazuje sygnaturę ``resolve_players(players:
list[NewGamePlayer], ...)``, ale ``NewGamePlayer`` mieszka w ``api/schemas.py`` —
zaimportowanie go tutaj stworzyłoby zakazany import ``core → api``. Zamiast tego
definiujemy lekki protokół strukturalny ``PlayerSetupInput`` opisujący pola, których
``resolve_players`` potrzebuje. ``NewGamePlayer`` (model Pydantic) spełnia ten
protokół strukturalnie (duck typing), więc router przekazuje ``request.players``
bez żadnej konwersji ani importu w dół. To realizuje intencję designu (``core``
konsumuje DTO setupu), nie łamiąc warstw.

Wszystkie wyszukiwania frakcji/technologii idą przez ``StaticDataRegistry`` (R11.5);
zbiór poziomów trudności i limity są WSTRZYKIWANE (z zadania 5 / ``engine_config``),
nie hardkodowane (⚠️ ZAŁOŻENIE, docs/RULES.md 36). Pierwszy wykryty problem →
``ValueError`` z komunikatem wskazującym pole i gracza (R11.4). Żaden ``GameState``
nie powstaje przed pełną walidacją.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from src.core import faction_support
from src.core.faction_setup import resolve_starting_tech
from src.core.game_state import ControlType
from src.core.models import FactionDef
from src.core.registry import StaticDataRegistry

# Maksymalna długość nazwy wyświetlanej po usunięciu białych znaków (R7.2 / R1.4).
# To NIE jest reguła TI4, tylko ograniczenie kontraktu modelu gracza z wymagań
# (1..50 znaków). Dolna granica (1) jest egzekwowana pośrednio: nazwa pusta po
# strip → nazwa automatyczna (R7.3), więc nie istnieje rozwiązany gracz z nazwą 0.
_NAME_MAX_LEN = 50


@runtime_checkable
class PlayerSetupInput(Protocol):
    """Strukturalny kontrakt pojedynczego gracza na wejściu setupu.

    Opisuje tylko pola, których potrzebuje ``resolve_players``. ``NewGamePlayer``
    z ``api/schemas.py`` spełnia go strukturalnie, dzięki czemu ``core`` nie musi
    importować DTO z ``api`` (patrz nota architektoniczna w nagłówku modułu).
    """

    faction_id: str | None
    player_id: str | None
    name: str | None
    color: str | None
    control_type: str
    difficulty: str | None
    personality: str | None
    home_position: str | None
    starting_tech: list[str] | None


@dataclass(frozen=True)
class ResolvedPlayer:
    """Znormalizowana konfiguracja jednego gracza po walidacji.

    Niezmienna (frozen) migawka wyniku ``resolve_players``: wszystkie pola są już
    rozwiązane i poprawne (nazwa niepusta, kolor ze zbioru, frakcja grywalna,
    trudność spójna z typem sterowania, technologie startowe o właściwej liczności).
    Router iteruje po tych obiektach, budując ``PlayerState`` bez dalszej walidacji.
    """

    player_id: str
    display_name: str
    color: str
    faction_id: str
    control_type: ControlType
    difficulty: str | None
    personality: str | None
    starting_tech: list[str] | None
    home_position: str | None


def resolve_players(
    players: Sequence[PlayerSetupInput],
    registry: StaticDataRegistry,
    *,
    available_colors: Sequence[str],
    max_players: int,
    valid_difficulties: frozenset[str],
    valid_personalities: frozenset[str] = frozenset(),
    rng: random.Random | None = None,
) -> list[ResolvedPlayer]:
    """Waliduje i normalizuje graczy w jednym przebiegu (R7, R8, R10, R11).

    Kolejność walidacji (wg design.md, sekcja 6):
    1. zakres liczby graczy (R11.3),
    2. nazwy — strip, długość 1..50, auto dla pustych, bez duplikatów
       case-insensitive (R7.2–R7.5),
    3. kolory — ze zbioru ``available_colors``, bez duplikatów (R7.6–R7.8),
    4. frakcje — grywalne w registry, bez duplikatów, losowy dobór nieprzypisanych
       (R8.5–R8.8),
    5. typ sterowania + trudność — BOT wymaga trudności ze zbioru, HUMAN ją czyści
       (R10.3–R10.6),
    6. technologie startowe — delegowane do ``resolve_starting_tech`` (R9/R11.6).

    ``home_position`` NIE jest tu walidowany względem mapy (istnienie/zajętość) —
    to robi router w zadaniu 9, gdzie dostępny jest grid (R14.4). Tu jest tylko
    przenoszony do wyniku bez zmian.

    Args:
        players: Gracze z żądania (strukturalnie zgodni z ``PlayerSetupInput``).
        registry: Rejestr statycznych danych — jedyne źródło frakcji/technologii
            (R11.5).
        available_colors: Zbiór dozwolonych kolorów graczy (R7.7 — liczność
            ≥ ``max_players``). Wstrzykiwany, nie hardkodowany.
        max_players: Maksymalna liczba graczy wspierana przez grę (R11.3).
        valid_difficulties: Dozwolony zbiór poziomów trudności bota (R1.8/R10.2) —
            wstrzykiwany z konfiguracji silnika (zadanie 5), nie hardkodowany.
        rng: Opcjonalne, seedowalne źródło losowości do deterministycznego doboru
            frakcji w testach. Gdy ``None`` — używany jest moduł ``random``.

    Returns:
        Lista ``ResolvedPlayer`` w kolejności wejściowej (= kolejność zasiadania).

    Raises:
        ValueError: Pierwszy wykryty problem; komunikat wskazuje pole i gracza
            (R11.4). Żaden ``GameState`` nie powstaje przed pełną walidacją.
    """
    # Seedowalne źródło losowości: wstrzyknięty ``rng`` (testy) lub nowa instancja
    # ``random.Random`` (entropia systemowa). Jednolity typ upraszcza adnotacje.
    chooser = rng if rng is not None else random.Random()

    # 1. Zakres liczby graczy (R11.3). Walidujemy PRZED czymkolwiek innym — pusta
    #    lub przeładowana lista nie ma sensu dalej normalizować.
    count = len(players)
    if count < 1 or count > max_players:
        raise ValueError(
            f"Invalid number of players: {count}. Allowed range: "
            f"1..{max_players}."
        )

    # Identyfikatory graczy (do komunikatów błędów wskazujących gracza — R11.4).
    # Pusty/brakujący player_id → auto "p{n}" (zgodnie z routerem).
    player_ids = [
        (p.player_id or f"p{index + 1}") for index, p in enumerate(players)
    ]

    display_names = _resolve_names(players, player_ids)
    colors = _resolve_colors(players, player_ids, available_colors)
    faction_ids = _resolve_factions(players, player_ids, registry, chooser)

    resolved: list[ResolvedPlayer] = []
    for index, player in enumerate(players):
        pid = player_ids[index]
        faction = registry.factions[faction_ids[index]]
        control_type = _resolve_control_type(player, pid)
        difficulty = _resolve_difficulty(
            player, pid, control_type, valid_difficulties, chooser
        )
        personality = _resolve_personality(
            player, pid, control_type, valid_personalities, chooser
        )
        starting_tech = _resolve_tech(player, pid, faction)
        resolved.append(
            ResolvedPlayer(
                player_id=pid,
                display_name=display_names[index],
                color=colors[index],
                faction_id=faction_ids[index],
                control_type=control_type,
                difficulty=difficulty,
                personality=personality,
                starting_tech=starting_tech,
                home_position=player.home_position,
            )
        )
    return resolved


# --- Nazwy (R7.2–R7.5) -------------------------------------------------


def _resolve_names(
    players: Sequence[PlayerSetupInput], player_ids: Sequence[str]
) -> list[str]:
    """Normalizuje nazwy: strip, 1..50, auto dla pustych, bez duplikatów.

    - Nazwa po ``strip()`` dłuższa niż 50 znaków → ``ValueError`` (R7.4).
    - Pusta/same-białe → nazwa automatyczna unikalna względem pozostałych (R7.3).
    - Dwie równe niepuste nazwy (po strip, bez rozróżniania wielkości liter) →
      ``ValueError`` (R7.5).

    Nazwy automatyczne są nadawane PO zebraniu nazw jawnych, tak by nie kolidowały
    z żadną jawną ani z innymi automatycznymi.
    """
    stripped: list[str] = []
    for index, player in enumerate(players):
        raw = (player.name or "").strip()
        if len(raw) > _NAME_MAX_LEN:
            raise ValueError(
                f"Player name {player_ids[index]!r} is too long "
                f"({len(raw)} characters after trimming whitespace; max {_NAME_MAX_LEN})."
            )
        stripped.append(raw)

    # Duplikaty wśród NIEPUSTYCH nazw (case-insensitive, po strip) — R7.5.
    seen: dict[str, int] = {}
    for index, name in enumerate(stripped):
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            raise ValueError(
                f"Duplicate player name {name!r} (players "
                f"{player_ids[seen[key]]!r} and {player_ids[index]!r})."
            )
        seen[key] = index

    # Auto-nazwy dla pustych, unikalne względem WSZYSTKICH (jawnych i wygenerowanych).
    taken = {name.casefold() for name in stripped if name}
    result = list(stripped)
    for index, name in enumerate(result):
        if name:
            continue
        auto = _next_auto_name(player_ids[index], taken)
        result[index] = auto
        taken.add(auto.casefold())
    return result


def _next_auto_name(player_id: str, taken: set[str]) -> str:
    """Generuje automatyczną nazwę unikalną względem ``taken`` (R7.3).

    Bazą jest ``"Gracz {player_id}"``; przy kolizji dokłada sufiks liczbowy.
    """
    base = f"Player {player_id}"
    if base.casefold() not in taken:
        return base
    suffix = 2
    while f"{base} ({suffix})".casefold() in taken:
        suffix += 1
    return f"{base} ({suffix})"


# --- Kolory (R7.6–R7.8) ------------------------------------------------


def _resolve_colors(
    players: Sequence[PlayerSetupInput],
    player_ids: Sequence[str],
    available_colors: Sequence[str],
) -> list[str]:
    """Przydziela kolory: ze zbioru dozwolonego, bez duplikatów.

    - Kolor podany jawnie, ale spoza ``available_colors`` → ``ValueError`` (R7.8).
    - Ten sam kolor u dwóch graczy → ``ValueError`` (R7.6).
    - Brak koloru (``None``) → pierwszy wolny kolor ze zbioru wg kolejności (auto).
    """
    allowed = list(available_colors)
    allowed_set = set(allowed)

    assigned: list[str | None] = [None] * len(players)
    used: dict[str, int] = {}

    # 1) Kolory jawne — walidacja zbioru i duplikatów.
    for index, player in enumerate(players):
        color = player.color
        if color is None:
            continue
        if color not in allowed_set:
            raise ValueError(
                f"Invalid color {color!r} of player {player_ids[index]!r}. "
                f"Allowed: {sorted(allowed_set)}."
            )
        if color in used:
            raise ValueError(
                f"Duplicate color {color!r} (players "
                f"{player_ids[used[color]]!r} and {player_ids[index]!r})."
            )
        used[color] = index
        assigned[index] = color

    # 2) Auto-przydział wolnych kolorów dla graczy bez jawnego koloru.
    free = [c for c in allowed if c not in used]
    free_iter = iter(free)
    for index, color in enumerate(assigned):
        if color is not None:
            continue
        try:
            picked = next(free_iter)
        except StopIteration as exc:  # pragma: no cover — chroni R7.7
            raise ValueError(
                f"No free color for player {player_ids[index]!r} "
                f"(color pool exhausted)."
            ) from exc
        assigned[index] = picked
        used[picked] = index

    return [c for c in assigned if c is not None]


# --- Frakcje (R8.5–R8.8) -----------------------------------------------


def _resolve_factions(
    players: Sequence[PlayerSetupInput],
    player_ids: Sequence[str],
    registry: StaticDataRegistry,
    chooser: random.Random,
) -> list[str]:
    """Rozwiązuje frakcje: grywalne, bez duplikatów, losowy dobór nieprzypisanych.

    - Frakcja jawna nieznana lub niegrywalna w registry → ``ValueError`` (R8.7).
    - Ten sam identyfikator frakcji u dwóch graczy → ``ValueError`` (R8.8).
    - Dwa warianty tej samej RODZINY frakcji (np. keleresm + keleresx) →
      ``ValueError``: Keleres to jedna frakcja z trzema wariantami mentora,
      więc w jednej grze może wystąpić najwyżej jeden (RULES.md 10,
      docs/rules_tirules/F_keleres.md).
    - Brak frakcji (``None``) → losowy dobór spośród grywalnych, jeszcze
      nieprzypisanych (R8.5). Pula bierze najwyżej jednego przedstawiciela
      z każdej rodziny, więc losowanie nie da dwóch wariantów Keleres.
      Pusta pula przy losowaniu → ``ValueError`` (R8.6). Losowanie bierze najpierw
      frakcje zrobione (``core/faction_support``), potem pozostałe.

    Lookupy idą wyłącznie przez ``registry.factions`` (R11.5).
    """
    assigned: list[str | None] = [None] * len(players)
    used: dict[str, int] = {}
    # Rodziny frakcji (klucz ``registry.faction_family``) już zajęte — jawnie
    # lub przez losowanie. Pozwala egzekwować „max 1 wariant z rodziny" (Keleres).
    used_families: dict[str, int] = {}

    # 1) Frakcje jawne — walidacja grywalności oraz duplikatów (id i rodziny).
    for index, player in enumerate(players):
        fid = player.faction_id
        if fid is None:
            continue
        faction = registry.factions.get(fid)
        if faction is None:
            raise ValueError(
                f"Unknown faction {fid!r} of player {player_ids[index]!r}."
            )
        if not faction.is_playable:
            raise ValueError(
                f"Faction {fid!r} of player {player_ids[index]!r} is not playable "
                f"(system placeholder)."
            )
        if fid in used:
            raise ValueError(
                f"Duplicate faction {fid!r} (players "
                f"{player_ids[used[fid]]!r} and {player_ids[index]!r})."
            )
        family = registry.faction_family(faction)
        if family in used_families:
            raise ValueError(
                f"Duplicate faction variant {fid!r} (players "
                f"{player_ids[used_families[family]]!r} and {player_ids[index]!r}): "
                f"only one variant of faction family {family!r} is allowed."
            )
        used[fid] = index
        used_families[family] = index
        assigned[index] = fid

    # 2) Losowy dobór dla slotów bez jawnej frakcji (R8.5) spośród nieprzypisanych.
    #    Pula wyklucza całe zajęte rodziny i daje jednego przedstawiciela na rodzinę.
    pool = _playable_faction_pool(registry, exclude_families=set(used_families))
    chooser.shuffle(pool)
    # Najpierw frakcje z pełną implementacją (decyzja użytkownika 2026-11-18: losowa frakcja
    # - zwłaszcza botów - z tych zrobionych); gdy ich zabraknie, reszta grywalnych.
    pool.sort(key=lambda fid: not faction_support.is_implemented(fid))
    pool_iter = iter(pool)
    for index, fid in enumerate(assigned):
        if fid is not None:
            continue
        try:
            picked = next(pool_iter)
        except StopIteration as exc:  # R8.6 — brak dostępnych frakcji
            raise ValueError(
                f"No playable factions available for random assignment for "
                f"player {player_ids[index]!r}."
            ) from exc
        assigned[index] = picked

    return [f for f in assigned if f is not None]


def _playable_faction_pool(
    registry: StaticDataRegistry, *, exclude_families: set[str]
) -> list[str]:
    """Pula grywalnych frakcji z registry, po jednym wariancie na rodzinę.

    Warianty tej samej rodziny (Keleres: keleresm/keleresx/keleresa) dzielą
    klucz ``registry.faction_family``; do losowania wpuszczamy tylko jednego
    przedstawiciela każdej rodziny, by losowy dobór nie przydzielił dwóm graczom
    dwóch wariantów tej samej frakcji (RULES.md 10). Pomijamy też rodziny już
    zajęte przez jawny wybór.

    Deterministyczny wybór przedstawiciela (najmniejsze id w rodzinie) i końcowe
    sortowanie po id dają powtarzalną kolejność bazową, na której działa seedowalny
    ``shuffle`` (powtarzalność testów przy danym seedzie).
    """
    representatives: dict[str, str] = {}
    for fid, faction in registry.factions.items():
        if not faction.is_playable:
            continue
        family = registry.faction_family(faction)
        if family in exclude_families:
            continue
        current = representatives.get(family)
        if current is None or fid < current:
            representatives[family] = fid
    return sorted(representatives.values())


# --- Typ sterowania + trudność (R10.3–R10.6) ---------------------------


def _resolve_control_type(
    player: PlayerSetupInput, player_id: str
) -> ControlType:
    """Waliduje i zwraca typ sterowania gracza (R10.1/R10.6).

    Wartość spoza zbioru {HUMAN, BOT} → ``ValueError`` wskazujący gracza.
    Brak typu (pusty napis) traktowany jak brak wyboru → ``ValueError`` (R10.6).
    """
    raw = (player.control_type or "").strip()
    if not raw:
        raise ValueError(
            f"Player {player_id!r} has no control type selected "
            f"(control_type)."
        )
    try:
        return ControlType(raw)
    except ValueError as exc:
        allowed = ", ".join(ct.value for ct in ControlType)
        raise ValueError(
            f"Invalid control type {raw!r} of player {player_id!r}. "
            f"Allowed: {allowed}."
        ) from exc


def _resolve_difficulty(
    player: PlayerSetupInput,
    player_id: str,
    control_type: ControlType,
    valid_difficulties: frozenset[str],
    chooser: random.Random,
) -> str | None:
    """Rozwiązuje poziom trudności zależnie od typu sterowania (R10.3–R10.5).

    - HUMAN → trudność czyszczona do ``None`` (R10.4), niezależnie od wejścia.
    - BOT bez wybranej trudności → losowa ze zbioru ``valid_difficulties``.
    - BOT z wartością spoza zbioru → ``ValueError`` (R10.5).
    """
    if control_type is ControlType.HUMAN:
        return None  # R10.4 — człowiek nie ma poziomu trudności

    difficulty = player.difficulty
    if difficulty is None and valid_difficulties:
        return chooser.choice(sorted(valid_difficulties))
    if difficulty is None or difficulty not in valid_difficulties:
        raise ValueError(
            f"Invalid difficulty level {difficulty!r} for bot "
            f"{player_id!r}. Allowed: {sorted(valid_difficulties)}."
        )
    return difficulty


def _resolve_personality(
    player: PlayerSetupInput,
    player_id: str,
    control_type: ControlType,
    valid_personalities: frozenset[str],
    chooser: random.Random,
) -> str | None:
    """Rozwiązuje osobowość bota: HUMAN → ``None``; BOT bez wyboru → losowa.

    Wartość spoza ``valid_personalities`` → ``ValueError``. Gdy zbiór jest pusty
    (brak konfiguracji), osobowość pozostaje ``None``.
    """
    if control_type is ControlType.HUMAN:
        return None

    personality = player.personality
    if personality is None:
        if not valid_personalities:
            return None
        return chooser.choice(sorted(valid_personalities))
    if personality not in valid_personalities:
        raise ValueError(
            f"Invalid personality {personality!r} for bot "
            f"{player_id!r}. Allowed: {sorted(valid_personalities)}."
        )
    return personality


# --- Technologie startowe (R9 / R11.6) ---------------------------------


def _resolve_tech(
    player: PlayerSetupInput, player_id: str, faction: FactionDef
) -> list[str] | None:
    """Rozwiązuje technologie startowe, delegując do ``resolve_starting_tech``.

    ``resolve_starting_tech`` egzekwuje właściwą liczność i przynależność do opcji
    frakcji (R9.2/R9.5) lub zwraca stałą listę. Komunikat błędu wzbogacamy o gracza
    (R11.4/R11.6), zachowując oryginalną przyczynę.

    Zwraca ``None``, gdy frakcja nie ma technologii startowych (pusta lista) — żeby
    ``ResolvedPlayer.starting_tech`` odróżniało „brak" od „puste przez wybór".
    """
    try:
        tech = resolve_starting_tech(faction, player.starting_tech)
    except ValueError as exc:
        raise ValueError(f"Player {player_id!r}: {exc}") from exc
    return tech or None
