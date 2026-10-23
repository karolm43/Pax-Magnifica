import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";

/** Frakcja do wyboru na ekranie startowym (z backendu Custodian Engine). */
export type FactionInfo = {
  id: string;
  name: string;
  home_system: string | null;
  home_planets: string[];
  starting_fleet: string | null;
  preferred_colours: string[];
  // Wybór technologii startowej: gracz wybiera `starting_tech_amount` spośród
  // `starting_tech_options`. Gdy amount == 0, frakcja ma stałe technologie.
  starting_tech_options: string[];
  starting_tech_amount: number;
};

/** Gracz w żądaniu nowej gry; pola opcjonalne przydziela backend automatycznie. */
export type NewGamePlayer = {
  faction_id: string;
  player_id?: string;
  color?: string;
  home_position?: string;
  // Wybrane technologie startowe (dla frakcji z wyborem, np. Winnu/Argent).
  starting_tech?: string[];
};

export type NewGameRequest = {
  players: NewGamePlayer[];
  map_string?: string;
  include_center?: boolean;
};

/*
 * Endpointy Custodian Engine żyją w KORZENIU backendu (/factions, /game/new),
 * nie pod /api. Proxy Vite mapuje "/bot/<x>" -> "/<x>" na backendzie, więc
 * bazą jest samo "/bot" (NIE config.api.botApiUrl = "/bot/api").
 */
const BOT_ROOT = "/bot";

/** Pobiera listę frakcji do ekranu startowego (GET /factions). */
export function useFactions() {
  return useQuery<FactionInfo[]>({
    queryKey: ["factions"],
    queryFn: () => fetchJson<FactionInfo[]>(`${BOT_ROOT}/factions`, "factions"),
    staleTime: Infinity,
  });
}

/** Tworzy nową grę jednym żądaniem (POST /game/new). Rzuca przy błędzie HTTP. */
export async function createNewGame(request: NewGameRequest): Promise<void> {
  const response = await fetch(`${BOT_ROOT}/game/new`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(
      `Nie udało się utworzyć gry (${response.status}). ${detail}`.trim()
    );
  }
}
