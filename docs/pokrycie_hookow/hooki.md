# Pokrycie hooków: zarejestrowane hooki

Generowany — nie edytuj. Podsumowanie: [`../POKRYCIE_HOOKOW.md`](../POKRYCIE_HOOKOW.md).

## 1. Zarejestrowane hooki

Razem: **116**. Opis = pierwsza linia docstringu funkcji hooka.

| Punkt zaczepienia | Rodzaj | Źródło | Komponent | Co robi |
|---|---|---|---|---|
| `bombardment.empty_planets` | PERMIT | technology:x89c4 | technologies:x89c4 | X-89 ΩΩ: wolno bombardować planetę bez sił naziemnych (C_technology). |
| `bombardment.extra_dice` | MODIFY | technology:ps | technologies:ps | Plasma Scoring: 1 z jednostek używających BOMBARDMENT rzuca 1 dodatkową kością. |
| `bombardment.granted_hits_on` | FORBID | effect:action_cards:blitz | — | — |
| `bombardment.roll_modifier` | MODIFY | effect:action_cards:bunker | — | — |
| `combat.afb_all_ships` | PERMIT | effect:action_cards:waylay | — | — |
| `combat.afb_granted` | FORBID | relic:metalivoidarmaments | relics:metalivoidarmaments | — |
| `combat.granted_sustain` | PERMIT | relic:metalivoidshielding | relics:metalivoidshielding | Metali Void Shielding: Each time hits are produced against 1 or more of your non-fighter |
| `combat.hit_multiplier` | MODIFY | technology:x89c4 | technologies:x89c4 | X-89 ΩΩ: podwaja trafienia z bombardowania i z rzutów w walce NAZIEMNEJ. |
| `combat.reroll_plus_one` | PERMIT | relic:thalnos | relics:thalnos | The Crown of Thalnos: During each combat round, this card's owner may reroll any number of |
| `combat.roll_modifier` | MODIFY | effect:action_cards:f_prototype | — | — |
| `combat.roll_modifier` | MODIFY | effect:action_cards:mb1 | — | — |
| `combat.roll_modifier` | MODIFY | effect:action_cards:mb2 | — | — |
| `combat.roll_modifier` | MODIFY | effect:action_cards:mb3 | — | — |
| `combat.roll_modifier` | MODIFY | effect:action_cards:mb4 | — | — |
| `command_tokens.strategy_from_reinforcements` | FORBID | relic:emelpar | relics:emelpar | — |
| `dice.adjust_result` | FORBID | relic:heartofixth | relics:heartofixth | — |
| `economy.commodity_value` | MODIFY | relic:dynamiscore | relics:dynamiscore | Dynamis Core: While this card is in your play area, your commodity value is +2. |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:const_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:diplo_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:imp_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:lead_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:politic_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:sanction | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:tech_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:trade_rider | — | — |
| `event:agenda.outcome_resolved:after` | TRIGGER | effect:action_cards:war_rider | — | — |
| `event:cards.action_played:after` | TRIGGER | effect:action_cards:dp_give | — | — |
| `event:combat.round:end` | TRIGGER | technology:da | technologies:da | Duranium Armor: w każdej rundzie walki po przypisaniu strat naprawia 1 uszkodzoną jednostkę. |
| `event:combat.won:after` | TRIGGER | technology:dxa | technologies:dxa | Dacxive Animators: po wygranej walce naziemnej możesz postawić 1 piechotę na tej planecie. |
| `event:combat:start` | TRIGGER | technology:asc | technologies:asc | Assault Cannon: na początku walki kosmicznej przeciwnik niszczy 1 swój statek niemyśliwski. |
| `event:combat:start` | TRIGGER | technology:md | technologies:md | Magen Defense Grid ΩΩ: na początku walki naziemnej na planecie z Twoją strukturą |
| `event:combat:start` | TRIGGER | relic:metalivoidarmaments | — | Metali Void Armaments: During the "Anti-Fighter Barrage" step of space combat, you may |
| `event:component.gained:when` | TRIGGER | relic:bookoflatvinia | — | Book of Latvinia: When you gain this card, research up to 2 technologies that have no |
| `event:component.gained:when` | TRIGGER | relic:obsidian | relics:obsidian | The Obsidian: When you gain this card, draw 1 secret objective. |
| `event:component.gained:when` | TRIGGER | relic:quantumcore | relics:quantumcore | The Quantumcore: When you gain this card, gain your breakthrough. |
| `event:component.gained:when` | TRIGGER | relic:shard | — | Shard of the Throne: When you gain this card, gain 1 victory point. |
| `event:objective.revealed:after` | TRIGGER | relic:neuraloop | relics:neuraloop | Neuraloop: When a public objective is revealed, you may purge one of your relics to discard |
| `event:phase:end` | TRIGGER | relic:emphidia | relics:emphidia | The Crown of Emphidia: At the end of the status phase, if you control the "Tomb of |
| `event:phase:start` | TRIGGER | technology:inf2 | technologies:inf2 | Piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:phase:start` | TRIGGER | technology:inf2 | technologies:inf2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:phase:start` | TRIGGER | relic:mawofworlds | relics:mawofworlds | Maw of Worlds: At the start of the agenda phase, you may purge this card and exhaust all of |
| `event:phase:start` | TRIGGER | technology:td | technologies:td | Transit Diodes: na początku Twojej tury w fazie akcji wyczerp kartę i przenieś do 4 sił |
| `event:planet.control_gained:after` | TRIGGER | technology:ie | technologies:ie | Integrated Economy: po zdobyciu planety możesz wyprodukować dowolną liczbę jednostek |
| `event:planet.control_gained:after` | TRIGGER | relic:shard | relics:shard | Shard of the Throne: When a player gains control of a legendary planet you control or a |
| `event:planet.control_gained:after` | TRIGGER | planet:styx | planets:styx | A Song Like Marrow: When you gain this card, gain 1 victory point. |
| `event:planet.control_gained:after` | TRIGGER | planet:thundersedge | planets:thundersedge | Jupiter Brain: Gain your breakthrough when you gain this card if you do not already have |
| `event:planet.control_lost:when` | TRIGGER | planet:styx | planets:styx | A Song Like Marrow: When you lose this card, lose 1 victory point. |
| `event:player.passed:when` | TRIGGER | planet:faunus | planets:faunus | Maxis Central Control: You may exhaust this card when you pass to gain control of a non-home, non-legendary planet that contains no units and has no attachments. |
| `event:player.passed:when` | TRIGGER | planet:garbozia | planets:garbozia | Dok 'N Pic's Salvage Yard: You may exhaust this card when you pass to place 1 action card from the discard pile faceup on this card. |
| `event:player.passed:when` | TRIGGER | planet:industrex | planets:industrex | Aeurex Mechanica: You may exhaust this card when you pass to place 1 ship that matches a unit upgrade technology you own from your reinforcements into a system that contains your ships. |
| `event:player.passed:when` | TRIGGER | planet:ordinian | planets:ordinian | Hyperion: You may exhaust this card when you pass to draw 1 action card and gain 1 command token. |
| `event:player.passed:when` | TRIGGER | planet:ordinianc4 | planets:ordinianc4 | Hyperion: You may exhaust this card when you pass to draw 1 action card and gain 1 command token. |
| `event:production.used:after` | TRIGGER | technology:sar | technologies:sar | Self-Assembly Routines: po PRODUCTION wyczerp kartę, by postawić 1 mecha z rezerwy |
| `event:strategy.imperial_victory_point:after` | TRIGGER | planet:custodiavigilia | planets:custodiavigilia | Custodian's Favour: Gain 2 command tokens when another player scores a victory point with |
| `event:tactical.action:end` | TRIGGER | technology:det | technologies:det | Dark Energy Tap: po akcji taktycznej w systemie z żetonem frontier i Twoim statkiem |
| `event:tactical.action:end` | TRIGGER | relic:emphidia | relics:emphidia | The Crown of Emphidia: After you perform a tactical action, you may exhaust this card to |
| `event:tactical.system_activated:after` | TRIGGER | promissory:<color>_an | promissory_notes:<color>_an | — |
| `event:tactical.system_activated:after` | TRIGGER | promissory:<color>_sftt | promissory_notes:<color>_sftt | — |
| `event:tactical.system_activated:after` | TRIGGER | relic:dominusorb | relics:dominusorb | Dominus Orb: Before you move units during a tactical action, you may purge this card to |
| `event:tactical.system_activated:after` | TRIGGER | technology:sdn | technologies:sdn | Scanlink Drone Network: przy aktywacji systemu możesz zbadać 1 planetę z Twoimi |
| `event:tactical.system_activated:after` | TRIGGER | planet:tempesta | planets:tempesta | Ionian Fuel Refinery: You may exhaust this card after you activate a system to apply +1 to the move value of 1 of your ships during this tactical action. |
| `event:tactical.system_activated:when` | TRIGGER | technology:md | technologies:md | Magen Defense Grid ΩΩ: aktywacja systemu z Twoimi strukturami → 1 piechota przy każdej. |
| `event:technology.research:when` | TRIGGER | relic:prophetstears | relics:prophetstears | The Prophet's Tears: When you research a technology, you may exhaust this card to ignore 1 |
| `event:transaction:after` | TRIGGER | effect:action_cards:blackmarketdealing | — | Karta dotyczy jednej transakcji: po jej rozstrzygnięciu efekt znika. |
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
| `event:turn:start` | TRIGGER | technology:inf2 | technologies:inf2 | Piechota z karty Infantry II trafia na wybraną planetę w systemie domowym. |
| `event:turn:start` | TRIGGER | technology:inf2 | technologies:inf2 | Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy |
| `event:turn:start` | TRIGGER | technology:td | — | Transit Diodes: na początku Twojej tury w fazie akcji wyczerp kartę i przenieś do 4 sił |
| `event:unit.ability_used:after` | TRIGGER | technology:x89c4 | technologies:x89c4 | X-89 ΩΩ: każda planeta, przeciw której użyto BOMBARDMENT, zostaje wyczerpana. |
| `event:unit.destroyed:after` | TRIGGER | technology:inf2 | technologies:inf2 | Infantry II: po zniszczeniu piechoty rzuć kością; przy 6+ jednostka trafia na kartę. |
| `event:unit.destroyed:after` | TRIGGER | technology:sar | — | Self-Assembly Routines: po zniszczeniu Twojego mecha zdobywasz 1 TG (za każdego mecha; |
| `movement.alpha_beta_adjacent` | PERMIT | effect:action_cards:lost_star | — | — |
| `movement.enter_asteroids` | PERMIT | technology:amd | technologies:amd | Antimass Deflectors: statki mogą wchodzić do pól asteroid i przez nie przechodzić. |
| `movement.enter_asteroids` | PERMIT | relic:circletofthevoid | — | Circlet of the Void: ruch przez/do pól asteroid (ignorowanie efektów anomalii). |
| `movement.ignore_anomalies` | PERMIT | effect:action_cards:nav_suite | — | — |
| `movement.ignore_anomalies` | PERMIT | relic:circletofthevoid | relics:circletofthevoid | Circlet of the Void: you ignore the effects of all other anomalies on movement. |
| `movement.ignore_own_command_token` | PERMIT | effect:relics:dominusorb | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs1 | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs2 | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs3 | — | — |
| `movement.move_value` | MODIFY | effect:action_cards:fs4 | — | — |
| `movement.move_value` | MODIFY | technology:gd | technologies:gd | Gravity Drive: po aktywacji +1 do wartości ruchu JEDNEGO statku w tej akcji. |
| `movement.move_value` | MODIFY | effect:planets:tempesta | planets:tempesta | Ionian Fuel Refinery: +1 do wartości ruchu JEDNEGO statku w tej akcji taktycznej. |
| `movement.pass_foreign_ships` | PERMIT | effect:action_cards:silence_space | — | Przelot przez obce statki dotyczy tylko statków startujących z wybranego systemu. |
| `movement.pass_foreign_ships` | PERMIT | technology:lwd | technologies:lwd | Light/Wave Deflector: statki mogą przechodzić przez systemy z cudzymi statkami. |
| `objectives.secret_limit` | MODIFY | relic:obsidian | relics:obsidian | The Obsidian: You can have 1 additional scored or unscored secret objective. |
| `production.cost` | MODIFY | effect:action_cards:war_machine | — | — |
| `production.cost` | MODIFY | technology:st | technologies:st | Sarween Tools: gdy jednostki używają PRODUCTION, łączny koszt jest niższy o 1. |
| `production.forbids` | FORBID | faction:arborec | — | Arborec: wartość PRODUCTION doków nie służy do produkcji piechoty (R_production). |
| `production.total_value` | MODIFY | effect:action_cards:war_machine | — | — |
| `retreat.anywhere` | PERMIT | technology:det | — | Dark Energy Tap: statki mogą wycofać się do sąsiedniego systemu bez cudzych jednostek. |
| `space_cannon.extra_dice` | MODIFY | technology:ps | technologies:ps | Plasma Scoring: 1 z jednostek używających SPACE CANNON rzuca 1 dodatkową kością. |
| `space_cannon.granted` | FORBID | relic:lightrailordnance | relics:lightrailordnance | Lightrail Ordnance: Your space docks gain SPACE CANNON 5 (x2). You may use your space |
| `space_cannon.offense_immune` | PERMIT | effect:action_cards:solar_flare | — | — |
| `space_cannon.pds_disabled` | PERMIT | effect:action_cards:disable | — | — |
| `space_cannon.roll_modifier` | MODIFY | technology:amd | technologies:amd | Antimass Deflectors: -1 do wyniku kości Space Cannon rzucanych przeciw jego jednostkom. |
| `status.action_cards` | MODIFY | technology:nm | technologies:nm | Neural Motivator: w fazie statusu gracz dobiera 2 karty akcji zamiast 1. |
| `status.command_tokens` | MODIFY | technology:hm | technologies:hm | Hyper Metabolism: w fazie statusu gracz zdobywa 3 żetony dowodzenia zamiast 2. |
| `technology.ignore_prerequisite` | FORBID | relic:prophetstears | relics:prophetstears | — |
| `technology.specialty_without_exhaust` | PERMIT | technology:pa | — | Psychoarchaeology: specjalności technologii działają bez wyczerpywania planet, także |
| `technology.synergy_all` | PERMIT | relic:quantumcore | — | The Quantumcore: You have SYNERGY for all technology types. |
| `transaction.extra_items` | PERMIT | effect:action_cards:blackmarketdealing | — | — |
| `turn.action_started` | PERSISTENT | effect:action_cards:extremeduress | — | Pierwsza akcja celu: strategiczna = bez kary; inna = karty, TG i tajne cele dla gracza. |
| `turn.actions` | MODIFY | effect:action_cards:master_plan | — | — |
| `turn.actions` | MODIFY | technology:fl | technologies:fl | Fleet Logistics: w swojej turze fazy akcji gracz wykonuje 2 akcje zamiast 1. |

Dostępne punkty zaczepienia (stałe `POINT_*` w `core/rules_hooks.py`):

- `turn.action_started`
- `agenda.vote_modifier`
- `bombardment.extra_dice`
- `bombardment.granted_hits_on`
- `bombardment.roll_modifier`
- `bombardment.empty_planets`
- `combat.afb_all_ships`
- `combat.afb_granted`
- `combat.extra_dice`
- `combat.granted_sustain`
- `combat.hit_multiplier`
- `combat.reroll_misses`
- `combat.reroll_plus_one`
- `combat.roll_modifier`
- `economy.commodity_value`
- `dice.adjust_result`
- `movement.alpha_beta_adjacent`
- `movement.enter_asteroids`
- `movement.ignore_anomalies`
- `movement.ignore_own_command_token`
- `movement.move_value`
- `movement.pass_foreign_ships`
- `payment.commodities_as_trade_goods`
- `space_cannon.pds_disabled`
- `production.cost`
- `production.forbids`
- `production.total_value`
- `production.value`
- `retreat.anywhere`
- `objectives.secret_limit`
- `space_cannon.extra_dice`
- `space_cannon.granted`
- `space_cannon.offense_immune`
- `space_cannon.roll_modifier`
- `status.action_cards`
- `status.command_tokens`
- `command_tokens.strategy_from_reinforcements`
- `technology.ignore_prerequisite`
- `technology.specialty_without_exhaust`
- `technology.synergy_all`
- `transaction.extra_items`
- `turn.actions`
