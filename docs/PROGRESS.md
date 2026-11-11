# Postęp projektu — Custodian Engine

Plik śledzi stan prac między sesjami. Aktualizowany na koniec każdego bloku.
Starsze, ukończone bloki (Faza 1 → E4·UI²) są w `PROGRESS_ARCHIWUM.md`.

> **Aktualny etap:** E8 (silnik-SĘDZIA) + fazy C/H: punkty centralne ✅, szkielet hooków ✅, karty akcji w toku.
> **Cel bieżący:** WSZYSTKIE karty gotowe i zagrywane przeciąganiem z ręki (`PLAN_PELNA_ROZGRYWKA.md`, sekcja
> „CEL PRODUKTOWY”); stan pokrycia: `POKRYCIE_HOOKOW.md` (generowany). Reguły: `RULES.md` 29, 43, 53.

## Status etapów silnika

| Etap | Zakres | Status |
|---|---|---|
| Faza 1 | Cyfrowa plansza + God-Mode (dane, mapa, setup, edycja, Undo) | ✅ ukończona |
| F0–F18 | Migracja na frontend ti4_web + panele graczy + God-Mode UI | ✅ ukończone |
| E1–E2 | Fazy + kolejność tur + faza strategii | ✅ ukończone |
| E3 | Akcja taktyczna (aktywacja, ruch, walka, inwazja, produkcja) | ✅ fundament |
| E4 | Kontrola komponentów (exhaust/refresh) + menu RMB | ✅ ukończone |
| E8 | Silnik-SĘDZIA: walidacja reguł + okna czasowe (T1–T7 + faza akcji 31.7/31.8) | 🔧 w toku |
| C | Punkty centralne C1–C9 (strażnik architektury) | ✅ ukończone |
| H1–H3 | Hooki: rejestr, punkty MODIFY/PERMIT/FORBID, raport pokrycia | ✅ ukończone |
| H4 | Karty akcji: zagrywanie ACTION + formularz + zagrywalność + UI z przeciąganiem (16/143 kart) | 🔧 w toku — cel: komplet |
| E6 | Faza agendy (głosowanie, remis, prawa); efekty agend | ✅ głosowanie / ⬜ efekty |
| H1b | STOP + pauza + predykaty zagrywalności (karty reakcji) | ⬜ model w RULES.md 43.4 |
| H5 / N | Frakcje (zdolności) / sieć (`actor_id`, tokeny, push per gracz) | ⬜ |

**Następne kroki (kolejność):** pozostałe karty ACTION (kolejka w `POKRYCIE_HOOKOW.md`) → efekty agend → hooki
at_start/at_end/during → STOP i karty reakcji → relikty / promissory notes / eksploracja → frakcje → sieć.

> Pełna historia ukończonych bloków ze szczegółami: `PROGRESS_ARCHIWUM.md`.

---

### ✅ Zegar szachowy graczy (2026-11-11) — RULES.md 58
- Backend: `core/game_clock.py` (holder, `settle`, pauza, `snapshot`), `GameState.clock`, rozliczanie w
  `StateService.replace_state`, `POST /clock/pause|resume`, `chess_clock` w `/game/new`, `chessClock` w web-data.
- Front: Ustawienia → „Chess clock” (pula minut + dodatek s), pasek `domains/clock/ChessClockPanel` nad mapą
  (pozostały czas każdego gracza, czas tury holdera, pauza). Testy: `tests/test_game_clock.py`, `clockMath.test.ts`.
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

## ✅ Setup: 3 kroki + pełna paleta kolorów AsyncTI4 (2026-11-09)
- Kroki: **Players & map** (nazwa, człowiek/bot, mapa) → **Faction** → **Seat & color** (miejsce przy stole + kolor + podpowiedź kolorów preferowanych przez frakcję). Między graczami a frakcją docelowo lobby/moduł sieciowy.
- Kolory: wszystkie 80 kolorów AsyncTI4 (standard / split / specjalne). Backend: core/player_colors.py (czyta pliki kolorów, normalizuje nazwę → alias kanoniczny, np. white→lgy), _available_colors() w game.py. Front: domains/setup/playerColors.ts; do entities/data/colors.ts dopisano brakujące gradienty (nea, psy, cam, blt).
- Miejsce = home_position (pozycje z /engine/config.seats); kolor/miejsce zajęte przez innego gracza = zamiana (brak duplikatów). Gracz z losową frakcją nie ma jeszcze preferencji kolorów.
- ⚠️ Kolejność przy stole/mówca nadal wynika z kolejności graczy w kroku 1, nie z wybranego miejsca (do ustalenia).

## ✅ Faza agendy: Rada Galaktyczna (2026-11-08) — RULES.md 51

`core/agenda_phase.py` (ujawnienie → głosowanie od lewej mówcy, mówca ostatni → wynik / remis rozstrzyga mówca →
druga agenda → odświeżenie planet → `Next phase`), router `/agenda/*`, web-data `agendaPhase`, okno
`domains/agenda/AgendaOverlay` (Senat w półkolu, podium z kartą i słupkami głosów, urna z planetami; tło `agenda2.jpg`).
Efekty agend NIE kodowane (wynik tylko zapisany; prawa w `decks.agenda_laws`). Założenia: RULES.md 51. Testy:
`tests/test_agenda_phase.py`. Zmiana: wejście w AGENDĘ wskazuje mówcę (nie inicjatywę).

## ✅ Thunder's Edge: ekspedycje + The Fracture + Thunder's Edge (2026-11-08) — RULES.md 50

Cały układ i koszty modułu — BEZ kodowania zdolności przełomów / legendarnej zdolności Thunder's Edge.

- **Ekspedycje** (`core/expeditions.py`): 6 plastrów żetonu (5 zasobów / 2 karty akcji / 5 wpływu /
  1 tajny cel / planeta ze specjalnością / 3 TG), 1 plaster na turę, tylko na koniec tury (po akcji lub
  pasie). Pierwsza ekspedycja = przełom (`core/breakthrough.py`, punkt centralny) + rzut d10 na Fracture.
- **The Fracture** (`core/fracture.py`): 1 lub 10 wprowadza 7 kafli `frac1..7`, neutralni z odwrotu kafli,
  ingress (3 na kolor synergii / po 1 na 4 kolory, auto gdy kandydatów mało, +1 na Mecatol albo Thunder's Edge),
  egress z danych kafla; graf mapy: ingress<->egress (krawędź `portal`). Mapa synchronizowana ze stanu → Undo działa.
- **Neutralni** (`core/neutral.py`): klucz `"neutral"` w jednostkach; walka kosmiczna i naziemna z nimi działa,
  straty neutralnych przypisuje silnik (najtańsza jednostka, zawsze Sustain), nie kontrolują planet.
- **Relikt** za pierwszą kontrolę planety w Fracture (`control.set_planet_control(..., registry)` →
  `core/relics.py`); talia reliktów leniwie z aktywnych źródeł. Efekty reliktów nie kodowane.
- **Thunder's Edge**: po 6. plastrze gracz kładzie planetę w pustym systemie; lider ekspedycji stawia piechotę
  i przejmuje kontrolę (`SystemState.added_planets`, `core/system_planets.py`).
- API: `GET /thunders-edge`, `POST /expeditions/perform`, `/fracture/ingress`, `/thunders-edge/place`,
  `/god-mode/fracture`. web-data: `expeditions`, tokeny ingress/thundersedge/relictoken, `gameState.thundersEdge`.
- Front: przycisk **Expedition** w `TurnControls`, `ExpeditionModal`, `ThundersEdgeOverlay` (baner kostki,
  dok ingress i dok Thunder's Edge z wyborem na MAPIE), układ: **Fracture u góry, pod Mallice, nad planszą i
  polami graczy** — plansza przesunięta o `FRACTURE_Y_BUMP` = 1050 (wolny pas ok. 200 px między nimi).
- **⚠ Do potwierdzenia:** liczby neutralnych na kaflach (z AsyncTI4), odrzucony tajny cel wraca do talii,
  statystyki neutralnych = bazowe jednostki, rzuty neutralnych robi silnik. Układ UI nieweryfikowany wizualnie.
- **Poza zakresem (następny krok):** zdolności przełomów (w tym Cabal / Onyxxa / Vuil'raith wprowadzające
  Fracture), legendarna zdolność Thunder's Edge, efekty reliktów, kafle `ef*` (rozszerzony Fracture), wpisy
  feedu aktywności dla nowych etykiet (`expedition:*`, `fracture:ingress:*`, `thunders-edge:place:*`).
- **QA:** `tests/test_thunders_edge.py` (29 testów); pełne: pytest, ruff, mypy; front: type-check, lint, build.

## ✅ Feed aktywności „kto co zrobił" (2026-11-08)

Panel History/Events miał pustą zakładkę zdarzeń (`/events` zwraca `[]`) i surowe etykiety migawek.
Teraz ma dwie zakładki: **Activity** (domyślna) i **Snapshots** (dawny HistoryPanel, cofanie).

- `core/activity.py` — czysta `derive_activity(label, before, after)`: aktor/cel/temat z etykiety
  commitu + skutki z RÓŻNICY stanów (VP, TG, technologie, planety). Etykiety czysto wewnętrzne
  nie tworzą wpisu, chyba że niosą skutek (np. badanie technologii w „kroku" → `misc/update`).
- `EventStore`: kolumny `created_at`, `activity_json` (migracja idempotentna); `StateService.replace_state`
  zapisuje wpis przy każdym commicie. Endpoint `GET /history/activity` (+ słownik graczy, `current_seq`).
- Front: `domains/game-shell/components/ActivityPanel/` — wiersze z ikoną frakcji, jednozdaniowy opis,
  chipy skutków, grupy rund, filtry kategorii i gracza, wpisy cofnięte Undo przygaszone, licznik nowych
  wpisów na przycisku. Nazwy (planety, techy, karty strategii, cele) rozwiązuje front z własnych lookupów.
- Ograniczenie: aktor z etykiet bez `player_id` to gracz aktywny PRZED commitem (np. `leader:*`).

## ✅ Ekran zwycięstwa + epilog + limit 10 rund (2026-11-08) — RULES.md 48

- Backend: `GameState.max_rounds` (10), `end_reason`, `epilogue`; `finish_status` kończy grę po
  rundzie granicznej; `core/epilogue.py` (głosowanie bez zwycięzcy, większość, remis → honorowe,
  boty głosują same) + `/epilogue/open|vote`; web-data: `endReason`, `maxRounds`, `epilogue`.
- Front: `domains/victory/VictoryScreen` — triumph (portret frakcji) → głosowanie → Kronika
  epilogu (crawl jak w intrze) → klasyfikacja i „nagrody". Montowany w `GameMapPage`.
- **Do uzupełnienia**: teksty kart epilogów per frakcja w `domains/victory/factionEpilogues.ts`
  (`FACTION_EPILOGUES`); do tego czasu działa ogólny zapychacz.

## ✅ Aktywne talie = wersje po rozszerzeniach (agendy / karty akcji / relikwie) (2026-11-08)

Audyt względem wiki TI (Agenda Cards, Action Cards) i upstreamu AsyncTI4:
- **Błąd silnika:** `objectives.deck_card_ids` przy remisie rozmiaru brał `agendas_base_game`
  (50) zamiast `agendas_pok` (50) — czyli stare agendy sprzed PoK. Remis rozstrzyga teraz
  priorytet źródła talii (RULES.md 14).
- **Błąd UI:** pule kart (przeglądarka, edytor ręki, stosy talii) filtrowały tylko po źródle,
  więc pokazywały 63 agendy (13 usuniętych w PoK), 143 karty akcji (3 nadliczbowe) i 24 relikwie
  (Enigmatic Device wycofane w TE). Front czyta teraz `entities/data/activeDecks.ts`,
  generowany z silnika: `uv run python scripts/gen_active_decks.py` (po zmianie assetów).
- Skład po poprawce: agendy 50 (PoK), karty akcji 140 (80 base + 20 codex I + 20 PoK + 20 TE),
  relikwie 23, tajne cele 40, cele publiczne 20+20 — zgodne z wiki. Test:
  `tests/test_active_decks_sync.py`.
- ⚠️ Otwarte: teksty 4 kart akcji (Fighter Conscription, Blitz, Ghost Squad, War Machine) mają
  starsze brzmienie z Codexu I; TE dał im Ω-sformułowanie (bez zmiany mechaniki). Dane pochodzą z
  assetów AsyncTI4 — nie edytujemy ich ręcznie.

## ✅ Akcja taktyczna: bez potwierdzeń, pomijanie pustych kroków, zasięg ruchu (2026-11-08)

- „Next step"/„End action" bez drugiego kliknięcia.
- `tactical.advance_skipping_empty` (używane przez `/tactical/step/next`): pomija Space Cannon
  (brak strzelców), Space Combat (brak dwóch flot), Inwazję (brak lądowania/bombardowania)
  i Produkcję (brak producentów); gdy pominięty ostatni krok, akcja się kończy.
- MovementStepPanel: lista „In range" (systemy źródłowe, statki, pojemność/ładunek); klik
  otwiera kreator z wybranym źródłem.

## ✅ Eksploracja planet po Establish Control (2026-11-07) — RULES.md 46

Przejęcie niczyjej planety z cechą (cultural/hazardous/industrial) otwiera okno eksploracji:
karta dobierana automatycznie (jedna planeta, jedna cecha) albo gracz wybiera kolejność planet i
talię; każda karta rozstrzygana w całości (opcje z powodami niedostępności), potem „Done exploring".
Backend: `core/exploration.py`, `routers/exploration.py` (`GET /exploration`, `POST /exploration/{draw,
resolve,finish}`), `GameState.exploration`, `DecksState.exploration_deck/_discard`,
`planet_attachments`, `PlayerState.relic_fragments`; blokada zamknięcia inwazji i wyjścia z kroku
do końca eksploracji. Front: `domains/exploration/`; panel prostej inwazji ma teraz „Close invasion".
Testy: `tests/test_exploration.py`, `tests/test_exploration_api.py`.
**Domknięte w tej samej sesji (RULES.md 46 X6–X8):** `core/planet_stats.py` (attachmenty zmieniają
zasoby/wpływy/specjalności w produkcji, celach i ekonomii), Freelancers przez okno produkcji
(`GameState.production_grant`, `POST /tactical/production/skip-grant`, UI: `ProductionOverlay` w trybie
karty), Gamma Wormhole jako żeton w systemie (`SystemState.wormhole_tokens`, `HexGrid.sync_token_wormholes`,
synchronizacja przy odczycie `ctx.current_grid`).
**Stosy kart w General (RULES.md 46.4):** talie pokazują, ile kart ZOSTAŁO (dobrane znikają), każda
talia (eksploracja ×4, akcje) ma stos odrzuconych, jest wspólny stos purge; w oknie talii szansa dobrania
każdej karty (%), zakładki Talia/Odrzucone/Purge i tryb Debug („Make next", przenoszenie kart,
`POST /decks/move`). Kod: `core/deck_piles.py`, `routers/decks.py`, front `domains/cards/components/DeckInspector`.
**Do zrobienia:** eksploracja frontier (Dark Energy Tap), rozstrzyganie fragmentów reliktów, handel w
oknie po ujawnieniu karty, reguła „zdejmij jednostkę z planszy" przy braku w rezerwie.

## ✅ Transakcje między graczami + żetony długu (debt) (2026-11-07) — RULES.md 47

Przycisk **Transaction** w pasku fazy akcji (`TurnControls`) otwiera `TransactionModal` (ładny
modal, 2 zakładki). Core: `core/transaction.py` (1 transakcja na sąsiada na turę, `PlayerState.
transacted_with` zerowane z nową turą; TG/commodities/1 notka/fragmenty reliktów; commodity → TG
u odbiorcy; nie jest akcją tury, nie blokuje go okno ani pas) i `core/debt.py` (nieformalne
żetony długu (debt) `GameState.debt_tokens`, bez sąsiedztwa, w dowolnej chwili). API:
`/transactions/resolve`, `/debt/give|return`; web-data: `transactedWith`,
`relicFragmentCards`, `debtTokens`. Testy: `tests/test_transaction.py`.
**Poza zakresem (⚠️ RULES.md 47.2):** Hacan (karty akcji — hook E7), zwrot pojmanych jednostek,
transakcje w agendzie (agendy poza zakresem), zgoda partnera (hot-seat: jeden operator).

## ✅ Setup graczy domknięty (2026-11-07) — RULES.md 45

`/game/new` zostawia grę w setupie: ręka promissory notes (5 wspólnych + 1 frakcyjna), 2 tajne cele
na gracza (zatrzymaj 1, drugi do talii), żeton Custodians kładzie mówca, mówca klika i odkrywa dwa
cele I etapu (pozostałe 8 zakryte). Backend: `core/game_setup.py`, `routers/setup.py`, `web_setup.py`;
front: `GameSetupOverlay`. Wybór karty strategii zablokowany do końca setupu. Testy: `tests/test_game_setup.py`
(+ `tests/setup_helpers.py::finish_setup` w testach faz gry). Do zrobienia: ręka notek w oknie setupu,
wysyłka kandydatów tylko właścicielowi w grze sieciowej.

## ✅ Wybór frakcji — sekcja „Faction components" (2026-11-07)

Panel `FactionSummary` pokazuje specjalne żetony/karty frakcji (ikona + liczba + nazwa, opis w
tooltipie): Creuss (Alpha/Beta/Gamma), Naalu („0"), Nekro (X/Y/Z), Empyrean (Void Tether ×2),
Titans (Sleepers ×5), Cabal (Dimensional Tear), Crimson (Breach ×7, Sever), Bastion (Galvanize ×7),
Deepwrought (Ocean cards ×5), Firmament/Obsidian (Plot cards ×5). Dane: `frontend/src/domains/setup/
factionComponents.ts` (źródła liczb w nagłówku pliku). Komponenty-jednostki/planety zostają w
„Breakthrough component". ⚠️ ZAŁOŻENIA do potwierdzenia: Valefar „Z" ×7 (limit z AsyncTI4),
Dimensional Tear ×3 (jeden na dok), Void Tether ×2 (z logiki `VoidTetherService` bota).
Ingress tokeny (Fracture) celowo pominięte — wspólny komponent gry, nie frakcji.

## Starsze bloki E8 (akcja taktyczna, okna czasowe, testy 4.4; 2026-11-06..08)

Przeniesione do `PROGRESS_ARCHIWUM.md` (sekcja „Przeniesione z PROGRESS.md”). Czytaj tylko punktowo, gdy potrzebny historyczny szczegół.

## 2026-11-09 — Bombardowanie bez artefaktów, fizyczne kości, wlot floty raz
- Bombardowanie (`invasion/InvasionFx.tsx`, CSS): pocisk leci prosto w punkt na globie (`shellPath`), znika na trafieniu (ostatnia klatka opacity 0, fill `backwards`), trafienie = błysk + pierścień + iskry, błysk wylotu na okręcie. Koniec "paska" po strzale.
- Walka: `battle/DiceTray.tsx` + `diceRoll.ts` — fizyczny rzut d10 (wlot z krawędzi, 3 odbicia, obrót 3D, cień, stuknięcia w WebAudio `diceThrow`/`diceClack`); strzały ruszają po wylądowaniu kości (`Volley.diceMs`), wynik w tacy ukryty do tego czasu.
- Bug: szybkie Roll/Auto powodowało ponowny wlot floty (przemontowanie okrętów przed końcem wlotu) — `BattleFleet.skipEntry` kończy wlot od pierwszej salwy/przypisania.

## 2026-11-09 (2) — Kości d10 w 3D i pula po przytrzymaniu Roll
- `battle/dieGeometry.ts` (+ test): prawdziwy d10 (pięciokątny trapezościan, 10 ścianek-latawców, przeciwległe sumują się do 11), `DieMesh.tsx` renderuje bryłę, `DiceTray.tsx` animuje pętlą rAF (oświetlenie liczone w każdej klatce). Kostki większe (42-84 px) i wolniejsze (`DIE_MS` 2300 ms).
- `DicePool.tsx`: przytrzymanie Roll/Fire barrage (>240 ms) zbiera kości obu stron w puli z licznikiem; puszczenie nad przyciskiem rzuca z puli, puszczenie poza nim anuluje. Zwykłe kliknięcie rzuca od razu.

## 2026-11-09 (3) — Technologie ogólne jako hooki, blok 1 (RULES.md 55)

- Nowe punkty zaczepienia: `turn.actions`, `status.action_cards`, `status.command_tokens`, `space_cannon.roll_modifier`, `space_cannon.extra_dice`, `bombardment.extra_dice`; `rules_hooks.declare_data_driven` (pokrycie z danych).
- `core/action_budget.py`: jedyne miejsce bramki i rejestracji akcji tury (limit z hooka); `PlayerState.actions_this_turn`; web-data `actionsLeft`, UI odblokowuje przyciski akcji dopóki zostały akcje.
- `space_cannon.roll_cannon`: jeden punkt rzutów Space Cannon (Offense + Defense).
- Gotowe: Fleet Logistics (`fl`), Neural Motivator (`nm`), Hyper Metabolism (`hm`), Antimass (`amd`, także −1 do Space Cannon), Light/Wave (`lwd`), Plasma Scoring (`ps`), Sarween Tools (`st`), ulepszenia `ws/cr2/dd2/cv2/pds2/dn2` (dane).
- Testy: `tests/test_technologies_general.py`. Zostało: technologie z wyborem gracza / oknami (patrz kolejne wpisy).
- Luka sieciowa: `actor_id` mają tylko 4 endpointy akcji (karty akcji, Thunder's Edge) — osobny blok (RULES.md 44.1).

## 2026-11-09 (4) — Technologie ogólne, blok 2: walka i ruch (RULES.md 55.6-55.7)

- Gotowe: Gravity Drive (`gd`), Duranium Armor (`da`), Assault Cannon (`asc`), Magen Defense Grid ΩΩ (`md`), X-89 ΩΩ (`x89c4`); starsze wersje Magen/X-89 oznaczone `declare_superseded`.
- Punkty: `combat.hit_multiplier`; `COMBAT_ROUND` END niesie `phase`/`sustained`/strony; `battle.start_combat` kończy walkę, gdy hooki startu zniszczą stronę.
- Testy: `tests/test_technologies_combat.py` (21).
- Założenia (55.7): wybory ofiary/właściciela rozstrzygane deterministycznie do czasu okna wyboru w UI.

## 2026-11-09 (5) — Technologie ogólne, blok 3: pasywne (RULES.md 55.8)

- Gotowe: Infantry II (`inf2`, rzut na stole + powrót w domu), `sd2`, `dn2` (dane); częściowo (bez `covers`): Dark Energy Tap (odwrót), Psychoarchaeology (specjalności), Self-Assembly (TG za mecha).
- Nowe punkty: `retreat.anywhere`, `technology.specialty_without_exhaust`; `PlayerState.infantry_ii_on_card`.
- Testy: `tests/test_technologies_passive.py` (13).
- Zostały technologie wymagające interakcji (okno ofert „may” + akcje technologii): `aida` (produkcja), `bs`, `dxa`, `gls`, `ie`, `pi`, `sar` (mech), `sdn`, `sr`, `td`, `pa` (TG), `det` (frontier), `ff2` (flota). Mechanizm ofert (`triggers.accept_offer`) jest w core, ale bez endpointu i UI.

## 2026-11-09 (6) — Decyzje graczy zamiast automatów, blok A (RULES.md 56)

- Decyzja użytkownika: technologie nigdy automatycznie; gracz decyduje przyciskiem/oknem. Infrastruktura: `core/offer_inputs.py`, `on_event(optional/decide/inputs/decider)`, `PendingOffer.owner_id/mandatory`, `core/offers.py`, router `/offers`, `pendingOffers` w web-data, `OffersModal` (front, wspólne pole formularza z kartami akcji).
- Walka: krok `TRIGGERS` + `battle.resume_after_triggers`. Przerobione: Assault Cannon (decyduje ofiara), Magen ΩΩ, Duranium Armor, Infantry II; nowe oferty: Dacxive Animators, Bio-Stims.
- Testy: `tests/test_offers.py` (14). Front: build + lint zielone.
- Dalej (bloki B-D): Gravity Drive/GLS/AIDA jako przełączniki w istniejących oknach; Scanlink i Dark Energy Tap przez eksplorację (frontier); Self-Assembly (mech), Integrated Economy, Transit Diodes, Predictive Intelligence; akcje Sling Relay i Psychoarchaeology (dispatch w `component_action`).

## 2026-11-09 (7) — Technologie ogólne: akcje, zdolności, frontier, oferty (RULES.md 57)

- Pokrycie ogólnych technologii: 31 z 33 (brak: Fighter II, Predictive Intelligence - druga zdolność).
- Nowe: dispatch efektów „ACTION:” w `component_action` (+ `TechnologyUseModal`), zdolności poza akcją (`/technology/*`, Psychoarchaeology), produkcja `free` (Sling Relay, Integrated Economy), eksploracja frontier w istniejącym oknie (Dark Energy Tap), oferty Scanlink/Self-Assembly/Transit Diodes/Predictive Intelligence, przełączniki GLS (Space Cannon) i AIDA (produkcja; UI liczy też zniżki hooków).
- Poprawka: `gravityDriveUsed` w web-data/typach (wcześniej brak, przełącznik Gravity Drive nie chował się po użyciu).
- Testy: `tests/test_technologies_actions.py` (25). Front: build + lint zielone.

## 2026-11-11 — Przegląd technologii ogólnych: wskaźniki w UI + luki (RULES.md 57.8)

- Wskaźniki „ta technologia działa tutaj": `core/tech_effects.py` (`TECH_CONTEXTS`), `PlayerData.techEffects`, komponent `shared/ui/ActiveTechs`. Wpięte w: produkcję, ruch (+ „Gravity Drive used"), Space Cannon (strzelec i cel), walkę, inwazję, agendę, fleet pool, fazę statusu, panel tury, badanie technologii.
- Zamknięte luki: Fighter II (nadmiar myśliwców liczy się do fleet pool, nie jest usuwany z capacity), Predictive Intelligence (+3 głosy jako decyzja gracza, wyczerpanie przy przegranym wyniku), X-89 ΩΩ (bombardowanie planety bez sił naziemnych, punkt `bombardment.empty_planets`), Self-Assembly (mech z planszy, gdy rezerwa pusta). Pokrycie ogólnych technologii: 33 z 33.
- Zweryfikowane względem C_technology bez zmian: Fleet Logistics, Dark Energy Tap, Sarween Tools, Integrated Economy, Magen, Duranium Armor, Assault Cannon.
- Niezamodelowane: „statek nie może przechodzić przez system z Fighter II innego gracza".
- Testy: `tests/test_technologies_review.py` (8).
