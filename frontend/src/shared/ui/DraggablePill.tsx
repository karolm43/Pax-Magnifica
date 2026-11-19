import { useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";

/** Przesunięcie kursora (px), od którego gest to przeciągnięcie, a nie klik. */
const DRAG_SLOP = 4;

/**
 * Pigułka zminimalizowanego okna (Decisions, okna ``AppModal minimizable``, dok karty
 * strategii): klik przywraca okno, przeciągnięcie przesuwa pigułkę (``useDraggablePanel``,
 * pozycja zapamiętana pod ``storageKey``).
 */
export function DraggablePill({
  storageKey,
  className,
  title,
  onRestore,
  children,
}: {
  storageKey: string;
  className: string;
  title: string;
  onRestore: () => void;
  children: ReactNode;
}) {
  const drag = useDraggablePanel(storageKey);
  const start = useRef<{ x: number; y: number } | null>(null);

  return createPortal(
    <button
      type="button"
      ref={drag.ref}
      className={className}
      data-draggable-panel
      data-dragging={drag.isDragging || undefined}
      // Przesunięta pigułka stoi od lewego-górnego rogu - bez centrowania i wjazdu z CSS.
      style={{
        ...drag.style,
        ...(drag.isMoved ? { transform: "none", animation: "none" } : {}),
        touchAction: "none",
      }}
      title={`${title} · drag to move`}
      onPointerDown={(event) => {
        start.current = { x: event.clientX, y: event.clientY };
        drag.onHandlePointerDown(event);
      }}
      onClick={(event) => {
        const from = start.current;
        start.current = null;
        const moved =
          from !== null &&
          Math.hypot(event.clientX - from.x, event.clientY - from.y) > DRAG_SLOP;
        if (!moved) onRestore();
      }}
    >
      {children}
    </button>,
    document.body,
  );
}
