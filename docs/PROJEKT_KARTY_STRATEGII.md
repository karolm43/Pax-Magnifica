# Design: Playing Strategy Cards (Primary + Secondary, Network-Ready)

Status: ✅ IMPLEMENTED (2026-11) — all 8 cards in `core/strategy_cards/` (module per card,
UI views). Document remains as a record of design decisions; on divergence, code wins. Rules sources: `docs/rules_tirules/R_strategic_action.md`,
`R_strategy_card.md`, `R_leadership|diplomacy|politics|construction|trade|warfare|technology_sc|imperial.md`,
`R_action_phase.md`. Card texts: `assets/data/strategy_cards/pok.json` (+ `te.json`).

## 0. Strategy Card Set in Game (User DECISION, latest errata)

The `te` set from `assets/data/strategy_card_sets/strategyCardSets.json` applies
(registry picks it automatically when `thunders_edge` is enabled; `test_registry.py` enforces
order). Version of each card = latest errata:

| # | Card | Asset ID | Version source |
|---|------|----------|----------------|
| 1 | Leadership | `pok1leadership` | base |
| 2 | Diplomacy | `pok2diplomacy` | **codex1** (errata) |
| 3 | Politics | `pok3politics` | base |
| 4 | Construction | `te4construction` | **thunders_edge** |
| 5 | Trade | `pok5trade` | base |
| 6 | Warfare | `te6warfare` | **thunders_edge** |
| 7 | Technology | `pok7technology` | base |
| 8 | Imperial | `pok8imperial` | base |

Conclusion: old Construction (PDS/dock) and Warfare (remove token + redistribute) texts from
`pok.json` do NOT apply — we implement texts from `te.json`. tirules2.com lacks TE versions,
so `rules_tirules/R_construction.md` and `R_warfare.md` were rewritten locally for TE
(see `SOURCE.md`, "Local adaptations"); their `⚠️ ASSUMPTION`s await your confirmation.
Warfare secondary in TE: PRODUCTION of ALL units in home system (not only docks).

## 1. Why the Current Skeleton Is Not Enough

`core/strategic_action.py` today does: primary effect in ONE call → `STRATEGY_SECONDARY`
window → respondent "follow/pass" with no data. This only works for
Leadership (+3 tokens). Almost every card requires player CHOICES (system, planet, technology,
objective, token pool, players), and secondary requires a COST (strategy pool token, influence, resources).
Additionally:

- secondary does NOT deduct a strategy pool token today (rule: 1 token, Leadership exception;
  in Trade, players chosen by active player do secondary for free and MUST do it),
- a player without a token in strategy pool cannot "follow" (except Leadership),
- a passed player CAN do secondary (R_action_phase) — the window cannot skip them.

## 2. Model: Multi-Step Resolution Instead of One Shot

New state in `GameState`: `pending_strategy` (one active strategic action at a time):

```
StrategyResolution:
  initiative: int            # which card
  owner_id: str              # active player
  stage: PRIMARY | SECONDARY | DONE
  step: str                  # e.g. "choose_system", "ready_planets", "pay"
  draft: dict                # choices collected so far (validated, not yet committed)
```

- PRIMARY: step by step, only `owner_id` may send responses. Effect applied
  atomically at the end of a step (draft → state) so a misclick doesn't leave half-applied state.
- SECONDARY: still `TimingWindow(STRATEGY_SECONDARY)`, but respondent's answer is
  `{decision: follow|pass, payload: {...}}`, and "follow" enters the card's mini-steps
  (e.g. tech choice + payment) on the same window (cursor stays put until respondent
  finishes steps). Order: clockwise from player to the left of active player (already exists).
- Exhausting the card: after closing the secondary window (rule R_strategic_action). Today
  we exhaust on play — keep as a "played" flag, and set `exhausted` after the window.
- Each card = module `core/strategy_cards/<card>.py` with functions
  `primary_steps()`, `apply_primary(step, draft)`, `secondary_cost()`, `apply_secondary(...)`.
  Dispatch by initiative as today. Faction/tech asymmetry (e.g. Fleet Logistics: 2 actions per
  turn) as `rules_hooks` hooks (E7), not `if faction`.

## 3. Network: What Follows From This

- Server is authoritative; every response carries `player_id` and is checked against
  `owner_id` (primary) or `current_responder` (secondary). Nobody answers for someone else.
- Secondary window is SEQUENTIAL (one respondent at a time) — per rules and simplest
  over network: broadcast "now X is deciding", others see only who already decided and how
  (follow/pass), without private details.
- Hidden info: Politics (peeking 2 agenda cards) and drawn action cards/secret objectives go
  EXCLUSIVELY to the owner (`core/visibility.py`); publicly only "X looked at the agenda".
- Timeout/disconnect: `deadline` field on window and "auto-pass" policy (bot/admin) —
  to be decided with the network module; hot-seat for now, so omitted.
- Bot: same `core/` functions, bot responds through the same contract (`decision` + `payload`).
- Idempotency: every response carries `step` and `window_id`/`version`; stale response
  (delayed on network) is rejected 422/409 instead of applied twice.

## 4. Card Analysis (`te` set, see section 0)

UI legend: 0 = button/confirm suffices, S = small selector, M = map pick,
P = payment (influence/resources from planets), H = large dedicated view.

| # | Card | Primary (choices) | Secondary (cost + choices) | UI |
|---|------|-------------------|----------------------------|----|
| 1 | Leadership | +3 tokens (pool choice) → optionally spend influence: 1 token / 3 influence | Spend influence → tokens; NO strategy token | P + S (pool) |
| 2 | Diplomacy | Choose system (not Mecatol) with own planet → others place token → ready 2 planets | 1 strategy token → ready up to 2 planets | M + S (planets) |
| 3 | Politics | Choose new speaker (not current) → +2 action cards → peek 2 agenda cards, top/bottom, order | 1 strategy token → +2 action cards | S (player) + H-small (agenda, private) |
| 4 | Construction (TE) | 1 structure on own planet OR PRODUCTION of one dock → then 1 structure on own planet | 1 token → 1 structure on own planet | S (planet/structure) + Production |
| 5 | Trade | +3 TG, replenish commodities, pick players who do secondary for free | 1 token → replenish commodities (or free if picked) | S (multi-select players), rest 0 |
| 6 | Warfare (TE) | Tactical action in ANY system without placing token (system counts as activated); redistribute tokens before & after | 1 token → PRODUCTION of units in home system (token doesn't land in system) | M + tactical flow + redistribution |
| 7 | Technology | Research 1 tech + optionally 2nd for 6 resources | 1 token + 4 resources → 1 tech | **H (tech tree)** + P |
| 8 | Imperial | Score 1 public objective (if qualified) → Mecatol control: +1 VP, else secret objective | 1 token → draw secret objective | S (objective choice) + S (3-secret limit → return) |

Simplicity takeaway: "primary is simple" really holds only for Trade. Other
primaries also require choices, so primary must be step-based (section 2), not one POST.

### Per-Card Notes

- **Leadership:** needs an influence model (exhausting planets → sum of influence). Same
  payment mechanism is in `production.py`/`objective_payment.py` — extract a shared
  "PaymentPicker" (influence vs resources) and use across all cards with a cost.
- **Diplomacy:** other players' token from REINFORCEMENTS; no token in reinforcements → from command sheet
  (player choice, so this is also a PROMPT for other players, not just active). A player who
  already has a token in the system places nothing. "Diplomacy" token is cosmetic only (RULES note).
- **Politics:** speaker changes immediately (affects `speaker_id` and order); agenda peek
  is private. Action hand >7 → discard (existing hand limit).
- **Construction (TE):** structure = PDS or dock. Limits (1 dock / planet, 2 PDS / planet,
  Demilitarized Zone), missing unit in reinforcements → take unit from a system without a token
  (`⚠️` confirm on tirules whether TE keeps these notes). Primary has an "or" branch: structure
  OR dock PRODUCTION (reuse `core/production.py`), then second structure. Secondary no longer
  requires choosing a system or placing a token.
- **Warfare (TE):** free tactical action (no token, even if a token is already in the system)
  with token redistribution before and after. Enters existing tactical flow
  (`core/tactical.py`) with "no token" flag; secondary = PRODUCTION in home system without
  activation. Entire sequence counts as ONE strategic action.
- **Technology:** color prerequisites (`requirements` in assets: B/BB, etc.), colors from
  abilities/skips, faction technologies (`faction`), unit upgrades
  (`baseUpgrade`), exhausting (`exhausted_technologies`). Resource discounts from effects
  (e.g. cards/factions) via hooks.
- **Imperial:** scoring an objective exists (`objectives.score_public`); needs to be called from
  card context (without "status" step). Secret objective: limit 3 (including scored) →
  prompt to return an unscored one.

## 5. Which Cards Need Dedicated UI

1. **Technology — YES, largest view: `TechnologyOverlay`** (user decision: style of
   production window `frontend/src/domains/production/ProductionOverlay`, info-dense).
   Layout (to refine in mockup):
   - **Technology tree** with prerequisite links: columns by type from assets
     (`BIOTIC`, `CYBERNETIC`, `PROPULSION`, `WARFARE`) + `UNITUPGRADE` lane; rows by number of
     required symbols from `requirements`; lines connect technology to its prerequisites
     (unit upgrades via `baseUpgrade`). Faction technologies (`faction`) as a separate
     player lane, with `homebrewReplacesID`/replacements swapped.
   - **Tile states:** owned / available to research / locked (tooltip "missing: B, B") /
     exhausted (`exhausted_technologies`). Path highlight on hover.
   - **Production-style payment:** list of own planets as cards with exhausting
     (resources), planet tech specialties (`techSpecialties`) as icons — grant
     a "skip" of one prerequisite symbol, so tile unlocks when planet is exhausted;
     cost counter: primary 0 / 2nd 6 resources / secondary 4 resources + strategy pool token.
   - **Side panel:** technology text, prerequisites, what it unlocks, "Research" button.
   - Backend: pure function `core/technology.py` (`can_research`, `missing_prereqs`,
     `research`), data exclusively from assets. Reusable outside the card ("research a
     technology" abilities, Codex). Skip and specialty rules: check in `R_technology.md` /
     `C_technology.md`, not from memory.
2. **Politics — small modal** (private): speaker picker + peek 2 agenda cards with top/bottom order.
3. **Shared PaymentPicker** (influence or resources, exhausting planets) — Leadership, Technology;
   reuse from Production/Objective payment.
4. **Map pick mode** (system / own token): Diplomacy, Construction (+secondary), Warfare.
   Reuse "activate mode" mechanism from tactical action.
5. **Small selectors:** player picker (Politics, Trade), token pools (Leadership, Warfare),
   planets to ready (Diplomacy), public objective (Imperial), secret objective return.
6. **Confirm only (0):** Trade/Politics/Imperial secondary (after token cost).

Style of remaining cards (user decision): **simple, compact windows like the tactical action
panel (`TacticalActionPanel`/`MovementStepPanel`) or status steps** — dock with current card's
steps and short description, with map choices clicked directly. Only Technology
gets a large overlay.

Shared shell: one "Strategy Card Step Panel" component rendering the current `step` —
on the respondent's side, a follow/don't follow popup appears (`SecondaryDecisionModal` already
exists), and after "follow" the same panel with card steps. For Technology, the "research"
step opens `TechnologyOverlay`.

## 6. Proposed Implementation Order

1. (DONE) One-action-per-turn validation + UI greys out card after action/pass.
2. (DONE, RULES.md 30.5) Multi-step skeleton: `pending_strategy` + `/strategy/primary-step`,
   follow cost (strategy pool token, Leadership & "free" exceptions), passed players can follow,
   `CardSpec` in `core/strategic_action.py`, generic step modal. Reference card: Trade.
   Deferred: `window_id/version` contract (network idempotency), exhaust after window.
3. "Pure" cards: Imperial, Politics (no planet influence/payment). Trade already exists.
4. PaymentPicker + Leadership, Diplomacy.
5. Construction, Warfare (map + production).
6. Technology (tree) — separate block due to largest UI and research model.
7. (`te` set already agreed — section 0; Construction/Warfare go straight in TE version.)

## 7. Open Questions

- Network timeout/auto-pass: when do we decide policy (hot-seat for now)?
- Should the Technology box be universal from the start (reused for other research sources)? Recommendation: yes.
