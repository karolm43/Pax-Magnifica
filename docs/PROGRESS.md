# Postęp projektu — Custodian Engine

Plik śledzi stan prac między sesjami. Aktualizowany na koniec każdego bloku.
Starsze, ukończone bloki (Faza 1 → E4·UI²) są w `PROGRESS_ARCHIWUM.md`.

> **Aktualny etap:** E8 (silnik-SĘDZIA) + hooki: karty akcji 143/143 ✅, relikty ✅, technologie ogólne ✅, cele ✅,
> karty strategii ✅, sieć N0–N3 ✅. **Cel bieżący:** efekty agend, potem frakcje (zdolności, liderzy, notki).
> Stan pokrycia: `POKRYCIE_HOOKOW.md` (generowany). Reguły: `RULES.md` 29, 43, 53.

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
- ~~Luka sieciowa: `actor_id` tylko w 4 endpointach~~ — domknięte 2026-11-11 (6), RULES.md 44.1a.

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

## 2026-11-11 (2) — Audyt silnika: sędzia tury domknięty (RULES.md 31.9, 32.1 R7, 33.1a, 42)

- **Bugi reguł naprawione (core):**
  - `turn_flow.end_turn` kończył turę W TRAKCIE akcji taktycznej (walka/inwazja w toku zostawały następnemu graczowi). Teraz End turn zamyka akcję jak „End action" (`tactical.end_action`): walka/inwazja/okno/obowiązkowa walka kosmiczna → 422; nadwyżka capacity/fleet pool albo reakcje po akcji otwierają okno i ZOSTAWIAJĄ turę graczowi (`/turn/end` przekazuje `registry`).
  - `tactical.activate_system` nie sprawdzał fazy, okna czasowego, pending primary ani pasa — system dało się aktywować w fazie strategii/statusu/agendy i w trakcie secondary (Fleet Logistics). Teraz sędzia jak przy akcji strategicznej/komponentu (`free=True` dla Warfare bez zmian).
  - Ruch: statek zaczynający krok ruchu w mgławicy ma wartość ruchu 1 (R_nebula) — brakowało (`movement.can_move`, R7).
  - Faza statusu liczyła nadwyżkę puli floty własną kopią reguły (bez Fighter II); `status_phase.fleet_excess` używa `fleet_pool.fleet_report`.
- **API:** globalny handler `ValueError → 422` w `create_app` (endpointy bez własnego `try`, np. `/tactical/end`, dawały 500 bez komunikatu).
- **UI:** panel okna czasowego nie pokazuje już generycznych Execute/Pass/Close dla okien z własnym panelem (walka, Space Cannon, pojemność, pula floty, oferty) — tylko wskazówkę, gdzie rozstrzygnąć; wentyle widoczne w God-Mode (ustawienie „Skip phases"). Tooltip End turn w trakcie akcji taktycznej.
- **Porządki:** `tests/test_docs_numbering.py` dostosowany do podziału RULES.md na `docs/rules/` (był czerwony po b98fa85); mojibake w docstringu `card_draw.rearrange_agenda_top`; nota R42 (3) o Fighter II zgodna z kodem.
- Testy: +10 (turn_flow, tactical, movement, status_phase, api).
- **Luki wypisane, NIE zmienione (do decyzji):** Sustain Damage w Space Cannon Offense (`space_cannon.assign_hits` niszczy bez sustain); `/window/respond` i `/window/close` to wentyle bez sędziego (omijają obowiązkowe decyzje — UI je chowa, backend przepuszcza); `turn_flow.next_phase` AGENDA→STRATEGY bez `round_number+1` i bez zwrotu kart (tylko ścieżka God-Mode bez `agenda`); limit ręki kart akcji (7) niemodelowany; pickup ładunku z systemów mijanych; gravity rift.

## 2026-11-11 (3) — Poprawki technologii: Antimass, Sling Relay, Plasma Scoring, Integrated Economy, okno decyzji (RULES.md 55.3, 57.3)
- **Sling Relay / produkcja z kart:** granty (`ProductionGrant`: Sling Relay, Integrated Economy, Freelancers) to „produce”, nie „use PRODUCTION” - `production.produce` nie odpala `PRODUCTION_USED` (Self-Assembly, Sarween nie aplikują się); `UNITS_PRODUCED` nadal tak. Granty `standalone` (Construction/Warfare) bez zmian.
- **Integrated Economy:** okno produkcji nie ma 99 slotów; pokazuje pasek kosztu (limit = zasoby planety), UI nie sprawdza już producentów PRODUCTION dla grantów (powód, dla którego jednostki nie dawały się dodać). `/tactical/production/view` zwraca `grant.maxCost` i `grant.shipsOnly`.
- **Plasma Scoring:** wybiera gracz (`plasma_unit`: klucz grupy strzelców w Space Cannon Offense/Defense, `typ|planeta` w bombardowaniu); bez wskazania brak dodatkowej kości. UI: radio „Plasma Scoring” w panelu Space Cannon, oknie bombardowania i na kartach Space Cannon Defense.
- **Antimass Deflectors:** dziennik rzutów niesie `modifier`/`extraDice`; panele pokazują „−1 to each die” i „6→5” na kościach, a scena kości używa tego modyfikatora.
- **Inwazja UI:** podświetlenie celu przy przeciąganiu wróciło (`dragenter` zamiast `:hover`), statki bombardujące (na orbicie i w doku) przeciąga się na inną planetę (Shift = cały stos), przygotowane do lądowania jednostki widać na orbicie planety jak statki bombardujące.
- **Decyzje „may”:** `OffersModal` to teraz niemodalny panel przy dolnej krawędzi (bez przyciemnienia, plansza klikalna), Enter = użyj, Esc = pomiń, minimalizacja do pastylki; usunięty komentarz „You may use this now…”.
- Testy: +3 (plasma wybór/odrzucenie, produce z karty bez PRODUCTION_USED), vitest `moveBombard`.
- **Sling Relay / Integrated Economy a limity:** `production.produce` dla grantów `free` od razu otwiera okno CAPACITY, a po jego rozstrzygnięciu (`capacity.resolve_capacity`) okno FLEET_POOL w systemie produkcji - limity egzekwowane natychmiast, nie dopiero przy wyjściu z kroku akcji. Test: `test_sling_relay_natychmiast_egzekwuje_pule_floty`.
- **Panel decyzji „may”:** przesuwalny za nagłówek (`useDraggablePanel`, pozycja zapamiętana, dwuklik = reset), przycisk powiększenia i natywne rozszerzanie za róg.
- **Fighter II (ujednolicenie):** UI miało listę statków „o własnym ruchu" bez myśliwca (`SHIP_ONLY_ASYNC`), więc Fighter II nie ruszał sam. Teraz `cargo.isSelfMoving` / `movesAsCargo` czytają `moveValue` z wariantu gracza (drag&drop, grupa Ctrl, MoveQuantityModal, kreator ruchu, podsumowanie capacity); nadal wolno go załadować na nosiciela. Capacity/fleet pool: API wystawia `fightersToFleet` (+`fleetFighters`), `capacityMath`, `CapacityModal` i `FleetPoolWarning` liczą myśliwce ponad capacity jako fleet pool (nie nadwyżkę capacity); `capacity.auto_removal` nie podpowiada już usuwania myśliwców, które nadwyżki nie zmniejszają.
- **Magen Defense Grid ΩΩ:** druga klauzula (trafienie na starcie walki naziemnej) zawsze jest decyzją właściciela (`offer_inputs.choice(always=True)`), także gdy cel jest jeden.
- **Inwazja UI:** jedno tło (`invasion_bombard.jpg`) dla wszystkich podkroków okna inwazji.
- **Transit Diodes - panel graficzny:** oferta TD (pola `unit1..4`/`to1..4`) ma własny wybór w panelu decyzji (`offers/TransitDiodesPicker`): 1) klik w stos sił naziemnych = podnieś (do 4), 2) wskaż miejsce - klik w podświetloną na mapie własną planetę (`mapPick`) albo chip planety; wskazana jednostka na liście, kolejna wybierana automatycznie. Backend: `offer_inputs.option(meta=...)` niesie strukturę opcji (system, strefa, typ, liczba, nazwa planety); format parametrów bez zmian, więc silnik waliduje jak dotąd. Test `test_transit_diodes_opcje_niosa_dane_dla_graficznego_wyboru`.

## 2026-11-11 (4) — Karty akcji: komplet ACTION + karty reakcji w oknach (RULES.md 53, 53.5)
- **Stan:** 135 z 143 kart akcji ma efekt w silniku (było 16). Bez efektu zostało 8, wszystkie wymagają ANULOWANIA już wykonanego kroku (model STOP, 43.4): Sabotage x4, Public Disgrace, Coup d'Etat, Political Stability, Crash Landing.
- **Karty ACTION (43 id):** nowe moduły `core/hooks/action_cards_economy.py` (technologie, relikty, planety, ekonomia) i `action_cards_board.py` (neutralni, żetony, plansza, Overrule/Strategize) + formularze `action_card_inputs_*`. Nowe funkcje centralne: `technology.return_technology`, `exploration.reveal_fragments`, `command_tokens.place_on_board_from_reinforcements/return_board_token_to_pool`, `strategic_action.begin_overrule_primary/begin_strategize_secondary`, `board_graph` (mapa dla efektów: systemy domowe, wormholes, sąsiedztwo), `state_grid`.
- **Karty reakcji (when/after/before/start/end):** `core/reaction_cards.py`. Okna są WYLICZANE ze stanu gry przez `@window_provider` (krok walki, agendy, akcji taktycznej, faza...), adres karty z tekstu okna (`classify_window`), nadpisywalny `declare_reaction`. `action_cards.playability` oznacza kartę reakcji jako zagrywalną, gdy pasuje otwarte okno; `play_action_card` zagrywa ją bez zużycia akcji (także gracz nieaktywny). Efekt trwały = `active_effects` + hook `SOURCE_EFFECT` (`card_effect_source`).
- **Grupy kart:** `reactions_agenda` (ridery, Veto, Diplomatic Pressure, Hack, Insider, Bribery, Distinguished, Confounding/Confusing, Deadly Plot, Ancient Burial Sites), `reactions_tactical` (Flank Speed, Lost Star, Nav Suite, Solar Flare, Rally, Upgrade, Counterstroke, Decoy, Forward Supply Base, Rescue, War Machine, Infiltrate, Reparations...), `reactions_combat` (Morale Boost, Skilled Retreat, Shields Holding, Direct Hit, Reflective Shielding, Fire Team, Salvage, Waylay, Rout, Intercept...), `reactions_invasion` (Blitz, Bunker, Disable, Ghost Squad, Parley, Maneuvering Jets, Scramble Frequency, Experimental Battlestation), `reactions_misc` (Manipulate Investments, Summit, Crisis, Puppets on a String, Extreme Duress, Master Plan, Lie in Wait, Reverse Engineer, Black Market Dealings).
- **Zmiany silnika:** nowy krok agendy `COUNTED` (pauza przed wynikiem, `POST /agenda/confirm`, tylko gdy ktoś ma jakąkolwiek kartę akcji = filtr jawny 43.4 pkt 5), nowe pola śladów (`tactical_moved`, `control_changes`, `turn_end_window`, `last_transaction`, `last_action_discard`, `bonus_turn`, `InvasionState.last_commit/parley_locked`, `ActiveCombat.destroyed_ships/sustained_ships/afb_assign`), nowe punkty `POINT_*` w `rules_hooks`, emisje `RETREAT_DECLARED`, `INVASION END`, `ACTION_CARD_DISCARDED`.
- **Front:** dok ręki ponad nakładkami walki/produkcji/inwazji/agendy (z-index 3050, strefa upuszczenia 3060), przełącznik ręki na dowolnego gracza (reakcje gra też gracz nieaktywny), pasek prywatnych podglądów (Insider Information, Extreme Duress), przycisk „Resolve the outcome" mówcy w kroku `COUNTED`. Nie testowane w przeglądarce.
- **Znane luki (⚠ w R53.md 53.5.a-e):** Courageous/Reflective Shielding/koniec rundy Emergency Repairs bez pełnej pauzy po przypisaniu strat; Scramble nie obejmuje AFB; Black Market Dealings nie ma pól w API/UI transakcji; Ghost Ship bez wariantu "zdejmij niszczyciel z planszy".
- Testy: nowe `test_reaction_cards`, `test_reactions_{agenda,tactical,combat,invasion,misc}`, `test_action_cards_{economy,board}`.

## 2026-11-11 (5) — Karty akcji 143/143: Hold-play (Sabotage), Hold-rewind (przycisk HOLD), czytelne formularze (RULES.md 53.6, 53.7)
- **Hold-play (`core/card_hold.py`):** zagrana karta akcji czeka ~10 s w `GameState.held_play` na Sabotage (tylko gdy ktoś inny ma kartę akcji i nie wszystkie Sabotage leżą na stosie odrzuconych = filtr jawny). Pas wszystkich uprawnionych albo timeout (czas serwera z routera) zwalnia efekt; reszta gry zablokowana middleware'em (poza `/action-card/*`, God-Mode, undo). `POST /action-card/held/pass|release`, `heldPlay` w web-data, Sabotage `sabo1..4` w `reactions_sabotage`.
- **Hold-rewind (`core/hold_rewind.py`, `routers/hold.py`):** przycisk HOLD cofa grę do wybranego kroku historii i od razu zagrywa kartę (jeden commit rozgałęziający historię). Zakazy: kości, dobranie/ujawnienie z talii, zmiana fazy/rundy, wcześniejszy rewind lub zagranie karty, więcej niż 8 kroków, trwający held_play. Karty: Public Disgrace, Coup d'Etat, Political Stability, Crash Landing (`reactions_stop`, z "hindsight" o cofniętym kroku).
- **Czytelność kart:** `card_labels.py` (planeta = nazwa + zasoby/wpływ + cechy + system, system, gracz, technologia), `hint` każdego wejścia, `summary` i podglądy skutku (`register_effect_preview`) w `GET /action-card/{id}/inputs`; modal pokazuje "dotyczy: …".
- **Front:** `HoldControls` (przycisk i panel kroków w doku), `HeldPlayBanner` (odliczanie, Pass, auto-otwarcie ręki do Sabotage), modal z `seq` i podsumowaniem. Nie testowane w przeglądarce.
- Wynik: wszystkie 143 karty akcji mają efekt w silniku.

## 2026-11-11 (6) — Etap sieciowy N0: `actor_id` we wszystkich endpointach (RULES.md 44.1a)
- **Mechanizm:** aktor w nagłówku `X-Actor-Id`, odczyt WYŁĄCZNIE w `api/actor.py::get_actor` (N1 podmieni go na token miejsca).
  Brak nagłówka = tryb zaufany (lokalne jedno okno, zachowanie bez zmian). Stare pola `actor_id` w treści łączy `merge_claimed`.
- **`core/actor.py`:** `check/subject/require/require_seated/merge_claimed` + listy uprawnionych (`turn_player`, `speaker`,
  `window_respondent`, `combat_sides`, `invasion_attacker/parties`, `exploring_player`, `strategy_owner`, `production_grantee`).
  `ActorError` (`PermissionError`) → HTTP 403; błędy reguł nadal 422.
- **Klasyfikacja 102 tras:** 75 akcji gracza/stołu (`actor: ActorId`), 27 operatora (`dependencies=[HostOnly]`: God-Mode,
  edycja planszy/graczy/talii, undo/redo/historia, nowa gra/mapa, ręczne okna/kroki, mówca, skip). Strażnik
  `tests/test_actor_guard.py` wymaga klasy dla każdej trasy i użycia parametru `actor`; zachowanie `tests/test_actor_rules.py`.
- **Front:** `api/actorIdentity.ts` — `?seat=<player_id>` (pamiętane w karcie) dokłada nagłówek do żądań `/bot…`. Dwie karty
  z różnymi `?seat=` = test „kilku graczy” (backend odrzuca cudze akcje 403). UI nadal pokazuje wszystko (widok per gracz = N2).
- Luki (N5): zgoda drugiej strony transakcji, równoległe decyzje, timeouty. Dalej: N1 (tokeny/role), N2 (projekcja per połączenie).

## 2026-11-11 (7) — Etap sieciowy N1 + N2: tokeny miejsc, role, projekcja per gracz (RULES.md 44.2a, 44.3)
- **Jak zagrać przez sieć:** `uv run python -m src.api --network` (drukuje link hosta) + `npm run dev -- --host`
  w `frontend/` (gracze łączą się z frontem hosta, np. `http://<IP-hosta>:5173`, w LAN/Tailscale). Host otwiera
  link hosta, tworzy grę, w panelu **Invites** (lewy dolny róg) kopiuje link każdego miejsca. Backend zostaje na 127.0.0.1.
- **N1:** `api/seats.py` (`SeatRegistry`, `Identity`), middleware tożsamości (401 bez tokenu), `get_actor` z tokenu,
  `require_host` z roli, router `network.py` (`/network/me`, `/network/seats`, rotacja, miejsce hosta).
- **N2:** `visibility.project_strict` (ręce, zakryte talie, ziarno RNG, cudze oferty, szkic karty strategii);
  `StateService.envelope()` rzutuje wg tożsamości żądania (każda odpowiedź akcji), WebSocket per klient
  (`broadcast_each`, token w `?token=`), web-data z perspektywy tokenu, `require_view`/`viewer_player` w GET-ach z `player_id`.
- **Front:** token z `?token=` (sessionStorage, usuwany z adresu) → `X-Seat-Token`; `useBackendPush` (WebSocket → odświeżenie
  zapytań, tylko w sieci); `NetworkPanel` + proxy Vite `ws: true`. Tryb lokalny bez zmian. Nie testowane w przeglądarce.
- Testy: `tests/test_network_game.py` (26: brak wycieków w 12 GET-ach, odpowiedziach akcji i WebSocket; role; rotacja; pełna gra).
- Dalej: N3 (zapis gry + tokenów, restart), N5 (UI „czekamy na X", blokada cudzych kontrolek, zgoda w transakcjach, timeouty).

## 2026-11-11 (8) — Relikty: zakładka Relics, akcje ACTION i efekty pasywne (RULES.md 59)
- **Stan/silnik:** `PlayerState.exhausted_relics` (+ `exhaust.*_relic`, odświeżanie w statusie), `relics.py` (transfer / detach /
  purge / `on_lost`), `relic_actions.py` (formularz + dispatch ACTION w `component_action`, `blocker`), `relic_cards.py`
  (zagrywalność + `play_relic`), hooki `hooks/relics_actions.py` i `hooks/relics_passive.py`. Nowe punkty: `economy.commodity_value`
  (Dynamis Core), `objectives.secret_limit` (Obsidian); `planet_stats.is_legendary` + relikt jako attachment (Nano-Forge);
  `SystemState.destroyed_planets` (Stellar Converter); `fracture.put_into_play`.
- **API:** `GET /relic/playable`, `GET /relic/{id}/inputs`, `POST /relic/play` (z `actor_id`). `web-data` zwraca realne `relics` i
  `exhaustedRelics` (wcześniej na sztywno puste), `commoditiesTotal` z `economy.commodity_value`.
- **Front:** zakładka **Relics** w `BottomHandDock` (ACTION przeciągane na strefę „Drop to use”, pasywne tylko do podglądu),
  `ActionCardPlayModal kind="relic"`, relikt z ACTION wybrany w „Play a component action” otwiera ten sam formularz.
- **Zrealizowane (11 z 23):** Codex, Dynamis Core, Book of Latvinia, Circlet of the Void, Nano-Forge, Stellar Converter, Silver Flame,
  Shard of the Throne, The Obsidian, Maw of Worlds, Quantumcore (bez synergii). Niezrobione: lista w `rules/R59.md` 59.6.
- Testy: `tests/test_relics.py` (20). `test_central_points`: `core/relics.py` właścicielem `purged`.

## 2026-11-11 (9) — N3 zapis partii w pliku + N5 część 1: interfejs gry sieciowej (RULES.md 44.4, 44.5)
- **Zapis:** `uv run python -m src.api [--network] [--save saves/partia.db] [--fresh]` — stan, historia Undo, mapa i tokeny
  miejsc zapisywane na bieżąco (SQLite, domyślnie `saves/game.db`); restart wznawia partię i linki zaproszeń. `EventStore`
  dostał tabelę `meta` (`get_meta/set_meta`), `HexGrid.to_placements/from_placements`, `AppContext.set_map/save_map`
  (też po dołożeniu gracza), `SeatRegistry` z `saved/persist`. Uszkodzony zapis → `*.broken-*`, `--fresh` → `*.old-*`.
  Zegar szachowy pauzowany po restarcie. Testy: `tests/test_save_resume.py`.
- **Interfejs:** `core/actor.awaiting` → `web-data.awaiting`; `NetworkPanel`: pasek „Your move / Waiting for X (co)",
  komunikat przy 403; `useDeskPlayer` w sieci = własne miejsce (ręka i kontrolki tury tylko swoje); skip phase tylko host.
- Nie testowane w przeglądarce. Dalej (N5 część 2): zgoda drugiej strony w transakcjach, timeouty/przejęcie przez bota
  (⚠ do decyzji użytkownika), wiele gier naraz.

## 2026-11-11 (10) — Lobby w menu, wczytywanie gry, plakietka „kim gram" (RULES.md 44.5a)
- **Jak grać przez ZeroTier:** `start.cmd` jak zwykle → menu **Host online game** → w kreatorze panel *Online lobby*
  pokazuje adres (np. `http://10.147.x.x:5173`) — znajomi wchodzą, wpisują imię, host wybiera „kto siedzi na którym
  miejscu" i startuje grę; goście same przechodzą do gry. Windows może zapytać o zgodę zapory dla Node (port 5173).
- **Backend:** `seats.py` (lobby: `join/kick/bind`, host = loopback, `member_id`), middleware (`_is_local`, 403 dla
  obcych przy zamkniętym lobby, 401 bez tokenu przy otwartym), router `network.py` (`/lobby*`, `/saves*`),
  `saves.py` (`SaveManager`), `AppContext.start_new_save/load_save`, `StateService.swap_store`; start bez flag =
  ostatnia partia z `saves/`, `--fresh` = nowy plik. Strażnik: `PublicJoin` dozwolony tylko dla `/lobby/join`.
- **Front:** `LobbyScreens.tsx` (`JoinScreen`, `LobbyHostPanel`, `LoadGameModal`), `useLobby.ts`, menu (Host online
  game, Load game), `WhoAmIBadge` w nagłówku, `storeSeatToken` (token z lobby bez przeładowania), Vite `host: true` + `xfwd`.
- Testy: lobby (dołączenie, przypisanie, wyrzucenie, tylko host, zamknięte lobby) w `test_network_game.py`,
  nowa gra = nowy plik + wczytanie w `test_save_resume.py`. Nie testowane w przeglądarce.

## 2026-11-11 (11) — Lobby uproszczone: „Play" = lobby (decyzja użytkownika)
- Menu: Play / Load game / Settings / Rules (bez „Host online game"). „Play" otwiera lobby: link do skopiowania, imię
  hosta, lista dołączających na żywo, „Add bot", „Start" → kreator od razu na kroku frakcji, miejsca przypisane
  automatycznie (host 1., dołączeni kolejno, boty na końcu). `LobbyScreen` zastąpił panel przypisań w kreatorze.

## 2026-11-11 (9) — Relikty: reszta (23/23), walka, kości, płatności (RULES.md 59)
- **Dopisane relikty:** JR-XS455-O, Scepter of Emelpar, Crown of Emphidia, Dominus Orb, Prophet's Tears, Neuraloop, Heart of Ixth,
  Crown of Thalnos, Lightrail Ordnance, Metali Void Armaments/Shielding, The Triad; Quantumcore ma już SYNERGY dla 4 kolorów.
- **Nowe punkty zaczepienia (`rules_hooks`):** `space_cannon.granted`, `combat.granted_sustain`, `combat.afb_granted`,
  `combat.reroll_plus_one`, `dice.adjust_result`, `command_tokens.strategy_from_reinforcements`, `technology.ignore_prerequisite`,
  `technology.synergy_all`, `movement.ignore_own_command_token`. `relic_planets.py` (relikt jak planeta), `objectives.replace_revealed`,
  `OBJECTIVE_REVEALED` emitowane.
- **API/UI:** `POST /tactical/battle/relic-reroll|relic-adjust` + `BattleResponse.relicTools` + `BattleRelicTools`; przełącznik Scepter
  w oknie secondary; skip `relic:<id>` w drzewie badań; Prophet's Tears w `autoSkips`.
- Testy: `tests/test_relics.py` (rozszerzone). Do dopisania później: purge kafla przez Silver Flame (decyzja użytkownika).

## God-Mode: relikty gracza

- `PlayerEditRequest.relics` + `board_edit._set_player_relics`: lista NADPISUJE relikty gracza, bez hooków „when you gain/lose".
  Dodany relikt znika z talii/stosu odrzuconych i od innych graczy; zdjęty wraca na spód talii (gdy zasiana).
- UI: edytor gracza (zakładka kart) ma sekcję „Relics" z wyborem pojedynczym oraz „Add all relics" / „Remove all relics".
- Test: `tests/test_api.py::test_god_mode_edytuje_relikty_gracza`.

## 2026-11-11 (12) — Lobby = graficzny kreator na żywo + tryb testowy hosta (RULES.md 44.5a)
- „Play" → kreator jako lobby: „Players & map" z panelem *Invite friends* (link do skopiowania), dołączający goście
  zajmują wolne miejsca (karty graczy pokazują kto); potem wszyscy razem: każdy sam wybiera frakcję, kolor i miejsce,
  cudze wybory widać na żywo; host prowadzi kroki i startuje grę, goście same wchodzą do planszy.
- Backend: `api/lobby_draft.py` (szkic: właściciele slotów, uprawnienia gościa, unikalność), `seats.py`
  (`reset_lobby/set_draft/patch_draft/draft_view/bind_from_draft`, `host_home`), `PUT|PATCH /lobby/draft`,
  `POST /lobby/seat`, `/lobby/open {reset}`; strażnik: `LobbyParty` tylko dla `/lobby/draft`.
- Front: `setupSync.ts` (synchronizacja `useSetupStore` ⇄ serwer, `useLobbyRole`, `canEditSlot`), blokady gościa
  w krokach (Players: podgląd; Faction/Seat & color: tylko własny slot), usunięty osobny ekran lobby.
- Tryb testowy: przełącznik w plakietce „kim gram" — host gra za wszystkich (operator) i wraca na swoje miejsce.
- Testy: szkic na żywo i nowe lobby w `test_network_game.py`, `setupSync.test.ts`. Nie testowane w przeglądarce.

## 2026-11-11 (13) — Start gry sieciowej: intro u gości + tajne cele równocześnie (RULES.md 45.3)
- Goście po starcie gry widzą tę samą planszę otwierającą (intro) co host, potem wchodzą do planszy
  (`useSetupSync(..., onGuestStarted)` → `SetupWizard`; tryb administratora pomija intro).
- Tajne cele: wybór równoczesny (`game_setup.pending_choosers`, `choose_secret` bez kolejki). web-data `setup` liczony
  z pełnego stanu: `pending`, `simultaneous`, `candidatesFor` (w sieci kandydaci tylko patrzącego). Wcześniej
  projekcja czyściła cudze ręce, więc każdy gość widział inny „wybierający".
- Okno setupu w sieci: każdy od razu swoje 2 karty, potem „Waiting for …"; Custodians/odkrycie klika tylko mówca,
  inni czekają i widzą odwracane karty; „Skip setup" tylko host. `awaiting`: `secret` / `setup`.
- Testy: `test_network_game.py::test_network_setup_secrets_are_simultaneous_and_private`, `test_game_setup.py`. Nie testowane w przeglądarce.

## 2026-11-11 (9) — Audyt: limity na stałe, eksploracja, relikty, technologie, czytelne błędy (RULES.md 42.x, 46 X12)
- **Limity capacity / fleet pool poza aktywacją:** `core/limits.enforce_limits` (jedno miejsce) woła `StateService.replace_state` po każdym zwykłym commicie; efekt dokładający statki/ładunek ponad limit otwiera okno `CAPACITY`/`FLEET_POOL` od razu. Pomija aktywny system akcji (własna bramka kroków), fazę statusu, trwające okno, eksplorację w toku i God-Mode/edycję planszy (wentyl). Testy: `tests/test_fleet_pool.py`.
- **Panele:** capacity i fleet pool to jeden komponent `RemovalWindowModal` (lista +/-, Auto/Reset, pasek statusu, stopka); `CapacityModal` zostawia tylko pasek ładowni, `FleetPoolModal` tylko opis puli i `ActiveTechs`. Powód odmowy serwera widać W oknie (wcześniej modal zasłaniał panel komunikatów, a błąd ginął).
- **Czytelne błędy:** `core/error_text` + middleware API: id graczy w `detail` → „Frakcja (kolor)", błędy walidacji Pydantic → jedno zdanie (`detail` zawsze string). Front: `api/apiError.ts` (`parseErrorDetail` obsługuje string/listę/brak treści; użyty w `useBoardEditor`, `fetchJson`, `throwResponseError`). Przepisane komunikaty eksploracji i reliktów (nazwy zamiast id, co zrobić dalej). ⚠ Zostało ~8 skopiowanych `parseDetail` w hookach domen (useInvasion, useExploration, useThundersEdge, useProduction, useMoveCard, useOffers, useTechnology, useClockActions) do przejścia na `parseErrorDetail`.
- **Eksploracja i hooki:** `PLANET_EXPLORED` jest teraz emitowane (`exploration.resolve`); skutki kart idą przez punkty centralne, więc ich hooki działają. Luki wypisane w R46 X12 (Enigmatic Device, Ion Storm, Mirage, Distant Suns, Fabrication).
- **Relikty:** wszystkie 23 aktywne mają efekt/hook; dodany brakujący test Maw of Worlds. Bez testu zostały gałęzie: `obsidian_gained`, `quantumcore_gained`, `book_gained`, pasywy Circlet (anomalie/asteroidy), Prophet's Tears (dobranie karty), Emphidia (eksploracja po akcji).
- **Technologie:** 36 ze 102 ma hook (wszystkie 33 ogólne + część frakcyjnych); 66 bez hooka to w większości technologie FRAKCYJNE (m.in. ulepszenia jednostek z danych, np. `ac2`, `sdn2`) — ich działanie zależy od `resolve_unit_variant`/danych, a zdolności tekstowe nie są kodowane. Bez testu po id: `dxa`, `bs`, `ws`, `pds2`, `cv2`. Raport `POKRYCIE_HOOKOW.md` odświeżony.

## 2026-11-11 (10) — Szybsze QA: pytest-xdist + pytest-testmon
- Dev-zależności: `pytest-xdist`, `pytest-testmon` (`pyproject.toml`, extra `dev`).
- `uv run pytest -q -n auto` — pełny zestaw równolegle: ~70 s → ~22 s (1862 passed, bez zmian w testach).
- `uv run pytest -q --testmon` — tylko testy, których kod się zmienił (bez zmian: <1 s). Działa też z `-n auto`.
  Baza `.testmondata` lokalna (gitignore); przed commitem i tak pełny zestaw.

## 2026-11-11 (10) — Karty frontier (Enigmatic Device, Ion Storm, Mirage) i wszystkie cele sprawdzane automatycznie (RULES.md 46 X13, 41.x)
- **Enigmatic Device:** `PlayerState.frontier_cards`; karta z eksploracji frontier wchodzi do ręki (zakładka Action cards, przeciąganie), ACTION = 6 zasobów + purge + badanie technologii (`core/frontier_cards.py`, `hooks/frontier_cards.py`, `/frontier-card/{playable,{id}/inputs,play}`, dispatch w `component_action`). Front: `BottomHandDock` miesza karty frontier z kartami akcji, `ActionCardPlayModal kind="frontier"`.
- **Ion Storm:** `SystemState.ion_storm` (+ `token_wormholes()` jako jedno źródło tokenów dla grafu), wybór strony, flip na końcu kroku ruchu / odwrotu (`core/ion_storm.py`, `HexGrid.link_kind`), token `ionalpha/ionbeta` w web-data. **Mirage:** planeta dołączana do systemu i zdobywana gotowa.
- **Cele:** 80/80 sprawdzanych automatycznie; 13 tajnych celów faz Action/Agenda zdobywanych zdarzeniami (`core/objective_events.py`: walka, zniszczenia, pas, utrata planety, agenda), `dhw` (purge 2 fragmentów) i `dp` (3 prawa) liczone w `objective_progress`; `MANUAL_OBJECTIVES` puste. Wcześniej tajne cele Action/Agenda nie miały żadnej ścieżki zdobycia.
- Testy: `tests/test_frontier_cards.py`, `tests/test_objective_events.py` (16), rozszerzone `test_objective_progress.py`.
- ⚠ Do przejrzenia: automatyczne zdobywanie tajnych celów zakłada, że gracz zawsze chce punktować (bez decyzji); limit „jeden tajny cel na walkę" i Ω-warianty celów (Fight with Precision Ω, TFtD Ω, MEoTW Ω) nie są rozróżniane.

## 2026-11-11 (11) — Testy E2E w przeglądarce (Playwright)
- `frontend/playwright.config.ts` + `npm run e2e` / `npm run e2e:ui`. Playwright stawia własny backend :8100
  (`scripts/e2e_server.py`: pusty stan, EventStore w pamięci, saves w katalogu tymczasowym, NIE zabija portów)
  i Vite :5273 z proxy na :8100 (`vite.config.ts`: zmienna `CUSTODIAN_BACKEND`, domyślnie :8000).
- Scenariusze (`frontend/e2e/*.e2e.ts`, rozszerzenie inne niż `*.test.ts`, żeby Vitest ich nie zbierał):
  menu startowe; gra solo z setupem przeklikanym ręcznie (tajny cel → Custodians → cele I etapu → faza strategii);
  „Skip setup"; gra sieciowa host + gość w dwóch przeglądarkach (dołączenie linkiem LAN, frakcje na żywo,
  wspólny start, równoczesne tajne cele). Każdy test pada przy błędzie JS/konsoli (`e2e/fixtures.ts`).
- Znalezisko: martwy socket STOMP (`useGameSocket`, `config.api.websocketUrl` = `ws://127.0.0.1:8000/ws-stomp`)
  po AsyncTI4 próbuje się łączyć i loguje błąd w konsoli; w fixture'ach zignorowany — do usunięcia.
- 4/4 zielone (~1,3 min).

## 2026-11-11 (11) — Zasada Ω dla celów, Mirage eksplorowana, Unveil Flagship (RULES.md 41.x, 46 X13)
- **Ω:** audyt katalogu: wersje zastępcze mają tylko technologie (X-89, Magen: `generic_pool` + `declare_superseded`) i fanowskie agendy Absol; cele nie mają kart Ω w assetach, więc rulingi Ω (FwP, MEoTW, TFtD) są jedynym zachowaniem celów zdarzeniowych.
- **Mirage:** po zdobyciu planeta trafia do kolejki eksploracji (cultural) w tym samym oknie. **Unveil Flagship:** `ActiveCombat.flagships_destroyed` (zniszczony w walce flagowiec przekreśla cel mimo odtworzenia); `GameState.destroyed_by` – własne straty (Thalnos) nie dają przeciwnikowi Destroy Their Greatest Ship.
- ⚠ Luka: zdolności legendarne planet (np. Mirage Flight Academy) – brak infrastruktury.


## 2026-11-11 (12) — README na GitHubie + przegląd aktualności dokumentacji
- **`README.md` (strona repo) przepisany:** był ze stanu „Faza 1” (SQLite/Numba, roadmapa M1–M6, assety poza repo, CDN).
  Teraz: co działa, status i pokrycie hooków, architektura (mermaid), instalacja, gra sieciowa, QA, mapa dokumentów.
- **Rozjazdy z kodem poprawione:** tabela statusu w `PROGRESS.md` (H4 143/143, H1b, karty strategii, sieć N0–N3),
  „Status” i plan kart strategii w `PLAN_PELNA_ROZGRYWKA.md` (było „16/143”, „nie rozpoczęty”, „sieć ⬜”),
  `PROJEKT_KARTY_STRATEGII.md` (zrealizowany), `docs/README.md` (QA frontu przez `tsc -p tsconfig.app.json`,
  brakujące moduły w mapie), `ARCHITEKTURA_KODU.md` §4 (32 routery), `ARCHITEKTURA_PO_MIGRACJI.md` (baner daty).
- **Raporty generowane odświeżone:** `OKNA_CZASOWE.md` (emitowane zdarzenia 41 → 45); `POKRYCIE_HOOKOW.md` bez zmian.
## 2026-11-11 (13) — Zdolności legendarnych planet + relikt za planetę w The Fracture (RULES.md 60)
- **Karty zdolności legendarnych** (`SOURCE_PLANET`, `ComponentCategory.PLANET`): wyczerpanie niezależne od karty planety
  (`PlayerState.exhausted_legendaries`, status krok 6, karta jedzie z planetą w `control.set_planet_control`).
  Hooki w `core/hooks/planets_legendary.py`: Mallice, Flight Academy x3, Hope's End, Primor, Emelpar, Mecatol (Galactic
  Council), Faunus, Garbozia (tylko kładzenie karty), Industrex, Ordinian x2, Styx, Tempesta, Thunder's Edge (przełom + dodatkowa
  akcja przez `turn_flow.begin_bonus_action`), Avernus (ACTION, `core/planet_abilities.py`), Custodia Vigilia (Mecatol ma
  SPACE CANNON/PRODUCTION: `space_cannon`, `production.producers`; 2 żetony przy VP z Imperial: zdarzenie `IMPERIAL_VICTORY_POINT`).
- **Fracture:** relikt za pierwszą kontrolę planety `frac*` działał tylko z jawnym `registry`; teraz `control` bierze rejestr
  z `rules_hooks.bound_registry` (lądowanie, produkcja, ręczne przejęcie).
- **UI:** `LegendaryUseModal` (ACTION w „Play a component action"), przełącznik „+1 do ruchu" także dla Tempesta,
  `web-data` `legendaryAbilities` i `extraMoveBoostActive`; `GET /planet-ability/{id}/form`.
- ⚠ Luki: granie kart akcji z Garbozii, zwykły STAR FORGE Muaat, karty legendarne nie są jeszcze widoczne w panelu gracza
  (oferty i lista akcji działają). Testy: `tests/test_legendary_planets.py` (30).
## 2026-11-11 (14) — Zoom mapy kółkiem, karty strategii na małych ekranach, „Report bug”
- **Zoom:** Ctrl + kółko (i pinch touchpada) zoomuje MAPĘ wokół kursora (`useWheelZoom`), `0` = dopasuj planszę,
  `_` jako zoom out (PL klawiatura); `+`/`=`/`-` bez zmian. Wpisy w oknie skrótów.
- **Wachlarz kart strategii:** karta `clamp(96px, min(10.4vw, 24vh), 230px)` zamiast `12.5vw` — wcześniej 8 kart = 100vw
  i karty 1/8 były obcięte nawet na 1920 px. Sprawdzone zrzutami 1920/1536/1366/1280/1024.
- **Nagłówek gry:** poniżej 1440 px przyciski HUD tylko z ikoną (`.hudLabel`), bo pasek się nie mieścił.
- **Report bug** (przycisk „Bug” w nagłówku): zrzut widoku w przeglądarce (`html-to-image`) + opis → `POST /bug-report`
  → `bug_reports/<data>_<gracz>/` na dysku HOSTA (`report.md`, `screenshot.png`, `client.json` z ostatnimi błędami
  konsoli, `state.json` = pełny `GameState`). Działa dla gości z sieci (token miejsca). `create_app(bug_reports_dir=…)`,
  `None` = 503. Testy: `tests/test_bug_report.py`, E2E `frontend/e2e/tools.e2e.ts`.
## 2026-11-11 (15) — Porządek w skrótach klawiszowych, skoki do pól graczy
- Gra renderuje tylko `PannableMapView`; boczne panele (`LeftSidebar` = cele/prawa, `RightSidebar` = „Seat dossier”)
  żyją wyłącznie w nieużywanym układzie „Panels” (`layouts/MapView.tsx`). Usunięte martwe skróty `h`/`l`/`r`
  i przełączniki „Collapse left/right panel” w Ustawieniach; z okna skrótów zniknęły nieistniejące `T`/`H`/`S`.
- Nowe skróty (`hooks/useKeyboardShortcuts.ts`, opis w `KeyboardShortcutsModal`): `1–8` = pole gracza pod planszą
  (ta sama cyfra = powrót), `Shift+1–8` = gracz na planszy, `[`/`]` = poprzedni/następny, `g` = cele i punkty,
  `b`/`Home` = plansza, `?` = lista skrótów. Skok przewija i podświetla cel stylem trafienia wyszukiwarki.
  Skróty milkną przy pisaniu i pod otwartym oknem modalnym. E2E: `frontend/e2e/tools.e2e.ts`.
## 2026-11-11 (16) — Usunięty układ „Panels”, naprawiony skok do planety
- Usunięta opcja „Map view: Pannable / Panels” (Ustawienia) i cały martwy układ „Panels”: `layouts/MapView.tsx`,
  `LeftSidebar`, `RightSidebar`, `PlayerCardDisplay`, `PanelToggleButton`, `mapPlayerPanels/`, `MapViewSelectionModal/`,
  `chrome/DragHandle`, `useSidebarDragHandle`, `useMapScrollPosition`, `utils/mapViewPreference.ts` oraz pola
  `leftPanelCollapsed`/`rightPanelCollapsed`/`mapViewPreference` w `appStore`.
- Klik w kartę planety w polu gracza znów przewija mapę do tej planety i ją podświetla: `useScrollToPlanet` był podpięty
  tylko w martwym `MapView`; przepisany na znacznik wyszukiwarki (`jumpToSearchHit` w `search/searchHits.ts`,
  wspólny ze skrótami 1–8) i podpięty w `PannableMapView`.

## Feed Activity: komplet skutków

Panel historii pokazywał tylko VP/TG/techy/planety/karty jawne. core/activity.py liczy teraz też: commodities, żetony dowodzenia (pule), zmianę liczby kart w rękach (tylko liczby), jednostki (produkcja/straty), żetony w systemach, relikty, karty frontier, stany liderów, breakthrough, karty strategii, prawa (wejście/uchylenie), karty przyczepione do planet, zdobyte cele publiczne, efekty trwałe, mówcę, Custodians i zwycięzcę. Opisy: describeActivity.tsx. Reguła na przyszłość: ARCHITEKTURA_KODU.md §5 (lista kontrolna).

## Płatność za cele „Spend…" wybiera gracz (cele publiczne, tajne, Imperial)

- `core/objective_payment.py`: `ObjectivePayment` (planety, TG, pule żetonów, karty akcji, fragmenty), `auto_payment` (domyślna/podpowiedź), walidacja jawnej płatności, `spend_spec` (opis kosztu dla UI). `POST /status/score` i krok Imperial przyjmują opcjonalne `payment`.
- Web-data: `publicOptions/secretOptions[].spend` (kind, goal, dostępne planety/pule/karty/fragmenty, `suggested`).
- Frontend: `ObjectiveSpendForm` rozwija się pod wierszem celu („Pay & score"), startuje od podpowiedzi silnika.
- Testy: `tests/test_objective_progress.py` (jawna płatność, za niska płatność, pule żetonów, fragmenty).

## Relikt z fragmentów + scena odsłonięcia reliktu (RULES.md 59.7–59.8)

- Nowa akcja komponentu: purge 3 fragmentów -> relikt (`core/relic_forge.py`). Typ, liczba i nagroda z tekstu kart fragmentów (assety); Unknown = dżoker, min. 1 nie-Unknown; pusta talia = purge bez reliktu. API: `GET /relic/forge/options`, `POST /relic/forge`. UI: przycisk „Forge relic” w zakładce Relics doku ręki (`domains/relics/RelicForgePanel`).
- Każde dobranie z talii reliktów zapisuje jawne `GameState.relic_reveal` (+`seq`, jak `table_roll`; źródło `fragments`/`fracture`/`explore`). Web-data: `gameState.relicReveal`.
- `domains/relics/RelicRevealWatcher` gra scenę u wszystkich: fragmenty krążą i zlewają się w błysku w kartę; przy planecie The Fracture pęknięcie w przestrzeni wypuszcza kartę; karta obraca się awersem + nazwa i tekst reliktu. Awers = placeholder (rewers + nazwa) — grafikę kart podpiąć w `relicFaceImage` (`domains/relics/relicReveal.ts`).
- Testy: `tests/test_relic_forge.py`, `test_thunders_edge.py` (źródło Fracture), `relicReveal.test.ts`.

## Przegląd UI: spójna oprawa TI + poprawki układu

- Nowa warstwa `frontend/src/styles/tiChrome.css` — tokeny oprawy wzięte ze sceny wyboru frakcji (bursztyn/złoto, gradient CTA,
  krój tytułów Handel Gothic, ścięte rogi `--ti-cut`). Bursztyn = rama i główne wezwanie, niebieski DS dalej = zaznaczenie/fokus.
  Klatek animacji tam nie ma (Vite lokalizuje `@keyframes` w modułach) — każdy moduł ma własne.
- Rama każdego okna (`ds` Modal/Drawer → wszystkie `AppModal`): płyta ze ściętymi rogami, obrys bursztynowy wygasający w prawo,
  tytuł krojem TI, linia pod nagłówkiem rysowana przy otwarciu; przyciski DS z krótkim „wciśnięciem” i ciepłym hoverem.
- Pełnoekranowe okna (agenda, produkcja, technologie, eksploracja, walka, inwazja): tytuły krojem TI, panele jako płyty ze ściętymi rogami.
  Baner fazy strategii: oprawa w bursztynie, „Next phase” jako złote CTA (przycisk zwijania został niebieski — prośba użytkownika).
  Płyty HUD (panel stanu, strefa tury, dok ręki): ciepła górna krawędź. Nagłówek przeglądarki zasad w tym samym stylu.
- Błędy układu: status tury gry sieciowej („Your move / Waiting for…”) nachodził na „You play” — teraz `TurnStatusChip` w nagłówku
  (pulsująca kropka przy moim ruchu). Dok ręki przy 1280 px zasłaniał „Next phase/End turn” — szerokość zostawia miejsce na panel tury,
  wąski dok chowa podpisy segmentów. Okno setupu przy 720 px ucinało tytuł (centrowanie grid) — flex + `margin: auto`, karty skalowane też `vh`.
- Scena wyboru frakcji nietknięta (zamknięta decyzją użytkownika).

## Walka: profesjonalniejsze pole bitwy i efekty

- Szyk floty skaluje się do panelu (`useFormationFit` w `BattleFleet.tsx`): duża flota (war sun, dreadnoughty, eskorta)
  nie wychodzi już poza krawędzie; proporcje „wagi” okrętów zostają. Szeregi bez zawijania.
- Przypisywanie trafień: celownik z czterech narożników zamiast nachodzących na siebie prostokątów
  (hover zaciska, Sustain = niebieski, zniszczenie = czerwony z pulsem namiaru).
- Zniszczenie okrętu: błysk rdzenia → kula ognia → fala uderzeniowa; ciężkie okręty (ws/fs/dn) mają łańcuch
  wtórnych detonacji i rozbłysk oświetlający panel floty. Podpisy jednostek na płytce, paski życia na listwie
  (uszkodzony = bursztynowy segment). Panele flot jako płyty TI.
- Nowa animacja: plansza „ROUND N” przecinająca pole przy przejściu do kolejnej rundy (od rundy 2).
- Okna pełnoekranowe (walka, inwazja, agenda, produkcja, technologie, eksploracja) mają `data-fullscreen-overlay`:
  dok ręki zwija się wtedy do paska (rozwinięcie chwilowe, bez nadpisania zapamiętanego wyboru), a okno rezerwuje
  pod nim miejsce — dok nie zasłania tabel jednostek. Inwazja: karta planety i dok orbity jako płyty TI.
- Animacje bombardowania / lądowania / walki naziemnej (ustalone wcześniej z użytkownikiem) bez zmian.

## 2026-11-12 — Frakcje Fala 0: liderzy (F1), promissory notes (F2), akcje komponentów frakcji (F3a) — RULES.md 61

- **F1 liderzy** (`core/leaders.py`): stany `locked/unlocked/exhausted/purged`, odblokowanie z warunku „Unlock” z danych
  (`register_unlock` po id, `register_unlock_condition` po tekście — wszyscy bohaterowie „3 scored objectives” działają od razu),
  sprawdzanie po każdym commicie w `StateService` (nie w trakcie ofert), koszt użycia z tekstu (wyczerpanie agenta, purge
  bohatera; wyjątki ⚠️ 61.1). Lider bez zakodowanego warunku: przycisk „Unlock” (`POST /leader/claim-unlock`, MANUAL).
- **F3a** (`core/faction_components.py`): `ACTION:` liderów / zdolności frakcji / przełomu przez akcję komponentu
  (`leader:` / `ability:` / `breakthrough:`), efekt `register_effect("leaders|abilities|breakthroughs:<id>")`, koszt płaci
  warstwa wspólna. API `/faction-component/*`. UI: `FactionComponentUseModal` z listy „Play a component action” (+ przełom)
  i z menu lidera w panelu gracza („Leader ability…”); bohater po użyciu „purged”.
- **F2 promissory notes** (`core/promissory_play.py`, `core/hooks/promissory_generic.py`): kopia z kolorem → szablon +
  właściciel, zakaz własnej notki, reakcje w modelu okien kart akcji, zwrot/strefa/purge po efekcie, „play immediately” przy
  otrzymaniu. Komplet 5 notek ogólnych: Ceasefire (zakaz ruchu w `movement.can_move`), Political Secret (głos + karty akcji +
  zdolności), Support for the Throne (±1 VP, zwrot), Trade Agreement (ślad `last_replenished`), Alliance (commander właściciela
  jako źródło hooków posiadacza). UI: zakładka Notes w doku ręki — przeciąganie legalnej notki (`ActionCardPlayModal kind="note"`).
- Feed Activity: `component.use`, `promissory.play` (+ fakt `leader` „purged”). Testy: `test_leaders.py`, `test_promissory_play.py`.
- **F3b**: `UnitDef.ability` + źródło hooków `SOURCE_UNIT` (wariant jednostki gracza), `core/faction_units.py`, pakiet
  `core/hooks/factions/` (Arborec przeniesiony), test kompletności `tests/factions/completeness.py`, kolumna „Jedn.” w raporcie pokrycia.
- Dalej: B1 (Sardakk N'orr + Barony of Letnev, komplet z liderami, przełomem, notką, flagowcem i mechem).

## 2026-11-12 (2) — B1a: Sardakk N'orr — komplet (RULES.md 62.0–62.1)

- Wszystkie 11 komponentów frakcji (`core/hooks/factions/sardakk.py`, test kompletności = 0 braków, 19 testów):
  Unrelenting, flagowiec C'morran N'orr, mech Valkyrie Exoskeleton, Valkyrie Particle Weave, Exotrireme II,
  Tekklar Legion, agent T'ro (decyzja aktywnego gracza), commander G'hom Sek'kus (+ warunek odblokowania),
  bohater Tekklar Conditioning, przełom N'orr Supremacy.
- Nowe fundamenty wspólne: tryb „window” komponentów frakcji (`faction_components.window_use`, RULES.md 62.0 —
  „During X: you may…” bez zużycia akcji), punkt `combat.extra_hits`, `battle.add_combat_hits` (trafienia po
  rzutach + powrót do kolejki przypisywania), PERMIT `invasion.skip_bombardment`, `invasion.commit_from_planets`,
  emisja `COMPONENT_EXHAUSTED` w `faction_components.pay_cost`, odporność na Direct Hit z tekstu jednostki.
- UI: `FactionComponentUseModal` obsługuje tryb „window” (wejście: menu lidera „Leader ability…”).
## 2026-11-12 (3) — Ruch z trasą i pickup po drodze (RULES.md 32.1/32.3 T3)
- Silnik (`core/movement.py`): BFS zwraca ścieżkę (`shortest_legal_path`), `route_through` (waypointy), `route_error`
  (walidacja trasy gracza), `legal_routes` (alternatywy), `route_cargo` (ładunek w systemach trasy). `can_move`/`move_fleet`
  przyjmują `route`; `CargoPickup.from_position` pozwala zabrać myśliwce/siły naziemne z systemu NA trasie (T4 per system).
- `core/movement_route.py` + `GET /tactical/move-route` (trasa, alternatywy, waypointy, statki z oceną zasięgu/boostu, ładunek);
  `POST /tactical/move` dostaje opcjonalne `route` i `cargo[].fromPosition`. Testy: `tests/test_movement_route.py`.
- UI (krok MOVEMENT): klik w świecący system na mapie otwiera przeciągalny box (`domains/movement/MoveRouteBox`): statki i
  ładunek z systemów na trasie (LPM +1, PPM −1, Shift = wszystkie), pasek capacity, alternatywy tras. Trasa rysowana na mapie
  (`MoveRouteLayer`: linia, strzałki, przerywane alternatywy, ładunek po drodze jako klikalne znaczniki). Klik w kolejny
  system przerzuca trasę przez niego (waypoint). Ctrl+zaznaczenie: PPM zdejmuje 1 sztukę (`ctrlUnpickUnit`).
- Dodane potem: Ctrl-grupa upuszczona na aktywny system otwiera box ruchu z gotowym wyborem (trasę można zmienić przed Move); gravity rift (+1 do ruchu, rzut d10 1-3 usuwa statek i załadowany ładunek, RULES.md 32.3 T6, ⚠️ ZAŁOŻENIE o ładunku); pickup sił naziemnych z planet systemu docelowego jako koniec trasy. Poza zakresem: Dimensional Tear jako szczelina, odwrót ze szczeliny.

## 2026-11-12 (3) — B1b: Barony of Letnev — komplet (RULES.md 62.2)

- Wszystkie 12 komponentów (`core/hooks/factions/letnev.py`, kompletność = 0 braków, 18 testów): Armada, Munitions
  Reserves (płatność na starcie rundy + przerzut po rzucie), Non-Euclidean Shielding, L4 Disruptors, flagowiec Arc
  Secundus (tarcze + naprawa), mech Dunlain Reaper (DEPLOY z płatnością), War Funding, agent Viscount Unlenn, commander
  Rear Admiral Farran (+ warunek), bohater Darktalon Treilla, przełom Gravleash Maneuvers (część bojowa).
- Fundamenty: pauza walki na decyzje z początku rundy (`resume="round_start"`), `battle.reroll_combat_dice` (centralny
  przerzut), punkty `combat.bonus_dice` / `combat.single_unit_bonus` / `combat.sustain_cancels` (`plan_losses(cancels=)`
  w walce, bombardowaniu i SC Defense), `fleet_pool.capacity` / `fleet_pool.unlimited`, `invasion.strips_planetary_shield`,
  `space_cannon.defense_immune`, `UNIT_SUSTAIN_DAMAGE` także w bombardowaniu i SC Defense, okno „po rzutach” w walce
  kosmicznej, `promissory_play.any_subject`.
- Druga klauzula Gravleash (wyrównanie ruchu) dokończona po przebudowie tras: PERMIT `movement.match_highest`.
- Premia Gravity Drive / Ionian Fuel Refinery propaguje się przy Gravleash (decyzja użytkownika).
- ⚠️ Otwarte (na później, decyzja użytkownika): „limited by laws” u Darktalon — po efektach agend.

## Letnev z testu użytkownika + okna decyzji (2026-11-12)

- Naprawa: `/tactical/move-route` padał (500) po niedokończonej przebudowie tras — router/schemat podawały stare
  `boosted`/`gravity_drive`. Teraz `alone`, `withShips` (Gravleash: dolatuje razem z innym typem), `bonusOptions`,
  `bonusMax`, `bonuses`; front (`routeTypes.shipMax/draftProblems`) pokazuje „with Cruiser (Gravleash)” i blokuje ruch
  statku bez wymaganego towarzysza.
- Munitions Reserves: przerzut prosto w oknie walki — `faction_components.combat_dice_uses` → `BattleResponse.abilityTools`
  → `BattleRelicTools` (zaznacz kości / „Select misses” / Reroll). Wcześniej tylko z menu akcji komponentu.
- Oferty: nazwa + tekst + rodzaj (`kind`: Agent, Faction ability, Breakthrough, Unit ability…) dla wszystkich kategorii
  komponentów (wcześniej tylko technologie); przycisk nazwany akcją z etykiety hooka.
- Wspólne pola decyzji `domains/offers/DecisionFields` (oferty, karty akcji, zdolności, technologie, legendarne planety):
  kafelki zamiast list rozwijanych (lista z wyszukiwaniem dopiero > 18 opcji), stepper zamiast pola liczbowego,
  `meta` opcji = sprite jednostki w kolorze gracza / planeta z wartością / kość z trafieniem. Płatność planety+TG
  (`offer_inputs.payment_planets` / `as_payment`) = jeden widżet z paskiem „Paid X / Y” (mech Dunlain Reaper, Pirate
  Fleet, Impersonation, Plagiarize, Reveal Prototype, Enigmatic Device).
- Agent Viscount Unlenn: opcje z nazwą frakcji zamiast `(p1)`, własne statki pierwsze. `validate_params`: pominięty
  opcjonalny multi (min 0) = pusta lista.

## Powiadomienia „kto co zrobił” (ActivityToasts)

- `ActivityPanel/ActivityToasts.tsx`: każdy nowy wpis feedu Activity od INNEGO gracza (tech, karta akcji, lider, ruch,
  walka, pas…) wyskakuje w prawym górnym rogu na 8 s (najechanie wstrzymuje, X zamyka, max 3 naraz). Treść = ten sam
  `describeActivity` co panel + tekst użytej karty/technologii (`activitySubject.ts` → `Named.hintFor`), czyli to, co
  w panelu jest w podpowiedzi. Pomijane: God-Mode, zdarzenia bez sprawcy, `turn.next/turn.end`, wpisy cofnięte Undo,
  wpisy sprzed otwarcia strony. Tryb lokalny (bez „mnie”): tylko akcje botów. Backend bez zmian.
- `useActivityContext.ts` wydzielony z panelu; poprawka: na trasie `/game` brał `mapid=""` (404, nierozwiązane nazwy
  systemów) — teraz `DEFAULT_GAME_ID`. Testy: `activityToasts.test.ts`.
- Poprawki po drugim teście: (1) Planetary Shield — `web_data` wysyłało zawsze `planetaryShield: False` (ikona tarczy
  na mapie nigdy się nie pokazywała); teraz `invasion.planet_shield(state, registry, position, planet)` = (jest, działa),
  mapa pokazuje działającą tarczę, a jej utratę (Arc Secundus) animuje `PlanetaryShieldOverlayLayer` (`shieldBreak`).
  W oknie inwazji `has_shield` = „stoi jednostka z tarczą”, więc kopuła zapada się z animacją też przy Arc Secundus
  i Disable (wcześniej znikała bez śladu). (2) Płatność: `buildActionCardParams` nie przepuszcza odpowiedzi, dopóki
  planety + TG nie pokryją `payment.cost` (przycisk był aktywny przy „Paid 0 / 2” i silnik odrzucał).
- Ikony jednostek w kafelkach decyzji (Viscount Unlenn i inne): duże statki wylewały się z pudełka 34×34 (ograniczany
  był tylko wrapper `Unit`, nie sam sprite). Teraz `--unit-fit` (`shared/ui/Unit/unitSprites.css`, `--unit-sprite-ratio`
  z `SpriteUnitImage`) mieści sprite z proporcjami; `DecisionFields.module.css` ustawia `--unit-fit: 34px`.
- Steering/Workflow: QA dobierane do zakresu zmiany (build/E2E tylko gdy potrzebne).
- Gravleash + Gravity Drive: `move_fleet` zużywał premię na pierwszym typie statku, więc reszta floty dostawała
  „Range too short”, choć podgląd trasy pokazywał dolot. Premia zużyta w TYM ruchu działa teraz na kolejne typy
  (niemyśliwskie) przy Gravleash; test `test_gravleash_z_gravity_drive_cala_flota_leci_3`.
- Pole bitwy, war sun (też Prototype War Sun Muaat — ta sama grafika `ws`): prawa flota nie odwraca go już o 180°
  (stał do góry nogami); rozmiar 180 → 136 (grafika 56×65 px była rozciągana ~2,2× = pikseloza, teraz ~1,6×).
- ActivityToasts: powiadomienie zwinięte = jedna linia „kto co zrobił” (max 2 wiersze); klik/strzałka rozwija skutki
  + nazwę, typ i tekst karty/technologii i wstrzymuje zamknięcie (zamyka X albo zwinięcie). Test `ActivityToastCard.test.tsx`.
- Efekty trwałe: panel „Active effects” przy planszy (`domains/effects/ActiveEffectsPanel`, lewa strona mapy, zwijany,
  klik = tekst karty) z `gameState.activeEffects` (`core/component_text.active_effects_view`: nazwa, rodzaj, tekst,
  „do kiedy”, czego dotyczy). `describe_component` przeniesione z `offers.py` do `core/component_text.py` (wspólne).
  Historia/powiadomienia: „used Darktalon Treilla (active for this game round)” zamiast „effect active:
  Leaders:letnevhero” (`resolveEffectName`, `describeEffectScope`).
- Darktalon Treilla: `FleetReport.unlimited` zamiast sztucznej puli 10**6 (`FleetPoolWarning` rysował milion kratek —
  zacinanie strony). Pula zostaje prawdziwą liczbą żetonów; UI: „no limit this round”, kratki maks. 24.
- Fighter II w ruchu: (1) `move_fleet` liczył dostępność statków i ładunku osobno — 6 myśliwców jako statki + 4 jako
  ładunek z tego samego systemu dawało 10 w celu; teraz ładunek ze startu odejmuje to, co leci samo. (2) Okno trasy
  pokazuje jednostkę w JEDNYM miejscu: dolatujące same = statki, niedolatujące = ładunek; zaznaczenie grupy z mapy
  zamienia „statek” na ładunek, gdy sam nie doleci (`routeTypes.prunePicks`).

## 2026-11-12 (4) — B2 Jol-Nar + B3 Sol — komplet (RULES.md 62.3–62.4)

- **Jol-Nar** (`core/hooks/factions/jolnar.py`, 12 komponentów, kompletność = 0 braków, 23 testy): Fragile, Shield
  Paling (znosi Fragile piechocie), J.N.S. Hylarim (+2 trafienia za naturalne 9–10), Analytical (darmowe ignorowanie
  1 prerekwizytu), Brilliant (secondary Technology jako primary — dwa etapy w oknie badania), E-Res Siphons, Spatial
  Conduit Cylinder (dodatkowe sąsiedztwo w ruchu), Research Agreement, Doctor Sucaban (badający zdejmuje piechotę =
  zniżka), Agnlan Oln (+ warunek 8 technologii; przerzut WYBRANYCH kości SCO/SCD/bombardowania), Genetic Memory
  (zamiana technologii tego samego koloru), Specialist Compounds (planeta ze specjalnością płaci za badanie).
- **Sol** (`core/hooks/factions/sol.py`, 12 komponentów, 0 braków, 18 testów): Orbital Drop (ACTION za żeton
  strategii) + mech ZS Thunderbolt M2 (DEPLOY za 3 zasoby), Versatile, Spec Ops II (mechanizm Infantry II, próg 5 z
  tekstu karty), Advanced Carrier II (dane), Genesis, Evelyn DeLouis, Claire Gibson (+ warunek 12 zasobów), Jace X,
  Military Support, Bellum Gloriosum (ładunek do capacity produkowanych statków poza limitem PRODUCTION).
- Nowe fundamenty: punkty `combat.natural_extra_hits` (`battle.natural_extra_hits` — rzut i przerzuty),
  `technology.free_prerequisite_ignores`, `strategy.secondary_as_primary`, `movement.extra_adjacent`
  (`_neighbors_for_move`), `production.free_cargo` (limit, producenci, `production_used`; front: `slotsUsed`),
  `technology.specialty_pays`; ślad `GameState.last_research` + okno „po badaniu”; zniżka badania
  `technology.RESEARCH_DISCOUNT`; `space_cannon.reroll_entries(picks=, source=)`; fakt feedu `tech_lost`.
- `leaders.claim_unlock`: najpierw „czy to twój lider”, potem „odblokowuje się sam”.
- ⚠️ Założenia do potwierdzenia (R62.3/62.4): Analytical i Brilliant działają automatycznie (zawsze korzystne);
  SCC tylko w ruchu Jol-Nar; Sucaban tylko przy badaniu z karty Technology; Agnlan Oln raz na rodzaj rzutu, bez AFB;
  Military Support nie działa w pierwszej turze fazy akcji (brak pauzy początku tury); Bellum Gloriosum liczy jedno
  zamówienie.
- Nowe pole stanu (`last_research`) i pola widoku produkcji (`freeCargo`, `capacity`) wymagają restartu backendu.

## 2026-11-12 (5) — Decyzje do Jol-Nar + B3 Arborec — komplet (RULES.md 62.3, 62.5)

- Decyzje użytkownika: Analytical i Brilliant działają same, a gracz dostaje informację — `core/ability_notes`
  → fakt feedu `ability_used` (opis w `describeActivity`), powiadomienie także dla właściciela (`shouldToast`).
- Płatne badania przez JEDNĄ funkcję `technology.pay_research` (karta Technology, Reveal Prototype, Enigmatic Device):
  zniżka + ślad `GameState.last_research_payment`. Doctor Sucaban przed zapłatą = zniżka, po zapłacie (karty
  rozstrzygane jednym ruchem) = zwrot planet/TG (`economy.refund_trade_goods`, bez zdarzenia „zdobycia”). Ślad
  posłuży też commanderowi Deepwrought.
- Agnlan Oln obejmuje AFB: `battle.resolve_afb` rozdzielony na rzut i `_apply_afb`; gdy po rzucie powstały oferty,
  walka czeka w TRIGGERS (`resume=afb_apply`). Oferta przerzutu wybranych kości AFB.
- **Arborec** (`core/hooks/factions/arborec.py`, 11 komponentów, 0 braków, 20 testów): Mitosis (+ mech Letani
  Behemoth jako opcja), Bioplasmosis (ruch jednoczesny), Letani Warrior II (mechanizm Infantry II), Letani Ospha
  (decyzja właściciela statku), Dirzuga Rophal (+ warunek 12 sił), Duha Menaimon (grant 5 jednostek), Ultrasonic
  Emitter (grant z kolejką systemów `ProductionGrant.queue`), Stymie, Psychospore.
- Domknięte (decyzje użytkownika): Focused Research (TG = zasoby) idzie przez `pay_research(trade_goods_only=True)`
  i Sucabana; cudza produkcja z grantu (Dirzuga Rophal) wstrzymuje ruch i zmianę kroku aktywnego gracza
  (`production.foreign_grant_reason`); Stymie Ω — żeton z arkusza przy pustej rezerwie (decyzja ruszającego);
  Letani Ospha — zamiennik z planszy (system bez żetonu właściciela), gdy rezerwa pusta.
- Nowe pola stanu (`last_research_payment`, `ability_notes`, `ProductionGrant.queue`) — restart backendu.

## 2026-11-12 (6) — Zdolności frakcji wyskakują same + scenariusze przez API (RULES.md 62.0)

- Zgłoszenie użytkownika: agent i bohater Sardakk „nie działały”. Przyczyny: (1) zdolności „During X: you may…”
  (62.0: bohater Sardakk, G'hom Sek'kus, Munitions Reserves, Doctor Sucaban, Agnlan Oln…) były dostępne tylko z menu
  lidera; (2) „End turn” w trakcie akcji taktycznej oddawał turę, mimo że koniec akcji właśnie utworzył oferty (T'ro).
- Naprawa: karta „Available now” (`domains/offers/AbilityPrompts`) pokazuje SAMA każdą zdolność, której można teraz
  użyć (`GET /faction-component/available-now`); `turn_flow.end_turn` zostawia turę, gdy zamknięcie akcji dodało oferty.
- Siatka bezpieczeństwa: `tests/factions/test_flows_api.py` — scenariusze przez prawdziwe API (nowa gra, setup, tura),
  sprawdzające to, co widzi gracz (oferta / „Available now”), a nie efekt na ręcznie zbudowanym stanie.

## 2026-11-12 (7) — Inwazja: planety z kafelków i nowe bombardowanie (front)

- Glob w oknie inwazji pokazuje grafikę planety wyciętą z jej kafelka (`entities/lookup/planetTileArt.ts`:
  środek z `centerPosition`/`positionInTile`, promień `planetRadius` lub 50 px; kadr lekko przepełniony, by
  etykiety z kafelka zostały poza kołem). Bez kafelka/pozycji zostaje dawny gradient. `PlanetCard` korzysta z tej samej funkcji.
- Bombardowanie od nowa (`InvasionFx`): ładowanie działa → plazmowy pocisk z warkoczem (przyspiesza jak przy spadaniu)
  → trafienie na powierzchni (warstwa przycięta do globu: rozświetlenie, kula ognia, płaska fala, stygnący żar) + błysk,
  odłamki i dym wzdłuż normalnej powierzchni; pudło gaśnie w atmosferze chłodnym rozbłyskiem. War sun: kula ładowania
  i gruba lanca. Wszystko wygasa do zera (bez pozostałości). SCD bez zmian.
- Rozmiar planety: glob ma promień zależny od wielkości planety na kafelku (`globeRadiusOf`, skala pierwiastkowa:
  zwykła ~76 px, Primor/legendarne ~100, Mecatol ~107). Promienie dużych planet zmierzone z grafik kafelków skryptem
  `scripts/measure_planet_radius.py` (krawędź tarczy, tylko aktywne źródła) => `entities/data/planetArtRadius.json`;
  reszta = standard 60 px. Wcześniej Primor (r~100) był kadrowany jak zwykła planeta (50) i ucięty.

## 2026-11-12 (7) — Scenariusze frakcji przez prawdziwe API + strażnik pokrycia

- `tests/factions/flow_harness.py`: nowa gra przez `/game/new` + setup, sytuacja przez God-Mode patch (także
  `rng_seed` - nowe pole `GodModePatch`, powtarzalne kości), przebieg przez endpointy gry: aktywacja, ruch, kroki
  taktyczne, walka z autopilotem strat, inwazja, karta Technology, pas/koniec tury, kroki fazy statusu.
- 33 scenariusze dla 5 frakcji (`test_flows_<frakcja>.py`), `@covers` na każdym interaktywnym komponencie.
  Strażnik `test_flow_coverage.py` wylicza interaktywne komponenty każdej frakcji z modułem hooków (oferta, okno
  62.0, ACTION, notka) i wymaga scenariusza; pilnuje też literówek w `@covers`. DoD bloku frakcji rozszerzone
  (`PLAN_FRAKCJE.md` §2, steering).
- Błąd znaleziony scenariuszem: gdy na starcie walki ktoś ma decyzję (krok TRIGGERS), okna „At the start of
  combat / combat round” nie były zgłaszane — Tekklar Legion i karty startu walki były martwe do czasu odpowiedzi
  na ofertę. Naprawa w `reactions_combat.combat_windows`.


## 2026-11-12 (7) — Audyt okien czasowych: komponenty wyskakują w swojej chwili (RULES.md 54.8)

- Narzędzie `src/audit/timing_reach.py` (+ sekcja §2a w `OKNA_CZASOWE.md`, strażnik `tests/test_timing_reach.py`):
  dla każdego komponentu z oknem ustala kanał do gracza (auto / oferta / ręka / Available now / przycisk / modyfikator
  / reguła) i wykrywa hooki na nieemitowanych momentach, karty z ręki bez dostawcy okna i efekty bez kanału. Wynik
  okablowania: 0 luk. Zostaje 163 komponentów z oknem bez efektu — prawie wyłącznie frakcje jeszcze nieobrobione
  (w bieżącej partii: Creuss) i 4 wydarzenia galaktyczne TE.
- Naprawy: (1) pierwsza tura fazy akcji nie miała „początku tury” (`TURN/START` i okno kart z ręki tylko po
  `end_turn`) — `next_phase` emituje je teraz dla pierwszego gracza (`TurnEndWindow.ended_player=None`);
  (2) `Next phase` przechodził nad otwartym oknem / ofertami (np. „at the end of your turn” ostatniej tury) —
  brama `turn_flow.open_decisions_reason`; (3) zdolności obowiązkowe działały po cichu — `triggers._run_visible`
  dopisuje `ability_notes` (feed + powiadomienie), gdy hook komponentu zmienił stan; (4) zagrywalność kart z ręki
  front pobierał tylko przy otwartym doku i aktywnej zakładce — teraz stale, z polem `reaction` w
  `/action-card/playable` i `/promissory/playable`; dok pulsuje zakładką i przyciskiem „Play now: <karta>”.
- Ion Storm i Demilitarized Zone (reguła bazowa) zadeklarowane jako pokryte. Nowe pola odpowiedzi — restart backendu.


## 2026-11-12 (8) — Okna reakcji kart z ręki widoczne, wskazywanie planet/systemów, mniej błędów konsoli

- **„Window open now”** (`offers/HandReactionPrompts.tsx`, w stosie `AbilityPrompts`): karta akcji / notka
  zagrywalna TERAZ w oknie reakcji (np. Tekklar Legion „At the start of an invasion combat”) wyskakuje sama w lewym
  dolnym rogu, NAD oknem walki/inwazji (dok ręki jest tam zwinięty). Fraza okna pogrubiona, bursztynowa pulsująca
  ramka, „Not now” wycisza do końca okna, „Play” otwiera ten sam formularz co upuszczenie karty. Kopie tej samej
  karty = jedno okno z licznikiem. Ręce: gra sieciowa tylko moja, lokalnie wszyscy ludzie (bez botów).
- Karta w doku ręki, której okno jest otwarte, miga (`data-reaction`).
- **Gdzie to jest?** (`search/mapPeek.ts`): opcja formularza decyzji wskazująca planetę/system (wartość albo
  `meta.planet/system/position`, sprawdzane po znacznikach wyszukiwarki na mapie) podświetla cel po najechaniu;
  przycisk z okiem prześwietla okna (`body[data-map-peek]`) i kliknięciem centruje mapę na celu.
- Konsola: dźwięki walki pytały o 16 opcjonalnych plików mp3 (każdy brak = czerwony 404). Nowy
  `GET /battle/sounds` zwraca listę istniejących próbek; front pobiera tylko je. Nowa trasa — restart backendu.

## 2026-11-12 (9) — Zgoda na transakcje, Sustain Damage przeciw Space Cannon, Ctrl+drag w ruchu

- **Transakcje ze zgodą partnera** (RULES.md 47.1a, zgłoszenie użytkownika): aktywny gracz składa propozycję
  (`/transactions/propose`), wymiana dzieje się dopiero po „Accept” partnera (`/transactions/respond`); można ją
  wycofać (`/transactions/cancel`). Odrzucenie nie zużywa limitu. Propozycja ginie z nową turą. Zawartość widzą
  tylko strony (`GET /transactions/state`), web-data niesie jawny skrót `transactionOffer`. Bot odpowiada od razu
  (⚠️ ZAŁOŻENIE `bot_accepts`). Feed: `transaction.proposed/declined/cancelled`. Stary `/transactions/resolve` usunięty.
- Okno transakcji: notki z PEŁNYM tekstem, karty akcji (gdy para może je wymieniać — Arbiters / Black Market
  Dealings) też z tekstem, panel „Waiting for … / Withdraw offer”. Partner dostaje samo wyskakujące okno
  `TransactionOfferPrompt` (stos „Available now”) z treścią i Accept / Decline.
- Nowe punkty `transaction.any_player` (transakcja bez sąsiedztwa) i `transaction.action_cards` — pod Hacan (B4).
- **Space Cannon Offense + Sustain Damage** (R_sustain_damage, RULES.md 38.4): cel pokrywa trafienia jak w walce
  (`space_cannon.required_hits`, `battle.plan_losses`, sustain / destroy / destroyDamaged), panel ma przyciski
  „Sustain” obok „Destroy”. Wcześniej trafienie zawsze niszczyło statek.
- **Ctrl+drag w ruchu**: ponowne przeciągnięcie grupy z tego samego systemu zerowało trasę w boxie, a zapytanie
  zwracało te same dane z cache, więc box nie pokazywał nowego wyboru. Efekt w `MoveRouteBox` reaguje teraz na brak trasy.
- Nowe pola stanu i trasy (`transaction_offer`, `/transactions/*`) — restart backendu.

## 2026-11-13 — B4 Hacan + Winnu — komplet (RULES.md 62.6–62.7) + pływające okna decyzji

- **Hacan** (`core/hooks/factions/hacan.py`, 12 komponentów, 0 braków, 7 testów + 6 scenariuszy API): Masters of Trade
  (secondary Trade bez żetonu — punkt `strategy.secondary_free`, okno dostaje `no_cost`), Guild Ships i Trade Convoys
  (`transaction.any_player`; notka wraca po aktywacji systemu z jednostkami Hacan), Arbiters (karty akcji w transakcji),
  Quantum Datahub Node (oferta na koniec fazy strategii), Production Biomes (ACTION), Carth of Golden Sands
  („Available now” w fazie akcji), Gila the Silvertongue (TG → głosy, efekt `Duration.AGENDA`), Harrugh Gefhara
  (`production.free`: koszt 0), Wrath of Kenara (oferta po rzucie: +1 za TG do wybranych kości, `battle.boost_combat_dice`),
  Pride of Kenara (karta planety w transakcji, `transaction.planets`, w oknie transakcji wybór planety docelowej
  jednostek), Auto-Factories.
- **Winnu** (`core/hooks/factions/winnu.py`, 11 komponentów, 0 braków, 7 testów + 4 scenariusze API): Blood Ties
  (`custodians.removal_cost` = 0), Reclamation i Reclaimer (oferty na koniec akcji taktycznej; `TACTICAL_ACTION/END` niesie
  `gained`), Lazax Gate Folding (Mecatol jako α/β w ruchu + ACTION), Hegemonic Trade Policy (`planet.swap_values` w
  `planet_stats`), Berekar Berekon (−2 do kosztu produkcji dowolnego gracza), Rickar Rickani (+2), Mathis Mathinus
  (`strategic_action.begin_hero_primary`: primary dowolnej karty, secondary tylko wybranych), Acquiescence (okno w trakcie
  secondary karty Winnu, `grant_no_cost`), Salai Sai Corian (kości = statki niemyśliwskie przeciwnika, 0 dozwolone),
  Imperator (+1 za SftT; +1 ruchu jednego statku po aktywacji systemu z planetą legendarną).
- Walka: gdy rzut stworzy oferty „po rzucie”, walka czeka w TRIGGERS (`resume=assign`) i dopiero potem otwiera przypisanie
  strat — wcześniej runda bez trafień kończyła się, zanim gracz mógł zareagować.
- ⚠️ Założenia (R62.6/62.7): limit 7 kart akcji po Arbiters nieegzekwowany; Auto-Factories liczy jedno zamówienie;
  LGF tylko w ruchu Winnu; planeta docelowa Pride of Kenara wybierana w propozycji; Imperator + Gravity Drive na tym samym
  statku; Reclamation bez reguły zastępczej przy pustej rezerwie.
- **Pływające okna decyzji** (prośba użytkownika): `ds/Modal` ma tryb `floating` — bez tła, nie blokuje planszy,
  przeciągany za nagłówek (pozycja zapamiętana, dwuklik = reset), klik poza oknem go nie zamyka. Włączony we wszystkich
  oknach decyzji gry (użycie zdolności / technologii / legendy, zagranie karty, transakcja, secondary, kroki primary,
  Custodians, ruch / załadunek / usuwanie nadwyżki, ekspedycja, lista akcji komponentów). Oferty już pływały.
- „Gdzie to jest?”: `mapRefKeys` rozbija wartości złożone (`pozycja|planeta`, `planeta>cel`), więc najechanie opcji
  w starych formularzach też podświetla cel na mapie.
- Nowe pola stanu (`StrategyResolution.secondary_players`) i odpowiedzi (`/transactions/state`: `myPlanets`, `planets`) —
  restart backendu.

## 2026-11-13 (2) — Domknięcie Fali 1 frakcji: rulingi, limit ręki, Imperator osobno (RULES.md 53.8, 62)

- Przegląd ⚠️ Fali 1 (B1–B4) z rulingami `F_*.md`; decyzje użytkownika: cała grupa „niezgodne z rulingiem” do naprawy.
- **Gila the Silvertongue:** bez zwykłych głosów (wstrzymanie się) brak dodatkowych głosów; wstrzymanie zwraca wydane TG
  (`agenda_phase.extra_votes(base_votes=)`, `_refund_vote_effects`).
- **Exotrireme II:** brak oferty po ogłoszonym odwrocie przeciwnika (z dozwolonym celem).
- **Sąsiedztwo z akcji taktycznej dla wszystkich** (`core/action_adjacency.py`): SCC i Lazax Gate Folding działają też dla
  Deep Space Cannon innych graczy, odwrotów i sąsiedztwa graczy (`neighbors`).
- **Reclamation / Reclaimer:** przy pustej rezerwie struktura zdjęta z systemu bez własnego żetonu
  (`board_structure_sources`, `place_structure(source=)`); Construction i produkcja jeszcze nie.
- **G'hom Sek'kus:** blokada wejścia (supernowa, asteroidy bez Antimass — `movement.entry_blocked`) i rzut za gravity rift
  (`movement.roll_rift_exit`). Travel Ban — z efektami agend.
- **Military Support w pierwszej turze fazy akcji** już działał (pauza początku tury z 3faeb3a) — scenariusz API to pilnuje.
- **Limit ręki kart akcji (RULES.md 53.8, `core/hand_limit.py`):** gracz ponad 7 kart nie zagra karty, nie odda jej w
  transakcji, nie skończy tury/fazy; odrzuca SAM przeciągnięciem karty na strefę „Drop to discard”
  (`POST /action-card/discard-excess`; `/action-card/playable` zwraca `discard`, `handLimit`). Dok ręki sam się otwiera.
- **Strefa zrzutu kart** (prośba użytkownika): prawie cały ekran nad dokiem, delikatna (cienka przerywana ramka, lekki
  odcień, podpis w pastylce); wariant szary dla odrzucania.
- **Imperator** (decyzja użytkownika): osobny kanał premii ruchu `imperator` (flaga `GameState.imperator_used`, przełącznik
  „Use Imperator” w panelu ruchu, `/tactical/move-range?imperator=`) — inny statek niż Gravity Drive albo ten sam.
  Wcześniej Imperator jechał na fladze Gravity Drive i bez technologii `gd` nie miał przełącznika w UI.
- **Decyzje użytkownika (2026-11-13, R62):** N'orr Supremacy pozwala pominąć prerekwizyty skipami (wejście `skips`).
  Pride of Kenara: cel jednostek zawsze wybiera Hacan — przy propozycji partnera wpis to sama planeta, cel Hacan podaje
  przy akceptacji (`planet_destinations`, lista w `offer.unitDestinations`, wybór w oknie oferty). T'ro (<2 piechoty
  → ile ma), Sucaban (zwrot po zapłacie), Agnlan Oln (raz na rodzaj rzutu), Auto-Factories (jedno użycie PRODUCTION)
  potwierdzone bez zmian. Fala 1 bez otwartych ⚠️ decyzji (zostają braki zależne: Travel Ban, Construction z planszy).
- Nowe pola stanu (`imperator_used`) i trasy (`/action-card/discard-excess`) — restart backendu.

## Walka naziemna bez Commit, nazwy bitew w feedzie, podsumowanie bitwy, transakcje na chipach (2026-11-13)

- **Walka naziemna zawsze w kroku 4** (decyzja użytkownika, RULES.md 40.1 I7a): sporna planeta (siły aktywnego obok
  cudzych, np. po Crash Landing) otwiera inwazję bez sił w przestrzeni; Commit bez lądowania nie pomija walki, Establish
  Control obejmuje też planety walki (`invasion._contested`, `begin_invasion`, `advance`, `_establish_control`).
- **Feed Activity — bitwy z nazwą:** „Space battle of <system>” / „Ground battle for <planeta>”; straty rundy
  (`combat.losses`), bombardowanie, Space Cannon Defense, Establish Control i straty od Space Cannon mają własne wpisy
  zamiast „Result of X's action”. `battle:close` = podsumowanie: zwycięzca/remis, liczba rund, łączne straty stron
  (fakt `battle_result` + `units`).
- **Okno bitwy:** ekran wyniku ma panel „Battle summary” (rundy, trafienia, Sustain Damage, zniszczone jednostki ikonami
  `Unit`) — `battle/BattleSummary.tsx`.
- **Okno transakcji:** notki = chip `PromissoryNote` z panelu gracza (opis po kliknięciu), karty akcji = chip z
  `ActionCardDetailsCard` w popoverze, wybór osobnym przyciskiem „Add / In deal”; fragmenty reliktów ze spritem jak
  `FragmentStack`. Także okno zgody partnera.
- **Hold:** przegląd — logika cofania (8 kroków, blokady kości/dobrań/fazy) bez zmian; panel opisuje cofany krok tak
  jak feed Activity (`nextSeq` w `/hold/candidates`) zamiast surowej etykiety, plus runda/faza migawki.
- **Steering:** nowa zasada „Spójność i reużycie” (używać istniejących komponentów, ujednolicać odstające elementy).
- Nowe pole odpowiedzi (`nextSeq`) i logika inwazji — restart backendu.

## Walka: Sustain ×2 w przydziale trafień, wynik dopiero po kościach, szyk eskadr, rakiety, Assault Cannon (2026-11-13)

- **Błąd przydziału (zgłoszenie: 13 trafień przy 11 HP, nie dało się zatwierdzić):** silnik liczył Sustain Letneva
  z Non-Euclidean Shielding ×2 (`required` 13 = 9 statków + 2 tarcze × 2), a front liczył tarczę za 1 i pokazywał HP 11.
  Teraz `battle.absorbable_hits` = jedno źródło „życia” strony (pasek HP i `required_hits`), widoki podają
  `sustainCancels` (walka) / `cancels` (bombardowanie, Space Cannon Defense, Space Cannon). Front: `markWeight`,
  `isCovered` (ostatnia tarcza może anulować mniej — same tarcze), `toggleMark` w `battleAssign.ts` — wspólne dla okna
  bitwy, inwazji i Space Cannon. Sustain nadany komponentem (Void Shielding) tylko dla `sustainable` egzemplarzy.
- **Bez spoilera:** do końca kości i strzałów okno nie pokazuje panelu przypisania („covers N hits”) ani akcji kolejnego
  kroku — `freezeBattleSides` ustawia `resolving` (panel „Dice are rolling… / Volley in flight…”).
- **Animacje nie wracają:** okręt to zawsze ten sam element (`div` z rolą przycisku; zamiana div↔button przemontowywała
  okręty), a wlot floty gra raz na bitwę także po „Hide” → powrót (`ENTERED` w `BattleFleet`, czyszczone po walce).
- **Szyk:** myśliwce w eskadrach-kluczach po ≤5 (prowadzący od strony wroga, eskadra dryfuje razem, 1–2 kolumny
  eskadr), liczny szereg (>5) w szachownicę zamiast jednej długiej kolumny.
- **Rakiety:** krążowniki, lotniskowce i co druga kość dreadnoughta odpalają rakiety lecące łukiem (`offset-path`) ze
  smugą dymu i pomarańczowym trafieniem; dźwięk `missile`.
- **Assault Cannon:** silnik dopisuje efekt do `ActiveCombat.effects` (NIE do `log` — pusty log = start walki), widok
  `effects`; okno bitwy: ładowanie działa na największym okręcie, ciężka wiązka do niszczonego statku, rozbłysk,
  plansza „Assault Cannon — X destroys Y's Z”, dźwięk `assaultCannon`.
- **Decyzje „wskaż okręt” w bitwie:** oferta z jednym wyborem jednostek jednej strony (ofiara Assault Cannon, naprawa
  Duranium Armor) podświetla okręty na polu bitwy — klik = wybór (panel decyzji zostaje alternatywą). Opcje mają
  grafikę jednostek (`unit_meta`).
- **Okno decyzji:** kafelek technologii źródłowej (`Tech`, jak w panelu gracza; pole `source` oferty), tytuły i nazwy
  opcji zawijają się zamiast ucinać, opis do 4 linii. **Predictive Intelligence:** pule żetonów − / + startujące od
  obecnego rozdziału (wspólny `shared/ui/CommandPools`, ten sam co w fazie statusu).
- Nowe pola (`effects`, `sustainCancels`, `cancels`, `source`) — restart backendu.

## Dźwięk: UI, muzyka tła, kwestie frakcji (2026-11-13)

- **Wspólny silnik** `frontend/src/shared/audio/`: jeden `AudioContext`, kanały `music` / `voices` / `ui` / `effects`,
  ustawienia w `audioSettings.ts` (localStorage), przycisk z suwakami w pływającym pasku mapy (`AudioSettingsButton`,
  obok Events). Efekty bitwy (`battleSound.ts`) idą pod suwak „Battle effects”.
- **Spis plików** `GET /audio/manifest` (`api/routers/audio.py`): głosy `assets/voices/<frakcja>/`, transmisje
  `assets/voices/transmissions/`, muzyka `assets/music/[<nastrój>/]` (poza repo), UI `assets/extra/sfx/ui/`.
  `GET /audio/homes` = domy graczy (`board_graph.home_positions_by_player`).
- **UI** (Kenney „Interface Sounds”, CC0, licencja obok plików): globalny nasłuch kliknięć (`installUiSounds`;
  przycisk = click, zakładka = select, przełącznik = toggle; `data-sound="<nazwa>|none"` nadpisuje), `turn` na moją
  turę, `transition` na zmianę fazy, `drop` przy upuszczeniu karty, `error` przy odrzuconej akcji (MutationCache).
- **Muzyka** (`music.ts`): JEDNA wspólna playlista z całego `assets/music/` (także podfoldery; decyzja
  użytkownika — bez nastrojów), start po pierwszym geście, losowo bez powtórek, przenikanie 2,5 s; ścisza się pod głos.
- **Kwestie frakcji** (`voiceCues.ts`, z NOWYCH wpisów feedu Activity): start walki → `homeinvasion`+`homedefense` w
  domu obrońcy, `offensesuperior` (+`defenseoutnumbered` przy miażdżącej przewadze), inaczej `battle`; zdolności z
  własnym nagraniem po id komponentu (Pillage, Orbital Drop, Reclamation, Fabrication, Yin Spinner, Devotion/Impulse
  Core, Artuno, Cavalry; relikt Naaz) — zagrają same, gdy mechanika trafi do silnika; bohater → `special`; pas → żart
  (30%); transakcja do mnie / faza agendy → transmisja. Jeden głos naraz, kolejka ≤2.
- **Motyw menu:** `assets/music/main theme.*` gra w pętli na ekranie startowym (menu, lobby, kreator: frakcje,
  kolory, miejsca — `MenuMusic` w `StartScreen`), wygasa przy starcie intro i nie wchodzi do playlisty w grze.
  `/audio/manifest` jest jawne (gość przed dołączeniem), `/audio/homes` — tylko z miejscem. Suwaki dźwięku także
  jako zakładka „Sound” w Settings (`AudioSettingsPanel`, wspólny z przyciskiem na mapie).
- Nowe trasy `/audio/*` — restart backendu.

## TYMCZASOWO: kreator tylko z gotowymi frakcjami (2026-11-13)

- Wybór i „Random” w kreatorze/lobby ograniczone do frakcji ukończonych w silniku (Sardakk, Letnev, Jol-Nar,
  Sol, Arborec, Hacan, Winnu) — `frontend/src/domains/setup/tempReadyFactions.ts`. „Random” rozstrzyga front
  przed `/game/new` (`resolveRandomFactions` z zawężonej puli). Backend bez zmian. Do usunięcia, gdy frakcje
  będą kompletne (plik + 2 użycia w `SetupWizard.tsx`).

## Poprawki: notki w transakcji (ukryta ręka) + Public Disgrace z ręki (2026-11-13)

- **Transakcja** (zgłoszenie: Hacan z nie-sąsiadem — „gracz nie ma notki w ręce”): w grze sieciowej `/hand`
  zwraca rękę oglądającego, więc okno pokazywało MOJE notki jako notki partnera. Ręka partnera jest ukryta
  (R_promissory_notes): strona „You receive” pokazuje notki możliwe (`transaction.requestable_notes`,
  `GET /transactions/state` → `requestableNotes`), propozycja nie sprawdza ręki partnera, akceptacja tak
  (bot bez notki odrzuca). Karty akcji partnera (Arbiters): „Their hand is hidden” — ⚠️ prośba o konkretną
  kartę do rozstrzygnięcia. RULES.md 47.1a.
- **Public Disgrace**: po wyborze karty strategii przez rywala karta jest grywalna w doku ręki (przeciągnięcie,
  „Play now”) — `hold_rewind.just_passed` → `hold_seq` w `GET /action-card/playable`, zagranie przez
  `/hold/play` (cofa ten wybór). Dotyczy każdej karty hold-rewind, której okno minęło ostatnim krokiem. RULES.md 53.7.
- Nowe pola API (`requestableNotes`, `hold_seq`) — restart backendu.

## Fala 2 · B5: The Mentak Coalition (2026-11-13)

- Komplet 12/12 komponentów (`core/hooks/factions/mentak.py`, RULES.md 62.8): Ambush, Pillage, Promise of
  Protection, Mirror Computing, Salvage Operations, Suffi An, S'ula Mentarion, Ipswitch (Sleeper Cell), Fourth Moon,
  Moll Terminus, The Table's Grace / Corsair. Testy: `tests/factions/test_mentak.py` (15),
  `test_flows_mentak.py` (6 scenariuszy przez API), Pillage w `test_activity.py`.
- Nowe punkty silnika (reużywalne): trafienia „na starcie walki” przypisywane w zwykłym ASSIGN przed AFB
  (`battle.add_start_hits`, `ActiveCombat.start_hits/start_assign`, wpis logu `AMBUSH` — okno bitwy rzuca kośćmi
  jak salwę); `combat.sustain_denied` w `battle.combat_units` (walka, Space Cannon, inwazja);
  `payment.trade_good_value` (walidacja, produkcja, cele; `tradeGoodValue` w widokach produkcji, badań, Leadership,
  Custodians, celów); `cause` w `TRADE_GOODS_GAINED` (transakcja / zamiana commodities); `ActiveCombat.destroyed_all`
  (ślad strat całej walki z `unit_ops`); `ProductionGrant.allowed_types`; typ statku w `movement.pass_foreign_ships`;
  `faction_components.ability_used` (emisja `FACTION_ABILITY_USED`).
- Poprawka: Corsair zastępował krążownik bez Cruiser II — teraz tylko z przełomem I `cr2` (silnik i panel gracza).
- ⚠️ ZAŁOŻENIA do potwierdzenia: P1 (TG z transakcji = jedno Pillage na stronę), P2 (zabrana commodity = TG u Mentaka),
  H1 (limit floty przy Sleeper Cell sprawdzany zwykłym oknem, nie od razu w walce).
- Do zrobienia przy okazji: płatność w formularzach ofert (`DecisionFields`) liczy TG 1:1 (Mirror Computing tam nie
  działa w podglądzie, silnik liczy dobrze); wybór notki przez przeciwnika to lista nazw, nie chipy `PromissoryNote`.
- Nowe pola stanu/API (`start_hits`, `destroyed_all`, `allowed_types`, `tradeGoodValue`) — restart backendu.

## Pula floty zawsze natychmiast + decyzje Mentak (2026-11-13)

- Decyzje użytkownika: Mentak P1 ✅ (TG z transakcji = jedno Pillage na stronę), P2 ✅ (zabrana commodity = TG).
- **RULES.md 42.1 (zasada ogólna):** nadwyżkę ponad pulę floty usuwa się NATYCHMIAST, w każdym systemie i w każdej
  chwili — także w aktywnym systemie i w trakcie walki. `limits.enforce_limits` po każdym commicie; okno `FLEET_POOL`
  przerywa inne okno (`timing.interrupt` → `GameState.suspended_window`, przywracane w `timing.close_window`); akcje bez
  własnego okna (ruch, produkcja, rzuty walki, AFB, przypisanie strat, odwrót, oferty, pas) blokuje
  `timing.require_no_limit_window`. Harness scenariuszy (`Flow.fight`) usuwa nadwyżkę podpowiedzią silnika.
- Capacity bez zmian (własne wyjątki w walce).
- Nowe pole stanu `suspended_window` — restart backendu.

## Efekty agend - cała talia oficjalna (50/50) + jawne riders (2026-11-13) — RULES.md 51.6

- Model: efekt WYNIKU = hook `AGENDA_OUTCOME_RESOLVED`/DURING ze źródłem `agenda:<id>`; rozstrzygana karta
  (`agenda.resolving`, też dyrektywa/„Against") jest źródłem dla KAŻDEGO gracza do „dalej" mówcy. Riders po efekcie
  (AFTER). Wybory graczy = oferty/decyzje (głosowanie, „dalej" i koniec fazy czekają). Moduły:
  `core/hooks/agendas_common.py`, `agendas_directives.py` (dyrektywy + skutki „Against"), `agendas_laws.py` (prawa).
- Faza: karty „reveal another agenda" odrzucają się same; Covert Legislation (ukryta agenda tylko dla mówcy);
  Miscount Disclosed (ponowne głosowanie nad prawem); Representative Government (1 głos); Public Execution (bez głosu
  do końca fazy); Committee Formation (wybór bez głosowania); Checks and Balances (karta strategii dla innego gracza
  - `recipient` w `/strategy/pick` + wybór w stole kart; „Against": 3 planety w kroku 3); Imperial Arbiter; Galactic
  Crisis Pact (okno secondary dla wszystkich); `agenda_phase.remove_law` = jedyne zdejmowanie prawa (`LAW_DISCARDED`).
- Nowe punkty `rules_hooks`: `agenda.single_vote`, `hand_limit.action_cards`, `action_cards.forbidden`,
  `fleet_pool.token_cap`, `limits.pds_unlimited`, `bombardment.forbidden_traits`, `movement.wormholes_blocked` (ruch +
  odwrót), `movement.through_nebula`, `production.units_per_cost`, `technology.strategy_card_free`,
  `units.sustain_lost`, `strategy.give_chosen_card`, `agenda.planets_ready_limit`; filtr zdolności jednostek
  (`register_unit_ability_filter`, Articles of War); `objectives.reveal_from_stage` / `make_secret_public`.
- **Riders jawne:** web-data `agendaPhase.predictions` (kto, karta, na jaki wynik), chipy przy wynikach i lista
  „Riders" w oknie Rady, wyniki riderów w historii agendy, fakt `rider` w feedzie Activity.
- Web: `agendaCovertCard` (tylko mówca), `revealedSecrets` + `knownUnscoredSecrets` (Search Warrant),
  `strategyGivesCards`, `voters[].singleVote`, `revoteLaw`, `phaseBlocked`.
- Testy: `tests/test_agenda_effects.py` (31), `tests/test_flows_agenda.py` (scenariusz przez API), rider w
  `test_activity.py`. Pokrycie: 50/50 agend talii `agendas_pok` (Covert jako reguła `core`).
- ⚠️ ZAŁOŻENIA 1-12 w RULES.md 51.6 (m.in. nadmiar fleet pool przy Fleet Regulations, statystyki mechów przy Articles of
  War, badanie bez pominięć specjalnością w Ixthian Artifact / Wormhole Research).
- Nowe pola stanu (`phase_blocked`, `covert_card`, `resolving`, `revote_law`, `strategy_choices`) i API — restart backendu.


## UI: mniej okienek, jedno okno badania i jedno okno ruchu (2026-11-14)

- **Badanie z komponentu = pełne okno badania.** Nowy `core/research_offer.py` + wejścia `research` / `info`
  (`offer_inputs`): Focused Research po zagraniu tworzy obowiązkową decyzję badania, którą front pokazuje tym
  samym `TechnologyOverlay` co karta Technology (`domains/offers/ResearchOfferOverlay.tsx`), zamiast listy.
  `strategy_cards.technology.research_view` = wspólny opis okna (`trade_goods_only` dla „Spend 4 trade goods”).
- **Doctor Sucaban przed zapłatą** (decyzja użytkownika, R62.md): dopóki decyzja badania czeka, `research_payer`
  zwraca badającego → zniżka zamiast zwrotu; kartę wolno zagrać z <4 TG, gdy możliwa zniżka pokrywa różnicę
  (`research_offer.potential_discount`, dostawca w `hooks/factions/jolnar.py`). Oferty badania idą na koniec kolejki
  w UI (najpierw decyzja Sucabana). Reveal Prototype / Enigmatic Device: nadal zwrot po zapłacie (do przeniesienia).
- **Ruch:** jedno okno (`MoveRouteBox`). Zwykłe przeciągnięcie na aktywny system w kroku MOVEMENT otwiera je z trasą
  (jak Ctrl+drag); z `MovementStepPanel` usunięty stary kreator „Move by picking a system” i lista „In range”.
- **Karta strategii bez rzędu techów** — technologie tury trafiły do nowej zakładki „Techs” w doku ręki (te same
  kafelki `Tech`, najpierw działające w turze).
- **Przeskok ekranu / pasek z prawej:** listy `Select` bez scroll locka (`modal={false}`), strona gry z
  `overflow: hidden` na `<html>` (desktop, zakładka mapy).
- Wspólny `hasNoLegalOption` (5 kopii sprawdzenia w modalach). Testy: `test_action_cards_economy.py`,
  `factions/test_jolnar.py`, scenariusz API `test_flows_jolnar.py::test_sucaban_obniza_koszt_focused_research`.
- Nowy hook i moduł — restart backendu.

## UI: centrum decyzji + wybory przez właściwe okna we wszystkich formularzach (2026-11-14)

- **Centrum decyzji** (`domains/offers/AbilityPrompts.tsx` → `DecisionCenter`): jedna kolumna w prawym dole
  (przeciągalna, zwijana do pastylki „Decisions”) zamiast trzech okien w dwóch rogach — bieżąca oferta/decyzja
  (`OfferCard`), propozycja transakcji, karty z ręki z otwartym oknem, „Available now”. Usunięty duplikat „Play now”
  z doku ręki (zakładka ręki dalej miga).
- **Wybory przez właściwe okna — wszystkie formularze** (karty akcji, relikty, technologie, liderzy, notki, oferty):
  `optionKinds.classifyOptions` rozpoznaje rodzaj opcji po wartościach; `DecisionPickers`: technologie = kafelki
  technologii (kolor + karta po najechaniu, bez list rozwijanych), gracze = ikony frakcji, planety/systemy = klik na
  mapie (`useMapPick`, jedno pole naraz). Test `optionKinds.test.ts`.
- **Badania jednym oknem:** `research_offer.register_decision` / `begin` (nowe zdarzenie
  `COMPONENT_DECISION`, ograniczenie `research_allowed`) — Focused Research, Reveal Prototype (tylko pasujące
  ulepszenia) i Enigmatic Device otwierają pełne okno badania po zagraniu; Sucaban przed zapłatą (R62.md).
- Restart backendu (nowe zdarzenie i hooki).

## Transakcje: stół zamiast propozycji + negocjacja Trade (wash, dług) (2026-11-14)

- **Stół transakcji** (RULES.md 47.1b, `core/transaction_table.py`, `GameState.transaction_tables`): para graczy
  siada do stołu (otwiera każda strona), każdy kładzie WYŁĄCZNIE własne rzeczy, rzeczy partnera widać dopiero na
  stole; dwa Ready = wymiana (`transaction.resolve_transaction`), każda zmiana zdejmuje Ready. Koniec list
  „o co mogę prosić” (`requestable_notes`) i `/transactions/propose|respond|cancel` → `/transactions/table/
  open|side|ready|close`. Jedna walidacja strony: `transaction.validate_side`.
- **Żetony długu na stole** (`debt_tokens` w stronie): z nie-sąsiadem / poza turą stół przyjmuje tylko dług
  (bez zużycia limitu transakcji). Zakładka „Debt tokens” zniknęła; rejestr długów (zwrot) został pod stołem.
- **Trade krok 3** (RULES.md 47.4): posiadacz „Negotiate” z każdym graczem — kładzie „darmowe secondary”, drugi
  gracz cenę (dług / wash −N / komponenty). Umowa = wskazanie (`draft.deal_players`) + dług od razu; komponenty
  i wash czekają w `GameState.trade_deals` i po uzupełnieniu commodities silnik otwiera stół wstępnie wypełniony
  (niewiążący — obaj Ready).
- Front: jeden komponent `TradingTable` (okno Transaction, dok decyzji — zaproszenie „X sat down to trade with
  you”, okno Trade). Feed: `transaction.opened|agreed|closed`. Testy: `test_transaction.py`, `test_trade_deal.py`,
  `Flow.transact` w harnessie.
- Nowe trasy i pola stanu — restart backendu.

## Komunikaty w jednym miejscu + decyzje „wskaż okręt” obu stron w walce (2026-11-14)

- **Assault Cannon u obu stron**: okno bitwy brało tylko PIERWSZĄ ofertę „wskaż okręt”, więc druga strona
  (np. Arborec) nie mogła kliknąć statku. `battle/shipPick.ts` → mapa gracz → oferta; obie floty klikalne naraz.
  Panel środkowy: „Your decision…” (moja), „X decides…” (steruję nim: lokalnie / tryb testowy hosta),
  „Waiting for X…” (cudza w sieci — statki nieklikalne).
- **Chip tury w trybie testowym hosta** nie pisze już „Waiting for Player p4”, gdy sterujesz p4: każda czekająca
  decyzja = „Your move - <frakcja>: …”; nazwy = pełne nazwy frakcji.
- **Jedna strefa komunikatów** `game-shell/components/Notifications/NotificationArea`: odrzucone akcje
  (422, `PhaseNoticePanel`) + 403 („Not your move”, dawny osobny dymek) + toasty Activity — kolumna u góry na środku
  mapy (nie zasłania paska narzędzi mapy ani zdarzeń w prawym rogu); przy oknie pełnoekranowym na środku jego
  nagłówka i NAD nim. Usunięte lokalne paski `notice` w oknach walki i inwazji (migały: store czyści notice po 80 ms).

## Stałe okna zdolności jako znacznik „Ready” + gracze z logo i kolorem w komunikatach (2026-11-14)

- **Carth of Golden Sands** (okno = cała faza akcji, także w cudzej turze) nie wyskakuje już jako pełna karta
  „Available now”: `window_use(..., standing=True)` → `available-now` zwraca `standing`, centrum decyzji pokazuje
  jedną cichą linię „Ready · Leader · Carth… [Use] [X]” (tekst po kliknięciu nazwy; sama nie otwiera paska centrum).
  Chwilowe okna (Sardakk, Sucaban, Munitions…) bez zmian.
- **`shared/ui/PlayerTag`** — znacznik gracza w linii (logo frakcji w obwódce koloru + nazwa w kolorze, wygląd
  `PlayerChip`). Użyty w: opisach feedu Activity i toastach (`describeActivity` → `name()`, wyniki agend), stole
  transakcji, kartach decyzji (właściciel cudzego komponentu, gracz przy kilku ludziach lokalnie), oknie Space Cannon
  („X fires on Y”), ostrzeżeniu o puli floty w fazie statusu.
- **Wybór gracza w formularzach**: kafelki z logo w kolorze gracza i podpisem skutku; opcja bez celu (Carth: „self”)
  nie psuje już rozpoznania graczy (`optionKinds.some`).
- Usunięty zdublowany `case "rider"` w `describeActivity` (ostrzeżenie Vite).

## 2026-11-14 — Fighter II: ładunek ze startu + limity w walce (RULES.md 39.6, 57.8)

- Okno trasy znów pokazuje Fighter II ze startu także jako ładunek (lecące same liczą się do fleet pool w celu,
  przewożone - nie). Wspólny limit sztuk w UI: `routeTypes.otherRoleCount` (store `bumpDraftPick`, `prunePicks`).
- W trakcie walki w systemie (`capacity.combat_in_progress`) nie ma nadwyżki capacity, a nadmiar Fighter II nie liczy się
  do fleet pool (R_fleet_pool, Notes); oba sprawdzane po walce. Statki nie-myśliwskie - pula floty cały czas (42.1).

## 2026-11-14 — Pasek u góry: menu God-Mode, pasek zasobów; Undo ruchu dla gracza; attachmenty w płatnościach

- Nagłówek gry: zostały Rules, Report bug i (tylko host) menu **God-Mode** — Undo/Redo historii, ruch jednostek bez reguł,
  edytor graczy, przełącznik „No action card hand limit”. Usunięte Refresh i luźne Undo/Redo/Move/Players.
- Limit ręki kart akcji do wyłączenia: `GameState.action_card_limit_disabled` (patch `/god-mode/patch`), web-data
  `gameState.actionCardLimitDisabled`; `hand_limit.action_card_limit` zwraca wtedy `None` (RULES.md 53.8).
- „Undo last move” w kroku ruchu: `POST /tactical/undo-move` — aktywny gracz (nie tylko host) cofa tylko ostatnią migawkę
  ruchu statków `tactical:move:*`; inaczej 422, inny gracz 403 (RULES.md 44.1a). Testy: `tests/test_undo_move.py`.
- Pasek zasobów „jak w strategiach” w pasku zakładek (`ResourceBar`): resources/influence (gotowe/wszystkie), TG,
  commodities, karty akcji/notki, CC, fragmenty, dług — ten sam `StoresStrip` co w strefie gracza (+ blok ekonomii).
- Planety w panelach wydawania (`PlanetCard` w trybie wyboru): pod kartą żetony attachmentów z nazwą i modyfikatorami
  w podpowiedzi (`PlanetAttachmentStrip`).

## 2026-11-14 — Klik na systemie, bez menu prawego klawisza, pasek zasobów v2, stół transakcji

- Mapa: LEWY klik w system = menu „Activate system” (+ „System details”), PRAWY klik = okno systemu (dossier).
  Telefon: tap dalej otwiera dossier. Klik w planetę na mapie działa jak klik w system.
- Usunięte menu prawego klawisza (exhaust/refresh, stan lidera) z planet, technologii i liderów — stan prowadzi gra.
  `leaderMenu.tsx` skasowany; prop `playerId` zostaje w typach dla zgodności wywołań.
- Pasek zasobów: grupy Total / Optimal (jak ledger w strefie gracza, z flex) / TG + commodities / CC / Ships (statki na
  planszy według typu, sprite `Unit`) / fragmenty. Bez kart akcji; jeden wygląd grup, kolor tylko w ikonach.
- Stół transakcji: układ Ty (lewa) | stół (środek: „X gives” obu stron w kolorach graczy) | partner (prawa, Ready,
  jego TG/commodities). Miganie/skakanie: `useTransactionState` ma `placeholderData: keepPreviousData` (klucz ze
  „stampem” stołu zmieniał się po każdym ruchu i stół się odmontowywał).

## 2026-11-14 — Corsair (Mentak, The Table's Grace): przelot przez obce statki w podglądzie trasy

- Błąd: `movement_route.route_report` liczył trasę bez typu statku, więc przez system z obcymi statkami zwracał
  „No legal route” i UI nie pozwalało ruszyć Corsairem (silnik `can_move`/`move_fleet` miał hook, podgląd nie).
- Poprawka: trasa najpierw dla całej floty, potem dla każdego typu statku ze źródła (wyjątki przejezdności,
  RULES.md 62.8); alternatywy = suma tras wszystkich typów. Na trasie przez obce statki dolatuje tylko Corsair.
- Test: `tests/factions/test_mentak.py::test_corsair_podglad_trasy_i_ruch_przez_obce_statki`.
## 2026-11-14 — Sarween Tools przy produkcji z karty strategii, wyraźna zniżka; Decisions w prawym górnym rogu

- Błąd: hook Sarween Tools (`core/hooks/technologies.py`) zwracał 0 przy KAŻDYM `production_grant`, także `standalone`
  (Warfare secondary, Minister of Industry) — a to użycie PRODUCTION (RULES.md 57.3). Teraz zniżki nie ma tylko dla
  grantów „produce N units”; R55.4 doprecyzowane.
- Widok produkcji: `costReductionSources` (`production.cost_reduction_sources`, nazwa z assetów). Okno pokazuje zieloną
  plakietkę „−1 Sarween Tools” (także AIDA po włączeniu), przekreślony koszt bazowy w pasku i w „Total cost”.
- Centrum decyzji (`DecisionCenter`) domyślnie w prawym GÓRNYM rogu pod paskiem narzędzi mapy (wcześniej prawy dół na
  panelach karty strategii i akcji); wysokość ograniczona nad nimi; klucz pozycji `decisionCenter.pos.v2`.
- Testy: `test_sarween_tools_dziala_przy_produkcji_z_karty_strategii`, `test_zrodla_zniżki_produkcji_maja_nazwe_z_danych`.
## 2026-11-15 — God-Mode „Skip player” (tury wszystkich graczy bez akcji)

- `skip_flow.skip_player` + `POST /turn/skip-player` (HostOnly): w fazie akcji tura przechodzi do następnego
  niespasowanego gracza (gdy wszyscy spasowali — po prostu następny w inicjatywie) bez akcji i pasa; blokady sprzątane
  jak przy „Skip phase”, nowy gracz dostaje świeżą turę (`action_budget.reset_turn`), bez wyzwalaczy końca/początku tury.
- UI: przycisk „Skip player” w `TurnControls` pod „Skip phase” (ustawienie „Skip phases”, tylko faza akcji, w sieci host).
- Feed: etykieta `turn:skip-player` → `turn.next`. Testy: `tests/test_skip_flow.py` (3 nowe), `test_activity.py`.

## 2026-11-15 — Prawa w grze: pasek + pełna karta po kliknięciu (bez podwójnego tekstu)

- `LawCard` (panel „Laws in play”) to teraz niski pasek jak chip technologii: pieczęć, nazwa, kto/co wybrano — bez
  skrótu `mapText` w wierszu. Klik otwiera `LawDetailsCard` z pełnym tekstem prawa (`text1`/`text2`).
- `LawDetailsCard` nie pokazuje już sekcji „Ongoing effect” (`mapText` to skrót AsyncTI4 tego samego prawa — tekst
  dublował się). Tylko front; QA: tsc + eslint.

## 2026-11-15 — Trade primary: szersze okno ze stołem transakcji

- Okno primary karty Trade (ze stołem `TradingTable` po „Negotiate”) miało stałe 560 px i stół się nie mieścił.
  Nowa mapa `PRIMARY_MODAL_SIZE` (`domains/strategy/cards/index.ts`): Trade = 1080 px (jak okno Transaction),
  reszta kart bez zmian (560). Szerokość i tak ograniczona do ekranu. Tylko front; QA: tsc + eslint + vitest.

## 2026-11-15 — Masters of Trade: scenariusz przez API + informacja w oknie follow

- Zgłoszenie „Hacan dalej płaci żeton za follow Trade”: silnik NIE pobiera żetonu (nowy scenariusz
  `test_masters_of_trade_follow_trade_bez_zetonu` w `tests/factions/test_flows_hacan.py` — pusta pula, follow
  przechodzi, żeton zostaje). Nie udało się odtworzyć poboru; jeśli wróci — potrzebny stan gry z momentu błędu.
- Okno secondary dostaje w kontekście `no_cost_why` (`"p1=abilities:master_of_trade;p2=promissory_notes:acq"`):
  `strategic_action._no_cost_source` (pokrycie `covers` hooka PERMIT), `grant_no_cost(..., source)` (Acquiescence),
  Galactic Crisis Pact (`agendas:crisis`). `SecondaryDecisionModal` pokazuje wyraźną linię
  „Masters of Trade: you may follow for free — no command token is spent.” (nazwa z danych).
- QA: pytest (factions, agendy, strategia), ruff, mypy zmienionych; front tsc + eslint + vitest game-shell.

## Sieć: okna karty strategii tylko dla adresata (2026-11-15)

- Błąd: gdy gracz zagrywał kartę strategii, pozostali widzieli pusty modal primary („Loading...”) i dostawali w pętli
  „Not your move: You can only see your own private information, not '<frakcja>'” — `StrategyPrimaryStepModal`
  pytał `GET /strategy/options` o `player_id` właściciela karty (403 z `require_view`, RULES.md 44.3).
- `network/useNetworkMe.ts`: `canActAs(me, playerId)` / `useCanActAs()` — lustro `Identity.sees_everything`
  (lokalnie i host bez miejsca: wszyscy; gracz sieciowy: tylko on). `StrategyPrimaryStepModal` renderuje się tylko
  właścicielowi karty, `SecondaryDecisionModal` tylko bieżącemu respondentowi. Pozostali widzą istniejący status
  „Waiting for X (resolve a strategy card)” w nagłówku (`TurnStatusChip`, `core/actor.awaiting`).
- QA: front tsc + eslint zmienionych + vitest `domains/network` (nowy `useNetworkMe.test.ts`). Backend bez zmian.

## Okna czasowe widoczne na ekranie + bramka zamknięcia walki (2026-11-15)

- Zgłoszenie: okna czasowe znikają po cichu (Salvage Operations po zamknięciu bitwy, agenda when/after). RULES.md 54.9.
- Błąd: `battle.close_combat` zamykało walkę mimo oczekującej oferty Salvage Operations; oferta zostawała martwa
  (`salvage_types` czyta zniszczone statki z `active_combat`). Teraz `close_combat` rzuca `ValueError`, gdy są
  `pending_offers`; „Close battle” jest wyłączony z podpisem „Waiting for decisions from this combat”.
- `core/timing_view.py` + `GET /window/open-now`: jawne okna otwarte teraz (`reaction_cards.open_windows`) z angielską
  etykietą, podmiotem i „co je zamyka”. `OpenWindow.public` (Acquiescence Winnu = niejawne, nie trafia do paska).
- Front: `TimingWindowChips` w centrum decyzji (chip „Window”, po zamknięciu chwilowo „Closed”), `useOpenWindows`,
  `timingWindows.ts` (cykl życia, test). `HandReactionRows`: karta z ręki, której okno minęło niezagrane, daje
  prywatny komunikat „Window closed”.
- Katalog wszystkich okien: `OKNA_CZASOWE.md` (67 zdarzeń, §2a: lista komponentów bez efektu w silniku).
- QA: pytest pełny, ruff, mypy; front tsc + eslint + vitest `domains/offers`, `domains/battle`; build; e2e 7/7.

## Okna czasowe: tylko istotne, jeden chip; Black Market Dealings tylko w negocjacji (2026-11-15)

- Zgłoszenie: na starcie tury Hacanu 3 chipy okien naraz, a Black Market Dealings dało się zagrać bez transakcji.
- `reactions_misc.transactions`: okno TRANSACTION/WHEN tylko przy otwartym stole transakcji (`transaction_tables`),
  podmiot = opener, `partner` = druga strona; `_can_negotiate` = gracz jest stroną stołu. RULES.md 53.5.e.
- `timing_view.live_points`: pasek pokazuje okno tylko, gdy reaguje na nie karta akcji spoza stosu odrzuconych
  (talia + ręce razem) albo notka z ręki, z efektem w silniku (`promissory_play.reaction_points`). RULES.md 54.9.
- Front: `TimingWindowChips` = jeden chip „Windows · N open · M closed”, lista (co zamyka okno) po kliknięciu.
- QA: pytest pełny, ruff, mypy; front tsc + eslint + vitest `domains/offers`.

## Okna na małych monitorach: sloty HUD; dossier systemu bez Battle calc, Edit tylko host (2026-11-15)

- Zgłoszenie: na małych ekranach okna się nakładają (karta strategii chowała się pod ręką przy 1366x768), agenda
  przewija się ciężko; w oknie systemu (prawy klik) „Edit board” widzą wszyscy, a „Battle calc” to artefakt AsyncTI4.
- `hooks/useHudMetric.ts`: panel w domyślnym miejscu publikuje wymiar jako zmienną CSS (`--hud-gsp-bottom`,
  `--hud-left-w`, `--hud-right-w`; ręka już miała `--hand-dock-clear`), sąsiedzi liczą z niej miejsce startowe.
  Przesunięty panel zwalnia slot. `useDraggablePanel` zwraca `el` i `isMoved`.
- Ręka stoi w wolnym pasie między dokiem akcji taktycznej a kartą strategii; dok taktyczny kończy się pod panelem
  stanu gry; StatusPhasePanel i MoveRouteBox nad ręką; MoveRouteBox obok centrum decyzji (`data-hud-slot`).
- Niski ekran (`max-height: 900px`): mniejsza ręka i kafelki kart, mniejsza karta strategii, ciaśniejsze przyciski.
- Agenda: bez `backdrop-filter` na przewijanych panelach (przeliczanie blur przy przewijaniu), ciaśniej przy niskim ekranie.
- Dossier: usunięte linki ti4battle.com (`battleCalcLink.ts` → `attacker.ts` z samym `findAttacker`, pasek przewagi
  zostaje); „Edit board” tylko dla hosta (`useIsHost` w `useNetworkMe.ts`).
- QA: front tsc + eslint + vitest `game-shell`, `map`, `offers`, `agenda`, `hooks`; zrzuty 1280/1366/1920 na żywej grze.
  Pominięte: backend (bez zmian), build i e2e.

## Audyt okien kart akcji: Coup d'Etat, Veto (2026-11-15)

- Coup d'Etat: okno dopiero po ogłoszeniu akcji strategicznej (`pending_strategy` na pierwszym kroku, pusty szkic),
  nie na początku cudzej tury. Efekt anuluje primary, odświeża kartę (`exhaust.ready_strategy_card`), oddaje akcję
  (`action_budget.unregister_action`) i kończy turę. `reactions_stop.declared_strategic_action`. RULES.md 53.7.
- Veto / Diplomatic Pressure: okno „when revealed” zamyka się po pierwszej karcie „after revealed” (ridery…)
  — `AgendaPhaseState.after_reveal_played`, `agenda_phase.note_reaction_played`. RULES.md 53.5.a.
- Audyt 107 kart akcji vs `C_action_cards.md`: pozostałe okna zgodne; luki do decyzji: Emergency Repairs (brak „end of
  round” i Space Cannon Offense), Direct Hit (brak okna Sustain Damage poza walką), HOLD tylko dla 4 kart.
- QA: pytest pełny, ruff, mypy. Front bez zmian.

## Dźwięk: cichszy, krzywa słuchu, bez toggle.ogg (2026-11-15)

- `shared/audio/audioSettings.ts`: `channelVolume` = krzywa kwadratowa suwaków (50 ≈ -12 dB) × stałe
  ściszenie kanałów `CHANNEL_TRIM` (UI 0.35, muzyka/efekty 0.6, głosy 0.8); niższe wartości domyślne.
- `uiSounds.ts`: przełączniki/checkboxy grają cichy `tick` zamiast `toggle` (plik `toggle.ogg` usunięty).
- Muzyka: wystarczy podmienić pliki w `assets/music/` i odświeżyć stronę (manifest czytany na żądanie).

## Pauza ochronna 10 s w kluczowych oknach + Emergency Repairs + Direct Hit poza walką (2026-11-15)

- `core/reaction_pause.py` (RULES.md 54.10): `GameState.reaction_pause` otwierane w `state_service.replace_state` po kroku
  gry w oknach: ogłoszona akcja strategiczna (Coup), ujawniona agenda, wygrana walka, Sustain Damage. Uprawnieni z
  informacji jawnej (`timing_view.live_relations` + liczba kart w ręce). Bramka `timing.require_no_reaction_pause` w
  `submit_primary_step`, `cast_vote`/`abstain`, krokach walki i Space Cannon. `POST /reaction-pause/pass|release`,
  middleware zwalnia przeterminowaną pauzę wg zegara serwera. Kontrakt `reactionPause` w web-data.
- Front: `ReactionPauseBanner` (wygląd i odliczanie jak okno Sabotage, „Pass”), „Close battle” wyłączony w pauzie.
- Emergency Repairs: okna koniec ostatniej rundy (`COMBAT_ROUND/END`) i Space Cannon Offense. Direct Hit: ślad
  `sustain_trace` po Sustain Damage w Space Cannon Offense. RULES.md 53.5.c.
- Testy: `test_reaction_pause.py`, nowe w `test_reactions_combat.py` / `test_reactions_invasion.py`; harness scenariuszy
  pasuje w pauzie (`Flow.pass_reactions`). `ReactionPauseBanner.test.tsx`.
- QA: pytest pełny, ruff, mypy; front tsc + eslint + vitest (BottomHandDock, battle, offers); build; e2e.

## Centrum decyzji: stały kształt chipów „Ready”/„Timing windows”, zawsze widoczny uchwyt (2026-11-15)

- Zgłoszenie: chipy aktywnych zdolności (np. bohater Letnev) nachodziły na siebie, a panel okien czasowych
  ciężko się przesuwał i po rozwinięciu zmieniał kształt.
- `AbilityPrompts.module.css`: chip na pełną szerokość kolumny, stały promień (bez pigułka → prostokąt), rozwinięty
  tekst z własnym przewijaniem (max 128 px); etykieta w dwóch liniach (`chipLabel`/`chipMeta`: „Ready · Hero · gracz”
  nad nazwą). Przezroczysta reszta kolumny nie łapie kliknięć nad mapą (`pointer-events`). Bez `resize: horizontal`.
- Pasek „Decisions” z uchwytem jest zawsze (wcześniej znikał przy samych chipach — zostawał wąski skrawek do chwycenia).
- QA: front tsc + eslint + vitest `domains/offers`; zrzut na tymczasowej stronie testowej (serwery gry były wyłączone).
  Pominięte: backend (bez zmian), build, e2e.

## HOLD dla wszystkich kart reakcji (2026-11-15)

- `reaction_cards.is_rewindable(registry, karta)`: każda karta akcji z oknem innym niż ACTION (poza Sabotage) jest
  zagrywalna przez hold-rewind — przycisk HOLD (`/hold/candidates`) i „Play now” w doku po kroku, który zamknął okno
  (`just_passed` → `hold_seq`). Wcześniej tylko Public Disgrace, Coup d'Etat, Political Stability, Crash Landing.
- Zakaz oszustwa (kości, talie, faza, zagrania kart, 8 kroków) bez zmian. RULES.md 53.7.
- Testy: `tests/test_hold_rewind.py` (zakres kart, Counterstroke po ruchu rywala przez HOLD).

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
