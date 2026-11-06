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
      data-loading={ghost.loading || undefined}
      aria-hidden="true"
    >
      {ghost.imageUrl ? (
        <img src={ghost.imageUrl} alt="" className={styles.sprite} />
      ) : (
        <span className={styles.chip}>{ghost.asyncId.toUpperCase()}</span>
      )}
      {ghost.count > 1 && <span className={styles.count}>{ghost.count}</span>}
      {/* Sygnał „włóż do statku" — plakietka LOAD nad duchem, gdy kursor jest nad
          statkiem-nosicielem z wolną capacity. */}
      {ghost.loading && (
        <span className={styles.loadTag}>
          <svg width="10" height="10" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 5v14M5 12h14"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
          Load
        </span>
      )}
    </div>,
    document.body,
  );
}
