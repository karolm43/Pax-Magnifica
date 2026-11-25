"""Warstwa widoczności — projekcja ``GameState`` do perspektywy jednego gracza (R4, R5).

Rzutuje pełny ``GameState`` na NOWY ``GameState`` widziany oczami jednego
„gracza patrzącego" (Viewing_Player): informacje publiczne (``Public_Info``)
wszystkich graczy pozostają bez zmian, prywatne (``Private_Info``) widać tylko
dla samego viewera, a prywatne ręce pozostałych graczy są zredagowane do samych
liczebności (zapisanych w ``hidden_card_counts``).

Zasady warstwy ``core/`` respektowane tutaj:

* **Czysta funkcja** (R4.6) — bez mutacji wejścia, bez efektów ubocznych, bez
  importów HTTP. Projekcja działa wyłącznie na kopii (``clone()``).
* **Jedno źródło klasyfikacji** (R2.4) — które pole gracza jest prywatne, czyta
  się WYŁĄCZNIE z ``player_fields`` (``PRIVATE_FIELDS``); moduł nie powiela
  listy pól ani nie klasyfikuje ich po swojemu.

Reprezentacja „zredagowanej" ręki to licznik, nie lista: wynik projekcji pozostaje
tym samym typem ``GameState`` (serializowalnym identycznie jak pełny stan), więc
zredagowane listy są czyszczone (długość 0), a ich pierwotne liczebności trafiają
do osobnego słownika ``PlayerState.hidden_card_counts`` (R4.4).
"""

from __future__ import annotations

from .game_state import GameState, PlayerPrivateState, PlayerState
from .player_fields import PRIVATE_FIELDS

# Nazwy prywatnych list w ``PlayerPrivateState`` — odczytane z modelu, nie
# hardkodowane, żeby dołożenie kolejnej prywatnej listy nie wymagało zmian tutaj.
_PRIVATE_LIST_FIELDS: tuple[str, ...] = tuple(
    name
    for name, info in PlayerPrivateState.model_fields.items()
    # kolekcje (listy/słowniki); flagi i podmodele (auto-pas, prefs) redakcja zeruje i tak
    if info.default_factory in (list, dict)
)

# Nazwa pola prywatnego w ``PlayerState`` (jedno źródło klasyfikacji, R2.4).
# Oczekujemy dokładnie jednego pola prywatnego: podmodelu ``private``.
_PRIVATE_FIELD: str = next(iter(PRIVATE_FIELDS))


class VisibilityError(ValueError):
    """Naruszenie niezmiennika widoczności (R5.4) albo nieznany viewer (R4.5).

    Podtyp ``ValueError`` — warstwa ``api/`` mapuje go na odpowiedź HTTP 422,
    tak jak pozostałe błędy domenowe.
    """


def project_counts(private: PlayerPrivateState) -> dict[str, int]:
    """Zwraca mapę liczebności prywatnych list: nazwa pola → długość listy.

    Pomocnicza przy redakcji: dla każdej prywatnej ręki (``action_cards``,
    ``secret_objectives``, ``promissory_notes`` i ewentualnych przyszłych)
    podaje liczbę kart, pomijając ich identyfikatory (R4.4). Pusta ręka → 0
    (R5.3), bez błędu.
    """
    return {
        field: len(getattr(private, field)) for field in _PRIVATE_LIST_FIELDS
    }


def project_for_viewer(state: GameState, viewing_player_id: str) -> GameState:
    """Zwraca NOWY ``GameState`` widziany oczami ``viewing_player_id``.

    Semantyka projekcji:

    * ``Public_Info`` wszystkich graczy — bez zmian (R4.1, R5.2).
    * ``Private_Info`` viewera — bez zmian (R4.2, R5.5).
    * ``Private_Info`` każdego gracza ≠ viewer — zredagowane: każda prywatna
      lista wyczyszczona (długość 0), a jej pierwotna liczebność zapisana
      w ``hidden_card_counts`` tego gracza (R4.3, R4.4, R5.1, R5.3).
    * Pusty stan (brak graczy) → kopia pustego stanu, bez błędu (R4.7).

    Czysta funkcja (R4.6): wejściowy ``state`` nie jest mutowany — redakcja
    działa na ``state.clone()``.

    Args:
        state: Pełny, niezredagowany stan gry.
        viewing_player_id: Identyfikator gracza, z którego perspektywy rzutujemy.

    Returns:
        Nowy ``GameState`` z prywatnymi rękami graczy ≠ viewer zredagowanymi do
        liczebności.

    Raises:
        VisibilityError: gdy viewer jest nieobecny w stanie (R4.5) — wejście
            pozostaje niezmienione; albo gdy asercja końcowa wykryje niepustą
            prywatną listę gracza ≠ viewer (R5.4) — zamiast zwracać częściowo
            zredagowany stan.
    """
    # 1. Pusty stan (brak graczy) → kopia pustego stanu, bez błędu (R4.7).
    if not state.players:
        return state.clone()

    # 2. Viewer nieobecny → błąd, bez mutacji wejścia (R4.5). Jeszcze nie
    #    klonowaliśmy mutująco, więc ``state`` pozostaje nietknięty.
    if viewing_player_id not in state.players:
        raise VisibilityError(
            f"Perspective player '{viewing_player_id}' does not exist in the game state."
        )

    # 3. Pracujemy wyłącznie na głębokiej kopii (czystość, R4.6).
    projected = state.clone()

    # 4. Redakcja prywatnych rąk każdego gracza ≠ viewer (R4.3, R4.4).
    for player_id, player in projected.players.items():
        if player_id == viewing_player_id:
            continue
        _redact_player(player)

    # 4b. Pasy w oknach reakcji - tylko własny (RULES.md 54.11).
    redact_reaction_windows(projected, viewing_player_id)

    # 5. Asercja końcowa (R5.4) — bezpiecznik przed wyciekiem: dla każdego gracza
    #    ≠ viewer wszystkie prywatne listy MUSZĄ być puste. Naruszenie → błąd,
    #    bez zwracania częściowo zredagowanego stanu.
    _assert_no_leak(projected, viewing_player_id)

    # 6. Zwróć zredagowaną projekcję.
    return projected


def project_all_redacted(state: GameState) -> GameState:
    """Zwraca NOWY ``GameState`` z rękami WSZYSTKICH graczy zredagowanymi (brak viewera).

    Perspektywa „nikt nie patrzy": używana, gdy nie da się ustalić viewera (brak
    jawnego ``viewing_player`` i brak aktywnego gracza — np. między turami, po
    komplecie wyboru kart strategii, w fazach bez aktywnego gracza). To POPRAWNY,
    normalny stan gry, nie błąd — dokument web-data musi się wtedy zbudować, tylko
    bez pełnej ręki kogokolwiek. Każda prywatna ręka jest zredagowana do liczebności
    (``hidden_card_counts``), więc widoczność jest bezpieczna (R4.3, R4.4): skoro
    nie wiadomo, kto patrzy, nie ujawniamy niczyich kart.

    Czysta funkcja (R4.6): wejście nie jest mutowane (redakcja na ``clone()``).
    Pusty stan → kopia pustego stanu (R4.7).
    """
    if not state.players:
        return state.clone()
    projected = state.clone()
    for player in projected.players.values():
        _redact_player(player)
    redact_reaction_windows(projected, None)
    return projected


def redact_reaction_windows(state: GameState, viewer_id: str | None) -> None:
    """Pasy i prośby o czas w oknach reakcji: tylko patrzący (MUTUJE kopię; RULES.md 54.11).

    Silnik pasuje sam za graczy bez pasującej karty, więc lista pasów zdradzałaby, kto ma kartę.
    Długość okna (``seconds``) zostaje jawna - jest taka sama niezależnie od rąk.
    """
    for window in (state.reaction_pause, state.held_play):
        if window is None:
            continue
        window.passed = [pid for pid in window.passed if pid == viewer_id]
        # Liczba próśb o czas jest jawna (widać przedłużenie), tożsamość - nie.
        window.extended_by = [pid if pid == viewer_id else "" for pid in window.extended_by]
    held = state.held_play
    if held is not None and held.frozen_by != viewer_id:
        held.frozen_by = "" if held.frozen_by else None  # zatrzymanie jawne, kto - prywatne


def _redact_player(player: PlayerState) -> None:
    """Redaguje ``Private_Info`` pojedynczego gracza (w miejscu, na kopii).

    Zapisuje liczebności prywatnych list w ``hidden_card_counts``, po czym
    zastępuje cały podmodel prywatny świeżym, pustym ``PlayerPrivateState``
    (wszystkie listy puste). Klasyfikacja „co jest prywatne" pochodzi z
    ``PRIVATE_FIELDS`` (jedno źródło, R2.4).
    """
    private = getattr(player, _PRIVATE_FIELD)
    player.hidden_card_counts = project_counts(private)
    setattr(player, _PRIVATE_FIELD, PlayerPrivateState())


def _assert_no_leak(projected: GameState, viewing_player_id: str) -> None:
    """Niezmiennik końcowy (R5.4): żadna cudza prywatna lista nie może być niepusta.

    Rzuca ``VisibilityError``, jeśli dla któregokolwiek gracza ≠ viewer jakakolwiek
    prywatna lista pozostała niepusta.
    """
    for player_id, player in projected.players.items():
        if player_id == viewing_player_id:
            continue
        private = getattr(player, _PRIVATE_FIELD)
        for field in _PRIVATE_LIST_FIELDS:
            if getattr(private, field):
                raise VisibilityError(
                    "Visibility violation: private list "
                    f"'{field}' of player '{player_id}' was not redacted."
                )


# --- Projekcja ścisła (gra sieciowa, RULES.md 44.3) ----------------------------------------

HIDDEN_CARD = "hidden"
"""Zaślepka karty w zakrytej talii: długość talii jawna, kolejność i skład — nie."""


_HIDDEN_DECKS = ("action_card_deck", "secret_objective_deck", "agenda_deck", "relic_deck")
_HIDDEN_OBJECTIVE_DECKS = ("stage1_deck", "stage2_deck")
_HIDDEN_DECK_PILES = ("exploration_deck",)


def _hide(cards: list[str]) -> list[str]:
    return [HIDDEN_CARD] * len(cards)


def project_strict(state: GameState, viewing_player_id: str | None) -> GameState:
    """Projekcja dla klienta sieciowego: TYLKO to, co ten gracz może wiedzieć (RULES.md 44.3).

    Ponad ``project_for_viewer`` (cudze ręce → liczniki) ukrywa też:

    * kolejność i skład zakrytych talii (karty akcji, agendy, tajne cele, cele etapu I/II,
      relikty, eksploracja) — zostaje sama długość (zaślepki ``HIDDEN_CARD``);
    * ziarno RNG (``rng_seed``) — znając je, dałoby się przewidzieć kości;
    * cudze decyzje (``pending_offers``) — zostaje kto/czy obowiązkowa, bez etykiety i kontekstu;
    * roboczy szkic karty strategii (``pending_strategy.draft``) dla nie-właściciela.

    ``viewing_player_id=None`` = obserwator (żadnej ręki). Czysta funkcja (kopia stanu).
    """
    if viewing_player_id is None or viewing_player_id not in state.players:
        projected = project_all_redacted(state)
    else:
        projected = project_for_viewer(state, viewing_player_id)
    # Projekcja kopii (nie zmiana stanu gry): ogólne ``setattr`` po nazwach, jak redakcja rąk.
    for holder, names in (
        (projected.decks, _HIDDEN_DECKS),
        (projected.objectives, _HIDDEN_OBJECTIVE_DECKS),
    ):
        for name in names:
            setattr(holder, name, _hide(getattr(holder, name)))
    for name in _HIDDEN_DECK_PILES:  # talie per rodzaj (eksploracja: {typ: [karty]})
        piles = getattr(projected.decks, name)
        setattr(projected.decks, name, {kind: _hide(cards) for kind, cards in piles.items()})
    projected.rng_seed = 0
    for offer in projected.pending_offers:
        if offer.player_id != viewing_player_id:
            offer.label = ""
            offer.ctx = {}
    pending = projected.pending_strategy
    if pending is not None and pending.owner_id != viewing_player_id:
        pending.draft = {}
    return projected
