1# Plan: pełna rozgrywka Twilight Imperium na stronie

Cel końcowy (ustalony z użytkownikiem): **możliwość rozegrania pełnej partii TI4 w aplikacji**
— nie tylko odwzorowanie stanu (God-Mode), ale realne fazy, akcje, walka, agenda, punktacja.

## Ustalenie bazowe (dowodowe)

- **Frontend `ti4_web` NIE ma logiki akcji.** To viewer: jedyne POST-y to nasze dodatki
  (`useNewGame`, `useBoardEditor`); oryginał deleguje akcje do Discorda przez
  `actionsJumpLink`/`tableTalkJumpLink`. Potwierdzone grepem (brak `useMutation`, brak
  POST do bota poza naszymi).
- **Logika gry jest w Java bocie** (`TI4_map_generator_bot/src/main/java/ti4/service/`):
  `turn/`, `strategycard/`, `tactical/`, `combat/`, `agenda/`, `status` (StatusCleanupService),
  `objectives/`, `leader/`, `tech/`, `explore/`, `transaction/`, `commodities/`, `planet/`,
  `relic/`, `abilities/`. Spleciona z Discordem (JDA buttony) — używamy jako ŹRÓDŁO REGUŁ.
- **Reużywalne z frontu:** komponenty wyświetlania/wyboru w `src/domains/cards/components/`
  (StrategyCardDetailsCard, StrategyCardSheet, TechCard, LeaderDetailsCard, PlanetDetailsCard,
  ObjectiveDetailsCard, UnitDetailsCard…), panele graczy/mapy, builder battle-calc.

## Zasada

Każda reguła → najpierw do `docs/RULES.md` ze źródłem (Java bot / LRR), potem implementacja
w Pythonie. Dane liczbowe wyłącznie z assetów przez `StaticDataRegistry`. Każdy krok:
kod + testy + QA + commit; grywalny przyrostowo.

## Etapy (kolejność jak pakiety Javy)

### E1 — Maszyna faz + kolejność tur (fundament)  ⬅ START
Źródło: `service/turn/` (StartTurn/EndTurn/Pass), `service/game/` (round).
- Model: `Phase` już jest; dodać przejścia faz i kolejność inicjatywy (z `scs`).
- Endpointy: `POST /phase/next`, `POST /turn/end`, `POST /turn/pass`, `POST /round/next`.
- Reguła: kolejność tur wg inicjatywy kart strategii; pas = gracz pomijany do końca rundy;
  koniec rundy gdy wszyscy spasowali → faza statusu.
- UI: panel faz (jest) + przyciski „Zakończ turę / Pas / Następna faza" w stylu strony.
- DoD: można przeklikać Strategia → Akcja (tury wg inicjatywy) → Status → Agenda → runda+1.

### E2 — Faza strategii (wybór kart strategii)
Źródło: `service/strategycard/` (PickStrategyCard, PlayStrategyCard, secondary/follow).
- Model: pula 8 kart strategii (SpeakerOrder), wybór per gracz (`strategy_cards`), exhausted.
- Endpointy: `POST /strategy/pick`, `POST /strategy/play`, `POST /strategy/follow`.
- Reguła: inicjatywa z numeru karty; primary/secondary; trade goods na niewybranych kartach.
- UI: wybór karty (komponenty SC z frontu), oznaczenie zagranej/wyczerpanej.
- DoD: faza strategii rozdaje karty, ustala inicjatywę dla fazy akcji.

### E3 — Akcja taktyczna (aktywacja → ruch → walka kosmiczna → inwazja → produkcja) ✅ GOTOWY
Źródło: `service/tactical/` (TacticalAction* + movement/planet/postmovement), `service/combat/`.
- **Decyzja projektowa (ustalona z użytkownikiem):** silnik to ASYSTENT STOŁU, nie sędzia —
  prowadzi przez kroki i daje pomoce liczbowe, ale NIE waliduje reguł (gracze grają fizycznie
  i wprowadzają wynik; ruch = istniejący God-Mode; walka = okno z ręcznym wpisywaniem trafień,
  zero rzucania). Zrealizowane w blokach T1–T4 (patrz PROGRESS.md), reguły RULES.md 19–22.
- Krokowa maszyna (TacticalStep FSM): ACTIVATION → MOVEMENT → SPACE_CANNON → SPACE_COMBAT →
  INVASION → PRODUCTION. Aktywacja kładzie żeton dowodzenia (pula taktyczna), `active_system`.
- Walka (kosmiczna/naziemna): okno-asystent z pomocami (kości, trafia na X+, expected hits
  z UnitDef); odejmowanie zniszczonych przez God-Mode. Inwazja: przejęcie kontroli planety.
  Produkcja: pomoc kosztu (UnitDef.cost + dostępne zasoby). Space cannon: krok FSM bez okna.
- DoD: ✅ pełna sekwencja przeklikalna krok po kroku (aktywacja → ruch → walka → przejęcie
  planety → produkcja → zakończenie akcji).

### E4 — Akcje komponentowe + strategiczne secondary
Źródło: `service/actioncard/`, `service/leader/`, `service/tech/`, `service/explore/`.
- Zagranie karty akcji, agent/hero, badanie technologii, eksploracja planet/frontier.
- UI: przyciski „Zagraj kartę / Aktywuj lidera / Zbadaj tech" (karty z frontu jako pickery).

### E5 — Faza statusu (punktacja + sprzątanie)
Źródło: `StatusCleanupService`, `service/objectives/`.
- Punktowanie celów publicznych/sekretnych (ewaluator — M3 roadmapy), custodian.
- Sprzątanie: odświeżenie kart/planet, zwrot żetonów, nowa runda.
- UI: panel celów (komponenty z frontu) + scoring.

### E6 — Faza agendy
Źródło: `service/agenda/`.
- Odkrycie agend, głosowanie (wpływy z planet), rozstrzygnięcie, prawa w grze.
- UI: panel agendy (jest w GameStatePanel) + głosowanie.

### E7 — Asymetria frakcyjna + end-game
Źródło: `service/abilities/`, dane `assets/data/abilities/*.json`, `rules_hooks` (spec), VP do zwycięstwa.
- Zdolności frakcji (hooki na ruch/walkę/produkcję), warunek wygranej (10 VP).
- Pełna lista frakcji i ich gimmicków do okodowania: patrz sekcja „Frakcje" niżej.

---

## Frakcje — zakres i gimmicki do okodowania (E7, po silniku bazowym)

Aktywne źródła: **base + pok + codex3 (Keleres) + thunders_edge**. Łącznie 30 frakcji
grywalnych (Keleres = 3 warianty startowe; Firmament/Obsidian = 2 osobne frakcje; plus
`neutral` jako pseudo-frakcja systemowa). **Zdolności czytane z danych** (`abilities` we
`FactionDef` → opisy w `assets/data/abilities/`), nigdy z pamięci.

> Jak to kodujemy (plan, nie teraz): każda zdolność to **hook** w odpowiednim oknie
> silnika (setup / ruch / walka / produkcja / status / agenda). Dopóki hook nie istnieje,
> zdolność jest „martwa" (frakcja gra jak generyczna). Implementujemy je PO ukończeniu
> silnika bazowego (E1–E6), frakcja po frakcji, każda z wpisem w `RULES.md` i testem.

### Base (17 frakcji)
| Frakcja | alias | Zdolności (gimmicki z danych) |
|---|---|---|
| The Arborec | `arborec` | Mitosis |
| The Barony of Letnev | `letnev` | Munitions Reserves, Armada |
| The Clan of Saar | `saar` | Scavenge, Nomadic |
| The Embers of Muaat | `muaat` | Star Forge, Gashlai Physiology |
| The Emirates of Hacan | `hacan` | Masters of Trade, Guild Ships, Arbiters |
| The Federation of Sol | `sol` | Orbital Drop, Versatile |
| The Ghosts of Creuss | `ghost` | Quantum Entanglement, Slipstream, Creuss Gate |
| The L1Z1X Mindnet | `l1z1x` | Assimilate, Harrow |
| The Mentak Coalition | `mentak` | Ambush, Pillage |
| The Naalu Collective | `naalu` | Telepathic, Foresight |
| The Nekro Virus | `nekro` | Galactic Threat, Technological Singularity, Propagation |
| Sardakk N'orr | `sardakk` | Unrelenting |
| The Universities of Jol-Nar | `jolnar` | Fragile, Brilliant, Analytical |
| The Winnu | `winnu` | Blood Ties, Reclamation |
| The Xxcha Kingdom | `xxcha` | Peace Accords, Quash |
| The Yin Brotherhood | `yin` | Indoctrination, Devotion |
| The Yssaril Tribes | `yssaril` | Stall Tactics, Scheming, Crafty |

### Prophecy of Kings (7 frakcji)
| Frakcja | alias | Zdolności |
|---|---|---|
| The Argent Flight | `argent` | Zeal, Raid Formation |
| The Empyrean | `empyrean` | Voidborn, Aetherpassage, Dark Whispers |
| The Mahact Gene-Sorcerers | `mahact` | Edict, Imperia, Hubris |
| The Naaz-Rokha Alliance | `naaz` | Distant Suns, Fabrication |
| The Nomad | `nomad` | The Company, Future Sight |
| The Titans of Ul | `titans` | Terragenesis, Awaken, Coalescence |
| The Vuil'Raith Cabal | `cabal` | Devour, Amalgamation, Riftmeld |

### Codex III — Council Keleres (1 frakcja, 3 warianty startowe)
| Frakcja | alias | Zdolności |
|---|---|---|
| The Council Keleres — Argent | `keleresa` | The Tribuni, Council Patronage, Law's Order |
| The Council Keleres — Mentak | `keleresm` | (jw.) |
| The Council Keleres — Xxcha | `keleresx` | (jw.) |

### Thunder's Edge (DLC, 6 frakcji + neutral)
| Frakcja | alias | Zdolności |
|---|---|---|
| Last Bastion | `bastion` | Liberate, Galvanize, Phoenix Standard |
| The Crimson Rebellion | `crimson` | Sundered, Incursion, Sorrow |
| The Deepwrought Scholarate | `deepwrought` | Research Team, Oceanbound |
| The Firmament | `firmament` | Plots Within Plots, Puppets of the Blade |
| The Obsidian | `obsidian` | Nocturne, The Blade's Orchestra, Marionettes |
| The Ral Nel Consortium | `ralnel` | Survival Instinct, Miniaturization |
| (Neutral) | `neutral` | — pseudo-frakcja systemowa (jednostki neutralne), nie gra |

> Pełne TEKSTY zdolności są w `assets/data/abilities/*.json` — nie przepisujemy ich tu
> ani do kodu z pamięci. Przy implementacji każdego gimmicka: odczyt tekstu z danych →
> wpis reguły do `RULES.md` ze źródłem → hook w silniku → test. Thunder's Edge to DLC,
> więc część mechanik może odbiegać od LRR — wtedy źródłem jest materiał Thunder's Edge
> (do potwierdzenia przez użytkownika, gdy reguła niejasna).

## Status i następny krok

- **Milestone 1 — cyfrowa plansza + God-Mode:** ✅ gotowy (mapa, jednostki, gracze,
  historia/Undo, edycja graficzna, panel faz).
- **E1 — fazy + kolejność tur:** ✅ gotowy (`turn_flow.py`, endpointy, panel faz).
- **E2 — faza strategii (wybór kart):** ✅ gotowy (`strategy_phase.py`, pula kart, wybór +
  transfer trade goods, akumulacja TG, picker w UI).
- **E3 — akcja taktyczna:** ✅ gotowy (`core/tactical.py` + `core/combat.py`,
  `api/routers/tactical.py`, panel taktyczny + okno walki w UI). Asystent stołu: aktywacja,
  FSM kroków, walka kosmiczna/naziemna z pomocami liczbowymi, przejęcie planety, pomoc
  produkcji. Zero walidacji reguł (decyzja projektowa). Bloki T1–T4, reguły RULES.md 19–22.
- **Następny krok: E4 — akcje komponentowe** (karty akcji, liderzy, badanie tech, eksploracja).
- **Frakcje (E7):** lista 30 frakcji + gimmicki spisane (sekcja „Frakcje"). Kodujemy je
  dopiero PO silniku bazowym (E3–E6), frakcja po frakcji, jako hooki w oknach silnika.

Szczegółowy dziennik postępu: `PROGRESS.md`. Mapa dokumentacji: `README.md` (w `docs/`).
