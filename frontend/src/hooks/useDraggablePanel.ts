import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";

/**
 * Pozycja panelu (piksele od lewego-górnego rogu obszaru planszy). Null = jeszcze
 * nieprzesunięty (panel trzyma pozycję domyślną z CSS).
 */
type Position = { x: number; y: number } | null;

type DraggablePanel = {
  /** Styl do nałożenia na panel (position/left/top albo pusty, gdy domyślny). */
  style: CSSProperties;
  /** Handler na uchwyt przeciągania (nagłówek panelu). */
  onHandlePointerDown: (event: ReactPointerEvent) => void;
  /** Czy panel jest właśnie przeciągany (do wyłączenia animacji/zaznaczania). */
  isDragging: boolean;
  /** Reset pozycji do domyślnej (np. dwuklik na uchwycie). */
  reset: () => void;
};

function readPosition(storageKey: string): Position {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { x: number; y: number };
    if (typeof parsed.x === "number" && typeof parsed.y === "number") {
      return parsed;
    }
  } catch {
    /* uszkodzony/niedostępny wpis — wracamy do domyślnej pozycji */
  }
  return null;
}

function writePosition(storageKey: string, next: Position): void {
  try {
    if (next) localStorage.setItem(storageKey, JSON.stringify(next));
    else localStorage.removeItem(storageKey);
  } catch (error) {
    console.warn("Nie udało się zapisać pozycji panelu:", error);
  }
}

/**
 * Czyni panel przesuwalnym myszą/dotykiem za uchwyt (nagłówek). Pozycja jest
 * zapamiętywana w ``localStorage`` pod ``storageKey`` (przeżywa przeładowanie).
 * Dopóki użytkownik nie przesunie panelu, zwracany ``style`` jest pusty i panel
 * trzyma pozycję z CSS (lewy-górny róg planszy). Panel jest utrzymywany w
 * granicach okna, żeby nie uciekł poza ekran.
 */
export function useDraggablePanel(storageKey: string): DraggablePanel {
  const [position, setPosition] = useState<Position>(() =>
    readPosition(storageKey),
  );
  const [isDragging, setIsDragging] = useState(false);

  // Offset kursora względem rogu panelu + rozmiar panelu (do trzymania w oknie).
  const dragRef = useRef<{
    offsetX: number;
    offsetY: number;
    width: number;
    height: number;
  } | null>(null);

  const persist = useCallback(
    (next: Position) => writePosition(storageKey, next),
    [storageKey],
  );

  const clampToViewport = useCallback(
    (x: number, y: number): { x: number; y: number } => {
      const drag = dragRef.current;
      const margin = 4;
      const w = drag?.width ?? 300;
      const h = drag?.height ?? 120;
      const maxX = Math.max(margin, window.innerWidth - w - margin);
      const maxY = Math.max(margin, window.innerHeight - h - margin);
      return {
        x: Math.min(Math.max(margin, x), maxX),
        y: Math.min(Math.max(margin, y), maxY),
      };
    },
    [],
  );

  useEffect(() => {
    if (!isDragging) return;

    // Na czas przeciągania wyłączamy zaznaczanie tekstu/kafelków na całej stronie
    // (inaczej kursor „maluje" zaznaczenie po mapie).
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.userSelect = "none";
    window.getSelection()?.removeAllRanges();

    const handleMove = (event: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag) return;
      const next = clampToViewport(
        event.clientX - drag.offsetX,
        event.clientY - drag.offsetY,
      );
      setPosition(next);
    };

    const handleUp = () => {
      setIsDragging(false);
      setPosition((current) => {
        persist(current);
        return current;
      });
    };

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
    window.addEventListener("pointercancel", handleUp);
    return () => {
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
      window.removeEventListener("pointercancel", handleUp);
    };
  }, [isDragging, clampToViewport, persist]);

  const onHandlePointerDown = useCallback((event: ReactPointerEvent) => {
    // Tylko lewy przycisk; pomijamy klik w interaktywne elementy nagłówka
    // (np. przycisk zwijania) — tam drag by przeszkadzał.
    if (event.button !== 0) return;
    const target = event.target as HTMLElement;
    if (target.closest("[data-no-drag]")) return;
    // Zapobiega startowi zaznaczania tekstu już na pointerdown.
    event.preventDefault();

    // Panel = najbliższy przodek z atrybutem data-draggable-panel (sam panel).
    const handle = event.currentTarget as HTMLElement;
    const panel = handle.closest("[data-draggable-panel]");
    const rect = (panel ?? handle).getBoundingClientRect();
    dragRef.current = {
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
      width: rect.width,
      height: rect.height,
    };
    setIsDragging(true);
  }, []);

  const reset = useCallback(() => {
    setPosition(null);
    persist(null);
  }, [persist]);

  const style: CSSProperties = position
    ? {
        position: "fixed",
        left: position.x,
        top: position.y,
        // KLUCZOWE: zdejmujemy CSS-owe ``bottom``/``right`` — inaczej przy ``fixed``
        // z jednoczesnym ``top`` i ``bottom`` (bez ``height``) panel rozciąga się
        // pionowo (bug „dok rośnie przy przesuwaniu"). Pozycjonujemy wyłącznie od
        // lewego-górnego rogu.
        right: "auto",
        bottom: "auto",
      }
    : {};

  return { style, onHandlePointerDown, isDragging, reset };
}
