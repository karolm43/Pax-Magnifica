# Okna czasowe komponentów (generowany — nie edytuj ręcznie)

Wygenerowano: `uv run python -m src.audit.timing_catalog --write`. Opis kontraktu: `RULES.md` 54, kod: `core/game_events.py` (zdarzenia, klasyfikator), `core/triggers.py` (emisja), `core/active_effects.py` (efekty trwałe).
Klasyfikacja to HEURYSTYKA po słowach kluczowych; wszystko, co nie dostało zdarzenia, jest w sekcji „Przypadki szczególne”.

## 1. Kontrakt silnika (skrót)

* **Okno = para (zdarzenie, moment)** + filtry kontekstu (np. `phase=strategy`). Momenty: `before`, `when`, `after`, `start`, `end`, `during`, `instead`, `any`, `action`.
* **Kolejność** (R_abilities): wszystkie `when` przed `after`; wszystkie `after` przed następnym `before`. Ta sama chwila w fazie akcji: kolejność inicjatywy od gracza aktywnego; w fazie strategii i agendy: od mówcy zgodnie z zegarem.
* **Obowiązkowe vs opcjonalne:** zdolność z komponentu w grze jest obowiązkowa, chyba że ma „may” (wtedy silnik tworzy ofertę i otwiera okno REACTION dla graczy z publicznym źródłem).
* **Karty z ręki** (karty akcji, ukryte notki) NIE tworzą ofert — grane są przez STOP (RULES.md 43.4), żeby pytanie nie zdradzało ręki.
* **Efekt trwały:** zakres `turn`, `tactical_action`, `combat`, `combat_round`, `phase`, `round`, `game` albo `while_in_play`; wygasa na zdarzeniach końca zakresu. Efekt z określonym czasem trwania zostaje, nawet gdy komponent zniknie (R_abilities).
* **`would`** w oknie („when you would ...”) = przed skutkiem; to miejsce na zastąpienie (REPLACE).

## 2. Zdarzenia: kto ich potrzebuje i czy silnik je emituje

`Emisja` = funkcja silnika, która woła `triggers.fire` (— = zdarzenie tylko zdefiniowane).

| Zdarzenie | Znaczenie | Komponentów | Momenty | Kategorie | Emisja |
|---|---|---:|---|---|---|
| `game.setup` | Przygotowanie gry (tworzenie planszy, rozdanie kart). | 7 | during×4, when×2, before×1 | abilities×6, galactic_events×1 | `game_setup.reveal_objectives` |
| `game.faction_in_play` | Frakcja wchodzi do gry (setup, flip Obsidian). | 1 | when×1 | abilities×1 | — |
| `state.condition` | Warunek stanu spełniony (np. 4 mechy w systemie). | 1 | when×1 | breakthroughs×1 | — |
| `round` | Początek/koniec rundy. | 0 | — | — | `turn_flow.next_round` |
| `phase` | Początek/koniec fazy. | 26 | start×11, during×9, end×5, when×1 | technologies×8, breakthroughs×5, action_cards×3, abilities×3, leaders×3, promissory_notes×2, relics×1, explores×1 | `turn_flow.next_phase` |
| `status.step` | Krok fazy statusu (1-8). | 2 | when×2 | promissory_notes×1, abilities×1 | — |
| `turn` | Początek/koniec tury gracza w fazie akcji. | 19 | start×12, end×5, during×2 | technologies×9, action_cards×3, promissory_notes×3, leaders×2, abilities×1, breakthroughs×1 | `turn_flow` |
| `speaker.changed` | Żeton mówcy zmienił właściciela. | 0 | — | — | `strategy_phase.set_speaker` |
| `player.passed` | Gracz spasował. | 0 | — | — | `turn_flow.pass_turn` |
| `player.last_passed` | Ostatni gracz spasował. | 1 | after×1 | leaders×1 | `turn_flow.pass_turn` |
| `strategy.card_chosen` | Gracz wybiera kartę strategii (faza strategii). | 1 | when×1 | action_cards×1 | `strategy_phase.pick_strategy_card` |
| `strategy.cards_returned` | Karty strategii wracają na stół (status). | 1 | when×1 | action_cards×1 | — |
| `strategy.action` | Akcja strategiczna / jej ability primary-secondary. | 5 | when×3, after×1, start×1 | action_cards×1, promissory_notes×1, abilities×1, technologies×1, breakthroughs×1 | `strategic_action` |
| `strategy.token_spent` | Żeton z puli strategicznej wydany (secondary, cele, zdolności). | 4 | when×3, after×1 | leaders×2, relics×1, abilities×1 | `command_tokens.spend_strategy_token` |
| `strategy.imperial_victory_point` | Punkt zwycięstwa z drugiej klauzuli Imperial (kontrola Mecatol Rex). | 0 | — | — | `strategy_cards.imperial` |
| `tactical.action` | Akcja taktyczna (początek/koniec). | 8 | after×3, end×3, during×2 | abilities×3, leaders×2, relics×1, promissory_notes×1, technologies×1 | `tactical.end_tactical_action` |
| `tactical.system_activated` | System aktywowany. | 36 | after×30, when×6 | action_cards×14, technologies×7, leaders×5, abilities×4, promissory_notes×3, breakthroughs×3 | `tactical.activate_system` |
| `tactical.ships_moved` | Statki weszły do aktywnego systemu. | 14 | after×11, before×1, end×1, when×1 | leaders×6, action_cards×2, relics×1, promissory_notes×1, explores×1, galactic_events×1, abilities×1, technologies×1 | `movement.move_ships` |
| `tactical.units_committed` | Siły naziemne zaangażowane do lądowania. | 5 | after×3, when×1, during×1 | action_cards×2, promissory_notes×1, abilities×1, leaders×1 | `invasion` |
| `component.action` | Akcja komponentu zagrana. | 133 | action×131, after×2 | action_cards×43, leaders×31, explores×23, technologies×10, promissory_notes×9, relics×7, abilities×5, breakthroughs×5 | `action_cards.play_action_card` |
| `component.decision` | Decyzja gracza otwarta przez efekt komponentu (okno badania). | 0 | — | — | `research_offer.begin` |
| `combat` | Początek/koniec walki. | 19 | start×13, end×5, during×1 | promissory_notes×5, leaders×5, technologies×5, abilities×3, action_cards×1 | `battle.start_combat / battle._after_losses` |
| `combat.round` | Początek/koniec rundy walki. | 21 | start×16, after×3, during×1, end×1 | action_cards×10, technologies×4, abilities×3, leaders×3, relics×1 | `battle.roll_round` |
| `combat.step` | Nazwany krok walki. | 3 | start×1, during×1, after×1 | action_cards×1, relics×1, leaders×1 | — |
| `combat.roll` | Rzut (combat, AFB, space cannon, bombardment). | 5 | after×3, before×2 | action_cards×2, relics×1, promissory_notes×1, breakthroughs×1 | `battle.roll_round` |
| `combat.hits_assigned` | Przypisanie trafień. | 10 | before×9, after×1 | action_cards×8, leaders×1, technologies×1 | `battle.assign_combat_hits` |
| `unit.sustain_damage` | Jednostka użyła Sustain Damage. | 7 | after×5, when×2 | action_cards×5, leaders×1, technologies×1 | `battle.assign_combat_hits` |
| `unit.destroyed` | Jednostka zniszczona. | 10 | when×7, after×3 | leaders×5, action_cards×2, technologies×2, abilities×1 | `unit_ops.remove_units` |
| `unit.removed` | Jednostka usunięta bez zniszczenia (nadwyżka, zwrot do rezerwy). | 0 | — | — | `unit_ops.remove_units` |
| `combat.won` | Gracz wygrał walkę. | 6 | after×5, when×1 | technologies×2, action_cards×1, abilities×1, leaders×1, breakthroughs×1 | `battle._after_losses` |
| `combat.retreat` | Odwrót ogłoszony. | 2 | after×1, when×1 | action_cards×1, leaders×1 | `battle.announce_retreat` |
| `invasion` | Początek inwazji. | 4 | start×3, during×1 | action_cards×3, technologies×1 | `invasion` |
| `unit.ability_used` | Jednostka użyła zdolności (AFB, bombardment, space cannon). | 8 | when×5, after×3 | technologies×3, leaders×2, action_cards×1, promissory_notes×1, abilities×1 | `battle / invasion / space_cannon` |
| `faction.ability_used` | Zdolność frakcji użyta (np. Pillage przeciw graczowi). | 1 | after×1 | leaders×1 | `faction_components.ability_used` |
| `unit.placed` | Struktura/jednostka postawiona. | 0 | — | — | `unit_ops.place_units` |
| `component.readied` | Komponent odświeżony. | 0 | — | — | `agenda_phase._ready_all_planets` |
| `component.exhausted` | Komponent (np. agent) wyczerpany. | 1 | after×1 | technologies×1 | `faction_components.pay_cost` |
| `combat.hits_produced` | Trafienia wyprodukowane przeciw graczowi. | 1 | when×1 | relics×1 | — |
| `unit.galvanized` | Jednostka galvanize. | 1 | when×1 | abilities×1 | — |
| `unit.coexist` | Jednostki zaczynają współistnieć na planecie. | 1 | when×1 | abilities×1 | — |
| `production.used` | Jednostki użyły PRODUCTION. | 10 | when×9, after×1 | action_cards×5, leaders×3, technologies×2 | `production.produce` |
| `production.units_produced` | Jednostki wyprodukowane. | 12 | when×11, after×1 | leaders×6, breakthroughs×3, technologies×2, abilities×1 | `production.produce` |
| `planet.control_gained` | Gracz zdobył kontrolę nad planetą. | 8 | when×4, after×4 | abilities×3, action_cards×2, leaders×1, technologies×1, breakthroughs×1 | `control.set_planet_control` |
| `planet.control_lost` | Gracz stracił kontrolę nad planetą. | 0 | — | — | `control.set_planet_control` |
| `planet.explored` | Planeta zbadana (karta eksploracji rozstrzygnięta; frontier nie emituje). | 3 | after×2, when×1 | abilities×2, technologies×1 | `exploration.resolve` |
| `planet.exhausted` | Planety wyczerpane (płatność). | 1 | when×1 | leaders×1 | — |
| `economy.trade_goods_gained` | Gracz zdobył trade goods. | 2 | after×1, when×1 | abilities×1, leaders×1 | `economy.gain_trade_goods` |
| `economy.resources_spent` | Gracz wydał zasoby/wpływy. | 3 | when×3 | leaders×2, technologies×1 | — |
| `economy.commodities_replenished` | Commodities uzupełnione. | 3 | when×2, after×1 | promissory_notes×1, galactic_events×1, leaders×1 | `economy.replenish_commodities` |
| `economy.commodities_given` | Commodities oddane innemu graczowi. | 0 | — | — | — |
| `tokens.gained` | Gracz zdobył żetony dowodzenia. | 0 | — | — | — |
| `tokens.placed` | Żeton dowodzenia położony w systemie. | 1 | after×1 | leaders×1 | `command_tokens.place_token` |
| `transaction` | Transakcja (negocjacja/rozstrzygnięcie). | 3 | when×2, after×1 | action_cards×2, abilities×1 | `transaction.resolve_transaction` |
| `technology.research` | Badanie technologii. | 8 | when×7, after×1 | abilities×3, relics×1, promissory_notes×1, leaders×1, technologies×1, breakthroughs×1 | `technology.apply_research` |
| `technology.gained` | Zdobycie technologii. | 4 | when×3, after×1 | technologies×2, leaders×1, breakthroughs×1 | `technology.grant_technology` |
| `technology.shared` | Technologia udostępniona innemu graczowi. | 0 | — | — | — |
| `cards.action_played` | Zagranie karty akcji. | 4 | when×4 | action_cards×4 | `action_cards.play_action_card` |
| `cards.action_drawn` | Dobranie kart akcji. | 1 | when×1 | abilities×1 | `card_draw.draw_action_card` |
| `cards.action_discarded` | Odrzucenie karty akcji. | 1 | after×1 | action_cards×1 | `card_draw._record_discards` |
| `component.gained` | Gracz zdobył komponent (relikt, notka, technologia). | 11 | when×10, after×1 | relics×4, promissory_notes×3, breakthroughs×3, technologies×1 | `relics / breakthrough / promissory_notes` |
| `fracture.ingress_placed` | The Fracture weszło do gry i wszystkie żetony ingress leżą (R_fracture). | 0 | — | — | `fracture.announce_ingress_placed` |
| `objective.revealed` | Cel publiczny ujawniony. | 1 | when×1 | relics×1 | `objectives.reveal_next_public` |
| `objective.scored` | Cel zdobyty. | 2 | when×2 | abilities×1, breakthroughs×1 | `objectives.score_public` |
| `objective.secret_discarded` | Tajny cel odrzucony. | 0 | — | — | — |
| `agenda.revealed` | Agenda ujawniona. | 28 | after×18, when×10 | action_cards×19, promissory_notes×6, abilities×2, leaders×1 | `agenda_phase.reveal_agenda` |
| `agenda.votes_cast` | Głosy oddane. | 6 | after×3, when×3 | action_cards×2, leaders×2, galactic_events×1, abilities×1 | `agenda_phase.cast_vote` |
| `agenda.outcome_resolved` | Wynik agendy rozstrzygany. | 65 | after×64, during×1 | agendas×63, action_cards×1, abilities×1 | `agenda_phase._resolve` |
| `agenda.elected` | Gracz wybrany jako wynik agendy. | 2 | when×2 | action_cards×2 | — |
| `agenda.law_discarded` | Prawo zdjęte z gry. | 0 | — | — | `agenda_phase.remove_law` |
| `any_time` | Dowolna chwila („at any time”). | 8 | any×8 | leaders×8 | — |

Zdarzeń zdefiniowanych: **70**, emitowanych przez silnik: **54**. Potrzebne komponentom, a jeszcze nie emitowane: **12**.

Nieemitowane, ale potrzebne: `agenda.elected`, `any_time`, `combat.hits_produced`, `combat.step`, `economy.resources_spent`, `game.faction_in_play`, `planet.exhausted`, `state.condition`, `status.step`, `strategy.cards_returned`, `unit.coexist`, `unit.galvanized`

## 2a. Osiągalność: czy komponent wyskakuje graczowi

Kanały: `auto` (działa sam + wpis w feedzie), `offer` (panel decyzji), `hand` (karta/notka z ręki zagrywalna w oknie, sygnał także przy zwiniętej ręce), `now` (karta „Available now”), `button` (zdolność technologii poza akcją), `mod` (modyfikator wewnątrz reguły), `rule` (dane / jawny wybór w akcji / wersja zastąpiona erratą). Strażnik: `tests/test_timing_reach.py`, kod: `src/audit/timing_reach.py`.

* Hooki na nieemitowanych (zdarzenie, moment): **0**
* Karty/notki z ręki z efektem, których okna nie otwiera żaden dostawca: **0**
* Efekty z oknem bez żadnego kanału: **0**

Komponenty z oknem (reakcja / przy zdobyciu) wg okna: ✅ = ma kanał do gracza, ⛔ = brak efektu w silniku (w grze nic się nie stanie — to one „uciekają”).

| Okno | ✅ | ⛔ | Brakujące (⛔) |
|---|---:|---:|---|
| `tactical.system_activated` · after | 26 | 4 | Aetherpassage, Aetherstream, So Ata, Survival Instinct |
| `agenda.revealed` · after | 16 | 1 | Odlynn Myrr |
| `combat.round` · start | 14 | 2 | Kuuasi Aun Jalatai, Proxima Targeting VI |
| `combat` · start | 13 | 0 |  |
| `turn` · start | 8 | 4 | Crimson Legionnaire II, Law's Order, Neural Parasite (Obsidian), Thunder's Paradox |
| `production.units_produced` · when | 6 | 5 | "A Tall Stranger", Agency Supply Network, Homesick Phantom, Navarch Feng, The Icon |
| `tactical.ships_moved` · after | 7 | 4 | Acamar, Call of the Void, Voidwatch, Xuange |
| `agenda.revealed` · when | 10 | 0 |  |
| `component.gained` · when | 8 | 2 | I.I.H.Q. Modernization, Planesplitter (Firmament) |
| `production.used` · when | 9 | 0 |  |
| `any_time` · any | 3 | 5 | Aroz Hollow, Captain Aroz, Nip and Tuck, Ssruu, Xander Alexin Victori III |
| `combat.hits_assigned` · before | 8 | 0 |  |
| `unit.destroyed` · when | 1 | 6 | ???\_NULL\_REFERENCE\_???, Dame Briar, F.S.S. Orlando, Lyra Keen, Subatomic Splicer, Vos Hollow |
| `tactical.system_activated` · when | 4 | 2 | Incursion, Void Tether |
| `combat.won` · after | 5 | 0 |  |
| `combat` · end | 1 | 4 | "Total Mystery", Ahk Siever, Exile II, Phoenix Standard |
| `phase` · during [phase=action] | 2 | 3 | Data Skimmer, Deepgloom Executable, Nekro Malleon |
| `phase` · start [phase=status] | 1 | 4 | Hydrothermal Mining, Neural Parasite (Firmament), Radical Advancement, The Reaping |
| `turn` · end | 4 | 1 | Field Marshal Mercer |
| `unit.sustain_damage` · after | 5 | 0 |  |
| `cards.action_played` · when | 4 | 0 |  |
| `game.setup` · during | 0 | 4 | Dark Whispers, Hubris, The Company, The Tribunii |
| `phase` · start [phase=strategy] | 3 | 1 | Council Patronage |
| `planet.control_gained` · after | 4 | 0 |  |
| `planet.control_gained` · when | 3 | 1 | Liberate |
| `unit.ability_used` · when [ability=roll] | 4 | 0 |  |
| `agenda.votes_cast` · when | 3 | 0 |  |
| `combat.roll` · after | 3 | 0 |  |
| `combat.round` · after | 3 | 0 |  |
| `economy.resources_spent` · when | 2 | 1 | Aello |
| `invasion` · start | 3 | 0 |  |
| `phase` · during [phase=status] | 3 | 0 |  |
| `phase` · end [phase=strategy] | 3 | 0 |  |
| `tactical.action` · after | 3 | 0 |  |
| `tactical.action` · end | 2 | 1 | Miniaturization |
| `tactical.units_committed` · after | 3 | 0 |  |
| `technology.gained` · when [would] | 0 | 3 | Valefar Assimilator X, Valefar Assimilator Y, Valefar Assimilator Z |
| `technology.research` · when | 2 | 1 | Doctor Carrina |
| `technology.research` · when [unit_upgrade=true] | 3 | 0 |  |
| `agenda.elected` · when | 2 | 0 |  |
| `agenda.votes_cast` · after | 2 | 0 |  |
| `combat.roll` · before | 2 | 0 |  |
| `component.action` · after | 1 | 1 | Suffi An |
| `economy.commodities_replenished` · when | 1 | 1 | Age of Commerce |
| `game.setup` · when | 1 | 1 | The Sorrow |
| `objective.scored` · when | 1 | 1 | Plots Within Plots |
| `phase` · end [phase=status] | 2 | 0 |  |
| `phase` · start [phase=agenda] | 2 | 0 |  |
| `planet.explored` · after | 2 | 0 |  |
| `status.step` · when [step=gain_command_tokens] | 2 | 0 |  |
| `strategy.action` · when [would] | 2 | 0 |  |
| `strategy.token_spent` · when [would] | 1 | 1 | Jae Mir Kan |
| `tactical.action` · during | 1 | 1 | Il Na Viroset |
| `transaction` · when | 2 | 0 |  |
| `turn` · during | 1 | 1 | Transparasteel Plating |
| `unit.ability_used` · after [ability=roll] | 2 | 0 |  |
| `unit.destroyed` · after | 2 | 0 |  |
| `unit.sustain_damage` · when | 2 | 0 |  |
| `agenda.outcome_resolved` · after | 0 | 1 | Future Sight |
| `agenda.outcome_resolved` · during [would] | 1 | 0 |  |
| `agenda.revealed` · after [1/agenda phase] | 0 | 1 | Galactic Threat |
| `agenda.votes_cast` · after [scope=all] | 0 | 1 | Hidden Agenda |
| `cards.action_discarded` · after | 1 | 0 |  |
| `cards.action_drawn` · when | 0 | 1 | Scheming |
| `combat.hits_assigned` · after | 1 | 0 |  |
| `combat.hits_assigned` · before [would] | 1 | 0 |  |
| `combat.hits_produced` · when | 1 | 0 |  |
| `combat.retreat` · after | 1 | 0 |  |
| `combat.retreat` · when | 0 | 1 | Watchful Ojz |
| `combat.round` · during | 1 | 0 |  |
| `combat.round` · end | 1 | 0 |  |
| `combat.step` · after [step=roll_dice] | 0 | 1 | The Thundarian |
| `combat.step` · during [step=anti_fighter_barrage] | 1 | 0 |  |
| `combat.step` · start [step=announce_retreats] | 1 | 0 |  |
| `combat.won` · when | 0 | 1 | Edict |
| `combat` · during | 1 | 0 |  |
| `component.exhausted` · after | 0 | 1 | Temporal Command Suite |
| `component.gained` · after | 1 | 0 |  |
| `economy.commodities_replenished` · after | 1 | 0 |  |
| `economy.trade_goods_gained` · after | 1 | 0 |  |
| `economy.trade_goods_gained` · when | 0 | 1 | Artuno the Betrayer |
| `faction.ability_used` · after | 1 | 0 |  |
| `game.faction_in_play` · when | 0 | 1 | The Blade's Orchestra |
| `game.setup` · before | 0 | 1 | Minor Factions |
| `invasion` · during | 1 | 0 |  |
| `objective.revealed` · when | 1 | 0 |  |
| `phase` · during [phase=agenda] | 1 | 0 |  |
| `phase` · when [phase=status] | 0 | 1 | The Sowing |
| `planet.exhausted` · when | 0 | 1 | Xxekir Grom |
| `planet.explored` · when | 1 | 0 |  |
| `player.last_passed` · after | 0 | 1 | Director Nel |
| `production.units_produced` · after | 1 | 0 |  |
| `production.used` · after | 1 | 0 |  |
| `state.condition` · when | 1 | 0 |  |
| `strategy.action` · after | 1 | 0 |  |
| `strategy.action` · start | 0 | 1 | Planesplitter (Obsidian) |
| `strategy.action` · when | 1 | 0 |  |
| `strategy.card_chosen` · when | 1 | 0 |  |
| `strategy.cards_returned` · when [would] | 1 | 0 |  |
| `strategy.token_spent` · after | 1 | 0 |  |
| `strategy.token_spent` · when | 1 | 0 |  |
| `tactical.ships_moved` · before | 1 | 0 |  |
| `tactical.ships_moved` · end | 1 | 0 |  |
| `tactical.ships_moved` · when | 0 | 1 | Myru Vos |
| `tactical.units_committed` · during | 1 | 0 |  |
| `tactical.units_committed` · when | 0 | 1 | Research Team |
| `technology.gained` · after | 0 | 1 | Nekro Acidos |
| `technology.research` · after | 1 | 0 |  |
| `technology.research` · when [would] | 0 | 1 | Propagation |
| `tokens.placed` · after | 1 | 0 |  |
| `transaction` · after | 1 | 0 |  |
| `unit.ability_used` · after [ability=afb] | 1 | 0 |  |
| `unit.ability_used` · when [ability=afb] | 1 | 0 |  |
| `unit.coexist` · when | 0 | 1 | Oceanbound |
| `unit.destroyed` · after [1/combat] | 0 | 1 | Technological Singularity |
| `unit.galvanized` · when | 0 | 1 | Galvanize |

## 3. Rodzaje komponentów wg kategorii

| Kategoria | akcja komponentu | reakcja w oknie | przy zdobyciu | efekt trwały | efekt ciągły | wynik agendy | razem |
|---|---:|---:|---:|---:|---:|---:|---:|
| abilities | 5 | 51 | 0 | 0 | 17 | 0 | 73 |
| action_cards | 42 | 101 | 0 | 0 | 0 | 0 | 143 |
| agendas | 0 | 0 | 0 | 0 | 0 | 63 | 63 |
| breakthroughs | 5 | 20 | 3 | 0 | 3 | 0 | 31 |
| explores | 23 | 2 | 0 | 0 | 55 | 0 | 80 |
| galactic_events | 0 | 4 | 0 | 0 | 16 | 0 | 20 |
| leaders | 30 | 73 | 0 | 0 | 0 | 0 | 103 |
| promissory_notes | 9 | 28 | 3 | 0 | 0 | 0 | 40 |
| relics | 7 | 10 | 4 | 0 | 3 | 0 | 24 |
| technologies | 10 | 57 | 1 | 0 | 34 | 0 | 102 |

## 4. Efekty trwałe i czasy trwania (77)

Zakres wygasania wykryty w tekście. `deferred` = „at the start of the next ... phase” (odroczony wyzwalacz; hook na `phase`/`start` sprawdza efekt w magazynie).

| Komponent | Nazwa | Zakresy | deferred | Tekst |
|---|---|---|---|---|
| `agendas:abolishment` | Judicial Abolishment | agenda | — | Elect Law (When this agenda is revealed, if there are no laws in play, discard this card and reveal another a… |
| `agendas:arms_reduction` | Arms Reduction | — | strategy | For/Against. For: Each player destroys all but 2 of their dreadnoughts and all but 4 of their cruisers. Again… |
| `agendas:checks` | Checks and Balances | agenda | — | For/Against. For: When a player chooses a strategy card during the strategy phase, they give that strategy ca… |
| `agendas:classified` | Classified Document Leaks | agenda | — | Elect Scored Secret Objective (When this agenda is revealed, if there are no scored secret objectives, discar… |
| `agendas:constitution` | New Constitution | agenda | strategy | For/Against. (When this agenda is revealed, if there are no laws in play, discard this card and reveal anothe… |
| `agendas:covert` | Covert Legislation | agenda | — | When this agenda is revealed, the speaker draws the next card in the agenda deck but does not reveal it to th… |
| `agendas:execution` | Public Execution | agenda | — | Elect Player. The elected player discards all of their action cards. If they have the speaker token, they giv… |
| `agendas:miscount` | Miscount Disclosed | agenda | — | Elect Law. (When this agenda is revealed, if there are no laws in play, discard this card and reveal another … |
| `agendas:rep_govt` | Representative Government | — | strategy | For/Against. For: Players cannot exhaust planets to cast votes during the agenda phase; each player may cast … |
| `agendas:representative_government` | Representative Government (Base Game) | — | strategy | For/Against. For: Players cannot exhaust planets to cast votes during the agenda phase; each player may cast … |
| `agendas:revolution` | Anti-Intellectual Revolution | — | strategy | For/Against. For: After a player researches a technology, that player must destroy 1 of their non-fighter shi… |
| `action_cards:assassin` | Assassinate Representative | agenda | — | Choose 1 player. That player cannot vote on this agenda. |
| `action_cards:blitz` | Blitz | invasion | — | Each of your non-fighter ships in the active system that do not have BOMBARDMENT gain BOMBARDMENT 6 until the… |
| `action_cards:bunker` | Bunker | invasion | — | During this invasion, apply -4 to the result of each BOMBARDMENT roll against planets you control. |
| `action_cards:const_rider` | Construction Rider | agenda | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, place… |
| `action_cards:diplo_rider` | Diplomacy Rider | agenda | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, choos… |
| `action_cards:disable` | Disable | invasion | — | Your opponents' PDS units lose PLANETARY SHIELD and SPACE CANNON during this invasion. |
| `action_cards:f_prototype` | Fighter Prototype | combat | — | Apply +2 to the result of each of your fighters' combat rolls during this combat round. |
| `action_cards:fs1` | Flank Speed | tactical_action | — | Apply +1 to the move value of each of your ships during this tactical action. |
| `action_cards:fs2` | Flank Speed | tactical_action | — | Apply +1 to the move value of each of your ships during this tactical action. |
| `action_cards:fs3` | Flank Speed | tactical_action | — | Apply +1 to the move value of each of your ships during this tactical action. |
| `action_cards:fs4` | Flank Speed | tactical_action | — | Apply +1 to the move value of each of your ships during this tactical action. |
| `action_cards:hack` | Hack Election | agenda | — | During this agenda, you vote last. |
| `action_cards:imp_rider` | Imperial Rider | agenda | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, gain … |
| `action_cards:intercept` | Intercept | round | — | Your opponent cannot retreat during this round of space combat. |
| `action_cards:lead_rider` | Leadership Rider | agenda | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, gain … |
| `action_cards:lost_star` | Lost Star Chart | tactical_action | — | During this tactical action, systems that contain alpha and beta wormholes are adjacent to each other. |
| `action_cards:mb1` | Morale Boost | combat | — | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `action_cards:mb2` | Morale Boost | combat | — | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `action_cards:mb3` | Morale Boost | combat | — | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `action_cards:mb4` | Morale Boost | combat | — | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `action_cards:nav_suite` | Nav Suite | tactical_action | — | During the "Movement" step of this tactical action, ignore the effect of anomalies. |
| `action_cards:politic_rider` | Politics Rider | agenda | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, draw … |
| `action_cards:reveal_prototype` | Reveal Prototype | combat | — | Spend 4 resources to research a unit upgrade technology of the same type as 1 of your units that is participa… |
| `action_cards:sanction` | Sanction | agenda | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, each … |
| `action_cards:silence_space` | In The Silence Of Space | tactical_action | — | Choose 1 system. During this tactical action, your ships in the chosen system can move through systems that c… |
| `action_cards:solar_flare` | Solar Flare | tactical_action | — | During the "Movement" step of this tactical action, other players cannot use SPACE CANNON against your ships. |
| `action_cards:tech_rider` | Technology Rider | agenda | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, resea… |
| `action_cards:trade_rider` | Trade Rider | agenda | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, gain … |
| `action_cards:veto` | Veto | agenda | — | Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead. |
| `action_cards:veto3` | Veto | agenda | — | Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead. |
| `action_cards:veto4` | Veto | agenda | — | Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead. |
| `action_cards:war_rider` | Warfare Rider | agenda | — | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, place… |
| `relics:dynamiscore` | Dynamis Core | while_in_play | — | While this card is in your play area, your commodity value is increased by 2. ACTION: Gain trade goods equal … |
| `relics:nanoforge` | Nano-Forge | tactical_action | — | ACTION: Attach this card to a non-legendary, non-home planet you control; its resource and influence values a… |
| `promissory_notes:<color>_an` | Alliance | while_in_play | — | When you receive this card, if you are not the <color> player, you must place it faceup in your play area. Wh… |
| `promissory_notes:<color>_ps` | Political Secret | agenda | — | When an agenda is revealed: The <color> player cannot vote, play action cards, or use faction abilities until… |
| `promissory_notes:antivirus` | Antivirus | while_in_play | — | At the start of a combat: Place this card faceup in your play area. While this card is in your play area, the… |
| `promissory_notes:cavalry` | The Cavalry | combat | — | At the start of a space combat against a player other than the Nomad: During this combat, treat 1 of your non… |
| `promissory_notes:convoys` | Trade Convoys | while_in_play | — | ACTION: Place this card faceup in your play area. While this card is in your play area, you may negotiate tra… |
| `promissory_notes:favor` | Political Favor | agenda | — | When an agenda is revealed: Remove 1 token from the Xxcha player's strategy pool and return it to their reinf… |
| `promissory_notes:pop` | Promise of Protection | while_in_play | — | ACTION: Place this card faceup in your play area. While this card is in your play area, the Mentak player can… |
| `promissory_notes:rider` | Keleres Rider | agenda | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:ridera` | Keleres Rider | agenda | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:riderm` | Keleres Rider | agenda | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:riderx` | Keleres Rider | agenda | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:tekklar` | Tekklar Legion | combat | — | At the start of an invasion combat: Apply +1 to the result of each of your unit's combat rolls during this co… |
| `abilities:quash` | Quash | agenda | — | You may spend 1 token from your strategy pool to discard that agenda and reveal 1 agenda from the top of the … |
| `leaders:ghostagent` | Emissary Taivra | tactical_action | — | [agent] You may exhaust this card; if you do, that system is adjacent to all other systems that contain a wor… |
| `leaders:keleresheroodlynn` | Odlynn Myrr | agenda | — | [hero] You may cast up to 6 additional votes on this agenda. Predict aloud an outcome of this agenda. For eac… |
| `leaders:letnevagent` | Viscount Unlenn | combat | — | [agent] You may exhaust this card to choose 1 ship in the active system; that ship rolls 1 additional die dur… |
| `leaders:mentakhero` | Ipswitch, Loose Cannon | combat | — | [hero] You may purge this card; if you do, for each other player's ship that is destroyed during this combat,… |
| `leaders:naazhero` | Hesh and Prit | tactical_action | — | [hero] Gain 1 relic and perform the secondary ability of up to 2 readied or unchosen strategy cards; during t… |
| `leaders:nomadagentthundarian` | The Thundarian | combat | — | [agent] You may exhaust this card. If you do, hits are not assigned to either player's units. Return to the s… |
| `leaders:solagent` | Evelyn DeLouis | combat | — | [agent] You may exhaust this card to choose 1 ground force in the active system; that ground force rolls 1 ad… |
| `technologies:as` | Aetherstream | tactical_action | — | After you or one of your neighbors activates a system that is adjacent to an anomaly, you may apply +1 to the… |
| `technologies:cl2` | Crimson Legionnaire II | — | next | Cost 1(x2), Combat 7 After this unit is destroyed, gain 1 commodity or convert 1 of your commodities to a tra… |
| `technologies:da` | Duranium Armor | combat | — | During each combat round, after you assign hits to your units, repair 1 of your damaged units that did not us… |
| `technologies:executiveorder` | Executive Order | agenda | — | ACTION: Exhaust this card and draw the top or bottom card of the agenda deck. Players immediately vote on thi… |
| `technologies:gd` | Gravity Drive | tactical_action | — | After you activate a system, apply +1 to the move value of 1 of your ships during this tactical action. |
| `technologies:inf2` | Infantry II | — | next | Cost 1(x2), Combat 7 After this unit is destroyed, roll 1 die. If the result is 6 or greater, place the unit … |
| `technologies:lw2` | Letani Warrior II | — | next | Cost 1(x2), Combat 7 PRODUCTION 2 After this unit is destroyed, roll 1 die. If the result is 6 or greater, pl… |
| `technologies:md_base` | Magen Defense Grid | combat | — | You may exhaust this card at the start of a round of ground combat on a planet that contains 1 or more of you… |
| `technologies:sc` | Supercharge | combat | — | At the start of a combat round, you may exhaust this card to apply +1 to the result of each of your unit's co… |
| `technologies:so2` | Spec Ops II | — | next | Cost 1(x2), Combat 6 After this unit is destroyed, roll 1 die. If the result is 5 or greater, place the unit … |
| `breakthroughs:argentbt` | Wing Transfer | tactical_action | — | When you activate a system that contains only your units, you may place command tokens from your reinforcemen… |
| `breakthroughs:winnubt` | Imperator | tactical_action | — | Apply +1 to the results of each of your unit's combat rolls for each "Support for the Throne" in your opponen… |

## 5. Agendy (63: base×50, pok×13)

Każda agenda: efekt wyniku rozstrzyga się `agenda.outcome_resolved`/`after`; prawo zostaje w grze (`while_in_play`), a jego klauzule czasowe stają się hookami prawa (`SOURCE_AGENDA`). Kolumna „Klauzule” to okna WEWNĄTRZ tekstu agendy.

| Id | Nazwa | Źródło | Typ | Klauzule czasowe w tekście | Trwanie | Tekst |
|---|---|---|---|---|---|---|
| `abolishment` | Judicial Abolishment | base | law | — | agenda | Elect Law (When this agenda is revealed, if there are no laws in play, discard this card and reveal another a… |
| `arbiter` | Imperial Arbiter | base | — | `phase` · end [phase=strategy]; `phase` · end [phase=strategy] | — | Elect Player. The elected player gains this card. At the end of the strategy phase, the owner of this card ma… |
| `arms_reduction` | Arms Reduction | base | — | `phase` · start [phase=strategy] | — | For/Against. For: Each player destroys all but 2 of their dreadnoughts and all but 4 of their cruisers. Again… |
| `articles_war` | Articles of War | pok | — | — | — | For/Against. For: All mechs lose their printed abilities except for SUSTAIN DAMAGE. Against: Each player that… |
| `artifact` | Ixthian Artifact | base | — | — | — | For/Against. For: The speaker rolls 1 die. If the result is 6-10, each player may research 2 technologies. If… |
| `censure` | Political Censure | pok | — | — | — | Elect Player. The elected player gains this card and 1 victory point. The elected player cannot play action c… |
| `checks` | Checks and Balances | pok | — | `strategy.card_chosen` · when; `strategy.card_chosen` · when | agenda | For/Against. For: When a player chooses a strategy card during the strategy phase, they give that strategy ca… |
| `cladenstine` | Clandestine Operations | pok | — | — | — | For/Against. For: Each player removes 2 command tokens from their command sheet and returns those tokens to t… |
| `classified` | Classified Document Leaks | base | — | — | agenda | Elect Scored Secret Objective (When this agenda is revealed, if there are no scored secret objectives, discar… |
| `committee` | Committee Formation | base | — | `agenda.votes_cast` · before; `agenda.votes_cast` · before | — | Elect Player. The elected player gains this card. Before players vote on an agenda that requires a player to … |
| `conscription` | Regulated Conscription | base | — | `production.units_produced` · when; `production.units_produced` · when | — | For/Against. For: When a player produces units, they produce only 1 fighter and infantry for its cost instead… |
| `constitution` | New Constitution | base | — | `phase` · start [phase=strategy] | agenda | For/Against. (When this agenda is revealed, if there are no laws in play, discard this card and reveal anothe… |
| `conventions` | Conventions of War | base | — | — | — | For/Against. For: Players cannot use BOMBARDMENT against units that are on cultural planets. Against: Each pl… |
| `core_mining` | Core Mining | base | — | — | — | Elect Planet. Attach this card to the elected planet's card. Then, destroy 1 infantry on the planet. The reso… |
| `covert` | Covert Legislation | pok | — | `agenda.revealed` · when | agenda | When this agenda is revealed, the speaker draws the next card in the agenda deck but does not reveal it to th… |
| `crisis` | Galactic Crisis Pact | pok | — | — | — | Elect Strategy Card. Each player may perform the secondary ability of the elected strategy card without spend… |
| `crown_of_emphidia` | The Crown of Emphidia | base | — | — | — | Elect Player. The elected player gains this card and 1 victory point. A player gains this card and 1 victory … |
| `crown_of_thalnos` | The Crown of Thalnos | base | — | `combat.round` · during | — | Elect Player. The elected player gains this card. During each combat round, the owner of this card may reroll… |
| `defense_act` | Homeland Defense Act | base | — | — | — | For/Against. For: Each player can have any number of PDS units on planets they control. Against: Each player … |
| `demilitarized_zone` | Demilitarized Zone | base | — | — | — | Elect Planet. Attach this card to the elected planet's card. Then, destroy all units on that planet. Player's… |
| `disarmament` | Compensated Disarmament | base | — | — | — | Elect Planet. Destroy each ground force on the elected planet; for each unit that was destroyed, the player w… |
| `economic_equality` | Economic Equality | base | — | — | — | For/Against. For: Each player returns all of their trade goods to the supply. Then, each player gains 5 trade… |
| `execution` | Public Execution | base | — | — | agenda | Elect Player. The elected player discards all of their action cards. If they have the speaker token, they giv… |
| `grant_reallocation` | Research Grant Reallocation | pok | — | — | — | Elect Player. The elected player gains any 1 technology of their choice. Then, for each prerequisite on that … |
| `holy_planet_of_ixth` | Holy Planet of Ixth | base | — | `planet.control_gained` · when; `planet.control_lost` · when | — | Elect Planet. Attach this card to the elected planet's card. The planet's owner gains 1 victory point. Units … |
| `incentive` | Incentive Program | base | — | — | — | For/Against. For: Draw and reveal 1 stage I public objective from the deck and place it near the public objec… |
| `minister_antiquities` | Minister of Antiquities | pok | — | — | — | Elect Player. The elected player gains 1 relic. |
| `minister_commerce` | Minister of Commerce | base | — | `economy.commodities_replenished` · after; `economy.commodities_replenished` · after | — | Elect Player. The elected player gains this card. After the owner of this card replenishes commodities, they … |
| `minister_exploration` | Minister of Exploration | base | — | `planet.control_gained` · when; `planet.control_gained` · when | — | Elect Player. The elected player gains this card. When the owner of this card gains control of a planet, they… |
| `minister_industry` | Minister of Industry | base | — | `unit.placed` · when; `unit.placed` · when | — | Elect Player. The elected player gains this card. When the owner of this card places a space dock in a system… |
| `minister_peace` | Minister of Peace | base | — | `tactical.system_activated` · after; `tactical.system_activated` · after | — | Elect Player. The elected player gains this card. After a player activates a system that contains 1 or more o… |
| `minister_policy` | Minister of Policy | base | — | `phase` · end [phase=status]; `phase` · end [phase=status] | — | Elect Player. The elected player gains this card. At the end of the status phase, the owner of this card draw… |
| `minister_sciences` | Minister of Sciences | base | — | `strategy.action` · when; `strategy.action` · when | — | Elect Player. The elected player gains this card. When the owner of this card resolves the primary or seconda… |
| `minister_war` | Minister of War | base | — | — | — | Elect Player. The elected player gains this card. The owner of this card may discard this card after performi… |
| `miscount` | Miscount Disclosed | base | law | — | agenda | Elect Law. (When this agenda is revealed, if there are no laws in play, discard this card and reveal another … |
| `mutiny` | Mutiny | base | — | — | — | For/Against. For: Each player that voted "For" gains 1 victory point. Against: Each player that voted "For" l… |
| `nexus` | Nexus Sovereignty | pok | — | — | — | For/Against. For: Alpha and beta wormholes in the wormhole nexus have no effect during movement. Against: Pla… |
| `plowshares` | Swords to Plowshares | base | — | — | — | For/Against. For: Each player destroys half of their infantry on each planet they control, rounded up. Then, … |
| `prophecy` | Prophecy of Ixth | base | — | `production.used` · when; `production.used` · when | — | Elect Player. The elected player gains this card. The owner of this card applies +1 to the result of their fi… |
| `rearmament` | Rearmament Agreement | pok | — | — | — | For/Against. For: Each player places 1 mech from their reinforcements on a planet they control in their home … |
| `redistribution` | Colonial Redistribution | base | — | — | — | Elect Non-Home Planet Other Than Mecatol Rex. Destroy each unit on the elected planet. Then, the player who c… |
| `regulations` | Fleet Regulations | base | — | — | — | For/Against. For: Each player cannot have more than 4 tokens in their fleet pool. Against: Each player places… |
| `rep_govt` | Representative Government | pok | — | `phase` · start [phase=strategy] | — | For/Against. For: Players cannot exhaust planets to cast votes during the agenda phase; each player may cast … |
| `representative_government` | Representative Government (Base Game) | base | — | `phase` · start [phase=strategy] | — | For/Against. For: Players cannot exhaust planets to cast votes during the agenda phase; each player may cast … |
| `revolution` | Anti-Intellectual Revolution | base | — | `technology.research` · after; `phase` · start [phase=strategy]; `technology.research` · after | — | For/Against. For: After a player researches a technology, that player must destroy 1 of their non-fighter shi… |
| `rt_biotic` | Research Team: Biotic | base | — | `technology.research` · when | — | Elect Planet. Attach this card to the elected planet's card. When the owner of this planet researches technol… |
| `rt_cybernetic` | Research Team: Cybernetic | base | — | `technology.research` · when | — | Elect Planet. Attach this card to the elected planet's card. When the owner of this planet researches technol… |
| `rt_propulsion` | Research Team: Propulsion | base | — | `technology.research` · when | — | Elect Planet. Attach this card to the elected planet's card. When the owner of this planet researches technol… |
| `rt_warfare` | Research Team: Warfare | base | — | `technology.research` · when | — | Elect Planet. Attach this card to the elected planet's card. When the owner of this planet researches technol… |
| `sanctions` | Executive Sanctions | base | — | — | — | For/Against. For: Each player can have a maximum of 3 action cards in their hand. Against: Each player discar… |
| `schematics` | Publicize Weapon Schematics | base | — | — | — | For/Against. For: If any player owns a war sun technology, all players may ignore all prerequisites on war su… |
| `secret` | Archived Secret | base | — | — | — | Elect Player. The elected player draws 1 secret objective. |
| `seed_empire` | Seed of an Empire | base | — | — | — | For/Against. For: The player with the most victory points gains 1 victory point. Against: The player with the… |
| `senate_sanctuary` | Senate Sanctuary | base | — | — | — | Elect Planet. Attach this card to the elected planet's card. The influence value of this planet is increased … |
| `shard_of_the_throne` | Shard of the Throne | base | — | — | — | Elect Player. The elected player gains this card and 1 victory point. A player gains this card and 1 victory … |
| `shared_research` | Shared Research | base | — | — | — | For/Against. For: Each player's units can move through nebulae. Against: Each player places a command token f… |
| `standardization` | Armed Forces Standardization | pok | — | — | — | Elect Player. The elected player places command tokens from their reinforcements so that they have 3 tokens i… |
| `terraforming_initiative` | Terraforming Initiative | base | — | — | — | Elect Planet. Attach this card to the elected planet's card. The resource and influence values of this planet… |
| `travel_ban` | Enforced Travel Ban | base | — | — | — | For/Against. For: Alpha and beta wormholes have no effect during movement. Against: Destroy each PDS in or ad… |
| `unconventional` | Unconventional Measures | base | — | — | — | For/Against. For: Each player that voted "For" draws 2 action cards. Against: Each player that voted "For" di… |
| `warrant` | Search Warrant | pok | — | — | — | Elect Player. The elected player gains this card and draws 2 secret objectives. The owner of this card plays … |
| `wormhole_recon` | Wormhole Reconstruction | base | — | — | — | For/Against. For: All systems that contain either an alpha or beta wormhole are adjacent to each other. Again… |
| `wormhole_research` | Wormhole Research | base | — | — | — | For/Against. For: Each player who has 1 or more ships in a system that contains a wormhole may research 1 tec… |

## 6. Frakcje: zdolności, liderzy, technologie, przełomy, notki

Dla każdej frakcji komponenty z oknem (reakcja/akcja/przy zdobyciu) i efekty ciągłe.

### The Arborec (`arborec`) — 8 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:stymie` | Stymie | reakcja w oknie | `tactical.ships_moved` · after | tak | After another player moves ships into a system that contains 1 or more of your units: You may place 1 command… |
| `abilities:mitosis` | Mitosis | reakcja w oknie | `phase` · start [phase=status] | — | Your space docks cannot produce infantry. Place 1 infantry from your reinforcements on any planet you control. |
| `leaders:arborecagent` | Letani Ospha | akcja komponentu | `component.action` · action | tak | [agent] Exhaust this card and choose a player's non-fighter ship; that player may replace that ship with one … |
| `leaders:arboreccommander` | Dirzuga Rophal | reakcja w oknie | `tactical.system_activated` · after | tak | [commander] You may produce 1 unit in that system. |
| `leaders:arborechero` | Letani Miasmiala | akcja komponentu | `component.action` · action | — | [hero] Produce any number of units in any number of systems that contain 1 or more of your ground forces. The… |
| `technologies:bio` | Bioplasmosis | reakcja w oknie | `phase` · end [phase=status] | tak | At the end of the status phase, you may remove any number of infantry from planets you control and place them… |
| `technologies:lw2` | Letani Warrior II | reakcja w oknie | `turn` · start | — | Cost 1(x2), Combat 7 PRODUCTION 2 After this unit is destroyed, roll 1 die. If the result is 6 or greater, pl… |
| `breakthroughs:arborecbt` | Psychospore | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card to remove a command token from a system that contains 1 or more of your infantry an… |

### The Argent Flight (`argent`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:ambuscade` | Strike Wing Ambuscade | reakcja w oknie | `unit.ability_used` · when [ability=roll] | — | When 1 or more of your units make a roll for a unit ability: Choose 1 of those units to roll 1 additional die… |
| `abilities:raid_formation` | Raid Formation | reakcja w oknie | `unit.ability_used` · when [ability=afb] | — | for each hit produced in excess of your opponent's fighters, choose 1 of your opponent's ships that has SUSTA… |
| `abilities:zeal` | Zeal | reakcja w oknie | `agenda.votes_cast` · when | — | You always vote first during the agenda phase. cast 1 additional vote for each player in the game, including … |
| `leaders:argentagent` | Trilossa Aun Mirik | reakcja w oknie | `production.units_produced` · when | tak | [agent] You may exhaust this card; that player may place those units on any planets they control in that syst… |
| `leaders:argentcommander` | Trrakan Aun Zulok | reakcja w oknie | `unit.ability_used` · when [ability=roll] | tak | [commander] You may choose 1 of those units to roll 1 additional die. |
| `leaders:argenthero` | Mirik Aun Sissiri | akcja komponentu | `component.action` · action | — | [hero] Move any number of your ships from any systems to any number of other systems that contain 1 of your c… |
| `technologies:ah` | Aerie Hololattice | efekt ciągły | — | — | Other players cannot move ships through systems that contain your structures. Each planet that contains 1 or … |
| `technologies:swa2` | Strike Wing Alpha II | efekt ciągły | — | — | Cost 1, Combat 7, Move 2, Capacity 1 ANTI-FIGHTER BARRAGE 6(x3) When this unit uses ANTI-FIGHTER BARRAGE, eac… |
| `breakthroughs:argentbt` | Wing Transfer | reakcja w oknie | `tactical.system_activated` · when | tak | When you activate a system that contains only your units, you may place command tokens from your reinforcemen… |

### Last Bastion (`bastion`) — 11 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:raisethestandard` | Raise the Standard | reakcja w oknie | `combat` · end | — | At the end of a combat: Galvanize 1 of your units that participated. Then, return this card to the Last Basti… |
| `abilities:galvanize` | Galvanize | reakcja w oknie | `unit.galvanized` · when | — | Galvanized units roll 1 additional die for combat rolls and unit abilities. They place a galvanize token bene… |
| `abilities:liberate` | Liberate | reakcja w oknie | `planet.control_gained` · when | — | Ready that planet if it contains a number of your infantry equal to or greater than that planet's resource va… |
| `abilities:phoenixstandard` | Phoenix Standard | reakcja w oknie | `combat` · end | tak | You may galvanize 1 of your units that participated. |
| `leaders:bastionagent` | Dame Briar | reakcja w oknie | `unit.destroyed` · when | tak | [agent] You may exhaust this card to galvanize another of that player's units in the destroyed unit's system. |
| `leaders:bastioncommander` | Nip and Tuck | reakcja w oknie | `any_time` · any | — | [commander] Your action cards cannot be canceled by "Sabotage" action cards. The Nekro Virus cannot place ass… |
| `leaders:bastionhero` | Lyra Keen | reakcja w oknie | `unit.destroyed` · when | tak | [hero] You may purge this card to roll 1 die for each unit in its system that belongs to another player; if t… |
| `leaders:orlandohero` | F.S.S. Orlando | reakcja w oknie | `unit.destroyed` · when | tak | [hero] You may purge this card to designate that unit as a catalyst: roll 1 die for each other player's unit … |
| `technologies:helios2` | 4X41C "Helios" V2 | efekt ciągły | — | — | This unit's PRODUCTION value is equal to 4 more than the resource value of this planet. The resource value of… |
| `technologies:proxima` | Proxima Targeting VI | reakcja w oknie | `combat.round` · start | tak | Cancel 1 hit produced by BOMBARDMENT rolls made against your ground forces for each of your galvanized units … |
| `breakthroughs:bastionbt` | The Icon | reakcja w oknie | `production.units_produced` · when | tak | When you produce ships, you may exhaust this card to place those ships in a system that contains 1 of your co… |

### The Ghosts of Creuss (`creuss`) — 10 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:iff` | Creuss Iff | reakcja w oknie | `turn` · start | — | At the start of your turn during the action phase: Place or move a Creuss wormhole token into either a system… |
| `abilities:creuss_gate` | Creuss Gate | reakcja w oknie | `game.setup` · when | — | When you create the game board, place the Creuss Gate (tile 17) where your home system would normally be plac… |
| `abilities:quantum_entanglement` | Quantum Entanglement | efekt ciągły | — | — | You treat all systems that contain either an alpha or beta wormhole as adjacent to each other. Game effects c… |
| `abilities:slipstream` | Slipstream | reakcja w oknie | `tactical.action` · during | — | Apply +1 to the move value of each of your ships that starts its movement in your home system or in a system … |
| `leaders:ghostagent` | Emissary Taivra | reakcja w oknie | `tactical.system_activated` · after | tak | [agent] You may exhaust this card; if you do, that system is adjacent to all other systems that contain a wor… |
| `leaders:ghostcommander` | Sai Seravus | reakcja w oknie | `tactical.ships_moved` · after | tak | [commander] For each ship that has a capacity value and moved through 1 or more wormholes, you may place 1 fi… |
| `leaders:ghosthero` | Riftwalker Meian | akcja komponentu | `component.action` · action | — | [hero] Swap the positions of any 2 non-Fracture systems that contain wormholes or your units, other than the … |
| `technologies:ds` | Dimensional Splicer | reakcja w oknie | `combat` · start | tak | At the start of space combat in a system that contains a wormhole and 1 or more of your ships, you may produc… |
| `technologies:wg` | Wormhole Generator | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card to place or move a Creuss wormhole token into either a system that contains a plane… |
| `breakthroughs:ghostbt` | Particle Synthesis | efekt ciągły | — | — | Each wormhole in a system that contains your ships gains PRODUCTION 1 as if it were a unit you control. Reduc… |

### The Deepwrought Scholarate (`deepwrought`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:shareknowledge` | Share Knowledge | akcja komponentu | `component.action` · action | — | ACTION: Place this card faceup in your play area and gain 1 non-faction, non-unit upgrade technology that the… |
| `abilities:oceanbound` | Oceanbound | reakcja w oknie | `unit.coexist` · when | — | Any time you have more ocean cards than there are planets that contain your coexisting units, discard ocean c… |
| `abilities:researchteam` | Research Team | reakcja w oknie | `tactical.units_committed` · when | tak | If your units on that planet are not already coexisting, you may choose for your units to coexist. |
| `leaders:deepwroughtagent` | Doctor Carrina | reakcja w oknie | `technology.research` · when | tak | [agent] You may exhaust this card to allow that player to ignore 1 prerequisite; if they do, you may place 1 … |
| `leaders:deepwroughtcommander` | Aello | reakcja w oknie | `economy.resources_spent` · when | tak | [commander] That player may reduce the cost by 1; if they do, gain 1 commodity or convert 1 of your commoditi… |
| `leaders:deepwroughthero` | Ta Zern | akcja komponentu | `component.action` · action | — | [hero] Purge this card and a non-unit upgrade technology you own or from your deck; then, purge all cards wit… |
| `technologies:hydrothermal` | Hydrothermal Mining | reakcja w oknie | `phase` · start [phase=status] | — | At the start of the status phase, gain 1 trade good for each ocean card in play. |
| `technologies:radical` | Radical Advancement | reakcja w oknie | `phase` · start [phase=status] | tak | At the start of the status phase, you may replace one of your non-unit upgrade technologies with a technology… |
| `breakthroughs:deepwroughtbt` | Visionaria Select | akcja komponentu | `component.action` · action | tak | ACTION: Exhaust this card to allow each other player to spend 3 trade goods and give you 1 promissory note. E… |

### The Empyrean (`empyrean`) — 11 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:blood_pact` | Blood Pact | akcja komponentu | `component.action` · action | — | ACTION: Place this card faceup in your play area. When you and the Empyrean player cast votes for the same ou… |
| `promissory_notes:dark_pact` | Dark Pact | akcja komponentu | `component.action` · action | — | ACTION: Place this card faceup in your play area. When you give a number of commodities to the Empyrean playe… |
| `abilities:aetherpassage` | Aetherpassage | reakcja w oknie | `tactical.system_activated` · after | tak | You may allow that player to move their ships through systems that contain your ships. |
| `abilities:dark_whispers` | Dark Whispers | reakcja w oknie | `game.setup` · during | — | During setup, take the additional Empyrean faction promissory note; you have 2 faction promissory notes |
| `abilities:voidborn` | Voidborn | efekt ciągły | — | — | Nebulae do not affect your ships' movement |
| `leaders:empyreanagent` | Acamar | reakcja w oknie | `tactical.ships_moved` · after | tak | [agent] You may exhaust this card; that player gains 1 command token. |
| `leaders:empyreancommander` | Xuange | reakcja w oknie | `tactical.ships_moved` · after | tak | [commander] You may return that token to your reinforcements. |
| `leaders:empyreanhero` | Conservator Procyon | akcja komponentu | `component.action` · action | — | [hero] Place 1 frontier token in each system that does not contain any planets and does not already have a fr… |
| `technologies:as` | Aetherstream | reakcja w oknie | `tactical.system_activated` · after | tak | After you or one of your neighbors activates a system that is adjacent to an anomaly, you may apply +1 to the… |
| `technologies:vw` | Voidwatch | reakcja w oknie | `tactical.ships_moved` · after | — | After a player moves ships into a system that contains 1 or more of your units, they must give you 1 promisso… |
| `breakthroughs:empyreanbt` | Void Tether | reakcja w oknie | `tactical.system_activated` · when | tak | When you activate a system that contains or is adjacent to a unit or planet you control, you may place or mov… |

### The Firmament (`firmament`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:blackops` | Black Ops | przy zdobyciu | `component.gained` · when | tak | When you receive this card, if you are not the Firmament: The Firmament may place 1 facedown plot card in the… |
| `abilities:plotsplots` | Plots Within Plots | reakcja w oknie | `objective.scored` · when | — | You can score secret objectives already scored by other players if you fulfill their requirements; this does … |
| `abilities:puppetsoftheblade` | Puppets of the Blade | akcja komponentu | `component.action` · action | — | ACTION: Purge The Firmament's faction sheet, leaders, planet cards, and promissory note. Then, gain all of th… |
| `leaders:firmamentagent` | Myru Vos | reakcja w oknie | `tactical.ships_moved` · when | tak | [agent] You may exhaust this card; if you do, SPACE CANNON cannot be used against those ships. If they are no… |
| `leaders:firmamentcommander` | Captain Aroz | reakcja w oknie | `any_time` · any | tak | [commander] You may treat planets in systems that contain your ships as if you controlled them for the purpos… |
| `leaders:firmamenthero` | Sharsiss | akcja komponentu | `component.action` · action | tak | [hero] Place 1 of your plot cards in play with any other player's control token on it. Then, you may place an… |
| `technologies:parasite-firm` | Neural Parasite (Firmament) | reakcja w oknie | `phase` · start [phase=status] | tak | At the start of the status phase, you may place 1 infantry from your reinforcements on a planet you control i… |
| `technologies:planesplitter-firm` | Planesplitter (Firmament) | przy zdobyciu | `component.gained` · when | — | When you gain this card, put The Fracture into play. Flip this card if the Obsidian faction is in play. |
| `breakthroughs:firmamentbt` | The Sowing | reakcja w oknie | `phase` · when [phase=status] | tak | When you gain this card and at the start of the status phase, you may place up to 3 of your trade goods on th… |

### The Emirates of Hacan (`hacan`) — 10 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:convoys` | Trade Convoys | akcja komponentu | `component.action` · action | tak | ACTION: Place this card faceup in your play area. While this card is in your play area, you may negotiate tra… |
| `abilities:arbiters` | Arbiters | reakcja w oknie | `transaction` · when | — | When you are negotiating a transaction, action cards can be exchanged as part of that transaction. |
| `abilities:guild_ships` | Guild Ships | efekt ciągły | — | — | You can negotiate transactions with players who are not your neighbor. |
| `abilities:master_of_trade` | Masters of Trade | efekt ciągły | — | — | You do not have to spend a command token to resolve the secondary ability of the "Trade" strategy card. |
| `leaders:hacanagent` | Carth of Golden Sands | reakcja w oknie | `phase` · during [phase=action] | tak | [agent] You may exhaust this card to gain 2 commodities or replenish another player's commodities. |
| `leaders:hacancommander` | Gila the Silvertongue | reakcja w oknie | `agenda.votes_cast` · when | tak | [commander] You may spend any number of trade goods; cast 2 additional votes for each trade good spent. |
| `leaders:hacanhero` | Harrugh Gefhara | reakcja w oknie | `production.used` · when | tak | [hero] You may reduce the cost of each of your units to 0 during this use of PRODUCTION. If you do, purge thi… |
| `technologies:pm` | Production Biomes | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card and spend 1 token from your strategy pool to gain 4 trade goods and choose 1 other … |
| `technologies:qdn` | Quantum Datahub Node | reakcja w oknie | `phase` · end [phase=strategy] | tak | At the end of the strategy phase, you may spend 1 token from your strategy pool and give another player 3 of … |
| `breakthroughs:hacanbt` | Auto-Factories | reakcja w oknie | `production.units_produced` · when | — | When you produce 3 or more non-fighter ships, place 1 command token from your reinforcements into your fleet … |

### The Universities of Jol-Nar (`jol-nar`) — 10 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:ra` | Research Agreement | reakcja w oknie | `technology.research` · after | — | After the Jol-Nar player researches a technology that is not a faction technology: Gain that technology. Then… |
| `abilities:analytical` | Analytical | reakcja w oknie | `technology.research` · when [unit_upgrade=true] | tak | You may ignore 1 prerequisite. |
| `abilities:brilliant` | Brilliant | reakcja w oknie | `strategy.token_spent` · when | tak | You may resolve the primary ability instead. |
| `abilities:fragile` | Fragile | efekt ciągły | — | — | Apply -1 to the result of each of your unit's combat rolls. |
| `leaders:jolnaragent` | Doctor Sucaban | reakcja w oknie | `economy.resources_spent` · when | tak | [agent] You may exhaust this card to allow that player to remove any number of their infantry from the game b… |
| `leaders:jolnarcommander` | Agnlan Oln | reakcja w oknie | `unit.ability_used` · after [ability=roll] | tak | [commander] You may reroll any of those dice. |
| `leaders:jolnarhero` | Rin, the Master's Legacy | akcja komponentu | `component.action` · action | tak | [hero] For each non-unit upgrade technology you own, you may replace that technology with any technology of t… |
| `technologies:ers` | E-Res Siphons | reakcja w oknie | `tactical.system_activated` · after | — | After another player activates a system that contains 1 or more of your ships, gain 4 trade goods. |
| `technologies:scc` | Spatial Conduit Cylinder | efekt ciągły | — | tak | You may exhaust this card after you activate a system that contains 1 or more of your units; that system is a… |
| `breakthroughs:jolnarbt` | Specialized Compounds | reakcja w oknie | `technology.research` · when | tak | When you research technology using the "Technology" strategy card, you may exhaust a planet that has a techno… |

### The Council Keleres - Mentak (`keleres`) — 16 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:rider` | Keleres Rider | reakcja w oknie | `agenda.revealed` · after | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:ridera` | Keleres Rider | reakcja w oknie | `agenda.revealed` · after | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:riderm` | Keleres Rider | reakcja w oknie | `agenda.revealed` · after | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:riderx` | Keleres Rider | reakcja w oknie | `agenda.revealed` · after | — | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `abilities:council_patronage` | Council Patronage | reakcja w oknie | `phase` · start [phase=strategy] | — | Replenish your commodities, then gain 1 trade good. |
| `abilities:laws_order` | Law's Order | reakcja w oknie | `turn` · start | tak | You may spend 1 trade good or 1 commodity to treat all laws as blank until the end of that turn. |
| `abilities:the_tribuni` | The Tribunii | reakcja w oknie | `game.setup` · during | — | During setup, choose a Keleres hero that corresponds to an unused faction; take that faction's home system, c… |
| `leaders:keleresagent` | Xander Alexin Victori III | reakcja w oknie | `any_time` · any | tak | [agent] You may exhaust this card to allow any player to spend commodities as if they were trade goods. |
| `leaders:kelerescommander` | Suffi An | reakcja w oknie | `component.action` · after | tak | [commander] You may perform an additional action. |
| `leaders:keleresheroharka` | Harka Leeds | akcja komponentu | `component.action` · action | — | [hero] Reveal cards from the action card deck until you reveal 3 action cards that have component actions. Dr… |
| `leaders:keleresherokuuasi` | Kuuasi Aun Jalatai | reakcja w oknie | `combat.round` · start | — | [hero] Place your flagship and any combination of up to 2 cruisers or destroyers from your reinforcements int… |
| `leaders:keleresheroodlynn` | Odlynn Myrr | reakcja w oknie | `agenda.revealed` · after | tak | [hero] You may cast up to 6 additional votes on this agenda. Predict aloud an outcome of this agenda. For eac… |
| `technologies:asn` | Agency Supply Network | reakcja w oknie | `production.units_produced` · when | tak | When you resolve a unit's PRODUCTION ability, you may resolve another of your unit's PRODUCTION abilities in … |
| `technologies:executiveorder` | Executive Order | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card and draw the top or bottom card of the agenda deck. Players immediately vote on thi… |
| `technologies:iihq` | I.I.H.Q. Modernization | efekt ciągły | — | — | You are neighbors with all players that have units or control planets in or adjacent to the Mecatol Rex syste… |
| `breakthroughs:keleresbt` | I.I.H.Q. Modernization | przy zdobyciu | `component.gained` · when | — | When you gain this card, gain the Custodia Vigilia planet card and its legendary planet ability card. You are… |

### The L1Z1X Mindnet (`l1z1x`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:ce` | Cybernetic Enhancements | reakcja w oknie | `status.step` · when [step=gain_command_tokens] | — | When you gain command tokens during the status phase: Gain 1 additional command token. Then, return this card… |
| `abilities:assimilate` | Assimilate | reakcja w oknie | `planet.control_gained` · when | — | Replace each PDS and space dock that is on that planet with a matching unit from your reinforcements. |
| `abilities:harrow` | Harrow | reakcja w oknie | `combat.round` · end | tak | Your ships in the active system may use their BOMBARDMENT abilities against your opponent's ground forces on … |
| `leaders:l1z1xagent` | I48S | reakcja w oknie | `tactical.system_activated` · after | tak | [agent] You may exhaust this card to allow that player to replace 1 of their infantry in the active system wi… |
| `leaders:l1z1xcommander` | 2RAM | reakcja w oknie | `any_time` · any | — | [commander] Units that have PLANETARY SHIELD do not prevent you from using BOMBARDMENT. |
| `leaders:l1z1xhero` | The Helmsman | akcja komponentu | `component.action` · action | tak | [hero] Choose 1 system that does not contain other players' ships; you may move your flagship and any number … |
| `technologies:is` | Inheritance Systems | efekt ciągły | — | tak | You may exhaust this card and spend 2 resources when you research a technology; ignore all of that technology… |
| `technologies:sdn2` | Super Dreadnought II | efekt ciągły | — | — | Cost 4, Combat 4, Move 2, Capacity 2 SUSTAIN DAMAGE, BOMBARDMENT 4 This unit cannot be destroyed by "Direct H… |
| `breakthroughs:l1z1xbt` | Fealty Uplink | reakcja w oknie | `planet.control_gained` · when | — | When you gain control of a planet, place infantry from your reinforcements equal to that planet's influence v… |

### The Barony of Letnev (`letnev`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:war_funding` | War Funding | reakcja w oknie | `combat.roll` · after | tak | After you and your opponent roll dice during space combat: You may reroll all of your opponent's dice. You ma… |
| `abilities:armada` | Armada | efekt ciągły | — | — | The maximum number of non-fighter ships you can have in each system is equal to 2 more than the number of tok… |
| `abilities:munitions` | Munitions Reserves | reakcja w oknie | `combat.round` · start | tak | You may spend 2 trade goods to re-roll any number of your dice during that combat round. |
| `leaders:letnevagent` | Viscount Unlenn | reakcja w oknie | `combat.round` · start | tak | [agent] You may exhaust this card to choose 1 ship in the active system; that ship rolls 1 additional die dur… |
| `leaders:letnevcommander` | Rear Admiral Farran | reakcja w oknie | `unit.sustain_damage` · after | tak | [commander] You may gain 1 trade good. |
| `leaders:letnevhero` | Darktalon Treilla | akcja komponentu | `component.action` · action | — | [hero] Place this card near the game board; the number of non-fighter ships you can have in systems is not li… |
| `technologies:l4` | L4 Disruptors | reakcja w oknie | `invasion` · during | — | During an invasion, units cannot use SPACE CANNON against your units. |
| `technologies:nes` | Non-Euclidean Shielding | reakcja w oknie | `unit.sustain_damage` · when | — | When 1 of your units uses SUSTAIN DAMAGE, cancel 2 hits instead of 1. |
| `breakthroughs:letnevbt` | Gravleash Maneuvers | reakcja w oknie | `combat.roll` · before | — | Before you roll dice during space combat, apply +X to the results of 1 of your ship's rolls, where X is the n… |

### The Mahact Gene-Sorcerers (`mahact`) — 10 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:scepter` | Scepter of Dominion | reakcja w oknie | `phase` · start [phase=strategy] | — | At the start of the strategy phase: Choose 1 non-home system that contains your units; each other player who … |
| `abilities:edict` | Edict | reakcja w oknie | `combat.won` · when | — | Other players' tokens in your fleet pool increase your fleet limit but cannot be redistributed. Place 1 comma… |
| `abilities:hubris` | Hubris | reakcja w oknie | `game.setup` · during | — | During setup, purge your "Alliance" promissory note. Other players cannot give you their "Alliance" promissor… |
| `abilities:imperia` | Imperia | efekt ciągły | — | — | While another player's command token is in your fleet pool, you can use the ability of that player's commande… |
| `leaders:mahactagent` | Jae Mir Kan | reakcja w oknie | `strategy.token_spent` · when [would] | tak | [agent] You may exhaust this card to remove 1 of the active player's command tokens from the board and use it… |
| `leaders:mahactcommander` | Il Na Viroset | reakcja w oknie | `tactical.action` · during | — | [commander] you can activate systems that contain your command tokens. If you do, return both command tokens … |
| `leaders:mahacthero` | Airo Shir Aur | akcja komponentu | `component.action` · action | — | [hero] Move all units in the space area of any system to an adjacent system that contains a different player'… |
| `technologies:cl2` | Crimson Legionnaire II | reakcja w oknie | `turn` · start | — | Cost 1(x2), Combat 7 After this unit is destroyed, gain 1 commodity or convert 1 of your commodities to a tra… |
| `technologies:gr` | Genetic Recombination | efekt ciągły | — | tak | You may exhaust this card before a player casts votes; that player must cast at least 1 vote for an outcome o… |
| `breakthroughs:mahactbt` | Vaults of the Heir | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card and purge 1 of your technologies to gain 1 relic. |

### The Mentak Coalition (`mentak`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:pop` | Promise of Protection | akcja komponentu | `component.action` · action | — | ACTION: Place this card faceup in your play area. While this card is in your play area, the Mentak player can… |
| `abilities:ambush` | Ambush | reakcja w oknie | `combat` · start | tak | You may roll 1 die for each of up to 2 of your cruisers or destroyers in the system. For each result equal to… |
| `abilities:pillage` | Pillage | reakcja w oknie | `economy.trade_goods_gained` · after | tak | If they have 3 or more trade goods, you may take 1 of their trade goods or commodities. |
| `leaders:mentakagent` | Suffi An | reakcja w oknie | `faction.ability_used` · after | tak | [agent] You may exhaust this card; if you do, you and that player each draw 1 action card. |
| `leaders:mentakcommander` | S'ula Mentarion | reakcja w oknie | `combat.won` · after | tak | [commander] You may force your opponent to give you 1 promissory note from their hand. |
| `leaders:mentakhero` | Ipswitch, Loose Cannon | reakcja w oknie | `combat` · start | tak | [hero] You may purge this card; if you do, for each other player's ship that is destroyed during this combat,… |
| `technologies:mc` | Mirror Computing | reakcja w oknie | `economy.resources_spent` · when | — | When you spend trade goods, each trade good is worth 2 resources or influence instead of 1. |
| `technologies:so` | Salvage Operations | reakcja w oknie | `combat.won` · after | tak | After you win or lose a space combat, gain 1 trade good; if you won the combat, you may also produce 1 ship i… |
| `breakthroughs:mentakbt` | The Table's Grace | efekt ciągły | — | — | If you have the Cruiser II unit upgrade technology, flip this card and place it on top of Cruiser II. Corsair… |

### The Embers of Muaat (`muaat`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:fires` | Fires of the Gashlai | akcja komponentu | `component.action` · action | — | ACTION: Remove 1 token from the Muaat player's fleet pool and return it to their reinforcements. Then, gain y… |
| `abilities:gashlai_physiology` | Gashlai Physiology | efekt ciągły | — | — | Your ships can move through supernovas. |
| `abilities:star_forge` | Star Forge | akcja komponentu | `component.action` · action | — | Spend 1 token from your strategy pool to place either 2 fighters or 1 destroyer from your reinforcements in a… |
| `leaders:muaatagent` | Umbat | akcja komponentu | `component.action` · action | tak | [agent] Exhaust this card to choose a player; that player may produce up to 2 units that each have a cost of … |
| `leaders:muaatcommander` | Magmus | reakcja w oknie | `strategy.token_spent` · after | tak | [commander] You may gain 1 trade good. |
| `leaders:muaathero` | Adjudicator Ba'al | reakcja w oknie | `tactical.ships_moved` · after | tak | [hero] You may destroy all other players' units in that system and replace that system tile with the Muaat su… |
| `technologies:mr` | Magmus Reactor | efekt ciągły | — | — | Your ships can move into supernovas. Each supernova that contains 1 or more of your units gains the PRODUCTIO… |
| `technologies:pws2` | Prototype War Sun II | efekt ciągły | — | — | Cost 10, Combat 3(x3), Move 3, Capacity 6 SUSTAIN DAMAGE, BOMBARDMENT 3(x3) Other players' units in this syst… |
| `breakthroughs:muaatbt` | Stellar Genesis | przy zdobyciu | `component.gained` · when | tak | When you gain this card, place the Avernus planet token into a non-home system that is adjacent to a planet y… |

### The Naalu Collective (`naalu`) — 10 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:gift` | Gift of Prescience | reakcja w oknie | `phase` · end [phase=strategy] | — | At the end of the Strategy Phase: Place this card faceup in your play area and place the Naalu '0' token on y… |
| `abilities:foresight` | Foresight | reakcja w oknie | `tactical.ships_moved` · after | tak | You may place 1 token from your strategy pool in an adjacent system that does not contain another player's sh… |
| `abilities:telepathic` | Telepathic | reakcja w oknie | `phase` · end [phase=strategy] | — | Place the Naalu "0" token on your strategy card; you are first in initiative order. |
| `leaders:naaluagent` | Z'eu | akcja komponentu | `component.action` · action | tak | [agent] Exhaust this card and choose a player. That player may perform a tactical action in a non-home system… |
| `leaders:naaluagent-te` | Z'eu | reakcja w oknie | `tokens.placed` · after | tak | [agent] You may exhaust this card to return that token to that player's reinforcements. |
| `leaders:naalucommander` | M'aban | reakcja w oknie | `any_time` · any | tak | [commander] You may look at your neighbors' hands of promissory notes and the top and bottom card of the agen… |
| `leaders:naaluhero` | The Oracle | reakcja w oknie | `phase` · end [phase=status] | tak | [hero] You may force each other player to give you 1 promissory note from their hand. If you do, purge this c… |
| `technologies:hcf2` | Hybrid Crystal Fighter II | efekt ciągły | — | tak | Cost 1(x2), Combat 7, Move 2 This unit may move without being transported. Each fighter in excess of your shi… |
| `technologies:ng` | Neuroglaive | reakcja w oknie | `tactical.system_activated` · after | — | After another player activates a system that contains 1 or more of your ships, that player removes 1 token fr… |
| `breakthroughs:naalubt` | Mindsieve | reakcja w oknie | `strategy.action` · when [would] | tak | When you would resolve the secondary ability of another player's strategy card, you may give them a promissor… |

### The Naaz-Rokha Alliance (`naaz-rokha`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:bmf` | Black Market Forgery | akcja komponentu | `component.action` · action | — | ACTION: Purge 2 of your relic fragments of the same type to gain 1 relic. Then, return this card to the Naaz-… |
| `abilities:distant_suns` | Distant Suns | reakcja w oknie | `planet.explored` · when | tak | You may draw 1 additional card; choose 1 to resolve and discard the rest. |
| `abilities:fabrication` | Fabrication | akcja komponentu | `component.action` · action | — | Either purge 2 of your relic fragments of the same type to gain 1 relic or purge 1 of your relic fragments to… |
| `leaders:naazagent` | Garv and Gunn | reakcja w oknie | `turn` · end | tak | [agent] You may exhaust this card to allow that player to explore 1 of their planets. |
| `leaders:naazcommander` | Dart and Tai | reakcja w oknie | `planet.control_gained` · after | tak | [commander] You may explore that planet. |
| `leaders:naazhero` | Hesh and Prit | akcja komponentu | `component.action` · action | — | [hero] Gain 1 relic and perform the secondary ability of up to 2 readied or unchosen strategy cards; during t… |
| `technologies:pfa` | Pre-Fab Arcologies | reakcja w oknie | `planet.explored` · after | — | After you explore a planet, ready that planet. |
| `technologies:sc` | Supercharge | reakcja w oknie | `combat.round` · start | tak | At the start of a combat round, you may exhaust this card to apply +1 to the result of each of your unit's co… |
| `breakthroughs:naazbt` | Absolute Synergy | reakcja w oknie | `state.condition` · when | tak | When you have 4 mechs in the same system, you may return 3 of those mechs to your reinforcements to flip this… |

### The Nekro Virus (`nekro`) — 12 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:antivirus` | Antivirus | reakcja w oknie | `combat` · start | — | At the start of a combat: Place this card faceup in your play area. While this card is in your play area, the… |
| `abilities:galactic_threat` | Galactic Threat | reakcja w oknie | `agenda.revealed` · after [1/agenda phase] | tak | You cannot vote on agendas You may predict aloud the outcome of that agenda. If your prediction is correct, g… |
| `abilities:propagation` | Propagation | reakcja w oknie | `technology.research` · when [would] | — | You cannot research technology Gain 3 command tokens instead. |
| `abilities:technological_singularity` | Technological Singularity | reakcja w oknie | `unit.destroyed` · after [1/combat] | tak | You may gain 1 technology that is owned by that player. |
| `leaders:nekroagent` | Nekro Malleon | reakcja w oknie | `phase` · during [phase=action] | tak | [agent] You may exhaust this card to choose a player; that player may discard 1 action card or spend 1 comman… |
| `leaders:nekrocommander` | Nekro Acidos | reakcja w oknie | `technology.gained` · after | tak | [commander] You may draw 1 action card. |
| `leaders:nekrohero` | UNIT.DSGN.FLAYESH | akcja komponentu | `component.action` · action | — | [hero] Choose a planet that has a technology specialty in a system that contains your units. Destroy any othe… |
| `technologies:nekroc4r` | ???\_ERROR\_ERROR\_??? | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card to place 1 PDS on a planet you control. ACTION: Exhaust this card to repair all of … |
| `technologies:nekroc4y` | ???\_NULL\_REFERENCE\_??? | reakcja w oknie | `unit.destroyed` · when | tak | When one of your ships is destroyed, you may produce a ship of the same type at a space dock in your home sys… |
| `technologies:vax` | Valefar Assimilator X | reakcja w oknie | `technology.gained` · when [would] | tak | When you would gain another player's technology using 1 of your faction abilities, you may place the "X" assi… |
| `technologies:vay` | Valefar Assimilator Y | reakcja w oknie | `technology.gained` · when [would] | tak | When you would gain another player's technology using 1 of your faction abilities, you may place the "Y" assi… |
| `breakthroughs:nekrobt` | Valefar Assimilator Z | reakcja w oknie | `technology.gained` · when [would] | tak | When you would gain another player's technology using one of your faction abilities, you may instead place on… |

### The Nomad (`nomad`) — 11 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:cavalry` | The Cavalry | reakcja w oknie | `combat` · start | — | At the start of a space combat against a player other than the Nomad: During this combat, treat 1 of your non… |
| `abilities:future_sight` | Future Sight | reakcja w oknie | `agenda.outcome_resolved` · after | — | Gain 1 trade good |
| `abilities:the_company` | The Company | reakcja w oknie | `game.setup` · during | — | During setup, take the 2 additional Nomad faction agents and place them next to your faction sheet; you have … |
| `leaders:nomadagentartuno` | Artuno the Betrayer | reakcja w oknie | `economy.trade_goods_gained` · when | tak | [agent] You may exhaust this card to place an equal number of trade goods on this card. When this card readie… |
| `leaders:nomadagentmercer` | Field Marshal Mercer | reakcja w oknie | `turn` · end | tak | [agent] You may exhaust this card to allow that player to remove up to 2 of their ground forces from the game… |
| `leaders:nomadagentthundarian` | The Thundarian | reakcja w oknie | `combat.step` · after [step=roll_dice] | tak | [agent] You may exhaust this card. If you do, hits are not assigned to either player's units. Return to the s… |
| `leaders:nomadcommander` | Navarch Feng | reakcja w oknie | `production.units_produced` · when | — | [commander] You can produce your flagship without spending resources. |
| `leaders:nomadhero` | Ahk-Syl Siven | akcja komponentu | `component.action` · action | — | [hero] Place this card near the game board; your flagship and units it transports can move out of systems tha… |
| `technologies:m2` | Memoria II | efekt ciągły | — | tak | Cost 8, Combat 5(x2), Move 2, Capacity 6 SUSTAIN DAMAGE, ANTI-FIGHTER BARRAGE 5(x3) You may treat this unit a… |
| `technologies:tcs` | Temporal Command Suite | reakcja w oknie | `component.exhausted` · after | tak | After any player's agent becomes exhausted, you may exhaust this card to ready that agent; if you ready anoth… |
| `breakthroughs:nomadbt` | Thunder's Paradox | reakcja w oknie | `turn` · start | tak | At the start of any player's turn, you may exhaust 1 of your agents to ready any other agent. |

### The Ral Nel Consortium (`ral nel`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:nanolink` | Nano-Link Permit | reakcja w oknie | `tactical.system_activated` · after | tak | After you activate a system: You may move your structures from adjacent systems that do not contain your comm… |
| `abilities:miniaturization` | Miniaturization | reakcja w oknie | `tactical.action` · end | tak | Your structures can be transported by any ship; this does not require or count against capacity. While your s… |
| `abilities:survivalinstinct` | Survival Instinct | reakcja w oknie | `tactical.system_activated` · after | tak | You may move up to 2 of your ships into the active system from adjacent systems that do not contain your comm… |
| `leaders:ralnelagent` | Kan Kip Rel | akcja komponentu | `component.action` · action | — | [agent] Exhaust this card to draw 2 action cards; give 1 of those cards to another player. |
| `leaders:ralnelcommander` | Watchful Ojz | reakcja w oknie | `combat.retreat` · when | — | [commander] Immediately retreat up to 2 of your ships from the active system to an adjacent system that does … |
| `leaders:ralnelhero` | Director Nel | reakcja w oknie | `player.last_passed` · after | tak | [hero] You may choose to no longer be passed; if you do, gain 2 command tokens, draw 1 action card, and purge… |
| `technologies:linkship2` | Linkship II | efekt ciągły | — | — | Cost 1, Combat 8, Move 4, ANTI-FIGHTER BARRAGE 6 (x3). This unit can use the SPACE CANNON ability of one of y… |
| `technologies:nanomachines` | Nanomachines | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card to place 1 PDS on a planet you control. ACTION: Exhaust this card to repair all of … |
| `breakthroughs:ralnelbt` | Data Skimmer | reakcja w oknie | `phase` · during [phase=action] | — | During the action phase, if you have not passed, when other players would discard action cards, they are plac… |

### The Crimson Rebellion (`rebellion`) — 13 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:sever` | Sever | akcja komponentu | `component.action` · action | — | ACTION: Place this card faceup in your play area and place the sever token in a system that contains your uni… |
| `abilities:incursion` | Incursion | reakcja w oknie | `tactical.system_activated` · when | tak | When you activate a system that contains a breach, you may flip that breach; systems that contain active brea… |
| `abilities:sorrow` | The Sorrow | reakcja w oknie | `game.setup` · when | — | When you create the game board, place The Sorrow (tile 94) where your home system would be placed, and place … |
| `abilities:sundered` | Sundered | efekt ciągły | — | — | You cannot use wormholes other than epsilon wormholes. Other players' units that move or are placed into your… |
| `leaders:crimsonagent` | Ahk Ravin | akcja komponentu | `component.action` · action | tak | [agent] Exhaust this card to choose 1 player. That player may swap the position of 2 of their ships in any sy… |
| `leaders:crimsoncommander` | Ahk Siever | reakcja w oknie | `combat` · end | — | [commander] Gain 1 commodity or convert 1 of your commodities to a trade good. |
| `leaders:crimsonhero` | Homesick Phantom | reakcja w oknie | `production.units_produced` · when | tak | [hero] You may place any of those ships onto this card. At the start of a space combat, you may purge this ca… |
| `leaders:redcreussagent` | "Who Knows?" | akcja komponentu | `component.action` · action | tak | [agent] Exhaust this card to choose 1 player. That player may swap the position of 2 of their ships in any sy… |
| `leaders:redcreusscommander` | "Total Mystery" | reakcja w oknie | `combat` · end | — | [commander] Gain 1 commodity or convert 1 of your commodities to a trade good. |
| `leaders:redcreusshero` | "A Tall Stranger" | reakcja w oknie | `production.units_produced` · when | tak | [hero] You may place any of those ships onto this card. At the start of a space combat, you may purge this ca… |
| `technologies:exile2` | Exile II | reakcja w oknie | `combat` · end | tak | Cost 1, Combat 7, Move 2, ANTI-FIGHTER BARRAGE 6 (x3). At the end of any player's combat in this unit's syste… |
| `technologies:subatomic` | Subatomic Splicer | reakcja w oknie | `unit.destroyed` · when | tak | When one of your ships is destroyed, you may produce a ship of the same type at a space dock in your home sys… |
| `breakthroughs:crimsonbt` | Resonance Generator | akcja komponentu | `component.action` · action | — | During your tactical actions, apply +1 to the move value of each of your ships that starts its movement in yo… |

### The Clan of Saar (`saar`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:ragh` | Ragh's Call | reakcja w oknie | `tactical.units_committed` · after | — | After you commit 1 or more units to land on a planet: Remove all of the Saar player's ground forces from that… |
| `abilities:nomadic` | Nomadic | efekt ciągły | — | — | You can score objectives even if you do not control the planets in your home system. |
| `abilities:scavenge` | Scavenge | reakcja w oknie | `planet.control_gained` · after | — | Gain 1 trade good. |
| `leaders:saaragent` | Captain Mendosa | reakcja w oknie | `tactical.system_activated` · when | tak | [agent] You may exhaust this card to increase the move value of 1 of that player's ships to match the move va… |
| `leaders:saarcommander` | Rowl Sarrig | reakcja w oknie | `production.units_produced` · when | tak | [commander] You may place each of those units at any of your space docks that are not blockaded. |
| `leaders:saarhero` | Gurno Aggero | akcja komponentu | `component.action` · action | — | [hero] Choose 1 system that is adjacent to 1 of your space docks. Destroy all other players' infantry and fig… |
| `technologies:cm` | Chaos Mapping | reakcja w oknie | `turn` · start | tak | Other players cannot activate asteroid fields that contain 1 or more of your ships. At the start of your turn… |
| `technologies:ffac2` | Floating Factory II | efekt ciągły | — | — | Move 2, Capacity 5 PRODUCTION 7. This unit is placed in a space area instead of on a planet. This unit can mo… |
| `breakthroughs:saarbt` | Deorbit Barrage | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card and spend any amount of resources to choose a planet up to 2 systems away from an a… |

### Sardakk Norr (`sardakk`) — 8 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:tekklar` | Tekklar Legion | reakcja w oknie | `combat` · start | — | At the start of an invasion combat: Apply +1 to the result of each of your unit's combat rolls during this co… |
| `abilities:unrelenting` | Unrelenting | efekt ciągły | — | — | Apply +1 to the result of each of your unit's combat rolls. |
| `leaders:sardakkagent` | T'ro | reakcja w oknie | `tactical.action` · end | tak | [agent] You may exhaust this card; if you do, that player may place 2 infantry from their reinforcements on a… |
| `leaders:sardakkcommander` | G'hom Sek'kus | reakcja w oknie | `tactical.units_committed` · during | — | [commander] You can commit (move) up to 1 ground force from each planet in the active system and each planet … |
| `leaders:sardakkhero` | Sh'val, Harbinger | reakcja w oknie | `tactical.ships_moved` · after | tak | [hero] You may skip directly to the "Commit Ground Forces" step. If you do, after you commit ground forces to… |
| `technologies:exo2` | Exotrireme II | reakcja w oknie | `combat.round` · after | tak | Cost 4, Combat 5, Move 2, Capacity 1 SUSTAIN DAMAGE, BOMBARDMENT 4(x2) This unit cannot be destroyed by "Dire… |
| `technologies:vpw` | Valkyrie Particle Weave | reakcja w oknie | `combat.round` · after | — | After making combat rolls during a round of ground combat, if your opponent produced 1 or more hits, you prod… |
| `breakthroughs:sardakkbt` | N'orr Supremacy | reakcja w oknie | `combat.won` · after | — | After you win a combat, either gain 1 command token or research a unit upgrade technology. |

### The Federation of Sol (`sol`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:ms` | Military Support | reakcja w oknie | `turn` · start | tak | At the start of the Sol player's turn: Remove 1 token from the Sol player's strategy pool, if able, and retur… |
| `abilities:orbital_drop` | Orbital Drop | akcja komponentu | `component.action` · action | — | Spend 1 token from your strategy pool to place 2 infantry from your reinforcements on 1 planet you control. |
| `abilities:versatile` | Versatile | reakcja w oknie | `status.step` · when [step=gain_command_tokens] | — | Gain 1 additional command token. |
| `leaders:solagent` | Evelyn DeLouis | reakcja w oknie | `combat.round` · start | tak | [agent] You may exhaust this card to choose 1 ground force in the active system; that ground force rolls 1 ad… |
| `leaders:solcommander` | Claire Gibson | reakcja w oknie | `combat` · start | tak | [commander] You may place 1 infantry from your reinforcements on that planet. |
| `leaders:solhero` | Jace X, 4th Air Legion | akcja komponentu | `component.action` · action | — | [hero] Remove each of your command tokens from the game board and return them to your reinforcements. Then, p… |
| `technologies:ac2` | Advanced Carrier II | efekt ciągły | — | — | Cost 3, Combat 9, Move 2, Capacity 8 SUSTAIN DAMAGE |
| `technologies:so2` | Spec Ops II | reakcja w oknie | `turn` · start | — | Cost 1(x2), Combat 6 After this unit is destroyed, roll 1 die. If the result is 5 or greater, place the unit … |
| `breakthroughs:solbt` | Bellum Gloriosum | reakcja w oknie | `production.units_produced` · when | tak | When you produce a ship that has capacity, you may also produce any combination of ground forces or fighters … |

### The Titans of Ul (`ul`) — 10 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:terraform` | Terraform | akcja komponentu | `component.action` · action | — | ACTION: Attach this card to a non-home planet you control other than Mecatol Rex. Its resource and influence … |
| `abilities:awaken` | Awaken | reakcja w oknie | `tactical.system_activated` · after | tak | You may replace each of those tokens with 1 PDS from your reinforcements. |
| `abilities:coalescence` | Coalescence | efekt ciągły | — | — | If your flagship or your AWAKEN faction ability places your units into the same space area or onto the same p… |
| `abilities:terragenesis` | Terragenesis | reakcja w oknie | `planet.explored` · after | tak | You may place or move 1 sleeper token onto that planet. |
| `leaders:titansagent` | Tellurian | reakcja w oknie | `combat.hits_assigned` · before [would] | tak | [agent] You may exhaust this card to cancel that hit. |
| `leaders:titanscommander` | Tungstantus | reakcja w oknie | `production.used` · when | tak | [commander] You may gain 1 trade good. |
| `leaders:titanshero` | Ul the Progenitor | akcja komponentu | `component.action` · action | — | [hero] Ready Elysium and attach this card to it. Its resource and influence values are each increased by 3, a… |
| `technologies:ht2` | Hel-Titan II | efekt ciągły | — | tak | Combat 6 PLANETARY SHIELD, SPACE CANNON 5, SUSTAIN DAMAGE, PRODUCTION 1 This unit is treated as both a struct… |
| `technologies:se2` | Saturn Engine II | efekt ciągły | — | — | Cost 2, Combat 6, Move 3, Capacity 2 SUSTAIN DAMAGE |
| `breakthroughs:titansbt` | Slumberstate Computing | reakcja w oknie | `phase` · during [phase=status] | tak | When COALESCENCE results in a ground combat, if you commit no other units, you may choose for your units to c… |

### The Vuil'raith Cabal (`vuil'raith`) — 10 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:crucible` | Crucible | reakcja w oknie | `tactical.system_activated` · after | — | After you activate a system: Your ships do not roll for gravity rifts during this movement; apply an addition… |
| `abilities:amalgamation` | Amalgamation | reakcja w oknie | `production.units_produced` · when | tak | You may return 1 captured unit of that type to produce that unit without spending resources. |
| `abilities:devour` | Devour | efekt ciągły | — | — | Capture your opponent's non-structure units that are destroyed during combat. |
| `abilities:riftmeld` | Riftmeld | reakcja w oknie | `technology.research` · when [unit_upgrade=true] | tak | You may return 1 captured unit of that type to ignore all of that technology's prerequisites. |
| `leaders:cabalagent` | The Stillness of Stars | reakcja w oknie | `economy.commodities_replenished` · after | tak | [agent] You may exhaust this card to convert their commodities to trade goods and capture 1 unit from their r… |
| `leaders:cabalcommander` | That Which Molds Flesh | reakcja w oknie | `production.units_produced` · when | — | [commander] Up to 2 of those units do not count against your PRODUCTION limit. |
| `leaders:cabalhero` | It Feeds on Carrion | akcja komponentu | `component.action` · action | — | [hero] Each other player rolls a die for each of his non-fighter ships that are in or adjacent to a system th… |
| `technologies:dt2` | Dimensional Tear II | efekt ciągły | — | — | PRODUCTION 7 This system is a gravity rift; your ships do not roll for this gravity rift. Place a dimensional… |
| `technologies:vtx` | Vortex | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card to choose another player's non-structure unit in a system that is adjacent to 1 or … |
| `breakthroughs:cabalbt` | Al'raith Ix Ianovar | przy zdobyciu | `component.gained` · after | — | This breakthrough causes The Fracture to enter play without a roll, if it is not already in play. After this … |

### The Winnu (`winnu`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:acq` | Acquiescence | reakcja w oknie | `strategy.action` · when | — | When the Winnu player resolves a strategic action: You do not have to spend or place a command token to resol… |
| `abilities:blood_ties` | Blood Ties | efekt ciągły | — | — | You do not have to spend influence to remove the custodians token from Mecatol Rex. |
| `abilities:reclamation` | Reclamation | reakcja w oknie | `tactical.action` · after | tak | You may place 1 PDS and 1 space dock from your reinforcements on Mecatol Rex. |
| `leaders:winnuagent` | Berekar Berekon | reakcja w oknie | `production.used` · when | tak | [agent] You may exhaust this card to reduce the combined cost of the produced units by 2. |
| `leaders:winnucommander` | Rickar Rickani | reakcja w oknie | `combat` · during | — | [commander] Apply +2 to the result of each of your unit's combat rolls in the Mecatol Rex system, your home s… |
| `leaders:winnuhero` | Mathis Mathinus | akcja komponentu | `component.action` · action | tak | [hero] Perform the primary ability of any strategy card. Then, choose any number of other players. Those play… |
| `technologies:htp` | Hegemonic Trade Policy | efekt ciągły | — | — | Exhaust this card when 1 or more of your units use PRODUCTION; swap the resource and influence values of 1 pl… |
| `technologies:lgf` | Lazax Gate Folding | akcja komponentu | `component.action` · action | — | During your tactical actions, if you do not control Mecatol Rex, treat its system as if it has both an α and … |
| `breakthroughs:winnubt` | Imperator | reakcja w oknie | `tactical.system_activated` · after | — | Apply +1 to the results of each of your unit's combat rolls for each "Support for the Throne" in your opponen… |

### The Xxcha Kingdom (`xxcha`) — 10 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:favor` | Political Favor | reakcja w oknie | `agenda.revealed` · when | — | When an agenda is revealed: Remove 1 token from the Xxcha player's strategy pool and return it to their reinf… |
| `abilities:peace_accords` | Peace Accords | reakcja w oknie | `strategy.action` · after | tak | You may gain control of 1 planet other than Mecatol Rex that does not contain any units and is in a system th… |
| `abilities:quash` | Quash | reakcja w oknie | `agenda.revealed` · when | tak | You may spend 1 token from your strategy pool to discard that agenda and reveal 1 agenda from the top of the … |
| `leaders:xxchaagent` | Ggrocuto Rinn | akcja komponentu | `component.action` · action | tak | [agent] Exhaust this card to ready any planet; if that planet is in a system that is adjacent to a planet you… |
| `leaders:xxchacommander` | Elder Qanoj | reakcja w oknie | `agenda.votes_cast` · when | — | [commander] Each planet you exhaust to cast votes provides 1 additional vote. Game effects cannot prevent you… |
| `leaders:xxchahero` | Xxekir Grom | reakcja w oknie | `planet.exhausted` · when | — | [hero] combine the values of their resources and influence. Treat the combined value as if it were both resou… |
| `leaders:xxchahero-te` | Xxekir Grom | akcja komponentu | `component.action` · action | — | [hero] Place any combination of up to 4 PDS or mechs onto planets you control; ready each planet that you pla… |
| `technologies:it` | Instinct Training | efekt ciągły | — | tak | You may exhaust this card and spend 1 token from your strategy pool when another player plays an action card;… |
| `technologies:nf` | Nullification Field | reakcja w oknie | `tactical.system_activated` · after | tak | After another player activates a system that contains 1 or more of your ships, you may exhaust this card and … |
| `breakthroughs:xxchabt` | Archon's Gift | efekt ciągły | — | — | You can spend influence as if it were resources. You can spend resources as if it were influence. |

### The Yin Brotherhood (`yin`) — 9 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:greyfire` | Greyfire Mutagen | reakcja w oknie | `combat` · start | — | At the start of a ground combat against 2 or more ground forces that are not controlled by the Yin player: Re… |
| `abilities:devotion` | Devotion | reakcja w oknie | `combat.round` · after | tak | You may destroy 1 of your cruisers or destroyers in the active system to produce 1 hit and assign it to 1 of … |
| `abilities:indoctrination` | Indoctrination | reakcja w oknie | `combat` · start | tak | You may spend 2 influence to replace 1 of your opponent's participating infantry with 1 infantry from your re… |
| `leaders:yinagent` | Brother Milor | reakcja w oknie | `unit.destroyed` · after | tak | [agent] You may exhaust this card to allow that player to place 2 fighters in the destroyed unit's system if … |
| `leaders:yincommander` | Brother Omar | reakcja w oknie | `any_time` · any | tak | [commander] This card satisfies a green technology prerequisite. When you research a tech owned by another pl… |
| `leaders:yinhero` | Dannel of the Tenth | akcja komponentu | `component.action` · action | — | [hero] Commit up to 3 infantry from your reinforcements to any non-home planets and resolve ground combats on… |
| `technologies:ic` | Impulse Core | reakcja w oknie | `combat` · start | tak | At the start of a space combat, you may destroy 1 of your cruisers or destroyers in the active system to prod… |
| `technologies:yso` | Yin Spinner | reakcja w oknie | `production.units_produced` · after | — | After you produce units, place up to 2 infantry from your reinforcements on any planet you control or in any … |
| `breakthroughs:yinbt` | Yin Ascendant | reakcja w oknie | `objective.scored` · when | — | When you gain this card or score a public objective, gain the alliance ability of a random, unused faction. |

### The Yssaril Tribes (`yssaril`) — 10 komponentów

| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |
|---|---|---|---|:---:|---|
| `promissory_notes:spynet` | Spy Net | reakcja w oknie | `turn` · start | — | At the start of your turn: Look at the Yssaril player's hand of action cards. Choose 1 of those cards and add… |
| `abilities:crafty` | Crafty | efekt ciągły | — | — | You can have any number of action cards in your hand. Game effects cannot prevent you from using this ability. |
| `abilities:scheming` | Scheming | reakcja w oknie | `cards.action_drawn` · when | — | Draw 1 additional action card. Then, choose and discard 1 action card from your hand. |
| `abilities:stall_tactics` | Stall Tactics | akcja komponentu | `component.action` · action | — | Discard 1 action card from your hand. |
| `leaders:yssarilagent` | Ssruu | reakcja w oknie | `any_time` · any | — | [agent] This card has the text ability of each other player's agent, even if that agent is exhausted. |
| `leaders:yssarilcommander` | So Ata | reakcja w oknie | `tactical.system_activated` · after | tak | [commander] You may look at that player's action cards, promissory notes, or secret objectives. |
| `leaders:yssarilhero` | Kyver, Blade and Key | akcja komponentu | `component.action` · action | tak | [hero] Each other player shows you 1 action card from their hand. For each player, you may either take that c… |
| `technologies:mi` | Mageon Implants | akcja komponentu | `component.action` · action | — | ACTION: Exhaust this card to look at another player's hand of action cards. Choose 1 of those cards and add i… |
| `technologies:tp` | Transparasteel Plating | reakcja w oknie | `turn` · during | — | During your turn of the action phase, players that have passed cannot play action cards. |
| `breakthroughs:yssarilbt` | Deepgloom Executable | reakcja w oknie | `phase` · during [phase=action] | tak | You can allow other players to use your STALL TACTICS or SCHEMING faction abilities; when you do, you may res… |

## 7. Karty akcji wg zdarzenia

### `agenda.elected` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:confounding` | Confounding Legal Text | `agenda.elected` · when | pok | You are the elected player instead. |
| `action_cards:confusing` | Confusing Legal Text | `agenda.elected` · when | base | Choose 1 player. That player is the elected player instead. |

### `agenda.outcome_resolved` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:deadly_plot` | Deadly Plot | `agenda.outcome_resolved` · during [would] | pok | If you voted for or predicted another outcome, discard the agenda instead; the agenda is resolved with no eff… |

### `agenda.revealed` (19)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:assassin` | Assassinate Representative | `agenda.revealed` · after | base | Choose 1 player. That player cannot vote on this agenda. |
| `action_cards:const_rider` | Construction Rider | `agenda.revealed` · after | base | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, place… |
| `action_cards:diplo_rider` | Diplomacy Rider | `agenda.revealed` · after | base | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, choos… |
| `action_cards:dp1` | Diplomatic Pressure | `agenda.revealed` · when | pok | Choose another player; that player must give you 1 promissory note from their hand. |
| `action_cards:dp2` | Diplomatic Pressure | `agenda.revealed` · when | pok | Choose another player; that player must give you 1 promissory note from their hand. |
| `action_cards:dp3` | Diplomatic Pressure | `agenda.revealed` · when | pok | Choose another player; that player must give you 1 promissory note from their hand. |
| `action_cards:dp4` | Diplomatic Pressure | `agenda.revealed` · when | pok | Choose another player; that player must give you 1 promissory note from their hand. |
| `action_cards:hack` | Hack Election | `agenda.revealed` · after | codex1 | During this agenda, you vote last. |
| `action_cards:imp_rider` | Imperial Rider | `agenda.revealed` · after | base | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, gain … |
| `action_cards:insider` | Insider Information | `agenda.revealed` · after | codex1 | Look at the top 3 cards of the agenda deck. |
| `action_cards:lead_rider` | Leadership Rider | `agenda.revealed` · after | base | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, gain … |
| `action_cards:politic_rider` | Politics Rider | `agenda.revealed` · after | base | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, draw … |
| `action_cards:sanction` | Sanction | `agenda.revealed` · after | codex1 | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, each … |
| `action_cards:tech_rider` | Technology Rider | `agenda.revealed` · after | base | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, resea… |
| `action_cards:trade_rider` | Trade Rider | `agenda.revealed` · after | base | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, gain … |
| `action_cards:veto` | Veto | `agenda.revealed` · when | base | Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead. |
| `action_cards:veto3` | Veto | `agenda.revealed` · when | base | Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead. |
| `action_cards:veto4` | Veto | `agenda.revealed` · when | base | Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead. |
| `action_cards:war_rider` | Warfare Rider | `agenda.revealed` · after | base | You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your prediction is correct, place… |

### `agenda.votes_cast` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:bribery` | Bribery | `agenda.votes_cast` · after | base | Spend any number of trade goods. For each trade good spent, cast 1 additional vote for the outcome on which y… |
| `action_cards:distinguished` | Distinguished Councilor | `agenda.votes_cast` · after | base | Cast 5 additional votes for that outcome. |

### `cards.action_discarded` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:reverse_engineer` | Reverse Engineer | `cards.action_discarded` · after | pok | Take that action card from the discard pile. |

### `cards.action_played` (4)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:sabo1` | Sabotage | `cards.action_played` · when | base | Cancel that action card. |
| `action_cards:sabo2` | Sabotage | `cards.action_played` · when | base | Cancel that action card. |
| `action_cards:sabo3` | Sabotage | `cards.action_played` · when | base | Cancel that action card. |
| `action_cards:sabo4` | Sabotage | `cards.action_played` · when | base | Cancel that action card. |

### `combat` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:reveal_prototype` | Reveal Prototype | `combat` · start | pok | Spend 4 resources to research a unit upgrade technology of the same type as 1 of your units that is participa… |

### `combat.hits_assigned` (8)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:mjets1` | Maneuvering Jets | `combat.hits_assigned` · before | base | Cancel 1 hit. |
| `action_cards:mjets2` | Maneuvering Jets | `combat.hits_assigned` · before | base | Cancel 1 hit. |
| `action_cards:mjets3` | Maneuvering Jets | `combat.hits_assigned` · before | base | Cancel 1 hit. |
| `action_cards:mjets4` | Maneuvering Jets | `combat.hits_assigned` · before | base | Cancel 1 hit. |
| `action_cards:sh1` | Shields Holding | `combat.hits_assigned` · before | base | Cancel up to 2 hits. |
| `action_cards:sh2` | Shields Holding | `combat.hits_assigned` · before | base | Cancel up to 2 hits. |
| `action_cards:sh3` | Shields Holding | `combat.hits_assigned` · before | base | Cancel up to 2 hits. |
| `action_cards:sh4` | Shields Holding | `combat.hits_assigned` · before | base | Cancel up to 2 hits. |

### `combat.retreat` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:intercept` | Intercept | `combat.retreat` · after | base | Your opponent cannot retreat during this round of space combat. |

### `combat.roll` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:fire_team` | Fire Team | `combat.roll` · after | base | Reroll any number of your dice. |
| `action_cards:waylay` | Waylay | `combat.roll` · before | pok | Hits from this roll are produced against all ships (not just fighters). |

### `combat.round` (10)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:emergency` | Emergency Repairs | `combat.round` · start | base | Repair all of your units that have SUSTAIN DAMAGE in the active system. |
| `action_cards:f_prototype` | Fighter Prototype | `combat.round` · start | base | Apply +2 to the result of each of your fighters' combat rolls during this combat round. |
| `action_cards:mb1` | Morale Boost | `combat.round` · start | base | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `action_cards:mb2` | Morale Boost | `combat.round` · start | base | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `action_cards:mb3` | Morale Boost | `combat.round` · start | base | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `action_cards:mb4` | Morale Boost | `combat.round` · start | base | Apply +1 to the result of each of your unit's combat rolls during this combat round. |
| `action_cards:s_retreat1` | Skilled Retreat | `combat.round` · start | base | Move all of your ships from the active system into an adjacent system that does not contain another player's … |
| `action_cards:s_retreat2` | Skilled Retreat | `combat.round` · start | base | Move all of your ships from the active system into an adjacent system that does not contain another player's … |
| `action_cards:s_retreat3` | Skilled Retreat | `combat.round` · start | base | Move all of your ships from the active system into an adjacent system that does not contain another player's … |
| `action_cards:s_retreat4` | Skilled Retreat | `combat.round` · start | base | Move all of your ships from the active system into an adjacent system that does not contain another player's … |

### `combat.step` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:rout` | Rout | `combat.step` · start [step=announce_retreats] | pok | Your opponent must announce a retreat, if able. |

### `combat.won` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:salvage` | Salvage | `combat.won` · after | base | Your opponent gives you all of their commodities. |

### `component.action` (43)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:arch_expedition` | Archaeological Expedition | `component.action` · action | pok | Reveal the top 3 cards of an exploration deck that matches a planet you control; gain any relic fragments tha… |
| `action_cards:brilliance` | Brilliance | `component.action` · action | thunders_edge | Ready 1 of your planets that has a technology specialty or choose 1 player to gain their breakthrough. |
| `action_cards:cripple` | Cripple Defenses | `component.action` · action | base | Choose 1 planet. Destroy each PDS on that planet. |
| `action_cards:divert_funding` | Divert Funding | `component.action` · action | pok | Return a non-unit upgrade, non-faction technology that you own to your technology deck. Then, research anothe… |
| `action_cards:economic_initiative` | Economic Initiative | `component.action` · action | base | Ready each cultural planet you control. |
| `action_cards:exchangeprogram` | Exchange Program | `component.action` · action | thunders_edge | Choose another player. You and that player may agree to place 1 infantry from each of your reinforcements int… |
| `action_cards:f_conscription` | Fighter Conscription | `component.action` · action | codex1 | Place 1 fighter from your reinforcements in each system that contains 1 or more of your space docks or units … |
| `action_cards:f_deployment` | Frontline Deployment | `component.action` · action | base | Place 3 infantry from your reinforcements on 1 planet you control. |
| `action_cards:f_researched` | Focused Research | `component.action` · action | base | Spend 4 trade goods to research 1 technology |
| `action_cards:ghost_ship` | Ghost Ship | `component.action` · action | base | Place 1 destroyer from your reinforcements in a non-home system that contains a wormhole and does not contain… |
| `action_cards:impersonation` | Impersonation | `component.action` · action | codex1 | Spend 3 influence to draw 1 secret objective. |
| `action_cards:industrial_initiative` | Industrial Initiative | `component.action` · action | base | Gain 1 trade good for each industrial planet you control. |
| `action_cards:insub` | Insubordination | `component.action` · action | base | Remove 1 token from another player's tactic pool and return it to their reinforcements. |
| `action_cards:jamming` | Signal Jamming | `component.action` · action | base | Choose 1 non-home system that contains or is adjacent to 1 of your ships. Place a command token from another … |
| `action_cards:lucky` | Lucky Shot | `component.action` · action | base | Destroy 1 dreadnought, cruiser, or destroyer in a system that contains a planet you control. |
| `action_cards:master_plan` | Master Plan | `component.action` · after | codex1 | Perform an additional action. |
| `action_cards:meltdown` | Reactor Meltdown | `component.action` · action | base | Destroy 1 space dock in a non-home system. |
| `action_cards:mercenarycontract` | Mercenary Contract | `component.action` · action | thunders_edge | Spend 2 trade goods to place 2 neutral infantry on any non-home planet that contains no units; if that planet… |
| `action_cards:messiah` | Rise of a Messiah | `component.action` · action | base | Place 1 infantry from your reinforcements on each planet you control. |
| `action_cards:mining_initiative` | Mining Initiative | `component.action` · action | base | Gain trade goods equal to the resource value of 1 planet you control. |
| `action_cards:overrule` | Overrule | `component.action` · action | thunders_edge | Perform the primary ability of a readied or unchosen strategy card. |
| `action_cards:piratecontract1` | Pirate Contract | `component.action` · action | thunders_edge | Place 1 neutral destroyer in a non-home system that contains no non-neutral ships. |
| `action_cards:piratecontract2` | Pirate Contract | `component.action` · action | thunders_edge | Place 1 neutral destroyer in a non-home system that contains no non-neutral ships. |
| `action_cards:piratecontract3` | Pirate Contract | `component.action` · action | thunders_edge | Place 1 neutral destroyer in a non-home system that contains no non-neutral ships. |
| `action_cards:piratecontract4` | Pirate Contract | `component.action` · action | thunders_edge | Place 1 neutral destroyer in a non-home system that contains no non-neutral ships. |
| `action_cards:piratefleet` | Pirate Fleet | `component.action` · action | thunders_edge | Spend 3 resources to place 1 neutral carrier, 1 neutral cruiser, 1 neutral destroyer, and 2 neutral fighters … |
| `action_cards:plagiarize` | Plagiarize | `component.action` · action | codex1 | Spend 5 influence and choose a non-faction technology owned by 1 of your neighbors; gain that technology. |
| `action_cards:plague` | Plague | `component.action` · action | base | Choose 1 planet that is controlled by another player. Roll 1 die for each infantry on that planet. For each r… |
| `action_cards:probe` | Exploration Probe | `component.action` · action | pok | Explore a frontier token that is in or adjacent to a system that contains 1 or more of your ships. |
| `action_cards:refit` | Refit Troops | `component.action` · action | pok | Choose 1 or 2 of your infantry on the game board; replace each of those infantry with mechs. |
| `action_cards:repeal` | Repeal Law | `component.action` · action | base | Discard 1 law from play. |
| `action_cards:scuttle` | Scuttle | `component.action` · action | pok | Choose 1 or 2 of your non-fighter ships on the game board and return them to your reinforcements; gain trade … |
| `action_cards:seize` | Seize Artifact | `component.action` · action | pok | Choose 1 of your neighbors that has 1 or more relic fragments. That player must give you 1 relic fragment of … |
| `action_cards:spy` | Spy | `component.action` · action | base | Choose 1 player. That player gives you 1 random action card from their hand. |
| `action_cards:strategize1` | Strategize | `component.action` · action | thunders_edge | Perform the secondary ability of any readied or unchosen strategy card. |
| `action_cards:strategize2` | Strategize | `component.action` · action | thunders_edge | Perform the secondary ability of any readied or unchosen strategy card. |
| `action_cards:strategize3` | Strategize | `component.action` · action | thunders_edge | Perform the secondary ability of any readied or unchosen strategy card. |
| `action_cards:strategize4` | Strategize | `component.action` · action | thunders_edge | Perform the secondary ability of any readied or unchosen strategy card. |
| `action_cards:tactical` | Tactical Bombardment | `component.action` · action | base | Choose 1 system that contains 1 or more of your units that have BOMBARDMENT. Exhaust each planet controlled b… |
| `action_cards:unexpected` | Unexpected Action | `component.action` · action | base | Remove 1 of your command tokens from the game board and return it to your reinforcements. |
| `action_cards:unstable` | Unstable Planet | `component.action` · action | base | Choose 1 hazardous planet. Exhaust that planet and destroy up to 3 infantry on it. |
| `action_cards:uprising` | Uprising | `component.action` · action | base | Exhaust 1 non-home planet controlled by another player. Then gain trade goods equal to its resource value. |
| `action_cards:war_effort` | War Effort | `component.action` · action | base | Place 1 cruiser from your reinforcements in a system that contains 1 or more of your ships. |

### `invasion` (3)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:blitz` | Blitz | `invasion` · start | codex1 | Each of your non-fighter ships in the active system that do not have BOMBARDMENT gain BOMBARDMENT 6 until the… |
| `action_cards:bunker` | Bunker | `invasion` · start | base | During this invasion, apply -4 to the result of each BOMBARDMENT roll against planets you control. |
| `action_cards:disable` | Disable | `invasion` · start | base | Your opponents' PDS units lose PLANETARY SHIELD and SPACE CANNON during this invasion. |

### `phase` (3)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:abs` | Ancient Burial Sites | `phase` · start [phase=agenda] | base | Choose 1 player. Exhaust each cultural planet owned by that player. |
| `action_cards:investments` | Manipulate Investments | `phase` · start [phase=strategy] | pok | Place a total of 5 trade goods from the supply on strategy cards of your choice; you must place these tokens … |
| `action_cards:summit` | Summit | `phase` · start [phase=strategy] | base | Gain 2 command tokens. |

### `planet.control_gained` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:infiltrate` | Infiltrate | `planet.control_gained` · when | base | Replace each PDS and space dock that is on that planet with a matching unit from your reinforcements. |
| `action_cards:reparations` | Reparations | `planet.control_gained` · after | base | Exhaust 1 planet that player controls and ready 1 planet you control. |

### `production.used` (5)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:war_machine1` | War Machine | `production.used` · when | codex1 | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |
| `action_cards:war_machine2` | War Machine | `production.used` · when | codex1 | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |
| `action_cards:war_machine3` | War Machine | `production.used` · when | codex1 | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |
| `action_cards:war_machine4` | War Machine | `production.used` · when | codex1 | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |
| `action_cards:war_machinell` | War Machine | `production.used` · when | codex1 | Apply +4 to the total PRODUCTION value of your units and reduce the combined cost of the produced units by 1. |

### `strategy.action` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:coup` | Coup d'Etat | `strategy.action` · when [would] | pok | End that player's turn; the strategic action is not resolved and the strategy card is not exhausted. |

### `strategy.card_chosen` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:disgrace` | Public Disgrace | `strategy.card_chosen` · when | base | That player must choose a different strategy card instead, if able. |

### `strategy.cards_returned` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:stability` | Political Stability | `strategy.cards_returned` · when [would] | base | Do not return your strategy card(s). You do not choose strategy cards during the next strategy phase. |

### `tactical.ships_moved` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:experimental` | Experimental Battlestation | `tactical.ships_moved` · after | base | Choose 1 of your space docks that is either in or adjacent to that system. That space dock uses SPACE CANNON … |
| `action_cards:rescue` | Rescue | `tactical.ships_moved` · after | thunders_edge | You may move 1 of your ships into the active system from any system that does not contain one of your command… |

### `tactical.system_activated` (14)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:counterstroke` | Counterstroke | `tactical.system_activated` · after | codex1 | Return that command token to your tactic pool. |
| `action_cards:decoy` | Decoy Operation | `tactical.system_activated` · after | pok | Remove up to 2 of your ground forces from the game board and place them on a planet you control in the active… |
| `action_cards:fs1` | Flank Speed | `tactical.system_activated` · after | base | Apply +1 to the move value of each of your ships during this tactical action. |
| `action_cards:fs2` | Flank Speed | `tactical.system_activated` · after | base | Apply +1 to the move value of each of your ships during this tactical action. |
| `action_cards:fs3` | Flank Speed | `tactical.system_activated` · after | base | Apply +1 to the move value of each of your ships during this tactical action. |
| `action_cards:fs4` | Flank Speed | `tactical.system_activated` · after | base | Apply +1 to the move value of each of your ships during this tactical action. |
| `action_cards:fsb` | Forward Supply Base | `tactical.system_activated` · after | codex1 | Gain 3 trade goods. Then, choose another player to gain 1 trade good. |
| `action_cards:harness` | Harness Energy | `tactical.system_activated` · after | codex1 | Replenish your commodities. |
| `action_cards:lost_star` | Lost Star Chart | `tactical.system_activated` · after | base | During this tactical action, systems that contain alpha and beta wormholes are adjacent to each other. |
| `action_cards:nav_suite` | Nav Suite | `tactical.system_activated` · after | pok | During the "Movement" step of this tactical action, ignore the effect of anomalies. |
| `action_cards:rally` | Rally | `tactical.system_activated` · after | codex1 | Place 2 command tokens from your reinforcements in your fleet pool. |
| `action_cards:silence_space` | In The Silence Of Space | `tactical.system_activated` · after | base | Choose 1 system. During this tactical action, your ships in the chosen system can move through systems that c… |
| `action_cards:solar_flare` | Solar Flare | `tactical.system_activated` · after | codex1 | During the "Movement" step of this tactical action, other players cannot use SPACE CANNON against your ships. |
| `action_cards:upgrade` | Upgrade | `tactical.system_activated` · after | base | Replace 1 of your cruisers in that system with 1 dreadnought from your reinforcements. |

### `tactical.units_committed` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:ghost_squad` | Ghost Squad | `tactical.units_committed` · after | codex1 | Move any number of ground forces from any planet you control in the active system to any other planet you con… |
| `action_cards:parley` | Parley | `tactical.units_committed` · after | base | Return the committed units to the space area. |

### `transaction` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:blackmarketdealing` | Black Market Dealings | `transaction` · when | thunders_edge | You and the other player can include relics, action cards, and unscored secret objectives as part of the tran… |
| `action_cards:lieinwait` | Lie in Wait | `transaction` · after | thunders_edge | Look at each of those players' hands of action cards, then choose and take 1 action card from each. |

### `turn` (3)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:crisis` | Crisis | `turn` · end | thunders_edge | Skip the next player's turn. |
| `action_cards:extremeduress` | Extreme Duress | `turn` · start | thunders_edge | If that player's next action is not a strategic action, they discard all of their action cards, give you all … |
| `action_cards:puppetsonastring` | Puppets on a String | `turn` · end | thunders_edge | Perform 1 action. |

### `unit.ability_used` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:scramble` | Scramble Frequency | `unit.ability_used` · after [ability=afb] | codex1 | That player rerolls all of their dice. |

### `unit.destroyed` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:courageous` | Courageous to the End | `unit.destroyed` · after | base | Roll 2 dice. For each result equal to or greater than that ship's combat value, your opponent must choose and… |
| `action_cards:crashlanding` | Crash Landing | `unit.destroyed` · when | thunders_edge | Place 1 of your ground forces from the space area of the active system onto a planet in that system other tha… |

### `unit.sustain_damage` (5)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `action_cards:dh1` | Direct Hit | `unit.sustain_damage` · after | base | Destroy that ship. |
| `action_cards:dh2` | Direct Hit | `unit.sustain_damage` · after | base | Destroy that ship. |
| `action_cards:dh3` | Direct Hit | `unit.sustain_damage` · after | base | Destroy that ship. |
| `action_cards:dh4` | Direct Hit | `unit.sustain_damage` · after | base | Destroy that ship. |
| `action_cards:reflective` | Reflective Shielding | `unit.sustain_damage` · when | codex1 | Produce 2 hits against your opponent's ships in the active system. |

## 8. Relikty, notki, eksploracja i wydarzenia wg zdarzenia

### `(efekt ciągły)` (74)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:lightrailordnance` | Lightrail Ordnance | — | thunders_edge | Your space docks gain SPACE CANNON 5 (x2). You may use your space dock's SPACE CANNON against ships that are … |
| `relics:thesilverflame` | The Silver Flame | — | thunders_edge | The Silver Flame may be exchanged as part of a transaction. > ACTION: Roll 1 die and purge this card; if the … |
| `relics:thetriad` | The Triad | — | thunders_edge | This card can be readied and spent as if it were a planet card. Its resource and influence values are equal t… |
| `explores:aw1` | Abandoned Warehouses | — | pok | You may gain 2 commodities, or you may convert up to 2 of your commodities to trade goods. |
| `explores:aw2` | Abandoned Warehouses | — | pok | You may gain 2 commodities, or you may convert up to 2 of your commodities to trade goods. |
| `explores:aw3` | Abandoned Warehouses | — | pok | You may gain 2 commodities, or you may convert up to 2 of your commodities to trade goods. |
| `explores:aw4` | Abandoned Warehouses | — | pok | You may gain 2 commodities, or you may convert up to 2 of your commodities to trade goods. |
| `explores:biotic` | Biotic Research Facility | — | pok | This planet has a green technology specialty; if this planet already has a technology specialty, this planet'… |
| `explores:cm1` | Core Mine | — | pok | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 trade good. |
| `explores:cm2` | Core Mine | — | pok | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 trade good. |
| `explores:cm3` | Core Mine | — | pok | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 trade good. |
| `explores:cybernetic` | Cybernetic Research Facility | — | pok | This planet has a yellow technology specialty; if this planet already has a technology specialty, this planet… |
| `explores:ds` | Dyson Sphere | — | pok | This planet's resource value is increased by 2 and its influence value is increased by 1. |
| `explores:dv1` | Derelict Vessel | — | pok | Draw 1 secret objective. |
| `explores:dv2` | Derelict Vessel | — | pok | Draw 1 secret objective. |
| `explores:dw` | Dead World | — | codex3 | Draw 1 relic. |
| `explores:ent` | Entropic Field | — | codex3 | Gain 1 command token and 2 trade goods. |
| `explores:exp1` | Expedition | — | pok | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, ready this planet. |
| `explores:exp2` | Expedition | — | pok | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, ready this planet. |
| `explores:exp3` | Expedition | — | pok | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, ready this planet. |
| `explores:fb1` | Functioning Base | — | pok | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to draw 1 action card. |
| `explores:fb2` | Functioning Base | — | pok | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to draw 1 action card. |
| `explores:fb3` | Functioning Base | — | pok | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to draw 1 action card. |
| `explores:fb4` | Functioning Base | — | pok | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to draw 1 action card. |
| `explores:frln1` | Freelancers | — | pok | You may produce 1 unit in this system; you may spend influence as if it were resources to produce this unit. |
| `explores:frln2` | Freelancers | — | pok | You may produce 1 unit in this system; you may spend influence as if it were resources to produce this unit. |
| `explores:frln3` | Freelancers | — | pok | You may produce 1 unit in this system; you may spend influence as if it were resources to produce this unit. |
| `explores:gamma` | Gamma Relay | — | pok | Place a gamma wormhole token in this system. Then, purge this card. |
| `explores:gw` | Gamma Wormhole | — | pok | Place a gamma wormhole token in this system. Then, purge this card. |
| `explores:kel1` | Keleres Ship | — | codex3 | Gain 2 command tokens. |
| `explores:kel2` | Keleres Ship | — | codex3 | Gain 2 command tokens. |
| `explores:lc1` | Lost Crew | — | pok | Draw 2 action cards. |
| `explores:lc2` | Lost Crew | — | pok | Draw 2 action cards. |
| `explores:lf1` | Local Fabricators | — | pok | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to place 1 mech from your reinforcemen… |
| `explores:lf2` | Local Fabricators | — | pok | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to place 1 mech from your reinforcemen… |
| `explores:lf3` | Local Fabricators | — | pok | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to place 1 mech from your reinforcemen… |
| `explores:lf4` | Local Fabricators | — | pok | You may gain 1 commodity, or you may spend 1 trade good or 1 commodity to place 1 mech from your reinforcemen… |
| `explores:ls` | Lazax Survivors | — | pok | This planet's resource value is increased by 1 and its influence value is increased by 2. |
| `explores:majent` | Major Entropic Field | — | codex3 | Gain 1 command token and 3 trade goods. |
| `explores:minent` | Minor Entropic Field | — | codex3 | Gain 1 command token and 1 trade good. |
| `explores:mirage` | Mirage | — | pok | Place the Mirage planet token in this system. Gain the Mirage planet card and ready it. Then, purge this card. |
| `explores:mo1` | Mercenary Outfit | — | pok | You may place 1 infantry from your reinforcements on this planet. |
| `explores:mo2` | Mercenary Outfit | — | pok | You may place 1 infantry from your reinforcements on this planet. |
| `explores:mo3` | Mercenary Outfit | — | pok | You may place 1 infantry from your reinforcements on this planet. |
| `explores:ms1` | Merchant Station | — | pok | You may replenish your commodities, or you may convert your commodities to trade goods. |
| `explores:ms2` | Merchant Station | — | pok | You may replenish your commodities, or you may convert your commodities to trade goods. |
| `explores:mw` | Mining World | — | pok | This planet's resource value is increased by 2. |
| `explores:propulsion` | Propulsion Research Facility | — | pok | This planet has a blue technology specialty; if this planet already has a technology specialty, this planet's… |
| `explores:pw` | Paradise World | — | pok | This planet's influence value is increased by 2. |
| `explores:rw` | Rich World | — | pok | This planet's resource value is increased by 1. |
| `explores:toe` | Tomb of Emphidia | — | pok | This planet's influence value is increased by 1. If the player who has the "Crown of Emphidia" relic has cont… |
| `explores:urf1` | Unknown Relic Fragment | — | pok | The card counts as a relic fragment of any type. |
| `explores:urf2` | Unknown Relic Fragment | — | pok | The card counts as a relic fragment of any type. |
| `explores:urf3` | Unknown Relic Fragment | — | pok | The card counts as a relic fragment of any type. |
| `explores:vfs1` | Volatile Fuel Source | — | pok | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 command toke… |
| `explores:vfs2` | Volatile Fuel Source | — | pok | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 command toke… |
| `explores:vfs3` | Volatile Fuel Source | — | pok | If you have at least 1 mech on this planet, or if you remove 1 infantry from this planet, gain 1 command toke… |
| `explores:warfare` | Warfare Research Facility | — | pok | This planet has a red technology specialty; if this planet already has a technology specialty, this planet's … |
| `galactic_events:advent_war_sun` | Advent of the War Sun | — | thunders_edge | - At the end of setup, all players other than the Embers of Muaat player gain the War Sun unit upgrade techno… |
| `galactic_events:age_exploration` | Age of Exploration | — | thunders_edge | - Relics require only 2 matching fragments be purged instead of 3. - The Naaz-Rokha Alliance's ***Fabrication… |
| `galactic_events:age_fighters` | Age of Fighters | — | thunders_edge | - During setup, all players gain the Fighter II unit upgrade technology; the Naalu Collective player gains Hy… |
| `galactic_events:civilized_society` | Civilized Society | — | thunders_edge | - During setup, turn all public objectives faceup. - There is no limit to the number of public objectives a p… |
| `galactic_events:cosmic_phenomenae` | Cosmic Phenomenae | — | thunders_edge | Anomalies are adjusted as follows: > - ***Nebulae:*** The defender applies +3 to each of their ship's combat … |
| `galactic_events:cowabunga` | Conventions of War Abandoned | — | thunders_edge | - Each hit produced by ***BOMBARDMENT*** rolls destroys 3 units instead of 1. - Players that have the ***X-89… |
| `galactic_events:cultural_exchange` | Cultural Exchange Program | — | thunders_edge | - At the end of setup, shuffle the reference cards that correspond to each faction in play. Each player draws… |
| `galactic_events:dangerous_wilds` | Dangerous Wilds | — | thunders_edge | - During setup, place neutral infantry on each hazardous planet equal to that planet's resource value. - At t… |
| `galactic_events:mercenaries` | Mercenaries for Hire | — | thunders_edge | - At the start of the game, shuffle the alliance cards that correspond to the factions not in play and place … |
| `galactic_events:mobilization` | Rapid Mobilization | — | thunders_edge | - After setup, put The Fracture into play. Then, each player simultaneously resolves the following effects in… |
| `galactic_events:monuments_ages` | Monuments to the Ages | — | thunders_edge | - When you would place a structure on a non-home planet, you may spend 5 trade goods to place a neutral space… |
| `galactic_events:stellar_atomics` | Stellar Atomics | — | thunders_edge | - During setup, each player places one of their control tokens on this card. - All players can perform the fo… |
| `galactic_events:total_war` | Total War | — | thunders_edge | - When a player destroys or produces hits that destroy another player's units, they place commodities from th… |
| `galactic_events:weird_wormholes` | Weird Wormholes | — | thunders_edge | - After a ship moves using at least 1 alpha, beta, or gamma wormhole, roll 1 die and consult the following li… |
| `galactic_events:wild_wild_galaxy` | Wild, Wild Galaxy | — | thunders_edge | Action cards are adjusted as follows: > - Direct Hit: Can be used against mechs > - Flank Speed: Applies +2 M… |
| `galactic_events:zealous_orthodoxy` | Zealous Orthodoxy | — | thunders_edge | - The first player to score 2 secret objectives gains 1 victory point. - Then, place that faction's alliance … |

### `agenda.revealed` (6)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `promissory_notes:<color>_ps` | Political Secret | `agenda.revealed` · when | base | When an agenda is revealed: The <color> player cannot vote, play action cards, or use faction abilities until… |
| `promissory_notes:favor` | Political Favor | `agenda.revealed` · when | base | When an agenda is revealed: Remove 1 token from the Xxcha player's strategy pool and return it to their reinf… |
| `promissory_notes:rider` | Keleres Rider | `agenda.revealed` · after | codex3 | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:ridera` | Keleres Rider | `agenda.revealed` · after | codex3 | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:riderm` | Keleres Rider | `agenda.revealed` · after | codex3 | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |
| `promissory_notes:riderx` | Keleres Rider | `agenda.revealed` · after | codex3 | After an agenda is revealed: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your… |

### `agenda.votes_cast` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `galactic_events:hidden_agenda` | Hidden Agenda | `agenda.votes_cast` · after [scope=all] | thunders_edge | - During the agenda phase, only the speaker can talk; all other players must remain silent except when declar… |

### `combat` (5)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `promissory_notes:antivirus` | Antivirus | `combat` · start | base | At the start of a combat: Place this card faceup in your play area. While this card is in your play area, the… |
| `promissory_notes:cavalry` | The Cavalry | `combat` · start | pok | At the start of a space combat against a player other than the Nomad: During this combat, treat 1 of your non… |
| `promissory_notes:greyfire` | Greyfire Mutagen | `combat` · start | base | At the start of a ground combat against 2 or more ground forces that are not controlled by the Yin player: Re… |
| `promissory_notes:raisethestandard` | Raise the Standard | `combat` · end | thunders_edge | At the end of a combat: Galvanize 1 of your units that participated. Then, return this card to the Last Basti… |
| `promissory_notes:tekklar` | Tekklar Legion | `combat` · start | base | At the start of an invasion combat: Apply +1 to the result of each of your unit's combat rolls during this co… |

### `combat.hits_produced` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:metalivoidshielding` | Metali Void Shielding | `combat.hits_produced` · when | thunders_edge | Each time hits are produced against 1 or more of your non-fighter ships, 1 of those ships may use SUSTAIN DAM… |

### `combat.roll` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:heartofixth` | Heart of Ixth | `combat.roll` · after | thunders_edge | After any die is rolled, you may exhaust this card to add or subtract 1 from its result. |
| `promissory_notes:war_funding` | War Funding | `combat.roll` · after | base | After you and your opponent roll dice during space combat: You may reroll all of your opponent's dice. You ma… |

### `combat.round` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:thalnos` | The Crown of Thalnos | `combat.round` · during | pok | During each combat round, this card's owner may reroll any number of their dice, applying +1 to the results; … |

### `combat.step` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:metalivoidarmaments` | Metali Void Armaments | `combat.step` · during [step=anti_fighter_barrage] | thunders_edge | During the "Anti-Fighter Barrage" step of space combat, you may resolve ANTI-FIGHTER BARRAGE 6 (x3) against y… |

### `component.action` (39)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:circletofthevoid` | Circlet of the Void | `component.action` · action | codex4 | Your units do not roll for gravity rifts, and you ignore the movement effects of other anomalies. ACTION: Exh… |
| `relics:codex` | The Codex | `component.action` · action | pok | ACTION: Purge this card to take up to 3 action cards of your choice from the action card discard pile. |
| `relics:dynamiscore` | Dynamis Core | `component.action` · action | codex2 | While this card is in your play area, your commodity value is increased by 2. ACTION: Gain trade goods equal … |
| `relics:enigmaticdevice` | Enigmatic Device | `component.action` · action | pok | Place this card faceup in your play area. ACTION: You may spend 6 resources and purge this card to research 1… |
| `relics:nanoforge` | Nano-Forge | `component.action` · action | codex2 | ACTION: Attach this card to a non-legendary, non-home planet you control; its resource and influence values a… |
| `relics:stellarconverter` | Stellar Converter | `component.action` · action | pok | ACTION: Choose 1 non-home, non-legendary planet other than Mecatol Rex in a system that is adjacent to 1 or m… |
| `relics:titanprototype` | JR-XS455-O | `component.action` · action | codex2 | ACTION: Exhaust this agent and choose a player; that player may spend 3 resources to place a structure on a p… |
| `promissory_notes:blood_pact` | Blood Pact | `component.action` · action | pok | ACTION: Place this card faceup in your play area. When you and the Empyrean player cast votes for the same ou… |
| `promissory_notes:bmf` | Black Market Forgery | `component.action` · action | pok | ACTION: Purge 2 of your relic fragments of the same type to gain 1 relic. Then, return this card to the Naaz-… |
| `promissory_notes:convoys` | Trade Convoys | `component.action` · action | base | ACTION: Place this card faceup in your play area. While this card is in your play area, you may negotiate tra… |
| `promissory_notes:dark_pact` | Dark Pact | `component.action` · action | pok | ACTION: Place this card faceup in your play area. When you give a number of commodities to the Empyrean playe… |
| `promissory_notes:fires` | Fires of the Gashlai | `component.action` · action | base | ACTION: Remove 1 token from the Muaat player's fleet pool and return it to their reinforcements. Then, gain y… |
| `promissory_notes:pop` | Promise of Protection | `component.action` · action | base | ACTION: Place this card faceup in your play area. While this card is in your play area, the Mentak player can… |
| `promissory_notes:sever` | Sever | `component.action` · action | thunders_edge | ACTION: Place this card faceup in your play area and place the sever token in a system that contains your uni… |
| `promissory_notes:shareknowledge` | Share Knowledge | `component.action` · action | thunders_edge | ACTION: Place this card faceup in your play area and gain 1 non-faction, non-unit upgrade technology that the… |
| `promissory_notes:terraform` | Terraform | `component.action` · action | pok | ACTION: Attach this card to a non-home planet you control other than Mecatol Rex. Its resource and influence … |
| `explores:crf1` | Cultural Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `explores:crf2` | Cultural Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `explores:crf3` | Cultural Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `explores:crf4` | Cultural Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `explores:crf5` | Cultural Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `explores:crf6` | Cultural Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `explores:crf7` | Cultural Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `explores:crf8` | Cultural Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `explores:crf9` | Cultural Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your cultural relic fragments to gain 1 relic. |
| `explores:ed1` | Enigmatic Device | `component.action` · action | pok | Place this card faceup in your play area. ACTION: You may spend 6 resource and purge this card to research 1 … |
| `explores:ed2` | Enigmatic Device | `component.action` · action | pok | Place this card faceup in your play area. ACTION: You may spend 6 resource and purge this card to research 1 … |
| `explores:hrf1` | Hazardous Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `explores:hrf2` | Hazardous Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `explores:hrf3` | Hazardous Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `explores:hrf4` | Hazardous Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `explores:hrf5` | Hazardous Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `explores:hrf6` | Hazardous Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `explores:hrf7` | Hazardous Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your hazardous relic fragments to gain 1 relic. |
| `explores:irf1` | Industrial Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |
| `explores:irf2` | Industrial Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |
| `explores:irf3` | Industrial Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |
| `explores:irf4` | Industrial Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |
| `explores:irf5` | Industrial Relic Fragment | `component.action` · action | pok | ACTION: Purge 3 of your industrial relic fragments to gain 1 relic. |

### `component.gained` (7)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:bookoflatvinia` | Book of Latvinia | `component.gained` · when | codex4 | When you gain this card, research up to 2 technologies that have no prerequisites. > ACTION: Purge this card;… |
| `relics:obsidian` | The Obsidian | `component.gained` · when | pok | When you gain this card, draw 1 secret objective. You can have 1 additional scored or unscored secret objecti… |
| `relics:quantumcore` | The Quantumcore | `component.gained` · when | thunders_edge | When you gain this card, gain your breakthrough. You have SYNERGY for all technology types. |
| `relics:shard` | Shard of the Throne | `component.gained` · when | pok | When you gain this card, gain 1 victory point; when you lose this card, lose 1 victory point. When a player g… |
| `promissory_notes:<color>_an` | Alliance | `component.gained` · when | pok | When you receive this card, if you are not the <color> player, you must place it faceup in your play area. Wh… |
| `promissory_notes:<color>_sftt` | Support for the Throne | `component.gained` · when | base | When you receive this card, if you are not the <color> player, you must place it faceup in your play area and… |
| `promissory_notes:blackops` | Black Ops | `component.gained` · when | thunders_edge | When you receive this card, if you are not the Firmament: The Firmament may place 1 facedown plot card in the… |

### `economy.commodities_replenished` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `promissory_notes:<color>_ta` | Trade Agreement | `economy.commodities_replenished` · when | base | When the <color> player replenishes commodities: The <color> player gives you all of their commodities. Then,… |
| `galactic_events:age_commerce` | Age of Commerce | `economy.commodities_replenished` · when | thunders_edge | - Players do not have to be neighbors to perform transactions with each other. - Players do not have a maximu… |

### `game.setup` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `galactic_events:minor_factions` | Minor Factions | `game.setup` · before | thunders_edge | - During setup, players are dealt 1 fewer blue tile. Before creating the galaxy, shuffle the reference cards … |

### `objective.revealed` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:neuraloop` | Neuraloop | `objective.revealed` · when | codex4 | When a public objective is revealed, you may purge one of your relics to discard that objective and replace i… |

### `phase` (4)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:mawofworlds` | Maw of Worlds | `phase` · start [phase=agenda] | pok | At the start of the agenda phase, you may purge this card and exhaust all of your planets to gain any 1 techn… |
| `promissory_notes:gift` | Gift of Prescience | `phase` · end [phase=strategy] | base | At the end of the Strategy Phase: Place this card faceup in your play area and place the Naalu '0' token on y… |
| `promissory_notes:scepter` | Scepter of Dominion | `phase` · start [phase=strategy] | pok | At the start of the strategy phase: Choose 1 non-home system that contains your units; each other player who … |
| `explores:dmz` | Demilitarized Zone | `phase` · during [phase=agenda] | pok | Return all structures on this planet to your reinforcements. Then, return all ground forces on this planet to… |

### `status.step` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `promissory_notes:ce` | Cybernetic Enhancements | `status.step` · when [step=gain_command_tokens] | base | When you gain command tokens during the status phase: Gain 1 additional command token. Then, return this card… |

### `strategy.action` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `promissory_notes:acq` | Acquiescence | `strategy.action` · when | base | When the Winnu player resolves a strategic action: You do not have to spend or place a command token to resol… |

### `strategy.token_spent` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:emelpar` | Scepter of Emelpar | `strategy.token_spent` · when [would] | pok | When you would spend a token from your strategy pool, you may exhaust this card to spend a token from your re… |

### `tactical.action` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:emphidia` | The Crown of Emphidia | `tactical.action` · after | pok | After you perform a tactical action, you may exhaust this card to explore 1 planet you control. At the end of… |
| `promissory_notes:malevolency` | Malevolency | `tactical.action` · end | thunders_edge | At the end of one of your tactical actions: Spend 1 influence to give this card to one of your neighbors; you… |

### `tactical.ships_moved` (4)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:dominusorb` | Dominus Orb | `tactical.ships_moved` · before | pok | Before you move units during a tactical action, you may purge this card to move and transport units that are … |
| `promissory_notes:stymie` | Stymie | `tactical.ships_moved` · after | base | After another player moves ships into a system that contains 1 or more of your units: You may place 1 command… |
| `explores:ion` | Ion Storm | `tactical.ships_moved` · end | pok | Place the ion storm token in this system with either side faceup. Then, place this card in the common play ar… |
| `galactic_events:call_of_the_void` | Call of the Void | `tactical.ships_moved` · after | thunders_edge | After you move 1 or more units into the active system, if that system is in The Fracture, gain 1 command toke… |

### `tactical.system_activated` (3)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `promissory_notes:<color>_cf` | Ceasefire | `tactical.system_activated` · after | base | After the <color> player activates a system that contains 1 or more of your units: The <color> player cannot … |
| `promissory_notes:crucible` | Crucible | `tactical.system_activated` · after | pok | After you activate a system: Your ships do not roll for gravity rifts during this movement; apply an addition… |
| `promissory_notes:nanolink` | Nano-Link Permit | `tactical.system_activated` · after | thunders_edge | After you activate a system: You may move your structures from adjacent systems that do not contain your comm… |

### `tactical.units_committed` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `promissory_notes:ragh` | Ragh's Call | `tactical.units_committed` · after | base | After you commit 1 or more units to land on a planet: Remove all of the Saar player's ground forces from that… |

### `technology.research` (2)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `relics:prophetstears` | The Prophet's Tears | `technology.research` · when | pok | When you research a technology, you may exhaust this card to ignore 1 prerequisite or draw 1 action card. |
| `promissory_notes:ra` | Research Agreement | `technology.research` · after | base | After the Jol-Nar player researches a technology that is not a faction technology: Gain that technology. Then… |

### `turn` (3)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `promissory_notes:iff` | Creuss Iff | `turn` · start | base | At the start of your turn during the action phase: Place or move a Creuss wormhole token into either a system… |
| `promissory_notes:ms` | Military Support | `turn` · start | base | At the start of the Sol player's turn: Remove 1 token from the Sol player's strategy pool, if able, and retur… |
| `promissory_notes:spynet` | Spy Net | `turn` · start | base | At the start of your turn: Look at the Yssaril player's hand of action cards. Choose 1 of those cards and add… |

### `unit.ability_used` (1)

| Komponent | Nazwa | Okno | Źródło | Tekst |
|---|---|---|---|---|
| `promissory_notes:ambuscade` | Strike Wing Ambuscade | `unit.ability_used` · when [ability=roll] | pok | When 1 or more of your units make a roll for a unit ability: Choose 1 of those units to roll 1 additional die… |

## 9. Przypadki szczególne (bez przypisanego zdarzenia)

* pole okna bez dopasowania: **0**
* klauzule w tekście bez dopasowania: **3**

### Pola okna bez dopasowania

| Komponent | Nazwa | Fraza okna |
|---|---|---|

### Klauzule w tekście bez dopasowania

| Komponent | Nazwa | Klauzula |
|---|---|---|
| `action_cards:hack` | Hack Election | During this agenda, you vote last |
| `breakthroughs:titansbt` | Slumberstate Computing | When COALESCENCE results in a ground combat, if you commit no other units, you may choose for your units to c… |
| `breakthroughs:yssarilbt` | Deepgloom Executable | when you do, you may resolve a transaction with that player |
