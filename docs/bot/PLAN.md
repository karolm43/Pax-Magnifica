# Bot AI — audyt silnika i plan pracy (krótkie branche)

Status (2026-11-16): B0, B1, B3 zrobione, B2 — rdzeń; reszta PLAN. Etap 3 projektu (`docs/README.md` §1).
Zasady projektowe bota: `docs/rules/R65.md`. Instrukcje dla Claude: `src/engine/CLAUDE.md`.
Wizja warstw (strategiczna / operacyjna / taktyczna / dyplomacja): `specyfikacja_techniczna_i_architektura_systemu.md` §4.
Ten plik jest ŻYWY: po każdym bloku bota aktualizuj tabele w §2 i §5.

**Decyzja użytkownika (2026-11-16):** bot będzie używał kilku osobnych, złożonych algorytmów
obliczeniowych, liczonych LOKALNIE (na maszynie hosta, bez chmury). Architektura (§4) musi to udźwignąć
od początku: wspólny interfejs algorytmu, osobne procesy, budżet czasu, porównywanie algorytmów w arenie.

---

## 1. Zasady (skrót; pełne w `docs/rules/R65.md`)

1. **Bot gra tą samą ścieżką reguł co człowiek** — każdy ruch przez funkcje `core/` (Sędzia, RULES 29).
2. **Bot nie oszukuje** — decyduje na `visibility.project_strict(state, bot_id)`; ukryte informacje losuje.
3. **Gra nigdy nie czeka na bota w nieskończoność** — budżet czasu + bezpieczny ruch domyślny.
4. **Algorytm = wymienny moduł** za jednym interfejsem; który algorytm do której decyzji — w konfiguracji.
5. **Ciężkie liczenie poza pętlą serwera** — procesy robocze; serwer gry nigdy nie zamarza.
6. **Determinizm** — ta sama projekcja + to samo ziarno + ten sam budżet iteracji = ta sama decyzja.

---

## 2. Audyt: co silnik już daje botowi (stan 2026-11-16)

| Potrzeba bota | Stan | Gdzie | Uwagi / co dodać |
|---|---|---|---|
| Kto ma teraz ruch i jaki | ✅ | `core/actor.awaiting(state)` | Kody `respond/decide/assign_hits/combat/invasion/explore/strategy/turn/speaker/secret/setup` — gotowy „dyspozytor” bota. |
| Uprawnienia aktora | ✅ | `core/actor.require/subject` | Bot działa jako `actor_id = swój player_id`; te same 403 co człowiek. |
| Widok bez oszustwa | ✅ | `core/visibility.project_strict` | Ukrywa ręce, tajne cele, `rng_seed`. |
| Seedowalny RNG | ✅ | `core/dice.roll_dice/next_rng` | Ziarno + licznik w stanie. Projekcja ma `rng_seed=0` → w symulacji ziarno ustawia algorytm (inaczej `secrets` = niedeterminizm). |
| Klonowanie stanu | 🟡 | `GameState.clone()` | Pomiar: **0,40 ms** (6 graczy, runda 2, ~23 KB JSON; `model_copy(deep)` 0,78 ms, `deepcopy` 0,60 ms). Wystarcza na heurystyki i płytki lookahead; dla Monte Carlo / MCTS z tysiącami symulacji za wolno → szybka reprezentacja (B6). |
| Mapa | 🟡 | `core/hex_grid.HexGrid` | Topologia POZA `GameState` (jednostki są w stanie). Symulacja potrzebuje pary `(state, grid)`; grid do procesu roboczego jako `to_placements()`. |
| Ustawienia bota | ✅ | `PlayerState.control_type/difficulty/personality`, `assets/config/engine_config.json` | Wartości to ⚠️ ZAŁOŻENIE. |
| Decyzje „za bota” w `core/` | ⚠️ | `core/transaction.bot_accepts`, `core/epilogue._bot_choice`, `core/transaction_table`, `core/game_setup.begin_setup` (losowy tajny cel bota), auto-pas botów w oknach reakcji (`core/reaction_window`) | Placeholdery decyzji w warstwie reguł. Przenieść do `src/engine/` (B10). Auto-pas w oknach reakcji może zostać (silnik zna ręce; pas za „nic do zagrania” dotyczy też ludzi). |
| Katalog akcji | 🟡 B1 | `src/engine/actions.py` | 29 rodzajów (setup, strategia z krokami primary, tura, okna, oferty, przypisanie trafień, status, agenda, ogłoszenia mówcy, limit ręki, okna o stałej długości). `apply_and_settle` = akcja + `core/step_settle` (dokładnie jak commit). Ruch, produkcja, inwazja, karty akcji: B5. |
| Generator legalnych ruchów | 🟡 B1 | `src/engine/legal.py` + `src/engine/observation.py` | Zakres B1 (bez własnej akcji taktycznej); pierwszy kandydat = bezpieczny ruch domyślny. Obserwacja = ścisła projekcja + własne monity (`step_options`, `offers_view`), czyli to samo, co dostaje klient człowieka. |
| Wyzwalacz bota | ✅ B3 | `src/api/bot_runner.py` | Pętla w lifespan serwera, budzona po broadcast i co 1 s; pyta `legal_actions` KAŻDEGO bota (decyzje równoległe). Ruch = to samo żądanie HTTP co człowieka (`api/bot_http.py`, ASGI w procesie). `--no-bots` wyłącza. Brak: przełącznik admin fast (opóźnienie 0) z UI. |
| Logika reguł poza `core/` | ✅ B1 | `core/phase_flow.py`, `core/step_settle.py` | Znalezione w B1 i przeniesione do `core/`: wybór domknięcia fazy w routerze `/phase/next` (+ `/round/next`) oraz reguły „po każdym kroku” w `StateService.replace_state`. Middleware zwalniający przeterminowaną pauzę przed każdym POST zostaje w `api/` (bot ma akcję `reaction_pause_release`). |
| Determinizm | ✅ B1 | `core/game_setup` | Błąd znaleziony testem zgodności: wybór tajnego celu tasował niezasianym `random.Random()`, teraz `next_rng(stan)`. Tworzenie gry nadal z entropii (start partii). |
| Okna czasowe a bot | ✅ | `engine/legal._window` | Usunięta ogólna odpowiedź `/window/respond` (+ akcja `window_respond`): omijała obowiązkową decyzję okna i nie zamykała dopełnionego okna (gra stawała). W oknie `COMBAT_ASSIGN_HITS` bot dostaje teraz `battle_assign` (wcześniej ogólne „OK” = pominięte straty). SPACE_CANNON / COMBAT_RETREAT / CAPACITY / FLEET_POOL: brak ruchu bota do B5 (`tests/engine/test_legal_windows.py`). |
| Infrastruktura obliczeń | 🟡 B2 | `src/engine/compute.py`, `BotConfig` w `engine_config.json` | `DecisionRequest/Result`, rejestr algorytmów (`first`, `random`), `Executor` inline/process z terminem i ruchem domyślnym, unieważnianie po `state_seq` (runner). Brak: `bench.py`, wynik „anytime” z procesu (dziś po terminie tylko ruch domyślny), inicjalizacja rejestru danych w procesie roboczym. |
| Współbieżność | ⬜ | N4 w `PLAN_PELNA_ROZGRYWKA.md` | Brak blokady na grę; runner bota musi serializować się z żądaniami ludzi. |
| Czas | ✅ | `core/game_clock.py`, `create_app(now=...)` | Wstrzykiwany `now` — także dla budżetu bota. |
| Feed Activity | ✅ | `core/activity.py` | Ruchy bota widoczne jak ruchy człowieka; etykiety commitów `bot:<kind>`. |
| Sprzęt / środowisko | ℹ️ | maszyna hosta | Python 3.14, 12 rdzeni logicznych, NumPy ≥ 2.5. Brak Numby (i niepewne wsparcie 3.14) — decyzja o zależnościach w B6. |

---

## 3. Algorytmy — architektura 4 warstw (wizja użytkownika 2026-11-16)

Każdy algorytm to osobny moduł z własnym branchem `bot/alg-<nazwa>`, testami i wynikiem w arenie,
zarejestrowany w `engine/compute` (`register_algorithm`) i przypisany w `engine_config.json`.
Bez sieci neuronowych, PyTorcha i GPU (RL/self-play wymagałby pełnego szybkiego symulatora całego TI4).
LLM do czatu/negocjacji — ewentualnie na samym końcu, poza logiką gry.

| Warstwa | Algorytmy | Decyzje | Biblioteki (⚠️ zależność = zgoda + pomiar w `bench.py`) |
|---|---|---|---|
| 1. Strategiczna (VP Solver) | MIP/ILP, CP-SAT | które planety wyczerpać (zasoby/wpływy) pod cele; produkcja jako plecak (siła floty w limicie zasobów i PRODUCTION) | Google OR-Tools |
| 2. Użyteczność i heurystyki | Utility AI (krzywe 0–1), mapy wpływu/zagrożenia, Monte Carlo walki | wartość każdej akcji wobec celów i odległości; szansa wygranej i straty przed atakiem (Sustain, AFB, modyfikatory) | NumPy (+ Numba `@njit`?) |
| 3. Operacyjna (kolejność w rundzie) | RHEA (krótkie sekwencje 4–6 makro-decyzji, mutacja/krzyżowanie) lub makro-ISMCTS | kiedy zagrać kartę strategii, kiedy spasować, kolejność aktywacji | własna pętla Python |
| 4. Taktyczna (logistyka) | graf + Dijkstra/A* na heksach | realny zasięg flot (anomalie, Gravity Drive, Antimass, wormhole) | NetworkX / NumPy |
| (dyplomacja) | heurystyki | głosy w agendzie, transakcje | — |

**Uwagi Claude do wizji (do decyzji przy danym branchu):**
1. **Warstwa 4 nie może liczyć zasięgu sama.** Ruch ma pełne reguły w `core/movement` (anomalie, technologie,
   frakcje, blokady). Dijkstra/A* liczy po grafie zbudowanym z enumeratora `core/` („dokąd ten statek
   legalnie doleci”), a nie po własnej kopii reguł — inaczej bot i Sędzia będą się rozjeżdżać. Pierwszy krok
   B5: taki enumerator w `core/`.
2. **Monte Carlo walki = osobny, szybki symulator z obowiązkowym testem zgodności z `core/battle`**
   (rozkład wyników na tych samych ziarnach/próbie). Numba: niepewne wsparcie Pythona 3.14 na tej maszynie —
   najpierw sama wektoryzacja NumPy (10 000 bitew < 50 ms jest realne bez Numby), Numba tylko po pomiarze.
3. **OR-Tools to ciężka zależność** (natywne koła, wsparcie 3.14 do sprawdzenia). Problemy płatności i
   produkcji są małe (kilkanaście planet, kilka typów jednostek) — dokładne programowanie dynamiczne /
   przegląd zupełny w czystym Pythonie daje optimum w milisekundach. Propozycja: zacząć od DP, OR-Tools
   wprowadzić, gdy pojawi się problem, którego DP nie udźwignie (np. łączny plan rundy).
4. **Wspólna funkcja oceny stanu** (warstwa 2) jest fundamentem dla warstw 1 i 3: RHEA/ISMCTS bez dobrej
   oceny liści gra losowo. Kolejność: ocena + Monte Carlo walki → enumerator ruchu → RHEA.
5. **RHEA/ISMCTS potrzebują szybkiego modelu do przodu** (`engine/fast`, B6) — `GameState.clone()` 0,4 ms
   pozwala na ~2 500 kroków/s na rdzeń; na makro-poziomie (4–6 decyzji) może wystarczyć bez B6. Zmierzyć.
6. **Brakuje modelu przeciwnika** (co zrobią inni w tej rundzie) — RHEA powinna symulować rywali choćby
   prostą polityką (bot „first”/utility), a ukryte karty losować z puli niewidocznych (determinizacja, 65.2).

## 4. Architektura docelowa

```text
                    ┌──────────────────────── proces serwera (FastAPI) ────────────────────────┐
 commit stanu ──►   │ api/bot_runner.py: awaiting ∋ BOT?                                      │
                    │   view = project_strict(state, bot)   legal = engine.legal_actions(...)  │
                    │   request = DecisionRequest(view, grid, legal, seed, budżet, state_seq)  │
                    │   ──► engine.compute.Executor ──┐                                         │
                    │   ◄── DecisionResult ───────────┤ (stary state_seq? => wynik odrzucony)   │
                    │   apply(action) przez core/ ──► commit „bot:<kind>” + Activity           │
                    └─────────────────────────────────┼────────────────────────────────────────┘
                                                      ▼
                         procesy robocze (ProcessPoolExecutor, N = rdzenie − 1)
                         initializer: StaticDataRegistry + tabele NumPy raz na proces
                         algorytm.decide(request) — anytime: najlepszy wynik do terminu
```

- **`src/engine/actions/`** — dyskryminowana unia `Action` (Pydantic) + `apply(state, grid, registry, action)`,
  wołające DOKŁADNIE te funkcje `core/`, które wołają routery. Jedno mapowanie: gra na żywo i symulacje.
- **`src/engine/legal.py`** — `legal_actions(view, grid, registry, player_id) -> list[Action]` dla bieżącego
  powodu z `awaiting`; brakujące enumeratory dopisujemy w `core/`.
- **`src/engine/compute/`** — infrastruktura obliczeń:
  - `DecisionRequest` / `DecisionResult` — serializowalne (picklable), z `state_seq`, ziarnem, budżetem
    (`deadline_ms` i/lub `max_iterations`), nazwą algorytmu i parametrami.
  - `Algorithm` (Protocol): `name`, `decide(request) -> DecisionResult`; funkcja modułowa (nie metoda
    obiektu z serwera), żeby dało się ją wysłać do procesu.
  - `Executor`: tryb `inline` (testy, arena deterministyczna) i `process` (gra na żywo, równoległe boty).
    Termin twardy: po przekroczeniu — ostatni wynik „anytime” albo ruch domyślny.
  - Rejestr algorytmów: `decyzja → algorytm + parametry` z `engine_config.json` (per poziom trudności/osobowość).
- **`src/engine/fast/`** (B6) — szybka reprezentacja stanu do symulacji (NumPy; Numba/inna akceleracja tylko
  po pomiarze i zgodzie użytkownika na zależność). Konwerter `GameState → FastState` + test zgodności
  wyników z `core/` na losowych pozycjach (szybki stan NIE może mieć innych reguł niż `core/`).
- **`src/engine/{strategic,operational,tactical,diplomacy}/`** — algorytmy (istniejące katalogi).
- **`src/api/bot_runner.py`** — wyzwalacz w procesie serwera, kolejka zadań na grę, opóźnienie „dla oka”.
- **`src/engine/arena.py`** — gry bez UI: bot kontra bot, turnieje algorytmów (A vs B na tych samych
  ziarnach i mapach), metryki: wygrane, VP, czas/ruch, iteracje/s. Też test regresji silnika.
- **`src/engine/bench.py`** — mikro-benchmarki (klon, symulacja walki, generator ruchów); poza `pytest -q`.

---

## 5. Krótkie branche (każdy 1–3 sesje, merge do `main` po zielonym QA)

Konwencja: `bot/<nr>-<temat>` (infrastruktura) i `bot/alg-<nazwa>` (algorytmy), zawsze z aktualnego `main`;
przed merge `git merge main` i QA. Zmiana w `core/` potrzebna botowi = osobny commit. Worktree tylko przy
równoległej sesji nad silnikiem.

| Branch | Zakres | DoD |
|---|---|---|
| ✅ `bot/b0-fundament` | Ten plan, `src/engine/CLAUDE.md`, `docs/rules/R65.md`, `ARCHITEKTURA_KODU.md` (`ai/`→`engine/`), indeks `docs/README.md`. | Dokumenty spójne; zero kodu. |
| ✅ `bot/b1-katalog-akcji` | `Action` + `apply` dla decyzji „nie blokuj gry”: tajny cel, Custodians/odkrycie celów, wybór karty strategii, pas / koniec tury, pas w oknie, odmowa „may”, pominięcie secondary, przypisanie trafień, głos w agendzie, kroki statusu, odrzut nad limit ręki. `legal_actions` dla tych powodów. | Test zgodności katalog ↔ HTTP dla każdej akcji; strażnik „engine nie importuje api”. **Wynik:** 3 scenariusze (6 botów; 6 botów + agenda; 4 „ludzi” + agenda) grają 2 pełne rundy bez zawieszenia, 0 rozjazdów z HTTP, 0 odrzuceń pierwszego kandydata; ten sam start + ziarno = ta sama partia. Niepokryte (lista `NOT_YET_COVERED` w `tests/engine/test_actions_parity.py`): `battle_assign`, `held_pass`, `held_release`, `offer_decline` → B5. |
| 🟡 `bot/b2-obliczenia` (rdzeń na `main` 2026-11-16) | `engine/compute`: `DecisionRequest/Result`, `Algorithm`, `Executor` inline + process, termin i wynik anytime, unieważnianie po `state_seq`, rejestr z `engine_config.json`, algorytm „domyślny” (bezpieczny ruch). `engine/bench.py`. | Ten sam request inline i w procesie → ta sama decyzja; przekroczenie terminu → ruch domyślny; serwer odpowiada w trakcie liczenia. |
| ✅ `bot/b3-runner` (na `main` 2026-11-16) | `api/bot_runner.py`: wyzwalacz po commicie, kolejka na grę, opóźnienie z ustawień (admin fast = 0), etykiety `bot:*`, Activity, odrzucanie wyników po Undo człowieka. | Partia 1 człowiek + 5 botów przechodzi pełne rundy bez zawieszenia (test API). |
| ⬜ `bot/b4-arena` | `python -m src.engine.arena`: gry bez UI, turnieje algorytmów na wspólnych ziarnach, raport (wygrane, VP, czas/ruch). Smoke w `tests/engine/`. | Arena z ziarnem deterministyczna (tryb inline); 422 na legalnym ruchu kończy grę raportem. |
| ⬜ `bot/b5-legalne-ruchy` | Generatory akcji taktycznej (aktywacja, ruch, produkcja, inwazja), prowadzenie walki (rzut, AFB, odwrót), secondary z wyborem, badań, akcji komponentu, kart akcji; brakujące enumeratory w `core/`; scenariusze pokrywające `NOT_YET_COVERED`. | Bot losowy gra w arenie 10 rund bez 422. |
| ⬜ `bot/b6-szybki-stan` | `engine/fast`: szybka reprezentacja i symulator kroków potrzebnych algorytmom (najpierw walka); test zgodności z `core/`; decyzja o Numbie/akceleracji po pomiarze. | Cel wydajności z pomiaru (np. symulacji walki/s) zapisany w tym planie; zgodność 100% na próbie losowej. |
| ⬜ `bot/alg-*` | Każdy algorytm z §3 osobno: moduł + testy + konfiguracja + wynik w arenie wobec poprzedniej wersji bota. | Algorytm wygrywa (lub nie przegrywa) w arenie z wersją bez niego; mieści się w budżecie. |
| ⬜ `bot/b10-dyplomacja-core` | Przeniesienie `bot_accepts`, `_bot_choice` i losowego tajnego celu bota (`begin_setup`) z `core/` do `engine/` (core pyta, engine odpowiada). | `core/` nie zawiera decyzji bota. |
| ⬜ `bot/b11-trudnosc` | Poziomy i osobowości = zestawy algorytmów + parametrów + budżetów w `engine_config.json`; reakcje w oknach. | Różnice poziomów mierzalne w arenie. |

Zależności: B3 wymaga prostej serializacji na grę (fragment N4). Od B5 każda nowa mechanika silnika
powinna od razu dostać wpis w `legal_actions` (strażnik do rozważenia w B5).

---

## 6. Decyzje użytkownika

Podjęte 2026-11-16 (szczegóły w `docs/rules/R65.md` 65.7):
1. Algorytmy: architektura 4 warstw (§3); bez sieci neuronowych i GPU.
2. Bot w procesie serwera + procesy robocze (rekomendacja przyjęta).
3. Budżet 2 s decyzja zwykła / 10 s kluczowa; rdzenie: maksymalnie (wszystkie poza jednym).
4. Tempo „dla oka” 1–2 s, admin fast = 0.
5. Bot nigdy nie cofa; po Undo człowieka liczy od nowa.
6. Przejęcie nieobecnego człowieka przez bota — na końcu prac.

Otwarte: zależności OR-Tools / Numba (§3, uwagi 2–3) — decyzja przy branchu algorytmu, po pomiarze.
