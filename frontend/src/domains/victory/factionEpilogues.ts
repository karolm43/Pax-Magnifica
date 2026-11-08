// Treść epilogów: karta na frakcję × rodzaj zwycięstwa (honorowe / niehonorowe).
//
// Epilog pokazuje się w Kronice po głosowaniu (VictoryScreen → etap „chronicle").
// Tekst frakcyjny wpisujesz w `FACTION_EPILOGUES` pod id frakcji (te same id co w
// `factionLore.ts`, np. "arborec", "hacan"). Brak wpisu = ogólny epilog z `GENERIC_*`
// (`{faction}` zastępowane nazwą frakcji). Teksty ogólne to TYLKO zapychacz — projektu,
// nie z gry; podmień je kartami epilogów.
//
// Akapity piszemy po angielsku (spójnie z Kroniką z intra i cytatami frakcji).

import type { EpilogueChoice } from "@/entities/data/types";

export interface EpilogueText {
  /** Akapity epilogu, pokazywane jako przewijana Kronika. */
  paragraphs: string[];
  /** Podpis pod tekstem (np. kronikarz). Brak = domyślny kustosz Kroniki. */
  author?: string;
}

export interface FactionEpilogue {
  honorable?: EpilogueText;
  dishonorable?: EpilogueText;
}

/** Wpisy per frakcja. TU wklejasz teksty z kart epilogów. */
export const FACTION_EPILOGUES: Record<string, FactionEpilogue> = {};

const GENERIC_AUTHOR =
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

/** Epilog dla frakcji i rodzaju zwycięstwa (z wpisu frakcji albo ogólny zapychacz). */
export function getEpilogue(
  factionId: string,
  factionName: string,
  choice: EpilogueChoice,
): EpilogueText {
  const own = FACTION_EPILOGUES[factionId]?.[choice];
  if (own && own.paragraphs.length > 0) return own;
  const template =
    choice === "honorable" ? GENERIC_HONORABLE : GENERIC_DISHONORABLE;
  return {
    paragraphs: template.map((p) => p.replaceAll("{faction}", factionName)),
    author: GENERIC_AUTHOR,
  };
}

export const DEFAULT_EPILOGUE_AUTHOR = GENERIC_AUTHOR;
