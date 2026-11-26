import { useEffect, useState, type ReactNode } from "react";
import { IconArrowsMaximize, IconMinus } from "@tabler/icons-react";
import { ActionIcon, Modal, type ModalProps } from "@/ds";
import cx from "clsx";
import { DraggablePill } from "./DraggablePill";
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

  // Minimalizacja stoi w prawym górnym rogu, tuż obok zamknięcia (×).
  const minimizeButton: ReactNode = canMinimize ? (
    <ActionIcon
      variant="subtle"
      className={styles.minimize}
      onClick={() => setMinimized(true)}
      aria-label="Minimize to see the board"
      title="Minimize to see the board"
    >
      <IconMinus size={16} aria-hidden="true" />
    </ActionIcon>
  ) : null;

  return (
    <>
      <Modal
        opened={opened && !(canMinimize && minimized)}
        centered={centered}
        zIndex={zIndex}
        title={title}
        headerActions={minimizeButton}
        classNames={{ ...classNames, header: cx("overlay-modal-header", classNames.header) }}
        styles={{ ...slotStyles, header: { padding: "14px 16px 12px", ...slotStyles.header } }}
        {...props}
      />
      {opened && canMinimize && minimized ? (
        <DraggablePill
          storageKey="minimizedPill.pos.v1"
          className={styles.pill}
          title="Restore the window"
          onRestore={() => setMinimized(false)}
        >
          <IconArrowsMaximize size={15} aria-hidden="true" />
          <span>{label}</span>
        </DraggablePill>
      ) : null}
    </>
  );
}
