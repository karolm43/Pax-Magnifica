# Faction Picker Scene (Setup) — Design, Files, Content

This document describes the **current state** of the faction picker UI and the "Players" step in the new game
wizard, as well as how to add content (portraits, quotes, lore) and what pitfalls to avoid. Iteration
history is in `PROGRESS.md` / `PROGRESS_ARCHIWUM.md`; code is authoritative over this description.

---

## 1. Wizard Flow

`StartScreen` (menu → "Play") → `SetupWizard` with two steps (`setupSteps.ts`):

1. **`name-color` — "Players"** (`steps/Step_NameColor.tsx`): per-player name, color, and
   **Human/Bot control + bot difficulty** (difficulty set from `GET /engine/config`,
   not from frontend). Separate "Human/bot" step was removed. Control validation lives in
   `validateStep("name-color")` (`useSetupStore.ts`). Player count and map string are
   in the wizard header only on the first step.
2. **`faction` — fullscreen scene** (`steps/Step_Faction.tsx`): faction selection per player
   along with starting technologies (embedded in `FactionSummary`). Step is in
   `STAGE_STEP_IDS` (`SetupWizard.tsx`), so it renders **without the wizard frame** and draws
   its own top bar (Back · player switcher · Start game). `StartScreen` in stage mode
   removes container padding/scroll (`.setupScreenStage`).

Obsidian is not selectable — entered only via the "View Obsidian" button in Firmament's
panel (`DERIVED_FACTION` in `FactionSummary.tsx`). The scene then shows its portrait/lore.

---

## 2. Scene Layout (left to right)

```
┌ top bar: ← Back │ Player1 Player2 … │ Start game → ──────────────────────────────┐
│ ┌ header (panel: icon + name + quote + author) ┐                                 │
│        [ CHARACTER ]──lore (2 columns, overlaps faded right edge of character)   │ detail │ faction │
│                      ✦ Pick for Player N ✦  (bottom-center button)               │(narrow)│  list   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

- **Character zone** (`.characterZone`, `Step_Faction.module.css`): portrait anchored to left
  and bottom edges of the screen; right edge fades with a mask. CSS vars: `--portrait-w`
  (strip width), `--quote-h` (header height; smaller without quote), `--lore-top`,
  `--pick-h` (height of bottom row with button), `--figure-cx` (center of **measured**
  silhouette, set from JS).
- **Detail panel** (`FactionSummary`): narrow (`clamp(280px, 18.5vw, 350px)`), blurred
  glass; abilities, technologies, units, leaders, game start. Appears **fast**.
- **Faction list** (right): vertical, with search; **click only** changes preview
  (no hover popovers — see gotcha "card sticks on hover"). "Random" tile picks immediately.
- **"Pick for Player N" button** (`.pickBar`): separate, centered at bottom, gold;
  once picked "✓ Picked for Player N". Warning when another player already has the faction.
- Below 1100 px the character zone is hidden and columns stack vertically.

---

## 3. Files

| File | Responsibility |
|---|---|
| `domains/setup/steps/Step_Faction.tsx` + `.module.css` | Scene layout, preview/player state, list, pick button |
| `domains/setup/FactionBackdrop.tsx` + `.module.css` | Scene layers: `FactionPortraitLayer`, `FactionHeader`, `FactionLore`, `splitLoreColumns`, color accent |
| `domains/setup/GlyphText.tsx` + `.module.css` | `useDecode` hook + `DecodedText` — script ↔ readable text (decryption effect) |
| `domains/setup/FactionSummary.tsx` + `.module.css` | Faction detail panel (reuses player panel components), derived faction preview |
| `domains/setup/factionLore.ts` | **Content**: quotes, authors, lore, portrait paths, `glyphLore`, `glitchPhrases` |
| `domains/setup/useSetupStore.ts`, `setupSteps.ts` | Wizard state and steps, validation |
| `styles/fonts.css` | `@font-face`: Ambroise Firmin, Handel Gothic, Lazaxian |

`FactionBackdrop.tsx` is long (≈560 lines) — intentionally kept in one file
(user decision); splitting lore into a separate file is a future option.

---

## 4. Character Portrait

- File: `frontend/public/faction_portraits/<id>.{png,jpg,jpeg,webp}` (or `portrait`
  in `factionLore.ts`). Fallback chain: portrait → faction hero `/leaders/<heroId>.webp`
  → faction icon (drawn as a dimmed symbol). No CDN.
- **Transparent background** (character PNG). After `onLoad`, `measureAlphaInset` (canvas, alpha > 16)
  measures the transparent margin from left/bottom and the silhouette width. `transform: translate(%)`
  correction nudges the **visible** silhouette to the screen edge, and the silhouette center
  (`--figure-cx`) is used to center the header and position the lore.
- Image box = visible content (`width/height: auto` + `max-*`, no `object-fit`),
  so `%` offsets are accurate.

---

## 5. Scene Header (`FactionHeader`)

Faction-sheet-style header panel: dark plate with chamfered corners (`clip-path`),
border in **faction color** (`--accent`), icon on the left, name on the right (Handel Gothic D
Bold), quote (italic), and author (`— Author`, no quotes). Text centered relative to
itself; whole panel centered over the measured silhouette; box hugs the text
(no `text-wrap: balance`).

- **Color accent**: computed from local icon `/static/factions/<id>.png`
  (`useFactionAccent` — saturation-weighted average → `hsl(hue 72% 58%)`, cached by id).
  Grey icon → amber. No hardcoded colors.
- **Quote**: in `factionLore.ts`, enter `quote` **without quotation marks** (component adds “ ”;
  if you paste with quotes — it strips them from the ends). `quoteAuthor` — author only; leading
  dash is optional (component prepends "— "). Author shows only when a quote is present.

---

## 6. Lore (`FactionLore`)

- **Two explicit columns** (`splitLoreColumns`), both starting at the same height.
  Split by character count; if the midpoint falls inside a long paragraph, it cuts at
  a sentence boundary; a subheading is never left orphaned at the bottom of a column. (Previously CSS `column-count`
  — rejected: uneven columns, torn paragraphs.)
- **Auto-fit font** to box: binary search for the largest size
  (window-dependent cap: `min(21, max(14, min(1.15vw, 2.1vh)))`, min 10.5 px) that
  fits **without scrolling** (height test only — width test failed due to
  `::before` protruding outside `article`). Recalculates on zone resize and font load.
- Lore starts at the right edge of the silhouette and **gently overlaps it**
  (`margin-left` from `--figure-cx`), lore background is light and translucent.
- Blocks in `lore`: `paragraph` / `heading` / `quote`; optional `tone` (`red`/`dark-red`)
  and `size` (`large`/`small`).

---

## 7. Animations (attention order)

Pacing is **intentionally varied**: atmosphere is slow, working info is fast.

| Element | Start | Duration |
|---|---|---|
| Character (opacity + slide + brightness; **blur clears separately in 2.2 s**) | 0.25 s | 5.5 s |
| Header panel → name → quote → author | 0.4 / 0.5 / 1.5 / 2.8 s | 1.6–2.2 s |
| Lore (block by block, 230 ms/block) + its background | from 4.2 s | 2.4 s |
| Detail panel (header + sections) | 0.05–0.6 s | 0.4–0.45 s |
| Pick button | 0.4 s | 0.9 s |

**Where to tune pacing:** `--t-*` variable block at the top of `.stage` in
`steps/Step_Faction.module.css` (with a comment on each). Smaller number = faster. Key vars:
`--t-portrait-fade` (full character emergence), `--t-portrait-unblur` (how long character stays
blurred — separate `portraitUnblur` animation, default 2.2 s), `--t-quote-delay`,
`--t-lore-delay`, `--t-lore-step`, `--t-detail-*`, `--t-pick-*`. Animation curves themselves
(motion, opacity/brightness stages) are in `@keyframes` in `FactionBackdrop.module.css`
(`portraitFade`, `portraitUnblur`, `portraitGrade`, `headIn`, `loreIn`) and `FactionSummary.module.css`
(`sectionIn`). The character consists of three animations on different properties (layer:
opacity/motion + blur; image: brightness), so blur can be shortened independently.

Everything replays on every faction change (`key` on layers).
`prefers-reduced-motion`: no motion/blur, but **a slow, visible fade remains** (a short fade
made the animation "invisible"); detail panel gets a short fade.

---

## 8. Lore Written in In-Game Script — Obsidian (`glyphLore`)

Obsidian has `glyphLore: true` in `factionLore.ts`:

- Text (uppercase, English) rendered in **Lazaxian** (`GlyphText.module.css`).
  **"Translate" / "Show original"** button switches to a readable serif face.
- **Decryption effect** (`useDecode`, ~3.6 s): wave moves block by block, character by
  character inside a block; ahead of the front, characters flicker (some swapped for random letters), at the front
  a red "cursor" glows; box jitters, text gets red-cyan aberration, a scanline band
  sweeps across the box. Deterministic randomness (frame hash).
  Font fitting runs only after the transition finishes (`busy`).
- **Dread (`glyphLore` only)** — timers in `FactionLore`, paused during
  decryption and under reduced-motion: random paragraph glitch (Web Animations API: skew,
  color split, clipped bands), whole-lore dimming, brief **phrase flash** from
  `glitchPhrases` at a random spot, and a "beating heart" (background pulse). Phrases authored by the project
  — editable in `factionLore.ts`.
- Lore transcription is fan-made: `(TH)` ligatures stripped, notes removed, illegible
  fragments omitted (e.g. "WHEN YOU'VE FINISHED PLAYING…", "EVERY TENTH CLOSE?",
  "LIFE BRINGS DEAD", "THE WORLD DRAWS ??P"). Fill in via `factionLore.ts`.

---

## 9. Gotchas (what NOT to do)

- **Web Animations API: `easing` in `animate(keyframes, {easing})` applies to the ENTIRE timeline**,
  not per step. `steps(1, end)` there holds the animation on the first frame until the end → effect
  invisible. Put stepped `easing` **inside each keyframe**.
- **Do not replace `animation` on an element with an entrance animation** (e.g. adding
  a "glitch" class): removing the class restarts the entrance animation and text vanishes again.
  Do transient effects via WAAPI (layers on top of CSS animations without restarting them).
- **`text-wrap: balance`** shortens lines, not the container — the box stays wide. For a box
  hugging the text, keep normal wrapping.
- Do not measure `article` width with a protruding pseudo-element (`::before` with negative `inset`).
- Layout centered relative to the **measured silhouette**, not the portrait strip (character can be narrower
  → shifts right).
- Hover-popover over a scrollable list tends to "stick" — hence click instead of hover.
- Blue = interaction signal (selection, focus), not decoration; decorations in warm TI4 tones.
  No ornamental bars/lines at the top of the screen.

---

## 10. External Files & Licenses

- Fonts (`frontend/public/font/`): **Ambroise Firmin Bold**, **Handel Gothic D Bold**,
  **Lazaxian-Bold.ttf** — commercial/fan typefaces; repo owner decides on committing.
  Missing file does not break UI (falls back to next face in `font-family` stack).
  `@font-face` in `styles/fonts.css`.
- Portraits: `frontend/public/faction_portraits/` (including `obsidian.png`, `firmament.png`
  which may still be uncommitted in a local copy).

---

## 11. QA

No frontend unit tests. After a change: `npm run type-check` (or `npx tsc --noEmit`),
`npm run lint`, `npm run build` in `frontend/`. Visual effects (animations, glitches,
centering) are verified in the browser only.

---

## 12. Game Opening Screen (`GameIntro`)

After "Start game" (game already created via `/game/new`), and before entering `/game`
(first strategy phase banner), `SetupWizard` shows a fullscreen screen in a portal
on `document.body` (ancestors have `transform` — `fixed` would break otherwise).

- **Data**: `introPlayers.ts` → `GET /bot/state` (random factions are picked by the
  backend, so we read the actual state; order = `seating_order`). Error/no players =
  intro skipped, straight into the game.
- **Content**: "Twilight Imperium" title (Ambroise + gradient like menu logo), chronicle crawl
  (`CHRONICLE` in `GameIntro.tsx`), row of faction cards (portrait from `portraitCandidates`,
  accent from `useFactionAccent`, name, player + color, human/bot), "Begin" button.
- **Crawl**: distance and duration computed from measurement (constant speed — `CRAWL_VIEWPORTS_PER_SECOND`),
  CSS vars `--from/--to/--dur`. "Begin" appears after text finishes; Skip/Esc/
  Enter/Space finish at any time.
- **Pacing**: `--t-*` vars at the top of `.overlay` in `GameIntro.module.css`.
- Reduced-motion: text stands still (manually scrollable), cards and title only slow fade.
