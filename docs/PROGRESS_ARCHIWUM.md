# Archiwum postępu — Custodian Engine

Historia ukończonych bloków pracy (Faza 1 → bloki do 2026-11-24). Przeniesiona z `PROGRESS.md`,
żeby odchudzić plik czytany na starcie każdej sesji. Aktualny etap i ostatnie bloki są
w `PROGRESS.md`. Prawda o stanie kodu zawsze w `src/` i testach — tu jest zapis decyzji.

---

## Faza 1: Fundament Danych, Graf Mapy i God-Mode UI

Podzielona na 4 bloki (jedna sesja = jeden blok):

- **Blok 1 — Bootstrap + dane (CORE dolna warstwa)** — ✅ UKOŃCZONY
- **Blok 2 — Mapa + stan (CORE górna warstwa)** — ✅ UKOŃCZONY
- **Blok 3 — API + mapa w UI** — ✅ UKOŃCZONY
- **Blok 4 — Edycja + map stringi (UI)** — 🔧 w toku (podzielony na części)
  - **4a — grafiki kafelków na mapie** — ✅ UKOŃCZONY
  - **4b — map stringi + zoom/pan + tło + sloty domowe** — ✅ UKOŃCZONY
  - **4c+ — interaktywna mapa śledząca stan gry** — ⬜ w planie
    (jednostki na kafelkach, edycja menu bocznym, gracze/VP/zasoby, planety).
    Pełny plan: `docs/plan_faza1_interaktywna_mapa.md`.

**Cel aktu (DoD Fazy 1):** rozgrywasz fizyczną partię używając aplikacji jako
interaktywnej mapy + licznika zasobów/VP, stan gotowy pod AI.

**Ustalone decyzje (4c+):**
- Skróty jednostek = oficjalne `asyncId` (`dd, ca, ff, dn, cv, gf, pd, sd, mf, ws, fs`),
  zgodne z nazwami grafik `assets/units/<kolor>_<asyncId>.png`.
- Edycja przez **menu boczne** (klik w kafelek → panel).
- Wybór frakcji z **setupem** (auto flota startowa + planety domowe z danych frakcji).
- Jednostki w **dwóch miejscach**: przestrzeń (statki) vs planeta (naziemne + struktury) —
  klasyfikacja zweryfikowana w `docs/RULES.md` 2b (NIE z flag AsyncTI4, które są błędne).

**Decyzja o UI (ustalona):** frontend = **React 19 + Vite + TypeScript + SVG** (wg spec).
Tauri (opakowanie desktopowe tego samego kodu web) opcjonalnie na końcu — rozwiązuje
dystrybucję, której teraz nie potrzebujemy. Nie wybieramy web vs Tauri — Tauri owija web.

---

## 📋 Mapowanie oficjalnego planu Fazy 1 na stan (checkpoint)

Oficjalny plan Fazy 1 ma 5 pozycji (3× CORE, 2× UI). Stan faktyczny w kodzie:

| # | Pozycja planu | Warstwa | Status |
|---|---------------|---------|--------|
| 1 | Import i konwersja JSON (planety, systemy, technologie, jednostki) | CORE | ✅ **zrobione, zmienione źródło** |
| 2 | Siatka heksagonalna (q,r,s) + krawędzie Wormholi (Alfa/Beta) | CORE | ✅ **zrobione** |
| 3 | GameState (Pydantic v2) + Event Sourcing (SQLite, Undo/Override) | CORE | ✅ **zrobione** |
| 4 | Mapa SVG w React + **szybki edytor jednostek (skróty "2D 1C 4F")** | UI | 🔧 **częściowo** |
| 5 | Parser map stringów (wklejenie kodu ustawia kafelki) | UI | ✅ **zrobione** |

**Szczegóły rozbieżności / stanu:**

- **#1 — źródło danych zmienione (świadomie):** plan mówił `surewht/ti4-mcp`. W Bloku 1
  porzucono to źródło jako niekompletne; dane pochodzą z lokalnych assetów **AsyncTI4**.
  Rejestr ładuje 104 jednostki, 111 planet, 195 systemów (base+pok+codex1-4). ✅ cel osiągnięty.
- **#2 — pełne:** `HexGrid` (q,r,s), sąsiedztwo geometryczne + wormhole, anomalie, pozycje
  z oficjalnego aliasu AsyncTI4 (`position_alias.properties`). Rozdzielone sąsiedztwo od
  przejezdności (patrz RULES.md 1).
- **#3 — pełne:** `GameState` (Pydantic v2, serializowalny), `EventStore` (Snapshot Stack
  w SQLite, bezpieczny wątkowo), Undo/Redo/God-Mode. API: `PUT /state`, `POST /god-mode/patch`.
- **#4 — mapa SVG zrobiona, EDYTOR JEDNOSTEK BRAKUJE:**
  - ✅ Mapa SVG: grafiki kafelków, zoom/pan, sloty domowe graczy, tło.
  - ❌ **Szybki edytor jednostek na heksie ze skrótami klawiszowymi (`"2D 1C 4F"`
    = 2 Destroyery, 1 Cruiser, 4 Fightery itp.)** — NIE istnieje. To jedyna realna
    luka Fazy 1. Wymaga: (a) kliknięcie w heks → wybór aktywnego systemu, (b) parser
    skrótu "liczba+litera jednostki" mapujący litery na `baseType` z rejestru,
    (c) zapis do `GameState.systems[pos].space_units` przez God-Mode/typowany endpoint,
    (d) render jednostek na kafelku.
- **#5 — pełne (z nadwyżką):** parser map stringów + `POST /map/load` + wklejanie w UI +
  rozpoznanie slotów domowych na rogach.

**Wniosek:** Faza 1 jest ukończona w ~90%. Do domknięcia zostaje **jeden element: szybki
edytor jednostek na heksie** (pozycja #4 planu). Dopiero po nim Faza 1 = 100%.

**Nadwyżki ponad plan (zrobione dodatkowo):** WebSocket (synchronizacja stanu live),
grafiki kafelków, zoom/pan, sloty domowe graczy, serwowanie assetów przez `/static`.

---

### ✅ Blok 1 — ukończony

**Zadania:**
- [x] **A0** Bootstrap środowiska: `pyproject.toml` (uv), zależności, ruff + mypy --strict + pytest
- [x] **A1** `src/config.py` + `assets/enabled_sources.json` (manifest aktywnych źródeł)
- [x] **A2** Modele Pydantic v2: `UnitDef`, `PlanetDef`, `SystemDef` (`src/core/models.py`)
- [x] **A3** `StaticDataRegistry` (`src/core/registry.py`): import, filtr źródeł, walidacja referencji

**Rezultat (zweryfikowany):**
- Rejestr ładuje oficjalny rdzeń: **104 jednostki, 111 planet, 195 systemów** (base + pok + codex1-4).
- Spójność referencji system→planeta: **OK** (zero wiszących referencji w rdzeniu).
- Homebrew prawidłowo pomijany (ds, theodisi, thunders_edge itd. nieładowane).
- **13 testów zielonych**, ruff czysty, mypy --strict czysty.

**Jak uruchomić:**
```powershell
uv run python -m src.core.registry   # statystyki rejestru
uv run pytest -q                      # testy
uv run ruff check src tests           # lint
uv run mypy src tests                 # typy
```

**Decyzje i ustalenia techniczne:**
- Python na maszynie: **3.14.x**; projekt celuje w `>=3.12`. **Numba** (potrzebna w Fazie 2/M2) może jeszcze nie wspierać 3.14 — do sprawdzenia przed Blokiem Fazy 2.
- Źródło danych: **lokalne assety AsyncTI4** (NIE `surewht/ti4-mcp` — porzucone, dane AsyncTI4 są kompletne).
- **Filtrowanie źródeł idzie po POLU `source` wewnątrz wpisu JSON**, nie po nazwie pliku (nazwy plików nie odpowiadają 1:1 źródłom, np. jednostki bazowe są w `baseUnits.json`).
- Pole `source` w danych bywa bardziej granularne niż `sources.json` (np. `andcat`, `somno`, `draft`) — nie problem, bo ładujemy inkluzywnie wg białej listy.
- Modele używają `extra="ignore"` — pomijają pola UI (pozycje tokenów, ścieżki obrazów, layouty).
- Manifest aktywnych źródeł: `assets/enabled_sources.json` = `["base","pok","codex1","codex2","codex3","codex4"]` (edytowalny bez zmian w kodzie).
- Podział assetów na dysku zostaje nienaruszony; grafiki poza repo (`.gitignore`).

**Struktura dodana w Bloku 1:**
```
pyproject.toml
assets/enabled_sources.json
src/config.py
src/core/models.py
src/core/registry.py
tests/test_config.py, test_models.py, test_registry.py
```

---

### ✅ Blok 2 — ukończony (CORE górna warstwa)

**Zadania:**
- [x] **A4** `HexGrid` (`src/core/hex_grid.py`): współrzędne kubiczne (q,r,s), sąsiedztwo, odległości, wormhole, anomalie
- [x] **A5** `GameState` + `EventStore` (`src/core/game_state.py`, `event_store.py`): Snapshot Stack w SQLite, Undo/Redo/God-Mode

**Rezultat (zweryfikowany):**
- Mapowanie pozycji AsyncTI4 `RPP` ↔ `(q,r,s)` działa: pierścień N = odległość N od centrum.
- Sąsiedztwo geometryczne + wormhole (ten sam typ łączy odległe systemy) + supernova blokuje ruch.
- `GameState` serializuje się do JSON (round-trip), `clone()` niezależny.
- `EventStore`: commit/undo/redo + God-Mode (commit po undo obcina gałąź redo).
- **34 testy zielone** (łącznie z Blokiem 1), ruff czysty, mypy --strict czysty.

**Zależności dodane:** `numpy==2.5.4`, `networkx==3.7`, `types-networkx` (dev).
Działają na Pythonie 3.14. (networkx wybrany zamiast rustworkx — czysty Python, zero ryzyka natywnych buildów na 3.14.)

**Decyzje techniczne:**
- Współrzędne heksów: pozycja AsyncTI4 to `RPP` (R=pierścień 1 cyfra, PP=indeks 2 cyfry). `000`=centrum=(0,0,0).
- Anomalie w danych AsyncTI4 to flagi boolowskie: `isNebula`, `isAsteroidField`, `isSupernova`, `isGravityRift` (dodane do `SystemDef`, znormalizowane do `anomalies: set[str]`).
- Supernova = jedyna anomalia blokująca ruch (brak krawędzi w grafie). Nebula/rift/asteroid nie blokują sąsiedztwa (modyfikują ruch/walkę — logika w późniejszych fazach).
- `tileAdjacencies.properties` zawiera gotowe sąsiedztwa dla przypadków specjalnych (hyperlanes `frac`, centrum) — na razie liczymy geometrycznie; hyperlanes do obsłużenia później, gdy wejdą w grę.
- `EventStore` używa SQLite (`:memory:` w testach, plik na dysku w produkcji) ze stosem migawek + wskaźnikiem `current`.

**Struktura dodana w Bloku 2:**
```
src/core/hex_grid.py       (Hex, position_to_hex, HexGrid)
src/core/game_state.py     (GameState, PlayerState, SystemState, Phase)
src/core/event_store.py    (EventStore - Snapshot Stack SQLite)
tests/test_hex_grid.py, test_game_state.py
```

---

### 🔧 Między-blok: weryfikacja reguł TI4 + steering (ukończony)

- Utworzono `docs/RULES.md` — zweryfikowane reguły TI4 ze źródłami (LRR 2.0 / wiki).
- **Weryfikacja anomalii ujawniła błąd projektowy w HexGrid:** mieszał sąsiedztwo
  z przejezdnością. Poprawione:
  - Graf = CZYSTE sąsiedztwo (geometria + wormhole), niezależne od gracza.
  - Supernova NIE usuwa już krawędzi (sąsiedztwo istnieje; blokowany tylko ruch).
  - `is_blocking` → `is_impassable` (dotyczy ruchu, nie sąsiedztwa) + `anomalies_at()`.
  - Metadane systemu zrefaktoryzowane na dataclass `_PlacedSystem` (lepsze typowanie).
- Zweryfikowane reguły anomalii: asteroid field (blokada warunkowa od Antimass
  Deflectors), nebula (wejście tylko gdy aktywny, ruch=1 przy wyjściu, +1 obrona),
  supernova (bezwarunkowo nieprzejezdna), gravity rift (+1 ruch, rzut 1-3 niszczy).
  Efekty ruchu/walki anomalii = DO ZROBIENIA w warstwie ruchu (późniejsza faza).
- Utworzono `.kiro/steering/custodian-engine.md` — zasady projektu wczytywane
  automatycznie w każdej sesji (zakaz hardkodowania reguł, workflow, stack, QA).
- **35 testów zielone, ruff + mypy --strict czyste.**

### ✅ Blok 3 — ukończony (API + mapa w UI)

**Zadania:**
- [x] **B1** Minimalne API FastAPI (`src/api/`): `GET /state`, `GET /map`, God-Mode
  (`PUT /state`, `POST /god-mode/patch`), `POST /undo|/redo`, `GET /static/*`,
  WebSocket `/ws` synchronizujący stan. Zależności: `fastapi`, `uvicorn[standard]`.
- [x] **B2** Mapa SVG w React 19 + Vite + TS (`frontend/`): render heksów z (q,r,s),
  krawędzie sąsiedztwa/wormhole, połączenie przez WebSocket (store Zustand), Undo/Redo.

**Rezultat (zweryfikowany):**
- Backend oddaje `GET /map` = 7 kafelków + 12 krawędzi (Mecatol `18` w centrum (0,0,0),
  pierścień z prawdziwych systemów rejestru; anomalie GRAVITY_RIFT/NEBULA wykryte z danych).
- `GET /state` zwraca kopertę `{type, state, history}`; mutacje commitują do EventStore
  i rozsyłają nowy stan przez WebSocket (zweryfikowane testem broadcastu).
- Undo/Redo przez REST działają; commit po undo obcina gałąź redo.
- Frontend: build (`tsc -b && vite build`) czysty; dev-serwer Vite + proxy `/api`,`/ws`
  do backendu zweryfikowane end-to-end (HTML 200, `/api/map` → 7 kafelków).
- **50 testów zielonych** (łącznie), ruff czysty, mypy --strict czysty.

**Jak uruchomić (dwa terminale):**
```powershell
# Terminal 1 — backend (katalog repo)
uv run python -m src.api            # FastAPI na http://127.0.0.1:8000

# Terminal 2 — frontend (katalog frontend/)
npm install                         # pierwszy raz
npm run dev                         # Vite na http://localhost:5173
```

**Decyzje techniczne:**
- Warstwa API w `src/api/` (osobny pakiet): `app.py` (fabryka `create_app`, endpointy,
  WebSocket), `schemas.py` (DTO Pydantic — oddzielone od modeli domenowych),
  `state_service.py` (jedyne miejsce mutujące stan: commit + broadcast),
  `connection_manager.py` (rejestr WS + broadcast), `demo_map.py` (mapa demonstracyjna).
- **Mapa demonstracyjna** (tymczasowa, do map stringów z Bloku 4): budowana z PRAWDZIWYCH
  systemów rejestru (Mecatol w centrum + 6 systemów na pierwszym pierścieniu, preferując
  anomalie dla demonstracji renderu). Zero statystyk/reguł z pamięci.
- **God-Mode w tym bloku = generyczny**: `PUT /state` (pełne nadpisanie) + `POST /god-mode/patch`
  (częściowy, walidowany `GameState`, błąd → 422). Typowane kreatory (set-vp, set-owner,
  place-units) → Blok 4.
- **Poprawka CORE wymuszona przez API:** `EventStore` (SQLite) musiał stać się bezpieczny
  wątkowo — FastAPI/Uvicorn obsługuje synchroniczne endpointy w threadpoolu. Dodano
  `check_same_thread=False` + `threading.RLock()` wokół operacji. (Realne ograniczenie
  produkcyjne, nie tylko testowe.)
- Dodano publiczne metody `HexGrid`: `coordinates()`, `system_id_at()`, `edges()` —
  API nie sięga do pól prywatnych grafu.
- **Frontend stack:** React 19.3 + Vite 8.3 + TS 5 + Zustand 5 + Tailwind 4 (plugin
  `@tailwindcss/vite`). Proxy Vite kieruje `/api` i `/ws` do backendu → front używa
  adresów względnych (działa też pod Tauri). shadcn/ui świadomie odłożone do Bloku 4.
- Render SVG: pointy-top layout `(q,r,s)→piksele`; kolor kafelka wg anomalii, wormhole
  obwódką/linią przerywaną. Etykiety: pozycja + nazwa/ID systemu + anomalie.

**Struktura dodana w Bloku 3:**
```
src/api/__init__.py, app.py, schemas.py, state_service.py,
        connection_manager.py, demo_map.py, __main__.py
tests/test_api.py, test_demo_map.py
frontend/  (package.json, vite.config.ts, tsconfig*.json, index.html, README.md,
            src/{main,App,HexMap,store,api,types,hex}.tsx|ts, index.css)
```

**Uwaga techniczna (do ewentualnej czystki):** `TestClient` zgłasza ostrzeżenie
`StarletteDeprecationWarning` (httpx vs httpx2) — nieblokujące, do rozważenia później.

**Przed Blokiem 4:** map stringi AsyncTI4 (prawdziwa inicjalizacja planszy zamiast
mapy demonstracyjnej), panele edycji God-Mode + Action Wizards (shadcn/ui), grafiki
kafelków ładowane lokalnie z assetów (poza gitem).
---

### ✅ Blok 4a — ukończony (grafiki kafelków na mapie)

**Zadania:**
- [x] Backend: pole `image_path` (alias `imagePath`) w `SystemDef` — czytane z danych
  AsyncTI4, nie zgadywane. Pole `image_url` w `MapTile`, budowane jako
  `/static/tiles/<imagePath>`. Stałe `TILES_DIR` i `STATIC_URL_PREFIX` w `config.py`.
- [x] Frontend: render prawdziwych grafik kafelków w SVG (`<image>` + clipPath heksagonalny)
  zamiast kolorowych wielokątów; fallback na kolor anomalii, gdy brak grafiki. Proxy Vite
  `/static` → backend. Layout siatki zmieniony na **flat-top** (zgodnie z orientacją grafik
  AsyncTI4), dodane `hexBounds()`.

**Rezultat (zweryfikowany):**
- `/map` zwraca `image_url` dla każdego kafelka: `000`(Mecatol)→`/static/tiles/18_MR.png`,
  `101`→`41_GravityRift.png`, `102`→`42_Nebula.png` itd.
- Grafiki serwują się przez backend (`18_MR.png` → 200, image/png, ~193 KB) i przez proxy
  Vite (`42_Nebula.png` → 200, image/png). Zweryfikowane end-to-end.
- Test `test_demo_tiles_image_files_exist` potwierdza, że każdy `imagePath` demo-mapy
  wskazuje istniejący plik na dysku (realne mapowanie, nie zgadywanie).
- **52 testy zielone**, ruff + mypy --strict czyste, build frontendu czysty.

**Decyzje techniczne:**
- Powiązanie system↔grafika idzie przez pole `imagePath` w danych systemu
  (np. `18.json` → `"18_MR.png"`) — 1:1 z plikami w `assets/tiles/`. Nie parsujemy nazw.
- Grafiki pozostają poza repo (`.gitignore`, `assets/*`) — serwowane lokalnie z dysku.
  Test grafik działa tylko lokalnie z pełnymi assetami (akceptowalne — to dane użytkownika).
- Orientacja heksów: **flat-top** (grafiki AsyncTI4 są flat-top). Poprzedni pointy-top
  z Bloku 3 zmieniony, by obrazy pokrywały się z komórkami siatki.

**Pułapka operacyjna (zanotowana):** osierocony proces Uvicorn z wcześniejszej weryfikacji
trzymał port 8000 (`Errno 10048`), przez co nowy serwer nie startował i serwował stary kod.
Rozwiązanie: ubicie procesu po PID z `Get-NetTCPConnection -LocalPort 8000`. Na przyszłość —
pilnować zwalniania portu po `stop`.

**Struktura zmieniona w Bloku 4a:**
```
src/core/models.py      (+ image_path w SystemDef)
src/config.py           (+ TILES_DIR, STATIC_URL_PREFIX)
src/api/schemas.py      (+ image_url w MapTile)
src/api/app.py          (build_map_view wypełnia image_url)
frontend/src/hex.ts     (flat-top layout + hexBounds)
frontend/src/HexMap.tsx (render <image> + clipPath, fallback kolor)
frontend/src/types.ts   (+ image_url), vite.config.ts (+ proxy /static)
tests/test_api.py, test_demo_map.py  (+ testy image_url / istnienia plików)
```
---

### ✅ Blok 4b — ukończony (map stringi + zoom/pan + tło)

**Zadania:**
- [x] Reguła map stringa + pozycji zweryfikowana i spisana do `docs/RULES.md` 2a
  (źródło: `assets/alias/position_alias.properties`, NIE z pamięci).
- [x] `src/core/positions.py` — tabela pozycja→Hex z pliku alias (źródło prawdy
  orientacji AsyncTI4). Wzór axial→kubiczny: `q=a, r=(b-a)/2, s=-q-r`.
- [x] `src/core/map_string.py` — parser map stringa (`0`=puste, Mecatol domyślny
  w centrum) + `build_grid_from_map_string` (buduje `HexGrid` z rejestru).
- [x] `HexGrid.place_system(hex_override=...)` — pozwala użyć współrzędnych z aliasu.
- [x] Backend: `POST /map/load` (wklejasz string → nowa mapa), broadcast zdarzenia
  `{type:"map"}` przez WebSocket; `/map` zwraca bieżącą mapę (`app.state.current_grid`).
- [x] Frontend: pole wklejania stringa + przycisk „Załaduj mapę" + „Przykład";
  zoom (kółko), pan (przeciąganie), reset (dwuklik); tło gradientowe (usunięte
  „dziwne prostokąty" — teraz czysty radialny gradient kosmosu).

**Rezultat (zweryfikowany na stringu użytkownika):**
- String `72 66 77 ... 41 40` (36 pozycji, 6 pustych) → **31 kafelków, 78 krawędzi**,
  wszystkie z `image_url`. Centrum = Mecatol (`18_MR.png`). Zero brakujących w rejestrze.
- `000` sąsiaduje dokładnie z `101-106`; wszystkie pozycje spełniają `q+r+s=0`.
- **63 testy zielone**, ruff + mypy --strict czyste, build frontendu czysty.

**Decyzje techniczne:**
- Orientacja pozycji: TERAZ ze źródła AsyncTI4 (`position_alias.properties`), nie
  z geometrycznego `position_to_hex` (Bloku 2 — inna rotacja). To było konieczne, by
  mapa odwzorowała numerację/wygląd AsyncTI4 (`101` nad centrum, zgodnie z zegarem).
- `position_to_hex` z Bloku 2 zostaje (geometria + testy), ale budowa realnej mapy
  używa tabeli aliasu przez `hex_override`.
- Kafelki spoza aktywnych źródeł (homebrew) są pomijane cicho — graf ma tylko znane.
- Zoom/pan: transformacja grupy SVG (`translate+scale`), zakres 0.3–4×.

**Pułapka operacyjna (ponownie):** osierocony Uvicorn trzymał port 8000 między
weryfikacjami. Ubijany po PID (`Get-NetTCPConnection -LocalPort 8000`). Do rozważenia:
skrypt/health-check zwalniający port przed startem.

**Struktura dodana/zmieniona w Bloku 4b:**
```
src/core/positions.py          (NOWY — tabela pozycji z aliasu)
src/core/map_string.py         (NOWY — parser + build_grid_from_map_string)
src/core/hex_grid.py           (+ hex_override w place_system)
src/config.py                  (+ POSITION_ALIAS_PATH)
src/api/schemas.py             (+ MapStringRequest)
src/api/app.py                 (+ POST /map/load, current_grid, broadcast map)
docs/RULES.md                  (+ sekcja 2a: map string i pozycje)
tests/test_map_string.py       (NOWY), tests/test_api.py (+ testy /map/load)
frontend/src/{api,store,App,HexMap}.ts|tsx  (map string, zoom/pan, tło)
```
---

### ✅ Blok 4b+ — sloty domowe graczy (home systems na rogach)

**Kontekst (ustalenie użytkownika):** 6 "brakujących" pozycji w map stringu
(`0` na `301, 304, 307, 310, 313, 316`) to **systemy domowe frakcji** — rogi
pierścienia 3 przy 6 graczach. Nie ma ich w stringu, bo kafelek domowy zależy od
wybranej frakcji. Potwierdzone geometrycznie (każdy róg: jedna współrzędna = 0, dwie = ±3).

**Zadania:**
- [x] `src/core/home_slots.py` — mapa rogów → kolor gracza (6-osobowy układ).
- [x] Parser: `0` na rogu domowym → `PlacedTile(is_home_slot, home_color)` zamiast pomijania.
- [x] `build_grid_from_map_string` umieszcza sloty jako węzły (pseudo-id `__home__`).
- [x] `MapTile`: pola `is_home_slot`, `home_color`. `build_map_view` rozpoznaje sloty.
- [x] Frontend: render kolorowego heksa gracza (grubszy obrys), paleta kolorów.
- [x] `docs/RULES.md` 2a: reguła home-slotów (✅ geometria) + kolory (⚠️ ZAŁOŻENIE).

**Rezultat (zweryfikowany na stringu użytkownika):**
- `/map/load` → 37 kafelków = 30 systemów + 6 slotów domowych + Mecatol.
- Kolory rogów: `301`red, `304`green, `307`white, `310`blue, `313`purple, `316`yellow
  (odwzorowuje render użytkownika). **65 testów zielone**, QA czyste.

**⚠️ DO POTWIERDZENIA:** przypisanie kolorów do konkretnych rogów to konwencja
wyświetlania (nie reguła LRR). Układ przyjęty z obrazka użytkownika — do akceptacji.
---

### ✅ Blok 4c — jednostki na mapie + setup frakcji + edycja (menu boczne)

Realizuje Etapy A+B+C planu `docs/plan_faza1_interaktywna_mapa.md` — mapa stała się
"żywa": śledzi jednostki, pozwala zrobić setup frakcji i edytować stan.

**Core (nowe moduły):**
- `unit_catalog.py` — jawne tabele reguł: umiejscowienie (space/planet), `asyncId`
  (grafiki), kody `startingFleet`→baseType. NIE opiera się na błędnych flagach AsyncTI4.
- `faction_setup.py` — parser `startingFleet` (liczba+kod+sufiks planety), `build_setup_plan`,
  `apply_setup_to_state`. Rozwiązuje kolizje sufiksów (Xxcha ar/at) i alias `ca`/`cr` (Keleres).
- `FactionDef` w models.py + ładowanie frakcji do rejestru (27 frakcji base+pok).

**API:**
- `GET /factions` — lista frakcji do setupu.
- `POST /setup/player` — frakcja+kolor na slocie domowym: podmienia slot na kafelek domowy
  (`homeSystem`), rozkłada flotę startową (statki→space, naziemne/struktury→planety), ustawia
  kontrolę planet, technologie, towary.
- `POST /system/{pos}/space` i `POST /system/{pos}/planet/{planet}` — zmiana jednostek (God-Mode).
- `MapTile` wzbogacony o `space_units` i `planet_units` z `image_url` jednostek
  (`/static/units/<kolor>_<asyncId>.png`).

**Frontend:**
- Render jednostek na kafelkach: ikony z grafik + licznik (stosy >1).
- Panel boczny (`SidePanel.tsx`): klik w kafelek → edycja. Setup frakcji na slotach domowych
  (wybór frakcji + kolor), edycja statków w przestrzeni i naziemnych/struktur na planetach
  (przyciski +/−). Podświetlenie wybranego kafelka.

**Rezultat (zweryfikowany E2E):**
- Setup Sol na `301` → kafelek `01_Jord.png`, statki (2 carrier, 1 destroyer, 3 fighter)
  z grafikami `red_cv/dd/ff.png`, planeta Jord: 5 infantry + 1 space dock. Grafiki serwowane
  (200, image/png). Edycja jednostek działa.
- **78 testów zielone**, ruff + mypy --strict czyste, build frontu czysty.

**Reguły (RULES.md 2b/2c):** klasyfikacja space/planet (flagi AsyncTI4 błędne dla mech/warsun),
format `startingFleet` (sufiks planety = najkrótszy jednoznaczny skrót; alias ca/cr Keleres).

**Status DoD Fazy 1:** osiągnięte podstawy grywalnej mapy — widać jednostki, można zrobić
setup i przestawiać jednostki. Do pełni: panel gracza (VP/zasoby/technologie), dopieszczenie
układu ikon przy planetach, gotowość pod AI (walidacja/eksport).

---

### ✅ Blok F0+F1 — wymiana frontendu na ti4_web + endpoint `web-data`

**Decyzja użytkownika:** porzucamy własny frontend SVG; nowym frontendem jest
`ti4_web_new-main` (dojrzały viewer planszy AsyncTI4). Backend (Custodian Engine)
pozostaje źródłem prawdy — dostosowujemy GO do frontendu, nie odwrotnie:
`GameState` serializuje się do dokumentu `PlayerDataResponse`, którego oczekuje viewer.

**Co ustalono o frontendzie (analiza, nie pamięć):**
- Cała plansza renderuje się z JEDNEGO zapytania HTTP: `GET {gameDataUrl}/{gameId}/web-data`
  → obiekt `PlayerDataResponse`. Dev `gameDataUrl` = `/bot/api/public/game` (proxy Vite
  zrzuca `/bot` → backend widzi `/api/public/game/{id}/web-data`).
- Statyczne katalogi (104 jednostki / 111 planet / 195 systemów + frakcje) są WBUDOWANE
  w bundle frontendu (`src/entities/data/*.ts`, auto-gen z assetów AsyncTI4). Backend
  wysyła tylko STAN (ID: `systemId`, `asyncId`, nazwy planet), nie definicje.
- Grafiki (kafelki, jednostki, tokeny) idą ze zdalnego CDN `images.asyncti4.com`
  (`cdnImage.ts`) — zero pracy po stronie backendu na start. (Local-first = później.)
- Jednostki w `tileUnitData` kluczowane `entityId = asyncId` (`ff, dd, ca, cv, gf, mf,
  sd, pd, ...`) per frakcja. Planety kluczowane ID planety (zgodne z naszym rejestrem).
- Pozycje: `tilePositions = ["<pozycja>:<systemId>", ...]`. Frontend liczy piksele sam
  z `tileCoordinates` po kluczu pozycji AsyncTI4 — nasze pozycje używają tych samych
  identyfikatorów (`000`, `101`…), więc NIE wysyłamy `(q,r,s)`.
- WebSocket STOMP (live-patche) jest OPCJONALNY — viewer działa przez refetch. Na razie
  pominięty (wskazany lokalny adres, by nie łączyć się z produkcją AsyncTI4).

**Zrobione:**
- [x] Stary `frontend/` usunięty; `ti4_web_new-main/` przeniesiony → `frontend/`.
- [x] `frontend/vite.config.ts`: proxy `/bot` → `http://127.0.0.1:8000` (zrzut `/bot`),
  `/static` → backend. `config.ts`: `websocketUrl` → lokalny (bez produkcji AsyncTI4).
- [x] `src/api/web_data.py` (NOWY): `build_web_data` — `GameState`+`HexGrid`+rejestr →
  `PlayerDataResponse`. Minimalny, kompletny dla viewera zestaw pól (tileUnitData,
  tilePositions, ringCount, playerData, puste objectives/cardPool/expeditions/...).
- [x] `src/api/app.py`: endpoint `GET /api/public/game/{game_id}/web-data`.
- [x] `.gitignore`: usunięto wpis `ti4_web_new-main/`, dodano `frontend/build`,`node_modules`.
- [x] `tests/test_web_data.py` (NOWY): kształt dokumentu, format `tilePositions`,
  jednostki jako asyncId, dane graczy.

**Rezultat (zweryfikowany E2E):**
- Backend: `/map/load` (string użytkownika) + `/setup/player` (Sol@301) → `web-data` 200,
  33 pozycje (`000:18`, `101:72`…), statki Sol w przestrzeni (`cv×2, dd×1, ff×3`),
  Jord: `gf×5, sd×1`, `controlledBy=sol`, gracz `red` VP=0.
- Frontend: `npm install` + `type-check` + `build` czyste. Dev-serwer Vite (5173) +
  proxy: `GET /bot/api/public/game/g/web-data` → 200, 33 pozycje. Pełny potok
  frontend → proxy → FastAPI → `build_web_data` działa.
- **82 testy zielone**, ruff + mypy --strict czyste, build frontu czysty.

**Do zrobienia dalej (następne bloki):**
- Weryfikacja wizualna renderu w przeglądarce (`/embed/{id}/map-only` lub `/game/{id}`).
  `gameId` na start jest dowolny — backend trzyma jeden stan (single-game).
- Edycja/God-Mode w nowym UI (frontend AsyncTI4 to viewer; nasz edytor trzeba dołożyć
  jako panel/akcje nad istniejącymi endpointami setup/space/planet/undo/redo).
- Opcjonalnie: STOMP WS emitujący `GameStateMessage{full:true}` dla live-sync.
- Opcjonalnie (local-first wg spec): przekierować `cdnImage()` na nasz `/static`.
- Rozważyć: `playerData` ekonomia planet / zasoby liczone realnie (teraz zera).

---

### ✅ Blok F2 — redukcja frontendu do pojedynczego widoku gry

**Decyzja użytkownika:** nie chcemy portalu AsyncTI (landing page, lista gier,
dashboard, logowanie). Chcemy JEDEN widok konkretnej gry z wszystkimi jego
komponentami (plansza + zakładki players/objectives/general + nagłówek, panele,
modale). Własny landing dorobimy później.

**Analiza zależności (context-gatherer):** prześledzono drzewo importów widoku gry
(`GameMapPage`) żeby wyciąć portal bez zepsucia planszy. Ustalono m.in.:
- `GameContextProvider` → `usePlayerData` pobiera `web-data` zwykłym (nieuwierzytelnionym)
  `fetch` — rdzeń widoku NIE wymaga logowania.
- `src/api/auth` + `src/domains/auth` są jednak importowane tranzytywnie (SecretHand,
  nagłówek, drawer). ZOSTAWIONE — degradują się łagodnie (brak użytkownika Discord =
  ukryta „ręka"; przycisk logowania lokalnie nieaktywny). Wycinanie ich = kaskada edycji.

**Usunięte (portal / legacy):**
- `pages/`: LandingPage/, GamesPage, DashboardPage, DashboardSettingsPage, LoginPage,
  MapTogglePage, EmbeddedMapPage, image-map/ (stary „OLD UI" + FoW).
- `domains/`: image-map/, dashboard/, music-video/. `src/music-video/` + `music-video.html`.
- `api/`: useCommunityStats, useMaps. `layout/PageShell`.

**Zmienione (usunięcie referencji do wyciętych części):**
- `main.tsx`: trasy zredukowane do `/` i `/game/:mapid` → `GameMapPage` (+ `/system/:id`).
  Root otwiera OD RAZU widok gry. Usunięto providerów/prefetch music-video. `gameId`
  domyślny = `"local"` (backend trzyma jeden stan, ignoruje identyfikator).
- `GameMapPage.tsx`: `gameId = params.mapid ?? "local"`; usunięto `onShowOldUI` i przełącznik
  „OLD UI" (zastąpiono `MapHeaderSwitch` → bezpośrednio `SiteHeader`).
- `NavigationDrawer.tsx`: usunięto przycisk „GO TO OLD UI" + prop `onShowOldUI`.
- `FloatingMapToolbar.tsx`: usunięto `MusicVideoButton`.
- `vite.config.ts`: usunięto build-entry `music-video.html` i wyjątek kompilatora dla music-video.
- `index.html`: tytuł/opis → Custodian Engine (branding AsyncTI usunięty; preconnect do
  `images.asyncti4.com` zostaje — to CDN grafik kafelków/jednostek).

**Rezultat (zweryfikowany E2E):**
- Frontend: `type-check` + `lint` + `build` czyste. Bundle pozbyty chunków music-video/
  dashboard (zostają tylko `index` + `SystemTilePage`).
- Live: backend (`/map/load` + `/setup/player` Sol@301) + Vite dev. Root `/` → 200 z `#root`.
  `web-data` przez proxy → 200, 33 kafelki, gracz `sol/red`. Widok gry serwuje się od razu.
- Backend bez zmian w tym bloku; 82 testy nadal zielone (QA Pythona niezmienione).

**Do zrobienia dalej:**
- Weryfikacja wizualna renderu planszy w przeglądarce (otwarcie `http://localhost:5173/`).
- Własny landing/ekran startowy (później, wg uznania).
- Edycja/God-Mode w nowym UI nad istniejącymi endpointami (setup/space/planet/undo/redo).

---

### ✅ Blok F3 — branding + sprzątanie + dokumentacja po migracji

**Branding (Custodian Engine zamiast AsyncTI4):**
- `src/shared/ui/Logo.tsx`: baner AsyncTI4 → tekstowy znak „CUSTODIAN ENGINE" (lewy róg).
- `main.tsx` (sygnatura konsoli), `GameMapPage.tsx` (tytuł zakładki), `index.html` — Custodian Engine.

**Sprzątanie cruftu po migracji:**
- `frontend/src/config.ts`: usunięto rozbicie dev/prod (działamy tylko lokalnie) oraz
  martwe pola (`mapsUrl`, `proxyMapsUrl`, `frogMapUrl`, `discordLoginUrl`). Zostają tylko
  żywe adresy: `gameDataUrl`, `botApiUrl`, `websocketUrl`, `discordRedirectUri` — z komentarzami.
- `frontend/vite.config.ts`: usunięto martwy proxy `/proxy` (nic go już nie używa).
- `frontend/README.md`: przepisany pod Custodian Engine (był README AsyncTI4).
- `README.md` (root): zaktualizowany status (Faza 1 niemal gotowa) + wiersz frontendu.

**Dokumentacja (żeby łatwo pracować dalej):**
- NOWY `docs/ARCHITEKTURA_PO_MIGRACJI.md` — mapa orientacyjna: obraz całości, jak
  uruchomić, backend/front po module, kontrakt `web-data`, tabela „co działa / luki"
  względem DoD Fazy 1, jak postawić realną grę przez API, następne kroki.

**Zidentyfikowane luki (spisane w nowym docu):**
- Brak UI edycji stanu (map string / setup / jednostki / VP) — nowy front to viewer;
  edycja tylko przez API. To największa luka do DoD Fazy 1.
- Brak szybkiego edytora jednostek na heksie (skróty „2D 1C 4F").
- Live-sync: front używa STOMP (nie wystawiamy go) → de facto refetch, nie push.

**Zweryfikowane:** type-check + lint + build frontu czyste; backend 82 testy zielone,
ruff + mypy czyste. Live: root `/` serwuje tytuł Custodian Engine, `web-data` przez proxy
= 200 (versionSchema=5, 33 kafelki, sol/red).

---

### ✅ Blok F4 — ekran startowy (landing) + endpoint `/game/new` + odświeżanie

**Cel:** własny ekran startowy sterujący setupem (liczba graczy, frakcje, map string)
zamiast portalu AsyncTI; dodatkowe sprzątanie chrome AsyncTI.

**Backend:**
- NOWY `POST /game/new` (`app.py`): tworzy grę jednym żądaniem — reset `GameState`,
  wczytanie mapy, setup wszystkich graczy. `map_string` opcjonalny (gdy brak → testowy
  `_DEFAULT_MAP_STRING`). Kolory i sloty domowe przydzielane automatycznie wg kolejności
  graczy (`_AUTO_SLOT_ORDER` z `HOME_SLOT_COLORS_6P`): gracz 1 → red/301, 2 → green/304, …
- `schemas.py`: `NewGameRequest` + `NewGamePlayer` (frakcja wymagana; player_id/kolor/slot opcjonalne).
- `tests/test_web_data.py`: testy `/game/new` (bez map stringa → testowy; za dużo graczy → 422).

**Frontend:**
- NOWY `pages/StartScreen.tsx` — ekran startowy na `/`: liczba graczy (2–6), Select frakcji
  per gracz (z `/factions`), opcjonalny map string, „Generuj i graj" → `POST /bot/game/new`
  → nawigacja na `/game`. Kolory pokazane jako podpowiedź (red/green/white/…).
- NOWY `api/useNewGame.ts` — `useFactions()` + `createNewGame()`. Baza `/bot` (NIE `/bot/api`):
  endpointy Custodian Engine są w korzeniu backendu (`/factions`, `/game/new`).
- `main.tsx`: `/` → StartScreen; `/game` i `/game/:mapid` → GameMapPage.
- Przerobiony „Refresh" (`ReconnectButton` → odświeżanie planszy): wisi na stałe i woła
  `refetch` (nie reconnect STOMP) — bo nie mamy live-sync. Etykieta „Odśwież".

**Dodatkowe sprzątanie chrome AsyncTI (wcześniej w tej sesji):**
- Usunięto Discord Login (HeaderMenu + NavigationDrawer) i martwą logikę gier/kont
  (`/my-games`), linki Dashboard/Settings. `GamesBar` bez auth.

**Zweryfikowane E2E (przez proxy Vite):** `/bot/factions` = 27 frakcji; `POST /bot/game/new`
(3 graczy, bez map stringa) = 200, 33 kafelki; web-data: `sol→red, hacan→green, xxcha→white`,
jednostki startowe na slotach (sol@301, xxcha@307). `/game` serwuje HTML. type-check + lint +
build frontu czyste; backend 84 testy zielone, ruff + mypy czyste.

**Pułapka operacyjna (znów):** osierocony backend trzymał port 8000 (`Errno 10048`) i serwował
STARY kod bez `/game/new` → proxy dawało 404. Rozwiązanie: ubicie procesu po PID z
`Get-NetTCPConnection -LocalPort 8000` i restart. Do rozważenia: health-check zwalniający port.

**Postęp DoD Fazy 1:** ekran startowy domyka „wprowadzanie stanu" dla setupu (mapa + gracze
+ flota startowa jednym kliknięciem). Zostaje edycja bieżącej gry z UI (zmiana jednostek,
VP/zasoby, Undo/Redo) — na razie przez API.

---

### ✅ Blok F5 — nowy map string, health-check portu, refresh w nagłówku, ekonomia planet

**Uwagi użytkownika + co zrobione:**
- **Nowy testowy map string** (`_DEFAULT_MAP_STRING` w `app.py`) — podany przez użytkownika
  (`23 49 77 … 62 44`). Używany, gdy ekran startowy nie poda własnego.
- **Health-check portu 8000** (`src/api/__main__.py`): przed startem Uvicorna sprawdza, czy
  port jest zajęty, i ubija osierocony proces (Windows: netstat + taskkill). Rozwiązuje
  powracającą pułapkę „Errno 10048 / stary kod". Zweryfikowane: log „Port 8000 zwolniony".
- **Przycisk „Odśwież" przeniesiony do nagłówka** (`shared/ui/HeaderRefreshButton.tsx`,
  renderowany w `SiteHeader` przez `GameMapPage`). Usunięto pływający `ReconnectButton`
  z `MapView`/`PannableMapView` (plik skasowany). Czyściej niż pływający przycisk na planszy.

**Bug ekonomii planet (znaleziony i naprawiony):** `web_data._build_planet_entry` NIE
uzupełniał zasobów/wpływów dla planet ZAJĘTYCH (tylko puste), więc kontrolowane planety
miały `resources=0 inf=0`. Dodatkowo `playerData` wysyłało zera ekonomii. Naprawione:
- `_build_planet_entry` uzupełnia staty z rejestru (jak `_empty_planet_entry`).
- `_build_player_data` sumuje zasoby/wpływy kontrolowanych planet (`_planet_economy`).
- Zweryfikowane E2E: `jord: res=4 inf=2 ctrl=sol`; panel gracza `sol: resources=4 influence=2`.
  (Wcześniej wszystko 0 — stąd „brak info na planetach".)

**Źródła danych udokumentowane (NIE kasujemy):** `docs/ARCHITEKTURA_PO_MIGRACJI.md` 6a —
`TI4_map_generator_bot/` (bot AsyncTI4 = słownik formatu `web-data`/assetów) oraz live viewer
`asyncti4.com` jako referencja renderu (gra `pbd30347`). Oba w `.gitignore`, zostają na dysku.

**O featurach ti4_web (planety z tokenami, podgląd jednostek po kliknięciu, panel gracza):**
to natywne funkcje frontendu renderowane ze STATYCZNYCH danych frontendu + dosyłanego stanu.
Działają „za darmo", gdy tylko dane się zgadzają — a po naprawie ekonomii planet dane są
kompletne (systemId, nazwy planet, kontrola, zasoby/wpływy, jednostki jako asyncId).

**QA:** backend 85 testów zielone, ruff + mypy czyste; frontend type-check + lint + build czyste.

---

### ✅ Blok F6 — fix: jednostki w panelu/dossier (pusta unitsOwned psuła lookupUnit)

**Objaw:** po kliknięciu w układ panel „System Dossier" nie pokazywał jednostek
(brak Orbit/sił na planetach, brak HITS/HP/CAP). Zasoby planet działały.

**Root cause (znaleziony przez analizę kodu frontendu):** backend wysyłał
`playerData[].unitsOwned = []` (pusta lista). W `lookupUnit` (frontend) pusta lista
jest TRUTHY, a `[].includes(id)` zawsze `False`, więc `filterUnitsFromList` odrzucał
WSZYSTKIE jednostki → `lookupUnit` zwracał `null` → `collectUnitRows` (dossier)
pomijał każdy wiersz. (Render sprite'ów na planszy NIE zależy od lookupUnit —
dlatego jednostki na kafelkach i tak się rysowały; problem był w panelu.)

**Fix:** `web_data.py` NIE wysyła już `unitsOwned`. Gdy pole jest nieobecne,
frontend rozwiązuje jednostki generycznie i frakcyjnie poprawnie. (Nigdy `[]` —
to najgorszy przypadek. Alternatywa: realne ID posiadanych jednostek.)
- Test regresji: `test_web_data_omits_empty_units_owned`.
- Zweryfikowano: klucze frakcji w `tileUnitData` == `playerData[].faction` (sol, xxcha),
  kolory rozpoznawane przez frontend → sprite'y się rozwiązują.

**Znana luka (nie-blokująca):** zielone heksy „player stats" przy planszy
(`PlayerStatsHex`) nie renderują się, bo wysyłamy `statTilePositions: {}`. To osobny
feature (dashboard frakcji liczony z pozycji stat-tile) — do zrobienia później, nie
jest to część jednostek. Patrz `docs/ARCHITEKTURA_PO_MIGRACJI.md`.

**QA:** backend 85 testów zielone, ruff + mypy czyste.

---

### ✅ Blok F7 — rezerwy jednostek (unitCounts), unitsOwned, heksy player-stats

**Uwaga użytkownika:** panel „ile jednostek zostało / na planszy / upgrade" pokazywał
złe liczby (wszystko „Upgraded", monument `NaN`); brakowało kolorowych heksów player-stats.

**Diagnoza (analiza kodu frontendu + dane żywej gry `pbd30347`):**
- Panel rezerwy czyta `playerData.unitCounts[asyncId] = {unitCap, deployedCount}` i pokazuje
  `unitCap - deployedCount`. Wysyłaliśmy `{}` → złe/NaN liczby.
- Błędne „Upgraded": `PlayerCardUnitsArea` wybiera jednostkę przez `lookupUnit`, które
  (przy pominiętym `unitsOwned`) `preferUpgradedUnit` → zwracało wariant ULEPSZONY.
- Zielone heksy: `PlayerStatsHex` zasilany `statTilePositions` (wysyłaliśmy `{}`).

**Źródło limitów (nie z pamięci):** `TI4_map_generator_bot/.../reinforcements.properties`
→ liczba par współrzędnych = limit sztuk. Spisane do `docs/RULES.md` 3 (+ monument=1).

**Zrobione (backend `web_data.py` + `unit_catalog.py`):**
- `UNIT_CAP_BY_ASYNC_ID` — zweryfikowane limity supply (gf 12, ff 10, dd/ca 8, cv/mf 4,
  dn 5, pd 6, sd 3, ws 2, fs/monument 1).
- `unitCounts` per gracz: `unitCap` z tabeli + `deployedCount` liczony z planszy
  (space + planety, per asyncId).
- `unitsOwned`: realne ID jednostek BAZOWYCH (generyczne + frakcyjne `<faction>_*`, bez
  ulepszeń) → `lookupUnit` zwraca bazowe, panel nie pokazuje błędnie „Upgraded". NIGDY [].
- `statTilePositions`: 3 najbliższe pozycje pierścienia 4 do slotu domowego (geometrycznie,
  zgodne 1:1 z AsyncTI4). Spisane do `docs/RULES.md` 4.

**Zweryfikowane E2E:** `sol cv cap=4 deployed=2`, `gf cap=12 deployed=5`; `unitsOwned`
= `carrier,cruiser,…,sol_flagship`; `statTilePositions sol=401,402,424 naaz=404,405,406`.
Backend 88 testów zielone, ruff + mypy czyste.

---

### ✅ Blok F8 — War Sun za technologią, kolejność heksów stat-area, launcher

**Uwagi użytkownika + fixy:**

1. **War Sun liczył się jak zbadany** — do `unitsOwned` trafiał generyczny `warsun`,
   mimo że wymaga technologii `ws`. Fix: `_units_owned_for_faction` filtruje jednostki
   po `required_tech_id` — pomija te, których technologii gracz NIE ma. War Sun pojawia
   się dopiero po zbadaniu `ws`; frakcje z wrodzonym (Muaat `muaat_warsun`, bez tech)
   mają go nadal. Zweryfikowane danymi żywej gry AsyncTI4 (gracze bez tech → brak warsun
   w unitsOwned, ale `ws` cap=2 zostaje).

2. **3 heksy stat-area miały złą kolejność** — frontend bierze `firstHex` = tożsamość
   frakcji (frakcja/VP/SC/sekrety w CENTRUM), `secondHex` = żetony dowodzenia (CC),
   `thirdHex` = trade goods/commodities/action cards + status ACTIVE/PASSED. Kolejność
   wyznacza tablica `statTilePositions`. Wysyłaliśmy posortowane `int` — teraz sortujemy
   wg ODLEGŁOŚCI od slotu domowego (najbliższy = centrum/frakcja). Zgodne 1:1 z AsyncTI4
   (`sol → 401,402,424`; `304 → 405,404,406`). Role heksów ustalone z `PlayerStatsArea.tsx`.

3. **Prostsze uruchamianie** — NOWE `start.cmd` (dwuklik) + `start.ps1`: jedno polecenie
   zwalnia port 8000, startuje backend i frontend w osobnych oknach (pierwszy raz robi
   `npm install`), czeka na dev-serwer i otwiera przeglądarkę. Koniec z ręcznym
   odpalaniem dwóch terminali. Opis w `docs/ARCHITEKTURA_PO_MIGRACJI.md` 2.

**Źródła (RULES.md):** limity sztuk (3) i pozycje stat-area (4) już spisane w F7.
War Sun za technologią to standardowa reguła TI4 (unit upgrade tech) — realizowana
przez `required_tech_id` z danych, nie z pamięci.

**QA:** backend 89 testów zielone, ruff + mypy czyste. Launcher zweryfikowany E2E
(oba porty nasłuchują, przeglądarka otwarta).

---

### ✅ Blok F9 — heksy stat-area: port algorytmu AsyncTI4 (pivot pierwszy)

**Uwaga użytkownika:** układ 3 heksów był inny niż oficjalny — znak frakcji trafiał
na zły heks, pozostałe dwa przesunięte. Oficjalnie: heks frakcji (symbol + VP) w CENTRUM
(pivot), a dwa pozostałe (TG/comm/AC oraz CC) po bokach.

**Znalezione źródło (nie z pamięci):** `TI4_map_generator_bot` →
`WebStatTilePositions.fromGame` → `PlayerStatsHelper.findThreeNearbyStatTiles`. Algorytm:
puste kafelki w pierścieniu ≤ ringCount+1, dobierane wg odległości do slotu domowego aż
powstanie ZWARTA trójka; zwracane jako `[pivot, sąsiad, sąsiad]` (pivot = kafelek sąsiadujący
z dwoma pozostałymi = środkowy). Frontend kładzie `firstHex`=frakcja/VP na pivocie.

**Fix:** `web_data.py` — `_build_stat_tile_positions` przepisane na port tego algorytmu
(`_three_nearby_stat_tiles`): kandydaci = puste pozycje (nie w gridzie), ring ≤ ringCount+1,
współdzielony `taken` (brak nakładania heksów między graczami), zwrot pivot-first. Wcześniej
sortowałem po odległości kubicznej i pivot nie zawsze był pierwszy.

**Zweryfikowane E2E:** 6 graczy → 18 unikalnych pozycji bez nakładania; pivot pierwszy
(`mentak 401,402,424`, `sol 405,404,406`, …), zgodne 1:1 z żywą grą AsyncTI4.
Reguła spisana do `docs/RULES.md` 4 (zaktualizowana). QA: 89 testów zielone, ruff+mypy czyste.

**Nadal otwarte (niekrytyczne):** heks CC (`secondHex`) jest pusty, bo nie liczymy jeszcze
żetonów dowodzenia (`tacticalCC/fleetCC/strategicCC = 0`) — pokaże się, gdy dodamy ich obsługę.

---

### ✅ Blok F10 — panel faz (gameState) + żetony dowodzenia (Warstwa A portu AsyncTI4)

**Cel użytkownika:** przenieść PEŁNĄ funkcjonalność AsyncTI4 na nasz tryb solo; na start
konkretnie phase box (lewy róg) i żetony dowodzenia w heksach + player stats.

**Analiza wykonalności (context-gatherer):** potwierdzona — frontend to viewer renderujący
całość z jednego dokumentu `web-data`. Podział na Warstwę A (dosłanie danych, bez logiki)
i Warstwę B (silnik faz/akcji = roadmapa M2–M6, port reguł z Javy). Pełny plan:
`docs/PORT_ASYNCTI4_PLAN.md`.

**Zrobione (Warstwa A):**
- `GameState`/`PlayerState` (`game_state.py`): dodane `tactical_cc=3, fleet_cc=3,
  strategic_cc=2, cc_reinf=8`, `passed`, `strategy_cards`.
- `web_data.py`: NOWY obiekt `gameState` (`_build_game_state`, `_to_web_phase`,
  `_active_color`) — faza w formacie frontendu (małe litery/podfazy), aktywny gracz jako
  KOLOR. Emisja CC + `scs` + `passed` w `playerData`.
- `app.py` `/game/new`: ustawia `active_player_id` = pierwszy gracz (panel podświetla kolejkę).
- Frontend: `DEFAULT_GAME_ID="local"` wyniesione do `config.ts`; `GameStatePanel` używało
  `params.mapid ?? ""` → `?? DEFAULT_GAME_ID` (inaczej czytało puste zapytanie i panel był ciemny).

**Źródła (RULES.md):** startowe CC (5, z `Player.java`), mapowanie faz (6).

**Zweryfikowane E2E:** `gameState.phase=strategy activePlayer=red` (Mentak aktywny);
CC gracza `3/3/2 reinf 8`. type-check + lint + build frontu czyste; backend 91 testów
zielone, ruff + mypy czyste.

**Dalej (Warstwa A, do włączenia):** karty strategii (display), cele/VP, prawa, liderzy.
**Warstwa B:** silnik faz/akcji — osobne bloki wg roadmapy.

---

### ✅ Blok F11 — fix flagi frakcji + edytor planszy God-Mode

**Bug (flaga frakcji na jednostkach):** `unitsOwned` zawierało i generyczny `mech`,
i frakcyjny `<faction>_mech` dla tego samego asyncId → `lookupUnit` rozwiązywał
niejednoznacznie, pokazując złą flagę (np. ghost). Fix: dla każdego asyncId wybieramy
JEDNĄ jednostkę — wariant frakcyjny ma pierwszeństwo przed generycznym (`web_data.py`
`_units_owned_for_faction`). Zweryfikowane: każda frakcja ma dokładnie swój mech/flagship.

**Edytor planszy (God-Mode, bez sprawdzania zasad):**
- Backend: `BASE_TYPE_BY_ASYNC_ID` (odwrotna mapa) w `unit_catalog.py`. NOWE endpointy
  w `app.py`:
  - `POST /system/{pos}/edit-units` — delta (+/−) jednostek w strefie (space/planeta)
    dla frakcji (asyncId). Operuje w terminach frontendu; tłumaczy asyncId→baseType,
    klucz frakcji→player_id. Ujemny wynik obcinany do 0 (usuwa).
  - `POST /units/move` — przesunięcie N jednostek między strefami/systemami.
  - Schematy `UnitEditRequest`, `UnitMoveRequest` (`schemas.py`).
- Frontend: `api/useBoardEditor.ts` (editUnit/moveUnit + invalidacja web-data).
  Komponent `SystemEditor.tsx` + CSS (styl dossier) — w stopce dossier przycisk
  „Edytuj planszę" odsłania panel: wybór gracza (SegmentedControl), strefy
  (Orbita/planety), siatka 11 typów jednostek z licznikiem i +/−. Zmiany natychmiast
  odświeżają planszę i panele.

**Zweryfikowane E2E:** add 2× cruiser @101, move 1 → 102 ⇒ 101=1, 102=1.
Backend 95 testów zielone, ruff + mypy czyste; frontend type-check + lint + build czyste.

**Uwaga:** edytor celowo NIE sprawdza zasad TI4 — to narzędzie operatora (gracze sami
pilnują legalności). Zgodne z modelem human-in-the-loop / God-Mode (spec 1.2.3).

---

### ✅ Blok F12 — Undo/Redo w UI + wygodne przenoszenie jednostek

**Undo/Redo (Event Sourcing w UI):** backend miał już `EventStore` (SQLite, Snapshot
Stack) + endpointy `/undo`/`/redo` — brakowało podpięcia w interfejsie. Dodane:
- `app.py`: `/undo`/`/redo` wołają teraz też `broadcast_map()` (spójność).
- `useBoardEditor`: akcje `undo()`/`redo()` + invalidacja web-data.
- `HeaderGameControls` (nowy): przyciski Cofnij / Ponów / Odśwież w nagłówku
  (zastąpił `HeaderRefreshButton`).
- Zweryfikowane E2E: +3 krążowniki → undo=0 → redo=3.

**Wygodne przenoszenie jednostek:** w edytorze systemu (`SystemEditor`) dodano
selektor „Przenieś do" (wyszukiwalny Select wszystkich stref: Orbita + planety
każdego systemu) + przycisk „→" przy jednostce, która ma count>0. Przenosi 1 sztukę
wybranej jednostki ze źródłowej strefy do wybranego celu (endpoint `/units/move`).
Zweryfikowane wcześniej E2E (101→102).

**Uwaga o zakresie Undo:** Event Sourcing obejmuje `GameState` (gracze, jednostki,
VP…). Mapa (`current_grid`: które systemy/kafelki domowe) jest poza historią, więc
undo cofa edycje jednostek/stanu, ale nie cofnie `/game/new` ani podmiany kafelka
domowego. Dla edycji jednostek (główny przypadek) działa w pełni.

**QA:** backend 95 testów zielone, ruff + mypy czyste; frontend type-check + lint +
build czyste.

---

### ✅ Blok F13 — panel historii (cofanie do punktu) + tryb przenoszenia „2 systemy"

**Panel historii (w menu Events):** zamiast polegać na logu zdarzeń AsyncTI4 (którego
nie produkujemy), dołożyliśmy własny `HistoryPanel` nad panelem Events. Pokazuje wszystkie
migawki Event Store z czytelnymi etykietami (Nowa gra, Edycja jednostek · 101, …) i pozwala
wrócić do dowolnego punktu jednym kliknięciem (undo/redo do punktu).
- Backend: `EventStore.history()` + `goto(seq)`; `GET /history`, `POST /history/goto/{seq}`.
  Stub `GET /api/public/game/{id}/events` → `[]` (koniec 404 w panelu AsyncTI4).
- Frontend: `useHistory` + `gotoHistory` w `useBoardEditor`; `HistoryPanel` + CSS;
  wpięty w stopkę/menu Events (`FloatingMapToolbar`). Nagłówek „Historia / Events".

**Nowy system przenoszenia „zaznacz 2 systemy":** stary dropdown w edytorze został,
ale doszedł wygodniejszy tryb mapowy:
- Przycisk „Przenieś" w nagłówku włącza TRYB PRZENOSZENIA (`appStore.moveMode`).
- Klik w kafelek = wybór ŹRÓDŁA (podświetlone na zielono), drugi klik = CEL.
- Otwiera się `MoveUnitsModal` ze wszystkimi jednostkami systemu źródłowego
  (Orbita + planety, per frakcja) — wybierasz strefę docelową i przenosisz
  (1 lub wszystkie). W trybie przenoszenia klik NIE otwiera dossier.

**Zweryfikowane E2E:** historia `#1 initial, #2 game:new, #3 edit:101:space (bieżący)`;
goto cofa jednostki; undo/redo 3→0→3. Backend 97 testów zielone, ruff+mypy czyste;
frontend type-check+lint+build czyste.

---

### ✅ Blok F14 — panel gracza: liderzy, planety, optimal/total ekonomia

**Uwaga użytkownika:** panel gracza miał martwe sekcje — liderzy (commander/hero/agent),
kontrolowane planety, optimal/total resources. Wszystkie to pola `playerData`, które
wysyłaliśmy puste/zerowe (komponenty frontendu już je renderują — brakowało danych).

**Zrobione (backend `web_data.py` + `models.py`):**
- **Liderzy:** `FactionDef.leaders` (z danych frakcji, np. `solagent/solcommander/solhero`).
  `_player_leaders` emituje `playerData.leaders` (`{id,type,tgCount,exhausted,locked,active}`)
  + `leaderIDs`. Typ z sufiksu id; start: agent gotowy, commander/hero locked. (RULES.md 8)
- **Optimal/total ekonomia:** `_planet_economy` → `_Economy` liczy optimal/flex per planeta
  wg reguły AsyncTI4 (`Planet.getOptimal*`, RULES.md 7): optimalRes = res gdy res>inf;
  optimalInf = inf gdy inf>res; flex gdy równe. Emituje `optimalResources/optimalInfluence/
  flexValue` + `tot*`.
- **Planety:** `playerData.planets` = kontrolowane planety (było już wysyłane; teraz z pełną
  ekonomią panele pokazują je sensownie).

**Zweryfikowane E2E:** Sol → liderzy `solagent(agent,unlocked), solcommander(locked),
solhero(locked)`; planeta `jord`; `res=4 inf=2 optRes=4 optInf=0`. Brak zmian we froncie
(komponenty już gotowe). Backend 98 testów zielone, ruff+mypy czyste, front type-check czysty.

---

### ✅ Blok F15 — God-Mode: edytor stanu gracza

**Cel użytkownika:** wszystkie dane graczy wysyłane i łatwo edytowalne (God-Mode), w stylu strony.

**Backend:**
- `POST /player/{player_id}/edit` (`app.py`) + `PlayerEditRequest` (`schemas.py`): patch
  dowolnych pól `PlayerState` (VP, trade_goods, commodities, tactical/fleet/strategic_cc,
  cc_reinf, passed, strategy_cards, controlled_planets, technologies, faction, color).
  Każde pole opcjonalne; tworzy gracza gdy nie istnieje. Commit → historia (Undo działa).
  Bez sprawdzania zasad.

**Frontend:**
- `useBoardEditor.editPlayer(playerId, edit)` + typ `PlayerEdit`.
- `PlayerEditorModal` (styl ds): selektor gracza (SegmentedControl), pola liczbowe ze
  stepperami +/− i polem liczbowym (VP, TG, commodities, 3× CC, rezerwa), przełącznik
  „passed", pola tekstowe (frakcja, kolor, technologie i planety po przecinku).
- Przycisk „Gracze" w nagłówku (`HeaderGameControls`) otwiera modal.

**Zweryfikowane E2E:** edycja p1 VP=5/tg=7/tacCC=1 → web-data to pokazuje; Undo cofa do
0/0/3. Backend 99 testów zielone, ruff+mypy czyste, build frontu czysty.

**Stan God-Mode (Milestone 1) — podsumowanie dostępnych edycji z UI:**
- Jednostki: dodaj/usuń per strefa (dossier → „Edytuj planszę"), przenieś (tryb „Przenieś”
  2 systemy lub select w edytorze).
- Gracz: wszystkie pola (przycisk „Gracze" w nagłówku).
- Historia: panel (menu Events) + Cofnij/Ponów/skok do punktu.

---

### ✅ Blok F16 — splash ładowania + liderzy w God-Mode (graficznie)

**1. Biały ekran przy starcie (odpowiedź: to nie bug).** Przyczyna: parsowanie ciężkiego
bundla React (~3 MB) zanim zamontuje się aplikacja. Dodany statyczny splash w `index.html`
(czysty HTML/CSS, renderuje się w pierwszej klatce): spinner + „CUSTODIAN ENGINE" +
„Ładowanie interfejsu…". React montuje do `#root` i podmienia zawartość → splash znika sam.
(Pełne przyspieszenie = code-splitting, osobny temat; splash rozwiązuje percepcję.)

**2. Liderzy w God-Mode (brakowało) + edycja graficzna (klik, nie wpisywanie).**
- Backend: `PlayerState.leader_states` (`{leader_id: locked|unlocked|exhausted}`);
  `web_data._player_leaders` czyta override; `PlayerEditRequest.leader_states`.
- Frontend: `PlayerEditorModal` ma sekcję liderów — klik na chip cykluje stan
  (zablokowany → gotowy → wyczerpany). Bez wpisywania ID.
- E2E: unlock commandera → `locked=False`, hero nietknięty.

**Uwaga o „edycji na samych panelach" (inline na mapie/kartach):** obecnie edycja graficzna
żyje w modalu „Gracze" (liczby stepperami, liderzy klikalni). Pełny inline-edit bezpośrednio
na komponentach dossier/player-card (klik w technologię/commodities/kontrolę planety w samym
panelu) to większy, wieloplikowy refactor — do zrobienia przyrostowo w kolejnych blokach.

**QA:** backend 100 testów zielone, ruff+mypy czyste; frontend type-check+lint+build czyste.

---

### ✅ Blok F17 — ustalenie: ti4_web to viewer + start silnika rozgrywki (Etap E1)

**Odpowiedź na pytanie użytkownika (dowodowo):** frontend `ti4_web` NIE ma logiki akcji
do przeniesienia. To czysty viewer — jedyne POST-y w kodzie to NASZE dodatki (`useNewGame`,
`useBoardEditor`); oryginał deleguje WSZYSTKIE akcje do Discorda (`actionsJumpLink`/
`tableTalkJumpLink` → linki do kanałów, render w `TabsControls`). Logika gry jest w Java
bocie (`TI4_map_generator_bot/.../service/*`), spleciona z Discordem — używamy jako ŹRÓDŁO
REGUŁ (port do Pythona), nie bibliotekę. Reużywalne z frontu: komponenty kart/pickerów
(`domains/cards/components/*`). Pełny plan: `docs/PLAN_PELNA_ROZGRYWKA.md`.

**Etap E1 — maszyna faz + kolejność tur (zrobione):**
- `src/core/turn_flow.py` (czyste funkcje): `turn_order` (inicjatywa z kart strategii),
  `next_unpassed_player`, `end_turn`, `pass_turn`, `next_phase`, `next_round`.
  Reguły z AsyncTI4 (`EndTurnService.findNextUnpassedPlayer`), spisane w RULES.md 9.
- Endpointy: `POST /turn/end`, `/turn/pass`, `/phase/next`, `/round/next` (commit→historia).
- Frontend: `PhaseControls` w `GameStatePanel` — przyciski „Zakończ turę / Pas / Następna
  faza / Nowa runda" w stylu panelu.
- `tests/test_turn_flow.py` (8 testów: inicjatywa, pas, koniec fazy, cykl faz, reset rundy).

**Zweryfikowane E2E:** 3 graczy, faza strategy→action; end turn red→green; pass green→white;
next phase → action. Backend 108 testów zielone, ruff+mypy czyste; frontend type-check+lint+
build czyste.

**Następne etapy** (PLAN_PELNA_ROZGRYWKA): E2 faza strategii (wybór kart) → E3 akcja
taktyczna (aktywacja/ruch/walka/inwazja/produkcja) → E4 akcje komponentowe → E5 status
(punktacja) → E6 agenda → E7 asymetria + end-game.

---
### ✅ Blok F18 — audyt i naprawa bugów game state (desync panel↔mapa + spójność)
**Kontekst:** użytkownik zgłosił, że game state ma być „wyraźny, czytelny i wolny od
bugów". Najpierw naprawiono duplikaty technologii w God-Mode (filtr oficjalnych źródeł
`base/pok/codex1-4` + dedup po nazwie w `PlayerEditorModal.tsx`). Następnie pełny audyt
serializacji web-data i endpointów edycji → 11 bugów, wszystkie naprawione.

**Naprawione bugi (wszystkie z testami regresji, RULES.md 10–12):**
- **Bug 1/2 (klucz tożsamości):** klucz grupujący jednostki/heksy/kontrolę w CAŁYM
  web-data liczony był lokalnie jako `faction or player_id` → dwaj gracze dzielący
  frakcję scalali się w jeden wpis i znikali z mapy. Wprowadzono `web_data._entity_key_map`
  (jedna mapa, klucz = frakcja gdy unikalna, inaczej `player_id`). `_resolve_player_id`
  (app.py) preferuje dokładne `player_id`, frakcję akceptuje tylko gdy jednoznaczna.
- **Bug 3 (kontrola planet — jedno źródło prawdy, opcja A):** `SystemState.planet_owners`
  jest jedynym źródłem; `playerData.planets`/ekonomia WYLICZANE z systemów
  (`_controlled_planets_from_systems`). Edycja gracza synchronizuje listę do
  `planet_owners` (`app._sync_controlled_planets`); edycja systemu od razu widać w panelu.
- **Bug 4 (phantom bucket):** jednostki nieznanego gracza są teraz widoczne pod własnym
  kluczem zamiast znikać (fallback w `_entities_from_counts`).
- **Bug 5 (nieznany baseType):** `/system/{pos}/space|planet` walidują `baseType` wobec
  katalogu (422) — koniec rozjazdu `/map` (emituje) vs web-data (pomijał).
- **Bug 6 (widmowy monument):** usunięto `"monument"` z `UNIT_CAP_BY_ASYNC_ID` (nie jest
  asyncId standardowej jednostki) → znika widmowy wiersz w panelu rezerwy.
- **Bug 7 (active↔passed / duplikat koloru):** serializer nie wskazuje aktywnego, gdy
  jest spasowany lub gdy kolor niejednoznaczny (`_effective_active_id`, `_active_color`).
- **Bug 8 (home_position spoza mapy):** `/game/new` odrzuca (422) pozycję domową spoza
  mapy — inaczej flota lądowała w systemie bez kafelka i nie renderowała się.
- **Bug 9 (kotwica heksa stat-area):** dodano `PlayerState.home_position` (ustawiane w
  setupie); `_player_home_position` kotwiczy heks do domu niezależnie od podbojów.
- **Bug 10 (prefiks id frakcji):** wybór wariantu frakcyjnego jednostki po POLU `faction`
  (nowe `UnitDef.faction`), nie po `id.startswith("{faction}_")` — koniec kolizji prefiksów.
- **Bug 11 (upgrady jednostek — zgłoszony przez użytkownika):** `_units_owned_for_faction`
  emituje wariant ULEPSZONY, gdy gracz zbadał jego `required_tech_id` (priorytet
  frakcyjny-ulepszony > frakcyjny-bazowy > generyczny-ulepszony > generyczny-bazowy).
  Wcześniej upgrade był zawsze pomijany, więc panel/mapa pokazywały statystyki bazowe
  mimo zbadanej technologii. E2E: research `ac2` → `sol_carrier`→`sol_carrier2`.

**QA:** backend 121 testów zielone (było 109; +12 regresji), ruff+mypy czyste; frontend
type-check+lint+build czyste (fix technologii). Reguły spisane w RULES.md 10/11/12.

---
### ✅ Blok E2 — faza strategii (wybór kart strategii)
**Zakres (szkielet grywalny):** pula 8 kart strategii z danych (zestaw PoK), wybór karty
przez gracza, transfer trade goods z karty do gracza, akumulacja +1 TG na niewybranych
kartach na przełomie rundy, oznaczenie karty jako zagranej (exhausted). Reguły: RULES.md 13
(źródło: `strategy_cards/pok.json` + bot `StrategyCardManager.incrementTradeGoods`,
`PickStrategyCardButtonHandler`). Inicjatywa fazy akcji wynika z wybranych kart (RULES.md 9).

**Backend:**
- Dane: `StrategyCardDef` (models.py), ładowanie w `StaticDataRegistry` + metoda
  `strategy_card_set("pok")` (8 kart z `strategyCardSets.json`). Config: `STRATEGY_CARDS_DIR`,
  `STRATEGY_CARD_SETS_PATH`.
- Model stanu: `GameState.strategy_card_tg` (TG na kartach), `GameState.speaker_id`,
  `PlayerState.exhausted_strategy_cards`.
- Logika: `src/core/strategy_phase.py` (czyste funkcje): `pick_strategy_card`,
  `play_strategy_card`, `accumulate_unpicked_tg`, `reset_strategy_cards`, `available_initiatives`,
  `picked_initiatives`.
- Endpointy: `GET /strategy/cards`, `POST /strategy/pick`, `POST /strategy/play`.
  `/round/next` rozszerzony: accumulate → reset → next_round (karty wracają do puli,
  niewybrane rosną w TG).
- web-data: `strategyCards[]` (initiative/name/id/picked/played/exhausted/tradeGoods/
  pickedByFaction) + `playerData.exhaustedSCs` wypełnione.

**Frontend:**
- `useStrategyCards` + `pickStrategyCard`/`playStrategyCard` w `useBoardEditor` (refresh
  inwaliduje też `strategyCards`).
- `StrategyCardPicker` w `GameStatePanel` (faza strategii): krążek inicjatywy w barwie karty,
  nazwa, odznaka TG, przyciski-ikony frakcji do przydziału + „Zagraj"/„zagrana".

**QA:** backend 139 testów zielone (było 121; +11 `test_strategy_phase.py` +7 API w
`test_web_data.py`), ruff+mypy czyste; frontend type-check+lint+build czyste.
**Następny etap:** E3 — akcja taktyczna (aktywacja → ruch → walka → inwazja → produkcja).

---
### ✅ Blok D1 — źródła danych: codexy + thunders_edge, dedup erraty, planety thunders_edge
**Kontekst/ustalenie (RULES.md 14/15):** użytkownik włączył thunders_edge zakładając, że
zawiera zmiany z codexów — audyt danych to OBALIŁ. thunders_edge to 13 nowych technologii
obok, nie nadbudowa; oficjalne erraty Ω/ΩΩ są tylko w codex1/codex4. Decyzja: codexy
pozostają włączone (`base, pok, codex1-4, thunders_edge`), inaczej X-89/Magen byłyby starsze.

**Zmiany:**
- `enabled_sources.json`: przywrócone codexy + thunders_edge.
- Dedup erraty w God-Mode pickerze (`PlayerEditorModal.tsx`): zamiast dedupu po nazwie —
  klucz rodziny (nazwa bez Ω/ΩΩ) + priorytet źródła (codex4 > codex1 > base). Zweryfikowane:
  X-89 i Magen zwijają się do wersji ΩΩ (codex4), 102 techy → 98 po dedupie.
- Planety thunders_edge (pole `planetTypes` zamiast `planetType`): backend `PlanetDef`
  trzyma oba pola; frontend liczy typ efektywny (`planetType ?? planetTypes[0]`) w
  `PlanetDetailsCard` i `planetCardStyle.ts` — kolor/etykieta/ikona frakcji działają.
  Grafiki/opisy planet thunders_edge nie istnieją w danych (nie do wygenerowania).

**QA:** backend 139 testów zielone (thunders_edge: 125 jednostek/160 planet/231 systemów),
ruff+mypy czyste; frontend type-check+lint+build czyste.

---
### ✅ Blok R1 — refaktor warstwy API (czytelność przed E3)
**Cel:** `app.py` urósł do 849 linii (27 endpointów + 37 funkcji w jednej `create_app`,
~44 miejsca mutujące stan W ENDPOINTCIE). Przed silnikiem taktycznym (E3) i AI groził
chaosem. Spłata długu bez zmiany zachowania (139 testów jako siatka bezpieczeństwa).

**Zmiany (tylko przeniesienie/rozdzielenie, zero nowej logiki):**
- **`core/board_edit.py`** (nowy, ~300 l.) — czyste funkcje God-Mode wyciągnięte z `app.py`:
  `resolve_player_id`, `edit_units`, `move_units`, `set_space_units`, `set_planet_units`,
  `sync_controlled_planets`, `edit_player`. Bez importów HTTP — testowalne i gotowe dla AI.
- **`app.py`** 849 → ~100 linii: cienka fabryka (montaż routerów + WS + static + CORS).
- **`api/context.py`** — `AppContext` (service/manager/registry/current_grid + broadcast_map),
  zależność `get_ctx`. Rozwiązuje dostęp routerów do współdzielonych obiektów.
- **`api/serializers.py`** — `build_map_view` + stałe setupu wyjęte z `app.py`.
- **`api/routers/`** — 6 routerów tematycznych: `game` (stan/mapa/web-data/new/setup),
  `board` (jednostki/ruch), `players`, `flow` (tury/fazy E1), `strategy` (E2), `history`.
- `pyproject.toml`: ruff `extend-immutable-calls` dla `fastapi.Depends/Query/Path/Body`
  (wzorzec frameworka, nie błąd B008).

**Zasada utrwalona (ARCHITEKTURA_KODU.md §4):** reguły w `core/` (czyste funkcje), endpoint
w `api/routers/` tylko woła core + commit/broadcast + mapuje `ValueError`→HTTP. Przy E3
dochodzi `core/tactical.py` + `api/routers/tactical.py` — bez puchnięcia `app.py`.

**QA:** 139 testów zielone (bez zmian — zachowanie identyczne), ruff+mypy czyste (46 plików).

---
### ✅ Blok S1 — poprawki setupu: liderzy Keleres, wybór tech, home off-board
Trzy mechaniki setupu zweryfikowane na danych AsyncTI4 (RULES.md 16/17) i zaimplementowane.

**1. Liderzy Keleres (bug) — fix.** `_player_leaders` zgadywał typ lidera po końcówce id;
`keleresherokuuasi` nie kończy się na „hero" → był błędnie agentem (odblokowanym). Naprawa:
typ czytany z POLA `type` danych lidera. Dodano `LeaderDef` + ładowanie liderów do
`StaticDataRegistry` (`config.LEADERS_DATA_DIR`). Wszystkie 3 warianty Keleres: agent/
commander/hero z poprawnym hero (locked). Keleres: system/planety były OK — tylko liderzy.

**2. Wybór technologii startowej.** 6 frakcji nie ma stałych tech, gracz wybiera N z opcji:
Winnu (1z8), Argent (2z3), Last Bastion/Firmament/Crimson/Ral Nel (TE, 1z4). Model:
`FactionDef.starting_tech_options/starting_tech_amount`; `faction_setup.resolve_starting_tech`
(walidacja liczności + dozwolonych opcji, fallback = pierwsze N dla quick-startu). API:
`starting_tech` w żądaniu setupu/new-game; `/factions` zwraca opcje. UI: `StartingTechPicker`
(MultiSelect) na ekranie startowym, gdy frakcja wymaga wyboru.

**3. Home system off-board: Ghost of Creuss + Crimson Rebellion.** Obie mają dom poza
planszą: brama na slocie (Ghost sys 17 Delta / Crimson sys 94 Epsilon), prawdziwy dom w
rogu obszaru gry (Ghost sys 51 z planetą creuss / Crimson sys 118 z ahkcreuxx). Reguła
z bota (`PlayerSetupService`): róg `tr/br/bl` wg slotu domowego, kolizja → flip tr↔br.
`faction_setup.OFF_BOARD_HOME` + `off_board_corner`; router kładzie bramę na slocie i dom
off-board (syntetyczny heks, sąsiedztwo przez wormhole), `apply_setup_to_state` dostaje
`unit_position`/`unit_system_id`. Frontend viewer już zna piksele `tr/br/bl` — render działa.

**QA:** backend 148 testów zielone (+9), ruff+mypy czyste (46 plików); frontend
type-check+lint+build czyste. Reguły: RULES.md 16/17.


---
### ✅ Blok A1 — panel gracza: zdolności frakcji, technologie frakcyjne, przełomy
**Cel użytkownika:** AsyncTI4 wypisuje na karcie gracza także zdolności frakcji
(abilities), technologie rasowe (faction tech) i przełomy (breakthrough) w odpowiednich
stanach (zbadane/niezbadane, locked/exhausted). Dodać emisję tych danych do web-data —
frontend (viewer) już je renderuje, brakowało tylko danych w dokumencie.

**Analiza (context-gatherer + kod frontu):** `PlayerData` (types.ts) oczekuje pól
`abilities: string[]`, `factionTechs: string[]`, `notResearchedFactionTechs: string[]`
oraz `breakthrough?: {breakthroughId, unlocked, exhausted, tradeGoodsStored}`. Render:
`PlayerDeckRow.tsx` (sekcja abilities — komponenty `Ability`/`Tech`, niezbadane
wyszarzone) + `Breakthrough.tsx`. Dane w assetach: `abilities/*.json` (pole `faction`),
`technologies/*.json` (pole `faction`), `breakthroughs/*.json` (pole `faction`). Reguła
spisana w RULES.md 18.

**Backend (dane/modele w core, cienka emisja w web_data — zgodnie z ARCHITEKTURA_KODU):**
- `config.py`: `ABILITIES_DATA_DIR`, `BREAKTHROUGHS_DATA_DIR` (TECHNOLOGIES już było).
- `models.py`: `FactionDef.abilities` + `FactionDef.faction_tech` (alias `factionTech`);
  nowe modele `AbilityDef`, `TechnologyDef`, `BreakthroughDef`.
- `registry.py`: ładowanie `abilities`/`technologies`/`breakthroughs` (filtr po `source`).
  Aktywne źródła: 73 zdolności, 102 technologie, 31 przełomów.
- `game_state.py`: `PlayerState.breakthrough_unlocked/exhausted/tg` (stan przełomu).
- `web_data.py`: `_faction_abilities`, `_faction_techs` (rozdział zbadane↔niezbadane),
  `_player_breakthrough`; emisja `abilities`/`factionTechs`/`notResearchedFactionTechs`/
  `breakthrough` w `_build_player_data`.

**Zweryfikowane E2E:** Arborec → `abilities=[mitosis]`, `factionTechs=[bio,lw2]`; po
zbadaniu `bio` → `notResearchedFactionTechs=[lw2]`, `bio` w `techs`; `breakthrough=
{arborecbt, unlocked=F, exhausted=F, tgStored=0}` (stan z PlayerState).

**QA:** backend 153 testy zielone (+3 regresji w test_web_data.py), ruff + mypy czyste.
Frontend bez zmian (viewer już renderuje te pola). Reguła: RULES.md 18.


---
### ✅ Blok E3·T1 — akcja taktyczna: aktywacja systemu + maszyna kroków (fundament)
**Cel użytkownika (decyzja projektowa):** silnik PROWADZI przez akcję taktyczną, ale
NIE waliduje reguł — gracze grają fizycznie (stół/Tabletop) i wprowadzają wynik. Asystent
stołu, nie sędzia. Walka = przyszłe okno z ręcznym wpisywaniem trafień + pomoce liczbowe
(bez rzucania). T1 to fundament: aktywacja systemu + FSM kroków.

**Analiza źródła (context-gatherer × AsyncTI4 bot):** model kontroli potwierdzony —
`UnitHolder.controlList` (addControl czyści poprzednika = jeden właściciel), Space vs Planet
jako osobne holdery; żeton dowodzenia w `Space.ccList`, kładziony z puli taktycznej
(`CommandCounterHelper.addCC` useTactic → `setTacticalCC-1`), globalny `Game.activeSystem`.
Kontrola przestrzeni LICZONA z obecności statków (brak osobnego pola). Bot NIE waliduje
twardo zasięgu/capacity/fleet — generuje przyciski, ufa graczowi (zgodne z naszym modelem).
Stan „planeta gracza A + przestrzeń gracza B" legalny. Reguła spisana w RULES.md 19.

**Model (game_state.py):**
- `TacticalStep` (enum): ACTIVATION/MOVEMENT/SPACE_CANNON/SPACE_COMBAT/INVASION/PRODUCTION.
- `SystemState.command_tokens: list[player_id]` — żetony dowodzenia w przestrzeni (aktywacja).
- `GameState.active_system`, `GameState.tactical_step` — aktualnie aktywowany system + krok FSM.

**Core (czyste funkcje):**
- `core/tactical.py` (NOWY): `activate_system` (kładzie CC aktywnego gracza, ustawia
  active_system, tactical_step=MOVEMENT, tactical_cc-1; idempotentne; ValueError gdy brak
  aktywnego gracza), `next_step` (sekwencja; po PRODUCTION kończy akcję), `set_step`
  (skok do kroku), `end_tactical_action` (czyści active_system/step; żeton zostaje).
- `core/board_edit.py`: `place_command_token`/`remove_command_token` (God-Mode CC bez reguł,
  bez zużycia puli).

**API (routers/tactical.py — NOWY):** `POST /tactical/activate`, `/tactical/step/next`,
`/tactical/step/set`, `/tactical/end` (envelope); `POST`/`DELETE /system/{pos}/command-token`
(God-Mode, MapView). Zarejestrowany w `app.py`. Schematy: `ActivateSystemRequest`,
`TacticalStepRequest`, `CommandTokenRequest`.

**web-data:** `gameState.activeSystem` + `gameState.tacticalStep` (nasze rozszerzenie — panel
taktyczny w T2 odczyta; viewer AsyncTI4 ignoruje); `tileUnitData[pos].ccs` wypełnione z
`command_tokens` (klucz tożsamości = frakcja, spójnie z jednostkami — frontend już renderuje
żetony dowodzenia na kafelku przez `CommandCounterLayer`).

**Zweryfikowane E2E:** aktywacja Sol@101 → ccs=[sol], activeSystem=101, step=MOVEMENT,
tacCC 3→2; next_step→SPACE_CANNON; end czyści (żeton zostaje). God-Mode CC add/remove.
Backend 165 testów zielone (+12: test_tactical.py +9, test_api.py +3 wliczone), ruff+mypy czyste.

**Następny blok (T2):** panel akcji taktycznej w UI (sterowanie krokami; ruch przez
istniejący tryb przenoszenia God-Mode). Potem T3 (okno walki + pomoce), T4 (inwazja+produkcja).


---
### ✅ Blok E3·T2 — panel akcji taktycznej w UI (sterowanie krokami + aktywacja klikiem)
**Cel:** widoczny panel prowadzący przez kroki akcji taktycznej; aktywacja systemu przez
klik w kafelek; ruch jednostek dalej istniejącym trybem przenoszenia God-Mode (bez reguł).

**Frontend:**
- `state/appStore.ts`: nowy tryb `activateMode` + `activateRequest`/`pickActivateTile`/
  `clearActivateRequest`/`toggleActivateMode`. Wzajemnie wykluczający z `moveMode` (jeden
  tryb klikania naraz).
- `domains/map/components/MapTile.tsx`: klik w kafelek w trybie aktywacji zgłasza pozycję
  (`pickActivateTile`) zamiast otwierać dossier; kursor „crosshair" też dla aktywacji.
- `api/useBoardEditor.ts`: akcje taktyczne `activateSystem`, `tacticalNextStep`,
  `tacticalSetStep`, `endTactical`, `placeCommandToken` (POST do endpointów T1 + refresh
  web-data).
- `entities/data/types.ts`: `GameState.tacticalStep?` (rozszerzenie kontraktu; viewer
  AsyncTI4 to ignoruje, nasz panel odczytuje przez `useGameState` = selektor web-data).
- `domains/game-shell/components/GameStatePanel.tsx`: nowy `TacticalActionPanel`
  (widoczny w fazie akcji). Brak aktywnego systemu → przycisk „Aktywuj system" włącza tryb
  klikania; po kliknięciu kafelka aktywuje (jednorazowo, przez efekt na `activateRequest`).
  Akcja trwa → ścieżka kroków (Ruch/Działa/Walka/Inwazja/Produkcja) + „Następny krok" /
  „Zakończ akcję". Ruch realizuje istniejący tryb „Przenieś".

**Zweryfikowane:** frontend type-check + lint + build czyste; backend 165 testów (bez zmian,
T2 to wyłącznie UI nad endpointami T1), ruff+mypy czyste.

**Następny blok (T3):** okno walki (asystent trafień — ręczne wpisywanie + pomoce liczbowe
z UnitDef, bez rzucania), `core/combat.py`.


---
### ✅ Blok E3·T3 — okno walki (asystent trafień) + pomoce liczbowe
**Cel użytkownika:** gdy w systemie są statki ≥2 graczy → przycisk „Walka" otwiera okno,
w którym gracze RĘCZNIE wpisują trafienia (odejmują zniszczone jednostki). Zero rzucania —
rzuty i trafienia ustalają przy stole. Obok pomoce liczbowe (ile kości, trafia na X+,
oczekiwane trafienia). Reguła: RULES.md 20 (statystyki z UnitDef).

**Core (`core/combat.py` — NOWY, czyste funkcje, zero mutacji):**
- `resolve_unit_variant(registry, faction, techs, base_type)` — wybór wariantu jednostki
  gracza (frakcyjny/ulepszony) wg priorytetu + wymaganej technologii (spójne z web_data 10).
- `space_combat_participants` / `ground_combat_participants` — uczestnicy walki (statki w
  przestrzeni / jednostki naziemne na planecie); zwrot tylko gdy walczących ≥2.
- Pomoce: `expected_hits = count * die_count * (11 - hits_on) / 10`; jednostki bez wartości
  walki (PDS/dok) pomijane. Dataclasses `UnitCombat`/`PlayerCombat`.

**API (`routers/tactical.py`):** `GET /tactical/combat/{pos}?planet=` — uczestnicy + pomoce
(DTO `CombatHelpResponse`/`CombatSideHelp`/`CombatUnitHelp`, aliasy camelCase). Klucz strony =
tożsamość (frakcja), spójny z web-data (`web_data.entity_key_map` — nowy publiczny alias).
Usuwanie zniszczonych = istniejący `edit-units` (delta -1), nie osobny endpoint.

**Frontend:**
- `api/useBoardEditor.ts`: `useCombatHelp(position, planet)` (+ typy CombatHelp*); refresh
  inwaliduje też `["combat"]`.
- `state/appStore.ts`: `combatTarget` + `openCombat`/`closeCombat`.
- `domains/map/components/CombatModal.tsx` (NOWY): dwie strony obok siebie, jednostki z
  pomocami (X+ ×kości · ~expected) + przycisk „−1" (edit-units delta -1), suma strony
  (kości · ~trafienia). Montowany w `GameMapPage`.
- `GameStatePanel` → `TacticalActionPanel`: przycisk „Walka" (gdy aktywny system ma statki
  ≥2 graczy) otwiera okno dla aktywnego systemu.

**Zweryfikowane E2E:** sol(2×cruiser,1×destroyer) vs hacan(1×dn,3×ff) w 101 → combat help:
cruiser 7+ exp 0.8, p1 total_dice 3; wariant frakcyjny (sol_carrier) rozpoznany; 1 gracz →
brak walki. Backend 171 testów zielone (+6), ruff+mypy czyste; frontend type-check+lint+build czyste.

**Następny blok (T4):** inwazja (commit piechoty + ground combat tym samym oknem + przejęcie
kontroli planety) + produkcja (pomoc kosztu z UnitDef.cost).


---
### ✅ Blok E3·T4 — inwazja (ground combat + przejęcie planety) + produkcja (pomoc kosztu)
**Cel:** domknięcie sekwencji akcji taktycznej. Krok inwazji: walka naziemna tym samym
oknem walki (per planeta) + przejęcie kontroli planety po wygranej. Krok produkcji: pomoc
liczbowa (dostępne zasoby + koszty jednostek). Wszystko bez walidacji — gracz decyduje.
Reguły: RULES.md 21 (kontrola planety), 22 (produkcja).

**Core (`core/tactical.py`):**
- `capture_planet(state, grid, position, planet, faction_key)` — nadpisuje
  `planet_owners[planet]` (jeden właściciel; reguła `UnitHolder.addControl` AsyncTI4).
- `production_help(state, registry, player_id)` → `ProductionHelp`: dostępne zasoby (suma
  `PlanetDef.resources` kontrolowanych planet) + koszty jednostek (`UnitDef.cost`, wariant
  przez `combat.resolve_unit_variant`); fighter/infantry oznaczone jako produkcja ×2
  (`_DUAL_PRODUCTION`). Ground combat: istniejące `combat.ground_combat_participants`.

**API (`routers/tactical.py`):** `POST /tactical/system/{pos}/capture` (przejęcie planety,
MapView); `GET /tactical/production?faction=` (pomoc produkcji). DTO `CapturePlanetRequest`,
`ProductionHelpResponse`/`ProducibleUnitHelp`. Walka naziemna: istniejące
`GET /tactical/combat/{pos}?planet=`.

**Frontend:**
- `useBoardEditor`: `capturePlanet(position, planet, faction)` + `useProductionHelp(faction)`
  (+ typy); refresh inwaliduje też `["production"]`.
- `CombatModal`: w walce naziemnej (planet ustawione) przycisk „Przejmij <planeta>" dla
  każdej strony → `capturePlanet`.
- `TacticalActionPanel`: krok INVASION → przyciski planet aktywnego systemu (otwierają okno
  walki naziemnej); krok PRODUCTION → `ProductionHelpRow` (zasoby aktywnego gracza + koszty).

**Zweryfikowane E2E:** capture nadpisuje właściciela (hacan→sol, controlledBy=sol w web-data);
production_help Sol → zasoby 4 (Jord), cruiser cost 2.0, fighter/infantry ×2. Backend 175
testów zielone (+4), ruff+mypy czyste; frontend type-check+lint+build czyste.

**E3 — status:** sekwencja akcji taktycznej kompletna jako asystent stołu (aktywacja → ruch
istniejącym trybem → walka kosmiczna/naziemna oknem-asystentem → przejęcie planety →
produkcja z pomocą kosztu → zakończenie). Zero walidacji reguł — zgodnie z decyzją
projektową. Space cannon to krok FSM bez dedykowanego okna (operator robi ręcznie; PDS mają
spaceCannonHitsOn w danych — ewentualne okno do dołożenia później, jak dla walki).
**Dalej (PLAN_PELNA_ROZGRYWKA):** E4 akcje komponentowe → E5 status (punktacja) → E6 agenda →
E7 asymetria frakcyjna + end-game.


---
### ✅ Blok E3·fix — kontrola planety przy stawianiu jednostek (auto)
**Zgłoszenie użytkownika:** stawianie statków/jednostek nie zmieniało statusu kontroli —
gracz nie pojawiał się w „kontrolowanych planetach".

**Root cause (analiza kodu + AsyncTI4):** `board_edit.edit_units`/`move_units` NIE dotykały
`planet_owners`. W AsyncTI4 po każdej zmianie jednostek wołane jest
`AddPlanetToPlayAreaService.addPlanetToPlayArea`, które automatycznie nadaje kontrolę.
Brakowało nam odpowiednika. web-data liczy kontrolowane planety wyłącznie z `planet_owners`,
więc panel się nie aktualizował.

**Fix (reguła z AsyncTI4, RULES.md 23):** `board_edit.recompute_planet_control(system, planet)`
— po zmianie jednostek na planecie: zbierz graczy z jednostkami naziemnymi/strukturami
(myśliwce/statki pomijane, `is_space_unit`); dokładnie jeden → nadaj kontrolę (nadpisuje
poprzednika); 0 lub ≥2 → bez zmiany (kontrola lepka). Wpięte w `edit_units`, `move_units`
(strefa źródłowa i docelowa) i `set_planet_units` (gdy brak jawnego `owner_id`). Statki w
przestrzeni (`space`) nigdy nie zmieniają kontroli planet.

**Zweryfikowane:** piechota → kontrola; usunięcie piechoty → kontrola zostaje (lepka);
statki w przestrzeni → brak kontroli planety; koegzystencja (2 kolory) → bez zmiany;
wycofanie jednego z dwóch → przejęcie przez drugiego; ruch piechoty → kontrola w celu.
Backend 180 testów zielone (+5 regresji), ruff+mypy czyste. Frontend bez zmian (web-data
już czyta `planet_owners`).


---
### ✅ Blok E1·turn-ux — przebudowa tur: speaker order + inicjatywa + UI panelu tury
**Cel użytkownika:** wyraźne, planszówkowe tury — widać CZYJA tura i że on rusza/wybiera,
przycisk „Zakończ turę". W fazie strategii wybór kart idzie w SPEAKER ORDER (od mówcy,
zegarowo), a w fazie akcji kolejność wg INICJATYWY kart. UI zgodne ze standardami strony,
wygodne. Filozofia: asystent stołu, nie sędzia (podpowiada kolejność, nie blokuje twardo).

**Reguła (RULES.md 24):** dwie różne kolejności. Faza strategii = speaker order (mówca
pierwszy, zegarowo wg kolejności miejsc). Faza akcji/status/agenda = inicjatywa (najniższy
numer karty pierwszy, RULES.md 9). Źródło: LRR „Strategy Phase" + AsyncTI4.

**Model (`game_state.py`):** `GameState.seating_order: list[str]` — kolejność miejsc przy
stole (ustalana przy nowej grze z kolejności podanych graczy). `speaker_id` = mówca (start =
pierwszy gracz). Speaker order = rotacja seating_order od mówcy.

**Core:**
- `strategy_phase.py`: `speaker_order` (rotacja od mówcy), `next_strategy_picker` (następny
  bez karty w speaker order, od mówcy). `pick_strategy_card` po wyborze przestawia
  `active_player_id` na następnego pickera (None gdy wszyscy wybrali). `reset_strategy_cards`
  ustawia aktywnego na mówcę (nowa faza strategii zaczyna mówca).
- `turn_flow.py`: `next_phase` wchodząc w STRATEGY ustawia aktywnego mówcę (picker),
  w ACTION — gracza o najniższej inicjatywie (bez zmian), status/agenda → None.
  `next_round` ustawia aktywnego mówcę (po reset_strategy_cards w flow.py).

**API:**
- `game.py` `/game/new`: zapisuje `seating_order` (kolejność graczy), `speaker_id` =
  pierwszy, `active_player_id` = pierwszy picker (mówca). `/setup/player` dopisuje gracza
  do seating_order i ustawia mówcę/aktywnego, gdy to pierwszy gracz.
- `flow.py` `/speaker/set` (NOWY, `SetSpeakerRequest`): ustawia mówcę; w fazie strategii
  przestawia, kto wybiera. Operator może nadpisać mówcę (asystent, nie sędzia).
- `web_data.py` `gameState`: nowe pola `speaker` (kolor) + `seatingOrder` (lista kolorów);
  `playerData[].isSpeaker` wypełniane prawdziwie. Helper `_color_of` (jednoznaczny kolor).

**Frontend (`GameStatePanel.tsx` + CSS):**
- Picker kart strategii przebudowany: wyraźny baner „Wybiera kartę: [gracz]" w barwie gracza;
  karty to duże, klikalne wiersze — klik przydziela kartę AKTYWNEMU graczowi i tura wyboru
  przechodzi sama do następnego (speaker order). Wybrane karty wygaszone, pokazują właściciela.
  Rząd „Mówca" (chipy frakcji) pozwala ustawić mówcę (operator).
- `buildSeats` sortuje wg fazy: strategia → speaker order (z `gameState.seatingOrder`),
  reszta → inicjatywa. `TurnOrder` z etykietą kolejności (PL: rusza/wybiera/czeka/spasował/
  wybrał) i wyraźnym podświetleniem aktywnego miejsca w barwie gracza.
- `PhaseControls`: główny, wyróżniony przycisk „Zakończ turę" (faza akcji) + „Pas";
  sterowanie fazami (Następna faza / Nowa runda) w osobnym, cichszym rzędzie (operator).
- `types.ts`: `GameState.speaker?` + `seatingOrder?`. `useBoardEditor.setSpeaker`.

**Zweryfikowane E2E (3 gracze sol/hacan/xxcha = red/green/white, mówca red):**
- Faza strategii: aktywny = mówca (red); wybór rotuje red→green→white→(None, wszyscy wybrali).
- Przejście do akcji: aktywny wg inicjatywy (green miał kartę 1 = pierwszy); end turn
  green→red→white wg inicjatywy. Zmiana mówcy na p3 (white) → aktywny=white, seating zachowany.
- Backend 187 testów zielone (+7: speaker order, rotacja wyboru, next_phase/next_round
  z mówcą), ruff+mypy czyste; frontend type-check+lint+build czyste.


---
### ✅ Blok UX·dnd — drag-and-drop przenoszenia jednostek na mapie
**Cel użytkownika:** szybkie, wygodne, intuicyjne przenoszenie jednostek — drag-and-drop.
Przeciągasz jednostkę z kafelka/strefy na inny kafelek lub planetę; dla zgrupowanych
(piechota `gf`, fightery `ff`, mechy `mf` — stos >1) po upuszczeniu pyta „ile przenieść".

**Analiza (context-gatherer):** mapa to HTML+CSS (divy z `transform: scale`), NIE SVG/canvas;
pan przez bibliotekę `dragscroll` na natywnym scrollerze (każdy mousedown+ruch przewija);
brak jakiejkolwiek biblioteki DnD w projekcie. Jednostki renderuje `UnitStack` (sprite i
badge) — ma już `faction`, `entityId`(asyncId), `count`, a strefę daje `stackHolder(stack)`.
Backend przenoszenia `POST /units/move` gotowy (obcina count, przelicza kontrolę planet).

**Implementacja (frontend, backend bez zmian):**
- `appStore.ts`: stan `unitDrop` (zamiar przeniesienia czekający na „ile przenieść") +
  `beginUnitDrop`/`clearUnitDrop`.
- `hooks/useUnitDrag.ts` (NOWY): DnD na pointer events. `setPointerCapture` na sprite +
  próg ruchu `DRAG_THRESHOLD=8px` odróżnia przeciąganie od kliknięcia (krótki ruch = klik →
  dossier); `preventDefault`/`stopPropagation` blokuje pan podczas dragu. Cel z DOM pod
  kursorem (`elementFromPoint`: kafelek `id="tile-*"`, planeta `data-search-key="planet:*"`,
  inaczej orbita `space`). Upuszczenie w inne miejsce: 1 szt. → `moveUnit` od razu; stos →
  `beginUnitDrop` (okno ilości). `onClickCapture` gasi klik po udanym dragu (żeby nie
  otwierał dossier).
- `UnitDragGhost.tsx` + CSS (NOWE): „duch" jednostki podążający za kursorem, portal do
  `document.body` (poza `transform: scale` mapy), `pointer-events: none`.
- `UnitStack.tsx`: podpięcie handlerów pointer na wrapper sprite'a ORAZ badge (piechota/
  fightery to badge) przez prop `tilePosition`; klasa `.draggable` (kursor grab,
  `touch-action: none` dla dotyku). `UnitImagesLayer` przekazuje `tilePosition=mapTile.position`.
- `MoveQuantityModal.tsx` (NOWY): pytanie „ile przenieść" ze stanu `unitDrop` — ikona
  jednostki, skąd→dokąd, `NumberInput` + szybkie przyciski (1 / połowa / wszystkie) +
  „Przenieś N". Domyślnie całość. Montowany w `GameMapPage`.

**Zweryfikowane:** backend `/units/move` dla scenariuszy DnD — 2×ff orbita 301→302 (między
kafelkami) i 3×gf Jord→orbita 301 (rozdzielenie stosu) działają, kontrola planet przeliczana.
Frontend type-check+lint+build czyste; backend 187 testów zielone (bez zmian core), ruff+mypy
czyste. DnD aktywny tylko dla realnych jednostek poza replayem. Reguła/konwencja: RULES.md 25.

**Uwaga:** istniejący tryb „Przenieś" (zaznacz 2 systemy + MoveUnitsModal) zostaje jako
alternatywa; DnD to szybsza ścieżka dla typowych przeniesień. Duch pokazuje asyncId jako chip
(fallback) — sprite'owy duch do dopieszczenia później.


---
### ✅ Blok UX·dnd-fix — drag jednostek: nie panuje mapy + chowa tooltip
**Zgłoszenie użytkownika:** DnD działa, ale (1) tooltip jednostki nie znika podczas
przeciągania (zasłania), (2) chwytając jednostkę przesuwa się CAŁA plansza (pan).

**Root cause:** `dragscroll` binduje NATYWNY `mousedown` (bubbling) na kontenerze mapy i
na nim startuje pan. Poprzednie DnD używało React `onPointerDown` + `stopPropagation`, co
NIE zatrzymuje natywnego mousedown — pan ruszał mimo to. Tooltip był niezależny od stanu dragu.

**Fix (przepisany `useUnitDrag.ts`):**
- Start gestu przez WŁASNE natywne listenery w fazie CAPTURE na sprite'cie
  (`mousedown`/`touchstart`) z `stopPropagation` — zdarzenie nie dociera do dragscroll, więc
  chwyt jednostki nie panuje mapy. Ruch/koniec na `window` (pointermove/up/cancel), próg 8px
  odróżnia drag od kliku. `dragRef` (callback ref) łączony z `flightRef` w `UnitStack`.
- Tooltip: nowa flaga `appStore.isDraggingUnit` (+ `setDraggingUnit`), ustawiana po
  przekroczeniu progu. `useTabsAndTooltips` chowa tooltip, gdy flaga true, i nie planuje
  nowego w trakcie dragu (dotyczy obu widoków — MapView i PannableMapView).
- Kompromis (świadomy): natywny `stopPropagation` na sprite'cie blokuje też React
  `onUnitSelect` (zaznaczenie frakcji przy mousedown) dla jednostek — chwyt = przenoszenie.
  Dossier nadal otwiera klik (`onUnitClick`/`click`), gaszony tylko tuż po udanym dragu.

**Zweryfikowane:** frontend type-check+lint+build czyste; aplikacja startuje (dev 5174,
`/game` 200, web-data przez proxy 33 kafelki, sol/hacan). Backend bez zmian. Reguła: RULES.md 25.


---
### ✅ Blok UX·dnd-fix2 — DnD jednostek: koniec zaznaczania grafiki „jak w przeglądarce"
**Zgłoszenie użytkownika:** podczas przeciągania często zaznacza się grafika (sprite'y/
kafelki podświetlone jak zaznaczony obrazek/tekst), przez co gest przestaje działać.

**Root cause:** sprite jednostki to `<img>` — domyślnie zaznaczalny (`user-select`) i z
natywnym HTML5 image-drag (duch obrazka przeglądarki). Szybkie szarpnięcie uruchamiało
drag-select / image-drag zamiast naszego DnD.

**Fix (trzy warstwy):**
- CSS `.draggable` + `.draggable img` (`UnitStack.module.css`): `user-select:none`,
  `-webkit-user-select:none`, `-webkit-user-drag:none`.
- `useUnitDrag.ts`: na sprite'cie natywny `dragstart`→`preventDefault` (ubija HTML5
  image-drag); na starcie realnego przeciągania dodaje `document.body.classList`
  `dragging-unit`, zdejmuje na końcu/anulowaniu.
- `ds/base.css`: `body.dragging-unit, body.dragging-unit *` → `user-select:none !important`
  (globalnie na czas gestu — szarpnięcie poza sprite nie zaznacza sąsiednich kafelków).

**Zweryfikowane:** frontend type-check+lint+build czyste. Backend bez zmian. Reguła: RULES.md 25.


---
### ✅ Blok UX·dnd-feel — podświetlenie celu + statki nie na planety + gotowość pod bota
**Cel użytkownika:** (1) planszówkowe podświetlenie kafelka-celu przy przeciąganiu;
(2) statki NIGDY na planetach (tylko piechota/mechy/struktury na planecie); (3) logika
gotowa pod przyszłego bota (ten sam punkt wejścia przenoszenia).

**Reguła umiejscowienia (RULES.md 26) — egzekwowana w core (chroni UI i bota):**
- `unit_catalog.placement_allows_zone(base_type, zone)` + `zone_is_space` — czysta reguła
  świata: statek tylko w `"space"`, siła naziemna/struktura tylko na planecie.
- `board_edit.move_units` waliduje umiejscowienie (`ValueError` → HTTP 422). To wspólny,
  czysty punkt wejścia przenoszenia (`state -> state`, bez HTTP) dla UI i BOTA — ani gracz,
  ani bot nie postawią statku na planecie. (Inne edycje God-Mode pozostają bez walidacji —
  umiejscowienie to wyjątek, bo „statek na planecie" jest niereprezentowalny.)
- Testy API: statek→planeta 422, piechota→orbita 422 (+ dozwolone ruchy 200).

**Frontend — podświetlenie celu + mapowanie gestu (prezentacja):**
- `appStore.dragOver` ({position, zone, valid}) aktualizowany w trakcie dragu.
- `useUnitDrag.resolveTarget`: nakłada regułę na cel pod kursorem — STATEK upuszczony na
  planetę celuje w ORBITĘ tego kafelka (wygodne, zawsze dozwolone); SIŁA NAZIEMNA nad orbitą
  = niedozwolone (`valid=false`, brak ruchu). `unitType.isShipUnit` (klasyfikacja asyncId
  spójna z backendem).
- `MapTile`: obwódka heksa celu — zielona (dozwolone, pulsuje) / czerwona (niedozwolone).
  CSS `.dropHighlight`/`.dropValid`/`.dropInvalid` (MapTile.module.css).

**Zweryfikowane E2E:** destroyer orbita→orbita 200, destroyer→planeta 422, piechota→orbita
422, piechota planeta→planeta 200. Backend 189 testów zielone (+2), ruff+mypy czyste;
frontend type-check+lint+build czyste. Reguły: RULES.md 26 (+ DnD 25).


---
### ✅ Blok E3·UI — przebudowa panelu fazy akcji (przesuwalny panel + rodzaje akcji + produkcja)

**Uwagi użytkownika + co zrobione:**
- **Panel stanu gry przesuwalny (drag).** Dotąd był przypięty na sztywno w lewym-górnym
  rogu planszy. Nowy hook `frontend/src/hooks/useDraggablePanel.ts` czyni panel pływającym:
  pointer-down na nagłówku (uchwyt z ikoną grip) przeciąga panel, pozycja trzymana w oknie
  (clamp) i zapamiętana w `localStorage` (`ti4_game_state_panel_pos`). Dwuklik na nagłówku =
  reset do pozycji domyślnej. Przycisk zwijania wydzielony jako osobny (`data-no-drag`), więc
  klik w niego nie rusza panelu. Na telefonie drag wyłączony (panel dokuje się paskiem).
- **Faza akcji przerobiona na planszówkowy podział na 3 RODZAJE akcji TI4** (RULES.md 19):
  Taktyczna / Strategiczna / Komponentowa — segmentowany wybór na górze, pod spodem szczegóły
  wybranego rodzaju. Gdy trwa akcja taktyczna (aktywny system), zakładka „taktyczna" jest
  wymuszona, a pozostałe zablokowane do zakończenia akcji (asystent prowadzi, nie wymusza).
  Nowy komponent `ActionPhasePanel`.
- **Kroki akcji taktycznej jako ładne, klikalne pigułki** (zamiast brzydkiego paska etykiet):
  numerowane kroki 1–5 (Ruch / Działa / Walka / Inwazja / Produkcja), wyróżniony bieżący,
  klik = skok do kroku (`tacticalSetStep`). Spójne z tonacją fazy (`--ph`). Krok walki i
  inwazji pokazują kontekstowe przyciski (otwórz okno walki / planety do walki naziemnej).
- **Produkcja całkowicie przebudowana — teraz STAWIA jednostki na planszy** (było: tylko
  sucha lista kosztów). Nowy `ProductionPanel`: statki → przestrzeń aktywnego systemu,
  siły naziemne/struktury → wybrana planeta (zakładki planet). Każda jednostka jako kafelek
  z ikoną (grafika `Unit`), kosztem i przyciskami +/− wołającymi `editUnit` (God-Mode delta;
  fighter/piechota po `unitsPerCost`). Dostępne zasoby pokazane jako podpowiedź (bez walidacji
  limitu — asystent, nie sędzia).

**Backend (dodatek do pomocy produkcji):**
- `core/tactical.py`: `ProducibleUnit` + `production_help` dostały pole `placement`
  (`"space"`/`"planet"`) z `unit_catalog.placement_of` — panel wie, gdzie stawiać jednostkę
  (RULES.md 26). DTO `ProducibleUnitHelp` i router `/tactical/production` przekazują pole.
- Stawianie jednostek idzie przez istniejący `POST /system/{pos}/edit-units` (God-Mode,
  z walidacją umiejscowienia w `board_edit`) — nowego endpointu nie trzeba.

**Zweryfikowane E2E:** produkcja statku (`+1 ca` do `space` 301) → cruiser pojawia się w
przestrzeni obok floty startowej; produkcja naziemna (`+2 gf` na `jord`) → piechota 5→7
(space dock nietknięty). Endpoint `/tactical/production` zwraca `placement` dla każdej
jednostki (statki=space, piechota/mech=planet). Health-check portu 8000 zadziałał na starcie.

**QA:** backend 189 testów zielone, ruff + mypy czyste; frontend type-check + lint + build
czyste.

**Luka świadomie zostawiona:** akcje komponentowe (E4) — karty akcji, liderzy, technologie,
relikty — mają w panelu zakładkę i notkę „rozlicz przy stole", ale dedykowanych pickerów
jeszcze nie ma (to zakres etapu E4).


---
### ✅ Blok E4·UI — kontrola komponentów (exhaust planet/tech/liderów) + fix wyboru frakcji

**Uwagi użytkownika + co zrobione:**

1. **Więcej kontroli nad komponentami** (planety, liderzy, technologie). Zakładka
   „Komponentowa" w panelu akcji (dotąd placeholder) ma teraz pełny `ComponentControlPanel`:
   chipy liderów (locked/ready/exhausted — cykl kliknięciem), technologii i planet
   (exhausted ↔ ready kliknięciem). Operator przełącza stan zgodnie z fizyczną grą;
   backend commituje do historii (Undo działa). Reguła: RULES.md 27.
   - **Core:** nowe pola `PlayerState.exhausted_planets`, `exhausted_technologies`; funkcje
     `board_edit.toggle_planet_exhaust`, `toggle_tech_exhaust`, `set_leader_state`
     (liderzy już mieli stan w `leader_states`, RULES.md 18).
   - **API:** `POST /player/planet/toggle-exhaust`, `/player/tech/toggle-exhaust`,
     `/player/leader/set-state` (router `players.py`).
   - **Web-data:** emisja `playerData.exhaustedPlanets`/`exhaustedTechs` (filtrowane do
     faktycznie posiadanych) + flaga `exhausted` w `PlanetEntityData` (per-planeta w
     `tileUnitData`). Liderzy już kompletni (`_player_leaders`).
   - **Frontend:** `useBoardEditor` — `togglePlanetExhaust`/`toggleTechExhaust`/
     `setLeaderState` + rozszerzony typ `PlayerEdit`. Nazwy komponentów z danych frontendu
     (`getTechData`/`getPlanetData`, fallback `prettifyId`).

2. **Bug: Neutral wybieralny jako frakcja — naprawione.** W danych AsyncTI4 `neutral`
   (i `lazax`) to placeholdery systemowe (puste `homeSystem`, brak liderów), nie grywalne
   frakcje. Dodano `FactionDef.is_playable` (ma dom ORAZ liderów). `GET /factions` zwraca
   tylko grywalne; `/setup/player` i `/game/new` odrzucają niegrywalne (422). Reguła:
   RULES.md 28. Lista frakcji w ekranie startowym spadła z ~35 do 33.

3. **Firmament vs Obsidian — ⚠️ KONFLIKT Z DANYMI, do potwierdzenia.** Użytkownik twierdzi,
   że Firmament to rozszerzenie Obsidianu, nie osobna frakcja. Ale dane AsyncTI4
   (`te_factions.json`) i plan projektu traktują je jako DWIE osobne grywalne frakcje
   (`firmament`=96a, `obsidian`=96b — dwie połowy domu TE, każda z własną flotą/liderami/
   zdolnościami/jednostkami). Zgodnie z zasadą „dane są źródłem prawdy, nie pamięć" OBIE
   pozostają wybieralne. Opisane w RULES.md 28 jako otwarte pytanie — czekam na decyzję
   użytkownika z materiałem Thunder's Edge, zanim ewentualnie usunę Firmament z puli.

**QA:** backend 192 testy zielone (+3: toggle planet/tech/leader, +fix faction filter),
ruff + mypy czyste; frontend type-check + lint + build czyste. Zweryfikowane E2E na żywym
backendzie: `/factions` bez neutral/lazax (firmament/obsidian zostają), toggle planety →
`exhaustedPlanets` + flaga `exhausted` w kafelku, toggle lidera → `exhausted=true`.


---
### ✅ Blok E4·UI² — wyczerpywanie przeniesione do menu kontekstowego (RMB) + reużywalny ContextMenu

**Uwaga użytkownika + co zrobione:** wyczerpywanie (exhaust planet/tech/liderów) to NIE akcja
komponentowa. Akcja komponentowa = zagranie karty z napisem „ACTION" (etap E4). Wyczerpywanie to
ogólna część rozgrywki, więc należy do **menu kontekstowego (prawy przycisk myszy)** na komponencie.

- **Wycofane:** panel `ComponentControlPanel` z zakładki „Komponentowa" w `GameStatePanel.tsx`
  (chipy exhaust) — zakładka wróciła do notki opisowej (akcje ACTION = E4, wyczerpywanie = RMB).
  Usunięte nieużywane importy/CSS.
- **Nowy, reużywalny komponent menu:** `frontend/src/shared/ui/ContextMenu/` (`useContextMenu`
  + `ContextMenu`). Otwiera się pod kursorem (`onContextMenu`→`preventDefault`), portaluje do
  roota DS, docisk do widoku, zamyka na klik-poza/Escape/scroll/resize. Pozycje to tablica
  `{label, onSelect, icon?, disabled?, danger?}` — ROZSZERZALNE (dokładamy kolejne później).
- **Podpięte RMB** na komponentach gracza: `PlanetCard` (Wyczerp/Odśwież), `Tech` (jw., tylko
  zbadane), `LeaderChip` + `CompactLeader` (Odblokuj / Wyczerp / Odśwież / Zablokuj — zależnie
  od stanu; helper `Leader/leaderMenu.tsx`). `ObjectShell` (silhouette techu) dostał opcjonalny
  prop `onContextMenu`.
- **Przewiercenie `playerId` (`discordId`)** z `PlayerCardDeck` w dół: przez `PlayerCardPlanetsArea`,
  `Leaders`, i argument `buildTechElementsForType` → liście. Backend `player_id` = `discordId`.
- Backend bez zmian w tym bloku (toggle-endpointy z poprzedniego bloku są tym, co menu woła).

**QA:** frontend type-check + lint + build czyste; backend 193 testy nadal zielone, ruff+mypy
czyste. Reguła zaktualizowana: RULES.md 27 (sekcja „UI — menu kontekstowe, NIE akcja komponentowa").

**Następnie (do rozbudowy menu RMB, wg uznania):** kolejne pozycje — np. „Pokaż kartę",
„Odczep attachment" (planety), „Aktywuj lidera" (gdy wejdzie E4), „Zwróć do rezerwy" itd.

---

### ✅ Przeróbka ekranu wyboru frakcji (setup) — galeria + faction summary (ukończone)

**Cel (prośba użytkownika):** dawny krok wyboru frakcji renderował osobną przewijalną
listę 30+ frakcji dla KAŻDEGO slotu gracza (ściana tekstu, małe przyciski, wybór z listy).
Nowy układ: klik we frakcję → bogaty podgląd (faction summary) z danymi, które widać też
w panelu gracza (zdolności, technologie frakcyjne, flagship/mech, liderzy, weksel). UI
spójne z resztą aplikacji (komponenty AsyncTI4) i wygodne w użyciu.

**Backend — rozszerzenie danych frakcji (dane statyczne z rejestru, bez stanu gry):**
- `src/core/models.py` — `FactionDef` dostał pola `promissory_notes` (alias `promissoryNotes`,
  dotąd po cichu pomijane przez `extra="ignore"`) i `complexity` (Low/Moderate/High).
- `src/api/schemas.py` — `FactionInfo` rozszerzony o pola bogate: `starting_tech`,
  `abilities`, `faction_tech`, `leaders`, `units`, `promissory_notes`, `commodities`,
  `complexity` (same identyfikatory; front rozwiązuje je po danych AsyncTI4).
- `src/api/routers/game.py` — handler `GET /factions` mapuje nowe pola z `FactionDef`.

**Frontend — układ master-detail:**
- `frontend/src/api/useNewGame.ts` — typ `FactionInfo` zsynchronizowany z backendem.
- `frontend/src/domains/setup/FactionSummary.tsx` (+ `.module.css`) — NOWY panel podglądu;
  reużywa komponenty panelu gracza (`Ability`, `Tech`, `LeaderChip`, `PromissoryNote`,
  `UnitDetailsCard`, `Unit`). Działa na etapie setupu, bo hooki stanu gry degradują do
  `undefined` poza providerem (bez rzutów).
- `frontend/src/domains/setup/steps/Step_Faction.tsx` (+ `.module.css`) — PRZEPISANY:
  pasek graczy (przełącznik, pokazuje kto co wybrał) + responsywna galeria kafli z
  wyszukiwarką + summary z przyciskiem „Wybierz dla gracza N". Klik w kafel = PODGLĄD,
  przypisanie dopiero przyciskiem. Frakcje wzięte przez innych graczy są przygaszone.
- Usunięto nieużywany już `FactionList.tsx` + `.module.css` (dawny quick-reference-on-hover
  zastąpiony pełnym summary).

**Zasady UI (zgodnie z preferencjami):** akcent zaznaczenia = niebieski DS (sygnał
interakcji); ciepły bursztyn/złoto TI4 jako wyróżnienie podglądu i nazwy frakcji.

**QA:** backend 280 testów zielonych, `ruff` + `mypy --strict` czyste; frontend `tsc`,
`eslint` i `vite build` czyste.

---

### ✅ Wybór frakcji (setup) — iteracja 2: scalenie techów, pełne nazwy, portret+lore (ukończone)

**Cel (uwagi użytkownika do iteracji 1):** panel wychodził poza okno; osobny krok wyboru
technologii był zbędny; skróty zamiast pełnych nazw (flota „cv", system domowy jako ID);
brakowało przełomu (breakthrough) i wszystkich jednostek frakcyjnych (np. argent_destroyer);
brak miejsca na portret i (długie) lore frakcji.

**Backend (`src/api/schemas.py`, `src/api/routers/game.py`):**
- `FactionInfo` dostał `breakthrough` (id dopasowany po `BreakthroughDef.faction`) i
  `starting_units` (lista `StartingUnit{base_type,count,placement}` budowana przez
  `parse_starting_fleet` — jedno źródło parsera floty, bez duplikowania kodów na froncie).
- Handler `get_factions` zrefaktorowany na helper `_faction_info` + `_faction_starting_units`
  + `_faction_breakthrough_id`.

**Frontend:**
- `FactionSummary.tsx` przebudowany: portret frakcji (z fallbackiem do ikony), sekcja lore
  (własny scroll — lore bywa długie), breakthrough (`Breakthrough`), WSZYSTKIE jednostki
  frakcyjne (filtr po `getUnitData(id).faction`, nie tylko flagship/mech), pełne nazwy
  jednostek/systemu/planet (`getUnitData`/`getTileById`/`getPlanetData`), wbudowany wybór
  technologii startowych (`StartingTechChoice`) — pokazywany, gdy frakcja jest przypisana
  aktywnemu graczowi.
- `factionLore.ts` (NOWY) — miejsce na lore (mapa `FACTION_LORE`) + konwencja portretów
  `/faction_portraits/<id>.{jpg,png,webp}`; `frontend/public/faction_portraits/README.md`.
- Scalono krok „Technologie startowe" z krokiem frakcji: `setupSteps.ts` (3 kroki zamiast 4),
  `useSetupStore.validateStep("faction")` waliduje też komplet techów; usunięto
  `Step_StartingTech.tsx` i `StartingTechPicker.tsx`.
- Naprawa „wychodzi poza okno": panel detalu `position: sticky` + `max-height: calc(100vh-…)`
  + własny `overflow-y` (nie wychodzi poza viewport).

**Gdzie użytkownik wkleja treść:** lore → `frontend/src/domains/setup/factionLore.ts`
(mapa `FACTION_LORE`, klucz = id frakcji); portrety → `frontend/public/faction_portraits/`.

**QA:** backend 280 testów + ruff + mypy czyste; front tsc + eslint + build czyste.

---

### ✅ Wybór frakcji (setup) — iteracja 3: boot, Obsidian, portret+lore z boku (ukończone)

**Cel (kolejne uwagi użytkownika):**
- ekran rozruchu „przeskakiwał" między dwoma wyglądami (splash HTML vs React BootScreen);
- ikony jednostek za duże względem boxów;
- planety: bez etykiet „system domowy"/„domowe", za to z wartościami resource/influence;
- edge-case Firmament → Obsidian: Obsidian to rozwinięcie Firmamentu — przycisk podglądu;
- portret postaci z boku + lore obok niego; prosty fade-in boxa i zdjęcia;
- ikona frakcji (placeholder portretu) z LOKALNYCH assetów, nie z CDN; usunąć legendę R/I.

**Co zrobione:**
- **Boot:** zsynchronizowano splash HTML (`index.html`) z React BootScreen — ten sam
  krój Ambroise + gradient TI4 + kreska pod logo + pulsujący pasek przy reduced-motion.
  Znika „przeskok dwóch ekranów" na starcie.
- **Backend:** nowy `GET /factions/{id}` (`_faction_info`) — pełne dane JEDNEJ frakcji,
  także NIEGRYWALNEJ (Obsidian), by dało się ją podejrzeć mimo braku w puli wyboru.
- **Frontend `useNewGame.ts`:** hook `useFaction(id)` (enabled na żądanie).
- **FactionSummary:** sprite jednostki wymuszony do boxa 34×34 (`:global(.unit-sprite)`);
  planety jako lista z wartościami resource (żółty) / influence (niebieski), bez etykiet
  „domowe"; przycisk „Zobacz Obsidian" dla Firmamentu → podgląd frakcji pochodnej z
  przyciskiem powrotu (mapa `DERIVED_FACTION`); portret postaci + lore w PRAWEJ kolumnie
  nagłówka; fade-in (`summaryFadeIn`, reduced-motion = sam opacity); placeholder portretu
  = LOKALNA ikona `/static/factions/<id>.png` (nie CDN); usunięto legendę „zasoby/wpływ".

**QA:** backend 280 testów + ruff + mypy czyste; front tsc + eslint + build czyste.

---

### ✅ Wybór frakcji (setup) — iteracja 4: wysuwany panel „postać + lore" (ukończone)

**Cel (uwaga użytkownika):** nagłówek panelu ma wrócić do prostego (ikona + nazwa +
złożoność), a portret POSTACI (lider) + duży box na lore mają być OSOBNYM panelem
wysuwanym z prawej po kliknięciu, z animacją.

**Co zrobione (`FactionSummary.tsx` + `.module.css`):**
- Nagłówek uproszczony: lokalna ikona frakcji (`/static/factions/<id>.png`) + nazwa +
  złożoność + akcje (przycisk „Postać i lore", „Zobacz Obsidian" dla Firmamentu).
- Nowy `LoreDrawer` — panel `position: fixed` przy prawej krawędzi ekranu (nie daje się
  przyciąć przez `overflow` panelu szczegółów), wjeżdża `translateX` po kliknięciu
  „Postać i lore"; duży portret postaci + duży box na lore; zamykany przyciskiem.
- Portret postaci (`LeaderPortrait`) — łańcuch źródeł LOKALNYCH: własny plik gracza
  `/faction_portraits/<id>.{jpg,png,webp}` → portret bohatera frakcji `/leaders/<heroId>.webp`
  → ikona frakcji `/static/factions/<id>.png`. Bez zewnętrznego CDN.
- Panel zamyka się automatycznie przy zmianie frakcji / wejściu w Obsidiana.

**QA:** front tsc + eslint + build czyste.

---

---

# Przeniesione z PROGRESS.md (2026-11-11): bloki E8 / akcja taktyczna / testy 4.4

## ▶ START KOLEJNEJ SESJI — stan akcji taktycznej (2026-11-06, commit `786549e`)

Cel etapu: pełna akcja taktyczna wg `R_tactical_action` (Activation → Movement + Space Cannon
Offense → Space Combat → Invasion → Production). FSM: `TacticalStep` (`core/game_state.py`),
kroki w `core/tactical.py`. QA na koniec sesji: backend 556 testów, front 25 testów vitest.

**Gotowe (szczegóły w blokach E8 niżej):**
- UX: „Activate system" w `TurnControls`; `TacticalActionDock` (przesuwany + skalowalny,
  kroki jako wskaźnik, potwierdzenia „Next step"/„End action").
- MOVEMENT: `move_fleet` z ładunkiem z przestrzeni i planet (`CargoPickup.from_zone`),
  `GET /tactical/move-range` (podświetlenie źródeł), drag&drop walidowany w akcji taktycznej,
  „włóż do statku" (drop ładunku na nosiciela → `LoadTransportModal`), monitor floty z Undo.
- SPACE CANNON: `core/dice.py` (seedowalny d10 w stanie), `core/space_cannon.py`, panel kroku,
  soczewka „Space Cannon range" (`tileUnitData.pds`).
- WALKA: `core/battle.py` + `core/damage.py`, pełnoekranowe okno `domains/battle/BattleOverlay`
  (szyk bitewny, armada, okręty obrócone 45° ku sobie, salwy okręt→okręt, straty klikaniem).
  Tło do podmiany: `assets/extra/battle_background.jpg` i `assets/extra/battle_ground.jpg`.

**Do zrobienia (proponowana kolejność):**
1. Feedback do nowego pola bitwy — kąt 45° na sprite'ach i ścisk dużych flot NIE były
   sprawdzone na żywo.
2. ✅ Odwroty w walce (RULES.md 39.5, commit `5d15835`): `core/retreat.py` (cele O4, wykonanie
   O5/O6 z ładunkiem i żetonem), kroki `CombatStep.ANNOUNCE`/`RETREAT` + okno `COMBAT_RETREAT`
   w `core/battle.py`, `POST /tactical/battle/announce-retreat` i `/retreat`, w oknie bitwy
   karty ogłoszenia/wyboru systemu, odlot floty (zamiast eksplozji) i dźwięki. 13 testów
   `tests/test_retreat.py`. TODO: gravity rift przy odwrocie, wyjątki frakcji/kart (E7), UI
   jawnego wyboru ładunku/puli żetonów (backend już przyjmuje `cargo`/`tokenPool`).
   ✅ Limit pojemności (RULES.md 39.6): `core/capacity.py` (statki + dok tylko dla myśliwców,
   ładunek = myśliwce/piechota/mechy w PRZESTRZENI), okno `CAPACITY` po zwycięstwie w walce
   kosmicznej i przy przejściu kroku (`next_step(state, registry)` — krok zostaje, gdy nadwyżka),
   `GET /tactical/capacity` + `POST /tactical/capacity/resolve`, globalny `CapacityModal`
   (ładownia, +/-, Auto = najtańsze najpierw). TODO: dok Cabal bez `capacityValue` w danych.
3. ✅ Pełna INWAZJA (RULES.md 40): `core/invasion.py` (Bombardment z Planetary Shield, Commit,
   Space Cannon Defense, wynik walki naziemnej, Establish Control), `GameState.invasion`,
   router `/tactical/invasion/*`, pełnoekranowe okno `domains/invasion/InvasionOverlay`
   (karty planet, lądowanie +/−/drag&drop/„Land all", przydział bombardowania, klikane straty;
   „Fight" otwiera pole bitwy NAD oknem inwazji). 13+3 testy backendu, 6 vitest.
   NIE sprawdzone na żywo (wymaga restartu backendu). TODO: Custodians na Mecatol, eksploracja
   po przejęciu (UI tylko sygnalizuje), mech z Bombardment, Plasma Scoring (RULES.md 40.3).
4. ✅ PRODUKCJA (RULES.md 33.3): `core/production.produce` — realna płatność (wyczerpanie planet,
   TG), limit PRODUCTION wspólny dla akcji (`GameState.production_used`), strefy umieszczenia,
   rezerwa, koszt pary (naprawiony błąd: pół ceny). `GET /tactical/production/view`, pełnoekranowe
   okno `domains/production/ProductionOverlay` (sloty „ile można zbudować", producenci, karty
   jednostek z +/−, planety jako klikalne boxy, TG, rachunek, zamówienie). Tło do podmiany:
   `assets/extra/production_bg.jpg` (fallback: starfield.png). NIE sprawdzone na żywo (restart
   backendu). TODO: „usuń z planszy, by dostawić z rezerwy", karty/tech (E7).
   Poprawka: płatność wybiera się tymi samymi kartami planet co w strefach graczy (`PlanetCard`
   z `onPick/picked`); karty jednostek pokazują „On board"; PRODUCTION to OSOBNE zdolności
   (Arborec: dok nie produkuje piechoty, piechota ma własne PRODUCTION 1) — RULES.md 33.3,
   `fits_producers`, `GameState.production_placed`; świeże jednostki nie dokładają PRODUCTION.
   FLEET POOL (RULES.md 42): `core/fleet_pool.py`, okno `FLEET_POOL` przy zmianie kroku akcji,
   `/tactical/fleet-pool`, ostrzeżenie w produkcji i ruchu (`FleetPoolWarning`) + wymuszony
   `FleetPoolModal`. Nie sprawdzone na żywo (restart backendu).
5. Braki: Sustain Damage w Space Cannon, capacity po walce, Plasma Scoring, multi-select
   Ctrl/Shift na mapie, pickup z systemów mijanych, >2 stron w walce (dziś 422).

**Pułapki (sprawdzone w tej sesji):**
- Zmiany backendu wymagają RESTARTU backendu, który kasuje grę w pamięci — pytać przed restartem.
- CSS `rgb(var(--x) / a)` wymaga składowych ze SPACJAMI (`255 0 0`), nie przecinków —
  inaczej cała deklaracja jest odrzucana (przezroczyste tła).
- Sprite `<Unit scaleSprite>`: wysokość w PIKSELACH; wrapper `<Unit>` nie ma wysokości, więc
  `100%` zapada się do zera (niewidoczne jednostki).
- Siatki kafelków jednostek: `minmax(0, 1fr)`, przyciski `flex: none`, a `grid-area` dzieci
  wymaga zdefiniowanych `grid-template-areas` u rodzica.
- Zmienna użyta przed definicją w komponencie → TDZ („Cannot access X before initialization").
- Okno pola bitwy przykrywa panel komunikatów mapy — 422 pokazujemy w samym oknie.
- W drzewie roboczym bywają obce zmiany z innej sesji — nie wciągać ich do commitów.

---

### ✅ Fix — dobór frakcji: Keleres max 1 wariant (losowanie + jawny wybór)

- **Problem:** przy wyborze „random" losowanie mogło przydzielić dwóm graczom różne
  warianty Council Keleres (`keleresm`/`keleresx`/`keleresa`) — a to jedna frakcja
  z trzema wariantami mentora, więc w grze może być najwyżej jeden.
- **Fix (`src/core/setup_service.py` → `_resolve_factions` / `_playable_faction_pool`):**
  pula losowania dedupuje po rodzinie frakcji (`registry.faction_family`) i bierze
  jednego przedstawiciela na rodzinę; rodziny zajęte jawnym wyborem są pomijane.
  Jawny wybór dwóch wariantów tej samej rodziny → `ValueError` (HTTP 422), obok
  istniejącej walidacji duplikatu `faction_id`.
- **Reguła:** `RULES.md` 28.1 (źródło: struktura danych + `F_keleres.md`).
- **Testy backendu:** `tests/test_setup_factions.py` (losowanie bez dwóch Keleres, jawny
  Keleres blokuje losowanie wariantu, dwa jawne warianty → błąd). QA: pytest 507, ruff, mypy.
- **Fix frontendu (ten sam problem w UI):** przy ręcznym wyborze gracze mogli klikać różne
  warianty Keleres i zobaczyć błąd dopiero przy starcie (422). Teraz:
  - `useSetupStore.ts` → `validateFactions` wykrywa duplikat RODZINY (`familyOfVariant`),
    nie tylko identycznego `faction_id` — blokuje przycisk „Start game";
  - `Step_Faction.tsx` → przycisk „Choose" jest ZABLOKOWANY („Already taken"), gdy inny
    gracz ma już wariant tej rodziny; komunikat mówi o Council Keleres (jedna frakcja),
    a nie o duplikacie id.
  - Testy: `frontend/src/domains/setup/useSetupStore.test.ts`. QA frontu: type-check,
    eslint (pliki zmienione), vitest 19, build — zielone.

---

### ✅ E8 Blok C+D — Walka: silnik + pełnoekranowe okno pola bitwy (ukończone)

- **Reguła (zweryfikowana):** `RULES.md` 39 ze źródłami `R_space_combat`, `R_ground_combat`,
  `R_anti_fighter_barrage`, `R_sustain_damage`, `R_attacker`, `R_nebula`, `R_status_phase`.
  Atakujący = aktywny gracz; AFB w 1. rundzie kosmicznej; rzuty atakujący→obrońca; mgławica +1
  obrońcy; straty w oknie `COMBAT_ASSIGN_HITS` (obrońca, potem atakujący) z Sustain Damage;
  koniec gdy ≤1 strona; naprawa uszkodzeń przy wejściu w STATUS.
- **Backend:** `core/battle.py` (start/AFB/roll/assign/close, wartości z wariantu gracza),
  `core/damage.py` + `SystemState.damaged_units`, `GameState.active_combat`. Krok SPACE_COMBAT
  nieopuszczalny przy dwóch flotach / trwającej walce; ruch przenosi uszkodzenia. Router `battle`
  (`GET /tactical/battle`, `POST start/afb/roll/assign/close`); web-data: `activeCombat` (kontrakt
  AsyncTI4) + `EntityData.sustained` (znacznik uszkodzenia na mapie). +21 testów (556 razem).
- **Frontend:** `domains/battle/` — pełnoekranowe **okno pola bitwy** (`BattleOverlay`): floty
  wlatują z lewej (atakujący) i prawej (obrońca), okręty zwrócone ku sobie, punkty życia (Sustain),
  pasek HP strony, spis jednostek z wartościami (combat/AFB/Sustain), tor kroków, salwy z animacją
  pocisków i rozbłysków trafień, animowane kości, eksplozje zniszczonych, ekran zwycięstwa/remisu.
  Przypisanie strat KLIKANIEM okrętów (tarcza = Sustain, czaszka = zniszczenie, „Auto"), licznik
  pokrycia. „Hide" chowa okno (plakietka „return"); dok: „Start space combat" / walka naziemna per
  planeta / „Return to battle". Komunikaty 422 w oknie. +6 testów vitest (`battleAssign`).
- **⚠️ TODO (RULES.md 39.4):** odwroty (Blok E), capacity po walce, zdolności frakcji/karty akcji
  (E7), Sustain w Space Cannon. **Backend wymaga restartu** (nowy router i pola stanu).

---

### ✅ E8 Blok F1 — Space Cannon Offense (silnik + zasięg + panel) (ukończone)

- **Reguła (zweryfikowana):** `RULES.md` 38 ze źródłem `docs/rules_tirules/R_space_cannon.md`.
  Strzela NIE tylko aktywny gracz: okno `SPACE_CANNON`, kolejka od aktywnego zgodnie z zegarem,
  nieaktywni celują w aktywnego, aktywny wybiera cel, gracz bez celu pominięty.
- **Zasięg z danych:** `UnitDef.spaceCannonHitsOn/DieCount/deepSpaceCannon`; wariant po technologiach
  gracza (PDS I 6+ → PDS II 5+ i deep = strzela z systemu sąsiedniego). Zero list technologii w kodzie.
- **Backend:** `core/dice.py` (seedowalny d10 w stanie gry — Undo deterministyczne; podstawa pod walkę),
  `core/space_cannon.py` (strzelcy, `coverage`, `offense_queue`, `open/fire/pass/assign_hits`),
  `api/routers/space_cannon.py` (panel + fire/pass/assign). Wejście w krok otwiera okno; wyjście z kroku
  blokowane (422) przy otwartym oknie; dziennik zostaje po zamknięciu okna (`space_cannon_log`).
  `web_data`: `tileUnitData[pos].pds` = pokrycie ostrzałem. +23 testy (535 razem).
- **Frontend:** soczewka mapy „**Space Cannon range**" (istniejąca soczewka PDS, teraz zasilona danymi)
  + osobny panel `SpaceCannonStepPanel`: kolejka, karta bieżącego strzelca (próg, kości, zasięg),
  wybór celu, Fire/Don't fire, animowane kości (trafienia świecą), przypisanie strat przez gracza-cel,
  dziennik. Przełącznik „Range" w panelu włącza soczewkę.
- **⚠️ Założenia/TODO (RULES.md 38.4):** Sustain Damage (brak modelu uszkodzeń → Blok C), wymuszenie
  capacity po stratach, Plasma Scoring, hooki frakcji (E7). **Backend wymaga restartu** (nowy router).

---

### ✅ E8 Blok B1–B6 — MOVEMENT dopracowany (drag&drop, monitor, zasięg, załadunek) (ukończone)

- **Decyzja (z użytkownikiem):** drag & drop statków to PREFEROWANY sposób ruchu; w akcji
  taktycznej idzie przez WALIDOWANY kanał (`/tactical/move`, reguły + capacity). Panel kroku
  MOVEMENT = MONITOR floty z cofaniem. Dok ma być ładny, przesuwany i skalowalny. Na mapie
  podgląd zasięgu. Zatrzymujemy się na MOVEMENT.
- **B1 — dok (fix + resizable):** root cause „dok rośnie / klei się do dołu" = `useDraggablePanel`
  nie zdejmował CSS-owego `bottom`/`right` → przy `fixed` z `top`+`bottom` bez `height` panel się
  rozciągał. Teraz `style` zwraca `bottom:auto`+`right:auto`. Nowy `useResizablePanel` (uchwyt w
  rogu, rozmiar w localStorage). Dok: stały nagłówek + przewijane ciało + przypięty uchwyt resize.
- **B2+B4 — piechota w przestrzeni + drag walidowany:** `RULES.md` 26 (wyjątek transportu, źródło
  `R_transport`/`R_invasion`): siły naziemne/myśliwce jadą jako ładunek i stoją w PRZESTRZENI
  aktywnego systemu do Commit Ground Forces; blokada „tylko planeta" tylko poza akcją (God-Mode).
  `useUnitDrag`: drop na aktywny system w akcji taktycznej → walidowany `moveShips` (statek vs
  ładunek po asyncId), poza akcją → God-Mode. `MoveQuantityModal` też routuje taktycznie. Wspólny
  `UnitStack/cargo.ts` (baseType/ship/cargo).
- **B3 — zasięg na mapie:** `core.movement.legal_move_sources` + `GET /tactical/move-range`
  (+3 testy). `useMoveRange` hook; `refresh()` invaliduje `moveRange`. `MapTile`: bursztynowe,
  pulsujące podświetlenie heksów będących legalnym źródłem ruchu.
- **B6 — panel = MONITOR floty:** krok MOVEMENT pokazuje flotę w przestrzeni AKTYWNEGO systemu
  + plakietka pojemności (zajęte/wolne, czerwona gdy przekroczona; liczona dla KONKRETNEGO gracza
  z `lookupUnit`). „Undo last move" (globalny `/undo`). Kreator ruchu schowany pod przełącznikiem.
- **B5 — okno ZAŁADUNKU transportu:** `LoadTransportModal` + store `loadTransport` — dla statku
  z capacity w systemie źródłowym: pokazuje jego pojemność i dostępny ładunek z tego systemu,
  „Fill to capacity"/„Clear", i rusza nosiciela + ładunek jednym walidowanym `/tactical/move`.
  Skrót „Load … with cargo…" w kreatorze ruchu.
- **Ograniczenia (świadome):** pickup ładunku tylko z przestrzeni systemu źródłowego; undo jest
  globalne (cofa ostatni commit, nie granularnie jeden statek); multi-select Ctrl/Shift na mapie
  — do rozbudowy (okno załadunku pokrywa wygodny multi-pickup transportu).
- **QA:** backend 510 testów zielonych (ruff + mypy --strict); frontend type-check + lint + build.

---

### ✅ E8 Blok A+B — UX akcji taktycznej + ruch z transportem (ukończone)

- **Cel (ustalony z użytkownikiem):** profesjonalna akcja taktyczna z ładnym UI na każdy z 5
  kroków. Start aktywacji wygodnie z prawego dolnego rogu; panel-przewodnik po krokach widoczny
  na MAP VIEW; ruch jako prawdziwy krok z transportem (nie tylko God-Mode).
- **Blok A — UX (frontend):**
  - Przycisk „**Activate system**" w `TurnControls` (prawy dolny róg, przy karcie strategii) —
    reużywa `activateMode`/`activateSystem`; odbiór kliknięcia w kafelek przeniesiony do
    `TurnControls` (żeby działał niezależnie od zakładki panelu). Wskaźnik „Tactical action in
    progress", gdy akcja trwa.
  - `TacticalActionDock` (NOWY) — PŁYWAJĄCY, PRZESUWANY dok na map view (`useDraggablePanel`,
    pozycja w localStorage, dwuklik = reset). Pokazuje panel kroków (reużyty `TacticalActionPanel`)
    TYLKO gdy trwa akcja (`activeSystem != null`). Powód: pływający „Game state" na mapie jest
    `variant="info"` i nie pokazywał kroków — brakowało przewodnika na samej mapie.
  - Pigułki kroków = WSKAŹNIK postępu (lista `<ol>`, nie przełącznik): nie wolno swobodnie skakać
    w przód/w tył. „Next step/Finish" i „End action" wymagają DRUGIEGO kliknięcia (inline confirm
    z ostrzegawczym akcentem) — nie kończy/przeskakuje akcji przypadkiem.
- **Blok B — ruch z transportem (backend + frontend):**
  - **Reguła (zweryfikowana, nie z pamięci):** `RULES.md` 32.3 ze źródłem
    `docs/rules_tirules/R_transport.md`, `R_capacity.md` (tirules2.com). Capacity = limit ładunku
    statku (myśliwce + siły naziemne), ładunek rusza razem i zostaje w przestrzeni (ląduje dopiero
    w INWAZJI), pickup z przestrzeni źródła, blokada CC przy pickupie, limit capacity w systemie.
  - `src/core/movement.py`: nowa `move_fleet(state, grid, registry, from_pos, ships, cargo,
    player_id)` — statki (każdy walidowany R1–R6) + ładunek w ramach wolnej capacity (odczyt
    `capacityValue`/`capacityUsed` z WARIANTU gracza). `move_ships` zostaje jako cienki wrapper
    (zgodność wsteczna). Capacity i klasyfikacja ładunku z danych/UnitDef, nie z pamięci.
  - `src/api/schemas.py`: `MoveShipsRequest` rozszerzony o `ships[]` (pełna flota) i `cargo[]`;
    `base_type` teraz opcjonalny. `src/api/routers/tactical.py`: `/tactical/move` woła `move_fleet`.
  - `tests/test_movement.py`: +6 testów transportu (przewóz myśliwców/piechoty, limit capacity,
    ładunek bez statku, blokada CC, wrapper `move_ships`).
  - `frontend` `MovementStepPanel` (NOWY): dedykowane okno kroku MOVEMENT — wybór systemu
    źródłowego (gdzie gracz ma statki), wybór statków + ładunku z licznikami, ruch do aktywnego
    systemu przez walidowany `moveShips` (422 z powodem → panel komunikatów). Zastępuje poleganie
    na trybie „move" na mapie w kroku ruchu.
- **Ograniczenia (świadome, do rozbudowy):** pickup ładunku tylko z przestrzeni źródła (nie z
  planet ani systemów mijanych); brak usuwania nadwyżki capacity poza ruchem; krok SPACE_CANNON
  na razie z notką (pełna interakcja w kolejnym bloku).
- **QA:** backend 503 testy zielone (ruff + mypy --strict czyste); frontend type-check + lint +
  build czyste.

---

### ✅ Akcja komponentu — trzeci typ akcji fazy akcji + modal „co zagrałeś?" (ukończone)

- **Cel (ustalony z użytkownikiem):** dać opcję zagrania AKCJI KOMPONENTU (trzeci typ akcji
  tury obok strategicznej i taktycznej) i pójść dalej. NA RAZIE bez mechaniki konkretnego
  komponentu — gracz oznacza „zagrałem coś z nagłówkiem Action", co odblokowuje End turn.
- **Reguła (zweryfikowana, nie z pamięci):** `RULES.md` 31.8 ze źródłem
  `docs/rules_tirules/R_component_action.md` (tirules2.com). Akcja komponentu bywa na karcie
  akcji, zdolności frakcji, liderze, technologii, relikcie, karcie eksploracji, promissory
  note, arkuszu frakcji — oznaczona nagłówkiem „Action". To akcja XOR pas w danej turze
  (31.7, R_action_phase).
- **Backend (core → api, silnik-sędzia):**
  - `src/core/component_action.py` (NOWY): `play_component_action(state, player_id?, component_id?)`
    — CZYSTA funkcja. Waliduje jak pozostałe akcje tury (faza ACTION, czyja tura, brak otwartego
    okna, jedna akcja na turę, nie po pasie) i ustawia `took_action_this_turn=True`. Efekt
    konkretnego komponentu NIE jest wykonywany (świadomy szkielet); `component_id` to adnotacja
    „co zagrano" (trafia do etykiety eventu), opcjonalna.
  - `src/api/schemas.py`: `ComponentActionRequest{player_id?, component_id?}`.
  - `src/api/routers/tactical.py`: `POST /tactical/component-action` (commit `_commit_flow`,
    `ValueError`→422). **UWAGA:** nowy endpoint wymaga RESTARTU backendu (stan w pamięci; stary
    proces serwuje stare trasy → 404 „Not Found").
  - `tests/test_component_action.py` (NOWY, 9): core (oznaczenie akcji, walidacje faza/tura/okno/
    po-akcji/po-pasie) + API (odblokowanie End turn, odmowa drugiej akcji).
- **Frontend (lista = WSZYSTKIE komponenty gracza z „Action", zero hardkodowania):**
  - `api/useBoardEditor.ts`: akcja `playComponentAction(playerId?, componentId?)` → endpoint.
  - `TurnControls.tsx`: przycisk „**Component action**" (fioletowy akcent ability) w panelu
    tury — między Pass a End turn; WYŁĄCZONY gdy gracz już działał / spasował / trwa okno.
    Klik otwiera modal „co zagrałeś?".
  - `componentActions.ts` (NOWY) `collectComponentActions(player, handActionCards)`: zbiera
    pozycje z DANYCH — karty akcji z ręki (`actionCardTiming==="Action"`), zdolności frakcji
    (`getAbilityKind==="action"`), liderzy (`abilityWindow`/`abilityText` od „ACTION"), techy
    i relikty (`text` z „ACTION"). Czyta to, co gracz REALNIE ma z web-data `playerData[]`
    (`abilities`/`leaderIDs`/`techs`/`relics`) + ręka. Deduplikacja po (kind,id), ikona + tag
    kategorii per wiersz.
  - Opcja awaryjna „Something else" na końcu listy — dla źródeł nieśledzonych jako posiadane
    (eksploracja / promissory). **TODO (ustalone z użytkownikiem):** docelowo USUNĄĆ „Something
    else" i listować też te źródła — do okodowania, gdy dojdzie ich śledzenie w stanie.
- **Ograniczenie (świadome):** relikty w web-data to na razie `[]` (backend ich nie emituje) —
  pojawią się na liście automatycznie, gdy dojdzie ich model. Efekt komponentu = TODO (dispatch
  po `component_id`, komponent po komponencie, z regułą/źródłem).
- **QA:** backend 497 testów zielonych (ruff + mypy --strict czyste); frontend type-check +
  lint + build czyste.

---

### ✅ Faza akcji: End turn wymaga akcji albo pasu (31.7) + dopieszczony UI tury (ukończone)

- **Reguła:** `RULES.md` 31.7 (źródło `R_action_phase`): w swojej turze gracz wykonuje JEDNĄ
  akcję (strategiczna/taktyczna/komponentu) ALBO pasuje — nie ma „pustej" tury.
- **Egzekucja (sędzia, `turn_flow`):** `end_turn` rzuca 422, gdy gracz nie ma
  `took_action_this_turn` ANI `passed`; `pass_turn` rzuca 422, gdy gracz już wykonał akcję w
  tej turze (pas jest ALTERNATYWĄ dla akcji, nie dodatkiem). Flaga `took_action_this_turn`
  ustawiana przez akcję strategiczną i taktyczną (a od 31.8 także komponentu), zerowana przy
  przekazaniu tury i wejściu w fazę.
- **Fix pustego okna secondary:** gdy kolejka respondentów jest pusta (gra solo / brak innych),
  `play_strategy_card` NIE otwiera okna — inaczej `pending_window` zostawał ustawiony i blokował
  End turn na stałe (bug: zagranie karty → End turn szary na zawsze). Dodano też możliwość pasu
  po akcji strategicznej.
- **UI tury (`TurnControls`):** potwierdzenie pasa w MODALU (pas ≠ koniec tury — trzeba jeszcze
  oddać turę), „nudge" na End turn po pasie/akcji, podpowiedzi jako zawijane „chipy" i STAŁA
  szerokość panelu (koniec przeskakiwania rozmiaru). End turn wygaszony na czas otwartego okna.
- **QA:** backend zielony (pytest + ruff + mypy), frontend type-check + lint + build czyste.

---

### ✅ Standaryzacja sterowania fazami: Pass≠End turn + brama „Next phase" + panel komunikatów (ukończone)

- **Cel (ustalony z użytkownikiem):** ujednolicić przyciski per faza i rozdzielić pas
  od zakończenia tury. Reguła projektowa: `RULES.md` 31.5 (DECYZJA 2026-11).
- **Pas jako akcja (AKCJA):** `turn_flow.pass_turn` tylko OZNACZA gracza
  (`passed=True`), NIE oddaje tury. Turę oddaje jedyny, spójny `end_turn` — także po
  pasie. `end_turn` pomija spasowanych.
- **Jedna flaga `passed` = „skończył swoją część fazy":** resetowana przy KAŻDYM
  wejściu w fazę (`next_phase`). STATUS „Next player" i AGENDA „Pass" wołają
  `/turn/phase-step` (`advance_active_player(mark_passed=True)`); AGENDA „Next player"
  woła `/turn/next-player` (bez oznaczania).
- **Brama „Next phase" (mówca):** `turn_flow.can_advance_phase` — STRATEGY po
  komplecie wyboru; ACTION/STATUS po `all_passed`; AGENDA zawsze. Projekcja do UI przez
  web-data `canAdvancePhase`+`allPassed`; twardy 422 z czytelnym komunikatem w
  `/phase/next`.
- **Przyciski per faza (frontend):** STRATEGY → Next phase (po komplecie); ACTION →
  Pass + End turn + (Next phase po komplecie); STATUS → Next player + Next phase (po
  komplecie); AGENDA → Pass + Next player + Next round. Spójnie w `TurnControls` i
  `GameStatePanel.PhaseControls`.
- **Panel komunikatów (UI):** nowy `PhaseNoticePanel` — osobny box przypięty u GÓRY
  ekranu, styl stołu (hairline + akcent tonu fazy). Prowadzi gracza przez fazę
  (`phaseNoticeMessage`) i pokazuje odrzucone akcje (422). Zastąpił lokalny
  `NoticeBanner` w panelu stanu.
- **Testy:** `test_turn_flow.py` (pas-bez-oddania, phase-step, reset flag,
  can_advance_phase × faza), `test_api.py` (phase-step w statusie, brama
  `/phase/next` w statusie). QA zielone: pytest 480, ruff, mypy; front type-check +
  build.

---

### ✅ Sąsiedzi gracza (Neighbors) w panelu + pole `neighbors` w web-data (ukończone)

- **Cel:** panel gracza (viewer ti4_web) pokazywał ikony sąsiadów, ale backend
  emitował `playerData[].neighbors` jako pustą listę — nic się nie renderowało.
- **Reguła (zweryfikowana, nie z pamięci):** RULES.md 2d na bazie
  `docs/rules_tirules/R_neighbors.md` (tirules2.com). Dwóch graczy jest sąsiadami,
  gdy obaj mają jednostkę lub kontrolują planetę w tym samym systemie LUB w
  systemach sąsiednich (sąsiedztwo przez wormhole wliczone).
- **Kod:** nowy czysty moduł `src/core/neighbors.py` (`neighbors_of`,
  `neighbors_by_player`) nad `GameState` + `HexGrid`. `api/web_data.py`:
  `_build_player_data` dostaje `grid`, liczy sąsiadów raz dla wszystkich graczy i
  emituje ich jako KOLORY (kontrakt viewera — `Neighbors.tsx` mapuje kolor→frakcja).
- **Testy:** `tests/test_neighbors.py` — ten sam system, systemy sąsiednie,
  nie-sąsiednie, kontrola planety bez jednostek, puste stosy, symetria, „gracz nie
  jest własnym sąsiadem".
- **Ograniczenia (RULES.md 2d):** hyperlanes i efekty frakcyjne zmieniające
  adjacency jeszcze nieuwzględnione (jak sekcja 2).
- **Promissory notes „in play area" (RULES.md 2e):** nowe JAWNE pole
  `PlayerState.promissory_notes_in_play` (strefa gracza — notki zagrane, odkryte,
  np. Support for the Throne; odrębne od tajnej RĘKI `private.promissory_notes`).
  Sklasyfikowane jako Public w `player_fields.py`, emitowane do viewera przez
  `promissoryNotesInPlayArea`, edytowalne przez God-Mode (`PlayerEditRequest`).
  Automatyczne przenoszenie notki z ręki do strefy przy zagraniu — przy logice
  transakcji (E8+); dziś zasila operator.
- **Własna frakcyjna notka (loadout) — `customPromissoryNotes` (RULES.md 2e):**
  web-data emitował to pole jako brak (panel nie pokazywał startowej notki frakcji,
  np. Sol Military Support). Dodany helper `_faction_promissory_notes` czyta listę z
  danych frakcji (`FactionDef.promissoryNotes`), nie z pamięci; emitowane w
  `customPromissoryNotes`. Obsłużone edge-case: `neutral` → `[]`, Empyrean → dwie
  notki. Test w `tests/test_web_data.py` (Sol `ms`, Hacan `convoys`).
- **QA:** `pytest` 454 ✅, `ruff` ✅, `mypy` ✅.

---

### 🐛 Naprawa regresji: manifest grafik obejmuje teraz całe `assets/` (ukończone)

- **Objaw:** po migracji grafik z CDN na lokalne plansza nie pokazywała żadnych
  grafik (brak tilesów planet, tokenów, emoji).
- **Źródło błędu:** `src/audit/assets_manifest.py` — stała `DEFAULT_ASSET_DIRS`
  zawierała tylko 9 katalogów i POMIJAŁA kluczowe grafiki planszy (`tiles`,
  `emojis`, `attachment_token` i inne). Manifest frontu (`assetManifest.json`) nie
  zawierał tych ścieżek, więc Resolver_Zasobów (`resolveAsset.ts`) zwracał
  `PLACEHOLDER_URL` dla każdego brakującego wpisu → tile'y planszy znikały.
- **Naprawa (odporna na przyszłość):** `DEFAULT_ASSET_DIRS = None`; przy `dirs=None`
  `list_asset_files()`/`build_manifest()` skanują CAŁE drzewo `assets/` pod kątem
  grafik (`IMAGE_SUFFIXES`), pomijając tylko `EXCLUDED_ASSET_DIRS` (dane/konfiguracja/
  surowce: `data`, `config`, `raw`, `META-INF`, `voices`, `hover_images`, `systems`,
  `planets`, `alias`). Nowe katalogi grafik trafiają do manifestu automatycznie.
  Jawna lista `dirs` zachowuje stare zachowanie (wsteczna kompatybilność).
- **Manifest po regeneracji:** 8666 wpisów (było 9 katalogów), w tym `tiles/` (848),
  `emojis/` (1556), `attachment_token/` (144). Oba manifesty (`audit/` i frontu)
  odtworzone przez `uv run python -m src.audit --write-manifest`.
- **Testy:** `tests/test_audit_diffs.py` — nowy test skanu całości przy `dirs=None`
  oraz test obecności grafik planszy w manifeście projektu.
- **QA:** `pytest` 443 ✅, `ruff` ✅, `mypy` ✅; frontend `npm run build` ✅.

---

### ✅ Baza danych TI4 · 4.1: spójność referencji `core/references.py` (ukończone)
- Nowy moduł `src/core/references.py` (czysty, bez I/O): `UnresolvedReference`,
  `TemplateReference`, `ReferenceReport`, `find_unresolved_references`,
  `build_reference_report`. Sprawdza listy frakcji (`leaders`, `abilities`,
  `promissoryNotes`, `factionTech`, `units`, `startingTech`, `startingTechOptions`),
  `cardIDs` talii kanonicznych (po `type` talii → kategoria celu), `attachmentId`
  eksploracji i `attachmentID` żetonów. Zachowane `missing_planet_references` (R7.4).
- Flaga `leaks_noncanonical` (R7.6) z `LoadReport.skipped_index`: cel istnieje, ale
  pochodzi ze źródła niekanonicznego (przeciek homebrew).
- Placeholder `<color>` (promissory `color.json`) raportowany OSOBNO jako „szablon”
  (`templates`), nie jako nierozwiązana referencja — ⚠️ ZAŁOŻENIE w `RULES.md` 35.
- Wpięcie w `StaticDataRegistry`: atrybut `reference_report` (budowany w `_load()` po
  złożeniu katalogu) i metoda `unresolved_references()`. Nierozwiązane referencje NIE
  blokują startu (dane lokalne, God-Mode działa) — zgłasza je Audytor_Danych (R7.5).
- Realne dane: 22 nierozwiązane referencje do zgłoszenia przez Audytora (deck
  `explores_cpti` → karty niekanoniczne z flagą leak; `attachmentId` eksploracji
  `mirage`/`gamma`/`ionalpha` bez odpowiadającego attachmentu). Rozstrzygnięcie
  (wyjątek/poprawka) należy do użytkownika/konfiguracji audytu.
- QA zielone: `pytest -q` (396 passed), `ruff check src tests`, `mypy src tests`.
- Dalej: 4.2 (`faction_bundle` + `FactionBundle`), 4.3/4.4 (testy referencji).
---

### ✅ Baza danych TI4 · 8.5 + 8.6: testy właściwościowe Audytora (ukończone)
- `tests/test_audit_props.py` (Hypothesis, min. 100 iteracji każdy):
  - **Property 15** (skaner zewnętrznych URL, `audit/locality.find_external_urls`,
    Validates 2.5): zgłasza DOKŁADNIE adresy `http(s)://` spoza `LOCAL_HOSTS` i listy
    dozwolonej (dopasowanie prefiksu po granicy segmentu), numer linii i nazwa pliku
    zgodne z modelem referencyjnym; hosty lokalne nigdy nie wpadają.
  - **Property 12** (luki źródeł kanonicznych z wyjątkami, `audit/diffs.find_gaps`,
    Validates 3.2/6.2/6.3/6.5/11.5): luka = (kategoria, źródło) z licznikiem zero
    (brak klucza = zero) minus potwierdzone wyjątki; wynik posortowany; wyjątki
    pokrywające wszystko → pusto.
  - **Property 13** (różnice to dokładne różnice zbiorów/słowników): `diff_sets`,
    `diff_embedded_ids`, `diff_manifest` (rozłączne `extra`/`missing`, `unused`/`missing`,
    pokrycie różnicy symetrycznej), `diff_counts` (dokładne pary o różnych licznikach,
    `None` jako różnica, pusty ⇔ tablice równe).
- QA zielone: `pytest -q` (373 passed), `ruff check src tests`, `mypy src tests`.
---

### ✅ Baza danych TI4 · 5.1: specyfikacja czasowa `core/timing_spec.py` (ukończone)
- `TriggerKind`, `TimingSpec`, `parse_timing`, `TRIGGER_WINDOW_MAP` (D10: when/after/before/
  instead → `REACTION`, reszta → brak okna; ⚠️ ZAŁOŻENIE w RULES.md 34). Klasyfikacja tylko
  po prefiksach, `raw_text` bez zmian, `play_timing_agrees` z `AGENDA_WHEN`/`AGENDA_AFTER`.
- `LeaderDef.ability_window` (alias `abilityWindow`). `core/timing.py` i `WindowType` bez zmian.
- Testy: `tests/test_timing_spec.py`. Dalej: 5.2 (`build_timing_specs`, `query_timing`).
---

### ✅ Baza danych TI4 · 5.2: specyfikacje czasowe w katalogu + `query_timing` (ukończone)
- `build_timing_specs(tables, leaders, abilities)` w `core/components.py`: buduje
  `TimingSpec` WYŁĄCZNIE z pól JSON (R8.2) — karty akcji (`window`+`phase`+`playTiming`),
  zdolności frakcji (`window`+`windowEffect`→`effect_text`), liderzy (`abilityWindow`).
  Komponenty bez frazy okna nie dostają specyfikacji.
- `ComponentCatalog` dostał opcjonalny parametr `timing_specs` (zgodny wstecz) oraz metody
  `timing_spec(ref)` i `query_timing(trigger, phase=None)` (filtr po wyzwalaczu i fazie,
  wynik posortowany deterministycznie po kategorii i id, R8.4/R8.6).
- Testy: `tests/test_components.py::test_build_timing_specs_i_query_timing`. QA zielone.
---

### ✅ Keleres (3 warianty): przełom i technologie wg Thunder's Edge (ukończone)

- **Błąd:** przełom TE Keleres ma `faction="keleres"`, a warianty to `keleresm/x/a` →
  dopasowanie po id nie znajdowało przełomu. Technologie frakcyjne były z Codexu
  (`iihq`, `asn`), a w TE I.I.H.Q. jest przełomem, a technologią frakcyjną jest Executive Order.
- **Naprawa:** `FactionDef.short_name` (rodzina frakcji), `registry.breakthrough_for_faction`
  (id lub rodzina), `registry._apply_thunders_edge_breakthrough_techs` (przy włączonym TE:
  technologia o nazwie przełomu wypada z `factionTech`, wchodzą techy TE rodziny →
  `executiveorder`, `asn`). Bez TE bez zmian. Testy w `tests/test_registry.py`.
- Nie ruszone: technologie startowe Keleres (zdolność The Tribuni — wybór 2 z cudzych
  startowych) nadal niezaimplementowane (RULES.md 16).

---

### ✅ Wybór frakcji (setup) — iteracja 5: pełnoekranowa scena, nagłówek frakcji, Obsidian (ukończone)

**Pełny opis (układ, pliki, format treści, animacje, gotchas): `UI_WYBOR_FRAKCJI.md`.**

**Cel (uwagi usera):** portret + lore jako JEDNA kompozycja na cały ekran; kolejność uwagi
nazwa → cytat → autor → lore; panel umiejętności szybki; sterowanie człowiek/bot w kroku 1;
osobny, „dziwny" wyjątek dla Obsidiana (lore pismem z gry).

**Co zrobione:**
- **Kreator ma 2 kroki** (`setupSteps.ts`): `name-color` („Gracze": nazwa + kolor + sterowanie
  HUMAN/BOT + trudność z `/engine/config`) i `faction` (scena). Usunięty `Step_Control.tsx`;
  `validateControl` przeniesione do `validateStep("name-color")`. Krok sceny jest w
  `STAGE_STEP_IDS` → renderowany bez ramki kreatora (`StageActions` w `SetupWizard.tsx`),
  `StartScreen` zdejmuje padding/scroll (`.setupScreenStage`).
- **Scena** (`Step_Faction.tsx`): pasek górny (Wstecz · gracze · Start gry), strefa postaci
  (portret przy lewej/dolnej krawędzi ekranu, maska wygaszająca prawą stronę, lore w 2
  kolumnach tuż przy sylwetce, delikatnie na nią nachodzące), wąski panel szczegółów
  (`FactionSummary` na szkle), pionowa lista frakcji (sam klik), osobny wyśrodkowany przycisk
  „Wybierz dla gracza N" na dole.
- **Portret** (`FactionBackdrop.tsx`): pomiar przezroczystego marginesu PNG (canvas) →
  sylwetka równo z krawędzią ekranu + środek sylwetki (`--figure-cx`) do centrowania nagłówka
  i ustawienia lore.
- **Nagłówek** (`FactionHeader`): panel w stylu karty frakcji (ścięte rogi, ikona, nazwa
  Handel Gothic D Bold, cytat w “ ”, autor „— …"), akcent koloru **wyliczany z ikony frakcji**.
  Nowe pola `quote`/`quoteAuthor` w `factionLore.ts`.
- **Lore**: dwie jawne kolumny (`splitLoreColumns`, cięcie na końcu zdania), auto-dopasowanie
  czcionki do boxa bez przewijania, tło lekkie i przezroczyste.
- **Animacje**: postać wyłania się z mgły (5.5 s), potem nagłówek (nazwa → cytat → autor), na
  końcu lore od 4.2 s; panel szczegółów i przycisk wchodzą szybko (~0.4 s). Reduced-motion:
  wolny fade bez ruchu (krótki fade był „niewidoczny").
- **Obsidian** (`glyphLore` w `factionLore.ts`): lore krojem **Lazaxian**, przycisk
  „Przetłumacz" z efektem rozszyfrowania (`GlyphText.tsx`: fala znak po znaku, migotanie,
  glitch, aberracja, skanlinie) + groza (losowe glitche akapitów przez WAAPI, przygasanie,
  błyski fraz `glitchPhrases`, bijące serce tła). Transkrypcja lore jest fanowska (lista
  pominiętych fragmentów w `UI_WYBOR_FRAKCJI.md`).
- Usunięte: `LoreDrawer`/`LorePanel`/`LeaderPortrait`/`LoreBlocks` z `FactionSummary.tsx`
  (przeniesione/zastąpione w `FactionBackdrop.tsx`).

**Pułapki odkryte po drodze** (szczegóły w `UI_WYBOR_FRAKCJI.md` §9): `easing` w WAAPI działa
na cały przebieg (steps(1) = niewidoczny efekt); podmiana `animation` na elemencie z
animacją wejścia restartuje ją; `text-wrap: balance` nie zwęża kontenera; test szerokości
z pseudo-elementem wystającym zbijał czcionkę do minimum.

**QA:** front `tsc` + `eslint` + `build` czyste. Brak testów jednostkowych frontu; efekty
wizualne weryfikowane tylko w przeglądarce.

**Otwarte:** tło sceny (`main_menu.jpg` przyciemnione) i pozycja portretu — user dopuścił
zmiany; uzupełnienie lore/cytatów/autorów pozostałych frakcji w `factionLore.ts`;
`obsidian.png`, `firmament.png` i `Lazaxian-Bold.ttf` mogą być jeszcze niezacommitowane.

---

### ✅ Zadanie 5.1 (feature `player-model-and-setup-ui`) — weryfikacja limitów rąk + poziomów trudności (ukończone)

**Cel (zadanie BADAWCZE, blokujące zad. 8 i 9):** potwierdzić ze źródeł wartości dotąd
oznaczone jako ⚠️ ZAŁOŻENIE (limity rąk, zbiór poziomów trudności bota) i udostępnić je
jako konfigurację czytaną przez `StaticDataRegistry` — bez hardkodowania liczb w regułach.

**Zweryfikowane ze źródeł (tirules2.com / lokalny zrzut `docs/rules_tirules/`):**
- Karty akcji — **max 7** na ręce (`R_action_cards`); efekty gry mogą zmienić limit.
- Tajne obiektywy — **max 3** łącznie zrealizowane + niezrealizowane (`R_objective_cards`).
- Promissory notes — **brak limitu** ręki w regułach (`R_promissory_notes`) → `null`.
- Poziomy trudności bota — **nie istnieją w TI4** (brak w assetach i w regułach) →
  ⚠️ ZAŁOŻENIE, zbiór konfigurowalny `["EASY", "NORMAL", "HARD"]` do potwierdzenia.

**Co zrobione:**
- Nowy asset `assets/config/engine_config.json` (limity rąk + `valid_difficulties`).
- `src/config.py` — ścieżka `ENGINE_CONFIG_PATH`.
- `src/core/models.py` — modele `HandLimits`, `EngineConfig` (Pydantic v2).
- `src/core/registry.py` — ładowanie configu + `hand_limits()` / `valid_difficulties()`.
- `docs/RULES.md` — nowa sekcja 30 (źródła + ⚠️ ZAŁOŻENIE trudności) + wpis w spisie treści.
- `tests/test_registry.py` — 3 testy (limity z assetu, zbiór trudności, fallback bez pliku).

**QA:** 280 testów zielonych, `ruff` i `mypy --strict` czyste.

**⚠️ Decyzja do potwierdzenia przez użytkownika:** zbiór poziomów trudności bota
(`["EASY", "NORMAL", "HARD"]`) — czy właściwy, czy preferowany inny (więcej poziomów,
polskie etykiety, skala liczbowa)? Zmiana wyłącznie w `engine_config.json`, bez kodu.

---

### ✅ Zadanie 9.1 (feature `player-model-and-setup-ui`) — delegacja walidacji do `resolve_players` w endpointach setupu (ukończone)

**Cel:** uczynić endpointy `/game/new` i `/setup/player` cienkimi — cała walidacja/
normalizacja graczy (liczba, nazwy, kolory, frakcje, typ sterowania, trudność, technologie,
losowy dobór frakcji) idzie do `resolve_players` w `core`, a router tylko buduje mapę,
nanosi `ResolvedPlayer` na stan i ustawia nowe pola `PlayerState`.

**Co zrobione (`src/api/routers/game.py`):**
- `post_new_game`: usunięto ręczną pętlę walidacji (frakcja/kolor/slot) i limit „za dużo
  graczy" — delegowane do `resolve_players` (`available_colors` z `AUTO_SLOT_ORDER`,
  `max_players=len(AUTO_SLOT_ORDER)`, `valid_difficulties` z registry). Iteracja po
  `ResolvedPlayer`; auto `home_position` ze slotu, gdy niepodany (R14.3).
- `post_setup_player`: analogiczna delegacja z jednoelementową listą; pula kolorów
  pomniejszona o kolory już rozstawionych graczy, by auto-dobór nie powielił koloru.
- Nowe helpery: `_available_colors`, `_validate_home_position` (R14.4 — istnieje na mapie
  i nieprzypisana; `HTTPException(422)`), `_apply_resolved_player` (woła
  `apply_setup_to_state` + ustawia `display_name`/`control_type`/`difficulty`).
- Usunięto tymczasowe strażniki z zad. 7.1 (`faction_id is None → 404`) — losowa frakcja
  (R8.5) działa teraz przez `resolve_players`.

**Decyzja (kontrakt błędów):** nieznana frakcja daje teraz **HTTP 422** (było 404), spójnie
z resztą błędów walidacji setupu (`ValueError → 422`, design §Error Handling). Zaktualizowano
test `test_setup_unknown_faction_404` → `test_setup_unknown_faction_422` w `tests/test_api.py`.

**QA:** 280 testów zielonych, `ruff` i `mypy --strict` czyste. Anomalia web-data nie wystąpiła.

---

### ✅ Blok E4·UI³ — menu RMB w player-area przy mapie + „Aktywuj system" na kafelku

**Uwagi użytkownika + co zrobione:**

1. **Menu RMB (wyczerp/odśwież) też w player-area przy mapie.** Wcześniej przewiercony był
   tylko `PlayerCardDeck`. Teraz `playerId` (`discordId`) leci też do dwóch pozostałych
   wariantów panelu gracza: `PlayerCardSidebar` (panel boczny osadzony przy mapie — to „player
   area w menu mapy") i `PlayerDeckRow` (wiersz deck). W `PlayerDeckRow` techy idą przez
   `TechGridMobile`, więc dodano mu prop `playerId` przekazywany do `buildTechElementsForType`.
   Efekt: RMB wyczerp/odśwież na planetach/tech/liderach działa we wszystkich panelach gracza.
   (Uwaga: `PlayerStatsArea` na heksach mapy NIE renderuje planet/tech/liderów — tylko
   statystyki — więc tam nic nie dodawano.)

2. **„Aktywuj system" pod RMB na kafelku.** `MapTile` dostał `onContextMenu` → menu z pozycją
   „Aktywuj system", która woła `activateSystem(position)` (POST `/tactical/activate`). Backend
   `core.tactical.activate_system` kładzie żeton dowodzenia AKTYWNEGO gracza w przestrzeni,
   ustawia `active_system` + krok `MOVEMENT`, zdejmuje 1 z puli taktycznej. Pozycja zablokowana,
   gdy brak aktywnego gracza (inaczej 422). Menu omija kafelki hyperlane/embedded; omija też
   tryb klikania (`activateMode`) — woła aktywację wprost (jak przycisk w panelu faz).

**Zweryfikowane E2E:** aktywacja 101 → `command_tokens=[p1]`, `active_system=101`,
`tactical_step=MOVEMENT`, `tactical_cc` 3→2. Reużyty komponent `shared/ui/ContextMenu`.

**QA:** frontend type-check + lint + build czyste; backend 193 testy zielone (bez zmian w tym
bloku — menu woła istniejące endpointy), ruff+mypy czyste. Reguła: RULES.md 27 (rozszerzona).

---

### 🔧 Blok E8-0 — zmiana kierunku na silnik-SĘDZIA + aktualizacja dokumentacji (w toku)

**Kontekst (ustalenie z użytkownikiem 2026-10):** projekt zmienia filozofię z „asystent stołu,
nie sędzia" na **silnik-SĘDZIA egzekwujący reguły TI4 przez kod**. Powody: (1) docelowy bot AI
i tak musi znać i respektować reguły; (2) egzekucja jest wygodniejsza dla gracza (user friendly);
(3) gra przestaje zakładać fizycznie rozłożoną planszę. God-Mode ZOSTAJE jako osobny kanał ręcznej
korekty omijający walidację. Dodajemy OKNA CZASOWE (timing windows) — np. zagranie karty strategii
otwiera pozostałym graczom okno na secondary. Tryb: solo vs boty + hot-seat (docelowo moduł sieciowy),
więc okna pytają graczy po kolei.

**Ustalenia projektowe (z użytkownikiem):**
- Egzekucja idzie DALEKO (wszystkie reguły TI4), ale God-Mode zostaje jako wentyl.
- Walka: pełna, interaktywna (rzuty kośćmi z animacją) — docelowo. Pierwszy rdzeń: rzuty + liczenie
  trafień + okno „przypisz straty", wielorundowo; AFB/space cannon jako kolejne okna.
- Okna czasowe modelowane JEDNOLICIE: stos/okno w `GameState` + kolejka respondentów (`core/timing.py`).
- Kolejność reakcji (POTWIERDZONA przez użytkownika): od gracza po aktywnym, zgodnie z zegarem
  (speaker order); inicjator domyślnie pomijany. Dotyczy secondary i reakcji „when/after".
- `src/engine/` (puste, pod AI) — można przebudować dowolnie.
- E1–E3 działają → dobudowujemy walidację + okna NA ISTNIEJĄCYM, nie przepisujemy.

**Plan zadań E8 (pełny opis: PLAN_PELNA_ROZGRYWKA.md „E8"; reguły: RULES.md 29):**
T1 model okna → T2 ekspozycja w web-data + UI → T3 secondary kart strategii → T4 aktualny gracz
w STATUS/AGENDA + walidacja flow → T5 ruch (core) + walidacja → T6 walidacja aktywacji/planety/
produkcji → T7 walka-rdzeń → T8 walka w UI → T9 AFB + space cannon → T10 dokumentacja + memory.

**Zrobione w tym bloku (T10 częściowo — dokumentacja PRZED kodem, zgodnie z zasadą projektu):**
- [x] `docs/RULES.md` — nowa sekcja 29 (zmiana kierunku „sędzia" + zweryfikowany MODEL OKNA
  czasowego 29.2 ze źródłem LRR „Timing" + AsyncTI4 + potwierdzenie użytkownika; 29.3 aktualny gracz).
- [x] `docs/RULES.md` — sekcje 19–22 i 24 oznaczone bannerem „AKTUALIZACJA KIERUNKU": ich adnotacje
  „asystent, nie sędzia" są UNIEWAŻNIONE (treść zostaje jako referencja mechaniki TI4).
- [x] `docs/PLAN_PELNA_ROZGRYWKA.md` — decyzja E3 zaktualizowana (asystent → fundament pod sędziego),
  dodany etap E8 z listą zadań, sekcja statusu wskazuje E8 jako AKTUALNY.
- [x] `docs/PROGRESS.md` — ten wpis.

**DO ZROBIENIA (następne bloki):**
- [ ] Aktualizacja `.kiro/steering/custodian-engine.md` oraz `docs/README.md` o nowy kierunek
  (wzmianka, że silnik egzekwuje reguły; God-Mode = wentyl) — przy najbliższej okazji.
- [ ] Aktualizacja memory projektu `engine-is-table-assistant-not-referee` → nowy kierunek
  „sędzia + God-Mode jako wentyl" (wymaga narzędzia pamięci — do zrobienia, gdy dostępne).
- [ ] T1: implementacja `core/timing.py` + model okna w `GameState` (pierwszy blok kodu E8).

**QA:** ten blok to wyłącznie dokumentacja (brak zmian w kodzie) — testy backendu bez zmian
(193 zielone z poprzedniego bloku). Kod wejdzie od T1.

### ✅ Blok E8-T1 — model okna czasowego w stanie + core/timing.py (ukończony)

**Cel:** wprowadzić jednolite pojęcie „okno czasowe" (timing window) i „kto teraz reaguje"
do stanu gry — fundament interakcji między graczami (secondary kart strategii, przypisanie
strat w walce, space cannon, reakcje). Reguła modelu: RULES.md 29.2.

**Zrobione:**
- [x] `src/core/game_state.py`: enum `WindowType` (STRATEGY_SECONDARY, COMBAT_ASSIGN_HITS,
  SPACE_CANNON, REACTION) + model `TimingWindow` (queue, cursor, responded, context +
  właściwości `is_complete`, `current_responder`) + pole `GameState.pending_window`.
- [x] `src/core/timing.py` (NOWY): czyste funkcje `state->state`:
  - `build_response_queue(state, initiator, include_initiator=False)` — kolejka od gracza
    PO inicjatorze zgodnie z zegarem (speaker order z `seating_order`; fallback: sorted ids);
    inicjator pomijany lub na końcu;
  - `open_window(state, type, queue, context=)` — otwiera okno (odrzuca zagnieżdżanie);
  - `current_responder`, `respond_current` (waliduje kolejność — odpowiedź poza kolejnością
    → ValueError), `is_window_complete`, `close_window` (idempotentne).
  - Rozdział odpowiedzialności: `timing` = CZYSTA mechanika kolejki; efekty okna (zużycie
    żetonu, usunięcie jednostek) stosuje warstwa wyżej PRZED/PO `respond_current`.
- [x] `tests/test_timing.py` (NOWY, 16 testów): budowa kolejki (po inicjatorze, zawijanie,
  include_initiator, brak seating, inicjator spoza stołu), open/respond/close, błędy
  (zagnieżdżanie, poza kolejnością, brak okna, okno zakończone), round-trip serializacji.

**QA:** 209 testów zielonych (było 193, +16), ruff czysty, mypy --strict czysty.
Ostrzeżenie StarletteDeprecationWarning bez zmian (znane, nieblokujące).

**Następny krok:** T2 — ekspozycja `pending_window` w `web_data` + endpoint `POST /window/respond`
+ panel okna w UI (kto teraz reaguje + przycisk odpowiedzi).

### ✅ Blok E8-T2 — ekspozycja okna czasowego w web-data + endpointy + panel UI (ukończony)

**Cel:** gracz WIDZI otwarte okno czasowe (kto teraz reaguje) i może odpowiedzieć. Spina
model z T1 (core/timing) z frontendem.

**Backend:**
- [x] `src/api/web_data.py`: helper `_pending_window(state)` + pole `gameState.pendingWindow`
  w `_build_game_state`. Tłumaczy okno na kształt dla frontu: `windowType`, `currentResponder`
  (KOLOR gracza, jak `activePlayer`), `currentResponderId` (stabilny player_id do adresowania
  odpowiedzi), `queue` (kolory), `cursor`, `remaining`, `responded`, `context`, `isComplete`.
- [x] `src/api/schemas.py`: `WindowOpenRequest` (typ + queue LUB initiator), `WindowRespondRequest`
  (player_id + decision).
- [x] `src/api/routers/window.py` (NOWY): `POST /window/open` (narzędzie/testowe — wylicza kolejkę
  z inicjatora przez `build_response_queue` lub bierze jawną), `POST /window/respond`
  (`timing.respond_current`, poza kolejnością/brak okna → 422), `POST /window/close`. Router
  zarejestrowany w `app.py`.
- [x] `tests/test_window_api.py` (NOWY, 9 testów): web-data null domyślnie, open eksponuje
  respondenta jako kolor, respond przesuwa kolejkę, poza kolejnością/brak okna/zły typ/zagnieżdżanie
  → 422, close czyści, wszystkie typy okien akceptowane.

**Frontend:**
- [x] `entities/data/types.ts`: typ `PendingWindow` + pole `GameState.pendingWindow`.
- [x] `api/useBoardEditor.ts`: akcje `respondWindow(playerId, decision?)` i `closeWindow()`
  (POST + invalidate web-data → panel odświeża się natychmiast).
- [x] `domains/game-shell/components/GameStatePanel.tsx`: komponent `WindowSection` renderowany
  NA GÓRZE `PlateBody` (okno reakcyjne ma priorytet). Baner „Reaguje: <gracz>" (spójny z pickerem
  fazy strategii), licznik „Pozostało w kolejce", przyciski „Wykonaj"/„Pas" (adresują
  `currentResponderId`); po zakończeniu kolejki przycisk „Zamknij okno". Etykiety typów okien PL.

**Rezultat (zweryfikowany E2E):** open (initiator p1, 3 graczy) → kolejka green,blue (p1 pominięty);
respond green → responder blue; respond blue → isComplete; close → null. Decyzje w T2 to etykiety
(„secondary"/„pass") — efekty konkretnych okien dojdą od T3.

**QA:** backend 218 testów zielonych (było 209, +9), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste. Warn o rozmiarze chunku i StarletteDeprecationWarning bez zmian.

**Następny krok:** T3 — pierwsze realne okno: secondary karty strategii. Zagranie karty otwiera
pozostałym graczom okno; respond dla secondary zużywa żeton strategiczny / pas. Potrzebne
potwierdzenie reguł primary/secondary konkretnej karty (RULES.md — do uzupełnienia ze źródła).

### ✅ Blok E8-T3 — pierwsze realne okno: secondary karty strategii (ukończony)

**Cel:** zagranie karty strategii rozstrzyga PRIMARY aktywnego gracza i OTWIERA okno
secondary dla pozostałych (kolejka po kolei). Pierwsza realna mechanika na modelu okien
(T1/T2). Reguła: RULES.md 30 (źródło: lokalny LRR 2.0 `docs/rules_tirules/R_strategic_action.md`
+ `R_leadership.md`; parametry z `assets/data/strategy_cards/pok.json`).

**Zakres (świadomy szkielet — „make it exist first", z haczykami pod rozbudowę):**
- Leadership primary: +3 żetony dowodzenia (do puli taktycznej — ⚠️ ZAŁOŻENIE: docelowo wybór puli).
- Secondary: mechanika okna (kolejka, wykonaj/pas) działa end-to-end; efekt „wykonaj" to
  NA RAZIE NO-OP (kupno żetonów za wpływ odłożone do modelu wpływu — jawne TODO w kodzie).
- Pozostałe karty: dispatch zwraca „brak efektu" — szkielet okna i tak działa.

**Backend:**
- [x] `src/core/strategic_action.py` (NOWY): `play_strategy_card` (primary dispatch + exhaust
  karty + otwarcie okna STRATEGY_SECONDARY z kolejką pozostałych), `resolve_secondary`
  (dispatch secondary + `timing.respond_current` + auto-zamknięcie po dopełnieniu).
  DISPATCH po inicjatywie (`_PRIMARY_EFFECTS`/`_SECONDARY_EFFECTS`) — rozszerzalny kartą po
  karcie, nie `if` w endpointcie. Kontekst okna niesie `initiative`.
- [x] `src/api/schemas.py`: `StrategySecondaryRequest` (player_id + execute).
- [x] `src/api/routers/strategy.py`: `/strategy/play` przekierowane na `strategic_action`
  (primary + okno; zastępuje dawne „tylko oznacz zagraną"); nowy `/strategy/secondary`.
- [x] `tests/test_strategic_action.py` (10) + `tests/test_strategic_action_api.py` (4).

**Frontend:**
- [x] `api/useBoardEditor.ts`: akcja `strategySecondary(playerId, execute)`.
- [x] `GameStatePanel.tsx` `WindowSection`: przyciski Wykonaj/Pas routowane po TYPIE okna —
  STRATEGY_SECONDARY → `/strategy/secondary` (efekt + kolejka), inne → generyczny `/window/respond`.

**Rezultat (zweryfikowany E2E):** play Leadership (p1) → tactical_cc 3→6, karta zagrana, okno
secondary queue [green,blue] responder p2; secondary p2(exec)→p3, p3(pass)→okno zamknięte (null).

**QA:** backend 232 testy zielone (było 218, +14), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T4 — pojęcie aktualnego gracza w STATUS/AGENDA + twarda walidacja flow
(czyja tura / co teraz wolno). Potem pozostałe karty strategii i model wpływu (odblokuje
realne secondary).

### ✅ Blok E8-T4 — twarda walidacja flow fazy akcji + aktywny gracz (ukończony)

**Cel:** pierwszy element „sędziego" (RULES.md 29.1) — zwykłe akcje flow walidowane TWARDO.
Reguła: RULES.md 31 (źródło: lokalny LRR 2.0 — R_active_player, R_action_phase, R_initiative_order,
R_status_phase, R_agenda_phase).

**Korekta względem pierwotnego zamysłu T4 (wymuszona regułą):** LRR mówi wprost „during the
strategy, status and agenda phases, NO player is the active player". Dlatego NIE wprowadzamy
sztucznego „aktywnego gracza" w STATUS/AGENDA — `active_player_id` pozostaje None (tak jak było).
Kolejność czynności w tych fazach to KOLEJKA (initiative dla statusu, speaker order dla agendy),
która wejdzie w etapach E5/E6 na modelu okien czasowych. T4 kładzie fundament + walidację akcji.

**Backend:**
- [x] `src/core/turn_flow.py`: `_require_action_turn` (faza ACTION + tożsamość aktywnego gracza);
  `end_turn(state, player_id=None)` i `pass_turn(state, player_id=None)` walidują twardo
  (ValueError). `pass_turn` dodatkowo: nie wolno pasować przed akcją strategiczną (gracz z kartą
  musi ją zagrać — `exhausted_strategy_cards`). Alias `initiative_order = turn_order` (status).
  God-Mode omija (osobny kanał). `player_id=None` zachowuje zgodność wsteczną (faza wciąż sprawdzana).
- [x] `src/api/schemas.py`: `TurnActionRequest` (opcjonalny player_id).
- [x] `src/api/routers/flow.py`: `/turn/end`, `/turn/pass` przyjmują body z player_id, mapują
  ValueError → 422.
- [x] `tests/test_turn_flow.py`: fixture gra z ZAGRANYMI kartami (by móc pasować) + 5 nowych
  testów walidacji (zła faza, cudza tura, pas przed akcją strategiczną, pas bez karty dozwolony,
  alias inicjatywy).

**Frontend:**
- [x] `api/useBoardEditor.ts`: `endTurn(playerId?)`/`passTurn(playerId?)` wysyłają player_id.
- [x] `GameStatePanel.tsx`: `PhaseControls` dostaje `activePlayerId` (z `active.discordId`) i
  przekazuje go do endTurn/passTurn — backend waliduje, że to tura tego gracza.

**Rezultat (zweryfikowany E2E):** p2 kończy turę p1 → 422; p1 pasuje bez akcji strategicznej →
422; p1 kończy turę → 200, aktywny p2; end/pass w fazie statusu → 422.

**QA:** backend 237 testów zielonych (było 232, +5), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T5 — ruch jako funkcja core (`core/movement.py`) + walidacja legalności ruchu
(zasięg z UnitDef, anomalie/przejezdność, aktywny system). Pierwsza twarda egzekucja mechaniki
taktycznej.

### ✅ Blok E8-T5 — ruch statków jako funkcja core + walidacja legalności (ukończony)

**Cel:** pierwsza twarda egzekucja mechaniki TAKTYCZNEJ — ruch przestaje być tylko God-Mode,
staje się walidowaną akcją. Reguła: RULES.md 32 (źródło: LRR R_movement + R_tactical_action).

**Reguły egzekwowane (R1–R6):** cel = aktywny system; zasięg ≤ moveValue (z UnitDef); start nie
z systemu z własnym CC (poza aktywnym); trasa nie przez obce statki (fightery też blokują); przez
własne CC można; anomalie (supernova nieprzejezdna, asteroid bez Antimass, nebula nieprzejezdna
jako węzeł pośredni). Pathfinding: BFS po grafie sąsiedztwa z filtrem węzłów pośrednich.

**Backend:**
- [x] `src/core/movement.py` (NOWY): `can_move` (walidacja R1–R6, zwraca powód) + `move_ships`
  (wykonanie: przenosi stos statków ze źródła do aktywnego). BFS `_shortest_legal_distance`.
  Antimass Deflectors: alias `amd` z danych (weryfikowany testem). Czyste funkcje state→state.
- [x] `src/api/schemas.py`: `MoveShipsRequest`.
- [x] `src/api/routers/tactical.py`: `POST /tactical/move` (walidowany; 422 na nielegalny ruch).
  W odróżnieniu od God-Mode `/units/move` (bez reguł).
- [x] `tests/test_movement.py` (NOWY, 10): ruch sąsiedni, brak aktywnego, zasięg, blokada obcymi
  statkami, start z własnym CC, supernova, asteroid+Antimass, fighter bez moveValue, za mało statków.

**Frontend:**
- [x] `api/useBoardEditor.ts`: akcja `moveShips({fromPosition, baseType, count, faction})` →
  `/tactical/move` (ruch walidowany; God-Mode drag-and-drop zostaje jako wentyl bez reguł).

**Zakres (świadomy szkielet, RULES.md 32.1):** ruch pojedynczego stosu jednego typu; transport
przez capacity = TODO (dlatego fighter sam nie rusza — nie ma moveValue, co jest regułowo poprawne);
wybór trasy pod gravity rift = TODO. UI picker ruchu dołożymy osobno (akcja w hooku już jest).

**Rezultat (zweryfikowany E2E):** /tactical/move przenosi destroyer 101→000 (aktywny); ruch bez
aktywnego systemu → 422 „Brak aktywnego systemu".

**QA:** backend 247 testów zielonych (było 237, +10), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T6 — walidacja aktywacji / przejęcia planety / produkcji (koszty, limity,
legalność) — domknięcie egzekucji fazy akcji poza walką.

### ✅ Blok E8-T5b — poprawki zgłoszone przez użytkownika (ukończony)

Trzy uwagi z testów użytkownika, naprawione przed T6:

1. **Ikony jednostek w panelu produkcji za duże (UI).** Sprite jednostki renderował się
   w naturalnym rozmiarze i wylewał poza pudełko 26×26. Naprawa (CSS
   `GameStatePanel.module.css`): `.unitTileIcon` dostał `overflow: hidden`, a wewnętrzny
   kontener sprite'a `transform: scale(0.42)` — ikona mieści się w kafelku.

2. **Nie dało się ZAGRAĆ karty strategii (brakujący przycisk).** Zakładka „Strategiczna" w
   panelu akcji miała tylko notkę „rozlicz przy stole" (relikt starej filozofii), bez przycisku
   wołającego `/strategy/play` (dodany w T3). Naprawa: nowy komponent `StrategicActionControl`
   w `GameStatePanel.tsx` — listuje karty aktywnego gracza i pozwala je zagrać (primary + okno
   secondary). Zagrana karta pokazuje się jako „zagrana".

3. **BŁĄD REGUŁY: Fighter II nie mógł się ruszać.** `movement.can_move` czytał `moveValue`
   z BAZOWEGO wpisu jednostki (`registry.units.get("fighter")` → move=None), ignorując
   ulepszenie. Fighter II (tech `ff2`) ma `moveValue=2`. Naprawa: `can_move` używa teraz
   `combat.resolve_unit_variant(registry, faction, technologies, base_type)` — wariant GRACZA
   wg posiadanych technologii (spójne z walką/produkcją, RULES.md 10/20). Bazowy fighter nadal
   nie rusza się sam (porusza się transportem — capacity TODO), ale Fighter II już tak.
   Zaktualizowano RULES.md 32.1 R2 + nowy test `test_fighter_ii_can_move_with_upgrade`.

**QA:** backend 248 testów zielonych (było 247, +1), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

### ✅ Blok E8-T6 — walidacja aktywacji + produkcji (ukończony)

**Cel:** domknięcie twardej egzekucji fazy akcji poza walką. Reguła: RULES.md 33 (źródło LRR
R_active_system, R_production, R_producing_units). Opcja „b" (ustalona z użytkownikiem): koszt
produkcji SPRAWDZANY, bez realnego wydawania zasobów.

**Aktywacja (RULES.md 33.1) — twardo:**
- [x] `core/tactical.activate_system`: odrzuca aktywację systemu z WŁASNYM żetonem gracza;
  wymaga ≥1 żetonu w puli taktycznej (było: tylko „dekrementuj jeśli >0"). God-Mode
  (`place_command_token`) nadal omija. Zaktualizowany docstring (zdjęta adnotacja „nie waliduje").

**Produkcja (RULES.md 33.2) — limit/blokada twardo, koszt jako sprawdzenie:**
- [x] `src/core/models.py`: pola `production_value` (int|str) + `basic_production` w UnitDef
  (dane: dok bazowy „+2" = zasoby planety + 2; Saar dok = 5 liczbowo).
- [x] `src/core/production.py` (NOWY): `production_limit` (suma PRODUCTION jednostek gracza w
  aktywnym systemie; modyfikator „+N" rozwiązywany względem planety doku), `available_budget`
  (gotowe planety + TG), `validate_production` (koszt ≤ budżet, liczba ≤ limit, blokada statków
  przy obcych statkach; fighter/infantry para za koszt). Czyste funkcje.
- [x] `src/api/schemas.py`: `ProduceOrderItem` + `ProduceRequest`.
- [x] `src/api/routers/tactical.py`: `POST /tactical/produce` (waliduje całe zamówienie → 422,
  przy sukcesie stawia jednostki przez edit_units). Obok God-Mode edit-units (bez reguł).
- [x] `tests/test_production.py` (NOWY, 9) + aktualizacja `tests/test_tactical.py` (testy
  walidacji aktywacji zamiast idempotentności).

**Frontend:**
- [x] `api/useBoardEditor.ts`: akcja `produce(faction, orders)` → `/tactical/produce`
  (walidowana; God-Mode edit zostaje jako wentyl). Pełny picker produkcji w panelu = refinement.

**Zakres (świadomy, opcja „b"):** koszt to SPRAWDZENIE (budżet = gotowe planety + TG), bez
wyczerpywania planet/zdejmowania TG — realne wydawanie dojdzie z modelem wpływu. Component
limitations (rezerwy) = TODO.

**Rezultat (zweryfikowany E2E):** produkcja 2 cruiserów (koszt 4, budżet 4, limit 6) → 200 +
postawione; 3 cruisery (koszt 6 > budżet 4) → 422 „Za mało zasobów".

**QA:** backend 258 testów zielonych (było 248, +10), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T7 — walka: rdzeń (rzuty seedowalnym RNG + liczenie trafień + okno „przypisz
straty", wielorundowo). Pierwsza wersja pełnej walki rozstrzyganej przez silnik.

### ✅ Blok E8-T6b — podłączenie walidacji do UI + komunikaty + poprawka ikon (ukończony)

Trzy problemy zgłoszone przez użytkownika: walidacja T6 istniała w backendzie, ale UI jej
nie wołało (szło przez God-Mode), brak komunikatów, ikony produkcji nadal złe.

1. **Walidacja nie działała w UI, bo panele szły przez God-Mode.** Produkcja (przyciski +)
   wołała `editUnit` (God-Mode, bez reguł) zamiast `/tactical/produce`. Naprawa:
   `ProductionPanel` — dodawanie (`+`) idzie teraz przez walidowany `produce(faction, orders)`
   (koszt/limit/blokada, RULES.md 33.2); usuwanie (`−`) zostaje God-Mode (korekta, nie reguła).
   Aktywacja już wołała `/tactical/activate` (walidowane w T6), brakowało tylko komunikatu.

2. **Brak komunikatów o odrzuceniu.** Dodano slice `notice` w `appStore` (setNotice/clearNotice)
   + komponent `NoticeBanner` na górze panelu gry + CSS. `useBoardEditor.post()` parsuje `detail`
   z 422 i ustawia notice — każda odrzucona akcja (np. „Nie można aktywować systemu, w którym
   masz już żeton dowodzenia", „Za mało zasobów") pokazuje baner. Wcześniej błąd był cicho połykany.

3. **Ikony jednostek w produkcji źle skalowane.** Poprzedni `transform: scale(0.42)` obcinał
   grafikę. Naprawa: zdjęto transform; sprite (`.unit-sprite`, skalowany procentowo do własnego
   pudełka) dostał jawny rozmiar 24×24 w `.unitTileIcon` — bez obcinania.

**Rezultat (zweryfikowany E2E):** ponowna aktywacja systemu → 422 „Nie można aktywować systemu,
w którym masz już żeton dowodzenia" (pokazane jako baner); produkcja ponad budżet → baner
„Za mało zasobów".

**QA:** backend 258 testów zielonych (bez zmian logiki), ruff + mypy czyste. Frontend
type-check + lint + build czyste.

### ✅ Blok E8-T6c — wskaźnik limitu produkcji (sprocket) + komunikat limitu (ukończony)

Dwie uwagi użytkownika: pokazać w panelu wartość PRODUCTION w systemie z ikoną AsyncTI4
(koło zębate „production_representation.png") oraz komunikat przy przekroczeniu limitu.

**Backend:**
- [x] `src/api/schemas.py`: `ProductionHelpResponse.production_limit` (alias `productionLimit`).
- [x] `src/api/routers/tactical.py`: `GET /tactical/production` liczy limit przez
  `production.production_limit` (suma PRODUCTION jednostek gracza w aktywnym systemie, z
  rozwiązaniem modyfikatora doku „+N" względem planety). Komunikat limitu już działał
  (`validate_production` → „Limit produkcji przekroczony" → 422 → baner notice z T6b).

**Frontend:**
- [x] `api/useBoardEditor.ts`: `ProductionHelp.productionLimit`.
- [x] `GameStatePanel.tsx` `ProductionPanel`: nagłówek pokazuje wskaźnik PRODUCTION — koło
  zębate (ta sama grafika CDN co na mapie, `cdnImage("/tiles/production_representation.png")`)
  z nałożoną liczbą = limit sztuk. Obok dotychczasowe „X zasobów".
- [x] CSS: `.prodStats/.prodLimit/.prodLimitIcon/.prodLimitValue` (ikona 22×22 + liczba z obrysem).

**Rezultat (zweryfikowany E2E):** `/tactical/production` zwraca `productionLimit=6` (dok „+2" na
Jord res 4); produkcja 7 piechoty > limit 6 → 422 „Limit produkcji przekroczony" (baner).

**QA:** backend 258 testów zielonych, ruff + mypy czyste. Frontend type-check + lint + build czyste.

### ✅ Blok „domknięcie fazy strategii" (feature `strategy-phase-complete`, ukończony)

**Cel:** domknąć FAZĘ STRATEGII TI4 (PoK, zestaw `pok`) na istniejącym fundamencie E1–E2 —
DOBUDOWA walidacji i brakującej logiki (silnik-SĘDZIA, RULES.md 29/13), NIE przepisywanie.
Spec: `.kiro/specs/strategy-phase-complete/`. Reguła przed kodem (zasada projektu).

**Reguła (RULES.md 13 rozszerzona, źródło: tirules `R_strategy_phase.md` + LRR „Strategy Phase"):**
- `Pick_Count` zależny od liczby graczy: **3–4 → 2 karty/gracz**, **5–8 → 1 karta/gracz**;
  liczba graczy <3 lub >8 = NIEOBSŁUGIWANA (błąd, bez zmiany stanu).
- **Druga runda wyboru (tylko 3–4 graczy):** po pierwszej rundzie wybór wraca do mówcy i idzie
  ponownie w speaker order, aż każdy ma `Pick_Count` kart (mechanicznie: „następny wybierający"
  = pierwszy w speaker order poniżej `Pick_Count`, bez osobnego licznika rund).
- **Walidacja przejścia STRATEGY→ACTION:** fazy nie można zakończyć, dopóki każdy gracz nie ma
  `Pick_Count` kart; kolejność tur fazy akcji ustala inicjatywa (RULES.md 9).

**Backend (`core/` → `api/`, QA zielone po każdym bloku):**
- [x] `core/strategy_phase.py`: nowa `pick_count` (3–4→2, 5–8→1; <3/>8 → `ValueError`);
  przebudowany `next_strategy_picker` (pierwszy w speaker order poniżej `Pick_Count`; <3 graczy
  → `None` przez złapanie `ValueError` — zgodność wsteczna wywołań wewnętrznych); rozszerzony
  `pick_strategy_card` (walidacja kolejności + limitu `Pick_Count` + sortowanie listy kart,
  zachowane dotychczasowe walidacje i transfer TG); nowa `ensure_strategy_complete` (kontrola
  kompletu wyboru); guard w `accumulate_unpicked_tg` (akumulacja TG dopiero po zakończeniu fazy);
  nowa `validate_strategy_card_set` (komplet/unikalność 8 kart, `Initiative` 1–8).
- [x] `core/turn_flow.py`: nowa `strict_initiative_order` (permutacja graczy wg rosnącej
  inicjatywy; gracz bez karty → `ValueError`); `next_phase` przy STRATEGY→ACTION woła
  `ensure_strategy_complete` PRZED zmianą fazy i ustawia `active = strict_initiative_order[0]`.
- [x] API: `routers/flow.py` — `/phase/next` i `/round/next` owinięte w try/except → HTTP 422;
  `routers/strategy.py` — `GET /strategy/cards` z guardem rejestru (`validate_strategy_card_set`)
  i kompletu pól per-karta → 422; `web_data.py` — ADDYTYWNE pole pochodne `strategyPickCount`
  (`_safe_pick_count` łapie `ValueError` → `None`, web-data nie rzuca).
- [x] Testy backendu zaktualizowane pod `Pick_Count=2` i fikstury ≥3 graczy (zadanie 5);
  5–8-osobowe scenariusze bez zmian. Pełny pytest zielony.

**Frontend (bramka type-check + lint + build):**
- [x] `GameStatePanel`: `allPicked` liczone z `gameState.strategyPickCount`
  (`scs.length >= pickCount`) zamiast samej obecności kart.
- [x] NOWY `StrategyCardTable` (karty „na stole" z pełną grafiką, stanem wybrania + właściciel,
  wskazaniem pickera/mówcy, banerem fazy; interakcja wyboru z blokadą poza kolejnością i fallbackiem
  tekstowym przy braku/błędzie grafiki). Montaż w `MapView`/`PannableMapView`, render tylko w fazie
  strategii.
- [x] NOWY `PhaseTransitionBanner` (baner przy zmianie GŁÓWNEJ fazy — jednorazowo na przejście,
  animacja fade/scale, auto-ukrycie ≤5 s, `pointer-events: none`, fallback tekstowy; dźwięk
  `phase_change.mp3` z cichą degradacją — 404/zablokowany autoplay nie psują banera).

**Decyzje projektowe:**
- **Silnik-SĘDZIA:** wszystkie nowe walidacje reguł rzucają `ValueError` → mapowane na HTTP 422
  (RULES.md 29.1). Nielegalny wybór / przedwczesne przejście / niespójny zestaw = odrzucone bez
  zmiany stanu.
- **God-Mode NIETKNIĘTY** jako wentyl — kanał ręcznej korekty (`/god-mode/patch`,
  `core/board_edit.*`) nadal omija walidację reguł.
- **Grafika kart** pobierana z danych `Strategy_Router` (`imageURL`, źródło ti4ultimate.com);
  fallback tekstowy, gdy brak/błąd.
- **Priorytet źródeł kart strategii (uzupełnienie):** ustalono `thunders_edge > pok > codex4..1 >
  base` — gdy wiele włączonych źródeł dostarcza wariant tej samej karty (Construction 4 / Warfare 6),
  wygrywa wariant z najwyższego źródła (Thunder's Edge). Dodano FALLBACK GRAFIKI w lookupie frontu
  (`entities/lookup/strategyCards.ts`): gdy wariant najwyższego źródła nie ma obrazu, UI bierze
  grafikę wariantu o tej samej initiative z niższego źródła (treść/parametry bez zmian). Usunięto
  hardkodowaną `defaultStrategyCardIdMap`. Szczegóły: RULES.md 14.
- **Baner/dźwięk fazy:** zasób pod ścieżką względną `/static/extra/...` (baner) i
  `/static/extra/sounds/...` (dźwięk); dźwięk i baner rozłączone (degradacja niezależna).

**QA (pełna bramka — wszystko zielone):** backend `uv run pytest -q` → **262 passed**;
`uv run ruff check src tests` → czyste; `uv run mypy src tests` → czyste (61 plików). Frontend:
`npm run type-check` → czyste; `npm run lint` → czyste; `npm run build` → OK (znana, nieblokująca
notka o rozmiarze chunku). Ostrzeżenie `StarletteDeprecationWarning` bez zmian (znane).

**Refaktoryzacja po przeglądzie semantycznym (`semantic-review/2026-11-01-005022-strategy-phase-review.md`,
znaleziska #1/#2/#3/#4/#7, czysto backendowa, zero zmian kontraktu z frontem):**
- [x] **Spójna obsługa liczby graczy spoza 3–8 w guardzie akumulacji (#2/#3):** `accumulate_unpicked_tg`
  woła teraz `ensure_strategy_complete` (które woła `pick_count` BEZPOŚREDNIO) zamiast wnioskować
  z `next_strategy_picker(state) is not None`. Dawny guard był dziurawy: `next_strategy_picker`
  łapie `ValueError` z `pick_count` i zwraca `None`, więc przy 2 graczach `/round/next`
  przepuszczało akumulację. Teraz <3/>8 graczy → `ValueError` (odrzucone), niekompletny wybór →
  zachowany komunikat „Nie można akumulować: faza strategii niezakończona.".
- [x] **Twarda kontrola `seating_order == players` przy przejściu STRATEGY→ACTION (#1):**
  `ensure_strategy_complete` sprawdza (dla niepustej `seating_order`) spójność ze zbiorem graczy
  i daje czytelny błąd ZANIM `strict_initiative_order` rzuci mylące „Gracz X nie ma karty"
  (realny edge-case: God-Mode dodaje gracza bez aktualizacji listy miejsc). Puste `seating_order`
  nietknięte.
- [x] **Walidacja pól karty przeniesiona do `core/` (#4):** `_ensure_card_fields_complete` z
  `api/routers/strategy.py` → nowa czysta funkcja `core.strategy_phase.ensure_card_fields_complete`,
  wołana wewnątrz `validate_strategy_card_set` (dostępna też dla przyszłego `ai/`). Router tylko
  woła `validate_strategy_card_set` i mapuje `ValueError`→422 (kontrakt bez zmian).
- [x] **Testy brzegowe (#7):** `tests/test_strategy_phase.py` + `tests/test_turn_flow.py` —
  rozjazd seating_order↔players, akumulacja przy 2 graczach, zachowany komunikat niekompletnego
  wyboru, walidacja pól karty w core, regresja poprawnego stanu 3 graczy.
- **QA po refaktorze:** `uv run pytest -q` → **269 passed**; ruff + mypy czyste.

**Znalezisko #5 — wybór wariantu kart strategii przeniesiony do CORE (część backendowa):**
Wcześniej priorytet źródeł kart (`thunders_edge > pok > codex4..1 > base`) żył TYLKO we froncie
(`entities/lookup/strategyCards.ts`), a backend zwracał zawsze twardy zestaw `pok` — przez co
`/strategy/cards` i web-data serwowały `pok4construction`/`pok6warfare` nawet przy włączonym
Thunder's Edge. Teraz reguła wyboru kanonicznego zestawu jest w `core/`:
- [x] `core/registry.py`: nowa czysta metoda `active_strategy_card_set_alias()` — wybiera alias
  zestawu o NAJWYŻSZYM włączonym źródle wg `_STRATEGY_SET_SOURCE_PRIORITY`
  (`thunders_edge > pok > codex4..1 > base`; homebrew ignorowane; fallback `pok`). `strategy_card_set`
  ma teraz `set_alias: str | None = None` — bez jawnego aliasu zwraca zestaw kanoniczny.
- [x] `core/strategy_phase.py`: `available_initiatives`, `pick_strategy_card`, `accumulate_unpicked_tg`,
  `validate_strategy_card_set` — domyślny `set_alias` zmieniony z twardego `"pok"` na `None`
  (kanoniczny). Jawny alias nadal dostępny (kompatybilność/testy).
- [x] `api/web_data._build_strategy_cards`: `registry.strategy_card_set()` bez aliasu → automatycznie
  kanoniczny (zmiana kontraktu POŻĄDANA: te4/te6 przy TE).
- **Zweryfikowane:** przy obecnym `enabled_sources.json` (base, pok, codex1–4, thunders_edge)
  `active_strategy_card_set_alias()` → `"te"` (Construction=`te4construction`, Warfare=`te6warfare`,
  reszta PoK); bez TE → `"pok"`. Karty `te4construction`/`te6warfare` mają KOMPLET pól
  (nazwa/primary/secondary/kolor), więc `validate_strategy_card_set` na zestawie TE przechodzi.
- [x] Testy: `tests/test_registry.py` (wybór aliasu + skład kanonicznego zestawu + jawny alias) +
  `tests/test_strategy_phase.py` (walidacja kanonicznego zestawu TE). Reguła: RULES.md 14.
  Część frontendowa (konsumpcja kanonicznych wariantów) pójdzie osobno.

### ✅ Blok E8-T6d — wskaźnik produkcji NA KAFELKU (nie w panelu) (ukończony)

Korekta po uwadze użytkownika: wskaźnik PRODUCTION (koło zębate) ma się pokazywać NA KAFELKU
mapy (jak w AsyncTI4), nie w panelu produkcji. Funkcjonalność renderu już istniała we froncie
(`ProductionIndicator` + `SystemIndicatorsLayer` w `MapTile`), ale NIE dostawała danych — backend
wysyłał `tileUnitData[pos].production = {}` (puste), więc `Math.max([])` = -Infinity i wskaźnik
nigdy się nie renderował (`highestProduction > 0` fałszywe).

**Backend (naprawa źródła danych):**
- [x] `src/core/production.py`: wydzielono `system_production_value(state, grid, registry,
  player_id, position)` (suma PRODUCTION w DOWOLNYM systemie); `production_limit` deleguje do
  niego dla `active_system`.
- [x] `src/api/web_data.py`: helper `_tile_production` wypełnia `tileUnitData[pos].production`
  mapą `{kolor_gracza: wartość}` (pomija ≤0; klucz = kolor jak reszta sygnałów mapy). Import
  `production`.

**Frontend (cofnięcie wskaźnika z panelu):**
- [x] `GameStatePanel.tsx`: usunięto wskaźnik PRODUCTION z nagłówka panelu produkcji (dodany
  błędnie w T6c) + nieużywany import `cdnImage`. Panel pokazuje tylko „X zasobów".
- [x] `GameStatePanel.module.css`: usunięto CSS `.prodStats/.prodLimit/...`.
  (`ProductionHelpResponse.production_limit` zostaje w kontrakcie — nieszkodliwe, może się przydać.)

**Rezultat (zweryfikowany E2E):** `tileUnitData["000"].production = {"red": 6}` (dok „+2" na Jord
res 4 = 6). Mapa renderuje koło zębate z „6" na kafelku — jak w AsyncTI4.

**QA:** backend 262 testy zielone, ruff + mypy czyste. Frontend type-check + lint + build czyste.

### ✅ Blok E8-T7 — zasada „zawsze czyjaś tura" + mówca ogłasza tranzycję (ukończony)

**Cel (ustalony z użytkownikiem):** fundament pod docelowo do 6 ludzkich graczy (hot-seat /
sieć) i bota AI — w toczącej się partii ZAWSZE wiadomo, czyja jest tura. Koniec tury/fazy to
TRANZYCJA ogłaszana przez mówcę, nie stan „niczyjej tury" (`None`).

**Decyzja projektowa (⚠️ odejście od LRR) — RULES.md 31.4:** oficjalna reguła (R_active_player)
mówi „during the strategy, status and agenda phases, no player is the active player". Świadomie
od niej odchodzimy: `active_player_id` w partii ≥2 graczy nigdy nie jest `None` (także w STRATEGY
/ STATUS / AGENDA). `None` pozostaje legalny TYLKO poza rozgrywką (0–1 graczy, pusty setup,
God-Mode budujący stół). Brak auto-tranzycji: przejście fazy ogłasza mówca przez `/phase/next`.

**Core (`turn_flow.py`):**
- [x] `end_turn`/`pass_turn`: gdy brak następnego niespasowanego → `active_player_id = speaker_id`
  (faza nadal ACTION), zamiast `None` + skok do STATUS. Okna czasowe końca tury/fazy zostają otwarte.
- [x] `next_phase`: STATUS/AGENDA → aktywny = pierwszy wg inicjatywy (`turn_order`), fallback mówca;
  STRATEGY → picker ∥ mówca; ACTION bez zmian (initiative[0]).
- [x] `next_round`: picker ∥ mówca.

**Core (`strategy_phase.py`):**
- [x] `pick_strategy_card` / `reset_strategy_cards`: po komplecie wyboru aktywny = mówca (nie `None`).

**API (`routers/flow.py`):**
- [x] `/phase/next` przyjmuje opcjonalny `player_id`; gdy podany, musi być `speaker_id` (inaczej 422,
  „Only the speaker announces a phase transition"). Pominięty = zgodność wsteczna. God-Mode omija.
- [x] `/speaker/set`: w STRATEGY po komplecie wyboru aktywny = nowy mówca (nie `None`).

**Projekcja (`web_data.py`):**
- [x] `_effective_active_id`: zaktualizowany komentarz — stan active+passed powstaje teraz także
  normalnie (wszyscy spasowali → aktywny = mówca, też `passed`). Panel nie podświetla wtedy
  aktywnego (spójność `active`/`passed`), ale `isSpeaker` niesie informację „kto ogłasza".

**Testy:** +7 (łącznie 467 zielonych). `test_turn_flow.py`: STATUS/AGENDA wskazują initiative[0];
pas ostatniego gracza → ACTION + mówca (bez skoku do STATUS); end_turn nie wyczerpuje aktywnego.
`test_strategy_phase.py`: po komplecie wyboru aktywny = mówca. `test_api.py`: `/phase/next`
odrzuca nie-mówcę (422), przyjmuje mówcę, działa bez `player_id` (legacy).

**QA:** `uv run pytest -q` (467 passed), `uv run ruff check src tests` (All checks passed!),
`uv run mypy src tests` (Success, 110 plików).

**Otwarte (do decyzji użytkownika):** czy panel tury ma podświetlać mówcę jako „active" także
gdy wszyscy spasowali (dziś: null, bo mówca jest passed — zachowanie z Bug 7). Zmiana dotyczy
tylko warstwy wyświetlania, nie stanu.

### ✅ Blok local-ti4-data-foundation 1.1 — `core/sources.py` + stałe w `config.py` (ukończony)
- `src/config.py`: katalogi danych nowych kategorii (karty akcji, agendy, cele, attachmenty, eksploracje, relikty, promissory, żetony, anomalie graniczne, wydarzenia, karty generyczne, talie), `AUDIT_DIR`, `EFFECTS_STATUS_PATH`, `FRONTEND_DIR`.
- `src/core/sources.py`: `SOURCE_PRIORITY` (RULES.md 14), `source_rank`, `known_source_ids`, `validate_enabled_sources`, `UnknownSourcesError`.
- `StaticDataRegistry`: `_STRATEGY_SET_SOURCE_PRIORITY` = `SOURCE_PRIORITY` (bez zmiany zachowania); `__init__` waliduje źródła przed `_load()`.
- Test `test_registry` używał nieistniejącego źródła `anarchy` → zastąpione znanym homebrew `absol`. Nowe testy: `tests/test_sources.py`.
### ✅ Blok local-ti4-data-foundation 8.1 — `src/audit/locality.py` + pliki konfiguracyjne `audit/` (ukończony)
- `src/audit/locality.py`: czyste funkcje nad tekstem `find_reference_path_usage` (literały kodu poza docstringami; nazwy folderów referencyjnych podaje wołający, nie ma ich w kodzie produkcyjnym), `find_outside_root_reads`, `find_external_urls` (hosty lokalne + lista dozwolona po granicy segmentu) oraz cienka otoczka (`collect_sources`, `scan_external_urls`, `load_allowlist`, `load_unused_asset_dirs`).
- `audit/expected_gaps.json` (`[]`), `audit/external_url_allowlist.json` (D2), `audit/unused_asset_dirs.json` (D8, nic nie jest usuwane).
- Test: `tests/test_audit_locality.py`. Skan realnego `src/` i `scripts/`: zero odwołań do folderów referencyjnych w kodzie i zero odczytów spoza korzenia.
### ✅ Blok local-ti4-data-foundation 2.1 — `core/components.py` (ukończony)
- `src/core/components.py`: `ComponentCategory`, `ComponentRef`, `ComponentBase` (pole `raw` z surowym JSON), modele kategorii (`ActionCardDef`, `AgendaDef`, `ObjectiveDef`, `AttachmentDef`, `ExplorationDef`, `RelicDef`, `PromissoryNoteDef`, `TokenDef`, `BorderAnomalyDef`, `GalacticEventDef`, `GenericCardDef`, `DeckDef`).
- `CATEGORY_SPECS` = jedyne miejsce kształtów JSON (`alias` vs `id`, pola tekstowe, pole okna); `build_component` łączy `flavorText`/`flavourText`, `cardIDs` rozcina po białych znakach. Zero hardkodowanych komponentów.
- `ComponentCatalog`: `get`, `all`, `counts`. Test: `tests/test_components.py`. Wszystkie realne wpisy 13 kategorii walidują się w modelach.
### ✅ Blok local-ti4-data-foundation 1.2 — test właściwościowy walidacji źródeł (ukończony)
- `tests/test_source_selection_props.py`: Property 3 (Hypothesis, 100 przykładów) — `validate_enabled_sources` zgłasza `UnknownSourcesError` wtedy i tylko wtedy, gdy są identyfikatory spoza zbioru znanych, a wyjątek wymienia dokładnie te nieznane. Validates: Requirements 4.2.
### ✅ Blok local-ti4-data-foundation 2.2 — `core/component_loader.py` (ukończony)
- `src/core/component_loader.py`: `EntryOrigin`, `iter_entries_with_origin`, `LoadReport` (`loaded`, `skipped`, `skipped_index`, `sourceless`, `invalid_id`, `conflicts`), czysta `select_entries` (filtr po `source`, wpisy bez źródła, wybór po `source_rank`, deterministyczny remis po `(file, index)`), `load_components(enabled)` z walidacją modelu i `DataValidationError(kategoria, plik, id)`.
- `load_components` przyjmuje opcjonalną tabelę `specs` (domyślnie `CATEGORY_SPECS`), co pozwala testować na `tmp_path`. Loader jeszcze nie jest wpięty w rejestr (zadanie 2.3).
- Test: `tests/test_component_loader.py`.

### ✅ Blok local-ti4-data-foundation 7.1 — `core/effects_registry.py` (ukończony)
- `src/core/effects_registry.py`: `EffectStatus` (`not_implemented`/`implemented`/`manual`), niemutowalny `EffectRegistry` (`status_of` z domyślnym `NOT_IMPLEMENTED`, `with_status` zwraca nowy rejestr, `load` z brakiem pliku = pusty, `to_json_dict`), `coverage` per kategoria (CoverageRow: total/implemented/manual/percent) i `resolve_action_card_ref` po `automationID` (z deterministycznym remisem, zapasowo po aliasie). Czysta struktura danych bez importów FastAPI/HTTP; zero logiki efektów jakiejkolwiek karty.
- `assets/config/effects_status.json` (`{}`) z wyjątkiem w `.gitignore` (obok `engine_config.json`).
- Test: `tests/test_effects_registry.py`. QA zielone dla moich plików (pytest 332 passed, ruff + mypy czyste). Wymagania: 9.1–9.7.
### ✅ Blok local-ti4-data-foundation 8.2 — moduły różnic Audytora (ukończony)
- `src/audit/diffs.py`: `IdDiff`, `diff_sets`, `diff_counts` (dokładne różnice tablic liczników kategoria×źródło, regresja względem baseline), `find_gaps` (pary kategoria/źródło kanoniczne z zerem, minus `audit/expected_gaps.json`), `load_expected_gaps`, `load_baseline_counts`.
- `src/audit/assets_manifest.py`: `build_manifest`/`write_manifest`/`load_manifest_paths` (lista `{path,size,sha256}` grafik, ścieżki POSIX względem `assets/`), `diff_manifest` (`missing`/`unused`), `list_asset_files`. Grafiki poza repo (D1) — manifest to jedyny wersjonowany ślad.
- `src/audit/frontend_data.py`: `extract_embedded_ids` (regex po `alias`/`id` tylko na najwyższym wcięciu wpisu TS), `scan_embedded_ids`, `diff_embedded_ids` (`extra`/`missing`, R11.5) nad danymi `frontend/src/entities/data/*.ts`.
- Czyste funkcje bez I/O (poza `load_*`/`build_manifest`), gotowe pod testy właściwościowe 8.6. Test przykładowy: `tests/test_audit_diffs.py`.
- QA: pytest (346 + 7 nowych) zielone, ruff + mypy czyste na plikach bloku.
### ✅ Blok local-ti4-data-foundation 7.2 — `core/rules_links.py` (ukończony)
- `src/core/rules_links.py`: `RulesTopic` (code/category/title), `RulesTopicIndex` z `from_json` (czyta tylko metadane `topics` z `tirules.json`; brak lub uszkodzony plik = pusty indeks) i `match`. Dopasowanie deterministyczne przez RÓWNOŚĆ znormalizowanej nazwy/aliasu (casefold + usunięcie znaków niealfanumerycznych) z tytułem, kodem lub kodem bez prefiksu `X_`; plus temat kategorialny z `CATEGORY_TOPIC_HINTS`. Brak rozmytego dopasowania — brak trafienia daje pustą listę. Moduł czyta wyłącznie metadane tematów; treść tematu to nadal `rules_content.py`, opisy kart pochodzą z JSON (R10.4).
- `CATEGORY_TOPIC_HINTS` mapuje kategorię komponentu (napis = wartość `ComponentCategory`, bez zależności od `components.py`) na kody tematów kategorialnych; nieistniejący w indeksie temat jest pomijany.
- Test: `tests/test_rules_links.py` (normalizacja, równość po tytule/kodzie, brak zgadywania, podpowiedź kategorialna + dedup, pusty indeks przy braku/uszkodzeniu pliku, realny zrzut `docs/rules_tirules/tirules.json`). QA zielone dla moich plików (pytest 346 passed w pełnym zestawie, ruff + mypy czyste dla `rules_links.py` i jego testu). Wymagania: 10.1–10.4.

### ✅ Blok local-ti4-data-foundation 7.4 — testy właściwościowe rejestru efektów (ukończony)
- `tests/test_effects_registry_props.py`: Property 10 i Property 11 (Hypothesis, 200 przykładów każdy).
- Property 10 (Rejestr efektów — domyślny status i zapis statusu): dla referencji spoza kluczy `status_of` zwraca `NOT_IMPLEMENTED`; `with_status` → `status_of` zwraca ustawiony status, statusy innych referencji w nowym rejestrze bez zmian, a rejestr wejściowy pozostaje niezmodyfikowany (niemutowalność). Validates: Requirements 9.1, 9.2.
- Property 11 (Pokrycie efektów ma poprawne granice): dla katalogu i rejestru (również z kluczami osieroconymi) każdy wiersz pokrycia spełnia `0 <= implemented <= total`, `0 <= manual <= total`, `implemented + manual <= total`, `percent_implemented ∈ [0, 100]`, `total == len(catalog.all(kategoria))` (liczone tylko komponenty z katalogu), a kategorie puste nie trafiają do wyniku. Validates: Requirements 9.3.
- Minimalny `ComponentCatalog` budowany z `ComponentBase(id, source)` i `EffectRegistry` z wygenerowanego słownika `ComponentRef -> EffectStatus`; bez ładowania realnych JSON.
- QA zielone dla moich plików: pytest `tests/test_effects_registry_props.py` (2 passed), ruff + mypy czyste. (W pełnym zestawie niezależny błąd w `tests/test_timing_spec_props.py` z równoległego zadania 5.3 — poza zakresem 7.4.) Wymagania: 9.1, 9.2, 9.3.
### ✅ Blok local-ti4-data-foundation 2.3 — wpięcie katalogu w StaticDataRegistry (ukończony)
- `src/core/registry.py`: w `_load()` buduję `registry.catalog` (ComponentCatalog) z wyniku `load_components(self._enabled)` i wystawiam `registry.load_report` (LoadReport). Specyfikacje czasowe (`build_timing_specs`) z kart akcji, zdolności frakcji i liderów (R8.2).
- Istniejące atrybuty rejestru (units/planets/systems/factions/strategy_cards/leaders/abilities/technologies/breakthroughs) bez zmian zachowania. Kolizje `id` w 9 STARYCH kategoriach tylko RAPORTOWANE przez `registry.legacy_id_collisions` (kategoria -> posortowane id); zasada „ostatni wpis wygrywa" zostaje (D9), więc brak regresji.
- Pola `FactionDef.abilities` i `FactionDef.promissory_notes` (alias `promissoryNotes`) były już obecne w `models.py` (dodane wcześniej addytywnie) — wymaganie zadania spełnione.
- Smoke na realnych danych: action_cards 143, agendas 63, decks 25, 13 kategorii w `load_report.loaded`, brak kolizji w starych kategoriach.
- QA zielone: `uv run pytest -q` (365 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste. Wymagania: 4.1, 5.1, 5.4, 5.5.
### ✅ Blok local-ti4-data-foundation 5.3 + 5.4 — testy właściwościowe specyfikacji czasowej (ukończony)
- `tests/test_timing_spec_props.py` (Hypothesis, 200 przykładów na właściwość). Oba zadania trafiają do jednego pliku.
- Property 7 (Specyfikacja czasowa zachowuje tekst okna i zamyka zbiór rodzajów): dla dowolnego tekstu okna i pola fazy `parse_timing` zwraca `None` dla tekstu pustego/samych białych znaków, w przeciwnym razie `raw_text` jest identyczny z wejściem (R8.5), `trigger ∈ TriggerKind` (zbiór zamknięty, R8.1), `phase_raw` równe wejściu, a `phase` różne od `None` tylko gdy `phase_raw` pasuje do `Phase` bez wielkości liter. Validates: Requirements 8.1, 8.3, 8.5.
- Property 8 (Klasyfikacja wyzwalacza deterministyczna i oparta tylko na prefiksie): dla każdego znanego prefiksu (dowolna wielkość liter, dowolne wiodące białe znaki) `classify_trigger`/`parse_timing` dają odpowiadający rodzaj; dla tekstu bez znanego prefiksu → `UNCLASSIFIED` z zachowanym tekstem; dwa wywołania na tych samych danych są równe. Validates: Requirements 8.2, 8.3.
- Property 9 (Zapytanie o specyfikacje czasowe zgadza się z modelem referencyjnym): dla wygenerowanego katalogu ze specyfikacjami `query_timing(trigger, phase)` zwraca dokładnie komponenty o danym rodzaju (i fazie, gdy podana), suma wyników po wszystkich rodzajach = zbiór wszystkich komponentów ze specyfikacją, a lista `UNCLASSIFIED` zgadza się z filtrem (podstawa raportu audytu). Validates: Requirements 8.4, 8.6.
- Triage kontrprzykładu: generator Property 8 początkowo doklejał dowolny tekst tuż po prefiksie `action`, co łamało zasadę całego słowa z designu (`action(?![^\W_])`); poprawiono TEST (implementacja poprawna) — dalszy ciąg po `action` zaczyna się od znaku niebędącego częścią słowa.
- QA zielone dla moich plików: pytest `tests/test_timing_spec_props.py` (4 passed), ruff + mypy czyste dla tego pliku. (W pełnym `ruff check` niezależny błąd E501 w `tests/test_rules_links_props.py` z równoległego zadania 7.5 — poza zakresem 5.3/5.4.) Wymagania: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6.

### ✅ Blok local-ti4-data-foundation 2.4 — testy właściwościowe filtrowania i kolizji (ukończony)
- `tests/test_source_selection_props.py`: dopisane Property 1 i Property 2 (Hypothesis, 200 przykładów każdy) obok istniejącej Property 3; generator `source` z `st.one_of(st.none(), st.integers(), st.lists(st.text()), st.text())` wymusza wpisy bez poprawnego źródła.
- Property 1 (Rachunek wpisów przy filtrowaniu po źródle): dla `select_entries` suma trzech rozłącznych klas — pominięte (źródło niekanoniczne) + bez źródła + aktywne — równa się liczbie wejść; aktywne = unikalni wybrani (po jednym na `id`) + przegrani w kolizjach; każdy wybrany ma źródło z aktywnego zbioru.
- Property 2 (Deterministyczny wybór przy kolizji identyfikatora): zbiór zwycięzców jest niezależny od kolejności wejścia (porównanie z przetasowaną kopią), a zwycięzca każdego `id` jest minimalny względem `(source_rank, file, index)` i ma rangę nie gorszą niż inni kandydaci (RULES.md 14, D9).
- QA zielone dla mojego pliku: `uv run pytest tests/test_source_selection_props.py -q` (3 passed), `ruff check` i `mypy` czyste. Validates: Requirements 4.1, 4.3, 4.4, 4.7, 6.1.

### ✅ Blok local-ti4-data-foundation 7.5 — test właściwościowy powiązań z regułami (ukończony)
- `tests/test_rules_links_props.py`: Property 16 (Powiązanie z tematami reguł jest deterministyczne i zawarte w indeksie), Hypothesis min. 100 przykładów na test. Testuje `RulesTopicIndex.match` z `src/core/rules_links.py`.
- Trzy niezmienniki: (1) `match` zwraca podzbiór tematów indeksu bez duplikatów, a brak trafienia daje pustą listę bez wyjątku; (2) dopasowanie po tytule jest deterministyczne i niewrażliwe na wielkość liter oraz wstawione znaki niealfanumeryczne (ten sam zestaw kodów co dla czystego tytułu); (3) nazwa, której znormalizowana postać nie jest kluczem indeksu, daje pustą listę.
- Smart generatory: unikalne kody tematów (opcjonalny prefiks `C_`/`F_`/`R_`), tytuły z interpunkcją, wariant wielkości liter + losowe separatory. Pomocnik `_match_keys` wiernie odwzorowuje klucze z `RulesTopicIndex.__init__` (tytuł, kod, kod bez prefiksu `_CODE_PREFIX`), żeby warunek „brak trafienia” zgadzał się z implementacją.
- QA zielone: `uv run pytest -q` (357 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste. Wymagania: 10.1, 10.2, 10.3.
### ✅ Blok local-ti4-data-foundation 2.3 — wpięcie katalogu w StaticDataRegistry (ukończony)
- `src/core/registry.py`: w `_load()` buduję `registry.catalog` (ComponentCatalog) z wyniku `load_components(self._enabled)` i wystawiam `registry.load_report` (LoadReport). Specyfikacje czasowe (`build_timing_specs`) z kart akcji, zdolności frakcji i liderów (R8.2).
- Istniejące atrybuty rejestru (units/planets/systems/factions/strategy_cards/leaders/abilities/technologies/breakthroughs) bez zmian zachowania. Kolizje `id` w 9 STARYCH kategoriach tylko RAPORTOWANE przez `registry.legacy_id_collisions` (kategoria -> posortowane id); zasada „ostatni wpis wygrywa" zostaje (D9), więc brak regresji.
- Pola `FactionDef.abilities` i `FactionDef.promissory_notes` (alias `promissoryNotes`) były już obecne w `models.py` (dodane wcześniej addytywnie) — wymaganie zadania spełnione.
- Smoke na realnych danych: action_cards 143, agendas 63, decks 25, 13 kategorii w `load_report.loaded`, brak kolizji w starych kategoriach.
- QA zielone: `uv run pytest -q` (365 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste. Wymagania: 4.1, 5.1, 5.4, 5.5.
### ✅ Blok local-ti4-data-foundation 5.5 — testy przykładowe mapowania i braku regresji okien (ukończony)
- `tests/test_timing_spec_mapping.py`: testy przykładowe pokrywające R8.7 i R8.8 dla `TRIGGER_WINDOW_MAP` z `src/core/timing_spec.py`.
- R8.7 (mapowanie całkowite nad `TriggerKind`): `TRIGGER_WINDOW_MAP` ma dokładnie jeden wpis dla każdej wartości `TriggerKind` (zbiór kluczy == `set(TriggerKind)`, brak nadmiarowych kluczy); wartości to wyłącznie `WindowType` lub `None` („brak okna"); rodzaje reakcji (when/after/before/instead) → `WindowType.REACTION`, a rodzaje bez odpowiednika (at_start/at_end/during/action/unclassified) → `None` (D10, RULES.md 34). Dodatkowo: rozłączność i zupełność podziału na „reakcja" / „brak okna" oraz zgodność `TimingSpec.window_type` z mapą dla próbki pokrywającej wszystkie rodzaje (klasyfikacja po prefiksie + `parse_timing`).
- R8.8 (brak regresji okien): zbiór wartości `WindowType` pozostaje nienaruszony (`STRATEGY_SECONDARY`, `COMBAT_ASSIGN_HITS`, `SPACE_CANNON`, `REACTION`), a publiczny interfejs `core/timing.py` (`build_response_queue`, `open_window`, `current_responder`, `respond_current`, `is_window_complete`, `close_window`) jest nadal dostępny. `tests/test_timing.py` NIE był modyfikowany i przechodzi zielony.
- QA zielone dla moich plików: `uv run pytest tests/test_timing_spec_mapping.py tests/test_timing.py tests/test_timing_spec.py -q` (42 passed), pełny `uv run pytest -q` (365 passed), `ruff check` i `mypy` czyste dla `tests/test_timing_spec_mapping.py`. (W pełnym `ruff check src tests` niezależny błąd E501 w `tests/test_audit_props.py` z równoległego zadania 8.5/8.6 — poza zakresem 5.5.) Wymagania: 8.7, 8.8.
### ✅ Blok local-ti4-data-foundation 2.5 — testy właściwościowe modeli i błędów walidacji (ukończony)
- `tests/test_components_props.py`: Property 4 (200 przykładów) i Property 5 (100 przykładów, Hypothesis). Testuje `build_component` z `src/core/components.py` oraz `load_components`/`DataValidationError` z `src/core/component_loader.py`.
- Property 4 (Zachowanie pól i surowych danych komponentu): dla wygenerowanego wpisu i dopasowanej `CategorySpec` (model `ObjectiveDef`, pole id `alias` lub `id`, losowe `text_fields` i pole okna) `build_component` daje `id` wyłącznie z pola wskazanego przez specyfikację, `raw` jest wierną KOPIĄ wpisu (nic nie ginie, R5.7), `texts` to dokładnie pola tekstowe obecne w JSON jako napisy, `window` odtwarzane tylko gdy specyfikacja ma pole okna, a `flavor_text` bierze `flavorText` lub `flavourText` bez preferencji spoza JSON. Validates: Requirements 5.2, 5.7.
- Property 5 (Błąd walidacji niesie kontekst wpisu): na `tmp_path` budowany jest prawdziwy katalog kategorii celów publicznych z jednym wpisem o kanonicznym `source` i niepoprawnym `points` (lista/napis/słownik — pydantic nie przyjmie jako `int | None`); `load_components` zgłasza `DataValidationError`, którego `category`, `file` i `entry_id` wskazują dokładnie wygenerowany wpis, a komunikat tekstowy także niesie ten kontekst. Validates: Requirements 5.5.
- Uwaga Windows/Hypothesis: `tmp_path` jest współdzielony między przykładami jednego testu, więc każdy przykład dostaje unikalny podkatalog (`uuid4`), z `suppress_health_check=[HealthCheck.function_scoped_fixture]`.
- QA zielone dla moich plików: `uv run pytest tests/test_components_props.py -q` (2 passed), pełny `uv run pytest -q` (385 passed), `ruff check` i `mypy` czyste dla `tests/test_components_props.py`. (W pełnym `mypy src tests` / `ruff check src tests` niezależne błędy w `src/core/registry.py` z równoległego zadania 4.1/4.3 wpinającego `references.py` — poza zakresem 2.5.) Wymagania: 5.2, 5.5, 5.7.

### ✅ Blok local-ti4-data-foundation 2.6 — testy katalogu na realnych danych (ukończony)
- `tests/test_components_real_data.py`: trzy testy przykładowe na REALNYCH assetach AsyncTI4, zbudowane na `StaticDataRegistry()` (domyślny `enabled_sources.json`: base, pok, codex1-4, thunders_edge) i jego `catalog`.
- Test 1 (R5.1, R5.4): każda kategoria z `CATEGORY_SPECS` jest niepusta, poza potwierdzonymi lukami z `audit/expected_gaps.json` (obecnie plik pusty → wszystkie 13 kategorii niepuste: action_cards 143, agendas 63, public_objectives 40, secret_objectives 40, attachments 22, explores 80, relics 24, promissory_notes 40, tokens 29, border_anomalies 1, galactic_events 20, genericcards 10, decks 25). Wyjątki czytane przez `src.audit.diffs.load_expected_gaps`, bez hardkodowania listy luk.
- Test 2 (R5.1): żaden załadowany komponent nie ma `source` spoza aktywnego manifestu (potwierdzenie filtra po polu `source`).
- Test 3 (R4.5, R5.1, D6): wpis `codex1` „War Machine" (alias `war_machinell`) ukryty w homebrew `assets/data/action_cards/theodisi.json` JEST ładowany z `source == "codex1"`, a karty homebrew z tego samego pliku (`source == "theodisi"`, np. `unchart_space`) są odfiltrowane — filtr działa po polu, nie po nazwie pliku.
- QA dla moich plików: `uv run pytest tests/test_components_real_data.py -q` (3 passed), `ruff check` i `mypy` czyste dla `tests/test_components_real_data.py`. (W pełnym zestawie niezależne błędy z równoległych zadań: 2.5 `tests/test_components_props.py` — reużycie `tmp_path` w Hypothesis na Windows; 4.1 `src/core/references.py` + nieużyte importy w `registry.py` — poza zakresem 2.6.) Wymagania: 4.5, 5.1, 5.4.

### ✅ Blok local-ti4-data-foundation 8.4 — `src/audit/sync_assets.py` (ukończony)
- `src/audit/sync_assets.py`: synchronizacja lokalnych grafik z katalogu referencyjnego. Ścieżka źródła to WYŁĄCZNIE argument CLI `--from <katalog>` (nigdy stała w kodzie — zgodność z R1.1). Czysta funkcja `sync_assets(source_dir, manifest_paths, assets_dir)` kopiuje do `assets/` tylko pliki z manifestu brakujące na dysku; pliki już obecne pomija (nie nadpisuje), a wpisy nieobecne w katalogu źródłowym trafiają na listę „niezsynchronizowane" (`SyncResult.unsynced`).
- Katalog źródłowy jest tylko czytany — nic w nim nie jest zmieniane ani usuwane (R12.8). Kopiowanie wyłącznie w stronę `assets/`.
- CLI (`main`): niezerowy kod wyjścia (1), gdy są pliki niezsynchronizowane; brak `--from` = komunikat o użyciu i kod 2 (argparse, `required=True`); nieistniejący katalog `--from` = `parser.error` (kod 2). `render_result` wypisuje liczby i listę braków.
- Test przykładowy na `tmp_path`: `tests/test_audit_sync_assets.py` (kopiowanie brakujących + pomijanie obecnych, lista niezsynchronizowanych + kod ≠ 0, nienaruszalność katalogu źródłowego przez porównanie sha256 przed/po, kod 0 przy komplecie, kod 2 przy braku `--from`).
- QA zielone dla moich plików: `uv run pytest tests/test_audit_sync_assets.py` (7 passed), pełny `uv run pytest -q` (385 passed), ruff + mypy czyste dla `sync_assets.py` i jego testu. (W pełnym `ruff check`/`mypy src tests` niezależne błędy z równoległych zadań 1.2/2.3/4.1 — poza zakresem 8.4.) Wymagania: 3.3, 12.8.

### ✅ Blok local-ti4-data-foundation 2.6 — testy katalogu na realnych danych (ukończony)
- `tests/test_components_real_data.py`: trzy testy przykładowe na REALNYCH assetach AsyncTI4, zbudowane na `StaticDataRegistry()` (domyślny `enabled_sources.json`: base, pok, codex1-4, thunders_edge) i jego `catalog`.
- Test 1 (R5.1, R5.4): każda kategoria z `CATEGORY_SPECS` jest niepusta, poza potwierdzonymi lukami z `audit/expected_gaps.json` (obecnie plik pusty → wszystkie 13 kategorii niepuste: action_cards 143, agendas 63, public_objectives 40, secret_objectives 40, attachments 22, explores 80, relics 24, promissory_notes 40, tokens 29, border_anomalies 1, galactic_events 20, genericcards 10, decks 25). Wyjątki czytane przez `src.audit.diffs.load_expected_gaps`, bez hardkodowania listy luk.
- Test 2 (R5.1): żaden załadowany komponent nie ma `source` spoza aktywnego manifestu (potwierdzenie filtra po polu `source`).
- Test 3 (R4.5, R5.1, D6): wpis `codex1` „War Machine" (alias `war_machinell`) ukryty w homebrew `assets/data/action_cards/theodisi.json` JEST ładowany z `source == "codex1"`, a karty homebrew z tego samego pliku (`source == "theodisi"`, np. `unchart_space`) są odfiltrowane — filtr działa po polu, nie po nazwie pliku.
- QA dla moich plików: `uv run pytest tests/test_components_real_data.py -q` (3 passed), `ruff check` i `mypy` czyste dla `tests/test_components_real_data.py`. (W pełnym zestawie niezależne błędy z równoległych zadań: 2.5 `tests/test_components_props.py` — reużycie `tmp_path` w Hypothesis na Windows; 4.1 `src/core/references.py` + nieużyte importy w `registry.py` — poza zakresem 2.6.) Wymagania: 4.5, 5.1, 5.4.

### ✅ Blok local-ti4-data-foundation 8.3 — raport Audytora_Danych i `__main__` (ukończony)
- `src/audit/report.py`: `AuditReport` (dataclass ze wszystkimi sekcjami z R12.1: `counts`, `skipped`, `sourceless`, `conflicts`, `unresolved`, `suspicious`, `gaps_to_confirm`, `unclassified_timing`, `effect_coverage`, `manifest`, `external_urls`, `frontend_diff`, `no_rules_note`, `orphan_effect_statuses` + `validation_error`, `references_module_available`).
- `build_report(registry, scans)` jest CZYSTE nad już zebranymi danymi (I/O żyje w `collect_scans`): liczby z `catalog.counts()`, luki przez `diffs.find_gaps` z `expected_gaps.json`, `unclassified` przez `catalog.query_timing(TriggerKind.UNCLASSIFIED)`, pokrycie i osierocone statusy przez `effects_registry.coverage`/`EffectRegistry.load`, „bez noty" przez `rules_links.RulesTopicIndex` (brak `tirules.json` ⇒ wszystkie „bez noty", R10.3).
- `render_text(report)` buduje czytelny raport tekstowy ze wszystkimi sekcjami; `exit_code(report)` zwraca 1 TYLKO przy błędzie krytycznym (nierozwiązana referencja, brakujący plik z manifestu, zewnętrzny URL spoza listy dozwolonej, błąd walidacji wpisu kanonicznego); ostrzeżenia (podejrzane, `unclassified`, luki, „bez noty", osierocone statusy, kolizje) nie zmieniają kodu 0 (Property 14, R3.4, R7.5, R12.2).
- `detect_suspicious` (R4.5): wpis o źródle kanonicznym w pliku, którego nazwa (bez rozszerzenia) NIE jest identyfikatorem żadnego znanego źródła ani nazwą bazową kategorii — czysto STRUKTURALNIE, bez listy nazw homebrew. Na realnych danych wykrywa m.in. `theodisi.json`/`codex1` oraz pliki `te_*`, `color.json`, `codexii/iv.json`, `base_game.json`.
- Spójność referencji (R7.x) z `core/references.py` przez import OBRONNY (`importlib`, zadanie 4.1 równoległe); gdy modułu brak, substytut `registry.missing_planet_references` + flaga `references_module_available=False`.
- `src/audit/__main__.py`: `python -m src.audit` z opcjami `--write-baseline`, `--write-manifest`, `--json`. `main()` łapie `DataValidationError` (rejestr nie wstał) jako błąd krytyczny.
- Uruchomiono `uv run python -m src.audit --write-baseline` → zapisano `audit/baseline_counts.json` (13 kategorii, m.in. action_cards 143, agendas 63, cele 40/40, explores 80, relics 24, promissory 40). Kod wyjścia 1 odzwierciedla realne, znane problemy jakości do naprawy w zadaniach 4.x/11.x (nierozwiązane referencje homebrew `explores_cpti`, zewnętrzne URL we froncie przed migracją grafik/fontów) — diff zatwierdza użytkownik przy commicie.
- Test przykładowy `tests/test_audit_report.py` (11 passed): `detect_suspicious` na `tmp_path` (plik homebrew vs plik źródła vs plik kategorii), rozróżnienie krytyczny/ostrzeżenie w `exit_code`, `build_report` + `render_text` na realnym rejestrze zawiera wszystkie sekcje R12.1, `write_baseline` zapisuje `counts`.
- QA dla moich plików: `uv run pytest -q` (396 passed), ruff + mypy czyste dla `src/audit/report.py`, `src/audit/__main__.py`, `tests/test_audit_report.py`. (W pełnym `ruff check src tests` niezależny błąd sortowania importów w `src/core/registry.py` z równoległego zadania 4.1 — poza zakresem 8.3.) Wymagania: 3.2, 3.4, 4.5, 6.1, 6.2, 7.5, 8.4, 9.3, 10.3, 12.1, 12.2.

### ✅ Blok local-ti4-data-foundation 8.9 — test regresji liczb wpisów (ukończony)
- `tests/test_audit_baseline.py`: test regresji porównujący liczby komponentów per kategoria i źródło (`StaticDataRegistry().catalog.counts()`) z wartościami referencyjnymi w `audit/baseline_counts.json` (R6.4). Rejestr budowany raz na moduł (fixture `scope="module"`).
- Różnice liczone czystą funkcją `diff_counts`, a wzorzec wczytywany przez `load_baseline_counts` — obie z `src/audit/diffs.py` (bez duplikowania logiki w teście). Klucze kategorii z `catalog.counts()` to `ComponentCategory` (StrEnum); normalizowane do `str` (`.value`), by porównanie i wypisane różnice operowały na zwykłych napisach.
- Przy rozbieżności (R6.5) test zawodzi z czytelnym, deterministycznie posortowanym wypisaniem różnic `kategoria/źródło: baseline → current` (`—` = brak wpisu po danej stronie, czyli nowe lub usunięte źródło w kategorii) oraz podpowiedzią regeneracji wzorca (`uv run python -m src.audit --write-baseline`). Dodatkowa asercja chroni przed pustym/brakującym baseline.
- QA zielone: `uv run pytest tests/test_audit_baseline.py -q` (1 passed), pełny `uv run pytest -q` (399 passed), `ruff check` i `mypy` czyste dla `tests/test_audit_baseline.py`. (W pełnym `ruff check src tests` niezależny błąd F401 nieużytego importu `pytest` w `tests/test_components.py` z równoległego zadania — poza zakresem 8.9.) Wymagania: 6.4, 6.5.
### ✅ Blok local-ti4-data-foundation 4.2 — `ComponentCatalog.faction_bundle` i `FactionBundle` (ukończony)
- `src/core/components.py`: dodano niemutowalny dataclass `FactionBundle` (frozen) z polami `faction`, `leaders`, `abilities`, `faction_tech`, `promissory_notes`, `units`, `breakthrough` oraz metodę `ComponentCatalog.faction_bundle(faction_id)` zwracającą komplet komponentów powiązanych z frakcją w JEDNYM wywołaniu (R5.6: liderzy, zdolności, technologie frakcyjne, promissory notes, jednostki, przełom).
- Identyfikatory czytane są WYŁĄCZNIE z list `FactionDef` (`leaders`, `abilities`, `faction_tech`, `promissory_notes`, `units`) i mapowane na modele z odpowiednich słowników. Zero hardkodowania nazw ani list. Identyfikatory nierozwiązane (brak w słowniku) są pomijane — ich wykryciem zajmuje się osobno `core/references.py` (zadanie 4.1).
- Konstruktor `ComponentCatalog` rozszerzony o keyword-only słowniki kategorii żyjących poza Katalogiem_Komponentów (w rejestrze): `factions`, `leaders`, `abilities`, `technologies`, `units`, `breakthroughs`. Puste domyślnie → pełna zgodność wsteczna z dotychczasowymi wywołaniami `ComponentCatalog(tables)`.
- Przełom (breakthrough, Thunder's Edge) NIE figuruje na liście `FactionDef`; dopasowywany po polu `faction` przełomu równym id frakcji LUB jej „rodzinie" (`short_name` małymi literami) — ta sama reguła co w rejestrze, bez listy frakcji w kodzie (`_breakthrough_for`).
- Promissory notes rozwiązywane ze słownika kategorii `PROMISSORY_NOTE` Katalogu_Komponentów (z filtrem typu `PromissoryNoteDef`), bo to komponenty ładowane do katalogu, a nie osobny słownik rejestru.
- Testy przykładowe `tests/test_components.py`: `test_faction_bundle_sklada_komponenty_z_list_faction_def` (rozwiązanie id na modele, pominięcie nierozwiązanego lidera `brak_lidera`, dopasowanie przełomu po rodzinie) oraz `test_faction_bundle_nieznana_frakcja_rzuca_key_error` (brak frakcji → `KeyError`).
- Bramka QA zielona: `uv run pytest -q` (405 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 101 source files). Wymagania: 5.6.
### ✅ Blok local-ti4-data-foundation 8.8 — test Strażnika_Lokalności, część backendowa (ukończony)
- `tests/test_locality_guard.py`: pilnuje lokalności kodu backendu i budowy aplikacji względem folderów referencyjnych AsyncTI4 (`TI4_map_generator_bot`, `ti4_web_new`) i korzenia projektu. Nazwy folderów są STAŁĄ W TEŚCIE (`REFERENCE_DIR_NAMES`), nie w kodzie produkcyjnym (R1.1), i korzystają z czystych skanerów z `src/audit/locality.py` (`find_reference_path_usage`, `collect_sources` — odczyt `utf-8-sig`, bezpieczny dla plików z BOM).
- R1.1: skan `ast` literałów napisowych (bez docstringów/komentarzy) w `src/**/*.py` i `scripts/**/*.py` — żaden nie zawiera nazwy folderu referencyjnego; sam plik Strażnika jest wykluczony ze skanu (celowo trzyma stałą).
- R1.2: skan `frontend/src/**` (ts/tsx/js/jsx/css), `index.html` i `vite.config.ts` pod kątem importu/proxy folderów referencyjnych — filtr `_import_or_proxy_lines` zachowuje numerację linii (linie nie-importowe → puste), bo osadzone URL-e CDN pokrywa osobny skaner URL (zad. 11.7), a dane homebrew — zad. 11.3.
- R1.3/R1.5: fixture `read_recorder` opakowuje `Path.read_text`, `Path.read_bytes` i `builtins.open` (deskryptory całkowite pomijane), zbierając czytane ścieżki. Testy budują `StaticDataRegistry()` oraz `create_app(store=EventStore(":memory:"))` i asertują, że żaden odczyt nie wychodzi poza `PROJECT_ROOT` ani do folderu referencyjnego (ścieżki rozwijane do bezwzględnych i sprawdzane `relative_to`).
- QA zielone: `uv run pytest tests/test_locality_guard.py -q` (4 passed), pełny `uv run pytest -q` (405 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste. Wymagania: 1.1, 1.2, 1.3, 1.5.
### ✅ Blok local-ti4-data-foundation 8.7 — Property 14 (kod wyjścia audytu) + test raportu (ukończony)
- **Property 14: Kod wyjścia audytu odzwierciedla błędy krytyczne** — dopisana do `tests/test_audit_props.py` (bez nadpisywania; dołączona po Property 12/13/15). Dwie funkcje właściwościowe Hypothesis budują `AuditReport` z losowych kombinacji pól krytycznych i ostrzegawczych (bez dysku i bez rejestru) i porównują z modelem referencyjnym niezależnym od `has_critical`:
  - `test_exit_code_jest_niezerowy_dokladnie_przy_bledzie_krytycznym` (max 200 iteracji): `exit_code(report) == 1` wtedy i tylko wtedy, gdy którekolwiek z pól krytycznych jest niepuste (`unresolved`, `manifest.missing`, `external_urls`, `validation_error`); ostrzeżenia (podejrzane, luki, `unclassified`, „bez noty”, osierocone statusy, pliki `unused` z manifestu) nie zmieniają kodu. Dodatkowo potwierdza, że kod jest zawsze ∈ {0, 1}.
  - `test_exit_code_zero_gdy_tylko_ostrzezenia` (max 100 iteracji): dowolny zestaw samych ostrzeżeń daje kod 0 i `has_critical is False`.
- Test raportu na realnym rejestrze (`build_report` + `render_text` zawiera wszystkie sekcje R12.1) już istniał w `tests/test_audit_report.py` z zadania 8.3 — NIE duplikowany.
- QA dla moich plików zielone: `uv run pytest tests/test_audit_props.py tests/test_audit_report.py -q` (21 passed), pełny `uv run pytest -q` (405 passed), `ruff check` i `mypy` czyste dla `tests/test_audit_props.py` i `tests/test_audit_report.py`. (Przejściowy, niezależny błąd ruff F401 w `src/audit/locality.py` z równoległego zadania — poza zakresem 8.7.) Wymagania: 3.4, 7.5, 12.1, 12.2.
### ✅ Blok local-ti4-data-foundation 7.3 — wpięcie rejestru efektów i indeksu reguł w `ComponentCatalog` (ukończony)
- `src/core/components.py`: konstruktor `ComponentCatalog` rozszerzony o dwa opcjonalne argumenty keyword-only — `effect_registry` (protokół `_EffectRegistryLike` z metodą `status_of`, by uniknąć cyklu importów: `effects_registry` importuje `components`) i `rules_index` (`RulesTopicIndex`, domyślnie pusty). Zmiana w pełni addytywna: istniejące wywołania `ComponentCatalog(tables)` działają bez zmian.
- Nowe metody katalogu: `effect_status(ref)` — deleguje do wpiętego `EffectRegistry`; brak rejestru → domyślny `NOT_IMPLEMENTED` (R9.3). `rules_topics(ref)` — zwraca tematy zrzutu reguł dopasowane deterministycznie (równość znormalizowanych nazw) po `id` i nazwie komponentu oraz temat kategorialny z `CATEGORY_TOPIC_HINTS`; brak trafień → pusta lista, nic nie jest zgadywane (R10.1).
- `src/core/registry.py`: w `_load()` wczytywany `EffectRegistry.load()` (brak pliku = pusty, R9.4) i `RulesTopicIndex.from_json()` (brak `tirules.json` = pusty, R10.2), wystawione jako `registry.effect_registry` i `registry.rules_index`, a następnie wpięte w `ComponentCatalog`. Oba czytane z lokalnych assetów — nic w kodzie.
- Testy przykładowe `tests/test_components.py`: `test_effect_status_i_rules_topics_wpiete_w_katalog` (status z wpiętego rejestru, domyślny `NOT_IMPLEMENTED` dla braku wpisu, tematy reguł: trafienie po nazwie + temat kategorialny, nieznany komponent → pusta lista) oraz `test_katalog_bez_rejestru_i_indeksu_dziala_wstecz` (zgodność wsteczna — wartości domyślne). Smoke test na realnym rejestrze: indeks reguł 149 tematów, karta akcji → `C_action_cards`, status `not_implemented`.
- Bramka QA zielona: `uv run pytest -q` (407 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 101 source files). Wymagania: 9.4, 10.2 (oraz R9.3, R10.1).

## Blok 4.4 — Testy przykładowe paczki frakcji i referencji realnych (local-ti4-data-foundation)

- Nowy plik `tests/test_references_real_data.py`: testy przykładowe na pełnym `StaticDataRegistry` (domyślny manifest: base, pok, codex1-4, Thunder's Edge), bez mocków.
- `faction_bundle` dla reprezentatywnych frakcji z każdego aktywnego źródła (`arborec`, `sol` — base; `titans` — pok; `keleresm` — codex3; `bastion` — thunders_edge): sprawdza, że paczka zawiera liderów i przełom (R5.6) oraz że każdy rozwiązany identyfikator (liderzy, zdolności, technologie frakcyjne, promissory notes, jednostki) to TEN SAM obiekt co w słowniku rejestru/katalogu (mapowanie 1:1, nic nie jest hardkodowane). Dodatkowo kontrakt: nieistniejąca frakcja → `KeyError`.
- `find_unresolved_references` na realnym rejestrze: asercja STRUKTURY (lista `UnresolvedReference`) zamiast porównania z `audit/expected_gaps.json` (ten plik trzyma pary `(kategoria, źródło)` dla brakujących źródeł kanonicznych — inne pojęcie). Znane, oczekiwane luki homebrew udokumentowane jako zbiór właścicieli `{explores_cpti, mirage, gamma, gw, ion}` (talia eksploracji `cpti` i attachmenty spoza aktywnych źródeł, R7.6) — test NIE traktuje ich jako błędu, tylko pilnuje, że nie pojawia się żadna NOWA, nieoczekiwana luka. Osobny test gwarantuje brak zerwanych referencji frakcji (`faction.*`) i systemów do planet (`system.planets`) (R7.1, R7.4).
- Bramka QA zielona: `uv run pytest -q` (425 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 103 source files). Wymagania: 5.6, 7.1, 7.4.

### ✅ Blok local-ti4-data-foundation 4.3 — test właściwościowy referencji (ukończony)
- `tests/test_references_props.py`: Property 6 (Spójność referencji jest wykrywana dokładnie), Hypothesis 200/100 przykładów na test. Testuje `find_unresolved_references` / `build_reference_report` z `src/core/references.py` na „mini-rejestrze” — lekkim obiekcie (`_MiniRegistry`) spełniającym protokół `RegistryLike`, z ręcznie złożonym `ComponentCatalog` i namiastką `LoadReport` (`_MiniLoadReport.skipped_index`). Bez dysku i bez pełnego `StaticDataRegistry`.
- Test 1 (R7.1, R7.6): promissory notes frakcji — cel istniejący w katalogu → brak zgłoszenia; cel wyłącznie wśród wpisów niekanonicznych (`skipped_index`) → `leaks_noncanonical=True`; cel nieznany nigdzie → `leaks_noncanonical=False`; każdy identyfikator z `<color>` trafia WYŁĄCZNIE do `report.templates`, nigdy do `unresolved`. Zbiór nierozwiązanych równa się dokładnie referencjom spoza katalogu (bez szablonów).
- Test 2 (R7.2): `cardIDs` talii typu `promissory_note` — brakujące → nierozwiązane (`kind="deck.cardIDs"`), `<color>` → szablon.
- Test 3 (R7.3): `attachmentId` eksploracji i `attachmentID` żetonów — brakujący attachment → nierozwiązana referencja o właściwym `kind`/`owner_id`/`missing_id`; istniejący → brak zgłoszenia.
- Test 4 (R7.5, R7.6): `find_unresolved_references` nie zawiera szablonów `<color>` i jest identyczne z `build_reference_report(...).unresolved`.
- Mini-rejestr buduje komponenty bezpośrednio przez modele (`PromissoryNoteDef`, `AttachmentDef`, `ExplorationDef`, `TokenDef`, `DeckDef`) z polem `id` (mapowanie `alias→id` żyje w `build_component`, nie w modelu) — stąd konstrukcja po `id=`, nie `alias=`.
- QA zielone: `uv run pytest -q` (425 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste (103 pliki). Validates: Requirements 7.1, 7.2, 7.3, 7.6.

### ✅ Blok local-ti4-data-foundation 10.1 — endpointy komponentów (ukończony)
- Nowy plik `src/api/schemas_components.py` (osobny od `schemas.py`, by nie puchł kontrakt podstawowy): DTO Pydantic v2 dla Katalogu_Komponentów z klasmetodami `from_core` — `CategoriesResponse`/`CategoryCount`, `CategoryComponentsResponse`, `ComponentDetailResponse`, `FactionBundleResponse`, `TimingSpecsResponse`, `ComponentRefDTO`, `TimingSpecDTO`, `RulesTopicDTO`. Modele komponentów serializowane po aliasach (`model_dump(mode="json", by_alias=True)`), zachowują pole `raw`.
- Nowy router `src/api/routers/components.py` (cienki, wzorzec `routers/rules.py`): TYLKO-DO-ODCZYTU nad `ctx.registry.catalog` przez `Depends(get_ctx)`, zero mutacji `GameState`, zero `broadcast`. Endpointy: `GET /components` (lista kategorii + liczniki ze `counts()`), `GET /components/{category}` (słownik `id -> komponent`), `GET /components/{category}/{component_id}` (komponent + `TimingSpec` + status efektu + tematy reguł), `GET /components/factions/{faction_id}/bundle` (`FactionBundle`, R5.6), `GET /timing-specs?trigger=&phase=` (`query_timing`, R8.6).
- Mapowanie błędów domenowych (R11.3): nieznana kategoria lub identyfikator → `HTTPException(404, "Component not found: <category>/<id>")`; nieznana frakcja (`KeyError` z `faction_bundle`) → 404 z kategorią `factions`. Nieprawidłowy `trigger`/`phase` → 422 dzięki walidacji enum FastAPI (parametry typowane jako `TriggerKind`/`Phase`). Źródła kanoniczne — filtr jest już w katalogu (R11.2), API niczego nie filtruje.
- Router zarejestrowany w fabryce `src/api/app.py` (`include_router(components.router)`); kolejność ścieżek bez kolizji (różna liczba segmentów: `/components/{category}/{component_id}` vs `/components/factions/{faction_id}/bundle`).
- Smoke-test TestClient potwierdził: `GET /components` → 13 kategorii, `action_cards` → 143 wpisy, detal zwraca `effect_status`, 404 dla złej kategorii i złego id z poprawnym komunikatem, `trigger=when` → 69 trafień, `trigger=bogus` → 422, bundle frakcji `arborec` → 3 liderów, 1 zdolność, 10 jednostek, przełom obecny.
- Bramka QA zielona: `uv run pytest -q` (425 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 105 source files). Wymagania: 11.1, 11.2, 11.3, 11.4.

### Blok 10.2 — Testy API Katalogu_Komponentów

- Nowy plik `tests/test_components_api.py` (pytest + FastAPI `TestClient`): testuje router `src/api/routers/components.py` na REALNYM `StaticDataRegistry` (fixture `registry` o zasięgu modułu) z osobnym `EventStore(":memory:")` na każdy test (fixture `client`), wzorzec z `tests/test_api.py`.
- Pokrycie endpointów (R11.1): `GET /components` (lista kategorii + liczniki, `total == sum(by_source)`, sortowanie po nazwie), `GET /components/{category}` (słownik `id -> komponent`, `count == len`), `GET /components/{category}/{id}` (detal z `timing_spec`/`effect_status`/`rules_topics`, `source` z aktywnego manifestu — R11.2), `GET /components/factions/{faction_id}/bundle` (paczka frakcji z realnym id z `/factions`, R5.6), `GET /timing-specs?trigger=&phase=` (lista adresów, propagacja fazy).
- Mapowanie błędów (R11.3): 404 dla nieznanej kategorii (`Component not found: <category>/`), nieznanego id (`<category>/<id>`) i nieznanej frakcji (`factions/<id>`); 422 dla nieprawidłowego `trigger` (enum FastAPI) i braku wymaganego `trigger`.
- Kategorie/identyfikatory wybierane dynamicznie z katalogu (pierwsza niepusta kategoria, pierwszy jej wpis) — test odporny na zmiany danych. Frakcje adresowane przez `/factions`, bo nie są tabelą katalogu.
- Bramka QA zielona: `uv run pytest -q` (437 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 106 source files). Wymagania: 11.1, 11.2, 11.3, 11.4.
### ✅ Blok local-ti4-data-foundation 11.1 — Resolver_Zasobów i manifest we froncie (ukończony)
- Nowy moduł `frontend/src/shared/assets/resolveAsset.ts` (Resolver_Zasobów): `assetUrl(logicalPath)` zamienia logiczną ścieżkę (np. `/units/blu_cruiser.png`) na LOKALNY URL `/static/units/blu_cruiser.png`, zwraca WYŁĄCZNIE ścieżki lokalne (`/static/...` albo `PLACEHOLDER_URL`), nigdy `://` (R2.1). Gdy dokładnej ścieżki nie ma w manifeście, próbuje alternatywnych rozszerzeń `.png/.jpg/.jpeg/.webp` (bo stare `cdnImage()` zamieniało `.png/.jpg -> .webp`, a Resolver nie kopiuje tej konwersji — rozstrzyga ją manifest, zgodnie z design.md). Brak wszystkich wariantów → `PLACEHOLDER_URL` (R2.6). `sheetUrl("units"|"tokens", name)` buduje ścieżkę do sprite sheetu (sheety są wyłącznie `.webp`). `PLACEHOLDER_URL = "/placeholder.svg"`.
- Pusty manifest (grafiki jeszcze niezsynchronizowane) → `assetUrl` zwraca ścieżkę `/static/...` bezpośrednio zamiast placeholdera, żeby nie psuć działającego dev-setupu.
- Nowy plik `frontend/public/placeholder.svg` — lokalny placeholder pokazywany, gdy grafiki nie ma w Zasobach_Lokalnych.
- Manifest frontendu `frontend/src/shared/assets/assetManifest.json` (tylko logiczne ścieżki, `{"paths": [...]}`) generowany z `audit/assets_manifest.json`. Rozszerzyłem `src/audit/assets_manifest.py` o `FRONTEND_MANIFEST_PATH` i `write_frontend_manifest()`, a CLI `uv run python -m src.audit --write-manifest` zapisuje teraz OBA pliki (główny w `audit/` + kopię logicznych ścieżek we froncie). Jedyne źródło prawdy: `audit/assets_manifest.json`; kopia we froncie to artefakt generowany.
- UWAGA: to zadanie TYLKO tworzy resolver i manifest — zamiana wszystkich wywołań `cdnImage()` to zadanie 11.2 (jeszcze niewykonane).
- Bramka frontendowa zielona dla plików tego bloku: `npm run type-check` (OK), `npx eslint src/shared/assets/resolveAsset.ts` (0 błędów), `npm run build` (OK). Uwaga: `npm run lint` dla całego repo zgłasza 2 PREISTNIEJĄCE błędy w `src/domains/rules/RulesBrowserPage.tsx` (plik niemodyfikowany w tym bloku, poza zakresem 11.1).
- Bramka backendowa zielona (zmiany w `src/audit/`): `uv run pytest -q` (437 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success, 106 plików).
- Wymagania: 2.1, 2.6, 3.1.
### ✅ Blok local-ti4-data-foundation 11.2 — zastąpienie `cdnImage()` Resolverem_Zasobów (ukończony)
- Mechaniczna zamiana wszystkich wywołań `cdnImage()` na `assetUrl()` (ta sama sygnatura `string -> string`) w 59 plikach `frontend/src`: import `@/entities/data/cdnImage` → `@/shared/assets/resolveAsset`, każde wywołanie `cdnImage(` → `assetUrl(`. Po zmianie w `frontend/src` nie pozostało żadne funkcjonalne odwołanie do `cdnImage` ani do CDN AsyncTI4 (jedyne wzmianki to komentarze w `resolveAsset.ts` opisujące zastąpienie).
- Usunięty przestarzały moduł `frontend/src/entities/data/cdnImage.ts` (wraz z budowaniem URL `https://images.asyncti4.com/...` i parametrem `?v=4`). Konwersja rozszerzeń `.png/.jpg -> .webp` nie jest już kopiowana — rozstrzyga ją manifest w Resolverze_Zasobów (zgodnie z 11.1 i design.md).
- Zaktualizowany `frontend/README.md`: wpis „Grafiki idą z CDN AsyncTI4 (cdnImage.ts)" zastąpiony opisem lokalnych grafik serwowanych pod `/static` przez Resolver_Zasobów (`src/shared/assets/resolveAsset.ts`).
- Bramka frontendowa zielona: `npm run type-check` (OK), `npm run build` (`tsc && vite build` — OK, exit 0). `npm run lint` zgłasza WYŁĄCZNIE 2 PREISTNIEJĄCE błędy w `src/domains/rules/RulesBrowserPage.tsx` (plik niemodyfikowany, poza zakresem 11.2) — zmiany tego bloku nie wprowadziły żadnych nowych uwag lintera.
- UWAGA: niezacommitowane zmiany innej osoby (`useNewGame.ts`, `Step_NameColor.tsx`, `useSetupStore.ts`, nowe pliki `faction_portraits`) NIE były ruszane ani stagowane.
- Wymagania: 2.1, 2.2, 2.6.

### ✅ Blok local-ti4-data-foundation 11.3 — lokalne sprite sheety, ikony frakcji, relikt, Discord (ukończony)
- `frontend/src/shared/ui/Unit/unitSprites.ts`: sprite sheet jednostek z `sheetUrl("units", color)` zamiast `https://images.asyncti4.com/units/sheets/...webp?v=4` — grafika lokalna z backendu (`/static/units/sheets/...`), bez CDN AsyncTI4 (R2.1).
- `frontend/src/shared/ui/Token/components/TokenSprite.tsx`: `backgroundImage` z `sheetUrl("tokens", sprite.sheet)` zamiast CDN AsyncTI4.
- `frontend/src/entities/lookup/factions.ts`: `getFactionImage` dla typów `EMOJI` (dawniej `emoji-cdn.mqrio.dev`) i `DISCORD` (surowy URL profilu) zwraca teraz LOKALNĄ grafikę frakcji (`assetUrl("/factions/<alias>.png")`, placeholder przy braku) — koniec z zasobem zewnętrznym (R2.4).
- `frontend/src/entities/data/relics.ts`: relikt „The Silver Flame" (`silverflame`) ma `imageURL` lokalny (`/hover_images/relics/misc_homebrew/the_silver_flame.png`) zamiast `cdn.statically.io` (R2.4), spójnie z pozostałymi reliktami.
- `frontend/src/config.ts`: dodana flaga `config.features.onlineLogin` (domyślnie `false`). `frontend/src/domains/auth/DiscordLogin.tsx`: komponent zwraca `null`, gdy `onlineLogin === false`, więc adres `discord.com` nie trafia do DOM w trybie offline (D2; `discord.com` zostaje w allowliście jako „tylko online, flaga").
- Usuwanie wbudowanych danych niekanonicznych z `entities/data/*.ts` POMINIĘTE zgodnie z decyzją D3 (tylko audyt + test różnic id) — potwierdzone przez użytkownika; ~3400 wpisów w 16 plikach zostaje jako cache do osobnej migracji.
- Bramka frontendowa zielona: `npm run type-check` i `npm run build` przechodzą; `npm run lint` zgłasza wyłącznie 2 preistniejące błędy w `RulesBrowserPage.tsx` (nietknięte, poza zakresem zadania). Brak nowych zasobów zewnętrznych w runtime; pozostałe URL-e (`discord.com` za flagą, `ti4battle.com`, `tirules2.com`, `github.com/dangothemango`) to allowlista nawigacyjna/atrybucyjna (D2). Wymagania: 2.2, 2.3, 2.6, 11.5.

### ✅ Blok local-ti4-data-foundation 11.4 — fonty lokalne i czyszczenie `index.html` (ukończony)
- Fonty tekstu i danych przeniesione z Google Fonts na LOKALNE pakiety `@fontsource` (D11): dodane do `frontend/package.json` z DOKŁADNIE przypiętymi wersjami `@fontsource/ibm-plex-sans@5.3.0` i `@fontsource/ibm-plex-mono@5.3.0` (bez `^`), `--save-exact`.
- `frontend/src/main.tsx`: importy CSS fontów na samej górze (przed resztą stylów). Tylko wagi z drabiny typograficznej (`styles/typography.css`): Sans 400/500/600/700, Mono 400/500/700. Podzbiory `latin` + `latin-ext` (polskie znaki ą/ę/ł…). Vite bundluje je jako lokalne `.woff2`/`.woff` do `dist/assets/` — ZERO żądań sieciowych w runtime.
- `frontend/index.html`: usunięte wszystkie zewnętrzne odwołania — `preconnect`/`dns-prefetch` do `images.asyncti4.com` oraz `preconnect` do `fonts.googleapis.com`/`fonts.gstatic.com` i `link rel=stylesheet` do Google Fonts (IBM Plex). Na ich miejscu komentarz wyjaśniający lokalność. Zostały wyłącznie zasoby lokalne: ikona `/favico.png`, preload + `@font-face` dla `Ambroise Firmin` (logo splashu, `/font/…`, self-hosted) i tło `/static/extra/main_menu.jpg` z Backendu. Brak skryptów analitycznych (nigdy ich nie było).
- Bez binarnych plików fontów w repo: `@fontsource` żyje w `node_modules` (gitignore), pliki trafiają do bundla przy buildzie — zgodne z polityką „grafiki/fonty poza repo" (D1); `.gitignore` bez zmian.
- Bramka frontendowa zielona: `npm run type-check` (czysto), `npm run build` (tsc + vite build OK; w `dist/assets/` widoczne lokalne `ibm-plex-sans-*`/`ibm-plex-mono-*` `.woff2`). `npm run lint` bez NOWYCH błędów — pozostają wyłącznie 2 preistniejące błędy w `RulesBrowserPage.tsx` (poza zakresem zadania, nietknięte).
- Staging TYLKO moich plików (nie `git add .`): `frontend/index.html`, `frontend/src/main.tsx`, `frontend/package.json`, `frontend/package-lock.json`, `docs/PROGRESS.md`. Niezacommitowane cudze zmiany nienaruszone. Wymagania: 2.1, 2.4, 2.6 (realizacja ładowania fontów lokalnie — R2.3, R2.7; czyszczenie zewnętrznych odwołań z `index.html`).
### ✅ Blok local-ti4-data-foundation 11.7 — statyczny test zewnętrznych URL + audyt (ukończony)
- `tests/test_locality_guard.py`: dopisany test `test_frontend_has_no_external_urls_outside_allowlist` (R2.5, R2.6, R12.2). Skanuje `frontend/src/**` (ts/tsx/js/jsx/css), `index.html` i `vite.config.ts` czystym skanerem `scan_external_urls` z `src/audit/locality.py` (pliki `*.test.ts(x)` i hosty lokalne `localhost`/`127.0.0.1` pomijane). Wszystkie pozostałe `http(s)://` muszą pasować do prefiksu z `audit/external_url_allowlist.json`; w komunikacie błędu podpowiedź, żeby dodać zasadny URL do listy dozwolonej z notą.
- `audit/external_url_allowlist.json`: dodany wpis `http://www.w3.org/2000/svg` z notą „identyfikator przestrzeni nazw SVG (xmlns) w osadzonych maskach data:image/svg+xml; nie jest pobierany po sieci". Skan wykrył DOKŁADNIE 3 trafienia tego namespace w CSS masek (`PlanetCard`, `Relic`, `Tech`) — to standardowy identyfikator XML, nie żądanie sieciowe. Pozostałe prefiksy (tirules2.com, github.com/dangothemango/tirules, ti4battle.com, discord.com za flagą D2) były już na liście z not.
- Uruchomiono `uv run python -m src.audit`: sekcja „Zewnętrzne URL spoza listy dozwolonej: 0" oraz „Manifest grafik: brakujące na dysku: 0" — części audytu w zakresie 11.7 są czyste, więc NIE trzeba było uruchamiać `--write-manifest` ani zgłaszać braków do `sync_assets`. Audyt kończy się kodem 1 z powodu PREISTNIEJĄCYCH, znanych luk referencyjnych homebrew (`explores_cpti`, attachmenty `gamma`/`mirage`/`ion` spoza aktywnych źródeł — R7.6) raportowanych w zadaniach 4.x; to nie jest regresja tego bloku ani błąd w zakresie 11.7.
- Bramka QA zielona: `uv run pytest -q` (438 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 106 source files). Wymagania: 2.5, 2.6, 12.2.
### ✅ Blok local-ti4-data-foundation 11.5 + 11.6 — testy Vitest frontendu (Resolver_Zasobów i grafiki lokalne) (ukończony)
- Infrastruktura testowa Vitest była już skonfigurowana w `frontend/vite.config.ts` (środowisko `jsdom`, `globals`, `setupFiles: ./src/test/setup.ts`, `passWithNoTests`), ale brakowało dwóch zależności dev (pliki testowe nie istniały jeszcze w projekcie): `fast-check` (do 11.5) oraz peer `@testing-library/dom` wymagany przez `@testing-library/react@16` używany w `src/test/setup.ts`. Dodane do `frontend/package.json` z DOKŁADNIE przypiętymi wersjami (`--save-exact`, bez `^`): `fast-check@4.10.2`, `@testing-library/dom@10.4.2`.
- 11.5 (Property 17) — `frontend/src/shared/assets/resolveAsset.test.ts`: test właściwościowy `fast-check` (`numRuns: 100`) sprawdzający, że dla DOWOLNEJ logicznej ścieżki `assetUrl`/`sheetUrl` zwraca wyłącznie napis lokalny (`/static/...` albo `PLACEHOLDER_URL`), NIGDY nie zawiera `://` ani hosta zewnętrznego. Osobny generator celowo wstrzykuje adresy CDN/URL-e (`images.asyncti4.com`, `emoji-cdn.mqrio.dev`, `fc.webUrl()`, losowe `scheme://host/...`) — wynik i tak jest lokalny. Dodatkowe przypadki: wiodące slashe i pusta ścieżka → placeholder. **Validates: Requirements 2.1, 2.6.**
- 11.6 — `frontend/src/shared/assets/localAssets.test.ts` (Vitest): (a) żaden plik źródłowy w `frontend/src` (poza `*.test.ts(x)`) nie importuje usuniętego `cdnImage` i plik `cdnImage.ts` nie istnieje (R2.2); (b) `getFactionImage` zwraca ścieżkę lokalną także dla dawnych ikon typu `EMOJI`/`DISCORD` (R2.4); (c) `sheetUrl` oraz `getUnitSprite` (jednostka kolorowa i współdzielona) dają lokalny obraz sheetu (R2.1); (d) `assetManifest.json` (artefakt frontu) jest DOKŁADNIE zgodny ze zbiorem ścieżek z jednego źródła prawdy `audit/assets_manifest.json` — brak nadmiarowych i brakujących (R3.1).
- Bramka frontendowa zielona: `npm run type-check` (czysto), `npm run test` (`vitest --run` → 2 pliki, 14 testów, wszystkie pass), `npm run build` (`tsc && vite build` OK, exit 0). `npm run lint` zgłasza WYŁĄCZNIE 2 PREISTNIEJĄCE błędy w `src/domains/rules/RulesBrowserPage.tsx` (plik niemodyfikowany, poza zakresem 11.5/11.6); oba nowe pliki testowe przechodzą lint osobno (`eslint` na nich → 0 problemów).
- UWAGA: niezacommitowane zmiany innej osoby (`assets/config/engine_config.json`, `src/api/schemas.py`, `src/core/*`, `frontend/src/api/useNewGame.ts`, `frontend/src/domains/setup/*`, nowe pliki `frontend/public/faction_portraits/*`) NIE były ruszane ani stagowane. Staging TYLKO moich plików: `frontend/src/shared/assets/resolveAsset.test.ts`, `frontend/src/shared/assets/localAssets.test.ts`, `frontend/package.json`, `frontend/package-lock.json`, `.kiro/specs/local-ti4-data-foundation/tasks.md`, `docs/PROGRESS.md`. Wymagania: 2.1, 2.2, 2.4, 2.6, 3.1.

### ✅ Blok local-ti4-data-foundation 13.1 — numeracja RULES.md + sekcja wyników audytu (ukończony)
- Ujednolicona numeracja `docs/RULES.md`: usunięte duplikaty numerów sekcji. Dawna „3 (bis)" (Limity sztuk jednostek) → `3a` (konwencja lettered-subsekcji jak `2a/2b/2c`). Druga sekcja „30" (Limity rąk i poziomy trudności bota) → `36`, przeniesiona fizycznie na koniec pliku, by kolejność w pliku = kolejność numeryczna (29, 30…35, 36). Podsekcje `30.1/30.2` → `36.1/36.2`.
- Spis treści uzupełniony o dotąd brakujące wpisy sekcji 31, 32, 33, 34, 35 oraz nowych 36 i 37 (wcześniej TOC kończył się na 30). Odwołania do sekcji 34/35 pozostają stabilne.
- Zaktualizowano odwołania w kodzie wskazujące na sekcję limitów rąk/trudności „RULES.md 30" → „RULES.md 36" (tylko komentarze/docstringi): `src/core/registry.py`, `src/core/setup_service.py`, `src/core/models.py`, `src/api/schemas.py`, `src/api/routers/game.py`, `src/config.py`, `assets/config/engine_config.json`, `frontend/src/api/useNewGame.ts`, `tests/test_registry.py`. Odwołania do akcji strategicznej („RULES.md 30" = sekcja 30) pozostały nienaruszone.
- Dodana sekcja `37. Wyniki audytu danych`: (37.1) tabela liczb komponentów per Źródło_Kanoniczne — ludzkie podsumowanie maszynowego `audit/baseline_counts.json` (zero liczb z pamięci; źródło `StaticDataCatalog.counts()`, zgrane z `uv run python -m src.audit --json`); (37.2) znane luki referencyjne homebrew udokumentowane jako NIE-usterki: `explores_cpti` (18 refów), `mirage`, `gamma`/`gw`, `ion`; (37.3) anomalia `codex1` w `theodisi.json` jako ⚠️ ZAŁOŻENIE (D6); (37.4) wpisy ⚠️ ZAŁOŻENIE: `TRIGGER_WINDOW_MAP` (D10, link do sekcji 34) i placeholder `<color>` (link do sekcji 35), z prośbą o potwierdzenie; (37.5) komendy odświeżenia liczb.
- Nowy test `tests/test_docs_numbering.py`: identyfikatory `## N.` są unikalne (blokuje ponowne duplikaty), sekcja audytu 37 istnieje, wpisy założeń (`TRIGGER_WINDOW_MAP`, `<color>`, `explores_cpti`) obecne.
- Bramka QA zielona: `uv run pytest -q` (441 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success, 107 plików), `npm run type-check` (czysto — zmiana w `useNewGame.ts` to tylko komentarz).
- UWAGA: równolegle trwa zadanie 13.2 edytujące inne pliki docs. Staging TYLKO moich plików (nie `git add .`). Wymagania: 6.6, 12.4, 12.7.

### ✅ Blok local-ti4-data-foundation 13.2 — dokumentacja fundacji danych + `.gitignore` (ukończony)
Domknięcie dokumentacji po całej fundacji danych (zadania 1–12 zrealizowane). Blok tylko
docs + `.gitignore` (bez zmian w kodzie → QA backendu/frontendu niekonieczna). Wymagania: 3.3, 12.3, 12.5.

- **`docs/README.md`** — sekcja 3 (struktura repo) rozbudowana o nowe moduły fundacji:
  `core/sources.py`, `core/components.py` (Katalog_Komponentów), `core/component_loader.py`,
  `core/references.py`, `core/timing_spec.py`, `core/effects_registry.py`, `core/rules_links.py`,
  cały katalog `src/audit/` (Audytor_Danych: `locality.py`, `assets_manifest.py`, `frontend_data.py`,
  `diffs.py`, `report.py`, `sync_assets.py`), router `api/routers/components.py`, Resolver_Zasobów
  (`frontend/src/shared/assets/`) i katalog `audit/` (manifest + baseline w repo, D1). Usunięte
  framingi „grafiki z CDN"; sekcja 4 dostała bullet o pełnej lokalności offline (Resolver_Zasobów,
  `@fontsource/*`, manifest + `sync_assets`, `uv run python -m src.audit`).
- **`docs/ARCHITEKTURA_KODU.md`** — mapa §2 uzupełniona o wszystkie nowe moduły `core/` i warstwę
  `src/audit/`; §4 (routery) dostał wiersz `api/routers/components.py` (tylko-odczyt); nowa sekcja
  **§4a „Fundacja danych i Audytor_Danych"** opisująca Katalog_Komponentów, wybór po `source` (D9),
  Specyfikację_Czasową (D10), Rejestr_Efektów (pod hooki, bez efektów kart), powiązania z regułami
  i lokalność grafik/fontów (D1/D12).
- **`docs/ARCHITEKTURA_PO_MIGRACJI.md`** — poprawione wszystkie opisy „grafiki z CDN /
  images.asyncti4.com": obraz całości, diagram ASCII i §4.1 (dawny `cdnImage.ts` → Resolver_Zasobów
  `resolveAsset.ts`, grafiki z `/static`, fonty `@fontsource/*`, D1/D11).
- **`.gitignore`** — nagłówek sekcji ASSETY opisuje decyzję D1 (grafiki/fonty POZA repo; lokalność
  przez `audit/assets_manifest.json` + `src.audit sync_assets --from <katalog>`); komentarz przy
  `assets/config/effects_status.json` tłumaczy Rejestr_Efektów (D12). Dodany blok dokumentujący, że
  konfiguracja Audytora i manifesty SĄ wersjonowane — `audit/assets_manifest.json`,
  `audit/baseline_counts.json` (D1: MUSZĄ być w repo), `expected_gaps.json`, `external_url_allowlist.json`,
  `unused_asset_dirs.json` oraz `frontend/src/shared/assets/assetManifest.json`.
- **Stan `.gitignore` zweryfikowany (`git check-ignore`):** grafiki (`assets/units/sheets`,
  `assets/factions`, `assets/tokens/sheets`) są ignorowane (poza repo, D1); `audit/*.json`,
  `assets/config/effects_status.json` i frontendowy `assetManifest.json` NIE są ignorowane i są
  śledzone (`git ls-files`). Żadnych nowych wyjątków nie trzeba było dodawać — wpis w `.gitignore`
  dokumentuje decyzję i zabezpiecza przed przyszłą szeroką regułą `audit/*`.

**Następny krok:** zadanie 14 (final checkpoint — pełny `uv run pytest -q` / `ruff` / `mypy` oraz
front type-check/lint/build zielone) i decyzje D1–D12 do potwierdzenia przez użytkownika.

---

### ✅ Strażnik anty-hardkodowania danych + instrukcja Katalogu_Komponentów (ukończone)
- Nowy test `tests/test_no_hardcoded_data_guard.py` (skanery AST, wzór
  `test_locality_guard.py`) pilnujący, by przyszłe moduły faktycznie używały lejka
  danych zamiast go obchodzić. Dwa testy:
  - **`test_zrodla_kanoniczne_tylko_w_sources_py`** — kolekcja literałów z ≥3 nazwami
    źródeł kanonicznych (`base`/`pok`/`codex1-4`/`thunders_edge`) jest DOZWOLONA tylko
    w `src/core/sources.py` (`SOURCE_PRIORITY`). Pojedyncze porównania (`source == "pok"`),
    komentarze i docstringi nie są łapane (odporność na fałszywe alarmy). Łapie
    „ktoś przekleił listę źródeł zamiast zaimportować `SOURCE_PRIORITY`".
  - **`test_dane_gry_czytane_tylko_przez_rejestr_i_loader`** — żaden plik w `src/core/`
    (poza `registry.py`, `component_loader.py`, `references.py`, `components.py`) ani
    `src/api/` nie odwołuje się do `config.<KATEGORIA>_DATA_DIR` RAZEM z odczytem dysku
    (`glob`/`open`/`read_*`) ani nie globuje `assets/data/<kategoria>`. Kategorie starsze
    (units/technologies/factions/leaders/abilities/breakthroughs) wyłączone — czyta je
    celowo `registry.py`. Lista katalogów kategorii wyliczana z modułu `config`, więc
    test nie rozjeżdża się przy dodaniu nowej kategorii.
- **Wynik skanu:** ZERO naruszeń w istniejącym kodzie — architektura jest lejkowa
  (`SOURCE_PRIORITY` importowany wszędzie z `sources.py`; dane kategorii czytane wyłącznie
  przez `load_components`/`StaticDataRegistry.catalog`).
- `docs/README.md`: nowa sekcja **„4a. Jak korzystać z Katalogu_Komponentów"** z
  przykładem (`catalog.all/get/faction_bundle/query_timing`), listą endpointów API i
  gwarancjami (filtr po `source`, regresja liczb, test anty-hardkodowania).
- QA zielone: `uv run pytest -q`, `uv run ruff check src tests`, `uv run mypy src tests`.

### ✅ Blok E8-T3b — popup decyzji secondary (follow/don't follow) + blokada End turn (ukończony)

**Cel (ustalenie z użytkownikiem):** gdy aktywny gracz ZAGRA kartę strategii, pozostali
gracze — po kolei, od gracza na lewo od aktywnego, zegarowo — dostają JAWNY wybór
„follow / don't follow" secondary (język planszówki). Dopiero gdy WSZYSCY zdecydują,
aktywny gracz może dać „End turn". Co dokładnie robi follow (efekt liczbowy) — poza
zakresem; tu tylko wybór i przesunięcie kolejki. Tryb: dziś hot-seat na jednym
komputerze, docelowo sieć — dlatego pyta graczy po kolei, nie zakłada jednego operatora.

**Backend (sędzia — RULES.md 31.6, R_strategic_action):**
- [x] `src/core/turn_flow.py::end_turn` — twarda blokada: gdy `state.pending_window is not
  None`, `ValueError` → HTTP 422 („Cannot end the turn while a timing window is open…").
  Dotyczy KAŻDEGO typu okna (secondary, assign-hits, space cannon, reakcja), nie tylko
  secondary — turę oddaje się tylko „między" oknami. Okno secondary już otwierał
  `strategic_action.play_strategy_card` (T3), a `/strategy/secondary` (execute true/false)
  przesuwa kolejkę i auto-zamyka po ostatnim graczu — bez zmian.
- [x] `docs/RULES.md` — nowa podsekcja 31.6 (End turn zablokowany, dopóki trwa okno;
  źródło R_strategic_action; „follow"/„don't follow" = `execute` true/false; popup +
  wygaszony End turn).
- [x] `tests/test_turn_flow.py::test_end_turn_blocked_while_timing_window_open` (nowy).

**Frontend (język planszówki + popup):**
- [x] `frontend/src/domains/game-shell/components/SecondaryDecisionModal.tsx` (NOWY):
  nieodrzucalny popup (`AppModal`, bez krzyżyka / klik poza / Escape) pytający BIEŻĄCEGO
  respondenta okna `STRATEGY_SECONDARY`: „Follow" (execute=true) / „Don't follow"
  (execute=false). Pokazuje ikonę+nazwę gracza, nazwę karty (z `context.initiative`) i ilu
  graczy jeszcze po nim. Adresuje po `currentResponderId`; znika, gdy backend domknie okno.
- [x] `frontend/src/pages/GameMapPage.tsx` — modal zamontowany obok pozostałych modali.
- [x] `TurnControls.tsx` i `GameStatePanel.tsx::PhaseControls` — „End turn" WYGASZONY
  (`disabled`) i z tooltipem, dopóki `pendingWindow` ≠ null; dodatkowa podpowiedź w
  `TurnControls`.
- [x] `GameStatePanel.tsx::WindowSection` — dla secondary etykiety przycisków panelu
  bocznego zmienione na „Follow" / „Don't follow" (inne okna zostają przy Execute/Pass).

**QA (wszystko zielone):** backend `uv run pytest -q` 482 passed (było 481, +1), ruff +
mypy --strict czyste (110 plików). Frontend `npm run type-check`, `npm run lint`,
`npm run build` czyste (warn o rozmiarze chunku bez zmian).

**Następny krok:** dokładanie realnych efektów secondary kartą po karcie (dispatch w
`strategic_action`, RULES.md 30) oraz kolejne typy okien (assign-hits w walce — T7/T8).

### ✅ Blok E8-T3b-fix — aktywny gracz nie znika po pasie / zamknięciu okna (ukończony)

**Zgłoszenie użytkownika:** po tym, jak aktywny gracz w fazie akcji SPASUJE (pas jest
„jak akcja" — trzeba potem i tak oddać turę) albo gdy po zamknięciu okna secondary gracz
jest spasowany, przycisk „End turn" ZNIKAŁ — nie dało się dokończyć tury.

**Diagnoza:** web-data gasi aktywnego gracza do PODŚWIETLENIA, gdy jest `passed`
(`_effective_active_id` → `activePlayer`=null, `playerData[].active`=false, Bug 7). Panel
tury (`TurnControls`/`useDeskPlayer`) opierał „czyja tura" właśnie na tych polach, więc po
pasie tracił gracza i chował przyciski. Backend przez cały czas trzymał poprawne
`active_player_id` (end_turn działał na 200) — problem był czysto w projekcji/UI.

**Naprawa (rozdział „podświetlenie" vs „czyja tura"):**
- [x] `src/api/web_data.py` — NOWE pole `gameState.activeTurnPlayer` (kolor gracza wg
  `active_player_id`, BEZ gaszenia przez `passed`; przez `_color_of`). `activePlayer`
  (highlight) bez zmian — dalej gaśnie dla spasowanego (Bug 7).
- [x] `frontend/src/entities/data/types.ts` — pole `activeTurnPlayer?: string | null`.
- [x] `useDeskPlayer` — „gracz pulpitu" najpierw po `activeTurnPlayer`, potem fallback na
  `playerData[].active`/mówcę/pierwszego posadzonego (zgodność ze starymi migawkami).
- [x] `TurnControls` — `isAction` liczony z `activeTurnPlayer` (czyja tura), nie z
  `active.active` (gaśnie przy passed).
- [x] `GameStatePanel.PlateBody` — gracz tury z `activeTurnPlayer ?? activePlayer`
  (status karty / canPass / PhaseControls nie gubią gracza po pasie).
- [x] `tests/test_web_data.py::test_active_turn_player_survives_pass_in_action_phase`
  (nowy): spasowany aktywny gracz → `activePlayer`=null, ale `activeTurnPlayer`=jego kolor.

**QA (wszystko zielone):** backend `uv run pytest -q` 483 passed (+1), ruff + mypy czyste;
frontend type-check + lint + build czyste.


### ✅ Blok E8-T3b-ui — reguła „akcja albo pas przed End turn" + dopieszczony UI tury (ukończony)

**Zgłoszenia użytkownika:** (1) box potwierdzenia pasa rozpychał panel (resize, brak
spójności); (2) ważna reguła — gracz musi wykonać JAKĄŚ akcję (strategiczna/taktyczna/
komponentu) albo spasować, i dopiero wtedy może dać End turn; (3) wyłączony przycisk dalej
miał kolor akcji — ma być szary; (4) „Next phase" nie powinien wyglądać na szary (wyblakły).
Dodatkowo potwierdzenie: ZAGRANIE KARTY STRATEGII to akcja (odblokowuje End turn).

**Backend (sędzia — RULES.md 31.7, R_action_phase):**
- [x] `PlayerState.took_action_this_turn` — flaga „akcja w bieżącej turze".
- [x] Ustawiana: `strategic_action.play_strategy_card` (akcja strategiczna = zagranie karty),
  `tactical.activate_system` (akcja taktyczna). Resetowana w `turn_flow.end_turn` (następny
  gracz) i `next_phase` (wejście w fazę akcji).
- [x] `turn_flow.end_turn` — 422, gdy aktywny gracz nie wykonał akcji ANI nie spasował.
- [x] `web_data`: `playerData[].tookActionThisTurn` do frontu.
- [x] `docs/RULES.md` 31.7; testy: `test_turn_flow` (wymóg akcji/pasu + reset flagi),
  `test_strategic_action_api` (zagranie karty = akcja → End turn bez pasu po oknie).

**Frontend (UI):**
- [x] Potwierdzenie pasa = MODAL (`AppModal`), NIE inline — panel tury nie zmienia rozmiaru
  (stabilny, spójny UI). Dotyczy `TurnControls` i `GameStatePanel.PhaseControls`.
- [x] „End turn" aktywny dopiero gdy `tookActionThisTurn || passed` i brak okna; inaczej
  SZARY + podpowiedź „Take an action or pass, then End turn." Po akcji/pasie pulsuje (nudge).
- [x] Wyłączone przyciski = SZARE (neutralne), bez barwy akcji (CSS `:disabled` w obu panelach).
- [x] „Next phase" dostał realny akcent (color-mix na `--ds-accent`), nie wygląda na szary.
- [x] `types.ts`: `GameState.activeTurnPlayer` (z poprzedniego bloku) + `PlayerData.tookActionThisTurn`.

**QA (wszystko zielone):** backend `uv run pytest -q` 486 passed, ruff + mypy czyste; frontend
type-check + lint + build czyste.

- Front/ruch: drag jednostek na mapie domyślnie tylko do aktywnego systemu (walidowany `/tactical/move`); swobodny drag (God-Mode) pod ustawieniem „Free unit dragging". Ctrl+klik zaznacza grupę (1 klik = 1 sztuka, statki + myśliwce/piechota/mechy), plakietka „Cap użyte/pojemność" przy kursorze, drag grupy = jedna komenda ruchu.

### Tactical action dock: stała stopka + walidowany „End action" (2026-11-07)
- `core/tactical.end_action` (+ wspólny `_check_can_leave` z `next_step`): `/tactical/end` nie pozwala
  porzucić trwającej walki, okien Space Cannon/CAPACITY/FLEET_POOL, niedokończonej inwazji ani
  obowiązkowej walki kosmicznej (422). Surowe `end_tactical_action` zostaje dla `next_step`/wewnętrznie.
- Front: panel akcji = nagłówek + kroki + przewijana zawartość + STOPKA przypięta (Next/End nie skaczą);
  przyciski wyszarzone z powodem blokady; usunięte skróty jednostek (flota/transport) z kroku Movement.
### Talia agend Absol przełączana w Ustawieniach (2026-11-08)
- Fanowskie źródło `absol` ładuje się WYŁĄCZNIE dla agend i talii agend
  (`sources.AGENDA_VARIANT_SOURCES`, `load_components(agenda_variant_sources=…)`); `enabled_sources.json`
  bez zmian. `objectives.deck_card_ids` pomija te talie, wariant wybiera `objectives.agenda_deck_ids`.
- `DecksState.agenda_variant` ustawiany przez `/game/new` (`agenda_deck`: standard | absol,
  nieznany → 422); `card_draw.ensure_agenda_deck` zasiewa wybraną talię. Absol = `agendas_absol` (60 kart). Black Spectrum odłożony.
- Front: przełącznik „Absol agenda deck" w Ustawieniach (Game variants, `settings.absolAgendas`); `createNewGame` wysyła `agenda_deck`. Kreator setupu bez zmian.
- Efekty kart agend nadal NIE są kodowane (ewidencja praw); nietypowe cele (`manual`) wpisuje operator.
- Baseline audytu odświeżony (`audit/baseline_counts.json`, +agendas/decks dla Absol).
- Pula agend na froncie idzie za talią gry: `cardPool.agendaVariant` (web-data) → `agendaPool(variant)`
  (rewers talii agend + wyszukiwarka). `activeDecks.ts` ma `AGENDA_VARIANT_DECK_IDS` (generator
  `scripts/gen_active_decks.py`). Karty Absol mają plakietkę „ABS" (`shared/ui/FanSourceBadge`):
  pula kart, Rada Galaktyczna, prawa w grze, panel stanu agendy.
- FAN-AGENDAS: w grze Absol każdy gracz dostaje „Absol's Political Secret" (`absol_<kolor>_ps`) ZAMIAST
  `<kolor>_ps` (`game_setup.common_promissory_note_ids(..., variant)` wg `homebrewReplacesID`). Loader
  wpuszcza ze źródła `absol` tylko notki-zamienniki; front rozpoznaje `absol_<kolor>_ps` w
  `entities/lookup/promissoryNotes.ts`, karta notki ma plakietkę „ABS". Baseline audytu +1 (promissory/absol).

---

# Bloki przeniesione z PROGRESS.md (2026-11-16)

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

---

<!-- Przeniesione z PROGRESS.md 2026-11-19: bloki 2026-11-08 … 2026-11-18 -->
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

## 2026-11-17 — Audyt rulingów Mentak + wstrzymanie walki po Sustain Damage

- Wstrzymanie walki po Sustain Damage ostatniej strony (RULES.md 54.10a, decyzja użytkownika): wcześniej
  okno „po Sustain Damage” strony przypisującej straty jako ostatnia (i jedynej przy trafieniach Ambush)
  zamykało się w tym samym kroku — Direct Hit / Reflective Shielding były niezagrywalne (F_mentak 4.1).
  `ActiveCombat.sustain_hold` + `reaction_pause.would_open` + `battle.release_sustain_hold` (wołane
  w `step_settle`); Reflective w trakcie wstrzymania otwiera nowe przypisanie (`battle.add_combat_hits`).
  Okno bitwy: notka „waiting for reactions” (`sustainHold` w `/tactical/battle`).
- Sleeper Cell + Direct Hit Mentaka: zastępczy statek staje od razu (F_mentak 7.1) —
  `sleeper_direct_hit` / `sleeper_on_direct_hit`; `reactions_combat.DIRECT_HIT` publiczne.
- `tests/factions/test_rulings_mentak.py` (43 testy), `@ruling` w `test_flows_mentak`; statusy: Creuss
  (requires creuss), Valefar (requires nekro), umowa o Pillage (na). Mentak zdjęty z UNAUDITED.
- RULES.md 62.8, 54.10a.
- Zauważone przy audycie (poza zakresem): transakcje w fazie agend nie są obsługiwane
  (`transaction.validate_transaction` przyjmuje tylko fazę akcji).
- QA: pytest 2714 ✓ (test_undo_move niestabilny — pada też bez zmian), ruff ✓, mypy ✓, tsc ✓, eslint ✓,
  vitest battle ✓. Bez build/e2e (drobna notka w BattleCenter). Wymaga restartu backendu.

## 2026-11-17 — Audyt rulingów Sardakk N'orr

- Valkyrie Particle Weave: przerzut/premia kości przed przypisaniem strat (Fire Team, War Funding,
  Wrath of Kenara, relikty) gubiły dodatkowe trafienie — `battle._recount_dice` + `_extra_hits`
  przeliczają je razem z kośćmi; Fire Team idzie przez `battle.reroll_combat_dice`.
  ⚠️ ZAŁOŻENIE: VPW patrzy na trafienia przeciwnika po zmianach kości.
- Exotrireme II: każdy egzemplarz osobno (`triggers.repeat_offer`); z Yin na zmianę od atakującego
  (gracz z ponowioną ofertą staje na końcu kolejki REACTION).
- G'hom Sek'kus: działa bez statków w aktywnym systemie (PERMIT `invasion.commit_from_planets`),
  Dominus Orb dopuszcza źródła z żetonem, nie na Demilitarized Zone. DMZ blokuje teraz każde
  lądowanie (`planet_stats.is_demilitarized` w `invasion.commit_*`).
- Tekklar Conditioning: oferty „po ruchu statków” przepadają.
- `tests/factions/test_rulings_sardakk.py` (24 testy), `@ruling` w `test_sardakk.py` i
  `test_rulings_audit.py`; statusy: Harrow (L1Z1X), Magmus Reactor (Muaat). Sardakk zdjęty z UNAUDITED.
- RULES.md 62.1.

## 2026-11-17 — Audyt rulingów Winnu

- Mathis Mathinus (bohater) + Trade: gracze wskazani primary Trade wypadali z kolejki secondary,
  gdy bohater ich nie wskazał — teraz są w niej i MUSZĄ je rozstrzygnąć bez żetonu (F_winnu Mathis 2);
  wskazani bohaterem mogą, płacąc żeton (`strategic_action._finish_primary`).
- Okno secondary bohatera ma znacznik `hero` (`strategic_action.HERO_KEY`): Acquiescence nie da się
  zagrać (bohater to nie akcja strategiczna — F_winnu Mathis 3); wcześniej notka była zagrywalna.
- `tests/factions/test_rulings_winnu.py` (21 testów), `@ruling` w `test_winnu`, `test_flows_winnu`
  (purge bohatera, powrót Acquiescence) i `test_rulings_audit`; statusy: stara Acquiescence (na),
  Construction PoK (na), Salai Sai Corian vs Nekro (requires nekro), Dimensional Splicer (requires
  creuss). Winnu zdjęty z UNAUDITED.
- RULES.md 62.7.

## 2026-11-17 — Audyt rulingów Federation of Sol

- Military Support: odzyskana transakcją w tym samym oknie „początek tury Sola” dawała się zagrać
  drugi raz — znacznik `sol.SUPPORT_PLAYED` (`Duration.TURN`) do końca tury Sola.
- Genesis: nadmiar capacity po piechocie z końca statusu przetrwał całą fazę strategii —
  `limits.enforce_limits` sprawdza teraz także fazę strategii od 2. rundy (runda 1 = rozstawienie
  startowe). RULES.md 42.x.
- `tests/factions/test_rulings_sol.py` (27 testów): Orbital Drop + DEPLOY mecha, Versatile, Military
  Support (przed Orbital Drop, tura pasu, 0 żetonów, transakcja na początku tury, 1 transakcja,
  nie dwa razy w oknie), Spec Ops II (próg 5, powrót), Advanced Carrier II, Genesis, Evelyn DeLouis
  (+1 kość dla grupy, cudza siła, tylko rzuty walki), Claire Gibson (każda planeta walki, bez walki
  bez sił, atak zniszczony przed walką — scenariusze przez API), Jace X, Bellum Gloriosum (łączna
  pojemność, koszt łączny). Status: Harrow L1Z1X (requires l1z1x). Sol zdjęty z UNAUDITED
  (lista pusta).
- QA: pytest 2799 ✓, ruff ✓, mypy ✓. Bez frontu. Wymaga restartu backendu.

## 2026-11-17 — Transakcje w fazie agendy + czat z szeptami

- RULES.md 47.5 (R_transactions, R_agenda_phase, C_agendas): przy każdej agendzie każda para graczy
  może zawrzeć jedną transakcję, bez sąsiedztwa. `transaction.agenda_window` / `agenda_pair_free`;
  limit pary zapisany po obu stronach `transacted_with`, zerowany przy każdym otwarciu głosowania
  (nowa agenda, Veto, Miscount Disclosed). Stół 47.1b bez zmian; w agendzie stroną inicjującą jest
  otwierający stół. Feed: etykieta `transaction:<partner>:<gracz>`.
- UI: przycisk Transaction w pasku okna Rady (`AgendaOverlay`) i w panelu tury w fazie agendy — to
  samo okno `TransactionModal` (teksty zależne od fazy, „traded this agenda”).
- RULES.md 47.6: czat + szepty (`core/chat.py`, `GET /chat`, `POST /chat/send`). Treść szeptu widzą
  nadawca i adresat; reszta widzi „X whispers to Y”. Czat poza `GameState` (metadane partii; Undo go
  nie cofa); push `{"type":"chat"}` odświeża tylko dziennik. `domains/chat/ChatPanel`: zwinięta ikonka
  z licznikiem (lewy dół, nad oknem Rady), przesuwalny panel, adresat szeptu = chip gracza.
- Testy: `tests/test_transaction_agenda.py`, `tests/test_chat.py`, `test_activity`,
  `ChatPanel.test.tsx`.
- QA: pytest 2800 ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest (chat, agenda, TurnControls, network) ✓,
  build ✓. e2e pominięte — port :5273 zajęty (inna sesja). Wymaga restartu backendu (nowe trasy).

## 2026-11-17 — Decyzje rulingów (VPW, Auto-Factories, Darktalon, Construction) + stonowane tło bitwy

- Decyzje użytkownika (RULES.md 62.1/62.2/62.5/62.6, 30.12):
  - Valkyrie Particle Weave: trafienia przeciwnika liczone po przerzutach i premiach do kości (kod
    już tak działał) — ⚠️ zamienione na ✅.
  - Auto-Factories (Hacan): liczą się statki niemyśliwskie z CAŁEJ akcji (suma zamówień,
    `production_placed`); żeton raz na akcję — przy zamówieniu przekraczającym próg 3 (`_many_ships`).
  - Darktalon Treilla: przegląd praw w aktywnych źródłach — jedyne to Fleet Regulations (limituje
    żetony puli floty), więc PERMIT `fleet_pool.unlimited` pokrywa „not limited by laws”. Bez zmian kodu.
  - Construction: przy pustej rezerwie struktura może być zdjęta z systemu bez własnego żetonu
    (R_component_limitations), w primary i secondary. `placeable_structures(allow_board=True)`,
    nowe `structure_board_sources`, payload `source`. UI: po wyborze planety drugi klik NA MAPIE
    wskazuje planetę źródłową („Change planet” wraca do wyboru celu).
- Okno bitwy kosmicznej: tło stonowane (przygaszona mgławica, nieruchome gwiazdy; usunięte smugi
  pyłu i błyski odległych wybuchów). Ruch przeniesiony na okręty: dryf z lekkim przechyłem,
  rzadkie ciągi korekcyjne dysz, powolne „żeglowanie” szeregów po wlocie (`rankCruise`).
- Naprawiony powtarzany wlot floty: w StrictMode efekt startu był wołany dwa razy i drugi raz
  wychodził przed ustawieniem `entered`, więc formacja zostawała „w trakcie wlotu” i każda zmiana
  animacji okrętu odpalała `fleetFly` od nowa. Teraz `ENTRY_START` pamięta chwilę startu, ponowny
  montaż dokańcza pozostały czas (dźwięki też liczone od startu).
- Testy: `test_strategy_construction_warfare.py` (+2), `test_rulings_hacan.py` (+1), `test_hacan.py`.
- QA: pytest (tests/factions, strategy) 606 ✓, ruff ✓ (poza `tests/rulings.py` z równoległej sesji),
  mypy ✓ (zmienione moduły), tsc ✓, eslint ✓, vitest battle+strategy ✓. Pełny pytest, build i e2e
  pominięte (zmiany punktowe, bez nowych importów). Wymaga restartu backendu.

## 2026-11-17 — Kontrakt rulingów kart i zasad ogólnych (C_*, R_*) + audyt reliktów i eksploracji

- Decyzja użytkownika: rulingi kart/komponentów ogólnych i zasad ogólnych mają ten sam kontrakt co
  frakcje — każdy punkt `docs/rules_tirules/C_*.md` i `R_*.md` = test z `@ruling` albo status.
  - `tests/rulings.py`: `general_contract` (ID `C_relics/neuraloop/3`, `R_movement/notes/2`;
    sekcje „Related Topics” pomijane). Pliki kart (`CARD_FILES`: karty akcji, agendy, relikty,
    technologie, notki, wydarzenia): wymagane tylko sekcje kart z hookiem — karta dodana później
    od razu wymaga testów rulingów (strażnik czerwony). Podgląd: `uv run python -m tests.rulings C_agendas`.
  - Strażnik `tests/test_ruling_coverage.py` (+3 testy): dług z chwili wprowadzenia w
    `tests/rulings_debt.json` (plik `R_x` albo sekcja `C_x/karta`), `GENERAL_DEBT_LIMIT` tylko maleje,
    przeaudytowany wpis trzeba usunąć. Nowy status `gap` = ruling sprawdzony, silnik go nie spełnia.
  - Stan: 295 → 271 wpisów długu (~2000 rulingów do audytu: karty akcji, agendy, technologie,
    cele, notki, zasady R_*).
- Przeaudytowane: `C_relics`, `C_exploration_cards`, `R_exploration`, `R_relics`, `R_frontier_tokens`,
  `R_attach`, `R_purge` (`tests/rulings_general/test_rulings_relics.py`, `test_rulings_exploration.py`
  + oznaczone istniejące testy). Naprawione błędy silnika:
  - Circlet of the Void zabierał +1 do ruchu za gravity rift (ten sam punkt co Nav Suite) — nowy
    punkt `movement.ignore_anomalies_keep_rift`, `movement.rift_rolls`, pole `riftRolls` w podglądzie trasy.
  - The Codex brał z odrzuconych przy pustej talii — `card_draw.reshuffle_action_deck_if_empty`.
  - Nano-Forge nie liczył się jako legenda w celach (`make_history`, `become_legend`, `sai`).
  - Derelict Vessel przy 3 zdobytych tajnych celach blokował dobranie — zawsze można oddać dobrany.
  - Freelancers pozwalał stawiać siły na planecie czekającej na eksplorację.
- Luki (`gap`): Scepter of Emelpar poza secondary (cele, zdolności frakcji), limit jednego celu na
  walkę, eliminacja gracza (fragmenty/relikty), wybór wormholu przy Ion Storm. Zgłoszone poza
  kontraktem: The Silver Flame „may be exchanged as part of a transaction” nie jest obsługiwane.

## 2026-11-18 — Audyt rulingów technologii, celów, notek i agend + luki z audytu reliktów

- Przeaudytowane (kontrakt C_/R_): `C_technology`, `C_agendas`, `C_promissory_notes`,
  `R_agenda_phase`, `R_agenda_card` — nowe `tests/rulings_general/test_rulings_technology.py`,
  `test_rulings_agendas*.py`, `test_rulings_agenda_phase.py`, `test_rulings_promissory.py`.
  Dług `tests/rulings_debt.json`: 271 → 213 wpisów (`GENERAL_DEBT_LIMIT`).
- Zamknięte luki z poprzedniego audytu:
  - Scepter of Emelpar także przy płatności celów żetonami i zdolnościach frakcji wydających żeton
    strategiczny (Xxcha, Hacan, Sol): `command_tokens.strategy_token_sources/_input`, pole
    `scepter` płatności celu.
  - Limit jednego celu na walkę (R_objective_cards, Neuraloop): `objective_events.combat_objective_used`.
  - Ion Storm: gracz wybiera wormhole, gdy system ma własny tego samego typu
    (`ion_storm.choice_needed`, `move_fleet(ion_storm_token=...)`, wybór w `MoveRouteBox`).
  - Eliminacja gracza (RULES.md 66, nowy `core/elimination.py`): warunki R_elimination, sprawdzana
    na końcu tury; fragmenty na stosy odrzuconych, relikty purge, notki, agendy, tajne cele, mówca.
    Strażnik: kandydat tylko z systemem domowym na planszy (niepełne scenariusze nie tracą graczy).
  - The Silver Flame wymienialny w transakcji (`transaction.tradable_relics`, chip `Relic` na stole).
  - Derelict Vessel: pełne nazwy celów w opcjach zwrotu.
  - Support for the Throne: przy wymianie pierwszy zyskuje aktywny gracz (w agendzie — od mówcy).
- Nowe funkcje punktów centralnych: `card_draw.take_agenda_from_discard`,
  `exploration.discard_cards`, `triggers.drop_player_offers`.
- `tests/test_undo_move.py` niestabilny (~30%): lotniskowiec startował na 101, a to gravity rift
  mapy demonstracyjnej API — rzut 1–3 go niszczył. Start na pozycji bez anomalii z tej samej mapy.
- Nowe luki (`gap` w `tests/rulings_status.json`): Sling Relay zamykany bez produkcji, brak okna
  przed Assault Cannon po dołożeniu statków, Ceasefire blokuje przeniesienie sił z planet na statki.
- QA: pytest 3041 ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest (TurnControls, battle, movement,
  Activity, StatusPhase) ✓, build ✓. e2e pominięte (bez zmian kreatora/lobby). Wymaga restartu backendu.

## 2026-11-18 — Moduły wariantów gry (fanowskie talie, erraty, własne komponenty)

- Wariant agend Absol był wpisany na sztywno (stałe w `sources.py`, ~15 miejsc `FAN-AGENDAS`).
  Teraz to ogólny mechanizm sterowany danymi: `assets/config/variants.json` + `core/variants.py`.
  Instrukcja: `docs/WARIANTY.md`.
- Moduł: cała talia (`decks`) albo errata pojedynczych kart (`replaces`, `homebrewReplacesID`;
  1 karta może zastąpić N kopii) dla agend, kart akcji, reliktów, eksploracji, celów i wspólnych
  notek. Loader dociąga ze źródła modułu tylko potrzebne wpisy (`VariantLoadPlan`).
- Gra: `/game/new` `variants` (stare `agenda_deck` działa dalej), `DecksState.variants`;
  `objectives.deck_card_ids(..., state)` liczy skład talii gry (agendy, relikty, karty akcji,
  cele, eksploracje). Stare gry z `agenda_variant="absol"` mapują się na moduł `absol_agendas`.
- Nowy moduł `absol_relics` (talia 20 reliktów Absol). Efekty reliktów Absol nie są
  oprogramowane (własne id, ręczna ewidencja).
- Front: przełączniki w Ustawieniach generowane z manifestu (`settings.gameVariants`, migracja
  z `absolAgendas`), pule kart i edytor gracza wg `cardPool.variants` (`isInGameDeck`),
  plakietki źródeł z manifestu. `scripts/gen_active_decks.py` emituje `VARIANT_MODULES`.
- Ograniczenia: front zna tylko karty ze starego eksportu (Black Spectrum i własne karty
  wymagają dopisania danych), tech/jednostki/frakcje nadal tylko globalnie przez
  `enabled_sources.json`.
- QA: pytest (pełny) ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest (entities, cards, search,
  settings, player, state, api) ✓. e2e pominięte (kreator bez zmian). Wymaga restartu backendu.

## 2026-11-18 — Moduły wariantów dla wszystkich komponentów (errata w miejscu, mechanika, tekst)

- Rejestr danych PER GRA: `StaticDataRegistry(variant_ids=...)`, `AppContext.registry` wg
  `decks.variants` (cache per zestaw), `/game/new` buduje setup na rejestrze z modułami.
- Errata w miejscu (`replaces`) dla każdej kategorii (technologie, jednostki, frakcje, zdolności,
  liderzy, przełomy, planety, karty strategii, karty, notki, cele, ploty): komponent zachowuje
  oficjalne id, dostaje treść wariantu; odwołania `bsp_*` przemapowane na id oficjalne. Nowe
  komponenty (`adds`), całe talie (`decks`), parametry reguł (`rules`, `variants.rule_value`).
- Mechanika: hooki z `variant=<źródło>` (`register`, `on_event`, `register_effect`,
  `register_ability`…); oficjalny hook podmienionego komponentu się wyłącza
  (`rules_hooks.variant_active`, `effect_for`). Bez hooka wariantu = ręczna ewidencja.
- Tekst: `/api/public/game/{id}/variant-data` + front `entities/lookup/variantData.ts` (nakładanie
  w lookupach i pulach kart, nowe karty spoza danych frontu).
- Fracture: rzut wejścia, liczba ingressów i jednostki neutralne jako parametry `rules`.
- Moduły: `absol_agendas`, `absol_relics`, `absol_tech`, `bsp_factions`, `bsp_firmament_plots`
  (zastępuje przełącznik „Black Spectrum Firmament Plots”), `bsp_objectives`, `bsp_cards`,
  `bsp_agendas`. Hooków wersji fanowskich jeszcze brak.
- Absol's Political Secret to teraz errata `<color>_ps` (ręka ma `red_ps` z tekstem Absol).
- Regenerowane: `OKNA_CZASOWE.md`, `POKRYCIE_HOOKOW.md` (agendy Absol już nie w rejestrze
  domyślnym), baseline audytu. Instrukcja: `docs/WARIANTY.md`.

## 2026-11-18 — B8: The Argent Flight (RULES.md 62.11)

- Moduł `core/hooks/factions/argent.py`: Zeal (głos pierwszy + głosy za graczy), Raid Formation
  (uszkadzanie statków nadwyżką AFB, decyzja Argent przy prawdziwym wyborze), Aerie Hololattice
  (blokada przelotu, PRODUCTION 1 planet ze strukturami), Strike Wing Alpha II (9–10 w AFB
  niszczy piechotę w przestrzeni, natychmiastowa eliminacja), Strike Wing Ambuscade, Trilossa Aun
  Mirik (przeniesienie wyprodukowanych sił naziemnych — decyduje producent), Trrakan Aun Zulok
  (odblokowanie 6 jednostek z AFB/SC/Bombardment, +1 kość), Helix Protocol, Quetzecoatl, Aerie
  Sentinel, Wing Transfer (żetony + ruch na koniec akcji).
- Nowe punkty silnika (`rules_hooks`): `agenda.vote_first`, `combat.afb_extra_dice`,
  `combat.afb_raid`, `combat.afb_infantry_kill`, `movement.passage_blocked`,
  `production.planet_value`. Okna `UNIT_ABILITY_USED/WHEN` przed rzutem AFB, Space Cannon
  i Bombardment. Pojemność: ładunek z `capacityUsed: 0` liczy się bez statku z pojemnością,
  transport wymaga statku z pojemnością. Okno Bribery zamyka głos kolejnego gracza (mówca Argent).
- UI: przepis bohatera na planszy (`heroBoardFx`), wybór „Extra dice” zamiast etykiety Plasma
  Scoring (commander/notka dokładają kości tej samej grupie). Ruch Helix/Wing Transfer = sloty
  „cel na mapie + jednostki na mapie” w zwykłym oknie decyzji.
- ⚠️ Założenia do potwierdzenia: Z1–Z3 w RULES.md 62.11, status `helix-protocol/3.1`.
- QA: pytest (pełny) ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest (KeyMoments, invasion,
  game-shell/components) ✓. e2e i `npm run build` pominięte (bez zmian kreatora/zależności).
  Wymaga restartu backendu.

## 2026-11-18 — Dodatkowe kości osobno + „Auto” w płatnościach

- ✅ Decyzja użytkownika: każde źródło dodatkowych kości (Plasma Scoring, commander Argent, Strike
  Wing Ambuscade) przypisywane osobno — „Auto” (najcelniejsza grupa, domyślnie) / grupa / bez
  kości. `core/extra_dice.py`; Space Cannon Offense/Defense i Bombardment: pole `extraDice`
  (stare `plasmaUnit` zostaje dla zgodności); AFB: `POST /tactical/battle/afb/extra-dice`
  (`ActiveCombat.afb_picks`), widok `afbExtra`. UI: wspólny `shared/ui/ExtraDicePicker`.
- ✅ Decyzja użytkownika: przycisk „Auto” tam, gdzie go brakowało — wspólny `PaymentPicker`
  (żeton Custodians, cele „Spend…”, ekspedycje) i pole płatności w oknach decyzji
  (`DecisionFields`); najtańsza płatność jak w produkcji/badaniu (`techModel.autoPay`).
- Agent Argent: zostaje przenoszenie tylko z planet (decyzja użytkownika).
- QA: pytest (pełny) ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest (battle, invasion, offers,
  strategy, game-shell/components, ExtraDicePicker) ✓. e2e i build pominięte. Wymaga restartu
  backendu (nowe pole stanu i trasa).

## 2026-11-18 — Wygoda okien decyzji: ruch z efektu, capacity, neutralni, kości, karty strategii

- ✅ Ruch z efektu (`offer_inputs.unit_moves`: Helix Protocol, Wing Transfer, kolejne) jak zwykły
  ruch: klik w świecący system → wiersze jednostek (+1 / prawy −1 / Shift = wszystkie, „Select all”)
  → klik w świecący cel; także Ctrl+klik jednostek na mapie (to samo zaznaczenie co w oknie)
  i przeciągnięcie stosu/grupy. Lista „Planned moves” z −/+, linie na mapie (`EffectMoveLayer`).
  Ponowny klik w wybrany system odznacza. `UnitMovesField`, `useUnitDrag`, `MultiSelectHud`.
- ✅ RULES.md 39.6 C5 (decyzja użytkownika): nadwyżka capacity bez wyboru (np. myśliwce zostawione
  bez nosiciela) znika od razu (`capacity.forced_removal` / `remove_forced_excess`); okno CAPACITY
  tylko przy realnym wyborze. Helix/Wing Transfer nie odrzucają już ruchu „Capacity exceeded”.
  `limits.enforce_limits` przenosi stan po automatycznym usunięciu.
- ✅ RULES.md 50.3 (decyzja użytkownika): neutralni walczą jednostkami ulepszonymi
  (`neutral.variant_key` w walce i inwazji) — zastępuje założenie „bazowe”.
- ✅ Bramka „kości w locie” (`domains/dice/diceGate.ts`): oferty, „Available now”, karty z ręki,
  okna capacity / fleet pool, toasty Activity i ekran zwycięstwa czekają, aż kości wylądują.
- ✅ Wybór na mapie: ponowny klik zawsze odznacza (GroupedMapField zostawiał fokus/chip,
  RouteNumbersField, Diplomacy, Construction).
- ✅ Okna przesuwane (pływający `Modal`, stół kart strategii) nie wychodzą poza ekran
  (`utils/keepOnScreen.ts`).
- ✅ Stół kart strategii: baner właściciela U GÓRY karty w kolorze gracza („Picked by” + frakcja),
  wybrane karty bez wygaszenia z obramowaniem, kolejka wyboru w nagłówku (kto wybiera, kto co ma).
- ✅ Karty z ręki: poza przeciągnięciem także przycisk „Play …” / „Discard …” w podglądzie.
- QA: pytest (pełny) ✓, ruff ✓, mypy (zmienione moduły) ✓, tsc ✓, eslint ✓, vitest (offers, dice,
  map, game-shell) ✓. e2e i build pominięte. Wymaga restartu backendu.

## 2026-11-18 — Argent: transport przy ruchu bohaterem (ruling FAQ)

- ✅ Ruling FAQ od użytkownika (dopisany do `F_argent`, `F_lizix`, `F_mahact`): „During movement
  abilities (L1Z1X Hero, Argent Hero, Mahact Hero), you may transport units out of systems that
  contain your tokens”. Helix Protocol zabiera piechotę/myśliwce także z systemu z żetonem Argent
  (zakaz `helix-protocol/3` → status „zastąpione”, 3.1/3.2 z testem).
- Ruch statków komponentem wydzielony do `core/direct_move.py` (Helix, Wing Transfer; dalej
  L1Z1X Dark Space Navigation).
- QA: pytest (Argent, flows, ruling coverage) ✓, ruff ✓. Wymaga restartu backendu.

## 2026-11-18 — Okna pływające nie zamykają się przy kliku w mapę (Helix Protocol)

- ✅ Błąd: Ctrl+klik / przeciągnięcie jednostki przy ruchu bohaterem Argent zamykało okno i
  pokazywało „Activate a system first”. Przyczyna: `Dialog` base-ui ma `closeOnFocusOut`, a ds
  `Modal` dla `floating` ignorował tylko `outside-press`. Teraz ignoruje też `focus-out`
  (`frontend/src/ds/overlays.tsx`), więc zaznaczenie Ctrl trafia do `UnitMovesField`.
- Test: `frontend/src/ds/overlays.test.tsx` (bez poprawki pada).
- QA: tsc ✓, eslint ✓, vitest (offers, ds) ✓. Backend bez zmian; build/e2e pominięte.

## 2026-11-18 — B9: The L1Z1X Mindnet (RULES.md 62.12)

- Moduł `core/hooks/factions/l1z1x.py` (11/11 komponentów): Assimilate (wymiana PDS/doków przy
  przejęciu, pusta rezerwa → struktura z planszy wybrana na mapie), Harrow (bombardowanie po
  rundzie walki naziemnej — oferta, rzut na stół, trafienia przypisuje obrońca), Inheritance
  Systems, Super Dreadnought II (dane), [0.0.1], Annihilator, I48S, 2RAM, Dark Space Navigation,
  Cybernetic Enhancements, Fealty Uplink (wybór „przed / po eksploracji”).
- Nowe punkty silnika: `control.structures_replaced` (inwazja nie niszczy struktur przed
  Assimilate), `bombardment.ignores_planetary_shield`, `bombardment.ground_units`
  (`invasion.ground_bombarders`), `combat.hits_to_non_fighters` (wymagany cel trafień w
  `battle._open_assign`), `technology.paid_ignore_all` (skip `paid:<karta>|<planety>|<tg>`,
  `ResearchPlan.reserved_planets` — osobna zapłata). Nowy rdzeń `core/combat_bombardment.py`.
  Okno „When you gain command tokens during the status phase” (krok REDISTRIBUTE).
- UI: `TechnologyOverlay` — przełącznik Inheritance Systems z osobną płatnością (wspólny
  `PaymentPicker` z „Auto”); efekt bohatera na planszy (`heroBoardFx`). Reszta przez zwykłe okna
  decyzji (mapa, chipy).
- ⚠️ Otwarte (zgłoszone): Infiltrate dla innych frakcji nie ma czego wymienić — `_establish_control`
  niszczy cudze struktury przed oknem karty (stan sprzed bloku); Harrow nie otwiera okna „przed
  rzutem zdolności” (Strike Wing Ambuscade przy Harrow — jeszcze nie).
- QA: pytest (pełny) ✓, ruff ✓, mypy ✓, tsc ✓, eslint (zmienione) ✓, vitest (technology,
  KeyMoments) ✓. e2e i `npm run build` pominięte (bez nowych zależności i zmian kreatora).
  Wymaga restartu backendu.

## 2026-11-18 — Infiltrate po inwazji, Harrow w oknie walki naziemnej

- ✅ Infiltrate (dla każdej frakcji): inwazja niszczy cudze struktury w chwili przejęcia, a karta
  „When you gain control” wymienia właśnie je — `_establish_control` zapisuje zniszczone
  struktury w `control_changes[...]["destroyed"]`, ślad zużywa się raz (RULES.md 53).
- ✅ Decyzja użytkownika: Harrow nie zamyka panelu walki naziemnej — rzut to wpis dziennika
  walki `BOMBARDMENT` (fizyczne kości okna bitwy, nagłówek „Harrow — orbital bombardment”),
  animacja: lance plazmy z orbity na siły obrońcy, kratery i wybuchy (`BattleOverlay`).
- ✅ Okno Strike Wing Ambuscade przed rzutem Harrow (`combat_bombardment.register_roll_offer`,
  `reactions_invasion.unit_ability_roll_windows`); źródło kości bez pola w formularzu = „Auto”.
- QA: pytest (pełny) ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest (battle) ✓. Animacja nie
  sprawdzona zrzutem ekranu. e2e i build pominięte. Wymaga restartu backendu.

## 2026-11-18 — B10: The Embers of Muaat (RULES.md 62.13)

- Moduł `core/hooks/factions/muaat.py` (13/13 komponentów): Star Forge, Gashlai Physiology,
  Magmus Reactor Ω (wejście do supernowej, PRODUCTION 5, brak eliminacji), Prototype War Sun I/II,
  The Inferno (nowy rodzaj akcji komponentu `unit:<id>`), Ember Colossus, Umbat, Magmus,
  Adjudicator Ba'al — Nova Seed, Fires of the Gashlai, Stellar Genesis (Avernus, The Nucleus).
- Nowe punkty silnika: `movement.through_supernova` / `movement.into_supernova`,
  `production.system_value`, `elimination.has_production`; `command_tokens.spend_strategy_token`
  emituje `STRATEGY_TOKEN_SPENT`; jedno miejsce emisji `SHIPS_MOVED` (`movement.fire_ships_moved`,
  `ctx.ships/route/kind` — ruch taktyczny, odwrót, ruch komponentem); wymiana kafla
  `core/tile_swap.py` (`GameState.replaced_tiles`, Undo przez `HexGrid.tile_originals`).
- Feed Activity: fakt `tile_replaced` („<stary system> was replaced by <nowy>”).
- Animacja: Nova Seed na planszy (`heroBoardFx` → `muaathero`, cel `nova` = kafel `81`, znacznik
  `nova`: rozbłysk gwiazdy, fala uderzeniowa, promienie plazmy) po scenie bohatera; sprawdzone
  zrzutem ekranu. Stellar Genesis — wspólna scena przełomu.
- Decyzja użytkownika: siły naziemne Muaat z planet wymienionego kafla trafiają do przestrzeni,
  struktury Muaat z tych planet wracają do rezerwy.
- QA: pytest (pełny) ✓, ruff ✓, mypy ✓, tsc ✓, eslint (zmienione) ✓, vitest (game-shell, map) ✓.
  e2e i `npm run build` pominięte (bez nowych zależności, kreatora). Wymaga restartu backendu.

## 2026-11-18 — Muaat: żeton Avernus na mapie, decyzja Stellar Genesis, Nova Seed przed wymianą kafla

- ✅ Żeton Avernus widać na mapie: web-data wystawia planety-żetony z `added_planets`
  (`PLANET_TOKENS` = Mirage, Avernus) jako token w przestrzeni systemu.
- ✅ Stellar Genesis: wybór systemu klikiem na mapie także przy jednej legalnej opcji
  (`choice(always=True)`), nic nie dzieje się po cichu.
- ✅ Nova Seed: do chwili wybuchu mapa rysuje STARY kafel (`useHeroFx.covers` z faktu
  `tile_replaced` we wpisie bohatera → `MapTile`); nowa animacja: brzeg heksa żarzy się,
  pierścienie zapadają do środka, błysk zasłania wymianę (`revealAt` 1,65 s), cienka fala
  uderzeniowa, odłamki plazmy, poświata supernowej; dźwięk (`warSunEnter`, `explosionHeavy`,
  `explosion` — próbki walki, suwak „Battle effects”). Przepisy bohaterów mogą mieć `sounds`.
- War suny w walce mają już własną animację (wyłanianie z wormhole, dźwięk wejścia, salwa
  „sunfire”) — Prototype War Sun Muaat używa tej samej grafiki `ws`.
- QA: pytest (Muaat, API, ruling coverage) ✓, ruff ✓, mypy (zmienione) ✓, tsc ✓, eslint ✓,
  vitest (game-shell, map) ✓; zrzuty animacji (bez obrazów kafli — harness bez backendu).
  e2e i build pominięte. Wymaga restartu backendu.

## 2026-11-18 — Prototype War Sun I/II: własna oprawa w oknie walki (Muaat)

- ✅ Decyzja użytkownika: war suny Muaat są dla frakcji kluczowe — mają własną animację.
  Wariant rozpoznawany z danych jednostki (`battle/protoWarSun.ts`: frakcyjny `muaat_warsun*` /
  `tf-pws`, poziom z `upgradesFromUnitId`), atrybut `data-proto="1|2"` okrętu i pocisków.
- Wejście: kuźnia gwiazdy (roztopione jądro z wirującym żarem) zamiast indygo wormhole; dźwięk
  zapłonu (`explosionHeavy` + `sunfire` obok `warSunEnter`). Na polu: korona plazmy z
  protuberancjami, żużel unoszący się z okrętu, ciepła poświata sprite'a; II — druga,
  przeciwbieżna obręcz i jaśniejszy żar. Salwa: większa, bielsza kula z dłuższym warkoczem,
  szersza pożoga. Śmierć: korona rozbłyska i zapada się.
- Ogólny war sun wariantu bez frakcji (`baldrick_muaat_warsun`) nie dostaje oprawy (test).
- QA: tsc ✓, eslint ✓, vitest (battle) ✓; zrzuty ekranu (bez sprite'ów — harness bez backendu).
  Backend bez zmian; build/e2e pominięte.

## 2026-11-18 — Muaat: Avernus także w systemach z planetami, Nova Seed jako supernowa

- ✅ Błąd Stellar Genesis: kandydaci byli brani ze `state.systems` / `grid_from_state`, a wpis
  stanu mają tylko systemy, w których coś się działo (np. żeton frontier w pustych) — zostawały
  same systemy bez planet. Teraz siatka gry (`board_graph.bound_grid`, z hyperlane i
  wormhole), lista `non_home_systems`, system bez wpisu tworzony przy położeniu
  (`ensure_system`). Ta sama siatka w Ember Colossus (sąsiedztwo).
- `card_labels.describe_system`: system bez wpisu stanu opisany z kafla mapy (planety i
  wartości zamiast samego „System 201”) — dla wszystkich kart z wyborem systemu.
- ✅ Nova Seed od nowa (9 s): gwiazda z koroną protuberancji puchnie i drga, korona i gwiazda
  zapadają się w punkt (wsysane pierścienie i materia), błysk całej planszy + promienie
  dyfrakcyjne (pod nim wymiana kafla, `revealAt` 3 s), poszarpana powłoka gazu (filtr
  turbulencji), fale uderzeniowe i ejekta, pulsująca mgławica z gwiazdą neutronową.
- Dźwięk głębszy: `playBattleSound` ma `rate` (niżej/dłużej) i `reverse` + `endIn` (próbka od
  tyłu kończąca się w zadanej chwili) — niski pomruk, wsysany wybuch zgrany z błyskiem, dwa
  głuche huki, ryk ognia.
- Strażnik `test_hero_board_fx_guard.py` rozpoznaje też przepis rozpisany na kilka linii.
- QA: pytest (pełny) ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest (game-shell, map, battle) ✓;
  zrzuty animacji ✓. e2e i build pominięte. Wymaga restartu backendu.

## 2026-11-18 — Fuzzer partii botów + luki generatora ruchów

- ✅ `tests/engine/fuzz.py`: losowe partie botów przez prawdziwe API
  (`uv run python -m tests.engine.fuzz --games 300 --rounds 5`, `--replay <ziarno>`). Losowe frakcje
  (3–6, jeden wariant z rodziny), bot losowy, losowa kolejność pytanych graczy, 50% partii z agendą.
  Po każdym ruchu: zgodność katalog ↔ HTTP, niezmienniki stanu (`check_invariants`), JSON round-trip
  i dokument web-data dla każdego gracza (to, co czyta front). Błąd = `fuzz_reports/fuzz_seed<N>.json`
  (ziarno, ostatnie akcje, traceback, migawka stanu); podsumowanie grupuje błędy po sygnaturze.
- `BotTable` (`tests/engine/driver.py`): wstrzykiwana polityka kolejności kandydatów, kolejność graczy
  i hook po kroku (bot pasywny bez zmian).
- ✅ Luki generatora znalezione fuzzerem (gra stawała): produkcja z Construction (krok `choose_dock`)
  i z secondary Warfare TE → nowa akcja `production_skip` („Finish production”,
  `/tactical/production/skip-grant`); obowiązkowa technologia z Research Grant Reallocation (wejście
  `research` w trybie GAIN → pierwsza dostępna); okno FLEET_POOL (np. po Clandestine Operations) → nowa
  akcja `fleet_pool_resolve` z podpowiedzią `core/fleet_pool.auto_removal`.
- Testy: zgodność HTTP obu nowych akcji (`test_actions_parity`), parametry GAIN (`test_legal_windows`),
  smoke fuzzera na stałych ziarnach (`test_fuzz_games`).
- Zakres fuzzera = zakres generatora: bez akcji taktycznej, walki i kart akcji (B5) — wejdą pod fuzzer
  automatycznie. Błędy UI: następny krok to odtwarzanie zapisanych stanów w przeglądarce (Playwright).
- QA: pytest `tests/engine` ✓, ruff ✓, mypy ✓. Pełny pytest i front pominięte (zmiana tylko
  w warstwie bota i testach). Wymaga restartu backendu (nowe akcje bota).

## Poprawki UI: ikona producenta Magmus Reactor, szary Avernus, Custodians najniżej (XI 2026)

- Okno produkcji: producent spoza jednostek dostaje `kind`/`sourceId` (`Producer.source` = HookSource
  hooka `POINT_PRODUCTION_SYSTEM_VALUE`) — Magmus Reactor pokazuje ikonę koloru technologii i jej
  nazwę zamiast pustego sprite'a „system”; planety-producenci (Custodian's Favour, Aerie Hololattice)
  ikonę planety.
- Wyczerpany żeton-planeta (Avernus) szarzeje cały (filtr na sprite w `Token.tsx`), okrąg planety
  go już nie przyciemnia częściowo.
- Żeton Custodians (`custodian`, `custodianvp`) ma z-index 2 — przykrywa go wszystko na kafelku.
- QA: pytest `-k "production or muaat"` ✓, ruff ✓, mypy ✓ (zmienione pliki), tsc ✓, eslint ✓,
  vitest production/map/utils ✓. Pełny pytest, build i e2e pominięte. Wymaga restartu backendu (nowe pola).

## 2026-11-19 — Okna reakcji: deklaracje pasu, wyciszenia, szybkie okna (RULES.md 54.12)

- ✅ `core/reaction_prefs.py`: prywatne deklaracje pasu per kategoria okna (`all`, `strategy`, `agenda`,
  `combat`, `sabotage`) z czasem trwania (`turn`/`round`/`agenda`/`combat`/`always`), „Ask me only when it
  concerns me” (`involved` liczone z informacji jawnej), wyciszone karty reakcji (po nazwie) i oferty
  „you may” (klucz `covers`; obowiązkowych nie da się wyciszyć). Wygasłe deklaracje czyści `step_settle`.
- „Quick windows” hosta (`GameState.quick_reaction_windows`, `POST /reaction-settings/quick`): okno kończy
  się, gdy wszyscy spasowali (`reaction_window.settle_quick`). Domyślna długość okna 4 → 5 s.
- UI: panel „Reactions” w `TurnControls` (`ReactionSettings`, zastępuje `ReactionAutoPassToggle`),
  „Never ask” w ofertach i prośbach o reakcję z ręki, ustawienie hosta w Ustawieniach;
  zminimalizowane okna jako przesuwalna pigułka `DraggablePill`.
- Testy: `tests/test_reaction_prefs.py`, `test_reaction_window.py`, `test_reaction_pause.py`, vitest
  `ReactionSettings`, `OfferNeverAsk`, `DraggablePill`.

## 2026-11-19 — B5: bot prowadzi akcję taktyczną + bot losowy (RULES.md 65.8)

- ✅ Katalog akcji podzielony: `engine/action_base.py` (kontekst, baza, kontrola aktora),
  `engine/actions_tactical.py` (aktywacja, ruch, produkcja, walka, odwrót, Space Cannon, inwazja,
  eksploracja, pojemność, karty akcji ACTION) + mapowanie HTTP w `api/bot_http.py`;
  generator wariantów `engine/legal_tactical.py` (pierwszy kandydat = ruch bezpieczny).
- `engine_config.json`: wszystkie poziomy trudności na `random` (do testów, decyzja użytkownika).
- Losowa frakcja (setup, kreator, fuzzer) najpierw z frakcji zrobionych (`core/faction_support`);
  znacznik „Ready” w kreatorze (tymczasowy). Wybór technologii startowych w kreatorze = karty `TechCard`.
- ✅ Błąd znaleziony fuzzerem (ziarno 11, gra stawała): „Finish production” z secondary Warfare w trakcie
  okna FLEET_POOL nie widziało okna secondary; po zamknięciu okna limitu (FLEET_POOL / CAPACITY)
  `strategic_action.resume_after_limit_window` kończy odpowiedź respondenta. Test w `tests/test_fleet_pool.py`.
- Strażnik `test_actions_parity`: rodzaje B5 jawnie w `NOT_YET_COVERED` („tylko fuzzer”) — celowane
  scenariusze zgodności HTTP do dopisania. Smoke fuzzera w pytest skrócony do 2 rund.
- Bot nie używa zdolności „may” wewnątrz kroków ani kart reakcji (okna reakcji botów pasuje silnik).

## 2026-11-19 — B11: The Clan of Saar (RULES.md 62.14)

- ✅ `core/hooks/factions/saar.py`: Scavenge, Nomadic, Floating Factory I/II (punkt centralny struktury
  pływającej `core/floating_structures.py`: dok w przestrzeni, ruch/odwrót jak statek, zniszczenie przy
  blokadzie), Chaos Mapping, Captain Mendosa, Rowl Sarrig, Gurno Aggero, Scavenger Zeta, Ragh's Call,
  Deorbit Barrage. Zmiany punktowe w `unit_ops`, `movement`, `retreat`, `tactical`, `objectives`,
  `board_edit`, `visibility`, `neighbors`.
- Setup: planety domowe przez `control.assign_home_planet` — bez zdarzenia `PLANET_CONTROL_GAINED`
  (Scavenge nie daje TG za dom), punkt centralny kontroli zachowany (z lustrem `controlled_planets`).
- Armageddon Relay: efekt na planszy (`heroBoardFx.ts`, fala z systemów z jednostkami Saar).
- Rulingi `F_saar` z testami (`tests/factions/test_saar.py`, scenariusze `test_flows_saar.py`); odroczone:
  scavenge 2.2 (Naaz-Rokha), floating-factory 8.1 (Nekro) w `tests/rulings_status.json`.
- QA (całość bloku 2026-11-19): pytest pełny ✓ (engine osobno), ruff ✓, mypy ✓, tsc ✓, eslint (zmienione) ✓,
  vitest offers/game-shell/settings/setup/shared/player/strategy/cards ✓, build ✓. e2e pominięte.
  Fuzzer: tylko 4 ziarna smoke (duża próba pominięta - za długa). Wymaga restartu backendu (nowe trasy i pola).

## 2026-11-19 — „No whens” / „No afters” w oknie Rady; bot bada technologie

- ✅ Połowiczne deklaracje agendy `agenda_when` / `agenda_after` (RULES.md 54.12): `reaction_prefs.skipped_moments`,
  `reaction_window.has_playable_reaction(skip_moments=...)` - karta akcji/notka pasująca tylko do okien
  z zadeklarowanym momentem nie liczy się; obie połowy = pas na całą agendę; zmiana w trakcie okna pasuje od
  razu (`pass_open_windows(..., registry)`).
- UI: `AgendaPassButtons` w oknie Rady (krok VOTE), deklaracja na bieżącą agendę; szersza deklaracja z panelu
  Reactions wciska obie połowy.
- ✅ Bot (RULES.md 65.8): primary i secondary karty Technology - warianty badania z zapłatą
  (`engine/legal.research_payloads`), wcześniej bot zawsze rezygnował.
- Scalanie okien before/after wokół jednego zdarzenia: poza agendą (już jedna pauza when+after) - nie ruszane.
- QA: pytest engine + reakcje/agendy/jolnar ✓, ruff ✓, mypy ✓ (zmienione), tsc ✓, eslint ✓, vitest agenda +
  ReactionSettings ✓. Duża próba fuzzera pominięta (puszcza użytkownik). Wymaga restartu backendu.

## 2026-11-19 — B11: The Naaz-Rokha Alliance (RULES.md 62.15)

- ✅ `core/hooks/factions/naaz.py`: Distant Suns, Fabrication, Black Market Forgery, Pre-Fab Arcologies,
  Supercharge, Visz El Vir, Eidolon / Z-Grav Eidolon, Garv and Gunn, Dart and Tai, Hesh and Prit (Perfect
  Synthesis), Absolute Synergy + Eidolon Maximum.
- Rdzeń (punkty ogólne, bez nazw frakcji):
  - Eksploracja: PERMIT `exploration.extra_draw` - `draw(extra=True)` dobiera 2 karty z tej samej talii,
    `POST /exploration/choose` wybiera jedną (reszta na stos odrzuconych); auto-dobór czeka na decyzję.
    „Po eksploracji planety” z kartą otwierającą produkcję (Freelancers) dopiero po tej produkcji
    (`ExplorationState.deferred_explored`, `exploration.after_grant` z `production`). Bot: `ExplorationChoose`.
  - `core/ship_roles` + FORBID `combat.space_ground_variant`: siły naziemne walczące jak statki z wartościami
    wariantu (Z-Grav tylko w trwającej walce kosmicznej w aktywnym systemie, Eidolon Maximum zawsze w
    przestrzeni); Assault Cannon i Demonstrate Your Power liczą je przez `space_ships`.
  - Rewersy kart (`combat.FLIP_SIDE_UNIT_IDS`) nigdy nie są wariantem bazowym; Eidolon Maximum wymaga
    `PlayerState.breakthrough_flipped` (`breakthrough.flip`/`flip_back`, `combat.player_variant`).
    Błąd danych AsyncTI4: `absol_naaz_mech_space` ma `source: pok` - wykluczony jawnie.
  - PERMIT `units.ground_moves_as_ship` (ruch/odwrót, pula floty, nie ładunek), FORBID
    `combat.ability_hit_immune` (Space Cannon, bombardowanie), FORBID `units.place_forbidden`
    (`unit_ops.place_units`, `board_reinforcements.can_place`), nowe zdarzenie `UNIT_REMOVED/AFTER`.
  - `strategic_action.begin_strategize_secondary(then=..., from_reinforcements=...)`: łańcuch okien secondary,
    żeton z rezerwy (bez `STRATEGY_TOKEN_SPENT`), pusta rezerwa = pula arkusza (`token_pool`).
  - Brother Milor Ω (Yin) za jednostkę statek+siła naziemna: wybór właściciela (F_yin 8, 8.1).
- UI: okno eksploracji („Draw 2 (Distant Suns)”, wybór 1 z 2 kart), okno secondary (koszt z rezerwy, wybór
  puli arkusza), chip przełomu „flipped” (`breakthrough.flipped` w web-data).
- Rulingi `F_naaz_rokha` z testami (`tests/factions/test_naaz.py`, scenariusze `test_flows_naaz.py`);
  domknięte odroczone: F_saar scavenge 2.2, F_yin milor Ω 8/8.1. Luki (`gap`): okno między flipem Eidolon a
  innymi zdolnościami startu walki (eidolon 2.1), Eidolon Maximum „albo pojemność” (eidolon-maximum 1),
  Direct Hit na Eidolon Maximum w walce naziemnej (6.1).
- ⚠️ Założenia do potwierdzenia: Garv and Gunn - planetę wybiera eksplorujący gracz (może zrezygnować);
  notatka AsyncTI4 „Eidolon Maximum na planecie walczy w walce kosmicznej” - NIE zaimplementowana (brak w tirules).

## 2026-11-19 — Entropic Scar (RULES.md 1.5), „Auto” żetonów w statusie, bez zaznaczania tekstu

- ✅ Anomalia Entropic Scar (Thunder's Edge, kafle `114` i `116` Lemox) - wcześniej flaga `isScar` w ogóle
  nie była czytana. `SystemDef.is_scar` -> anomalia `ENTROPIC_SCAR`; `core/entropic_scar.py` = jedno pytanie
  „czy blizna”. Blokady zdolności jednostek (przez i przeciw jednostkom w bliźnie): Sustain Damage
  (`battle.sustain_denied`), AFB (także nadany komponentem), Space Cannon (z blizny, w bliznę, Experimental
  Battlestation), Planetary Shield, Bombardment (inwazja i walka naziemna), Production jednostek, DEPLOY
  (Letani Behemoth, Dunlain Reaper, Scavenger Zeta, ZS Thunderbolt M2). Żeton Gamma w bliźnie wraca do puli.
- ✅ Start fazy statusu: statki w bliźnie -> oferta „may” (okno drzewa technologii, tryb GAIN, tylko
  nieposiadane technologie frakcyjne) za żeton z puli strategii; druga blizna = druga oferta. Nowe źródło
  hooków `SOURCE_RULE` (`rules_hooks.declare_rule_source`) - zasada ogólna posiadana przez każdego gracza.
- Rulingi `R_entropic_scars` z testami (`tests/rulings_general/test_rulings_entropic_scar.py`); zdjęte z długu.
- ⚠️ Założenia do potwierdzenia: DEPLOY nie stawia jednostki W bliźnie; Ion Storm to nie „wormhole token”.
- Przegląd anomalii: asteroidy, mgławica, supernowa, szczelina, blizna - obsłużone na kaflach. Żetony anomalii
  (`tokens/other.json`: nebula/asteroids/rift/entropicscar) nie mają dziś źródła w grze (włączone dodatki ich
  nie kładą) - silnik ich nie czyta.
- UI fazy statusu, krok 5: przycisk „Auto” (nowe żetony dopełniają pulę floty do największej floty, reszta do
  taktycznej; gracz zatwierdza). W grze sieciowej każdy widzi tylko SWOJĄ kartę rozdziału / punktowania,
  pozostali jako „Waiting for …” (`useCanActAs`).
- UI: globalnie wyłączone zaznaczanie tekstu i natywne przeciąganie obrazków (`ds/base.css`); pola edycji
  zostają zaznaczalne, wyjątek klasą `ds-selectable`.

## 2026-11-19 — Pole bitwy: bez ponownego wlotu po AFB i przeskoków po wrakach

- ✅ Szereg myśliwców liczony płasko (`wingRank` w `BattleFleet.tsx`): bez `div`-ów eskadr. Po stratach z AFB
  eskadry dzieliły się od nowa i myśliwce przechodziły do innego rodzica — React montował je od nowa (efekt
  „wlotu” i restart animacji). Szereg ma stały klucz = numer z `RANK` (wcześniej typ pierwszego okrętu).
- ✅ Domykanie szyku (FLIP) mierzy pozycje bez transformacji (`offset*`), działa też przy zmianie skali szyku
  i kontynuuje trwające dosuwanie (wcześniej po zniknięciu szeregu flota przeskakiwała).
- ✅ Fazy dryfu okrętów/silników/piechoty z id okrętu (`--ph`), dryf szeregu z numeru `RANK` — bez skoków
  po usunięciu wraku.
- Test: `frontend/src/domains/battle/battleFormation.test.ts`. Naprawiony błąd typów w
  `AgendaPassButtons.test.tsx` (blokował `tsc`).

## 2026-11-19 — Hesh and Prit (bohater Naaz-Rokha), kafelki kart strategii, mechy w kosmosie, kolejność reliktu

- ✅ Perfect Synthesis: jedno pole wyboru 0–2 kart strategii (`oi.multi`, kolejność kliknięć = kolejność
  rozstrzygania, F_naaz_rokha hesh 2–3) zamiast dwóch pól „First/Second” z opcją „None”; podpowiedź mówi
  o reliktcie i żetonach z rezerwy. Parametr `{"cards": [..]}`. Test okna w `tests/factions/test_naaz.py`.
- ✅ Kafelki kart strategii w oknach decyzji (Naaz, Hacan, Winnu, karty akcji): sama nazwa + „initiative N”,
  bez drobnego tekstu primary/secondary — ten jest pod ⓘ i w podpowiedzi (`DescribedOptionBody brief`).
- ✅ Walka w kosmosie: mechy (Z-Grav Eidolon) i piechota stoją prosto, bez obrotu okrętu (`BattleOverlay.module.css`).
- ✅ Scena odsłonięcia reliktu czeka na koniec sceny kluczowego momentu (`useHeroFx.stageBusy`, karencja
  1,2 s na feed) — najpierw animacja bohatera, potem relikt.

## 2026-11-19 — Paczka do rozesłania (PaxMagnifica.exe + zip) i samouczek w grze

- ✅ Paczka: `uv run python packaging/build_release.py` → `release/PaxMagnifica/` + `release/PaxMagnifica-<data>.zip`
  (~1,4 GB). Odbiorca rozpakowuje i klika `PaxMagnifica.exe` — bez Pythona, Node i dwóch okien.
  PyInstaller onedir (`packaging/pax_magnifica.spec`, cały pakiet `src` bo hooki frakcji są wykrywane `pkgutil`),
  obok `.exe`: `assets/` bez nieużywanych katalogów (`music_originals` 1,2 GB, `quick_reference`, `stickers`,
  `server_icons`), `docs/rules_tirules`, `frontend/dist`, `JAK_GRAC.txt`.
- ✅ `src/api/bundle.py` (`BundleApp`): jeden serwer na :8000 robi to, co w devie proxy Vite — `/bot/*` → API
  (z WebSocketem i lifespan), `/static` → assety, reszta → `dist` z fallbackiem SPA. USUWA `X-Forwarded-For`
  (bez proxy gość podałby `127.0.0.1` i udawał hosta, RULES.md 44.6); launcher uruchamia uvicorn z
  `proxy_headers=False`. Test: `tests/test_bundle.py` (prefiks, nagłówek, SPA, path traversal, WS, lifespan).
- ✅ `packaging/launcher.py`: `CUSTODIAN_ROOT` (nowe w `src/config.py`) = katalog `.exe`, `saves/` i
  `bug_reports/` obok `.exe`, pierwszy wolny port od 8000 (nie ubija cudzych procesów), adresy LAN w konsoli,
  `freeze_support` dla procesów roboczych bota. `src/api/__main__.py`: wydzielone `build_parser`/`build_server_app`.
- ✅ Samouczek (`frontend/src/domains/tutorial/`): okno „How to play” (13 rozdziałów: cel, ekran, runda, fazy,
  akcja taktyczna, walka, ekonomia, karty, gra sieciowa) — z toolbara mapy, z menu głównego i z panelu podpowiedzi.
  Panel „What now?” (lewy dół, nad czatem; zwija się do kompasu, przesuwany) mówi, co zrobić teraz: wybór karty,
  akcje tury, krok akcji taktycznej, walka, decyzja w oknie, cudza tura/bot, „Next phase” u mówcy, status, agenda.
  Logika: czysta `coachHint.ts` + testy; `HowToPlayModal.test.tsx`.
- E2E: lokatory `Play` z `exact: true` (nowy przycisk „How to play”). `tools.e2e.ts` „zoom mapy” pada też bez
  tych zmian — kursor testu (1300, 700) trafia w wachlarz kart strategii; do poprawy w teście.
- ✅ Zaproszenia w grze (okno Invites): link z adresem hosta w sieci zamiast `localhost`, ten sam port co strona
  (`network/inviteOrigin.ts` + test); przy kilku sieciach (dom + ZeroTier) wybór „Friends connect through”.
- `build_release.py`: nie nadpisuje `release/PaxMagnifica`, gdy gra z niego działa albo ma zapisy w `saves/`
  (PyInstaller czyści katalog razem z zapisami); `--out KATALOG` buduje obok.

## 2026-11-19 — Podział dużych plików (mniej tokenów na odczyt)

- Backend (warstwy tylko w dół; moduł bazowy eksportuje nazwy dalej `n as n`, wywołania `battle.x` bez zmian):
  `battle.py` 2134 → 1593 + `battle_units.py` (jednostki, trafienia, Sustain) + `battle_rerolls.py`
  (przerzuty/zmiany kości po rzucie: relikty, Fire Team, War Funding); `invasion.py` 1536 → 779 +
  `invasion_common.py` / `invasion_bombard.py` / `invasion_defense.py`; `movement.py` 1426 → 987 +
  `movement_paths.py`; `web_data.py` 1922 → 297 + `web_game` / `web_tiles` / `web_player_units` /
  `web_players`; `schemas.py` 1833 → pakiet `api/schemas/` (`common`, `setup`, `tactical`, `combat`, `cards`).
- Front: `useBoardEditor.ts` 1853 → 1180 + `api/boardQueries.ts` (zapytania tylko do odczytu, `export *`);
  `BattleOverlay.tsx` 1509 → 763 + `BattleVolley.tsx` + `BattleAssaultCannon.tsx`.
- Pominięte: `GameStatePanel.tsx` (równoległa sesja ma w nim niezacommitowane zmiany), rdzeń maszyny stanów
  `battle.py` i jeden hook `useBoardEditor` (wzajemna rekurencja / jeden hook — podział zmieniłby API).
- Testy: `monkeypatch` kości przerzutu celuje teraz w `battle_rerolls`. Opis warstw: `ARCHITEKTURA_KODU.md`.
- QA: pytest (pełny) ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest (battle, api, game-shell) ✓, build ✓.
  e2e pominięte. Wymaga restartu backendu (nowe moduły).

## 2026-11-19 — Porządek ekranu gry (mniej okien, nic się nie nakłada)

- Setup: „Skip setup (random)” widoczny TYLKO z opcją Settings → „Skip phases button (God-Mode)”
  (`GameSetupOverlay.tsx`); e2e włączają ją przez `enableSkipShortcuts` (`e2e/fixtures.ts`) + nowy test „bez opcji brak przycisku”.
- Panel fazy (`GameStatePanel`, wariant info): bez listy kart strategii i bez kolejności wyboru w fazie strategii
  (pokazuje to stół kart); martwa gałąź info w `StrategyCardPicker` usunięta.
- „What now?” = sekcja panelu fazy (`tutorial/CoachSection.tsx`, dawniej osobne okno `CoachPanel` w lewym dole,
  nachodziło na panel fazy i czat); zwija się nagłówkiem do jednej linii.
- Czat przypięty do lewego dolnego rogu (`bottom: 16px`, nie `--hand-dock-clear` — rozwinięta ręka wypychała go
  pod panel fazy); dok akcji taktycznej i panel fazy kończą się nad ikoną czatu.
- Invites hosta: przycisk w nagłówku (`InvitesButton` w `HeaderGameControls`) zamiast pływającego na planszy.
- Stół kart strategii: bez wiersza „Now picking / Speaker” (chipy kolejki: „picking…”, korona mówcy); baner mieści
  się między panelem fazy a centrum decyzji.
- Ręka: pusta zakładka kurczy się do linii komunikatu (zamiast 176 px pustej tacy).
- QA: tsc ✓ (poza niezacommitowanym `useBoardEditor.ts` równoległej sesji), eslint ✓, vitest (game-shell, tutorial,
  network, setup, chat) ✓, build ✓, e2e 8/8 (tools.e2e: zoom zwija stół kart przed kółkiem). Backend bez zmian.

## 2026-11-22 — B12: The Naalu Collective (RULES.md 62.16)

- ✅ `core/hooks/factions/naalu.py`: Telepathic, Foresight, Gift of Prescience, Neuroglaive, Hybrid Crystal
  Fighter II, Matriarch, Iconoclast TE, Z'eu (TE), M'aban (Codex), The Oracle, Mindsieve. Older variants
  (Z'eu/Z'eu Ω, M'aban PoK, Iconoclast/Iconoclast Ω) = `na` in `rulings_status.json`.
- Core (generic points, no faction names):
  - "0" token: `core/initiative_zero.py` (player effect, initiative 0 in `turn_flow.turn_order` /
    `strict_initiative_order`, removed when returning strategy cards in `status_phase.finish_status`); reaction window
    "end of strategy phase" (`reactions_misc.strategy_phase_end`) for PNs from hand.
  - `command_tokens.place_token` = single place putting a token in a system + new `COMMAND_TOKEN_PLACED/AFTER` event
    (activation, retreat, Diplomacy, Signal Jamming, Stymie...).
  - Fleet pool: PERMIT `fleet_pool.fighters_overflow` + MODIFY `fleet_pool.fighters_per_ship` (HCF II = 1/2 ship,
    rounded up); `FleetReport.excess_after`, excess removal without redundant units.
  - Invasion: FORBID `invasion.ground_force_types` (`ship_roles.ground_force_types`) — Matriarch fighters land,
    fight, take Space Cannon Defense hits, return to space after combat and before Establish Control
    (`invasion.return_ships_to_space`); API invasion view shows them as committable forces.
  - `core/peek.py` + FORBID `info.peek`: persistent peek (M'aban) in web-data `gameState.peek`; agenda deck seeded
    when unlocking M'aban.
  - `combat.resolve_unit_variant` and `web_player_units`: on rank tie, variant from `faction.units` wins
    (previously registry order gave Iconoclast PoK instead of TE).
  - Dacxive Animators: only with surviving ground force on planet (F_naalu matriarch 3).
- UI: "0" token marker on strategy card tile (`StrategyCard zeroToken`, `gameState.initiativeZero`), M'aban peek
  in hand preview lines (`BottomHandDock`), The Oracle hero effect (`heroBoardFx.ts`). Offers
  (Foresight, Z'eu, The Oracle, Iconoclast) and Mindsieve (Available now) go through shared windows.
- `F_naalu` rulings with tests (`tests/factions/test_naalu.py`, `test_flows_naalu.py` scenarios); F_muaat umbat 4/4.1
  → `na` (active M'aban does not produce). Gap: Neuroglaive with Mahact (`requires faction:mahact`).
- `⚠️ ASSUMPTION`s to confirm: Foresight takes ground forces from space automatically (mechs, then infantry,
  up to capacity); Gift of Prescience is played in a window after all strategy cards are picked, before speaker clicks "Next phase".

## 2026-11-22 — Naalu: Choice + "Auto" in Foresight, End-of-Strategy-Phase Pause

- User decision: every player choice = manual choice + "Auto" (also `CLAUDE.md`). Generally:
  `oi.number(..., auto=N)` — UI pre-fills Auto value and shows "Auto" button (`DecisionField`), omitted field
  = Auto (`validate_params`, `single_params`, bot).
- Foresight: player chooses how many mechs and infantry from space to carry (`carry_mech` / `carry_infantry` fields,
  Auto = up to capacity, mechs first — `⚠️ ASSUMPTION`); over capacity = 422, uncarried stay behind.
- Protective pause (54.10) in "end of strategy phase" window: `PAUSE_POINTS` (`PHASE/END`), eligible = players with a PN
  in hand excluding the owner of the faction note reacting in the window (`promissory_play.faction_note_owners`, explicit);
  `turn_flow.next_phase` from strategy phase waits for pause end.
- Fix: offers from placing a token during primary (Diplomacy + Z'eu) do not open their own window — they wait
  in the secondary window (fuzz seed 11 stalled).
- QA: pytest (factions, engine, reaction pause, strategy) ✓, ruff/mypy ✓, tsc ✓, eslint ✓, vitest (offers, api) ✓.
  Did not run full pytest on this tree: parallel session has uncommitted changes (Vuil'raith,
  `transaction.py` — red `test_pride_of_kenara_w_gravity_rift_rzut` is its change). Build/e2e skipped
  (no new frontend modules).

## 2026-11-22 — I1 Capture + B13 The Vuil'raith Cabal (RULES.md 61.5, 62.17)

- **I1 capture** (`core/capture.py`, central point): `PlayerState.captured_units` (ships/mechs by original
  owner, including own) and `captured_tokens` (fighter/infantry tokens from pool). Owner's reserve excludes
  captured (`production.reinforcements_left`), destruction → PERMIT `capture.destroyed` hook
  (`unit_ops.remove_units`), from reserve / from board without destruction, return (box on elimination), dock blockade
  returns ships immediately (`step_settle` → `capture.release_blockaded`), forbid capturing from blockader,
  transaction returns ships/mechs only to owner (`TransactionSide.captured_units`). View: `nombox`
  in web-data (`Nombox` component, now with full faction name). Feed: `ability_notes` "captured …".
- **Unit-sourced anomalies** (`core/map_anomalies.py`, `HexGrid.sync_extra_anomalies`): Dimensional Tear makes system
  a gravity rift for everyone; Cabal's own ships do not roll (`movement.rift_roll_nodes`, `rolls_at`).
  "Up to N fighters" capacity from dock ability text (data lacks `capacityValue`).
- **Cabal** (`hooks/factions/cabal.py`): Devour, The Terror Between (also after destruction this round),
  Reanimator, Amalgamation (`captured` production field, chips in `ProductionOverlay`), Riftmeld (skip
  `captured:<owner>`, section in `TechnologyOverlay`), Vortex, The Stillness of Stars (offer after replenishing
  commodities; swap without "gain"), That Which Molds Flesh (2 fighters/infantry ignoring limit, unlock 3 rifts),
  Dimensional Anchor (roll once per ship, excess capacity via CAPACITY window also captured), Crucible
  (no rolls, single extra +1, also with Nav Suite), Al'raith Ix Ianovar (Fracture without roll, move
  2 ingresses to rifts — Available now, +1 move from The Fracture).
- Fix: "after replenishes" offers during Trade primary wait in secondary window
  (`economy.replenish_commodities(open_window=False)`) — previously blocked opening the secondary window.
- Rulings: `F_vuilraith` + `R_capture` (removed from debt, limit 211) with tests (`tests/test_capture.py`,
  `tests/factions/test_cabal.py`, `test_flows_cabal.py` scenarios). Statuses: Amalgamation 5 & Stillness 4 (`gap`),
  Anchor 5 / R_capture notes 4 (`requires` Nekro/Yssaril).
- `⚠️` For user decision: Trade primary collects choices from players with free secondary BEFORE primary, so agent chooses
  after them (ruling Stillness 4); ingress-move window lasts until the end of the turn the breakthrough entered play.
- Transaction table: "Captured units" section (stepper per type, silhouette in partner color, only partner's
  ships/mechs from Nombox, only when components are allowed), summary "Returns captured …"; API scenario
  `test_transakcja_zwraca_przechwycony_statek`. By the way: missing `hint` in `DecisionFields.test.tsx` (tsc).

## 2026-11-23 — Cabal: Ingress Move Right After Fracture Enters

- User decision: Al'raith Ix Ianovar moves ingresses immediately after they are placed per rules, not
  in an "Available now" window until end of turn. New event `GameEvent.FRACTURE_INGRESS_PLACED`
  (`fracture.announce_ingress_placed`: after `_enter` without choices and after last `choose_ingress`); Cabal
  hook = offer (`ingress_offer`). Fracture already in play → offer immediately when breakthrough enters.
- QA: pytest (Cabal, Fracture/expeditions, events, triggers) ✓, ruff/mypy ✓.

## 2026-11-23 — Faction The Titans of Ul (B14, RULES.md 62.18) + Faction Tokens on Map (I2, 61.6)

- **Faction tokens** (`core/faction_tokens.py`, `SystemState.faction_tokens = {zone: {kind: owner}}`):
  sleeper ×5 (AsyncTI4), place / move / remove, return on tile swap (Nova Seed) and planet destruction.
  View: `sleeper` token on planet in web-data, `sleeperTokensReinf` in player panel, feed
  `faction_token` / `faction_token_removed`.
- **Titans** (`hooks/factions/titans.py`): Terragenesis (offer after exploration: pool or move – click
  planet), Awaken (snapshot of tokens & PDS on `SYSTEM_ACTIVATED/WHEN`; per token PDS / mech+infantry / leave; PDS
  from board when reserve empty; rival planet with no ground forces captured immediately, with forces – combat in Invasion),
  Coalescence (base rule), Hel-Titan as structure & ground force (FORBID `units.structure_ground_forces`:
  defenders, contested planets, hold after combat, shieldless bombardment target; no SCD hits), Ouranos (DEPLOY
  from snapshot), Hecatoncheires ("mech instead of PDS" in `place_structure` – Construction & Awaken), Tellurian
  (use in window: cancels 1 hit of combat / Space Cannon / bombardment for any player), Tungstantus
  (unlock 5 structures; toggle in `ProductionOverlay`, TG before payment), Geoform (attachment `titanshero`:
  +3/+3, SPACE CANNON 5×3 for Elysium controller; card on planet blocks reuse), Terraform
  (attachment `titanspn` +1/+1 and 3 traits – `planet_stats.traits`, `exploration.planet_traits(state=…)`, objectives;
  PN does not return and does not sit in play area), Slumberstate sentence 3 (request → controller decision Allow/Refuse).
- Shared changes: strategy cards (Construction, Warfare) produce only with docks (`ProductionGrant.producer_types`,
  F_ul hel-titan 1); `invasion.cancel_bombardment_hits`; SPACE CANNON from attachments (`space_cannon`);
  attachments from PNs and leaders (`planet_stats._card_attachment`); `titanshero` board hero effect.
- `F_ul` rulings (`titans → F_ul` map) with tests (`test_titans.py`, `test_flows_titans.py` scenarios); Farran
  + Hel-Titan (F_letnev 2.1) has a test. `gap` statuses: breakthrough sentences 1–2 (coexist, block I4), Hel-Titan 3
  (Decoy Operation / Transit Diodes).
- `⚠️ ASSUMPTION`s (to confirm): Awaken – each token separately, "Auto" = PDS; Tungstantus – "Auto" = enabled;
  Slumberstate – request anytime in action phase, no action; Tellurian does not cancel AFB (no assign step).


## Board Hero Effects — Review & New Faction Marks (RULES.md 64.4)

- Ul the Progenitor (Titans) had no scene or effect: Geoform does not purge the card (attaches it to Elysium),
  so the feed lacked `leader purged`. `momentsForEntry` now recognizes `attached` with a hero card
  (actor = `actor_id`, planet in `planets`); `planet` effect target = Elysium system. Backend test in
  `tests/test_activity.py`, frontend tests in `keyMoments.test.ts`.
- Cabal (Dimensional Anchor): vortex starts from systems with Cabal docks (Dimensional Tear, `docks` target), tentacles reach
  to NEIGHBORING systems (`neighborTiles` — hex grid, visualization only) and pull in their ships.
- Each hero has its own mark (`layers/HeroFxMarks.tsx` + `.module.css`): Letnev reticles, Jol-Nar circuits,
  Mentak boarding hooks, Argent double helix, Yin clone pods, L1Z1X materialization grid + glitch,
  Saar Armageddon Relay wave from docks, Naalu psionic eye + mist, Titans magma rifts / titan core in plates /
  3× SPACE CANNON, Cabal Event Horizon. Arborec got spores, Sol pillar core, Xxcha shield grid.
- New in recipe: `quake` (board shake via `translate` on tile container — doesn't break zoom; disabled under
  prefers-reduced-motion), `static` and `mist` transitions, sounds for all heroes.
- QA: vitest (KeyMoments, map), tsc app, eslint, pytest `test_activity`; animation screenshots (puppeteer) inspected.

## Hero Effects: Action Location from Feed (`area` facts, RULES.md 64.4)

- Audit of all 18 heroes (Arborec … Titans): ACTION effects targeted too broadly (e.g. Sol lit up
  every system with units). `core/activity.py` now appends `area` facts to hero-use entries (purge or
  card attach): position + player unit `gain`/`loss` or `token_removed`; feed does not print them
  (`describeActivity`), `momentsForEntry` maps them into the moment (`areas`, `self` = hero).
- Recipe can use `area` (fallback remains `target`): Sol — systems where its tokens vanished (light pillar
  lifts token); Saar — system where rivals lost units; Argent / L1Z1X — fleet destination systems;
  Yin / Xxcha / Arborec — systems with new units. No board impact (Jol-Nar, Naaz, Naalu, Winnu) unchanged;
  reactions (Hacan, Mentak, Sardakk, Muaat) — active system / Nova Seed.
- Tests: `tests/test_activity.py` (`area` facts), `tests/factions/test_hero_area_feed.py` (Sol/Saar/L1Z1X via
  API), vitest `keyMoments`/`heroBoardFx`; Sol effect screenshot inspected.

## 2026-11-23 — AFB via Assign Step (Shields Holding, Tellurian) + "Auto" in List Choices

- User decision: regular AFB hits are assigned by the fighter owner in an ASSIGN step (like Waylay;
  `afb_assign`, required target `hit_targets` = fighters, choice + "Auto"), so before assignment they can be cancelled by
  Shields Holding (C_action_cards 4.1) and Tellurian (RULES.md 39 W4, 53, 62.18).
- Shields Holding: C_action_cards rulings audit (1–5, 4.1) with tests, card removed from debt (limit 210).
  Bug fixed: a player could play a second Shields Holding on the same roll (trace in `combat.effects`).
- `oi.choice(auto=...)`: "Auto" button in list choices (`DecisionFields`), omitted field = Auto option.
  Titans: Awaken = PDS, token source = pool, Tellurian = hit on own units, Ouranos = first PDS,
  Terraform = planet with highest total value, Slumberstate: controller "Auto" = refuse.
- QA: full pytest ✓, ruff/mypy ✓, tsc/eslint/vitest (offers, ActivityPanel) ✓, e2e 8/8 ✓.


## Hero Effects: Hacan, Sardakk, Winnu, Naaz-Rokha + Fade-Out Fix (RULES.md 64.4)

- Hacan (Sanction of the Quieron): trade routes converge on the system, caravans, rain of trade goods,
  and spinning Quieron coin. Sardakk (Brood Swarm): N'orr swarm dives, strikes, three slashes, and glowing
  wound + quake. Winnu (Sins of the Father, `crown` mark): crown stamps Mecatol Rex, laurel and rays of
  authority across the board. Naaz-Rokha (Forge Legend, `forge` mark): runic rings align, forge sparks,
  relic crystal, and two strategy cards. `seal` mark removed (no hero shares it).
- Bug: `fadeLate` attached as a second animation overrode `opacity` of the entrance animation — elements (Arborec
  leaves, titan plates, Naalu eye, coin…) were visible before their moment. Removed; everything already fades
  with its layer (`fxLife`).
- QA: tsc app, eslint, vitest (map, KeyMoments); frame screenshots inspected.

## Fix: Multi-Player Simultaneous Rolls (Dimensional Anchor — Cabal Hero)

- Bug: `state.table_roll` held ONE roll, while Dimensional Anchor records a roll separately for each
  opponent — each overwrote the previous one, so UI animated dice only for the last player (engine rolled
  correctly, once per ship). Now `dice.record_table_roll` also appends to `GameState.table_rolls`
  (last 12, web: `tableRolls`), and `TableRollWatcher` replays all new rolls sequentially
  (`domains/dice/tableRolls.ts`), each in the roller's color. Applies to any multi-roll effect.
- Test: `test_bohater_rzuty_kazdego_przeciwnika_widoczne`, `tableRolls.test.ts`.
- QA: full pytest, ruff, mypy (changed), tsc app, eslint, vitest `domains/dice`. No build/e2e.

## Fix: Yin Invasion Window (Quantum Dissemination) After Animation & Without Empty Invasion

- Bug: component invasion window opened immediately, before the scene and hero board effect, even when
  no enemy troops were present (no combat, SCD, bombardment).
- `InvasionOverlay`: window waits for end of moments queue (`useHeroFx.stageBusy`); component invasion without
  contested planets runs Commit/Establish automatically (attacker's client, one call per step). When a step
  fails (e.g. exploration), window stays with message. Backend unchanged (post-commit reactions).
- QA: tsc app, eslint, vitest `domains/invasion`. No unit test, no build/e2e.

## Decision Windows: Tile Payment + Leadership Without 3-Influence Lock, with "Auto" (Plan U2, partial)

- `docs/PLAN_OKNA_DECYZJI.md`: added user decisions (P1 payment tiles, P2 chip grid/drag instead of
  lists, "+N" queue, U1→U6 order).
- `PaymentPicker` (PromptParts): planets as `Tile` from `DecisionTiles` (as in offers) instead of planet cards —
  applies to all payment windows (Leadership, technologies, status, Custodians, expeditions).
- Leadership: removed pointless-spend lock (pay any amount, remainder info), "Auto"
  via `target` (rules/R30.md 30.7, `⚠️ ASSUMPTION`). Backend unchanged (`paid // 3`).
- QA: tsc app, eslint (changed), vitest domains technology/invasion/game-shell/thunders-edge/offers.
  No Leadership test, no build/e2e, no visual verification.

## Decision Windows — U1: Shared `DecisionFrame` + Single `ComponentUseModal`

- `shared/ui/DecisionFrame`: header (kind badge, title = component name/chip + ⓘ, legible
  "Required", "+N more"), full text in NORMAL color (collapsible >420 chars), fields, notices (notes/warnings),
  footer [Never ask] [Skip Esc] [action Enter]; Enter/Esc shortcuts in one place; `embedded` variant in window.
  Styling moved from `OffersDock.module.css` (only token pools remain there).
- `OfferDock` (OffersModal) = `DecisionFrame` (behavior unchanged: Never ask, Skip, Enter/Esc, Transit Diodes, pools).
- `ComponentUseModal` replaces the body of 4 modals: `ActionCardPlayModal` (card/relic/frontier/PN),
  `TechnologyUseModal`, `LegendaryUseModal`, `FactionComponentUseModal` — thin wrappers; now also
  with chip/ⓘ, full text, Enter/Esc, unified "Cancel", no form for exhausted/blocked
  (warning instead of fields), load error with Cancel button.
- Strategy card windows: no second AppModal title ("Strategic action" / "Strategy Card — secondary
  ability") when the card view has its own header (PromptShell). Full rewiring of PromptShell to the frame — later.
- Out of scope for U1 (deferred to U2–U5): `Stepper`/`Payment`, decision zone, duplicate info, "Follow"
  inactive without influence.
- QA: tsc app, eslint, vitest (game-shell, offers, strategy, shared; new `DecisionFrame.test.tsx`),
  `npm run build`, `npm run e2e` (8/8). No in-game visual verification.

## Decision Windows — U2: One `Stepper`, One Payment (`PaymentTiles`), Shared `AutoButton`

- `shared/ui/Stepper` replaces 5 copies (PromptParts, DecisionTiles, TradingTable, RemovalWindowModal,
  `CommandPools` controls); aria: "Less/More <label>"; `bare` variant (buttons only in a row with own label).
- `domains/offers/PaymentTiles`: one payment widget (planet tiles + TG + "Paid X / Y" bar + Auto). Adapters:
  `PaymentField` (DecisionFields) and `PaymentPicker` (Leadership, technologies, status, Custodians, expeditions).
- `shared/ui/AutoButton`: one "Auto" beside the field (subtle); rewired: numeric/choice fields, payment, token pools,
  unit removal, combat (BattleCenter), assignment (AssignPanel), Production, Technology. Intentionally skipped:
  `ExtraDicePicker` (Auto is one of mutually exclusive options there). New "Auto": Leadership/Warfare
  (token allocation), Predictive Intelligence, "Spend…" objectives (pools, mixed) — `⚠️ ASSUMPTION`s in R30.md/R41.md.
- `CommandPools` (+`onAuto`, `current`) also used by `PoolDistributor` (Leadership, Warfare) and status (Auto moved
  from separate button into pools, no orange "secondary").
- Out of scope: Stepper in Invasion/Production/Technology/SpaceCannon/Politics (other widgets: reorder, dice) — for U-later.
- QA: tsc app, eslint (changed), vitest (offers, strategy, game-shell, map, technology, invasion, production, battle, shared;
  new `Stepper.test.tsx`), `npm run build`. `npm run e2e` (8/8). No visual verification.

## Decision Windows — U3: Decision Zone & "+N" Queue (Less Clutter)

- `hooks/useDecisionZone.ts`: DOM markers `data-decision-zone` (every decision window: `DecisionFrame`) and
  `data-phase-window` (phase window: status panel, Council, strategy cards `PromptShell`, secondary "Follow" window);
  `useDomPresence`, `decisionZoneOverlaps`.
- "Decisions" center when a phase window is open is not a second window: collapses to a "+N" counter pill
  (offers + "Available now" + table invites; required decision = warning color). Click shows them
  temporarily; returns automatically when phase window closes. "Ready" markers/timing windows are not counted (Z1, Z2).
- Hand dock (`useDockCovered`): collapses when a decision window enters the EXPANDED dock area (remembered
  height - no flicker) or on fullscreen window; temporary expand works as before.
- Map tooltips (`MapTooltipPositioner`) hide when overlapping a decision window (Z10).
- Reaction window banner moves to the top when a decision window is open (below tabs; in Council - on title bar),
  `NotificationArea` toasts slide beneath it (Z2).
- Not done (kept): offer as "next step" INSIDE phase window ("+N" pill is used); plan item 6
  (clearer "don't use", e.g. hero "do not place").
- QA: tsc app, eslint (changed), vitest (offers, hooks, game-shell, agenda, strategy, shared, map; new
  `useDecisionZone.test.tsx`), `npm run build`, `npm run e2e` (8/8). No in-game visual verification.

## Decision Windows — U4: Removing Duplicate Info

- Respondent: timing window side panel (`GameStatePanel`/`WindowSection`) shows only the queue
  ("Remaining in queue"), without "Responding" banner; "Your call" window does not repeat "Remaining after you" (Z8).
- Agenda: "N votes available" removed from outcomes (votes only in Senate seat list); "Agenda N of M" counter
  only in Council header (Z3). Tie = click winning outcome on podium (speaker; no separate button
  list; non-tied outcomes dimmed). `manual` agenda unchanged (description + "Resolve as chosen").
- Option tiles: no native `title` (description via ⓘ). Offer: field label equal to frame title is not
  repeated (`FrameTitleContext` + `FieldHead`; set in `OffersModal`) (Z12).
- Component action: list without hand action cards (played by dragging), new intro, ⓘ with description on
  leader/technology/relic/breakthrough (Z9).
- QA: tsc app, eslint (changed), vitest (offers, agenda, game-shell). No in-game visual verification.

## Decision Windows — U5: Readability & Dead Ends (+ Plan Item 6: Clear "Skip / Don't Do")

- Secondary ("Follow"): cost as a separate clear line ("Cost: …", also free ones with source name); engine
  provides `follow_blocked` in secondary options (Leadership: < 3 influence or empty reserve, R30.md 30.7) -
  "Follow" disabled with reason (Z7). "free" respondent is not blocked.
- Leadership: `base_gain` and `per_token` from engine in texts (no constant 3).
- Faction/leader ability texts: sentences with period, window with colon
  ("…infantry. At the start of the status phase: Place…") - `faction_components._sentence/_windowed` (Z12).
- "Your move / Waiting for" bar: reasons by phase (`core/actor.awaiting`: `score`, `redistribute`, `vote`
  instead of "take a turn" in status/agenda). "What now?" coach in host test mode = same as local (player's
  turn, not "Watch the map"). Feed/notifications: full faction name instead of "Player p1" (Z13).
- Item 6: decline options ("Do not place", "Decline …", "- none -") as a separate row after "or" - tile with ⊘
  and dashed border, selected says "Chosen - click again to undo" (`isDeclineOption`, `DeclineRow`; regular
  and map fields). Offers: "Don't use" instead of "Skip".
- QA: pytest (full, -n auto), ruff, mypy (changed), tsc app, eslint (changed), vitest (domains, shared,
  hooks), `npm run build`, `npm run e2e`. No in-game visual verification.

## Decision Windows — U6: Planet Selection Only on Map, No Dropdowns

- Agenda "Elect Planet" (`domains/agenda/AgendaMapPick.tsx`): "Choose a planet on the map" button on podium
  collapses Council to bar; outcome planets glow (tie: only tied ones); click returns to Council with selection (tie =
  speaker resolution). Outcome list for planets = vote preview only.
- `DecisionFields`: no `Select`/`MultiSelect` - above 18 options, scrollable tile grid with helper
  filter (decision P2).
- U1–U4 review: no bugs to fix. Note: map tooltip hidden over decision window returns on cursor move.


## Tactical Action Panel: Undo Activation, Wrap-Around Counter, Single Invasion

- "Undo last move" with no moves made undoes system activation ("Undo activation"; `/tactical/undo-move` accepts
  `tactical:activate:*` label when no window is active) — RULES.md 44.1a; web-data `tacticalMoved`.
- `RouteUnitChip` (movement, map route, movement offers): click +1, at full (2/2) wraps to 0; right-click −1 unchanged.
- Invasion once per action (RULES.md 40.1 I9): `GameState.invasion_resolved`, web-data `invasionResolved`; after closing,
  panel does not show "Start invasion" again.
- Tests: `test_undo_move.py`, `test_invasion.py`, `RouteUnitChip.test.tsx`.


## "Component" Button: Unavailable Items Greyed, ⓘ Description for Every Item

- `collectComponentActions` carries `unavailable` from web-data: leader exhausted/locked/purged, tech & relic
  exhausted (`exhaustedTechs`/`exhaustedRelics`), breakthrough & legendary planet exhausted — row greyed with reason.
- "Component" button greyed when nothing can be played (list, relic fragments, non-action tech abilities);
  fragment & tech-ability options fetched when button is active.
- ⓘ on every row: new kinds `ability` (faction ability, `AbilityDetailsCard`) and `legendary`
  (`PlanetAbilityDetailsCard`) in `ComponentInfo` + `hintFor`; also on technology abilities.
- Test: `componentActions.test.ts`.


## Action Cards: Audit + Agenda Deck Knowledge (Insider Information) + Hidden Decks

- Audit of 140 action cards (script on 6-player state): every card has an effect; forms reviewed for map/overlay/Auto.
- Agenda deck knowledge (RULES.md 53.5.a1): `agenda_peek` + new `agenda_peek_bottom` in `core/card_draw.py` —
  persists until deck changes (does not vanish after agenda phase); drawing an agenda removes it from knowledge, Politics gives owner
  new top/bottom and clears others' knowledge, reshuffle clears for everyone. `/hand` → `agendaPeekBottom`.
- UI: `KnownCards` in hand dock instead of text lines — `KnownAgenda` chips ("Top 1: …", "Bottom: …", card on
  click), secret objectives from Extreme Duress as `ScoredSecret`, PNs from M'aban as `PromissoryNote`, player = faction icon.
- Hidden decks: `browseDecks` setting (Settings → Admin / testing, off by default) — without it, clicking cardback
  shows nothing; discard and purge piles remain public.
- Brilliance: planet by map click (`planet`) or player (`player`), exactly one.
- "Auto" in card numeric fields (RULES.md 53.9): Bribery, Unstable Planet, Shields Holding, Leadership Rider,
  Manipulate Investments.
- Tests: `test_reactions_agenda.py` (knowledge), `test_strategy_diplomacy_politics_imperial.py`, `test_action_cards_economy.py`,
  `KnownCards.test.ts`.


## "AAA" Main Menu + Lobby: Match Setup Method (Accounts Plan)

- New menu `pages/MainMenu.tsx` (+css): left column on dark glass (two-line logo, captioned navigation,
  primary action in TI4 gradient), "Continue" when a current match exists, "Recent games" panel (saves, one-click
  load), "Guest" profile in corner (login disabled with reason), footer with server status.
  Button labels unchanged (E2E). "Game history" = "Soon" (requires accounts).
- Shared save logic: `useLoadSave`, `describeSave`, `formatSavePhase` in `LobbyScreens.tsx` (Load game modal + menu).
- Lobby (`Step_Players`): "Setup method" section — Standard active; Full random / Milty Draft / Franken Draft greyed
  ("Soon"), no logic.
- Removed dead styles of old menu/wizard from `StartScreen.module.css`. `.env` in root `.gitignore`.
- Accounts, history, and drafts plan + Supabase guide: `docs/PLAN_KONTA_LOBBY.md`.
- QA: tsc, eslint (changed), vitest `domains/network` + `domains/setup`, Playwright screenshots (menu 1600/1920, lobby).


## Hidden Decks in Board Search Too

- Without `browseDecks` setting, search does not open deck lists (agendas, objectives, relics, exploration, action cards)
  and does not index cards from hidden decks — finds only cards from public piles (discards, purge), so it never leaks
  what's in a deck or someone's hand. `buildSearchIndex(gameData, { browseDecks })`, `CardbackModal` ignores search request.
- Test: `searchIndexDecks.test.ts`.


## Main Menu: Single-Line Logo, "Components" Library, Organized Settings

- "Custodian Engine" logo on one line (sized in `cqi` of brand column, no wrapping).
- New menu item "Components" → `domains/library/ComponentsLibrary.tsx`: factions (list by expansion +
  `FactionSummary`, Keleres variant switcher), strategy cards (`StrategyCardDetailsCard`), general technologies
  (`GeneralTechCatalog` with `playerData=[]`, no owner hints), base units (`UnitDetailsCard`),
  and all decks (`CardPoolBrowser`: action, agenda, objectives I/II, secrets, relics, exploration, generic PNs)
  with search. New `genericPromissoryPool()` (`<color>` marker → "[color]") + test.
- Settings: tabs Game (clock, reaction windows) / Variants (deck modules) / Display (map + player cards) / Sound /
  Testing (Fast mode + God-Mode). Shorter, crisper descriptions. Removed dead store fields: `showControlLayer`,
  `animateEventPreviews` (+ `toggleShowControlLayer`). References to old names (tooltips, comments) fixed.


## Lobby: Who Sits Where, Player Numbers; Map String with Pre-placed Homes

- Map string: token resolved via data aliases (`8` = `08`, `96` = `96a`, `nekro`) — `core/map_string.resolve_tile_id`.
  Previously `8`/`96` vanished silently (holes in map). Unknown tile = 422 with list (`/game/new`, `/map/load`).
- Pre-made map with homes (e.g. Milty): `map_seats` detects home faction at each seat (also `51` Creuss / `118` Crimson);
  `GET /map/seats` for wizard. Player on a home gets its faction by default (wizard `applySeatFactions`, backend for
  player without `faction_id`); swapping seats moves the faction; vacated home returns to empty slot. RULES 2a.
- Table seating order clockwise from Player 1 (`home_slots.seating_by_seats`), not by player number. RULES 24.
- "Players & map" step: seat board (`SeatBoard`, home icons from map), "Seat N" chip on card, ◀ ▶ arrows
  changing player number. In networked lobby, swap goes through server together with owner (`PATCH /lobby/draft
  {"swap": [i, j]}`, host only; `setupSync.swapPlayers`). Unknown tiles block "Choose factions".
- Tests: `tests/test_map_string_seats.py`, `test_network_game.py::test_host_swaps_player_numbers_with_owners`,
  `useSetupStore.test.ts` (applySeatFactions, swapPlayers).

## Faster Frontend Dev & Tests

- `vite.config.ts`: React Compiler (Babel) only in `vite build` (force in dev: `REACT_COMPILER=1`). In Vitest
  transform ~10 s → ~1.4 s on sample, full suite of 357 tests ~20 s. `server.warmup` compiles the tree from `main.tsx`
  right after Vite starts, so first browser visit doesn't wait.
- Players over ZeroTier: Vite dev server serves ~900 separate modules (each = network round-trip). For networked
  play, better use `npm run build` + `uv run python packaging/launcher.py` (single server, `src/api/bundle.py`, few files).

## Slots for System Lore

- `frontend/src/entities/data/systems.ts`: every named system (except hyperlanes and empty tile) has a
  `"flavourText": ""` field right under `"name"` — 435 slots for manual fill-in (anomalies, empty systems, planet
  systems). Type `TileData.flavourText`.
- `SystemDossier` (`Flavour`): non-empty system lore renders above planet descriptions; empty is skipped.

## Planet Lore from AsyncTI4 (PR #6213)

- Upstream AsyncTI4 PR #6213 (merged 2026-11-20) added/fixed planet `flavourText`. Synced 92 files
  `assets/planets/*.json` from active sources (base, pok, codex*, thunders_edge) + same fields in
  `frontend/src/entities/data/planets.ts`: +40 new descriptions (incl. New Terra and rest of Thunder's Edge), typo
  fixes, swapped Darien/Archon Tau/Archon Ren lore, names "Ba'kal" and "Vira-Pics III", periods in
  `legendaryAbilityText` (Primor, Hope's End, Mirage, Mr Te, Thunder's Edge, Custodia Vigilia), alias dedup.
- Custom Keleres `*k` planet texts (commit 4145b436) preserved — upstream gave them copies of originals' lore.
- Rest of PR (action/agenda/tech/leader card texts, faction lore, `asteroid.json`) NOT synced.

## Board: Irregular Tiles, Fracture/Mallice, Effects Tray, "Player color" Theme

- Spiral tiles (Creuss 51, Crimson 118, Mallice 82a/82b, Kwon c10, Ethan c11; art ~416x386): hit-target and
  all highlights follow shape outline (`entities/geometry/tileOutline.ts`, outlines from alpha channel:
  `scripts/gen_tile_outlines.py` → `tileOutlines.generated.ts`), not 345x299 hex. Hover points for
  gamma/delta/epsilon wormholes measured from art (`WormholeBlockedLayer`), "leads to" lines from shape center.
- Fracture adjoins Player 1's slot (bump 400 = adjacent grid cells), Mallice with Fracture left of frac1,
  no shape overlap (`tilePositioning.test.ts`).
- System click menu: "Name (103)" (`systemDisplayName` in `entities/lookup/systems.ts`).
- Effects tray (RULES.md 54) is a hex on the board grid in a free cell between players 2 and 3 (6p: 407), effect
  tokens 2x3; more effects = next hexes to the right. Occupied cell => past right edge of board.
- "Player color" theme (default): muted page accent in my player's color (`usePlayerAccent` →
  `--player-accent-rgb`, `styles/playercolortheme.css`); game signals unchanged. Other themes in bar dots.
  Previously saved browser theme choice takes precedence.

## Chronicle of the Empire, Cleaner Feed, New Achievements

- Quill button (`domains/chronicle/ChronicleButton`) beside Events in `FloatingMapToolbar`: golden "breath", quill
  writing, flash and counter on new major entries (`prefers-reduced-motion` disables animations). Opens book
  `ChronicleBook` (ds `Modal`, chapter = round, round chips, arrows, "All events", "Show all facts").
- `buildChronicle.ts`: pure function Activity feed → chapters. Entry = story (`chronicleLore.ts`, variant pools
  chosen deterministically, faction epithets) + motto from planet lore (`flavourText`) + "What exactly happened"
  (dry facts). Battles described by existing `describeBattle` (`domains/lore/battleLore.ts`) — same text as in outcome
  window. Events: battles, conquest / colony / home-planet fall, objectives, laws and agendas, relics, leaders,
  heroes, Custodians claim, elimination, Fracture, Nova Seed, pacts; minor ones (tech, pacts, strategy cards,
  exploration, Speaker) hidden in "Major events". Rewound (`seq > current_seq`) and God-Mode skipped.
- Feed: new `moved` (fleet move: type, count, dest) and `landed` (planet landing) facts — movement cancelled out in
  unit totals (`core/activity.py::_movement_facts`); headers "moved N ships from A to B", "landed N ground forces
  on X"; strategy card secondary with card name (initiative from window); `update` entry named after first effect.
- Achievements (`core/chronicle_awards.py`): First Blood, Home Sweet Home, Sacker of Capitals, Blitzkrieg,
  The Pacifist, A Throne Contested (leader changes), Photo Finish. Fix: "Mutual Annihilation" no longer shows
  battles without losses. Icons in `AchievementCard.tsx`.
- `⚠️ ASSUMPTION`s: faction epithets (`FACTION_EPITHET`) and text pools are my drafts — for user to refine/expand.
  Chronicle has no own endpoint (reads feed), so requires no backend restart beyond new facts.


## Lore: Card Flavour Slots, Faction Voice Lines, Battle Narration & History

PRESENTATION layer (nothing in rules). User writes texts themselves; I provided slots + battle description generator.
- **Card lore slots** (`frontend/src/entities/lore/cardLore.ts`, template from `scripts/gen_lore_template.py` — adds
  missing cards from active sources and NEVER touches filled texts): leaders, agendas, PNs, public/secret objectives,
  technologies, breakthroughs, faction abilities (~490 empty slots). Rendered by `shared/ui/DetailsCard/CardLore.tsx` (italic
  at bottom of details card, empty = nothing). Action cards, relics, and exploration have AsyncTI4 flavour (`flavorText`) and already
  show it; **leaders in AsyncTI4 have no flavour** (only 2 from homebrew `wftv`), agendas/PNs/objectives/tech/breakthroughs don't either.
- **Faction voice lines**: `entities/lore/factionVoiceLines.ts` (empty arrays per faction, filled by user) →
  `domains/chat/FactionVoice.tsx`: speech-bubble button by own player's strategy cards (panel header),
  list of lines as large chips, pick = public chat message with `voice` flag (`core/chat.py`, `POST /chat/send`).
  9 s bubble above sender's area for everyone + italic in chat. `⚠️ ASSUMPTION`: line content is not validated
  server-side (only length limit and no whisper); new `voice` field in chat response — backend restart.
- **Battle narration** (`domains/lore/battleLore.ts`): classes Crushing / Decisive / Hard-fought / Pyrrhic / Skirmish /
  Annihilation / Standoff × space/ground, ~100 templates substituting names, losses, and unit types (full names);
  variant chosen by deterministic seed from battle data. Shown on outcome screen (`BattleSummary`) and in history.
  `⚠️ ASSUMPTION`: class thresholds (crushing = 0 own losses & ≥4 enemy etc.) in `classifyBattle`, with tests.
- **Battle history in system dossier**: `chronicle.battle_history` (+ `lost_types` in `record_battle`) → `battleHistory`
  in web-data → `SystemDossier/SystemBattleHistory.tsx` (newest on top). Backend restart (new field).

## AsyncTI4 Asset Sync (2026-11-23, master 9ff908b)
- `assets/data` (base/pok/codex/thunders_edge sources only): overwrote fields differing from upstream (typo and text fixes,
  names: The Sorrow, Ragh's Call, Specialized Compounds, Yin Spinner, Scholarate Founder) and added missing: leader `flavourText`,
  faction `lore`/`quotes`/`information`/`complexity`/`wikiURL`. Skipped: image fields, `theodisi.json`, `tokens/base.json`
  (`wormholeIconMerge`), `border_anomalies` (one-way adjacency rules — engine lacks them).
- `frontend/src/entities/lore/cardLore.ts`: 97/103 leader lore from upstream. `scripts/sync_card_texts.py` refreshed frontend card texts.
- Tests: `@ruling` of agents/PNs shifted after sentence-split change (`;` instead of `:`), `abilities:fabrication#2` merged into `#1`.

## Lore Typography (Quotes and Flavour)

- `frontend/src/entities/lore/typography.ts`: `typeset` (curly quotes, `--`→`—`, `...`→`…`, non-breaking space before dash and after "a"/"I"),
  `quoted` (quote with `”` joined to last word via word joiner), `attribution` (`—` + nbsp + author). Test: `typography.test.ts`.
- Wired into `lookupCardLore`/`lookupLoreOr` (all card lore) and quotes: `FactionVoice` bubble, `FactionBackdrop`, `GameIntro`, `VictoryScreen`, `ChronicleBook`.
  Bubble quotes moved from CSS (`::before/::after`) into text.
- `text-wrap: pretty` in flavour styles (DetailsCard, agendas, PNs/objectives, hero, relic, system dossier, chronicle) — no orphan last words.
- Skipped: `clean`/`cleanFlavour` in `SystemDetailsCard`/`SystemDossier` remain (strip `*...*` also from `cardLore.ts` entries).

## Victory Screen: Podium, Hall of Honors, 20 New Achievements (2026-11-23)

- **Podium** (`domains/victory/Podium.tsx`): places 2 · 1 · 3 with faction portraits (`portraitCandidates`), sharp center
  and blurred sides, gold/silver/bronze pedestals. Click filters achievements to player. Scoreboard remains below podium.
- **Hall of honors** (`AchievementBoard` in `AchievementCard.tsx`): card grid instead of scrollable row, filters for
  all players (everyone sees theirs) and categories. Chronicle + stat awards in one board.
- **New achievements** (`core/chronicle_feats.py`, catalog `assets/config/achievements.json`): oathbreaker, vulture,
  kingmaker, saboteur, voice_of_council, senate_master, dissident, staller, silk_road, giant_slayer, last_stand,
  punching_bag, tactical_retreat, rain_of_fire, first_to_throne, mecatol_tourist, void_walker, card_shark, sun_forger,
  late_bloomer.
- **Chronicle log** (`core/chronicle_log.py`, new `GameChronicle` fields): agendas (`agenda_phase._resolve`), out-of-combat
  fire (Space Cannon, bombardment, Space Cannon Defense), and from state diff in `step_settle.settle_step(before=)`
  — same path for server and bot (`engine/actions.apply_and_settle`): passes, speaker, action cards, explorations,
  Mecatol, War Sun peak. Battles: `retreated`, `survivors`. God-Mode does not enter chronicle.
- `⚠️ ASSUMPTION`s (presentation, not rules): Oathbreaker = attacking main trade partner; Kingmaker = SftT held by
  winner or attacking runner-up in final round; Staller = last pass in round; Last Stand = 1 unit
  (no structures); Late Bloomer from 4+ players.
- Tests: `tests/test_chronicle_feats.py`, `AchievementBoard.test.tsx`. Full pytest, ruff, mypy, tsc, eslint, vitest OK.
  Skipped: `npm run build` (aborted — long), e2e. Backend restart (new chronicle fields).

## Battle Window: Separate Roll Per Side (Left/Right)
- `core/battle.roll_round(..., side=None)`: roll for ONE side; result waits in `ActiveCombat.side_rolls`, and once both
  sides have rolled the round proceeds as before (extra hits, hit assignment). `side=None` = both at once (bot, tests; RNG
  order unchanged). Neutral side rolls together with the other (nobody clicks it). Re-rolling same side = 422.
- API: `POST /tactical/battle/roll` accepts optional `{faction}` (actor must be that side); view has `sideRolls`.
- UI: Roll step is two halves (`RollSide`: attacker on left, defender on right) with own button, dice pool (hold),
  and result; "Last volley" also in two columns. "Auto" in Auto/Clear/Confirm row matches neighboring buttons
  (`AutoButton className`).
- `⚠️ ASSUMPTION`: physical 3D dice and shots fire after BOTH sides roll (animation reads from log entry);
  first side immediately sees its dice and hits in the panel. AFB still single button (rule: simultaneous).
- Tests: `tests/test_battle.py::test_sides_roll_separately_and_round_closes_after_both`. Skipped: build, e2e. Backend restart.

## Battle Window: Separate Dice & Shot Animation Per Side
- `useVolley` returns a LIST of volleys: one side's roll (`sideRolls`) immediately triggers its 3D dice and shots, independently of the other;
  the second side animates only its volley. Volleys can run simultaneously (both clicked at once). AFB/Ambush/bombardment entries
  still animate both sides together.
- COMBAT log entry has `early` (sides that rolled earlier separately) — UI does not replay their volley a second time,
  and effect hold (`battleHoldMs`) waits only for the second side.
- Tests: `test_sides_roll_separately_and_round_closes_after_both` (+`early`). Not visually checked in browser; skipped build, e2e. Backend restart.

## tirules2: aktualizacja zrzutu z upstreamu + przemapowanie rulingów (2026-11-24)
- `docs/rules_tirules/` odświeżone z github.com/dangothemango/tirules (HEAD `015e4a9`, 2026-11-22); 137/149 tematów
  zmienionych. `R_construction`/`R_warfare` (lokalne adaptacje TE) zachowane. Różnice: `rules_tirules/ZMIANY_2026-11-24.md`.
- `scripts/scrape_tirules.py`: pomija przypisy źródłowe `<sup>1,2</sup>` (ale nie `<sup>th</sup>`) i linki w nagłówkach h2.
- ID rulingów: 314 przepisanych na nowe numery (`@ruling`, `rulings_status.json`), 105 usuniętych (ruling zniknął lub zmienił
  znaczenie); wildcardy wariantów → sekcje `*-replaced-by-omega*`; dług 210 → 199.
- ⚠️ Strażnik `test_ruling_coverage.py` CZERWONY: 211 nowych rulingów bez testu + 93 testy, które straciły ruling (do przeglądu,
  np. Specialized Compounds odwrócony) — lista w `ZMIANY_2026-11-24.md`. Pominięte: pełny pytest, front.

## Rules Viewer: Wiki Component Links Open In-Game Cards, No Top Banner (2026-11-24)
- `domains/rules/componentLinks.ts`: fandom-wiki links in the tirules dump that name one component (URL text fragment
  `:~:text=`) resolve to official-source game data — abilities, techs, leaders (also hero ability names), PNs,
  breakthroughs, units, planets, relics, active action cards/agendas. Name prefix covers variants (Valefar Assimilator =
  X + Y); wiki section (`#Faction_Technologies`, `#Leaders`…) and page faction narrow ambiguous names.
- `ComponentLink` (MarkdownView `a`): dotted-underline link, click = `SmoothPopover` with `ComponentCard` /
  `UnitDetailsCard` (same cards as player panel). Page-only wiki links (expansion, whole faction) stay external.
- Coverage: every component wiki link in the dump resolves except 3 components missing from game data (Agnlan Oln,
  Trillossa Aun Mirik, Enervate) — guarded by `componentLinks.test.ts`.
- Attribution banner above the rules removed (user decision); credit is one muted line under the topic index.
  Notes alert translated to English. Topic body drops the dump's own `# Title` + `> Źródło:` blockquote
  and the generic opening `## Rules Reference` heading (`domains/rules/topicBody.ts`) — title was shown twice;
  dump files unchanged.
- QA: tsc (app), eslint rules domain, vitest `src/domains/rules`; checked in browser (F_nekro: 26 card links, 0 wiki
  links). Skipped: backend QA (frontend-only), build, e2e (rules page not part of game flow).

## Rulings Update Review: 93 Tests That Lost Their Ruling (2026-11-24)
- Reviewed every test listed in `rules_tirules/ZMIANY_2026-11-24.md` › "Testy, które straciły ruling" against the new
  tirules2 dump. Three engine behaviours contradicted the new rulings and were fixed:
  - Gravity rift: the same rift gives +1 move only once per ship, each exit still rolls (`movement_paths.rift_bonus`
    counts distinct rifts; R_gravity_rift notes/2, F_vuilraith dimensional-tear/2). Old test asserted +1 per exit.
  - Specialized Compounds: synergy pair now counts as one color — yellow planet pays for green tech and vice versa
    (`technology.specialty_payment_planets`; F_jol_nar specialized-compounds/1). Old test asserted the ban.
  - Black Market Forgery: playable with an empty relic deck (fragments purged, no relic; F_naaz_rokha bmf/1).
- Remaining tests: behaviour still correct; re-tagged to the current source (general R_/C_ rulings, card-text clauses,
  renumbered faction rulings). Removed wrong auto-remap tags (Self-Assembly test carried a Psychoarchaeology ID; Milor
  test pointed at the original card — asset text is ΩΩ). Uncovered rulings in `test_ruling_coverage` 211 → 202.
- QA: affected suites (factions, rulings_general, exploration — 1209 passed), ruff, mypy (changed files).
  `test_ruling_coverage` still red (pre-existing debt of new rulings). Skipped: full suite, frontend (no change).

## System hover: forces, HP/attack, win probability
- Hovering a system now lists units per zone (space + planets) with hit points (2 with Sustain Damage, minus damage taken)
  and attack (hits on X+ ×dice), plus per-faction totals (HP, expected hits/round). Frontend: `SystemDetailsCard/SystemForces.tsx`
  (reuses `summarizeZone`, `Unit`, `FactionIcon`, `useFactionHelpers`).
- Zones with exactly two fighting sides also show a win-probability bar (attacker / draw / defender).
  Backend: `core/combat_odds.py` (seeded Monte Carlo over `battle_units.combat_units`, so upgrades, hooks, damage and nebula
  count) behind `GET /tactical/odds/{position}`; hook `useSystemOdds`.
- ⚠️ ASSUMPTION (estimate only, documented in the module): cheapest-first loss assignment with Sustain Damage preferred,
  AFB once before round 1, no Space Cannon/Bombardment/retreats/action cards/rerolls. New route: restart the backend.
- QA: `tests/test_combat_odds.py`, ruff, mypy, `tsc` (app), eslint. Skipped: full suite, vitest, build, e2e.

## Rulings Update Review: 314 Remapped Ruling IDs (2026-11-24)
- Reviewed all 314 IDs that the 2026-11-22 dump remap moved to new numbers (`@ruling` + `rulings_status.json`):
  198 have the same text (renumbered only); 116 have reworded text and were checked against their tests, statuses and
  the engine one by one.
- Two rulings now mean the opposite, so the engine was changed:
  - G'hom Sek'kus + Dominus Orb (F_norr ghom-sekkus/7): purging Dominus Orb no longer lets the commander commit
    ground forces from systems that contain the N'orr player's command token (`sardakk._commander_sources`; R62).
  - Own captured units (R_capture notes/5): a player may return their own captured ships/mechs to reinforcements at
    any time. New `capture.return_own`, `POST /capture/return-own` (actor = that player), Activity
    `capture.return_own`, and a UI path: click an own unit on your own `Nombox` → "Return 1 to reinforcements". Tokens
    (fighters/infantry) are excluded because they belong to no one (R61.5).
- Wrong auto-remapped tags were fixed: Triad voting test → `the-triad/3` (was `/2`, Diplomacy readying);
  the Classified re-elect test no longer claims `miscount-disclosed/3.1`; the Enigmatic Device test no longer claims
  `R_exploration/notes/5` (Ion Storm only now); the Political Favor test no longer claims `quash/2`.
- `the-triad/2` (Diplomacy can ready The Triad) is now honestly uncovered; it needs a relic pick in Diplomacy. The
  uncovered count stays at 202.
- QA: factions + rulings_general + capture/activity/frontier/relics suites (1262 passed; the 3 failures come from
  another session's uncommitted argent/l1z1x/naalu edits and pass without them), ruff (only the other session's
  file), mypy (changed files), frontend tsc/eslint/vitest (Nombox, ActivityPanel). Skipped: full suite, build, e2e.
  Backend restart needed (new route).

## Nebula: Entry Without Activation, Retreats Allowed (2026-11-24)
- User decision: adopt the design intent in `R_nebula` notes/2–3 — ships may move INTO a nebula that is not the
  active system (retreat, Skilled Retreat, Foresight, Helix Protocol, Dark Space Navigation), still never THROUGH it.
- `retreat.retreat_destinations` / `ships_move_destinations`, Argent/L1Z1X hero targets and Naalu Foresight no longer
  exclude nebulae; pathing (`movement_paths._passable`) unchanged. Docs: RULES.md 1.2, 32 (R6), 39 (O4), 53, 62.
- QA: full backend suite before test updates (only expected nebula tests + pre-existing guards failed), then the 6
  updated tests, ruff, mypy. Pre-existing red: `test_ruling_coverage` (new-rulings debt), `test_locality_guard`
  (fandom URLs in `frontend/src/domains/rules/componentLinks.ts` — parallel session). Skipped: frontend (no change).

## Physical Ship Movement Replay, Phase 1: Live Post-Move Flight (2026-11-24)
- Backend: `GameState.last_move` (`MoveRecord`: ordered route, hop kinds `lane`/`wormhole`/`portal`/`jump`,
  route anomalies, ships, cargo) set by `movement.move_fleet` / single-stack move via
  `movement_paths.build_move_record`; cleared on activation and at the end of the tactical action. Presentation
  only, rules never read it. Activity `tactical.move` gains facts `move_route` (route/hops/anomalies) and
  `carried` (cargo; feed: "carried 2 Infantry", "via … / through a wormhole").
- Frontend: every client pairs a new `move_route` entry with the live map before/after the move
  (`state/useLiveMoveReplay.ts`, pure helpers in `state/liveMoveReplay.ts`) and replays it through the existing
  `buildMapReplayPlan` (`liveMove` option; planner now works on a resolved movement, `liveMovement.ts`).
- Flight (`entities/replay/flightPath.ts`): one smooth Catmull-Rom path through every route system, easing only
  at launch/landing, slow and heavy (~1.4 s per system; user: first pace "way too fast"); history replays keep the
  legacy arc. Wormhole/ingress-egress hop = fly to the wormhole printed on the tile or the wormhole/ingress token
  (`entities/geometry/wormholePoints.ts`, moved out of `WormholeBlockedLayer`/`wormholeLinks`), shrink-and-spin
  into a swirl, emerge at the linked gate; gravity rift = faster leg + violet warp ring/trail; nebula = damped,
  dimmed entry + mist. Engine flames on flying ships (`UnitStack/FlightEngines.tsx`, nozzle table shared with
  the battle overlay in `shared/ui/Unit/engines.ts`), lit only for the flight. Ground forces ride hidden inside
  the carrier (mini badges on the hull, `UnitStack/CarriedCargo.tsx`). Ships still park in the native
  north-west heading after landing (unchanged).
- Skippable: "Skip" pill, Esc/Space (outside inputs/buttons) end any map replay; admin fast mode = no replay
  (`replayRunDuration`).
- QA: backend full suite (failures only pre-existing `test_locality_guard`, `test_ruling_coverage` x2, and
  `test_bot_runner` under xdist load - passes alone); ruff; mypy (changed); frontend tsc (app), eslint (changed),
  vitest (`entities`, `state`, `domains/map`, `domains/battle`, ActivityPanel), build, e2e. Backend restart
  needed (new state field / facts).

## Flight Replay: Cargo Packs Into Carriers, Invasion Landings, Slower Pace (2026-11-24)
- User feedback: fighters/infantry flying as numbered badges looked like a blob. Fighters and ground forces now
  pack into a moving ship with capacity (slide in and shrink, `PACK_MS`), the fleet launches once they are aboard,
  the carrier shows a few small icons without counts in flight, and the units unpack from its landing point to
  their slots (`UNPACK_MS`). `liveMovement.packRidingCargo`, `flightPath.buildCargoKeyframes`,
  `MapUnitTransition.cargoRide` (replaces `hiddenInFlight`).
- Invasion: a new `invasion.commit` entry (`landed` facts) replays on every client as ground forces flying from
  space down to their planets (`LiveLanding`, `resolveLanding`; per-unit `toHolder` in `ResolvedMovement`).
- Slower overall (user: "a little bit slower"): ~1.75 s per system, wormhole jump 1.8 s.
- QA: frontend tsc (app), eslint (changed), vitest (`entities`, `state`, `domains/map`, `domains/battle`,
  ActivityPanel), build, e2e. Skipped: backend (no change).

## Flight Replay: Armada Weight, Plain Cargo Sprites (2026-11-24)
- User feedback: cargo showed the round-rect token background and the fleet still felt too fast ("I want to see
  weight as an armada moves"). Cargo on the carrier and while packing/unpacking now uses plain unit sprites in a
  loose group (`LooseCargo`, no token, no count); the map token with its count returns once the replay ends.
- Heavy motion (`flightPath.ts`): ignition (`IGNITION_MS`, turn onto course in place while engines spool up and the
  ship lifts: +7% scale, deeper shadow), ~2.8 s per system, settle (`SETTLE_MS`: stop, touch down, turn to park);
  wormhole jump 2.4 s, pack/unpack 1.1/1.3 s. Engine flames spool up, burn and cut with those phases.
- QA: frontend tsc (app), eslint (changed), vitest (`entities`, `state`, `domains/map`, `domains/battle`,
  ActivityPanel), build, e2e. Skipped: backend (no change).

## Flight Replay: Fleet Visible While Cargo Boards, Cargo Physics (2026-11-24)
- Bug: while cargo packed, the fleet waiting for it was invisible (its flight animation only filled forwards, so
  the delay showed the hidden CSS state) - fighters/infantry slid into nothing. Routed and cargo flights now use
  `fill: "both"`: ships rest visibly at their start until they launch.
- Cargo moves like the ships (`buildCargoKeyframes`): boarding = fighters turn toward the carrier, accelerate,
  brake into the hangar and only then shrink and vanish (fully visible while travelling); unpacking = emerge from
  the carrier, launch out, brake, fighters turn back to the parked heading. Ground forces stay upright.
- QA: frontend tsc (app), eslint (changed), vitest (`entities`, `state`, `domains/map`, `domains/battle`,
  ActivityPanel), build, e2e. Skipped: backend (no change).

## Flight Replay: Ships That Fly, Cargo Goes Inside, Throttled Engines (2026-11-25)
- User feedback: infantry/fighter icons drawn under/on the flying ships looked bad; too much rotation, ships did not
  feel like they were flying; wanted visible engines and a war-fleet feel.
- Cargo: no icons on the hull in flight (`CarriedCargo` and `carriedCargo` removed; `LooseCargo` split into its own
  file). Boarding cargo is drawn BELOW the ships (no +200 badge z-boost for `cargoRide`), shrinks as it nears the
  carrier and dwindles to a speck while fading as it slips under the hull; unpacking grows out from under it.
- Motion (`flightPath.ts`): no pivot in place. Ignition only lifts off (+10% scale) and spools up the engines; the
  ship comes about while accelerating and swings to its parked heading while braking (`TURN_WINDOW_*`); settle only
  sets it down. Look-ahead steering (`LOOK_AHEAD_PX`) leads the nose into corners. A single hop is a straight line
  (no arc). Wormholes: dive in holding the heading and emerge facing the next course (no 720° spin).
- Engines: `buildPathKeyframes` returns a `thrust` timeline (flare at launch, burn with speed, fade while braking,
  cold on landing) that the flight hook plays on each nozzle and a new ion wake (`[data-thrust]`); bigger flames with
  a hot core and fast flicker. History replays keep the fixed CSS burn.
- Fleet: ships launch in waves by class (`staggerFleetLaunch`: destroyers, cruisers, carriers, dreadnoughts,
  flagship/war sun; `LAUNCH_WAVE_MS`); cargo unpacks exactly when its own carrier lands; wormhole/anomaly effects
  are shared by ships passing within `SHARED_EFFECT_MS`.
- QA: frontend tsc (app), eslint (changed), vitest (`entities/replay`, `state`, `domains/map`), build. Skipped:
  backend (no change), e2e (replay layer only, not setup/flow), visual check in a live game.
