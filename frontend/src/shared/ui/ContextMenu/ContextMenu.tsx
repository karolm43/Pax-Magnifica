import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { getPortalRoot } from "@/ds";
import styles from "./ContextMenu.module.css";

/**
 * Pojedyncza pozycja menu kontekstowego. Rozszerzalne — dokładasz kolejne obiekty
 * do tablicy ``items`` bez zmiany komponentu.
 */
export type ContextMenuItem = {
  /** Etykieta pozycji. */
  label: ReactNode;
  /** Akcja po kliknięciu (menu zamyka się automatycznie po wywołaniu). */
  onSelect: () => void;
  /** Opcjonalna ikona po lewej. */
  icon?: ReactNode;
  /** Wyszarzenie i blokada kliknięcia. */
  disabled?: boolean;
  /** Ton „ostrzegawczy" (np. akcje destrukcyjne) — inny akcent. */
  danger?: boolean;
};

type Position = { x: number; y: number };

/**
 * Lekkie menu kontekstowe otwierane pod kursorem (prawy przycisk myszy). Hook
 * ``useContextMenu`` daje handler ``onContextMenu`` i stan; komponent ``ContextMenu``
 * renderuje listę pozycji w porcie DS (nad całą planszą), zamyka się na klik poza,
 * Escape, scroll i zmianę rozmiaru okna. Pozycja jest dociskana do widoku, żeby menu
 * nie wyszło poza ekran.
 */
export function useContextMenu() {
  const [position, setPosition] = useState<Position | null>(null);

  const onContextMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setPosition({ x: event.clientX, y: event.clientY });
  }, []);

  const close = useCallback(() => setPosition(null), []);

  return { position, onContextMenu, close, isOpen: position !== null };
}

export function ContextMenu({
  position,
  items,
  onClose,
  title,
}: {
  position: Position | null;
  items: ContextMenuItem[];
  onClose: () => void;
  /** Opcjonalny nagłówek menu (np. nazwa komponentu). */
  title?: ReactNode;
}) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [adjusted, setAdjusted] = useState<Position | null>(null);

  // Po wyrenderowaniu docisk do widoku (nie wychodzić poza prawą/dolną krawędź).
  useEffect(() => {
    if (!position) {
      setAdjusted(null);
      return;
    }
    const el = menuRef.current;
    if (!el) {
      setAdjusted(position);
      return;
    }
    const rect = el.getBoundingClientRect();
    const margin = 6;
    const x = Math.min(position.x, window.innerWidth - rect.width - margin);
    const y = Math.min(position.y, window.innerHeight - rect.height - margin);
    setAdjusted({ x: Math.max(margin, x), y: Math.max(margin, y) });
  }, [position]);

  // Zamknięcie na Escape, scroll i resize (klik-poza obsługuje overlay niżej).
  useEffect(() => {
    if (!position) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onClose);
    window.addEventListener("scroll", onClose, true);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onClose);
      window.removeEventListener("scroll", onClose, true);
    };
  }, [position, onClose]);

  const root = getPortalRoot();
  if (!position || !root) return null;

  const pos = adjusted ?? position;

  return createPortal(
    <>
      {/* Przezroczysty overlay łapie klik/RMB poza menu → zamknięcie. */}
      <div
        className={styles.overlay}
        onPointerDown={onClose}
        onContextMenu={(e) => {
          e.preventDefault();
          onClose();
        }}
      />
      <div
        ref={menuRef}
        className={styles.menu}
        style={{ left: pos.x, top: pos.y }}
        role="menu"
      >
        {title && <div className={styles.title}>{title}</div>}
        {items.map((item, index) => (
          <button
            key={index}
            type="button"
            role="menuitem"
            className={styles.item}
            data-danger={item.danger || undefined}
            disabled={item.disabled}
            onClick={() => {
              if (item.disabled) return;
              item.onSelect();
              onClose();
            }}
          >
            {item.icon && <span className={styles.itemIcon}>{item.icon}</span>}
            <span className={styles.itemLabel}>{item.label}</span>
          </button>
        ))}
      </div>
    </>,
    root,
  );
}
