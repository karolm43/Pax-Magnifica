import type { ReactNode } from "react";
import styles from "./HoldControls.module.css";

/**
 * Treść dymka przycisków narzędzi ręki (Undo, Hold): co robi przycisk + stan „teraz".
 * Jeden wzór dla obu, żeby gracz zawsze wiedział, co się stanie po kliknięciu.
 */
export function ToolHint({
  title,
  children,
  status,
  tone = "info",
}: {
  title: string;
  children: ReactNode;
  status?: ReactNode;
  tone?: "info" | "blocked";
}) {
  return (
    <span className={styles.hint}>
      <b className={styles.hintTitle}>{title}</b>
      <span className={styles.hintBody}>{children}</span>
      {status && (
        <span className={styles.hintStatus} data-tone={tone}>
          {status}
        </span>
      )}
    </span>
  );
}
