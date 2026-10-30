# Postęp projektu — Custodian Engine

Plik śledzi stan prac między sesjami. Aktualizowany na koniec każdego bloku.
Starsze, ukończone bloki (Faza 1 → E4·UI²) są w `PROGRESS_ARCHIWUM.md`.

> **Aktualny etap:** E8 — przejście na silnik-SĘDZIA (egzekucja reguł) + okna czasowe.
> Plan zadań: `PLAN_PELNA_ROZGRYWKA.md` („E8"); reguły: `RULES.md` 29.

## Status etapów silnika

| Etap | Zakres | Status |
|---|---|---|
| Faza 1 | Cyfrowa plansza + God-Mode (dane, mapa, setup, edycja, Undo) | ✅ ukończona |
| F0–F18 | Migracja na frontend ti4_web + panele graczy + God-Mode UI | ✅ ukończone |
| E1–E2 | Fazy + kolejność tur + faza strategii | ✅ ukończone |
| E3 | Akcja taktyczna (aktywacja, ruch, walka, inwazja, produkcja) | ✅ fundament |
| E4 | Kontrola komponentów (exhaust/refresh) + menu RMB | ✅ ukończone |
| E8 | Silnik-SĘDZIA: walidacja reguł + okna czasowe (T1–T3 done) | 🔧 w toku |

> Pełna historia ukończonych bloków ze szczegółami: `PROGRESS_ARCHIWUM.md`.

---

### ✅ Blok E4·UI³ — menu RMB w player-area przy mapie + „Aktywuj system" na kafelku

**Uwagi użytkownika + co zrobione:**

1. **Menu RMB (wyczerp/odśwież) też w player-area przy mapie.** Wcześniej przewiercony był
   tylko `PlayerCardDeck`. Teraz `playerId` (`discordId`) leci też do dwóch pozostałych
   wariantów panelu gracza: `PlayerCardSidebar` (panel boczny osadzony przy mapie — to „player
   area w menu mapy") i `PlayerDeckRow` (wiersz deck). W `PlayerDeckRow` techy idą przez
   `TechGridMobile`, więc dodano mu prop `playerId` przekazywany do `buildTechElementsForType`.
   Efekt: RMB wyczerp/odśwież na planetach/tech/liderach działa we wszystkich panelach gracza.
   (Uwaga: `PlayerStatsArea` na heksach mapy NIE renderuje planet/tech/liderów — tylko
   statystyki — więc tam nic nie dodawano.)

2. **„Aktywuj system" pod RMB na kafelku.** `MapTile` dostał `onContextMenu` → menu z pozycją
   „Aktywuj system", która woła `activateSystem(position)` (POST `/tactical/activate`). Backend
   `core.tactical.activate_system` kładzie żeton dowodzenia AKTYWNEGO gracza w przestrzeni,
   ustawia `active_system` + krok `MOVEMENT`, zdejmuje 1 z puli taktycznej. Pozycja zablokowana,
   gdy brak aktywnego gracza (inaczej 422). Menu omija kafelki hyperlane/embedded; omija też
   tryb klikania (`activateMode`) — woła aktywację wprost (jak przycisk w panelu faz).

**Zweryfikowane E2E:** aktywacja 101 → `command_tokens=[p1]`, `active_system=101`,
`tactical_step=MOVEMENT`, `tactical_cc` 3→2. Reużyty komponent `shared/ui/ContextMenu`.

**QA:** frontend type-check + lint + build czyste; backend 193 testy zielone (bez zmian w tym
bloku — menu woła istniejące endpointy), ruff+mypy czyste. Reguła: RULES.md 27 (rozszerzona).

---

### 🔧 Blok E8-0 — zmiana kierunku na silnik-SĘDZIA + aktualizacja dokumentacji (w toku)

**Kontekst (ustalenie z użytkownikiem 2026-10):** projekt zmienia filozofię z „asystent stołu,
nie sędzia" na **silnik-SĘDZIA egzekwujący reguły TI4 przez kod**. Powody: (1) docelowy bot AI
i tak musi znać i respektować reguły; (2) egzekucja jest wygodniejsza dla gracza (user friendly);
(3) gra przestaje zakładać fizycznie rozłożoną planszę. God-Mode ZOSTAJE jako osobny kanał ręcznej
korekty omijający walidację. Dodajemy OKNA CZASOWE (timing windows) — np. zagranie karty strategii
otwiera pozostałym graczom okno na secondary. Tryb: solo vs boty + hot-seat (docelowo moduł sieciowy),
więc okna pytają graczy po kolei.

**Ustalenia projektowe (z użytkownikiem):**
- Egzekucja idzie DALEKO (wszystkie reguły TI4), ale God-Mode zostaje jako wentyl.
- Walka: pełna, interaktywna (rzuty kośćmi z animacją) — docelowo. Pierwszy rdzeń: rzuty + liczenie
  trafień + okno „przypisz straty", wielorundowo; AFB/space cannon jako kolejne okna.
- Okna czasowe modelowane JEDNOLICIE: stos/okno w `GameState` + kolejka respondentów (`core/timing.py`).
- Kolejność reakcji (POTWIERDZONA przez użytkownika): od gracza po aktywnym, zgodnie z zegarem
  (speaker order); inicjator domyślnie pomijany. Dotyczy secondary i reakcji „when/after".
- `src/engine/` (puste, pod AI) — można przebudować dowolnie.
- E1–E3 działają → dobudowujemy walidację + okna NA ISTNIEJĄCYM, nie przepisujemy.

**Plan zadań E8 (pełny opis: PLAN_PELNA_ROZGRYWKA.md „E8"; reguły: RULES.md 29):**
T1 model okna → T2 ekspozycja w web-data + UI → T3 secondary kart strategii → T4 aktualny gracz
w STATUS/AGENDA + walidacja flow → T5 ruch (core) + walidacja → T6 walidacja aktywacji/planety/
produkcji → T7 walka-rdzeń → T8 walka w UI → T9 AFB + space cannon → T10 dokumentacja + memory.

**Zrobione w tym bloku (T10 częściowo — dokumentacja PRZED kodem, zgodnie z zasadą projektu):**
- [x] `docs/RULES.md` — nowa sekcja 29 (zmiana kierunku „sędzia" + zweryfikowany MODEL OKNA
  czasowego 29.2 ze źródłem LRR „Timing" + AsyncTI4 + potwierdzenie użytkownika; 29.3 aktualny gracz).
- [x] `docs/RULES.md` — sekcje 19–22 i 24 oznaczone bannerem „AKTUALIZACJA KIERUNKU": ich adnotacje
  „asystent, nie sędzia" są UNIEWAŻNIONE (treść zostaje jako referencja mechaniki TI4).
- [x] `docs/PLAN_PELNA_ROZGRYWKA.md` — decyzja E3 zaktualizowana (asystent → fundament pod sędziego),
  dodany etap E8 z listą zadań, sekcja statusu wskazuje E8 jako AKTUALNY.
- [x] `docs/PROGRESS.md` — ten wpis.

**DO ZROBIENIA (następne bloki):**
- [ ] Aktualizacja `.kiro/steering/custodian-engine.md` oraz `docs/README.md` o nowy kierunek
  (wzmianka, że silnik egzekwuje reguły; God-Mode = wentyl) — przy najbliższej okazji.
- [ ] Aktualizacja memory projektu `engine-is-table-assistant-not-referee` → nowy kierunek
  „sędzia + God-Mode jako wentyl" (wymaga narzędzia pamięci — do zrobienia, gdy dostępne).
- [ ] T1: implementacja `core/timing.py` + model okna w `GameState` (pierwszy blok kodu E8).

**QA:** ten blok to wyłącznie dokumentacja (brak zmian w kodzie) — testy backendu bez zmian
(193 zielone z poprzedniego bloku). Kod wejdzie od T1.

### ✅ Blok E8-T1 — model okna czasowego w stanie + core/timing.py (ukończony)

**Cel:** wprowadzić jednolite pojęcie „okno czasowe" (timing window) i „kto teraz reaguje"
do stanu gry — fundament interakcji między graczami (secondary kart strategii, przypisanie
strat w walce, space cannon, reakcje). Reguła modelu: RULES.md 29.2.

**Zrobione:**
- [x] `src/core/game_state.py`: enum `WindowType` (STRATEGY_SECONDARY, COMBAT_ASSIGN_HITS,
  SPACE_CANNON, REACTION) + model `TimingWindow` (queue, cursor, responded, context +
  właściwości `is_complete`, `current_responder`) + pole `GameState.pending_window`.
- [x] `src/core/timing.py` (NOWY): czyste funkcje `state->state`:
  - `build_response_queue(state, initiator, include_initiator=False)` — kolejka od gracza
    PO inicjatorze zgodnie z zegarem (speaker order z `seating_order`; fallback: sorted ids);
    inicjator pomijany lub na końcu;
  - `open_window(state, type, queue, context=)` — otwiera okno (odrzuca zagnieżdżanie);
  - `current_responder`, `respond_current` (waliduje kolejność — odpowiedź poza kolejnością
    → ValueError), `is_window_complete`, `close_window` (idempotentne).
  - Rozdział odpowiedzialności: `timing` = CZYSTA mechanika kolejki; efekty okna (zużycie
    żetonu, usunięcie jednostek) stosuje warstwa wyżej PRZED/PO `respond_current`.
- [x] `tests/test_timing.py` (NOWY, 16 testów): budowa kolejki (po inicjatorze, zawijanie,
  include_initiator, brak seating, inicjator spoza stołu), open/respond/close, błędy
  (zagnieżdżanie, poza kolejnością, brak okna, okno zakończone), round-trip serializacji.

**QA:** 209 testów zielonych (było 193, +16), ruff czysty, mypy --strict czysty.
Ostrzeżenie StarletteDeprecationWarning bez zmian (znane, nieblokujące).

**Następny krok:** T2 — ekspozycja `pending_window` w `web_data` + endpoint `POST /window/respond`
+ panel okna w UI (kto teraz reaguje + przycisk odpowiedzi).

### ✅ Blok E8-T2 — ekspozycja okna czasowego w web-data + endpointy + panel UI (ukończony)

**Cel:** gracz WIDZI otwarte okno czasowe (kto teraz reaguje) i może odpowiedzieć. Spina
model z T1 (core/timing) z frontendem.

**Backend:**
- [x] `src/api/web_data.py`: helper `_pending_window(state)` + pole `gameState.pendingWindow`
  w `_build_game_state`. Tłumaczy okno na kształt dla frontu: `windowType`, `currentResponder`
  (KOLOR gracza, jak `activePlayer`), `currentResponderId` (stabilny player_id do adresowania
  odpowiedzi), `queue` (kolory), `cursor`, `remaining`, `responded`, `context`, `isComplete`.
- [x] `src/api/schemas.py`: `WindowOpenRequest` (typ + queue LUB initiator), `WindowRespondRequest`
  (player_id + decision).
- [x] `src/api/routers/window.py` (NOWY): `POST /window/open` (narzędzie/testowe — wylicza kolejkę
  z inicjatora przez `build_response_queue` lub bierze jawną), `POST /window/respond`
  (`timing.respond_current`, poza kolejnością/brak okna → 422), `POST /window/close`. Router
  zarejestrowany w `app.py`.
- [x] `tests/test_window_api.py` (NOWY, 9 testów): web-data null domyślnie, open eksponuje
  respondenta jako kolor, respond przesuwa kolejkę, poza kolejnością/brak okna/zły typ/zagnieżdżanie
  → 422, close czyści, wszystkie typy okien akceptowane.

**Frontend:**
- [x] `entities/data/types.ts`: typ `PendingWindow` + pole `GameState.pendingWindow`.
- [x] `api/useBoardEditor.ts`: akcje `respondWindow(playerId, decision?)` i `closeWindow()`
  (POST + invalidate web-data → panel odświeża się natychmiast).
- [x] `domains/game-shell/components/GameStatePanel.tsx`: komponent `WindowSection` renderowany
  NA GÓRZE `PlateBody` (okno reakcyjne ma priorytet). Baner „Reaguje: <gracz>" (spójny z pickerem
  fazy strategii), licznik „Pozostało w kolejce", przyciski „Wykonaj"/„Pas" (adresują
  `currentResponderId`); po zakończeniu kolejki przycisk „Zamknij okno". Etykiety typów okien PL.

**Rezultat (zweryfikowany E2E):** open (initiator p1, 3 graczy) → kolejka green,blue (p1 pominięty);
respond green → responder blue; respond blue → isComplete; close → null. Decyzje w T2 to etykiety
(„secondary"/„pass") — efekty konkretnych okien dojdą od T3.

**QA:** backend 218 testów zielonych (było 209, +9), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste. Warn o rozmiarze chunku i StarletteDeprecationWarning bez zmian.

**Następny krok:** T3 — pierwsze realne okno: secondary karty strategii. Zagranie karty otwiera
pozostałym graczom okno; respond dla secondary zużywa żeton strategiczny / pas. Potrzebne
potwierdzenie reguł primary/secondary konkretnej karty (RULES.md — do uzupełnienia ze źródła).

### ✅ Blok E8-T3 — pierwsze realne okno: secondary karty strategii (ukończony)

**Cel:** zagranie karty strategii rozstrzyga PRIMARY aktywnego gracza i OTWIERA okno
secondary dla pozostałych (kolejka po kolei). Pierwsza realna mechanika na modelu okien
(T1/T2). Reguła: RULES.md 30 (źródło: lokalny LRR 2.0 `docs/rules_tirules/R_strategic_action.md`
+ `R_leadership.md`; parametry z `assets/data/strategy_cards/pok.json`).

**Zakres (świadomy szkielet — „make it exist first", z haczykami pod rozbudowę):**
- Leadership primary: +3 żetony dowodzenia (do puli taktycznej — ⚠️ ZAŁOŻENIE: docelowo wybór puli).
- Secondary: mechanika okna (kolejka, wykonaj/pas) działa end-to-end; efekt „wykonaj" to
  NA RAZIE NO-OP (kupno żetonów za wpływ odłożone do modelu wpływu — jawne TODO w kodzie).
- Pozostałe karty: dispatch zwraca „brak efektu" — szkielet okna i tak działa.

**Backend:**
- [x] `src/core/strategic_action.py` (NOWY): `play_strategy_card` (primary dispatch + exhaust
  karty + otwarcie okna STRATEGY_SECONDARY z kolejką pozostałych), `resolve_secondary`
  (dispatch secondary + `timing.respond_current` + auto-zamknięcie po dopełnieniu).
  DISPATCH po inicjatywie (`_PRIMARY_EFFECTS`/`_SECONDARY_EFFECTS`) — rozszerzalny kartą po
  karcie, nie `if` w endpointcie. Kontekst okna niesie `initiative`.
- [x] `src/api/schemas.py`: `StrategySecondaryRequest` (player_id + execute).
- [x] `src/api/routers/strategy.py`: `/strategy/play` przekierowane na `strategic_action`
  (primary + okno; zastępuje dawne „tylko oznacz zagraną"); nowy `/strategy/secondary`.
- [x] `tests/test_strategic_action.py` (10) + `tests/test_strategic_action_api.py` (4).

**Frontend:**
- [x] `api/useBoardEditor.ts`: akcja `strategySecondary(playerId, execute)`.
- [x] `GameStatePanel.tsx` `WindowSection`: przyciski Wykonaj/Pas routowane po TYPIE okna —
  STRATEGY_SECONDARY → `/strategy/secondary` (efekt + kolejka), inne → generyczny `/window/respond`.

**Rezultat (zweryfikowany E2E):** play Leadership (p1) → tactical_cc 3→6, karta zagrana, okno
secondary queue [green,blue] responder p2; secondary p2(exec)→p3, p3(pass)→okno zamknięte (null).

**QA:** backend 232 testy zielone (było 218, +14), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T4 — pojęcie aktualnego gracza w STATUS/AGENDA + twarda walidacja flow
(czyja tura / co teraz wolno). Potem pozostałe karty strategii i model wpływu (odblokuje
realne secondary).

### ✅ Blok E8-T4 — twarda walidacja flow fazy akcji + aktywny gracz (ukończony)

**Cel:** pierwszy element „sędziego" (RULES.md 29.1) — zwykłe akcje flow walidowane TWARDO.
Reguła: RULES.md 31 (źródło: lokalny LRR 2.0 — R_active_player, R_action_phase, R_initiative_order,
R_status_phase, R_agenda_phase).

**Korekta względem pierwotnego zamysłu T4 (wymuszona regułą):** LRR mówi wprost „during the
strategy, status and agenda phases, NO player is the active player". Dlatego NIE wprowadzamy
sztucznego „aktywnego gracza" w STATUS/AGENDA — `active_player_id` pozostaje None (tak jak było).
Kolejność czynności w tych fazach to KOLEJKA (initiative dla statusu, speaker order dla agendy),
która wejdzie w etapach E5/E6 na modelu okien czasowych. T4 kładzie fundament + walidację akcji.

**Backend:**
- [x] `src/core/turn_flow.py`: `_require_action_turn` (faza ACTION + tożsamość aktywnego gracza);
  `end_turn(state, player_id=None)` i `pass_turn(state, player_id=None)` walidują twardo
  (ValueError). `pass_turn` dodatkowo: nie wolno pasować przed akcją strategiczną (gracz z kartą
  musi ją zagrać — `exhausted_strategy_cards`). Alias `initiative_order = turn_order` (status).
  God-Mode omija (osobny kanał). `player_id=None` zachowuje zgodność wsteczną (faza wciąż sprawdzana).
- [x] `src/api/schemas.py`: `TurnActionRequest` (opcjonalny player_id).
- [x] `src/api/routers/flow.py`: `/turn/end`, `/turn/pass` przyjmują body z player_id, mapują
  ValueError → 422.
- [x] `tests/test_turn_flow.py`: fixture gra z ZAGRANYMI kartami (by móc pasować) + 5 nowych
  testów walidacji (zła faza, cudza tura, pas przed akcją strategiczną, pas bez karty dozwolony,
  alias inicjatywy).

**Frontend:**
- [x] `api/useBoardEditor.ts`: `endTurn(playerId?)`/`passTurn(playerId?)` wysyłają player_id.
- [x] `GameStatePanel.tsx`: `PhaseControls` dostaje `activePlayerId` (z `active.discordId`) i
  przekazuje go do endTurn/passTurn — backend waliduje, że to tura tego gracza.

**Rezultat (zweryfikowany E2E):** p2 kończy turę p1 → 422; p1 pasuje bez akcji strategicznej →
422; p1 kończy turę → 200, aktywny p2; end/pass w fazie statusu → 422.

**QA:** backend 237 testów zielonych (było 232, +5), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T5 — ruch jako funkcja core (`core/movement.py`) + walidacja legalności ruchu
(zasięg z UnitDef, anomalie/przejezdność, aktywny system). Pierwsza twarda egzekucja mechaniki
taktycznej.
