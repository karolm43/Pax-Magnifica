> 🟤 **ARCHIWALNY — werdykt wykonalności + podział na warstwy A/B.** Konkretny plan
> etapów (E1–E7) przejął [`PLAN_PELNA_ROZGRYWKA.md`](PLAN_PELNA_ROZGRYWKA.md). Ten plik
> trzymamy dla kontekstu decyzji (dlaczego port reguł, a nie integracja z botem).

# Plan przeniesienia pełnej funkcjonalności AsyncTI4 na nasz tryb solo

Cel (ustalony z użytkownikiem): przenieść PEŁNĄ funkcjonalność AsyncTI4 (fazy, akcje,
kolejność tur, karty strategii, agenda, walka, cele/VP, dodatki PoK/homebrew) na nasz
lokalny backend solo + stan gry. Dodatki włączalne/wyłączalne (już mamy `enabled_sources.json`).

## Werdykt wykonalności: TAK, przyrostowo

Architektura to umożliwia, bo **frontend (viewer AsyncTI4) renderuje cały stan z jednego
dokumentu `web-data`**. Każdy feature „zapala się", gdy backend wyśle odpowiednie pola.
Istnieje ostry podział na dwie warstwy:

### Warstwa A — „włącz teraz" przez dosłanie danych (małe zmiany, bez logiki gry)
Czysta serializacja w `src/api/web_data.py` (+ drobne pola w `PlayerState`/`GameState`).
Odzwierciedla stan fizycznej planszy (ręcznie / God-Mode), bez autonomicznych reguł:

1. ✅ **Panel faz (`gameState`)** — ZROBIONE (Blok F10). Faza + aktywny gracz (kolor);
   kolejność tur liczona z `playerData` (`active`/`passed`/`scs`).
2. ✅ **Żetony dowodzenia (CC)** — ZROBIONE. `tacticalCC/fleetCC/strategicCC/ccReinf`.
3. ⬜ **Karty strategii (wyświetlanie)** — per-gracz `scs`/`exhaustedSCs` + top-level
   `strategyCards[]` (`{initiative,name,id,picked,played,exhausted,tradeGoods,pickedByFaction}`).
4. ⬜ **Cele/VP + prawa** — `objectives`, per-gracz `secretsScored`/`soCount`/`totalVps`, `lawsInPlay`.
5. ⬜ **Liderzy / karty akcji / relikty** — `leaders`/`leaderIDs`, `acCount`, `relics`.

### Warstwa B — prawdziwy silnik (duże; roadmapa M2–M6)
Logika faz, akcji, walki, produkcji, agendy. Kod referencyjny jest w
`TI4_map_generator_bot/src/main/java/ti4/service/` (katalogi 1:1 z roadmapą):
- `turn/` (StartTurn/EndTurn/Pass), `strategycard/` (pick/play/secondary),
  `tactical/` (activate→move→combat→invasion→production), `combat/` (dice/rozstrzyganie),
  `agenda/` + `StatusCleanupService`, oraz `objectives/leader/tech/planet/...`.

**Separowalność:** usługi są splecione z Discordem (JDA buttony/wiadomości) — NIE da się
przenieść usługi w całości. Wzorzec (zgodny ze steeringiem „zero reguł z pamięci"):
czytaj regułę z Javy → zapisz w `docs/RULES.md` ze źródłem → zaimplementuj w Pythonie.
Tak zrobiliśmy już z limitami jednostek (RULES.md 3), pozycjami stat-area (4),
startowymi CC (5). Bot = tekst referencyjny, nie biblioteka.

**Kolejność Warstwy B (jak pakiety Javy):** turn/pass → strategycard → tactical+combat
→ status → agenda. Każdy krok samodzielnie testowalny; po jego zrobieniu pola Warstwy A
wypełniają się automatycznie zamiast przez God-Mode.

## Kontrakt web-data (gdzie co leży)

- `src/api/web_data.py` → `build_web_data` buduje cały dokument `PlayerDataResponse`.
- Kształt pól: `frontend/src/entities/data/types.ts` (`PlayerDataResponse`, `GameState`,
  `GamePhase`, `StrategyCard`, `PlayerData`).
- Panel faz: `frontend/.../GameStatePanel.tsx` (czyta `gameState` + `playerData`).
- Heksy stat-area: `frontend/.../PlayerStatsArea.tsx` (CC na drugim heksie).

## Zasada

Każda przenoszona reguła TI4 trafia najpierw do `docs/RULES.md` ze wskazaniem źródła
(Java bot / LRR). Dane liczbowe wyłącznie z assetów AsyncTI4 przez `StaticDataRegistry`.
