import { IconAlertTriangle, IconShip } from "@tabler/icons-react";
import { useFleetPool } from "@/api/useBoardEditor";
import styles from "./FleetPoolWarning.module.css";

/**
 * Wskaźnik FLEET POOL (RULES.md 42) aktywnego gracza w aktywnym systemie: ile statków
 * nie-myśliwskich stoi względem puli floty. `extra` = statki, które gracz dopiero dodaje
 * (np. zamówienie w produkcji). Pod spodem prognoza CAPACITY: myśliwce w przestrzeni mieszczą się
 * w pojemności statków oraz w miejscach doków (dok: „do 3 myśliwców nie liczy się do capacity").
 *
 * Reguła pozwala przekroczyć pulę (ruch, produkcja), ale nadwyżka zostanie zaraz usunięta -
 * dlatego przy przekroczeniu pokazujemy OSTRZEŻENIE, zanim gracz zatwierdzi akcję.
 */
export function FleetPoolWarning({
  extra = 0,
  extraFighters = 0,
}: {
  extra?: number;
  /** Myśliwce, które gracz dopiero dodaje do przestrzeni (zamówienie w produkcji). */
  extraFighters?: number;
}) {
  const { data } = useFleetPool(true);
  if (!data?.known) return null;
  const total = data.total + extra;
  const over = Math.max(0, total - data.pool);
  const cells = Math.max(data.pool, total);
  const cap = data.capacity;
  const fighters = cap.fighters + extraFighters;
  const fighterLoad = fighters * cap.fighterCost;
  const capNeed = fighterLoad + cap.otherLoad - Math.min(fighterLoad, cap.fighterOnly);
  const capOver = Math.max(0, capNeed - cap.general);
  const showCap = cap.general + cap.fighterOnly > 0 || fighters + cap.otherLoad > 0;
  return (
    <div
      className={styles.box}
      data-over={over > 0 || capOver > 0 || undefined}
      role="status"
    >
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
      {showCap && (
        <div className={styles.capRow} data-over={capOver > 0 || undefined}>
          <span className={styles.label}>Capacity</span>
          <b>
            {capNeed} / {cap.general}
          </b>
          {cap.fighterOnly > 0 && (
            <small>
              + {Math.min(fighterLoad, cap.fighterOnly)} / {cap.fighterOnly} dock slots (fighters
              only, don't count against capacity)
            </small>
          )}
          {capOver > 0 && (
            <p className={styles.warn}>
              <IconAlertTriangle size={14} aria-hidden="true" />
              <span>
                Fighters / ground forces exceed capacity by {capOver}. Extra units in space will
                have to be removed.
              </span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default FleetPoolWarning;
