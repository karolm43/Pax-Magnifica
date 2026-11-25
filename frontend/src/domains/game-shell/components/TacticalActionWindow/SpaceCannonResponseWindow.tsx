import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  IconBolt,
  IconGripVertical,
  IconMaximize,
  IconMinimize,
  IconTarget,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useSpaceCannon } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { getTileById } from "@/entities/lookup/systems";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { useResizablePanel } from "@/hooks/useResizablePanel";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { SpaceCannonStepPanel } from "../SpaceCannonStepPanel";
import { spaceCannonRole } from "./spaceCannonRole";
import styles from "./TacticalActionWindow.module.css";

const POS_KEY = "ti4_space_cannon_response_pos";
const SIZE_KEY = "ti4_space_cannon_response_size";

/**
 * Space Cannon Offense window for a NON-active seat in a network game (RULES.md 38).
 *
 * The Tactical Action Window belongs to the active player only, but Space Cannon Offense is a
 * window for every player: anyone with Space Cannon in range fires in turn (clockwise from the
 * active player), and the player hit by the active player's shot covers the hits. This window
 * opens for such a seat with the same shell and the same Space Cannon panel (queue, turn card,
 * dice, hit assignment, log) - the active player sees it inside their tactical window.
 */
export function SpaceCannonResponseWindow() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const gameData = useGameData();
  const { data: me } = useNetworkMe();
  const desk = useDeskPlayer();
  const [minimized, setMinimized] = useState(false);
  const drag = useDraggablePanel(POS_KEY);
  const resize = useResizablePanel(SIZE_KEY, {
    minW: 340,
    minH: 260,
    maxW: 680,
    maxH: 960,
  });

  const activeSystem = gameState?.activeSystem ?? null;
  const turnColor = gameState?.activeTurnPlayer ?? gameState?.activePlayer ?? null;
  const otherSeat = !!me?.network && !!desk && !!turnColor && desk.color !== turnColor;
  const cannonStep = otherSeat && !!activeSystem && gameState?.tacticalStep === "SPACE_CANNON";
  const { data: panel } = useSpaceCannon(cannonStep);

  const role = cannonStep && panel && desk ? spaceCannonRole(panel, desk.faction) : null;
  if (!activeSystem || !role) return null;

  const sysId = gameData?.tiles?.[activeSystem]?.systemId;
  const systemName = (sysId ? getTileById(sysId)?.name : undefined) ?? activeSystem;
  const prompt =
    role === "assign"
      ? "You were hit by Space Cannon fire - choose which of your ships cover the hits."
      : role === "fire"
        ? "Your turn: fire your Space Cannon at the active player's ships in the active system, or don't fire."
        : role === "done"
          ? "You have resolved your Space Cannon - the other players are still responding."
          : "Space Cannon Offense: players fire in order, clockwise from the active player. Wait for your turn.";

  return (
    <aside
      className={styles.window}
      ref={drag.ref}
      style={{ ...drag.style, ...(minimized ? {} : resize.style) }}
      aria-label="Space Cannon response"
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
        <IconBolt size={15} aria-hidden="true" />
        <span className={styles.windowTitle}>Space Cannon response</span>
        {minimized ? (
          <>
            <span className={styles.miniStep}>{systemName}</span>
            <button
              type="button"
              className={styles.expand}
              data-no-drag
              onClick={() => setMinimized(false)}
            >
              <IconMaximize size={13} aria-hidden="true" /> Open
            </button>
          </>
        ) : (
          <button
            type="button"
            className={styles.expand}
            style={{ marginLeft: "auto" }}
            data-no-drag
            onClick={() => setMinimized(true)}
            title="Minimize to inspect the map"
          >
            <IconMinimize size={13} aria-hidden="true" /> Map
          </button>
        )}
      </header>
      <div className={styles.windowBody} hidden={minimized}>
        <div className={styles.panel}>
          <header className={styles.head}>
            <div className={styles.system}>
              <IconTarget size={16} aria-hidden="true" />
              <span className={styles.systemName} title={systemName}>
                {systemName}
              </span>
              <small className={styles.tileId}>{activeSystem}</small>
            </div>
          </header>
          <p className={styles.prompt} role="status">
            {prompt}
          </p>
          <div className={styles.body}>
            <SpaceCannonStepPanel />
          </div>
        </div>
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

export default SpaceCannonResponseWindow;
