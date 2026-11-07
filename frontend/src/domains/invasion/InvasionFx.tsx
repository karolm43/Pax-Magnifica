import { useRef, type CSSProperties } from "react";
import type { InvasionLogEntry } from "./useInvasion";
import styles from "./InvasionOverlay.module.css";

/**
 * Efekty okna inwazji (czysto wizualne, bez wpływu na stan):
 * - ``ShieldDome``: kopuła Planetary Shield nad planetą (stoi / zapada się pod war sunem);
 * - ``StrikeLayer``: salwa orbitalna spadająca na planetę (bombardowanie) albo kontrostrzał
 *   z ziemi w górę (Space Cannon Defense) — jeden pocisk na kość, trafienie = rozbłysk.
 */

/** Kopuła tarczy: pulsująca siatka; ``collapsed`` = tarcza istnieje, ale war sun ją łamie. */
export function ShieldDome({
  up,
  collapsed,
}: {
  up: boolean;
  collapsed: boolean;
}) {
  if (!up && !collapsed) return null;
  return (
    <div
      className={styles.dome}
      data-state={up ? "up" : "down"}
      aria-hidden="true"
    />
  );
}

/** Pseudolosowa, ale stała pozycja pocisku (0..1) z jego numeru. */
function spread(n: number, salt: number): number {
  const h = Math.sin(n * 12.9898 + salt * 78.233) * 43758.5453;
  return h - Math.floor(h);
}

/**
 * Pokazuje salwę tylko dla wpisu dziennika, który POJAWIŁ SIĘ po zamontowaniu karty
 * (otwarcie okna nie odtwarza starych strzałów).
 */
export function StrikeLayer({
  entry,
  entryId,
  from,
}: {
  entry: InvasionLogEntry | undefined;
  /** Numer wpisu w dzienniku (rośnie z każdym rozstrzygnięciem). */
  entryId: number;
  from: "orbit" | "ground";
}) {
  const initial = useRef(entryId);
  if (!entry || entry.passed || entryId === initial.current) return null;
  const bolts = entry.rolls.flatMap((r, ri) =>
    r.dice.map((d, di) => ({ hit: d >= r.hitsOn, id: `${ri}-${di}` })),
  );
  return (
    <div
      className={styles.strikes}
      data-from={from}
      data-hits={bolts.some((b) => b.hit) || undefined}
      key={entryId}
      aria-hidden="true"
    >
      {bolts.map((b, n) => (
        <span
          key={b.id}
          className={styles.strike}
          data-hit={b.hit || undefined}
          style={
            {
              "--x": `${10 + spread(n, 1) * 80}%`,
              "--delay": `${n * 170 + spread(n, 2) * 120}ms`,
              "--land": `${52 + spread(n, 3) * 26}%`,
            } as CSSProperties
          }
        >
          <i className={styles.strikeTrail} />
          <i className={styles.strikeBlast} />
        </span>
      ))}
    </div>
  );
}
