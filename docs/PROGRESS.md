# Project Progress — Custodian Engine

This file tracks work status between sessions. Updated at the end of every block.
Older, completed blocks (Phase 1 → blocks of 2026-11-25) are in `PROGRESS_ARCHIWUM.md` (read selectively).

> **Current stage:** E8 (REFEREE engine) + hooks: action cards (143/143), relics (23/23 active), general technologies (33/33),
> objectives (80/80), strategy cards (8/8), official agendas (50/50) ✅; **21/30 factions** done (Waves 1–2 ✅, Wave 3: I1 Capture + Cabal + Titans + I2 tokens 🔧 + I3 adjacency + Creuss + Empyrean + Nomad, Wave 4: I4 Coexistence ✅);
> **bot:** B0–B1, B3 ✅, B2 core, next B4 (arena) / B5 (`docs/bot/PLAN.md`).
> Coverage status: `POKRYCIE_HOOKOW.md` (generated, **501 hooks**). Rules: `RULES.md` 29, 43, 53, 65.

## Engine Stage Status

| Stage | Scope | Status |
|---|---|---|
| Phase 1 | Digital board + God-Mode (data, map, setup, editing, Undo) | ✅ completed |
| F0–F18 | Migration to `ti4_web` frontend + player panels + God-Mode UI + Tactical Window / Player Command Banner | ✅ completed |
| E1–E2 | Phases + turn order + strategy phase | ✅ completed |
| E3 | Tactical action (activation, batched movement, flight replay, Space Cannon, combat, invasion, production) | ✅ completed |
| E4 | Component control (exhaust/refresh) + RMB menu | ✅ completed |
| S | Strategy cards 1–8: primary + secondary (`core/strategy_cards/`) | ✅ completed |
| E8 | REFEREE engine: rule validation + timing windows (T1–T9 + reaction pacing, AFK decay, component mutes) | 🔧 in progress (closing ruling gaps & unemitted events) |
| C | Central points C1–C9 (architecture guard) | ✅ completed |
| H1–H3 | Hooks: registry, MODIFY/PERMIT/FORBID points, coverage report (454 hooks) | ✅ completed |
| H1b | Reactions with rewind: hold-play (Sabotage) + hold-rewind (HOLD) | ✅ (RULES.md 53.6, 53.7) |
| H4 | Action cards: ACTION + window reactions + drag-from-hand | ✅ 143/143 |
| — | Relics (23/23 active), general technologies (33/33), objectives (80/80 automatic) | ✅ |
| E6 | Agenda phase (voting, tie-breaking, laws); agenda effects | ✅ full phase + official deck effects (50/50); ⬜ Absol (13+60) |
| H5 | Factions: abilities, leaders, PNs, breakthroughs, faction techs | 🔧 **18/30 factions** (Waves 1–2 ✅, Cabal, Titans; techs 72/102, leaders 54/102, abilities 38/73, PNs 23/40, breakthroughs 18/31, units 46/90); ⬜ 12 factions |
| — | Exploration cards & Galactic Events (0/20) | 🔧 Exploration implemented in `core/exploration*.py` (only 4/80 in `effects_status`); ⬜ Galactic Events (0/20) |
| N | Network: N0 `actor_id` ✅, N1 tokens ✅, N2 projection ✅, N3 saves ✅, N5 part 1 ✅; N4 concurrency ⬜ | 🔧 |
| QA | pytest-xdist/testmon, ruff, mypy --strict, E2E Playwright (solo + host/guest), ruling coverage guard | ✅ |

**Next steps (order):**
1. **Remaining factions (12):** I3 player-dependent adjacency → Creuss, Empyrean, Nekro, Nomad, Yssaril, Mahact, Keleres (Wave 3) → Deepwrought, Last Bastion, Crimson Rebellion, Ral Nel, Firmament/Obsidian (Wave 4).
2. **Galactic Events (0/20)** + **Exploration status tracking** (`effects_status` vs `core/exploration*.py`) + **unemitted timing events** (`OKNA_CZASOWE.md`, e.g. `game.faction_in_play`, `status.step`, `combat.step`) + **ruling debt** (`tests/rulings_debt.json`: 102 items).
3. **AI Bot (`docs/bot/PLAN.md`):** B4 (`arena`) → B5 (`legal_actions` for tactical action, combat, action cards) → B6 (`fast` state) → algorithms (evaluation, combat MC, RHEA).

> Full history of completed blocks with details: `PROGRESS_ARCHIWUM.md`.


## Action card ruling gaps: user decisions + "Sustain now"

- All four Phase 2 assumptions confirmed by the user; recorded in `rules/R53.md` §53.10 (EB fires in Space Cannon
  Offense and a destroyed dock does not fire; Rescue cargo chosen manually per type + Auto; no step-by-step Sustain
  Damage for directed hits; Puppets "not your turn" rules only for Puppets).
- `BonusTurn.restore_passed` → `not_a_turn` (set only by Puppets on a String): a passed player using Jupiter Brain is
  no longer treated as acting outside their turn (transactions, Minister of Peace). Test in `test_legendary_planets.py`.
- Battle window: "Sustain now" next to "Confirm losses" (`POST /tactical/battle/sustain`): enabled when exactly one
  ship carries a shield mark alone; hidden for directed hits (`sustainNowType`, `battleAssign.test.ts`).

## Docs cleanup, Exploration status tracking, N4 per-game lock (2026-11-26)
- Docs: archived 2026-11-22..24 blocks to `PROGRESS_ARCHIWUM.md` (`PROGRESS.md` ~33 KB), updated Engine Stage Status, `PLAN_FRAKCJE.md` §6, `README.md`, and regenerated `POKRYCIE_HOOKOW.md` / `OKNA_CZASOWE.md`.
- Exploration tracking (`assets/config/effects_status.json`): marked all 80 exploration cards (`77 implemented`, `3 manual` for Entropic Field variants) to match `core/exploration*.py`.
- N4 per-game lock (`api/context.py` `AppContext.game_lock`, `api/app.py` `_game_lock` middleware): serializes mutating HTTP requests (`POST`/`PUT`/`PATCH`/`DELETE`), including middleware mutations, without blocking `GET` or WebSocket. Tests: `tests/test_game_lock.py` (2).

## Action cards: map-picked board sources + "Auto", 4 edge cases (2026-11-26)
- Empty reinforcements → unit taken from the board is clicked ON THE MAP (`board_reinforcements.map_source_options`,
  `unit_at` meta → `GroupedMapField`): Construction/Warfare Rider, Refit Troops, Rearmament Agreement ("Auto" = "Do not
  place"), War Effort / Ghost Ship ("Auto" = first legal source). L1Z1X/Saar reuse the helper. `optionKinds.located`:
  space-area sources next to planets no longer fall back to loose tiles.
- Skilled Retreat token pool: real "Auto" field (tactic → fleet → strategy). Impersonation: full objective names + ⓘ.
- Fixes: Political Stability holder is not asked to pick under Checks and Balances (`GameState.strategy_kept`);
  eliminated players' home tiles stay home systems in `board_graph.home_system_ids` (Mercenary Contract etc.).
- Verified + tested: R_action_cards 6.2 audit guard (every duplicated reaction card blocks its second copy),
  Public Disgrace vs Imperial Arbiter. Assumptions in `rules/R53.md` §53.11. New `GameState` field: restart the backend.

## I3 · Player-dependent adjacency (2026-11-26)
- New hook point FORBID `adjacency.extra_for_player` (ctx `position`, `grid`), read ONLY via
  `board_graph.extra_adjacent_for_player`; `neighbors_for_player` / `are_adjacent_for_player` combine map graph +
  tactical-action adjacency (`action_adjacency`) + the player's own layer. `HexGrid` stays pure topology (RULES.md 61.7).
- Consumers: movement (`movement_paths._neighbors_for_move`, outside the wormhole-law filter), retreats
  (`retreat_destinations`, `skilled_retreat` destinations), Space Cannon offense + range lens (`coverage`: the SHOOTER's
  adjacency), neighbors (A↔B when X,Y adjacent for A OR B; `neighbors_of` now delegates to `neighbors_by_player`) →
  transactions, Pillage, objectives, web-data `neighbors`. Target-centric effects (Ixthian etc.) keep pure adjacency.
- Tests `tests/test_player_adjacency.py` (16, with/without a temporary QE-like hook). `R_adjacency` audited and
  removed from `rulings_debt.json` (`GENERAL_DEBT_LIMIT` 101; hyperlanes = `gap` status); R_wormholes rr/2, rr/3, notes/3 tested.
- No real hook yet — Creuss Quantum Entanglement arrives in B15; Crimson breaches in B24.

## B15 · The Ghosts of Creuss (2026-11-26)
- `core/hooks/factions/ghost.py` (RULES.md 62.19): all 12 components hooked (`missing_components == []`), rulings contract
  `F_creuss` 88/88 (tests or statuses). Texts from `faction_bundle("ghost")`; `tests.rulings` maps `ghost -> F_creuss`.
- Creuss wormhole tokens = faction tokens (`faction_tokens.CREUSS_WORMHOLES`, kinds from `assets/data/tokens` +
  `TokenDef.wormholes`) feeding `SystemState.token_wormholes()` -> real map wormhole edges. One placement function
  (`place_or_move_token`) for Wormhole Generator (tech ACTION), Creuss IFF (turn-start note, once per window) and Icarus
  Drive (offer after ANY activation); entropic scar discards the token; Fracture allowed; neutral ships block.
- New central points: `board.unit_wormholes` (Hil Colish delta, read via `board_graph.unit_wormholes` /
  `placed_wormholes` -> API map sync, `wormholes_at`, objective progress), `movement.wormhole_laws_immune` (replaces the
  old `if faction == creuss` in `agendas_laws`), `movement.moves_separately` (Ion Storm flips right after the Hil Colish
  moves), `system.action_wormholes` (Lazax Gate Folding: Mecatol "has" alpha+beta during the Winnu action -> Splicer),
  `core/system_swap.swap_systems` (hero: SystemStates trade positions, tiles via `replaced_tiles`, homes follow).
- Quantum Entanglement = the first real layer-3 hook (`adjacency.extra_for_player`, I3). Slipstream = move value +1
  from home 51 / alpha-beta systems. Taivra = global `TACTICAL_ACTION` effect (source of `movement.extra_adjacent`).
  Sai Seravus: fighters after a wormhole hop (number field, Auto = max). Particle Synthesis: PRODUCTION per wormhole +
  cost cut per wormhole in the production system. Creuss Gate setup was already engine (declared core rule).
- Activity: `faction_token` facts carry `position`; feed lines "placed / moved ... from X to Y / returned"
  (`describeActivity`, `entities/lookup/wormholeTokens.ts`).
- Frontend FX: `ghosthero` recipe + `CreussFxMarks.SingularityRiftMark` (vortices, tether, old tiles fly along the arc
  and trade places, reveal under the flash; target `swapped`), KeyMoment `wormhole` + `TOKEN_BOARD_FX` portal (token
  colour, origin collapses), caption with the token image (RULES.md 64.4).
- Tests: `tests/factions/test_ghost.py` (44), `test_flows_ghost.py` (9, API: setup, WG, Splicer + Shields Holding /
  Direct Hit, Taivra, Icarus, Sai Seravus, hero, IFF), `test_activity.py`; vitest heroBoardFx / keyMoments /
  CreussFxMarks / describeActivity.creuss. 8 cross-faction `requires: faction:creuss` statuses resolved by tests.
- ⚠️ ASSUMPTIONS (RULES.md 62.19): "Auto" defaults (token, system, Splicer target, mech, hero pair, fighters);
  Hil Colish order = order of submitted fleet moves; "moved through a wormhole" = hop between two wormhole systems that
  do not share an edge. New `GameState`/API fields (`TokenDef.wormholes`, `ActivityFact.position`): restart the backend.

## Player tab as a physical player zone (frontend only)
- Layout (`PlayerTab/`): seat switcher + table badges (`TableStrip`), the 3-wing board (`board/PlayerBoard`:
  `LeaderWing` | `FactionSheet` | `CommandWing`) on a starfield playmat; command sheet = the printed hexagon
  (tactic / fleet / strategy / trade goods / reinforcements) with live token piles. Below it `EmpireDock`, no tabs:
  briefing sorted by urgency, empire + shipyard, hand, army strength (planets/tech/cards stay on the Players tab).
  `CommandBanner` and the telemetry strip are gone.
- Unit boxes (`board/SheetUnit` + `sheetUnits.ts`) print stat boxes, keywords and the UPGRADE strip from unit data
  only; live deployed/cap tag. Click opens the shared `UnitCard/UnitDetails`; upgrade modifiers now live in
  `UnitCard/unitModifiers.ts` (used by `UnitCard` too). `PlayerCard` lost the unused `hideHeader`/`sections` props.
- Responsive by container queries: wings under the sheet below 1240px, one column on a phone.
- Tests: `board/PlayerBoard.test.tsx`; checked in a real browser (solo Muaat game, 1920 / 1366 / 420 px).

## Player tab: full-height wings, readable text, production lines, everything below (frontend only)
- One printed-board chrome for the three pieces (`--piece-*` in `board/PlayerBoard.module.css`); the side pieces
  stretch to the faction sheet's height (`contain: size`). Leader slots share the height, long text fades out.
  Command wing: hexagon + supply tray (ready to spend, planet traits, relic fragments, debts, special tokens).
- Rules text (leaders, faction abilities, unit abilities) = `board/RulesText` in the page's body face, timing window
  on its own gold line; the faction quote is a book italic (same face as the Lore window), not a slanted display cut.
- Production line under every silhouette (`board/productionTips.ts`, from `empireStats`: "Build up to N · limit",
  "Fleet pool full", "Costs X · Y to spend", space dock = PRODUCTION per system, `productionSystems`).
- Dock: technologies (+ skips, unresearched faction techs/notes), planets and cards in play are back, always open
  (`TablePanels.tsx`, the Players-tab components); trait counts moved from the Empire panel to the command wing.
- Pools hold the map's own token (`map/CommandCounter`, new `fluid` size: colour + faction emblem, fleet side up in
  the fleet pool). Fonts enlarged across the board and dock. Production plate = headline + limit ("Can build 4 /
  Jol / Nar produce 4", "Can't afford / costs 8 · you have 3"), so units never read as having PRODUCTION.
- Empire panel: "versus the table" (`empireCompare.ts`) - 14 measures with value, place, leader(s), table/map total.
- Tests: `board/PlayerBoard.test.tsx` (production lines + tips), `empireCompare.test.ts`; checked in the live game.

## Creuss: Singularity Reactor Effect Fix, Hil Colish Move Order + Delta Portal (2026-11-26)

- Singularity Reactor board effect (`map/layers/CreussFxMarks.tsx`): vortex arms rotate on a wrapping `<g>` (the
  CSS `transform-box: fill-box` pivoted each arm around its own bbox, scattering them off centre — the token portal
  had the same bug); vortices, tether, void and flying tiles follow the SHAPE of the tile shown in the slot
  (`shapeCentre` + `tileOutline`: spiral tiles 416x386), each tile lands on its own shape centre; the empty slot is
  a translucent lit wormhole mouth (not a near-black hex) only while its tile is in flight; board dim 0.62 -> 0.45.
- Hil Colish "may move before or after your other ships" in the flight plan: route preview flags the ship
  (`movesSeparately`, PERMIT `movement.moves_separately`, new API field — restart); with its leg + other legs the
  Movement panel asks Before / After / Auto (= after, `⚠️ ASSUMPTION` in R62.19). Before = its leg flies first as
  its own request, then the rest (`flightBatches`); a hint suggests flying it alone first to use the delta at the
  destination.
- Delta wormhole moving with the flagship: Activity facts `unit_wormhole` / `unit_wormhole_removed`
  (`board_graph.unit_wormholes_by_owner`), feed line "Delta wormhole moved with the ship from X to Y", and the
  board portal (`TOKEN_BOARD_FX.whdelta`): a vortex collapses where it left and opens where it arrived.
- Tests: `test_ghost.py` (route flag, feed facts), `flightPlan.test.ts`, `CreussFxMarks.test.tsx`,
  `keyMoments.test.ts`, `heroBoardFx.test.ts`, `describeActivity.creuss.test.tsx`.

## Creuss: Hil Colish Delta Always on the Map, Quantum Entanglement Hover Links (2026-11-26)

- `web_tiles`: a `whdelta` space marker wherever a unit carries a wormhole (`board_graph.unit_wormholes`) - the
  map's Token renders it with the hover links and a "Delta wormhole (Hil Colish)" rule popover (view only).
- `web_players.wormholeLinks`: per player, wormhole system -> systems adjacent only for that player
  (`board_graph.extra_adjacent_for_player`; new `HexGrid.all_wormhole_positions`). `WormholeLinkLayer` draws them
  on hover as dashed lines in that player's colour (Creuss: alpha <-> beta) besides the common links.
- Tests: `test_ghost.py` (marker, links only for Creuss), `wormholeLinks.playerLinks.test.ts`. New web-data fields
  - restart the backend.

## Fix: Hil Colish "Before the others" - later legs re-planned (2026-11-26)

- "Before" flew the other legs with routes previewed while the flagship (and its delta) was still at its start:
  the backend rejected them (422). `useFlightPlan` now re-plans every leg of a later flight on the current board
  (`move-route` with the leg's source + waypoints, `replannedLeg`); a leg that can no longer fly (no route, ship
  out of range, cargo off the new route) stops with a clear notice, the flown legs stay flown.
- Tests: `flightPlan.test.ts` (re-plan), `test_flows_ghost.py` (two flights in one Movement step via API).

## Empyrean (B16, RULES.md 62.20) (2026-11-26)

- `core/hooks/factions/empyrean.py`: all 13 components. Voidborn (PERMIT `movement.through_nebula` + new PERMIT
  `movement.nebula_ignored` in `move_value`), Aetherpassage / Aetherstream / Void Tether permission = offers on
  `SYSTEM_ACTIVATED/AFTER` creating tactical-action effects, Voidwatch = mandatory note choice of the mover
  (not a transaction), Acamar -> the gaining player picks the pool, Xuange (unlock: neighbours with everybody),
  Dark Pact / Blood Pact (play area, return on activation), Dynamo (repair for 2 influence, auto-payment), Watcher
  (cancel an action card - unit window use in the hold window, like Instinct Training), Multiverse Shift.
- Core points (RULES.md 43.1a): adjacency layer 4 `adjacency.cut_for_player` (`board_graph.cut_adjacent_for_player`
  - movement, retreat, Space Cannon, neighbours; RULES.md 61.7 updated); Void Tether = faction token in the zone
  `border:<other>` (`faction_tokens.VOID_TETHER`, supply 2, kept in place by `system_swap`); `economy.give_to_player`
  fires `COMMODITIES_GIVEN`; `UNIT_SUSTAIN_DAMAGE` ctx carries `position`/`zone`; `ExplorationState.frontier_queue`
  (several frontier tokens explored one after another); on-board units with a window use are owned components;
  Direct Hit still targets a ship the Dynamo repaired in the same window (F_empyrean dynamo 3).
- Web data `borderAnomalies` (Void Tether -> existing `BorderAnomalyLayer`; direction from the AsyncTI4 position
  table). Activity: `frontier_tokens` fact, hero areas `frontier` / `explore`, Void Tether feed lines. New fields -
  restart the backend.
- Board FX: `HERO_BOARD_FX.empyreanhero` (void mist, frontier sigils, an eye opens and flares over explored tokens;
  `EmpyreanFxMarks.VoidEyeMark`) and KeyMoment `tether` / `TETHER_BOARD_FX` (dark seam sealing the border, void
  chains, both sides recoil; `VoidTetherMark`), with `battleSound` cues.
- Gaps (statuses in `tests/rulings_status.json`): one SUSTAIN DAMAGE per unit per window (dynamo 1, Reflective
  Shielding 1.1), research card announced at play (watcher 6), Fleet Logistics scenario (watcher 8.1).
- Tests: `test_empyrean.py` (41), `test_flows_empyrean.py` (12), `test_activity.py`, frontend `empyreanFx.test.ts`,
  `EmpyreanFxMarks.test.tsx`, `describeActivity.empyrean.test.tsx`, `heroBoardFx.test.ts`.

## Rulings audit: R_exhausted + R_readied (2026-11-26)

- Verified `core/exhaust.py` and its callers (payment, status step 6, end of agenda phase, strategic action,
  exhaust-cost technologies, "exhaust / ready a planet" effects) against `R_exhausted.md` / `R_readied.md`: no
  discrepancies, no `src/` change.
- `tests/rulings_general/test_rulings_exhaust_ready.py` (10 tests, every point of both files): facedown = on the
  `exhausted_*` list; exhausted planet cannot be spent; Sling Relay exhausts itself and cannot be reused while
  exhausted; Psychoarchaeology does not exhaust its own card; exhausted Self-Assembly Routines still pays 1 TG per
  destroyed mech; Ready Cards readies planets/techs/SCs/relics/legendaries/breakthrough/exhausted leaders; end of
  agenda readies planets, space stations and The Triad only; Uprising (another player's planet) vs Brilliance /
  Psychoarchaeology (own planets only).
- Statuses: Deepwrought ocean cards (`R_exhausted/notes/1.1`, `R_readied/notes/2.1`) `requires faction:deepwrought`.
- `tests/rulings_debt.json` -2 entries, `GENERAL_DEBT_LIMIT` 101 -> 99. Ruff fix in `tests/test_activity.py:657`.

## Quantum Entanglement hover links: own seat only

- Bug: `WormholeLinkLayer` drew the Creuss dashed alpha <-> beta links for every viewer. They are now drawn only for
  the desk player (`useDeskPlayer`: my seat in a network game, the turn player locally). Printed wormhole links
  are unchanged. They look like any other wormhole connection (no player colour, no dashes), coloured by the destination wormhole. Frontend only; test `WormholeLinkLayer.test.tsx`.
- Hovering any wormhole now shows the connections of every wormhole in that system (`kindsToShow`;
  ingress / egress stay separate).

## Decision windows only for the deciding player; Freelancers off-turn

- Network game: Production, Exploration, Capacity and Fleet pool windows render only for the player who decides
  (`useCanActAs` / new `useCanActAsFaction` in `useNetworkMe.ts`); Invasion only for the attacker and the invaded
  players. Watchers keep the "Waiting for X" status chip and the Activity feed. Local mode / unseated host still see
  everything. Strategy-card tech windows and offers were already per player.
- Freelancers (RULES.md 46 X7): "produce in this system" = the explored system. The option is no longer disabled
  outside the active system; an exploration outside the explorer's own tactical action (another player's turn,
  Naaz-Rokha agent) opens a `free` grant there, paid with influence as resources. Production header shows
  "res/inf" for such grants. Tests in `tests/test_exploration.py`.

## Home tile swap keeps the stat area in place

- Singularity Reactor on a home tile moved the 3 stat hexes; they now stay at `PlayerState.seat_position`.

## B18 · The Nomad (RULES.md 62.21) (2026-11-27)

- All 14 components (`core/hooks/factions/nomad.py`, coverage 14/14): The Company (data: 3 agents), Future Sight
  (vote or rider prediction → 1 TG), Memoria I/II (flagship-only movement adjacency to mech systems), Temporal
  Command Suite (ready any agent — JR-XS455-O too — + a granted transaction), Field Marshal Mercer (end of any
  turn: that player moves up to 2 ground forces onto their planets in the system activated this turn), The
  Thundarian (window use in any combat: rolls discarded, back to the Roll Dice step), Artuno the Betrayer (TG from
  the supply onto the card, paid out when it readies), Navarch Feng (free flagship), Ahk-Syl Siven Time Warp
  (flagship + its cargo leave command-token systems this round), The Cavalry (1 ship fights as the Nomad
  flagship, returns at combat end), Quantum Manipulator (mech in space cancels hits on ships), Thunder's Paradox.
- New central points: `movement.unit_extra_adjacent` (`movement_paths._neighbors_for_move` gets the moving
  `base_type`), `production.free_types` (`order_cost` + `freeTypes` in the production view), `combat.champion`
  (`CombatUnit.champion_*`: dice bonus segment, own AFB roll, sustain), `combat.hit_shields`
  (`battle_units.hit_shields` / `assign_units`: shield rows only sustain, also against AFB / directed hits; bot
  `legal._assign_hits` uses them), `battle.roll_step_open` / `rewind_roll_step` (+ `COMBAT_STEP/START` roll_dice,
  resume `roll`), `economy.gain_trade_goods(from_supply=)` + `stash_on_leader` / `release_from_leader`
  (`PlayerState.leader_trade_goods`, leader `tgCount`), `exhaust.ready_leader` / `ready_all_leaders` fire
  `COMPONENT_READIED/AFTER`, `leaders.exhaust_announced`, `transaction.grant_pair` (no neighbour / active player /
  per-turn limit), `GameState.turn_active_system` + `position` in `TURN/END`, `base_type` ctx of
  `movement.ignore_own_command_token` (flagship as carrier in `move_fleet` T4, capacity checked).
- Cross fixes: Duranium Armor no longer repairs a ground force in the space area (Eidolon Maximum still does);
  Gravleash Maneuvers may move its bonus after The Thundarian (`F_letnev/gravleash-maneuvers/8`).
- Frontend: Time Warp board FX (`NomadFxMarks.tsx`: rewinding chronometer + ghost hexes over the flagship,
  hourglass + opening chrono-lock on command-token systems; static sweep, flash, quake, reversed sound cues);
  battle window shield rows / champion tag / "rolls undone" log; production "Navarch Feng" discount; Activity
  `leader_tg`; God-Mode "Trade goods on <leader>".
- Tests: `tests/factions/test_nomad.py` (36), `test_flows_nomad.py` (6, harness gained an optional third player),
  `test_activity.py`, vitest `nomadFx`, `NomadFxMarks`, `describeActivity.nomad`, `battleAssign.nomad`.
  Statuses: 15 F_nomad entries (`na` with reasons; `gap`: Emergency Repairs repairs a Cavalry-damaged ship).
- ⚠️ ASSUMPTIONS for the user (RULES.md 62.21): Mercer's "active system" = the system activated that turn, Auto =
  move nothing; TCS transaction grant lasts until the phase ends; hero purged on use (effect to round end);
  Cavalry "combat value" includes the ×2 dice, champion is the last of its group to die, Auto = worst group;
  Thunder's Paradox Auto = first ready own agent / first exhausted agent. A combat roll with no hits opens no
  assignment, so The Thundarian cannot rewind it.

## Decision boxes: one frame, no clipping, two widths (frontend)

- `DecisionCenter` cards ("Available now", "Window open now" / "Window closed", trading-table invite) now render
  through `DecisionFrame` instead of the ad-hoc `.card`/`.actions`/`.ghost`/`.primary` styles (removed from
  `AbilityPrompts.module.css`). `DecisionFrame` gained `icon`, `tone` (`window` pulse / `closed`), `subtitle`,
  `hint`, `neverAskHint`, a ReactNode `kind`, `shortcuts` (only the current offer owns Enter/Esc; other cards pass
  `false` so one Enter never fires several actions) and drops the footer when it has no buttons. The redundant
  header × on those cards is gone (footer "Not now" does the same).
- Footer `[Never ask] [Skip Esc] [Secondary] [Use Enter]` wraps (`flex-wrap`), buttons keep one height; a long
  primary label wraps inside its button, the key hint stays on one line.
- `SlotsMapField`: the `−` button shows only at ×2+ (with one piece it equalled `×`).
- `DecisionFields.module.css`: no more line-clamp on option names, option sub-labels and rich descriptions.
- Widths: `--decision-w` 460px / `--decision-w-wide` 560px (`styles/themeSharedTokens.css`) mirrored by
  `DECISION_WIDTH` in `DecisionFrame.tsx`; used by `DecisionCenter`, `PromptDock`, `ComponentUseModal`,
  `ActionCardPlayModal`, `SecondaryDecisionModal`, `StrategyPrimaryStepModal` (card-specific 1080 kept).
- Tests: vitest `DecisionFrame` (+3: footer order/wrap, `shortcuts={false}`, no empty footer + tone),
  new `SlotsMapField.test.tsx`.
