import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import { getBotApiUrl } from "@/api/auth/botApiUrl";
import type { PlayerHandData } from "@/shared/types/playerHand";

/**
 * Ręka KONKRETNEGO gracza (po ``player_id``) na potrzeby edytora God-Mode.
 *
 * W odróżnieniu od ``usePlayerHand`` (która celuje w AKTYWNEGO gracza i ma bramkę
 * Discorda) tu pytamy o wskazanego gracza przez query param ``?player=`` — operator
 * w trybie lokalnym widzi wszystko. Endpoint zwraca jawnie identyfikatory kart
 * (karty akcji / tajne cele / promissory notes). Puste listy, gdy gracza nie ma.
 */
export function usePlayerHandById(gameId: string, playerId: string | null) {
  return useQuery<PlayerHandData>({
    queryKey: ["playerHand", gameId, "god", playerId],
    enabled: Boolean(gameId) && Boolean(playerId),
    queryFn: () =>
      fetchJson<PlayerHandData>(
        getBotApiUrl(
          `/game/${gameId}/hand?player=${encodeURIComponent(playerId ?? "")}`,
        ),
        "player hand (god-mode)",
      ),
    staleTime: 0,
  });
}
