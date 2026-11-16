import type { CSSProperties } from "react";
import fx from "./BattleAmbience.module.css";

/**
 * TŁO W RUCHU pola bitwy (czysta dekoracja, bez wpływu na klik i stan):
 * - kosmos: druga, bliższa warstwa gwiazd (paralaksa), dryfująca mgławica i rzadkie błyski
 *   odległej bitwy na krawędziach kadru;
 * - ziemia: błyski artylerii za horyzontem, unoszące się iskry/żar i nisko ścielący się dym.
 * Pozycje są stałe (deterministyczne), więc tło nie „skacze" przy przerysowaniu.
 */

/** Stała pseudolosowa wartość 0..1 z numeru elementu. */
function rnd(n: number, salt: number): number {
  const h = Math.sin(n * 91.345 + salt * 47.853) * 24634.6345;
  return h - Math.floor(h);
}

function vars(v: Record<string, string | number>): CSSProperties {
  return v as CSSProperties;
}

const FLASHES = 5;
const EMBERS = 18;

export function BattleAmbience({ kind }: { kind: "space" | "ground" }) {
  if (kind === "ground") {
    return (
      <div className={fx.ambience} data-kind="ground" aria-hidden="true">
        {Array.from({ length: FLASHES }, (_, i) => (
          <i
            key={`f${i}`}
            className={fx.horizonFlash}
            style={vars({
              "--x": `${8 + rnd(i, 1) * 84}%`,
              "--d": `${(rnd(i, 2) * 9).toFixed(2)}s`,
              "--t": `${(7 + rnd(i, 3) * 6).toFixed(2)}s`,
            })}
          />
        ))}
        <i className={fx.fog} />
        <i className={fx.fog} data-back />
        {Array.from({ length: EMBERS }, (_, i) => (
          <i
            key={`e${i}`}
            className={fx.ember}
            style={vars({
              "--x": `${rnd(i, 4) * 100}%`,
              "--d": `${(-rnd(i, 5) * 12).toFixed(2)}s`,
              "--t": `${(8 + rnd(i, 6) * 7).toFixed(2)}s`,
              "--sway": `${((rnd(i, 7) - 0.5) * 80).toFixed(0)}px`,
            })}
          />
        ))}
      </div>
    );
  }
  return (
    <div className={fx.ambience} data-kind="space" aria-hidden="true">
      <i className={fx.nebula} />
      <i className={fx.starsNear} />
      {Array.from({ length: FLASHES }, (_, i) => (
        <i
          key={`f${i}`}
          className={fx.farFlash}
          style={vars({
            "--x": `${rnd(i, 8) < 0.5 ? 3 + rnd(i, 9) * 14 : 83 + rnd(i, 9) * 14}%`,
            "--y": `${10 + rnd(i, 10) * 75}%`,
            "--d": `${(rnd(i, 11) * 14).toFixed(2)}s`,
            "--t": `${(11 + rnd(i, 12) * 8).toFixed(2)}s`,
          })}
        />
      ))}
    </div>
  );
}
