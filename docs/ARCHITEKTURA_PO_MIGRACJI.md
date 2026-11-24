# Architecture After Migration to the `ti4_web` Frontend

> 🟡 **REFERENCE (code map).** Describes backend/frontend and the `web-data` contract — where
> things live and how they work. Current work status: [`PROGRESS.md`](PROGRESS.md); plan:
> [`PLAN_PELNA_ROZGRYWKA.md`](PLAN_PELNA_ROZGRYWKA.md). When in doubt — code wins.
>
> ⚠️ **Description as of: 2026-11-04.** Since then we added e.g. God-Mode UI, strategy cards, action cards,
> relics, networked multiplayer (lobby, tokens, saves in `saves/`), and ~25 new routers. Current file
> map: [`README.md`](README.md) §3 and [`ARCHITEKTURA_KODU.md`](ARCHITEKTURA_KODU.md) §4.

This document describes the project state after migrating from our custom SVG frontend to the mature
AsyncTI4 viewer (`ti4_web`). It is an orientation map: where everything lives and how it works.
Read it alongside `PROGRESS.md` (work status) and the technical specification
(`specyfikacja_techniczna_i_architektura_systemu.md`).

---

## 1. Big Picture in One Paragraph

Backend (Python/FastAPI, `src/` directory) is the **source of truth** for game state.
Frontend (React, `frontend/` directory) is a **viewer**: it fetches a single
`web-data` document and renders the entire board + player panels from it. Backend translates its
internal `GameState` into the format expected by the frontend (`PlayerDataResponse`).
Static game data (units, planets, systems) is **bundled** in the frontend and
resolved by ID — backend sends only state. Graphics (tiles, units) are served
**locally** from Backend (`/static/...`) via AssetResolver — no CDN (spec
`local-ti4-data-foundation`, decision D1).

```
┌───────────────────────────┐     GET /api/public/game/{id}/web-data     ┌──────────────────────────┐
│  Frontend (frontend/)     │  ◄─────────── PlayerDataResponse ───────────│  Backend (src/)          │
│  React + Vite viewer      │                                             │  FastAPI + GameState     │
│  - board, player panels   │     POST /map/load, /setup/player, ...       │  - HexGrid, registry     │
│  - reads IDs, local art   │  ──────────── state mutations ──────────────►│  - EventStore (SQLite)   │
└───────────────────────────┘                                             └──────────────────────────┘
         │  graphics (webp) /static                                              │  JSON assets
         ▼                                                                       ▼
   Backend /static/... (local)                                        assets/ (JSON in repo; art outside repo, D1)
```

---

## 2. How to Run

**Simplest — one click:** run `start.cmd` (double-click) or `./start.ps1`
in the repo directory. The script frees port 8000, starts backend (FastAPI :8000) and frontend
(Vite :5173) in separate windows, runs `npm install` on first launch, waits for
the dev server to come up, and opens the browser at `http://localhost:5173/`. To stop:
close both PowerShell windows.

**Manual (two terminals)** — when you want separate logs:
```powershell
# Terminal 1 — backend (repo directory)
uv run python -m src.api            # FastAPI at http://127.0.0.1:8000 (frees port itself)

# Terminal 2 — frontend (frontend/ directory)
npm install                         # first time
npm run dev                         # Vite at http://localhost:5173
```

Then open `http://localhost:5173/` in a browser — opens STRAIGHT to the game view
(no landing page). **At startup the backend only has a demo map** (7 tiles),
so to see a real board you need to load a map and set up players
(see section 6 — via API for now, as edit UI doesn't exist yet).

Backend QA after every change:
```powershell
uv run pytest -q -n auto ; uv run ruff check src tests ; uv run mypy src tests
```
Frontend QA:
```powershell
# in frontend/ directory
npx tsc --noEmit -p tsconfig.app.json ; npm run lint ; npm run build ; npx vitest --run
```

---

## 3. Backend (`src/`)

### 3.1. Core (`src/core/`) — unchanged after migration
- `registry.py` — `StaticDataRegistry`: loads units/planets/systems/factions from
  AsyncTI4 assets (filtered by `source` field per `assets/enabled_sources.json`).
- `models.py` — Pydantic models for static entities (`UnitDef`, `PlanetDef`, `SystemDef`, `FactionDef`).
- `hex_grid.py` — `HexGrid`: cubic coordinates `(q,r,s)`, adjacency, wormholes, anomalies.
- `positions.py` — AsyncTI4 position table (`101`, `102`…) → `Hex`, from alias file.
- `map_string.py` — map string parser → `HexGrid`.
- `game_state.py` — `GameState` (players, systems, units) + `clone()`.
- `event_store.py` — `EventStore` (Snapshot Stack in SQLite, Undo/Redo/God-Mode).
- `unit_catalog.py` — explicit rule tables: placement (space/planet), `asyncId`, fleet codes.
- `faction_setup.py` — `startingFleet` parser + placing fleet/planets at setup.
- `home_slots.py` — corner colors (home slots) for 6 players.

### 3.2. API Layer (`src/api/`)
- `app.py` — `create_app` factory, all endpoints, WebSocket, serving `/static`.
- `web_data.py` — **KEY post-migration.** `build_web_data`: `GameState` + `HexGrid`
  + registry → `PlayerDataResponse` document for frontend. Entire UI contract lives here.
- `schemas.py` — DTOs (MapView, setup/unit requests, God-Mode patch).
- `state_service.py` — sole place mutating state (commit + broadcast).
- `connection_manager.py` — WebSocket connection registry + broadcast.
- `demo_map.py` — **temporary** starter map (7 tiles) before you load a map string.

### 3.3. Endpoints (what is exposed)
| Method + path | Role |
|---|---|
| `GET /api/public/game/{id}/web-data` | **Document for frontend** (board + players). |
| `GET /map` | Legacy map view (`MapView` DTO) — used by tests, not by the new frontend. |
| `GET /state` | Raw `GameState` + history metadata. |
| `GET /factions` | List of factions for setup. |
| `POST /game/new` | **New game in one step**: reset + map (optional string, otherwise test) + player setup (auto colors/slots). Used by start screen. |
| `POST /map/load` | Loads map from map string (sets `current_grid`). |
| `POST /setup/player` | Faction setup on home slot (fleet + planets). |
| `POST /system/{pos}/space` | Edit units in space (God-Mode). |
| `POST /system/{pos}/planet/{planet}` | Edit units on planet (God-Mode). |
| `PUT /state`, `POST /god-mode/patch` | God-Mode: overwrite / patch state. |
| `POST /undo`, `POST /redo` | History navigation. |
| `WS /ws` | `StateEnvelope` stream (our simple WS — NOT STOMP, see gaps). |
| `GET /static/*` | Assets from `assets/` (JSON and local graphics/fonts — source for AssetResolver). |
| `GET /components`, `/components/{cat}`, `/components/{cat}/{id}` | **Read-only ComponentCatalog** (component + `TimingSpec` + effect status + rule topics). Spec `local-ti4-data-foundation` (R11). |
| `GET /components/factions/{id}/bundle` | Faction bundle (leaders, abilities, techs, promissory, units, breakthrough). |
| `GET /timing-specs?trigger=&phase=` | Components matching trigger kind and phase (`TimingSpec`). |

> **DataAuditor (CLI, not an endpoint):** `uv run python -m src.audit` — data consistency
> and locality report (entry counts, references, external URLs, missing graphics from manifest);
> critical error → non-zero exit code. Details: `ARCHITEKTURA_KODU.md` §4a.

### 3.4. `web-data` Contract — Mapping Rules (don't guess!)
- `tilePositions`: list of `"<position>:<systemId>"` (e.g. `"101:72"`). Frontend computes
  pixels itself from `tileCoordinates` by position key — uses the same IDs as us (`000`, `101`…).
- Units in `tileUnitData[pos].space[faction]` and `...planets[planet][faction]`:
  keyed by **`asyncId`** (`ff`, `dd`, `ca`, `cv`, `gf`, `mf`, `sd`, `pd`…), `entityType: "unit"`.
- `versionSchema` MUST be ≥ 5, otherwise frontend blocks rendering with "Update Needed" screen
  (`WEB_DATA_SCHEMA_VERSION` constant in `web_data.py` = `REQUIRED_VERSION_SCHEMA` in `GameMapPage.tsx`).
- Many fields (`objectives`, `cardPool`, `expeditions`, strategy cards, laws) are sent
  empty/default — the viewer requires their presence, even before round logic populates them.

---

## 4. Frontend (`frontend/`)

Source: AsyncTI4 `ti4_web` (React 19 + Vite + TS, custom design system in `src/ds/`,
react-query, react-router, Zustand). Post-migration REDUCED to a single game view.

### 4.1. What Remained (game view)
- Entry: `src/main.tsx` → `/` = `pages/StartScreen.tsx` (start screen: player count,
  factions, map string → `POST /game/new` → `/game`); `/game` and `/game/:mapid` →
  `pages/GameMapPage.tsx`. Default `gameId` = `"local"` (backend holds one game).
- Start screen: `src/pages/StartScreen.tsx` + `src/api/useNewGame.ts` (`useFactions`, `createNewGame`).
- `GameMapPage` → `GameContextProvider` (fetches `web-data`, builds `GameData`) →
  `MapView` / `PannableMapView` (board) + **players / objectives / general** tabs.
- Domains used by view: `domains/{map, player, objectives, tabs, cards, settings, game-shell}`,
  plus `entities/`, `state/`, `api/`, `shared/`, `layout/`, `hooks/`, `ds/`, `styles/`.
- `src/api/usePlayerData.ts` — single data entry: `fetch({gameDataUrl}/{id}/web-data)`.
- `src/entities/data/*.ts` — BUNDLED static catalogs (systems/units/planets…),
  auto-generated from AsyncTI4 assets. Frontend resolves IDs locally, zero catalog fetches.
- `src/shared/assets/resolveAsset.ts` — **AssetResolver**: graphics LOCALLY from Backend
  (`/static/...`), `assetUrl`/`sheetUrl` + `assetManifest.json`, placeholder for missing items.
  Replaced old `cdnImage.ts` (removed) — no requests to `images.asyncti4.com`. Spec
  `local-ti4-data-foundation` (R2), decision D1. Local fonts via `@fontsource/*` (D11).

### 4.2. What Was Removed (AsyncTI portal — not needed for us)
Landing page, games list, dashboard, login-as-page, old "OLD UI" (image-map),
FoW view, music-video. Details in `PROGRESS.md` (Block F2).

### 4.3. Branding
- Top-left label: `src/shared/ui/Logo.tsx` — now text "CUSTODIAN ENGINE" (was AsyncTI4 banner).
- Tab title / console / `index.html` — Custodian Engine.

### 4.4. AsyncTI4 Leftovers Kept Intentionally
- `src/api/auth/`, `src/domains/auth/` — transitively required (SecretHand, header,
  drawer). Locally they degrade gracefully: no Discord user = hidden "hand",
  login button inactive. Cutting them out = cascade of edits, deferred.
- STOMP WebSocket (`src/api/useGameSocket.ts`) — client tries to connect to
  `ws://127.0.0.1:8000/ws-stomp`, which backend does NOT expose. `reconnectDelay: 0`
  → no reconnect spam, connection error is swallowed. Live-sync for now
  via refetch, not socket.

---

## 5. Feature Status & History

What is done and what is in progress — see [`PROGRESS.md`](PROGRESS.md) (stage status + recent
blocks) and [`PROGRESS_ARCHIWUM.md`](PROGRESS_ARCHIWUM.md) (full block history). Plan for upcoming
stages: [`PLAN_PELNA_ROZGRYWKA.md`](PLAN_PELNA_ROZGRYWKA.md). Real code state is in `src/`
and tests — this document is only an orientation map of "where everything lives".

---

## 6. Data Sources & References (DO NOT delete)

Two directories in the repo are **local AsyncTI4 data sources and references**. They are in
`.gitignore` (not versioned), but physically sit on disk and serve as:

- **`TI4_map_generator_bot/`** — original AsyncTI4 bot (Java). Source of:
  - assets (`src/main/resources/...`), from which we take data for `assets/`;
  - `web-data` / graphic naming conventions (`imagePath`, `asyncId`), CDN paths;
  - mechanical rules to verify (see `docs/RULES.md`).
  Treat as the "dictionary of truth" for AsyncTI4 data format.
- **Live AsyncTI4 viewer** (`https://asyncti4.com/game/<id>`, data:
  `https://bot.asyncti4.com/api/public/game/<id>/web-data`) — reference for HOW the
  finished render should look (player panels, planet info, unit preview).
  Example active game for comparison: `pbd30347`.

Frontend (`frontend/`) is AsyncTI4 `ti4_web` code — it has lots of features we
don't use yet (replay, cards, diplomacy). They aren't deleted; just
inactive because backend doesn't populate the corresponding `web-data` fields. We enable them
gradually by sending data from backend (e.g. planet info renders from static
frontend data, so it works "for free" as soon as `systemId`/planet names match).
