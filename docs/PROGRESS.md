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
| — | Exploration cards & Galactic Events (0/20) | ✅ Exploration (77/80 + 3 manual); ⏸️ Galactic Events (0/20, deferred) |
| N | Network: N0 `actor_id` ✅, N1 tokens ✅, N2 projection ✅, N3 saves ✅, N5 part 1 ✅, N4 per-game lock ✅ | ✅ |
| QA | pytest-xdist/testmon, ruff, mypy --strict, E2E Playwright (solo + host/guest), ruling coverage guard | ✅ |

**Next steps (order):**
1. **Remaining factions (7):** Nekro, Keleres (Wave 3) → Deepwrought, Last Bastion, Crimson Rebellion, Ral Nel, Firmament/Obsidian (Wave 4).
2. **AI Bot (`docs/bot/PLAN.md`):** B4 (`arena`) → B5 (`legal_actions` for tactical action, combat, action cards) → B6 (`fast` state) → algorithms (evaluation, combat MC, RHEA).
3. **Gaps & audit:** mechanical/ruling gaps (`rulings_status.json`), unemitted timing events (`OKNA_CZASOWE.md`), and ruling debt (`tests/rulings_debt.json`: 93 items).
4. **Deferred (user decision 2026-11-27 — not doing for now):** Galactic Events (0/20), Absol agendas (13+60), general binding deals, hyperlanes, global `cannot` arbitration / interleaved `REACTION` offers.

> Full history of completed blocks with details: `PROGRESS_ARCHIWUM.md`.


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

## Bots roll their own combat side and fire AFB as defender

- After per-side combat rolls (each player clicks their own roll), `legal_tactical.combat` still offered
  AFB/Roll only to the attacker, and the bot's roll covered both sides. A bot defender never rolled its side,
  so a human attacking a bot hung at the roll step.
- Now each bot side gets `BattleRoll` for its own side only, until it has rolled (`side_rolls`). The action and
  HTTP mapping pass `faction` and call `roll_round(..., side)`. A human opponent still clicks their own roll.
- AFB (both sides at once in core) can be fired by either side's bot. It waits while a human opponent still has an
  AFB extra-dice choice (`afb_extra_sources`, RULES.md 62.11). `battle_close` is still for the attacker only.
- Tests: `tests/engine/test_legal_windows.py` (+3: defender bot rolls its side, attacker bot rolls only its
  side, defender bot fires AFB); fuzz/passive all-bot games green.

## Start screen: warp transition, faster faction reveal (user decision)

- Menu <-> setup no longer scrolls vertically: the screens are stacked and swap with a depth zoom + blur,
  plus a soft bloom and light ring on the way in (the user rejected a brighter flash). Reduced motion = cross-fade.
- Faction scene: portrait, header and lore reveal about twice as fast (`--t-*` in `Step_Faction.module.css`,
  fixed header durations in `FactionBackdrop.module.css`).
- QA: tsc, eslint, setup vitest, e2e (8 passed). No visual screenshot check.

## Structured wait reasons (who the game waits for and why, RULES.md 44.5)

- `core/actor.describe_wait_reasons(state, registry)` -> `WaitReason(player_id, reason_code, summary, blocking)`;
  `awaiting` is now derived from it. New relative to the old list: reaction pause / held card (all eligible, passes
  never read), hand-limit discard, granted production, Space Cannon target / Defense shooters, bombardment defender,
  per-side combat rolls; nothing is awaited after the game ends. Strategy secondary uses `secondary` (was `respond`).
- A hand-limit discard blocks only that player (others keep their reasons). After the last pass the last passer
  "may still end the turn" (non-blocking - the speaker can advance). Checked against bot moves: in 3 fuzz games
  (1259 moves) every move came from a blocking player, except timer releases of reaction windows (any seat) and
  that optional end of turn.
- `web-data.waitReasons`; header chip `TurnStatusChip` shows `PlayerTag` per player, groups equal reasons
  (`domains/network/waitReasons.ts`, replaces `describeAwaiting`). `web-data.awaiting` kept, unused by the UI.
- Diagnostics: `format_wait_reasons` in bot runner warnings (rejected, timed out, exception, new "Bot game stalled"
  check) and in fuzzer failures (`waiting: ...` line, `wait_reasons` in the dump).
- Tests: `tests/test_wait_reasons.py` (incl. non-interference: changing private data never changes the output),
  vitest `waitReasons`.

## Faster reactions + Push vs Pull cooperative effects (RULES.md 54.11-54.15, 30.13)

- Reaction windows: default 20 s (max 60). With Quick windows + a bluff range (new UI games: on, 8 s) every
  engine auto-pass lands at a private random moment (25-100% of the range) and an all-passed window closes
  at the last one - never at 0.0 s (`reaction_window.bluff_offset` / `schedule_auto_passes`, 54.13).
- "...unless something changes" pre-passes (54.13): lapse on another player's notable move (`note_change`:
  card / note played, agent used, retreat, extra hits); a notice says who did what. Optional auto-assignment
  of combat hits (`core/combat_auto_assign.py`, 54.14) through the normal assignment path (Sustain windows,
  Direct Hit, the protective pause fire as usual). Queued strategy card secondaries (30.13).
- Push vs Pull (54.15, `core/cooperative.py`): cooperative agents (Mendosa, Trilossa, Acamar, Taivra, I48S,
  Garv and Gunn, T'ro, Milor, Z'eu TE, Unlenn, Evelyn, Berekar, Sucaban, Tellurian) no longer open a
  window on another player's event - a boost is recorded and the beneficiary asks for it ("Boosts" in the
  hand dock, only while one is available). Owner's terms in the Reactions panel: Ask me / Standing offer
  (price, free for chosen players) / Self-only, plus "Watch" (this turn / combat). Accepting = payment (a
  normal transaction) + effect in ONE step; declined / withdrawn / lapsed = nothing paid. Push effects
  (Sabotage, Direct Hit, Cabal's agent...) unchanged.
- UI: `ReactionSettings` (notices, "unless something changes", combat hits, `CooperativeSettings`),
  `BoostsButton`, `SecondaryQueueChip`, deal line on the offer card (`DealLine`), Activity `boost.request`;
  Settings: 20 s / 60 s, bluff range 0-12 s.
- Tests: `test_cooperative.py` (23), `test_reaction_bluff.py`, `test_combat_auto_assign.py`,
  `test_secondary_queue.py`, `test_activity.py` (boost), faction / flow tests moved to the request flow
  (`tests/boosts.py`, `Flow.request_boost`); vitest `ReactionSettings`, `BoostsButton`, `DealLine`,
  `describeActivity.boosts`.
- ⚠️ ASSUMPTIONS for the user: see RULES.md 54.13-54.15 and 30.13 (bluff bounds and defaults, pull list,
  bot owner accepts a paid request, the owner picks the details on Ask me, price cap 20).

## B19 — The Yssaril Tribes (RULES.md 62.22, 2026-11-27)

- All 14 components (`src/core/hooks/factions/yssaril.py`): Stall Tactics, Scheming, Crafty, Transparasteel
  Plating, Mageon Implants, Ssruu, So Ata, Kyver (Guild of Spies), Spy Net, Y'sia Y'ssrila, Blackshade
  Infiltrator, Deepgloom Executable.
- Core points: leader proxy (`rules_hooks.register_leader_proxy` / `leader_proxy`: every other player's
  agent is a source of the Yssaril and reads/writes Ssruu's state in `leaders` + `exhaust`; copies listed in
  `faction_components.owned`, `COMPONENT_EXHAUSTED` carries `proxy`), draw batches
  (`card_draw.draw_action_cards` - one `ACTION_CARDS_DRAWN` per draw: Politics, status phase, Politics
  Rider, Unconventional Measures, Lost Crew), `card_draw.draw_without_event`, `discard_random_action_cards`,
  `hand_limit.unlimited` (PERMIT read before the limit MODIFY), `faction_components.granted_abilities`
  (`data.abilities` of an effect), `oi.info(show=True)` = read-only card chips in a decision.
- Cross fixes: Suffi An answers any player's Pillage against another player (Ssruu copy, ssruu 4); Temporal
  Command Suite readies Ssruu after a copy. Pre-existing guard fix: 6 audited files removed from
  `tests/rulings_debt.json` (`GENERAL_DEBT_LIMIT` 99 -> 93).
- Frontend: Kyver board FX `keyhole` (`YssarilFxMarks.tsx`, mist + fronds + keyhole, blade slash at the
  flash, a card lifted out; area `kyver` = every rival home), sound cues; `DecisionFields` shows `info`
  inputs with `show` as read-only card chips (So Ata / Kyver looks).
- Tests: `tests/factions/test_yssaril.py` (35), `test_flows_yssaril.py` (8), `test_activity.py` (Kyver areas,
  looks never name cards); vitest `yssarilFx`, `YssarilFxMarks`, `describeActivity.yssaril`, `DecisionFields`.
- Gap: Ssruu cannot copy JR-XS455-O (a relic agent - needs a relic proxy). ⚠️ ASSUMPTIONS ("Auto" defaults,
  sequential Kyver, Deepgloom grant to the end of the action phase): RULES.md 62.22.

## Cooperative effects: sellable components (RULES.md 54.15 e, 2026-11-27)

- `cooperative.PullSpec` (`mutual`, `target` / `target_of`, `owner_picks`) on `register_pull` /
  `register_pull_component`. Mutual = owner keeps the offer AND others may request; target = deal
  limited to the requester (offer form + 422 on another answer); owner_picks = the accepted request
  goes to the owner. `ACTION:` components / technologies are requestable on the owner's turn and use
  the owner's component action (`_accept_component`; Wormhole Generator via `_owner_components`).
  `spec_for(key, component=...)` separates a hook and a component on one key (Deepgloom).
- Registered every ticked row of `docs/faction_components_checklist.md` for implemented factions
  (Arborec, Cabal, Empyrean x5, Creuss x2, Hacan, Mentak, Muaat, Naalu, Nomad x3, Titans, Winnu,
  Xxcha, Yssaril). Ssruu inherits the copied agent's registration (proxy).
- Tests: `tests/test_cooperative_specs.py` (mutual, target 422, tech ACTION deal, own-turn only,
  Deepgloom shared key, Ssruu copy, guard over all ticked keys); Empyrean
  and Nomad tests moved to the request flow; `test_cooperative.py` updated (Cabal = mutual pull,
  `PullSpec`).
- Fix: `cooperative.prune` kept boosts on HTTP `offer:` / `reaction-pause` steps but dropped them on
  the bot engine's `bot:offer_*` / `bot:reaction_pause_release` (fuzz mismatch `boosts`) - aligned.
- Pre-existing failures at HEAD (not touched): `test_undo_move::test_active_player_undoes_own_move`,
  `test_player_undo::test_endpoint_undo_mine_cofa_aktywacje_tylko_autorowi`,
  `test_technologies_actions::test_kazda_karta_frontier_da_sie_rozstrzygnac_w_oknie_eksploracji`.
- ⚠️ ASSUMPTIONS: RULES.md 54.15 e (which effects are mutual / owner_picks; Watcher for third
  players; the Creuss picks the token's system).

## B20: The Mahact Gene-Sorcerers (RULES.md 62.23, 2026-11-27)

- All 14 components in `core/hooks/factions/mahact.py`. Central points: other players' tokens in the
  fleet pool (`PlayerState.foreign_fleet_tokens`; `command_tokens.fleet_pool_count` is THE fleet pool
  size - fleet report, Fleet Regulations cap; `remove_fleet_token` = own first, a foreign token goes to
  its owner - agendas, Neuroglaive, action cards routed through it), commander provider
  (`rules_hooks.register_commander_provider`, Imperia), PERMIT `tactical.activate_own_token`
  (Il Na Viroset: both tokens return, turn ends, only PN return conditions fire), FORBID
  `agenda.required_outcome` (Genetic Recombination, enforced in `cast_vote` / `abstain`), FORBID
  `promissory.cannot_receive` + `promissory_notes.giveable` / `purge_from_hand` (Hubris),
  `command_tokens.register_secondary_alternative` (Jae Mir Kan pays a secondary with the active
  player's board token), component space combat `battle.start_combat(source=, position=, attacker=,
  no_retreat=)` + `retreat_destinations` honouring `no_retreat` (Benediction), `technology.purge_technology`
  + `purged_technologies` (Vaults of the Heir; war suns leave with their upgrade).
- Cross fixes: `SHIPS_MOVED` carries `mover` (Voidwatch asks the mover, Nova Seed needs mover = owner)
  and can fire without its own window (`open_window=False` - Sai Seravus waits in the combat's start
  triggers); Armed Forces Standardization counts foreign fleet tokens (holder keeps / returns each);
  S'ula Mentarion / Diplomatic Pressure only offer receivable notes; `tactical_pn_owners` cleared for a
  component combat (no Betray a Friend).
- Frontend: Benediction board FX `benediction` (`MahactFxMarks.tsx`: gene-sigil over the origin, chain of
  command dragging the fleet, six binding links + crown at the combat system; areas `benediction_origin`
  / `benediction`), sounds; web data `mahactEdict` (existing command-sheet/map token UI), `canActivateOwnTokens`
  (tile menu "Activate again (Il Na Viroset...)"), `requiredOutcome` (vote panel note, preselected outcome,
  no abstain); secondary window: Jae Mir Kan switch + system picked on the map
  (`SecondaryTokenAlternatives`); unit keys (`units:...`) resolve to full unit names in the feed.
- Tests: `tests/factions/test_mahact.py` (53), `test_flows_mahact.py` (6), hero area feed; 7 cross-faction
  rulings waiting on the Mahact closed (Neuroglaive 1, Yin Ascendant 1.1, Nova Seed 1.1, AFS 1, Fleet
  Regulations 3, Rout 2, Sai Seravus 2.2); vitest `mahactFx`, `MahactFxMarks`, `describeActivity.mahact`.
- Gaps: Benediction "when you move your own ships" abilities other than Nova Seed are not filtered by
  `mover` (F_mahact benediction 2/2.1/2.3 tested only for Voidwatch / Nova Seed); Jae Mir Kan is ticked
  as cooperative in `faction_components_checklist.md` but a secondary payment is not a pull-able offer.
- ⚠️ ASSUMPTIONS (remaining Benediction capacity choice = cheapest-first, Crimson Legionnaires stay on the
  card without a home planet): RULES.md 62.23. The "Auto" defaults and own-first fleet token removal were
  replaced later (block "Auto only for spending and combat" below).

## Fix: 3 pre-existing failing backend tests (RULES.md 44.7)

- Undo vs presence: the identity middleware records "I'm back" (54.12 e) as its own history snapshot
  (`reaction-settings:presence`) for ANY player's POST - even a rejected one - so another player's click
  closed both player Undo (`/undo/mine`: "Another player has acted since") and `/tactical/undo-move` (422).
  Presence snapshots are now transparent to both (`reaction_prefs.PRESENCE_LABEL`), and presence is carried
  into the restored state like the clock (`reaction_prefs.carry_presence`); undo-move pops the presence
  snapshots on top together with the move and re-records current presence.
- `test_kazda_karta_frontier_da_sie_rozstrzygnac_w_oknie_eksploracji`: Mirage chains a cultural exploration
  from an unpinned deck; Freelancers (intentional `production_grant`) then blocked `finish()`. The test now
  pins the cultural deck to a relic fragment.
- Tests: new `test_migawka_obecnosci_innego_gracza_jest_przezroczysta`; targeted undo / exploration /
  reaction suites (585 passed), ruff, mypy. Full suite and frontend QA skipped (backend-only, targeted scope).

## "Auto" only for spending and combat (user decision 2026-11-27)

- Every non-spending, non-combat choice lost its "Auto": faction hooks (Empyrean, Creuss/Ghost, Mahact, Naalu
  Foresight, Nomad, Titans, Yssaril), action cards (War Effort / Ghost Ship board source, Unstable Planet,
  Refit Troops, Rescue cargo, Investments), agendas (Rearmament, Leadership Rider), Hil Colish move order and
  token redistribution (status phase, Leadership, Warfare, Predictive Intelligence, capacity / fleet pool
  removal windows - `autoAlloc.ts` deleted). Payments, trade goods and combat keep "Auto".
- `offer_inputs`: `choice(..., optional=True)` (field may be skipped, e.g. Mercer's 2nd ground force); a
  skipped `number` without "Auto" = its `min` (the stepper start); `cooperative` never adds an "Auto".
- Fleet pool removal is now ONE point, `command_tokens.remove_fleet_tokens(state, pid, n, reason)`: with tokens
  of several owners (Mahact Edict) the Mahact chooses which leave (`EDICT_REMOVE` decision, `own` count +
  `foreign` owners) instead of "own first". Used by Exchange Program, Clandestine Operations, Research Grant
  Reallocation, Fleet Regulations, Sanction, Genetic Recombination, Neuroglaive.
- Docs: resolved `⚠️ ASSUMPTION` markers in RULES.md 5, 13, 30-65 (user decisions / verified against tirules).
- Tests: updated `auto` asserts across faction and ruling tests; new `@ruling("F_mahact/edict/2")` choice test.

## Sustain Damage once per timing window; Emergency Repairs only units with SUSTAIN DAMAGE

- `ActiveCombat.sustain_spent` + `damage.repair_after_sustain` / `sustain_spent` / `forget_sustain_spent`: a unit
  the Dynamo repaired after it sustained cannot SUSTAIN DAMAGE again until the next Roll Dice step
  (`CombatUnit.spent`); destroyed undamaged units take the "spent" ones first; Direct Hit on a repaired ship
  clears its record. Closes gaps F_empyrean dynamo 1 and C_action_cards reflective-shielding 1.1.
- `battle_units.damaged_with_sustain`: Emergency Repairs repairs only damaged units that currently HAVE the
  ability (own, not lost/denied; The Cavalry's champion only during that combat) - closes F_nomad the-cavalry 2.4.
- Tests: `test_empyrean.py` (dynamo 1), `test_nomad.py` (cavalry 2.4), `test_reactions_combat.py` (reflective 1.1).

## Mecatol Rex: Thunder's Edge tile 112 (RULES.md 2)

- `map_string.is_mecatol_system` / `mecatol_system_id` and `legendary_planets.MECATOL_PLANETS` replace every
  `== "18"` / `"mr"` check (Custodians, Diplomacy, Imperial, Xxcha Peace Accords, Titans Terraform, objectives,
  Fracture ingress, web tiles, demo map, random map).
- ⚠️ ASSUMPTION (RULES.md 2, to confirm): with Thunder's Edge active, new maps use tile 112 (legendary
  *The Galactic Council*) and an explicit `18` is swapped for `112`.
- Tests: `test_map_string.py` (3 new), Mecatol asserts in `test_web_data.py`, `test_demo_map.py`,
  `test_random_map_new_game.py` follow the active tile.

QA (all three blocks): full backend suite (10 failures, all stale asserts, fixed and re-run: 270 passed in
those files), ruff, mypy; frontend `tsc`, eslint (changed files), vitest (62 files, 271 passed). Skipped:
`npm run build` (no new modules/imports), e2e (no wizard/flow change).

## Boosts: turn-end agents during your turn, debt-token payments, no Auto (RULES.md 54.15 f)

- `cooperative._turn_end_previews`: another player's cooperative "at the end of a player's turn" effect
  (Garv and Gunn, Field Marshal Mercer) is listed in the active player's Boosts panel once they have taken an
  action on their own turn (id `te:<owner>:<seq>`, rebuilt on read); accepting resolves it at once with the
  turn's `TURN END` context. ⚠️ ASSUMPTION: resolves on acceptance, not held until End turn.
- Deals may be paid with debt tokens (`request(..., debt_tokens=)`, `POST /boosts/request` `debt_tokens`):
  always possible (RULES.md 47.3), count towards a standing price, given on acceptance (`debt.give_debt_tokens`);
  `deal_view.debtTokens`, `DealLine` / outgoing request text show them.
- `BoostsButton`: no "Auto" (payment starts at 0), "Debt tokens" field always shown.
- Tests: `tests/test_cooperative_turn_end.py` (5), `BoostsButton.test.tsx` (updated).

## B17: The Nekro Virus (RULES.md 62.24)

- `core/hooks/factions/nekro.py`: every component (3 abilities, Valefar X/Y, Valefar Z, 3 leaders, Antivirus,
  The Alastor, Mordred). ⚠️ ASSUMPTION (to confirm): the Nekro starts owning `vax` + `vay` (data lists only `dxa`).
- Valefar X/Y copies: the copied tech id joins `technologies` + `PlayerState.assimilated`
  (`technology.assimilate` / `release_assimilated` - not a "gain"); exhaust/ready mirrored to the assimilator
  (`core/exhaust.py`); `resolve_unit_variant` accepts a copied faction unit upgrade (faction beats generic on a tie);
  losing a war sun copy removes war suns; `technology.owned_cards` (copies are not owned - AIR "Against").
- Valefar Z: `PlayerState.assimilated_flagships` + `rules_hooks.register_unit_source_provider` (other flagships'
  text hooks work for The Alastor); web data `valefarZTargets` / `valefarCopies`.
- Propagation: PERMIT `technology.research_replaced` in `apply_research` (WHEN fires, no tech, no AFTER/trace) +
  mandatory decision: one pool choice per token (bot-safe first answer); research view `propagation` banner in the TechnologyOverlay; plan_research
  allows an owned tech when replaced (Book of Latvinia: 6 tokens).
- Galactic Threat: PERMIT `agenda.cannot_vote` (`_open_card` blocks, unless `vote_unblockable`); prediction offer
  after reveal (once per agenda phase), correct -> mandatory gain from `voters_for`.
- Technological Singularity: once per combat, opponent's destruction in that combat, not vs Antivirus in play;
  shared gain form (TechnologyOverlay + X/Y/Z token). Commander Acidos skips card swaps (`grant_technology(replacement=True)`,
  Genetic Memory). Hero Devour World: planet on the map + tech of its specialty; `hero_planet` activity fact.
- The Alastor: `ActiveCombat.ground_as_ships` read by `ship_roles` / `combat_units` (space area only; ground forces
  on planets = gap). Fixed along the way: Salai Sai Corian and Raid Formation count ground forces fighting as
  ships; Develop Weaponry counts unit upgrades per unit type.
- Frontend: `HERO_BOARD_FX.nekrohero` + `NekroFxMarks` (viral hex lattice, tendrils, planet implosion, tech core,
  sigil; static sweep, flash/quake, 7 sound cues) aimed at the exact devoured planet; describeActivity tests.
- Tests: `test_nekro.py` (41), `test_rulings_nekro.py` (22, incl. 18 cross-file rulings that waited for the Nekro),
  `test_flows_nekro.py` (7), activity / hero-area feed, frontend `nekroFx`, `NekroFxMarks`, `describeActivity.nekro`.
  Gaps recorded in `rulings_status.json` (Alastor on planets, same-window gains, Infantry II card transfers).
