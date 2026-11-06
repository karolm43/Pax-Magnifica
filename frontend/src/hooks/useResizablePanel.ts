import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";

/** Rozmiar panelu (piksele). Null = jeszcze nieskalowany (trzyma rozmiar z CSS). */
type Size = { w: number; h: number } | null;

type ResizablePanel = {
  /** Styl rozmiaru do nałożenia na panel (width/height albo pusty, gdy domyślny). */
  style: CSSProperties;
  /** Handler na uchwyt skalowania (róg panelu). */
  onHandlePointerDown: (event: ReactPointerEvent) => void;
  /** Czy panel jest właśnie skalowany (do wyłączenia animacji/zaznaczania). */
  isResizing: boolean;
  /** Reset rozmiaru do domyślnego (CSS). */
  reset: () => void;
};

type Bounds = { minW: number; minH: number; maxW: number; maxH: number };

const DEFAULT_BOUNDS: Bounds = { minW: 260, minH: 180, maxW: 640, maxH: 900 };

function readSize(storageKey: string): Size {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { w: number; h: number };
    if (typeof parsed.w === "number" && typeof parsed.h === "number") {
      return parsed;
    }
  } catch {
    /* uszkodzony/niedostępny wpis — wracamy do rozmiaru domyślnego */
  }
  return null;
}

function writeSize(storageKey: string, next: Size): void {
  try {
    if (next) localStorage.setItem(storageKey, JSON.stringify(next));
    else localStorage.removeItem(storageKey);
  } catch (error) {
    console.warn("Nie udało się zapisać rozmiaru panelu:", error);
  }
}

/**
 * Czyni panel SKALOWALNYM za uchwyt w rogu (pointer/dotyk). Rozmiar zapamiętywany
 * w ``localStorage`` pod ``storageKey`` (przeżywa przeładowanie). Dopóki użytkownik
 * nie zmieni rozmiaru, zwracany ``style`` jest pusty i panel trzyma rozmiar z CSS.
 * Rozmiar jest utrzymywany w granicach (``bounds``) i okna, żeby panel był użyteczny.
 */
export function useResizablePanel(
  storageKey: string,
  bounds: Partial<Bounds> = {},
): ResizablePanel {
  const b = { ...DEFAULT_BOUNDS, ...bounds };
  const [size, setSize] = useState<Size>(() => readSize(storageKey));
  const [isResizing, setIsResizing] = useState(false);

  // Punkt startu skalowania: róg panelu (clientX/Y) + rozmiar bazowy.
  const resizeRef = useRef<{
    startX: number;
    startY: number;
    baseW: number;
    baseH: number;
  } | null>(null);

  const persist = useCallback(
    (next: Size) => writeSize(storageKey, next),
    [storageKey],
  );

  const clamp = useCallback(
    (w: number, h: number): { w: number; h: number } => {
      const maxW = Math.min(b.maxW, window.innerWidth - 24);
      const maxH = Math.min(b.maxH, window.innerHeight - 24);
      return {
        w: Math.min(Math.max(b.minW, w), Math.max(b.minW, maxW)),
        h: Math.min(Math.max(b.minH, h), Math.max(b.minH, maxH)),
      };
    },
    [b.minW, b.minH, b.maxW, b.maxH],
  );

  useEffect(() => {
    if (!isResizing) return;

    const handleMove = (event: PointerEvent) => {
      const r = resizeRef.current;
      if (!r) return;
      event.preventDefault();
      const next = clamp(
        r.baseW + (event.clientX - r.startX),
        r.baseH + (event.clientY - r.startY),
      );
      setSize(next);
    };

    const handleUp = () => {
      setIsResizing(false);
      setSize((current) => {
        persist(current);
        return current;
      });
    };

    window.addEventListener("pointermove", handleMove, { passive: false });
    window.addEventListener("pointerup", handleUp);
    window.addEventListener("pointercancel", handleUp);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
      window.removeEventListener("pointercancel", handleUp);
    };
  }, [isResizing, clamp, persist]);

  const onHandlePointerDown = useCallback((event: ReactPointerEvent) => {
    if (event.button !== 0 && event.pointerType === "mouse") return;
    // Uchwyt resize siedzi na panelu (data-draggable-panel) — mierzymy jego rozmiar.
    const handle = event.currentTarget as HTMLElement;
    const panel = handle.closest("[data-draggable-panel]") ?? handle;
    const rect = panel.getBoundingClientRect();
    resizeRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      baseW: rect.width,
      baseH: rect.height,
    };
    // Nie pozwól, by gest skalowania zaczął też przeciąganie panelu / pan mapy.
    event.stopPropagation();
    setIsResizing(true);
  }, []);

  const reset = useCallback(() => {
    setSize(null);
    persist(null);
  }, [persist]);

  const style: CSSProperties = size ? { width: size.w, height: size.h } : {};

  return { style, onHandlePointerDown, isResizing, reset };
}
