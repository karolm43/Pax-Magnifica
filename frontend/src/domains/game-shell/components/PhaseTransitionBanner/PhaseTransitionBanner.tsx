import type { CSSProperties, ReactElement } from "react";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
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
 * Stała ścieżka do pliku dźwięku przejścia fazy (R10.6). Ten sam schemat względny
 * co obrazki banera — `/static` idzie przez proxy Vite (dev) albo ten sam origin
 * (prod). Plik jest OPCJONALNY (dostarczany później), więc jego brak (404) musi
 * degradować się po cichu — patrz `playSound()`.
 */
const SOUND_URL = `${STATIC_BASE}/sounds/phase_change.mp3`;

/*
 * Jednorazowa próba odtworzenia dźwięku przejścia fazy z CICHĄ DEGRADACJĄ
 * (R10.6/R10.10/R10.11). Dźwięk i baner są ROZŁĄCZONE: tu nie dotykamy stanu
 * banera, a każdy błąd (brak pliku/404, wyjątek konstruktora `Audio`, zablokowany
 * autoplay przez przeglądarkę) jest połykany — baner działa dalej niezależnie.
 */
function playSound(): void {
  try {
    const audio = new Audio(SOUND_URL);
    // `play()` zwraca Promise; odrzucenie (np. zablokowany autoplay, R10.11) łapiemy
    // i ignorujemy. `void` — świadomie nie czekamy na wynik.
    void audio.play().catch(() => {
      /* R10.10/R10.11: ciche pominięcie (brak pliku lub zablokowany autoplay) */
    });
  } catch {
    /* R10.10: wyjątek konstruktora `Audio` / brak pliku -> ciche pominięcie */
  }
}

/*
 * Mapowanie GŁÓWNEJ fazy → plik banera (R10.2). Klucz to znormalizowana główna
 * faza (`phase.split(".")[0]`), więc podfazy `status.*`/`agenda.*` trafiają na
 * jeden baner swojej głównej fazy (R10.3). Fazy spoza tej mapy (np. `setup`,
 * `unknown`, `finished`) nie mają banera — render zwraca `null` bez błędu.
 */
const BANNER_FILE: Record<string, string> = {
  strategy: "strategy2.png",
  action: "acionphase2.png",
  status: "status2.png",
  agenda: "agenda2.png",
};

/*
 * Polskie nazwy GŁÓWNYCH faz (czysto wizualne, R10). ZAWSZE widoczne na planszy
 * przejścia (nie tylko w fallbacku po błędzie grafiki). Klucze pokrywają się z
 * `BANNER_FILE`, więc każda wyzwalana faza ma swoją etykietę.
 */
const PHASE_LABEL: Record<string, string> = {
  strategy: "FAZA STRATEGII",
  action: "FAZA AKCJI",
  status: "FAZA STATUSU",
  agenda: "FAZA AGENDY",
};

/*
 * Akcent koloru per faza — poświata/obwódka planszy przejścia (R10, wizualne).
 * Wartości dobrane z istniejących tokenów sygnałów (`frontend/src/ds/tokens.css`):
 * tokeny `--ds-sig-*` to trójki RGB (używane przez `rgb(var(...) / <alfa>)`), a
 * `--ds-accent` to pełny hex (plus `--ds-accent-rgb` do alfy). Rozróżnienie jest
 * istotne — poniżej budujemy gotowe wyrażenia `rgb(...)` do użycia w CSS vars.
 */
const PHASE_ACCENT: Record<string, { solid: string; soft: string }> = {
  // interakcyjny akcent: hex + osobna trójka RGB do przezroczystości
  strategy: {
    solid: "var(--ds-accent)",
    soft: "rgb(var(--ds-accent-rgb) / 0.35)",
  },
  action: {
    solid: "rgb(var(--ds-sig-war))",
    soft: "rgb(var(--ds-sig-war) / 0.35)",
  },
  status: {
    solid: "rgb(var(--ds-sig-ok))",
    soft: "rgb(var(--ds-sig-ok) / 0.35)",
  },
  agenda: {
    solid: "rgb(var(--ds-sig-law))",
    soft: "rgb(var(--ds-sig-law) / 0.35)",
  },
};

/*
 * Czas widoczności banera przed auto-ukryciem (R10.4). 3500 ms daje wyraźny,
 * planszówkowy sygnał z zapasem poniżej twardego limitu 5 s z kryterium akceptacji.
 */
const BANNER_VISIBLE_MS = 3500;

/**
 * Phase_Banner (Requirement 10) — pełnoekranowa plansza przejścia sygnalizująca
 * wejście w nową GŁÓWNĄ fazę gry. Montowana na poziomie layoutu mapy (`MapView`,
 * `PannableMapView`) obok pozostałych nakładek, bo reaguje na KAŻDĄ zmianę fazy,
 * nie tylko strategii — dlatego żyje poza panelem strategii.
 *
 * MECHANIZM WYKRYWANIA ZMIANY głównej fazy (bez zmian funkcjonalnych): `useRef`
 * trzyma poprzednią główną fazę, a `useEffect` (zależny od `mainPhase`) porównuje
 * ją z bieżącą i wyzwala baner DOKŁADNIE raz na przejście (R10.7). Re-rendery w
 * obrębie tej samej głównej fazy (np. podfaza `status.*` → `status.**`, odświeżenie
 * stanu) nie wyzwalają banera ponownie (R10.8).
 *
 * WARSTWA WIZUALNA (plansza przejścia): pełnoekranowa nakładka (`inset: 0`) z
 * przyciemnieniem tła, ale `pointer-events: none` przez cały czas (R10.5). Układ
 * PIONOWY: duży obraz banera NAD blokiem tekstu (polska nazwa fazy + „Runda N").
 * Przy błędzie grafiki (`onError`, R10.9) chowamy sam obraz — blok tekstowy (nazwa
 * + runda) zostaje bez skoku layoutu. Nazwa fazy jest ZAWSZE widoczna.
 *
 * ŹRÓDŁA DANYCH (dwa osobne, istniejące hooki, zero nowych):
 * - `useGameState` → `phase` (jedyne źródło prawdy o fazie);
 * - `useGameData` → `gameRound` (top-level web-data `PlayerDataResponse.gameRound`).
 */
export function PhaseTransitionBanner(): ReactElement | null {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  // Numer rundy z OSOBNEGO źródła (web-data). Hook może zwrócić `undefined`
  // (brak kontekstu/jeszcze niezaładowane) — zabezpieczamy `?.` i pomijamy
  // podtytuł, gdy rundy brak (bez błędu, R10.9).
  const gameData = useGameData();
  const gameRound = gameData?.gameRound;

  // Źródło fazy: `gameState.phase` (jedyne źródło prawdy o fazie na froncie).
  // Normalizacja do głównej fazy: `"status.scoring" → "status"` (R10.3).
  const mainPhase = (gameState?.phase ?? "").split(".")[0];

  // Poprzednia GŁÓWNA faza — `null` oznacza „jeszcze nie zainicjalizowano" (pierwszy
  // render), co świadomie NIE jest traktowane jako przejście (brak „fałszywego" banera).
  const prevPhase = useRef<string | null>(null);
  // Główna faza aktualnie POKAZYWANA przez baner (wyzwolona przejściem).
  const [active, setActive] = useState<string | null>(null);
  // Czy obraz banera zawiódł → ukrywamy sam obraz, zostaje blok tekstowy (R10.9).
  const [imgFailed, setImgFailed] = useState(false);
  // Id timera auto-ukrycia; trzymany w ref, by czyścić go w cleanup efektu oraz
  // przy ponownym wyzwoleniu — kolejne przejście nie może nakładać starego timera.
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Wykrywanie ZMIANY głównej fazy i jednorazowe wyzwolenie (R10.7, R10.8).
  // Zależność od `mainPhase`: efekt przelicza się tylko gdy zmieni się główna faza,
  // ale PORÓWNANIE z `prevPhase.current` chroni przed podwójnym wyzwoleniem przy
  // re-renderach, gdyby `mainPhase` pozostał ten sam.
  useEffect(() => {
    // Pierwszy render (`prevPhase.current === null`): tylko inicjalizujemy ref,
    // BEZ wyzwalania banera — unikamy „fałszywego" banera na wejściu (R10.8).
    if (prevPhase.current === null) {
      prevPhase.current = mainPhase;
      return;
    }

    // Brak realnej zmiany głównej fazy → nic nie robimy (R10.8).
    if (mainPhase === prevPhase.current) {
      return;
    }

    // Doszło do ZMIANY głównej fazy. Baner wyzwalamy TYLKO dla faz mapowalnych
    // (obecnych w `BANNER_FILE`); dla faz spoza mapy baner się nie pojawia.
    if (BANNER_FILE[mainPhase]) {
      setActive(mainPhase);
      setImgFailed(false);
      // Jednorazowa próba dźwięku przejścia — RAZ na przejście fazy (R10.7), wspólny
      // mechanizm wyzwolenia z banerem. Ciche pominięcie przy braku pliku/autoplay
      // (R10.6/R10.10/R10.11); nie przerywa banera (dźwięk i baner rozłączone).
      playSound();

      // Auto-ukrycie po `BANNER_VISIBLE_MS` (R10.4). Najpierw czyścimy ewentualny
      // poprzedni timer (szybkie, kolejne przejście), żeby stary odmierzony czas nie
      // ukrył świeżo pokazanego banera. Po czasie `setActive(null)` odmontowuje baner.
      if (hideTimer.current !== null) {
        clearTimeout(hideTimer.current);
      }
      hideTimer.current = setTimeout(() => {
        setActive(null);
        hideTimer.current = null;
      }, BANNER_VISIBLE_MS);
    }

    // `prevPhase.current` aktualizujemy ZAWSZE przy zmianie — także dla faz spoza
    // mapy — żeby późniejsze wejście w fazę mapowalną poprawnie wykryć jako przejście.
    prevPhase.current = mainPhase;
  }, [mainPhase]);

  // Cleanup przy odmontowaniu komponentu: anuluj wiszący timer auto-ukrycia, by
  // nie wywołać `setActive` po odmontowaniu (brak wycieku timera, R10.4).
  useEffect(() => {
    return () => {
      if (hideTimer.current !== null) {
        clearTimeout(hideTimer.current);
        hideTimer.current = null;
      }
    };
  }, []);

  // Render pokazuje baner dla AKTYWNEJ (wyzwolonej) fazy. Fazy spoza mapy oraz brak
  // wyzwolenia → `active` jest `null`/niemapowalne → nic nie pokazujemy (bez błędu).
  const activeFile = active ? BANNER_FILE[active] : undefined;
  if (!active || !activeFile) return null;

  // Polska nazwa fazy (ZAWSZE widoczna) oraz akcent koloru per faza. Dla faz obecnych
  // w `BANNER_FILE` oba lookupy są zdefiniowane; akcent wstrzykujemy jako CSS vars.
  const label = PHASE_LABEL[active] ?? active;
  const accent = PHASE_ACCENT[active];
  const accentStyle = {
    "--banner-accent": accent?.solid ?? "var(--ds-accent)",
    "--banner-accent-soft": accent?.soft ?? "rgb(var(--ds-accent-rgb) / 0.35)",
  } as CSSProperties;

  return (
    <div className={styles.overlay} style={accentStyle} aria-hidden="true">
      <div className={styles.stage}>
        {/* Układ PIONOWY: duży obraz NAD blokiem tekstu. Przy błędzie grafiki
            (R10.9) chowamy sam obraz — blok tekstowy zostaje bez skoku layoutu. */}
        {!imgFailed && (
          <img
            className={styles.banner}
            src={`${STATIC_BASE}/${activeFile}`}
            alt={label}
            // onError → ukrywamy obraz bez propagacji błędu, nazwa fazy zostaje (R10.9).
            onError={() => setImgFailed(true)}
          />
        )}
        {/* Blok tekstowy: nazwa fazy (ZAWSZE) + opcjonalny podtytuł „Runda N". */}
        <div className={styles.text}>
          <div className={styles.phase}>{label}</div>
          {gameRound !== undefined && (
            <div className={styles.round}>Runda {gameRound}</div>
          )}
        </div>
      </div>
    </div>
  );
}
