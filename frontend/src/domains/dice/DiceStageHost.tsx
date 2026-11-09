import type { CSSProperties } from "react";
import { createPortal } from "react-dom";
import { DicePool } from "@/domains/battle/DicePool";
import { DiceTray } from "@/domains/battle/DiceTray";
import { READ_MS } from "@/domains/battle/diceRoll";
import styles from "@/domains/battle/BattleOverlay.module.css";
import { useDiceStage } from "./diceStage";

/**
 * Pełnoekranowa scena kości (portal nad całą aplikacją, bez przechwytywania kliknięć):
 * przyciemnia tło, pokazuje pulę kości (gdy trzymasz przycisk rzutu) i sam rzut. Montowana raz
 * na stronie gry; steruje nią ``useDiceStage`` (patrz ``diceStage.ts``).
 */
export function DiceStageHost() {
  const roll = useDiceStage((s) => s.roll);
  const pool = useDiceStage((s) => s.pool);
  // Pula widoczna przy przytrzymaniu i do chwili, gdy nadejdzie rzut wykonany z niej.
  const showPool = pool.phase !== "off";
  if (!roll && !showPool) return null;

  const rgb = showPool
    ? { l: pool.leftRgb, r: pool.rightRgb }
    : { l: roll!.leftRgb, r: roll!.rightRgb };
  const life = roll ? roll.diceMs + READ_MS + 1500 + 600 : 0;
  return createPortal(
    <div
      className={styles.stageHost}
      style={{ "--left-rgb": rgb.l, "--right-rgb": rgb.r } as CSSProperties}
      aria-hidden="true"
    >
      {showPool ? (
        <>
          <div className={styles.stageDim} data-steady />
          <DicePool
            left={pool.left}
            right={pool.right}
            solo={pool.solo}
          />
        </>
      ) : (
        roll && (
          <>
            <div
              key={`dim-${roll.id}`}
              className={styles.stageDim}
              style={{ "--life": `${life}ms` } as CSSProperties}
            />
            <DiceTray
              key={roll.id}
              volley={roll}
              solo={roll.solo}
              fromPool={roll.fromPool}
              pool={roll.pool}
            />
          </>
        )
      )}
    </div>,
    document.body,
  );
}
