# Bot AI — audyt silnika i plan pracy (krótkie branche)

Status: B0 (fundament) zrobione 2026-11-16, reszta PLAN. Etap 3 projektu (`docs/README.md` §1).
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
| Decyzje „za bota” w `core/` | ⚠️ | `core/transaction.bot_accepts`, `core/epilogue._bot_choice`, `core/transaction_table` | Placeholdery decyzji w warstwie reguł. Przenieść do `src/engine/` (B10). |
| **Katalog akcji** | ❌ | 131 endpointów POST w `api/routers/` | Brak jednego typu „akcja gracza”. Routery są cienkie (actor → `core/` → commit), mapowanie proste, ale do zbudowania. **Główna luka.** |
| **Generator legalnych ruchów** | 🟡 | `action_cards.playability`, `offers.offer_view` (inputs), `research_offer`, `movement_route`, `strategy_phase` | Częściowe enumeratory per obszar; brak „wypisz legalne ruchy gracza X teraz”. |
| **Wyzwalacz bota** | ❌ | — | Nikt nie uruchamia bota, gdy `awaiting` wskazuje gracza `BOT`. |
| **Infrastruktura obliczeń** | ❌ | — | Brak interfejsu algorytmu, procesów roboczych, budżetu czasu, unieważniania nieaktualnych wyników. |
| Współbieżność | ⬜ | N4 w `PLAN_PELNA_ROZGRYWKA.md` | Brak blokady na grę; runner bota musi serializować się z żądaniami ludzi. |
| Czas | ✅ | `core/game_clock.py`, `create_app(now=...)` | Wstrzykiwany `now` — także dla budżetu bota. |
| Feed Activity | ✅ | `core/activity.py` | Ruchy bota widoczne jak ruchy człowieka; etykiety commitów `bot:<kind>`. |
| Sprzęt / środowisko | ℹ️ | maszyna hosta | Python 3.14, 12 rdzeni logicznych, NumPy ≥ 2.5. Brak Numby (i niepewne wsparcie 3.14) — decyzja o zależnościach w B6. |

---

## 3. Algorytmy (katalog — do uzupełnienia przez użytkownika)

Każdy algorytm to osobny moduł z własnym branchem `bot/alg-<nazwa>`, testami i wynikiem w arenie.
Lista startowa ze specyfikacji; **użytkownik dopisze własne algorytmy** (§6, pytanie 1).

| Algorytm (roboczo) | Warstwa | Decyzje | Charakter obliczeń |
|---|---|---|---|
| Ocena celów (`objective_evaluator`) | strategiczna | wybór celów, karty strategii, wydatki | heurystyka, tania |
| Symulator walki Monte Carlo | taktyczna | czy atakować, ile wysłać, przypisanie trafień | tysiące rzutów; wektoryzacja NumPy |
| Planer ruchu / ekspansji | operacyjna | aktywacja, trasy, produkcja | przeszukiwanie grafu + ocena |
| (IS)MCTS dla akcji w turze | operacyjna/taktyczna | wybór akcji z determinizacją ukrytych informacji | ciężkie; wymaga szybkiego stanu (B6) |
| Głosowanie w agendzie | dyplomacja | głosy, wybór wyniku | ocena wpływu na wektor stanu |
| Ocena transakcji | dyplomacja | przyjęcie / oferta | heurystyka |

---

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
| ⬜ `bot/b1-katalog-akcji` | `Action` + `apply` dla decyzji „nie blokuj gry”: tajny cel, Custodians/odkrycie celów, wybór karty strategii, pas / koniec tury, pas w oknie, odmowa „may”, pominięcie secondary, przypisanie trafień, głos w agendzie, kroki statusu, odrzut nad limit ręki. `legal_actions` dla tych powodów. | Test zgodności katalog ↔ HTTP dla każdej akcji; strażnik „engine nie importuje api”. |
| ⬜ `bot/b2-obliczenia` | `engine/compute`: `DecisionRequest/Result`, `Algorithm`, `Executor` inline + process, termin i wynik anytime, unieważnianie po `state_seq`, rejestr z `engine_config.json`, algorytm „domyślny” (bezpieczny ruch). `engine/bench.py`. | Ten sam request inline i w procesie → ta sama decyzja; przekroczenie terminu → ruch domyślny; serwer odpowiada w trakcie liczenia. |
| ⬜ `bot/b3-runner` | `api/bot_runner.py`: wyzwalacz po commicie, kolejka na grę, opóźnienie z ustawień (admin fast = 0), etykiety `bot:*`, Activity, odrzucanie wyników po Undo człowieka. | Partia 1 człowiek + 5 botów przechodzi pełne rundy bez zawieszenia (test API). |
| ⬜ `bot/b4-arena` | `python -m src.engine.arena`: gry bez UI, turnieje algorytmów na wspólnych ziarnach, raport (wygrane, VP, czas/ruch). Smoke w `tests/engine/`. | Arena z ziarnem deterministyczna (tryb inline); 422 na legalnym ruchu kończy grę raportem. |
| ⬜ `bot/b5-legalne-ruchy` | Generatory akcji taktycznej (aktywacja, ruch, produkcja, inwazja), primary/secondary, badań, akcji komponentu; brakujące enumeratory w `core/`. | Bot losowy gra w arenie 10 rund bez 422. |
| ⬜ `bot/b6-szybki-stan` | `engine/fast`: szybka reprezentacja i symulator kroków potrzebnych algorytmom (najpierw walka); test zgodności z `core/`; decyzja o Numbie/akceleracji po pomiarze. | Cel wydajności z pomiaru (np. symulacji walki/s) zapisany w tym planie; zgodność 100% na próbie losowej. |
| ⬜ `bot/alg-*` | Każdy algorytm z §3 osobno: moduł + testy + konfiguracja + wynik w arenie wobec poprzedniej wersji bota. | Algorytm wygrywa (lub nie przegrywa) w arenie z wersją bez niego; mieści się w budżecie. |
| ⬜ `bot/b10-dyplomacja-core` | Przeniesienie `bot_accepts` i `_bot_choice` z `core/` do `engine/` (core pyta, engine odpowiada). | `core/` nie zawiera decyzji bota. |
| ⬜ `bot/b11-trudnosc` | Poziomy i osobowości = zestawy algorytmów + parametrów + budżetów w `engine_config.json`; reakcje w oknach. | Różnice poziomów mierzalne w arenie. |

Zależności: B3 wymaga prostej serializacji na grę (fragment N4). Od B5 każda nowa mechanika silnika
powinna od razu dostać wpis w `legal_actions` (strażnik do rozważenia w B5).

---

## 6. Decyzje użytkownika (otwarte)

1. **Jakie algorytmy** chcesz wprowadzić (nazwy / podejścia: MCTS, minimax, sieci neuronowe, programowanie
   liniowe…)? Od tego zależy, czy B6 potrzebuje NumPy, Numby, czy np. PyTorcha (lokalne GPU?).
2. Bot w procesie serwera + procesy robocze (rekomendacja) czy osobny klient sieciowy?
3. Budżet czasu na decyzję (np. 2 s zwykła / 10 s kluczowa) i ile rdzeni oddać botom?
4. Tempo bota „dla oka”: opóźnienie 1–2 s między ruchami (admin fast = 0)?
5. Undo: bot nigdy nie cofa; po Undo człowieka liczy od nowa (rekomendacja) — potwierdź.
6. Przejęcie nieobecnego człowieka przez bota (RULES 44.5) — w którym etapie?
