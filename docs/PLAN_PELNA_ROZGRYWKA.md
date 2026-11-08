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
- **⚠️ DECYZJA ZMIENIONA (2026-10, patrz RULES.md 29):** pierwotnie silnik był ASYSTENTEM
  STOŁU (prowadził kroki, NIE walidował reguł). NOWY KIERUNEK: silnik jest SĘDZIĄ — EGZEKWUJE
  reguły TI4 przez kod (bo bot AI i tak musi je znać, a to wygodniejsze dla gracza). God-Mode
  zostaje jako osobny kanał ręcznej korekty (omija walidację). E3 w wersji asystenta (bloki
  T1–T4) jest FUNDAMENTEM — dobudowujemy na nim walidację + okna czasowe (patrz etap E8 niżej).
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

### E8 — Silnik-SĘDZIA: egzekucja reguł + okna czasowe (PRZEBUDOWA, w toku) ⬅ AKTUALNY

Źródło decyzji: RULES.md 29 (zmiana kierunku z „asystent" na „sędzia"). Dobudowujemy walidację
i okna czasowe NA ISTNIEJĄCYM E1–E3 (nie przepisujemy). Tryb: solo vs boty + hot-seat (docelowo
sieć), więc okna pytają graczy po kolei. God-Mode zostaje jako kanał omijający walidację.

Zadania (pełny opis i reguły: RULES.md 29.1–29.3; dziennik: PROGRESS.md):
- T1: model okna czasowego w `GameState` + `core/timing.py` (kolejka respondentów, open/respond/close).
- T2: ekspozycja okna w `web_data` + panel okna w UI (kto teraz reaguje + odpowiedź).
- T3: pierwsze realne okno — secondary karty strategii (zagranie karty otwiera okno pozostałym).
- T4: pojęcie aktualnego gracza w STATUS/AGENDA + twarda walidacja flow (czyja tura, co wolno).
- T5: ruch jako funkcja core (`core/movement.py`) + walidacja zasięgu/anomalii/przejezdności.
- T6: walidacja aktywacji / przejęcia planety / produkcji (koszty, limity, legalność).
- T7: walka — rdzeń: rzuty (seedowalny RNG) + liczenie trafień + okno „przypisz straty", wielorundowo.
- T8: interaktywna walka w UI (animacja rzutów kośćmi) spięta z oknami.
- T9: dodatkowe okna walki — anti-fighter barrage + space cannon offense.
- T10: aktualizacja dokumentacji (RULES.md 29, PLAN, PROGRESS, README) + memory projektu.

DoD E8: pełna runda rozgrywana z egzekwowanymi regułami i oknami czasowymi (secondary działa dla
wszystkich graczy po kolei; nielegalne akcje odrzucane; walka rozstrzygana przez silnik z rzutami).

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
  transfer trade goods, akumulacja TG, picker w UI). **DOMKNIĘTE jako sędzia** (feature
  `strategy-phase-complete`, RULES.md 13): Pick_Count (3–4→2, 5–8→1), druga runda od mówcy,
  walidacja przejścia STRATEGY→ACTION + ścisła kolejność inicjatywy → HTTP 422; UI
  `StrategyCardTable` + `PhaseTransitionBanner`. Szczegóły: PROGRESS.md.
- **E3 — akcja taktyczna:** ✅ gotowy (`core/tactical.py` + `core/combat.py`,
  `api/routers/tactical.py`, panel taktyczny + okno walki w UI). Asystent stołu: aktywacja,
  FSM kroków, walka kosmiczna/naziemna z pomocami liczbowymi, przejęcie planety, pomoc
  produkcji. Zero walidacji reguł (decyzja projektowa). Bloki T1–T4, reguły RULES.md 19–22.
- **E3 — akcja taktyczna (wersja asystenta):** ✅ gotowy jako FUNDAMENT (bloki T1–T4, RULES.md 19–22).
- **⬅ AKTUALNY: E8 — silnik-sędzia (egzekucja reguł + okna czasowe)** — PRZEBUDOWA na istniejącym
  E1–E3 (patrz etap E8 wyżej + RULES.md 29). Rozpoczęta od aktualizacji dokumentacji (T10 częściowo).
- **E4 — akcje komponentowe** (karty akcji, liderzy, badanie tech, eksploracja) — po E8.
- **Frakcje (E7):** lista 30 frakcji + gimmicki spisane (sekcja „Frakcje"). Kodujemy je
  dopiero PO silniku bazowym (E3–E6), frakcja po frakcji, jako hooki w oknach silnika.

Szczegółowy dziennik postępu: `PROGRESS.md`. Mapa dokumentacji: `README.md` (w `docs/`).

## OSTATECZNY PLAN KOLEJNOŚCI (nadrzędny wobec starszych kolejności w tym pliku)

Ustalone z użytkownikiem. Karty strategii i dodawanie technologii istnieją (bez pełnych efektów), więc
następny krok to **porządkowanie punktów centralnych (C) i szkielet hooków (H)**.

| Faza | Zakres | Uwagi |
|---|---|---|
| **C** | Punkty centralne: jedna funkcja na każdą rozproszoną operację (płatności, żetony, wyczerpywanie, kontrola planet, zniszczenie/postawienie jednostek, zdobycie technologii, VP) | Czysty refaktor, ZERO zmiany zachowania; testy regresji. Patrz „Audyt miejsc rozproszonych" niżej |
| **H0–H2** | Szkielet `core/rules_hooks.py` + punkty zaczepienia NA punktach centralnych z C | Pierwsze przypadki: Arborec (`production.py`), Antimass (`movement.py`), technologia „ruch przez systemy z obcymi statkami", Keleres (commodities jako TG) |
| **T** | Dokończenie technologii: zdobywanie (karta Technology, skipy, prerekwizyty) + efekty technologii jako hooki | Efekty po H2; reguły z `R_technology`, `R_technology_sc`, `R_unit_upgrades` |
| **S** | Dokończenie kart strategii (efekty primary/secondary, wyjątki frakcyjne jako hooki) | Wg stanu kodu `core/strategy_cards/*` |
| **X** | Eksploracja: dokończenie (talie, attachmenty, relikwie) + efekty kart jako hooki | Wg stanu `core/exploration.py` |
| **H1b** | STOP: punkty kontrolne + przerwanie (RULES.md 43.4) | Przed kartami akcji |
| **E4–E7** | Karty akcji, frakcje (proste → złożone), agendy | Wg raportu pokrycia (H3) |
| **N** | Sieć do 6 graczy (RULES.md 44) | `actor_id` w nowych endpointach OD TERAZ |

Zasady przekrojowe:
- Każdy blok: RULES.md ze źródłem → kod w `core/` → test → cienki endpoint → QA (pytest/ruff/mypy) → commit.
  Wątpliwa reguła = ⚠ ZAŁOŻENIE i pytanie do użytkownika.
- Do czasu ukończenia H2: żadnych nowych `if faction == ...`/sprawdzeń konkretnej karty w regułach bazowych.
  Jeśli wyjątek jest konieczny, ląduje w JEDNYM nazwanym miejscu (stała/słownik) z komentarzem `HOOK-CANDIDATE`
  (jak `_PRODUCTION_FORBIDS`), żeby migracja do hooków była mechaniczna.
- Każda zmiana stanu opisana w „punktach centralnych" (niżej) idzie WYŁĄCZNIE przez jej funkcję centralną.

## Audyt miejsc rozproszonych (punkty centralne) — wynik wyszukiwania w `src/core/`

Hook przyczepia się w JEDNYM miejscu, więc operacja musi mieć jedną funkcję. Poniżej wynik wyszukiwania
(grep po kodzie, stan z tej sesji). Liczby = liczba trafień we wzorcach, wstępne; DOKŁADNĄ listę wywołań
ustala blok C0 (przegląd przed refaktorem).

| # | Operacja | Gdzie rozproszone dziś | Funkcja centralna (propozycja) | Przykłady hooków |
|---|---|---|---|---|
| 1 | Trade goods / commodities (dodanie, wydanie, konwersja) | `payment.py`, `production.py` (osobna ścieżka), `objective_payment.py`, `exploration.py` (TG i commodities), `strategy_phase.py`, `transaction.py`, `strategy_cards/trade.py` | `core/economy.py`: `gain_tg`, `spend_tg`, `gain/spend_commodities`, `convert_commodities`, `payment_sources` | commodities liczone jak TG (Keleres), zmiana kosztu, zwrot |
| 2 | Płatność zasobami/wpływem (planety + TG) | `payment.py` (karty), `production.py` (`Spend`, `auto_pay`), `objective_payment.py`, `exploration.py` | jedna `pay(...)` używana przez wszystkich; produkcja przepięta | modyfikatory kosztu, dodatkowe źródła zapłaty |
| 3 | Żetony dowodzenia (taktyczne/flota/strategiczne) | `objective_payment.py`, `status_phase.py`, `strategic_action.py`, `tactical.py`, `strategy_cards/common.py` | `core/command_tokens.py`: `gain`, `spend`, `move_between_pools` | darmowa aktywacja, dodatkowe żetony |
| 4 | Wyczerpywanie/odświeżanie planet i technologii | `exhausted_planets` w ~11 plikach (m.in. `invasion.py`, `production.py`, `payment.py`), `exhausted_technologies` (`status_phase`, `board_edit`) | `core/exhaust.py`: `exhaust_planet/ready_planet`, `exhaust_tech/ready_tech` | odświeżanie planet, zdolności „exhaust this card" |
| 5 | Statystyki jednostek (ruch, pojemność, koszt, walka, produkcja) | `resolve_unit_variant` wołane w ~11 plikach (16 wywołań) — dobry punkt centralny już istnieje | zostaje; hook MODIFY na wyniku (`unit_stat(...)`) | bonusy do ruchu/walki, jednostki frakcyjne |
| 6 | Wartość planet (resources/influence) | `planet_stats.py` (`resources_of`, `influence_of`; użycia: `production.py`, `tactical.py`, `payment.py`) | zostaje; hook MODIFY na wartości | attachmenty, cechy |
| 7 | Zmiana kontroli planety | zapisy `planet_owners[...]=` w `invasion.py`, `tactical.py`, `faction_setup.py` (poza God-Mode `board_edit`) | `core/control.py`: `set_planet_control` (RULES.md 12, 23) | „po zdobyciu planety", wyczerpanie przy zdobyciu |
| 8 | Zniszczenie/postawienie/usunięcie jednostek | `battle.py` (13), `invasion.py` (10), `space_cannon.py` (5), `movement.py`, `unit_catalog.py`; stawianie: `production.py`, `retreat.py`, `exploration.py` | `core/unit_ops.py`: `destroy`, `place`, `remove`, `move` (z limitem fleet pool/reinforcements) | „gdy jednostka zniszczona", odrodzenie, limity |
| 9 | Zdobycie technologii | brak funkcji centralnej (listę zmienia setup/God-Mode; karta Technology brakuje) | `core/technology.py`: `gain_technology`, `can_research`, prerekwizyty, skipy | „gdy zbadasz technologię", skipy frakcyjne |
| 10 | Punkty zwycięstwa | `objectives.award_points` (jest) + zapisy w `status_phase.py`, `imperial.py`, `game_end.py` | upewnić się, że wszystkie idą przez `award_points`/`remove_points` | „gdy zdobywasz/tracisz punkt" |
| 11 | Karty (dobór/odrzucenie/ręka) | `card_draw.py`, `deck_piles.py`, `status_phase.py` | jedna `draw`/`discard` | limit ręki, dobór dodatkowy |
| 12 | Modyfikatory walki (rzuty, trafienia, reroll, straty) | `battle.py`, `combat.py`, `components.py` | punkty zaczepienia w jednym pipeline rzutu | +1 do rzutu, reroll, ignorowanie sustain |
| 13 | Dostępność/limit jednostek (fleet pool, reinforcements) | `fleet_pool.py`, `capacity.py`, `production.py`, `retreat.py`, `unit_catalog.py` | pozostaje w `unit_ops` (pkt 8) | zmiana limitów |
| 14 | Okna czasowe | `open_window` w `battle`, `capacity`, `fleet_pool`, `space_cannon`, `status_phase`, `strategic_action`, `timing` — już jedno API | zostaje | wszystkie TRIGGER-y |
| 15 | Wyjątki na sztywno (długi) | `production.py::_PRODUCTION_FORBIDS` (Arborec), `movement.py` (alias Antimass), `unit_catalog.py` (aliasy technologii) | migrować do hooków w H2 | — |

Uwagi:
- Pozycje 5, 6, 14 mają już dobry punkt centralny; wystarczy dodać punkt zaczepienia.
- Najwięcej pracy: 1–4, 7, 8, 9 (rozproszone lub brak funkcji). To zakres fazy C.
- Wyszukiwanie było wzorcowe (grep); mogą istnieć miejsca, których wzorce nie złapały (np. zmiany przez `setattr`,
  przez serializację albo w warstwie `api/`). Blok C0 ma to doprecyzować, a testy architektury (niżej) pilnować na przyszłość.
- Przykład z prośby użytkownika: „Keleres: może wyczerpać kartę, by każdy gracz wydawał commodities jak TG" —
  po C to JEDEN wpis w `payment_sources`, bo wszystkie płatności idą przez `pay(...)`.

### Faza C — bloki (czysty refaktor, bez zmiany zachowania)
**Stan wykonania fazy C (aktualizowane po każdym bloku):**

| Blok | Zakres | Status | Gdzie |
|---|---|---|---|
| C0 | Przegląd miejsc zapisu (skan AST per pole, nie sam grep) | ✅ robiony przy każdym bloku | — |
| C1 | Ekonomia: trade goods, commodities (tabela, wiersze 1–2) | ✅ | `core/economy.py`; płatność za wydanie (planety + TG) przez `payment.apply_payment` |
| C2 | Żetony dowodzenia: rezerwa + 3 pule (wiersz 3) | ✅ | `core/command_tokens.py` |
| C3 | Wyczerpywanie/odświeżanie: planety, technologie, karty strategii, liderzy, przełom (wiersz 4) | ✅ | `core/exhaust.py` |
| C4 | Kontrola planet: `planet_owners` + lustro `controlled_planets` (wiersz 7) | ✅ | `core/control.py` (`set_planet_control`) |
| C5 | Operacje na jednostkach: zniszczenie/postawienie/usunięcie/ruch + limity (wiersze 8, 13) | ⬜ następny, NAJWIĘKSZY (~30 miejsc w `battle`, `invasion`, `space_cannon`, `production`, `retreat`, `movement`, `exploration`) | planowany `core/unit_ops.py` |
| C6 | Zdobycie technologii: `gain_technology` (wiersz 9; dziś `technology.apply_research`) | ⬜ | planowany `core/technology.py` |
| C7 | Punkty zwycięstwa i karty (wiersze 10–11) | ⬜ | `objectives.award_points`, `card_draw.py` |
| C8 | Strażnik architektury | ✅ częściowo: pilnuje 13 pól + `setattr`; kolejne pola dopisujemy do `OWNERS` | `tests/test_central_points.py` |

Reguły wykonania: skan AST (a nie grep) znajduje też zapisy w krotkach, po kluczu słownika (`x.pole[k] = …`), `del` i mutacje list;
refaktor nie zmienia zachowania (jedyny wyjątek: operacje ponad stan — np. wydanie żetonu/TG, którego nie ma — kończą się `ValueError`
zamiast ujemnego licznika); każdy blok = kod + testy + QA (pytest/ruff/mypy) + commit.

Opis zamierzonych bloków (historyczny):
- **C0 — Przegląd:** dla każdego wiersza tabeli: pełna lista wywołań (grep + czytanie), decyzja nazwa/sygnatura, kolejność.
- **C1 — Ekonomia (1–2):** `core/economy.py` + płatność; przepięte `payment`, `production`, `objective_payment`, `exploration`,
  `strategy_phase`, `transaction`, `strategy_cards/trade`. Test regresji: istniejące testy bez zmian.
- **C2 — Żetony dowodzenia (3)** i **C3 — Exhaust/ready (4).**
- **C4 — Kontrola planet (7)** i **C5 — Operacje na jednostkach (8, 13).**
- **C6 — Technologia (9):** funkcja `gain_technology` (także pod kartę Technology i efekty „zdobądź technologię").
- **C7 — VP (10), karty (11).**
- **C8 — Test architektury:** test, który skanuje `src/core/` i pada, gdy ktoś zmienia pole stanu (np. `trade_goods`,
  `exhausted_planets`, `planet_owners`) poza funkcją centralną (lista wyjątków: God-Mode `board_edit`). To strażnik,
  żeby rozproszenie nie wróciło.
- DoD fazy C: pytest + ruff + mypy zielone, zachowanie niezmienione, strażnik C8 działa.

## Plan kart strategii (S0–S9) — PLAN, jeszcze nie rozpoczęty

Stan: `core/strategic_action.py` ma okno secondary (`STRATEGY_SECONDARY`) i tablice dispatchu
`_PRIMARY_EFFECTS`/`_SECONDARY_EFFECTS` po numerze inicjatywy. Realnie działa tylko primary Leadership
(+3 żetony); secondary Leadership jest NO-OP (TODO: kupno żetonów za wpływ, wymaga modelu wydawania).
Treść kart WYŁĄCZNIE z `assets/data/strategy_cards/*.json`; reguły z `docs/rules_tirules/` (`R_<karta>.md`,
`R_strategic_action.md`); nic z pamięci. Wpis w RULES.md 30 rozszerzamy kartą po karcie (30.x).

### S0 — Model wydawania zasobów i wpływu (fundament dla wszystkich kart)
- Czysta funkcja `core/spending.py`: wyczerpanie planet (exhaust), sumowanie resources/influence z uwzględnieniem
  flex/optimal (RULES.md 7, 27), trade goods jako zamiennik, walidacja „czy stać gracza", zwrot reszty/nadpłaty.
- Wspólny punkt zaczepienia dla produkcji, technologii, głosowania, kart (jedno miejsce, później hook).
- DoD: wydawanie testowane na przypadkach brzegowych; produkcja przepięta na ten model bez zmiany wyniku.

### S1 — Przegląd danych i zależności 8 kart
- Z JSON + tirules: tabela „karta → primary / secondary → od jakich podsystemów zależy" (np. talia kart akcji,
  badanie technologii, stawianie struktur, produkcja, punktowanie, ruch). Wynik w RULES.md 30.
- Ustalenie kolejności S2–S9 wg zależności (najpierw karty bez nowych podsystemów).

### S2–S9 — Karty strategii po jednej (kolejność wg S1)
- Każda karta = osobny blok: RULES.md 30.x ze źródłem → primary + secondary w `strategic_action.py` (dispatch)
  → test → endpointy/okno w UI (komponenty `StrategyCardDetailsCard` itp.) → QA → commit.
- Nowe podsystemy dobudowane „na zamówienie" przez karty (np. talia kart akcji, badanie tech) — każdy z własnym RULES,
  testem i oznaczeniem ⚠, jeśli reguła niejasna.
- Secondary jest zagrywane w oknie, w którym wszyscy są pytani — nie wymaga STOP (RULES.md 43.4).
- Każda karta strategii to osobny temat ⇒ osobny plik (`core/strategy_cards/<karta>.py`) + cienki dispatch w `strategic_action.py`.
- DoD: 8 kart ma działające primary i secondary (lub jawnie ⚠ MANUAL, z uzasadnieniem), status w `effects_registry`.

### Zależności frakcyjne kart strategii
- Wyjątki frakcji dotyczące kart strategii (modyfikujące primary/secondary) NIE wchodzą do S2–S9; dochodzą po H2
  jako hooki (RULES.md 43), żeby nie wplatać `if faction == ...` w reguły kart.

## Etap sieciowy (N) — PLAN, po silniku bazowym (RULES.md 44)

Cel: partia do 6 graczy (ludzie + boty) przez sieć. Fundamenty już są: logika w `core/`/`api/`, WebSocket
(`ConnectionManager`), projekcja widoczności (`core/visibility.py`), okna czasowe z kolejką, `EventStore`.
**Od teraz:** każdy nowy endpoint akcji ma `actor_id` (RULES.md 44.1).

- **N0 — Audyt:** które endpointy akcji nie mają `actor_id`, które walidują gracza; lista luk.
- **N1 — Tożsamość i autoryzacja:** token na miejsce przy stole (link zaproszenia), role host/observer,
  `actor_id` ustalane z tokenu, `viewing_player` z tokenu w trybie sieciowym (44.2).
- **N2 — Push per gracz:** WebSocket z własną projekcją dla każdego połączenia; wiadomości jawne/prywatne;
  testy „nic nie wycieka" (44.3).
- **N3 — Wiele gier i trwałość:** `game_id`, lobby/pokoje, zapis `EventStore` na dysk, wznowienie po restarcie
  i ponownym połączeniu (44.4).
- **N4 — Współbieżność:** blokada na grę, idempotencja żądań, odtwarzanie stanu po reconnect (44.4).
- **N5 — UI wielu graczy:** „czekamy na gracza X", równoległe odpowiedzi tam, gdzie reguły pozwalają,
  timeouty i przejęcie przez bota/pas (44.5); STOP z jednolitym timerem (43.4).
- DoD: partia 6 graczy (z botami) w sieci; żaden klient nie widzi cudzej ręki; restart serwera nie kasuje gry.
- Ryzyko największe: wyciek informacji (autoryzacja + projekcja) — testy bezpieczeństwa przed udostępnieniem innym.

## Plan hooków i wyjątków (E7 + E4 + E6) — PLAN, jeszcze nie rozpoczęty (po blokach S)

Zasady architektury: **RULES.md 43** (hooki, kolejność, MANUAL vs IMPLEMENTED). Cel: dodawanie wyjątków
(frakcje, karty akcji, agendy) bez ruszania reguł bazowych, kodowane po jednym, z wpisem w RULES + testem.

Baza, która już jest (nie budujemy od zera): `core/effects_registry.py` (status efektu per komponent:
`NOT_IMPLEMENTED/IMPLEMENTED/MANUAL`), `core/timing_spec.py` (wyzwalacz → typ okna, RULES.md 34),
`core/timing.py` (okna), `core/component_action.py` (szkielet akcji komponentu — bez efektów),
`core/components.py` + `component_loader.py` (katalog komponentów z assetów). Brakuje: `core/rules_hooks.py`
i punktów zaczepienia w regułach; wyjątek Arborec jest dziś na sztywno w `production.py` (`_PRODUCTION_FORBIDS`).

### H0 — Przygotowanie (bez kodu gry)
- Przejrzeć miejsca w `core/` z twardymi wyjątkami (grep po `faction`/`_FORBIDS`/id kart) — lista „długu".
- Ustalić w RULES.md 43 ⚠ założenia z użytkownikiem (typy hooków, kolejność, MANUAL vs blokada).
- DoD: lista punktów zaczepienia potrzebnych na start + zatwierdzone założenia.

### H1 — Szkielet `core/rules_hooks.py`
- Rejestr: `(źródło komponentu, punkt zaczepienia, kategoria, funkcja)`; pobieranie hooków dla stanu
  (kto posiada frakcję/kartę/tech/prawo) w deterministycznej kolejności (RULES.md 43.1 pkt 5).
- API: `apply_modifiers(point, state, ctx, base)`, `check_permissions(...)`, `collect_triggers(...)`,
  `resolve_replace(...)`. Czyste funkcje, zero HTTP.
- Test regresji: pusty rejestr ⇒ wszystkie obecne testy bez zmian.
- DoD: szkielet + testy jednostkowe kolejności/konfliktów; pytest + ruff + mypy zielone.

### H1b — Model reakcji: punkty kontrolne + STOP (RULES.md 43.4)
- Oznaczanie migawek `EventStore` jako punkt kontrolny / nieodwracalny (rzut, ujawnienie karty, dobór);
  `goto(seq)` już istnieje, dochodzi tylko metadane i blokada cofania poza punktem kontrolnym.
- Filtr po informacji jawnej (liczba kart akcji itp.) wyznaczający, kogo w ogóle można pytać.
- Odpytywanie botów wewnętrzne (bez UI); STOP człowieka otwiera okno czasowe (`core/timing.py`)
  z zatrzymującym graczem jako pierwszym.
- UI: baner „ostatnia akcja" z przyciskiem STOP, aktywny do najbliższego punktu nieodwracalnego (w walce:
  przycisk „Rzuć" jako naturalna granica).
- Robimy PRZED kartami akcji (H4): od tego zależy, jak wchodzi każda reakcja.
- DoD: jedna testowa reakcja (np. prosta karta „when/after") działa przez STOP bez pytania wszystkich
  graczy; test: zachowanie dla gracza z kartą i bez karty jest identyczne z zewnątrz.

### H2 — Punkty zaczepienia w istniejących regułach (cienkie wywołania)
- Produkcja (`production.py`): `production_forbids`, `production_value`, `cost_modifier`.
- Ruch (`movement.py`): `move_value`, `can_pass_system`, `ignore_anomaly`, `capacity`.
- Walka (`combat.py`/`battle.py`/`space_cannon.py`/`invasion.py`): `roll_modifier`, `extra_dice`,
  `reroll`, `hit_assignment`, `before_combat`/`after_combat` (przez okna).
- Status/agenda: `status_start`, `status_end`, `vote_modifier`.
- **Pierwszy przypadek:** przenieść wyjątek Arborec z `production.py` do hooka (zachowanie bez zmian, testy zielone).
- DoD: żadna reguła bazowa nie zawiera `if faction == ...`; Arborec działa przez rejestr.

### H3 — Raport pokrycia (priorytetyzacja)
- Rozszerzyć audyt (`src/audit/`, `effects_registry`) o: komponent → wymagany punkt zaczepienia
  (z `timing_spec` + typ efektu). Wynik: ile kart/zdolności obsłuży każdy punkt.
- DoD: raport w `docs/` (generowany, nie ręczny) + kolejka kolejnych kroków wg liczby obsłużonych komponentów.

### H4 — Karty akcji (E4)
- Dispatch po `component_id` w `component_action`/oknach REACTION; każda karta: tekst z assetów → wpis RULES →
  hook → test; status w `effects_registry` na `IMPLEMENTED`. Karty bez hooka zostają `MANUAL`.
- Kolejność: najpierw karty o prostym, jednofazowym efekcie (modyfikatory, +/- zasoby), potem z oknami reakcji,
  na końcu „instead of"/zmiana kolejności.
- DoD (iteracyjnie): % pokrycia kart akcji rośnie, brak regresji.

### H5 — Frakcje (E7)
- Wg tabel w sekcji „Frakcje": najpierw modyfikatory liczb/legalności (np. Sardakk, Jol-Nar, Sol, Letnev,
  Winnu, Hacan), potem zdolności z oknami (Mentak, Xxcha, Saar), na końcu strukturalne
  (Nekro, Creuss, Mahact, Naalu, Yssaril, Titans, Cabal, Obsidian, Firmament, Crimson, Deepwrought, Ral Nel,
  Last Bastion). Liderzy, tech frakcyjne i jednostki specjalne jako osobne hooki tej samej frakcji.
- Jedna frakcja = jeden blok: RULES.md + hooki + test + commit.
- DoD: frakcja ma status `IMPLEMENTED` dla wszystkich swoich zdolności lub jawnie `MANUAL` dla wybranych.

### H6 — Faza agendy i agendy (E6)
- Warunek wstępny: `core/agenda_phase.py` (odsłonięcie, głosowanie wg wpływów, rozstrzygnięcie, okna
  „when/after agenda revealed", remisy po stronie mówcy wg reguł) — NAJPIERW z tirules2 (`R_agenda_phase`).
- Prawa jako hooki `PERSISTENT` (wygasanie przy odrzuceniu/zamianie), dyrektywy jako jednorazowe efekty.
- DoD: pełna faza agendy działa bez agend-wyjątków; potem agendy po jednej wg tej samej procedury.

### H7 — Dokumentacja i porządek
- Po każdym bloku: RULES.md (43 + wpis komponentu), PROGRESS.md, `effects_registry`, QA
  (`uv run pytest -q`, `uv run ruff check src tests`, `uv run mypy src tests`), commit (konkretne pliki).
- Po H2 zaktualizować `docs/ARCHITEKTURA_KODU.md` (sekcja o `rules_hooks` i katalogu `hooks/`).

### Ryzyka
- Interakcje wielu efektów (np. dwa „instead of" na jednym kroku) → obsługa przez kolejność z RULES 43.1 pkt 5
  i weryfikacja na tirules2; nierozstrzygnięte przypadki zostają ⚠ ZAŁOŻENIEM do decyzji użytkownika.
- Thunder's Edge: część mechanik może odbiegać od LRR — źródłem są assety + potwierdzenie użytkownika.
- Rozrost rejestru: pilnować podziału tematycznego plików (pkt 12) i raportu pokrycia (H3).
