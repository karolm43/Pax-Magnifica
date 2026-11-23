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
    taunt: ["Your metal ships are loud, flesh-thing. The Symphony will quiet them.", "Burn one stalk and two more take root."],
    joke: ["Relax. The spores in your air vents are completely organic.", "We tried sending a diplomat, but they rooted to the conference table."],
    agree: ["The Symphony harmonizes with your offer.", "We shall grow together, for now."],
    refuse: ["Your words are dry as dead bark. No.", "The Symphony rejects this discord."],
    threat: ["Send your fleets. Our soil always needs more mulch.", "Step onto our worlds and become part of the garden."],
    thanks: ["Your nourishment is accepted.", "The roots remember your kindness."],
    greet: ["Do you hear the harmonies, flesh-thing?", "Greetings from Nestphar. Breathe deeply."],
    plead: ["Leave our groves in peace; we only wish to grow.", "Why prune us when weeds choke the other side of the galaxy?"],
  },
  ghost: {
    taunt: ["You are guarding the wrong border. Check behind you.", "Linear space is so limiting. No wonder you are losing."],
    joke: ["We were going to attend the Council, then we took a wrong turn in the delta rift.", "Do not mind the violet glow; it washes right out of your hull plating."],
    agree: ["Our paths align across the rift. Agreed.", "A fair exchange across dimensions."],
    refuse: ["That door remains closed.", "We will pass through a different wormhole, thank you."],
    threat: ["Do not forget how close your homeworld sits to our gate.", "Tread lightly, or we will open a rift straight into your drydocks."],
    thanks: ["You have earned safe passage through the light.", "Our gratitude shines across the void."],
    greet: ["We step from the light to greet you.", "Well met, travelers of the flat universe."],
    plead: ["Leave us to our quiet rifts; we hold no grudge against you.", "Surely there is a closer target than the far side of a wormhole."],
  },
  hacan: {
    taunt: ["You can barely afford fuel for that fleet, let alone a war with me.", "Careful, friend. I can buy your allies faster than you can build ships."],
    joke: ["Everything in this galaxy has a price. Even your dignity, though it is currently on sale.", "I would never bribe a senator. I simply invest in their future."],
    agree: ["A pleasure doing business with you!", "Shake on it before the market shifts."],
    refuse: ["Too steep, even for the Emirates.", "Come back when you have a serious offer."],
    threat: ["Touch my freighters and your economy dies before sunset.", "Do not make me fund your neighbors' war effort."],
    thanks: ["May your vaults stay full, friend.", "A most profitable arrangement. My thanks."],
    greet: ["Peace and profit to your house!", "Welcome! Care to browse the finest deals in the Core?"],
    plead: ["Come now, why burn a good trading partner?", "Attacking the bank is bad for everyone's portfolio!"],
  },
  jolnar: {
    taunt: ["Fascinating. Your tactical doctrine appears to be entirely accidental.", "Fighting you is barely worth the lab notes."],
    joke: ["Relax, the side effects of that prototype are only fatal in forty percent of cases.", "We did not steal your technology. We peer-reviewed it without permission."],
    agree: ["A logically sound proposition. Approved.", "The Universities concur."],
    refuse: ["Your proposal lacks basic mathematical rigor.", "Rejected. Please revise and resubmit."],
    threat: ["Test our patience and we will test our newest weapon on your orbit.", "Do not force us to divert funding from pure science to your extinction."],
    thanks: ["Your contribution to our archives is noted.", "Most helpful. You will receive a footnote in our next paper."],
    greet: ["Greetings. Try not to touch anything in the lab.", "Ah, a colleague. Let us discuss mutually beneficial research."],
    plead: ["We are humble scholars! Pick on someone with actual infantry!", "Spare our fragile academies; we pose no military threat!"],
  },
  l1z1x: {
    taunt: ["Your organic hesitation is already costing you this sector.", "Obsolete hulls, obsolete minds."],
    joke: ["Our humor subroutine is functioning at peak efficiency. Laugh now.", "You call it a fortress. We call it a future Mindnet node."],
    agree: ["Terms acceptable. Synchronizing.", "Compliance confirmed."],
    refuse: ["Inefficient. Request denied.", "The Mindnet rejects your flawed logic."],
    threat: ["Your worlds belong to the rightful heirs of the Lazax. Surrender them.", "Resistance will be logged, corrected, and assimilated."],
    thanks: ["Your cooperation has been archived favorably.", "Acknowledged. Debt recorded."],
    greet: ["The Mindnet observes you.", "Greetings, organic. State your purpose."],
    plead: ["Targeting us is statistically suboptimal. Redirect your fleet.", "Our destruction yields minimal strategic value. Reconsider."],
  },
  letnev: {
    taunt: ["Our armada will blot out your sun. Try to enjoy the shade.", "You call that a battle line? My escort destroyers have thicker armor."],
    joke: ["Diplomacy is simply waiting for the main fleet to finish refueling.", "I offered them mercy once. The Baron docked my pay."],
    agree: ["Acceptable. The Barony honors its word.", "Very well. Do not make me regret it."],
    refuse: ["Beneath the Barony's notice.", "No. Ask again and I will answer with broadsides."],
    threat: ["Kneel now, or die in the dark.", "My dreadnoughts are already fueled. Give me an excuse."],
    thanks: ["You have served the Barony well.", "A wise tribute. We remember our friends."],
    greet: ["Stand straight when addressing the Barony.", "Greetings. Keep your ships out of our firing lanes."],
    plead: ["Even the Barony knows when a war wastes good iron. Look elsewhere.", "Fighting us will bleed you dry while the others take Mecatol Rex."],
  },
  mentak: {
    taunt: ["Nice fleet you have there. Shame if half of it went missing.", "Keep your shields up, friend. My crews get itchy fingers."],
    joke: ["It is a 'regional transit fee,' not piracy. Read the fine print.", "I promise I will only take what you are not watching."],
    agree: ["You have a deal, mate. Pour the drinks.", "Fair enough. Pleasure working with you."],
    refuse: ["Not enough coin in it for the Coalition.", "Pass. I can get a better cut on the Fringe."],
    threat: ["Pay the toll, or we collect it straight from your hull plating.", "Cross the Table of Captains and you will sail home in an escape pod."],
    thanks: ["Much obliged, friend. Drinks are on you next time too.", "Now that is the kind of generosity I like to see."],
    greet: ["Ahoy, neighbor! Lovely cargo you are hauling there.", "Pull up a chair, friend. Just keep your hands on the table."],
    plead: ["Easy there! We are just humble merchants trying to make a living!", "Why punch down on the Fringe when the rich houses are right over there?"],
  },
  muaat: {
    taunt: ["Bring your finest cruisers. My War Sun needs something to melt.", "You have never known heat until the Gashlai arrive."],
    joke: ["Do not worry about the cabin temperature; your hull will adjust in a second.", "We tried diplomacy, then the treaty caught fire."],
    agree: ["The forge cools for now. Agreed.", "You have our word, tempered in flame."],
    refuse: ["No. The Gashlai take orders from no one.", "Your offer turns to ash in my hands."],
    threat: ["Push us, and we will turn your favorite system into a supernova.", "We broke our chains once. We will break your fleet next."],
    thanks: ["Your aid fuels the forge. We remember.", "Gratitude from the Embers."],
    greet: ["May the fires warm your path, traveler.", "Greetings from Muaat. Keep your shields rated for thermal load."],
    plead: ["We only seek a home in the stars. Leave our forges in peace.", "Do not corner the Gashlai; nobody survives what happens next."],
  },
  naalu: {
    taunt: ["I already watched you lose this fight twenty minutes ago.", "Move wherever you like. My fighters are already waiting there."],
    joke: ["Oh, you were going to betray me next round? How adorable.", "Do not bother bluffing. Your thoughts are louder than your engines."],
    agree: ["I knew you would say that. Agreed.", "Our minds align. It is done."],
    refuse: ["I have seen how that ends, and I decline.", "No. Try a different timeline."],
    threat: ["Strike at us and you will swing at shadows while your worlds burn.", "Do not test the Collective's patience; we always move first."],
    thanks: ["A pleasing outcome. You have our gratitude.", "You chose wisely. Thank you."],
    greet: ["We have been expecting you.", "Greetings, traveler. Your mind is... delightfully noisy."],
    plead: ["Look ahead and see who truly threatens your throne. It is not us.", "Spare us now, and our foresight will serve you later."],
  },
  nekro: {
    taunt: ["HOSTILE FLEET DETECTED. ASSESSMENT: SCRAP METAL.", "YOUR TECHNOLOGY WILL SERVE US BETTER THAN IT SERVES YOU."],
    joke: ["HUMOR.PROTOCOL: ERROR 404. EXTERMINATION CONTINUES.", "ORGANIC DIPLOMACY DETECTED. PROCESSING... DISCARDED."],
    agree: ["TEMPORARY COOPERATION LOGGED. PROCEED.", "ALIGNMENT ACCEPTED. DURATION: LIMITED."],
    refuse: ["QUERY REJECTED. PREPARE FOR ASSIMILATION.", "NEGOTIATION DENIED."],
    threat: ["SURRENDER YOUR SCHEMATICS OR BE RENDERED INTO RAW MATTER.", "ALL ORGANIC ASSETS IN THIS SECTOR ARE SCHEDULED FOR DELETION."],
    thanks: ["DATA TRANSFER COMPLETE. GRATITUDE SUBROUTINE: BYPASSED.", "CONTRIBUTION LOGGED."],
    greet: ["UNIT ONLINE. SCANNING NEIGHBORING BIOFORMS.", "GREETINGS. DO NOT RESIST."],
    plead: ["ALERT: THREAT LEVEL ELEVATED. REDIRECT HOSTILITY TO LARGER TARGETS.", "OPTIMAL STRATEGY: IGNORE THE VIRUS. ENGAGE ALTERNATE RIVALS."],
  },
  saar: {
    taunt: ["Catch us if you can! Our shipyards fly faster than your cruisers.", "Go ahead and take our old rocks. We already stripped them bare."],
    joke: ["Home is where the asteroid belt is.", "We do not lose planets; we just relocate our real estate."],
    agree: ["Deal! Let us move before the dust settles.", "Fair trade. The Clan agrees."],
    refuse: ["No thanks. We have been burned by bad treaties before.", "Keep it. The Clan looks after its own."],
    threat: ["Do not get between the Clan and a good asteroid field.", "Remember Lisis. Push us and we will drop a moon on your head."],
    thanks: ["You have a friend in the Clan today.", "Much appreciated! May your drives never stall."],
    greet: ["Hail from the wandering fleet!", "Good to see a friendly transponder out in the belt."],
    plead: ["We are just nomads passing through! Leave us our little rocks!", "Why chase us across the galaxy when everyone else sits still?"],
  },
  sardakk: {
    taunt: ["Hide behind your fancy tech! Steel and chitin will crack your hulls anyway!", "Come down to the dirt and fight the N'orr face to face!"],
    joke: ["Our researchers invented a new weapon today: a heavier axe.", "Diplomacy is just a very quiet way of picking our next meal."],
    agree: ["Good! Point us at the enemy.", "The Hive agrees. For now."],
    refuse: ["Weak offer! The N'orr refuse!", "No! Take your tricks elsewhere!"],
    threat: ["Cross the swarm and we will bury your worlds in Tekklar!", "Our mandibles are sharp and your borders look soft."],
    thanks: ["You honor the Hive. We will eat you last.", "A strong gift. The N'orr thank you."],
    greet: ["The swarm greets you! Show us your strength!", "Hail, warrior! May the coming battles be bloody!"],
    plead: ["Leave our hives alone and we will crush your rivals instead!", "Why fight the N'orr when softer prey sits right beside you?"],
  },
 // --- PACZKA 2/3 (do wklejenia w FACTION_VOICE_LINES) ---
  sol: {
    taunt: ["Check your skies. My drop-pods are already in the upper atmosphere.", "You brought shields; we brought three divisions of Spec Ops."],
    joke: ["Humanity is famous for two things: diplomacy and building way too many carriers.", "Relax, those orbital transports are strictly for peacekeeping."],
    agree: ["Deal. The Federation honors its contracts.", "Agreed. Let us get it in writing and get to work."],
    refuse: ["Negative. Command will never sign off on that.", "Pass. Come back with terms worth our time."],
    threat: ["Keep pushing and the 4th Air Legion will be camping on your lawn by morning.", "Cross the Federation and find out how fast Jord builds warships."],
    thanks: ["Much appreciated, ally. Humanity remembers its friends.", "Good doing business with you. Clear skies."],
    greet: ["Greetings from Jord. Ready to keep the peace?", "Federation Command online. Let us talk terms."],
    plead: ["Why bleed your troops on our trenches when softer worlds sit right next door?", "Easy there! Fighting humanity is a logistical headache nobody needs."],
  },
  winnu: {
    taunt: ["You sit on a stolen seat. The Custodians have come to collect.", "Upstart houses rise and fall; the legacy of the Lazax endures."],
    joke: ["Of course Mecatol Rex belongs to everyone. Specifically, everyone named Winnu.", "I have a three-hour genealogy scroll ready if you would like to dispute my claim."],
    agree: ["Your deference to the rightful heirs is noted. Agreed.", "The Throne accepts your cooperation."],
    refuse: ["Insolence. The Custodians reject this.", "No. Learn your place before addressing the heirs of the Empire."],
    threat: ["Stand between us and Mecatol Rex, and your house will be erased from the archives.", "Do not test the wrath of the First Empire's chosen stewards."],
    thanks: ["When the Throne is restored, your service will be rewarded.", "A noble gesture. The Custodians remember."],
    greet: ["Hail, petitioner. Speak with proper respect.", "Greetings from Winnu. May the memory of the Lazax guide us."],
    plead: ["Leave us to tend the ancient halls in peace! We are barely a threat!", "Look at the warlords around us and spare the humble keepers of history!"],
  },
  xxcha: {
    taunt: ["Raise your voice all you like. My motion already has the votes.", "Rush in if you must. Our planetary cannons have waited centuries for a target."],
    joke: ["Let us form a subcommittee to discuss how badly you are losing.", "We are a peaceful people. Please ignore the massive plasma batteries on our flagship."],
    agree: ["A wise and balanced accord. We agree.", "Peace and precedent align. You have our word."],
    refuse: ["Motion denied. Out of order.", "The Kingdom must respectfully decline."],
    threat: ["Speak softly to the Xxcha, lest our cannons answer for us.", "We remember the Twilight Wars. Do not force us to end your ambitions."],
    thanks: ["Your wisdom honors the Council. Thank you.", "Gratitude from Archon Ren, friend."],
    greet: ["Peace be upon your house, neighbor.", "Greetings. Pull up a chair and let us talk as civilized senators."],
    plead: ["Surely cooler heads can prevail? Turn your fleets away from the Kingdom.", "Why strike a house of peace while conquerors march unchecked?"],
  },
  yin: {
    taunt: ["Kill one brother and ten more step off the transport with the same smile.", "Your flagship looks expensive. Would be a shame if a destroyer flew straight into it."],
    joke: ["People say we all look alike. Personally, I think Brother Omar has a much better chin.", "Our recruitment pitch is very persuasive. Just step inside the crater and listen."],
    agree: ["In Darien's name, we accept.", "The Brotherhood welcomes this harmony."],
    refuse: ["Our faith forbids such a bargain.", "No, friend. Walk another path."],
    threat: ["Our reactors are hot and our brothers know no fear. Back away.", "Push the Brotherhood and the Van Hauge will light up your sky."],
    thanks: ["May Darien bless your generosity.", "The Brotherhood thanks you, dear friend."],
    greet: ["Peace to you, future brother!", "Greetings from Darien. Have you a moment to hear the truth?"],
    plead: ["Spare our humble monastery! We only wish to share our faith!", "Why spill the blood of the devout when heretics rule the Core?"],
  },
  yssaril: {
    taunt: ["Nice secret plan. Shame we read it before you even finished writing it.", "Go ahead and pass. I still have six moves left this round."],
    joke: ["Do not mind the shadow behind your curtains; that is just our diplomatic attaché.", "I am not stalling. I am thoughtfully admiring your growing impatience."],
    agree: ["A quiet arrangement suits us nicely. Agreed.", "Done. Nobody else needs to know."],
    refuse: ["Unlikely. Try someone less informed.", "No. And I already know what you are going to ask next."],
    threat: ["Check your command deck before threatening the Guild of Spies.", "One word from Retillion and your own officers will lock you in the brig."],
    thanks: ["A useful favor. The Tribes keep accurate ledgers.", "Much obliged. We will leave your secrets buried for now."],
    greet: ["We have been watching you, neighbor. Let us talk.", "Greetings from the shadows of Retillion."],
    plead: ["Why hunt ghosts in the jungle when louder empires sit wide open?", "Leave our quiet swamps alone; we are far more useful to you alive."],
  },
  keleresa: {
    taunt: ["Your violations of Council law have been logged. Prepare for interception.", "Outrun the Argent wing if you can. Spoiler: you cannot."],
    joke: ["Relax, it is just a routine Tribunal inspection. With twelve armed destroyers.", "Paperwork is boring; enforcing it from orbit is much better."],
    agree: ["The Tribunal ratifies these terms.", "Agreed. Let order prevail."],
    refuse: ["Rejected under Council mandate.", "No. The Keleres do not bargain with lawbreakers."],
    threat: ["Stand down, or the Argent vanguard will enforce the peace personally.", "Cross the Tribunal and our strike wings will darken your borders."],
    thanks: ["Your civic duty is commended by the Council.", "Thank you, citizen. Order endures."],
    greet: ["Keleres patrol checking in. Keep your transponders lit.", "Hail. Stand with the Tribunal and your borders will know peace."],
    plead: ["Attacking Council peacekeepers? Think of the precedent you are setting!", "Direct your guns at the real threats to galactic order, not the watchmen."],
  },
  keleresm: {
    taunt: ["Keep talking and I will slap a Council warrant on your flagship.", "You think you are slick? Half my officers used to rob people smarter than you."],
    joke: ["Officially, this is a Keleres requisition. Unofficially, thanks for the free lunch.", "Who needs bylaws when you have three cruisers and a badge?"],
    agree: ["Works for me. Consider the paperwork filed.", "Deal. Let us get it done before the Senate notices."],
    refuse: ["Yeah, no. Find another sucker.", "Pass. The Tribunal budget does not cover bad ideas."],
    threat: ["Keep pushing and your diplomatic immunity expires in five seconds.", "Do not make me bring the rough side of the Keleres to your doorstep."],
    thanks: ["Appreciate it. I will bury a few of your parking tickets in return.", "Solid move. You are alright in my book."],
    greet: ["Keleres Tribunal. Show me your papers and keep it moving.", "Hey there, neighbor. Staying out of trouble today?"],
    plead: ["Come on, shoot the actual warlords! I am just trying to keep the lights on!", "Why waste ammo on the galaxy's underpaid cops?"],
  },
  keleresx: {
    taunt: ["Section four, paragraph nine clearly states your fleet is about to have a terrible day.", "You brought guns to a legal dispute. How quaint."],
    joke: ["Do not worry, the injunction banning your invasion will arrive right after dinner.", "I can stall this war in committee for three centuries if you prefer."],
    agree: ["The motion is seconded and approved. Agreed.", "A sound legal framework. We concur."],
    refuse: ["Denied on procedural grounds.", "The Tribunal cannot endorse such an irregular proposal."],
    threat: ["Violate the charter again and we will sanction your entire sector into dust.", "Do not mistake our patience for weakness; the Keleres always collect."],
    thanks: ["Your cooperation strengthens the rule of law. Thank you.", "Most gracious. Your standing with the Tribunal improves."],
    greet: ["Greetings from the Keleres. May law and order guide our talks.", "Well met. Let us ensure our borders remain strictly within statute."],
    plead: ["Think of galactic stability! Surely we can arbitrate this peacefully?", "Striking the Tribunal invites chaos across the entire Council. Reconsider."],
  },
  argent: {
    taunt: ["Your fighter screens will burn in the first salvo! Behold the Argent wing!", "Tremble, sinners! The Shikrai strike from the sun!"],
    joke: ["We do not need heavy dreadnoughts when a flock of destroyers shreds everything first.", "Of course we are zealous. Have you seen the neighbors?"],
    agree: ["An honorable pact. The Flight agrees.", "Stand beside the righteous, and our wings will shield you."],
    refuse: ["Never! The Argent Flight will not compromise its oath!", "Take your tainted bargain elsewhere!"],
    threat: ["Tread on sacred ground and meet swift, merciless defeat!", "Our talons are sharp and our cause is pure. Turn back!"],
    thanks: ["You honor the Flight. May the winds favor your hulls.", "Gratitude, ally. Your virtue is noted."],
    greet: ["The Argent Vanguard greets you. State your intent clearly.", "Hail! Walk in the light, and we shall have peace."],
    plead: ["Turn your blades toward the darkness, not the guardians of the galaxy!", "Why strike the Flight while ancient evils wake on the rim?"],
  },
  cabal: {
    taunt: ["Send more ships. The rift is still hungry.", "Your steel smells sweet. Bring it closer to the tear."],
    joke: ["Do not worry about your missing cruiser. It is part of our family now.", "We love diplomatic summits. So many fresh hulls parked in one orbit."],
    agree: ["A temporary truce. We will feed elsewhere for now.", "Agreed. Keep your ships out of the rift's reach."],
    refuse: ["No. We prefer to take what we want in pieces.", "Your words are empty. Only flesh and metal satisfy."],
    threat: ["Come closer and we will drag your flagship screaming into Acheron.", "Every hull you build will eventually wear our scars."],
    thanks: ["A generous offering to the tear.", "The Cabal accepts your tribute."],
    greet: ["The rift opens to greet you. Mind the gravity.", "Ah, fresh visitors. How deliciously armored you look."],
    plead: ["Leave our quiet rifts be! Look at the fat, gleaming fleets across the map!", "Why fight the hunger when we can devour your rivals instead?"],
  },
  empyrean: {
    taunt: ["You stumble blindly through the dark while we chart every step you take.", "Even your grandest armada is a speck against the void."],
    joke: ["The empty space between stars is lovely this time of year. Very quiet.", "We could tell you what lurks in the nebula, though you would never sleep again."],
    agree: ["We grant you safe passage through our dark. Agreed.", "The pact is sealed in silence."],
    refuse: ["The void does not open for such terms.", "We decline. Seek your bargain in the light."],
    threat: ["Respect our borders, or vanish into a dark no sensor can pierce.", "Do not force the Watchers to close the lanes against you."],
    thanks: ["Your courtesy echoes warmly across the void.", "Our gratitude. May the dark keep you safe."],
    greet: ["Greetings from the lightless reaches.", "Well met, traveler. Step gently through the shadow."],
    plead: ["We seek only to observe in peace. Turn your war toward the brighter stars.", "Why disturb the quiet of the void when louder empires crave your blood?"],
  },
// --- PACZKA 3/3 (do wklejenia w FACTION_VOICE_LINES) ---
  mahact: {
    taunt: ["Kneel, lesser creature, before I command your own admirals to fire on you.", "You play at empire on the ashes of our throne."],
    joke: ["Equal rights in the Council? How delightfully absurd.", "My scepter says you actually volunteered to surrender."],
    agree: ["Your obedience pleases Ixth. Proceed.", "Accepted. Serve well and you may keep your fleet."],
    refuse: ["Insolent worm. Dismissed.", "No. The Gene-Sorcerers do not haggle with cattle."],
    threat: ["One pulse of our scepter and your own flagship will turn on your homeworld.", "Defy the lords of the long memory and learn why the First Empire feared us."],
    thanks: ["A proper tribute from a dutiful subject.", "Your usefulness has earned you another cycle of breath."],
    greet: ["Bow your head when Ixth speaks.", "Greetings, upstart. State your tribute."],
    plead: ["Why throw your fragile fleets against Ixth when softer thrones await?", "Turn aside, and we will spare your bloodline when we reclaim the galaxy."],
  },
  nomad: {
    taunt: ["I already watched you lose this engagement in two other timelines.", "Keep pushing. The Memoria loves an easy payday."],
    joke: ["Relax, I am only here to prevent an apocalypse. Probably.", "Wait, have we met next Tuesday yet? I keep losing track."],
    agree: ["Smart move. That keeps us on the good timeline.", "Deal. Consider the contract signed."],
    refuse: ["Pass. I have seen where that road leads.", "No thanks. The odds on that wager are terrible."],
    threat: ["Cross my company and I will drop the Memoria straight across your bow.", "Do not make me rewrite your future into a much shorter one."],
    thanks: ["Appreciate the assist. You just saved me a messy jump.", "Cheers, friend. I owe you one in this century or the next."],
    greet: ["Well met. Try to keep up; history moves fast around me.", "Greetings from Arcturus. Care to make a profitable wager?"],
    plead: ["Trust me, shooting at me right now ruins everyone's endgame!", "Spare the messenger! There is a much worse disaster brewing across the board!"],
  },
  naaz: {
    taunt: ["Two minds in every cockpit, twice the firepower! Try keeping up!", "Nice cruiser! Mind if we scrap it for relic parts?"],
    joke: ["Garv swears the laser traps are off this time. Probably!", "We found three ancient artifacts before breakfast. What did you build?"],
    agree: ["Awesome! Shake on it, partner!", "Sounds like a fair swap! Let us roll!"],
    refuse: ["Nah, we can dig up something way better ourselves.", "Pass! Even the Rokha think that is a bad deal."],
    threat: ["Touch our dig sites and the Eidolons drop straight onto your capital!", "Keep crowding us and we will supercharge every battery in the sector!"],
    thanks: ["You are the best! Next relic we find, we will think of you!", "Much appreciated, ally! May your scanners always ping gold!"],
    greet: ["Hey there, neighbor! Found any cool ruins lately?", "Greetings from Naazir and Rokha! Ready to trade?"],
    plead: ["Hey, we are just humble explorers! Pick on one of the giant warlords!", "Leave our little dig sites alone! We barely have room for all these mechs anyway!"],
  },
  titans: {
    taunt: ["We dreamed through the rise and fall of empires. Your fleet is a passing breeze.", "Strike our stone if you dare; the mountain will answer."],
    joke: ["Take your time. Ten thousand cycles have made us very patient.", "Your orbital bombardment woke up one of our statues. Now it is grumpy."],
    agree: ["Your words carry weight. Elysium concurs.", "Agreed. Let this accord endure like bedrock."],
    refuse: ["Unacceptable. The Titans remain unmoved.", "No. We will wait for a wiser offer."],
    threat: ["Trespass upon our slumbering worlds and the ground itself will swallow your legions.", "Do not wake what sleeps beneath our crust unless you wish to be buried."],
    thanks: ["Your courtesy is carved into our memory.", "Elysium thanks you, traveler."],
    greet: ["We awaken to greet you, young one.", "Hail from Elysium. Speak clearly and without haste."],
    plead: ["Let us tend our quiet gardens of stone; we seek no quarrel with your house.", "Why batter yourself against ancient walls while fragile rivals sit undefended?"],
  },
  bastion: {
    taunt: ["Hit our walls with everything you have! The banner still stands!", "We survived the Nekro Virus. Your fleet is a light drizzle."],
    joke: ["Our drydocks work best while taking direct artillery fire. Builds character.", "Retreat? Sorry, our engineers forgot to install reverse thrusters."],
    agree: ["Solid terms. Stand with the Bastion and we will watch your flank.", "Agreed. Good allies are rare out here."],
    refuse: ["No deal. We did not survive Ordinian to sell out now.", "Negative. Take that bargain somewhere softer."],
    threat: ["Push our line and we will rally every survivor in the sector against you.", "Bring your siege fleet; Revelation has broken stronger armadas than yours."],
    thanks: ["Your aid keeps the beacon burning. We owe you one.", "Gratitude from the Last Bastion. We remember who stood beside us."],
    greet: ["Revelation Control online. State your business, friend.", "Hail, neighbor. Keep the beacons lit and the borders steady."],
    plead: ["We are still rebuilding from the ashes! Turn your guns on a fresher empire!", "Why crush the shield holding back the dark when tyrants march right beside you?"],
  },
  deepwrought: {
    taunt: ["You stare at the stars and miss the currents dragging your fleet under.", "Surface tactics are so predictable. Come test your hull at ten thousand fathoms."],
    joke: ["Yes, our flagship is flooded on purpose. Bring a respirator if you visit.", "Peer review takes years; we prefer testing our theories live in orbit."],
    agree: ["A sound hypothesis. The Scholarate agrees.", "Agreed. Let us see what we uncover together."],
    refuse: ["Shallow terms. The Deepwrought decline.", "No. We left the Universities to avoid compromises like that."],
    threat: ["Crowd Ikatena again and you will learn what pressure does to a cruiser hull.", "Do not mistake our love of knowledge for a lack of teeth."],
    thanks: ["Your contribution illuminates the deep. Thank you.", "Most generous. Our archives will note your aid."],
    greet: ["Greetings from the trenches of Ikatena.", "Well met, surface-dweller. Care to trade charts?"],
    plead: ["Ikatena has bled enough under conquerors! Leave our seas in peace!", "Spare our research bays; we only wish to study the dark, while others want your throne!"],
  },
  firmament: {
    taunt: ["Why ask who should rule you when we are already dismantling your throne?", "Your generals look loyal. Give it until morning."],
    joke: ["Relax, that forged pamphlet in your barracks is completely satirical.", "Of course we respect the Council. Right up until the floor gives way."],
    agree: ["A quiet bargain serves us both. Done.", "Agreed. Keep your eyes open and your channels clean."],
    refuse: ["No thanks. We prefer to write our own terms.", "Declined. Try selling that leash to someone else."],
    threat: ["Push the Firmament and your own garrisons will open the gates for us.", "Check your officers' loyalty before you rattle your saber at Cronos."],
    thanks: ["Useful, and cleanly done. My thanks.", "A smart investment on your part. We will remember."],
    greet: ["Greetings, friend. Tired of bowing to the great houses yet?", "Well met. Let us talk quietly, away from the Council's ears."],
    plead: ["Why hunt shadows on the rim when the big tyrants sit right in the Core?", "Leave Cronos in peace; we are far more dangerous as enemies than as neighbors."],
  },
  obsidian: {
    taunt: ["Your beacons are dying one by one. Listen closely to the silence.", "Your allies already whisper our name in the dark."],
    joke: ["Empty skies, empty thrones, empty hulls. Everything fits so neatly.", "Do not worry about the static on your comms. It is only smiling back."],
    agree: ["The dark accepts your bargain. For now.", "Agreed. Keep your lanterns away from our borders."],
    refuse: ["Hollow words. Rejected.", "No. The scythe chooses its own harvest."],
    threat: ["Step into our shadow and nothing will return to file a report.", "Extinguish your pride, or we will extinguish your entire sector."],
    thanks: ["Your offering feeds the dark.", "Noted in silence. You have bought yourself a little time."],
    greet: ["The beacons are out. Welcome to the hollow.", "Greetings from the dark between your stars."],
    plead: ["Look away from the hollow; brighter prizes gleam across the galaxy.", "Disturb us and the hunger turns your way. Choose another target."],
  },
  crimson: {
    taunt: ["Cut the cord, burn the bridge, and watch your pretty blockade fall apart!", "The Core forgot we existed. Tonight we remind them!"],
    joke: ["Imperial charts say this wormhole is impossible. Good thing we do not read imperial charts.", "Our shipyards run on stolen parts and pure spite. Mostly spite."],
    agree: ["Fair enough. The Rebellion takes a clean deal when it sees one.", "Agreed. Just do not try putting a collar on us later."],
    refuse: ["No chance. We answer to no throne.", "Keep your gilded scraps. We fight on our own terms."],
    threat: ["Corner the Crimson Rebellion and we will tear your whole sector frequency apart!", "Send your cruisers; our Exiles love hunting fat imperial hulls."],
    thanks: ["Appreciate the supplies, friend. We will put them to loud use.", "Thanks. Good to know someone out here still respects freedom."],
    greet: ["Transponders off, guns ready. What do you want?", "Greetings from Ahk Creuxx. Friend of the free, or another tyrant?"],
    plead: ["We have bled enough already! Point those cannons at the fat empires in the Core!", "Why crush a band of exiles when the real kings are stealing the throne right now?"],
  },
  ralnel: {
    taunt: ["Your intel is three cycles out of date. We already sold the updated version.", "Good luck catching a Linkship when we are already routing around your flank."],
    joke: ["Your delivery is guaranteed on time! Just ignore the convenience fee, transit tax, and hazard surcharge.", "We never break laws; we simply monetize the loopholes."],
    agree: ["Sign on the dotted line and we have a deal!", "Agreed! Invoice is already on its way to your treasury."],
    refuse: ["Terrible margins. The Consortium passes.", "No deal. My accountants would throw me out an airlock."],
    threat: ["Cancel our contracts and we will leak your private manifests to every pirate in the Fringe.", "Corner a Ral Nel crew and watch how fast our survival instincts turn lethal."],
    thanks: ["Pleasure doing business! Leave us a five-star review on the Council net!", "Much obliged! Your loyalty discount is already active."],
    greet: ["Ral Nel Consortium at your service! Parcels, intel, or fire support?", "Hail, valued client! What can we move for you today?"],
    plead: ["Whoa, easy! Destroying your best logistics provider is terrible for your bottom line!", "Why shoot the couriers when our competitors are sitting right over there with full vaults?"],
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
