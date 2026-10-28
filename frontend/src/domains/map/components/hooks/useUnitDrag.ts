import { useCallback, useEffect, useRef, useState } from "react";
import { useAppStore } from "@/state/appStore";
import { useBoardEditor } from "@/api/useBoardEditor";
import { isShipUnit } from "../UnitStack/unitType";

/**
 * Drag-and-drop przeciągania jednostek na mapie (God-Mode, bez reguł).
 *
 * Dwa źródła tarcia, oba rozwiązane tutaj:
 *
 * 1. **Pan mapy łapie gest.** Mapa przewija się biblioteką ``dragscroll``, która
 *    binduje natywny ``mousedown`` (bubbling) na kontenerze ``.dragscroll`` i na nim
 *    startuje przewijanie. React ``stopPropagation`` nie zatrzymuje tego natywnie,
 *    dlatego podpinamy WŁASNE natywne listenery w fazie CAPTURE na elemencie sprite'a
 *    (``mousedown``/``touchstart``) i wołamy ``stopPropagation`` — zdarzenie nie dociera
 *    do kontenera dragscroll, więc chwytając jednostkę NIE przesuwasz planszy.
 *
 * 2. **Tooltip zasłania w trakcie.** Gdy ruch przekroczy próg (``DRAG_THRESHOLD``),
 *    ustawiamy w store ``isDraggingUnit`` — tooltip jednostki nie pokazuje się i jest
 *    chowany na czas przeciągania (patrz useTabsAndTooltips).
 *
 * Krótszy ruch niż próg zostaje zwykłym klikiem (dossier). Cel upuszczenia czytamy z
 * DOM pod kursorem (``elementFromPoint``): kafelek ``id="tile-<pozycja>"``, planeta
 * ``data-search-key="planet:<id>"``, inaczej orbita (``"space"``). Po upuszczeniu na inną
 * strefę: stos >1 → pytanie „ile przenieść" (``beginUnitDrop``), 1 szt. → ruch od razu.
 */

// Ruch (px ekranu) odróżniający przeciąganie od kliknięcia. Spójny z progiem
// pan-vs-klik w SystemHexTarget (tam 6px) — tu nieco większy, by start dragu był
// zdecydowany i drobne drgnięcie nie blokowało otwarcia dossier.
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

type RawZone = { position: string; zone: string; label: string } | null;

/** Surowa strefa pod kursorem (kafelek + planeta/orbita), bez reguł umiejscowienia. */
function rawZoneAt(clientX: number, clientY: number): RawZone {
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

/** Rozstrzygnięty cel: strefa po regule umiejscowienia + czy ruch dozwolony. */
type ResolvedTarget = {
  position: string;
  zone: string;
  label: string;
  valid: boolean;
} | null;

/**
 * Nakłada regułę umiejscowienia (RULES.md 26) na surowy cel pod kursorem:
 * - STATEK upuszczony na planetę → trafia w ORBITĘ tego samego kafelka (gracz wskazał
 *   system) — wygodne mapowanie gestu, zawsze dozwolone.
 * - SIŁA NAZIEMNA/STRUKTURA upuszczona na orbitę → brak sensownej planety-celu →
 *   niedozwolone (``valid=false``), front nie wykona ruchu.
 * - Upuszczenie w tę samą strefę co źródło → niedozwolone (brak ruchu).
 */
function resolveTarget(
  data: UnitDragData,
  clientX: number,
  clientY: number,
): ResolvedTarget {
  const raw = rawZoneAt(clientX, clientY);
  if (!raw) return null;
  const ship = isShipUnit(data.asyncId);
  let zone = raw.zone;
  let label = raw.label;
  let valid = true;
  if (ship && zone !== "space") {
    // Statek na planetę → orbita tego kafelka.
    zone = "space";
    label = "Orbita";
  } else if (!ship && zone === "space") {
    // Jednostka naziemna/struktura nie może stać w przestrzeni.
    valid = false;
  }
  // Brak ruchu, gdy cel = źródło.
  if (
    valid &&
    raw.position === data.fromPosition &&
    zone === data.fromZone
  ) {
    valid = false;
  }
  return { position: raw.position, zone, label, valid };
}

export function useUnitDrag(data: UnitDragData | null) {
  const beginUnitDrop = useAppStore((s) => s.beginUnitDrop);
  const setDraggingUnit = useAppStore((s) => s.setDraggingUnit);
  const setDragOver = useAppStore((s) => s.setDragOver);
  const { moveUnit } = useBoardEditor();
  const [ghost, setGhost] = useState<DragGhost | null>(null);

  // Najświeższe dane jednostki w ref — natywne listenery nie łapią ich przez domknięcie.
  const dataRef = useRef<UnitDragData | null>(data);
  dataRef.current = data;

  // Stan jednego aktywnego przeciągania (ref — bez re-renderów na mousemove).
  const drag = useRef<{
    startX: number;
    startY: number;
    active: boolean; // czy przekroczono próg (realne przeciąganie)
  } | null>(null);
  // Klik po udanym dragu musi być zgaszony (inaczej otworzyłby dossier).
  const justDragged = useRef(false);
  // Sprzątanie natywnych listenerów sprite'a (ustawiane w dragRef).
  const cleanupRef = useRef<(() => void) | null>(null);

  const endDrag = useCallback(
    (clientX: number, clientY: number, committed: boolean) => {
      const d = drag.current;
      const info = dataRef.current;
      drag.current = null;
      setGhost(null);
      setDraggingUnit(false);
      setDragOver(null);
      document.body.classList.remove("dragging-unit");
      if (!d || !d.active || !committed || !info) return;
      justDragged.current = true;
      const target = resolveTarget(info, clientX, clientY);
      if (!target || !target.valid) return; // niedozwolony cel = brak ruchu
      if (info.count <= 1) {
        void moveUnit({
          fromPosition: info.fromPosition,
          fromZone: info.fromZone,
          toPosition: target.position,
          toZone: target.zone,
          faction: info.faction,
          asyncId: info.asyncId,
          count: 1,
        });
        return;
      }
      beginUnitDrop({
        fromPosition: info.fromPosition,
        fromZone: info.fromZone,
        toPosition: target.position,
        toZone: target.zone,
        toLabel: target.label,
        faction: info.faction,
        asyncId: info.asyncId,
        available: info.count,
      });
    },
    [beginUnitDrop, moveUnit, setDraggingUnit, setDragOver],
  );

  // Globalne listenery ruchu/końca dopięte dopiero po starcie gestu (gdy ``drag`` jest
  // ustawiony). Na window — gest kończy się nawet, gdy kursor zjedzie poza sprite.
  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      const d = drag.current;
      if (!d) return;
      const travel = Math.hypot(e.clientX - d.startX, e.clientY - d.startY);
      if (!d.active && travel < DRAG_THRESHOLD) return;
      if (!d.active) {
        d.active = true;
        setDraggingUnit(true); // chowa tooltip
        // Globalnie wyłącz zaznaczanie tekstu/grafiki na czas gestu — szarpnięcie
        // poza sprite nie zaznacza wtedy sąsiednich kafelków „jak w przeglądarce".
        document.body.classList.add("dragging-unit");
      }
      e.preventDefault();
      const info = dataRef.current;
      if (info) {
        setGhost({
          x: e.clientX,
          y: e.clientY,
          asyncId: info.asyncId,
          count: info.count,
          imageUrl: info.imageUrl,
        });
        // Podświetl kafelek-cel pod kursorem (planszówkowy feedback „tu upuścisz").
        const target = resolveTarget(info, e.clientX, e.clientY);
        setDragOver(
          target
            ? { position: target.position, zone: target.zone, valid: target.valid }
            : null,
        );
      }
    };
    const onUp = (e: PointerEvent) => endDrag(e.clientX, e.clientY, true);
    const onCancel = () => endDrag(0, 0, false);
    window.addEventListener("pointermove", onMove, { passive: false });
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onCancel);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onCancel);
    };
  }, [endDrag, setDraggingUnit, setDragOver]);

  // Callback ref: podpina natywne listenery startu gestu w fazie CAPTURE na sprite'cie.
  // Capture + stopPropagation blokuje dragscroll (pan) ZANIM złapie mousedown.
  const dragRef = useCallback((node: HTMLElement | null) => {
    const cleanup = cleanupRef.current;
    if (cleanup) {
      cleanup();
      cleanupRef.current = null;
    }
    if (!node) return;

    const start = (clientX: number, clientY: number) => {
      drag.current = { startX: clientX, startY: clientY, active: false };
    };
    const onMouseDown = (e: MouseEvent) => {
      if (e.button !== 0 || !dataRef.current) return;
      e.stopPropagation(); // nie pozwól dragscroll zacząć pana
      start(e.clientX, e.clientY);
    };
    const onTouchStart = (e: TouchEvent) => {
      if (!dataRef.current || e.touches.length !== 1) return;
      e.stopPropagation();
      start(e.touches[0].clientX, e.touches[0].clientY);
    };
    // Natywny HTML5 drag obrazka (``<img>`` sprite'a) tworzy „ducha obrazka"
    // przeglądarki i przejmuje gest — tłumimy go twardo.
    const onDragStart = (e: DragEvent) => e.preventDefault();
    node.addEventListener("mousedown", onMouseDown, { capture: true });
    node.addEventListener("touchstart", onTouchStart, {
      capture: true,
      passive: true,
    });
    node.addEventListener("dragstart", onDragStart);
    cleanupRef.current = () => {
      node.removeEventListener("mousedown", onMouseDown, { capture: true });
      node.removeEventListener("touchstart", onTouchStart, { capture: true });
      node.removeEventListener("dragstart", onDragStart);
    };
  }, []);

  // Gasi klik tuż po udanym przeciąganiu (jednorazowo) — dossier się nie otwiera.
  const onClickCapture = useCallback((event: React.MouseEvent) => {
    if (justDragged.current) {
      justDragged.current = false;
      event.preventDefault();
      event.stopPropagation();
    }
  }, []);

  return { ghost, dragRef, onClickCapture };
}
