import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Button } from "@/ds";
import { useFactions } from "@/api/useNewGame";
import SetupWizard from "@/domains/setup/SetupWizard";
import { SettingsModal } from "@/domains/settings/components/SettingsModal";
import { usePageThemeClass } from "@/hooks/usePageThemeClass";
import styles from "./StartScreen.module.css";

/**
 * Pełnoekranowy ekran rozruchu — pokazywany, dopóki ładujemy dane gry (frakcje)
 * z backendu, oraz gdy ładowanie się nie powiedzie. Trzyma ten sam ciemny klimat
 * co menu (to samo tło, mocno przyciemnione), logo i animowany pasek postępu —
 * żeby start aplikacji wyglądał jak rozruch prawdziwej gry, nie jak pusty ekran
 * z kręciołkiem.
 */
function BootScreen({
  state,
  onRetry,
  leaving = false,
}: {
  state: "loading" | "error";
  onRetry?: () => void;
  /** Faza wyjścia: ekran płynnie się wygasza (nad gotowym już menu). */
  leaving?: boolean;
}) {
  const themeClassName = usePageThemeClass();
  return (
    <div
      className={`${themeClassName} ${styles.boot} ${
        leaving ? styles.bootLeaving : ""
      }`}
    >
      <div className={styles.bootInner}>
        <div className={styles.menuTitleWrap}>
          <h1 className={`${styles.menuTitle} ${styles.bootTitle}`}>
            Custodian Engine
          </h1>
          <span className={styles.titleRule} aria-hidden />
        </div>

        {state === "loading" ? (
          <div className={styles.bootStatus}>
            <div
              className={styles.progressTrack}
              role="progressbar"
              aria-label="Loading game assets"
            >
              <span className={styles.progressBar} />
            </div>
            <p className={styles.bootLabel}>Loading game assets…</p>
          </div>
        ) : (
          <div className={styles.bootStatus}>
            <p className={styles.bootError}>
              Failed to load game data. Check that the backend is running
              (port 8000) and try again.
            </p>
            {onRetry && (
              <Button variant="default" onClick={onRetry}>
                Try again
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Ekran startowy Custodian Engine. Menu główne (Graj / Ustawienia / Zasady), a po
 * kliknięciu „Graj" — kreator nowej gry (`Setup_Wizard`): liczba graczy, nazwy,
 * kolory, frakcje, technologie startowe oraz człowiek/bot + trudność, zakończony
 * utworzeniem gry i przejściem do planszy.
 *
 * Konfigurację i wysyłkę `/game/new` obsługuje w całości `SetupWizard` (jedno źródło
 * prawdy w `useSetupStore`). Ten ekran odpowiada już tylko za rozruch (ładowanie
 * frakcji), menu i przełączanie widoku menu ↔ setup.
 */
export default function StartScreen() {
  const themeClassName = usePageThemeClass();
  const navigate = useNavigate();
  // Ładowanie frakcji trzymamy TUTAJ, by pokazać ekran rozruchu, zanim wejdziemy
  // w menu/kreator. `SetupWizard` korzysta z tego samego zapytania (react-query
  // cache), więc nie ma podwójnego pobrania.
  const { isLoading, isError, refetch } = useFactions();

  // Minimalny czas pokazania ekranu rozruchu. Lokalny backend odpowiada niemal
  // natychmiast, więc bez tego BootScreen tylko by „mignął". Dzięki temu rozruch
  // jest widoczny i płynnie znika, zamiast przeskakiwać od razu do menu.
  const MIN_BOOT_MS = 1100;
  // Czas wygaszania rozruchu — musi odpowiadać `--ds-dur-slow` z transition w CSS
  // (fallback 0.45s), żeby odmontować dopiero po zakończeniu fade-outu.
  const BOOT_FADE_MS = 450;
  const [bootMinElapsed, setBootMinElapsed] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setBootMinElapsed(true), MIN_BOOT_MS);
    return () => window.clearTimeout(t);
  }, []);

  // Rozruch znika PŁYNNIE, nie przeskokiem: gdy dane są gotowe i minął minimalny
  // czas, renderujemy menu, a BootScreen trzymamy jeszcze jako wygaszaną nakładkę
  // na wierzchu, po czym go odmontowujemy.
  const bootDataReady = !isLoading && !isError && bootMinElapsed;
  const [bootGone, setBootGone] = useState(false);
  useEffect(() => {
    if (!bootDataReady || bootGone) return;
    const t = window.setTimeout(() => setBootGone(true), BOOT_FADE_MS);
    return () => window.clearTimeout(t);
  }, [bootDataReady, bootGone]);

  // Widok ekranu startowego: "menu" (ekran tytułowy z 3 przyciskami) lub "setup"
  // (kreator nowej gry). Oba leżą w jednym pionowym „decku" wysokim na dwa ekrany;
  // zmiana widoku PRZEWIJA deck w pionie (translateY) z animacją, więc klik „Graj"
  // wygląda jak zjechanie strony w dół do kreatora.
  const [view, setView] = useState<"menu" | "setup">("menu");
  // Okno szkieletowe — na razie placeholder, wypełnimy je później.
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Dopóki ładujemy frakcje (lub gdy się nie powiodło) — pełnoekranowy rozruch,
  // zamiast migać pustym menu bez danych. Boot utrzymujemy też przez minimalne
  // okno czasu, żeby przy błyskawicznym backendzie nie „mignął".
  if (isError) return <BootScreen state="error" onRetry={() => void refetch()} />;
  if (!bootDataReady) return <BootScreen state="loading" />;

  return (
    <Box className={`${themeClassName} ${styles.root}`}>
      {/*
       * Nakładka wygaszanego rozruchu NAD menu: menu jest już w pełni zmontowane,
       * a boot płynnie znika (opacity), więc przejście jest smooth — bez przeskoku.
       * Po zakończeniu fade-outu (`bootGone`) nakładka znika z drzewa.
       */}
      {!bootGone && (
        <div className={styles.bootOverlay}>
          <BootScreen state="loading" leaving />
        </div>
      )}
      {/*
       * Pionowy „deck" wysoki na dwa ekrany. Klasa `deckSetup` przesuwa go w
       * górę o 50% (translateY) z animacją, odsłaniając ekran konfiguracji —
       * efekt „strona zjeżdża w dół do kreatora".
       */}
      <div
        className={`${styles.deck} ${
          view === "setup" ? styles.deckSetup : ""
        }`}
      >
        {/* ── Ekran tytułowy (menu główne) ──────────────────────────────── */}
        <div
          className={styles.menuScreen}
          aria-hidden={view === "setup"}
          inert={view === "setup"}
        >
          <div className={styles.menuTitleWrap}>
            <h1 className={styles.menuTitle}>Custodian Engine</h1>
            <span className={styles.titleRule} aria-hidden />
            <p className={styles.menuTagline}>Twilight Imperium 4 — web game</p>
          </div>

          <nav className={styles.menuButtons} aria-label="Main menu">
            <Button
              size="xl"
              fullWidth
              className={styles.menuButton}
              onClick={() => setView("setup")}
            >
              Play
            </Button>
            <Button
              size="xl"
              fullWidth
              variant="default"
              className={styles.menuButton}
              onClick={() => setSettingsOpen(true)}
            >
              Settings
            </Button>
            <Button
              size="xl"
              fullWidth
              variant="default"
              className={styles.menuButton}
              onClick={() => navigate("/rules")}
            >
              Rules
            </Button>
          </nav>
        </div>

        {/* ── Ekran konfiguracji nowej gry (Setup_Wizard) ───────────────── */}
        <div
          className={`${styles.setupScreen} ${styles.setupScreenStage}`}
          aria-hidden={view === "menu"}
          inert={view === "menu"}
        >
          {/*
           * Cały kreator (kroki, walidacja, wysyłka /game/new i nawigacja do /game)
           * żyje w `SetupWizard`. Każdy krok to pełnoekranowa scena z własnym paskiem
           * górnym; „Wstecz" na pierwszym kroku wraca do menu głównego (`onExit`).
           */}
          <SetupWizard onExit={() => setView("menu")} />
        </div>
      </div>

      {/* Ustawienia — ten sam panel co w grze (`SettingsModal`), żeby np. tryb
          administratora (szybkie testy) dało się włączyć JESZCZE przed startem gry,
          zanim pojawi się intro. Stan jest współdzielony przez `useSettingsStore`. */}
      <SettingsModal
        opened={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </Box>
  );
}
