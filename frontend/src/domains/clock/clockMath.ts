// Czysta logika zegara szachowego (RULES.md 58) — formatowanie i doliczanie upływu.
// Bez Reacta, żeby dało się ją przetestować jednostkowo.

import type { ChessClockPlayer, ChessClockView } from "@/entities/data/types";

/** Czas jako `m:ss` albo `h:mm:ss`; ujemny z minusem (przekroczony limit). */
export function formatClock(ms: number): string {
  const negative = ms < 0;
  // Pozostały czas zaokrąglamy W GÓRĘ (jak zegar szachowy: 0:01 do ostatniej chwili).
  const totalSeconds = Math.ceil(Math.abs(ms) / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const ss = String(seconds).padStart(2, "0");
  const body =
    hours > 0
      ? `${hours}:${String(minutes).padStart(2, "0")}:${ss}`
      : `${minutes}:${ss}`;
  return negative && totalSeconds > 0 ? `−${body}` : body;
}

/** Czas tury liczony w górę (zaokrąglony w dół, jak stoper). */
export function formatElapsed(ms: number): string {
  return formatClock(Math.floor(Math.max(0, ms) / 1000) * 1000);
}

/**
 * Zegar gracza po upływie `deltaMs` od odbioru dokumentu: tylko gracz z `running`
 * traci czas i nabija czas tury. Wartości z serwera są aktualne na chwilę budowy.
 */
export function livePlayer(player: ChessClockPlayer, deltaMs: number): ChessClockPlayer {
  if (!player.running || deltaMs <= 0) return player;
  return {
    ...player,
    remainingMs: player.remainingMs - deltaMs,
    turnMs: player.turnMs + deltaMs,
  };
}

/** Czy cokolwiek w zegarze tyka (wtedy UI odświeża się w pętli). */
export function isTicking(view: ChessClockView | null | undefined): boolean {
  return !!view && !view.paused && view.players.some((p) => p.running);
}

/** Próg ostrzeżenia: mniej niż 10% puli albo mniej niż minuta. */
export function isLow(player: ChessClockPlayer, initialMs: number): boolean {
  return player.remainingMs < Math.max(60_000, initialMs * 0.1);
}
