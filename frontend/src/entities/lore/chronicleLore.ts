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
 * Tekst bitew pochodzi z `entities/lore/battleLore.ts` (ten sam co w oknie wyniku bitwy).
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
  argent: "the Argent Flight, zealous wings of the Torus",
  bastion: "the Last Bastion, wardens of the unbroken wall",
  cabal: "the Vuil'raith Cabal, who feed on what they conquer",
  crimson: "the Crimson Rebellion, banner of the unbowed",
  deepwrought: "the Deepwrought Scholarate, keepers of the deep",
  empyrean: "the Empyrean, watchers of the Void",
  firmament: "the Firmament, quiet architects of the outer dark",
  ghost: "the Ghosts of Creuss, born of the gate",
  hacan: "the Emirates of Hacan, merchant-princes of the stars",
  jolnar: "the Universities of Jol-Nar, masters of the hidden law",
  keleresa: "the Council Keleres, wardens of the Argent wing",
  keleresm: "the Council Keleres, enforcers of the Fringe",
  keleresx: "the Council Keleres, keepers of the Lazax ledger",
  l1z1x: "the L1Z1X Mindnet, cybernetic heirs of the Lazax",
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
 * od upadku Lazax spisują dzieje galaktycznych potęg (motto Custodia Vigilia z assetów:
 * „Pax magnifica, bellum gloriosum"). Imiona w stylu Winnu (Berekar Berekon, Rickar Rickani:
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
    "No Emperor sat on Mecatol Rex, and the whole galaxy knew it. The Custodians keep the gate and I keep the record. Let the contenders begin.",
    "The throne of the Lazax stands empty. Pax magnifica, bellum gloriosum: peace is great, they said, and war is glorious. Every empire at the table will test both.",
    "A fresh volume opens in the Scriptorium, its pages blank and waiting. The fleets are fueled along the rim, and every envoy smiles with clenched teeth.",
    "The old Empire has been dust for centuries, yet its chair still commands the room. I dip my stylus and wait to see who moves first.",
  ],
  war: [
    "The last cycle belonged to the sword: {n} battles, and the fiercest at {place}, where {A} met {B}. I counted the dead, as I am bound to.",
    "Smoke still hung over {place} when the new cycle began. {A} and {B} had spoken there in the only language the stars respect.",
    "Last cycle, {A} struck and {B} answered at {place}. The ledger of the Custodians stays impartial, though it forgets nothing.",
    "My ink barely dried between dispatches last cycle. {n} engagements scarred the star-charts, with {A} and {B} bleeding hardest at {place}.",
    "Diplomacy stepped aside for {n} battles in the previous cycle. Above {place}, {A} and {B} reminded the galaxy how quickly treaties burn.",
    "Another cycle written in hull plating and ash. Across {n} clashes, the loudest reckoning fell upon {place}, where {A} and {B} refused to yield.",
    "The repair yards worked through the night after {n} engagements last cycle. None left deeper scars than the fight between {A} and {B} at {place}.",
    "Warships spoke louder than senators last cycle: {n} battles logged, culminating in the collision of {A} and {B} at {place}.",
  ],
  homeworld: [
    "A thing I never thought to write: {place}, the cradle of {B}, has fallen to {A}. The new cycle opens over that wound.",
    "{A} stands on {place} now, the heart of {B}. Realms have fallen before, yet rarely so swiftly as in the last cycle.",
    "The banners of {A} fly over {place}, where {B} once felt untouchable. Every other capital doubled its watch before dawn.",
    "Last cycle proved that no border is sacred. {B} lost {place} to {A}, and the whole Council suddenly remembered how thin its shields are.",
  ],
  fall: [
    "A great power is gone: {A}. I write its name once more, because after this cycle no one else will.",
    "The last cycle took {A} from the table. The stars do not mourn, so the scribes must.",
    "One fewer seat was filled when the Conclave bells rang. {A} vanished in the last cycle, leaving only debt and debris behind.",
    "I closed the ledger of {A} before sunrise. Empires rarely end in song; most simply run out of worlds.",
  ],
  throne: [
    "The seal of Mecatol Rex is broken. {A} lifted it, and the Custodians stepped aside. From this cycle on, the throne is an open prize.",
    "The Custodians have left their post on Mecatol, and {A} holds the keys. The race for the throne has begun in earnest.",
    "The ancient gates of Mecatol City stand wide after {A} claimed the square. Every fleet in the galaxy just recalibrated its jump-drives.",
    "History pivoted on Mecatol Rex last cycle. {A} cleared the Custodian garrison, and now every rival measures the distance to the Core.",
  ],
  hero: [
    "In the last cycle {A} did what the old songs only dared to promise. The galaxy has yet to decide whether to cheer or to fear.",
    "Something formidable was loosed in the last cycle by {A}. I will record it faithfully and let future scribes judge the cost.",
    "The tactics of ordinary wars bent last cycle when {A} played its greatest hand. Admirals across the sector are still rewriting their plans.",
    "Legends rarely announce themselves politely. What {A} unleashed in the last cycle left half the Council staring in stunned silence.",
  ],
  law: [
    "The Council spoke last cycle: \"{detail}\" is now law. The voting hall is quiet, and quiet halls are where plots are drafted.",
    "A new decree, \"{detail}\", binds the galaxy. Those who voted for it are smiling; those who opposed it are reading the fine print.",
    "After hours of bargaining, \"{detail}\" entered the imperial code. Already, three delegations are testing how far the wording bends.",
    "Ink replaced plasma in the last cycle as \"{detail}\" passed the Conclave. Even bad laws leave deep footprints.",
    "The previous cycle ended beneath the Speaker's gavel with \"{detail}\" inscribed in the ledger. Half the chamber left furious.",
    "Senators traded favors until dawn to pass \"{detail}\". Now the fleets must live with what the diplomats signed.",
  ],
  relic: [
    "{A} came away from the last cycle with {detail}. Ancient things wake with a price, and that price has yet to be named.",
    "{detail} has a new keeper: {A}. The Lazax buried such instruments for a reason, and we are about to learn which one.",
    "From the dust of forgotten ages, {A} claimed {detail}. Scholars in the Scriptorium grew uneasy the moment the report arrived.",
    "Old power returned to the board last cycle when {A} secured {detail}. Whoever holds the past tends to reshape the present.",
  ],
  score: [
    "{A} finished \"{detail}\" and the ledger leaned their way. {lead} leads the race with {vp} points, though a lead is mostly a target painted on one's back.",
    "The last cycle was one of quiet ambition. \"{detail}\" went to {A}, and {lead} stands first with {vp} points.",
    "Progress rarely looks dramatic until you check the tally. After {A} claimed \"{detail}\", {lead} holds the front with {vp} points.",
    "Every rival glanced nervously at the scoreboard as {A} completed \"{detail}\". {lead} now paces the field on {vp} points.",
    "The clerks updated the imperial roll after {A} secured \"{detail}\". With {vp} points, {lead} sits closest to the crown.",
    "Ambition paid dividends last cycle: \"{detail}\" fell to {A}, while {lead} kept the summit at {vp} points.",
    "As {A} checked off \"{detail}\", the race tightened across the Core. {lead} enters the new cycle ahead on {vp} points.",
  ],
  quiet: [
    "The last cycle passed in near silence. I have rarely had so little to write, and never trusted such a silence less.",
    "Nothing of note happened last cycle, which is the most worrying entry a scribe can put in a ledger.",
    "The fleets stayed in dock and the guns stayed cold last cycle. When empires go this quiet, they are sharpening knives.",
    "A peaceful cycle on paper, though every archivist knows peace in this galaxy is merely logistics between battles.",
  ],
};

/** Wiersz o stanie punktów na koniec rozdziału. */
export const STANDINGS_LEAD: Pool = [
  "At the close of the cycle, {A} stood highest in the race for the throne with {n} points.",
  "When the cycle ended, {A} led the race with {n} points, and every rival took note.",
  "The ledgers closed with {A} ahead on {n} points.",
  "By nightfall, {A} held the front of the pack with {n} points, drawing quiet glances from across the chamber.",
  "The Speaker tallied the marks and placed {A} first at {n} points.",
  "With {n} points recorded, {A} ended the cycle closest to the crown.",
  "The Scriptorium sealed the chapter with {A} in command of the tally at {n} points.",
  "Every envoy left the rotunda calculating how to stop {A}, now standing at {n} points.",
  "The cycle's final reckoning favored {A}, who held the lead on {n} points.",
  "At {n} points, {A} finished the cycle setting the pace for the entire galaxy.",
  "Clerks pinned {A}'s seal at the top of the board with {n} points as the bells rang.",
];

export const STANDINGS_TIE: Pool = [
  "At the close of the cycle, the race was tied at {n} points. Nobody dared call the throne.",
  "The cycle ended in a dead heat at {n} points.",
  "No single power pulled clear; the leaders finished level on {n} points.",
  "The ledgers closed with the frontrunners locked together at {n} points.",
  "Equal on {n} points at the cycle's end, the leaders watched each other with polite, hollow smiles.",
  "The tally offered no clear favorite, leaving the foremost rivals deadlocked at {n} points.",
  "As the chapter closed, the top seats shared {n} points and twice as much suspicion.",
];

export const POOLS: Record<Exclude<ChronicleKind, "battle">, Pool> = {
  prologue: [
    "{n} powers answered the call of the empty throne. This is the chronicle of what they did.",
    "The Lazax are gone. {n} empires remain, and every one of them intends to be remembered.",
    "{n} banners gathered along the edges of the star-charts, each convinced that Mecatol Rex awaits their hand.",
    "From {n} distant capitals, fleets broke orbit toward the Core. The Scriptorium opens its pages.",
    "When the great seal cracked, {n} contenders stepped forward to claim the ashes of the First Empire.",
  ],
conquest: [
    "{Ae} took {planet} from {B}. The banners above {planet} changed in a single day.",
    "{planet} fell to {Ae}. {B} watched it go and did not forgive.",
    "The garrisons of {B} on {planet} were broken, and {A} raised a new flag over the ruins.",
    "{A} marched onto {planet} and left {B} with nothing but the memory of owning it.",
    "By the end of the day, {planet} belonged to {Ae}. {B} would remember the date.",
    "{B}'s governors surrendered {planet} before dusk, handing the spaceports to {Ae}.",
    "The borders shifted at {planet}, where {A} pried the world straight out of {B}'s grip.",
    "{A} secured {planet} over {B}'s protests, turning a rival stronghold into a fresh outpost.",
    "Local beacons on {planet} switched from {B}'s codes to {A}'s before the dust even settled.",
    "{B} lost its foothold on {planet} as {Ae} locked down every landing pad.",
    "The mapmakers crossed out {B}'s seal over {planet} and inked in {A}.",
    "After a sharp exchange, {planet} passed from {B} to {Ae} without a treaty in sight.",
    "{A} stripped {planet} from {B}'s ledger and folded its resources into their own.",
    "Supply lines for {B} snapped at {planet} the hour {A}'s troops claimed the capital.",
    "What {B} built on {planet} now answers to {Ae}.",
    "{planet} traded one master for another as {A} drove {B} off the surface.",
  ],
  homeworld: [
    "{Ae} stood on {planet}, the cradle of {B}, and the sky was full of strangers.",
    "{planet} was the heart of {B}. Now {A} holds it, and the heart beats for someone else.",
    "Few thought it possible, yet {planet}, ancestral seat of {B}, fell into the hands of {Ae}.",
    "The founding monuments of {B} on {planet} now stand in the shadow of {A}'s transports.",
    "{A} breached the inner defenses of {planet}, stripping {B} of its home and its pride.",
    "When {Ae} occupied {planet}, the archives recorded a wound that {B} will carry to the end of the war.",
  ],
settle: [
    "{Ae} claimed {planet} and put down roots.",
    "No fleet defended {planet}. {A} simply arrived, and it was theirs.",
    "{A} planted a claim on {planet}, and their realm grew by one world.",
    "{planet} gained a new master in {Ae}.",
    "Survey beacons belonging to {A} flickered to life across {planet}, bringing another world into the fold.",
    "Unopposed in orbit, {Ae} landed garrisons on {planet} and drafted its first tax charter.",
    "{A} extended its reach to {planet}, turning an empty dot on the map into a frontier holding.",
    "Local beacons above {planet} switched to {A}'s frequencies without a single shot fired.",
    "Drop-shuttles from {A} touched down on {planet}, claiming the world for the empire.",
    "{Ae} staked a banner on {planet} before any rival scout could reach the jump-point.",
    "An empty frontier world no longer: {planet} entered the records under {A}'s seal.",
    "{A} quietly annexed {planet}, folding its docks into their border network.",
    "With no garrison to object, {Ae} brought {planet} under imperial administration.",
    "The star-charts updated at dawn, marking {planet} as newly held by {A}.",
  ],
score: [
    "{Ae} fulfilled \"{obj}\" and was counted among the great.",
    "\"{obj}\" was finished by {A}, and the Speaker had no choice but to mark it.",
    "{A} achieved \"{obj}\", moving one step closer to the throne.",
    "The deed was called \"{obj}\", and it belonged to {Ae}.",
    "Clerks in the Conclave logged \"{obj}\" under {A}'s seal, nudging the race forward.",
    "With \"{obj}\" complete, {Ae} gave the rest of the galaxy fresh cause for alarm.",
    "{A} met every demand of \"{obj}\", earning another notch in the imperial tally.",
    "The chroniclers inked \"{obj}\" beside the name of {Ae}.",
    "Envoys murmured as {A} presented proof of \"{obj}\" before the Council floor.",
    "Another milestone fell to {Ae}: \"{obj}\" was sealed and entered into the Codex.",
    "{A} claimed credit for \"{obj}\", tightening its grip on the imperial race.",
    "No rival could dispute it: \"{obj}\" stood completed under {A}'s banner.",
    "The tally shifted in {A}'s favor the moment \"{obj}\" was verified by the scribes.",
    "Quiet applause and loud glares greeted {Ae} upon completing \"{obj}\".",
    "{A} turned ambition into record, adding \"{obj}\" to its growing ledger.",
    "When the bells sounded for \"{obj}\", it was {A} who stepped forward to collect.",
  ],
law: [
    "The Council passed \"{law}\". The vote was close enough to be remembered.",
    "\"{law}\" became the law of the galaxy, and the voting hall fell quiet for a moment.",
    "The Council enacted \"{law}\". The ink was barely dry before someone began looking for a way around it.",
    "By the will of the Council, \"{law}\" now binds every fleet in the Core and beyond.",
    "The gavel fell on \"{law}\", locking a new set of rules onto an unwilling galaxy.",
    "After a tense tally, \"{law}\" entered the statutes while the losing delegates quietly drafted reprisals.",
    "\"{law}\" carried the chamber, proving once again that a well-placed bribe outguns a cruiser.",
    "With \"{law}\" ratified, imperial clerks spent the night rewriting half the sector charters.",
    "The Conclave stamped its seal upon \"{law}\", leaving half the delegates cheering and the rest reaching for their comms.",
    "\"{law}\" passed into imperial precedent, enforced by custom and the threat of a blockade.",
    "A narrow majority pushed \"{law}\" through the chamber before the opposition could rally.",
    "The scribes inscribed \"{law}\" in the great book, knowing full well how soon someone would break it.",
  ],
 agenda: [
    "The Council convened to hear \"{law}\".",
    "\"{law}\" was brought before the Council, and every delegate began to count their votes.",
    "A new matter was laid before the Conclave: \"{law}\".",
    "The Speaker unsealed \"{law}\", sending aides scrambling across the rotunda floor.",
    "Debate opened on \"{law}\", accompanied by the usual chorus of polite threats.",
    "Clerks distributed copies of \"{law}\" to every seat, and the quiet bargaining began.",
    "The chamber doors sealed as \"{law}\" was read into the record.",
    "Whispers rippled through the gallery the instant \"{law}\" appeared on the docket.",
    "Delegates leaned forward over their voting plinths to weigh \"{law}\".",
    "The Conclave paused its wars long enough to argue over \"{law}\".",
    "\"{law}\" took the floor, and old alliances were immediately tested against its text.",
    "Every faction weighed the cost of \"{law}\" while the Speaker called for order.",
    "Aides raced between booths with encrypted notes as \"{law}\" came up for a vote.",
    "The rotunda grew loud as the Speaker placed \"{law}\" before the assembled powers.",
  ],
tech: [
    "{Ae} mastered {tech}. Rival laboratories fell quiet with envy.",
    "{A} finished work on {tech} and moved it straight from blueprint to fleet.",
    "In the laboratories of {A}, {tech} stopped being a theory.",
    "Field trials succeeded for {A}, putting {tech} into active service across their sector.",
    "Engineers serving {Ae} cracked the final barrier on {tech}.",
    "Spies across the galaxy scrambled to copy {tech} the moment {A} unveiled it.",
    "{A} unlocked {tech}, quietly rendering a dozen rival manuals obsolete.",
    "Drydocks across {A}'s territory began retrofitting hulls with {tech} before dawn.",
    "The archives logged a fresh advance for {Ae}: {tech}.",
    "What began as an expensive rumor in {A}'s academies became working hardware under the name {tech}.",
    "{A} brought {tech} online, and neighboring commanders immediately requested updated threat assessments.",
    "Research teams under {A}'s banner delivered {tech} ahead of schedule.",
    "The gap in galactic science shifted slightly as {Ae} perfected {tech}.",
    "{A} finalized {tech}, adding a sharp new tool to its arsenal.",
    "Quiet celebrations broke out in {A}'s research spires upon the completion of {tech}.",
    "Encrypted schematics for {tech} began circulating through {A}'s command channels.",
  ],
  relic: [
    "{Ae} claimed the relic {relic}, a thing older than the Lazax themselves.",
    "{relic} passed into the hands of {A}. The ancients had left it for someone, and now someone had come.",
    "From the dust of a forgotten world, {A} lifted {relic}.",
    "Ancient seals gave way before {Ae}, yielding {relic} to a new era.",
    "Word spread quickly across the net: {A} now holds {relic}.",
    "Archivists on Mecatol Rex grew pale upon hearing that {relic} had fallen to {Ae}.",
  ],
leader: [
    "{leader} answered the call of {Ae}.",
    "{A} brought {leader} into active command, giving their realm a sharper edge.",
    "The service of {leader} to {Ae} was sworn that day.",
    "Fleet channels crackled as {leader} assumed their post under {A}'s banner.",
    "{A} unlocked the full authority of {leader}, and neighboring borders tightened in response.",
    "With {leader} stepping onto the bridge, {Ae} gained a voice that rivals could ill afford to ignore.",
    "Orders signed by {leader} began flowing out of {A}'s headquarters.",
    "Intelligence dossiers across the Core were hastily updated when {leader} took the field for {A}.",
  ],
hero: [
    "{leader} of {Ae} entered legend. What followed was terrible to behold.",
    "{A} called upon {leader}, and the course of the war bent around them.",
    "The great champion {leader} acted for {Ae}, leaving a mark the galaxy will not soon erase.",
    "In a single decisive stroke, {leader} reshaped the sector for {A}.",
    "Songs and nightmares alike will remember the hour {leader} moved at {A}'s command.",
    "The Scriptorium set aside a full page for {leader}, whose gambit for {Ae} stunned the Conclave.",
    "When {leader} intervened for {A}, even veteran admirals fell silent at their holomaps.",
    "The hour belonged to {leader}, whose decisive act for {Ae} echoed across every sector.",
  ],
  throne: [
    "The Custodians left Mecatol Rex. {Ae} lifted the seal of the Lazax and opened the throne room to the galaxy.",
    "{A} broke the old seal on Mecatol Rex. The Custodians stood down, and the race began in earnest.",
    "On Mecatol Rex, the Custodians gave way to {Ae}, placing the throne within reach of every contender.",
    "The ancient wardens of Mecatol City yielded their keys to {A}, ending centuries of quiet stewardship.",
    "When {Ae} stepped across the threshold of the Imperial Palace, every rival fleet turned toward the Core.",
  ],
  fall: [
    "{A} was lost. Their banners vanished from the charts, and the stars closed over their name.",
    "The realm of {A} fell silent, having run out of ships, worlds, and time.",
    "With their last world taken, {Ae} faded from the race for the throne.",
    "The seat of {A} stood empty in the Conclave; nothing remained of their empire save footnotes and wreckage.",
    "History closed the book on {Ae}, leaving their former sectors to the vultures.",
  ],
  fracture: [
    "{Ae} tore open the Fracture. What lay beyond had been waiting for a very long time.",
    "{A} breached the Fracture, and long-range sensors across the galaxy screamed in unison.",
    "Space split like cracked glass at {A}'s touch, exposing the dark corridors of the Fracture.",
    "Ignoring every warning from the Scriptorium, {Ae} stepped straight into the Fracture.",
    "A bruised tear widened along the rim as {A} forced the Fracture open.",
  ],
  supernova: [
    "{A} detonated the Nova Seed. {system} was a living sector, and now it is a burning lesson.",
    "A new sun was born where {system} had been, and {Ae} offered no apology.",
    "Blinding fire swallowed {system} at {A}'s command, erasing every chart of the region in a heartbeat.",
    "Where {system} once turned, only an incandescent maelstrom remains, stamped with the wrath of {Ae}.",
    "{A} cracked the heavens over {system}, leaving behind a star that no conventional hull can cross.",
  ],
deal: [
    "{A} and {B} came to an agreement, the kind spoken quietly and remembered for a long time.",
    "{Ae} and {B} sat down together and rose with a deal. Neither said what it cost.",
    "{A} traded with {B}. In this galaxy, that is sometimes more dangerous than war.",
    "Envoys from {A} and {B} exchanged sealed manifests away from the Council's ears.",
    "A handshake between {A} and {B} shifted resources across the border before anyone else could bid.",
    "{A} and {B} found common profit for a cycle, though both kept a hand near their sidearms.",
    "Coin and favors passed quietly between {A} and {B} under the table.",
    "Cargo shuttles moved smoothly between {A} and {B} under a newly inked understanding.",
    "{A} and {B} struck a quiet bargain that left their neighbors wondering who got cheated.",
    "Terms were settled between {A} and {B} in a back corridor of the rotunda.",
    "For one brief moment, {A} and {B} preferred profit to plasma.",
    "The ledgers recorded a private transfer between {A} and {B}, with no further explanation offered.",
    "{A} and {B} signed a quick compact, each convinced they had gotten the better end.",
    "Diplomats for {A} and {B} left the booth smiling, which made everyone else nervous.",
    "A discreet exchange of goods and promises linked {A} and {B} for the cycle.",
    "Whatever {A} and {B} traded behind closed doors moved fleets before sunset.",
  ],
strategy: [
    "{Ae} played {card}.",
    "{A} turned the rhythm of the cycle with {card}.",
    "{card} was {A}'s chosen instrument.",
    "The tempo shifted as {Ae} activated {card}, forcing every neighbor to react.",
    "{A} committed to {card}, setting the pace for the rest of the round.",
    "Across the holomaps, admirals paused to answer {A}'s use of {card}.",
    "With crisp timing, {Ae} put {card} into motion.",
    "Dispatches flared across the sector as {A} invoked {card}.",
    "Every rival checked their reserves the instant {A} triggered {card}.",
    "{A} seized the initiative of the hour by playing {card}.",
    "The Conclave's attention snapped toward {Ae} upon the activation of {card}.",
    "{A} played {card} cleanly, leaving the rest of the table scrambling to follow.",
    "Command channels lit up across the galaxy as {A} called {card}.",
    "Choosing the moment carefully, {Ae} brought {card} to bear.",
    "{card} rang out across the cycle under {A}'s seal.",
    "Fleets and treasuries alike shifted when {A} enacted {card}.",
  ],
explore: [
    "{Ae} explored {planet} and found something missing from the imperial charts.",
    "{A} sent surveyors to {planet}; they returned carrying {card}.",
    "Beneath the dust of {planet}, scouts for {A} uncovered {card}.",
    "{A}'s expedition on {planet} paid off handsomely, logging {card} into their manifests.",
    "Frontier teams from {Ae} combed the ruins of {planet} and emerged with {card}.",
    "What {A} pulled from the frontier of {planet} was entered in the ledger as {card}.",
    "Deep scans of {planet} rewarded {A} with {card}.",
    "A salvage crew working for {A} broke open an old vault on {planet} and found {card}.",
    "{planet} surrendered a forgotten secret to {Ae}: {card}.",
    "Survey drones dispatched by {A} mapped the wilds of {planet} and flagged {card}.",
    "Between the storms and rubble of {planet}, {A}'s scouts secured {card}.",
    "The frontier paid its tribute to {A} on {planet} in the form of {card}.",
    "Field notes from {planet} credited {Ae} with recovering {card}.",
    "Scouts for {A} dug deeper than anyone before them on {planet} and came back with {card}.",
  ],
speaker: [
    "{Ae} took the gavel and became Speaker.",
    "The right to speak first passed to {A}.",
    "{A} assumed the Speaker's podium, claiming control over the Council's docket.",
    "The golden baton moved to {Ae}, and every envoy suddenly grew more polite.",
    "Order of business now bends to {A}, newly seated as Speaker of the Conclave.",
    "With {Ae} holding the gavel, the next round of politics will march to their beat.",
    "The Speaker's chair changed hands, settling firmly under {A}'s banner.",
    "{A} claimed the high lectern on Mecatol Rex, dictating who speaks and who waits.",
    "Clerks bowed to a new Speaker as {Ae} took command of the floor.",
    "The gavel rested before {A}, granting them the prized first word of the coming cycle.",
  ],
  victory: [
    "{Ae} took the throne of the Lazax. The chronicle can end here, though the history of the galaxy does not.",
    "{A} sat on the throne of Mecatol Rex. Every rival that had opposed them knelt, or remembered how to.",
    "The race was over. {A} stood crowned as Emperor, giving the galaxy a new name for the old order.",
    "The banners of {Ae} rose above the Imperial Palace, closing this volume of the Codex of the Lazax.",
    "One power outlasted them all: {Ae} claimed Mecatol Rex, and the scribes sealed the final page.",
  ],
};

/** Uchylenie prawa przez Radę. */
export const REPEAL: Pool = [
  "The Council repealed \"{law}\". What was law yesterday is now only a story.",
  "\"{law}\" was struck from the books by a vote of the Council.",
  "With a single motion, the Conclave erased \"{law}\" from the imperial code.",
  "Clerks quietly shredded \"{law}\" after the Council voted to bury its own precedent.",
  "\"{law}\" lasted until it became inconvenient, at which point the Council repealed it.",
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
  tech: "Technology",
  relic: "Relic Found",
  leader: "A Leader Rises",
  hero: "A Hero Acts",
  throne: "The Throne Opens",
  fall: "A Power Falls",
  fracture: "The Fracture",
  supernova: "Nova Seed",
  deal: "A Deal Struck",
  strategy: "Strategy",
  explore: "Exploration",
  speaker: "Speaker",
  victory: "The Throne Is Taken",
};