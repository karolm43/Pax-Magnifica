import { useEffect, useState } from "react";
import { create } from "zustand";

/**
 * BRAMKA „KOŚCI W LOCIE”: dopóki kości toczą się po stole (pole bitwy, inwazja, wspólna scena
 * kości), nic poza nimi nie może zdradzić wyniku - okna decyzji (np. „po wygranej walce”),
 * limit pojemności / puli floty, powiadomienia Activity, ekran zwycięstwa czekają, aż kości
 * wylądują. Rzut ogłaszają ``useDiceHold`` (bitwa, inwazja) i ``useDiceStage.throwDice``.
 */
type Gate = {
  /** Do kiedy (``Date.now()``) trwa rzut. */
  until: number;
  /** Rzut trwa jeszcze ``ms`` od teraz (dłuższy wygrywa). */
  hold: (ms: number) => void;
};

export const useDiceGate = create<Gate>((set, get) => ({
  until: 0,
  hold: (ms) => {
    const until = Date.now() + Math.max(0, ms);
    if (until > get().until) set({ until });
  },
}));

/**
 * Nowa treść (np. oferta po walce) przychodzi czasem odrobinę PRZED danymi rzutu (osobne
 * zapytanie o pole bitwy) - tyle czekamy, zanim uznamy, że rzutu nie ma.
 */
export const DICE_GRACE_MS = 350;

/**
 * Czy wolno już pokazać treść ``contentKey`` (pusty klucz = nic do pokazania = true).
 * Treść pojawiająca się na nowo czeka ``DICE_GRACE_MS`` i do końca trwającego rzutu; treść już
 * widoczna nie znika przy kolejnym rzucie (bez migania).
 */
export function useAfterDice(contentKey: string, graceMs = DICE_GRACE_MS): boolean {
  const until = useDiceGate((s) => s.until);
  const [seen, setSeen] = useState<{ key: string; at: number; shown: boolean }>({
    key: contentKey,
    at: 0,
    shown: contentKey !== "",
  });
  let current = seen;
  if (seen.key !== contentKey) {
    // Nowa treść: od teraz czeka (stan liczony w renderze - wzorzec „derived state”).
    current = { key: contentKey, at: Date.now(), shown: false };
    setSeen(current);
  }
  const openAt = current.shown ? 0 : Math.max(until, current.at + graceMs);
  const left = openAt - Date.now();
  const [, tick] = useState(0);
  useEffect(() => {
    const ms = openAt - Date.now();
    if (ms <= 0) return;
    const t = window.setTimeout(() => tick((n) => n + 1), ms);
    return () => window.clearTimeout(t);
  }, [openAt]);
  const open = contentKey === "" || left <= 0;
  useEffect(() => {
    if (open && !current.shown && contentKey !== "") {
      setSeen((s) => (s.key === contentKey ? { ...s, shown: true } : s));
    }
  }, [open, current.shown, contentKey]);
  return open;
}
