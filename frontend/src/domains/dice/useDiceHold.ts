import { useEffect, useRef, useState } from "react";
import { useDiceGate } from "./diceGate";

/**
 * Wstrzymuje SKUTKI rzutu w widoku do chwili, gdy kości i strzały skończą animację.
 *
 * Silnik rzuca i nakłada straty w jednym żądaniu, więc świeży widok od razu nie ma zniszczonych
 * jednostek, a kości na stole jeszcze się toczą. Gdy w dzienniku (``log``) pojawia się nowy wpis,
 * hook przez ``holdMsOf(...)`` ms zwraca widok z jednostkami sprzed rzutu (``freeze`` składa go
 * z żywego widoku i poprzedniego). Dziennik i reszta pozostają żywe, więc animacja kości startuje
 * normalnie. ``holdMsOf`` zwraca 0 = bez wstrzymania.
 */
export function useDiceHold<V extends { log: unknown[] }>(
  view: V | undefined,
  holdMsOf: (live: V, fromLen: number) => number,
  freeze: (live: V, before: V) => V,
): { view: V | undefined; holding: boolean } {
  const lenRef = useRef<number | null>(null);
  const shownRef = useRef<V | undefined>(view);
  const holdRef = useRef<{ before: V; until: number } | null>(null);
  const [, rerender] = useState(0);

  if (view) {
    const len = view.log.length;
    if (lenRef.current === null || len < lenRef.current) {
      // Pierwszy odczyt (nie animuj historii) albo cofnięcie (Undo).
      lenRef.current = len;
      holdRef.current = null;
    } else if (len > lenRef.current) {
      const fromLen = lenRef.current;
      lenRef.current = len;
      const ms = holdMsOf(view, fromLen);
      const before = shownRef.current;
      if (ms > 0 && before) holdRef.current = { before, until: Date.now() + ms };
    }
  }

  const hold = holdRef.current;
  const holding = hold !== null && Date.now() < hold.until;
  const shown = view && holding && hold ? freeze(view, hold.before) : view;
  shownRef.current = shown;

  useEffect(() => {
    const h = holdRef.current;
    if (!h) return;
    const left = h.until - Date.now();
    // Reszta UI (oferty, limity, powiadomienia) czeka na kości (``diceGate``).
    if (left > 0) useDiceGate.getState().hold(left);
    const done = () => {
      if (holdRef.current === h) holdRef.current = null;
      rerender((n) => n + 1);
    };
    if (left <= 0) {
      done();
      return;
    }
    const t = window.setTimeout(done, left);
    return () => window.clearTimeout(t);
  });

  return { view: shown, holding };
}
