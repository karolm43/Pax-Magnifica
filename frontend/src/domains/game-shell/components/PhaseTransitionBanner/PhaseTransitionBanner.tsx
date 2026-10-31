import type { ReactElement } from "react";
import { useParams } from "react-router-dom";
import { useGameState } from "@/api/useGameState";
import { DEFAULT_GAME_ID } from "@/config";
import styles from "./PhaseTransitionBanner.module.css";

/*
 * Baza statycznych assetów serwowanych przez backend (`app.mount("/static", ...)`).
 * Ścieżka WZGLĘDNA (nie `cdnImage()`): w dev proxy Vite kieruje `/static` na
 * backend :8000, a w prod front i backend są za tym samym originem — więc ten sam
 * zapis działa w obu trybach bez doklejania hosta (decyzja z design.md).
 */
const STATIC_BASE = "/static/extra";

/*
 * Mapowanie GŁÓWNEJ fazy → plik banera (R10.2). Klucz to znormalizowana główna
 * faza (`phase.split(".")[0]`), więc podfazy `status.*`/`agenda.*` trafiają na
 * jeden baner swojej głównej fazy (R10.3). Fazy spoza tej mapy (np. `setup`,
 * `unknown`, `finished`) nie mają banera — render zwraca `null` bez błędu.
 */
const BANNER_FILE: Record<string, string> = {
  strategy: "strategybanner.png",
  action: "actionbanner.png",
  status: "statusbanner.png",
  agenda: "agendabanner.png",
};

/**
 * Phase_Banner (Requirement 10) — czysto wizualna nakładka nad mapą sygnalizująca
 * wejście w nową GŁÓWNĄ fazę gry. Montowana na poziomie layoutu mapy (`MapView`,
 * `PannableMapView`) obok pozostałych nakładek, bo reaguje na KAŻDĄ zmianę fazy,
 * nie tylko strategii — dlatego żyje poza panelem strategii.
 *
 * To ZADANIE 10.1 to SZKIELET + montaż: komponent istnieje, czyta fazę z
 * istniejącego hooka `useGameState` (to samo źródło co `StrategyCardTable`/
 * `GameStatePanel` — zero nowych hooków/źródeł), normalizuje `mainPhase` i ma
 * stałą `BANNER_FILE`. Nakładka ma `pointer-events: none`, więc nie przechwytuje
 * interakcji z mapą/panelami (R10.5) i nie psuje layoutów.
 *
 * Co dochodzi w kolejnych zadaniach:
 * - 10.2: wykrywanie ZMIANY głównej fazy (`useRef`) i jednorazowe wyzwolenie;
 * - 10.3: animacja wejścia/wyjścia, auto-ukrycie, fallback tekstowy przy `onError`;
 * - 10.4: krótki dźwięk przejścia z cichą degradacją.
 * Tutaj render jest minimalny: dla mapowalnej fazy pokazuje obrazek banera,
 * dla pozostałych faz — nic.
 */
export function PhaseTransitionBanner(): ReactElement | null {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);

  // Źródło fazy: `gameState.phase` (jedyne źródło prawdy o fazie na froncie).
  // Normalizacja do głównej fazy: `"status.scoring" → "status"` (R10.3).
  const mainPhase = (gameState?.phase ?? "").split(".")[0];
  const bannerFile = BANNER_FILE[mainPhase];

  // Fazy spoza mapy `BANNER_FILE` → brak banera (bez błędu).
  if (!bannerFile) return null;

  return (
    <div className={styles.overlay} aria-hidden="true">
      <img
        className={styles.banner}
        src={`${STATIC_BASE}/${bannerFile}`}
        alt={mainPhase}
      />
    </div>
  );
}
