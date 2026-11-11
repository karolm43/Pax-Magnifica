/*
 * Kim jestem w grze sieciowej (RULES.md 44.2): GET /network/me.
 * Tryb lokalny zwraca `network: false` — wtedy UI działa jak dotychczas.
 */
import { useQuery } from "@tanstack/react-query";

export type NetworkMe = {
  network: boolean;
  authenticated: boolean;
  player_id: string | null;
  host: boolean;
};

export const NETWORK_ME_KEY = ["network", "me"] as const;

export function useNetworkMe() {
  return useQuery({
    queryKey: NETWORK_ME_KEY,
    queryFn: async (): Promise<NetworkMe> => {
      const res = await fetch("/bot/network/me");
      if (!res.ok) throw new Error(`network/me: ${res.status}`);
      return (await res.json()) as NetworkMe;
    },
    staleTime: 60_000,
  });
}
