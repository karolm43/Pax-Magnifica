# src/engine/ — warstwa bota AI (instrukcje dla Claude Code)

Uzupełnia główny `CLAUDE.md` (wszystkie jego zasady obowiązują dalej). Na start sesji nad botem czytaj
`docs/bot/PLAN.md` (stan, branche, otwarte decyzje) i `docs/rules/R65.md` (zasady projektowe bota).
Po bloku aktualizuj tabele w `docs/bot/PLAN.md`.

## Granice warstwy

- Zależności: `api/` → `engine/` → `core/` → registry/assets. `engine/` NIGDY nie importuje `api/`
  (strażnik testem). `core/` nie wie, że bot istnieje.
- Bot NIE zmienia stanu sam. Każdy ruch to `Action` z `engine/actions`, stosowana przez te same funkcje `core/`,
  których używają routery. Nielegalny ruch = `ValueError` z `core/` = błąd bota lub generatora, nie „obejście”.
- Zakaz God-Mode (`core/board_edit.*`, `/god-mode/*`) i Undo w logice bota.
- Brakująca reguła lub enumerator legalnych ruchów => dopisz w `core/` (z wpisem w `docs/rules/` i testem),
  nie odtwarzaj reguły w `engine/`.

## Uczciwość

- Decyzje tylko na `visibility.project_strict(state, bot_id)`. Nigdy nie podawaj botowi pełnego `GameState`.
- Symulacje na kopii z WŁASNYM ziarnem RNG; ukryte informacje przeciwników losuj (determinizacja)
  z puli niewidocznych kart, nie czytaj ich ze stanu.

## Algorytmy i obliczenia (decyzja użytkownika: kilka złożonych algorytmów, liczone lokalnie)

- Każdy algorytm = osobny moduł za interfejsem `DecisionRequest → DecisionResult` (`engine/compute`), funkcja
  modułowa i dane picklable, żeby działała w procesie roboczym. Osobny branch `bot/alg-<nazwa>` na algorytm.
- Ciężkie liczenie nigdy w pętli zdarzeń serwera: `Executor` w trybie `process`; tryb `inline` dla testów i areny.
- Każda decyzja ma budżet (termin i/lub limit iteracji) i ruch domyślny; algorytmy są „anytime”.
- Wynik dla nieaktualnego `state_seq` jest odrzucany.
- Szybka reprezentacja stanu (`engine/fast`) nie ma własnych reguł: test zgodności z `core/` jest obowiązkowy.
- Nowa zależność (Numba, PyTorch…) tylko za zgodą użytkownika i po pomiarze w `engine/bench.py`.
- Przypisanie „decyzja → algorytm + parametry + budżet” w `assets/config/engine_config.json`, nie w kodzie.

## Determinizm i czas

- Ziarno i termin przychodzą z zewnątrz; zero `time.time()`, `secrets` i `random` bez ziarna w `engine/`.
- Testy i arena używają limitu iteracji (nie milisekund) — wtedy decyzja jest powtarzalna.

## Reguły TI4 a decyzje bota

- Zasady gry: jak w głównym `CLAUDE.md` (assety, `docs/rules_tirules/`, nic z pamięci).
- Heurystyki, wagi, poziomy trudności i osobowości to ⚠️ ZAŁOŻENIA projektowe — opisuj je w `docs/rules/R65.md`.
- Asymetria frakcji przez oferty/hooki i katalog akcji, nie `if faction == ...`.

## Testy i QA

- Każda nowa `Action`: test zgodności z odpowiadającym endpointem HTTP (ten sam stan wynikowy).
- Każdy nowy typ decyzji: ruch domyślny + test, że gra z samymi botami nie staje.
- Każdy algorytm: testy jednostkowe + wynik w arenie wobec poprzedniej wersji bota (zapis w `docs/bot/PLAN.md`).
- Testy w `tests/engine/`; benchmarki poza `pytest -q` (`python -m src.engine.bench`).
- QA backendu jak w głównym `CLAUDE.md`; front tylko gdy blok go dotyka.

## Branche

- `bot/<nr>-<temat>` (infrastruktura) i `bot/alg-<nazwa>` (algorytmy) z aktualnego `main`, krótko żyjące,
  merge po zielonym QA. Zmiany w `core/` potrzebne botowi = osobny commit.
