import { createPortal } from "react-dom";
import type { DragGhost } from "./hooks/useUnitDrag";
import styles from "./UnitDragGhost.module.css";

/**
 * „Duch" jednostki podążający za kursorem podczas przeciągania. Renderowany przez
 * portal do ``document.body``, bo mapa ma ``transform: scale`` (containing block dla
 * ``position: fixed``) — duch w drzewie mapy skakałby ze skalą. W body jest w pikselach
 * ekranu (clientX/Y) i nie przechwytuje zdarzeń (``pointer-events: none``), więc nie
 * przeszkadza wykrywaniu celu pod kursorem.
 */
export function UnitDragGhost({ ghost }: { ghost: DragGhost | null }) {
  if (!ghost) return null;
  return createPortal(
    <div
      className={styles.ghost}
      style={{ left: `${ghost.x}px`, top: `${ghost.y}px` }}
      aria-hidden="true"
    >
      {ghost.imageUrl ? (
        <img src={ghost.imageUrl} alt="" className={styles.sprite} />
      ) : (
        <span className={styles.chip}>{ghost.asyncId.toUpperCase()}</span>
      )}
      {ghost.count > 1 && <span className={styles.count}>{ghost.count}</span>}
    </div>,
    document.body,
  );
}
