// Paleta kolorów graczy w setupie — wszystkie kolory AsyncTI4 (zwykłe, dwukolorowe
// „split" i specjalne gradientowe), czytane z `entities/data/colors.ts` (zero
// hardkodowania wartości). Backend ma ten sam zbiór w `assets/data/colors/*.json`
// (`src/core/player_colors.py`), a grafiki jednostek nazywają się wg ALIASU
// (`units/lgy_gf.png`), więc w całym setupie kolor jest identyfikowany aliasem.

import { colors } from "@/entities/data/colors";
import type { Color, RGBColor } from "@/entities/data/types";
import { findColorData, getColorValues, toRgb } from "@/entities/lookup/colors";

/**
 * Rodzaj koloru w palecie:
 * - `solid` — jeden kolor,
 * - `split` — kolor podstawowy + czarny/szary (referencje do innych kolorów),
 * - `special` — gradient / wzór dwukolorowy (rainbow, chrome, plaid, …).
 */
export type ColorKind = "solid" | "split" | "special";

export interface PlayerColorOption {
  /** Alias kanoniczny (np. `lgy`, `splitred`, `rbw`) — wartość wysyłana do backendu. */
  alias: string;
  /** Nazwa do wyświetlenia (np. „LightGray”). */
  label: string;
  kind: ColorKind;
}

function kindOf(color: Color): ColorKind {
  if (color.primaryColorRef) return "split";
  if (color.secondaryColor) return "special";
  return "solid";
}

function labelOf(color: Color): string {
  if (color.displayName) return color.displayName;
  return color.name.charAt(0).toUpperCase() + color.name.slice(1);
}

/** Wszystkie kolory do wyboru, w kolejności z danych AsyncTI4. */
export const PLAYER_COLOR_OPTIONS: readonly PlayerColorOption[] = colors.map((color) => ({
  alias: color.alias,
  label: labelOf(color),
  kind: kindOf(color),
}));

/** Etykiety sekcji palety (kolejność = kolejność wyświetlania). */
export const COLOR_KIND_LABEL: Record<ColorKind, string> = {
  solid: "Standard",
  split: "Split",
  special: "Special",
};

export const COLOR_KINDS: readonly ColorKind[] = ["solid", "split", "special"];

/**
 * Domyślne kolory sześciu miejsc (te same, co rogi domowe w backendzie:
 * red, green, lightgray, blue, purple, yellow — w postaci aliasów).
 */
export const DEFAULT_PLAYER_COLORS: readonly string[] = [
  "red",
  "grn",
  "lgy",
  "blu",
  "ppl",
  "ylw",
];

/** Alias kanoniczny dowolnej nazwy/aliasu albo `null`, gdy kolor jest nieznany. */
export function canonicalColor(color: string): string | null {
  return findColorData(color)?.alias ?? null;
}

/** Kolor podstawowy i (opcjonalnie) drugi kolor wzoru — do próbek. */
function swatchRgb(alias: string): { primary: RGBColor; secondary?: RGBColor } | null {
  const data = findColorData(alias);
  if (!data) return null;
  const primary = getColorValues(data.primaryColorRef, data.primaryColor);
  if (!primary) return null;
  const secondary = getColorValues(data.secondaryColorRef, data.secondaryColor);
  return { primary, secondary };
}

/** Tło CSS próbki koloru: jednolite albo ukośny podział na dwa kolory. */
export function colorSwatchBackground(alias: string): string {
  const rgb = swatchRgb(alias);
  if (!rgb) return "#94a3b8";
  if (!rgb.secondary) return toRgb(rgb.primary);
  return `linear-gradient(135deg, ${toRgb(rgb.primary)} 0 50%, ${toRgb(rgb.secondary)} 50% 100%)`;
}

/** Kolor akcentu karty gracza (kolor podstawowy). */
export function colorAccent(alias: string): string {
  const rgb = swatchRgb(alias);
  return rgb ? toRgb(rgb.primary) : "#94a3b8";
}

/** Nazwa koloru do wyświetlenia (alias, gdy nieznany). */
export function colorLabel(alias: string): string {
  const option = PLAYER_COLOR_OPTIONS.find((o) => o.alias === alias);
  return option?.label ?? alias;
}

/**
 * Preferowane kolory frakcji znormalizowane do aliasów i ograniczone do palety.
 * Kolejność z danych frakcji zostaje zachowana (pierwszy = najbardziej preferowany).
 */
export function preferredColorsOf(preferred: readonly string[] | undefined): string[] {
  const known = new Set(PLAYER_COLOR_OPTIONS.map((o) => o.alias));
  const result: string[] = [];
  for (const raw of preferred ?? []) {
    const alias = canonicalColor(raw);
    if (alias && known.has(alias) && !result.includes(alias)) result.push(alias);
  }
  return result;
}
