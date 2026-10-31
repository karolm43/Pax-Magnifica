import type { ReactElement } from "react";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import cx from "clsx";
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
 *
 * UWAGA: ścieżki plików są świadomie ustawione przez użytkownika — NIE zmieniać.
 */
const BANNER_FILE: Record<string, string> = {
  strategy: "strategy2.jpg",
  action: "acionphase2.jpg",
  status: "status2.jpg",
  agenda: "agenda2.jpg",
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
 * Czas widoczności banera przed rozpoczęciem wygaszania (R10.4). 3500 ms daje
 * wyraźny, planszówkowy sygnał z zapasem poniżej twardego limitu 5 s z kryterium
 * akceptacji. Po tym czasie startuje fade-out (patrz `FADE_OUT_MS`).
 */
const BANNER_VISIBLE_MS = 3500;

/*
 * Czas trwania wygaszania (fade-out) planszy, zsynchronizowany z przejściem opacity
 * w CSS. Po jego upływie baner jest odmontowywany (`setActive(null)`). Dopiero to
 * daje PRAWDZIWY fade-out (opacity 1→0 widoczne na ekranie), a nie natychmiastowe
 * zniknięcie przez odmontowanie.
 */
const FADE_OUT_MS = 400;

/**
 * Phase_Banner (Requirement 10) — PEŁNOEKRANOWA plansza przejścia sygnalizująca
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
 * WARSTWA WIZUALNA (plansza przejścia): PEŁNOEKRANOWA nakładka (`position: fixed;
 * inset: 0`) z obrazem banera wypełniającym CAŁY viewport (`object-fit: cover`) i
 * napisami wyśrodkowanymi NAD obrazem. Nakładka ma `pointer-events: none` przez
 * cały czas (R10.5). Przy błędzie grafiki (`onError`, R10.9) zostaje przyciemnione
 * tło + napisy, bez skoku layoutu. Nazwa fazy jest ZAWSZE widoczna.
 *
 * ANIMACJA: wyłącznie fade-in (na wejściu) + fade-out (`.leaving`), bez slajdu/skali.
 * Fade-out jest PRAWDZIWY dzięki dwufazowemu cyklowi życia: po `BANNER_VISIBLE_MS`
 * ustawiamy `leaving = true` (CSS wygasza opacity), a dopiero po `FADE_OUT_MS`
 * odmontowujemy baner. `prefers-reduced-motion` wyłącza animacje w CSS.
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
  // Czy baner jest w trakcie wygaszania (fade-out) — steruje klasą `.leaving`.
  const [leaving, setLeaving] = useState(false);
  // Czy obraz banera zawiódł → chowamy sam obraz, zostaje przyciemnione tło + napisy (R10.9).
  const [imgFailed, setImgFailed] = useState(false);
  // Id timera „start fade-out" (po `BANNER_VISIBLE_MS`); trzymany w ref, by czyścić go
  // w cleanup oraz przy ponownym wyzwoleniu — kolejne przejście nie może nakładać starego.
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Id timera „odmontowanie po fade-out" (po `FADE_OUT_MS`); analogicznie trzymany w ref.
  const fadeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

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
      // Nowe wyzwolenie zaczyna się od stanu „widoczny" — resetujemy ewentualne
      // wygaszanie po poprzednim banerze, żeby fade-in zadziałał od zera.
      setLeaving(false);
      setImgFailed(false);
      // Jednorazowa próba dźwięku przejścia — RAZ na przejście fazy (R10.7), wspólny
      // mechanizm wyzwolenia z banerem. Ciche pominięcie przy braku pliku/autoplay
      // (R10.6/R10.10/R10.11); nie przerywa banera (dźwięk i baner rozłączone).
      playSound();

      // Czyścimy OBA poprzednie timery (szybkie, kolejne przejście), żeby stary
      // odmierzony czas nie wygasił/odmontował świeżo pokazanego banera.
      if (hideTimer.current !== null) {
        clearTimeout(hideTimer.current);
      }
      if (fadeTimer.current !== null) {
        clearTimeout(fadeTimer.current);
      }
      // Po `BANNER_VISIBLE_MS` NIE odmontowujemy od razu — tylko startujemy fade-out
      // (R10.4). Samo odmontowanie następuje później, w efekcie zależnym od `leaving`.
      hideTimer.current = setTimeout(() => {
        setLeaving(true);
        hideTimer.current = null;
      }, BANNER_VISIBLE_MS);
    }

    // `prevPhase.current` aktualizujemy ZAWSZE przy zmianie — także dla faz spoza
    // mapy — żeby późniejsze wejście w fazę mapowalną poprawnie wykryć jako przejście.
    prevPhase.current = mainPhase;
  }, [mainPhase]);

  // Drugi krok cyklu życia: gdy baner wchodzi w fazę wygaszania (`leaving === true`),
  // odczekujemy `FADE_OUT_MS` (czas przejścia opacity w CSS) i dopiero wtedy
  // odmontowujemy baner oraz zerujemy `leaving`. To daje PRAWDZIWY fade-out.
  useEffect(() => {
    if (!leaving) {
      return;
    }
    fadeTimer.current = setTimeout(() => {
      setActive(null);
      setLeaving(false);
      fadeTimer.current = null;
    }, FADE_OUT_MS);
    // Cleanup: jeśli `leaving` zmieni się wcześniej (np. nowe wyzwolenie), anuluj timer.
    return () => {
      if (fadeTimer.current !== null) {
        clearTimeout(fadeTimer.current);
        fadeTimer.current = null;
      }
    };
  }, [leaving]);

  // Cleanup przy odmontowaniu komponentu: anuluj OBA wiszące timery, by nie wywołać
  // `setState` po odmontowaniu (brak wycieku timerów, R10.4).
  useEffect(() => {
    return () => {
      if (hideTimer.current !== null) {
        clearTimeout(hideTimer.current);
        hideTimer.current = null;
      }
      if (fadeTimer.current !== null) {
        clearTimeout(fadeTimer.current);
        fadeTimer.current = null;
      }
    };
  }, []);

  // Render pokazuje baner dla AKTYWNEJ (wyzwolonej) fazy. Fazy spoza mapy oraz brak
  // wyzwolenia → `active` jest `null`/niemapowalne → nic nie pokazujemy (bez błędu).
  const activeFile = active ? BANNER_FILE[active] : undefined;
  if (!active || !activeFile) return null;

  // Polska nazwa fazy (ZAWSZE widoczna). Dla faz obecnych w `BANNER_FILE` lookup
  // jest zdefiniowany; fallback na surową fazę gdyby etykiety brakło.
  const label = PHASE_LABEL[active] ?? active;

  return (
    <div
      className={cx(styles.overlay, leaving && styles.leaving)}
      aria-hidden="true"
    >
      {/* PEŁNOEKRANOWY obraz banera (R10.2): wypełnia cały viewport (`object-fit:
          cover`). Przy błędzie grafiki (R10.9) chowamy sam obraz — zostaje
          przyciemnione tło nakładki + napisy, bez skoku layoutu. */}
      {!imgFailed && (
        <img
          className={styles.banner}
          src={`${STATIC_BASE}/${activeFile}`}
          alt={label}
          // onError → ukrywamy obraz bez propagacji błędu, nazwa fazy zostaje (R10.9).
          onError={() => setImgFailed(true)}
        />
      )}
      {/* Napisy NAD obrazem: wyśrodkowane, z półprzezroczystym tłem i cieniem dla
          czytelności nad dowolną grafiką. Nazwa fazy ZAWSZE, „Runda N" opcjonalnie. */}
      <div className={styles.text}>
        <div className={styles.phase}>{label}</div>
        {gameRound !== undefined && (
          <div className={styles.round}>Runda {gameRound}</div>
        )}
      </div>
    </div>
  );
}
