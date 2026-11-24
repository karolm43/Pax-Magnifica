# Plan: Decision Windows — Consistency, Readability, Less Clutter

Status: 2026-11-23. Basis: code review + screenshots from an isolated game (Sol + 5 bots, Leadership,
action card, technology, status phase, agenda phase). Executed in blocks U1–U6; each block = code +
tests + section in `PROGRESS.md` + commit.

## Target Principles (one pattern for all windows)

1. **One decision on screen at a time.** Decision windows occupy one spot ("decision zone");
   queued ones wait as a "+N more" counter, not as a second window.
2. **One window frame** (`DecisionFrame`): header = component chip (same as in player panel,
   ⓘ on click) + kind badge (Primary / Secondary / Action card / Required);
   body = full text in normal color; fields; footer = [Never ask] [Skip/Cancel Esc] [Action Enter].
   No second title above the frame.
3. **One widget set:** one `Stepper`, one payment (`Payment`), one token allocation
   (`CommandPools`), one option tile (`Tile`). "Auto" always in the same place and style
   (helper button beside the field; primary action always in the footer, strongest color).
4. **Every piece of info once.** Who decides — in the window frame (not repeated in side panel and bar);
   counts (votes, queue) — in one place.
5. **Nothing obscures the decision window:** planet tooltips, reaction toasts, hand dock, "Decisions" panel
   yield to the decision zone.
6. Also need to rework "don't do something" cases, e.g. not using hero / do not place — currently too hard to read.

## What Screenshots Showed (evidence)

| # | Location | Problem |
|---|---|---|
| Z1 | Status phase | Two decision windows at once: status panel (Sol) + Mitosis offer (Arborec), plus "Reaction window" panel, Effects tray, and "PLAYED" card |
| Z2 | Agenda | "Decisions / Timing windows" panel sits on top of the Ballot card text (unreadable); reaction toast covers Senate list and outcomes; hand dock covers bottom of outcomes |
| Z3 | Agenda | "Votes available" shown 3×: Senate arc + list under arc, seat list "N to spend", each outcome "N votes available"; "Agenda 1 of 2" 2× |
| Z4 | Leadership primary/secondary | Double header: "STRATEGIC ACTION" / "STRATEGY CARD — SECONDARY ABILITY" + "Leadership PRIMARY" frame |
| Z5 | Leadership | Token allocation without "Auto"; different look from `CommandPools` in status phase (rows vs columns) |
| Z6 | Status phase | "Auto" is orange and stronger than "Confirm"; in other windows "Auto" is subtle |
| Z7 | Secondary Leadership | "Follow" available even though player has 2 influence (can't buy anything) → dead end with only "Back" |
| Z8 | Secondary | Respondent shown 3× (top bar, side panel "Responding", window "Your call"); queue 2× ("Remaining in queue: 5" and "Remaining after you: 4") |
| Z9 | Component action | List duplicates action cards visible in hand; intro text outdated; missing description and ⓘ |
| Z10 | Sling Relay | Planet tooltip (Mecatol Rex) pops up over the form and covers the selection field |
| Z11 | Use modals (card/tech/leader/legendary) | Card text grey (`dimmed`), title as plain text instead of chip, no Enter/Esc |
| Z12 | Mitosis offer | Title "Mitosis" 2× (header + field label); text of two abilities glued without a period ("…infantry At the start…"); "Required" badge barely visible |
| Z13 | Bar/coach | In status phase bar says "take a turn"; "What now?" coach in test mode says "Watch the map" even though it's player's turn; notification "Player p1 revealed…" instead of faction name |
| Z14 | No board | With strategy window open, board is barely visible: left panel + window + right panel + hand dock + strategy cards zone |

## Implementation Blocks

### U1 — Shared Decision Window Frame (foundation)
- `shared/ui/DecisionFrame` extracted from `OfferDock`: header with component chip
  (`Tech`, `ComponentInfoButton`, strategy card by `ComponentRef`), badges, text
  (normal color, collapse > 420 chars), fields slot, footer with Enter/Esc.
- Rewire: `OfferDock`, `ActionCardPlayModal`, `TechnologyUseModal`, `LegendaryUseModal`,
  `FactionComponentUseModal` (4 modals → one `ComponentUseModal` + kind config).
- Strategy cards `PromptShell` = `DecisionFrame`; remove `AppModal` title (Z4).
- Unified copy: "Cancel", "Use", one no-targets message; exhausted = message
  instead of form (Z11).
- Tests: frame vitest (Enter/Esc, Required, chip), update modal tests; e2e (always-mounted
  component).

### U2 — One Widget Set
- One `Stepper` (from `DecisionTiles`) instead of 5 copies (PromptParts, TradingTable,
  RemovalWindowModal, CommandPools).
- Payment: one widget = tiles (`PaymentField`); remove `PaymentPicker` (planet cards from Leadership)
  (decision P1). Leadership: no multiple-of-3 requirement + "Auto".
- Token allocation: `CommandPools` everywhere (Leadership, Warfare, Predictive Intelligence, status),
  always with "Auto" (Z5).
- "Auto": one `AutoButton` component, always beside the field, helper style; primary action in footer
  (Z6). Add missing ones: `multi`, Leadership (target = full multiples of 3), agenda voting.

### U3 — Decision Zone and Queue (clutter)
- One decision zone: if a phase window is open (status, agenda, strategy card), own
  offers enter it as the next step or wait as "+N", never as a second window (Z1).
- "Decisions / Timing windows" panel hides while a decision window is active, and does not overlap
  the agenda overlay (Z2).
- Reaction toast and map tooltips do not overlap the decision window (z-index layer + position) (Z2, Z10).
- Hand dock collapses when a decision window covers it.
- **Status (2026-11-23): done** — `data-decision-zone` / `data-phase-window` markers
  (`hooks/useDecisionZone.ts`); offers alongside a phase window wait as a "+N" pill (not as a step
  inside the phase window); reaction banner moves to the top when a decision window is open.

### U4 — Removing Duplicate Info
- Respondent: only in window frame; side panel shows queue without "Responding" (Z8).
- Agenda: one place for "votes available" (propose: Senate seat list); remove
  "N votes available" from outcomes; agenda counter only in header (Z3). Tiebreak = click on podium.
- Tiles: remove native `title` (tooltip via ⓘ and Tooltip). Offer: field label does not repeat
  title (Z12).
- Component action: only non-hand components (action cards = drag), description + ⓘ (Z9).
- **Status (2026-11-23): done** — see `PROGRESS.md` (U4).

### U5 — Readability and Dead Ends
- Secondary: follow cost as a separate clear line; "Follow" disabled with reason when nothing can
  be gained (Leadership < 3 influence) (Z7).
- `Required` as a legible badge; ability text with separators (backend: joining texts) (Z12).
- Status bar and coach aligned with phase and test mode; faction names instead of "Player p1" (Z13).
- Leadership: `base_gain` from engine instead of constant 3.
- **Status (2026-11-23): done** — see `PROGRESS.md` (U5); also rule #6 (clear "skip / don't do").

### U6 — Planet Selection Only on Map (user rules)
- Agenda "Elect Planet": outcome selection by clicking on map (highlighted planets) + outcome list
  only as vote preview.
- DecisionFields: instead of `Select`/`MultiSelect` → grid of large chips, drag/click instead of lists (decision P2).
- **Status (2026-11-23): done** — see `PROGRESS.md` (U6). Drag&drop in grid not added (click suffices).

## User Decisions (answers to questions)
- **P1 — Payment: unify, make it look good.** User dislikes the Leadership look (planet rows/cards)
  "at all" — remove it. One payment widget across the whole game = compact tiles with value
  (pattern: offers/`PaymentField`), consistent with the rest. In Leadership:
  - REMOVE the "can only pay in multiples of 3 influence" restriction (any amount; token count = `base_gain`
    from engine per card rule, not forced multiples of 3 in UI),
  - ADD "Auto" (sensible default amount/allocation; document `⚠️ ASSUMPTION` in `rules/R<NN>.md`).
- **P2 — Many options (>18) non-planet/non-tech: most convenient, prefer dragging and clicking, not lists.**
  Grid of large clickable chips (no `Select`/`MultiSelect`), drag&drop where sensible; search/
  grouping only as helpers. General rule for all windows: drag/click > list.
- **Decision queue = "queue for your decision".** Pending player decisions sit in a queue shown
  as a "+N" counter on one open window (rule #1); not as extra windows or a separate list
  (Z1, Z8). Handling order = arrival order, player decides one by one.
- **P3** Block order unchanged: U1 → U2 → U3 → U4 → U5 → U6 (U2 includes the payment and Leadership
  changes above; U5 "`base_gain` from engine" touches the same spot).
