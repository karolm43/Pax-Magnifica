import type { CSSProperties } from "react";
import fx from "./BattleAmbience.module.css";

/**
 * TŁO W RUCHU pola floty (czysta dekoracja, bez wpływu na klik i stan), rysowane W PANELU
 * strony pod jednostkami (wcześniej leżało pod panelami i nie było go widać):
 * - kosmos: STONOWANE — przygaszona mgławica w barwie strony i nieruchome gwiazdy (decyzja
 *   użytkownika 2026-11-17: bez smug pyłu i błysków; ruch jest w okrętach, nie w tle);
 * - ziemia: błyski artylerii nad horyzontem, podmuchy pyłu przy ziemi, żar i dym.
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

const GROUND_FLASHES = 4;
const EMBERS = 16;
const GUSTS = 5;

export function BattleAmbience({
  kind,
  side,
}: {
  kind: "space" | "ground";
  /** Strona panelu — pył leci ku wrogowi, ziarno rozrzutu różne dla stron. */
  side: "left" | "right";
}) {
  const salt = side === "left" ? 0 : 100;
  const dir = side === "left" ? 1 : -1;
  if (kind === "ground") {
    return (
      <div className={fx.ambience} data-kind="ground" aria-hidden="true">
        {Array.from({ length: GROUND_FLASHES }, (_, i) => (
          <i
            key={`f${i}`}
            className={fx.horizonFlash}
            style={vars({
              "--x": `${10 + rnd(i, salt + 1) * 80}%`,
              "--d": `${(rnd(i, salt + 2) * 8).toFixed(2)}s`,
              "--t": `${(5 + rnd(i, salt + 3) * 5).toFixed(2)}s`,
            })}
          />
        ))}
        {Array.from({ length: GUSTS }, (_, i) => (
          <i
            key={`g${i}`}
            className={fx.gust}
            style={vars({
              "--y": `${62 + rnd(i, salt + 4) * 30}%`,
              "--d": `${(-rnd(i, salt + 5) * 9).toFixed(2)}s`,
              "--t": `${(7 + rnd(i, salt + 6) * 5).toFixed(2)}s`,
              "--dir": dir,
            })}
          />
        ))}
        <i className={fx.fog} />
        {Array.from({ length: EMBERS }, (_, i) => (
          <i
            key={`e${i}`}
            className={fx.ember}
            style={vars({
              "--x": `${rnd(i, salt + 7) * 100}%`,
              "--d": `${(-rnd(i, salt + 8) * 9).toFixed(2)}s`,
              "--t": `${(5 + rnd(i, salt + 9) * 5).toFixed(2)}s`,
              "--sway": `${((rnd(i, salt + 10) - 0.5) * 60).toFixed(0)}px`,
            })}
          />
        ))}
      </div>
    );
  }
  return (
    <div className={fx.ambience} data-kind="space" aria-hidden="true">
      <i className={fx.nebula} />
      <i className={fx.starsFar} />
      <i className={fx.starsNear} />
    </div>
  );
}
