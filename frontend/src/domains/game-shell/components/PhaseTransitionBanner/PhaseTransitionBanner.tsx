import type { ReactElement } from "react";
import { useEffect, useRef, useState } from "react";
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

/*
 * Czas widoczności banera przed auto-ukryciem (R10.4). 3500 ms daje wyraźny,
 * planszówkowy sygnał z zapasem poniżej twardego limitu 5 s z kryterium akceptacji.
 */
const BANNER_VISIBLE_MS = 3500;

/**
 * Phase_Banner (Requirement 10) — czysto wizualna nakładka nad mapą sygnalizująca
 * wejście w nową GŁÓWNĄ fazę gry. Montowana na poziomie layoutu mapy (`MapView`,
 * `PannableMapView`) obok pozostałych nakładek, bo reaguje na KAŻDĄ zmianę fazy,
 * nie tylko strategii — dlatego żyje poza panelem strategii.
 *
 * To ZADANIE 10.2 dokłada MECHANIZM WYKRYWANIA ZMIANY głównej fazy: `useRef`
 * trzyma poprzednią główną fazę, a `useEffect` (zależny od `mainPhase`) porównuje
 * ją z bieżącą i wyzwala baner DOKŁADNIE raz na przejście (R10.7). Re-rendery w
 * obrębie tej samej głównej fazy (np. podfaza `status.*` → `status.**`, odświeżenie
 * stanu) nie wyzwalają banera ponownie (R10.8).
 *
 * Co dochodzi w kolejnych zadaniach:
 * - 10.3: animacja wejścia/wyjścia, auto-ukrycie (timer), fallback tekstowy przy `onError`;
 * - 10.4: realny krótki dźwięk przejścia z cichą degradacją.
 * Tutaj render pokazuje obrazek dla AKTYWNEJ (wyzwolonej) fazy; timer auto-ukrycia
 * i dźwięk są jeszcze stubami oznaczonymi komentarzem, żeby nie psuć type-check/lint/build.
 */
export function PhaseTransitionBanner(): ReactElement | null {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);

  // Źródło fazy: `gameState.phase` (jedyne źródło prawdy o fazie na froncie).
  // Normalizacja do głównej fazy: `"status.scoring" → "status"` (R10.3).
  const mainPhase = (gameState?.phase ?? "").split(".")[0];

  // Poprzednia GŁÓWNA faza — `null` oznacza „jeszcze nie zainicjalizowano" (pierwszy
  // render), co świadomie NIE jest traktowane jako przejście (brak „fałszywego" banera).
  const prevPhase = useRef<string | null>(null);
  // Główna faza aktualnie POKAZYWANA przez baner (wyzwolona przejściem).
  const [active, setActive] = useState<string | null>(null);
  // Czy obraz banera zawiódł → renderujemy tekstowy fallback (R10.9).
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
      // TODO(10.4): tutaj jednorazowe `playSound()` z cichą degradacją (R10.6/R10.7).

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

  return (
    <div className={styles.overlay} aria-hidden="true">
      {imgFailed ? (
        // Fallback tekstowy (R10.9): grafika się nie załadowała, więc w tej samej
        // nakładce (ta sama animacja, to samo auto-ukrycie) pokazujemy nazwę fazy.
        // Kontynuujemy bez zgłaszania błędu — baner „działa" dalej jako tekst.
        <div className={styles.fallback}>Faza: {active}</div>
      ) : (
        <img
          className={styles.banner}
          src={`${STATIC_BASE}/${activeFile}`}
          alt={active}
          // onError → przełączamy na fallback tekstowy bez propagacji błędu (R10.9).
          onError={() => setImgFailed(true)}
        />
      )}
    </div>
  );
}
