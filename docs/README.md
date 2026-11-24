# Custodian Engine Documentation — Index

This file is the **gateway to the documentation**: why this project exists, where everything lives, which document
serves what purpose, and in what order to read them. Start here.

---

## 1. Project Goal (one sentence)

**Custodian Engine is a local engine for playing Twilight Imperium 4 in solo mode —
ultimately an autonomous AI BOT opponent** that runs its own factions: picks strategy cards,
moves fleets, fights, votes in the agenda phase, and scores objectives so a human can play
a full game against the computer (or with the computer filling out the table).

### What this means in practice (maturity stages)
1. **Digital board + God-Mode** (done) — the app mirrors the state of a physical/digital
   board, lets you edit it and undo/redo (Undo). Foundation for the rest.
2. **Gameplay engine** (in progress) — real phases, turns, strategy cards, tactical action,
   combat, status, agenda. The game ENFORCES the rules (referee engine) and drives the round flow
   through TIMING WINDOWS (e.g. strategy card secondaries for all players in turn order). God-Mode
   remains as a manual override valve. Direction shift and window model: `RULES.md` 29, stage E8
   in `PLAN_PELNA_ROZGRYWKA.md`.
3. **AI Bot** (end goal) — decision layer (strategic → operational → tactical)
   that plays a faction independently. The Stage 2 engine serves as its "rules of the world".

Full vision and target architecture: [`specyfikacja_techniczna_i_architektura_systemu.md`](specyfikacja_techniczna_i_architektura_systemu.md).

---

## 2. Document Map (what to read for what)

| Document | Role | Status |
|---|---|---|
| **`README.md`** (this file) | Index: goal, structure, conventions, reading order. | 🟢 living |
| **`PROGRESS.md`** | Work status: stage status + recent blocks (slimmed down). Read at session start. | 🟢 living |
| **`PROGRESS_ARCHIWUM.md`** | Full history of completed blocks (Phase 1 → E4·UI²). Reach for details. | 🟤 archival |
| **`RULES.md`** + **`rules/R<NN>.md`** | **Source of truth for TI4 mechanics.** `RULES.md` is a small INDEX; section N content lives in `rules/R<NN>.md` (e.g. 43.1a = `rules/R43.md`). Read only the needed file. | 🟢 living |
| **`rules_tirules/`** | **Offline dump of rules from tirules2.com** (149 MD topics + `tirules.json`). Check rules here first. Start: `rules_tirules/INDEX.md`. | 🟢 living |
| **`PLAN_PELNA_ROZGRYWKA.md`** | **Main engine plan** (stages E1–E8, phases C/H/N), list of factions and gimmicks, plus **PRODUCT GOAL: all cards ready + drag-from-hand to play**. | 🟢 living |
| **`PLAN_FRAKCJE.md`** | **Faction plan (H5/E7) in session-sized blocks**: foundations (leaders, PNs, abilities), shared mechanics (capture, tokens, adjacency, coexist), faction order, DoD template. | 🟢 living |
| **`bot/PLAN.md`** | **AI Bot (Stage 3)**: audit of what the engine gives the bot, `src/engine/` architecture, local compute (algorithms in worker processes), short `bot/*` branch plan, open decisions. Rules: `rules/R65.md`. Claude instructions: `src/engine/CLAUDE.md`. | 🟢 living |
| **`ARCHITEKTURA_KODU.md`** | **Layers (core/api/engine), development conventions, hook pattern, tech debt.** Read before adding a new mechanic. | 🟢 living |
| **`POKRYCIE_HOOKOW.md`** | **GENERATED hook coverage report** — short summary (~10 KB: % per category, areas, ACTION queue, factions); details (hook list, per-category tables) in `pokrycie_hookow/*.md`, read selectively. Do not edit; refresh: `uv run python -m src.audit.hook_coverage --write`. | 🟢 generated |
| **`OKNA_CZASOWE.md`** | **GENERATED timing window catalog** of all components (events, agendas, factions, persistent effects, special cases). Do not edit; refresh: `uv run python -m src.audit.timing_catalog --write`. Contract: RULES.md 54. | 🟢 generated |
| **`UI_WYBOR_FRAKCJI.md`** | **Faction picker scene + "Players" wizard step**: layout, files, content format (portraits/quotes/lore), animations, Obsidian (script + dread), gotchas. Read before changing setup UI. | 🟢 living |
| **`WARIANTY.md`** | **Game variant modules**: fan decks (Absol, Black Spectrum), single-card errata, custom components — step-by-step recipes and limitations. Data: `assets/config/variants.json`. | 🟢 living |
| **`PROJEKT_KARTY_STRATEGII.md`** | Strategy cards 1–8 design (`te` set, errata, primary/secondary) — implemented in `core/strategy_cards/`. | 🟡 reference |
| **`ARCHITEKTURA_PO_MIGRACJI.md`** | Code map: backend/frontend, `web-data` contract, endpoints. | 🟡 reference |
| **`specyfikacja_techniczna_i_architektura_systemu.md`** | Target vision + AI layer architecture. | 🟡 reference |
| **`PORT_ASYNCTI4_PLAN.md`** | Verdict: how we port AsyncTI4 features (layer A/B). | 🟤 archival¹ |
| **`plan_faza1_interaktywna_mapa.md`** | Phase 1 plan (digital board) — implemented. | 🟤 archival² |

¹ Content absorbed into `PLAN_PELNA_ROZGRYWKA.md`; kept for decision context.
² Phase 1 completed (God-Mode works); kept as a record of DoD and data findings.

> **Currency rule:** when a document and the CODE disagree — **code wins**. Reference (🟡)
> and archival (🟤) documents may contain outdated details; living (🟢) docs
> are kept up to date. Always verify against `src/` and tests.

---

## 3. Repository Structure (where everything is)

```
Pax Magnifica/
├── README.md                     # install/run instructions (for humans)
├── docs/                         # DOCUMENTATION (this directory) — see table above
├── src/                          # BACKEND (Python / FastAPI) — source of truth for state
│   ├── core/                     #   core: state, data registry, map, rules engine
│   │   ├── registry.py           #     StaticDataRegistry — loads data from assets/ by `source` (+ catalog)
│   │   ├── models.py             #     static models (UnitDef, PlanetDef, FactionDef, ...)
│   │   ├── sources.py            #     canonical source priority and validation (SOURCE_PRIORITY)
│   │   ├── components.py         #     ComponentCatalog: category models + CATEGORY_SPECS + ComponentCatalog
│   │   ├── component_loader.py   #     loading/selecting entries by `source` (select_entries, LoadReport)
│   │   ├── references.py         #     reference integrity (factions, decks, attachments)
│   │   ├── timing_spec.py        #     TimingSpec: parse_timing + TRIGGER_WINDOW_MAP (D10)
│   │   ├── effects_registry.py   #     EffectRegistry: component id -> status (not/impl/manual)
│   │   ├── rules_links.py        #     linking components to RulesDump topics (INDEX)
│   │   ├── game_state.py         #     GameState / PlayerState / SystemState (+ clone)
│   │   ├── hex_grid.py           #     hex grid (q,r,s), adjacency, wormholes, anomalies
│   │   ├── map_string.py         #     AsyncTI4 map string parser -> HexGrid
│   │   ├── positions.py          #     RPP positions (101, 201, ...) -> coordinates
│   │   ├── unit_catalog.py       #     explicit unit rule tables (placement, asyncId, limits)
│   │   ├── faction_setup.py      #     faction setup (startingFleet parser, placement)
│   │   ├── turn_flow.py          #     E1: phases + turn order (pure functions)
│   │   ├── strategy_phase.py     #     E2: strategy phase (card selection, trade goods)
│   │   ├── timing.py             #     timing windows (respondent queue) — RULES.md 29.2
│   │   ├── event_store.py        #     EventStore (SQLite) — Undo/Redo/God-Mode
│   │   ├── economy.py, command_tokens.py, exhaust.py, control.py, unit_ops.py  # central points (RULES.md 43.1a)
│   │   ├── secret_objectives.py, promissory_notes.py, relic_fragments.py, card_draw.py  # cards/resources (C9)
│   │   ├── rules_hooks.py        #     hook registry, card effects, and choice descriptors (RULES.md 43)
│   │   ├── hooks/                #     exceptions by topic: factions, technologies, action card effects + forms
│   │   ├── action_cards.py       #     playing action cards: form, playability, effect (RULES.md 53)
│   │   ├── reaction_cards.py, card_hold.py, hold_rewind.py  # window reactions, Sabotage, HOLD (53.5–53.7)
│   │   ├── strategy_cards/       #     strategy cards 1–8: module per card (CardSpec)
│   │   ├── tactical.py, movement.py, combat.py, battle.py, invasion.py, production.py  # tactical action
│   │   ├── relics.py, relic_*.py, exploration*.py, frontier_cards.py, objectives*.py  # relics, exploration, objectives
│   │   ├── game_events.py, triggers.py, active_effects.py  # events and timing windows (RULES.md 54)
│   │   ├── actor.py              #     who can perform an action (actor_id, RULES.md 44.1a)
│   │   ├── game_clock.py         #     chess clock (RULES.md 58)
│   │   └── agenda_phase.py       #     agenda phase: voting, tie-breaking, laws (RULES.md 51)
│   ├── audit/                    #   DATA AUDITOR (CLI: `uv run python -m src.audit`)
│   │   ├── locality.py           #     LocalityGuard: reference paths, reads outside repo, URLs
│   │   ├── assets_manifest.py    #     image/font manifest (path+size+sha256), disk diff
│   │   ├── frontend_data.py      #     diff of bundled frontend data IDs vs Catalog (R11.5)
│   │   ├── diffs.py              #     count/set diffs, canonical source gaps (expected_gaps)
│   │   ├── report.py             #     AuditReport / build_report / render_text / exit_code
│   │   └── sync_assets.py        #     copying missing graphics from manifest (`--from <dir>`)
│   └── api/                      #   HTTP/WS layer
│       ├── app.py                #     FastAPI factory (router mounting) + WebSocket
│       ├── routers/              #     thin topic endpoints (game, board, components, ...)
│       │   └── components.py     #       /components, /components/{cat}/{id}, /timing-specs, faction bundle
│       ├── web_data.py           #     build_web_data: GameState -> document for frontend (UI CONTRACT); parts web_*.py
│       ├── schemas/              #     request/response DTOs (Pydantic), topic package
│       ├── seats.py, actor.py    #     networked multiplayer: lobby, seat tokens, identity (RULES.md 44)
│       ├── saves.py              #     saving games to file (saves/*.db), resume after restart
│       └── state_service.py      #     sole place mutating state (commit + broadcast)
├── frontend/                     # FRONTEND (React/Vite) — board viewer (based on ti4_web)
│   └── src/
│       ├── api/                  #   data hooks (useBoardEditor, useNewGame, ...)
│       ├── domains/              #   functional UI areas (map, player, game-shell, cards, ...)
│       ├── entities/             #   BUNDLED static data (units/planets/techs) + lookups
│       ├── shared/assets/        #   AssetResolver (assetUrl/sheetUrl) + assetManifest.json (local URLs)
│       ├── state/                #   store (Zustand) + game context
│       └── ds/                   #   design system (base components)
│   └── e2e/                      #   Playwright E2E tests (*.e2e.ts)
├── scripts/                      # tools (e2e_server.py, kiro_memories.py, ...)
├── tests/                        # BACKEND TESTS (pytest) — one file per core/api/audit module
├── audit/                        # AUDITOR CONFIG (in repo — D1/D12): image manifest, count baseline,
│   │                             #   gap exceptions, URL allowlist, unused assets/ dirs
│   ├── assets_manifest.json      #   manifest of required graphics/fonts (graphics outside repo — D1)
│   └── baseline_counts.json      #   reference entry counts (regression test)
├── assets/                       # GAME DATA (AsyncTI4): JSON in repo (~5 MB), graphics OUTSIDE repo (D1)
│   ├── enabled_sources.json      #   active data sources (base, pok, codex1-4, thunders_edge)
│   ├── config/effects_status.json #  EffectRegistry (in repo); engine_config.json; rest ignored
│   ├── data/ systems/ planets/ alias/   # engine data (versioned)
│   └── ... (graphics/fonts — outside repo, locally via manifest + sync_assets; see .gitignore)
└── TI4_map_generator_bot/        # REFERENCE SOURCE (Java, outside repo) — read-only, never link
```

---

## 4. How We Work (conventions — summary; full rules in steering)

- **Zero TI4 rules from memory.** Numeric data from `assets/` via `StaticDataRegistry`.
  Mechanical rules go into `RULES.md` first with a source (LRR / AsyncTI4 bot), then code.
- **Work in blocks.** One block = one coherent, testable step = commit in English.
- **QA after every change — all green before commit:**
  - backend: `uv run pytest -q -n auto` ; `uv run ruff check src tests` ; `uv run mypy src tests`
  - during work: `uv run pytest -q --testmon` (only tests affected by changes; `.testmondata` db,
    gitignored). `-n auto` = parallel on all cores (full suite ~20 s instead of ~70 s).
  - frontend (in `frontend/`): `npx tsc --noEmit -p tsconfig.app.json` (NOTE: `npm run type-check` does NOT
    check `src/`) ; `npm run lint` ; `npm run build` ; `npx vitest --run`
  - E2E (Playwright, in `frontend/`): `npm run e2e` (headless) / `npm run e2e:ui` (step viewer).
    Playwright spins up its own backend :8100 (`scripts/e2e_server.py`, in-memory) and frontend :5273,
    so the game on :8000/:5173 and `saves/` are untouched. Scenarios: `frontend/e2e/*.e2e.ts`
    (solo game with setup; networked game host + guest in two browsers). On failure:
    `npx playwright show-report` (screenshot, video, trace). New test: `npx playwright codegen localhost:5273`.
- **Documentation and comments in English.** Stage specific files (no `git add .`).
  Do not push (`git push`) without consent.
- **Everything local (offline).** Frontend loads graphics and fonts exclusively locally
  (AssetResolver `frontend/src/shared/assets/resolveAsset.ts`, `@fontsource/*` fonts) —
  no CDN. Graphics/fonts are OUTSIDE the repo (D1); manifest `audit/assets_manifest.json`
  describes the required set, and `uv run python -m src.audit sync_assets --from <dir>`
  copies them locally. Data consistency and locality are checked by the Data Auditor:
  `uv run python -m src.audit` (entry counts, references, external URLs, missing files).
- **Code > doc.** When in doubt, check `src/` and tests, not memory or prose.

---

## 4a. How to Use ComponentCatalog (for upcoming sessions)

Need an action card, agenda, objective, token, deck, promissory note, etc.?
**Read from `registry.catalog` (`ComponentCatalog`) — DO NOT write your own JSON parser
and DO NOT hardcode lists.** The catalog is already built in `StaticDataRegistry` (filtered by
`source` field, deduplicated by source priority).

```python
from src.core.components import ComponentCategory, ComponentRef

catalog = registry.catalog
cards = catalog.all(ComponentCategory.ACTION_CARD)      # dict id -> model
agenda = catalog.get(ComponentCategory.AGENDA, "censure")  # single model or None
bundle = catalog.faction_bundle("arborec")               # faction leaders/tech/promissory/…
refs = catalog.query_timing(trigger, phase)              # components by timing window
```

- **Canonical (official) sources** are defined EXCLUSIVELY by `src/core/sources.py`
  (`SOURCE_PRIORITY`). Import from there — do not paste `base/pok/codex1-4/thunders_edge`.
- **Via API (read-only):** `GET /components`, `/components/{category}`,
  `/components/{category}/{id}`, `/components/factions/{id}/bundle`, `/timing-specs`.
- **Guarantees:** filtered by `source` field (only active/official sources, not by filename);
  count regression test (`audit/baseline_counts.json`); anti-hardcoding test
  (`tests/test_no_hardcoded_data_guard.py`) — prevents bypassing the registry
  with a custom loader or duplicating the source list.

---

## 5. Reading Order at Session Start

1. This `README.md` — orientation (goal + where everything is).
2. `PROGRESS.md` — what was recently done and what's next.
3. `PLAN_PELNA_ROZGRYWKA.md` — which engine stage we are currently on.
4. `RULES.md` — before touching a mechanic, check/record the rule.
5. Real code in `src/` + tests — ultimate source of truth for current state.
