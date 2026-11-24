# Plan: Full Twilight Imperium Gameplay on the Web

End goal (agreed with user): **ability to play a full game of TI4 in the app**
— not just mirroring state (God-Mode), but real phases, actions, combat, agenda, scoring.

## Baseline Findings (evidence-based)

- **The `ti4_web` frontend has NO action logic.** It is a viewer: the only POSTs are our additions
  (`useNewGame`, `useBoardEditor`); the original delegates actions to Discord via
  `actionsJumpLink`/`tableTalkJumpLink`. Confirmed by grep (no `useMutation`, no
  POST to bot outside ours).
- **Game logic lives in the Java bot** (`TI4_map_generator_bot/src/main/java/ti4/service/`):
  `turn/`, `strategycard/`, `tactical/`, `combat/`, `agenda/`, `status` (StatusCleanupService),
  `objectives/`, `leader/`, `tech/`, `explore/`, `transaction/`, `commodities/`, `planet/`,
  `relic/`, `abilities/`. Tangled with Discord (JDA buttons) — we use it as a RULES SOURCE.
- **Reusable from frontend:** display/picker components in `src/domains/cards/components/`
  (StrategyCardDetailsCard, StrategyCardSheet, TechCard, LeaderDetailsCard, PlanetDetailsCard,
  ObjectiveDetailsCard, UnitDetailsCard…), player/map panels, battle-calc builder.

## Principle

Every rule → first into `docs/RULES.md` with a source (Java bot / LRR), then implementation
in Python. Numeric data exclusively from assets via `StaticDataRegistry`. Every step:
code + tests + QA + commit; incrementally playable.

## Stages (ordered like Java packages)

### E1 — Phase Machine + Turn Order (foundation) ⬅ START
Source: `service/turn/` (StartTurn/EndTurn/Pass), `service/game/` (round).
- Model: `Phase` already exists; add phase transitions and initiative order (from `scs`).
- Endpoints: `POST /phase/next`, `POST /turn/end`, `POST /turn/pass`, `POST /round/next`.
- Rule: turn order by strategy card initiative; pass = player skipped until end of round;
  end of round when all have passed → status phase.
- UI: phase panel (exists) + "End turn / Pass / Next phase" buttons matching site style.
- DoD: can click through Strategy → Action (turns by initiative) → Status → Agenda → round+1.

### E2 — Strategy Phase (strategy card selection)
Source: `service/strategycard/` (PickStrategyCard, PlayStrategyCard, secondary/follow).
- Model: pool of 8 strategy cards (SpeakerOrder), per-player pick (`strategy_cards`), exhausted.
- Endpoints: `POST /strategy/pick`, `POST /strategy/play`, `POST /strategy/follow`.
- Rule: initiative from card number; primary/secondary; trade goods on unpicked cards.
- UI: card picker (SC components from frontend), played/exhausted indicator.
- DoD: strategy phase deals cards, sets initiative for the action phase.

### E3 — Tactical Action (activation → movement → space combat → invasion → production) ✅ DONE
Source: `service/tactical/` (TacticalAction* + movement/planet/postmovement), `service/combat/`.
- **⚠️ DECISION CHANGED (2026-10, see RULES.md 29):** originally the engine was a TABLE
  ASSISTANT (guided steps, did NOT validate rules). NEW DIRECTION: the engine is a REFEREE — it ENFORCES
  TI4 rules in code (since the AI bot has to know them anyway, and it's more convenient for the player). God-Mode
  remains as a separate manual correction channel (bypasses validation). Assistant-version E3 (blocks
  T1–T4) is the FOUNDATION — we build validation + timing windows on top of it (see stage E8 below).
- Step state machine (TacticalStep FSM): ACTIVATION → MOVEMENT → SPACE_CANNON → SPACE_COMBAT →
  INVASION → PRODUCTION. Activation places a command token (tactic pool), `active_system`.
- Combat (space/ground): assistant window with helpers (dice, hits on X+, expected hits
  from `UnitDef`); removing destroyed units via God-Mode. Invasion: establishing planet control.
  Production: cost helper (`UnitDef.cost` + available resources). Space cannon: FSM step without window.
- DoD: ✅ full sequence clickable step by step (activation → movement → combat → planet
  capture → production → end action).

### E4 — Component Actions + Strategic Secondaries
Source: `service/actioncard/`, `service/leader/`, `service/tech/`, `service/explore/`.
- Playing an action card, agent/hero, researching technology, exploring planets/frontier.
- UI: "Play card / Activate leader / Research tech" buttons (frontend cards as pickers).

### E5 — Status Phase (scoring + cleanup)
Source: `StatusCleanupService`, `service/objectives/`.
- Scoring public/secret objectives (evaluator — roadmap M3), custodian.
- Cleanup: ready cards/planets, return tokens, new round.
- UI: objectives panel (frontend components) + scoring.

### E6 — Agenda Phase
Source: `service/agenda/`.
- Revealing agendas, voting (planet influence), resolution, laws in play.
- UI: agenda panel (in GameStatePanel) + voting.

### E7 — Faction Asymmetry + End-Game
Source: `service/abilities/`, data `assets/data/abilities/*.json`, `rules_hooks` (spec), VP to win.
- Faction abilities (hooks on movement/combat/production), win condition (10 VP).
- Full list of factions and their gimmicks to code: see "Factions" section below.

---

### E8 — Referee Engine: Rule Enforcement + Timing Windows (OVERHAUL, in progress) ⬅ CURRENT

Decision source: RULES.md 29 (direction shift from "assistant" to "referee"). We add validation
and timing windows ON TOP OF EXISTING E1–E3 (no rewrite). Mode: solo vs bots + hot-seat (ultimately
networked), so windows prompt players in order. God-Mode stays as a validation-bypassing channel.

Tasks (full description and rules: RULES.md 29.1–29.3; log: PROGRESS.md):
- T1: timing window model in `GameState` + `core/timing.py` (respondent queue, open/respond/close).
- T2: expose window in `web_data` + window panel in UI (who is reacting now + response).
- T3: first real window — strategy card secondary (playing a card opens a window for others).
- T4: concept of current player in STATUS/AGENDA + hard flow validation (whose turn, what's allowed).
- T5: movement as a `core/` function (`core/movement.py`) + range/anomaly/traversability validation.
- T6: activation / planet capture / production validation (costs, limits, legality).
- T7: combat — core: rolls (seedable RNG) + hit counting + "assign hits" window, multi-round.
- T8: interactive combat in UI (dice roll animation) wired to windows.
- T9: extra combat windows — anti-fighter barrage + space cannon offense.
- T10: update documentation (RULES.md 29, PLAN, PROGRESS, README) + project memory.

DoD E8: full round playable with enforced rules and timing windows (secondary works for
all players in turn order; illegal actions rejected; combat resolved by engine with rolls).

## Factions — Scope and Gimmicks to Code (E7, after base engine)

Active sources: **base + pok + codex3 (Keleres) + thunders_edge**. Total 30 playable
factions (Keleres = 3 starting variants; Firmament/Obsidian = 2 separate factions; plus
`neutral` as a system pseudo-faction). **Abilities read from data** (`abilities` in
`FactionDef` → descriptions in `assets/data/abilities/`), never from memory.

> How we code this (plan, not now): each ability is a **hook** in the appropriate engine
> window (setup / movement / combat / production / status / agenda). Until a hook exists,
> the ability is "inert" (faction plays as generic). We implement them AFTER completing
> the base engine (E1–E6), faction by faction, each with an entry in `RULES.md` and a test.

### Base (17 factions)
| Faction | alias | Abilities (gimmicks from data) |
|---|---|---|
| The Arborec | `arborec` | Mitosis |
| The Barony of Letnev | `letnev` | Munitions Reserves, Armada |
| The Clan of Saar | `saar` | Scavenge, Nomadic |
| The Embers of Muaat | `muaat` | Star Forge, Gashlai Physiology |
| The Emirates of Hacan | `hacan` | Masters of Trade, Guild Ships, Arbiters |
| The Federation of Sol | `sol` | Orbital Drop, Versatile |
| The Ghosts of Creuss | `ghost` | Quantum Entanglement, Slipstream, Creuss Gate |
| The L1Z1X Mindnet | `l1z1x` | Assimilate, Harrow |
| The Mentak Coalition | `mentak` | Ambush, Pillage |
| The Naalu Collective | `naalu` | Telepathic, Foresight |
| The Nekro Virus | `nekro` | Galactic Threat, Technological Singularity, Propagation |
| Sardakk N'orr | `sardakk` | Unrelenting |
| The Universities of Jol-Nar | `jolnar` | Fragile, Brilliant, Analytical |
| The Winnu | `winnu` | Blood Ties, Reclamation |
| The Xxcha Kingdom | `xxcha` | Peace Accords, Quash |
| The Yin Brotherhood | `yin` | Indoctrination, Devotion |
| The Yssaril Tribes | `yssaril` | Stall Tactics, Scheming, Crafty |

### Prophecy of Kings (7 factions)
| Faction | alias | Abilities |
|---|---|---|
| The Argent Flight | `argent` | Zeal, Raid Formation |
| The Empyrean | `empyrean` | Voidborn, Aetherpassage, Dark Whispers |
| The Mahact Gene-Sorcerers | `mahact` | Edict, Imperia, Hubris |
| The Naaz-Rokha Alliance | `naaz` | Distant Suns, Fabrication |
| The Nomad | `nomad` | The Company, Future Sight |
| The Titans of Ul | `titans` | Terragenesis, Awaken, Coalescence |
| The Vuil'Raith Cabal | `cabal` | Devour, Amalgamation, Riftmeld |

### Codex III — Council Keleres (1 faction, 3 starting variants)
| Faction | alias | Abilities |
|---|---|---|
| The Council Keleres — Argent | `keleresa` | The Tribuni, Council Patronage, Law's Order |
| The Council Keleres — Mentak | `keleresm` | (same) |
| The Council Keleres — Xxcha | `keleresx` | (same) |

### Thunder's Edge (DLC, 6 factions + neutral)
| Faction | alias | Abilities |
|---|---|---|
| Last Bastion | `bastion` | Liberate, Galvanize, Phoenix Standard |
| The Crimson Rebellion | `crimson` | Sundered, Incursion, Sorrow |
| The Deepwrought Scholarate | `deepwrought` | Research Team, Oceanbound |
| The Firmament | `firmament` | Plots Within Plots, Puppets of the Blade |
| The Obsidian | `obsidian` | Nocturne, The Blade's Orchestra, Marionettes |
| The Ral Nel Consortium | `ralnel` | Survival Instinct, Miniaturization |
| (Neutral) | `neutral` | — system pseudo-faction (neutral units), non-playable |

> Full ability TEXTS are in `assets/data/abilities/*.json` — we do not copy them here
> or into code from memory. When implementing each gimmick: read text from data →
> rule entry in `RULES.md` with source → hook in engine → test. Thunder's Edge is DLC,
> so some mechanics may diverge from LRR — then the source is Thunder's Edge material
> (for user confirmation when a rule is unclear).

## Status and Next Step

- **Milestone 1 — digital board + God-Mode:** ✅ done (map, units, players,
  history/Undo, visual editing, phase panel).
- **E1 — phases + turn order:** ✅ done (`turn_flow.py`, endpoints, phase panel).
- **E2 — strategy phase (card selection):** ✅ done (`strategy_phase.py`, card pool, pick +
  trade good transfer, TG accumulation, UI picker). **CLOSED as referee** (feature
  `strategy-phase-complete`, RULES.md 13): Pick_Count (3–4→2, 5–8→1), second round from speaker,
  STRATEGY→ACTION transition validation + strict initiative order → HTTP 422; UI
  `StrategyCardTable` + `PhaseTransitionBanner`. Details: PROGRESS.md.
- **E3 — tactical action:** ✅ done (`core/tactical.py` + `core/combat.py`,
  `api/routers/tactical.py`, tactical panel + combat window in UI). Table assistant: activation,
  step FSM, space/ground combat with numeric helpers, planet capture, production
  helper. Zero rule validation (design decision). Blocks T1–T4, rules RULES.md 19–22.
- **E3 — tactical action (assistant version):** ✅ done as FOUNDATION (blocks T1–T4, RULES.md 19–22).
- **⬅ CURRENT: E8 — referee engine (rule enforcement + timing windows)** — OVERHAUL on existing
  E1–E3 (see stage E8 above + RULES.md 29). Started with documentation update (T10 partial).
- **E4 — component actions** (action cards, leaders, tech research, exploration) — after E8.
- **Factions (E7):** list of 30 factions + gimmicks documented ("Factions" section). We code them
  only AFTER the base engine (E3–E6), faction by faction, as hooks in engine windows.

**Status as of 2026-11-08 (update):**
- **Phase C (central points C1–C9):** ✅ — guard `tests/test_central_points.py` protects ~40 state fields.
- **Hooks:** H1 skeleton (`core/rules_hooks.py`, package `core/hooks/`) ✅, H2 MODIFY/PERMIT/FORBID points ✅ (movement,
  combat, production, payment, agenda), H3 coverage report ✅ (`POKRYCIE_HOOKOW.md`). **H1b (STOP) ⬜** — model
  agreed in RULES.md 43.4, implementation pending.
- **E6 agenda phase:** `core/agenda_phase.py` ✅ (reveal, voting, ties, laws in play); **agenda effects ⬜**.
- **Action cards (H4):** ACTION play ✅ (`core/action_cards.py`, choice form, playability, UI with
  drag-from-hand); **16 of 143 cards have effects**. Goal: complete set (see "PRODUCT GOAL" below).
- **Factions (H5):** 1 faction hook (Arborec); rest ⬜. **Network (N) ⬜** (missing `actor_id` in most endpoints).

**Status as of 2026-11-11 (supersedes points above):**
- **Strategy cards:** all 8 (primary + secondary) ✅ in `core/strategy_cards/` (`CardSpec` modules).
- **Action cards (H4):** 143/143 with effects ✅; window reactions + **H1b ✅** as hold-play (Sabotage) and
  hold-rewind (HOLD button) — RULES.md 53.6, 53.7.
- **Relics** 23/23 ✅, **general technologies** 33/33 ✅ (faction techs in H5), **objectives** 80/80 auto-checked ✅.
- **Agendas:** voting ✅, law/directive effects ⬜ (0/123) — next block.
- **Factions (H5):** ⬜. **Network (N):** N0–N3 ✅, N5 part 1 ✅, N4 ⬜ ("Network Stage" section below).

Detailed progress log: `PROGRESS.md`. Documentation map: `README.md` (in `docs/`).

## FINAL ORDERING PLAN (supersedes older orderings in this file)

Agreed with user. Strategy cards and adding technologies exist (without full effects), so
the next step is **consolidating central points (C) and the hook skeleton (H)**.

| Phase | Scope | Notes |
|---|---|---|
| **C** | Central points: one function per scattered operation (payments, tokens, exhausting, planet control, destroying/placing units, gaining tech, VP) | Pure refactor, ZERO behavior change; regression tests. See "Scattered Sites Audit" below |
| **H0–H2** | Skeleton `core/rules_hooks.py` + hook points ON central points from C | First cases: Arborec (`production.py`), Antimass (`movement.py`), "move through systems with enemy ships" tech, Keleres (commodities as TG) |
| **T** | Finish technologies: gaining (Technology card, skips, prerequisites) + tech effects as hooks | Effects after H2; rules from `R_technology`, `R_technology_sc`, `R_unit_upgrades` |
| **S** | Finish strategy cards (primary/secondary effects, faction exceptions as hooks) | Per state of `core/strategy_cards/*` code |
| **X** | Exploration: finish (decks, attachments, relics) + card effects as hooks | Per state of `core/exploration.py` |
| **H1b** | STOP: checkpoints + interrupt (RULES.md 43.4) | Before action cards |
| **E4–E7** | Action cards, factions (simple → complex), agendas | Per coverage report (H3) |
| **N** | Network up to 6 players (RULES.md 44) | `actor_id` in new endpoints FROM NOW ON |

Cross-cutting rules:
- Every block: RULES.md with source → code in `core/` → test → thin endpoint → QA (pytest/ruff/mypy) → commit.
  Uncertain rule = `⚠ ASSUMPTION` and question to user.
- Until H2 is done: no new `if faction == ...` / specific card checks in base rules.
  If an exception is necessary, it goes in ONE named place (constant/dict) with a `HOOK-CANDIDATE` comment
  (like `_PRODUCTION_FORBIDS`) so migrating to hooks is mechanical.
- Every state mutation described in "central points" (below) goes EXCLUSIVELY through its central function.

## PRODUCT GOAL: all cards ready + drag-from-hand to play (user decision 2026-11-08)

**We want ALL cards ready**, not just selected ones: no component from active decks stays "dead".
Ultimately 100% of components have status `IMPLEMENTED`, and exceptions are explicitly `MANUAL` with justification in RULES.md
(RULES.md 43.1 item 7). Scope (counts from generated `POKRYCIE_HOOKOW.md`): action cards 143, agendas 63,
exploration cards 80, relics 24, promissory notes 40, galactic events 20, leaders 103, faction abilities 73,
technologies 102, breakthroughs 31. Today: 16 action cards and 1 tech have effects.

**Definition of "card ready" (DoD for a single card):**
1. entry in RULES.md (component, text from assets, source in `docs/rules_tirules/`, `⚠` on assumptions);
2. effect: `register_effect("<category>:<id>")` or hook (`core/hooks/*`) — state mutation EXCLUSIVELY through central
   points (RULES.md 43.1a);
3. choice form: `register_effect_inputs` — legal options computed by engine (frontend doesn't know cards);
4. playability: card is playable only when the engine can fully resolve it
   (`action_cards.playability`: window, turn, legal targets);
5. tests: "without / with effect" pair, form round-trip (UI-shaped params pass validation), and errors;
6. regenerated coverage report (`uv run python -m src.audit.hook_coverage --write`).

**UX Standard — drag-from-hand to play:**
- A card is played by **dragging it from the hand bar** onto the "Drop to play" zone; on drop, the choice
  form opens (targets, payment), and the engine validates and applies the effect. Clicking a card still shows preview.
- **A card can only be picked up when it can be played** (engine's decision, not UI's). Others are dimmed,
  and a tooltip states why (not your turn, no target, reaction card…).
- Status today: ✅ action cards with ACTION window (`BottomHandDock`, `GET /action-card/playable`).
- To do at the same standard: reaction cards (when/after/instead) — drag in reaction window / after STOP
  (RULES.md 43.4); promissory notes (play to player's area, `⚠` assumption to confirm); relics and other
  action components. Secret objectives are NOT played (scored in status phase).

**Work order (per coverage report; "ACTION Card Queue" section in `POKRYCIE_HOOKOW.md` is generated):**
1. Remaining ACTION cards (list in report) — require e.g. "home system" helper, traits & wormholes, technology
   research, and executing strategy card abilities.
2. Agenda effects (laws as persistent hooks, directives one-shot) — `SOURCE_AGENDA` mechanism already exists.
3. Components with at_start / at_end / during window (hook at start/end of phase or turn).
4. STOP + pause + playability predicates → reaction cards (~157 when/after/before components).
5. Relics, promissory notes, exploration cards, galactic events.
6. Factions (abilities, leaders, faction techs, breakthroughs, special units): simple to structural.
7. `actor_id` in action endpoints alongside each block, then network stage (N).

## Scattered Sites Audit (central points) — search results in `src/core/`

A hook attaches in ONE place, so an operation must have one function. Below are search results
(code grep, state from this session). Counts = pattern hits, preliminary; EXACT call list
is determined by block C0 (pre-refactor review).

| # | Operation | Where scattered today | Central function (proposal) | Hook examples |
|---|---|---|---|---|
| 1 | Trade goods / commodities (gain, spend, convert) | `payment.py`, `production.py` (separate path), `objective_payment.py`, `exploration.py` (TG & commodities), `strategy_phase.py`, `transaction.py`, `strategy_cards/trade.py` | `core/economy.py`: `gain_tg`, `spend_tg`, `gain/spend_commodities`, `convert_commodities`, `payment_sources` | commodities counted as TG (Keleres), cost change, refund |
| 2 | Resource/influence payment (planets + TG) | `payment.py` (cards), `production.py` (`Spend`, `auto_pay`), `objective_payment.py`, `exploration.py` | single `pay(...)` used by all; production rewired | cost modifiers, extra payment sources |
| 3 | Command tokens (tactic/fleet/strategy) | `objective_payment.py`, `status_phase.py`, `strategic_action.py`, `tactical.py`, `strategy_cards/common.py` | `core/command_tokens.py`: `gain`, `spend`, `move_between_pools` | free activation, extra tokens |
| 4 | Exhausting/readying planets & techs | `exhausted_planets` in ~11 files (e.g. `invasion.py`, `production.py`, `payment.py`), `exhausted_technologies` (`status_phase`, `board_edit`) | `core/exhaust.py`: `exhaust_planet/ready_planet`, `exhaust_tech/ready_tech` | readying planets, "exhaust this card" abilities |
| 5 | Unit stats (move, capacity, cost, combat, production) | `resolve_unit_variant` called in ~11 files (16 calls) — good central point already exists | stays; MODIFY hook on result (`unit_stat(...)`) | move/combat bonuses, faction units |
| 6 | Planet value (resources/influence) | `planet_stats.py` (`resources_of`, `influence_of`; uses: `production.py`, `tactical.py`, `payment.py`) | stays; MODIFY hook on value | attachments, traits |
| 7 | Planet control change | writes to `planet_owners[...]=` in `invasion.py`, `tactical.py`, `faction_setup.py` (outside God-Mode `board_edit`) | `core/control.py`: `set_planet_control` (RULES.md 12, 23) | "after gaining control of a planet", exhaust on capture |
| 8 | Destroy/place/remove units | `battle.py` (13), `invasion.py` (10), `space_cannon.py` (5), `movement.py`, `unit_catalog.py`; placing: `production.py`, `retreat.py`, `exploration.py` | `core/unit_ops.py`: `destroy`, `place`, `remove`, `move` (with fleet pool/reinforcements limit) | "when a unit is destroyed", respawn, limits |
| 9 | Gaining technology | no central function (list mutated by setup/God-Mode; Technology card missing) | `core/technology.py`: `gain_technology`, `can_research`, prerequisites, skips | "when you research a tech", faction skips |
| 10 | Victory points | `objectives.award_points` (exists) + writes in `status_phase.py`, `imperial.py`, `game_end.py` | ensure all go through `award_points`/`remove_points` | "when you gain/lose a point" |
| 11 | Cards (draw/discard/hand) | `card_draw.py`, `deck_piles.py`, `status_phase.py` | single `draw`/`discard` | hand limit, extra draw |
| 12 | Combat modifiers (rolls, hits, reroll, losses) | `battle.py`, `combat.py`, `components.py` | hook points in one roll pipeline | +1 to roll, reroll, ignore sustain |
| 13 | Unit availability/limits (fleet pool, reinforcements) | `fleet_pool.py`, `capacity.py`, `production.py`, `retreat.py`, `unit_catalog.py` | stays in `unit_ops` (item 8) | limit changes |
| 14 | Timing windows | `open_window` in `battle`, `capacity`, `fleet_pool`, `space_cannon`, `status_phase`, `strategic_action`, `timing` — already one API | stays | all TRIGGERs |
| 15 | Hardcoded exceptions (debt) | `production.py::_PRODUCTION_FORBIDS` (Arborec), `movement.py` (Antimass literal), `unit_catalog.py` (tech literals) | migrate to hooks in H2 | — |

Notes:
- Items 5, 6, 14 already have a good central point; just add a hook point.
- Most work: 1–4, 7, 8, 9 (scattered or missing function). This is Phase C's scope.
- Search was pattern-based (grep); places missed by patterns may exist (e.g. via `setattr`,
  serialization, or in `api/`). Block C0 will refine this, and architecture tests (below) will guard the future.
- Example from user request: "Keleres: may exhaust card so each player spends commodities as TG" —
  after C this is ONE entry in `payment_sources`, because all payments go through `pay(...)`.

### Phase C — Blocks (pure refactor, no behavior change)
**Phase C execution status (updated after each block):**

| Block | Scope | Status | Where |
|---|---|---|---|
| C0 | Write-site review (AST scan per field, not grep alone) | ✅ done per block | — |
| C1 | Economy: trade goods, commodities (table, rows 1–2) | ✅ | `core/economy.py`; spending payment (planets + TG) via `payment.apply_payment` |
| C2 | Command tokens: reinforcements + 3 pools (row 3) | ✅ | `core/command_tokens.py` |
| C3 | Exhausting/readying: planets, technologies, strategy cards, leaders, breakthrough (row 4) | ✅ | `core/exhaust.py` |
| C4 | Planet control: `planet_owners` + `controlled_planets` mirror (row 7) | ✅ | `core/control.py` (`set_planet_control`) |
| C5 | Unit operations: place/take/remove/destroy/move (rows 8, 13) | ✅ | `core/unit_ops.py` (`place/take/remove/transfer/replace`, `cause` = `UnitCause`); `damage.py` owns damage; `control.recompute_from_units` |
| C6 | Gaining technology (row 9) | ✅ | `technology.grant_technology` (research and "gain" through it) |
| C7 | Victory points, action cards (hand/deck/discard), speaker (rows 10–11) | ✅ | `objectives.award_points`, `card_draw.py` (`draw/discard/seed`), `strategy_phase.set_speaker` |
| C8 | Architecture guard | ✅ guards 22 fields + `setattr`, with alias analysis (`units = system.space_units…; units[k] = …`) | `tests/test_central_points.py` |
| C9 | Remaining resources and cards | ✅ (except logic in `api/`, see below) | `core/secret_objectives.py`, `core/promissory_notes.py`, `core/relic_fragments.py`, `card_draw.rearrange_agenda_top`; guard extended to agenda/exploration decks, `purged`, `planet_attachments`, `breakthrough_*` |

Execution rules: AST scan (not grep) also finds writes in tuples, by dict key (`x.field[k] = …`), `del`, and list mutations;
refactor does not change behavior (only exception: over-budget ops — e.g. spending a token/TG you don't have — raise `ValueError`
instead of a negative counter); each block = code + tests + QA (pytest/ruff/mypy) + commit.

Description of planned blocks (historical):
- **C0 — Review:** for each table row: full call list (grep + reading), name/signature decision, order.
- **C1 — Economy (1–2):** `core/economy.py` + payment; rewired `payment`, `production`, `objective_payment`, `exploration`,
  `strategy_phase`, `transaction`, `strategy_cards/trade`. Regression test: existing tests unchanged.
- **C2 — Command tokens (3)** and **C3 — Exhaust/ready (4).**
- **C4 — Planet control (7)** and **C5 — Unit operations (8, 13).**
- **C6 — Technology (9):** `gain_technology` function (also for Technology card and "gain a technology" effects).
- **C7 — VP (10), cards (11).**
- **C8 — Architecture test:** test that scans `src/core/` and fails if anyone mutates a state field (e.g. `trade_goods`,
  `exhausted_planets`, `planet_owners`) outside the central function (exception list: God-Mode `board_edit`). This is a guard
  so scattering never returns.
- DoD Phase C: pytest + ruff + mypy green, behavior unchanged, C8 guard active.

## Strategy Cards Plan (S0–S9) — ✅ COMPLETED (2026-11)

> All 8 cards work (primary + secondary) in `core/strategy_cards/` (module per card, shared `base.py`/`common.py`).
> The plan below remains as a decision record; "Status" below is historical.

Status (historical, pre-implementation): `core/strategic_action.py` has a secondary window (`STRATEGY_SECONDARY`) and dispatch
tables `_PRIMARY_EFFECTS`/`_SECONDARY_EFFECTS` by initiative number. Actually only Leadership primary works
(+3 tokens); Leadership secondary is NO-OP (TODO: buy tokens with influence, requires spending model).
Card content EXCLUSIVELY from `assets/data/strategy_cards/*.json`; rules from `docs/rules_tirules/` (`R_<card>.md`,
`R_strategic_action.md`); nothing from memory. Entry in RULES.md 30 expands card by card (30.x).

### S0 — Resource and Influence Spending Model (foundation for all cards)
- Pure function `core/spending.py`: exhausting planets, summing resources/influence accounting for
  flex/optimal (RULES.md 7, 27), trade goods as substitute, "can player afford" validation, change/overpay handling.
- Shared hook point for production, technology, voting, cards (one place, later a hook).
- DoD: spending tested on edge cases; production rewired to this model without behavior change.

### S1 — Data and Dependency Review of 8 Cards
- From JSON + tirules: table "card → primary / secondary → which subsystems it depends on" (e.g. action card deck,
  tech research, placing structures, production, scoring, movement). Output in RULES.md 30.
- Determine order S2–S9 by dependencies (cards without new subsystems first).

### S2–S9 — Strategy Cards One by One (order per S1)
- Each card = separate block: RULES.md 30.x with source → primary + secondary in `strategic_action.py` (dispatch)
  → test → endpoints/UI window (`StrategyCardDetailsCard` etc.) → QA → commit.
- New subsystems built "on demand" by cards (e.g. action card deck, tech research) — each with its own RULES,
  test, and `⚠` marker if rule is unclear.
- Secondary is played in a window where everyone is prompted — does not require STOP (RULES.md 43.4).
- Each strategy card is a separate topic ⇒ separate file (`core/strategy_cards/<card>.py`) + thin dispatch in `strategic_action.py`.
- DoD: 8 cards have working primary and secondary (or explicitly `⚠ MANUAL`, with justification), status in `effects_registry`.

### Faction Dependencies of Strategy Cards
- Faction exceptions for strategy cards (modifying primary/secondary) do NOT enter S2–S9; they arrive after H2
  as hooks (RULES.md 43) so we don't weave `if faction == ...` into card rules.

## Network Stage (N) — IN PROGRESS: N0–N3 ✅, N5 part 1 ✅, N4 ⬜ (RULES.md 44)

Goal: game up to 6 players (humans + bots) over network. Foundations already exist: logic in `core/`/`api/`, WebSocket
(`ConnectionManager`), visibility projection (`core/visibility.py`), queued timing windows, `EventStore`.
**From now on:** every new action endpoint has `actor_id` (RULES.md 44.1).

- **N0 — Audit + `actor_id` ✅ (2026-11-11):** all 102 state-mutating endpoints classified (player /
  table / host action, RULES.md 44.1a), `X-Actor-Id` header, `core/actor.py`, guard `tests/test_actor_guard.py`.
- ✅ (2026-11-11) **N1 — Identity and authorization:** seat token (invite link), host/observer roles,
  `actor_id` resolved from token, `viewing_player` from token in network mode (44.2).
- ✅ (2026-11-11) **N2 — Per-player push:** WebSocket with its own projection per connection; public/private messages;
  "nothing leaks" tests (44.3).
- ✅ persistence (2026-11-11; multiple concurrent games — next) **N3 — Multi-game and persistence:** `game_id`, lobby/rooms, saving `EventStore` to disk, resume after restart
  and reconnect (44.4).
- **N4 — Concurrency:** per-game lock, request idempotency, state recovery on reconnect (44.4).
- 🟡 part 1 (2026-11-11: waiting bar, own desk, 403) **N5 — Multiplayer UI:** "waiting for player X", parallel responses where rules allow,
  timeouts and bot takeover/pass (44.5); STOP with unified timer (43.4).
- DoD: 6-player game (with bots) over network; no client sees another's hand; server restart does not wipe the game.
- Biggest risk: information leak (auth + projection) — security tests before sharing with others.

## Hooks and Exceptions Plan (E7 + E4 + E6) — IN PROGRESS (H1–H4 ✅, H1b ✅, H5/H6 ⬜)

Architecture rules: **RULES.md 43** (hooks, ordering, MANUAL vs IMPLEMENTED). Goal: adding exceptions
(factions, action cards, agendas) without touching base rules, coded one by one, with a RULES entry + test.

Base that already exists (not building from scratch): `core/effects_registry.py` (effect status per component:
`NOT_IMPLEMENTED/IMPLEMENTED/MANUAL`), `core/timing_spec.py` (trigger → window type, RULES.md 34),
`core/timing.py` (windows), `core/component_action.py` (component action skeleton — no effects),
`core/components.py` + `component_loader.py` (component catalog from assets). **Built (2026-11-08):**
`core/rules_hooks.py` (hook, effect, and choice descriptor registry), `core/hooks/` package, `core/action_cards.py`,
`src/audit/hook_coverage.py` report. Arborec exception moved into a hook.

### H0 — Preparation (no game code)
- Review places in `core/` with hardcoded exceptions (grep for `faction`/`_FORBIDS`/card ids) — "debt" list.
- Agree in RULES.md 43 on `⚠` assumptions with user (hook types, ordering, MANUAL vs lock).
- DoD: list of hook points needed to start + approved assumptions.

### H1 — Skeleton `core/rules_hooks.py`
- Registry: `(component source, hook point, category, function)`; fetching hooks for state
  (who owns faction/card/tech/law) in deterministic order (RULES.md 43.1 item 5).
- API: `apply_modifiers(point, state, ctx, base)`, `check_permissions(...)`, `collect_triggers(...)`,
  `resolve_replace(...)`. Pure functions, zero HTTP.
- Regression test: empty registry ⇒ all current tests unchanged.
- DoD: skeleton + unit tests for ordering/conflicts; pytest + ruff + mypy green.

### H1b — Reaction Model: Checkpoints + STOP (RULES.md 43.4) ✅
> Implemented as hold-play (`core/card_hold.py`, Sabotage) + hold-rewind (`core/hold_rewind.py`, HOLD button) —
> RULES.md 53.6, 53.7. List below is the original plan.
- Marking `EventStore` snapshots as checkpoint / irreversible (roll, card reveal, draw);
  `goto(seq)` already exists, only metadata and blocking rewind past a checkpoint are added.
- Filter by public info (action card count, etc.) determining who can even be asked.
- Internal bot polling (no UI); human STOP opens a timing window (`core/timing.py`)
  with the stopping player first.
- UI: "last action" banner with STOP button, active until nearest irreversible point (in combat:
  "Roll" button as natural boundary).
- Done BEFORE action cards (H4): how every reaction enters depends on it.
- DoD: one test reaction (e.g. simple "when/after" card) works via STOP without prompting all
  players; test: behavior for a player with and without the card is identical from the outside.

### H2 — Hook Points in Existing Rules (thin calls)
- Production (`production.py`): `production_forbids`, `production_value`, `cost_modifier`.
- Movement (`movement.py`): `move_value`, `can_pass_system`, `ignore_anomaly`, `capacity`.
- Combat (`combat.py`/`battle.py`/`space_cannon.py`/`invasion.py`): `roll_modifier`, `extra_dice`,
  `reroll`, `hit_assignment`, `before_combat`/`after_combat` (via windows).
- Status/agenda: `status_start`, `status_end`, `vote_modifier`.
- **First case:** move Arborec exception from `production.py` into a hook (behavior unchanged, tests green).
- DoD: no base rule contains `if faction == ...`; Arborec runs through the registry.

### H3 — Coverage Report (prioritization) ✅ (H0-H2 skeleton + MODIFY/PERMIT/FORBID points also ✅)
- Extend audit (`src/audit/`, `effects_registry`) with: component → required hook point
  (from `timing_spec` + effect type). Output: how many cards/abilities each point serves.
- DoD: report in `docs/` (generated, not manual) + queue of next steps by number of served components.

### H4 — Action Cards (E4)
- Dispatch by `component_id` in `component_action`/REACTION windows; each card: text from assets → RULES entry →
  hook → test; status in `effects_registry` set to `IMPLEMENTED`. Cards without hook stay `MANUAL`.
- Order: first cards with simple, single-phase effect (modifiers, +/- resources), then reaction windows,
  finally "instead of"/order changes.
- DoD (iterative): % action card coverage rises, no regressions. **Status:** ACTION play + form +
  playability + drag UI ✅, **143/143 cards ✅** (2026-11-11).

### H5 — Factions (E7)
- **Detailed session-by-session plan: `PLAN_FRAKCJE.md`** (takes precedence over order below).
- Per tables in "Factions" section: first number/legality modifiers (e.g. Sardakk, Jol-Nar, Sol, Letnev,
  Winnu, Hacan), then abilities with windows (Mentak, Xxcha, Saar), finally structural
  (Nekro, Creuss, Mahact, Naalu, Yssaril, Titans, Cabal, Obsidian, Firmament, Crimson, Deepwrought, Ral Nel,
  Last Bastion). Leaders, faction techs, and special units as separate hooks of the same faction.
- One faction = one block: RULES.md + hooks + test + commit.
- DoD: faction has `IMPLEMENTED` status for all its abilities or explicitly `MANUAL` for selected ones.

### H6 — Agenda Phase and Agendas (E6)
- Prerequisite: `core/agenda_phase.py` (reveal, voting by influence, resolution,
  "when/after agenda revealed" windows, ties broken by speaker per rules) — FIRST from tirules2 (`R_agenda_phase`).
- Laws as `PERSISTENT` hooks (expiring on discard/swap), directives as one-shot effects.
- DoD: full agenda phase works without exception agendas; then agendas one by one via the same procedure.
- **Status:** `core/agenda_phase.py` ✅ (voting, tie, laws saved in `decks.agenda_laws`,
  `agenda.vote_modifier` point); laws are already a hook source (`SOURCE_AGENDA`), but NO agenda has an effect yet ⬜.

### H7 — Documentation and Housekeeping
- After each block: RULES.md (43 + component entry), PROGRESS.md, `effects_registry`, QA
  (`uv run pytest -q`, `uv run ruff check src tests`, `uv run mypy src tests`), commit (specific files).
- After H2, update `docs/ARCHITEKTURA_KODU.md` (section on `rules_hooks` and `hooks/` directory).

### Risks
- Multi-effect interactions (e.g. two "instead of" on one step) → handled by ordering from RULES 43.1 item 5
  and verified on tirules2; unresolved cases stay `⚠ ASSUMPTION` for user decision.
- Thunder's Edge: some mechanics may diverge from LRR — source is assets + user confirmation.
- Registry growth: keep topic file splits (item 12) and coverage report (H3) clean.

## Hook Point Catalog (Phase C output) — what to wire in H1–H2

Rule: a hook attaches in the central function (RULES.md 43.1a). Below: where the point is, its inputs, and which hook types (RULES.md 43.1 item 4) fit here.
Card/ability names are only ILLUSTRATIONS of effect kind; content always from JSON assets and tirules2 (never from memory).

### A. WRITE Points (state mutation) — TRIGGER / MODIFY / REPLACE type

| Module | Functions | What a hook can change or react to |
|---|---|---|
| `core/economy.py` | `gain_trade_goods`, `spend_trade_goods`, `gain_commodities`, `replenish_commodities`, `spend_commodities`, `convert_commodities_to_trade_goods`, `give_to_player` | MODIFY amount gained/spent (e.g. +1 TG); TRIGGER "when you gain/spend TG"; REPLACE "commodity instead of TG" |
| `core/payment.py` | `validate_payment`, `apply_payment` | **PAYMENT SOURCES POINT** (today planets + TG): hook adds a source (e.g. commodities counted as TG) and modifies cost (MODIFY) |
| `core/command_tokens.py` | `spend_from_pool`, `spend_to_reinforcements`, `take_from_reinforcements`, `return_to_reinforcements`, `gain_from_reinforcements`, `set_pools`, `add_to_pool` | MODIFY amount; PERMIT "activate without token"; TRIGGER "when you gain a token" |
| `core/exhaust.py` | `exhaust_planets`, `ready_planets`, `ready_all_planets`, `exhaust_technology`, `ready_all_technologies`, `exhaust_strategy_card`, `exhaust_leader`, `ready_all_leaders`, `exhaust_breakthrough`, `ready_breakthrough` | FORBID/PERMIT exhausting; REPLACE "ready instead of exhaust"; TRIGGER "when you ready" (status step 6) |
| `core/control.py` | `set_planet_control`, `recompute_from_units` | TRIGGER "when you gain/lose control"; MODIFY "captured planet is not exhausted" (today `invasion` exhausts it) |
| `core/unit_ops.py` | `place_units`, `take_units`, `remove_units`, `transfer_units`, `replace_zone_units` + `UnitCause` | TRIGGER by `cause`: `DESTROYED` ("when your unit is destroyed"), `PLACED` ("after production"), `MOVED`, `REMOVED`; REPLACE "instead of destruction"; PERMIT/FORBID placement sites |
| `core/damage.py` | `set_damaged`, `move_damage`, `clear_zone_damage`, `repair_all` | MODIFY Sustain Damage; repair in status (hook "repair extra units") |
| `core/technology.py` | `grant_technology`, `apply_research`, `gain_technology` | TRIGGER "when you research a tech"; MODIFY prerequisites and specialties (skips) in `plan_research` |
| `core/objectives.py` | `award_points` | MODIFY/TRIGGER "when you gain/lose a point"; win condition |
| `core/card_draw.py` | `draw_action_card`, `discard_action_cards`, `seed_action_deck` | MODIFY "draw an extra card"; TRIGGER "when you draw/discard" |
| `core/strategy_phase.py` | `set_speaker` | TRIGGER "when speaker changes" |
| `core/timing.py` | `open_window`, `respond_current` | already ONE window API — ALL when/after/before/instead TRIGGERs go through here (RULES.md 34, 43.4) |

### B. READ Points (compute result, do not mutate state) — MODIFY / PERMIT / FORBID type

| Where | What today | Hook |
|---|---|---|
| `combat.resolve_unit_variant` (used in 11 modules) | unit variant choice by tech/faction | MODIFY stats: move, capacity, cost, combat value, production (`unit_stat`) |
| `planet_stats.resources_of`, `influence_of` | planet value from data + attachments | MODIFY planet value (attachments, abilities) |
| `movement` (`_node_passable_intermediate`, `_target_passable`, `_has_antimass`, `can_move`) | blocking passage through enemy ships, anomalies; Antimass tech literal | PERMIT/FORBID passage and entry (first case: Antimass, "move through systems with enemy ships" tech) |
| `production` (`_PRODUCTION_FORBIDS`, `remaining_production`, `producers`, `available_budget`, `auto_pay`, `_validate_spend`) | Arborec dock infantry ban; PRODUCTION limit; budget | FORBID/MODIFY types, limit, and cost; **budget should query `payment` for sources** (today counts TG itself) |
| `objective_progress` (reads `trade_goods` etc.) | objective progress | MODIFY together with payment sources |
| `capacity`, `fleet_pool` | capacity and fleet limits | MODIFY limits |
| `battle`, `combat`, `space_cannon`, `invasion` (rolls, hits, AFB, bombardment) | roll pipeline | MODIFY roll, extra dice, reroll, ignore Sustain; hit assignment |
| `retreat` (`retreat_destinations`) | retreat targets | PERMIT/FORBID targets |
| `tactical.activate_system` | activation cost from tactic pool, `free` flag | PERMIT "without token" (via `command_tokens`) |

### C. What Does NOT Exist Yet (build during hooks, not Phase C)
- `core/rules_hooks.py`: registry, resolution order, 5 hook types (RULES.md 43.1).
- Actions "play action card / use leader / use ability" (today `component_action` only logs "action performed", no effect) — here hooks get their first real calls; must use central functions A.
- Persistent effects state (PERSISTENT: agenda laws, cards staying in play, expiry) and exhaustible abilities registry ("exhaust this card").
- STOP / checkpoints (RULES.md 43.4) and `actor_id` in action endpoints (RULES.md 44.1).

## C9 — closed; what remains after Phase C

Done in C9 (guard `tests/test_central_points.py` protects all fields):
- secret objectives (deck, hand, candidates, scored) → `core/secret_objectives.py` (limit 3 and returning excess here);
- promissory notes (hand, play area) → `core/promissory_notes.py`;
- relic fragments → `core/relic_fragments.py`;
- agenda decks (seeding, stacking top for Politics) → `card_draw.py`;
- exploration decks/discards/purged and `planet_attachments` → `exploration.py` (+ `deck_piles.py` as debug);
- `breakthrough_unlocked`, `breakthrough_tg` — protected, today God-Mode only (logic arrives with hooks).

Still open:
- game logic in `api/` endpoints (e.g. `game.py`: seating/speaker at setup) — move to `core/` during network stage;
- `board_edit.recompute_planet_control` (God-Mode) duplicates `control.recompute_from_units` — intentional, as God-Mode bypasses rules.
