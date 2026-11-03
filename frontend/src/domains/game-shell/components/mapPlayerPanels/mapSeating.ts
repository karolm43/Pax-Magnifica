// Czysta logika kolejności paneli graczy w widoku mapy (Map_View, R13).
//
// Web-data niesie w `gameState`:
//   - `activePlayer` — KOLOR aktywnego gracza (albo null),
//   - `seatingOrder` — lista KOLORÓW w kolejności zasiadania przy stole.
//
// Zadanie 14.1 wymaga, by panele nieaktywnych układały się w jeden pionowy stos
// „w kolejności zasiadania zaczynając od gracza po lewej stronie aktywnego"
// (R13.2). „Po lewej" = następny gracz zgodnie z kierunkiem zasiadania, czyli
// wpis występujący bezpośrednio po aktywnym w `seatingOrder`. Stąd rotujemy listę
// tak, aby zaczynała się od gracza następującego po aktywnym, a aktywnego z niej
// usuwamy (ma własny, powiększony panel).
//
// Funkcje są czyste i niezależne od Reacta — dzięki temu test (zadanie 14.2) może
// zweryfikować kolejność bez renderowania komponentu.

import type { PlayerData } from "@/entities/data/types";

/**
 * Zwraca kolory graczy nieaktywnych w kolejności stosu: od gracza po lewej
 * aktywnego, dalej zgodnie z kierunkiem zasiadania, z pominięciem aktywnego.
 *
 * Reguły brzegowe:
 *  - gdy `activePlayer` jest null albo nie występuje w `seatingOrder`, zwracamy
 *    `seatingOrder` bez rotacji (nie mamy od czego liczyć „lewej strony");
 *  - gdy `seatingOrder` jest puste, zwracamy pustą listę.
 */
export function inactiveSeatingOrder(
  seatingOrder: readonly string[],
  activePlayer: string | null | undefined,
): string[] {
  if (seatingOrder.length === 0) return [];

  const activeIndex =
    activePlayer != null ? seatingOrder.indexOf(activePlayer) : -1;

  // Brak aktywnego w kolejności → zwróć kolejność bez rotacji (ale odfiltruj
  // ewentualnego aktywnego, gdyby pojawił się mimo braku indeksu — tu nie).
  if (activeIndex === -1) {
    return seatingOrder.filter((color) => color !== activePlayer);
  }

  const count = seatingOrder.length;
  const ordered: string[] = [];
  // Zaczynamy od gracza PO aktywnym (po lewej) i obchodzimy stół w kółko,
  // pomijając samego aktywnego.
  for (let step = 1; step < count; step += 1) {
    ordered.push(seatingOrder[(activeIndex + step) % count]);
  }
  return ordered;
}

/**
 * Układa dane graczy (`PlayerData[]`) w kolejności stosu nieaktywnych wyznaczonej
 * przez {@link inactiveSeatingOrder}. Gracze bez wpisu w `seatingOrder` (np. gdy
 * kolejność zasiadania jest niepełna) trafiają na koniec, zachowując swoją
 * pierwotną kolejność z `playerData`. Aktywny gracz jest zawsze pomijany.
 */
export function orderInactivePlayers(
  playerData: readonly PlayerData[],
  seatingOrder: readonly string[],
  activePlayer: string | null | undefined,
): PlayerData[] {
  const byColor = new Map<string, PlayerData>();
  for (const player of playerData) {
    if (!byColor.has(player.color)) byColor.set(player.color, player);
  }

  const order = inactiveSeatingOrder(seatingOrder, activePlayer);
  const used = new Set<string>();
  const result: PlayerData[] = [];

  for (const color of order) {
    const player = byColor.get(color);
    if (player && color !== activePlayer) {
      result.push(player);
      used.add(color);
    }
  }

  // Gracze spoza `seatingOrder` (ale nie aktywny) — na koniec, w kolejności z
  // `playerData`, żeby nie zgubić żadnego panelu.
  for (const player of playerData) {
    if (player.color === activePlayer) continue;
    if (used.has(player.color)) continue;
    result.push(player);
    used.add(player.color);
  }

  return result;
}

/**
 * Wyszukuje aktywnego gracza. Preferuje dopasowanie po `activePlayer` (kolorze)
 * z `gameState`; w razie braku dopasowania sięga po flagę `player.active`
 * z web-data. Zwraca `null`, gdy aktywnego nie da się ustalić.
 */
export function findActivePlayer(
  playerData: readonly PlayerData[],
  activePlayer: string | null | undefined,
): PlayerData | null {
  if (activePlayer != null) {
    const byColor = playerData.find((player) => player.color === activePlayer);
    if (byColor) return byColor;
  }
  return playerData.find((player) => player.active) ?? null;
}
