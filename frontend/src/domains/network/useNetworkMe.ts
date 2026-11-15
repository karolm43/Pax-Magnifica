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
  /** Członek lobby (dołączył imieniem), także zanim dostał miejsce. */
  member_id?: string | null;
  name?: string | null;
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

/**
 * Czy ten klient jest hostem/adminem (tryb lokalny = admin). Dopóki /network/me się
 * ładuje: ``false`` — narzędzia God-Mode nie mignują graczom sieciowym.
 */
export function useIsHost(): boolean {
  const { data: me } = useNetworkMe();
  return !!me && (!me.network || me.host);
}

/**
 * Czy ten klient może działać jako ``playerId`` i widzieć jego dane prywatne — lustro
 * ``Identity.sees_everything`` / ``require_view`` (RULES.md 44.3): tryb lokalny albo host
 * bez miejsca widzi wszystkich, gracz sieciowy tylko siebie. Monity adresowane do innego
 * gracza (primary/secondary karty strategii) chowamy — status „Waiting for X" daje
 * ``TurnStatusChip``. Dopóki /network/me się ładuje: ``false`` (bez zapytań kończących 403).
 */
export function canActAs(me: NetworkMe | undefined, playerId: string | null | undefined): boolean {
  if (!me || !playerId) return false;
  if (!me.network || (me.host && !me.player_id)) return true;
  return me.player_id === playerId;
}

/** Hook: ``canActAs`` z bieżącym ``/network/me``. */
export function useCanActAs(): (playerId: string | null | undefined) => boolean {
  const { data: me } = useNetworkMe();
  return (playerId) => canActAs(me, playerId);
}
