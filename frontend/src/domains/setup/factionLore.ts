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
    quoteAuthor: "Dirzuga Rophal",
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
  letnev:{
quote:"Hold your fire until the main fleet arrives. Our armada will blot out their sun-when they die, they will die in darkness!",
quoteAuthor: "Baron Unlenn",
lore: [
{
    kind: "paragraph",
    text: "In the third deep of Arc Prime, Vvlos Samrac XVII, the Baron of Letnev, has awaited the Days of Reckoning with ill-contained wroth. Ever since he slit the throat of his father at age 19, Vvlos has presided over a populace as near to revolt as to starvation. The Baron is keenly aware that the shadows may soon leap for his own throat, should he not manage to improve the lot of the Letnev and feed their ambition for glory and conquest.",
  },
  {
    kind: "heading",
    text: "The Quann Conflict & The Embargoes",
  },
  {
    kind: "paragraph",
    text: "When his father burned the ancient papers of submission, in the wake of the Quann Conflict nearly seventy years prior, the old man expected a military response from the Lazax. Such a response would have allowed Vvlos' father to unite the sparring Letnev dynasties, and - more importantly - given him more direct authority over the Cimm Fenn: the powerful Letnev security force whose assassins and operatives infiltrated nearly every echelon of the empire.",
  },
  {
    kind: "paragraph",
    text: "Instead, the intolerable Lazax hit the Barony with a range of cowardly trade embargoes and out-planet asset seizures. Unlike the Sol Federation (who had also abdicated at that time), such measures bit the Letnev deep. Despite its incredible metallurgical wealth, Arc Prime suffered from chronic foodstuff and water shortages, and worse, the unstated ambitions of its warrior nobility.",
  },
  {
    kind: "heading",
    text: "The Fall of Mecatol & Secret Deployments",
  },
  {
    kind: "paragraph",
    text: "Only a few short months ago, by word of the Cimm Fenn masters, Vvlos learned of Sol's assault on Mecatol Rex. In this, Vvlos tasted the day long-awaited. With only months to spare, the Baron wasted no time. As the humans would strike their dagger into the heart of the empire, Letnev raiders would be ready to assault vital neighboring systems. Here they would reap food sources and slaves, bolstering the Letnev engine of war that Vvlos meant to unleash on the galaxy.",
  },
  {
    kind: "paragraph",
    text: "While his ambition far exceeds the conquest of a single planet, Vvlos understands that ceding a trophy such as Mecatol Rex to the humans would be unwise. To counter the Sol power-grab, Vvlos has, with the support of the Cimm Fenn, smuggled hundreds of capable operatives and thousands of Letnev special forces to the surface of Mecatol Rex. Secretly encased in shipping containers, or covertly undercover in Mecatol City, they await the Days of Reckoning. Should the situation warrant additional attention, the Baron has arranged for military transportation to Mecatol Rex by means of the Hacan Gisnada group. Hungry for access to the metals of Arc Prime, the opportunist felines have guaranteed safe delivery of additional Letnev forces despite \"possible objections by third parties\".",
  },
  {
    kind: "quote",
    text: "The days foreseen are surely at hand, and when that hour finally comes, the Baron of Letnev intends to plunge a spear deep into the side of an already wounded galaxy.",
  },

]
  },
  mahact: {
    quote: "KNEEL",
    quoteAuthor: "Airo Shir Aur",
    lore: [
{
kind: "paragraph",
text: "Gene-sorcerers. Mad tyrants. Kings. The Mahact are a primal tale from ancient history. In the distant past, the Mahact dynasties terrorized the galaxy with their infighting and gene-sorcery. They could warp the forms of living beings, compel eternal obedience with a gesture, and turn the biospheres of entire worlds into seething, caustic hells. They unleashed their most vile technologies in war or even in debauched sport, and it seemed, even as their houses crumbled, that their fall might bring down all of civilized space."
},
{
kind: "paragraph",
text: "But in the midst of their orgy of self-destruction, a new Empire rose to challenge them. The Lazax, a young and fiery race, led the effort to destroy the Mahact and restore peace. When the last Mahact King was slain, the Lazax claimed the fruits of their victory, establishing just dominion over the ashes of the Mahact’s kingdoms."
},
{
kind: "heading",
text: "The Fall and the Gate of Acheron"
},
{
kind: "quote",
text: "However, the truth was somewhat more complicated than the Lazax wished anyone to remember."
},
{
kind: "paragraph",
text: "The new Empire did overthrow the Mahact Kings, slaying many of them and claiming the Mahact’s main fortress of Mecatol as their own. However, the Mahact were too powerful to defeat utterly. The last of them retreated into Mecatol, sowing anarchy and chaos in their wake, and leaving agents and sleepers to do their bidding. They fled the galaxy to their original home, the planet of Ixt. This world lay far beyond the furthest wisps of dust on the galactic arms, unreachable except through the great wormhole gate of Acheron. Here, in their ancient fastness, the remaining Mahact plotted their eventual return."
},
{
kind: "paragraph",
text: "The Lazax pursued the foes to the entrance of the gate on Acheron, but every attempt they made to invade Ixt failed. So the young Empire tried a different plan. They studied the gate’s arcane workings, and though they could not destroy it, they could shut it down. Thus, Lazax engineers deactivated the gate and buried its machinery beneath an entire ocean to guarantee that none would ever discover it again. They even purged all nearby worlds of life, turning surrounding space into a wilderness."
},
{
kind: "paragraph",
text: "Without control of the machinery on Acheron, the Mahact could not reopen their gate, or even rip it free and set its endpoint somewhere else in the galaxy. They were trapped on their dying world, overlooking a galaxy that was steadily forgetting their existence. Eventually, the remaining Mahact entered the stasis crypts beneath their dead city, to sleep until the stars burned out around them."
},
{
kind: "heading",
text: "The Awakening"
},
{
kind: "paragraph",
text: "And there they remained, until the Creuss expedition discovered the Acheron gate, opened it, and awoke them."
},
{
kind: "paragraph",
text: "In an instant, the first Mahact saw the Creuss explorers and used arcane techno-rituals to dominate them and summon their ships through the Acheron Gate. Then, having no desire to remain prisoners on Ixt, the Mahact used the gate machinery to rip Ixt free from its star and hurl it into the heart of the galaxy. Never again would they be trapped on their homeworld."
},
{
kind: "paragraph",
text: "Now Ixt sails untethered through the galactic core, and the Mahact survey their former domain. Though there are only a handful of them left, each has the power of eons of techno-sorcery at their fingertips. The remaining Mahact turn to their own holdings, awakening their Tethian bio-factories and assemblers, and summoning their dormant agents and their genetic descendants."
},
{
kind: "paragraph",
text: "The corridors and halls of Ixt’s great city-machines fill with gene-sorcerers’ thrall legions. Immense dreadnoughts have begun to rise from the underground assembler halls to hang in orbit above the planet, ready to march to war."
},
{
kind: "heading",
text: "The Golden Emissaries"
},
{
kind: "paragraph",
text: "As the Mahact began to marshal their forces, a single golden ship appeared in orbit over Mecatol Rex. It descended to the Senate Promenade in the heart of Mecatol City, touching down on the perfectly manicured trile grass lawn. The hatches opened, and four emissaries stepped out. Each was one of the observers the Council had dispatched to the Creuss expedition to Ixt, reported lost by the few survivors who escaped. Now they were robes of gold and steel, and were flanked by hulking Creuss legionaries, whose armor seethed with an ominous crimson glow."
},
{
kind: "paragraph",
text: "They walked into the chambers of the Galactic Senate without fanfare or invitation and stood in the middle of the hall. Before the stunned audience, they announced that they were the emissaries of Verta Auran Oblis, first amongst the galaxy’s rightful race of rulers."
},
{
kind: "quote",
text: "As Oblis was a magnanimous ruler, all those who surrendered immediately would be favored slaves."
},
{
kind: "paragraph",
text: "The emissaries returned to their ship and left the city behind. However, many fear that it is only a matter of time before a golden armada returns to the sky above Mecatol Rex. And when it does, the Mahact will return the world to the center of their kingdom."
}


    ]
  }
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
