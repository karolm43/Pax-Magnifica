# Custodian Engine — zasady projektu (steering)

Ten plik jest wczytywany automatycznie w każdej sesji. Definiuje trwałe zasady,
których trzymam się niezależnie od tego, czy pamiętam poprzednią rozmowę.

## Czym jest projekt

Lokalny silnik do **Twilight Imperium: 4th Edition** w trybie solo, którego CELEM
KOŃCOWYM jest **autonomiczny bot-przeciwnik** grający własnymi frakcjami (strategia,
ruch, walka, agenda, punktacja). Dojrzałość w trzech etapach:
1. cyfrowa plansza + God-Mode (gotowe) — odwzorowanie i edycja stanu, Undo;
2. silnik rozgrywki (w toku) — realne fazy/tury/akcje/walka (reguły świata dla bota);
3. bot AI (cel) — warstwa decyzyjna grająca frakcją samodzielnie.
Mapa dokumentacji i cel szczegółowo: `docs/README.md`. Wizja/architektura:
`docs/specyfikacja_techniczna_i_architektura_systemu.md`.

## Jak czytać stan projektu na starcie sesji

Zawsze na początku sesji sprawdź w tej kolejności:
1. `docs/README.md` — indeks dokumentacji: cel, struktura repo, gdzie co jest.
2. `docs/PROGRESS.md` — co zrobione, co następne, decyzje projektowe.
3. `docs/PLAN_PELNA_ROZGRYWKA.md` — który etap silnika (E1–E7) robimy teraz + frakcje.
4. `docs/RULES.md` — zweryfikowane reguły TI4 (źródło prawdy dla mechanik).
5. Realny kod w `src/` i testy w `tests/` — nadrzędne źródło prawdy o stanie,
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
- Aktywne źródła: `assets/enabled_sources.json` — obecnie `base, pok, codex1-4,
  thunders_edge`. Codexy MUSZĄ być włączone (oficjalne erraty Ω/ΩΩ, patrz RULES.md 14).
  Pozostały homebrew zostaje na dysku, ale nie jest ładowany.
- **Dane JSON/properties są W REPO** (`assets/data`, `systems`, `planets`, `alias` +
  `enabled_sources.json`, ~5 MB) — `git clone` wystarcza do uruchomienia. Grafiki/fonty
  są poza repo (`.gitignore`); frontend bierze je z CDN AsyncTI4.

## Stack i narzędzia

- Backend: Python >=3.12 (lokalnie 3.14), zarządzany przez `uv`.
- Dane: Pydantic v2. Obliczenia: NumPy (+ Numba w fazie taktycznej — uwaga na
  wsparcie Pythona 3.14). Graf: networkx.
- Frontend: viewer oparty na AsyncTI4 `ti4_web` — React 19 + Vite + TypeScript +
  Zustand + react-query + własny design system (`frontend/src/ds/`). Tauri opcjonalnie
  na końcu (owija ten sam kod web).
- QA: pytest + hypothesis, ruff, mypy --strict.

## Architektura kodu (chroń czytelność — pełny opis: docs/ARCHITEKTURA_KODU.md)

Twilight jest złożony (frakcje/tech/karty łamią reguły bazowe) i dojdzie silnik AI —
dlatego trzymamy ostry podział warstw, zależności tylko w dół:
- **`core/`** — reguły gry jako CZYSTE funkcje nad `GameState` (`state -> state`). Zero
  importów FastAPI/HTTP. Testowalne bez sieci. To jedyne źródło reguł — woła je i `api/`,
  i przyszłe `ai/`.
- **`api/`** — CIENKIE endpointy: odczyt stanu → wywołanie `core/` → commit/broadcast →
  mapowanie błędów domenowych na HTTP. Żadnej logiki gry w endpointcie.
- **`ai/`** (przyszłość) — decyzje bota; woła wyłącznie `core/`.
- **Asymetria (frakcje/tech/karty)** = hooki w oknach silnika (`core/rules_hooks.py` przy
  E7), NIE `if faction == ...` w regule bazowej.
- Nowa mechanika: reguła → `RULES.md` ze źródłem → czysta funkcja w `core/` + test →
  cienki endpoint w `api/routers/<temat>.py`. Plik > ~300 linii → podział tematyczny.
- **Struktura API (po refaktorze):** `app.py` to cienka fabryka; endpointy w
  `api/routers/*`; logika God-Mode w `core/board_edit.py`; współdzielone zależności w
  `AppContext` (`api/context.py`, zależność `get_ctx`). Wzorzec routera: ARCHITEKTURA_KODU.md §4.
  Przy E3 dodaj `core/tactical.py` + `api/routers/tactical.py`.

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
