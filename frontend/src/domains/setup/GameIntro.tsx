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
import { getFactionLore } from "./factionLore";
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

/**
 * Muzyka tła (`/intro/background.mp3`, 1:50) gra od startu planszy. Crawl jest do niej
 * dopasowany: tekst dojeżdża na miejsce (hasło „Pax Magnifica") dokładnie w chwili końca
 * utworu, więc czas przewijania wynika z długości muzyki, a nie ze stałej prędkości.
 */
const MUSIC_SRC = "/intro/background.mp3";
const MUSIC_SECONDS = 110;
const MUSIC_VOLUME = 0.25;
/** Narrator (`/intro/final.mp3`, 1:35) czyta kronikę; wchodzi 5 s po starcie planszy. */
const NARRATOR_SRC = "/intro/final.mp3";
const NARRATOR_VOLUME = 1;
const NARRATOR_DELAY_S = 5;
/** Start przewijania (s) — MUSI być równy opóźnieniu `--t-crawl-delay` w CSS. */
const CRAWL_DELAY_S = 2.4;
/** Gdzie (ułamek wysokości okna) zatrzymuje się dolny brzeg tekstu po dojechaniu. */
const CRAWL_REST_FRACTION = 0.6;
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

  // Dźwięk: muzyka od razu, narrator razem z początkiem crawl. Brak pliku albo
  // zablokowany autoplay = cisza (intro działa dalej). Cleanup zatrzymuje oba tory.
  const audioRef = useRef<HTMLAudioElement[]>([]);
  useEffect(() => {
    const music = new Audio(MUSIC_SRC);
    music.volume = MUSIC_VOLUME;
    const narrator = new Audio(NARRATOR_SRC);
    narrator.volume = NARRATOR_VOLUME;
    audioRef.current = [music, narrator];
    const play = (a: HTMLAudioElement) => void a.play().catch(() => undefined);
    play(music);
    const timer = window.setTimeout(
      () => play(narrator),
      reduced ? 0 : NARRATOR_DELAY_S * 1000,
    );
    return () => {
      window.clearTimeout(timer);
      music.pause();
      narrator.pause();
      audioRef.current = [];
    };
  }, [reduced]);

  const finish = useCallback(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    setLeaving(true);
    // Dźwięk cichnie razem z wygaszaniem treści.
    const tracks = audioRef.current;
    const startVolumes = tracks.map((a) => a.volume);
    const steps = 14;
    let step = 0;
    const fade = window.setInterval(() => {
      step += 1;
      tracks.forEach((a, i) => {
        a.volume = Math.max(0, startVolumes[i] * (1 - step / steps));
      });
      if (step >= steps) window.clearInterval(fade);
    }, LEAVE_MS / steps);
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
 * pozycji spoczynku); czas = długość muzyki minus opóźnienie startu, więc koniec
 * przewijania pokrywa się z końcem utworu. Zmienne CSS `--from/--to/--dur` czyta animacja `crawl`.
 */
function Crawl({
  reduced,
  onArrived,
}: {
  reduced: boolean;
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
      setRoute((prev) => {
        // Pomiar po załadowaniu fontów bywa o piksele inny — nie restartuj animacji.
        if (prev && Math.abs(prev.to - to) < 24 && Math.abs(prev.from - from) < 24) {
          return prev;
        }
        return { from, to, dur: MUSIC_SECONDS - CRAWL_DELAY_S };
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
        "--t-crawl-delay": `${CRAWL_DELAY_S}s`,
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
          <p className={styles.motto}>Pax Magnifica</p>
          <p className={styles.motto}>Bellum Gloriosum</p>
          <p className={styles.outroLine}>The Strategy Phase begins</p>
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
  // Cytat frakcji z `factionLore.ts` (zapisany bez cudzysłowu; zdejmujemy ewentualne).
  const lore = getFactionLore(player.faction.id);
  const quote = lore?.quote?.trim().replace(/^["“”„«»]+|["“”„«»]+$/g, "").trim();
  const author = lore?.quoteAuthor?.trim().replace(/^[—–-]\s*/, "");

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
        {quote && (
          <blockquote className={styles.cardQuote}>
            “{quote}”
            {author && <footer className={styles.cardAuthor}>— {author}</footer>}
          </blockquote>
        )}
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
