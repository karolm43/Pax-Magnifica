import { useEffect, useState } from "react";

/*
 * STREFA DECYZJI (`docs/PLAN_OKNA_DECYZJI.md`, U3): okna, w których gracz właśnie decyduje, oznaczają
 * swój korzeń atrybutem w DOM, a reszta interfejsu im ustępuje (zasada 5: „Nic nie zasłania okna
 * decyzji”). Atrybut zamiast wspólnego stanu - okna żyją w różnych domenach (oferty, faza statusu,
 * Rada, karty strategii), a ten sam wzorzec ma już `data-fullscreen-overlay`.
 *
 * - `data-decision-zone`  - każde okno decyzji (rama `DecisionFrame`, panel fazy statusu, Rada,
 *   okno karty strategii). Dymki mapy go nie zasłaniają, dok ręki zwija się, gdy na nie wchodzi,
 *   baner okna reakcji przenosi się na górę ekranu.
 * - `data-phase-window`   - okno FAZY (status, agenda, karta strategii). Gdy jest otwarte, centrum
 *   „Decisions” nie otwiera drugiego okna: zwija się do pastylki z licznikiem „+N”.
 */
export const DECISION_ZONE_SELECTOR = "[data-decision-zone]";
export const PHASE_WINDOW_SELECTOR = "[data-phase-window]";
export const FULLSCREEN_OVERLAY_SELECTOR = "[data-fullscreen-overlay]";

/** Atrybuty korzenia okna decyzji (rozwijane w JSX: `<div {...DECISION_ZONE}>`). */
export const DECISION_ZONE = { "data-decision-zone": "" } as const;
/** Okno fazy jest zawsze też oknem decyzji. */
export const PHASE_WINDOW = { "data-phase-window": "", "data-decision-zone": "" } as const;

/** Czy w dokumencie jest element pasujący do selektora (śledzi montowanie i atrybuty). */
export function useDomPresence(selector: string): boolean {
  const [present, setPresent] = useState(false);
  useEffect(() => {
    const check = () => setPresent(document.querySelector(selector) !== null);
    check();
    const observer = new MutationObserver(check);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["data-decision-zone", "data-phase-window", "data-fullscreen-overlay"],
    });
    return () => observer.disconnect();
  }, [selector]);
  return present;
}

export type Box = { left: number; top: number; right: number; bottom: number };

/** Czy dwa prostokąty (współrzędne ekranu) mają część wspólną o niezerowym polu. */
export function boxesOverlap(a: Box, b: Box): boolean {
  return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
}

/**
 * Czy jakieś okno decyzji nachodzi na prostokąt `box` (pomija elementy wewnątrz `ignore`, np.
 * sam dok ręki). Okna z zerowym rozmiarem (niewyrenderowane, `display: contents`) się nie liczą.
 */
export function decisionZoneOverlaps(box: Box, ignore?: Element | null): boolean {
  for (const el of document.querySelectorAll(DECISION_ZONE_SELECTOR)) {
    if (ignore && ignore.contains(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (boxesOverlap(box, r)) return true;
  }
  return false;
}
