# Postęp projektu — Custodian Engine

Plik śledzi stan prac między sesjami. Aktualizowany na koniec każdego bloku.
Starsze, ukończone bloki (Faza 1 → bloki do 2026-11-14) są w `PROGRESS_ARCHIWUM.md` (czytaj punktowo).

> **Aktualny etap:** E8 (silnik-SĘDZIA) + hooki: karty, relikty, technologie ogólne, cele, karty strategii,
> agendy ✅; frakcje (Fala 2) w toku; bot: B0–B1, B3 ✅, B2 rdzeń, następne B2 (bench) / B5 (`docs/bot/PLAN.md`).
> Stan pokrycia: `POKRYCIE_HOOKOW.md` (generowany). Reguły: `RULES.md` 29, 43, 53, 65.

## Status etapów silnika

| Etap | Zakres | Status |
|---|---|---|
| Faza 1 | Cyfrowa plansza + God-Mode (dane, mapa, setup, edycja, Undo) | ✅ ukończona |
| F0–F18 | Migracja na frontend ti4_web + panele graczy + God-Mode UI | ✅ ukończone |
| E1–E2 | Fazy + kolejność tur + faza strategii | ✅ ukończone |
| E3 | Akcja taktyczna (aktywacja, ruch, walka, inwazja, produkcja) | ✅ fundament |
| E4 | Kontrola komponentów (exhaust/refresh) + menu RMB | ✅ ukończone |
| S | Karty strategii 1–8: primary + secondary (`core/strategy_cards/`) | ✅ ukończone |
| E8 | Silnik-SĘDZIA: walidacja reguł + okna czasowe (T1–T7 + faza akcji 31.7/31.8, audyt 31.9) | 🔧 w toku |
| C | Punkty centralne C1–C9 (strażnik architektury) | ✅ ukończone |
| H1–H3 | Hooki: rejestr, punkty MODIFY/PERMIT/FORBID, raport pokrycia | ✅ ukończone |
| H1b | Reakcje z cofnięciem: hold-play (Sabotage) + hold-rewind (HOLD) | ✅ (RULES.md 53.6, 53.7) |
| H4 | Karty akcji: ACTION + reakcje w oknach + przeciąganie z ręki | ✅ 143/143 |
| — | Relikty (23/23 aktywnych), technologie ogólne (33/33), cele (80/80 automatycznie) | ✅ |
| E6 | Faza agendy (głosowanie, remis, prawa); efekty agend | ✅ cała faza + efekty talii oficjalnej (50/50); ⬜ Absol (60) |
| H5 | Frakcje: zdolności, liderzy, notki, przełomy, technologie frakcyjne | ⬜ (technologie 36/102) |
| N | Sieć: N0 `actor_id` ✅, N1 tokeny ✅, N2 projekcja ✅, N3 zapis ✅, N5 część 1 ✅; N4 współbieżność ⬜ | 🔧 |
| QA | pytest-xdist/testmon, E2E Playwright (solo + host/gość) | ✅ |

**Następne kroki (kolejność):** efekty agend Absol → hooki at_start/at_end/during (16 zdarzeń jeszcze nieemitowanych,
`OKNA_CZASOWE.md`) → frakcje (zdolności, liderzy, promissory notes) → N4/N5 część 2 → bot.

> Pełna historia ukończonych bloków ze szczegółami: `PROGRESS_ARCHIWUM.md`.

---

### ✅ Zegar szachowy graczy (2026-11-11) — RULES.md 58
- Backend: `core/game_clock.py` (holder, `settle`, pauza, `snapshot`), `GameState.clock`, rozliczanie w
  `StateService.replace_state`, `POST /clock/pause|resume`, `chess_clock` w `/game/new`, `chessClock` w web-data.
- Front: Ustawienia → „Chess clock” (pula minut + dodatek s), pasek `domains/clock/ChessClockPanel` nad mapą
  (pozostały czas każdego gracza, czas tury holdera, pauza). Testy: `tests/test_game_clock.py`, `clockMath.test.ts`.
- Poprawka po uwadze użytkownika: pasek w widoku mapy (przesuwalny), start/wyłączenie zegara w TRWAJĄCEJ grze
  (Ustawienia → Current game, `/clock/configure|disable`) — wcześniej działał tylko od nowej gry, więc go nie było widać.
- Do decyzji użytkownika: kara za przekroczenie czasu (58.4), zasady dodatku (58.3).

### ✅ Baza zdarzeń i okien czasowych (2026-11-08) — RULES.md 54

`core/game_events.py` (zdarzenia + klasyfikator okien), `core/triggers.py` (fire, REPLACE, oferty, REACTION), `core/active_effects.py` (efekty trwałe), rozszerzony `rules_hooks` (`on_event`, źródła: relikt/lider/przełom/efekt), emisje wpięte w tury, fazy, walkę, inwazję, agendę, strategię, produkcję i inne. Katalog `docs/OKNA_CZASOWE.md` (740 komponentów, 123 agendy). Testy: `test_game_events.py`, `test_triggers.py`. Dalej: wpięcie pozostałych zdarzeń (`emitted_by=None`), efekty agend, kolejne karty ACTION.
### ✅ Zdjęcie żetonu Custodians w inwazji na Mecatol Rex (2026-11-08) — RULES.md 52
- Nowe: `core/custodians.py` (blokada lądowania, `remove_token`: 6 wpływu, +1 VP, `custodians_removed` => faza agendy),
  `invasion.claim_custodians`, `POST /tactical/invasion/custodians`, widok `custodians` w `GET /tactical/invasion`.
- UI: `CustodiansClaim` (baner + okno płatności `PaymentPicker`) w oknie inwazji i panelu pomocy; zablokowana karta Mecatol.
- Testy: `tests/test_custodians_invasion.py`.

### ✅ Hooki: źródła trwałe + karty akcji z oknem ACTION (2026-11-08) — RULES.md 53
- `rules_hooks`: źródła obejmują prawa w grze (`SOURCE_AGENDA`) i notki w strefie (`SOURCE_PROMISSORY`);
  `register_effect`/`effect_for` (efekty jednorazowe, IMPLEMENTED w rejestrze efektów); nowe punkty
  `agenda.vote_modifier` (podpięty w `agenda_phase.extra_votes`), `combat.extra_dice`, `combat.reroll_misses`.
- `core/action_cards.play_action_card` + `POST /action-card/play` (z `actor_id`): walidacja -> efekt na klonie -> odrzucenie.
  5 kart: Industrial/Economic/Mining Initiative, Frontline Deployment, Rise of a Messiah. Karta ACTION bez efektu =
  zagrana + `implemented=false` (⚠ założenie 43.3). Karty reakcji odrzucane do czasu STOP (43.4).
- Testy: `tests/test_action_cards.py`, rozszerzone `tests/test_rules_hooks_points.py`. Brak UI do zagrania karty
  z parametrami (front jeszcze woła tylko szkielet `/tactical/component-action`).
- **Przeciąganie karty z ręki + poprawka błędu:** dok ręki (`BottomHandDock`) pozwala przeciągnąć kartę akcji na strefę
  „Drop to play” (otwiera `ActionCardPlayModal`); podnieść można tylko kartę zagrywalną wg `GET /action-card/playable`
  (odświeżane co 3 s i po akcjach), pozostałe przyciemnione z powodem w podpowiedzi. Naprawiony błąd formularza:
  adres `/bot/api/...` (404) zamiast `/bot/...`; modal pokazuje teraz prawdziwy powód błędu. Nie testowane w przeglądarce.
- **UI zagrania karty akcji:** wybór karty z listy „Play a component action” otwiera `ActionCardPlayModal`
  (`frontend/.../TurnControls/`): formularz z `GET /action-card/{id}/inputs` (legalne opcje z silnika), zagranie przez
  `POST /action-card/play` (`useBoardEditor.playActionCard`); karta bez automatyzacji = komunikat „rozstrzygnij ręcznie”.
  Pliki: `api/useActionCard.ts` (+ test `useActionCard.test.ts`), `ActionCardPlayModal.tsx`. Nie testowane wizualnie w przeglądarce.
- **Druga paczka (11 kart):** Unexpected Action, Insubordination, Spy, Repeal Law, Impersonation, War Effort, Lucky Shot,
  Cripple Defenses, Plague, Refit Troops, Scuttle (`core/hooks/action_cards_units.py`, `action_cards_other.py`,
  wspólne pomocniki `card_helpers.py`). Nowe funkcje centralne: `command_tokens.remove_from_board`,
  `card_draw.take_random_action_card`, `agenda_phase.repeal_law`. Razem 16 z 143 kart akcji ma efekt.
- Nie ujęte: liderzy/relikty/przełom jako źródła hooków; efekty agend (prawa jako hooki) - następny blok.
- Dług: żetony na planszy (`SystemState.command_tokens`) nadal zmieniane też w `tactical`, `retreat`,
  `status_phase` - nie są w strażniku punktów centralnych (do domknięcia razem z hookami żetonów).

### ✅ Hooki: H1 + H2 (punkty MODIFY/PERMIT/FORBID) + H3 (raport pokrycia) (2026-11-08) — RULES.md 43
- **H2 dodatkowe punkty:** `movement.move_value`, `movement.pass_foreign_ships`, `combat.roll_modifier`, `production.value`,
  `production.cost`, `payment.commodities_as_trade_goods` (`economy.spendable_trade_goods`/`spend_as_trade_goods`).
  Testy par bez/z wyjątkiem: `tests/test_rules_hooks_points.py`.
- **H3:** `src/audit/hook_coverage.py` -> `docs/POKRYCIE_HOOKOW.md` (hooki, pokrycie per kategoria, wyzwalacze, obszary
  reguł wg słów kluczowych — heurystyka). Hook z `covers` => komponent IMPLEMENTED w `registry.effect_registry`
  (`effects_status.json` zostaje na jawne nadpisania, np. MANUAL). Testy: `tests/test_hook_coverage.py`.
- **NIE zrobione (świadomie):** H1b (STOP / punkty kontrolne) — wymaga zmian w `event_store.py`/`state_service.py` i
  potwierdzenia założeń z RULES.md 43.4; TRIGGER/REPLACE/PERSISTENT i okna; H4-H6 to treść (karty, frakcje, agenda).

### Hooki H1 + pierwsze punkty H2 (2026-11-08) — RULES.md 43
- Nowe: `core/rules_hooks.py` (rejestr, kolejność REPLACE>FORBID>PERMIT>MODIFY>TRIGGER>PERSISTENT, hook działa tylko
  dla posiadacza źródła: frakcja/technologia), `core/hooks/factions_base.py`, `core/hooks/technologies.py`.
- Migracja bez zmiany zachowania: Arborec (`production.forbidden_types(state, player_id, type)`) i Antimass
  (`movement._can_enter_asteroids`, używane też przez `retreat.py`). Testy: `tests/test_rules_hooks.py`.
- Następne punkty zaczepienia: walka (`roll_modifier`, reroll), status/agenda, koszt produkcji, ruch (`move_value`);
  potem H3 (raport pokrycia + `effects_registry`).

### 🔧 Faza C — punkty centralne (refaktor bez zmiany zachowania) — C1–C9 gotowe
- **C9 ✅ (2026-11-08):** `core/secret_objectives.py`, `core/promissory_notes.py`, `core/relic_fragments.py`,
  `card_draw.rearrange_agenda_top`; `OWNERS` w strażniku rozszerzone o 14 pól (agendy, tajne cele, PN, fragmenty,
  talie eksploracji, `purged`, attachmenty, przełom). Zachowanie bez zmian (873 testy, ruff, mypy zielone).
  Następny krok: H0–H2 (`core/rules_hooks.py`). Otwarte: logika w `api/` (etap sieciowy).
Plan i audyt: `PLAN_PELNA_ROZGRYWKA.md` („OSTATECZNY PLAN KOLEJNOŚCI", „Audyt miejsc rozproszonych"); zasada: `RULES.md` 43.1a.
- **C1 ✅ Ekonomia (trade goods / commodities):** nowy `core/economy.py` (`gain/spend_trade_goods`, `gain/spend_commodities`,
  `replenish_commodities`, `convert_commodities_to_trade_goods`, `give_to_player`, `commodity_gap`). Przepięto: `payment.apply_payment`
  (wydanie TG), `production.produce` i `objective_payment` (wydanie przez `apply_payment`), `exploration`, `transaction`,
  `strategy_phase` (TG z karty), `strategy_cards/trade`. Poza `economy.py` i God-Mode nikt nie zapisuje `trade_goods`/`commodities`.
  Jedyna zmiana zachowania: wydanie więcej TG niż gracz ma → `ValueError` (wcześniej licznik mógł zejść poniżej 0 w ścieżkach „nie do osiągnięcia").
- **C2 ✅ Żetony dowodzenia:** nowy `core/command_tokens.py` (rezerwa `cc_reinf` + pule `tactical/fleet/strategic`; ruchy:
  `spend_from_pool`, `spend_to_reinforcements`, `take_from_reinforcements`, `return_to_reinforcements`, `add_to_pool`,
  `gain_from_reinforcements`, `set_pools`). Przepięto: `tactical` (aktywacja), `strategic_action` (koszt secondary), `status_phase`
  (kroki 4–5, redistribute, tryb testowy), `objective_payment`, `retreat`, `exploration`, karty `diplomacy`/`warfare`/`common`/`leadership`.
- **C3 ✅ Wyczerpywanie:** nowy `core/exhaust.py` (`exhaust_planets`, `ready_planets`, `ready_all_planets`, `exhaust_technology`,
  `ready_all_technologies`). Przepięto: `payment`, `technology.apply_research`, `invasion` (utrata/zdobycie planety),
  `status_phase.finalize_status`, `exploration`, `strategy_cards/common`.
- **C3 (uzupełnienie) ✅ Liderzy, karty strategii, przełom:** `core/exhaust.py` rozszerzony o `exhaust_strategy_card`/`ready_all_strategy_cards`
  (`strategic_action`, `strategy_phase`), `exhaust_leader`/`ready_all_leaders` i `exhaust_breakthrough`/`ready_breakthrough`
  (`status_phase`, krok 6). Uwaga: w grze liderzy są dziś wyczerpywani tylko God-Modem (brak akcji „użyj lidera"), więc `exhaust_leader`
  czeka na pierwszego wołającego (E4/E7).
- **C4 ✅ Kontrola planet:** nowy `core/control.py` (`set_planet_control(state, position, planet, owner|None)`): ustawia `planet_owners`,
  utrzymuje lustro `controlled_planets` obu graczy i zdejmuje znacznik wyczerpania poprzedniemu kontrolerowi. Przepięto: `invasion`
  (przejęcie i remis), `tactical.take_control`, `faction_setup` (planety domowe). Zdobywca nadal dostaje planetę wyczerpaną
  (decyzja `invasion`, nie `control`). Zmiana zachowania: `tactical.take_control` aktualizuje teraz też `controlled_planets`.
- **Strażnik C8 (częściowo):** `tests/test_central_points.py` (AST) pilnuje właściciela 13 pól (TG, commodities, 4 pola żetonów,
  5 pól wyczerpania, `planet_owners`, `controlled_planets`); wykrywa przypisania (także krotkowe), zapis/`del` po kluczu, mutacje kolekcji
  (`append`/`remove`/`update`…) i `setattr` poza listą dozwolonych modułów. Kolejne pola dopisujemy do `OWNERS`.
- Zmiany zachowania (tylko ścieżki „nie do osiągnięcia" po wcześniejszej walidacji): zdjęcie żetonu/TG ponad stan i zdobycie żetonu przy
  pustej rezerwie → `ValueError` zamiast liczby ujemnej.
- **C5 ✅ Jednostki:** nowy `core/unit_ops.py` (`place_units`, `take_units`, `remove_units`, `transfer_units`, `replace_zone_units`,
  `UnitCause` = PLACED/SETUP/MOVED/DESTROYED/REMOVED, żeby hook odróżniał zniszczenie od usunięcia i ruchu). Przepięto: `battle`
  (straty, AFB), `capacity`, `fleet_pool`, `retreat`, `movement` (ruch i flota z ładunkiem), `invasion` (lądowanie, struktury przy zdobyciu),
  `space_cannon`, `exploration` (piechota/mech/DMZ), `faction_setup`, `strategy_cards/common` (struktury), `production` (nie woła już
  God-Mode `board_edit.edit_units`; kontrolę planety przelicza `control.recompute_from_units`). `damage.py` jest właścicielem uszkodzeń
  (+`clear_zone_damage`). Zmiana zachowania: usunięcie jednostki (walka, space cannon, struktury przy zdobyciu) zawsze przycina uszkodzenia
  do liczby jednostek (wcześniej przycinał tylko odczyt).
- **C6 ✅ Technologie:** `technology.grant_technology` — jedyne miejsce zmiany `technologies` (badanie i „gain" idą przez nią).
- **C7 ✅ VP, karty akcji, mówca:** `objectives.award_points` (jedyne miejsce `victory_points`); `card_draw.py` ma `draw_action_card`,
  `discard_action_cards`, `seed_action_deck` (faza statusu, cel „fsn" i setup nie dotykają już ręki/talii wprost);
  `strategy_phase.set_speaker` (Politics, endpoint mówcy, setup).
- **C8 ✅ Strażnik z analizą aliasów:** `tests/test_central_points.py` łapie też zapis przez zmienną pomocniczą
  (`units = system.space_units.get(…); units[k] = …`, pętle po `.items()`), ma własne testy (formy zmiany i kopie/odczyty bez fałszywych alarmów)
  i sprawdza 22 pola. Zweryfikowany na starych wersjach plików sprzed refaktoru (wykrywa wszystkie dawne zapisy).
- **Katalog punktów zaczepienia hooków i lista C9 (czego świadomie nie ruszyłem):** `PLAN_PELNA_ROZGRYWKA.md`.
- Testy: `test_economy.py`, `test_command_tokens_exhaust.py`, `test_control.py`, `test_unit_ops.py`, `test_central_tech_cards.py`;
  pełny zestaw 869 testów, ruff, mypy zielone.
- **Dalej:** H0–H2 (szkielet hooków) albo C9 (pozostałe karty/zasoby) wg potrzeby.
  Uwaga: `production.available_budget`/`auto_pay` i `objective_progress` nadal CZYTAJĄ `trade_goods` na własny sposób (odczyt, nie zapis);
  do ujednolicenia razem z hookiem źródeł płatności w H2.

---

### ✅ Faza statusu (8 kroków) + cele publiczne/tajne + punkty zwycięstwa (ukończone)

- **Reguła (zweryfikowana):** `RULES.md` 41 ze źródłami `R_status_phase`, `R_objective_cards`,
  `R_victory_points`, `R_custodians_token`, `R_fleet_pool` (lokalny zrzut tirules2.com).
- **Setup (`/game/new`):** `core/objectives.setup_objectives` losuje 5 celów I + 5 celów II etapu,
  odkrywa 2 cele I etapu, rozdaje po 1 tajnym celu i tasuje talię kart akcji (talie wybierane z
  katalogu, bez hardkodowania id). Nowy stan: `GameState.objectives/decks/status/custodians_removed/
  vps_to_win/winner_id`, `PlayerState.scored_secrets`.
- **Silnik (`core/status_phase.py`):** krok 1 interaktywny (gracze wg inicjatywy, ≤1 publiczny + ≤1 tajny,
  kontrola planet domowych), kroki 2–4 automatem (odkrycie celu / koniec gry, karty akcji, zdjęcie
  żetonów + 2 nowe), krok 5 interaktywny (rozdział żetonów, raport nadwyżki fleet pool), kroki 6–7
  automatem (ready + naprawa), krok 8 przez `/phase/next` mówcy (zwrot kart → agenda przy zdjętym
  Custodians, inaczej nowa runda). Naprawa jednostek przeniesiona z wejścia w STATUS do kroku 7.
- **API/web-data:** `/status/{score,finish-scoring,redistribute}`; `objectives`, `scoreBreakdowns`,
  `gameState.status/winner`, `secretsScored` — istniejące moduły AsyncTI4 (tabele celów pod mapą,
  rozbicie punktów pod paskiem, panel Objectives) dostają teraz prawdziwe dane.
- **UI:** `StatusPhasePanel` (8 kroków, punktowanie, rozdział żetonów, zwycięzca); stare „Next player"
  w statusie ukryte, „Next phase" mówcy zablokowany do końca kroków.
- **Zmiana zachowania:** bez zdjętego Custodians status kończy rundę BEZ fazy agendy (zgodnie z
  regułą). Zdjęcie żetonu na razie God-Mode (`custodians_removed` w `/god-mode/patch`).
- **Sprawdzanie celów (iteracja 2):** `core/objective_progress.py` + `objective_payment.py` — progi i postęp dla
  wszystkich celów statusu (4 „ręczne": załączniki, fragmenty, prawa), twarda walidacja przy zdobywaniu,
  automatyczna płatność celów „Spend…". Panel statusu przebudowany (płyta + zagłębienie, lista celów z
  wymaganiem, postępem i przyciskiem Score), box „Other points" (Custodians) widoczny od startu.
- **⚠ Do potwierdzenia / następny blok:** setup daje 1 tajny cel bez wyboru z dwóch,
  limit ręki kart akcji niemodelowany, nadwyżka fleet pool tylko zgłaszana, zdjęcie Custodians w inwazji.
- **QA:** backend 640+ testów zielonych (`tests/test_status_phase.py`, `tests/test_status_api.py`),
  ruff + mypy czyste; front: eslint + build czyste, `tsc -p tsconfig.app.json` tylko 3 błędy bazowe.

---

## Audyt rulingów C_/F_ + pusta rezerwa → jednostka z planszy (2026-11-15)

- Zasada w CLAUDE.md: przy implementacji i przeglądzie zawsze `C_<typ>.md` / `F_<frakcja>.md` / `R_<temat>.md`;
  `⚠️ ZAŁOŻENIE` sprzeczne z rulingiem = błąd.
- `core/board_reinforcements.py` — JEDNO miejsce R_component_limitations (źródło z systemu bez żetonu gracza,
  wybór gracza). Produkcja: `ProductionOrder.sources`, `units[].boardSources`, chipy w `ProductionOverlay`.
  Użycia: Rearmament Agreement, Infiltrate, Local Fabricators, Sleeper Cell, Salvage Operations, struktury z kart.
- Agendy (C_agendas): Classified po odrzuceniu → cel nie do zdobycia (`objectives.retire`); Wormhole Research nie
  rusza struktur w przestrzeni; Search Warrant/Archived Secret — zwrot nadmiaru PO odkryciu kart; Colonial
  Redistribution — oferta „may”; Homeland Defense Act odrzucone → max 2 PDS; badania z agend i Technology Rider
  z pominięciem prerekwizytu specjalnością/AIDA (`technology.plan_with_skips`).
- Frakcje: G'hom Sek'kus nie przez zablokowane wormhole; Reclaimer — struktura za każdego; Pride of Kenara —
  rzut gravity rift. Eksploracja: DMZ otwiera CAPACITY. Relikty: Book of Latvinia tylko bez prerekwizytów.
- Otwarte (RULES.md 63.5): wybór wormhole przy Ion Storm w systemie z tym samym wormhole; JR-XS455-O — odpowiedź
  wskazanego gracza.
- Testy: `tests/test_rulings_audit.py` (19). QA: pytest pełny (2353), ruff, mypy src+tests; front tsc + eslint +
  vitest `domains/production`. Pominięte: build (bez nowych zależności), e2e (okno produkcji nie jest stale montowane).
- Uwaga: większość tej pracy weszła w commit równoległej sesji `46be583`; tu dokończenie (Technology Rider).

## Undo dla graczy (2026-11-16)

- `core/player_undo.py` + `GET/POST /undo/mine`: gracz cofa własny ostatni krok (krok po kroku), dopóki nikt inny
  nie działał, tura nie przeszła dalej, nie było kości/dobrania/zmiany fazy/zagrania karty, krok nie dotknął innego
  gracza i nie trwa pauza reakcji. RULES.md 44.7. Host: pełne Undo/Redo bez zmian.
- Autor kroku w historii: kolumna `author` w `EventStore` (migracja), `seats.current_author` z middleware tożsamości.
- Front: przycisk „Undo” obok „Hold” w doku ręki (`UndoControls`), wyłączony z powodem w `title`; feed `turn.undo`.
- Testy: `tests/test_player_undo.py`, `UndoControls.test.tsx`. Nowe trasy i kolumna — restart backendu.


## Agenda: Hack Election, Research Grant w oknie drzewa, opisy wyborów, panel dowódcy (2026-11-16)

- Hack Election: ⚠ zmiana z tego bloku była BŁĘDNA (stara wersja karty) — cofnięta w bloku niżej (TE Ω).
- Research Grant Reallocation: zamiast listy nazw — pełne okno drzewa technologii (`research_offer.gain_input`,
  tryb „gain”: bez płatności i prerekwizytów, na kaflu koszt `-N fleet`, bez przycisku rezygnacji). Wormhole
  Research („may research 1”) też w oknie badania (koszt 0, skipy specjalnością).
- Kafelki decyzji zawsze z opisem: technologia — tekst karty pod nazwą; cele / agendy / karty akcji / notki /
  liderzy rozpoznawane po id (`describeOption`) z punktami, oknem i tekstem; bez listy rozwijanej dla takich opcji.
  Imperial Arbiter: pełne nazwy kart strategii zamiast numerów.
- Podium Rady: pod każdym wynikiem informacja — planeta (R/I, typ, specjalność, kto trzyma + podgląd na mapie),
  gracz (VP, mówca, dostępne głosy), prawo / cel / karta strategii (rodzaj + tekst, pełny opis po najechaniu).
- Zakładka „Player” = panel dowódcy: działa w KAŻDEJ fazie (gracz pulpitu `useDeskPlayer`, nie `player.active`),
  przełączanie na innego gracza ze „stołu” (wyścig VP, tura, pas, karty strategii), odprawa ze wskazówkami
  (`commanderTips.ts`: co teraz, cele gotowe / o krok, limit kart, żetony, liderzy, prawa, głosowanie), zasoby
  (`ResourceBarFor`), pełna karta gracza, akcje + ręka dla gracza pulpitu. Web-data: `actionCardLimit` z silnika.
- Testy: `test_reactions_agenda` (Hack ×3), `test_agenda_effects` (Grant ×2, Arbiter), `test_rulings_audit`
  (Wormhole Research), `test_flows_agenda` (Grant przez API, `actionCardLimit`); front `DecisionFields.test.tsx`,
  `commanderTips.test.ts`. QA: pytest pełny, ruff/mypy (poza cudzym E501 w `core/activity.py`), tsc, eslint,
  vitest, build. Pominięte: e2e (zmienione okna nie są stale montowane). Zmiana hooków i web-data — restart backendu.

## Podgląd „dokąd prowadzi” wormhole / ingress / egress (front)

- Najechanie na wormhole (nadruk na kafelku albo żeton: Creuss, Gamma…) albo portal ingress/egress rysuje na
  mapie animowane łuki do połączonych systemów (płynąca przerywana linia, „kometa” od źródła do celu, pulsujący
  heks celu; kolor wg typu). Logika `domains/map/wormholeLinks.ts` (reużywa `wormholesOnTile`/`linkedPositions`
  z dossier; ingress → każdy egress i odwrotnie), warstwa `layers/WormholeLinkLayer`, niewidoczne punkty nad
  nadrukami `layers/WormholeHotspotsLayer` (pozycje z tabeli `WormholeBlockedLayer`), żetony przez `Token`.
- Żetony wormhole dostały dymek reguły (ta sama treść co dossier). Przekazywanie kliku pod żeton wydzielone do
  `forwardClickBelow`. Prawa Wormhole Reconstruction / Travel Ban nie zmieniają linii (do rozważenia).
- Testy: `wormholeLinks.test.ts`. QA: tsc, eslint, vitest `domains/map`. Pominięte: backend (bez zmian), build,
  e2e (nowe moduły tylko w obrębie mapy).

## Kluczowe momenty gry (animacje dla wszystkich) + szybkie przejścia faz (RULES 64)

- Reguła `docs/rules/R64.md`: ważne momenty pokazywane WSZYSTKIM graczom (także sprawcy) z publicznych faktów
  feedu Activity: bohater użyty (`leader` → `purged`, typ `hero`), The Fracture wchodzi do gry (NOWY fakt
  `fracture_entered` w `core/activity.py`, `player_id` = kto ją wprowadził), przełom zdobyty, żeton Custodians
  zdjęty. God-Mode nie wyzwala momentów — poza wejściem Fracture.
- Front `game-shell/components/KeyMoments/`: `keyMoments.ts` (czyste: wpis → momenty, zmiana fazy → pasek),
  `KeyMomentStage` (kolejka kinowych scen: letterbox, portret bohatera `/leaders/<id>.webp` + nazwa, tytuł i tekst
  zdolności z danych, szczelina Fracture z błyskiem/drżeniem/odłamkami, pierścienie przełomu, żeton Custodians;
  „Skip”/Esc; scena Fracture czeka, aż wyląduje d10 ze sceny kości), `PhaseSweep` (zastępuje usunięty
  `PhaseTransitionBanner`: wąski pasek ~1,6 s „ROUND N / Strategy Phase”, „Action Phase / Round N” w kolorze
  fazy oraz „YOUR TURN” w kolorze gracza, gdy tura przechodzi do tej przeglądarki). Obie warstwy bez wskaźnika
  (poza „Skip”), `prefers-reduced-motion` i `adminFastMode` („skip intro & cinematics”) respektowane.
- Feed: opis faktu `fracture_entered` w `describeActivity.tsx`.
- Testy: `test_activity::test_wejscie_fracture_jako_fakt`, `keyMoments.test.ts`. QA: pytest `test_activity`,
  ruff/mypy (zmienione pliki), tsc, eslint, vitest `game-shell` + `shared/audio`, build, e2e (7/7). Zrzuty scen
  zweryfikowane wizualnie. Nowy fakt w backendzie — restart backendu.

## Najnowsze wersje kart (TE / Codex) — audyt tekstów i Hack Election Ω (2026-11-16)

- Audyt talii: karty akcji `action_cards_te` (140) i agendy `agendas_pok` (50) — w assetach silnika brak starszych
  duplikatów z włączonych źródeł; 8 kart „Thunder's Edge Updated” (wiki TI4: Master Plan, Fighter Conscription,
  Blitz, Hack Election, Solar Flare, Counterstroke, Ghost Squad, War Machine) ma w assetach brzmienie TE (różnice
  tylko stylistyczne). TE nie zmienił agend (wiki Agenda Cards).
- Hack Election Ω (TE): „During this agenda, you vote last” — przywrócone `agenda_phase.vote_last`; rulingi Ω:
  mówca głosuje przed zagrywającym, zablokowany dalej nie głosuje, zagrywający nie zagra Bribery (znacznik
  `HACK_ELECTION`). RULES `R53.md`. Przyczyna „nie działa” w UI: Senat przestawiał mówcę na koniec (ignorował
  `voteOrder` silnika) + w ręce stary tekst karty. Naprawione oba.
- Dane frontu miały stare teksty (Hack Election, Insider Information „top card”, Master Plan, Solar Flare, Ghost
  Squad, Counterstroke, Experimental Battlestation, Skilled Retreat, Minister of War…) i brak 2 agend talii
  (Compensated Disarmament, Minister of Commerce). Nowy `scripts/sync_card_texts.py` (+ `--check`) wpisuje teksty
  z assetów; strażnik `tests/test_card_texts_sync.py`.
- Testy: `test_reactions_agenda` (Hack Ω ×5), `test_flows_agenda` (Hack przez API), `test_card_texts_sync`.
  QA: pytest pełny (1 niestabilny `test_undo_move` przy `-n auto`, osobno zielony — obszar równoległej sesji),
  ruff, mypy, tsc, eslint. Restart backendu (zmiana hooków).

## Bohaterowie: portret frakcji w scenie + efekty na planszy (RULES 64.4)

- Scena bohatera: zamiast słabej grafiki lidera portret frakcji ze sceny wyboru (`FactionPortraitLayer`, ten sam
  kadr co ekran zwycięstwa: postać przy lewej/dolnej krawędzi, przed pasami letterbox; tekst od prawej krawędzi
  sylwetki przez `--figure-cx`). Wykrycie bohatera także po efekcie `leaders:<bohater>` (jeden moment na wpis).
- Efekt na planszy po scenie: `KeyMoments/heroBoardFx.ts` (`HERO_BOARD_FX` — przepis na każdego bohatera z silnika:
  Letnev cienie okrętów `Unit` nad przyciemnioną planszą, Arborec pnącza z sił naziemnych, Sol złota fala + słupy
  światła, Jol-Nar skan, Hacan trade goods nad aktywnym systemem, Mentak fale, Sardakk szpony, Winnu pieczęć nad
  Mecatol Rex; `fxTargets` z kafelków mapy) + warstwa `map/components/layers/HeroBoardFxLayer` w treści mapy (idzie
  za zoomem, bez wskaźnika). Kolejka `KeyMomentStage`: scena → efekt na mapie → następny moment; „Skip”/Esc ze
  sceny przechodzi do efektu, z planszy kończy.
- Testy: `heroBoardFx.test.ts` (cele + strażnik: każdy bohater silnika ma przepis), `keyMoments.test.ts`. QA: tsc,
  eslint, vitest `game-shell` + `map`, build, e2e (7/7); zrzuty scen i wszystkich efektów sprawdzone wizualnie.
  Backend bez zmian (bez QA backendu).

## Pasek ręki: wyśrodkowanie, taca przy krawędzi, czytelne Undo/Hold

- `BottomHandDock`: dok zawsze na środku ekranu (oba boki = większy ze slotów HUD `--hud-left-w`/`--hud-right-w`),
  przyklejony do dolnej krawędzi (bez szczeliny, zaokrąglone tylko górne rogi). Nagłówek jako siatka 3 kolumn
  (kto | segmenty | narzędzia) — segmenty zawsze na środku, nic się nie przesuwa po zmianie stanu Undo.
- Undo/Hold (`UndoControls`, `HoldControls`): wspólny `.toolBtn` (Undo niebieski, Hold bursztynowy, ta sama wysokość
  co segmenty), stała szerokość; opis „co robi” + stan („Will undo: …” / „Not possible now: …”) w dymku `Tooltip`
  przez nowy `ToolHint`. Niedostępne Undo = `aria-disabled` (dymek z powodem działa też na wyłączonym). Wąski dok:
  narzędzia tylko ikonami.
- QA: tsc, eslint, vitest `BottomHandDock`. Bez build/e2e (tylko CSS + istniejące moduły), backend bez zmian.

## Zakładka Player: porządek, ręka jak na mapie, panel Empire i kalkulator budowy

- Usunięty box „Actions” (`GameStateActionControls`) — akcje tury są w panelu sterowania na mapie.
- Ręka: kafelek karty wydzielony z doku do `BottomHandDock/HandCard.tsx` (`HandCard`, `CardDetails`, `TABS`…) —
  JEDEN komponent dla paska ręki i zakładki. `PlayerTab/HandPanel.tsx`: siatka pogrupowana (karty akcji + frontier,
  tajne cele, notki), klik = pełna karta, bez przeciągania (`onDragChange` opcjonalne = tylko podgląd); ten sam
  endpoint ręki co dok. Cudzy gracz = same liczby.
- `PlayerTab/empireStats.ts` (czysta funkcja z `gameData.tiles` + `PlayerData`): systemy (obecność / bez innych
  graczy), planety ready/total, cechy, legendarne, specjalizacje na GOTOWYCH planetach, siły (statki, myśliwce, siły
  naziemne, doki, PDS), największa flota bez myśliwców vs pula floty (R_fleet_pool), najwyższe PRODUCTION gracza
  (nowe pole `Tile.productionByColor` z web-data `production`). Kalkulator „Shipyard”: budżet = gotowe zasoby + TG,
  max = min(koszt z assetów, PRODUCTION, posiłki); fighter/infantry 2 za koszt, każdy liczy się do PRODUCTION,
  bez limitu posiłków (żetony) — R_producing_units.
- `EmpirePanel.tsx`: kafelki liczb + ikony `PlanetTraitIcon`/`TechSkipIcon` + lista budowy ze sprite'ami `Unit`.
- Odprawa (`commanderTips.empireTips`): specjalizacje do badania, brak PRODUCTION na planszy, flota przy limicie
  puli, typy jednostek bez posiłków.
- Testy: `empireStats.test.ts` (statystyki, kalkulator, porady). QA: tsc, eslint (zmienione), vitest `PlayerTab`
  + `BottomHandDock`, build. Bez e2e (zakładka nie jest montowana zawsze), backend bez zmian.

## Okna reakcji: stała długość hosta + auto-pas silnika + „Skip all reactions” (RULES 54.11)

- Problem: przy 6 graczach pauzy ochronne (54.10) i okna Sabotage (53.6) po 10 s plus klikanie „Pass” przez każdego
  kumulowały się w długiej grze. Boty w ogóle nie pasowały, więc bot z kartami wymuszał pełne 10 s.
- Model (decyzja użytkownika 2026-11-16): okno trwa STAŁY czas ustawiony przez hosta (domyślnie 4 s, 2–30 s) i nie
  kończy się po pasach. Silnik przy otwarciu sam pasuje za graczy bez karty reakcji zagrywalnej teraz, za botów i za
  graczy z „Skip all reactions”. Pasy są prywatne (projekcja `visibility.redact_reaction_windows`, web-data bez
  licznika „N/M passed”). „More time” (+10 s, raz na gracza) może wcisnąć każdy uprawniony, także spasowany przez
  silnik; inni widzą anonimowo. Test w parach: z kartą i bez karty z zewnątrz okno wygląda identycznie.
- Backend: `core/reaction_window.py` (długość, auto-pas, More time, przełącznik), zmiany w `reaction_pause.py`,
  `card_hold.py` (`begin` dostaje `registry`), pola `seconds`/`extended_by`, `GameState.reaction_window_seconds`,
  `PlayerPrivateState.auto_pass_reactions`. Router `reaction_settings.py` (`/window` HostOnly, `/auto-pass`), trasy
  `/reaction-pause/wait`, `/action-card/held/wait`, opcja `reaction_window_seconds` w `/game/new`. Middleware zwalnia
  przeterminowane okno Sabotage przy dowolnym POST. Feed: `reactions.window`, `reactions.wait` (bez nazwiska).
- Front: wspólny `useWindowCountdown` + `reactionWindowParts` (tekst oczekiwania, „+10s”) w `ReactionPauseBanner` i
  `HeldPlayBanner`; przełącznik `ReactionAutoPassToggle` na pasku nazwy własnego gracza w „Player areas” (blada ikona,
  żółta pigułka „Auto-pass” gdy włączony, opis w dymku); Ustawienia → „Reaction windows” (nowa gra + „Apply” w
  trwającej grze).
- Testy: nowy `tests/test_reaction_window.py`, przepisane `test_card_hold`, `test_reaction_pause`; harness scenariuszy
  dostał sterowany zegar (`Flow.clock`, `finish_hold`). Front: `ReactionPauseBanner.test`, `ReactionAutoPassToggle.test`.
  QA: pytest pełny (1 znany niestabilny `test_undo_move` przy `-n auto`, osobno zielony), ruff, mypy, tsc, eslint,
  vitest (player, game-shell, settings), build, e2e. Wymaga restartu backendu (nowe trasy i pola stanu).

## Bot B0: fundament warstwy bota (docs, bez kodu)

- Branch `bot/b0-fundament`. Audyt silnika pod bota + plan krótkich branchy: `docs/bot/PLAN.md` (co już jest:
  `actor.awaiting`, `project_strict`, seedowalny RNG, `clone` 0,40 ms; luki: katalog akcji, generator legalnych
  ruchów, wyzwalacz bota, infrastruktura obliczeń, decyzje bota w `core/` do przeniesienia).
- Decyzja użytkownika: kilka osobnych, złożonych algorytmów liczonych lokalnie → wspólny interfejs
  `DecisionRequest → DecisionResult`, procesy robocze, budżet czasu, odrzucanie wyników po zmianie stanu, arena
  do porównywania algorytmów. Zasady projektowe: nowa sekcja `docs/rules/R65.md` (+ indeks `RULES.md`).
- Instrukcje warstwy dla Claude: `src/engine/CLAUDE.md`. `ARCHITEKTURA_KODU.md`: warstwa bota `ai/` → `src/engine/`.
- QA: `tests/test_docs_numbering.py`. Zmiana tylko dokumentacji (bez pełnego QA backendu i frontu).
## Okna decyzji: opis komponentu na kafelku + pełna karta po kliknięciu (ⓘ)

- Zgłoszenie: Strategize (i inne) pokazywały same nazwy kart strategii. Audyt WSZYSTKICH zarejestrowanych wejść
  (efekty kart akcji, agend, reliktów, notek, liderów, technologii, zdolności; skrypt na bogatym stanie jak
  `test_action_cards_smoke`) + przegląd statyczny ofert „may”. Znalezione: karty strategii jako sama nazwa / numer
  (Strategize ×4, Overrule, Winnu hero „Strategy card N”, Hacan QDN „Your card N”), technologie z prefiksem
  (`tech:`, „Keep X” Jol-Nar hero, Sardakk N'orr, Bio-Stims), relikt surowym id (Sardakk „Relic <id>”), relikty
  i przełomy w ogóle nierozpoznawane przez front, surowy typ jednostki (Sardakk komandor „infantry -> …”).
- Kontrakt: opcja może nieść `meta.ref = {kind, id}` (`offer_inputs.option(ref=...)`, `_option(ref=...)`,
  `REF_KINDS`; nieznany rodzaj = `ValueError`). Etykiety: `card_labels.describe_strategy_card` („Leadership -
  initiative 1”), `card_labels.relic_name`.
- Front: wspólny `cards/components/ComponentInfo` (`ComponentCard` = te same karty co chipy panelu gracza;
  `ComponentInfoButton` = ⓘ, klik otwiera pełną kartę, działa na dotyku, nie wybiera opcji). `describeOption`
  czyta `meta.ref`, potem gołe id (doszły relikty i przełomy w `hintFor`); kafelek pokazuje CAŁY tekst (primary
  i secondary), nie pierwszy akapit. ⓘ także w: Imperial (zwrot celu tajnego - opis w chipie), Politics (agenda z
  celem i oboma akapitami), wyniki głosowania agendy (prawo/cel/karta strategii/planeta).
- Testy: `test_card_labels` (odnośniki kart strategii, walidacja rodzaju), `DecisionFields.test` (karta strategii z
  odnośnikiem, ⓘ nie wybiera). QA: pytest pełny (znany niestabilny `test_undo_move` przy `-n auto`), ruff, mypy,
  tsc, eslint, vitest (offers, agenda, strategy, ActivityPanel), build. Bez e2e (brak zmian w przepływie gry).
  Wymaga restartu backendu (nowe pole `meta.ref` w opcjach).

## Bot B1: katalog akcji i legalne ruchy (bot „pasywny” gra pełne rundy)

- `src/engine/actions.py`: 30 rodzajów `Action` (Pydantic, `kind`) + `apply_action` przez te same funkcje `core/`
  i tę samą kontrolę aktora co routery; `apply_and_settle` dokłada rozliczenie po kroku (jak commit serwera).
  `src/engine/observation.py`: ścisła projekcja + własne monity (jak klient). `src/engine/legal.py`: kandydaci
  dla gracza, pierwszy = bezpieczny ruch domyślny (RULES.md 65.4), w tym kroki primary wszystkich 8 kart.
- Zmiany w `core/` (osobne commity): `core/phase_flow.py` (logika `/phase/next` i `/round/next` z routera),
  `core/step_settle.py` (reguły „po każdym kroku” ze `StateService`), seedowalne tasowanie przy wyborze tajnego
  celu (`game_setup.choose_secret`/`skip_setup` miały niezasiany `random.Random()`).
- Testy `tests/engine/`: gra samych botów przez prawdziwe API z porównaniem stanu katalog ↔ HTTP po każdym
  kroku (3 scenariusze, 2 pełne rundy, z agendą), celowane testy zgodności, determinizm, strażnik pokrycia
  (`NOT_YET_COVERED`: 5 rodzajów do B5) i strażnik warstwy (bez `api/`, `time`, `secrets`).
  `test_game_setup`: tasowanie tajnych celów seedowalne.
- QA: pytest pełny (2405), ruff, mypy. Front bez zmian. Bez nowych tras; po merge warto zrestartować backend
  (zmieniony `StateService` i router faz).

## Fala 2 B6: Xxcha Kingdom — komplet (11/11, RULES.md 62.9) (2026-11-16)

- Moduł `core/hooks/factions/xxcha.py`: Peace Accords (oferta po primary/secondary Diplomacy, eksploracja
  niekontrolowanej, planeta wyczerpana), Quash (okno 62.0 przy ujawnieniu agendy), Political Favor (notka w tym samym
  oknie), Instinct Training, Nullification Field (koniec tury aktywnego, oferty „after activates” przepadają),
  Ggrocuto Rinn, Elder Qanoj, Xxekir Grom w wersji TE (Planetary Defense Nexus), Loncara Ssodu / Indomitus (Deep Space
  Cannon z danych), Archon's Gift.
- ✅ Decyzja użytkownika: najnowsza wersja bohatera — loader liderów stosuje `homebrewReplacesID`
  (`StaticDataRegistry._apply_leader_replacements`; dotyczy też `naaluagent-te`). Audyt pokrycia pomija karty
  zastąpione.
- Nowe punkty centralne: `payment.flex_spend` (planeta wnosi większą wartość tylko przy wydawaniu),
  `agenda.votes_per_planet` + `agenda.vote_unblockable`, `action_cards.canceller` (anulowanie bez karty w ręce).
- Okno hold kart akcji: Sabotage na czekającą kartę samo czeka na Instinct Training (`HeldPlay.counter`, baner
  pokazuje je pod kartą); anulowanie komponentem oddaje akcję tury ACTION (`card_hold.cancel_by_component`).
  `faction_components` ma rodzaj `technology` (tylko technologie z `window_use`), `holds=True` = jedyne użycie
  dozwolone w trakcie okna hold (API wpuszcza `/faction-component/play`).
- Auto-pas / pauza ochronna liczą też zdolności z oknem i notki-reakcje (`reaction_window.window_component_users`).
- Poprawka silnika: oferty „after primary” nie otwierały okna REACTION przed oknem secondary („Another timing window is
  already open”) — teraz czekają w oknie secondary (`triggers.open_offers_window` bez secondary).
- Feed Activity: użycie komponentu ma gracza w etykiecie (`component-use:<rodzaj>:<id>:<gracz>`), bo Quash i Instinct
  Training używa gracz nieaktywny.
- Testy: `tests/factions/test_xxcha.py` (24), `test_flows_xxcha.py` (8 scenariuszy przez API), `test_activity`.
  Restart backendu wymagany (nowe hooki, pole `HeldPlay.counter`, loader liderów).

## Okna czasowe bez ogólnej odpowiedzi + bot w oknie strat; odchudzenie docs (2026-11-16)

- **Błąd:** `/window/respond` przesuwał kolejkę dowolnego okna, ale nie zamykał dopełnionego (zamknąć mógł
  tylko host przez `/window/close`) i omijał obowiązkową decyzję (straty, nadwyżka, oferty). Każdy typ okna ma
  własne rozstrzygnięcie w `core/`, więc endpoint usunięty: `api/routers/window.py`, `WindowRespondRequest`,
  akcja bota `WindowRespond`, `respondWindow` w `useBoardEditor.ts`. `GameStatePanel` WindowSection: przyciski
  tylko dla secondary; w God-Mode okno z własnym panelem ma wentyl „Close window”.
- **Bot:** `engine/legal._window` w oknie `COMBAT_ASSIGN_HITS` zwracał ogólne „OK” zamiast `battle_assign`
  (gałąź walki była nieosiągalna). Teraz `_assign_hits`; pozostałe okna z własną decyzją → brak ruchu do B5.
  Test: `tests/engine/test_legal_windows.py`; `test_window_api.py` sprawdza brak endpointu.
- **Porządki:** starsze bloki `PROGRESS.md` (166 KB → 39 KB) przeniesione do `PROGRESS_ARCHIWUM.md`;
  usunięty czysty, zmergowany worktree `.claude/worktrees/bot-b1` (863 MB; branch zostaje).
- QA: pytest (2443 ✅), ruff, mypy; front: tsc, eslint (zmienione), vitest `game-shell`. Bez build/e2e
  (bez nowych importów; panel okna zmieniony tylko warunkami).

## Bot B2 (rdzeń) + B3: boty grają same w serwerze (2026-11-16) — RULES.md 65.7

- `src/engine/compute.py`: `DecisionRequest/DecisionResult`, rejestr algorytmów (`first` = pasywny,
  `random` = losowy z ziarnem), `Executor` inline/process z twardym terminem → ruch domyślny.
- `src/api/bot_runner.py`: pętla w lifespan serwera (budzona po `StateService.broadcast` i co 1 s);
  obserwacja → `legal_actions` → decyzja → to samo żądanie HTTP co klient człowieka (ASGI w procesie,
  `api/bot_http.py` przeniesiony z testów). Stan zmieniony w trakcie (człowiek, Undo) → liczy od nowa;
  odrzucony ruch → kolejny kandydat. Gra sieciowa: `SeatRegistry.bot_token` (tylko w pamięci) → `Identity.bot`.
- `BotConfig` (`engine_config.json` → `bot`): algorytm per poziom, `move_delay_s` 1 s, terminy 2 s / 10 s
  (kluczowe rodzaje), `executor`, `workers: 0` = rdzenie − 1. `create_app(bots=True)` w serwerze,
  `--no-bots` wyłącza; testy domyślnie bez runnera.
- Wizja 4 warstw algorytmów + uwagi i decyzje §6 w `docs/bot/PLAN.md`.
- Test: `tests/engine/test_bot_runner.py` — 6 botów same do rundy 3 (189 ruchów, etykiety routerów),
  1 człowiek + 3 boty: boty czekają na człowieka, pętla w lifespan rusza po `/game/new`, proces = inline.
- Brak: przełącznik admin fast (opóźnienie 0) z UI, `engine/bench.py`, wynik „anytime” z procesu.


## Wybór miejsca na mapie zamiast list + efekt bohatera Xxcha (2026-11-16)

- **Problem (użytkownik):** Xxekir Grom pokazywał listę „PDS on X”, „Mech on X #2”… — klasyfikator
  `optionKinds` odrzucał opcje z `meta.unit` i powtórzone cele. Audyt WSZYSTKICH formularzy (skrypt wywołujący
  każde `register_effect_inputs` i `inputs` ofert na bogatym stanie + ręczny przegląd ofert zależnych od
  kontekstu) znalazł ten sam wzór w: Xxekir Grom, Refit Troops, Scuttle, Lucky Shot, Decoy, ruch sił naziemnych
  w inwazji, Arborec agent, Titan Prototype, Sardakk commander, agendy niszczące jednostki
  (Revolution, Arms Reduction, Homeland Defense Act, artefakty), notki `ms` i `stymie`
  („Do not place” blokowało mapę), Mercenary Contract / Jamming (cel w wartości-słowniku) i Bioplasmosis
  (lista stepperów „A -> B” dla każdej pary planet).
- **Front:** `GroupedMapField` — cele świecą na mapie (i jako chipy), klik otwiera, co można zrobić TAM;
  jednakowe jednostki = licznik −/+ (`optionKinds.stacksOf`, `withStackCount`, także w zwykłym multi).
  `classifyOptions`: grupy (`grouped`), do 2 opcji bez celu obok mapy, cel z wartości-słownika.
  `RouteNumbersField` (Bioplasmosis): źródło, potem cel = +1. Kafelki wydzielone do `DecisionTiles.tsx`.
  `useMapPick` wyłączony nie czyści już cudzego wyboru na mapie.
- **Backend:** `offer_inputs.unit_at` (jednostka + planeta/system), `number(..., meta=route_meta(...))`;
  `agendas_common.unit_options/destroy_choice_input` biorą gracza (nazwy wariantów zamiast „carrier #1”).
- **Bohater Xxcha:** scena grała (fakt `leader purged`), ale nie było efektu na planszy — dodany „Aegis”
  (kopuły tarcz nad systemami z PDS/mechami, cel `defense`). Strażnik `tests/test_hero_board_fx_guard.py`
  porównuje bohaterów z silnika z `HERO_BOARD_FX`.
- Reguła: RULES.md 56.5, 64.4. QA: pytest (2475 ✅ po commicie Yin z efektem `yinhero`), ruff,
  mypy; front: tsc, eslint (zmienione), vitest (cały, 207 ✅), build ✅. Bez e2e (zmiany tylko w obrębie
  okien decyzji). Restart backendu wymagany (nowe metadane wejść).

## Fala 2 B7: Yin Brotherhood — komplet (11/11, RULES.md 62.10) (2026-11-16)

- Moduł `core/hooks/factions/yin.py` (wersje Ω): Indoctrination (+ Moyin's Ashes jako opcja „mech” za +1 wpływu),
  Devotion, Impulse Core, Yin Spinner Ω, Greyfire Mutagen Ω (notka-reakcja na starcie walki naziemnej), Brother
  Milor Ω (tylko faza akcji, także Space Cannon / bombardowanie), Brother Omar Ω (odblokowanie zdarzeniowe
  `unlocks:yincommander` — pierwsze w projekcie), Dannel Ω — Quantum Dissemination, Van Hauge, Yin Ascendant.
- Punkty centralne: wymagany cel trafień `ActiveCombat.hit_targets` (Impulse Core: nie-myśliwce „if able”,
  Devotion: typ wybrany przez Yin) walidowany w `assign_combat_hits`; trafienia po rundzie
  `battle.add_round_end_hits` (własny krok ASSIGN, bez ponownych zdarzeń końca rundy); strona bez jednostek
  przed rzutem przegrywa od razu (`roll_round`); `technology.virtual_prerequisites` i skip
  `infantry:<pozycja>|<strefa>` (`technology.infantry_skip`); commanderzy z efektów trwałych (`data.commanders`
  w `rules_hooks`); emisja `OBJECTIVE_SCORED` w `objectives.score_public`.
- **Inwazja komponentu** (`InvasionState.source`, `queue`, `invasion.start_component_invasion`): Quantum
  Dissemination stawia piechotę, potem okno inwazji system po systemie od kroku Commit (Ghost Squad / Parley —
  Parley bez statków z pojemnością zdejmuje piechotę z planszy, F_yin Ω), bez Space Cannon Defense, walka
  naziemna bez aktywnego systemu (`battle.start_combat`), zamknięcie otwiera kolejny system; lądowanie z
  przestrzeni zablokowane; koniec tury czeka na koniec inwazji.
- UI: okno badania — sekcja „Brother Omar · return 1 infantry” (gracz wybiera miejsce; auto-dobór tylko gdy
  specjalności nie wystarczą), `infantry_skips` w widoku badania; efekt bohatera na planszy `yinhero`. Bot:
  przypisanie strat najpierw na wymagany cel.
- ⚠️ ZAŁOŻENIA (RULES.md 62.10, do potwierdzenia): Quantum Dissemination nie zdejmuje żetonu Custodians
  (Mecatol z żetonem niedostępny); Yin Ascendant „unused” = frakcja spoza gry i jeszcze niezdobyta.
- Testy: `tests/factions/test_yin.py` (18), `test_flows_yin.py` (7 scenariuszy przez API), `techModel.test.ts`;
  strażnik `test_hook_coverage` zna klucze `unlocks:`. Restart backendu wymagany (nowe pola stanu i hooki).

## Yin Ascendant: zdobycie z edytora i sojusze w panelu liderów (2026-11-16)

- **Błąd (zgłoszenie użytkownika: „Yin Ascendant nie działa”):** przełom przyznany w edytorze gracza ustawiał samo
  pole, bez „zdobycia” — efekt nie odpalał; a zdobyty sojusz nie był nigdzie widoczny poza feedem. Teraz
  `board_edit.edit_player` przy `breakthrough_unlocked` false→true woła `breakthrough.unlock_breakthrough`
  (efekty „when you gain this card”, bez walidacji), a web-data dokłada commanderów z sojuszu (Yin Ascendant
  i notka Alliance) do `leaders` z `alliance: true` — ten sam `LeaderChip` z dopiskiem „alliance”; edytor
  liderów God-Mode ich nie pokazuje.
- ✅ Decyzje użytkownika (RULES.md 62.10): Quantum Dissemination bez zdejmowania żetonu Custodians; „unused” =
  frakcja spoza gry i jeszcze niezdobyta.
- Test: `test_flows_yin.py::test_yin_ascendant_z_edytora_i_w_panelu_liderow`. QA: pytest (2476 ✅), ruff, mypy;
  front: tsc, eslint (zmienione), vitest `domains/player`. Bez build/e2e. Restart backendu wymagany.

## Dźwięk: Yin `bomb` = Van Hauge (decyzja użytkownika)

- `voiceCues.ts`: kwestie `assets/voices/yin/Bomb1–2` grają przy utracie flagowca Yin (fakt `units`
  `flagship` < 0; bez duplikatu w podsumowaniu `combat.end`), nie przy Devotion/Impulse Core.
- Test: `audio.test.ts`. QA: front tsc, eslint (zmienione), vitest `shared/audio`. Bez backendu/build/e2e.
- Bohater frakcji: `special`, a gdy frakcja go nie ma -> `battle`; Yin -> konkretnie `battle1`. Kwestie specjalne
  zdolności: zapas `special`, potem `battle` (`SPECIAL_FALLBACK`). `sayVoice(..., file)` gra wskazane nagranie.

## Planety tylko na mapie, technologie tylko w drzewie (2026-11-16, RULES.md 56.5a)

- **Zgłoszenie (Yin hero):** Quantum Dissemination dawał tylko planety w systemach z jednostkami i pokazywał listę.
  Przyczyny: `dissemination_targets` szedł po `state.systems` (tylko systemy z wpisem) — nowy
  `system_planets.board_planets` (cała plansza; siatka dla systemów bez wpisu), efekt stawia przez
  `board_graph.ensure_system`; ten sam błąd poprawiony w Stellar Converter (`relics_actions`) i nexusie
  (`agendas_laws`). Na froncie opcje z `meta.ref` planety/tech nie były rozpoznawane (`optionKinds`).
- **Front:** każde pole planet/systemów → `GroupedMapField` (bez listy celów; wybrane = chip z ×, wezwanie do kliku
  na mapie); `RouteNumbersField` i `TransitDiodesPicker` bez list planet; Pride of Kenara w `TradingTable` — cel
  na mapie zamiast `<select>`. Technologie → nowy `TechPickField` (drzewo `TechnologyOverlay`, tryb „gain”).
  Usunięty martwy `useFieldMapPick`.
- Testy: `test_yin.py::test_dissemination_cala_plansza_nie_tylko_systemy_z_jednostkami`,
  `optionKinds.test.ts` (ref planety/tech), `DecisionFields.test.tsx` (mapa przez `appStore.mapPick`, drzewo tech).
- QA: pytest (2478 ✅), ruff, mypy; front: tsc, eslint (zmienione), vitest `offers`, `TurnControls`,
  `technology`, `strategy`. `npm run build` pada na `index.html?html-proxy&inline-css` (nie te pliki; do
  sprawdzenia osobno). Bez e2e. Restart backendu wymagany.

## Pole efektów trwałych na stole obok planszy (2026-11-16, RULES.md 54)

- **Decyzja użytkownika:** „Active effects” to nie nakładka na ekran, tylko fizyczne miejsce przy planszy, jak pola
  graczy, ale w innym stylu. `ActiveEffectsPanel` → `domains/effects/BoardEffectsZone` (wpuszczona w blat taca
  z grawerowaną przerywaną ramką; leży zawsze, także pusta).
- Strefa jest dzieckiem opakowania planszy (`InteractiveMapRenderer` przyjmuje `children`), przy prawym górnym
  rogu (za bleedem), przesuwa się z mapą. Usunięta z `GameMapPage`.
- Poprawka (użytkownik): pudełko wielkości jednego systemu (`TILE_WIDTH/HEIGHT × zoom`, min. 170×140 px), efekty
  jako chipy, opis w `SmoothPopover` + `DetailsCard` po kliknięciu; układ planszy (centrowanie, Fit board) bez zmian.
- Test: `BoardEffectsZone.test.tsx`. QA: front tsc, eslint (zmienione), vitest `domains/effects`. Bez backendu,
  build i e2e (brak nowych zależności); bez zrzutu ekranu — do obejrzenia w działającej grze.
- Poprawka 2 (użytkownik): taca leży W WARSTWIE PLANSZY (`MapRenderLayer`, skala zoomu), po prawej między polami
  graczy 2 i 3 — `effectsZoneAnchor` szuka największej pionowej luki między polami graczy na prawo od środka
  (mapa 6-osobowa = pozycja 407). Wysokość jednego systemu, żetony po 3 w kolumnie, kolejne kolumny w prawo
  (taca rośnie z liczbą efektów). Cofnięte `children` w `InteractiveMapRenderer` i zmiany w `PannableMapView`.
  QA: tsc, eslint, vitest `effects`, `map`, `game-shell`.

## Panel punktów: wszystkie źródła VP w „Other points” + stany toru (2026-11-16, RULES.md 41)

- **Zgłoszenie użytkownika:** w „Other points” był tylko żeton Custodians; brakowało Styx, agend, reliktów itd.;
  stany „Can be lost” / „Ready to score” / „Possible” nie działały.
- **Rejestr źródeł VP:** `objectives.award_points(..., source=...)` zapisuje `ObjectivesState.point_sources`
  (`{źródło: {gracz: VP netto}}`). Podpięte wszystkie miejsca: Custodians, Imperial (primary), Shard of the Throne,
  The Crown of Emphidia, Book of Latvinia, The Silver Flame, Styx, Support for the Throne, Mutiny, Seed of an
  Empire, Political Censure (wybór i odrzucenie prawa), Imperial Rider. `LOSABLE_POINT_SOURCES`: Shard, Styx, SftT,
  Political Censure.
- **Web-data:** nowy `api/web_points.py` (z `web_objectives` wydzielone rozbicie toru). „Other points”: Custodians i
  Imperial zawsze, Styx gdy jest na mapie, relikty z VP u graczy, plus wszystko z rejestru; pola `factionPoints`
  (ujemne = utracone) i `losable`. Tor: SCORED (z `losable`), potem QUALIFIES (cele gotowe teraz, Imperial
  z Mecatol), potem POTENTIAL (wszystkie niezdobyte cele z postępem, tajne, Custodians, relikty). VP bez źródła
  (God-Mode) = żeton „OTHER”, więc tor sumuje się do wyniku.
- **Front:** typy `RELIC`/`OTHER`, „+N possible” liczone z niezdobytych żetonów, w „Other points” czerwona
  komórka utraconych punktów i plakietka „can be lost”.
- **Intimidate Council:** liczenie działa (symulacja na żywej mapie: statki w 2 systemach przy Mecatol → 2/2,
  gotowe). Na obecnej mapie Mecatol ma tylko 3 sąsiednie systemy (+ Fracture) i nikt tam nie stoi → 0/2 poprawnie.
- Testy: `tests/test_web_points.py` + asercje rejestru w testach Styx, SftT, Mutiny, Shard. QA: pytest -n auto
  (2481 ✅; `test_undo_move` niestabilny od kolejności testów — pada też bez tych zmian), ruff, mypy; front tsc,
  eslint (zmienione). Bez build/e2e (brak nowych zależności). Restart backendu wymagany (nowe pole stanu).
- Poprawka 3 (użytkownik: taca nachodziła na planszę): prostokąt w miejscu heksa 407 wchodził na rogi heksów
  304/305. Teraz `effectsZoneAnchor` kładzie tacę ZA najdalszą w prawo kolumną heksów (plansza + pola graczy)
  + `ZONE_GAP`, nadal na wysokości luki gracza 2 i 3. Zweryfikowane zrzutem (izolowany backend :8100, 0/5/9
  efektów, sprawdzenie przecięć prostokątów z heksami — brak).

## Devotion / Magen: zagrywający wskazuje KONKRETNY cel + koniec rundy po odwrocie (RULES.md 39.5 O7a, 55, 62.10)

- Zgłoszenie użytkownika: Devotion (Yin) — trafienie przypisywał przeciwnik, nie Yin. Audyt rulingów F_yin wykazał 3 błędy:
  (1) Yin wybierał tylko TYP statku (nie dało się wskazać uszkodzonego pancernika), (2) przeciwnik dostawał zwykłe
  przypisanie bez informacji o wymuszonym celu (422 przy próbie), (3) `COMBAT_ROUND/END` odpalał się PRZED krokiem
  Retreat (i drugi raz po nim) — Devotion/Exotrireme II trafiały uciekiniera, Duranium mogło działać dwa razy.
- Silnik: `hit_targets` z `damaged` i `chooser` (`add_start_hits`/`add_round_end_hits`), walidacja egzemplarza
  w `_check_hit_targets` (naprawiony w międzyczasie cel = nieuszkodzony); `_retreat_due` — Retreat przed zdarzeniami
  końca rundy, decyzje ze strat (Brother Milor) przed odwrotem (`_RESUME_RETREAT`).
- Ta sama klasa błędu: Magen Defense Grid Ω/ΩΩ (C_technology) — właściciel wskazuje jednostkę z uszkodzeniem,
  obrońca sam decyduje o Sustain Damage (wcześniej Sustain włączał się automatycznie). Creuss (Dimensional Splicer)
  i Argent (Raid Formation) nie mają jeszcze hooków — przy implementacji użyć `chooser`/`damaged`.
- API: `BattleResponse.hitTargets`. Front: `shipPickSteps` — wieloetapowy wybór okrętów na polu bitwy (Devotion:
  swój krążownik/niszczyciel → wrogi okręt, rozróżnia uszkodzone; klika DECYDUJĄCY, nie właściciel okrętów);
  przy przypisaniu klikalny tylko wymuszony cel, znacznik ustawiony, notka w panelu (`targetNote`).
- Testy: `test_flows_yin.py` (cel uszkodzony/nieuszkodzony, brak Devotion po odwrocie), Magen w
  `test_technologies_combat.py`/`test_offers.py`, `shipPick.test.ts`. Harness: `announce` zamiast złego klucza `retreat`.
- QA: pytest 2485 ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest battle+offers 47 ✓, e2e 7 ✓. Restart backendu wymagany.

## 2026-11-16 — Kontrakt rulingów: każdy ruling i zdanie karty = test (pilot: Xxcha)

- Decyzja użytkownika: elementy dodanych frakcji często nie działały, bo rulingi `F_<frakcja>.md` były pomijane.
  Nowy kontrakt: `tests/rulings.py` nadaje stałe ID każdemu punktowi rulingu (`F_xxcha/quash/1.1`) i każdemu zdaniu
  tekstu komponentu z assetów (`abilities:quash#2`, `leaders:<id>#unlock`); testy oznacza `@ruling(...)`.
  Strażnik `tests/test_ruling_coverage.py`: każde ID audytowanej frakcji ma test albo status z powodem
  (`tests/rulings_status.json`: `na` / `requires` — `requires` robi się czerwony, gdy brakujący element powstanie),
  nieznane ID = błąd. `UNAUDITED` (9 frakcji sprzed strażnika) może tylko maleć; nowa frakcja od razu pełna.
  Checklista: `uv run python -m tests.rulings <frakcja>`.
- Xxcha (pilot): 98 punktów kontraktu — 70 z testem, 27 nieaktywnych wariantów bohatera (Codex/Ω; gra wersja TE),
  1 `requires: faction:nekro`. Nowy plik `tests/factions/test_rulings_xxcha.py` (25 testów) + znaczniki w `test_xxcha.py`.
- Błędy znalezione audytem i poprawione:
  - Indomitus/Space Cannon (F_xxcha, RULES.md 39.6): po zestrzeleniu nosicieli przez Space Cannon aktywnego mech
    zostawał w przestrzeni ponad pojemność i dalej strzelał — teraz `space_cannon.assign_hits` od razu otwiera
    okno `CAPACITY` (`timing.interrupt`, istniejący `CapacityModal`).
  - Archon's Gift (F_xxcha 2.1, RULES.md 62.9): cele „Spend…” liczyły surowe wartości planet — Xxcha nie mógł zdobyć
    Amass Wealth/Sway the Council wydając wpływ jak zasoby (`objective_progress.spend_planets`, `auto_payment`).
  - Amass Wealth / Vast Reserves (RULES.md 41.4): jawna płatność (UI) wymagała 9/18 na KAŻDĄ część („21 TG needed”) —
    cel był nie do zdobycia dla nikogo; `objective_payment.spend_goal` = 3/6 (walidacja i `spendSpec.goal` w UI).
  - Divert Funding (F_xxcha Instinct Training/6, RULES.md 53): badana technologia była ogłaszana przy zagraniu —
    teraz okno badania po rozstrzygnięciu karty (`research_offer`, jak Focused Research).

## 2026-11-16 — Okna decyzji z wyborem na mapie: przebudowa (front)

- Zgłoszenie użytkownika (np. Yin Spinner): ucięte podświetlenie systemu, „klik w jedno okno blokuje drugie”.
  Przyczyny i poprawki:
  - Jeden globalny `appStore.mapPick` — okno ustawiające wybór ostatnie wygrywało, a sprzątanie jednego kasowało
    wybór drugiego. Teraz REJESTR `mapPicks` (wpis na okno, `useId`): aktywny = najnowszy albo przejęty klikiem
    w okno (`claim`/`raiseMapPick`); zamknięcie okna oddaje mapę poprzedniemu. `useMapPick` (stare API) +
    `useMapTargets` (systemy i planety naraz). Trasa ruchu działa obok aktywnego wyboru (inne cele).
  - Skip/Use znikały w ukrytym przewijaniu kolumny decyzji (sztywne 360 px rezerwy): stopka karty decyzji jest
    przyklejona (`sticky`), a wysokość kolumny liczona z nowych slotów HUD `--hud-action-top`/`--hud-card-top`.
  - Ucięta poświata: niekontrolowane systemy mają `opacity: 0.7` (osobny kontekst warstw) — cel wyboru ma teraz
    zawsze pełną nieprzezroczystość. Systemy bez celu przygasają (`mapPickDim`), kontur celu grubszy, pierścień
    planety-celu na zewnątrz planety i nad żetonami; klik w statki na heksie-celu wybiera system (nie karta jednostki).
  - Wybór „na planecie ALBO w przestrzeni” (Yin Spinner): planeta = klik w planetę, przestrzeń = klik w heks,
    jednym kliknięciem (wcześniej luźny kafelek „Space area…” albo dwustopniowy panel).
  - Karta decyzji: chip technologii jest tytułem (bez uciętej, zdublowanej nazwy), tekst 3 linie + „more”, zamiast
    dużego pola „Click a glowing…” jedna linia `MapPickStatus` z liczbą celów, „Show” (przewija mapę do celu
    zasłoniętego dokiem ręki / poza ekranem) i „Pick here”, gdy mapę trzyma inne okno.
- Testy: `GroupedMapField.test.tsx` (Yin Spinner 1 i 3 przestrzenie, rejestr dwóch okien), `DecisionFields.test.tsx`.
- QA: tsc ✓, eslint ✓ (zmienione), vitest offers+map+strategy+game-shell 72 ✓, e2e 7 ✓, weryfikacja zrzutami na
  izolowanym backendzie :8100. Backend bez zmian (bez QA backendu, bez restartu).

## 2026-11-16 — Audyt rulingów Arborec (kontrakt rulingów)

- Arborec zdjęty z `UNAUDITED` (`tests/test_ruling_coverage.py`): 58 punktów kontraktu (`python -m tests.rulings
  arborec`) = 52 z testem `@ruling` + 6 statusów (3 wpisy) w `tests/rulings_status.json`.
- Nowy `tests/factions/test_rulings_arborec.py` (32 testy): Mitosis (piechota Letani na planecie doku, dok produkuje
  Letani Behemoth, decyzja obowiązkowa), Stymie Ω (bez domu gracza przy stole), Bioplasmosis (łańcuch A–B–C, ruch
  jednoczesny, mech nie rusza się), Letani Warrior (sumowanie PRODUCTION, dowolny podział, LW II: statystyki, rzut,
  powrót), granty flagowca/commandera/bohatera (płatne, bez Sarween Tools, blokada statków, siły naziemne na dowolną
  planetę albo w przestrzeń, jednostka z planszy nieuszkodzona), Letani Ospha (bez zniszczenia/produkcji, Sarween nie
  podnosi limitu, statek z planszy nieuszkodzony, myśliwiec). Znaczniki dopisane do istniejących testów
  (`test_arborec.py`, `test_leaders.py`).
- Statusy „na”: `F_arborec/stymie/*` (stara karta w strefie gry; assety mają tylko Stymie Ω) oraz
  `letani-warrior/1` i `letani-behemoth/2` (blokada Warfare z PoK; w grze `te6warfare` — „Production abilities of
  the units in your home system”, RULES.md 30.4).
- Silnik bez zmian — wszystkie rulingi były już spełnione.
- QA: testy Arborec + strażnik + leaders + technologies_passive 93 ✓, ruff ✓, mypy (zmienione) ✓. Pełny zestaw
  pominięty (zmiana tylko w testach).

## 2026-11-16 — Okna decyzji intuicyjnie: odznaczanie, sloty „klik = +1”, klik w jednostkę w walce (front)

- Zgłoszenie użytkownika: „No infantry” (Dannel of the Tenth, bohater Yin) nie dawało się odkliknąć; w walce wybór
  jednostki tylko z kafelków. Zasada: gracz planszówki, który nie zna UI.
- Każdy pojedynczy wybór (kafelek albo cel na mapie): ponowny klik odznacza.
- Jednakowe pola wyboru (`slotGroups` w `optionKinds.ts`: kolejne `choice` z identycznymi opcjami) z celami na
  mapie = jedno pole `SlotsMapField`: klik w planetę dokłada 1 sztukę (×2, ×3), chip z − i ×; opcja bez celu
  („No infantry”) nie jest kafelkiem - wolne sloty dostają ją same; komplet = mapa gaśnie.
- Walka (`shipPick.ts`): klik w jednostkę na polu bitwy dla KAŻDEJ decyzji, której pola wskazują jednostki stron
  walki - także obu stron w jednym polu (Viscount Unlenn, Evelyn DeLouis) i wybór wielu (Ambush). Klik zaznacza
  (zielony celownik), ponowny klik odznacza, pojedynczy wybór zamienia się klikiem w inną jednostkę; zatwierdza
  Confirm w panelu środkowym (+ Clear, Skip dla „may”) - przypadkowy klik niczego nie zużywa. Decyzja z opcją bez
  jednostki (odmowa) zostaje w oknie decyzji.
- Testy: `GroupedMapField.test.tsx` (sloty Dannel, odznaczanie), `shipPick.test.ts` (Devotion zaznacz/odznacz,
  Viscount Unlenn obie strony, Ambush do 2, decyzja z odmową).
- QA: tsc ✓, eslint ✓ (zmienione), vitest battle+offers+map+strategy+game-shell 99 ✓. Bez e2e (zmienione
  komponenty nie są montowane stale), bez QA backendu (tylko front). Równoległa sesja (dźwięki walki naziemnej)
  zmienia `BattleFleet.tsx`/`BattleOverlay.module.css` - zacommitowane tylko własne hunki.

## 2026-11-16 — Arborec: trzy poprawki po audycie rulingów

- Planeta bezczynnego producenta (F_arborec Mitosis/1, RULES.md 33): piechota Letani może stanąć na planecie doku
  tylko, gdy dok wyprodukował w tej akcji co najmniej 1 jednostkę (`production._check_idle_producer_zones`: 1 sztuka
  przypisana do tamtejszego producenta + warunek Halla dla reszty). Producent w przestrzeni i granty bez zmian.
- Infantry II / Letani Warrior II / Spec Ops II (RULES.md 55): każda sztuka z karty ma osobny wybór planety w domu
  (jednakowe sloty `planet_1..N`, klik na mapie) — można rozdzielić. Pora bez zmian: początek następnej tury (tekst karty).
- Letani Behemoth (RULES.md 62.5): Mitosis może zamienić także piechotę w przestrzeni (`mech|pozycja|space`, jak Yin Spinner).
- Testy: `test_rulings_arborec.py` (+3), `test_offers.py` (rozdział piechoty). QA: pytest 2552 ✓, mypy ✓, ruff ✓ dla
  zmienionych plików (6 błędów w plikach równoległej sesji: battle.py, card_labels.py). Front bez zmian.
- Restart backendu potrzebny (zmiana kształtu oferty Infantry II).

## 2026-11-16 — Tekst karty raz: bez kopii w podpowiedzi każdego pola

- Zgłoszenie użytkownika (Dannel of the Tenth): pod polem „Infantry commits to” wisiał „Dannel of the Tenth: Infantry 1
  commits to. ACTION: …” - cały tekst karty drugi raz. Źródło: `card_labels.with_default_hints` wpisywał „nazwa: etykieta.
  tekst karty” do KAŻDEGO pola bez własnego `hint` (karty akcji, komponenty frakcji, relikty). Okna (ActionCardPlayModal,
  FactionComponentUseModal, Technology/LegendaryUseModal, OfferDock) i tak pokazują tekst karty nad formularzem.
- Usunięte `with_default_hints` i trzy wywołania; `hint` to wyłącznie porada hooka (np. „+2 = number of your ship types”).
- Test `test_card_labels.py`: zamiast „każde pole ma hint” - żaden hint nie jest kopią tekstu karty / „nazwa: …”.
- QA: pytest 2552 ✓, mypy ✓, ruff ✓ na zmienionych plikach (I001 w `api/routers/battle.py` to zmiana równoległej sesji).
  Wymaga restartu backendu.

## 2026-11-16 — Dźwięki walki z próbek CC0 + przebudowa walki naziemnej (piechota ≠ mech)

- Syntezowane „pikanie” zastąpione próbkami: `assets/extra/sfx/battle/<zdarzenie>-<n>.ogg` (114 plików, 1,3 MB, CC0:
  Kenney, OpenGameArt, Free Firearm Sound Library; spis w `SOURCES.md`). Warianty losowane bez powtórzeń z rzędu, ±5%
  wysokości; synteza zostaje tylko jako zapas. `GET /battle/sounds` zwraca też `files` (podkatalog `battle/`, każdy
  format audio) — wymaga restartu backendu.
- Walka naziemna: piechota strzela seriami 3 kul smugowych (karabin), mech z działa (łuk, odrzut, wybuch także przy
  pudle). Śmierć piechoty: odrzut, upadek na plecy, kurz, okrzyk + upadek ciała (limit krzyków). Śmierć mecha: iskry
  z pancerza, dym, gasnący reaktor, osunięcie, wybuch z odłamkami, płonący wrak. Sustain mecha = łomot pancerza.
  Desant: świst kapsuł, przyziemienie z kurzem; jednostki mają własny „oddech” (bez dryfu okrętów).
- Inwazja (dotąd cicha): dźwięki bombardowania, lancy war suna, Space Cannon Defense i lądowania kapsuł.
- Pliki: `battleSound.ts`, `GroundDeathFx.tsx` + `GroundCombat.module.css` (nowe), `BattleFleet.tsx`,
  `BattleOverlay.tsx/.module.css`, `InvasionFx.tsx`, `routers/battle.py`, `routers/audio.py` (`audio_files` publiczne).
- Testy: `groundCombatFx.test.ts`, `strikeSounds.test.ts`, `test_battle_sounds.py`. QA: vitest battle/invasion/audio ✓,
  tsc ✓, eslint ✓, build ✓, pytest (dźwięki/audio/actor_guard) ✓, ruff/mypy zmienionych ✓. Bez e2e i bez weryfikacji
  wizualnej w przeglądarce (do sprawdzenia na żywej bitwie).


## 2026-11-16 — Audyt rulingów Yin + przejęcie kontroli po Quantum Dissemination

- Błąd zgłoszony przez użytkownika: po bohaterze Yin nie działało przejęcie kontroli. Planeta bez obrońców dawała
  „prostą” inwazję (panel kroku taktycznego INVASION), a inwazja komponentu nie ma akcji taktycznej - nic nie
  prowadziło jej do Establish Control. `InvasionResponse.source`; inwazja komponentu zawsze `simple=False`, bez
  „cargo” z orbity (F_yin Ω 4.1); `InvasionOverlay`: etykieta „Continue to ground combat” i podpowiedź kroku Commit.
- Mecatol Rex z żetonem Custodians: zgodnie z decyzją użytkownika (RULES.md 62.10) bohater nie zdejmuje żetonu -
  test przez API (brak celu w formularzu, 422 przy ręcznym celu).
- Luki znalezione audytem: Space Cannon Defense nie istnieje w inwazji komponentu (`defense_planets` puste,
  „Players cannot use SPACE CANNON”); Mallice przed odwróceniem - flip Nexusa przenosi klucze planety w
  `InvasionState`, więc Yin przejmuje Mallice; Greyfire Mutagen Ω nie drugi raz w tej samej walce (F_yin Ω 1.3).
- `tests/factions/test_rulings_yin.py` (30 testów) + znaczniki `@ruling` w `test_yin.py` / `test_flows_yin.py`;
  `rulings_status.json`: stare warianty sprzed Codexu (Greyfire, Spinner, Milor, Omar, Spinner Overdrive) oraz
  Milor Ω 8/8.1 (jednostka statek+siła naziemna = tylko naaz_voltron, Naaz-Rokha niezaimplementowana). Yin zdjęty
  z UNAUDITED. RULES.md 62.10: usunięte nieaktualne ⚠️ ZAŁOŻENIE o Parley (ruling F_yin Ω 7 - działa).
- QA: pytest 2582 ✓, ruff ✓, mypy zmienionych ✓, tsc ✓, eslint ✓, vitest invasion ✓. Bez e2e/build (brak nowych
  modułów). Wymaga restartu backendu (nowe pole widoku inwazji).

## 2026-11-16 — Pole bitwy: giną kliknięte sztuki, bez ponownego wlotu, ciszej, więcej animacji

- Błąd „giną nie te sztuki”: id egzemplarza wynikało z indeksu, a silnik zwraca tylko liczby — po zniszczeniu
  klikniętego znikał ostatni z typu. `shipIdentity.ts` (`reconcileShips`/`useStableShips`): id stabilne między
  odczytami, zmiany liczb trafiają w egzemplarze z zamiaru gracza (Confirm przypisania: destroy/sustain; wskazanie
  w decyzji, np. Assault Cannon: prefer), bez zamiaru — od końca szeregu. Konający okręt zostaje na swoim miejscu
  w szyku (`useDyingShips`). U przeciwnika w sieci (bez jego zamiaru) nadal heurystyka.
- Błąd „statek wlatuje drugi raz” (Assault Cannon na starcie walki): wlot floty miał wyższą specyficzność CSS niż
  śmierć — ginący w trakcie wlotu dostawał `fleetFly`. Teraz śmierć wygrywa (też desant naziemny); pamięć wlotu
  kasowana dopiero po 4 s bez walki.
- Ciszej: próbki 0,42 (było 0,8), wlot floty/desant/kroki mecha ściszone; wszystkie dźwięki walki przez kompresor.
- Animacje: `BattleAmbience` (kosmos: paralaksa gwiazd, mgławica, błyski odległej bitwy; ziemia: artyleria za
  horyzontem, dym, żar), błysk i szarpnięcie trafionej jednostki, leje po pociskach artylerii, zwycięzca robi krok
  naprzód ze złotą poświatą.
- Testy: `shipIdentity.test.ts` (+6). QA: vitest battle/invasion ✓, tsc ✓, eslint ✓, build ✓. Front-only. Bez e2e
  i bez podglądu w przeglądarce.


## 2026-11-16 — Audyt rulingów Hacan

- `tests/factions/test_rulings_hacan.py` (31 testów): każdy punkt `F_hacan.md` i każde zdanie kart Hacan ma
  `@ruling`; znaczniki w `test_flows_hacan.py`; Hacan zdjęty z `UNAUDITED` (bez wpisów w `rulings_status.json`).
- Gila the Silvertongue przez Alliance (F_hacan 1.2): commander z oknem użycia z Alliance / Yin Ascendant trafia do
  komponentów posiadacza (`faction_components.borrowed_commanders`), bez kosztu i bez zmiany stanu u właściciela.
  Wcześniej posiadacz Alliance Hacan nie mógł użyć Gili.
- Carth of Golden Sands: zablokowany, gdy leży ujawniona karta eksploracji (F_hacan 3).
- Quantum Datahub Node: 3 TG sprawdzane przed wydaniem żetonu (F_hacan 3).
- RULES.md 62.6 i 61 (Alliance) uzupełnione.
- QA: pytest 2613 ✓, ruff ✓, mypy ✓. Front bez zmian. Wymaga restartu backendu.

## 2026-11-17 — Audyt rulingów Jol-Nar

- `battle.resolve_afb`: wpis rzutu AFB ma modyfikator 0 (wcześniej modyfikator combat jednostki,
  więc po przerzucie Agnlan Oln trafienia AFB Jol-Nar liczyły się z −1 z Fragile — F_jol_nar/fragile/1).
- Research Agreement: jedno badanie Jol-Nar daje technologię przez notkę tylko raz (F_jol_nar 2.2) —
  wcześniej notka przekazana trzeciemu graczowi działała ponownie dla tego samego badania.
- `tests/factions/test_rulings_jolnar.py` (28 testów), `@ruling` w `test_jolnar.py`; statusy: umowy
  niewiążące (na), Nekro Alliance + Genetic Memory (requires nekro). Jol-Nar zdjęty z UNAUDITED.
- RULES.md 62.3.

## 2026-11-17 — Pole bitwy: zgony rozłożone w czasie, tło w panelach, poprawki walki naziemnej

- Zweryfikowane zrzutami prawdziwej walki (izolowany backend :8100 + Vite :5273, scenariusz z `flow_harness`).
- Zgony jednej salwy co 280 ms (`useDyingShips` → `dieDelay`, CSS `--die-delay` we wszystkich animacjach śmierci,
  dźwięki przesunięte); limit dźwięków: zwykłe wybuchy 2/0,5 s, krzyk piechoty 1/0,9 s, wybuch mecha 2/0,6 s.
- Domykanie szyku (FLIP, `useCloseRanks`): po śmierci ocalałe płynnie dosuwają się zamiast przeskakiwać.
- `BattleAmbience` przeniesione do pól flot (wcześniej zasłonięte panelami): mgławica w barwie strony, paralaksa
  gwiazd, pył, dalekie wybuchy; na ziemi łuna artylerii, podmuchy pyłu, dym, żar.
- Walka naziemna: piechota kuli się i zapada w kurz (zamiast żetonu leżącego na boku), pocisk mecha podłużny ze
  smugą, wybuch bez wielkiej elipsy, bez rozbłysku całej formacji, wyraźniejsze kule, Sustain mecha = iskry.
- QA: tsc ✓, eslint ✓, vitest battle/invasion ✓, build ✓. Front-only.

## 2026-11-17 — Audyt rulingów Letnev

- Non-Euclidean Shielding: Sustain musi anulować 2 trafienia, gdy są co najmniej 2 (F_letnev 3) —
  `battle.plan_losses` przepuszczał zniszczenie jednostki + Sustain anulujący 1. Dotyczy walki,
  bombardowania i Space Cannon.
- War Funding Ω: raz na rundę walki (F_letnev Ω 1.3/1.4) — wcześniej notkę odzyskaną transakcją albo
  przekazaną atakującemu po zagraniu przez obrońcę można było zagrać ponownie w tej samej rundzie.
- Rear Admiral Farran: odblokowanie dopiero po usunięciu nadwyżki puli floty (F_letnev 1) — wcześniej
  `refresh_unlocks` odblokowywał przy otwartym oknie `FLEET_POOL`; TG z kilku Sustainów po jednym (4).
- `tests/factions/test_rulings_letnev.py` (28 testów), `@ruling` w `test_letnev.py`; statusy: stara
  War Funding i bazowy Magen (na), Ul + Alliance (requires titans). Letnev zdjęty z UNAUDITED.
- RULES.md 62.2.
- QA: pytest 2669 ✓, ruff ✓, mypy ✓. Front bez zmian. Wymaga restartu backendu.
