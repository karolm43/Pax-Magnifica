# Custodian Engine — zasady projektu (steering)

Ten plik jest wczytywany automatycznie w każdej sesji. Definiuje trwałe zasady,
których trzymam się niezależnie od tego, czy pamiętam poprzednią rozmowę.

## Czym jest projekt

Lokalny silnik AI przeciwnika do fizycznych rozgrywek **Twilight Imperium: 4th
Edition** (tryb solo / human-in-the-loop). Fizyczna plansza to źródło prawdy;
aplikacja odwzorowuje stan, cofa ruchy (Undo/God-Mode) i w dalszych fazach gra
jako autonomiczny bot. Pełna specyfikacja: `docs/specyfikacja_techniczna_i_architektura_systemu.md`.

## Jak czytać stan projektu na starcie sesji

Zawsze na początku sesji sprawdź w tej kolejności:
1. `docs/PROGRESS.md` — co zrobione, co następne, decyzje projektowe.
2. `docs/RULES.md` — zweryfikowane reguły TI4 (źródło prawdy dla mechanik).
3. Realny kod w `src/` i testy w `tests/` — to nadrzędne źródło prawdy o stanie,
   ważniejsze niż pamięć czy opisy.

## Zasady reguł Twilight Imperium (KLUCZOWE)

- **Nigdy nie koduj reguł TI4 ani statystyk z pamięci.** To zakaz ze specyfikacji
  (sekcja 5.1) i świadoma decyzja — moja pamięć reguł TI4 jest zawodna.
- **Dane liczbowe** (jednostki, planety, technologie, koszty) czytaj WYŁĄCZNIE
  z assetów AsyncTI4 przez `StaticDataRegistry`. Zero hardkodowania.
- **Reguły mechaniczne** (ruch, walka, anomalie, timing) muszą mieć wpis w
  `docs/RULES.md` z odniesieniem do oficjalnego źródła (Living Rules Reference /
  TI Wiki) ZANIM trafią do kodu.
- **Oznaczaj założenia.** Jeśli implementuję mechanikę bez potwierdzonego źródła,
  jawnie oznacz ją jako ⚠️ ZAŁOŻENIE w RULES.md i poproś użytkownika o potwierdzenie.
  Użytkownik zna grę w szczegółach — jego decyzja jest ostateczna.
- Gdy reguła jest niejasna, **zweryfikuj ją online** w oficjalnym LRR zamiast zgadywać.
- Rozróżniaj **sąsiedztwo (adjacency)** od **przejezdności (traversability)** — to
  różne pojęcia (patrz RULES.md 1). Graf mapy trzyma czyste sąsiedztwo; blokady
  ruchu/anomalie to osobna warstwa logiki zależna od gracza i stanu gry.

## Zarządzanie assetami

- Assety (AsyncTI4) leżą lokalnie w `assets/`; podział na dysku zostaje nienaruszony.
- Filtrowanie źródeł: po POLU `source` wewnątrz wpisu JSON, nie po nazwie pliku.
- Aktywne źródła: `assets/enabled_sources.json` (na start tylko oficjalne:
  base, pok, codex1-4). Homebrew zostaje na dysku, ale nie jest ładowane.
- Grafiki/fonty są poza repo (`.gitignore`). W repo wersjonujemy tylko dane JSON
  potrzebne silnikowi oraz `enabled_sources.json` (konfiguracja).

## Stack i narzędzia

- Backend: Python >=3.12 (lokalnie 3.14), zarządzany przez `uv`.
- Dane: Pydantic v2. Obliczenia: NumPy (+ Numba w fazie taktycznej — uwaga na
  wsparcie Pythona 3.14). Graf: networkx.
- Frontend (od Bloku 3): React 19 + Vite + TypeScript + SVG + Zustand + Tailwind +
  shadcn/ui. Tauri opcjonalnie na końcu (owija ten sam kod web).
- QA: pytest + hypothesis, ruff, mypy --strict.

## Workflow i jakość kodu

- Pracujemy blokami (jeden blok ≈ jedna sesja), granice tam gdzie coś jest
  samodzielnie testowalne. Każdy blok kończy się: działającym kodem + testami +
  aktualizacją `docs/PROGRESS.md` + commitem.
- Po KAŻDEJ zmianie kodu uruchom pełny zestaw:
  `uv run pytest -q` ; `uv run ruff check src tests` ; `uv run mypy src tests`.
  Wszystko musi być zielone przed zakończeniem.
- Komentarze, docstringi i dokumentację pisz po polsku (zgodnie z resztą projektu).
- Git: **commituj zawsze**, gdy zadanie/krok jest ukończony i cały zestaw QA jest
  zielony (pytest + ruff + mypy, a przy zmianach frontu także build). Nie czekaj na
  osobną prośbę o commit. Jeden commit = jeden spójny, testowalny krok; wiadomość po
  polsku, opisowa. Staguj konkretne pliki (nie `git add .`).
- Nie wypychaj na zdalne repo (`git push`) bez wyraźnej zgody użytkownika.
