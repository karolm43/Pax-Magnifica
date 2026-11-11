/*
 * Lobby gry sieciowej i zapisy partii (RULES.md 44.4, 44.6) — zapytania i akcje.
 *
 * Host (ten komputer) otwiera lobby, gracze z innych komputerów (np. ZeroTier) dołączają
 * imieniem i dostają token członka (zapamiętany w karcie, `storeSeatToken`). Przy starcie
 * gry host przypisuje członków do miejsc (`assignLobbySeats`): slot i → gracz `p{i+1}`
 * (tak backend numeruje graczy w `/game/new`).
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { create } from "zustand";
import { storeSeatToken } from "@/api/actorIdentity";
import { NETWORK_ME_KEY } from "./useNetworkMe";

export type LobbyMember = { member_id: string; name: string; player_id: string | null };

export type LobbyView = {
  open: boolean;
  members: LobbyMember[];
  game_started: boolean;
  addresses: string[];
  save_name: string | null;
};

export type SaveEntry = {
  name: string;
  modified: number;
  round_number: number | null;
  phase: string | null;
  players: string[];
  broken: boolean;
  current: boolean;
};

export const LOBBY_KEY = ["network", "lobby"] as const;
export const SAVES_KEY = ["network", "saves"] as const;

async function call<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/bot${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const raw = await res.text().catch(() => "");
    let message = raw || `Error ${res.status}`;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // nie-JSON — zostaje surowy tekst
    }
    throw new Error(message);
  }
  return (await res.json()) as T;
}

/** Stan lobby (odświeżany co 2 s, gdy otwarte — widać dołączających). */
export function useLobby(enabled = true) {
  return useQuery({
    queryKey: LOBBY_KEY,
    queryFn: () => call<LobbyView>("/lobby"),
    enabled,
    refetchInterval: (query) => (query.state.data?.open ? 2000 : false),
  });
}

export function useSaves(enabled: boolean) {
  return useQuery({
    queryKey: SAVES_KEY,
    queryFn: () => call<{ enabled: boolean; saves: SaveEntry[] }>("/saves"),
    enabled,
  });
}

/** Akcje lobby/zapisów z odświeżeniem zależnych zapytań. */
export function useLobbyActions() {
  const queryClient = useQueryClient();
  const refresh = async (lobby?: LobbyView) => {
    if (lobby) queryClient.setQueryData(LOBBY_KEY, lobby);
    await queryClient.invalidateQueries({ queryKey: NETWORK_ME_KEY });
    await queryClient.invalidateQueries({ queryKey: LOBBY_KEY });
  };
  return {
    open: async () => refresh(await call<LobbyView>("/lobby/open", {})),
    close: async () => refresh(await call<LobbyView>("/lobby/close", {})),
    kick: async (memberId: string) =>
      refresh(await call<LobbyView>(`/lobby/kick/${encodeURIComponent(memberId)}`, {})),
    /** Dołączenie imieniem: token członka trafia do karty (od teraz wszystkie żądania z nim). */
    join: async (name: string) => {
      const joined = await call<{ member_id: string; name: string; token: string }>(
        "/lobby/join",
        { name },
      );
      storeSeatToken(joined.token);
      await refresh();
      return joined;
    },
    loadSave: async (name: string) => {
      await call("/saves/load", { name });
      await queryClient.invalidateQueries();
    },
  };
}

/** Kto siedzi na którym slocie kreatora: `"host"` albo `member_id` (puste = nikt / bot). */
type AssignmentStore = {
  bySlot: Record<number, string>;
  setSlot: (slot: number, who: string | null) => void;
  clear: () => void;
};

export const useLobbyAssignments = create<AssignmentStore>((set) => ({
  bySlot: {},
  setSlot: (slot, who) =>
    set((s) => {
      const next = { ...s.bySlot };
      // Jeden człowiek = jedno miejsce: zdejmij go z innego slotu.
      for (const [k, v] of Object.entries(next)) if (v === who) delete next[Number(k)];
      if (who) next[slot] = who;
      else delete next[slot];
      return { bySlot: next };
    }),
  clear: () => set({ bySlot: {} }),
}));

/** Po `/game/new`: przypisuje członków lobby do graczy `p{slot+1}`. */
export async function assignLobbySeats(bySlot: Record<number, string>): Promise<void> {
  const assignments = Object.fromEntries(
    Object.entries(bySlot).map(([slot, who]) => [`p${Number(slot) + 1}`, who]),
  );
  if (Object.keys(assignments).length === 0) return;
  await call("/lobby/assign", { assignments });
}
