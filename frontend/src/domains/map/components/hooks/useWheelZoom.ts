import { useEffect, useLayoutEffect, useRef, type RefObject } from "react";

/*
 * Ctrl + kółko myszy (oraz „pinch" na touchpadzie — Chrome/Edge/Firefox wysyłają go jako
 * wheel z ctrlKey) zmienia zoom MAPY zamiast zoomu całej strony przeglądarki.
 *
 * Zoom idzie po drabince ze store'a (krok = jeden szczebel), więc delty kółka zbieramy do
 * progu: jeden „ząbek" myszy (~100 px) = jeden krok, drobne delty touchpada sumują się.
 * Punkt planszy pod kursorem zostaje pod kursorem: zapamiętujemy go w jednostkach planszy
 * przed zmianą i po renderze z nowym zoomem przewijamy kontener tak, by wrócił na miejsce.
 * `clearance` to stały (nieskalowany) margines planszy w kontenerze.
 */
const WHEEL_STEP = 100;

type Anchor = { boardX: number; boardY: number; offsetX: number; offsetY: number };

export function useWheelZoom({
  containerRef,
  zoom,
  onZoomIn,
  onZoomOut,
  clearance = 0,
  enabled = true,
}: {
  containerRef: RefObject<HTMLElement | null>;
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  clearance?: number;
  enabled?: boolean;
}) {
  const anchor = useRef<Anchor | null>(null);
  const zoomRef = useRef(zoom);
  zoomRef.current = zoom;
  const handlers = useRef({ onZoomIn, onZoomOut });
  handlers.current = { onZoomIn, onZoomOut };

  useEffect(() => {
    const area = containerRef.current;
    if (!area || !enabled) return;
    let accumulated = 0;

    function handleWheel(event: WheelEvent) {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault(); // bez tego przeglądarka zoomuje całą stronę
      // deltaMode 1 = linie (Firefox): przeliczamy na piksele, żeby próg był wspólny.
      accumulated += event.deltaMode === 1 ? event.deltaY * 33 : event.deltaY;
      if (Math.abs(accumulated) < WHEEL_STEP) return;
      const zoomIn = accumulated < 0;
      accumulated = 0;
      const rect = area!.getBoundingClientRect();
      const offsetX = event.clientX - rect.left;
      const offsetY = event.clientY - rect.top;
      const current = zoomRef.current;
      anchor.current = {
        boardX: (area!.scrollLeft + offsetX - clearance) / current,
        boardY: (area!.scrollTop + offsetY - clearance) / current,
        offsetX,
        offsetY,
      };
      if (zoomIn) handlers.current.onZoomIn();
      else handlers.current.onZoomOut();
    }

    area.addEventListener("wheel", handleWheel, { passive: false });
    return () => area.removeEventListener("wheel", handleWheel);
  }, [containerRef, clearance, enabled]);

  useLayoutEffect(() => {
    const area = containerRef.current;
    const point = anchor.current;
    if (!area || !point) return;
    anchor.current = null;
    area.scrollLeft = point.boardX * zoom + clearance - point.offsetX;
    area.scrollTop = point.boardY * zoom + clearance - point.offsetY;
  }, [containerRef, zoom, clearance]);
}
