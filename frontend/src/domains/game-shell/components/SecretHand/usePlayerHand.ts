import { useQuery } from "@tanstack/react-query";
import { PlayerHandData } from "@/shared/types/playerHand";
import { authenticatedFetch, getBotApiUrl } from "@/api/auth";
import { fetchJson } from "@/api/fetchJson";
import { useSecretHandAccess } from "./useSecretHandAccess";

const fetchPlayerHand = (
  gameId: string,
  player?: string | null,
  // Tryb lokalny/solo (ignoreAuthGate): użyj ZWYKŁEGO fetch, bo authenticatedFetch
  // RZUCA „No authentication token available", gdy nikt nie jest zalogowany przez
  // Discord — a backend tego endpointu nie wymaga tokenu. To była przyczyna pustego
  // paska ręki mimo poprawnych danych w backendzie.
  local = false,
) => {
  const q = player ? `?player=${encodeURIComponent(player)}` : "";
  return fetchJson<PlayerHandData>(
    getBotApiUrl(`/game/${gameId}/hand${q}`),
    "player hand",
    local ? {} : { fetcher: authenticatedFetch },
  );
};

type UsePlayerHandOptions = {
  /**
   * Pomija bramkę uwierzytelniania (Discord) i zawsze pobiera rękę. W trybie
   * lokalnym/solo operator widzi wszystko, a backend zwraca rękę AKTYWNEGO
   * gracza — więc „pasek ręki" na mapie działa bez logowania. Domyślnie bramka
   * działa (zakładka gracza pokazuje tylko rękę zalogowanego gracza w grze).
   */
  ignoreAuthGate?: boolean;
  /**
   * Którego gracza rękę pobrać (``player_id``). Gdy pominięty — backend zwraca
   * rękę AKTYWNEGO gracza. Dok ręki podaje tu „gracza pulpitu" (aktywny → mówca
   * → pierwszy), by pulpit działał też między turami (status/agenda, brak
   * aktywnego gracza).
   */
  player?: string | null;
};

export const usePlayerHand = (
  gameId: string,
  { ignoreAuthGate = false, player = null }: UsePlayerHandOptions = {},
) => {
  const { userId, canViewSecretHand } = useSecretHandAccess();

  return useQuery({
    queryKey: [
      "playerHand",
      gameId,
      ignoreAuthGate ? "local" : userId,
      player ?? "active",
    ],
    queryFn: () => fetchPlayerHand(gameId, player, ignoreAuthGate),
    enabled: ignoreAuthGate || canViewSecretHand,
    staleTime: 0,
  });
};
