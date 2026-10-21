# Plan: pełna rozgrywka Twilight Imperium na stronie

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

### E3 — Akcja taktyczna (aktywacja → ruch → walka kosmiczna → inwazja → produkcja)
Źródło: `service/tactical/` (TacticalAction* + movement/planet/postmovement), `service/combat/`.
- Krokowa maszyna (Timing Windows FSM wg spec 1.2.2): ACTIVATION → MOVEMENT →
  SPACE_CANNON → SPACE_COMBAT → INVASION → PRODUCTION, z oknami na reakcje.
- Reguła ruchu: zasięg, wormhole, anomalie (RULES.md 1), pojemność transportu.
- Walka: na start ręczne przypisanie trafień (God-Mode), potem symulator (M2 roadmapy).
- UI: „Aktywuj system" → wybór ruchu (tryb przenoszenia mamy) → okna fazowe.
- DoD: pełna akcja taktyczna krok po kroku z reakcjami między oknami.

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
Źródło: `service/abilities/`, `rules_hooks` (spec), VP do zwycięstwa.
- Zdolności frakcji (hooki na ruch/walkę/produkcję), warunek wygranej (10 VP).

## Status i następny krok

- God-Mode (Milestone 1) — ✅ zasadniczo gotowy: mapa, jednostki, gracze, historia/Undo.
- Następny krok: **E1 (fazy + tury)** — najmniejszy fundament, który czyni grę „grywalną"
  krok po kroku. Reszta dokłada realne akcje na tym szkielecie.
