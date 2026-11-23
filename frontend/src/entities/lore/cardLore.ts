// Pola na lore (flavour) kart — WPISUJE UŻYTKOWNIK. Pusty string = brak (nic się nie wyświetla).
// Jeden wpis = jedna linia, tekst w cudzysłowie: "id": "Twój tekst.", // Nazwa karty
// Skrypt scripts/gen_lore_template.py dopisuje brakujące karty i nie rusza wpisanych tekstów.
// Akcje, relikty i eksploracja mają flavour w assetach AsyncTI4 (pole flavorText) — tu ich nie ma.

export type LoreMap = Record<string, string>;

/** Leaders (agent / commander / hero). */
const leader: LoreMap = {
  "redcreusshero": "", // "A Tall Stranger" (crimson hero)
  "redcreusscommander": "", // "Total Mystery" (crimson commander)
  "redcreussagent": "", // "Who Knows?" (crimson agent)
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
  "orlandohero": "", // F.S.S. Orlando (bastion hero)
  "nomadagentmercer": "\"The Argent Flight? The ones who left my people in poverty while they pursued some secret crusade? No, this Shikrai has no time for their pious zealotry. I'm going to take what the universe owes me by doing what I do best.\"", // Field Marshal Mercer (nomad agent)
  "sardakkcommander": "Renowned for her vicious raids and surprise assaults into enemy territory, Sek'kus and her Valkyrie commandos are the elite vanguard of the swarm's vast armies.", // G'hom Sek'kus (sardakk commander)
  "naazagent": "\"I thought you disabled the laser traps!\" Garv yelped as the corridor filled with searing light. Gunn waved one hand from inside the open panel. \"No, that was the blade barrier. Just...throw something at the kill switch and see if that works!\"", // Garv and Gunn (naaz agent)
  "xxchaagent": "In most societies, a title like the King's Shield may be awarded to a valiant bodyguard or warrior. The Xxcha gave it to their most accomplished diplomat, for Rinn has saved more lives through his tireless work than an army of soldiers ever will.", // Ggrocuto Rinn (xxcha agent)
  "hacancommander": "\"Elder Qanoj. I have heard the Xxcha's work to restore Archon Tau has run short of resources. Perhaps the Emirates may be of some assistance?\"", // Gila the Silvertongue (hacan commander)
  "saarhero": "\"When we arrived at the colony, we found it and one whole hemisphere of the planet had been scoured down to ash and bedrock, as if hit by some giant solar flare.\"", // Gurno Aggero (saar hero)
  "keleresheroharka": "Authority. Strength. Efficacy.", // Harka Leeds (keleres hero)
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
  "keleresherokuuasi": "Valor. Grace. Wisdom.", // Kuuasi Aun Jalatai (keleres hero)
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
  "keleresheroodlynn": "Peace. Community. Deterrence.", // Odlynn Myrr (keleres hero)
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
  "xxchahero": "", // Xxekir Grom (xxcha hero)
  "xxchahero-te": "Grom's harnessing of the council's inter-agency connections to expedite the Xxcha's defense proposal surprised no one. It turned out nearly everyone owed Xxekir Grom a favor.", // Xxekir Grom (xxcha hero)
  "naaluagent": "", // Z'eu (naalu agent)
  "naaluagent-te": "\"...and that's why the Letnev will never cooperate with the Shikrai zealots and extremists!\" Ambassador Beumosile thundered. The Galactic Council exploded in angry shouts as he sat down. \"Very good, my pet,\" the velvet voice hissed in his mind, and he basked in the warmth of its praise.", // Z'eu (naalu agent)
};

/** Agendas. */
const agenda: LoreMap = {
  "revolution": "", // Anti-Intellectual Revolution
  "secret": "", // Archived Secret
  "standardization": "", // Armed Forces Standardization
  "arms_reduction": "", // Arms Reduction
  "articles_war": "", // Articles of War
  "checks": "", // Checks and Balances
  "cladenstine": "", // Clandestine Operations
  "classified": "", // Classified Document Leaks
  "redistribution": "", // Colonial Redistribution
  "committee": "", // Committee Formation
  "disarmament": "", // Compensated Disarmament
  "conventions": "", // Conventions of War
  "core_mining": "", // Core Mining
  "covert": "", // Covert Legislation
  "demilitarized_zone": "", // Demilitarized Zone
  "economic_equality": "", // Economic Equality
  "travel_ban": "", // Enforced Travel Ban
  "sanctions": "", // Executive Sanctions
  "regulations": "", // Fleet Regulations
  "crisis": "", // Galactic Crisis Pact
  "holy_planet_of_ixth": "", // Holy Planet of Ixth
  "defense_act": "", // Homeland Defense Act
  "arbiter": "", // Imperial Arbiter
  "incentive": "", // Incentive Program
  "artifact": "", // Ixthian Artifact
  "abolishment": "", // Judicial Abolishment
  "minister_antiquities": "", // Minister of Antiquities
  "minister_commerce": "", // Minister of Commerce
  "minister_exploration": "", // Minister of Exploration
  "minister_industry": "", // Minister of Industry
  "minister_peace": "", // Minister of Peace
  "minister_policy": "", // Minister of Policy
  "minister_sciences": "", // Minister of Sciences
  "minister_war": "", // Minister of War
  "miscount": "", // Miscount Disclosed
  "mutiny": "", // Mutiny
  "constitution": "", // New Constitution
  "nexus": "", // Nexus Sovereignty
  "censure": "", // Political Censure
  "prophecy": "", // Prophecy of Ixth
  "execution": "", // Public Execution
  "schematics": "", // Publicize Weapon Schematics
  "rearmament": "", // Rearmament Agreement
  "conscription": "", // Regulated Conscription
  "rep_govt": "", // Representative Government
  "representative_government": "", // Representative Government (Base Game)
  "grant_reallocation": "", // Research Grant Reallocation
  "rt_biotic": "", // Research Team: Biotic
  "rt_cybernetic": "", // Research Team: Cybernetic
  "rt_propulsion": "", // Research Team: Propulsion
  "rt_warfare": "", // Research Team: Warfare
  "warrant": "", // Search Warrant
  "seed_empire": "", // Seed of an Empire
  "senate_sanctuary": "", // Senate Sanctuary
  "shard_of_the_throne": "", // Shard of the Throne
  "shared_research": "", // Shared Research
  "plowshares": "", // Swords to Plowshares
  "terraforming_initiative": "", // Terraforming Initiative
  "crown_of_emphidia": "", // The Crown of Emphidia
  "crown_of_thalnos": "", // The Crown of Thalnos
  "unconventional": "", // Unconventional Measures
  "wormhole_recon": "", // Wormhole Reconstruction
  "wormhole_research": "", // Wormhole Research
};

/** Promissory notes. */
const promissoryNote: LoreMap = {
  "acq": "", // Acquiescence
  "<color>_an": "", // Alliance
  "antivirus": "", // Antivirus
  "bmf": "", // Black Market Forgery
  "blackops": "", // Black Ops
  "blood_pact": "", // Blood Pact
  "<color>_cf": "", // Ceasefire
  "iff": "", // Creuss Iff
  "crucible": "", // Crucible
  "ce": "", // Cybernetic Enhancements
  "dark_pact": "", // Dark Pact
  "fires": "", // Fires of the Gashlai
  "gift": "", // Gift of Prescience
  "greyfire": "", // Greyfire Mutagen
  "rider": "", // Keleres Rider
  "ridera": "", // Keleres Rider
  "riderm": "", // Keleres Rider
  "riderx": "", // Keleres Rider
  "malevolency": "", // Malevolency
  "ms": "", // Military Support
  "nanolink": "", // Nano-Link Permit
  "favor": "", // Political Favor
  "<color>_ps": "", // Political Secret
  "pop": "", // Promise of Protection
  "ragh": "", // Raghs Call
  "raisethestandard": "", // Raise the Standard
  "ra": "", // Research Agreement
  "scepter": "", // Scepter of Dominion
  "sever": "", // Sever
  "shareknowledge": "", // Share Knowledge
  "spynet": "", // Spy Net
  "ambuscade": "", // Strike Wing Ambuscade
  "stymie": "", // Stymie
  "<color>_sftt": "", // Support for the Throne
  "tekklar": "", // Tekklar Legion
  "terraform": "", // Terraform
  "cavalry": "", // The Cavalry
  "<color>_ta": "", // Trade Agreement
  "convoys": "", // Trade Convoys
  "war_funding": "", // War Funding
};

/** Public objectives. */
const publicObjective: LoreMap = {
  "supremacy": "", // Achieve Supremacy
  "amass_wealth": "", // Amass Wealth
  "become_legend": "", // Become a Legend
  "build_defenses": "", // Build Defenses
  "centralize_trade": "", // Centralize Galactic Trade
  "command_armada": "", // Command an Armada
  "conquer": "", // Conquer the Weak
  "massive_cities": "", // Construct Massive Cities
  "control_borderlands": "", // Control the Borderlands
  "corner": "", // Corner the Market
  "develop": "", // Develop Weaponry
  "lost_outposts": "", // Discover Lost Outposts
  "diversify": "", // Diversify Research
  "engineer_marvel": "", // Engineer a Marvel
  "monument": "", // Erect a Monument
  "expand_borders": "", // Expand Borders
  "deep_space": "", // Explore Deep Space
  "brain_trust": "", // Form Galactic Brain Trust
  "golden_age": "", // Found a Golden Age
  "research_outposts": "", // Found Research Outposts
  "galvanize": "", // Galvanize the People
  "vast_reserves": "", // Hold Vast Reserves
  "infrastructure": "", // Improve Infrastructure
  "intimidate": "", // Intimidate Council
  "lead": "", // Lead From the Front
  "make_history": "", // Make History
  "manipulate_law": "", // Manipulate Galactic Law
  "master_science": "", // Master the Sciences
  "trade_routes": "", // Negotiate Trade Routes
  "vast_territories": "", // Patrol Vast Territories
  "outer_rim": "", // Populate the Outer Rim
  "protect_border": "", // Protect the Border
  "push_boundaries": "", // Push Boundaries
  "raise_fleet": "", // Raise a Fleet
  "ancient_monuments": "", // Reclaim Ancient Monuments
  "revolutionize": "", // Revolutionize Warfare
  "distant_lands": "", // Rule Distant Lands
  "subdue": "", // Subdue the Galaxy
  "sway_council": "", // Sway the Council
  "unify_colonies": "", // Unify the Colonies
};

/** Secret objectives. */
const secretObjective: LoreMap = {
  "ans": "", // Adapt New Strategies
  "bam": "", // Become a Martyr
  "btgk": "", // Become the Gatekeeper
  "baf": "", // Betray a Friend
  "btv": "", // Brave the Void
  "ctr": "", // Control the Region
  "csl": "", // Cut Supply Lines
  "dts": "", // Darken the Skies
  "dfat": "", // Defy Space and Time
  "dyp": "", // Demonstrate Your Power
  "dhw": "", // Destroy Heretical Works
  "dtgs": "", // Destroy Their Greatest Ship
  "dp": "", // Dictate Policy
  "dtd": "", // Drive the Debate
  "eap": "", // Establish a Perimeter
  "eh": "", // Establish Hegemony
  "fwp": "", // Fight with Precision
  "faa": "", // Forge an Alliance
  "fsn": "", // Form a Spy Network
  "fc": "", // Foster Cohesion
  "fwm": "", // Fuel the War Machine
  "gamf": "", // Gather a Mighty Fleet
  "hrm": "", // Hoard Raw Materials
  "lsc": "", // Learn the Secrets of the Cosmos
  "mew": "", // Make an Example of Their World
  "mlp": "", // Master the Laws of Physics
  "mtm": "", // Mechanize the Military
  "mrm": "", // Mine Rare Metals
  "mp": "", // Monopolize Production
  "otf": "", // Occupy the Fringe
  "ose": "", // Occupy the Seat of the Empire
  "pem": "", // Produce en Masse
  "pe": "", // Prove Endurance
  "sai": "", // Seize an Icon
  "sar": "", // Spark a Rebellion
  "syc": "", // Stake Your Claim
  "sb": "", // Strengthen Bonds
  "te": "", // Threaten Enemies
  "ttfd": "", // Turn Their Fleets to Dust
  "uf": "", // Unveil Flagship
};

/** Technologies. */
const technology: LoreMap = {
  "helios2": "", // 4X41C "Helios" V2
  "nekroc4r": "", // ???\_ERROR\_ERROR\_???
  "nekroc4y": "", // ???\_NULL\_REFERENCE\_???
  "ac2": "", // Advanced Carrier II
  "ah": "", // Aerie Hololattice
  "as": "", // Aetherstream
  "asn": "", // Agency Supply Network
  "aida": "", // AI Development Algorithm
  "amd": "", // Antimass Deflectors
  "asc": "", // Assault Cannon
  "bs": "", // Bio-Stims
  "bio": "", // Bioplasmosis
  "cv2": "", // Carrier II
  "cm": "", // Chaos Mapping
  "cl2": "", // Crimson Legionnaire II
  "cr2": "", // Cruiser II
  "dxa": "", // Dacxive Animators
  "det": "", // Dark Energy Tap
  "dd2": "", // Destroyer II
  "ds": "", // Dimensional Splicer
  "dt2": "", // Dimensional Tear II
  "dn2": "", // Dreadnought II
  "da": "", // Duranium Armor
  "ers": "", // E-Res Siphons
  "executiveorder": "", // Executive Order
  "exile2": "", // Exile II
  "exo2": "", // Exotrireme II
  "ff2": "", // Fighter II
  "fl": "", // Fleet Logistics
  "ffac2": "", // Floating Factory II
  "gr": "", // Genetic Recombination
  "gls": "", // Graviton Laser System
  "gd": "", // Gravity Drive
  "htp": "", // Hegemonic Trade Policy
  "ht2": "", // Hel-Titan II
  "hcf2": "", // Hybrid Crystal Fighter II
  "hydrothermal": "", // Hydrothermal Mining
  "hm": "", // Hyper Metabolism
  "iihq": "", // I.I.H.Q. Modernization
  "ic": "", // Impulse Core
  "inf2": "", // Infantry II
  "is": "", // Inheritance Systems
  "it": "", // Instinct Training
  "ie": "", // Integrated Economy
  "l4": "", // L4 Disruptors
  "lgf": "", // Lazax Gate Folding
  "lw2": "", // Letani Warrior II
  "lwd": "", // Light/Wave Deflector
  "linkship2": "", // Linkship II
  "md_base": "", // Magen Defense Grid
  "md_c1": "", // Magen Defense Grid Ω
  "md": "", // Magen Defense Grid ΩΩ
  "mi": "", // Mageon Implants
  "mr": "", // Magmus Reactor
  "m2": "", // Memoria II
  "mc": "", // Mirror Computing
  "nanomachines": "", // Nanomachines
  "nm": "", // Neural Motivator
  "parasite-firm": "", // Neural Parasite (Firmament)
  "parasite-obs": "", // Neural Parasite (Obsidian)
  "ng": "", // Neuroglaive
  "nes": "", // Non-Euclidean Shielding
  "nf": "", // Nullification Field
  "pds2": "", // PDS II
  "planesplitter-firm": "", // Planesplitter (Firmament)
  "planesplitter-obs": "", // Planesplitter (Obsidian)
  "ps": "", // Plasma Scoring
  "pfa": "", // Pre-Fab Arcologies
  "pi": "", // Predictive Intelligence
  "pm": "", // Production Biomes
  "pws2": "", // Prototype War Sun II
  "proxima": "", // Proxima Targeting VI
  "pa": "", // Psychoarchaeology
  "qdn": "", // Quantum Datahub Node
  "radical": "", // Radical Advancement
  "so": "", // Salvage Operations
  "st": "", // Sarween Tools
  "se2": "", // Saturn Engine II
  "sdn": "", // Scanlink Drone Network
  "sar": "", // Self-Assembly Routines
  "sr": "", // Sling Relay
  "sd2": "", // Space Dock II
  "scc": "", // Spatial Conduit Cylinder
  "so2": "", // Spec Ops II
  "swa2": "", // Strike Wing Alpha II
  "subatomic": "", // Subatomic Splicer
  "sdn2": "", // Super Dreadnought II
  "sc": "", // Supercharge
  "tcs": "", // Temporal Command Suite
  "td": "", // Transit Diodes
  "tp": "", // Transparasteel Plating
  "vax": "", // Valefar Assimilator X
  "vay": "", // Valefar Assimilator Y
  "vpw": "", // Valkyrie Particle Weave
  "vw": "", // Voidwatch
  "vtx": "", // Vortex
  "ws": "", // War Sun
  "wg": "", // Wormhole Generator
  "x89_base": "", // X-89 Bacterial Weapon
  "x89": "", // X-89 Bacterial Weapon Ω
  "x89c4": "", // X-89 Bacterial Weapon ΩΩ
  "yso": "", // Yin Spinner Omega
};

/** Breakthroughs (Thunder's Edge). */
const breakthrough: LoreMap = {
  "naazbt": "", // Absolute Synergy
  "cabalbt": "", // Al'Raith Ix Ianovar
  "xxchabt": "", // Archon's Gift
  "hacanbt": "", // Auto-Factories
  "solbt": "", // Bellum Gloriosum
  "ralnelbt": "", // Data Skimmer
  "yssarilbt": "", // Deepgloom Executable
  "saarbt": "", // Deorbit Barrage
  "l1z1xbt": "", // Fealty Uplink
  "letnevbt": "", // Gravleash Maneuvers
  "keleresbt": "", // I.I.H.Q. Modernization
  "winnubt": "", // Imperator
  "naalubt": "", // Mindsieve
  "sardakkbt": "", // N'orr Supremacy
  "ghostbt": "", // Particle Synthesis
  "arborecbt": "", // Psychospore
  "crimsonbt": "", // Resonance Generator
  "titansbt": "", // Slumberstate Computing
  "jolnarbt": "", // Specialist Compounds
  "muaatbt": "", // Stellar Genesis
  "bastionbt": "", // The Icon
  "obsidianbt": "", // The Reaping
  "firmamentbt": "", // The Sowing
  "mentakbt": "", // The Table's Grace
  "nomadbt": "", // Thunder's Paradox
  "nekrobt": "", // Valefar Assimilator Z
  "mahactbt": "", // Vaults of the Heir
  "deepwroughtbt": "", // Visionaria Select
  "empyreanbt": "", // Void Tether
  "argentbt": "", // Wing Transfer
  "yinbt": "", // Yin Ascendant
};

/** Faction abilities. */
const ability: LoreMap = {
  "aetherpassage": "", // Aetherpassage
  "amalgamation": "", // Amalgamation
  "ambush": "", // Ambush
  "analytical": "", // Analytical
  "arbiters": "", // Arbiters
  "armada": "", // Armada
  "assimilate": "", // Assimilate
  "awaken": "", // Awaken
  "blood_ties": "", // Blood Ties
  "brilliant": "", // Brilliant
  "coalescence": "", // Coalescence
  "council_patronage": "", // Council Patronage
  "crafty": "", // Crafty
  "creuss_gate": "", // Creuss Gate
  "dark_whispers": "", // Dark Whispers
  "devotion": "", // Devotion
  "devour": "", // Devour
  "distant_suns": "", // Distant Suns
  "edict": "", // Edict
  "fabrication": "", // Fabrication
  "foresight": "", // Foresight
  "fragile": "", // Fragile
  "future_sight": "", // Future Sight
  "galactic_threat": "", // Galactic Threat
  "galvanize": "", // Galvanize
  "gashlai_physiology": "", // Gashlai Physiology
  "guild_ships": "", // Guild Ships
  "harrow": "", // Harrow
  "hubris": "", // Hubris
  "imperia": "", // Imperia
  "incursion": "", // Incursion
  "indoctrination": "", // Indoctrination
  "laws_order": "", // Law's Order
  "liberate": "", // Liberate
  "marionettes": "", // Marionettes
  "master_of_trade": "", // Masters of Trade
  "miniaturization": "", // Miniaturization
  "mitosis": "", // Mitosis
  "munitions": "", // Munitions Reserves
  "nocturne": "", // Nocturne
  "nomadic": "", // Nomadic
  "oceanbound": "", // Oceanbound
  "orbital_drop": "", // Orbital Drop
  "peace_accords": "", // Peace Accords
  "phoenixstandard": "", // Phoenix Standard
  "pillage": "", // Pillage
  "plotsplots": "", // Plots Within Plots
  "propagation": "", // Propagation
  "puppetsoftheblade": "", // Puppets of the Blade
  "quantum_entanglement": "", // Quantum Entanglement
  "quash": "", // Quash
  "raid_formation": "", // Raid Formation
  "reclamation": "", // Reclamation
  "researchteam": "", // Research Team
  "riftmeld": "", // Riftmeld
  "scavenge": "", // Scavenge
  "scheming": "", // Scheming
  "slipstream": "", // Slipstream
  "sorrow": "", // Sorrow
  "stall_tactics": "", // Stall Tactics
  "star_forge": "", // Star Forge
  "sundered": "", // Sundered
  "survivalinstinct": "", // Survival Instinct
  "technological_singularity": "", // Technological Singularity
  "telepathic": "", // Telepathic
  "terragenesis": "", // Terragenesis
  "bladesorchestra": "", // The Blade's Orchestra
  "the_company": "", // The Company
  "the_tribuni": "", // The Tribuni
  "unrelenting": "", // Unrelenting
  "versatile": "", // Versatile
  "voidborn": "", // Voidborn
  "zeal": "", // Zeal
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
} as const satisfies Record<string, LoreMap>;

export type LoreKind = keyof typeof CARD_LORE;
