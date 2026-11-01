# Domknięcie fazy strategii: silnik-sędzia dla wyboru kart i przejścia STRATEGY→ACTION

Zakres: od commita `921b670~1` (`01c523c`, przed serią fazy strategii) do `HEAD` (`a62be4c`). Zmiana domyka E2: wprowadza `Pick_Count` zależny od liczby graczy (2 przy 3–4, 1 przy 5–8), egzekwuje kolejność i limit wyboru w `pick_strategy_card`, blokuje przejście do fazy akcji przy niekompletnym wyborze (`ensure_strategy_complete` w `next_phase`), dodaje guard akumulacji TG (`accumulate_unpicked_tg`) i guard spójności zestawu (`validate_strategy_card_set`). Endpointy `/phase/next`, `/round/next`, `/strategy/cards` mapują błędy domenowe na HTTP 422. Frontend dostaje `strategyPickCount` i pełne nazwy frakcji z rejestru, a `strategyCards.ts` — priorytet źródeł (te>pok>codex>base) z fallbackiem grafiki. Kierunek „silnik-sędzia" (RULES.md 29) jest tu konsekwentnie realizowany: reguły egzekwowane w `core/`, endpointy cienkie, God-Mode zostaje wentylem.

Watch for: (1) **confirmed** — asymetria między `speaker_order` (baza dla `ensure_strategy_complete`/`next_strategy_picker`) a `strict_initiative_order`: gracz obecny w `state.players`, ale nieobecny w niepustym `seating_order` jest cicho pomijany przy kompletności, a potem wymagany przy inicjatywie; realna ścieżka to God-Mode (`edit_player`/patch). (2) **confirmed** — frontendowy priorytet źródeł w `strategyCards.ts` to logika wyboru wariantu kart duplikowana poza backendem; to dług, który bot AI będzie musiał rozwiązywać niezależnie. (3) **likely** — `next_strategy_picker` łapie `ValueError` z `pick_count` i zwraca `None`, przez co przy <3 graczach `/round/next` pominie guard akumulacji i przejdzie, zamiast odrzucić.

**Verdict**: NEEDS_CHANGES

## High-level view

Egzekucja reguł wyboru siedzi w całości w `core/strategy_phase.py` jako czyste funkcje nad `GameState`, a `turn_flow.next_phase` jest jedyną bramą przejścia STRATEGY→ACTION i woła `ensure_strategy_complete` na `state` przed klonowaniem — przy błędzie faza zostaje nietknięta. To dobry, spójny wzorzec sędziego i jest bezpośrednio wywoływalny przez przyszłe `ai/` bez HTTP.

Spójność pojęć kolejności jest najsłabszym punktem. `next_strategy_picker` i `ensure_strategy_complete` iterują `speaker_order` (oparte na `seating_order`), a `strict_initiative_order` iteruje `state.players`. Gdy te dwa zbiory się rozjadą (realne tylko przez God-Mode), kompletność może zostać uznana za spełnioną dla gracza, który i tak zablokuje `strict_initiative_order` albo odwrotnie — zostanie pominięty w wyborze.

Obsługa liczby graczy spoza 3–8 jest niejednolita: `pick_count` rzuca, ale `next_strategy_picker` ten błąd połyka i zwraca `None`. To sprawia, że guardy zbudowane na „czy jest jeszcze picker" (akumulacja TG, pośrednio kompletność) interpretują niepełny set jako „faza zakończona".

API jest cienkie i poprawnie mapuje `ValueError`→422. Jedyny zgrzyt warstwowy to `_ensure_card_fields_complete` w routerze `strategy.py` — to walidacja danych rejestru (reguła inicjalizacji R6.4), która według zasad projektu należy do `core/` obok `validate_strategy_card_set`, bo i bot będzie jej potrzebował.

Frontend `strategyCards.ts` wprowadza własny ranking źródeł i fallback grafiki. Działa i jest dobrze udokumentowany, ale to reguła wyboru wariantu żyjąca w prezentacji, podczas gdy backend ma już `strategy_card_set("pok")` jako kanoniczne źródło. Rozjazd priorytetów front/back jest możliwy i bot nie skorzysta z tej logiki.

Pokrycie testami nowych reguł backendu jest solidne (kolejność, limit, druga runda od mówcy, guard akumulacji, walidacja zestawu). Brakuje testu dla rozjazdu `seating_order`↔`players` oraz dla ścieżki `/round/next` przy liczbie graczy spoza 3–8.

<details>
<summary>Issues (7)</summary>

1. **Rozjazd speaker_order↔players** (confirmed) — `ensure_strategy_complete`/`next_strategy_picker` liczą po `speaker_order` (z `seating_order`), a `strict_initiative_order` po `state.players`. Gracz w `players`, ale spoza niepustego `seating_order` jest pomijany przy kompletności i wymagany przy inicjatywie. Ujednolicić źródło zbioru graczy albo twardo walidować zgodność `seating_order == set(players)` przy przejściu STRATEGY→ACTION.
2. **next_strategy_picker połyka błąd liczby graczy** (likely) — przy <3 lub >8 graczy zwraca `None`, przez co `accumulate_unpicked_tg` (guard „czy jest picker") i inne ścieżki traktują niepełny set jako fazę zakończoną. Rozważyć propagację błędu albo osobny stan „faza nieobsługiwana".
3. **`/round/next` nie waliduje kompletności wprost** (likely) — polega na guardzie w `accumulate_unpicked_tg`, który z kolei polega na `next_strategy_picker`. Przy liczbie graczy spoza 3–8 guard nie zadziała (patrz #2) i runda przejdzie. Dodać jawną walidację lub test.
4. **Walidacja pól karty w routerze** (confirmed) — `_ensure_card_fields_complete` w `api/routers/strategy.py` to reguła danych rejestru (R6.4), która wg zasad projektu należy do `core/` obok `validate_strategy_card_set`. Przenieść do `core/`, by bot/`ai/` też ją miał.
5. **Priorytet źródeł kart na froncie** (confirmed) — `strategyCards.ts` implementuje ranking te>pok>codex>base + fallback grafiki; to reguła wyboru wariantu duplikowana poza backendem (`strategy_card_set`). Dług: rozjazd priorytetów front/back i brak reużycia przez bota. Rozważyć, by backend zwracał kanoniczny wariant + URL grafiki.
6. **Brak gwarancji przejścia, gdy picker ustawiony poza kolejnością** (possible) — `pick_strategy_card` waliduje `player_id == next_strategy_picker(state)`, ale `active_player_id` może być nadpisany przez God-Mode/`set_speaker`; picker liczony jest zawsze od mówcy, więc rozjazd `active_player_id`↔realny picker może mylić front. Zweryfikować, czy front zawsze czyta pickera z `next_strategy_picker`, nie z `active_player_id`.
7. **Brak testu rozjazdu i ścieżki brzegowej liczby graczy** (confirmed) — brak testu dla #1 i #2/#3. Dodać testy jednostkowe.

</details>

<details>
<summary>Details</summary>

### Rozjazd active_player_id ↔ realny picker

Walidacja `player_id != next_strategy_picker(state)` opiera się wyłącznie na `speaker_order` i liczbie kart, nie na `active_player_id`. To celowo odporne na nadpisanie aktywnego gracza, ale oznacza, że `active_player_id` i realny picker mogą się rozjechać (np. po `set_speaker` w trakcie wyboru). Front w `StrategyCardTable` czyta pickera z `gameState.activePlayer` (kolor), nie z osobnego sygnału „kto wybiera". Jeśli backend nie utrzymuje `active_player_id == next_strategy_picker` po każdej operacji God-Mode, picker pokazany na stole może nie zgadzać się z tym, kogo zaakceptuje `pick_strategy_card`. Warto potwierdzić, że wszystkie ścieżki zmiany stanu w fazie strategii przeliczają `active_player_id` (pick/reset/next_round to robią; `set_speaker`/`edit_player` — do sprawdzenia).

### Asymetria kolejności: speaker_order vs strict_initiative_order

To najważniejsze znalezisko. Dwa pojęcia zbioru graczy współistnieją w przejściu STRATEGY→ACTION:

```
next_phase(STRATEGY):
  ensure_strategy_complete(state)        # iteruje speaker_order(state)  → z seating_order
  ...
  strict_initiative_order(new_state)[0]  # iteruje state.players         → wszyscy gracze
```

`speaker_order` filtruje do graczy obecnych w `seating_order` (lub, gdy puste, `sorted(players)`). `strict_initiative_order` iteruje `state.players` wprost i wymaga, by KAŻDY miał kartę. Rozjazd powstaje, gdy `seating_order` jest niepuste, ale nie zawiera wszystkich graczy z `players`:

- gracz w `players`, poza `seating_order` → `ensure_strategy_complete` go nie sprawdzi (kompletność „przejdzie" mimo że nie ma kart), ale `strict_initiative_order` rzuci `ValueError("Gracz X nie ma przypisanej karty strategii.")` — przejście padnie na 422 z mylącym komunikatem;
- w wariancie odwrotnym (gracz ma karty, ale poza `seating_order`) `next_strategy_picker` nigdy go nie wskaże, więc nie dobierze kart w normalnym flow.

Normalna ścieżka tworzenia gry (`game.py` `create`/add-player) dba o `seating_order == players`, więc w czystym flow problem się nie ujawnia. Realna droga do rozjazdu to God-Mode: `board_edit.edit_player` i patch dodają/nadpisują `new_state.players[player_id]` bez dotykania `seating_order`. Ponieważ God-Mode celowo omija walidację reguł, sam akt dodania gracza jest OK — ale przejście fazy przez `/phase/next` już przechodzi przez sędziego i powinno dać spójny, czytelny błąd. Sugestia: albo jedno źródło zbioru graczy dla obu funkcji, albo w `next_phase` (lub w `ensure_strategy_complete`) twarda kontrola `set(seating_order) == set(players)` z własnym komunikatem, zanim dojdzie do `strict_initiative_order`.

### Obsługa liczby graczy spoza 3–8 jest niejednolita

`pick_count` rzuca `ValueError` przy <3 lub >8. Ale `next_strategy_picker` łapie ten błąd i zwraca `None`:

```python
try:
    needed = pick_count(state)
except ValueError:
    return None
```

Konsekwencja: wszystko, co pyta „czy jest jeszcze picker", interpretuje niepełny set jako fazę zakończoną. Dotyczy to `accumulate_unpicked_tg`, którego guard brzmi `if next_strategy_picker(state) is not None: raise`. Przy 2 graczach guard nie zadziała → `/round/next` wykona akumulację i przejdzie rundę zamiast odrzucić nieobsługiwaną liczbę graczy. `ensure_strategy_complete` jest tu bezpieczniejsze, bo woła `pick_count` bezpośrednio (propaguje błąd), ale to oznacza, że dwie funkcje w tym samym module traktują ten sam warunek brzegowy przeciwnie. Intencja z docstringa `next_strategy_picker` (nie psuć wywołań z niepełnym setem w God-Mode/setupie) jest zrozumiała, ale skutkuje tym, że guard akumulacji jest fałszywie „spełniony". Sugestia: rozdzielić „faza zakończona" od „faza nieobsługiwana przy tej liczbie graczy" — np. guard akumulacji powinien sam zawołać `pick_count` (jak `ensure_strategy_complete`), a nie wnioskować z `None`.

### Walidacja pól karty w routerze zamiast w core

`validate_strategy_card_set` żyje w `core/` (komplet 8 kart, zakres 1–8, brak duplikatów, czytane z rejestru) i jest dostępne dla bota. Natomiast `_ensure_card_fields_complete` (komplet pól per karta: nazwa, primary, secondary, kolor — R6.4) siedzi w `api/routers/strategy.py`. To ta sama klasa reguły (spójność danych inicjalizacji fazy), tyle że na poziomie pól. Trzymanie jej w routerze łamie zasadę „reguła w `core/`, endpoint cienki": gdy `ai/` będzie budować pulę kart, dostanie `validate_strategy_card_set`, ale nie kontrolę pól. Sugestia: przenieść `_ensure_card_fields_complete` do `core/strategy_phase.py` (jako część `validate_strategy_card_set` lub osobną czystą funkcję), a router niech tylko woła i mapuje błąd.

### Frontendowy priorytet źródeł kart — dług warstwowy

`strategyCards.ts` wprowadza `SOURCE_PRIORITY = [thunders_edge, pok, codex4..1, base]`, `sourceRank`, `variantsByPriority`, `fallbackImageURL`, `withImageFallback` i zmienia `getStrategyCardByInitiative` tak, że przy braku jawnej mapy wybiera wariant o najwyższym priorytecie źródła i uzupełnia grafikę z niższego źródła, gdy wyższe jej nie ma (np. te4construction treść, pok4construction grafika).

Sam fallback grafiki (treść z wyższego źródła, obraz z niższego, gdy pusty) to czysta prezentacja i jest OK. Problem to **wybór wariantu karty wg priorytetu źródeł**: to reguła („który wariant Construction/Warfare obowiązuje przy wielu włączonych dodatkach", RULES.md 14), a backend ma już kanoniczne źródło zestawu — `registry.strategy_card_set("pok")` zwraca uporządkowaną listę i `/strategy/cards` ją serializuje. Trzymanie równoległej logiki wyboru wariantu na froncie oznacza dwa źródła prawdy: jeśli kiedyś zmieni się aktywny zestaw albo priorytet źródeł, backend i front mogą pokazać różne warianty. Dla bota ta logika jest bezużyteczna (bot nie czyta TS). Sugestia (dług, nie blocker): niech backend zwraca kanoniczny wariant każdej karty (id + imageURL, już ma dostęp do pól assetów), a front tylko renderuje; ranking źródeł zostaje po stronie `core/registry`, spójnie z `enabled_sources.json`.

### Pokrycie testami

Pokryte: `pick_count` pośrednio przez sekwencje, kolejność i limit w `pick_strategy_card`, druga runda od mówcy, guard `accumulate_unpicked_tg` (wymaga zakończonego wyboru), domknięcie do `None`, `validate_strategy_card_set` (zła liczba, poza zakresem, duplikat), przejście STRATEGY→ACTION z kompletem kart. 262 testy zielone.

Not tested: (a) rozjazd `seating_order`↔`players` i jego wpływ na `ensure_strategy_complete` vs `strict_initiative_order`; (b) ścieżka `/round/next` oraz `accumulate_unpicked_tg` przy liczbie graczy spoza 3–8 (gdzie `next_strategy_picker` zwraca `None` i guard nie zadziała); (c) spójność `active_player_id` z `next_strategy_picker` po `set_speaker`/God-Mode w trakcie wyboru.

</details>

<details>
<summary>Mapa plików</summary>

- `src/core/strategy_phase.py` — `pick_count`, przebudowa `next_strategy_picker` wg Pick_Count, `ensure_strategy_complete`, walidacja kolejności/limitu w `pick_strategy_card` (+sortowanie kart), guard w `accumulate_unpicked_tg`, `validate_strategy_card_set`.
- `src/core/turn_flow.py` — `strict_initiative_order`, walidacja STRATEGY→ACTION w `next_phase` (`ensure_strategy_complete` + twarda inicjatywa).
- `src/api/routers/flow.py` — `/phase/next` i `/round/next` owinięte w try/except → 422.
- `src/api/routers/strategy.py` — guard `/strategy/cards` (`validate_strategy_card_set` + `_ensure_card_fields_complete`), mapowanie na 422.
- `src/api/web_data.py` — `_safe_pick_count`→`strategyPickCount`, pełne nazwy frakcji w displayName/flexibleDisplayName, `_tile_production` (poboczne względem fazy strategii).
- `frontend/src/entities/lookup/strategyCards.ts` — priorytet źródeł (te>pok>codex>base) + fallback grafiki.
- `frontend/src/domains/game-shell/components/StrategyCardTable/*`, `PhaseTransitionBanner/*` — prezentacja (nakładka kart, baner przejścia faz).
- `frontend/src/pages/StartScreen.*` — quick reference frakcji, nazwy graczy.
- `frontend/src/entities/data/types.ts` — pole `strategyPickCount` w `GameState`.
- `tests/test_strategy_phase.py`, `tests/test_turn_flow.py`, `tests/test_web_data.py`, `tests/test_api.py` — testy nowych reguł.

Pełny diff: `git diff 921b670~1 HEAD`.

</details>
