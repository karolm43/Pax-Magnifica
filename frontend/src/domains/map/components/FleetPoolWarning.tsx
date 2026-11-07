import { IconAlertTriangle, IconShip } from "@tabler/icons-react";
import { useFleetPool } from "@/api/useBoardEditor";
import styles from "./FleetPoolWarning.module.css";

/**
 * Wskaźnik FLEET POOL (RULES.md 42) aktywnego gracza w aktywnym systemie: ile statków
 * nie-myśliwskich stoi względem puli floty. `extra` = statki, które gracz dopiero dodaje
 * (np. zamówienie w produkcji).
 *
 * Reguła pozwala przekroczyć pulę (ruch, produkcja), ale nadwyżka zostanie zaraz usunięta -
 * dlatego przy przekroczeniu pokazujemy OSTRZEŻENIE, zanim gracz zatwierdzi akcję.
 */
export function FleetPoolWarning({ extra = 0 }: { extra?: number }) {
  const { data } = useFleetPool(true);
  if (!data?.known) return null;
  const total = data.total + extra;
  const over = Math.max(0, total - data.pool);
  const cells = Math.max(data.pool, total);
  return (
    <div className={styles.box} data-over={over > 0 || undefined} role="status">
      <div className={styles.head}>
        <span className={styles.label}>
          <IconShip size={14} aria-hidden="true" /> Fleet pool
        </span>
        <b className={styles.count}>
          {total}
          <small> / {data.pool} ships</small>
        </b>
      </div>
      <div className={styles.cells} aria-hidden="true">
        {Array.from({ length: cells }, (_, i) => (
          <span
            key={i}
            className={styles.cell}
            data-kind={i >= data.pool ? "over" : i < data.total ? "have" : "new"}
          />
        ))}
      </div>
      {over > 0 ? (
        <p className={styles.warn}>
          <IconAlertTriangle size={14} aria-hidden="true" />
          <span>
            Over the pool by {over}. You may place them, but {over} ship
            {over === 1 ? "" : "s"} must be removed right after.
          </span>
        </p>
      ) : (
        <small className={styles.ok}>
          Non-fighter ships in this system. Fighters and ground forces don't count.
        </small>
      )}
    </div>
  );
}

export default FleetPoolWarning;
