# Tactical Action Window — Redesign Plan

## Problems with the Current Implementation

Based on the current codebase (`TacticalActionDock`, `TacticalActionPanel`, `MovementStepPanel`, `MoveRouteBox`, `SpaceCannonStepPanel`, `InvasionStepPanel`, and `ProductionStepPanel`):

1. **Fragmented & Cramped UI for First-Time Players**
   - `TacticalActionDock` (`340px` wide) is squeezed into the bottom-left corner, while `MoveRouteBox` pops up as a separate draggable portal, and Combat / Invasion / Production open separate overlays.
   - First-time players see small helper notes (`prodNote`) with hidden shortcuts (e.g., *"Ctrl+click picks units first"*) instead of a clear guided flow explaining what is happening, what is optional vs. mandatory, and what the primary action is.
2. **One-System-at-a-Time Movement**
   - Clicking a source system opens `MoveRouteBox` for that single `from` system and immediately commits `POST /tactical/move` (`movement.move_fleet`).
   - Players cannot stage ships from multiple systems, compare total incoming Fleet Pool / Capacity, or assign single-ship boosts (`Gravity Drive`, `Ionian Fuel Refinery`, `Imperator`) across the whole move before flying. Fixing a mistake requires repeated `Undo last move` clicks.
3. **Redundant "Start X" Gates**
   - `advance_skipping_empty` (`src/core/tactical.py`) skips empty steps and auto-opens `SPACE_CANNON`, but `SPACE_COMBAT`, `INVASION`, and `PRODUCTION` still stop on a placeholder card requiring the player to click **Start space combat**, **Start invasion**, or **Open production**.
4. **Clunky Space Cannon Step**
   - `SpaceCannonStepPanel` packs a shooter queue, stat boxes, unit table, modifiers, target radio cards, `HoldRollButton` (with `hint={false}`), inline hit assignment, and a log into a narrow scrolling column, with no automatic map visualization of who is firing from where.

---

## Proposed Architecture: Unified Guided Tactical Window

Replace the narrow `TacticalActionDock` + scattered `MoveRouteBox` with a **robust, guided Tactical Action Window** (e.g., `TacticalActionWindow`) that anchors cleanly on the map (collapsible/minimizable so players can always inspect the board) and acts as a **single guided wizard** for the active system.

### 1. Guided Wizard Shell (Beginner-First UX)
- **Header & Stepper Bar**:
  - Shows the **Active System** (name, tile ID, planet summary) and a clear **5-step progress bar**:
    `1. Move Ships` → `2. Space Cannon` → `3. Space Combat` → `4. Invasion` → `5. Production`
  - Each step pill shows status (`Done`, `Active`, `Skipped`, `Upcoming`) and a brief **1-line plain-English subtitle** for the current step (e.g., *"Select ships from glowing systems to fly into [System]. When ready, click Fly All."*).
- **Sticky Primary Action Footer**:
  - One unmistakable primary CTA on the right (context-aware: **Fly All (N ships)**, **Next Step**, **Skip / No Invasion**, **Finish Action**) and secondary **Undo** / **Minimize to Map** controls on the left.
  - Rule locks (Fleet Pool, Capacity, Combat, Active Window) appear as clear inline callouts right above the CTA, explaining *how* to resolve them.

---

### 2. Batched Multi-System Movement ("Choose All, Then Fly All")

Replace immediate per-system `MoveRouteBox` commits with a **Flight Plan Stager** inside the Movement step:

- **Frontend State (`movePlan` in `appStore` or step state)**:
  - Holds a list of staged **Movement Legs**: `{ id, from, via[], ships: Record<string, number>, cargo: CargoPickup[], boost?: 'gd' | 'tempesta' | 'imperator', ionStormToken?: boolean, routeData }[]`.
  - **Adding/Editing a Leg**:
    - Clicking a glowing source system on the map (or picking from a *"Reachable Systems"* list inside the Tactical Window) opens/focuses that leg's ship & cargo picker **directly inside the Tactical Window** (no separate floating `MoveRouteBox` portal).
    - Clicking another glowing system stages a second leg while keeping the first leg in the plan.
    - All staged routes render **simultaneously on the map** with distinct arrows/badges showing ship counts flying from each source.
  - **Live Combined Preview**:
    - Before anything moves, the window computes and displays:
      - **Resulting Fleet in Active System**: existing ships + all staged incoming ships vs. **Fleet Pool** limit (with live red/green indicator).
      - **Total Cargo vs. Capacity**: per-leg and total capacity check.
      - **One-Ship Boost Assignment**: instead of global toggles that are easy to forget, show `Gravity Drive (+1)`, `Ionian Fuel Refinery (+1)`, and `Imperator (+1)` as assignable chips you can toggle onto a specific leg/ship that needs the extra range.
- **Backend Batch Endpoint (`POST /tactical/move-batch`)**:
  - Add `MoveBatchRequest` (`legs: list[MoveShipsRequest]`) in `src/api/routers/tactical.py` and `movement.move_batch(...)` in `src/core/movement.py`.
  - Validates and executes all legs sequentially on a cloned `GameState` inside a **single atomic commit** (`tactical:move-batch:...`), so:
    - If any leg is illegal, the whole batch returns `422` with the exact failing leg/reason without leaving half-moved fleets.
    - One **Undo** reverses the entire flight plan cleanly.
    - `FLEET_POOL` / `CAPACITY` / `fire_ships_moved` / `ion_storm` are evaluated cleanly once the full fleet arrives.
- **Primary CTA & Animation**:
  - **"Fly All Ships (X ships from Y systems)"** → executes `POST /tactical/move-batch` and plays the existing ship-flying animation across all staged legs without jarring step jumps mid-flight.
  - **Whole-Step Undo**: **"Undo Movement"** reverses the entire batch move in one click (or **"Undo Activation"** if nothing has moved yet).
  - **"Next Step"** (or **"No Movement / Next Step"** when nothing is staged) advances once the player is ready.

---

### 3. Fluid Auto-Opening of Big Overlays (Eliminate "Start Invasion" / "Start Combat" Clicks)

Make step transitions seamless so players never have to click a placeholder button just to *open* the step they are already on, while keeping the full-size overlays (`BattleOverlay`, `InvasionOverlay`, `ProductionOverlay`) as the primary workspace for those steps:

- **Backend (`src/core/tactical.py` → `advance_skipping_empty`)**:
  - When entering `SPACE_COMBAT` (and `space_combat_required` is true): automatically initialize `active_combat` so `BattleOverlay` opens immediately.
  - When entering `INVASION` (and `_step_is_empty` is false): automatically call `begin_invasion(...)` so `state.invasion` is populated immediately upon arrival.
  - *(Note: `SPACE_CANNON` already auto-opens via `open_offense`.)*
- **Frontend (`TacticalActionPanel` / `InvasionStepPanel` / `ProductionStepPanel`)**:
  - **`SPACE_COMBAT`**: Fluidly auto-opens `BattleOverlay` (`setBattleHidden(false)`) without an intermediate *"Start space combat"* button.
  - **`INVASION`**: Fluidly auto-opens `InvasionOverlay` (or the simple landing view when uncontested) without a *"Start invasion"* button. If the player chooses not to land any ground forces, provide a clear **"Skip Invasion (Land Nothing)"** action.
  - **`PRODUCTION`**: Fluidly auto-opens `ProductionOverlay` (`setProductionHidden(false)`) on step entry, with a **"Return to Production"** button if the player hides it to inspect the map.

---

### 4. Redesigned Space Cannon Step

Make `SpaceCannonStepPanel` clear, visual, and effortless for first-time players:

1. **Map-First Firing Visualization**:
   - Automatically highlight the active system and draw subtle range/firing lines from every system with Space Cannon units in range (no need to hunt for the `Range` toggle).
2. **Clear Turn Ownership Banner**:
   - Replace the small `TurnCard` header with a bold status banner:
     - **"Your Space Cannon — [Faction]"** (with clear action controls) vs. **"Waiting for [Faction] to fire or pass"** (in multiplayer).
   - Compact horizontal **Firing Order** strip showing who fired, who passed, and who is next.
3. **Polished Hold-to-Roll & Modifiers**:
   - Keep `HoldRollButton` for the tactile dice-shake feel, but upgrade its styling and clarity (clear label **"Fire Space Cannon (N dice · hits on X+)"**, visible hold/click feedback instead of `hint={false}` so first-time players immediately understand it).
   - Show modifiers (`Antimass Deflectors -1`, `Plasma Scoring +1 die`, `Graviton Laser System`) as plain-English chips/toggles right next to the Fire button.
4. **Streamlined Target & Hit Assignment**:
   - Auto-select the target when only 1 valid target exists (and show why).
   - When hits occur, present a clean **Hit Assignment** card with visual ship icons, `Sustain Damage` / `Destroy` toggles, and a **"Auto-assign cheapest"** helper button for faster play.
   - Collapse the `SpaceCannonLog` into a tidy, expandable footer section so it doesn't crowd the active controls.

---

## Suggested Implementation Phases

| Phase | Scope | Key Files |
| :--- | :--- | :--- |
| **Phase 1: Backend Batch Move & Auto-Start** | Add `POST /tactical/move-batch` and auto-init `SPACE_COMBAT` / `INVASION` in `advance_skipping_empty`. | `src/core/movement.py`, `src/core/tactical.py`, `src/api/routers/tactical.py`, `src/api/schemas/tactical.py` |
| **Phase 2: Unified Tactical Window Shell** | Build `TacticalActionWindow` with wider guided layout, plain-English step prompts, sticky footer, and minimize-to-map mode. | `TacticalActionDock.tsx`, `GameStatePanel.tsx`, `TacticalActionDock.module.css` |
| **Phase 3: Multi-System Flight Plan** | Replace single-system `MoveRouteBox` commits with staged multi-leg `movePlan`, combined Fleet Pool/Capacity preview, and multi-route map overlay. | `MovementStepPanel.tsx`, `MoveRouteBox.tsx`, `appStore.ts`, map route layer |
| **Phase 4: Space Cannon & Invasion Polish** | Auto-open Invasion/Production, add Space Cannon map lines, polished `HoldRollButton` CTA, and auto-assign hits helper. | `SpaceCannonStepPanel.tsx`, `InvasionStepPanel.tsx`, `SpaceCannonParts.tsx` |
