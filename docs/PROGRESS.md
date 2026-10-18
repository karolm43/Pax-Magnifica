# Postęp projektu — Custodian Engine

Plik śledzi stan prac między sesjami. Aktualizowany na koniec każdego bloku.

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
