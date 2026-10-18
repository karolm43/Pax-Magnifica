// Store Zustand — jedno źródło prawdy dla UI, synchronizowane z backendem.
// Stan gry przychodzi przez WebSocket (push po każdej mutacji); mapa jest
// pobierana jednorazowo przez REST (geometria mapy demonstracyjnej jest stała
// w ramach sesji backendu).

import { create } from "zustand";
import {
  fetchFactions,
  fetchMap,
  fetchState,
  loadMapString,
  openStateSocket,
  postRedo,
  postUndo,
  setPlanetUnits,
  setSpaceUnits,
  setupPlayer,
  type SetupPlayerPayload,
  type UnitChange,
} from "./api";
import type { FactionInfo, GameState, HistoryInfo, MapView } from "./types";

type ConnectionStatus = "idle" | "connecting" | "open" | "closed";

interface AppStore {
  map: MapView | null;
  gameState: GameState | null;
  history: HistoryInfo | null;
  factions: FactionInfo[];
  selectedPosition: string | null;
  status: ConnectionStatus;
  error: string | null;
  socket: WebSocket | null;

  /** Pobiera mapę i stan początkowy, otwiera WebSocket. */
  connect: () => Promise<void>;
  /** Zamyka WebSocket i czyści referencję. */
  disconnect: () => void;
  undo: () => Promise<void>;
  redo: () => Promise<void>;
  /** Ładuje mapę z map stringa AsyncTI4. */
  loadMap: (mapString: string) => Promise<void>;
  selectTile: (position: string | null) => void;
  setupPlayerFaction: (payload: SetupPlayerPayload) => Promise<void>;
  updateSpaceUnits: (position: string, changes: UnitChange[]) => Promise<void>;
  updatePlanetUnits: (
    position: string,
    planet: string,
    changes: UnitChange[],
    ownerId?: string,
  ) => Promise<void>;
}

export const useAppStore = create<AppStore>((set, get) => ({
  map: null,
  gameState: null,
  history: null,
  factions: [],
  selectedPosition: null,
  status: "idle",
  error: null,
  socket: null,

  connect: async () => {
    if (get().socket) return; // już połączono
    set({ status: "connecting", error: null });
    try {
      const [mapView, envelope, factions] = await Promise.all([
        fetchMap(),
        fetchState(),
        fetchFactions(),
      ]);
      set({
        map: mapView,
        gameState: envelope.state,
        history: envelope.history,
        factions,
      });

      const socket = openStateSocket({
        onState: (env) => set({ gameState: env.state, history: env.history }),
        onMap: (mapView) => set({ map: mapView }),
      });
      socket.addEventListener("open", () => set({ status: "open" }));
      socket.addEventListener("close", () => set({ status: "closed" }));
      socket.addEventListener("error", () =>
        set({ error: "Błąd połączenia WebSocket" }),
      );
      set({ socket });
    } catch (err) {
      set({
        status: "closed",
        error: err instanceof Error ? err.message : "Nieznany błąd połączenia",
      });
    }
  },

  disconnect: () => {
    const { socket } = get();
    socket?.close();
    set({ socket: null, status: "closed" });
  },

  undo: async () => {
    const env = await postUndo();
    set({ gameState: env.state, history: env.history });
  },

  redo: async () => {
    const env = await postRedo();
    set({ gameState: env.state, history: env.history });
  },

  loadMap: async (mapString: string) => {
    set({ error: null });
    try {
      const mapView = await loadMapString(mapString);
      set({ map: mapView });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Błąd ładowania map stringa",
      });
    }
  },

  selectTile: (position) => set({ selectedPosition: position }),

  setupPlayerFaction: async (payload) => {
    set({ error: null });
    try {
      const mapView = await setupPlayer(payload);
      set({ map: mapView });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Błąd setupu gracza" });
    }
  },

  updateSpaceUnits: async (position, changes) => {
    set({ error: null });
    try {
      const mapView = await setSpaceUnits(position, changes);
      set({ map: mapView });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Błąd edycji jednostek" });
    }
  },

  updatePlanetUnits: async (position, planet, changes, ownerId) => {
    set({ error: null });
    try {
      const mapView = await setPlanetUnits(position, planet, changes, ownerId);
      set({ map: mapView });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Błąd edycji jednostek" });
    }
  },
}));
