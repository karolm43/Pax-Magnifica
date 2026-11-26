# Project Progress — Custodian Engine

This file tracks work status between sessions. Updated at the end of every block.
Older, completed blocks (Phase 1 → blocks up to 2026-11-24) are in `PROGRESS_ARCHIWUM.md` (read selectively).

> **Current stage:** E8 (REFEREE engine) + hooks: action cards (143/143), relics (23/23 active), general technologies (33/33),
> objectives (80/80), strategy cards (8/8), official agendas (50/50) ✅; **19/30 factions** done (Waves 1–2 ✅, Wave 3: I1 Capture + Cabal + Titans + I2 tokens 🔧 + I3 adjacency + Creuss, Wave 4: I4 Coexistence ✅);
> **bot:** B0–B1, B3 ✅, B2 core, next B4 (arena) / B5 (`docs/bot/PLAN.md`).
> Coverage status: `POKRYCIE_HOOKOW.md` (generated, **467 hooks**). Rules: `RULES.md` 29, 43, 53, 65.

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

## Titans: F_ul Ruling Coverage + Terragenesis Move Fix (2026-11-25)
- New `tests/factions/test_rulings_titans.py`: 12 `@ruling` tests (terragenesis 1, awaken 3/4/6/7, terraform 2.1/5,
  heltitan 4, geoform 2, hecatoncheires 6, slumberstate-computing 1/4).
- Fix (F_ul terragenesis 2): Terragenesis may move a placed sleeper token only once all sleeper tokens are on the
  board — while the pool has tokens the only source is the pool (`titans._terragenesis_sources`; the effect rejects
  other sources). Slumberstate Computing keeps its own source list. `rules/R62.md` updated.
- `tests/rulings_status.json`: gaps for awaken 5, coalescence 4 (turn ended by Nullification Field drops the
  combat), terraform 4 (Fracture planets not explorable with Terraform), hecatoncheires 5 and slumberstate 5
  (coexistence I4), slumberstate 3.1 (no binding deals).
- QA: Titans tests + other tests touching Titans/sleepers (206 passed), ruff, mypy on changed files. Skipped: full
  backend suite, frontend (no change).

## Flight Replay: Fracture Portals, Asteroid Fields, Supernovas (2026-11-25)
- Fighters unpacking from a carrier turn to their launch heading while still hidden inside it, so they come out
  nose-first (user: they were "rotating out of ships, not flying out"); the parking turn happens while braking.
- Ingress/egress (route hop `portal`) is now its own leg kind (`FlightLeg.kind = "portal"`), distinct from a
  wormhole: `PORTAL_MS` (2 s, quicker than a 2.4 s wormhole), the ship accelerates into the tear stretching along
  its nose into a streak (`Frame.stretch`), flashes out and shoots out of the egress tear as a streak. Board effect
  `portalIn` / `portalOut`: a jagged amber-white tear with a crimson glow that rips open and snaps shut.
- Asteroid field (`ASTEROID_FIELD`, reachable with a tech): slower leg, the ship weaves sideways between the rocks
  with small nose swings, dusty glow, `asteroidDust` cloud with rock flecks. Supernova (`SUPERNOVA`): hot orange
  glow, buffeting shake, `supernovaFlare`. Both act in a bell around the system and fade at the chain ends, so
  launch and landing points stay exact.
- QA: frontend tsc (app), eslint (changed), vitest (`entities/replay`, `state`, `domains/map`). Skipped: backend
  (no change: the route already carried `portal` hops and anomaly names), build (no new modules), e2e, visual check.

## Flight Replay: Ships Swallowed by a Gravity Rift (2026-11-25)
- User request: a ship that fails its gravity rift roll should be shown swallowed by a black hole. Before, the lost
  ship flew all the way to the destination and faded out there.
- Backend (presentation only, no rule change): `_resolve_rift_losses` also returns `MoveLoss` entries (unit type,
  count, rift system `at`) for lost ships and the cargo that went down with them; `MoveRecord.lost` carries them and
  `tactical.move` emits one `rift_lost` Activity fact each (value = unit, delta = count, detail = rift). Feed line:
  "lost N <unit> to the gravity rift in <system>".
- Frontend: `liveMoveFromEntry` reads `rift_lost` (base type -> map unit id); a move whose whole fleet was lost still
  replays. `resolveFleetMove` splits each moved stack into survivors and `lostAt` units; the planner flies a lost
  unit with the fleet up to its rift (`swallowLegs`) and a final `swallow` leg (`SWALLOW_MS`): caught, it is dragged
  into an ever tighter, faster spiral, stretched thin and shrunk to nothing at the rift's center. Own destination
  key, so arrivals/combat/losses at the real target never count it. Lost cargo boards a doomed carrier and never
  unpacks (`CargoRide.lost`); surviving cargo rides a carrier that gets through. Board effect `blackHole`: a
  lightless core in a spinning purple-orange accretion ring that opens before the capture and collapses after.
- QA: backend ruff + mypy (changed), pytest (`-k move/rift/activity/tactical/transport` + rift-using faction
  tests); frontend tsc (app), eslint (changed), vitest (`entities/replay`, `state`, `domains/map`, ActivityPanel).
  Skipped: full backend suite, build (no new modules), e2e, visual check in a live game.

## Timing-window / ordering gaps closed (2026-11-25)
- Six `gap` entries removed from `tests/rulings_status.json`, each with a `@ruling` test:
  - `F_ul/awaken/5`, `F_ul/coalescence/4`: Nullification Field no longer drops Awaken's ground combat —
    `invasion.begin_forced_combat` (`InvasionState.forced_end`) runs only Ground Combat + Establish Control, then ends
    the action and the turn. Space combat from Coalescence is not covered.
  - `F_muaat/adjudicator-baal-nova-seed/10`: same-window offers are re-validated after each accepted ability
    (`triggers._drop_stale_offers`); emptied responders are skipped in the REACTION queue. Nova Seed (active) now
    kills Foresight's offer.
  - `F_vuilraith/the-stillness-of-stars/4`: `CardSpec.on_begin` — Trade's +3 TG and replenish run when the card is
    played, the agent's window opens before `choose_free_players`; `submit_primary_step` blocked until it closes.
    Old tests that expected the primary effect at the end were updated.
  - `R_exploration/notes/1`: `accept_offer` refuses "after you gain control" offers while the planet is still queued
    for / being explored.
  - `C_technology/assault-cannon/3.1`: Assault Cannon is a separate combat-start stage after all other start offers
    (`triggers.fire(hook_filter=)`, `battle._assault_cannon_stage`). ⚠️ ASSUMPTION documented in R56.5.
- QA: ruff (src, tests), mypy (changed files; the only error, `battle.py` `has_planet_ships`, is another session's
  hunk), pytest timing/ruling coverage + full suite (see report).

## Flight Replay: Antimass Deflector Fields, Gravity Drive, Space Cannon Volley (2026-11-25)
- User feedback: the asteroid-field weave looked ugly; wanted the Antimass Deflectors visible as fields, an
  animation for Gravity Drive, and one for Space Cannon shooting at ships in the next step.
- Asteroid field (`flightPath.ts`): weaving removed - the ship holds its line (still slower). An energy bubble with a
  hex lattice and rim sparks glows up around each hull while it crosses the field (`buildPathKeyframes().shield`,
  `[data-shield]` in `UnitStack/FlightEngines.tsx`); the board effect `asteroidDust` is now rocks flung outward over a
  cyan ripple.
- Gravity Drive: backend `MoveRecord.boosted` (base types that spent the bonus, `movement.move_fleet`) -> Activity
  fact `gravity_drive` (+ feed line). The boosted ship flies in a violet gravity well (`drive` timeline, `[data-drive]`)
  and a `gravityDrive` effect (rings sucked inward, shockwave) opens at launch (`MapUnitTransition.gravityDrive`).
- Space Cannon Offense: `spacecannon.fire` now carries one `cannon_shot` fact per roll group (target player, zone,
  hits, new `ActivityFact.dice`, route = [shooter system, active system]). Every client replays it as a
  `LiveCannon` (`entities/replay/cannonVolley.ts`): after the physical dice land (`CANNON_DICE_LEAD_MS`) amber slugs
  leave each shooter (planet / unit / system), hits strike a target ship with a burst + shock ring, misses sail wide.
  Moves nothing, so it pairs with the live map at once. ⚠️ ASSUMPTION (presentation only): the dice lead is a fixed
  2.6 s, not synced to the dice stage; ships destroyed by the hits still vanish without a fade (assign step).
- QA: backend pytest (`-k move/activity/space_cannon/tactical/gravity/rift`, 356 passed), ruff + mypy (changed);
  frontend tsc (app), eslint (changed), vitest (`entities/replay`, `state`, `domains/map`, ActivityPanel). Skipped:
  full backend suite, build, e2e, visual check in a live game. Backend restart needed (new fields / facts).

## Coexistence (block I4): Slumberstate, Pride of Kenara, bombardment of coexisting players (2026-11-25)
- `core/coexistence.py` (RULES.md 40.1 I7b): coexistence is derived from the board (controller + other players with
  units on the planet). New `SystemState.coexisting[planet]` = players coexisting BY CHOICE, exempt from the I7a forced
  ground combat via `coexistence.fighting` (`invasion._contested`, `battle.start_combat`); a commit to the planet
  starts the combat again. Establish Control keeps players coexisting by choice (and their structures) when an invader
  takes the planet from its controller (R_coexistence 14-15).
- Slumberstate Computing (62.18): sentence 1 = field `coexist:<planet>` in the Awaken window ("Auto" = coexist; also
  for Hecatoncheires + infantry); sentence 2 = MODIFY `POINT_STATUS_ACTION_CARDS` from a rule source every player owns
  (`coexistence.partners`), so only the Draw Action Cards step draws more.
- Bombardment (R40 I2): `BombardAssignment.target` / API `target`; on a planet with several defenders the hits wait
  under `planet@player` (`invasion.split_bombard_key`), the surplus stays with the chosen player, Plasma Scoring adds
  its die to one roll. "Auto" = the controller. TODO: target picker in the bombardment window (UI sends "Auto").
- Pride of Kenara: `transaction._apply_planets` changes control before moving the Hacan units (IE window first);
  coexisting units stay.
- Gaps closed: `breakthroughs:titansbt#1/#2`, `F_ul/hecatoncheires/5`, `F_ul/slumberstate-computing/5`,
  `F_hacan/pride-of-kenara/4`, `C_technology/plasma-scoring/2`; R_coexistence 1, 2, 2.1, 11-11.2, 12-15 tested
  (file stays in `rulings_debt.json`). Not modelled: automatic control hand-off to the last coexisting player (7-7.4).
- QA: ruling coverage, `pytest --testmon` (2 failures from other sessions' hunks: relics sustain `zone`, frontend
  locality URL), ruff, mypy. Skipped: frontend (no change), build, e2e. Backend restart needed (new state field).

## Gap sweep: Compensated Disarmament /5, Wormhole Research /5-5.2, Salvage Yard /2
- Compensated Disarmament /5: already correct after block I4 (the controller gets every TG, coexisting players
  pay out to nobody); now pinned by a coexistence test.
- Wormhole Research (R51): the alpha/beta destruction is DEFERRED (`core/wormhole_research.py`, active effect
  `agendas:wormhole_research:destroy`). `agenda_phase.continue_agenda` settles it, i.e. only after the research and
  Anti-Intellectual Revolution choices (doomed ships can be picked), then capacity (`capacity.open_capacity_check`; a
  CAPACITY window keeps the speaker on "continue" until it is closed), then destroys with flagships LAST so The Terror
  Between still captures the others (and captures nothing when it was destroyed for the Revolution).
- Salvage Yard (R60.6): cards on Garbozia are played "as if in hand" - `card_draw.salvage_yard_cards` /
  `borrow_salvage_yard_card`, purge via `discard_specific_action_cards` (`GameState.salvage_yard_borrowed`). No UI tray yet.
- Gaps closed: `C_agendas/compensated-disarmament/5`, `C_agendas/wormhole-research/5`, `/5.1`, `/5.2`,
  `C_legendary_planets/dok-n-pics-salvage-yard-garbozia/2`. Backend restart needed (new state field).

## Tactical window redesign, phase 1: batched flight plan + guided step entry (RULES.md 32.4, 19.1)
- `POST /tactical/move-batch` -> `core/movement_batch.move_batch`: the whole Move Ships declaration (legs from
  any number of systems) is validated before anything moves; illegal leg -> 422 `Leg N (from X): ...`. Each leg
  runs through `movement.move_fleet`; ships flown in by an earlier leg cannot move again (simultaneity).
  One snapshot per leg (`tactical:move:<from>:b<seq>`), one broadcast; `/tactical/undo-move` and `/undo/mine`
  revert the whole plan.
- `tactical.advance_guided` (HTTP next step + bot `tactical_next`): entering SPACE_COMBAT starts the mandatory
  combat, entering INVASION begins the invasion (label `battle:start:space` / `invasion:begin`); waits when a
  window / reaction pause is open. `POST /tactical/invasion/skip` (`tactical.decline_invasion`) closes an invasion
  with nothing bombarded or committed.
- Tests: `tests/test_move_batch.py`; flow harness `start_space_combat()` tolerates the auto-start.
- QA: full pytest (only failures: frontend locality URL in `componentLinks.ts`, from another commit), ruff, mypy
  (errors only in other sessions' files). Backend restart needed (new routes).

## Tactical window redesign, phases 2-4: guided Tactical Action Window, flight plan UI, step polish
- `TacticalActionWindow` (replaces `TacticalActionDock`; panel moved out of `GameStatePanel`): active system +
  planets, 5-step bar with Done / Active / Skipped / Upcoming (`tacticalSteps.ts`, pure + tested), one-line
  prompt, sticky footer with ONE context-aware primary action (Fly plan / Next step / No movement - next step /
  Return to battle / Start space combat / Finish action), Undo + "Map" (minimize keeps the panel mounted),
  rule locks phrased as what to do. Wider (420 px), resizable.
- Flight plan (RULES.md 32.4): `movePlan` in `appStore`; `MoveRouteBox` is now the leg editor embedded in the
  window ("Add to flight plan" / "Update leg"; units staged in other legs are not offered again); staged
  routes drawn by `FlightPlanLayer`; `FlightPlanList` shows legs with the one-ship bonus each spends; combined
  fleet pool / capacity preview (`FleetPoolWarning` `extraCapacity` / `extraGround`); `useFlightPlan.fly` =
  one `/tactical/move-batch`. No system list in the window (planets/systems only on the map - user rule).
- Step entry: battle / production windows open with their step; invasion "Skip invasion (land nothing)".
- Space Cannon: whose-turn banner (network: other seats wait), "Fire Space Cannon (N dice · hits on X+)" with
  the hold hint visible, range lens on by itself while firing, results log folded, "Auto" hit assignment
  (`autoAssignHits`, RULES.md 38.4 ⚠️ ASSUMPTION).
- Not done: the live flight replay still animates only the newest leg of a batch (`useLiveMoveReplay` pairs one
  move per refresh; that code is being reworked in another session). No firing lines for Space Cannon beyond
  the range lens (cannon volley animation is in progress elsewhere).
- QA: tsc, eslint (changed files), vitest (new + movement/invasion/map/state folders; `StrategyCardTable.test.tsx`
  runs out of memory also on clean HEAD), `npm run build`, `npm run e2e` (8 passed). Backend unchanged here.

## Player tab: Command Banner, telemetry strip, tabbed deck, Opponent Intel
- `CommandBanner` replaces the plain `.hero`: faction portrait (same `portraitCandidates` chain as the faction
  picker, now typed on `{id, leaders}` so a seated player works), tinted with `--pc`, faction quote + author,
  "Lore" button (full lore in `AppModal`), table tokens via the exported `HeaderTokens` (speaker, tyrant,
  strategy cards, `FactionVoice`), plus `NeedsToFollow`, `Neighbors`, `Breakthrough` moved up from the card header.
- `PlayerCard` gets `hideHeader` and `sections`; `PlayerCardDeck` draws only the requested groups
  (`loadout | status | tech | units | planets`). Player tab: telemetry strip under the banner (`ResourceBarFor` +
  fleet use, hand AC/limit · SO · PN, strategy cards ready, agenda votes), then tabs Briefing | Status |
  Tech & units | Planets. Players tab unchanged.
- `commanderTips`: `briefingMode` = self / scout (another player viewed from my seat). Scout = Opponent Intel
  (VP distance, objectives they can score, near objectives with progress, unplayed SCs, neighbour + trade stock,
  hand counts, fleet pool). Self adds near-objective progress `(3/4)`, unlocked commanders, secondaries to follow
  (`unfollowedSCs` - the backend still always sends `[]`). Fixed: the status-phase secret tip used
  `numScoreableSecrets`, which is the secret LIMIT (always 3); it now uses `numUnscoredSecrets`.
- Tip references are buttons: click opens the full card (`ComponentCard`, same as the decision-window ⓘ).
- `empireStats`: `readyInfluence`, `fleetRoom` (best production system: fleet pool − non-fighter ships there);
  Shipyard caps non-fighter ships by it (`limitedBy: "fleetPool"`) and greys blocked tiles ("fleet pool full" /
  "none left").
- QA: tsc, eslint (changed files), vitest (player, setup, game-shell, chat), `npm run build`; screenshots of the
  live game (self, scout, Tech & units). Skipped: backend QA (frontend-only), e2e (the Player tab is not always mounted).

## Space Cannon Offense for non-active seats (frontend)

- `SpaceCannonResponseWindow` (TacticalActionWindow shell + the same `SpaceCannonStepPanel`): in a network game the
  Tactical Action Window is the active player's only, so other seats never saw Space Cannon Offense. Now a seat that
  is queued to fire (wait / fire / done) or is the target of a pending shot (covers hits even without its own PDS)
  gets its own draggable, minimizable window. Role logic in `spaceCannonRole.ts` (+ test).
- Hit assignment is interactive only for the targeted seat in a network game; others see "Waiting for X to assign".
- Wording: a single target is no longer "the ships that moved in" - Space Cannon Offense hits ANY of the target's
  ships in the active system (active shooter: "only player with ships in the active system"; others: "must target
  the active player's ships"). Backend targeting already matched R_space_cannon (Offense step 2).
- QA: tsc, eslint (changed), vitest game-shell, `npm run build`, `npm run e2e` (8 passed). Skipped: backend QA
  (frontend-only).

## Reaction pacing: component mutes, per-combat pass, AFK decay, quick jitter (RULES 54.12)

- `reaction_prefs`: `combat` duration (stamp = round|kind|system|planet|attacker|defender; dies with the combat),
  `muted_components` (key = `faction_components.effect_key`, scopes combat/turn/round/always) -> `has_playable_reaction`
  skips muted agents/components via `window_component_users(respect_mutes=True)`; the PUBLIC eligible list is
  unchanged, so a mute never leaks.
- AFK decay: a window ending by server timeout gives a strike to every eligible player who did not pass (manual or
  engine), did not ask for time and did nothing in the UI since the window opened (`responded`). `AFK_STRIKES = 2`
  strikes => `skips_automatically`. Any POST by the player (middleware in `api/app.py`) resets it ("I'm back").
- Quick windows + `reaction_jitter_seconds` (host, `/reaction-settings/jitter`, 0-2 s): the window shrinks to a
  deterministic 50-100% of the jitter instead of vanishing (`reaction_window.quick_settle`).
- UI: `ReactionQuickPass` in `ReactionPauseBanner` ("Pass this combat", "Pass <agent> this round", "Auto-pass
  uninvolved"); "This combat" duration in the Reactions panel. Contract: `reactionPrefs.windowComponents/mutedComponents/afk`,
  `reactionPause.category`, `reactionJitterSeconds`.
- NOT done: quick-pass buttons in `HeldPlayBanner` (Sabotage window; file has a parallel session's edits); no host UI
  control for jitter yet (endpoint only); involvement filter for "global" agents (Naalu/Saar) = mute, not auto-detected.
- Tests: `tests/test_reaction_pacing.py` (25).

## Space stations, Fabrication gating, Distant Suns buttons

- `planet_stats.is_space_station`: ground forces cannot be committed to (`invasion.commit_ground_forces`,
  `apply_commit_from_planets`) or produced on (`production.allowed_ground_zones`) a space station
  (R_space_stations). A system with only a station no longer opens the invasion window.
- Component-action list now greys out faction abilities using the engine blockers
  (`/faction-component/playable`, `useFactionComponentPlayability`): Fabrication needs a relic fragment.
- Exploration overlay: Distant Suns shows a labelled pair "Draw 1" / "Draw 2, keep 1 (Distant Suns)".
- Not reproduced: the unexpected tactical Bombardment step (needs a repro: which system/units).

## Stellar Converter: targets without units, destroyed planet token, board effect (RULES 59, 64.4a)

- Bug: `_converter_planets` used `grid_from_state` (only systems with a state entry), so a planet in an untouched
  system (no units/tokens) was never adjacent -> no legal target. Now adjacency = bound map grid + state-only links;
  Mecatol Rex excluded by planet id (also without a state entry).
- Bug: the destroyed planet token was never drawn. Web-data `tileUnitData[pos].destroyedPlanets` -> `positioning`
  places `worlddestroyed` on the printed planet (planet stays out of `tile.planets`).
- Activity fact `planet_destroyed` (also The Silver Flame) + feed line; KeyMoment `converter` (only with the relic
  purged) -> `RELIC_BOARD_FX.stellarconverter` + `StellarConverterMark` (charge, beams from adjacent ships, lattice
  squeeze, burst, debris ring, ash) with sounds; token veiled until the flash; caption instead of a portrait scene.
- Tests: `test_rulings_relics.py` (3 new), `keyMoments.test.ts` (2), `StellarConverterMark.test.ts` (4),
  `positioning/destroyedPlanet.test.ts` (1).

## /dev/ui audit: design-system and gallery fixes (frontend only)

- ds `color()` maps semantic words (`info`/`warning`/`error`/`danger`/`success`) to palette hues: `Alert` with these
  colours was unstyled (invalid `--ds-alert-c`). Alert gets a stronger tint + 3px accent bar.
- New token `--ds-sig-tech`; `NumberInput` with only `defaultValue` is uncontrolled (was forced to `null`, steppers dead).
- ds `Modal`: `headerActions` slot beside ×; no title => no header strip, controls float top-right (body keeps a gutter;
  floating window drags by its body only in that case). `AppModal` minimize moved next to × (ActionIcon); pill uses
  `--z-minimized-pill` (3490), below every modal and backdrop.
- Readable disabled states (ds Button / ActionIcon, DecisionFrame primary); bigger select caret; stronger loader track.
- Status headings render digits in the data font with a slashed zero (Naalu "0" no longer reads as "O").
- `Surface` falls back to ds tokens when no theme class is set; stronger grid/circle patterns.
- `/dev/ui`: applies the theme class, one-line sticky header + `scroll-margin-top`, real token names (hairlines were
  `h08/h36/h56` = undefined), framed swatches, working phase stepper / notice dismiss + reset, Drawer/Tooltip/Popover
  demos, footer-pinned Close in long modals, ds Buttons instead of raw buttons in the Transaction mock.

## Card lore: missing slots and missing display

- `gen_lore_template.py` only made slots for action cards / relics / exploration that had asset flavour, and none for
  generic units. Now every card in the game gets a slot (24 relic fragments, 12 attach cards, JR-XS455-O, 9 units).
- Attach exploration cards with an empty slot read their attachment's lore (`lookupCardLore`).
- Lore now shown: generic promissory notes in the library/deck browser, hover hints and ⓘ hint cards (action card,
  relic, exploration, planet), legendary planet ability card (`legendaryAbilityFlavourText`).
- Still empty, for the user to write: relic fragments, generic units, JR-XS455-O. Strategy cards have no lore kind.

## Intro → setup: no board flash

- The wizard enters `/game` with `state.newGame`; `GameSetupOverlay` shows its backdrop while web-data loads.
- The setup backdrop no longer fades in (only the panel does). New game drops the cached `playerData` (host and guest).
- Follow-up: slots for Corsair and Eidolon Maximum; The Cavalry unit cards read the promissory note's lore; no slots
  for never-displayed ids (Keleres `rider`, `enigmaticdevice` relic) or the fan-made Combat Transport. Held Enigmatic
  Device popup shows its exploration lore. Unit aliases (`LORE_ALIASES.unit`). `unitLoreId` prefers the unit's own slot (Corsair no longer looks under Cruiser II).

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
