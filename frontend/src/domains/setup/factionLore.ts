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
  /** Kolor wyróżnienia: `red` (czerwień), `dark-red` (przyciemniona). Brak = zwykły. */
  tone?: "red" | "dark-red";
  /** Rozmiar względem reszty: `large` (większy napis) lub `small` (drobny). */
  size?: "large" | "small";
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
  /**
   * Lore napisane w piśmie z gry (czcionka Lazaxian). Domyślnie pokazywane glifami, a
   * przycisk „Przetłumacz" zamienia je na czytelny tekst z efektem „rozszyfrowania".
   * Teksty podawaj WIELKIMI LITERAMI — to zwykły angielski, tylko wyświetlany krojem pisma.
   */
  glyphLore?: boolean;
  /**
   * Krótkie frazy, które tylko dla `glyphLore` na ułamek sekundy „przebijają" przez lore
   * w losowych miejscach (efekt grozy). Pisz WIELKIMI LITERAMI; w trybie glifów są
   * nieczytelne, po „Przetłumacz" czytelne.
   */
  glitchPhrases?: string[];
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
  // ── Obsidian (frakcja pochodna Firmamentu) — lore w piśmie z gry. ──
  // Tekst to transkrypcja fanowska z karty lore: znaczniki ligatur typu „(TH)" zdjęte,
  // uwagi transkrybującego usunięte, nieczytelne fragmenty pominięte. Kolejność: kolumna
  // lewa (góra→dół), środkowa, a na końcu teksty ukośne. `tone` = czerwień z oryginału,
  // `size` = większy/mniejszy krój. Przycisk „Przetłumacz" odsłania treść po angielsku.
  obsidian: {
    quote: "This is the nightmare scenario. Case midnight omega. Mayday mayday mayday",
quoteAuthor:"Keleres Agent Niall, final report",
    glyphLore: true,
    // Frazy „przebijające" przez lore (autorstwa projektu, w tonie karty) — edytuj dowolnie.
    glitchPhrases: [
      "I SEE YOU",
      "DO NOT LOOK AWAY",
      "IT WATCHES",
      "YOU ARE NOT ALONE",
      "EYES IN THE DARK",
    ],
    lore: [
      { kind: "paragraph", text: "HOMEWORLD: A FALSE CONCEPT, COMFORT FOR CHILDREN" },
      {
        kind: "paragraph",
        text: "GOVERNMENTS ARE LIES REPEATED SO OFTEN THEY CREATE THEMSELVES A DELUSIONAL TRUTH",
      },
      {
        kind: "paragraph",
        text: "WHAT LIES BEYOND BEYOND THE VEIL BEYOND THE EDGE? WITHIN THE BLACK OF SLEEP IS WITHIN YOU",
      },
      {
        kind: "paragraph",
        size: "large",
        text: "WHAT IS FEARED BY FEAR ITSELF? WHAT CONSUMES THE ALL-CONSUMING?",
      },
      { kind: "paragraph", tone: "dark-red", text: "EYES IN THE DARK." },
      {
        kind: "paragraph",
        text: "I REMEMBER BEING SANE. I DON'T REMEMBER WHEN IT CHANGED. I SOUND SANE NOW BUT I KNOW THAT I'M NOT. ONE THING I KNOW: THAT THEY CAN ONLY BE CONTEMPLATED BY THE MAD. IT'S THE KNIFE THAT DRAWS ACROSS THE VEIL OF FLESH, THE VEIL OF STARS. IN THE WORLD THAT IS TO BLAME.",
      },
      { kind: "paragraph", tone: "red", text: "BLOOD THAT BLEEDS FROM THE WOUND" },
      {
        kind: "paragraph",
        text: "WHAT IS THE POINT OF A THRONE? LAST IDIOT IN THE KINGDOM OF THE DEAD.",
      },
      {
        kind: "paragraph",
        text: "ENTROPY HAS TEETH, OBLIVION IS THE NATURAL STATE OF ALL THAT LIVES",
      },
      { kind: "paragraph", size: "large", text: "ONE UNIVERSE IS NOT ENOUGH" },
      {
        kind: "paragraph",
        text: "WHAT'S THE POINT OF SANITY IN THE FACE OF THE TRUTH?",
      },
      {
        kind: "paragraph",
        tone: "dark-red",
        text: "THE TRUTH HAS SO MANY EYES SO MANY TEETH",
      },
      { kind: "paragraph", text: "BUBBLING THE BLACK TAR OF THE MEMBRANE" },
      {
        kind: "paragraph",
        text: "THE KNIFE DRAWS ACROSS THE VEIL OF FLESH, THE VEIL OF STARS.",
      },
      { kind: "paragraph", tone: "red", text: "BLOOD THAT BLEEDS FROM THE WOUND" },
      { kind: "paragraph", text: "BUBBLING THE VEIL. THE OLD FILM BURNING." },
      { kind: "paragraph", tone: "red", text: "BLACK TAR" },
      {
        kind: "paragraph",
        size: "large",
        text: "ONE WORLD IS NOT ENOUGH. ONE UNIVERSE IS NOT ENOUGH.",
      },
      {
        kind: "paragraph",
        text: "I DRAW THE KNIFE ACROSS THE VEIL OF STARS THROUGH TO FIND MORE AND MORE AND MORE BUT MORE ALWAYS ENDS IN NOTHING.",
      },
      {
        kind: "paragraph",
        text: "EVERY EXCHANGE OF ENERGY ALWAYS INCREASE ENTROPY. THE UNIVERSE IS A CLOCK AND EVERY TICK WINDS DOWN THIS UNIVERSE. TICK TICK TICK",
      },
      {
        kind: "paragraph",
        text: "BACK OF YOUR MIND. MELDS BIOPLAS BURNS THROUGH. THEY FLASH AND GONE, LIGHT AND DARKNESS. WORLD DRAWS AWAY.",
      },
      { kind: "paragraph", text: "A NEW UNIVERSE TO END." },
      { kind: "paragraph", text: "THE BREAK THROUGH TO THE NEXT, A NEW TOP." },
      {
        kind: "paragraph",
        tone: "dark-red",
        text: "A NEW FEAST THAT LURKS AT THE END OF EVERYTHING",
      },
      {
        kind: "paragraph",
        
        text: "THE KNIFE THAT CUTS THAT CUTS",
      },
       {
        kind: "paragraph",
        
        text: "OF STARS",
      },
    ],
  },

  // ── Przykład wypełniony (Arborec) — wzorzec do kopiowania dla reszty frakcji. ──
  // Portret: wrzuć frontend/public/faction_portraits/arborec.png (już dodany).
  // Cytat (quote) zostaw lub wstaw oficjalny — uzupełnij, gdy go znajdziesz.
  arborec: {
    quote: "Do you hear, flesh-thing? The harmonies of the Arborec? Your golems of metal and noise and fire have deafened you to the symphony", // ← wstaw cytat frakcji (pojawi się pod nazwą).
    quoteAuthor: "Dirzuga Rophal",
    lore: [
      {
    kind: "paragraph",
    text: "On first approach to Nestphar, a first-time visitor may be surprised by the soupy haze that bleeds from the planet's atmosphere like a dusty cloud. This cloud consists of quadrillions of tiny living spores emitted by Nestphar's many Flaah, city-sized floating forests in its stratosphere. The short-lived (and therefore continually resupplied) orbital presence of the Flaah spores allows the Arborec denizens in Nestphar's space-stations and shipyards to remain in continuous symbiotic contact with their planet. The Arborec term for this vital connection, shared among all living things on Nestphar, is best translated as “the Symphony.”",
  },
  {
    kind: "heading",
    text: "The Letani and the Symphony",
  },
  {
    kind: "paragraph",
    text: "When traveling beyond the reach of Nestphar's Flaah spores, and therefore outside connection to the prime Symphony, the Arborec employ the massive Letani. Physically, the Letani are the largest sentient beings yet discovered in the galaxy (each slightly larger than a Sol Elephantus), their bodies resembling a kraken-shaped mushroom crossed with a monstrous carnivorous flower. The Letani are each uniquely capable of embodying a powerful instance of the Symphony (and are therefore closest to an “individual” within Arborec society) which may act as a harmonic nexus for Arborec organisms in near proximity. All ships in the Arborec fleet are based around the presence of at least one (with some ships as many as five) Letani orchestrating the unity of Arborec lifeforms crewing the vessel. Once a Letani returns to the embrace of Nestphar's prime Symphony, its experiences are reconnected and absorbed into the Arborec, as a data-capsule would be reconnected to its mainframe.",
  },
  {
    kind: "paragraph",
    text: "While surely intelligent and demonstrably capable of crafting impressive technologies, structures, and a sophisticated fleet of interstellar craft, the Arborec's method of communication remains a source of great controversy. Being a race of vegetative and fungal matter, handling its own data transmission and emotive projection through the prime Symphony, the Arborec have never developed any form of visual or auditory communication (concepts which, to this day, remain foreign to them).",
  },
  {
    kind: "heading",
    text: "The Dies Opulen & The Dirzuga",
  },
  {
    kind: "paragraph",
    text: "Arborec scientists found the solution to this dilemma in the Sol merchant vessel Dies Opulen. The crew of the Dies Opulen had tragically become infected by Yborin Plague on Maaluk and had later died in deep space.",
  },
  {
    kind: "paragraph",
    text: "When the derelict ship was found by an Arborec scout, it was determined the cool bodies of the human crew were in perfect condition for an ambitious experiment. The bodies were sent to the great laboratories in Kushin, near the Arborec capital Phara.",
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
    kind: "heading",
    text: "Galactic Recognition and Hidden Shadows",
  },
  {
    kind: "paragraph",
    text: "The Arborec insist the host bodies of the Dirzuga are devoid of the expired individuals' consciousness. With a cultural relationship to death rooted in the natural cycle of decomposition and regrowth, the Arborec have little understanding or sympathy for those who vigorously protest against the bodies of their citizens being reused (some use the term “enslaved”) in such a manner.",
  },
  {
    kind: "paragraph",
    text: "Ultimately, despite the objections of the dissident races, the Arborec were admitted as a member of the galactic council. The potential wealth of foodstuffs, medicines, and other treasures of Nestphar proved effective in overcoming any objections.",
  },
  {
    kind: "quote",
    text: "While the Arborec insist that the past knowledge and experiences of Dirzuga bodies do not persist beyond this reincarnation, there are some who suspect the Arborec do not tell the entire truth. Such theorists can provide many examples in which the Arborec seem to have come upon information, or intimate understanding of other cultures, that seem inexplicable otherwise.",
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
  },
  firmament:{
quote:"Asking 'who should rule us?' is overlooking a more important question: 'why have rulers at all?'",
quoteAuthor:"Sharsiss of Druaa",
lore:[
  {
    kind: "paragraph",
    text: "Whether the Firmament is a collection of revolutionary idealists or a sprawling and secretive criminal empire is a matter of perspective. To the Great Powers, the important question is: Who will be the next to inherit the Imperial throne? But the founders of the Firmament dared to ask: Why should there be an Imperial throne at all?",
  },
  {
    kind: "paragraph",
    text: "To these philosophers, diplomats, and soldiers, assuming that empire was the galaxy’s natural state was a monumental error. After all, twenty-four millennia of the Lazax Imperium had led to stagnation, repression, and exploitation. The more the Lazax Emperors had attempted to control their subjects, the greater the resentment. Eventually, this resentment created the Twilight Wars, and how many trillions had died as a result? For over three thousand years the galaxy had been in the grip of the worst dark ages in recorded history, and now with that age overcome, was the best plan really Imperium again, but with someone else in charge?",
  },
  {
    kind: "heading",
    text: "Origins and the Soft Power Phase",
  },
  {
    kind: "paragraph",
    text: "These individuals spoke out against the course they saw their various governments taking. They wrote treatises, published holo-books, and engaged in fiery debates in the halls of power across the galaxy. They proposed a single, pangalactic society, without any of the divisions of the Great Civilizations or the rule of an Emperor, and they were almost universally ignored.",
  },
  {
    kind: "paragraph",
    text: "So, they reached out to one another in search of kindred spirits. They began to meet, and eventually, they began to organize. They chose a name for themselves, the “Firmament,” and pledged loyalty to their new cause.",
  },
  {
    kind: "paragraph",
    text: "At first, the Firmament avoided direct action. Instead they amassed soft power through projects such as restoring lost galactic monuments. They hoped to persuade so many people to join their cause that the Great Civilizations would be forced to listen. But when the Great Civilizations did, their response was framed in terms of mass arrests and “peacekeepers” in riot gear.",
  },
  {
    kind: "heading",
    text: "Sharsiss and the Obsidian",
  },
  {
    kind: "paragraph",
    text: "Then a young Druaa dissident uncovered an ancient artifact on a forgotten world.",
  },
  {
    kind: "paragraph",
    text: "Sharsiss grew up on Druaa, consigned to the lower roles in his society. He grew sick of the “equality” of the Naalu Collective and left as soon as he was able. Sharsiss rose to become a prominent player in the Firmament’s dispersed leadership, and became an obvious choice to lead the latest expedition searching for fragments of the Lazax maps. On distant Oranth XI, Sharsiss found a crashed vault ship. Deep in its hold, the young Druaa uncovered the ships only cargo: a massive sword called the Obsidian. The blade seemed perfectly black, though Sharsiss thought he could make out something stirring in its inky depths. Then he grasped the hilt...",
  },
  {
    kind: "paragraph",
    text: "Sharsiss returned to the Firmament changed. He had been ambitious, but now he was driven. He gathered the cadre leaders and proclaimed that if they wanted to see their dream realized, they would have to take action. The Great Powers already considered them criminals. Why not prove them right? The leadership would form an action committee, and as many members as stars in the sky. And with that power at their disposal, they would become a force to rival the Great Civilizations.",
  },
  {
    kind: "heading",
    text: "Expansion: Cronos and Tallin",
  },
  {
    kind: "paragraph",
    text: "The first step to power was on Cronos. Firmament members emigrated there in large numbers and took on roles as political and business leaders. They crafted a message to their fellow citizens that portrayed Cronos as the key to a bright galactic future with wealth and prosperity for all. The Firmament never needed to fire a shot; the next election cycle saw Firmament members elected to every leadership role in the government.",
  },
  {
    kind: "paragraph",
    text: "Since then, covert and overt Firmament sympathizers have spread to dozens of nearby systems. Sharsiss himself orchestrated a slightly less peaceful takeover of Tallin, which had long been a haven for criminals and pirates from across the galaxy. In addition to strengthening the Firmament’s control over various criminal concerns, Tallin’s leaders have also begun a rapid armament program. New warships leave the spacedocks every week, and hordes of eager volunteers flock to the army recruitment centers on both Cronos and Tallin.",
  },
  {
    kind: "heading",
    text: "Divergence at Thunder's Edge",
  },
  {
    kind: "paragraph",
    text: "Some of the Firmament’s founding members quietly worry about this new militarism, just as they worry that Sharsiss has amassed too much power around himself, and that he never goes anywhere without his blade. They have researched the Obsidian, and found obscure references to a blade that drives its bearers to conquest and destruction. But that does not explain why Sharsiss has begun to take an interest in Thunder’s Edge, or why he has begun to retask assets from the eventual populist uprising on Mecatol Rex to take the newly discovered world.",
  },
  {
    kind: "quote",
    text: "What is so compelling about that strange world when there’s an entire imperium to overthrow?",
  },
]
  },

  // ─────────────────────────────────────────────────────────────────────────
  // SZKIELETY DO UZUPEŁNIENIA — po jednym wpisie na grywalną frakcję (klucz = alias).
  // W każdym: `quote` BEZ cudzysłowu (komponent doda “ ”), `quoteAuthor` sam autor,
  // `lore` jako lista bloków { kind: "paragraph" | "heading" | "quote", text: "..." }.
  // Portret: frontend/public/faction_portraits/<alias>.png. Puste pola = pomijane.
  // ─────────────────────────────────────────────────────────────────────────

  argent: {
    quote: "You tread upon sacred ground. There is no path to atonement for your sins, only swift and merciless defeat.",
    quoteAuthor: "Sakora Aun Navori, Argent Vanguard",
    lore: [{
    kind: "paragraph",
    text: "Few alive today have dealings with the Shikrai. This collection of related avian subspecies lives scattered across a stretch of the galactic rim. Their clutch of worlds is scattered, windswept, and poor, lacking in valuable resources or useful minerals. Their small and technologically backward populations tend to stay out of galactic affairs. Most rightfully dismiss the Shikrai as just one more group of sentients in a galaxy full of life.",
  },
  {
    kind: "paragraph",
    text: "But there is more to the Shikrai than the rest of the galaxy, or even themselves, realize.",
  },
  {
    kind: "heading",
    text: "Debt to the Lazax and the Secret Retreat",
  },
  {
    kind: "paragraph",
    text: "Long ago, Shikrai territory had the misfortune of being the disputed vassalage of two powerful Mahact. These gene-sorcerers fought a vicious internecine war for the avians’ planets, with the Shikrai forced to fight as proxies on both sides. Shikrai partisans fought back against the fight to claim them, until a Lazax battlegroup arrived. A Lazax warlord named Harkor Ibban Tal liberated the Shikrai and personally slew both gene-sorcerers in single combat.",
  },
  {
    kind: "paragraph",
    text: "To pay their debt, the remaining Shikrai immediately allied with Avar and Ylir, which they had abandoned long ago when they set out to colonize the stars. The Lazax erased all mention of the worlds from their newly constructed Hall of Cartography, and the newly founded Argent Flight retreated to their sanctuary to wait... and prepare.",
  },
  {
    kind: "paragraph",
    text: "They would call it the Argent Flight.",
  },
  {
    kind: "paragraph",
    text: "To do so, the Shikrai turned to their ancestral homeworlds of Valk, Avar, and Ylir, which they had abandoned long ago when they set out to colonize the stars. The Lazax erased all mention of the worlds from their newly constructed Hall of Cartography, and the newly founded Argent Flight retreated to their sanctuary to wait... and prepare.",
  },
  {
    kind: "heading",
    text: "The Atharal Gas Torus and the Murmuration",
  },
  {
    kind: "paragraph",
    text: "Valk, Avar, and Ylir are curiousities even in a galaxy full of wonders. The three worlds are barely larger than moons, and share a narrow orbit around the neutron star Phorus and the gas giant Hacial. The unique environment created the Atharal Gas Torus—a ring of breathable air in orbit around Phorus. The three worlds orbit in the center of the ring, and the Shikrai say their winged ancestors used to fly from world to world.",
  },
  {
    kind: "paragraph",
    text: "In the millennia since their return, the Argent Flight has worked hard to colonize the three worlds and the smaller chunks of rock that drift between them. Numerous flocks of Shikrai live throughout the torus. Each flock focuses on a different trade or calling, and any member of the Argent Flight can join or leave a flock as they choose. Their actions are coordinated by the Murmuration, a council of representatives from each flock who direct the Argent Flight from their spindle tower sanctuary on Avar.",
  },
  {
    kind: "paragraph",
    text: "The Murmuration continues to quietly recruit promising members from the various Shikrai worlds, though the population of the Atharal Gas Torus is now large enough to be self-sustaining. It has also developed beyond simply a martial order into a fully functional society. Large-bellied cloud-scoops dive into the atmosphere of Hacial to gather rare gases that are refined into industrial compounds, while the comet-miners of the outer system keep the Atharal Torus well-supplied in fresh water. The Argent Flight has even gene-crafted the massive, zero-gravity trees that live free-floating in the Torus so that they grow edible fruits, and has built mechanical wing-gravs so that its members can soar from planet to planet once more.",
  },
  {
    kind: "heading",
    text: "Holy Crusade Against Ancient Evil",
  },
  {
    kind: "paragraph",
    text: "However, the Argent Flight still remembers its sworn oaths. Millennia of service have seen its duty evolve into something akin to a religion, and the Shikrai see themselves as sacred guardians appointed by the galaxy’s rightful rulers. The various flocks never revealed themselves to the wider galaxy during the Twilight Wars. Instead they fought their own battles in the shadows against the Mahact’s sleeper agents and greedy explorers who ventured too deeply into Shikrai Space. And they succeeded in their task until a new race, the Creuss, sent an expedition past the Tolari Pulsar too large to defeat in combat.",
  },
  {
    kind: "paragraph",
    text: "In the aftermath of the Mahact’s awakening, the Argent Flight has begun to gather its forces. The Murmuration is in accord; the time for secrecy is past. Already, agents move amongst the Shikrai worlds, calling worthy fighters to take the vows of the Flight. In the open-air ship docks of the Atharal Torus, master shipwrights have laid down the keels of sleek, gull-winged destroyers.",
  },
  {
    kind: "quote",
    text: "The Argent Flight knows, now that its ancient nemesis has returned, that it has no choice. It must lead the rest of the galaxy on a holy crusade to finish what the Lazax started so long ago.",
  },],
  },
  saar: {
    quote: "O, Lisis, you whose fate is forever carved. into the backs of the weary. Your spectre is all we see.",
    quoteAuthor: "The Lay of Lisis",
    lore: [{
    kind: "paragraph",
    text: "Few historians dispute that the Saar were the first of the known races to venture into space, but it remains unknown whether it was need or curiosity that drove the otherwise primitive people into such exploration. Their peaceful ways and dispersed civilization never promulgated them to official Lazax recognition. Some scholars have thus called them \"the forgotten race\".",
  },
  {
    kind: "paragraph",
    text: "The tale of the Saar is a tragic one. Historical records are awash with accounts of deliberate planetary expulsions, even massacres, of Saar settlements found on planets colonized by the other races. The musical Saar often chant the \"Lay of Lisis” in memory of the largest known Saar colony prior to Ragh’s Call. After the planet of Lisis was annexed by the Sardakk N’orr, no word came from the great Saar settlement there again. They simply disappeared. In their memory, most Saar females wear a carefully carved silver pendant called the Y’ouf Lisis, or the \"Tear of Lisis\". During the Houw Shanan, the Saar Holy Day, such pendants are given to young Saar women, while Saar cubs throw beetles and insects into a raging fire and the elders howl at the stars with a longing rage.",
  },
  {
    kind: "paragraph",
    text: "Before the Call began, the Saar were scattered across the galaxy, existing at the mercy of other races. On dozens of worlds, Saar could be found living in slums and sublevel cities, working in the most noxious and despicable industries, and making slim sustenance from the scraps of other civilizations. Considered unclean and barely sentient by other races, Saar life was cheap and subject to little justice. With hard work, polluted environments, and no access to proper medical care, the bitter lives of the Saar were often short.",
  },
  {
    kind: "heading",
    text: "The Captain of Hope",
  },
  {
    kind: "paragraph",
    text: "It was in the hopeless middle period of the Dark Years that a single Saar, Ragh Gavar, would forever change the destiny of his people.",
  },
  {
    kind: "paragraph",
    text: "Ragh made his living as the captain of an old scrap metal freighter that flew between Xxehan and Sol, a route that had been in his family for centuries. Despite being a capable trader, Ragh’s passion lay in poetry and the imagination of the pen, in the creation of succinct writings of hope, scrawled on paper scraps during long trade hauls. At his ports of call, other Saar would often congregate before his loading doors so that they might hear his latest verses and tales. Many of his listeners began to call him the \"Captain of Hope\".",
  },
  {
    kind: "paragraph",
    text: "Yet one year, Ragh did not arrive at his destination. His rusty navigation system had finally failed, and Ragh’s ship was lost among the stars. Floating in unknown space, as his ancestors had once done so bravely before him, Ragh prayed that the One Between the Stars would see him and his small crew home.",
  },
  {
    kind: "heading",
    text: "Ragh's Call and the Asteroids of Jorun",
  },
  {
    kind: "paragraph",
    text: "The Call began a few years after Ragh Gavar’s disappearance. Throughout the great expanses of the galaxy, every Saar began to feel within himself an unyielding longing for the stars, and especially for a certain distant place beyond known space.",
  },
  {
    kind: "paragraph",
    text: "Early followers of the Call found its origin in the great asteroid field of Jorun, and here found a small but blossoming Saar colony on the two gigantic asteroids of Ragh and Lisis II. As the Call continued, Saar brethren from across the galaxy continued to arrive at Jorun, together building the infrastructure of civilization and hope for a lost race.",
  },
  {
    kind: "paragraph",
    text: "Years before, Ragh’s ship had crashed in the Jorun. Miraculously, he and his crew had survived, and with great wonder they soon discovered the mineral richness, frozen water, atmospheric caverns, and strange fauna that lay hidden within the endless ocean of rock.",
  },
  {
    kind: "paragraph",
    text: "Yet Ragh was restless in his new home. It is told that the Captain awoke one night from a dream and then bade his crewmates farewell, disappearing into the great network of caverns that lies within the asteroid named after him. Ragh Gavar was never found or heard from again. But less than a month after his disappearance, the Call began. Saar mystics believe that the Captain of Hope has joined the One Between the Stars, and that he at last won forgiveness for the Saar, and has called them to relieve their suffering. They believe that Ragh’s Call has brought them home, that the live-giving rocks surrounding them are the remnants of the ancient Saar planet of origin, and that even in death it is giving its people a second life.",
  },
  {
    kind: "quote",
    text: "For centuries the unified and passionate Saar people have built a formidable home and civilization in the Jorun asteroid field. The Saar have finally found home, and they have found that they are strong.",
  },],
  },
  muaat: {
    quote: "No longer will the Gashlai be shackled by your whims. Be extinguished, now, and know that you have lost.",
    quoteAuthor: "Fire Warden Umbat",
    lore: [{
    kind: "paragraph",
    text: "It was during the early years of the Age of Dusk that Jol-Nar explorers came upon the volcanic planet of Muaat. Scouting for resources beyond the Mahact Plateau, the explorers were amazed by the mineral wealth of their discovery, but they were truly awestruck by the extraordinary qualities of the planet’s fiery inhabitants, the Gashlai.",
  },
  {
    kind: "paragraph",
    text: "The Gashlai were unlike any race known to the Jol-Nar: sentient beings with bodies slowly consumed by a fiery heat. After their conception, the Gashlai cocooning process somehow enables conversion of energy into mass—a process hinted at by scientific theory, but forever thought unattainable on a sub-cosmic scale.",
  },
  {
    kind: "heading",
    text: "Enslavement and the Doolak Plague",
  },
  {
    kind: "paragraph",
    text: "The Jol-Nar benefited greatly from Muaat’s resources, yet they were frustrated in their attempts to replicate the Gashlai cocooning process. Instead, the Gashlai proved useful as slave labor, as the Headmasters transformed the orbit of Muaat into a massive shipyard for their navy. It was here, at the Muaat shipyards, that the construction of the secret Jol-Nar superweapon began.",
  },
  {
    kind: "paragraph",
    text: "The Gashlai suffered tragically under their enslavement by the Jol-Nar, but events of the early Twilight Wars would dramatically change their ill fortune.",
  },
  {
    kind: "paragraph",
    text: "Just after the Twilight Wars erupted, a Jol-Nar expedition party searching for mineral deposits on Muaat became infected by an organism in the Doolak Mountains. The infection developed into a disease later known as the Doolak plague. The covert, yet frequent, traffic between Muaat and the Garian star system allowed for the spread of the virus to the Jol-Nar home worlds.",
  },
  {
    kind: "paragraph",
    text: "The plague became one of the greatest disasters in Jol-Nar history, and only the early research of Gashlai biology allowed the Headmasters to devise a vaccine before the entire Jol-Nar population was destroyed. Before the Jol-Nar could recover from this disaster, their military offensive collapsed, and soon the Headmasters would face the ruthless advance of the Sardakk N’orr.",
  },
  {
    kind: "heading",
    text: "The Uprising and the War Sun",
  },
  {
    kind: "paragraph",
    text: "As the Jol-Nar navy retreated, the Headmasters were forced to call forth their secret weapon at Muaat—an enormous battle vessel called the “War Sun”—was not yet entirely complete, but with their fleets clinging to the defenses of the Saudor system, the Headmasters had no choice but to bring it to bear against the enemy.",
  },
  {
    kind: "paragraph",
    text: "As the Jol-Nar left its Muaat moorings, and as the majority of the remaining Jol-Nar personnel left with it, the Gashlai finally carved their own destiny. Having long schemed against their enslavers, they incinerated the remaining Jol-Nar in the system, capturing their shipyard and every available scientific document left behind by their hated oppressors.",
  },
  {
    kind: "paragraph",
    text: "Not long after their costly victory at Saudor, the Jol-Nar sought to return to their colony at Muaat, but found that all communications with the system had been severed. Exploratory ships sent to Muaat would not return. Though the Headmasters suspected what might have taken place on their old colony, they were unable to return there again.",
  },
  {
    kind: "heading",
    text: "The Embers Ascendant",
  },
  {
    kind: "paragraph",
    text: "Throughout the long Dark Years, the Gashlai prospered. Clad in Ember suits, special body armor shielding the Gashlai from the cold and others from their lethal heat, a large assembly of Gashlai envoys have recently arrived at Mecatol Rex, demanding recognition and representation. The High Fire Warden Sushon Azh has simultaneously sent forth Gashlai ambassadors to all the great races in the distinctive gold-bronze frigates of the Gashlai.",
  },
  {
    kind: "paragraph",
    text: "Yet one such ambassador did not arrive in a frigate. As the Gashlai ambassador assigned to the Jol-Nar sailed past the Garian star and began his approach to Jol, the Headmasters paled in fear. For this representative arrived in a War Sun, a copy of their own ancient designs. The message was not wasted on the Headmasters. Their former slaves had become formidable, and they had not forgotten, nor forgiven the past.",
  },
  {
    kind: "quote",
    text: "Led by the Fire Wardens, the Gashlai are resolved to never be enslaved again. Inside their golden Ember suits they burn with ambition. The Jol-Nar fear what the rest of the galaxy is about to learn: that the Embers of Muaat intend to bring their fire to the furthest reaches of space, burning the unwilling into submission.",
  },],
  },
  hacan: {
    quote: "There is no price too great for the Hacan, no silk too fine, and no war too long. My people will persevere.",
    quoteAuthor: "Hacan Carth",
    lore: [{
    kind: "quote",
    text: "\"For a trader to flourish beyond current successes, he must embrace change. For it is change that originates both source and market, opening the void between them where the merchant prospers. Yet one must beware: despite innovative contracts, monopolizing conditions, or clever manipulation of price and supply, any lucrative exploit between economic attractors will in time lessen, and ultimately close. The wise merchant therefore always must look to the trade winds that favorably replace an existing product with a fresh opportunity.\"\n",
  },
  {
    kind:"paragraph",
    text:"- Excerpt from \"Market Cycles\" by Quieron Roban II"
  },
  {
    kind: "paragraph",
    text: "Through their widespread trade networks, the Hacan leadership have long sensed the impending upheaval in the fabric of the empire. Thus far, it has not overly concerned them; as a general rule, upheaval is not anathema to the general trade, only to certain goods and the pricing of others.",
  },
  {
    kind: "heading",
    text: "Imperial Embargoes and Market Stagnation",
  },
  {
    kind: "paragraph",
    text: "What does concern the Hacan, however, has been the increased Lazax reliance on trade embargoes as punishment to dissenters. Through most of the empire's trading history, the costs of breaching Lazax trade restrictions were sufficient to halt trade pursuits in affected regions. However, in recent decades where no less than three major civilizations had been declared non-fabrica ports of call, the scales were shifting.",
  },
  {
    kind: "paragraph",
    text: "Those broad imperial embargoes against Sol, Jol-Nar, and Letnev had sent a deep chill through the galaxy's commercial activity. For the first time in ages, significant segments of Hacan cargo haulers were sitting idle, and the reduction in transaction velocities had forced the financier tribes to make cuts in both short-term funding, and broader investments, further dampening commercial activity.",
  },
  {
    kind: "heading",
    text: "Agents of Change",
  },
  {
    kind: "paragraph",
    text: "Though the teachings of Roban II embrace the virtue of market change, they are short on guidance for the merchant himself as an active agent of change. The current Quieron, Waech Sla, has concluded the Hacan must become such agents, while staying true to their old creeds whenever possible.",
  },
  {
    kind: "paragraph",
    text: "As the Sol fleet rushed towards Mecatol, it did so relying on Hacan trading fleets for its logistical needs. Yet, to the Federation’s impending surprise, the Hacan does not consider Sol its only customer in the matter of the Mecatol siege. With complete control over shipping routes to the Gul system, and the sole purveyor of supplies to Mecatol's surface, the Hacan are not inclined to turn down lucrative offers from invested parties. In fact, Waech Sla ponders what gains would lie in a greater change; one in which the Hacan took the reins of the empire and led the galaxy to prosperity through commerce.",
  },],
  },
  empyrean: {
    quote: "We see what you are. We see what you are not. There is nothing we do not know.",
    quoteAuthor: "Conservator Procyon",
    lore: [{
    kind: "paragraph",
    text: "Since time immemorial, travelers have told tales of the Empyrean, enigmatic beings who live in the depths of space. The oldest Jol-Nar libraries have references to faceless creatures who sailed the void long before the Hylar left their watery cradle. Winnaran custodians still maintain fragmented historical documents that managed to survive the ancient Sol bombardment and suggest that the Empyrean predate the discovery of supraluminal travel, a technology so old that no race has presented credible evidence that they invented it. If these records are to be believed, the Empyrean have been crossing the vast gulf of space in sublight vessels for tens of thousands of years before the first FTL drives made galactic civilization possible.",
  },
  {
    kind: "paragraph",
    text: "Whether or not this is true, historians agree that whenever a species establishes colonies beyond their homeworld, the Empyrean arrive to observe their progress. They tend to lurk on the edges of star systems, making no effort to announce their presence. They can remain drifting in the outer cometary halos for centuries, occasionally sending unobtrusive probes orbiting through the inner system for closer observations.",
  },
  {
    kind: "heading",
    text: "The Silent Observers",
  },
  {
    kind: "paragraph",
    text: "Though they do not actively avoid confrontations, anthropologists and diplomats who have attempted to establish contact with the Empyrean tend to find them frustratingly noncommunicative. Individual Empyrean tend to avoid answering questions about their purpose in observing the actions of other species, or about themselves or their civilization. Though they are sometimes referred to as the galaxy’s “historians,” nobody knows if the Empyrean keep a unified record of galactic events. If they do, they have not shared it with anyone else.",
  },
  {
    kind: "heading",
    text: "Biology and the Void",
  },
  {
    kind: "paragraph",
    text: "Most of what is known of the Empyrean has been gleaned through direct observation. The most startling fact about them is that they are a species who survive in space. Their ships have no pressurized compartments, and beyond some radiation and debris protection, are completely exposed to vacuum. The Empyrean themselves have no visible sensory organs or orifices, and seem to spend much of their time absorbing starlight with the great leathery wings that protrude from their backs. Their body shape does suggest that they evolved on a planet’s surface, leading some scientists to suggest that their original home may have been largely aquatic. Others believe that at some point in the distant past, the Empyrean were a more traditional avian species who bio-crafted themselves to thrive in the vacuum of space.",
  },
  {
    kind: "heading",
    text: "Patience and Communal Anarchy",
  },
  {
    kind: "paragraph",
    text: "Whatever their origins, most species find interacting with the Empyrean difficult. Communication isn’t a problem—individual Empyrean are able to broadcast radio waves that can be picked up by most standard comms devices—but patience is. The Empyrean act slowly and deliberately, perhaps a consequence of subsisting on the meager solar energy of stars, or possibly because of their extremely long lifespans. They can spend hours or even days contemplating an answer to a single question. In addition, Empyrean society seems to operate as a form of communal anarchy. They make decisions based on the consensus of all Empyrean currently present. They seem cooperative enough that this works, but it does mean governments have no way to negotiate with the “whole of the Empyrean people.”",
  },
  {
    kind: "paragraph",
    text: "They do, however, make some effort to engage with other sentients, such as donning clothing to make guests feel at ease. They also engage in trade for rare metals and trace elements in exchange for new astronomical and scientific information. Most species tend to ignore the Empyrean unless they seek some esoteric knowledge, or the Empyrean approach them first.",
  },
  {
    kind: "heading",
    text: "A Gathering of Black Wings",
  },
  {
    kind: "paragraph",
    text: "In recent years, more and more black-winged Empyrean ships have begun to gather near major trade lanes and on the outskirts of civilized systems. Some free traders have begun to refuse to follow the deep space commerce trails, repeating rumors that ships have begun to vanish in greater numbers, and Empyrean craft have been sighted following lone vessels. One Empyrean ship has even traveled to Mecatol Rex, and individuals who say they speak for the Empyrean have engaged in long meetings with the Winnarans in Mecatol City. Their representatives say they believe the galaxy itself is engulfed by a storm worse than the Twilight Wars of a millennia ago. They maintain that the struggle for the throne will tear the galaxy to shreds, and that none of the rising powers have the mandate or the moral authority to rule over their fellows. Instead, the Empyrean have come to believe that only a truly neutral arbitrator can hope to rule a galactic empire, an arbitrator that already knows all other species better than they know themselves.",
  },],
  },
  sol: {
    quote: "Our enemies consider us children. They think us weak. Show them. Show them what the children of Jord can do!",
    quoteAuthor: "Supreme Admiral DeLouis",
    lore: [{
    kind: "paragraph",
    text: "Nestled in the third orbit of the Sol system lies Jord, the ancestral home of the human race. Few planets can rival Jord’s diversity of climates, seasons and ecology. Much of this wealth is attributed to its enormous moon, which causes dramatic tidal motions in Jord’s oceans, which is thought to be the impetus of its diverse life and weather patterns. Much of Jord’s orbit, as well as its moon, is crowded with stellar traffic from the orbital and lunar space stations. Military ships of the line, bearing the distinctive Sol symbol, are often moored to the bulky military platforms in Jord’s orbit, or to the fleet base Churchill Prima that orbits the reddish fourth planet of the system.",
  },
  {
    kind: "heading",
    text: "The Prolific Diaspora",
  },
  {
    kind: "paragraph",
    text: "The humans themselves represent the most numerous and most diverse species of the galaxy. Since the discovery of the mass-drive, humans have left Jord to explore, and they continue to explore, the distant corners of space. Humans can be found in all corners of the galaxy and seem to demonstrate the greatest variation in intellect and application of skills. Human colonies and settlements can be found everywhere, as can human servants, traders, cartographers, explorers, mercenaries, scholars, construction crews, smugglers, scientists, diplomats, etc. It is commonly recognised among galactic historians that it has been the diversified skills of the human race that has been the determining factor in avoiding annihilation or extinction.",
  },
  {
    kind: "heading",
    text: "Spark of the Twilight Wars",
  },
  {
    kind: "paragraph",
    text: "Of the untold billions of humans that dwell across the galaxy, all of whose ancestors once migrated from the Sol system, most feel no allegiance or kinship to the Sol federation or the humans of Jord. Some feel a traditional friendship, while a few remain loyal to Jord and its policies. Being the last civilisation to be admitted into the galactic council, it is ironic that Sol was the first to openly declare war against the failing empire. It was a Sol fleet that fired the first shot at the Letnev blockade of the Quann wormhole, escalating the minor conflict into the full scale galactic war known as the Twilight Wars.",
  },
  {
    kind: "heading",
    text: "Governance of New Moscow",
  },
  {
    kind: "paragraph",
    text: "The Sol Federation of Nations is governed by the bi-annually elected High Minister, who has the executive control of the economy, budget and Sol military. The executive powers of the High Minister are held in check by three distinct governing houses: The House of Law, The House of the People, and The House of Industry. The four governing bodies of the Federation are all centrally located in the massive metropolis of New Moscow, a bustling center of politics, trade and high culture.",
  },
  {
    kind: "paragraph",
    text: "The current High Minister, Salvador Tao, is preparing for a new age the he knows is rapidly evolving before him. He is eager to expand the official colonisation of Sol once more, especially to the old colonies of Centauri, Gral and Quann. He knows the balance of power is shifting and that the universe will soon be governed under one empire. The High Minister will make sure that his Federation will prevail during the coming power struggle and inevitable war.",
  },
  {
    kind: "quote",
    text: "Already the Sol fleet awaits his orders to strike nearby systems. Soon the human destiny will be fulfilled, and the distant suns theirs to command.",
  },],
  },
  ghost: {
    quote: "We do not mean to offend the honored ambassador. We mean only to imply that should his ship attempt to pass through the gate, it will not return.",
    quoteAuthor: "Emissary Talvra",
    lore: [{
    kind: "quote",
    text: "They’re ghosts. Frightful tales whispered to children by night cycle lamps. Dread accounts told to fellow sailors in the humming darkness of long-haul freighters.",
  },
  {
    kind: "paragraph",
    text: "Even now, in our growing enlightenment, when we know so much more about the Shaleri passage and its strange inhabitants, the sheer differentness of the Shaleri and its Ghosts seduces such tales to persist.",
  },
  {
    kind: "paragraph",
    text: "An almost endless variation of hearsay and rumor can be found on the topic of the Creuss anomaly. Rare records of purported fact are, at best, of irregular verifiability. While not a respected sociological study, what is truly known of the Shaleri remains infinitely smaller than the abundance of myth that clouds its past.",
  },
  {
    kind: "heading",
    text: "The Mystery of \"Bad Space\"",
  },
  {
    kind: "paragraph",
    text: "For millennia, space in proximity of the Shaleri anomaly has been mistrusted and avoided by spacelabers. Despite the undeniable historic universality in avoiding this region, few concrete explanations have been made as to the reason for such aversion. Some simply denote the area as “high risk.” Others conjecture that the area elbs with “unknown radiation.” Regrettably, most navigation records simply refer to the Shaleri region as “bad space”—the superstitious space-faring analogy of “here be dragons.”",
  },
  {
    kind: "paragraph",
    text: "What is known for sure is that Shaleri space has over time been responsible for an unusually high number of missing vessels. An extraordinarily high number, in fact. For such a high proportion of lost traffic the absence of distress beacons, message capsules, or any signs whatsoever of the missing ships has been described in official records as “disturbing.” It is perhaps more aptly described, using a favored term of sailors and storytellers, as spooky.",
  },
  {
    kind: "paragraph",
    text: "The mystery of the Shaleri region grows further and deeper than just that of missing spaceships. Among crews who have safely made journeys through the region, there are records of strange equipment malfunctions, bad dreams, and sudden illnesses. There are accounts of purported “sightings,” eldritch encounters with beings described as strange fibrous clouds of energy. While such accounts may have been dismissed in the past as the fantasies of oxygen-deprived sailors, the hindsight of the galaxy’s recent association with the Ghosts places these reports in a more credible light.",
  },
  {
    kind: "heading",
    text: "First Contact and the Creuss Gate",
  },
  {
    kind: "paragraph",
    text: "There are several trade routes that when traced through rather than around Shaleri space will save the traveler substantial time and fuel. It follows, therefore, that willingness to brave its dark reputation has come with substantial profit for those captains who have dared to travel in this “bad space” and returned to tell the tale. It was in pursuit of such profit that the Mentak frigate Entropic undertook its fifth journey through Shaleri space.",
  },
  {
    kind: "paragraph",
    text: "The Entropic had been traveling through Shaleri space for three days when it was interdicted by three formidable vessels of unknown origin. The vessels, each the size of a Mentak battlecruiser, were of grey lob- stered steel, their surface intricately inscribed with interweaving runic latticework. It is this meeting between the Entropic and the Creuss warships that is marked as First Contact between the Ghosts of Creuss and a member race of the galactic council.",
  },
  {
    kind: "paragraph",
    text: "It is not known why the beings that dwell within the Shaleri anomaly (now commonly called the “Creuss Gate”) chose to reveal themselves during the early Years of Awakening. Perhaps they’d finally learned progress had finally propelled them into the greater universe? A more ominous possibility, one favored by storytellers, is that the Ghosts of Creuss have come forth for some sinister purpose yet to be revealed.",
  },
  {
    kind: "heading",
    text: "Ethereal Nature and Runic Armor",
  },
  {
    kind: "paragraph",
    text: "As beings of energy and light, the Ghosts certainly can be placed among the strangest of the known races. The famous historian Merean Barqan described them as “ethereal luxyscapes souls.” As their forms do not remain visible outside the strange gravity of the Creuss itself, the Ghosts garb themselves in intricate metalwork. Only does the armor stabilize the Ghosts, but its tangible shape places members of the other races more at ease in their presence. Individual Creuss can be discerned from one another by the unique design of their helmets, which, like their ships, are intricately carved with runes.",
  },
  {
    kind: "paragraph",
    text: "The Ghosts of Creuss have drawn themselves to be perfectly civilized, polite, and amasters of many strange sciences and materials. Yet, they’re also regarded as exceptionally secretive, ritualistic, and prickly on a wide range of matters. It is generally undecided whether their behavior is one to be expected of a race so recently introduced to the material galaxy, or whether there are signs that something more ominous lurks beneath their brooding metal helmets.",
  },],
  },
  l1z1x: {
    quote: "You do not know the meaning of time. You do not comprehend the infinite. Your ignorance is surpassed only by your irrelevance.",
    quoteAuthor: "Diplomat 2RAM",
    lore: [{
    kind: "paragraph",
    text: "It has been 13 years since the Hacan trader Zollar was lost, its final desperate broadcast intercepted by a Yssaril outpost near the Mahact asteroid fields. The last transmission of the Zollar told a grim story. After leaving Moll Primus in the Mahact region, its navigation equipment failed. The crew found themselves lost far beyond the remote borderlands. After nearly two weeks adrift in deep space, the crew’s joy soon turned to terror. The warship closed, bringing its broadside cannons to bear on the helpless freighter. The Hacan captain was able to send a final emergency broadcast before his ship was destroyed.",
  },
  {
    kind: "heading",
    text: "The Cybernetic Claimants",
  },
  {
    kind: "paragraph",
    text: "No longer at the disappearance of the Zollar, a mighty alien fleet appears on the outskirts of Yssaril space. From that fleet, small delegations of representatives travels to Mecatol, submitting an ancestral claim to the Imperial Throne. They claim to be the true remnants of the ancient Lazax, now calling themselves the L1z1x (“THE Won Zee Won Ex”). Grisly to behold, they resemble the Lazax, but utterly changed, their bodies almost entirely overtaken by invasive cybernetic implants.",
  },
  {
    kind: "paragraph",
    text: "The Winnaran custodians are deeply divided over the issue. Some claim that the L1z1x are not the ruling race, but a new and potentially dangerous hybrid. Other Winnarans argue that the Lazax have returned, in unexpected form, but returned nonetheless, and that their custodianship is over.",
  },
  {
    kind: "paragraph",
    text: "A Winnaran observer has been allowed to visit the L1z1x home world, called “0.0.0” by its inhabitants, or “Null” by most others. The observer has not yet returned, and the L1z1x remain a largely unknown entity. What little is known of them has been provided by the L1z1x themselves, or obtained from a few old records provided by the Jol-Nar Regents.",
  },
  {
    kind: "heading",
    text: "The Diaspora of Ibna Vel Syd",
  },
  {
    kind: "paragraph",
    text: "From the Hylar records and from the L1z1x claim, it has been inferred that the L1z1x history started during the final days of the Lazax. It was less than a year before the great bombing of Mecatol that a councilor to the Emperor by the name of Ibna Vel Syd saw the impending doom. The Emperor and his other councilors refused to listen to Ibna’s dire warnings. Soon Ibna grew frustrated with their myopia. Although the Lazax navy was clearly failing, although droves of systems were daily joining the three rebellions, although trade had entirely failed, and food supplies on Mecatol were running out, the Emperor and his cabinet simply could not comprehend that their birthright, their empire, could possibly fall.",
  },
  {
    kind: "paragraph",
    text: "Refusing to share the fate of his liege, Ibna Vel Syd began secretly planning a furtive diaspora for his own family and the few thousand Lazax who shared his fears. With him, Ibna sought to bring the pillars of Lazax culture, technology, and knowledge. He even managed to persuade a small group of Hylar scientists to join him, recognizing that the Hylar’s skill was instrumental to the underlying technology of the empire.",
  },
  {
    kind: "paragraph",
    text: "Then, on a fateful night during the seventy-second year of the Twilight Wars, Syd, left the great spaceport of Mecatol City. Below him, the great Hall of Cartography burned. So fearful had Ibna been of discovery and persecution by the Lazax’s enemies that he had engineered the destruction of any record that could possibly identify his secret destination: a cold but adequate planet orbiting the small star Hylar, far beyond the borderlands.",
  },
  {
    kind: "heading",
    text: "Prophecy and Steel",
  },
  {
    kind: "paragraph",
    text: "It is guessed that the colony, struggling to survive, started to rely almost exclusively on technology to assist them in their hardships. Presumably helped by the small contingent of Hylar, technology crept into their lives and bodies, until they became almost indistinguishable from it.",
  },
  {
    kind: "paragraph",
    text: "It is rumored that Ibna Vel Syd still leads his people, encased in eldritch technology that keeps his ancient body alive. Whether the L1z1x are guided by the wisdom that saved them or by the insanity that destroyed the famed Hall of Cartography, it is not known. Behind their vacant red eyes lies both a tragic melody and a terrible malevolence.",
  },
  {
    kind: "quote",
    text: "It seems certain that the return of the Lazax will wash across the galaxy like a tide of prophecy and steel.",
  },],
  },
  mentak: {
    quote: "One people. One mind. One destiny. We will rise above the pit they have thrown us in.",
    quoteAuthor: "Erwan Mentak, Founder of the Coalition",
    lore: [{
    kind: "paragraph",
    text: "Beyond the Mahact Plateau, part of the borderlands and the old star route known as the Passage of Tears, lies distant Moll Primus with its three tiny moons. The young planet is predominantly covered by extensive plains of the orange meet grass and sprinkled with a million lakes. Sharp youthful mountains pierce the heart of many of its continents, their icy mountain streams giving life to steep lush mountain valleys, where green fruitful trees and flowers grow in colorful contrast to the orange plains.",
  },
  {
    kind: "heading",
    text: "The Penal Colony and the Passage of Tears",
  },
  {
    kind: "paragraph",
    text: "Although rich for exploitation, the remoteness of Moll Primus allowed the planet to go without organized colonization by the Lazax for thousands of years after its discovery. After the failed Gandar rebellion, however, the Lazax started to use the planet as a penal colony, a distant prison, for the worst offending political dissidents and other criminals from all races. Exile to Moll Primus meant a long journey in the bowels of a prison freighter along the Passage of Tears, a winding dark journey around the treacherous gravity wells of the Mahact Plateau. Only the remote planet Hope’s End lies farther than Moll Primus on the Passage of Tears. Once on Moll Primus, prisoners were assigned to manual labor under the supervision of one of the regional planetary Governors. The Governors of Moll Primus mostly consisted of Lazax politicians or servicemen fallen into disgrace. An assignment to Moll Primus was as much a sentence to a Lazax public career as it was a prison for its population. Thus, the Governors were often incompetent, cruel, and bitter individuals. Although the planet itself was quite pleasant, even considered beautiful, its prisoner population was tortured, malnourished, and forced to battle small-scale wars against the population of neighboring Governors.",
  },
  {
    kind: "heading",
    text: "Rebellion and Erwan Mentak",
  },
  {
    kind: "paragraph",
    text: "Then, after more than 800 years, the Twilight Wars began. As the empire crumbled, as the supply ships and supervision from Mecatol Rex became infrequent and finally failed, the Governors panicked. Some fled the planet overnight with their entire households. Others perished in the inevitable prisoner revolts that followed. Before the Twilight Wars had subsided, Moll Primus was free. Some of its most recent prisoners soon left, but for most of its mixed-race population, Moll Primus was home. After the united rebellion against the Governor wardens, a brief period of infighting among the different regions followed. A single human, Erwan Mentak, soon brought the regions together in a final peace, and before he died, prosperity.",
  },
  {
    kind: "heading",
    text: "The Table of Captains",
  },
  {
    kind: "paragraph",
    text: "Today, Moll Primus is governed by the Table of Captains, elected leaders from each region. Among them a single leader is chosen every ten cycles and granted the honorary title Erwan’s Hand or \"the Hand” in short. Helped by their Hylar brothers, the coalition has made great progress in advancing their technological status. Metals mined from Moll Primus’s moons, various products made from the rich meet grass, income from “special\" fleet excursions, and the hard work of its population has slowly formed the strong economic backbone of a proud civilization.",
  },
  {
    kind: "quote",
    text: "Although publicly denied by Mentak ambassadors, the Mentak employ a vast pirating fleet which wreaks havoc among merchant shipping lanes and smaller military convoys. Although now an educated culture and civilization in their own right, the Mentak people have never forgotten their roots as rogues and usurpers. Every Mentak feels an historical need for revenge: revenge against a galaxy that shipped their ancestors to torture and rot on Moll Primus centuries ago. The Table of Captains has given their Hand a clear mandate: to scheme, pillage, and conquer until the ruled are rulers and the enslaved are emperors.",
  },],
  },
  naalu: {
    quote: "You insult me, ssskinling. Ze monstrosity you suggest-ze Druua, we are not capable of such cruelty. Purge zis madness from your mind and leave zis world.",
    quoteAuthor: "Q'uesh Sish",
    lore: [{
    kind: "paragraph",
    text: "It was not until the middle of the Twilight Wars that the Naalu civilization made itself known to the rest of the galaxy. Their system, dominated by the white star Maliac, had remained suspiciously undetected by the empire, despite being surrounded by wealthy systems whose recorded history predates even the Lazax. After a period of sheer astonishment, stellar cartographers and historians began suspecting manipulation by the Naalu themselves. After researching old records, investigators found a remarkably high number of missing ships incidents in that sector and an even more incriminating number of ships found stranded in space, their crews suffering from deep space memory loss. Some scientists (the most vociferous of whom had died amidst questionable circumstances) have indicated that records exist indicating a great number of Yssaril ships passing into Maliac’s area of space, but no records of any derelict or amnesic Yssaril crews have ever been recorded.",
  },
  {
    kind: "heading",
    text: "Telepathic Mastery and Secret Pacts",
  },
  {
    kind: "paragraph",
    text: "The Naalu, it was later discovered to the horror of their neighbors, are highly telepathic and armed with technology and weapons that redirect, manipulate, or damage the neuron impulses guiding the brains of all major known races.",
  },
  {
    kind: "paragraph",
    text: "A secret prior relationship between the Yssaril Guild of Spies and the mind-bending Naalu goes a long way in explaining how the home worlds, a seemingly isolated civilization claiming no prior contact with the rest of the galaxy, developed premium civilian and military technology similar, and in some cases superior, to the rest of the galaxy.",
  },
  {
    kind: "paragraph",
    text: "Soon after the appearance of the Naalu, several of the great races, sensing the potential of a powerful new ally in explaining how the home worlds, a seemingly isolated civilization claiming no prior contact with the rest of the galaxy, developed premium civilian and military technology similar, and in some cases superior, to the rest of the galaxy.",
  },
  {
    kind: "heading",
    text: "The Illusion of Druaa and the Plight of Maaliak",
  },
  {
    kind: "paragraph",
    text: "Despite originating on the dark and nondescript planet Maaliak, the Naalu have taken the breathtakingly beautiful Druaa as their home world. Most Naalu will scoff at any mention of their Malak heritage, and recent Naalu generations often seek to root out even hard scientific evidence which indicates that their proud, stoic race originated from any planet other than the scenic Druaa—especially the striking bogs and mist-plains of Maaliak.",
  },
  {
    kind: "paragraph",
    text: "The Druaa seldom communicate with each other by speaking. Their telepathic communication is more effective, facilitates emotional as well as intelligent understanding, and has allowed the collective to prevent larger internal wars, which in turn has spurred their rapid advance in culture, technology (assisted by the Yssaril), and the creation of the Naalu fleet and military might. Unless speaking to off-worlders, the Naalu use their voices only for their music — hauntingly alluring arias of melodic hissing.",
  },
  {
    kind: "paragraph",
    text: "The Naalu have kept the pristine beauty of their crystal cities and Druaa’s environment intact by locating most of their heavy industries on Maaliak. These industries are manned by the Maalish, a low-sentient marshland race enslaved by the Naalu to work in the great iron-extraction plants, underground gas mines, and on the thousands of rodent farms. Raw materials are promptly shipped to Druaa, stored in massive underground warehouses, and distributed to the Druaa cities by airborne gliders.",
  },
  {
    kind: "heading",
    text: "Quesh Sish and the Great Plan",
  },
  {
    kind: "paragraph",
    text: "The leader of the Naalu collective is always female, as most Naalu leaders and off-world representatives are female. For the last decade, the tall red-scaled Quesh Sish has ruled the collective from her palace in the shining crystal city of Eershian. The beautiful, sleek spaceship of the Naalu patrol Maaliak’s outer borders, while Naalu troops train and muster on Druaa’s two moons. With her Nefesh, a rare crystal radium device, Quesh sees the minds of the other races. She smiles at the knowledge, and with her, the collective Naalu leaders smile, sensing the knowledge in her mind and relishing the sweet poison of her thoughts. The great plan of the collective is about to take its final shape. Long have the Naalu observed the chaos and ugliness of the other races from a distance. The time nears that the beauty of Druaa must bring forth the borders of the galaxy.",
  },
  {
    kind: "quote",
    text: "The time now nears when the rest of the galaxy will know the tranquility, order, and the true beauty of the Naalu. They will submit to that beauty… or be destroyed.",
  },],
  },
  naaz: {
    quote: "For too long the galaxy has squabbled over the bones of our predecessors. It's time for something new.",
    quoteAuthor: "Tetrarch Clik",
    lore: [{
    kind: "paragraph",
    text: "The Naaz have had the distinct misfortune of being a species of technological savants who were discovered by other races before they could build their own civilization. In the chaotic aftermath of the Twilight Wars, their world of Naazir was happened upon by scouts from a Winnu corporate-collective. The collective promptly set up an industrial colony on Naazir and began exploiting the talents of the Naaz. This continued until the corporate leaders were charged and prosecuted for their crimes against sentients... at which point a small army of Sol deserters invaded and claimed Naazir as their own.",
  },
  {
    kind: "heading",
    text: "An Alliance of the Downtrodden",
  },
  {
    kind: "paragraph",
    text: "The pattern continued for centuries, with the Naaz barely able to rid themselves of one conqueror before being invaded by the next. Eventually, a network of Naaz rebels gathered enough resources to try a new plan. To get rid of their current overlords (an alliance of Letnev merchant-princes), they would hire an equally downtrodden group of mercenaries—the Rokha.",
  },
  {
    kind: "paragraph",
    text: "The Rokha are a race of felids, distant relatives of the Hacan who once split with their genetic cousins. Their story since the Twilight Wars had also been one of tragedy, forced to become a race of nomad warriors, employed as mercenaries but barred from settling in any civilized system in the galaxy. To the Rokha, the Naaz were just one more in a long line of employers. But that would change.",
  },
  {
    kind: "paragraph",
    text: "The nascent alliance between the Naaz and the Rokha proved successful, driving the merchant princes from their world. However, in the aftermath of the victory, the Naaz did settle where the Rokha did not expect. They offered them the chance to settle on Naazir and join the Naaz in a unified society. Exhausted from centuries of a nomadic life, the Rokha accepted.",
  },
  {
    kind: "heading",
    text: "A Unified Society",
  },
  {
    kind: "paragraph",
    text: "Together, the Naaz-Rokha Alliance proved much greater than the sum of its parts. Not only did the two species complement one another, their shared history as the galaxy’s outcasts drove them to work all the harder together to ensure neither would be taken advantage of again. The two cultures didn’t just co-exist, they merged. Every level of Naaz-Rokha society became an equal partnership, from families (a typical Naaz-Rokha family consists of two Naaz and two Rokha, plus any children from either couple) to government (the Alliance Chamber of Congress is overseen by an executive Tetrarchy of two Naaz and two Rokha who each oversee different portions of Alliance territory). When any elected official steps down, only an official from the other species is allowed to take their place. And when the Alliance terraformed and colonized one of Naazir’s neighboring worlds so that the Rokha could have a homeworld of their own, the population of their new world was equally divided between both species—the same as on Naazir.",
  },
  {
    kind: "heading",
    text: "The Acheron Gateway and Entropic Harvesting",
  },
  {
    kind: "paragraph",
    text: "The Alliance would undoubtedly have been satisfied to build their own civilization and keep the other races from exploiting it. However, the Creuss expedition to Ixt changed their trajectory. Two of the few survivors from that ill-fated adventure were a pair of Naaz scientists. They, along with a few lucky others, were able to escape aboard a Letnev corvette even as the rest of the expedition was captured by the Mahact. Then, as the other survivors reported to the Council, the scientists returned to Naazir with precious readings from the Acheron gateway, as well as the machinery that created it.",
  },
  {
    kind: "paragraph",
    text: "Using this invaluable information as a starting point, the Alliance has discovered a means of creating momentary micro-wormholes into another dimension and tapping the energy released during that process. This “entropic field harvesting” has proven marvelously efficient. Alliance ships and factories now drink deeply from entropic field taps, and the other galactic powers have suddenly been confronted by the reality that two species they long ago dismissed and exploited are now very real players on the galactic stage.",
  },
  {
    kind: "heading",
    text: "A New Claim to the Stars",
  },
  {
    kind: "paragraph",
    text: "As chaos builds around the Mahact return, the Tetrarchy has stood before the Chamber of Congress and announced its intent. The Naaz-Rokha Alliance has already demonstrated that two species can live harmoniously as one.",
  },
  {
    kind: "quote",
    text: "Who better to take control of the present seat of the Imperium and bring that harmonious cooperation to the stars?",
  },],
  },
  nekro: {
    quote: "The final step of all craft. The gate to eternity. A transcendency to a state of being that can only be described as godhood.",
    quoteAuthor: "Mordai, The First",
    lore: [{
    kind: "paragraph",
    text: "On the eve of the Lazax empire’s fall, the legendary councilor Ibna Vel Syd led a small contingent of his people on a secret exodus into unknown space and, in doing so, escaped the massacre of his people that would follow. Only they had the foresight of increasingly extreme technological augmentation did they survive the early years of resettlement. This reliance on technology became the foundation of what would evolve into the vast cybernetic civilization of the L1z1x.",
  },
  {
    kind: "paragraph",
    text: "While the narrative of Ibna’s early struggles are common lore, few know of the much darker struggle that shadows the L1z1x past: the great schism which ravaged their society a thousand years before their belligerent return to known space. The seams of Vel Syd were rapidly accumulating the power needed to return to known space and reclaim their lost empire. Already, detailed plans circulated in the Mindnet that very goal. Then came the madness of Mordai.",
  },
  {
    kind: "heading",
    text: "The Madness of Mordai",
  },
  {
    kind: "paragraph",
    text: "Mordai was the greatest of the L1z1x enhancers. His innovation and foresight made him foremost among the L1z1x elite. He worked tirelessly for the advancement of his society, always using his own body as the first subject for any new brilliant augmentation of his invention. He was meticulous, inspirational, and brazenly ambitious. He believed in the possibility of the perfect existential reality: an apex of the living soul and the helpful machine.",
  },
  {
    kind: "paragraph",
    text: "Unsurprisingly such hubris would meet its nemesis. As Mordai underwent the self-imposed implant of a cortex migrator, the first of several devices leading to his final ascension, something went horribly awry. It assumed that the smallest of software glitches existed in the cortex module, overlooked even by the meticulous Mordai. As the software began to iterate and integrate with Mordai’s neural activity, it began a powerful recursive disease, a virus that would infect Mordai’s sanity. The personality changes in Mordai were subtle at first. A new subtext entered his work. He had come to believe that the conscious machine was the true higher form of being, one more naturally fit to rule the galaxy than the accident of phosphorous chemistry at the primordial heart of biomatter.",
  },
  {
    kind: "heading",
    text: "The Rise of the Nekro",
  },
  {
    kind: "paragraph",
    text: "Mordai began a series of severe operations to excise the biology of his own body, encouraging and coercing his staff and investors to do the same. Mordai’s charismatic preaching soon gained momentum. His growing cadre of followers, calling themselves the Nekro, began clandestine assaults on their unwilling brethren, forcefully submitting them to the removal of living tissue.",
  },
  {
    kind: "paragraph",
    text: "By the time the leaders of the Mindnet came to realize that the Nekro movement had to be stopped, Mordai had completed his transformation into a fully mechanical being: a gibbering arachnid of black metal, mad with recursive corruption and the hunger to perpetuate. The efficiency of the Nekro virus was astounding. Mordai’s body had been rebuilt as a micro-factory, and from it thousands of microscopic insectile machines sprung forth, attaching themselves to any technology in sight, replicating Mordai’s madness with horrible speed.",
  },
  {
    kind: "paragraph",
    text: "Rebuilding themselves to Mordai’s visions, the new machines became reproductive. Perceiving the threat posed by the Mindnet, they quickly began to construct an army with a single terrifying purpose: the utter subjugation of all organic matter.",
  },
  {
    kind: "heading",
    text: "The Schism and the Resurgence",
  },
  {
    kind: "paragraph",
    text: "The war to subdue the Nekro virus was a great setback for the L1z1x. The virus’s numbers were legion and its visage sprung from Mordai’s nightmares. Like scorpion-inspired Defilers to the giant Mordreds, each new Nekro model was more demonic and deadly than the last. Reborn from this evil army were the monstrous Abaddons, moving facilities that ravenously consumed all materials in their path, seamlessly feeding fresh metals to their internal construction facilities.",
  },
  {
    kind: "paragraph",
    text: "This civil war lasted about five years, with the Mindnet ultimately vanquishing the virus. It took the L1z1x nearly five centuries to regain their former strength, and another five to arrive at their current power. With no new Nekro infestation resurfacing for nearly 700 years, the L1z1x came to believe the virus was wiped out forever. Until now.",
  },
  {
    kind: "paragraph",
    text: "Until the time of the recent Nekro resurgence, it is conjectured that a virus-infested orbital satellite must have escaped Null’s gravity during the schism and vanished undetected into deep space. Here, it must have traveled silently for years until it was pulled into a mineral rich planet somewhere at the edge of the galaxy. Left alone to its own devices, the virus was able to adapt and replicate again.",
  },
  {
    kind: "paragraph",
    text: "Some will seek to understand and find common ground with the Nekro, preaching tolerance or the inherent value of all life. But those who have seen the devastated systems absorbed by the resurgent Nekro know that while angels remain a fantasy of the hopeful, out of the darkness have come demons.",
  },
  {
    kind: "quote",
    text: "And in their wake follows blackness and death.",
  },],
  },
  nomad: {
    quote: "The future must be preserved at all costs.",
    quoteAuthor: "The Nomad",
    lore: [{
    kind: "paragraph",
    text: "Shortly before the Creuss Expedition left to plumb the depths of Shaleri Space, a number of sensor nets and observatories began to receive messages broadcast from the very heart of the galaxy. These messages repeated in a multitude of languages, and warned of a dark future to come that must be prevented at all costs. What struck the various scientists as odd was the source—the galactic center being utterly devoid of life—and the means of transmission. The messages were not sent via supraluminal communications, but instead broadcast on ancient radio frequencies. That meant the message had been sent thousands of years before the Lazax first founded their empire on Mecatol Rex.",
  },
  {
    kind: "heading",
    text: "The Information Broker",
  },
  {
    kind: "paragraph",
    text: "In the confused wake of the Creuss disaster, the galaxy’s network of data brokers began sharing stories of a wealthy individual who was hungry for information. Brokers rarely met with their new client in person, but the few who did said they were a nondescript humanoid wearing an environmental suit and shrouded in merchant’s garb. They referred to themself only as “The Nomad,” and paid in valuable information as often as in coin. The Nomad seemed particularly interested in any information regarding the failed Creuss expedition, and about the scattered rumors of nightmare demons haunting Shaleri space.",
  },
  {
    kind: "paragraph",
    text: "Some argued that the Nomad had to be a mask for members of a larger organization. Anyone could use an environmental suit to obscure their identity, after all. Others insisted that the Nomad was a single individual, even in the face of rumors that they had conducted business in several different star systems across the span of a few days. Still, most dismissed the Nomad as a harmless curiosity—until Sumerian.",
  },
  {
    kind: "heading",
    text: "The Fall of Space Station Sumerian",
  },
  {
    kind: "paragraph",
    text: "Space Station Sumerian encircles the frostbitten world of Arcturus. Though the ice-locked planet has few inhabitants save for the smugglers who hide caches of contraband on the surface, the massive station is one of the busiest independent trading ports in the galaxy. Laws are loose and enforcement lax, so one can buy nearly anything in one of Sumerian’s hundreds of markets and bazaars. Ships from every corner of the galaxy dock in its shipping bays, and the various galactic powers have traditionally left Sumerian alone while quietly skimming riches from the businesses conducted there.",
  },
  {
    kind: "paragraph",
    text: "In the course of a few weeks, the Nomad took over Sumerian, seemingly by chance. A series of licenses, contracts, and deals ended and began at the perfect time to grant the Nomad control of the station’s operations and most of its major factions. The few magnates and mercenary leaders who attempted to resist the takeover simply vanished. The head of Sumerian, a trader by the name of Haro M’res, ended up being quietly arrested and imprisoned.",
  },
  {
    kind: "heading",
    text: "A Formidable Armada",
  },
  {
    kind: "paragraph",
    text: "With the Nomad in control of Sumerian, they began to expand their grasp over the surrounding systems. It quickly became apparent that the Nomad had access to nearly limitless sums of money, and they used their funds to buy influence in planetary governments and outright control of corporations. At the same time, mercenary groups began flocking to Sumerian, drawn by promises of lucrative contracts. Whole starships were purchased through shell corporations and eventually ended up in Sumerian docks, being refitted with military weapons and hardware. The Nomad also brought with them a small cadre of loyal agents that they seemed to trust to act in their name. The most feared of these was the Creuss warrior Ahk-Syl Siven, whose armor glowed with intermingled blue and crimson sparks.",
  },
  {
    kind: "paragraph",
    text: "Many have since come to realize that the Nomad is the center of a creeping web of influence and blackmail that stretches across the galaxy, and at the same time has also amassed a formidable mercenary army. However, all attempts to covertly eliminate this nascent threat have so far ended in failure. The Nomad seems to have an almost prescient ability to anticipate threats and defeat them. Whoever the Nomad is, they clearly are enacting a plan of mind-boggling scope and complexity.",
  },
  {
    kind: "quote",
    text: "Now, as their agents infiltrate the Galactic Council and mercenary warships set out from Sumerian’s docks, many suspect that the ultimate goal of that plan is Mecatol Rex.",
  },],
  },
  sardakk: {
    quote: "Fear is death. Most of you will die. The Queen Mother thanks you for your worthy sacrifice.",
    quoteAuthor: "G'hom Sek'kus",
    lore: [{
    kind: "paragraph",
    text: "Not far past the Unicorn Nebula, the golden Sardakk star shines its ancient, hot light on giant oceanless Quinarra. The massive planet radiates a red glow like a dusty ruby in the night, its massive polar storms clearly visible from space. A great network of orbital space stations and massive complements of fleet units occupy the system in the fashion of the insectile N’orr. Massive whale-like N’orr carriers spew fighters like angry hornets from a disturbed nest. Convoys of ice-mountain transports are always inbound from the planet Trenlak. Small spider-like robotic ships drill into the sides of the ice, guiding the ice to the orbital liquid processing plants, after which the derived water and salt is flown to Quinarra by bloated sun gliders that, like beetle balloons, slowly descend to the N’orr cities below.",
  },
  {
    kind: "heading",
    text: "The Desolation of Quinarra",
  },
  {
    kind: "paragraph",
    text: "Quinarra itself is among the most inhospitable of planets inhabited by a major civilization. Only Letnev’s Arc Prime is recognized as more desolate than Quinarra. The Letnev, however, live exclusively under Arc Prime’s surface, whereas the N’orr civilization is well established both on and below Quinarra’s continents. Only Quinarra’s polar regions, where even the hardy N’orr cannot survive the deadly storms for extended periods of time, are largely uninhabited. Brutal electric, hail, and dust storms, although not approaching the ferocity of the polar storms, are frequent throughout the planet and considered normal by the N’orr.",
  },
  {
    kind: "paragraph",
    text: "Visitors to Quinarra will be flown directly to the immigration nexus in the capital H’cor. Whether permits sufficient visibility, most visitors will be impressed by the massive size and explosive traffic of the city. The N’orr structures are typically oval or rounded, created from a hardened reddish material similar to the general topography of the planet. Like most major N’orr cities, H’cor features towering building constructs, sprawling low-story buildings, and deep gorges that reveal city-nests deep below the surface, delving into the red earth. Busy roads and hover-lanes cross the city in a thousand ways, often congested with N’orr traffic.",
  },
  {
    kind: "heading",
    text: "The Queen Mother and the Veiled Brood",
  },
  {
    kind: "paragraph",
    text: "The N’orr will tell you that they are ruled by “Sardakk the Queen Mother,” but that acknowledgment seems more steeped in ritual than fact. None have ever met the mythical “mother,” and no off-world documentation exists suggesting there is any truth to the notion. The accepted and visible head of the N’orr state is the Envoy of the Queen, a male N’orr in direct command of the cultural, economic, and military matters of the race. The length of the Envoy’s tenure and the process of his election seems to be decided by a secret brotherhood, the “Veiled Brood,” in which lies the real power of the N’orr.",
  },
  {
    kind: "heading",
    text: "The Tekklar Order and the Gathering Swarm",
  },
  {
    kind: "paragraph",
    text: "The Envoy and the Veiled Brood oversee the rapid expansion of the N’orr military forces and fleets. The Tekklar Elite soldiers are the pride of their people. The Tekklar train exclusively in the southern polar regions, where the weak and the strong become G’hom: members of the prestigious Tekklar order, treated like knights by the N’orr and feared across the galaxy. As Quinarra slowly turns, as the stars again come into their right constellations, the Veiled Brood knows that the time to swarm is coming again.",
  },
  {
    kind: "quote",
    text: "And this time, the swarm will cover the stars.",
  },],
  },
  titans: {
    quote: "The Titans seek something more permanent than a mere empire.",
    quoteAuthor: "Pyrolusius the Observer",
    lore: [{
    kind: "paragraph",
    text: "Tens of thousands of years ago, Mahact gene-sorcerers crafted one of their most brilliant creations, the Titans. Though they looked like massive machines, beneath their metallic shells they were a living creature of silicates and steel. They combined the best elements of the biological and the mechanical. They could work for ages without tiring and were exceedingly durable. They could also heal injuries and, over time, expand their numbers. Most importantly, they were intelligent beings, not mindless automatons—though the Mahact programmed them so that the Titans would never disobey their masters. In all, the gene-sorcerers had created the perfect guardians and laborers for their kingdoms.",
  },
  {
    kind: "heading",
    text: "The Millennia of Dormancy",
  },
  {
    kind: "paragraph",
    text: "When the Mahact were driven from the galaxy by the Lazax, they seeded sleepers in their wake to facilitate their eventual return. The greatest of these were to be the Titans. At the Mahact’s command, the Titans buried themselves in the wilds of their worlds and went into a deep dormancy. And they slept, as the Lazax Empire rose and fell, and the Twilight Wars raged and quieted. Occasionally, a Titan may be uncovered by explorers, but they appeared to be just one more relic of a forgotten past.",
  },
  {
    kind: "paragraph",
    text: "Then the Mahact returned, and the gene-sorcerers sent out a call to awaken their servants. Many of the Titans heard the call and woke. However, the Mahact had gravely underestimated their creations. During their millennia of dormancy, the Titans had continued to develop, and their minds had continued to expand. When they woke, they found that they no longer felt any compulsion to obey their former masters.",
  },
  {
    kind: "heading",
    text: "Elysium and the Ul",
  },
  {
    kind: "paragraph",
    text: "Instead, the Titans began to seek out others of their kind. The greatest population of Titans had gone dormant on one of the wonders they had constructed during the last days of the Mahact rule: a massive Dyson sphere. The Titans had constructed the shell around a singularity, using its harnessed energy for power, and its immense mass to create gravity on the outer surface. Now, they claimed their home, calling it Elysium and summoning all other Titans to join them.",
  },
  {
    kind: "paragraph",
    text: "In the years that followed, the Titans have worked hard to establish their new civilization. Elysium offers more space than ten thousand normal planets. This has proven invaluable, because though the Titans grow slowly, they never stop. The youngest Titans are easily ten meters tall, while an elder can be the size of a habitat tower. Titans also have a great preference for order and organization. They freely submit to a hierarchical society, where the oldest and most experienced Titan, called the “Ul,” rules.",
  },
  {
    kind: "heading",
    text: "Transcendence and the Living Garden",
  },
  {
    kind: "paragraph",
    text: "While the Titans are bio-mechanical creatures, they tend to show a great love of living things. Many Titans devote themselves to cultivating Elysium into a lush garden world, seeding myriad biomes across its formerly barren surface. Titan towns blend seamlessly with the surrounding landscape, even though Titan structures are massive by necessity. That said, since the Titans tend to spread out across Elysium’s surface, the only true city is their capital, Transcendence. Here one can find the Ul literally watching over their people. The eldest Titan is so massive that they eclipse even the largest buildings. Instead, the Ul stands in the center of Transcendence, unmoving as they speak with their fellows about the issues confronting their people.",
  },
  {
    kind: "paragraph",
    text: "Though the Titans have been preoccupied with cultivating their new world and developing their society, they have not forgotten about the wider galaxy. Already trading vessels descend on Elysium with holds full of rare minerals and exotic plant and animal life. In exchange, the Titans construct wondrous devices from the ancient days, and travel to other worlds to build huge stations and massive geoforming and terraforming projects. They continue to scour the galaxy, looking for any of their kin who may still slumber beneath the surfaces of countless worlds.",
  },
  {
    kind: "heading",
    text: "A Steady Hand for the Galaxy",
  },
  {
    kind: "paragraph",
    text: "As the ancient prophecies come to pass and war looms, the Ul looks into the skies of Elysium and sees a galaxy in chaos. They know that the only chance that teeming multitudes scattered across countless worlds have for survival is a steady hand guiding them to peace.",
  },
  {
    kind: "quote",
    text: "They know that while some may not realize it, there is a place for everyone in the universe, and everyone must find their place—with the Titans to watch over them all.",
  },],
  },
  jolnar: {
    quote: "We cannot halt progress for the sake of morality. If you have not the stomach for science, then I suggest you depart Wun-Escha immediately.",
    quoteAuthor: "Doctor Sucaban",
    lore: [{
    kind: "paragraph",
    text: "Most technological devices used in the galaxy today have at least one or two components originating from the Jol-Nar laboratories. At the height of the Lazax Imperium, the galaxy was even more reliant on underlying Jol-Nar technology and the knowledge of the aquatic Hylar. The reliance on Jol-Nar engineers and skills was one of the key factors leading to the total collapse of galactic civilization and its descent into the Dark Years that followed the Twilight Wars.",
  },
  {
    kind: "paragraph",
    text: "When the Twilight Wars first began, the Jol-Nar closed their embassies, withdrew their workers, and started a war of aggression on their own. Among the other races, few individuals remained who now understood the complex Jol-Nar machinery, virtual code, and chemical compounds. Soon, fundamental machinery started failing, setting off a chain reaction of integrated technological failures over a period of hundreds of years. Combined with devastating wars, this spurred massive famine, poverty, and chaos. As cultures, economies, and finally the tools of war completely collapsed, the Twilight Wars quickly ebbed and the Dark Years began.",
  },
  {
    kind: "heading",
    text: "The Doolak Plague and Saudor",
  },
  {
    kind: "paragraph",
    text: "Even the Jol-Nar were devastated by the Twilight Wars. Although the rest of the galaxy had relied on their technologies, they so had the Jol-Nar relied on the income, protection, and natural resources of others. The arrogance of the High Scholars spurred them to wage a sudden aggressive war after the Quann conflict erupted. Then, a few years later, the Doolak plague destroyed nearly a quarter of the Jol-Nar population, causing a massive loss of knowledge by itself. The Jol-Nar aggression soon turned defensive, and the powerful N’orr looked to conquer all Jol-Nar. Only after a decisive Jol-Nar victory in the Saudor system did the Hylar receive a needed respite.",
  },
  {
    kind: "heading",
    text: "The Twin Ocean Worlds and the University",
  },
  {
    kind: "paragraph",
    text: "Like azure sapphires, the twin ocean planets of Jol and Nar slowly circle the Garian star. Under their waters lie the great civilization of the Hylar, a water-breathing, soft-bodied species with oversized heads and intellects to match. The Hylar are governed by an ancient system of high scholars, who combined are called the University. A single Hylar ruler, the Headmaster, oversees the Hylar from the deep underwater city of Wun-Escha on the planet of Jol. Under the Headmaster, the Circle of Regents governs the local regions and specific areas of knowledge.",
  },
  {
    kind: "heading",
    text: "Physiology and Evolution",
  },
  {
    kind: "paragraph",
    text: "Although the Hylar are often considered one race, there are in fact several distinct variations within the Hylar species, mainly derivative of the geographical region and ocean depth from which they hail. Most Hylar are capable of breathing surface air, and some can exist for weeks without being submerged. Others cannot breathe surface air at all, and must travel in massive tanks when off planet. None know how an underwater race came to be masters of technology. Most agree that the large bio-cerebral areas of the Hylar physique, combined with a need to adapt their soft-boned and slow bodies to their environment, created an evolution of material usage, as opposed to one of physical adaptation.",
  },
  {
    kind: "heading",
    text: "The Circle of Regents Ascendant",
  },
  {
    kind: "paragraph",
    text: "Despite their physical weakness, the Hylar are a proud people, often to the point of abrasiveness and arrogance. Since the catastrophic Dark Years, the Hylar have started utilizing the natural resources of their own planets, and they now extract metals and medicines from the many algae and coral formations of both Jol and Nar. As a new age nears, the Circle of Regents has secretly decided that the Hylar must take the place of the Lazax in governing and advancing a new united galaxy. Under their mandate, the Headmaster has begun building his forces, and Jol-Nar diplomats and engineers have started appearing among the other civilizations in large numbers, appearing friendly, but with hidden agendas.",
  },
  {
    kind: "quote",
    text: "Soon the Headmaster will make his claim for the empire, and the galaxy will enter an age of technological advancement and intellectual achievement.",
  },],
  },
  cabal: {
    quote: "YOUR FORM IS FRAGILE AND WEAK. LET ME RELIEVE YOU OF YOUR HARDSHIPS",
    quoteAuthor: "That Which Molds Flesh",
    lore: [{
    kind: "paragraph",
    text: "Philosophers and scientists have long theorized that the galaxy is only one of a host of realities. These other dimensions exist on a different plane, and the physical laws one takes for granted in this space—such as gravity and entropy—may be wildly different or nonexistent. The existence of fabled worlds like Malice seems to support such conjectures, for the world may exist in one such alternate reality. Some researchers even attempt to predict the nature of these theoretical dimensions. However, even the most deranged scientist could not imagine a universe of seething, fleshy masses floating in a thick, cloying mist, or the ravenous creatures that could thrive in such a place.",
  },
  {
    kind: "heading",
    text: "The Ruin of Acheron",
  },
  {
    kind: "paragraph",
    text: "After the disaster on Acheron, a single Letnev corvette returned from the depths of Shaleri space with the horrifying tale of what had befallen the Creuss expedition to Ixt. As the various members of the Galactic Council began to gather their forces to deal with the Mahact, the Mentak Coalition dispatched one of its fastest void sloops to reconnoiter the Acheron system and see what the Mahact may be up to.",
  },
  {
    kind: "paragraph",
    text: "After a week’s hard travel, the void sloop drifted quietly in past the Acheron system’s icy outer bodies and got its first good look at the gateway to Ixt. To the crew’s shock, the planet was no more. Acheron had shattered into shards of rock that now tumbled around an immense roiling vortex of gravitational instability that seethed with a baleful purple light.",
  },
  {
    kind: "paragraph",
    text: "The vortex was in the midst of consuming the inner system. Even days out, the sloop’s commander could feel the strain on her vessel, and watched in horror as Acheron’s star twisted and writhed under the assault. But the pressure on, as close as she dared. There was no sign of the Mahact or the Creuss expeditionary armada. However, there were strange readings amongst the tumbling remnants of the planet. When one of the sensor returns suddenly accelerated toward her ship, the commander had her crew put about and fled for open space. That was the last successful expedition to the Acheron system.",
  },
  {
    kind: "heading",
    text: "Incursion from the Rift",
  },
  {
    kind: "paragraph",
    text: "In the months following the event, researchers and intelligence operatives began to make conjectures about what new threat had fallen on the galaxy.",
  },
  {
    kind: "paragraph",
    text: "Ixt, supposed paradise and ancient home of the Mahact, sat far outside the bounds of the galaxy. In order to construct a gateway that could reach across the gulf of intergalactic space, the Mahact had to sink it deep into the very fabric of space-time. As part of their entropic research, the Naaz-Rokha theorized that the wormhole may have crossed the threshold of this universe, into an entirely different dimension.",
  },
  {
    kind: "paragraph",
    text: "When the Mahact awoke, they ripped their world from its orbit and flung it into the galaxy’s heart. In doing so, they destroyed the Acheron Gateway, leaving a great gaping wound in the planet’s heart and in the fabric of the universe.",
  },
  {
    kind: "paragraph",
    text: "Through this rift came the Vuil’raith—a race of creatures from beyond the stars, resembling the demons that haunt many of the galaxy’s oldest myths. No two are alike, and they range in size from tiny monsters no larger than a finger to great fleshy beasts as large as dreadnoughts that swim through the void. They have infested the twisted space around the bones of Acheron. From there they gather their forces and cast their covetous eyes upon the galaxy.",
  },
  {
    kind: "heading",
    text: "The Cabal and the Spreading Rot",
  },
  {
    kind: "paragraph",
    text: "The Vuil’raith are not mindless monsters. They possess a malign intelligence and powerful ambitions. They are even led by a Cabal, though the council has no set size. If a Vuil’raith is vicious and powerful enough to slay all of its rivals, eventually it amasses enough power to join the Cabal’s ranks. It remains a part of the Cabal as long as it can dominate a significant horde of lesser Vuil’raith and keep its foes from slaying it to lay claim to its holdings. However, there are no true allies in the Cabal—only mutually distrusted rivals bound by shared interests. The Cabal has set out to sow dissension ahead of its invasion. Cults of the Vuil’raith fester in the shadows of the galaxy’s great cities. The weak-willed and disaffected are drawn to serve the Cabal, some with the hope of reaping grand rewards, while others simply want to watch the galaxy burn. The Vuil’raith send their agents to advance their interests and weaken their foes, and even the halls of the Galactic Council may not be free of their taint.",
  },
  {
    kind: "paragraph",
    text: "Meanwhile, the worlds on the edges of Shaleri space have come under assault from the Vuil’raith. Looming flesh-ships smash system defense fleets from the void, and cracking portals open in the streets to disgorge hordes of ravenous demon-beasts.",
  },
  {
    kind: "quote",
    text: "With the Acheron rift providing an anchor into this reality, the Vuil’raith work tirelessly to build additional gateways to their hellish domain, their only desire to rip open the heart of Mecatol Rex and set a gateway among its bones.",
  },],
  },
  winnu: {
    quote: "We will claim what is ours by right, cousins. We will fulfill the destiny of those who came before us, and your treachery will not be forgotten.",
    quoteAuthor: "Muad Di Faruuq",
    lore: [{
    kind: "paragraph",
    text: "The Winnu system was the first system to seek annexation into the Lazax Empire. Throughout their history, the Winnarans had suffered countless civil wars, a deteriorating climate, and debilitating disease. They were a race on the brink of extinction when they first came into contact with the Lazax, and only with generous Lazax support did the Winnaran race survive. The Lazax allowed the Winnarans into their empire, and over time healed the scars of Winnu. More importantly, the Winnarans came to embrace the Lazax code of strength and peace, the powerful doctrine which had allowed the first Lazax emperor to defeat the last of the mad Mahact kings and to emerge as a shining beacon of peace and stability in a dark galaxy.",
  },
  {
    kind: "heading",
    text: "The Imperial Servants & The Diaspora",
  },
  {
    kind: "paragraph",
    text: "The Winnarans were eternally grateful to the Lazax, and swore an oath of servitude to the emperors. Disciplined and diligent, the Winnarans became indispensable to the Lazax as bureaucrats, councilors, and administrators. As their empire grew increasingly complex, it is likely that the Lazax would not have been able to hold their empire together without the work and attention to detail of the Winnarans. Then, as the Lazax decided to move their imperial seat to a planet more central to the galaxy, more than half of the population of Winnu joined the Lazax diaspora to this new home. That home was the planet of Mecatol, which would become the Rex, the splendid jewel in the imperial crown. As the ages came and went, most Winnarans began to think of Mecatol as their ancestral home, and the relevance and memory of Winnu and their brethren there diminished.",
  },
  {
    kind: "paragraph",
    text: "Yet the Winnaran population on Winnu, now generally called the “Winnu”, quietly built their own civilization following the doctrine of the emperors. Much Lazax lore, wisdom, and culture is intact on Winnu, even as all other Lazax imagery and culture was destroyed elsewhere in the galaxy during the Great Scourge.",
  },
  {
    kind: "heading",
    text: "Estrangement and the True Inheritors",
  },
  {
    kind: "paragraph",
    text: "As the memory of the Great Scourge faded, and as the Dark Years seemed to stretch along endlessly, the Mecatol Winnarans and the Winnu grew estranged from one another. On Mecatol, the Winnarans were bound to rigid tradition and scholarship, while the Winnu culture had evolved and prospered. The Winnu became ashamed of their submissive cousins on Mecatol, whom they began to regard as a grey, backwards people, devoid of fashion, art, and culture.",
  },
  {
    kind: "paragraph",
    text: "As a new age is dawning, the Winnu truly believe themselves to be the inheritors of the Lazax. Their philosophies, their artwork, and even the clothing fashion of the Winnu is rooted in that of the ancient Lazax. Some outside observers, however, will note that along with the Winnu preservation of Lazax imagery and culture, that time has brought the return of more traditional Winnaran traits in the Winnu—ambition, pride, and impatience.",
  },
  {
    kind: "paragraph",
    text: "As they grew prosperous and powerful, the Winnu witnessed the reemergence of the other great races with annoyance and mistrust. Those were the races that had slaughtered their benefactors, and their return to power felt to the Winnu like sacrilege against the memory of the Lazax. Even more poisonous to the Winnu was the fact that their submissive cousins on Mecatol had invited these races to reestablish the galactic council there—even going as far as inviting the races that resigned from the Lazax council immediately before the Age of Twilight.",
  },
  {
    kind: "heading",
    text: "The Defiance of Muab Di Faruuq",
  },
  {
    kind: "paragraph",
    text: "With the pride of a new, powerful civilization and the sense of Lazax entitlement, the supreme Winnu leader Muab Di Faruuq traveled to Mecatol and demanded that the Winnarans return to the sovereignty of Winnu, and that the custodians grant the Imperial Throne to their own race as the rightful heirs of the Lazax.",
  },
  {
    kind: "paragraph",
    text: "The Mecatol Winnarans, ever mindful of their responsibility to the entire galaxy, sorrowfully declined the demand of their brethren. As they did so, they feared that their short-tempered Winnu brothers and sisters would become angered, and that the resulting bitterness would forever break apart whatever kinship remained between them.",
  },
  {
    kind: "paragraph",
    text: "The Winnarans’ fear was well placed. Muad Di Faruuq was furious with their decision and rushed back to Winnu, but not before establishing a consulate and council presence for the Winnu on Mecatol. Upon his return to Winnu, he proclaimed the betrayal of the Winnarans, and swore that if Mecatol and the Imperial Throne would not be ceded to the Winnu by peaceful means, then, in the memory of the Lazax, force would be the only answer.",
  },
  {
    kind: "quote",
    text: "The Winnu population rushed to Faruuq’s support, a sense of righteousness and superiority motivating them to an intense mobilization. Building massive fleets, eerily reminiscent of ancient Lazax designs, and training massive invasion forces, the Winnu are intent on returning true Lazax culture to the galaxy.",
  },],
  },
  xxcha: {
    quote: "To fight without cause is not the way, human.. Curb your anger. Let us walk through the gardens and consider how to proceed.",
    quoteAuthor: "Elder Qanoj",
    lore: [{
    kind: "paragraph",
    text: "Even the oldest annals recognize the ancient kingdom of the reptilian Xxcha as the first of the great interstellar civilizations. Nestled in the middle of a wealthy section of space, the Xxcha twin planets of Archon Ren and Archon Tau lie bathed in the gentle light of the Xxlak star. While the Xxcha still call the two planets “twins”, an outsider will instantly notice that the grayish and shadowy Archon Tau in no way resembles the brilliant, healthy green of Archon Ren.",
  },
  {
    kind: "heading",
    text: "The Unheeded Warnings",
  },
  {
    kind: "paragraph",
    text: "Throughout the tenure of the lost Lazax Imperium, the Xxcha were the most peaceful, docile, and content of the major civilizations. They did not, unlike the other races, scheme for power and territory during the Age of Dusk. Unlike the Lazax, the Xxcha elders did see the growing threat to the galaxy. They fruitlessly sought to warn the Lazax of their peril, and struggled to bring dialogue to the increasing racial factionalism. A powerful Lazax councilor by the name of Ibna Vel Syd listened to the Xxcha warning, but even he could not sway the false idealism of the emperor. Then, disaster struck.",
  },
  {
    kind: "heading",
    text: "The Fall of Archon Tau",
  },
  {
    kind: "paragraph",
    text: "The Quann crisis erupted into sudden war, and the Letnev, led by the Baron Daz Arkolan I, moved towards the rich Xxcha system in conquest. The Xxcha, unprepared and weaponless, used their formidable powers of negotiation and goodwill to broker an agreement in which they ceded only Archon Tau to the invaders, while the kingdom retained a Letnev-supervised autonomy on Archon Ren. The Xxcha, never fools, were aware of the nature of Letnev promises and the futility of the arrangement. The agreement would only last as long as the Barony was occupied in war elsewhere. In time, the Xxcha knew, the Letnev would return to claim the rest of their prize and enslave them. It was then, for the first time in their history, that the Xxcha started to create their first weapons and train their first armies. In secret deep groves and in hidden vales, the Xxcha sadly watched their people develop into warriors.",
  },
  {
    kind: "paragraph",
    text: "Less than a decade after the occupation of Archon Tau, the Letnev fleet suffered a stunning defeat against Sol in the Gral system. Only a few cycles after the battle, the Sol Phoenix fleet entered the Xxlak system and engaged the heavily fortified Letnev positions on Archon Tau. The ensuing bombardments and battles lasted for almost two years. In the end, the Letnev occupiers were defeated, but at a terrible toll. The ecology of Archon Tau had been shattered beyond recall. What was once a true twin to the green and fruitful Archon Ren was now a noxious, blackened crater. Its forests had burned. Ashes and scattered dust started a planet-wide winter that lasted for a hundred years, killing most plant and animal life.",
  },
  {
    kind: "heading",
    text: "The Kingdom on Archon Ren",
  },
  {
    kind: "paragraph",
    text: "Now, recovered from the loss of Archon Tau, the Xxcha kingdom has prospered on the generous Archon Ren. Covered by mostly leafy forests, small inland oceans, and fruitful jungles, Archon Ren is rich in minerals, energy, foodstuffs, and water. The Xxcha civilization dwells in a myriad of arboreal villages and towns. The only true metropolis is the giant city of Klkaj, found on the planet’s southern hemisphere. Klkaj functions as the seat of the Xxcha King, whose extensive palace, entirely sculpted of Qweard wood, and flower gardens, stretch for miles at the center of the city.",
  },
  {
    kind: "paragraph",
    text: "The Xxcha are an inherently peaceful, slow, and thoughtful people. They hold their nobles and town elders in deep respect. A common pastime of Xxcha males and females alike is to debate meaning and origin while smoking gerr root on long-stemmed pipes. The jungles and lakes of Archon Ren are surprisingly free from the invasive insects that so often make forest and jungle planets unbearable.",
  },
  {
    kind: "heading",
    text: "Sentinels of Peace",
  },
  {
    kind: "paragraph",
    text: "Although the Xxcha still believe in the doctrine of peace and negotiation, they will never again bend to foreign invasion. Travelers to the Xxlak system will often notice impressive sentinel Xxcha superdreadnoughts and the distinctive Xxchan fighters in intense naval exercises. Although the typical Xxcha may seem slow and encumbered by a heavy reptilian bodily weight, when roused, the Xxcha are surprisingly strong and fast.",
  },
  {
    kind: "paragraph",
    text: "The pale shadow of Archon Tau hangs like a scar in the Xxcha skies. The sight of it is a lasting sorrow of the Xxcha, and the ever-present reminder of the cost of submission. The Xxcha will never allow such tragedy to befall them again.",
  },
  {
    kind: "quote",
    text: "Ceryuss, the Xxcha King, knows that for the sake of a peaceful galaxy, the Xxcha must seek the Imperial Throne and be wise for all.",
  },],
  },
  yin: {
    quote: "A-ah! You mistake me for a human; that we share the blood of Jord. I am no son of humanity. My life for the Yin!",
    quoteAuthor: "Brother Milor",
    lore: [{
    kind: "paragraph",
    text: "Lazax law strictly forbade the practice of cloning, the dangerous science that led to the madness, disease, and ultimate downfall of the Mahact kings. The emperors severely punished any regime or independent scientist dabbling in this dangerous field.",
  },
  {
    kind: "heading",
    text: "The Obsession of Darien Van Hauge",
  },
  {
    kind: "paragraph",
    text: "Darien Van Hauge, a prominent Sol scientist, had lost both his children to the terrible wasting disease Greyfire. After their loss, he was intent on finding a cure for this horrible affliction, and refused to let any law stay his hand. In silent revenge against the destiny of his children, he left his employment with the prestigious Hospitaler Clinic in New Moscow and traveled to the third moon of Emelpar, where he secretly sought and finally acquired ancient Mahact bio studies.",
  },
  {
    kind: "paragraph",
    text: "The brilliant Darien made great advances in the following years. His wife Moya contributed the embryos he needed for his forbidden experiments. With his successes, however, word of his work began to leak, and a congregation of the hopeful began to surround him, bringing their sick and dying to his care, clinging to a last hope that his discoveries could cure them.",
  },
  {
    kind: "paragraph",
    text: "Darien’s secret ended the day a sick child died in his care. The anguished, remorseful parents blamed Darien for the death and contacted the Sol authorities. That night, Darien fled Jord with his wife and a few of his most devout followers.",
  },
  {
    kind: "heading",
    text: "Exile to Lael and the Hills of Grace",
  },
  {
    kind: "paragraph",
    text: "Now a known fugitive, Darien narrowly escaped capture again and again. To finally escape the Lazax authorities, his small group joined religious colonists migrating to a new home on the remote planet of Lael, a place of harsh oceans and stormy climates. Their fugitive years brought healing and perspective on the death of their children, and Darien and Moya found happiness again on the windy plains of Lael.",
  },
  {
    kind: "paragraph",
    text: "But a few years later, Moya developed Greyfire.",
  },
  {
    kind: "paragraph",
    text: "Desperate to save his wife, Darien employed all his skills and forbidden knowledge, but still he failed. Before her death, he extracted a single egg from her womb—preserving the genetic blueprint of her unborn children.",
  },
  {
    kind: "paragraph",
    text: "He burned her body on the summit of the Hills of Grace, which they had named after their lost daughter. As Moya’s ashes drifted upwards into the strong winds, Darien dug a stone out of the hillside with his bare hands and placed it near the fire. That stone became part of the foundation for the great monastery of Lucas, named after Darien and Moya’s lost son.",
  },
  {
    kind: "heading",
    text: "The Creation of the Brothers",
  },
  {
    kind: "paragraph",
    text: "In the following decades, Darien was able to produce a child from a clone of Moya’s egg and his own seed. It was a boy. Cloning Moya’s egg by the thousands, producing child after child with increasing success, Darien became a master of the forbidden craft. Yet, inexplicably to him, all the children were boys, and he was never able to eradicate the vulnerability to Greyfire from his creation. Though he was able to eliminate the lethal outcome of the disease in his “sons” as he called them, the Greyfire would attack their skins and topical tissues, hideously deforming most of the children.",
  },
  {
    kind: "paragraph",
    text: "After Darien’s death, his sons diligently continued his work. They continued cloning Moya’s egg, which they called the “Yin,” and they continued the production of new “brothers” from their own seed. Over the centuries, the monastery of Lucas became a vast facility, completely covering the Hills of Grace and the surrounding plains.",
  },
  {
    kind: "paragraph",
    text: "The Brotherhood, blessed with the brilliant minds of both Darien and Moya, grew to vast proportions and renamed their planet “Darien.” As the Age of Dusk neared its end, the Brotherhood ventured into space, establishing monasteries on Darien’s moons and its surrounding systems.",
  },
  {
    kind: "heading",
    text: "The Blessed and The Untouched",
  },
  {
    kind: "paragraph",
    text: "The Brotherhood long ago abandoned any hope of the female creation, and instead worship the Yin as the mother and the feminine in their lives. Despite centuries of continued work, they have never been able to completely eradicate the signs of Greyfire. Instead, the brothers who are completely ravaged and deformed by the disease are revered as “The Blessed,” and the brothers left untouched by the disease are called “The Untouched.” The Blessed form the inner elders and councilors of the Yin society. The Untouched are trained as ambassadors to the other races and as elite soldiers of the Brotherhood.",
  },
  {
    kind: "paragraph",
    text: "In their flesh, the brothers carry the secret inner fire and rebellious ambition of Darien. The eldest of the Blessed, the Elder Brother, intimately understands the emotions and aspirations of all his brothers.",
  },
  {
    kind: "quote",
    text: "Intent and unified, the Brotherhood now builds a vast fleet with which to bring Darien’s legacy and the light of Yin to the imperial throne itself.",
  },],
  },
  yssaril: {
    quote: "Clever Ssruu has met the offworlder and made it dead. What does the Guild want for Ssruu to meet next?",
    quoteAuthor: "Ssruu",
    lore: [{
    kind: "paragraph",
    text: "Near the Mahact Plateau, diagonally opposite the Passage of Tears, but located in a far richer area of the region, shines the Myock star and its two habitable planets, Shalloq and Retillion. As recorded in even the earliest annals, Retillion has been known for the edible and delicious menn root. Throughout the Lazax Imperium, many farming colonies existed on Retillion, harvesting the roots along the musky and odorous shores of the Fianni swamps. In the years of Lazax emperor Munhan Las Ida, the colonization efforts were dramatically expanded. Not long after the start of the farming expansion, however, things started to go terribly wrong on Retillion: farm machines were sabotaged, isolated farms destroyed, inhabitants murdered by an unseen foe that would strike when the bog mists rolled over the lands.",
  },
  {
    kind: "heading",
    text: "The Swamps of Fianni & The Aborigines",
  },
  {
    kind: "paragraph",
    text: "The empire sent reinforcements, and the colonists soon realized they were under systematic attack by a small native chameleon race with natural greenish skin and large yellow lamp-like eyes. These aborigines had the ability to “fade,” making them both virtually invisible to the naked eye and a great threat to the farming boom towns springing up along the edges of the measureless swamps. It was clear that the natives were a primitive race, but fierce, intelligent, and relentless in their intent to stop the invasive farming of their native swamplands. From the few early prisoners, it was learned that they called themselves the “Yssaril” and that a vast network of villages and tribes was to be found in the continent-sized Fianni swamp.",
  },
  {
    kind: "paragraph",
    text: "Eager to renew the supplies of their beloved menn root, the Lazax sent their 21st Expeditionary Division to suppress the Yssaril uprising, allowing for the resumption of the increased farming mandate. During these bloody days, thousands of Yssaril were captured and shipped to governments and buyers across the galaxy for study or hunting sports. Although farming did resume, the Lazax military division never completely suppressed the Yssaril natives. As the small green Yssaril adapted to the Lazax style of warfare, as they stole and learned to use Lazax weapons, the Fianni swamp soon became an embarrassing killing field for Lazax conscripts.",
  },
  {
    kind: "heading",
    text: "The Guild of Spies",
  },
  {
    kind: "paragraph",
    text: "It was during the Age of Dusk that the great races learned to utilize the potential of the intelligent Yssaril as spies and assassins for their covert operations. For a hundred years, the Yssaril learned the skills of stealth, the usage of technologies, and the power of information. Combined with their own natural ability to become nearly invisible, they soon came to realize their own potential and established the powerful and feared Guild of Spies. By the proceeds derived from Guild business, the Yssaril added a formidable income source to their civilization and to the development of Retillion. With this power and influence, they were able to convince the Lazax to leave the planet (while still supplying menn root). Over a few generations, the Yssaril became industrial, educated, and ambitious.",
  },
  {
    kind: "paragraph",
    text: "Although still powerful in covert circles, the Guild now functions as the prime governing body of the united Yssaril tribes. The Guild elects its leader from its faction of master assassins. This prime leader, the C’qarck, leads the powerful civilization of the intelligent, determined, ambitious people, a people whose history has left them with little love for the other great races.",
  },
  {
    kind: "heading",
    text: "Retillion and Shalloq",
  },
  {
    kind: "paragraph",
    text: "Since the Lazax left, no off-worlders have been allowed on Retillion. The Yssaril capital Wuecca lies somewhere deep in the Fianni swamps, its actual location unknown to all but the Yssaril. The official business, trade, and covert operations are conducted from the planet Shalloq, which the Yssaril colonized not long after gaining independence from the Lazax. The only actual Yssaril city known to off-worlders is the city of Mojeb on Shalloq. From here, from Shalloq’s great orbital trade station Haarsath, the Yssaril receive foreign emissaries, merchants, and visitors.",
  },
  {
    kind: "paragraph",
    text: "The proud, fierce Yssaril are slowly starting to look beyond their borders and beyond the income of the Guild. Hidden in the planetary shadow of Shalloq, and kept secret from the rest of the galaxy, is the covert means at which the Yssaril excel, a great invasion fleet is being built.",
  },
  {
    kind: "quote",
    text: "Although the rest of the galaxy may shudder at the Yssaril’s unseen eyes and ears, it will be terrified if it knew the ruthless imperial ambitions of the small green people.",
  },],
  },
  keleresa: {
    quote: "By the time the Senate agrees that a fire has started, a dozen worlds are already ash. Ask for forgiveness after the threat is dead.",
    quoteAuthor: "Tribunii Kuuasi Aun Jalatai",
    lore: [{
    kind: "paragraph",
    text: "When the Galactic Council first chartered the Keleres, its founders envisioned a modest investigative bureau that would mediate minor trade disputes and police the spacelanes. None of them anticipated a galaxy tearing itself apart at the seams. As ancient gene-sorcerers awoke from millennia of slumber and dimensional rifts began bleeding horrors into realspace, the fractured empires of the Council remained paralyzed by mutual distrust—each waiting for a rival to bleed first.",
  },
  {
    kind: "heading",
    text: "The Burden of Command",
  },
  {
    kind: "paragraph",
    text: "For a canny commander like Tribunii Kuuasi Aun Jalatai, the dysfunctions of the Keleres are simply a tactical equation to be solved. Drawn from the ranks of the Argent Flight, Jalatai knows that an organization built from the cast-offs, exiles, and unwanted soldiers of twenty different species will never march in parade-ground unison. The secret to commanding the Keleres lies in knowing when to use a scalpel, when to set the agency aside, and precisely who among its unruly ranks is right for a suicide mission.",
  },
  {
    kind: "paragraph",
    text: "To give the Council's shadow agency the teeth it desperately lacked, Jalatai forged a direct operational link between the Keleres intelligence apparatus and the rapid-response strike wings of the Atharal Torus, codenamed Overwing Zeta. While multi-species investigative cells—crewed by disgraced Letnev tacticians, rogue Hylar engineers, and Sol defectors—infiltrate frontier systems to track existential threats, Jalatai’s interceptor flotillas wait on high alert just beyond sensor range.",
  },
  {
    kind: "heading",
    text: "Vigilance Above the Law",
  },
  {
    kind: "paragraph",
    text: "Whenever a Keleres field cell uncovers a Vuil’raith cult, a dormant Mahact vault, or a clandestine bio-weapons facility, Jalatai does not waste days petitioning the Galactic Council for a mandate that will inevitably be vetoed by self-interested ambassadors. Instead, Overwing Zeta strikes immediately, burning the corruption from orbit and extracting the field agents before local planetary defense grids can even power up their targeting arrays.",
  },
  {
    kind: "paragraph",
    text: "Such unilateral action has made Jalatai countless enemies in the senate chambers, where outraged delegates routinely demand the Tribunii's dismissal for violating sovereign airspace. Yet for those Tribunii who possess the resolve to wield the full might of the Keleres, the rewards far outweigh the political peril: they stand as the only true bulwark between a blind, squabbling galaxy and the abyss.",
  },
  {
    kind: "quote",
    text: "The Council debates while stars go dark; the Keleres exist to make sure there is still a galaxy left when they finish talking.",
  },],
  },
  keleresm: {
    quote: "Our duty is to protect the billions of people in our galaxy, not the few hundred in these Council Chambers.",
    quoteAuthor: "Tribunii Harka Leeds",
    lore: [{
    kind: "paragraph",
    text: "Across the galaxy, planetary governors compete for trade opportunities, the Great Civilizations joust for superiority on the battlefront, and still other, more insidious factions play at shaping galactic history for their own ends. In a galaxy fraught with so many agendas, it is no surprise that the Galactic Council took it upon itself to assemble an executive agency of its own to manage its affairs. The Keleres of the Council are that force, yet they are far from the gleaming honor guard the senate once envisioned. They are a ragtag shadow service of bureaucrats, soldiers, and spies drawn from every corner of known space, perpetually at odds with themselves and rarely appreciated by the galaxy they bleed to protect.",
  },
  {
    kind: "heading",
    text: "An Army of Exiles and Liabilities",
  },
  {
    kind: "paragraph",
    text: "By decree, every member state of the Council must contribute recruits to the Keleres, selected according to local custom. In practice, the Great Powers quickly realized that the agency could be used as both a political dumping ground and a Trojan horse. Rather than sending their finest officers, planetary regimes routinely offload political dissidents, disgraced commanders, dangerous prisoners, and inconvenient whistleblowers who are too prominent to execute quietly. At the same time, intelligence ministries seed these drafts with double agents meant to clandestinely advance their homeworlds' agendas from within.",
  },
  {
    kind: "paragraph",
    text: "Left with a roster of cynical outcasts and compromised operatives, the Keleres should have collapsed in its infancy. Instead, under the leadership of Tribunii Harka Leeds, this volatility became the agency's greatest weapon. A veteran of the Mentak Coalition’s clandestine networks, Leeds recognized that conventional law enforcement could never survive the corruption of Mecatol Rex. If the Council would only give him criminals, misfits, and spies, then he would run the Keleres like an outlaw syndicate.",
  },
  {
    kind: "heading",
    text: "Black Budgets and Unsanctioned Strikes",
  },
  {
    kind: "paragraph",
    text: "Operating out of shadow ports and hidden slipways financed through Moll Primus, Leeds insulates the Keleres from the bureaucratic paralysis of the Council floor. When senate committees stall funding or leak operational details to rival empires, Leeds’s cells fund themselves—seizing the black-market vaults of planetary warlords, commandeering smuggling vessels, and turning the Great Powers' own disavowed rogues against their former masters.",
  },
  {
    kind: "paragraph",
    text: "Field teams under Leeds rarely wait for formal warrants. When timeliness is a factor, Keleres operatives cross sovereign borders in unmarked corvettes, neutralizing pirate cartels, sabotaging illegal weapons labs, and brokering backroom truces at the barrel of a gun. Time and again, Leeds stands before the Galactic Council to accept formal censure for his agents' unauthorized interventions—knowing full well that the very councilors condemning him in public sleep safer because of the crimes his people committed in the dark.",
  },
  {
    kind: "quote",
    text: "In a galaxy ruled by thieves and emperors, justice cannot afford to wait for a quorum.",
  },],
  },
  keleresx: {
    quote: "The Great Powers send us their outcasts, their whistleblowers, and their spies, never realizing they have handed us every secret required to rule them.",
    quoteAuthor: "Tribunii Odlynn Myrr",
    lore: [{
    kind: "paragraph",
    text: "The Galactic Council elects three of its own to serve as the Tribunii, the supreme directors of the Keleres. Among the delegates on Mecatol Rex, appointment to the Tribunii is viewed with a mixture of ambition and dread. While the office grants immense authority to implement the designs of the Council in a concrete way, the chaotic nature of the Keleres guarantees a steady stream of diplomatic scandals and operational failures—each of which becomes a weapon in the hands of political rivals seeking accountability.",
  },
  {
    kind: "heading",
    text: "The Lethal Seat of the Tribunii",
  },
  {
    kind: "paragraph",
    text: "So fraught is this political environment that few Councilors survive the office for long. In the first five years following the Keleres’ founding, seven different individuals held the title of Tribunii. Two were forced to resign in disgrace after covert operations went catastrophically wrong, one was killed on a field mission in the borderlands, and another was assassinated in a ruthless inter-agency power struggle right in the shadow of the Imperial Palace.",
  },
  {
    kind: "paragraph",
    text: "Into this viper's nest stepped Tribunii Odlynn Myrr. Backed by the diplomatic apparatus of the Xxcha Kingdom, Myrr understood that the true battlefield of the Keleres was not merely in deep space, but within the labyrinthine corridors of Mecatol City itself. Where previous directors tried to brute-force their fractured ranks into submission, Myrr embraced the subtle art of institutional leverage.",
  },
  {
    kind: "heading",
    text: "The Web of Operation Archon",
  },
  {
    kind: "paragraph",
    text: "Every Great Civilization believed it had cleverly infiltrated the Keleres by planting informants among the bureaucrats, archivists, and junior diplomats sent to fulfill their recruitment quotas. Myrr patiently mapped every single one of those loyalties. Instead of purging the double agents, she compartmentalized them—feeding carefully tailored intelligence back to their home capitals while using the agency’s cast-off analysts and exiled jurists to audit the secret finances and treaty violations of the Council’s most powerful members.",
  },
  {
    kind: "paragraph",
    text: "Under Myrr’s oversight, the Keleres operates as an unseen constitutional shield. Before an aggressive empire can launch a border invasion, its supply contracts are mysteriously frozen by Council injunction, its covert staging grounds are exposed to rival powers, and a multi-species Keleres peacekeeping task force drops out of warp directly across its approach vector. The Great Powers fume at the interference, yet none dare move openly against a Tribunii who holds the receipts to every treasonous whisper on Mecatol Rex.",
  },
  {
    kind: "quote",
    text: "Let the great empires believe they have filled our ranks with their pawns; every spy they send us is another thread by which we bind their hands.",
  },],
  },
  bastion: {
    quote: "There is no sacrifice I would not make to see this through. No choice but forward, no option but victory. Go. We will handle this.",
    quoteAuthor: "Lyra Keen, Shield of the Reef",
    lore: [{
    kind: "paragraph",
    text: "It started as a joint military expedition into the Lysantis Cluster to liberate a handful of independent worlds captured by the L1Z1X. Binding together the Xxcha Kingdom and the Federation of Sol, the endeavor, dubbed the Salient Sun Joint Task Force, would demonstrate that the Kingdom could be a potent fighting force and the Federation could be heroic rescuers. Most importantly, it would bind the two militaries together in a short, victorious war that would, hopefully, help to ease the ancient trauma of Archon Tau.",
  },
  {
    kind: "paragraph",
    text: "Unfortunately, the expedition encountered the Nekro Virus.",
  },
  {
    kind: "heading",
    text: "The Crucible of Retreat & Defiance",
  },
  {
    kind: "paragraph",
    text: "The fighting transformed into a desperate struggle to hold back the endless onslaught of homicidal machines. The task force fell back again and again, fighting hopeless rearguard actions while whole planets evacuated and fled deeper into the galactic core.",
  },
  {
    kind: "paragraph",
    text: "The Kingdom and the Federation grew weary of supporting these hopeless efforts. This was not the propaganda coup they had been expecting and the worlds they were defending weren’t even theirs. Eventually, both civilizations ordered their respective forces to withdraw. But those orders were not followed.",
  },
  {
    kind: "paragraph",
    text: "Over years of fighting, the Xxcha and Human soldiers had become more devoted to each other than their distant superiors, a bond forged in the bitter crucible of a hopeless cause. Subtly, at first, blaming miscommunication or the challenges of a dynamic situation on the war front, the Salient Sun ceased all communication with their superiors. Even as they were declared renegades, forces rallied to Salient Sun’s cause: civilian volunteers, soldiers of fortune, and even survivors from other failed military offensives all swelled the depleted ranks. Soon, what was once an efficiently organized joint military venture had morphed into a ragtag band of resistance fighters whose allegiance was to their comrades in arms.",
  },
  {
    kind: "heading",
    text: "The Siege of Oridian",
  },
  {
    kind: "paragraph",
    text: "But no matter how dedicated they were, they were still losing.",
  },
  {
    kind: "paragraph",
    text: "In desperation, their council of military commanders decided they had to take back at least one world to prove that they weren’t fighting a hopeless cause. The council picked Oridian. The Naaz-Rokha colony was invaded relatively recently; many of its survivors fled the ranks of the Salient Sun already, and its location at the mouth of a nebula isolated it from the Nekro fleet.",
  },
  {
    kind: "paragraph",
    text: "At first, the liberation went well. The fleet swept aside the orbital defenses, landing troops on formidable highlands in the middle of Oridian’s largest continent. But soon the ground forces found themselves surrounded by a planet of hostile machines. Hour by hour, more mechanical horrors arrived, pushing the troops back to their last defensive bastion in an isolated mountain valley.",
  },
  {
    kind: "heading",
    text: "The Fall of the Orlandio & The Seraphs",
  },
  {
    kind: "paragraph",
    text: "As Salient Sun began to retreat, a lone warship arrived in-system. FSS *Orlandio*, thought lost in a previous battle, decelerated from superluminal speeds and raced toward the planet. Its captain demanded that the Bastion’s Red Cavalry fleet clear a path for them to attach the heart of the Nekro forces. They had an Apollo-priority weapon aboard, taken from the frontier world of Thunder’s Edge.",
  },
  {
    kind: "paragraph",
    text: "The cruiser smashed into the heart of the Nekro swarms in a barely-controlled aerobraking maneuver, blasting a landing zone at the last possible moment. As the Nekro rallied to attack the crashed warship, the *Orlandio*’s cargo bays blew open and it deployed its payload.",
  },
  {
    kind: "paragraph",
    text: "It’s not clear what happened next. All the battered soldiers of Salient Sun knew was that in less than an hour, all traces of the Nekro virus vanished. Instead, drifting silently over the piles of dead machines was a pair of massive, hovering guardians of ragged metal who searched ceaselessly for more of the Nekro virus to expunge. The awestruck troops called them “seraphs,” concluding they were remnants of *Orlandio*’s weapon.",
  },
  {
    kind: "heading",
    text: "Rise of the Last Bastion",
  },
  {
    kind: "paragraph",
    text: "In the wake of the liberation, a new banner was raised over the blackened landscape of Oridian. The Salient Sun declared themselves an independent state—a bulwark against the destructive forces menacing races on the rim. Last Bastion. Tirelessly, they work to rebuild what they can on Oridian, clearing the junk-strewn wastes one kilometer at a time. The wreck of the *Orlandio* is a monument to their victory and hub of their new capital city.",
  },
  {
    kind: "paragraph",
    text: "Over Oridian, a massive orbital shipyard, the *Fortress Revelation*, is being constructed with the theft of the Seraphs, Helios and Hyperion, and backed by the personal funding of one of the Galaxy’s most enigmatic personas—Harrugh Gefhara, ex-Quier of the Hacan—who has become the public face of the Bastion. As each spacedock is completed, it fills with ships from across the galaxy. Now, after a decade of defeats, the Salient Sun has finally earned its victory. And with the galaxy hails them as heroes and their former masters quietly rage, the Command Authority of the Bastion maneuvers their fleets in defense of Thunder’s Edge.",
  },
  {
    kind: "quote",
    text: "Whatever the weapon was that was found there, they do not mean to share it.",
  },],
  },
  crimson: {
    quote: "Whatever afflicts them, it is beyond my experience. Pain unending. Rage consuming. Hope unknowing.",
    quoteAuthor: "Ahk-Syl Siven",
    lore: [{
    kind: "paragraph",
    text: "When the Creuss discovered the records leading to the ancient world of Ixt, they saw their chance to unearth a galactic monomyth and use the resulting glory to step to the forefront of all other major civilizations. Instead, they uncovered the homeworld of the dreaded Mahact gene-sorcerers.",
  },
  {
    kind: "paragraph",
    text: "When the Mahact awoke, they dominated the entire armada the Creuss had sent to Ixt. With the high technology of their homeworld, they rewrote the frequency of the Creuss’ energetic structure as one might rewrite the ending of a book. In a matter of moments they reduced each individual Creuss to an obedient thrall. As the Creuss succumbed, their blue glow shifted to an ominous red, leading to their new moniker, the “Crimson Legion.”",
  },
  {
    kind: "heading",
    text: "The Ikatena Incident and Liberation",
  },
  {
    kind: "paragraph",
    text: "The fate of their fleet horrified the undominated Creuss. Their desire to rescue their enslaved kin was arrested by the fear that the Mahact could do this again. Instead, the Creuss devoted themselves to ensuring the Mahact could never breach the Shaleri anomaly and enter the Creuss Gate. The Ikatena Incident occurred.",
  },
  {
    kind: "paragraph",
    text: "In the wake of the Deepwrought Scholarate deploying their Waveform Arbitrator, a significant portion of the Legion found itself unexpectedly freed of Mahact domination. Confused and disoriented, the Crimson Legionnaires turned on their former masters and fled the battle. Over the next few weeks, they began to regroup in out-of-the-way corners of the galaxy and take stock of their situation.",
  },
  {
    kind: "paragraph",
    text: "The Arbitrator had broken the Mahact hold over the Crimson Legionnaires, but it had not reversed the changes done to them on a fundamental level. In fact, it may have changed them even further. Now the Creuss could just sense how wrong they felt. It was as though the very photons of their beings were trying to tear themselves apart, restrained only by the suits of armor they wore.",
  },
  {
    kind: "heading",
    text: "Exile to Ahk Creuxx",
  },
  {
    kind: "paragraph",
    text: "The one desire every former Crimson Legionnaire shared was to return home, so the remnants of the armada made for the Creuss Gate. But when they first entered Shaleri space they were intercepted by their former kin. Hasty explanations avoided outright combat, but the Creuss refused to allow the former Legionnaires passage. Even across the gulf of space, the Creuss could sense the fundamental changes and feared the frequency alterations made by the Mahact could still cascade to untainted Creuss—or even their home dimension.",
  },
  {
    kind: "paragraph",
    text: "Angered, saddened, and betrayed, the crimson Creuss attempted to open a new wormhole gate into the Creuss dimension with the drives aboard their largest ships. They successfully opened a new wormhole, but when they passed through it they found themselves in a strange alternate realm. It was brimming with the same energy as their old home, but on a different phase. While they could survive here without their suits, to the Creuss this new dimension was like a barren desert in comparison to the lush complexity of their home.",
  },
  {
    kind: "paragraph",
    text: "Unfortunately, they were stuck. They could travel back to the known galaxy, but would eventually establish a truce with the rest of the Creuss, when a delegation finally traveled through the Creuss Gate. The energy patterns of their old home obliterated the crimson Creuss in an instant. It turned out that only in this new realm, which they dubbed Ahk Creuxx, could the crimson Creuss live.",
  },
  {
    kind: "heading",
    text: "The Crimson Rebellion and Thunder's Edge",
  },
  {
    kind: "paragraph",
    text: "In the time since the Ikatena Incident, the Crimson Rebellion has worked to make the best of their new life. The parallel realm of Ahk Creuxx has also begun to “birth” new crimson Creuss in the same manner as their old universe, so the population of the Rebellion has begun to grow. But even new crimson Creuss are plagued with the same sense of wrongness as their kin, and the entire species still longs for a true homecoming.",
  },
  {
    kind: "paragraph",
    text: "Despair has swept through the population. It is entirely possible that the Crimson Rebellion would have launched itself on a self-destructive war of vengeance against the Mahact in hopes of obliterating both itself and its former oppressors. However, even as the Crimson Rebellion established contact with the known galaxy, they learned of the events at Oridian and the strange power at the heart of the world called Thunder’s Edge.",
  },
  {
    kind: "paragraph",
    text: "The Crimson Rebellion has no ruler. After years of utter enslavement, none of the crimson Creuss wish to be controlled by another ever again. But among the ranks of the Rebellion two schools of thought have taken hold. Some of the crimson Creuss wish to seat themselves in the Galactic Council and even claim the Imperial Throne. With the might of the galaxy behind them, they can avenge themselves against the Mahact.",
  },
  {
    kind: "quote",
    text: "Others look to the marvelous power of Thunder’s Edge, and wonder. Perhaps the crimson Creuss can wield it to repair their broken people, and to finally feel the peace of a true home.",
  },],
  },
  deepwrought: {
    quote: "~Together-sing-one-together-~sing-deep-together-ends-suffering- -life-triumphs-death-",
    quoteAuthor: "Aello, Kieros",
    lore: [{
    kind: "paragraph",
    text: "Facing grave threats to the galaxy, some factions within the great powers sought to work together, creating the Keleres and striving for better relations between all.",
  },
  {
    kind: "heading",
    text: "The Waveform Arbitrator",
  },
  {
    kind: "paragraph",
    text: "One of these factions was the Universities of Jol-Nar. They sought a way to break the domination of the Mahact’s most dangerous thralls, the infamous Crimson Legionnaires—and most importantly, to prevent similar mind-control from affecting any Hylar victims. The newly developed Waveform Arbitrator could shatter the Mahact control of any Crimson Legionnaires—or others—within a million kilometers. At least in theory.",
  },
  {
    kind: "paragraph",
    text: "This breakthrough was developed by the Deepwrought Scholarate, a prominent school within Jol-Nar’s universities. The Deepwrought, led by Ta Zern and known for their desire to propagate knowledge throughout the galaxy, wanted to give the blueprints to each of the Great Civilizations. The rest of the Universities disagreed. Furthermore, they refused to risk using it themselves. The frustrated Deepwrought secretly contracted the Ral Nel Consortium, whose microprocessors were advanced enough to run the quintillion calculations necessary to track, override, and break the Mahact dominance signals. Together, they constructed the first Arbitrator in secret.",
  },
  {
    kind: "heading",
    text: "The Trap at Ikatena",
  },
  {
    kind: "paragraph",
    text: "Next, the Deepwrought sought a place to deploy their weapon. They had to engage the Mahact in a major fleet, which would risk losing a sizable portion of the Jol-Nar fleet. The Headmaster and Circle of Regents would not approve such a gamble, so Ta Zern lied. He convinced the Universities that the oceanic world of Ikatena, recently captured by King Zel Tel Mosin, was weakly defended. Meanwhile, University agents leaked plans of the attack to Mosin, convincing him to reinforce his position with every Crimson Legionnaire at his disposal.",
  },
  {
    kind: "paragraph",
    text: "When the Universities’ fleet attacked, both sides thought they were springing a trap. The Jol-Nar pummeled the orbital defenses while their allies, resistance cells of the native Kieros people, established the ocean world’s floating PDS platforms. But even as the Universities’ ships settled into orbit, a massive Crimson Legionnaire fleet emerged from the dark of Ikatena’s largest moon. The Jol-Nar were trapped at the bottom of a planetary gravity well, and their ships began to burn.",
  },
  {
    kind: "paragraph",
    text: "Then, Ta Zern deployed the Arbitrator. Suddenly, the various Creuss vessels flashed with a rainbow of colors, before settling to a dull, red glow. They began to scatter in all directions, some accelerating for deep space while others attacked the Mahact. Deserted by his former thralls, Zel Tel Mosin could only rage helplessly until beam cannons charred his flagship apart.",
  },
  {
    kind: "heading",
    text: "Independence and the Conclave",
  },
  {
    kind: "paragraph",
    text: "In the aftermath of the “Ikatena Incident,” Ta Zern and the Deepwrought expected to be celebrated as heroes. However, the Universities’ leadership knew that the Deepwrought had illegally shared the Arbitrator blueprints and duped their fleet into a dangerous battle. They cried treason and demanded Ta Zern’s head.",
  },
  {
    kind: "paragraph",
    text: "Instead, the Deepwrought Scholarate declared itself independent and liberated the Ikatena Conclave of Singers. The Kieros were more than willing to welcome Ta Zern’s rebels, and together they began establishing a new home shared by both Kieros and Hylar. New ships began to drift from orbital gray-docks, developed from cutting-edge Deepwrought designs and crewed by eager Kieros enlistees. Although the Deepwrought had not expected to become a military force, they knew a strong navy was one of the few means to keep their Universities from exacting vengeance.",
  },
  {
    kind: "heading",
    text: "Pelagic Enclaves & Thunder's Edge",
  },
  {
    kind: "paragraph",
    text: "The other was to make as many friends as possible. Since the Deepwrought mostly consisted of two aquatic peoples, they began approaching various civilizations with a proposal: allow the Scholarate to establish enclaves in the otherwise unused depths of their planet’s oceans, and in exchange those enclaves would share their bounty of research and discoveries. Already, many civilizations have jumped at the chance to gain access to Deepwrought technology, and every day more and more Deepwrought citizens settle in the pelagic depths of far-off worlds.",
  },
  {
    kind: "paragraph",
    text: "To the surprise of everyone involved, the Deepwrought Scholarate found itself propelled from a collection of eclectic scientists and researchers to some of the founding members of a civilization. Even as they frantically work with their newfound Kieros allies to build and maintain a working alliance, some have begun to take interest in the discoveries coming from the strange world of Thunder’s Edge.",
  },
  {
    kind: "quote",
    text: "Perhaps that planet’s secrets can catapult the Deepwrought Scholarate from struggling newcomer to a major player on the galactic stage.",
  },],
  },
  ralnel: {
    quote: "The great web of obligation binds us all as surely as gravity. Those who would cheat us would cheat the galaxy of its right to exist.",
    quoteAuthor: "Actuary General 'Watchful' Ojz",
    lore: [{
    kind: "paragraph",
    text: "The Ral Nel are known for their fast ships, their advanced microprocessor technology, and their frustrating refusal to share either with the galaxy at large—except on their own terms, for cash in hand. After all, the rest of the galaxy can’t be trusted to honor their debts, and the twin worlds of Ral Orz run on a system of finely balanced obligation.",
  },
  {
    kind: "heading",
    text: "The Twin Worlds and the Zio Qen",
  },
  {
    kind: "paragraph",
    text: "Mez Lo Orz Zio Zeha is a more heavily populated world. From orbit, one can spot the huge circular cities scattered across the surface and the constant stream of shuttle traffic. Fei Zeha is extremely developed, and each city is home and stronghold to a different zio qen. The closest translation is “corporation,” but to the Ral Nel, zio qen are far more complex. They are vertically integrated conglomerates comprising hundreds of smaller businesses, and also serve as governments and provide civic services for their millions of employees. Sun-drenched Rep Lo Orz Qet, its hemispherical deserts bisected by a tropical equatorial sea, is also completely controlled by dozens of zio qen.",
  },
  {
    kind: "heading",
    text: "Transactions, Debt, and Corporate Strife",
  },
  {
    kind: "paragraph",
    text: "These mega-corporations are born from the culture and psychology of the Ral Nel, specifically their need to frame everything in the form of a transaction. Whatever a Ral Nel does is either to repay a debt they owe or in anticipation of receiving something in the future. This mercenary outlook is tempered by the Ral Nel’s practice of inter-generational debt. Ral Nel consider the rearing of children to create a debt that the children fulfill by supporting their elders, to be supported in turn by their own children. Scaled over the long term and the breadth of their society, Ral Nel zio qen are reluctant to pursue short-term gains at the expense of the long-term debts from their future society that they may need to survive. It has also spared their original homeworld, Qet, some of the worst excesses of corporate exploitation; such actions are limited by the Ral Nel’s debts to the biosphere that evolved them. Instead, the majority of development has taken place on neighboring Fei Zeha.",
  },
  {
    kind: "paragraph",
    text: "This attitude only goes so far in reigning in internecine conflict, however. Nearly all Ral Nel work for a zio qen, and their transnational loyalty is first and foremost to that zio qen, not to the Ral Nel as a whole. In fact, all zio qen are cooperatively owned by their employees, which reinforces those bonds of loyalty. Conflict between zio qen is common enough to be mundane, ranging from malicious corporate deals and hostile takeovers to actual armed incursions by corporate strike teams. Only the potential debts that can be incurred by hostile action keep the fights from rising above the level of surgical strikes.",
  },
  {
    kind: "heading",
    text: "The Consortium and the Wider Galaxy",
  },
  {
    kind: "paragraph",
    text: "These quirks of Ral Nel society mean their planetary government is merely a consortium of the zio qen who happen to have the most political and economic power overseas by a board of zio leaders appointed by their zio qen shareholders. Because power depends largely on favors owed and given, the zio who run the consortium can change at any time. Other civilizations who maintain diplomatic relations with the Ral Nel Consortium have grown used to dealing with a new set of representatives who are not warning at all. The larger obstacle to dealing with the Consortium, however, is that the Ral Nel have learned from hard experience that outsiders have little incentive to engage in their system of debts and credit. While the Consortium has had quite a bit of success running various courier, logistic, and technology concerns across the galaxy, they only do so for immediate payment and rarely consent to long-term contracts that they don’t believe outsiders will honor.",
  },
  {
    kind: "heading",
    text: "The Waveform Arbitrator & The Greatest Debt",
  },
  {
    kind: "paragraph",
    text: "The Deepwrought and their Waveform Arbitrator caused the Consortium to set aside their isolationist attitudes. The Arbitrator was too powerful a defense for the zio to ignore, and twenty of the largest zio qen formed the most powerful Consortium in Ral Nel history in order to build it. Most battling to the zios, the Deepwrought Scholarate appeared to be motivated not by the typical short-sighted greed the Ral Nel expected from outsiders, but by a keen awareness of the mutual debts that would reasonably exist between great powers if those great powers were sane (that is to say, behaving like proper Ral Nel). Since the Arbitrator’s successful deployment, the current Consortium has remained stable, and has been tentatively making deals with other civilizations as well. Ral Nel microprocessors and courier services are in high demand, and the recent theorems of galactic relations has created a bit of a run on Ral Nel goods and services.",
  },
  {
    kind: "paragraph",
    text: "Meanwhile, the goal of the Consortium’s zio is simple: to guarantee the Ral Nel’s place in the galaxy. The rest of the galaxy owes them debts it can never repay. If the Ral Nel can use their unrivaled microprocessor technologies to take control of the strange forces within the world of Thunder’s Edge, they can use that power to save the galaxy from the forces that threaten to destroy it.",
  },
  {
    kind: "quote",
    text: "And that salvation would create the biggest debt of all.",
  },],
  },
};

/**
 * Domyślne ścieżki portretu próbowane po kolei (pierwsza istniejąca wygrywa).
 * Kolejność: png → jpg → jpeg → webp (Twoje pliki to przeważnie png).
 */
export function defaultPortraitCandidates(factionId: string): string[] {
  const key = portraitKey(factionId);
  return [
    `/faction_portraits/${key}.png`,
    `/faction_portraits/${key}.jpg`,
    `/faction_portraits/${key}.jpeg`,
    `/faction_portraits/${key}.webp`,
  ];
}

/**
 * Warianty jednej frakcji dzielą jeden portret: Keleres (keleresm/keleresx/keleresa)
 * używa pliku `keleres.png`, więc nie trzeba dublować grafiki per wariant.
 */
const PORTRAIT_FAMILIES: Record<string, string> = {
  keleresm: "keleres",
  keleresx: "keleres",
  keleresa: "keleres",
};

function portraitKey(factionId: string): string {
  return PORTRAIT_FAMILIES[factionId] ?? factionId;
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
