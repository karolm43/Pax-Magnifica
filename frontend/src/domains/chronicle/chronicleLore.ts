/*
 * TEKSTY KRONIKI IMPERIUM („Codex of the Lazax") — wszystko, co czyta się w księdze, jest tutaj.
 * Edytuj swobodnie: każda pula to lista wariantów, silnik wybiera jeden deterministycznie
 * (to samo zdarzenie zawsze dostaje ten sam tekst), więc im więcej wariantów, tym mniej powtórzeń.
 *
 * Znaczniki w tekście (nieznane zostają puste):
 *   {A} główny bohater zdarzenia   {Ae} to samo, ale z przydomkiem („the Federation of Sol")
 *   {B} druga strona               {Be} jej przydomek
 *   {planet} planeta               {system} system             {obj} cel (punktowany)
 *   {law} prawo/agenda             {tech} technologia          {relic} relikt
 *   {leader} lider                 {card} karta                {n} liczba
 *   {round} numer rundy            {ordinal} „first", „second"…
 * Tekst bitew pochodzi z `domains/lore/battleLore.ts` (ten sam co w oknie wyniku bitwy).
 */

export type ChronicleKind =
  | "prologue"
  | "battle"
  | "conquest"
  | "homeworld"
  | "settle"
  | "score"
  | "law"
  | "agenda"
  | "tech"
  | "relic"
  | "leader"
  | "hero"
  | "throne"
  | "fall"
  | "fracture"
  | "supernova"
  | "deal"
  | "strategy"
  | "explore"
  | "speaker"
  | "victory";

/** Zdarzenia „drugiego planu": ukryte w widoku „Major events", widoczne po przełączeniu. */
export const MINOR_KINDS: ReadonlySet<ChronicleKind> = new Set([
  "tech",
  "deal",
  "strategy",
  "explore",
  "speaker",
]);

/** Przydomki frakcji do zdań w stylu kronikarskim; brak wpisu = sama nazwa frakcji. */
export const FACTION_EPITHET: Record<string, string> = {
  arborec: "the Arborec, children of the Symphony",
  argent: "the Argent Flight, wings of the Zephyrian sky",
  bastion: "the Bastion, wardens of the old walls",
  cabal: "the Vuil'raith Cabal, who feed on what they conquer",
  crimson: "the Crimson Rebellion, banner of the unbowed",
  deepwrought: "the Deepwrought Scholarate, keepers of the deep",
  empyrean: "the Empyrean, watchers of the Void",
  ghost: "the Ghosts of Creuss, born of the gate",
  hacan: "the Emirates of Hacan, merchant-princes of the stars",
  jolnar: "the Universities of Jol-Nar, masters of the hidden law",
  keleresa: "the Council Keleres, heirs of the Lazax ledger",
  keleresm: "the Council Keleres, heirs of the Lazax ledger",
  keleresx: "the Council Keleres, heirs of the Lazax ledger",
  l1z1x: "the L1Z1X Mindnet, the cold logic of the Dyson spheres",
  letnev: "the Barony of Letnev, iron lords of the dark",
  mahact: "the Mahact Gene-Sorcerers, lords of the long memory",
  mentak: "the Mentak Coalition, corsairs of the Fringe",
  muaat: "the Embers of Muaat, who forge ships from stars",
  naalu: "the Naalu Collective, whose gaze reaches before they do",
  naaz: "the Naaz-Rokha Alliance, tenders of the living machine",
  nekro: "the Nekro Virus, the endless hunger",
  nomad: "the Nomad, drifting blade of the lost",
  obsidian: "the Obsidian, who answer to no light",
  ralnel: "the Ral Nel Consortium, brokers of the rebuilt",
  saar: "the Clan of Saar, a people who never stop moving",
  sardakk: "the N'orr, whose cry is war",
  sol: "the Federation of Sol, builders of the great shipyards",
  titans: "the Titans of Ul, who sleep beneath their world",
  winnu: "the Winnu, who remember their place in the Lazax court",
  xxcha: "the Xxcha Kingdom, patient as stone",
  yin: "the Yin Brotherhood, who walk willingly into the fire",
  yssaril: "the Yssaril Tribes, masters of the quiet knife",
};

export type Pool = string[];

const ORDINALS = [
  "zeroth",
  "first",
  "second",
  "third",
  "fourth",
  "fifth",
  "sixth",
  "seventh",
  "eighth",
  "ninth",
  "tenth",
];

export const ordinalWord = (n: number): string => ORDINALS[n] ?? `${n}th`;

/** O czym była poprzednia runda — wybiera kronikarza i pulę zdań otwierających. */
export type OpenerTheme =
  | "start"
  | "throne"
  | "fall"
  | "homeworld"
  | "hero"
  | "war"
  | "law"
  | "relic"
  | "score"
  | "quiet";

export type Chronicler = { name: string; title: string; themes: OpenerTheme[] };

/**
 * KANON: dziesięciu kronikarzy Scriptorium Custodianów na Mecatol Rex — archiwistów, którzy
 * od upadku Lazax spisują dzieje domów (motto Custodia Vigilia z assetów: „Pax magnifica,
 * bellum gloriosum"). Imiona w stylu Winnu (Berekar Berekon, Rickar Rickani, Perdin Perdona:
 * podwojony rdzeń). Rozdział cytuje kronikarza, którego specjalność pasuje do tego, co
 * wydarzyło się w POPRZEDNIEJ rundzie; ten sam kronikarz nie wraca, dopóki są wolni.
 */
export const CHRONICLERS: Chronicler[] = [
  { name: "Tavorin Tavoris", title: "Archivist of the Silent Court", themes: ["start", "quiet"] },
  { name: "Marek Maranth", title: "Warden of the Long Record", themes: ["war"] },
  { name: "Halvar Halvanis", title: "Scribe of the Fallen Throne", themes: ["fall", "homeworld"] },
  { name: "Ilvar Ilvanor", title: "Voice of the Last Council", themes: ["law"] },
  { name: "Corvan Corvinus", title: "Keeper of the Lazax Ledger", themes: ["score"] },
  { name: "Seldin Seldara", title: "Reader of Ashes", themes: ["war", "homeworld"] },
  { name: "Doran Doravel", title: "Chronicler of Mecatol", themes: ["throne"] },
  { name: "Pelor Pelanis", title: "Keeper of the Unwritten Hours", themes: ["quiet", "score"] },
  { name: "Berenik Berenis", title: "Seeker of Relics", themes: ["relic"] },
  { name: "Ostrin Ostravel", title: "Last Witness of the Custodians", themes: ["hero", "fall"] },
];

/**
 * Zdania otwierające rozdział — o tym, co działo się w poprzedniej rundzie. Znaczniki:
 * {A} {B} bohaterowie (z najważniejszego zdarzenia), {place} miejsce, {n} liczba bitew,
 * {detail} nazwa prawa/reliktu/celu, {lead} lider wyścigu, {vp} jego punkty.
 */
export const OPENERS: Record<OpenerTheme, Pool> = {
  start: [
    "No Emperor sat on Mecatol Rex, and the whole galaxy knew it. The Custodians keep the gate and I keep the record. Let the houses begin.",
    "The throne of the Lazax stands empty. Pax magnifica, bellum gloriosum: peace is great, they said, and war is glorious. The houses will test both.",
  ],
  war: [
    "The last cycle belonged to the sword: {n} battles, and the fiercest at {place}, where {A} met {B}. I counted the dead, as I am bound to.",
    "Smoke still hung over {place} when the new cycle began. {A} and {B} had spoken there in the only language the stars respect.",
    "Last cycle, {A} struck and {B} answered at {place}. The ledger of the Custodians does not take sides, but it does remember.",
  ],
  homeworld: [
    "A thing I never thought to write: {place}, the cradle of {B}, has fallen to {A}. The new cycle opens over that wound.",
    "{A} stands on {place} now, the heart of {B}. Houses have fallen before, but never so quietly as in the last cycle.",
  ],
  fall: [
    "A house is gone: {A}. I write its name once more, because after this cycle no one else will.",
    "The last cycle took {A} from the table. The stars do not mourn, so the scribes must.",
  ],
  throne: [
    "The seal of Mecatol Rex is broken. {A} lifted it, and the Custodians stepped aside. From this cycle on, the throne is a prize and not a memory.",
    "The Custodians have left their post on Mecatol, and {A} holds the keys. The race for the throne is truly open.",
  ],
  hero: [
    "In the last cycle {A} did what the old songs only dared to promise. The galaxy has not yet decided whether to cheer or to fear.",
    "Something was loosed in the last cycle by {A}. I will write it down exactly, and let the next scribes decide what it meant.",
  ],
  law: [
    "The Council spoke last cycle: \u201c{detail}\u201d is now law. The voting hall is quiet, and quiet halls are where plots are drafted.",
    "A new law, \u201c{detail}\u201d, binds the houses. Those who voted for it are smiling. Those who did not are reading the fine print.",
  ],
  relic: [
    "{A} came away from the last cycle with {detail}. Ancient things do not wake without a price, and the price has not yet been named.",
    "{detail} has a new keeper: {A}. The Lazax buried such things for a reason, and I mean to find out which.",
  ],
  score: [
    "{A} finished \u201c{detail}\u201d and the ledger leaned their way. {lead} leads the race with {vp}, though a lead is only a place to be attacked from.",
    "The last cycle was one of quiet ambition. \u201c{detail}\u201d went to {A}, and {lead} stands first with {vp} points.",
  ],
  quiet: [
    "The last cycle passed in near silence. I have rarely had so little to write, and never trusted such a silence less.",
    "Nothing of note happened last cycle, and that is the most worrying thing I can put in a ledger.",
  ],
};

/** Wiersz o stanie punktów na koniec rozdziału. */
export const STANDINGS_LEAD: Pool = [
  "At the close of the cycle {A} stood highest in the race for the throne with {n} points.",
  "When the cycle ended, {A} led the race with {n} points, and the others took note.",
  "The ledgers closed with {A} ahead on {n} points.",
];

export const STANDINGS_TIE: Pool = [
  "At the close of the cycle the race was tied at {n} points. Nobody dared call the throne.",
  "The cycle ended in a dead heat at {n} points.",
];

export const POOLS: Record<Exclude<ChronicleKind, "battle">, Pool> = {
  prologue: [
    "{n} houses answered the call of the empty throne. This is the chronicle of what they did.",
    "The Lazax are gone. {n} houses remain, and every one of them intends to be remembered.",
  ],
  conquest: [
    "{Ae} took {planet} from {B}. The banners above {planet} changed in a single day.",
    "{planet} fell to {Ae}. {B} watched it go and did not forgive.",
    "The garrisons of {B} on {planet} were broken, and {A} raised a new flag over the ruins.",
    "{A} marched into {planet} and left {B} with nothing but the memory of owning it.",
    "By the end of the day {planet} belonged to {Ae}. {B} would remember the date.",
  ],
  homeworld: [
    "{Ae} stood on {planet}, the cradle of {B}, and the sky was full of strangers.",
    "{planet} was the heart of {B}. Now {A} holds it, and the heart beats for someone else.",
    "It was a thing no one had thought possible: {planet}, homeworld of {B}, in the hands of {Ae}.",
  ],
  settle: [
    "{Ae} claimed {planet} and put down roots.",
    "No fleet defended {planet}. {A} simply arrived, and it was theirs.",
    "{A} planted a claim on {planet}, and the empire grew by one world.",
    "{planet} gained a new master: {Ae}.",
  ],
  score: [
    "{Ae} fulfilled \"{obj}\" and was counted among the great.",
    "\"{obj}\" was finished by {A}, and the Speaker had no choice but to mark it.",
    "{A} achieved \"{obj}\". It moved them closer to the throne.",
    "The deed was called \"{obj}\", and it belonged to {Ae}.",
  ],
  law: [
    "The Council passed \"{law}\". The vote was close enough to be remembered.",
    "\"{law}\" became the law of the galaxy, and the voting hall was quiet for a moment.",
    "The Council enacted \"{law}\". The ink was not yet dry when someone began looking for a way around it.",
    "By the will of the Council, \"{law}\" now binds the houses.",
  ],
  agenda: [
    "The Council convened to hear \"{law}\".",
    "\"{law}\" was brought before the Council, and every delegate began to count their votes.",
    "A new matter was laid before the Council: \"{law}\".",
  ],
  tech: [
    "{Ae} mastered {tech}. The labs of other houses fell quiet with envy.",
    "{A} finished work on {tech}.",
    "In the laboratories of {A}, {tech} stopped being a theory.",
  ],
  relic: [
    "{Ae} claimed the relic {relic}, a thing older than the Lazax themselves.",
    "{relic} passed into the hands of {A}. The ancients had left it for someone, and now someone had come.",
    "From the dust of a forgotten world {A} lifted {relic}.",
  ],
  leader: [
    "{leader} answered the call of {Ae}.",
    "{A} unsealed {leader}, and the house of {A} had a new voice.",
    "The service of {leader} to {Ae} was sworn that day.",
  ],
  hero: [
    "{leader} of {Ae} entered legend. What they did was not for the faint of heart.",
    "{A} called {leader}, and the stars bent.",
    "The great champion {leader} acted for {Ae}, and history was altered.",
  ],
  throne: [
    "The Custodians left Mecatol Rex. {Ae} lifted the seal of the Lazax and opened the throne room to the galaxy.",
    "{A} broke the old seal on Mecatol Rex. The Custodians were done, and the race had truly begun.",
    "On Mecatol Rex the Custodians gave way to {Ae}, and the throne was within reach of every house.",
  ],
  fall: [
    "{A} was lost. {Ae} left the table, and the stars closed over their name.",
    "The house of {A} fell silent. {Ae} had run out of ships, worlds and time.",
    "Their last world taken, {Ae} faded from the race for the throne.",
  ],
  fracture: [
    "{Ae} tore open the Fracture. What lay beyond had been waiting for a very long time.",
    "{A} entered the Fracture and the galaxy trembled.",
  ],
  supernova: [
    "{A} detonated the Nova Seed. {system} was a world, and now it is a lesson.",
    "A new sun was born where {system} had been. {Ae} would not explain.",
  ],
  deal: [
    "{A} and {B} came to an agreement, the kind that is spoken quietly and remembered for a long time.",
    "{Ae} and {B} sat down together and rose with a deal. Neither said what it cost.",
    "{A} traded with {B}. In this galaxy that is sometimes more dangerous than war.",
  ],
  strategy: [
    "{Ae} played {card}.",
    "{A} turned the tide of the cycle with {card}.",
    "{card} was {A}'s move.",
  ],
  explore: [
    "{Ae} explored {planet} and found something that was not on the charts.",
    "{A} sent surveyors to {planet}. They returned with {card}.",
  ],
  speaker: [
    "{Ae} took the gavel and became Speaker.",
    "The right to speak first passed to {A}.",
  ],
  victory: [
    "{Ae} took the throne of the Lazax. The chronicle can end here, though the history of the galaxy does not.",
    "{A} sat on the throne of Mecatol Rex. Every house that had opposed it knelt, or remembered how to.",
    "The race was over. {Ae} was Emperor, and the galaxy had a new name for the old order.",
  ],
};

/** Uchylenie prawa przez Radę. */
export const REPEAL: Pool = [
  "The Council repealed \"{law}\". What was law yesterday is now only a story.",
  "\"{law}\" was struck from the books by a vote of the Council.",
];

/** Podtytuły (małe nagłówki) wpisów. */
export const KIND_LABEL: Record<ChronicleKind, string> = {
  prologue: "Prologue",
  battle: "Battle",
  conquest: "Conquest",
  homeworld: "A Homeworld Falls",
  settle: "New Colony",
  score: "A Deed Recorded",
  law: "The Council Decides",
  agenda: "The Council Convenes",
  tech: "Breakthrough",
  relic: "Relic Found",
  leader: "A Leader Rises",
  hero: "A Hero Acts",
  throne: "The Throne Opens",
  fall: "A House Falls",
  fracture: "The Fracture",
  supernova: "Nova Seed",
  deal: "A Deal Struck",
  strategy: "Strategy",
  explore: "Exploration",
  speaker: "Speaker",
  victory: "The Throne Is Taken",
};
