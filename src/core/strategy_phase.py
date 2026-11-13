"""Faza strategii — wybór kart strategii (Etap E2 planu pełnej rozgrywki).

Czyste funkcje nad ``GameState``: przyjmują stan, zwracają NOWY stan (przez ``clone``),
nie mutując wejścia — spójne z Event Sourcingiem. Reguły spisane w ``docs/RULES.md`` 13
na podstawie danych AsyncTI4 (`strategy_cards/pok.json`) i logiki bota
(`StrategyCardManager.incrementTradeGoods`, `PickStrategyCardButtonHandler`). Zero reguł
z pamięci; numery/nazwy kart pochodzą z rejestru.

Zakres E2 (szkielet): pula kart, wybór (transfer trade goods z karty do gracza),
akumulacja +1 TG na niewybranych kartach na koniec fazy, oznaczenie karty jako zagranej
(exhausted). Rozstrzyganie efektów primary/secondary (Leadership +3 CC itd.) to etap E4.
"""

from __future__ import annotations

from src.core import active_effects, economy, exhaust, rules_hooks, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.models import StrategyCardDef
from src.core.registry import StaticDataRegistry

# Klucze efektów kart reakcji wpływających na wybór/zwrot kart strategii (RULES.md 53.7).
DISGRACE_KEY = "action_cards:disgrace"  # Public Disgrace: data["forbidden"] = zakazane inicjatywy
STABILITY_KEY = "action_cards:stability"  # Political Stability: karty strategii nie wracają


def retains_strategy_cards(state: GameState, player_id: str) -> bool:
    """Czy Political Stability sprawia, że karty strategii gracza NIE wracają do puli."""
    return active_effects.has_effect(state, player_id, STABILITY_KEY)


def forbidden_picks(state: GameState, player_id: str) -> set[int]:
    """Inicjatywy, których gracz nie może teraz wybrać (Public Disgrace)."""
    forbidden: set[int] = set()
    for effect in active_effects.effects_for(state, player_id, DISGRACE_KEY):
        forbidden.update(int(i) for i in effect.data.get("forbidden", []))
    return forbidden


def available_initiatives(
    registry: StaticDataRegistry, set_alias: str | None = None
) -> list[int]:
    """Lista numerów inicjatywy kart w aktywnym zestawie (rosnąco).

    ``set_alias=None`` (domyślnie) → zestaw KANONICZNY wg włączonych źródeł
    (RULES.md 14): przy włączonym Thunder's Edge legalne są też te4/te6. Jawny alias
    wymusza konkretny zestaw (kompatybilność/testy).
    """
    return [card.initiative for card in registry.strategy_card_set(set_alias)]


def picked_initiatives(state: GameState) -> set[int]:
    """Zbiór numerów inicjatywy kart już wybranych przez graczy."""
    picked: set[int] = set()
    for player in state.players.values():
        picked.update(player.strategy_cards)
    return picked


def speaker_order(state: GameState) -> list[str]:
    """Kolejność graczy wg SPEAKER ORDER (mówca pierwszy, zegarowo) (RULES.md 24).

    Rotuje ``seating_order`` tak, by zaczynał się od ``speaker_id``. Gdy brak
    seating order (np. gra utworzona ręcznie), awaryjnie używa kolejności po id
    graczy — dalej zaczynając od mówcy, jeśli jest znany.
    """
    order = list(state.seating_order) or sorted(state.players)
    # Zostaw tylko istniejących graczy (seating_order może mieć nieaktualne id).
    order = [pid for pid in order if pid in state.players]
    if not order:
        return []
    speaker = state.speaker_id
    if speaker in order:
        idx = order.index(speaker)
        return order[idx:] + order[:idx]
    return order


def pick_count(state: GameState) -> int:
    """Liczba kart strategii na gracza wg liczby graczy (RULES.md 13).

    Reguła TI4: 2 karty/gracz przy 3–4 graczach, 1 karta/gracz przy 5–8. Liczba
    graczy liczona jako ``len(state.players)``. Czysta funkcja — tylko oblicza,
    nie zmienia stanu.

    ⚠️ ZAŁOŻENIE (gra 2-osobowa) — RULES.md 13: oficjalne TI4 nie definiuje trybu
    2-osobowego, więc przyjmujemy wariant spójny z progiem 3–4 graczy: **2 karty na
    gracza**. Dzięki temu silnik (solo vs 1 bot, hot-seat 1v1) nie wywraca się w
    fazie strategii. Wartość do potwierdzenia przez użytkownika — zmiana tutaj w
    jednym miejscu, jeśli preferowany jest inny wariant (np. 3 karty/gracz).

    Raises:
        ValueError: Gdy liczba graczy jest mniejsza niż 2 lub większa niż 8
            (liczba nieobsługiwana przez regułę); stan pozostaje bez zmian, bo
            funkcja go nie dotyka.
    """
    n = len(state.players)
    if n < 2 or n > 8:
        raise ValueError(f"Invalid number of players: {n} (allowed 2-8).")
    return 2 if n <= 4 else 1


def next_strategy_picker(state: GameState) -> str | None:
    """Następny gracz w speaker order poniżej ``Pick_Count`` (lub None).

    Startuje od mówcy (``speaker_order`` zawsze liczy od mówcy) i zwraca pierwszego
    gracza, który ma mniej niż ``pick_count(state)`` kart. Gdy wszyscy osiągnęli
    ``Pick_Count`` — zwraca None (faza strategii gotowa do przejścia w akcję).

    Druga runda wyboru (3–4 graczy, a także 2 graczy — ⚠️ ZAŁOŻENIE) jest RUNDOWA,
    zgodnie ze źródłem (tirules „Strategy Phase", Step 1): *„After the last player has
    received their first strategy card, each player chooses a second strategy card,
    starting with the speaker and proceeding clockwise."* Czyli NAJPIERW wszyscy biorą
    PIERWSZĄ kartę (w speaker order), a DOPIERO potem wszyscy drugą — a nie jeden gracz
    obie z rzędu. Realizujemy to bez osobnego licznika rund: „bieżąca runda" = najmniejsza
    liczba kart wśród graczy (``floor``), a następny picker to pierwszy w speaker order,
    który ma DOKŁADNIE tyle kart (czyli jeszcze nie wybierał w tej rundzie) i wciąż jest
    poniżej ``Pick_Count``. Dzięki temu kolejność to p1, p2, …, p1, p2, … (RULES.md 13, 24).

    Robustność dla niepełnego setu (<2 lub >8 graczy): ``pick_count`` rzuca wtedy
    ``ValueError``; tutaj ŁAPIEMY go i zwracamy None, by nie psuć wywołań
    wewnętrznych z niepełnym setem (np. setup, gra budowana w God-Mode). Twardy błąd
    liczby graczy pozostaje tam, gdzie to świadoma akcja gracza
    (``pick_strategy_card``/``ensure_strategy_complete``). Przy 5–8 graczach
    (``pick_count == 1``) jest tylko jedna runda, więc wynik jest identyczny jak dawniej
    (pierwszy gracz bez karty).
    """
    try:
        needed = pick_count(state)
    except ValueError:
        return None
    order = speaker_order(state)
    if not order:
        return None
    # Bieżąca runda = najmniejsza liczba kart wśród graczy. Następny wybiera pierwszy
    # w speaker order, który ma jeszcze TYLE kart (nie wybierał w tej rundzie) i wciąż
    # < Pick_Count. Gdy wszyscy osiągnęli Pick_Count → None (faza gotowa do akcji).
    # Checks and Balances: liczą się WYBORY gracza, nie karty, które dostał od innych.
    def count(pid: str) -> int:
        if gives_chosen_cards(state):
            return state.strategy_choices.get(pid, 0)
        return len(state.players[pid].strategy_cards)

    current_round = min(count(pid) for pid in order)
    if current_round >= needed:
        return None
    for pid in order:
        if count(pid) == current_round:
            return pid
    return None


def gives_chosen_cards(state: GameState) -> bool:
    """Checks and Balances („For"): wybraną kartę strategii dostaje inny gracz (RULES.md 51.6)."""
    return any(
        rules_hooks.permits(rules_hooks.POINT_STRATEGY_GIVE_CHOSEN, state, pid)
        for pid in state.players
    )


def card_recipients(state: GameState, player_id: str) -> list[str]:
    """Kto może dostać wybraną kartę: inni gracze z mniej niż ``pick_count`` kartami."""
    needed = pick_count(state)
    return [
        pid for pid in speaker_order(state)
        if pid != player_id and len(state.players[pid].strategy_cards) < needed
    ]


def ensure_strategy_complete(state: GameState) -> None:
    """Waliduje, że wybór kart strategii został w pełni ukończony.

    Każdy gracz w ``speaker_order`` musi osiągnąć ``pick_count(state)`` kart.
    W przeciwnym razie faza strategii nie może przejść w fazę akcji (RULES.md 13,
    29) — wołane przez ``turn_flow.next_phase`` przy przejściu STRATEGY→ACTION.

    Czysta kontrola: NIE zmienia stanu (nie klonuje, nie mutuje), jedynie czyta
    liczbę kart każdego gracza. ``pick_count`` propaguje własny ``ValueError`` przy
    nieobsługiwanej liczbie graczy (<2 lub >8) — tu świadomie nie łapiemy go, bo
    sprawdzenie kompletności dla takiego setu nie ma sensu.

    Spójność kolejności (znalezisko #1 przeglądu): ``speaker_order`` iteruje po
    ``seating_order``, a ``turn_flow.strict_initiative_order`` po ``state.players``.
    Gdy niepuste ``seating_order`` nie pokrywa się ze zbiorem graczy (realna ścieżka:
    God-Mode dodaje gracza bez aktualizacji ``seating_order``), kompletność liczona
    po ``speaker_order`` mogłaby „przejść", a ``strict_initiative_order`` rzuciłoby
    mylący błąd o braku karty. Dlatego TUTAJ — przed sprawdzeniem kompletności —
    twardo walidujemy ``set(seating_order) == set(players)`` i dajemy czytelny
    komunikat. Puste ``seating_order`` jest OK: ``speaker_order`` używa wtedy
    ``sorted(players)`` (spójne ze zbiorem graczy).

    Raises:
        ValueError: Gdy niepuste ``seating_order`` nie pokrywa się z listą graczy
            (znalezisko #1), lub gdy którykolwiek gracz ma mniej kart niż
            ``pick_count`` — komunikat „Wybór kart strategii nie został ukończony."
            (R9.2, R9.3).
    """
    if state.seating_order and set(state.seating_order) != set(state.players):
        raise ValueError(
            "Inconsistent state: seating_order does not match the "
            "players. Use God-Mode to fix it."
        )
    needed = pick_count(state)
    for pid in speaker_order(state):
        if len(state.players[pid].strategy_cards) < needed:
            raise ValueError("Strategy card selection has not been completed.")


def pick_strategy_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    initiative: int,
    *,
    set_alias: str | None = None,
    recipient: str | None = None,
) -> GameState:
    """Gracz wybiera kartę strategii o danym numerze inicjatywy.

    ``recipient`` - Checks and Balances („For"): gracz, który dostaje wybraną kartę (inny,
    bez kompletu kart; gdy nikt taki nie istnieje - karta zostaje u wybierającego).

    Efekty (RULES.md 13):
    - Karta musi należeć do aktywnego zestawu i nie być wcześniej wybrana.
    - Wybór musi odbywać się w kolejności (to tura danego gracza) i poniżej
      limitu ``Pick_Count`` (2 karty/gracz przy 3–4 graczach, 1 przy 5–8).
    - Gracz otrzymuje wszystkie trade goods leżące na karcie; licznik karty → 0.
    - Numer karty trafia do ``player.strategy_cards`` (lista utrzymywana rosnąco,
      ustala inicjatywę tur).

    Kolejność walidacji (wszystkie PRZED ``clone`` — stan wejściowy niezmieniony
    przy błędzie, R5): gracz istnieje → karta w zestawie → karta niewybrana →
    kolejność wyboru → limit ``Pick_Count``. Walidacje „co" (gracz/karta) idą
    przed „kiedy" (kolejność/limit), bo błąd „nie twoja kolej" ma sens dopiero dla
    istniejącego gracza i realnej karty.

    Raises:
        ValueError: Gdy gracz nie istnieje (R5.6), karta spoza zestawu (R5.4),
            karta już wybrana (R5.5), wybór poza kolejnością (R4.5) lub osiągnięto
            limit ``Pick_Count`` (R3.5).
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    if state.setup is not None:
        raise ValueError("Finish the game setup (secret objectives, tokens, objectives) first.")
    if initiative not in available_initiatives(registry, set_alias):
        raise ValueError(f"Initiative card {initiative} is not in the set.")
    if initiative in picked_initiatives(state):
        raise ValueError(f"Initiative card {initiative} is already taken.")
    # Kolejność (R4.5): wybierać może tylko bieżący picker w speaker order.
    picker = next_strategy_picker(state)
    if player_id != picker:
        raise ValueError(f"Out-of-turn pick: it is now the pick of {picker}.")
    # Limit Pick_Count (R3.5): gracz nie może przekroczyć dozwolonej liczby kart.
    allowed = pick_count(state)
    giving = gives_chosen_cards(state)
    if not giving and len(state.players[player_id].strategy_cards) >= allowed:
        raise ValueError(f"Allowed number of cards exceeded ({allowed}).")
    holder = player_id
    if giving:
        eligible = card_recipients(state, player_id)
        if eligible:
            if recipient not in eligible:
                raise ValueError(
                    "Checks and Balances: give the chosen strategy card to another player "
                    f"without a full hand of strategy cards ({', '.join(eligible)})."
                )
            holder = recipient
        elif len(state.players[player_id].strategy_cards) >= allowed:
            raise ValueError(f"Allowed number of cards exceeded ({allowed}).")
    elif recipient not in (None, player_id):
        raise ValueError("Strategy cards cannot be given to another player now.")

    # Public Disgrace (RULES.md 53.7): gracz musi wybrać INNĄ kartę, o ile jest dostępna.
    forbidden = forbidden_picks(state, player_id)
    if initiative in forbidden:
        taken = picked_initiatives(state)
        if any(
            i not in taken and i not in forbidden
            for i in available_initiatives(registry, set_alias)
        ):
            raise ValueError(
                f"Public Disgrace: you must choose a different strategy card than {initiative}."
            )

    new_state = state.clone()
    fired = triggers.fire(
        new_state, GameEvent.STRATEGY_CARD_CHOSEN, Moment.WHEN, subject=player_id,
        ctx={"player": player_id, "initiative": initiative},
    )
    if fired.replaced:  # „instead of”: wybór nie następuje, gracz wybiera ponownie
        return new_state
    player = new_state.players[holder]
    new_state.strategy_choices[player_id] = new_state.strategy_choices.get(player_id, 0) + 1
    # Transfer trade goods z karty do gracza (WYBIERAJĄCEGO - C_agendas), zerowanie licznika.
    tg_on_card = new_state.strategy_card_tg.get(initiative, 0)
    if tg_on_card:
        economy.gain_trade_goods(new_state, player_id, tg_on_card)
    new_state.strategy_card_tg[initiative] = 0
    # Lista kart utrzymywana rosnąco (R5.1) — ustala poprawną inicjatywę tur.
    player.strategy_cards = sorted([*player.strategy_cards, initiative])
    active_effects.remove_by_key(new_state, DISGRACE_KEY, owner=player_id)  # zakaz spełniony
    # Przekaż turę wyboru następnemu graczowi w speaker order. Gdy wszyscy już
    # wybrali (picker = None), faza jest gotowa do przejścia w akcję, ale aktywny
    # NIE staje się None — wskazuje MÓWCĘ, który ogłosi tranzycję przez /phase/next
    # (RULES.md 24, 31.4; zasada "zawsze czyjaś tura").
    new_state.active_player_id = (
        next_strategy_picker(new_state) or new_state.speaker_id
    )
    triggers.fire(
        new_state, GameEvent.STRATEGY_CARD_CHOSEN, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "initiative": initiative},
    )
    return new_state


def play_strategy_card(
    state: GameState, player_id: str, initiative: int
) -> GameState:
    """Oznacza kartę strategii gracza jako ZAGRANĄ (exhausted/odwróconą).

    Nie rozstrzyga efektów primary (to etap E4) — jedynie zmienia stan karty, by
    panel pokazał ją jako zużytą. Idempotentne (ponowne zagranie nie duplikuje).

    Raises:
        ValueError: Gdy gracz nie posiada tej karty.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    player = state.players[player_id]
    if initiative not in player.strategy_cards:
        raise ValueError(f"Player does not hold the initiative card {initiative}.")

    new_state = state.clone()
    exhaust.exhaust_strategy_card(new_state, player_id, initiative)
    return new_state


def accumulate_unpicked_tg(
    state: GameState, registry: StaticDataRegistry, *, set_alias: str | None = None
) -> GameState:
    """Dokłada +1 trade good na każdej NIEWYBRANEJ karcie zestawu (koniec fazy).

    Port reguły ``StrategyCardManager.incrementTradeGoods``: dla każdego numeru karty
    spoza zbioru wybranych licznik TG rośnie o 1. Wywoływane przy przejściu do nowej
    rundy (karty wracają do puli, niechciane zyskują TG).

    Guard (R7.5): akumulacja ma sens dopiero po zakończeniu fazy strategii.
    Sprawdzenie na WEJŚCIU, przed ``clone`` — liczniki TG pozostają bez zmian przy
    błędzie.

    Wariant guardu (znalezisko #2/#3 przeglądu): wołamy ``ensure_strategy_complete``
    zamiast wnioskować z ``next_strategy_picker(state) is not None``. Poprzedni guard
    był dziurawy dla liczby graczy spoza 2–8: ``next_strategy_picker`` ŁAPIE
    ``ValueError`` z ``pick_count`` i zwraca ``None``, więc dla 1 gracza guard
    „czy jest picker" fałszywie uznawał fazę za zakończoną i ``/round/next``
    przepuszczało akumulację zamiast ją odrzucić. ``ensure_strategy_complete`` woła
    ``pick_count`` BEZPOŚREDNIO, więc:
    - dla <2/>8 graczy propaguje „Nieprawidłowa liczba graczy…" (akumulacja
      ODRZUCONA — nieobsługiwany set nie może być „zakończoną fazą");
    - dla niekompletnego wyboru rzuca „Wybór kart strategii nie został ukończony." —
      owijamy to w dotychczasowy komunikat akumulacji, by zachować kontrakt.

    Raises:
        ValueError: Gdy faza strategii nie została zakończona (niekompletny wybór) —
            komunikat „Nie można akumulować: faza strategii niezakończona." (R7.5);
            albo gdy liczba graczy jest spoza 2–8 (propagacja z ``pick_count``).
    """
    try:
        ensure_strategy_complete(state)
    except ValueError as exc:
        # Niekompletny wybór → zachowujemy komunikat akumulacji (kontrakt R7.5).
        # Pozostałe błędy (zła liczba graczy, rozjazd seating_order) propagujemy
        # z oryginalnym, sensownym komunikatem.
        if "has not been completed" in str(exc):
            raise ValueError(
                "Cannot accumulate: strategy phase not completed."
            ) from exc
        raise
    new_state = state.clone()
    picked = picked_initiatives(new_state)
    for initiative in available_initiatives(registry, set_alias):
        if initiative not in picked:
            new_state.strategy_card_tg[initiative] = (
                new_state.strategy_card_tg.get(initiative, 0) + 1
            )
    return new_state


def add_trade_goods_to_card(state: GameState, initiative: int, amount: int) -> None:
    """Kładzie ``amount`` trade goods z zasobów ogólnych na karcie strategii (mutuje ``state``).

    Punkt centralny dla efektów „place trade goods on a strategy card” (Manipulate Investments):
    TG nie pochodzą z puli gracza. Wybierający kartę dostanie je jak każde TG z karty
    (``pick_strategy_card``).

    Raises:
        ValueError: Ujemna ilość.
    """
    if amount < 0:
        raise ValueError("The number of trade goods cannot be negative.")
    state.strategy_card_tg[initiative] = state.strategy_card_tg.get(initiative, 0) + amount


def set_speaker(state: GameState, player_id: str | None) -> None:
    """Przekazuje żeton mówcy — JEDYNE miejsce zmiany ``GameState.speaker_id`` (RULES.md 43.1a).

    Hook „gdy zmienia się mówca" (np. zdolności reagujące na przejęcie żetonu) dopisujemy tu.
    Mutuje ``state`` (KLON roboczy wołającego); nie zmienia kolejności miejsc ani aktywnego
    gracza — to robi wołający.
    """
    if player_id is not None and player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    state.speaker_id = player_id
    if player_id is not None:
        triggers.fire(
            state,
            GameEvent.SPEAKER_CHANGED,
            Moment.AFTER,
            subject=player_id,
            ctx={"player": player_id},
        )


def reset_strategy_cards(state: GameState) -> GameState:
    """Zwraca wszystkie karty strategii do puli (czyści wybory graczy).

    Używane na starcie nowej fazy strategii: karty wracają do puli, ``strategy_cards``
    i ``exhausted_strategy_cards`` graczy są czyszczone. Trade goods na kartach
    (``strategy_card_tg``) NIE są czyszczone — akumulują się między rundami.
    """
    new_state = state.clone()
    new_state.strategy_choices = {}
    for player_id, player in new_state.players.items():
        # Political Stability (RULES.md 53.7): karty zostają u gracza (jest "gotowy"), a w
        # następnej fazie strategii nie wybiera - ``next_strategy_picker`` pomija go samo.
        if not retains_strategy_cards(new_state, player_id):
            player.strategy_cards = []
        exhaust.ready_all_strategy_cards(new_state, player_id)
    # Nowa faza strategii zaczyna wybierać mówca (speaker) — RULES.md 24.
    # Fallback na mówcę przy niepełnym secie (picker = None), by nie zostawić
    # None w toczącej się partii (RULES.md 31.4).
    new_state.active_player_id = (
        next_strategy_picker(new_state) or new_state.speaker_id
    )
    return new_state


def close_round_cards(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Koniec rundy: TG na niewybranych kartach + zwrot kart strategii do puli.

    Gdy nikt już nie trzyma kart (zwrócono je w kroku 8 fazy statusu — RULES.md 41), nic
    nie robi: akumulacja TG i reset już się odbyły. Inaczej: ``accumulate`` → ``reset``.
    """
    if not any(
        player.strategy_cards and not retains_strategy_cards(state, player_id)
        for player_id, player in state.players.items()
    ):
        return state.clone()
    return reset_strategy_cards(accumulate_unpicked_tg(state, registry))


def ensure_card_fields_complete(cards: list[StrategyCardDef]) -> None:
    """Sprawdza komplet pól per-karta wymaganych do opisu puli (R6.4).

    Reguła spójności danych rejestru — klasa reguły inicjalizacji fazy strategii,
    dlatego żyje w ``core/`` obok ``validate_strategy_card_set`` (a nie w routerze):
    tej samej kontroli potrzebuje zarówno ``api/``, jak i przyszłe ``ai/`` przy
    budowaniu puli kart. Przeniesione z ``api/routers/strategy.py`` (znalezisko #4
    przeglądu semantycznego).

    Dla każdej karty wymagamy: nazwy, tekstu primary, tekstu secondary oraz koloru
    (``initiative`` jest zwalidowana osobno w ``validate_strategy_card_set``). Gdy
    któregokolwiek pola brakuje w danych rejestru → ``ValueError("Karta {id}: brak
    pola {pole}.")``. Zero wartości kodowanych w module — wyłącznie odczyt z danych
    karty.

    Raises:
        ValueError: Gdy karta nie ma kompletu pól (nazwa/primary/secondary/kolor).
    """
    for card in cards:
        if not card.name:
            raise ValueError(f"Card {card.id}: missing name field.")
        if not card.primary_texts:
            raise ValueError(f"Card {card.id}: missing primary text field.")
        if not card.secondary_texts:
            raise ValueError(f"Card {card.id}: missing secondary text field.")
        if not card.colour_hex_code:
            raise ValueError(f"Card {card.id}: missing color field.")


def validate_strategy_card_set(
    registry: StaticDataRegistry, *, set_alias: str | None = None
) -> list[StrategyCardDef]:
    """Zwraca 8 kart zestawu lub ``ValueError``, gdy łamany komplet/unikalność/pola.

    Guard spójności danych rejestru — reguła inicjalizacji fazy strategii
    (Requirement 6.1, 6.2, 6.4), dlatego żyje w ``core/``, a nie w routerze: woła go
    zarówno ``api/``, jak i przyszłe ``ai/``. Dane kart pochodzą WYŁĄCZNIE z
    ``StaticDataRegistry.strategy_card_set`` — zero hardkodowania.

    Sprawdza niezmienniki zestawu podstawowego TI4:
    - dokładnie 8 kart,
    - każdy ``Initiative`` mieści się w zakresie 1..8,
    - brak duplikatów ``Initiative``,
    - komplet pól per karta (nazwa/primary/secondary/kolor) — przez
      ``ensure_card_fields_complete`` (R6.4, przeniesione z routera — znalezisko #4).

    Returns:
        Lista ``StrategyCardDef`` (ta sama, co z rejestru — posortowana po
        ``initiative``), gdy zestaw jest spójny.

    Raises:
        ValueError: Gdy komplet (dokładnie 8), unikalność ``Initiative`` 1–8 lub
            komplet pól karty jest złamany; komunikat
            „Niespójny zestaw kart: {szczegół}." albo „Karta {id}: brak pola {pole}.".
    """
    cards = registry.strategy_card_set(set_alias)

    if len(cards) != 8:
        raise ValueError(
            f"Inconsistent card set: expected 8 cards, got {len(cards)}."
        )

    initiatives = [card.initiative for card in cards]

    out_of_range = sorted({i for i in initiatives if i < 1 or i > 8})
    if out_of_range:
        raise ValueError(
            "Inconsistent card set: initiative outside range 1-8: "
            f"{out_of_range}."
        )

    duplicates = sorted({i for i in initiatives if initiatives.count(i) > 1})
    if duplicates:
        raise ValueError(
            f"Inconsistent card set: duplicate initiatives: {duplicates}."
        )

    # Komplet pól każdej karty (R6.4) — ostatnia kontrola po sprawdzeniu kompletu
    # i unikalności inicjatyw.
    ensure_card_fields_complete(cards)

    return cards
