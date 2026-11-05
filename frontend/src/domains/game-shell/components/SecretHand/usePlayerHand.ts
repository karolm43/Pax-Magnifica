import { useQuery } from "@tanstack/react-query";
import { PlayerHandData } from "@/shared/types/playerHand";
import { authenticatedFetch, getBotApiUrl } from "@/api/auth";
import { fetchJson } from "@/api/fetchJson";
import { useSecretHandAccess } from "./useSecretHandAccess";

const fetchPlayerHand = (gameId: string) =>
  fetchJson<PlayerHandData>(
    getBotApiUrl(`/game/${gameId}/hand`),
    "player hand",
    {
      fetcher: authenticatedFetch,
    },
  );

type UsePlayerHandOptions = {
  /**
   * Pomija bramkę uwierzytelniania (Discord) i zawsze pobiera rękę. W trybie
   * lokalnym/solo operator widzi wszystko, a backend zwraca rękę AKTYWNEGO
   * gracza — więc „pasek ręki" na mapie działa bez logowania. Domyślnie bramka
   * działa (zakładka gracza pokazuje tylko rękę zalogowanego gracza w grze).
   */
  ignoreAuthGate?: boolean;
};

export const usePlayerHand = (
  gameId: string,
  { ignoreAuthGate = false }: UsePlayerHandOptions = {},
) => {
  const { userId, canViewSecretHand } = useSecretHandAccess();

  return useQuery({
    queryKey: ["playerHand", gameId, ignoreAuthGate ? "local" : userId],
    queryFn: () => fetchPlayerHand(gameId),
    enabled: ignoreAuthGate || canViewSecretHand,
    staleTime: 0,
  });
};
