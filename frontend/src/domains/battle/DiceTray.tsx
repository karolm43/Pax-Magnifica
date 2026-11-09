import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { playBattleSound } from "./battleSound";
import {
  CONTACTS,
  DIE_MS,
  READ_MS,
  planDice,
  type Die,
  type Point,
} from "./diceRoll";
import type { Volley } from "./useBattleFx";
import styles from "./BattleOverlay.module.css";

/**
 * Fizyczny rzut kośćmi na stół pola bitwy (czysta prezentacja — wartości z silnika).
 *
 * Kostki d10 wpadają z krawędzi ekranu (atakujący z lewej, obrońca z prawej), obracają się w
 * 3D, odbijają trzykrotnie od stołu (coraz niżej i krócej, z cieniem rosnącym przy zderzeniu),
 * stukają i układają się płasko. W locie ścianka „migocze" losowymi liczbami; wynik pojawia
 * się, gdy kostka traci pęd. Po odczytaniu rzutu stół znika, a salwa rusza dopiero po
 * wylądowaniu ostatniej kostki (``Volley.diceMs``).
 */

/** Wysokość kostki nad stołem w kolejnych klatkach (px) — odbicia słabną. */
const LIFT_AT = [0, 0.34, 0.47, 0.6, 0.7, 0.8, 0.9, 1] as const;
const LIFT_Z = [100, 0, 38, 0, 14, 0, 4, 0] as const;
/** Chwile klatek pozycji i obrotu (ułamek lotu) oraz ułamek obrotu, który jeszcze został. */
const MOVE_AT = [0, CONTACTS[0], CONTACTS[1], CONTACTS[2], 1] as const;
const SPIN_LEFT = [1, 0.45, 0.15, 0.04, 0] as const;
/** Po tej części lotu ścianka przestaje migotać i pokazuje wynik. */
const REVEAL_AT = 0.74;

const FALL = "cubic-bezier(0.55, 0, 0.9, 0.55)";
const RISE = "cubic-bezier(0.1, 0.45, 0.45, 1)";

const reducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function DieBody({ die }: { die: Die }) {
  const ref = useRef<HTMLDivElement>(null);
  const at = (p: Point) => `translate3d(${p.x}px, ${p.y}px, 0)`;

  useLayoutEffect(() => {
    const wrap = ref.current;
    if (!wrap) return;
    const part = (name: string) =>
      wrap.querySelector<HTMLElement>(`[data-part="${name}"]`);
    const lift = part("lift");
    const shadow = part("shadow");
    const cube = part("cube");
    const face = part("face");
    if (!lift || !shadow || !cube || !face) return;
    if (reducedMotion()) {
      wrap.style.transform = at(die.rest);
      wrap.dataset.settled = "1";
      return;
    }
    const timing = {
      duration: DIE_MS,
      delay: die.delayMs,
      fill: "both" as const,
    };
    const points = [die.start, ...die.hops, die.rest];
    const run = [
      wrap.animate(
        MOVE_AT.map((offset, i) => ({
          offset,
          transform: at(points[i]),
          easing: "linear",
        })),
        timing,
      ),
      lift.animate(
        LIFT_AT.map((offset, i) => {
          const z = LIFT_Z[i];
          const next = LIFT_Z[Math.min(i + 1, LIFT_Z.length - 1)];
          return {
            offset,
            transform: `translateY(${-z}px) scale(${1 + z / 260})`,
            easing: next < z ? FALL : RISE,
          };
        }),
        timing,
      ),
      shadow.animate(
        LIFT_AT.map((offset, i) => {
          const z = LIFT_Z[i];
          const next = LIFT_Z[Math.min(i + 1, LIFT_Z.length - 1)];
          return {
            offset,
            transform: `translate(${z * 0.25}px, ${z * 0.45}px) scale(${1 - z / 400})`,
            opacity: Math.max(0.12, 0.6 - z / 260),
            easing: next < z ? FALL : RISE,
          };
        }),
        timing,
      ),
      cube.animate(
        MOVE_AT.map((offset, i) => {
          const f = SPIN_LEFT[i];
          return {
            offset,
            transform: `rotateX(${die.rx * f}deg) rotateY(${die.ry * f}deg) rotateZ(${die.rz * f + die.restRz * (1 - f)}deg)`,
            easing: "linear",
          };
        }),
        timing,
      ),
    ];
    // Ścianka w locie: losowe liczby, po utracie pędu — prawdziwy wynik z silnika.
    const label = face.querySelector("b");
    const t0 = performance.now() + die.delayMs;
    const flicker = window.setInterval(() => {
      if (!label) return;
      const elapsed = performance.now() - t0;
      if (elapsed >= DIE_MS * REVEAL_AT) {
        label.textContent = String(die.value);
        window.clearInterval(flicker);
      } else if (elapsed >= 0) {
        label.textContent = String(1 + Math.floor(Math.random() * 10));
      }
    }, 70);
    void run[0].finished
      .then(() => {
        wrap.dataset.settled = "1";
      })
      .catch(() => undefined);
    return () => {
      window.clearInterval(flicker);
      run.forEach((a) => a.cancel());
    };
    // Plan kostki jest stały dla danej salwy — animacja startuje raz, przy montowaniu.
  }, []);

  return (
    <div
      ref={ref}
      className={styles.dieWrap}
      data-side={die.side}
      data-hit={die.hit || undefined}
      style={
        {
          "--ds": `${die.size}px`,
          transform: at(die.start),
        } as CSSProperties
      }
    >
      <i className={styles.dieShadow} data-part="shadow" />
      <div className={styles.dieLift} data-part="lift">
        <div className={styles.dieCube} data-part="cube">
          <span className={styles.dieFace} data-part="face">
            <b>{die.value}</b>
          </span>
        </div>
      </div>
    </div>
  );
}

/** Stół z kośćmi dla jednej salwy (znika sam po odczytaniu rzutu). */
export function DiceTray({ volley }: { volley: Volley }) {
  const trayRef = useRef<HTMLDivElement>(null);
  const [dice, setDice] = useState<Die[]>([]);
  const [gone, setGone] = useState(false);
  const holdMs = volley.diceMs + READ_MS + 1100;

  useLayoutEffect(() => {
    const tray = trayRef.current;
    if (!tray) return;
    setDice(
      planDice({
        left: volley.rolls.left,
        right: volley.rolls.right,
        width: tray.clientWidth,
        height: tray.clientHeight,
        seed: volley.id,
      }),
    );
  }, [volley]);

  // Dźwięk: grzechot przy rzucie każdej strony i stuknięcia przy kolejnych odbiciach.
  useEffect(() => {
    const tray = trayRef.current;
    if (dice.length === 0 || !tray) return;
    const width = tray.clientWidth || 1;
    const timers: number[] = [];
    const later = (ms: number, fn: () => void) =>
      timers.push(window.setTimeout(fn, ms));
    for (const side of ["left", "right"] as const) {
      const first = dice.find((d) => d.side === side);
      if (first) {
        later(first.delayMs, () =>
          playBattleSound("diceThrow", {
            pan: side === "left" ? -0.5 : 0.5,
            gain: 0.7,
          }),
        );
      }
    }
    dice.forEach((die, i) => {
      die.hops.forEach((p, k) => {
        // Stuknięcia: pierwsze odbicie większości kostek, kolejne tylko kilku (nie ściana hałasu).
        if (!((k === 0 && i < 9) || (k > 0 && i < 4))) return;
        later(die.delayMs + CONTACTS[k] * DIE_MS, () =>
          playBattleSound("diceClack", {
            pan: Math.max(-0.8, Math.min(0.8, (p.x / width - 0.5) * 1.4)),
            gain: [0.9, 0.55, 0.32][k],
          }),
        );
      });
    });
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [dice]);

  useEffect(() => {
    const t = window.setTimeout(() => setGone(true), holdMs + 600);
    return () => window.clearTimeout(t);
  }, [holdMs]);

  if (gone) return null;
  return (
    <div
      ref={trayRef}
      className={styles.diceTray}
      style={{ "--fade": `${holdMs}ms` } as CSSProperties}
      aria-hidden="true"
    >
      {dice.map((die) => (
        <DieBody key={die.id} die={die} />
      ))}
    </div>
  );
}
