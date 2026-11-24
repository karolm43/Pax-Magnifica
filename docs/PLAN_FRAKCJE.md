# Plan: Factions (H5 / E7) — Session-Sized Blocks

Implementation plan for **all faction components**: abilities, faction technologies, leaders
(agent / commander / hero), breakthrough (Thunder's Edge), faction promissory notes, and faction units
(flagship, mech, special units). Expands section "H5 — Factions" from
`PLAN_PELNA_ROZGRYWKA.md`. Plan: 2026-11-11, status (§6): 2026-11-17.

> **Overriding rule unchanged:** texts and numbers EXCLUSIVELY from assets (`registry.catalog`,
> `catalog.faction_bundle(<id>)`), rule in `docs/rules/R<NN>.md` BEFORE it enters code, exception =
> hook (never `if faction == ...` in a base rule). Mechanic descriptions below are APPROXIMATE (for
> planning) — the card text in the data is authoritative.

---

## 1. Starting Point (verified in code)

> **Historical state (2026-11-11, before F1–F3)** — the table describes the baseline for the plan, not the current state.
> Current state: §6 and `POKRYCIE_HOOKOW.md` §7. Since F1–F3, leaders, PNs, and breakthroughs have a full lifecycle
> (unlock, play, return), and in the 10 completed factions all leaders, PNs, and breakthroughs have
> hooks (as of 2026-11-17).

| Area | Status | What it means for factions |
|---|---|---|
| Hook registry, `SOURCE_FACTION/LEADER/BREAKTHROUGH/PROMISSORY` sources | ✅ | `owned_sources` already returns faction (id **and** family), unlocked leaders, unlocked breakthrough, PNs in play area. Hooks can be written right away. |
| Event engine + "may" offers (`on_event`, `PendingOffer`, `OffersModal`) | ✅ | "When/After … you may" abilities = same pattern as general technologies (RULES 56). |
| Component action with dispatch (`component_action` → `register_effect`) | ✅ for action cards, techs, relics, planets | Missing branches for **leaders, faction abilities, breakthrough, PNs**. |
| Leaders | ⚠️ state only (`leader_states`, `exhaust_leader/ready_leader`, God-Mode) | **Missing** unlock condition checks (`unlockCondition` in data), hero purge, playing ACTION. |
| Promissory notes | ⚠️ hand + `transfer` + play area (`promissory_notes_in_play`) | **Missing** playing from hand, effects, return to owner. 5 generic notes (`_cf, _ps, _sftt, _ta, _an`) also have no effects. |
| Breakthrough | ⚠️ `unlock_breakthrough`, `exhaust/ready_breakthrough` | No effects (0/31). |
| Faction units | ✅ stats from data (`resolve_unit_variant`) | `ability` field (flagships, mechs) has no hooks; coverage report does not count them. |
| Faction hooks | 1 (Arborec: space docks cannot produce infantry) | Faction coverage in `POKRYCIE_HOOKOW.md` §7: **0 / ~300**. |
| Cross-faction shared mechanics | ❌ | **Capture** — ~40 faction components; **coexist** — ~27; **faction tokens on map** (sleeper, breach, Creuss wormhole, galvanize); **player-dependent adjacency** (Creuss, Crimson, Empyrean). |

**Key pitfall:** faction family (`registry.faction_family` = `shortName`) differs from id:
`ghost→creuss`, `jolnar→jol-nar`, `naaz→naaz-rokha`, `titans→ul`, `cabal→vuil'raith`,
`ralnel→ral nel`, `crimson→rebellion`, `keleres{a,m,x}→keleres`. A hook can be registered under id
(`ghost`) — `owned_sources` provides both keys — but cards in data (`faction: ...`) reference the FAMILY.

---

## 2. Template for One Faction Block (DoD)

Every faction block goes through the same pipeline (pattern: `ARCHITEKTURA_KODU.md` §3a):

1. **Inventory** — `catalog.faction_bundle(<id>)` + faction units; list components and their windows
   (`OKNA_CZASOWE.md`, grep by id — do not read in full).
2. **Rules** — faction subsection in `docs/rules/R62.md` (see §5): text from data → interpretation
   → source (tirules / LRR / rulings) → `⚠️ ASSUMPTION`s for user confirmation.
3. **Code** — module `src/core/hooks/factions/<id>.py` (one file per faction, ~≤500 lines), every
   hook with `covers="<category>:<id>"`; missing hook point → add in ONE central
   function (RULES 43.1a), not in the base rule.
4. **Tests** — `tests/factions/test_<id>.py`, pair convention (without exception / with exception) + faction
   completeness test (every component `IMPLEMENTED` or explicitly `MANUAL` in `effects_status.json`).
   **+ scenarios through the real API** (user decision 2026-11-12): `tests/factions/test_flows_<id>.py`
   on harness `tests/factions/flow_harness.py` (new game, God-Mode situation patch, real endpoints),
   `@covers(...)` for EVERY interactive component (offer, use in window 62.0, ACTION, PN).
   They verify what the player sees: offer in `/offers`, "Available now", playability. Guard
   `tests/factions/test_flow_coverage.py` will not pass a faction (module in `core/hooks/factions`) without them.
5. **UI** — only what shared windows don't cover (offers, component action form, leader
   menu). A new faction-specific window = exception, justified in PROGRESS.
6. **QA + wrap-up** — full backend QA (+ frontend if touched), refresh
   `POKRYCIE_HOOKOW.md` and `OKNA_CZASOWE.md`, short section in `PROGRESS.md`, commit.

**Session size:** ~10–12 components and ≤2 new UI elements. A "simple" faction (modifiers,
few windows) → two per session. A structural faction (new board / deck mechanic) → one or
two sessions.

---

## 3. Blocks (execution order)

Legend: **[F]** foundation, **[I]** shared mechanic, **[B]** faction block. Number in parentheses =
faction components per `POKRYCIE_HOOKOW.md` §7 (+ flagship/mech).

### Wave 0 — foundations (without these, factions cannot close)

**F1 · Leaders: lifecycle** (1 session) — `RULES 61.1`
- Commander and hero unlock conditions: predicate registry `register_unlock("leaders:<id>")`
  checked after events (planet control, scoring, research, combat…) → unlock + entry in
  log. Without a predicate = manual unlock button (MANUAL), so the game never deadlocks.
- Agent: exhaust on use; hero: purge (new state `purged`).
- Dispatch in `component_action` for leaders with "ACTION:" + offers for "When/After" (source already exists).
- Leader menu in player panel: "Use" (legal only when usable) instead of God-Mode only.
- Pilot: 1–2 leaders with a simple effect to test the path end-to-end.

**F2 · Promissory notes: play and return** (1 session) — `RULES 61.2`
- Playing a PN from hand (by dragging, like action cards; only legal ones can be picked up), forbidding
  playing your own, placing in recipient's play area, returning to owner per card text condition.
- Reaction PNs in STOP model (hidden hand — like action cards, RULES 43.4).
- 5 generic notes as template: Ceasefire, Political Secret, Support for the Throne,
  Trade Agreement, Alliance (Alliance = sharing commander ability → depends on F1).

**F3 · Abilities, breakthroughs, faction units + scaffolding** (1 session) — `RULES 61.3`
- ACTION dispatch for faction abilities (`abilities:<id>`) and breakthrough (`breakthroughs:<id>`).
- Hook source for faction units with `ability` field (flagship/mech "on board"):
  key `units:<id>`, helper "does player have this unit in system X".
- Coverage report: add faction units category; per-faction completeness test.
- Package `src/core/hooks/factions/` (move `factions_base.py` → `factions/arborec.py`),
  `tests/factions/` template, faction ability indicators in player panel (pattern `TECH_CONTEXTS`).

### Wave 1 — modifiers and simple windows (pipeline pilot)

| Block | Factions | Scope / new hook points |
|---|---|---|
| **B1** | Sardakk N'orr (8) + Barony of Letnev (9) | Combat roll modifiers, reroll for TG at start of round, fleet limit (`fleet_pool.capacity` point). Best pilot: minimal UI. |
| **B2** | Universities of Jol-Nar (10) | −1 to rolls, Technology secondary as primary, ignoring prerequisites when researching (point in `technology`). |
| **B3** | Federation of Sol (9) + Arborec (8, finish) | ACTION for strategy token (placing infantry), +1 token in status, Mitosis at start of status. |
| **B4** | Emirates of Hacan (10) + Winnu (9) | Transactions (RULES 47): without adjacency, action cards in transaction, Trade secondary without token; Mecatol/Custodians free, structures after taking Mecatol. |

### Wave 2 — abilities with reaction windows / decisions

| Block | Factions | Scope |
|---|---|---|
| **B5** | Mentak Coalition (9) | Ambush (pre-combat roll), Pillage (reaction to neighbor's TG/transaction). |
| **B6** | Xxcha Kingdom (10) | Peace Accords (after Diplomacy), Quash (swap agenda) — touches `agenda_phase`. |
| **B7** | Yin Brotherhood (9) | Indoctrination (start of ground combat, pay influence), Devotion (sacrifice ship = hit). |
| **B8** | Argent Flight (9) | Zeal (votes + vote first), Raid Formation (excess AFB). |
| **B9** | L1Z1X Mindnet (9) | Assimilate (replace structures on capture), Harrow (bombardment after ground combat round). |
| **B10** | Embers of Muaat (9) | Star Forge (ACTION), move through supernovas, board-altering hero. |
| **B11** | Clan of Saar (9) + Naaz-Rokha (9) | Floating docks, scoring without home control, +1 TG on capture; extra exploration card, fragments → relic/token, mech in space. |
| **B12** | Naalu Collective (10) | "0" token (initiative order — `turn_flow`), Foresight (retreat with strategy token). |

### Wave 3 — shared mechanics + structural factions

| Block | Scope |
|---|---|
| **I1 · Capture** | Player's captured units zone (state, return, limits, panel view), rule from tirules (`R_capture`) — shared across ~40 components. |
| **B13** | Vuil'Raith Cabal (10): Devour, Amalgamation, Riftmeld, gravity-rift dock, hero. |
| **I2 · Faction tokens on map** | Token layer in system/on planet (sleeper, breach, Creuss wormhole, galvanize under unit), render + God-Mode. |
| **B14** | Titans of Ul (10): Terragenesis, Awaken, Coalescence, Terraform PN. |
| **I3 · Player-dependent adjacency** | Point `adjacency.extra_for_player` in board graph (adjacency ≠ traversability — separate layer). |
| **B15** | Ghosts of Creuss (10): Quantum Entanglement, Slipstream, Creuss Gate, wormhole tokens (I2+I3). |
| **B16** | Empyrean (11): Voidborn, Aetherpassage, Dark Whispers (2 PNs). |
| **B17** | Nekro Virus (12): Valefar Assimilator, Technological Singularity, Galactic Threat (agenda prediction), Propagation (tokens instead of research). |
| **B18** | Nomad (11): 3 agents (The Company), flagship upgrade, Future Sight. |
| **B19** | Yssaril Tribes (10): Stall Tactics, Scheming, Crafty; agent copying other players' agents → **after all agents**. |
| **B20** | Mahact Gene-Sorcerers (10): Edict (other players' tokens in fleet pool), Imperia (other players' commanders → **after F1 and most factions**), Hubris. |
| **B21** | Council Keleres (16, 3 variants): The Tribuni (setup after others, take home), Council Patronage, Law's Order (ignore laws → **requires agenda effects**), 3 heroes. Possibly 2 sessions. |

### Wave 4 — Thunder's Edge

| Block | Scope |
|---|---|
| **I4 · Coexist** | Shared units on a planet without combat, impact on control/production/objectives — ~27 components. |
| **B22** | Deepwrought Scholarate (9): Research Team, Oceanbound (ocean cards) + setup debt: 2 starting technologies from empty options list (RULES 16). |
| **B23** | Last Bastion (11): Liberate, Galvanize (tokens from I2), Phoenix Standard. |
| **B24** | Crimson Rebellion (13): Sundered, Incursion (breach, I2+I3), Sorrow (home tile). |
| **B25** | Ral Nel Consortium (9): Survival Instinct (movement reaction), Miniaturization (structures in space). |
| **B26–B27** | Firmament → Obsidian (9 + flip): plot cards (scoring others' secrets), Puppets of the Blade, flip to Obsidian (The Blade's Orchestra, flipping components). 2 sessions. |

**Total:** 3 foundations + 4 shared mechanics + 27 faction blocks ≈ **34 sessions**.

---

## 4. Dependencies and Risks

- **Agenda effects (0/123)** are in `PROGRESS.md` ahead of factions. Only Keleres has a hard dependency
  (Law's Order); Xxcha/Argent/Nekro only need the agenda phase (✅). Waves 0–2 can run in parallel
  with agendas.
- **Other factions' agents/commanders** (Yssaril, Mahact, Alliance PN): do those factions last,
  once most leaders work.
- **at_start/at_end/during hooks** (16 unemitted events): wire event emission in the block
  that first needs it (`test_emitted_by_zgadza_sie_z_kodem`).
- **Bot (Stage 3):** every hook with a decision must have `inputs` (form) — the bot will get the same
  choices as a human. No hidden autos (RULES 56).
- **Size risk:** factions with a board-rebuilding hero (Muaat, Creuss, Titans) — the hero
  can go into a separate mini-session so the rest of the faction doesn't wait.

---

## 5. Rule Numbering

- `docs/rules/R61.md` — faction foundations: 61.1 leaders, 61.2 promissory notes, 61.3 abilities /
  breakthroughs / faction units, 61.4+ shared mechanics (capture, tokens, adjacency, coexist).
- `docs/rules/R62.md` — factions: one subsection per faction in implementation order (62.1 Sardakk,
  62.2 Letnev, …). If the file exceeds ~400 lines — split into `R63.md` (Wave 3) and `R64.md` (TE).

## 6. Block Status

| Block | Status |
|---|---|
| F1 Leaders | ✅ 2026-11-12 (RULES 61.1) |
| F2 Promissory notes | ✅ 2026-11-12 (RULES 61.2, 5 generic notes) |
| F3 Abilities / breakthroughs / units | ✅ 2026-11-12 (RULES 61.3–61.4) |
| B1–B12 (Waves 1–2) | 🟡 B1 ✅ 2026-11-12: Sardakk (62.1), Letnev (62.2); B2 ✅ Jol-Nar (62.3); B3 ✅ Sol (62.4), Arborec (62.5); B4 ✅ 2026-11-13 Hacan (62.6), Winnu (62.7); Wave 1 wrap-up (2026-11-13: group A rulings, hand limit 53.8, Imperator separate); B5 ✅ 2026-11-13 Mentak (62.8); B6 ✅ 2026-11-16 Xxcha (62.9); B7 ✅ 2026-11-16 Yin (62.10); B8 ✅ 2026-11-18 Argent (62.11); B9 L1Z1X (62.12), B10 Muaat (62.13), B11 Saar (62.14) & Naaz-Rokha (62.15); B12 ✅ 2026-11-22 Naalu (62.16) |
| Rulings contract (every `F_<faction>.md` point & component sentence = test or status) | ✅ for 10 factions of Waves 1–2: pilot Xxcha + Arborec, Yin, Hacan (2026-11-16); Jol-Nar, Letnev, Mentak, Sardakk, Winnu, Sol (2026-11-17); Argent in B8 (2026-11-18); Naalu in B12 (2026-11-22); Vuil'raith Cabal in B13 (2026-11-22); Titans of Ul in B14 (2026-11-23). Each subsequent faction passes it in its block (`uv run python -m tests.rulings <faction>`) |
| I1–I3, B13–B21 (Wave 3) | 🟡 I1 ✅ 2026-11-22 capture (RULES.md 61.5, `core/capture.py`); B13 ✅ 2026-11-22 Vuil'raith Cabal (62.17); I2 🟡 2026-11-23 faction tokens — sleeper (61.6, `core/faction_tokens.py`; breach/galvanize/Creuss wormhole in faction blocks); B14 ✅ 2026-11-23 Titans of Ul (62.18) — next I3 |
| I4, B22–B27 (Wave 4) | ⬜ |
