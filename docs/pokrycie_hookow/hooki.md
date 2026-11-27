# Pokrycie hooków: zarejestrowane hooki

Generowany — nie edytuj. Podsumowanie: [`../POKRYCIE_HOOKOW.md`](../POKRYCIE_HOOKOW.md).

## 1. Zarejestrowane hooki

Razem: **515**. Opis = pierwsza linia docstringu funkcji hooka.

| Punkt zaczepienia | Rodzaj | Źródło | Komponent | Co robi |
|---|---|---|---|---|
| `action_cards.canceller` | PERMIT | unit:empyrean_mech | units:empyrean_mech | Public: a Watcher in / next to the card player's units - the hold window opens. |
| `action_cards.canceller` | PERMIT | technology:it | technologies:it | Jawne: gotowa technologia i żeton w strategy pool - okno anulowania się otwiera. |
| `action_cards.forbidden` | FORBID | agenda:censure | agendas:censure | — |
| `action_cards.forbidden` | FORBID | rule:technologies:tp:passed_players | technologies:tp | Transparasteel Plating: During your turn of the action phase, players that have passed |
| `adjacency.cut_for_player` | FORBID | rule:breakthroughs:empyreanbt:cut | breakthroughs:empyreanbt | ...other players do not treat those systems as adjacent to each other unless you allow it |
| `adjacency.extra_for_player` | FORBID | faction:ghost | abilities:quantum_entanglement | Quantum Entanglement: You treat all systems that contain either an alpha or beta wormhole as |
| `agenda.planets_ready_limit` | FORBID | effect:agendas:checks:against | agendas:checks | — |
| `agenda.single_vote` | PERMIT | agenda:rep_govt | agendas:rep_govt | — |
| `agenda.vote_first` | PERMIT | faction:argent | abilities:zeal | Zeal: You always vote first during the agenda phase (także jako mówca - F_argent). |
| `agenda.vote_modifier` | MODIFY | faction:argent | abilities:zeal | Zeal: When you cast at least 1 vote: cast 1 additional vote for each player in the game |
| `agenda.vote_modifier` | MODIFY | effect:leaders:hacancommander:votes | — | F_hacan: przy 0 zwykłych głosów (wstrzymanie się) dodatkowych głosów nie ma. |
| `agenda.vote_unblockable` | PERMIT | leader:xxchacommander | leaders:xxchacommander | Elder Qanoj: Game effects cannot prevent you from voting on an agenda (F_xxcha: Political |
| `agenda.votes_per_planet` | MODIFY | leader:xxchacommander | leaders:xxchacommander | Elder Qanoj: Each planet you exhaust to cast votes provides 1 additional vote (także planeta |
| `board.unit_wormholes` | FORBID | unit:ghost_flagship | units:ghost_flagship | Hil Colish: This ship's system contains a delta wormhole. (Not a token - an entropic scar |
| `bombardment.empty_planets` | PERMIT | technology:x89c4 | technologies:x89c4 | X-89 ΩΩ: wolno bombardować planetę bez sił naziemnych (C_technology). |
| `bombardment.extra_dice` | MODIFY | leader:argentcommander | leaders:argentcommander | — |
| `bombardment.extra_dice` | MODIFY | effect:promissory_notes:ambuscade:die | — | — |
| `bombardment.extra_dice` | MODIFY | technology:ps | technologies:ps | Plasma Scoring: 1 z jednostek używających BOMBARDMENT rzuca 1 dodatkową kością. |
| `bombardment.forbidden_traits` | FORBID | agenda:conventions | agendas:conventions | — |
| `bombardment.granted_hits_on` | FORBID | effect:action_cards:blitz | — | — |
| `bombardment.ground_units` | FORBID | unit:l1z1x_mech | units:l1z1x_mech | Annihilator: While not participating in ground combat, this unit can use its BOMBARDMENT |
| `bombardment.ignores_planetary_shield` | PERMIT | leader:l1z1xcommander | leaders:l1z1xcommander | 2RAM: At any time: Units that have PLANETARY SHIELD do not prevent you from using |
| `bombardment.roll_modifier` | MODIFY | effect:action_cards:bunker | — | — |
| `breakthrough.fracture_no_roll` | PERMIT | breakthrough:cabalbt | breakthroughs:cabalbt | Al'raith Ix Ianovar: This breakthrough causes The Fracture to enter play without a roll, |
| `capture.destroyed` | PERMIT | faction:cabal | abilities:devour | Devour: Capture your opponent's non-structure units that are destroyed during combat. |
| `capture.destroyed` | PERMIT | unit:cabal_flagship | units:cabal_flagship | The Terror Between: Capture all other non-structure units that are destroyed in this |
| `capture.destroyed` | PERMIT | unit:cabal_mech | units:cabal_mech | Reanimator: When your infantry on this planet are destroyed, place them on your faction |
| `combat.ability_hit_immune` | FORBID | unit:naaz_voltron | — | It cannot be assigned hits from unit abilities (trafienia na inne jednostki - 2). |
| `combat.afb_all_ships` | PERMIT | effect:action_cards:waylay | — | — |
| `combat.afb_extra_dice` | MODIFY | leader:argentcommander | leaders:argentcommander | — |
| `combat.afb_extra_dice` | MODIFY | effect:promissory_notes:ambuscade:die | — | — |
| `combat.afb_granted` | FORBID | relic:metalivoidarmaments | relics:metalivoidarmaments | — |
| `combat.afb_infantry_kill` | FORBID | technology:swa2 | technologies:swa2 | Strike Wing Alpha II: When this unit uses ANTI-FIGHTER BARRAGE, each result of 9 or 10 also |
| `combat.afb_raid` | PERMIT | faction:argent | abilities:raid_formation | Raid Formation: When 1 or more of your units uses ANTI-FIGHTER BARRAGE: for each hit |
| `combat.bonus_dice` | MODIFY | effect:leaders:letnevagent:die | — | — |
| `combat.bonus_dice` | MODIFY | effect:leaders:solagent:die | — | — |
| `combat.champion` | FORBID | effect:promissory_notes:cavalry:ship | promissory_notes:cavalry | — |
| `combat.extra_dice` | MODIFY | unit:naaz_flagship | units:naaz_flagship | Visz El Vir: Your mechs in this system roll 1 additional die during combat (każdy mech, |
| `combat.extra_dice` | MODIFY | unit:winnu_flagship | units:winnu_flagship | Salai Sai Corian: When this unit makes a combat roll, it rolls a number of dice (hit on a 7) |
| `combat.extra_hits` | MODIFY | technology:vpw | technologies:vpw | Valkyrie Particle Weave: After making combat rolls during a round of ground combat, if your |
| `combat.granted_sustain` | PERMIT | relic:metalivoidshielding | relics:metalivoidshielding | Metali Void Shielding: Each time hits are produced against 1 or more of your non-fighter |
| `combat.hit_multiplier` | MODIFY | technology:x89c4 | technologies:x89c4 | X-89 ΩΩ: podwaja trafienia z bombardowania i z rzutów w walce NAZIEMNEJ. |
| `combat.hit_shields` | FORBID | unit:nomad_mech | units:nomad_mech | Quantum Manipulator: While this unit is in a space area during combat, you may use its |
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
| `combat.roll_modifier` | MODIFY | effect:technologies:sc | — | +1 tylko do rzutów walki - AFB, bombardowanie i Space Cannon mają własne punkty (1). |
| `combat.roll_modifier` | MODIFY | breakthrough:winnubt | breakthroughs:winnubt | Imperator: Apply +1 to the results of each of your unit's combat rolls for each "Support for |
| `combat.roll_modifier` | MODIFY | leader:winnucommander | leaders:winnucommander | Rickar Rickani: Apply +2 to the result of each of your unit's combat rolls in the Mecatol Rex |
| `combat.single_unit_bonus` | MODIFY | effect:breakthroughs:letnevbt:ship | — | — |
| `combat.space_ground_variant` | FORBID | unit:naaz_mech | units:naaz_mech_space | Z-Grav Eidolon: If this unit is in the space area of the active system, it is also a ship |
| `combat.space_ground_variant` | FORBID | unit:naaz_voltron | breakthroughs:naazbt | Eidolon Maximum: This unit is both a ship and ground force (w przestrzeni - statek). |
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
| `event:agenda.outcome_resolved:after` | TRIGGER | faction:nomad | abilities:future_sight | Future Sight: During the Agenda phase, after an outcome that you voted for or predicted is |
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
| `event:agenda.votes_cast:after` | TRIGGER | promissory:blood_pact | promissory_notes:blood_pact | Blood Pact: When you and the Empyrean player cast votes for the same outcome, cast 4 |
| `event:cards.action_drawn:after` | TRIGGER | faction:yssaril | abilities:scheming | Scheming: When you draw 1 or more action cards: Draw 1 additional action card. Then, choose |
| `event:cards.action_drawn:after` | TRIGGER | breakthrough:yssarilbt | breakthroughs:yssarilbt | Deepgloom Executable: You can allow other players to use your ... SCHEMING faction |
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
| `event:combat.round:start` | TRIGGER | unit:naaz_voltron | — | Repair it at the start of every combat round. |
| `event:combat.round:start` | TRIGGER | technology:sc | technologies:sc | Supercharge: At the start of a combat round, you may exhaust this card to apply +1 to the |
| `event:combat.round:start` | TRIGGER | leader:solagent | leaders:solagent | Evelyn DeLouis: At the start of a ground combat round: You may exhaust this card to choose 1 |
| `event:combat.step:start` | TRIGGER | effect:breakthroughs:letnevbt:ship | — | F_letnev gravleash-maneuvers 8: after The Thundarian the Letnev player may assign the bonus |
| `event:combat.won:after` | TRIGGER | technology:dxa | technologies:dxa | Dacxive Animators: po wygranej walce naziemnej możesz postawić 1 piechotę na tej planecie. |
| `event:combat.won:after` | TRIGGER | leader:mentakcommander | leaders:mentakcommander | S'ula Mentarion: After you win a space combat: You may force your opponent to give you 1 |
| `event:combat.won:after` | TRIGGER | breakthrough:sardakkbt | breakthroughs:sardakkbt | N'orr Supremacy: After you win a combat, either gain 1 command token or research a unit |
| `event:combat.won:after` | TRIGGER | technology:so | technologies:so | Salvage Operations: ... if you won the combat, you may also produce 1 ship in that system of |
| `event:combat:end` | TRIGGER | unit:naalu_flagship | — | After combat, return those units to the space area (tylko z planety tej walki; reszta - |
| `event:combat:end` | TRIGGER | unit:naaz_mech | units:naaz_mech_space | Z-Grav Eidolon: At the end of a space battle in the active system, flip this card (mechy |
| `event:combat:end` | TRIGGER | effect:promissory_notes:cavalry:ship | — | Return this card to the Nomad player at the end of the combat (also after a retreat). |
| `event:combat:end` | TRIGGER | unit:saar_spacedock | — | If this unit is blockaded, it is destroyed. |
| `event:combat:end` | TRIGGER | unit:saar_spacedock2 | — | If this unit is blockaded, it is destroyed. |
| `event:combat:end` | TRIGGER | technology:so | technologies:so | Salvage Operations: After you win or lose a space combat, gain 1 trade good (remis = nic, |
| `event:combat:start` | TRIGGER | technology:asc | technologies:asc | Assault Cannon: na początku walki kosmicznej przeciwnik niszczy 1 swój statek niemyśliwski. |
| `event:combat:start` | TRIGGER | technology:ds | technologies:ds | Dimensional Splicer: At the start of space combat in a system that contains a wormhole and 1 |
| `event:combat:start` | TRIGGER | technology:ic | technologies:ic | Impulse Core: At the start of a space combat, you may destroy 1 of your cruisers or |
| `event:combat:start` | TRIGGER | technology:md | technologies:md | Magen Defense Grid ΩΩ: na początku walki naziemnej na planecie z Twoją strukturą |
| `event:combat:start` | TRIGGER | faction:mentak | abilities:ambush | Ambush: At the start of a space combat: You may roll 1 die for each of up to 2 of your |
| `event:combat:start` | TRIGGER | leader:mentakhero | leaders:mentakhero | Ipswitch, Loose Cannon — Sleeper Cell: At the start of a space combat that you are |
| `event:combat:start` | TRIGGER | relic:metalivoidarmaments | — | Metali Void Armaments: During the "Anti-Fighter Barrage" step of space combat, you may |
| `event:combat:start` | TRIGGER | unit:naaz_mech | units:naaz_mech | Eidolon: If this unit is in the space area of the active system at the start of a space |
| `event:combat:start` | TRIGGER | leader:solcommander | leaders:solcommander | Claire Gibson: At the start of a ground combat on a planet you control: You may place 1 |
| `event:combat:start` | TRIGGER | faction:yin | abilities:indoctrination | Indoctrination: At the start of a ground combat: You may spend 2 influence to replace 1 of |
| `event:component.action:after` | TRIGGER | agenda:minister_war | agendas:minister_war | — |
| `event:component.decision:after` | TRIGGER | rule:entropic_scar | — | Statki w drugiej bliźnie: druga technologia za drugi żeton (R_entropic_scars 5.3). |
| `event:component.decision:after` | TRIGGER | effect:research:divert_funding | action_cards:divert_funding | — |
| `event:component.decision:after` | TRIGGER | effect:research:enigmatic_device | explores:ed1 | — |
| `event:component.decision:after` | TRIGGER | effect:research:f_researched | action_cards:f_researched | — |
| `event:component.decision:after` | TRIGGER | effect:research:reveal_prototype | action_cards:reveal_prototype | — |
| `event:component.exhausted:after` | TRIGGER | leader:empyreanagent | — | — |
| `event:component.exhausted:after` | TRIGGER | leader:nomadagentmercer | — | The player Mercer helped moves up to 2 ground forces onto planets they control in the |
| `event:component.exhausted:after` | TRIGGER | leader:sardakkagent | — | — |
| `event:component.exhausted:after` | TRIGGER | technology:tcs | technologies:tcs | Temporal Command Suite: After any player's agent becomes exhausted, you may exhaust this |
| `event:component.gained:when` | TRIGGER | relic:bookoflatvinia | — | Book of Latvinia: When you gain this card, research up to 2 technologies that have no |
| `event:component.gained:when` | TRIGGER | breakthrough:cabalbt | breakthroughs:cabalbt | After this card enters play, move up to 2 ingress tokens into systems that contain gravity |
| `event:component.gained:when` | TRIGGER | breakthrough:muaatbt | breakthroughs:muaatbt | Stellar Genesis: When you gain this card, place the Avernus planet token into a non-home |
| `event:component.gained:when` | TRIGGER | unit:naalu_mech_te | units:naalu_mech_te | Iconoclast TE: DEPLOY: When another player gains a relic, place 1 mech on any planet you |
| `event:component.gained:when` | TRIGGER | leader:naalucommander | — | Talia agend powstaje leniwie - przy odblokowaniu M'aban zasiewamy ją, żeby podgląd |
| `event:component.gained:when` | TRIGGER | relic:obsidian | relics:obsidian | The Obsidian: When you gain this card, draw 1 secret objective. |
| `event:component.gained:when` | TRIGGER | relic:quantumcore | relics:quantumcore | The Quantumcore: When you gain this card, gain your breakthrough. |
| `event:component.gained:when` | TRIGGER | relic:shard | — | Shard of the Throne: When you gain this card, gain 1 victory point. |
| `event:component.gained:when` | TRIGGER | breakthrough:yinbt | breakthroughs:yinbt | Yin Ascendant: When you gain this card ..., gain the alliance ability of a random, unused |
| `event:component.readied:after` | TRIGGER | leader:nomadagentartuno | leaders:nomadagentartuno | When this card readies, gain the trade goods on this card (not from the supply - 3). |
| `event:component.readied:when` | TRIGGER | effect:agendas:checks:against | agendas:checks | — |
| `event:economy.commodities_given:after` | TRIGGER | promissory:dark_pact | promissory_notes:dark_pact | Dark Pact: When you give a number of commodities to the Empyrean player equal to your maximum |
| `event:economy.commodities_replenished:after` | TRIGGER | leader:cabalagent | leaders:cabalagent | The Stillness of Stars: After another player replenishes commodities: You may exhaust this |
| `event:economy.commodities_replenished:after` | TRIGGER | agenda:minister_commerce | agendas:minister_commerce | — |
| `event:economy.trade_goods_gained:after` | TRIGGER | faction:mentak | abilities:pillage | Pillage: After 1 of your neighbors gains trade goods ... |
| `event:economy.trade_goods_gained:after` | TRIGGER | leader:nomadagentartuno | leaders:nomadagentartuno | Artuno the Betrayer: When you gain trade goods from the supply: You may exhaust this card to |
| `event:faction.ability_used:after` | TRIGGER | effect:agendas:redistribution:place | agendas:redistribution | — |
| `event:faction.ability_used:after` | TRIGGER | faction:arborec | — | — |
| `event:faction.ability_used:after` | TRIGGER | leader:arborecagent | leaders:arborecagent | Zamieniany statek nie jest niszczony, nowy nie jest produkowany (F_arborec). |
| `event:faction.ability_used:after` | TRIGGER | faction:argent | abilities:raid_formation | Argent wybiera statki do uszkodzenia (wybrany uszkodzony statek - bez skutku, F_argent). |
| `event:faction.ability_used:after` | TRIGGER | leader:argentagent | — | Gracz produkujący przenosi wyprodukowane siły naziemne na swoje planety (0 = zostają). |
| `event:faction.ability_used:after` | TRIGGER | leader:jolnaragent | leaders:jolnaragent | — |
| `event:faction.ability_used:after` | TRIGGER | leader:l1z1xagent | — | Aktywny gracz wymienia 1 piechotę na mecha (mech zdjęty z planszy - nieuszkodzony, F_lizix |
| `event:faction.ability_used:after` | TRIGGER | effect:leaders:naazagent:explore | — | Gracz, któremu Garv and Gunn pozwolili, eksploruje 1 swoją planetę z cechą. |
| `event:faction.ability_used:after` | TRIGGER | effect:leaders:yinagent:dual | — | Właściciel zniszczonej jednostki-statku-i-siły-naziemnej stawia 2 myśliwce albo 2 piechotę. |
| `event:faction.ability_used:after` | TRIGGER | leader:mentakagent | leaders:mentakagent | Suffi An: After the Pillage faction ability is used against another player: You may exhaust |
| `event:faction.ability_used:after` | TRIGGER | leader:mentakcommander | — | Przeciwnik oddaje wybraną notkę z ręki (decyzja obowiązkowa przeciwnika). |
| `event:faction.ability_used:after` | TRIGGER | unit:muaat_mech | units:muaat_mech | Ember Colossus: When you use your Star Forge faction ability in this system or an adjacent |
| `event:faction.ability_used:after` | TRIGGER | leader:muaatagent | — | Wybrany gracz otwiera produkcję: grant ``free`` (bez PRODUCTION jednostek - F_muaat umbat |
| `event:faction.ability_used:after` | TRIGGER | faction:naalu | — | — |
| `event:faction.ability_used:after` | TRIGGER | breakthrough:saarbt | — | Saar przypisuje trafienia; jednostki z Sustain Damage - decyzja ich właściciela (3). |
| `event:faction.ability_used:after` | TRIGGER | breakthrough:saarbt | — | Właściciel trafionej jednostki decyduje o Sustain Damage (F_saar deorbit 3). |
| `event:faction.ability_used:after` | TRIGGER | unit:sol_mech | units:sol_mech | ZS Thunderbolt M2 — DEPLOY: After you use your Orbital Drop faction ability, you may spend |
| `event:faction.ability_used:after` | TRIGGER | breakthrough:titansbt | breakthroughs:titansbt | — |
| `event:faction.ability_used:after` | TRIGGER | faction:yin | unlocks:yincommander | Unlock: Use one of your faction abilities (Indoctrination albo Devotion - F_yin Ω). |
| `event:faction.ability_used:after` | TRIGGER | faction:yssaril | — | The mandatory discard - nothing else resolves until it is made (scheming 4). |
| `event:faction.ability_used:after` | TRIGGER | faction:yssaril | — | The Yssaril takes the chosen card (they may not show the hand to anyone - mi 2). |
| `event:faction.ability_used:after` | TRIGGER | faction:yssaril | — | — |
| `event:faction.ability_used:after` | TRIGGER | faction:yssaril | — | — |
| `event:faction.ability_used:after` | TRIGGER | faction:yssaril | — | — |
| `event:faction.ability_used:after` | TRIGGER | unit:yssaril_mech | units:yssaril_mech | Blackshade Infiltrator: DEPLOY: After you use your Stall Tactics faction ability, you may |
| `event:faction.ability_used:after` | TRIGGER | breakthrough:yssarilbt | — | The allowed player uses Scheming; when they do, they may make a transaction with the |
| `event:faction.ability_used:after` | TRIGGER | leader:yssarilcommander | — | Looking changes nothing; the decision only shows the cards to the Yssaril. |
| `event:fracture.ingress_placed:after` | TRIGGER | breakthrough:cabalbt | breakthroughs:cabalbt | Oferta zaraz po rozłożeniu ingressów (ruling 1.2) - wykonuje :func:`move_ingress`. |
| `event:objective.revealed:after` | TRIGGER | relic:neuraloop | relics:neuraloop | Neuraloop: When a public objective is revealed, you may purge one of your relics to discard |
| `event:objective.scored:after` | TRIGGER | breakthrough:yinbt | breakthroughs:yinbt | Yin Ascendant: ... or score a public objective, gain the alliance ability of a random, |
| `event:phase:end` | TRIGGER | technology:bio | technologies:bio | Bioplasmosis: At the end of the status phase, you may remove any number of infantry from |
| `event:phase:end` | TRIGGER | relic:emphidia | relics:emphidia | The Crown of Emphidia: At the end of the status phase, if you control the "Tomb of |
| `event:phase:end` | TRIGGER | promissory:gift | promissory_notes:gift | Return this card to the Naalu player at the end of the status phase. |
| `event:phase:end` | TRIGGER | agenda:minister_policy | agendas:minister_policy | — |
| `event:phase:end` | TRIGGER | faction:naalu | abilities:telepathic | Telepathic: At the end of the strategy phase: Place the Naalu "0" token on your strategy |
| `event:phase:end` | TRIGGER | leader:naaluhero | leaders:naaluhero | The Oracle — C-Radium Geometry: At the end of the status phase: You may force each other |
| `event:phase:end` | TRIGGER | technology:qdn | technologies:qdn | Quantum Datahub Node: At the end of the strategy phase, you may spend 1 token from your |
| `event:phase:end` | TRIGGER | unit:sol_flagship | units:sol_flagship | Genesis: At the end of the status phase, place 1 infantry from your reinforcements in this |
| `event:phase:start` | TRIGGER | effect:agendas:arms_reduction:against | agendas:arms_reduction | — |
| `event:phase:start` | TRIGGER | effect:agendas:constitution:for | agendas:constitution | — |
| `event:phase:start` | TRIGGER | effect:agendas:rep_govt:against | agendas:rep_govt | — |
| `event:phase:start` | TRIGGER | effect:agendas:revolution:against | agendas:revolution | — |
| `event:phase:start` | TRIGGER | faction:arborec | abilities:mitosis | Mitosis: At the start of the status phase: Place 1 infantry from your reinforcements on any |
| `event:phase:start` | TRIGGER | technology:cm | — | Chaos Mapping: At the start of your turn during the action phase, you may produce 1 unit |
| `event:phase:start` | TRIGGER | rule:entropic_scar | — | Statki w bliźnie: żeton z puli strategii -> technologia frakcyjna (R_entropic_scars 5). |
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
| `event:planet.control_gained:after` | TRIGGER | leader:naazcommander | leaders:naazcommander | Dart and Tai: After you gain control of a planet that was controlled by another player: You |
| `event:planet.control_gained:after` | TRIGGER | faction:saar | abilities:scavenge | Scavenge: After you gain control of a planet: Gain 1 trade good. |
| `event:planet.control_gained:after` | TRIGGER | unit:saar_mech | units:saar_mech | Scavenger Zeta — DEPLOY: After you gain control of a planet, you may spend 1 trade good to |
| `event:planet.control_gained:after` | TRIGGER | unit:saar_mech | — | Planeta niczyja: DEPLOY dopiero po eksploracji (F_saar zeta 2). |
| `event:planet.control_gained:after` | TRIGGER | relic:shard | relics:shard | Shard of the Throne: When a player gains control of a legendary planet you control or a |
| `event:planet.control_gained:after` | TRIGGER | planet:styx | planets:styx | A Song Like Marrow: When you gain this card, gain 1 victory point. |
| `event:planet.control_gained:after` | TRIGGER | planet:thundersedge | planets:thundersedge | Jupiter Brain: Gain your breakthrough when you gain this card if you do not already have |
| `event:planet.control_lost:when` | TRIGGER | planet:styx | planets:styx | A Song Like Marrow: When you lose this card, lose 1 victory point. |
| `event:planet.explored:after` | TRIGGER | effect:abilities:scavenge:after_explore | — | TG ze Scavenge po eksploracji zdobytej planety (F_saar scavenge 2). |
| `event:planet.explored:after` | TRIGGER | effect:breakthroughs:l1z1xbt:after_explore | — | Piechota Fealty Uplink postawiona po eksploracji planety (wybór gracza, F_lizix 1). |
| `event:planet.explored:after` | TRIGGER | technology:pfa | technologies:pfa | Pre-Fab Arcologies: After you explore a planet, ready that planet (po produkcji |
| `event:planet.explored:after` | TRIGGER | faction:titans | abilities:terragenesis | Terragenesis: After you explore a planet that does not have a sleeper token: You may place |
| `event:planet.explored:after` | TRIGGER | effect:units:saar_mech:after_explore | — | — |
| `event:player.passed:when` | TRIGGER | planet:faunus | planets:faunus | Maxis Central Control: You may exhaust this card when you pass to gain control of a non-home, non-legendary planet that contains no units and has no attachments. |
| `event:player.passed:when` | TRIGGER | planet:garbozia | planets:garbozia | Dok 'N Pic's Salvage Yard: You may exhaust this card when you pass to place 1 action card from the discard pile faceup on this card. |
| `event:player.passed:when` | TRIGGER | planet:industrex | planets:industrex | Aeurex Mechanica: You may exhaust this card when you pass to place 1 ship that matches a unit upgrade technology you own from your reinforcements into a system that contains your ships. |
| `event:player.passed:when` | TRIGGER | planet:ordinian | planets:ordinian | Hyperion: You may exhaust this card when you pass to draw 1 action card and gain 1 command token. |
| `event:player.passed:when` | TRIGGER | planet:ordinianc4 | planets:ordinianc4 | Hyperion: You may exhaust this card when you pass to draw 1 action card and gain 1 command token. |
| `event:production.units_produced:after` | TRIGGER | leader:argentagent | leaders:argentagent | Trilossa Aun Mirik: When a player produces ground forces in a system: You may exhaust this |
| `event:production.units_produced:after` | TRIGGER | breakthrough:hacanbt | breakthroughs:hacanbt | Auto-Factories: When you produce 3 or more non-fighter ships, place 1 command token from your |
| `event:production.units_produced:after` | TRIGGER | faction:muaat | unlocks:muaatcommander | Unlock: Produce a war sun. |
| `event:production.units_produced:after` | TRIGGER | leader:saarcommander | leaders:saarcommander | Rowl Sarrig: When you produce fighters or infantry: You may place each of those units at |
| `event:production.units_produced:after` | TRIGGER | technology:yso | technologies:yso | Yin Spinner Ω: After you produce units, place up to 2 infantry from your reinforcements on |
| `event:production.used:after` | TRIGGER | agenda:prophecy | agendas:prophecy | — |
| `event:production.used:after` | TRIGGER | technology:sar | technologies:sar | Self-Assembly Routines: po PRODUCTION wyczerp kartę, by postawić 1 mecha z rezerwy |
| `event:strategy.action:after` | TRIGGER | agenda:minister_war | agendas:minister_war | — |
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
| `event:tactical.ships_moved:after` | TRIGGER | leader:empyreanagent | leaders:empyreanagent | Acamar: After a player moves ships into a system that does not contain any planets: You may |
| `event:tactical.ships_moved:after` | TRIGGER | leader:empyreancommander | leaders:empyreancommander | Xuange: After another player moves ships into a system that contains 1 of your command |
| `event:tactical.ships_moved:after` | TRIGGER | leader:ghostcommander | leaders:ghostcommander | Sai Seravus: After your ships move: For each ship that has a capacity value and moved through |
| `event:tactical.ships_moved:after` | TRIGGER | effect:leaders:saaragent | — | Wybrany statek ruszył - premia dotyczy tylko jego (1 statek). |
| `event:tactical.ships_moved:after` | TRIGGER | breakthrough:muaatbt | breakthroughs:muaatbt | After you move one of your war suns out of or through Avernus's system and into a non-home |
| `event:tactical.ships_moved:after` | TRIGGER | leader:muaathero | leaders:muaathero | Adjudicator Ba'al — Nova Seed: After you move a war sun into a non-home system other than |
| `event:tactical.ships_moved:after` | TRIGGER | faction:naalu | abilities:foresight | Foresight: After another player moves ships into a system that contains 1 or more of your |
| `event:tactical.ships_moved:after` | TRIGGER | unit:saar_spacedock | — | If this unit is blockaded, it is destroyed. |
| `event:tactical.ships_moved:after` | TRIGGER | unit:saar_spacedock2 | — | If this unit is blockaded, it is destroyed. |
| `event:tactical.ships_moved:after` | TRIGGER | technology:vw | technologies:vw | Voidwatch: After a player moves ships into a system that contains 1 or more of your units, |
| `event:tactical.system_activated:after` | TRIGGER | promissory:<color>_an | promissory_notes:<color>_an | — |
| `event:tactical.system_activated:after` | TRIGGER | promissory:<color>_sftt | promissory_notes:<color>_sftt | — |
| `event:tactical.system_activated:after` | TRIGGER | unit:arborec_flagship | units:arborec_flagship | Duha Menaimon: After you activate this system, you may produce up to 5 units in this |
| `event:tactical.system_activated:after` | TRIGGER | leader:arboreccommander | leaders:arboreccommander | Dirzuga Rophal: After another player activates a system that contains 1 or more of your |
| `event:tactical.system_activated:after` | TRIGGER | breakthrough:argentbt | breakthroughs:argentbt | Wing Transfer: When you activate a system that contains only your units, you may place |
| `event:tactical.system_activated:after` | TRIGGER | technology:as | technologies:as | Aetherstream: After you or one of your neighbors activates a system that is adjacent to an |
| `event:tactical.system_activated:after` | TRIGGER | promissory:blood_pact | promissory_notes:blood_pact | If you activate a system that contains 1 or more of the Empyrean player's units, return this |
| `event:tactical.system_activated:after` | TRIGGER | promissory:convoys | promissory_notes:convoys | If you activate a system that contains 1 or more of the Hacan player's units, return this |
| `event:tactical.system_activated:after` | TRIGGER | promissory:dark_pact | promissory_notes:dark_pact | If you activate a system that contains 1 or more of the Empyrean player's units, return this |
| `event:tactical.system_activated:after` | TRIGGER | relic:dominusorb | relics:dominusorb | Dominus Orb: Before you move units during a tactical action, you may purge this card to |
| `event:tactical.system_activated:after` | TRIGGER | faction:empyrean | abilities:aetherpassage | Aetherpassage: After a player activates a system: You may allow that player to move their |
| `event:tactical.system_activated:after` | TRIGGER | breakthrough:empyreanbt | breakthroughs:empyreanbt | Void Tether: When you activate a system that contains or is adjacent to a unit or planet you |
| `event:tactical.system_activated:after` | TRIGGER | breakthrough:empyreanbt | breakthroughs:empyreanbt | ...other players do not treat those systems as adjacent to each other unless you allow it. |
| `event:tactical.system_activated:after` | TRIGGER | technology:ers | technologies:ers | E-Res Siphons: After another player activates a system that contains 1 or more of your |
| `event:tactical.system_activated:after` | TRIGGER | unit:ghost_mech | units:ghost_mech | Icarus Drive: After any player activates a system, you may remove this unit from the game |
| `event:tactical.system_activated:after` | TRIGGER | leader:ghostagent | leaders:ghostagent | Emissary Taivra: After a player activates a system that contains a non-delta wormhole: You |
| `event:tactical.system_activated:after` | TRIGGER | leader:l1z1xagent | leaders:l1z1xagent | I48S: After a player activates a system: You may exhaust this card to allow that player to |
| `event:tactical.system_activated:after` | TRIGGER | agenda:minister_peace | agendas:minister_peace | — |
| `event:tactical.system_activated:after` | TRIGGER | technology:nf | technologies:nf | Nullification Field: After another player activates a system that contains 1 or more of your |
| `event:tactical.system_activated:after` | TRIGGER | technology:ng | technologies:ng | Neuroglaive: After another player activates a system that contains 1 or more of your ships, |
| `event:tactical.system_activated:after` | TRIGGER | promissory:pop | promissory_notes:pop | If you activate a system that contains 1 or more of the Mentak player's units, return this |
| `event:tactical.system_activated:after` | TRIGGER | leader:saaragent | leaders:saaragent | Captain Mendosa: When a player activates a system: You may exhaust this card to increase |
| `event:tactical.system_activated:after` | TRIGGER | technology:scc | technologies:scc | Spatial Conduit Cylinder: You may exhaust this card after you activate a system that |
| `event:tactical.system_activated:after` | TRIGGER | technology:sdn | technologies:sdn | Scanlink Drone Network: przy aktywacji systemu możesz zbadać 1 planetę z Twoimi |
| `event:tactical.system_activated:after` | TRIGGER | planet:tempesta | planets:tempesta | Ionian Fuel Refinery: You may exhaust this card after you activate a system to apply +1 to the move value of 1 of your ships during this tactical action. |
| `event:tactical.system_activated:after` | TRIGGER | faction:titans | abilities:awaken | Awaken: After you activate a system that contains 1 or more of your sleeper tokens: You may |
| `event:tactical.system_activated:after` | TRIGGER | unit:titans_flagship | units:titans_flagship | Ouranos: DEPLOY: After you activate a system that contains 1 or more of your PDS, you may |
| `event:tactical.system_activated:after` | TRIGGER | leader:yssarilcommander | leaders:yssarilcommander | So Ata: After another player activates a system that contains your units: You may look at |
| `event:tactical.system_activated:when` | TRIGGER | technology:md | technologies:md | Magen Defense Grid ΩΩ: aktywacja systemu z Twoimi strukturami → 1 piechota przy każdej. |
| `event:tactical.system_activated:when` | TRIGGER | faction:titans | — | Migawka chwili aktywacji: żetony sleeper i PDS gracza w systemie. Awaken i Ouranos |
| `event:tactical.units_committed:after` | TRIGGER | effect:leaders:sardakkhero | — | — |
| `event:technology.research:after` | TRIGGER | agenda:revolution | agendas:revolution | — |
| `event:technology.research:when` | TRIGGER | relic:prophetstears | relics:prophetstears | The Prophet's Tears: When you research a technology, you may exhaust this card to ignore 1 |
| `event:tokens.placed:after` | TRIGGER | leader:naaluagent-te | leaders:naaluagent-te | Z'eu: After any player's command token is placed in a system: You may exhaust this card to |
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
| `event:turn:end` | TRIGGER | leader:naazagent | leaders:naazagent | Garv and Gunn: At the end of a player's turn: You may exhaust this card to allow that player |
| `event:turn:end` | TRIGGER | leader:nomadagentmercer | leaders:nomadagentmercer | Field Marshal Mercer: At the end of a player's turn: You may exhaust this card to allow that |
| `event:turn:end` | TRIGGER | planet:phantasm | planets:phantasm | Flight Academy: You may exhaust this card at the end of your turn to place up to 2 fighters from your reinforcements in any system that contains 1 or more of your ships. |
| `event:turn:end` | TRIGGER | technology:pi | technologies:pi | Predictive Intelligence: na końcu tury wyczerp kartę, by przerozdzielić żetony dowodzenia. |
| `event:turn:end` | TRIGGER | planet:primor | planets:primor | The Atrament: You may exhaust this card at the end of your turn to place up to 2 infantry from your reinforcements on any planet you control. |
| `event:turn:end` | TRIGGER | planet:thundersedge | planets:thundersedge | Jupiter Brain: You may exhaust this card at the end of your turn to perform another action. |
| `event:turn:start` | TRIGGER | technology:cm | technologies:cm | Chaos Mapping: At the start of your turn during the action phase, you may produce 1 unit |
| `event:turn:start` | TRIGGER | technology:inf2 | technologies:inf2 | Każda piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:turn:start` | TRIGGER | technology:inf2 | technologies:inf2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:turn:start` | TRIGGER | technology:lw2 | technologies:lw2 | Każda piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:turn:start` | TRIGGER | technology:lw2 | technologies:lw2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:turn:start` | TRIGGER | breakthrough:nomadbt | breakthroughs:nomadbt | Thunder's Paradox: At the start of any player's turn, you may exhaust 1 of your agents to |
| `event:turn:start` | TRIGGER | technology:so2 | technologies:so2 | Każda piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:turn:start` | TRIGGER | technology:so2 | technologies:so2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:turn:start` | TRIGGER | technology:td | — | Transit Diodes: na początku Twojej tury w fazie akcji wyczerp kartę i przenieś do 4 sił |
| `event:unit.ability_used:after` | TRIGGER | leader:jolnarcommander | — | Agnlan Oln (AFB): walka czeka po rzucie AFB na tę ofertę (``battle.resolve_afb``). |
| `event:unit.ability_used:after` | TRIGGER | effect:promissory_notes:ambuscade:die | — | Po rzucie zdolności jednostki premia z notki przepada (jedna kość, jeden rzut). |
| `event:unit.ability_used:after` | TRIGGER | technology:x89c4 | technologies:x89c4 | X-89 ΩΩ: każda planeta, przeciw której użyto BOMBARDMENT, zostaje wyczerpana. |
| `event:unit.destroyed:after` | TRIGGER | technology:inf2 | technologies:inf2 | Infantry II / Spec Ops II: po zniszczeniu piechoty rzuć kością; przy progu+ jednostka |
| `event:unit.destroyed:after` | TRIGGER | effect:leaders:mentakhero:sleeper | leaders:mentakhero | F_mentak 7.1: po Direct Hit Mentaka statek tego typu staje od razu (może jeszcze w tej |
| `event:unit.destroyed:after` | TRIGGER | technology:lw2 | technologies:lw2 | Infantry II / Spec Ops II: po zniszczeniu piechoty rzuć kością; przy progu+ jednostka |
| `event:unit.destroyed:after` | TRIGGER | unit:naaz_voltron | — | When this unit is destroyed or removed, flip this card and return it to your play area. |
| `event:unit.destroyed:after` | TRIGGER | unit:saar_spacedock | — | If this unit is blockaded, it is destroyed. |
| `event:unit.destroyed:after` | TRIGGER | unit:saar_spacedock2 | — | If this unit is blockaded, it is destroyed. |
| `event:unit.destroyed:after` | TRIGGER | technology:sar | — | Self-Assembly Routines: po zniszczeniu Twojego mecha zdobywasz 1 TG (za każdego mecha; |
| `event:unit.destroyed:after` | TRIGGER | technology:so2 | technologies:so2 | Infantry II / Spec Ops II: po zniszczeniu piechoty rzuć kością; przy progu+ jednostka |
| `event:unit.destroyed:after` | TRIGGER | unit:yin_flagship | units:yin_flagship | Van Hauge: When this ship is destroyed, destroy all ships in this system. |
| `event:unit.destroyed:after` | TRIGGER | leader:yinagent | leaders:yinagent | Brother Milor Ω: After a player's unit is destroyed during combat: You may exhaust this card |
| `event:unit.placed:after` | TRIGGER | agenda:minister_industry | agendas:minister_industry | — |
| `event:unit.removed:after` | TRIGGER | effect:leaders:cabalhero:anchor | leaders:cabalhero | Dimensional Anchor: usunięte siły naziemne / myśliwce (nadwyżka ładunku) są przechwycone. |
| `event:unit.removed:after` | TRIGGER | unit:naaz_voltron | — | When this unit is destroyed or removed, flip this card and return it to your play area. |
| `event:unit.sustain_damage:after` | TRIGGER | unit:empyrean_flagship | units:empyrean_flagship | Dynamo: After any player's unit in this system or an adjacent system uses SUSTAIN DAMAGE, |
| `event:unit.sustain_damage:after` | TRIGGER | leader:letnevcommander | leaders:letnevcommander | Rear Admiral Farran: After 1 of your units uses SUSTAIN DAMAGE: You may gain 1 trade good |
| `event:unit.sustain_damage:after` | TRIGGER | unit:sardakk_mech | units:sardakk_mech | Valkyrie Exoskeleton: After this unit uses its SUSTAIN DAMAGE ability during ground combat, |
| `exploration.extra_draw` | PERMIT | faction:naaz | abilities:distant_suns | Distant Suns: When you explore a planet that contains 1 of your mechs: You may draw 1 |
| `fleet_pool.capacity` | MODIFY | faction:letnev | abilities:armada | Armada: The maximum number of non-fighter ships you can have in each system is equal to 2 |
| `fleet_pool.fighters_overflow` | PERMIT | technology:hcf2 | technologies:hcf2 | Hybrid Crystal Fighter II: This unit may move without being transported (Move z wariantu |
| `fleet_pool.fighters_per_ship` | MODIFY | technology:hcf2 | units:naalu_fighter2 | „count as 1/2 of a ship” - 2 myśliwce ponad pojemność = 1 statek puli floty. |
| `fleet_pool.token_cap` | MODIFY | agenda:regulations | agendas:regulations | — |
| `fleet_pool.unlimited` | PERMIT | effect:leaders:letnevhero | — | — |
| `hand_limit.action_cards` | MODIFY | agenda:sanctions | agendas:sanctions | — |
| `hand_limit.unlimited` | PERMIT | faction:yssaril | abilities:crafty | Crafty: You can have any number of action cards in your hand. Game effects cannot prevent |
| `info.peek` | FORBID | leader:naalucommander | leaders:naalucommander | M'aban: At any time: You may look at your neighbors' hands of promissory notes and the top |
| `invasion.commit_from_planets` | PERMIT | leader:sardakkcommander | — | F_norr: G'hom Sek'kus działa także bez statków w aktywnym systemie - inwazja otwiera |
| `invasion.ground_force_types` | FORBID | unit:naalu_flagship | units:naalu_flagship | Matriarch: During an invasion in this system, you may commit fighters to planets as if they |
| `invasion.skip_bombardment` | PERMIT | effect:leaders:sardakkhero | — | — |
| `invasion.strips_planetary_shield` | PERMIT | unit:letnev_flagship | units:letnev_flagship | Arc Secundus: Other player's units in this system lose PLANETARY SHIELD. |
| `limits.pds_unlimited` | PERMIT | agenda:defense_act | agendas:defense_act | — |
| `map.gravity_rifts` | FORBID | unit:cabal_spacedock | units:cabal_spacedock | Dimensional Tear: This system is a gravity rift; your ships do not roll for this gravity |
| `map.gravity_rifts` | FORBID | unit:cabal_spacedock2 | technologies:dt2 | Dimensional Tear: This system is a gravity rift; your ships do not roll for this gravity |
| `movement.alpha_beta_adjacent` | PERMIT | effect:action_cards:lost_star | — | — |
| `movement.alpha_beta_adjacent` | PERMIT | agenda:wormhole_recon | agendas:wormhole_recon | — |
| `movement.enter_asteroids` | PERMIT | technology:amd | technologies:amd | Antimass Deflectors: statki mogą wchodzić do pól asteroid i przez nie przechodzić. |
| `movement.enter_asteroids` | PERMIT | relic:circletofthevoid | — | Circlet of the Void: ruch przez/do pól asteroid (ignorowanie efektów anomalii). |
| `movement.extra_adjacent` | FORBID | effect:action_cards:lost_star | — | Systems with alpha / beta wormholes are adjacent to each other during this action. |
| `movement.extra_adjacent` | FORBID | effect:leaders:ghostagent:link | — | The linked system is adjacent to every other system with ANY wormhole (delta, epsilon, |
| `movement.extra_adjacent` | FORBID | technology:lgf | technologies:lgf | Lazax Gate Folding: During your tactical actions, if you do not control Mecatol Rex, treat |
| `movement.extra_adjacent` | FORBID | effect:technologies:scc | — | Aktywny system sąsiaduje ze wszystkimi systemami z jednostkami gracza (i odwrotnie). |
| `movement.ignore_anomalies` | PERMIT | effect:action_cards:nav_suite | — | — |
| `movement.ignore_anomalies_keep_rift` | PERMIT | relic:circletofthevoid | relics:circletofthevoid | Circlet of the Void: Your units do not roll for gravity rifts, and you ignore the effects |
| `movement.ignore_own_command_token` | PERMIT | effect:leaders:nomadhero:time_warp | — | Only the flagship (and the units it transports - the move passes it as the carrier). |
| `movement.ignore_own_command_token` | PERMIT | effect:relics:dominusorb | — | — |
| `movement.into_supernova` | PERMIT | technology:mr | technologies:mr | Magmus Reactor: Your ships can move into supernovas (cel ruchu i odwrót - R_space_combat). |
| `movement.match_highest` | PERMIT | breakthrough:letnevbt | — | Gravleash Maneuvers: During movement, your non-fighter ships' move values are equal to the |
| `movement.move_value` | MODIFY | effect:action_cards:fs1 | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs2 | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs3 | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs4 | — | — |
| `movement.move_value` | MODIFY | breakthrough:cabalbt | breakthroughs:cabalbt | Apply +1 to the MOVE value of each of your ships that start their movement in The |
| `movement.move_value` | MODIFY | technology:gd | technologies:gd | Gravity Drive: po aktywacji +1 do wartości ruchu JEDNEGO statku w tej akcji. |
| `movement.move_value` | MODIFY | faction:ghost | abilities:slipstream | Slipstream: During your tactical actions: Apply +1 to the move value of each of your ships |
| `movement.move_value` | MODIFY | effect:planets:tempesta | planets:tempesta | Ionian Fuel Refinery: +1 do wartości ruchu JEDNEGO statku w tej akcji taktycznej. |
| `movement.move_value` | MODIFY | effect:technologies:as:boost | — | — |
| `movement.move_value` | MODIFY | breakthrough:winnubt | — | After you activate a system that contains a legendary planet, apply +1 to the move value of 1 |
| `movement.moves_separately` | PERMIT | unit:ghost_flagship | units:ghost_flagship | During movement, this ship may move before or after your other ships (separate fleet move; |
| `movement.nebula_ignored` | PERMIT | faction:empyrean | abilities:voidborn | Voidborn: a ship starting in a nebula keeps its move value (also outside the Movement step |
| `movement.pass_foreign_ships` | PERMIT | effect:abilities:aetherpassage:allowed | — | Only the granting Empyrean player's ships may be flown through (another rival's still |
| `movement.pass_foreign_ships` | PERMIT | effect:action_cards:silence_space | — | Przelot przez obce statki dotyczy tylko statków startujących z wybranego systemu. |
| `movement.pass_foreign_ships` | PERMIT | technology:lwd | technologies:lwd | Light/Wave Deflector: statki mogą przechodzić przez systemy z cudzymi statkami. |
| `movement.pass_foreign_ships` | PERMIT | unit:mentak_cruiser3 | units:mentak_cruiser3 | Corsair: If the active system contains another player's non-fighter ships, this unit can |
| `movement.pass_foreign_ships` | PERMIT | unit:yssaril_flagship | units:yssaril_flagship | Y'sia Y'ssrila: This ship can move through systems that contain other player's ships |
| `movement.passage_blocked` | PERMIT | technology:ah | technologies:ah | Aerie Hololattice: Other players cannot move ships through systems that contain your |
| `movement.rift_extra_bonus` | PERMIT | effect:promissory_notes:crucible | — | — |
| `movement.rift_no_roll` | FORBID | unit:cabal_spacedock | units:cabal_spacedock | Dimensional Tear: This system is a gravity rift; your ships do not roll for this gravity |
| `movement.rift_no_roll` | FORBID | unit:cabal_spacedock2 | technologies:dt2 | Dimensional Tear: This system is a gravity rift; your ships do not roll for this gravity |
| `movement.single_ship_value` | MODIFY | effect:leaders:saaragent | — | Wartość ruchu wybranego statku (punkt ``movement.single_ship_value``). |
| `movement.through_nebula` | PERMIT | faction:empyrean | abilities:voidborn | Voidborn: Nebulae do not affect your ships' movement (a nebula may be crossed). |
| `movement.through_nebula` | PERMIT | agenda:shared_research | agendas:shared_research | — |
| `movement.through_supernova` | PERMIT | faction:muaat | abilities:gashlai_physiology | Gashlai Physiology: Your ships can move through supernovas (węzeł pośredni trasy). |
| `movement.unit_extra_adjacent` | FORBID | unit:nomad_flagship | units:nomad_flagship | You may treat this unit as if it were adjacent to systems that contain 1 or more of your |
| `movement.unit_extra_adjacent` | FORBID | unit:nomad_flagship2 | units:nomad_flagship2 | You may treat this unit as if it were adjacent to systems that contain 1 or more of your |
| `movement.wormhole_laws_immune` | PERMIT | faction:ghost | abilities:quantum_entanglement | Game effects cannot prevent you from using this ability (Enforced Travel Ban, Nexus |
| `movement.wormholes_blocked` | FORBID | agenda:nexus | agendas:nexus | — |
| `movement.wormholes_blocked` | FORBID | agenda:travel_ban | agendas:travel_ban | — |
| `objectives.ignore_home_control` | PERMIT | faction:saar | abilities:nomadic | Nomadic: You can score objectives even if you do not control the planets in your home |
| `objectives.secret_limit` | MODIFY | relic:obsidian | relics:obsidian | The Obsidian: You can have 1 additional scored or unscored secret objective. |
| `payment.flex_spend` | PERMIT | breakthrough:xxchabt | breakthroughs:xxchabt | Archon's Gift: You can spend influence as if it were resources. You can spend resources as if |
| `payment.trade_good_value` | MODIFY | technology:mc | technologies:mc | Mirror Computing: When you spend trade goods, each trade good is worth 2 resources or |
| `planet.swap_values` | FORBID | effect:technologies:htp:swap | — | — |
| `production.captured_free` | PERMIT | faction:cabal | abilities:amalgamation | Amalgamation: When you produce a unit: You may return 1 captured unit of that type to |
| `production.cost` | MODIFY | effect:action_cards:war_machine | — | — |
| `production.cost` | MODIFY | breakthrough:ghostbt | breakthroughs:ghostbt | Reduce the combined cost of units you produce in systems that contain wormholes by 1 for each |
| `production.cost` | MODIFY | effect:leaders:winnuagent:cut | — | — |
| `production.cost` | MODIFY | technology:st | technologies:st | Sarween Tools: gdy jednostki używają PRODUCTION, łączny koszt jest niższy o 1. |
| `production.forbids` | FORBID | faction:arborec | — | Mitosis: Your space docks cannot produce infantry (R_production). |
| `production.forbids` | FORBID | unit:naaz_voltron | — | Game effects cannot place or produce your mechs. |
| `production.free` | PERMIT | effect:leaders:hacanhero:free | — | — |
| `production.free_cargo` | PERMIT | breakthrough:solbt | breakthroughs:solbt | Bellum Gloriosum: When you produce a ship that has capacity, you may also produce any |
| `production.free_small_units` | MODIFY | leader:cabalcommander | leaders:cabalcommander | That Which Molds Flesh: When you produce fighter or infantry units: Up to 2 of those units |
| `production.free_types` | FORBID | leader:nomadcommander | leaders:nomadcommander | Navarch Feng: When you produce: You can produce your flagship without spending resources |
| `production.gain_trade_good` | PERMIT | leader:titanscommander | leaders:titanscommander | Tungstantus: When 1 or more of your units use PRODUCTION: You may gain 1 trade good. |
| `production.planet_value` | MODIFY | technology:ah | technologies:ah | Aerie Hololattice: Each planet that contains 1 or more of your structures gains the |
| `production.system_value` | MODIFY | breakthrough:ghostbt | breakthroughs:ghostbt | Each wormhole in a system that contains your ships gains PRODUCTION 1 as if it were a unit |
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
| `status.action_cards` | MODIFY | rule:breakthroughs:titansbt:coexistence | breakthroughs:titansbt | Slumberstate Computing: During the status phase, for each player you are coexisting with, |
| `status.action_cards` | MODIFY | technology:nm | technologies:nm | Neural Motivator: w fazie statusu gracz dobiera 2 karty akcji zamiast 1. |
| `status.command_tokens` | MODIFY | technology:hm | technologies:hm | Hyper Metabolism: w fazie statusu gracz zdobywa 3 żetony dowodzenia zamiast 2. |
| `status.command_tokens` | MODIFY | faction:sol | abilities:versatile | Versatile: When you gain command tokens during the status phase: Gain 1 additional command |
| `strategy.give_chosen_card` | PERMIT | agenda:checks | agendas:checks | — |
| `strategy.secondary_as_primary` | PERMIT | faction:jolnar | abilities:brilliant | Brilliant: When you spend a command token to resolve the secondary ability of the |
| `strategy.secondary_free` | PERMIT | faction:hacan | abilities:master_of_trade | Masters of Trade: You do not have to spend a command token to resolve the secondary |
| `structures.pds_as_mech` | PERMIT | unit:titans_mech | units:titans_mech | Hecatoncheires: DEPLOY: When you would place a PDS on a planet, you may place 1 mech and |
| `system.action_wormholes` | FORBID | technology:lgf | technologies:lgf | "treat its system as if it has both an α and β wormhole" - the system counts as containing |
| `tactical.activation_blocked` | PERMIT | technology:cm | technologies:cm | Other players cannot activate asteroid fields that contain 1 or more of your ships. |
| `technology.captured_skip` | PERMIT | faction:cabal | abilities:riftmeld | Riftmeld: When you research a unit upgrade technology: You may return 1 captured unit of |
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
| `units.floating_structure` | PERMIT | unit:saar_spacedock | units:saar_spacedock | This unit is placed in the space area instead of on a planet. This unit can move and |
| `units.floating_structure` | PERMIT | unit:saar_spacedock2 | technologies:ffac2 | This unit is placed in the space area instead of on a planet. This unit can move and |
| `units.ground_moves_as_ship` | PERMIT | unit:naaz_voltron | — | Statek: rusza się sam (Move 3), liczy się do puli floty (eidolon-maximum 1). |
| `units.place_forbidden` | FORBID | unit:naaz_voltron | — | Game effects cannot place or produce your mechs (nigdy dwa Eidolon Maximum - 4). |
| `units.structure_ground_forces` | FORBID | unit:titans_pds | units:titans_pds | Hel-Titan I/II: This unit is treated as both a structure and a ground force. It cannot be |
| `units.structure_ground_forces` | FORBID | unit:titans_pds2 | technologies:ht2 | Hel-Titan I/II: This unit is treated as both a structure and a ground force. It cannot be |
| `units.sustain_lost` | FORBID | agenda:schematics | agendas:schematics | — |

Dostępne punkty zaczepienia (stałe `POINT_*` w `core/rules_hooks.py`):

- `action_cards.forbidden`
- `action_cards.canceller`
- `turn.action_started`
- `adjacency.cut_for_player`
- `adjacency.extra_for_player`
- `agenda.single_vote`
- `agenda.votes_per_planet`
- `agenda.vote_first`
- `agenda.vote_modifier`
- `agenda.vote_unblockable`
- `board.unit_wormholes`
- `bombardment.extra_dice`
- `bombardment.forbidden_traits`
- `bombardment.granted_hits_on`
- `bombardment.ground_units`
- `bombardment.ignores_planetary_shield`
- `bombardment.roll_modifier`
- `bombardment.empty_planets`
- `breakthrough.fracture_no_roll`
- `capture.destroyed`
- `combat.ability_hit_immune`
- `combat.afb_all_ships`
- `combat.afb_extra_dice`
- `combat.afb_granted`
- `combat.afb_infantry_kill`
- `combat.afb_raid`
- `combat.bonus_dice`
- `combat.champion`
- `combat.extra_dice`
- `combat.extra_hits`
- `combat.granted_sustain`
- `combat.hits_to_non_fighters`
- `combat.hit_multiplier`
- `combat.hit_shields`
- `combat.natural_extra_hits`
- `combat.reroll_misses`
- `combat.reroll_plus_one`
- `combat.roll_modifier`
- `combat.single_unit_bonus`
- `combat.space_ground_variant`
- `combat.sustain_cancels`
- `combat.sustain_denied`
- `economy.commodity_value`
- `control.structures_replaced`
- `custodians.free`
- `dice.adjust_result`
- `elimination.has_production`
- `exploration.extra_draw`
- `fleet_pool.capacity`
- `fleet_pool.fighters_overflow`
- `fleet_pool.fighters_per_ship`
- `fleet_pool.token_cap`
- `fleet_pool.unlimited`
- `hand_limit.action_cards`
- `hand_limit.unlimited`
- `info.peek`
- `invasion.commit_from_planets`
- `invasion.ground_force_types`
- `invasion.skip_bombardment`
- `map.gravity_rifts`
- `movement.alpha_beta_adjacent`
- `movement.enter_asteroids`
- `movement.extra_adjacent`
- `movement.ignore_anomalies`
- `movement.ignore_anomalies_keep_rift`
- `movement.ignore_own_command_token`
- `movement.into_supernova`
- `movement.match_highest`
- `movement.moves_separately`
- `movement.move_value`
- `movement.nebula_ignored`
- `movement.passage_blocked`
- `movement.pass_foreign_ships`
- `movement.rift_extra_bonus`
- `movement.rift_no_roll`
- `movement.single_ship_value`
- `movement.through_nebula`
- `movement.through_supernova`
- `movement.unit_extra_adjacent`
- `movement.wormholes_blocked`
- `movement.wormhole_laws_immune`
- `objectives.ignore_home_control`
- `payment.commodities_as_trade_goods`
- `payment.flex_spend`
- `payment.trade_good_value`
- `space_cannon.pds_disabled`
- `limits.pds_unlimited`
- `agenda.planets_ready_limit`
- `planet.swap_values`
- `production.captured_free`
- `production.cost`
- `production.forbids`
- `production.free`
- `production.free_cargo`
- `production.free_small_units`
- `production.free_types`
- `production.gain_trade_good`
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
- `structures.pds_as_mech`
- `system.action_wormholes`
- `tactical.activation_blocked`
- `technology.captured_skip`
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
- `units.floating_structure`
- `units.ground_moves_as_ship`
- `units.place_forbidden`
- `units.structure_ground_forces`
- `units.sustain_lost`
