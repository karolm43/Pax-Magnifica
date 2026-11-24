# Project Progress — Custodian Engine

This file tracks work status between sessions. Updated at the end of every block.
Older, completed blocks (Phase 1 → blocks up to 2026-11-19) are in `PROGRESS_ARCHIWUM.md` (read selectively).

> **Current stage:** E8 (REFEREE engine) + hooks: cards, relics, general technologies, objectives, strategy cards,
> agendas ✅; factions (Wave 2) in progress; bot: B0–B1, B3 ✅, B2 core, next B2 (bench) / B5 (`docs/bot/PLAN.md`).
> Coverage status: `POKRYCIE_HOOKOW.md` (generated). Rules: `RULES.md` 29, 43, 53, 65.

## Engine Stage Status

| Stage | Scope | Status |
|---|---|---|
| Phase 1 | Digital board + God-Mode (data, map, setup, editing, Undo) | ✅ completed |
| F0–F18 | Migration to `ti4_web` frontend + player panels + God-Mode UI | ✅ completed |
| E1–E2 | Phases + turn order + strategy phase | ✅ completed |
| E3 | Tactical action (activation, movement, combat, invasion, production) | ✅ foundation |
| E4 | Component control (exhaust/refresh) + RMB menu | ✅ completed |
| S | Strategy cards 1–8: primary + secondary (`core/strategy_cards/`) | ✅ completed |
| E8 | REFEREE engine: rule validation + timing windows (T1–T7 + action phase 31.7/31.8, audit 31.9) | 🔧 in progress |
| C | Central points C1–C9 (architecture guard) | ✅ completed |
| H1–H3 | Hooks: registry, MODIFY/PERMIT/FORBID points, coverage report | ✅ completed |
| H1b | Reactions with rewind: hold-play (Sabotage) + hold-rewind (HOLD) | ✅ (RULES.md 53.6, 53.7) |
| H4 | Action cards: ACTION + window reactions + drag-from-hand | ✅ 143/143 |
| — | Relics (23/23 active), general technologies (33/33), objectives (80/80 automatic) | ✅ |
| E6 | Agenda phase (voting, tie-breaking, laws); agenda effects | ✅ full phase + official deck effects (50/50); ⬜ Absol (60) |
| H5 | Factions: abilities, leaders, PNs, breakthroughs, faction techs | ⬜ (technologies 36/102) |
| N | Network: N0 `actor_id` ✅, N1 tokens ✅, N2 projection ✅, N3 saves ✅, N5 part 1 ✅; N4 concurrency ⬜ | 🔧 |
| QA | pytest-xdist/testmon, E2E Playwright (solo + host/guest) | ✅ |

**Next steps (order):** Absol agenda effects → at_start/at_end/during hooks (16 unemitted events,
`OKNA_CZASOWE.md`) → factions (abilities, leaders, promissory notes) → N4/N5 part 2 → bot.

> Full history of completed blocks with details: `PROGRESS_ARCHIWUM.md`.


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
