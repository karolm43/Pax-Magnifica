import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { playBattleSound } from "./battleSound";
import { poolLayout, rng, type DieSide } from "./diceRoll";
import { DieMesh, findMesh, poseMesh, type MeshParts } from "./DieMesh";
import styles from "./BattleOverlay.module.css";

/**
 * Pula kości na czas przytrzymania „Roll": wszystkie kostki obu stron wpadają do garści i
 * się w niej przetaczają (widać, ILE kości rzuca każda strona). Puszczenie przycisku kończy
 * pulę, a kości lecą na stół (``DiceTray`` startuje z tych samych miejsc).
 */

type Wobble = {
  side: DieSide;
  key: string;
  base: { x: number; y: number };
  size: number;
  /** Fazy i prędkości kołysania oraz obrotu (rad/ms). */
  fx: number;
  fy: number;
  px: number;
  py: number;
  wx: number;
  wy: number;
  wz: number;
  enter: number;
};

export function DicePool({
  left,
  right,
}: {
  left: number;
  right: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState({ w: 0, h: 0 });
  useLayoutEffect(() => {
    const el = ref.current;
    if (el) setBox({ w: el.clientWidth, h: el.clientHeight });
  }, []);

  const dice = useMemo<Wobble[]>(() => {
    if (box.w === 0) return [];
    const rand = rng(7);
    return (["left", "right"] as const).flatMap((side) => {
      const n = Math.min(side === "left" ? left : right, 30);
      const { points, size } = poolLayout(side, n, box.w, box.h);
      return points.map((base, i) => ({
        side,
        key: `${side}-${i}`,
        base,
        size,
        fx: 0.008 + rand() * 0.008,
        fy: 0.009 + rand() * 0.008,
        px: rand() * 6.28,
        py: rand() * 6.28,
        wx: (rand() < 0.5 ? -1 : 1) * (0.004 + rand() * 0.006),
        wy: (rand() < 0.5 ? -1 : 1) * (0.004 + rand() * 0.006),
        wz: (rand() < 0.5 ? -1 : 1) * (0.002 + rand() * 0.004),
        enter: (side === "left" ? 0 : 120) + i * 55,
      }));
    });
  }, [box, left, right]);

  useLayoutEffect(() => {
    const root = ref.current;
    if (!root || dice.length === 0) return;
    const meshes: (MeshParts | null)[] = dice.map((d) => findMesh(root, d.key));
    const t0 = performance.now();
    let raf = 0;
    const frame = (now: number) => {
      const t = now - t0;
      dice.forEach((d, i) => {
        const mesh = meshes[i];
        if (!mesh) return;
        const te = t - d.enter;
        // Wpadanie do puli: kostka spada z góry i dopiero potem zaczyna się przetaczać.
        const drop = Math.max(0, 1 - te / 320);
        mesh.wrap.style.visibility = te < 0 ? "hidden" : "visible";
        const amp = d.size * 0.3;
        poseMesh(
          mesh,
          {
            x: d.base.x + Math.sin(t * d.fx + d.px) * amp,
            y: d.base.y + Math.cos(t * d.fy + d.py) * amp,
            z:
              drop * drop * d.size * 1.8 +
              Math.abs(Math.sin(t * d.fx * 1.7 + d.py)) * d.size * 0.32,
            rx: t * d.wx,
            ry: t * d.wy,
            rz: t * d.wz,
          },
          d.size,
          0,
        );
      });
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [dice]);

  // Grzechot kości w garści, dopóki trzymasz przycisk.
  useEffect(() => {
    const total = left + right;
    if (total === 0) return;
    const id = window.setInterval(() => {
      playBattleSound("diceClack", {
        pan: (Math.random() - 0.5) * 1.2,
        gain: 0.18 + Math.random() * 0.18,
      });
    }, 110);
    return () => window.clearInterval(id);
  }, [left, right]);

  return (
    <div ref={ref} className={styles.dicePool} aria-hidden="true">
      {dice.map((d) => (
        <DieMesh
          key={d.key}
          meshKey={d.key}
          side={d.side}
          hit={false}
          size={d.size}
        />
      ))}
      <span className={styles.poolCount} data-side="left">
        <b>{left}</b> dice
      </span>
      <span className={styles.poolCount} data-side="right">
        <b>{right}</b> dice
      </span>
    </div>
  );
}
