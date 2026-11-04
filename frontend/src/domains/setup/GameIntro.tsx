// Plansza otwierająca grę: pojawia się po „Start gry" (gra jest już utworzona), a przed
// pierwszym przejściem fazy strategii.
//
// Układ (od góry): tytuł „Twilight Imperium" (krój i gradient jak logo menu) →
// przewijający się wolno tekst kroniki (crawl) → rząd frakcji biorących udział w grze
// (portret, nazwa, gracz, człowiek/bot), wyłaniających się po kolei → przycisk „Begin".
//
// Sterowanie: „Skip" / Esc / Enter / Spacja kończą intro w każdej chwili. Intro nie
// zatrzymuje się samo — po dojechaniu tekstu czeka na „Begin", żeby nikogo nie zmuszać
// do pośpiechu. Przy `prefers-reduced-motion` tekst stoi w miejscu (bez crawl).

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { createPortal } from "react-dom";
import { portraitCandidates, useFactionAccent } from "./FactionBackdrop";
import type { IntroPlayer } from "./introPlayers";
import styles from "./GameIntro.module.css";

/** Kolory graczy → CSS (tylko prezentacja; spójne z krokiem „Gracze"). */
const COLOR_SWATCH: Record<string, string> = {
  red: "#d94a4a",
  green: "#49a14a",
  white: "#e8e8e8",
  blue: "#4a7fd9",
  purple: "#9a4ad9",
  yellow: "#e0c23a",
};

/** Prędkość crawl: tyle wysokości okna tekstu przejeżdża w ciągu 1 s (mniej = wolniej). */
const CRAWL_VIEWPORTS_PER_SECOND = 1 / 11;
/** Gdzie (ułamek wysokości okna) zatrzymuje się dolny brzeg tekstu po dojechaniu. */
const CRAWL_REST_FRACTION = 0.62;
/** Czas wygaszenia treści przed przejściem do gry (ms) — zgodny z CSS `.leaving`. */
const LEAVE_MS = 700;

/** Kronika, od której zaczyna się rozgrywka (cytat z gry — oryginał, bez tłumaczenia). */
const CHRONICLE: string[] = [
  "The Twilight Wars continued for centuries, but no race was powerful enough to seize the throne and risk suffering a similar fate as the Emperor. Slowly, the strength of great civilizations failed as their economies crumbled and as knowledge and technology was lost in the destruction and strain of long war.",
  "And so the Age of Twilight ended in a slow whisper. The time that followed, now known as the Dark Years, was a period of economic, cultural, and intellectual collapse. The Great Races retreated into their own small, safe areas of space, abandoning what they could no longer hold by force. After several millennia, the Dark Years came to an end, and a calm but uncertain period of rebuilding began.",
  "As I write this, the Great Races of the galaxy have regained elements of their former strength. Here on Mecatol Rex, the Galactic Council is growing in influence once more, while civilizations new and old, are re-colonizing the neighboring systems abandoned during the Dark Years.",
  "The day will soon come when a new Empire will rise. For the sake of all, may the new Emperor have not only the power to seize the throne, but the strength to conquer the peace. If not, I fear that a sea of desolation will drown us all.",
];

const CHRONICLE_AUTHOR =
  "Mahthom Iq Seerva, Winnaran keeper of the Custodian Chronicle";

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export interface GameIntroProps {
  players: IntroPlayer[];
  /** Wywoływane po zakończeniu (Begin / Skip) i wygaszeniu treści. */
  onFinish: () => void;
}

/**
 * Pełnoekranowa plansza otwierająca. Renderowana w portalu na `document.body`, bo
 * przodkowie kreatora mają `transform` (deck menu), który psuje `position: fixed`.
 */
export default function GameIntro({ players, onFinish }: GameIntroProps) {
  const reduced = useRef(prefersReducedMotion()).current;
  // Czy tekst dojechał na miejsce (pokazuje „Begin").
  const [arrived, setArrived] = useState(reduced);
  const [leaving, setLeaving] = useState(false);
  const finishedRef = useRef(false);

  const finish = useCallback(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    setLeaving(true);
    window.setTimeout(onFinish, reduced ? 0 : LEAVE_MS);
  }, [onFinish, reduced]);

  // Skróty: Esc / Enter / Spacja kończą intro (też w trakcie crawl).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        finish();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [finish]);

  return createPortal(
    <div
      className={`${styles.overlay} ${leaving ? styles.leaving : ""}`}
      role="dialog"
      aria-modal="true"
      aria-label="Game introduction"
    >
      <div className={styles.content}>
        <header className={styles.titleBlock}>
          <h1 className={styles.title}>Twilight Imperium</h1>
          <span className={styles.titleRule} aria-hidden />
          <p className={styles.edition}>Fourth Edition</p>
        </header>

        <Crawl
          reduced={reduced}
          playerCount={players.length}
          onArrived={() => setArrived(true)}
        />

        <ul className={styles.roster} aria-label="Factions in this game">
          {players.map((player, index) => (
            <RosterCard key={player.id} player={player} index={index} />
          ))}
        </ul>

        <div className={styles.footer}>
          {arrived && (
            <button
              type="button"
              className={styles.begin}
              onClick={finish}
              autoFocus
            >
              Begin
            </button>
          )}
        </div>
      </div>

      <button type="button" className={styles.skip} onClick={finish}>
        Skip
      </button>
    </div>,
    document.body,
  );
}

/**
 * Przewijany tekst kroniki. Po zmierzeniu okna i treści wylicza trasę (od dołu okna do
 * pozycji spoczynku) oraz czas z STAŁEJ prędkości, więc tempo nie zależy od długości
 * tekstu ani rozmiaru ekranu. Zmienne CSS `--from/--to/--dur` czyta animacja `crawl`.
 */
function Crawl({
  reduced,
  playerCount,
  onArrived,
}: {
  reduced: boolean;
  playerCount: number;
  onArrived: () => void;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const [route, setRoute] = useState<{
    from: number;
    to: number;
    dur: number;
  } | null>(null);

  useLayoutEffect(() => {
    if (reduced) return;
    const measure = () => {
      const box = boxRef.current;
      const text = textRef.current;
      if (!box || !text) return;
      const h = box.clientHeight;
      const from = h;
      const to = h * CRAWL_REST_FRACTION - text.scrollHeight;
      const speed = h * CRAWL_VIEWPORTS_PER_SECOND; // px / s
      setRoute((prev) => {
        // Pomiar po załadowaniu fontów bywa o piksele inny — nie restartuj animacji.
        if (prev && Math.abs(prev.to - to) < 24 && Math.abs(prev.from - from) < 24) {
          return prev;
        }
        return { from, to, dur: Math.max(8, (from - to) / speed) };
      });
    };
    measure();
    // Fonty (Ambroise/serif) zmieniają wysokość tekstu — zmierz ponownie po ich załadowaniu.
    void document.fonts?.ready.then(measure);
  }, [reduced]);

  const style = route
    ? ({
        "--from": `${route.from}px`,
        "--to": `${route.to}px`,
        "--dur": `${route.dur}s`,
      } as CSSProperties)
    : undefined;

  return (
    <div
      ref={boxRef}
      className={`${styles.crawlBox} ${reduced ? styles.crawlStatic : ""}`}
    >
      <div
        ref={textRef}
        className={`${styles.crawlText} ${route ? styles.crawlRunning : ""}`}
        style={style}
        onAnimationEnd={(e) => {
          if (e.animationName.includes("crawl")) onArrived();
        }}
      >
        <p className={styles.chronicleLabel}>The Custodian Chronicle</p>
        {CHRONICLE.map((paragraph) => (
          <p key={paragraph.slice(0, 24)} className={styles.paragraph}>
            {paragraph}
          </p>
        ))}
        <p className={styles.author}>— {CHRONICLE_AUTHOR}</p>

        <div className={styles.outro}>
          <p className={styles.outroLine}>The Galactic Council convenes.</p>
          <p className={styles.outroLine}>
            {playerCount} {playerCount === 1 ? "power" : "powers"}. One throne.
          </p>
          <p className={`${styles.outroLine} ${styles.outroStrong}`}>
            The Strategy Phase begins.
          </p>
        </div>
      </div>
    </div>
  );
}

/** Karta jednej frakcji: portret (z łańcuchem zapasowym), nazwa, gracz, człowiek/bot. */
function RosterCard({ player, index }: { player: IntroPlayer; index: number }) {
  const accent = useFactionAccent(player.faction.id);
  const sources = useMemo(() => portraitCandidates(player.faction), [player.faction]);
  const [sourceIndex, setSourceIndex] = useState(0);
  const isIcon = sourceIndex === sources.length - 1;
  const exhausted = sourceIndex >= sources.length;
  const swatch = player.color ? COLOR_SWATCH[player.color] : undefined;

  return (
    <li
      className={styles.card}
      style={
        {
          "--accent": accent,
          "--i": index,
          ...(swatch ? { "--player": swatch } : {}),
        } as CSSProperties
      }
    >
      <div className={styles.cardArt} aria-hidden>
        {!exhausted && (
          <img
            key={sources[sourceIndex]}
            src={sources[sourceIndex]}
            alt=""
            className={isIcon ? styles.cardIcon : styles.cardPortrait}
            onError={() => setSourceIndex((i) => i + 1)}
          />
        )}
      </div>
      <div className={styles.cardInfo}>
        <img
          src={`/static/factions/${player.faction.id}.png`}
          alt=""
          className={styles.cardCrest}
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
        <h2 className={styles.cardFaction}>{player.faction.name}</h2>
        <p className={styles.cardPlayer}>
          <span className={styles.cardDot} aria-hidden />
          {player.name}
        </p>
        <p className={styles.cardControl}>
          {player.isBot
            ? `Bot${player.difficulty ? ` · ${player.difficulty}` : ""}`
            : "Human"}
        </p>
      </div>
    </li>
  );
}
