/*
 * Menu główne Custodian Engine (ekran tytułowy na „/").
 *
 * Układ jak w dużych grach strategicznych:
 *   - lewa kolumna na przyciemnionym szkle: logo + nawigacja (duże pozycje z podpisem),
 *     główna akcja w złotym gradiencie TI4;
 *   - prawa kolumna: „Recent games" (zapisy z serwera, wczytanie jednym kliknięciem);
 *   - prawy górny róg: profil (dziś „Guest" — konta i historia gier to następny etap);
 *   - stopka: status serwera (lokalny / lobby sieciowe).
 *
 * Gość sieciowy (inny komputer, RULES.md 44.5a) zamiast nawigacji widzi `JoinScreen`.
 * Logika przycisków (otwarcie lobby, okna) zostaje w `StartScreen` — tu tylko widok.
 */
import { useId, type ReactNode } from "react";
import {
  describeSave,
  JoinScreen,
  LoadGameModal,
  useLoadSave,
} from "@/domains/network/LobbyScreens";
import { useSaves, type SaveEntry } from "@/domains/network/useLobby";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import startStyles from "./StartScreen.module.css";
import styles from "./MainMenu.module.css";

/** Ile ostatnich partii pokazuje panel boczny (reszta w oknie „Load game"). */
const RECENT_LIMIT = 4;

export interface MainMenuProps {
  isGuest: boolean;
  onPlay: () => void;
  onLoad: () => void;
  onSettings: () => void;
  onGuide: () => void;
  onRules: () => void;
  /** „Continue" — bieżąca partia jest już wczytana w backendzie, więc tylko wejście do gry. */
  onContinue: () => void;
  lobbyError: string | null;
  loadOpen: boolean;
  onLoadClose: () => void;
}

/**
 * Pozycja nawigacji: duża etykieta + podpis. Nazwa dostępna = SAMA etykieta
 * (`aria-label`), podpis idzie przez `aria-describedby` — lokatory `getByRole(name)`
 * w testach E2E zostają proste („Play", „Load game"…).
 */
function NavItem({
  label,
  caption,
  onClick,
  primary = false,
  disabled = false,
  badge,
}: {
  label: string;
  caption: string;
  onClick?: () => void;
  primary?: boolean;
  disabled?: boolean;
  badge?: string;
}) {
  const captionId = useId();
  return (
    <button
      type="button"
      className={`${styles.navItem} ${primary ? styles.navItemPrimary : ""}`}
      aria-label={label}
      aria-describedby={captionId}
      disabled={disabled}
      onClick={onClick}
    >
      <span className={styles.navLabel}>
        {label}
        {badge && <span className={styles.badge}>{badge}</span>}
      </span>
      <span id={captionId} className={styles.navCaption}>
        {caption}
      </span>
    </button>
  );
}

/** Nagłówek sekcji panelu bocznego (mały, rozstrzelony, bursztynowy). */
function PanelTitle({ children }: { children: ReactNode }) {
  return <h2 className={styles.panelTitle}>{children}</h2>;
}

/** Krótka data zapisu: „dziś 14:05" albo pełna data lokalna. */
function formatWhen(epochSeconds: number): string {
  const d = new Date(epochSeconds * 1000);
  const today = new Date();
  const sameDay = d.toDateString() === today.toDateString();
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return sameDay ? `Today, ${time}` : `${d.toLocaleDateString()} ${time}`;
}

/** Panel „Recent games": ostatnie zapisy poza bieżącą partią (ta jest w „Continue"). */
function RecentGames({ saves, onShowAll }: { saves: SaveEntry[]; onShowAll: () => void }) {
  const { load, loading, loadError } = useLoadSave();
  const recent = saves.filter((s) => !s.current).slice(0, RECENT_LIMIT);
  return (
    <section className={styles.panel} aria-label="Recent games">
      <PanelTitle>Recent games</PanelTitle>
      {recent.length === 0 ? (
        <p className={styles.empty}>No other saved games yet. Finished and paused games appear here.</p>
      ) : (
        <ul className={styles.saveList}>
          {recent.map((s) => (
            <li key={s.name} className={styles.saveRow}>
              <div className={styles.saveText}>
                <span className={styles.savePlayers}>
                  {s.players.length > 0 ? s.players.join(", ") : "Empty game"}
                </span>
                <span className={styles.saveMeta}>
                  {describeSave(s)} · {formatWhen(s.modified)}
                </span>
              </div>
              <button
                type="button"
                className={styles.saveButton}
                disabled={s.broken || loading !== null}
                aria-label={`Load game: ${s.players.join(", ") || s.name}`}
                onClick={() => void load(s.name)}
              >
                {loading === s.name ? "Loading…" : "Load"}
              </button>
            </li>
          ))}
        </ul>
      )}
      {loadError && (
        <p className={styles.error} role="alert">
          {loadError}
        </p>
      )}
      <button type="button" className={styles.linkButton} onClick={onShowAll}>
        All saved games →
      </button>
    </section>
  );
}

/**
 * Profil w prawym górnym rogu. Konta (logowanie, historia gier, statystyki) to następny
 * etap — dziś gracz jest „Guest", a przycisk logowania jest nieaktywny z powodem.
 */
function ProfileChip() {
  return (
    <div className={styles.profile}>
      <span className={styles.avatar} aria-hidden>
        G
      </span>
      <span className={styles.profileText}>
        <span className={styles.profileName}>Guest</span>
        <span className={styles.profileSub}>Local profile</span>
      </span>
      <button
        type="button"
        className={styles.signIn}
        disabled
        title="Accounts are coming soon: profile, game history and statistics."
      >
        Sign in
      </button>
    </div>
  );
}

export default function MainMenu({
  isGuest,
  onPlay,
  onLoad,
  onSettings,
  onGuide,
  onRules,
  onContinue,
  lobbyError,
  loadOpen,
  onLoadClose,
}: MainMenuProps) {
  const { data: me } = useNetworkMe();
  // Zapisy widzi tylko host / tryb lokalny (`/saves` = HostOnly).
  const { data: saves } = useSaves(!isGuest);
  const current = saves?.saves.find((s) => s.current && !s.broken && s.players.length > 0);
  const lobbyOpen = me?.network === true;

  return (
    <div className={styles.layout}>
      {!isGuest && <ProfileChip />}

      <div className={styles.left}>
        <div className={styles.brand}>
          <h1 className={`${startStyles.menuTitle} ${styles.logo}`}>
            <span className={styles.logoLine}>Custodian</span>{" "}
            <span className={styles.logoLine}>Engine</span>
          </h1>
          <span className={styles.logoRule} aria-hidden />
          <p className={styles.tagline}>Twilight Imperium 4 — web game</p>
        </div>

        {isGuest ? (
          <div className={styles.join}>
            <JoinScreen />
          </div>
        ) : (
          <nav className={styles.nav} aria-label="Main menu">
            {current && (
              <NavItem
                label="Continue"
                caption={`${describeSave(current)} · ${current.players.join(", ")}`}
                primary
                onClick={onContinue}
              />
            )}
            <NavItem
              label="Play"
              caption="New game — open a lobby, invite friends or add bots"
              primary={!current}
              onClick={onPlay}
            />
            <NavItem label="Load game" caption="Resume a saved game" onClick={onLoad} />
            <NavItem
              label="Game history"
              caption="Your past games and statistics — requires an account"
              badge="Soon"
              disabled
            />
            <span className={styles.navDivider} aria-hidden />
            <NavItem label="How to play" caption="Interactive guide to the game" onClick={onGuide} />
            <NavItem label="Rules" caption="Living Rules Reference and rulings" onClick={onRules} />
            <NavItem label="Settings" caption="Audio, display and game options" onClick={onSettings} />
            {lobbyError && (
              <p className={styles.error} role="alert">
                {lobbyError}
              </p>
            )}
          </nav>
        )}
      </div>

      {!isGuest && (
        <aside className={styles.right}>
          {saves?.enabled && <RecentGames saves={saves.saves} onShowAll={onLoad} />}
        </aside>
      )}

      <footer className={styles.footer}>
        <span className={styles.status}>
          <span
            className={`${styles.statusDot} ${lobbyOpen ? styles.statusDotLive : ""}`}
            aria-hidden
          />
          {isGuest ? "Connected to host" : lobbyOpen ? "Network lobby open" : "Local server"}
        </span>
        <span className={styles.footerNote}>Unofficial fan project · not affiliated with Fantasy Flight Games</span>
      </footer>

      <LoadGameModal opened={loadOpen} onClose={onLoadClose} />
    </div>
  );
}
