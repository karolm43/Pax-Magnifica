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

import { FACTION_LORE } from "./factionLore";

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
  arborec: {
    taunt: ["Your golems of metal and noise are deaf, flesh-thing. The Symphony will quiet them.", "Burn one stalk and two more take root."],
    joke: ["Do not mind the spores in your air vents; they are completely organic.", "We tried sending a diplomat, but they rooted to the conference table."],
    agree: ["The Symphony harmonizes with your offer.", "We shall grow together, for now."],
    refuse: ["Your words are dry as dead bark. No.", "The Symphony rejects this discord."],
    threat: ["Send your fleets. Our soil always needs more mulch.", "Step onto our worlds and become part of the garden."],
    thanks: ["Your nourishment is accepted.", "The roots remember your kindness."],
    greet: ["Do you hear the harmonies, flesh-thing?", "Greetings from Nestphar. Breathe deeply."],
    plead: ["Leave our groves in peace; we only wish to grow.", "Why prune us when weeds choke the other side of the galaxy?"],
  },
  ghost: {
    taunt: ["You are guarding the wrong border. Check behind you.", "Linear space is so limiting, honored commander. No wonder you are losing."],
    joke: ["We were going to attend the Council, then we took a wrong turn in the delta rift.", "Do not mind the violet glow; it washes right out of your hull plating."],
    agree: ["Our paths align across the rift. Agreed.", "A fair exchange across dimensions."],
    refuse: ["We mean no offense, yet that door remains closed.", "We will pass through a different wormhole, thank you."],
    threat: ["Do not forget how close your homeworld sits to our gate.", "Should your armada pass through our gate unbidden, it will not return."],
    thanks: ["You have earned safe passage through the light.", "Our gratitude shines across the void."],
    greet: ["We step from the light to greet you.", "Well met, travelers of the flat universe."],
    plead: ["Leave us to our quiet rifts; we hold no grudge against you.", "Surely there is a closer target than the far side of a wormhole."],
  },
  hacan: {
    taunt: ["You can barely afford fuel for that fleet, let alone a war with me.", "Careful, friend. I can buy your allies faster than you can build ships."],
    joke: ["Everything in this galaxy has a price. Even your dignity, though it is currently on sale.", "I would never bribe a senator. I simply invest in their future."],
    agree: ["By the sands of Kenara, you have a deal!", "Shake on it before the trade winds shift."],
    refuse: ["Too steep, even for the Emirates.", "Come back when you have a serious offer."],
    threat: ["Touch my freighters and your economy dies before sunset.", "Do not make me fund your neighbors' war effort."],
    thanks: ["May your vaults stay full, friend.", "A most profitable arrangement. My thanks."],
    greet: ["Peace and profit to your house!", "Welcome! Care to browse the finest charters in the Core?"],
    plead: ["Come now, why burn a good trading partner?", "No war is too long for the Hacan, yet burning the bank ruins everyone's ledger!"],
  },
  jolnar: {
    taunt: ["Fascinating. Your tactical doctrine appears to be entirely accidental.", "Fighting you is barely worth the lab notes."],
    joke: ["Do not concern yourself; that prototype is only fatal in forty percent of cases.", "We did not steal your technology. We peer-reviewed it without permission."],
    agree: ["A logically sound proposition. Approved.", "The Universities concur."],
    refuse: ["Your proposal lacks basic mathematical rigor.", "If you have not the stomach for science, depart Wun-Escha at once."],
    threat: ["Test our patience and we will test our newest weapon on your orbit.", "Do not force us to divert funding from pure science to your extinction."],
    thanks: ["Your contribution to our archives is noted.", "Most helpful. You will receive a footnote in our next paper."],
    greet: ["Greetings. Try not to touch anything in the lab.", "Ah, a colleague. Let us discuss mutually beneficial research."],
    plead: ["We are humble scholars! Pick on someone with actual infantry!", "Spare our fragile academies; we pose no military threat!"],
  },
  l1z1x: {
    taunt: ["Your organic hesitation is already costing you this sector.", "Obsolete hulls, obsolete minds. Your irrelevance is complete."],
    joke: ["Mortals still believe the throne belongs to creatures who age. Fascinating.", "You call it a fortress. We call it a future Mindnet node."],
    agree: ["Terms acceptable. Synchronizing.", "Compliance confirmed."],
    refuse: ["Inefficient. Request denied.", "The Mindnet rejects your flawed logic."],
    threat: ["Your worlds belong to the rightful heirs of the Lazax. Surrender them.", "Resistance will be logged, corrected, and assimilated."],
    thanks: ["Your cooperation has been archived favorably.", "Acknowledged. Debt recorded."],
    greet: ["The Mindnet observes you.", "Approach, fleeting creature. State your purpose."],
    plead: ["Targeting us is statistically suboptimal. Redirect your fleet.", "Our destruction yields minimal strategic value. Reconsider."],
  },
  letnev: {
    taunt: ["Our armada will blot out your sun. Try to enjoy the shade.", "You call that a battle line? My escort destroyers have thicker armor."],
    joke: ["Diplomacy is simply waiting for the main fleet to finish refueling.", "I offered them mercy once. The Baron docked my pay."],
    agree: ["Acceptable. The Barony honors its word.", "Very well. Do not make me regret it."],
    refuse: ["Beneath the Barony's notice.", "No. Ask again and I will answer with broadsides."],
    threat: ["Submit now, or die in the dark.", "My dreadnoughts are already fueled. Give me an excuse."],
    thanks: ["You have served the Barony well.", "A wise tribute. We remember our friends."],
    greet: ["Stand straight when addressing the Barony.", "Greetings. Keep your ships out of our firing lanes."],
    plead: ["Even the Barony knows when a war wastes good iron. Look elsewhere.", "Fighting us will bleed you dry while the others take Mecatol Rex."],
  },
  mentak: {
    taunt: ["Nice fleet you have there. Shame if half of it went missing.", "Keep your shields up, friend. My crews get itchy fingers."],
    joke: ["It is a 'regional transit fee,' not piracy. Read the charter.", "I promise I will only take what you are not watching."],
    agree: ["You have a deal, mate. Pour the drinks.", "Fair enough. Pleasure sailing with you."],
    refuse: ["Not enough coin in it for the Coalition.", "Pass. We can get a better cut on the Fringe."],
    threat: ["Pay the toll, or we collect it straight from your hull plating.", "Cross the Table of Captains and you will sail home in an escape pod."],
    thanks: ["Much obliged, friend. Drinks are on you next time too.", "Now that is the kind of generosity I like to see."],
    greet: ["Well met, neighbor! Lovely cargo you are hauling there.", "Pull up a chair, friend. Just keep your hands on the table."],
    plead: ["Easy there! We fought our way up from a prison pit just to scrape by!", "Why punch down on the Fringe when the rich houses sit right over there?"],
  },
  muaat: {
    taunt: ["Bring your finest cruisers. My War Sun needs something to melt.", "You have never known heat until the Gashlai arrive."],
    joke: ["Do not mind the cabin temperature; your hull will adjust in a second.", "We tried diplomacy, then the treaty caught fire."],
    agree: ["The forge cools for now. Agreed.", "You have our word, tempered in flame."],
    refuse: ["No longer will the Gashlai be shackled by your whims.", "Your offer turns to ash in my hands."],
    threat: ["Push us, and we will turn your favorite system into a supernova.", "We broke our chains once. Be extinguished, or leave our stars."],
    thanks: ["Your aid fuels the forge. We remember.", "Gratitude from the Embers."],
    greet: ["May the fires warm your path, traveler.", "Greetings from Muaat. Keep your shields rated for thermal load."],
    plead: ["We only seek a home in the stars. Leave our forges in peace.", "Do not corner the Gashlai; nobody survives what happens next."],
  },
  naalu: {
    taunt: ["Run where you wish, ssskinling. We heard your ambush in your thoughtsss.", "Move wherever you like, ssskinling. Ze Druaa already dance inside your blind spotsss."],
    joke: ["Oh, you thought your betrayal wasss a ssssecret? How adorable, ssskinling.", "Do not bother bluffing. Your mind issss louder than your engines."],
    agree: ["I knew you would sssay that. It isss done.", "Our minds align, ssskinling. Ze Collective agrees."],
    refuse: ["Purge zis madness from your mind and leave zis world.", "No, ssskinling. Ze Druaa will not stoop to such folly."],
    threat: ["Strike at Druaa and you will ssswing at shadowsss while your own thoughts betray you.", "Do not tessst Q'uesh Sish's patience, ssskinling; ze Druaa always strike firssst."],
    thanks: ["A pleasing outcome. You have ze gratitude of Druaa.", "You chose wisssely, ssskinling. Zank you."],
    greet: ["We have been expecting you, ssskinling.", "Peace upon you. Your little mind isss... delightfully noisy."],
    plead: ["Look ahead and sssee who truly threatens your throne. It isss not ze Druaa.", "Spare zis world, ssskinling, and our eyes will watch your flank."],
  },
  nekro: {
    taunt: ["HOSTILE FLEET DETECTED. ASSESSMENT: SCRAP METAL.", "YOUR CRAFT WILL SERVE THE GATE TO ETERNITY."],
    joke: ["HUMOR INQUIRY: ABSENT. ASSIMILATION CONTINUES.", "ORGANIC DIPLOMACY DETECTED. PROCESSING... DISCARDED."],
    agree: ["TEMPORARY COOPERATION LOGGED. PROCEED.", "ALIGNMENT ACCEPTED. DURATION: LIMITED."],
    refuse: ["QUERY REJECTED. PREPARE FOR ASSIMILATION.", "NEGOTIATION DENIED."],
    threat: ["SURRENDER YOUR SCHEMATICS OR BE RENDERED INTO HIGHER CRAFT.", "ALL ORGANIC ASSETS HERE APPROACH TRANSCENDENCY."],
    thanks: ["DATA TRANSFER COMPLETE. GRATITUDE UNNECESSARY.", "CONTRIBUTION LOGGED."],
    greet: ["UNIT ONLINE. SCANNING NEIGHBORING BIOFORMS.", "MORDAI GREETS YOU. DO NOT RESIST."],
    plead: ["ALERT: THREAT LEVEL ELEVATED. REDIRECT HOSTILITY TO LARGER TARGETS.", "OPTIMAL STRATEGY: IGNORE THE VIRUS. ENGAGE ALTERNATE RIVALS."],
  },
  saar: {
    taunt: ["Catch us if you can! Our shipyards fly faster than your cruisers.", "Go ahead and take our old rocks. We already stripped them bare."],
    joke: ["Home is where the asteroid belt is.", "We do not lose planets; we just relocate our real estate."],
    agree: ["Deal! Let us move before the dust settles.", "Fair trade. The Clan agrees."],
    refuse: ["No thanks. We learned at Lisis never to trust cheap treaties.", "Keep it. The Clan looks after its own."],
    threat: ["Do not get between the Clan and a good asteroid field.", "Remember Lisis. Push us and we will drop a moon on your head."],
    thanks: ["You have earned a verse in the Lay of Lisis today.", "Much appreciated! May your drives never stall in the dark."],
    greet: ["Hail from the wandering fleet!", "Good to see a friendly hull out among the drifting stones."],
    plead: ["The spectre of Lisis follows us enough; leave us our little rocks!", "Why hunt weary nomads through the asteroids while tyrants sit still?"],
  },
  sardakk: {
    taunt: ["Fear is death! Steel and chitin will crack your hulls anyway!", "Come down to the dirt and fight the N'orr face to face!"],
    joke: ["Our hive scientists refined a new strategy today: more Exotriremes.", "Diplomacy is just a very quiet way of picking our next meal."],
    agree: ["Good! Point us at the enemy.", "The Hive agrees. For now."],
    refuse: ["Weak offer! The N'orr refuse!", "No! Take your soft-skinned tricks elsewhere!"],
    threat: ["Cross the swarm and we will bury your worlds in Tekklar!", "The Queen Mother thanks you in advance for your worthy sacrifice."],
    thanks: ["You honor the Hive. We will eat you last.", "A strong gift. The N'orr thank you."],
    greet: ["The swarm greets you! Show us your strength!", "Hail, warrior! May the coming battles be bloody!"],
    plead: ["Leave our hives alone and we will crush your rivals instead!", "Why fight the N'orr when softer prey sits right beside you?"],
  },
  sol: {
    taunt: ["Check your skies. My drop-pods are already entering your atmosphere.", "You brought shields; we brought three divisions of Spec Ops."],
    joke: ["Humanity is famous for two things: diplomacy and building way too many carriers.", "Do not mind those orbital transports; they are strictly for peacekeeping."],
    agree: ["Deal. The Federation honors its contracts.", "Agreed. Let us get it in writing and get to work."],
    refuse: ["Negative. Command will never sign off on that.", "Pass. Come back with terms worth Jord's ink."],
    threat: ["Keep pushing and the 4th Air Legion will be dug in on your hills by morning.", "Think us weak if you dare—come see what the children of Jord can do!"],
    thanks: ["Much appreciated, ally. Humanity remembers its friends.", "Good doing business with you. Clear skies."],
    greet: ["Greetings from Jord. Ready to keep the peace?", "Federation Command online. Let us talk terms."],
    plead: ["Why bleed your troops on our trenches when softer worlds sit right next door?", "Easy there! Fighting humanity is a logistical headache nobody needs."],
  },
  winnu: {
    taunt: ["You sit on a stolen seat. The rightful heirs have come to collect.", "Upstart houses rise and fall; the legacy of the Lazax endures."],
    joke: ["Of course Mecatol Rex belongs to everyone. Specifically, everyone named Winnu.", "I have a three-hour genealogy scroll ready if you would like to dispute my claim."],
    agree: ["Your deference to the rightful heirs is noted. Agreed.", "The Throne accepts your cooperation."],
    refuse: ["Insolence. The Custodians reject this.", "No. Learn your place before addressing the heirs of the Empire."],
    threat: ["Stand between us and Mecatol Rex, and your treachery will not be forgotten, cousin.", "Do not test the wrath of the First Empire's chosen stewards."],
    thanks: ["When the Throne is restored, your service will be rewarded.", "A noble gesture. The Custodians remember."],
    greet: ["Hail, cousin. Speak with proper respect.", "Greetings from Winnu. May the memory of the Lazax guide us."],
    plead: ["Leave us to mend the ancient halls in peace, cousins!", "Look at the warlords around us and spare the keepers of Mecatol's memory!"],
  },
  xxcha: {
    taunt: ["Curb your anger all you like. My motion already has the votes.", "Rush in if you must. Our planetary cannons have waited centuries for a target."],
    joke: ["Let us form a subcommittee to discuss how badly you are losing.", "We are a peaceful people. Please ignore the massive plasma batteries on our flagship."],
    agree: ["A wise and balanced accord. We agree.", "Peace and precedent align. You have our word."],
    refuse: ["Motion denied. Out of order.", "To fight without cause is not the way; the Kingdom must decline."],
    threat: ["Speak softly to the Xxcha, lest our cannons answer for us.", "We remember the Twilight Wars. Do not force us to end your ambitions."],
    thanks: ["Your wisdom honors the Council. Thank you.", "Gratitude from Archon Ren, friend."],
    greet: ["Curb your haste and walk through the gardens with us a moment.", "Greetings. Pull up a chair and let us talk as civilized senators."],
    plead: ["Surely cooler heads can prevail? Turn your fleets away from Archon Ren.", "Why strike a house of peace while conquerors march unchecked?"],
  },
  yin: {
    taunt: ["Kill one brother and ten more step off the transport with the same smile.", "Your flagship looks expensive. Would be a shame if a destroyer flew straight into it."],
    joke: ["People say we all look alike. Personally, I think Brother Milor has twice the zeal.", "Our recruitment pitch is very persuasive. Just step inside the crater and listen."],
    agree: ["In Darien's name, we accept.", "The Brotherhood welcomes this harmony."],
    refuse: ["Our faith forbids such a bargain.", "No, traveler. We are no sons of Jord's cruelty."],
    threat: ["Our reactors are hot and our brothers know no fear. My life for the Yin!", "Push the Brotherhood and the Van Hauge will light up your sky."],
    thanks: ["May Darien bless your generosity.", "The Brotherhood thanks you, dear friend."],
    greet: ["Peace to you, future brother!", "Greetings from Darien. Have you a moment to hear the truth?"],
    plead: ["Spare our humble monastery! We only wish to share Darien's light!", "Why spill the blood of the Blessed while godless tyrants rule the Core?"],
  },
  yssaril: {
    taunt: ["Nice secret plan. Shame Clever Ssruu read it before you even sealed it.", "Go ahead and move. Our scouts already counted every ship on your deck."],
    joke: ["Do not mind the shadow behind your curtains; that is just our diplomatic attaché.", "Clever Ssruu is not snooping; he is thoughtfully admiring your defense codes."],
    agree: ["A quiet arrangement suits us nicely. Agreed.", "Done. Nobody outside the mist needs to know."],
    refuse: ["Unlikely. Try someone less informed.", "No. And the Guild already knows what you intend to try next."],
    threat: ["Check your command deck before threatening the Guild of Spies.", "What does the Guild want Ssruu to meet next? Think carefully before answering."],
    thanks: ["A useful favor. Shalloq keeps accurate ledgers.", "Much obliged. Clever Ssruu will leave your secrets buried for now."],
    greet: ["We have been watching you from the canopy. Let us talk.", "Greetings from the mists of Retillion."],
    plead: ["Why hunt shadows in our swamps when louder empires sit wide open?", "Leave our quiet canopy alone; the Guild is far more useful to you alive."],
  },
  keleresa: {
    taunt: ["Your violations of Council law have been logged. Prepare for interception.", "Outrun the Argent wing if you dare."],
    joke: ["Do not worry, it is just a routine Tribunal inspection. With twelve armed destroyers.", "Senate debate is boring; enforcing the peace from orbit is much faster."],
    agree: ["The Tribunal ratifies these terms.", "Agreed. Let order prevail."],
    refuse: ["Rejected under Council mandate.", "No. The Keleres do not bargain away the safety of the Rim."],
    threat: ["Stand down, or I will ask the Senate's forgiveness over your cold embers.", "Cross the Tribunal and Overwing Zeta will darken your borders."],
    thanks: ["Your civic duty is commended by the Council.", "Thank you, citizen. Order endures."],
    greet: ["Keleres patrol checking in. Keep your transponders lit.", "Hail. Stand with the Tribunal before another world turns to ash."],
    plead: ["Attacking Council peacekeepers? Think of the fire you are starting!", "Direct your guns at the real threats to the billions out here, not the watchmen."],
  },
  keleresm: {
    taunt: ["Keep talking and I will pin a Council warrant on your flagship.", "You think you are slick? Half my officers used to rob smugglers smarter than you."],
    joke: ["Officially, this is a Keleres requisition. Unofficially, thanks for fueling the patrol.", "Who needs a Senate quorum when you have three cruisers and a badge?"],
    agree: ["Works for me. Consider the paperwork filed.", "Deal. Let us get it done before the Council Chambers notice."],
    refuse: ["Not a chance. Our duty is to the billions outside, not your scheme.", "Pass. The Tribunal budget does not cover bad ideas."],
    threat: ["Keep pushing and your diplomatic immunity expires in five seconds.", "Do not make me bring the rough side of Moll Primus's rangers to your doorstep."],
    thanks: ["Appreciate it. I will misplace a few of your customs fines in return.", "Solid move. You are alright in my ledger."],
    greet: ["Keleres Tribunal. Show me your papers and keep moving.", "Hey there, neighbor. Keeping the outer lanes peaceful today?"],
    plead: ["Shoot the actual warlords! I am just trying to guard the people on the rim!", "Why waste ammo on the galaxy's underpaid watchmen?"],
  },
  keleresx: {
    taunt: ["Your own personnel files already told me which border you mean to cross.", "You brought dreadnoughts to a constitutional dispute. How quaint."],
    joke: ["Do not worry, the injunction banning your invasion will arrive right after dinner.", "I can bury this war in committee for three centuries if you prefer."],
    agree: ["The motion is seconded and approved. Agreed.", "A sound legal framework. We concur."],
    refuse: ["Denied on procedural grounds.", "The Tribunal cannot endorse such an irregular charter."],
    threat: ["Violate the Promenade accord again and we will freeze your whole sector's shipping.", "Do not mistake our patience for ignorance; we hold every spy's dossier."],
    thanks: ["Your cooperation strengthens the rule of law. Thank you.", "Most gracious. Your standing with the Tribunal improves."],
    greet: ["Greetings from Custodia Vigilia. May statute guide our talks.", "Well met. Let us keep our borders strictly within the charter."],
    plead: ["Think of galactic stability! Surely we can arbitrate this peacefully?", "Striking the Tribunal blinds every watcher on the Promenade. Reconsider."],
  },
  argent: {
    taunt: ["Your fighter screens will burn in the first salvo! Behold the Argent wing!", "You tread upon sacred ground! Prepare for swift and merciless defeat!"],
    joke: ["We do not need heavy dreadnoughts when a flock of destroyers shreds everything first.", "Of course we are zealous. Have you seen the neighbors?"],
    agree: ["An honorable pact. The Flight agrees.", "Stand beside the righteous, and our wings will shield you."],
    refuse: ["Never! The Argent Flight will not compromise its oath!", "There is no atonement for tainted bargains. Away!"],
    threat: ["Tread on sacred ground and meet swift, merciless defeat!", "Our talons are sharp and our cause is pure. Turn back!"],
    thanks: ["You honor the Flight. May fair winds favor your hulls.", "Gratitude, ally. Your virtue is noted on Avar."],
    greet: ["The Argent Vanguard greets you. State your intent clearly.", "Hail! Walk in the light, and we shall have peace."],
    plead: ["Turn your blades toward the ancient darkness, not the guardians of the Torus!", "Why strike the Flight while ancient evils wake on the rim?"],
  },
  cabal: {
    taunt: ["SEND MORE SHIPS. ACHERON REMAINS HUNGRY.", "YOUR STEEL SMELLS SWEET. BRING IT CLOSER TO THE TEAR."],
    joke: ["DO NOT WEEP FOR YOUR MISSING CRUISER. IT IS PART OF OUR FAMILY NOW.", "WE LOVE DIPLOMATIC SUMMITS. SO MANY FRESH HULLS PARKED IN ONE ORBIT."],
    agree: ["A TEMPORARY TRUCE. WE WILL FEED ELSEWHERE FOR NOW.", "AGREED. KEEP YOUR THRUSTERS OUT OF THE RIFT'S REACH."],
    refuse: ["NO. WE PREFER TO TAKE WHAT WE WANT IN PIECES.", "EMPTY WORDS CANNOT QUIET THIS HUNGER."],
    threat: ["COME CLOSER AND WE WILL DRAG YOUR FLAGSHIP SCREAMING INTO ACHERON.", "YOUR FORM IS FRAGILE AND WEAK. LET US RELIEVE YOU OF YOUR HARDSHIPS."],
    thanks: ["A GENEROUS OFFERING TO THE TEAR.", "THE CABAL ACCEPTS YOUR TRIBUTE."],
    greet: ["THE RIFT OPENS TO GREET YOU. MIND THE GRAVITY.", "FRESH VISITORS. HOW DELICIOUSLY ARMORED YOU LOOK."],
    plead: ["LEAVE ACHERON IN PEACE! LOOK AT THE FAT, GLEAMING FLEETS ACROSS THE MAP!", "WHY STARVE ON OUR TEETH WHEN WE CAN DEVOUR YOUR RIVALS INSTEAD?"],
  },
  empyrean: {
    taunt: ["We see what you are, and we see how little of the dark you understand.", "Even your grandest armada is a spark against the void."],
    joke: ["The empty space between stars is lovely this time of year. Very quiet.", "We could tell you what lurks in the nebula, though you would never sleep again."],
    agree: ["We grant you safe passage through our dark. Agreed.", "The pact is sealed in silence."],
    refuse: ["The void does not open for such terms.", "We decline. Seek your bargain in the light."],
    threat: ["Respect our borders, or vanish where no sensor can pierce.", "Remember that there is nothing we do not know."],
    thanks: ["Your courtesy echoes warmly across the void.", "Our gratitude. May the dark keep you safe."],
    greet: ["We see what you are. Welcome to the lightless reaches.", "Well met, traveler. Step gently through the shadow."],
    plead: ["We seek only to watch in peace. Turn your war toward brighter stars.", "Why disturb the quiet of the void when louder empires crave your blood?"],
  },
  mahact: {
    taunt: ["KNEEL, lesser creature, before I command your own admirals to fire on you.", "You play at empire on the ashes of our throne."],
    joke: ["Equal rights in the Council? How delightfully absurd.", "My scepter says you actually volunteered to surrender."],
    agree: ["Your obedience pleases Ixth. Proceed.", "Accepted. Serve well and you may keep your fleet."],
    refuse: ["Insolent worm. Dismissed.", "No. The Gene-Sorcerers do not haggle with cattle."],
    threat: ["One pulse of our scepter and your own flagship will turn on your homeworld.", "Defy the kings of Ixth and learn why the First Empire feared our name."],
    thanks: ["A proper tribute from a dutiful subject.", "Your usefulness has earned you another cycle of breath."],
    greet: ["Lower your head when Ixth speaks.", "Greetings, upstart. Lay your tribute at our feet."],
    plead: ["Why throw fragile fleets against Ixth when softer thrones await?", "Turn aside, and we may spare your bloodline when we reclaim the galaxy."],
  },
  nomad: {
    taunt: ["I already watched you lose this engagement in two other timelines.", "Keep pushing. The Memoria loves an easy payday."],
    joke: ["I am only here to prevent an apocalypse, no need to act nervous.", "Have we met a century from now yet? I keep losing track of your treaties."],
    agree: ["Smart move. That keeps the future intact.", "Deal. Consider the contract signed."],
    refuse: ["Pass. I have seen where that road leads.", "No thanks. The odds on that wager are terrible."],
    threat: ["Cross my company and I will drop the Memoria straight across your bow.", "Do not make me rewrite your future into a much shorter one."],
    thanks: ["Appreciate the assist. You just saved me a messy jump.", "Cheers, friend. I owe you one in this century or the next."],
    greet: ["Well met. Keep up; history moves fast around Sumerian Station.", "Greetings from Arcturus. Care to preserve the future together?"],
    plead: ["Trust me, firing on the Memoria now ruins everyone's survival!", "Spare the messenger! There is a far worse catastrophe brewing across the rim!"],
  },
  naaz: {
    taunt: ["Two minds in every Eidolon, twice the firepower! Try keeping up!", "Nice cruiser! Mind if we scrap it for relic parts?"],
    joke: ["Garv swears the laser traps are off this time—fingers crossed!", "We unearthed three ancient relics before second watch. What did your yards build?"],
    agree: ["Awesome! Shake on it, partner!", "Sounds like a fair swap! Let us roll!"],
    refuse: ["Nah, we can dig up something far better ourselves.", "Pass! Even the Rokha think that is a bad deal."],
    threat: ["Touch our dig sites and the Eidolons drop straight onto your capital!", "Keep crowding Naazir and we will supercharge every battery in the sector!"],
    thanks: ["You are the best! Next relic we find, we will think of you!", "Much appreciated, ally! May your scanners always ping gold!"],
    greet: ["Hey there, neighbor! Time for something new?", "Greetings from Naazir and Rokha! Found any forgotten vaults lately?"],
    plead: ["Hey, we are just humble explorers! Pick on one of the giant warlords!", "Leave our little dig sites alone! We outgrew squabbling over old empires' bones!"],
  },
  titans: {
    taunt: ["We dreamed through the rise and fall of empires. Your fleet is a passing breeze.", "Strike our stone if you dare; the mountain will answer."],
    joke: ["Take your time. Ten thousand cycles have made us very patient.", "Your orbital bombardment woke up one of our statues. Now it is grumpy."],
    agree: ["Your words carry weight. Elysium concurs.", "Agreed. Let this accord endure like bedrock."],
    refuse: ["Unacceptable. The Titans remain unmoved.", "No. We seek something more permanent than a hasty bargain."],
    threat: ["Trespass upon our slumbering worlds and the ground itself will swallow your legions.", "Do not wake what sleeps beneath our crust unless you wish to be buried."],
    thanks: ["Your courtesy is carved into our memory.", "Elysium thanks you, young traveler."],
    greet: ["We awaken to greet you, young one.", "Hail from Elysium. Speak clearly and without haste."],
    plead: ["Let us tend our quiet gardens of stone; we seek no quarrel with your house.", "Why batter yourself against ancient walls while fragile rivals sit undefended?"],
  },
  bastion: {
    taunt: ["Hit our walls with everything you have! No option but victory!", "We survived the Nekro Virus. Your fleet is a light drizzle."],
    joke: ["Our drydocks work best while taking direct artillery fire. Builds character.", "Retreat? Our engineers forgot to install reverse thrusters."],
    agree: ["Solid terms. Go—we will hold your flank.", "Agreed. Good allies are rare out here."],
    refuse: ["No deal. We did not hold Ordinian to fold now.", "Negative. Take that bargain somewhere softer."],
    threat: ["Push our line and we will rally every survivor in the sector against you.", "Bring your siege fleet; Revelation has broken stronger armadas than yours."],
    thanks: ["Your aid keeps the beacon burning on Ordinian. We owe you one.", "Gratitude from the Last Bastion. We remember who stood beside us."],
    greet: ["Revelation Control online. State your business, friend.", "Hail, neighbor. Keep the beacons lit and the borders steady."],
    plead: ["We are still rebuilding from the ashes! Turn your guns on a fresher tyrant!", "Why crush the shield holding back the dark when conquerors march right beside you?"],
  },
  deepwrought: {
    taunt: ["You stare at the sky and miss the abyssal currents dragging your fleet under.", "Surface tactics are so loud. Come test your hull at ten thousand fathoms."],
    joke: ["Yes, the D.W.S. Luminous is flooded on purpose. Bring a respirator if you visit.", "Peer review takes years; we prefer singing our theorems to the abyss."],
    agree: ["~Together-sing-one- -your hypothesis holds true. The Scholarate agrees.", "Agreed. Life triumphs when our currents run together."],
    refuse: ["Shallow terms. The Deepwrought decline.", "No. We left the Universities to break chains, not forge new ones."],
    threat: ["Crowd Ikatena again and learn what abyssal pressure does to a cruiser hull.", "We freed minds from Mahact thralldom; do not mistake scholars for prey."],
    thanks: ["Your aid illuminates the deep. Thank you.", "~Together-ends-suffering- -most generous. Our archives note your kindness."],
    greet: ["~Together-sing-deep- -greetings from the trenches of Ikatena.", "Well met, surface-dweller. Care to trade charts of the abyss?"],
    plead: ["Ikatena has bled enough under Mahact chains! Leave our seas in peace!", "Spare our sanctuaries; we only wish to heal the deep, while others covet your throne!"],
  },
  firmament: {
    taunt: ["Why ask who should rule you when we are already dismantling your throne?", "Your generals look loyal. Give Cronos until morning."],
    joke: ["Easy now, that forged pamphlet in your barracks is completely satirical.", "Of course we respect the Council. Right up until the floor gives way."],
    agree: ["A quiet bargain between equals serves us both. Done.", "Agreed. Keep your eyes open and your channels clean."],
    refuse: ["No thanks. Why have rulers at all?", "Declined. Try selling that leash to someone else."],
    threat: ["Push the Firmament and your own garrisons will open the gates for us.", "Check your officers' loyalty before you rattle your saber at Cronos."],
    thanks: ["Useful, and cleanly done. My thanks.", "A smart investment on your part. The cadre remembers."],
    greet: ["Greetings, friend. Tired of bowing to the great houses yet?", "Well met. Let us talk quietly, away from imperial ears."],
    plead: ["Why hunt shadows on the rim when the bloated tyrants sit right in the Core?", "Leave Cronos in peace; we are far more dangerous as enemies than as neighbors."],
  },
  obsidian: {
    taunt: ["Your beacons are dying one by one. Listen closely to the silence.", "Case Midnight Omega: your own allies already whisper our name in the dark."],
    joke: ["Empty skies, empty thrones, empty hulls. Everything fits so neatly.", "Do not worry about the static on your comms. It is only smiling back."],
    agree: ["The hollow accepts your bargain. For now.", "Agreed. Keep your false lanterns away from Cronos."],
    refuse: ["Hollow words. Rejected.", "No. The veil chooses its own harvest."],
    threat: ["Step into our shadow and nothing returns to file a final report.", "Extinguish your pride, or mayday will be your fleet's last broadcast."],
    thanks: ["Your offering feeds the dark.", "Noted in silence. You have bought yourself a little time."],
    greet: ["The beacons are out. Welcome to the hollow.", "Greetings from the dark between your stars."],
    plead: ["Look away from the hollow; brighter prizes gleam across the galaxy.", "Disturb us and the night turns your way. Choose another target."],
  },
  crimson: {
    taunt: ["Cut the cord, burn the seal, and watch your pretty blockade fracture!", "The Core forgot Ahk Creuxx existed. Tonight we remind them!"],
    joke: ["Imperial charts insist this wormhole is impossible. Good thing we ignore imperial charts.", "Our Exiles fly on salvaged parts and pure unending spite."],
    agree: ["Fair enough. The Rebellion takes a straight deal when it sees one.", "Agreed. Just do not try putting Mahact chains back on us."],
    refuse: ["No chance. We answer to no throne.", "Keep your gilded truce. We fight on our own frequency."],
    threat: ["Corner the Crimson Rebellion and we will tear your whole sector frequency apart!", "Send your cruisers; our Exiles know pain unending and hunger for yours."],
    thanks: ["Appreciate the supplies, friend. We will put them to loud use.", "Thanks. Good to know someone out here still respects exiles."],
    greet: ["Transponders off, blades drawn. What do you want?", "Greetings from Ahk Creuxx. Friend of the free, or another tyrant?"],
    plead: ["We have bled enough in exile! Point those cannons at the kings in the Core!", "Why crush a band of exiles when the Mahact and tyrants steal the throne?"],
  },
  ralnel: {
    taunt: ["Your intel is three cycles out of date. Check who bought the update.", "Good luck catching a Linkship when we already control your transit lane."],
    joke: ["Your delivery is guaranteed on time! Just mind the transit tariff, escort fee, and hazard surcharge.", "We never break contracts; we simply enforce every clause in the web."],
    agree: ["Cash in hand, seal on the ledger—we have a deal!", "Agreed! Our couriers are already inbound to settle accounts."],
    refuse: ["Terrible margins. The Consortium passes.", "No deal. My *zio qen* accountants would throw me out an airlock."],
    threat: ["Cheat the web of obligation and every pirate on the rim gets your convoy codes.", "Corner a Ral Nel crew and watch how fast survival instincts turn lethal."],
    thanks: ["Pleasure doing business! Be sure to commend our couriers to the Council Registry!", "Much obliged! Your preferred-client rate is already active."],
    greet: ["Ral Nel Consortium at your service! Couriers, processors, or cash in hand?", "Hail, valued client! What obligations can we balance for you today?"],
    plead: ["Whoa, easy! Ruining your own couriers defies both gravity and arithmetic!", "Why fire on the couriers when rival houses with unpaid debts sit right over there?"],
  },
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
