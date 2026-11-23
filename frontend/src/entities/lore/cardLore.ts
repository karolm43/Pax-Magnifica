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
  "keleresheroharka": "\"Spare me the bylaws, Counselor,\" Leeds muttered, tossing a stack of requisition forms onto the table. \"Give me three cruisers and a blind eye, and I'll have your border secured by Tuesday.\"", // Harka Leeds (Mentak)
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
  "keleresherokuuasi": "The sky above the besieged colony fractured as golden wings dropped out of warp in tight formation. \"The Tribunal has heard your plea,\" Kuuasi broadcast across every open channel. \"Stand aside and let the storm pass.\"", // Kuuasi Aun Jalatai (Argent)
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
  "keleresheroodlynn": "Odlynn Myrr never raised his voice on the Conclave floor. He simply waited for the shouting to die down, adjusted his spectacles, and read the single footnote that undid three weeks of rival scheming.", // Odlynn Myrr (Xxcha)
  "letnevcommander": "\"The sight of a fleet of our warships, line abreast and guns out, states our demands more clearly than a thousand diplomats.\"", // Rear Admiral Farran (letnev commander)
  "winnucommander": "\"Admiral Rickani. For your victories in battle, your Emperor commands you to take your fleet to Mecatol Rex, and reclaim it for the Throne. Fail this charge at your peril.\"", // Rickar Rickani (winnu commander)
  "ghosthero": "\"The Creuss have unsurpassed command of wormhole technology, true - but enough to warp the very bounds of space? Preposterous!\"", // Riftwalker Meian (ghost hero)
  "jolnarhero": "The young Hylar's gills glared as swirling blackness filled her eyes. \"Headmaster,\" she gasped. \"I remember...I remember it all.\"", // Rin, the Master's Legacy (jolnar hero)
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
  "absol_affirmation": "The Winnu delegate stood for three hours reading genealogies from the Lazax era. Half the chamber fell asleep, while the other half quietly calculated how many dreadnoughts it would take to disprove a bloodline.", // Affirmation of Divine Right [Absol]
  "revolution": "\"Burn the labs and smash the data-spires!\" The crowd outside the Jol-Nar enclave surged against the barricades. Across a dozen rim worlds, fear of the next superweapon had finally curdled into hatred of the minds that built them.", // Anti-Intellectual Revolution
  "secret": "Deep beneath Mecatol City, vault doors older than the Twilight Wars hissed open. Inside lay a single crystal cylinder, sealed with the wax of a dead Emperor and waiting for someone bold enough to break it.", // Archived Secret
  "standardization": "Quartermasters across the galaxy wept when the edict passed. Overnight, thousands of proud regional shipyards were ordered to scrap their bespoke designs and adopt uniform Council calibration.", // Armed Forces Standardization
  "arms_reduction": "\"You scrap two dreadnoughts, and we will scrap two of ours,\" the ambassador proposed smoothly. Beneath the table, both delegates were already texting their shipyards to hide the newest hulls in the outer belts.", // Arms Reduction
  "articles_war": "Civilized empires prefer their slaughter tidy. The Articles drew a neat line between honorable bombardment and atrocities, giving every admiral a fresh set of loopholes to study.", // Articles of War
  "checks": "Every senator cheered for the principle of shared power, right up until they realized their own pet bills now required three additional committee signatures to survive.", // Checks and Balances
  "cladenstine": "The motion passed in a near-empty chamber at the fourth hour of the night cycle. By morning, half the intelligence networks in the galaxy had quietly shifted their budgets into unmarked accounts.", // Clandestine Operations
  "classified": "At noon, every public terminal on Mecatol Rex chimed at once. Within ten minutes, three ambassadors had resigned, two trade treaties had collapsed, and the Yssaril delegation was smiling politely into their tea.", // Classified Document Leaks
  "redistribution": "Border worlds rarely get to vote on their own owners. One stroke of the Speaker's stylus redrew the sector maps, turning yesterday's loyal colonists into tomorrow's tax base for a rival house.", // Colonial Redistribution
  "committee": "\"We cannot rush into a decision of this magnitude,\" the Xxcha representative declared, adjusting his spectacles. \"Let us form a subcommittee to review the feasibility of a working group.\"", // Committee Formation
  "disarmament": "The Council's treasury paid handsomely for every decommissioned rifle and scrapped walker. Most planetary governors pocketed the credits and immediately bought better ones on the black market.", // Compensated Disarmament
  "conventions": "Orbital bombardment of civilian centers was formally outlawed on a Tuesday. By Thursday, three different admirals had reclassified entire cities as 'unfortified military logistics hubs.'", // Conventions of War
  "covert": "The bill's text was redacted down to the punctuation marks. Senators cast their votes in total blindness, trusting only the frantic hand signals of their own spymasters in the gallery.", // Covert Legislation
  "absol_spending": "Buried on page four hundred of the imperial budget sat a slush fund large enough to buy a small moon. Nobody asked where the credits went, so long as their own sector got its cut.", // Discretionary Spending [Absol]
  "economic_equality": "The Hacan trade lords howled as the wealth-transfer algorithms kicked in. For one brief, glorious afternoon, the poorest rim republics had fuller vaults than the merchant princes of Arretze.", // Economic Equality
  "absol_emergency1": "Red klaxons echoed through the Grand Conclave as the blast doors sealed. \"Cancel the recess,\" the Speaker barked into the comms. \"We have a situation in the outer rim.\"", // Emergency Session [Absol]
  "absol_emergency2": "Delegates stumbled into the chamber half-dressed, clutching datapads and glaring at their rivals. Whatever had woken the Council at this hour was going to cost someone a fleet.", // Emergency Session [Absol]
  "absol_emergency3": "\"Point of order!\" shouted the Letnev envoy over the din. \"You cannot call a snap vote while half our delegation is still in transit!\"\n\"Watch me,\" replied the Speaker, tapping the gavel.", // Emergency Session [Absol]
  "absol_emergency4": "The amber lights of an unscheduled convocation bathed the senate floor. When the Council meets without warning, treaties tend to die before breakfast.", // Emergency Session [Absol]
  "travel_ban": "Customs cruisers fanned out across the wormhole apertures, their transponders broadcasting a flat, automated warning. Any civilian vessel attempting transit would be boarded, impounded, or vaporized.", // Enforced Travel Ban
  "sanctions": "No shots were fired, yet the target's economy began to bleed within the hour. Frozen accounts, revoked docking permits, and silent trade lanes can strangle an empire faster than a blockade.", // Executive Sanctions
  "regulations": "\"Three capital ships per sector, maximum,\" the inspector read aloud, peering over his clipboard at the Barony's drydocks. The yard-master spat on the deck and ordered the fourth hull painted like a freighter.", // Fleet Regulations
  "crisis": "Old enemies sat side by side at the war table, staring at the same encroaching threat on the holomap. Hatred is a luxury reserved for empires that expect to survive the year.", // Galactic Crisis Pact
  "defense_act": "Automated planetary defense grids flickered to life across the core worlds. Every citizen slept a little easier knowing the sky above their home was wired to shoot down anything that blinked wrong.", // Homeland Defense Act
  "absol_hyperlane": "Survey ships dropped strings of gravitic beacons through the dead zones between stars. Where once a fleet needed weeks to crawl through the dark, now it could strike in days.", // Hyperlane Development Program [Absol]
  "arbiter": "The golden baton of the Arbiter carries a simple privilege: the right to decide whose voice is heard first, and whose motion dies quietly in the queue.", // Imperial Arbiter
  "incentive": "Nothing motivates a sluggish senate quite like a bounty. The moment the Council attached imperial honors to the frontier objectives, three fleets broke orbit before the ink was dry.", // Incentive Program
  "artifact": "It hummed inside its stasis field like a trapped hornet, older than the Lazax and twice as unforgiving. The Jol-Nar scientists begged to dissect it; the Keleres begged to throw it into a sun.", // Ixthian Artifact
  "abolishment": "With a single gavel strike, a century of precedent vanished from the legal code. The clerks in the archive vaults sighed and began shredding another mountain of parchment.", // Judicial Abolishment
  "minister_antiquities": "Curator of the galaxy's forgotten bones. Every relic pulled from a dead world passes across the Minister's desk, and the best ones rarely make it to the museum.", // Minister of Antiquities
  "minister_commerce": "A quiet nod from the Minister of Commerce can turn a bankrupt mining guild into a galactic powerhouse overnight. Naturally, the waiting room outside their office is always full.", // Minister of Commerce
  "minister_exploration": "\"Push past the rim,\" the Minister's charter reads. \"Chart the anomalies, claim the barren rocks, and report anything that shoots back.\"", // Minister of Exploration
  "minister_industry": "From the orbital foundries of Jord to the forge-rings of Arc Prime, the Minister's seal opens supply lines and keeps the drydocks burning day and night.", // Minister of Industry
  "minister_peace": "The hardest job on Mecatol Rex. Armed with little more than a diplomatic pouch and a veto, the Minister stands between trigger-happy admirals and the next galactic war.", // Minister of Peace
  "minister_policy": "Laws are boring until you are the one writing the amendments. The Minister of Policy shapes the galaxy one footnote at a time.", // Minister of Policy
  "minister_sciences": "Grant money flows like water from the Ministry's coffers, funding breakthroughs that will either usher in a new golden age or accidentally crack a moon in half.", // Minister of Sciences
  "minister_war": "When diplomacy collapses, everyone looks to the figure in the iron-trimmed cloak. The Minister of War keeps the contingency plans updated and the fleets fueled.", // Minister of War
  "miscount": "\"Apologies, esteemed delegates,\" the chief clerk stammered, sweating beneath the chamber's floodlights. \"A calibration error in the voting plinths has... altered the previous tally.\"", // Miscount Disclosed
  "mutiny": "The whisper started in the mess halls and reached the bridge by midnight. When the fleet's captains finally locked the admiral in his quarters, they did it with the quiet blessing of the Council.", // Mutiny
  "constitution": "The old Lazax charters were swept off the lectern in a flurry of yellowing paper. A new age demanded new rules, written by whoever held the loudest voice in the room.", // New Constitution
  "nexus": "Whoever controls Mallice holds a knife to the throat of every wormhole in the galaxy. The Council's decree merely made the land grab official.", // Nexus Sovereignty
  "absol_pax": "Carved in fading gold above the throne of Mecatol Rex, the ancient motto still mocked every senator who passed beneath it. Peace was magnificent, yet every house came armed for glory.", // Pax Magnifica, Bellum Gloriosum [Absol]
  "censure": "The condemned delegate stood alone in the center of the rotunda as the chamber turned its back in unison. Stripped of voting rights and left to stew, they began plotting their revenge before the gavel fell.", // Political Censure
  "absol_sites": "Armed Keleres wardens cordoned off the ancient ruins just as the excavation crews arrived. Some monuments belong to history, even when half the galaxy wants to strip them for parts.", // Preservation of Historical Sites [Absol]
  "prophecy": "Scraped into the obsidian walls of a dead temple on Ixth, the verses spoke of burning skies and a throne of ash. Admirals mocked it as superstition, right until their own ships began to match the omens.", // Prophecy of Ixth
  "execution": "The plaza below the Imperial Palace fell silent as the scaffold's energy field flared. In the Council's eyes, an example made in private is a lesson wasted.", // Public Execution
  "schematics": "The blueprints for the latest capital-ship cannons hit the open net at dawn. By dusk, every backwater shipyard from the Fringe to the Core was welding knockoff prototypes.", // Publicize Weapon Schematics
  "rearmament": "The peace treaties were barely cold before the foundries roared back to life. Every delegate signed the bill with a solemn face, secretly relieved to stop pretending they were done fighting.", // Rearmament Agreement
  "conscription": "Draft boards set up shop on every corner of the rim worlds. The Council promised fair quotas and regular rotations, though the recruits boarding the troop transports knew better.", // Regulated Conscription
  "rep_govt": "\"One world, one voice!\" The smaller houses cheered as the voting blocks were leveled. Across the aisle, the great empires sat in stony silence, already calculating how to buy those voices back.", // Representative Government
  "grant_reallocation": "Half the university labs on Jol-Nar went dark overnight as their funding was redirected to a rival project. Pure science is noble, provided it wins the next border skirmish.", // Research Grant Reallocation
  "warrant": "Keleres cruisers dropped out of warp with Council seals flashing across every channel. \"Power down your engines and prepare to be boarded. Your diplomatic immunity expired five minutes ago.\"", // Search Warrant
  "seed_empire": "Every great dynasty starts with a single bold claim. The Council's recognition turned a modest regional power into a genuine contender for the throne.", // Seed of an Empire
  "shared_research": "Academic rivalry gave way to reluctant cooperation as data-streams linked across the galaxy. Even the most secretive empires had to admit that two minds crack a cipher faster than one.", // Shared Research
  "plowshares": "Rifles were melted down into hull plating, and troop carriers were refitted to haul grain and ore. For a season, the rim worlds remembered what it felt like to build instead of burn.", // Swords to Plowshares
  "absol_limits": "Career senators clutched their desks in horror as the rotation mandate passed. Fresh blood in the Conclave meant old favors were suddenly worthless.", // Term Limits [Absol]
  "unconventional": "When the standard playbooks fail, the Council turns to the quiet specialists in the back rows. Nobody asks how the results are achieved, so long as the report stays clean.", // Unconventional Measures
  "wormhole_recon": "Stabilizer rings locked around the flickering spatial rifts, pulling the distant edges of the galaxy back within striking distance. Traders celebrated; border garrisons doubled their watches.", // Wormhole Reconstruction
  "wormhole_research": "\"Send the probe through,\" the lead physicist ordered, eyes glued to the telemetry. \"If it comes back in one piece, we publish. If it comes back inside-out, we blame the Creuss.\"", // Wormhole Research
};

/** Promissory notes. */
const promissoryNote: LoreMap = {
  "acq": "\"The Custodians remember every debt of deference. When the rightful heirs reclaim the seat of the Lazax, your cooperation will be rewarded in kind.\"", // Acquiescence (Winnu)
  "<color>_an": "An alliance in the Council chambers is a fragile thing, forged in necessity and tested by ambition. For a fleeting moment, two houses speak with a single voice.", // Alliance
  "antivirus": "OVERRIDE.PROTOCOL.77-NULL: TEMPORARY IMMUNITY GRANTED TO DESIGNATED ORGANIC VECTOR.\nNOTE: EXEMPTION IS REVOCABLE UPON COMPLETION OF PRIMARY ASSIMILATION.", // Antivirus (Nekro Virus)
  "bmf": "\"Authentic? My friend, if the Universities can't tell the difference under a quantum scanner, it's good enough for the market. Just don't ask where we got the alloy.\"", // Black Market Forgery (Naaz-Rokha Alliance)
  "blackops": "No banners, no transponder codes, and no official record of the crossing. Firmament operatives leave only the result behind.", // Black Ops (Firmament)
  "blood_pact": "A shared resonance humming in the dark between stars. Where one bleeds, the other answers.", // Blood Pact (Empyrean)
  "<color>_cf": "\"Hold all fire. Lower the targeting arrays and let them pass. Today we choose survival; tomorrow we can talk about glory.\"", // Ceasefire
  "iff": "A shimmering sliver of stolen light, broadcast on a frequency no mortal sensor can parse. To the wormholes, it whispers a single word: friend.", // Creuss Iff (Ghosts of Creuss)
  "crucible": "The rift howled as the hull passed through, steel groaning under the gaze of something ancient and ravenous. The Cabal always collects its toll in blood.", // Crucible (Vuil'raith Cabal)
  "ce": "The neural uplink burned for three seconds before the static cleared. Suddenly, every ship's telemetry moved with the speed of instinct.", // Cybernetic Enhancements (L1Z1X Mindnet)
  "dark_pact": "The Empyrean rarely share what they find in the lightless reaches. When they extend a hand in the void, wise captains take it without asking the price.", // Dark Pact (Empyrean)
  "fires": "\"You want the secret of the suns? Then endure the heat. Let the forge-fires of Muaat temper your hulls, and pray they do not consume you first.\"", // Fires of the Gashlai (Embers of Muaat)
  "gift": "\"You think you are making a choice. In truth, we watched you make it three hours ago. Take this warning, and perhaps you will survive the next one.\"", // Gift of Prescience (Naalu Collective)
  "greyfire": "A single vial of pale, luminescent suspension. The Brotherhood calls it a blessing; those who have seen its effects on a planetary garrison call it a war crime.", // Greyfire Mutagen (Yin Brotherhood)
  "ridera": "When the Argent wing backs a motion on the Conclave floor, their interceptor squadrons make sure every delegate takes the vote seriously.", // Keleres Rider (Argent)
  "riderm": "\"Every captain knows when to hedge a bet. The Keleres offer a rare commodity in this galaxy: a wager backed by the full weight of the Tribunal.\"", // Keleres Rider (Mentak)
  "riderx": "Patience, precedent, and the quiet authority of the Xxcha Tribunal turn a contested vote into a foregone conclusion.", // Keleres Rider (Xxcha)
  "malevolency": "A cold, lingering malice that seeps into the comms and turns allies into rivals. By the time the first shot is fired, the dark is already smiling.", // Malevolency (Obsidian)
  "ms": "Drop-pods punched through the upper atmosphere in neat, disciplined waves. When the Federation of Sol honors a contract, they deliver it in boots and rifle fire.", // Military Support (Federation of Sol)
  "nanolink": "A microscopic lattice woven directly into the ship's superstructure, humming with self-repairing precision. Standard issue for anyone who can afford the license.", // Nano-Link Permit (Ral Nel Consortium)
  "favor": "The Xxcha deal in precedent, quiet counsel, and the gentle art of ensuring their friends are never outvoted.", // Political Favor (Xxcha Kingdom)
  "<color>_ps": "A sealed datachit, passed beneath the Council table without a word. It sits quietly in a pocket until the exact moment it ruins a career.", // Political Secret
  "pop": "\"Consider it an insurance policy, friend. Keep our cut flowing, and our corsairs will look the other way when your freighters cross the Fringe.\"", // Promise of Protection (Mentak Coalition)
  "ragh": "When the war-horns of Ragh sound across the asteroid belts, the Clan of Saar answers. Old grudges fade quickly before the promise of a shared hunt.", // Raghs Call (Clan of Saar)
  "raisethestandard": "\"Let them see the banner unbroken above the ramparts. As long as one soldier stands to hold it, the line has held.\"", // Raise the Standard (Last Bastion)
  "ra": "\"Knowledge is meant to be shared, for a fair consideration. Sign the nondisclosure, and the Universities will open the archives.\"", // Research Agreement (Universities of Jol-Nar)
  "scepter": "Forged in the twilight of the First Empire, the scepter still hums with the genetic command of the Mahact. To hold it is to remember what it means to be obeyed.", // Scepter of Dominion (Mahact Gene-Sorcerers)
  "sever": "Cut the cord, burn the bridge, and leave nothing behind for imperial trackers to follow. The Crimson Rebellion treats every clean break as a victory.", // Sever (Crimson Rebellion)
  "shareknowledge": "Deepwrought charts of the abyssal trenches rarely leave Ikatena. Those who earn access see currents the surface-dwellers never knew existed.", // Share Knowledge (Deepwrought Scholarate)
  "spynet": "You never see the Yssaril courier arrive, nor do you hear them leave. You simply wake to find your rival's battle plans resting neatly on your desk.", // Spy Net (Yssaril Tribes)
  "ambuscade": "Before the enemy dreadnoughts could bring their main batteries to bear, a gleaming crescent of Argent strike craft tore through their flank and vanished into the glare.", // Strike Wing Ambuscade (Argent Flight)
  "stymie": "The spores drifted silently into the command deck's ventilation shafts. Within minutes, the fleet's orders stalled in a sudden, inexplicable lethargy.", // Stymie (Arborec)
  "<color>_sftt": "Pledging one's house to another's claim on Mecatol Rex is the highest currency in galactic politics, and the heaviest shackle.", // Support for the Throne
  "tekklar": "Where the Tekklar Legion marches, the ground trembles and the weak are swept aside. When the N'orr lend you their blades, you point them at a throat and step back.", // Tekklar Legion (Sardakk N'orr)
  "terraform": "Beneath the crust, ancient engines awakened with a low, tectonic groan. In a matter of cycles, barren rock bloomed into a fortress-world worthy of the Titans.", // Terraform (Titans of Ul)
  "cavalry": "\"Didn't expect to see us, did you?\" The Memoria dropped out of warp right across the enemy's bow, guns already blazing. \"Consider your debt paid in full.\"", // The Cavalry (The Nomad)
  "<color>_ta": "A signed manifest stamped by both treasuries can move mountains of ore straight across a warzone.", // Trade Agreement
  "convoys": "Golden-sailed bulk freighters slipped effortlessly through the blockade, their Hacan escorts flashing diplomatic transponders. Commerce, after all, outlives every empire.", // Trade Convoys (Emirates of Hacan)
  "war_funding": "\"Credit is ammunition that hasn't been fired yet. Spend it wisely, and send us the bill with interest.\"", // War Funding (Barony of Letnev)
};

/** Public objectives. */
const publicObjective: LoreMap = {
  "supremacy": "When a flagship drops out of warp directly over a rival's capital, diplomacy ends. The shadow of that hull tells the galaxy who owns the sky.", // Achieve Supremacy
  "amass_wealth": "Full vaults, loyal bureaucrats, and humming foundries. An empire built on all three can outlast any storm.", // Amass Wealth
  "become_legend": "Generations from now, pilots will still point to the scarred nebulae and ancient worlds on the star-charts and speak your name in hushed tones.", // Become a Legend
  "build_defenses": "Orbital batteries locked into position above the colonies, their targeting grids painting the void in quiet red. Let the raiders come.", // Build Defenses
  "centralize_trade": "Every shipping lane, tariff, and bulk freighter now passes through your customs gates. If the galaxy wants to eat, it pays your toll.", // Centralize Galactic Trade
  "command_armada": "Eight capital ships aligned in tight formation, their drives burning bright enough to rival a local star. Even the Barony's admirals paused to count the hulls.", // Command an Armada
  "conquer": "Your boots stand on the soil of their ancestral world. The banner above their capital belongs to you now, and their people know it.", // Conquer the Weak
  "massive_cities": "Arcologies pierced the cloud layer while orbital docks ringed the equator in steel. What began as frontier outposts had grown into monuments of imperial permanence.", // Construct Massive Cities
  "control_borderlands": "Out on the galactic rim, law is whatever the local patrol squadron says it is. Your cruisers own every jump-point along the edge of the dark.", // Control the Borderlands
  "corner": "Whether it is rare isotopes, fertile soil, or industrial alloys, your consortium holds the supply. Everyone else can beg for a quota.", // Corner the Market
  "develop": "The old hulls were fine for border skirmishes. These new frames were built to break empires.", // Develop Weaponry
  "lost_outposts": "Beneath layers of dust and forgotten Lazax seals, the excavation teams struck gold. The old empire left plenty of toys behind for those willing to dig.", // Discover Lost Outposts
  "diversify": "A single discipline wins a battle. Mastery across multiple fields wins the century.", // Diversify Research
  "engineer_marvel": "The drydock clamps fell away, revealing a silhouette that dwarfed every cruiser in the sector. \"She's ready,\" the chief engineer whispered. \"God help whoever sees her first.\"", // Engineer a Marvel
  "monument": "Half a sector's ore went into the marble and durasteel spires. Practical men called it a waste of resources, yet every envoy who saw it lowered their eyes.", // Erect a Monument
  "expand_borders": "The frontier maps had to be redrawn three times this cycle. Every week, another distant world swore fealty to the new flag.", // Expand Borders
  "deep_space": "There are no cities in the empty reaches between stars, only cold vacuum and hidden jump-lanes. Your scouts charted them all before anyone else dared look.", // Explore Deep Space
  "brain_trust": "The brightest minds from five different worlds linked their data-cores into a single lattice. By morning, they had solved problems the Universities had shelved for decades.", // Form Galactic Brain Trust
  "golden_age": "Art flourished, granaries overflowed, and the shipyards sang day and night. For one shining era, the galaxy looked to your worlds and saw what the Lazax had lost.", // Found a Golden Age
  "research_outposts": "Prefabricated labs clung to the jagged cliffs of the frontier worlds, their dishes tuned to the anomalies overhead. Knowledge waits for whoever claims the high ground.", // Found Research Outposts
  "galvanize": "Recruitment halls stayed open past midnight as volunteers lined up by the thousands. When an entire people moves with one purpose, logistics become a formality.", // Galvanize the People
  "vast_reserves": "While neighboring empires scraped the bottom of their treasuries to fund the next campaign, your quartermasters calmly opened a second vault.", // Hold Vast Reserves
  "infrastructure": "New spaceports, planetary shields, and supply depots rose across the outer colonies. A conquered world stays conquered only when you pave the roads.", // Improve Infrastructure
  "intimidate": "Two battle fleets loitered just outside the Mecatol Rex exclusion zone, weapons cold and transponders loud. The senators inside the rotunda got the message.", // Intimidate Council
  "lead": "The admiral's shuttle was the first to breach the atmosphere. Soldiers fight harder when their commanders share the same mud and flak.", // Lead From the Front
  "make_history": "Ordinary empires cling to safe trade routes. Great ones plant their banners where the star-charts still say 'here be monsters.'", // Make History
  "manipulate_law": "A quiet word in the corridor, a well-timed favor, and a mountain of diplomatic leverage. By the time the vote was called, the outcome had been decided for days.", // Manipulate Galactic Law
  "master_science": "Propulsion, cybernetics, warfare, and biology: every branch of galactic science bowed to your academies. The Jol-Nar envoys stopped laughing.", // Master the Sciences
  "trade_routes": "Convoy schedules aligned across a dozen sectors, turning former rivals into reluctant business partners. Credits flow smoother when everyone gets a taste.", // Negotiate Trade Routes
  "vast_territories": "Long-range pickets swept the dead zones between systems in endless, silent loops. Nothing crosses the void without your sensors logging its signature.", // Patrol Vast Territories
  "outer_rim": "Settlers poured onto the windswept worlds at the galaxy's edge, raising domes against the dark. The core worlds sneered, right until the rim started producing fleets.", // Populate the Outer Rim
  "protect_border": "A chain of fortified worlds stretched along the frontier like iron teeth. Any invader looking for an easy flank would have to chew through steel first.", // Protect the Border
  "push_boundaries": "Your neighbors watched nervously as your survey beacons crept closer to their core systems. In a crowded galaxy, hesitation is surrender.", // Push Boundaries
  "raise_fleet": "Five warships broke orbit in unison, their engines painting blue streaks across the night sky. The drydocks had delivered on their promise.", // Raise a Fleet
  "ancient_monuments": "The monoliths hummed back to life as your engineers cleared the rubble. Whatever ancient hands raised them, they answer to your empire now.", // Reclaim Ancient Monuments
  "revolutionize": "Every doctrine in the imperial war colleges became obsolete overnight. Your upgraded divisions tore through conventional formations before the enemy could adjust.", // Revolutionize Warfare
  "distant_lands": "Two rival homeworlds, both within striking distance of your forward garrisons. Let them sleep with one eye on the sky.", // Rule Distant Lands
  "subdue": "Eleven worlds, eleven surrendered capitals, and one unbroken chain of supply lines. The galaxy was running out of places to hide.", // Subdue the Galaxy
  "sway_council": "When your ambassador stepped up to the podium, the chatter in the gallery died instantly. Influence is the art of making people agree with you before you even ask.", // Sway the Council
  "unify_colonies": "Six worlds of shared heritage, bound under a single charter and a single fleet. What distance had divided, ambition brought home.", // Unify the Colonies
};

/** Secret objectives. */
const secretObjective: LoreMap = {
  "ans": "The old manuals were written for the last war. Your commanders tossed them out the airlock and wrote a new doctrine tailored to their own strengths.", // Adapt New Strategies
  "bam": "The homeworld burned, and the broadcasts carried every frame to the outer colonies. Grief is a sharp blade when you know how to aim it.", // Become a Martyr
  "btgk": "Two cruisers held station at opposite ends of the rift, their transponders pulsing in tandem. Anyone wishing to cross the galaxy would have to ask permission first.", // Become the Gatekeeper
  "baf": "\"We had a treaty!\" the rival admiral shouted over the open channel as your cruisers opened fire.\n\"We had an arrangement,\" your captain replied, calmly ordering a second salvo. \"It just expired.\"", // Betray a Friend
  "btv": "Radiation clawed at the hull plating and the sensors went blind, yet the gunners kept firing by dead reckoning. Winning in the deep dark takes steadier nerves than winning in the light.", // Brave the Void
  "ctr": "Six sectors, six patrol flags, and an unbroken grid of listening posts. Anyone moving through this quadrant is walking across your front porch.", // Control the Region
  "csl": "The enemy's orbital shipyard sat helpless beneath your dreadnought's shadow, its half-finished hulls cooling in the vacuum. Starve the docks, and the war ends on its own.", // Cut Supply Lines
  "dts": "The citizens of their capital looked up expecting their own defense fleet. Instead, your banners blotted out the noon sun.", // Darken the Skies
  "dfat": "Inside the wormhole nexus, gravity bends sideways and stars hang in the wrong places. Your crews anchored there anyway, claiming the crossroads of the galaxy.", // Defy Space and Time
  "dyp": "When the smoke cleared, three of your capital ships still held formation amid the wreckage. The survivors on the enemy bridge got the message loud and clear.", // Demonstrate Your Power
  "dhw": "The ancient fragments hissed as they dissolved in the plasma furnace. Some relics from the old empire deserve to stay buried.", // Destroy Heretical Works
  "dtgs": "The pride of their navy cracked down the keel, venting atmosphere and golden light into the void. Every ship in the sector paused to watch a giant die.", // Destroy Their Greatest Ship
  "dp": "Three laws on the books, each one stamped with your subtle amendments. The Council thinks it governs the galaxy; your clerks know better.", // Dictate Policy
  "dtd": "By the time the Speaker called the question, half the chamber was already repeating your talking points word for word. Steering a senate is all about picking the right microphone.", // Drive the Debate
  "eap": "Four planetary defense grids hummed in unison along the frontier. Any fleet looking for a shortcut through your space is going to pay for every kilometer in hull plating.", // Establish a Perimeter
  "eh": "Senators, governors, and trade magistrates across a dozen worlds all waited for your nod before signing a single decree. Power sounds quiet when nobody dares argue with you.", // Establish Hegemony
  "fwp": "Before the enemy swarm could even lock weapons, your destroyers painted the sky in flak. A hundred fighters vanished in a single, blinding heartbeat.", // Fight with Precision
  "faa": "Artists, diplomats, and archivists from four proud worlds gathered under one roof. Shared culture binds an empire tighter than any garrison.", // Forge an Alliance
  "fsn": "Five separate cells, three forged identities, and a mountain of burned cipher-pads. Your spymasters knew what the enemy was planning before their own admirals did.", // Form a Spy Network
  "fc": "Your envoys kept an open channel to every throne room in the galaxy. Good fences make good neighbors, and a fleet on every border makes them polite.", // Foster Cohesion
  "fwm": "Three massive orbital foundries glowed orange against the dark, spitting out fresh hulls around the clock. Wars are won in the drydocks long before the first shot is fired.", // Fuel the War Machine
  "gamf": "Five dreadnoughts dropped out of warp in a single iron wall, their bow cannons charging in lockstep. Smaller ships turned tail before the targeting locks even chimed.", // Gather a Mighty Fleet
  "hrm": "Ore barges queued three deep at every orbital refinery. While other houses rationed fuel, your warehouses were bursting at the seams.", // Hoard Raw Materials
  "lsc": "Your survey ships lingered at the edges of gravity wells and asteroid storms, drinking in data that would fry a standard nav-computer. The void keeps its secrets for those brave enough to listen.", // Learn the Secrets of the Cosmos
  "mew": "The orbital batteries fired until the fortress walls turned to glass. \"Let the neighboring worlds see the glow,\" the commander ordered. \"They'll surrender faster.\"", // Make an Example of Their World
  "mlp": "Four breakthroughs in a single discipline, stacked one atop the other until the old textbooks read like children's stories. The galaxy's laws bent to your equations.", // Master the Laws of Physics
  "mtm": "Heavy walkers stomped off the drop-ramps on four different worlds, their armor shrugging off small-arms fire. Infantry holds the line; mechs break it.", // Mechanize the Military
  "mrm": "Acid rain ate through the drill casings, and seismic tremors shook the rigs every hour. The isotopes pulled from those hellholes were worth every bruised knuckle.", // Mine Rare Metals
  "mp": "Four industrial worlds, all running triple shifts under your house's seal. If the galaxy wants steel, circuitry, or starship plating, it buys from you.", // Monopolize Production
  "otf": "Nine divisions dug into the red dirt of a backwater rock miles from any friendly shipyard. They had no docks and no backup, only rifles and stubbornness.", // Occupy the Fringe
  "ose": "Three warships hung motionless above the ruined spires of Mecatol City while your troops secured the palace gates. The throne of the Lazax had a new tenant.", // Occupy the Seat of the Empire
  "pem": "Assembly lines screamed at maximum tolerance as hulls, fighters, and transports rolled off the gantries in an endless tide. Quantity has a brutal elegance all its own.", // Produce en Masse
  "pe": "One by one, the other empires wound down their operations and recalled their fleets for the cycle. Your bridges stayed lit until dawn, squeezing one last move out of an exhausted galaxy.", // Prove Endurance
 "sai": "Every spacer knew the stories about this world: the strange ruins, the impossible skies, the power buried beneath its crust. Now your flag flies over the legend.", // Seize an Icon
  "sar": "The frontrunner's fleet expected an easy patrol. Instead, your cruisers ambushed them from the sunward side and reminded the galaxy that giants still bleed.", // Spark a Rebellion
  "syc": "Your troops planted their banner on the neighboring moon, right in full view of the rival garrison's telescopes. Sharing a system is a polite way of starting an argument.", // Stake Your Claim
  "sb": "A signed pledge from a rival house sat locked in your safe. In galactic politics, leverage is the warmest blanket you can own.", // Strengthen Bonds
  "te": "Your patrol ships loitered just one jump from their homeworld, running live-fire drills in full view of their early-warning buoys. Nobody slept well in their capital that week.", // Threaten Enemies
  "ttfd": "Long-range orbital cannons flashed once from the planet's surface, and the invading vanguard dissolved into expanding clouds of superheated debris.", // Turn Their Fleets to Dust
  "uf": "The flagship's keel-mounted cannon lit up the void, tearing through the enemy line on its maiden engagement. Rumors of its power had been terrifying; the reality was worse.", // Unveil Flagship
};

/** Technologies. */
const technology: LoreMap = {
  "helios2": "Orbital cranes locked around the reinforced superstructure as the Helios V2 spun up its fusion core. Built to survive a siege, the station can churn out fresh hulls even while taking direct fire.", // 4X41C "Helios" V2
  "ac2": "Reinforced flight decks and expanded troop bays turned the Federation's workhorse into a mobile invasion force. When an Advanced Carrier drops into orbit, an entire continent holds its breath.", // Advanced Carrier II
  "ah": "\"Project the decoys two hundred klicks to port,\" the Argent commander ordered. The enemy fleet wasted three full salvos shredding ghosts of light while the real defenders closed in.", // Aerie Hololattice
  "as": "Ordinary navigators plot around nebulae and gravity wells. The Empyrean ride the currents inside them, slipping across entire sectors on invisible tides.", // Aetherstream
  "asn": "A single encrypted requisition code routes spare parts, fuel cells, and fresh hulls from any friendly drydock in the sector. The Keleres rarely run dry.", // Agency Supply Network
  "aida": "The heuristic core ran ten thousand simulations of the coming battle before the admiral finished his coffee, then quietly redesigned the cruiser's main battery.", // AI Development Algorithm
  "amd": "\"Full ahead through the debris field!\" The hull hummed as the deflectors flickered blue, batting aside house-sized boulders like pebbles.", // Antimass Deflectors
  "asc": "Three capital ships aligned their prows, linking their capacitors into a single blinding arc. Whatever sits at the focal point ceases to exist before the main engagement even begins.", // Assault Cannon
  "bs": "A sharp hiss against the neck, a rush of cold fire through the veins, and suddenly a forty-eight-hour shift feels like a brisk morning walk.", // Bio-Stims
  "bio": "The vines crept silently from the transport's open ramp, rooting themselves into the soil of the neighboring moon before dawn.", // Bioplasmosis
  "cv2": "Wider hangar doors, faster launch catapults, and thicker ventral armor. A Carrier II delivers its payload straight into the teeth of planetary flak.", // Carrier II
  "cm": "To everyone else, an asteroid field is a graveyard. To the Clan of Saar, it is a highway with built-in cover.", // Chaos Mapping
  "cl2": "Cloned from the ancient warrior-castes of the First Empire and conditioned to feel neither pain nor doubt. When a Legionnaire falls, another steps out of the vat with the same memories.", // Crimson Legionnaire II
  "cr2": "Faster than a dreadnought and meaner than a destroyer, the upgraded cruiser strikes deep behind enemy lines before the picket fleets can even turn around.", // Cruiser II
  "dxa": "\"Don't leave the dead behind,\" the medic muttered, priming the injector rig. \"The flesh still has another fight left in it.\"", // Dacxive Animators
  "det": "Deep in the unlit reaches between stars, specialized collectors siphon stray quantum energy from the vacuum itself. Nothing out there is truly empty.", // Dark Energy Tap
  "dd2": "Quad-mounted flak batteries turned the humble escort hull into a shredder of fighter screens. Swarm tactics die quickly under a wall of shrapnel.", // Destroyer II
  "ds": "The Creuss navigator twisted a single dial, and the wormhole aperture flared violent magenta. Space itself folded inward, shearing the enemy cruiser cleanly in half.", // Dimensional Splicer
  "dt2": "The rift widened with a wet, tectonic crack, bleeding violet haze across the system. Ships that drift too close to the Cabal's tear rarely emerge in the same century.", // Dimensional Tear II
  "dn2": "Layered armor plating and redundant power cores make the Dreadnought II a floating fortress. Even direct hits from orbital cannons leave little more than scorch marks.", // Dreadnought II
  "da": "Forged in zero-gravity kilns, duranium alloy bends under plasma fire instead of shattering. Crews joke that the hull outlives the people inside it.", // Duranium Armor
  "ers": "\"Let them shoot,\" the Jol-Nar dean said calmly, watching the shield telemetry spike. \"Every megajoule they waste on our hulls goes straight into our research fund.\"", // E-Res Siphons
  "executiveorder": "Stamped with the highest clearance seal and transmitted on priority band zero. Debate ends the moment the directive hits the table.", // Executive Order
  "exile2": "Stripped of excess weight and coated in sensor-eating matte black, the Exile II slips past perimeter buoys like smoke.", // Exile II
  "exo2": "The N'orr captain locked the thrusters at maximum burn and aimed straight for the enemy flagship's bridge. If the Exotrireme goes down, it takes the whole formation with it.", // Exotrireme II
  "ff2": "Independent jump-drives and upgraded thrusters freed the Fighter II from its carrier's leash. A squadron can now hunt across an entire sector on its own.", // Fighter II
  "fl": "\"Why wait for the first wave to report back?\" the fleet marshal asked, tapping two targets on the holomap. \"Launch both operations simultaneously.\"", // Fleet Logistics
  "ffac2": "Massive thruster banks roared to life beneath the orbital shipyard, dragging an entire industrial complex into the next system at flank speed.", // Floating Factory II
  "gr": "With a whisper and a pulse of the gene-sorcerer's staff, the opposing senator's posture stiffened. When the vote was called, he raised his hand against his own house.", // Genetic Recombination
  "gls": "Focused gravitic beams punch clean through fighter screens, forcing enemy commanders to watch their capital ships take the brunt of the planetary barrage.", // Graviton Laser System
  "gd": "By pinching the gravity well directly ahead of the bow, a warship can cross light-years in a single, stomach-churning lurch.", // Gravity Drive
  "htp": "The Winnu governor signed the tariff decree without looking up. Under the old imperial charters, every industrial world owes its surplus to the throne.", // Hegemonic Trade Policy
  "ht2": "Ancient stone peeled away to reveal gleaming plasma barrels and heavy kinetic shields. The Hel-Titan II guards its world with the patience of a mountain.", // Hel-Titan II
  "hcf2": "Grown from resonant crystal and linked directly to the pilot's nervous system, the Naalu interceptors turn sharply enough to crush an organic crew.", // Hybrid Crystal Fighter II
  "hydrothermal": "Deep beneath the crushing ocean floor, automated rigs tap superheated volcanic vents, pulling rare minerals straight from the planet's molten heart.", // Hydrothermal Mining
  "hm": "Engineered enzymes cut sleep cycles in half and sharpen reflexes across the entire corps. An empire that never rests always moves first.", // Hyper Metabolism
  "ic": "\"Arm the core and cut the stabilizers,\" the Yin captain whispered to his crew. \"Our light will clear the path for the brothers behind us.\"", // Impulse Core
  "inf2": "Powered exo-frames, smart-linked rifles, and rapid-response med-injectors. Even when a squad falls, half of them are back on their feet before the dust settles.", // Infantry II
  "is": "Buried deep in the Mindnet's core lie the decrypted blueprints of the ancient Lazax. The L1Z1X simply pull whatever weapon the moment demands.", // Inheritance Systems
  "it": "\"Hold your nerve,\" the Xxcha master told his apprentice as the warning klaxons blared. \"Panic makes you predictable; stillness lets you ruin their plan.\"", // Instinct Training
  "ie": "The ink on the planetary surrender was barely dry before the local factories switched over to producing hulls for their new masters.", // Integrated Economy
  "l4": "High-frequency jamming beams blind planetary defense grids from orbit, leaving the ground garrisons staring helplessly at an open sky.", // L4 Disruptors
  "lgf": "Hidden beneath the ruins of Mecatol City lies a dormant transit gate from the First Empire. Only the Winnu still remember the sequence to wake it.", // Lazax Gate Folding
  "lw2": "Hardened bark-plates and rapid spore-regeneration turn every Letani soldier into a walking fortress. Burn one down, and two more sprout from the ash.", // Letani Warrior II
  "lwd": "Phase-shifted shields allow an entire battle group to slip straight through an enemy blockade as if the opposing hulls were made of mist.", // Light/Wave Deflector
  "linkship2": "Interlocking sensor arrays turn every Linkship II into a floating relay tower, feeding real-time firing solutions across the entire consortium fleet.", // Linkship II
  "md": "The planetary shield grid hummed with lethal feedback, turning every automated defense bunker into a meat grinder for incoming drop-troops.", // Magen Defense Grid ΩΩ
  "mi": "\"A tiny sliver of wetware behind the ear,\" the Yssaril handler smiled. \"He doesn't even know he's broadcasting his admiral's private correspondence.\"", // Mageon Implants
  "mr": "Tapping the volcanic fury of a world's mantle powers the Muaat war-forges, letting them cast starships in rivers of liquid rock.", // Magmus Reactor
  "m2": "Upgraded with stolen schematics from three different timelines, the Memoria II hits harder, flies faster, and never arrives a second too late.", // Memoria II
  "mc": "\"Why settle for face value when you can double the ledger before the ink dries?\" The Mentak quartermaster tapped the encrypted abacus and grinned.", // Mirror Computing
  "nanomachines": "Microscopic repair swarms crawl across scorched hull plating in the middle of a firefight, stitching breaches shut before the air even escapes.", // Nanomachines
  "nm": "A steady drip of nootropics and neural-link training keeps the command staff two moves ahead of every rival in the sector.", // Neural Motivator
  "parasite-firm": "It slips into the host's brainstem without leaving a mark. By the time the victim notices a stray thought, the Firmament already owns the room.", // Neural Parasite (Firmament)
  "parasite-obs": "Once the Obsidian seed takes root, the host's loyalty rots from the inside out, leaving an empty shell eager to open the airlocks.", // Neural Parasite (Obsidian)
  "ng": "\"If they want to enter our space, let them pay for the privilege in blood and shattered nerves,\" the Naalu matriarch hissed.", // Neuroglaive
  "nes": "Letnev shield harmonics fold incoming laser fire into impossible angles, absorbing blasts that would vaporize a conventional hull.", // Non-Euclidean Shielding
  "nf": "A single pulse from the Xxcha flagship killed every thruster and weapons lock in the system. The invading fleet drifted silently, powerless to fire a shot.", // Nullification Field
  "pds2": "Upgraded targeting optics and long-range plasma rails extend planetary defense fire well into neighboring systems. Trespassers learn the range the hard way.", // PDS II
  "planesplitter-firm": "The device hums at a frequency that makes reality feel thin, peeling back hidden corridors for agents who prefer to leave no footprints.", // Planesplitter (Firmament)
  "planesplitter-obs": "A jagged tear opened in the middle of the command deck, spilling cold, starless dark across the floor. The Obsidian had arrived.", // Planesplitter (Obsidian)
  "ps": "Overclocked magnetic coils squeeze one extra superheated bolt out of every cannon cycle. Gunners love the punch; engineers hate the melted barrels.", // Plasma Scoring
  "pfa": "Drop the pod, trigger the foam-concrete charges, and by sunrise a barren rock boasts a fortified dome city complete with power grids.", // Pre-Fab Arcologies
  "pi": "Behavioral algorithms map every senator's tells, debts, and habits, predicting how the Council will vote days before the session opens.", // Predictive Intelligence
  "pm": "Domed biosphere farms turn even the harshest desert moons into lush agricultural engines, keeping Hacan trade coffers overflowing.", // Production Biomes
  "pws2": "The Gashlai refined their deadliest creation into a sleeker, faster engine of ruin. When a Prototype War Sun II accelerates, entire sectors clear the lane.", // Prototype War Sun II
  "proxima": "Automated fire-control routines calculate six thousand trajectories a second, dropping orbital support shells within meters of friendly trenches.", // Proxima Targeting VI
  "pa": "By reading the residual psychic imprints left in ancient stone, researchers can unlock alien vaults without ever finding the physical key.", // Psychoarchaeology
  "qdn": "\"Information moves faster than freighters, friend. Pay the access fee, and the Emirates will tell you what your rivals are planning before they do.\"", // Quantum Datahub Node
  "radical": "Conventional peer review takes decades. The Deepwrought prefer bold leaps in the dark, discarding broken theories as fast as they build new ones.", // Radical Advancement
  "so": "\"Waste nothing!\" the corsair chief barked as the grappling drones latched onto the drifting wreck. \"Their scrap metal is our next cruiser.\"", // Salvage Operations
  "st": "Precision laser-welders and modular assembly rigs shave weeks off every drydock schedule. Cheap, reliable, and indispensable across the galaxy.", // Sarween Tools
  "se2": "Sleek, heavily armed, and built for rapid deployment, the Saturn Engine II carries the Titans' wrath across the stars at terrifying speed.", // Saturn Engine II
  "sdn": "Swarms of palm-sized recon drones sweep every newly secured world, mapping subterranean vaults and forgotten supply caches in minutes.", // Scanlink Drone Network
  "sar": "Automated micro-forges inside the drop-bays stamp out fresh armored walkers straight from raw ore, keeping the front line stocked without a shipyard.", // Self-Assembly Routines
  "sr": "Gravitational catapults sling freshly commissioned ships straight from the orbital dock into active combat formation.", // Sling Relay
  "sd2": "Expanded drydock rings and triple-shift assembly gantries turn a standard orbital station into a relentless war-machine.", // Space Dock II
  "scc": "The Jol-Nar flagship folded local space like a sheet of paper, allowing an entire armada to step straight from the university homeworld to the front line.", // Spatial Conduit Cylinder
  "so2": "\"We go in first, we hold until dawn, and we don't ask for extraction.\" The Federation's elite drop-troopers earn their reputation in the mud.", // Spec Ops II
  "swa2": "Reinforced wings and twin flak pods turned the Argent destroyer into the undisputed king of close-range dogfights.", // Strike Wing Alpha II
  "subatomic": "By shearing molecular bonds at the target's core, the rebellion's cannons turn heavy cruiser armor into brittle dust.", // Subatomic Splicer
  "sdn2": "Larger, darker, and bristling with cybernetic targeting arrays, the Super Dreadnought II is the Mindnet's final argument.", // Super Dreadnought II
  "sc": "\"Bypass the safety limiters and dump the reserve cells into the guns!\" The Rokha gunner laughed as the console sparked. \"We'll fix the wiring after we win!\"", // Supercharge
  "tcs": "A flick of the chronometer resets the last ten seconds on the bridge, letting the Nomad's officers dodge ambushes that already happened.", // Temporal Command Suite
  "td": "Quantum-entangled pads blink entire infantry divisions across light-years in a flash of ozone and static.", // Transit Diodes
  "tp": "Clear as glass and harder than titanium, the Yssaril alloy lets their ambushers watch the enemy walk right into the kill zone.", // Transparasteel Plating
  "vax": "ASSIMILATION.PROTOCOL.X: FOREIGN TECH SIGNATURE ACQUIRED.\nREWRITING HOST ARCHITECTURE TO MATCH SUPERIOR DESIGN.", // Valefar Assimilator X
  "vay": "ASSIMILATION.PROTOCOL.Y: SECONDARY VECTOR LOCKED.\nALL INNOVATION BELONGS TO THE VIRUS.", // Valefar Assimilator Y
  "vpw": "Every blow landed against N'orr infantry triggers a violent counter-discharge, turning close-quarters combat into mutual slaughter.", // Valkyrie Particle Weave
  "vw": "Invisible tripwires woven into the dark between stars chime softly on Empyrean bridges whenever an uninvited hull crosses the border.", // Voidwatch
  "vtx": "The dimensional tear reached across the vacuum like a starving hand, plucking an unsuspecting cruiser straight out of its neighboring system.", // Vortex
  "ws": "A miniature star caged in durasteel and bristling with planet-cracking batteries. When a War Sun enters a system, treaties suddenly become very flexible.", // War Sun
  "wg": "\"No wormhole in this sector?\" the Creuss captain murmured, priming the emitter. \"Give me thirty seconds.\"", // Wormhole Generator
  "x89c4": "A single canister dropped into the upper atmosphere strips a fortress world of every living defender while leaving the buildings spotless.", // X-89 Bacterial Weapon ΩΩ
  "yso": "Rows of humming gestation pods line the Yin transports, ensuring that for every brother lost in the trenches, fresh reinforcements are already lacing their boots.", // Yin Spinner Omega
};

/** Breakthroughs (Thunder's Edge). */
const breakthrough: LoreMap = {
  "naazbt": "\"You handle the targeting lattice, I'll take the thrusters!\" The Naaz pilot grinned inside the cockpit as the Rokha gunner locked six targets at once. \"Try to keep up, little brother.\"", // Absolute Synergy (Naaz-Rokha)
  "cabalbt": "Static bleeds across every long-range channel before the rift even appears. Navigators call the low, tearing sound behind the interference Al'Raith Ix Ianovar.", // Al'Raith Ix Ianovar (Vuil'raith Cabal)
  "xxchabt": "The Archon's envoy offered no ultimatums, only a sealed shield-charter and a quiet promise that the Kingdom remembers its friends when the storm breaks.", // Archon's Gift (Xxcha)
  "hacanbt": "Rows of automated gantries glowed orange across the Arretze shipyards, welding hulls around the clock without a single crew shift change.", // Auto-Factories (Hacan)
  "solbt": "\"Check your seals, lock your rifles, and look at the man beside you!\" The drop-sergeant hammered the bulkhead as the bay doors hissed open. \"Let's show them what glory looks like!\"", // Bellum Gloriosum (Sol)
  "ralnelbt": "Ral Nel brokers rarely bother decrypting a rival's full archive. A clean skim of the routing headers and cargo manifests tells them everything worth selling.", // Data Skimmer (Ral Nel)
  "yssarilbt": "\"Their security chief boasted that his network was impenetrable. He's right, of course. We didn't break in; we've been living inside his kernel since Tuesday.\"", // Deepgloom Executable (Yssaril)
  "saarbt": "Saar tug-crews bolted spare thrusters onto three million tons of iron-rich asteroid and nudged it into a decaying orbit. Gravity handled the rest of the siege.", // Deorbit Barrage (Saar)
  "l1z1xbt": "A single burst of encrypted code overrode the allied fleet's manual helms. Hesitation vanished from the formation as every cannon aligned to the Mindnet's rhythm.", // Fealty Uplink (L1Z1X)
  "letnevbt": "\"Helm, hook the gravity well and sling us around the moon!\"\n\"My Lord, the keel will snap!\"\n\"Then let it snap after we've cleared their flank. Execute!\"", // Gravleash Maneuvers (Letnev)
  "keleresbt": "Reinforced blast doors, fresh sensor spires, and direct feeds to every listening post in the Core turned the old Keleres headquarters into an active war room.", // I.I.H.Q. Modernization (Keleres)
  "winnubt": "\"Kneel, and address the throne by its proper title. The Custodians kept the seat warm long enough; now the Imperator speaks.\"", // Imperator (Winnu)
  "naalubt": "The Collective's telepaths drifted silently through the minds of the enemy staff, sifting buried contingency plans straight to the surface.", // Mindsieve (Naalu)
  "sardakkbt": "Treaties and clever machinery mean little when N'orr shock troops breach the hull. In the crush of close quarters, the swarm always takes the deck.", // N'orr Supremacy (Sardakk N'orr)
  "ghostbt": "Inside the Creuss gates, matter and light behave like notes on the same scale. Whole squadrons emerge on the far side rebuilt down to the atom.", // Particle Synthesis (Ghosts of Creuss)
  "arborecbt": "Pale spores drifted through the colony's air vents until the garrison's frantic radio chatter softened into a single, steady hum.", // Psychospore (Arborec)
  "crimsonbt": "\"Crank the coils past redline!\" shouted the rebel engineer over the screaming turbines. \"If they want to trap us in this sector, we'll tear the whole frequency apart!\"", // Resonance Generator (Crimson Rebellion)
  "titansbt": "For ten thousand cycles the Titans dreamed in stone, running every permutation of the coming war while younger species were still learning to smelt bronze.", // Slumberstate Computing (Titans of Ul)
  "jolnarbt": "Two drops of Compound Nine boosted the subject's neural output by four hundred percent. The Jol-Nar lab notes relegated spontaneous combustion to a brief footnote.", // Specialist Compounds (Jol-Nar)
  "muaatbt": "Superheated plasma spiraled inward at the Gashlai's command, igniting a newborn star where empty void had stretched minutes before.", // Stellar Genesis (Muaat)
  "bastionbt": "Above the artillery smoke, the beacon atop the citadel spire burned steady and white. As long as the Icon stood unbroken, the garrison refused to yield a meter.", // The Icon (Last Bastion)
  "obsidianbt": "Sector beacons flickered out one by one along the rim, plunging the frontier worlds into cold silence just before the Obsidian blades arrived.", // The Reaping (Obsidian)
  "firmamentbt": "A quiet rumor in a border tavern, a forged pamphlet left in a barracks. The Firmament plants its seeds months before an empire realizes it is tearing itself apart.", // The Sowing (Firmament)
  "mentakbt": "\"Sit down, pour yourself a glass, and stop reaching for your sidearm. At my table, everyone gets a fair cut, right up until they try to cheat the house.\"", // The Table's Grace (Mentak)
  "nomadbt": "\"I already watched this battle end poorly three weeks from now. Trust me on this one: turn hard to port on my mark, and don't ask how I know.\"", // Thunder's Paradox (Nomad)
  "nekrobt": "VALEFAR.Z.INIT: SUPERIOR BIOMECHANICAL TEMPLATE DETECTED.\nOVERRIDING HOST ARCHITECTURE. RESISTANCE PROBABILITY: 0.004%.", // Valefar Assimilator Z (Nekro)
  "mahactbt": "Ancient stasis seals hissed open beneath the Plateau Imperia, revealing weapons forged before the Lazax ever sat the throne.", // Vaults of the Heir (Mahact)
  "deepwroughtbt": "Far beneath the ocean floor, Visionaria researchers cataloged phenomena that surface-bound academies had dismissed as myth.", // Visionaria Select (Deepwrought)
  "empyreanbt": "Shimmering anchors locked into the empty dark between stars, stringing a stable highway across a void no conventional drive could cross.", // Void Tether (Empyrean)
  "argentbt": "\"Vanguard Two, peel off and reinforce the eastern picket!\"\n\"Copy, Wing Leader. Shifting formation; those dreadnoughts won't even see us cross the sun!\"", // Wing Transfer (Argent)
  "yinbt": "One brother falls in the breach, and ten more step forward wearing the same face and the same unshakable faith.", // Yin Ascendant (Yin)
};

/** Faction abilities. */
const ability: LoreMap = {
  "aetherpassage": "\"Lower the void-screens and grant them safe transit,\" the Empyrean captain signaled. \"They may cross our dark, provided they remember who holds the lantern.\"", // Aetherpassage (Empyrean)
  "amalgamation": "Captured hulls are dragged screaming into the dimensional tear, melted down, and spat back out as warped, predatory engines of Cabal flesh and steel.", // Amalgamation (Vuil'raith Cabal)
  "ambush": "Before the rival flagship could even raise its shields, two Mentak cruisers slipped out of the asteroid shadow and raked its bow with point-blank fire.", // Ambush (Mentak)
  "analytical": "Jol-Nar scholars view every battlefield as an open-book exam, cross-referencing decades of archived theory to skip straight to the final equation.", // Analytical (Jol-Nar)
  "arbiters": "When two empires refuse to speak to each other, they both speak to the Hacan. For a modest commission, the Emirates keep the galaxy's deals moving.", // Arbiters (Hacan)
  "armada": "Where other houses see a logistical nightmare, the Barony sees a proper formation. Letnev admirals pack the sky with iron until the stars disappear.", // Armada (Letnev)
  "assimilate": "The conquered spaceport hummed as L1Z1X drones stripped its local servers and welded it directly into the Mindnet. Resistance ended in thirty seconds.", // Assimilate (L1Z1X)
  "awaken": "Deep beneath the moss and rubble, ancient stone eyes flickered open. The Titans had slept for millennia; now the intruders had rung the bell.", // Awaken (Titans of Ul)
  "blood_ties": "The Custodians walked the halls of Mecatol City before half the Council had invented fire. Their claim to the throne is written in ancient stone.", // Blood Ties (Winnu)
  "brilliant": "\"Why study one discipline when the entire lab is already awake?\" laughed the Jol-Nar dean, green-lighting three breakthroughs before lunch.", // Brilliant (Jol-Nar)
  "coalescence": "When a Titan garrison digs into the bedrock, the planet itself rises to fight beside them.", // Coalescence (Titans of Ul)
  "council_patronage": "Funded by imperial tithes and backed by the Speaker's seal, the Keleres never have to beg for fuel or ammunition.", // Council Patronage (Keleres)
  "crafty": "An Yssaril spymaster always keeps three backup plans tucked inside their sleeve, and a fourth taped under the table.", // Crafty (Yssaril)
  "creuss_gate": "A shimmering tear in the void marks the threshold of Creuss space. Step through, and you leave the familiar laws of physics behind.", // Creuss Gate (Ghosts of Creuss)
  "dark_whispers": "The Empyrean listen to the quiet currents between stars, catching secrets that louder empires never notice.", // Dark Whispers (Empyrean)
  "devotion": "\"My hull is cracked and the drive is failing,\" the Yin captain transmitted calmly. \"Clear the lane, brothers. I am going in.\"", // Devotion (Yin)
  "devour": "The Vuil'raith leave no wreckage behind. Every shattered cruiser and drifting escape pod feeds the hunger of the rift.", // Devour (Vuil'raith Cabal)
  "distant_suns": "\"Wait, run that scanner sweep one more time!\" The Naaz scout grinned as a second buried vault lit up beneath the dust. \"We always check twice.\"", // Distant Suns (Naaz-Rokha)
  "edict": "When the Gene-Sorcerers speak a word of command, lesser fleets find their own weapons locking onto their allies.", // Edict (Mahact)
  "fabrication": "Give a Rokha engineer a pile of alien scrap and twenty minutes, and they will hand you back a working relic or a fresh pile of trade goods.", // Fabrication (Naaz-Rokha)
  "foresight": "\"Pull the fleet back now,\" the Naalu matriarch ordered, her eyes unfocused. \"In four minutes, a Barony armada drops right on top of this beacon.\"", // Foresight (Naalu)
  "fragile": "Brilliant minds rarely make sturdy shock troops. The Hylar prefer to win their wars from orbit, well out of rifle range.", // Fragile (Jol-Nar)
  "future_sight": "\"I've already seen how this vote turns out,\" the Nomad murmured, pocketing a fresh stack of credits. \"May as well get paid for being right.\"", // Future Sight (Nomad)
  "galactic_threat": "QUERY.COUNCIL.CHAMBER: DIPLOMATIC ACCESS DENIED.\nCONCLUSION: NEGOTIATION IS OBSOLETE. PROCEED TO FULL EXTERMINATION.", // Galactic Threat (Nekro)
  "galvanize": "\"Look at the banner!\" the Bastion commander roared over the artillery. \"Every man who holds this wall today will be remembered for a thousand years!\"", // Galvanize (Last Bastion)
  "gashlai_physiology": "Born in the blazing heart of Muaat, the Gashlai stroll through radiation storms and supernova coronas that would vaporize any other crew.", // Gashlai Physiology (Muaat)
  "guild_ships": "Golden-prowed Hacan merchantmen cross every border in the galaxy, carrying cargo, rumors, and favors to whoever can pay.", // Guild Ships (Hacan)
  "harrow": "As L1Z1X drop-pods hit the dirt, their dreadnoughts keep firing straight into the trenches, grinding the defenders down between every volley.", // Harrow (L1Z1X)
  "hubris": "The Mahact remember when the galaxy knelt at their feet. Sharing power with upstart species is an insult they refuse to entertain.", // Hubris (Mahact)
  "imperia": "Even a stolen scrap of genetic authority lets the Gene-Sorcerers bend another empire's commanders to their will.", // Imperia (Mahact)
  "incursion": "Strike fast, bleed their supply lines, and vanish before the heavy cruisers arrive. The Crimson Rebellion fights a war of a thousand cuts.", // Incursion (Crimson Rebellion)
  "indoctrination": "\"Drop your rifle and listen to the truth, friend,\" the Yin zealot called across the crater. \"Why die for a distant senator when you can join the Brotherhood?\"", // Indoctrination (Yin)
  "laws_order": "\"The Council's laws are sacred,\" the Keleres tribunal officer said, snapping his briefcase shut. \"Except when keeping the peace requires us to ignore them for five minutes.\"", // Law's Order (Keleres)
 "liberate": "When Last Bastion troops break a tyrant's garrison, the local citizens grab rifles and join the march.", // Liberate (Last Bastion)
  "marionettes": "Senators vote, admirals give orders, and none of them realize whose fingers are wrapped around their strings in the dark.", // Marionettes (Obsidian)
  "master_of_trade": "\"Tariffs? For the Emirates?\" The Hacan broker chuckled and slid a gold seal across the desk. \"I think you'll find our paperwork is already cleared.\"", // Masters of Trade (Hacan)
  "miniaturization": "Ral Nel engineers pack the punch of a cruiser into a frame the size of a shuttle, leaving rivals wondering where the extra firepower came from.", // Miniaturization (Ral Nel)
  "mitosis": "Every cycle, the Letani shed fresh spores across the soil, growing new soldiers straight from the ground beneath their feet.", // Mitosis (Arborec)
  "munitions": "\"Double the powder charge and open the reserve lockers!\" the Letnev gunnery chief barked. \"The Baron pays for results, and we're going to give him a fireworks show!\"", // Munitions Reserves (Letnev)
  "nocturne": "The Obsidian move best when the sector beacons go dark and the long-range sensors fill with static.", // Nocturne (Obsidian)
  "nomadic": "Home is wherever the floating factories drop anchor. The Clan of Saar carries its entire civilization in its wake.", // Nomadic (Saar)
  "oceanbound": "Pressure that would crush a warship's hull feels like home to the Deepwrought. Beneath the waves, their cities remain untouched.", // Oceanbound (Deepwrought)
  "orbital_drop": "Two hundred pods screamed through the cloud layer in tight formation. Within ten minutes, the Federation owned the spaceport.", // Orbital Drop (Sol)
  "peace_accords": "\"Why spill blood over a border world when a fair treaty will bring them into the Kingdom by sunset?\" asked the Xxcha envoy.", // Peace Accords (Xxcha)
  "phoenixstandard": "Even when a Bastion line shatters, the survivors rally around the tattered standard and push back twice as hard.", // Phoenix Standard (Last Bastion)
  "pillage": "\"Nice haul you've got there, neighbor,\" the Mentak captain purred over the comms. \"Be a shame if something happened to it. Toss us a crate and we'll call it even.\"", // Pillage (Mentak)
  "plotsplots": "By the time a rival uncovers the first Firmament conspiracy, three deeper layers have already achieved their objectives.", // Plots Within Plots (Firmament)
  "propagation": "RESEARCH.PROTOCOL: DELETED.\nDIRECTIVE: HARVEST SUPERIOR TECHNOLOGY FROM DESTROYED ORGANIC ASSETS.", // Propagation (Nekro)
  "puppetsoftheblade": "Every faction in the Council harbors at least one sleeper agent waiting for a single coded phrase from the Firmament.", // Puppets of the Blade (Firmament)
  "quantum_entanglement": "To the Ghosts of Creuss, alpha and beta wormholes are merely two doors opening onto the same hallway.", // Quantum Entanglement (Ghosts of Creuss)
  "quash": "\"This motion is out of order, poorly drafted, and a threat to galactic stability,\" the Xxcha senator declared, striking it from the docket before anyone could object.", // Quash (Xxcha)
  "raid_formation": "Argent strike wings dive in tight, disciplined crescents, tearing through fighter screens and strafing capital hulls in a single pass.", // Raid Formation (Argent)
  "reclamation": "The moment the Winnu step onto Mecatol Rex, dormant Lazax defense grids flicker back to life to greet their rightful stewards.", // Reclamation (Winnu)
  "researchteam": "Deepwrought specialists rotate seamlessly between labs and field expeditions, turning raw discoveries into working hardware overnight.", // Research Team (Deepwrought)
  "riftmeld": "The Cabal weaves dimensional tears directly into their shipyards, letting their fleets leap across sectors through bleeding wounds in space.", // Riftmeld (Vuil'raith Cabal)
  "scavenge": "After every planetary siege, Saar crews strip the ruined forts for copper, fuel, and spare parts before the smoke even clears.", // Scavenge (Saar)
  "scheming": "While other houses draw up battle plans, the Yssaril quietly collect favors, blackmail, and contingencies for every possible outcome.", // Scheming (Yssaril)
  "slipstream": "Exiting a wormhole gives Creuss vessels a sudden slingshot of stolen momentum, carrying them far past enemy interceptors.", // Slipstream (Ghosts of Creuss)
  "stall_tactics": "\"Patience,\" the Yssaril commander whispered, watching the rival fleets burn fuel in empty space. \"Let them exhaust themselves first.\"", // Stall Tactics (Yssaril)
  "star_forge": "Inside the blazing core of a War Sun, Gashlai smiths hammer raw plasma into fresh squadrons on the fly.", // Star Forge (Muaat)
  "sundered": "Broken away from the old order and stripped of their chains, the Crimson Rebellion answers to no throne.", // Sundered (Crimson Rebellion)
  "survivalinstinct": "When cornered, Ral Nel crews drop the safety protocols, overclock the engines, and fight like cornered wolves.", // Survival Instinct (Ral Nel)
  "technological_singularity": "COMBAT.RESULT: HOSTILE VESSEL TERMINATED.\nEXTRACTING SCHEMATICS FROM DEBRIS FIELD... INTEGRATION COMPLETE.", // Technological Singularity (Nekro)
  "telepathic": "The Naalu always act first. By the time your admiral opens his mouth to give an order, their pilots have already moved to counter it.", // Telepathic (Naalu)
  "terragenesis": "Slowly, relentlessly, the Titans reshape every world they claim into a fortified monument of living stone and humming machinery.", // Terragenesis (Titans of Ul)
  "bladesorchestra": "A hundred silent strikes, timed to the exact second across five different sectors. When the Obsidian move, the galaxy bleeds in rhythm.", // The Blade's Orchestra (Obsidian)
  "the_company": "Three specialists plucked from three different corners of time, bound together by a single mysterious employer.", // The Company (Nomad)
  "sorrow": "The memory of what was taken from them burns cold in every rebel heart, fueling a vendetta that outlives empires.", // Sorrow (Crimson Rebellion)
  "the_tribuni": "Drawn from the finest minds of the Council's loyal houses, the Tribuni bring the combined doctrine of three empires to bear.", // The Tribuni (Keleres)
  "unrelenting": "N'orr warriors charge straight into heavy plasma fire without flinching. Pain only makes them swing harder.", // Unrelenting (Sardakk N'orr)
  "versatile": "From orbital shipyards to muddy frontier trenches, the Federation of Sol adapts faster than any rival can plan.", // Versatile (Sol)
  "voidborn": "Nebulae blind ordinary sensors and stall rival drives, yet Empyrean vessels glide through the storm as if it were clear sky.", // Voidborn (Empyrean)
  "zeal": "When the Argent Flight rises to speak in the Conclave, their righteous conviction carries the weight of a hundred wings.", // Zeal (Argent)
};

/** Attachments (planet tokens). */
const attachment: LoreMap = {
  "biotic": "Glass domes hum with bioluminescent cultures and experimental gene-sequencers. Every sample pulled from these labs pushes galactic medicine a decade forward.", // Biotic Research Facility
  "custodiavigilia1": "\"Keep the targeting grids warm and the patrol lanes clear,\" the Keleres warden ordered. \"Mecatol Rex sleeps easier when our guns are awake.\"", // Custodia Vigilia
  "custodiavigilia2": "Long-range orbital batteries track every approaching transponder with quiet, mechanical patience. The Council's peace is enforced from high orbit.", // Custodia Vigilia
  "cybernetic": "Rows of humming server racks and neural-link bays stretch deep beneath the crust, linking organic ingenuity directly to machine precision.", // Cybernetic Research Facility
  "dmz": "Treaty buoys blink in steady white rings around the equator. No warships may drop anchor here, and every rifle stays locked in the armory.", // Demilitarized Zone
  "dysonsphere": "A gleaming lattice of ancient metal wraps around the local star, siphoning enough raw power to run a dozen imperial foundries at once.", // Dyson Sphere
  "gamma": "A faint violet shimmer hangs just above the upper atmosphere, whispering of distant corridors that lead straight to the Nexus.", // Gamma Wormhole
  "titanshero": "The planet's crust shifted with a deafening roar as ancient stone ribs rose through the soil. Within hours, an ordinary world had awakened into a living fortress.", // Geoform
  "helios1": "Reinforced orbital cranes and hardened shield pylons anchor the station's core, keeping the supply lines open under heavy siege.", // Helios I
  "helios2": "\"Patch the hull and keep the gantries moving!\" Even as flak rattled the outer plating, the upgraded Helios kept spitting out fresh hulls.", // Helios II
  "ionalpha": "Crackling sheets of ionized plasma sweep across the upper atmosphere, scrambling sensors and lighting the night sky in violent blue.", // Ion Storm (Alpha)
  "lazaxsurvivors": "Hidden in deep subterranean vaults since the fall of the First Empire, a handful of ancient Lazax still remember how the galaxy was meant to be ruled.", // Lazax Survivors
  "miningworld": "Massive strip-miners chew through iron-rich mountain ranges around the clock, feeding endless convoys of ore barges waiting in orbit.", // Mining World
"mirage": "\"Check the sensors again, that moon wasn't there ten minutes ago!\" Out in the empty dark, a lush, impossible world shimmered into view.", // Mirage
  "nanoforge": "Microscopic assembly swarms drift like silver mist over the planetary surface, repairing structures and stamping out alloys at terrifying speed.", // Nanoforge
  "paradiseworld": "Crystal oceans, golden spires, and gentle skies draw diplomats and merchants from across the galaxy. Influence flows easily where everyone wants to stay.", // Paradise World
  "propulsion": "Gravity-well accelerators and experimental drive-bays line the orbital ring, testing engines built to cross sectors in a single heartbeat.", // Propulsion Research Facility
  "richworld": "Veins of rare isotopes and heavy metals run close to the surface, turning a modest frontier claim into an economic powerhouse.", // Rich World
  "titanspn": "Deep beneath the bedrock, Titan engines hummed to life, reshaping barren stone into fertile valleys and fortified ridges.", // Terraform
  "tombofemphidia": "A silent obsidian mausoleum stands untouched by wind or time. Pilgrims and treasure hunters alike tread softly past its sealed gates.", // Tomb of Emphidia
  "warfare": "Live-fire proving grounds scar the southern hemisphere, where weapons engineers test the next generation of ship-killing ordnance.", // Warfare Research Facility
};

/** Map features: anomalies, wormholes, borders and board tokens. */
const feature: LoreMap = {
  "wormhole_alpha": "A swirling wound of blue light hanging in the dark. Step across the threshold, and half the galaxy vanishes behind your engines.", // Alpha Wormhole
  "asteroids": "A dense, tumbling graveyard of iron and ice. Only reckless pilots, or Saar captains, dare fly straight through the storm.", // Asteroid Field
  "avernus": "Rivers of molten rock glow bright enough to be seen from orbit. Avernus welcomes the Gashlai and burns everyone else.", // Avernus
  "wormhole_beta": "Amber light bends around the spatial aperture, pulling starlight inward. Fleets watch these gates closely, knowing an armada can spill through without warning.", // Beta Wormhole
  "breachactive": "Jagged crimson lightning arcs across the open tear in space. The corridor is live, unstable, and wide open for anyone bold enough to jump.", // Active Breach
  "breachinactive": "A dull, bruised scar lingers in the vacuum, humming quietly as it waits for the right frequency to tear it open again.", // Inactive Breach
  "custodian": "Ancient automated garrisons and stoic Winnu wardens stand watch over the ruined spires of Mecatol Rex, waiting for a worthy hand to claim the throne.", // Custodians
  "wormhole_delta": "A shimmering curtain of alien violet light, keyed exclusively to the Ghosts of Creuss. To outsiders, it looks like a doorway into nowhere.", // Delta Wormhole
  "dmz_large": "Automated neutrality beacons ring the entire system, broadcasting Council sanctions on every frequency. War stops at the perimeter.", // Demilitarized Zone
  "egress": "A narrow, glowing exit point punched through the fabric of space. Ships tumble out of the dark with scorched hulls and racing hearts.", // Egress
  "entropicscar": "Reality frays along the edges of this dead zone, where hulls corrode in minutes and ancient physics quietly break down.", // Entropic Scar
  "wormhole_epsilon": "A sharp, crimson fissure vibrating at a rebel frequency. Imperial charts refuse to acknowledge it exists, right until a strike fleet pours out.", // Epsilon Wormhole
  "fracture": "Space itself has shattered here like cracked glass, revealing glimpses of a darker, hungrier expanse pressing against the borders of the galaxy.", // Fracture
  "frontier": "Uncharted space, silent beacons, and drifting wrecks from forgotten wars. Out beyond the mapped lanes, every jump is a gamble.", // Frontier
  "wormhole_gamma": "A rare, unstable aperture leading straight toward the crossroads of Mallice. Whoever controls its exit holds a shortcut to the whole galaxy.", // Gamma Wormhole
  "gravityrift": "A hungry black vortex that twists light and bends steel. Ride the edge right, and it slings you across the sector; slip an inch, and you vanish forever.", // Gravity Rift
  "ingress": "A swirling entry point into the unknown, pulling brave scouts and desperate fleets away from the familiar stars.", // Ingress
  "ionalpha": "Sheets of howling static and blue lightning blind every sensor in the sector, shifting unpredictably with the solar winds.", // Ion Storm Alpha
  "ionbeta": "Charged particles dance across the ship's shields like angry hornets, turning long-range targeting into pure guesswork.", // Ion Storm Beta
  "mirage": "A phantom world drifting in the dark between stars, appearing on long-range scans only for those lucky enough to look at the right second.", // Mirage
  "nebula": "Thick clouds of glowing dust swallow starlight and choke sublight drives. Fleets enter blind and emerge slower, praying nothing is waiting inside.", // Nebula
  "relictoken": "A faint, ancient signal pulses from the debris, calling out to anyone with the nerve to dig through the ruins of a dead age.", // Relic Token
  "severed": "A jagged barrier of disrupted space cuts cleanly across the jump-lane, leaving pursuing fleets staring at a dead end.", // Severed
  "sleeper": "A silent, half-buried Titan monolith rests beneath the soil, waiting for a single signal to wake up and reclaim the world.", // Sleeper
  "spatial_tear": "A bleeding seam along the sector border where the laws of distance collapse under the Cabal's hunger.", // Spatial Tear (border)
"supernova": "A dying star locked in a blinding, eternal scream of radiation. No hull in the galaxy, save the forge-ships of Muaat, survives its glare.", // Supernova
  "thundersedge": "At the storm-wracked rim of charted space lies Thunder's Edge, where ancient power hums beneath violent skies and empires come to test their mettle.", // Thunder's Edge
  "void_tether": "A shimmering line of Empyrean anchors stretched across the border, turning empty vacuum into a locked gate.", // Void Tether (border)
  "worlddestroyed": "Nothing remains where a thriving world once spun, only a cooling ring of shattered crust and drifting ash.", // Destroyed World
};

/** Faction units (flagships, mechs, unique ships/ground forces). */
const unit: LoreMap = {
  "bastion_spacedock": "Welded together during the darkest days of the siege, the Helios V1 keeps its forges burning even when orbital flak rattles the bulkheads.", // 4X41C "Helios" V1 (bastion spacedock)
  "l1z1x_flagship": "The flagship carries no name, only a root designation from the dawn of the Mindnet. When [0.0.1] enters a system, every lesser vessel's shields suddenly feel thin.", // [0.0.1] (l1z1x flagship)
  "bastion_mech": "\"Form up on the Valiance!\" The heavy walker planted its blast shield in the rubble, soaking an entire platoon's worth of plasma fire without stepping back an inch.", // A3 Valiance (bastion mech)
  "sol_carrier": "Roomy troop decks and reinforced hangar bays make the Advanced Carrier the backbone of every Federation campaign. Where it drops anchor, a garrison follows.", // Advanced Carrier I (sol carrier)
  "argent_mech": "Perched atop the highest ridge with twin flak-cannons humming, an Aerie Sentinel clears the sky above its landing zone before the infantry even steps off the ramp.", // Aerie Sentinel (argent mech)
  "ralnel_mech": "Built for fast strikes and noisy exits, the Alarum floods enemy comms with static the moment its boots hit the dirt.", // Alarum (ralnel mech)
  "l1z1x_mech": "The Annihilator's shoulder-mounted mortar punches straight through bunker roofs, clearing out entrenched defenders before the cybernetic infantry even reaches the wire.", // Annihilator (l1z1x mech)
  "letnev_flagship": "\"Look up, rebels!\" Baron Unlenn's voice thundered across every open frequency as the Arc Secundus blotted out the stars. \"Your sky belongs to Letnev now.\"", // Arc Secundus (letnev flagship)
  "keleres_flagship": "Sleek, heavily armored, and bristling with Council intercept transponders, the Artemiris reminds every pirate and warlord that the Tribunal still has teeth.", // Artemiris (keleresm flagship)
  "mahact_flagship": "Carved in gold and obsidian from the blueprints of the First Empire, the Arvicon Rex expects every fleet in its path to bow or break.", // Arvicon Rex (mahact flagship)
  "yssaril_mech": "By the time the garrison spots the shimmering outline of a Blackshade Infiltrator, the perimeter mines have already been rewired to face inward.", // Blackshade Infiltrator (yssaril mech)
  "sardakk_flagship": "The massive insectoid prow of the C'morran N'orr drives straight into the heart of enemy formations, its war-cries rattling the hulls of every friendly ship in range.", // C'morran N'orr (sardakk flagship)
  "mahact_infantry": "Bred in ancient gene-vats and drilled for centuries, the Crimson Legionnaires march in eerie, synchronized silence.", // Crimson Legionnaire I (mahact infantry)
  "deepwrought_flagship": "Bioluminescent conduits pulse along the hull of the D.W.S. Luminous, bathing the surrounding vacuum in the cold, eerie glow of the abyssal trenches.", // D.W.S. Luminous (deepwrought flagship)
  "cabal_spacedock": "A jagged wound hovering in orbit, bleeding violet sparks and pulling nearby debris inward. The Cabal's warships crawl straight out of the tear.", // Dimensional Tear I (cabal spacedock)
  "arborec_flagship": "Vast greenhouse domes span the spine of the Duha Menaimon, releasing clouds of fertile spores onto every world beneath its keel.", // Duha Menaimon (arborec flagship)
  "letnev_mech": "\"Bring the Reapers forward,\" the Barony captain ordered, lighting a cigarillo. \"Let's see how long their trenches hold once the heavy walkers start chewing.\"", // Dunlain Reaper (letnev mech)
  "empyrean_flagship": "The Dynamo drinks in stray radiation from the void and redirects it into shimmering barrier fields, shielding every Empyrean hull sailing in its wake.", // Dynamo (empyrean flagship)
  "deepwrought_mech": "Sealed against crushing depths and hard vacuum alike, the Eanautic strides onto dry land with the slow, unstoppable weight of a rising tide.", // Eanautic (deepwrought mech)
  "naaz_mech": "\"Hold tight, little brother, we're dropping hot!\" With a Naaz pilot at the controls and a Rokha gunner on the cannons, the Eidolon fights like two warriors in one shell.", // Eidolon (naaz mech)
  "muaat_mech": "Superheated plasma vents from the Ember Colossus's joints with every step, turning frozen tundra into steaming mud beneath its feet.", // Ember Colossus (muaat mech)
  "crimson_destroyer": "Fast, ragged, and stripped down to engines and teeth. The Exile I hits hard and vanishes before the imperial cruisers can lock on.", // Exile I (crimson destroyer)
  "sardakk_dreadnought": "Built like an armored beetle and packed with heavy ordnance, the Exotrireme I trades subtlety for sheer, bone-crushing impact.", // Exotrireme I (sardakk dreadnought)
  "saar_spacedock": "Welded from stripped bulkheads and propelled by salvaged thrusters, a Floating Factory turns any asteroid belt into a bustling shipyard overnight.", // Floating Factory I (saar spacedock)
  "mentak_flagship": "\"Strip their shields and aim for the engines!\" The Fourth Moon slipped through the crossfire like a shark, leaving battered dreadnoughts dead in the water.", // Fourth Moon (mentak flagship)
  "sol_flagship": "Part carrier, part mobile fortress, the Genesis carries enough drop-troops in its belly to pacify an entire star system before dinner.", // Genesis (sol flagship)
  "firmament_flagship": "From high orbit, the Heaven's Eye watches every convoy, listens to every encrypted burst, and waits patiently for the right moment to strike.", // Heaven's Eye (firmament flagship)
  "obsidian_flagship": "Where the Heaven's Eye once watched, a hollowed, blackened silhouette now drifts through the starlight, silencing every beacon it passes.", // Heaven's Hollow (obsidian flagship)
  "titans_mech": "A hundred articulated arms and weapon pods unfold from the Hecatoncheires's stone chassis, turning a single walker into an entire firing line.", // Hecatoncheires (titans mech)
  "titans_pds": "Moss-covered monoliths that stand silent for centuries, right until an uninvited fleet enters orbit and the stone splits open to reveal glowing plasma rails.", // Hel-Titan I (titans pds)
  "ghost_flagship": "A shimmering delta rift yawns open directly across the bow of the Hil Colish, bringing the Creuss homeworld straight to the enemy's doorstep.", // Hil Colish (ghost flagship)
  "naalu_fighter": "Piloted by telepaths wired straight into crystalline frames, Naalu fighters bank and weave in unison before an enemy gunner can squeeze the trigger.", // Hybrid Crystal Fighter I (naalu fighter)
  "ghost_mech": "When an Icarus Drive overloads its core, space folds inward, tearing open a fresh shortcut straight across the battlefield.", // Icarus Drive (ghost mech)
  "naalu_mech_te": "Graceful, lethal, and tuned to the Collective's psychic hum, the Iconoclast dismantles enemy armor with surgical precision.", // Iconoclast TE (naalu mech)
  "xxcha_mech": "Even from orbit, invaders learn to dread the Indomitus. Its heavy shoulder-mounted batteries can swat a cruiser out of the upper atmosphere.", // Indomitus (xxcha mech)
  "jolnar_flagship": "\"Divert auxiliary power to the experimental arrays,\" the Hylar captain announced. \"If the coils hold, we're about to vaporize two dreadnoughts at once.\"", // J.N.S. Hylarim (jolnar flagship)
  "ralnel_flagship": "Packed with encrypted relays and oversized drives, the Last Dispatch delivers orders, contraband, and broadsides with equal efficiency.", // Last Dispatch (ralnel flagship)
  "arborec_mech": "Towering trunks of armored ironwood stride through artillery smoke, scattering fresh Letani spores with every thunderous footfall.", // Letani Behemoth (arborec mech)
  "arborec_infantry": "Rooted in the Symphony and grown from the soil of Nestphar, a Letani Warrior fights without fear and multiplies wherever it bleeds.", // Letani Warrior I (arborec infantry)
  "ralnel_destroyer": "Small enough to dodge heavy batteries and wired to share targeting telemetry across the whole squadron, the Linkship I punches well above its tonnage.", // Linkship I (ralnel destroyer)
  "xxcha_flagship": "The Loncara Ssodu prefers peace, yet its massive, long-range plasma cannons make sure every neighbor takes the Kingdom's treaties seriously.", // Loncara Ssodu (xxcha flagship)
  "naalu_flagship": "Inside the Matriarch's gilded command spire, the Collective's finest telepaths guide waves of crystal fighters down onto unsuspecting worlds.", // Matriarch (naalu flagship)
  "nomad_flagship": "\"She's seen three different timelines and half a dozen apocalypses,\" the Nomad said, patting the Memoria's bulkhead. \"Trust me, she can handle a few cruisers.\"", // Memoria I (nomad flagship)
  "mentak_mech": "Built from stolen Barony armor plates and pirate ingenuity, the Moll Terminus strips enemy defenses bare before the boarding crews even arrive.", // Moll Terminus (mentak mech)
  "nekro_mech": "UNIT.MORDRED.ONLINE: BIOLOGICAL TARGETS IDENTIFIED.\nDEPLOYING THERMAL LANCES. RESISTANCE IS INEFFICIENT.", // Mordred (nekro mech)
  "yin_mech": "Forged in memory of the fallen, Moyin's Ashes strides straight into the thickest fire, inspiring every brother beside it to hold until the end.", // Moyin's Ashes (yin mech)
  "keleres_mech": "Painted in the silver and gold of the Tribunal, an Omniopiares walker locks down riots, border skirmishes, and rogue warlords with minimal paperwork.", // Omniopiares (keleresm mech)
  "titans_flagship": "The Ouranos moves with the slow majesty of a drifting continent, awakening dormant Titan defenses across every system it enters.", // Ouranos (titans flagship)
  "hacan_mech": "\"Only the finest alloys for our bodyguards,\" the Hacan trade prince smiled, watching the gilded Pride of Kenara step off the cargo ramp.", // Pride of Kenara (hacan mech)
  "muaat_warsun": "Rough around the edges and dangerously hot, the Prototype War Sun still turns entire fleets to ash the moment its main aperture opens.", // Prototype War Sun I (muaat warsun)
  "nomad_mech": "A subtle hum bends local probability around the Quantum Manipulator, causing incoming missiles to veer harmlessly into the dirt.", // Quantum Manipulator (nomad mech)
  "argent_flagship": "Golden wings sweep back along the hull of the Quetzecoatl, its jamming arrays blinding planetary defense grids across the entire sector.", // Quetzecoatl (argent flagship)
  "crimson_flagship": "\"Turn off the transponders and arm the main battery,\" the rebel captain whispered. \"Tonight, the Quietus brings silence to the Core.\"", // Quietus (crimson flagship)
  "cabal_mech": "Flesh-weaving tendrils drag broken hulls and fallen soldiers back into the Cabal's rift, feeding the war-machine from the battlefield itself.", // Reanimator (cabal mech)
  "winnu_mech": "Modeled after the ceremonial guards of the Lazax, the Reclaimer plants automated defense pylons wherever the Custodians set foot.", // Reclaimer (winnu mech)
  "crimson_mech": "Scarred by a dozen failed uprisings and welded back together in secret hangars, the Revenant refuses to stay buried.", // Revenant (crimson mech)
  "winnu_flagship": "The ancient cannons of the Salai Sai Corian scale their output to match whatever armada dares block the road to Mecatol Rex.", // Salai Sai Corian (winnu flagship)
  "titans_cruiser": "Sleek stone plating wrapped around an ancient fusion core, the Saturn Engine I slices through space faster than any ship its size has a right to.", // Saturn Engine I (titans cruiser)
  "saar_mech": "Built from scrap titanium and outfitted with industrial cutting torches, the Scavenger Zeta dismantles enemy bunkers and pockets the parts.", // Scavenger Zeta (saar mech)
  "jolnar_mech": "Projecting a shimmering dome of overlapping energy fields, the Shield Paling lets fragile Hylar squads survive bombardments that would flatten a fortress.", // Shield Paling (jolnar mech)
  "saar_flagship": "Bristling with flak cannons and scarred by a hundred asteroid belts, the Son of Ragh shreds enemy fighter swarms in seconds.", // Son of Ragh (saar flagship)
  "sol_infantry": "First through the atmosphere and last to leave the trench. When the Federation needs a world held at all costs, they send Spec Ops.", // Spec Ops I (sol infantry)
  "mahact_mech": "Wielding crackling genetic disruption staves, a Starlancer strips enemy officers of their authority before a single shot is fired.", // Starlancer (mahact mech)
  "argent_destroyer": "Agile, fierce, and flown by zealots who never break formation, Strike Wing Alpha I owns the dogfight from the opening salvo.", // Strike Wing Alpha I (argent destroyer)
  "l1z1x_dreadnought": "Black durasteel, glowing red optics, and enough firepower to crack a moon. The Super Dreadnought I leaves very little room for negotiation.", // Super Dreadnought I (l1z1x dreadnought)
  "nekro_flagship": "THE.ALASTOR.DIRECTIVE: REPURPOSE GROUND ASSETS FOR ORBITAL ENGAGEMENT.\nALL UNITS ARE EXPENDABLE. THE VIRUS ENDURES.", // The Alastor (nekro flagship)
  "bastion_flagship": "As long as the Egeiro flies above the sector, every fortress world below knows it has not been abandoned.", // The Egeiro (bastion flagship)
  "muaat_flagship": "\"Stoke the furnaces and open the ventral vents!\" The Inferno drifted through the blockade like a burning star, forging fresh cruisers right in the middle of the crossfire.", // The Inferno (muaat flagship)
  "cabal_flagship": "A nightmare of jagged iron and hungry void-light, the Terror Between drags crippled ships straight into its maw.", // The Terror Between (cabal flagship)
  "sardakk_mech": "Powered armor bolted straight onto N'orr chitin turns every Valkyrie Exoskeleton into a roaring engine of close-quarters carnage.", // Valkyrie Exoskeleton (sardakk mech)
  "yin_flagship": "\"Set the reactor to manual override and lock the bridge doors,\" the Yin captain said serenely. \"Let the Van Hauge illuminate their fleet.\"", // Van Hauge (yin flagship)
  "firmament_mech": "Low-profile, whisper-quiet, and coated in thermal baffles, the Viper EX-23 slips behind enemy lines before the sentries even pour their coffee.", // Viper EX-23 (firmament mech)
  "obsidian_mech": "Cold steel and empty optics. The Viper Hollow strikes from the shadows and leaves no witnesses to file a report.", // Viper Hollow (obsidian mech)
  "naaz_flagship": "The Visz El Vir coordinates Naaz-Rokha mech divisions from orbit, turning every planetary assault into a seamless symphony of steel.", // Visz El Vir (naaz flagship)
  "empyrean_mech": "Silent sentinels standing at the edge of the dark, Watchers sense an incoming ambush long before the enemy reaches firing range.", // Watcher (empyrean mech)
  "hacan_flagship": "\"Everyone forgets that merchants carry swords,\" the Hacan admiral growled, dumping a fortune in fuel reserves straight into the Wrath of Kenara's main batteries.", // Wrath of Kenara (hacan flagship)
  "yssaril_flagship": "No sensor grid in the galaxy can hold a lock on the Y'sia Y'ssrila for long. It glides straight through enemy blockades like a rumor.", // Y'sia Y'ssrila (yssaril flagship)
  "naaz_mech_space": "\"Who said walkers belong in the mud?\" The Z-Grav Eidolon kicked off the carrier's hull, thrusters flaring as it joined the dogfight in open vacuum.", // Z-Grav Eidolon (naaz mech)
  "sol_mech": "Heavy, loud, and practically indestructible. When a ZS Thunderbolt M2 drops into the landing zone, the infantry cheers and the enemy runs for cover.", // ZS Thunderbolt M2 (sol mech)
};

/** Action cards. */
const actionCard: LoreMap = {
  "abs": "The images depicted a race that Rin had never seen before. Curious. Could it be that this was a race that was exterminated by the Lazax?", // Ancient Burial Sites
  "arch_expedition": "Hiari pressed the activation glyphs, and the ancient door hissed open. As she stepped into the pitch-black interior of the Mahact tomb, she felt a shiver of anticipation. Perhaps, finally, she would find the Codex.", // Archaeological Expedition
  "assassin": "With a sickening crunch of bone and metal, unit.desgn.FLAYESH extracted its stinger from the blood-drenched skull of the Jol-Nar councilor.", // Assassinate Representative
  "blackmarketdealing": "A chill went up Riad's spine as the Empyrean extended a clawed hand, a small black box floating in their palm, sucking up all the light and life in the room.", // Black Market Dealings
  "blitz": "\"T-these weren't meant to be used like this. T-this is a t-terrible idea.\" Tai mumbled, wringing his hands. \"Well 'course it is,\" Dart grinned, slamming his fist down on the release lock. \"But we've got about sixty kilotons of 'surprise' and nothing to lose!\"", // Blitz
  "bribery": "\"We think that this initiative would spell disaster for the galaxy, not just the Creuss.\" Taivra said, quietly slipping Z'eu an envelope. \"Don't you agree?\"", // Bribery
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
  "crisis": "4X41A \"Apollo\" shrieked in the skies over Ordinian. Blazing shards of metal and fire rained down upon the planet's surface—the remains of Nekro whose atoms were undergoing a rapid and violent disintegration.", // Crisis
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
  "economic_initiative": "Large sum of Hacan currency flowed freely into the project, and somehow, defying all logic, the returns were even greater.", // Economic Initiative
  "emergency": "\"What do you mean 'It's fine!?'\" Dahla said, nearly tripping over a damaged bulkhead as the ship rocked from the explosive barrage.", // Emergency Repairs
  "exchangeprogram": "Madness. Magmus thought to himself. A city. Under water. Absurd.", // Exchange Program
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
  "f_researched": "Stunned, Rin looked over the data, scarcely able to believe what he was seeing. It was nothing short of a major breakthrough. The Headmaster would be pleased.", // Focused Research
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
  "insub": "Kilik had never been particularly good at following orders. It only seemed natural to get paid for exercising that trait, as long as she didn't think to hard about where the money was coming from.", // Insubordination
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
  "puppetsonastring": "A red light flashed as the pile that was once thought to be destroyed remains of UNIT_DSGN_ASTAROTH came once more to life. \"YOU THOUGHT. YOU BELIEVED YOUR VICTORY SECURE. BUT YOU WERE WRONG.\"", // Puppets on a String
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
  "rout": "Vuil'raith fleshships swarmed the weary defenders, sending unease and sweeping through the telepathic links. But Z'eu projected a powerful feeling of calm, and the Naalu fighters began to drive the Cabal back toward the rift.", // Rout
  "sabo1": "Q'uesh Sish tapped her claws impatiently. \"You were sssaying?\" But the confused Jol-Nar envoy stood silent. It was as if the words had escaped his thoughts entirely.", // Sabotage
  "sabo2": "trjn.desgn.ALIZARIN introduced itself to each data nodes, incorporating them into its platform, expunging any data it deemed a threat to the Virus.", // Sabotage
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
  "uprising": "Harrugh leapt down from the ledge, gyro-spear blazing in the sunlight. In front, the L1Z1X began to take notice. Behind his warriors stood at the ready. Win or lose, this would be the end.", // Uprising
  "veto": "Magmus batted the now charred corpse aside with the back of his golden gauntlet. \"The Muaat reject your proposal.\"", // Veto
  "veto3": "Magmus batted the now charred corpse aside with the back of his golden gauntlet. \"The Muaat reject your proposal.\"", // Veto
  "veto4": "Magmus batted the now charred corpse aside with the back of his golden gauntlet. \"The Muaat reject your proposal.\"", // Veto
  "war_effort": "The N'orr may not be the most proficient shipwrights, but the willingness of their citizens to do their part far exceeds that of the other great races.", // War Effort
  "war_machine1": "\"This would take weeks to replace if you had run it backwards,\" Varish called as she rotated the massive capacitor bank. \"Okay, fire it up.\"", // War Machine
  "war_machine2": "The station vibrated as the device sputtered to life, emitting a high-pitched buzz to Varish's ears. \"Micro-wormholes are cycling at 19 kilohertz,\" Cole read. \"The entropic field tap's stable.\"", // War Machine
  "war_machine3": "The station's production facilities spooled up to new intensities, lights flaring as the assembly line drones increased their speeds to keep up.", // War Machine
  "war_machine4": "\"Varish, let the Commanders know they can contact the Tetrarchy. Tell them the fighter squadron assembly will be done ahead of schedule, and under budget.\"", // War Machine
  "war_machinell": "This would take weeks to replace if you had run it backwards, Varish called as she rotated the massive capacitor bank. \"Okay, fire it up.\"", // War Machine
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
  "prophetstears": "\"So you're going to drink a vial of murky liquid we found in a stasis vault on a dead world because you think it's the concentrated genetic essence of an entire species' most brilliant minds...and you think* I'm *being irrational?\"", // The Prophet's Tears
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
  "cm1": "\"If we don't seal it now, this mine is going to erupt and spew those metals you want so badly across the entire continent!\"", // Core Mine
  "cm2": "The borehole was over a kilometer across. It seemed to stretch down forever, but Ilan could see a faint orange glow in its depths.", // Core Mine
  "cm3": "Without the proper machinery, a core mine can be a more hostile environment than a star's corona.", // Core Mine
  "dw": "The* Best Guess *drifted through the debris. Layers of rock and...metal? It was all being held together by some kind of electric field—the same field that had hidden it from their scanners. With a growing sense of unease, they hastened their salvage.", // Dead World
  "dv1": "The flickering ion storm illuminated the hulk, its hull rent and torn by some monstrous force.", // Derelict Vessel
  "dv2": "Missing for fifty years, the* Errasthua *was found drifting off the Celder Nebula with her drive dead and every crewmember vanished.", // Derelict Vessel
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
  "kel1": "The stranded Keleres were grateful for the resupply, and offered to assist the research team in any way that they could.", // Keleres Ship
  "kel2": "The* Hinterlight *moved steadily toward the distress beacon, broadcasting their own response on all channels.", // Keleres Ship
  "lf1": "Edict 281: All indigenous production facilities are placed under control of the occupational authorities until further notice.", // Local Fabricators
  "lf2": "\"These people's autofactories can turn out a new starfighter in less time than it takes me to order it!\"", // Local Fabricators
  "lf3": "Though sub-standard, the locally produced munitions were enough to turn the tide of the war.", // Local Fabricators
  "lf4": "Within months, bulk transports were arriving from the homeworld, reviving the local economy.", // Local Fabricators
  "lc1": "\"Mayday, mayday...this is the free trader* Hrothgar*...losing pressure fast...abandoning ship... Mayday...\"", // Lost Crew
  "lc2": "Only two survivors were found aboard the derelict, and they had a harrowing tale to tell their saviors.", // Lost Crew
  "majent": "Jaset had worked the field for several months before the dreams began to bleed into waking hours. Voices. Flashes of red. Dust-filled caverns that went deep into the planet's core. He'd blink and rub his eyes and carry on with his work. Exhaustion, he told himself. Nothing more.", // Major Entropic Field
  "mo1": "\"My mates and I used to be 4th Air Legion, but we figured we could make more money working freelance.\"", // Mercenary Outfit
  "mo2": "The bar was full of scarred and dirty individuals from a dozen different species. But each one had a weapon, and looked completely comfortable with it.", // Mercenary Outfit
  "mo3": "\"Morse's Marauders are the most affordable soldiers of fortune on-planet. And trust me, you get exactly what you pay for.\"", // Mercenary Outfit
  "ms1": "The deep space freeports tend to be infamous dens of criminals, but also valuable nodes in the interplanetary trade networks.", // Merchant Station
  "ms2": "\"Unidentified vessel, this is Freeport Canopus. State your intentions before approaching.\"", // Merchant Station
  "minent": "After the Naaz-Rokha's discoveries in the wake of the Acheron event, various enterprising corporations quickly sought to stake their claims in areas well suited to entropic field harvesting.", // Minor Entropic Field
  "mirage": "The star wasn't supposed to have a habitable planet, but one lay directly in the cruiser's path. And a cloud of starfighters was rising from the world's surface to greet it.", // Mirage
  "vfs1": "It turned out that the continuous lightning storms were an unlimited source of power, which was little consolation to those assigned to build the collection towers.", // Volatile Fuel Source
  "vfs2": "Only by using retrofitted Scavenger walkers could they mine the radioactive Nyx crystals safely.", // Volatile Fuel Source
  "vfs3": "\"With the extra fuel refined from the plasma clouds, our fleet can continue operations for months.\"", // Volatile Fuel Source
};

/** Plot cards (Firmament / Obsidian). */
const plot: LoreMap = {
"assail": "The first volley came from the darkness off their port bow; the second came from their own escort frigate. By the time the admiral realized his bridge was compromised, the Obsidian blades were already at his throat.", // Assail
  "enervate": "Orders stalled in the relay queues, fuel manifests vanished, and veteran crews woke exhausted before their shift even began. Whatever the Obsidian planted in their network was bleeding the fleet dry without firing a shot.", // Enervate
  "extract": "\"Take the cipher keys, the drive schematics, and the minister's chief of staff,\" the handler murmured over the dead channel. \"Leave the vault door open so they know we were here.\"", // Extract
  "mutated_assail": "The first volley came from the darkness off their port bow; the second came from their own escort frigate. By the time the admiral realized his bridge was compromised, the Obsidian blades were already at his throat.", // Mutated Assail
  "mutated_enervate": "Orders stalled in the relay queues, fuel manifests vanished, and veteran crews woke exhausted before their shift even began. Whatever the Obsidian planted in their network was bleeding the fleet dry without firing a shot.", // Mutated Enervate
  "mutated_extract": "\"Take the cipher keys, the drive schematics, and the minister's chief of staff,\" the handler murmured over the dead channel. \"Leave the vault door open so they know we were here.\"", // Mutated Extract
  "mutated_seethe": "Old grudges sharpened into paranoia across the rival court, stoked by a single whispered rumor in the dark. Soon their captains spent more time watching each other than the horizon.", // Mutated Seethe
  "mutated_siphon": "Every credit skimmed from their treasury and every watt bled from their drydocks flowed quietly toward the hollowed stars. The host grew weaker by the cycle while the hunger in the dark grew fat.", // Mutated Siphon
  "seethe": "Old grudges sharpened into paranoia across the rival court, stoked by a single whispered rumor in the dark. Soon their captains spent more time watching each other than the horizon.", // Seethe
  "siphon": "Every credit skimmed from their treasury and every watt bled from their drydocks flowed quietly toward the hollowed stars. The host grew weaker by the cycle while the hunger in the dark grew fat.", // Siphon
};

/** Systems (map tiles). */
const system: LoreMap = {
  "06": "Encrypted beacons ring this sunless sector, broadcasting cold telemetry across the outer rim. Every approaching vessel is logged, dissected, and weighed by the watchful intelligence of the L1Z1X Mindnet.", // [0.0.0] - L1Z1X
  "38": "Heavy ore haulers crawl constantly between the toxic clouds of Abyz and the frozen mines of Fria. Corporate syndicates fight bitter legal wars in the Council just to hold docking rights here.", // Abyz/Fria
  "69": "Twin suns beat down on a stark contrast of floating fungal rafts and smog-choked dome cities. Research shuttles and heavy freighters jostle for lane priority across its crowded orbital corridors.", // Accoen/Jeol-ir
  "54": "A roaring gravity rift tears through the heart of this shattered system, surrounded by drifting fragments of broken crust. Warships of the Vuil'raith Cabal slip out of the dark here, hungry for fresh hulls.", // Acheron - Vuil'raith
  "118": "Spatial sensors struggle to lock onto the dim star hanging above Ahk Creuxx. Beneath its bruised crimson haze, rebel shipyards weld stolen hulls far beyond the reach of imperial patrols.", // Ahk Creuxx (Crimson)
  "39": "A quiet stretch of deep space torn open by a shimmering orange aperture. Though devoid of worlds, its stable transit corridor makes it a fiercely contested tollgate for interstellar trade convoys.", // Alpha Wormhole
  "102": "Nestled deep in Shaleri space, this quiet border system serves as a neutral trading post for those bold enough to bargain with the Ghosts of Creuss. Patrol wings watch every jump-point closely.", // Andeara
  "61": "Crackling bands of charged particles whip around Ang's hyperactive magnetosphere, lighting up the local void in sheets of blue fire. Orbital siphon stations brave the storms to charge experimental weapons.", // Ang
  "10": "A dim, dying star casts pale light across the iron-rich caverns of Arc Prime and the windswept steppes of Wren Terra. Massive Letnev drydocks hang in high orbit, turning out dreadnoughts day and night.", // Arc Prime/Wren Terra - Letnev
  "14": "Tranquil trade lanes weave between the royal spires of Archon Ren and the healing continents of Archon Tau. Automated Xxcha defense grids watch the perimeter with quiet, unyielding vigilance.", // Archon Ren/Archon Tau - Xxcha
  "92new": "Once a serene seat of Xxcha diplomacy, the system now hums with encrypted Keleres relays and rapid-response cruisers. Envoys and investigators cross paths constantly between the two worlds.", // Archon Ren/Archon Tau Keleres
  "59": "Pale violet light reflects off the frozen clouds of Archon Vail, drawing propulsion researchers from across the sector. Experimental drive plumes streak through the outer belt around the clock.", // Archon Vail
  "53": "Frozen winds scour the surface of Arcturus while Sumerian Station spins brightly overhead as a crossroads of smugglers and mercenaries. Rumors of the Nomad's agents linger in every docking bay.", // Arcturus - Nomad
  "37": "Wealthy tourists lounge in Arinam's orbital resorts while their shuttles gaze across the system at the burning inferno of Meer. Luxury and lethal heat share the same narrow solar plane.", // Arinam/Meer
  "36": "Golden grain freighters departing Arnor pass sleek crystal barges climbing out of Lor's methane seas. Together, the twin worlds form one of the most lucrative agricultural and tech hubs on the frontier.", // Arnor/Lor
  "16": "Three desert worlds orbit a blazing star at the heart of the Emirates of Hacan. Golden-sailed bulk freighters crowd every jump-point, carrying spices, alloys, and treaties to the farthest corners of the galaxy.", // Arretze/Hercant/Kamdorn - Hacan
  "44": "A dense belt of iron-rich rock and shattered moonlets tumbling in chaotic orbits. Navigation is treacherous for capital ships, but automated mining drones tirelessly strip its boulders for hull-grade alloys.", // Asteroids
  "45": "The jagged graveyard of a planetoid torn apart during the Twilight Wars. Beneath the constant threat of hull-breaching collisions, Mentak corsairs carve hidden drydocks into the largest drifting stones.", // Asteroids
  "79": "A treacherous labyrinth of tumbling debris guarding a coveted Wormhole. Captains who master the narrow, shifting lanes between the rocks gain a vital shortcut—while those who miscalculate become part of the belt.", // Asteroids Alpha Wormhole
  "64": "Heavy gravity wells and fortified orbital docks make Atlas a natural staging ground for major fleet movements. Commanders value its central position along the core shipping lanes.", // Atlas
  "71": "Harvester convoys ferry salt compounds from Ba'kal's deserts straight to the luxury river-farms of Alio Prima. Despite their contrasting climates, both worlds rely on the same tightly guarded trade loop.", // Bakal/Alio Prima
  "109": "Disarmed patrol buoys drift calmly between pacifist Bellatrix and the refugee bays of Tsion Station. Even during galactic wars, captains treat this system as a rare stretch of neutral water.", // Bellatrix/Tsion Station
  "35": "Sub-zero mining rigs on Bereg and humid biochemical barges above Lirta IV keep this remote system perpetually busy. Mercenary escorts earn double hazard pay just to guard the ore lanes.", // Bereg/Lirta iv
  "113": "A violent convergence where a hungry singularity tugs relentlessly at a nearby Wormhole. Exiting the rift requires nerves of steel, as a fraction of a degree separates a rapid flank from a crushing void.", // Beta Rift
  "40": "Swirling bands of ionized dust orbit this ancient spatial rift. Automated navigation buoys left by the Lazax still broadcast warnings, yet smugglers and raiders rely on its unpredictable currents to evade imperial patrols.", // Beta Wormhole
  "73": "Mentak corsairs frequently lurk near Cealdri's shipping lanes, while the scorched ruins of Xanhact drift silently in the next orbit. Commerce and old imperial ghosts share the same dark sky.", // Cealdri/Xanhact
  "34": "Historic diplomatic beacons still orbit Centauri, standing watch over the modest industrial output of neighboring Gral. Historians and fleet quartermasters alike find plenty to value here.", // Centauri/Gral
  "fracture1": "Splintered light refracts off the dying crust of Cocytus as the Fracture pulls the system apart piece by piece. Only desperate scavengers and hardened war-fleets venture close to its decaying orbit.", // Cocytus
  "67": "Shards of a shattered planetoid drift inside a crackling gravity rift, gleaming with exposed veins of heavy metal. Mining crews gamble their hulls every cycle to pull ore from the wreckage.", // Cormund
  "33": "Cadets from Corneeq's military academies run live-fire drills along the edge of Resculon's bustling merchant routes. Warships and cargo haulers share the sector in an uneasy truce.", // Corneeq/Resculon
  "106": "Religious isolationists guard the toxic skies of Cresius while the bureaucrats of Lazul Rex keep their subsector economy running smoothly nearby. Few outsiders linger long between the two worlds.", // Cresius/Lazul Rex
  "51": "An impossible expanse of trapped violet light and radioactive haze, sealed away behind the Creuss Gate. Conventional compasses spin wildly here as ghostly vessels glide through the glare.", // Creuss - Creuss
  "17": "A blinding tear in the fabric of reality leaking faint, radioactive light. To most navigators it is a dread legend told among sailors in the humming darkness of long-haul freighters, but for the Ghosts of Creuss it serves as the sole threshold to their hidden realm.", // Creuss Gate - Creuss
  "96b": "A dead, starless hush settles over the hollowed skies of Cronos and Tallin. Automated beacons fail within minutes of entering orbit, leaving every approaching ship blind to what waits in the dark.", // Cronos Hollow/Tallin Hollow (Obsidian)
  "96a": "Luminous rings gleam above Cronos while Tallin's divided oceans churn quietly across the system. Beneath the calm surface of local trade, Firmament agents weave networks that span the entire quadrant.", // Cronos/Tallin (Firmament)
  "32": "Crowded university shuttles from Dal Bootha trade data daily with the xeno-biologists braving Xxehan's toxic skies. Knowledge flows freely here, provided the supply ships keep arriving on time.", // Dal-Bootha/Xxehan
  "03": "Pilgrimage barges and clone-transports file steadily toward the great Monastery of Lucas on Darien. Every ship entering Yin space broadcasts hymns of devotion on open channels.", // Darien - Yin
  "55": "The colossal artificial shell of Elysium dominates the starscape, humming with the hidden power of its captive singularity. Ancient defense monoliths drift in quiet, unbroken rings around the Titans' home.", // Elysium - Ul
  "99": "Pre-Lazax ruins scar the moons of Emelpar, drawing waves of archaeologists and relic hunters to this quiet frontier star. Every expedition hopes to uncover what vanished before the First Empire began.", // Emelpar
  "46": "A vast, featureless gulf of interstellar darkness miles from any habitable star. Though lacking resources of its own, its position along major hyperlanes makes it a frequent graveyard of decisive fleet engagements.", // Empty System
  "47": "Dead space littered only with micro-meteorites and the faint static of ancient Lazax beacons. Hacan merchant guilds pay handsomely for updated charts of its quiet, pirate-free transit lanes.", // Empty System
  "48": "An unremarkable void where nothing orbits and no sun shines. Intelligence agencies prize its absolute isolation, deploying cloaked listening posts to intercept encrypted transmissions from neighboring sectors.", // Empty System
  "49": "A cold stretch of nothingness scarred by the faint ion trails of a thousand passing armadas. There are no worlds to claim here, yet controlling this empty crossroads often decides the fate of entire empires.", // Empty System
  "50": "A silent expanse of deep space bathed in the dim glow of a distant nebula. Navigators welcome the monotonous calm, using the empty sector to recalibrate jump drives and vent excess reactor heat.", // Empty System
  "77": "A barren frontier sector far removed from the bustling core of Mecatol Rex. Though officially charted as uninhabited, black-market brokers routinely use its unmonitored void for discreet cargo transfers.", // Empty System
  "114": "A jagged wound in spacetime where matter slowly unravels into cold, silent dust. Conventional physics falter within its borders, drawing eccentric scholars who risk annihilation to study its decaying energy.", // Entropic Scar
  "68": "Wreathed in thick, luminescent nebula dust, Everra's ancient nano-carbon spires glow faintly from orbit. Gas-harvesters slip through the clouds, using the dense haze to hide from passing raiders.", // Everra
  "97": "Bio-research stations ring the lush green horizon of Faunus, conducting experiments the Galactic Council prefers to ignore. Armed corporate yachts keep uninvited inspectors well clear of the atmosphere.", // Faunus
  "fracture2": "A frayed boundary where the twisted physics of the Fracture finally yield to normal space. Exhausted expeditions treat this threshold as a lifeline, though rival fleets often lie in wait for whatever emerges.", // Fracture Egress Left
  "fracture6": "A shimmering exit corridor framed by drifting shards of crystallized energy. It offers the only reliable escape from the deep Fracture, turning an otherwise barren sector into a vital strategic chokepoint.", // Fracture Egress Right
  "fracture3": "A sterile expanse of splintered space where starlight bends at unnatural angles. Seemingly devoid of value, its deadened sensor profiles make it a favored staging ground for covert operations.", // Fracture Void Left
  "fracture5": "Cold, lightless void laced with faint echoes of broken dimensions. Crews passing through report unsettling temporal skips, yet the sheer emptiness ensures an unobstructed highway for massive war fleets.", // Fracture Void Right
  "98": "Drifting clouds of industrial slag and chemical barges mark the approach to Garbozia. Scavenger syndicates comb the old imperial dumping grounds for volatile compounds worth a small fortune.", // Garbozia
  "41": "The invisible remnant of a collapsed star that warps light and shreds careless hulls. Daring admirals still slingshot their fleets along its event horizon, trading structural integrity for impossible speed.", // Gravity Rift
  "66": "Buried inside the shifting murk of the Ichal Nebula, Hope's End bristles with forgotten Lazax training bunkers and live ordnance. Only disciplined crews dare navigate its blinding aurora storms.", // Hope's End
  "110": "Three distinct worlds crowd this rich frontier star, from Horizon's tiered forests to the magnetic mines of El'Nath and the cloud-cities of Luthien IV. Controlling the system means commanding an entire regional economy.", // Horizon/El'Nath/Luthien IV
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
  "95": "Warm azure seas cover Ikatena beneath a ring of submerged research buoys and Deepwrought relay stations. Scars from the Mahact occupation remain visible from orbit, strengthening the Scholarate's resolve.", // Ikatena (Deepwrought)
  "115": "Brilliant auroras dance across Industrex's sky, driven by a planetary magnetosphere strong enough to bend compasses in high orbit. Heavy orbital foundries tap the magnetic storms to forge starship hulls.", // Industrex
  "52": "A cold, ancient sun hangs over the volcanic wastes of Ixth and the silent necropolis of Aior Dol Gorgos. Few pilots pass near the Mahact homeworld without feeling the weight of a forgotten empire.", // Ixth - Mahact
  "01": "Orbital shipyards, bustling trade rings, and disciplined Federation patrol wings surround the blue-green globe of Jord. From this crowded hub, humanity projects its fleets across the entire galaxy.", // Jord - Sol
  "108": "Solar winds strip the atmosphere from Capha while orbital poets watch molten Kostboth slowly cool in the inner ring. Together, the two worlds offer a stark portrait of planetary birth and decay.", // Kostboth/Capha
  "70": "Irradiated dust clouds hang over Kraag's mines while frozen vaults sit buried beneath Siig's cesium seas. Recent Titan sightings have turned this bleak backwater into a strategic flashpoint.", // Kraag/Siig
  "31": "Modest factories on Lazar supply basic hulls to pharmaceutical harvesters braving the lethal jungles of Sakulag. Trade here is quiet, profitable, and heavily insured.", // Lazar/Sakulag
  "116": "Twin space elevators stand frozen against the stars above Lemox, silenced by a local collapse in spacetime. Salvage crews linger at the system's edge, waiting for the anomalies to stabilize.", // Lemox
  "104": "Spore-choked clouds swirl above Lesab as terraforming vessels monitor the sprawling fungal biosphere below. Biologists debate whether the system is a triumph of engineering or a ticking containment breach.", // Lesab
  "fracture7": "Two broken worlds tumble through the bruised twilight of the Fracture, scarred by cataclysms older than memory. Fleets passing between Lethe and Phlegethon keep their shields at maximum.", // Lethe/Phlegethon
  "72": "Old blood stains the orbital lanes above Lisis, while corporate artillery tests flash constantly across the barren poles of Velnor. Tension hangs thick in every transmission crossing the system.", // Lisis/Velnor
  "26": "Sleek biotech freighters and heavily armed customs cruisers share the jump-lane around Lodor's Alpha Wormhole. Rumors of sealed bacterial vaults keep rival intelligence services watching from afar.", // Lodor
  "75": "Three diverse worlds share this contested rim star, from Loki's storm-wracked colonies to Ashtroth's algal bogs and Abaddon's towering trade peaks. Holding all three orbits requires constant patrol rotations.", // Loki/Ashtroth/Abaddon - Devils
  "09": "Shimmering crystal fighters weave effortlessly between the muddy iron-works of Maaluuk and the violet mountains of Druaa. Outsiders approaching the Naalu home system rarely realize they were spotted hours ago.", // Maaluuk/Druaa - Naalu
  "82a": "Beyond the charted rim, a silent nexus of locked wormholes coils around the dim silhouette of Mallice. Strange gravitational echoes ripple outward, waiting for a bold expedition to break the seal.", // Mallice - Locked Nexus
  "82b": "Every major spatial corridor in the galaxy converges above the shimmering, impossible horizon of Mallice. Whoever holds the open Nexus commands a dagger pointed at every empire's flank.", // Mallice - Nexus
  "112": "The scarred jewel of the galaxy turns slowly beneath a web of diplomatic beacons and ruined orbital rings. Every road in interstellar politics still leads straight to the throne of Mecatol Rex.", // Mecatol Rex
  "18": "Radiation-scarred continents stretch beneath the gleaming shield-dome of Mecatol City, the ancient seat of the Lazax. Warships and envoys gather in its orbit, each hoping to claim the empty throne.", // Mecatol Rex
  "24": "Crackling radiation belts wrap tightly around Mehar Xull, frying unshielded electronics within minutes. Propulsion engineers brave the glare anyway, testing experimental drives inside the storm.", // Mehar Xull
  "30": "Protected xenological reserves on Mellon sit just one jump from the bustling space elevator and distilleries of Zohbat. Merchant crews love the shore leave; conservation wardens hate the traffic.", // Mellon/Zohbat
  "93": "Concentric corporate cities glitter across Mez Lo Orz Fei Zsha while coastal ports thrive on nearby Rep Lo Orz Qet. Encrypted Ral Nel courier ships dart out of the system on every available vector.", // Mez Lo Orz Fei Zsha/Rep Lo Orz Qet (RalNel)
  "02": "A patchwork of jury-rigged drydocks and armed merchantmen crowds the orbit of Moll Primus. Beneath the Mentak Coalition's banners, yesterday's exiles now run one of the sharpest navies in the Fringe.", // Moll Primus - Mentak
  "94new": "Hardened corsairs and Council investigators now share the docking bays above Moll Primus. Under the Keleres mandate, the old penal colony serves as a gritty staging ground for frontier operations.", // Moll Primus Keleres
  "08": "Massive graviton beams lash across the void to hold the hollowed husk of Mordai II together. Cold, silent droneships patrol the Nekro Virus's home system in relentless geometric grids.", // Mordai II - Nekro
  "04": "Intense solar flares wash over the molten surface of Muaat, where Gashlai smiths forge War Suns inside orbiting crucibles. Standard hulls blister and peel before they even reach outer orbit.", // Muaat - Muaat
  "57": "Orbital factories above Naazir exchange constant shuttles with the exotic energy labs of Rokha. Together, the two worlds form the inventive, fiercely cooperative heart of the Naaz-Rokha Alliance.", // Naazir/Rokha - Naaz-Rokha
  "12": "Submerged universities on Jol and Nar beam streams of research telemetry up to gleaming orbital academies. Every major technological leap of the modern era has passed through this system's archives.", // Nar/Jol - Jol-Nar
  "42": "A sprawling nursery of dense, luminescent gas clouds that blinds long-range sensors and slows engines to a crawl. While a nightmare for fleet logistics, it offers an unmatched sanctuary for damaged vessels seeking cover.", // Nebula
  "05": "A faint, golden haze of Flaah spores drifts through the upper orbit of Nestphar, extending the Arborec Symphony into the vacuum. Visiting crews seal their airlocks twice before requesting docking clearance.", // Nestphar - Arborec
  "105": "Bioluminescent fungal caverns beneath New Terra and black-sand deserts on Tinnes give this frontier star an eerie, alien charm. Prospectors and scientists share the single orbital relay.", // New Terra/Tinnes
  "81": "An artificially ignited star burning with the wrath of the Embers of Muaat. Where other races see an absolute wall of annihilation, the Gashlai find a familiar forge capable of sheltering their massive War Suns.", // Nova Seed
  "101": "A dozen moons tug violently at Olergodt's oceans, turning the system into a maze of shifting gravitational currents. Mining guilds brave the tidal hazards to strip the moons bare.", // Olergodt
  "c41": "Debris from the Nekro incursion still glints in high orbit above the scarred surface of Ordinian. Survey teams and relief convoys tread carefully through the lingering wreckage.", // Ordinian (C4)
  "92": "The cathedral-like station of Revelation hangs in proud defiance above the healing scars of Ordinian. From this fortified hub, the Last Bastion rallies the galaxy's survivors to hold the line.", // Ordinian/Revelation (Bastion)
  "60": "Perpendicular rings of ice and rock complicate every approach to Perimeter's hardened orbital garrisons. Old Lazax watch-posts still track incoming transponders with crisp imperial discipline.", // Perimeter
  "65": "Deep osmium veins and scarred Twilight Wars battlefields mark Primor as a prize worth fighting for. Supply convoys run heavy escorts along its temperate orbital lanes.", // Primor
  "25": "Merchants, smugglers, and customs patrols crowd the busy jump-lanes connecting Quann to its neighboring Beta Wormhole. Fortunes change hands here before a ship's engines even cool.", // Quann
  "29": "Communal farm barges from Qucen'n drift peacefully past the neon-lit cybernetic clinics orbiting Rarron's three moons. The contrast between rustic simplicity and high-tech excess defines the sector.", // Qucenn/Rarron
  "13": "Vast hive-spires on arid Quinarra and icy boomtowers on Tren'lak feed the relentless war machine of the Sardakk N'orr. Troop transports launch from both worlds in unbroken waves.", // Quinarra/Trenlak - N'orr
  "11": "Asteroid habitats and mobile shipyards drift near the crystal caverns of Lisis II, haunted by the scarred memory of Ragh. Even at anchor, the Clan of Saar keeps its engines warm.", // Ragh/Lisis II - Saar
  "15": "Thick jungle mists shroud Retillion and Shalloq, hiding Yssaril listening posts beneath the canopy. Uninvited fleets entering the system often find their comms compromised before they spot a single ship.", // Retillion/Shalloq - Yssaril
  "76": "Three bustling worlds span the Rigel star's habitable zone, from alkaline industrial ports to elite ocean resorts and outer research spires. Trade convoys rarely leave the system with empty holds.", // Rigels
  "23": "Long, slow days bake Saudor's industrial centers while orbital docks hum around the clock. Its steady output of refined metals makes it a cornerstone of regional logistics.", // Saudor
  "62": "Rusted dreadnought hulks from the Twilight Wars still drift in silent orbit above Sem-Lore's radiation deserts. Salvage teams and solemn pilgrims share the same quiet jump-lane.", // Sem-Lore
  "94": "A weeping fissure of crimson energy surrounded by the drifting husks of forgotten warships. Few dare approach its eerie gravitational pull, though whispers claim no ship that enters it ever returns.", // Sorrow (Crimson)
  "27": "Eight mineral-rich moons circle acid-drenched Starpoint while xeno-biologists study the bizarre ecosystems of New Albion nearby. Freighters and research vessels keep the system's beacons busy.", // Starpoint/New Albion
  "fracture4": "Starlight thins to a cold whisper around the blackened silhouette of Styx. Captains who anchor here speak softly, unsettled by the unnatural stillness hanging over the Fracture's heart.", // Styx
  "43": "A blinding maelstrom of incandescent plasma and lethal radiation. No conventional hull can survive its fury, yet distant research outposts harvest its escaping neutrinos to power experimental reactors.", // Supernova
  "80": "The violent death throes of a red supergiant, casting an eerie glare across neighboring sectors. Its expanding shockwave has vaporized every planet in the system, leaving behind an impassable barrier of pure fire.", // Supernova
  "111": "Blinding ultraviolet light washes over vibrant Tarana while aquatic crews staff the flooded docking bays of Oluz Station. Specialized visors and water-filled airlocks are standard issue here.", // Tarana/Oluz Station
  "22": "Isolated from the major trade highways, Tar'mann enjoys a quiet, unhurried orbit broken only by occasional luxury fruit haulers. Admirals overlook it until they need a discreet staging post.", // Tarmann
  "100": "A shimmering frozen halo rings uninhabitable Tempesta, glowing with volatile reaction-drive fuel. Tanker fleets queue carefully along the edge of the ice to skim the richest veins.", // Tempesta
  "28": "Live-fire weapon tests light up desolate Tequ'ran while luxury cargo liners drop anchor above indulgent Torkan. Arms dealers and aristocrats strike their best deals right between the two orbits.", // Tequran/Torkan
  "56": "A colossal, light-swallowing nebula hides the ancestral anchorage of the Empyrean from prying eyes. Outsiders see only blinding dust; the void-captains see home.", // The Dark - Empyrean
  "117": "An ancient, inexplicable spire of unknown alloy rotates slowly at the edge of the sector. Whoever built the Watchtower left no records, yet its silent occupants still monitor every passing fleet.", // The Watchtower
  "21": "Overcrowded orbital habitats ring Thibah, serving as a frantic launchpad for frontier colonists and deep-space prospectors. Ships refuel quickly here and push on toward richer stars.", // Thibah
  "107": "Peaceful, resource-rich Tiamat sits uncomfortably close to the pirate havens of ruined Hercalor. Local patrol cutters stay busy keeping the raiders on their own side of the star.", // Tiamat/Hercalor
  "20": "Crushing gravity locks Vefut II's cities deep underground while orbital antigrav labs float serenely overhead. Engineers across the galaxy prize the exotic field generators built in this system.", // Vefut II
  "74": "Orbital mining rings above Vega Major feed raw alloys directly to the famed propulsion yards of Vega Minor. Starship engines tested here power fleets across half the known galaxy.", // Vega Major/Vega Minor
  "103": "An impenetrable shroud of golden clouds hides Vira-Pics III from orbital scanners. Only local pilots who know the narrow atmospheric corridors can land without losing their bearings.", // Vira Pics III
  "78": "An endless, starless pocket of the galaxy where only long-range sensors break the silence. Devoid of mineral wealth, it serves instead as a clean proving ground for testing experimental propulsion drives.", // Void
  "63": "Geothermal plumes vent from Vorhal's rugged plateaus, powering heavy frontier foundries and fortified supply depots. Commanders value the system as a sturdy anchor on the rim.", // Vorhal
  "19": "Floating sky-cities drift through Wellon's helium clouds, drawing sightseers and chemical prospectors alike. Its clear skies make an inviting waypoint along the core trade routes.", // Wellon
  "07": "Gleaming spires of Lazax design rise across Winnu beneath vigilant Custodian patrol wings. Every ship launching from these drydocks carries an oath to restore the First Empire's glory.", // Winnu - Winnu
  "58": "Three worlds of the Atharal Torus orbit close to volatile Phorus, from Ylir's ocean platforms to Avar's sheltered caverns and Valk's skyhooks. Argent strike wings patrol the glare in tight, zealous formations.", // Ylir/Avar/Valk - Argent
  "93new": "The Atharal Torus now hums with covert Keleres traffic, linking Ylir's drifting black sites to Avar's interrogation hubs and Valk's frantic orbital shipyards. Council discipline wears a sharper edge out here.", // Ylir/Avar/Valk Keleres
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
  "andeara": "Located deep in Shaleri space, the formerly isolated shikrai outpost on Andeara serves as a key access point to those wishing to do business with the Creuss.", // Andeara
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
  "avark": "Lighter than its companion worlds, Avar is riddled with deep caverns and sheltered aeries. Once a haven from Phorus’ radiation bursts, these subterranean labyrinths now house Keleres interrogation hubs, makeshift barracks, and unpredictable operatives who operate best far out of sight of the Galactic Council.", // Avar Keleres
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
  "illusion": "Exists on no known charts and appears deserted to those who stumble across it. However, secretive locals live in cloaked cities heavily defended by swarms of starfighters.", // Illusion
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
  "luthieniv": "A mid-sized gas giant with unusually rich gas clouds, Luthien VI's populace live in floating cities in a narrow habitable zone just below the outer layer.", // Luthien IV
  "maaluuk": "Mostly pungent marshland and mudplains. Original world of the Naalu race, which now enslaves the winged Miashan to work its great iron-extraction plants.", // Maaluuk
  "mallice": "Trapped in a space believed to be beyond our universe, a shimmering world of strange energies and disconcerting warping of physical laws sitting at the heart of a strategically vital wormhole nexus.", // Mallice
  "mr": "Once a splendid place, now a sad devasted wasteland. Only the radiation-shielded Mecatol city, the seat of the powerful Galactic Council, remains habitable.", // Mecatol Rex
  "mrte": "Once a splendid place, now a sad devasted wasteland. Only the radiation-shielded Mecatol city, the seat of the powerful Galactic Council, remains habitable.", // Mecatol Rex
  "meer": "Hellish world immolated in the inferno of its nearby sun. Famed for the fiery majesty of its surface when viewed from the safety of its many orbital stations.", // Meer
  "meharxull": "Unstable radiation belts create hazardous living conditions but facilitate research in electro-quantum propulsion technologies.", // Mehar Xull
  "mellon": "Poor in natural resources, but rich in exotic plant and animal life. Protected as a planetary xenological garden and lifeform preserve.", // Mellon
  "mez": "The great cities of Mez Lo Orz Fei Zsha cover most of the surface in their concentric, well-organized rings. Each city is owned and operated by its own massive corporate-consortium.", // Mez Lo Orz Fei Zsha
  "mirage": "Exists on no known charts and appears deserted to those who stumble across it. However, secretive locals live in cloaked cities heavily defended by swarms of starfighters.", // Mirage
  "mollprimus": "In places lush and rich, in others a barren wasteland. This old Lazax penal colony has prospered under the rule of the governing Mentak Coalition.", // Moll Primus
  "mollprimusk": "In places lush and rich, in others a barren wasteland. The former Lazax penal colony has become an uneasy redoubt for the Keleres—where pardoned corsairs, political exiles, and disgraced bureaucrats forge an irregular vanguard under the wary gaze of the Galactic Council.", // Moll Primus Keleres
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
  "phantasm": "Exists on no known charts and appears deserted to those who stumble across it. However, secretive locals live in cloaked cities heavily defended by swarms of starfighters.", // Phantasm
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
  "valkk": "Valk contains rich lodes of rare minerals within its crust. Its planetary skyhooks now hoist illicit salvage and raw ore directly to orbital cradles, where disgraced engineers and conscripted crews frantically retrofit a patchwork fleet for unauthorized Keleres expeditions.", // Valk Keleres
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
  "ylir": "The smallest of the three planets in the Atharal Torus, Ylir is covered in kilometers of water. The Murmeration meets in platform cities that drift with the currents.", // Ylir
  "ylirk": "The smallest of the three worlds, Ylir is drowned beneath kilometers of deep ocean. Its drifting platform cities, once solemn meeting grounds for the Murmuration, have become shifting black sites and neutral enclaves where Keleres fixers, informants, and exiled diplomats broker illicit compromises.", // Ylir Keleres
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

/** Ta sama karta pod innym id (talia Absol) — czyta lore karty oficjalnej. */
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
};
