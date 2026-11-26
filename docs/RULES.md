# Verified Twilight Imperium 4 Rules (Source of Truth for Code)

This file is the **single source of truth** for TI4 rules implemented in the code.
Project rule (spec 5.1): no rule or stat is ever coded from memory.
Every rule below has a reference to an official source.

Verification status of each rule:
- ✅ **VERIFIED** — confirmed in the official Living Rules Reference (LRR) / wiki.
- ⚠️ **ASSUMPTION** — coded temporarily, requires confirmation by someone who knows the game.
- ⬜ **TODO** — rule not yet implemented.

**Primary sources** (in order of precedence):
- 🥇 **tirules2.com — PRIMARY SOURCE OF TRUTH:** https://www.tirules2.com/
  Full Living Rules Reference 2.0 (PoK) + Codex notes (up to IV, 06/2025) and preliminary
  Thunder's Edge notes (10/2025), plus rulings by Dane Beltrami (TI4 lead designer)
  and community consensus. Every rule in this file is verified here first;
  topics have dedicated subpages (e.g. "Anomalies", "Movement", "Space Combat").
  Other sources are auxiliary/backup.
- 📁 **LOCAL DUMP (offline, fastest):** [`docs/rules_tirules/`](rules_tirules/INDEX.md)
  — complete dump of tirules2.com (149 topics: 109 rules, 30 factions, 10 components)
  in Markdown + `tirules.json`. **Check rules HERE first** (no
  online requests). Refresh and attribution: [`docs/rules_tirules/SOURCE.md`](rules_tirules/SOURCE.md).
  When the local dump isn't enough, check live tirules2.com.
  > **These are RULES and CLARIFICATIONS** (edge cases, interactions, Dane's rulings) —
  > NOT descriptions of how faction/card abilities work. Full component descriptions are in
  > AsyncTI4 JSON assets; `F_*`/`C_*` files contain only clarification notes (see `SOURCE.md`).
- Living Rules Reference 2.0 (Prophecy of Kings), FFG, 09/2020 —
  [PDF](https://images-cdn.fantasyflightgames.com/filer_public/51/55/51552c7f-c05c-445b-84bf-4b073456d008/ti10_pok_living_rules_reference_20_web.pdf)
- TI Wiki (mirrors LRR): https://twilight-imperium.fandom.com/wiki/Anomalies

> Note: all rules can be overridden by cards and special abilities
> (factions, technologies, action cards). We handle this via `rules_hooks` (asymmetry).

---

## Table of Contents (sections in separate files)

RULES.md is an INDEX. Each section's content lives in `docs/rules/R<no>.md` (numbering unchanged, so
references like "RULES.md 43.1a" are read in `rules/R43.md`). Subsections 2a–2e are in `R02.md`, 3a in `R03.md`.
Read ONLY the section file you need. Add a new rule to its section file (or a new `R<no>.md` + row here).

| # | Section | Lines |
|---|---|---:|
| 1 | [Anomalies](rules/R01.md) | 48 |
| 2 | [Adjacency and wormholes](rules/R02.md) | 220 |
| 3 | [Movement](rules/R03.md) | 60 |
| 4 | [Stat-area positions (player-stats hexes)](rules/R04.md) | 26 |
| 5 | [Starting command counters](rules/R05.md) | 13 |
| 6 | [Game phases — mapping to frontend format](rules/R06.md) | 15 |
| 7 | [Planet economy: optimal / flex](rules/R07.md) | 13 |
| 8 | [Faction leaders (agent/commander/hero)](rules/R08.md) | 12 |
| 9 | [Action phase turn order and pass](rules/R09.md) | 19 |
| 10 | [Owned units and upgrades (unitsOwned)](rules/R10.md) | 45 |
| 11 | [Player identity key in web-data (panel↔map desync)](rules/R11.md) | 23 |
| 12 | [Planet control — single source of truth (option A)](rules/R12.md) | 21 |
| 13 | [Strategy phase (strategy card selection)](rules/R13.md) | 79 |
| 14 | [Data sources: codexes + thunders_edge, errata dedup](rules/R14.md) | 59 |
| 15 | [Planet type: `planetTypes` (list) vs `planetType` field](rules/R15.md) | 17 |
| 16 | [Faction starting technology selection](rules/R16.md) | 49 |
| 17 | [Off-board home systems: Ghost of Creuss, Crimson Rebellion](rules/R17.md) | 27 |
| 18 | [Player panel: abilities, faction technologies, breakthroughs](rules/R18.md) | 38 |
| 19 | [Tactical action: system activation + step state machine](rules/R19.md) | 41 |
| 20 | [Combat: numeric helpers (assistant, not referee)](rules/R20.md) | 32 |
| 21 | [Establishing planet control (invasion)](rules/R21.md) | 18 |
| 22 | [Production: numeric helper (cost + resources)](rules/R22.md) | 19 |
| 23 | [Planet control when placing units (auto)](rules/R23.md) | 28 |
| 24 | [Player order: seating order, speaker, strategy card selection](rules/R24.md) | 38 |
| 25 | [Unit drag-and-drop movement (UI/God-Mode)](rules/R25.md) | 40 |
| 26 | [Unit placement when moving: ship↔space, ground↔planet](rules/R26.md) | 38 |
| 27 | [Exhausting components: planets, technologies, leaders (exhaust/ready)](rules/R27.md) | 45 |
| 28 | [Playable factions vs system placeholders (Neutral/Lazax)](rules/R28.md) | 50 |
| 29 | [DIRECTION SHIFT: REFEREE engine + timing windows (replaces "assistant, not referee")](rules/R29.md) | 85 |
| 30 | [Strategic action: primary + secondary window](rules/R30.md) | 184 |
| 31 | [Action phase flow validation + active player (hard enforcement)](rules/R31.md) | 287 |
| 32 | [Ship movement: legality enforcement (tactical action)](rules/R32.md) | 99 |
| 33 | [Activation and production validation (hard enforcement)](rules/R33.md) | 103 |
| 34 | [Component timing spec: trigger → window type](rules/R34.md) | 21 |
| 35 | [Reference integrity: `<color>` promissory notes placeholder as TEMPLATE](rules/R35.md) | 31 |
| 36 | [Hand limits and bot difficulty level set](rules/R36.md) | 48 |
| 37 | [Data audit results (baseline, reference gaps, assumptions)](rules/R37.md) | 92 |
| 38 | [Space Cannon Offense: order, range (Deep Space Cannon), rolls, hits](rules/R38.md) | 67 |
| 39 | [Combat (space and ground): rounds, AFB, rolls, Sustain Damage, hits](rules/R39.md) | 125 |
| 40 | [Invasion: Bombardment, Commit, Space Cannon Defense, ground combat, Establish Control](rules/R40.md) | 35 |
| 41 | [Status phase, public/secret objectives, victory points](rules/R41.md) | 46 |
| 42 | [Fleet pool: system ship limit and excess removal](rules/R42.md) | 35 |
| 43 | [Asymmetry and exceptions (factions, action cards, agendas): hook architecture rules](rules/R43.md) | 172 |
| 44 | [Networked multiplayer (up to 6 players): identity, auth, visibility, `actor_id` rule](rules/R44.md) | 66 |
| 45 | [Initial setup: secret objectives, PNs, Custodians token, public objectives](rules/R45.md) | 27 |
| 46 | [Planet exploration after establishing control](rules/R46.md) | 41 |
| 47 | [Player transactions + debt tokens](rules/R47.md) | 36 |
| 48 | [Game end: round limit and epilogue (honorable / dishonorable vote)](rules/R48.md) | 18 |
| 49 | [Technology research + Technology card](rules/R49.md) | 45 |
| 50 | [Thunder's Edge: expeditions, The Fracture, Thunder's Edge](rules/R50.md) | 74 |
| 51 | [Agenda phase: reveal, voting, outcome, planets](rules/R51.md) | 34 |
| 52 | [Custodians token: removal during Mecatol Rex invasion](rules/R52.md) | 25 |
| 53 | [Playing action cards (ACTION window) + effects as hooks + hand limit (53.8)](rules/R53.md) | 64 |
| 54 | [Event base and timing windows (event engine)](rules/R54.md) | 20 |
| 55 | [General technologies as hooks](rules/R55.md) | 32 |
| 56 | [Player decisions and technology offers (never automatic) — user decision 2026-11-09](rules/R56.md) | 12 |
| 57 | [ACTION technologies, non-action abilities, frontier and "free" production — user decision 2026-11-09](rules/R57.md) | 28 |
| 58 | [Player chess clock](rules/R58.md) | 31 |
| 59 | [Relics — ownership, "ACTION:" actions, passive and event effects](rules/R59.md) | 24 |
| 60 | [Legendary planets — ability cards, readying, and abilities](rules/R60.md) | 25 |
| 61 | [Faction foundations — leaders, promissory notes, abilities, breakthroughs, unit capture (61.5), faction tokens on map (61.6), player-dependent adjacency (61.7)](rules/R61.md) | 53 |
| 62 | [Factions — faction components (B1: Sardakk N'orr, Barony of Letnev; B2: Jol-Nar; B3: Sol, Arborec, … B7: Yin, B8: Argent, B9: L1Z1X, B10: Muaat, B11: Saar, Naaz-Rokha; B12: Naalu; B13: Vuil'raith Cabal; B14: Titans of Ul; B15: Ghosts of Creuss)](rules/R62.md) | 287 |
| 63 | [Empty reserve → unit from board; C_/F_ rulings audit (2026-11-15)](rules/R63.md) | 52 |
| 64 | [Key game moments — animations for everyone, hero effects on board, phase transitions (2026-11-16)](rules/R64.md) | 58 |
| 65 | [AI Bot — decision layer design rules (single rules path, information, local compute, budget) (2026-11-16)](rules/R65.md) | 57 |
| 66 | [Player elimination — conditions, check timing, consequences (2026-11-18)](rules/R66.md) | 39 |
