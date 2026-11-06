# Postęp projektu — Custodian Engine

Plik śledzi stan prac między sesjami. Aktualizowany na koniec każdego bloku.
Starsze, ukończone bloki (Faza 1 → E4·UI²) są w `PROGRESS_ARCHIWUM.md`.

> **Aktualny etap:** E8 — przejście na silnik-SĘDZIA (egzekucja reguł) + okna czasowe.
> Plan zadań: `PLAN_PELNA_ROZGRYWKA.md` („E8"); reguły: `RULES.md` 29.

## Status etapów silnika

| Etap | Zakres | Status |
|---|---|---|
| Faza 1 | Cyfrowa plansza + God-Mode (dane, mapa, setup, edycja, Undo) | ✅ ukończona |
| F0–F18 | Migracja na frontend ti4_web + panele graczy + God-Mode UI | ✅ ukończone |
| E1–E2 | Fazy + kolejność tur + faza strategii | ✅ ukończone |
| E3 | Akcja taktyczna (aktywacja, ruch, walka, inwazja, produkcja) | ✅ fundament |
| E4 | Kontrola komponentów (exhaust/refresh) + menu RMB | ✅ ukończone |
| E8 | Silnik-SĘDZIA: walidacja reguł + okna czasowe (T1–T7 + faza akcji 31.7/31.8) | 🔧 w toku |

> Pełna historia ukończonych bloków ze szczegółami: `PROGRESS_ARCHIWUM.md`.

---

### ✅ Fix — dobór frakcji: Keleres max 1 wariant (losowanie + jawny wybór)

- **Problem:** przy wyborze „random" losowanie mogło przydzielić dwóm graczom różne
  warianty Council Keleres (`keleresm`/`keleresx`/`keleresa`) — a to jedna frakcja
  z trzema wariantami mentora, więc w grze może być najwyżej jeden.
- **Fix (`src/core/setup_service.py` → `_resolve_factions` / `_playable_faction_pool`):**
  pula losowania dedupuje po rodzinie frakcji (`registry.faction_family`) i bierze
  jednego przedstawiciela na rodzinę; rodziny zajęte jawnym wyborem są pomijane.
  Jawny wybór dwóch wariantów tej samej rodziny → `ValueError` (HTTP 422), obok
  istniejącej walidacji duplikatu `faction_id`.
- **Reguła:** `RULES.md` 28.1 (źródło: struktura danych + `F_keleres.md`).
- **Testy backendu:** `tests/test_setup_factions.py` (losowanie bez dwóch Keleres, jawny
  Keleres blokuje losowanie wariantu, dwa jawne warianty → błąd). QA: pytest 507, ruff, mypy.
- **Fix frontendu (ten sam problem w UI):** przy ręcznym wyborze gracze mogli klikać różne
  warianty Keleres i zobaczyć błąd dopiero przy starcie (422). Teraz:
  - `useSetupStore.ts` → `validateFactions` wykrywa duplikat RODZINY (`familyOfVariant`),
    nie tylko identycznego `faction_id` — blokuje przycisk „Start game";
  - `Step_Faction.tsx` → przycisk „Choose" jest ZABLOKOWANY („Already taken"), gdy inny
    gracz ma już wariant tej rodziny; komunikat mówi o Council Keleres (jedna frakcja),
    a nie o duplikacie id.
  - Testy: `frontend/src/domains/setup/useSetupStore.test.ts`. QA frontu: type-check,
    eslint (pliki zmienione), vitest 19, build — zielone.

---

### ✅ E8 Blok B1–B6 — MOVEMENT dopracowany (drag&drop, monitor, zasięg, załadunek) (ukończone)

- **Decyzja (z użytkownikiem):** drag & drop statków to PREFEROWANY sposób ruchu; w akcji
  taktycznej idzie przez WALIDOWANY kanał (`/tactical/move`, reguły + capacity). Panel kroku
  MOVEMENT = MONITOR floty z cofaniem. Dok ma być ładny, przesuwany i skalowalny. Na mapie
  podgląd zasięgu. Zatrzymujemy się na MOVEMENT.
- **B1 — dok (fix + resizable):** root cause „dok rośnie / klei się do dołu" = `useDraggablePanel`
  nie zdejmował CSS-owego `bottom`/`right` → przy `fixed` z `top`+`bottom` bez `height` panel się
  rozciągał. Teraz `style` zwraca `bottom:auto`+`right:auto`. Nowy `useResizablePanel` (uchwyt w
  rogu, rozmiar w localStorage). Dok: stały nagłówek + przewijane ciało + przypięty uchwyt resize.
- **B2+B4 — piechota w przestrzeni + drag walidowany:** `RULES.md` 26 (wyjątek transportu, źródło
  `R_transport`/`R_invasion`): siły naziemne/myśliwce jadą jako ładunek i stoją w PRZESTRZENI
  aktywnego systemu do Commit Ground Forces; blokada „tylko planeta" tylko poza akcją (God-Mode).
  `useUnitDrag`: drop na aktywny system w akcji taktycznej → walidowany `moveShips` (statek vs
  ładunek po asyncId), poza akcją → God-Mode. `MoveQuantityModal` też routuje taktycznie. Wspólny
  `UnitStack/cargo.ts` (baseType/ship/cargo).
- **B3 — zasięg na mapie:** `core.movement.legal_move_sources` + `GET /tactical/move-range`
  (+3 testy). `useMoveRange` hook; `refresh()` invaliduje `moveRange`. `MapTile`: bursztynowe,
  pulsujące podświetlenie heksów będących legalnym źródłem ruchu.
- **B6 — panel = MONITOR floty:** krok MOVEMENT pokazuje flotę w przestrzeni AKTYWNEGO systemu
  + plakietka pojemności (zajęte/wolne, czerwona gdy przekroczona; liczona dla KONKRETNEGO gracza
  z `lookupUnit`). „Undo last move" (globalny `/undo`). Kreator ruchu schowany pod przełącznikiem.
- **B5 — okno ZAŁADUNKU transportu:** `LoadTransportModal` + store `loadTransport` — dla statku
  z capacity w systemie źródłowym: pokazuje jego pojemność i dostępny ładunek z tego systemu,
  „Fill to capacity"/„Clear", i rusza nosiciela + ładunek jednym walidowanym `/tactical/move`.
  Skrót „Load … with cargo…" w kreatorze ruchu.
- **Ograniczenia (świadome):** pickup ładunku tylko z przestrzeni systemu źródłowego; undo jest
  globalne (cofa ostatni commit, nie granularnie jeden statek); multi-select Ctrl/Shift na mapie
  — do rozbudowy (okno załadunku pokrywa wygodny multi-pickup transportu).
- **QA:** backend 510 testów zielonych (ruff + mypy --strict); frontend type-check + lint + build.

---

### ✅ E8 Blok A+B — UX akcji taktycznej + ruch z transportem (ukończone)

- **Cel (ustalony z użytkownikiem):** profesjonalna akcja taktyczna z ładnym UI na każdy z 5
  kroków. Start aktywacji wygodnie z prawego dolnego rogu; panel-przewodnik po krokach widoczny
  na MAP VIEW; ruch jako prawdziwy krok z transportem (nie tylko God-Mode).
- **Blok A — UX (frontend):**
  - Przycisk „**Activate system**" w `TurnControls` (prawy dolny róg, przy karcie strategii) —
    reużywa `activateMode`/`activateSystem`; odbiór kliknięcia w kafelek przeniesiony do
    `TurnControls` (żeby działał niezależnie od zakładki panelu). Wskaźnik „Tactical action in
    progress", gdy akcja trwa.
  - `TacticalActionDock` (NOWY) — PŁYWAJĄCY, PRZESUWANY dok na map view (`useDraggablePanel`,
    pozycja w localStorage, dwuklik = reset). Pokazuje panel kroków (reużyty `TacticalActionPanel`)
    TYLKO gdy trwa akcja (`activeSystem != null`). Powód: pływający „Game state" na mapie jest
    `variant="info"` i nie pokazywał kroków — brakowało przewodnika na samej mapie.
  - Pigułki kroków = WSKAŹNIK postępu (lista `<ol>`, nie przełącznik): nie wolno swobodnie skakać
    w przód/w tył. „Next step/Finish" i „End action" wymagają DRUGIEGO kliknięcia (inline confirm
    z ostrzegawczym akcentem) — nie kończy/przeskakuje akcji przypadkiem.
- **Blok B — ruch z transportem (backend + frontend):**
  - **Reguła (zweryfikowana, nie z pamięci):** `RULES.md` 32.3 ze źródłem
    `docs/rules_tirules/R_transport.md`, `R_capacity.md` (tirules2.com). Capacity = limit ładunku
    statku (myśliwce + siły naziemne), ładunek rusza razem i zostaje w przestrzeni (ląduje dopiero
    w INWAZJI), pickup z przestrzeni źródła, blokada CC przy pickupie, limit capacity w systemie.
  - `src/core/movement.py`: nowa `move_fleet(state, grid, registry, from_pos, ships, cargo,
    player_id)` — statki (każdy walidowany R1–R6) + ładunek w ramach wolnej capacity (odczyt
    `capacityValue`/`capacityUsed` z WARIANTU gracza). `move_ships` zostaje jako cienki wrapper
    (zgodność wsteczna). Capacity i klasyfikacja ładunku z danych/UnitDef, nie z pamięci.
  - `src/api/schemas.py`: `MoveShipsRequest` rozszerzony o `ships[]` (pełna flota) i `cargo[]`;
    `base_type` teraz opcjonalny. `src/api/routers/tactical.py`: `/tactical/move` woła `move_fleet`.
  - `tests/test_movement.py`: +6 testów transportu (przewóz myśliwców/piechoty, limit capacity,
    ładunek bez statku, blokada CC, wrapper `move_ships`).
  - `frontend` `MovementStepPanel` (NOWY): dedykowane okno kroku MOVEMENT — wybór systemu
    źródłowego (gdzie gracz ma statki), wybór statków + ładunku z licznikami, ruch do aktywnego
    systemu przez walidowany `moveShips` (422 z powodem → panel komunikatów). Zastępuje poleganie
    na trybie „move" na mapie w kroku ruchu.
- **Ograniczenia (świadome, do rozbudowy):** pickup ładunku tylko z przestrzeni źródła (nie z
  planet ani systemów mijanych); brak usuwania nadwyżki capacity poza ruchem; krok SPACE_CANNON
  na razie z notką (pełna interakcja w kolejnym bloku).
- **QA:** backend 503 testy zielone (ruff + mypy --strict czyste); frontend type-check + lint +
  build czyste.

---

### ✅ Akcja komponentu — trzeci typ akcji fazy akcji + modal „co zagrałeś?" (ukończone)

- **Cel (ustalony z użytkownikiem):** dać opcję zagrania AKCJI KOMPONENTU (trzeci typ akcji
  tury obok strategicznej i taktycznej) i pójść dalej. NA RAZIE bez mechaniki konkretnego
  komponentu — gracz oznacza „zagrałem coś z nagłówkiem Action", co odblokowuje End turn.
- **Reguła (zweryfikowana, nie z pamięci):** `RULES.md` 31.8 ze źródłem
  `docs/rules_tirules/R_component_action.md` (tirules2.com). Akcja komponentu bywa na karcie
  akcji, zdolności frakcji, liderze, technologii, relikcie, karcie eksploracji, promissory
  note, arkuszu frakcji — oznaczona nagłówkiem „Action". To akcja XOR pas w danej turze
  (31.7, R_action_phase).
- **Backend (core → api, silnik-sędzia):**
  - `src/core/component_action.py` (NOWY): `play_component_action(state, player_id?, component_id?)`
    — CZYSTA funkcja. Waliduje jak pozostałe akcje tury (faza ACTION, czyja tura, brak otwartego
    okna, jedna akcja na turę, nie po pasie) i ustawia `took_action_this_turn=True`. Efekt
    konkretnego komponentu NIE jest wykonywany (świadomy szkielet); `component_id` to adnotacja
    „co zagrano" (trafia do etykiety eventu), opcjonalna.
  - `src/api/schemas.py`: `ComponentActionRequest{player_id?, component_id?}`.
  - `src/api/routers/tactical.py`: `POST /tactical/component-action` (commit `_commit_flow`,
    `ValueError`→422). **UWAGA:** nowy endpoint wymaga RESTARTU backendu (stan w pamięci; stary
    proces serwuje stare trasy → 404 „Not Found").
  - `tests/test_component_action.py` (NOWY, 9): core (oznaczenie akcji, walidacje faza/tura/okno/
    po-akcji/po-pasie) + API (odblokowanie End turn, odmowa drugiej akcji).
- **Frontend (lista = WSZYSTKIE komponenty gracza z „Action", zero hardkodowania):**
  - `api/useBoardEditor.ts`: akcja `playComponentAction(playerId?, componentId?)` → endpoint.
  - `TurnControls.tsx`: przycisk „**Component action**" (fioletowy akcent ability) w panelu
    tury — między Pass a End turn; WYŁĄCZONY gdy gracz już działał / spasował / trwa okno.
    Klik otwiera modal „co zagrałeś?".
  - `componentActions.ts` (NOWY) `collectComponentActions(player, handActionCards)`: zbiera
    pozycje z DANYCH — karty akcji z ręki (`actionCardTiming==="Action"`), zdolności frakcji
    (`getAbilityKind==="action"`), liderzy (`abilityWindow`/`abilityText` od „ACTION"), techy
    i relikty (`text` z „ACTION"). Czyta to, co gracz REALNIE ma z web-data `playerData[]`
    (`abilities`/`leaderIDs`/`techs`/`relics`) + ręka. Deduplikacja po (kind,id), ikona + tag
    kategorii per wiersz.
  - Opcja awaryjna „Something else" na końcu listy — dla źródeł nieśledzonych jako posiadane
    (eksploracja / promissory). **TODO (ustalone z użytkownikiem):** docelowo USUNĄĆ „Something
    else" i listować też te źródła — do okodowania, gdy dojdzie ich śledzenie w stanie.
- **Ograniczenie (świadome):** relikty w web-data to na razie `[]` (backend ich nie emituje) —
  pojawią się na liście automatycznie, gdy dojdzie ich model. Efekt komponentu = TODO (dispatch
  po `component_id`, komponent po komponencie, z regułą/źródłem).
- **QA:** backend 497 testów zielonych (ruff + mypy --strict czyste); frontend type-check +
  lint + build czyste.

---

### ✅ Faza akcji: End turn wymaga akcji albo pasu (31.7) + dopieszczony UI tury (ukończone)

- **Reguła:** `RULES.md` 31.7 (źródło `R_action_phase`): w swojej turze gracz wykonuje JEDNĄ
  akcję (strategiczna/taktyczna/komponentu) ALBO pasuje — nie ma „pustej" tury.
- **Egzekucja (sędzia, `turn_flow`):** `end_turn` rzuca 422, gdy gracz nie ma
  `took_action_this_turn` ANI `passed`; `pass_turn` rzuca 422, gdy gracz już wykonał akcję w
  tej turze (pas jest ALTERNATYWĄ dla akcji, nie dodatkiem). Flaga `took_action_this_turn`
  ustawiana przez akcję strategiczną i taktyczną (a od 31.8 także komponentu), zerowana przy
  przekazaniu tury i wejściu w fazę.
- **Fix pustego okna secondary:** gdy kolejka respondentów jest pusta (gra solo / brak innych),
  `play_strategy_card` NIE otwiera okna — inaczej `pending_window` zostawał ustawiony i blokował
  End turn na stałe (bug: zagranie karty → End turn szary na zawsze). Dodano też możliwość pasu
  po akcji strategicznej.
- **UI tury (`TurnControls`):** potwierdzenie pasa w MODALU (pas ≠ koniec tury — trzeba jeszcze
  oddać turę), „nudge" na End turn po pasie/akcji, podpowiedzi jako zawijane „chipy" i STAŁA
  szerokość panelu (koniec przeskakiwania rozmiaru). End turn wygaszony na czas otwartego okna.
- **QA:** backend zielony (pytest + ruff + mypy), frontend type-check + lint + build czyste.

---

### ✅ Standaryzacja sterowania fazami: Pass≠End turn + brama „Next phase" + panel komunikatów (ukończone)

- **Cel (ustalony z użytkownikiem):** ujednolicić przyciski per faza i rozdzielić pas
  od zakończenia tury. Reguła projektowa: `RULES.md` 31.5 (DECYZJA 2026-11).
- **Pas jako akcja (AKCJA):** `turn_flow.pass_turn` tylko OZNACZA gracza
  (`passed=True`), NIE oddaje tury. Turę oddaje jedyny, spójny `end_turn` — także po
  pasie. `end_turn` pomija spasowanych.
- **Jedna flaga `passed` = „skończył swoją część fazy":** resetowana przy KAŻDYM
  wejściu w fazę (`next_phase`). STATUS „Next player" i AGENDA „Pass" wołają
  `/turn/phase-step` (`advance_active_player(mark_passed=True)`); AGENDA „Next player"
  woła `/turn/next-player` (bez oznaczania).
- **Brama „Next phase" (mówca):** `turn_flow.can_advance_phase` — STRATEGY po
  komplecie wyboru; ACTION/STATUS po `all_passed`; AGENDA zawsze. Projekcja do UI przez
  web-data `canAdvancePhase`+`allPassed`; twardy 422 z czytelnym komunikatem w
  `/phase/next`.
- **Przyciski per faza (frontend):** STRATEGY → Next phase (po komplecie); ACTION →
  Pass + End turn + (Next phase po komplecie); STATUS → Next player + Next phase (po
  komplecie); AGENDA → Pass + Next player + Next round. Spójnie w `TurnControls` i
  `GameStatePanel.PhaseControls`.
- **Panel komunikatów (UI):** nowy `PhaseNoticePanel` — osobny box przypięty u GÓRY
  ekranu, styl stołu (hairline + akcent tonu fazy). Prowadzi gracza przez fazę
  (`phaseNoticeMessage`) i pokazuje odrzucone akcje (422). Zastąpił lokalny
  `NoticeBanner` w panelu stanu.
- **Testy:** `test_turn_flow.py` (pas-bez-oddania, phase-step, reset flag,
  can_advance_phase × faza), `test_api.py` (phase-step w statusie, brama
  `/phase/next` w statusie). QA zielone: pytest 480, ruff, mypy; front type-check +
  build.

---

### ✅ Sąsiedzi gracza (Neighbors) w panelu + pole `neighbors` w web-data (ukończone)

- **Cel:** panel gracza (viewer ti4_web) pokazywał ikony sąsiadów, ale backend
  emitował `playerData[].neighbors` jako pustą listę — nic się nie renderowało.
- **Reguła (zweryfikowana, nie z pamięci):** RULES.md 2d na bazie
  `docs/rules_tirules/R_neighbors.md` (tirules2.com). Dwóch graczy jest sąsiadami,
  gdy obaj mają jednostkę lub kontrolują planetę w tym samym systemie LUB w
  systemach sąsiednich (sąsiedztwo przez wormhole wliczone).
- **Kod:** nowy czysty moduł `src/core/neighbors.py` (`neighbors_of`,
  `neighbors_by_player`) nad `GameState` + `HexGrid`. `api/web_data.py`:
  `_build_player_data` dostaje `grid`, liczy sąsiadów raz dla wszystkich graczy i
  emituje ich jako KOLORY (kontrakt viewera — `Neighbors.tsx` mapuje kolor→frakcja).
- **Testy:** `tests/test_neighbors.py` — ten sam system, systemy sąsiednie,
  nie-sąsiednie, kontrola planety bez jednostek, puste stosy, symetria, „gracz nie
  jest własnym sąsiadem".
- **Ograniczenia (RULES.md 2d):** hyperlanes i efekty frakcyjne zmieniające
  adjacency jeszcze nieuwzględnione (jak sekcja 2).
- **Promissory notes „in play area" (RULES.md 2e):** nowe JAWNE pole
  `PlayerState.promissory_notes_in_play` (strefa gracza — notki zagrane, odkryte,
  np. Support for the Throne; odrębne od tajnej RĘKI `private.promissory_notes`).
  Sklasyfikowane jako Public w `player_fields.py`, emitowane do viewera przez
  `promissoryNotesInPlayArea`, edytowalne przez God-Mode (`PlayerEditRequest`).
  Automatyczne przenoszenie notki z ręki do strefy przy zagraniu — przy logice
  transakcji (E8+); dziś zasila operator.
- **Własna frakcyjna notka (loadout) — `customPromissoryNotes` (RULES.md 2e):**
  web-data emitował to pole jako brak (panel nie pokazywał startowej notki frakcji,
  np. Sol Military Support). Dodany helper `_faction_promissory_notes` czyta listę z
  danych frakcji (`FactionDef.promissoryNotes`), nie z pamięci; emitowane w
  `customPromissoryNotes`. Obsłużone edge-case: `neutral` → `[]`, Empyrean → dwie
  notki. Test w `tests/test_web_data.py` (Sol `ms`, Hacan `convoys`).
- **QA:** `pytest` 454 ✅, `ruff` ✅, `mypy` ✅.

---

### 🐛 Naprawa regresji: manifest grafik obejmuje teraz całe `assets/` (ukończone)

- **Objaw:** po migracji grafik z CDN na lokalne plansza nie pokazywała żadnych
  grafik (brak tilesów planet, tokenów, emoji).
- **Źródło błędu:** `src/audit/assets_manifest.py` — stała `DEFAULT_ASSET_DIRS`
  zawierała tylko 9 katalogów i POMIJAŁA kluczowe grafiki planszy (`tiles`,
  `emojis`, `attachment_token` i inne). Manifest frontu (`assetManifest.json`) nie
  zawierał tych ścieżek, więc Resolver_Zasobów (`resolveAsset.ts`) zwracał
  `PLACEHOLDER_URL` dla każdego brakującego wpisu → tile'y planszy znikały.
- **Naprawa (odporna na przyszłość):** `DEFAULT_ASSET_DIRS = None`; przy `dirs=None`
  `list_asset_files()`/`build_manifest()` skanują CAŁE drzewo `assets/` pod kątem
  grafik (`IMAGE_SUFFIXES`), pomijając tylko `EXCLUDED_ASSET_DIRS` (dane/konfiguracja/
  surowce: `data`, `config`, `raw`, `META-INF`, `voices`, `hover_images`, `systems`,
  `planets`, `alias`). Nowe katalogi grafik trafiają do manifestu automatycznie.
  Jawna lista `dirs` zachowuje stare zachowanie (wsteczna kompatybilność).
- **Manifest po regeneracji:** 8666 wpisów (było 9 katalogów), w tym `tiles/` (848),
  `emojis/` (1556), `attachment_token/` (144). Oba manifesty (`audit/` i frontu)
  odtworzone przez `uv run python -m src.audit --write-manifest`.
- **Testy:** `tests/test_audit_diffs.py` — nowy test skanu całości przy `dirs=None`
  oraz test obecności grafik planszy w manifeście projektu.
- **QA:** `pytest` 443 ✅, `ruff` ✅, `mypy` ✅; frontend `npm run build` ✅.

---

### ✅ Baza danych TI4 · 4.1: spójność referencji `core/references.py` (ukończone)
- Nowy moduł `src/core/references.py` (czysty, bez I/O): `UnresolvedReference`,
  `TemplateReference`, `ReferenceReport`, `find_unresolved_references`,
  `build_reference_report`. Sprawdza listy frakcji (`leaders`, `abilities`,
  `promissoryNotes`, `factionTech`, `units`, `startingTech`, `startingTechOptions`),
  `cardIDs` talii kanonicznych (po `type` talii → kategoria celu), `attachmentId`
  eksploracji i `attachmentID` żetonów. Zachowane `missing_planet_references` (R7.4).
- Flaga `leaks_noncanonical` (R7.6) z `LoadReport.skipped_index`: cel istnieje, ale
  pochodzi ze źródła niekanonicznego (przeciek homebrew).
- Placeholder `<color>` (promissory `color.json`) raportowany OSOBNO jako „szablon”
  (`templates`), nie jako nierozwiązana referencja — ⚠️ ZAŁOŻENIE w `RULES.md` 35.
- Wpięcie w `StaticDataRegistry`: atrybut `reference_report` (budowany w `_load()` po
  złożeniu katalogu) i metoda `unresolved_references()`. Nierozwiązane referencje NIE
  blokują startu (dane lokalne, God-Mode działa) — zgłasza je Audytor_Danych (R7.5).
- Realne dane: 22 nierozwiązane referencje do zgłoszenia przez Audytora (deck
  `explores_cpti` → karty niekanoniczne z flagą leak; `attachmentId` eksploracji
  `mirage`/`gamma`/`ionalpha` bez odpowiadającego attachmentu). Rozstrzygnięcie
  (wyjątek/poprawka) należy do użytkownika/konfiguracji audytu.
- QA zielone: `pytest -q` (396 passed), `ruff check src tests`, `mypy src tests`.
- Dalej: 4.2 (`faction_bundle` + `FactionBundle`), 4.3/4.4 (testy referencji).
---

### ✅ Baza danych TI4 · 8.5 + 8.6: testy właściwościowe Audytora (ukończone)
- `tests/test_audit_props.py` (Hypothesis, min. 100 iteracji każdy):
  - **Property 15** (skaner zewnętrznych URL, `audit/locality.find_external_urls`,
    Validates 2.5): zgłasza DOKŁADNIE adresy `http(s)://` spoza `LOCAL_HOSTS` i listy
    dozwolonej (dopasowanie prefiksu po granicy segmentu), numer linii i nazwa pliku
    zgodne z modelem referencyjnym; hosty lokalne nigdy nie wpadają.
  - **Property 12** (luki źródeł kanonicznych z wyjątkami, `audit/diffs.find_gaps`,
    Validates 3.2/6.2/6.3/6.5/11.5): luka = (kategoria, źródło) z licznikiem zero
    (brak klucza = zero) minus potwierdzone wyjątki; wynik posortowany; wyjątki
    pokrywające wszystko → pusto.
  - **Property 13** (różnice to dokładne różnice zbiorów/słowników): `diff_sets`,
    `diff_embedded_ids`, `diff_manifest` (rozłączne `extra`/`missing`, `unused`/`missing`,
    pokrycie różnicy symetrycznej), `diff_counts` (dokładne pary o różnych licznikach,
    `None` jako różnica, pusty ⇔ tablice równe).
- QA zielone: `pytest -q` (373 passed), `ruff check src tests`, `mypy src tests`.
---

### ✅ Baza danych TI4 · 5.1: specyfikacja czasowa `core/timing_spec.py` (ukończone)
- `TriggerKind`, `TimingSpec`, `parse_timing`, `TRIGGER_WINDOW_MAP` (D10: when/after/before/
  instead → `REACTION`, reszta → brak okna; ⚠️ ZAŁOŻENIE w RULES.md 34). Klasyfikacja tylko
  po prefiksach, `raw_text` bez zmian, `play_timing_agrees` z `AGENDA_WHEN`/`AGENDA_AFTER`.
- `LeaderDef.ability_window` (alias `abilityWindow`). `core/timing.py` i `WindowType` bez zmian.
- Testy: `tests/test_timing_spec.py`. Dalej: 5.2 (`build_timing_specs`, `query_timing`).
---

### ✅ Baza danych TI4 · 5.2: specyfikacje czasowe w katalogu + `query_timing` (ukończone)
- `build_timing_specs(tables, leaders, abilities)` w `core/components.py`: buduje
  `TimingSpec` WYŁĄCZNIE z pól JSON (R8.2) — karty akcji (`window`+`phase`+`playTiming`),
  zdolności frakcji (`window`+`windowEffect`→`effect_text`), liderzy (`abilityWindow`).
  Komponenty bez frazy okna nie dostają specyfikacji.
- `ComponentCatalog` dostał opcjonalny parametr `timing_specs` (zgodny wstecz) oraz metody
  `timing_spec(ref)` i `query_timing(trigger, phase=None)` (filtr po wyzwalaczu i fazie,
  wynik posortowany deterministycznie po kategorii i id, R8.4/R8.6).
- Testy: `tests/test_components.py::test_build_timing_specs_i_query_timing`. QA zielone.
---

### ✅ Keleres (3 warianty): przełom i technologie wg Thunder's Edge (ukończone)

- **Błąd:** przełom TE Keleres ma `faction="keleres"`, a warianty to `keleresm/x/a` →
  dopasowanie po id nie znajdowało przełomu. Technologie frakcyjne były z Codexu
  (`iihq`, `asn`), a w TE I.I.H.Q. jest przełomem, a technologią frakcyjną jest Executive Order.
- **Naprawa:** `FactionDef.short_name` (rodzina frakcji), `registry.breakthrough_for_faction`
  (id lub rodzina), `registry._apply_thunders_edge_breakthrough_techs` (przy włączonym TE:
  technologia o nazwie przełomu wypada z `factionTech`, wchodzą techy TE rodziny →
  `executiveorder`, `asn`). Bez TE bez zmian. Testy w `tests/test_registry.py`.
- Nie ruszone: technologie startowe Keleres (zdolność The Tribuni — wybór 2 z cudzych
  startowych) nadal niezaimplementowane (RULES.md 16).

---

### ✅ Wybór frakcji (setup) — iteracja 5: pełnoekranowa scena, nagłówek frakcji, Obsidian (ukończone)

**Pełny opis (układ, pliki, format treści, animacje, gotchas): `UI_WYBOR_FRAKCJI.md`.**

**Cel (uwagi usera):** portret + lore jako JEDNA kompozycja na cały ekran; kolejność uwagi
nazwa → cytat → autor → lore; panel umiejętności szybki; sterowanie człowiek/bot w kroku 1;
osobny, „dziwny" wyjątek dla Obsidiana (lore pismem z gry).

**Co zrobione:**
- **Kreator ma 2 kroki** (`setupSteps.ts`): `name-color` („Gracze": nazwa + kolor + sterowanie
  HUMAN/BOT + trudność z `/engine/config`) i `faction` (scena). Usunięty `Step_Control.tsx`;
  `validateControl` przeniesione do `validateStep("name-color")`. Krok sceny jest w
  `STAGE_STEP_IDS` → renderowany bez ramki kreatora (`StageActions` w `SetupWizard.tsx`),
  `StartScreen` zdejmuje padding/scroll (`.setupScreenStage`).
- **Scena** (`Step_Faction.tsx`): pasek górny (Wstecz · gracze · Start gry), strefa postaci
  (portret przy lewej/dolnej krawędzi ekranu, maska wygaszająca prawą stronę, lore w 2
  kolumnach tuż przy sylwetce, delikatnie na nią nachodzące), wąski panel szczegółów
  (`FactionSummary` na szkle), pionowa lista frakcji (sam klik), osobny wyśrodkowany przycisk
  „Wybierz dla gracza N" na dole.
- **Portret** (`FactionBackdrop.tsx`): pomiar przezroczystego marginesu PNG (canvas) →
  sylwetka równo z krawędzią ekranu + środek sylwetki (`--figure-cx`) do centrowania nagłówka
  i ustawienia lore.
- **Nagłówek** (`FactionHeader`): panel w stylu karty frakcji (ścięte rogi, ikona, nazwa
  Handel Gothic D Bold, cytat w “ ”, autor „— …"), akcent koloru **wyliczany z ikony frakcji**.
  Nowe pola `quote`/`quoteAuthor` w `factionLore.ts`.
- **Lore**: dwie jawne kolumny (`splitLoreColumns`, cięcie na końcu zdania), auto-dopasowanie
  czcionki do boxa bez przewijania, tło lekkie i przezroczyste.
- **Animacje**: postać wyłania się z mgły (5.5 s), potem nagłówek (nazwa → cytat → autor), na
  końcu lore od 4.2 s; panel szczegółów i przycisk wchodzą szybko (~0.4 s). Reduced-motion:
  wolny fade bez ruchu (krótki fade był „niewidoczny").
- **Obsidian** (`glyphLore` w `factionLore.ts`): lore krojem **Lazaxian**, przycisk
  „Przetłumacz" z efektem rozszyfrowania (`GlyphText.tsx`: fala znak po znaku, migotanie,
  glitch, aberracja, skanlinie) + groza (losowe glitche akapitów przez WAAPI, przygasanie,
  błyski fraz `glitchPhrases`, bijące serce tła). Transkrypcja lore jest fanowska (lista
  pominiętych fragmentów w `UI_WYBOR_FRAKCJI.md`).
- Usunięte: `LoreDrawer`/`LorePanel`/`LeaderPortrait`/`LoreBlocks` z `FactionSummary.tsx`
  (przeniesione/zastąpione w `FactionBackdrop.tsx`).

**Pułapki odkryte po drodze** (szczegóły w `UI_WYBOR_FRAKCJI.md` §9): `easing` w WAAPI działa
na cały przebieg (steps(1) = niewidoczny efekt); podmiana `animation` na elemencie z
animacją wejścia restartuje ją; `text-wrap: balance` nie zwęża kontenera; test szerokości
z pseudo-elementem wystającym zbijał czcionkę do minimum.

**QA:** front `tsc` + `eslint` + `build` czyste. Brak testów jednostkowych frontu; efekty
wizualne weryfikowane tylko w przeglądarce.

**Otwarte:** tło sceny (`main_menu.jpg` przyciemnione) i pozycja portretu — user dopuścił
zmiany; uzupełnienie lore/cytatów/autorów pozostałych frakcji w `factionLore.ts`;
`obsidian.png`, `firmament.png` i `Lazaxian-Bold.ttf` mogą być jeszcze niezacommitowane.

---

### ✅ Zadanie 5.1 (feature `player-model-and-setup-ui`) — weryfikacja limitów rąk + poziomów trudności (ukończone)

**Cel (zadanie BADAWCZE, blokujące zad. 8 i 9):** potwierdzić ze źródeł wartości dotąd
oznaczone jako ⚠️ ZAŁOŻENIE (limity rąk, zbiór poziomów trudności bota) i udostępnić je
jako konfigurację czytaną przez `StaticDataRegistry` — bez hardkodowania liczb w regułach.

**Zweryfikowane ze źródeł (tirules2.com / lokalny zrzut `docs/rules_tirules/`):**
- Karty akcji — **max 7** na ręce (`R_action_cards`); efekty gry mogą zmienić limit.
- Tajne obiektywy — **max 3** łącznie zrealizowane + niezrealizowane (`R_objective_cards`).
- Promissory notes — **brak limitu** ręki w regułach (`R_promissory_notes`) → `null`.
- Poziomy trudności bota — **nie istnieją w TI4** (brak w assetach i w regułach) →
  ⚠️ ZAŁOŻENIE, zbiór konfigurowalny `["EASY", "NORMAL", "HARD"]` do potwierdzenia.

**Co zrobione:**
- Nowy asset `assets/config/engine_config.json` (limity rąk + `valid_difficulties`).
- `src/config.py` — ścieżka `ENGINE_CONFIG_PATH`.
- `src/core/models.py` — modele `HandLimits`, `EngineConfig` (Pydantic v2).
- `src/core/registry.py` — ładowanie configu + `hand_limits()` / `valid_difficulties()`.
- `docs/RULES.md` — nowa sekcja 30 (źródła + ⚠️ ZAŁOŻENIE trudności) + wpis w spisie treści.
- `tests/test_registry.py` — 3 testy (limity z assetu, zbiór trudności, fallback bez pliku).

**QA:** 280 testów zielonych, `ruff` i `mypy --strict` czyste.

**⚠️ Decyzja do potwierdzenia przez użytkownika:** zbiór poziomów trudności bota
(`["EASY", "NORMAL", "HARD"]`) — czy właściwy, czy preferowany inny (więcej poziomów,
polskie etykiety, skala liczbowa)? Zmiana wyłącznie w `engine_config.json`, bez kodu.

---

### ✅ Zadanie 9.1 (feature `player-model-and-setup-ui`) — delegacja walidacji do `resolve_players` w endpointach setupu (ukończone)

**Cel:** uczynić endpointy `/game/new` i `/setup/player` cienkimi — cała walidacja/
normalizacja graczy (liczba, nazwy, kolory, frakcje, typ sterowania, trudność, technologie,
losowy dobór frakcji) idzie do `resolve_players` w `core`, a router tylko buduje mapę,
nanosi `ResolvedPlayer` na stan i ustawia nowe pola `PlayerState`.

**Co zrobione (`src/api/routers/game.py`):**
- `post_new_game`: usunięto ręczną pętlę walidacji (frakcja/kolor/slot) i limit „za dużo
  graczy" — delegowane do `resolve_players` (`available_colors` z `AUTO_SLOT_ORDER`,
  `max_players=len(AUTO_SLOT_ORDER)`, `valid_difficulties` z registry). Iteracja po
  `ResolvedPlayer`; auto `home_position` ze slotu, gdy niepodany (R14.3).
- `post_setup_player`: analogiczna delegacja z jednoelementową listą; pula kolorów
  pomniejszona o kolory już rozstawionych graczy, by auto-dobór nie powielił koloru.
- Nowe helpery: `_available_colors`, `_validate_home_position` (R14.4 — istnieje na mapie
  i nieprzypisana; `HTTPException(422)`), `_apply_resolved_player` (woła
  `apply_setup_to_state` + ustawia `display_name`/`control_type`/`difficulty`).
- Usunięto tymczasowe strażniki z zad. 7.1 (`faction_id is None → 404`) — losowa frakcja
  (R8.5) działa teraz przez `resolve_players`.

**Decyzja (kontrakt błędów):** nieznana frakcja daje teraz **HTTP 422** (było 404), spójnie
z resztą błędów walidacji setupu (`ValueError → 422`, design §Error Handling). Zaktualizowano
test `test_setup_unknown_faction_404` → `test_setup_unknown_faction_422` w `tests/test_api.py`.

**QA:** 280 testów zielonych, `ruff` i `mypy --strict` czyste. Anomalia web-data nie wystąpiła.

---

### ✅ Blok E4·UI³ — menu RMB w player-area przy mapie + „Aktywuj system" na kafelku

**Uwagi użytkownika + co zrobione:**

1. **Menu RMB (wyczerp/odśwież) też w player-area przy mapie.** Wcześniej przewiercony był
   tylko `PlayerCardDeck`. Teraz `playerId` (`discordId`) leci też do dwóch pozostałych
   wariantów panelu gracza: `PlayerCardSidebar` (panel boczny osadzony przy mapie — to „player
   area w menu mapy") i `PlayerDeckRow` (wiersz deck). W `PlayerDeckRow` techy idą przez
   `TechGridMobile`, więc dodano mu prop `playerId` przekazywany do `buildTechElementsForType`.
   Efekt: RMB wyczerp/odśwież na planetach/tech/liderach działa we wszystkich panelach gracza.
   (Uwaga: `PlayerStatsArea` na heksach mapy NIE renderuje planet/tech/liderów — tylko
   statystyki — więc tam nic nie dodawano.)

2. **„Aktywuj system" pod RMB na kafelku.** `MapTile` dostał `onContextMenu` → menu z pozycją
   „Aktywuj system", która woła `activateSystem(position)` (POST `/tactical/activate`). Backend
   `core.tactical.activate_system` kładzie żeton dowodzenia AKTYWNEGO gracza w przestrzeni,
   ustawia `active_system` + krok `MOVEMENT`, zdejmuje 1 z puli taktycznej. Pozycja zablokowana,
   gdy brak aktywnego gracza (inaczej 422). Menu omija kafelki hyperlane/embedded; omija też
   tryb klikania (`activateMode`) — woła aktywację wprost (jak przycisk w panelu faz).

**Zweryfikowane E2E:** aktywacja 101 → `command_tokens=[p1]`, `active_system=101`,
`tactical_step=MOVEMENT`, `tactical_cc` 3→2. Reużyty komponent `shared/ui/ContextMenu`.

**QA:** frontend type-check + lint + build czyste; backend 193 testy zielone (bez zmian w tym
bloku — menu woła istniejące endpointy), ruff+mypy czyste. Reguła: RULES.md 27 (rozszerzona).

---

### 🔧 Blok E8-0 — zmiana kierunku na silnik-SĘDZIA + aktualizacja dokumentacji (w toku)

**Kontekst (ustalenie z użytkownikiem 2026-10):** projekt zmienia filozofię z „asystent stołu,
nie sędzia" na **silnik-SĘDZIA egzekwujący reguły TI4 przez kod**. Powody: (1) docelowy bot AI
i tak musi znać i respektować reguły; (2) egzekucja jest wygodniejsza dla gracza (user friendly);
(3) gra przestaje zakładać fizycznie rozłożoną planszę. God-Mode ZOSTAJE jako osobny kanał ręcznej
korekty omijający walidację. Dodajemy OKNA CZASOWE (timing windows) — np. zagranie karty strategii
otwiera pozostałym graczom okno na secondary. Tryb: solo vs boty + hot-seat (docelowo moduł sieciowy),
więc okna pytają graczy po kolei.

**Ustalenia projektowe (z użytkownikiem):**
- Egzekucja idzie DALEKO (wszystkie reguły TI4), ale God-Mode zostaje jako wentyl.
- Walka: pełna, interaktywna (rzuty kośćmi z animacją) — docelowo. Pierwszy rdzeń: rzuty + liczenie
  trafień + okno „przypisz straty", wielorundowo; AFB/space cannon jako kolejne okna.
- Okna czasowe modelowane JEDNOLICIE: stos/okno w `GameState` + kolejka respondentów (`core/timing.py`).
- Kolejność reakcji (POTWIERDZONA przez użytkownika): od gracza po aktywnym, zgodnie z zegarem
  (speaker order); inicjator domyślnie pomijany. Dotyczy secondary i reakcji „when/after".
- `src/engine/` (puste, pod AI) — można przebudować dowolnie.
- E1–E3 działają → dobudowujemy walidację + okna NA ISTNIEJĄCYM, nie przepisujemy.

**Plan zadań E8 (pełny opis: PLAN_PELNA_ROZGRYWKA.md „E8"; reguły: RULES.md 29):**
T1 model okna → T2 ekspozycja w web-data + UI → T3 secondary kart strategii → T4 aktualny gracz
w STATUS/AGENDA + walidacja flow → T5 ruch (core) + walidacja → T6 walidacja aktywacji/planety/
produkcji → T7 walka-rdzeń → T8 walka w UI → T9 AFB + space cannon → T10 dokumentacja + memory.

**Zrobione w tym bloku (T10 częściowo — dokumentacja PRZED kodem, zgodnie z zasadą projektu):**
- [x] `docs/RULES.md` — nowa sekcja 29 (zmiana kierunku „sędzia" + zweryfikowany MODEL OKNA
  czasowego 29.2 ze źródłem LRR „Timing" + AsyncTI4 + potwierdzenie użytkownika; 29.3 aktualny gracz).
- [x] `docs/RULES.md` — sekcje 19–22 i 24 oznaczone bannerem „AKTUALIZACJA KIERUNKU": ich adnotacje
  „asystent, nie sędzia" są UNIEWAŻNIONE (treść zostaje jako referencja mechaniki TI4).
- [x] `docs/PLAN_PELNA_ROZGRYWKA.md` — decyzja E3 zaktualizowana (asystent → fundament pod sędziego),
  dodany etap E8 z listą zadań, sekcja statusu wskazuje E8 jako AKTUALNY.
- [x] `docs/PROGRESS.md` — ten wpis.

**DO ZROBIENIA (następne bloki):**
- [ ] Aktualizacja `.kiro/steering/custodian-engine.md` oraz `docs/README.md` o nowy kierunek
  (wzmianka, że silnik egzekwuje reguły; God-Mode = wentyl) — przy najbliższej okazji.
- [ ] Aktualizacja memory projektu `engine-is-table-assistant-not-referee` → nowy kierunek
  „sędzia + God-Mode jako wentyl" (wymaga narzędzia pamięci — do zrobienia, gdy dostępne).
- [ ] T1: implementacja `core/timing.py` + model okna w `GameState` (pierwszy blok kodu E8).

**QA:** ten blok to wyłącznie dokumentacja (brak zmian w kodzie) — testy backendu bez zmian
(193 zielone z poprzedniego bloku). Kod wejdzie od T1.

### ✅ Blok E8-T1 — model okna czasowego w stanie + core/timing.py (ukończony)

**Cel:** wprowadzić jednolite pojęcie „okno czasowe" (timing window) i „kto teraz reaguje"
do stanu gry — fundament interakcji między graczami (secondary kart strategii, przypisanie
strat w walce, space cannon, reakcje). Reguła modelu: RULES.md 29.2.

**Zrobione:**
- [x] `src/core/game_state.py`: enum `WindowType` (STRATEGY_SECONDARY, COMBAT_ASSIGN_HITS,
  SPACE_CANNON, REACTION) + model `TimingWindow` (queue, cursor, responded, context +
  właściwości `is_complete`, `current_responder`) + pole `GameState.pending_window`.
- [x] `src/core/timing.py` (NOWY): czyste funkcje `state->state`:
  - `build_response_queue(state, initiator, include_initiator=False)` — kolejka od gracza
    PO inicjatorze zgodnie z zegarem (speaker order z `seating_order`; fallback: sorted ids);
    inicjator pomijany lub na końcu;
  - `open_window(state, type, queue, context=)` — otwiera okno (odrzuca zagnieżdżanie);
  - `current_responder`, `respond_current` (waliduje kolejność — odpowiedź poza kolejnością
    → ValueError), `is_window_complete`, `close_window` (idempotentne).
  - Rozdział odpowiedzialności: `timing` = CZYSTA mechanika kolejki; efekty okna (zużycie
    żetonu, usunięcie jednostek) stosuje warstwa wyżej PRZED/PO `respond_current`.
- [x] `tests/test_timing.py` (NOWY, 16 testów): budowa kolejki (po inicjatorze, zawijanie,
  include_initiator, brak seating, inicjator spoza stołu), open/respond/close, błędy
  (zagnieżdżanie, poza kolejnością, brak okna, okno zakończone), round-trip serializacji.

**QA:** 209 testów zielonych (było 193, +16), ruff czysty, mypy --strict czysty.
Ostrzeżenie StarletteDeprecationWarning bez zmian (znane, nieblokujące).

**Następny krok:** T2 — ekspozycja `pending_window` w `web_data` + endpoint `POST /window/respond`
+ panel okna w UI (kto teraz reaguje + przycisk odpowiedzi).

### ✅ Blok E8-T2 — ekspozycja okna czasowego w web-data + endpointy + panel UI (ukończony)

**Cel:** gracz WIDZI otwarte okno czasowe (kto teraz reaguje) i może odpowiedzieć. Spina
model z T1 (core/timing) z frontendem.

**Backend:**
- [x] `src/api/web_data.py`: helper `_pending_window(state)` + pole `gameState.pendingWindow`
  w `_build_game_state`. Tłumaczy okno na kształt dla frontu: `windowType`, `currentResponder`
  (KOLOR gracza, jak `activePlayer`), `currentResponderId` (stabilny player_id do adresowania
  odpowiedzi), `queue` (kolory), `cursor`, `remaining`, `responded`, `context`, `isComplete`.
- [x] `src/api/schemas.py`: `WindowOpenRequest` (typ + queue LUB initiator), `WindowRespondRequest`
  (player_id + decision).
- [x] `src/api/routers/window.py` (NOWY): `POST /window/open` (narzędzie/testowe — wylicza kolejkę
  z inicjatora przez `build_response_queue` lub bierze jawną), `POST /window/respond`
  (`timing.respond_current`, poza kolejnością/brak okna → 422), `POST /window/close`. Router
  zarejestrowany w `app.py`.
- [x] `tests/test_window_api.py` (NOWY, 9 testów): web-data null domyślnie, open eksponuje
  respondenta jako kolor, respond przesuwa kolejkę, poza kolejnością/brak okna/zły typ/zagnieżdżanie
  → 422, close czyści, wszystkie typy okien akceptowane.

**Frontend:**
- [x] `entities/data/types.ts`: typ `PendingWindow` + pole `GameState.pendingWindow`.
- [x] `api/useBoardEditor.ts`: akcje `respondWindow(playerId, decision?)` i `closeWindow()`
  (POST + invalidate web-data → panel odświeża się natychmiast).
- [x] `domains/game-shell/components/GameStatePanel.tsx`: komponent `WindowSection` renderowany
  NA GÓRZE `PlateBody` (okno reakcyjne ma priorytet). Baner „Reaguje: <gracz>" (spójny z pickerem
  fazy strategii), licznik „Pozostało w kolejce", przyciski „Wykonaj"/„Pas" (adresują
  `currentResponderId`); po zakończeniu kolejki przycisk „Zamknij okno". Etykiety typów okien PL.

**Rezultat (zweryfikowany E2E):** open (initiator p1, 3 graczy) → kolejka green,blue (p1 pominięty);
respond green → responder blue; respond blue → isComplete; close → null. Decyzje w T2 to etykiety
(„secondary"/„pass") — efekty konkretnych okien dojdą od T3.

**QA:** backend 218 testów zielonych (było 209, +9), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste. Warn o rozmiarze chunku i StarletteDeprecationWarning bez zmian.

**Następny krok:** T3 — pierwsze realne okno: secondary karty strategii. Zagranie karty otwiera
pozostałym graczom okno; respond dla secondary zużywa żeton strategiczny / pas. Potrzebne
potwierdzenie reguł primary/secondary konkretnej karty (RULES.md — do uzupełnienia ze źródła).

### ✅ Blok E8-T3 — pierwsze realne okno: secondary karty strategii (ukończony)

**Cel:** zagranie karty strategii rozstrzyga PRIMARY aktywnego gracza i OTWIERA okno
secondary dla pozostałych (kolejka po kolei). Pierwsza realna mechanika na modelu okien
(T1/T2). Reguła: RULES.md 30 (źródło: lokalny LRR 2.0 `docs/rules_tirules/R_strategic_action.md`
+ `R_leadership.md`; parametry z `assets/data/strategy_cards/pok.json`).

**Zakres (świadomy szkielet — „make it exist first", z haczykami pod rozbudowę):**
- Leadership primary: +3 żetony dowodzenia (do puli taktycznej — ⚠️ ZAŁOŻENIE: docelowo wybór puli).
- Secondary: mechanika okna (kolejka, wykonaj/pas) działa end-to-end; efekt „wykonaj" to
  NA RAZIE NO-OP (kupno żetonów za wpływ odłożone do modelu wpływu — jawne TODO w kodzie).
- Pozostałe karty: dispatch zwraca „brak efektu" — szkielet okna i tak działa.

**Backend:**
- [x] `src/core/strategic_action.py` (NOWY): `play_strategy_card` (primary dispatch + exhaust
  karty + otwarcie okna STRATEGY_SECONDARY z kolejką pozostałych), `resolve_secondary`
  (dispatch secondary + `timing.respond_current` + auto-zamknięcie po dopełnieniu).
  DISPATCH po inicjatywie (`_PRIMARY_EFFECTS`/`_SECONDARY_EFFECTS`) — rozszerzalny kartą po
  karcie, nie `if` w endpointcie. Kontekst okna niesie `initiative`.
- [x] `src/api/schemas.py`: `StrategySecondaryRequest` (player_id + execute).
- [x] `src/api/routers/strategy.py`: `/strategy/play` przekierowane na `strategic_action`
  (primary + okno; zastępuje dawne „tylko oznacz zagraną"); nowy `/strategy/secondary`.
- [x] `tests/test_strategic_action.py` (10) + `tests/test_strategic_action_api.py` (4).

**Frontend:**
- [x] `api/useBoardEditor.ts`: akcja `strategySecondary(playerId, execute)`.
- [x] `GameStatePanel.tsx` `WindowSection`: przyciski Wykonaj/Pas routowane po TYPIE okna —
  STRATEGY_SECONDARY → `/strategy/secondary` (efekt + kolejka), inne → generyczny `/window/respond`.

**Rezultat (zweryfikowany E2E):** play Leadership (p1) → tactical_cc 3→6, karta zagrana, okno
secondary queue [green,blue] responder p2; secondary p2(exec)→p3, p3(pass)→okno zamknięte (null).

**QA:** backend 232 testy zielone (było 218, +14), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T4 — pojęcie aktualnego gracza w STATUS/AGENDA + twarda walidacja flow
(czyja tura / co teraz wolno). Potem pozostałe karty strategii i model wpływu (odblokuje
realne secondary).

### ✅ Blok E8-T4 — twarda walidacja flow fazy akcji + aktywny gracz (ukończony)

**Cel:** pierwszy element „sędziego" (RULES.md 29.1) — zwykłe akcje flow walidowane TWARDO.
Reguła: RULES.md 31 (źródło: lokalny LRR 2.0 — R_active_player, R_action_phase, R_initiative_order,
R_status_phase, R_agenda_phase).

**Korekta względem pierwotnego zamysłu T4 (wymuszona regułą):** LRR mówi wprost „during the
strategy, status and agenda phases, NO player is the active player". Dlatego NIE wprowadzamy
sztucznego „aktywnego gracza" w STATUS/AGENDA — `active_player_id` pozostaje None (tak jak było).
Kolejność czynności w tych fazach to KOLEJKA (initiative dla statusu, speaker order dla agendy),
która wejdzie w etapach E5/E6 na modelu okien czasowych. T4 kładzie fundament + walidację akcji.

**Backend:**
- [x] `src/core/turn_flow.py`: `_require_action_turn` (faza ACTION + tożsamość aktywnego gracza);
  `end_turn(state, player_id=None)` i `pass_turn(state, player_id=None)` walidują twardo
  (ValueError). `pass_turn` dodatkowo: nie wolno pasować przed akcją strategiczną (gracz z kartą
  musi ją zagrać — `exhausted_strategy_cards`). Alias `initiative_order = turn_order` (status).
  God-Mode omija (osobny kanał). `player_id=None` zachowuje zgodność wsteczną (faza wciąż sprawdzana).
- [x] `src/api/schemas.py`: `TurnActionRequest` (opcjonalny player_id).
- [x] `src/api/routers/flow.py`: `/turn/end`, `/turn/pass` przyjmują body z player_id, mapują
  ValueError → 422.
- [x] `tests/test_turn_flow.py`: fixture gra z ZAGRANYMI kartami (by móc pasować) + 5 nowych
  testów walidacji (zła faza, cudza tura, pas przed akcją strategiczną, pas bez karty dozwolony,
  alias inicjatywy).

**Frontend:**
- [x] `api/useBoardEditor.ts`: `endTurn(playerId?)`/`passTurn(playerId?)` wysyłają player_id.
- [x] `GameStatePanel.tsx`: `PhaseControls` dostaje `activePlayerId` (z `active.discordId`) i
  przekazuje go do endTurn/passTurn — backend waliduje, że to tura tego gracza.

**Rezultat (zweryfikowany E2E):** p2 kończy turę p1 → 422; p1 pasuje bez akcji strategicznej →
422; p1 kończy turę → 200, aktywny p2; end/pass w fazie statusu → 422.

**QA:** backend 237 testów zielonych (było 232, +5), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T5 — ruch jako funkcja core (`core/movement.py`) + walidacja legalności ruchu
(zasięg z UnitDef, anomalie/przejezdność, aktywny system). Pierwsza twarda egzekucja mechaniki
taktycznej.

### ✅ Blok E8-T5 — ruch statków jako funkcja core + walidacja legalności (ukończony)

**Cel:** pierwsza twarda egzekucja mechaniki TAKTYCZNEJ — ruch przestaje być tylko God-Mode,
staje się walidowaną akcją. Reguła: RULES.md 32 (źródło: LRR R_movement + R_tactical_action).

**Reguły egzekwowane (R1–R6):** cel = aktywny system; zasięg ≤ moveValue (z UnitDef); start nie
z systemu z własnym CC (poza aktywnym); trasa nie przez obce statki (fightery też blokują); przez
własne CC można; anomalie (supernova nieprzejezdna, asteroid bez Antimass, nebula nieprzejezdna
jako węzeł pośredni). Pathfinding: BFS po grafie sąsiedztwa z filtrem węzłów pośrednich.

**Backend:**
- [x] `src/core/movement.py` (NOWY): `can_move` (walidacja R1–R6, zwraca powód) + `move_ships`
  (wykonanie: przenosi stos statków ze źródła do aktywnego). BFS `_shortest_legal_distance`.
  Antimass Deflectors: alias `amd` z danych (weryfikowany testem). Czyste funkcje state→state.
- [x] `src/api/schemas.py`: `MoveShipsRequest`.
- [x] `src/api/routers/tactical.py`: `POST /tactical/move` (walidowany; 422 na nielegalny ruch).
  W odróżnieniu od God-Mode `/units/move` (bez reguł).
- [x] `tests/test_movement.py` (NOWY, 10): ruch sąsiedni, brak aktywnego, zasięg, blokada obcymi
  statkami, start z własnym CC, supernova, asteroid+Antimass, fighter bez moveValue, za mało statków.

**Frontend:**
- [x] `api/useBoardEditor.ts`: akcja `moveShips({fromPosition, baseType, count, faction})` →
  `/tactical/move` (ruch walidowany; God-Mode drag-and-drop zostaje jako wentyl bez reguł).

**Zakres (świadomy szkielet, RULES.md 32.1):** ruch pojedynczego stosu jednego typu; transport
przez capacity = TODO (dlatego fighter sam nie rusza — nie ma moveValue, co jest regułowo poprawne);
wybór trasy pod gravity rift = TODO. UI picker ruchu dołożymy osobno (akcja w hooku już jest).

**Rezultat (zweryfikowany E2E):** /tactical/move przenosi destroyer 101→000 (aktywny); ruch bez
aktywnego systemu → 422 „Brak aktywnego systemu".

**QA:** backend 247 testów zielonych (było 237, +10), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T6 — walidacja aktywacji / przejęcia planety / produkcji (koszty, limity,
legalność) — domknięcie egzekucji fazy akcji poza walką.

### ✅ Blok E8-T5b — poprawki zgłoszone przez użytkownika (ukończony)

Trzy uwagi z testów użytkownika, naprawione przed T6:

1. **Ikony jednostek w panelu produkcji za duże (UI).** Sprite jednostki renderował się
   w naturalnym rozmiarze i wylewał poza pudełko 26×26. Naprawa (CSS
   `GameStatePanel.module.css`): `.unitTileIcon` dostał `overflow: hidden`, a wewnętrzny
   kontener sprite'a `transform: scale(0.42)` — ikona mieści się w kafelku.

2. **Nie dało się ZAGRAĆ karty strategii (brakujący przycisk).** Zakładka „Strategiczna" w
   panelu akcji miała tylko notkę „rozlicz przy stole" (relikt starej filozofii), bez przycisku
   wołającego `/strategy/play` (dodany w T3). Naprawa: nowy komponent `StrategicActionControl`
   w `GameStatePanel.tsx` — listuje karty aktywnego gracza i pozwala je zagrać (primary + okno
   secondary). Zagrana karta pokazuje się jako „zagrana".

3. **BŁĄD REGUŁY: Fighter II nie mógł się ruszać.** `movement.can_move` czytał `moveValue`
   z BAZOWEGO wpisu jednostki (`registry.units.get("fighter")` → move=None), ignorując
   ulepszenie. Fighter II (tech `ff2`) ma `moveValue=2`. Naprawa: `can_move` używa teraz
   `combat.resolve_unit_variant(registry, faction, technologies, base_type)` — wariant GRACZA
   wg posiadanych technologii (spójne z walką/produkcją, RULES.md 10/20). Bazowy fighter nadal
   nie rusza się sam (porusza się transportem — capacity TODO), ale Fighter II już tak.
   Zaktualizowano RULES.md 32.1 R2 + nowy test `test_fighter_ii_can_move_with_upgrade`.

**QA:** backend 248 testów zielonych (było 247, +1), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

### ✅ Blok E8-T6 — walidacja aktywacji + produkcji (ukończony)

**Cel:** domknięcie twardej egzekucji fazy akcji poza walką. Reguła: RULES.md 33 (źródło LRR
R_active_system, R_production, R_producing_units). Opcja „b" (ustalona z użytkownikiem): koszt
produkcji SPRAWDZANY, bez realnego wydawania zasobów.

**Aktywacja (RULES.md 33.1) — twardo:**
- [x] `core/tactical.activate_system`: odrzuca aktywację systemu z WŁASNYM żetonem gracza;
  wymaga ≥1 żetonu w puli taktycznej (było: tylko „dekrementuj jeśli >0"). God-Mode
  (`place_command_token`) nadal omija. Zaktualizowany docstring (zdjęta adnotacja „nie waliduje").

**Produkcja (RULES.md 33.2) — limit/blokada twardo, koszt jako sprawdzenie:**
- [x] `src/core/models.py`: pola `production_value` (int|str) + `basic_production` w UnitDef
  (dane: dok bazowy „+2" = zasoby planety + 2; Saar dok = 5 liczbowo).
- [x] `src/core/production.py` (NOWY): `production_limit` (suma PRODUCTION jednostek gracza w
  aktywnym systemie; modyfikator „+N" rozwiązywany względem planety doku), `available_budget`
  (gotowe planety + TG), `validate_production` (koszt ≤ budżet, liczba ≤ limit, blokada statków
  przy obcych statkach; fighter/infantry para za koszt). Czyste funkcje.
- [x] `src/api/schemas.py`: `ProduceOrderItem` + `ProduceRequest`.
- [x] `src/api/routers/tactical.py`: `POST /tactical/produce` (waliduje całe zamówienie → 422,
  przy sukcesie stawia jednostki przez edit_units). Obok God-Mode edit-units (bez reguł).
- [x] `tests/test_production.py` (NOWY, 9) + aktualizacja `tests/test_tactical.py` (testy
  walidacji aktywacji zamiast idempotentności).

**Frontend:**
- [x] `api/useBoardEditor.ts`: akcja `produce(faction, orders)` → `/tactical/produce`
  (walidowana; God-Mode edit zostaje jako wentyl). Pełny picker produkcji w panelu = refinement.

**Zakres (świadomy, opcja „b"):** koszt to SPRAWDZENIE (budżet = gotowe planety + TG), bez
wyczerpywania planet/zdejmowania TG — realne wydawanie dojdzie z modelem wpływu. Component
limitations (rezerwy) = TODO.

**Rezultat (zweryfikowany E2E):** produkcja 2 cruiserów (koszt 4, budżet 4, limit 6) → 200 +
postawione; 3 cruisery (koszt 6 > budżet 4) → 422 „Za mało zasobów".

**QA:** backend 258 testów zielonych (było 248, +10), ruff + mypy --strict czyste. Frontend
type-check + lint + build czyste.

**Następny krok:** T7 — walka: rdzeń (rzuty seedowalnym RNG + liczenie trafień + okno „przypisz
straty", wielorundowo). Pierwsza wersja pełnej walki rozstrzyganej przez silnik.

### ✅ Blok E8-T6b — podłączenie walidacji do UI + komunikaty + poprawka ikon (ukończony)

Trzy problemy zgłoszone przez użytkownika: walidacja T6 istniała w backendzie, ale UI jej
nie wołało (szło przez God-Mode), brak komunikatów, ikony produkcji nadal złe.

1. **Walidacja nie działała w UI, bo panele szły przez God-Mode.** Produkcja (przyciski +)
   wołała `editUnit` (God-Mode, bez reguł) zamiast `/tactical/produce`. Naprawa:
   `ProductionPanel` — dodawanie (`+`) idzie teraz przez walidowany `produce(faction, orders)`
   (koszt/limit/blokada, RULES.md 33.2); usuwanie (`−`) zostaje God-Mode (korekta, nie reguła).
   Aktywacja już wołała `/tactical/activate` (walidowane w T6), brakowało tylko komunikatu.

2. **Brak komunikatów o odrzuceniu.** Dodano slice `notice` w `appStore` (setNotice/clearNotice)
   + komponent `NoticeBanner` na górze panelu gry + CSS. `useBoardEditor.post()` parsuje `detail`
   z 422 i ustawia notice — każda odrzucona akcja (np. „Nie można aktywować systemu, w którym
   masz już żeton dowodzenia", „Za mało zasobów") pokazuje baner. Wcześniej błąd był cicho połykany.

3. **Ikony jednostek w produkcji źle skalowane.** Poprzedni `transform: scale(0.42)` obcinał
   grafikę. Naprawa: zdjęto transform; sprite (`.unit-sprite`, skalowany procentowo do własnego
   pudełka) dostał jawny rozmiar 24×24 w `.unitTileIcon` — bez obcinania.

**Rezultat (zweryfikowany E2E):** ponowna aktywacja systemu → 422 „Nie można aktywować systemu,
w którym masz już żeton dowodzenia" (pokazane jako baner); produkcja ponad budżet → baner
„Za mało zasobów".

**QA:** backend 258 testów zielonych (bez zmian logiki), ruff + mypy czyste. Frontend
type-check + lint + build czyste.

### ✅ Blok E8-T6c — wskaźnik limitu produkcji (sprocket) + komunikat limitu (ukończony)

Dwie uwagi użytkownika: pokazać w panelu wartość PRODUCTION w systemie z ikoną AsyncTI4
(koło zębate „production_representation.png") oraz komunikat przy przekroczeniu limitu.

**Backend:**
- [x] `src/api/schemas.py`: `ProductionHelpResponse.production_limit` (alias `productionLimit`).
- [x] `src/api/routers/tactical.py`: `GET /tactical/production` liczy limit przez
  `production.production_limit` (suma PRODUCTION jednostek gracza w aktywnym systemie, z
  rozwiązaniem modyfikatora doku „+N" względem planety). Komunikat limitu już działał
  (`validate_production` → „Limit produkcji przekroczony" → 422 → baner notice z T6b).

**Frontend:**
- [x] `api/useBoardEditor.ts`: `ProductionHelp.productionLimit`.
- [x] `GameStatePanel.tsx` `ProductionPanel`: nagłówek pokazuje wskaźnik PRODUCTION — koło
  zębate (ta sama grafika CDN co na mapie, `cdnImage("/tiles/production_representation.png")`)
  z nałożoną liczbą = limit sztuk. Obok dotychczasowe „X zasobów".
- [x] CSS: `.prodStats/.prodLimit/.prodLimitIcon/.prodLimitValue` (ikona 22×22 + liczba z obrysem).

**Rezultat (zweryfikowany E2E):** `/tactical/production` zwraca `productionLimit=6` (dok „+2" na
Jord res 4); produkcja 7 piechoty > limit 6 → 422 „Limit produkcji przekroczony" (baner).

**QA:** backend 258 testów zielonych, ruff + mypy czyste. Frontend type-check + lint + build czyste.

### ✅ Blok „domknięcie fazy strategii" (feature `strategy-phase-complete`, ukończony)

**Cel:** domknąć FAZĘ STRATEGII TI4 (PoK, zestaw `pok`) na istniejącym fundamencie E1–E2 —
DOBUDOWA walidacji i brakującej logiki (silnik-SĘDZIA, RULES.md 29/13), NIE przepisywanie.
Spec: `.kiro/specs/strategy-phase-complete/`. Reguła przed kodem (zasada projektu).

**Reguła (RULES.md 13 rozszerzona, źródło: tirules `R_strategy_phase.md` + LRR „Strategy Phase"):**
- `Pick_Count` zależny od liczby graczy: **3–4 → 2 karty/gracz**, **5–8 → 1 karta/gracz**;
  liczba graczy <3 lub >8 = NIEOBSŁUGIWANA (błąd, bez zmiany stanu).
- **Druga runda wyboru (tylko 3–4 graczy):** po pierwszej rundzie wybór wraca do mówcy i idzie
  ponownie w speaker order, aż każdy ma `Pick_Count` kart (mechanicznie: „następny wybierający"
  = pierwszy w speaker order poniżej `Pick_Count`, bez osobnego licznika rund).
- **Walidacja przejścia STRATEGY→ACTION:** fazy nie można zakończyć, dopóki każdy gracz nie ma
  `Pick_Count` kart; kolejność tur fazy akcji ustala inicjatywa (RULES.md 9).

**Backend (`core/` → `api/`, QA zielone po każdym bloku):**
- [x] `core/strategy_phase.py`: nowa `pick_count` (3–4→2, 5–8→1; <3/>8 → `ValueError`);
  przebudowany `next_strategy_picker` (pierwszy w speaker order poniżej `Pick_Count`; <3 graczy
  → `None` przez złapanie `ValueError` — zgodność wsteczna wywołań wewnętrznych); rozszerzony
  `pick_strategy_card` (walidacja kolejności + limitu `Pick_Count` + sortowanie listy kart,
  zachowane dotychczasowe walidacje i transfer TG); nowa `ensure_strategy_complete` (kontrola
  kompletu wyboru); guard w `accumulate_unpicked_tg` (akumulacja TG dopiero po zakończeniu fazy);
  nowa `validate_strategy_card_set` (komplet/unikalność 8 kart, `Initiative` 1–8).
- [x] `core/turn_flow.py`: nowa `strict_initiative_order` (permutacja graczy wg rosnącej
  inicjatywy; gracz bez karty → `ValueError`); `next_phase` przy STRATEGY→ACTION woła
  `ensure_strategy_complete` PRZED zmianą fazy i ustawia `active = strict_initiative_order[0]`.
- [x] API: `routers/flow.py` — `/phase/next` i `/round/next` owinięte w try/except → HTTP 422;
  `routers/strategy.py` — `GET /strategy/cards` z guardem rejestru (`validate_strategy_card_set`)
  i kompletu pól per-karta → 422; `web_data.py` — ADDYTYWNE pole pochodne `strategyPickCount`
  (`_safe_pick_count` łapie `ValueError` → `None`, web-data nie rzuca).
- [x] Testy backendu zaktualizowane pod `Pick_Count=2` i fikstury ≥3 graczy (zadanie 5);
  5–8-osobowe scenariusze bez zmian. Pełny pytest zielony.

**Frontend (bramka type-check + lint + build):**
- [x] `GameStatePanel`: `allPicked` liczone z `gameState.strategyPickCount`
  (`scs.length >= pickCount`) zamiast samej obecności kart.
- [x] NOWY `StrategyCardTable` (karty „na stole" z pełną grafiką, stanem wybrania + właściciel,
  wskazaniem pickera/mówcy, banerem fazy; interakcja wyboru z blokadą poza kolejnością i fallbackiem
  tekstowym przy braku/błędzie grafiki). Montaż w `MapView`/`PannableMapView`, render tylko w fazie
  strategii.
- [x] NOWY `PhaseTransitionBanner` (baner przy zmianie GŁÓWNEJ fazy — jednorazowo na przejście,
  animacja fade/scale, auto-ukrycie ≤5 s, `pointer-events: none`, fallback tekstowy; dźwięk
  `phase_change.mp3` z cichą degradacją — 404/zablokowany autoplay nie psują banera).

**Decyzje projektowe:**
- **Silnik-SĘDZIA:** wszystkie nowe walidacje reguł rzucają `ValueError` → mapowane na HTTP 422
  (RULES.md 29.1). Nielegalny wybór / przedwczesne przejście / niespójny zestaw = odrzucone bez
  zmiany stanu.
- **God-Mode NIETKNIĘTY** jako wentyl — kanał ręcznej korekty (`/god-mode/patch`,
  `core/board_edit.*`) nadal omija walidację reguł.
- **Grafika kart** pobierana z danych `Strategy_Router` (`imageURL`, źródło ti4ultimate.com);
  fallback tekstowy, gdy brak/błąd.
- **Priorytet źródeł kart strategii (uzupełnienie):** ustalono `thunders_edge > pok > codex4..1 >
  base` — gdy wiele włączonych źródeł dostarcza wariant tej samej karty (Construction 4 / Warfare 6),
  wygrywa wariant z najwyższego źródła (Thunder's Edge). Dodano FALLBACK GRAFIKI w lookupie frontu
  (`entities/lookup/strategyCards.ts`): gdy wariant najwyższego źródła nie ma obrazu, UI bierze
  grafikę wariantu o tej samej initiative z niższego źródła (treść/parametry bez zmian). Usunięto
  hardkodowaną `defaultStrategyCardIdMap`. Szczegóły: RULES.md 14.
- **Baner/dźwięk fazy:** zasób pod ścieżką względną `/static/extra/...` (baner) i
  `/static/extra/sounds/...` (dźwięk); dźwięk i baner rozłączone (degradacja niezależna).

**QA (pełna bramka — wszystko zielone):** backend `uv run pytest -q` → **262 passed**;
`uv run ruff check src tests` → czyste; `uv run mypy src tests` → czyste (61 plików). Frontend:
`npm run type-check` → czyste; `npm run lint` → czyste; `npm run build` → OK (znana, nieblokująca
notka o rozmiarze chunku). Ostrzeżenie `StarletteDeprecationWarning` bez zmian (znane).

**Refaktoryzacja po przeglądzie semantycznym (`semantic-review/2026-11-01-005022-strategy-phase-review.md`,
znaleziska #1/#2/#3/#4/#7, czysto backendowa, zero zmian kontraktu z frontem):**
- [x] **Spójna obsługa liczby graczy spoza 3–8 w guardzie akumulacji (#2/#3):** `accumulate_unpicked_tg`
  woła teraz `ensure_strategy_complete` (które woła `pick_count` BEZPOŚREDNIO) zamiast wnioskować
  z `next_strategy_picker(state) is not None`. Dawny guard był dziurawy: `next_strategy_picker`
  łapie `ValueError` z `pick_count` i zwraca `None`, więc przy 2 graczach `/round/next`
  przepuszczało akumulację. Teraz <3/>8 graczy → `ValueError` (odrzucone), niekompletny wybór →
  zachowany komunikat „Nie można akumulować: faza strategii niezakończona.".
- [x] **Twarda kontrola `seating_order == players` przy przejściu STRATEGY→ACTION (#1):**
  `ensure_strategy_complete` sprawdza (dla niepustej `seating_order`) spójność ze zbiorem graczy
  i daje czytelny błąd ZANIM `strict_initiative_order` rzuci mylące „Gracz X nie ma karty"
  (realny edge-case: God-Mode dodaje gracza bez aktualizacji listy miejsc). Puste `seating_order`
  nietknięte.
- [x] **Walidacja pól karty przeniesiona do `core/` (#4):** `_ensure_card_fields_complete` z
  `api/routers/strategy.py` → nowa czysta funkcja `core.strategy_phase.ensure_card_fields_complete`,
  wołana wewnątrz `validate_strategy_card_set` (dostępna też dla przyszłego `ai/`). Router tylko
  woła `validate_strategy_card_set` i mapuje `ValueError`→422 (kontrakt bez zmian).
- [x] **Testy brzegowe (#7):** `tests/test_strategy_phase.py` + `tests/test_turn_flow.py` —
  rozjazd seating_order↔players, akumulacja przy 2 graczach, zachowany komunikat niekompletnego
  wyboru, walidacja pól karty w core, regresja poprawnego stanu 3 graczy.
- **QA po refaktorze:** `uv run pytest -q` → **269 passed**; ruff + mypy czyste.

**Znalezisko #5 — wybór wariantu kart strategii przeniesiony do CORE (część backendowa):**
Wcześniej priorytet źródeł kart (`thunders_edge > pok > codex4..1 > base`) żył TYLKO we froncie
(`entities/lookup/strategyCards.ts`), a backend zwracał zawsze twardy zestaw `pok` — przez co
`/strategy/cards` i web-data serwowały `pok4construction`/`pok6warfare` nawet przy włączonym
Thunder's Edge. Teraz reguła wyboru kanonicznego zestawu jest w `core/`:
- [x] `core/registry.py`: nowa czysta metoda `active_strategy_card_set_alias()` — wybiera alias
  zestawu o NAJWYŻSZYM włączonym źródle wg `_STRATEGY_SET_SOURCE_PRIORITY`
  (`thunders_edge > pok > codex4..1 > base`; homebrew ignorowane; fallback `pok`). `strategy_card_set`
  ma teraz `set_alias: str | None = None` — bez jawnego aliasu zwraca zestaw kanoniczny.
- [x] `core/strategy_phase.py`: `available_initiatives`, `pick_strategy_card`, `accumulate_unpicked_tg`,
  `validate_strategy_card_set` — domyślny `set_alias` zmieniony z twardego `"pok"` na `None`
  (kanoniczny). Jawny alias nadal dostępny (kompatybilność/testy).
- [x] `api/web_data._build_strategy_cards`: `registry.strategy_card_set()` bez aliasu → automatycznie
  kanoniczny (zmiana kontraktu POŻĄDANA: te4/te6 przy TE).
- **Zweryfikowane:** przy obecnym `enabled_sources.json` (base, pok, codex1–4, thunders_edge)
  `active_strategy_card_set_alias()` → `"te"` (Construction=`te4construction`, Warfare=`te6warfare`,
  reszta PoK); bez TE → `"pok"`. Karty `te4construction`/`te6warfare` mają KOMPLET pól
  (nazwa/primary/secondary/kolor), więc `validate_strategy_card_set` na zestawie TE przechodzi.
- [x] Testy: `tests/test_registry.py` (wybór aliasu + skład kanonicznego zestawu + jawny alias) +
  `tests/test_strategy_phase.py` (walidacja kanonicznego zestawu TE). Reguła: RULES.md 14.
  Część frontendowa (konsumpcja kanonicznych wariantów) pójdzie osobno.

### ✅ Blok E8-T6d — wskaźnik produkcji NA KAFELKU (nie w panelu) (ukończony)

Korekta po uwadze użytkownika: wskaźnik PRODUCTION (koło zębate) ma się pokazywać NA KAFELKU
mapy (jak w AsyncTI4), nie w panelu produkcji. Funkcjonalność renderu już istniała we froncie
(`ProductionIndicator` + `SystemIndicatorsLayer` w `MapTile`), ale NIE dostawała danych — backend
wysyłał `tileUnitData[pos].production = {}` (puste), więc `Math.max([])` = -Infinity i wskaźnik
nigdy się nie renderował (`highestProduction > 0` fałszywe).

**Backend (naprawa źródła danych):**
- [x] `src/core/production.py`: wydzielono `system_production_value(state, grid, registry,
  player_id, position)` (suma PRODUCTION w DOWOLNYM systemie); `production_limit` deleguje do
  niego dla `active_system`.
- [x] `src/api/web_data.py`: helper `_tile_production` wypełnia `tileUnitData[pos].production`
  mapą `{kolor_gracza: wartość}` (pomija ≤0; klucz = kolor jak reszta sygnałów mapy). Import
  `production`.

**Frontend (cofnięcie wskaźnika z panelu):**
- [x] `GameStatePanel.tsx`: usunięto wskaźnik PRODUCTION z nagłówka panelu produkcji (dodany
  błędnie w T6c) + nieużywany import `cdnImage`. Panel pokazuje tylko „X zasobów".
- [x] `GameStatePanel.module.css`: usunięto CSS `.prodStats/.prodLimit/...`.
  (`ProductionHelpResponse.production_limit` zostaje w kontrakcie — nieszkodliwe, może się przydać.)

**Rezultat (zweryfikowany E2E):** `tileUnitData["000"].production = {"red": 6}` (dok „+2" na Jord
res 4 = 6). Mapa renderuje koło zębate z „6" na kafelku — jak w AsyncTI4.

**QA:** backend 262 testy zielone, ruff + mypy czyste. Frontend type-check + lint + build czyste.

### ✅ Blok E8-T7 — zasada „zawsze czyjaś tura" + mówca ogłasza tranzycję (ukończony)

**Cel (ustalony z użytkownikiem):** fundament pod docelowo do 6 ludzkich graczy (hot-seat /
sieć) i bota AI — w toczącej się partii ZAWSZE wiadomo, czyja jest tura. Koniec tury/fazy to
TRANZYCJA ogłaszana przez mówcę, nie stan „niczyjej tury" (`None`).

**Decyzja projektowa (⚠️ odejście od LRR) — RULES.md 31.4:** oficjalna reguła (R_active_player)
mówi „during the strategy, status and agenda phases, no player is the active player". Świadomie
od niej odchodzimy: `active_player_id` w partii ≥2 graczy nigdy nie jest `None` (także w STRATEGY
/ STATUS / AGENDA). `None` pozostaje legalny TYLKO poza rozgrywką (0–1 graczy, pusty setup,
God-Mode budujący stół). Brak auto-tranzycji: przejście fazy ogłasza mówca przez `/phase/next`.

**Core (`turn_flow.py`):**
- [x] `end_turn`/`pass_turn`: gdy brak następnego niespasowanego → `active_player_id = speaker_id`
  (faza nadal ACTION), zamiast `None` + skok do STATUS. Okna czasowe końca tury/fazy zostają otwarte.
- [x] `next_phase`: STATUS/AGENDA → aktywny = pierwszy wg inicjatywy (`turn_order`), fallback mówca;
  STRATEGY → picker ∥ mówca; ACTION bez zmian (initiative[0]).
- [x] `next_round`: picker ∥ mówca.

**Core (`strategy_phase.py`):**
- [x] `pick_strategy_card` / `reset_strategy_cards`: po komplecie wyboru aktywny = mówca (nie `None`).

**API (`routers/flow.py`):**
- [x] `/phase/next` przyjmuje opcjonalny `player_id`; gdy podany, musi być `speaker_id` (inaczej 422,
  „Only the speaker announces a phase transition"). Pominięty = zgodność wsteczna. God-Mode omija.
- [x] `/speaker/set`: w STRATEGY po komplecie wyboru aktywny = nowy mówca (nie `None`).

**Projekcja (`web_data.py`):**
- [x] `_effective_active_id`: zaktualizowany komentarz — stan active+passed powstaje teraz także
  normalnie (wszyscy spasowali → aktywny = mówca, też `passed`). Panel nie podświetla wtedy
  aktywnego (spójność `active`/`passed`), ale `isSpeaker` niesie informację „kto ogłasza".

**Testy:** +7 (łącznie 467 zielonych). `test_turn_flow.py`: STATUS/AGENDA wskazują initiative[0];
pas ostatniego gracza → ACTION + mówca (bez skoku do STATUS); end_turn nie wyczerpuje aktywnego.
`test_strategy_phase.py`: po komplecie wyboru aktywny = mówca. `test_api.py`: `/phase/next`
odrzuca nie-mówcę (422), przyjmuje mówcę, działa bez `player_id` (legacy).

**QA:** `uv run pytest -q` (467 passed), `uv run ruff check src tests` (All checks passed!),
`uv run mypy src tests` (Success, 110 plików).

**Otwarte (do decyzji użytkownika):** czy panel tury ma podświetlać mówcę jako „active" także
gdy wszyscy spasowali (dziś: null, bo mówca jest passed — zachowanie z Bug 7). Zmiana dotyczy
tylko warstwy wyświetlania, nie stanu.

### ✅ Blok local-ti4-data-foundation 1.1 — `core/sources.py` + stałe w `config.py` (ukończony)
- `src/config.py`: katalogi danych nowych kategorii (karty akcji, agendy, cele, attachmenty, eksploracje, relikty, promissory, żetony, anomalie graniczne, wydarzenia, karty generyczne, talie), `AUDIT_DIR`, `EFFECTS_STATUS_PATH`, `FRONTEND_DIR`.
- `src/core/sources.py`: `SOURCE_PRIORITY` (RULES.md 14), `source_rank`, `known_source_ids`, `validate_enabled_sources`, `UnknownSourcesError`.
- `StaticDataRegistry`: `_STRATEGY_SET_SOURCE_PRIORITY` = `SOURCE_PRIORITY` (bez zmiany zachowania); `__init__` waliduje źródła przed `_load()`.
- Test `test_registry` używał nieistniejącego źródła `anarchy` → zastąpione znanym homebrew `absol`. Nowe testy: `tests/test_sources.py`.
### ✅ Blok local-ti4-data-foundation 8.1 — `src/audit/locality.py` + pliki konfiguracyjne `audit/` (ukończony)
- `src/audit/locality.py`: czyste funkcje nad tekstem `find_reference_path_usage` (literały kodu poza docstringami; nazwy folderów referencyjnych podaje wołający, nie ma ich w kodzie produkcyjnym), `find_outside_root_reads`, `find_external_urls` (hosty lokalne + lista dozwolona po granicy segmentu) oraz cienka otoczka (`collect_sources`, `scan_external_urls`, `load_allowlist`, `load_unused_asset_dirs`).
- `audit/expected_gaps.json` (`[]`), `audit/external_url_allowlist.json` (D2), `audit/unused_asset_dirs.json` (D8, nic nie jest usuwane).
- Test: `tests/test_audit_locality.py`. Skan realnego `src/` i `scripts/`: zero odwołań do folderów referencyjnych w kodzie i zero odczytów spoza korzenia.
### ✅ Blok local-ti4-data-foundation 2.1 — `core/components.py` (ukończony)
- `src/core/components.py`: `ComponentCategory`, `ComponentRef`, `ComponentBase` (pole `raw` z surowym JSON), modele kategorii (`ActionCardDef`, `AgendaDef`, `ObjectiveDef`, `AttachmentDef`, `ExplorationDef`, `RelicDef`, `PromissoryNoteDef`, `TokenDef`, `BorderAnomalyDef`, `GalacticEventDef`, `GenericCardDef`, `DeckDef`).
- `CATEGORY_SPECS` = jedyne miejsce kształtów JSON (`alias` vs `id`, pola tekstowe, pole okna); `build_component` łączy `flavorText`/`flavourText`, `cardIDs` rozcina po białych znakach. Zero hardkodowanych komponentów.
- `ComponentCatalog`: `get`, `all`, `counts`. Test: `tests/test_components.py`. Wszystkie realne wpisy 13 kategorii walidują się w modelach.
### ✅ Blok local-ti4-data-foundation 1.2 — test właściwościowy walidacji źródeł (ukończony)
- `tests/test_source_selection_props.py`: Property 3 (Hypothesis, 100 przykładów) — `validate_enabled_sources` zgłasza `UnknownSourcesError` wtedy i tylko wtedy, gdy są identyfikatory spoza zbioru znanych, a wyjątek wymienia dokładnie te nieznane. Validates: Requirements 4.2.
### ✅ Blok local-ti4-data-foundation 2.2 — `core/component_loader.py` (ukończony)
- `src/core/component_loader.py`: `EntryOrigin`, `iter_entries_with_origin`, `LoadReport` (`loaded`, `skipped`, `skipped_index`, `sourceless`, `invalid_id`, `conflicts`), czysta `select_entries` (filtr po `source`, wpisy bez źródła, wybór po `source_rank`, deterministyczny remis po `(file, index)`), `load_components(enabled)` z walidacją modelu i `DataValidationError(kategoria, plik, id)`.
- `load_components` przyjmuje opcjonalną tabelę `specs` (domyślnie `CATEGORY_SPECS`), co pozwala testować na `tmp_path`. Loader jeszcze nie jest wpięty w rejestr (zadanie 2.3).
- Test: `tests/test_component_loader.py`.

### ✅ Blok local-ti4-data-foundation 7.1 — `core/effects_registry.py` (ukończony)
- `src/core/effects_registry.py`: `EffectStatus` (`not_implemented`/`implemented`/`manual`), niemutowalny `EffectRegistry` (`status_of` z domyślnym `NOT_IMPLEMENTED`, `with_status` zwraca nowy rejestr, `load` z brakiem pliku = pusty, `to_json_dict`), `coverage` per kategoria (CoverageRow: total/implemented/manual/percent) i `resolve_action_card_ref` po `automationID` (z deterministycznym remisem, zapasowo po aliasie). Czysta struktura danych bez importów FastAPI/HTTP; zero logiki efektów jakiejkolwiek karty.
- `assets/config/effects_status.json` (`{}`) z wyjątkiem w `.gitignore` (obok `engine_config.json`).
- Test: `tests/test_effects_registry.py`. QA zielone dla moich plików (pytest 332 passed, ruff + mypy czyste). Wymagania: 9.1–9.7.
### ✅ Blok local-ti4-data-foundation 8.2 — moduły różnic Audytora (ukończony)
- `src/audit/diffs.py`: `IdDiff`, `diff_sets`, `diff_counts` (dokładne różnice tablic liczników kategoria×źródło, regresja względem baseline), `find_gaps` (pary kategoria/źródło kanoniczne z zerem, minus `audit/expected_gaps.json`), `load_expected_gaps`, `load_baseline_counts`.
- `src/audit/assets_manifest.py`: `build_manifest`/`write_manifest`/`load_manifest_paths` (lista `{path,size,sha256}` grafik, ścieżki POSIX względem `assets/`), `diff_manifest` (`missing`/`unused`), `list_asset_files`. Grafiki poza repo (D1) — manifest to jedyny wersjonowany ślad.
- `src/audit/frontend_data.py`: `extract_embedded_ids` (regex po `alias`/`id` tylko na najwyższym wcięciu wpisu TS), `scan_embedded_ids`, `diff_embedded_ids` (`extra`/`missing`, R11.5) nad danymi `frontend/src/entities/data/*.ts`.
- Czyste funkcje bez I/O (poza `load_*`/`build_manifest`), gotowe pod testy właściwościowe 8.6. Test przykładowy: `tests/test_audit_diffs.py`.
- QA: pytest (346 + 7 nowych) zielone, ruff + mypy czyste na plikach bloku.
### ✅ Blok local-ti4-data-foundation 7.2 — `core/rules_links.py` (ukończony)
- `src/core/rules_links.py`: `RulesTopic` (code/category/title), `RulesTopicIndex` z `from_json` (czyta tylko metadane `topics` z `tirules.json`; brak lub uszkodzony plik = pusty indeks) i `match`. Dopasowanie deterministyczne przez RÓWNOŚĆ znormalizowanej nazwy/aliasu (casefold + usunięcie znaków niealfanumerycznych) z tytułem, kodem lub kodem bez prefiksu `X_`; plus temat kategorialny z `CATEGORY_TOPIC_HINTS`. Brak rozmytego dopasowania — brak trafienia daje pustą listę. Moduł czyta wyłącznie metadane tematów; treść tematu to nadal `rules_content.py`, opisy kart pochodzą z JSON (R10.4).
- `CATEGORY_TOPIC_HINTS` mapuje kategorię komponentu (napis = wartość `ComponentCategory`, bez zależności od `components.py`) na kody tematów kategorialnych; nieistniejący w indeksie temat jest pomijany.
- Test: `tests/test_rules_links.py` (normalizacja, równość po tytule/kodzie, brak zgadywania, podpowiedź kategorialna + dedup, pusty indeks przy braku/uszkodzeniu pliku, realny zrzut `docs/rules_tirules/tirules.json`). QA zielone dla moich plików (pytest 346 passed w pełnym zestawie, ruff + mypy czyste dla `rules_links.py` i jego testu). Wymagania: 10.1–10.4.

### ✅ Blok local-ti4-data-foundation 7.4 — testy właściwościowe rejestru efektów (ukończony)
- `tests/test_effects_registry_props.py`: Property 10 i Property 11 (Hypothesis, 200 przykładów każdy).
- Property 10 (Rejestr efektów — domyślny status i zapis statusu): dla referencji spoza kluczy `status_of` zwraca `NOT_IMPLEMENTED`; `with_status` → `status_of` zwraca ustawiony status, statusy innych referencji w nowym rejestrze bez zmian, a rejestr wejściowy pozostaje niezmodyfikowany (niemutowalność). Validates: Requirements 9.1, 9.2.
- Property 11 (Pokrycie efektów ma poprawne granice): dla katalogu i rejestru (również z kluczami osieroconymi) każdy wiersz pokrycia spełnia `0 <= implemented <= total`, `0 <= manual <= total`, `implemented + manual <= total`, `percent_implemented ∈ [0, 100]`, `total == len(catalog.all(kategoria))` (liczone tylko komponenty z katalogu), a kategorie puste nie trafiają do wyniku. Validates: Requirements 9.3.
- Minimalny `ComponentCatalog` budowany z `ComponentBase(id, source)` i `EffectRegistry` z wygenerowanego słownika `ComponentRef -> EffectStatus`; bez ładowania realnych JSON.
- QA zielone dla moich plików: pytest `tests/test_effects_registry_props.py` (2 passed), ruff + mypy czyste. (W pełnym zestawie niezależny błąd w `tests/test_timing_spec_props.py` z równoległego zadania 5.3 — poza zakresem 7.4.) Wymagania: 9.1, 9.2, 9.3.
### ✅ Blok local-ti4-data-foundation 2.3 — wpięcie katalogu w StaticDataRegistry (ukończony)
- `src/core/registry.py`: w `_load()` buduję `registry.catalog` (ComponentCatalog) z wyniku `load_components(self._enabled)` i wystawiam `registry.load_report` (LoadReport). Specyfikacje czasowe (`build_timing_specs`) z kart akcji, zdolności frakcji i liderów (R8.2).
- Istniejące atrybuty rejestru (units/planets/systems/factions/strategy_cards/leaders/abilities/technologies/breakthroughs) bez zmian zachowania. Kolizje `id` w 9 STARYCH kategoriach tylko RAPORTOWANE przez `registry.legacy_id_collisions` (kategoria -> posortowane id); zasada „ostatni wpis wygrywa" zostaje (D9), więc brak regresji.
- Pola `FactionDef.abilities` i `FactionDef.promissory_notes` (alias `promissoryNotes`) były już obecne w `models.py` (dodane wcześniej addytywnie) — wymaganie zadania spełnione.
- Smoke na realnych danych: action_cards 143, agendas 63, decks 25, 13 kategorii w `load_report.loaded`, brak kolizji w starych kategoriach.
- QA zielone: `uv run pytest -q` (365 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste. Wymagania: 4.1, 5.1, 5.4, 5.5.
### ✅ Blok local-ti4-data-foundation 5.3 + 5.4 — testy właściwościowe specyfikacji czasowej (ukończony)
- `tests/test_timing_spec_props.py` (Hypothesis, 200 przykładów na właściwość). Oba zadania trafiają do jednego pliku.
- Property 7 (Specyfikacja czasowa zachowuje tekst okna i zamyka zbiór rodzajów): dla dowolnego tekstu okna i pola fazy `parse_timing` zwraca `None` dla tekstu pustego/samych białych znaków, w przeciwnym razie `raw_text` jest identyczny z wejściem (R8.5), `trigger ∈ TriggerKind` (zbiór zamknięty, R8.1), `phase_raw` równe wejściu, a `phase` różne od `None` tylko gdy `phase_raw` pasuje do `Phase` bez wielkości liter. Validates: Requirements 8.1, 8.3, 8.5.
- Property 8 (Klasyfikacja wyzwalacza deterministyczna i oparta tylko na prefiksie): dla każdego znanego prefiksu (dowolna wielkość liter, dowolne wiodące białe znaki) `classify_trigger`/`parse_timing` dają odpowiadający rodzaj; dla tekstu bez znanego prefiksu → `UNCLASSIFIED` z zachowanym tekstem; dwa wywołania na tych samych danych są równe. Validates: Requirements 8.2, 8.3.
- Property 9 (Zapytanie o specyfikacje czasowe zgadza się z modelem referencyjnym): dla wygenerowanego katalogu ze specyfikacjami `query_timing(trigger, phase)` zwraca dokładnie komponenty o danym rodzaju (i fazie, gdy podana), suma wyników po wszystkich rodzajach = zbiór wszystkich komponentów ze specyfikacją, a lista `UNCLASSIFIED` zgadza się z filtrem (podstawa raportu audytu). Validates: Requirements 8.4, 8.6.
- Triage kontrprzykładu: generator Property 8 początkowo doklejał dowolny tekst tuż po prefiksie `action`, co łamało zasadę całego słowa z designu (`action(?![^\W_])`); poprawiono TEST (implementacja poprawna) — dalszy ciąg po `action` zaczyna się od znaku niebędącego częścią słowa.
- QA zielone dla moich plików: pytest `tests/test_timing_spec_props.py` (4 passed), ruff + mypy czyste dla tego pliku. (W pełnym `ruff check` niezależny błąd E501 w `tests/test_rules_links_props.py` z równoległego zadania 7.5 — poza zakresem 5.3/5.4.) Wymagania: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6.

### ✅ Blok local-ti4-data-foundation 2.4 — testy właściwościowe filtrowania i kolizji (ukończony)
- `tests/test_source_selection_props.py`: dopisane Property 1 i Property 2 (Hypothesis, 200 przykładów każdy) obok istniejącej Property 3; generator `source` z `st.one_of(st.none(), st.integers(), st.lists(st.text()), st.text())` wymusza wpisy bez poprawnego źródła.
- Property 1 (Rachunek wpisów przy filtrowaniu po źródle): dla `select_entries` suma trzech rozłącznych klas — pominięte (źródło niekanoniczne) + bez źródła + aktywne — równa się liczbie wejść; aktywne = unikalni wybrani (po jednym na `id`) + przegrani w kolizjach; każdy wybrany ma źródło z aktywnego zbioru.
- Property 2 (Deterministyczny wybór przy kolizji identyfikatora): zbiór zwycięzców jest niezależny od kolejności wejścia (porównanie z przetasowaną kopią), a zwycięzca każdego `id` jest minimalny względem `(source_rank, file, index)` i ma rangę nie gorszą niż inni kandydaci (RULES.md 14, D9).
- QA zielone dla mojego pliku: `uv run pytest tests/test_source_selection_props.py -q` (3 passed), `ruff check` i `mypy` czyste. Validates: Requirements 4.1, 4.3, 4.4, 4.7, 6.1.

### ✅ Blok local-ti4-data-foundation 7.5 — test właściwościowy powiązań z regułami (ukończony)
- `tests/test_rules_links_props.py`: Property 16 (Powiązanie z tematami reguł jest deterministyczne i zawarte w indeksie), Hypothesis min. 100 przykładów na test. Testuje `RulesTopicIndex.match` z `src/core/rules_links.py`.
- Trzy niezmienniki: (1) `match` zwraca podzbiór tematów indeksu bez duplikatów, a brak trafienia daje pustą listę bez wyjątku; (2) dopasowanie po tytule jest deterministyczne i niewrażliwe na wielkość liter oraz wstawione znaki niealfanumeryczne (ten sam zestaw kodów co dla czystego tytułu); (3) nazwa, której znormalizowana postać nie jest kluczem indeksu, daje pustą listę.
- Smart generatory: unikalne kody tematów (opcjonalny prefiks `C_`/`F_`/`R_`), tytuły z interpunkcją, wariant wielkości liter + losowe separatory. Pomocnik `_match_keys` wiernie odwzorowuje klucze z `RulesTopicIndex.__init__` (tytuł, kod, kod bez prefiksu `_CODE_PREFIX`), żeby warunek „brak trafienia” zgadzał się z implementacją.
- QA zielone: `uv run pytest -q` (357 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste. Wymagania: 10.1, 10.2, 10.3.
### ✅ Blok local-ti4-data-foundation 2.3 — wpięcie katalogu w StaticDataRegistry (ukończony)
- `src/core/registry.py`: w `_load()` buduję `registry.catalog` (ComponentCatalog) z wyniku `load_components(self._enabled)` i wystawiam `registry.load_report` (LoadReport). Specyfikacje czasowe (`build_timing_specs`) z kart akcji, zdolności frakcji i liderów (R8.2).
- Istniejące atrybuty rejestru (units/planets/systems/factions/strategy_cards/leaders/abilities/technologies/breakthroughs) bez zmian zachowania. Kolizje `id` w 9 STARYCH kategoriach tylko RAPORTOWANE przez `registry.legacy_id_collisions` (kategoria -> posortowane id); zasada „ostatni wpis wygrywa" zostaje (D9), więc brak regresji.
- Pola `FactionDef.abilities` i `FactionDef.promissory_notes` (alias `promissoryNotes`) były już obecne w `models.py` (dodane wcześniej addytywnie) — wymaganie zadania spełnione.
- Smoke na realnych danych: action_cards 143, agendas 63, decks 25, 13 kategorii w `load_report.loaded`, brak kolizji w starych kategoriach.
- QA zielone: `uv run pytest -q` (365 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste. Wymagania: 4.1, 5.1, 5.4, 5.5.
### ✅ Blok local-ti4-data-foundation 5.5 — testy przykładowe mapowania i braku regresji okien (ukończony)
- `tests/test_timing_spec_mapping.py`: testy przykładowe pokrywające R8.7 i R8.8 dla `TRIGGER_WINDOW_MAP` z `src/core/timing_spec.py`.
- R8.7 (mapowanie całkowite nad `TriggerKind`): `TRIGGER_WINDOW_MAP` ma dokładnie jeden wpis dla każdej wartości `TriggerKind` (zbiór kluczy == `set(TriggerKind)`, brak nadmiarowych kluczy); wartości to wyłącznie `WindowType` lub `None` („brak okna"); rodzaje reakcji (when/after/before/instead) → `WindowType.REACTION`, a rodzaje bez odpowiednika (at_start/at_end/during/action/unclassified) → `None` (D10, RULES.md 34). Dodatkowo: rozłączność i zupełność podziału na „reakcja" / „brak okna" oraz zgodność `TimingSpec.window_type` z mapą dla próbki pokrywającej wszystkie rodzaje (klasyfikacja po prefiksie + `parse_timing`).
- R8.8 (brak regresji okien): zbiór wartości `WindowType` pozostaje nienaruszony (`STRATEGY_SECONDARY`, `COMBAT_ASSIGN_HITS`, `SPACE_CANNON`, `REACTION`), a publiczny interfejs `core/timing.py` (`build_response_queue`, `open_window`, `current_responder`, `respond_current`, `is_window_complete`, `close_window`) jest nadal dostępny. `tests/test_timing.py` NIE był modyfikowany i przechodzi zielony.
- QA zielone dla moich plików: `uv run pytest tests/test_timing_spec_mapping.py tests/test_timing.py tests/test_timing_spec.py -q` (42 passed), pełny `uv run pytest -q` (365 passed), `ruff check` i `mypy` czyste dla `tests/test_timing_spec_mapping.py`. (W pełnym `ruff check src tests` niezależny błąd E501 w `tests/test_audit_props.py` z równoległego zadania 8.5/8.6 — poza zakresem 5.5.) Wymagania: 8.7, 8.8.
### ✅ Blok local-ti4-data-foundation 2.5 — testy właściwościowe modeli i błędów walidacji (ukończony)
- `tests/test_components_props.py`: Property 4 (200 przykładów) i Property 5 (100 przykładów, Hypothesis). Testuje `build_component` z `src/core/components.py` oraz `load_components`/`DataValidationError` z `src/core/component_loader.py`.
- Property 4 (Zachowanie pól i surowych danych komponentu): dla wygenerowanego wpisu i dopasowanej `CategorySpec` (model `ObjectiveDef`, pole id `alias` lub `id`, losowe `text_fields` i pole okna) `build_component` daje `id` wyłącznie z pola wskazanego przez specyfikację, `raw` jest wierną KOPIĄ wpisu (nic nie ginie, R5.7), `texts` to dokładnie pola tekstowe obecne w JSON jako napisy, `window` odtwarzane tylko gdy specyfikacja ma pole okna, a `flavor_text` bierze `flavorText` lub `flavourText` bez preferencji spoza JSON. Validates: Requirements 5.2, 5.7.
- Property 5 (Błąd walidacji niesie kontekst wpisu): na `tmp_path` budowany jest prawdziwy katalog kategorii celów publicznych z jednym wpisem o kanonicznym `source` i niepoprawnym `points` (lista/napis/słownik — pydantic nie przyjmie jako `int | None`); `load_components` zgłasza `DataValidationError`, którego `category`, `file` i `entry_id` wskazują dokładnie wygenerowany wpis, a komunikat tekstowy także niesie ten kontekst. Validates: Requirements 5.5.
- Uwaga Windows/Hypothesis: `tmp_path` jest współdzielony między przykładami jednego testu, więc każdy przykład dostaje unikalny podkatalog (`uuid4`), z `suppress_health_check=[HealthCheck.function_scoped_fixture]`.
- QA zielone dla moich plików: `uv run pytest tests/test_components_props.py -q` (2 passed), pełny `uv run pytest -q` (385 passed), `ruff check` i `mypy` czyste dla `tests/test_components_props.py`. (W pełnym `mypy src tests` / `ruff check src tests` niezależne błędy w `src/core/registry.py` z równoległego zadania 4.1/4.3 wpinającego `references.py` — poza zakresem 2.5.) Wymagania: 5.2, 5.5, 5.7.

### ✅ Blok local-ti4-data-foundation 2.6 — testy katalogu na realnych danych (ukończony)
- `tests/test_components_real_data.py`: trzy testy przykładowe na REALNYCH assetach AsyncTI4, zbudowane na `StaticDataRegistry()` (domyślny `enabled_sources.json`: base, pok, codex1-4, thunders_edge) i jego `catalog`.
- Test 1 (R5.1, R5.4): każda kategoria z `CATEGORY_SPECS` jest niepusta, poza potwierdzonymi lukami z `audit/expected_gaps.json` (obecnie plik pusty → wszystkie 13 kategorii niepuste: action_cards 143, agendas 63, public_objectives 40, secret_objectives 40, attachments 22, explores 80, relics 24, promissory_notes 40, tokens 29, border_anomalies 1, galactic_events 20, genericcards 10, decks 25). Wyjątki czytane przez `src.audit.diffs.load_expected_gaps`, bez hardkodowania listy luk.
- Test 2 (R5.1): żaden załadowany komponent nie ma `source` spoza aktywnego manifestu (potwierdzenie filtra po polu `source`).
- Test 3 (R4.5, R5.1, D6): wpis `codex1` „War Machine" (alias `war_machinell`) ukryty w homebrew `assets/data/action_cards/theodisi.json` JEST ładowany z `source == "codex1"`, a karty homebrew z tego samego pliku (`source == "theodisi"`, np. `unchart_space`) są odfiltrowane — filtr działa po polu, nie po nazwie pliku.
- QA dla moich plików: `uv run pytest tests/test_components_real_data.py -q` (3 passed), `ruff check` i `mypy` czyste dla `tests/test_components_real_data.py`. (W pełnym zestawie niezależne błędy z równoległych zadań: 2.5 `tests/test_components_props.py` — reużycie `tmp_path` w Hypothesis na Windows; 4.1 `src/core/references.py` + nieużyte importy w `registry.py` — poza zakresem 2.6.) Wymagania: 4.5, 5.1, 5.4.

### ✅ Blok local-ti4-data-foundation 8.4 — `src/audit/sync_assets.py` (ukończony)
- `src/audit/sync_assets.py`: synchronizacja lokalnych grafik z katalogu referencyjnego. Ścieżka źródła to WYŁĄCZNIE argument CLI `--from <katalog>` (nigdy stała w kodzie — zgodność z R1.1). Czysta funkcja `sync_assets(source_dir, manifest_paths, assets_dir)` kopiuje do `assets/` tylko pliki z manifestu brakujące na dysku; pliki już obecne pomija (nie nadpisuje), a wpisy nieobecne w katalogu źródłowym trafiają na listę „niezsynchronizowane" (`SyncResult.unsynced`).
- Katalog źródłowy jest tylko czytany — nic w nim nie jest zmieniane ani usuwane (R12.8). Kopiowanie wyłącznie w stronę `assets/`.
- CLI (`main`): niezerowy kod wyjścia (1), gdy są pliki niezsynchronizowane; brak `--from` = komunikat o użyciu i kod 2 (argparse, `required=True`); nieistniejący katalog `--from` = `parser.error` (kod 2). `render_result` wypisuje liczby i listę braków.
- Test przykładowy na `tmp_path`: `tests/test_audit_sync_assets.py` (kopiowanie brakujących + pomijanie obecnych, lista niezsynchronizowanych + kod ≠ 0, nienaruszalność katalogu źródłowego przez porównanie sha256 przed/po, kod 0 przy komplecie, kod 2 przy braku `--from`).
- QA zielone dla moich plików: `uv run pytest tests/test_audit_sync_assets.py` (7 passed), pełny `uv run pytest -q` (385 passed), ruff + mypy czyste dla `sync_assets.py` i jego testu. (W pełnym `ruff check`/`mypy src tests` niezależne błędy z równoległych zadań 1.2/2.3/4.1 — poza zakresem 8.4.) Wymagania: 3.3, 12.8.

### ✅ Blok local-ti4-data-foundation 2.6 — testy katalogu na realnych danych (ukończony)
- `tests/test_components_real_data.py`: trzy testy przykładowe na REALNYCH assetach AsyncTI4, zbudowane na `StaticDataRegistry()` (domyślny `enabled_sources.json`: base, pok, codex1-4, thunders_edge) i jego `catalog`.
- Test 1 (R5.1, R5.4): każda kategoria z `CATEGORY_SPECS` jest niepusta, poza potwierdzonymi lukami z `audit/expected_gaps.json` (obecnie plik pusty → wszystkie 13 kategorii niepuste: action_cards 143, agendas 63, public_objectives 40, secret_objectives 40, attachments 22, explores 80, relics 24, promissory_notes 40, tokens 29, border_anomalies 1, galactic_events 20, genericcards 10, decks 25). Wyjątki czytane przez `src.audit.diffs.load_expected_gaps`, bez hardkodowania listy luk.
- Test 2 (R5.1): żaden załadowany komponent nie ma `source` spoza aktywnego manifestu (potwierdzenie filtra po polu `source`).
- Test 3 (R4.5, R5.1, D6): wpis `codex1` „War Machine" (alias `war_machinell`) ukryty w homebrew `assets/data/action_cards/theodisi.json` JEST ładowany z `source == "codex1"`, a karty homebrew z tego samego pliku (`source == "theodisi"`, np. `unchart_space`) są odfiltrowane — filtr działa po polu, nie po nazwie pliku.
- QA dla moich plików: `uv run pytest tests/test_components_real_data.py -q` (3 passed), `ruff check` i `mypy` czyste dla `tests/test_components_real_data.py`. (W pełnym zestawie niezależne błędy z równoległych zadań: 2.5 `tests/test_components_props.py` — reużycie `tmp_path` w Hypothesis na Windows; 4.1 `src/core/references.py` + nieużyte importy w `registry.py` — poza zakresem 2.6.) Wymagania: 4.5, 5.1, 5.4.

### ✅ Blok local-ti4-data-foundation 8.3 — raport Audytora_Danych i `__main__` (ukończony)
- `src/audit/report.py`: `AuditReport` (dataclass ze wszystkimi sekcjami z R12.1: `counts`, `skipped`, `sourceless`, `conflicts`, `unresolved`, `suspicious`, `gaps_to_confirm`, `unclassified_timing`, `effect_coverage`, `manifest`, `external_urls`, `frontend_diff`, `no_rules_note`, `orphan_effect_statuses` + `validation_error`, `references_module_available`).
- `build_report(registry, scans)` jest CZYSTE nad już zebranymi danymi (I/O żyje w `collect_scans`): liczby z `catalog.counts()`, luki przez `diffs.find_gaps` z `expected_gaps.json`, `unclassified` przez `catalog.query_timing(TriggerKind.UNCLASSIFIED)`, pokrycie i osierocone statusy przez `effects_registry.coverage`/`EffectRegistry.load`, „bez noty" przez `rules_links.RulesTopicIndex` (brak `tirules.json` ⇒ wszystkie „bez noty", R10.3).
- `render_text(report)` buduje czytelny raport tekstowy ze wszystkimi sekcjami; `exit_code(report)` zwraca 1 TYLKO przy błędzie krytycznym (nierozwiązana referencja, brakujący plik z manifestu, zewnętrzny URL spoza listy dozwolonej, błąd walidacji wpisu kanonicznego); ostrzeżenia (podejrzane, `unclassified`, luki, „bez noty", osierocone statusy, kolizje) nie zmieniają kodu 0 (Property 14, R3.4, R7.5, R12.2).
- `detect_suspicious` (R4.5): wpis o źródle kanonicznym w pliku, którego nazwa (bez rozszerzenia) NIE jest identyfikatorem żadnego znanego źródła ani nazwą bazową kategorii — czysto STRUKTURALNIE, bez listy nazw homebrew. Na realnych danych wykrywa m.in. `theodisi.json`/`codex1` oraz pliki `te_*`, `color.json`, `codexii/iv.json`, `base_game.json`.
- Spójność referencji (R7.x) z `core/references.py` przez import OBRONNY (`importlib`, zadanie 4.1 równoległe); gdy modułu brak, substytut `registry.missing_planet_references` + flaga `references_module_available=False`.
- `src/audit/__main__.py`: `python -m src.audit` z opcjami `--write-baseline`, `--write-manifest`, `--json`. `main()` łapie `DataValidationError` (rejestr nie wstał) jako błąd krytyczny.
- Uruchomiono `uv run python -m src.audit --write-baseline` → zapisano `audit/baseline_counts.json` (13 kategorii, m.in. action_cards 143, agendas 63, cele 40/40, explores 80, relics 24, promissory 40). Kod wyjścia 1 odzwierciedla realne, znane problemy jakości do naprawy w zadaniach 4.x/11.x (nierozwiązane referencje homebrew `explores_cpti`, zewnętrzne URL we froncie przed migracją grafik/fontów) — diff zatwierdza użytkownik przy commicie.
- Test przykładowy `tests/test_audit_report.py` (11 passed): `detect_suspicious` na `tmp_path` (plik homebrew vs plik źródła vs plik kategorii), rozróżnienie krytyczny/ostrzeżenie w `exit_code`, `build_report` + `render_text` na realnym rejestrze zawiera wszystkie sekcje R12.1, `write_baseline` zapisuje `counts`.
- QA dla moich plików: `uv run pytest -q` (396 passed), ruff + mypy czyste dla `src/audit/report.py`, `src/audit/__main__.py`, `tests/test_audit_report.py`. (W pełnym `ruff check src tests` niezależny błąd sortowania importów w `src/core/registry.py` z równoległego zadania 4.1 — poza zakresem 8.3.) Wymagania: 3.2, 3.4, 4.5, 6.1, 6.2, 7.5, 8.4, 9.3, 10.3, 12.1, 12.2.

### ✅ Blok local-ti4-data-foundation 8.9 — test regresji liczb wpisów (ukończony)
- `tests/test_audit_baseline.py`: test regresji porównujący liczby komponentów per kategoria i źródło (`StaticDataRegistry().catalog.counts()`) z wartościami referencyjnymi w `audit/baseline_counts.json` (R6.4). Rejestr budowany raz na moduł (fixture `scope="module"`).
- Różnice liczone czystą funkcją `diff_counts`, a wzorzec wczytywany przez `load_baseline_counts` — obie z `src/audit/diffs.py` (bez duplikowania logiki w teście). Klucze kategorii z `catalog.counts()` to `ComponentCategory` (StrEnum); normalizowane do `str` (`.value`), by porównanie i wypisane różnice operowały na zwykłych napisach.
- Przy rozbieżności (R6.5) test zawodzi z czytelnym, deterministycznie posortowanym wypisaniem różnic `kategoria/źródło: baseline → current` (`—` = brak wpisu po danej stronie, czyli nowe lub usunięte źródło w kategorii) oraz podpowiedzią regeneracji wzorca (`uv run python -m src.audit --write-baseline`). Dodatkowa asercja chroni przed pustym/brakującym baseline.
- QA zielone: `uv run pytest tests/test_audit_baseline.py -q` (1 passed), pełny `uv run pytest -q` (399 passed), `ruff check` i `mypy` czyste dla `tests/test_audit_baseline.py`. (W pełnym `ruff check src tests` niezależny błąd F401 nieużytego importu `pytest` w `tests/test_components.py` z równoległego zadania — poza zakresem 8.9.) Wymagania: 6.4, 6.5.
### ✅ Blok local-ti4-data-foundation 4.2 — `ComponentCatalog.faction_bundle` i `FactionBundle` (ukończony)
- `src/core/components.py`: dodano niemutowalny dataclass `FactionBundle` (frozen) z polami `faction`, `leaders`, `abilities`, `faction_tech`, `promissory_notes`, `units`, `breakthrough` oraz metodę `ComponentCatalog.faction_bundle(faction_id)` zwracającą komplet komponentów powiązanych z frakcją w JEDNYM wywołaniu (R5.6: liderzy, zdolności, technologie frakcyjne, promissory notes, jednostki, przełom).
- Identyfikatory czytane są WYŁĄCZNIE z list `FactionDef` (`leaders`, `abilities`, `faction_tech`, `promissory_notes`, `units`) i mapowane na modele z odpowiednich słowników. Zero hardkodowania nazw ani list. Identyfikatory nierozwiązane (brak w słowniku) są pomijane — ich wykryciem zajmuje się osobno `core/references.py` (zadanie 4.1).
- Konstruktor `ComponentCatalog` rozszerzony o keyword-only słowniki kategorii żyjących poza Katalogiem_Komponentów (w rejestrze): `factions`, `leaders`, `abilities`, `technologies`, `units`, `breakthroughs`. Puste domyślnie → pełna zgodność wsteczna z dotychczasowymi wywołaniami `ComponentCatalog(tables)`.
- Przełom (breakthrough, Thunder's Edge) NIE figuruje na liście `FactionDef`; dopasowywany po polu `faction` przełomu równym id frakcji LUB jej „rodzinie" (`short_name` małymi literami) — ta sama reguła co w rejestrze, bez listy frakcji w kodzie (`_breakthrough_for`).
- Promissory notes rozwiązywane ze słownika kategorii `PROMISSORY_NOTE` Katalogu_Komponentów (z filtrem typu `PromissoryNoteDef`), bo to komponenty ładowane do katalogu, a nie osobny słownik rejestru.
- Testy przykładowe `tests/test_components.py`: `test_faction_bundle_sklada_komponenty_z_list_faction_def` (rozwiązanie id na modele, pominięcie nierozwiązanego lidera `brak_lidera`, dopasowanie przełomu po rodzinie) oraz `test_faction_bundle_nieznana_frakcja_rzuca_key_error` (brak frakcji → `KeyError`).
- Bramka QA zielona: `uv run pytest -q` (405 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 101 source files). Wymagania: 5.6.
### ✅ Blok local-ti4-data-foundation 8.8 — test Strażnika_Lokalności, część backendowa (ukończony)
- `tests/test_locality_guard.py`: pilnuje lokalności kodu backendu i budowy aplikacji względem folderów referencyjnych AsyncTI4 (`TI4_map_generator_bot`, `ti4_web_new`) i korzenia projektu. Nazwy folderów są STAŁĄ W TEŚCIE (`REFERENCE_DIR_NAMES`), nie w kodzie produkcyjnym (R1.1), i korzystają z czystych skanerów z `src/audit/locality.py` (`find_reference_path_usage`, `collect_sources` — odczyt `utf-8-sig`, bezpieczny dla plików z BOM).
- R1.1: skan `ast` literałów napisowych (bez docstringów/komentarzy) w `src/**/*.py` i `scripts/**/*.py` — żaden nie zawiera nazwy folderu referencyjnego; sam plik Strażnika jest wykluczony ze skanu (celowo trzyma stałą).
- R1.2: skan `frontend/src/**` (ts/tsx/js/jsx/css), `index.html` i `vite.config.ts` pod kątem importu/proxy folderów referencyjnych — filtr `_import_or_proxy_lines` zachowuje numerację linii (linie nie-importowe → puste), bo osadzone URL-e CDN pokrywa osobny skaner URL (zad. 11.7), a dane homebrew — zad. 11.3.
- R1.3/R1.5: fixture `read_recorder` opakowuje `Path.read_text`, `Path.read_bytes` i `builtins.open` (deskryptory całkowite pomijane), zbierając czytane ścieżki. Testy budują `StaticDataRegistry()` oraz `create_app(store=EventStore(":memory:"))` i asertują, że żaden odczyt nie wychodzi poza `PROJECT_ROOT` ani do folderu referencyjnego (ścieżki rozwijane do bezwzględnych i sprawdzane `relative_to`).
- QA zielone: `uv run pytest tests/test_locality_guard.py -q` (4 passed), pełny `uv run pytest -q` (405 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste. Wymagania: 1.1, 1.2, 1.3, 1.5.
### ✅ Blok local-ti4-data-foundation 8.7 — Property 14 (kod wyjścia audytu) + test raportu (ukończony)
- **Property 14: Kod wyjścia audytu odzwierciedla błędy krytyczne** — dopisana do `tests/test_audit_props.py` (bez nadpisywania; dołączona po Property 12/13/15). Dwie funkcje właściwościowe Hypothesis budują `AuditReport` z losowych kombinacji pól krytycznych i ostrzegawczych (bez dysku i bez rejestru) i porównują z modelem referencyjnym niezależnym od `has_critical`:
  - `test_exit_code_jest_niezerowy_dokladnie_przy_bledzie_krytycznym` (max 200 iteracji): `exit_code(report) == 1` wtedy i tylko wtedy, gdy którekolwiek z pól krytycznych jest niepuste (`unresolved`, `manifest.missing`, `external_urls`, `validation_error`); ostrzeżenia (podejrzane, luki, `unclassified`, „bez noty”, osierocone statusy, pliki `unused` z manifestu) nie zmieniają kodu. Dodatkowo potwierdza, że kod jest zawsze ∈ {0, 1}.
  - `test_exit_code_zero_gdy_tylko_ostrzezenia` (max 100 iteracji): dowolny zestaw samych ostrzeżeń daje kod 0 i `has_critical is False`.
- Test raportu na realnym rejestrze (`build_report` + `render_text` zawiera wszystkie sekcje R12.1) już istniał w `tests/test_audit_report.py` z zadania 8.3 — NIE duplikowany.
- QA dla moich plików zielone: `uv run pytest tests/test_audit_props.py tests/test_audit_report.py -q` (21 passed), pełny `uv run pytest -q` (405 passed), `ruff check` i `mypy` czyste dla `tests/test_audit_props.py` i `tests/test_audit_report.py`. (Przejściowy, niezależny błąd ruff F401 w `src/audit/locality.py` z równoległego zadania — poza zakresem 8.7.) Wymagania: 3.4, 7.5, 12.1, 12.2.
### ✅ Blok local-ti4-data-foundation 7.3 — wpięcie rejestru efektów i indeksu reguł w `ComponentCatalog` (ukończony)
- `src/core/components.py`: konstruktor `ComponentCatalog` rozszerzony o dwa opcjonalne argumenty keyword-only — `effect_registry` (protokół `_EffectRegistryLike` z metodą `status_of`, by uniknąć cyklu importów: `effects_registry` importuje `components`) i `rules_index` (`RulesTopicIndex`, domyślnie pusty). Zmiana w pełni addytywna: istniejące wywołania `ComponentCatalog(tables)` działają bez zmian.
- Nowe metody katalogu: `effect_status(ref)` — deleguje do wpiętego `EffectRegistry`; brak rejestru → domyślny `NOT_IMPLEMENTED` (R9.3). `rules_topics(ref)` — zwraca tematy zrzutu reguł dopasowane deterministycznie (równość znormalizowanych nazw) po `id` i nazwie komponentu oraz temat kategorialny z `CATEGORY_TOPIC_HINTS`; brak trafień → pusta lista, nic nie jest zgadywane (R10.1).
- `src/core/registry.py`: w `_load()` wczytywany `EffectRegistry.load()` (brak pliku = pusty, R9.4) i `RulesTopicIndex.from_json()` (brak `tirules.json` = pusty, R10.2), wystawione jako `registry.effect_registry` i `registry.rules_index`, a następnie wpięte w `ComponentCatalog`. Oba czytane z lokalnych assetów — nic w kodzie.
- Testy przykładowe `tests/test_components.py`: `test_effect_status_i_rules_topics_wpiete_w_katalog` (status z wpiętego rejestru, domyślny `NOT_IMPLEMENTED` dla braku wpisu, tematy reguł: trafienie po nazwie + temat kategorialny, nieznany komponent → pusta lista) oraz `test_katalog_bez_rejestru_i_indeksu_dziala_wstecz` (zgodność wsteczna — wartości domyślne). Smoke test na realnym rejestrze: indeks reguł 149 tematów, karta akcji → `C_action_cards`, status `not_implemented`.
- Bramka QA zielona: `uv run pytest -q` (407 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 101 source files). Wymagania: 9.4, 10.2 (oraz R9.3, R10.1).

## Blok 4.4 — Testy przykładowe paczki frakcji i referencji realnych (local-ti4-data-foundation)

- Nowy plik `tests/test_references_real_data.py`: testy przykładowe na pełnym `StaticDataRegistry` (domyślny manifest: base, pok, codex1-4, Thunder's Edge), bez mocków.
- `faction_bundle` dla reprezentatywnych frakcji z każdego aktywnego źródła (`arborec`, `sol` — base; `titans` — pok; `keleresm` — codex3; `bastion` — thunders_edge): sprawdza, że paczka zawiera liderów i przełom (R5.6) oraz że każdy rozwiązany identyfikator (liderzy, zdolności, technologie frakcyjne, promissory notes, jednostki) to TEN SAM obiekt co w słowniku rejestru/katalogu (mapowanie 1:1, nic nie jest hardkodowane). Dodatkowo kontrakt: nieistniejąca frakcja → `KeyError`.
- `find_unresolved_references` na realnym rejestrze: asercja STRUKTURY (lista `UnresolvedReference`) zamiast porównania z `audit/expected_gaps.json` (ten plik trzyma pary `(kategoria, źródło)` dla brakujących źródeł kanonicznych — inne pojęcie). Znane, oczekiwane luki homebrew udokumentowane jako zbiór właścicieli `{explores_cpti, mirage, gamma, gw, ion}` (talia eksploracji `cpti` i attachmenty spoza aktywnych źródeł, R7.6) — test NIE traktuje ich jako błędu, tylko pilnuje, że nie pojawia się żadna NOWA, nieoczekiwana luka. Osobny test gwarantuje brak zerwanych referencji frakcji (`faction.*`) i systemów do planet (`system.planets`) (R7.1, R7.4).
- Bramka QA zielona: `uv run pytest -q` (425 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 103 source files). Wymagania: 5.6, 7.1, 7.4.

### ✅ Blok local-ti4-data-foundation 4.3 — test właściwościowy referencji (ukończony)
- `tests/test_references_props.py`: Property 6 (Spójność referencji jest wykrywana dokładnie), Hypothesis 200/100 przykładów na test. Testuje `find_unresolved_references` / `build_reference_report` z `src/core/references.py` na „mini-rejestrze” — lekkim obiekcie (`_MiniRegistry`) spełniającym protokół `RegistryLike`, z ręcznie złożonym `ComponentCatalog` i namiastką `LoadReport` (`_MiniLoadReport.skipped_index`). Bez dysku i bez pełnego `StaticDataRegistry`.
- Test 1 (R7.1, R7.6): promissory notes frakcji — cel istniejący w katalogu → brak zgłoszenia; cel wyłącznie wśród wpisów niekanonicznych (`skipped_index`) → `leaks_noncanonical=True`; cel nieznany nigdzie → `leaks_noncanonical=False`; każdy identyfikator z `<color>` trafia WYŁĄCZNIE do `report.templates`, nigdy do `unresolved`. Zbiór nierozwiązanych równa się dokładnie referencjom spoza katalogu (bez szablonów).
- Test 2 (R7.2): `cardIDs` talii typu `promissory_note` — brakujące → nierozwiązane (`kind="deck.cardIDs"`), `<color>` → szablon.
- Test 3 (R7.3): `attachmentId` eksploracji i `attachmentID` żetonów — brakujący attachment → nierozwiązana referencja o właściwym `kind`/`owner_id`/`missing_id`; istniejący → brak zgłoszenia.
- Test 4 (R7.5, R7.6): `find_unresolved_references` nie zawiera szablonów `<color>` i jest identyczne z `build_reference_report(...).unresolved`.
- Mini-rejestr buduje komponenty bezpośrednio przez modele (`PromissoryNoteDef`, `AttachmentDef`, `ExplorationDef`, `TokenDef`, `DeckDef`) z polem `id` (mapowanie `alias→id` żyje w `build_component`, nie w modelu) — stąd konstrukcja po `id=`, nie `alias=`.
- QA zielone: `uv run pytest -q` (425 passed), `uv run ruff check src tests` i `uv run mypy src tests` czyste (103 pliki). Validates: Requirements 7.1, 7.2, 7.3, 7.6.

### ✅ Blok local-ti4-data-foundation 10.1 — endpointy komponentów (ukończony)
- Nowy plik `src/api/schemas_components.py` (osobny od `schemas.py`, by nie puchł kontrakt podstawowy): DTO Pydantic v2 dla Katalogu_Komponentów z klasmetodami `from_core` — `CategoriesResponse`/`CategoryCount`, `CategoryComponentsResponse`, `ComponentDetailResponse`, `FactionBundleResponse`, `TimingSpecsResponse`, `ComponentRefDTO`, `TimingSpecDTO`, `RulesTopicDTO`. Modele komponentów serializowane po aliasach (`model_dump(mode="json", by_alias=True)`), zachowują pole `raw`.
- Nowy router `src/api/routers/components.py` (cienki, wzorzec `routers/rules.py`): TYLKO-DO-ODCZYTU nad `ctx.registry.catalog` przez `Depends(get_ctx)`, zero mutacji `GameState`, zero `broadcast`. Endpointy: `GET /components` (lista kategorii + liczniki ze `counts()`), `GET /components/{category}` (słownik `id -> komponent`), `GET /components/{category}/{component_id}` (komponent + `TimingSpec` + status efektu + tematy reguł), `GET /components/factions/{faction_id}/bundle` (`FactionBundle`, R5.6), `GET /timing-specs?trigger=&phase=` (`query_timing`, R8.6).
- Mapowanie błędów domenowych (R11.3): nieznana kategoria lub identyfikator → `HTTPException(404, "Component not found: <category>/<id>")`; nieznana frakcja (`KeyError` z `faction_bundle`) → 404 z kategorią `factions`. Nieprawidłowy `trigger`/`phase` → 422 dzięki walidacji enum FastAPI (parametry typowane jako `TriggerKind`/`Phase`). Źródła kanoniczne — filtr jest już w katalogu (R11.2), API niczego nie filtruje.
- Router zarejestrowany w fabryce `src/api/app.py` (`include_router(components.router)`); kolejność ścieżek bez kolizji (różna liczba segmentów: `/components/{category}/{component_id}` vs `/components/factions/{faction_id}/bundle`).
- Smoke-test TestClient potwierdził: `GET /components` → 13 kategorii, `action_cards` → 143 wpisy, detal zwraca `effect_status`, 404 dla złej kategorii i złego id z poprawnym komunikatem, `trigger=when` → 69 trafień, `trigger=bogus` → 422, bundle frakcji `arborec` → 3 liderów, 1 zdolność, 10 jednostek, przełom obecny.
- Bramka QA zielona: `uv run pytest -q` (425 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 105 source files). Wymagania: 11.1, 11.2, 11.3, 11.4.

### Blok 10.2 — Testy API Katalogu_Komponentów

- Nowy plik `tests/test_components_api.py` (pytest + FastAPI `TestClient`): testuje router `src/api/routers/components.py` na REALNYM `StaticDataRegistry` (fixture `registry` o zasięgu modułu) z osobnym `EventStore(":memory:")` na każdy test (fixture `client`), wzorzec z `tests/test_api.py`.
- Pokrycie endpointów (R11.1): `GET /components` (lista kategorii + liczniki, `total == sum(by_source)`, sortowanie po nazwie), `GET /components/{category}` (słownik `id -> komponent`, `count == len`), `GET /components/{category}/{id}` (detal z `timing_spec`/`effect_status`/`rules_topics`, `source` z aktywnego manifestu — R11.2), `GET /components/factions/{faction_id}/bundle` (paczka frakcji z realnym id z `/factions`, R5.6), `GET /timing-specs?trigger=&phase=` (lista adresów, propagacja fazy).
- Mapowanie błędów (R11.3): 404 dla nieznanej kategorii (`Component not found: <category>/`), nieznanego id (`<category>/<id>`) i nieznanej frakcji (`factions/<id>`); 422 dla nieprawidłowego `trigger` (enum FastAPI) i braku wymaganego `trigger`.
- Kategorie/identyfikatory wybierane dynamicznie z katalogu (pierwsza niepusta kategoria, pierwszy jej wpis) — test odporny na zmiany danych. Frakcje adresowane przez `/factions`, bo nie są tabelą katalogu.
- Bramka QA zielona: `uv run pytest -q` (437 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 106 source files). Wymagania: 11.1, 11.2, 11.3, 11.4.
### ✅ Blok local-ti4-data-foundation 11.1 — Resolver_Zasobów i manifest we froncie (ukończony)
- Nowy moduł `frontend/src/shared/assets/resolveAsset.ts` (Resolver_Zasobów): `assetUrl(logicalPath)` zamienia logiczną ścieżkę (np. `/units/blu_cruiser.png`) na LOKALNY URL `/static/units/blu_cruiser.png`, zwraca WYŁĄCZNIE ścieżki lokalne (`/static/...` albo `PLACEHOLDER_URL`), nigdy `://` (R2.1). Gdy dokładnej ścieżki nie ma w manifeście, próbuje alternatywnych rozszerzeń `.png/.jpg/.jpeg/.webp` (bo stare `cdnImage()` zamieniało `.png/.jpg -> .webp`, a Resolver nie kopiuje tej konwersji — rozstrzyga ją manifest, zgodnie z design.md). Brak wszystkich wariantów → `PLACEHOLDER_URL` (R2.6). `sheetUrl("units"|"tokens", name)` buduje ścieżkę do sprite sheetu (sheety są wyłącznie `.webp`). `PLACEHOLDER_URL = "/placeholder.svg"`.
- Pusty manifest (grafiki jeszcze niezsynchronizowane) → `assetUrl` zwraca ścieżkę `/static/...` bezpośrednio zamiast placeholdera, żeby nie psuć działającego dev-setupu.
- Nowy plik `frontend/public/placeholder.svg` — lokalny placeholder pokazywany, gdy grafiki nie ma w Zasobach_Lokalnych.
- Manifest frontendu `frontend/src/shared/assets/assetManifest.json` (tylko logiczne ścieżki, `{"paths": [...]}`) generowany z `audit/assets_manifest.json`. Rozszerzyłem `src/audit/assets_manifest.py` o `FRONTEND_MANIFEST_PATH` i `write_frontend_manifest()`, a CLI `uv run python -m src.audit --write-manifest` zapisuje teraz OBA pliki (główny w `audit/` + kopię logicznych ścieżek we froncie). Jedyne źródło prawdy: `audit/assets_manifest.json`; kopia we froncie to artefakt generowany.
- UWAGA: to zadanie TYLKO tworzy resolver i manifest — zamiana wszystkich wywołań `cdnImage()` to zadanie 11.2 (jeszcze niewykonane).
- Bramka frontendowa zielona dla plików tego bloku: `npm run type-check` (OK), `npx eslint src/shared/assets/resolveAsset.ts` (0 błędów), `npm run build` (OK). Uwaga: `npm run lint` dla całego repo zgłasza 2 PREISTNIEJĄCE błędy w `src/domains/rules/RulesBrowserPage.tsx` (plik niemodyfikowany w tym bloku, poza zakresem 11.1).
- Bramka backendowa zielona (zmiany w `src/audit/`): `uv run pytest -q` (437 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success, 106 plików).
- Wymagania: 2.1, 2.6, 3.1.
### ✅ Blok local-ti4-data-foundation 11.2 — zastąpienie `cdnImage()` Resolverem_Zasobów (ukończony)
- Mechaniczna zamiana wszystkich wywołań `cdnImage()` na `assetUrl()` (ta sama sygnatura `string -> string`) w 59 plikach `frontend/src`: import `@/entities/data/cdnImage` → `@/shared/assets/resolveAsset`, każde wywołanie `cdnImage(` → `assetUrl(`. Po zmianie w `frontend/src` nie pozostało żadne funkcjonalne odwołanie do `cdnImage` ani do CDN AsyncTI4 (jedyne wzmianki to komentarze w `resolveAsset.ts` opisujące zastąpienie).
- Usunięty przestarzały moduł `frontend/src/entities/data/cdnImage.ts` (wraz z budowaniem URL `https://images.asyncti4.com/...` i parametrem `?v=4`). Konwersja rozszerzeń `.png/.jpg -> .webp` nie jest już kopiowana — rozstrzyga ją manifest w Resolverze_Zasobów (zgodnie z 11.1 i design.md).
- Zaktualizowany `frontend/README.md`: wpis „Grafiki idą z CDN AsyncTI4 (cdnImage.ts)" zastąpiony opisem lokalnych grafik serwowanych pod `/static` przez Resolver_Zasobów (`src/shared/assets/resolveAsset.ts`).
- Bramka frontendowa zielona: `npm run type-check` (OK), `npm run build` (`tsc && vite build` — OK, exit 0). `npm run lint` zgłasza WYŁĄCZNIE 2 PREISTNIEJĄCE błędy w `src/domains/rules/RulesBrowserPage.tsx` (plik niemodyfikowany, poza zakresem 11.2) — zmiany tego bloku nie wprowadziły żadnych nowych uwag lintera.
- UWAGA: niezacommitowane zmiany innej osoby (`useNewGame.ts`, `Step_NameColor.tsx`, `useSetupStore.ts`, nowe pliki `faction_portraits`) NIE były ruszane ani stagowane.
- Wymagania: 2.1, 2.2, 2.6.

### ✅ Blok local-ti4-data-foundation 11.3 — lokalne sprite sheety, ikony frakcji, relikt, Discord (ukończony)
- `frontend/src/shared/ui/Unit/unitSprites.ts`: sprite sheet jednostek z `sheetUrl("units", color)` zamiast `https://images.asyncti4.com/units/sheets/...webp?v=4` — grafika lokalna z backendu (`/static/units/sheets/...`), bez CDN AsyncTI4 (R2.1).
- `frontend/src/shared/ui/Token/components/TokenSprite.tsx`: `backgroundImage` z `sheetUrl("tokens", sprite.sheet)` zamiast CDN AsyncTI4.
- `frontend/src/entities/lookup/factions.ts`: `getFactionImage` dla typów `EMOJI` (dawniej `emoji-cdn.mqrio.dev`) i `DISCORD` (surowy URL profilu) zwraca teraz LOKALNĄ grafikę frakcji (`assetUrl("/factions/<alias>.png")`, placeholder przy braku) — koniec z zasobem zewnętrznym (R2.4).
- `frontend/src/entities/data/relics.ts`: relikt „The Silver Flame" (`silverflame`) ma `imageURL` lokalny (`/hover_images/relics/misc_homebrew/the_silver_flame.png`) zamiast `cdn.statically.io` (R2.4), spójnie z pozostałymi reliktami.
- `frontend/src/config.ts`: dodana flaga `config.features.onlineLogin` (domyślnie `false`). `frontend/src/domains/auth/DiscordLogin.tsx`: komponent zwraca `null`, gdy `onlineLogin === false`, więc adres `discord.com` nie trafia do DOM w trybie offline (D2; `discord.com` zostaje w allowliście jako „tylko online, flaga").
- Usuwanie wbudowanych danych niekanonicznych z `entities/data/*.ts` POMINIĘTE zgodnie z decyzją D3 (tylko audyt + test różnic id) — potwierdzone przez użytkownika; ~3400 wpisów w 16 plikach zostaje jako cache do osobnej migracji.
- Bramka frontendowa zielona: `npm run type-check` i `npm run build` przechodzą; `npm run lint` zgłasza wyłącznie 2 preistniejące błędy w `RulesBrowserPage.tsx` (nietknięte, poza zakresem zadania). Brak nowych zasobów zewnętrznych w runtime; pozostałe URL-e (`discord.com` za flagą, `ti4battle.com`, `tirules2.com`, `github.com/dangothemango`) to allowlista nawigacyjna/atrybucyjna (D2). Wymagania: 2.2, 2.3, 2.6, 11.5.

### ✅ Blok local-ti4-data-foundation 11.4 — fonty lokalne i czyszczenie `index.html` (ukończony)
- Fonty tekstu i danych przeniesione z Google Fonts na LOKALNE pakiety `@fontsource` (D11): dodane do `frontend/package.json` z DOKŁADNIE przypiętymi wersjami `@fontsource/ibm-plex-sans@5.3.0` i `@fontsource/ibm-plex-mono@5.3.0` (bez `^`), `--save-exact`.
- `frontend/src/main.tsx`: importy CSS fontów na samej górze (przed resztą stylów). Tylko wagi z drabiny typograficznej (`styles/typography.css`): Sans 400/500/600/700, Mono 400/500/700. Podzbiory `latin` + `latin-ext` (polskie znaki ą/ę/ł…). Vite bundluje je jako lokalne `.woff2`/`.woff` do `dist/assets/` — ZERO żądań sieciowych w runtime.
- `frontend/index.html`: usunięte wszystkie zewnętrzne odwołania — `preconnect`/`dns-prefetch` do `images.asyncti4.com` oraz `preconnect` do `fonts.googleapis.com`/`fonts.gstatic.com` i `link rel=stylesheet` do Google Fonts (IBM Plex). Na ich miejscu komentarz wyjaśniający lokalność. Zostały wyłącznie zasoby lokalne: ikona `/favico.png`, preload + `@font-face` dla `Ambroise Firmin` (logo splashu, `/font/…`, self-hosted) i tło `/static/extra/main_menu.jpg` z Backendu. Brak skryptów analitycznych (nigdy ich nie było).
- Bez binarnych plików fontów w repo: `@fontsource` żyje w `node_modules` (gitignore), pliki trafiają do bundla przy buildzie — zgodne z polityką „grafiki/fonty poza repo" (D1); `.gitignore` bez zmian.
- Bramka frontendowa zielona: `npm run type-check` (czysto), `npm run build` (tsc + vite build OK; w `dist/assets/` widoczne lokalne `ibm-plex-sans-*`/`ibm-plex-mono-*` `.woff2`). `npm run lint` bez NOWYCH błędów — pozostają wyłącznie 2 preistniejące błędy w `RulesBrowserPage.tsx` (poza zakresem zadania, nietknięte).
- Staging TYLKO moich plików (nie `git add .`): `frontend/index.html`, `frontend/src/main.tsx`, `frontend/package.json`, `frontend/package-lock.json`, `docs/PROGRESS.md`. Niezacommitowane cudze zmiany nienaruszone. Wymagania: 2.1, 2.4, 2.6 (realizacja ładowania fontów lokalnie — R2.3, R2.7; czyszczenie zewnętrznych odwołań z `index.html`).
### ✅ Blok local-ti4-data-foundation 11.7 — statyczny test zewnętrznych URL + audyt (ukończony)
- `tests/test_locality_guard.py`: dopisany test `test_frontend_has_no_external_urls_outside_allowlist` (R2.5, R2.6, R12.2). Skanuje `frontend/src/**` (ts/tsx/js/jsx/css), `index.html` i `vite.config.ts` czystym skanerem `scan_external_urls` z `src/audit/locality.py` (pliki `*.test.ts(x)` i hosty lokalne `localhost`/`127.0.0.1` pomijane). Wszystkie pozostałe `http(s)://` muszą pasować do prefiksu z `audit/external_url_allowlist.json`; w komunikacie błędu podpowiedź, żeby dodać zasadny URL do listy dozwolonej z notą.
- `audit/external_url_allowlist.json`: dodany wpis `http://www.w3.org/2000/svg` z notą „identyfikator przestrzeni nazw SVG (xmlns) w osadzonych maskach data:image/svg+xml; nie jest pobierany po sieci". Skan wykrył DOKŁADNIE 3 trafienia tego namespace w CSS masek (`PlanetCard`, `Relic`, `Tech`) — to standardowy identyfikator XML, nie żądanie sieciowe. Pozostałe prefiksy (tirules2.com, github.com/dangothemango/tirules, ti4battle.com, discord.com za flagą D2) były już na liście z not.
- Uruchomiono `uv run python -m src.audit`: sekcja „Zewnętrzne URL spoza listy dozwolonej: 0" oraz „Manifest grafik: brakujące na dysku: 0" — części audytu w zakresie 11.7 są czyste, więc NIE trzeba było uruchamiać `--write-manifest` ani zgłaszać braków do `sync_assets`. Audyt kończy się kodem 1 z powodu PREISTNIEJĄCYCH, znanych luk referencyjnych homebrew (`explores_cpti`, attachmenty `gamma`/`mirage`/`ion` spoza aktywnych źródeł — R7.6) raportowanych w zadaniach 4.x; to nie jest regresja tego bloku ani błąd w zakresie 11.7.
- Bramka QA zielona: `uv run pytest -q` (438 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success: no issues found in 106 source files). Wymagania: 2.5, 2.6, 12.2.
### ✅ Blok local-ti4-data-foundation 11.5 + 11.6 — testy Vitest frontendu (Resolver_Zasobów i grafiki lokalne) (ukończony)
- Infrastruktura testowa Vitest była już skonfigurowana w `frontend/vite.config.ts` (środowisko `jsdom`, `globals`, `setupFiles: ./src/test/setup.ts`, `passWithNoTests`), ale brakowało dwóch zależności dev (pliki testowe nie istniały jeszcze w projekcie): `fast-check` (do 11.5) oraz peer `@testing-library/dom` wymagany przez `@testing-library/react@16` używany w `src/test/setup.ts`. Dodane do `frontend/package.json` z DOKŁADNIE przypiętymi wersjami (`--save-exact`, bez `^`): `fast-check@4.10.2`, `@testing-library/dom@10.4.2`.
- 11.5 (Property 17) — `frontend/src/shared/assets/resolveAsset.test.ts`: test właściwościowy `fast-check` (`numRuns: 100`) sprawdzający, że dla DOWOLNEJ logicznej ścieżki `assetUrl`/`sheetUrl` zwraca wyłącznie napis lokalny (`/static/...` albo `PLACEHOLDER_URL`), NIGDY nie zawiera `://` ani hosta zewnętrznego. Osobny generator celowo wstrzykuje adresy CDN/URL-e (`images.asyncti4.com`, `emoji-cdn.mqrio.dev`, `fc.webUrl()`, losowe `scheme://host/...`) — wynik i tak jest lokalny. Dodatkowe przypadki: wiodące slashe i pusta ścieżka → placeholder. **Validates: Requirements 2.1, 2.6.**
- 11.6 — `frontend/src/shared/assets/localAssets.test.ts` (Vitest): (a) żaden plik źródłowy w `frontend/src` (poza `*.test.ts(x)`) nie importuje usuniętego `cdnImage` i plik `cdnImage.ts` nie istnieje (R2.2); (b) `getFactionImage` zwraca ścieżkę lokalną także dla dawnych ikon typu `EMOJI`/`DISCORD` (R2.4); (c) `sheetUrl` oraz `getUnitSprite` (jednostka kolorowa i współdzielona) dają lokalny obraz sheetu (R2.1); (d) `assetManifest.json` (artefakt frontu) jest DOKŁADNIE zgodny ze zbiorem ścieżek z jednego źródła prawdy `audit/assets_manifest.json` — brak nadmiarowych i brakujących (R3.1).
- Bramka frontendowa zielona: `npm run type-check` (czysto), `npm run test` (`vitest --run` → 2 pliki, 14 testów, wszystkie pass), `npm run build` (`tsc && vite build` OK, exit 0). `npm run lint` zgłasza WYŁĄCZNIE 2 PREISTNIEJĄCE błędy w `src/domains/rules/RulesBrowserPage.tsx` (plik niemodyfikowany, poza zakresem 11.5/11.6); oba nowe pliki testowe przechodzą lint osobno (`eslint` na nich → 0 problemów).
- UWAGA: niezacommitowane zmiany innej osoby (`assets/config/engine_config.json`, `src/api/schemas.py`, `src/core/*`, `frontend/src/api/useNewGame.ts`, `frontend/src/domains/setup/*`, nowe pliki `frontend/public/faction_portraits/*`) NIE były ruszane ani stagowane. Staging TYLKO moich plików: `frontend/src/shared/assets/resolveAsset.test.ts`, `frontend/src/shared/assets/localAssets.test.ts`, `frontend/package.json`, `frontend/package-lock.json`, `.kiro/specs/local-ti4-data-foundation/tasks.md`, `docs/PROGRESS.md`. Wymagania: 2.1, 2.2, 2.4, 2.6, 3.1.

### ✅ Blok local-ti4-data-foundation 13.1 — numeracja RULES.md + sekcja wyników audytu (ukończony)
- Ujednolicona numeracja `docs/RULES.md`: usunięte duplikaty numerów sekcji. Dawna „3 (bis)" (Limity sztuk jednostek) → `3a` (konwencja lettered-subsekcji jak `2a/2b/2c`). Druga sekcja „30" (Limity rąk i poziomy trudności bota) → `36`, przeniesiona fizycznie na koniec pliku, by kolejność w pliku = kolejność numeryczna (29, 30…35, 36). Podsekcje `30.1/30.2` → `36.1/36.2`.
- Spis treści uzupełniony o dotąd brakujące wpisy sekcji 31, 32, 33, 34, 35 oraz nowych 36 i 37 (wcześniej TOC kończył się na 30). Odwołania do sekcji 34/35 pozostają stabilne.
- Zaktualizowano odwołania w kodzie wskazujące na sekcję limitów rąk/trudności „RULES.md 30" → „RULES.md 36" (tylko komentarze/docstringi): `src/core/registry.py`, `src/core/setup_service.py`, `src/core/models.py`, `src/api/schemas.py`, `src/api/routers/game.py`, `src/config.py`, `assets/config/engine_config.json`, `frontend/src/api/useNewGame.ts`, `tests/test_registry.py`. Odwołania do akcji strategicznej („RULES.md 30" = sekcja 30) pozostały nienaruszone.
- Dodana sekcja `37. Wyniki audytu danych`: (37.1) tabela liczb komponentów per Źródło_Kanoniczne — ludzkie podsumowanie maszynowego `audit/baseline_counts.json` (zero liczb z pamięci; źródło `StaticDataCatalog.counts()`, zgrane z `uv run python -m src.audit --json`); (37.2) znane luki referencyjne homebrew udokumentowane jako NIE-usterki: `explores_cpti` (18 refów), `mirage`, `gamma`/`gw`, `ion`; (37.3) anomalia `codex1` w `theodisi.json` jako ⚠️ ZAŁOŻENIE (D6); (37.4) wpisy ⚠️ ZAŁOŻENIE: `TRIGGER_WINDOW_MAP` (D10, link do sekcji 34) i placeholder `<color>` (link do sekcji 35), z prośbą o potwierdzenie; (37.5) komendy odświeżenia liczb.
- Nowy test `tests/test_docs_numbering.py`: identyfikatory `## N.` są unikalne (blokuje ponowne duplikaty), sekcja audytu 37 istnieje, wpisy założeń (`TRIGGER_WINDOW_MAP`, `<color>`, `explores_cpti`) obecne.
- Bramka QA zielona: `uv run pytest -q` (441 passed), `uv run ruff check src tests` (All checks passed!), `uv run mypy src tests` (Success, 107 plików), `npm run type-check` (czysto — zmiana w `useNewGame.ts` to tylko komentarz).
- UWAGA: równolegle trwa zadanie 13.2 edytujące inne pliki docs. Staging TYLKO moich plików (nie `git add .`). Wymagania: 6.6, 12.4, 12.7.

### ✅ Blok local-ti4-data-foundation 13.2 — dokumentacja fundacji danych + `.gitignore` (ukończony)
Domknięcie dokumentacji po całej fundacji danych (zadania 1–12 zrealizowane). Blok tylko
docs + `.gitignore` (bez zmian w kodzie → QA backendu/frontendu niekonieczna). Wymagania: 3.3, 12.3, 12.5.

- **`docs/README.md`** — sekcja 3 (struktura repo) rozbudowana o nowe moduły fundacji:
  `core/sources.py`, `core/components.py` (Katalog_Komponentów), `core/component_loader.py`,
  `core/references.py`, `core/timing_spec.py`, `core/effects_registry.py`, `core/rules_links.py`,
  cały katalog `src/audit/` (Audytor_Danych: `locality.py`, `assets_manifest.py`, `frontend_data.py`,
  `diffs.py`, `report.py`, `sync_assets.py`), router `api/routers/components.py`, Resolver_Zasobów
  (`frontend/src/shared/assets/`) i katalog `audit/` (manifest + baseline w repo, D1). Usunięte
  framingi „grafiki z CDN"; sekcja 4 dostała bullet o pełnej lokalności offline (Resolver_Zasobów,
  `@fontsource/*`, manifest + `sync_assets`, `uv run python -m src.audit`).
- **`docs/ARCHITEKTURA_KODU.md`** — mapa §2 uzupełniona o wszystkie nowe moduły `core/` i warstwę
  `src/audit/`; §4 (routery) dostał wiersz `api/routers/components.py` (tylko-odczyt); nowa sekcja
  **§4a „Fundacja danych i Audytor_Danych"** opisująca Katalog_Komponentów, wybór po `source` (D9),
  Specyfikację_Czasową (D10), Rejestr_Efektów (pod hooki, bez efektów kart), powiązania z regułami
  i lokalność grafik/fontów (D1/D12).
- **`docs/ARCHITEKTURA_PO_MIGRACJI.md`** — poprawione wszystkie opisy „grafiki z CDN /
  images.asyncti4.com": obraz całości, diagram ASCII i §4.1 (dawny `cdnImage.ts` → Resolver_Zasobów
  `resolveAsset.ts`, grafiki z `/static`, fonty `@fontsource/*`, D1/D11).
- **`.gitignore`** — nagłówek sekcji ASSETY opisuje decyzję D1 (grafiki/fonty POZA repo; lokalność
  przez `audit/assets_manifest.json` + `src.audit sync_assets --from <katalog>`); komentarz przy
  `assets/config/effects_status.json` tłumaczy Rejestr_Efektów (D12). Dodany blok dokumentujący, że
  konfiguracja Audytora i manifesty SĄ wersjonowane — `audit/assets_manifest.json`,
  `audit/baseline_counts.json` (D1: MUSZĄ być w repo), `expected_gaps.json`, `external_url_allowlist.json`,
  `unused_asset_dirs.json` oraz `frontend/src/shared/assets/assetManifest.json`.
- **Stan `.gitignore` zweryfikowany (`git check-ignore`):** grafiki (`assets/units/sheets`,
  `assets/factions`, `assets/tokens/sheets`) są ignorowane (poza repo, D1); `audit/*.json`,
  `assets/config/effects_status.json` i frontendowy `assetManifest.json` NIE są ignorowane i są
  śledzone (`git ls-files`). Żadnych nowych wyjątków nie trzeba było dodawać — wpis w `.gitignore`
  dokumentuje decyzję i zabezpiecza przed przyszłą szeroką regułą `audit/*`.

**Następny krok:** zadanie 14 (final checkpoint — pełny `uv run pytest -q` / `ruff` / `mypy` oraz
front type-check/lint/build zielone) i decyzje D1–D12 do potwierdzenia przez użytkownika.

---

### ✅ Strażnik anty-hardkodowania danych + instrukcja Katalogu_Komponentów (ukończone)
- Nowy test `tests/test_no_hardcoded_data_guard.py` (skanery AST, wzór
  `test_locality_guard.py`) pilnujący, by przyszłe moduły faktycznie używały lejka
  danych zamiast go obchodzić. Dwa testy:
  - **`test_zrodla_kanoniczne_tylko_w_sources_py`** — kolekcja literałów z ≥3 nazwami
    źródeł kanonicznych (`base`/`pok`/`codex1-4`/`thunders_edge`) jest DOZWOLONA tylko
    w `src/core/sources.py` (`SOURCE_PRIORITY`). Pojedyncze porównania (`source == "pok"`),
    komentarze i docstringi nie są łapane (odporność na fałszywe alarmy). Łapie
    „ktoś przekleił listę źródeł zamiast zaimportować `SOURCE_PRIORITY`".
  - **`test_dane_gry_czytane_tylko_przez_rejestr_i_loader`** — żaden plik w `src/core/`
    (poza `registry.py`, `component_loader.py`, `references.py`, `components.py`) ani
    `src/api/` nie odwołuje się do `config.<KATEGORIA>_DATA_DIR` RAZEM z odczytem dysku
    (`glob`/`open`/`read_*`) ani nie globuje `assets/data/<kategoria>`. Kategorie starsze
    (units/technologies/factions/leaders/abilities/breakthroughs) wyłączone — czyta je
    celowo `registry.py`. Lista katalogów kategorii wyliczana z modułu `config`, więc
    test nie rozjeżdża się przy dodaniu nowej kategorii.
- **Wynik skanu:** ZERO naruszeń w istniejącym kodzie — architektura jest lejkowa
  (`SOURCE_PRIORITY` importowany wszędzie z `sources.py`; dane kategorii czytane wyłącznie
  przez `load_components`/`StaticDataRegistry.catalog`).
- `docs/README.md`: nowa sekcja **„4a. Jak korzystać z Katalogu_Komponentów"** z
  przykładem (`catalog.all/get/faction_bundle/query_timing`), listą endpointów API i
  gwarancjami (filtr po `source`, regresja liczb, test anty-hardkodowania).
- QA zielone: `uv run pytest -q`, `uv run ruff check src tests`, `uv run mypy src tests`.

### ✅ Blok E8-T3b — popup decyzji secondary (follow/don't follow) + blokada End turn (ukończony)

**Cel (ustalenie z użytkownikiem):** gdy aktywny gracz ZAGRA kartę strategii, pozostali
gracze — po kolei, od gracza na lewo od aktywnego, zegarowo — dostają JAWNY wybór
„follow / don't follow" secondary (język planszówki). Dopiero gdy WSZYSCY zdecydują,
aktywny gracz może dać „End turn". Co dokładnie robi follow (efekt liczbowy) — poza
zakresem; tu tylko wybór i przesunięcie kolejki. Tryb: dziś hot-seat na jednym
komputerze, docelowo sieć — dlatego pyta graczy po kolei, nie zakłada jednego operatora.

**Backend (sędzia — RULES.md 31.6, R_strategic_action):**
- [x] `src/core/turn_flow.py::end_turn` — twarda blokada: gdy `state.pending_window is not
  None`, `ValueError` → HTTP 422 („Cannot end the turn while a timing window is open…").
  Dotyczy KAŻDEGO typu okna (secondary, assign-hits, space cannon, reakcja), nie tylko
  secondary — turę oddaje się tylko „między" oknami. Okno secondary już otwierał
  `strategic_action.play_strategy_card` (T3), a `/strategy/secondary` (execute true/false)
  przesuwa kolejkę i auto-zamyka po ostatnim graczu — bez zmian.
- [x] `docs/RULES.md` — nowa podsekcja 31.6 (End turn zablokowany, dopóki trwa okno;
  źródło R_strategic_action; „follow"/„don't follow" = `execute` true/false; popup +
  wygaszony End turn).
- [x] `tests/test_turn_flow.py::test_end_turn_blocked_while_timing_window_open` (nowy).

**Frontend (język planszówki + popup):**
- [x] `frontend/src/domains/game-shell/components/SecondaryDecisionModal.tsx` (NOWY):
  nieodrzucalny popup (`AppModal`, bez krzyżyka / klik poza / Escape) pytający BIEŻĄCEGO
  respondenta okna `STRATEGY_SECONDARY`: „Follow" (execute=true) / „Don't follow"
  (execute=false). Pokazuje ikonę+nazwę gracza, nazwę karty (z `context.initiative`) i ilu
  graczy jeszcze po nim. Adresuje po `currentResponderId`; znika, gdy backend domknie okno.
- [x] `frontend/src/pages/GameMapPage.tsx` — modal zamontowany obok pozostałych modali.
- [x] `TurnControls.tsx` i `GameStatePanel.tsx::PhaseControls` — „End turn" WYGASZONY
  (`disabled`) i z tooltipem, dopóki `pendingWindow` ≠ null; dodatkowa podpowiedź w
  `TurnControls`.
- [x] `GameStatePanel.tsx::WindowSection` — dla secondary etykiety przycisków panelu
  bocznego zmienione na „Follow" / „Don't follow" (inne okna zostają przy Execute/Pass).

**QA (wszystko zielone):** backend `uv run pytest -q` 482 passed (było 481, +1), ruff +
mypy --strict czyste (110 plików). Frontend `npm run type-check`, `npm run lint`,
`npm run build` czyste (warn o rozmiarze chunku bez zmian).

**Następny krok:** dokładanie realnych efektów secondary kartą po karcie (dispatch w
`strategic_action`, RULES.md 30) oraz kolejne typy okien (assign-hits w walce — T7/T8).

### ✅ Blok E8-T3b-fix — aktywny gracz nie znika po pasie / zamknięciu okna (ukończony)

**Zgłoszenie użytkownika:** po tym, jak aktywny gracz w fazie akcji SPASUJE (pas jest
„jak akcja" — trzeba potem i tak oddać turę) albo gdy po zamknięciu okna secondary gracz
jest spasowany, przycisk „End turn" ZNIKAŁ — nie dało się dokończyć tury.

**Diagnoza:** web-data gasi aktywnego gracza do PODŚWIETLENIA, gdy jest `passed`
(`_effective_active_id` → `activePlayer`=null, `playerData[].active`=false, Bug 7). Panel
tury (`TurnControls`/`useDeskPlayer`) opierał „czyja tura" właśnie na tych polach, więc po
pasie tracił gracza i chował przyciski. Backend przez cały czas trzymał poprawne
`active_player_id` (end_turn działał na 200) — problem był czysto w projekcji/UI.

**Naprawa (rozdział „podświetlenie" vs „czyja tura"):**
- [x] `src/api/web_data.py` — NOWE pole `gameState.activeTurnPlayer` (kolor gracza wg
  `active_player_id`, BEZ gaszenia przez `passed`; przez `_color_of`). `activePlayer`
  (highlight) bez zmian — dalej gaśnie dla spasowanego (Bug 7).
- [x] `frontend/src/entities/data/types.ts` — pole `activeTurnPlayer?: string | null`.
- [x] `useDeskPlayer` — „gracz pulpitu" najpierw po `activeTurnPlayer`, potem fallback na
  `playerData[].active`/mówcę/pierwszego posadzonego (zgodność ze starymi migawkami).
- [x] `TurnControls` — `isAction` liczony z `activeTurnPlayer` (czyja tura), nie z
  `active.active` (gaśnie przy passed).
- [x] `GameStatePanel.PlateBody` — gracz tury z `activeTurnPlayer ?? activePlayer`
  (status karty / canPass / PhaseControls nie gubią gracza po pasie).
- [x] `tests/test_web_data.py::test_active_turn_player_survives_pass_in_action_phase`
  (nowy): spasowany aktywny gracz → `activePlayer`=null, ale `activeTurnPlayer`=jego kolor.

**QA (wszystko zielone):** backend `uv run pytest -q` 483 passed (+1), ruff + mypy czyste;
frontend type-check + lint + build czyste.


### ✅ Blok E8-T3b-ui — reguła „akcja albo pas przed End turn" + dopieszczony UI tury (ukończony)

**Zgłoszenia użytkownika:** (1) box potwierdzenia pasa rozpychał panel (resize, brak
spójności); (2) ważna reguła — gracz musi wykonać JAKĄŚ akcję (strategiczna/taktyczna/
komponentu) albo spasować, i dopiero wtedy może dać End turn; (3) wyłączony przycisk dalej
miał kolor akcji — ma być szary; (4) „Next phase" nie powinien wyglądać na szary (wyblakły).
Dodatkowo potwierdzenie: ZAGRANIE KARTY STRATEGII to akcja (odblokowuje End turn).

**Backend (sędzia — RULES.md 31.7, R_action_phase):**
- [x] `PlayerState.took_action_this_turn` — flaga „akcja w bieżącej turze".
- [x] Ustawiana: `strategic_action.play_strategy_card` (akcja strategiczna = zagranie karty),
  `tactical.activate_system` (akcja taktyczna). Resetowana w `turn_flow.end_turn` (następny
  gracz) i `next_phase` (wejście w fazę akcji).
- [x] `turn_flow.end_turn` — 422, gdy aktywny gracz nie wykonał akcji ANI nie spasował.
- [x] `web_data`: `playerData[].tookActionThisTurn` do frontu.
- [x] `docs/RULES.md` 31.7; testy: `test_turn_flow` (wymóg akcji/pasu + reset flagi),
  `test_strategic_action_api` (zagranie karty = akcja → End turn bez pasu po oknie).

**Frontend (UI):**
- [x] Potwierdzenie pasa = MODAL (`AppModal`), NIE inline — panel tury nie zmienia rozmiaru
  (stabilny, spójny UI). Dotyczy `TurnControls` i `GameStatePanel.PhaseControls`.
- [x] „End turn" aktywny dopiero gdy `tookActionThisTurn || passed` i brak okna; inaczej
  SZARY + podpowiedź „Take an action or pass, then End turn." Po akcji/pasie pulsuje (nudge).
- [x] Wyłączone przyciski = SZARE (neutralne), bez barwy akcji (CSS `:disabled` w obu panelach).
- [x] „Next phase" dostał realny akcent (color-mix na `--ds-accent`), nie wygląda na szary.
- [x] `types.ts`: `GameState.activeTurnPlayer` (z poprzedniego bloku) + `PlayerData.tookActionThisTurn`.

**QA (wszystko zielone):** backend `uv run pytest -q` 486 passed, ruff + mypy czyste; frontend
type-check + lint + build czyste.
