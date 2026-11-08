import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { IconArrowsMaximize, IconMinus } from "@tabler/icons-react";
import { Modal, type ModalProps } from "@/ds";
import cx from "clsx";
import styles from "./AppModal.module.css";

type AppModalProps = ModalProps & {
  /**
   * Pozwala ZMINIMALIZOWAĆ okno, żeby zobaczyć planszę (decyzje follow, wybory kart,
   * walka...). Zminimalizowane okno zostaje „w grze" - zamienia się w pastylkę przy dolnej
   * krawędzi; klik przywraca. ``true`` = etykieta pastylki z tytułu; napis = własna etykieta.
   */
  minimizable?: boolean | string;
};

/**
 * The app's modal frame: the ds Modal with the shared header from
 * overlays.css. The header keeps its own padding whatever the body uses, so a
 * modal can lay out a full-bleed body and a decision footer with padding={0}.
 */
export function AppModal({
  zIndex = "var(--z-app-modal)",
  centered = true,
  classNames = {},
  styles: slotStyles = {},
  minimizable,
  title,
  opened,
  ...props
}: AppModalProps) {
  const [minimized, setMinimized] = useState(false);
  // Zamknięcie okna (koniec decyzji) kasuje minimalizację - następne otwiera się normalnie.
  useEffect(() => {
    if (!opened) setMinimized(false);
  }, [opened]);

  const canMinimize = minimizable !== undefined && minimizable !== false;
  const label: ReactNode =
    typeof minimizable === "string" ? minimizable : (title ?? "Window");

  const header: ReactNode = canMinimize ? (
    <span className={styles.titleRow}>
      <span className={styles.titleText}>{title}</span>
      <button
        type="button"
        className={styles.minimize}
        onClick={() => setMinimized(true)}
        aria-label="Minimize to see the board"
        title="Minimize to see the board"
      >
        <IconMinus size={16} aria-hidden="true" />
      </button>
    </span>
  ) : (
    title
  );

  return (
    <>
      <Modal
        opened={opened && !(canMinimize && minimized)}
        centered={centered}
        zIndex={zIndex}
        title={header}
        classNames={{ ...classNames, header: cx("overlay-modal-header", classNames.header) }}
        styles={{ ...slotStyles, header: { padding: "14px 16px 12px", ...slotStyles.header } }}
        {...props}
      />
      {opened && canMinimize && minimized
        ? createPortal(
            <button
              type="button"
              className={styles.pill}
              onClick={() => setMinimized(false)}
              title="Restore the window"
            >
              <IconArrowsMaximize size={15} aria-hidden="true" />
              <span>{label}</span>
            </button>,
            document.body,
          )
        : null}
    </>
  );
}
