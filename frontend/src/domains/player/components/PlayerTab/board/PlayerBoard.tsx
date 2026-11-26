import type { PlayerData } from "@/entities/data/types";
import type { EmpireStats } from "../empireStats";
import { CommandWing } from "./CommandWing";
import { FactionSheet } from "./FactionSheet";
import { LeaderWing } from "./LeaderWing";
import styles from "./PlayerBoard.module.css";

/**
 * The physical player zone: leader organizer | faction sheet | command sheet, all three the
 * height of the faction sheet. `empire` (board-derived stats) feeds the production lines under
 * the unit silhouettes and the fleet-pool check; without it those lines are simply left out.
 */
export function PlayerBoard({ player, empire }: { player: PlayerData; empire?: EmpireStats }) {
  return (
    <div className={styles.board}>
      <div className={styles.wings}>
        <div className={styles.leaders}>
          <LeaderWing player={player} empire={empire} />
        </div>
        <div className={styles.sheet}>
          <FactionSheet key={player.color} player={player} empire={empire} />
        </div>
        <div className={styles.command}>
          <CommandWing player={player} empire={empire} />
        </div>
      </div>
    </div>
  );
}
