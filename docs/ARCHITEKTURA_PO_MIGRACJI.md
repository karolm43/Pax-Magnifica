# Architektura po migracji na frontend ti4_web

Ten dokument opisuje **aktualny** stan projektu po przejściu z własnego frontendu
SVG na dojrzały viewer AsyncTI4 (`ti4_web`). Jest mapą orientacyjną: gdzie co leży,
jak to działa, co jest gotowe, a co jest luką. Czytaj go razem z `PROGRESS.md`
(historia bloków) i specyfikacją techniczną (`specyfikacja_techniczna_i_architektura_systemu.md`).

---

## 1. Obraz całości w jednym akapicie

Backend (Python/FastAPI, katalog `src/`) jest **źródłem prawdy** o stanie gry.
Frontend (React, katalog `frontend/`) jest **viewerem**: pobiera jeden dokument
`web-data` i renderuje z niego całą planszę + panele graczy. Backend tłumaczy swój
wewnętrzny `GameState` na format, którego oczekuje frontend (`PlayerDataResponse`).
Statyczne dane gry (jednostki, planety, systemy) frontend ma **wbudowane** i
rozwiązuje po ID — backend wysyła tylko stan. Grafiki (kafelki, jednostki) idą ze
zdalnego CDN AsyncTI4.

```
┌───────────────────────────┐     GET /api/public/game/{id}/web-data     ┌──────────────────────────┐
│  Frontend (frontend/)     │  ◄─────────── PlayerDataResponse ───────────│  Backend (src/)          │
│  React + Vite viewer      │                                             │  FastAPI + GameState     │
│  - plansza, panele graczy │     POST /map/load, /setup/player, ...       │  - HexGrid, rejestr      │
│  - czyta ID, grafiki z CDN│  ──────────── mutacje stanu ───────────────►│  - EventStore (SQLite)   │
└───────────────────────────┘                                             └──────────────────────────┘
         │  grafiki (webp)                                                        │  assety JSON
         ▼                                                                        ▼
   images.asyncti4.com (CDN)                                            assets/ (lokalne, poza repo)
```

---

## 2. Jak uruchomić

**Najprościej — jedno kliknięcie:** uruchom `start.cmd` (dwuklik) albo `./start.ps1`
w katalogu repo. Skrypt zwalnia port 8000, startuje backend (FastAPI :8000) i frontend
(Vite :5173) w osobnych oknach, przy pierwszym razie robi `npm install`, czeka aż
dev-serwer wstanie i otwiera przeglądarkę na `http://localhost:5173/`. Zamknięcie:
zamknij oba okna PowerShella.

**Ręcznie (dwa terminale)** — gdy chcesz widzieć logi osobno:
```powershell
# Terminal 1 — backend (katalog repo)
uv run python -m src.api            # FastAPI na http://127.0.0.1:8000 (sam zwalnia port)

# Terminal 2 — frontend (katalog frontend/)
npm install                         # pierwszy raz
npm run dev                         # Vite na http://localhost:5173
```

Potem w przeglądarce otwórz `http://localhost:5173/` — otwiera się OD RAZU widok gry
(bez landing page'a). **Na starcie backend ma tylko mapę demonstracyjną** (7 kafelków),
więc żeby zobaczyć prawdziwą planszę, trzeba wczytać mapę i zrobić setup graczy
(patrz sekcja 6 — na razie przez API, bo UI edycji jeszcze nie ma).

QA backendu po każdej zmianie:
```powershell
uv run pytest -q ; uv run ruff check src tests ; uv run mypy src tests
```
QA frontendu:
```powershell
# w katalogu frontend/
npm run type-check ; npm run lint ; npm run build
```

---

## 3. Backend (`src/`)

### 3.1. Rdzeń (`src/core/`) — bez zmian po migracji
- `registry.py` — `StaticDataRegistry`: ładuje jednostki/planety/systemy/frakcje z
  assetów AsyncTI4 (filtr po polu `source` wg `assets/enabled_sources.json`).
- `models.py` — modele Pydantic statycznych encji (`UnitDef`, `PlanetDef`, `SystemDef`, `FactionDef`).
- `hex_grid.py` — `HexGrid`: współrzędne kubiczne `(q,r,s)`, sąsiedztwo, wormhole, anomalie.
- `positions.py` — tabela pozycja AsyncTI4 (`101`, `102`…) → `Hex`, z pliku alias.
- `map_string.py` — parser map stringa → `HexGrid`.
- `game_state.py` — `GameState` (gracze, systemy, jednostki) + `clone()`.
- `event_store.py` — `EventStore` (Snapshot Stack w SQLite, Undo/Redo/God-Mode).
- `unit_catalog.py` — jawne tabele reguł: umiejscowienie (space/planet), `asyncId`, kody floty.
- `faction_setup.py` — parser `startingFleet` + rozłożenie floty/planet przy setupie.
- `home_slots.py` — kolory rogów (slotów domowych) przy 6 graczach.

### 3.2. Warstwa API (`src/api/`)
- `app.py` — fabryka `create_app`, wszystkie endpointy, WebSocket, serwowanie `/static`.
- `web_data.py` — **KLUCZOWY po migracji.** `build_web_data`: `GameState` + `HexGrid`
  + rejestr → dokument `PlayerDataResponse` dla frontendu. Tu żyje cały kontrakt z UI.
- `schemas.py` — DTO (MapView, żądania setupu/jednostek, God-Mode patch).
- `state_service.py` — jedyne miejsce mutujące stan (commit + broadcast).
- `connection_manager.py` — rejestr połączeń WebSocket + broadcast.
- `demo_map.py` — **tymczasowa** mapa startowa (7 kafelków), zanim wczytasz map string.

### 3.3. Endpointy (co jest wystawione)
| Metoda + ścieżka | Rola |
|---|---|
| `GET /api/public/game/{id}/web-data` | **Dokument dla frontendu** (plansza + gracze). |
| `GET /map` | Stary widok mapy (DTO `MapView`) — używany przez testy, nie przez nowy front. |
| `GET /state` | Surowy `GameState` + metadane historii. |
| `GET /factions` | Lista frakcji do setupu. |
| `POST /game/new` | **Nowa gra jednym krokiem**: reset + mapa (opcjonalny string, inaczej testowy) + setup graczy (kolory/sloty auto). Używany przez ekran startowy. |
| `POST /map/load` | Wczytuje mapę z map stringa (ustawia `current_grid`). |
| `POST /setup/player` | Setup frakcji na slocie domowym (flota + planety). |
| `POST /system/{pos}/space` | Zmiana jednostek w przestrzeni (God-Mode). |
| `POST /system/{pos}/planet/{planet}` | Zmiana jednostek na planecie (God-Mode). |
| `PUT /state`, `POST /god-mode/patch` | God-Mode: nadpisanie / patch stanu. |
| `POST /undo`, `POST /redo` | Nawigacja po historii. |
| `WS /ws` | Strumień `StateEnvelope` (nasz prosty WS — NIE STOMP, patrz luki). |
| `GET /static/*` | Assety JSON z `assets/`. |

### 3.4. Kontrakt `web-data` — reguły mapowania (nie zgaduj!)
- `tilePositions`: lista `"<pozycja>:<systemId>"` (np. `"101:72"`). Frontend sam liczy
  piksele z `tileCoordinates` po kluczu pozycji — używa tych samych ID co my (`000`, `101`…).
- Jednostki w `tileUnitData[pos].space[frakcja]` i `...planets[planeta][frakcja]`:
  kluczowane **`asyncId`** (`ff`, `dd`, `ca`, `cv`, `gf`, `mf`, `sd`, `pd`…), `entityType: "unit"`.
- `versionSchema` MUSI być ≥ 5, inaczej frontend blokuje render ekranem „Update Needed"
  (stała `WEB_DATA_SCHEMA_VERSION` w `web_data.py` = `REQUIRED_VERSION_SCHEMA` w `GameMapPage.tsx`).
- Wiele pól (`objectives`, `cardPool`, `expeditions`, karty strategii, prawa) wysyłamy
  puste/domyślne — viewer wymaga ich obecności, ale logika rundy jeszcze ich nie wypełnia.

---

## 4. Frontend (`frontend/`)

Źródło: AsyncTI4 `ti4_web` (React 19 + Vite + TS, własny design system w `src/ds/`,
react-query, react-router, Zustand). Po migracji ZREDUKOWANY do pojedynczego widoku gry.

### 4.1. Co zostało (widok gry)
- Wejście: `src/main.tsx` → `/` = `pages/StartScreen.tsx` (ekran startowy: liczba graczy,
  frakcje, map string → `POST /game/new` → `/game`); `/game` i `/game/:mapid` →
  `pages/GameMapPage.tsx`. `gameId` domyślny = `"local"` (backend trzyma jedną grę).
- Ekran startowy: `src/pages/StartScreen.tsx` + `src/api/useNewGame.ts` (`useFactions`, `createNewGame`).
- `GameMapPage` → `GameContextProvider` (pobiera `web-data`, buduje `GameData`) →
  `MapView` / `PannableMapView` (plansza) + zakładki **players / objectives / general**.
- Domeny używane przez widok: `domains/{map, player, objectives, tabs, cards, settings, game-shell}`,
  oraz `entities/`, `state/`, `api/`, `shared/`, `layout/`, `hooks/`, `ds/`, `styles/`.
- `src/api/usePlayerData.ts` — jedyne wejście danych: `fetch({gameDataUrl}/{id}/web-data)`.
- `src/entities/data/*.ts` — WBUDOWANE statyczne katalogi (systemy/jednostki/planety…),
  auto-generowane z assetów AsyncTI4. Frontend rozwiązuje ID lokalnie, zero fetchu katalogów.
- `src/entities/data/cdnImage.ts` — grafiki z `https://images.asyncti4.com/...`.

### 4.2. Co usunięto (portal AsyncTI — nam niepotrzebne)
Landing page, lista gier, dashboard, logowanie-jako-strona, stary „OLD UI" (image-map),
widok FoW, music-video. Szczegóły w `PROGRESS.md` (Blok F2).

### 4.3. Branding
- Napis w lewym rogu: `src/shared/ui/Logo.tsx` — teraz tekst „CUSTODIAN ENGINE" (był baner AsyncTI4).
- Tytuł zakładki/konsola/`index.html` — Custodian Engine.

### 4.4. Pozostałości AsyncTI4 ZOSTAWIONE świadomie
- `src/api/auth/`, `src/domains/auth/` — wymagane tranzytywnie (SecretHand, nagłówek,
  drawer). Lokalnie degradują się łagodnie: brak użytkownika Discord = ukryta „ręka",
  przycisk logowania nieaktywny. Wycinanie = kaskada przeróbek, odłożone.
- STOMP WebSocket (`src/api/useGameSocket.ts`) — klient próbuje połączyć się z
  `ws://127.0.0.1:8000/ws-stomp`, którego backend NIE wystawia. `reconnectDelay: 0`
  → brak spamu reconnectów, błąd połączenia jest pochłaniany. Live-sync na razie
  przez refetch, nie przez socket (patrz luki).

---

## 5. Co działa, a co jest luką (względem DoD Fazy 1)

**DoD Fazy 1:** rozgrywasz fizyczną partię używając aplikacji jako interaktywnej mapy
+ licznika zasobów/VP.

| Element | Stan |
|---|---|
| Import danych (jednostki/planety/systemy) | ✅ backend (rejestr) + frontend (wbudowane) |
| Siatka heksagonalna `(q,r,s)` + wormhole | ✅ `HexGrid` |
| `GameState` + Event Sourcing (Undo/Override) | ✅ `GameState` + `EventStore` |
| Parser map stringów | ✅ backend `POST /map/load` |
| Render planszy (kafelki, jednostki, planety) | ✅ nowy frontend (viewer) |
| Panele graczy / VP / zasoby / cele | ✅ render w nowym froncie (dane z `web-data`) |
| Setup gry z UI (liczba graczy, frakcje, map string) | ✅ ekran startowy `/` → `POST /game/new` |
| **Edycja bieżącej gry z UI** (zmiana jednostek, VP/zasoby) | ❌ **LUKA** — tylko przez API |
| Szybki edytor jednostek na heksie (skróty „2D 1C 4F") | ❌ **LUKA** — nie istnieje w żadnym froncie |
| Live-sync po mutacji (WebSocket) | ⚠️ nasz WS `/ws` istnieje, ale front używa STOMP → refetch zamiast push |

**Wniosek:** render stanu jest gotowy (nawet bogatszy niż w starym froncie). Największa
luka to **brak UI do wprowadzania/edycji stanu** — nowy frontend to viewer. Żeby domknąć
DoD Fazy 1 (operujesz aplikacją przy stole), trzeba dołożyć warstwę edycji nad istniejącymi
endpointami: wczytanie map stringa, setup frakcji, zmiana jednostek, VP/zasoby, Undo/Redo.

---

## 6. Jak teraz postawić realną grę (tymczasowo, przez API)

Dopóki nie ma UI edycji, planszę ustawia się żądaniami do backendu:

```powershell
# 1) Wczytaj mapę z map stringa (przykład 6-osobowej mapy)
$ms = '72 66 77 65 69 50 61 44 64 76 60 73 46 42 71 79 70 59 48 45 68 51 67 47 49 62 43 58 63 78 41 40'
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/map/load' -ContentType 'application/json' -Body (@{map_string=$ms} | ConvertTo-Json)

# 2) Ustaw gracza (frakcja + kolor na slocie domowym)
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/setup/player' -ContentType 'application/json' -Body (@{player_id='p1';faction_id='sol';color='red';home_position='301'} | ConvertTo-Json)

# 3) Odśwież przeglądarkę (http://localhost:5173/) — plansza pokaże mapę + jednostki Sol
```

---

## 6a. Źródła danych i referencje (NIE kasować)

Dwa katalogi w repo to **lokalne źródła danych i referencje** AsyncTI4. Są w
`.gitignore` (nie wersjonujemy ich), ale fizycznie leżą na dysku i służą jako:

- **`TI4_map_generator_bot/`** — oryginalny bot AsyncTI4 (Java). Źródło:
  - assetów (`src/main/resources/...`), z których bierzemy dane do `assets/`;
  - konwencji `web-data` / nazw grafik (`imagePath`, `asyncId`), ścieżek CDN;
  - reguł mechanicznych do weryfikacji (patrz `docs/RULES.md`).
  Traktuj jako „słownik prawdy" o formacie danych AsyncTI4.
- **Live viewer AsyncTI4** (`https://asyncti4.com/game/<id>`, dane:
  `https://bot.asyncti4.com/api/public/game/<id>/web-data`) — referencja, JAK ma
  wyglądać gotowy render (panele graczy, info na planetach, podgląd jednostek).
  Przykład aktywnej gry do porównań: `pbd30347`.

Frontend (`frontend/`) to kod `ti4_web` AsyncTI4 — ma mnóstwo featurów, których
jeszcze nie wykorzystujemy (replay, karty, dyplomacja). Nie są usuwane; po prostu
nieaktywne, bo backend nie wypełnia odpowiednich pól `web-data`. Włączamy je
stopniowo, dosyłając dane z backendu (np. info o planetach rysuje się ze statycznych
danych frontendu, więc działa „za darmo" gdy tylko `systemId`/nazwy planet się zgadzają).

## 7. Następne kroki (propozycja kolejności)

1. **UI edycji nad istniejącym API** — panel/akcje: wczytaj map string, setup frakcji,
   zmiana jednostek w systemie, VP/zasoby, Undo/Redo. To domyka DoD Fazy 1.
2. **Live-sync** — albo dołożyć STOMP po stronie backendu (emisja `GameStateMessage{full:true}`),
   albo przełączyć front na nasz prosty WS `/ws` / refetch po mutacji.
3. **Sprzątanie opcjonalne** — rozważyć wycięcie `auth`/`domains/auth` jeśli chcemy w pełni
   lokalną apkę bez chrome logowania; `demo_map.py` można zastąpić pustą mapą startową.
4. **Local-first grafiki** (opcjonalnie, wg spec) — przekierować `cdnImage()` na nasz `/static`.
```
