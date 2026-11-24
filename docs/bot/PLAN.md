# AI Bot — Engine Audit & Work Plan (Short Branches)

Status (2026-11-16): B0, B1, B3 done, B2 — core; rest is PLAN. Stage 3 of the project (`docs/README.md` §1).
Bot design rules: `docs/rules/R65.md`. Claude instructions: `src/engine/CLAUDE.md`.
Layer vision (strategic / operational / tactical / diplomacy): `specyfikacja_techniczna_i_architektura_systemu.md` §4.
This file is LIVING: after every bot block, update the tables in §2 and §5.

**User decision (2026-11-16):** the bot will use several separate, complex computational
algorithms, computed LOCALLY (on the host machine, no cloud). The architecture (§4) must support this
from the start: common algorithm interface, separate processes, time budget, comparing algorithms in an arena.

---

## 1. Rules (summary; full in `docs/rules/R65.md`)

1. **The bot plays through the same rules path as a human** — every move via `core/` functions (Referee, RULES 29).
2. **The bot does not cheat** — decides on `visibility.project_strict(state, bot_id)`; hidden info is sampled.
3. **The game never waits on a bot forever** — time budget + safe default move.
4. **Algorithm = swappable module** behind one interface; which algorithm for which decision lives in config.
5. **Heavy compute outside the server loop** — worker processes; the game server never freezes.
6. **Determinism** — same projection + same seed + same iteration budget = same decision.

---

## 2. Audit: What the Engine Already Gives the Bot (as of 2026-11-16)

| Bot need | Status | Where | Notes / what to add |
|---|---|---|---|
| Who has a move now & what kind | ✅ | `core/actor.awaiting(state)` | Codes `respond/decide/assign_hits/combat/invasion/explore/strategy/turn/speaker/secret/setup` — ready-made bot "dispatcher". |
| Actor permissions | ✅ | `core/actor.require/subject` | Bot acts as `actor_id = its player_id`; same 403s as a human. |
| Cheat-free view | ✅ | `core/visibility.project_strict` | Hides hands, secret objectives, `rng_seed`. |
| Seedable RNG | ✅ | `core/dice.roll_dice/next_rng` | Seed + counter in state. Projection has `rng_seed=0` → in simulation the seed is set by the algorithm (otherwise `secrets` = non-determinism). |
| State cloning | 🟡 | `GameState.clone()` | Measured: **0.40 ms** (6 players, round 2, ~23 KB JSON; `model_copy(deep)` 0.78 ms, `deepcopy` 0.60 ms). Enough for heuristics and shallow lookahead; too slow for Monte Carlo / MCTS with thousands of simulations → fast representation (B6). |
| Map | 🟡 | `core/hex_grid.HexGrid` | Topology OUTSIDE `GameState` (units are in state). Simulation needs `(state, grid)` pair; grid to worker process via `to_placements()`. |
| Bot settings | ✅ | `PlayerState.control_type/difficulty/personality`, `assets/config/engine_config.json` | Values are `⚠️ ASSUMPTION`s. |
| "Bot" decisions inside `core/` | ⚠️ | `core/transaction.bot_accepts`, `core/epilogue._bot_choice`, `core/transaction_table`, `core/game_setup.begin_setup` (random bot secret objective), bot auto-pass in reaction windows (`core/reaction_window`) | Decision placeholders in the rules layer. Move to `src/engine/` (B10). Auto-pass in reaction windows can stay (engine knows hands; "nothing to play" pass applies to humans too). |
| Action catalog | 🟡 B1 | `src/engine/actions.py` | 31 kinds (setup, strategy with primary steps, turn, windows, offers, hit assignment, status, agenda, speaker announcements, hand limit, fixed-length windows, `production_skip` = "Finish production" after card production, `fleet_pool_resolve` = FLEET_POOL window). `apply_and_settle` = action + `core/step_settle` (exactly like commit). Movement, production, invasion, action cards: B5. |
| Legal move generator | 🟡 B1 | `src/engine/legal.py` + `src/engine/observation.py` | B1 scope (no tactical action of its own); first candidate = safe default move. Observation = strict projection + own prompts (`step_options`, `offers_view`), i.e. the same thing a human client receives. |
| Bot trigger | ✅ B3 | `src/api/bot_runner.py` | Loop in server lifespan, woken after broadcast and every 1 s; queries `legal_actions` of EVERY bot (parallel decisions). Move = same HTTP request as a human (`api/bot_http.py`, in-process ASGI). `--no-bots` disables. Missing: admin fast toggle (delay 0) from UI. |
| Rules logic outside `core/` | ✅ B1 | `core/phase_flow.py`, `core/step_settle.py` | Found in B1 and moved to `core/`: phase-closing choice in `/phase/next` (+ `/round/next`) router and "after every step" rules in `StateService.replace_state`. Middleware releasing expired pause before every POST stays in `api/` (bot has `reaction_pause_release` action). |
| Determinism | ✅ B1 | `core/game_setup` | Bug found by parity test: secret objective choice shuffled with unseeded `random.Random()`, now `next_rng(state)`. Game creation still uses entropy (match start). |
| Timing windows & bot | ✅ | `engine/legal._window` | Removed generic `/window/respond` (+ `window_respond` action): it bypassed mandatory window decisions and didn't close a fulfilled window (game stalled). In `COMBAT_ASSIGN_HITS` window, bot now gets `battle_assign` (previously generic "OK" = skipped hits). FLEET_POOL: `fleet_pool_resolve` with `core/fleet_pool.auto_removal` hint. SPACE_CANNON / COMBAT_RETREAT / CAPACITY: no bot move until B5 (`tests/engine/test_legal_windows.py`). |
| Compute infrastructure | 🟡 B2 | `src/engine/compute.py`, `BotConfig` in `engine_config.json` | `DecisionRequest/Result`, algorithm registry (`first`, `random`), inline/process `Executor` with deadline and default move, `state_seq` invalidation (runner). Missing: `bench.py`, "anytime" result from process (currently only default move on timeout), data registry init in worker process. |
| Game fuzzer | 🟡 | `tests/engine/fuzz.py` (`python -m tests.engine.fuzz --games N`), smoke `tests/engine/test_fuzz_games.py` | Random games via API: random factions (3–6, one variant per family), random bot, random player order, 50% with agenda. After each move: catalog ↔ HTTP parity, invariants (`check_invariants`: no negative TG/tokens/VP, commodities ≤ value, active player in action phase, JSON round-trip), and web-data for each player. Failure = JSON with seed, recent actions, and state snapshot. Generator gaps found (fixed): production from Construction and Warfare secondary, mandatory tech choice from Research Grant Reallocation, FLEET_POOL window. Scope = generator scope: no tactical action, combat, or action cards until B5. |
| Concurrency | ⬜ | N4 in `PLAN_PELNA_ROZGRYWKA.md` | No per-game lock; bot runner must serialize with human requests. |
| Time | ✅ | `core/game_clock.py`, `create_app(now=...)` | Injected `now` — also for bot budget. |
| Activity feed | ✅ | `core/activity.py` | Bot moves visible like human moves; commit labels `bot:<kind>`. |
| Hardware / environment | ℹ️ | host machine | Python 3.14, 12 logical cores, NumPy ≥ 2.5. No Numba (and uncertain 3.14 support) — dependency decision in B6. |

---

## 3. Algorithms — 4-Layer Architecture (user vision 2026-11-16)

Every algorithm is a separate module with its own `bot/alg-<name>` branch, tests, and arena result,
registered in `engine/compute` (`register_algorithm`) and assigned in `engine_config.json`.
No neural networks, PyTorch, or GPU (RL/self-play would require a full fast simulator of all of TI4).
LLM for chat/negotiations — possibly at the very end, outside game logic.

| Layer | Algorithms | Decisions | Libraries (⚠️ dependency = approval + `bench.py` measurement) |
|---|---|---|---|
| 1. Strategic (VP Solver) | MIP/ILP, CP-SAT | which planets to exhaust (resources/influence) for objectives; production as knapsack (fleet power within resource and PRODUCTION limits) | Google OR-Tools |
| 2. Utility & Heuristics | Utility AI (0–1 curves), influence/threat maps, combat Monte Carlo | value of each action vs objectives and distance; win chance and losses before attacking (Sustain, AFB, modifiers) | NumPy (+ Numba `@njit`?) |
| 3. Operational (round order) | RHEA (short sequences of 4–6 macro-decisions, mutation/crossover) or macro-ISMCTS | when to play strategy card, when to pass, activation order | custom Python loop |
| 4. Tactical (logistics) | graph + Dijkstra/A* on hexes | real fleet reach (anomalies, Gravity Drive, Antimass, wormholes) | NetworkX / NumPy |
| (diplomacy) | heuristics | agenda votes, transactions | — |

**Claude notes on the vision (for decision on the relevant branch):**
1. **Layer 4 cannot compute range on its own.** Movement has full rules in `core/movement` (anomalies, technologies,
   factions, blockades). Dijkstra/A* runs over a graph built from a `core/` enumerator ("where can this ship
   legally fly"), not its own copy of the rules — otherwise bot and Referee will diverge. First step of
   B5: such an enumerator in `core/`.
2. **Combat Monte Carlo = separate, fast simulator with mandatory parity test against `core/battle`**
   (outcome distribution on the same seeds/sample). Numba: uncertain Python 3.14 support on this machine —
   first pure NumPy vectorization (10,000 battles < 50 ms is realistic without Numba), Numba only after measurement.
3. **OR-Tools is a heavy dependency** (native wheels, 3.14 support to be checked). Payment and production
   problems are small (a dozen planets, a few unit types) — exact dynamic programming /
   exhaustive search in pure Python gives the optimum in milliseconds. Proposal: start with DP, introduce OR-Tools
   when a problem appears that DP cannot handle (e.g. joint round plan).
4. **A shared state evaluation function** (Layer 2) is the foundation for Layers 1 and 3: RHEA/ISMCTS without good
   leaf evaluation plays randomly. Order: evaluation + combat Monte Carlo → movement enumerator → RHEA.
5. **RHEA/ISMCTS need a fast forward model** (`engine/fast`, B6) — `GameState.clone()` at 0.4 ms
   allows ~2,500 steps/s per core; at the macro level (4–6 decisions) it may suffice without B6. Measure.
6. **Missing opponent model** (what others will do this round) — RHEA should simulate rivals with at least
   a simple policy ("first"/utility bot), and sample hidden cards from the unseen pool (determinization, 65.2).

## 4. Target Architecture

```text
                    ┌──────────────────────── server process (FastAPI) ────────────────────────┐
 state commit ──►   │ api/bot_runner.py: awaiting ∋ BOT?                                       │
                    │   view = project_strict(state, bot)   legal = engine.legal_actions(...)  │
                    │   request = DecisionRequest(view, grid, legal, seed, budget, state_seq)  │
                    │   ──► engine.compute.Executor ──┐                                         │
                    │   ◄── DecisionResult ───────────┤ (stale state_seq? => result discarded) │
                    │   apply(action) via core/ ───► commit "bot:<kind>" + Activity            │
                    └─────────────────────────────────┼────────────────────────────────────────┘
                                                      ▼
                         worker processes (ProcessPoolExecutor, N = cores − 1)
                         initializer: StaticDataRegistry + NumPy tables once per process
                         algorithm.decide(request) — anytime: best result before deadline
```

- **`src/engine/actions/`** — discriminated union `Action` (Pydantic) + `apply(state, grid, registry, action)`,
  calling the EXACT same `core/` functions that routers call. Single mapping: live game and simulations.
- **`src/engine/legal.py`** — `legal_actions(view, grid, registry, player_id) -> list[Action]` for the current
  reason from `awaiting`; missing enumerators are added in `core/`.
- **`src/engine/compute/`** — compute infrastructure:
  - `DecisionRequest` / `DecisionResult` — serializable (picklable), with `state_seq`, seed, budget
    (`deadline_ms` and/or `max_iterations`), algorithm name, and parameters.
  - `Algorithm` (Protocol): `name`, `decide(request) -> DecisionResult`; module-level function (not a method
    on a server object) so it can be sent to a worker process.
  - `Executor`: `inline` mode (tests, deterministic arena) and `process` mode (live game, parallel bots).
    Hard deadline: on timeout — latest "anytime" result or default move.
  - Algorithm registry: `decision → algorithm + parameters` from `engine_config.json` (per difficulty/personality).
- **`src/engine/fast/`** (B6) — fast state representation for simulations (NumPy; Numba/other acceleration only
  after measurement and user approval of dependency). Converter `GameState → FastState` + parity test
  against `core/` on random positions (fast state MUST NOT have different rules from `core/`).
- **`src/engine/{strategic,operational,tactical,diplomacy}/`** — algorithms (existing directories).
- **`src/api/bot_runner.py`** — trigger in server process, per-game task queue, "human-paced" delay.
- **`src/engine/arena.py`** — headless games: bot vs bot, algorithm tournaments (A vs B on the same
  seeds and maps), metrics: wins, VP, time/move, iterations/s. Also an engine regression test.
- **`src/engine/bench.py`** — micro-benchmarks (clone, combat sim, move generator); outside `pytest -q`.

---

## 5. Short Branches (1–3 sessions each, merge to `main` after green QA)

Convention: `bot/<no>-<topic>` (infrastructure) and `bot/alg-<name>` (algorithms), always from current `main`;
before merge `git merge main` and QA. `core/` change needed by the bot = separate commit. Worktree only during
parallel work on the engine.

| Branch | Scope | DoD |
|---|---|---|
| ✅ `bot/b0-fundament` | This plan, `src/engine/CLAUDE.md`, `docs/rules/R65.md`, `ARCHITEKTURA_KODU.md` (`ai/`→`engine/`), `docs/README.md` index. | Docs consistent; zero code. |
| ✅ `bot/b1-katalog-akcji` | `Action` + `apply` for "don't stall the game" decisions: secret objective, Custodians/objective reveal, strategy card pick, pass / end turn, pass in window, decline "may", skip secondary, assign hits, agenda vote, status steps, hand limit discard. `legal_actions` for those reasons. | Catalog ↔ HTTP parity test for every action; guard "engine does not import api". **Result:** 3 scenarios (6 bots; 6 bots + agenda; 4 "humans" + agenda) play 2 full rounds without stalling, 0 HTTP divergences, 0 rejections of first candidate; same start + seed = same match. Uncovered (`NOT_YET_COVERED` list in `tests/engine/test_actions_parity.py`): `battle_assign`, `held_pass`, `held_release`, `offer_decline` → B5. |
| 🟡 `bot/b2-obliczenia` (core on `main` 2026-11-16) | `engine/compute`: `DecisionRequest/Result`, `Algorithm`, `Executor` inline + process, deadline and anytime result, `state_seq` invalidation, registry from `engine_config.json`, "default" algorithm (safe move). `engine/bench.py`. | Same request inline and in process → same decision; timeout → default move; server stays responsive during compute. |
| ✅ `bot/b3-runner` (on `main` 2026-11-16) | `api/bot_runner.py`: post-commit trigger, per-game queue, delay from settings (admin fast = 0), `bot:*` labels, Activity, discarding results after human Undo. | 1 human + 5 bots game completes full rounds without stalling (API test). |
| ⬜ `bot/b4-arena` | `python -m src.engine.arena`: headless games, algorithm tournaments on shared seeds, report (wins, VP, time/move). Smoke in `tests/engine/`. | Seeded arena deterministic (inline mode); 422 on a legal move ends the game with a report. |
| ⬜ `bot/b5-legalne-ruchy` | Tactical action generators (activation, movement, production, invasion), running combat (roll, AFB, retreat), secondary with choice, research, component actions, action cards; missing enumerators in `core/`; scenarios covering `NOT_YET_COVERED`. | Random bot plays 10 rounds in arena without 422. |
| ⬜ `bot/b6-szybki-stan` | `engine/fast`: fast representation and step simulator needed by algorithms (combat first); parity test with `core/`; decision on Numba/acceleration after measurement. | Target performance from benchmark (e.g. combat sims/s) recorded in this plan; 100% parity on random sample. |
| ⬜ `bot/alg-*` | Each algorithm from §3 separately: module + tests + config + arena result against previous bot version. | Algorithm wins (or doesn't lose) in arena vs version without it; fits within budget. |
| ⬜ `bot/b10-dyplomacja-core` | Move `bot_accepts`, `_bot_choice`, and random bot secret objective (`begin_setup`) from `core/` to `engine/` (core asks, engine answers). | `core/` contains no bot decisions. |
| ⬜ `bot/b11-trudnosc` | Levels and personalities = sets of algorithms + parameters + budgets in `engine_config.json`; window reactions. | Measurable level differences in arena. |

Dependencies: B3 requires simple per-game serialization (part of N4). From B5 onward, every new engine
mechanic should immediately get an entry in `legal_actions` (guard to consider in B5).

---

## 6. User Decisions

Made 2026-11-16 (details in `docs/rules/R65.md` 65.7):
1. Algorithms: 4-layer architecture (§3); no neural networks or GPU.
2. Bot in server process + worker processes (recommendation accepted).
3. Budget 2 s normal decision / 10 s key decision; cores: maximum (all minus one).
4. Pace "human-paced" 1–2 s, admin fast = 0.
5. Bot never undoes; after human Undo, recomputes from scratch.
6. Bot takeover for absent human — at the end of development.

Open: OR-Tools / Numba dependencies (§3, notes 2–3) — decide on the algorithm branch after measurement.
