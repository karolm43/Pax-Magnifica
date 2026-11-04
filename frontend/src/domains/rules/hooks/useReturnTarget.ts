/**
 * Hook kontekstu powrotu przeglądarki Zasad (Rules_Browser).
 *
 * Rozstrzyga, dokąd kieruje kontrolka powrotu, zależnie od miejsca otwarcia ekranu
 * Zasad (Req 10.5/10.6):
 * - otwarcie z panelu gry (`/rules?from=game`) → powrót do `/game` („Back to game");
 * - otwarcie z menu głównego (bez `from=game`) → powrót do `/` („Main menu").
 *
 * Źródłem sygnału jest w pierwszej kolejności parametr zapytania `?from=game`
 * (czytany przez `useSearchParams`), a jako fallback — `location.state.from`
 * (ustawiany przy nawigacji programowej, gdy nie chcemy zaśmiecać adresu). Oba
 * sprowadzamy do tej samej reguły: `from === "game"` → cel gry, inaczej cel menu.
 */

import { useMemo } from "react";
import { useLocation, useSearchParams } from "react-router-dom";

/** Cel powrotu: ścieżka routingu + etykieta widoczna na kontrolce powrotu. */
export type ReturnTarget = {
  /** Ścieżka routingu docelowa dla kontrolki powrotu. */
  path: string;
  /** Etykieta tekstowa kontrolki powrotu (po polsku). */
  label: string;
};

/** Cel powrotu do panelu gry (otwarcie z `/rules?from=game`). */
const GAME_TARGET: ReturnTarget = { path: "/game", label: "Back to game" };

/** Domyślny cel powrotu do menu głównego (otwarcie z menu). */
const MENU_TARGET: ReturnTarget = { path: "/", label: "Main menu" };

/**
 * Wyznacza cel powrotu na podstawie `?from=game` z fallbackiem na `location.state`.
 *
 * @returns `{ path: "/game", label: "Back to game" }`, gdy ekran otwarto z panelu
 *   gry (`from === "game"`); w przeciwnym razie `{ path: "/", label: "Main menu" }`.
 */
export function useReturnTarget(): ReturnTarget {
  const [searchParams] = useSearchParams();
  const location = useLocation();

  return useMemo(() => {
    // Priorytet: parametr zapytania `?from=...`; fallback na `location.state.from`.
    const fromQuery = searchParams.get("from");
    const state = location.state as { from?: unknown } | null;
    const fromState =
      typeof state?.from === "string" ? state.from : undefined;
    const from = fromQuery ?? fromState;

    return from === "game" ? GAME_TARGET : MENU_TARGET;
  }, [searchParams, location.state]);
}
