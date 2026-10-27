import { useCallback, useRef, useState } from "react";
import { useAppStore } from "@/state/appStore";
import { useBoardEditor } from "@/api/useBoardEditor";

/**
 * Drag-and-drop przeciągania jednostek na mapie (God-Mode, bez reguł).
 *
 * Mapa przewija się biblioteką ``dragscroll`` (pan na natywnym scrollerze), więc
 * każdy ``pointerdown`` + ruch nad planszą normalnie PRZEWIJA. Dlatego start dragu
 * jednostki przejmujemy na samym sprite'cie: ``setPointerCapture`` przykleja kolejne
 * zdarzenia do elementu jednostki, a ``stopPropagation``/``preventDefault`` nie daje
 * panowi przejąć gestu. Dopiero po przekroczeniu progu ruchu (``DRAG_THRESHOLD``)
 * uznajemy to za przeciąganie — krótszy ruch zostaje zwykłym klikiem (dossier).
 *
 * Cel upuszczenia wykrywamy z DOM pod kursorem (``elementFromPoint``): kafelek ma
 * ``id="tile-<pozycja>"``, planeta ``data-search-key="planet:<id>"``. Strefa docelowa
 * to nazwa planety albo ``"space"`` (orbita). Po upuszczeniu na inną strefę otwieramy
 * pytanie „ile przenieść" (``beginUnitDrop``) dla stosów >1; pojedynczą sztukę
 * przenosimy od razu.
 */

// Ruch (px ekranu) odróżniający przeciąganie od kliknięcia. Spójny z progiem
// pan-vs-klik w SystemHexTarget (tam 6px) — tu nieco większy, bo start dragu musi
// być zdecydowany, żeby nie wyłączać otwierania dossier przy drobnym drgnięciu.
const DRAG_THRESHOLD = 8;

/** Dane przeciąganej jednostki (skąd, co, ile, czyja). */
export type UnitDragData = {
  fromPosition: string;
  fromZone: string; // "space" albo ID planety
  faction: string;
  asyncId: string;
  count: number;
  /** URL sprite'a do „ducha" podążającego za kursorem (opcjonalny). */
  imageUrl?: string | null;
};

/** Pozycja i dane „ducha" przeciąganej jednostki (render w ``UnitDragGhost``). */
export type DragGhost = {
  x: number;
  y: number;
  asyncId: string;
  count: number;
  imageUrl?: string | null;
};

type DropZone = { position: string; zone: string; label: string } | null;

/** Znajduje strefę docelową (kafelek + planeta/orbita) pod punktem ekranu. */
function dropZoneAt(clientX: number, clientY: number): DropZone {
  const el = document.elementFromPoint(clientX, clientY);
  if (!el) return null;
  const tile = el.closest<HTMLElement>('[id^="tile-"]');
  if (!tile) return null;
  const position = tile.id.slice("tile-".length);
  // Planeta pod kursorem? Koła planet są wyżej niż hex-target i niosą search-key.
  const planetEl = el.closest<HTMLElement>('[data-search-key^="planet:"]');
  if (planetEl) {
    const planetId = planetEl
      .getAttribute("data-search-key")!
      .slice("planet:".length);
    return { position, zone: planetId, label: planetId };
  }
  return { position, zone: "space", label: "Orbita" };
}

export function useUnitDrag() {
  const beginUnitDrop = useAppStore((s) => s.beginUnitDrop);
  const { moveUnit } = useBoardEditor();
  const [ghost, setGhost] = useState<DragGhost | null>(null);

  // Stan jednego aktywnego przeciągania (ref — bez re-renderów na pointermove).
  const drag = useRef<{
    data: UnitDragData;
    startX: number;
    startY: number;
    active: boolean; // czy przekroczono próg (realne przeciąganie)
  } | null>(null);
  // Czy właśnie zakończyliśmy realne przeciąganie — blokuje klik, który
  // przeglądarka może wygenerować po pointerup (inaczej drag otwierałby dossier).
  const justDragged = useRef(false);

  const onPointerDown = useCallback(
    (data: UnitDragData, event: React.PointerEvent) => {
      // Tylko lewy przycisk / dotyk; prawy zostaw menu kontekstowemu.
      if (event.button !== 0) return;
      const target = event.currentTarget as HTMLElement;
      target.setPointerCapture?.(event.pointerId);
      drag.current = {
        data,
        startX: event.clientX,
        startY: event.clientY,
        active: false,
      };
    },
    [],
  );

  const onPointerMove = useCallback((event: React.PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    const travel = Math.hypot(
      event.clientX - d.startX,
      event.clientY - d.startY,
    );
    if (!d.active && travel < DRAG_THRESHOLD) return;
    // Przekroczono próg → to przeciąganie. Blokuj pan i pokaż ducha.
    d.active = true;
    event.preventDefault();
    event.stopPropagation();
    setGhost({
      x: event.clientX,
      y: event.clientY,
      asyncId: d.data.asyncId,
      count: d.data.count,
      imageUrl: d.data.imageUrl,
    });
  }, []);

  const onPointerUp = useCallback(
    (event: React.PointerEvent) => {
      const d = drag.current;
      drag.current = null;
      setGhost(null);
      // Nie było realnego przeciągania → zostaw to klikowi (dossier/select).
      if (!d || !d.active) return;
      event.stopPropagation();
      // Zablokuj klik wygenerowany przez ten gest (dossier nie ma się otworzyć).
      justDragged.current = true;
      const target = dropZoneAt(event.clientX, event.clientY);
      if (!target) return;
      const { data } = d;
      // Upuszczenie w to samo miejsce = brak ruchu.
      if (target.position === data.fromPosition && target.zone === data.fromZone) {
        return;
      }
      // Jedna sztuka → przenieś od razu; stos → zapytaj „ile przenieść".
      if (data.count <= 1) {
        void moveUnit({
          fromPosition: data.fromPosition,
          fromZone: data.fromZone,
          toPosition: target.position,
          toZone: target.zone,
          faction: data.faction,
          asyncId: data.asyncId,
          count: 1,
        });
        return;
      }
      beginUnitDrop({
        fromPosition: data.fromPosition,
        fromZone: data.fromZone,
        toPosition: target.position,
        toZone: target.zone,
        toLabel: target.label,
        faction: data.faction,
        asyncId: data.asyncId,
        available: data.count,
      });
    },
    [beginUnitDrop, moveUnit],
  );

  const onPointerCancel = useCallback(() => {
    drag.current = null;
    setGhost(null);
  }, []);

  // Przechwytuje i gasi klik bezpośrednio po udanym przeciąganiu (jednorazowo).
  const onClickCapture = useCallback((event: React.MouseEvent) => {
    if (justDragged.current) {
      justDragged.current = false;
      event.preventDefault();
      event.stopPropagation();
    }
  }, []);

  return {
    ghost,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onPointerCancel,
    onClickCapture,
  };
}
