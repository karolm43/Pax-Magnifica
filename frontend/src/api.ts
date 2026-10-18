// Warstwa dostępu do backendu. Adresy są względne — dev-serwer Vite kieruje
// /api i /ws do FastAPI (patrz vite.config.ts). W buildzie produkcyjnym (Tauri /
// serwer statyczny) te same ścieżki działają, o ile backend serwuje front lub
// proxy jest skonfigurowane analogicznie.

import type { FactionInfo, MapView, StateEnvelope } from "./types";

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} → ${resp.status}`);
  }
  return (await resp.json()) as T;
}

export const fetchState = () => request<StateEnvelope>("/state");
export const fetchMap = () => request<MapView>("/map");
export const postUndo = () => request<StateEnvelope>("/undo", { method: "POST" });
export const postRedo = () => request<StateEnvelope>("/redo", { method: "POST" });

/** Ładuje mapę z map stringa AsyncTI4 i zwraca nowy widok mapy. */
export const loadMapString = (mapString: string) =>
  request<MapView>("/map/load", {
    method: "POST",
    body: JSON.stringify({ map_string: mapString }),
  });

export const fetchFactions = () => request<FactionInfo[]>("/factions");

export interface SetupPlayerPayload {
  player_id: string;
  faction_id: string;
  color: string;
  home_position: string;
}

export const setupPlayer = (payload: SetupPlayerPayload) =>
  request<MapView>("/setup/player", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export interface UnitChange {
  player_id: string;
  base_type: string;
  count: number;
}

export const setSpaceUnits = (position: string, changes: UnitChange[]) =>
  request<MapView>(`/system/${position}/space`, {
    method: "POST",
    body: JSON.stringify({ changes }),
  });

export const setPlanetUnits = (
  position: string,
  planet: string,
  changes: UnitChange[],
  ownerId?: string,
) =>
  request<MapView>(`/system/${position}/planet/${planet}`, {
    method: "POST",
    body: JSON.stringify({ changes, owner_id: ownerId ?? null }),
  });

interface SocketHandlers {
  onState: (env: StateEnvelope) => void;
  onMap?: (map: MapView) => void;
}

/** Otwiera połączenie WebSocket do strumienia stanu i (opcjonalnie) mapy. */
export function openStateSocket(handlers: SocketHandlers): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${proto}://${window.location.host}/ws`);
  socket.addEventListener("message", (event) => {
    try {
      const parsed = JSON.parse(event.data as string) as { type?: string };
      if (parsed.type === "state") {
        handlers.onState(parsed as unknown as StateEnvelope);
      } else if (parsed.type === "map" && handlers.onMap) {
        handlers.onMap(parsed as unknown as MapView);
      }
    } catch {
      // Ignorujemy wiadomości niezgodne z kontraktem.
    }
  });
  return socket;
}
