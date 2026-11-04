// Dane graczy dla planszy otwierającej grę (`GameIntro`).
//
// Frakcje losowe są dobierane PO STRONIE BACKENDU, więc po `/game/new` pytamy o
// faktyczny stan gry (`GET /state`) i z niego bierzemy: kto (nazwa, człowiek/bot, kolor)
// gra którą frakcją. Kolejność = kolejność zasiadania przy stole (`seating_order`).
// Plansza jest tylko oprawą — każdy błąd tutaj kończy się pominięciem intra, nigdy
// blokadą wejścia do gry.

import { fetchJson } from "@/api/fetchJson";
import type { FactionInfo } from "@/api/useNewGame";

/** Jeden uczestnik gry pokazany na planszy otwierającej. */
export interface IntroPlayer {
  id: string;
  /** Nazwa wyświetlana gracza. */
  name: string;
  faction: FactionInfo;
  /** Kolor gracza (id ze zbioru `AVAILABLE_COLORS`) albo `null`. */
  color: string | null;
  isBot: boolean;
  /** Poziom trudności bota (tylko `isBot`). */
  difficulty: string | null;
}

/** Fragment `PlayerState` z backendu, który jest tu potrzebny. */
interface RawPlayer {
  player_id: string;
  display_name: string;
  control_type: string;
  difficulty: string | null;
  faction: string | null;
  color: string | null;
}

interface RawStateEnvelope {
  state: {
    players: Record<string, RawPlayer>;
    seating_order: string[];
  };
}

/**
 * Pobiera uczestników świeżo utworzonej gry w kolejności zasiadania. Gracze bez
 * rozpoznanej frakcji są pomijani. Rzuca przy błędzie HTTP (wywołujący to łapie).
 */
export async function loadIntroPlayers(
  factionById: Map<string, FactionInfo>,
): Promise<IntroPlayer[]> {
  const envelope = await fetchJson<RawStateEnvelope>("/bot/state", "game state");
  const { players, seating_order: seating } = envelope.state;
  // Kolejność przy stole; gracze spoza listy (nie powinno się zdarzyć) idą na koniec.
  const ids = [
    ...seating.filter((id) => id in players),
    ...Object.keys(players).filter((id) => !seating.includes(id)),
  ];

  const result: IntroPlayer[] = [];
  for (const id of ids) {
    const raw = players[id];
    const faction = raw.faction ? factionById.get(raw.faction) : undefined;
    if (!faction) continue;
    result.push({
      id,
      name: raw.display_name || id,
      faction,
      color: raw.color,
      isBot: raw.control_type === "BOT",
      difficulty: raw.difficulty,
    });
  }
  return result;
}
