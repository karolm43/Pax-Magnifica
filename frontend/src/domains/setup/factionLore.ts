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
  },
  firmament:{
quote:"Asking 'who should rule us?' is overlooking a more important question: 'why have rulers at all?'",
quoteAuthor:"Sharsiss of Druaa",
lore:[
  {
    kind: "paragraph",
    text: "Whether the Firmament is a collection of revolutionary idealists or a sprawling and secretive criminal empire is a matter of perspective. To the Great Powers, the important question is: Who will be the next to inherit the Imperial throne? But the founders of the Firmament dared to ask: ",
  },
  {
    kind: "quote",
    text: "Why should there be an Imperial throne at all?",
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
    text: "Then a young Druaa dissident uncovered an ancient artifact on a forgotten world. Sharsiss grew up on Druaa, consigned to the lower roles in his society. He grew sick of the “equality” of the Naalu Collective and left as soon as he was able. Sharsiss rose to become a prominent player in the Firmament’s dispersed leadership, and became an obvious choice to lead the latest expedition searching for fragments of the Lazax maps. On distant Oranth XI, Sharsiss found a crashed vault ship. Deep in its hold, the young Druaa uncovered the ships only cargo: a massive sword called the Obsidian. The blade seemed perfectly black, though Sharsiss thought he could make out something stirring in its inky depths. Then he grasped the hilt...",
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
