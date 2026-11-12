import { IconAlertTriangle, IconShip } from "@tabler/icons-react";
import { useFleetPool } from "@/api/useBoardEditor";
import styles from "./FleetPoolWarning.module.css";

/** Górny limit kratek paska puli (zabezpieczenie widoku; realna pula to kilka-kilkanaście). */
const MAX_CELLS = 24;

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
  const cap = data.capacity;
  const fighters = cap.fighters + extraFighters;
  const fighterLoad = fighters * cap.fighterCost;
  // Fighter II: myśliwce ponad capacity nie są usuwane z capacity, tylko liczą się do puli floty.
  const toFleet = cap.fightersToFleet === true;
  const room = cap.fighterOnly + Math.max(0, cap.general - cap.otherLoad);
  const fleetFighters = toFleet
    ? Math.max(0, fighters - Math.floor(room / Math.max(cap.fighterCost, 1)))
    : 0;
  const total = data.total + extra + (fleetFighters - (cap.fleetFighters ?? 0));
  // Bez limitu (np. bohater Letnev do końca rundy): nic nie jest „ponad pulę”, kratki tylko
  // dla obecnych statków.
  const unlimited = data.unlimited === true;
  const over = unlimited ? 0 : Math.max(0, total - data.pool);
  const cells = Math.min(MAX_CELLS, unlimited ? total : Math.max(data.pool, total));
  const capNeed = toFleet
    ? cap.otherLoad
    : fighterLoad + cap.otherLoad - Math.min(fighterLoad, cap.fighterOnly);
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
          <small>{unlimited ? " ships · no limit this round" : ` / ${data.pool} ships`}</small>
        </b>
      </div>
      <div className={styles.cells} aria-hidden="true">
        {Array.from({ length: cells }, (_, i) => (
          <span
            key={i}
            className={styles.cell}
            data-kind={
              !unlimited && i >= data.pool ? "over" : i < data.total ? "have" : "new"
            }
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
          {toFleet
            ? `Non-fighter ships${fleetFighters > 0 ? ` + ${fleetFighters} fighter${fleetFighters === 1 ? "" : "s"} beyond capacity (Fighter II)` : ""}. Other fighters and ground forces don't count.`
            : "Non-fighter ships in this system. Fighters and ground forces don't count."}
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

/**
 * Ten sam wskaźnik FLEET POOL dla FAZY STATUSU (RULES.md 42): gracz zmienia liczbę żetonów
 * w puli floty, a pasek pokazuje jego NAJWIĘKSZĄ flotę względem nowej puli. Gdy pula spada
 * poniżej floty w jakimś systemie, ostrzega, ile statków i gdzie trzeba będzie usunąć - po
 * zatwierdzeniu silnik otworzy wymuszone okno usuwania.
 */
export function FleetPoolStatusMeter({
  pool,
  ships,
  systemName,
}: {
  /** Planowana liczba żetonów w puli floty. */
  pool: number;
  /** Statki liczone do puli per system: `{pozycja: ile}`. */
  ships: Record<string, number>;
  systemName?: (position: string) => string;
}) {
  const entries = Object.entries(ships).sort((a, b) => b[1] - a[1]);
  const largest = entries[0]?.[1] ?? 0;
  const where = entries[0]?.[0];
  const overList = entries.filter(([, n]) => n > pool);
  const overTotal = overList.reduce((sum, [, n]) => sum + (n - pool), 0);
  const cells = Math.min(MAX_CELLS, Math.max(pool, largest));
  const label = (pos: string) => systemName?.(pos) ?? pos;
  return (
    <div className={styles.box} data-over={overTotal > 0 || undefined} role="status">
      <div className={styles.head}>
        <span className={styles.label}>
          <IconShip size={14} aria-hidden="true" /> Fleet pool
        </span>
        <b className={styles.count}>
          {largest}
          <small> / {pool} ships</small>
        </b>
      </div>
      <div className={styles.cells} aria-hidden="true">
        {Array.from({ length: cells }, (_, i) => (
          <span
            key={i}
            className={styles.cell}
            data-kind={i >= pool ? "over" : i < largest ? "have" : undefined}
          />
        ))}
      </div>
      {overTotal > 0 ? (
        <p className={styles.warn}>
          <IconAlertTriangle size={14} aria-hidden="true" />
          <span>
            Too few fleet tokens. You will have to remove{" "}
            {overList
              .map(([pos, n]) => `${n - pool} ship${n - pool === 1 ? "" : "s"} in ${label(pos)}`)
              .join(", ")}
            .
          </span>
        </p>
      ) : (
        <small className={styles.ok}>
          {where
            ? `Largest fleet: ${largest} in ${label(where)}. Fighters don't count.`
            : "No ships on the board."}
        </small>
      )}
    </div>
  );
}
