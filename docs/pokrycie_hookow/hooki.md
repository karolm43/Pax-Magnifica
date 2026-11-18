# Pokrycie hooków: zarejestrowane hooki

Generowany — nie edytuj. Podsumowanie: [`../POKRYCIE_HOOKOW.md`](../POKRYCIE_HOOKOW.md).

## 1. Zarejestrowane hooki

Razem: **366**. Opis = pierwsza linia docstringu funkcji hooka.

| Punkt zaczepienia | Rodzaj | Źródło | Komponent | Co robi |
|---|---|---|---|---|
| `action_cards.canceller` | PERMIT | technology:it | technologies:it | Jawne: gotowa technologia i żeton w strategy pool - okno anulowania się otwiera. |
| `action_cards.forbidden` | FORBID | agenda:censure | agendas:censure | — |
| `agenda.planets_ready_limit` | FORBID | effect:agendas:checks:against | agendas:checks | — |
| `agenda.single_vote` | PERMIT | agenda:rep_govt | agendas:rep_govt | — |
| `agenda.vote_first` | PERMIT | faction:argent | abilities:zeal | Zeal: You always vote first during the agenda phase (także jako mówca - F_argent). |
| `agenda.vote_modifier` | MODIFY | faction:argent | abilities:zeal | Zeal: When you cast at least 1 vote: cast 1 additional vote for each player in the game |
| `agenda.vote_modifier` | MODIFY | effect:leaders:hacancommander:votes | — | F_hacan: przy 0 zwykłych głosów (wstrzymanie się) dodatkowych głosów nie ma. |
| `agenda.vote_unblockable` | PERMIT | leader:xxchacommander | leaders:xxchacommander | Elder Qanoj: Game effects cannot prevent you from voting on an agenda (F_xxcha: Political |
| `agenda.votes_per_planet` | MODIFY | leader:xxchacommander | leaders:xxchacommander | Elder Qanoj: Each planet you exhaust to cast votes provides 1 additional vote (także planeta |
| `bombardment.empty_planets` | PERMIT | technology:x89c4 | technologies:x89c4 | X-89 ΩΩ: wolno bombardować planetę bez sił naziemnych (C_technology). |
| `bombardment.extra_dice` | MODIFY | leader:argentcommander | leaders:argentcommander | — |
| `bombardment.extra_dice` | MODIFY | effect:promissory_notes:ambuscade:die | — | — |
| `bombardment.extra_dice` | MODIFY | technology:ps | technologies:ps | Plasma Scoring: 1 z jednostek używających BOMBARDMENT rzuca 1 dodatkową kością. |
| `bombardment.forbidden_traits` | FORBID | agenda:conventions | agendas:conventions | — |
| `bombardment.granted_hits_on` | FORBID | effect:action_cards:blitz | — | — |
| `bombardment.ground_units` | FORBID | unit:l1z1x_mech | units:l1z1x_mech | Annihilator: While not participating in ground combat, this unit can use its BOMBARDMENT |
| `bombardment.ignores_planetary_shield` | PERMIT | leader:l1z1xcommander | leaders:l1z1xcommander | 2RAM: At any time: Units that have PLANETARY SHIELD do not prevent you from using |
| `bombardment.roll_modifier` | MODIFY | effect:action_cards:bunker | — | — |
| `combat.afb_all_ships` | PERMIT | effect:action_cards:waylay | — | — |
| `combat.afb_extra_dice` | MODIFY | leader:argentcommander | leaders:argentcommander | — |
| `combat.afb_extra_dice` | MODIFY | effect:promissory_notes:ambuscade:die | — | — |
| `combat.afb_granted` | FORBID | relic:metalivoidarmaments | relics:metalivoidarmaments | — |
| `combat.afb_infantry_kill` | FORBID | technology:swa2 | technologies:swa2 | Strike Wing Alpha II: When this unit uses ANTI-FIGHTER BARRAGE, each result of 9 or 10 also |
| `combat.afb_raid` | PERMIT | faction:argent | abilities:raid_formation | Raid Formation: When 1 or more of your units uses ANTI-FIGHTER BARRAGE: for each hit |
| `combat.bonus_dice` | MODIFY | effect:leaders:letnevagent:die | — | — |
| `combat.bonus_dice` | MODIFY | effect:leaders:solagent:die | — | — |
| `combat.extra_dice` | MODIFY | unit:winnu_flagship | units:winnu_flagship | Salai Sai Corian: When this unit makes a combat roll, it rolls a number of dice (hit on a 7) |
| `combat.extra_hits` | MODIFY | technology:vpw | technologies:vpw | Valkyrie Particle Weave: After making combat rolls during a round of ground combat, if your |
| `combat.granted_sustain` | PERMIT | relic:metalivoidshielding | relics:metalivoidshielding | Metali Void Shielding: Each time hits are produced against 1 or more of your non-fighter |
| `combat.hit_multiplier` | MODIFY | technology:x89c4 | technologies:x89c4 | X-89 ΩΩ: podwaja trafienia z bombardowania i z rzutów w walce NAZIEMNEJ. |
| `combat.hits_to_non_fighters` | FORBID | unit:l1z1x_flagship | units:l1z1x_flagship | [0.0.1]: During a space combat, hits produced by this ship and by your dreadnoughts in this |
| `combat.natural_extra_hits` | MODIFY | unit:jolnar_flagship | units:jolnar_flagship | J.N.S. Hylarim: When making a combat roll for this ship, each result of 9 or 10, before |
| `combat.reroll_plus_one` | PERMIT | relic:thalnos | relics:thalnos | The Crown of Thalnos: During each combat round, this card's owner may reroll any number of |
| `combat.roll_modifier` | MODIFY | effect:action_cards:f_prototype | — | — |
| `combat.roll_modifier` | MODIFY | effect:action_cards:mb1 | — | — |
| `combat.roll_modifier` | MODIFY | effect:action_cards:mb2 | — | — |
| `combat.roll_modifier` | MODIFY | effect:action_cards:mb3 | — | — |
| `combat.roll_modifier` | MODIFY | effect:action_cards:mb4 | — | — |
| `combat.roll_modifier` | MODIFY | faction:jolnar | abilities:fragile | Fragile: Apply -1 to the result of each of your unit's combat rolls (obowiązkowo). |
| `combat.roll_modifier` | MODIFY | unit:jolnar_mech | units:jolnar_mech | Shield Paling: Your infantry on this planet are not affected by your Fragile faction |
| `combat.roll_modifier` | MODIFY | effect:promissory_notes:tekklar | — | — |
| `combat.roll_modifier` | MODIFY | effect:promissory_notes:tekklar:penalty | — | — |
| `combat.roll_modifier` | MODIFY | agenda:prophecy | agendas:prophecy | — |
| `combat.roll_modifier` | MODIFY | faction:sardakk | abilities:unrelenting | Unrelenting: Apply +1 to the result of each of your unit's combat rolls. |
| `combat.roll_modifier` | MODIFY | unit:sardakk_flagship | units:sardakk_flagship | C'morran N'orr: Apply +1 to the result of each of your other ship's combat rolls in this |
| `combat.roll_modifier` | MODIFY | breakthrough:winnubt | breakthroughs:winnubt | Imperator: Apply +1 to the results of each of your unit's combat rolls for each "Support for |
| `combat.roll_modifier` | MODIFY | leader:winnucommander | leaders:winnucommander | Rickar Rickani: Apply +2 to the result of each of your unit's combat rolls in the Mecatol Rex |
| `combat.single_unit_bonus` | MODIFY | effect:breakthroughs:letnevbt:ship | — | — |
| `combat.sustain_cancels` | MODIFY | technology:nes | technologies:nes | Non-Euclidean Shielding: When 1 of your units uses SUSTAIN DAMAGE, cancel 2 hits instead |
| `combat.sustain_denied` | PERMIT | unit:mentak_flagship | units:mentak_flagship | Fourth Moon: Other player's ships in this system cannot use SUSTAIN DAMAGE. |
| `combat.sustain_denied` | PERMIT | unit:mentak_mech | units:mentak_mech | Moll Terminus: Other player's ground forces on this planet cannot use SUSTAIN DAMAGE. |
| `command_tokens.strategy_from_reinforcements` | FORBID | relic:emelpar | relics:emelpar | — |
| `control.structures_replaced` | PERMIT | faction:l1z1x | abilities:assimilate | Assimilate: struktury na zdobytej planecie wymienia hook niżej (nie giną od razu). |
| `custodians.free` | PERMIT | faction:winnu | abilities:blood_ties | Blood Ties: You do not have to spend influence to remove the custodians token from Mecatol |
| `dice.adjust_result` | FORBID | relic:heartofixth | relics:heartofixth | — |
| `economy.commodity_value` | MODIFY | relic:dynamiscore | relics:dynamiscore | Dynamis Core: While this card is in your play area, your commodity value is +2. |
| `elimination.has_production` | PERMIT | technology:mr | technologies:mr | F_muaat Magmus Reactor Ω 1: jednostka w supernowej = PRODUCTION, gracz nie odpada. |
| `event:agenda.law_discarded:when` | TRIGGER | agenda:censure | agendas:censure | — |
| `event:agenda.law_discarded:when` | TRIGGER | agenda:classified | agendas:classified | — |
| `event:agenda.law_discarded:when` | TRIGGER | agenda:defense_act | agendas:defense_act | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:const_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:diplo_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:imp_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:lead_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:politic_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:sanction | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:tech_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:trade_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:war_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:agendas:artifact:losses | agendas:artifact | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:agendas:artifact:research | agendas:artifact | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:agendas:redistribution:choose | agendas:redistribution | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:agendas:secret:return | agendas:secret | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:agendas:warrant:return | agendas:warrant | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | agenda:wormhole_research | agendas:wormhole_research | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:abolishment | agendas:abolishment | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:arms_reduction | agendas:arms_reduction | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:arms_reduction | agendas:arms_reduction | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:articles_war | agendas:articles_war | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:artifact | agendas:artifact | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:censure | agendas:censure | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:checks | agendas:checks | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:cladenstine | agendas:cladenstine | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:cladenstine | agendas:cladenstine | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:classified | agendas:classified | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:constitution | agendas:constitution | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:conventions | agendas:conventions | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:crisis | agendas:crisis | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:defense_act | agendas:defense_act | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:disarmament | agendas:disarmament | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:economic_equality | agendas:economic_equality | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:execution | agendas:execution | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:grant_reallocation | agendas:grant_reallocation | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:incentive | agendas:incentive | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:minister_antiquities | agendas:minister_antiquities | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:miscount | agendas:miscount | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:mutiny | agendas:mutiny | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:nexus | agendas:nexus | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:plowshares | agendas:plowshares | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:rearmament | agendas:rearmament | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:rearmament | agendas:rearmament | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:redistribution | agendas:redistribution | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:regulations | agendas:regulations | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:rep_govt | agendas:rep_govt | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:revolution | agendas:revolution | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:sanctions | agendas:sanctions | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:schematics | agendas:schematics | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:secret | agendas:secret | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:seed_empire | agendas:seed_empire | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:shared_research | agendas:shared_research | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:standardization | agendas:standardization | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:travel_ban | agendas:travel_ban | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:unconventional | agendas:unconventional | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:warrant | agendas:warrant | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:wormhole_recon | agendas:wormhole_recon | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:wormhole_research | agendas:wormhole_research | — |
| `event:agenda.outcome_resolved:during` | TRIGGER | agenda:wormhole_research | agendas:wormhole_research | — |
| `event:agenda.revealed:after` | TRIGGER | agenda:committee | agendas:committee | — |
| `event:cards.action_played:after` | TRIGGER | effect:action_cards:dp_give | — | — |
| `event:cards.action_played:when` | TRIGGER | effect:leaders:mentakhero:sleeper | leaders:mentakhero | Mentak zagrywa Direct Hit: statek zniszczony tą kartą zastępuje się OD RAZU, zanim inne |
| `event:combat.roll:after` | TRIGGER | unit:hacan_flagship | units:hacan_flagship | Wrath of Kenara: After you roll a die during a space combat in this system, you may spend 1 |
| `event:combat.round:end` | TRIGGER | technology:da | technologies:da | Duranium Armor: w każdej rundzie walki po przypisaniu strat naprawia 1 uszkodzoną jednostkę. |
| `event:combat.round:end` | TRIGGER | technology:exo2 | technologies:exo2 | Exotrireme II: After a round of space combat, you may destroy this unit to destroy up to 2 |
| `event:combat.round:end` | TRIGGER | faction:l1z1x | abilities:harrow | Harrow: At the end of each round of ground combat: Your ships in the active system may use |
| `event:combat.round:end` | TRIGGER | effect:leaders:mentakhero:sleeper | leaders:mentakhero | Po przypisaniu strat obu stron (F_mentak: „before the Mentak player places"). |
| `event:combat.round:end` | TRIGGER | faction:yin | abilities:devotion | Devotion: After each space combat round: You may destroy 1 of your cruisers or destroyers in |
| `event:combat.round:start` | TRIGGER | effect:leaders:mentakhero:sleeper | leaders:mentakhero | Straty z Ambush (przed 1. rundą) - statki przed rzutami rundy. |
| `event:combat.round:start` | TRIGGER | faction:letnev | abilities:munitions | Munitions Reserves: At the start of each round of space combat: You may spend 2 trade goods |
| `event:combat.round:start` | TRIGGER | unit:letnev_flagship | — | Arc Secundus: At the start of each space combat round, repair this ship. |
| `event:combat.round:start` | TRIGGER | unit:letnev_mech | units:letnev_mech | Dunlain Reaper — DEPLOY: At the start of a round of ground combat, you may spend 2 |
| `event:combat.round:start` | TRIGGER | leader:letnevagent | leaders:letnevagent | Viscount Unlenn: At the start of a space combat round: You may exhaust this card to choose 1 |
| `event:combat.round:start` | TRIGGER | breakthrough:letnevbt | breakthroughs:letnevbt | Gravleash Maneuvers: Before you roll dice during space combat, apply +X to the results of 1 |
| `event:combat.round:start` | TRIGGER | leader:solagent | leaders:solagent | Evelyn DeLouis: At the start of a ground combat round: You may exhaust this card to choose 1 |
| `event:combat.won:after` | TRIGGER | technology:dxa | technologies:dxa | Dacxive Animators: po wygranej walce naziemnej możesz postawić 1 piechotę na tej planecie. |
| `event:combat.won:after` | TRIGGER | leader:mentakcommander | leaders:mentakcommander | S'ula Mentarion: After you win a space combat: You may force your opponent to give you 1 |
| `event:combat.won:after` | TRIGGER | breakthrough:sardakkbt | breakthroughs:sardakkbt | N'orr Supremacy: After you win a combat, either gain 1 command token or research a unit |
| `event:combat.won:after` | TRIGGER | technology:so | technologies:so | Salvage Operations: ... if you won the combat, you may also produce 1 ship in that system of |
| `event:combat:end` | TRIGGER | technology:so | technologies:so | Salvage Operations: After you win or lose a space combat, gain 1 trade good (remis = nic, |
| `event:combat:start` | TRIGGER | technology:asc | technologies:asc | Assault Cannon: na początku walki kosmicznej przeciwnik niszczy 1 swój statek niemyśliwski. |
| `event:combat:start` | TRIGGER | technology:ic | technologies:ic | Impulse Core: At the start of a space combat, you may destroy 1 of your cruisers or |
| `event:combat:start` | TRIGGER | technology:md | technologies:md | Magen Defense Grid ΩΩ: na początku walki naziemnej na planecie z Twoją strukturą |
| `event:combat:start` | TRIGGER | faction:mentak | abilities:ambush | Ambush: At the start of a space combat: You may roll 1 die for each of up to 2 of your |
| `event:combat:start` | TRIGGER | leader:mentakhero | leaders:mentakhero | Ipswitch, Loose Cannon — Sleeper Cell: At the start of a space combat that you are |
| `event:combat:start` | TRIGGER | relic:metalivoidarmaments | — | Metali Void Armaments: During the "Anti-Fighter Barrage" step of space combat, you may |
| `event:combat:start` | TRIGGER | leader:solcommander | leaders:solcommander | Claire Gibson: At the start of a ground combat on a planet you control: You may place 1 |
| `event:combat:start` | TRIGGER | faction:yin | abilities:indoctrination | Indoctrination: At the start of a ground combat: You may spend 2 influence to replace 1 of |
| `event:component.action:after` | TRIGGER | agenda:minister_war | agendas:minister_war | — |
| `event:component.decision:after` | TRIGGER | effect:research:divert_funding | action_cards:divert_funding | — |
| `event:component.decision:after` | TRIGGER | effect:research:enigmatic_device | explores:ed1 | — |
| `event:component.decision:after` | TRIGGER | effect:research:f_researched | action_cards:f_researched | — |
| `event:component.decision:after` | TRIGGER | effect:research:reveal_prototype | action_cards:reveal_prototype | — |
| `event:component.exhausted:after` | TRIGGER | leader:sardakkagent | — | — |
| `event:component.gained:when` | TRIGGER | relic:bookoflatvinia | — | Book of Latvinia: When you gain this card, research up to 2 technologies that have no |
| `event:component.gained:when` | TRIGGER | breakthrough:muaatbt | breakthroughs:muaatbt | Stellar Genesis: When you gain this card, place the Avernus planet token into a non-home |
| `event:component.gained:when` | TRIGGER | relic:obsidian | relics:obsidian | The Obsidian: When you gain this card, draw 1 secret objective. |
| `event:component.gained:when` | TRIGGER | relic:quantumcore | relics:quantumcore | The Quantumcore: When you gain this card, gain your breakthrough. |
| `event:component.gained:when` | TRIGGER | relic:shard | — | Shard of the Throne: When you gain this card, gain 1 victory point. |
| `event:component.gained:when` | TRIGGER | breakthrough:yinbt | breakthroughs:yinbt | Yin Ascendant: When you gain this card ..., gain the alliance ability of a random, unused |
| `event:component.readied:when` | TRIGGER | effect:agendas:checks:against | agendas:checks | — |
| `event:economy.commodities_replenished:after` | TRIGGER | agenda:minister_commerce | agendas:minister_commerce | — |
| `event:economy.trade_goods_gained:after` | TRIGGER | faction:mentak | abilities:pillage | Pillage: After 1 of your neighbors gains trade goods ... |
| `event:faction.ability_used:after` | TRIGGER | effect:agendas:redistribution:place | agendas:redistribution | — |
| `event:faction.ability_used:after` | TRIGGER | faction:arborec | — | — |
| `event:faction.ability_used:after` | TRIGGER | leader:arborecagent | leaders:arborecagent | Zamieniany statek nie jest niszczony, nowy nie jest produkowany (F_arborec). |
| `event:faction.ability_used:after` | TRIGGER | faction:argent | abilities:raid_formation | Argent wybiera statki do uszkodzenia (wybrany uszkodzony statek - bez skutku, F_argent). |
| `event:faction.ability_used:after` | TRIGGER | leader:argentagent | — | Gracz produkujący przenosi wyprodukowane siły naziemne na swoje planety (0 = zostają). |
| `event:faction.ability_used:after` | TRIGGER | leader:jolnaragent | leaders:jolnaragent | — |
| `event:faction.ability_used:after` | TRIGGER | leader:l1z1xagent | — | Aktywny gracz wymienia 1 piechotę na mecha (mech zdjęty z planszy - nieuszkodzony, F_lizix |
| `event:faction.ability_used:after` | TRIGGER | leader:mentakagent | leaders:mentakagent | Suffi An: After the Pillage faction ability is used against another player: You may exhaust |
| `event:faction.ability_used:after` | TRIGGER | leader:mentakcommander | — | Przeciwnik oddaje wybraną notkę z ręki (decyzja obowiązkowa przeciwnika). |
| `event:faction.ability_used:after` | TRIGGER | unit:muaat_mech | units:muaat_mech | Ember Colossus: When you use your Star Forge faction ability in this system or an adjacent |
| `event:faction.ability_used:after` | TRIGGER | leader:muaatagent | — | Wybrany gracz otwiera produkcję: grant ``free`` (bez PRODUCTION jednostek - F_muaat umbat |
| `event:faction.ability_used:after` | TRIGGER | unit:sol_mech | units:sol_mech | ZS Thunderbolt M2 — DEPLOY: After you use your Orbital Drop faction ability, you may spend |
| `event:faction.ability_used:after` | TRIGGER | faction:yin | unlocks:yincommander | Unlock: Use one of your faction abilities (Indoctrination albo Devotion - F_yin Ω). |
| `event:objective.revealed:after` | TRIGGER | relic:neuraloop | relics:neuraloop | Neuraloop: When a public objective is revealed, you may purge one of your relics to discard |
| `event:objective.scored:after` | TRIGGER | breakthrough:yinbt | breakthroughs:yinbt | Yin Ascendant: ... or score a public objective, gain the alliance ability of a random, |
| `event:phase:end` | TRIGGER | technology:bio | technologies:bio | Bioplasmosis: At the end of the status phase, you may remove any number of infantry from |
| `event:phase:end` | TRIGGER | relic:emphidia | relics:emphidia | The Crown of Emphidia: At the end of the status phase, if you control the "Tomb of |
| `event:phase:end` | TRIGGER | agenda:minister_policy | agendas:minister_policy | — |
| `event:phase:end` | TRIGGER | technology:qdn | technologies:qdn | Quantum Datahub Node: At the end of the strategy phase, you may spend 1 token from your |
| `event:phase:end` | TRIGGER | unit:sol_flagship | units:sol_flagship | Genesis: At the end of the status phase, place 1 infantry from your reinforcements in this |
| `event:phase:start` | TRIGGER | effect:agendas:arms_reduction:against | agendas:arms_reduction | — |
| `event:phase:start` | TRIGGER | effect:agendas:constitution:for | agendas:constitution | — |
| `event:phase:start` | TRIGGER | effect:agendas:rep_govt:against | agendas:rep_govt | — |
| `event:phase:start` | TRIGGER | effect:agendas:revolution:against | agendas:revolution | — |
| `event:phase:start` | TRIGGER | faction:arborec | abilities:mitosis | Mitosis: At the start of the status phase: Place 1 infantry from your reinforcements on any |
| `event:phase:start` | TRIGGER | technology:inf2 | technologies:inf2 | Każda piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:phase:start` | TRIGGER | technology:inf2 | technologies:inf2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:phase:start` | TRIGGER | technology:lw2 | technologies:lw2 | Każda piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:phase:start` | TRIGGER | technology:lw2 | technologies:lw2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:phase:start` | TRIGGER | relic:mawofworlds | relics:mawofworlds | Maw of Worlds: At the start of the agenda phase, you may purge this card and exhaust all of |
| `event:phase:start` | TRIGGER | technology:so2 | technologies:so2 | Każda piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:phase:start` | TRIGGER | technology:so2 | technologies:so2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:phase:start` | TRIGGER | technology:td | technologies:td | Transit Diodes: na początku Twojej tury w fazie akcji wyczerp kartę i przenieś do 4 sił |
| `event:planet.control_gained:after` | TRIGGER | technology:ie | technologies:ie | Integrated Economy: po zdobyciu planety możesz wyprodukować dowolną liczbę jednostek |
| `event:planet.control_gained:after` | TRIGGER | faction:l1z1x | abilities:assimilate | Assimilate: When you gain control of a planet: Replace each PDS and space dock that is on |
| `event:planet.control_gained:after` | TRIGGER | breakthrough:l1z1xbt | breakthroughs:l1z1xbt | Fealty Uplink: When you gain control of a planet, place infantry from your reinforcements |
| `event:planet.control_gained:after` | TRIGGER | agenda:minister_exploration | agendas:minister_exploration | — |
| `event:planet.control_gained:after` | TRIGGER | relic:shard | relics:shard | Shard of the Throne: When a player gains control of a legendary planet you control or a |
| `event:planet.control_gained:after` | TRIGGER | planet:styx | planets:styx | A Song Like Marrow: When you gain this card, gain 1 victory point. |
| `event:planet.control_gained:after` | TRIGGER | planet:thundersedge | planets:thundersedge | Jupiter Brain: Gain your breakthrough when you gain this card if you do not already have |
| `event:planet.control_lost:when` | TRIGGER | planet:styx | planets:styx | A Song Like Marrow: When you lose this card, lose 1 victory point. |
| `event:planet.explored:after` | TRIGGER | effect:breakthroughs:l1z1xbt:after_explore | — | Piechota Fealty Uplink postawiona po eksploracji planety (wybór gracza, F_lizix 1). |
| `event:player.passed:when` | TRIGGER | planet:faunus | planets:faunus | Maxis Central Control: You may exhaust this card when you pass to gain control of a non-home, non-legendary planet that contains no units and has no attachments. |
| `event:player.passed:when` | TRIGGER | planet:garbozia | planets:garbozia | Dok 'N Pic's Salvage Yard: You may exhaust this card when you pass to place 1 action card from the discard pile faceup on this card. |
| `event:player.passed:when` | TRIGGER | planet:industrex | planets:industrex | Aeurex Mechanica: You may exhaust this card when you pass to place 1 ship that matches a unit upgrade technology you own from your reinforcements into a system that contains your ships. |
| `event:player.passed:when` | TRIGGER | planet:ordinian | planets:ordinian | Hyperion: You may exhaust this card when you pass to draw 1 action card and gain 1 command token. |
| `event:player.passed:when` | TRIGGER | planet:ordinianc4 | planets:ordinianc4 | Hyperion: You may exhaust this card when you pass to draw 1 action card and gain 1 command token. |
| `event:production.units_produced:after` | TRIGGER | leader:argentagent | leaders:argentagent | Trilossa Aun Mirik: When a player produces ground forces in a system: You may exhaust this |
| `event:production.units_produced:after` | TRIGGER | breakthrough:hacanbt | breakthroughs:hacanbt | Auto-Factories: When you produce 3 or more non-fighter ships, place 1 command token from your |
| `event:production.units_produced:after` | TRIGGER | faction:muaat | unlocks:muaatcommander | Unlock: Produce a war sun. |
| `event:production.units_produced:after` | TRIGGER | technology:yso | technologies:yso | Yin Spinner Ω: After you produce units, place up to 2 infantry from your reinforcements on |
| `event:production.used:after` | TRIGGER | agenda:prophecy | agendas:prophecy | — |
| `event:production.used:after` | TRIGGER | technology:sar | technologies:sar | Self-Assembly Routines: po PRODUCTION wyczerp kartę, by postawić 1 mecha z rezerwy |
| `event:strategy.action:after` | TRIGGER | faction:xxcha | abilities:peace_accords | Peace Accords: After you resolve the primary or secondary ability of the "Diplomacy" |
| `event:strategy.card_chosen:after` | TRIGGER | agenda:arbiter | agendas:arbiter | — |
| `event:strategy.imperial_victory_point:after` | TRIGGER | planet:custodiavigilia | planets:custodiavigilia | Custodian's Favour: Gain 2 command tokens when another player scores a victory point with |
| `event:strategy.token_spent:after` | TRIGGER | leader:muaatcommander | leaders:muaatcommander | Magmus: After you spend a token from your strategy pool: You may gain 1 trade good. |
| `event:tactical.action:end` | TRIGGER | breakthrough:argentbt | breakthroughs:argentbt | Wing Transfer: … at the end of this action, you may move ships among the active system and |
| `event:tactical.action:end` | TRIGGER | technology:det | technologies:det | Dark Energy Tap: po akcji taktycznej w systemie z żetonem frontier i Twoim statkiem |
| `event:tactical.action:end` | TRIGGER | relic:emphidia | relics:emphidia | The Crown of Emphidia: After you perform a tactical action, you may exhaust this card to |
| `event:tactical.action:end` | TRIGGER | agenda:minister_war | agendas:minister_war | — |
| `event:tactical.action:end` | TRIGGER | leader:sardakkagent | leaders:sardakkagent | T'ro: At the end of a player's tactical action: You may exhaust this card: if you do, that |
| `event:tactical.action:end` | TRIGGER | faction:winnu | abilities:reclamation | Reclamation: After you resolve a tactical action during which you gained control of Mecatol |
| `event:tactical.action:end` | TRIGGER | unit:winnu_mech | units:winnu_mech | Reclaimer: After you resolve a tactical action where you gained control of this planet, you |
| `event:tactical.ships_moved:after` | TRIGGER | breakthrough:muaatbt | breakthroughs:muaatbt | After you move one of your war suns out of or through Avernus's system and into a non-home |
| `event:tactical.ships_moved:after` | TRIGGER | leader:muaathero | leaders:muaathero | Adjudicator Ba'al — Nova Seed: After you move a war sun into a non-home system other than |
| `event:tactical.system_activated:after` | TRIGGER | promissory:<color>_an | promissory_notes:<color>_an | — |
| `event:tactical.system_activated:after` | TRIGGER | promissory:<color>_sftt | promissory_notes:<color>_sftt | — |
| `event:tactical.system_activated:after` | TRIGGER | unit:arborec_flagship | units:arborec_flagship | Duha Menaimon: After you activate this system, you may produce up to 5 units in this |
| `event:tactical.system_activated:after` | TRIGGER | leader:arboreccommander | leaders:arboreccommander | Dirzuga Rophal: After another player activates a system that contains 1 or more of your |
| `event:tactical.system_activated:after` | TRIGGER | breakthrough:argentbt | breakthroughs:argentbt | Wing Transfer: When you activate a system that contains only your units, you may place |
| `event:tactical.system_activated:after` | TRIGGER | promissory:convoys | promissory_notes:convoys | If you activate a system that contains 1 or more of the Hacan player's units, return this |
| `event:tactical.system_activated:after` | TRIGGER | relic:dominusorb | relics:dominusorb | Dominus Orb: Before you move units during a tactical action, you may purge this card to |
| `event:tactical.system_activated:after` | TRIGGER | technology:ers | technologies:ers | E-Res Siphons: After another player activates a system that contains 1 or more of your |
| `event:tactical.system_activated:after` | TRIGGER | leader:l1z1xagent | leaders:l1z1xagent | I48S: After a player activates a system: You may exhaust this card to allow that player to |
| `event:tactical.system_activated:after` | TRIGGER | agenda:minister_peace | agendas:minister_peace | — |
| `event:tactical.system_activated:after` | TRIGGER | technology:nf | technologies:nf | Nullification Field: After another player activates a system that contains 1 or more of your |
| `event:tactical.system_activated:after` | TRIGGER | promissory:pop | promissory_notes:pop | If you activate a system that contains 1 or more of the Mentak player's units, return this |
| `event:tactical.system_activated:after` | TRIGGER | technology:scc | technologies:scc | Spatial Conduit Cylinder: You may exhaust this card after you activate a system that |
| `event:tactical.system_activated:after` | TRIGGER | technology:sdn | technologies:sdn | Scanlink Drone Network: przy aktywacji systemu możesz zbadać 1 planetę z Twoimi |
| `event:tactical.system_activated:after` | TRIGGER | planet:tempesta | planets:tempesta | Ionian Fuel Refinery: You may exhaust this card after you activate a system to apply +1 to the move value of 1 of your ships during this tactical action. |
| `event:tactical.system_activated:when` | TRIGGER | technology:md | technologies:md | Magen Defense Grid ΩΩ: aktywacja systemu z Twoimi strukturami → 1 piechota przy każdej. |
| `event:tactical.units_committed:after` | TRIGGER | effect:leaders:sardakkhero | — | — |
| `event:technology.research:after` | TRIGGER | agenda:revolution | agendas:revolution | — |
| `event:technology.research:when` | TRIGGER | relic:prophetstears | relics:prophetstears | The Prophet's Tears: When you research a technology, you may exhaust this card to ignore 1 |
| `event:transaction:after` | TRIGGER | effect:action_cards:blackmarketdealing | — | Karta dotyczy jednej transakcji: po jej rozstrzygnięciu efekt znika. |
| `event:transaction:after` | TRIGGER | faction:mentak | abilities:pillage | Pillage: After 1 of your neighbors ... resolves a transaction (strona aktywna). |
| `event:transaction:after` | TRIGGER | faction:mentak | abilities:pillage | Pillage przeciw partnerowi transakcji (F_mentak: także przeciw obu stronom i przeciw |
| `event:turn:end` | TRIGGER | technology:bs | technologies:bs | Bio-Stims: na końcu tury możesz wyczerpać kartę, by odświeżyć planetę ze specjalnością |
| `event:turn:end` | TRIGGER | planet:emelpar | planets:emelpar | The Acropolis: You may exhaust this card at the end of your turn to ready another component that isn't a strategy card. |
| `event:turn:end` | TRIGGER | planet:hopesend | planets:hopesend | Imperial Arms Vault: You may exhaust this card at the end of your turn to place 1 mech from your reinforcements on any planet you control or draw 1 action card. |
| `event:turn:end` | TRIGGER | planet:illusion | planets:illusion | Flight Academy: You may exhaust this card at the end of your turn to place up to 2 fighters from your reinforcements in any system that contains 1 or more of your ships. |
| `event:turn:end` | TRIGGER | planet:lockedmallice | planets:lockedmallice | Exterrix Headquarters: You may exhaust this card at the end of your turn to gain 2 trade goods or convert all of your commodities to trade goods. |
| `event:turn:end` | TRIGGER | planet:mallice | planets:mallice | Exterrix Headquarters: You may exhaust this card at the end of your turn to gain 2 trade goods or convert all of your commodities to trade goods. |
| `event:turn:end` | TRIGGER | planet:mirage | planets:mirage | Flight Academy: You may exhaust this card at the end of your turn to place up to 2 fighters from your reinforcements in any system that contains 1 or more of your ships. |
| `event:turn:end` | TRIGGER | planet:mrte | planets:mrte | The Galactic Council: You may exhaust this card at the end of your turn and discard 1 secret objective to draw 1 secret objective. |
| `event:turn:end` | TRIGGER | planet:phantasm | planets:phantasm | Flight Academy: You may exhaust this card at the end of your turn to place up to 2 fighters from your reinforcements in any system that contains 1 or more of your ships. |
| `event:turn:end` | TRIGGER | technology:pi | technologies:pi | Predictive Intelligence: na końcu tury wyczerp kartę, by przerozdzielić żetony dowodzenia. |
| `event:turn:end` | TRIGGER | planet:primor | planets:primor | The Atrament: You may exhaust this card at the end of your turn to place up to 2 infantry from your reinforcements on any planet you control. |
| `event:turn:end` | TRIGGER | planet:thundersedge | planets:thundersedge | Jupiter Brain: You may exhaust this card at the end of your turn to perform another action. |
| `event:turn:start` | TRIGGER | technology:inf2 | technologies:inf2 | Każda piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:turn:start` | TRIGGER | technology:inf2 | technologies:inf2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:turn:start` | TRIGGER | technology:lw2 | technologies:lw2 | Każda piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:turn:start` | TRIGGER | technology:lw2 | technologies:lw2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:turn:start` | TRIGGER | technology:so2 | technologies:so2 | Każda piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:turn:start` | TRIGGER | technology:so2 | technologies:so2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:turn:start` | TRIGGER | technology:td | — | Transit Diodes: na początku Twojej tury w fazie akcji wyczerp kartę i przenieś do 4 sił |
| `event:unit.ability_used:after` | TRIGGER | leader:jolnarcommander | — | Agnlan Oln (AFB): walka czeka po rzucie AFB na tę ofertę (``battle.resolve_afb``). |
| `event:unit.ability_used:after` | TRIGGER | effect:promissory_notes:ambuscade:die | — | Po rzucie zdolności jednostki premia z notki przepada (jedna kość, jeden rzut). |
| `event:unit.ability_used:after` | TRIGGER | technology:x89c4 | technologies:x89c4 | X-89 ΩΩ: każda planeta, przeciw której użyto BOMBARDMENT, zostaje wyczerpana. |
| `event:unit.destroyed:after` | TRIGGER | technology:inf2 | technologies:inf2 | Infantry II / Spec Ops II: po zniszczeniu piechoty rzuć kością; przy progu+ jednostka |
| `event:unit.destroyed:after` | TRIGGER | effect:leaders:mentakhero:sleeper | leaders:mentakhero | F_mentak 7.1: po Direct Hit Mentaka statek tego typu staje od razu (może jeszcze w tej |
| `event:unit.destroyed:after` | TRIGGER | technology:lw2 | technologies:lw2 | Infantry II / Spec Ops II: po zniszczeniu piechoty rzuć kością; przy progu+ jednostka |
| `event:unit.destroyed:after` | TRIGGER | technology:sar | — | Self-Assembly Routines: po zniszczeniu Twojego mecha zdobywasz 1 TG (za każdego mecha; |
| `event:unit.destroyed:after` | TRIGGER | technology:so2 | technologies:so2 | Infantry II / Spec Ops II: po zniszczeniu piechoty rzuć kością; przy progu+ jednostka |
| `event:unit.destroyed:after` | TRIGGER | unit:yin_flagship | units:yin_flagship | Van Hauge: When this ship is destroyed, destroy all ships in this system. |
| `event:unit.destroyed:after` | TRIGGER | leader:yinagent | leaders:yinagent | Brother Milor Ω: After a player's unit is destroyed during combat: You may exhaust this card |
| `event:unit.placed:after` | TRIGGER | agenda:minister_industry | agendas:minister_industry | — |
| `event:unit.sustain_damage:after` | TRIGGER | leader:letnevcommander | leaders:letnevcommander | Rear Admiral Farran: After 1 of your units uses SUSTAIN DAMAGE: You may gain 1 trade good |
| `event:unit.sustain_damage:after` | TRIGGER | unit:sardakk_mech | units:sardakk_mech | Valkyrie Exoskeleton: After this unit uses its SUSTAIN DAMAGE ability during ground combat, |
| `fleet_pool.capacity` | MODIFY | faction:letnev | abilities:armada | Armada: The maximum number of non-fighter ships you can have in each system is equal to 2 |
| `fleet_pool.token_cap` | MODIFY | agenda:regulations | agendas:regulations | — |
| `fleet_pool.unlimited` | PERMIT | effect:leaders:letnevhero | — | — |
| `hand_limit.action_cards` | MODIFY | agenda:sanctions | agendas:sanctions | — |
| `invasion.commit_from_planets` | PERMIT | leader:sardakkcommander | — | F_norr: G'hom Sek'kus działa także bez statków w aktywnym systemie - inwazja otwiera |
| `invasion.skip_bombardment` | PERMIT | effect:leaders:sardakkhero | — | — |
| `invasion.strips_planetary_shield` | PERMIT | unit:letnev_flagship | units:letnev_flagship | Arc Secundus: Other player's units in this system lose PLANETARY SHIELD. |
| `limits.pds_unlimited` | PERMIT | agenda:defense_act | agendas:defense_act | — |
| `movement.alpha_beta_adjacent` | PERMIT | effect:action_cards:lost_star | — | — |
| `movement.alpha_beta_adjacent` | PERMIT | agenda:wormhole_recon | agendas:wormhole_recon | — |
| `movement.enter_asteroids` | PERMIT | technology:amd | technologies:amd | Antimass Deflectors: statki mogą wchodzić do pól asteroid i przez nie przechodzić. |
| `movement.enter_asteroids` | PERMIT | relic:circletofthevoid | — | Circlet of the Void: ruch przez/do pól asteroid (ignorowanie efektów anomalii). |
| `movement.extra_adjacent` | FORBID | technology:lgf | technologies:lgf | Lazax Gate Folding: During your tactical actions, if you do not control Mecatol Rex, treat |
| `movement.extra_adjacent` | FORBID | effect:technologies:scc | — | Aktywny system sąsiaduje ze wszystkimi systemami z jednostkami gracza (i odwrotnie). |
| `movement.ignore_anomalies` | PERMIT | effect:action_cards:nav_suite | — | — |
| `movement.ignore_anomalies_keep_rift` | PERMIT | relic:circletofthevoid | relics:circletofthevoid | Circlet of the Void: Your units do not roll for gravity rifts, and you ignore the effects |
| `movement.ignore_own_command_token` | PERMIT | effect:relics:dominusorb | — | — |
| `movement.into_supernova` | PERMIT | technology:mr | technologies:mr | Magmus Reactor: Your ships can move into supernovas (cel ruchu i odwrót - R_space_combat). |
| `movement.match_highest` | PERMIT | breakthrough:letnevbt | — | Gravleash Maneuvers: During movement, your non-fighter ships' move values are equal to the |
| `movement.move_value` | MODIFY | effect:action_cards:fs1 | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs2 | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs3 | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs4 | — | — |
| `movement.move_value` | MODIFY | technology:gd | technologies:gd | Gravity Drive: po aktywacji +1 do wartości ruchu JEDNEGO statku w tej akcji. |
| `movement.move_value` | MODIFY | effect:planets:tempesta | planets:tempesta | Ionian Fuel Refinery: +1 do wartości ruchu JEDNEGO statku w tej akcji taktycznej. |
| `movement.move_value` | MODIFY | breakthrough:winnubt | — | After you activate a system that contains a legendary planet, apply +1 to the move value of 1 |
| `movement.pass_foreign_ships` | PERMIT | effect:action_cards:silence_space | — | Przelot przez obce statki dotyczy tylko statków startujących z wybranego systemu. |
| `movement.pass_foreign_ships` | PERMIT | technology:lwd | technologies:lwd | Light/Wave Deflector: statki mogą przechodzić przez systemy z cudzymi statkami. |
| `movement.pass_foreign_ships` | PERMIT | unit:mentak_cruiser3 | units:mentak_cruiser3 | Corsair: If the active system contains another player's non-fighter ships, this unit can |
| `movement.passage_blocked` | PERMIT | technology:ah | technologies:ah | Aerie Hololattice: Other players cannot move ships through systems that contain your |
| `movement.through_nebula` | PERMIT | agenda:shared_research | agendas:shared_research | — |
| `movement.through_supernova` | PERMIT | faction:muaat | abilities:gashlai_physiology | Gashlai Physiology: Your ships can move through supernovas (węzeł pośredni trasy). |
| `movement.wormholes_blocked` | FORBID | agenda:nexus | agendas:nexus | — |
| `movement.wormholes_blocked` | FORBID | agenda:travel_ban | agendas:travel_ban | — |
| `objectives.secret_limit` | MODIFY | relic:obsidian | relics:obsidian | The Obsidian: You can have 1 additional scored or unscored secret objective. |
| `payment.flex_spend` | PERMIT | breakthrough:xxchabt | breakthroughs:xxchabt | Archon's Gift: You can spend influence as if it were resources. You can spend resources as if |
| `payment.trade_good_value` | MODIFY | technology:mc | technologies:mc | Mirror Computing: When you spend trade goods, each trade good is worth 2 resources or |
| `planet.swap_values` | FORBID | effect:technologies:htp:swap | — | — |
| `production.cost` | MODIFY | effect:action_cards:war_machine | — | — |
| `production.cost` | MODIFY | effect:leaders:winnuagent:cut | — | — |
| `production.cost` | MODIFY | technology:st | technologies:st | Sarween Tools: gdy jednostki używają PRODUCTION, łączny koszt jest niższy o 1. |
| `production.forbids` | FORBID | faction:arborec | — | Mitosis: Your space docks cannot produce infantry (R_production). |
| `production.free` | PERMIT | effect:leaders:hacanhero:free | — | — |
| `production.free_cargo` | PERMIT | breakthrough:solbt | breakthroughs:solbt | Bellum Gloriosum: When you produce a ship that has capacity, you may also produce any |
| `production.planet_value` | MODIFY | technology:ah | technologies:ah | Aerie Hololattice: Each planet that contains 1 or more of your structures gains the |
| `production.system_value` | MODIFY | technology:mr | technologies:mr | Each supernova that contains 1 or more of your units gains the PRODUCTION 5 ability as if |
| `production.total_value` | MODIFY | effect:action_cards:war_machine | — | — |
| `production.units_per_cost` | MODIFY | agenda:conscription | agendas:conscription | — |
| `retreat.anywhere` | PERMIT | technology:det | — | Dark Energy Tap: statki mogą wycofać się do sąsiedniego systemu bez cudzych jednostek. |
| `space_cannon.defense_immune` | PERMIT | technology:l4 | technologies:l4 | L4 Disruptors: During an invasion, units cannot use SPACE CANNON against your units. |
| `space_cannon.extra_dice` | MODIFY | leader:argentcommander | leaders:argentcommander | — |
| `space_cannon.extra_dice` | MODIFY | effect:promissory_notes:ambuscade:die | — | — |
| `space_cannon.extra_dice` | MODIFY | technology:ps | technologies:ps | Plasma Scoring: 1 z jednostek używających SPACE CANNON rzuca 1 dodatkową kością. |
| `space_cannon.granted` | FORBID | relic:lightrailordnance | relics:lightrailordnance | Lightrail Ordnance: Your space docks gain SPACE CANNON 5 (x2). You may use your space |
| `space_cannon.offense_immune` | PERMIT | effect:action_cards:solar_flare | — | — |
| `space_cannon.offense_immune` | PERMIT | unit:argent_flagship | units:argent_flagship | Quetzecoatl: Other players cannot use space cannon against your ships in this system. |
| `space_cannon.pds_disabled` | PERMIT | effect:action_cards:disable | — | — |
| `space_cannon.roll_modifier` | MODIFY | technology:amd | technologies:amd | Antimass Deflectors: -1 do wyniku kości Space Cannon rzucanych przeciw jego jednostkom. |
| `status.action_cards` | MODIFY | technology:nm | technologies:nm | Neural Motivator: w fazie statusu gracz dobiera 2 karty akcji zamiast 1. |
| `status.command_tokens` | MODIFY | technology:hm | technologies:hm | Hyper Metabolism: w fazie statusu gracz zdobywa 3 żetony dowodzenia zamiast 2. |
| `status.command_tokens` | MODIFY | faction:sol | abilities:versatile | Versatile: When you gain command tokens during the status phase: Gain 1 additional command |
| `strategy.give_chosen_card` | PERMIT | agenda:checks | agendas:checks | — |
| `strategy.secondary_as_primary` | PERMIT | faction:jolnar | abilities:brilliant | Brilliant: When you spend a command token to resolve the secondary ability of the |
| `strategy.secondary_free` | PERMIT | faction:hacan | abilities:master_of_trade | Masters of Trade: You do not have to spend a command token to resolve the secondary |
| `technology.free_prerequisite_ignores` | MODIFY | faction:jolnar | abilities:analytical | Analytical: When you research a technology that is not a unit upgrade technology: You may |
| `technology.free_prerequisite_ignores` | MODIFY | agenda:schematics | agendas:schematics | — |
| `technology.ignore_prerequisite` | FORBID | relic:prophetstears | relics:prophetstears | — |
| `technology.infantry_skip` | PERMIT | leader:yincommander | leaders:yincommander | Brother Omar Ω: When you research a tech owned by another player, you may return 1 of your |
| `technology.paid_ignore_all` | FORBID | technology:is | technologies:is | Inheritance Systems: You may exhaust this card and spend 2 resources when you research a |
| `technology.specialty_pays` | PERMIT | breakthrough:jolnarbt | breakthroughs:jolnarbt | Specialist Compounds: When you research technology using the 'Technology' strategy card, |
| `technology.specialty_without_exhaust` | PERMIT | technology:pa | — | Psychoarchaeology: specjalności technologii działają bez wyczerpywania planet, także |
| `technology.strategy_card_free` | PERMIT | agenda:minister_sciences | agendas:minister_sciences | — |
| `technology.synergy_all` | PERMIT | relic:quantumcore | — | The Quantumcore: You have SYNERGY for all technology types. |
| `technology.virtual_prerequisites` | MODIFY | leader:yincommander | leaders:yincommander | Brother Omar Ω: This card satisfies a green technology prerequisite. |
| `transaction.action_cards` | PERMIT | faction:hacan | abilities:arbiters | Arbiters: When you are negotiating a transaction, action cards can be exchanged as part of |
| `transaction.any_player` | PERMIT | promissory:convoys | — | While this card is in your play area, you may negotiate transactions with players who are |
| `transaction.any_player` | PERMIT | faction:hacan | abilities:guild_ships | Guild Ships: You can negotiate transactions with players who are not your neighbor. |
| `transaction.extra_items` | PERMIT | effect:action_cards:blackmarketdealing | — | — |
| `transaction.planets` | FORBID | unit:hacan_mech | units:hacan_mech | Pride of Kenara: This planet's card may be traded as part of a transaction; if you do, move |
| `transaction.tradable_relics` | FORBID | relic:thesilverflame | relics:thesilverflame | „The Silver Flame may be exchanged as part of a transaction” - bez Black Market Dealings. |
| `turn.action_started` | PERSISTENT | effect:action_cards:extremeduress | — | Pierwsza akcja celu: strategiczna = bez kary; inna = karty, TG i tajne cele dla gracza. |
| `turn.actions` | MODIFY | effect:action_cards:master_plan | — | — |
| `turn.actions` | MODIFY | effect:agendas:minister_war:action | agendas:minister_war | — |
| `turn.actions` | MODIFY | technology:fl | technologies:fl | Fleet Logistics: w swojej turze fazy akcji gracz wykonuje 2 akcje zamiast 1. |
| `units.sustain_lost` | FORBID | agenda:schematics | agendas:schematics | — |

Dostępne punkty zaczepienia (stałe `POINT_*` w `core/rules_hooks.py`):

- `action_cards.forbidden`
- `action_cards.canceller`
- `turn.action_started`
- `agenda.single_vote`
- `agenda.votes_per_planet`
- `agenda.vote_first`
- `agenda.vote_modifier`
- `agenda.vote_unblockable`
- `bombardment.extra_dice`
- `bombardment.forbidden_traits`
- `bombardment.granted_hits_on`
- `bombardment.ground_units`
- `bombardment.ignores_planetary_shield`
- `bombardment.roll_modifier`
- `bombardment.empty_planets`
- `combat.afb_all_ships`
- `combat.afb_extra_dice`
- `combat.afb_granted`
- `combat.afb_infantry_kill`
- `combat.afb_raid`
- `combat.bonus_dice`
- `combat.extra_dice`
- `combat.extra_hits`
- `combat.granted_sustain`
- `combat.hits_to_non_fighters`
- `combat.hit_multiplier`
- `combat.natural_extra_hits`
- `combat.reroll_misses`
- `combat.reroll_plus_one`
- `combat.roll_modifier`
- `combat.single_unit_bonus`
- `combat.sustain_cancels`
- `combat.sustain_denied`
- `economy.commodity_value`
- `control.structures_replaced`
- `custodians.free`
- `dice.adjust_result`
- `elimination.has_production`
- `fleet_pool.capacity`
- `fleet_pool.token_cap`
- `fleet_pool.unlimited`
- `hand_limit.action_cards`
- `invasion.commit_from_planets`
- `invasion.skip_bombardment`
- `movement.alpha_beta_adjacent`
- `movement.enter_asteroids`
- `movement.extra_adjacent`
- `movement.ignore_anomalies`
- `movement.ignore_anomalies_keep_rift`
- `movement.ignore_own_command_token`
- `movement.into_supernova`
- `movement.match_highest`
- `movement.move_value`
- `movement.passage_blocked`
- `movement.pass_foreign_ships`
- `movement.through_nebula`
- `movement.through_supernova`
- `movement.wormholes_blocked`
- `payment.commodities_as_trade_goods`
- `payment.flex_spend`
- `payment.trade_good_value`
- `space_cannon.pds_disabled`
- `limits.pds_unlimited`
- `agenda.planets_ready_limit`
- `planet.swap_values`
- `production.cost`
- `production.forbids`
- `production.free`
- `production.free_cargo`
- `production.planet_value`
- `production.system_value`
- `production.total_value`
- `production.units_per_cost`
- `production.value`
- `retreat.anywhere`
- `objectives.secret_limit`
- `space_cannon.defense_immune`
- `space_cannon.extra_dice`
- `space_cannon.granted`
- `space_cannon.offense_immune`
- `space_cannon.roll_modifier`
- `status.action_cards`
- `status.command_tokens`
- `strategy.give_chosen_card`
- `strategy.secondary_as_primary`
- `strategy.secondary_free`
- `command_tokens.strategy_from_reinforcements`
- `invasion.strips_planetary_shield`
- `technology.free_prerequisite_ignores`
- `technology.ignore_prerequisite`
- `technology.infantry_skip`
- `technology.paid_ignore_all`
- `technology.strategy_card_free`
- `technology.specialty_without_exhaust`
- `technology.specialty_pays`
- `technology.synergy_all`
- `technology.virtual_prerequisites`
- `transaction.action_cards`
- `transaction.any_player`
- `transaction.extra_items`
- `transaction.planets`
- `transaction.tradable_relics`
- `turn.actions`
- `units.sustain_lost`
