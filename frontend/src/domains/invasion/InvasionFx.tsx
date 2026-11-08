import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import type { InvasionLogEntry } from "./useInvasion";
import styles from "./InvasionOverlay.module.css";

/**
 * Efekty okna inwazji (czysto wizualne, bez wpływu na stan):
 * - ``PlanetStage``: okrągła planeta (powierzchnia z gradientów wg typu), nad nią orbita ze
 *   statkami; kopuła Planetary Shield otacza glob (stoi / zapada się pod war sunem);
 * - ``StrikeLayer``: bombardowanie to powolne, ciężkie ładunki z okrętów na orbicie (ładowanie →
 *   opadanie → wielka kula ognia, fala i słup dymu); Space Cannon Defense to szybkie wyładowania jonowe z ziemi w górę.
 * Każda salwa sprząta po sobie: po zakończeniu warstwa znika z DOM (żadnych pozostałości).
 */

/** Rodzaj powierzchni globu z typu planety (dane: CULTURAL/HAZARDOUS/INDUSTRIAL/FACTION…). */
export function surfaceOf(type: string | undefined): string {
  const t = (type ?? "").toLowerCase();
  if (t.includes("cultur")) return "cultural";
  if (t.includes("hazard")) return "hazardous";
  if (t.includes("industr")) return "industrial";
  if (t.includes("frontier")) return "frontier";
  if (t.includes("faction")) return "faction";
  return "neutral";
}

/** Maksymalny odstęp elementów na orbicie (px). */
export const SHIP_GAP = 74;

/** Przesunięcie (px) n-tego z `count` elementów względem środka globu (zagęszcza tłum). */
export function shipDx(n: number, count: number): number {
  const gap = count > 1 ? Math.min(SHIP_GAP, 250 / (count - 1)) : 0;
  return (n - (count - 1) / 2) * gap;
}

/** Element orbity: statek bombardujący albo mała jednostka desantu (kapsuła). */
export type OrbitItem = {
  node: ReactNode;
  /** Stan kapsuły: drop (zrzut), hold (zawieszona w locie), dead (zestrzelona), land (ląduje). */
  state?: "drop" | "hold" | "dead" | "land";
};

/**
 * Scena planety: orbita ze statkami (``children``), okrągły glob z kopułą tarczy i warstwa
 * salwy. Bez grafik planet - powierzchnia to gradienty CSS dobierane po typie planety.
 */
export function PlanetStage({
  surface,
  shielded,
  collapsed,
  ships,
  children,
  strike,
}: {
  surface: string;
  shielded: boolean;
  collapsed: boolean;
  ships: OrbitItem[];
  children?: ReactNode;
  strike: ReactNode;
}) {
  return (
    <div className={styles.stage}>
      <div className={styles.orbitRow} aria-label="Ships in orbit">
        {ships.map((ship, n) => (
          <span
            key={n}
            className={styles.orbitShip}
            data-state={ship.state}
            style={
              {
                "--dx": `${shipDx(n, ships.length)}px`,
                "--k": n,
              } as CSSProperties
            }
          >
            {ship.node}
          </span>
        ))}
      </div>
      <div className={styles.globe} data-surface={surface}>
        <div className={styles.globeSurface} />
        <div className={styles.globeShade} />
        {(shielded || collapsed) && (
          <div
            className={styles.dome}
            data-state={shielded ? "up" : "down"}
            aria-hidden="true"
          />
        )}
        {children}
      </div>
      {strike}
    </div>
  );
}

/** Pseudolosowa, ale stała wartość (0..1) z numeru pocisku. */
function spread(n: number, salt: number): number {
  const h = Math.sin(n * 12.9898 + salt * 78.233) * 43758.5453;
  return h - Math.floor(h);
}

/**
 * Strzał Space Cannon Defense: smuga leci z powierzchni PROSTO W SPADAJĄCĄ KAPSUŁĘ (kąt i długość
 * liczone od działa do kapsuły); trafienie kończy się błyskiem flaku na kapsule, pudło mija ją.
 */
function FlakShot({
  n,
  targetDx,
  shooterDx,
}: {
  n: number;
  targetDx: number;
  shooterDx: number;
}) {
  const vx = targetDx - shooterDx;
  const vy = IMPACT_Y - POD_Y;
  const len = Math.hypot(vx, vy);
  const angle = (Math.atan2(vx, vy) * 180) / Math.PI;
  return (
    <>
      <i
        className={styles.flak}
        style={
          {
            "--sx": `${shooterDx - targetDx}px`,
            "--sy": `${IMPACT_Y}px`,
            "--ang": `${angle}deg`,
            "--len": `${len}px`,
          } as CSSProperties
        }
      >
        <i />
      </i>
      <i
        className={styles.flakBurst}
        style={
          {
            "--by": `${POD_Y}px`,
            "--bx": `${(spread(n, 11) - 0.5) * 8}px`,
          } as CSSProperties
        }
      />
    </>
  );
}

/** Najdłuższa animacja salwy (ms) - po tym czasie warstwa jest zdejmowana z DOM. */
const BOMBARD_MS = 3600;
const DEFENSE_MS = 2800;
/** Odstęp między kolejnymi strzałami salwy (ms): bombardowanie to gęsty deszcz, SCD rzadsze strzały. */
const STAGGER_ORBIT = 170;
const STAGGER_GROUND = 380;
/** Wysokość (px od góry sceny), na której pociski uderzają w glob / stoją kapsuły w locie. */
const IMPACT_Y = 205;
const POD_Y = 105;
/** Pociski w jednej "serii" ze statku (deszcz). */
const ROUNDS = 3;

/**
 * Pokazuje salwę tylko dla wpisu dziennika, który POJAWIŁ SIĘ po zamontowaniu karty
 * (otwarcie okna nie odtwarza starych strzałów), a po jej końcu zdejmuje się sama.
 */
export function StrikeLayer({
  entry,
  entryId,
  from,
  shipCount,
}: {
  entry: InvasionLogEntry | undefined;
  /** Numer wpisu w dzienniku (rośnie z każdym rozstrzygnięciem). */
  entryId: number;
  from: "orbit" | "ground";
  /** Ile statków stoi na orbicie (źródła lanc); 0 = pociski z losowych punktów. */
  shipCount: number;
}) {
  const initial = useRef(entryId);
  const [finished, setFinished] = useState(-1);
  const fresh = !!entry && !entry.passed && entryId !== initial.current;
  const bolts = fresh
    ? entry.rolls.flatMap((r, ri) => {
        const offset = entry.rolls.slice(0, ri).reduce((n, x) => n + x.count, 0);
        return r.dice.map((d, di) => ({
          hit: d >= r.hitsOn,
          id: `${ri}-${di}`,
          sun: r.baseType === "warsun",
          ship: offset + (di % Math.max(1, r.count)),
        }));
      })
    : [];
  const stagger = from === "orbit" ? STAGGER_ORBIT : STAGGER_GROUND;
  const total =
    (from === "orbit" ? BOMBARD_MS : DEFENSE_MS) + bolts.length * stagger;
  useEffect(() => {
    if (!fresh) return;
    const t = window.setTimeout(() => setFinished(entryId), total);
    return () => window.clearTimeout(t);
  }, [fresh, entryId, total]);

  if (!fresh || finished === entryId) return null;
  return (
    <div
      className={styles.strikes}
      data-from={from}
      data-hits={bolts.some((b) => b.hit) || undefined}
      aria-hidden="true"
    >
      {bolts.map((b, n) => {
        const dx =
          shipCount > 0
            ? shipDx(from === "orbit" ? b.ship : n % shipCount, shipCount)
            : (spread(n, 1) - 0.5) * 120;
        return (
          <span
            key={b.id}
            className={styles.strike}
            data-hit={b.hit || undefined}
            data-sun={b.sun || undefined}
            style={
              {
                "--dx": `${dx}px`,
                "--delay": `${n * stagger}ms`,
              } as CSSProperties
            }
          >
            {from === "orbit" ? (
              b.sun ? (
                <>
                  <i className={styles.sunBeam} />
                  <i
                    className={styles.blast}
                    style={{ "--rd": "350ms", "--rx": "0px" } as CSSProperties}
                  />
                </>
              ) : (
                Array.from({ length: ROUNDS }, (_, r) => (
                  <span
                    key={r}
                    className={styles.round}
                    style={
                      {
                        "--rd": `${r * 130 + spread(n, 3 + r) * 90}ms`,
                        "--rx": `${(spread(n, 5 + r) - 0.5) * 46}px`,
                      } as CSSProperties
                    }
                  >
                    <i className={styles.shell} />
                    <i className={styles.blast} />
                  </span>
                ))
              )
            ) : (
              <FlakShot
                n={n}
                targetDx={dx}
                shooterDx={(spread(n, 9) - 0.5) * 150}
              />
            )}
          </span>
        );
      })}
    </div>
  );
}
