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
  dieState,
  planDice,
  type Die,
  type DiceGroup,
} from "./diceRoll";
import { faceOf } from "./dieGeometry";
import { DieMesh, findMesh, poseMesh, type MeshParts } from "./DieMesh";
import styles from "./BattleOverlay.module.css";

/**
 * Fizyczny rzut kośćmi d10 na stół pola bitwy (czysta prezentacja — wartości z silnika).
 *
 * Każda kostka to prawdziwa bryła 3D (10 ścianek, oświetlenie liczone w każdej klatce). Wpada
 * na stół z krawędzi ekranu albo z puli (gdy gracz przytrzymał „Roll"), obraca się, odbija
 * trzy razy od blatu (coraz niżej, z cieniem) i układa ścianką z wynikiem do góry. Salwa
 * rusza dopiero po wylądowaniu ostatniej kostki (``Volley.diceMs``).
 */

const reducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Rzut do pokazania na stole: kości obu stron i moment, w którym wszystkie już leżą. */
export type DiceRollSpec = {
  id: number;
  rolls: { left: DiceGroup[]; right: DiceGroup[] };
  diceMs: number;
  /** Wall-clock start (``Date.now()``) to anchor the animation to; absent = starts on mount. */
  startedAt?: number;
};

/** Stół z kośćmi dla jednej salwy (znika sam po odczytaniu rzutu). */
export function DiceTray({
  volley,
  fromPool,
  pool,
  solo = false,
}: {
  volley: DiceRollSpec;
  /** Rzuca jedna strona: kostki lądują pośrodku. */
  solo?: boolean;
  /** Rzut po przytrzymaniu „Roll": kostki startują z puli, nie z krawędzi ekranu. */
  fromPool: boolean;
  /** Liczba kostek w puli każdej strony (układ startowy). */
  pool: { left: number; right: number };
}) {
  const trayRef = useRef<HTMLDivElement>(null);
  const [dice, setDice] = useState<Die[]>([]);
  const [gone, setGone] = useState(false);
  const holdMs = volley.diceMs + READ_MS + 1500;

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
        fromPool,
        pool,
        solo,
      }),
    );
    // Plan liczymy raz na salwę.
  }, [volley.id]);

  // Pętla animacji: pozycja, obrót i oświetlenie każdej kostki w każdej klatce.
  useLayoutEffect(() => {
    const tray = trayRef.current;
    if (!tray || dice.length === 0) return;
    const meshes: (MeshParts | null)[] = dice.map((d) => findMesh(tray, d.id));
    const faces = dice.map((d) => faceOf(d.value));
    const settled = dice.map(() => false);
    const pose = (i: number, t: number) => {
      const mesh = meshes[i];
      if (!mesh || settled[i]) return true;
      const st = dieState(dice[i], t - dice[i].delayMs);
      poseMesh(mesh, st, dice[i].size, faces[i]);
      if (st.settled) {
        settled[i] = true;
        mesh.wrap.dataset.settled = "1";
      }
      return st.settled;
    };
    if (reducedMotion()) {
      dice.forEach((_, i) => pose(i, DIE_MS + 5000));
      return;
    }
    // Anchor to the roll's own start: render lag or a throttled background tab makes the dice
    // skip ahead instead of landing after the result (timed from the same start) is revealed.
    const late = volley.startedAt ? Math.max(0, Date.now() - volley.startedAt) : 0;
    const t0 = performance.now() - late;
    dice.forEach((_, i) => pose(i, late));
    let raf = 0;
    const frame = (now: number) => {
      let alive = false;
      for (let i = 0; i < dice.length; i++) {
        if (!pose(i, now - t0)) alive = true;
      }
      if (alive) raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [dice]);

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
        <DieMesh
          key={die.id}
          meshKey={die.id}
          side={die.side}
          hit={die.hit}
          size={die.size}
        />
      ))}
    </div>
  );
}
