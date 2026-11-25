import { useEffect, useRef, useState } from "react";

/**
 * Odliczanie okna reakcji o stałej długości (RULES.md 54.11) — wspólne dla pauzy ochronnej i okna
 * Sabotage. Czas liczony lokalnie od chwili, gdy okno pojawiło się u nas (bez zgadywania różnicy
 * zegarów); długość może urosnąć w trakcie („More time”), więc odczytujemy ją z refa. Po zerze
 * klient raz prosi serwer o zwolnienie — serwer i tak sprawdza własny zegar.
 *
 * @param key Klucz okna (nowy klucz = nowe odliczanie); `null` = brak okna.
 * @param total Bieżąca długość okna w s (z przedłużeniami).
 * @param onExpire Prośba o zwolnienie po upływie czasu.
 * @returns Pozostałe sekundy (albo `null`, gdy brak okna).
 */
export function useWindowCountdown(
  key: string | null,
  total: number,
  onExpire: () => void,
  /** Okno zatrzymane (ktoś zagrywa Sabotage): czas stoi i nie ma zwolnienia. */
  paused = false,
): number | null {
  const [left, setLeft] = useState<number | null>(null);
  const totalRef = useRef(total);
  const expireRef = useRef(onExpire);
  const pausedRef = useRef(paused);

  useEffect(() => {
    totalRef.current = total;
    expireRef.current = onExpire;
    pausedRef.current = paused;
  });

  useEffect(() => {
    if (!key) {
      setLeft(null);
      return;
    }
    let elapsedMs = 0;
    let last = Date.now();
    let released = false;
    const tick = () => {
      const now = Date.now();
      if (!pausedRef.current) elapsedMs += now - last;
      last = now;
      const elapsed = Math.floor(elapsedMs / 1000);
      const remaining = Math.max(0, totalRef.current - elapsed);
      setLeft(remaining);
      if (remaining === 0 && !released && !pausedRef.current) {
        released = true;
        expireRef.current();
      }
    };
    tick();
    const timer = window.setInterval(tick, 250);
    return () => window.clearInterval(timer);
  }, [key]);

  return left;
}
