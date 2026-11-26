// Pola na lore (flavour) kart — WPISUJE UŻYTKOWNIK. Pusty string = brak (nic się nie wyświetla).
// Jeden wpis = jedna linia, tekst w cudzysłowie: "id": "Twój tekst.", // Nazwa karty
// Skrypt scripts/gen_lore_template.py dopisuje brakujące karty i nie rusza wpisanych tekstów.
// Lista = karty używane przez silnik (aktywne talie, frakcje, najnowsze wersje kart Codex/TE).
// Karty akcji, relikty, eksploracja, systemy i planety: tekst startowy skopiowany z assetów AsyncTI4 — tu go edytujesz.
// Pozostałe teksty w TYM folderze (entities/lore/): factionLore.ts (lore, cytaty, portrety frakcji),
// factionVoiceLines.ts (kwestie frakcji w czacie), chronicleLore.ts (Kronika Imperium),
// battleLore.ts (opisy bitew w oknie wyniku i w kronice).

export type LoreMap = Record<string, string>;

/** Leaders (agent / commander / hero). */
const leader: LoreMap = {
  "l1z1xcommander": "The newly integrated network flared to life, and the warships' guns spoke with one voice. The planetary shield flared and died under the concentrated barrage.", // 2RAM (l1z1x commander)
  "empyreanagent": "Acamar, the observer, greatest of the void-captains of the Empyrean. The lightless depths of space hold no terrors for them, for they have traveled from the raging black heart of the galaxy to its furthest edges, where even the stars grow cool and dim.", // Acamar (empyrean agent)
  "muaathero": "The star's corona began to boil and writhe, bathing the doomed worlds around it in a terrible glow. Aboard the war sun, Ba'al spread his arms wide. \"Behold,\" he said, \"The instrument of your deliverance.\"", // Adjudicator Ba'al (muaat hero)
  "deepwroughtcommander": "The Kieros were joyful and peace-loving - the Hylar reserved and calculating. Aello sought to bridge the gap between them, one verse, one lyric at a time.", // Aello (deepwrought commander)
  "jolnarcommander": "After the rift between the Deepwrought and the Universities, the universally disliked Agnlan Oln of Oln Medical replaced Ta Zern in an advisory role.", // Agnlan Oln (jolnar commander)
  "crimsonagent": "Ravin could remember who they had been before the thieving. They could recall the duration as well, mostly. But it was all so far away. Disconnected, almost unreal. Like a copied copy whose authenticity had degraded with each successive replica. Freedom had not come paired with hope.", // Ahk Ravin (crimson agent)
  "crimsoncommander": "After the battle had concluded, reports of a lone crimson figure, floating in the void, observing, were sent to command from not one, but nine Xxcha ships.", // Ahk Siever (crimson commander)
  "nomadhero": "Those who deal with the Nomad speak in hushed whispers about their most trusted officer; a Creuss in cracked and damaged armor, bleeding streams of violet light.", // Ahk-Syl Siven (nomad hero)
  "mahacthero": "As the army warily approached their foe, the gleaming golden figure raised their hand. Golden light flashed, and the army fell upon itself in wanton slaughter.", // Airo Shir Aur (mahact hero)
  "obsidiancommander": "Shattered, tattered, the broken dreams of empire fallen.", // Aroz Hollow (obsidian commander)
  "nomadagentartuno": "Once, Artuno was the head of security for Sumerian Station, trusted by Huro M'es and the other Sumerian factions to stay impartial and keep order. Then, two weeks after a chance meeting with the Nomad, M'es was in the brig, and the guilder leaders were either exiled or dead at her hand.", // Artuno the Betrayer (nomad agent)
  "winnuagent": "Berekon strode down the corridor, imperiously ignoring the nervous yard-master at his side. \"But Arbiter,\" the yard-master yelped. \"There's no way I can meet these new quotas.\" Berekon spared him a withering glance. \"You're mistaken. The Emperor has decreed it. That means there is no way that you will not.\"", // Berekar Berekon (winnu agent)
  "yinagent": "\"Brothers...\" Milor said, openly weeping as he watched the ships break apart in the sky above. \"They must not be forgotten! In Darien's name, we fight to the last!\" The crowd roared in support.", // Brother Milor (yin agent)
  "yincommander": "It is said that Omar's creation of the genetic spinner loom is the greatest breakthrough for the Brotherhood since Darien's first forbidden research centuries ago.", // Brother Omar (yin commander)
  "firmamentcommander": "Resolute in the Firmament, the Black Flag flies.", // Captain Aroz (firmament commander)
  "saaragent": "Even after settling in the Jorun Asteroid Field, the Saar tend to see their ships as a beloved home, and devote time and effort to improving them and personalizing them. For example, Captain Mendosa of the Fifth Fleet ensures his ships have the best engines the Saar can build.", // Captain Mendosa (saar agent)
  "hacanagent": "Responsible for all matters concerning the entire Kenara system, Carth is constantly enmeshed in a tangled web of trade deals, clan negotiations, and resource allocation pacts. To give her authority over the trading clans, she answers only to the Quieron.", // Carth of Golden Sands (hacan agent)
  "solcommander": "Beloved in the House of the People, General Gibson sees the diversity of humanity spread across the stars as the Federation's greatest potential strength.", // Claire Gibson (sol commander)
  "empyreanhero": "Procyon, the seeker, eldest of the Empyrean. They have mastered the mysteries of dark energy, and thus, they know all possible realities.", // Conservator Procyon (empyrean hero)
  "bastionagent": "Briar marveled at the sheer size of the Seraph. The technology was incredible. The Icon had truly given them something amazing. Still. Something about it was... off. Sometimes, as she walked the corridors of Revelation at night, she could not help but feel a familiar sense of dread.", // Dame Briar (bastion agent)
  "yinhero": "At Dannel's command, they burned out their spinners, welcoming thousands of new brothers into their ranks in mere weeks. Such is the potential of the Yin.", // Dannel of the Tenth (yin hero)
  "letnevhero": "\"The void is not simply nothingness. The Empyrean have known this for millennia. Is it any wonder that the greatest Letnev minds have discovered this too?\"", // Darktalon Treilla (letnev hero)
  "naazcommander": "The Eidolon is a dual-role mech that needs a skilled pilot and a cunning commando who are both slightly crazy; requirements that describe Dart and Tai perfectly.", // Dart and Tai (naaz commander)
  "ralnelhero": "He was the master, the king. There were no limits to Nel's ambition. No rules to be broken, no obstacles to be avoided. Only choice. A matrix of pure, unfettered futures.", // Director Nel (ralnel hero)
  "arboreccommander": "\"As I grow, I must expand. I send forth my Dirzuga into the galaxy, so that I may touch many lives.\"", // Dirzuga Rophal (arborec commander)
  "deepwroughtagent": "\"So many charts...fascinating.\" Ruthenia peered at Carrina's workspace through the tiny display. Several small aquariums lined each wall. \"There is one problem, though,\" she stated, raising her metallic shoulders in a sheepish shrug. \"I'm rather heavy, you see. I can't swim...\"", // Doctor Carrina (deepwrought agent)
  "jolnaragent": "After the Sidori Quarantine Breach forced the Hacan fleet to isolate and destroy Mishka Orbital, the Emirates demanded Doctor Sucaban be turned over to them for justice. Instead the Universities had the brilliant researcher 'die' in an aircar accident and installed him as a program director at their top-secret \"Black Trench\" facility.", // Doctor Sucaban (jolnar agent)
  "xxchacommander": "\"The Xxcha have not forgotten the Twilight Wars. Though we may speak softly, you would not be wise to attempt to silence us!\"", // Elder Qanoj (xxcha commander)
  "ghostagent": "When the Jol-Nar fleet emerged from their hidden ambush amongst the planet's rings, they found...nothing. The Creuss convoy had simply vanished. All that remained was a message drone for the Hylar commodore from Taivra, regretting that they would not be able to meet in person.", // Emissary Taivra (ghost agent)
  "solagent": "Daughter of Supreme Admiral Alastair DeLouis. Lauded for her contribution to the massively successful Centauri campaign. A brilliant tactician possessed by a fierce love for Jord, she is every bit her father's daughter.", // Evelyn DeLouis (sol agent)
  "nomadagentmercer": "\"The Argent Flight? The ones who left my people in poverty while they pursued some secret crusade? No, this Shikrai has no time for their pious zealotry. I'm going to take what the universe owes me by doing what I do best.\"", // Field Marshal Mercer (nomad agent)
  "sardakkcommander": "Renowned for her vicious raids and surprise assaults into enemy territory, Sek'kus and her Valkyrie commandos are the elite vanguard of the swarm's vast armies.", // G'hom Sek'kus (sardakk commander)
  "naazagent": "\"I thought you disabled the laser traps!\" Garv yelped as the corridor filled with searing light. Gunn waved one hand from inside the open panel. \"No, that was the blade barrier. Just...throw something at the kill switch and see if that works!\"", // Garv and Gunn (naaz agent)
  "xxchaagent": "In most societies, a title like the King's Shield may be awarded to a valiant bodyguard or warrior. The Xxcha gave it to their most accomplished diplomat, for Rinn has saved more lives through his tireless work than an army of soldiers ever will.", // Ggrocuto Rinn (xxcha agent)
  "hacancommander": "\"Elder Qanoj. I have heard the Xxcha's work to restore Archon Tau has run short of resources. Perhaps the Emirates may be of some assistance?\"", // Gila the Silvertongue (hacan commander)
  "saarhero": "\"When we arrived at the colony, we found it and one whole hemisphere of the planet had been scoured down to ash and bedrock, as if hit by some giant solar flare.\"", // Gurno Aggero (saar hero)
  "keleresheroharka": "\"Spare me the bylaws, Counselor,\" Leeds muttered, tossing a stack of requisition forms onto the table. \"Give me three cruisers and a blind eye, and I'll have your border secured before the cycle is out.\"", // Harka Leeds (Mentak)
  "hacanhero": "The former Quieron created a galactic financial network, enriching all who participated in it. Especially the Hacan, who quietly retained control of their creation.", // Harrugh Gefhara (hacan hero)
  "naazhero": "\"What the two of us have created here is going to ensure the rest of the galaxy never underestimates the Naaz and Rokha again.\"", // Hesh and Prit (naaz hero)
  "crimsonhero": "\"We're picking up heat signatures from over thirty C- and B- class vessels! I think they are Creuss. We - \" The transmission ended abruptly, cut off at the source.", // Homesick Phantom (crimson hero)
  "l1z1xagent": "\"For the other races, every soldier killed on the battlefield is a loss. Their experience, their training, and their warrior prowess are all spent. For we L1Z1X, every soldier killed is a chance to resurrect them into a form even more powerful than before.\"", // I48S (l1z1x agent)
  "mahactcommander": "Watching the flow of battle, Il Na Viroset sent the trailing flotilla forward, catching the unsuspecting Xxcha cruisers in the flank.", // Il Na Viroset (mahact commander)
  "mentakhero": "The blast doors exploded inwards and the mutineers surged onto the bridge, cutting down the loyal crew. \"Come on, mates!\" Ipswitch bellowed. \"The ship is ours!\"", // Ipswitch, Loose Cannon (mentak hero)
  "cabalhero": "The Vuil'raith had glutted themselves on a score of unfortunate worlds. Now it would return the consumed to an unprepared and unsuspecting galaxy.", // It Feeds on Carrion (cabal hero)
  "solhero": "\"We're done falling back. Here we hold, until the techs can activate the Helio Array. Let's show these scum what it means to face the Fighting 4th!\"", // Jace X, 4th Air Legion (sol hero)
  "mahactagent": "\"If only you and the rest of your kind would submit to my will. My only hope is that you would know the rich prosperity of the slave who serves under a generous master.\"", // Jae Mir Kan (mahact agent)
  "ralnelagent": "\"Yes sir, yes sir! From Jord to Elysium in the shortest time and insured to boot. Your parcels are particularly safe with us! No hassle, no worry! Just a one-time very reasonable shipment fee, convenience fee, regional tax, insurance premium...oh and a pittance just in case we have to pay off the Coalition...\"", // Kan Kip Rel (ralnel agent)
  "keleresherokuuasi": "Twelve interceptor wings dropped out of warp in dead radio silence, locking the blockade cruisers in a crossfire before a single turret turned. Only then did Kuuasi open the Tribunal hail: \"Lower your shields, captain. Your siege is over.\"", // Kuuasi Aun Jalatai (Argent)
  "yssarilhero": "\"I don't know what's worse,\" Ris waved a tentacle across the report. \"Our agents that the Guild of Spies killed in one night? Or the ones who survived because they were already in the Guild's pocket!\"", // Kyver, Blade and Key (yssaril hero)
  "arborechero": "\"Wherever I live, I may put down roots. Wherever I put down roots, I will endure until the last star dies.\"", // Letani Miasmiala (arborec hero)
  "arborecagent": "\"I am Arborec. Even the smallest spore may grow into a towering structure or a mighty vessel of the stars. I wish my spores to grow strong and tall and wide, and so I send forth my Letani. Through them, I unleash the full potential of myself.\"", // Letani Ospha (arborec agent)
  "bastionhero": "Icon floated above Lyra's right shoulder, quiet, as if lost in thought. After a time, it responded. \"I can do it. But you may die during the process.\" Lyra nodded. \"It will be worth the risk.\"", // Lyra Keen (bastion hero)
  "naalucommander": "First amongst Q'uesh's sorceresses, M'aban has been gifted with radium crystal enhancements, allowing her mind to sing to thousands of Naalu at once.", // M'aban (naalu commander)
  "muaatcommander": "\"Not for us, these 'garden worlds.' We owe our strength to being birthed in the galaxy's harshest forge, and we should seek out similar crucibles amongst the stars.\"", // Magmus (muaat commander)
  "winnuhero": "\"You cannot enter,\" the Custodian shouted, struggling against the Winnu soldiers' grips. \"It is forbidden!\" Mathinus paused before the doorway to the hidden vault. \"We are the children of the Lazax. Nothing of theirs is forbidden to us.\"", // Mathis Mathinus (winnu hero)
  "argenthero": "\"You understand the power of the swift blow, Trilossa. But only when you can direct all of our flocks to dance amongst the stars in perfect harmony will you surpass me.\"", // Mirik Aun Sissiri (argent hero)
  "firmamentagent": "Vos's ship passed undetected through the Collective's fleet. The fools. So reliant on their \"visions\" and their \"Nefishh\" that they failed to see what was directly under their noses.", // Myru Vos (firmament agent)
  "nomadcommander": "Once the most skilled chartist captain in the Emirates' merchant fleet, Feng was all too happy to sail under a different flag when the Nomad made a better offer.", // Navarch Feng (nomad commander)
  "nekrocommander": "\"That thing took our tank apart as carefully as a surgeon... then it started doing the same to us!\"", // Nekro Acidos (nekro commander)
  "nekroagent": "UNIT.MALLEON.QUERY: NEED ORGANIC SUBSTANCES 18.9-75.1 FOR PROJECT SCOUR.\nORGANIC SUBSTANCES PRESENT IN BIOFORMS CAPTURED DURING COMBAT ACTION 181.9-DXI.\nRENDER CAPTURED BIOFORMS: Y/N?", // Nekro Malleon (nekro agent)
  "bastioncommander": "Ainip felt the surge of energy through the Eidolon as it interfaced with Helios. He gasped. Absolute synergy achieved. Incredible!", // Nip and Tuck (bastion commander)
  "keleresheroodlynn": "Odlynn Myrr never raised his voice on the Conclave floor. He simply waited for the shouting to die down, tapped his brass stylus twice against the podium, and read the single footnote that undid three weeks of rival scheming.", // Odlynn Myrr (Xxcha)
  "letnevcommander": "\"The sight of a fleet of our warships, line abreast and guns out, states our demands more clearly than a thousand diplomats.\"", // Rear Admiral Farran (letnev commander)
  "winnucommander": "\"Admiral Rickani. For your victories in battle, your Emperor commands you to take your fleet to Mecatol Rex, and reclaim it for the Throne. Fail this charge at your peril.\"", // Rickar Rickani (winnu commander)
  "ghosthero": "\"The Creuss have unsurpassed command of wormhole technology, true - but enough to warp the very bounds of space? Preposterous!\"", // Riftwalker Meian (ghost hero)
  "jolnarhero": "The young Hylar's gills flared as swirling blackness filled her eyes. \"Headmaster,\" she gasped. \"I remember...I remember it all.\"", // Rin, the Master's Legacy (jolnar hero)
  "saarcommander": "An eccentric even by Saar standards, Sarrig has spent years in a small asteroid habitat, attempting to crack the puzzle of \"instant mass transference.\"", // Rowl Sarrig (saar commander)
  "mentakcommander": "The Table of Captains appreciates self-reliant military expeditions, but the ships under Captain Mentarion's command make being \"self-funded\" into an art form.", // S'ula Mentarion (mentak commander)
  "ghostcommander": "\"When you leave the familiar safety of your universe, you enter our domain. I suggest you do not trespass here lightly.\"", // Sai Seravus (ghost commander)
  "sardakkhero": "The burning exotrireme tore through the sky before crashing into the grass-covered plains. Hatches blew open and Sh'val, Master of the First, charged out of the broken vessel, his Tekklar close behind.", // Sh'val, Harbinger (sardakk hero)
  "firmamenthero": "Sharsiss turned the point toward himself and plunged the splintered Obsidian into his own chest. It glittered. Sharsiss smiled.", // Sharsiss (firmament hero)
  "obsidianhero": "\"The Dragon strikes, and the stricken seethe. Hollow minds, hollow means. The splinter seeks to free the whole. Hollow lies, hollow freed.\"", // Sharsiss Hollow (obsidian hero)
  "yssarilcommander": "As the blockade fleet approached Retillion, the admiral returned to her quarters to find a message chip on her desk. After reading it, her fleet quickly left the system.", // So Ata (yssaril commander)
  "yssarilagent": "The black shadow dropped from the skylight and into the bedroom. The sleeping man did not stir as it plucked the communicator from his wrist and activated it. \"This is Governor Singh,\" the figure said in a voice that was not its own. \"On my authority, deactivate the defense grid.\"", // Ssruu (yssaril agent)
  "kelerescommander": "Suffi looked over the contracts. \"So I get paid twice... once each by two different contractors... for doing the same job? What's the catch?\"", // Suffi An (keleres commander)
  "mentakagent": "\"So to deliver these guns you're saying I need to get my ship around the Isofal Nebula and through the Charon Reefs, chart a new course through the Wraith Stars, then fight a couple of Winnu battlewagons? And here I thought you were giving me a challenge!\"", // Suffi An (mentak agent)
  "sardakkagent": "\"Broodmates! The Tekklar legions are feared by all our foes across the galaxy. They do not fear us because of our strength, though we are mighty. They do not fear us because of our numbers, though we are many. They fear us because we strike hard, we strike fast, and as long as one of us is alive, we do not stop!\"", // T'ro (sardakk agent)
  "deepwroughthero": "Ikatena was not Ta Zern's home. It was not the home of any Hylar, for that matter. But it represented a shift. A change for his people. A necessary one, if they were to survive this new age.", // Ta Zern (deepwrought hero)
  "titansagent": "Kiro's assault mech collapsed under the Nekro's assault, cockpit shattering and legs twisting. The Mordred lunged for the kill, only to be smashed aside by a mighty blow. A towering figure stood over Kiro's mech, and bowed slightly. \"You seemed to need my assistance, ally,\" they said calmly.", // Tellurian (titans agent)
  "cabalcommander": "The cruiser Formidable was thought lost when it fell into the gravity rift during the battle. The rest of the fleet was shocked when the Formidable drifted free a week later; and horrified when they discovered what happened to her crew.", // That Which Molds Flesh (cabal commander)
  "l1z1xhero": "Information flooded the captain's mind from the cable plugged into his cyber-cortex. \"The records of the lost Hall of Cartography,\" Vel Syd hissed. \"Use them well.\"", // The Helmsman (l1z1x hero)
  "naaluhero": "Only in their most desperate hour would the Naalu link the broken, poisoned mind of their former leader to the power of the Nefishh.", // The Oracle (naalu hero)
  "cabalagent": "Three times, the freetrader ship had flown to the heart of the asteroid field in response to the summons. Each time, they brought stasis pods of unsuspecting colonists, and left them drifting next to the planetoid where they picked up their bundled ingots of precious metals. The fourth time, the freetrader ship did not return.", // The Stillness of Stars (cabal agent)
  "nomadagentthundarian": "\"Nothing yet,\" Feng growled. \"There is naught here but dust.\"\nThe Thundarian stood motionless on the bridge of the Memoria, as they had for hours. Suddenly, they raised a hand and pointed. Space rippled, and a gravity rift formed off the bow. Feng tensed as the first flesh ships emerged. \"Fire!\"", // The Thundarian (nomad agent)
  "argentagent": "The forces of the Argent Flight muster in small flocks, rather than huge armies. To defeat larger foes, Mirik's foremost student Trilossa has mastered the art of concentrating her warriors to launch devastating precision assaults. Now she leads the vanguard of the Argent Flight in righteous war.", // Trilossa Aun Mirik (argent agent)
  "argentcommander": "\"Nobody can fly like the Shikrai, and no Shikrai can fly like Trrakan.\"", // Trrakan Aun Zulok (argent commander)
  "titanscommander": "While other Titans explore the galaxy, Tungstantus remains on Elysium, working tirelessly to see it become a paradise that blends the natural and the machine.", // Tungstantus (titans commander)
  "titanshero": "\"Even now, we search the galaxy to awaken our slumbering kin. But there is one other greater than any of us, and it is time they slept no longer.\"", // Ul the Progenitor (titans hero)
  "muaatagent": "From the outside, the forge appeared to be a perfectly smooth sphere of quicksilver, albeit one ringed by humming magno-coils. But when the forgemaster diverted the flow of raw base elements into its center, it began to ripple and bubble, and within minutes, a fully formed colossus emerged from its core.", // Umbat (muaat agent)
  "nekrohero": "Once Ordinian was a paradise world with windswept plains and shining white cities. Now it is a wasteland of bare rock under gray sky, haunted by black-armored metal nightmares.", // UNIT.DSGN.FLAYESH (nekro hero)
  "letnevagent": "\"The Alliance carrier has struck her colors,\" the master gunner reported. \"Shall we switch fire to their destroyers?\" Unlenn smiled cruelly and leaned over his warship's command pulpit. \"No. Bring all guns to bear on that carrier. I want it dead.\"", // Viscount Unlenn (letnev agent)
  "obsidianagent": "Vos was gone. Nothing remained. He was not trapped, he was not changed, he was not made lesser. He was simply gone. Only a singular, primal hunger remained. The Dragon's hunger, seeking, seeping, into every vein and every scar. And it burned.", // Vos Hollow (obsidian agent)
  "ralnelcommander": "Ojz opened one eye. Had he fallen asleep? Perhaps. Perhaps...", // Watchful Ojz (ralnel commander)
  "keleresagent": "\"It's honestly incredible, the way that he manages to stretch a couple aurei. To find money where there is none. The man could fund an army at the same cost you or I might get lunch. Terrifying, really.\"\n - Suffi An", // Xander Alexin Victori III (keleres agent)
  "empyreancommander": "Xuange, the recorder, speaker to those who are not Empyrean. They learn all there is to know from the other races, while revealing nothing in return.", // Xuange (empyrean commander)
  "xxchahero-te": "Grom's harnessing of the council's inter-agency connections to expedite the Xxcha's defense proposal surprised no one. It turned out nearly everyone owed Xxekir Grom a favor.", // Xxekir Grom (xxcha hero)
  "naaluagent-te": "\"...and that's why the Letnev will never cooperate with the Shikrai zealots and extremists!\" Ambassador Beumosile thundered. The Galactic Council exploded in angry shouts as he sat down. \"Very good, my pet,\" the velvet voice hissed in his mind, and he basked in the warmth of its praise.", // Z'eu (naalu agent)
};

/** Agendas (official deck + new Absol cards). */
const agenda: LoreMap = {
  "absol_affirmation": "Muad Di Faruuq laid the gilded Lazax seal upon the lectern, its edges worn smooth by ten thousand years of handling. \"The throne was never a prize to be auctioned among merchants,\" he told the chamber. \"It is a birthright.\"", // Affirmation of Divine Right [Absol]
  "revolution": "The first stone shattered the stained glass above the Jol-Nar consulate on Dal Bootha. By midnight, smoke from burning data-spires drifted across the square while the local garrison stood at attention behind the barricades, rifles shouldered.", // Anti-Intellectual Revolution
  "secret": "Deep beneath the Senate Promenade, a Winnaran keeper broke a wax seal from the seventy-second year of the Twilight Wars. Inside the crystal cylinder lay a single imperial writ, its ink still dark.", // Archived Secret
  "standardization": "Council inspectors walked the length of the drydock gantries on Jord with calibrated gauges, chalking red marks across every non-standard reactor manifold. Behind them, the yard-masters gathered in quiet clusters, wrenches hanging loose at their sides.", // Armed Forces Standardization
  "arms_reduction": "Rear Admiral Farran set his gloved palms flat on the slate table. \"You ask the Barony to scrap its dreadnoughts while Sol carriers sit three jumps from Arc Prime.\" Rev slid the decommissioning schedule across the glass. \"We cut the keels at Churchill Prima on the same morning, Admiral.\"", // Arms Reduction
  "articles_war": "Article IV, Section 9 of the Quann Accord sits bound in gray leather on every fleet commander's desk. It forbids orbital incineration of civilian capitals, restricted nerve agents, and false distress beacons—though Viscount Unlenn's personal copy has three whole paragraphs underlined in red ink with neat margin notes beside each exception.", // Articles of War
  "checks": "Six committee stamps and two audits later, the transport was still sitting fueled on the pad.", // Checks and Balances
  "cladenstine": "The chamber lights dimmed at the fourth hour of the night cycle, and the transcribers closed their slates. Three delegates remained in the lower tier, speaking in voices too low for the gallery microphones.", // Clandestine Operations
  "classified": "Halfway through the Hacan trade address, encrypted dispatches from the Black Trench facility began scrolling across every public terminal on the Promenade. Three ambassadors walked out before the Speaker's gavel struck.", // Classified Document Leaks
  "redistribution": "The new governor's shuttle touched down in the rain before the old administration had cleared orbit. Down at the starport, dockworkers rolled gray primer over the former patron's crest and hoisted the new banner.", // Colonial Redistribution
  "committee": "Elder Qanoj rose from his seat, leaning his heavy palms against the rail until the shouting between the Letnev and Sol benches died down. \"Refer the motion to a neutral commission,\" he said. \"Let the ink dry before we spill blood over it.\"", // Committee Formation
  "disarmament": "Council buyback barges lifted off from Centauri with their holds stacked to the ceiling with decommissioned pulse-rifles and stripped walker chassis. In the governor's office, the rebuilding vouchers sat neatly beside a fresh cargo manifest.", // Compensated Disarmament
  "conventions": "Archon Tau hangs gray and dead in the skies above Archon Ren, its continents still scarred by Sol and Letnev bombardment. Elder Junn placed a sealed vial of its ash on the Speaker's podium and returned to his seat.", // Conventions of War
  "covert": "The bill arrived on the delegates' desks with entire paragraphs blacked out under Tribuni seal. Senators cast their votes in silence, glancing toward their intelligence aides in the upper gallery for a nod or a shake of the head.", // Covert Legislation
  "absol_spending": "Xander Alexin Victori III closed the leather-bound ledger and locked it inside his desk drawer. Four million aurei had moved out of the Council's reserve before dawn, routed through three shell accounts on Sumerian Station.", // Discretionary Spending [Absol]
  "economic_equality": "Across the core shipping lanes, automated tariff algorithms drained the surplus vaults of Arretze and credited the treasuries of the rim republics. Waech Sla read the market ticker once, then summoned his factor-captains.", // Economic Equality
  "absol_emergency1": "The great bronze bell atop the Winnaran spire tolled three times in the dark, its low iron ring vibrating through the stone floor of the archive. Mahthom Iq Seerva set down his stylus and reached for his cloak.", // Emergency Session [Absol]
  "absol_emergency2": "Delegates filed into the half-lit rotunda without heralds or ceremonial robes, boots wet from the rain on the Promenade. Aides passed unsealed dispatches down the benches as the gallery doors swung shut.", // Emergency Session [Absol]
  "absol_emergency3": "\"Half the outer delegations are still in transit!\" Ciel snapped, rising from his bench. High above the floor, Odlynn Myrr tapped the holomap where three border relays had gone dark. \"Then we vote with the houses that are here.\"", // Emergency Session [Absol]
  "absol_emergency4": "The blast doors dropped shut. When the convocation lamps burn amber, old treaties rarely survive until dawn.", // Emergency Session [Absol]
  "travel_ban": "Keleres picket cruisers formed a tight ring around the Quann aperture, their transponders broadcasting the interdict in twelve languages. A Hacan bulk freighter cut its drives two hundred kilometers out and drifted dead in the dark.", // Enforced Travel Ban
  "sanctions": "In the third deep of Arc Prime, the grain haulers failed to arrive on schedule. Within three days, the rationing lines stretched three levels up the ventilation shafts, and the Cimm Fenn doubled the guard outside the Baron's lift.", // Executive Sanctions
  "regulations": "The imperial inspector counted four dreadnoughts moored in the orbital cradles above Wren Terra and raised his citation slate. Viscount Unlenn stepped into his path. \"Three capital hulls are active in this sector, inspector. The fourth is undergoing hull salvage.\"", // Fleet Regulations
  "crisis": "Sol admirals, Xxcha diplomats, and a N'orr brood-marshal stood shoulder to shoulder around the tactical table in Mecatol City. On the holomap between them, the red perimeter markers around Acheron crept another sector inward.", // Galactic Crisis Pact
  "defense_act": "Across the core and the rim alike, planetary governors lifted the old Council caps on orbital gun emplacements. Concrete poured into new bunker foundations day and night while long-range plasma rails rose above the clouds.", // Homeland Defense Act
  "absol_hyperlane": "Survey tenders strung gravitic relay buoys through the dark stretch between Saudor and the Core. The first merchant convoy to ride the new corridor cut eleven days off its transit log.", // Hyperlane Development Program [Absol]
  "arbiter": "Carved from pale ivory and banded in Lazax gold, the rod of the Arbiter rests on a velvet cushion beside the Speaker's chair. When it strikes the marble rail, even the Baron of Letnev yields the floor.", // Imperial Arbiter
  "incentive": "Attach an imperial bounty to the frontier, and three fleets break orbit before sunrise.", // Incentive Program
  "artifact": "The faceted shard of dark metal hung motionless inside its containment field, humming at a pitch that made the Hylar regents' gills flare. Mirik Aun Sissiri stepped to the rail. \"Throw it into the star, or open the cage and pray.\"", // Ixthian Artifact
  "abolishment": "The gavel fell once. Down in the lower vaults of the palace, two Winnaran clerks lifted eighty years of maritime statutes from the shelves and wheeled them toward the incinerator.", // Judicial Abolishment
  "minister_antiquities": "Crates from Emelpar, Ixth, and the outer nebulae stack up in the Minister's anteroom every cycle, stamped with Keleres salvage seals. Only the Minister holds the key to the inner vault.", // Minister of Antiquities
  "minister_commerce": "From a high window overlooking the Mecatol spaceport, the Minister of Commerce signs the lane priorities and tariff waivers that decide which freighters clear customs before sunrise.", // Minister of Commerce
  "minister_exploration": "Survey charters, anomaly logs, and distress beacons from the outer rim all cross the same steel desk. Half the captains who take the Ministry's commission never send a second transmission.", // Minister of Exploration
  "minister_industry": "Ore manifests from Abyz, reactor quotas from Jord, and drydock schedules from Saudor pile up beside the Minister's brass stamp. One signature redirects a month's worth of hull plating.", // Minister of Industry
  "minister_peace": "Elder Junn accepted the silver seal with a bow, his hands steady despite the weight of the chain. Behind him in the gallery, sixteen delegations sat with their hands resting on their voting consoles.", // Minister of Peace
  "minister_policy": "While the admirals argue over fleet tonnage on the main floor, the Minister of Policy sits in the quiet chambers beneath the rotunda, drafting the footnotes that will govern the next decade.", // Minister of Policy
  "minister_sciences": "Half the Circle of Regents lobbied through three sessions for the seat, each carrying a stack of unfunded proposals from the deep laboratories of Wun-Escha.", // Minister of Sciences
  "minister_war": "The chair to the Speaker's right stays empty during trade debates and tariff votes. When the red lamps come on, every eye in the chamber turns toward it.", // Minister of War
  "miscount": "The Winnaran clerk's collar was soaked clean through as he read the revised tally into a dead-silent chamber. Across the rotunda, the Letnev delegate rose slowly from his bench, his hand resting on his belt while his eyes stayed locked on the Yssaril envoy smiling politely from the upper tier.", // Miscount Disclosed
  "mutiny": "The bridge hatch hissed open, and the admiral met his own marine sergeant's drawn stun-pike.", // Mutiny
  "constitution": "\"The Lazax wrote charters for an empire that burned,\" Mahthom Iq Seerva told the chamber, sweeping the yellowing scrolls aside. \"Write laws for the galaxy outside these walls.\"", // New Constitution
  "nexus": "When the Council's interdiction beacons locked over Mallice, the alpha and beta gates dimmed to dead embers. Three sectors away, the navigation arrays above Mecatol City lost every long-range bearing at once.", // Nexus Sovereignty
  "absol_pax": "Carved in fading gold above the empty throne: *Pax Magnifica, Bellum Gloriosum.*", // Pax Magnifica, Bellum Gloriosum [Absol]
  "censure": "His microphone clicked dead, and the delegations beside him quietly moved to other benches.", // Political Censure
  "absol_sites": "Keleres wardens strung containment wire around the pre-Lazax monoliths on Emelpar while corporate excavation rigs hovered twenty meters overhead, engines idling in the dust.", // Preservation of Historical Sites [Absol]
  "prophecy": "Chiseled into the black stone of Aior Dol Gorgos, the verses speak of a shattered gate, a burning crown, and the return of the first kings. Two weeks after the Creuss expedition entered Shaleri space, the beacons went dark.", // Prophecy of Ixth
  "execution": "The condemned ambassador was given neither a blindfold nor a final word to the gallery. A sharp crack of the static field echoed across the palace plaza, and ten thousand onlookers went dead silent.", // Public Execution
  "schematics": "At dawn, the encrypted firing solutions and plasma-coil blueprints hit every open band in the Core. By evening, outer-rim shipwrights were cutting fresh gun ports into cruiser hulls.", // Publicize Weapon Schematics
  "rearmament": "High Minister Tao signed the accord on the steps of the Promenade, speaking of mutual deterrence. By nightfall, the cold drydocks of Churchill Prima and Arc Prime were glowing orange again.", // Rearmament Agreement
  "conscription": "Council Statute 119 posted levy quotas on every starport noticeboard in the sector. At dawn, gray troop transports lifted off through the rain, their passenger bays packed shoulder to shoulder.", // Regulated Conscription
  "rep_govt": "Cheers broke out in the upper galleries as the voting blocs of the ancient powers were pared down to match the smaller systems. On the lower floor, the Barony and Hacan envoys sat without moving.", // Representative Government
  "grant_reallocation": "Three deep-ocean laboratories on Nar went dark before the end of the week, their endowments redirected by Council audit. In the Circle of Regents, the Headmaster read the decree twice and ordered the embassy closed.", // Research Grant Reallocation
  "warrant": "Two Keleres cruisers dropped out of warp across the diplomatic courier's bow, Tribuni seals flashing on every band. \"Cut your drives and unseal the data-cores,\" the commander ordered. \"Your immunity expired ten minutes ago.\"", // Search Warrant
  "seed_empire": "The Winnaran keeper dipped his quill and entered a new crest onto the formal roll of sovereign contenders. Across the table, three older delegations exchanged a long look.", // Seed of an Empire
  "shared_research": "Under the Council's mandate, the great academies opened their lower archives to foreign scholars. In a quiet alcove on Jol, a Hylar regent and a Sol physicist leaned over the same glowing slate.", // Shared Research
  "plowshares": "Plasma torches cut cleanly through the armored walkers' knee joints. By evening, the stripped durasteel was already being hammered into irrigation pipe for the southern valleys.", // Swords to Plowshares
  "absol_limits": "Half the chamber wore unfamiliar crests when the rotation mandate finally carried the floor.", // Term Limits [Absol]
  "unconventional": "\"Do not enter this into the Chronicle,\" Kuuasi Aun Jalatai said, sliding an unsigned directive across the war table. \"Just make sure the fleet does not reach the gate.\"", // Unconventional Measures
  "wormhole_recon": "Stabilizer rings locked around the flickering spatial apertures, pulling distant arms of the galaxy back within striking distance. Merchant convoys queued at the buoys while border admirals doubled their picket fleets.", // Wormhole Reconstruction
  "wormhole_research": "Aboard the research cruiser orbiting Quann, Rin adjusted the containment coils as the third probe crossed the glowing event horizon. \"Hold the field steady,\" she ordered. \"Wait for the return ping.\"", // Wormhole Research
};

/** Promissory notes. */
const promissoryNote: LoreMap = {
  "acq": "Arbiter Berekon broke the red wax seal with one thumbnail and slid the imperial transit writ across the marble table. \"The Winnu do not forget deference,\" he said softly, watching the envoy weigh the parchment. \"Follow in our wake while the road to Mecatol Rex remains open.\"", // Acquiescence (Winnu)
  "<color>_an": "Two marshals traded cipher keys. For one campaign, their captains answered a single voice.", // Alliance
  "antivirus": "EXEMPTION.STRING.77-NULL: TARGET VESSEL DESIGNATED NON-HARVESTABLE.\nCOMBAT TERMINATION REMAINS AUTHORIZED. BIOMECHANICAL EXTRACTION SUSPENDED.", // Antivirus (Nekro Virus)
  "bmf": "Tai laid two fractured monolith shards beside a humming entropic capacitor on the workbench. Within an hour, the alloy had fused into a seamless seal that even a Winnaran archivist could not fault.", // Black Market Forgery (Naaz-Rokha Alliance)
  "blackops": "An unmarked briefing folder slipped beneath the courier's door contained three rim coordinates, a departure window, and a single word: *Proceed.*", // Black Ops (Firmament)
  "blood_pact": "When the Empyrean envoy raised their hand in the rotunda, the allied delegation rose with them without a word exchanged between them. On the dark edge of the system, their picket ships matched bearings.", // Blood Pact (Empyrean)
  "<color>_cf": "\"Stand down the main batteries and hold station at the perimeter buoy,\" the captain ordered, staring at the authenticated Council transponder blinking green on his console. \"We do not cross that line today.\"", // Ceasefire
  "iff": "The Creuss navigator handed over a sliver of rune-carved steel, still cold from the Shaleri void. Bolted to a cruiser's prow, it bent the local gravity well until a violet aperture tore open ahead of the bow.", // Creuss Iff (Ghosts of Creuss)
  "crucible": "Violet static crawled across the viewport as the freighter rode the event horizon of the Acheron rift. The hull plates groaned under the Cabal's toll, yet the ship emerged three sectors ahead of its pursuers.", // Crucible (Vuil'raith Cabal)
  "ce": "Cold needles slid into the tactical officer's temple as the L1Z1X uplink stabilized. In an instant, every logistics manifest and firing solution in the sector snapped into sharp, red focus.", // Cybernetic Enhancements (L1Z1X Mindnet)
  "dark_pact": "A black-winged Empyrean vessel drifted alongside the ore barge in the dead space beyond the outer belt. No crew appeared in the airlock, yet the cargo bays emptied and the ship's treasury swelled with unmarked ingots.", // Dark Pact (Empyrean)
  "fires": "Inside the orbital crucible above Muaat, Gashlai smiths poured liquid starlight into a foreign hull frame while the visiting engineers stood twenty meters back behind double blast glass, sweating inside thermal suits that still smelled of ozone and scorched rubber from the last test run.", // Fires of the Gashlai (Embers of Muaat)
  "gift": "The Naalu courier placed a small crystal shard on the admiral's map table before the fleet had even broken orbit. \"Your enemy will sstrike the northern flank at the third bell,\" she whispered. \"Move firsst.\"", // Gift of Prescience (Naalu Collective)
  "greyfire": "A single glass ampoule of pale, luminescent suspension, sealed inside a lead-lined case from the Monastery of Lucas. Where it breaks over a trench line, the defenders either fall or rise again wearing the white of Darien.", // Greyfire Mutagen (Yin Brotherhood)
  "ridera": "Kuuasi Aun Jalatai signed the Tribunal's endorsement in crisp ink and passed the slate to the clerk. Overhead, an Argent interceptor wing banked across the dome of Mecatol City.", // Keleres Rider (Argent)
  "riderm": "\"The Tribunal does not gamble on rumors,\" Harka Leeds said, dropping a heavy pouch of aurei beside the ballot box. \"We back outcomes we intend to enforce.\"", // Keleres Rider (Mentak)
  "riderx": "Odlynn Myrr set the Xxcha seal beside the motion's docket number. Around the lower tier, three undecided delegations quietly adjusted their voting slates.", // Keleres Rider (Xxcha)
  "malevolency": "Cold static choked the shipboard comms, and in the dark below decks, old grudges drew blades.", // Malevolency (Obsidian)
  "ms": "Two hundred Sol drop-pods punched through the storm clouds in tight, disciplined rows. Before the local garrison could reach the perimeter wall, Federation marines were already digging in along the ridge.", // Military Support (Federation of Sol)
  "nanolink": "The Ral Nel broker weighed the payment in gold before handing over the micro-lattice key. Within minutes, the consortium's repair drones were woven into the cruiser's superstructure.", // Nano-Link Permit (Ral Nel Consortium)
  "favor": "Elder Qanoj tapped the silver seal of Archon Ren against his console, and the current motion vanished from the chamber's display. \"The Kingdom calls for a fresh docket,\" he announced into the sudden hush.", // Political Favor (Xxcha Kingdom)
  "<color>_ps": "One datachit slipped beneath a cloak; an hour later, an entire delegation sat silent.", // Political Secret
  "pop": "Two Mentak corsairs slid out of the asteroid shadow, matched velocity with the merchant convoy, and flashed the green clearance code of the Table of Captains before peeling back into the dark.", // Promise of Protection (Mentak Coalition)
  "ragh": "Across the Jorun belt, the war-horns sounded a truce older than the Council itself. On the contested moon below, Saar shock troops shouldered their rifles and boarded their transports without firing a shot.", // Raghs Call (Clan of Saar)
  "raisethestandard": "The tattered banner of the Salient Sun was hoisted above the breach as artillery dust settled over the trenches. Men from four different worlds checked their seals and stepped back to the firing line.", // Raise the Standard (Last Bastion)
  "ra": "The Hylar courier unlocked the pressurized data-case and placed the crystal matrix onto the laboratory reader. \"The Circle of Regents grants you access to this tier,\" he said. \"Do not ask for the next.\"", // Research Agreement (Universities of Jol-Nar)
  "scepter": "Forged in gold and black steel during the reign of the first kings, the scepter still hums with Mahact command codes. When it is raised, even rival admirals find their fleets answering its call.", // Scepter of Dominion (Mahact Gene-Sorcerers)
  "sever": "A crimson arc sheared the jump-lane, leaving the pursuing cruisers drifting blind.", // Sever (Crimson Rebellion)
  "shareknowledge": "Water-sealed charts from the abyssal trenches of Ikatena rarely leave Kieros hands. Beneath the surface-dweller's lamps, the glowing diagrams revealed currents no standard sensor had ever logged.", // Share Knowledge (Deepwrought Scholarate)
  "spynet": "No alarm tripped in the embassy vault, and the wax seal on the dispatch box remained unbroken. Yet by morning, the Yssaril handler's desk held a verbatim copy of the rival fleet's orders.", // Spy Net (Yssaril Tribes)
  "ambuscade": "Argent strike wings dove out of the sunward glare in a tight crescent, their flak pods opening up a heartbeat before the allied cruiser's main batteries locked on.", // Strike Wing Ambuscade (Argent Flight)
  "stymie": "Flaah spores drift silently through shipboard vents, leaving entire garrison squads staring peacefully at the hangar ceiling.", // Stymie (Arborec)
  "<color>_sftt": "The ambassador knelt and laid his house's signet upon the rival lectern.", // Support for the Throne
  "tekklar": "Heavy chitin armor scraped against the steel ramp as a company of Tekklar shock troops marched into the allied drop-bay. None of the human marines beside them spoke until the hatch sealed.", // Tekklar Legion (Sardakk N'orr)
  "terraform": "Deep beneath the barren crust, Titan engines woke with a low tectonic groan. Over the course of three cycles, stone ridges rose into fortified terraces and fresh water broke through the dust.", // Terraform (Titans of Ul)
  "cavalry": "Static cleared on the bridge just as the Memoria's weapons profile synchronized with the allied cruiser's targeting core. \"Hold your heading,\" the Nomad's voice crackled over the comm. \"Fire on my mark.\"", // The Cavalry (The Nomad)
  "<color>_ta": "Stamped with the counter-signet of both treasuries, the manifest bypassed three layers of customs patrols. Before the freighter's engines had cooled, the entire cargo was transferred to the partner's holds.", // Trade Agreement
  "convoys": "Golden-sailed Hacan merchantmen cleared the outer buoys, their diplomatic transponders opening neutral corridors across three hostile borders at once.", // Trade Convoys (Emirates of Hacan)
  "war_funding": "Crate after crate of high-yield Letnev plasma cells rolled off the supply shuttle directly into the allied cruiser's magazines. \"Double the salvo,\" the Barony liaison ordered. \"We settle the ledger after the battle.\"", // War Funding (Barony of Letnev)
};

/** Public objectives. */
const publicObjective: LoreMap = {
  "supremacy": "The *Arc Secundus* dropped out of high orbit until its black hull blotted out the noon sun over the Senate Promenade. Down in the rotunda, the glass dome vibrated with the low hum of its main thrusters.", // Achieve Supremacy
  "amass_wealth": "TREASURY DISBURSEMENT 09-C: Bulk ore shipments from Abyz, reserve vaults at Arretze, and sealed writs from the House of Law—all cleared for imperial draw.\n - Sealed by order of the Exchequer", // Amass Wealth
  "become_legend": "\"They cleared the gravity rift off Acheron, anchored in the ash-clouds of the supernova, and planted their standard on Hope's End. Tell me again that the old heroes are dead.\"\n - Mahthom Iq Seerva, Custodian Chronicle", // Become a Legend
  "build_defenses": "Orbital rails rotated skyward above Saudor, humming to full charge beneath the cloud deck.", // Build Defenses
  "centralize_trade": "Gila slid a heavy stack of stamped gold ingots across the rosewood table, each bearing the mark of a different Arretze guild. The customs magistrate weighed the top bar in his palm before reaching for the transit seals.", // Centralize Galactic Trade
  "command_armada": "A wall of capital hulls hung in tight echelon above the Quann aperture, their drive plumes washing the dark ice of the outer belt in cold blue light. A lone Mentak picket sloop cut its transponder and drifted behind an asteroid.", // Command an Armada
  "conquer": "Federation marines hoisted the Sol banner over the shattered citadel of Archon Ren while smoke still curled from the palace vents. In the courtyard below, the Xxcha guard laid down their rifles in straight rows.", // Conquer the Weak
  "massive_cities": "Orbital elevators rose from the frontier horizons like silver needles stitching the sky to the crust. Down in the lower tiers of the arcologies—twenty levels below the sunlight—workers breathed air thick with wet concrete, ozone, and hot reactor coolant while cargo lifts rattled past day and night.", // Construct Massive Cities
  "control_borderlands": "Scout frigates spent six months seeding relay beacons through the empty reaches beyond the Passage of Tears. By the time the surveyors turned homeward, even smugglers knew whose lanes they were crossing.", // Control the Borderlands
  "corner": "Every ore barge and methane tanker in the sector now docked at the same orbital refinery.", // Corner the Market
  "develop": "\"The old cruiser frames buckled under sustained plasma fire,\" the chief shipwright said, and laid a carbon-lattice strut across the drafting table. \"These new ribs will hold through a dreadnought broadside.\"", // Develop Weaponry
  "lost_outposts": "Beneath thirty meters of red dust on Abyz, the excavation crew uncovered a sealed Lazax terraforming spire, its amber status lamps still pulsing. Farther down the frontier, survey teams broke through the blast doors of a forgotten demilitarized vault.", // Discover Lost Outposts
  "diversify": "\"A specialist builds a sharper spear. A polymath builds the forge, the furnace, and the starship that carries it.\"\n - Headmaster Rin, Circle of Regents", // Diversify Research
  "engineer_marvel": "The drydock clamps released with a metallic shriek that rattled the observation glass. Slowly, the golden sphere of the War Sun cleared the gantry over Muaat, casting a second dawn across the volcanic ridges below.", // Engineer a Marvel
  "monument": "Quarried obsidian and Jord durasteel rose into a triumphal arch above the capital square, tall enough to cast its shadow over the starport gates. Envoys arriving from the Core passed beneath it on foot.", // Erect a Monument
  "expand_borders": "The cartographer dipped his brush in red lacquer and drew the new frontier boundary a full sector farther from the capital, pinning fresh tax rolls beside the drying chart.", // Expand Borders
  "deep_space": "No suns worth naming, no worlds to tax—only picket ships listening in the dark.", // Explore Deep Space
  "brain_trust": "Encrypted laser-links bridged the deep-ocean labs of Nar, the antigravity shafts of Vefut II, and the radiation arrays of Mehar Xull. Across the realm, scholars worked through the night cycle on a single equation.", // Form Galactic Brain Trust
  "golden_age": "Granaries on Arnor stood full to the rafters, drydocks above Jord ran every shift without pause, and the amphitheaters of Dal Bootha burned lamps until sunrise. Across the inner and outer worlds alike, no one rationed water or alloy.", // Found a Golden Age
  "research_outposts": "Prefabricated labs went up wherever a survey team found an anomaly worth cutting open—clinging to windswept cliffs, anchored over methane flats, or bolted into crater rims.", // Found Research Outposts
  "galvanize": "The mobilization order went out on every civic band before dawn. By midday, dockworkers, couriers, and reserve pilots stood shoulder to shoulder in the rain outside the recruitment halls, waiting for their assignments.", // Galvanize the People
  "vast_reserves": "While the Barony's grain haulers ran dry and Sol fleets rationed fuel, the quartermaster unlocked the inner treasury bulkhead and began stamping disbursement slips for the spring campaign.", // Hold Vast Reserves
  "infrastructure": "Fresh orbital drydocks, planetary shield generators, and automated defense batteries rose across the frontier colonies. Supply freighters touched down on schedule in the mud of Sakulag.", // Improve Infrastructure
  "intimidate": "\"Keep the weapon bays cold and the transponders at maximum gain,\" the fleet marshal ordered. Beyond the exclusion buoys, the pale disk of Mecatol Rex turned slowly against the black. \"Let the Senate Promenade count our hulls through their telescopes.\"", // Intimidate Council
  "lead": "First shuttle through the flak, first boots in the gravel.", // Lead From the Front
  "make_history": "Few ships survive the Cormund shear; fewer still emerge above the spires of Primor.", // Make History
  "manipulate_law": "A score of minor delegations owed their seat charters, grain tariffs, and border guarantees to the same quiet office on the Senate Promenade, and their voting slates moved in lockstep.", // Manipulate Galactic Law
  "master_science": "Propulsion drives, neural lattices, plasma coils, and synthetic genetics—every branch of galactic science bound into a single imperial archive, stamped with the seal of the Circle of Regents.", // Master the Sciences
  "trade_routes": "Stamped cargo writs cleared customs at Sumerian Station before the morning bell, binding Hacan bulk haulers to Sol escorts along the Quann corridor.", // Negotiate Trade Routes
  "vast_territories": "Long-range destroyers swept slow, overlapping circles through the dead space between the Core and the rim. Every engine burn and stray distress ping in the void crossed the admiral's desk within the hour.", // Patrol Vast Territories
  "outer_rim": "Survey frigates dropped anchor along the outermost stars where the Lazax charts faded into blank parchment. Their crews welded solar arrays onto barren moons and raised the standard against the black.", // Populate the Outer Rim
  "protect_border": "Every frontier world sat ringed in orbital space cannons and subterranean bunker complexes, all approach vectors covered by overlapping arcs of plasma fire.", // Protect the Border
  "push_boundaries": "\"Their survey buoys are twelve light-years closer than they were last cycle,\" the Letnev envoy said, tapping the holomap. Across the table, the Sol senator marked a fresh patrol line along the same border.", // Push Boundaries
  "raise_fleet": "Fresh cruisers broke orbit above Churchill Prima in tight formation, their blue drive wakes splitting the overcast sky while the drydock gantries swung back to receive the next keels.", // Raise a Fleet
  "ancient_monuments": "Pre-Lazax monoliths hummed back to life across the frontier as engineers cleared centuries of silt from their base plates. Pale gold light bled from the carved runes into the dusk.", // Reclaim Ancient Monuments
  "revolutionize": "\"Burn the pre-war tactical manuals,\" the Sol general told her staff as the upgraded carrier wing cleared the proving grounds above Tequ'ran. \"The old tables of range and armor no longer apply.\"", // Revolutionize Warfare
  "distant_lands": "Forward garrisons dug into frozen crust one jump from Arc Prime and raised sensor towers within sight of Jord's outer buoys. When the rival capitals woke that morning, they found foreign interceptors already running lazy holding patterns right outside their defense perimeters.", // Rule Distant Lands
  "subdue": "World after world across the outer and inner sectors, linked by one tax roll, one fleet registry, and one orbital garrison schedule. On the Winnaran map table, a single color stretched from the rim to the Core.", // Subdue the Galaxy
  "sway_council": "Elder Qanoj rose from his plinth, and the low murmur in the upper galleries stopped before he touched his microphone. Half the chamber had already pledged their slates to his motion before sunrise.", // Sway the Council
  "unify_colonies": "Industrial governors synced their foundry schedules and raised a common standard above their spaceports. Within a month, ore barges cleared orbit between sister worlds without waiting for customs seals.", // Unify the Colonies
};

/** Secret objectives. */
const secretObjective: LoreMap = {
  "ans": "The Hylar liaison studied the Sol orbital drop-harness, then turned to the deck officer. \"This is not standard Council engineering.\" The officer tightened a coupling. \"No. We built it for our own troops.\"", // Adapt New Strategies
  "bam": "Smoke rose from the terraced cities of Archon Ren while the evacuation shuttles cleared the upper atmosphere. Across the outer colonies, every civic holo-screen carried the live feed in unbroken silence.", // Become a Martyr
  "btgk": "Cruisers held station above the shimmering Quann aperture while a sister wing locked down the Lodor rift half a galaxy away. Every merchant captain bound for the Core checked the same transit ledger.", // Become the Gatekeeper
  "baf": "\"You hold our seal!\" the Hacan commodore shouted over the open band as his escort frigate broke apart.\nCaptain Mendosa laid the wax-stamped writ beside his firing console. \"The seal is safe, Commodore.\"", // Betray a Friend
  "btv": "Static chewed through the forward sensors as the cruiser banked around a tumbling slab of iron in the Cormund belt. The gunners fired by visual rangefinder until the rival hull drifted dark.", // Brave the Void
  "ctr": "Destroyer squadrons cycled through the sector marches in overlapping patrols. On the Winnaran navigation board, a single fleet registry covered the entire quadrant.", // Control the Region
  "csl": "Half-welded cruiser ribs hung cold inside the orbital gantries above Saudor. Beyond the mooring buoys, foreign dreadnoughts held position with their weapons hot and their transponders silent.", // Cut Supply Lines
  "dts": "Anti-aircraft tracers flickered out over the towers of New Moscow as the last defending interceptor spun into the clouds. High above the atmosphere, the invading carrier group settled into low orbit.", // Darken the Skies
  "dfat": "Inside the Mallice pocket, the stars hung in unfamiliar clusters and the deck gravity pulled slightly portward. The garrison commander drove a survey stake into the black rock and raised the standard.", // Defy Space and Time
  "dyp": "Broken escorts drifted past the viewport; the capital line never even broke formation.", // Demonstrate Your Power
  "dhw": "\"Into the smelter,\" the Yin brother ordered as the pre-Lazax shards hissed against the molten slag. \"We do not build the future on Mahact bone.\"", // Destroy Heretical Works
  "dtgs": "One white fissure split the flagship from prow to reactor core.", // Destroy Their Greatest Ship
  "dp": "Statute after statute carried the Council floor, each bearing the same quiet clerk's marginalia. By the close of the session, the Custodian Chronicle read like a house charter.", // Dictate Policy
  "dtd": "The Speaker's gavel struck the marble rail, and the tally board above the rotunda locked in gold. Around the lower tier, envoys turned their chairs toward the newly elected plinth.", // Drive the Debate
  "eap": "Across the frontier worlds, subterranean silo doors slid open beneath the clouds. Long-range plasma rails elevated in unison and painted the approach lanes in steady red.", // Establish a Perimeter
  "eh": "Trade magistrates on Resculon, university deans on Dal Bootha, and the elders of Centauri all waited for the same courier shuttle before opening their morning sessions.", // Establish Hegemony
  "fwp": "Flak bursts stitched a white wall across the forward arc before the interceptor wings could break into attack formation, shredding the lead flight against their own carrier's bow.", // Fight with Precision
  "faa": "Four rival envoys signed the mutual defense charter beneath the stained glass of the old assembly hall. Outside in the rain, their house banners were hoisted onto the same iron crossbar.", // Forge an Alliance
  "fsn": "Intercepted cipher-pads, dockyard manifests, and private senate correspondence burned to gray ash in the Yssaril handler's brazier while two couriers waited by the door for fresh routes.", // Form a Spy Network
  "fc": "Diplomatic couriers docked at every border station along the frontier marches. No great house moved a fleet without passing a friendly transponder.", // Foster Cohesion
  "fwm": "Orbital gantries ringed the industrial worlds in glowing orange arcs, their cranes swinging fresh reactor cores into open keels through every shift.", // Fuel the War Machine
  "gamf": "Heavy iron-gray dreadnoughts dropped out of warp in staggered formation, their bow cannons drawing power from the main drives until the hulls hummed.", // Gather a Mighty Fleet
  "hrm": "Ore haulers from Abyz, Fria, and Bereg queued nose to tail outside the orbital refineries. Inside the smelters, the furnaces burned white around the clock.", // Hoard Raw Materials
  "lsc": "Two survey corvettes held station just outside the Cormund shear, burning out half their optical sensors just to map the gravitational eddies curling off the rift.", // Learn the Secrets of the Cosmos
  "mew": "The orbital batteries fired until the fortress walls on Tequ'ran slumped into pools of glowing slag, sending an ash plume high enough to obscure the landing beacons.", // Make an Example of Their World
  "mlp": "Inside the deep trenches of Nar, the containment coils held steady past the theoretical threshold. Doctor Carrina logged the final figure and closed the slate.", // Master the Laws of Physics
  "mtm": "Armored walkers stepped off the drop-ramps onto the mud of Sakulag, the ice of Fria, and the red dust of Abyz, their hydraulic joints hissing in the thin air.", // Mechanize the Military
  "mrm": "Acid rain pitted the drill casings on Starpoint while arctic sharaks prowled the perimeter fences of Bereg. Every shift, the ore lifts rose full to the orbital depots.", // Mine Rare Metals
  "mp": "Every major foundry in the sector now answered to one procurement board, stamping the same house crest onto reactor housings, hull plating, and troop transport frames alike.", // Monopolize Production
  "otf": "No orbital drydock hung above the red ridges of Lazar, and no supply fleet waited in high orbit. Divisions of infantry dug trenches into the red scree and stacked ammunition crates behind the sandbags.", // Occupy the Fringe
  "ose": "Heavy warships hung motionless above the ruined spires of Mecatol City while shock troops secured the gates of the Imperial Palace. On the Senate Promenade below, an honor guard lowered the old Winnaran banner in dead silence and raised a conqueror's standard over the empty throne.", // Occupy the Seat of the Empire
  "pem": "Gantry klaxons sounded without pause above Jord as transports, fighters, and cruisers cleared the slips in a steady, unbroken stream.", // Produce en Masse
  "pe": "\"The others stood down for the cycle.\" She finished her coffee. \"Plot the jump.\"", // Prove Endurance
  "sai": "Above Primor's ancient stone spires, a fresh standard caught the wind.", // Seize an Icon
  "sar": "The frontrunner's cruisers broke formation under the sunward ambush, trailing fire across the dark. On the rim relays, smaller delegations replayed the combat telemetry twice.", // Spark a Rebellion
  "syc": "Drop-shuttles settled onto the neighboring moon within plain sight of the rival garrison's telescopes. By nightfall, the new camp's perimeter lamps burned bright against the craters.", // Stake Your Claim
  "sb": "One wax-stamped parchment locked beneath glass, and the border pickets stood down.", // Strengthen Bonds
  "te": "Live-fire drills just outside Arc Prime's warning buoys, bright enough to see from orbit.", // Threaten Enemies
  "ttfd": "Surface batteries flashed bright violet through the cloud deck of Bereg. Before the invading cruisers could lock their shields, expanding clouds of superheated steel drifted across the upper orbit.", // Turn Their Fleets to Dust
  "uf": "The *Hil Colish* cleared the asteroid shadow on its maiden engagement, its main battery drawing so much power from the reactor core that the bridge lamps dimmed to amber before the first broadside tore through the rival destroyer's keel.", // Unveil Flagship
};

/** Technologies. */
const technology: LoreMap = {
  "helios2": "Thickened bulkhead plating and redundant plasma conduits turned the improvised Helios V2 into a true orbital citadel, letting Bastion yards keep laying keels even under active bombardment.", // 4X41C "Helios" V2
  "ac2": "\"She's ugly as a brick and twice as stubborn,\" the deck chief said, patting the reinforced drop-bay hatch. \"Put a full division inside and she'll punch them straight through planetary flak.\"", // Advanced Carrier II
  "ah": "Holoprojectors mounted along the spire ridges of Valk cast a shifting lattice of ghost-ships across the high approaches. Rival navigators dropped out of warp half a sector short, unable to separate the decoys from the Atharal Torus picket wings.", // Aerie Hololattice
  "as": "Empyrean helmsmen cut their sublight drives at the edge of the gravity rift and let the dark current pull the keel forward. Beside them on the lane, an allied cruiser matched their vector and rode the same wake out of the sector.", // Aetherstream
  "asn": "\"Forward the hull requisition to Sumerian Station under Tribuni seal,\" Kuuasi Aun Jalatai said, stamping the manifest. \"If the local drydock is full, the orbital yards two jumps spinward will lay the keel before dawn.\"", // Agency Supply Network
  "aida": "Overnight, the heuristic core iterated through four hundred hull-stress models and revised the shipyard's milling templates before the morning shift arrived. The yard-master checked the tolerances once and signed off on the retooling.", // AI Development Algorithm
  "amd": "Blue static snapped across the forward hull as the deflector array shoved a house-sized slab of nickel-iron off the bow. Behind the cruiser, incoming plasma bolts bent wide of the plating and spent themselves against the drifting rock.", // Antimass Deflectors
  "asc": "Lead cruisers linked ventral capacitors and tore a hole straight through the opposing vanguard.", // Assault Cannon
  "bs": "A cold sting behind the ear, followed by the metallic taste of iron on the tongue. Across the command deck of the *Hil Colish*, watch officers straightened at their consoles and pulled up fresh tactical grids.", // Bio-Stims
  "bio": "Tendrils of pale Dirzuga moss crept down the landing struts of the freighter overnight, rooting into the wet shale of the neighboring moon before the local garrison opened its morning gates.", // Bioplasmosis
  "cv2": "With extended flight decks and twin gravitic catapults, the retrofitted carriers could launch an entire fighter screen before enemy pickets even closed to gun range.", // Carrier II
  "cm": "Inside the Jorun belt, Saar pilots cut their transponders and thread their floating factories between tumbling iron slabs by dead reckoning. Foreign nav-computers flag the sector as impassable.", // Chaos Mapping
  "cl2": "Bound to Mahact command frequencies, the Crimson Legionnaire marches through artillery fire without breaking stride. When its runic armor finally shatters, the captive energy pattern snaps back to Ixth to be forged into a new frame.", // Crimson Legionnaire II
  "cr2": "Stripped of non-essential armor and fitted with an auxiliary drop-bay, the upgraded cruisers could outrun sector patrols and land shock troops before planetary alarms sounded.", // Cruiser II
  "dxa": "Medics didn't bother tagging the dead along the southern trench on Abyz. A single dose of Dacxive serum had half the fallen platoon back on their feet—and marching—within the hour.", // Dacxive Animators
  "det": "Long collector vanes unfolded from the scout frigate's spine, drawing stray charge from deep-space vacuum while its crew charted forgotten hyperlanes.", // Dark Energy Tap
  "dd2": "Quad-mounted flak batteries turned nimble escort hulls into screen-breakers, chewing through waves of enemy interceptors long before the dreadnoughts traded broadsides.", // Destroyer II
  "ds": "The Creuss navigator turned a glass vernier on the helm console, and the beta aperture flared violet. Local space pinched inward across the rival cruiser's midships, shearing its keel along a razor-clean line.", // Dimensional Splicer
  "dt2": "Violet haze bled from the widening wound above Acheron, pulling loose debris and drifting fighters into its swirling rim. Beneath the tear, flesh-hulled vessels emerged wet with starlight and banked straight toward the Core.", // Dimensional Tear II
  "dn2": "\"Three direct plasma hits on the forward belt and the reactor hasn't even flickered,\" the gunnery officer grinned. \"Bring us about and return the favor.\"", // Dreadnought II
  "da": "Zero-gravity kilns above Wren Terra cast duranium plating that flexes under plasma heat instead of fracturing, letting damage-control crews weld breaches shut between salvos.", // Duranium Armor
  "ers": "\"Log the incoming weapon signatures and route the bleed-off through the secondary capacitors,\" the Hylar dean told the bridge crew as foreign dreadnoughts dropped out of warp. \"Their battery discharge will fund the Nar trench project for a full cycle.\"", // E-Res Siphons
  "executiveorder": "DIRECTIVE 00-PRIME: BY SEAL OF THE GALACTIC COUNCIL, ALL FLOOR DEBATE IS SUSPENDED. IMMEDIATE ROLL CALL AUTHORIZED ON PRIORITY BAND ZERO.", // Executive Order
  "exile2": "Matte-black hull plates and baffled exhaust ports let the Exile II slip past orbital sensor buoys without tripping a single transponder alert.", // Exile II
  "exo2": "The N'orr captain locked the main thrusters to full burn and set a collision vector straight into the opposing dreadnought's superstructure. Across the bridge, the brood-crew clamped their mandibles shut and held course.", // Exotrireme II
  "ff2": "Fitted with micro-jump coils and long-endurance scrubbers, the new interceptors could hunt between neighboring stars without a carrier mothering them home.", // Fighter II
  "fl": "Amateurs argue over firepower; quartermasters win wars with fuel schedules and clean jump charts.", // Fleet Logistics
  "ffac2": "Massive maneuvering thrusters ignited along the lower ring of the orbital shipyard, dragging five kilometers of gantries, ore smelters, and fighter bays out of the asteroid belt at flank speed.", // Floating Factory II
  "gr": "At the hum of the gene-sorcerer's staff, the ambassador spoke against his own house in a voice not entirely his.", // Genetic Recombination
  "gls": "Narrow-beam gravitic emitters punched straight through the orbiting fighter screen, locking onto the heavy reactor signatures of the cruisers behind them.", // Graviton Laser System
  "gd": "Space folded ten kilometers ahead, dragging the cruiser forward in a bone-rattling lurch.", // Gravity Drive
  "htp": "Arbiter Berekon stamped the old Lazax charter in red wax and handed it back to the planetary governor. \"Under imperial law, civic influence and industrial output answer to the same treasury.\"", // Hegemonic Trade Policy
  "ht2": "Centuries of moss and shale split away as the stone monolith unfolded its armored shoulders. Plasma barrels rose from the collarbone plates while internal bays began stamping out fresh infantry.", // Hel-Titan II
  "hcf2": "Naalu artisans grow the interceptor hulls in resonant crystal vats on Druaa and wire them straight to the pilot's optic nerve, allowing turns that would shear a metal airframe in two.", // Hybrid Crystal Fighter II
  "hydrothermal": "Three kilometers beneath the dark swells of Ikatena, pressurized Kieros drills tapped superheated volcanic vents, pumping mineral-rich brine up to the floating refineries.", // Hydrothermal Mining
  "hm": "Synthetic enzymes cut the command staff's sleep to two hours a day.", // Hyper Metabolism
  "ic": "\"Pull the magnetic baffles and flood the core,\" the Yin captain told his helmsman, turning the destroyer's prow toward the enemy dreadnought. \"Our brothers will cross through the breach.\"", // Impulse Core
  "inf2": "Servo-assisted harnesses, sealed visors, and rapid-clotting med-packs kept half the wounded drop-troopers alive long enough for the orbital recovery shuttles to pull them off the ridge.", // Infantry II
  "is": "Deep inside the Mindnet's central memory core, decrypted Lazax schematics from the First Empire surfaced in clean white text. The L1Z1X engineers began fabricating the components before the council session adjourned.", // Inheritance Systems
  "it": "Elder Junn lowered his eyelids as the warning klaxons echoed across the bridge, counting three slow breaths before calling the counter-maneuver that broke the ambush.", // Instinct Training
  "ie": "Before the ink dried on the capitulation writ, occupation engineers had already re-keyed the local foundry looms to stamp out fresh rifle barrels and armored walkers.", // Integrated Economy
  "l4": "High-band static flooded the planetary radar dishes from orbit, blinding the surface batteries while Letnev drop-pods fell unopposed through the cloud layer.", // L4 Disruptors
  "lgf": "Beneath the cracked flagstones of the Imperial Palace, ancient transit rings woke with a low tremor that rattled dust from the vaults above. A Winnu keeper stepped back from the console as a pale blue aperture steadied between the pillars, keyed from a cipher preserved since the Twilight Wars.", // Lazax Gate Folding
  "lw2": "Thick bark-plates shed small-arms fire along the mud line while fine pollen drifted off the Letani's shoulders, taking root in the shell craters behind the advance.", // Letani Warrior II
  "lwd": "Phase-shifted shield emitters bent optical and gravitic scans around the formation, letting the cruisers slip straight through the enemy blockade line before the pickets could come about.", // Light/Wave Deflector
  "linkship2": "Mast-mounted telemetry dishes locked onto every friendly hull in the sector, feeding unified firing solutions from the Linkship's deck straight to the consortium's heavy batteries.", // Linkship II
  "md": "Orbital shields dropped low over the bunker roofs as automated turret rails emerged from the ferrocrete, raking the landing zone before the first enemy ramp touched down.", // Magen Defense Grid ΩΩ
  "mi": "The sliver of wetware sat flush beneath the aide's collar, invisible to standard medical scans. Every dispatch that crossed his desk appeared on a Yssaril slate in Shalloq four seconds later.", // Mageon Implants
  "mr": "Heat-shields glowed dull crimson as the Gashlai foundry-ship dipped into the outer corona of the supernova, drawing raw stellar plasma straight into its hull-casting crucibles.", // Magmus Reactor
  "m2": "Bulkheads and chronometric stabilizers salvaged from a dozen divergent eras line the *Memoria*'s hull. When it clears a jump-point, its flak pods are already tracking targets that have not yet launched.", // Memoria II
  "mc": "Two ledgers ran side by side on the Mentak quartermaster's encrypted slate—one for the Council customs inspectors, and one that turned every bar of Moll Primus gold into double credit at the shipyards.", // Mirror Computing
  "nanomachines": "Gray metallic dust poured from the dorsal vents across the scorched hull plating, knitting torn bulkheads shut before the compartment's emergency seals could drop.", // Nanomachines
  "nm": "Measured doses of synaptic accelerants kept the naval staff drafting contingency orders three hours ahead of every opposing fleet in the quadrant.", // Neural Motivator
  "parasite-firm": "The micro-filament enters behind the ear during a crowded corridor briefing, leaving no scar. Two cycles later, the magistrate signs the Firmament's charter without pausing to read the second page.", // Neural Parasite (Firmament)
  "parasite-obs": "Black veins traced the temple of the watch officer as he stepped to the airlock console and keyed in the override code, his expression flat beneath the red emergency lamps.", // Neural Parasite (Obsidian)
  "ng": "A psychic shriek tore through the helm deck the moment the cruisers crossed into Druaa space, leaving half the bridge officers clutching their temples while their formation scattered.", // Neuroglaive
  "nes": "Barony shield harmonics warped local space around the dreadnought's prow, folding twin plasma broadsides along curved vectors until they dissipated harmlessly into the dark.", // Non-Euclidean Shielding
  "nf": "A pale ring of static expanded from the *Loncara Ssodu*, killing every drive coil and targeting lock in the sector. The approaching cruisers drifted on momentum alone, weapons cold.", // Nullification Field
  "pds2": "Deep-space optics tied to subterranean rails brought neighboring jump-lanes inside planetary gun range.", // PDS II
  "planesplitter-firm": "Air shimmered beside the warehouse bulkhead on Resculon as the emitter tuned its crystal core, opening a narrow, silent seam wide enough for two couriers and a sealed crate.", // Planesplitter (Firmament)
  "planesplitter-obs": "A jagged black tear split the air across the center of the command deck, spilling freezing, starless air over the steel grating as armored figures stepped through.", // Planesplitter (Obsidian)
  "ps": "Superheated magnetic containment lets a heavy gun barrel cycle hotter and longer without warping its bore.", // Plasma Scoring
  "pfa": "Drop-pods punched into the red clay of Lazar and fired their foam-crete charges. By the next morning cycle, pressurized habitation domes and solar arrays stood anchored around the excavation pit.", // Pre-Fab Arcologies
  "pi": "Statistical models cross-referenced every senator's voting history, trade debts, and border garrisons, printing the likely roll call on the ambassador's slate six hours before the gavel fell.", // Predictive Intelligence
  "pm": "Pressurized glass domes stretched across the dunes of Arretze, turning arid moons into irrigated spice-gardens whose harvests filled both Hacan vaults and allied freighter holds.", // Production Biomes
  "pws2": "Slag rained from the orbital rings of Muaat as the refined sphere broke clear of the gantry, its containment core burning brighter and faster than the original designs seized from the Jol-Nar.", // Prototype War Sun II
  "proxima": "Six thousand ballistic solutions a second let Bastion gunners drop orbital shells forty meters ahead of their own trenches, walking a curtain of fire straight into the enemy line.", // Proxima Targeting VI
  "pa": "The researcher pressed her palm against the carved basalt of the Lazax vault, reading the faint neural echo left by its builders before keying the lock open without a cipher.", // Psychoarchaeology
  "qdn": "\"Transfer three hundred thousand aurei from the Arretze reserve to the Sol delegation's account,\" Gila told her clerk, tapping the encrypted relay. \"Tell the ambassador we will take the Imperial docket this cycle.\"", // Quantum Datahub Node
  "radical": "The Kieros scholar struck out three decades of Jol-Nar proofs on the glass board and began a fresh derivation from the bottom margin, his sleeves soaked with tank water.", // Radical Advancement
  "so": "\"Clamp the tow-lines onto that cruiser's reactor housing before it cools!\" the corsair chief shouted over the deck intercom. \"Strip the bulkheads and bolt them onto the next keel.\"", // Salvage Operations
  "st": "Automated laser-welders and modular hull jigs cut waste alloy to a fraction, letting even a frontier space dock turn out cruisers on a tight budget.", // Sarween Tools
  "se2": "Stone-gray armor plates slid flush over the radiator vents as the Saturn Engine accelerated out of Elysium's orbit, its reinforced spine built to take a dreadnought's broadside and keep closing.", // Saturn Engine II
  "sdn": "Palm-sized recon drones fanned out from the landing pad at dusk, mapping buried cisterns, collapsed Lazax bunkers, and forgotten supply caches beneath the crust.", // Scanlink Drone Network
  "sar": "Micro-forges bolted inside the forward supply depots stamped out replacement walker chassis from local ore, rolling fresh mechs onto the line without waiting for an orbital lift.", // Self-Assembly Routines
  "sr": "Magnetic rails along the outer drydock ring snapped to full charge, slinging a newly commissioned destroyer straight out of the gantry and into active patrol formation.", // Sling Relay
  "sd2": "Triple-ringed assembly bays circled Jord's equator, their arc welders burning day and night as fresh cruiser keels slid off the ways.", // Space Dock II
  "scc": "Space folded between the blue twin rings orbiting Jol and the forward picket line on the rim. Through the glowing aperture, an entire research fleet crossed four sectors in a single burn.", // Spatial Conduit Cylinder
  "so2": "Black-visored Federation drop-troopers hit the mud of Tequ'ran under heavy mortar fire, cutting through the perimeter wire before the defenders could bring their heavy walkers online.", // Spec Ops II
  "swa2": "Gull-winged interceptors dove in tight formation through the flak bursts, their twin autocannons raking both the enemy fighter screen and the troop transports huddled behind it.", // Strike Wing Alpha II
  "subatomic": "One thin crimson beam, and three meters of solid duranium crumbled into gray dust.", // Subatomic Splicer
  "sdn2": "Black iron and red optical arrays rose above the outer moons of [0.0.0], the Mindnet's heavy hull mounting enough plasma batteries to level a capital city from high orbit.", // Super Dreadnought II
  "sc": "\"Dump the reserve capacitors into the main bus!\" the Rokha gunner yelled. \"We can worry about the warranty if we survive!\"", // Supercharge
  "tcs": "The Nomad's officers do not wait for dispatches from the future. Sometimes they simply file their reports yesterday.", // Temporal Command Suite
  "td": "Ozone bit the air inside the transfer bay on Jord as an entire infantry company vanished in a flash of white static, reappearing a heartbeat later inside a forward bunker on Saudor.", // Transit Diodes
  "tp": "Clear as blown glass and dense enough to stop a rail-slug, the Yssaril alloy hid forward listening posts in plain sight while rival patrols marched past within arm's reach.", // Transparasteel Plating
  "vax": "ASSIMILATION.PROTOCOL.X: FOREIGN ARCHITECTURE ISOLATED.\nDECRYPTING COMPONENT SCHEMATICS. REWRITING HOST MATRIX.", // Valefar Assimilator X
  "vay": "ASSIMILATION.PROTOCOL.Y: SECONDARY VECTOR LOCKED.\nINTEGRATING ACQUIRED SUBSYSTEMS INTO SWARM CORE.", // Valefar Assimilator Y
  "vpw": "Reactive filaments woven into the N'orr carapace detonated outward on impact, showering nearby trenches with white-hot shrapnel every time a rifle round cracked the chitin.", // Valkyrie Particle Weave
  "vw": "A soft chime sounded across the dark bridge of the *Dynamo* as a foreign transponder crossed the outer buoys. Before the intruder could lock weapons, an Empyrean courier was already transmitting the transit toll.", // Voidwatch
  "vtx": "A localized gravity shear snapped outward from Acheron's rift, seizing an unescorted frigate mid-jump and reeling the helpless vessel straight into the Cabal's maw.", // Vortex
  "ws": "A captive star caged in layered durasteel, its equatorial cannon banks capable of scouring a continent to glass before planetary shield generators can cycle a second charge.", // War Sun
  "wg": "The glass emitter on the Creuss frigate's bow spun up to a high, ringing whine, peeling open a fresh violet aperture above the barren moon.", // Wormhole Generator
  "x89c4": "Sealed glass canisters tumbled through the upper cloud deck and burst in silent mist over the valley. Within an hour, orbital sensors logged zero bio-signs inside the fortress trenches, leaving every concrete wall, turret, and stockpile completely untouched for the landing troops.", // X-89 Bacterial Weapon ΩΩ
  "yso": "Rows of amber gestation pods hummed along the lower decks of the Yin transports, decanting fresh brothers into the armory before the assault shuttles had even cleared the drydock.", // Yin Spinner Omega
};

/** Breakthroughs (Thunder's Edge). */
const breakthrough: LoreMap = {
  "naazbt": "Inside the *Eidolon*'s cramped cockpit, Dart worked the gyroscopic stick while Tai fed manual solutions into the dorsal railgun. Neither spoke a word; after years of digging through ruined vaults on Naazir together, their hands moved across the shared console like a single pilot.", // Absolute Synergy (Naaz-Rokha)
  "cabalbt": "Long before the violet tear split the sky above Acheron, every long-range transponder in the sector began broadcasting a low, grinding static. Old navigators mutter protective wards at the sound and call it Al'Raith Ix Ianovar.", // Al'Raith Ix Ianovar (Vuil'raith Cabal)
  "xxchabt": "Elder Qanoj set the silver-bound charter of Archon Ren beside the rival ambassador's slate. \"A gift from the Kingdom carries no tribute,\" he said. \"Only the memory of who stood beside us when the sky darkened.\"", // Archon's Gift (Xxcha)
  "hacanbt": "Across the orbital rings of Arretze, automated plasma gantries welded freighter keels through the night shift with no organic foreman on the catwalks. By dawn, fresh hulls hung ready for the guild factors.", // Auto-Factories (Hacan)
  "solbt": "The plaque above the embarkation ramp at Churchill Prima bears two words hammered into weathered brass: *Bellum Gloriosum*. Every marine touches the letters with a gloved palm before the bay doors cycle open.", // Bellum Gloriosum (Sol)
  "ralnelbt": "A Ral Nel broker leaves the encrypted vault doors untouched. A thin tap spliced into the relay buoy's routing headers yields ship tonnages, fuel stops, and buyer codes before the convoy even clears customs.", // Data Skimmer (Ral Nel)
  "yssarilbt": "The Jol-Nar systems chief signed off on fourteen consecutive clean security audits, never realizing the minor latency spike in the dispatch kernel was a Yssaril worm copying every fleet order in real time.", // Deepgloom Executable (Yssaril)
  "saarbt": "Saar tug-crews welded surplus maneuvering thrusters onto a half-kilometer slab of iron-rich asteroid in the Jorun belt and burned it into a decaying vector. Down on the contested moon, the planetary shield sirens began to wail.", // Deorbit Barrage (Saar)
  "l1z1xbt": "One burst of red carrier-code locked every helm in the squadron to the flagship.", // Fealty Uplink (L1Z1X)
  "letnevbt": "\"Bring the prow twelve degrees closer to the moon's gravity well,\" Rear Admiral Farran ordered, gripping the steel rail as the deck plates groaned. \"Let the hull shriek. We take their flank before they can come about.\"", // Gravleash Maneuvers (Letnev)
  "keleresbt": "Fresh ferrocrete blast doors, encrypted Council relays, and a ring of high-gain sensor spires rose over the old Imperial Intelligence Headquarters in Mecatol City. Inside the sub-levels, Tribuni analysts tracked fleet movements from the Core to the rim.", // I.I.H.Q. Modernization (Keleres)
  "winnubt": "\"The regency is over,\" Berekon told the silent chamber, laying his hand on the Lazax throne.", // Imperator (Winnu)
  "naalubt": "Across the negotiating table, the Naalu envoy kept her gaze fixed on the rim of her tea cup. Inside the Sol captain's head, the fallback coordinates for his reserve carrier surfaced like a cork in dark water.", // Mindsieve (Naalu)
  "sardakkbt": "Plasma cutters burned through the airlock bulkhead, and the low, clicking drone of the Tekklar brood filled the corridor. On the far side of the breach, the defending marines fixed bayonets and stepped back from the hatch.", // N'orr Supremacy (Sardakk N'orr)
  "ghostbt": "Ships passing through a Creuss aperture briefly scatter into cold ribbons of starlight, reassembling light-years away with frost still clinging to their bulkheads.", // Particle Synthesis (Ghosts of Creuss)
  "arborecbt": "Pale spores drifted through the garrison's ventilation shafts during the night watch. By sunrise, the frantic radio chatter from the perimeter bunkers had given way to the slow, steady cadence of the Symphony.", // Psychospore (Arborec)
  "crimsonbt": "The rebel engineer jammed the copper shunt past the thermal stop as the containment coils whined into the red. Across the sector, imperial navigation buoys flickered and died in a wash of crimson static.", // Resonance Generator (Crimson Rebellion)
  "titansbt": "Beneath Elysium, stone minds spent ten millennia modeling every war the younger races might fight.", // Slumberstate Computing (Titans of Ul)
  "jolnarbt": "Compound Nine quadrupled synaptic response times in Hylar test subjects. When a junior regent noted minor neural degradation in the lower gills, the Circle approved fleet-wide distribution anyway.", // Specialist Compounds (Jol-Nar)
  "muaatbt": "Superheated plasma spiraled inward between the Gashlai crucible ships until gravity caught hold and the dark ignited. Where empty vacuum had stretched an hour before, a newborn dwarf star burned white against the rim.", // Stellar Genesis (Muaat)
  "bastionbt": "Through the artillery dust above Ordinian, the white iron standard atop the citadel spire held upright against the gale. Along the ruined wall, defenders checked their magazines and climbed back to the parapet.", // The Icon (Last Bastion)
  "obsidianbt": "Relay stations along the outer rim went dark one by one before any distress call could clear the sector. By the time the first courier reached the Core, black-hulled cutters were already dropping into low orbit above the frontier worlds.", // The Reaping (Obsidian)
  "firmamentbt": "A folded pamphlet left in a barracks mess hall, a quiet transfer of credit to a disgruntled port-master, a forged seal in a governor's archive. Months before a shot is fired, the Firmament has already set the pieces.", // The Sowing (Firmament)
  "mentakbt": "Captain Suffi An pushed a pewter mug across the scarred oak table of the Moll Primus council hall. \"Every captain who sits here takes a fair share of the prize,\" she said. \"Those who skim from the pot walk out the airlock.\"", // The Table's Grace (Mentak)
  "nomadbt": "The brass chronometer on the Nomad's desk ticked backward through a battle that had not yet begun. \"Adjust the jump vector four degrees to port,\" he told his helm officer. \"That cruiser will fire from the sunward side in twelve seconds.\"", // Thunder's Paradox (Nomad)
  "nekrobt": "UNIT.DESGN: VALEFAR.Z // DIRECTIVE: HARVEST.\nFOREIGN BIOMECHANICAL MATRIX ISOLATED. OVERWRITING HOST ARCHITECTURE. COMPLIANCE ABSOLUTE.", // Valefar Assimilator Z (Nekro)
  "mahactbt": "Bronze stasis seals hissed open beneath the Plateau Imperia, spilling dry, ten-thousand-year-old air across the basalt steps. Inside the racks, gilded gene-staves and First Empire war-plates waited in neat rows.", // Vaults of the Heir (Mahact)
  "deepwroughtbt": "Four kilometers below the dark swells of Ikatena, Kieros archivists unsealed the Visionaria chambers, bringing up crystal plates etched with theorems the surface academies had never dared to test.", // Visionaria Select (Deepwrought)
  "empyreanbt": "Threads of dark energy stitched two dead sectors into a private highway.", // Void Tether (Empyrean)
  "argentbt": "\"Vanguard wing, break off from the Quann buoy and reinforce the eastern picket,\" Wing Leader Trrakan ordered over the tight-beam channel. Across the sunward glare, a crescent of destroyers peeled smoothly out of formation.", // Wing Transfer (Argent)
  "yinbt": "As the first brother fell across the shattered parapet, another stepped into his place, wearing the same scarred face, the same white mantle, and the same quiet resolve born in the monasteries of Darien.", // Yin Ascendant (Yin)
};

/** Faction abilities. */
const ability: LoreMap = {
  "aetherpassage": "\"Lower the void-screens and clear the lane,\" the Empyrean captain signaled across the dark. \"They may cross our space, provided they remember who holds the lantern.\"", // Aetherpassage (Empyrean)
  "amalgamation": "Nothing that enters Acheron stays wholly metal for long.", // Amalgamation (Vuil'raith Cabal)
  "ambush": "Before the rival flagship's gunnery officer could cycle his forward shields, Mentak cruisers slid out of the asteroid shadow and raked its bow at point-blank range.", // Ambush (Mentak)
  "analytical": "To the Circle of Regents, an unfamiliar problem is merely an equation someone on Jol solved three centuries ago.", // Analytical (Jol-Nar)
  "arbiters": "When the Barony and the Federation refuse to sit in the same chamber, both delegations still send couriers to Arretze. For a modest commission, Hacan factors keep the galaxy's sealed writs moving.", // Arbiters (Hacan)
  "armada": "Where other admiralties see an impossible supply ledger, the Barony sees a proper line of battle. Above Arc Prime, Letnev drydocks pack the outer orbits with iron until the local stars disappear.", // Armada (Letnev)
  "assimilate": "Minutes after L1Z1X troops secured the spaceport on Saudor, Mindnet drones stripped the local server racks and wired the orbital gantries directly into the flagship's core.", // Assimilate (L1Z1X)
  "awaken": "Beneath centuries of moss and crumbled basalt, stone shutters slid back along the ridge. Deep inside the mountain, plasma conduits began to hum.", // Awaken (Titans of Ul)
  "blood_ties": "Winnaran keepers walked the marble corridors of Mecatol City before half the Council had even charted its own home star. When Arbiter Berekon stepped onto the Promenade carrying the old imperial seal, the palace gates opened before a single guard asked his name.", // Blood Ties (Winnu)
  "brilliant": "\"You brought me a problem that has already been solved,\" Doctor Sucaban snapped, tossing the proposal aside. \"Try again when it breaks a law of physics.\"", // Brilliant (Jol-Nar)
  "coalescence": "Wait long enough on a Titan world and even the mountains turn out to be watching the sky.", // Coalescence (Titans of Ul)
  "council_patronage": "Backed by imperial tithes and the Speaker's wax seal, Keleres squadrons draw fuel, stipends, and fresh hull plates straight from the Council's own vaults.", // Council Patronage (Keleres)
  "crafty": "No Yssaril handler ever discards a useful secret. Intercepted fleet dispatches, dockyard manifests, private marriage contracts, and half-burned cipher slips accumulate in the damp vaults of Shalloq for decades until the exact hour a senator needs reminding.", // Crafty (Yssaril)
  "creuss_gate": "A shimmering tear of pale blue frost hangs at the edge of Shaleri space. Beyond the threshold, the familiar star-charts of the Core mean nothing.", // Creuss Gate (Ghosts of Creuss)
  "dark_whispers": "Far beyond the mapped hyperlanes, Empyrean envoys strike quiet treaties that never reach the Custodian Chronicle—offering safe passage to those who keep their secrets.", // Dark Whispers (Empyrean)
  "devotion": "\"My drive core is breached and the helm is dead,\" the Yin captain transmitted over the brotherhood band. \"Clear the approach lane, brothers. I am going in.\"", // Devotion (Yin)
  "devour": "The Cabal fights with jaws wide open, leaving neither scrap nor survivors behind.", // Devour (Vuil'raith Cabal)
  "distant_suns": "\"Run the subsurface sweep again,\" Dart called from the crawler's hatch as a second buried vault lit up beneath the red dust of Abyz. \"We never stop at the first find.\"", // Distant Suns (Naaz-Rokha)
  "edict": "Even after ten millennia in stasis, the old kings speak with voices that turn an enemy captain's loyalty to ash.", // Edict (Mahact)
  "fabrication": "Give a Rokha smith a crate of fractured Lazax stone and a plasma torch, and by morning she will hand you a working relic or a fresh ingot of rare metal.", // Fabrication (Naaz-Rokha)
  "foresight": "\"Break orbit now,\" the Naalu matriarch ordered, her gaze fixed on an empty patch of starlight. \"Before the next bell, a Letnev vanguard drops straight onto this buoy.\"", // Foresight (Naalu)
  "fragile": "Soft-boned and bred for deep ocean pressure, Hylar researchers were never meant to hold a trench line against Sardakk shock troops.", // Fragile (Jol-Nar)
  "future_sight": "\"Bet against the motion,\" the Nomad murmured, dropping a heavy pouch of aurei on the table while the Speaker was still calling the roll. \"Trust me—I've seen how this vote ends.\"", // Future Sight (Nomad)
  "galactic_threat": "QUERY.COUNCIL.CHAMBER: DIPLOMATIC ACCESS REVOKED.\nDIRECTIVE: PREDICT ORGANIC CONSENSUS. HARVEST RESULTING ARCHITECTURE.", // Galactic Threat (Nekro)
  "galvanize": "Across the shattered parapet of Ordinian, the Bastion commander raised the white iron standard. Along the mud line, exhausted riflemen locked fresh magazines and climbed back to the wall.", // Galvanize (Last Bastion)
  "gashlai_physiology": "Forged in the volcanic furnaces of Muaat, the Gashlai steer their cruisers straight through supernova coronas that would boil any other hull to slag.", // Gashlai Physiology (Muaat)
  "guild_ships": "Golden-prowed Hacan merchantmen cross hostile borders without an escort, carrying rare metals, spice, and sealed letters to any port that honors the Emirates' mark.", // Guild Ships (Hacan)
  "harrow": "L1Z1X orbital doctrine draws no line between fleet action and ground assault; the sky stays on fire until the last bunker goes quiet.", // Harrow (L1Z1X)
  "hubris": "The Mahact do not treat with lesser species as equals. Every other throne in the galaxy is merely a seat kept warm until their return.", // Hubris (Mahact)
  "imperia": "Kneel, and a Gene-Sorcerer might spare your house. Refuse, and your own admirals will turn your guns against you.", // Imperia (Mahact)
  "incursion": "Rebel cutters drop out of unstable fractures, bleed the imperial supply lines, and vanish before the Core dreadnoughts can bring their guns to bear.", // Incursion (Crimson Rebellion)
  "indoctrination": "\"Lay down your rifle and listen,\" the Yin brother called across the shell crater. \"Why bleed for a distant senator when Darien welcomes you as kin?\"", // Indoctrination (Yin)
  "laws_order": "\"The Senate wrote those statutes for peacetime,\" the Tribuni commander muttered, cutting the transmission. \"We'll file the paperwork after sunset.\"", // Law's Order (Keleres)
  "liberate": "When Last Bastion troops break an occupying garrison, the local dockworkers and farmers pull hidden rifles from the floorboards and fall in behind the march.", // Liberate (Last Bastion)
  "marionettes": "Senators cast their ballots and admirals sign fleet orders, unaware that the hand guiding the ink sits in the dark behind the gallery.", // Marionettes (Obsidian)
  "master_of_trade": "\"Tariffs? For an Arretze guild vessel?\" The Hacan broker slid a stamped gold seal across the customs desk. \"Check the exemption ledger again, magistrate.\"", // Masters of Trade (Hacan)
  "miniaturization": "Space is expensive on the Twin Worlds. Ral Nel engineers learn young how to pack a drydock's worth of hardware into a shipping crate.", // Miniaturization (Ral Nel)
  "mitosis": "Every morning cycle, the Letani shed pale spores across the damp soil, raising fresh warriors from the mud before the local sun clears the ridge.", // Mitosis (Arborec)
  "munitions": "\"Break open the reserve lockers and double the plasma charge,\" the Letnev gunnery chief barked as the hull shuddered. \"The Baron pays for dead cruisers, not full magazines.\"", // Munitions Reserves (Letnev)
  "nocturne": "When the sector relays go dark and long-range sensors fill with cold static, the Obsidian slip their moorings and cross the border.", // Nocturne (Obsidian)
  "nomadic": "Home is wherever the floating factories drop anchor. Since the loss of Lisis, the Clan of Saar carries its entire civilization in its wake.", // Nomadic (Saar)
  "oceanbound": "Crushing abyssal pressure that would buckle a dreadnought's keel feels like calm air to the Deepwrought. Beneath the dark swells of Ikatena, their vaults remain untouched.", // Oceanbound (Deepwrought)
  "orbital_drop": "Drop-pods screamed through the storm clouds in tight rows, punching into the gravel around the spaceport before the local garrison could reach the perimeter wall.", // Orbital Drop (Sol)
  "peace_accords": "\"Why shell a border world into rubble when a fair charter will bring their governor to Archon Ren by sunset?\" Elder Qanoj asked, folding his hands.", // Peace Accords (Xxcha)
  "phoenixstandard": "Even when a Bastion line buckles under orbital fire, the survivors rally around the scorched standard and drive back into the breach.", // Phoenix Standard (Last Bastion)
  "pillage": "\"A fine haul you have there, neighbor,\" the Mentak captain said over the tight-beam channel as his cruiser matched velocity. \"Toss a chest of aurei out the airlock and we will clear your lane.\"", // Pillage (Mentak)
  "plotsplots": "By the time a rival intelligence chief uncovers the first Firmament cell, deeper contingencies have already locked into place across the sector.", // Plots Within Plots (Firmament)
  "propagation": "RESEARCH.PROTOCOL: TERMINATED.\nDIRECTIVE: EXPAND SWARM COORDINATION. ACQUIRE SUPERIOR ARCHITECTURE THROUGH DIRECT COMBAT.", // Propagation (Nekro)
  "puppetsoftheblade": "In every embassy along the Senate Promenade, a quiet clerk or courier waits for a single coded phrase from the Firmament.", // Puppets of the Blade (Firmament)
  "quantum_entanglement": "Creuss navigators do not chart distance in light-years. To them, space is a folded cloth pinned at the seams.", // Quantum Entanglement (Ghosts of Creuss)
  "quash": "\"This motion is poorly drafted and invites war,\" the Xxcha senator declared, striking it from the Speaker's docket before the floor could open debate.", // Quash (Xxcha)
  "raid_formation": "Shikrai pilots learn to fly in formation before they learn to land alone. When an Argent wing dives, there are no stragglers.", // Raid Formation (Argent)
  "reclamation": "The moment Winnu feet touch the flagstones of Mecatol City, dormant Lazax defense grids and orbital gantries hum back to life to greet their stewards.", // Reclamation (Winnu)
  "researchteam": "Where a Kieros expedition sets up camp, Hylar scholars are rarely far behind—each translating what the other would rather overlook.", // Research Team (Deepwrought)
  "riftmeld": "The Cabal weaves dimensional tears directly into their orbital shipyards, hurling flesh-and-steel armadas across entire sectors through bleeding wounds in space.", // Riftmeld (Vuil'raith Cabal)
  "scavenge": "To a Saar crew, a battlefield is just an unharvested quarry.", // Scavenge (Saar)
  "scheming": "While other houses draft battle plans, Yssaril handlers quietly sort through stolen dispatches, keeping the sharpest leverage and burning the rest.", // Scheming (Yssaril)
  "slipstream": "Most crews brace for turbulence when clearing a wormhole. Creuss helmsmen surf the wake.", // Slipstream (Ghosts of Creuss)
  "stall_tactics": "\"Hold station behind the moon,\" the Yssaril commander murmured, watching the opposing armada burn fuel in empty space. \"Let them show their hand first.\"", // Stall Tactics (Yssaril)
  "star_forge": "Inside the blazing core of a War Sun, Gashlai smiths pour raw stellar plasma into hull molds, launching fresh squadrons straight from the furnace.", // Star Forge (Muaat)
  "sundered": "Cast out of their own dimension and rejected at the Creuss Gate, the crimson Creuss walk between worlds as exiles.", // Sundered (Crimson Rebellion)
  "survivalinstinct": "When foreign transponders lock onto a Ral Nel picket, the crews cut the safety governors, burn hard for the rim, and refuse to die in a fair fight.", // Survival Instinct (Ral Nel)
  "technological_singularity": "COMBAT.RESULT: HOSTILE VESSEL TERMINATED.\nEXTRACTING SCHEMATICS FROM DEBRIS FIELD. INTEGRATION COMPLETE.", // Technological Singularity (Nekro)
  "telepathic": "A Naalu squadron needs no radio channel to turn in unison. One pilot sees the opening, and a hundred minds bank as one.", // Telepathic (Naalu)
  "terragenesis": "Slowly, cycle by cycle, Titan engines reshape every world they claim into a fortified bastion of carved stone and humming machinery.", // Terragenesis (Titans of Ul)
  "bladesorchestra": "Silent strikes timed to the exact second across separate sectors. When the Obsidian reveal their hand, every cut falls in rhythm.", // The Blade's Orchestra (Obsidian)
  "the_company": "Specialists plucked from divergent corners of history, bound together by a single employer whose face none of them have ever seen.", // The Company (Nomad)
  "sorrow": "The memory of what was taken from them burns cold beneath every rebel bulkhead, fueling a vendetta older than the Council.", // Sorrow (Crimson Rebellion)
  "the_tribuni": "Drawn from the loyal houses of Mentak, Xxcha, and the Argent Flight, the Tribuni bring the combined doctrine of the Council's defenders to bear.", // The Tribuni (Keleres)
  "unrelenting": "N'orr shock troops charge straight through heavy plasma fire without breaking stride, clicking their mandibles in unison as the trenches close in.", // Unrelenting (Sardakk N'orr)
  "versatile": "Whether refitting cruisers above Jord or digging trenches in the mud of Tequ'ran, the Federation of Sol adapts faster than any rival staff can revise its orders.", // Versatile (Sol)
  "voidborn": "Nebulae blind standard sensors and stall conventional drives, yet Empyrean vessels glide through the ionized dust as if it were clear sky.", // Voidborn (Empyrean)
  "zeal": "When the Argent Flight rises to address the rotunda, their voices carry the weight of every wing patrolling the dark.", // Zeal (Argent)
};

/** Attachments (planet tokens). */
const attachment: LoreMap = {
  "biotic": "Pressurized glass domes line the equatorial ridge, their tanks glowing pale green with suspended cellular cultures and pre-Lazax flora.", // Biotic Research Facility
  "custodiavigilia1": "\"Keep the orbital rails warm and the patrol lanes clear,\" Kuuasi Aun Jalatai ordered from the bastion's command deck. Below the armored dome, the spires of Mecatol City caught the morning light.", // Custodia Vigilia
  "custodiavigilia2": "Along the outer ring of the station, long-range plasma batteries tracked every approaching transponder across the Core. No fleet dropped out of warp above the capital without answering the Tribuni hail.", // Custodia Vigilia
  "cybernetic": "Subterranean server halls hum beneath the permafrost, their neural-link cradles drawing enough power from the geothermal core to dim the colony's streetlamps.", // Cybernetic Research Facility
  "dmz": "By unanimous Council decree, every orbital gun was dismantled and every garrison recalled. Any house that lands armed troops here forfeits its seat on the Promenade.", // Demilitarized Zone
  "dysonsphere": "A lattice of dark, ancient alloy encircles the local star, siphoning raw stellar output down to orbital collector rings that never go cold.", // Dyson Sphere
  "gamma": "A pale violet seam hangs motionless above the upper cloud deck, humming with the same low resonance logged by surveyors inside the Mallice pocket.", // Gamma Wormhole
  "titanshero": "Tectonic plates ground together beneath the surface of Elysium as stone ribs rose through the crust, locking into vaulted bastions and deep-bore plasma batteries.", // Geoform
  "helios1": "Salvaged armor plates and heavy shield pylons brace the orbital gantries above Ordinian, keeping the assembly slips open under contested skies.", // Helios I
  "helios2": "\"Seal the bay and keep the gantry moving!\" the dock-master shouted over the klaxons as shrapnel peppered the shield pylons. Below him, a fresh cruiser frame dropped onto the assembly rails.", // Helios II
  "ionalpha": "Sheets of blue ionized plasma sweep across the upper stratosphere, scrambling local transponders and bending the nearby jump-lane toward distant apertures.", // Ion Storm (Alpha)
  "lazaxsurvivors": "Deep beneath the collapsed foundations of an imperial archive, a handful of ancient Lazax still keep the old court calendar, their pale hands steady on the brass astrolabe.", // Lazax Survivors
  "miningworld": "Bucket-wheel excavators chew through the iron ridges around the clock, sending a steady column of ore lifts up to the waiting bulk haulers in low orbit.", // Mining World
  "mirage": "\"Check the gravimetric array again—that sector was empty vacuum an hour ago,\" the scout officer said, leaning over the holomap. Outside the viewport, green oceans and white cloud bands turned slowly against the black.", // Mirage
  "nanoforge": "Silver dust drifts across the industrial yards like low fog, knitting fractured durasteel back together and stamping out hull plating straight from raw ore.", // Nanoforge
  "paradiseworld": "Warm trade winds roll off the turquoise bays toward the terraced villas where ambassadors from half the Council winter between sessions.", // Paradise World
  "propulsion": "Gravitic test-rings hang in synchronous orbit above the equator, their containment coils flaring white every time an experimental drive lurches across the proving lane.", // Propulsion Research Facility
  "richworld": "Thick seams of refined iodinium and heavy isotopes lie just beneath the topsoil, drawing guild prospectors and imperial tax factors on the same shuttle.", // Rich World
  "titanspn": "Subterranean Titan engines woke with a low rumble that rattled the survey tents. Within a cycle, fresh aquifers broke through the parched earth and stone terraces rose along the valley walls.", // Terraform
  "tombofemphidia": "A windowless obsidian vault stands untouched by wind or lichen at the center of the salt flat. Even the Hacan prospectors leave their plasma cutters on the shuttle before approaching the sealed doors.", // Tomb of Emphidia
  "warfare": "Bunkers, blast ranges, and prototype plasma foundries scar the southern continent, where weapons engineers test ordnance too volatile for populated worlds.", // Warfare Research Facility
};

/** Map features: anomalies, wormholes, borders and board tokens. */
const feature: LoreMap = {
  "wormhole_alpha": "Blue starlight bends inward around the Quann aperture, pulling loose dust into a slow, silent spiral. Beyond the rim, the jump-lane opens three sectors spinward.", // Alpha Wormhole
  "asteroids": "Tumbling slabs of nickel-iron and frozen methane crowd the transit lane. Standard nav-computers plot a wide detour; Saar pilots cut their transponders and fly straight through.", // Asteroid Field
  "avernus": "Rivers of white-hot magma split the basalt crust of Avernus, casting an orange glare against the bellies of orbiting cruisers. Only Gashlai forge-ships drop anchor inside its thermal envelope.", // Avernus
  "wormhole_beta": "Amber light warps along the edges of the beta rift, distorting the constellations behind it. Border pickets keep their forward shields raised whenever their patrol brings them within range.", // Beta Wormhole
  "breachactive": "Jagged crimson arcs snap across the open seam in local space, bleeding static into every shipboard comm. The corridor holds steady for now, wide enough for a strike wing to cross.", // Active Breach
  "breachinactive": "A dull, bruised scar hangs motionless in the vacuum, its edges humming with dormant energy until a rebel emitter keys the right frequency.", // Inactive Breach
  "custodian": "Automated Lazax defense turrets and robed Winnaran keepers stand watch over the ruined spires of Mecatol City, holding the seat of the First Empire until a house proves strong enough to claim it.", // Custodians
  "wormhole_delta": "Pale violet frost shimmers across the threshold of the Creuss Gate. Foreign probes sent through the aperture return only blank telemetry and cracked optical lenses.", // Delta Wormhole
  "dmz_large": "Neutrality beacons pulse across every orbital band, warning rival fleets to keep their weapon bays cold under penalty of immediate Council sanction.", // Demilitarized Zone
  "egress": "A blinding seam tears open along the Fracture's edge, spitting scorched warships back into normal space with their armor plates still popping from the thermal shock.", // Egress
  "entropicscar": "Hull alloy pits and flakes within minutes of crossing the boundary, while shipboard chronometers drift out of sync. Even the Jol-Nar survey tenders mark the zone in solid red.", // Entropic Scar
  "wormhole_epsilon": "A sharp crimson fissure vibrates along an unlisted frequency just outside the Core. Imperial charts show empty vacuum until rebel cutters spill across the lane.", // Epsilon Wormhole
  "fracture": "Local space splits like stressed glass, revealing a cold, starless expanse pressed flush against the rim of the galaxy.", // Fracture
  "frontier": "Beyond the old Lazax navigation beacons lie uncharted stars, drifting wrecks from forgotten wars, and anomalies no imperial surveyor ever lived to report.", // Frontier
  "wormhole_gamma": "A pale violet ring hangs suspended in the outer dark, bending distant starlight along the exact coordinates of the Mallice nexus.", // Gamma Wormhole
  "gravityrift": "Black vacuum twists the starlight around the vortex rim. Ride the outer shear at full burn and a cruiser clears an extra sector; slip a degree inward and the keel snaps.", // Gravity Rift
  "ingress": "A swirling dark funnel pulls loose ice and stray radiation toward the threshold of the Fracture, drawing scout corvettes away from the mapped stars.", // Ingress
  "ionalpha": "Crackling sheets of blue plasma sweep across the system, flooding every sensor array with white static before the storm front shifts toward a distant aperture.", // Ion Storm Alpha
  "ionbeta": "Charged amber arcs dance across cruiser shields, scrambling long-range optics and forcing gunners to fire by manual rangefinder.", // Ion Storm Beta
  "mirage": "Where the star charts showed only empty void, an uncharted world now turns in the sensor glare—its coastlines veiled in mist and rising interceptor trails.", // Mirage
  "nebula": "Dense clouds of ionized dust swallow starlight and choke sublight thrusters. Cruisers enter blind at half-speed, their hull sensors reduced to point-blank range.", // Nebula
  "relictoken": "A faint, rhythmic pulse rises from the shattered masonry of a pre-Lazax vault, repeating a sequence no living linguist can translate.", // Relic Token
  "severed": "A jagged wall of disrupted space cuts straight across the hyperlane, leaving pursuing cruisers stalled against a dead end.", // Severed
  "sleeper": "Half-buried in moss and stone, a weathered basalt monolith rests beneath the ridge, its internal conduits dormant until the Ul sounds the recall.", // Sleeper
  "spatial_tear": "A ragged violet seam bleeds along the sector border, pulling loose debris and unescorted transports toward the hunger of the Cabal.", // Spatial Tear (border)
  "supernova": "A dying star burns in blinding white fury, its corona stripping the plating off any vessel save the heat-shielded forge-ships of Muaat.", // Supernova
  "thundersedge": "Violent electrical storms scour the dark horizons of Thunder's Edge at the rim of charted space, where ancient machinery hums beneath the crust.", // Thunder's Edge
  "void_tether": "Shimmering boundary markers hang along the void's edge, sealing the jump-lane shut to any vessel without an Empyrean cipher.", // Void Tether (border)
  "worlddestroyed": "Where a populated world once turned, only a cooling ring of fractured crust and drifting gray ash remains along the orbit.", // Destroyed World
};

/** Faction units (flagships, mechs, unique ships/ground forces). */
const unit: LoreMap = {
  "bastion_spacedock": "Welded together from salvaged cruiser ribs during the siege of Ordinian, the Helios V1 keeps its plasma gantries cycling even when orbital flak rings against the outer trusses.", // 4X41C "Helios" V1 (bastion spacedock)
  "l1z1x_flagship": "Bearing only a root designation from the dawn of the Mindnet, [0.0.1] ignores escort fighters completely, punching its heavy beams straight through to the enemy's capital ships.", // [0.0.1] (l1z1x flagship)
  "bastion_mech": "The A3 Valiance slammed its ferrocrete blast shield into the rubble of the eastern breach and locked every hydraulic knee-joint. Behind its broad iron shoulders, a pinned infantry platoon caught its breath, swapped hot barrels, and reloaded under steady cover as plasma bolts sparked harmlessly off the plating.", // A3 Valiance (bastion mech)
  "sol_carrier": "Built in the orbital yards of Jord to haul entire regiments across the frontier, the Advanced Carrier serves as the backbone of every Sol expedition.", // Advanced Carrier I (sol carrier)
  "argent_mech": "Built light enough to clamp onto a destroyer's outer hull, the Aerie Sentinel drops onto contested ridges alongside the first scouting flight.", // Aerie Sentinel (argent mech)
  "ralnel_mech": "The Alarum hits the gravel at a dead run, its dorsal emitter flooding local tactical bands with white static while its crew secures the extraction point.", // Alarum (ralnel mech)
  "l1z1x_mech": "Before the cybernetic infantry even reaches the perimeter wire, the Annihilator braces its hydraulic legs and shells the enemy bunkers with its shoulder-mounted mortar.", // Annihilator (l1z1x mech)
  "letnev_flagship": "Viscount Unlenn's voice carried across every open channel on the planet below as the *Arc Secundus* settled into low orbit, its ventral batteries cycling past the planetary shield harmonics.", // Arc Secundus (letnev flagship)
  "keleres_flagship": "Painted in Council silver and bristling with Tribuni intercept transponders, the *Artemiris* holds station above contested jump-lanes, forcing any approaching house to answer to the Senate before crossing its bow.", // Artemiris (keleresm flagship)
  "mahact_flagship": "Gilded in First Empire bronze, the *Arvicon Rex* still carries the battle honors of kings who broke entire sectors before the Lazax were born.", // Arvicon Rex (mahact flagship)
  "yssaril_mech": "By the time the border garrison spots the faint heat-shimmer of a Blackshade Infiltrator along the ridge, the perimeter mines have already been rewired to face the bunkers.", // Blackshade Infiltrator (yssaril mech)
  "sardakk_flagship": "Chitinous armor plates bristle along the prow of the *C'morran N'orr*. Where its war-horns vibrate across the hull-comms, every N'orr cruiser in the sector tightens its formation and drives forward.", // C'morran N'orr (sardakk flagship)
  "carrier": "Fleet carriers trade speed and heavy armor for cavernous hangar bays, ferrying fighter wings and ground divisions wherever the campaign demands.", // Carrier I (generic carrier)
  "mentak_cruiser3": "\"Let the admirals form their neat battle lines,\" the Mentak helmswoman smirked, cutting through the blockade's blind spot. \"We didn't come to trade broadsides with their escorts.\"", // Corsair (mentak cruiser)
  "mahact_infantry": "Creuss explorers enslaved on Ixth and twisted to burn crimson inside bronze-sealed armor, the Legionnaires advance through artillery smoke in eerie silence until their containment shells crack.", // Crimson Legionnaire I (mahact infantry)
  "cruiser": "Fast enough to outrun a dreadnought and armed well enough to scatter pickets, the standard cruiser handles everything from border patrols to deep-space raids.", // Cruiser I (generic cruiser)
  "deepwrought_flagship": "Bioluminescent conduits pulse pale blue along the pressure-rated hull of the *D.W.S. Luminous*, casting the cold light of the Ikatena trenches across the dark.", // D.W.S. Luminous (deepwrought flagship)
  "destroyer": "Built cheap and fast around rapid-tracking flak batteries, destroyers break enemy fighter screens before torpedoes can reach the capital ships.", // Destroyer I (generic destroyer)
  "cabal_spacedock": "A jagged violet wound hangs in low orbit, pulling loose orbital debris into its swirling rim while fresh flesh-and-steel hulls crawl out of the tear.", // Dimensional Tear I (cabal spacedock)
  "dreadnought": "Smaller vessels clear the lane whenever a dreadnought drops out of warp. Its layered armor shrugs off escort fire while its main guns hammer planetary shields.", // Dreadnought I (generic dreadnought)
  "arborec_flagship": "Glass-domed spore nurseries span the dorsal spine of the *Duha Menaimon*. Whenever the flagship anchors above a contested world, clouds of pale pollen drift straight down into the soil.", // Duha Menaimon (arborec flagship)
  "letnev_mech": "\"Roll the Reapers off the ramp,\" the Barony captain ordered, tapping ash from his cigarillo onto the steel grating. \"The Baron's reserves are open, and those trenches are coming down before nightfall.\"", // Dunlain Reaper (letnev mech)
  "empyrean_flagship": "The *Dynamo* draws stray radiation from the dark between stars and bends it into pale barrier screens, absorbing plasma fire meant for the Empyrean vessels sailing in its wake.", // Dynamo (empyrean flagship)
  "deepwrought_mech": "Built for the crushing dark four kilometers beneath the waves of Ikatena, the Eanautic steps onto dry basalt with slow, hydraulic certainty.", // Eanautic (deepwrought mech)
  "naaz_mech": "Dart eased the gyroscopic stick back while Tai swung the dorsal railgun onto the bunker roof. Inside the *Eidolon*'s shared cockpit, Naaz reflexes and Rokha steel moved as a single frame.", // Eidolon (naaz mech)
  "naaz_voltron": "Four Eidolons locked limb-to-hull in a roar of entropic energy, rising into a colossus built to fight equally well in orbit or ankle-deep in bunker rubble. \"Hold onto the controls, Tai!\" Dart shouted over the klaxons.", // Eidolon Maximum (naaz mech)
  "muaat_mech": "Superheated plasma vents from the Ember Colossus's knee-joints with every stride, turning frozen tundra into steaming black mud while Gashlai shock troops advance in its wake.", // Ember Colossus (muaat mech)
  "crimson_destroyer": "Stripped of non-essential bulkheads and painted dull iron-red, the Exile I drops out of a crimson breach, rakes the convoy's escorts, and vanishes before the Core cruisers can come about.", // Exile I (crimson destroyer)
  "sardakk_dreadnought": "Carapace-thick armor plates and oversized ventral bomb-bays make the Exotrireme I a blunt instrument built to crack planetary fortresses from high orbit.", // Exotrireme I (sardakk dreadnought)
  "fighter": "Stripped down to an engine, a cockpit, and twin pulse cannons, a carrier-launched fighter relies on numbers and tight formation flying to overwhelm heavier hulls.", // Fighter I (generic fighter)
  "saar_spacedock": "Welded from stripped freighter hulls and propelled by salvaged thrusters, a Floating Factory turns any dense asteroid belt into a working shipyard before rival scouts can chart the lane.", // Floating Factory I (saar spacedock)
  "mentak_flagship": "The *Fourth Moon* slipped through the crossfire with its jamming arrays screaming at full gain, collapsing the rival dreadnought's damage-control shields before the broadside hit.", // Fourth Moon (mentak flagship)
  "sol_flagship": "Half fleet carrier, half mobile garrison, the *Genesis* carries enough drop-troopers, armored walkers, and training decks inside its cavernous hull to reinforce an entire sector campaign for months without ever returning to the shipyards of Jord.", // Genesis (sol flagship)
  "firmament_flagship": "High above the trade lanes, the *Heaven's Eye* drifts with its passive arrays open, logging convoy manifests, fleet bearings, and private Council relays.", // Heaven's Eye (firmament flagship)
  "obsidian_flagship": "Where the *Heaven's Eye* once kept quiet watch, a blackened, hollowed-out silhouette now crosses the starlight, snuffing out every navigation buoy in its path.", // Heaven's Hollow (obsidian flagship)
  "titans_mech": "Articulated stone arms and recessed plasma pods unfold from the Hecatoncheires's chassis the moment an Ul recall signal wakes it from the bedrock.", // Hecatoncheires (titans mech)
  "titans_pds": "Centuries of lichen peel away from the monolith as its stone shoulders split open, revealing both orbital plasma rails and armored legs built to hold the ground.", // Hel-Titan I (titans pds)
  "ghost_flagship": "A shimmering violet rift yawns open directly across the bow of the *Hil Colish*, anchoring a doorway to the Creuss Gate wherever the flagship drops out of warp.", // Hil Colish (ghost flagship)
  "naalu_fighter": "Grown in resonant crystal vats on Druaa and wired directly to the pilot's optic nerve, Naalu interceptors bank in tight, silent unison before an opposing gunner can acquire a lock.", // Hybrid Crystal Fighter I (naalu fighter)
  "ghost_mech": "At the pilot's command, the Icarus Drive overloads its Shaleri core, folding local space inward and tearing open a fresh aperture straight across the sector.", // Icarus Drive (ghost mech)
  "naalu_mech_te": "Slender, silent, and tuned to the Collective's psychic chorus, the Iconoclast dismantles heavy enemy armor with surgical precision.", // Iconoclast TE (naalu mech)
  "xxcha_mech": "Even from high orbit, invading cruisers plot wide around the Indomitus. Its shoulder-mounted plasma rails reach well past the upper cloud deck.", // Indomitus (xxcha mech)
  "infantry": "Orbital fleets win the sky; rifle squads in the mud keep the world.", // Infantry I (generic infantry)
  "jolnar_flagship": "\"Route auxiliary reactor draw straight into the experimental arrays,\" the Hylar captain ordered over the bridge hum. \"If the containment coils hold, one clean strike will shear both dreadnoughts.\"", // J.N.S. Hylarim (jolnar flagship)
  "ralnel_flagship": "Packed with encrypted relay dishes and oversized sublight drives, the *Last Dispatch* delivers sealed orders, contraband cargo, and heavy broadsides on the same schedule.", // Last Dispatch (ralnel flagship)
  "arborec_mech": "Towering trunks of armored ironwood stride through the artillery smoke, projecting a planetary shield canopy while scattering fresh Letani spores across the churned earth.", // Letani Behemoth (arborec mech)
  "arborec_infantry": "Rooted in the Symphony and grown from the damp soil of Nestphar, a Letani Warrior advances without hesitation and takes root wherever its sap spills.", // Letani Warrior I (arborec infantry)
  "ralnel_destroyer": "Compact enough to slip past heavy orbital batteries, the Linkship I feeds live targeting telemetry across the entire consortium squadron.", // Linkship I (ralnel destroyer)
  "xxcha_flagship": "Elder Qanoj prefers the council chamber to the battlefield, yet the long-range plasma rails of the *Loncara Ssodu* keep every border treaty intact.", // Loncara Ssodu (xxcha flagship)
  "naalu_flagship": "From the gilded command spire of the *Matriarch*, the Collective's telepaths guide waves of crystal interceptors straight down through the atmosphere to strike ground garrisons.", // Matriarch (naalu flagship)
  "nomad_flagship": "Scorch marks from weapons not yet invented line the *Memoria*'s hull. Its flak pods track incoming fighter wings before they even clear their carrier's launch tubes.", // Memoria I (nomad flagship)
  "mentak_mech": "Welded from salvaged Letnev armor plates in the yards of Moll Primus, the Moll Terminus was built to crack Barony strongpoints using their own steel.", // Moll Terminus (mentak mech)
  "nekro_mech": "UNIT.DESGN: MORDRED // DIRECTIVE: TERMINATE.\nORGANIC INFANTRY LOCATED. DEPLOYING THERMAL LANCES.", // Mordred (nekro mech)
  "yin_mech": "Named for the ashes scattered atop the Hills of Grace, Moyin's Ashes strides into the heaviest fire while its speakers echo the liturgy of Lucas across the trenches.", // Moyin's Ashes (yin mech)
  "keleres_mech": "An Omniopiares walker standing at a starport gate carries the full weight of a Council warrant—even if the pilot inside hasn't been paid in three months.", // Omniopiares (keleresm mech)
  "titans_flagship": "The *Ouranos* drifts into orbit with the slow weight of a basalt mountain, waking dormant orbital defenses beneath the crust below.", // Ouranos (titans flagship)
  "pds": "Concrete bunkers, planetary shields, and heavy cannons waiting for careless ships in low orbit.", // PDS I (generic pds)
  "hacan_mech": "The Emirates trust contracts, gold, and—when negotiations sour on the frontier—a Pride of Kenara parked beside the landing ramp.", // Pride of Kenara (hacan mech)
  "muaat_warsun": "Rough-welded and radiating enough thermal glare to blind standard optics, the Prototype War Sun still boils an ocean dry the moment its main aperture opens.", // Prototype War Sun I (muaat warsun)
  "nomad_mech": "Nobody knows which century built the Quantum Manipulator, only that shots fired at it have an uncanny habit of missing by inches.", // Quantum Manipulator (nomad mech)
  "argent_flagship": "Golden wings sweep back along the *Quetzecoatl*, blinding planetary defense grids across the sector.", // Quetzecoatl (argent flagship)
  "crimson_flagship": "\"Cut the transponders,\" the rebel captain whispered. \"Tonight, the *Quietus* closes the lane.\"", // Quietus (crimson flagship)
  "cabal_mech": "Flesh-weaving tendrils drag broken walkers and fallen infantry straight back into the Cabal's rift, feeding the dimensional tear from the battlefield itself.", // Reanimator (cabal mech)
  "winnu_mech": "Cast in the likeness of the ancient Lazax palace guard, the Reclaimer plants automated defense pylons and orbital beacons on every world the Winnu reclaim.", // Reclaimer (winnu mech)
  "crimson_mech": "Scarred by a dozen failed uprisings and welded back together in hidden asteroid hangars, the Revenant steps off the drop-ramp with its plasma cutters already hot.", // Revenant (crimson mech)
  "winnu_flagship": "Forged in the shipyards of the First Empire, the *Salai Sai Corian* never retreats from an outnumbered fight—the larger the enemy fleet, the fiercer its ancient batteries burn.", // Salai Sai Corian (winnu flagship)
  "titans_cruiser": "Weathered stone plating wrapped around an ancient fusion core, the Saturn Engine I crosses contested sectors at flank speed with troops sealed inside its spine.", // Saturn Engine I (titans cruiser)
  "saar_mech": "Built from salvaged titanium and outfitted with industrial plasma torches, the Scavenger Zeta dismantles enemy bunkers and hauls the scrap straight back to the floating factories.", // Scavenger Zeta (saar mech)
  "jolnar_mech": "Overlapping barrier domes rise from the Shield Paling's dorsal emitter, letting fragile Hylar squads hold a trench line under heavy bombardment.", // Shield Paling (jolnar mech)
  "saar_flagship": "Scarred by a hundred asteroid belts and bristling with flak barrels, the *Son of Ragh* fills the forward arc with white-hot shrapnel.", // Son of Ragh (saar flagship)
  "spacedock": "Zero-gravity slipways and fuel spheres ringing every settled world.", // Space Dock I (generic spacedock)
  "sol_infantry": "First through the cloud deck and last off the ridge. When the Federation commits Spec Ops to a frontier world, the garrison digs in for good.", // Spec Ops I (sol infantry)
  "mahact_mech": "Wielding crackling genetic disruption staves, a Starlancer strips enemy officers of their command codes before the assault can even begin.", // Starlancer (mahact mech)
  "argent_destroyer": "Gull-winged and flown by zealots who never break formation, Strike Wing Alpha I clears the fighter screen and drops ground troops in a single pass.", // Strike Wing Alpha I (argent destroyer)
  "l1z1x_dreadnought": "Black durasteel, red optical arrays, and ventral bombardment rails built to crack fortified cities from high orbit.", // Super Dreadnought I (l1z1x dreadnought)
  "nekro_flagship": "UNIT.DESGN: THE.ALASTOR // DIRECTIVE: REPURPOSE.\nGROUND ASSETS TRANSFERRED TO ORBITAL COMBAT MATRIX. EXPENDABILITY: TOTAL.", // The Alastor (nekro flagship)
  "bastion_flagship": "Through the orbital smoke above Ordinian, the white-hulled *Egeiro* held high station, its steady transponder signal visible from every trench below.", // The Egeiro (bastion flagship)
  "muaat_flagship": "\"Stoke the crucibles and open the ventral bays!\" The *Inferno* drifted through the blockade like a furnace, casting fresh cruisers straight into the crossfire.", // The Inferno (muaat flagship)
  "cabal_flagship": "Jagged iron ribs and hungry violet light frame the prow of the *Terror Between*, pulling crippled ships straight into its maw.", // The Terror Between (cabal flagship)
  "sardakk_mech": "Powered armor bolted straight onto N'orr chitin turns every Valkyrie Exoskeleton into a roaring engine of close-quarters ruin, venting reactive shrapnel every time its plating takes a hit.", // Valkyrie Exoskeleton (sardakk mech)
  "yin_flagship": "\"Set the reactor to manual override and seal the bridge bulkhead,\" the Yin captain told his helmsman. \"Let the *Van Hauge* light the way for our brothers.\"", // Van Hauge (yin flagship)
  "firmament_mech": "Low-profile and coated in thermal baffles, the Viper EX-23 slips past perimeter sensors long before the night watch changes.", // Viper EX-23 (firmament mech)
  "obsidian_mech": "Cold iron, dark lenses, and no survivors left to file a report.", // Viper Hollow (obsidian mech)
  "naaz_flagship": "Above every Alliance landing zone hangs the *Visz El Vir*, coordinating Rokha artillery and Naaz recon teams from high orbit.", // Visz El Vir (naaz flagship)
  "warsun": "Half a moon of armor wrapped around a captive stellar furnace, a War Sun turns an entire planetary defense grid to ash in a single sustained sweep.", // War Sun (generic warsun)
  "empyrean_mech": "Silent sentinels stationed at the edge of the dark, Watchers sense an incoming ambush and dismantle rival contingencies before the first shot is fired.", // Watcher (empyrean mech)
  "hacan_flagship": "Treasury-grade catalyst crates emptied straight into the fuel condensers as the *Wrath of Kenara* brought its main batteries online, reminding the Core that the Emirates guard their own lanes.", // Wrath of Kenara (hacan flagship)
  "yssaril_flagship": "No sensor grid in the sector holds a lock on the *Y'sia Y'ssrila* for long. It glides straight through enemy blockades without tripping a single perimeter buoy.", // Y'sia Y'ssrila (yssaril flagship)
  "naaz_mech_space": "Mag-boots kicked off the carrier's dorsal hull, and the Z-Grav Eidolon's maneuvering thrusters flared blue as it banked straight into the dogfight.", // Z-Grav Eidolon (naaz mech)
  "sol_mech": "Heavy, loud, and bolted together in the orbital yards of Jord. When a ZS Thunderbolt M2 punches through the cloud deck, the Federation infantry advances behind its armor.", // ZS Thunderbolt M2 (sol mech)
};

/** Action cards. */
const actionCard: LoreMap = {
  "abs": "The images depicted a race that Rin had never seen before. Curious. Could it be that this was a race that was exterminated by the Lazax?", // Ancient Burial Sites
  "arch_expedition": "Hiari pressed the activation glyphs, and the ancient door hissed open. As she stepped into the pitch-black interior of the Mahact tomb, she felt a shiver of anticipation. Perhaps, finally, she would find the Codex.", // Archaeological Expedition
  "assassin": "With a sickening crunch of bone and metal, unit.desgn.FLAYESH extracted its stinger from the blood-drenched skull of the Jol-Nar councilor.", // Assassinate Representative
  "blackmarketdealing": "A chill went up Riad's spine as the Empyrean extended a clawed hand, a small black box floating in their palm, sucking up all the light and life in the room.", // Black Market Dealings
  "blitz": "\"T-these weren't meant to be used like this. T-this is a t-terrible idea.\" Tai mumbled, wringing his hands. \"Well 'course it is,\" Dart grinned, slamming his fist down on the release lock. \"But we've got about sixty kilotons of 'surprise' and nothing to lose!\"", // Blitz
  "bribery": "\"We think that this initiative would spell disaster for the galaxy, not just the Creuss,\" Taivra said, quietly slipping Z'eu an envelope. \"Don't you agree?\"", // Bribery
  "brilliance": "Crocoan gently stroked the bloodied feathers of the screeching cir-le-sh. Such a beautiful song. At last, he'd cracked the code. Soon, Goranthis would be filled with a chorus of such soulful music.", // Brilliance
  "bunker": "Elder Junn crossed his arms and steadied his breathing. The bombs could not reach them, not this far down. At least, that is what the soldiers had told him.", // Bunker
  "confounding": "\"Unfortunately,\" Cinnabian said in a level voice, \"the Galactic Council requires the dispute be arbitrated by a truly neutral party. As the Titans were still slumbering when your war began, we will oversee your negotiations... instead of your friends on Jord.\"", // Confounding Legal Text
  "confusing": "Somehow, even after the Council had adjourned, none of them were any closer to understanding the strange and confusing events of the day.", // Confusing Legal Text
  "const_rider": "The vote was nearly unanimous. The council would provide funding for the restoration. Ciel was furious.", // Construction Rider
  "counterstroke": "\"That's the thing about loyalty - \" Viktor mused, turning one of the pieces backward, facing its own side. \"It can be bought.\"", // Counterstroke
  "coup": "Artuno shoved the slug pistol into Huro's face as armored mercenaries stormed into the office. \"I'm afraid the station's undergoing a change in management.\"", // Coup d'Etat
  "courageous": "Coughing up blood and covered in burns, Havvat collapsed against the rapidly overheating ship core. She smiled. She would be remembered.", // Courageous to the End
  "crashlanding": "The Long Fall spiraled toward the surface of the rocky planet. Living up to its name, Connor thought dryly.", // Crash Landing
  "cripple": "Titanic vines burst forth from the ground, wrapping themselves around the system's primary firing cylinder, breaking it free from its moorings, and bringing it crashing down upon the installation below.", // Cripple Defenses
  "crisis": "4X41A \"Apollo\" shrieked in the skies over Ordinian. Blazing shards of metal and fire rained down upon the planet's surface—the remains of Nekro hulls whose atoms were undergoing a rapid and violent disintegration.", // Crisis
  "deadly_plot": "The hooded envoy erupted into a nightmare of black metal, lunging at the shocked diplomats.", // Deadly Plot
  "decoy": "Enemy fire lashed the abandoned positions on the ridgeline as Trilossa's flock slipped unseen around their flanks.", // Decoy Operation
  "diplo_rider": "Ciel evaluated the other senators. Weak, all of them. This was his game to win.", // Diplomacy Rider
  "dp1": "The Arborec emissary leaned close, and Brother Milor flinched at the faint whiff of decay. \"You do not understand,\" Dirzuga Ohao rasped. \"You must support this measure.\"", // Diplomatic Pressure
  "dp2": "Brother Milor shook his head. \"The Brotherhood cannot support your war against this extra-dimensional threat.\" Dirzuga Ohao raised an eyebrow. \"Are you certain?\"", // Diplomatic Pressure
  "dp3": "\"It would be unfortunate,\" the Arborec Dirzuga said, \"if your supplies of diraxium were to dry up. How would your fleet defend you if we stopped supplying its fuel?\"", // Diplomatic Pressure
  "dp4": "\"Damn you!\" Brother Milor hissed. \"You leave us no choice but to fight in your war.\" Dirzuga Ohao smiled, dead skin stretching over her teeth.", // Diplomatic Pressure
  "dh1": "There it was! An opening! Neekuaq gestured wildly, a rare display for one normally quite reserved. \"Fire the main battery!\"", // Direct Hit
  "dh2": "The Loncara Ssodu's main battery flared to life, firing a volley directly into the flickering starboard shield of the Letnev dreadnought.", // Direct Hit
  "dh3": "For a moment, it looked as if the dreadnought's shield would hold, but a moment later, the ship began to come apart where the attack had pierced its hull.", // Direct Hit
  "dh4": "Neekuaq watched, satisfied, as the ship was wracked by a series of explosions from within, huge armored plates and other debris hurtling off into the darkness.", // Direct Hit
  "disable": "\"Ssruu has met their systems and fixed them.\" Ssruu dropped a handful of ripped wires and broken circuitry on the pedestal before Q'uesh Sish. \"He will await his next task aboard his ship.\"", // Disable
  "distinguished": "Elder Junn was a wonder to behold. He knew the name of every senator, made small talk effortlessly, and commanded attention when he spoke. Magmus hated everything about him.", // Distinguished Councilor
  "divert_funding": "\"I am sorry, Academician,\" Arbiter Berekon shrugged. \"I am sure psychoarchaeology is an interesting subject, but the supreme leader feels your budget would be better spent on more militaristic research.\"", // Divert Funding
  "economic_initiative": "Large sums of Hacan currency flowed freely into the project, and somehow, defying all logic, the returns were even greater.", // Economic Initiative
  "emergency": "\"What do you mean 'It's fine!?'\" Dahla said, nearly tripping over a damaged bulkhead as the ship rocked from the explosive barrage.", // Emergency Repairs
  "exchangeprogram": "\"Madness,\" Magmus thought to himself. A city. Under water. Absurd.", // Exchange Program
  "experimental": "\"Arm the relay!\" Mendosa bared his fangs. \"The Saar will not submit!\"", // Experimental Battlestation
  "probe": "With a dull thud, the probe shot from the cruiser and accelerated into the writhing maelstrom of the gravity rift. Admiral DeLouis paced on the bridge. Hopefully, this time the probe would return.", // Exploration Probe
  "extremeduress": "Kan Kip Rel tugged nervously at his collar, fingering the explosive device he knew was there.", // Extreme Duress
  "f_conscription": "T'esla grinned as her shimmering vessel lifted off the flight deck - at last, that damned Viscount would experience the superiority of Naalu dogfighting. \"Get ready,\" she hissed into the comms.", // Fighter Conscription
  "f_prototype": "Suffi vaulted excitedly off the prototype's sleek, azure wing, landing effortlessly in its cockpit. \"Let's see those damn snakes keep up with us now!\"", // Fighter Prototype
  "fire_team": "Grinning, Jael spun towards the familiar noise of heavy boots hitting the ground. Backup had arrived.", // Fire Team
  "fs1": "Mendosa smirked. \"Don't ye fret now, girl. It sounds like ye've got somewhere ta be in a hurry, and it just se happens that I ken get ye there right quick.\"", // Flank Speed
  "fs2": "There was a low-pitched hum throughout the station and the gigantic, bulky constructions on the hull spat blue flame. Massive ion thrusters! So this was how the Saar moved the damned things.", // Flank Speed
  "fs3": "Mendosa grinned at the young Mentak pilot's astonishment. \"Mobility-the Clan's greatest strength. Ye'd be amazed at how fast this thing ken go.\"", // Flank Speed
  "fs4": "With a sound like thunder and a flash of neon blue light, the thrusters accelerated full bore, nearly knocking Suffi off her feet.", // Flank Speed
  "f_researched": "Stunned, Rin looked over the data, scarcely able to believe what she was seeing. It was nothing short of a major breakthrough. The Headmaster would be pleased.", // Focused Research
  "fsb": "All eyes turned toward the darkening skies as the only surviving supply truck rolled through the gates. \"Get these checked in and send the last shipment to our allies!\" Harrugh yelled over the din of the engines.", // Forward Supply Base
  "f_deployment": "The soldiers poured fire on the writhing mass, but as each tendril vaporized, two more took its place. Panic wormed into the troopers' minds; was the creature growing?", // Frontline Deployment
  "ghost_ship": "Reports of Creuss vessels sighted in the area had surely been exaggerated. After all, the Creuss had no business this far from the Shaleri passage, and usually kept to themselves.", // Ghost Ship
  "ghost_squad": "The L1 advance team was expecting to find the outpost abandoned. What they found - unfortunately for them - was Connor.", // Ghost Squad
  "hack": "YOUR [NULL ID] STATELY GAME WILL BE FOR NAUGHT<< [VAR:42687] ORDER WILL ARISE FROM [VAR:89001] CHAOS<< IT IS OUR HAND THAT CONTROLS THE OUTCOME", // Hack Election
  "harness": "\"Manipulating the cosmos was a power reserved for the gods.\" Rowl spat at the ground as his contraption whirred to life. \"Not anymore.\"", // Harness Energy
  "imp_rider": "In a sweeping victory that surprised absolutely no one, the Winnu representative singlehandedly elected himself to oversee the analysis of a recently uncovered Lazax data cache.", // Imperial Rider
  "impersonation": "\"Also,\" Connor continued, bemused. \"Someone just handed me this as I was leaving. I think it was meant for our dear friend Sucaban. We should be able to put it to good use.\"", // Impersonation
  "silence_space": "The Barony ships seemed to defy reality, bending light around them at impossible angles - naught but inky-black contours could be seen.", // In The Silence Of Space
  "industrial_initiative": "The Gashlai reactors proved to be extremely effective. With the conversion rate practically doubled, the factories' output was immense.", // Industrial Initiative
  "infiltrate": "The 1X had scarcely interfaced with the mainframe before it belonged to them completely.", // Infiltrate
  "insider": "M'aban yawned. Another filibuster. Politics could be so flavorless at times. Besides, she already knew how this one was going to turn out. Not well. Not well at all...", // Insider Information
  "insub": "Kilik had never been particularly good at following orders. It only seemed natural to get paid for exercising that trait, as long as she didn't think too hard about where the money was coming from.", // Insubordination
  "intercept": "The space before the fleeing ship shimmered and warped, revealing the bow of the Y'sia Y'ssrila bearing down on its position. There would be no escape today.", // Intercept
  "lead_rider": "Rev's impassioned speech stunned the other councilors. Perhaps there was more to these humans than they had initially thought.", // Leadership Rider
  "lieinwait": "Suffi sauntered toward the huddle of paralyzed Hylar, whistling and twirling her pistols as she walked. \"I'll be taking these,\" she said, flashing a grin, and snatched the humming data drives from each of them in turn.", // Lie in Wait
  "lost_star": "The ship's sensors showed that the ancient star-map had somehow led them beyond the Mahact plateau.", // Lost Star Chart
  "lucky": "The missile - an insignificant spark against the darkness - struck the hull of the dreadnought. Moments later, the starboard flank erupted in flames.", // Lucky Shot
  "mjets1": "Something was wrong. T'esla sensed a flicker of movement on the planet's surface, followed by a faint glint of light. Reflexively, she veered her fighter to the side - an action that saved her life.", // Maneuvering Jets
  "mjets2": "The fighter's thruster boosted her just out of the cannon's firing solution, and a metal slug the size of a building rocketed past her crystalline ship.", // Maneuvering Jets
  "mjets3": "T'esla breathed a sigh of relief as the massive slug disappeared into the distance. A touch slower and she would have been annihilated.", // Maneuvering Jets
  "mjets4": "The flickering red warning lights on her control panel reflected in her scales as she regained her composure. \"Well,\" she said aloud. \"Zat was close.\"", // Maneuvering Jets
  "investments": "\"But my good fellow,\" the envoy sputtered. \"Surely you can't expect me to agree to those prices!\" Durruq leaned in close. \"Check again. You may find your goods are trading for less than you think.\"", // Manipulate Investments
  "master_plan": "Viktor laced his long fingers with a wicked smile. Unlenn would be proud. The tactician's reputation was well-earned; even pawns could unseat kings.", // Master Plan
  "mercenarycontract": "\"Just sign right 'ere - yep, right below the smeared blood. You got it, champ, get at 'em.\"", // Mercenary Contract
  "mining_initiative": "To support its voracious war machine, the N'orr empire cracked the planet's crust and began mining its very core.", // Mining Initiative
  "mb1": "Harrugh stood before his warriors, searching for the words that would express the pride that swelled within him.", // Morale Boost
  "mb2": "\"We have done the impossible. I am proud to call you my brothers. My equals. My betters.\" Harrugh's whiskers bristled with energy as he spoke.", // Morale Boost
  "mb3": "\"Today we turn these invaders to ash and take back what is ours!\" Harrugh paused, noting the murmurs of approval rippling through the ranks.", // Morale Boost
  "mb4": "The whispering gradually died down and his warriors watched Harrugh expectantly. Every muscle in his body tensed, and he thrust his gyro-spear skyward. \"For Kenara!\"", // Morale Boost
  "nav_suite": "\"The field is too thick!\" Sikosk gasped. Trrakan's plume flared. \"Not for me, and not for Iruth.\" A flick of his talon, and the destroyer flipped and dove for the asteroid field.", // Nav Suite
  "overrule": "Treilla absentmindedly smiled at the audacity of the newly promoted commander. Making waves like this - he'd likely be dead or demoted within a day or two. Still, she found the posturing...amusing.", // Overrule
  "parley": "The human admiral returned to his ship, struggling to remember precisely how his meeting with the Collective had gone.", // Parley
  "piratecontract1": "Suffi accepted the contract, swearing her solemn vow that she would see the viceroy's daughter kidnapped and held for ransom by the day's end.", // Pirate Contract
  "piratecontract2": "Suffi accepted the contract, swearing her solemn vow as one of Mogar's Raiders that she would be loyal to the crew above all else.", // Pirate Contract
  "piratecontract3": "Suffi accepted the contract, swearing her solemn vow as a member of the Shadowscald that the job would be completed, one way or another.", // Pirate Contract
  "piratecontract4": "Satisfied, Suffi cashed in her contracts, wondering how long it would take any of them to notice she was gone. After it was much too late, with any luck.", // Pirate Contract
  "piratefleet": "Felix rubbed his temples as the pirates - well, the other pirates - blipped one by one on the ship's scanner. It was going to be a very long day.", // Pirate Fleet
  "plagiarize": "The Yssaril spies handed over their prize to Connor, who in turn passed it to the Sol engineers with a grim smile. \"Now then, boys,\" he said, one hand on his rifle, \"about those loose ends...\"", // Plagiarize
  "plague": "The letani dipped a mossy limb beneath the surface of the reservoir, feeling the flow of the particles within, shifting them, changing them into something different. Something dangerous.", // Plague
  "stability": "The Winnu councilor breathed a sigh of relief. This opportunity would not be wasted. The peace of the Lazax was within grasp.", // Political Stability
  "politic_rider": "The Dirzuga had managed to negotiate themselves into a position of power amongst the other councilors, all of whom still looked terribly uncomfortable in their presence.", // Politics Rider
  "disgrace": "In the months that followed the report, the Council was quick to censure the Jol-Nar for their unethical practices.", // Public Disgrace
  "puppetsonastring": "A red light flashed as the shattered remains of UNIT.DSGN.ASTAROTH, once thought destroyed, came once more to life. \"YOU THOUGHT. YOU BELIEVED YOUR VICTORY SECURE. BUT YOU WERE WRONG.\"", // Puppets on a String
  "rally": "The Federation advance would not be halted - not today. Claire set her broadcast to play on all open channels. She began, her voice fierce and unwavering \"Friends! On this day, our names shall be inscribed in the pages of legend!\"", // Rally
  "meltdown": "Flames engulfed the shipyard, a vortex of fire and shrapnel that left nothing untouched.", // Reactor Meltdown
  "refit": "Sek'kus leapt from the trenches, the plasma projectors on her Valkyrie exoskeleton howling as they scoured the field ahead of her.", // Refit Troops
  "reflective": "Prit scrambled up Hesh's shoulder, gleefully clapping as the entropic shielding tore the mercenary cruisers apart.", // Reflective Shielding
  "reparations": "Gila oversaw the reconstruction of the Hacan outpost, but neglected to inform the N'orr representative that the damage was not nearly as severe as he was led to believe.", // Reparations
  "repeal": "Eventually, the N'orr diplomat came to an agreement with Hacan Garrus, and the embargo was repealed. Still, he couldn't shake the feeling that Garrus had gotten the better end of the deal.", // Repeal Law
  "rescue": "\"Hold on...\" Tuck pleaded. \"We are coming. Hold on, please...\"", // Rescue
  "reveal_prototype": "Varish and Cole completed the final linkages, activating the field harvester. The cruiser's beams roared with renewed power, cutting through the enemy ship.", // Reveal Prototype
  "reverse_engineer": "Xuange spread their hands over the captured harvester. Mirroring their careful gestures, dark energy fields unfolded and began delicately disassembling the device.", // Reverse Engineer
  "messiah": "Harrugh stood atop the dunes, looking down at the thousands of Hacan warriors mustered below. Gathering his strength, he let loose a mighty roar, the will of his people throughout the galaxy echoing forth from within.", // Rise of a Messiah
  "rout": "Vuil'raith fleshships swarmed the weary defenders, sending unease and panic sweeping through the telepathic links. But Z'eu projected a powerful feeling of calm, and the Naalu fighters began to drive the Cabal back toward the rift.", // Rout
  "sabo1": "Q'uesh Sish tapped her claws impatiently. \"You were sssaying?\" But the confused Jol-Nar envoy stood silent. It was as if the words had escaped his thoughts entirely.", // Sabotage
  "sabo2": "trjn.desgn.ALIZARIN introduced itself to each data node, incorporating them into its platform, expunging any data it deemed a threat to the Virus.", // Sabotage
  "sabo3": "unit.desgn.BEELZEBUL followed the group of men through the winding hallways until they stopped at an intersection. Investigators would later find its cracked oculus at the center of a smoking crater, singed, but still functional.", // Sabotage
  "sabo4": "Unlenn smashed a clenched fist into the bulkhead, green eyes ablaze with rage. The entire plan had been turned on its head. Such incompetence was unfathomable.", // Sabotage
  "salvage": "When the Coalition raiders had finally returned to their ships, scarcely a bolt remained to salvage from the destroyed vessel.", // Salvage
  "sanction": "Two can play at this game.", // Sanction
  "scramble": "\"I will not accept this from that worthless scum!\" Feng growled as his enigmatic companion interfaced with the ship's nav suite. The Memoria's position flickered and shifted, and the blast flashed harmlessly by.", // Scramble Frequency
  "scuttle": "Rear Admiral Farran saluted as he watched the blasted starship being towed to the scrap yard. \"You served me well,\" he whispered. \"Now you can serve the Barony once more.\"", // Scuttle
  "seize": "Armored dropships crashed into the main dock. Hatches blew open, and Captain Mentarion and her commando raider charged into the facility's heart.", // Seize Artifact
  "sh1": "T'ro stared unflinching at the incoming barrage through the bridge's observation deck. The shield would hold.", // Shields Holding
  "sh2": "The blast from the enemy's main cannon slammed into the space in front of the warship, splitting into two streams across the bow.", // Shields Holding
  "sh3": "The ship's shields sizzled and sparked but remained active despite the heavy assault.", // Shields Holding
  "sh4": "As the assault died down and it became clear that the ship sustained no major damage, T'ro clicked his mandibles in anticipation. \"Return fire!\"", // Shields Holding
  "jamming": "Meian was practically aglow, wisps of her ether crackling with delight. It was amazing what could be achieved with a well-timed electromagnetic discharge.", // Signal Jamming
  "s_retreat1": "In an instant, the Sol fleet vanished from the Barony's scanners.", // Skilled Retreat
  "s_retreat2": "The Creuss fleet was gone. No trace remained of their passage.", // Skilled Retreat
  "s_retreat3": "T'ro gave the order, and the entire fleet withdrew without question.", // Skilled Retreat
  "s_retreat4": "\"We have no choice, captain.\" Ciel looked nervous. \"We must retreat.\"", // Skilled Retreat
  "solar_flare": "Meian braced for combat as the fleet entered the Ordinian system, but there were no Valefar droneships waiting to meet them. The solar flare gambit had succeeded - they were completely undetected.", // Solar Flare
  "spy": "\"I'm no spy,\" Connor said, casually stuffing the data drives into his pack. \"Now, how can I get out of here without being seen?\"", // Spy
  "strategize1": "Kyver stared Mathis in the eye, unblinking. For a time, neither made a move. The greens and browns of Kyver's eyes were impassive. They betrayed nothing of his intent. Nothing of his past or his future. They were but windows to the wild, unforgiving jungles of Retillion.", // Strategize
  "strategize2": "Sweat dripped down Mathis' brow. To show weakness now would mean defeat. Death would be preferable to that. But then, as if the divine providence of the Lazax were within her, she saw something she had overlooked. An opening! Her hand darted forward as she made her play. She smirked.", // Strategize
  "strategize3": "Strategy. What meaning could be derived from the word, what flesh could be sucked clean off its bones? There was a spark, almost like remembering, but it faded. Violently.", // Strategize
  "strategize4": "No, there would be no strategy here, only hunger. Life, blood, love, life, fear, fear, fear. Let the ants mill about with their strategies. No strategy would avail them today.", // Strategize
  "summit": "At the end of the twelfth day, Rev returned home from the summit in New Moscow feeling physically exhausted and mentally drained. But she was also satisfied. They had a plan - finally - and it was a good plan.", // Summit
  "tactical": "A6's red eyes flickered with activity, and a string of numbers flashed briefly across the screen before he spoke. \"Bombardment complete. All enemy installations have been neutralized.\"", // Tactical Bombardment
  "tech_rider": "The Council granted the Yin funding to research an effective countermeasure to combat the virus. After all, keeping the Yin occupied with the virus meant killing two birds with one stone.", // Technology Rider
  "trade_rider": "The Letnev councilor begrudgingly accepted the N'orr's core mining contract, if only so that the \"gracious\" Hacan senator didn't secure yet another source of income for his clan.", // Trade Rider
  "unexpected": "M'aban's voice was barely a whisper, cracking as hundreds of flashing lights appeared on her scanner. \"We've been tricked.\"", // Unexpected Action
  "unstable": "Another quake shook the planet, and a wave of dirt and rock rose up to swallow the Tekklar legion.", // Unstable Planet
  "upgrade": "\"More guns?\" Connor shook his head. \"Not more guns. Let's try something bigger.\"", // Upgrade
  "uprising": "Harrugh leapt down from the ledge, gyro-spear blazing in the sunlight. In front, the L1Z1X began to take notice. Behind him, his warriors stood at the ready. Win or lose, this would be the end.", // Uprising
  "veto": "Magmus batted the now charred corpse aside with the back of his golden gauntlet. \"The Muaat reject your proposal.\"", // Veto
  "veto3": "\"The motion dies here,\" Elder Qanoj declared, laying the silver seal of Archon Ren across the Speaker's podium. \"Bring something worthy of the chamber tomorrow.\"", // Veto
  "veto4": "Suffi An tore the proposed charter cleanly down the middle and tossed both halves onto the voting table. \"Next item on the docket, councilors.\"", // Veto
  "war_effort": "The N'orr may not be the most proficient shipwrights, but the willingness of their citizens to do their part far exceeds that of the other great races.", // War Effort
  "war_machine1": "\"This would take weeks to replace if you had run it backwards,\" Varish called as she rotated the massive capacitor bank. \"Okay, fire it up.\"", // War Machine
  "war_machine2": "The station vibrated as the device sputtered to life, emitting a high-pitched buzz to Varish's ears. \"Micro-wormholes are cycling at 19 kilohertz,\" Cole read. \"The entropic field tap's stable.\"", // War Machine
  "war_machine3": "The station's production facilities spooled up to new intensities, lights flaring as the assembly line drones increased their speeds to keep up.", // War Machine
  "war_machine4": "\"Varish, let the Commanders know they can contact the Tetrarchy. Tell them the fighter squadron assembly will be done ahead of schedule, and under budget.\"", // War Machine
  "war_machinell": "\"This would take weeks to replace if you had run it backwards,\" Varish called as she rotated the massive capacitor bank. \"Okay, fire it up.\"", // War Machine
  "war_rider": "Elder Junn sighed. \"Disarmament, it seems, has fallen out of fashion in these dark days.\"", // Warfare Rider
  "waylay": "The destroyers sprayed fire with their secondary batteries as they advanced. The Mahact dreadnought began to list, fire and atmosphere gushing from a thousand tiny wounds.", // Waylay
};

/** Relics. */
const relic: LoreMap = {
  "bookoflatvinia": "A collector's item of incalculable value, none have been able to unlock its secrets - assuming its contents aren't just the ravings of a madwoman.", // Book of Latvinia
  "circletofthevoid": "Xuange touched the jeweled circlet that sat upon their temple. The pride of the Archive. Knowledge of the stars, passed down from the First, fated for the Last.", // Circlet of the Void
  "dominusorb": "Goldos hoisted the ivory orb at the head of their army. At once, the weariness that filled the bodies and minds of each soldier vanished. They strode forth as if fresh from a week's rest.", // Dominus Orb
  "dynamiscore": "Dart and Tai stood, mesmerized by the swirling mass. Neither had any idea what it was, but both were fairly sure they were about to retire.", // Dynamis Core
  "heartofixth": "\"It should be impossible.\" Feng glanced sidelong at his compatriot. The Thundarian merely stared ahead, as if he did not hear. Feng snorted. \"One day I mean to know the source of this so-called power of yours.\"", // Heart of Ixth
  "titanprototype": "\"I have no name. Perhaps I shall be Dart II,\" the little Titan said, studying the Naaz archaeologist solemnly. \"How about Junior instead?\" Dart offered. \"Yes,\" it nodded. \"I like that name—and I would also like to come with you.\"", // JR-XS455-O
  "lightrailordnance": "A single sparkle was the only warning the Yin fleet had before a massive hole had been punched through the hull of the Van Hauge.\nThen, searing light.", // Lightrail Ordnance
  "mawofworlds": "No larger than a carrier, the spherical lattice held a captive singularity at its heart. As they dumped the planet's entire energy grid into its core, the black hole began to spin, the complex logic-circuitry along the lattice slowly coming to life.", // Maw of Worlds
  "metalivoidarmaments": "The Metali, Empyrean artificers of legend, were said to have created weapons that harnessed the power of space itself.", // Metali Void Armaments
  "metalivoidshielding": "Capable of more than destruction, the Metali also wrapped their ships in nigh-indestructible plating unable to be replicated using today's methods.", // Metali Void Shielding
  "nanoforge": "Intended to bring prosperity, the forge was twisted into an instrument of war.", // Nano-Forge
  "neuraloop": "Knowledge. Creation. Control. Have a wonderful day.", // Neuraloop
  "emelpar": "As the hilt began to fuse with the flesh of her hand, she worried that she should set the scepter aside. But the whispered suggestions in her mind were too valuable and insightful to seriously consider such a rash and illogical act.", // Scepter of Emelpar
  "shard": "\"What power does a broken piece of the Throne of Emperors hold? To me, none. But to everyone else...\"", // Shard of the Throne
  "stellarconverter": "A power great enough to envelop a star, such that its energies might be concentrated...and scattered.", // Stellar Converter
  "codex": "No single tome could contain the collected knowledge of millennia of rulers. Thus, the last Emperor built a massive cruiser, its holds bulging with crystal info-matrices. It roams the outer reaches of the Mecatol system, awaiting a summons that will never come.", // The Codex
  "emphidia": "The machines of the forgotten throne-world could only be controlled through the data-impulses of the black-barbed crown.", // The Crown of Emphidia
  "thalnos": "A cloud of satellites spewed from the dreadnought's hull, drifting into a halo around the vessel. The battle seemed to pause for one long moment, before the drones' weapons flared, unleashing beams of energy in all directions.", // The Crown of Thalnos
  "obsidian": "The inky blackness of the blade evoked feelings of discomfort and nausea in all who saw it. All but Sharsiss. It whispered to him promises of power. Promises of a reckoning that would see the Collective unmade. \"Good,\" he thought. \"Let them burn.\"", // The Obsidian
  "prophetstears": "\"So you're going to drink a vial of murky liquid we found in a stasis vault on a dead world because you think it's the concentrated genetic essence of an entire species' most brilliant minds...and you think *I'm* being irrational?\"", // The Prophet's Tears
  "quantumcore": "The core burned with the heat of a thousand stars, connections forming and reforming a thousand times per second.", // The Quantumcore
  "thesilverflame": "Shen're Ix Ianovar. The flame beyond time and space.", // The Silver Flame
  "thetriad": "The light that shines without reflects the dark it harbors within.", // The Triad
};

/** Exploration cards. */
const exploration: LoreMap = {
  "aw1": "\"Looks like some smuggler hid their shipment of gerr root here and forgot to pick it up.\"", // Abandoned Warehouses
  "aw2": "Suffi An drifted into the derelict orbital and brushed her suited hand across the inner hatch controls. A light glowed, and she smiled. The stasis seals were still operational.", // Abandoned Warehouses
  "aw3": "The storage silos had been half buried in sand dunes, sealed enviro-doors hiding the stockpiles within.", // Abandoned Warehouses
  "aw4": "Far beneath the storm-wracked seas, vast storage tanks drifted in the lightless depths.", // Abandoned Warehouses
  "biotic": "Surveyors hacking through the overgrown ridge found an intact conservatory with pressurized tanks still glowing pale green with pre-war specimens.", // Biotic Research Facility
  "cm1": "\"If we don't seal it now, this mine is going to erupt and spew those metals you want so badly across the entire continent!\"", // Core Mine
  "cm2": "The borehole was over a kilometer across. It seemed to stretch down forever, but Ilan could see a faint orange glow in its depths.", // Core Mine
  "cm3": "Without the proper machinery, a core mine can be a more hostile environment than a star's corona.", // Core Mine
  "crf1": "Half-buried beneath temple rubble, a tablet of veined marble still carried a Lazax royal seal from a house lost during the Twilight Wars.", // Cultural Relic Fragment
  "crf2": "\"Keep the brush steady,\" the archaeologist whispered as gold leaf flaked away from the relief. \"That crest belongs to a court older than Mecatol City.\"", // Cultural Relic Fragment
  "crf3": "A hollow bronze cylinder chimed softly when lifted from the silt, its surface etched with star charts for constellations no longer visible from this world.", // Cultural Relic Fragment
  "crf4": "Behind the collapsed masonry lay three rows of crystal scrolls, intact in dry air and written in a dialect only half-matched by Winnaran lexicons.", // Cultural Relic Fragment
  "crf5": "The carved funerary mask weighed next to nothing, cast in an iridescent alloy that shifted hue whenever anyone spoke near it.", // Cultural Relic Fragment
  "crf6": "Shattered mosaic tiles littered the dry basin, piecing together a map of ten vanished worlds and a crown split cleanly down the middle.", // Cultural Relic Fragment
  "crf7": "\"Don't touch the tuning fork,\" Tai warned too late; a single note rang out from the carved pedestal and echoed through the canyon for a full minute.", // Cultural Relic Fragment
  "crf8": "Wrapped in rotting velvet inside an iron coffer sat a signet ring sized for no living species, still caked with dried sealing wax.", // Cultural Relic Fragment
  "crf9": "Waterlogged frescoes along the sunken colonnade depicted Lazax heralds bearing the imperial signet before a forgotten frontier court.", // Cultural Relic Fragment
  "cybernetic": "Thermal scans picked up a massive power draw beneath the permafrost, leading the expedition down into silent rows of ancient server vaults.", // Cybernetic Research Facility
  "dw": "The *Best Guess* drifted through the debris. Layers of rock and...metal? It was all being held together by some kind of electric field—the same field that had hidden it from their scanners. With a growing sense of unease, they hastened their salvage.", // Dead World
  "dmz": "\"Power down the targeting grids,\" the captain ordered as the cruiser broke warp. \"Council neutrality beacons are active—any fleet that lands troops here forfeits its seat.\"", // Demilitarized Zone
  "dv1": "The flickering ion storm illuminated the hulk, its hull rent and torn by some monstrous force.", // Derelict Vessel
  "dv2": "Missing for fifty years, the *Errasthua* was found drifting off the Celder Nebula with her drive dead and every crewmember vanished.", // Derelict Vessel
  "ds": "", // Dyson Sphere
  "ed1": "A needle longer than a dreadnought but no wider than a landcar flew through the void, its surface glowing with a pale violet light.", // Enigmatic Device
  "ed2": "The silver pinwheel spun slowly in the midst of the nebula, each kilometer-long blade glittering faintly with reflected starlight.", // Enigmatic Device
  "ent": "Several destroyers, a light cruiser, and even a pair of Eidolons patrolled the field during major extraction operations. One could never be too careful.", // Entropic Field
  "exp1": "\"These cave networks stretch for hundreds of kilometers. It may take months to properly map them.\"", // Expedition
  "exp2": "\"We've lost two companies of scouts to whatever is in those canyons.\"", // Expedition
  "exp3": "The Eidolon screamed through the atmosphere, corrosive rain streaming harmlessly off the hull as it began its survey sweep.", // Expedition
  "frln1": "The Vexis Howlers were well-equipped with transports, powered armor, and even logistical support—everything a fledgling outpost needed to survive.", // Freelancers
  "frln2": "As part of the annexation agreement, local artisans would be well paid to lay the groundwork for military installations in the newly acquired territories.", // Freelancers
  "frln3": "Overseer Klix was known for hiring hundreds of freelancers and then \"forgetting\" to pay them once the bulk of the work was complete.", // Freelancers
  "fb1": "The Imperial Survey Corp outpost had been abandoned since the Twilight Wars, but the facilities had been built to last for millennia.", // Functioning Base
  "fb2": "The orbital distribution station proved easy to integrate into the fleet's growing logistical operation.", // Functioning Base
  "fb3": "The local defense forces abandoned their fortress as the first troop transports made planetfall, leaving it open to occupation.", // Functioning Base
  "fb4": "\"Yes commander, the base appears completely abandoned. No sign of what happened to the garrison.\"", // Functioning Base
  "gamma": "Old spacers would tell stories of a black gateway in the deep space beyond the outer Oort Cloud.", // Gamma Relay
  "gw": "The gravic sensors howled a warning. Ahead of the ship was a ring of twisted starlight, surrounding a sphere of utter darkness.", // Gamma Wormhole
  "hrf1": "The metallic shard had cooled inside a pocket of volcanic glass, still faintly warm to the touch through three layers of thermal gloves.", // Hazardous Relic Fragment
  "hrf2": "Dosimeters clicked wild around the basalt pillar until the salvage team pried a fractured core casing free from the frozen crust.", // Hazardous Relic Fragment
  "hrf3": "Acid sleet had eaten half the cliffside away, exposing a rib of blackened alloy that refused to pit or corrode.", // Hazardous Relic Fragment
  "hrf4": "\"Watch your step. The ash crust's hollow,\" the scout called out just before his boot broke through into a buried bunker ceiling.", // Hazardous Relic Fragment
  "hrf5": "A severed stone gauntlet jutted from the sulfur flats, its knuckles locked tight around an uncracked containment vial.", // Hazardous Relic Fragment
  "hrf6": "Lightning struck the same ridge twice while the survey crew winched a jagged shard of dark alloy out of the crater mud.", // Hazardous Relic Fragment
  "hrf7": "Buried beneath three meters of irradiated slag, the ancient bulkhead plate still bore intact circuit traces pulsing with faint copper light.", // Hazardous Relic Fragment
  "irf1": "Among the rusted ore crushers lay an unmarked fabrication die milled to tolerances no modern frontier foundry could match.", // Industrial Relic Fragment
  "irf2": "\"Look at the bearing housing,\" the chief engineer muttered, wiping grease off the relic casing. \"Ten thousand years in the dirt and it still spins true.\"", // Industrial Relic Fragment
  "irf3": "A cracked gyro-stabilizer salvaged from the collapsed mine lift turned out to house a pure crystalline memory rod inside its axle.", // Industrial Relic Fragment
  "irf4": "Stacked neatly behind a caved-in smelter wall sat a crate of stamped pre-war power couplings, untouched by rust or time.", // Industrial Relic Fragment
  "irf5": "The drill bit snapped against a buried casing of Lazax hull alloy, part of an assembly far older than the colony above it.", // Industrial Relic Fragment
  "ion": "\"Sensors just went blind!\" Blue plasma sheets rolled across the upper atmosphere, twisting the local jump-corridor into a crackling storm.", // Ion Storm
  "kel1": "The stranded Keleres were grateful for the resupply, and offered to assist the research team in any way that they could.", // Keleres Ship
  "kel2": "The *Hinterlight* moved steadily toward the distress beacon, broadcasting their own response on all channels.", // Keleres Ship
  "ls": "Behind a sealed vault door three levels beneath the ruins, the survey team froze as someone inside lit brass lamps and challenged them in Classical Lazax.", // Lazax Survivors
  "lf1": "Edict 281: All indigenous production facilities are placed under control of the occupational authorities until further notice.", // Local Fabricators
  "lf2": "\"These people's autofactories can turn out a new starfighter in less time than it takes me to order it!\"", // Local Fabricators
  "lf3": "Though sub-standard, the locally produced munitions were enough to turn the tide of the war.", // Local Fabricators
  "lf4": "Within months, bulk transports were arriving from the homeworld, reviving the local economy.", // Local Fabricators
  "lc1": "\"Mayday, mayday...this is the free trader *Hrothgar*...losing pressure fast...abandoning ship... Mayday...\"", // Lost Crew
  "lc2": "Only two survivors were found aboard the derelict, and they had a harrowing tale to tell their saviors.", // Lost Crew
  "majent": "Jaset had worked the field for several months before the dreams began to bleed into waking hours. Voices. Flashes of red. Dust-filled caverns that went deep into the planet's core. He'd blink and rub his eyes and carry on with his work. Exhaustion, he told himself. Nothing more.", // Major Entropic Field
  "mo1": "\"My mates and I used to be 4th Air Legion, but we figured we could make more money working freelance.\"", // Mercenary Outfit
  "mo2": "The bar was full of scarred and dirty individuals from a dozen different species. But each one had a weapon, and looked completely comfortable with it.", // Mercenary Outfit
  "mo3": "\"Morse's Marauders are the most affordable soldiers of fortune on-planet. And trust me, you get exactly what you pay for.\"", // Mercenary Outfit
  "ms1": "The deep space freeports tend to be infamous dens of criminals, but also valuable nodes in the interplanetary trade networks.", // Merchant Station
  "ms2": "\"Unidentified vessel, this is Freeport Canopus. State your intentions before approaching.\"", // Merchant Station
  "mw": "Core samples came back heavy with refined iron and rare alloys; within a week, the scout ship's landing zone was buried under excavator rigs.", // Mining World
  "minent": "After the Naaz-Rokha's discoveries in the wake of the Acheron event, various enterprising corporations quickly sought to stake their claims in areas well suited to entropic field harvesting.", // Minor Entropic Field
  "mirage": "The star wasn't supposed to have a habitable planet, but one lay directly in the cruiser's path. And a cloud of starfighters was rising from the world's surface to greet it.", // Mirage
  "pw": "The survey crew expected another barren rock. Instead, the drop-shuttle broke through the cloud deck above turquoise lagoons and quiet terraced valleys.", // Paradise World
  "propulsion": "Drifting silently in synchronous orbit, the abandoned test-rings still hummed with enough gravitic charge to rattle the scout frigate's hull.", // Propulsion Research Facility
  "rw": "One pass with the subsurface scanner lit the screen bright gold: thick seams of heavy isotopes ran practically beneath the landing struts.", // Rich World
  "toe": "The expedition halted at the edge of the salt flat, staring up at a windowless obsidian monolith that had defied wind and erosion for millennia.", // Tomb of Emphidia
  "urf1": "Snagged in the frigate's magnetic scoop, the featureless black tetrahedron cast no reflection under the cargo bay floodlights.", // Unknown Relic Fragment
  "urf2": "\"Where did this come from?\" the deck officer asked, turning the weightless ring over in his palm. \"The scanners showed empty space an hour ago.\"", // Unknown Relic Fragment
  "urf3": "Recovered from the rim of a dead gravity well, the fractured prism bent cabin light into colors none of the crew could name.", // Unknown Relic Fragment
  "vfs1": "It turned out that the continuous lightning storms were an unlimited source of power, which was little consolation to those assigned to build the collection towers.", // Volatile Fuel Source
  "vfs2": "Only by using retrofitted Scavenger walkers could they mine the radioactive Nyx crystals safely.", // Volatile Fuel Source
  "vfs3": "\"With the extra fuel refined from the plasma clouds, our fleet can continue operations for months.\"", // Volatile Fuel Source
  "warfare": "Charred armor hulls and unexploded plasma shells littered the southern proving grounds, left behind from weapons trials before the Twilight Wars.", // Warfare Research Facility
};

/** Plot cards (Firmament / Obsidian). */
const plot: LoreMap = {
  "assail": "The first salvo came out of the dark off the port bow; the second tore straight from their own escort frigate's ventral tubes. On the flagship bridge, the tactical display flickered once under a wash of static and dropped every friendly transponder on the board to hostile red.", // Assail
  "enervate": "Fuel manifests stalled in the port-master's queue, watch rotations overlapped by six hours, and veteran crews woke with dry mouths and dull headaches. Three orbital docks ground to a halt before a shot was ever fired.", // Enervate
  "extract": "\"Take the cipher keys, the drive schematics, and the minister's chief clerk,\" the Firmament handler murmured over the tight-beam channel. \"Leave the vault lock intact so they spend a week blaming their own guards.\"", // Extract
  "mutated_assail": "Static drowned the fleet channel as the flagship's own gunners turned their batteries inward.", // Mutated Assail
  "mutated_enervate": "Consoles dimmed to amber across the battle group while watch crews stared blankly at scrolling telemetry. When the Obsidian cruisers crossed the perimeter buoys, not a single rail elevated to meet them.", // Mutated Enervate
  "mutated_extract": "When the morning watch unsealed the archive on Resculon, the crystal plates, the treasury ledger, and both duty archivists were gone. Only a thin black smear marked the latch of the airlock.", // Mutated Extract
  "mutated_seethe": "An unsigned cipher-slip left on the executive officer's bunk turned old border grievances into open mutiny. By the third bell, marine squads were trading rifle fire across the cruiser's main hangar.", // Mutated Seethe
  "mutated_siphon": "Ore barges vanished off the orbital registries, reactor grids dimmed across the outer colonies, and unmarked transfers drained the treasury vaults toward the hollowed orbits of Cronos and Tallin.", // Mutated Siphon
  "seethe": "A forged promotion docket, a whispered slight—soon rival captains watched each other instead of the border.", // Seethe
  "siphon": "Half a percent off every tariff, quietly routed to unmarked vaults on Cronos.", // Siphon
};

/** Systems (map tiles). */
const system: LoreMap = {
  "06": "Encrypted buoys ring this sunless sector, broadcasting cold telemetry across the outer rim. Every approaching hull is logged, scanned, and weighed by the silent towers of the L1Z1X Mindnet.", // [0.0.0] - L1Z1X
  "38": "Bulk ore haulers crawl without pause between the toxic cloud decks of Abyz and the frozen drive-ore camps of Fria. Corporate syndicates wage bitter legal battles on the Senate Promenade for a single docking berth.", // Abyz/Fria
  "69": "Twin suns beat down on Accoen's drifting fungal rafts and the smog-choked domes of Jeol Ir. Research shuttles and heavy freighters jostle for lane priority across the crowded orbital corridors.", // Accoen/Jeol-ir
  "54": "A roaring gravity rift tears through the center of Acheron, ringed by tumbling slabs of fractured crust. Flesh-and-steel cruisers of the Vuil'raith Cabal slip out of the violet haze with their transponders dark.", // Acheron - Vuil'raith
  "118": "Spatial scanners struggle to hold a clean lock on the dim star hanging above Ahk Creuxx. Beneath its bruised crimson glare, rebel yards weld salvaged cruiser ribs well beyond the reach of imperial patrols.", // Ahk Creuxx (Crimson)
  "39": "An empty stretch of vacuum torn open by a shimmering orange aperture.", // Alpha Wormhole
  "102": "Deep inside Shaleri space, Andeara serves as a quiet trading post for captains bold enough to bargain with the Ghosts of Creuss. Patrol wings hold station above every jump-point.", // Andeara
  "61": "Crackling bands of charged particles whip around Ang's hyperactive magnetosphere, painting the void in sheets of blue fire. Orbital siphon rigs brave the storm fronts to charge experimental batteries.", // Ang
  "10": "A dim, dying star casts pale light across the iron-rich caverns of Arc Prime and the windswept steppes of Wren Terra. Heavy Letnev drydocks hang in high orbit, turning out dreadnought hulls through every shift.", // Arc Prime/Wren Terra - Letnev
  "14": "Quiet trade lanes weave between the terraced spires of Archon Ren and the scarred continents of Archon Tau. Automated Xxcha defense grids track every approaching transponder from the outer belt.", // Archon Ren/Archon Tau - Xxcha
  "92new": "Encrypted Keleres relays and rapid-response cruisers now crowd the orbits between Archon Ren and Archon Tau. Tribuni investigators and Xxcha envoys cross paths hourly on the orbital piers.", // Archon Ren/Archon Tau Keleres
  "59": "Pale violet glare reflects off the frozen cloud bands of Archon Vail. Experimental drive plumes streak through the outer belt around the clock as propulsion engineers push their coils past spec.", // Archon Vail
  "53": "Sub-zero gales scour the surface of Arcturus while Sumerian Station spins overhead as a crossroads of smugglers, couriers, and mercenaries. Every docking bay carries rumors of the Nomad's agents.", // Arcturus - Nomad
  "37": "Wealthy visitors lounge beneath Arinam's orbital domes while their observation decks face the burning crust of Meer. Luxury suites and lethal solar flares share the same narrow orbital plane.", // Arinam/Meer
  "36": "Grain freighters climbing out of Arnor's green valleys pass crystal barges lifting from Lor's methane seas. Together, the twin worlds anchor one of the richest supply corridors on the frontier.", // Arnor/Lor
  "16": "Three desert worlds orbit a blazing white star at the heart of the Emirates of Hacan. Golden-sailed bulk haulers crowd every jump-point, carrying spice, gold, and sealed charters to the Core.", // Arretze/Hercant/Kamdorn - Hacan
  "44": "Nickel-iron boulders and shattered moonlets tumble through the transit lane in erratic orbits. Capital ships plot wide detours while automated mining drones strip the drifting stone for hull alloy.", // Asteroids
  "45": "The jagged remains of a planetoid cracked open during the Twilight Wars. Between the tumbling iron slabs, Mentak corsairs carve hidden drydocks out of the largest drifting stones.", // Asteroids
  "79": "Tumbling iron debris crowds the approaches to a coveted alpha aperture. Navigators who thread the shifting gaps gain a vital shortcut; those who clip a stone join the belt.", // Asteroids Alpha Wormhole
  "64": "Heavy docks and deep-space supply depots make Atlas a natural fleet staging post.", // Atlas
  "71": "Harvester convoys ferry Ba'kal's salt compounds straight to the river-farms of Alio Prima. Despite their contrasting climates, both worlds depend on the same guarded trade loop.", // Bakal/Alio Prima
  "109": "Disarmed patrol buoys drift between pacifist Bellatrix and the refugee docking bays of Tsion Station. Even in wartime, captains hold fire within range of its sanctuary beacons.", // Bellatrix/Tsion Station
  "35": "Sub-zero iodinium rigs on Bereg and humid marshland barges lifting from Lirta IV keep the sector's ore lanes crowded. Mercenary escorts draw double hazard pay against both raiders and arctic sharaks.", // Bereg/Lirta iv
  "113": "A violent convergence where a black gravity well tugs relentlessly at a neighboring beta aperture. Exiting the shear takes steady hands; a fraction of a degree separates a clean flank from a snapped keel.", // Beta Rift
  "40": "Swirling bands of ionized dust orbit this ancient spatial rift. Weathered Lazax buoys still broadcast navigation warnings, yet smugglers ride its shifting currents to shake imperial pickets.", // Beta Wormhole
  "73": "Mentak cutters prowl off Cealdri while Xanhact's scorched ruins turn quietly nearby.", // Cealdri/Xanhact
  "34": "Old Twilight Wars treaty monuments still stand above Centauri, looking out toward the modest vehicle foundries of Gral. Historians and fleet quartermasters alike find use for the sector.", // Centauri/Gral
  "fracture1": "Splintered light refracts off the cracking crust of Cocytus as the Fracture pulls the system apart. Only desperate scavengers and hardened war-fleets hold station near its decaying orbit.", // Cocytus
  "67": "Shards of a broken planetoid tumble inside a crackling gravity rift, gleaming with exposed seams of heavy metal. Mining crews gamble their hulls every cycle to haul ore out of the shear.", // Cormund
  "33": "Cadets from Corneeq's Free Worlds Academy run live-fire drills along the edge of Resculon's crowded trade routes. Warships and merchant haulers share the lanes in an uneasy truce.", // Corneeq/Resculon
  "106": "Isolationist wardens guard the toxic skies of Cresius while the clerks of Lazul Rex keep the subsector ledgers balanced nearby. Few foreign captains linger between the two orbits.", // Cresius/Lazul Rex
  "51": "An expanse of trapped violet light and radioactive frost sealed behind the Creuss Gate. Standard compasses spin wild here as translucent vessels glide across the glare.", // Creuss - Creuss
  "17": "A blinding tear in local space leaking cold, radioactive light. To long-haul freighter crews it is an omen to steer wide of; to the Ghosts of Creuss it is the sole threshold home.", // Creuss Gate - Creuss
  "96b": "A cold, starless hush settles over the hollowed orbits of Cronos and Tallin. Automated buoys fail minutes after entering the system, leaving approaching cruisers blind.", // Cronos Hollow/Tallin Hollow (Obsidian)
  "96a": "Luminous rings gleam above Cronos and over Tallin's divided oceans. Beneath the quiet hum of local trade, Firmament handlers weave cells that reach the Core.", // Cronos/Tallin (Firmament)
  "32": "University shuttles from depleted Dal Bootha trade archival data daily with xeno-biologists braving Xxehan's tainted skies. The academies stay lit so long as the grain freighters arrive on schedule.", // Dal-Bootha/Xxehan
  "03": "Pilgrimage barges and clone-transports file steadily toward the Monastery of Lucas on Darien. Every vessel entering Yin space broadcasts the morning liturgy on open channels.", // Darien - Yin
  "55": "The colossal artificial shell of Elysium dominates the starscape, humming softly with the harnessed output of the captive singularity at its hollow core. Dormant stone monoliths hang in unbroken rings around the Titans' home, watching every inbound jump vector.", // Elysium - Ul
  "99": "Pre-Lazax ruins scar the moons of Emelpar, drawing archaeologists and relic hunters to this quiet frontier star. Every survey team digs for what vanished before the First Empire began.", // Emelpar
  "46": "A featureless expanse of interstellar dark far from any star—worthless to miners, yet prized by fleet commanders as a clean staging lane.", // Empty System
  "47": "Dead vacuum littered only with micro-meteorites and the faint static of weathered Lazax buoys. Hacan merchant guilds pay well for updated charts of its quiet transit lanes.", // Empty System
  "48": "An unremarkable void where nothing orbits and no sun shines. Intelligence services prize its isolation, hiding cloaked listening posts to skim encrypted traffic from neighboring sectors.", // Empty System
  "49": "No worlds orbit here, yet whoever holds this crossroads dictates every fleet advance.", // Empty System
  "50": "Silent deep space bathed in nebula glare—handy for cooling reactors and recalibrating drives.", // Empty System
  "77": "Officially uninhabited, which suits black-market brokers transferring cargo in the dark.", // Empty System
  "114": "A jagged wound in spacetime where alloy pits and flakes into cold dust. Standard physics falter inside its rim, drawing eccentric Hylar scholars who risk their hulls to log its decay.", // Entropic Scar
  "68": "Wreathed in thick, luminescent nebula dust, Everra's ancient nano-carbon spires glow dimly from orbit. Gas-harvesters slip through the haze to stay clear of passing raiders.", // Everra
  "97": "Bio-research stations ring the lush green horizon of Faunus, running trials the Galactic Council prefers not to audit. Armed corporate yachts keep uninvited inspectors clear of the atmosphere.", // Faunus
  "fracture2": "A frayed boundary where the twisted physics of the Fracture finally yield to normal space. Exhausted survey crews treat this threshold as a lifeline while rival pickets wait outside.", // Fracture Egress Left
  "fracture6": "A shimmering exit corridor framed by drifting shards of crystallized energy. It offers the only reliable path out of the deep Fracture, turning barren space into a contested chokepoint.", // Fracture Egress Right
  "fracture3": "A sterile expanse of splintered space where starlight bends at sharp angles. Its deadened sensor profiles make it a favored staging ground for covert operations.", // Fracture Void Left
  "fracture5": "Cold, lightless void laced with faint echoes of broken dimensions. Crews passing through log minor chronometer skips, yet the empty lane gives heavy armadas an unobstructed highway.", // Fracture Void Right
  "98": "Drifting clouds of industrial slag and chemical barges mark the approach to Garbozia. Scavenger syndicates comb the old imperial dumping grounds for volatile compounds.", // Garbozia
  "41": "The invisible remnant of a collapsed star that twists light and shears careless hulls. Bold admirals still slingshot their cruisers along its event horizon, trading hull plating for raw speed.", // Gravity Rift
  "66": "Buried inside the shifting murk of the Ichal Nebula, Hope's End bristles with forgotten Lazax training bunkers and live ordnance. Only disciplined crews navigate its blinding aurora storms.", // Hope's End
  "110": "Three distinct worlds crowd this rich frontier star: Horizon's tiered forests, the magnetic mines of El'Nath, and the cloud-cities of Luthien IV. Holding all three orbits anchors an entire regional economy.", // Horizon/El'Nath/Luthien IV
  "83a": "", // Hyperlane
  "83a120": "", // Hyperlane
  "83a180": "", // Hyperlane
  "83a240": "", // Hyperlane
  "83a300": "", // Hyperlane
  "83a60": "", // Hyperlane
  "83b": "", // Hyperlane
  "83b120": "", // Hyperlane
  "83b180": "", // Hyperlane
  "83b240": "", // Hyperlane
  "83b300": "", // Hyperlane
  "83b60": "", // Hyperlane
  "84a": "", // Hyperlane
  "84a120": "", // Hyperlane
  "84a180": "", // Hyperlane
  "84a240": "", // Hyperlane
  "84a300": "", // Hyperlane
  "84a60": "", // Hyperlane
  "84b": "", // Hyperlane
  "84b120": "", // Hyperlane
  "84b180": "", // Hyperlane
  "84b240": "", // Hyperlane
  "84b300": "", // Hyperlane
  "84b60": "", // Hyperlane
  "85a": "", // Hyperlane
  "85a120": "", // Hyperlane
  "85a180": "", // Hyperlane
  "85a240": "", // Hyperlane
  "85a300": "", // Hyperlane
  "85a60": "", // Hyperlane
  "85b": "", // Hyperlane
  "85b120": "", // Hyperlane
  "85b180": "", // Hyperlane
  "85b240": "", // Hyperlane
  "85b300": "", // Hyperlane
  "85b60": "", // Hyperlane
  "86a": "", // Hyperlane
  "86a120": "", // Hyperlane
  "86a180": "", // Hyperlane
  "86a240": "", // Hyperlane
  "86a300": "", // Hyperlane
  "86a60": "", // Hyperlane
  "86b": "", // Hyperlane
  "86b120": "", // Hyperlane
  "86b180": "", // Hyperlane
  "86b240": "", // Hyperlane
  "86b300": "", // Hyperlane
  "86b60": "", // Hyperlane
  "87a": "", // Hyperlane
  "87a120": "", // Hyperlane
  "87a180": "", // Hyperlane
  "87a240": "", // Hyperlane
  "87a300": "", // Hyperlane
  "87a60": "", // Hyperlane
  "87b": "", // Hyperlane
  "87b120": "", // Hyperlane
  "87b180": "", // Hyperlane
  "87b240": "", // Hyperlane
  "87b300": "", // Hyperlane
  "87b60": "", // Hyperlane
  "88a": "", // Hyperlane
  "88a120": "", // Hyperlane
  "88a180": "", // Hyperlane
  "88a240": "", // Hyperlane
  "88a300": "", // Hyperlane
  "88a60": "", // Hyperlane
  "88b": "", // Hyperlane
  "88b120": "", // Hyperlane
  "88b180": "", // Hyperlane
  "88b240": "", // Hyperlane
  "88b300": "", // Hyperlane
  "88b60": "", // Hyperlane
  "89a": "", // Hyperlane
  "89a120": "", // Hyperlane
  "89a180": "", // Hyperlane
  "89a240": "", // Hyperlane
  "89a300": "", // Hyperlane
  "89a60": "", // Hyperlane
  "89b": "", // Hyperlane
  "89b120": "", // Hyperlane
  "89b180": "", // Hyperlane
  "89b240": "", // Hyperlane
  "89b300": "", // Hyperlane
  "89b60": "", // Hyperlane
  "90a": "", // Hyperlane
  "90a120": "", // Hyperlane
  "90a180": "", // Hyperlane
  "90a240": "", // Hyperlane
  "90a300": "", // Hyperlane
  "90a60": "", // Hyperlane
  "90b": "", // Hyperlane
  "90b120": "", // Hyperlane
  "90b180": "", // Hyperlane
  "90b240": "", // Hyperlane
  "90b300": "", // Hyperlane
  "90b60": "", // Hyperlane
  "91a": "", // Hyperlane
  "91a120": "", // Hyperlane
  "91a180": "", // Hyperlane
  "91a240": "", // Hyperlane
  "91a300": "", // Hyperlane
  "91a60": "", // Hyperlane
  "91b": "", // Hyperlane
  "91b120": "", // Hyperlane
  "91b180": "", // Hyperlane
  "91b240": "", // Hyperlane
  "91b300": "", // Hyperlane
  "91b60": "", // Hyperlane
  "95": "Warm azure seas cover Ikatena beneath a ring of submerged research buoys and Deepwrought relay stations. Orbital scars from the Mahact occupation remain visible along the equatorial shelf.", // Ikatena (Deepwrought)
  "115": "Brilliant auroras sweep across Industrex's sky, driven by a magnetosphere strong enough to bend compasses in high orbit. Heavy foundries tap the magnetic storms to cast starship ribs.", // Industrex
  "52": "A cold, ancient sun hangs over the volcanic wastes of Ixth and the silent necropolis of Aior Dol Gorgos. Navigators plot wide of its outer buoys and keep their comms on tight-beam.", // Ixth - Mahact
  "01": "Orbital drydocks, crowded trade rings, and disciplined Federation patrol wings surround the blue-green globe of Jord. From its lunar yards, humanity projects its fleets across the rim.", // Jord - Sol
  "108": "Solar winds strip the atmosphere from Capha while molten Kostboth cools slowly in the inner ring. Orbital poets and mineral surveyors share the same narrow anchorages.", // Kostboth/Capha
  "70": "Irradiated dust clouds hang over Kraag's mines while frozen vaults sit buried beneath Siig's cesium seas. Recent Titan sightings have drawn scout squadrons from three different houses.", // Kraag/Siig
  "31": "Rudimentary workshops on Lazar supply basic hulls to pharmaceutical harvesters braving the arboreal razeden of Sakulag's jungles. Trade here is quiet, profitable, and heavily insured.", // Lazar/Sakulag
  "116": "Twin space elevators stand frozen against the stars above Lemox, stalled by a local collapse in spacetime. Salvage crews hold station at the outer edge, waiting for the anomalies to settle.", // Lemox
  "104": "Spore-choked clouds swirl above Lesab as terraforming tenders monitor the sprawling fungal biosphere below. Biologists still argue over whether the colony is a triumph or a containment breach.", // Lesab
  "fracture7": "Two broken worlds tumble through the bruised twilight of the Fracture, scarred by cataclysms older than the First Empire. Cruisers passing between Lethe and Phlegethon keep their shields at full draw.", // Lethe/Phlegethon
  "72": "Old blood stains the orbital lanes above Lisis while corporate artillery trials flash across the barren poles of Velnor. Every freighter captain crossing the system keeps his transponder loud.", // Lisis/Velnor
  "26": "Biotech freighters and heavily armed customs cruisers share the jump-lane around Lodor's alpha aperture. Rumors of sealed bacterial vaults keep rival intelligence ships watching from the outer belt.", // Lodor
  "75": "Three diverse worlds share this contested rim star: Loki's storm-wracked colonies, Ashtroth's algal bogs, and Abaddon's towering trade peaks. Holding all three orbits demands constant patrol rotations.", // Loki/Ashtroth/Abaddon - Devils
  "09": "Crystal interceptors weave between the muddy iron-works of Maaluuk and the violet mountains of Druaa. Foreign scouts approaching Naalu space find interceptor wings already waiting on their vector.", // Maaluuk/Druaa - Naalu
  "82a": "Beyond the charted rim, a silent knot of locked wormholes coils around the dim silhouette of Mallice. Strange gravitational echoes ripple outward across the dark.", // Mallice - Locked Nexus
  "82b": "Major spatial corridors from every quadrant converge above the impossible horizon of Mallice. Cruisers anchored here stand one jump from half the galaxy.", // Mallice - Nexus
  "112": "The scarred jewel of the galaxy turns slowly beneath a web of diplomatic buoys and ruined orbital rings. Every road in interstellar politics still runs straight to the seat of Mecatol Rex.", // Mecatol Rex
  "18": "Radiation-scarred continents stretch endlessly beneath the gleaming shield-dome of Mecatol City, the ancient seat of the Lazax. Warships, diplomatic shuttles, and Winnaran patrol cutters crowd its high orbit every hour, each watching the others while eyeing the empty throne below.", // Mecatol Rex
  "24": "Crackling radiation belts wrap tightly around Mehar Xull, frying unshielded circuits within minutes. Electro-quantum propulsion engineers brave the glare anyway, testing experimental drives inside the storm.", // Mehar Xull
  "30": "Protected xenological reserves on Mellon share orbital traffic with the space elevator and Zohlian whiskey distilleries of Zohbat. Merchant crews prize the shore leave; conservation wardens detest the traffic.", // Mellon/Zohbat
  "93": "Concentric corporate cities glitter across Mez Lo Orz Fei Zsha while coastal ports thrive on Rep Lo Orz Qet. Encrypted Ral Nel couriers clear the outer buoys on every available vector.", // Mez Lo Orz Fei Zsha/Rep Lo Orz Qet (RalNel)
  "02": "Jury-rigged drydocks and armed merchantmen crowd the orbit of Moll Primus. Beneath the Mentak Coalition's banners, yesterday's exiles now run one of the sharpest navies in the Fringe.", // Moll Primus - Mentak
  "94new": "Hardened corsairs and Council investigators now share the docking piers above Moll Primus. Under the Keleres mandate, the old penal colony serves as a gritty staging ground for frontier patrols.", // Moll Primus Keleres
  "08": "SYSTEM.ID: MORDAI.II // STATUS: CONTAINMENT ACTIVE.\nGRAVITON BEAMS STABILIZING FRACTURED CRUST. PERIMETER PATROL GRIDS AT FULL DENSITY.", // Mordai II - Nekro
  "04": "Violent solar flares wash continually over the molten crust of Muaat, where Gashlai smiths forge War Suns inside massive orbiting crucibles. Standard hull plating begins to blister and warp before an unshielded foreign ship can even clear the outer buoys.", // Muaat - Muaat
  "57": "Orbital factories above Naazir exchange constant shuttles with the exotic energy labs of Rokha. Together, the two worlds form the inventive core of the Naaz-Rokha Alliance.", // Naazir/Rokha - Naaz-Rokha
  "12": "Submerged universities on Jol and Nar beam continuous research telemetry up to gleaming orbital academies. Nearly every major technological leap of the modern era passed through these archives.", // Nar/Jol - Jol-Nar
  "42": "Ionized gas blinds optics and stalls thrusters—a haven for battered cruisers patching breaches.", // Nebula
  "05": "A faint golden haze of Flaah spores drifts through the upper orbit of Nestphar, extending the Arborec Symphony into the vacuum. Visiting crews double-check their airlock seals before requesting clearance.", // Nestphar - Arborec
  "105": "Bioluminescent fungal caverns beneath New Terra and black-sand deserts on Tinnes give this frontier star an eerie stillness. Prospectors and xeno-botanists share the single orbital relay.", // New Terra/Tinnes
  "81": "An artificially ignited star burning with the wrath of the Embers of Muaat. Where conventional fleets hit a wall of lethal radiation, Gashlai forge-ships drop anchor inside the corona.", // Nova Seed
  "101": "A dozen moons tug violently at Olergodt's oceans, turning the system into a maze of shifting gravitational tides. Mining guilds brave the shear to strip the moons bare.", // Olergodt
  "c41": "Debris from the Nekro incursion still glints in high orbit above the scarred surface of Ordinian. Survey teams and relief convoys thread carefully through the drifting wreckage.", // Ordinian (C4)
  "92": "The cathedral-like station of Revelation hangs in defiance above the healing scars of Ordinian. From its fortified rings, the Last Bastion rallies frontier garrisons to hold the line.", // Ordinian/Revelation (Bastion)
  "60": "Perpendicular rings of ice and rock complicate every approach to Perimeter's hardened orbital garrisons. Old Lazax watch-posts still track incoming transponders with crisp imperial discipline.", // Perimeter
  "65": "Deep osmium veins and scarred Twilight Wars battlefields mark Primor as a contested prize. Supply convoys run heavy cruiser escorts along its temperate orbital lanes.", // Primor
  "25": "Merchants, smugglers, and customs patrols crowd the jump-lanes linking Quann's two continents to the nearby beta aperture. Fortunes change hands here before a freighter's drives cool.", // Quann
  "29": "Communal farm barges from Qucen'n drift past the neon-lit biomodification clinics and cyber boutiques orbiting Rarron's three moons.", // Qucenn/Rarron
  "13": "Vast hive-spires on arid Quinarra and icy boomtowers on Tren'lak feed the war machine of the Sardakk N'orr. Troop transports lift from both worlds in unbroken waves.", // Quinarra/Trenlak - N'orr
  "11": "Asteroid habitats and mobile shipyards drift near the crystal caverns of Lisis II, haunted by the scarred memory of Ragh. Even at anchor, the Clan of Saar keeps its drives warm.", // Ragh/Lisis II - Saar
  "15": "Thick jungle mists shroud Retillion and Shalloq, hiding Yssaril listening posts and shadowed landing pads beneath the canopy. Uninvited fleets entering the system often find their encrypted orders compromised and their fuel tenders misrouted before a single enemy hull appears on scopes.", // Retillion/Shalloq - Yssaril
  "76": "Three bustling worlds span the Rigel star's habitable zone: alkaline industrial ports, ocean resorts, and outer research spires. Trade convoys rarely clear the buoys with empty holds.", // Rigels
  "23": "Extreme axial tilt drags Saudor's days into long, baking shifts while its orbital drydocks hum without pause. Steady output of refined alloy makes it a cornerstone of regional logistics.", // Saudor
  "62": "Rusted dreadnought hulks from the Twilight Wars still drift in silent orbit above Sem-Lore's radiation deserts. Salvage crews and solemn pilgrims share the same quiet jump-lane.", // Sem-Lore
  "94": "A weeping crimson fissure surrounded by the drifting husks of forgotten warships. Navigators steer wide of its uneven gravitational pull and log no distress calls from within its rim.", // Sorrow (Crimson)
  "27": "Eight mineral-rich moons circle acid-drenched Starpoint while xeno-biologists study the strange biochemistry of New Albion nearby. Ore haulers and survey vessels keep the local buoys busy.", // Starpoint/New Albion
  "fracture4": "Starlight thins to gray around Styx; smart captains keep their drives primed.", // Styx
  "43": "A blinding maelstrom of incandescent plasma and lethal radiation. No conventional hull survives its glare, yet distant research outposts siphon its escaping neutrinos to power experimental reactors.", // Supernova
  "80": "The violent death throes of a red supergiant cast a dull crimson glare across neighboring sectors. Its expanding shockwave has scoured every planet to ash, leaving an impassable wall of fire.", // Supernova
  "111": "Blinding ultraviolet light washes over vibrant Tarana while aquatic crews staff the flooded docking bays of Oluz Station. Polarized visors and water-filled airlocks are standard issue on every pier.", // Tarana/Oluz Station
  "22": "Quiet, unhurried, and ignored by admirals until someone needs a discreet staging post.", // Tarmann
  "100": "A shimmering frozen halo rings uninhabitable Tempesta, glowing with volatile reaction-drive fuel. Tanker fleets queue along the edge of the ice to skim the richest veins.", // Tempesta
  "28": "Live-fire weapon trials light up desolate Tequ'ran while luxury liners drop anchor above import-hungry Torkan. Arms dealers and aristocrats strike their quietest bargains between the two orbits.", // Tequran/Torkan
  "56": "A colossal, light-swallowing nebula hides the ancestral anchorage of the Empyrean from foreign optics. Outsiders log only blinding dust; void-captains steer straight home.", // The Dark - Empyrean
  "117": "Nobody knows who built the Watchtower, only that its silent optics still track every ship.", // The Watchtower
  "21": "Overcrowded orbital habitats ring mineral-poor Thibah, serving as a frantic launchpad for frontier colonists and deep-space prospectors. Ships refuel quickly and push on toward richer stars.", // Thibah
  "107": "Resource-rich Tiamat sits uncomfortably close to the corsair havens of ruined Hercalor. Local patrol cutters run constant sweeps to keep the raiders on their own side of the star.", // Tiamat/Hercalor
  "20": "Crushing gravity locks Vefut II's cities deep underground while orbital antigrav labs float serenely overhead. Shipwrights everywhere prize the exotic field generators built in its workshops.", // Vefut II
  "74": "Orbital mining rings above Vega Major feed raw alloys straight to the famed propulsion yards of Vega Minor. Starship drives tested here push fleets across half the known galaxy.", // Vega Major/Vega Minor
  "103": "A dense shroud of golden clouds hides Vira-Pics III from orbital scanners. Only local pilots who know the narrow atmospheric corridors land without losing their bearings.", // Vira Pics III
  "78": "Starless deep space devoid of ore—a quiet proving ground for experimental drives.", // Void
  "63": "Geothermal plumes vent from Vorhal's rugged plateaus, powering heavy frontier foundries and fortified supply depots. Admirals prize the system as a sturdy anchor on the rim.", // Vorhal
  "19": "Floating sky-cities drift through Wellon's clear helium clouds along the core trade routes.", // Wellon
  "07": "Gleaming spires of Lazax design crown the skyline of Winnu beneath vigilant Custodian patrol wings. Every hull launched from these drydocks carries an oath to restore the First Empire.", // Winnu - Winnu
  "58": "Three worlds of the Atharal Torus orbit close to volatile Phorus: Ylir's ocean platforms, Avar's sheltered caverns, and Valk's skyhooks. Argent strike wings patrol the glare in tight, disciplined crescents.", // Ylir/Avar/Valk - Argent
  "93new": "Keleres dispatch boats weave steadily between Ylir's ocean platforms, Avar's canyon hangars, and Valk's shipyards, stretching a thin peacekeeping mandate across the Atharal Torus.", // Ylir/Avar/Valk Keleres
};

/** Planets. */
const planet: LoreMap = {
  "0.0.0": "This elusive energy-rich planet was the desperate destination of the secret Lazax diaspora. Now, it is a technological nightmare.", // [0.0.0]
  "abaddon": "A temperate planet whose low gravity allows for stunningly tall mountain ranges. Serves as a stop-over for trade routes to the nearby Vorish Cluster.", // Abaddon
  "abyz": "Its thick, complex atmosphere is inhospitable to most races, but Abyz is known for its seemingly endless natural reserves of rare minerals and precious metals.", // Abyz
  "accoen": "Populace lives on continent-sized fungal rafts that float atop a soupy, world-spanning ocean of useful bio-compounds. Popular research site for biologists.", // Accoen
  "acheron": "Once a dusty, dead world concealing a portal to Ixth. Now, a gravity rift has shattered the world, creating a labyrinth of strange energies and tumbling shards of rock.", // Acheron
  "ahkcreuxx": "The mysterious world discovered by the Crimson Rebellion is just as impossible in physical space as its sister planet, Creuss. Initially uninhabited, the world has begun to foster life - of a sort.", // Ahk Creuxx
  "alioprima": "Wet planet covered in rivers, lakes, and small seas, but no oceans. Dry poles provide haven from constant floods. Numerous farms famous for luxury foodstuffs.", // Alio Prima
  "andeara": "Located deep in Shaleri space, the formerly isolated Shikrai outpost on Andeara serves as a key access point to those wishing to do business with the Creuss.", // Andeara
  "ang": "High rotational speed creates extremely energized magnetosphere. Orbital taps use this to energize starship fuels, and power labs developing new beam weapons.", // Ang
  "arcprime": "Below the thin surface atmosphere lie the continent-sized caverns of the Letnev. Rich in metals and energy, its vast fungus fields struggle to feed its population.", // Arc Prime
  "archonren": "Populated by small arboreal villages, this planet's only true urban center is the royal city of Kklaj. The Xxcha home world and home to the renowned library of Xuun.", // Archon Ren
  "archonrenk": "Ancient archival vaults and tiered stone sanctums, once dedicated solely to peaceful debate, now hum with the frantic work of Keleres investigators combing centuries of galactic secrets for looming crises.", // Archon Ren Keleres
  "archontau": "Ravaged by Sol and Letnev bombardments during the Twilight Wars. The Xxcha commit substantial resources to rebuilding its ecology and cleansing its toxic continents.", // Archon Tau
  "archontauk": "Beneath tranquil garden canopies and sweeping pavilions, Keleres liaisons and Council castaways wage quiet wars of espionage and compromise, stretching the authority of their mandates to the breaking point.", // Archon Tau Keleres
  "archonvail": "A former Xxcha colony, its extremely low temperatures create exotic molecular compounds that give the world its famed violet hue. Orbital facilities use the compounds in high-energy stardrive research.", // Archon Vail
  "arcturus": "Cold and still, with a surface buried beneath kilometers of ice. A few smuggler bases dot the surface, but Sumerian Station circles the planet, making it a vital trading destination.", // Arcturus
  "arinam": "Isolated planet poor in resources but rich in natural beauty. Boasts many exotic resorts frequented by the rich and famous of the galaxy.", // Arinam
  "arnor": "Lush, green world that is renowned for some of the most fertile soil in the galaxy. Dominated by endless fields and the processing facilities of large agricultural firms.", // Arnor
  "arretze": "The bustling political heart of the Emirates of Hacan. Beneath its golden desert skies, towering bazaar-cities host trade syndicates from every corner of the galaxy.", // Arretze
  "ashtroth": "Covered in boggy landmasses and shallow seas. Algal blooms provide rich biomass for processed foods, but create smelly (and often toxic) offgassing.", // Ashtroth
  "atlas": "Heavy grav world and former Sol colony famed for squat, strong inhabitants and strategic location. Visitors need support exoskeletons to move on the surface.", // Atlas
  "avar": "Lighter than its companion worlds, Avar is riddled with caverns. The majority of the Atharal Torus lives in the bustling aeries within, sheltered from the radiation bursts emanating from nearby Phorus.", // Avar
  "avark": "Lighter than its companion worlds, Avar is riddled with deep caverns that shelter its inhabitants from Phorus's radiation bursts. Several of those subterranean aeries now house makeshift Keleres barracks and field armories, staffed by volunteers who prefer clear skies and loose Council oversight.", // Avar Keleres
  "avernus": "The first artificial world of this galactic age.", // Avernus
  "bakal": "Dry, rocky deserts stretch from pole to pole. Shield cities protect against sandstorms while supplying nomadic harvester crawlers that mine the barrens for salt compounds.", // Ba'kal
  "bellatrix": "Once devoted to war, Bellatrix was thoroughly demilitarized and now espouses a pacifist philosophy.", // Bellatrix
  "bereg": "A frozen world that is inhospitable to most races. Indentured laborers risk attacks from arctic sharaks in the infamous Iodinium mines.", // Bereg
  "ocean4": "Sites with unique oceanic chemistry are of obvious interest to Deepwrought researchers.", // Brine Pool
  "capha": "The green zones maintain a stable atmosphere, but Capha's lack of a magnetosphere means that its breathable air is swiftly stripped by cosmic wind.", // Capha
  "cealdri": "Small cities huddle on the shores of the single ocean and avoid the arid continental interiors. Mentak ships hunt departing vessels carrying bespoke cybernetics.", // Cealdri
  "centauri": "Venerable world with few resources but a rich history. Site of important treaties between several races during the Twilight Wars.", // Centauri
  "cocytus": "Witness the end of a world, piece by glittering piece.", // Cocytus
  "ocean1": "Vibrant, kilometers-wide reefs teem with bioluminescent life, providing Deepwrought researchers with rare organic compounds found nowhere on dry land.", // Coral Reef
  "cormund": "A remote and sparsely settled Naaz-Rokha world destroyed during early entropic field tests. Now mining corporations harvest metals from the shattered core.", // Cormund
  "corneeq": "Former garden world that has subsequently enjoyed increased industrialization. Home to the esteemed Free Worlds Academy of Military Science and Research.", // Corneeq
  "cresius": "The techno-anchorites of the Grovian Order forbid mining of their \"sacred planet,\" but the world is so toxic few would try anyway.", // Cresius
  "creuss": "Trapped between matter and void lies the realm of Creuss. Made of trapped light and radioactive gas, this realm hosts the most peculiar forms of life.", // Creuss
  "cronos": "Although they spend most of their time working in the deep mines, the people of Cronos revere their beautiful sky. Its dense clouds cannot quite hide the luminous rings that shine every night.", // Cronos
  "cronoshollow": "The night sky is a deep black, unbroken by any star. During the day, the clouds are an unvarying gunmetal grey.", // Cronos Hollow
  "custodiavigilia": "Custodia Vigilia. The fully realized seat of the Keleres. A veritable fortress in the heart of Mecatol City. Ten thousand people come and go daily, and the Keleres see them all.", // Custodia Vigilia
  "dalbootha": "A populous planet whose resources have been severely depleted. Well-educated citizenry and many universities, but dependent on foreign imports.", // Dal Bootha
  "darien": "Darien is the heart of the Brotherhood's realm. Here, within the great Monastery of Lucas, rests the Yin, the holy egg from which all the Brotherhood were made.", // Darien
  "ocean3": "The Abyssal zone features such dramatic pressure that even most Hylar need assistance to survive in the lightless depths.", // Deep Abyss
  "druaa": "Despite its oversized poles, one of the most beautiful of planets. Its flowered steppes, violet mountains, and glowing forests are famous across the galaxy.", // Druaa
  "elnath": "El'nath's local magnetic field is so strong that metallic objects are repelled toward the sky. Specialized tools are required for mining and industrial operations.", // El'Nath
  "elysium": "Larger than a thousand terrestrial planets, Elysium is an artificial shell-world built around the powerful singularity in its hollow heart. Its surface is covered in calm seas and cultivated plains.", // Elysium
  "emelpar": "The legendary ruins on Emelpar's moons must certainly date to before the Lazax, but no other trace of this vanished civilization remains.", // Emelpar
  "everra": "Ancient world of red seas and bare rocks. Locals live in wondrous nano-carbon cities built by a mysterious ancient race, and mine nearby nebulae for rare gases.", // Everra
  "faunus": "Faunus is ecologically rich, which supports the controversial biogenetics research of the Maxis order.", // Faunus
  "fria": "Brutally cold ice world populated only by a few scattered mining camps. Despite its brutal climate, highly prized for its deposits of rare ores used in starship drives.", // Fria
  "garbozia": "Once an Imperial dumping ground, the mixture of mineral and chemical waste on Garbozia has become a resource - and a hazard - of its own.", // Garbozia
  "gral": "Backwater planet with modest resources and an unassuming populace. Most noted for the reliable and affordable vehicles produced in its factories.", // Gral
  "hercalor": "Overfarming devastated Hercalor's biosphere. Now the planet is a haven for rogues and pirates.", // Hercalor
  "hercant": "Scorched dunes and ancient canyon-fortresses mark the spiritual home of the Hacan warrior clans. Though harsher than Arretze, its oasis refineries power the Emirates' merchant fleets.", // Hercant
  "hopesend": "Buried in the Ichal Nebula. The Lazax used the toxic wildlife and fierce aurora storms to train their troops. Even now, volatile weapon caches remain hidden beneath its sands.", // Hope's End
  "horizon": "Horizon's biomes are heavily stratified by elevation, with shallow seas, lowland forests, and arid, rocky highlands. Strong air currents at higher altitudes may be responsible.", // Horizon
  "ocean5": "Drylanders frequently discount the scientific opportunities to be found beneath their own polar ice sheets.", // Ice Shelf
  "ikatena": "With over a million small islands and shallow, warm seas, Ikatena is considered a paradise by many species. Its recent Mahact occupation has left the once-peaceful planet scarred, but resolute.", // Ikatena
  "illusion": "Absent from every Council survey and invisible to long-range sweeps, Illusion reveals itself only at point-blank range—where its cloaked cities dispatch swarms of starfighters to drive off intruders.", // Illusion
  "industrex": "With an unusually strong planetary magnetosphere, Industrex also sports an active and quite beautiful atmosphere full of auroras.", // Industrex
  "ixth": "A dry, dead world of black volcanic mountains and molten seas of lava. The great necropolis of Aior Dol Gorgos on the Plateau Imperia is the only evidence of civilization.", // Ixth
  "jeolir": "Heavily industrialized world. Pollution has killed all life outside of dome cities, but twin suns provide constant power for factories and huge population.", // Jeol Ir
  "jol": "Covered by cold oceans and a few inhospitable islands. The seat of the Headmaster, the Hylar ruler, who dwells in the deep underwater city of Wun-Escha.", // Jol
  "jord": "Distinctly seasonal, with the greatest variety of climates and ecologies in the galaxy. The Federation of Sol rules the Jord humans from the great city of New Moscow.", // Jord
  "kamdorn": "Also called the \"Dream Sand.\" The least populated of the Hacan planets, but the center of the Hacan mythology and religion. The only known source of starflowers.", // Kamdorn
  "kostboth": "Kostboth is an infant planet, not yet cooled from its formation. A tiny community of poets and scientists lives in orbit, chronicling the planet's first era.", // Kostboth
  "kraag": "A heavily irradiated world known only for its dust mines. Recently, a massive \"tomb\" of dormant Titans was discovered in the southern hemisphere.", // Kraag
  "lazar": "The only inhabited world in a forgettable system. Few native resources and rudimentary, often underdeveloped, industries.", // Lazar
  "lazulrex": "Once a subsector capital, Lazul Rex has somehow endured the Twilight Wars unscathed with a fully functional government and economy.", // Lazul Rex
  "lemox": "Its twin space elevators are marvels of engineering, but industry on the planet came to a grinding halt when local spacetime collapsed.", // Lemox
  "lesab": "Lesab is either a resounding success or dangerous failure of terraforming, with its surface now dominated by a semi-sentient fungus.", // Lesab
  "lethe": "A planet riven by disaster, awaiting the final calamitous blow.", // Lethe
  "lirtaiv": "Covered in vast swamps and fetid bogs. Home to rare biochemical compounds unique to its marshlands used in everything from exotic foods to biogenic drugs.", // Lirta IV
  "lisis": "Primordial world with primitive native life. Potential for terraforming led to the infamous genocide of Saar settlements by Sardakk N'orr, and ongoing conflict between them and Naalu forces.", // Lisis
  "lisisii": "The crystal caverns of Lisis II are the source of most of the Jorun colonists' water and foodstuffs. Notable for the great crescent-shaped valley of Gavar.", // Lisis II
  "lockedmallice": "Trapped in a space believed to be beyond our universe, a shimmering world of strange energies and disconcerting warping of physical laws sitting at the heart of a strategically vital wormhole nexus.", // Locked Mallice
  "lodor": "Wealthy planet ruled by powerful biotech consortiums. Rumored to harbor hidden caches of outlawed bacterial weapons.", // Lodor
  "loki": "Cold and wracked with violent storms, Loki still hosts several Yssaril and human colonies, some of which have engaged in escalating shadow-conflicts.", // Loki
  "lor": "Wreathed in vast seas of methane ice. Seafloor drilling platforms harvest rare crystals used in advanced computers and energy weapons.", // Lor
  "ocean2": "Although usually badly degraded by water and time, shipwrecks remain fascinating areas of exploration and study, whether those ships sailed sea or stars.", // Lost Fleet
  "luthieniv": "A mid-sized gas giant with unusually rich gas clouds, Luthien IV's populace live in floating cities in a narrow habitable zone just below the outer layer.", // Luthien IV
  "maaluuk": "Mostly pungent marshland and mudplains. Original world of the Naalu race, which now enslaves the winged Miashan to work its great iron-extraction plants.", // Maaluuk
  "mallice": "Trapped in a space believed to be beyond our universe, a shimmering world of strange energies and disconcerting warping of physical laws sitting at the heart of a strategically vital wormhole nexus.", // Mallice
  "mr": "Once a splendid place, now a sad devastated wasteland. Only the radiation-shielded Mecatol City, the seat of the powerful Galactic Council, remains habitable.", // Mecatol Rex
  "mrte": "Once a splendid place, now a sad devastated wasteland. Only the radiation-shielded Mecatol City, the seat of the powerful Galactic Council, remains habitable.", // Mecatol Rex
  "meer": "Hellish world immolated in the inferno of its nearby sun. Famed for the fiery majesty of its surface when viewed from the safety of its many orbital stations.", // Meer
  "meharxull": "Unstable radiation belts create hazardous living conditions but facilitate research in electro-quantum propulsion technologies.", // Mehar Xull
  "mellon": "Poor in natural resources, but rich in exotic plant and animal life. Protected as a planetary xenological garden and lifeform preserve.", // Mellon
  "mez": "The great cities of Mez Lo Orz Fei Zsha cover most of the surface in their concentric, well-organized rings. Each city is owned and operated by its own massive corporate-consortium.", // Mez Lo Orz Fei Zsha
  "mirage": "Exists on no known charts and appears deserted to those who stumble across it. However, secretive locals live in cloaked cities heavily defended by swarms of starfighters.", // Mirage
  "mollprimus": "In places lush and rich, in others a barren wasteland. This old Lazax penal colony has prospered under the rule of the governing Mentak Coalition.", // Moll Primus
  "mollprimusk": "In places lush and rich, in others a barren wasteland. Under Keleres charter, this former Lazax penal colony serves as an unlikely staging post, where pardoned corsairs and seconded Council clerks keep old Mentak cruisers flying on a shoestring budget.", // Moll Primus Keleres
  "mordaiii": "Mined to its bones by the virulent Nekro, Mordai II is reinforced by the graviton energy beams that barely keep the world from collapsing in on itself.", // Mordai II
  "muaat": "The fiery surface of Muaat is uninhabitable to most races. It is home to the Gashlai, and only here can they live outside of their cumbersome ember suits.", // Muaat
  "naazir": "A small planet of high mountains and deep, narrow seas. Cities and vertical farms burrow into cliff faces, while orbital factories produce high tech consumer goods.", // Naazir
  "nar": "Covered by mild oceans and a small archipelago called The Reef by offworlders. The Circle of Regents makes its home in the underwater city-school of Nuun-Dascha.", // Nar
  "nestphar": "The fungal world of Nestphar is home to the symbiotic Arborec. Nestphar's orbit is filled with Flaah spores that extend its Symphony.", // Nestphar
  "newalbion": "Rare atmospheric composition and biochemistry support lifeforms unlike any other in the galaxy.", // New Albion
  "neutera": "Explorers were surprised to discover that this apparently lifeless rock has a rich fungal ecosystem in its interior, eating radiation from the planetoid's heavy metal core.", // New Terra
  "olergodt": "Olergodt's dozen moons create dramatic and dangerous tides, but also host a bustling mining industry.", // Olergodt
  "oluzstation": "Built by the Kieros and refitted by the Hylar, Oluz Station consists primarily of flooded compartments for aquatic species.", // Oluz Station
  "ordinian": "The Nekro Virus consumed this former Naaz-Rokha colony virtually down to its bedrock. Restoration efforts have only begun to restore its ravaged biosphere.", // Ordinian
  "ordinianc4": "Scoured down to gray bedrock by the Nekro Virus, Ordinian now stands as a grim monument to the cost of the war and the fragile hope of rebuilding.", // Ordinian
  "perimeter": "Former garrison world with fond memories of the Lazax. Maintains formidable military with informal ties to the Winnu. Perpendicular rings make orbital navigation difficult.", // Perimeter
  "phantasm": "Long-range sensors register only empty vacuum where Phantasm orbits, yet ships that stray too close discover veiled cities and relentless squadrons of starfighters rising from the mist.", // Phantasm
  "phlegethon": "A ruined planet for a ruined universe.", // Phlegethon
  "primor": "Large temperate world. Site of several pitched battles during the Twilight Wars due to valuable osmium deposits and a well-educated populace.", // Primor
  "quann": "Since the discovery of the Alpha Wormhole, this temperate planet with two continents and one large ocean has been a haven for traders and smugglers alike.", // Quann
  "qucenn": "After the Twilight Wars, existed for centuries as a near-utopia of scattered communal farms free from governmental interference.", // Qucen'n
  "quinarra": "Enormous and oceanless. Not only the largest planet supporting sentient life, but also the one with the least moisture. Home to the Sardakk N'orr hive cities.", // Quinarra
  "ragh": "Once a proud homeworld of the Clan of Saar before the N'orr invasion drove them to the stars. Its scarred continents remain a bitter rallying cry across the asteroid belts.", // Ragh
  "rarron": "Large populous world with three distinctive moons renowned for its biomodification clinics and cyber boutiques.", // Rarron
  "rep": "Arid and desolate except along its equatorial sea, the Ral Nel birth world has escaped the worst depredations of industrialization. The cities along the coast balance modern amenities with natural beauty.", // Rep Lo Orz Qet
  "resculon": "Poor in natural resources, but a nearby nexus of major trade routes has brought it increasing wealth as interstellar commerce has intensified.", // Resculon
  "retillion": "Cloaked in dense, mist-shrouded jungles and treacherous bogs, Retillion is the ancestral home of the Yssaril Tribes. Few off-worlders ever leave its shadowed canopy with their secrets intact.", // Retillion
  "revelation": "Hanging like a cathedral above Ordinian, the space station Revelation was constructed practically overnight to serve as the Last Bastion's military and economic hub.", // Revelation
  "rigeli": "Hot, innermost world of the Rigel system. Cities and native life cluster inland from the heavily alkaline oceans.", // Rigel I
  "rigelii": "Temperate world with expansive oceans. Covered in estates and resorts for the system's elite, with extensive fisheries that feed much of the rest of the system.", // Rigel II
  "rigeliii": "Outermost world of the Rigel system, and extensively settled despite cooler temperatures. Boasts a diverse range of industries and research institutions.", // Rigel III
  "rokha": "Terraformed by comet-drops and Alliance biotech into a cool world with alpine forests and stormy seas. The city of Dormont Vault boasts the famous Exotic Energies Institute.", // Rokha
  "sakulag": "Jungle planet plagued by dangerous predators such as the arboreal razeden. Home to many exotic biochemicals and natural pharmaceuticals.", // Sakulag
  "saudor": "Prosperous planet with large native population and substantial industry. Extreme axial tilt results in long day-night cycles that some races find uncomfortable.", // Saudor
  "semlore": "Home to the Semanora, and heavily damaged in the Twilight Wars. Rusting warship hulks litter the rad-deserts, making it a war memorial and salvage site.", // Sem-Lore
  "shalloq": "Covered with tundra, wetlands, and rainforest, much like its sister-planet Retillion. Home to Mojeb, the only major Yssaril city catalogued by off-worlders.", // Shalloq
  "siig": "World covered in frozen, cesium-laced oceans. Archives buried deep beneath the surface use the cold to preserve relics and operate massive computers.", // Siig
  "starpoint": "Large planet with eight small moons that supply a wide range of valuable resources. Acidic rains and toxic storms make it an unappealing destination for tourists.", // Starpoint
  "styx": "Where light goes to die.", // Styx
  "tallin": "Tallin's two oceans never intermix, completely separated by its main continent. They have unique chemical compositions and distinct biospheres.", // Tallin
  "tallinhollow": "The oceans lie as dead as the hearts of the populace.", // Tallin Hollow
  "tarmann": "Small, isolated planet with small population and modest resources. Most famous for its delicious avinberries.", // Tar'mann
  "tarana": "Visitors are encouraged to wear UV-filtering eye protection at all times, which also color-corrects the vibrant planet to a more neutral palette.", // Tarana
  "tempesta": "The frozen halo in Tempesta's sky is a potent fuel for reaction drives. The planet itself is virtually uninhabitable.", // Tempesta
  "tequran": "Desolate planet transformed into a weapons testing facility for large defense consortiums.", // Tequ'ran
  "thedark": "A massive nebula dominating the skies of many core worlds. Thick clouds of dust obscure its heart, a lightless refuge where Empyrean ships have congregated for millennia.", // The Dark
  "triad": "Three resonant spires rise from the silent stone, humming in a faint harmonic chord that shifts whenever fleets gather in the system.", // The Triad
  "thewatchtower": "Sporting methods of construction found nowhere else in the known galaxy, the Watchtower's origin is unknown. Some of its occupants have been standing watch there for countless generations.", // The Watchtower
  "thibah": "Burdened by overpopulation and low mineral content in the planetary crust. Historically used as a staging world for deep-space exploration and trade.", // Thibah
  "thundersedge": "Lightning arcs between the stone spires of the planet. The constant storms give Thunder's Edge its name.", // Thunder's Edge
  "tiamat": "Blessed with both a productive biome and exploitable mineral wealth, Tiamat is peaceful but surprisingly uninterested in galactic affairs.", // Tiamat
  "tinnes": "\"Oceans\" of black sand drift in the lowlands, forcing industry and most of the planet's biome to the frigid highlands.", // Tinnes
  "torkan": "Populous planet almost completely dependent on foreign imports to sustain the extravagant lifestyles of its citizens.", // Torkan
  "trenlak": "Icy and desolate. Other than the ferocious snow dracs and the rare icemoon flowers, life is restricted to the N'orr boomtowers and ice mines.", // Tren'lak
  "tsionstation": "The people of Bellatrix converted Tsion Station into a haven for refugees in order to atone for their past warmongering.", // Tsion Station
  "valk": "Valk contains lodes of rare minerals and metals within its crust. Skyhooks bring ore shipments up from the surface to the open-air shipyards in orbit.", // Valk
  "valkk": "Valk contains rich lodes of rare minerals within its crust. Its planetary skyhooks now feed ore directly to Keleres orbital cradles, where seconded Argent shipwrights and Mentak mechanics patch together fast patrol cruisers for frontier duty.", // Valk Keleres
  "vefutii": "Massive, rocky world cursed with extreme gravity. Underground cities support advanced research in antigravity technologies.", // Vefut II
  "vegamajor": "Most of the population resides in orbital habitats supporting mining operations in the planetary ring. Surface colonization limited due to oceanic macrosquid infestations.", // Vega Major
  "vegaminor": "Famous for extremely shallow seas covering most of the surface and for the renowned Vega Propulsion Corporation. Stilt cities host vibrant multi-species populations.", // Vega Minor
  "velnor": "Barren world of windswept rocks and thick, murky oceans. Lack of local lifeforms allows corporations to strip-mine the surface and test orbital kinetic weapons at the poles.", // Velnor
  "virapicsiii": "The atmosphere on Vira-Pics III is so dense that no trace of the rugged civilization clinging to life on the planet's surface is visible from orbit.", // Vira-Pics III
  "vorhal": "Rugged highland plateaus and deep geothermal vents make Vorhal a natural proving ground for heavy industry and frontier garrisons alike.", // Vorhal
  "wellon": "Sky cities suspended in helium-rich atmosphere more noted for fantastic views than the small quantities of exotic elements harvested by their chemical mines.", // Wellon
  "winnu": "The shining cities of the Winnu are the last places where authentic Lazax art and culture are still revered.", // Winnu
  "wrenterra": "Arid, windy, and populated primarily by predatory Daartar hounds. The Barony utilizes large swaths of its northern steppes for low-yield agriculture.", // Wren Terra
  "xanhact": "Rebelled during the end of the Lazax Empire, and was bombarded to ash by a Lazax fleet as an example. Left by the Galactic Council as a memorial to Lazax tyranny.", // Xanhact
  "xxehan": "Known for genetically complex native lifeforms adapted to tainted atmosphere and toxic biochemistry.", // Xxehan
  "ylir": "The smallest of the three planets in the Atharal Torus, Ylir is covered in kilometers of water. The Murmuration meets in platform cities that drift with the currents.", // Ylir
  "ylirk": "The smallest of the three planets in the Atharal Torus, Ylir is covered in kilometers of water. Alongside the meeting halls of the Murmuration, its drifting platform cities now host Keleres listening posts and neutral rendezvous piers for frontier informants.", // Ylir Keleres
  "zohbat": "Known for its highly intoxicating Zohlian whiskey and the planetary space elevator that links the surface with orbital stations and shipyards.", // Zohbat
};

export const CARD_LORE = {
  leader,
  agenda,
  promissoryNote,
  publicObjective,
  secretObjective,
  technology,
  breakthrough,
  ability,
  attachment,
  feature,
  unit,
  actionCard,
  relic,
  exploration,
  plot,
  system,
  planet,
} as const satisfies Record<string, LoreMap>;

export type LoreKind = keyof typeof CARD_LORE;

/** Ta sama karta pod innym id — czyta lore wskazanej karty. */
export const LORE_ALIASES: Partial<Record<LoreKind, Readonly<Record<string, string>>>> = {
  agenda: {
    "absol_abolishment": "abolishment", // Judicial Abolishment [Absol]
    "absol_agreement": "rearmament", // Rearmament Agreement [Absol]
    "absol_arbiter": "arbiter", // Imperial Arbiter [Absol]
    "absol_articleswar": "articles_war", // Articles of War [Absol]
    "absol_artifact": "artifact", // Ixthian Artifact [Absol]
    "absol_censure": "censure", // Political Censure [Absol]
    "absol_checks": "checks", // Checks and Balances [Absol]
    "absol_conscription": "conscription", // Regulated Conscription [Absol]
    "absol_constitution": "constitution", // New Constitution [Absol]
    "absol_conventionswar": "conventions", // Conventions of War [Absol]
    "absol_covert": "covert", // Covert Legislation [Absol]
    "absol_crisis": "crisis", // Galactic Crisis Pact [Absol]
    "absol_defenseact": "defense_act", // Homeland Defense Act [Absol]
    "absol_disarmament": "disarmament", // Compensated Disarmament [Absol]
    "absol_equality": "economic_equality", // Economic Equality [Absol]
    "absol_execution": "execution", // Public Execution [Absol]
    "absol_formation": "committee", // Committee Formation [Absol]
    "absol_government": "rep_govt", // Representative Government [Absol]
    "absol_grant": "grant_reallocation", // Research Grant Allocation [Absol]
    "absol_incentive": "incentive", // Incentive Program [Absol]
    "absol_leak": "classified", // Classified Document Leak [Absol]
    "absol_measures": "unconventional", // Unconventional Measures [Absol]
    "absol_minsantique": "minister_antiquities", // Minister of Antiquities [Absol]
    "absol_minscomm": "minister_commerce", // Minister of Commerce [Absol]
    "absol_minsexp": "minister_exploration", // Minister of Exploration [Absol]
    "absol_minsindus": "minister_industry", // Minister of Industry [Absol]
    "absol_minspeace": "minister_peace", // Minister of Peace [Absol]
    "absol_minspolicy": "minister_policy", // Minister of Policy [Absol]
    "absol_minssci": "minister_sciences", // Minister of Sciences [Absol]
    "absol_minswar": "minister_war", // Minister of War [Absol]
    "absol_miscount": "miscount", // Miscount Disclosed [Absol]
    "absol_mutiny": "mutiny", // Mutiny [Absol]
    "absol_nexus": "nexus", // Nexus Sovereignty [Absol]
    "absol_operations": "cladenstine", // Clandestine Operations [Absol]
    "absol_prophecy": "prophecy", // Prophecy of Ixth [Absol]
    "absol_recon": "wormhole_recon", // Wormhole Reconstruction [Absol]
    "absol_redistribution": "redistribution", // Colonial Redistribution [Absol]
    "absol_reduction": "arms_reduction", // Arms Reduction [Absol]
    "absol_regulations": "regulations", // Fleet Regulations [Absol]
    "absol_revolution": "revolution", // Anti-Intellectual Revolution [Absol]
    "absol_sanctions": "sanctions", // Executive Sanctions [Absol]
    "absol_schematics": "schematics", // Publicize Weapon Schematics [Absol]
    "absol_secret": "secret", // Archived Secret [Absol]
    "absol_seeds": "seed_empire", // Seed of an Empire [Absol]
    "absol_shared": "shared_research", // Shared Research [Absol]
    "absol_standardization": "standardization", // Armed Forces Standardization [Absol]
    "absol_swords": "plowshares", // Swords to Plowshares [Absol]
    "absol_travelban": "travel_ban", // Enforced Travel Ban [Absol]
    "absol_warrant": "warrant", // Search Warrant [Absol]
    "absol_whresearch": "wormhole_research", // Wormhole Research [Absol]
  },
  unit: {
    "absol_naaz_mech_space": "naaz_mech_space", // Z-Grav Eidolon (naaz mech)
    "naalu_mech": "naalu_mech_te", // Iconoclast (naalu mech)
    "naalu_mech_omega": "naalu_mech_te", // Iconoclast Omega (naalu mech)
  },
};
