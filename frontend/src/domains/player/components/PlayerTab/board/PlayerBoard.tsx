import type { PlayerData } from "@/entities/data/types";
import { CommandWing } from "./CommandWing";
import { FactionSheet } from "./FactionSheet";
import { LeaderWing } from "./LeaderWing";
import styles from "./PlayerBoard.module.css";

/** The physical player zone: leader organizer | faction sheet | command sheet. */
export function PlayerBoard({
  player,
  largestFleet,
}: {
  player: PlayerData;
  largestFleet: number | null;
}) {
  return (
    <div className={styles.board}>
      <div className={styles.wings}>
        <div className={styles.leaders}>
          <LeaderWing player={player} />
        </div>
        <div className={styles.sheet}>
          <FactionSheet key={player.color} player={player} />
        </div>
        <div className={styles.command}>
          <CommandWing player={player} largestFleet={largestFleet} />
        </div>
      </div>
    </div>
  );
}
