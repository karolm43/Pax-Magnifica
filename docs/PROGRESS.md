# Postęp projektu — Custodian Engine

Plik śledzi stan prac między sesjami. Aktualizowany na koniec każdego bloku.
Starsze, ukończone bloki (Faza 1 → bloki do 2026-11-19) są w `PROGRESS_ARCHIWUM.md` (czytaj punktowo).

> **Aktualny etap:** E8 (silnik-SĘDZIA) + hooki: karty, relikty, technologie ogólne, cele, karty strategii,
> agendy ✅; frakcje (Fala 2) w toku; bot: B0–B1, B3 ✅, B2 rdzeń, następne B2 (bench) / B5 (`docs/bot/PLAN.md`).
> Stan pokrycia: `POKRYCIE_HOOKOW.md` (generowany). Reguły: `RULES.md` 29, 43, 53, 65.

## Status etapów silnika

| Etap | Zakres | Status |
|---|---|---|
| Faza 1 | Cyfrowa plansza + God-Mode (dane, mapa, setup, edycja, Undo) | ✅ ukończona |
| F0–F18 | Migracja na frontend ti4_web + panele graczy + God-Mode UI | ✅ ukończone |
| E1–E2 | Fazy + kolejność tur + faza strategii | ✅ ukończone |
| E3 | Akcja taktyczna (aktywacja, ruch, walka, inwazja, produkcja) | ✅ fundament |
| E4 | Kontrola komponentów (exhaust/refresh) + menu RMB | ✅ ukończone |
| S | Karty strategii 1–8: primary + secondary (`core/strategy_cards/`) | ✅ ukończone |
| E8 | Silnik-SĘDZIA: walidacja reguł + okna czasowe (T1–T7 + faza akcji 31.7/31.8, audyt 31.9) | 🔧 w toku |
| C | Punkty centralne C1–C9 (strażnik architektury) | ✅ ukończone |
| H1–H3 | Hooki: rejestr, punkty MODIFY/PERMIT/FORBID, raport pokrycia | ✅ ukończone |
| H1b | Reakcje z cofnięciem: hold-play (Sabotage) + hold-rewind (HOLD) | ✅ (RULES.md 53.6, 53.7) |
| H4 | Karty akcji: ACTION + reakcje w oknach + przeciąganie z ręki | ✅ 143/143 |
| — | Relikty (23/23 aktywnych), technologie ogólne (33/33), cele (80/80 automatycznie) | ✅ |
| E6 | Faza agendy (głosowanie, remis, prawa); efekty agend | ✅ cała faza + efekty talii oficjalnej (50/50); ⬜ Absol (60) |
| H5 | Frakcje: zdolności, liderzy, notki, przełomy, technologie frakcyjne | ⬜ (technologie 36/102) |
| N | Sieć: N0 `actor_id` ✅, N1 tokeny ✅, N2 projekcja ✅, N3 zapis ✅, N5 część 1 ✅; N4 współbieżność ⬜ | 🔧 |
| QA | pytest-xdist/testmon, E2E Playwright (solo + host/gość) | ✅ |

**Następne kroki (kolejność):** efekty agend Absol → hooki at_start/at_end/during (16 zdarzeń jeszcze nieemitowanych,
`OKNA_CZASOWE.md`) → frakcje (zdolności, liderzy, promissory notes) → N4/N5 część 2 → bot.

> Pełna historia ukończonych bloków ze szczegółami: `PROGRESS_ARCHIWUM.md`.


## 2026-11-22 — B12: The Naalu Collective (RULES.md 62.16)

- ✅ `core/hooks/factions/naalu.py`: Telepathic, Foresight, Gift of Prescience, Neuroglaive, Hybrid Crystal
  Fighter II, Matriarch, Iconoclast TE, Z'eu (TE), M'aban (Codex), The Oracle, Mindsieve. Starsze warianty
  (Z'eu/Z'eu Ω, M'aban PoK, Iconoclast/Iconoclast Ω) = `na` w `rulings_status.json`.
- Rdzeń (punkty ogólne, bez nazw frakcji):
  - Żeton „0”: `core/initiative_zero.py` (efekt gracza, inicjatywa 0 w `turn_flow.turn_order` /
    `strict_initiative_order`, zdejmowany przy zwrocie kart strategii w `status_phase.finish_status`); okno reakcji
    „koniec fazy strategii” (`reactions_misc.strategy_phase_end`) dla notek z ręki.
  - `command_tokens.place_token` = jedyne położenie żetonu w systemie + nowe zdarzenie `COMMAND_TOKEN_PLACED/AFTER`
    (aktywacja, odwrót, Diplomacy, Signal Jamming, Stymie...).
  - Pula floty: PERMIT `fleet_pool.fighters_overflow` + MODIFY `fleet_pool.fighters_per_ship` (HCF II = 1/2 statku,
    w górę); `FleetReport.excess_after`, usuwanie nadwyżki bez zbędnych jednostek.
  - Inwazja: FORBID `invasion.ground_force_types` (`ship_roles.ground_force_types`) — myśliwce Matriarch lądują,
    walczą, obrywają w Space Cannon Defense, wracają do przestrzeni po walce i przed Establish Control
    (`invasion.return_ships_to_space`); widok inwazji w API pokazuje je jako siły do lądowania.
  - `core/peek.py` + FORBID `info.peek`: stały podgląd (M'aban) w web-data `gameState.peek`; talia agend zasiewana
    przy odblokowaniu M'aban.
  - `combat.resolve_unit_variant` i `web_player_units`: przy remisie rangi wygrywa wariant z `faction.units`
    (wcześniej kolejność rejestru dawała Iconoclast PoK zamiast TE).
  - Dacxive Animators: tylko z ocalałą siłą naziemną na planecie (F_naalu matriarch 3).
- UI: znacznik żetonu „0” na płytce karty strategii (`StrategyCard zeroToken`, `gameState.initiativeZero`), podgląd
  M'aban w liniach podglądu ręki (`BottomHandDock`), efekt bohatera The Oracle (`heroBoardFx.ts`). Oferty
  (Foresight, Z'eu, The Oracle, Iconoclast) i Mindsieve (Available now) idą przez wspólne okna.
- Rulingi `F_naalu` z testami (`tests/factions/test_naalu.py`, scenariusze `test_flows_naalu.py`); F_muaat umbat 4/4.1
  → `na` (aktywny M'aban nie produkuje). Luka: Neuroglaive przy Mahact (`requires faction:mahact`).
- ⚠️ Założenia do potwierdzenia: Foresight zabiera siły naziemne z przestrzeni automatycznie (mechy, potem piechota,
  do pojemności); Gift of Prescience gra się w oknie po komplecie kart strategii, zanim mówca kliknie „Next phase”.

## 2026-11-22 — Naalu: wybór + „Auto” w Foresight, pauza końca fazy strategii

- Decyzja użytkownika: każdy wybór gracza = wybór ręczny + „Auto” (także `CLAUDE.md`). Ogólnie:
  `oi.number(..., auto=N)` — UI wstawia wartość Auto i pokazuje przycisk „Auto” (`DecisionField`), pominięte pole
  = Auto (`validate_params`, `single_params`, bot).
- Foresight: gracz wybiera, ile mechów i piechoty z przestrzeni zabrać (pola `carry_mech` / `carry_infantry`,
  Auto = do pojemności, najpierw mechy — ⚠️ ZAŁOŻENIE); ponad pojemność = 422, niezabrane zostają.
- Pauza ochronna (54.10) w oknie „koniec fazy strategii”: `PAUSE_POINTS` (`PHASE/END`), uprawnieni = gracze z notką
  w ręce poza właścicielem notki frakcji reagującej w oknie (`promissory_play.faction_note_owners`, jawne);
  `turn_flow.next_phase` z fazy strategii czeka na koniec pauzy.
- Poprawka: oferty z położenia żetonu w trakcie primary (Diplomacy + Z'eu) nie otwierają własnego okna — czekają
  w oknie secondary (fuzz seed 11 stał).
- QA: pytest (factions, engine, reaction pause, strategia) ✓, ruff/mypy ✓, tsc ✓, eslint ✓, vitest (offers, api) ✓.
  Pełnego pytest nie puszczałem na tym drzewie: równoległa sesja ma niezacommitowane zmiany (Vuil'raith,
  `transaction.py` — czerwony `test_pride_of_kenara_w_gravity_rift_rzut` to jej zmiana). Build/e2e pominięte
  (bez nowych modułów frontu).

## 2026-11-22 — I1 Przechwytywanie (capture) + B13 The Vuil'raith Cabal (RULES.md 61.5, 62.17)

- **I1 capture** (`core/capture.py`, punkt centralny): `PlayerState.captured_units` (statki/mechy wg pierwotnego
  właściciela, także własne) i `captured_tokens` (żetony myśliwców/piechoty z puli). Rezerwa właściciela bez
  przechwyconych (`production.reinforcements_left`), zniszczenie → hook PERMIT `capture.destroyed`
  (`unit_ops.remove_units`), z rezerwy / z planszy bez zniszczenia, zwrot (pudełko po eliminacji), blokada doku
  oddaje statki od razu (`step_settle` → `capture.release_blockaded`), zakaz przechwytywania od blokującego,
  transakcja zwraca statki/mechy tylko właścicielowi (`TransactionSide.captured_units`). Widok: `nombox`
  w web-data (komponent `Nombox`, teraz z pełną nazwą frakcji). Feed: `ability_notes` „captured …”.
- **Anomalie z jednostek** (`core/map_anomalies.py`, `HexGrid.sync_extra_anomalies`): Dimensional Tear czyni system
  gravity rift dla wszystkich; własne statki Cabal nie rzucają (`movement.rift_roll_nodes`, `rolls_at`).
  Pojemność „Up to N fighters” z tekstu zdolności doku (dane bez `capacityValue`).
- **Cabal** (`hooks/factions/cabal.py`): Devour, The Terror Between (także po zniszczeniu w tej rundzie),
  Reanimator, Amalgamation (pole produkcji `captured`, chipy w `ProductionOverlay`), Riftmeld (skip
  `captured:<właściciel>`, sekcja w `TechnologyOverlay`), Vortex, The Stillness of Stars (oferta po uzupełnieniu
  commodities; zamiana bez „gain”), That Which Molds Flesh (2 myśliwce/piechota poza limitem, unlock 3 szczeliny),
  Dimensional Anchor (rzut raz na statek, nadwyżka ładunku przez okno CAPACITY też przechwycona), Crucible
  (bez rzutów, jedno dodatkowe +1, także z Nav Suite), Al'raith Ix Ianovar (Fracture bez rzutu, przesunięcie
  2 ingressów do szczelin — Available now, +1 ruchu z The Fracture).
- Poprawka: oferty „after replenishes” w trakcie primary Trade czekają w oknie secondary
  (`economy.replenish_commodities(open_window=False)`) — wcześniej blokowały otwarcie okna secondary.
- Rulingi: `F_vuilraith` + `R_capture` (usunięty z długu, limit 211) z testami (`tests/test_capture.py`,
  `tests/factions/test_cabal.py`, scenariusze `test_flows_cabal.py`). Statusy: Amalgamation 5 i Stillness 4 (`gap`),
  Anchor 5 / R_capture notes 4 (`requires` Nekro/Yssaril).
- ⚠️ Do decyzji użytkownika: Trade primary zbiera wybór graczy z darmowym secondary PRZED primary, więc agent wybiera
  już po nim (ruling Stillness 4); okno przesunięcia ingressów trwa do końca tury, w której przełom wszedł do gry.
- Stół transakcji: sekcja „Captured units” (stepper na typ, sylwetka w barwie partnera, tylko statki/mechy
  partnera z Nombox, tylko gdy wolno kłaść komponenty), podsumowanie „Returns captured …”; scenariusz API
  `test_transakcja_zwraca_przechwycony_statek`. Przy okazji: brak `hint` w `DecisionFields.test.tsx` (tsc).

## 2026-11-23 — Cabal: przesunięcie ingressów zaraz po wejściu Fracture

- Decyzja użytkownika: Al'raith Ix Ianovar przesuwa ingressy od razu po rozłożeniu ich wg zasad, nie
  w oknie „Available now” do końca tury. Nowe zdarzenie `GameEvent.FRACTURE_INGRESS_PLACED`
  (`fracture.announce_ingress_placed`: po `_enter` bez wyborów i po ostatnim `choose_ingress`); hook
  Cabal = oferta (`ingress_offer`). Fracture już w grze → oferta od razu po wejściu przełomu.
- QA: pytest (Cabal, Fracture/ekspedycje, zdarzenia, triggery) ✓, ruff/mypy ✓.

## 2026-11-23 — Frakcja The Titans of Ul (B14, RULES.md 62.18) + żetony frakcyjne na mapie (I2, 61.6)

- **Żetony frakcji** (`core/faction_tokens.py`, `SystemState.faction_tokens = {strefa: {rodzaj: właściciel}}`):
  sleeper ×5 (AsyncTI4), place / move / remove, zwrot przy wymianie kafla (Nova Seed) i zniszczeniu planety.
  Widok: żeton `sleeper` na planecie w web-data, `sleeperTokensReinf` w panelu gracza, feed
  `faction_token` / `faction_token_removed`.
- **Titans** (`hooks/factions/titans.py`): Terragenesis (oferta po eksploracji: pula albo przeniesienie – klik
  planety), Awaken (migawka żetonów i PDS na `SYSTEM_ACTIVATED/WHEN`; per żeton PDS / mech+piechota / zostaw; PDS
  z planszy przy pustej rezerwie; cudza planeta bez sił naziemnych przejęta od razu, z siłami – walka w Invasion),
  Coalescence (reguła bazowa), Hel-Titan jako struktura i siła naziemna (FORBID `units.structure_ground_forces`:
  obrońcy, sporne planety, utrzymanie po walce, cel bombardowania bez tarczy; bez trafień SCD), Ouranos (DEPLOY
  z migawki), Hecatoncheires („mech zamiast PDS” w `place_structure` – Construction i Awaken), Tellurian
  (użycie w oknie: anuluje 1 trafienie walki / Space Cannon / bombardowania dowolnego gracza), Tungstantus
  (unlock 5 struktur; przełącznik w `ProductionOverlay`, TG przed zapłatą), Geoform (attachment `titanshero`:
  +3/+3, SPACE CANNON 5×3 dla kontrolera Elysium; karta przy planecie blokuje ponowne użycie), Terraform
  (attachment `titanspn` +1/+1 i 3 cechy – `planet_stats.traits`, `exploration.planet_traits(state=…)`, cele;
  notka nie wraca i nie leży w strefie), Slumberstate zdanie 3 (prośba → decyzja kontrolera Allow/Refuse).
- Zmiany wspólne: karty strategii (Construction, Warfare) produkują tylko dokami (`ProductionGrant.producer_types`,
  F_ul hel-titan 1); `invasion.cancel_bombardment_hits`; SPACE CANNON z attachmentów (`space_cannon`);
  attachmenty z notek i liderów (`planet_stats._card_attachment`); efekt bohatera na planszy `titanshero`.
- Rulingi `F_ul` (mapa `titans → F_ul`) z testami (`test_titans.py`, scenariusze `test_flows_titans.py`); Farran
  + Hel-Titan (F_letnev 2.1) ma test. Statusy `gap`: przełom zdania 1–2 (koegzystencja, blok I4), Hel-Titan 3
  (Decoy Operation / Transit Diodes).
- ⚠️ ZAŁOŻENIA (do potwierdzenia): Awaken – każdy żeton osobno, „Auto” = PDS; Tungstantus – „Auto” = włączone;
  Slumberstate – prośba w dowolnej chwili fazy akcji, bez akcji; Tellurian nie anuluje AFB (brak kroku przypisania).


## Efekty bohaterów na planszy — przegląd i nowe znaczniki frakcji (RULES.md 64.4)

- Ul the Progenitor (Titans) nie miał sceny ani efektu: Geoform nie purge'uje karty (dołącza ją do Elysium),
  więc feed nie miał faktu `leader purged`. `momentsForEntry` rozpoznaje teraz fakt `attached` z kartą bohatera
  (sprawca = `actor_id`, planeta w `planets`); cel efektu `planet` = system Elysium. Test backendu w
  `tests/test_activity.py`, testy frontu w `keyMoments.test.ts`.
- Cabal (Dimensional Anchor): wir startuje z systemów z dokami Cabal (Dimensional Tear, cel `docks`), macki sięgają
  do SĄSIEDNICH systemów (`neighborTiles` — siatka heksów, tylko wizualizacja) i wciągają ich okręty.
- Każdy bohater ma własny znacznik (`layers/HeroFxMarks.tsx` + `.module.css`): Letnev celowniki, Jol-Nar obwody,
  Mentak haki abordażowe, Argent podwójna spirala, Yin kapsuły z klonami, L1Z1X siatka materializacji + zakłócenia,
  Saar fala Armageddon Relay z doków, Naalu oko psioniczne + mgła, Titans szczeliny magmy / rdzeń tytana w płytach /
  3× SPACE CANNON, Cabal Event Horizon. Arborec dostał zarodniki, Sol rdzeń słupa, Xxcha siatkę tarczy.
- Nowe w przepisie: `quake` (wstrząs planszy przez `translate` kontenera kafli — nie psuje zoomu; wyłączone przy
  prefers-reduced-motion), przejścia `static` i `mist`, dźwięki dla wszystkich bohaterów.
- QA: vitest (KeyMoments, map), tsc app, eslint, pytest `test_activity`; zrzuty animacji (puppeteer) obejrzane.

## Efekty bohaterów: miejsce działania z feedu (fakty `area`, RULES.md 64.4)

- Przegląd wszystkich 18 bohaterów (Arborec … Titans): efekty z ACTION celowały zbyt szeroko (np. Sol świecił
  nad wszystkimi systemami z jednostkami). `core/activity.py` dopisuje we wpisie z użyciem bohatera (purge albo
  dołączenie karty) fakty `area` (pozycja + `gain`/`loss` jednostek gracza albo `token_removed`); feed ich nie
  wypisuje (`describeActivity`), `momentsForEntry` przenosi je do momentu (`areas`, `self` = bohater).
- Przepis może mieć `area` (zapasem zostaje `target`): Sol — systemy, z których zniknęły jego żetony (słup światła
  unosi żeton); Saar — system, gdzie rywale stracili jednostki; Argent / L1Z1X — systemy docelowe floty;
  Yin / Xxcha / Arborec — systemy z nowymi jednostkami. Bez wpływu na planszę (Jol-Nar, Naaz, Naalu, Winnu) bez
  zmian; reakcje (Hacan, Mentak, Sardakk, Muaat) — aktywny system / Nova Seed.
- Testy: `tests/test_activity.py` (fakty `area`), `tests/factions/test_hero_area_feed.py` (Sol/Saar/L1Z1X przez
  API), vitest `keyMoments`/`heroBoardFx`; zrzut efektu Sol obejrzany.

## 2026-11-23 — AFB przez krok przypisania (Shields Holding, Tellurian) + „Auto” w wyborach z listy

- Decyzja użytkownika: trafienia zwykłego AFB przypisuje właściciel myśliwców w kroku ASSIGN (jak Waylay;
  `afb_assign`, wymagany cel `hit_targets` = myśliwce, wybór + „Auto”), więc przed przypisaniem anulują je
  Shields Holding (C_action_cards 4.1) i Tellurian (RULES.md 39 W4, 53, 62.18).
- Shields Holding: audyt rulingów C_action_cards (1–5, 4.1) z testami, karta zdjęta z długu (limit 210).
  Naprawiony błąd: drugą Shields Holding gracz mógł zagrać na ten sam rzut (ślad w `combat.effects`).
- `oi.choice(auto=...)`: przycisk „Auto” w wyborach z listy (`DecisionFields`), pominięte pole = opcja Auto.
  Titans: Awaken = PDS, źródło żetonu = pula, Tellurian = trafienie we własne jednostki, Ouranos = pierwszy PDS,
  Terraform = planeta o najwyższej sumie wartości, Slumberstate: kontroler „Auto” = odmowa.
- QA: pytest całość ✓, ruff/mypy ✓, tsc/eslint/vitest (offers, ActivityPanel) ✓, e2e 8/8 ✓.


## Efekty bohaterów: Hacan, Sardakk, Winnu, Naaz-Rokha + poprawka wygaszania (RULES.md 64.4)

- Hacan (Sanction of the Quieron): szlaki handlowe zbiegają się do systemu, karawany, deszcz trade goods
  i obracająca się moneta Quieron. Sardakk (Brood Swarm): rój N'orr nurkuje, uderzenia, trzy cięcia i żarząca
  się rana + wstrząs. Winnu (Sins of the Father, znacznik `crown`): korona stempluje Mecatol Rex, laur i promienie
  władzy przez planszę. Naaz-Rokha (Forge Legend, znacznik `forge`): runiczne pierścienie zgrywają się, iskry
  kuźni, kryształ reliktu i dwie karty strategii. Znacznik `seal` usunięty (żaden bohater go nie dzieli).
- Błąd: `fadeLate` dołączane jako druga animacja nadpisywało `opacity` animacji wejścia — elementy (liście
  Arborec, płyty tytana, oko Naalu, moneta…) były widoczne przed swoim momentem. Usunięte; całość i tak gaśnie
  z warstwą (`fxLife`).
- QA: tsc app, eslint, vitest (map, KeyMoments); zrzuty klatek obejrzane.

## Poprawka: rzuty kilku graczy naraz (Dimensional Anchor — bohater Cabal)

- Błąd: `state.table_roll` trzymał JEDEN rzut, a Dimensional Anchor zapisuje rzut osobno dla każdego
  przeciwnika — każdy nadpisywał poprzedni, więc UI animowało kości tylko ostatniego gracza (silnik rzucał
  poprawnie, raz na statek). Teraz `dice.record_table_roll` dopisuje też do `GameState.table_rolls`
  (ostatnie 12, web: `tableRolls`), a `TableRollWatcher` odtwarza po kolei wszystkie nowe rzuty
  (`domains/dice/tableRolls.ts`), każdy w kolorze rzucającego. Dotyczy każdego efektu z kilkoma rzutami.
- Test: `test_bohater_rzuty_kazdego_przeciwnika_widoczne`, `tableRolls.test.ts`.
- QA: pełny pytest, ruff, mypy (zmienione), tsc app, eslint, vitest `domains/dice`. Bez build/e2e.

## Poprawka: okno inwazji Yin (Quantum Dissemination) po animacji i bez pustej inwazji

- Błąd: okno inwazji komponentu otwierało się od razu, przed sceną i efektem bohatera na planszy, nawet gdy
  nie było wojsk przeciwnika (brak walki, SCD, bombardowania).
- `InvasionOverlay`: okno czeka na koniec kolejki momentów (`useHeroFx.stageBusy`); inwazja komponentu bez
  spornych planet przechodzi Commit/Establish sama (klient atakującego, jedno wywołanie na krok). Gdy krok
  się nie uda (np. eksploracja), okno zostaje z komunikatem. Backend bez zmian (reakcje po zaangażowaniu).
- QA: tsc app, eslint, vitest `domains/invasion`. Bez testu jednostkowego, bez build/e2e.

## Okna decyzji: płatność kafelkami + Leadership bez blokady 3 wpływu, z „Auto” (plan U2, część)

- `docs/PLAN_OKNA_DECYZJI.md`: dopisane decyzje użytkownika (P1 kafelki płatności, P2 siatka chipów/drag zamiast
  list, kolejka „+N”, kolejność U1→U6).
- `PaymentPicker` (PromptParts): planety jako `Tile` z `DecisionTiles` (jak w ofertach) zamiast kart planet —
  dotyczy wszystkich okien z płatnością (Leadership, technologie, status, Custodians, ekspedycje).
- Leadership: usunięta blokada zbędnego wydatku (płatność w dowolnej kwocie, informacja o reszcie), „Auto”
  przez `target` (rules/R30.md 30.7, ⚠️ ZAŁOŻENIE). Backend bez zmian (`paid // 3`).
- QA: tsc app, eslint (zmienione), vitest domains technology/invasion/game-shell/thunders-edge/offers.
  Bez testu Leadership, bez build/e2e, bez weryfikacji wizualnej.

## Okna decyzji — U1: wspólna rama `DecisionFrame` + jeden `ComponentUseModal`

- `shared/ui/DecisionFrame`: nagłówek (plakietka rodzaju, tytuł = nazwa/chip komponentu + ⓘ, czytelne
  „Required”, „+N more”), pełny tekst NORMALNYM kolorem (zwijany >420 zn.), pola, komunikaty (notes/warnings),
  stopka [Never ask] [Skip Esc] [akcja Enter]; skróty Enter/Esc w jednym miejscu; wariant `embedded` w oknie.
  Styl przeniesiony z `OffersDock.module.css` (tam zostały tylko pule żetonów).
- `OfferDock` (OffersModal) = `DecisionFrame` (zachowanie bez zmian: Never ask, Skip, Enter/Esc, Transit Diodes, pule).
- `ComponentUseModal` zastępuje treść 4 modali: `ActionCardPlayModal` (karta/relikt/frontier/notka),
  `TechnologyUseModal`, `LegendaryUseModal`, `FactionComponentUseModal` — cienkie nakładki; teraz też
  z chipem/ⓘ, pełnym tekstem, Enter/Esc, jednolitym „Cancel”, bez formularza dla wyczerpanych/zablokowanych
  (ostrzeżenie zamiast pól), błąd ładowania z przyciskiem Cancel.
- Okna kart strategii: bez drugiego tytułu AppModal („Strategic action” / „Strategy Card — secondary
  ability”), gdy widok karty ma własny nagłówek (PromptShell). Pełne przepięcie PromptShell na ramę — później.
- Poza zakresem U1 (zostaje na U2–U5): `Stepper`/`Payment`, strefa decyzji, duplikaty informacji, „Follow”
  nieaktywne bez wpływu.
- QA: tsc app, eslint, vitest (game-shell, offers, strategy, shared; nowy `DecisionFrame.test.tsx`),
  `npm run build`, `npm run e2e` (8/8). Bez weryfikacji wizualnej w grze.

## Okna decyzji — U2: jeden `Stepper`, jedna płatność (`PaymentTiles`), wspólny `AutoButton`

- `shared/ui/Stepper` zastępuje 5 kopii (PromptParts, DecisionTiles, TradingTable, RemovalWindowModal, kontrolki
  `CommandPools`); aria: „Less/More <label>”; wariant `bare` (same przyciski w wierszu z własną etykietą).
- `domains/offers/PaymentTiles`: jeden widżet płatności (kafelki planet + TG + pasek „Paid X / Y” + Auto). Adaptery:
  `PaymentField` (DecisionFields) i `PaymentPicker` (Leadership, technologie, status, Custodians, ekspedycje).
- `shared/ui/AutoButton`: jedno „Auto” przy polu (subtelne); przepięte: pola liczbowe/wybór, płatność, pule żetonów,
  usuwanie jednostek, walka (BattleCenter), przydział (AssignPanel), Production, Technology. Pominięte świadomie:
  `ExtraDicePicker` (Auto jest tam jedną z wzajemnie wykluczających się opcji). Nowe „Auto”: Leadership/Warfare
  (rozdział żetonów), Predictive Intelligence, cele „Spend…” (pule, mixed) — ⚠️ ZAŁOŻENIA w R30.md/R41.md.
- `CommandPools` (+`onAuto`, `current`) używany też przez `PoolDistributor` (Leadership, Warfare) i status (Auto przeniesione
  z osobnego przycisku do pul, bez pomarańczowego „secondary”).
- Poza zakresem: Stepper w Invasion/Production/Technology/SpaceCannon/Politics (inne widżety: reorder, kości) — do U-dalej.
- QA: tsc app, eslint (zmienione), vitest (offers, strategy, game-shell, map, technology, invasion, production, battle, shared;
  nowy `Stepper.test.tsx`), `npm run build`. `npm run e2e` (8/8). Bez weryfikacji wizualnej.

## Okna decyzji — U3: strefa decyzji i kolejka „+N” (mniej clutteru)

- `hooks/useDecisionZone.ts`: znaczniki w DOM `data-decision-zone` (każde okno decyzji: `DecisionFrame`) i
  `data-phase-window` (okno fazy: panel statusu, Rada, `PromptShell` kart strategii, okno „Follow” secondary);
  `useDomPresence`, `decisionZoneOverlaps`.
- Centrum „Decisions” przy otwartym oknie fazy nie jest drugim oknem: zwija się do pastylki z licznikiem „+N”
  (oferty + „Available now” + zaproszenia do stołu; wymagana decyzja = kolor ostrzeżenia). Klik pokazuje je
  chwilowo; po zamknięciu okna fazy wraca samo. Znaczniki „Ready”/okna czasowe nie są liczone (Z1, Z2).
- Dok ręki (`useDockCovered`): zwija się, gdy okno decyzji wchodzi na miejsce ROZWINIĘTEGO doku (pamiętana
  wysokość - bez migania) albo przy oknie pełnoekranowym; rozwinięcie chwilowe jak dotąd.
- Dymki mapy (`MapTooltipPositioner`) chowają się, gdy wchodzą na okno decyzji (Z10).
- Baner okna reakcji przy otwartym oknie decyzji jedzie na górę (pod zakładki; w Radzie - na pasek tytułu),
  komunikaty `NotificationArea` zjeżdżają pod niego (Z2).
- Nie zrobione (zostaje): oferta jako „kolejny krok” WEWNĄTRZ okna fazy (jest pastylka „+N”); pkt 6 planu
  (czytelniejsze „nie używasz”, np. „do not place” bohatera).
- QA: tsc app, eslint (zmienione), vitest (offers, hooks, game-shell, agenda, strategy, shared, map; nowy
  `useDecisionZone.test.tsx`), `npm run build`, `npm run e2e` (8/8). Bez weryfikacji wizualnej w grze.

## Okna decyzji — U4: usunięcie duplikatów informacji

- Respondent: panel boczny okna czasowego (`GameStatePanel`/`WindowSection`) pokazuje tylko kolejkę
  („Remaining in queue”), bez banera „Responding”; okno „Your call” nie powtarza „Remaining after you” (Z8).
- Agenda: „N votes available” usunięte z wyników (głosy tylko na liście miejsc Senatu); licznik „Agenda N of M”
  tylko w nagłówku Rady (Z3). Remis = klik zwycięskiego wyniku na podium (speaker; bez osobnej listy
  przycisków; nietypowe wyniki poza remisem wyszarzone). Agenda `manual` bez zmian (opis + „Resolve as chosen”).
- Kafelki opcji: bez natywnego `title` (opis przez ⓘ). Oferta: etykieta pola równa tytułowi ramy nie jest
  powtarzana (`FrameTitleContext` + `FieldHead`; ustawiane w `OffersModal`) (Z12).
- Akcja komponentu: lista bez kart akcji z ręki (zagrywane przeciągnięciem), nowy wstęp, ⓘ z opisem przy
  liderze/technologii/relikcie/przełomie (Z9).
- QA: tsc app, eslint (zmienione), vitest (offers, agenda, game-shell). Bez weryfikacji wizualnej w grze.

## Okna decyzji — U5: czytelność i ślepe uliczki (+ pkt 6 planu: czytelne „nie robię”)

- Secondary („Follow”): koszt jako osobna wyraźna linia („Cost: …”, także darmowe z nazwą źródła); silnik
  podaje `follow_blocked` w opcjach secondary (Leadership: < 3 wpływu albo pusta rezerwa, R30.md 30.7) -
  „Follow” nieaktywne z powodem (Z7). Respondent „free” nie jest blokowany.
- Leadership: `base_gain` i `per_token` z silnika w tekstach (bez stałej 3).
- Teksty zdolności frakcji/liderów: zdania z kropką, okno z dwukropkiem
  („…infantry. At the start of the status phase: Place…”) - `faction_components._sentence/_windowed` (Z12).
- Pasek „Your move / Waiting for”: powody wg fazy (`core/actor.awaiting`: `score`, `redistribute`, `vote`
  zamiast „take a turn” w statusie/agendzie). Coach „What now?” w trybie testowym hosta = jak lokalnie (tura
  gracza, nie „Watch the map”). Feed/powiadomienia: pełna nazwa frakcji zamiast „Player p1” (Z13).
- Pkt 6: opcje odmowy („Do not place”, „Decline …”, „- none -”) to osobny wiersz za „or” - kafelek z ⊘
  i przerywaną ramką, wybrany mówi „Chosen - click again to undo” (`isDeclineOption`, `DeclineRow`; pola
  zwykłe i mapowe). Oferty: „Don't use” zamiast „Skip”.
- QA: pytest (pełny, -n auto), ruff, mypy (zmienione), tsc app, eslint (zmienione), vitest (domains, shared,
  hooks), `npm run build`, `npm run e2e`. Bez weryfikacji wizualnej w grze.

## Okna decyzji — U6: wybór planet tylko na mapie, bez list rozwijanych

- Agenda „Elect Planet” (`domains/agenda/AgendaMapPick.tsx`): przycisk „Choose a planet on the map” na podium
  chowa Radę do paska; świecą planety-wyniki (remis: tylko remisowe); klik wraca do Rady z wyborem (remis =
  rozstrzygnięcie mówcy). Lista wyników dla planet = tylko podgląd głosów.
- `DecisionFields`: bez `Select`/`MultiSelect` - powyżej 18 opcji siatka kafelków przewijana z pomocniczym
  filtrem (decyzja P2).
- Przegląd U1–U4: bez błędów do poprawy. Uwaga: dymek mapy schowany nad oknem decyzji wraca po ruchu kursora.


## Panel akcji taktycznej: cofnięcie aktywacji, licznik w kółko, jedna inwazja

- „Undo last move” bez żadnego ruchu cofa aktywację systemu („Undo activation”; `/tactical/undo-move` przyjmuje
  etykietę `tactical:activate:*`, gdy nie trwa okno) — RULES.md 44.1a; web-data `tacticalMoved`.
- `RouteUnitChip` (ruch, trasa na mapie, oferty ruchu): klik +1, na komplecie (2/2) przekręca do 0; prawy −1 bez zmian.
- Inwazja raz na akcję (RULES.md 40.1 I9): `GameState.invasion_resolved`, web-data `invasionResolved`; po zamknięciu
  panel nie pokazuje ponownie „Start invasion”.
- Testy: `test_undo_move.py`, `test_invasion.py`, `RouteUnitChip.test.tsx`.


## Przycisk „Component”: niedostępne pozycje szare, opis ⓘ dla każdej

- `collectComponentActions` niesie `unavailable` z web-data: lider wyczerpany/zablokowany/purge, tech i relikt
  wyczerpany (`exhaustedTechs`/`exhaustedRelics`), przełom i legendarna planeta wyczerpane — wiersz szary z powodem.
- Przycisk „Component” szary, gdy nic nie da się zagrać (lista, fragmenty reliktów, zdolności techów bez akcji);
  opcje fragmentów i zdolności techów pobierane już przy aktywnym przycisku.
- ⓘ przy każdym wierszu: nowe rodzaje `ability` (zdolność frakcji, `AbilityDetailsCard`) i `legendary`
  (`PlanetAbilityDetailsCard`) w `ComponentInfo` + `hintFor`; także przy zdolnościach technologii.
- Test: `componentActions.test.ts`.


## Karty akcji: przegląd + wiedza o talii agend (Insider Information) + zakryte talie

- Audyt 140 kart akcji (skrypt na stanie 6 graczy): każda ma efekt; formularze przejrzane pod kątem mapy/overlay/Auto.
- Wiedza o talii agend (RULES.md 53.5.a1): `agenda_peek` + nowe `agenda_peek_bottom` w `core/card_draw.py` —
  trwa do zmiany talii (nie znika po fazie agendy); dobranie agendy zdejmuje ją z wiedzy, Politics daje właścicielowi
  nową górę/spód i kasuje wiedzę innych, przetasowanie kasuje wszystkim. `/hand` → `agendaPeekBottom`.
- UI: `KnownCards` w doku ręki zamiast linii tekstu — chipy `KnownAgenda` („Top 1: …”, „Bottom: …”, karta po
  kliknięciu), tajne cele z Extreme Duress jako `ScoredSecret`, notki z M'aban jako `PromissoryNote`, gracz = ikona frakcji.
- Zakryte talie: ustawienie `browseDecks` (Settings → Admin / testing, domyślnie wyłączone) — bez niego klik w rewers
  nic nie pokazuje; stosy odrzuconych i purge nadal jawne.
- Brilliance: planeta klikiem na mapie (`planet`) albo gracz (`player`), dokładnie jedno.
- „Auto” w polach liczbowych kart (RULES.md 53.9): Bribery, Unstable Planet, Shields Holding, Leadership Rider,
  Manipulate Investments.
- Testy: `test_reactions_agenda.py` (wiedza), `test_strategy_diplomacy_politics_imperial.py`, `test_action_cards_economy.py`,
  `KnownCards.test.ts`.


## Menu główne „AAA” + lobby: sposób przygotowania partii (plan kont)

- Nowe menu `pages/MainMenu.tsx` (+css): lewa kolumna na ciemnym szkle (logo w dwóch liniach, nawigacja z podpisami,
  główna akcja w gradiencie TI4), „Continue” gdy jest bieżąca partia, panel „Recent games” (zapisy, wczytanie
  jednym kliknięciem), profil „Guest” w rogu (logowanie nieaktywne z powodem), stopka ze statusem serwera.
  Nazwy przycisków bez zmian (E2E). „Game history” = „Soon” (wymaga kont).
- Wspólna logika zapisów: `useLoadSave`, `describeSave`, `formatSavePhase` w `LobbyScreens.tsx` (okno Load game + menu).
- Lobby (`Step_Players`): sekcja „Setup method” — Standard aktywny; Full random / Milty Draft / Franken Draft szare
  („Soon”), bez logiki.
- Usunięte martwe style starego menu/kreatora z `StartScreen.module.css`. `.env` w głównym `.gitignore`.
- Plan kont, historii i draftów + instrukcja Supabase: `docs/PLAN_KONTA_LOBBY.md`.
- QA: tsc, eslint (zmienione), vitest `domains/network` + `domains/setup`, zrzuty Playwright (menu 1600/1920, lobby).


## Zakryte talie także w wyszukiwarce planszy

- Bez ustawienia `browseDecks` wyszukiwarka nie otwiera list talii (agendy, cele, relikty, eksploracja, karty akcji)
  i nie indeksuje kart z zakrytych talii — znajduje tylko karty z jawnych stosów (odrzucone, purge), więc nie zdradza,
  co leży w talii ani w czyjej ręce. `buildSearchIndex(gameData, { browseDecks })`, `CardbackModal` ignoruje prośbę wyszukiwarki.
- Test: `searchIndexDecks.test.ts`.


## Menu główne: logo w jednej linii, biblioteka „Components”, uporządkowane Ustawienia

- Logo „Custodian Engine” w jednej linii (rozmiar w `cqi` kolumny marki, bez łamania).
- Nowa pozycja menu „Components” → `domains/library/ComponentsLibrary.tsx`: frakcje (lista wg dodatków +
  `FactionSummary`, przełącznik wariantów Keleres), karty strategii (`StrategyCardDetailsCard`), technologie ogólne
  (`GeneralTechCatalog` z `playerData=[]`, bez podpowiedzi o właścicielach), jednostki bazowe (`UnitDetailsCard`)
  i wszystkie talie (`CardPoolBrowser`: akcje, agendy, cele I/II, sekrety, relikty, eksploracja, notki ogólne)
  z wyszukiwarką. Nowa pula `genericPromissoryPool()` (znacznik `<color>` → „[color]”) + test.
- Ustawienia: zakładki Game (zegar, okna reakcji) / Variants (moduły talii) / Display (mapa + karty graczy) / Sound /
  Testing (Fast mode + God-Mode). Krótsze, konkretniejsze opisy. Usunięte martwe pola store: `showControlLayer`,
  `animateEventPreviews` (+ `toggleShowControlLayer`). Odwołania do starych nazw (podpowiedzi, komentarze) poprawione.


## Lobby: kto gdzie siedzi, numery graczy; map string z gotowymi domami

- Map string: token tłumaczony aliasami z danych (`8` = `08`, `96` = `96a`, `nekro`) — `core/map_string.resolve_tile_id`.
  Wcześniej `8`/`96` cicho znikały (dziury w mapie). Nieznany kafelek = 422 z listą (`/game/new`, `/map/load`).
- Gotowa mapa z domami (np. Milty): `map_seats` wykrywa frakcję domu na każdym miejscu (też `51` Creuss / `118` Crimson);
  `GET /map/seats` dla kreatora. Gracz na domu dostaje jego frakcję domyślnie (kreator `applySeatFactions`, backend dla
  gracza bez `faction_id`); przesiadka przenosi frakcję; nieobsadzony dom wraca do pustego slotu. RULES 2a.
- Kolejność przy stole wg miejsc zgodnie z zegarem od gracza 1 (`home_slots.seating_by_seats`), nie wg numeru. RULES 24.
- Krok „Players & map”: plansza miejsc (`SeatBoard`, ikony domów z mapy), chip „Seat N” na karcie, strzałki ◀ ▶
  zmieniające numer gracza. W lobby sieciowym zamiana idzie przez serwer razem z właścicielem (`PATCH /lobby/draft
  {"swap": [i, j]}`, tylko host; `setupSync.swapPlayers`). Nieznane kafelki blokują „Choose factions”.
- Testy: `tests/test_map_string_seats.py`, `test_network_game.py::test_host_swaps_player_numbers_with_owners`,
  `useSetupStore.test.ts` (applySeatFactions, swapPlayers).

## Szybszy dev i testy frontu

- `vite.config.ts`: React Compiler (Babel) tylko w `vite build` (wymuszenie w dev: `REACT_COMPILER=1`). W Vitest
  transformacja ~10 s → ~1,4 s na próbce, cały zestaw 357 testów ~20 s. `server.warmup` kompiluje drzewo od `main.tsx`
  zaraz po starcie Vite, więc pierwsze wejście w przeglądarkę nie czeka.
- Gracze przez ZeroTier: dev-serwer Vite podaje ~900 osobnych modułów (każdy = round-trip przez sieć). Do gry
  sieciowej lepiej `npm run build` + `uv run python packaging/launcher.py` (jeden serwer, `src/api/bundle.py`, kilka plików).

## Miejsce na lore systemów

- `frontend/src/entities/data/systems.ts`: każdy nazwany system (poza hyperlane'ami i pustym kafelkiem) ma pole
  `"flavourText": ""` zaraz pod `"name"` — 435 miejsc do ręcznego uzupełnienia (anomalie, puste systemy, systemy z
  planetami). Typ `TileData.flavourText`.
- `SystemDossier` (`Flavour`): niepusty lore systemu wyświetla się nad opisami planet; pusty jest pomijany.

## Lore planet z AsyncTI4 (PR #6213)

- Upstream AsyncTI4 PR #6213 (scalony 2026-11-20) dodał/poprawił `flavourText` planet. Zsynchronizowane 92 pliki
  `assets/planets/*.json` z aktywnych źródeł (base, pok, codex*, thunders_edge) + te same pola we
  `frontend/src/entities/data/planets.ts`: +40 nowych opisów (m.in. New Terra i reszta Thunder's Edge), poprawki
  literówek, zamiana lore Darien/Archon Tau/Archon Ren, nazwy „Ba'kal” i „Vira-Pics III”, kropki w
  `legendaryAbilityText` (Primor, Hope's End, Mirage, Mr Te, Thunder's Edge, Custodia Vigilia), dedup aliasów.
- Własne teksty Keleres planet `*k` (commit 4145b436) zostawione — upstream dał im kopię lore oryginałów.
- Pozostała część PR (teksty kart akcji/agend/techów/liderów, lore frakcji, plik `asteroid.json`) NIE zsynchronizowana.
