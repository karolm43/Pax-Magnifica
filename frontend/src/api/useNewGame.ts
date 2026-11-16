import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import { useSettingsStore } from "@/state/appStore";

/** Frakcja do wyboru na ekranie startowym (z backendu Custodian Engine). */
export type FactionInfo = {
  id: string;
  name: string;
  // Źródło/dodatek frakcji ("base" / "pok" / "thunders_edge" / "codex3" …) — backend.
  // Front grupuje listę wyboru wg dodatków na jego podstawie.
  source: string;
  home_system: string | null;
  home_planets: string[];
  starting_fleet: string | null;
  preferred_colours: string[];
  // Wybór technologii startowej: gracz wybiera `starting_tech_amount` spośród
  // `starting_tech_options`. Gdy amount == 0, frakcja ma stałe technologie.
  starting_tech_options: string[];
  starting_tech_amount: number;
  // Pola bogate do podglądu frakcji (faction summary) — same identyfikatory z rejestru
  // backendu; front rozwiązuje je po swoich danych AsyncTI4 (te same komponenty co
  // panel gracza w grze). Zdolności, technologie frakcyjne, liderzy, jednostki, weksle.
  starting_tech: string[];
  abilities: string[];
  faction_tech: string[];
  leaders: string[];
  units: string[];
  promissory_notes: string[];
  commodities: number;
  complexity: string | null;
  // Przełom frakcji (breakthrough) — identyfikator lub null, gdy frakcja go nie ma.
  breakthrough: string | null;
  // Flota startowa rozbita na pozycje (liczba + typ jednostki). Front rozwiązuje
  // `base_type` na pełną nazwę jednostki (bez surowych kodów typu `cv`/`dd`).
  starting_units: StartingUnit[];
};

/** Jedna pozycja floty startowej frakcji (liczba + typ jednostki). */
export type StartingUnit = {
  base_type: string;
  count: number;
  placement: string;
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
  // Osobowość bota; pominięta → backend losuje.
  personality?: string;
  home_position?: string;
  // Wybrane technologie startowe (dla frakcji z wyborem, np. Winnu/Argent).
  starting_tech?: string[];
};

export type NewGameRequest = {
  players: NewGamePlayer[];
  map_string?: string;
  include_center?: boolean;
  // Talia agend: "standard" (PoK/TE) albo fanowska ("absol", "black_spectrum").
  agenda_deck?: string;
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
 * Pobiera pełne dane JEDNEJ frakcji po id (GET /factions/{id}) — także niegrywalnej
 * (np. Obsidian). Używane dla edge-case'u Firmament → Obsidian: podgląd komponentów
 * frakcji, której nie ma w puli wyboru. `enabled` pozwala odpalić zapytanie dopiero,
 * gdy faktycznie potrzebujemy detalu (po kliknięciu „Zobacz Obsidian").
 */
export function useFaction(factionId: string | null) {
  return useQuery<FactionInfo>({
    queryKey: ["faction", factionId],
    queryFn: () =>
      fetchJson<FactionInfo>(
        `${BOT_ROOT}/factions/${factionId}`,
        `faction ${factionId}`,
      ),
    enabled: factionId !== null,
    staleTime: Infinity,
  });
}

/**
 * Konfiguracja silnika wystawiana na potrzeby setupu (GET /engine/config).
 *
 * Niesie dozwolony zbiór poziomów trudności bota (R10.2). Front NIE trzyma
 * własnej kopii tej listy — zbiór jest konfiguracją backendu (`engine_config.json`
 * → `valid_difficulties`, ⚠️ ZAŁOŻENIE, patrz docs/RULES.md 36) czytaną przez
 * `StaticDataRegistry`.
 */
export type EngineConfigInfo = {
  valid_difficulties: string[];
  // Dozwolone osobowości (style gry) bota — też z `engine_config.json`.
  valid_personalities: string[];
  // Pozycje miejsc przy stole (sloty domowe) w kolejności; indeks = `SetupSlot.seat`.
  seats: string[];
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
  // Talia agend pochodzi z Ustawień (Game variants), nie z kreatora setupu.
  const settings = useSettingsStore.getState().settings;
  const agendaDeck = settings.absolAgendas ? "absol" : "standard";
  // Zegar szachowy (RULES.md 58) też pochodzi z Ustawień; null = gra bez zegara.
  const chessClock = settings.chessClockEnabled
    ? {
        total_minutes: settings.chessClockMinutes,
        increment_seconds: settings.chessClockIncrementSeconds,
      }
    : null;
  const response = await fetch(`${BOT_ROOT}/game/new`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      agenda_deck: agendaDeck,
      chess_clock: chessClock,
      // Stała długość okien reakcji (RULES.md 54.11) — ustawienie hosta.
      reaction_window_seconds: settings.reactionWindowSeconds,
      ...request,
    }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(
      `Failed to create game (${response.status}). ${detail}`.trim()
    );
  }
}
