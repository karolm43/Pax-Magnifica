// Portrety, cytaty i lore frakcji — TREŚĆ DO UZUPEŁNIENIA PRZEZ CIEBIE.
//
// ───────────────────────────────────────────────────────────────────────────
// GDZIE CO WKLEJAĆ (wszystko w mapie `FACTION_LORE`, klucz = id frakcji, np. "arborec"):
//
// 1) CYTAT (`quote`) + AUTOR (`quoteAuthor`) — pokazują się POD NAZWĄ frakcji, nad lore.
//    Cytat wklejaj BEZ cudzysłowu — komponent sam otoczy go “ ” (jeśli wkleisz z cudzysłowem,
//    zostanie zdjęty z brzegów). Autor to osobna linia „— Autor", poza cudzysłowem; wiodący
//    myślnik możesz pominąć. Autor pokazuje się tylko razem z cytatem.
//      quote: "Do you hear, flesh-thing?...",
//      quoteAuthor: "Imię lub tytuł autora",
//
// 2) LORE (`lore`) — treść opisu. Możesz podać na DWA sposoby:
//    a) PROSTO jako jeden string (puste linie rozdzielą akapity) — szybkie wklejenie.
//    b) JAKO BLOKI (tablica) — gdy chcesz kontrolować style/podział:
//         lore: [
//           { kind: "paragraph", text: "Pierwszy akapit..." },
//           { kind: "heading",   text: "Dirzuga" },
//           { kind: "paragraph", text: "Kolejny akapit..." },
//           { kind: "quote",     text: "Cytat wyróżniony kursywą." },
//         ]
//       Rodzaje bloków: "paragraph" (zwykły akapit), "heading" (śródtytuł),
//       "quote" (wyróżniony cytat). Łatwo dzielić długi tekst: każdy akapit = jeden
//       blok `paragraph`. Panel sam ostyluje każdy rodzaj.
//
// 3) PORTRET (obrazek postaci) — wrzucasz plik do:
//        frontend/public/faction_portraits/<id>.<ext>
//    np. frontend/public/faction_portraits/arborec.png
//    Obsługiwane rozszerzenia (próbowane po kolei): png → jpg → jpeg → webp.
//    Możesz też podać własną ścieżkę w polu `portrait`.
//
// Brak cytatu / portretu / lore NIE jest błędem — panel pokaże fallback lub ukryje sekcję.
// ───────────────────────────────────────────────────────────────────────────

/** Rodzaj bloku lore — steruje stylem renderowania. */
export type LoreBlockKind = "paragraph" | "heading" | "quote";

/** Jeden blok treści lore (akapit / śródtytuł / cytat). */
export interface LoreBlock {
  kind: LoreBlockKind;
  text: string;
}

/** Lore jako prosty string ALBO jako lista bloków (do dzielenia i stylowania). */
export type LoreContent = string | LoreBlock[];

/** Wpis jednej frakcji. Wszystkie pola opcjonalne. */
export interface FactionLore {
  /** Cytat frakcji — wklejaj BEZ cudzysłowu (dokłada go komponent). Pod nazwą w nagłówku. */
  quote?: string;
  /** Autor cytatu — wyświetlany pod cytatem jako „— Autor", poza cudzysłowem. */
  quoteAuthor?: string;
  /** Opis frakcji: string (akapity po pustych liniach) albo tablica bloków. */
  lore?: LoreContent;
  /** Własna ścieżka portretu (nadpisuje domyślne /faction_portraits/<id>.<ext>). */
  portrait?: string;
}

/**
 * Mapa „id frakcji → cytat / lore / portret". UZUPEŁNIAJ TUTAJ.
 *
 * Przykład pełny (Arborec):
 *
 *   arborec: {
 *     quote: "Wszystko, co żyje, śpiewa w Symfonii.",
 *     lore: [
 *       { kind: "paragraph", text: "On first approach to Nestphar..." },
 *       { kind: "heading",   text: "The Letani" },
 *       { kind: "paragraph", text: "When traveling beyond the reach..." },
 *       { kind: "quote",     text: "The Symphony remembers." },
 *     ],
 *   },
 */
export const FACTION_LORE: Record<string, FactionLore> = {
  // ── Przykład wypełniony (Arborec) — wzorzec do kopiowania dla reszty frakcji. ──
  // Portret: wrzuć frontend/public/faction_portraits/arborec.png (już dodany).
  // Cytat (quote) zostaw lub wstaw oficjalny — uzupełnij, gdy go znajdziesz.
  arborec: {
    quote: "Do you hear, flesh-thing? The harmonies of the Arborec? Your golems of metal and noise and fire have deafened you to the symphony", // ← wstaw cytat frakcji (pojawi się pod nazwą).
    lore: [
      {
        kind: "paragraph",
        text: "On first approach to Nestphar, a first-time visitor may be surprised by the soupy haze that bleeds from the planet's atmosphere like a dusty cloud. This cloud consists of quadrillions of tiny living spores emitted by Nestphar's many Flaah, city-sized floating forests in its stratosphere. The short-lived (and therefore continually resupplied) orbital presence of the Flaah spores allows the Arborec denizens in Nestphar's space-stations and shipyards to remain in continuous symbiotic contact with their planet. The Arborec term for this vital connection, shared among all living things on Nestphar, is best translated as \u201cthe Symphony.\u201d",
      },

      {
        kind: "paragraph",
        text: "When traveling beyond the reach of Nestphar's Flaah spores, and therefore outside connection to the prime Symphony, the Arborec employ the massive Letani. Physically, the Letani are the largest sentient beings yet discovered in the galaxy (each slightly larger than a Sol Elephantus), their bodies resembling a kraken-shaped mushroom crossed with a monstrous carnivorous flower. The Letani are each uniquely capable of embodying a powerful instance of the Symphony (and are therefore closest to an \u201cindividual\u201d within Arborec society) which may act as a harmonic nexus for Arborec organisms in near proximity. All ships in the Arborec fleet are based around the presence of at least one (with some ships as many as five) Letani orchestrating the unity of Arborec lifeforms crewing the vessel. Once a Letani returns to the embrace of Nestphar's prime Symphony, its experiences are reconnected and absorbed into the Arborec, as a data-capsule would be reconnected to its mainframe.",
      },
      {
        kind: "paragraph",
        text: "While surely intelligent and demonstrably capable of crafting impressive technologies, structures, and a sophisticated fleet of interstellar craft, the Arborec's method of communication remains a source of great controversy. Being a race of vegetative and fungal matter, handling its own data transmission and emotive projection through the prime Symphony, the Arborec have never developed any form of visual or auditory communication (concepts which, to this day, remain foreign to them).",
      },

      {
        kind: "paragraph",
        text: "Arborec scientists found the solution to this dilemma in the Sol merchant vessel Dies Opulen. The crew of the Dies Opulen had tragically become infected by Yborin Plague on Maaluk and had later died in deep space. When the derelict ship was found by an Arborec scout, it was determined the cool bodies of the human crew were in perfect condition for an ambitious experiment. The bodies were sent to the great laboratories in Kushin, near the Arborec capital Phara.",
      },
      {
        kind: "paragraph",
        text: "Here, fungal Arzuga cells were attached to the brainstems of the dead humans. It was hoped, when grown under proper conditions, the complex acidic properties of Arzuga would successfully merge the cells with the innate brain-tissue of the deceased subjects, slowly re-stimulating the neural pathways back to life. Then, by injecting photo-voltaic stims into the soft tissues of the dead body, the neurally active Arzuga would spur the soft tissue cells to heal and regrow, effectively reanimating the dead body. Symbiotically attached to the host body, the Arzuga fungi evolved into a new being, one which the Arborec call the Dirzuga.",
      },
      {
        kind: "paragraph",
        text: "The Dirzuga were the missing link between the Symphony and the manifestation of physical communication that the Arborec lacked. Over the following few decades, the Arborec eagerly acquired additional subjects (human bodies seem to work best and are the most frequently used, but Letnev, Winnu, and Xxcha bodies are also commonly used as Dirzuga hosts), establishing a sizable diplomatic and trading corps that have become the basis for the Arborec's interaction with the rest of the galaxy.",
      },
      {
        kind: "paragraph",
        text: "The Arborec insist the host bodies of the Dirzuga are devoid of the expired individuals' consciousness. With a cultural relationship to death rooted in the natural cycle of decomposition and regrowth, the Arborec have little understanding or sympathy for those who vigorously protest against the bodies of their citizens being reused (some use the term \u201censlaved\u201d) in such a manner.",
      },
      {
        kind: "paragraph",
        text: "Ultimately, despite the objections of the dissident races, the Arborec were admitted as a member of the galactic council. The potential wealth of foodstuffs, medicines, and other treasures of Nestphar proved effective in overcoming any objections.",
      },
      {
        kind: "paragraph",
        text: "While the Arborec insist that the past knowledge and experiences of Dirzuga bodies do not persist beyond this reincarnation, there are some who suspect the Arborec do not tell the entire truth. Such theorists can provide many examples in which the Arborec seem to have come upon information, or intimate understanding of other cultures, that seem inexplicable otherwise.",
      },
    ],
  },
};

/**
 * Domyślne ścieżki portretu próbowane po kolei (pierwsza istniejąca wygrywa).
 * Kolejność: png → jpg → jpeg → webp (Twoje pliki to przeważnie png).
 */
export function defaultPortraitCandidates(factionId: string): string[] {
  return [
    `/faction_portraits/${factionId}.png`,
    `/faction_portraits/${factionId}.jpg`,
    `/faction_portraits/${factionId}.jpeg`,
    `/faction_portraits/${factionId}.webp`,
  ];
}

/** Wpis lore frakcji (lub undefined, gdy nie uzupełniono). */
export function getFactionLore(factionId: string): FactionLore | undefined {
  return FACTION_LORE[factionId];
}

/**
 * Normalizuje lore do listy bloków — żeby panel renderował jednolicie.
 * String dzielimy na akapity po pustych liniach (każdy → blok `paragraph`).
 */
export function loreToBlocks(content: LoreContent | undefined): LoreBlock[] {
  if (!content) return [];
  if (Array.isArray(content)) return content;
  return content
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter((part) => part.length > 0)
    .map((text) => ({ kind: "paragraph" as const, text }));
}
