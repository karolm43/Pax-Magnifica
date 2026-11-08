// Treść epilogów: karta na frakcję × rodzaj zwycięstwa (honorowe / niehonorowe).
//
// Teksty wklejasz do PLIKU `epilogues.txt` (obok), pod nagłówkami frakcji — instrukcja jest
// na górze tego pliku. Tu tylko parsujemy go przy starcie (Vite `?raw`) i dobieramy epilog.
// Puste pole = ogólny epilog z `GENERIC_*` (`{faction}` → nazwa frakcji), tylko zapychacz.
//
// Format: `## id | Nazwa` otwiera frakcję, `### honorable` / `### dishonorable` otwiera pole,
// akapity rozdziela pusta linia, opcjonalny podpis to linia zaczynająca się od `-- `.

import type { EpilogueChoice } from "@/entities/data/types";
import rawEpilogues from "./epilogues.txt?raw";

export interface EpilogueText {
  /** Akapity epilogu, pokazywane jako przewijana Kronika. */
  paragraphs: string[];
  /** Podpis pod tekstem (np. kronikarz). Brak = domyślny kustosz Kroniki. */
  author?: string;
}

export type FactionEpilogue = Partial<Record<EpilogueChoice, EpilogueText>>;

/** Zamienia treść jednego pola (linie) na akapity + opcjonalny podpis; pusta → undefined. */
function toText(lines: string[]): EpilogueText | undefined {
  const paragraphs: string[] = [];
  let author: string | undefined;
  let current: string[] = [];
  const flush = () => {
    if (current.length > 0) paragraphs.push(current.join(" "));
    current = [];
  };
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === "") flush();
    else if (trimmed.startsWith("-- ")) {
      flush();
      author = trimmed.slice(3).trim();
    } else current.push(trimmed);
  }
  flush();
  return paragraphs.length > 0 ? { paragraphs, author } : undefined;
}

/** Parser `epilogues.txt` → `{ id frakcji: { honorable?, dishonorable? } }`. */
export function parseEpilogues(source: string): Record<string, FactionEpilogue> {
  const result: Record<string, FactionEpilogue> = {};
  let factionId: string | null = null;
  let slot: EpilogueChoice | null = null;
  let buffer: string[] = [];
  const commit = () => {
    if (factionId && slot) {
      const text = toText(buffer);
      if (text) (result[factionId] ??= {})[slot] = text;
    }
    buffer = [];
  };
  for (const line of source.split(/\r?\n/)) {
    if (line.startsWith("//")) continue;
    const faction = /^##\s+([^|#\s]+)/.exec(line);
    const slotMatch = /^###\s+(honorable|dishonorable)\s*$/i.exec(line);
    if (slotMatch) {
      commit();
      slot = slotMatch[1].toLowerCase() as EpilogueChoice;
    } else if (faction) {
      commit();
      factionId = faction[1];
      slot = null;
    } else {
      buffer.push(line);
    }
  }
  commit();
  return result;
}

export const FACTION_EPILOGUES: Record<string, FactionEpilogue> =
  parseEpilogues(rawEpilogues);

export const DEFAULT_EPILOGUE_AUTHOR =
  "Mahthom Iq Seerva, Winnaran keeper of the Custodian Chronicle";

const GENERIC_HONORABLE: string[] = [
  "The throne of Mecatol Rex has found its master. {faction} did not merely seize the Empire; they earned it in the open, before the eyes of every rival, and the Galactic Council could find no stain upon the claim.",
  "Even those who fought hardest against them now bend the knee without bitterness. Treaties were kept, promises were honored, and the long peace that follows will be built on trust rather than fear.",
  "Historians of later ages will say that the Dark Years ended not on the day the old powers fell, but on the day a worthy ruler finally sat upon the throne.",
];

const GENERIC_DISHONORABLE: string[] = [
  "The throne of Mecatol Rex has found its master, yet no one in the Council Chamber cheers. {faction} climbed to the Empire over broken oaths and shattered alliances, and every rival remembers the knife in the dark.",
  "The crown is theirs by force and by cunning, and the Galactic Council will bow because it must, not because it wishes to. Whispers of betrayal already travel the long lanes between the stars.",
  "The Custodians record the victory as it was: complete, undeniable, and bitterly remembered. A throne won this way must be defended for the rest of its days.",
];

/** Epilog dla frakcji i rodzaju zwycięstwa (z `epilogues.txt` albo ogólny zapychacz). */
export function getEpilogue(
  factionId: string,
  factionName: string,
  choice: EpilogueChoice,
): EpilogueText {
  const own = FACTION_EPILOGUES[factionId]?.[choice];
  if (own) return own;
  const template =
    choice === "honorable" ? GENERIC_HONORABLE : GENERIC_DISHONORABLE;
  return {
    paragraphs: template.map((p) => p.replaceAll("{faction}", factionName)),
    author: DEFAULT_EPILOGUE_AUTHOR,
  };
}
