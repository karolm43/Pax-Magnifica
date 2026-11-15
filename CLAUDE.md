# Custodian Engine — zasady projektu (Claude Code)

Lokalny silnik **Twilight Imperium 4**, cel: autonomiczny bot-przeciwnik. Etapy: (1) plansza + God-Mode (gotowe),
(2) silnik egzekwujący reguły (w toku), (3) bot AI. Gra sieciowa (ludzie + boty); solo z botami to szczególny przypadek;
hot-seat NIE jest wspierany. Nie czytaj `.kiro/` ani `~/.kiro/` (decyzja użytkownika) — wiedza jest w pamięci Claude.

## Kontekst (najważniejsze)

- Start: `docs/README.md` (indeks). NIGDY w całości: `docs/PROGRESS_ARCHIWUM.md`, `docs/OKNA_CZASOWE.md`,
  `docs/rules_tirules/tirules.json`, `docs/RULES.md` — tylko grep/offset.
- `docs/PROGRESS.md` (~35 KB) punktowo po temacie. `docs/RULES.md` to INDEKS; sekcja N = `docs/rules/R<NN>.md`.
- `docs/POKRYCIE_HOOKOW.md` (~10 KB) można czytać; szczegóły w `docs/pokrycie_hookow/*.md` punktowo.
- `docs/rules_tirules/` — małe pliki tematyczne, indeks `INDEX.md`.
- Kod `src/` i testy `tests/` są nadrzędnym źródłem prawdy. Zadanie frontendowe: nie ruszaj dokumentów reguł.

## Spójność i reużycie (decyzja użytkownika)

- Zanim zbudujesz element UI, znajdź istniejący odpowiednik (panel gracza, ręka, feed Activity, okno bitwy) i UŻYJ go.
  Np. notki w transakcji = chip `PromissoryNote` (ikona wystawcy, opis po kliknięciu), nie własna lista.
- Ten sam obiekt gry = ten sam komponent wszędzie (chip + opis po kliknięciu, `Unit`, `describeActivity`, pełne nazwy z danych).
- Coś odstaje (własne style, surowe id, zdublowany komponent) — ujednolić przy okazji albo zgłoś.

## Reguły TI4 (KLUCZOWE)

- Nie koduj reguł ani statystyk z pamięci. Liczby i teksty kart tylko z assetów AsyncTI4 (`StaticDataRegistry`, `assets/`).
- Źródło reguł: `docs/rules_tirules/` (zrzut tirules2.com: LRR 2.0 PoK + Codexy + Thunder's Edge + rulingi). Zdolności
  frakcji/kart są w assetach JSON. Gdy zrzut nie wystarcza: tirules2.com, potem LRR PDF / TI Wiki.
- ZAWSZE (implementacja i przegląd) sprawdź rulingi z `docs/rules_tirules/`: karta/komponent ogólny =>
  `C_<typ>.md` (`C_agendas`, `C_action_cards`, `C_technology`, `C_relics`, `C_objectives`, `C_promissory_notes`,
  `C_units`, `C_exploration_cards`…); komponent frakcji (zdolność, tech, lider, mech, flagowiec, PN, przełom) =>
  `F_<frakcja>.md`; mechanika ogólna => `R_<temat>.md`. Szukaj też krzyżowo (ruling o frakcji w `C_*`, o karcie
  w `F_*`). Każdy ruling = kod albo test; `⚠️ ZAŁOŻENIE` sprzeczne z istniejącym rulingiem to błąd.
- Reguła mechaniczna musi mieć wpis w `docs/rules/R<NN>.md` ze źródłem, ZANIM trafi do kodu.
- Brak źródła => ⚠️ ZAŁOŻENIE i pytanie do użytkownika; jego decyzja jest ostateczna.
- Adjacency ≠ traversability: graf mapy = czyste sąsiedztwo, blokady to osobna warstwa.

## Silnik: SĘDZIA (RULES 29)

- Zwykłe akcje walidują legalność: nielegalne => `ValueError` => HTTP 422.
- God-Mode (`/god-mode/patch`, `core/board_edit.*`) CELOWO omija walidację.
- Okna czasowe (`GameState` + `core/timing.py`): gracze pytani po kolei od gracza po aktywnym. Reakcje when/after/instead:
  STOP z cofaniem + jednolita pauza (RULES 43.4).
- Walka pełna, interaktywna, seedowalny RNG. E1–E3 to fundament: dobudowuj, nie przepisuj. `src/engine/` = przyszła warstwa AI.
- Stan gry żyje tylko w pamięci backendu — restart kasuje grę. Nowe trasy/pola wymagają restartu: uprzedź użytkownika.
- Czas rzeczywisty: nigdy `time.time()` w `core/` — wstrzykuj `now` (wzór `core/game_clock.py`, `create_app(now=...)`).

## Architektura (zależności tylko w dół)

- `core/` — czyste funkcje `state -> state`, zero HTTP; jedyne źródło reguł.
- `api/routers/<temat>.py` — cienkie endpointy. Zmiana stanu: `actor: ActorId` + `core/actor.py` ALBO
  `dependencies=[HostOnly]` (RULES 44.1a; strażnik `tests/test_actor_guard.py`).
- Asymetria frakcji/tech/kart = hooki (`core/rules_hooks.py`, `core/hooks/`), NIE `if faction == ...`.
- Punkty centralne (RULES 43.1a): płatność, TG, żetony, exhaust, kontrola planet, jednostki, tech, VP — JEDNA funkcja
  w `core/`; wyjątki z komentarzem `HOOK-CANDIDATE`.
- Nowa mechanika: reguła w `rules/` => funkcja w `core/` + test => endpoint.
- Komponent używany przez gracza (oferta, „During X: you may…”, ACTION, notka) SAM wyskakuje w UI + scenariusz przez
  API (`tests/factions/test_flows_<frakcja>.py`, strażnik `test_flow_coverage.py`).
- Każdy widoczny skutek => feed Activity: `core/activity.py` + `ActivityPanel/describeActivity.tsx` + `tests/test_activity.py`.
- Assety w `assets/`; filtr po polu `source` w JSON; aktywne w `assets/enabled_sources.json` (Codexy MUSZĄ być włączone).
- Rozmiar pliku ~500 linii to miękka wskazówka.

## Kości i karty

- Każdy rzut w UI to fizyczny d10 (scena 3D), wynik liczy silnik. Poza walką: `dice.record_table_roll(...)` w `core/`;
  własne okno: `HoldRollButton` + `soloHold` + `useDiceStage().throwDice`. Bez własnych animacji. Przepis: `ARCHITEKTURA_KODU.md` §3a.1.
- Cel: KOMPLET kart. Pipeline `ARCHITEKTURA_KODU.md` §3a (RULES => `register_effect` => `register_effect_inputs` =>
  zagrywalność => test => raport). Karta zagrywana PRZECIĄGNIĘCIEM z ręki; podnieść można tylko legalną
  (`action_cards.playability`). Postęp: `POKRYCIE_HOOKOW.md`.

## Stack

Python >=3.12 + `uv`, Pydantic v2, NumPy, networkx. Front: React 19 + Vite + TS + Zustand + react-query, design system
`frontend/src/ds/`. Ikony jednostek w małym pudełku: kontener ustawia `--unit-fit: <rozmiar>` (`shared/ui/Unit/unitSprites.css`),
nie stałe `width/height` na `.unit-sprite`. Lokatory testów po rolach ARIA (`getByRole`).

## Workflow i QA

- Blok pracy = kod + testy + krótka nowa sekcja na końcu `docs/PROGRESS.md` + commit (po polsku, konkretne pliki,
  bez `git add .`, bez `git push` bez zgody). Komentarze/docstringi/dokumentacja po polsku.
- Równoległa sesja może pracować w repo: przed commitem `git status`, staguj WYŁĄCZNIE własne hunki.
- QA dobieraj do zakresu (pełny zestaw ~5 min — nie „na wszelki wypadek”); pominięte kroki wymień w raporcie:
  - Backend: `uv run pytest -q -n auto` ; `uv run ruff check src tests` ; `uv run mypy src tests`.
    W trakcie: `uv run pytest -q --testmon`. Zmiana tylko frontu => bez QA backendu.
  - Front zawsze (w `frontend/`): `npx tsc --noEmit -p tsconfig.app.json` (`npm run type-check` NIE sprawdza `src/`) ;
    `npx eslint <zmienione>` ; `npx vitest --run <folder>`.
  - `npm run build` (~2 min): raz przed commitem, gdy zmieniły się importy/zależności, Vite, assety lub nowe moduły.
  - `npm run e2e` (~3 min, własne serwery :8100/:5273, gra na :8000 nietknięta): tylko po zmianie kreatora/lobby/setupu,
    przepływu gry albo komponentu montowanego zawsze na stronie gry.
- Python w Git Bash zapisuje cp1252 — przy edycji skryptem podawaj `encoding="utf-8"`.
