# Code Architecture — Layers, Conventions, Scaling Without Chaos

🟢 **LIVING.** This document answers: *"where does a new feature go, and how do we avoid
drowning the project in complexity once the tactical engine and AI arrive?"*. Twilight is a game
where almost everything breaks the base rules (factions, technologies, cards) — the architecture
MUST anticipate this. Follow these rules for every new mechanic.

---

## 1. Golden Rule: Rules in `core/`, HTTP in `api/`, Decisions in `engine/`

Three layers, strictly separated. **Dependencies flow in one direction only:**

```
  api/  (HTTP/WS) ───►  engine/  (bot — src/engine/, plan: docs/bot/PLAN.md)
     \                   /
      \                 /
       ▼               ▼
         core/  (game rules — pure functions over GameState)
                         │
                         ▼
              registry / assets  (data, zero rules)
```

- **`core/` DOES NOT KNOW HTTP exists.** No FastAPI imports, no `HTTPException`,
  no requests. Pure functions: `state -> new state` (or result / domain exception).
- **`api/` is thin.** Endpoint = (1) read state, (2) call function from `core/`,
  (3) commit + broadcast, (4) map domain errors to HTTP. **Zero game rules in endpoints.**
- **`engine/` (bot, `src/engine/`) calls `core/` exclusively** (never `api/`; `api/` runs the bot).
  Layer instructions: `src/engine/CLAUDE.md`. The bot generates an action → `core/` validates
  and applies it. The exact same functions `api/` uses. Thus bot and human
  play through a single rules path — they cannot diverge.

> **Litmus test:** if a new TI4 rule (movement, combat, faction ability)
> can ONLY be tested via `TestClient`/HTTP — it is in the wrong place. A rule must
> be testable as `function(state, args) -> state` without a network.

---

## 2. Map: Where Each Kind of Code Goes

| Kind of code | Directory / file | Examples |
|---|---|---|
| Game state (model) | `core/game_state.py` | `GameState`, `PlayerState`, `SystemState` |
| Static data (model) | `core/models.py` | `UnitDef`, `FactionDef`, `StrategyCardDef` |
| Data loading | `core/registry.py` | `StaticDataRegistry`, `strategy_card_set()`, `catalog` |
| Canonical sources | `core/sources.py` | `SOURCE_PRIORITY`, `validate_enabled_sources` |
| **ComponentCatalog** | `core/components.py` | category models, `CATEGORY_SPECS`, `ComponentCatalog` |
| Component loading | `core/component_loader.py` | `select_entries`, `load_components`, `LoadReport` |
| Reference integrity | `core/references.py` | `find_unresolved_references`, `ReferenceReport` |
| TimingSpec | `core/timing_spec.py` | `parse_timing`, `TRIGGER_WINDOW_MAP` (D10) |
| EffectRegistry | `core/effects_registry.py` | `EffectStatus`, `EffectRegistry`, `coverage` |
| Rules links | `core/rules_links.py` | `RulesTopicIndex`, `match` (RulesDump) |
| Unit rule tables | `core/unit_catalog.py` | placement, asyncId, limits |
| **Phase/action rules** | `core/<phase>.py` | `turn_flow.py`, `strategy_phase.py`, `tactical.py`, `movement.py`, `combat.py`, `production.py`, `strategic_action.py` |
| Timing windows | `core/timing.py` | respondent queue (RULES.md 29.2) |
| Setup / map | `core/faction_setup.py`, `core/map_string.py`, `core/hex_grid.py` | |
| History / Undo | `core/event_store.py` | |
| **DataAuditor / locality** | `src/audit/` | `locality.py`, `assets_manifest.py`, `frontend_data.py`, `diffs.py`, `report.py`, `sync_assets.py` (CLI `python -m src.audit`) |
| UI serialization | `api/web_data.py` | `build_web_data` (frontend contract); parts: `web_game` (round state) → `web_tiles` (tiles) → `web_player_units` → `web_players` (+ `web_agenda`, `web_objectives`, `web_points`, `web_setup`) |
| HTTP/WS endpoints | `api/routers/<topic>.py` | (post-refactor — see §4) |
| Request/response DTOs | `api/schemas/` package (`common`, `setup`, `tactical`, `combat`, `cards`; always import `src.api.schemas`), `api/schemas_components.py` | |
| Mutation + broadcast | `api/state_service.py` | sole place committing state |
| Bot decisions | `src/engine/` (plan: `docs/bot/PLAN.md`) | strategic → operational → tactical |

**Rule for adding a new mechanic (e.g. tactical phase E3):**
1. Write the rule into `docs/RULES.md` with a source (LRR / AsyncTI4 bot).
2. Implement as pure functions in `core/tactical.py` (+ unit test without HTTP).
3. Add a thin endpoint in `api/routers/tactical.py` that calls those functions.
4. If needed — add fields to web-data in `api/web_data.py`.
5. QA + commit.

---

## 3. How Twilight "Breaks the Rules" — The Hook Pattern (key for factions/tech/cards)

Almost every faction, technology, and card modifies the base rules (different movement, extra
hits, free production…). If we wove these exceptions into `if faction == ...` inside the rules
code, `core/` would become unreadable after 10 factions. Therefore:

- **Base rule** in `core/` computes the "vanilla" game result (e.g. movement value, hit count).
- **Modifiers** (faction abilities, technologies, cards, laws) are **hooks** registered
  in one place (`core/rules_hooks.py`, DONE) that the base rule queries at
  defined **hook points** (movement, combat, production, payment…).
- **Where things live:** registry and API (`forbidden` / `permits` / `modify`, order REPLACE>FORBID>
  PERMIT>MODIFY>TRIGGER>PERSISTENT) in `core/rules_hooks.py`; exceptions themselves by topic in package
  `core/hooks/` (`factions/<faction>.py`, `technologies.py`; add and import new ones in
  `hooks/__init__.py`). Hook point names are `POINT_*` constants in `rules_hooks.py`. A hook fires only for
  the player who owns its source (faction/technology). `covers="<category>:<id>"` marks
  the component as IMPLEMENTED in the effects registry; report: `docs/POKRYCIE_HOOKOW.md` (generated:
  `uv run python -m src.audit.hook_coverage --write`).
- **New exception (recipe):** RULES.md (component + source) -> function in `core/hooks/<topic>.py`
  with `@register(POINT_*, HookSource(...), HookKind.*, covers=...)` -> test as a "without/with
  exception" pair (`rules_hooks.temporary_hooks()`) -> regenerate coverage report.
- The hook receives context (`state`, `player`, `system`) and returns a modifier/decision. A new
  faction = a new hook file + entry in `RULES.md` + test. **Zero changes to the base rule.**

> This is the architectural answer to "Twilight breaks its own rules". The base rule
> stays simple and stable; all asymmetry lives in isolated, testable hooks.
> Details and list of 30 factions: `PLAN_PELNA_ROZGRYWKA.md` ("Factions" section).

---

## 3a. Card from A to Z (mandatory recipe; goal: ALL cards ready)

Every card goes through the same pipeline, so adding another is one entry per layer without touching base rules:

| Layer | File | What it does |
|---|---|---|
| Data | `assets/data/...` | card text and timing window (never from memory); `timing_spec` classifies the trigger |
| Rule | `docs/RULES.md` (+ `rules_tirules/`) | entry with source, ⚠ on assumptions |
| Effect | `core/hooks/action_cards*.py` → `@register_effect("action_cards:<id>")` | mutates state only through central points |
| Inputs | `core/hooks/action_card_inputs.py` → `@register_effect_inputs(...)` | form descriptor: `choice` / `multi` / `number`, options computed by engine |
| Playability | `core/action_cards.playability` | turn, phase, window, one action, legal targets |
| API | `api/routers/action_cards.py` | `GET /action-card/playable`, `GET /action-card/{id}/inputs`, `POST /action-card/play` |
| UI | `BottomHandDock` (drag), `ActionCardPlayModal` (form) | frontend doesn't know cards, renders descriptor from engine |
| Tests | `tests/test_action_cards.py` | without/with effect pair, form round-trip, errors |
| Report | `docs/POKRYCIE_HOOKOW.md` | `uv run python -m src.audit.hook_coverage --write` |
| Reaction (when/after/before/start/end) | `core/reaction_cards.py` + `core/hooks/reactions_*.py` | window COMPUTED from state (`@window_provider`), address from window text (`declare_reaction` overrides), card condition; effect as above, window in `params["__window"]`; persistent effect = `active_effects` + `card_effect_source` hook; reaction card does not consume an action (RULES.md 53.5) |
| Dice | `dice.record_table_roll(...)` in effect | **EVERY dice roll** (card, relic, breakthrough…) is recorded with this call, and UI replays it with physical dice (see 3a.1) |

**UX rule:** a card is played by dragging it from hand, and only a card the engine allows to play
(`playability`) can be picked up. Other card types (reactions, promissory notes) get the same standard — see "PRODUCT GOAL"
in `PLAN_PELNA_ROZGRYWKA.md`.

### 3a.1. Dice Rolls: ONE Physical Dice Stage (applies everywhere)

Dice in the game are physical (d10, 3D mesh, bounces, sound), and the result is always computed by the engine (`core/dice.py`, seedable
RNG); the UI only replays it. **A new dice roll DOES NOT get its own animation or its own "dice banner"** — it uses
the shared stage:

| Situation | Backend | Frontend |
|---|---|---|
| Out-of-combat roll (action card, relic, breakthrough, Fracture) | after rolling `dice.record_table_roll(state, player_id, kind, label, results, hits_on=… or hit_values=…, summary=…)` | nothing: `TableRollWatcher` (mounted in `GameMapPage`) rolls the dice itself, and after landing shows `summary` |
| Window with roll button (Space Cannon, bombardment, SCD) | roll in `core/` as before, result in log/`pending` | button = `HoldRollButton` + `onHold={soloHold(num_dice, rgb)}` (pool while holding); new result → `useDiceStage.getState().throwDice({...})`, and returned `pauseMs` = time until which **we do not reveal the result** in UI |
| Combat (AFB / round roll) | as before | built-in table in `BattleOverlay` (`DiceTray`, `DicePool`) — does not use the shared stage |

Files: `frontend/src/domains/dice/` (`diceStage.ts`, `DiceStageHost.tsx`, `HoldRollButton.tsx`, `TableRollWatcher.tsx`),
`frontend/src/domains/battle/` (`diceRoll.ts` plan & physics, `dieGeometry.ts` d10 mesh, `DieMesh.tsx`, `DiceTray.tsx`,
`DicePool.tsx`). Everything that depends on the result (hits, hit assignment panel, effect volleys) starts after `pauseMs`.

---

## 3b. Event Hook (timing windows) — RULES.md 54

1. Find the component's window in `docs/OKNA_CZASOWE.md` (event + moment).
2. Register: `@rules_hooks.on_event(GameEvent.X, Moment.WHEN, HookSource(...), kind=HookKind.TRIGGER|REPLACE, optional=True/False)` in `core/hooks/<topic>.py`.
3. If the event is not emitted (`EVENT_INFO.emitted_by is None`) — add `triggers.fire(...)` in the appropriate `core/` function and fill in `emitted_by` (`test_emitted_by_zgadza_sie_z_kodem` enforces consistency).
4. Timed effect: `active_effects.add_effect(state, key, scope, owner)`; expiry via `triggers.EXPIRY`.
5. Cards in hand are not hook sources (STOP, 43.4) — played through the ACTION window.

## 4. API Layer Structure (post-refactor before E3) — ✅ paid off

`app.py` is now a THIN factory (mounting routers + WebSocket + static, ~100 lines).
Endpoints grouped by topic in `api/routers/`, God-Mode logic in `core/board_edit.py`.

| File | Lines | Role |
|---|---|---|
| `core/board_edit.py` | ~300 | **Pure God-Mode functions** (editing units/planets/control/player). Zero HTTP — ready for AI. |
| `api/app.py` | ~100 | Factory: router mounting, WebSocket `/ws`, static, CORS, lifespan. |
| `api/context.py` | ~45 | `AppContext` (service/manager/registry/current_grid) + `broadcast_map`; `get_ctx` dependency. |
| `api/serializers.py` | ~130 | `build_map_view` + setup constants (`DEFAULT_MAP_STRING`, `AUTO_SLOT_ORDER`). |
| `api/routers/game.py` | ~190 | state, map, web-data, factions, new game, load map, player setup. |
| `api/routers/board.py` | ~108 | units in space/on planets, editing, movement (calls `core.board_edit`). |
| `api/routers/players.py` | ~34 | player editing. |
| `api/routers/flow.py` | ~61 | turns/phases/round (E1). |
| `api/routers/strategy.py` | ~86 | card pool, pick, play (E2). |
| `api/routers/components.py` | — | **read-only** ComponentCatalog: `/components`, `/components/{cat}`, `/components/{cat}/{id}` (component + `TimingSpec` + effect status + rules topics), `/components/factions/{id}/bundle`, `/timing-specs?trigger=&phase=`. No `broadcast`; 404 with category and id. |
| `api/routers/history.py` | ~76 | God-Mode patch, PUT state, history, undo/redo. |

> **Status 2026-11-11:** the table above is from the refactor; today there are 32 routers — one per topic:
> `tactical`, `battle`, `invasion`, `space_cannon`, `production`, `capacity`, `fleet_pool`, `status`, `agenda`,
> `action_cards`, `hold`, `window`, `offers`, `relics`, `exploration`, `frontier_cards`, `technology`, `decks`,
> `transactions`, `thunders_edge`, `epilogue`, `clock`, `network`, `setup`, `rules` (+ those listed above).
> Router pattern unchanged; adds `actor: ActorId` or `dependencies=[HostOnly]` (RULES.md 44.1a).

**Router pattern (stick to it for E3):**
```python
@router.post("/path", response_model=...)
async def handler(request: XRequest, ctx: AppContext = Depends(get_ctx)) -> ...:
    try:
        new_state = core_module.function(ctx.service.current_state(), ctx.current_grid, ...)
    except ValueError as exc:                 # domain error from core/
        raise HTTPException(422, str(exc)) from exc
    ctx.service.replace_state(new_state, label="...")   # commit → history
    await ctx.service.broadcast(); await ctx.broadcast_map()
    return ctx.service.envelope()
```

**Splitting large modules (2026-11-19):** layers depend downward only, and the base module re-exports
names (`from x import n as n`, mypy strict), so calls like `battle.side_units` etc. do not change.
`core/battle_units.py` → `battle.py` → `battle_rerolls.py` (rerolls/post-roll die modifications);
`core/invasion_common.py` → `invasion_bombard.py` / `invasion_defense.py` → `invasion.py`;
`core/movement_paths.py` → `movement.py`. Frontend: `api/boardQueries.ts` (read-only queries,
re-exported via `useBoardEditor.ts`), `battle/BattleVolley.tsx` and `BattleAssaultCannon.tsx`
(`BattleOverlay` animation layers). Tests mocking a function (`monkeypatch.setattr(mod, ...)`)
must target the module that CALLS it.
For E3 we add `core/tactical.py` + `api/routers/tactical.py`.

---

## 4a. Data Foundation and DataAuditor (spec local-ti4-data-foundation)

A separate layer that FEEDS `core/` with complete TI4 data and enforces locality. Follows
the same rule as the rest: logic is pure functions, I/O is thin, zero rules from memory.

- **ComponentCatalog (`core/components.py`).** Single place with typed models
  for ALL TI4 categories (action cards, agendas, objectives, attachments, explorations, relics,
  promissory notes, tokens, frontier anomalies, events, generic cards, decks + existing
  units/planets/factions/techs/leaders). JSON shapes live ONLY in `CATEGORY_SPECS` —
  zero hardcoded components. Extra fields outside the model land in `raw` (nothing is lost, R5.7).
- **Selection by `source` (`core/component_loader.py`, `core/sources.py`).** Filter by the
  `source` FIELD (not by filename) per `assets/enabled_sources.json`; `id` collisions are resolved
  by source priority `thunders_edge > pok > codex4..1 > base` (D9, RULES.md 14). `LoadReport`
  counts skipped / sourceless entries.
- **TimingSpec (`core/timing_spec.py`).** `parse_timing` classifies the window phrase
  (`when/after/before/instead/...`) by prefix while preserving the original text; `TRIGGER_WINDOW_MAP`
  (D10, `⚠️ ASSUMPTION` in RULES.md) binds the kind to `WindowType` from `core/game_state.py`. For future
  when/after reactions on the window model (RULES.md 29.2).
- **EffectRegistry (`core/effects_registry.py`).** `component id -> status` (`not_implemented`
  / `implemented` / `manual`), data in `assets/config/effects_status.json`. For hooks from RULES.md 29;
  by ITSELF it encodes no card effect (those are future hooks, see §3).
- **Rules links (`core/rules_links.py`).** Deterministic (normalized name/alias equality,
  no guessing) linking of a component to RulesDump topics (`docs/rules_tirules/`).
  Rule + clarification → RulesDump; card text/parameters → JSON in `assets/data/`.
- **DataAuditor (`src/audit/`).** CLI `uv run python -m src.audit` (text report; `--json`,
  `--write-baseline`, `--write-manifest`). Counts entries per category×source, detects unresolved
  references, `unclassified` timing, external URLs, missing/unused graphics from the manifest.
  `locality.py` = LocalityGuard (no reads outside `PROJECT_ROOT`, no paths to
  Reference Sources in code). Critical error → non-zero exit code.
- **Graphics/fonts locality (D1).** Graphics and fonts are OUTSIDE the repo; `audit/assets_manifest.json`
  (in repo) describes the required set, and `src/audit/sync_assets.py --from <dir>` copies them
  locally. Frontend fetches them via AssetResolver (`frontend/src/shared/assets/resolveAsset.ts`,
  `assetManifest.json`) — zero CDN. Auditor config and count baseline are versioned
  (`audit/*.json`, D1/D12 — see `.gitignore`).

---

## 5. Checklist for Every New Feature (stick to it)

- [ ] TI4 rule? → first an entry in `RULES.md` with a source, then code.
- [ ] Game logic goes into `core/` as a pure function (testable without HTTP).
- [ ] Endpoint in `api/` only calls `core/` + commit/broadcast + maps errors.
- [ ] Domain exception (`ValueError`/custom) in `core/`, mapped to HTTP in `api/`.
- [ ] Faction/tech/card modifier = hook, not `if` in the base rule.
- [ ] New card = full pipeline from section 3a (effect + form + playability + test + coverage report).
- [ ] New VISIBLE effect (new resource/component/player or table state)? → add it to the
      "Activity" feed (history panel): fact in `core/activity.py` (`_facts` and subfunctions, state diff
      before/after; hands as COUNTS only) + description in `ActivityPanel/describeActivity.tsx` (`describeFact`)
      + test in `tests/test_activity.py`. New action with its own commit label => also `_parse_*`.
- [ ] Tests: unit test for `core/`, integration test (`TestClient`) for the endpoint.
- [ ] File already covers multiple topics (usually > ~500 lines)? → consider splitting into a topic submodule. Don't split a cohesive module just for line count.
- [ ] QA green (pytest/ruff/mypy + frontend build) → commit in English.
