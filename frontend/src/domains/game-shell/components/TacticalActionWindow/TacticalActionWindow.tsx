import { useState } from "react";
import { useParams } from "react-router-dom";
import { IconCrosshair, IconGripVertical, IconMaximize } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { getTileById } from "@/entities/lookup/systems";
import { useHudMetric } from "@/hooks/useHudMetric";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { useResizablePanel } from "@/hooks/useResizablePanel";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { tutorialTarget } from "@/domains/tutorial/targets";
import { TacticalActionPanel } from "./TacticalActionPanel";
import { TACTICAL_STEPS, stepIndex } from "./tacticalSteps";
import styles from "./TacticalActionWindow.module.css";

/** Saved position / size of the window (localStorage) - kept between sessions. */
const POS_KEY = "ti4_tactical_window_pos";
const SIZE_KEY = "ti4_tactical_window_size";

/**
 * Tactical Action Window on the map view: ONE guided wizard for the whole tactical action
 * (RULES.md 19) - move ships (flight plan), Space Cannon, space combat, invasion, production.
 *
 * Draggable (header grip, double-click resets) and resizable; "Map" minimizes it to a slim bar
 * so the board can be inspected - the panel stays mounted (staged flight plan, map targets).
 * Shown only during a tactical action and, in a network game, only to the active player (the
 * others see combat and reaction decisions in their own windows).
 */
export function TacticalActionWindow() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const gameData = useGameData();
  const drag = useDraggablePanel(POS_KEY);
  const resize = useResizablePanel(SIZE_KEY, {
    minW: 340,
    minH: 260,
    maxW: 680,
    maxH: 960,
  });
  const [minimized, setMinimized] = useState(false);
  // HUD slot "bottom left": the hand narrows from the left while the window sits there.
  useHudMetric(drag.el, "--hud-left-w", (rect) => rect.right, !drag.isMoved);

  const { data: me } = useNetworkMe();
  const desk = useDeskPlayer();

  const activeSystem = gameState?.activeSystem ?? null;
  if (!activeSystem) return null;
  const turnColor = gameState?.activeTurnPlayer ?? gameState?.activePlayer ?? null;
  if (me?.network && desk && turnColor && desk.color !== turnColor) return null;

  const sysId = gameData?.tiles?.[activeSystem]?.systemId;
  const name = sysId ? getTileById(sysId)?.name : undefined;
  const label = name ? `${activeSystem} · ${name}` : activeSystem;
  const step = gameState?.tacticalStep ?? null;
  const index = stepIndex(step);

  return (
    <aside
      className={styles.window}
      ref={drag.ref}
      style={{ ...drag.style, ...(minimized ? {} : resize.style) }}
      aria-label="Tactical action"
      {...tutorialTarget("tactical-action")}
      data-draggable-panel
      data-minimized={minimized || undefined}
      data-dragging={drag.isDragging || undefined}
      data-slotted={!drag.isMoved || undefined}
      data-resizing={resize.isResizing || undefined}
    >
      <header
        className={styles.windowHead}
        onPointerDown={drag.onHandlePointerDown}
        onDoubleClick={drag.reset}
        title="Drag to move · double-click resets position"
      >
        <span className={styles.grip} aria-hidden="true">
          <IconGripVertical size={13} />
        </span>
        <IconCrosshair size={15} aria-hidden="true" />
        <span className={styles.windowTitle}>Tactical action</span>
        {minimized && (
          <>
            <span className={styles.miniStep}>
              {index >= 0 ? `${index + 1}/5 · ${TACTICAL_STEPS[index].label}` : label}
            </span>
            <button
              type="button"
              className={styles.expand}
              data-no-drag
              onClick={() => setMinimized(false)}
            >
              <IconMaximize size={13} aria-hidden="true" /> Open
            </button>
          </>
        )}
      </header>
      <div className={styles.windowBody} hidden={minimized}>
        <TacticalActionPanel
          activeSystem={activeSystem}
          tacticalStep={step}
          systemLabel={label}
          activePlayerColor={turnColor}
          onMinimize={() => setMinimized(true)}
        />
      </div>
      {!minimized && (
        <span
          className={styles.resizeHandle}
          data-no-drag
          onPointerDown={resize.onHandlePointerDown}
          onDoubleClick={resize.reset}
          title="Drag to resize · double-click resets size"
          aria-hidden="true"
        />
      )}
    </aside>
  );
}

export default TacticalActionWindow;
