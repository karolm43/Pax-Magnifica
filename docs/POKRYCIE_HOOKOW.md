# Pokrycie hooków (generowany — nie edytuj ręcznie)

Wygenerowano: `uv run python -m src.audit.hook_coverage --write`. Zasady: `RULES.md` 43.
Obszary reguł i typ hooka to HEURYSTYKA po słowach kluczowych (priorytetyzacja, nie decyzja).

## 1. Zarejestrowane hooki

Razem: **2**. Opis = pierwsza linia docstringu funkcji hooka.

| Punkt zaczepienia | Rodzaj | Źródło | Komponent | Co robi |
|---|---|---|---|---|
| `movement.enter_asteroids` | PERMIT | technology:amd | technologies:amd | Antimass Deflectors: statki mogą wchodzić do pól asteroid i przez nie przechodzić. |
| `production.forbids` | FORBID | faction:arborec | — | Arborec: wartość PRODUCTION doków nie służy do produkcji piechoty (R_production). |

Dostępne punkty zaczepienia (stałe `POINT_*` w `core/rules_hooks.py`):

- `agenda.vote_modifier`
- `combat.extra_dice`
- `combat.reroll_misses`
- `combat.roll_modifier`
- `movement.enter_asteroids`
- `movement.move_value`
- `movement.pass_foreign_ships`
- `payment.commodities_as_trade_goods`
- `production.cost`
- `production.forbids`
- `production.value`

## 2. Pokrycie per kategoria

| Kategoria | Komponentów | Z hookiem | % |
|---|---:|---:|---:|
| action_cards | 143 | 5 | 3.5 |
| agendas | 123 | 0 | 0.0 |
| explores | 80 | 0 | 0.0 |
| relics | 24 | 0 | 0.0 |
| promissory_notes | 40 | 0 | 0.0 |
| galactic_events | 20 | 0 | 0.0 |
| leaders | 103 | 0 | 0.0 |
| abilities | 73 | 0 | 0.0 |
| technologies | 102 | 1 | 1.0 |
| breakthroughs | 31 | 0 | 0.0 |

## 3. Rodzaj wyzwalacza (komponenty z oknem czasowym)

| Wyzwalacz | Komponentów |
|---|---:|
| after | 78 |
| action | 76 |
| when | 69 |
| at_start | 30 |
| at_end | 12 |
| unclassified | 11 |
| before | 10 |
| during | 8 |

## 4. Zapotrzebowanie na obszary reguł i typy hooków (priorytety)

Im więcej komponentów dotyka obszaru, tym bardziej opłaca się domknąć jego punkty zaczepienia.

| Obszar | Komponentów | Bez hooka |
|---|---:|---:|
| planety i eksploracja (control, exploration) | 246 | 241 |
| walka (combat.*, space_cannon, bombardment) | 196 | 195 |
| produkcja (production.*) | 177 | 175 |
| ekonomia i płatności (economy, payment) | 168 | 166 |
| karty (card_draw, promissory) | 145 | 145 |
| status i odświeżanie (status_phase) | 143 | 142 |
| ruch (movement.*) | 125 | 124 |
| żetony dowodzenia (command_tokens) | 109 | 109 |
| agenda i głosowanie (agenda_phase) | 97 | 97 |
| technologie (technology) | 78 | 78 |
| karty strategii i inicjatywa | 46 | 43 |
| cele i punkty (objectives) | 45 | 45 |

Szacowany typ hooka (RULES.md 43.1 pkt 4):

| Typ | Komponentów |
|---|---:|
| — | 228 |
| TRIGGER (okno reakcji) | 157 |
| PERMIT (pozwolenie) | 153 |
| MODIFY (liczba/rzut) | 108 |
| FORBID (zakaz) | 51 |
| REPLACE (instead of) | 42 |

## 5. Przypadki szczególne: bez dopasowania do obszaru (25)

Te komponenty nie trafiły w żadne słowo kluczowe — wymagają ręcznego przeglądu (często to unikalne mechaniki albo teksty zbyt ogólne).

| Kategoria | Id | Nazwa | Źródło | Wyzwalacz | Tekst |
|---|---|---|---|---|---|
| abilities | `brilliant` | Brilliant | base | when | You may resolve the primary ability instead. |
| abilities | `creuss_gate` | Creuss Gate | base | — | When you create the game board, place the Creuss Gate (tile 17) where your home system would normally be placed. The Creuss Gate system is … |
| abilities | `guild_ships` | Guild Ships | base | — | You can negotiate transactions with players who are not your neighbor. |
| abilities | `nocturne` | Nocturne | thunders_edge | — | This faction cannot be chosen during setup. |
| abilities | `phoenixstandard` | Phoenix Standard | thunders_edge | at_end | you may galvanize 1 of your units that participated. |
| abilities | `sorrow` | Sorrow | thunders_edge | — | When you create the game board, place the Sorrow (tile 94) where your home system would normally be placed, then place a inactive breach th… |
| abilities | `the_company` | The Company | pok | — | During setup, take the 2 additional Nomad faction agents and place them next to your faction sheet; you have 3 agents |
| action_cards | `confounding` | Confounding Legal Text | pok | when | You are the elected player instead. |
| action_cards | `confusing` | Confusing Legal Text | base | when | Choose 1 player. That player is the elected player instead. |
| action_cards | `crisis` | Crisis | thunders_edge | at_end | Skip the next player's turn. |
| action_cards | `fire_team` | Fire Team | base | after | Reroll any number of your dice. |
| action_cards | `master_plan` | Master Plan | codex1 | after | Perform an additional action. |
| action_cards | `parley` | Parley | base | after | Return the committed units to the space area. |
| action_cards | `puppetsonastring` | Puppets on a String | thunders_edge | at_end | Perform 1 action. |
| action_cards | `refit` | Refit Troops | pok | action | Choose 1 or 2 of your infantry on the game board. Replace each of those infantry with mechs. |
| action_cards | `scramble` | Scramble Frequency | codex1 | after | That player rerolls all of their dice. |
| agendas | `covert` | Covert Legislation | pok | — |  |
| breakthroughs | `yssarilbt` | Deepgloom Executable | thunders_edge | — | You can allow other players to use your STALL TACTICS or SCHEMING faction abilities; when you do, you may resolve a transaction with that p… |
| leaders | `jolnarcommander` | Agnlan Oln | pok | after | [commander] You may reroll any of those dice. |
| leaders | `kelerescommander` | Suffi An | pok | after | [commander] You may perform an additional action. |
| promissory_notes | `<color>_an` | Alliance | pok | — | When you receive this card, if you are not the <color> player, you must place it faceup in your play area. While this card is in your play … |
| promissory_notes | `convoys` | Trade Convoys | base | — | ACTION: Place this card faceup in your play area. While this card is in your play area, you may negotiate transactions with players who are… |
| promissory_notes | `pop` | Promise of Protection | base | — | ACTION: Place this card faceup in your play area. While this card is in your play area, the Mentak player cannot use their Pillage faction … |
| technologies | `fl` | Fleet Logistics | base | — | During each of your turns of the action phase, you may perform 2 actions instead of 1. |
| technologies | `planesplitter-firm` | Planesplitter (Firmament) | thunders_edge | — | When you gain this card, put The Fracture into play. Flip this card if the Obsidian faction is in play. |

## 6. Frakcje (komponenty frakcyjne i pokrycie)

Zdolności, technologie frakcyjne, liderzy, przełom i promissory notes przypisane do frakcji. Keleres (3 warianty) liczony jako jedna rodzina.

| Frakcja | Zdolności | Tech. | Liderzy | Przełom | PN | Z hookiem / razem | Obszary reguł |
|---|---:|---:|---:|---:|---:|---:|---|
| The Arborec (`arborec`) | 1 | 2 | 3 | 1 | 1 | 0 / 8 | planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Argent Flight (`argent`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | agenda i głosowanie, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| Last Bastion (`bastion`) | 3 | 2 | 4 | 1 | 1 | 0 / 11 | ekonomia i płatności, karty, planety i eksploracja, produkcja, status i odświeżanie, walka, żetony dowodzenia |
| The Ghosts of Creuss (`creuss`) | 3 | 2 | 3 | 1 | 1 | 0 / 10 | planety i eksploracja, produkcja, ruch, status i odświeżanie, walka |
| The Deepwrought Scholarate (`deepwrought`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | ekonomia i płatności, karty, planety i eksploracja, produkcja, status i odświeżanie, technologie |
| The Empyrean (`empyrean`) | 3 | 2 | 3 | 1 | 2 | 0 / 11 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, żetony dowodzenia |
| The Firmament (`firmament`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | cele i punkty, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Emirates of Hacan (`hacan`) | 3 | 2 | 3 | 1 | 1 | 0 / 10 | agenda i głosowanie, ekonomia i płatności, karty, karty strategii i inicjatywa, produkcja, status i odświeżanie, żetony dowodzenia |
| The Universities of Jol-Nar (`jol-nar`) | 3 | 2 | 3 | 1 | 1 | 0 / 10 | ekonomia i płatności, karty strategii i inicjatywa, planety i eksploracja, ruch, status i odświeżanie, technologie, walka |
| The Council Keleres - Mentak (`keleres`) | 3 | 3 | 5 | 1 | 4 | 0 / 16 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The L1Z1X Mindnet (`l1z1x`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Barony of Letnev (`letnev`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | ekonomia i płatności, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Mahact Gene-Sorcerers (`mahact`) | 3 | 2 | 3 | 1 | 1 | 0 / 10 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Mentak Coalition (`mentak`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | ekonomia i płatności, karty, produkcja, ruch, status i odświeżanie, technologie, walka |
| The Embers of Muaat (`muaat`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | ekonomia i płatności, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Naalu Collective (`naalu`) | 2 | 2 | 4 | 1 | 1 | 0 / 10 | agenda i głosowanie, ekonomia i płatności, karty, karty strategii i inicjatywa, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Naaz-Rokha Alliance (`naaz-rokha`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | ekonomia i płatności, karty, karty strategii i inicjatywa, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Nekro Virus (`nekro`) | 3 | 4 | 3 | 1 | 1 | 0 / 12 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Nomad (`nomad`) | 2 | 2 | 5 | 1 | 1 | 0 / 11 | ekonomia i płatności, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Ral Nel Consortium (`ral nel`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Crimson Rebellion (`rebellion`) | 3 | 2 | 6 | 1 | 1 | 0 / 13 | ekonomia i płatności, produkcja, ruch, status i odświeżanie, walka |
| The Clan of Saar (`saar`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | cele i punkty, ekonomia i płatności, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka |
| Sardakk Norr (`sardakk`) | 1 | 2 | 3 | 1 | 1 | 0 / 8 | karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Federation of Sol (`sol`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | ekonomia i płatności, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Titans of Ul (`ul`) | 3 | 2 | 3 | 1 | 1 | 0 / 10 | ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka |
| The Vuil'raith Cabal (`vuil'raith`) | 3 | 2 | 3 | 1 | 1 | 0 / 10 | ekonomia i płatności, produkcja, ruch, status i odświeżanie, technologie, walka |
| The Winnu (`winnu`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | ekonomia i płatności, karty strategii i inicjatywa, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Xxcha Kingdom (`xxcha`) | 2 | 2 | 4 | 1 | 1 | 0 / 10 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, żetony dowodzenia |
| The Yin Brotherhood (`yin`) | 2 | 2 | 3 | 1 | 1 | 0 / 9 | cele i punkty, ekonomia i płatności, planety i eksploracja, produkcja, status i odświeżanie, technologie, walka |
| The Yssaril Tribes (`yssaril`) | 3 | 2 | 3 | 1 | 1 | 0 / 10 | cele i punkty, karty, status i odświeżanie |

## 7. Lista szczegółowa komponentów

Każda kategoria zwinięta; kolumna „Typ” to oszacowanie heurystyczne.

<details><summary>action_cards (143)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `abs` | Ancient Burial Sites | — | at_start | — | planety i eksploracja, status i odświeżanie | — | Choose 1 player. Exhaust each cultural planet owned by that player. |
| `arch_expedition` | Archaeological Expedition | — | action | — | karty, planety i eksploracja | — | Reveal the top 3 cards of an exploration deck that matches a planet you control; gain any relic fragments that you reveal and discard the r… |
| `assassin` | Assassinate Representative | — | after | TRIGGER (okno reakcji) | agenda i głosowanie | — | Choose 1 player. That player cannot vote on this agenda. |
| `blackmarketdealing` | Black Market Dealings | — | when | TRIGGER (okno reakcji) | karty, planety i eksploracja, cele i punkty | — | You and the other player may include relics, action cards, and unscored secret objectives as part of the transaction. This card cannot be c… |
| `blitz` | Blitz | — | at_start | — | walka | — | Each of your non-fighter ships in the active system that do not have BOMBARDMENT gain BOMBARDMENT 6 until the end of the invasion. |
| `bribery` | Bribery | — | after | TRIGGER (okno reakcji) | ekonomia i płatności, agenda i głosowanie | — | Spend any number of trade goods. For each trade good spent, cast 1 additional vote for the outcome on which you voted. |
| `brilliance` | Brilliance | — | action | — | technologie, planety i eksploracja, status i odświeżanie | — | Ready 1 of your planets that has a technology specialty or choose 1 player to gain their breakthrough. |
| `bunker` | Bunker | — | at_start | MODIFY (liczba/rzut) | walka, planety i eksploracja | — | During this invasion, apply -4 to the result of each BOMBARDMENT roll against planets you control. |
| `confounding` | Confounding Legal Text | — | when | TRIGGER (okno reakcji) | — | — | You are the elected player instead. |
| `confusing` | Confusing Legal Text | — | when | TRIGGER (okno reakcji) | — | — | Choose 1 player. That player is the elected player instead. |
| `const_rider` | Construction Rider | — | after | TRIGGER (okno reakcji) | produkcja, planety i eksploracja, agenda i głosowanie | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, place 1 space dock from your reinfo… |
| `counterstroke` | Counterstroke | — | after | TRIGGER (okno reakcji) | żetony dowodzenia | — | Return that command token to your tactic pool. |
| `coup` | Coup d'Etat | — | when | TRIGGER (okno reakcji) | status i odświeżanie, karty strategii i inicjatywa | — | End that player's turn, the strategic action is not resolved and the strategy card is not exhausted. |
| `courageous` | Courageous to the End | — | after | TRIGGER (okno reakcji) | walka | — | Roll 2 dice. For each result equal to or greater than that ship's combat value, your opponent must choose and destroy 1 of their ships. |
| `crashlanding` | Crash Landing | — | when | TRIGGER (okno reakcji) | planety i eksploracja | — | Place 1 of your ground forces from the space area of the active system onto a planet in that system other than Mecatol Rex; if the planet c… |
| `cripple` | Cripple Defenses | — | action | — | walka, planety i eksploracja | — | Choose 1 planet. Destroy each PDS on that planet. |
| `crisis` | Crisis | — | at_end | — | — | — | Skip the next player's turn. |
| `deadly_plot` | Deadly Plot | — | during | REPLACE (instead of) | karty, planety i eksploracja, agenda i głosowanie, status i odświeżanie | — | If you voted for or predicted another outcome, discard the agenda instead. The agenda is resolved with no effect and it is not replaced. Th… |
| `decoy` | Decoy Operation | — | after | TRIGGER (okno reakcji) | planety i eksploracja | — | Remove up to 2 of your ground forces from the game board and place them on a planet you control in the active system. |
| `dh1` | Direct Hit | — | after | TRIGGER (okno reakcji) | walka | — | Destroy that ship. |
| `dh2` | Direct Hit | — | after | TRIGGER (okno reakcji) | walka | — | Destroy that ship. |
| `dh3` | Direct Hit | — | after | TRIGGER (okno reakcji) | walka | — | Destroy that ship. |
| `dh4` | Direct Hit | — | after | TRIGGER (okno reakcji) | walka | — | Destroy that ship. |
| `diplo_rider` | Diplomacy Rider | — | after | TRIGGER (okno reakcji) | produkcja, żetony dowodzenia, planety i eksploracja, agenda i głosowanie | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, choose 1 system that contains a pla… |
| `disable` | Disable | — | at_start | — | walka | — | Your opponents' PDS units lose PLANETARY SHIELD and SPACE CANNON during this invasion. |
| `disgrace` | Public Disgrace | — | when | TRIGGER (okno reakcji) | karty strategii i inicjatywa | — | That player must choose a different strategy card instead, if able. |
| `distinguished` | Distinguished Councilor | — | after | TRIGGER (okno reakcji) | agenda i głosowanie | — | Cast 5 additional votes for that outcome. |
| `divert_funding` | Divert Funding | — | action | — | technologie | — | Return a non-unit upgrade, non-faction technology that you own to your technology deck. Then, research another technology. |
| `dp1` | Diplomatic Pressure | — | when | TRIGGER (okno reakcji) | karty | — | Choose another player. That player must give you 1 promissory note from their hand. |
| `dp2` | Diplomatic Pressure | — | when | TRIGGER (okno reakcji) | karty | — | Choose another player. That player must give you 1 promissory note from their hand. |
| `dp3` | Diplomatic Pressure | — | when | TRIGGER (okno reakcji) | karty | — | Choose another player. That player must give you 1 promissory note from their hand. |
| `dp4` | Diplomatic Pressure | — | when | TRIGGER (okno reakcji) | karty | — | Choose another player. That player must give you 1 promissory note from their hand. |
| `economic_initiative` | Economic Initiative | — | action | — | planety i eksploracja, status i odświeżanie, karty strategii i inicjatywa | ✔ | Ready each cultural planet you control. |
| `emergency` | Emergency Repairs | — | at_start | — | walka | — | Repair all of your units that have SUSTAIN DAMAGE in the active system. |
| `exchangeprogram` | Exchange Program | — | action | PERMIT (pozwolenie) | produkcja, żetony dowodzenia, karty, planety i eksploracja | — | Choose another player. You and that player may agree to place 1 infantry from each of your reinforcements into coexistence on a planet the … |
| `experimental` | Experimental Battlestation | — | after | TRIGGER (okno reakcji) | ruch, walka, produkcja | — | Choose 1 of your space docks that is either in or adjacent to that system. That space dock uses SPACE CANNON 5(x3) against the active playe… |
| `extremeduress` | Extreme Duress | — | at_start | — | ekonomia i płatności, karty, cele i punkty | — | If that player's next action is not a strategic action, they discard all of their action cards, give you all of their trade goods, and show… |
| `f_conscription` | Fighter Conscription | — | action | FORBID (zakaz) | produkcja | — | Place 1 fighter from your reinforcements in each system that contains 1 or more of your space docks or units that have capacity. They canno… |
| `f_deployment` | Frontline Deployment | — | action | — | produkcja, planety i eksploracja | ✔ | Place 3 infantry from your reinforcements on 1 planet you control. |
| `f_prototype` | Fighter Prototype | — | at_start | MODIFY (liczba/rzut) | walka | — | Apply +2 to the result of each of your fighters' combat rolls during this combat round. |
| `f_researched` | Focused Research | — | action | — | ekonomia i płatności, technologie | — | Spend 4 trade goods to research 1 technology |
| `fire_team` | Fire Team | — | after | TRIGGER (okno reakcji) | — | — | Reroll any number of your dice. |
| `fs1` | Flank Speed | — | after | TRIGGER (okno reakcji) | ruch | — | Apply +1 to the move value of each of your ships during this tactical action. |
| `fs2` | Flank Speed | — | after | TRIGGER (okno reakcji) | ruch | — | Apply +1 to the move value of each of your ships during this tactical action. |
| `fs3` | Flank Speed | — | after | TRIGGER (okno reakcji) | ruch | — | Apply +1 to the move value of each of your ships during this tactical action. |
| `fs4` | Flank Speed | — | after | TRIGGER (okno reakcji) | ruch | — | Apply +1 to the move value of each of your ships during this tactical action. |
| `fsb` | Forward Supply Base | — | after | TRIGGER (okno reakcji) | ekonomia i płatności | — | Gain 3 trade goods. Then, choose another player to gain 1 trade good. |
| `ghost_ship` | Ghost Ship | — | action | — | ruch, walka, produkcja | — | Place 1 destroyer from your reinforcements in a non-home system that contains a wormhole and does not contain other players' ships. |
| `ghost_squad` | Ghost Squad | — | after | TRIGGER (okno reakcji) | ruch, planety i eksploracja | — | Move any number of your ground forces from any planet you control in the active system to any other planet you control in the active system. |
| `hack` | Hack Election | — | after | TRIGGER (okno reakcji) | agenda i głosowanie | — | During this agenda, you vote last. |
| `harness` | Harness Energy | — | after | TRIGGER (okno reakcji) | ekonomia i płatności | — | Replenish your commodities. |
| `imp_rider` | Imperial Rider | — | after | TRIGGER (okno reakcji) | agenda i głosowanie, cele i punkty | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, gain 1 victory point. |
| `impersonation` | Impersonation | — | action | — | ekonomia i płatności, karty, cele i punkty | — | Spend 3 influence to draw 1 secret objective. |
| `industrial_initiative` | Industrial Initiative | — | action | — | ekonomia i płatności, planety i eksploracja, karty strategii i inicjatywa | ✔ | Gain 1 trade good for each industrial planet you control. |
| `infiltrate` | Infiltrate | — | when | TRIGGER (okno reakcji) | produkcja, planety i eksploracja | — | Replace each PDS and space dock that is on that planet with a matching unit from your reinforcements. |
| `insider` | Insider Information | — | after | TRIGGER (okno reakcji) | agenda i głosowanie | — | Look at the top 3 cards of the agenda deck. |
| `insub` | Insubordination | — | action | — | produkcja | — | Remove 1 token from another player's tactic pool and return it to their reinforcements. |
| `intercept` | Intercept | — | after | TRIGGER (okno reakcji) | walka | — | Your opponent cannot retreat during this round of space combat. |
| `investments` | Manipulate Investments | — | at_start | — | ekonomia i płatności, karty strategii i inicjatywa | — | Place a total of 5 trade goods from the supply on strategy cards of your choice. You must place these tokens on at least 3 different cards. |
| `jamming` | Signal Jamming | — | action | — | ruch, produkcja, żetony dowodzenia | — | Choose 1 non-home system that contains or is adjacent to 1 of your ships. Place a command token from another player's reinforcements in tha… |
| `lead_rider` | Leadership Rider | — | after | TRIGGER (okno reakcji) | żetony dowodzenia, agenda i głosowanie | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, gain 3 command tokens. |
| `lieinwait` | Lie in Wait | — | after | TRIGGER (okno reakcji) | karty | — | Look at each of those players' hands of action cards, then choose and take 1 action card from each. |
| `lost_star` | Lost Star Chart | — | after | TRIGGER (okno reakcji) | ruch | — | During this tactical action, systems that contain alpha and beta wormholes are adjacent to each other. |
| `lucky` | Lucky Shot | — | action | — | walka, planety i eksploracja | — | Destroy 1 dreadnought, cruiser, or destroyer in a system that contains a planet you control. |
| `master_plan` | Master Plan | — | after | TRIGGER (okno reakcji) | — | — | Perform an additional action. |
| `mb1` | Morale Boost | — | at_start | MODIFY (liczba/rzut) | walka | — | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `mb2` | Morale Boost | — | at_start | MODIFY (liczba/rzut) | walka | — | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `mb3` | Morale Boost | — | at_start | MODIFY (liczba/rzut) | walka | — | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `mb4` | Morale Boost | — | at_start | MODIFY (liczba/rzut) | walka | — | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `meltdown` | Reactor Meltdown | — | action | — | walka, produkcja | — | Destroy 1 space dock in a non-home system. |
| `mercenarycontract` | Mercenary Contract | — | action | — | ekonomia i płatności, planety i eksploracja | — | Spend 2 trade goods to place 2 neutral infantry on any non-home planet that contains no units; if that planet was owned by another player, … |
| `messiah` | Rise of a Messiah | — | action | — | produkcja, planety i eksploracja | ✔ | Place 1 infantry from your reinforcements on each planet you control. |
| `mining_initiative` | Mining Initiative | — | action | — | ekonomia i płatności, planety i eksploracja, karty strategii i inicjatywa | ✔ | Gain trade goods equal to the resource value of 1 planet you control. |
| `mjets1` | Maneuvering Jets | — | before | TRIGGER (okno reakcji) | walka | — | Cancel 1 hit. |
| `mjets2` | Maneuvering Jets | — | before | TRIGGER (okno reakcji) | walka | — | Cancel 1 hit. |
| `mjets3` | Maneuvering Jets | — | before | TRIGGER (okno reakcji) | walka | — | Cancel 1 hit. |
| `mjets4` | Maneuvering Jets | — | before | TRIGGER (okno reakcji) | walka | — | Cancel 1 hit. |
| `nav_suite` | Nav Suite | — | after | TRIGGER (okno reakcji) | ruch | — | During the 'Movement' step of this tactical action, ignore the effect of anomalies. |
| `overrule` | Overrule | — | action | — | karty strategii i inicjatywa | — | Perform the primary ability of a readied or unchosen strategy card. |
| `parley` | Parley | — | after | TRIGGER (okno reakcji) | — | — | Return the committed units to the space area. |
| `piratecontract1` | Pirate Contract | — | action | — | walka | — | Place 1 neutral destroyer in a non-home system that contains no non-neutral ships. |
| `piratecontract2` | Pirate Contract | — | action | — | walka | — | Place 1 neutral destroyer in a non-home system that contains no non-neutral ships. |
| `piratecontract3` | Pirate Contract | — | action | — | walka | — | Place 1 neutral destroyer in a non-home system that contains no non-neutral ships. |
| `piratecontract4` | Pirate Contract | — | action | — | walka | — | Place 1 neutral destroyer in a non-home system that contains no non-neutral ships. |
| `piratefleet` | Pirate Fleet | — | action | — | walka, ekonomia i płatności | — | Spend 3 resources to place 1 neutral carrier, 1 neutral cruiser, 1 neutral destroyer, and 2 neutral fighters in a non-home system that cont… |
| `plagiarize` | Plagiarize | — | action | — | ekonomia i płatności, technologie | — | Spend 5 influence and choose a non-faction technology owned by 1 of your neighbors. Gain that technology. |
| `plague` | Plague | — | action | — | walka, planety i eksploracja | — | Choose 1 planet that is controlled by another player. Roll 1 die for each infantry on that planet. For each result of 6 or greater, destroy… |
| `politic_rider` | Politics Rider | — | after | TRIGGER (okno reakcji) | karty, agenda i głosowanie | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, draw 3 action cards and gain the sp… |
| `probe` | Exploration Probe | — | action | MODIFY (liczba/rzut) | ruch, planety i eksploracja | — | Explore a frontier token that is in or adjacent to a system that contains 1 or more of your ships. |
| `puppetsonastring` | Puppets on a String | — | at_end | — | — | — | Perform 1 action. |
| `rally` | Rally | — | after | TRIGGER (okno reakcji) | produkcja, żetony dowodzenia | — | Place 2 command tokens from your reinforcements in your fleet pool. |
| `refit` | Refit Troops | — | action | — | — | — | Choose 1 or 2 of your infantry on the game board. Replace each of those infantry with mechs. |
| `reflective` | Reflective Shielding | — | when | TRIGGER (okno reakcji) | walka, produkcja | — | Produce 2 hits against your opponent's ships in the active system. |
| `reparations` | Reparations | — | after | TRIGGER (okno reakcji) | planety i eksploracja, status i odświeżanie | — | Exhaust 1 planet that player controls and ready 1 planet you control. |
| `repeal` | Repeal Law | — | action | — | karty | — | Discard 1 law from play. |
| `rescue` | Rescue | — | after | TRIGGER (okno reakcji) | ruch, żetony dowodzenia | — | You may move 1 of your ships into the active system from any system that does not contain one of your command tokens. |
| `reveal_prototype` | Reveal Prototype | — | at_start | — | walka, ekonomia i płatności, technologie | — | Spend 4 resources to research a unit upgrade technology of the same type as 1 of your units that is participating in this combat. |
| `reverse_engineer` | Reverse Engineer | — | after | TRIGGER (okno reakcji) | karty | — | Take that action card from the discard pile. |
| `rout` | Rout | — | at_start | PERMIT (pozwolenie) | walka | — | Your opponent must announce a retreat, if able. |
| `s_retreat1` | Skilled Retreat | — | at_start | — | ruch, walka, produkcja, żetony dowodzenia, karty | — | Move all of your ships from the active system into an adjacent system that does not contain another player's ships. The space combat ends i… |
| `s_retreat2` | Skilled Retreat | — | at_start | — | ruch, walka, produkcja, żetony dowodzenia, karty | — | Move all of your ships from the active system into an adjacent system that does not contain another player's ships. The space combat ends i… |
| `s_retreat3` | Skilled Retreat | — | at_start | — | ruch, walka, produkcja, żetony dowodzenia, karty | — | Move all of your ships from the active system into an adjacent system that does not contain another player's ships. The space combat ends i… |
| `s_retreat4` | Skilled Retreat | — | at_start | — | ruch, walka, produkcja, żetony dowodzenia, karty | — | Move all of your ships from the active system into an adjacent system that does not contain another player's ships. The space combat ends i… |
| `sabo1` | Sabotage | — | when | TRIGGER (okno reakcji) | karty | — | Cancel that action card. |
| `sabo2` | Sabotage | — | when | TRIGGER (okno reakcji) | karty | — | Cancel that action card. |
| `sabo3` | Sabotage | — | when | TRIGGER (okno reakcji) | karty | — | Cancel that action card. |
| `sabo4` | Sabotage | — | when | TRIGGER (okno reakcji) | karty | — | Cancel that action card. |
| `salvage` | Salvage | — | after | TRIGGER (okno reakcji) | ekonomia i płatności | — | Your opponent gives you all of their commodities. |
| `sanction` | Sanction | — | after | TRIGGER (okno reakcji) | produkcja, żetony dowodzenia, agenda i głosowanie | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, each player that voted for that out… |
| `scramble` | Scramble Frequency | — | after | TRIGGER (okno reakcji) | — | — | That player rerolls all of their dice. |
| `scuttle` | Scuttle | — | action | — | produkcja, ekonomia i płatności | — | Choose 1 or 2 of your non-fighter ships on the game board and return them to your reinforcements. Gain trade goods equal to the combined co… |
| `seize` | Seize Artifact | — | action | MODIFY (liczba/rzut) | planety i eksploracja | — | Choose 1 of your neighbors that has 1 or more relic fragments. That player must give you 1 relic fragment of your choice. |
| `sh1` | Shields Holding | — | before | TRIGGER (okno reakcji) | walka | — | Cancel up to 2 hits. |
| `sh2` | Shields Holding | — | before | TRIGGER (okno reakcji) | walka | — | Cancel up to 2 hits. |
| `sh3` | Shields Holding | — | before | TRIGGER (okno reakcji) | walka | — | Cancel up to 2 hits. |
| `sh4` | Shields Holding | — | before | TRIGGER (okno reakcji) | walka | — | Cancel up to 2 hits. |
| `silence_space` | In The Silence Of Space | — | after | TRIGGER (okno reakcji) | ruch | — | Choose 1 system. During this tactical action, your ships in the chosen system can move through systems that contain other players' ships. |
| `solar_flare` | Solar Flare | — | after | TRIGGER (okno reakcji) | ruch, walka | — | During the "Movement" step of this tactical action, other players cannot use SPACE CANNON against your ships. |
| `spy` | Spy | — | action | — | karty | — | Choose 1 player. That player gives you 1 random action card from their hand. |
| `stability` | Political Stability | — | when | TRIGGER (okno reakcji) | karty strategii i inicjatywa | — | Do not return your strategy card(s). You do not choose strategy cards during the next strategy phase. |
| `strategize1` | Strategize | — | action | — | karty strategii i inicjatywa | — | Perform the secondary ability of any readied or unchosen strategy card. |
| `strategize2` | Strategize | — | action | — | karty strategii i inicjatywa | — | Perform the secondary ability of any readied or unchosen strategy card. |
| `strategize3` | Strategize | — | action | — | karty strategii i inicjatywa | — | Perform the secondary ability of any readied or unchosen strategy card. |
| `strategize4` | Strategize | — | action | — | karty strategii i inicjatywa | — | Perform the secondary ability of any readied or unchosen strategy card. |
| `summit` | Summit | — | at_start | — | żetony dowodzenia | — | Gain 2 command tokens. |
| `tactical` | Tactical Bombardment | — | action | MODIFY (liczba/rzut) | walka, planety i eksploracja, status i odświeżanie | — | Choose 1 system that contains 1 or more of your units that have BOMBARDMENT. Exhaust each planet controlled by other players in that system. |
| `tech_rider` | Technology Rider | — | after | TRIGGER (okno reakcji) | technologie, agenda i głosowanie | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, research 1 technology. |
| `trade_rider` | Trade Rider | — | after | TRIGGER (okno reakcji) | ekonomia i płatności, agenda i głosowanie | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, gain 5 trade goods. |
| `unexpected` | Unexpected Action | — | action | — | produkcja, żetony dowodzenia | — | Remove 1 of your command tokens from the game board and return it to your reinforcements. |
| `unstable` | Unstable Planet | — | action | — | walka, planety i eksploracja, status i odświeżanie | — | Choose 1 hazardous planet. Exhaust that planet and destroy up to 3 infantry on it. |
| `upgrade` | Upgrade | — | after | TRIGGER (okno reakcji) | produkcja | — | Replace 1 of your cruisers in that system with 1 dreadnought from your reinforcements. |
| `uprising` | Uprising | — | action | — | ekonomia i płatności, planety i eksploracja, status i odświeżanie | — | Exhaust 1 non-home planet controlled by another player. Then gain trade goods equal to its resource value. |
| `veto` | Veto | — | when | TRIGGER (okno reakcji) | karty, agenda i głosowanie | — | Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead. |
| `veto3` | Veto | — | when | TRIGGER (okno reakcji) | karty, agenda i głosowanie | — | Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead. |
| `veto4` | Veto | — | when | TRIGGER (okno reakcji) | karty, agenda i głosowanie | — | Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead. |
| `war_effort` | War Effort | — | action | MODIFY (liczba/rzut) | produkcja | — | Place 1 cruiser from your reinforcements in a system that contains 1 or more of your ships. |
| `war_machine1` | War Machine | — | when | TRIGGER (okno reakcji) | produkcja | — | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |
| `war_machine2` | War Machine | — | when | TRIGGER (okno reakcji) | produkcja | — | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |
| `war_machine3` | War Machine | — | when | TRIGGER (okno reakcji) | produkcja | — | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |
| `war_machine4` | War Machine | — | when | TRIGGER (okno reakcji) | produkcja | — | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |
| `war_machinell` | War Machine | — | when | TRIGGER (okno reakcji) | produkcja | — | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |
| `war_rider` | Warfare Rider | — | after | TRIGGER (okno reakcji) | produkcja, agenda i głosowanie | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, place 1 dreadnought from your reinf… |
| `waylay` | Waylay | — | before | TRIGGER (okno reakcji) | walka, produkcja | — | Hits from this roll are produced against all ships (not just fighters). |

</details>

<details><summary>agendas (123)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `abolishment` | Judicial Abolishment | — | — | — | karty | — | Discard the elected law from play. |
| `absol_abolishment` | Judicial Abolishment | — | — | PERMIT (pozwolenie) | ekonomia i płatności, karty, agenda i głosowanie | — | For: At the start of the Agenda Phase, the speaker may spend 6 influence to discard any 1 law in play. Against: Reveal cards from the botto… |
| `absol_affirmation` | Affimation of Divine Right | — | — | FORBID (zakaz) | karty, planety i eksploracja, cele i punkty, status i odświeżanie, karty strategii i inicjatywa | — | For: Mecatol Rex is a legendary planet. At the end of each strategy phase, each other player must give the player who controls Mecatol Rex … |
| `absol_agreement` | Rearmament Agreement | — | — | MODIFY (liczba/rzut) | produkcja, żetony dowodzenia, planety i eksploracja, agenda i głosowanie | — | For: Each player places 1 mech from their reinforcements on a planet they control in their home system. The player who cast the most votes … |
| `absol_arbiter` | Imperial Arbiter | — | — | PERMIT (pozwolenie) | ekonomia i płatności, żetony dowodzenia, karty, agenda i głosowanie, karty strategii i inicjatywa | — | The elected player gains this card and gives each other player who voted for them 1 promissory note from their hand (from most votes to lea… |
| `absol_articleswar` | Articles of War | — | — | PERMIT (pozwolenie) | walka, produkcja, karty, planety i eksploracja, agenda i głosowanie | — | For: The player who cast the most votes "For" places 3 of their control tokens on this card. All mechs lose their printed abilities except … |
| `absol_artifact` | Ixthian Artifact | — | — | MODIFY (liczba/rzut) | ruch, walka, technologie, planety i eksploracja, agenda i głosowanie, cele i punkty | — | For: The speaker rolls 1 die. If the result is 7-10, each player may research 2 technologies. If the result is 1-6, destroy all units in Me… |
| `absol_censure` | Political Censure | — | — | FORBID (zakaz) | karty, agenda i głosowanie, cele i punkty | — | The elected player gains this card and 1 victory point. If they are speaker, the other player who cast the most votes for them takes the sp… |
| `absol_checks` | Checks and Balances | — | — | REPLACE (instead of) | karty, planety i eksploracja, agenda i głosowanie, cele i punkty, karty strategii i inicjatywa | — | For: The player who cast the most votes "For" places 1 of their control tokens on this card. When a player chooses a strategy card during t… |
| `absol_conscription` | Regulated Conscription | — | — | REPLACE (instead of) | produkcja, ekonomia i płatności, karty, planety i eksploracja, agenda i głosowanie, status i odświeżanie | — | For: The player who cast the most votes "For" gains 1 trade good for every industrial planet they control. When a player produces units, th… |
| `absol_constitution` | New Constitution | — | — | — | karty, agenda i głosowanie | — | For: Discard all laws in play, if any. The player who cast the most votes "For" takes the speaker token, then reveals cards from the bottom… |
| `absol_conventionswar` | Conventions of War | — | — | FORBID (zakaz) | walka, ekonomia i płatności, karty, planety i eksploracja, agenda i głosowanie | — | For: The player who cast the most votes "For" gains 1 trade good for each of their cultural planets. Players cannot use BOMBARDMENT against… |
| `absol_covert` | Covert Legislation | — | — | — | agenda i głosowanie | — | The speaker reads the eligible outcomes aloud (for, against, elect player, etc); the other players vote for these outcomes as if they were … |
| `absol_crisis` | Galactic Crisis Pact | — | — | REPLACE (instead of) | produkcja, ekonomia i płatności, żetony dowodzenia, agenda i głosowanie, karty strategii i inicjatywa | — | Each player may resolve the secondary ability of the elected strategy card without spending a command token; command tokens placed by the a… |
| `absol_defenseact` | Homeland Defense Act | — | — | REPLACE (instead of) | walka, karty, planety i eksploracja, agenda i głosowanie | — | For: When placing 1 or more PDS on a planet, players may place an additional PDS on that planet. The player who cast the most votes "For" m… |
| `absol_disarmament` | Compensated Disarmament | — | — | — | ekonomia i płatności, karty, planety i eksploracja, agenda i głosowanie | — | Remove each ground force on the elected planet; the player who controls that planet gains 1 trade good for each infantry removed and 2 trad… |
| `absol_emergency1` | Emergency Session | — | — | MODIFY (liczba/rzut) | karty, agenda i głosowanie | — | When this card is revealed, place it in the common play area. This card is not an agenda, and players do not vote on this card. After all o… |
| `absol_emergency2` | Emergency Session | — | — | MODIFY (liczba/rzut) | karty, agenda i głosowanie | — | When this card is revealed, place it in the common play area. This card is not an agenda, and players do not vote on this card. After all o… |
| `absol_emergency3` | Emergency Session | — | — | MODIFY (liczba/rzut) | karty, agenda i głosowanie | — | When this card is revealed, place it in the common play area. This card is not an agenda, and players do not vote on this card. After all o… |
| `absol_emergency4` | Emergency Session | — | — | MODIFY (liczba/rzut) | karty, agenda i głosowanie | — | When this card is revealed, place it in the common play area. This card is not an agenda, and players do not vote on this card. After all o… |
| `absol_equality` | Economic Equality | — | — | PERMIT (pozwolenie) | ekonomia i płatności, agenda i głosowanie | — | Each player returns all their trade goods to the supply. All players have a commodity value of 3. The player that cast the most votes "For"… |
| `absol_execution` | Public Execution | — | — | PERMIT (pozwolenie) | karty, planety i eksploracja, agenda i głosowanie, status i odświeżanie | — | The elected player exhausts all of their planets, then reveals the action cards in their hand. The players that voted for the elected playe… |
| `absol_formation` | Committee Formation | — | — | PERMIT (pozwolenie) | karty, agenda i głosowanie | — | The elected player gains this card and gives each other player who voted for them 1 promissory note from their hand (in order of most votes… |
| `absol_government` | Representative Government | — | — | REPLACE (instead of) | ekonomia i płatności, planety i eksploracja, agenda i głosowanie, status i odświeżanie, karty strategii i inicjatywa | — | For: The player who cast the most votes "For" takes the speaker token. When casting votes, players cast votes equal to the number of planet… |
| `absol_grant` | Research Grant Allocation | — | — | PERMIT (pozwolenie) | ekonomia i płatności, technologie, agenda i głosowanie | — | The elected player researches any 1 non-faction technology. The other player who cast the most votes for the elected player may spend 2 tra… |
| `absol_hyperlane` | Hyperlane Development Program | — | — | PERMIT (pozwolenie) | ruch, walka, produkcja, ekonomia i płatności, technologie, planety i eksploracja, agenda i głosowanie, status i odświeżanie, karty strategii i inicjatywa | — | For: The player who cast the most votes "For" may research 1 propulsion technology. Non-anomaly systems that contain no planets do not cost… |
| `absol_incentive` | Incentive Program | — | — | PERMIT (pozwolenie) | karty, agenda i głosowanie, cele i punkty | — | For: Draw and reveal 1 stage I public objective from the deck and place it near the public objectives. The player who cast the most votes "… |
| `absol_leak` | Classified Document Leak | — | — | PERMIT (pozwolenie) | karty, agenda i głosowanie, cele i punkty | — | The elected secret objective becomes a public objective. The player who cast the most votes for that objective may immediately score it, if… |
| `absol_limits` | Term Limits | — | — | FORBID (zakaz) | karty, planety i eksploracja, agenda i głosowanie, status i odświeżanie, karty strategii i inicjatywa | — | For: The speaker places 1 of their control tokens on this card. When a player takes or receives the speaker token, they place 1 of their co… |
| `absol_measures` | Unconventional Measures | — | — | — | żetony dowodzenia, karty, agenda i głosowanie, status i odświeżanie, karty strategii i inicjatywa | — | For: Each player who voted "For" draws 2 action cards. Each player who voted "Against" gains 1 command token. Against: Each player who vote… |
| `absol_minsantique` | Minister of Antiquities | — | — | REPLACE (instead of) | ekonomia i płatności, żetony dowodzenia, karty, planety i eksploracja, cele i punkty, karty strategii i inicjatywa | — | The elected player gains this card. The owner of this card may resolve the secondary ability of the Imperial strategy card without spending… |
| `absol_minscomm` | Minister of Commerce | — | — | PERMIT (pozwolenie) | ekonomia i płatności, żetony dowodzenia, karty strategii i inicjatywa | — | The elected player gains this card. The owner of this card may resolve the secondary ability of the Trade strategy card without spending a … |
| `absol_minsexp` | Minister of Exploration | — | — | MODIFY (liczba/rzut) | żetony dowodzenia, planety i eksploracja, karty strategii i inicjatywa | — | The elected player gains this card. The owner of this card gains 1 additional command token when resolving the secondary ability of the Lea… |
| `absol_minsindus` | Minister of Industry | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności, żetony dowodzenia, karty strategii i inicjatywa | — | The elected player gains this card. The owner of this card may resolve the secondary ability of the Construction strategy card without spen… |
| `absol_minspeace` | Minister of Peace | — | — | MODIFY (liczba/rzut) | ekonomia i płatności, żetony dowodzenia, karty, karty strategii i inicjatywa | — | The elected player gains this card. The owner of this card may resolve the secondary ability of the Diplomacy strategy card without spendin… |
| `absol_minspolicy` | Minister of Policy | — | — | REPLACE (instead of) | ekonomia i płatności, żetony dowodzenia, technologie, karty, status i odświeżanie, karty strategii i inicjatywa | — | The elected player gains this card. The owner of this card may use the secondary ability of the Politics strategy card without spending a c… |
| `absol_minssci` | Minister of Sciences | — | — | PERMIT (pozwolenie) | ekonomia i płatności, żetony dowodzenia, technologie, karty strategii i inicjatywa | — | The elected player gains this card. The owner of this card may resolve the secondary ability of the Technology strategy card without spendi… |
| `absol_minswar` | Minister of War | — | — | PERMIT (pozwolenie) | ekonomia i płatności, żetony dowodzenia, status i odświeżanie, karty strategii i inicjatywa | — | The elected player gains this card. The owner of this card may resolve the secondary ability of the Warfare strategy card without spending … |
| `absol_miscount` | Miscount Disclosed | — | — | MODIFY (liczba/rzut) | karty, agenda i głosowanie | — | When this agenda is revealed, if there are no laws in play, discard this card and reveal another agenda from the top of the deck. Vote on t… |
| `absol_mutiny` | Mutiny | — | — | MODIFY (liczba/rzut) | karty, agenda i głosowanie, cele i punkty, status i odświeżanie, karty strategii i inicjatywa | — | For: Exhaust the Politics strategy card. The player who cast the most votes "For" takes the speaker token. All players who voted "For" gain… |
| `absol_nexus` | Nexus Sovereignty | — | — | PERMIT (pozwolenie) | ruch, walka, ekonomia i płatności, planety i eksploracja, agenda i głosowanie | — | For: Alpha and beta wormholes in the wormhole nexus have no effect on movement. The player who controls Mallice may spend 1 influence at an… |
| `absol_operations` | Clandestine Operations | — | — | — | produkcja, żetony dowodzenia, agenda i głosowanie, status i odświeżanie, karty strategii i inicjatywa | — | For: The player who cast the most votes "For" gains 2 command tokens and takes the speaker token. Then, each player removes 1 command token… |
| `absol_pax` | Pax Magnifica, Bellum Gloriosum | — | — | FORBID (zakaz) | produkcja, żetony dowodzenia, karty, planety i eksploracja, agenda i głosowanie, status i odświeżanie, karty strategii i inicjatywa | — | For: Exhaust the Warfare strategy card. The player who cast the most votes "For" adds 2 command tokens from their reinforcements to their s… |
| `absol_prophecy` | Prophecy of Ixth | — | — | MODIFY (liczba/rzut) | walka, produkcja, technologie, karty | — | The elected player gains this card. The owner of this card may ignore the prerequisites on fighter unit upgrade technologies and applies +1… |
| `absol_recon` | Wormhole Reconstruction | — | — | PERMIT (pozwolenie) | ruch, produkcja, ekonomia i płatności, żetony dowodzenia, planety i eksploracja, agenda i głosowanie | — | For: The player who cast the most votes "For" places 1 control token on this card. Players may treat alpha wormholes as beta wormholes duri… |
| `absol_redistribution` | Colonial Redistribution | — | — | MODIFY (liczba/rzut) | produkcja, planety i eksploracja, cele i punkty | — | Remove each unit on the elected planet. The player who controls that planet places the removed units on 1 or more planets they control in t… |
| `absol_reduction` | Arms Reduction | — | — | PERMIT (pozwolenie) | walka, produkcja, ekonomia i płatności, żetony dowodzenia, technologie, agenda i głosowanie | — | For: Each player destroys all of their dreadnoughts and half of their cruisers (rounding up). Players gain 2 trade goods for each dreadnoug… |
| `absol_regulations` | Fleet Regulations | — | — | PERMIT (pozwolenie) | produkcja, żetony dowodzenia, planety i eksploracja, agenda i głosowanie | — | For: The player who cast the most votes "For" places 1 of their control tokens on this card. A player whose control token is on this card c… |
| `absol_revolution` | Anti-Intellectual Revolution | — | — | — | walka, ekonomia i płatności, technologie, status i odświeżanie, karty strategii i inicjatywa | — | For: Each player who voted "For" or abstained returns 1 technology they own with the most prerequisites to their technology decks. Double t… |
| `absol_sanctions` | Executive Sanctions | — | — | PERMIT (pozwolenie) | karty, planety i eksploracja, agenda i głosowanie | — | For: The player who cast the most votes “For” places 1 of their control tokens on this card. A player whose control token is on this card c… |
| `absol_schematics` | Publicize Weapon Schematics | — | — | PERMIT (pozwolenie) | walka, technologie, karty, agenda i głosowanie | — | When this agenda is revealed, if there are no eligible technologies in play, discard this card and reveal another agenda from the top of th… |
| `absol_secret` | Archived Secret | — | — | — | karty, agenda i głosowanie, cele i punkty | — | The elected player draws 2 secret objectives, then gives 1 promissory note from their hand to the other player who cast the most votes for … |
| `absol_seeds` | Seed of an Empire | — | — | PERMIT (pozwolenie) | produkcja, żetony dowodzenia, karty, agenda i głosowanie, cele i punkty | — | For: The player with the most victory points (speaker breaks ties) gains the speaker token and 1 victory point, then gives 1 promissory not… |
| `absol_shared` | Shared Research | — | — | PERMIT (pozwolenie) | ruch, produkcja, żetony dowodzenia, technologie, planety i eksploracja, agenda i głosowanie | — | For: The player who cast the most votes "For" may explore any frontier tokens in systems that contain anomalies and their ships. During tac… |
| `absol_sites` | Preservation of Historical Sites | — | — | PERMIT (pozwolenie) | ekonomia i płatności, planety i eksploracja, agenda i głosowanie | — | For: The player who cast the most votes "For" gains 2 trade goods for each legendary planet or planet with attachments that they control. P… |
| `absol_spending` | Discretionary Spending | — | — | FORBID (zakaz) | produkcja, ekonomia i płatności, technologie, karty, planety i eksploracja, agenda i głosowanie | — | For: All players gain trade goods equal to the number of planets they control. The player who cast the most votes "For" replenishes their c… |
| `absol_standardization` | Armed Forces Standardization | — | — | — | produkcja, żetony dowodzenia, karty, agenda i głosowanie | — | The elected player places command tokens from their reinforcements until they they have 3 tokens in their tactic pool, 3 tokens in their fl… |
| `absol_swords` | Swords to Plowshares | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności, planety i eksploracja, agenda i głosowanie | — | For: Each player removes half of their infantry on each planet they control, rounding down. Each player gains trade goods equal to the numb… |
| `absol_travelban` | Enforced Travel Ban | — | — | MODIFY (liczba/rzut) | ruch, ekonomia i płatności, karty, planety i eksploracja, agenda i głosowanie | — | For: The player who cast the most votes "For" places 3 of their control tokens on this card. Alpha and beta wormholes have no effect during… |
| `absol_warrant` | Search Warrant | — | — | REPLACE (instead of) | karty, planety i eksploracja, agenda i głosowanie, cele i punkty | — | The non-elected player who cast the most votes for the elected player places 1 of their control tokens on this card. The elected player gai… |
| `absol_whresearch` | Wormhole Research | — | — | MODIFY (liczba/rzut) | ruch, walka, produkcja, żetony dowodzenia, technologie, agenda i głosowanie | — | For: Players with ships in systems that contain 1 or more wormholes may research a technology with no more than 1 prerequisite per type of … |
| `arbiter` | Imperial Arbiter | — | — | PERMIT (pozwolenie) | karty, karty strategii i inicjatywa | — | The elected player gains this card. At the end of the strategy phase, the owner of this card may discard this card to swap 1 of their strat… |
| `arms_reduction` | Arms Reduction | — | — | — | walka, technologie, planety i eksploracja, status i odświeżanie | — | For: Each player destroys all but 2 of their dreadnoughts and all but 4 of their cruisers. Against: At the start of the next strategy phase… |
| `articles_war` | Articles of War | — | — | — | walka, ekonomia i płatności | — | For: All mechs lose their printed abilities except for SUSTAIN DAMAGE. Against: Each player that voted "For" gains 3 trade goods. All mechs… |
| `artifact` | Ixthian Artifact | — | — | MODIFY (liczba/rzut) | ruch, walka, technologie, agenda i głosowanie | — | For: The speaker rolls 1 die. If the result is 6-10, each player may research 2 technologies. If the result is 1-5, destroy all units in Me… |
| `censure` | Political Censure | — | — | FORBID (zakaz) | karty, cele i punkty | — | The elected player gains this card and 1 victory point. The elected player cannot play action cards. If the owner of this card loses this c… |
| `checks` | Checks and Balances | — | — | PERMIT (pozwolenie) | planety i eksploracja, agenda i głosowanie, karty strategii i inicjatywa | — | For: When a player chooses a strategy card during the strategy phase, they give that strategy card to another player who does not have 1 (o… |
| `cladenstine` | Clandestine Operations | — | — | — | produkcja, żetony dowodzenia | — | For: Each player removes 2 command tokens from their command sheet and returns those tokens to their reinforcements. Against: Each player r… |
| `classified` | Classified Document Leaks | — | — | — | cele i punkty | — | The elected secret objective becomes a public objective - place it near the other public objectives in the common play area. The elected se… |
| `committee` | Committee Formation | — | — | PERMIT (pozwolenie) | karty, agenda i głosowanie | — | The elected player gains this card. Before players vote on an agenda that requires a player to be elected, the owner of this card may disca… |
| `conscription` | Regulated Conscription | — | — | REPLACE (instead of) | produkcja | — | For: When a player produces units, they produce only 1 fighter and infantry for its cost instead of 2. Against: No effect. When a player pr… |
| `constitution` | New Constitution | — | — | — | karty, planety i eksploracja, agenda i głosowanie, status i odświeżanie | — | (When this agenda is revealed, if there are no laws in play, discard this card and reveal another agenda from the top of the deck.) For: Di… |
| `conventions` | Conventions of War | — | — | FORBID (zakaz) | walka, karty, planety i eksploracja | — | For: Players cannot use BOMBARDMENT against units that are on cultural planets. Against: Each player that voted "Against" discards all of t… |
| `core_mining` | Core Mining | — | — | — | walka, ekonomia i płatności, planety i eksploracja | — | Attach this card to the elected planet's card. Then, destroy 1 infantry on the planet. The resource value of this planet is increased by 2. |
| `covert` | Covert Legislation | — | — | — | — | — |  |
| `crisis` | Galactic Crisis Pact | — | — | REPLACE (instead of) | produkcja, ekonomia i płatności, żetony dowodzenia, karty strategii i inicjatywa | — | Each player may perform the secondary ability of the elected strategy card without spending a command token - command tokens placed by the … |
| `crown_of_emphidia` | The Crown of Emphidia | — | — | — | planety i eksploracja, cele i punkty | — | The elected player gains this card and 1 victory point. A player gains this card and 1 victory point after they gain control of a planet in… |
| `crown_of_thalnos` | The Crown of Thalnos | — | — | MODIFY (liczba/rzut) | walka, produkcja | — | The elected player gains this card. During each combat round, the owner of this card may reroll any number of dice; they must destroy each … |
| `defense_act` | Homeland Defense Act | — | — | PERMIT (pozwolenie) | walka, planety i eksploracja | — | For: Each player can have any number of PDS units on planets they control. Against: Each player destroys 1 of their PDS units. Each player … |
| `demilitarized_zone` | Demilitarized Zone | — | — | FORBID (zakaz) | walka, produkcja, planety i eksploracja | — | Attach this card to the elected planet's card. Then, destroy all units on that planet. Player's units cannot land, be produced, or be place… |
| `disarmament` | Compensated Disarmament | — | — | — | walka, ekonomia i płatności, planety i eksploracja | — | Destroy each ground force on the elected planet. For each unit that was destroyed, the player who control that planet gains 1 trade good. |
| `economic_equality` | Economic Equality | — | — | — | ekonomia i płatności | — | For: Each player returns all of their trade goods to the supply. Then, each player gains 5 trade goods. Against: Each player returns all of… |
| `execution` | Public Execution | — | — | FORBID (zakaz) | karty, agenda i głosowanie | — | The elected player discards all of their action cards. If they have the speaker token, they give it to the player on their left. The electe… |
| `grant_reallocation` | Research Grant Reallocation | — | — | — | produkcja, żetony dowodzenia, technologie | — | The elected player gains any 1 technology of their choice. Then, for each prerequisite on that technology, they remove 1 token from their f… |
| `holy_planet_of_ixth` | Holy Planet of Ixth | — | — | FORBID (zakaz) | produkcja, planety i eksploracja, cele i punkty | — | Attach this card to the elected planet's card. The planet's owner gains 1 victory point. Units on this planet cannot use PRODUCTION. When a… |
| `incentive` | Incentive Program | — | — | — | karty, cele i punkty | — | For: Draw and reveal 1 stage I public objective from the deck and place it near the public objectives. Against: Draw and reveal 1 stage II … |
| `minister_antiquities` | Minister of Antiquities | — | — | — | planety i eksploracja | — | The elected player gains 1 relic. |
| `minister_commerce` | Minister of Commerce | — | — | — | ekonomia i płatności | — | The elected player gains this card. After the owner of this card replenishes commodities, they gain 1 trade good for each player that is th… |
| `minister_exploration` | Minister of Exploration | — | — | — | ekonomia i płatności, planety i eksploracja | — | The elected player gains this card. When the owner of this card gains control of a planet, they gain 1 trade good. When you gain control of… |
| `minister_industry` | Minister of Industry | — | — | PERMIT (pozwolenie) | produkcja | — | The elected player gains this card. When the owner of this card places a space dock in a system, their units in that system may use their P… |
| `minister_peace` | Minister of Peace | — | — | MODIFY (liczba/rzut) | karty | — | The elected player gains this card. After a player activates a system that contains 1 or more of a different player's units, the owner of t… |
| `minister_policy` | Minister of Policy | — | — | — | karty, status i odświeżanie | — | The elected player gains this card. At the end of the status phase, the owner of this card draws 1 action card. At the end of the status ph… |
| `minister_sciences` | Minister of Sciences | — | — | — | ekonomia i płatności, technologie, karty strategii i inicjatywa | — | The elected player gains this card. When the owner of this card resolves the primary or secondary ability of the "Technology" strategy card… |
| `minister_war` | Minister of War | — | — | MODIFY (liczba/rzut) | produkcja, żetony dowodzenia, karty | — | The elected player gains this card. The owner of this card may discard this card after performing an action to remove 1 of their command to… |
| `miscount` | Miscount Disclosed | — | — | — | karty, agenda i głosowanie | — | (When this agenda is revealed, if there are no laws in play, discard this card and reveal another agenda from the top of the deck.) Vote on… |
| `mutiny` | Mutiny | — | — | — | cele i punkty | — | For: Each player that voted "For" gains 1 victory point. Against: Each player that voted "For" loses 1 victory point. |
| `nexus` | Nexus Sovereignty | — | — | — | ruch | — | For: Alpha and beta wormholes in the wormhole nexus have no effect during movement. Against: Place a gamma wormhole token in the Mecatol Re… |
| `plowshares` | Swords to Plowshares | — | — | — | walka, produkcja, ekonomia i płatności, planety i eksploracja | — | For: Each player destroys half of their infantry on each planet they control, rounded up. Then, each player gains trade goods equal to the … |
| `prophecy` | Prophecy of Ixth | — | — | MODIFY (liczba/rzut) | walka, produkcja, karty | — | The elected player gains this card. The owner of this card applies +1 to the result of their fighter's combat rolls. When the owner of this… |
| `rearmament` | Rearmament Agreement | — | — | — | produkcja, planety i eksploracja | — | For: Each player places 1 mech from their reinforcements on a planet they control in their home system. Against: Each player replaces each … |
| `redistribution` | Colonial Redistribution | — | — | PERMIT (pozwolenie) | walka, produkcja, planety i eksploracja, cele i punkty | — | Destroy each unit on the elected planet. Then, the player who controls that planet chooses 1 player with the fewest victory points - that p… |
| `regulations` | Fleet Regulations | — | — | FORBID (zakaz) | produkcja, żetony dowodzenia | — | For: Each player cannot have more than 4 tokens in their fleet pool. Against: Each player places 1 command token from their reinforcements … |
| `rep_govt` | Representative Government | — | — | REPLACE (instead of) | planety i eksploracja, agenda i głosowanie, status i odświeżanie | — | For: Players cannot exhaust planets to cast votes during the agenda phase. each player may cast 1 vote on each agenda instead. Players cann… |
| `representative_government` | Representative Government (Base Game) | — | — | REPLACE (instead of) | planety i eksploracja, agenda i głosowanie, status i odświeżanie | — | For: Players cannot exhaust planets to cast votes during the agenda phase. Each player may cast 1 vote on each agenda instead. Against: At … |
| `revolution` | Anti-Intellectual Revolution | — | — | — | walka, technologie, planety i eksploracja, status i odświeżanie | — | For: After a player researches a technology, that player must destroy 1 of their non-fighter ships. Against: At the start of the next strat… |
| `rt_biotic` | Research Team: Biotic | — | — | PERMIT (pozwolenie) | technologie, planety i eksploracja, status i odświeżanie | — | Attach this card to the elected planet's card. When the owner of this planet researches technology, they may exhaust this card to ignore 1 … |
| `rt_cybernetic` | Research Team: Cybernetic | — | — | PERMIT (pozwolenie) | technologie, planety i eksploracja, status i odświeżanie | — | Attach this card to the elected planet's card. When the owner of this planet researches technology, they may exhaust this card to ignore 1 … |
| `rt_propulsion` | Research Team: Propulsion | — | — | PERMIT (pozwolenie) | technologie, planety i eksploracja, status i odświeżanie | — | Attach this card to the elected planet's card. When the owner of this planet researches technology, they may exhaust this card to ignore 1 … |
| `rt_warfare` | Research Team: Warfare | — | — | PERMIT (pozwolenie) | technologie, planety i eksploracja, status i odświeżanie | — | Attach this card to the elected planet's card. When the owner of this planet researches technology, they may exhaust this card to ignore 1 … |
| `sanctions` | Executive Sanctions | — | — | PERMIT (pozwolenie) | karty | — | For: Each player can have a maximum of 3 action cards in their hand. Against: Each player discards 1 random action card from their hand. Ea… |
| `schematics` | Publicize Weapon Schematics | — | — | PERMIT (pozwolenie) | walka, technologie, karty | — | For: If any player owns a war sun technology, all players may ignore all prerequisites on war sun technologies. All war suns lose SUSTAIN D… |
| `secret` | Archived Secret | — | — | — | karty, cele i punkty | — | The elected player draws 1 secret objective. |
| `seed_empire` | Seed of an Empire | — | — | — | cele i punkty | — | For: The player with the most victory points gains 1 victory point. Against: The player with the fewest victory points gains 1 victory poin… |
| `senate_sanctuary` | Senate Sanctuary | — | — | — | ekonomia i płatności, planety i eksploracja | — | Attach this card to the elected planet's card. The influence value of this planet is increased by 2. |
| `shard_of_the_throne` | Shard of the Throne | — | — | — | walka, cele i punkty | — | The elected player gains this card and 1 victory point. A player gains this card and 1 victory point when they win a combat against the own… |
| `shared_research` | Shared Research | — | — | PERMIT (pozwolenie) | ruch, produkcja, żetony dowodzenia, technologie | — | For: Each player's units can move through nebulae. Against: Each player places a command token from their reinforcements in their home syst… |
| `standardization` | Armed Forces Standardization | — | — | — | produkcja, żetony dowodzenia | — | The elected player place command tokens from their reinforcements so that they have 3 tokens in their tactic pool, 3 tokens in their fleet … |
| `terraforming_initiative` | Terraforming Initiative | — | — | — | ekonomia i płatności, planety i eksploracja, karty strategii i inicjatywa | — | Attach this card to the elected planet's card. The resource and influence values of this planet are increased by 1. |
| `travel_ban` | Enforced Travel Ban | — | — | — | ruch, walka | — | For: Alpha and beta wormholes have no effect during movement. Against: Destroy each PDS in or adjacent to a system that contains a wormhole… |
| `unconventional` | Unconventional Measures | — | — | — | karty | — | For: Each player that voted "For" draws 2 action cards. Against: Each player that voted "For" discards all of their action cards. |
| `warrant` | Search Warrant | — | — | — | karty, cele i punkty | — | The elected player gains this card and draws 2 secret objectives. The owner of this card plays with their secret objectives revealed. You p… |
| `wormhole_recon` | Wormhole Reconstruction | — | — | MODIFY (liczba/rzut) | ruch, produkcja, żetony dowodzenia | — | For: All systems that contain either an alpha or beta wormhole are adjacent to each other. Against: Each player places a command token from… |
| `wormhole_research` | Wormhole Research | — | — | MODIFY (liczba/rzut) | ruch, walka, produkcja, żetony dowodzenia, technologie | — | For: Each player who has 1 or more ships in a system that contains a wormhole may research 1 technology. Then, destroy all ships in systems… |

</details>

<details><summary>explores (80)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `aw1` | Abandoned Warehouses | — | — | PERMIT (pozwolenie) | ekonomia i płatności | — | You may gain 2 commodities, or you may convert up to 2 of your commodities to trade goods. |
| `aw2` | Abandoned Warehouses | — | — | PERMIT (pozwolenie) | ekonomia i płatności | — | You may gain 2 commodities, or you may convert up to 2 of your commodities to trade goods. |
| `aw3` | Abandoned Warehouses | — | — | PERMIT (pozwolenie) | ekonomia i płatności | — | You may gain 2 commodities, or you may convert up to 2 of your commodities to trade goods. |
| `aw4` | Abandoned Warehouses | — | — | PERMIT (pozwolenie) | ekonomia i płatności | — | You may gain 2 commodities, or you may convert up to 2 of your commodities to trade goods. |
| `biotic` | Biotic Research Facility | — | — | REPLACE (instead of) | ekonomia i płatności, technologie, planety i eksploracja | — | This planet has a green technology specialty. If this planet already has a technology specialty, this planet's resource and influence value… |
| `cm1` | Core Mine | — | — | — | ekonomia i płatności, planety i eksploracja | — | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 trade good. |
| `cm2` | Core Mine | — | — | — | ekonomia i płatności, planety i eksploracja | — | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 trade good. |
| `cm3` | Core Mine | — | — | — | ekonomia i płatności, planety i eksploracja | — | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 trade good. |
| `crf1` | Cultural Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `crf2` | Cultural Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `crf3` | Cultural Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `crf4` | Cultural Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `crf5` | Cultural Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `crf6` | Cultural Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `crf7` | Cultural Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `crf8` | Cultural Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `crf9` | Cultural Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `cybernetic` | Cybernetic Research Facility | — | — | REPLACE (instead of) | ekonomia i płatności, technologie, planety i eksploracja | — | This planet has a yellow technology specialty. If this planet already has a technology specialty, this planet's resource and influence valu… |
| `dmz` | Demilitarized Zone | — | — | FORBID (zakaz) | produkcja, planety i eksploracja, agenda i głosowanie | — | Return all structures on this planet to your reinforcements. Then, return all ground forces on this planet to the space area. Attach: Units… |
| `ds` | Dyson Sphere | — | — | — | ekonomia i płatności, planety i eksploracja | — | This planet's resource value is increased by 2 and its influence value is increased by 1. |
| `dv1` | Derelict Vessel | — | — | — | karty, planety i eksploracja, cele i punkty | — | Draw 1 secret objective. |
| `dv2` | Derelict Vessel | — | — | — | karty, planety i eksploracja, cele i punkty | — | Draw 1 secret objective. |
| `dw` | Dead World | — | — | — | karty, planety i eksploracja | — | Draw 1 relic. |
| `ed1` | Enigmatic Device | — | — | PERMIT (pozwolenie) | ekonomia i płatności, technologie | — | Place this card faceup in your play area. ACTION: You may spend 6 resource and purge this card to research 1 technology. |
| `ed2` | Enigmatic Device | — | — | PERMIT (pozwolenie) | ekonomia i płatności, technologie | — | Place this card faceup in your play area. ACTION: You may spend 6 resource and purge this card to research 1 technology. |
| `ent` | Entropic Field | — | — | — | ekonomia i płatności, żetony dowodzenia | — | Gain 1 command token and 2 trade goods. |
| `exp1` | Expedition | — | — | — | planety i eksploracja, status i odświeżanie | — | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, ready this planet. |
| `exp2` | Expedition | — | — | — | planety i eksploracja, status i odświeżanie | — | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, ready this planet. |
| `exp3` | Expedition | — | — | — | planety i eksploracja, status i odświeżanie | — | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, ready this planet. |
| `fb1` | Functioning Base | — | — | PERMIT (pozwolenie) | ekonomia i płatności, karty | — | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to draw 1 action card. |
| `fb2` | Functioning Base | — | — | PERMIT (pozwolenie) | ekonomia i płatności, karty | — | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to draw 1 action card. |
| `fb3` | Functioning Base | — | — | PERMIT (pozwolenie) | ekonomia i płatności, karty | — | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to draw 1 action card. |
| `fb4` | Functioning Base | — | — | PERMIT (pozwolenie) | ekonomia i płatności, karty | — | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to draw 1 action card. |
| `frln1` | Freelancers | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności | — | You may produce 1 unit in this system. You may spend influence as if it were resources to produce this unit. |
| `frln2` | Freelancers | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności | — | You may produce 1 unit in this system. You may spend influence as if it were resources to produce this unit. |
| `frln3` | Freelancers | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności | — | You may produce 1 unit in this system. You may spend influence as if it were resources to produce this unit. |
| `gamma` | Gamma Relay | — | — | — | ruch | — | Place a gamma wormhole token in this system. Then, purge this card. |
| `gw` | Gamma Wormhole | — | — | — | ruch | — | Place a gamma wormhole token in this system. Then, purge this card. |
| `hrf1` | Hazardous Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `hrf2` | Hazardous Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `hrf3` | Hazardous Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `hrf4` | Hazardous Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `hrf5` | Hazardous Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `hrf6` | Hazardous Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `hrf7` | Hazardous Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `ion` | Ion Storm | — | — | MODIFY (liczba/rzut) | ruch, walka | — | Place the ion storm token in this system with either side faceup. Then, place this card in the common play area. At the end of the "Move Sh… |
| `irf1` | Industrial Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |
| `irf2` | Industrial Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |
| `irf3` | Industrial Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |
| `irf4` | Industrial Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |
| `irf5` | Industrial Relic Fragment | — | — | — | planety i eksploracja | — | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |
| `kel1` | Keleres Ship | — | — | — | żetony dowodzenia | — | Gain 2 command tokens. |
| `kel2` | Keleres Ship | — | — | — | żetony dowodzenia | — | Gain 2 command tokens. |
| `lc1` | Lost Crew | — | — | — | karty | — | Draw 2 action cards. |
| `lc2` | Lost Crew | — | — | — | karty | — | Draw 2 action cards. |
| `lf1` | Local Fabricators | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności, planety i eksploracja | — | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to place 1 mech from your reinforcements on this planet. |
| `lf2` | Local Fabricators | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności, planety i eksploracja | — | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to place 1 mech from your reinforcements on this planet. |
| `lf3` | Local Fabricators | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności, planety i eksploracja | — | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to place 1 mech from your reinforcements on this planet. |
| `lf4` | Local Fabricators | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności, planety i eksploracja | — | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to place 1 mech from your reinforcements on this planet. |
| `ls` | Lazax Survivors | — | — | — | ekonomia i płatności, planety i eksploracja | — | This planet's resource value is increased by 1 and its influence value is increased by 2. |
| `majent` | Major Entropic Field | — | — | — | ekonomia i płatności, żetony dowodzenia | — | Gain 1 command token and 3 trade goods. |
| `minent` | Minor Entropic Field | — | — | — | ekonomia i płatności, żetony dowodzenia | — | Gain 1 command token and 1 trade good. |
| `mirage` | Mirage | — | — | — | planety i eksploracja, status i odświeżanie | — | Place the Mirage planet token in this system. Gain the Mirage planet card and ready it. Then, purge this card. |
| `mo1` | Mercenary Outfit | — | — | PERMIT (pozwolenie) | produkcja, planety i eksploracja | — | You may place 1 infantry from your reinforcements on this planet. |
| `mo2` | Mercenary Outfit | — | — | PERMIT (pozwolenie) | produkcja, planety i eksploracja | — | You may place 1 infantry from your reinforcements on this planet. |
| `mo3` | Mercenary Outfit | — | — | PERMIT (pozwolenie) | produkcja, planety i eksploracja | — | You may place 1 infantry from your reinforcements on this planet. |
| `ms1` | Merchant Station | — | — | PERMIT (pozwolenie) | ekonomia i płatności | — | You may replenish your commodities, or you may convert your commodities to trade goods. |
| `ms2` | Merchant Station | — | — | PERMIT (pozwolenie) | ekonomia i płatności | — | You may replenish your commodities, or you may convert your commodities to trade goods. |
| `mw` | Mining World | — | — | — | ekonomia i płatności, planety i eksploracja | — | This planet's resource value is increased by 2. |
| `propulsion` | Propulsion Research Facility | — | — | REPLACE (instead of) | ekonomia i płatności, technologie, planety i eksploracja | — | This planet has a blue technology specialty. If this planet already has a technology specialty, this planet's resource and influence values… |
| `pw` | Paradise World | — | — | — | ekonomia i płatności, planety i eksploracja | — | This planet's influence value is increased by 2. |
| `rw` | Rich World | — | — | — | ekonomia i płatności, planety i eksploracja | — | This planet's resource value is increased by 1. |
| `toe` | Tomb of Emphidia | — | — | PERMIT (pozwolenie) | ekonomia i płatności, planety i eksploracja | — | This planet's influence value is increased by 1. If the player who has the "Crown of Emphidia" relic has control of this planet, they can u… |
| `urf1` | Unknown Relic Fragment | — | — | — | planety i eksploracja | — | The card counts as a relic fragment of any type. |
| `urf2` | Unknown Relic Fragment | — | — | — | planety i eksploracja | — | The card counts as a relic fragment of any type. |
| `urf3` | Unknown Relic Fragment | — | — | — | planety i eksploracja | — | The card counts as a relic fragment of any type. |
| `vfs1` | Volatile Fuel Source | — | — | — | żetony dowodzenia, planety i eksploracja | — | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 command token. |
| `vfs2` | Volatile Fuel Source | — | — | — | żetony dowodzenia, planety i eksploracja | — | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 command token. |
| `vfs3` | Volatile Fuel Source | — | — | — | żetony dowodzenia, planety i eksploracja | — | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 command token. |
| `warfare` | Warfare Research Facility | — | — | REPLACE (instead of) | ekonomia i płatności, technologie, planety i eksploracja | — | This planet has a red technology specialty. If this planet already has a technology specialty, this planet's resource and influence values … |

</details>

<details><summary>relics (24)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `bookoflatvinia` | Book of Latvinia | — | — | — | technologie, planety i eksploracja, agenda i głosowanie, cele i punkty | — | When you gain this card, research up to 2 technologies that have no prerequisites. > ACTION: Purge this card; if you control planets that h… |
| `circletofthevoid` | Circlet of the Void | — | — | — | ruch, walka, planety i eksploracja, status i odświeżanie | — | Your units do not roll for gravity rifts, and you ignore the effects of all other anomalies on movement. ACTION: Exhaust this card to explo… |
| `codex` | The Codex | — | — | — | karty | — | ACTION: Purge this card to take up to 3 action cards of your choice from the action card discard pile. |
| `dominusorb` | Dominus Orb | — | — | PERMIT (pozwolenie) | ruch, żetony dowodzenia | — | Before you move units during a tactical action, you may purge this card to move and transport units that are in systems that contain 1 of y… |
| `dynamiscore` | Dynamis Core | — | — | — | ekonomia i płatności | — | While this card is in your play area, your commodity value is increased by 2. ACTION: Gain trade goods equal to your commodity value, then … |
| `emelpar` | Scepter of Emelpar | — | — | REPLACE (instead of) | produkcja, ekonomia i płatności, żetony dowodzenia, status i odświeżanie | — | When you would spend a token from your strategy pool, you may exhaust this card to spend a token from your reinforcements instead. |
| `emphidia` | The Crown of Emphidia | — | — | PERMIT (pozwolenie) | planety i eksploracja, cele i punkty, status i odświeżanie | — | After you perform a tactical action, you may exhaust this card to explore 1 planet you control. At the end of the status phase, if you cont… |
| `enigmaticdevice` | Enigmatic Device | — | — | PERMIT (pozwolenie) | ekonomia i płatności, technologie | — | Place this card faceup in your play area. ACTION: You may spend 6 resources and purge this card to research 1 technology. |
| `heartofixth` | Heart of Ixth | — | — | PERMIT (pozwolenie) | walka, status i odświeżanie | — | After any die is rolled, you may exhaust this card to add or subtract 1 from its result. |
| `lightrailordnance` | Lightrail Ordnance | — | — | PERMIT (pozwolenie) | ruch, walka, produkcja | — | Your space docks gain SPACE CANNON 5 (x2). You may use your space dock's SPACE CANNON against ships that are adjacent to their systems. |
| `mawofworlds` | Maw of Worlds | — | — | PERMIT (pozwolenie) | technologie, planety i eksploracja, agenda i głosowanie, status i odświeżanie | — | At the start of the agenda phase, you may purge this card and exhaust all of your planets to gain any 1 technology. |
| `metalivoidarmaments` | Metali Void Armaments | — | — | PERMIT (pozwolenie) | walka | — | During the "Anti-Fighter Barrage" step of space combat, you may resolve ANTI-FIGHTER BARRAGE 6 (x3) against your opponent's units. |
| `metalivoidshielding` | Metali Void Shielding | — | — | MODIFY (liczba/rzut) | walka, produkcja | — | Each time hits are produced against 1 or more of your non-fighter ships, 1 of those ships may use SUSTAIN DAMAGE as if it had that ability. |
| `nanoforge` | Nano-Forge | — | — | FORBID (zakaz) | ekonomia i płatności, planety i eksploracja | — | ACTION: Attach this card to a non-legendary, non-home planet you control, its resource and influence values are increased by 2 and it is a … |
| `neuraloop` | Neuraloop | — | — | PERMIT (pozwolenie) | karty, planety i eksploracja, cele i punkty | — | When a public objective is revealed, you may purge one of your relics to discard that objective and replace it with a random objective from… |
| `obsidian` | The Obsidian | — | — | MODIFY (liczba/rzut) | karty, cele i punkty | — | When you gain this card, draw 1 secret objective. You can have 1 additional scored or unscored secret objective. |
| `prophetstears` | The Prophet's Tears | — | — | PERMIT (pozwolenie) | technologie, karty, status i odświeżanie | — | When you research a technology, you may exhaust this card to ignore 1 prerequisite or draw 1 action card. |
| `quantumcore` | The Quantumcore | — | — | — | technologie | — | When you gain this card, gain your breakthrough. You have SYNERGY for all technology types. |
| `shard` | Shard of the Throne | — | — | — | planety i eksploracja, cele i punkty | — | When you gain this card, gain 1 victory point, when you lose this card, lose 1 victory point. When a player gains control of a legendary pl… |
| `stellarconverter` | Stellar Converter | — | — | MODIFY (liczba/rzut) | ruch, walka, planety i eksploracja | — | ACTION: Choose 1 non-home, non-legendary planet other than Mecatol Rex in a system that is adjacent to 1 or more of your units that have BO… |
| `thalnos` | The Crown of Thalnos | — | — | MODIFY (liczba/rzut) | walka, produkcja | — | During each combat round, this card's owner may reroll any number of their dice, applying +1 to the results, any units that reroll dice but… |
| `thesilverflame` | The Silver Flame | — | — | FORBID (zakaz) | walka, cele i punkty | — | The Silver Flame may be exchanged as part of a transaction. > ACTION: Roll 1 die and purge this card; if the result is a 10, gain 1 victory… |
| `thetriad` | The Triad | — | — | PERMIT (pozwolenie) | ekonomia i płatności, planety i eksploracja | — | This card can be readied and spent as if it were a planet card. Its resource and influence values are equal to 3 plus the number of differe… |
| `titanprototype` | JR-XS455-O | — | — | PERMIT (pozwolenie) | ekonomia i płatności, planety i eksploracja, status i odświeżanie | — | ACTION: Exhaust this agent and choose a player, that player may spend 3 resources to place a structure on a planet they control. If they do… |

</details>

<details><summary>promissory_notes (40)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `<color>_an` | Alliance | — | — | MODIFY (liczba/rzut) | — | — | When you receive this card, if you are not the <color> player, you must place it faceup in your play area. While this card is in your play … |
| `<color>_cf` | Ceasefire | — | — | FORBID (zakaz) | ruch | — | After the <color> player activates a system that contains 1 or more of your units: The <color> player cannot move units to the active syste… |
| `<color>_ps` | Political Secret | — | — | FORBID (zakaz) | karty, agenda i głosowanie | — | When an agenda is revealed: The <color> player cannot vote, play action cards, or use faction abilities until after that agenda has been re… |
| `<color>_sftt` | Support for the Throne | — | — | MODIFY (liczba/rzut) | cele i punkty | — | When you receive this card, if you are not the <color> player, you must place it faceup in your play area and gain 1 victory point. When yo… |
| `<color>_ta` | Trade Agreement | — | — | — | ekonomia i płatności | — | When the <color> player replenishes commodities: The <color> player gives you all of their commodities. Then, return this card to the <colo… |
| `acq` | Acquiescence | winnu | — | — | ekonomia i płatności, żetony dowodzenia, karty strategii i inicjatywa | — | When the Winnu player resolves a strategic action: You do not have to spend or place a command token to resolve the secondary ability of th… |
| `ambuscade` | Strike Wing Ambuscade | argent | — | MODIFY (liczba/rzut) | walka | — | When 1 or more of your units make a roll for a unit ability: Choose 1 of those units to roll 1 additional die. Then, return this card to th… |
| `antivirus` | Antivirus | nekro | — | FORBID (zakaz) | walka, technologie | — | At the start of a combat: Place this card faceup in your play area. While this card is in your play area, the Nekro player cannot use their… |
| `blackops` | Black Ops | firmament | — | PERMIT (pozwolenie) | ekonomia i płatności, żetony dowodzenia, planety i eksploracja | — | When you receive this card, if you are not the Firmament: The Firmament player may place 1 facedown plot card in their play area with your … |
| `blood_pact` | Blood Pact | empyrean | — | MODIFY (liczba/rzut) | agenda i głosowanie | — | ACTION: Place this card faceup in your play area. When you and the Empyrean player cast votes for the same outcome, cast 4 additional votes… |
| `bmf` | Black Market Forgery | naaz | — | — | planety i eksploracja | — | ACTION: Purge 2 of your relic fragments of the same type to gain 1 relic. Then, return this card to the Naaz-Rokha player. |
| `cavalry` | The Cavalry | nomad | — | — | walka | — | At the start of a space combat against a player other than the Nomad: During this combat, treat 1 of your non-fighter ships as if it has th… |
| `ce` | Cybernetic Enhancements | l1z1x | — | MODIFY (liczba/rzut) | żetony dowodzenia, status i odświeżanie | — | When you gain command tokens during the status phase: Gain 1 additional command token. Then, return this card to the L1Z1X player. |
| `convoys` | Trade Convoys | hacan | — | MODIFY (liczba/rzut) | — | — | ACTION: Place this card faceup in your play area. While this card is in your play area, you may negotiate transactions with players who are… |
| `crucible` | Crucible | cabal | — | REPLACE (instead of) | ruch, walka | — | After you activate a system: Your ships do not roll for gravity rifts during this movement, apply an additional +1 to the move values of yo… |
| `dark_pact` | Dark Pact | empyrean | — | MODIFY (liczba/rzut) | ekonomia i płatności | — | ACTION: Place this card faceup in your play area. When you give a number of commodities to the Empyrean player equal to your maximum commod… |
| `favor` | Political Favor | xxcha | — | REPLACE (instead of) | produkcja, żetony dowodzenia, karty, agenda i głosowanie | — | When an agenda is revealed: Remove 1 token from the Xxcha player's strategy pool and return it to their reinforcements. Then, discard the r… |
| `fires` | Fires of the Gashlai | muaat | — | — | produkcja, żetony dowodzenia, technologie | — | ACTION: Remove 1 token from the Muaat player's fleet pool and return it to their reinforcements. Then, gain your war sun unit upgrade techn… |
| `gift` | Gift of Prescience | naalu | — | FORBID (zakaz) | status i odświeżanie, karty strategii i inicjatywa | — | At the end of the Strategy Phase: Place this card faceup in your play area and place the Naalu '0' token on your strategy card, you are the… |
| `greyfire` | Greyfire Mutagen | yin | — | MODIFY (liczba/rzut) | walka, produkcja, planety i eksploracja | — | At the start of a ground combat against 2 or more ground forces that are not controlled by the Yin player: Replace 1 of your opponent's inf… |
| `iff` | Creuss Iff | ghost | — | — | ruch, planety i eksploracja | — | At the start of your turn during the action phase: Place or move a Creuss wormhole token into either a system that contains a planet you co… |
| `malevolency` | Malevolency | obsidian | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności, żetony dowodzenia, status i odświeżanie | — | At the end of one of your tactical actions: Spend 1 influence to give this card to one of your neighbors; you can use this ability even if … |
| `ms` | Military Support | sol | — | PERMIT (pozwolenie) | produkcja, żetony dowodzenia, planety i eksploracja | — | At the start of the Sol player's turn: Remove 1 token from the Sol player's strategy pool, if able, and return it to their reinforcements. … |
| `nanolink` | Nano-Link Permit | ralnel | — | PERMIT (pozwolenie) | ruch, żetony dowodzenia, planety i eksploracja | — | After you activate a system: You may move your structures from adjacent systems that do not contain your command tokens onto planets you co… |
| `pop` | Promise of Protection | mentak | — | FORBID (zakaz) | — | — | ACTION: Place this card faceup in your play area. While this card is in your play area, the Mentak player cannot use their Pillage faction … |
| `ra` | Research Agreement | jolnar | — | — | technologie | — | After the Jol-Nar player researches a technology that is not a faction technology: Gain that technology. Then, return this card to the Jol-… |
| `ragh` | Raghs Call | saar | — | MODIFY (liczba/rzut) | planety i eksploracja | — | After you commit 1 or more units to land on a planet: Remove all of the Saar player's ground forces from that planet and place them on a pl… |
| `raisethestandard` | Raise the Standard | bastion | — | — | walka | — | At the end of a combat: Galvanize 1 of your units that participated. Then, return this card to the Last Bastion player. |
| `rider` | Keleres Rider | keleres | — | FORBID (zakaz) | ekonomia i płatności, karty, agenda i głosowanie | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, draw 1… |
| `ridera` | Keleres Rider | keleresa | — | FORBID (zakaz) | ekonomia i płatności, karty, agenda i głosowanie | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, draw 1… |
| `riderm` | Keleres Rider | keleresm | — | FORBID (zakaz) | ekonomia i płatności, karty, agenda i głosowanie | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, draw 1… |
| `riderx` | Keleres Rider | keleresx | — | FORBID (zakaz) | ekonomia i płatności, karty, agenda i głosowanie | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, draw 1… |
| `scepter` | Scepter of Dominion | mahact | — | — | produkcja | — | At the start of the strategy phase: Choose 1 non-home system that contains your units, each other player who has a token on the Mahact play… |
| `sever` | Sever | crimson | — | — | ruch, status i odświeżanie | — | ACTION: place this card face up in your play area, and place the sever token in a system that contains your units, wormholes in that system… |
| `shareknowledge` | Share Knowledge | deepwrought | — | — | technologie, status i odświeżanie | — | ACTION: Place this card faceup in your play area and gain 1 non-faction, non-unit upgrade technology that the Deepwrought player owns; plac… |
| `spynet` | Spy Net | yssaril | — | — | karty | — | At the start of your turn: Look at the Yssaril player's hand of action cards. Choose 1 of those cards and add it to your hand. Then, return… |
| `stymie` | Stymie | arborec | — | MODIFY (liczba/rzut) | ruch, produkcja, żetony dowodzenia | — | After another player moves ships into a system that contains 1 or more of your units: You may place 1 command token from that player's rein… |
| `tekklar` | Tekklar Legion | sardakk | — | MODIFY (liczba/rzut) | walka | — | At the start of an invasion combat: Apply +1 to the result of each of your unit's combat rolls during this combat. If your opponent is the … |
| `terraform` | Terraform | titans | — | — | ekonomia i płatności, planety i eksploracja | — | ACTION: Attach this card to a non-home planet you control other than Mecatol Rex. Its resource and influence values are each increased by 1… |
| `war_funding` | War Funding | letnev | — | MODIFY (liczba/rzut) | walka | — | After you and your opponent roll dice during space combat: You may reroll all of your opponent's dice. You may reroll any number of your di… |

</details>

<details><summary>galactic_events (20)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `advent_war_sun` | Advent of the War Sun | — | — | MODIFY (liczba/rzut) | technologie, karty | — | - At the end of setup, all players other than the Embers of Muaat player gain the War Sun unit upgrade technology. - The Embers of Muaat pl… |
| `age_commerce` | Age of Commerce | — | — | REPLACE (instead of) | ekonomia i płatności, technologie, status i odświeżanie | — | - Players do not have to be neighbors to perform transactions with each other. - Players do not have a maximum number of commodities; when … |
| `age_exploration` | Age of Exploration | — | — | REPLACE (instead of) | ruch, walka, karty, planety i eksploracja, status i odświeżanie | — | - Relics require only 2 matching fragments be purged instead of 3. - The Naaz-Rokha Alliance's ***Fabrication*** faction ability and ***Bla… |
| `age_fighters` | Age of Fighters | — | — | REPLACE (instead of) | walka, żetony dowodzenia, technologie | — | - During setup, all players gain the Fighter II unit upgrade technology; the Naalu Collective player gains Hybrid Crystal Fighter II techno… |
| `call_of_the_void` | Call of the Void | — | — | MODIFY (liczba/rzut) | ruch, żetony dowodzenia | — | After you move 1 or more units into the active system, if that system is in The Fracture, gain 1 command token. - When you activate a syste… |
| `civilized_society` | Civilized Society | — | — | REPLACE (instead of) | ekonomia i płatności, planety i eksploracja, cele i punkty, status i odświeżanie | — | - During setup, turn all public objectives face up. - There is no limit on the number of public objectives a player may score during the st… |
| `cosmic_phenomenae` | Cosmic Phenomenae | — | — | REPLACE (instead of) | ruch, walka, produkcja | — | Anomalies have the following additional rules: > - ***Nebulae:*** Defending ships in nebulae apply an additional +3 to their combat rolls i… |
| `cowabunga` | Conventions of War Abandoned | — | — | REPLACE (instead of) | walka, produkcja, technologie, planety i eksploracja, status i odświeżanie | — | - Each hit produced by ***BOMBARDMENT*** rolls destroys 3 units instead of 1. - ***X-89 BACTERIAL WEAPON*** technology gains the following … |
| `cultural_exchange` | Cultural Exchange Program | — | — | REPLACE (instead of) | karty, planety i eksploracja | — | - At the end of setup, shuffle the reference cards that correspond to each faction in play. Each player draws 1 of those cards and takes al… |
| `dangerous_wilds` | Dangerous Wilds | — | — | PERMIT (pozwolenie) | walka, ekonomia i płatności, technologie, planety i eksploracja | — | - During setup, place neutral infantry on each hazardous planet equal to that planet's resource value. - At the end of each round, for each… |
| `hidden_agenda` | Hidden Agenda | — | — | FORBID (zakaz) | karty, agenda i głosowanie | — | - During the agenda phase, only the speaker can talk; all other players must remain silent except when declaring action cards/abilities. Tr… |
| `mercenaries` | Mercenaries for Hire | — | — | PERMIT (pozwolenie) | ekonomia i płatności | — | - At the start of the game, shuffle the alliance cards that correspond to the factions not in play and place them in the common play area; … |
| `minor_factions` | Minor Factions | — | — | MODIFY (liczba/rzut) | planety i eksploracja, agenda i głosowanie | — | - During setup, players are dealt 1 fewer blue tile. Before creating the galaxy, shuffle the reference cards for factions not being played … |
| `mobilization` | Rapid Mobilization | — | — | MODIFY (liczba/rzut) | ruch, produkcja, technologie, planety i eksploracja, status i odświeżanie | — | - After setup, put The Fracture into play. Then, each player simultaneously resolves the following effects in order: > - Place 1 infantry o… |
| `monuments_ages` | Monuments to the Ages | — | — | REPLACE (instead of) | walka, produkcja, ekonomia i płatności, planety i eksploracja, cele i punkty, status i odświeżanie | — | - When you would place a structure on a non-home planet, you may spend 5 trade goods to place a neutral space dock instead; this is a monum… |
| `stellar_atomics` | Stellar Atomics | — | — | FORBID (zakaz) | walka, karty, planety i eksploracja, agenda i głosowanie | — | - During setup, each player places one of their control markers on this card. - All players can perform the following action: > - **Action:… |
| `total_war` | Total War | — | — | PERMIT (pozwolenie) | ruch, walka, ekonomia i płatności, karty, planety i eksploracja, cele i punkty | — | - When a player destroys another player's units, they place commodities from the supply equal to the combined cost of those units on a plan… |
| `weird_wormholes` | Weird Wormholes | — | — | MODIFY (liczba/rzut) | ruch, walka, produkcja, technologie | — | - After a ship moves using at least 1 alpha, beta, or gamma wormhole, roll 1 die and consult the following list: > - [ Fighter -> Destroyer… |
| `wild_wild_galaxy` | Wild, Wild Galaxy | — | — | REPLACE (instead of) | ruch, walka, żetony dowodzenia, karty, planety i eksploracja | — | Action cards are adjusted as follows: > - Direct hit: Can be used against mechs. > - Flank Speed: Applies +2 move instead of +1. > - Maneuv… |
| `zealous_orthodoxy` | Zealous Orthodoxy | — | — | — | karty, cele i punkty | — | - The first player to score 2 secret objectives gains 1 victory point. - Then, place that faction's alliance card on this card; all players… |

</details>

<details><summary>leaders (103)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `arborecagent` | Letani Ospha | arborec | action | MODIFY (liczba/rzut) | produkcja, status i odświeżanie | — | [agent] Exhaust this card and choose a player's non-fighter ship: that player may replace that ship with one from their reinforcements that… |
| `arboreccommander` | Dirzuga Rophal | arborec | after | TRIGGER (okno reakcji) | produkcja | — | [commander] You may produce 1 unit in that system. |
| `arborechero` | Letani Miasmiala | arborec | action | MODIFY (liczba/rzut) | produkcja | — | [hero] Produce any number of units in any number of systems that contain 1 or more of your ground forces. Then, purge this card. |
| `argentagent` | Trilossa Aun Mirik | argent | when | TRIGGER (okno reakcji) | ruch, planety i eksploracja, status i odświeżanie | — | [agent] You may exhaust this card: that player may place those units on any planets they control in that system and any adjacent systems. |
| `argentcommander` | Trrakan Aun Zulok | argent | when | TRIGGER (okno reakcji) | walka | — | [commander] You may choose 1 of those units to roll 1 additional die. |
| `argenthero` | Mirik Aun Sissiri | argent | action | — | ruch, żetony dowodzenia | — | [hero] Move any number of your ships from any systems to any number of other systems that contain 1 of your command tokens and no other pla… |
| `bastionagent` | Dame Briar | bastion | when | TRIGGER (okno reakcji) | walka, status i odświeżanie | — | [agent] You may exhaust this card to galvanize another of that player's units in the destroyed unit's system. |
| `bastioncommander` | Nip and Tuck | bastion | unclassified | FORBID (zakaz) | karty | — | [commander] Your action cards cannot be canceled by "Sabotage" action cards. The Nekro Virus cannot place assimilator tokens on your compon… |
| `bastionhero` | Lyra Keen | bastion | when | TRIGGER (okno reakcji) | walka | — | [hero] You may purge this card to roll 1 die for each unit in its system that belongs to another player; if the result is equal to or great… |
| `cabalagent` | The Stillness of Stars | cabal | after | TRIGGER (okno reakcji) | produkcja, ekonomia i płatności, status i odświeżanie | — | [agent] You may exhaust this card to convert their commodities to trade goods and capture 1 unit from their reinforcements that has a cost … |
| `cabalcommander` | That Which Molds Flesh | cabal | when | TRIGGER (okno reakcji) | produkcja | — | [commander] Up to 2 of those units do not count against your PRODUCTION limit. |
| `cabalhero` | It Feeds on Carrion | cabal | action | MODIFY (liczba/rzut) | ruch, walka | — | [hero] Each other player rolls a die for each of his non-fighter ships that are in or adjacent to a system that contains a dimensional tear… |
| `crimsonagent` | Ahk Ravin | crimson | action | PERMIT (pozwolenie) | status i odświeżanie | — | [agent] Exhaust this card to choose 1 player. That player may swap the position of 2 of their ships in any systems; they may transport unit… |
| `crimsoncommander` | Ahk Siever | crimson | at_end | — | ekonomia i płatności | — | [commander] Gain 1 commodity or convert 1 of your commodities to a trade good. |
| `crimsonhero` | Homesick Phantom | crimson | when | TRIGGER (okno reakcji) | walka | — | [hero] You may place any of those ships onto this card. At the start of a space combat, you may purge this card to place all ships from thi… |
| `deepwroughtagent` | Doctor Carrina | deepwrought | when | TRIGGER (okno reakcji) | produkcja, technologie, planety i eksploracja, status i odświeżanie | — | [agent] You may exhaust this card to allow that player to ignore 1 prerequisite; if they do, you may place 1 infantry from your reinforceme… |
| `deepwroughtcommander` | Aello | deepwrought | when | TRIGGER (okno reakcji) | ekonomia i płatności | — | [commander] That player may reduce the cost by 1; if they do, gain 1 commodity or convert 1 of your commodities to a trade good. |
| `deepwroughthero` | Ta Zern | deepwrought | action | — | technologie | — | [hero] Purge this card and a non-unit upgrade technology you own or from your deck; then, purge all cards with the same name owned by other… |
| `empyreanagent` | Acamar | empyrean | after | TRIGGER (okno reakcji) | żetony dowodzenia, status i odświeżanie | — | [agent] You may exhaust this card: that player gains 1 command token. |
| `empyreancommander` | Xuange | empyrean | after | TRIGGER (okno reakcji) | produkcja | — | [commander] You may return that token to your reinforcements. |
| `empyreanhero` | Conservator Procyon | empyrean | action | MODIFY (liczba/rzut) | planety i eksploracja | — | [hero] Place 1 frontier token in each system that does not contain any planets and does not already have a frontier token. Then, explore ea… |
| `firmamentagent` | Myru Vos | firmament | when | TRIGGER (okno reakcji) | ruch, walka, status i odświeżanie | — | [agent] You may exhaust this card; if you do, SPACE CANNON cannot be used against those ships. If they are not transporting units, they can… |
| `firmamentcommander` | Captain Aroz | firmament | unclassified | PERMIT (pozwolenie) | planety i eksploracja, cele i punkty | — | [commander] You can treat planets in systems that contain your ships as if they were controlled by you for the purpose of scoring secret ob… |
| `firmamenthero` | Sharsiss | firmament | action | FORBID (zakaz) | planety i eksploracja | — | [hero] Place 1 of your plot cards in play with any other player's control token on it. Then, you may place any player's control token on 1 … |
| `ghostagent` | Emissary Taivra | ghost | after | TRIGGER (okno reakcji) | ruch, status i odświeżanie | — | [agent] You may exhaust this card: if you do, that system is adjacent to all other systems that contain a wormhole during this tactical act… |
| `ghostcommander` | Sai Seravus | ghost | after | TRIGGER (okno reakcji) | ruch, produkcja | — | [commander] For each ship that has a capacity value and moved through 1 or more wormholes, you may place 1 fighter from your reinforcements… |
| `ghosthero` | Riftwalker Meian | ghost | action | — | ruch | — | [hero] Swap the positions of any 2 non-Fracture systems that contain wormholes or your units, other than the Creuss system, Ahk Creuxx syst… |
| `hacanagent` | Carth of Golden Sands | hacan | during | PERMIT (pozwolenie) | ekonomia i płatności, status i odświeżanie | — | [agent] You may exhaust this card to gain 2 commodities or replenish another player's commodities. |
| `hacancommander` | Gila the Silvertongue | hacan | when | TRIGGER (okno reakcji) | ekonomia i płatności, agenda i głosowanie | — | [commander] You may spend any number of trade goods: cast 2 additional votes for each trade good spent. |
| `hacanhero` | Harrugh Gefhara | hacan | when | TRIGGER (okno reakcji) | produkcja | — | [hero] You may reduce the cost of each of your units to 0 during this use of PRODUCTION. If you do, purge this card. |
| `jolnaragent` | Doctor Sucaban | jolnar | when | TRIGGER (okno reakcji) | ekonomia i płatności, status i odświeżanie | — | [agent] You may exhaust this card to allow that player to remove any number of their infantry from the game board. For each unit removed, r… |
| `jolnarcommander` | Agnlan Oln | jolnar | after | TRIGGER (okno reakcji) | — | — | [commander] You may reroll any of those dice. |
| `jolnarhero` | Rin, the Master's Legacy | jolnar | action | PERMIT (pozwolenie) | technologie | — | [hero] For each non-unit upgrade technology you own, you may replace that technology with any technology of the same color from the deck. T… |
| `keleresagent` | Xander Alexin Victori III | keleres | unclassified | PERMIT (pozwolenie) | ekonomia i płatności, status i odświeżanie | — | [agent] You may exhaust this card to allow any player to spend commodities as if they were trade goods. |
| `kelerescommander` | Suffi An | keleres | after | TRIGGER (okno reakcji) | — | — | [commander] You may perform an additional action. |
| `keleresheroharka` | Harka Leeds | keleres | action | — | karty | — | [hero] Reveal cards from the action card deck until you reveal 3 action cards that have component actions. Draw those cards and shuffle the… |
| `keleresherokuuasi` | Kuuasi Aun Jalatai | keleres | at_start | — | walka, produkcja | — | [hero] Place your flagship and up to a total of 2 cruisers and/or destroyers from your reinforcements in the active system. Then, purge thi… |
| `keleresheroodlynn` | Odlynn Myrr | keleres | after | TRIGGER (okno reakcji) | ekonomia i płatności, żetony dowodzenia, agenda i głosowanie | — | [hero] You may cast up to 6 additional votes on this agenda. Predict aloud an outcome of this agenda. For each player that abstains or vote… |
| `l1z1xagent` | I48S | l1z1x | after | TRIGGER (okno reakcji) | produkcja, status i odświeżanie | — | [agent] You may exhaust this card to allow that player to replace 1 of their infantry in the active system with 1 mech from their reinforce… |
| `l1z1xcommander` | 2RAM | l1z1x | unclassified | — | walka | — | [commander] Units that have PLANETARY SHIELD do not prevent you from using BOMBARDMENT. |
| `l1z1xhero` | The Helmsman | l1z1x | action | PERMIT (pozwolenie) | ruch | — | [hero] Choose 1 system that does not contain other players' ships. you may move your flagship and any number of your dreadnoughts from othe… |
| `letnevagent` | Viscount Unlenn | letnev | at_start | MODIFY (liczba/rzut) | walka, status i odświeżanie | — | [agent] You may exhaust this card to choose 1 ship in the active system: that ship rolls 1 additional die during this combat round. |
| `letnevcommander` | Rear Admiral Farran | letnev | after | TRIGGER (okno reakcji) | ekonomia i płatności | — | [commander] You may gain 1 trade good. |
| `letnevhero` | Darktalon Treilla | letnev | action | PERMIT (pozwolenie) | żetony dowodzenia | — | [hero] Place this card near the game board. the number of non-fighter ships you can have in systems is not limited by laws or by the number… |
| `mahactagent` | Jae Mir Kan | mahact | when | TRIGGER (okno reakcji) | żetony dowodzenia, status i odświeżanie | — | [agent] You may exhaust this card to remove 1 of the active player's command tokens from the board and use it instead. |
| `mahactcommander` | Il Na Viroset | mahact | during | PERMIT (pozwolenie) | produkcja, żetony dowodzenia | — | [commander] you can activate systems that contain your command tokens. If you do, return both command tokens to your reinforcements and end… |
| `mahacthero` | Airo Shir Aur | mahact | action | PERMIT (pozwolenie) | ruch, walka | — | [hero] Move all units in the space area of any system to an adjacent system that contains a different player's ships. Space combat is resol… |
| `mentakagent` | Suffi An | mentak | after | TRIGGER (okno reakcji) | karty, status i odświeżanie | — | [agent] You may exhaust this card: if you do, you and that player each draw 1 action card. |
| `mentakcommander` | S'ula Mentarion | mentak | after | TRIGGER (okno reakcji) | karty | — | [commander] You may force your opponent to give you 1 promissory note from their hand. |
| `mentakhero` | Ipswitch, Loose Cannon | mentak | at_start | PERMIT (pozwolenie) | walka, produkcja | — | [hero] You may purge this card. if you do, for each other player's ship that is destroyed during this combat, place 1 ship of that type fro… |
| `muaatagent` | Umbat | muaat | action | PERMIT (pozwolenie) | produkcja, status i odświeżanie | — | [agent] Exhaust this card to choose a player: that player may produce up to 2 units that each have a cost of 4 or less in a system that con… |
| `muaatcommander` | Magmus | muaat | after | TRIGGER (okno reakcji) | ekonomia i płatności | — | [commander] You may gain 1 trade good. |
| `muaathero` | Adjudicator Ba'al | muaat | after | TRIGGER (okno reakcji) | walka, planety i eksploracja | — | [hero] You may destroy all other players' units in that system and replace that system tile with the Muaat supernova tile. If you do, purge… |
| `naaluagent` | Z'eu | naalu | action | PERMIT (pozwolenie) | żetony dowodzenia, status i odświeżanie | — | [agent] Exhaust this card and choose a player. That player may perform a tactical action in a non-home system without placing a command tok… |
| `naaluagent-te` | Z'eu | naalu | after | TRIGGER (okno reakcji) | produkcja, status i odświeżanie | — | [agent] You may exhaust this card to return that token to that player's reinforcements. |
| `naalucommander` | M'aban | naalu | unclassified | PERMIT (pozwolenie) | karty, agenda i głosowanie | — | [commander] You may look at your neighbors' hands of promissory notes and the top and bottom card of the agenda deck. |
| `naaluhero` | The Oracle | naalu | at_end | PERMIT (pozwolenie) | karty | — | [hero] You may force each other player to give you 1 promissory note from their hand. If you do, purge this card. |
| `naazagent` | Garv and Gunn | naaz | at_end | PERMIT (pozwolenie) | planety i eksploracja, status i odświeżanie | — | [agent] You may exhaust this card to allow that player to explore 1 of their planets. |
| `naazcommander` | Dart and Tai | naaz | after | TRIGGER (okno reakcji) | planety i eksploracja | — | [commander] You may explore that planet. |
| `naazhero` | Hesh and Prit | naaz | action | REPLACE (instead of) | produkcja, ekonomia i płatności, żetony dowodzenia, planety i eksploracja, karty strategii i inicjatywa | — | [hero] Gain 1 relic and perform the secondary ability of up to 2 readied or unchosen strategy cards. during this action, spend command toke… |
| `nekroagent` | Nekro Malleon | nekro | during | PERMIT (pozwolenie) | ekonomia i płatności, żetony dowodzenia, karty, status i odświeżanie | — | [agent] You may exhaust this card to choose a player: that player may discard 1 action card or spend 1 command token from their command she… |
| `nekrocommander` | Nekro Acidos | nekro | after | TRIGGER (okno reakcji) | karty | — | [commander] You may draw 1 action card. |
| `nekrohero` | UNIT.DSGN.FLAYESH | nekro | action | — | walka, ekonomia i płatności, technologie, planety i eksploracja | — | [hero] Choose a planet that has a technology specialty in a system that contains your units. Destroy any other player's units on that plane… |
| `nomadagentartuno` | Artuno the Betrayer | nomad | when | TRIGGER (okno reakcji) | ekonomia i płatności, status i odświeżanie | — | [agent] You may exhaust this card to place an equal number of trade goods on this card. When this card readies, gain the trade goods on thi… |
| `nomadagentmercer` | Field Marshal Mercer | nomad | at_end | PERMIT (pozwolenie) | planety i eksploracja, status i odświeżanie | — | [agent] You may exhaust this card to allow that player to remove up to 2 of their ground forces from the game board and place them on plane… |
| `nomadagentthundarian` | The Thundarian | nomad | after | TRIGGER (okno reakcji) | walka, status i odświeżanie | — | [agent] You may exhaust this card. If you do, hits are not assigned to either player's units. Return to the start of this combat round's "R… |
| `nomadcommander` | Navarch Feng | nomad | when | TRIGGER (okno reakcji) | produkcja, ekonomia i płatności | — | [commander] You can produce your flagship without spending resources. |
| `nomadhero` | Ahk-Syl Siven | nomad | action | PERMIT (pozwolenie) | ruch, żetony dowodzenia | — | [hero] Place this card near the game board. your flagship and units it transports can move out of systems that contain your command tokens … |
| `obsidianagent` | Vos Hollow | obsidian | when | TRIGGER (okno reakcji) | walka, status i odświeżanie | — | [agent] You may exhaust this card; if you do, that player's opponent must destroy 1 of their ships of the same type in the active system. |
| `obsidiancommander` | Aroz Hollow | obsidian | unclassified | MODIFY (liczba/rzut) | walka | — | [commander] Apply +1 to the result of each of your units' combat rolls in The Fracture. |
| `obsidianhero` | Sharsiss Hollow | obsidian | action | — | planety i eksploracja, status i odświeżanie | — | [hero] Ready all of your planets. Then, purge this card. |
| `orlandohero` | F.S.S. Orlando | bastion | when | TRIGGER (okno reakcji) | walka | — | [hero] You may purge this card to designate that unit as a catalyst: roll 1 die for each other player's unit in the system. For each result… |
| `ralnelagent` | Kan Kip Rel | ralnel | action | — | karty, status i odświeżanie | — | [agent] Exhaust this card and draw 2 action cards; give 1 of those cards to another player. |
| `ralnelcommander` | Watchful Ojz | ralnel | when | TRIGGER (okno reakcji) | ruch, walka, produkcja, żetony dowodzenia | — | [commander] Immediately retreat up to 2 of your ships from the active system to an adjacent system that does not contain another player's s… |
| `ralnelhero` | Director Nel | ralnel | after | TRIGGER (okno reakcji) | żetony dowodzenia, karty | — | [hero] You may choose to no longer be passed; if you do, gain 2 command tokens, draw 1 action card, and purge this card. |
| `redcreussagent` | "Who Knows?" | crimson | action | PERMIT (pozwolenie) | status i odświeżanie | — | [agent] Exhaust this card to choose 1 player. That player may swap the position of 2 of their ships in any systems; they may transport unit… |
| `redcreusscommander` | "Total Mystery" | crimson | at_end | — | ekonomia i płatności | — | [commander] Gain 1 commodity or convert 1 of your commodities to a trade good. |
| `redcreusshero` | "A Tall Stranger" | crimson | when | TRIGGER (okno reakcji) | walka | — | [hero] You may place any of those ships onto this card. At the start of a space combat, you may purge this card to place all ships from thi… |
| `saaragent` | Captain Mendosa | saar | when | TRIGGER (okno reakcji) | ruch, status i odświeżanie | — | [agent] You may exhaust this card to increase the move value of 1 of that player's ships to match the move value of the ship on the game bo… |
| `saarcommander` | Rowl Sarrig | saar | when | TRIGGER (okno reakcji) | produkcja | — | [commander] You may place each of those units at any of your space docks that are not blockaded. |
| `saarhero` | Gurno Aggero | saar | action | — | ruch, walka, produkcja | — | [hero] Choose 1 system that is adjacent to 1 of your space docks. Destroy all other players' infantry and fighters in that system. Then, pu… |
| `sardakkagent` | T'ro | sardakk | at_end | PERMIT (pozwolenie) | produkcja, planety i eksploracja, status i odświeżanie | — | [agent] You may exhaust this card: if you do, that player may place 2 infantry from their reinforcements on a planet they control in the ac… |
| `sardakkcommander` | G'hom Sek'kus | sardakk | during | PERMIT (pozwolenie) | ruch, żetony dowodzenia, planety i eksploracja | — | [commander] You can commit (move) up to 1 ground force from each planet in the active system and each planet in adjacent systems that do no… |
| `sardakkhero` | Sh'val, Harbinger | sardakk | after | TRIGGER (okno reakcji) | produkcja, planety i eksploracja | — | [hero] You may skip directly to the "Commit Ground Forces" step. If you do, after you commit ground forces to land on planets, purge this c… |
| `solagent` | Evelyn DeLouis | sol | at_start | MODIFY (liczba/rzut) | walka, status i odświeżanie | — | [agent] You may exhaust this card to choose 1 ground force in the active system: that ground force rolls 1 additional die during this comba… |
| `solcommander` | Claire Gibson | sol | at_start | PERMIT (pozwolenie) | produkcja, planety i eksploracja | — | [commander] You may place 1 infantry from your reinforcements on that planet. |
| `solhero` | Jace X, 4th Air Legion | sol | action | — | produkcja, żetony dowodzenia | — | [hero] Remove each of your command tokens from the game board and return them to your reinforcements. Then, purge this card. |
| `titansagent` | Tellurian | titans | before | TRIGGER (okno reakcji) | walka, status i odświeżanie | — | [agent] You may exhaust this card to cancel that hit. |
| `titanscommander` | Tungstantus | titans | when | TRIGGER (okno reakcji) | ekonomia i płatności | — | [commander] You may gain 1 trade good. |
| `titanshero` | Ul the Progenitor | titans | action | — | walka, ekonomia i płatności, planety i eksploracja, status i odświeżanie | — | [hero] Ready Elysium and attach this card to it. Its resource and influence values are each increased by 3, and it gains the SPACE CANNON 5… |
| `winnuagent` | Berekar Berekon | winnu | when | TRIGGER (okno reakcji) | produkcja, status i odświeżanie | — | [agent] You may exhaust this card to reduce the combined cost of the produced units by 2. |
| `winnucommander` | Rickar Rickani | winnu | during | MODIFY (liczba/rzut) | walka, planety i eksploracja | — | [commander] Apply +2 to the result of each of your unit's combat rolls in the Mecatol Rex system, your home system, and each system that co… |
| `winnuhero` | Mathis Mathinus | winnu | action | PERMIT (pozwolenie) | karty strategii i inicjatywa | — | [hero] Perform the primary ability of any strategy card. Then, choose any number of other players. Those players may perform the secondary … |
| `xxchaagent` | Ggrocuto Rinn | xxcha | action | PERMIT (pozwolenie) | ruch, produkcja, planety i eksploracja, status i odświeżanie | — | [agent] Exhaust this card to ready any planet; if that planet is in a system that is adjacent to a planet you control, you may remove 1 inf… |
| `xxchacommander` | Elder Qanoj | xxcha | when | TRIGGER (okno reakcji) | planety i eksploracja, agenda i głosowanie, status i odświeżanie | — | [commander] Each planet you exhaust to cast votes provides 1 additional vote. Game effects cannot prevent you from voting on an agenda. |
| `xxchahero` | Xxekir Grom | xxcha | when | TRIGGER (okno reakcji) | ekonomia i płatności | — | [hero] combine the values of their resources and influence. Treat the combined value as if it were both resources and influence. |
| `xxchahero-te` | Xxekir Grom | xxcha | action | — | planety i eksploracja, status i odświeżanie | — | [hero] Place any combination of up to 4 PDS or mechs onto planets you control; ready each planet that you place a unit on. Then, purge this… |
| `yinagent` | Brother Milor | yin | after | TRIGGER (okno reakcji) | walka, planety i eksploracja, status i odświeżanie | — | [agent] You may exhaust this card to allow that player to place 2 fighters in the destroyed unit's system if it was a ship, or 2 infantry o… |
| `yincommander` | Brother Omar | yin | unclassified | PERMIT (pozwolenie) | produkcja, technologie | — | [commander] This card satisfies a green technology prerequisite. When you research a tech owned by another player, you may return 1 of your… |
| `yinhero` | Dannel of the Tenth | yin | action | FORBID (zakaz) | walka, produkcja, planety i eksploracja | — | [hero] Commit up to 3 infantry from your reinforcements to any non-home planets and resolve ground combats on those planets. Players cannot… |
| `yssarilagent` | Ssruu | yssaril | unclassified | — | status i odświeżanie | — | [agent] This card has the text ability of each other player's agent, even if that agent is exhausted. |
| `yssarilcommander` | So Ata | yssaril | after | TRIGGER (okno reakcji) | karty, cele i punkty | — | [commander] You may look at that player's action cards, promissory notes, or secret objectives. |
| `yssarilhero` | Kyver, Blade and Key | yssaril | action | PERMIT (pozwolenie) | karty | — | [hero] Each other player shows you 1 action card from their hand. For each player, you may either take that card or force that player to di… |

</details>

<details><summary>abilities (73)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `aetherpassage` | Aetherpassage | empyrean | after | TRIGGER (okno reakcji) | ruch | — | You may allow that player to move their ships through systems that contain your ships. |
| `amalgamation` | Amalgamation | cabal | when | TRIGGER (okno reakcji) | produkcja, ekonomia i płatności | — | You may return 1 captured unit of that type to produce that unit without spending resources. |
| `ambush` | Ambush | mentak | at_start | PERMIT (pozwolenie) | walka, produkcja | — | You may roll 1 die for each of up to 2 of your cruisers or destroyers in the system. For each result equal to or greater than that ship's c… |
| `analytical` | Analytical | jolnar | when | TRIGGER (okno reakcji) | technologie | — | You may ignore 1 prerequisite. |
| `arbiters` | Arbiters | hacan | — | PERMIT (pozwolenie) | karty | — | When you are negotiating a transaction, action cards can be exchanged as part of that transaction. |
| `armada` | Armada | letnev | — | MODIFY (liczba/rzut) | żetony dowodzenia | — | The maximum number of non-fighter ships you can have in each system is equal to 2 more than the number of tokens in your fleet pool |
| `assimilate` | Assimilate | l1z1x | when | TRIGGER (okno reakcji) | produkcja, planety i eksploracja | — | Replace each PDS and space dock that is on that planet with a matching unit from your reinforcements. |
| `awaken` | Awaken | titans | after | TRIGGER (okno reakcji) | produkcja | — | You may replace each of those tokens with 1 PDS from your reinforcements. |
| `bladesorchestra` | The Blade's Orchestra | obsidian | when | TRIGGER (okno reakcji) | planety i eksploracja, status i odświeżanie | — | flip your home system, double-sided faction components, and all of your in-play plot cards. Then, ready Cronos Hollow and Tallin Hollow if … |
| `blood_ties` | Blood Ties | winnu | — | — | ekonomia i płatności | — | You do not have to spend influence to remove the custodians token from Mecatol Rex. |
| `brilliant` | Brilliant | jolnar | when | TRIGGER (okno reakcji) | — | — | You may resolve the primary ability instead. |
| `coalescence` | Coalescence | titans | — | — | walka, planety i eksploracja | — | If your flagship or your AWAKEN faction ability places your units into the same space area or onto the same planet as another player's unit… |
| `council_patronage` | Council Patronage | keleres | at_start | — | ekonomia i płatności | — | Replenish your commodities, then gain 1 trade good. |
| `crafty` | Crafty | yssaril | — | FORBID (zakaz) | karty | — | You can have any number of action cards in your hand. Game effects cannot prevent you from using this ability. |
| `creuss_gate` | Creuss Gate | ghost | — | — | — | — | When you create the game board, place the Creuss Gate (tile 17) where your home system would normally be placed. The Creuss Gate system is … |
| `dark_whispers` | Dark Whispers | empyrean | — | MODIFY (liczba/rzut) | karty | — | During setup, take the additional Empyrean faction promissory note; you have 2 faction promissory notes |
| `devotion` | Devotion | yin | after | TRIGGER (okno reakcji) | walka, produkcja | — | You may destroy 1 of your cruisers or destroyers in the active system to produce 1 hit and assign it to 1 of your opponent's ships in that … |
| `devour` | Devour | cabal | — | — | walka | — | Capture your opponent's non-structure units that are destroyed during combat. |
| `distant_suns` | Distant Suns | naaz | when | TRIGGER (okno reakcji) | karty | — | You may draw 1 additional card; choose 1 to resolve and discard the rest. |
| `edict` | Edict | mahact | when | TRIGGER (okno reakcji) | produkcja, żetony dowodzenia | — | Other player's tokens in your fleet pool increase your fleet limit but cannot be redistributed. Place 1 command token from your opponent's … |
| `fabrication` | Fabrication | naaz | action | — | żetony dowodzenia, planety i eksploracja | — | Either purge 2 of your relic fragments of the same type to gain 1 relic; or purge 1 of your relic fragments to gain 1 command token. |
| `foresight` | Foresight | naalu | after | TRIGGER (okno reakcji) | ruch, żetony dowodzenia | — | You may place 1 token from your strategy pool in an adjacent system that does not contain another player's ships; move your ships from the … |
| `fragile` | Fragile | jolnar | — | MODIFY (liczba/rzut) | walka | — | Apply -1 to the result of each of your unit's combat rolls. |
| `future_sight` | Future Sight | nomad | during | — | ekonomia i płatności | — | Gain 1 trade good |
| `galactic_threat` | Galactic Threat | nekro | unclassified | FORBID (zakaz) | technologie, agenda i głosowanie | — | You cannot vote on agendas You may predict aloud the outcome of that agenda. If your prediction is correct, gain 1 technology that is owned… |
| `galvanize` | Galvanize | bastion | when | TRIGGER (okno reakcji) | walka | — | Galvanized units roll 1 additional die for combat rolls and unit abilities. they place a galvanize token beneath it if it does not have one. |
| `gashlai_physiology` | Gashlai Physiology | muaat | — | PERMIT (pozwolenie) | ruch | — | Your ships can move through supernovas |
| `guild_ships` | Guild Ships | hacan | — | PERMIT (pozwolenie) | — | — | You can negotiate transactions with players who are not your neighbor. |
| `harrow` | Harrow | l1z1x | at_end | PERMIT (pozwolenie) | walka, planety i eksploracja | — | Your ships in the active system may use their BOMBARDMENT abilities against your opponent's ground forces on the planet. |
| `hubris` | Hubris | mahact | — | FORBID (zakaz) | karty | — | During setup, purge your "Alliance" promissory note. Other players cannot give you their 'Alliance" promissory note. |
| `imperia` | Imperia | mahact | — | PERMIT (pozwolenie) | żetony dowodzenia | — | While another player's command token is in your fleet pool, you can use the ability of that player's commander, if it is unlocked. |
| `incursion` | Incursion | crimson | — | PERMIT (pozwolenie) | ruch, status i odświeżanie | — | When you activate a system that contains a breach, you may flip that breach; systems that contain active breaches are adjacent. at the end … |
| `indoctrination` | Indoctrination | yin | at_start | PERMIT (pozwolenie) | produkcja, ekonomia i płatności | — | You may spend 2 influence to replace 1 of your opponent's participating infantry with 1 infantry from your reinforcements. |
| `laws_order` | Law's Order | keleres | at_start | PERMIT (pozwolenie) | ekonomia i płatności | — | You may spend 1 trade good or 1 commodity to treat all laws as blank until the end of that turn. |
| `liberate` | Liberate | bastion | when | TRIGGER (okno reakcji) | ekonomia i płatności, planety i eksploracja, status i odświeżanie | — | ready that planet if it contains a number of your infantry equal to or greater than that planet's resource value; otherwise, place 1 infant… |
| `marionettes` | Marionettes | obsidian | — | — | planety i eksploracja | — | The player or players whose control tokens are on each plot card are the puppeted players for that plot. |
| `master_of_trade` | Masters of Trade | hacan | — | — | ekonomia i płatności, żetony dowodzenia, karty strategii i inicjatywa | — | You do not have to spend a command token to resolve the secondary ability of the "Trade" strategy card. |
| `miniaturization` | Miniaturization | ralnel | at_end | FORBID (zakaz) | planety i eksploracja | — | Your structures can be transported by any ship; this does not require or count against capacity. While your structures are in the space are… |
| `mitosis` | Mitosis | arborec | at_start | FORBID (zakaz) | produkcja, planety i eksploracja | — | Your space docks cannot produce infantry Place 1 infantry from your reinforcements on any planet you control. |
| `munitions` | Munitions Reserves | letnev | at_start | MODIFY (liczba/rzut) | walka, ekonomia i płatności | — | You may spend 2 trade goods to re-roll any number of your dice during that combat round. |
| `nocturne` | Nocturne | obsidian | — | FORBID (zakaz) | — | — | This faction cannot be chosen during setup. |
| `nomadic` | Nomadic | saar | — | PERMIT (pozwolenie) | planety i eksploracja, cele i punkty | — | You can score objectives even if you do not control the planets in your home system. |
| `oceanbound` | Oceanbound | deepwrought | when | TRIGGER (okno reakcji) | karty, planety i eksploracja, status i odświeżanie | — | Any time you have more ocean cards than there are planets that contain your coexisting units, discard ocean cards until you do not. gain an… |
| `orbital_drop` | Orbital Drop | sol | action | — | produkcja, ekonomia i płatności, żetony dowodzenia, planety i eksploracja | — | Spend 1 token from your strategy pool to place 2 infantry from your reinforcements on 1 planet you control. |
| `peace_accords` | Peace Accords | xxcha | after | TRIGGER (okno reakcji) | ruch, planety i eksploracja | — | You may gain control of 1 planet other than Mecatol Rex that does not contain any units and is in a system that is adjacent to a planet you… |
| `phoenixstandard` | Phoenix Standard | bastion | at_end | PERMIT (pozwolenie) | — | — | you may galvanize 1 of your units that participated. |
| `pillage` | Pillage | mentak | after | TRIGGER (okno reakcji) | ekonomia i płatności | — | If they have 3 or more trade goods, you may take 1 of their trade goods or commodities. |
| `plotsplots` | Plots Within Plots | firmament | when | TRIGGER (okno reakcji) | planety i eksploracja, cele i punkty | — | You can score secret objectives already scored by other players if you fulfill their requirements; this does not count against your secret … |
| `propagation` | Propagation | nekro | when | TRIGGER (okno reakcji) | żetony dowodzenia, technologie | — | You cannot research technology Gain 3 command tokens instead. |
| `puppetsoftheblade` | Puppets of the Blade | firmament | unclassified | — | karty, planety i eksploracja | — | ACTION: Purge The Firmament's faction sheet, leaders, planet cards, and promissory note. Then, gain all of the faction components for The O… |
| `quantum_entanglement` | Quantum Entanglement | ghost | — | FORBID (zakaz) | ruch | — | You treat all systems that contain either an alpha or beta wormhole as adjacent to each other. Game effects cannot prevent you from using t… |
| `quash` | Quash | xxcha | when | TRIGGER (okno reakcji) | ekonomia i płatności, żetony dowodzenia, karty, agenda i głosowanie | — | You may spend 1 token from your strategy pool to discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this age… |
| `raid_formation` | Raid Formation | argent | when | TRIGGER (okno reakcji) | walka, produkcja | — | for each hit produced in excess of your opponent's fighters, choose 1 of your opponent's ships that has SUSTAIN DAMAGE to become damaged. |
| `reclamation` | Reclamation | winnu | after | TRIGGER (okno reakcji) | produkcja | — | You may place 1 PDS and 1 space dock from your reinforcements on Mecatol Rex. |
| `researchteam` | Research Team | deepwrought | when | TRIGGER (okno reakcji) | technologie, planety i eksploracja | — | if your units on that planet are not already coexisting, you may choose for your units to coexist. |
| `riftmeld` | Riftmeld | cabal | when | TRIGGER (okno reakcji) | technologie | — | You may return 1 captured unit of that type to ignore all of the technology's prerequisites. |
| `scavenge` | Scavenge | saar | after | TRIGGER (okno reakcji) | ekonomia i płatności | — | Gain 1 trade good. |
| `scheming` | Scheming | yssaril | when | TRIGGER (okno reakcji) | karty | — | Draw 1 additional action card. Then, choose and discard 1 action card from your hand. |
| `slipstream` | Slipstream | ghost | during | MODIFY (liczba/rzut) | ruch | — | Apply +1 to the move value of each of your ships that starts its movement in your home system or in a system that contains either an alpha … |
| `sorrow` | Sorrow | crimson | — | — | — | — | When you create the game board, place the Sorrow (tile 94) where your home system would normally be placed, then place a inactive breach th… |
| `stall_tactics` | Stall Tactics | yssaril | action | — | karty | — | Discard 1 action card from your hand |
| `star_forge` | Star Forge | muaat | action | MODIFY (liczba/rzut) | walka, produkcja, ekonomia i płatności, żetony dowodzenia | — | Spend 1 token from your strategy pool to place either 2 fighters or 1 destroyer from your reinforcements in a system that contains 1 or mor… |
| `sundered` | Sundered | crimson | — | FORBID (zakaz) | ruch, walka | — | You cannot use wormholes other than epsilon wormholes. Other players' units that move or are placed into your home system are destroyed. |
| `survivalinstinct` | Survival Instinct | ralnel | after | TRIGGER (okno reakcji) | ruch, żetony dowodzenia | — | you may move up to 2 of your ships into the active system from adjacent systems that do not contain your command tokens. |
| `technological_singularity` | Technological Singularity | nekro | unclassified | PERMIT (pozwolenie) | technologie | — | You may gain 1 technology that is owned by that player. |
| `telepathic` | Telepathic | naalu | at_end | — | karty strategii i inicjatywa | — | Place the Naalu "0" token on your strategy card; you are first in initiative order. |
| `terragenesis` | Terragenesis | titans | after | TRIGGER (okno reakcji) | ruch, planety i eksploracja | — | You may place or move 1 sleeper token onto that planet. |
| `the_company` | The Company | nomad | — | MODIFY (liczba/rzut) | — | — | During setup, take the 2 additional Nomad faction agents and place them next to your faction sheet; you have 3 agents |
| `the_tribuni` | The Tribuni | keleres | — | — | żetony dowodzenia, planety i eksploracja | — | During setup, choose an unplayed faction from among the Mentak, the Xxcha and The Argent Flight; take that faction's home system, command t… |
| `unrelenting` | Unrelenting | sardakk | — | MODIFY (liczba/rzut) | walka | — | Apply +1 to the result of each of your unit's combat rolls. |
| `versatile` | Versatile | sol | when | TRIGGER (okno reakcji) | żetony dowodzenia | — | Gain 1 additional command token. |
| `voidborn` | Voidborn | empyrean | — | — | ruch | — | Nebulae do not affect your ships' movement |
| `zeal` | Zeal | argent | when | TRIGGER (okno reakcji) | agenda i głosowanie | — | You always vote first during the agenda phase cast 1 additional vote for each player in the game including you. |

</details>

<details><summary>technologies (102)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `ac2` | Advanced Carrier II | sol | — | — | ruch, walka | — | Cost 3, Combat 9, Move 2, Capacity 8 SUSTAIN DAMAGE |
| `ah` | Aerie Hololattice | argent | — | FORBID (zakaz) | ruch, produkcja, planety i eksploracja | — | Other players cannot move ships through systems that contain your structures. Each planet that contains 1 or more of your structures gains … |
| `aida` | AI Development Algorithm | — | — | MODIFY (liczba/rzut) | produkcja, technologie, status i odświeżanie | — | When you research a unit upgrade technology, you may exhaust this card to ignore any 1 prerequisite. When 1 or more of your units use PRODU… |
| `amd` | Antimass Deflectors | — | — | MODIFY (liczba/rzut) | ruch, walka | ✔ | Your ships can move into and through asteroid fields. When other players' units use SPACE CANNON against your units, apply -1 to the result… |
| `as` | Aetherstream | empyrean | — | MODIFY (liczba/rzut) | ruch | — | After you or one of your neighbors activates a system that is adjacent to an anomaly, you may apply +1 to the move value of all of that pla… |
| `asc` | Assault Cannon | — | — | MODIFY (liczba/rzut) | walka | — | At the start of a space combat in a system that contains 3 or more of your non-fighter ships, your opponent must destroy 1 of their non-fig… |
| `asn` | Agency Supply Network | keleres | — | PERMIT (pozwolenie) | produkcja | — | Once per action, when you resolve a unit's PRODUCTION ability, you may resolve another of your unit's PRODUCTION abilities in any system. |
| `bio` | Bioplasmosis | arborec | — | MODIFY (liczba/rzut) | ruch, planety i eksploracja, status i odświeżanie | — | At the end of the status phase, you may remove any number of infantry from planets you control and place them on 1 or more planets you cont… |
| `bs` | Bio-Stims | — | — | PERMIT (pozwolenie) | technologie, planety i eksploracja, status i odświeżanie | — | You may exhaust this card at the end of your turn to ready 1 of your planets that has a technology specialty or 1 of your other technologie… |
| `cl2` | Crimson Legionnaire II | mahact | — | — | walka, ekonomia i płatności, planety i eksploracja | — | Cost 1(x2), Combat 7 After this unit is destroyed, gain 1 commodity or convert 1 of your commodities to a trade good. Then, place the unit … |
| `cm` | Chaos Mapping | saar | — | FORBID (zakaz) | produkcja | — | Other players cannot activate asteroid fields that contain 1 or more of your ships. At the start of your turn during the action phase, you … |
| `cr2` | Cruiser II | — | — | — | ruch, walka | — | Cost 2, Combat 6, Move 3, Capacity 1 |
| `cv2` | Carrier II | — | — | — | ruch, walka | — | Cost 3, Combat 9, Move 2, Capacity 6 |
| `da` | Duranium Armor | — | — | — | walka | — | During each combat round, after you assign hits to your units, repair 1 of your damaged units that did not use SUSTAIN DAMAGE during this c… |
| `dd2` | Destroyer II | — | — | — | ruch, walka | — | Cost 1, Combat 8, Move 2 ANTI-FIGHTER BARRAGE 6(x3) |
| `det` | Dark Energy Tap | — | — | MODIFY (liczba/rzut) | ruch, walka, planety i eksploracja | — | After you perform a tactical action in a system that contains a frontier token, if you have 1 or more ships in that system, explore that to… |
| `dn2` | Dreadnought II | — | — | FORBID (zakaz) | ruch, walka, karty | — | Cost 4, Combat 5, Move 2, Capacity 1 SUSTAIN DAMAGE, BOMBARDMENT 5 This unit cannot be destroyed by "Direct Hit" action cards. |
| `ds` | Dimensional Splicer | ghost | — | MODIFY (liczba/rzut) | ruch, walka, produkcja | — | At the start of space combat in a system that contains a wormhole and 1 or more of your ships, you may produce 1 hit and assign it to 1 of … |
| `dt2` | Dimensional Tear II | cabal | — | — | ruch, walka, produkcja | — | PRODUCTION 7 This system is a gravity rift; your ships do not roll for this gravity rift. Place a dimensional tear token beneath this unit … |
| `dxa` | Dacxive Animators | — | — | PERMIT (pozwolenie) | walka, produkcja, planety i eksploracja | — | After you win a ground combat, you may place 1 infantry from your reinforcements on that planet. |
| `ers` | E-Res Siphons | jolnar | — | MODIFY (liczba/rzut) | ekonomia i płatności | — | After another player activates a system that contains 1 or more of your ships, gain 4 trade goods. |
| `executiveorder` | Executive Order | keleres | — | PERMIT (pozwolenie) | ekonomia i płatności, karty, agenda i głosowanie, status i odświeżanie | — | ACTION: Exhaust this card and draw the top or bottom card of the Agenda deck. Players immediately vote on this agenda as if you were the sp… |
| `exile2` | Exile II | crimson | — | PERMIT (pozwolenie) | ruch, walka | — | Cost 1, Combat 7, Move 2, ANTI-FIGHTER BARRAGE 6 (x3). At the end of any players' combat in this unit's system or up to 2 systems away, you… |
| `exo2` | Exotrireme II | sardakk | — | FORBID (zakaz) | ruch, walka, karty | — | Cost 4, Combat 5, Move 2, Capacity 1 SUSTAIN DAMAGE, BOMBARDMENT 4(x2) This unit cannot be destroyed by "Direct Hit" action cards. After a … |
| `ff2` | Fighter II | — | — | PERMIT (pozwolenie) | ruch, walka, żetony dowodzenia | — | Cost 1(x2), Combat 8, Move 2 This unit may move without being transported. Fighters in excess of your ships' capacity count against your fl… |
| `ffac2` | Floating Factory II | saar | — | REPLACE (instead of) | ruch, walka, produkcja, planety i eksploracja | — | Move 2, Capacity 5 PRODUCTION 7. This unit is placed in the space area instead of on a planet. This unit can move and retreat as if it were… |
| `fl` | Fleet Logistics | — | — | REPLACE (instead of) | — | — | During each of your turns of the action phase, you may perform 2 actions instead of 1. |
| `gd` | Gravity Drive | — | — | MODIFY (liczba/rzut) | ruch | — | After you activate a system, apply +1 to the move value of 1 of your ships during this tactical action. |
| `gls` | Graviton Laser System | — | — | MODIFY (liczba/rzut) | walka, produkcja, status i odświeżanie | — | You may exhaust this card before 1 or more of your units uses SPACE CANNON; hits produced by those units must be assigned to non-fighter sh… |
| `gr` | Genetic Recombination | mahact | — | PERMIT (pozwolenie) | produkcja, żetony dowodzenia, agenda i głosowanie, status i odświeżanie | — | You may exhaust this card before a player casts votes; that player must cast at least 1 vote for an outcome of your choice or remove 1 toke… |
| `hcf2` | Hybrid Crystal Fighter II | naalu | — | PERMIT (pozwolenie) | ruch, walka, żetony dowodzenia | — | Cost 1(x2), Combat 7, Move 2 This unit may move without being transported. Fighters in excess of your ships' capacity count as 1/2 of a shi… |
| `helios2` | 4X41C "Helios" V2 | bastion | — | MODIFY (liczba/rzut) | produkcja, ekonomia i płatności, planety i eksploracja | — | This unit's PRODUCTION value is equal to 4 more than the resource value of this planet. The resource value of this planet is increased by 2… |
| `hm` | Hyper Metabolism | — | — | REPLACE (instead of) | żetony dowodzenia, status i odświeżanie | — | During the status phase, gain 3 command tokens instead of 2. |
| `ht2` | Hel-Titan II | titans | — | FORBID (zakaz) | ruch, walka, produkcja | — | Combat 6 PLANETARY SHIELD, SPACE CANNON 5, SUSTAIN DAMAGE, PRODUCTION 1 This unit is treated as both a structure and a ground force. It can… |
| `htp` | Hegemonic Trade Policy | winnu | — | MODIFY (liczba/rzut) | produkcja, ekonomia i płatności, planety i eksploracja, status i odświeżanie | — | Exhaust this card when 1 or more of your units use PRODUCTION; swap the resource and influence values of 1 planet you control during that u… |
| `hydrothermal` | Hydrothermal Mining | deepwrought | — | — | ekonomia i płatności, status i odświeżanie | — | At the start of the status phase, gain 1 trade good for each ocean card in play. |
| `ic` | Impulse Core | yin | — | PERMIT (pozwolenie) | walka, produkcja | — | At the start of a space combat, you may destroy 1 of your cruisers or destroyers in the active system to produce 1 hit against your opponen… |
| `ie` | Integrated Economy | — | — | PERMIT (pozwolenie) | produkcja, ekonomia i płatności, planety i eksploracja | — | After you gain control of a planet, you may produce any number of units on that planet that have a combined cost equal to or less than that… |
| `iihq` | I.I.H.Q. Modernization | keleres | — | FORBID (zakaz) | ruch, planety i eksploracja | — | You are neighbors with all players that have units or control planets in or adjacent to the Mecatol Rex system. Gain the Custodia Vigilia p… |
| `inf2` | Infantry II | — | — | — | walka, planety i eksploracja | — | Cost 1(x2), Combat 7 After this unit is destroyed, roll 1 die. If the result is 6 or greater, place the unit on this card. At the start of … |
| `is` | Inheritance Systems | l1z1x | — | PERMIT (pozwolenie) | ekonomia i płatności, technologie, status i odświeżanie | — | You may exhaust this card and spend 2 resources when you research a technology; ignore all of that technology's prerequisites. |
| `it` | Instinct Training | xxcha | — | PERMIT (pozwolenie) | ekonomia i płatności, żetony dowodzenia, karty, status i odświeżanie | — | You may exhaust this card and spend 1 token from your strategy pool when another player plays an action card; cancel that action card. |
| `l4` | L4 Disruptors | letnev | — | FORBID (zakaz) | walka | — | During an invasion, units cannot use SPACE CANNON against your units. |
| `lgf` | Lazax Gate Folding | winnu | — | — | ruch, produkcja, planety i eksploracja, status i odświeżanie | — | During your tactical actions, if you do not control Mecatol Rex, treat its system as if it has both an α and β wormhole. ACTION: If you con… |
| `linkship2` | Linkship II | ralnel | — | PERMIT (pozwolenie) | ruch, walka | — | Cost 1, Combat 8, Move 4, ANTI-FIGHTER BARRAGE 6 (x3). This unit can use the SPACE CANNON ability of one of your structures in its space ar… |
| `lw2` | Letani Warrior II | arborec | — | — | walka, produkcja, planety i eksploracja | — | Cost 1(x2), Combat 7 PRODUCTION 2 After this unit is destroyed, roll 1 die. If the result is 6 or greater, place the unit on this card. At … |
| `lwd` | Light/Wave Deflector | — | — | PERMIT (pozwolenie) | ruch | — | Your ships can move through systems that contain other players' ships. |
| `m2` | Memoria II | nomad | — | MODIFY (liczba/rzut) | ruch, walka | — | Cost 8, Combat 5(x2), Move 2, Capacity 6 SUSTAIN DAMAGE, ANTI-FIGHTER BARRAGE 5(x3) You may treat this unit as if it were adjacent to syste… |
| `mc` | Mirror Computing | mentak | — | REPLACE (instead of) | ekonomia i płatności | — | When you spend trade goods, each trade good is worth 2 resources or influence instead of 1. |
| `md` | Magen Defense Grid ΩΩ | — | — | MODIFY (liczba/rzut) | walka, produkcja, planety i eksploracja | — | When any player activates a system that contains 1 or more of your structures, place 1 infantry from your reinforcements with each of those… |
| `md_base` | Magen Defense Grid | — | — | FORBID (zakaz) | walka, planety i eksploracja, status i odświeżanie | — | You may exhaust this card at the start of a round of ground combat on a planet that contains 1 or more of your units that have PLANETARY SH… |
| `md_c1` | Magen Defense Grid Ω | — | — | MODIFY (liczba/rzut) | walka, produkcja, planety i eksploracja | — | At the start of ground combat on a planet that contains 1 or more of your structures, produce 1 hit and assign it to 1 of your opponent's g… |
| `mi` | Mageon Implants | yssaril | — | — | karty, status i odświeżanie | — | ACTION: Exhaust this card to look at another player's hand of action cards. Choose 1 of those cards and add it to your hand. |
| `mr` | Magmus Reactor | muaat | — | MODIFY (liczba/rzut) | ruch, produkcja | — | Your ships can move into supernovas. Each supernova that contains 1 or more of your units gains the PRODUCTION 5 ability as if it were 1 of… |
| `nanomachines` | Nanomachines | ralnel | — | — | karty, planety i eksploracja, status i odświeżanie | — | ACTION: Exhaust this card to place 1 PDS on a planet you control. ACTION: Exhaust this card to repair all of your damaged units. ACTION: Ex… |
| `nekroc4r` | ???\_ERROR\_ERROR\_??? | nekro | — | — | karty, planety i eksploracja, status i odświeżanie | — | ACTION: Exhaust this card to place 1 PDS on a planet you control. ACTION: Exhaust this card to repair all of your damaged units. ACTION: Ex… |
| `nekroc4y` | ???\_NULL\_REFERENCE\_??? | nekro | — | PERMIT (pozwolenie) | walka, produkcja | — | When one of your ships is destroyed, you may produce a ship of the same type at a space dock in your home system. |
| `nes` | Non-Euclidean Shielding | letnev | — | REPLACE (instead of) | walka | — | When 1 of your units uses SUSTAIN DAMAGE, cancel 2 hits instead of 1. |
| `nf` | Nullification Field | xxcha | — | MODIFY (liczba/rzut) | ekonomia i płatności, żetony dowodzenia, status i odświeżanie | — | After another player activates a system that contains 1 or more of your ships, you may exhaust this card and spend 1 token from your strate… |
| `ng` | Neuroglaive | naalu | — | MODIFY (liczba/rzut) | produkcja, żetony dowodzenia | — | After another player activates a system that contains 1 or more of your ships, that player removes 1 token from their fleet pool and return… |
| `nm` | Neural Motivator | — | — | REPLACE (instead of) | karty, status i odświeżanie | — | During the status phase, draw 2 action cards instead of 1. |
| `pa` | Psychoarchaeology | — | — | PERMIT (pozwolenie) | ekonomia i płatności, technologie, planety i eksploracja, status i odświeżanie | — | You can use technology specialties on planets you control without exhausting them, even if those planets are exhausted. During the action p… |
| `parasite-firm` | Neural Parasite (Firmament) | firmament | — | PERMIT (pozwolenie) | produkcja, planety i eksploracja, status i odświeżanie | — | At the start of the status phase, you may place 1 infantry from your reinforcements on a planet you control in your home system. Flip this … |
| `parasite-obs` | Neural Parasite (Obsidian) | obsidian | — | FORBID (zakaz) | ruch, walka, technologie | — | At the start of your turn, destroy 1 of another player's infantry in or adjacent to a system that contains your infantry. This technology c… |
| `pds2` | PDS II | — | — | PERMIT (pozwolenie) | ruch, walka | — | PLANETARY SHIELD, SPACE CANNON 5 You may use this unit's SPACE CANNON against ships that are adjacent to this unit's system. |
| `pfa` | Pre-Fab Arcologies | naaz | — | — | planety i eksploracja, status i odświeżanie | — | After you explore a planet, ready that planet. |
| `pi` | Predictive Intelligence | — | — | MODIFY (liczba/rzut) | żetony dowodzenia, agenda i głosowanie, status i odświeżanie | — | At the end of your turn, you may exhaust this card to redistribute your command tokens. When you cast votes during the agenda phase, you ma… |
| `planesplitter-firm` | Planesplitter (Firmament) | firmament | — | — | — | — | When you gain this card, put The Fracture into play. Flip this card if the Obsidian faction is in play. |
| `planesplitter-obs` | Planesplitter (Obsidian) | obsidian | — | FORBID (zakaz) | ruch, technologie | — | When you perform a strategic action, you may move an ingress token into a system that contains or is adjacent to your units. This technolog… |
| `pm` | Production Biomes | hacan | — | — | produkcja, ekonomia i płatności, żetony dowodzenia, status i odświeżanie | — | ACTION: Exhaust this card and spend 1 token from your strategy pool to gain 4 trade goods and choose 1 other player; that player gains 2 tr… |
| `proxima` | Proxima Targeting VI | bastion | — | PERMIT (pozwolenie) | walka, produkcja | — | Cancel 1 hit produced by BOMBARDMENT rolls made against your ground forces for each of your galvanized units present. At the start of a rou… |
| `ps` | Plasma Scoring | — | — | MODIFY (liczba/rzut) | walka | — | When 1 or more of your units use BOMBARDMENT or SPACE CANNON, 1 of those units may roll 1 additional die. |
| `pws2` | Prototype War Sun II | muaat | — | — | ruch, walka | — | Cost 10, Combat 3(x3), Move 3, Capacity 6 SUSTAIN DAMAGE, BOMBARDMENT 3(x3) Other players' units in this system lose PLANETARY SHIELD. |
| `qdn` | Quantum Datahub Node | hacan | — | PERMIT (pozwolenie) | ekonomia i płatności, żetony dowodzenia, karty strategii i inicjatywa | — | At the end of the strategy phase, you may spend 1 token from your strategy pool and give another player 3 of your trade goods. If you do, g… |
| `radical` | Radical Advancement | deepwrought | — | MODIFY (liczba/rzut) | technologie, status i odświeżanie | — | At the start of the status phase, you may replace one of your non-unit upgrade technologies with a technology of the same color that has ex… |
| `sar` | Self-Assembly Routines | — | — | MODIFY (liczba/rzut) | walka, produkcja, ekonomia i płatności, planety i eksploracja, status i odświeżanie | — | After 1 or more of your units use PRODUCTION, you may exhaust this card to place 1 mech from your reinforcements on a planet you control in… |
| `sc` | Supercharge | naaz | — | MODIFY (liczba/rzut) | walka, status i odświeżanie | — | At the start of a combat round, you may exhaust this card to apply +1 to the result of each of your unit's combat rolls during this combat … |
| `scc` | Spatial Conduit Cylinder | jolnar | — | MODIFY (liczba/rzut) | ruch, status i odświeżanie | — | You may exhaust this card after you activate a system that contains 1 or more of your units; that system is adjacent to all other systems t… |
| `sd2` | Space Dock II | — | — | MODIFY (liczba/rzut) | produkcja, ekonomia i płatności, planety i eksploracja | — | PRODUCTION X This unit's PRODUCTION value is equal to 4 more than the resource value of this planet. Up to 3 fighters in this system do not… |
| `sdn` | Scanlink Drone Network | — | — | MODIFY (liczba/rzut) | planety i eksploracja | — | When you activate a system, you may explore 1 planet in that system which contains 1 or more of your units. |
| `sdn2` | Super Dreadnought II | l1z1x | — | FORBID (zakaz) | ruch, walka, karty | — | Cost 4, Combat 4, Move 2, Capacity 2 SUSTAIN DAMAGE, BOMBARDMENT 4 This unit cannot be destroyed by "Direct Hit" action cards. |
| `se2` | Saturn Engine II | titans | — | — | ruch, walka | — | Cost 2, Combat 6, Move 3, Capacity 2 SUSTAIN DAMAGE |
| `so` | Salvage Operations | mentak | — | PERMIT (pozwolenie) | walka, produkcja, ekonomia i płatności | — | After you win or lose a space combat, gain 1 trade good; if you won the combat, you may also produce 1 ship in that system of any ship type… |
| `so2` | Spec Ops II | sol | — | — | walka, planety i eksploracja | — | Cost 1(x2), Combat 6 After this unit is destroyed, roll 1 die. If the result is 5 or greater, place the unit on this card. At the start of … |
| `sr` | Sling Relay | — | — | — | produkcja, status i odświeżanie | — | ACTION: Exhaust this card to produce 1 ship in any system that contains one of your space docks. |
| `st` | Sarween Tools | — | — | MODIFY (liczba/rzut) | produkcja | — | When 1 or more of your units use PRODUCTION, reduce the combined cost of the produced units by 1. |
| `subatomic` | Subatomic Splicer | crimson | — | PERMIT (pozwolenie) | walka, produkcja | — | When one of your ships is destroyed, you may produce a ship of the same type at a space dock in your home system. |
| `swa2` | Strike Wing Alpha II | argent | — | — | ruch, walka | — | Cost 1, Combat 7, Move 2, Capacity 1 ANTI-FIGHTER BARRAGE 6(x3) When this unit uses ANTI-FIGHTER BARRAGE, each result of 9 or 10 also destr… |
| `tcs` | Temporal Command Suite | nomad | — | PERMIT (pozwolenie) | status i odświeżanie | — | After any player's agent becomes exhausted, you may exhaust this card to ready that agent; if you ready another player's agent, you may per… |
| `td` | Transit Diodes | — | — | MODIFY (liczba/rzut) | planety i eksploracja, status i odświeżanie | — | You may exhaust this card at the start of your turn during the action phase; remove up to 4 of your ground forces from the game board and p… |
| `tp` | Transparasteel Plating | yssaril | — | FORBID (zakaz) | karty | — | During your turn of the action phase, players that have passed cannot play action cards. |
| `vax` | Valefar Assimilator X | nekro | — | REPLACE (instead of) | technologie | — | When you would gain another player's technology using 1 of your faction abilities, you may place the "X" assimilator token on a faction tec… |
| `vay` | Valefar Assimilator Y | nekro | — | REPLACE (instead of) | technologie | — | When you would gain another player's technology using 1 of your faction abilities, you may place the "Y" assimilator token on a faction tec… |
| `vpw` | Valkyrie Particle Weave | sardakk | — | MODIFY (liczba/rzut) | walka, produkcja | — | After making combat rolls during a round of ground combat, if your opponent produced 1 or more hits, you produce 1 additional hit. |
| `vtx` | Vortex | cabal | — | MODIFY (liczba/rzut) | ruch, produkcja, status i odświeżanie | — | ACTION: Exhaust this card to choose another player's non-structure unit in a system that is adjacent to 1 or more of your space docks. Capt… |
| `vw` | Voidwatch | empyrean | — | MODIFY (liczba/rzut) | ruch, karty | — | After a player moves ships into a system that contains 1 or more of your units, they must give you 1 promissory note from their hand, if ab… |
| `wg` | Wormhole Generator | ghost | — | — | ruch, planety i eksploracja, status i odświeżanie | — | ACTION: Exhaust this card to place or move a Creuss wormhole token into either a system that contains a planet you control or a non-home sy… |
| `ws` | War Sun | — | — | — | ruch, walka | — | Cost 12, Combat 3(x3), Move 2, Capacity 6 SUSTAIN DAMAGE, BOMBARDMENT 3(x3) Other players' units in this system lose PLANETARY SHIELD. |
| `x89` | X-89 Bacterial Weapon Ω | — | — | MODIFY (liczba/rzut) | walka, planety i eksploracja | — | After 1 or more of your units use BOMBARDMENT against a planet, if at least 1 of your opponent's infantry was destroyed, you may destroy al… |
| `x89_base` | X-89 Bacterial Weapon | — | — | MODIFY (liczba/rzut) | walka, planety i eksploracja, status i odświeżanie | — | ACTION: Exhaust this card and choose 1 planet in a system that contains 1 or more of your ships that have BOMBARDMENT; destroy all infantry… |
| `x89c4` | X-89 Bacterial Weapon ΩΩ | — | — | — | walka, produkcja, planety i eksploracja, status i odświeżanie | — | Double the hits produced by your units' BOMBARDMENT and ground combat rolls. Exhaust each planet you use BOMBARDMENT against. |
| `yso` | Yin Spinner Omega | yin | — | MODIFY (liczba/rzut) | produkcja, planety i eksploracja | — | After you produce units, place up to 2 infantry from your reinforcements on any planet you control or in any space area that contains 1 or … |

</details>

<details><summary>breakthroughs (31)</summary>

| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |
|---|---|---|---|---|---|:---:|---|
| `arborecbt` | Psychospore | arborec | — | MODIFY (liczba/rzut) | produkcja, żetony dowodzenia, status i odświeżanie | — | ACTION: Exhaust this card to remove a command token from a system that contains 1 or more of your infantry and return it to your reinforcem… |
| `argentbt` | Wing Transfer | argent | — | PERMIT (pozwolenie) | ruch, produkcja, żetony dowodzenia | — | When you activate a system that contains only your units, you may place command tokens from your reinforcements into any systems adjacent t… |
| `bastionbt` | The Icon | bastion | — | PERMIT (pozwolenie) | produkcja, żetony dowodzenia, status i odświeżanie | — | When you produce ships, you may exhaust this card to place those ships in a system that contains 1 of your command tokens, at least 1 of yo… |
| `cabalbt` | Al'Raith Ix Ianovar | cabal | — | MODIFY (liczba/rzut) | ruch, walka | — | This breakthrough causes The Fracture to enter play without a roll, if it is not already in play. After this card enters play, move up to 2… |
| `crimsonbt` | Resonance Generator | crimson | — | MODIFY (liczba/rzut) | ruch, status i odświeżanie | — | During your tactical actions, apply +1 to the move value of each of your ships that starts its movement in your home system or in a system … |
| `deepwroughtbt` | Visionaria Select | deepwrought | — | PERMIT (pozwolenie) | ekonomia i płatności, technologie, karty, status i odświeżanie | — | ACTION: Exhaust this card to allow each other player to spend 3 trade goods and give you 1 promissory note. Each player that does may resea… |
| `empyreanbt` | Void Tether | empyrean | — | PERMIT (pozwolenie) | ruch, planety i eksploracja | — | When you activate a system that contains or is adjacent to a unit or planet you control, you may place or move 1 of your Void Tether tokens… |
| `firmamentbt` | The Sowing | firmament | — | PERMIT (pozwolenie) | ekonomia i płatności, status i odświeżanie | — | When you gain this card and at the start of the status phase, you may place up to 3 of your trade goods on this card. Flip this card if you… |
| `ghostbt` | Particle Synthesis | ghost | — | — | ruch, produkcja, planety i eksploracja | — | Each wormhole in a system that contains your ships gains PRODUCTION 1 as if it were a unit you control. Reduce the combined cost of units y… |
| `hacanbt` | Auto-Factories | hacan | — | MODIFY (liczba/rzut) | produkcja, żetony dowodzenia | — | When you produce 3 or more non-fighter ships, place 1 command token from your reinforcements into your fleet pool. |
| `jolnarbt` | Specialist Compounds | jolnar | — | REPLACE (instead of) | ekonomia i płatności, technologie, planety i eksploracja, status i odświeżanie, karty strategii i inicjatywa | — | When you research technology using the 'Technology' strategy card, you may exhaust a planet that has a technology specialty instead of spen… |
| `keleresbt` | I.I.H.Q. Modernization | keleres | — | — | ruch, planety i eksploracja | — | When you gain this card, gain the Custodia Vigilia planet card and its legendary planet ability card. You are neighbors with all players th… |
| `l1z1xbt` | Fealty Uplink | l1z1x | — | — | produkcja, ekonomia i płatności, planety i eksploracja | — | When you gain control of a planet, place infantry from your reinforcements equal to that planet's influence value on that planet. |
| `letnevbt` | Gravleash Maneuvers | letnev | — | — | ruch, walka | — | Before you roll dice during space combat, apply +X to the results of 1 of your ship's rolls, where X is the number of ship types you have i… |
| `mahactbt` | Vaults of the Heir | mahact | — | — | technologie, planety i eksploracja, status i odświeżanie | — | ACTION: Exhaust this card and purge 1 of your technologies to gain 1 relic. |
| `mentakbt` | The Table's Grace | mentak | — | PERMIT (pozwolenie) | ruch, walka, technologie | — | If you have the Cruiser II unit upgrade technology, flip this card and place it on top of cruiser II. Corsair [Cost 2, Combat 6, Move 3, Ca… |
| `muaatbt` | Stellar Genesis | muaat | — | PERMIT (pozwolenie) | ruch, planety i eksploracja, status i odświeżanie | — | When you gain this card, place the Avernus planet token into a non-home system that is adjacent to a planet you control; gain the Avernus p… |
| `naalubt` | Mindsieve | naalu | — | PERMIT (pozwolenie) | ekonomia i płatności, żetony dowodzenia, karty, karty strategii i inicjatywa | — | When you would resolve the secondary ability of another player's strategy card, you may give them a promissory note to resolve it without s… |
| `naazbt` | Absolute Synergy | naaz | — | FORBID (zakaz) | ruch, walka, produkcja | — | When you have 4 mechs in the same system, you may return 3 of those mechs to your reinforcements to flip this card and place it on top of y… |
| `nekrobt` | Valefar Assimilator Z | nekro | — | REPLACE (instead of) | technologie | — | When you would gain another player's technology using one of your faction abilities, you may instead place one of your "Z" assimilator toke… |
| `nomadbt` | Thunder's Paradox | nomad | — | PERMIT (pozwolenie) | status i odświeżanie | — | At the start of any player's turn, you may exhaust 1 of your agents to ready any other agent. |
| `obsidianbt` | The Reaping | obsidian | — | — | walka, ekonomia i płatności, status i odświeżanie | — | Place 1 trade good from the supply onto this card each time you win a combat against a puppeted player. At the start of the status phase, g… |
| `ralnelbt` | Data Skimmer | ralnel | — | REPLACE (instead of) | karty | — | During the action phase, if you have not passed, when other players would discard action cards, they are placed on this card instead. When … |
| `saarbt` | Deorbit Barrage | saar | — | — | walka, ekonomia i płatności, planety i eksploracja, status i odświeżanie | — | ACTION: Exhaust this card and spend any amount of resources to choose a planet up to 2 systems away from an asteroid field that contains yo… |
| `sardakkbt` | N'orr Supremacy | sardakk | — | — | walka, żetony dowodzenia, technologie | — | After you win a combat, either gain 1 command token or research a unit upgrade technology. |
| `solbt` | Bellum Gloriosum | sol | — | PERMIT (pozwolenie) | produkcja | — | When you produce a ship that has capacity, you may also produce any combination of ground forces or fighters up to that ship's capacity; th… |
| `titansbt` | Slumberstate Computing | titans | — | REPLACE (instead of) | walka, karty, planety i eksploracja, status i odświeżanie | — | When COALESCENCE results in a ground combat, if you commit no other units, you may choose for your units to coexist instead. During the sta… |
| `winnubt` | Imperator | winnu | — | MODIFY (liczba/rzut) | ruch, walka, planety i eksploracja | — | Apply +1 to the results of each of your unit's combat rolls for each "Support for the Throne" in your opponent's play area. After you activ… |
| `xxchabt` | Archon's Gift | xxcha | — | PERMIT (pozwolenie) | ekonomia i płatności | — | You can spend influence as if it were resources. You can spend resources as if it were influence. |
| `yinbt` | Yin Ascendant | yin | — | — | cele i punkty | — | When you gain this card or score a public objective, gain the alliance ability of a random, unused faction. |
| `yssarilbt` | Deepgloom Executable | yssaril | — | PERMIT (pozwolenie) | — | — | You can allow other players to use your STALL TACTICS or SCHEMING faction abilities; when you do, you may resolve a transaction with that p… |

</details>
