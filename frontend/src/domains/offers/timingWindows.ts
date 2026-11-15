/*
 * Cykl życia okien czasowych w UI (RULES.md 54.9): okno, które zniknęło między odświeżeniami,
 * zostaje chwilę na ekranie jako „Closed”, żeby gracze widzieli, że gra z niego wyszła.
 */

/** Jak długo pokazujemy okno zamknięte / kartę, której okno minęło (ms). */
export const CLOSED_NOTICE_MS = 6000;

/** Element, który zniknął, z chwilą, do której go pokazujemy. */
export type Gone<T> = { item: T; until: number };

/** Elementy z `prev`, których nie ma w `next` (po kluczu), w kolejności `prev`. */
export function goneSince<T>(prev: T[], next: T[], key: (item: T) => string): T[] {
  const live = new Set(next.map(key));
  return prev.filter((item) => !live.has(key(item)));
}

/**
 * Nowa lista „zniknętych”: bez tych, które wróciły (`open`) albo wygasły (`now`), plus świeżo
 * zniknięte (`justGone`, ważne do `now + CLOSED_NOTICE_MS`). Bez zmian zwraca TĘ SAMĄ tablicę.
 */
export function mergeGone<T>(
  gone: Gone<T>[],
  justGone: T[],
  open: T[],
  key: (item: T) => string,
  now: number,
): Gone<T>[] {
  const live = new Set(open.map(key));
  const kept = gone.filter((g) => !live.has(key(g.item)) && g.until > now);
  const known = new Set(kept.map((g) => key(g.item)));
  const added = justGone
    .filter((item) => !known.has(key(item)))
    .map((item) => ({ item, until: now + CLOSED_NOTICE_MS }));
  if (added.length === 0 && kept.length === gone.length) return gone;
  return [...kept, ...added];
}
