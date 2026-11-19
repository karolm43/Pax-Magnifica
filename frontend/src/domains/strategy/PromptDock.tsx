import { useState, type ReactNode } from "react";
import { DraggablePill } from "@/shared/ui/DraggablePill";
import { IconArrowsMaximize, IconMinus } from "@tabler/icons-react";
import modalStyles from "@/shared/ui/AppModal.module.css";
import styles from "./StrategyPrompt.module.css";

/**
 * Nieblokujący dok kroku karty strategii - u GÓRY ekranu, mapa pod nim zostaje klikalna
 * (wybór systemu / planety, akcja taktyczna). Można go zminimalizować do pastylki, jak
 * okna ``AppModal minimizable``.
 */
export function PromptDock({ label, children }: { label: string; children: ReactNode }) {
  const [minimized, setMinimized] = useState(false);
  if (minimized) {
    return (
      <DraggablePill
        storageKey="minimizedPill.pos.v1"
        className={modalStyles.pill}
        title="Restore the window"
        onRestore={() => setMinimized(false)}
      >
        <IconArrowsMaximize size={15} aria-hidden="true" />
        <span>{label}</span>
      </DraggablePill>
    );
  }
  return (
    <div className={styles.topDock} role="dialog" aria-label={label}>
      <div className={styles.dockBar}>
        <button
          type="button"
          className={modalStyles.minimize}
          onClick={() => setMinimized(true)}
          aria-label="Minimize to see the board"
          title="Minimize to see the board"
        >
          <IconMinus size={16} aria-hidden="true" />
        </button>
      </div>
      {children}
    </div>
  );
}
