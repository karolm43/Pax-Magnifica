# Custodian Engine — zasady projektu (steering)

Wczytywany w każdej sesji, więc trzymany krótko. Szczegóły: `docs/README.md`,
`docs/ARCHITEKTURA_KODU.md`, `docs/PLAN_PELNA_ROZGRYWKA.md`.

## Projekt

Lokalny silnik **Twilight Imperium 4** z celem: autonomiczny bot-przeciwnik. Etapy: (1) plansza + God-Mode
(gotowe), (2) silnik rozgrywki egzekwujący reguły (w toku), (3) bot AI. Tryb: gra sieciowa (ludzie + boty);
solo z botami to szczególny przypadek; hot-seat NIE jest wspierany.

## OSZCZĘDZANIE KONTEKSTU (najważniejsze)

NIGDY nie czytaj w całości: `docs/PROGRESS_ARCHIWUM.md`, `docs/POKRYCIE_HOOKOW.md`, `docs/OKNA_CZASOWE.md`
(generowane, po 100–190 KB), `docs/rules_tirules/tirules.json`, `docs/RULES.md` jako całości. Zawsze grep/offset.
- Start: tylko `docs/README.md`. Dalej punktowo:
  - `docs/PROGRESS.md` (~35 KB): szukaj sekcji po temacie.
  - `docs/RULES.md` to INDEKS; treść sekcji N jest w `docs/rules/R<NN>.md` (np. „RULES.md 43.1a” = `rules/R43.md`).
  - `docs/rules_tirules/` — małe pliki tematyczne (`R_*.md`, `F_*`, `C_*`), indeks `INDEX.md`.
- Kod w `src/` i testy w `tests/` są nadrzędnym źródłem prawdy o stanie. Zadanie frontendowe: nie ruszaj dokumentów reguł.
- Nie uruchamiaj całego `pytest`/`ruff`/`mypy` bez potrzeby w trakcie pracy; pełny zestaw na końcu kroku.

## Reguły TI4 (KLUCZOWE)

- **Nie koduj reguł ani statystyk TI4 z pamięci.** Dane liczbowe i teksty kart tylko z assetów AsyncTI4
  (`StaticDataRegistry`, `assets/`), zero hardkodowania.
- **Źródło reguł: `docs/rules_tirules/`** (offline zrzut tirules2.com: LRR 2.0 PoK + Codexy + Thunder's Edge + rulingi Dane).
  To zasady i doprecyzowania, NIE opisy zdolności frakcji/kart (te są w assetach JSON). Gdy zrzut nie wystarcza: tirules2.com,
  potem LRR PDF / TI Wiki.
- Reguła mechaniczna musi mieć wpis w `docs/rules/R<NN>.md` (indeks w `RULES.md`) ze źródłem, ZANIM trafi do kodu.
- Brak potwierdzonego źródła => oznacz ⚠️ ZAŁOŻENIE i poproś użytkownika o potwierdzenie. Jego decyzja jest ostateczna.
- Adjacency (sąsiedztwo) ≠ traversability (przejezdność): graf mapy trzyma czyste sąsiedztwo, blokady to osobna warstwa.

## Silnik: SĘDZIA (RULES 29)

- Zwykłe akcje walidują legalność przez kod: nielegalne => `ValueError` => HTTP 422.
- **God-Mode** (`/god-mode/patch`, `core/board_edit.*`) to wentyl, CELOWO omija walidację.
- **Okna czasowe** (`GameState` + `core/timing.py`): kolejka graczy pytanych po kolei (od gracza po aktywnym, zgodnie z zegarem).
  Reakcje when/after/instead: STOP z cofaniem + jednolita pauza (RULES 43.4).
- Walka pełna, interaktywna, seedowalny RNG. E1–E3 to fundament: dobudowuj, nie przepisuj.
- `src/engine/` (puste katalogi) = przyszła warstwa AI, można przebudować.

## Assety

Lokalnie w `assets/`. Filtrowanie źródeł po polu `source` w JSON (nie po nazwie pliku). Aktywne: `assets/enabled_sources.json`
(`base, pok, codex1-4, thunders_edge`; Codexy MUSZĄ być włączone). Dane JSON są w repo, grafiki/fonty poza repo (CDN AsyncTI4).

## Stack

Python >=3.12 + `uv`, Pydantic v2, NumPy, networkx. Frontend: React 19 + Vite + TypeScript + Zustand + react-query,
design system `frontend/src/ds/`. QA: pytest + hypothesis, ruff, mypy --strict.

## Architektura (zależności tylko w dół)

- `core/` — czyste funkcje `state -> state`, zero HTTP. Jedyne źródło reguł (woła je `api/` i przyszłe `ai/`).
- `api/routers/<temat>.py` — cienkie endpointy (stan -> `core/` -> commit/broadcast -> mapowanie błędów). Zależności: `AppContext`/`get_ctx`.
  Każdy endpoint zmieniający stan: `actor: ActorId` + kontrola `core/actor.py` ALBO `dependencies=[HostOnly]` (RULES 44.1a;
  pilnuje `tests/test_actor_guard.py`).
- Asymetria frakcji/tech/kart = hooki (`core/rules_hooks.py`, `core/hooks/`), NIE `if faction == ...` w regule bazowej.
- Punkty centralne (RULES 43.1a): płatność, TG, żetony, exhaust, kontrola planet, jednostki, technologie, VP mają JEDNĄ funkcję w `core/`;
  wyjątki tylko z komentarzem `HOOK-CANDIDATE`.
- Nowa mechanika: reguła w `rules/` => funkcja w `core/` + test => endpoint w `api/routers/`.
- Rozmiar pliku to miękka wskazówka (~500 linii); dziel tematycznie, nie na siłę.

## Kości

Każdy rzut w UI to fizyczny d10 (scena 3D). Wynik liczy silnik. Rzut poza walką: w `core/` wołaj `dice.record_table_roll(...)`;
własne okno: `HoldRollButton` + `soloHold` + `useDiceStage().throwDice`. Bez własnych animacji kostek. Przepis: `ARCHITEKTURA_KODU.md` §3a.1.

## Karty

Cel: KOMPLET kart (akcji, agend, eksploracji, reliktów, notek, liderów, zdolności, technologii). Pipeline: `ARCHITEKTURA_KODU.md` §3a
(RULES => `register_effect` => `register_effect_inputs` => zagrywalność => test => raport). Tekst karty z assetów. Karta zagrywana
PRZECIĄGNIĘCIEM z ręki; podnieść można tylko kartę legalną (`action_cards.playability`). Postęp: `POKRYCIE_HOOKOW.md` (nie czytaj w całości).

## Workflow

- Blok pracy = działający kod + testy + aktualizacja `docs/PROGRESS.md` (krótko, nowa sekcja na końcu) + commit.
- Po zmianie kodu: `uv run pytest -q` ; `uv run ruff check src tests` ; `uv run mypy src tests` (+ build przy froncie). Wszystko zielone.
- Komentarze, docstringi i dokumentacja po polsku.
- Commituj po ukończonym kroku przy zielonym QA, wiadomość po polsku, staguj konkretne pliki (nie `git add .`).
- Bez `git push` bez wyraźnej zgody.
