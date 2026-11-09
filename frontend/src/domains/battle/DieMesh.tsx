import type { CSSProperties } from "react";
import {
  FACES,
  apply,
  mul,
  restMatrix,
  rotX,
  rotY,
  rotZ,
  shade,
  toMatrix3d,
  BOX,
  type Mat,
} from "./dieGeometry";
import styles from "./BattleOverlay.module.css";

/**
 * Bryła kostki d10 złożona z 10 płaskich ścianek ustawionych w 3D (patrz ``dieGeometry``).
 * Komponent tylko RENDERUJE strukturę; pozycją, obrotem i oświetleniem steruje pętla
 * animacji przez ``poseMesh`` (bez Reacta w każdej klatce).
 */

export type MeshParts = {
  wrap: HTMLElement;
  lift: HTMLElement;
  cube: HTMLElement;
  shadow: HTMLElement;
  faces: HTMLElement[];
};

export function DieMesh({
  side,
  hit,
  size,
  meshKey,
}: {
  side: "left" | "right";
  hit: boolean;
  size: number;
  /** Identyfikator do odnalezienia kostki przez pętlę animacji. */
  meshKey: string;
}) {
  return (
    <div
      className={styles.dieWrap}
      data-die={meshKey}
      data-side={side}
      data-hit={hit || undefined}
      style={{ "--sz": `${size}px` } as CSSProperties}
    >
      <i className={styles.dieShadow} data-part="shadow" />
      <i className={styles.dieGlow} />
      <div className={styles.dieLift} data-part="lift">
        <div className={styles.dieCube} data-part="cube">
          {FACES.map((f, i) => (
            <div
              key={i}
              className={styles.dieFaceP}
              data-part="face"
              style={
                {
                  width: f.width,
                  height: f.height,
                  transform: f.matrix,
                } as CSSProperties
              }
            >
              <i className={styles.faceEdge} style={{ clipPath: f.outer }} />
              <i className={styles.faceFill} style={{ clipPath: f.inner }} />
              <b
                data-ul={f.value === 6 || f.value === 9 || undefined}
                style={{ left: f.cx, top: f.cy }}
              >
                {f.value}
              </b>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Wyszukuje elementy kostki ``meshKey`` w kontenerze (raz, po zamontowaniu). */
export function findMesh(root: HTMLElement, meshKey: string): MeshParts | null {
  const wrap = root.querySelector<HTMLElement>(`[data-die="${meshKey}"]`);
  if (!wrap) return null;
  const part = (name: string) =>
    wrap.querySelector<HTMLElement>(`[data-part="${name}"]`);
  const lift = part("lift");
  const cube = part("cube");
  const shadow = part("shadow");
  if (!lift || !cube || !shadow) return null;
  return {
    wrap,
    lift,
    cube,
    shadow,
    faces: [...wrap.querySelectorAll<HTMLElement>('[data-part="face"]')],
  };
}

/**
 * Ustawia kostkę: pozycja na stole (``x``,``y``), wysokość ``z`` (px), obroty (rad) i ścianka
 * ``face`` leżąca na wierzchu po wyhamowaniu. Przelicza oświetlenie widocznych ścianek.
 */
export function poseMesh(
  parts: MeshParts,
  pose: { x: number; y: number; z: number; rx: number; ry: number; rz: number },
  size: number,
  face: number,
): void {
  const k = size / BOX;
  parts.wrap.style.transform = `translate3d(${pose.x.toFixed(1)}px, ${pose.y.toFixed(1)}px, 0) scale(${k.toFixed(3)})`;
  const lift = pose.z / k;
  parts.lift.style.transform = `translateY(${(-lift).toFixed(1)}px) scale(${(1 + pose.z / (size * 3.2)).toFixed(3)})`;
  parts.shadow.style.transform = `translate(${(lift * 0.22).toFixed(1)}px, ${(lift * 0.4).toFixed(1)}px) scale(${Math.max(0.5, 1 - pose.z / (size * 4)).toFixed(3)})`;
  parts.shadow.style.opacity = String(
    Math.max(0.15, 0.62 - pose.z / (size * 3.4)).toFixed(2),
  );
  const m: Mat = mul(
    mul(rotZ(pose.rz), mul(rotX(pose.rx), rotY(pose.ry))),
    restMatrix(face),
  );
  parts.cube.style.transform = toMatrix3d(m);
  for (let i = 0; i < FACES.length; i++) {
    const n = apply(m, FACES[i].normal);
    if (n[2] > 0) parts.faces[i].style.setProperty("--b", shade(n).toFixed(2));
  }
}
