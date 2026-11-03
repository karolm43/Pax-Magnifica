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

/**
 * Gracz w żądaniu nowej gry; pola opcjonalne przydziela backend automatycznie.
 *
 * Kontrakt zgodny z `NewGamePlayer` z backendu (design.md §5): `faction_id`
 * pominięty → backend losuje frakcję bez powtórzeń (R8.5); `name` pusty → auto-nazwa
 * (R7.3); `control_type` domyślnie "HUMAN"; `difficulty` tylko dla botów (R10.3).
 */
export type NewGamePlayer = {
  // Pominięty = losowa frakcja (dobierana przez backend bez powtórzeń).
  faction_id?: string;
  player_id?: string;
  // Nazwa wyświetlana; pusta/pominięta → backend nada automatyczną.
  name?: string;
  color?: string;
  // Typ sterowania: "HUMAN" (domyślny po stronie backendu) lub "BOT".
  control_type?: string;
  // Poziom trudności bota; wysyłany tylko gdy control_type === "BOT".
  difficulty?: string;
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

/**
 * Konfiguracja silnika wystawiana na potrzeby setupu (GET /engine/config).
 *
 * Niesie dozwolony zbiór poziomów trudności bota (R10.2). Front NIE trzyma
 * własnej kopii tej listy — zbiór jest konfiguracją backendu (`engine_config.json`
 * → `valid_difficulties`, ⚠️ ZAŁOŻENIE, patrz docs/RULES.md 30) czytaną przez
 * `StaticDataRegistry`.
 */
export type EngineConfigInfo = {
  valid_difficulties: string[];
};

/** Pobiera konfigurację silnika (dozwolony zbiór trudności bota). */
export function useEngineConfig() {
  return useQuery<EngineConfigInfo>({
    queryKey: ["engineConfig"],
    queryFn: () =>
      fetchJson<EngineConfigInfo>(`${BOT_ROOT}/engine/config`, "engine config"),
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
