import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";

/*
 * Okna czasowe otwarte TERAZ (RULES.md 54.9): jawne dla wszystkich graczy, bez informacji o rękach.
 * Silnik liczy je ze stanu gry (`GET /window/open-now`), więc odświeżamy je przy każdej zmianie stanu.
 */

export type OpenTimingWindow = {
  /** Stały klucz okna (porównanie między odświeżeniami → „Closed”). */
  key: string;
  event: string;
  moment: string;
  /** Angielska etykieta, np. „After a space combat is won”. */
  label: string;
  /** Gracz-podmiot okna (kto wygrał, kto aktywował…); `null` = okno wspólne. */
  subject: string | null;
  position: string | null;
  /** Co zamyka okno, np. „Ends when the battle is closed”. */
  closes: string;
};

export function useOpenWindows(stateVersion: unknown) {
  const query = useQuery({
    queryKey: ["openTimingWindows"],
    staleTime: 0,
    queryFn: async () =>
      (
        await fetchJson<{ windows: OpenTimingWindow[] }>(
          "/bot/window/open-now",
          "open timing windows",
        )
      ).windows,
  });
  const { refetch } = query;
  useEffect(() => {
    void refetch();
  }, [stateVersion, refetch]);
  return query;
}
