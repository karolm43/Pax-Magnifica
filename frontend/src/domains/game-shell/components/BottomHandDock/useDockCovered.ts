import { useEffect, useRef, useState } from "react";
import {
  FULLSCREEN_OVERLAY_SELECTOR,
  decisionZoneOverlaps,
} from "@/hooks/useDecisionZone";

/** Wysokość rozwiniętego doku, zanim pierwszy raz go zmierzymy (wachlarz kart + pasek). */
const FALLBACK_OPEN_HEIGHT = 220;

/**
 * Czy dok ręki ma ustąpić (start zwinięty, rozwinięcie tylko chwilowe):
 * - otwarte okno pełnoekranowe (walka, inwazja, Rada, produkcja… - `data-fullscreen-overlay`),
 * - okno decyzji (`data-decision-zone`, U3) wchodzi na miejsce ROZWINIĘTEGO doku.
 *
 * Zasłonięcie liczymy względem wysokości rozwiniętego doku (zapamiętanej, gdy był otwarty), a nie
 * bieżącej - inaczej zwinięcie odsłaniałoby okno i dok rozwijałby się z powrotem (miganie).
 */
export function useDockCovered(dockNode: HTMLElement | null): boolean {
  const [covered, setCovered] = useState(false);
  const openTop = useRef<number | null>(null);

  useEffect(() => {
    let frame = 0;
    const check = () => {
      frame = 0;
      if (document.querySelector(FULLSCREEN_OVERLAY_SELECTOR)) {
        setCovered(true);
        return;
      }
      if (!dockNode) {
        setCovered(false);
        return;
      }
      const rect = dockNode.getBoundingClientRect();
      if (dockNode.hasAttribute("data-open")) openTop.current = rect.top;
      const top = openTop.current ?? window.innerHeight - FALLBACK_OPEN_HEIGHT;
      setCovered(
        decisionZoneOverlaps(
          { left: rect.left, right: rect.right, top, bottom: window.innerHeight },
          dockNode,
        ),
      );
    };
    // Przesuwanie okien zmienia ich `style` w każdej klatce - liczymy najwyżej raz na klatkę.
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(check);
    };
    check();
    const observer = new MutationObserver(schedule);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["style", "data-decision-zone", "data-fullscreen-overlay"],
    });
    window.addEventListener("resize", schedule);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", schedule);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [dockNode]);

  return covered;
}
