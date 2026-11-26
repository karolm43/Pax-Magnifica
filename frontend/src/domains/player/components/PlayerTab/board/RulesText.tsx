import cx from "clsx";
import styles from "./RulesText.module.css";

/*
 * Printed rules text of the player zone - leader cards, faction abilities, unit abilities. One
 * typeface, size and timing-window style for all of them, so the board reads as one sheet.
 */
export function RulesText({
  timing,
  text,
  className,
}: {
  /** Timing window ("When a player spends resources to research:"), on its own line. */
  timing?: string;
  text?: string;
  className?: string;
}) {
  if (!timing && !text) return null;
  return (
    <p className={cx(styles.rules, className)}>
      {timing && <b className={styles.window}>{timing}</b>}
      {text}
    </p>
  );
}
