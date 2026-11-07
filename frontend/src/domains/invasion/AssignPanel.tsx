import { useState } from "react";
import {
  absorbed,
  autoMarks,
  MARK_WEIGHT,
  nextMark,
  planFromMarks,
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
  colorAlias,
  faction,
  busy,
  onConfirm,
}: {
  title: string;
  ships: ShipEntity[];
  required: number;
  hits: number;
  colorAlias: string;
  faction: string;
  busy: boolean;
  onConfirm: (plan: BattleAssignPlan) => void;
}) {
  const [marks, setMarks] = useState<Record<string, Mark>>({});
  const covered = absorbed(marks);

  const toggle = (ship: ShipEntity) => {
    const current = marks[ship.id];
    let candidate = nextMark(ship, current);
    const others = covered - (current ? MARK_WEIGHT[current] : 0);
    // Nie pozwól pokryć więcej trafień, niż trzeba.
    while (candidate && others + MARK_WEIGHT[candidate] > required) {
      candidate = nextMark(ship, candidate);
    }
    const next = { ...marks };
    if (candidate) next[ship.id] = candidate;
    else delete next[ship.id];
    setMarks(next);
  };

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
          onClick={() => setMarks(autoMarks(ships, required))}
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
          disabled={busy || covered !== required}
          onClick={() => onConfirm(planFromMarks(ships, marks))}
        >
          Confirm {covered}/{required}
        </button>
      </div>
    </div>
  );
}
