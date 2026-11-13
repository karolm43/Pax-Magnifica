import { useState } from "react";
import {
  autoMarks,
  coveredCount,
  isCovered,
  planFromMarks,
  toggleMark,
  type Mark,
  type ShipEntity,
} from "@/domains/battle/battleAssign";
import type { BattleAssignPlan } from "@/api/useBoardEditor";
import { GroundToken } from "./invasionUi";
import styles from "./InvasionOverlay.module.css";

/**
 * Pokrycie trafień na planecie (bombardowanie / Space Cannon Defense): właściciel jednostek
 * klika swoje siły naziemne (tarcza = Sustain Damage, czaszka = zniszczenie), „Auto" podpowiada.
 * Stan znaczników żyje tu — znika razem z panelem po zatwierdzeniu.
 */
export function AssignPanel({
  title,
  ships,
  required,
  hits,
  cancels = 1,
  colorAlias,
  faction,
  busy,
  onConfirm,
}: {
  title: string;
  ships: ShipEntity[];
  required: number;
  hits: number;
  /** Ile trafień anuluje tarcza (Non-Euclidean Shielding: 2). */
  cancels?: number;
  colorAlias: string;
  faction: string;
  busy: boolean;
  onConfirm: (plan: BattleAssignPlan) => void;
}) {
  const [marks, setMarks] = useState<Record<string, Mark>>({});
  const covered = coveredCount(marks, required, cancels);
  // Nie pozwól pokryć więcej trafień, niż trzeba.
  const toggle = (ship: ShipEntity) =>
    setMarks(toggleMark(marks, ship, required, cancels));

  return (
    <div className={styles.assign} role="group" aria-label={title}>
      <p className={styles.assignTitle}>
        {title}: <b>{hits}</b> hit{hits === 1 ? "" : "s"}
        {required < hits && (
          <small> — only {required} can be absorbed, the rest is wasted</small>
        )}
      </p>
      <div className={styles.tokens}>
        {ships.map((ship) => (
          <GroundToken
            key={ship.id}
            ship={ship}
            colorAlias={colorAlias}
            faction={faction}
            mark={marks[ship.id]}
            onClick={() => toggle(ship)}
          />
        ))}
      </div>
      <div className={styles.assignActions}>
        <button
          type="button"
          className={styles.ghostBtn}
          onClick={() => setMarks(autoMarks(ships, required, cancels))}
        >
          Auto
        </button>
        <button
          type="button"
          className={styles.ghostBtn}
          onClick={() => setMarks({})}
          disabled={covered === 0}
        >
          Clear
        </button>
        <button
          type="button"
          className={styles.primaryBtn}
          disabled={busy || !isCovered(marks, required, cancels)}
          onClick={() => onConfirm(planFromMarks(ships, marks))}
        >
          Confirm {covered}/{required}
        </button>
      </div>
    </div>
  );
}
