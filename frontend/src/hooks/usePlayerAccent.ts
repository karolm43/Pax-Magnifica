import { useEffect } from "react";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";

type Rgb = { red: number; green: number; blue: number };

/** Granice „stonowania”: nasycenie i jasność akcentu w HSL. */
const MAX_SATURATION = 0.5;
const MIN_LIGHTNESS = 0.5;
const MAX_LIGHTNESS = 0.68;

function hslToRgb(h: number, s: number, l: number): Rgb {
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h * 12) % 12;
    return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))));
  };
  return { red: f(0), green: f(8), blue: f(4) };
}

/**
 * Stonowany akcent z koloru gracza: ten sam odcień, nasycenie obcięte do 50%, jasność
 * w paśmie 50-68% - neonowy róż czy czysta czerwień nie krzyczą, a czarny/szary gracz
 * dostaje jasny grafit (akcent musi być widoczny na ciemnym tle).
 */
export function mutedAccentRgb({ red, green, blue }: Rgb): Rgb {
  const r = red / 255;
  const g = green / 255;
  const b = blue / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  let h = 0;
  let s = 0;
  if (d > 0) {
    s = d / (1 - Math.abs(2 * l - 1));
    if (max === r) h = ((g - b) / d + 6) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h /= 6;
  }
  return hslToRgb(
    h,
    Math.min(s, MAX_SATURATION),
    Math.min(Math.max(l, MIN_LIGHTNESS), MAX_LIGHTNESS),
  );
}

/**
 * Ustawia `--player-accent-rgb` na <body> z koloru MOJEGO gracza (`useDeskPlayer`: w grze
 * sieciowej moje miejsce). Czyta go motyw „Player color” (styles/playercolortheme.css);
 * pozostałe motywy zmiennej nie używają. Bez gracza zmienna znika (motyw - neutralny łupek).
 */
export function usePlayerAccent() {
  const color = useDeskPlayer()?.color;
  useEffect(() => {
    const rgb = color ? resolvePrimaryRgb(color) : undefined;
    const body = document.body.style;
    if (!rgb) {
      body.removeProperty("--player-accent-rgb");
      return;
    }
    const muted = mutedAccentRgb(rgb);
    body.setProperty("--player-accent-rgb", `${muted.red} ${muted.green} ${muted.blue}`);
    return () => {
      body.removeProperty("--player-accent-rgb");
    };
  }, [color]);
}
