// Tekst lore pisany pismem z gry (czcionka Lazaxian) z efektem „rozszyfrowania".
//
// Stan trzyma hook `useDecode`: tryb (`glyph` = oryginalne pismo, `plain` = czytelny
// tekst), postęp przejścia 0..1 oraz flagę `busy`. Każdy blok tekstu (`DecodedText`)
// wylicza z postępu własny punkt „rozstrzygnięcia" — fala przechodzi blok po bloku od góry
// do dołu, a w obrębie bloku znak po znaku. Przed frontem fali znaki są jeszcze w starym
// kroju i migoczą (część podmieniana na losowe litery), na froncie świeci czerwony
// „kursor", za nim tekst jest już w docelowym kroju. Losowość jest deterministyczna
// (hash z numeru klatki) — render pozostaje czystą funkcją propsów.

import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./GlyphText.module.css";

export type GlyphMode = "glyph" | "plain";

/** Litery podstawiane w migotaniu (tylko te, które pismo ma jako glify). */
const SCRAMBLE = "ABCDEFGHIKLMNOPRSTUVWXYZ";
/** Część osi czasu zajęta na opóźnienia między blokami (reszta = czas jednego bloku). */
const STAGGER = 0.5;
/** Liczba kroków migotania na całe przejście. */
const FLICKER_STEPS = 110;

/** Deterministyczna pseudolosowa liczba 0..1 z ziarna. */
function hash01(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/**
 * Stan i sterowanie przejściem pismo ↔ tekst czytelny. `toggle` uruchamia animację
 * (ignorowany w trakcie trwania poprzedniej). Przy `prefers-reduced-motion` tryb zmienia
 * się natychmiast, bez fali migotania.
 */
export function useDecode(durationMs = 3600) {
  const [mode, setMode] = useState<GlyphMode>("glyph");
  const [progress, setProgress] = useState(1);
  const [busy, setBusy] = useState(false);
  const frame = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    },
    [],
  );

  const toggle = useCallback(() => {
    if (busy) return;
    const next: GlyphMode = mode === "glyph" ? "plain" : "glyph";
    setMode(next);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setProgress(1);
      return;
    }
    setProgress(0);
    setBusy(true);
    const start = performance.now();
    const step = (now: number) => {
      const t = clamp01((now - start) / durationMs);
      setProgress(t);
      if (t >= 1) {
        setBusy(false);
        frame.current = null;
        return;
      }
      frame.current = requestAnimationFrame(step);
    };
    frame.current = requestAnimationFrame(step);
  }, [busy, mode, durationMs]);

  return { mode, progress, busy, toggle };
}

interface DecodedTextProps {
  text: string;
  /** Tryb docelowy (do którego zmierza przejście albo w którym tekst już jest). */
  mode: GlyphMode;
  /** Postęp przejścia 0..1 (1 = zakończone). */
  progress: number;
  /** Numer bloku w kolejności czytania i liczba wszystkich bloków (do fali). */
  index: number;
  total: number;
}

const fontClass = (mode: GlyphMode) => (mode === "glyph" ? styles.glyph : styles.plain);

/** Jeden blok tekstu w trakcie (lub po) rozszyfrowaniu. */
export function DecodedText({ text, mode, progress, index, total }: DecodedTextProps) {
  const previous: GlyphMode = mode === "glyph" ? "plain" : "glyph";
  const offset = total > 1 ? (index / (total - 1)) * STAGGER : 0;
  const local = clamp01((progress - offset) / (1 - STAGGER));

  // Przed falą: stary krój; po fali (albo bez przejścia): docelowy.
  if (progress >= 1 || local >= 1) return <span className={fontClass(mode)}>{text}</span>;
  if (local <= 0) return <span className={fontClass(previous)}>{text}</span>;

  const eased = local * local * (3 - 2 * local);
  const resolved = Math.floor(eased * text.length);
  const tick = Math.floor(progress * FLICKER_STEPS);

  const head = text.slice(0, resolved);
  const frontChar = text[resolved] ?? "";
  const tail = text
    .slice(resolved + 1)
    .split("")
    .map((ch, i) => {
      if (!/[A-Z]/.test(ch)) return ch;
      const flicker = hash01(resolved * 7.3 + i * 13.1 + tick * 3.7) < 0.09;
      return flicker
        ? SCRAMBLE[Math.floor(hash01(i * 5.1 + tick) * SCRAMBLE.length)]
        : ch;
    })
    .join("");
  const front = /[A-Z]/.test(frontChar)
    ? SCRAMBLE[Math.floor(hash01(resolved + tick * 2.3) * SCRAMBLE.length)]
    : frontChar;

  return (
    <>
      <span className={fontClass(mode)}>{head}</span>
      <span className={styles.front}>{front}</span>
      <span className={fontClass(previous)}>{tail}</span>
    </>
  );
}
