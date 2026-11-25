"""Okna reakcji o stałej długości + auto-pas silnika (RULES.md 54.11).

Wspólna mechanika pauzy ochronnej (``core/reaction_pause.py``, 54.10) i okna Sabotage
(``core/card_hold.py``, 53.6):

* **Stała długość.** Okno trwa zawsze ``GameState.reaction_window_seconds`` (ustawia host) plus
  ewentualne „More time”. Pasy go NIE skracają - długość to jedyny sygnał widoczny dla innych,
  więc nie może zależeć od treści rąk (43.4).
* **Auto-pas.** Silnik zna ręce, więc przy otwarciu okna pasuje za uprawnionych, którzy nie mają
  karty reakcji zagrywalnej teraz, za botów i za graczy z „Skip all reactions”. Lista pasów jest
  prywatna (``visibility.redact_reaction_windows``).
* **„More time”.** Każdy uprawniony (także ten, za którego silnik spasował) może raz na okno
  przedłużyć je o ``WAIT_EXTENSION_SECONDS`` - prośba nic nie mówi o ręce.

Moduł jest czysty: czas (``now``) podaje wołający, funkcje zwracają nowy stan albo mutują
przekazany klon (opisane w docstringach).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Protocol

from src.core import reaction_prefs
from src.core.components import ComponentCategory
from src.core.game_state import ControlType, GameState
from src.core.registry import StaticDataRegistry

DEFAULT_SECONDS = 5
MIN_SECONDS = 2
MAX_SECONDS = 30
WAIT_EXTENSION_SECONDS = 10
MAX_JITTER_SECONDS = 2.0


class TimedWindow(Protocol):
    """Wspólny kształt ``ReactionPause`` i ``HeldPlay`` (pola czasu i pasów)."""

    opened_at: float
    seconds: float
    eligible: list[str]
    passed: list[str]
    extended_by: list[str]
    involved: list[str]


def window_seconds(state: GameState) -> int:
    """Długość nowego okna reakcji w s (ustawienie hosta, przycięte do zakresu)."""
    return max(MIN_SECONDS, min(MAX_SECONDS, int(state.reaction_window_seconds)))


def configure(state: GameState, seconds: int) -> GameState:
    """Host ustawia długość okien reakcji (nowy stan; trwające okno zachowuje swoją długość).

    Raises:
        ValueError: Wartość poza zakresem ``MIN_SECONDS``..``MAX_SECONDS``.
    """
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise ValueError(
            f"Reaction window must be between {MIN_SECONDS} and {MAX_SECONDS} seconds."
        )
    new_state = state.clone()
    new_state.reaction_window_seconds = int(seconds)
    return new_state


def expired(window: TimedWindow, now: float) -> bool:
    """Czy minął stały czas okna (z przedłużeniami)."""
    return now - window.opened_at >= window.seconds


def has_playable_reaction(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    skip_moments: frozenset[str] = frozenset(),
) -> bool:
    """Czy gracz może TERAZ zareagować (prywatne - tylko dla silnika): karta reakcji z ręki,
    notka-reakcja z ręki albo komponent frakcji z oknem użycia (Quash, Instinct Training -
    RULES.md 62.9).

    ``skip_moments``: momenty, na które gracz z góry spasował („No whens” / „No afters”, 54.12) -
    karta pasująca WYŁĄCZNIE do okien z tymi momentami się nie liczy.
    """
    # lokalnie: moduły kart i komponentów importują moduły okien
    from src.core import action_cards, promissory_play, reaction_cards

    prefs = state.players[player_id].private.reaction_prefs

    def card_counts(card_id: str) -> bool:
        if not skip_moments:
            return True
        windows = reaction_cards.matching_windows(state, registry, player_id, card_id)
        return any(w.moment.value not in skip_moments for w in windows)

    def note_counts(template: str) -> bool:
        if not skip_moments:
            return True
        moments = promissory_play.reaction_moments(registry, template)
        return any(m not in skip_moments for m in moments)

    # Wyciszone karty (54.12) nie liczą się jako „ma kartę” - auto-pas jak bez karty.
    if any(
        entry["reaction"] and entry["playable"]
        and not reaction_prefs.is_card_muted(
            prefs, card_name(registry, ComponentCategory.ACTION_CARD, entry["card_id"])
        )
        and card_counts(entry["card_id"])
        for entry in action_cards.playability(state, registry, player_id)
    ):
        return True
    # ⚠️ ZAŁOŻENIE (54.12 d): komponent frakcji z oknem użycia liczy się mimo połowicznej
    # deklaracji (moment komponentu nie jest tu znany) - gracz zostanie zapytany.
    if window_component_users(state, registry, [player_id], respect_mutes=True):
        return True
    return any(
        row["reaction"] and row["playable"]
        and not reaction_prefs.is_card_muted(
            prefs, card_name(registry, ComponentCategory.PROMISSORY_NOTE, row["template"])
        )
        and note_counts(row["template"])
        for row in promissory_play.playability(state, registry, player_id)
    )


def card_name(registry: StaticDataRegistry, category: ComponentCategory, card_id: str) -> str:
    """Nazwa karty z assetów (klucz wyciszenia - wszystkie kopie, np. ``sabo1``..``sabo4``)."""
    card = registry.catalog.get(category, card_id)
    return (card.name if card is not None else None) or card_id


def window_component_users(
    state: GameState,
    registry: StaticDataRegistry,
    player_ids: Iterable[str],
    *,
    respect_mutes: bool = False,
) -> list[str]:
    """Gracze z komponentem frakcji, którego mogą użyć TERAZ w chwilowym oknie (jawne: zdolność,
    technologia, żetony; bez okien trwających całą fazę - ``standing``).

    ``respect_mutes``: pomija komponenty/agentów wyciszonych przez gracza (54.12). Wyciszenia są
    PRYWATNE, więc tylko auto-pas silnika ich używa - lista uprawnionych (jawna) zostaje pełna.
    """
    from src.core import faction_components  # lokalnie: importuje moduły okien

    ids = list(player_ids)
    users = {
        row["player_id"]
        for row in faction_components.available_now(state, registry, ids)
        if not row["standing"]
        and not (
            respect_mutes
            and reaction_prefs.is_component_muted(
                state,
                row["player_id"],
                faction_components.effect_key(row["kind"], row["component_id"]),
            )
        )
    }
    return [pid for pid in ids if pid in users]


def skips_automatically(
    state: GameState,
    player_id: str,
    category: str | None = None,
    involved: Iterable[str] | None = None,
) -> bool:
    """Bot (brak jeszcze AI reakcji), „Skip all reactions”, deklaracja pasu w kategorii okna albo
    okno, które gracza nie dotyczy przy „only when it concerns me” (RULES.md 54.11-54.12)."""
    player = state.players.get(player_id)
    if player is None:
        return True
    if player.control_type is ControlType.BOT or player.private.auto_pass_reactions:
        return True
    if reaction_prefs.is_afk(state, player_id):
        return True  # AFK: stół nie czeka na nieobecnego (dowolna akcja w UI go przywraca)
    if reaction_prefs.declares_pass(state, player_id, category):
        return True
    return involved is not None and reaction_prefs.skips_uninvolved(state, player_id, involved)


def auto_passers(
    state: GameState,
    registry: StaticDataRegistry,
    eligible: Iterable[str],
    *,
    category: str | None = None,
    involved: Iterable[str] | None = None,
) -> list[str]:
    """Uprawnieni, za których silnik pasuje od razu (stan z JUŻ otwartym oknem).

    Kolejność jak w ``eligible``. Wynik zależy od treści rąk, dlatego trafia wyłącznie do
    prywatnej listy pasów - na zewnątrz okno wygląda identycznie (stała długość).
    """
    concerned = list(involved) if involved is not None else None
    return [
        pid
        for pid in eligible
        if skips_automatically(state, pid, category, concerned)
        or not has_playable_reaction(
            state, registry, pid, reaction_prefs.skipped_moments(state, pid, category)
        )
    ]


def all_passed(window: TimedWindow) -> bool:
    """Czy wszyscy uprawnieni spasowali (ręcznie albo auto-pasem)."""
    return set(window.eligible) <= set(window.passed)


def closes_early(state: GameState, window: TimedWindow) -> bool:
    """„Quick windows” hosta (54.12): okno kończy się, gdy wszyscy uprawnieni spasowali."""
    return state.quick_reaction_windows and all_passed(window)


def quick_delay(state: GameState, key: str) -> float:
    """Opóźnienie zamknięcia okna z „bluff jitter” (s): deterministyczne z klucza okna, w
    zakresie 50-100% ``reaction_jitter_seconds`` (0 = natychmiast)."""
    jitter = max(0.0, float(state.reaction_jitter_seconds))
    if jitter == 0.0:
        return 0.0
    fraction = int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], "big") / 0xFFFFFFFF
    return jitter * (0.5 + 0.5 * fraction)


def quick_settle(state: GameState, window: TimedWindow, key: str) -> bool:
    """„Quick windows”: czy okno ma się zamknąć TERAZ, bo wszyscy spasowali (MUTUJE ``window``).

    Bez jittera zwraca ``True``. Z jitterem okno NIE znika natychmiast (tempo zamknięcia nie
    zdradza, że nikt nie ma reakcji): skraca się do :func:`quick_delay` liczonego od otwarcia
    i kończy zwykłym upływem czasu.
    """
    if not closes_early(state, window):
        return False
    if state.reaction_jitter_seconds <= 0:
        return True
    window.seconds = min(float(window.seconds), quick_delay(state, key))
    return False


def record_timeout(state: GameState, window: TimedWindow) -> None:
    """Okno zakończone upływem czasu: cisi uprawnieni dostają strajk AFK (MUTUJE ``state``).

    Cisi = uprawnieni, którzy nie spasowali (także auto-pasem) i nie prosili o czas.
    """
    silent = [
        pid for pid in window.eligible
        if pid not in window.passed and pid not in window.extended_by
    ]
    reaction_prefs.record_timeout(state, silent)


def configure_jitter(state: GameState, seconds: float) -> GameState:
    """Host ustawia „bluff jitter” przy „Quick windows” (nowy stan).

    Raises:
        ValueError: Wartość poza ``0``..``MAX_JITTER_SECONDS``.
    """
    if not 0.0 <= seconds <= MAX_JITTER_SECONDS:
        raise ValueError(f"Jitter must be between 0 and {MAX_JITTER_SECONDS} seconds.")
    new_state = state.clone()
    new_state.reaction_jitter_seconds = float(seconds)
    return new_state


def configure_quick(state: GameState, enabled: bool) -> GameState:
    """Host włącza/wyłącza „Quick windows” (nowy stan; trwające okna zamyka wołający)."""
    new_state = state.clone()
    new_state.quick_reaction_windows = bool(enabled)
    return new_state


def ask_for_time(window: TimedWindow, player_id: str) -> None:
    """„More time”: przedłuża okno o ``WAIT_EXTENSION_SECONDS`` (MUTUJE okno na klonie stanu).

    Raises:
        ValueError: Gracz nie jest uprawniony albo już prosił w tym oknie.
    """
    if player_id not in window.eligible:
        raise ValueError(f"{player_id} is not asked to react in this window.")
    if player_id in window.extended_by:
        raise ValueError("You already asked for more time in this window.")
    window.extended_by = [*window.extended_by, player_id]
    window.seconds = float(window.seconds) + WAIT_EXTENSION_SECONDS


def set_auto_pass(state: GameState, player_id: str, enabled: bool) -> GameState:
    """Gracz włącza/wyłącza „Skip all reactions” (nowy stan).

    Włączenie w trakcie okna pasuje od razu w trwających oknach; wyłączenie nie cofa pasu.

    Raises:
        ValueError: Nieznany gracz.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    new_state = state.clone()
    new_state.players[player_id].private.auto_pass_reactions = bool(enabled)
    pass_open_windows(new_state, player_id)
    return new_state


def pass_open_windows(
    state: GameState, player_id: str, registry: StaticDataRegistry | None = None
) -> None:
    """Po zmianie preferencji: pasuje za gracza w trwających oknach, które teraz pomija (MUTUJE).

    Odwołanie nie cofa pasu (54.11). Z ``registry`` uwzględnia też deklaracje połowiczne
    („No whens”, gdy gracz ma tylko karty „when” = pas). Zamknięcie okien w trybie
    „Quick windows” robi :func:`settle_quick` (potrzebuje rejestru do rozstrzygnięcia karty).
    """
    pause = state.reaction_pause
    if pause is not None and player_id in pause.eligible and player_id not in pause.passed:
        category = reaction_prefs.category_of_event(pause.event)
        skip = reaction_prefs.skipped_moments(state, player_id, category)
        if skips_automatically(state, player_id, category, pause.involved) or (
            registry is not None
            and bool(skip)
            and not has_playable_reaction(state, registry, player_id, skip)
        ):
            pause.passed = [*pause.passed, player_id]
    held = state.held_play
    if held is not None and player_id in held.eligible and player_id not in held.passed:
        if skips_automatically(state, player_id, reaction_prefs.SABOTAGE, held.involved):
            held.passed = [*held.passed, player_id]


def settle_quick(state: GameState, registry: StaticDataRegistry) -> GameState:
    """„Quick windows”: zamyka trwające okna, w których wszyscy spasowali (nowy stan albo ten sam).

    Pauza po prostu znika; czekająca karta (okno Sabotage) rozstrzyga się od razu.
    """
    from src.core import card_hold  # lokalnie: card_hold importuje ten moduł

    result = state
    if result.reaction_pause is not None and closes_early(result, result.reaction_pause):
        result = result.clone()
        pause = result.reaction_pause
        assert pause is not None
        if quick_settle(result, pause, pause.key):
            result.reaction_pause = None
    held = result.held_play
    if held is not None and closes_early(result, held):
        result = result.clone()
        held = result.held_play
        assert held is not None
        if quick_settle(result, held, f"{held.player_id}|{held.card_id}|{held.opened_at}"):
            result = card_hold.resolve(result, registry)
    return result

