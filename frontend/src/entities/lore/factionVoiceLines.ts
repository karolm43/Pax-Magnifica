// Komunikaty frakcji — KWESTIE DO UZUPEŁNIENIA PRZEZ CIEBIE.
//
// W polu gracza przy planszy jest przycisk z dymkiem. Klik otwiera 9 JEDNAKOWYCH przycisków
// (kategorii) dla każdej frakcji; klik w kategorię wysyła do wszystkich LOSOWĄ kwestię tej
// kategorii z listy Twojej frakcji (dymek nad polem + wpis w czacie). Niczego nie zmienia w grze.
//
// 1) KATEGORIE — `VOICE_CATEGORIES`: zmień `label` (napis na przycisku) albo dodaj/usuń wpisy.
//    Kategoria `quote` jest ZAWSZE pierwsza i bierze cytat frakcji z `factionLore.ts`
//    (pole `quote` + `quoteAuthor`) — jej nie wypełniasz tutaj.
// 2) KWESTIE — `FACTION_VOICE_LINES`: klucz = id frakcji (jak w `factionLore.ts`), potem
//    kategoria → tablica krótkich kwestii (do ~200 znaków). Im więcej, tym większa losowość:
//      sol: { taunt: ["Your fleet is a rounding error.", "Surrender while it is free."], joke: [] },
// 3) `DEFAULT_VOICE_LINES` — kwestie dla WSZYSTKICH frakcji, gdy dana nie ma własnych w kategorii.
//
// Kategoria bez kwestii ma wyszarzony przycisk (po najechaniu: „no lines yet”).

import { FACTION_LORE } from "@/domains/setup/factionLore";

export const VOICE_CATEGORIES = [
  { id: "quote", label: "Quote" },
  { id: "taunt", label: "Taunt" },
  { id: "joke", label: "Joke" },
  { id: "agree", label: "Agree" },
  { id: "refuse", label: "Refuse" },
  { id: "threat", label: "Threat" },
  { id: "thanks", label: "Thanks" },
  { id: "greet", label: "Greet" },
  { id: "plead", label: "Plead" },
] as const;

export type VoiceCategoryId = (typeof VOICE_CATEGORIES)[number]["id"];
type LineBook = Partial<Record<Exclude<VoiceCategoryId, "quote">, string[]>>;

export const DEFAULT_VOICE_LINES: LineBook = {};

export const FACTION_VOICE_LINES: Record<string, LineBook> = {
  arborec: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  ghost: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  hacan: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  jolnar: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  l1z1x: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  letnev: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  mentak: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  naalu: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  nekro: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  saar: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  sardakk: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  sol: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  winnu: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  xxcha: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  yin: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  yssaril: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  keleresa: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  keleresm: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  keleresx: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  argent: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  cabal: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  empyrean: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  mahact: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  nomad: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  naaz: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  titans: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  bastion: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  deepwrought: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  firmament: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  obsidian: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  crimson: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
  ralnel: { taunt: [], joke: [], agree: [], refuse: [], threat: [], thanks: [], greet: [], plead: [] },
};

/** Cytat frakcji z `factionLore.ts` („tekst — autor”), bez ozdobnych cudzysłowów. */
function factionQuote(faction: string): string | null {
  const lore = FACTION_LORE[faction];
  const quote = lore?.quote?.trim().replace(/^[“"]+|[”"]+$/g, "");
  if (!quote) return null;
  return lore?.quoteAuthor ? `${quote} — ${lore.quoteAuthor.replace(/^[—–-]\s*/, "")}` : quote;
}

/** Wszystkie kwestie kategorii dla frakcji (własne, a gdy brak — domyślne). */
export function voiceLinesFor(faction: string | null | undefined, category: VoiceCategoryId): string[] {
  if (!faction) return [];
  if (category === "quote") {
    const quote = factionQuote(faction);
    return quote ? [quote] : [];
  }
  const own = FACTION_VOICE_LINES[faction]?.[category] ?? [];
  const lines = own.length ? own : (DEFAULT_VOICE_LINES[category] ?? []);
  return lines.filter((line) => line.trim().length > 0);
}

/** Losowa kwestia kategorii (lub null, gdy brak). `random` do testów. */
export function pickVoiceLine(
  faction: string | null | undefined,
  category: VoiceCategoryId,
  random: () => number = Math.random,
): string | null {
  const lines = voiceLinesFor(faction, category);
  return lines.length ? lines[Math.floor(random() * lines.length)] : null;
}
