# Zweryfikowane reguły Twilight Imperium 4 (źródło prawdy dla kodu)

Ten plik jest **jedynym źródłem prawdy** dla reguł TI4 implementowanych w kodzie.
Zasada projektu (spec 5.1): żadna reguła ani statystyka nie jest kodowana z pamięci.
Każda reguła poniżej ma odniesienie do oficjalnego źródła.

Status weryfikacji każdej reguły:
- ✅ **ZWERYFIKOWANE** — potwierdzone w oficjalnym Living Rules Reference (LRR) / wiki.
- ⚠️ **ZAŁOŻENIE** — zakodowane tymczasowo, wymaga potwierdzenia przez znającego grę.
- ⬜ **DO ZROBIENIA** — reguła jeszcze niezaimplementowana.

**Główne źródła** (w kolejności pierwszeństwa):
- 🥇 **tirules2.com — GŁÓWNE ŹRÓDŁO PRAWDY:** https://www.tirules2.com/
  Pełny Living Rules Reference 2.0 (PoK) + noty do Codexów (do IV, 06/2025) i wstępne
  noty do Thunder's Edge (10/2025), plus rulingi Dane Beltramiego (lead designer TI4)
  i konsensus społeczności. Każda reguła w tym pliku jest weryfikowana najpierw tutaj;
  tematy mają osobne podstrony (np. „Anomalies", „Movement", „Space Combat").
  Pozostałe źródła są pomocnicze/backup.
- 📁 **LOKALNY ZRZUT (offline, najszybszy):** [`docs/rules_tirules/`](rules_tirules/INDEX.md)
  — kompletny zrzut tirules2.com (149 tematów: 109 reguł, 30 frakcji, 10 komponentów)
  w Markdown + `tirules.json`. **Sprawdzaj reguły TUTAJ w pierwszej kolejności** (bez
  requestów online). Odświeżenie i atrybucja: [`docs/rules_tirules/SOURCE.md`](rules_tirules/SOURCE.md).
  Gdy lokalny zrzut nie wystarcza, zajrzyj na żywą stronę tirules2.com.
  > **To są ZASADY i DOPRECYZOWANIA reguł** (edge-case'y, interakcje, rulingi Dane) —
  > NIE opisy działania umiejętności frakcji/kart. Pełne opisy komponentów są w assetach
  > JSON AsyncTI4; pliki `F_*`/`C_*` zawierają tylko noty-doprecyzowania (patrz `SOURCE.md`).
- Living Rules Reference 2.0 (Prophecy of Kings), FFG, 09/2020 —
  [PDF](https://images-cdn.fantasyflightgames.com/filer_public/51/55/51552c7f-c05c-445b-84bf-4b073456d008/ti10_pok_living_rules_reference_20_web.pdf)
- TI Wiki (odzwierciedla LRR): https://twilight-imperium.fandom.com/wiki/Anomalies

> Uwaga: wszystkie reguły mogą być nadpisane przez karty i zdolności specjalne
> (frakcje, technologie, karty akcji). To obsługujemy przez `rules_hooks` (asymetria).

---

## Spis treści

Każda sekcja ma odnośnik `📎 tirules:` do odpowiedniego tematu w lokalnym zrzucie
[`rules_tirules/`](rules_tirules/INDEX.md) (pełny indeks tematów: [`INDEX.md`](rules_tirules/INDEX.md)).

| # | Sekcja | Status | Główny temat tirules |
|---|---|---|---|
| 1 | [Anomalie (Anomalies)](#1-anomalie-anomalies) | ✅ | [Anomalies](rules_tirules/R_anomalies.md) |
| 2 | [Sąsiedztwo i wormhole (Adjacency)](#2-sąsiedztwo-i-wormhole-adjacency---zweryfikowane-częściowo) | ✅ częściowo | [Adjacency](rules_tirules/R_adjacency.md) |
| 2a | [Map string i pozycje planszy (AsyncTI4)](#2a-map-string-i-pozycje-planszy-asyncti4---zweryfikowane) | ✅ | [Game Board](rules_tirules/R_game_board.md) |
| 2b | [Klasyfikacja jednostek: przestrzeń vs planeta](#2b-klasyfikacja-jednostek-przestrzeń-vs-planeta---zweryfikowane) | ✅ | [Units](rules_tirules/R_units.md) |
| 2c | [Format `startingFleet` i setup frakcji](#2c-format-startingfleet-i-setup-frakcji---zweryfikowane) | ✅ | [Ships](rules_tirules/R_ships.md) |
| 2d | [Sąsiedztwo graczy (Neighbors)](#2d-sąsiedztwo-graczy-neighbors---zweryfikowane-częściowo) | ✅ częściowo | [Neighbors](rules_tirules/R_neighbors.md) |
| 2e | [Promissory notes: ręka vs strefa gracza](#2e-promissory-notes-ręka-vs-strefa-gracza---zweryfikowane-model) | ✅ | [Promissory Notes](rules_tirules/R_promissory_notes.md) |
| 3 | [Ruch (Movement)](#3-ruch-movement---do-zrobienia-warstwa-logiki-ruchu-późniejsza-faza) | ⬜ | [Movement](rules_tirules/R_movement.md) |
| 3a | [Limity sztuk jednostek (supply caps)](#3a-limity-sztuk-jednostek-plastic--supply-caps---zweryfikowane) | ✅ | [Reinforcements](rules_tirules/R_reinforcements.md) |
| 4 | [Pozycje stat-area](#4-pozycje-stat-area-player-stats-heksy---zweryfikowane-port-algorytmu-asyncti4) | ✅ | [Game Board](rules_tirules/R_game_board.md) |
| 5 | [Startowe żetony dowodzenia](#5-startowe-żetony-dowodzenia-command-counters---zweryfikowane) | ✅ | [Command Tokens](rules_tirules/R_command_tokens.md) |
| 6 | [Fazy gry — mapowanie na frontend](#6-fazy-gry--mapowanie-na-format-frontendu---format--logika) | ✅/⬜ | [Game Round](rules_tirules/R_game_round.md) |
| 7 | [Ekonomia planet: optimal / flex](#7-ekonomia-planet-optimal--flex---zweryfikowane) | ✅ | [Planets](rules_tirules/R_planets.md) |
| 8 | [Liderzy frakcji](#8-liderzy-frakcji-agentcommanderhero---zweryfikowane-dane) | ✅ | [Leaders](rules_tirules/R_leaders.md) |
| 9 | [Kolejność tur fazy akcji i pas](#9-kolejność-tur-fazy-akcji-i-pas---zweryfikowane) | ✅ | [Initiative Order](rules_tirules/R_initiative_order.md) |
| 10 | [Posiadane jednostki i ulepszenia](#10-posiadane-jednostki-i-ulepszenia-unitsowned---zweryfikowane-dane) | ✅ | [Unit Upgrades](rules_tirules/R_unit_upgrades.md) |
| 11 | [Klucz tożsamości gracza w web-data](#11-klucz-tożsamości-gracza-w-web-data-desync-panelmapa---zweryfikowane-kod-frontendu) | ✅ | — (kontrakt frontendu) |
| 12 | [Kontrola planet — jedno źródło prawdy](#12-kontrola-planet--jedno-źródło-prawdy-opcja-a---decyzja-projektowa) | ✅ | [Control](rules_tirules/R_control.md) |
| 13 | [Faza strategii (wybór kart)](#13-faza-strategii-wybór-kart-strategii---zweryfikowane-dane--java-bot) | ✅ | [Strategy Phase](rules_tirules/R_strategy_phase.md) |
| 14 | [Źródła danych: codexy + thunders_edge](#14-źródła-danych-codexy--thunders_edge-dedup-erraty---zweryfikowane-dane) | ✅ | [Technology](rules_tirules/R_technology.md) |
| 15 | [Typ planety: `planetTypes` vs `planetType`](#15-typ-planety-pole-planettypes-lista-vs-planettype---zweryfikowane-dane) | ✅ | [Planets](rules_tirules/R_planets.md) |
| 16 | [Wybór technologii startowej frakcji](#16-wybór-technologii-startowej-frakcji---zweryfikowane-dane) | ✅ | [Technology](rules_tirules/R_technology.md) |
| 17 | [Systemy domowe poza planszą (Creuss, Rebellion)](#17-systemy-domowe-poza-planszą-ghost-of-creuss-crimson-rebellion---zweryfikowane-bot) | ✅ | [Wormholes](rules_tirules/R_wormholes.md) |
| 18 | [Panel gracza: zdolności, tech frakcyjny, przełomy](#18-panel-gracza-zdolności-technologie-frakcyjne-przełomy---zweryfikowane-dane--frontend) | ✅ | [Breakthroughs](rules_tirules/R_breakthroughs.md) |
| 19 | [Akcja taktyczna: aktywacja + maszyna kroków](#19-akcja-taktyczna-aktywacja-systemu--maszyna-kroków---zweryfikowane-asyncti4-bot) | ✅ | [Tactical Action](rules_tirules/R_tactical_action.md) |
| 20 | [Walka: pomoce liczbowe / statystyki](#20-walka-pomoce-liczbowe-asystent-nie-sędzia---zweryfikowane-dane-unitdef) | ✅ | [Space Combat](rules_tirules/R_space_combat.md) |
| 21 | [Przejęcie kontroli planety (inwazja)](#21-przejęcie-kontroli-planety-inwazja---zweryfikowane-asyncti4-bot) | ✅ | [Invasion](rules_tirules/R_invasion.md) |
| 22 | [Produkcja: pomoc liczbowa](#22-produkcja-pomoc-liczbowa-koszt--zasoby---zweryfikowane-dane-unitdef) | ✅ | [Producing Units](rules_tirules/R_producing_units.md) |
| 23 | [Kontrola planety przy stawianiu jednostek](#23-kontrola-planety-przy-stawianiu-jednostek-auto---zweryfikowane-asyncti4-bot) | ✅ | [Control](rules_tirules/R_control.md) |
| 24 | [Kolejność graczy: seating, speaker, inicjatywa](#24-kolejność-graczy-seating-order-speaker-wybór-kart-strategii---zweryfikowane-lrr--asyncti4-bot) | ✅ | [Speaker](rules_tirules/R_speaker.md) |
| 25 | [Drag-and-drop przenoszenia jednostek (UI)](#25-drag-and-drop-przenoszenia-jednostek-uigod-mode---decyzja-projektowa) | ✅ (UI) | [Transport](rules_tirules/R_transport.md) |
| 26 | [Umiejscowienie jednostek: statek↔przestrzeń](#26-umiejscowienie-jednostek-przy-przenoszeniu-statekprzestrzeń-naziemneplaneta---zweryfikowane) | ✅ | [Units](rules_tirules/R_units.md) |
| 27 | [Wyczerpywanie komponentów (exhaust/ready)](#27-wyczerpywanie-komponentów-planety-technologie-liderzy-exhaustready---zweryfikowane-lrr--dane) | ✅ | [Exhausted](rules_tirules/R_exhausted.md) |
| 28 | [Grywalne frakcje vs placeholdery](#28-grywalne-frakcje-vs-placeholdery-systemowe-neutrallazax---zweryfikowane-dane-asyncti4) | ✅ | [Neutral Units](rules_tirules/R_neutral_units.md) |
| 29 | [ZMIANA KIERUNKU: silnik-SĘDZIA + okna czasowe](#29-zmiana-kierunku-silnik-sędzia--okna-czasowe-zastępuje-asystent-nie-sędzia) | decyzja | [Strategic Action](rules_tirules/R_strategic_action.md) |
| 30 | [Akcja strategiczna: primary + okno secondary](#30-akcja-strategiczna-primary--okno-secondary---zweryfikowane-lrr-20) | ✅ | [Strategic Action](rules_tirules/R_strategic_action.md) |
| 31 | [Walidacja przepływu fazy akcji + aktywny gracz](#31-walidacja-przepływu-fazy-akcji--aktywny-gracz-twarda-egzekucja---zweryfikowane-lrr-20) | ✅ | [Action Phase](rules_tirules/R_action_phase.md) |
| 32 | [Ruch statków: egzekucja legalności](#32-ruch-statków-egzekucja-legalności-akcja-taktyczna---zweryfikowane-lrr-20) | ✅ | [Movement](rules_tirules/R_movement.md) |
| 33 | [Walidacja aktywacji i produkcji](#33-walidacja-aktywacji-i-produkcji-twarda-egzekucja---zweryfikowane-lrr-20) | ✅ | [Producing Units](rules_tirules/R_producing_units.md) |
| 34 | [Specyfikacja czasowa komponentów: wyzwalacz → typ okna](#34-specyfikacja-czasowa-komponentów-wyzwalacz--typ-okna---założenie-d10) | ⚠️ | [Action Cards](rules_tirules/R_action_cards.md) |
| 35 | [Spójność referencji: placeholder `<color>` jako szablon](#35-spójność-referencji-placeholder-color-promissory-notes-jako-szablon---założenie) | ⚠️ | [Promissory Notes](rules_tirules/R_promissory_notes.md) |
| 36 | [Limity rąk i zbiór poziomów trudności bota](#36-limity-rąk-i-zbiór-poziomów-trudności-bota----zweryfikowane-reguły-ti4--założenie-trudność) | ✅ / ⚠️ | [Action Cards](rules_tirules/R_action_cards.md) |
| 37 | [Wyniki audytu danych (baseline, luki, założenia)](#37-wyniki-audytu-danych-baseline-luki-referencyjne-założenia) | 📊 | [Technology](rules_tirules/R_technology.md) |
| 38 | [Space Cannon Offense: kolejność, zasięg, rzuty, straty](#38-space-cannon-offense-kolejność-zasięg-deep-space-cannon-rzuty-straty---zweryfikowane-lrr-20) | ✅ / ⚠️ | [Space Cannon](rules_tirules/R_space_cannon.md) |
| 39 | [Walka: rundy, AFB, rzuty, Sustain Damage, straty](#39-walka-kosmiczna-i-naziemna-rundy-afb-rzuty-sustain-damage-straty---zweryfikowane-lrr-20) | ✅ / ⚠️ | [Space Combat](rules_tirules/R_space_combat.md) |
| 40 | [Inwazja: Bombardment, Commit, Space Cannon Defense, walka naziemna, Establish Control](#40-inwazja-bombardment-commit-space-cannon-defense-walka-naziemna-establish-control---zweryfikowane-lrr-20) | ✅ / ⚠ | [Invasion](rules_tirules/R_invasion.md) |

---

## 1. Anomalie (Anomalies)

📎 tirules: [Anomalies](rules_tirules/R_anomalies.md) · [Asteroid Field](rules_tirules/R_asteroid_field.md) · [Nebula](rules_tirules/R_nebula.md) · [Supernova](rules_tirules/R_supernova.md) · [Gravity Rift](rules_tirules/R_gravity_rift.md) · [Movement](rules_tirules/R_movement.md)

Źródło: LRR 2.0, sekcja „Anomalies"; TI Wiki /wiki/Anomalies.
Treść sparafrazowana dla zgodności z licencją.

Kluczowe rozróżnienie architektoniczne:
- **Sąsiedztwo (adjacency)** — statyczna właściwość mapy, niezależna od gracza.
  Dwa systemy są sąsiednie geometrycznie lub przez wormhole. Potrzebne m.in. dla
  Space Cannon, zdolności „w sąsiednim systemie" itd.
- **Przejezdność (traversability)** — czy statek *może* wykonać ruch przez/do
  systemu. Zależy od anomalii, technologii gracza i tego, który system jest aktywny.
  To NIE jest właściwość grafu sąsiedztwa — to warstwa logiki ruchu.

### 1.1. Asteroid Field (Pole asteroid) — ✅ ZWERYFIKOWANE
- Statki **nie mogą poruszać się przez ani wchodzić** do pola asteroid...
- ...**chyba że** gracz posiada technologię **Antimass Deflectors** (wtedy ruch dozwolony).
- Wniosek dla kodu: blokada **zależna od gracza** (posiadana technologia) — NIE statyczna.
- Flaga w danych AsyncTI4: `isAsteroidField`.
- Źródło: TI Wiki /wiki/Anomalies; TI3-SA /wiki/System.

### 1.2. Nebula (Mgławica) — ✅ ZWERYFIKOWANE
- Statek może **wejść** do mgławicy tylko jeśli jest ona **systemem aktywnym**.
- Statek rozpoczynający krok „Movement" w mgławicy ma **wartość ruchu = 1**
  na czas tego kroku (może być zwiększona innymi efektami).
- Obrońca w mgławicy ma **+1 do walki** (combat).
- Wniosek dla kodu: wpływa na ruch (warunek wejścia + ruch=1 przy wyjściu) i na walkę
  (bonus obrony) — NIE blokuje statycznego sąsiedztwa.
- Flaga w danych: `isNebula`.
- Źródło: TI Wiki /wiki/Anomalies.

### 1.3. Supernova — ✅ ZWERYFIKOWANE
- Statki **nie mogą poruszać się przez ani wchodzić** do supernowej. Zawsze nieprzejezdna.
- Wniosek dla kodu: blokada ruchu **bezwarunkowa** (niezależna od gracza/technologii).
  Ale sąsiedztwo geometryczne nadal istnieje (dla efektów adjacency).
- Flaga w danych: `isSupernova`.
- Źródło: TI Wiki /wiki/Anomalies.

### 1.4. Gravity Rift (Szczelina grawitacyjna) — ✅ ZWERYFIKOWANE
- Statek, który **wychodzi z** lub **przechodzi przez** szczelinę: **+1 do wartości ruchu**.
- Przy opuszczaniu szczeliny: rzut kością; wynik **1-3 niszczy** statek.
- Wniosek dla kodu: modyfikator ruchu (+1) i ryzyko zniszczenia — NIE blokuje sąsiedztwa.
- Flaga w danych: `isGravityRift`.
- Źródło: TI Wiki /wiki/Anomalies.

---

## 2. Sąsiedztwo i wormhole (Adjacency) — ✅ ZWERYFIKOWANE (częściowo)

📎 tirules: [Adjacency](rules_tirules/R_adjacency.md) · [Wormholes](rules_tirules/R_wormholes.md) · [Neighbors](rules_tirules/R_neighbors.md) · [Hyperlanes](rules_tirules/R_hyperlanes.md)

- Systemy są sąsiednie, jeśli przylegają do siebie na mapie (6 krawędzi heksa).
- Systemy zawierające **wormhole tego samego typu** (Alpha, Beta, Gamma, Delta...)
  są traktowane jako **sąsiednie** wzajemnie.
- Hyperlanes (kafelki `hl_*`, pozycje `frac*`) tworzą nieliniowe połączenia —
  ⬜ DO ZROBIENIA (obecnie liczymy tylko geometrię + wormhole).
- Źródło: TI Wiki /wiki/Movement; `assets/positions/tileAdjacencies.properties`.

---

## 2a. Map string i pozycje planszy (AsyncTI4) — ✅ ZWERYFIKOWANE

📎 tirules: [Game Board](rules_tirules/R_game_board.md) · [System Tiles](rules_tirules/R_system_tiles.md) · [Mecatol Rex](rules_tirules/R_mecatol_rex.md)

Źródło: lokalny asset AsyncTI4 `assets/alias/position_alias.properties`
(autorytatywne mapowanie TTPG → pozycje Async). Zweryfikowane 2026-10 porównaniem
z realnymi danymi, nie z pamięci.

**Format map stringa (TTS/AsyncTI4):**
- Ciąg identyfikatorów kafelków oddzielonych spacjami, np.
  `72 66 77 26 27 34 50 69 76 31 35 37 78 62 75 67 38 65 0 28 79 0 48 64 0 44 29 0 25 47 0 39 49 0 41 40`.
- **Mecatol Rex (system `18`) jest DOMYŚLNY w centrum (`000`)** i NIE występuje
  w stringu (chyba że string zaczyna się od ID centrum — wariant z jawnym centrum).
- Kafelki przypisywane są **po kolei** do pozycji w ustalonej kolejności (patrz niżej),
  pierścień po pierścieniu, zaczynając od pierścienia 1.
- **`0` = puste miejsce** (brak kafelka na tej pozycji) — pomijane przy budowie mapy,
  ale ZAJMUJE pozycję w sekwencji (nie przesuwa kolejnych kafelków).
- Długość: 36 ID = pierścienie 1-3 (6 + 12 + 18). 3 pierścienie to standardowa mapa
  (do 6 graczy). Dłuższe stringi obejmują pierścień 4+.

**Kolejność pozycji (z `position_alias.properties`):**
- Centrum: `000`.
- Pierścień 1: `101 102 103 104 105 106` (6 pozycji).
- Pierścień 2: `201 .. 212` (12 pozycji).
- Pierścień 3: `301 .. 318` (18 pozycji).
- Pierścień N: `N01 .. N{6N}` (6N pozycji).
- Numeracja idzie **zgodnie z ruchem wskazówek zegara**, zaczynając od pozycji
  bezpośrednio NAD centrum (`101` = nad Mecatolem).

**Współrzędne (axial → kubiczne):**
- Plik podaje axial TTPG `(a, b)` (układ "doubled"): np. `101 = (0, +2)`.
- Przeliczenie na kubiczne: **`q = a`, `r = (b - a) / 2`, `s = -q - r`**.
  Zweryfikowane: `(b - a)` zawsze parzyste; odległość od centrum = numer pierścienia.
- UWAGA: ta orientacja (AsyncTI4) różni się od wcześniejszego geometrycznego
  generatora `position_to_hex` z Bloku 2. Źródłem prawdy pozycji jest TERAZ plik alias
  (nie samodzielna geometria), bo ma odwzorować wygląd i numerację AsyncTI4.
- Orientacja heksów przy renderze: **flat-top** (zgodnie z grafikami kafelków AsyncTI4).

**Źródło:** `assets/alias/position_alias.properties`; format map stringa — standard
TTS/AsyncTI4 (grupa standaryzująca na Discordzie TTS, por. ti4-map-lab).

**Pozycje domowe (home systems) i puste `0` w stringu — ✅ ZWERYFIKOWANE geometrycznie:**
- Przy 6 graczach systemy domowe stoją na **6 rogach pierścienia 3**: pozycje
  `301, 304, 307, 310, 313, 316` (każda ma jedną współrzędną kubiczną = 0, dwie = ±3).
- W map stringu te pozycje są zwykle `0` (puste), bo kafelek domowy zależy od wybranej
  frakcji i nie jest częścią losowanej mapy. Potwierdzone na stringu użytkownika:
  dokładnie te 6 pozycji było `0`.
- Wniosek dla kodu: `0` na rogu pierścienia (gdy pierścień ma komplet 6 rogów-domów)
  traktujemy jako **slot domowy gracza**, nie zwykłą pustkę — renderujemy kolorowy heks.

**Kolejność kolorów graczy na rogach — ⚠️ ZAŁOŻENIE (do potwierdzenia):**
- To NIE jest reguła TI4 (LRR nie narzuca kolorów na pozycje) — to konwencja wyświetlania.
- Przyjęty układ (flat-top, góra = `301`, zgodnie z ruchem wskazówek zegara):
  `301`=czerwony, `304`=zielony, `307`=biały, `310`=niebieski, `313`=fioletowy, `316`=żółty.
- Odwzorowuje przykładowy render użytkownika. Użytkownik potwierdza ostatecznie.

---

## 2b. Klasyfikacja jednostek: przestrzeń vs planeta — ✅ ZWERYFIKOWANE

📎 tirules: [Units](rules_tirules/R_units.md) · [Ships](rules_tirules/R_ships.md) · [Ground Forces](rules_tirules/R_ground_forces.md) · [Structures](rules_tirules/R_structures.md) · [Mechs](rules_tirules/R_mechs.md)

Źródło: TI Wiki/LRR — /wiki/Units, /wiki/Mechs, /wiki/War_Sun, /wiki/Infantry.
Treść sparafrazowana dla zgodności z licencją.

Jednostki istnieją w **dwóch rozłącznych miejscach** systemu:
- **Przestrzeń (space)** — statki stojące w przestrzeni systemu (biorą udział w space combat).
- **Planeta (ground)** — siły naziemne i struktury NA konkretnej planecie (ground combat / instalacje).

**Klasyfikacja (umiejscowienie):**

| baseType     | asyncId | Umiejscowienie | Kategoria     |
|--------------|---------|----------------|---------------|
| fighter      | ff      | przestrzeń     | statek        |
| destroyer    | dd      | przestrzeń     | statek        |
| cruiser      | ca      | przestrzeń     | statek        |
| carrier      | cv      | przestrzeń     | statek        |
| dreadnought  | dn      | przestrzeń     | statek        |
| flagship     | fs      | przestrzeń     | statek        |
| **warsun**   | ws      | **przestrzeń** | statek        |
| **infantry** | gf      | **planeta**    | siła naziemna |
| **mech**     | mf      | **planeta**    | siła naziemna |
| **pds**      | pd      | **planeta**    | struktura     |
| **spacedock**| sd      | **planeta**    | struktura     |

**⚠️ UWAGA — flagi w danych AsyncTI4 są NIEWIARYGODNE dla tej klasyfikacji:**
- W danych `mech` ma `isShip=True`, a `warsun` ma `isShip=False` — oba błędne wobec reguł.
  LRR: War Sun to statek (space combat); Mech to siła naziemna (ground combat, trzyma planety).
- Dlatego umiejscowienie bierzemy z **jawnej tabeli reguł** (powyżej), NIE z pól `isShip`/
  `isStructure`. Kod ma stałą mapę `asyncId → placement` opartą o tę tabelę.

Odwzorowanie w `GameState`:
- `SystemState.space_units[player_id][base_type] = liczba` — statki w przestrzeni.
- `SystemState.planet_units[planet_id][player_id][base_type] = liczba` — naziemne/struktury.

---

## 2c. Format `startingFleet` i setup frakcji — ✅ ZWERYFIKOWANE

📎 tirules: [Ships](rules_tirules/R_ships.md) · [Ground Forces](rules_tirules/R_ground_forces.md) · [Reinforcements](rules_tirules/R_reinforcements.md) · [Units](rules_tirules/R_units.md)

Źródło: dane frakcji AsyncTI4 (`assets/data/factions/*.json`), zweryfikowane na
base+pok (2026-10). Format sparafrazowany; wzorzec potwierdzony empirycznie.

**Pola frakcji istotne dla setupu:**
- `homeSystem` — ID kafelka domowego (np. Arborec → `05`, Muaat → `04`).
- `homePlanets` — lista planet systemu domowego (np. Hacan → `arretze, hercant, kamdorn`).
- `startingFleet` — flota startowa (format niżej).
- `startingTech`, `factionTech`, `commodities`, `preferredColours`.

**Format `startingFleet`:** tokeny oddzielone przecinkami, każdy:
`[liczba] <kod> [sufiks_planety]`
- Liczba domyślnie 1 (gdy pominięta).
- Separatory niespójne (przecinki, zmienne spacje) — parser tnie po przecinku i białych znakach.
- **Kody jednostek `startingFleet`** (INNY zestaw niż `asyncId`!):
  `cr`→cruiser, `cv`→carrier, `dd`→destroyer, `dn`→dreadnought, `ff`→fighter,
  `fs`→flagship, `ws`→warsun, `inf`→infantry, `mech`→mech, `pds`→pds, `sd`→spacedock.
  - ⚠️ Niespójność danych: Keleres (3 warianty) używa `ca` dla cruisera zamiast `cr`.
    Akceptujemy `ca` jako alias cruisera w mapie kodów.
- **Sufiks planety** = najkrótszy **jednoznaczny prefiks** nazwy planety domowej:
  - Występuje TYLKO przy jednostkach naziemnych/strukturach (inf, mech, pds, sd).
  - Statki (cr, cv, dd, dn, ff, fs, ws) NIE mają sufiksu → trafiają do przestrzeni.
  - Przy kolizji 1-literowej używany jest dłuższy prefiks: Xxcha `archonren`/`archontau`
    → `ar`/`at` (bo samo `a` jest niejednoznaczne).
  - Przykłady: Arborec `inf n` → nestphar; Hacan `sd a` → arretze, `inf k` → kamdorn.

**Setup gracza (wynik):**
1. Kafelek domowy frakcji (`homeSystem`) trafia na slot domowy wybranego koloru.
2. `startingFleet` rozkładany: statki → `space_units`; naziemne/struktury → `planet_units`
   na planecie wskazanej sufiksem.
3. Gracz kontroluje planety domowe (`homePlanets` → `planet_owners`).
4. `startingTech` ustawiane na stanie gracza. **`commodities` NIE są ilością startową:**
   pole frakcji `commodities` to **commodity value = MAKSIMUM** (limit, do którego
   gracz „replenishuje"). Zapisujemy je jako `commodity_value`, a **bieżące
   `commodities` startują z 0** — 📎 tirules [Commodities](rules_tirules/R_commodities.md):
   „A player starts the game with zero commodities". Viewer pokazuje
   `commodities / commoditiesTotal` = bieżące / `commodity_value`.

**Grafiki jednostek:** `assets/units/<kolor>_<asyncId>.png`. UWAGA: `asyncId` ≠ kod
`startingFleet` (np. cruiser: `asyncId=ca`, kod fleet=`cr`). Mapowanie przez `baseType`.

---

## 2d. Sąsiedztwo graczy (Neighbors) — ✅ ZWERYFIKOWANE (częściowo)

📎 tirules: [Neighbors](rules_tirules/R_neighbors.md) · [Adjacency](rules_tirules/R_adjacency.md) · [Transactions](rules_tirules/R_transactions.md)

Źródło: tirules2.com → `docs/rules_tirules/R_neighbors.md`. Treść sparafrazowana.

Pojęcie GRACZA (kto z kim graniczy), odrębne od statycznego sąsiedztwa mapy
(sekcja 2): sąsiedztwo systemów jest wejściem, sąsiedztwo graczy — wynikiem.

- Dwóch graczy jest **sąsiadami (neighbors)**, jeśli OBAJ mają jednostkę lub
  kontrolują planetę w **tym samym systemie**.
- Są sąsiadami również, gdy obaj mają jednostkę lub kontrolują planetę w systemach
  **sąsiadujących** ze sobą (sąsiedztwo przez wormhole wliczone — bo to część
  adjacency z sekcji 2).
- „Obecność" w systemie = jednostka w przestrzeni, jednostka na planecie LUB
  kontrola planety (`planet_owners`). Puste stosy (0 sztuk) nie liczą się.
- Relacja jest **symetryczna**; gracz nie jest własnym sąsiadem.
- Znaczenie: tylko sąsiedzi mogą zawierać transakcje (R_transactions). Pole
  `neighbors` w web-data zasila panel gracza (ikony sąsiadów), jako lista KOLORÓW.

**Zakres w kodzie:** `src/core/neighbors.py` (`neighbors_of`, `neighbors_by_player`)
— czyste funkcje nad `GameState` + `HexGrid`. Serializacja w `api/web_data.py`
mapuje `player_id` → kolor.

**⚠️ Ograniczenia (do rozbudowy z pełną warstwą adjacency):**
- Sąsiedztwo systemów bierzemy z `HexGrid` (geometria + wormhole); **hyperlanes**
  nie są jeszcze uwzględnione (jak w sekcji 2).
- Efekty frakcyjne/agendy zmieniające adjacency (np. Creuss *Quantum Entanglement*,
  Mentak przez wormhole) nie są modelowane — wejdą przez hooki, gdy powstaną.

---

## 2e. Promissory notes: ręka vs strefa gracza — ✅ ZWERYFIKOWANE (model)

📎 tirules: [Promissory Notes](rules_tirules/R_promissory_notes.md) · [Transactions](rules_tirules/R_transactions.md)

Źródło: tirules2.com → `docs/rules_tirules/R_promissory_notes.md`. Sparafrazowane.

Promissory notes występują w TRZECH rozłącznych reprezentacjach — rozróżnienie
istotne dla widoczności (R2/R6) i dla handlu:

- **RĘKA (hand)** — notki trzymane do ewentualnego przehandlowania. **TAJNA**
  (prywatna): inni widzą tylko LICZEBNOŚĆ (jawna — „the number of promissory notes
  in a player's hand is public information"), nigdy identyfikatory. Model:
  `PlayerState.private.promissory_notes`; licznik w web-data to `pnCount`.
- **STREFA GRACZA (play area)** — notki ZAGRANE i leżące odkryte (np. *Support for
  the Throne*, *Alliance*, które muszą być zagrane natychmiast). **JAWNE**: widoczne
  dla wszystkich. „Promissory notes in the play area cannot be traded." Model:
  `PlayerState.promissory_notes_in_play`; w web-data pole `promissoryNotesInPlayArea`,
  które panel gracza renderuje w racku holdings (obok relikwii i tajnych celów).
- **WŁASNA FRAKCYJNA (loadout)** — unikalna notka, z którą KAŻDY gracz zaczyna grę
  (np. Sol `ms` = Military Support, Hacan `convoys` = Trade Convoys; Empyrean ma dwie:
  `dark_pact`, `blood_pact`). To stały, JAWNY fakt (frakcja X ma notkę Y) czytany z
  danych frakcji (`FactionDef.promissoryNotes`), NIE stan rozgrywki. W web-data pole
  `customPromissoryNotes` (helper `_faction_promissory_notes`); panel renderuje je w
  sekcji loadoutu (obok zdolności i techów frakcyjnych), gated `showPlayerAreaFactionAbilities`.

**⚠️ Zakres:** pole strefy istnieje i jest JAWNE (klasyfikacja w `player_fields.py`),
emitowane do viewera i edytowalne przez God-Mode (`/player/{id}/edit`). Automatyczne
przenoszenie notki z ręki do strefy przy jej zagraniu wejdzie dopiero z logiką
transakcji/zagrywania notek (okna czasowe, E8+). Do tego czasu strefę zasila operator.

---

## 3. Ruch (Movement) — ⬜ DO ZROBIENIA (warstwa logiki ruchu, późniejsza faza)

📎 tirules: [Movement](rules_tirules/R_movement.md) · [Move (Attribute)](rules_tirules/R_move.md) · [Transport](rules_tirules/R_transport.md) · [Active System](rules_tirules/R_active_system.md) · [Anomalies](rules_tirules/R_anomalies.md)

Zweryfikowane zasady do zaimplementowania, gdy powstanie logika ruchu
(obecnie HexGrid dostarcza tylko sąsiedztwo i odległości):
- Statek musi zakończyć ruch w systemie aktywnym.
- Nie może przejść przez system z żetonami dowodzenia innego gracza / jego statkami.
- Nie może ruszyć, jeśli zaczynał w systemie z własnym żetonem dowodzenia.
- Liczba systemów na trasie ≤ wartość ruchu statku.
- Modyfikatory anomalii z sekcji 1 nakładają się na powyższe.
- Źródło: TI Wiki /wiki/Movement (odzwierciedla LRR Movement).

---

## Dziennik zmian w kodzie wynikających z weryfikacji

- **2026-10**: Weryfikacja anomalii ujawniła, że HexGrid mieszał sąsiedztwo
  z przejezdnością. Supernova NIE powinna usuwać krawędzi sąsiedztwa (sąsiedztwo
  istnieje; blokowany jest tylko ruch). Asteroid field blokuje ruch warunkowo
  (zależnie od technologii gracza), więc też nie może usuwać statycznych krawędzi.
  → HexGrid przeprojektowany: graf = czyste sąsiedztwo (geometria + wormhole);
  przejezdność/blokady przeniesione do metadanych anomalii per-system do użycia
  przez przyszłą warstwę ruchu.

---

## 3a. Limity sztuk jednostek (plastic / supply caps) — ✅ ZWERYFIKOWANE

📎 tirules: [Reinforcements](rules_tirules/R_reinforcements.md) · [Units](rules_tirules/R_units.md) · [Fighter Tokens](rules_tirules/R_fighter_tokens.md) · [Infantry Tokens](rules_tirules/R_infantry_tokens.md)

Źródło (NIE z pamięci): AsyncTI4 bot,
`TI4_map_generator_bot/src/main/resources/positions/reinforcements.properties`.
`Player.getUnitCap(unit)` zwraca liczbę pozycji (par współrzędnych) danej jednostki
w layoucie rezerwy = liczba sztuk, które gracz ma w puli. Monument = 1 (specjalny
przypadek w `Player.getUnitCap`). Potwierdzone zgodnością z danymi żywej gry AsyncTI4.

Limity per `asyncId` (zakodowane w `src/core/unit_catalog.py` → `UNIT_CAP_BY_ASYNC_ID`):

| asyncId | jednostka | limit |
|---|---|---|
| gf | infantry | 12 |
| ff | fighter | 10 |
| mf | mech | 4 |
| dd | destroyer | 8 |
| ca | cruiser | 8 |
| cv | carrier | 4 |
| dn | dreadnought | 5 |
| fs | flagship | 1 |
| ws | warsun | 2 |
| pd | pds | 6 |
| sd | spacedock | 3 |
| monument | monument | 1 |

Zastosowanie: `playerData.unitCounts[asyncId] = {unitCap, deployedCount}` w dokumencie
`web-data`. Panel rezerwy frontendu pokazuje `unitCap - deployedCount` (ile zostało
w puli). `deployedCount` = liczba sztuk danego typu gracza na planszy.

---

## 4. Pozycje stat-area (player-stats heksy) — ✅ ZWERYFIKOWANE (port algorytmu AsyncTI4)

📎 tirules: [Game Board](rules_tirules/R_game_board.md) · [Command Sheet](rules_tirules/R_command_sheet.md) · [Victory Points](rules_tirules/R_victory_points.md)

Kolorowe heksy „player stats" przy planszy to **zwarta trójka pustych kafelków**
w pobliżu slotu domowego gracza. Algorytm (PORT, nie z pamięci) ze źródła AsyncTI4:
`TI4_map_generator_bot/.../PlayerStatsHelper.findThreeNearbyStatTiles`:

1. Kandydaci = PUSTE pozycje (brak systemu), pierścień ≤ `ringCount+1`, nie zajęte
   przez innego gracza (współdzielony `taken`).
2. Dobierz najbliższe (odległość do slotu domowego + kara za pierścień) aż powstanie
   zwarta trójka (jeden kafelek sąsiaduje z dwoma pozostałymi).
3. Zwróć `[pivot, sąsiad, sąsiad]` — **pivot (środkowy) PIERWSZY**.

Kolejność ma znaczenie: frontend kładzie `firstHex` = tożsamość frakcji (grafika,
nazwa, karty strategii, sekrety, **VP**), `secondHex` = żetony dowodzenia (CC),
`thirdHex` = trade goods / commodities / action cards + status ACTIVE/PASSED
(źródło ról: `frontend/.../PlayerStatsArea.tsx`). Dlatego pivot (środkowy heks) musi
być pierwszy — tam ma być znak frakcji.

Implementacja: `src/api/web_data.py` → `_three_nearby_stat_tiles` / `_build_stat_tile_positions`.
Odległość w metryce kubicznej (proxy pikseli z oryginału). Zweryfikowane 1:1 z żywą grą
AsyncTI4 oraz dla 6 graczy (18 unikalnych pozycji, bez nakładania).

---

## 5. Startowe żetony dowodzenia (command counters) — ✅ ZWERYFIKOWANE

📎 tirules: [Command Tokens](rules_tirules/R_command_tokens.md) · [Command Sheet](rules_tirules/R_command_sheet.md) · [Fleet Pool](rules_tirules/R_fleet_pool.md) · [Leadership (Strategy Card)](rules_tirules/R_leadership.md)

Źródło (nie z pamięci): AsyncTI4 bot, `Player.java` wartości domyślne:
`private int tacticalCC = 3; private int fleetCC = 3; private int strategicCC = 2;`.
Czyli start gry: **3 taktyczne, 3 floty, 2 strategiczne** żetony na arkuszu.
Zakodowane w `src/core/game_state.py` → `PlayerState` (`tactical_cc`, `fleet_cc`,
`strategic_cc`). Zasilają panele gracza (CCPool) i heks stat-area (drugi heks).

⚠️ ZAŁOŻENIE: `cc_reinf = 8` (rezerwa w szkole dowodzenia). TI4 ma 16 żetonów łącznie,
8 na starcie na arkuszu → 8 w rezerwie. Do potwierdzenia dokładnej liczby/źródła.

## 6. Fazy gry — mapowanie na format frontendu — ✅ (format), ⬜ (logika)

📎 tirules: [Game Round](rules_tirules/R_game_round.md) · [Strategy Phase](rules_tirules/R_strategy_phase.md) · [Action Phase](rules_tirules/R_action_phase.md) · [Status Phase](rules_tirules/R_status_phase.md) · [Agenda Phase](rules_tirules/R_agenda_phase.md)

Frontend (`GamePhase` w `entities/data/types.ts`) używa stringów małymi literami z
podfazami: `strategy`, `action`, `status.scoring`, `status.homework`, `agenda.*`,
`setup.*`, `finished`. Nasza enum `Phase` (STRATEGY/ACTION/STATUS/AGENDA) mapowana w
`web_data.py` → `_to_web_phase` (STATUS→`status.scoring`, AGENDA→`agenda.voting`).
`gameState.activePlayer` to KOLOR gracza (nie id) — frontend dopasowuje po kolorze.

Pełna LOGIKA faz (przejścia, akcje, timing) = Warstwa B (roadmapa M2–M6), port z
`TI4_map_generator_bot/src/main/java/ti4/service/{turn,strategycard,tactical,combat,agenda}`.

---

## 7. Ekonomia planet: optimal / flex — ✅ ZWERYFIKOWANE

📎 tirules: [Planets](rules_tirules/R_planets.md) · [Resources](rules_tirules/R_resources.md) · [Influence](rules_tirules/R_influence.md)

Źródło (nie z pamięci): AsyncTI4 bot, `Planet.getOptimalResources/getOptimalInfluence/
getFlexResourcesOrInfluence`. Reguła per kontrolowana planeta:
- `optimalResources` = `resources`, gdy `resources > influence`, inaczej 0;
- `optimalInfluence` = `influence`, gdy `influence > resources`, inaczej 0;
- `flex` = wartość (res==inf), gdy `resources == influence`, inaczej 0.
Sumy po planetach gracza zasilają `playerData.optimalResources/optimalInfluence/flexValue`
(oraz `tot*`). `resources`/`influence`/`totResources`/`totInfluence` = sumy surowe.
Implementacja: `src/api/web_data.py` → `_planet_economy` / `_Economy`.

## 8. Liderzy frakcji (agent/commander/hero) — ✅ ZWERYFIKOWANE (dane)

📎 tirules: [Leaders](rules_tirules/R_leaders.md) · [Leader Sheet](rules_tirules/R_leader_sheet.md)

Źródło: pole `leaders` w danych frakcji AsyncTI4 (np. Sol: `solagent, solcommander,
solhero`). Typ wyprowadzany z sufiksu id. Start: agent gotowy (odblokowany),
commander/hero zablokowani (odblokowują się przez warunki — logika w późniejszej fazie).
Model: `FactionDef.leaders`; emisja: `web_data._player_leaders` → `playerData.leaders`
(`{id,type,tgCount,exhausted,locked,active}`) + `leaderIDs`.

---

## 9. Kolejność tur fazy akcji i pas — ✅ ZWERYFIKOWANE

📎 tirules: [Initiative Order](rules_tirules/R_initiative_order.md) · [Action Phase](rules_tirules/R_action_phase.md) · [Active Player](rules_tirules/R_active_player.md) · [Strategy Card](rules_tirules/R_strategy_card.md)

Źródło (nie z pamięci): AsyncTI4 bot, `EndTurnService.findNextUnpassedPlayer` +
`Game.getActionPhaseTurnOrder`. Reguły:
- **Kolejność inicjatywy:** gracze ustawieni wg numeru karty strategii (inicjatywa),
  rosnąco (najniższy numer pierwszy). Bez kart → kolejność stabilna (po id gracza).
- **Następny gracz:** po zakończeniu tury przechodzi do kolejnego gracza w kolejności,
  który NIE spasował i nie jest wyeliminowany (rotacja listy za bieżącego).
- **Pas:** gracz pasuje → jest pomijany do końca fazy akcji. Gdy wszyscy spasowali →
  faza akcji się kończy (przejście do fazy statusu).
- **Nowa runda:** reset pasów; faza wraca do strategii, runda +1.

Implementacja: `src/core/turn_flow.py` (czyste funkcje) + endpointy
`/turn/end`, `/turn/pass`, `/phase/next`, `/round/next` w `app.py`.

---

## 10. Posiadane jednostki i ulepszenia (unitsOwned) — ✅ ZWERYFIKOWANE (dane)

📎 tirules: [Unit Upgrades](rules_tirules/R_unit_upgrades.md) · [Units](rules_tirules/R_units.md) · [Technology](rules_tirules/R_technology.md) · [Units (komponenty)](rules_tirules/C_units.md)

Źródło (nie z pamięci): dane jednostek AsyncTI4 (`assets/.../units/*.json`) + kod
frontendu `frontend/src/entities/lookup/units.ts` (`lookupUnit`, `preferUpgradedUnit`).
Zweryfikowane 2026-10 na załadowanym rejestrze (base+pok+codex).

**Jak frontend rozwiązuje jednostkę do renderu i statystyk:**
- `playerData.unitsOwned` to lista ID jednostek posiadanych przez gracza.
- `lookupUnit(asyncId, faction, playerData)` filtruje jednostki o danym `asyncId`
  do tych z `unitsOwned` i przez `preferUpgradedUnit` wybiera wariant z
  `upgradesFromUnitId` (ulepszony), gdy jest obecny. Statystyki (combat, move,
  capacity) i panel ulepszeń czytają z tak wybranej jednostki.

**Powiązanie ulepszenie ↔ technologia (z danych, zweryfikowane):**
- Każda ulepszona jednostka generyczna ma `upgradesFromUnitId` = bazowa oraz
  `requiredTechId` = alias technologii ulepszenia. Potwierdzone mapowanie:
  `carrier2→cv2`, `cruiser2→cr2`, `destroyer2→dd2`, `dreadnought2→dn2`,
  `fighter2→ff2`, `infantry2→inf2`, `pds2→pds2`, `spacedock2→sd2`.
- `warsun` (generyczny) ma `requiredTechId="ws"` — posiadany dopiero po zbadaniu
  technologii War Sun. Warianty frakcyjne wrodzone (np. `muaat_warsun`) nie mają
  `requiredTechId` i są posiadane od startu.

**Reguła emisji `unitsOwned` (implementacja `web_data._units_owned_for_faction`):**
Dla każdego `asyncId` wybieramy DOKŁADNIE JEDNĄ jednostkę (posiadanie dwóch o tym
samym asyncId psuje `lookupUnit`). Priorytet:
1. wariant frakcyjny gracza, ulepszony (gdy ma wymaganą technologię),
2. wariant frakcyjny gracza, bazowy,
3. wariant generyczny, ulepszony (gdy ma wymaganą technologię),
4. wariant generyczny, bazowy.
Jednostka za technologią (z `requiredTechId`), której gracz NIE ma, jest pomijana.
Przynależność jednostki do frakcji: **lista `FactionDef.units` jest autorytatywna** (plus
pole `faction` jednostki jako fallback). Keleres dzieli `keleres_flagship`/`keleres_mech`
między 3 warianty, a pole `faction` wskazuje tylko `keleresm` — bez listy `units` pozostałe
dwa warianty gubiły flagship/mech. Ulepszenie dziedziczy przynależność po bazie
(`upgradesFromUnitId` w liście `units`).

**Dlaczego to ważne (Bug 11):** wcześniej serializer pomijał WSZYSTKIE jednostki z
`upgradesFromUnitId`, więc po zbadaniu np. Carrier II panel i mapa dalej pokazywały
statystyki bazowego Carriera. Teraz zbadanie technologii ulepszenia podmienia wpis
w `unitsOwned` na wariant ulepszony → `preferUpgradedUnit` pokazuje właściwe statystyki.

---

## 11. Klucz tożsamości gracza w web-data (desync panel↔mapa) — ✅ ZWERYFIKOWANE (kod frontendu)

📎 tirules: — (kontrakt frontendu, nie reguła TI4; pojęciowo [Units](rules_tirules/R_units.md))

Źródło: `frontend/src/entities/lookup/units.ts` (`lookupUnit` dopasowuje jednostki po
`playerData[].faction`) + `tileUnitData`/`statTilePositions` kluczowane tym samym stringiem.

**Reguła:** klucz grupujący jednostki/heksy/kontrolę w CAŁYM dokumencie web-data musi
być ten sam co `playerData[].faction` i musi JEDNOZNACZNIE wskazywać gracza. Gdy frakcja
jest unikalna w grze — używamy jej; przy kolizji frakcji lub braku frakcji — używamy
stabilnego `player_id`. Implementacja: `web_data._entity_key_map` (jedna mapa dla
`_entities_from_counts`, `_planet_controller`, `_build_stat_tile_positions`,
`_build_player_data`).

**Dlaczego (Bug 1/2):** wcześniej klucz = `faction or player_id` liczony lokalnie w
wielu miejscach. Dwaj gracze dzielący frakcję (lub `None`) dostawali ten sam klucz →
ich jednostki scalały się w jeden wpis `tileUnitData` i znikały z mapy, mimo że
`playerData` pokazywał obu. Edycja (`_resolve_player_id`) z warunkiem `faction==key OR
pid==key` trafiała w złego gracza. Teraz `_resolve_player_id` preferuje dokładne
`player_id`, a frakcję akceptuje tylko gdy jednoznaczna.

---

## 12. Kontrola planet — jedno źródło prawdy (opcja A) — ✅ DECYZJA PROJEKTOWA

📎 tirules: [Control](rules_tirules/R_control.md) · [Planets](rules_tirules/R_planets.md) · [Invasion](rules_tirules/R_invasion.md) · [Coexistence](rules_tirules/R_coexistence.md)

**Reguła:** `SystemState.planet_owners` (kontrola planety w jej systemie) jest JEDYNYM
źródłem prawdy o tym, kto kontroluje planetę. Lista planet gracza w web-data
(`playerData.planets`) oraz ekonomia są WYLICZANE z `planet_owners`
(`web_data._controlled_planets_from_systems`). Edycja God-Mode listy planet gracza
(`/player/{id}/edit` z `controlled_planets`) jest synchronizowana do `planet_owners`
systemów (`app._sync_controlled_planets`). Edycja własności w systemie
(`/system/{pos}/planet` z `owner_id`) jest od razu widoczna w panelu (bo panel liczy
z `planet_owners`).

**Dlaczego (Bug 3):** wcześniej istniały dwa niezależne źródła — `player.controlled_planets`
(panel) i `SystemState.planet_owners` (mapa) — i edycja jednego nie aktualizowała
drugiego. Panel pokazywał planetę, mapa nie miała właściciela (i odwrotnie). Opcja A
odzwierciedla model gry: planeta fizycznie leży w systemie i to system „wie", kto ją
kontroluje; jest też naturalną podstawą pod przyszłą logikę podbojów/inwazji.

---

## 13. Faza strategii (wybór kart strategii) — ✅ ZWERYFIKOWANE (dane + Java bot)

📎 tirules: [Strategy Phase](rules_tirules/R_strategy_phase.md) · [Strategy Card](rules_tirules/R_strategy_card.md) · [Strategic Action](rules_tirules/R_strategic_action.md) · [Trade Goods](rules_tirules/R_trade_goods.md) · [Initiative Order](rules_tirules/R_initiative_order.md)

Źródło (nie z pamięci): dane kart `assets/data/strategy_cards/pok.json` +
`assets/data/strategy_card_sets/strategyCardSets.json`; logika z AsyncTI4 bot:
`StrategyCardManager.incrementTradeGoods`, `PickStrategyCardButtonHandler` (grant TG przy
wyborze), `PlayStrategyCardService`. Zweryfikowane 2026-10 na kodzie bota.

**Zestaw kart (domyślny PoK, 8 kart):** każda ma `initiative` (1–8) i `name`:
1 Leadership, 2 Diplomacy, 3 Politics, 4 Construction, 5 Trade, 6 Warfare,
7 Technology, 8 Imperial. Inicjatywa = numer karty. Dane czytane z rejestru po
`enabled_sources.json` (zestaw `pok`). Zero hardkodowania nazw/numerów.

**Reguła wyboru (pick):**
- W fazie strategii wybór idzie **od mówcy (speaker) zgodnie z ruchem zegara**
  (speaker order — RULES.md 24). Każdy gracz wybiera po kolei jedną kartę z puli.
- **Pick_Count (liczba kart na gracza) — zależna od liczby graczy:**
  - **2 graczy → 2 karty/gracz** — ⚠️ **ZAŁOŻENIE** (oficjalne TI4 nie definiuje trybu
    2-osobowego). Przyjmujemy wariant spójny z progiem 3–4 graczy (2 karty/gracz, z
    DRUGĄ rundą wyboru), żeby silnik solo vs 1 bot / hot-seat 1v1 działał w fazie
    strategii. Do potwierdzenia przez użytkownika; zmiana w jednym miejscu
    (`strategy_phase.pick_count`), jeśli preferowany jest inny wariant (np. 3 karty/gracz).
  - **3–4 graczy → 2 karty/gracz** (gra przewiduje DRUGĄ rundę wyboru, patrz niżej),
  - **5–8 graczy → 1 karta/gracz**,
  - **liczba graczy < 2 lub > 8 → NIEOBSŁUGIWANA (błąd).** Silnik odrzuca ustalenie
    `Pick_Count` i nie zmienia stanu fazy.

  Źródło: tirules [Strategy Phase](rules_tirules/R_strategy_phase.md) — Step 1: „When
  playing with three or four players, each player will choose a second strategy card.";
  LRR „Strategy Phase" (liczba kart zależna od liczby graczy; 3–4 graczy → dwie rundy
  wyboru). Zakres 3–8 graczy = oficjalnie obsługiwane liczby graczy TI4/PoK.
- **DRUGA runda wyboru (tylko 3–4 graczy):** po tym, jak ostatni gracz otrzyma swoją
  PIERWSZĄ kartę, wybór **wraca do mówcy** i przechodzi PONOWNIE w speaker order, aż
  każdy gracz będzie miał `Pick_Count` (= 2) kart. Mechanicznie: „następny wybierający"
  to pierwszy w speaker order (licząc od mówcy), który ma mniej kart niż `Pick_Count` —
  dlatego druga runda naturalnie zaczyna się od mówcy, bez osobnego licznika rund.
  Źródło: tirules [Strategy Phase](rules_tirules/R_strategy_phase.md) — Step 1, ostatni
  punkt: „After the last player has received their first strategy card, each player
  chooses a second strategy card, starting with the speaker and proceeding clockwise.";
  LRR „Strategy Phase".
- **Walidacja przejścia do fazy akcji:** fazy strategii **nie można zakończyć**, dopóki
  KAŻDY gracz nie ma dokładnie `Pick_Count` kart. Dopóki istnieje gracz poniżej
  `Pick_Count`, silnik wskazuje kolejnego wybierającego zamiast pozwolić na przejście;
  próba przejścia przy niekompletnym wyborze jest odrzucana (błąd), a faza pozostaje
  bez zmian. Kolejność tur fazy akcji ustala inicjatywa (najniższy numer wybranej karty —
  RULES.md 9). Źródło: tirules [Strategy Phase](rules_tirules/R_strategy_phase.md)
  („Then, players proceed to the action phase." — po zakończeniu Step 1/Step 2, tj. po
  skompletowaniu wyboru) + [Initiative Order](rules_tirules/R_initiative_order.md); LRR
  „Strategy Phase".
- **Spójność kolejności przy przejściu STRATEGY→ACTION (kontrola silnika):** przejście
  wymaga, by niepusta `seating_order` pokrywała się ze zbiorem graczy
  (`set(seating_order) == set(players)`); rozjazd (realny edge-case God-Mode: gracz
  dodany bez aktualizacji listy miejsc) jest odrzucany czytelnym błędem silnika
  (`ensure_strategy_complete`) ZANIM dojdzie do ustalania inicjatywy — to kontrola
  silnika-sędziego, nie reguła TI4. Puste `seating_order` jest OK (kolejność wtedy po id
  graczy).
- **Trade goods na kartach:** na każdej NIEWYBRANEJ karcie leży pula trade goods (start 0).
  Gdy gracz wybiera kartę, **otrzymuje wszystkie TG z tej karty**, a licznik karty zeruje
  się (`PickStrategyCardButtonHandler`: `player.setTg(tg + tgCount)`, potem
  `setScTradeGood(scPicked, 0)`).
- **Akumulacja TG:** na koniec fazy strategii (przy przejściu do kolejnej rundy) do każdej
  karty, której NIKT nie wybrał, dokładany jest +1 TG (`StrategyCardManager.incrementTradeGoods`:
  dla każdego `scNumber` spoza wybranych → `tgCount+1`). Dzięki temu niechciane karty rosną w TG.

**Inicjatywa dla fazy akcji:** kolejność tur ustala najniższy numer wybranej karty
(już zaimplementowane w `turn_flow.turn_order`, RULES.md 9).

**Primary/secondary (treść zdolności):** `primaryTexts`/`secondaryTexts` z danych karty —
pełne rozstrzyganie efektów (np. Leadership: +3 CC; Trade: +3 TG) to kolejne etapy (E4/akcje
strategiczne). W E2 implementujemy szkielet: pulę kart, wybór, akumulację/transfer TG,
oznaczenie karty jako ZAGRANEJ (exhausted). Efekty primary/secondary jako osobny krok.

Implementacja: `src/core/strategy_phase.py` (czyste funkcje) + model
`GameState.strategy_card_tg`, `GameState.speaker_id`, `PlayerState.exhausted_strategy_cards`;
endpointy `POST /strategy/pick`, `/strategy/play`, `/strategy/reset`.

---

## 14. Źródła danych: codexy + thunders_edge, dedup erraty — ✅ ZWERYFIKOWANE (dane)

📎 tirules: [Technology](rules_tirules/R_technology.md) · [Technology (komponenty)](rules_tirules/C_technology.md) · [Breakthroughs](rules_tirules/R_breakthroughs.md)

Źródło: dane technologii AsyncTI4 (`assets/data/technologies/*.json`), zweryfikowane
2026-10 na załadowanym rejestrze.

**Aktywne źródła (`enabled_sources.json`):** `base, pok, codex1, codex2, codex3, codex4,
thunders_edge`.

**Ustalenie (obala wcześniejsze założenie):** thunders_edge **NIE zawiera** zmian
z codexów. Wnosi 13 całkowicie nowych technologii (bez `homebrewReplacesID`), a nie
nadbudowę nad erratami. Oficjalne erraty (Ω/ΩΩ) istnieją TYLKO w codex1/codex4:
- X-89 Bacterial Weapon: `x89_base` (base) → `x89` ΩΩ? nie — `x89` (codex1, Ω) →
  `x89c4` (codex4, ΩΩ, najnowsza).
- Magen Defense Grid: `md_base` (base) → `md_c1` (codex1, Ω) → `md` (codex4, ΩΩ).

Dlatego codexy MUSZĄ pozostać włączone — bez nich gra używałaby starszych (błędnych)
wersji X-89 i Magen Defense Grid.

**Dedup erraty (God-Mode picker technologii):** warianty tej samej karty (base/Ω/ΩΩ)
mają różne nazwy (sufiks Ω/ΩΩ), więc dedup po nazwie ich nie zwijał. Reguła:
- Klucz rodziny = nazwa karty z usuniętym markerem Ω/ΩΩ i białymi znakami.
- Dla każdej rodziny zostaje wariant o najwyższym priorytecie źródła:
  `codex4 > codex3 > codex2 > codex1 > {pok, thunders_edge} > base`.
- Marker Ω/ΩΩ = oficjalny znacznik kolejnej erraty (dane AsyncTI4).
Implementacja: `frontend/.../PlayerEditorModal.tsx` (`techFamilyKey`, `SOURCE_PRIORITY`).

**Priorytet źródeł (od najwyższego):** `thunders_edge > pok > codex4..1 > base`
(źródła spoza listy = homebrew, najniższy priorytet). Gdy wiele włączonych źródeł
dostarcza wariant tego samego komponentu (np. karty strategii Construction/Warfare),
obowiązuje wariant z NAJWYŻSZEGO włączonego źródła (Thunder's Edge). To świadoma decyzja
projektowa użytkownika (wszystkie dodatki włączone, Thunder's Edge nadrzędny) — Thunder's
Edge przerabia Construction (4) i Warfare (6), więc jego warianty `te4construction` /
`te6warfare` wypierają `pok4construction` / `pok6warfare`.

**Grafika — fallback czysto wizualny:** gdy wariant najwyższego źródła nie ma assetu
obrazu (`imageURL: ""`, tak jest dla `te4construction`/`te6warfare`), UI używa grafiki
wariantu o tej samej initiative z niższego źródła (np. `ConstructionProphecyOfKings.webp`
z `pok4construction`, `Warfare.webp` z `pok6warfare`). Treść i parametry (nazwa, teksty,
inicjatywa, kolor) POZOSTAJĄ z wariantu najwyższego źródła — fallback dotyczy wyłącznie
obrazka. Gdy żaden wariant nie ma grafiki, UI daje fallback tekstowy.
Implementacja: `frontend/src/entities/lookup/strategyCards.ts`
(`SOURCE_PRIORITY`, `sourceRank`, `withImageFallback`).

**Wybór zestawu kart strategii — reguła w CORE (nie na froncie).** Silnik wybiera
kanoniczny zestaw kart strategii wg NAJWYŻSZEGO włączonego źródła (priorytet
`thunders_edge > pok > codex4 > codex3 > codex2 > codex1 > base`; źródła spoza listy =
homebrew są ignorowane przy tym wyborze). Przy włączonym Thunder's Edge obowiązuje
zestaw TE (alias `te`): Construction=`te4construction`, Warfare=`te6warfare`, pozostałe
karty PoK; bez TE — zestaw `pok` (`pok4construction`/`pok6warfare`); w dół aż do
`base_game`. Gdy żaden standardowy zestaw nie pasuje (same homebrew/puste źródła) —
bezpieczny fallback na `pok`. Reguła żyje w `core/registry.active_strategy_card_set_alias`
(czysta funkcja nad włączonymi źródłami), a `strategy_card_set()` bez jawnego aliasu
zwraca zestaw kanoniczny. Dzięki temu `/strategy/cards` i web-data zwracają kanoniczne
warianty (te4/te6 przy TE) niezależnie od frontu — front tylko renderuje. Priorytet
źródeł identyczny jak przy dedupie erraty technologii (wyżej). Znalezisko #5 przeglądu
semantycznego (część backendowa).

## 15. Typ planety: pole `planetTypes` (lista) vs `planetType` — ✅ ZWERYFIKOWANE (dane)

📎 tirules: [Planets](rules_tirules/R_planets.md) · [Legendary Planets](rules_tirules/R_legendary_planets.md)

Źródło: dane planet AsyncTI4 (`assets/planets/*.json`). Część źródeł (np. thunders_edge)
podaje typ planety jako listę `planetTypes` (np. `["FACTION"]`) i NIE ma pojedynczego
`planetType`. Konsekwencje i naprawa:
- Backend: `PlanetDef` trzyma oba pola (`planet_type`, `planet_types`).
- Frontend: podgląd planety czytał tylko `planetType` (pojedynczy) — dla planet
  thunders_edge brak koloru/etykiety/ikony frakcji. Naprawa: typ efektywny =
  `planetType ?? planetTypes[0]` w `PlanetDetailsCard` (`effectivePlanetType`,
  `PlanetGlyph`) oraz w `PlanetCard/planetCardStyle.ts` (`getPlanetIconSrc`).
- Grafiki (cardImage) i opisy (flavourText) planet thunders_edge nie istnieją w danych —
  nie da się ich wygenerować; frontend bierze grafiki z CDN gdy ścieżka jest dostępna.

---

## 16. Wybór technologii startowej frakcji — ✅ ZWERYFIKOWANE (dane)

📎 tirules: [Technology](rules_tirules/R_technology.md) · [Technology (Strategy Card)](rules_tirules/R_technology_sc.md)

Źródło: dane frakcji AsyncTI4 (`assets/data/factions/*.json`), pola `startingTechOptions`
+ `startingTechAmount`. Zweryfikowane 2026-10 na aktywnych źródłach.

Większość frakcji ma STAŁE technologie startowe (`startingTech`). Część NIE ma stałych —
gracz WYBIERA ``startingTechAmount`` technologii spośród ``startingTechOptions``:

| Frakcja | Ile | Opcje (alias) |
|---|---|---|
| Winnu | 1 | amd, det, nm, pa, st, sdn, ps, aida (dowolna 1) |
| Argent Flight | 2 | nm, st, ps |
| Last Bastion (TE) | 1 | amd, det, st, sdn |
| The Firmament (TE) | 1 | nm, pa, st, sdn |
| The Crimson Rebellion (TE) | 1 | det, amd, ps, aida |
| The Ral Nel Consortium (TE) | 1 | nm, pa, ps, aida |

Implementacja: `faction_setup.resolve_starting_tech` (walidacja liczności i dozwolonych
opcji) + wybór przekazywany przez `starting_tech` w żądaniu setupu/nowej gry; UI pokazuje
menu wyboru N z listy, gdy `startingTechAmount > 0`.

### 16a. Odroczony wybór technologii: Keleres i Deepwrought — ✅ ZWERYFIKOWANE (tirules)

📎 tirules: [Council Keleres](rules_tirules/F_keleres.md) (The Tribunii) ·
[The Deepwrought Scholarate](rules_tirules/F_deepwrought.md) (Research Team)

Dwie frakcje wybierają technologie startowe NIE w setupie, tylko PÓŹNIEJ — w grze, po tym
jak WSZYSCY pozostali gracze otrzymają swoje technologie startowe:

- **The Council Keleres** (`keleresm`/`keleresx`/`keleresa`) — reguła „The Tribunii": wybiera
  DO 2 nie-frakcyjnych technologii POSIADANYCH przez innych graczy (jeśli nie ma 2 unikalnych,
  startuje z mniejszą liczbą). W danych: `startingTech=[]`, brak opcji → `startingTechAmount=0`.
- **The Deepwrought Scholarate** (`deepwrought`) — zdolność „Research Team": „research
  technology twice" (2 dowolne technologie z początku drzewka, zgodnie z prerekwizytami).
  W danych: `startingTechAmount=2`, ale `startingTechOptions=[]` (PUSTE).

Stan implementacji:
- `resolve_starting_tech` traktuje „amount > 0 przy pustej liście opcji" jako frakcję
  z odroczonym wyborem → zwraca `[]` (start bez technologii), zamiast błędu/fallbacku.
- UI setupu (`frontend/.../setup/deferredTech.ts`) klasyfikuje te 4 id jako „deferred":
  nie pokazuje panelu wyboru, tylko komunikat (po angielsku), że wybór nastąpi w grze
  przed 1. fazą agendy; walidacja ich nie wymaga i `starting_tech` nie jest wysyłane.
- ⚠️ ZAŁOŽENIE / TODO: faktyczny ODROCZONY wybór w grze (okno czasowe po rozstawieniu
  wszystkich graczy; dla Keleresa odczyt technologii innych graczy + prereqs dla
  Deepwrought) NIE jest jeszcze zakodowany — na razie operator nadaje te technologie
  ręcznie (God-Mode). Do dokodowania przy odpowiednim etapie silnika (okna czasowe).

## 17. Systemy domowe poza planszą: Ghost of Creuss, Crimson Rebellion — ✅ ZWERYFIKOWANE (bot)

📎 tirules: [Wormholes](rules_tirules/R_wormholes.md) · [The Ghosts of Creuss](rules_tirules/F_creuss.md) · [The Crimson Rebellion](rules_tirules/F_rebellion.md) · [System Tiles](rules_tirules/R_system_tiles.md)

Źródło (nie z pamięci): AsyncTI4 bot, `PlayerSetupService` (blok „GHOST AND CRIMSON EXTRA
HS TILES"). Obie frakcje mają system domowy fizycznie POZA planszą, połączony z nią przez
wormhole:

- **Ghost of Creuss**: na slocie domowym stoi **brama** — kafelek `17` „Creuss Gate"
  (pusty, wormhole DELTA). Prawdziwy system domowy to kafelek `51` „Creuss" (planeta
  `creuss`, DELTA), kładziony POZA planszą. Flota startowa i kontrola planety są na `51`.
- **Crimson Rebellion**: brama to kafelek `94` „The Sorrow" (pusty, wormhole EPSILON);
  prawdziwy dom to kafelek `118` (planeta `ahkcreuxx`, EPSILON) poza planszą.

**Pozycja off-board (róg obszaru gry)** — wg slotu domowego gracza (reguła z bota):
- sloty `301`, `304` → `tr` (prawy górny róg),
- sloty `307`, `310` → `br` (prawy dolny),
- sloty `313`, `316` → `bl` (lewy dolny),
- kolizja (róg zajęty) → zamiana `tr`↔`br`.

Pozycje `tr/br/bl/tl` to specjalne sloty narożne obszaru gry (nie pierścienie). Frontend
viewer zna ich piksele (`frontend/.../tileCoordinates.ts`, `tilePositioning.ts`), więc
wystarczy wyemitować kafelek na tej pozycji. Mapowanie brama→dom (`17→51`, `94→118`) oraz
rogi pochodzą z `PlayerSetupService` AsyncTI4 — zakodowane jawnie jako tabela reguł
(`faction_setup.OFF_BOARD_HOME`), nie zgadywane.


## 18. Panel gracza: zdolności, technologie frakcyjne, przełomy — ✅ ZWERYFIKOWANE (dane + frontend)

📎 tirules: [Breakthroughs](rules_tirules/R_breakthroughs.md) · [Synergy](rules_tirules/R_synergy.md) · [Technology](rules_tirules/R_technology.md) · [Leaders](rules_tirules/R_leaders.md)

AsyncTI4 wypisuje na karcie gracza także **zdolności frakcji** (faction abilities),
**technologie frakcyjne** (faction tech) i **przełom** (breakthrough — mechanika
Thunder's Edge), każde w odpowiednim stanie. Źródła (nie z pamięci):

- **Dane** (`assets/data/`): zdolności w `abilities/*.json` (pola `id`, `name`,
  `faction`, `permanentEffect`/`window`/`windowEffect`); technologie w
  `technologies/*.json` (pola `alias`→id, `faction`, `types`); przełomy w
  `breakthroughs/*.json` (pola `alias`→id, `faction`, `synergy`). Przypisanie do
  frakcji idzie przez POLE `faction` wpisu (oraz listy `abilities`/`factionTech` w
  danych frakcji) — nie z pamięci.
- **Frontend** (kontrakt `web-data`, zweryfikowany w kodzie viewera): `PlayerData`
  czyta `abilities: string[]` (ID zdolności → komponent `Ability`), `factionTechs`
  i `notResearchedFactionTechs` (niezbadane frontend WYSZARZA, prop `unresearched`
  komponentu `Tech`), oraz `breakthrough?: {breakthroughId, unlocked, exhausted,
  tradeGoodsStored}` (komponent `Breakthrough`; slot chowa się, gdy nikt nie ma
  przełomu). Plik typów: `frontend/src/entities/data/types.ts`; render:
  `domains/player/components/deck/PlayerDeckRow.tsx` + `usePlayerCardComputedData.ts`.

**Reguła stanów (jak emitujemy):**
- Zdolności są pasywnie stanowe — ich okno/efekt wynika z danych (`permanentEffect`
  vs `window`), więc wysyłamy tylko identyfikatory (`abilities`). Brak locked/exhausted
  w stylu liderów.
- Technologia frakcyjna jest **zbadana**, gdy jej ID jest na liście `technologies`
  gracza → trafia do `techs` (rack techów). **Niezbadana** → `notResearchedFactionTechs`
  (frontend wyszarza). `factionTechs` = pełna lista z danych frakcji.
- Przełom (jeden per frakcja) — stan z `PlayerState`: `breakthrough_unlocked` (po
  spełnieniu synergii), `breakthrough_exhausted` (po akcji), `breakthrough_tg`
  (odłożone TG). Start: zablokowany.

Implementacja: `FactionDef.abilities`/`faction_tech` + modele `AbilityDef`/
`TechnologyDef`/`BreakthroughDef` (rejestr ładuje je z assetów po `source`); emisja
w `web_data.py` (`_faction_abilities`, `_faction_techs`, `_player_breakthrough`).


## 19. Akcja taktyczna: aktywacja systemu + maszyna kroków — ✅ ZWERYFIKOWANE (AsyncTI4 bot)

📎 tirules: [Tactical Action](rules_tirules/R_tactical_action.md) · [Active System](rules_tirules/R_active_system.md) · [Command Tokens](rules_tirules/R_command_tokens.md) · [Movement](rules_tirules/R_movement.md) · [Invasion](rules_tirules/R_invasion.md) · [Producing Units](rules_tirules/R_producing_units.md)

> ⚠️ **AKTUALIZACJA KIERUNKU (patrz sekcja 29):** adnotacje `NIE waliduje` / `asystent, nie sędzia` w tej sekcji są UNIEWAŻNIONE. Treść pozostaje poprawna jako REFERENCJA mechaniki TI4; egzekucja reguł wchodzi do `core/` zgodnie z 29.1.


Etap E3. **Decyzja projektowa (ustalona z użytkownikiem):** aplikacja PROWADZI gracza
przez kroki akcji taktycznej, ale **NIE waliduje reguł TI4** — gracze grają fizycznie
(stół/Tabletop) i wprowadzają wynik. Silnik to asystent stołu, nie sędzia. Dlatego poniższe
reguły są REFERENCJĄ TI4; egzekucję (legalność ruchu, zasięg, fleet supply) pilnuje operator.

**Sekwencja kroków akcji taktycznej** (okna czasowe fazy akcji), źródło: AsyncTI4
`service/tactical/` + LRR: `ACTIVATION → MOVEMENT → SPACE_CANNON (offense) → SPACE_COMBAT →
INVASION → PRODUCTION`. Model: `GameState.tactical_step` (enum `TacticalStep`), `active_system`
(pozycja aktywowanego kafelka). Maszyna: `core/tactical.py` (`activate_system`, `next_step`,
`set_step`, `end_tactical_action`).

**Aktywacja systemu** (źródło: `CommandCounterHelper.addCC` z `useTactic=true`, `Tile.addCC`
→ `Space.ccList`, `Game.setActiveSystem`):
- Aktywny gracz kładzie **żeton dowodzenia** (command token) w **przestrzeni** systemu —
  model: `SystemState.command_tokens: list[player_id]`. Żeton bierze się z **puli taktycznej**
  gracza (`PlayerState.tactical_cc`, dekrementowane o 1).
- Ustawiany jest `active_system`; maszyna startuje od `MOVEMENT` (aktywacja to krok zerowy).
- **Reguła TI4 (referencyjnie, NIE egzekwowana):** nie można aktywować systemu, w którym
  leży już TWÓJ żeton dowodzenia (AsyncTI4 `ButtonHelper.canActivateTile`:
  `!hasCC(player.color, tile)`). U nas operator tego pilnuje; `activate_system` jest
  idempotentne (nie duplikuje żetonu) i nie blokuje.
- Żeton **zostaje** na systemie po zakończeniu akcji (jak na stole) — `end_tactical_action`
  czyści tylko `active_system`/`tactical_step`, nie zdejmuje CC.

**Kontrola a żetony (potwierdzone w AsyncTI4):** żeton dowodzenia (`command_tokens` /
`Space.ccList`) jest NIEZALEŻNY od kontroli. Kontrola PRZESTRZENI nie jest osobnym polem —
wynika z obecności statków (`space_units`). Kontrola PLANETY to jawny `planet_owners[planet]`
(jeden właściciel; `UnitHolder.addControl` czyści poprzednika). Stan „planetę kontroluje
gracz A, a przestrzeń/żeton ma gracz B" jest legalny i reprezentowalny (patrz RULES.md 2b/12).

**God-Mode:** `board_edit.place_command_token` / `remove_command_token` pozwalają operatorowi
ręcznie korygować żetony (bez zużycia puli — to korekta, nie aktywacja).


## 20. Walka: pomoce liczbowe (asystent, nie sędzia) — ✅ ZWERYFIKOWANE (dane UnitDef)

📎 tirules: [Space Combat](rules_tirules/R_space_combat.md) · [Ground Combat](rules_tirules/R_ground_combat.md) · [Combat (Attribute)](rules_tirules/R_combat.md) · [Sustain Damage](rules_tirules/R_sustain_damage.md) · [Rerolls](rules_tirules/R_rerolls.md) · [Anti–Fighter Barrage](rules_tirules/R_anti_fighter_barrage.md)

> ⚠️ **AKTUALIZACJA KIERUNKU (patrz sekcja 29):** adnotacje `NIE waliduje` / `asystent, nie sędzia` w tej sekcji są UNIEWAŻNIONE. Treść pozostaje poprawna jako REFERENCJA mechaniki TI4; egzekucja reguł wchodzi do `core/` zgodnie z 29.1.


Etap E3. **Decyzja projektowa:** aplikacja NIE rozstrzyga walki — nie rzuca kośćmi i nie
przypisuje trafień. Gracze robią to fizycznie na stole; aplikacja daje tylko POMOCE
liczbowe i wygodne okno do odejmowania zniszczonych jednostek (przez God-Mode edit-units).

**Statystyki bojowe** czytane z `UnitDef` (rejestr, zero z pamięci): `combat_hits_on`
(trafia na X+), `combat_die_count` (ile kości na sztukę). Jednostki bez tych pól (PDS, dok)
NIE biorą udziału w walce kosmicznej — pomijane (PDS ma osobny `spaceCannonHitsOn`, inna
mechanika). Oczekiwane trafienia grupy: `count * die_count * (11 - hits_on) / 10`.

**Dobór wariantu jednostki gracza** (`core/combat.resolve_unit_variant`): dla danego
`base_type` wybieramy wariant wg priorytetu frakcyjny-ulepszony > frakcyjny-bazowy >
generyczny-ulepszony > generyczny-bazowy. Ulepszenie liczy się tylko, gdy gracz ma wymaganą
technologię (`required_tech_id`). Spójne z regułą doboru jednostek w web-data (RULES.md 10),
więc statystyki w oknie walki odpowiadają faktycznym jednostkom gracza (np. Sol carrier
ulepszony, flagship frakcyjny 5+/2 kości, War Sun 3+/3 kości).

**Wykrycie walki:** `space_combat_participants` (statki w przestrzeni) / `ground_combat_participants`
(jednostki naziemne na planecie) zwracają strony TYLKO gdy walczących ≥2 (inaczej brak walki).
Siły liczone z `space_units` / `planet_units` (kontrola przestrzeni = obecność statków, RULES.md 19).

**Przepływ w UI:** przycisk „Walka" w panelu taktycznym (gdy aktywny system ma statki ≥2
graczy) → `GET /tactical/combat/{pos}` → okno z dwiema stronami, listą jednostek + pomoce
(kości, X+, expected). Odejmowanie zniszczonych = `edit-units` delta -1 (God-Mode).


## 21. Przejęcie kontroli planety (inwazja) — ✅ ZWERYFIKOWANE (AsyncTI4 bot)

📎 tirules: [Invasion](rules_tirules/R_invasion.md) · [Ground Combat](rules_tirules/R_ground_combat.md) · [Control](rules_tirules/R_control.md) · [Bombardment](rules_tirules/R_bombardment.md) · [Planetary Shield](rules_tirules/R_planetary_shield.md)

> ⚠️ **AKTUALIZACJA KIERUNKU (patrz sekcja 29):** adnotacje `NIE waliduje` / `asystent, nie sędzia` w tej sekcji są UNIEWAŻNIONE. Treść pozostaje poprawna jako REFERENCJA mechaniki TI4; egzekucja reguł wchodzi do `core/` zgodnie z 29.1.


Etap E3. Po wygranej inwazji gracz przejmuje kontrolę planety. Reguła (źródło: AsyncTI4
`UnitHolder.addControl` = `controlList.clear(); controlList.add(cc)` oraz `AddPlanetService.addPlanet`
usuwający poprzedniego właściciela przez `player_.removePlanet`): planeta ma DOKŁADNIE
JEDNEGO właściciela — nowy nadpisuje poprzedniego. Model: `SystemState.planet_owners[planet]`.

Implementacja: `core/tactical.capture_planet(state, grid, position, planet, faction_key)` —
ustawia `planet_owners[planet] = player_id` (rozwiązany jak w God-Mode). Aplikacja NIE
sprawdza, czy inwazja faktycznie się powiodła — operator potwierdza przyciskiem „Przejmij"
w oknie walki naziemnej. Kontrola planety jest niezależna od kontroli przestrzeni (statki
innego gracza mogą zostać w systemie — RULES.md 19).

## 22. Produkcja: pomoc liczbowa (koszt + zasoby) — ✅ ZWERYFIKOWANE (dane UnitDef)

📎 tirules: [Producing Units](rules_tirules/R_producing_units.md) · [Production (Unit Ability)](rules_tirules/R_production.md) · [Cost (Attribute)](rules_tirules/R_cost.md) · [Resources](rules_tirules/R_resources.md) · [Space Dock](rules_tirules/R_space_dock.md)

> ⚠️ **AKTUALIZACJA KIERUNKU (patrz sekcja 29):** adnotacje `NIE waliduje` / `asystent, nie sędzia` w tej sekcji są UNIEWAŻNIONE. Treść pozostaje poprawna jako REFERENCJA mechaniki TI4; egzekucja reguł wchodzi do `core/` zgodnie z 29.1.


Etap E3. Aplikacja NIE waliduje limitów produkcji ani wydatków — to pomoc liczbowa.
`core/tactical.production_help(state, registry, player_id)` liczy:
- **dostępne zasoby** = suma `PlanetDef.resources` planet kontrolowanych przez gracza
  (`planet_owners`), z rejestru (nie z pamięci);
- **koszt jednostek** gracza z `UnitDef.cost` (wariant frakcyjny/ulepszony wg technologii —
  `combat.resolve_unit_variant`, spójnie z RULES.md 10/20).

**Produkcja podwójna** (2 sztuki za pojedynczy koszt): fighter, infantry — reguła LRR
„Producing Units"; trzymana jako jawna tabela `_DUAL_PRODUCTION` (dane kosztu z UnitDef).
Stawianie jednostek robi operator przez God-Mode (edit-units), produkcja to tylko podpowiedź.


## 23. Kontrola planety przy stawianiu jednostek (auto) — ✅ ZWERYFIKOWANE (AsyncTI4 bot)

📎 tirules: [Control](rules_tirules/R_control.md) · [Ground Forces](rules_tirules/R_ground_forces.md) · [Planets](rules_tirules/R_planets.md) · [Coexistence](rules_tirules/R_coexistence.md)

Postawienie/przeniesienie jednostki NAZIEMNEJ lub struktury na planetę automatycznie
nadaje kontrolę. Źródło (nie z pamięci): AsyncTI4 `AddPlanetToPlayAreaService.addPlanetToPlayArea`,
wołane po KAŻDEJ zmianie jednostek (`AddUnitService`/`RemoveUnitService`). Reguła:

1. **Przestrzeń nie liczy się.** Zmiana jednostek w strefie `space` (statki) NIE zmienia
   kontroli żadnej planety (statki kontrolują tylko przestrzeń — obecność, RULES.md 19).
2. **Myśliwce pomijane.** Przy liczeniu „kto jest na planecie" pomijamy jednostki kosmiczne
   (u nas filtr `is_space_unit` — myśliwiec jest kosmiczny). Liczą się piechota, mech,
   dok, PDS (jednostki naziemne/struktury).
3. **Dokładnie jeden kolor → kontrola.** Jeśli po pominięciu myśliwców na planecie jest
   DOKŁADNIE JEDEN gracz → nadajemy mu kontrolę (nadpisując poprzedniego właściciela).
4. **Lepkość kontroli.** 0 graczy (planeta pusta) lub ≥2 (koegzystencja) → kontrola BEZ
   zmiany. Usunięcie ostatniej piechoty NIE odbiera planety — kontrola trwa, dopóki ktoś
   inny jej nie przejmie (postawi swoją jednostkę jako jedyny kolor). To wierne TI4.

Implementacja: `board_edit.recompute_planet_control(system, planet)` wołane w `edit_units`,
`move_units` (strefa źródłowa i docelowa), `set_planet_units` (gdy brak jawnego `owner_id`).
Jawny `owner_id` od operatora ma priorytet (celowe ustawienie God-Mode). Utrata kontroli
tylko przez przejęcie przez innego gracza albo jawny edytor gracza (`sync_controlled_planets`).

**Dlaczego to był bug:** `edit_units`/`move_units` nie dotykały `planet_owners`, więc
stawianie piechoty nie dawało kontroli (panel „kontrolowane planety" się nie aktualizował).
web-data liczy kontrolowane planety wyłącznie z `planet_owners` — stąd brak efektu.

## 24. Kolejność graczy: seating order, speaker, wybór kart strategii — ✅ ZWERYFIKOWANE (LRR + AsyncTI4 bot)

📎 tirules: [Speaker](rules_tirules/R_speaker.md) · [Initiative Order](rules_tirules/R_initiative_order.md) · [Strategy Phase](rules_tirules/R_strategy_phase.md) · [Active Player](rules_tirules/R_active_player.md)

> ⚠️ **AKTUALIZACJA KIERUNKU (patrz sekcja 29):** adnotacje `NIE waliduje` / `asystent, nie sędzia` w tej sekcji są UNIEWAŻNIONE. Treść pozostaje poprawna jako REFERENCJA mechaniki TI4; egzekucja reguł wchodzi do `core/` zgodnie z 29.1.


Etap E1/E2 (przebudowa tur). Dwie RÓŻNE kolejności obowiązują w różnych fazach:

- **Speaker order (kolejność miejsc)** — używana w **fazie strategii** przy wyborze kart.
  Zaczyna **mówca (speaker)**, dalej **zgodnie z ruchem wskazówek zegara** (następni gracze
  przy stole). To kolejność zasiadania, NIE inicjatywa kart. Źródło: LRR „Strategy Phase"
  (gracze wybierają karty w speaker order) + AsyncTI4 `StartStrategyPhase` / kolejka wyboru.
- **Initiative order (kolejność inicjatywy)** — używana w **fazie akcji** (oraz statusu/
  agendzie). Ustalana przez **najniższy numer wybranej karty strategii** (patrz RULES.md 9).

**Seating order w modelu:** `GameState.seating_order: list[str]` = kolejność graczy wokół
stołu (player_id), ustalana przy `/game/new` z kolejności podanych graczy (gracz 1 =
pierwszy przy stole). `GameState.speaker_id` = mówca; na start = pierwszy gracz seating order.
Speaker order to rotacja `seating_order` zaczynająca się od `speaker_id` (zgodnie z zegarem).

**Wybór kart w fazie strategii (reguła przepływu):**
- W fazie strategii `active_player_id` = gracz, którego kolej wybierać. Start: `speaker_id`.
- Po wyborze karty tura przechodzi do **następnego gracza w speaker order**, który jeszcze
  nie ma karty. Gdy wszyscy wybrali → `active_player_id = None` (faza strategii gotowa do
  przejścia w akcję; `next_phase` ustawi aktywnego wg inicjatywy).
- **Asystent, nie sędzia (decyzja projektowa, memory `engine-is-table-assistant-not-referee`):**
  silnik PODPOWIADA, kto wybiera (podświetlenie), i automatycznie przechodzi do następnego,
  ale NIE blokuje twardo wyboru za innego gracza — operator może nadpisać kolejność. Wybór
  karty już posiadanej/niedostępnej dalej jest odrzucany (to spójność danych, nie reguła).

**Faza akcji:** pierwszy turę zaczyna gracz o najniższej inicjatywie (`turn_flow.next_phase`
wchodząc w akcję ustawia `active_player_id = turn_order[0]`). Kolejność i pas: RULES.md 9.

Implementacja: `GameState.seating_order`/`speaker_id` (`game_state.py`); `strategy_phase`
(`speaker_order`, `next_strategy_picker`, `pick_strategy_card` rotujące aktywnego);
`turn_flow.next_phase`/`next_round` ustawiające aktywnego mówcę na starcie fazy strategii.

## 25. Drag-and-drop przenoszenia jednostek (UI/God-Mode) — ✅ DECYZJA PROJEKTOWA

📎 tirules: [Transport](rules_tirules/R_transport.md) · [Movement](rules_tirules/R_movement.md) · [Units](rules_tirules/R_units.md) · [Capacity](rules_tirules/R_capacity.md)

To mechanika WYGODY UI, nie reguła TI4 — przenoszenie bez walidacji zasad (asystent, nie
sędzia). Przeciągasz sprite jednostki z kafelka/strefy na inny kafelek lub planetę; dla
stosów (>1 szt., np. piechota `gf`, fightery `ff`, mechy `mf`) po upuszczeniu pojawia się
pytanie „ile przenieść" (1 / połowa / wszystkie / dowolna liczba), pojedyncza sztuka
przenosi się od razu.

**Jak to działa (konwencje, nie reguły):**
- Mapa przewija się biblioteką `dragscroll`, która binduje NATYWNY `mousedown` (bubbling)
  na kontenerze `.dragscroll` i na nim startuje pan. React `stopPropagation` tego nie
  zatrzymuje, dlatego start dragu jednostki przejmujemy WŁASNYMI natywnymi listenerami w
  fazie CAPTURE na sprite'cie (`mousedown`/`touchstart`) z `stopPropagation` — zdarzenie nie
  dociera do dragscroll, więc chwytając jednostkę NIE przesuwasz planszy. Próg ruchu
  (`DRAG_THRESHOLD=8px`) odróżnia przeciąganie od kliknięcia (krótki ruch = klik → dossier).
  Duch jednostki renderowany portalem do `document.body` (mapa ma `transform: scale`, który
  łamałby `position: fixed`).
- Tooltip jednostki (hover) jest CHOWANY na czas przeciągania — flaga `appStore.isDraggingUnit`
  (ustawiana po przekroczeniu progu) blokuje pokazanie tooltipa i czyści istniejący
  (inaczej zasłaniałby mapę w trakcie gestu).
- Natywne zaznaczanie tekstu/grafiki i HTML5 image-drag są WYŁĄCZONE (inaczej szarpnięcie
  zaznaczało sprite'y/kafelki „jak obrazek w przeglądarce" i gubiło gest): statycznie
  `.draggable` + `.draggable img` (`user-select:none`, `-webkit-user-drag:none`), twardo
  `dragstart`→`preventDefault` na sprite'cie, oraz globalnie `body.dragging-unit`
  (`user-select:none !important`) na czas realnego przeciągania.
- Cel upuszczenia z DOM pod kursorem (`elementFromPoint`): kafelek = `id="tile-<pozycja>"`,
  planeta = `data-search-key="planet:<id>"`. Strefa docelowa = nazwa planety albo `"space"`
  (orbita), spójnie z `stackHolder(stack) = planetName ?? "space"` i kontraktem
  `/units/move` (RULES.md: `from_zone`/`to_zone` = `"space"` albo ID planety).
- Przeniesienie wykonuje istniejący endpoint `POST /units/move` (`board_edit.move_units`) —
  obcina `count` do dostępnych, przelicza kontrolę planety przy wejściu/wyjściu na planetę
  (RULES.md 23). Commit → historia (Undo działa).

Implementacja: `frontend/.../hooks/useUnitDrag.ts` (pointer events + duch + wykrycie celu),
`UnitStack.tsx` (podpięcie na sprite/badge), `UnitDragGhost.tsx` (duch), `MoveQuantityModal.tsx`
(pytanie „ile przenieść"), `appStore.unitDrop` (stan pytania). DnD aktywny tylko dla realnych
jednostek poza odtwarzaniem historii (replay).

## 26. Umiejscowienie jednostek przy przenoszeniu: statek↔przestrzeń, naziemne↔planeta — ✅ ZWERYFIKOWANE

📎 tirules: [Units](rules_tirules/R_units.md) · [Ships](rules_tirules/R_ships.md) · [Ground Forces](rules_tirules/R_ground_forces.md) · [Structures](rules_tirules/R_structures.md) · [Transport](rules_tirules/R_transport.md)

Reguła TI4 (LRR /wiki/Units, /wiki/Movement; spójna z klasyfikacją RULES.md 2b): jednostka
istnieje tylko w strefie zgodnej z jej typem.
- **Statki** (`fighter`, `destroyer`, `cruiser`, `carrier`, `dreadnought`, `flagship`,
  `warsun`) stoją WYŁĄCZNIE w PRZESTRZENI systemu (`"space"`) — nigdy na planecie.
- **Siły naziemne i struktury** (`infantry`, `mech`, `pds`, `spacedock`) stoją WYŁĄCZNIE
  na PLANECIE (strefa = id planety) — nigdy w przestrzeni.

**Egzekucja (nie tylko UX):** w odróżnieniu od innych edycji God-Mode (asystent, nie sędzia),
tę regułę EGZEKWUJEMY w `core`, bo „statek na planecie" to stan niereprezentowalny fizycznie
i psułby render/kontrolę. `board_edit.move_units` odrzuca (``ValueError`` → HTTP 422)
przeniesienie łamiące umiejscowienie. Funkcja decyzyjna: `unit_catalog.placement_allows_zone(
base_type, zone)` — czysta reguła świata, wołana przez UI (drag-and-drop) i przyszłego BOTA
(ten sam punkt wejścia, więc bot też nie postawi statku na planecie).

**UX drag-and-drop (prezentacja, nie reguła):** upuszczenie STATKU na planetę nie jest błędem
dla gracza — front celuje wtedy w ORBITĘ (`"space"`) tego samego kafelka (gracz wskazał system).
Backend i tak waliduje twardo — to tylko wygodne mapowanie gestu na dozwoloną strefę.

**⚠️ WYJĄTEK TRANSPORTU (Blok B2) — siły naziemne/myśliwce W PRZESTRZENI podczas ruchu.**
Reguła „naziemne tylko na planecie" dotyczy stanu SPOCZYNKOWEGO (setup, God-Mode edycja). W
AKCJI TAKTYCZNEJ siły naziemne i myśliwce jadą statkiem jako ŁADUNEK i stoją w PRZESTRZENI
systemu docelowego aż do kroku **Commit Ground Forces** (inwazja), kiedy lądują na planecie
(źródło: `R_transport.md`, `R_invasion.md` — „Units are considered to be on the planet for game
effects from the Commit Ground Forces step onward"). Dlatego podczas MOVEMENT front NIE blokuje
piechoty/mecha upuszczonego na ORBITĘ aktywnego systemu (wcześniej `resolveTarget valid=false` —
to był błąd). Blokada „naziemne nie na orbitę" obowiązuje nadal POZA akcją taktyczną (God-Mode:
`board_edit.move_units` + `placement_allows_zone`). Capacity transportu i tak waliduje
`move_fleet` (RULES.md 32.3).

Implementacja: `unit_catalog.placement_allows_zone`/`zone_is_space`, `board_edit.move_units`
(walidacja God-Mode), frontend `useUnitDrag` (mapowanie statek→orbita; w akcji taktycznej
dopuszcza ładunek naziemny w przestrzeni aktywnego systemu).


## 27. Wyczerpywanie komponentów: planety, technologie, liderzy (exhaust/ready) — ✅ ZWERYFIKOWANE (LRR + dane)

📎 tirules: [Exhausted](rules_tirules/R_exhausted.md) · [Readied](rules_tirules/R_readied.md) · [Status Phase](rules_tirules/R_status_phase.md) · [Planets](rules_tirules/R_planets.md) · [Technology](rules_tirules/R_technology.md)

Etap E4 (kontrola komponentów). **Decyzja projektowa:** asystent stołu — operator ręcznie
przełącza stan, aplikacja NIE wymusza, kiedy komponent się wyczerpuje. Backend trzyma stan
i commituje do historii (Undo działa).

**Planety i technologie** mają stan GOTOWY (ready) / WYCZERPANY (exhausted). W TI4 planetę
wyczerpuje się, wydając jej zasoby lub wpływy; część technologii (jednostkowe/akcji) też się
wyczerpuje. Odświeżenie (ready) następuje w fazie statusu („Ready Cards"). Źródło: LRR 2.0,
hasła „Exhausted" i „Status Phase" (TI Wiki / Living Rules). Jednostki bez stanu (np. technologie
pasywne) i tak mogą być oznaczone — to narzędzie operatora, nie walidator reguł.

**Model:** `PlayerState.exhausted_planets: list[str]`, `PlayerState.exhausted_technologies:
list[str]` (gotowy = kontrolowany/posiadany, którego NIE ma na liście). Liderzy mają osobny,
już istniejący stan w `leader_states: {leader_id: "locked"|"unlocked"|"exhausted"}` (RULES.md 18).

**Core:** `board_edit.toggle_planet_exhaust`, `toggle_tech_exhaust` (przełącznik obecności na
liście), `set_leader_state` (ustawia stan jednego lidera, scala z resztą). **API:**
`POST /player/planet/toggle-exhaust`, `/player/tech/toggle-exhaust`, `/player/leader/set-state`.
**Web-data:** `playerData.exhaustedPlanets`/`exhaustedTechs` (filtrowane do faktycznie
posiadanych) + flaga `exhausted` w `PlanetEntityData` (`tileUnitData[pos].planets[id].exhausted`).

**UI — menu kontekstowe (prawy przycisk myszy), NIE akcja komponentowa.** Wyczerpywanie to
ogólna część rozgrywki, więc NIE mieszkało w zakładce „Komponentowa" panelu akcji (ta jest dla
AKCJI komponentowych = kart z napisem „ACTION", etap E4). Zamiast tego: RMB na komponencie
gracza w panelu gracza otwiera menu z „Wyczerp / Odśwież" (liderzy też „Odblokuj/Zablokuj").
Komponent menu: `frontend/src/shared/ui/ContextMenu` (`useContextMenu` + `ContextMenu`) —
pozycjonowane pod kursorem, portalowane, rozszerzalne listą pozycji (dokładamy kolejne później).
Podpięte w `PlanetCard`, `Tech`, `LeaderChip`, `CompactLeader`; `player_id` (`discordId`)
przewiercony do WSZYSTKICH trzech wariantów panelu gracza: `PlayerCardDeck` (panel pełny),
`PlayerCardSidebar` (panel boczny przy mapie) i `PlayerDeckRow` (wiersz deck; techy przez
`TechGridMobile`) — przez `PlayerCardPlanetsArea`/`Leaders`/`buildTechElementsForType`.
Akcje wołają `useBoardEditor.togglePlanetExhaust/toggleTechExhaust/setLeaderState`.

**Menu kontekstowe kafelka systemu (mapa):** RMB na kafelku (`MapTile`) → „Aktywuj system" —
woła `useBoardEditor.activateSystem(position)` (POST `/tactical/activate`), co KŁADZIE żeton
dowodzenia AKTYWNEGO gracza w przestrzeni systemu, ustawia `active_system` i krok `MOVEMENT`,
zdejmuje 1 z puli taktycznej (`core.tactical.activate_system`, RULES.md 19). Pozycja jest
zablokowana (disabled), gdy nie ma aktywnego gracza (`active_player_id` None → backend 422).
Menu pomija kafelki hyperlane/embedded. To ta sama akcja co przycisk „Aktywuj system" w panelu
faz — menu RMB omija tryb klikania (`activateMode`) i woła ją wprost.


## 28. Grywalne frakcje vs placeholdery systemowe (Neutral/Lazax) — ✅ ZWERYFIKOWANE (dane AsyncTI4)

📎 tirules: [Neutral Units](rules_tirules/R_neutral_units.md) · [⚪ The Firmament / ✖ The Obsidian](rules_tirules/F_firmament.md) · [Abilities](rules_tirules/R_abilities.md)

W danych frakcji AsyncTI4 (`assets/data/factions/`) są wpisy, które NIE są grywalnymi frakcjami,
tylko placeholderami systemowymi dla jednostek neutralnych / scen:
- `neutral` (`other.json`, source `thunders_edge`) — puste `homeSystem`, brak liderów/zdolności;
- `lazax` (`other.json`, source `lazax`) — jw.

**Kryterium grywalności** (`FactionDef.is_playable`): frakcja jest grywalna, gdy ma NIEPUSTY
`homeSystem` ORAZ komplet liderów (`leaders`). To odróżnia placeholdery (oba warunki fałszywe)
od wszystkich realnych frakcji. Źródło: struktura danych (plik `other.json` vs reszta), nie
reguła z pamięci. Endpoint `GET /factions` zwraca tylko grywalne; setup (`/setup/player`,
`/game/new`) odrzuca niegrywalne (422).

**Firmament vs Obsidian (ROZSTRZYGNIĘTE danymi):** `firmament` (homeSystem `96a`) i `obsidian`
(homeSystem `96b`) to dwie POŁOWY jednego, dwustronnego kafelka domowego Thunder's Edge. Przy
setupie wybiera się TYLKO **Firmament**; **Obsidian NIE jest wybieralny** — wchodzi do gry
wyłącznie przez akcję Firmamentu: „ACTION: Purge the Firmament's faction sheet, leaders, planet
card, and promissory note, then gain all of the faction components for The Obsidian." Obsidiana
w grę wprowadza jego zdolność THE BLADE'S ORCHESTRA (flip dwustronnych komponentów + gotowe
Cronos Hollow / Tallin Hollow).

Reguła w danych (nie z pamięci): Obsidian ma zdolność **`nocturne`**
(`assets/data/abilities/te_abilities.json`, `faction: "obsidian"`), której `permanentEffect` =
„This faction cannot be chosen during setup." (dodatkowo franken errata oznacza `nocturne` jako
`undraftable`). Dlatego `FactionDef.is_playable` wyklucza frakcje mające zdolność `nocturne`
(stała `NO_SETUP_CHOICE_ABILITY` w `models.py`). Efekt: `/factions` pokazuje Firmament, ukrywa
Obsidian; setup odrzuca Obsidian (422). Gdyby doszła inna frakcja „non-setup" (np. druga strona
innego kafelka), oznaczymy ją tą samą zdolnością w danych — kod jej nie wymaga zmieniać.

**28.1 Keleres: jedna frakcja, trzy warianty — MAX 1 w grze.** Council Keleres
występuje w danych AsyncTI4 jako trzy osobne, grywalne wpisy (`keleresm`, `keleresx`,
`keleresa`) — to warianty jednego „mentora" tej samej frakcji, dzielące wspólną
`shortName` „Keleres" (patrz nota o rodzinie frakcji w `core/registry.py` →
`faction_family`). Gracz Keleresa wybiera JEDEN wariant, więc w jednej grze może
wystąpić najwyżej jeden przedstawiciel rodziny. Źródło: struktura danych (trzy wpisy
wspólnej `shortName`) + doprecyzowania frakcji w [Council Keleres](rules_tirules/F_keleres.md);
to jedna frakcja, a nie trzy niezależne.

Egzekucja w setupie (`src/core/setup_service.py` → `_resolve_factions`):
- jawny wybór dwóch różnych wariantów Keleres u różnych graczy → `ValueError` (HTTP 422),
  obok istniejącej walidacji duplikatu tego samego `faction_id`;
- losowy dobór („random") bierze najwyżej jednego przedstawiciela z każdej rodziny
  (`_playable_faction_pool` dedupuje po `faction_family`) i pomija rodziny już zajęte
  jawnym wyborem — dzięki temu losowanie nie przydzieli dwóm graczom dwóch wariantów
  Keleres. Testy: `tests/test_setup_factions.py`.

---

## 29. ZMIANA KIERUNKU: silnik-SĘDZIA + okna czasowe (zastępuje "asystent, nie sędzia")

📎 tirules: [Strategic Action](rules_tirules/R_strategic_action.md) · [Strategy Card](rules_tirules/R_strategy_card.md) · [Space Combat](rules_tirules/R_space_combat.md) · [Space Cannon](rules_tirules/R_space_cannon.md) · [Modifiers](rules_tirules/R_modifiers.md) · [Abilities](rules_tirules/R_abilities.md)

**Data decyzji: 2026-10. Ustalenie z użytkownikiem — ŚWIADOMA zmiana filozofii projektu.**

### 29.1. Nowa decyzja projektowa (obala wcześniejsze "asystent stołu, nie sędzia")

Dotychczasowa decyzja (sekcje 19-22, 24, 25, 27 i memory `engine-is-table-assistant-not-referee`)
mówiła: silnik PROWADZI przez kroki i daje pomoce liczbowe, ale NIE waliduje reguł — gracze grają
fizycznie i wprowadzają wynik. **Ta decyzja zostaje ZASTĄPIONA.**

**Nowy kierunek:** silnik EGZEKWUJE reguły TI4 przez kod (jest SĘDZIĄ). Powody (ustalone z użytkownikiem):
1. Docelowy bot AI i tak musi znać i respektować reguły — egzekucja w `core/` to jego "reguły świata".
2. Dla gracza egzekucja jest wygodniejsza (user friendly) — nie musi pamiętać i pilnować legalności.
3. Gra przestaje zakładać, że gracz ma fizycznie rozłożoną planszę.

**God-Mode ZOSTAJE** jako osobny, świadomy kanał ręcznej korekty, który OMIJA walidację (wentyl na
zapomniane/brzegowe przypadki). Zasada: zwykłe akcje (ruch, aktywacja, pick, produkcja, walka)
walidowane TWARDO (nielegalne → `ValueError` → HTTP 422); God-Mode (`/god-mode/patch`, `board_edit.*`)
celowo nie waliduje reguł — to "ręka operatora".

**Tryb gry (ustalony):** solo przeciw botom + hot-seat (wielu ludzi lokalnie), docelowo moduł sieciowy.
Dlatego okna czasowe muszą pytać graczy PO KOLEI (kolejka), a nie zakładać jednego operatora.

**Zakres pierwszego wdrożenia walki (ustalony):** rdzeń najpierw — rzuty kośćmi + liczenie trafień
+ okno "przypisz straty" (obrońca wskazuje, które jednostki giną), wielorundowo. Warianty (anti-fighter
barrage, space cannon offense) dokładane jako KOLEJNE okna czasowe po rdzeniu.

> Sekcje 19-22 pozostają poprawne jako REFERENCJA mechanik TI4 (sekwencja kroków, przejęcie planety,
> statystyki bojowe z UnitDef), ale ich adnotacje "NIE waliduje / asystent, nie sędzia" są UNIEWAŻNIONE
> przez tę sekcję. Przy implementacji każdej z nich walidacja wchodzi do `core/` zgodnie z 29.1.

### 29.2. Model okna czasowego (timing window) — ✅ ZWERYFIKOWANE (LRR "Timing" + AsyncTI4 + potwierdzenie użytkownika 2026-10)

Źródło: LRR 2.0 hasło "Timing of Component Abilities" / "Strategy Phase" (kolejność secondary);
AsyncTI4 `service/strategycard/` (kolejka secondary/follow). Potwierdzone przez użytkownika 2026-10.

**Czym jest okno czasowe:** moment w rozgrywce, w którym JEDEN lub WIELU graczy ma okazję podjąć
decyzję/akcję reaktywną (np. secondary karty strategii, zareagowanie kartą akcji, przypisanie strat
w walce). Okno ma KOLEJKĘ graczy pytanych PO KOLEI i zamyka się, gdy wszyscy odpowiedzieli.

**Kolejność reagowania (POTWIERDZONA):**
- Kolejka zaczyna się od gracza PO AKTYWNYM (po lewej / następny w speaker order) i idzie ZGODNIE
  Z RUCHEM WSKAZÓWEK ZEGARA (speaker order rotowany od gracza po inicjatorze).
- **Secondary kart strategii:** po rozstrzygnięciu primary przez aktywnego gracza, pozostali gracze
  wykonują secondary w tej kolejności; każdy może wykonać secondary ALBO zrezygnować (pas).
- **Reakcje "when/after" (karty akcji, technologie):** modelowane UNIWERSALNIE tym samym mechanizmem —
  kolejka graczy pytanych po kolei w tej samej kolejności.
- **Inicjator okna** jest domyślnie POMIJANY w kolejce (okno dotyczy reakcji pozostałych). Okna, które
  wyjątkowo dotyczą też inicjatora, mogą go dodać jawnie (parametr przy otwarciu okna).

**Model w stanie (plan implementacji — Task 1):** jednolite pole w `GameState` (np. `pending_window`):
typ okna, kolejka `player_id` do zapytania, wskaźnik bieżącego respondenta, kto już odpowiedział,
dane kontekstowe (np. numer karty strategii, pozycja systemu walki). Czyste funkcje w nowym module
`core/timing.py`: `open_window`, `current_responder`, `respond_current`, `advance_window`, `close_window`.
Jedno pojęcie obsługuje: secondary kart strategii, space cannon, przypisanie strat w walce, reakcje.

**Zastosowanie (planowane etapy):**
- Task 3: secondary karty strategii (pierwsze realne okno).
- Task 7/9: okno "przypisz straty", anti-fighter barrage, space cannon offense w walce.
- Przyszłość: reakcje kartami akcji / technologiami (etap E4).

### 29.3. Pojęcie "aktualny gracz / czyja tura" — rozszerzenie

`GameState.active_player_id` (pojedyncza wartość) zostaje jako "czyja tura". Okna czasowe wprowadzają
OBOK niego "kto teraz reaguje" (bieżący respondent okna z 29.2) — to osobny wskaźnik, nie nadpisuje
aktywnego gracza. STATUS/AGENDA przestają zerować aktywnego gracza (Task 4) — dostają właściwą
kolejność (inicjatywa dla statusu, speaker order dla agendy; do potwierdzenia przy tych etapach).

**Status wdrożenia (dziennik):**
- ⬜ Task 1: model okna w stanie + `core/timing.py`.
- ⬜ Task 2: ekspozycja okna w web-data + panel okna w UI.
- ⬜ Task 3: secondary karty strategii.
- ⬜ Task 4: aktualny gracz w STATUS/AGENDA + walidacja flow.
- ⬜ Task 5: ruch jako funkcja core + walidacja (zasięg, anomalie, przejezdność).
- ⬜ Task 6: walidacja aktywacji, przejęcia planety, produkcji.
- ⬜ Task 7: walka — rdzeń (rzuty + trafienia + okno przypisania strat, wielorundowo).
- ⬜ Task 8: interaktywna walka w UI (animacja rzutów).
- ⬜ Task 9: anti-fighter barrage + space cannon offense.
- ⬜ Task 10: aktualizacja dokumentacji (ta sekcja) + memory.

---

## 30. Akcja strategiczna: primary + okno secondary — ✅ ZWERYFIKOWANE (LRR 2.0)

Etap E8-T3. Źródło: lokalny zrzut oficjalnego LRR 2.0 — `docs/rules_tirules/R_strategic_action.md`
oraz `R_leadership.md` (treść © Fantasy Flight Games; patrz `docs/rules_tirules/SOURCE.md`).
Parametry/teksty kart z assetów: `assets/data/strategy_cards/pok.json` (zero z pamięci).

### 30.1. Przebieg akcji strategicznej (R_strategic_action) — ✅ ZWERYFIKOWANE

- W fazie akcji aktywny gracz może wykonać AKCJĘ STRATEGICZNĄ: rozstrzyga PRIMARY swojej
  karty strategii.
- Po rozstrzygnięciu primary KAŻDY INNY gracz, zaczynając OD GRACZA PO LEWEJ aktywnego i dalej
  ZGODNIE Z RUCHEM WSKAZÓWEK ZEGARA, MOŻE rozstrzygnąć SECONDARY tej karty (nie musi — pas).
- Po tym, jak każdy miał okazję na secondary, aktywny gracz WYCZERPUJE (exhaust) kartę
  (odwraca ją — nie użyje jej ponownie w tej rundzie; może odtąd pasować).
- Efekty primary i secondary rozstrzyga się OD GÓRY DO DOŁU (kolejność linii tekstu karty).
- Gra 3-4 osobowa: gracz musi rozstrzygnąć akcję strategiczną KAŻDEJ swojej karty zanim spasuje
  (dotyczy wariantu 2 kart/gracz — na razie wspieramy 1 kartę/gracz, patrz RULES.md 13).

**Mapowanie na model okien czasowych (RULES.md 29.2):** zagranie karty = rozstrzygnięcie primary
(aktywny gracz) + OTWARCIE okna ``STRATEGY_SECONDARY`` z kolejką pozostałych graczy (od gracza po
aktywnym, zgodnie z zegarem — to DOKŁADNIE kolejka z ``timing.build_response_queue``, inicjator
pominięty). Każdy respondent okna wykonuje secondary albo pasuje. Po zamknięciu okna karta jest
wyczerpana.

### 30.2. Leadership — primary i secondary (R_leadership + dane) — ✅ ZWERYFIKOWANE

- **Primary:** aktywny gracz otrzymuje 3 żetony dowodzenia. Następnie MOŻE wydać dowolną ilość
  wpływu, zyskując 1 żeton za każde wydane 3 wpływu.
- **Secondary:** każdy inny gracz (w oknie) MOŻE wydać dowolną ilość wpływu, zyskując 1 żeton za
  każde 3 wpływu. **Secondary Leadership NIE wymaga żetonu strategicznego** (wyjątek — nota LRR;
  większość innych kart wymaga żetonu ze strategy pool).
- Zdobyte żetony gracz kładzie w DOWOLNEJ puli (taktyczna/floty/strategiczna) — wybór gracza.
- Nadwyżka wpływu (1-2 ponad wielokrotność 3) przepada.

**⚠️ ZAKRES T3 (świadomy, „make it exist first"):** implementujemy SZKIELET okna secondary na
realnej karcie:
- Primary Leadership: +3 żetony dowodzenia (do puli taktycznej domyślnie — ⚠️ ZAŁOŻENIE: docelowo
  gracz wybiera pulę; pole do rozbudowy).
- Secondary: mechanika okna (kolejka, wykonaj/pas) działa end-to-end; opcja „wykonaj" na razie
  NIE kupuje żetonów za wpływ (odłożone — wymaga modelu wydawania wpływu / wyczerpywania planet
  jako akcji). Oznaczone TODO w kodzie. Kupno żetonów za wpływ (primary nadwyżka i secondary)
  dojdzie, gdy powstanie model wpływu (powiązać z `exhausted_planets` + wartości influence planet).

**Architektura pod rozbudowę:** rozstrzyganie primary/secondary to osobny, rozszerzalny dispatch
po karcie (``core/strategic_action.py``), nie `if` w endpointcie. Każda kolejna karta = nowa
gałąź dispatchu + wpis reguły tutaj ze źródłem. Model okna niesie kontekst (numer inicjatywy),
więc respond potrafi rozstrzygnąć właściwy secondary bez zmiany kształtu okna.

**Status wdrożenia:**
- ⬜→✅ T3: Leadership primary (+3 żetony) + okno secondary (szkielet, wykonaj/pas).
- ⬜ Pozostałe karty (Diplomacy, Politics, Construction, Trade, Warfare, Technology, Imperial) —
  primary/secondary dokładane kolejno, każda z notą tutaj.
- ⬜ Model wpływu (wydawanie / wyczerpywanie planet) — odblokuje realne kupno żetonów i inne secondary.

---

## 31. Walidacja przepływu fazy akcji + aktywny gracz (twarda egzekucja) — ✅ ZWERYFIKOWANE (LRR 2.0)

Etap E8-T4. Źródło: lokalny LRR 2.0 — `docs/rules_tirules/R_active_player.md`,
`R_action_phase.md`, `R_initiative_order.md`, `R_status_phase.md`, `R_agenda_phase.md`
(treść © FFG; patrz SOURCE.md). Pierwszy element „sędziego" (RULES.md 29.1): zwykłe akcje
flow walidowane TWARDO; God-Mode omija.

### 31.1. Aktywny gracz wg LRR vs DECYZJA PROJEKTOWA — ⚠️ ODEJŚCIE OD ŹRÓDŁA (patrz 31.4)

- Reguła źródłowa (R_active_player): „The active player is the player taking a turn during
  the action phase." Oraz w notach wprost: „During the strategy, status and agenda phases,
  no player is the active player."
- **Decyzja projektowa (2026-11, ustalona z użytkownikiem — KORYGUJE wcześniejszy zamysł
  T4, patrz 31.4):** silnik ŚWIADOMIE odchodzi od „no active player". W TOCZĄCEJ SIĘ partii
  (≥2 graczy) `active_player_id` jest ZAWSZE ustawiony — także w STRATEGY, STATUS i AGENDA —
  nigdy `None`. Powód: UI i bot AI zawsze potrzebują wskazanego gracza, a koniec tury/fazy
  ma być TRANZYCJĄ (ogłaszaną przez mówcę), nie stanem „niczyjej tury". `None` pozostaje
  LEGALNY wyłącznie jako stan „gra nie ruszyła / <2 graczy / God-Mode buduje stół".
- Kolejność czynności w STATUS/AGENDA to nadal KOLEJKA wg inicjatywy/speaker order (31.3);
  „aktywny gracz" w tych fazach jest tylko WSKAŹNIKIEM „czyja teraz kolej", nie zmienia reguł.

### 31.2. Walidacja przepływu fazy akcji — ✅ ZWERYFIKOWANE

Reguły (R_action_phase, R_active_player):
- Gracze wykonują tury w INITIATIVE ORDER (najniższy numer karty pierwszy — RULES.md 9).
- Turę kończy/pasuje bieżący AKTYWNY gracz — nie dowolny.
- Po spasowaniu gracz nie ma kolejnych tur (pomijany do końca fazy akcji).
- **Gracz NIE MOŻE spasować, dopóki nie wykona akcji strategicznej swojej karty** (zagranie
  karty = exhaust, RULES.md 30). (Wariant 3-4 graczy: obu kart — na razie 1 karta/gracz.)
- Po spasowaniu wszystkich → faza statusu.

**Egzekucja w kodzie (twarda, `ValueError` → HTTP 422):**
- `end_turn(state, player_id=...)` / `pass_turn(state, player_id=...)`:
  - faza musi być ACTION (inaczej błąd — w innych fazach nie ma tury do zakończenia);
  - `player_id`, jeśli podany, musi być równy `active_player_id` (nie cudza tura);
  - `pass_turn` dodatkowo: gracz musi mieć zagraną kartę strategii (`exhausted_strategy_cards`
    niepuste), inaczej „nie możesz spasować przed akcją strategiczną".
- Wywołanie BEZ `player_id` (legacy/God-Mode-ish) zachowuje się jak dotąd (dla zgodności —
  ale endpointy przekazują `player_id` z żądania, więc realnie walidują).
- **God-Mode** (`/god-mode/patch`, `board_edit`) omija — operator może ustawić cokolwiek.

### 31.3. Kolejność w STATUS/AGENDA = kolejka, nie „tura" — ✅ ZWERYFIKOWANE

- **Status**: kroki w INITIATIVE ORDER (R_status_phase). Punktowanie/akcje per gracz w kolejności
  inicjatywy.
- **Agenda (głosowanie)**: „starting with the player to the left of the speaker and continuing
  clockwise" (R_agenda_phase) — czyli SPEAKER ORDER od gracza po mówcy. To ta sama mechanika,
  co kolejka okna czasowego (RULES.md 29.2, `timing.build_response_queue` z inicjatorem = mówca).
- **Wniosek dla kodu:** gdy dojdą realne kroki statusu/agendy (osobne etapy), użyją KOLEJKI
  (initiative albo speaker order). `turn_flow` dostarcza `initiative_order` (= `turn_order`)
  jako kolejność dla statusu. Od decyzji 31.4 `active_player_id` w STATUS/AGENDA wskazuje
  pierwszego gracza tej kolejki (nie `None`), ale rozstrzyganie kroków i tak pójdzie przez
  kolejkę — wskaźnik „aktywnego" nie zmienia reguł.

### 31.4. ZASADA „zawsze czyjaś tura" + mówca ogłasza tranzycję — ⚠️ DECYZJA PROJEKTOWA (2026-11)

Ustalono z użytkownikiem. Fundament pod docelowo do 6 ludzkich graczy (hot-seat / sieć) i
bota AI: w każdej chwili toczącej się partii musi być jasne, CZYJA jest tura.

**(1) `active_player_id` nigdy `None` w toczącej się partii (≥2 graczy):**
- STRATEGY: aktywny = bieżący picker; po komplecie wyborów = MÓWCA (czeka na ogłoszenie).
- ACTION: aktywny = gracz wg inicjatywy; gdy ostatni spasuje = MÓWCA (faza wciąż ACTION,
  bez auto-przejścia — zostają okna czasowe „end of turn"/„end of action phase").
- STATUS/AGENDA: aktywny = pierwszy gracz w initiative order (odejście od LRR — 31.1).
- `None` TYLKO poza rozgrywką: 0–1 graczy, pusty setup, God-Mode budujący stół. `pick_count`
  nie obsługuje <2 graczy, więc `next_strategy_picker` zwraca tam `None`; kod robi fallback na
  `speaker_id`, który też bywa `None` w pustej grze — i to jedyny dozwolony `None`.

**(2) Brak auto-tranzycji; przejście fazy OGŁASZA MÓWCA:**
- Spasowanie/koniec tury ostatniego gracza NIE przełącza fazy automatycznie — przy końcu tury
  i fazy jest wiele okien czasowych, których auto-przejście by nie uruchomiło.
- Fazę zmienia `/phase/next`, egzekwowane jako akcja mówcy: gdy żądanie podaje `player_id`,
  musi być równy `speaker_id` (inaczej HTTP 422). God-Mode (`/god-mode/patch`) omija.

**Egzekucja w kodzie:**
- `turn_flow.end_turn`/`pass_turn`: gdy brak następnego niespasowanego → `active_player_id =
  speaker_id` (faza nadal ACTION), zamiast `None`+STATUS.
- `turn_flow.next_phase`: ACTION → initiative[0]; STRATEGY → picker ∥ speaker; STATUS/AGENDA →
  initiative[0] ∥ speaker. `next_round`, `strategy_phase.pick_strategy_card`/
  `reset_strategy_cards`: picker ∥ speaker.
- `api/routers/flow.post_next_phase`: walidacja „to mówca" (opcjonalny `player_id`).

**Status wdrożenia:**
- ✅ Zasada „zawsze czyjaś tura" + fallback na mówcę we wszystkich funkcjach flow/strategii.
- ✅ Walidacja mówcy w `/phase/next`; walidacja end_turn/pass_turn (faza, aktywny gracz, pas
  dopiero po akcji strategicznej); God-Mode omija.
- ⬜ Realne kroki statusu (punktowanie, odświeżanie) — etap E5, użyją initiative order (kolejka).
- ⬜ Realne głosowanie agendy — etap E6, użyje speaker order (kolejka jak okno czasowe).

### 31.5. Pas jako akcja + jedna flaga „skończył fazę" + brama „Next phase" — ⚠️ DECYZJA PROJEKTOWA (2026-11)

Ustalono z użytkownikiem. Standaryzuje sterowanie przepływem w UI i odpowiadającą mu
semantykę w silniku, spójnie dla wszystkich faz.

**(1) Pas jest „jak akcja", nie zakończeniem tury (faza AKCJI):**
- `turn_flow.pass_turn` oznacza aktywnego gracza `passed=True`, ale NIE oddaje tury —
  `active_player_id` pozostaje bez zmian. Turę oddaje się JEDNYM, spójnym klikiem
  `end_turn` (również PO pasie). Dzięki temu każda tura kończy się tak samo, niezależnie
  od tego, czy był to zwykły ruch, czy pas. `end_turn` pomija już spasowanych
  (`next_unpassed_player`).
- Bramka „pas dopiero po akcji strategicznej" (R_action_phase) bez zmian.

**(2) Jedna flaga `passed` = „gracz skończył swoją część TEJ fazy":**
- Flaga `PlayerState.passed` jest RESETOWANA przy KAŻDYM wejściu w nową fazę
  (`turn_flow.next_phase`). Niesie: pas w AKCJI, krok w STATUSIE (R31.3), reakcję/głos
  w AGENDZIE.
- STATUS „Next player" i AGENDA „Pass" wołają `advance_active_player(mark_passed=True)`
  (`/turn/phase-step`) — oznaczają gracza i przesuwają wskaźnik. AGENDA „Next player"
  woła `advance_active_player()` bez oznaczania (`/turn/next-player`) — tylko przewija.

**(3) „Next phase" (mówca) widoczny dopiero po komplecie:**
- `turn_flow.can_advance_phase`: STRATEGY — po `ensure_strategy_complete`; ACTION/STATUS —
  gdy `all_passed` (wszyscy skończyli swoją część); AGENDA — zawsze (kolejne głosowania
  modelujemy oknami, nie tą bramą).
- Projekcja do UI przez pola web-data `canAdvancePhase` + `allPassed`. Twarda walidacja
  także w `api/routers/flow.post_next_phase` (czytelny 422, gdy mówca próbuje za wcześnie).

**(4) Panel komunikatów (UI) = TYLKO niedozwolone akcje:**
- Osobny box przypięty u GÓRY ekranu (`frontend/.../PhaseNoticePanel`). Pokazuje
  WYŁĄCZNIE komunikaty o odrzuconych akcjach (422 → `notice` w appStore): np. „Next
  phase" w strategii zanim wszyscy wybiorą, „Pass" zanim zagrasz kartę strategii.
  Pojawia się na zdarzenie i ZNIKA Z FADE-OUT (auto po ~6 s albo krzyżyk). NIE jest
  stałym przypomnieniem ani nie ogłasza zmian faz. Zastępuje dawny `NoticeBanner`.

**(5) „Next phase" widoczny zawsze dla mówcy; brama egzekwowana przez 422:**
- Zamiast ukrywać przycisk do czasu kompletu, mówca ZAWSZE widzi „Next phase" w
  głównych fazach. Gdy przejście nie jest dozwolone (strategia: nie wszyscy wybrali;
  akcja/status: nie wszyscy spasowali/zrobili krok), klik zwraca 422 z czytelnym
  komunikatem, który pokazuje panel. Twarda walidacja: `can_advance_phase` +
  `/phase/next`. Pola web-data `canAdvancePhase`/`allPassed` zostają (diagnostyka/bot).

**(6) Przyciski flow wołają backend BEZ `player_id`:**
- UI wysyła `/turn/pass`, `/turn/end`, `/turn/phase-step`, `/turn/next-player` bez
  `player_id` — backend adresuje własny `active_player_id`. Powód: „gracz pulpitu"
  (`useDeskPlayer`) bywa fallbackiem na mówcę i rozjeżdżał się z realnym aktywnym
  graczem (status „Next player" wysyłał zły id → 422 → „klik nic nie robił").

**Egzekucja w kodzie:**
- `turn_flow`: `pass_turn` (tylko flaga), `end_turn` (jedyne oddanie tury), `all_passed`,
  `can_advance_phase`, `advance_active_player(mark_passed=…)`, reset flag w `next_phase`.
- `api/routers/flow`: `/turn/pass`, `/turn/end`, `/turn/phase-step` (nowy), `/turn/next-player`,
  brama w `/phase/next`.
- `api/web_data`: pola `canAdvancePhase`, `allPassed`.
- Frontend: `TurnControls`, `GameStatePanel.PhaseControls` (przyciski per faza + brama),
  `PhaseNoticePanel` (+ `phaseNoticeMessage`), hook `useBoardEditor.phaseStep`.

### 31.6. End turn zablokowany, dopóki trwa okno czasowe — ✅ ZWERYFIKOWANE (R_strategic_action) + ⚠️ DECYZJA UI (2026-11)

📎 tirules: [Strategic Action](rules_tirules/R_strategic_action.md)

Ustalono z użytkownikiem. Wiąże secondary kart strategii (okno 29.2) z zakończeniem tury:
aktywny gracz, który ZAGRAŁ kartę strategii, może dać „End turn" DOPIERO gdy wszyscy inni
gracze zdecydowali o secondary („follow"/„don't follow").

**Reguła źródłowa (R_strategic_action):** po rozstrzygnięciu PRIMARY przez aktywnego gracza
każdy inny gracz — „beginning with the player to the left of the active player and proceeding
clockwise" — MA OKAZJĘ („may resolve") na secondary (follow jest dobrowolny). Dopiero „after
each player has had an opportunity to resolve a strategy card's secondary ability" aktywny
gracz wyczerpuje kartę i kontynuuje. Czyli: nie można zakończyć tury „w środku" okna.

**Egzekucja (sędzia):**
- `turn_flow.end_turn` rzuca `ValueError`, gdy `state.pending_window is not None`
  („Nie można zakończyć tury, gdy trwa okno czasowe…") → HTTP 422. Blokada dotyczy KAŻDEGO
  typu okna (secondary, przypisanie strat, space cannon, reakcja), nie tylko secondary —
  turę oddaje się tylko „między" oknami.
- Okno secondary otwiera `strategic_action.play_strategy_card` (kolejka od gracza po aktywnym,
  zegarowo — `timing.build_response_queue`), a każdy respondent odpowiada przez
  `/strategy/secondary` (`execute=True` = follow, `execute=False` = don't follow). Po
  odpowiedzi ostatniego kolejka się dopełnia i okno zamyka się samo (`resolve_secondary`).
  Wtedy dopiero `end_turn` przechodzi.
- God-Mode (`/god-mode/patch`) i tu omija — operator może domknąć/skasować okno ręcznie.

**UI (język planszówki + popup):**
- Decyzja secondary nazwana „Follow" / „Don't follow" (potoczny termin planszówkowy TI4;
  „follow the strategy card"). W silniku to wciąż `execute` true/false.
- Pytanie do bieżącego respondenta pokazuje MODAL (popup) na środku ekranu —
  `SecondaryDecisionModal` — a nie tylko panel boczny. Modal adresuje respondenta po
  `currentResponderId`; po decyzji kolejka przechodzi do następnego gracza (nowy modal).
- „End turn" (oba miejsca: `TurnControls` i `GameStatePanel.PhaseControls`) jest WYGASZONY
  i zablokowany, dopóki `pendingWindow` ≠ null, z tooltipem wyjaśniającym (czekamy aż
  wszyscy zdecydują o secondary). Twarda walidacja i tak siedzi w `end_turn` (422).
- ZAKRES: modal daje tylko WYBÓR follow/don't follow i przesuwa kolejkę — CO dokładnie
  robi „follow" (efekt liczbowy secondary) jest poza zakresem tego kroku (dispatch efektów
  w `strategic_action` dojdzie kartą po karcie, patrz RULES.md 30).

### 31.7. End turn wymaga AKCJI albo PASU — ✅ ZWERYFIKOWANE (R_action_phase)

📎 tirules: [Action Phase](rules_tirules/R_action_phase.md)

Ustalono z użytkownikiem. Gracz nie może oddać tury „bez niczego": w swojej turze fazy
akcji musi wykonać JEDNĄ akcję albo spasować, i dopiero wtedy odda turę.

**Reguła źródłowa (R_action_phase):** „During a player's turn, they perform a **single
action**" — jedna z trzech: akcja strategiczna, taktyczna albo komponentu. „If a player
cannot perform an action, they must pass." Czyli tura = akcja XOR pas; nie ma „pustej" tury.

**Model (``PlayerState.took_action_this_turn``):** flaga „gracz wykonał akcję w BIEŻĄCEJ
turze". Ustawiana na `True` przez:
- akcję strategiczną — `strategic_action.play_strategy_card` (ZAGRANIE KARTY STRATEGII
  liczy się jako akcja);
- akcję taktyczną — `tactical.activate_system` (aktywacja systemu rozpoczyna akcję);
- (akcja komponentu — gdy dojdzie jej endpoint, ustawi tę samą flagę).
RESETOWANA przy każdym przekazaniu tury (`end_turn` zeruje ją następnemu graczowi) i przy
wejściu w fazę akcji (`next_phase`) — bo dotyczy POJEDYNCZEJ tury, nie całej fazy.

**Egzekucja (sędzia):**
- `turn_flow.end_turn` rzuca `ValueError` („You must take an action … or pass before ending
  your turn.") → HTTP 422, gdy aktywny gracz NIE ma `took_action_this_turn` ANI `passed`.
- `turn_flow.pass_turn` rzuca `ValueError` („You already took an action this turn - end your
  turn instead of passing."), gdy gracz w TEJ turze już wykonał akcję. Pas jest ALTERNATYWĄ
  dla akcji w danej turze, nie dodatkiem po niej (R_action_phase: „perform a single action …
  or pass"). Czyli po zagraniu karty / aktywacji systemu jedyne wyjście to `end_turn`.
- Pas (`pass_turn`) jest osobną, dozwoloną ścieżką zakończenia tury (RULES.md 31.5): po pasie
  End turn przechodzi mimo braku „akcji" (pas JEST zakończeniem aktywności w rundzie).
- PUSTE OKNO secondary: gdy kolejka respondentów jest pusta (gra solo / brak innych graczy),
  `strategic_action.play_strategy_card` NIE otwiera okna — inaczej `pending_window` zostawałby
  ustawiony (okno „zakończone", ale nikt go nie zamyka) i blokował End turn na stałe.
- God-Mode omija (operator może oddać turę ręcznie).

**UI (web-data + panele):** `playerData[].tookActionThisTurn` niesie flagę do frontu. „End
turn" jest aktywny dopiero, gdy `tookActionThisTurn || passed` i nie trwa okno; wcześniej
jest SZARY (wyłączony) z podpowiedzią „Take an action or pass, then End turn." Po akcji/pasie
przycisk pulsuje (nudge) + drobna informacja, że trzeba jeszcze oddać turę. Przycisk „Pass"
jest WYŁĄCZONY, gdy gracz już wykonał akcję w tej turze (`tookActionThisTurn`) — z tooltipem
„You already acted this turn — End turn instead".

### 31.8. Akcja komponentu — trzeci typ akcji fazy akcji — ✅ ZWERYFIKOWANE (R_component_action)

📎 tirules: [Component Action](rules_tirules/R_component_action.md) · [Action Phase](rules_tirules/R_action_phase.md)

**Reguła źródłowa (R_component_action):** akcja komponentu to typ akcji wykonywany w swojej
turze fazy akcji. Jest oznaczona nagłówkiem „**Action**" na komponencie — karcie akcji,
technologii, liderze, relikcie, karcie eksploracji, promissory note albo arkuszu frakcji.
„To perform a component action, a player reads the action's text and follows the instructions."
Akcja komponentu NIE może być wykonana, jeśli jej efektu nie da się w pełni rozstrzygnąć; jeśli
zostanie anulowana, NIE zużywa akcji gracza. Karta akcji BEZ nagłówka „Action" nie jest akcją
komponentu (R_action_cards). To jedna z trzech akcji tury (RULES.md 31.7): akcja = strategiczna
XOR taktyczna XOR komponentu, albo pas.

**Model (`core/component_action.play_component_action`):** CZYSTA funkcja `state -> state`.
ZAKRES (świadomy szkielet, „make it exist first"): rejestruje, że gracz wykonał akcję komponentu
w tej turze (`took_action_this_turn = True`, jak akcja strategiczna/taktyczna) — i nic więcej.
Efekt KONKRETNEGO komponentu NIE jest wykonywany; dojdzie dispatchem po `component_id`,
komponent po komponencie, z osobnym wpisem reguły/źródłem. `component_id` jest na razie wyłącznie
ADNOTACJĄ „co zagrano" (trafia do etykiety eventu), opcjonalną — bo akcja bywa też z reliktu/
techu/zdolności, nie tylko z karty.

**Egzekucja (sędzia):** `play_component_action` rzuca `ValueError` → HTTP 422, gdy: faza ≠ ACTION;
brak aktywnego gracza; `player_id` ≠ aktywny gracz; trwa otwarte okno (`pending_window`); gracz
już wykonał akcję w tej turze (`took_action_this_turn` — jedna akcja na turę); gracz spasował
(`passed` — po pasie nie wykonuje już akcji w tej fazie, R_action_phase). Po sukcesie `End turn`
jest dostępny (ta sama ścieżka co po akcji strategicznej/taktycznej). Endpoint:
`POST /tactical/component-action` (`ComponentActionRequest{player_id?, component_id?}`).

**UI (`TurnControls`):** w fazie akcji, obok Pass/End turn, przycisk „**Component action**"
(ikona iskry, fioletowy akcent ability). Klik otwiera modal „co zagrałeś?" z listą WSZYSTKICH
komponentów z nagłówkiem „Action" dostępnych aktywnemu graczowi — zebranych z danych, bez
hardkodowania (`componentActions.collectComponentActions`): karty akcji z ręki (`window`
„Action"), zdolności frakcji (`getAbilityKind === "action"`), liderzy (`abilityWindow`/
`abilityText` od „ACTION"), technologie i relikty (`text` z nagłówkiem „ACTION"). Lista czyta to,
co gracz REALNIE posiada (web-data `playerData[]`: `abilities`/`leaderIDs`/`techs`/`relics` +
ręka). Na końcu zawsze opcja „Something else" (eksploracja / promissory / nieśledzone źródło).
Wybór to tylko adnotacja (`component_id`); efekt = oznaczenie akcji wykonanej. Przycisk WYŁĄCZONY,
gdy gracz już działał / spasował / trwa okno (spójnie z Pass).

---

## 32. Ruch statków: egzekucja legalności (akcja taktyczna) — ✅ ZWERYFIKOWANE (LRR 2.0)

Etap E8-T5. Źródło: lokalny LRR 2.0 — `docs/rules_tirules/R_movement.md`, `R_tactical_action.md`
(treść © FFG; patrz SOURCE.md). Uzupełnia szkic z RULES.md 3 (ten był „DO ZROBIENIA") i
anomalie z RULES.md 1. Ruch przestaje być tylko God-Mode — staje się WALIDOWANĄ akcją (RULES.md 29.1).

### 32.1. Reguły ruchu (R_movement, krok „Move Ships") — ✅ ZWERYFIKOWANE

Statek rusza do AKTYWNEGO systemu (akcja taktyczna, krok 2), przestrzegając:
- **(R1) Cel = aktywny system.** Statek musi ZAKOŃCZYĆ ruch w aktywnym systemie
  (``GameState.active_system``). Ruch poza akcją taktyczną (bez aktywnego systemu) jest nielegalny
  w tej ścieżce (ruch zdolnościami to osobna sprawa — nie T5).
- **(R2) Zasięg.** Liczba systemów, w które statek WCHODZI (długość trasy po sąsiednich systemach),
  nie przekracza jego ``moveValue``. UWAGA: ``moveValue`` bierzemy z WARIANTU jednostki GRACZA
  (uwzględnia ulepszenia wg posiadanych technologii — ``combat.resolve_unit_variant``), nie z
  bazowego wpisu. Przykład: bazowy **Fighter** ma ``moveValue=None`` (porusza się wyłącznie
  transportem przez capacity), ale **Fighter II** (technologia ``ff2``) ma ``moveValue=2`` i
  może ruszać się samodzielnie. Jednostki o ``moveValue=None`` w aktualnym wariancie NIE ruszają
  się tą ścieżką (ruszą przez transport — TODO capacity).
- **(R3) Start nie z własnym CC.** Statek NIE może ruszyć, jeśli startuje w systemie z własnym
  żetonem dowodzenia (``SystemState.command_tokens`` zawiera gracza) — WYJĄTEK: aktywny system
  (można „wyjść i wrócić"). Źródło + nota R_movement.
- **(R4) Nie przez obce statki.** Trasa NIE może przechodzić przez system zawierający statki INNEGO
  gracza (nawet same myśliwce blokują — nota R_movement). Węzły POŚREDNIE muszą być wolne od
  obcych statków. Cel (aktywny system) może mieć obce statki (tam dojdzie do walki — krok 3).
- **(R5) Przez własne CC można.** Trasa MOŻE przechodzić przez systemy z WŁASNYM żetonem gracza.
- **(R6) Anomalie / przejezdność.** Supernova bezwarunkowo nieprzejezdna (nie wchodzi do trasy —
  RULES.md 1.3). Asteroid field nieprzejezdny bez technologii Antimass Deflectors (RULES.md 1.1).
  Nebula: wejście tylko gdy to system aktywny (RULES.md 1.2) — tu egzekwujemy warunek wejścia do
  węzłów pośrednich (nebula pośrednia zablokowana). Trasa idzie po krawędziach SĄSIEDZTWA grafu
  (geometria + wormhole — RULES.md 2).

**⚠️ ZAKRES T5 (świadomy szkielet, „make it exist first"):**
- Walidujemy i wykonujemy ruch POJEDYNCZEGO stosu jednego typu statku z systemu źródłowego do
  aktywnego (``move_ships(state, grid, registry, from_pos, base_type, count, player_id)``).
  Wiele źródeł/typów = wiele wywołań (lub God-Mode). Deklaracja „wszystkie naraz" i jednoczesność
  to warstwa UI/orkiestracji — do rozbudowy.
- Transport sił naziemnych/myśliwców przez ``capacityValue`` — ⬜ TODO (osobny krok; na razie
  ruszamy tylko statki, capacity nie liczony). Oznaczone w kodzie.
- Antimass Deflectors: sprawdzamy posiadanie technologii gracza (``PlayerState.technologies``);
  alias technologii z danych (nie z pamięci). Gdy brak — asteroid nieprzejezdny.
- Pathfinding: najkrótsza legalna trasa (BFS po grafie z filtrem węzłów pośrednich). Jeśli istnieje
  trasa o długości ≤ moveValue spełniająca R4/R6 — ruch legalny. (Gracz nie wybiera trasy ręcznie
  w T5 — silnik sprawdza istnienie legalnej; wybór trasy pod efekty gravity rift itp. = rozbudowa.)

### 32.2. Model i implementacja

- `core/movement.py` (NOWY): `legal_move_destinations`/`can_move` (walidacja) + `move_ships`
  (wykonanie: przenosi ``count`` statków ``base_type`` ze źródła do aktywnego systemu; mutuje
  ``space_units``). Czyste funkcje ``state -> state``.
- Walidacja twarda: złamanie R1–R6 → ``ValueError`` → HTTP 422. God-Mode (``board_edit.move_units``)
  NADAL omija (osobny kanał, bez reguł — RULES.md 25/26).
- Endpoint: `POST /tactical/move` (router tactical). UI podłączy w kroku ruchu (MOVEMENT).

**Status:** ✅ T5 ruch statków z walidacją R1–R6 (pojedynczy stos). ⬜ wybór trasy pod
gravity rift, ⬜ ruch zdolnościami — rozbudowa. (Transport/capacity → 32.3 niżej.)

### 32.3. Transport (capacity) — ✅ ZWERYFIKOWANE (LRR 2.0 / tirules)

Etap E8 Blok B. Źródło: `docs/rules_tirules/R_transport.md`, `R_capacity.md` (treść © FFG;
patrz SOURCE.md). Domyka ruch o przewożenie myśliwców i sił naziemnych przez statki.

- **(T1) Capacity = limit ładunku statku.** Statek może przewieźć dowolną kombinację
  myśliwców i sił naziemnych, pod warunkiem że łączna liczba przewożonych jednostek nie
  przekracza jego wartości `capacityValue` (z WARIANTU gracza — ulepszenia liczą się, np.
  Carrier/upgrade). Każdy myśliwiec/piechota/mech zajmuje `capacityUsed` (zwykle 1).
- **(T2) Ładunek rusza razem ze statkiem** i pozostaje w PRZESTRZENI systemu docelowego
  (nie ląduje — lądowanie to krok INWAZJA). Myśliwce są statkami (`space`), ale bez własnego
  `moveValue` ruszają się wyłącznie jako ładunek (chyba że Fighter II — wtedy mają własny ruch).
  Siły naziemne (piechota/mech) w trakcie transportu są w przestrzeni jako „ładunek na statku".
- **(T3) Skąd pickup (akcja taktyczna).** Ładunek można zabrać z systemu źródłowego statku:
  z PRZESTRZENI oraz z PLANET tego systemu (źródło: R_transport „from the active system, the
  system it started its movement in, and each system it moves through"; „A ship may pick up
  ground forces from a planet"). Siły naziemne zdjęte z planety jadą w przestrzeni jako ładunek
  i lądują dopiero w Commit Ground Forces. Pickup z systemów MIJANYCH po drodze = rozbudowa.
- **(T4) Blokada CC przy pickup.** Nie wolno zabierać myśliwców/sił naziemnych z systemu,
  który zawiera WŁASNY żeton dowodzenia gracza (wyjątek: aktywny system).
- **(T5) Limit capacity w systemie.** Łączna `capacityValue` statków gracza w systemie
  ogranicza liczbę myśliwców + sił naziemnych, jakie gracz może mieć w przestrzeni tego
  systemu. Nadwyżkę trzeba usunąć (gracz wybiera). W Bloku B egzekwujemy to jako walidację
  ruchu: ładunek ≤ wolna capacity statków RUSZAJĄCYCH w tym ruchu.

**Model/implementacja:** `core/movement.py` — nowa funkcja `move_fleet(state, grid, registry,
from_pos, ships, cargo, player_id)` (ships/cargo = `{base_type: count}`): waliduje każdy statek
przez `can_move` (R1–R6), liczy wolną capacity (suma `capacityValue` wariantów statków − suma
`capacityUsed` ładunku) i przenosi statki + ładunek do aktywnego systemu w `space_units`.
`move_ships` zostaje jako cienki wrapper (jeden typ statku, bez ładunku — zgodność wsteczna).
Endpoint `POST /tactical/move` dostaje opcjonalne pole `cargo`. Złamanie reguły → `ValueError`
→ 422. God-Mode (`/units/move`) nadal omija.

**Status:** ✅ transport z przestrzeni ORAZ z planet systemu źródłowego (ships + cargo z
``from_zone``, limit capacity). ⬜ pickup z systemów mijanych, ⬜ usuwanie nadwyżki capacity
poza ruchem — rozbudowa.

---

## 33. Walidacja aktywacji i produkcji (twarda egzekucja) — ✅ ZWERYFIKOWANE (LRR 2.0)

Etap E8-T6. Źródło: lokalny LRR 2.0 — `docs/rules_tirules/R_active_system.md`,
`R_production.md`, `R_producing_units.md` (treść © FFG; patrz SOURCE.md). Domyka egzekucję
fazy akcji poza walką (RULES.md 29.1). Dane liczbowe (koszt, produkcja) z UnitDef/rejestru.

### 33.1. Aktywacja systemu (R_active_system) — ✅ ZWERYFIKOWANE

- Gracz NIE może aktywować systemu, w którym leży już JEGO WŁASNY żeton dowodzenia.
- Gracz MOŻE aktywować system z żetonami INNYCH graczy.
- Aktywacja kładzie żeton z puli TAKTYCZNEJ (`PlayerState.tactical_cc`) — potrzebny ≥1 żeton.

**Egzekucja (twarda, ValueError → 422):** `tactical.activate_system` sprawdza:
- jest aktywny gracz (było);
- gracz ma ≥1 żeton w puli taktycznej (było: tylko dekrementacja „jeśli >0", teraz TWARDO);
- system NIE zawiera już własnego żetonu gracza (nowe).
God-Mode (`board_edit.place_command_token`) nadal omija (korekta bez zużycia puli).

### 33.2. Produkcja: koszt i limit (R_production, R_producing_units) — ✅ ZWERYFIKOWANE

- **Koszt (R_producing_units):** by wyprodukować jednostkę, gracz wydaje zasoby ≥ jej koszt.
  Zasoby pochodzą z planet (wyczerpanie) i trade goods gracza. Nadwyżka przepada. Przy wielu
  jednostkach koszty się sumują.
- **Produkcja podwójna:** fighter/infantry = 2 sztuki za jeden koszt; można wyprodukować 1, ale
  płaci się pełny koszt. Każda sztuka liczy do LIMITU.
- **Limit produkcji (R_production):** gracz może wyprodukować liczbę jednostek ≤ sumie wartości
  `Production` swoich jednostek w aktywnym systemie (doki/jednostki z PRODUCTION). Fighter/infantry
  liczą po sztuce do limitu.
- **Blokada statków (R_producing_units):** nie wolno produkować STATKÓW w systemie z obcymi
  statkami; siły naziemne można.

**⚠️ ZAKRES T6 (świadomy szkielet — opcja „b", ustalona z użytkownikiem):**
- **Koszt: egzekwujemy SPRAWDZENIE, bez realnego wydawania.** Silnik liczy dostępny budżet
  (suma `resources` planet GOTOWYCH gracza + `trade_goods`) i ODRZUCA zamówienie produkcji
  przekraczające budżet. NIE wyczerpuje planet ani nie zdejmuje TG — realne wydawanie dojdzie
  z modelem wpływu (ten sam, który odblokuje secondary Leadership z T3). Oznaczone TODO.
- **Limit produkcji: egzekwujemy TWARDO** — suma wartości PRODUCTION jednostek gracza w aktywnym
  systemie (z UnitDef — `production_value`). Fighter/infantry po sztuce.
- **Blokada statków: egzekwujemy TWARDO** — statki odrzucone, gdy w aktywnym systemie stoją obce
  statki; siły naziemne/struktury dozwolone.
- Umiejscowienie (statek→przestrzeń, naziemne→planeta) już egzekwowane przy stawianiu (RULES.md 26);
  tu dochodzi budżet + limit + blokada. Wybór konkretnych planet pod naziemne = jak dotąd (God-Mode
  edit stawia; auto-kontrola RULES.md 23).
- Realne wyczerpywanie planet/TG + „usuń z planszy by dostawić z rezerwy" (component limitations) =
  TODO (rozbudowa z modelem wpływu i rezerw).

**Model i implementacja:**
- `core/production.py` (NOWY): `production_limit(state, grid, registry, player_id)` (suma PRODUCTION
  w aktywnym systemie), `available_budget(state, registry, player_id)` (gotowe planety + TG),
  `validate_production(...)` (koszt ≤ budżet, liczba ≤ limit, blokada statków) → `ValueError`.
  Wołane przez endpoint produkcji PRZED postawieniem jednostek (God-Mode edit zostaje jako wykonanie).
- Czyste funkcje. God-Mode (`/system/{pos}/edit-units`) NADAL omija (wentyl bez reguł).

**Status:** ✅ T6 aktywacja (własny CC + pula) + produkcja (budżet-check, limit, blokada statków).
Realne wydawanie i rezerwy — patrz 33.3 (✅ zrobione, z jednym wyjątkiem opisanym niżej).

### 33.3. Krok PRODUCTION domknięty: płatność, wspólny limit, strefy, rezerwa — ✅ ZWERYFIKOWANE

📎 tirules: [Production](rules_tirules/R_production.md) · [Producing Units](rules_tirules/R_producing_units.md) · [Cost](rules_tirules/R_cost.md) · [Component Limitations](rules_tirules/R_component_limitations.md) · [Blockaded](rules_tirules/R_blockaded.md)

Zastępuje „opcję b" z 33.2. `core/production.produce(...)` (endpoint `POST /tactical/produce`):
- **Płatność REALNA:** wybrane planety są wyczerpywane (`exhausted_planets`), TG schodzą z puli;
  planety muszą być kontrolowane i gotowe; zapłata ≥ koszt, nadwyżka przepada. Pominięte `spend`
  → `auto_pay` (planety od największych, zbędne zdejmowane, TG tylko na resztę — dla bota).
- **Koszt pary:** dane AsyncTI4 trzymają koszt PER SZTUKA (fighter/infantry = 0.5); karta mówi „1
  za dwie". Para = 2 × koszt sztuki, N sztuk = ⌈N/2⌉ par, liczone łącznie dla typu (piechota na dwóch
  planetach to nadal jedna para). Poprzedni kod pobierał pół ceny — naprawione.
- **Limit WSPÓLNY dla akcji:** `GameState.production_used` (zerowane przy aktywacji/końcu akcji);
  kolejne zamówienia w tym samym kroku liczą się do tego samego limitu PRODUCTION.
- **Strefy (R_production):** statki → tylko przestrzeń aktywnego systemu. Siły naziemne → planety z
  jednostką PRODUCTION (dok); gdy produkuje jednostka w przestrzeni — także każda planeta gracza w
  systemie albo sama przestrzeń (`allowed_ground_zones`).
- **Rezerwa (R_component_limitations):** typy poza fighter/infantry ograniczone plastikiem
  (`UNIT_CAP_BY_ASYNC_ID`); brak w rezerwie → odrzucenie.
- Widok dla okna: `GET /tactical/production/view` (limit, użyte, producenci, strefy, planety, TG,
  jednostki z rezerwą). Front: `frontend/src/domains/production/` (okno otwiera się samo w kroku).

**Osobne zdolności PRODUCTION (R_production) — ✅ ZWERYFIKOWANE:** każda jednostka z PRODUCTION to
osobne źródło (`Producer`: strefa, typ, `per_unit`, `value`, `forbids`). Wartości SUMUJĄ się do limitu,
ale ograniczenia typów są per źródło. Arborec: „Production value from Arborec space docks cannot be
used to produce infantry" — dok (`("arborec","spacedock")` → `forbids=("infantry",)`) nie produkuje
piechoty; piechota Letani Warrior ma własne PRODUCTION 1 (II: 2) za sztukę i produkuje dowolny typ.
Walidacja = warunek Halla (`fits_producers`) na SKUMULOWANYCH sztukach tej akcji, więc kolejność
zamówień nie ma znaczenia. `GameState.production_placed` (strefa→typ→sztuki) trzyma, co powstało w
akcji; świeżo wyprodukowane jednostki NIE dokładają PRODUCTION w tym samym kroku (producenci =
stan sprzed kroku). Widok: `producers[].perUnit/forbids`, `usedByType`, `units[].onBoard`.

⚠️ ZAŁOŻENIA / luki (do decyzji użytkownika): (1) „usuń jednostkę z planszy, by dostawić z rezerwy"
(R_component_limitations) NIE jest zaimplementowane — brak rezerwy blokuje, wentylem jest God-Mode;
(2) ograniczenie doku Arborec siedzi na razie w tabeli `_PRODUCTION_FORBIDS` (docelowo hook frakcji,
E7); (3) modyfikatory kosztu/limitu z kart i technologii (E7) pominięte; (4) umiejscowienie naziemnych
nie jest wiązane z konkretnym producentem (planeta z dowolną zdolnością PRODUCTION przyjmuje sztuki
dowolnego producenta w systemie — zgodnie z przykładem z R_production).


---

## 34. Specyfikacja czasowa komponentów: wyzwalacz → typ okna — ⚠ ZAŁOŻENIE (D10)

📎 tirules: [Action Cards](rules_tirules/R_action_cards.md) · [Abilities](rules_tirules/R_abilities.md)

Implementacja: `src/core/timing_spec.py` (`TriggerKind`, `TimingSpec`, `parse_timing`,
`TRIGGER_WINDOW_MAP`); spec `local-ti4-data-foundation`, R8.

**Zweryfikowane (dane):** frazy okien (`window` kart akcji i zdolności frakcji,
`abilityWindow` liderów) są czytane z JSON AsyncTI4 i klasyfikowane wyłącznie po
prefiksie: `when ` / `after ` / `before ` / `instead of` / `at the start` / `at the end` /
`during ` / `action`; reszta → `unclassified`. Tekst okna zostaje bez zmian (`raw_text`).
`playTiming` (`AGENDA_WHEN`/`AGENDA_AFTER`) służy tylko do kontroli zgodności z oknem.

**⚠ ZAŁOŻENIE (do potwierdzenia przez użytkownika):** odwzorowanie rodzaju wyzwalacza na
`WindowType` silnika: `when`, `after`, `before`, `instead` → `REACTION`; `at_start`,
`at_end`, `during`, `action`, `unclassified` → „brak okna" (`None`). To decyzja
projektowa (D10), nie reguła TI4 — np. „at the start of..." może w przyszłości wymagać
własnego okna. Zmiana = edycja jednej tablicy `TRIGGER_WINDOW_MAP` + test.

---

## 35. Spójność referencji: placeholder `<color>` promissory notes jako SZABLON — ⚠ ZAŁOŻENIE

📎 tirules: [Promissory Notes](rules_tirules/R_promissory_notes.md)

Implementacja: `src/core/references.py` (`find_unresolved_references`,
`build_reference_report`, `UnresolvedReference`, `TemplateReference`); wpięcie w
`StaticDataRegistry` (`reference_report`, `unresolved_references()`). Spec
`local-ti4-data-foundation`, R7.

**Zweryfikowane (dane):** sprawdzanie spójności czyta WYŁĄCZNIE identyfikatory z JSON
AsyncTI4 (listy frakcji: `leaders`, `abilities`, `promissoryNotes`, `factionTech`,
`units`, `startingTech`, `startingTechOptions`; `cardIDs` talii kanonicznych;
`attachmentId` eksploracji; `attachmentID` żetonów) i porównuje je z Katalogiem_Komponentów
oraz słownikami rejestru. Zachowane jest istniejące sprawdzenie systemów → planet
(`missing_planet_references`). Cel istniejący, ale ze źródła niekanonicznego, jest
oznaczany flagą `leaks_noncanonical` (przeciek homebrew, R7.6), wykrywany przez
`LoadReport.skipped_index`.

**⚠ ZAŁOŻENIE (do potwierdzenia przez użytkownika):** promissory notes z pliku
`color.json` mają identyfikator z placeholderem `<color>` (np. `<color>_cf`,
`<color>_sftt`). To SZABLONY — jedna karta na każdy kolor gracza, nie konkretny
komponent. Przyjęte zachowanie: każda referencja, której identyfikator zawiera
`<color>`, jest raportowana OSOBNO jako „szablon” (`ReferenceReport.templates`) i NIE
liczona jako nierozwiązana referencja (nie wchodzi do `find_unresolved_references`).
Dopasowanie referencji odbywa się po dosłownym `id`, bez rozwijania koloru. To decyzja
projektowa (design R7, sekcja `core/references.py`), nie reguła TI4 — do potwierdzenia
po pierwszym raporcie Audytora_Danych. Zmiana = rozwinięcie szablonu na realne kolory
graczy (osobny krok) albo odmienne traktowanie w `references.py`.

---

## 36. Limity rąk i zbiór poziomów trudności bota — ✅ ZWERYFIKOWANE (reguły TI4) + ⚠️ ZAŁOŻENIE (trudność)

📎 tirules: [Action Cards](rules_tirules/R_action_cards.md) · [Objective Cards](rules_tirules/R_objective_cards.md) · [Promissory Notes](rules_tirules/R_promissory_notes.md)

Weryfikacja dla specyfikacji `player-model-and-setup-ui`, zadanie 5.1 (blokujące walidację
setupu w zad. 8 i 9). Wartości czytane są z assetu `assets/config/engine_config.json`
przez `StaticDataRegistry` (`hand_limits()`, `valid_difficulties()`) — NIE są hardkodowane
w logice silnika. Data weryfikacji: 2026-10.

### 36.1. Limity rąk (reguły TI4) — ✅ ZWERYFIKOWANE

Źródło główne: tirules2.com (lokalny zrzut `docs/rules_tirules/`). Reguła nadrzędna:
limit może być zmieniony przez efekty gry (karty/technologie) — bazowy limit poniżej.

| Ręka | Limit | Źródło (tirules) | Cytat-doprecyzowanie |
|---|---|---|---|
| Karty akcji (action cards) | **7** | [R_action_cards](rules_tirules/R_action_cards.md) | „Each player's hand can have a maximum of seven action cards." + „A game effect can increase or decrease the number of cards a player's hand can have." |
| Tajne obiektywy (secret objectives) | **3** (łącznie zrealizowane + niezrealizowane) | [R_objective_cards](rules_tirules/R_objective_cards.md) | „Each player can have up to three total scored and unscored secret objectives." (nadmiar → zwrot do talii) |
| Promissory notes | **brak limitu** (`null`) | [R_promissory_notes](rules_tirules/R_promissory_notes.md) | Reguły NIE podają górnego limitu ręki promissory notes. Gracz startuje z 6 własnymi (1 unikalna + 5 generycznych), lecz są one rozdawane innym; „The number of promissory notes in a player's hand is public information", ale bez kapu. |

Uwaga do tajnych obiektywów: limit „3 total" dotyczy zrealizowanych + niezrealizowanych.
W modelu (`PlayerPrivateState.secret_objectives`) trzymamy obecnie tylko NIEzrealizowane
(na ręce). Egzekucja limitu z uwzględnieniem zrealizowanych dojdzie, gdy powstanie
mechanika punktowania sekretów. Do tego czasu `secret_objectives = 3` jest limitem ręki
niezrealizowanych (zgodnym z regułą jako górne ograniczenie).

Zapis w assecie (`assets/config/engine_config.json`):
```json
"hand_limits": { "action_cards": 7, "secret_objectives": 3, "promissory_notes": null }
```
`null` = brak górnego limitu (reguła go nie nakłada).

### 36.2. Zbiór poziomów trudności bota — ⚠️ ZAŁOŻENIE (do potwierdzenia przez użytkownika)

Poziomy trudności bota **NIE istnieją w regułach TI4** — to koncepcja naszej warstwy AI
(sprawdzono: brak „difficulty" w assetach AsyncTI4 oraz w zrzucie reguł tirules). Zgodnie
z zasadą projektu nie hardkodujemy zbioru w kodzie: jest to wartość KONFIGUROWALNA czytana
z `engine_config.json` przez `StaticDataRegistry.valid_difficulties()`.

Zaproponowany zbiór startowy (⚠️ ZAŁOŻENIE): `["EASY", "NORMAL", "HARD"]`.

**Prośba o decyzję użytkownika:** czy ten zbiór jest właściwy, czy preferujesz inny
(np. dodać „VERY_HARD"/„INSANE", użyć polskich etykiet, albo skali liczbowej 1–5)? Zbiór
można zmienić wyłącznie edycją `assets/config/engine_config.json` — bez zmian w kodzie.
Do czasu potwierdzenia traktujemy ten zbiór jako tymczasowe założenie.

---

## 37. Wyniki audytu danych (baseline, luki referencyjne, założenia) — 📊 RAPORT

📎 tirules: [Technology](rules_tirules/R_technology.md) · [Promissory Notes](rules_tirules/R_promissory_notes.md) · [Exploration](rules_tirules/R_exploration.md)

Źródło danych: Audytor_Danych (`uv run python -m src.audit`), spec
`local-ti4-data-foundation` (R6, R7, R12). Liczby poniżej to zrzut z aktualnego rejestru
(źródła aktywne: `assets/enabled_sources.json` = `base, pok, codex1-4, thunders_edge`).
Baseline liczb trzymany jest maszynowo w `audit/baseline_counts.json` (test regresji
`tests/test_audit_baseline.py`, R6.4/R6.5) — tabela niżej jest jego ludzkim podsumowaniem.
**Zero liczb z pamięci:** wszystkie wartości pochodzą z `StaticDataCatalog.counts()`.

### 37.1. Liczby komponentów per Źródło_Kanoniczne (baseline)

| Kategoria | Σ | base | pok | codex1 | codex2 | codex3 | codex4 | thunders_edge |
|---|---|---|---|---|---|---|---|---|
| action_cards | 143 | 82 | 20 | 21 | — | — | — | 20 |
| agendas | 63 | 50 | 13 | — | — | — | — | — |
| attachments | 22 | — | 18 | — | — | 2 | — | 2 |
| border_anomalies | 1 | — | — | — | — | — | — | 1 |
| decks | 25 | 9 | 11 | — | — | — | — | 5 |
| explores | 80 | — | 74 | — | — | 6 | — | — |
| galactic_events | 20 | — | — | — | — | — | — | 20 |
| genericcards | 10 | — | — | — | — | — | — | 10 |
| promissory_notes | 40 | 21 | 9 | — | — | 4 | — | 6 |
| public_objectives | 40 | 20 | 20 | — | — | — | — | — |
| relics | 24 | — | 11 | — | 3 | — | 3 | 7 |
| secret_objectives | 40 | 20 | 20 | — | — | — | — | — |
| tokens | 29 | 6 | 14 | — | — | — | — | 9 |

„—" = brak wpisów danego źródła w kategorii. To NIE jest błąd: większość kart base/PoK
nie ma erraty Codex ani dodatków Thunder's Edge. Pełna, maszynowa lista braków
(„do potwierdzenia") jest w `audit/expected_gaps.json`; audyt raportuje 59 takich luk
(np. brak agend, celów publicznych i tajnych z `codex*` i `thunders_edge`) — to pozycje
do potwierdzenia przez użytkownika (R6.2), nie usterki.

### 37.2. Znane luki referencyjne (homebrew — udokumentowane, nie usterki)

Audytor wykrywa 22 nierozwiązane referencje. **Wszystkie pochodzą z treści homebrew**,
która mimo niekanonicznego źródła odwołuje się do komponentów nieładowanych przez rejestr.
Są tu świadomie udokumentowane jako znane i NIE blokują dalszego kodowania reguł
kanonicznych (do finalnego potwierdzenia przez użytkownika):

- **`explores_cpti`** (talia homebrew „cpti") — 18 wpisów `deck.cardIDs` wskazujących
  nieistniejące karty (`fiveac1..3`, `fivetg1..3`, `freetech1..3`, `gain*agent`, `kel3`).
  Flaga `leaks_noncanonical=True` (przeciek homebrew, R7.6). Talia nie jest kanoniczna —
  do wykluczenia lub zignorowania.
- **`mirage`** — `exploration.attachmentId='mirage'` → brak attachmentu `mirage`
  (homebrew / wariant nieładowany).
- **`gamma`** i **`gw`** — `exploration.attachmentId='gamma'` → brak attachmentu `gamma`
  (homebrew anomalii „gamma wormhole").
- **`ion`** — `exploration.attachmentId='ionalpha'` → brak attachmentu `ionalpha`
  (homebrew „ion storm").

Rekomendacja: traktować te referencje jako przeciek treści fanowskiej. Docelowo filtr
źródeł lub wykluczenie talii homebrew usunie je z raportu; do tego czasu są tu spisane,
by audyt nie był „czerwony z nieznanego powodu".

### 37.3. Anomalia danych: wpis `codex1` w `theodisi.json` — ⚠️ ZAŁOŻENIE (do potwierdzenia)

Audytor oznacza jako „podejrzane" wpisy ze Źródłem_Kanonicznym leżące w plikach o nazwie
wskazującej na homebrew (R4.5). Kluczowy przypadek: karta akcji ze `source=codex1`
w pliku homebrew `theodisi.json`. **Przyjęte zachowanie (D6):** wpis jest ŁADOWANY
(filtr działa po polu `source`, nie po nazwie pliku), więc trafia do katalogu jako
kanoniczny `codex1`. To ⚠️ ZAŁOŻENIE — do potwierdzenia przez użytkownika, czy to
prawdziwa karta Codex 1, czy błąd oznaczenia w pliku homebrew.

### 37.4. Założenia projektowe powiązane z audytem — ⚠️ ZAŁOŻENIA

- **`TRIGGER_WINDOW_MAP` (D10)** — odwzorowanie rodzaju wyzwalacza na `WindowType`
  (`when/after/before/instead` → `REACTION`; reszta → brak okna). Opis i prośba
  o potwierdzenie: [sekcja 34](#34-specyfikacja-czasowa-komponentów-wyzwalacz--typ-okna---założenie-d10).
  Audyt raportuje 11 komponentów ze specyfikacją `unclassified`.
- **Placeholder `<color>` w promissory notes (D35 / sekcja 35)** — identyfikatory
  szablonowe (`<color>_cf`, `<color>_sftt`) traktowane jako SZABLON, raportowane osobno
  i NIE liczone jako nierozwiązane referencje. Opis i prośba o potwierdzenie:
  [sekcja 35](#35-spójność-referencji-placeholder-color-promissory-notes-jako-szablon---założenie).

### 37.5. Odświeżenie liczb

Aktualny zrzut generuje się jedną komendą:

```bash
uv run python -m src.audit --json        # liczby + statystyki w JSON
uv run python -m src.audit               # pełny raport tekstowy (kod ≠ 0 przy błędach krytycznych)
uv run python -m src.audit --write-baseline   # zapis audit/baseline_counts.json
```

Po zmianie liczb (nowe źródło, errata) zaktualizuj baseline i to podsumowanie razem.


---

## 38. Space Cannon Offense: kolejność, zasięg (Deep Space Cannon), rzuty, straty — ✅ ZWERYFIKOWANE (LRR 2.0)

📎 tirules: [Space Cannon](rules_tirules/R_space_cannon.md) · [PDS](rules_tirules/R_pds.md) · [Adjacency](rules_tirules/R_adjacency.md) · [Active Player](rules_tirules/R_active_player.md) · [Sustain Damage](rules_tirules/R_sustain_damage.md) · [Capacity](rules_tirules/R_capacity.md)

Etap E8, krok SPACE_CANNON akcji taktycznej. Źródło: lokalny `R_space_cannon.md` (treść © FFG;
patrz SOURCE.md). Dane liczbowe wyłącznie z UnitDef (`spaceCannonHitsOn`, `spaceCannonDieCount`,
`deepSpaceCannon`) — zero liczb z pamięci.

### 38.1. Reguły (Space Cannon Offense)

- **(S1) Po ruchu, przed walką.** Po kroku Move Ships każdy gracz MOŻE użyć Space Cannon swoich
  jednostek w AKTYWNYM systemie. Działa także, gdy nikt nie ruszył statków.
- **(S2) NIE tylko aktywny gracz.** „A player is **not** required to be the active player". Kolejność:
  zaczyna AKTYWNY gracz i idzie ZGODNIE Z ZEGAREM (`seating_order` obrócone tak, by aktywny był
  pierwszy). To okno czasowe (`WindowType.SPACE_CANNON`, RULES.md 29.2), nie ruch aktywnego gracza.
- **(S3) Cele.** Gracze inni niż aktywny MUSZĄ celować w jednostki aktywnego gracza. Aktywny gracz,
  używając własnych jednostek, WYBIERA gracza mającego statki w aktywnym systemie. Gracz bez
  legalnego celu (nikt do trafienia) jest pomijany w kolejce.
- **(S4) Rzut.** Jeden rzut (d10) na każdą kość każdej jednostki z Space Cannon w aktywnym systemie
  (statki w przestrzeni ORAZ struktury/jednostki na planetach tego systemu). Trafienie = wynik ≥
  `spaceCannonHitsOn`. Kości = `spaceCannonDieCount` (brak wartości = 1 kość). „0" na d10 = 10.
  Efekty modyfikujące/przerzucające rzuty bojowe NIE dotyczą rzutów space cannon.
- **(S5) Wszystko albo nic.** Gracz używający Space Cannon musi użyć go dla WSZYSTKICH swoich
  kwalifikujących się jednostek (łącznie z sąsiednimi — S6).
- **(S6) Zasięg — Deep Space Cannon.** Jednostka z Space Cannon stojąca w systemie SĄSIEDNIM do
  aktywnego (sąsiedztwo grafu, `R_adjacency`: geometria + wormhole) strzela TYLKO wtedy, gdy jej
  WARIANT u danego gracza ma `deepSpaceCannon`. Wariant zależy od technologii gracza: PDS I
  (`spaceCannonHitsOn=6`, bez deep) → PDS II (tech `pds2`: `5`, `deepSpaceCannon=true`). Trafienia
  nadal trafiają jednostki w AKTYWNYM systemie. Wariant wybiera `combat.resolve_unit_variant`
  (frakcyjny-ulepszony > … > generyczny-bazowy), nie lista technologii wpisana w kod.
- **(S7) Przypisanie strat.** Gracz trafiony niszczy po jednym SWOIM statku w aktywnym systemie za
  każde trafienie (łącznie z myśliwcami). Nie może przypisać trafień do cudzych jednostek.
  Liczba zniszczonych = min(trafienia, liczba jego statków w systemie).
- **(S8) Kolejność w obrębie okna.** Najpierw rozstrzygają się straty po rzucie danego gracza,
  dopiero potem rzuca następny.

### 38.2. Zasięg do podglądu na mapie („Space Cannon range")

Soczewka mapy pokazuje, które systemy są POD OSTRZAŁEM: dla każdego kafelka i każdego gracza liczy
jednostki z Space Cannon stojące w tym kafelku (bezpośrednio) oraz jednostki z `deepSpaceCannon`
stojące w sąsiednich. Wynik trafia do web-data jako `tileUnitData[pos].pds[faction] = {count,
expected}` (kontrakt, który front AsyncTI4 już rysuje); `expected` = Σ kości × (11 − hitsOn)/10.

### 38.3. Implementacja

- `core/dice.py` — seedowalny rzut d10 trzymany w stanie gry (`GameState.rng_seed/rng_counter`),
  więc Undo/Redo są deterministyczne. Wspólna podstawa pod walkę (Blok C).
- `core/space_cannon.py` — strzelcy, pokrycie, kolejka, `open_offense`/`fire`/`pass`/`assign_hits`.
- `api/routers/space_cannon.py` — `GET /tactical/space-cannon`, `POST …/fire`, `…/pass`, `…/assign`.
- Wejście do kroku SPACE_CANNON (`/tactical/step/next`) otwiera okno automatycznie; wyjście z kroku
  jest blokowane (422), dopóki okno trwa.
- Po ostatnim graczu okno się zamyka, ale dziennik rozstrzygnięcia (rzuty, trafienia, straty) zostaje
  w `GameState.space_cannon_log` do końca akcji taktycznej — panel pokazuje wynik (`resolved`).

### 38.4. ⚠️ ZAŁOŻENIA / TODO (do potwierdzenia)

- ⚠️ **Sustain Damage nie jest modelowany** (stan nie rozróżnia uszkodzonych jednostek) — trafienie
  zawsze niszczy statek. `R_space_cannon`: statek MOŻE użyć Sustain Damage, by anulować trafienie.
  Dojdzie z modelem uszkodzeń w Bloku C (walka).
- ⚠️ **Capacity po stratach** — reguła wymaga rozstrzygnąć capacity po przypisaniu strat (a przed
  rzutem następnego gracza); na razie nie wymuszamy, nadwyżkę usuwa operator.
- ⚠️ **Plasma Scoring** (tech `ps`: +1 kość dla jednej jednostki) — nie zaimplementowane.
- ⚠️ Efekty zdolności frakcji/kart modyfikujące Space Cannon — hooki E7.


---

## 39. Walka (kosmiczna i naziemna): rundy, AFB, rzuty, Sustain Damage, straty — ✅ ZWERYFIKOWANE (LRR 2.0)

📎 tirules: [Space Combat](rules_tirules/R_space_combat.md) · [Ground Combat](rules_tirules/R_ground_combat.md) · [Anti–Fighter Barrage](rules_tirules/R_anti_fighter_barrage.md) · [Sustain Damage](rules_tirules/R_sustain_damage.md) · [Combat](rules_tirules/R_combat.md) · [Attacker](rules_tirules/R_attacker.md) · [Nebula](rules_tirules/R_nebula.md) · [Status Phase](rules_tirules/R_status_phase.md)

Etap E8, Blok C (silnik walki) + D (okno pola bitwy). Źródło: lokalne pliki tirules (treść © FFG;
patrz SOURCE.md). Dane liczbowe wyłącznie z UnitDef wariantu gracza (`combatHitsOn`,
`combatDieCount`, `afbHitsOn`, `afbDieCount`, `sustainDamage`) — zero liczb z pamięci.

### 39.1. Strony i uczestnicy

- **(W1) Atakujący = aktywny gracz** (`R_attacker`); obrońca = jego przeciwnik w walce.
- **(W2) Walka kosmiczna**: gdy w aktywnym systemie statki ma dwóch graczy (`R_space_combat`). Walczą
  statki (przestrzeń) z wartością `combat`; siły naziemne w przestrzeni NIE walczą.
- **(W3) Walka naziemna**: na planecie aktywnego systemu, gdy siły naziemne mają tam aktywny gracz i
  inny gracz (`R_ground_combat`). Walczą siły naziemne z wartością `combat` (struktury bez combat nie).
- ⚠️ ZAŁOŻENIE: gdy w miejscu walki jest więcej niż jeden przeciwnik aktywnego gracza — silnik odmawia
  (422) i rozstrzyga się to God-Mode (sytuacja brzegowa, brak jednoznacznej reguły w zrzucie).

### 39.2. Przebieg rundy

- **(W4) AFB** — tylko 1. runda walki KOSMICZNEJ: obaj gracze rzucają jednocześnie dla jednostek z
  `Anti–Fighter Barrage` (trafienie = wynik ≥ `afbHitsOn`, kości = `afbDieCount`). Każdy niszczy swoje
  MYŚLIWCE za trafienia przeciwnika; nadwyżka przepada; Sustain Damage NIE anuluje trafień AFB.
  Krok występuje także bez myśliwców. Gdy po AFB któraś strona nie ma statków — walka kończy się.
- **(W5) Rzuty** — każda jednostka rzuca `combatDieCount` kości (brak = 1); trafienie = wynik ≥ wartość
  combat. Najpierw rzuca atakujący, potem obrońca. „0" na d10 = 10.
- **(W6) Mgławica** — w walce KOSMICZNEJ w mgławicy obrońca dodaje +1 do każdego rzutu combat swoich
  statków (nie dotyczy AFB, space cannon, bombardmentu ani walki naziemnej) — `R_nebula`.
- **(W7) Przypisanie strat** — każdy gracz niszczy SWOJE jednostki w walce za każde trafienie
  przeciwnika. Kolejność w oknie czasowym `COMBAT_ASSIGN_HITS` (RULES.md 29.2): obrońca, potem atakujący.
  Liczba trafień do pokrycia = min(trafienia, jednostki + nieuszkodzone jednostki z Sustain Damage).
- **(W8) Sustain Damage** — przed przypisaniem gracz może użyć Sustain Damage dowolnych swoich
  NIEUSZKODZONYCH jednostek z tą zdolnością: każda anuluje jedno trafienie i staje się USZKODZONA.
  Uszkodzona jednostka działa normalnie, ale nie może ponownie użyć Sustain Damage do naprawy.
- **(W9) Koniec walki** — gdy po rundzie najwyżej jeden gracz ma jednostki w walce. Zwycięzca = ten,
  komu zostały jednostki; brak jednostek u obu = remis. Inaczej kolejna runda (bez AFB).
- **(W10) Naprawa** — w fazie statusu (krok 7 „Repair Units") wszystkie uszkodzone jednostki są
  naprawiane (`R_status_phase`). Silnik czyści stan uszkodzeń przy wejściu w STATUS.

### 39.3. Model i implementacja

- `SystemState.damaged_units` = `{strefa: {player_id: {base_type: liczba}}}` (strefa `"space"` albo id
  planety). Liczba uszkodzonych ≤ liczba jednostek (odczyt przycinany). Web-data wystawia
  `EntityData.sustained` (front AsyncTI4 rysuje znacznik uszkodzenia).
- `GameState.active_combat` (`ActiveCombat`: rodzaj, miejsce, atakujący/obrońca, runda, krok
  `AFB/ROLL/ASSIGN/DONE`, trafienia, rzuty rundy, dziennik, zwycięzca).
- `core/battle.py` — `start_combat`/`resolve_afb`/`roll_round`/`assign_combat_hits`/`close_combat`.
  Rzuty przez `core/dice.py` (seedowalne, w stanie).
- Krok SPACE_COMBAT nie może zostać opuszczony, gdy dwóch graczy ma statki w aktywnym systemie albo
  walka trwa (422). Zakończenie akcji czyści walkę (wentyl).
- Ruch (`move_fleet`) przenosi uszkodzenia razem ze statkami: najpierw ruszają nieuszkodzone
  (⚠️ ZAŁOŻENIE — wybór konkretnych egzemplarzy nie jest modelowany).

### 39.5. Odwroty (Announce Retreats / Retreat) — ✅ ZWERYFIKOWANE (LRR 2.0)

📎 tirules: [Space Combat](rules_tirules/R_space_combat.md) · [Ground Combat](rules_tirules/R_ground_combat.md) · [Movement](rules_tirules/R_movement.md) · [Nebula](rules_tirules/R_nebula.md) · [Gravity Rift](rules_tirules/R_gravity_rift.md) · [Neutral Units](rules_tirules/R_neutral_units.md) · [Command Tokens](rules_tirules/R_command_tokens.md)

Kolejność kroków rundy walki KOSMICZNEJ: AFB (tylko 1. runda) → **Announce Retreats** → Roll → Assign
Hits → **Retreat** → (kolejna runda od Announce Retreats).

- **(O1) Tylko walka kosmiczna.** Z walki naziemnej nie ma odwrotu (`R_ground_combat`). Jednostki
  neutralne się nie wycofują (`R_neutral_units`).
- **(O2) Ogłoszenie** — każdy gracz MOŻE ogłosić odwrót, zaczynając od obrońcy. Odwrót nie następuje
  od razu, tylko w kroku Retreat. Gdy obrońca ogłosi odwrót, atakujący NIE może go ogłosić w tej rundzie.
  Gracz nie może ogłosić odwrotu bez co najmniej jednego dozwolonego systemu (O4).
  Model: okno czasowe `COMBAT_RETREAT` (RULES.md 29.2), kolejka = [obrońca, atakujący] przefiltrowana
  do graczy z dozwolonym celem; gdy nikt nie ma celu — krok jest pomijany.
- **(O3) Wykonanie** — w kroku Retreat gracz, który ogłosił odwrót, MUSI się wycofać, o ile wciąż ma
  dozwolony system. Gdy przeciwnikowi nie zostały statki — walka kończy się od razu, odwrót nie
  następuje. Gdy dozwolonego systemu już nie ma — odwrót nie następuje, walka toczy się dalej.
- **(O4) Dozwolony system** — SĄSIEDNI z aktywnym; zawiera jednostki gracza lub planetę, którą kontroluje
  (albo oba); NIE zawiera statków innego gracza. Anomalie: nie do mgławicy (nie jest systemem aktywnym —
  `R_nebula`), nie do supernowej, do pola asteroid tylko z Antimass Deflectors. Do gravity rift wolno.
- **(O5) Ruch** — wycofują się WSZYSTKIE statki gracza z wartością ruchu (wariant gracza: `moveValue`),
  razem, do JEDNEGO systemu. Wartość ruchu nie ma znaczenia (tylko sąsiedni). Statki mogą przewieźć
  myśliwce i siły naziemne z przestrzeni aktywnego systemu (w granicach `capacityValue`) oraz siły naziemne
  z planet, które gracz kontroluje w aktywnym systemie (`R_space_combat` Notes). Gracz NIE może zostawić
  myśliwców/sił naziemnych z przestrzeni, jeśli ma wolną pojemność. Myśliwce i siły naziemne z przestrzeni,
  których nie da się przewieźć, są USUWANE. Transport z aktywnego systemu jest dozwolony (`R_movement`).
- **(O6) Żeton dowodzenia** — gdy jakiekolwiek jednostki faktycznie się wycofały, gracz kładzie żeton z
  REZERWY (`cc_reinf`) w systemie docelowym; gdy już ma tam żeton — nie kładzie drugiego. Pusta rezerwa →
  żeton z arkusza dowodzenia (wybór puli). Same myśliwce I (bez ruchu) → zostają usunięte, żetonu nie ma.
- **(O7) Po kroku Retreat** — jeśli obaj gracze nadal mają statki w aktywnym systemie, kolejna runda
  od Announce Retreats; inaczej walka się kończy (zwycięzca = gracz ze statkami).
- ⚠️ ZAŁOŻENIE: gdy rezerwa żetonów jest pusta i gracz nie wskazał puli, silnik bierze żeton kolejno z
  puli taktycznej, floty, strategicznej (reguła pozwala graczowi wybrać — UI może podać pulę jawnie).
- ⚠️ ZAŁOŻENIE: domyślny ładunek (gdy gracz go nie wskaże) = najpierw mechy, potem piechota, potem myśliwce
  z przestrzeni, do zapełnienia pojemności; bez sił naziemnych z planet. Jawny wybór jest walidowany
  regułą O5.
- ⚠️ TODO: rzuty gravity rift przy odwrocie z gravity rift (`R_gravity_rift`), wyjątki frakcji/technologii
  (Magmus Reactor — supernova, Empyrean — mgławica, Dark Energy Tap, Skilled Retreat) — hooki E7.

### 39.6. Limit pojemności (capacity) w przestrzeni systemu — ✅ ZWERYFIKOWANE (LRR 2.0)

📎 tirules: [Capacity](rules_tirules/R_capacity.md) · [Space Combat](rules_tirules/R_space_combat.md) · [Space Dock](rules_tirules/R_space_dock.md)

- **(C1) Co się liczy** — łączna `capacityValue` statków gracza w systemie wyznacza, ile myśliwców i sił
  naziemnych (piechota, mech) gracz może mieć w PRZESTRZENI tego systemu. Siły naziemne na planetach się
  nie liczą. Każda jednostka ładunku zajmuje `capacityUsed` z wariantu (brak = 1).
- **(C2) Nadwyżka** — gdy ładunku w przestrzeni jest więcej niż pojemności, gracz MUSI usunąć nadmiar
  (wraca do rezerwy) i SAM wybiera, które jednostki. Usuwa tylko tyle, ile trzeba.
- **(C3) Kiedy** — w trakcie walki limit nie obowiązuje. Sprawdzany jest po wyłonieniu zwycięzcy walki
  kosmicznej (można wygrać samymi myśliwcami, a potem je usunąć) oraz przed Space Cannon Offense / walką
  kosmiczną, jeśli nosiciel zginął albo ruch dowiózł ładunek (`R_capacity` Notes).
- **(C4) Dok** — dane doku (`assets/.../units`: `capacityValue` + zdolność „Up to N fighters in this
  system do not count against your ships' capacity") → dok gracza na planecie systemu daje pojemność
  TYLKO dla myśliwców, równą `capacityValue` wariantu. Jednostka typu dok stojąca w przestrzeni (Saar,
  „Floating Factory") daje zwykłą pojemność jak statek.
- Model: okno czasowe `CAPACITY` (RULES.md 29.2), kolejka = gracze z nadwyżką w aktywnym systemie, od
  aktywnego zgodnie z zegarem. Dopóki trwa, nie można przejść do kolejnego kroku akcji.
- ⚠️ ZAŁOŻENIE: dok Mahact/Cabal (Dimensional Tear) ma w danych opis „6 fighters", ale BRAK
  `capacityValue` — silnik liczy wtedy 0 (dane rozstrzygają; do uzupełnienia hookiem frakcji E7).
- ⚠️ ZAŁOŻENIE: przycisk „Auto" w UI usuwa najpierw jednostki najtańsze (`cost` z danych). To tylko
  podpowiedź — wybór gracza jest walidowany regułą C2.
- ⚠️ TODO: limit przy produkcji (myśliwce/piechota w przestrzeni) i po Commit Ground Forces nie otwiera
  jeszcze okna samodzielnie — przy kolejnym przejściu kroku silnik i tak wykryje nadwyżkę.

### 39.4. ⚠️ TODO (kolejne bloki)

- Odwroty: wyjątki frakcji/kart i gravity rift (39.5 TODO).
- Zdolności frakcji, karty akcji (Shields Holding, Direct Hit), Non-Euclidean Shielding — hooki E7.
- Space Cannon Offense nie korzysta jeszcze z Sustain Damage (RULES.md 38.4) — do ujednolicenia.

---

## 40. Inwazja: Bombardment, Commit, Space Cannon Defense, walka naziemna, Establish Control — ✅ ZWERYFIKOWANE (LRR 2.0)

📎 tirules: [Invasion](rules_tirules/R_invasion.md) · [Bombardment](rules_tirules/R_bombardment.md) · [Planetary Shield](rules_tirules/R_planetary_shield.md) · [Ground Combat](rules_tirules/R_ground_combat.md) · [Space Cannon](rules_tirules/R_space_cannon.md) · [Control](rules_tirules/R_control.md)

Etap E8 (krok INVASION akcji taktycznej). Źródło: lokalne pliki tirules (treść © FFG; patrz SOURCE.md).

### 40.1. Reguły

- (I1) **Pięć podkroków** w stałej kolejności: Bombardment → Commit Ground Forces → Space Cannon Defense → Ground Combat → Establish Control. Jednostki są „na planecie" (dla efektów gry) od Commit.
- (I2) **Bombardment**: tylko aktywny gracz. Wybiera planetę dla każdej jednostki z Bombardment i rzuca `X (×Y)` kośćmi; trafienie = wynik ≥ X. Efekty modyfikujące rzuty bojowe NIE działają na bombardowanie. Kości jednej jednostki idą w JEDNĄ planetę. Gracz może nie bombardować wcale, ale jeśli bombarduje, MUSI użyć Bombardment KAŻDEJ swojej jednostki w aktywnym systemie.
- (I3) Obrońca planety niszczy własne siły naziemne za każde trafienie (nadwyżka przepada); mech może użyć Sustain Damage, by anulować trafienie. Bombardment dzieje się POZA walką (nie liczy się do celów „wygraj walkę").
- (I4) **Planetary Shield**: planety z jednostką Planetary Shield (PDS) nie mogą być bombardowane. War sun (`disablesPlanetaryShield`) ignoruje tarcze cudzych jednostek w swoim systemie — wtedy bombardować mogą wszystkie jednostki z Bombardment. Tarcza jednej planety nie chroni innych planet systemu.
- (I5) **Commit Ground Forces**: aktywny gracz może zlądować dowolną liczbę sił naziemnych z przestrzeni aktywnego systemu na dowolne planety systemu (także z cudzymi siłami). Brak lądowania → od razu Production.
- (I6) **Space Cannon Defense**: jednostki Space Cannon STOJĄCE NA planecie, na którą zlądowano siły, mogą strzelać w zlądowane siły (opcjonalnie). Aktywny gracz wybiera kolejność planet. Trafienia pokrywa atakujący (Sustain Damage dozwolone).
- (I7) **Ground Combat**: planeta, na której aktywny gracz i inny gracz mają siły naziemne → walka (RULES.md 39, kind="ground"). Po Space Cannon Defense na WSZYSTKICH planetach, przed Establish Control na jakiejkolwiek. Aktywny gracz wybiera kolejność walk. Bez odwrotów.
- (I8) **Establish Control**: aktywny gracz przejmuje każdą planetę, na którą lądował, jeśli wciąż ma tam siłę naziemną. Struktury innych graczy na planecie są natychmiast niszczone; gracz dostaje kartę planety i ją WYCZERPUJE. Nie można przejąć planety już kontrolowanej. Gdy była walka i zginęły wszystkie jednostki obu stron — obrońca zachowuje kontrolę (kładzie żeton kontroli). Przejęcie niekontrolowanej planety → eksploracja.

### 40.2. Model i implementacja

- `GameState.invasion: InvasionState | None` (`phase: InvasionPhase`, `committed`, `bombard_pending`, `defense_pending/resolved`, `combat_results`, `results`, `log`). Otwierana przy wejściu w krok INVASION (`invasion.begin_invasion`); nie otwiera się, gdy nie ma ani bombardowania, ani sił do lądowania.
- `core/invasion.py`: `bombard` / `assign_bombard_hits`, `commit_ground_forces`, `defense_fire` / `defense_pass` / `assign_defense_hits`, `advance` (pomija podkroki bez pracy), `_establish_control`. Wartości z wariantu jednostki (`bombardHitsOn/DieCount`, `planetaryShield`, `disablesPlanetaryShield`, `spaceCannon*`).
- Walka naziemna = `core/battle.py` (`start_combat(planet)`); `close_combat` zapisuje wynik w `invasion.combat_results` (remis → obrońca zachowuje planetę). Wspólny kod strat: `battle.plan_losses` / `apply_losses`.
- Z kroku INVASION nie wolno wyjść (`tactical.next_step`) dopóki inwazja nie doszła do ESTABLISH.
- Inwazja startuje PRZYCISKIEM w panelu pomocy (`POST /tactical/invasion/begin`), nie przy wejściu w krok. „Prosta inwazja" (`simple`: brak celu bombardowania, brak sił naziemnych obrońcy i brak Space Cannon na planetach) pomija kroki 1, 3, 4 — lądowanie robi się w panelu pomocy (ile piechoty/mechów na którą planetę); pełne okno inwazji otwiera się tylko, gdy ktoś broni planety.
- API: `GET /tactical/invasion`, `POST /tactical/invasion/{bombard, bombard/assign, commit, defense/fire, defense/pass, defense/assign, next}`.

### 40.3. ⚠ ZAŁOŻENIA / TODO

- ⚠ ZAŁOŻENIE: bombardują wyłącznie STATKI w przestrzeni (mech z Bombardment, np. L1Z1X, nie jest modelowany).
- ⚠ ZAŁOŻENIE: przy >1 obrońcy na planecie (koegzystencja) bombardowanie i walka → 422 (God-Mode), jak w walce 39.1.
- ⚠ ZAŁOŻENIE: Space Cannon Defense strzela WSZYSTKIMI jednostkami Space Cannon nie-atakujących graczy na planecie naraz (jedna decyzja „strzelać / nie" na planetę).
- ⚠ TODO: żeton Custodians na Mecatol Rex (musi zostać zdjęty przed lądowaniem), (eksploracja po przejęciu → ZROBIONE, patrz 46), karta legendarnej planety, Plasma Scoring, Magen Defense Grid, X-89, L1Z1X Harrow, Sustain Damage w Space Cannon — hooki E7.

---

## 41. Faza statusu, cele publiczne/tajne, punkty zwycięstwa — ✅ ZWERYFIKOWANE (tirules2.com) + ⚠ ZAŁOŻENIA

📎 tirules: [Status Phase](rules_tirules/R_status_phase.md) · [Objective Cards](rules_tirules/R_objective_cards.md) · [Victory Points](rules_tirules/R_victory_points.md) · [Custodians Token](rules_tirules/R_custodians_token.md) · [Command Tokens](rules_tirules/R_command_tokens.md) · [Fleet Pool](rules_tirules/R_fleet_pool.md) · [Objectives (noty kart)](rules_tirules/C_objectives.md)

Etap E8 (faza statusu). Źródło: lokalne pliki tirules (treść © FFG; patrz SOURCE.md). Dane kart celów (nazwa, punkty, faza) z katalogu komponentów AsyncTI4.

### 41.1. Setup celów (R_objective_cards)
- (O1) Gra ma **pięć** celów I etapu i **pięć** II etapu (zakryte, losowane z talii). Mówca **odkrywa dwa cele I etapu** w setupie; reszta zakryta.
- (O2) Każdy gracz zaczyna z **jednym tajnym celem**. Limit: **3** tajne cele łącznie (zdobyte + niezdobyte).
- (O3) Etap celu = talia, z której pochodzi (`public_stage_1/2_objective`); punkty z karty (I = 1 VP, II = 2 VP).

### 41.2. Osiem kroków fazy statusu (R_status_phase)
1. **Score Objectives** — wg inicjatywy każdy gracz może zdobyć ≤ 1 cel publiczny i ≤ 1 tajny z fazą „Status". Każdy cel tylko raz na grę; ten sam cel może zdobyć wielu graczy. Cel publiczny wymaga kontroli KAŻDEJ planety systemu domowego (stacje kosmiczne się nie liczą).
2. **Reveal Public Objective** — mówca odkrywa następny cel; cele II etapu dopiero po wszystkich z I etapu. Brak zakrytych celów na początku kroku → **koniec gry** (najwięcej VP, remis → pierwszy wg inicjatywy).
3. **Draw Action Cards** — każdy dobiera 1 kartę (wg inicjatywy). Przy niedoborze: najpierw gracze NAJNIŻEJ w inicjatywie, potem tasowanie odrzuconych i reszta.
4. **Remove Command Tokens** — żetony z planszy wracają do rezerwy (`cc_reinf`).
5. **Gain and Redistribute** — każdy bierze 2 żetony z rezerwy (mniej, jeśli rezerwa mniejsza) i rozdziela WSZYSTKIE żetony między pule strategy/tactic/fleet. Po zmniejszeniu fleet pool trzeba sprawdzić statki (R_fleet_pool: ≤ tyle statków nie-myśliwców w systemie, ile żetonów we flocie).
6. **Ready Cards** — planety, technologie, liderzy (agenci), przełom i karty strategii wracają do stanu gotowego.
7. **Repair Units** — wszystkie uszkodzone jednostki naprawione (także bez Sustain Damage).
8. **Return Strategy Cards** — karty wracają do puli. Jeśli **zdjęto żeton Custodians** → dalej faza agendy, inaczej nowa runda od fazy strategii.

### 41.3. Punkty zwycięstwa (R_victory_points)
- (V1) Gra kończy się natychmiast, gdy gracz osiągnie `vps_to_win` (10; 14 na drugiej stronie toru). Remis na progu → pierwszy wg inicjatywy.
- (V2) Zdobycie celu publicznego: gracz kładzie żeton kontroli na karcie i przesuwa się o punkty karty; tajny cel jest przy zdobyciu **ujawniany**.

### 41.4. Implementacja
- `GameState`: `objectives` (`ObjectivesState`: `stage1_deck`, `stage2_deck`, `revealed`, `scored`, `custom_points`), `decks` (`action_card_deck/discard`, `secret_objective_deck`), `status` (`StatusPhaseState`: `step` ∈ `SCORE_OBJECTIVES|REDISTRIBUTE|COMPLETE`, `scored_public/secret`, `done`, `unassigned_cc`, `fleet_excess`, `log`), `custodians_removed`, `vps_to_win`, `winner_id`; `PlayerState.scored_secrets` (jawne).
- `core/objectives.py` — setup talii (`setup_objectives`, wołane w `/game/new`), `reveal_next_public`, `score_public/secret`, `controls_home_planets`, `award_points`.
- `core/status_phase.py` — kroki: `score_objective`, `finish_scoring` (po ostatnim graczu automaty 2–4 + zdobycie żetonów), `redistribute` (po ostatnim automaty 6–7 → `COMPLETE`), `finish_status` (krok 8 = `/phase/next` mówcy), `complete_status` (tryb testowy `/phase/skip`).
- `turn_flow.next_phase` przy wejściu w STATUS inicjuje `status` (naprawa jednostek NIE dzieje się już przy samym wejściu — to krok 7). `can_advance_phase` w zainicjowanym statusie = `step == COMPLETE`. `/turn/phase-step` w zainicjowanym statusie → 422. Status wprowadzony God-Mode (`status = None`) działa starą ścieżką (pasy → `next_phase`).
- Karty strategii wracają w kroku 8 (TG na niewybranych doliczone PRZED zwrotem), więc `/round/next` po agendzie używa `strategy_phase.close_round_cards` (nic nie robi, gdy karty już zwrócone).
- API: `POST /status/score`, `/status/finish-scoring`, `/status/redistribute`; `POST /phase/next` w statusie = krok 8. Web-data: `objectives` (tabele I/II etapu + „inne punkty", zakryte cele jako `UNREVEALED_*`), `scoreBreakdowns` (tor punktów per gracz), `gameState.status`, `gameState.winner/winnerId`, `playerData.secretsScored/knownUnscoredSecrets`.
- UI: `StatusPhasePanel` (8 kroków, punktowanie, rozdział żetonów), istniejące moduły AsyncTI4 (tabele celów pod mapą, `PlayerScoreSummary`) zasilane już prawdziwymi danymi.

### 41.5. ⚠ ZAŁOŻENIA / TODO (do potwierdzenia przez użytkownika)
- ✅ **Sprawdzanie treści kart celów** (`core/objective_progress.py`, port `ListPlayerInfoService` z AsyncTI4): próg (`THRESHOLDS`) + postęp gracza dla WSZYSTKICH 40 publicznych i 26 tajnych celów fazy statusu; `score_*` odrzuca zdobycie, gdy `postęp < próg` (422 „requirements not met (x/y)"). Cele „Spend…" opłaca automatycznie `core/objective_payment.py` (planety wyczerpane najpierw, brak dopłacają TG; żetony z puli taktycznej, potem strategicznej; ⚠ ZAŁOŻENIE — gracz nie wybiera planet). Web-data: `objectives[].progressThreshold/factionProgress` oraz `gameState.status.publicOptions/secretOptions` (postęp, gotowość). Test `test_every_status_objective_is_covered` pilnuje, by każdy cel z katalogu miał ewaluator.
- ⚠ ZAŁOŻENIE: 4 cele są **ręczne** (`MANUAL_OBJECTIVES`: `ancient_monuments`, `lost_outposts` — brak załączników planet w stanie; `dhw` — brak fragmentów reliktów; `dp` — brak praw w grze): silnik ich nie blokuje, operator potwierdza spełnienie. Pominięte uproszczenia AsyncTI4: zdolności modyfikujące liczenie (Xxcha hero/breakthrough, Keleres agent, Hacan `mc`, Nekro/Valefar, coexistence, Mirage/Nano-Forge, synergie technologii w `mlp`/`diversify`) oraz sąsiedztwo hyperlane.
- ⚠ ZAŁOŻENIE: setup rozdaje **1** tajny cel na gracza (bez wyboru „dobierz dwa, zachowaj jeden"); karty akcji nie są rozdawane w setupie — pierwsze dobiera się w pierwszej fazie statusu.
- ⚠ ZAŁOŻENIE: limit ręki kart akcji (7) i odrzucanie nadmiaru przed przetasowaniem talii nie są modelowane (krok 3); brak talii → dobór pomijany.
- ⚠ ZAŁOŻENIE: nadwyżka statków ponad fleet pool jest tylko **zgłaszana** (`status.fleet_excess`, ostrzeżenie w panelu) — usuwa się ją ręcznie (narzędzia planszy/God-Mode); nie blokuje zakończenia kroku 5.
- ⚠ ZAŁOŻENIE: „gotowy" lider po kroku 6 = stan `unlocked` (agenci); tajne cele fazy Akcji/Agendy nie są punktowane w statusie.
- ⚠ TODO: zdjęcie żetonu Custodians (6 influence + lądowanie na Mecatol Rex, +1 VP, `custodians_removed`) — do czasu integracji z inwazją ustawiane God-Mode (`custodians_removed` w `/god-mode/patch`); Imperial/Support for the Throne/relikty jako źródła VP; cele akcji/agendy punktowane poza statusem; remis-złamanie przy równoczesnym 10. VP.


---

## 42. Fleet pool: limit statków w systemie i usuwanie nadwyżki — ✅ ZWERYFIKOWANE (tirules2.com)

📎 tirules: [Fleet Pool](rules_tirules/R_fleet_pool.md) · [Capacity](rules_tirules/R_capacity.md) · [Command Sheet](rules_tirules/R_command_sheet.md)

- **Limit (R_fleet_pool):** liczba żetonów w puli floty (`PlayerState.fleet_cc`) = maks. liczba
  statków NIE-myśliwskich gracza w jednym systemie. Nie liczą się: myśliwce i siły naziemne (to
  capacity, RULES.md 39.6), jednostki na planetach, statki przewożone w ruchu. Struktur w
  przestrzeni (poza statkami) nie liczymy.
- **Wolno przekroczyć, trzeba usunąć:** statki WOLNO ruszyć / wyprodukować / postawić ponad pulę
  (ruch może też przejść przez zapchany system), ale nadwyżkę gracz wybiera i zwraca do rezerwy.
  Silnik więc NIE blokuje akcji, tylko (1) OSTRZEGA przed nią, (2) wymusza usunięcie po niej.
- **Implementacja:** `core/fleet_pool.py` — `fleet_report` (pula, statki, nadwyżka),
  `open_fleet_pool_check` (okno `WindowType.FLEET_POOL`, kolejka od aktywnego gracza),
  `resolve_fleet_pool` (usuń DOKŁADNIE nadwyżkę; tylko statki nie-myśliwskie), `auto_removal`
  (podpowiedź: najtańsze najpierw — ⚠️ ZAŁOŻENIE, wybór należy do gracza).
- **Kiedy sprawdzamy:** w `tactical.next_step` przed opuszczeniem kroku (po ruchu, produkcji,
  walce, Space Cannon) — zaraz po sprawdzeniu capacity. Krok zostaje, dopóki okno trwa. Koniec
  akcji taktycznej czyści okno. Endpointy: `GET /tactical/fleet-pool` (respondent okna ALBO
  aktywny gracz w aktywnym systemie — do ostrzeżeń), `POST /tactical/fleet-pool/resolve`.
- **UI:** `FleetPoolWarning` (pasek „N / pula", ostrzeżenie o nadwyżce) w oknie produkcji (liczy
  też statki z koszyka) i w panelu kroku ruchu; `FleetPoolModal` — wymuszone okno wyboru.
- **Faza statusu (krok 5, redystrybucja żetonów):** zmniejszenie puli floty może stworzyć nadwyżkę.
  Panel pokazuje `FleetPoolStatusMeter` (największa flota vs planowana pula, lista systemów do
  oczyszczenia; dane `status.fleetShips`). Po zatwierdzeniu `status_phase.advance_fleet_check`
  otwiera okno `FLEET_POOL` (kontekst `phase=status`) dla pierwszego systemu z nadwyżką; po jego
  zamknięciu — kolejny system/gracz. Kroki 6–7 (`finalize_status`) czekają, aż nadwyżek nie będzie.

⚠️ ZAŁOŻENIA / luki: (1) God-Mode (edit-units, drag&drop w trybie bez reguł) omija pulę — wentyl;
(2) sprawdzenie następuje przy zmianie kroku, nie „w każdej chwili" (np. nie w trakcie walki — tam
nadwyżka z efektów kart jest dozwolona do końca walki); (3) Myśliwce II liczone do capacity, nigdy
do puli (zgodnie z notą w R_fleet_pool); (4) faza statusu ma osobne `status_phase.fleet_excess`
(redystrybucja żetonów) — obie ścieżki mówią o tej samej regule.

---

## 43. Asymetria i wyjątki (frakcje, karty akcji, agendy): zasady architektury hooków — ⚠ ZAŁOŻENIE (decyzja projektowa, do potwierdzenia)

📎 tirules: [Abilities](rules_tirules/R_abilities.md) · [Modifiers](rules_tirules/R_modifiers.md) · [Action Cards](rules_tirules/R_action_cards.md) · [Agenda Phase](rules_tirules/R_agenda_phase.md) · [Agenda Card](rules_tirules/R_agenda_card.md)

Status: PLAN (nic z tej sekcji nie jest jeszcze w kodzie). Realizacja krok po kroku: `docs/PLAN_PELNA_ROZGRYWKA.md`, sekcja „Plan hooków i wyjątków (E7 + E4 + E6)".
To są zasady PROJEKTOWE (jak kodujemy wyjątki), nie reguły TI4. Treść konkretnych kart, zdolności
i agend wynika wyłącznie z assetów JSON, a reguły ich interakcji z tirules2.com (zasada z steering).

### 43.1. Zasady (obowiązują każdą implementację wyjątku)

1. **Reguła bazowa nie zna wyjątków.** W `core/` nie wolno pisać `if faction == ...`, `if card_id == ...`
   ani warunków na konkretną kartę/agendę/technologię. Reguła bazowa wywołuje PUNKT ZACZEPIENIA
   (hook point), a wyjątek rejestruje się osobno w `core/rules_hooks.py`.
2. **Wyjątek = rejestracja, nie edycja reguły.** Dodanie karty/frakcji = nowy wpis rejestru
   (źródło komponentu → punkt zaczepienia → funkcja) + wpis w RULES.md + test. Zero zmian w regule bazowej,
   chyba że brakuje punktu zaczepienia (wtedy dodajemy punkt, a nie obejście).
3. **Hooki są czystymi funkcjami** (`state, kontekst -> wynik/state`), bez I/O i HTTP, deterministyczne
   (losowość tylko przez seedowalny RNG silnika). Hook nie mutuje wejścia (klon jak reszta `core/`).
4. **Typy punktów zaczepienia (kategorie):**
   - `MODIFY` — zmienia liczbę/flagę w trakcie liczenia (ruch, rzut, koszt, limit, zasięg, wartość produkcji);
   - `PERMIT/FORBID` — rozszerza lub zawęża legalność akcji (walidacja → `ValueError` → 422);
   - `TRIGGER` — reakcja na zdarzenie silnika, otwiera OKNO czasowe (when/after/before/instead of);
   - `REPLACE` — „instead of": podmienia rozstrzygnięcie kroku (jawnie, z pierwszeństwem);
   - `PERSISTENT` — efekt trwały (prawo agendy, trwała karta), z wygaśnięciem (do końca fazy/rundy/gry).
5. **Kolejność i konflikty są jawne.** Wiele hooków na jednym punkcie ⇒ deterministyczna kolejność:
   najpierw REPLACE, potem FORBID, PERMIT, MODIFY (addytywne przed multiplikatywnymi), na końcu TRIGGER.
   Remis: kolejność inicjatywy / od aktywnego gracza zgodnie z ruchem zegara (jak okna, RULES.md 29.2).
   Reguła „zakaz wygrywa z pozwoleniem" (can't > can) — do potwierdzenia na tirules2 przy pierwszym konflikcie.
6. **Okna czasowe dla reakcji.** Każdy hook typu TRIGGER działa przez `core/timing.py` (kolejka graczy),
   a nie własną ścieżką. Klasyfikacja wyzwalacza = `timing_spec.py` (RULES.md 34).
7. **Brak hooka ≠ błąd.** Komponent bez implementacji jest „martwy" i oznaczony w `effects_registry`
   (`NOT_IMPLEMENTED`); silnik wtedy NIE zgaduje, tylko oddaje decyzję operatorowi (`MANUAL`, God-Mode)
   i jasno to komunikuje w UI. Status `IMPLEMENTED` wolno ustawić dopiero, gdy jest hook + wpis w RULES + test.
8. **Źródło prawdy o treści:** tekst karty/zdolności z assetów JSON; doprecyzowania z tirules2.com
   (`docs/rules_tirules/`). Nigdy z pamięci. Każdy hook ma w RULES.md: komponent, tekst (lub id w assetach),
   punkt zaczepienia, timing, źródło, status ✅/⚠.
9. **Dane bez zmian:** wartości liczbowe (jednostki, koszty, tech) dalej tylko przez `StaticDataRegistry`;
   hook modyfikuje wynik, nie duplikuje statystyk.
10. **Wyjątki testujemy parami:** test „bez wyjątku → reguła bazowa" oraz „z wyjątkiem → zmieniony wynik".
    Dodatkowo test regresji: rejestr pusty ⇒ zachowanie identyczne jak przed wprowadzeniem hooków.
11. **God-Mode omija hooki** tak samo jak reguły (RULES.md 29) — to wentyl. Zdarzenie z God-Mode nie odpala TRIGGER-ów.
12. **Podział tematyczny zamiast jednego wielkiego pliku.** Hooki grupujemy per temat (`hooks/factions_*.py`,
    `hooks/action_cards.py`, `hooks/agendas.py`), rejestr w jednym miejscu. Rozmiar pliku jest miękką
    wskazówką (zwykle do ~500 linii spójnego modułu), a decyduje spójność tematyczna, nie sama liczba linii.

### 43.2. Kolejność wdrażania (uzasadnienie)

1. **Najpierw mechanizm, potem treść.** Szkielet `rules_hooks` + punkty zaczepienia w istniejących regułach
   (ruch, walka, produkcja, status, okna), przeniesienie wyjątku Arborec z `production.py` jako pierwszy
   przypadek testowy. Powód: bez szkieletu każdy z ~30 wyjątków frakcji i setek kart wymusiłby edycję reguł bazowych.
2. **Raport pokrycia** na bazie `effects_registry` + `timing_spec`: ile komponentów trafia w który punkt
   zaczepienia ⇒ priorytet = punkty obsługujące najwięcej komponentów.
3. **Karty akcji** (jednolity schemat: timing + efekt) — pierwszy duży test szkieletu.
4. **Frakcje**: najpierw proste (modyfikatory liczb/legalności), na końcu te łamiące strukturę gry
   (np. Nekro, Creuss, Mahact, Naalu, Yssaril, Titans, Cabal, Obsidian, Firmament).
5. **Agendy** na końcu: wymagają działającej fazy agendy (głosowanie) i trwałych praw (`PERSISTENT`).
6. Długi ogon kart bez hooka zostaje `MANUAL` (God-Mode) — świadomy kompromis, nie dług do ukrycia.

### 43.3. ⚠ ZAŁOŻENIA / do potwierdzenia przez użytkownika

- ⚠ ZAŁOŻENIE: pięć typów punktów zaczepienia (43.1 pkt 4) i kolejność rozstrzygania (pkt 5) to propozycja
  projektowa; po napotkaniu realnego konfliktu kart zweryfikować na tirules2.com (`R_abilities`, `R_modifiers`).
- ⚠ ZAŁOŻENIE: komponent bez hooka ⇒ `MANUAL` (operator rozstrzyga), zamiast blokować grę. Alternatywa:
  twarde blokowanie zagrania nieobsługiwanej karty — decyzja użytkownika.
- ⚠ ZAŁOŻENIE: kolejność wdrażania w 43.2 (karty akcji → frakcje proste → frakcje złożone → agendy).
- ⚠ TODO: faza agendy nie ma jeszcze osobnego modułu `core/` (głosowanie, prawa) — warunek wstępny dla agend.

### 43.4. Reakcje gracza i przycisk STOP (model przerwania) — ⚠ ZAŁOŻENIE (decyzja projektowa, do potwierdzenia)

To zasada projektowa (jak silnik daje szansę na reakcję), nie reguła TI4. Dotyczy kart i zdolności
zagrywanych „w reakcji" (when / after / before / instead of — klasyfikacja w `timing_spec.py`, RULES.md 34).
Cel: nie pytać każdego gracza po każdej akcji „czy zagrywasz kartę?" i jednocześnie nie ujawniać,
kto ją ma. Odwzorowuje grę przy stole: „stop, zanim to się stanie, gram kartę".

**Trzy warstwy (obowiązują łącznie):**
1. **Filtr po informacji JAWNEJ.** Gracza nie pytamy, gdy z danych publicznych wynika, że nie może
   zareagować (np. 0 kart akcji w ręce; liczba kart akcji jest jawna). Filtr NIGDY nie korzysta z treści ręki
   ani z żadnej informacji ukrytej, więc jego działanie nie ujawnia, kto ma kartę.
2. **Boty decydują wewnętrznie.** Silnik odpytuje bota bez udziału UI. Interfejs pokazuje coś dopiero,
   gdy bot faktycznie zagra kartę. Bot niereagujący nie wydłuża gry ani nie zdradza stanu ręki.
3. **Człowiek ma przycisk STOP.** Krok akcji stosuje się od razu (optymistycznie). Silnik pamięta stan
   sprzed ostatniego kroku. STOP przywraca ten stan, otwiera okno czasowe z zatrzymującym graczem
   jako pierwszym respondentem (reszta w kolejności okien, RULES.md 29.2), a po rozstrzygnięciu
   wznawia przerwaną akcję. STOP używa tej samej maszynerii co okna (`core/timing.py`), nie osobnej ścieżki.

**Punkty kontrolne i granica nieodwracalności:**
- Każdy krok akcji, na który może zareagować jakaś karta/zdolność, jest PUNKTEM KONTROLNYM
  (wyznacza go `timing_spec`). STOP cofa wyłącznie do ostatniego punktu kontrolnego, nie całą akcję.
- STOP działa tylko do najbliższego punktu NIEODWRACALNEGO: rzut kośćmi, ujawnienie karty,
  dobranie z talii (informacja ukryta lub losowa). Po nim cofanie jest zablokowane. Powód: zapobiega
  używaniu wiedzy z przyszłości (zobaczenie wyniku rzutu i dopiero potem STOP). Przy stole odpowiada temu
  reguła „mów przed rzutem". Naturalny punkt w UI: przycisk „Rzuć".
- Wyniki losowe są zapisane (seedowalny RNG, memory: kości po stronie silnika), więc cofnięcie przed
  rzutem nie pozwala go przerzucić.
- Po zagraniu karty z STOP przerwany krok wznawia się od tego samego punktu kontrolnego, z uwzględnieniem
  efektu karty (hook typu REPLACE/MODIFY, 43.1). Jeśli karta anuluje krok („instead of"), krok się nie wykonuje.

**Mechanizm cofania (istniejący kod):** `core/event_store.py` trzyma stos migawek stanu z `goto(seq)`
i `undo()`/`redo()`. Silnik opiera się na `state -> state`, więc „stan sprzed kroku" już istnieje. Nowe jest
wyłącznie oznaczanie migawek jako punktów kontrolnych/nieodwracalnych oraz blokada cofania poza punktem kontrolnym.
UWAGA: zwykłe Undo operatora (God-Mode, historia) jest czym innym niż STOP i dalej nie podlega tym ograniczeniom.

**⚠ ZAŁOŻENIA / do potwierdzenia przez użytkownika:**
- ⚠ ZAŁOŻENIE: STOP działa do rzutu kośćmi / ujawnienia karty / dobrania z talii (granica nieodwracalności).
- ⚠ ZAŁOŻENIE: cofamy jeden krok do ostatniego punktu kontrolnego, nie całą akcję.
- ⚠ ZAŁOŻENIE: filtr jawny = tylko liczba kart akcji w ręce i fakt posiadania właściwego typu komponentu
  (jawnego). Szerszy filtr wymaga potwierdzenia, że niczego nie ujawnia.
- ⚠ TODO (tryb sieciowy): przy grze sieciowej STOP musi mieć krótki, jednolity timer niezależny od zawartości
  ręki, inaczej sama obecność pauzy zdradza posiadanie karty. Hot-seat i solo vs boty tego nie wymagają.
- ⚠ TODO: ujawnienie informacji przez samą zmianę zachowania UI (np. szybsze/wolniejsze przejście kroku)
  należy testować — kroki dla graczy z kartą i bez karty mają wyglądać identycznie.

---

## 44. Gra sieciowa (do 6 graczy): tożsamość, autoryzacja, widoczność, zasada `actor_id` — ⚠ ZAŁOŻENIE (decyzja projektowa, do potwierdzenia)

📎 tirules: [Active Player](rules_tirules/R_active_player.md) · [Initiative Order](rules_tirules/R_initiative_order.md) · [Speaker](rules_tirules/R_speaker.md) · [Transactions](rules_tirules/R_transactions.md)

Status: PLAN (poza `actor_id` w punkcie 44.1 nic nie jest jeszcze w kodzie). To są zasady PROJEKTOWE
(architektura sieci), nie reguły TI4. Etap realizacji: `docs/PLAN_PELNA_ROZGRYWKA.md`, sekcja „Etap sieciowy (N)".
Cel: partia do 6 graczy przez sieć (ludzie + boty), obok trybów solo vs boty i hot-seat (steering: tryby gry).

### 44.1. Zasada `actor_id` (OBOWIĄZUJE JUŻ TERAZ dla każdego nowego endpointu akcji)

- Każda akcja gracza (nie God-Mode) w `api/` przyjmuje jawne `actor_id` — kto ją wykonuje — i przekazuje je do `core/`.
  Dziś może to być zaufane (hot-seat/solo), ale pole MUSI istnieć, żeby późniejsza autoryzacja nie wymagała
  zmiany sygnatur w kilkudziesięciu endpointach.
- `core/` waliduje `actor_id` względem stanu gry (jest to gracz aktywny, respondent bieżącego okna albo gracz
  uprawniony do danej akcji), tak jak już robi to dla `player_id` (np. `component_action`, RULES.md 31). Nie wolno
  zakładać, że „klient jest uczciwy".
- `core/` pozostaje nieświadome sieci: nie zna sesji, tokenów, WebSocketów ani HTTP. Zna wyłącznie `player_id`.
- Akcje God-Mode (`/god-mode/*`, `core/board_edit.*`) mają osobne uprawnienie (operator/host), nie `actor_id` gracza.

### 44.2. Tożsamość i autoryzacja (warstwa `api/`)

- Każde miejsce przy stole ma token (np. link zaproszenia). Token mapuje się na `player_id`; to `api/` ustala `actor_id`
  z tokenu, a NIE z treści żądania ani parametru w URL.
- **Widok (`viewing_player`) nie może być parametrem swobodnie wybieranym przez klienta** w trybie sieciowym —
  dziś jest on parametrem zapytania (RULES.md 6/web-data), co w sieci pozwalałoby podejrzeć cudzą rękę. W trybie sieciowym
  perspektywa wynika z tokenu; w hot-seat/solo zostaje jak dotychczas.
- Rola `host` (tworzy grę, God-Mode, odtwarza po awarii) i rola `observer` (bez rąk, tylko jawne informacje) —
  ⚠ ZAŁOŻENIE do potwierdzenia.
- Błędy autoryzacji mapowane w `api/` (nie w `core/`) na 401/403; błędy reguł jak dotąd 422.

### 44.3. Widoczność per gracz (używa istniejącego `core/visibility.py`)

- Każde połączenie WebSocket dostaje WŁASNĄ projekcję stanu (`project_for_viewer`), nigdy wspólny broadcast pełnego stanu.
  Obecny `broadcast_map` (jedna wiadomość do wszystkich) wolno stosować wyłącznie do danych w pełni jawnych.
- Zasada: serwer wysyła klientowi tylko to, co klient wolno zobaczyć. Ukrycie po stronie UI NIE jest zabezpieczeniem.
- Zdarzenia (np. „zagrano kartę", wynik rzutu) mają typ jawny/prywatny; prywatne trafiają tylko do uprawnionych.
- Test obowiązkowy dla każdej nowej wiadomości: nie ujawnia cudzych kart, tajnych celów ani liczb innych niż jawne
  (por. 43.4: zachowanie z zewnątrz nie może zdradzać zawartości ręki).

### 44.4. Pokoje, trwałość i współbieżność

- Wiele gier naraz: identyfikator gry (`game_id`) w stanie serwisu; dziś stan jest w pamięci jednego procesu i
  restart backendu kasuje partię. Docelowo zapis (`EventStore` na dysku) i wznowienie po restarcie.
- Akcje w jednej grze są serializowane (jedna blokada na grę); dwie akcje naraz nie mogą się przeplatać.
- Idempotencja: powtórzone żądanie (ponowne kliknięcie, retry po zerwaniu) nie może wykonać akcji dwa razy
  (numer migawki/`seq` w żądaniu lub klucz idempotentności) — ⚠ ZAŁOŻENIE co do mechanizmu.
- Klient po ponownym połączeniu pobiera pełny aktualny stan (własną projekcję), zamiast dogrywać zdarzenia.

### 44.5. Interakcje równoległe i nieobecni gracze

- Okna czasowe (RULES.md 29.2) już pytają graczy po kolei; w sieci UI pokazuje „czekamy na gracza X".
  Tam, gdzie reguły pozwalają, by kilku graczy działało jednocześnie (np. wybory bez wpływu na siebie nawzajem),
  rozważyć odpowiedzi równoległe — ⚠ ZAŁOŻENIE, do decyzji po zbadaniu każdego przypadku w tirules2.
- Rozłączenie / brak odpowiedzi: timeout okna → przejęcie decyzji przez bota (poziom trudności z RULES.md 36)
  albo pas — ⚠ ZAŁOŻENIE do potwierdzenia przez użytkownika.
- STOP (43.4) w sieci wymaga jednolitego timera niezależnego od zawartości ręki; w hot-seat i solo nie dotyczy.

### 44.6. ⚠ ZAŁOŻENIA / do potwierdzenia przez użytkownika

- ⚠ ZAŁOŻENIE: token na miejsce przy stole (link zaproszenia) jako mechanizm tożsamości; role host/observer.
- ⚠ ZAŁOŻENIE: projekcja per połączenie (push zmian) zamiast pobierania całości co chwilę (polling).
- ⚠ ZAŁOŻENIE: timeout i przejęcie przez bota/pas przy nieobecnym graczu.
- ⚠ TODO: nie sprawdzono jeszcze, które istniejące endpointy akcji przyjmują identyfikator gracza i które
  go walidują; audyt przed etapem N (lista endpointów bez `actor_id`).

## 45. Setup startowy: tajne cele, notki, żeton Custodians, cele publiczne — ✅ ZWERYFIKOWANE (tirules2.com) + ⚠ ZAŁOŻENIA

Źródło: `rules_tirules/R_objective_cards.md`, `R_mecatol_rex.md`, `R_custodians_token.md`, `R_promissory_notes.md`. Kod: `core/game_setup.py`, `api/routers/setup.py`, `api/web_setup.py`, UI `frontend/src/domains/setup/GameSetupOverlay.tsx`.

### 45.1. Reguły
- (S1) Gra ma po **pięć** celów publicznych I i II etapu, zakrytych; mówca odkrywa **dwa cele I etapu** (R_objective_cards). Pozostałe osiem leży zakryte do fazy statusu.
- (S2) Żeton Custodians jest w setupie położony na Mecatol Rex (R_mecatol_rex). Zdjęcie: RULES.md 41 / R_custodians_token.
- (S3) Każdy gracz zaczyna z jedną ręką promissory notes: **5 wspólnych** (szablony `<color>_*` z katalogu: Ceasefire, Political Secret, Support for the Throne, Trade Agreement, Alliance) w kolorze gracza + **1 frakcyjna** (`faction.promissory_notes`).
- (S4) Każdy gracz zaczyna z jednym tajnym celem (R_objective_cards).
- (S5) Żetony frontier (R_frontier_tokens): w setupie **jeden** żeton w każdym systemie **bez planet** — pusta przestrzeń, anomalie bez planet, wormhole, a także **Creuss Gate** (17) i **The Sorrow** (94). **Nie** na kafelkach hyperlane. Najwyżej jeden żeton na system.

### 45.2. ⚠ ZAŁOŻENIE (decyzja użytkownika)
- Zrzut tirules mówi „każdy zaczyna z jednym tajnym celem" i nie opisuje doboru. Wg decyzji użytkownika każdy gracz **dobiera 2 tajne cele, zatrzymuje 1, a drugi wraca do talii (talia tasowana)** — tak jak w instrukcji planszówki. Stąd etap `SECRETS`.

### 45.3. Implementacja
- `GameState.setup: SetupState | None` (`stage` ∈ `SECRETS|CUSTODIANS|OBJECTIVES`, `secrets_chosen`, `custodians_placed`); `None` = setup zakończony (też dla stanów spoza `/game/new`).
- `PlayerPrivateState.secret_candidates` — dwa dobrane cele (prywatne; redakcja widoczności działa automatycznie).
- `objectives.setup_objectives(..., interactive=True)`: 5+5 zakrytych, 2 kandydaci na gracza; tryb domyślny (testy) zachowany.
- `/game/new` → `begin_setup` (talie, ręka notek, boty wybierają losowo). Kolejka wyboru = kolejność zasiadania; `active_player_id` = wybierający, potem mówca.
- Endpointy: `POST /setup/secret`, `/setup/custodians` (tylko mówca), `/setup/reveal-objectives` (tylko mówca; kończy setup i oddaje turę pierwszemu wybierającemu kartę strategii).
- `strategy_phase.pick_strategy_card` odrzuca wybór karty, dopóki `state.setup` nie jest `None` (silnik-sędzia).
- web-data: `gameState.setup`; żeton Custodians jako token planety `mr` pod kluczem `neutral`, dopóki leży na planszy (`web_setup.custodian_on_board`).
- Frontier: `SystemState.frontier_token: bool`; `game_setup.place_frontier_tokens(state, grid, registry)` wołane w `/game/new` (systemy z rejestru bez `planets`, z pominięciem nazwy „Hyperlane"). web-data: token `frontier` w `space` pod kluczem `neutral`. Zdjęcie żetonu przez eksplorację (Dark Energy Tap) — do zrobienia w RULES.md 46.
- UI: pełnoekranowe okno z bramką „przekaż ekran" przed pokazaniem tajnych celów (hot-seat); w grze sieciowej backend ma wysyłać kandydatów tylko ich właścicielowi (RULES.md 44).

---

## 46. Eksploracja planet po przejęciu kontroli — ✅ ZWERYFIKOWANE (tirules2.com) + ⚠ ZAŁOŻENIA

📎 tirules: [Exploration](rules_tirules/R_exploration.md) · [Exploration Cards (noty)](rules_tirules/C_exploration_cards.md) · [Attach](rules_tirules/R_attach.md) · [Control](rules_tirules/R_control.md) · [Relics](rules_tirules/R_relics.md) · [Frontier Tokens](rules_tirules/R_frontier_tokens.md)

Kod: `core/exploration.py`, `api/routers/exploration.py`, `api/schemas_exploration.py`; UI `frontend/src/domains/exploration/`. Karty (typ, treść, rozstrzygnięcie) wyłącznie z katalogu komponentów (`ComponentCategory.EXPLORATION`).

### 46.1. Reguły

- (X1) Gracz, który przejmuje planetę NIEkontrolowaną przez nikogo, ją **eksploruje**: dobiera i rozstrzyga kartę z talii odpowiadającej cesze planety (cultural / hazardous / industrial). Planeta bez cechy (Mecatol Rex, planety domowe, stacje) nie podlega eksploracji.
- (X2) Planeta z kilkoma cechami → gracz wybiera talię. Kilka planet naraz → gracz wybiera kolejność; każda karta jest rozstrzygana W CAŁOŚCI przed następną. Karta jest ujawniana wszystkim przed rozstrzygnięciem.
- (X3) Rozstrzygnięcie: gracz czyta kartę, podejmuje decyzje, wykonuje efekt. Karta inna niż fragment reliktu i attach trafia na stos odrzuconych swojej talii; karta purge'ująca się (żetony wormhole) NIE trafia na stos odrzuconych. Pusta talia → stos odrzuconych tasuje się w nową talię.
- (X4) Karta z nagłówkiem „attach" zostaje przy planecie (też po zmianie kontroli — R_attach). Karta „relic fragment" leży jawnie w strefie gracza (można je wymieniać w transakcjach — RULES.md 47).
- (X5) Limit commodities: gracz nie może mieć więcej niż commodity value (noty Abandoned Warehouses / Functioning Base / Local Fabricators).

### 46.2. Model i implementacja

- `GameState.exploration: ExplorationState | None` (`player_id`, `position`, `queue`, `current`, `log`) — okno otwiera się w `invasion._establish_control` dla planet z `result["explore"]` (przejęta, bez poprzedniego właściciela, z cechą). Karta dobierana jest **automatycznie**, gdy nie ma wyboru (jedna planeta w kolejce, jedna cecha); inaczej gracz wybiera planetę (kolejność) i talię (`exploration.draw`).
- Talie: `DecksState.exploration_deck/_discard` (klucz = nazwa talii), zasiewane LENIWIE przy pierwszym dobraniu (`next_rng` — seedowalne, Undo-safe). `GameState.planet_attachments {planeta: [karta]}`, `PlayerState.relic_fragments [karta]` (JAWNE).
- Rozstrzygnięcie: `exploration.options_for` (opcje z flagą `enabled` i powodem) → `exploration.resolve(opcja, param)`; zamknięcie okna: `exploration.finish` (dopiero przy pustej kolejce i braku ujawnionej karty).
- Blokady: `invasion.advance` z ESTABLISH, `tactical.next_step` i `tactical.end_action` → 422, dopóki trwa eksploracja. God-Mode (`end_tactical_action`, `set_step`) czyści okno.
- API: `GET /exploration`, `POST /exploration/{draw, resolve, finish}`; sygnał `gameState.activeExploration` w web-data.
- Skutki zautomatyzowane: Freelancers (produkcja, X7), Gamma Wormhole (żeton, X8), Mercenary Outfit (piechota), Volatile Fuel Source (żeton do wybranej puli), Expedition (ready), Core Mine (TG), Abandoned Warehouses, Functioning Base (dobranie karty akcji), Local Fabricators (mech), wszystkie attach (w tym Demilitarized Zone: struktury znikają, siły naziemne wracają na orbitę) i fragmenty reliktów.

### 46.3. ⚠ ZAŁOŻENIA / TODO

- (X6) **Statystyki z attachmentów** — `core/planet_stats.py` jest JEDYNYM źródłem zasobów, wpływów i specjalności technologicznych planety po attachmentach (modyfikatory z danych `AttachmentDef`). Czytają stąd: płatność i budżet produkcji, wartość PRODUCTION doku (`zasoby planety + N`), cele (postęp, płatność, „tech skip"), ekonomia gracza w web-data. Research Facility: planeta dostaje specjalność; jeśli już jakąś ma → zasoby i wpływy +1 ZAMIAST. Dane potrafią dublować specjalność (np. tiamat) — liczy się jedna. Kod spoza `planet_stats` NIE czyta `registry.planets[..].resources` wprost.
- (X7) **Freelancers**: opcja „produce" otwiera `GameState.production_grant` (1 jednostka w aktywnym systemie, wpływ liczy się jak zasoby — nota: planeta płaci zasobami ALBO wpływem, więc wartość = max). To okno produkcji (to samo co w kroku PRODUCTION) poza tym krokiem: limit z karty zamiast wartości PRODUCTION, bez doków, blokada statków w systemie z obcymi statkami nadal działa, siły naziemne na planety gracza w systemie albo do przestrzeni. Nie zużywa limitu kroku PRODUCTION. Eksploracja (kolejna karta, „Done") czeka na produkcję lub rezygnację (`POST /tactical/production/skip-grant`).
- (X8) **Gamma Wormhole**: karta kładzie `SystemState.wormhole_tokens += ["GAMMA"]` i jest purge'owana. `HexGrid.sync_token_wormholes` łączy wszystkie systemy z takim żetonem (obok wbudowanych wormholi); kontekst API synchronizuje mapę ze stanem przy KAŻDYM odczycie `current_grid`, więc Undo/Redo zdejmuje żeton także z grafu. Cele (`View.wormholes`) i mapa (token `gamma` w przestrzeni, web-data) widzą go jak wbudowany.
- ⚠ ZAŁOŻENIE: przy braku mecha / piechoty w rezerwie opcja jest niedostępna (reguła pozwala zdjąć jednostkę z planszy z systemu bez własnego żetonu — niezaimplementowane).
- ⚠ ZAŁOŻENIE: wszystkie przejęte planety są już kontrolowane w chwili eksploracji (reguła: wiele planet w systemie → „zdobądź i eksploruj po kolei"); wpływa tylko na Freelancers, który i tak jest ręczny.
- ⚠ TODO: eksploracja frontier (Dark Energy Tap, żetony frontier, Enigmatic Device, Ion Storm), „explore" jako osobny efekt kart/zdolności, relikty (rozstrzyganie fragmentów), Dead World / Entropic Field i inne karty spoza bazowego PoK, handel w oknie po ujawnieniu karty (transakcje — RULES.md 47).

### 46.4. Stosy kart (talia / odrzucone / purge) i narzędzia debug

- (X9) Każda karta jest w JEDNYM miejscu: w talii, na stosie odrzuconych swojej talii, na wspólnym stosie purge (`DecksState.purged`), w ręce/strefie gracza (fragmenty reliktów), przyczepiona do planety albo właśnie ujawniona. Dobrana karta znika z talii; karta purge'owana (żeton wormhole) NIE trafia na stos odrzuconych i nie wraca przy tasowaniu.
- (X10) Panel General (Card pool) pokazuje stan talii z `cardPool`: liczba kart, które ZOSTAŁY w talii eksploracji (cultural / hazardous / industrial / frontier) i kart akcji, stosy odrzuconych per talia oraz jeden stos purge. Listy kart w talii są wysyłane POSORTOWANE (nie zdradzają kolejności). Szansa dobrania karty = kopie karty / karty w talii (liczona na froncie).
- (X11) **Debug** (`core/deck_piles.move_card`, `POST /decks/move`, God-Mode — omija reguły): przenosi kartę między talią / odrzuconymi / purge. Cel `top` = wierzch talii, czyli ustawienie, jaka karta będzie dobrana jako NASTĘPNA; `deck` = w losowe miejsce. Przełącznik „Debug" w oknie talii (pamiętany w localStorage). Wierzch talii (`cardPool.exploreTop`) jest widoczny tylko w trybie debug.
- ⚠ ZAŁOŻENIE: talie relikwii, agend i celów nie śledzą jeszcze stosów (relikty nie mają talii w stanie gry); talia kart akcji pokazuje pełną pulę, dopóki gra nie przejdzie przez setup.

---

## 47. Transakcje między graczami + żetony długu (debt) — ✅ ZWERYFIKOWANE (tirules2.com) + ⚠ ZAŁOŻENIA

Źródło: `docs/rules_tirules/R_transactions.md`, `R_commodities.md`, `R_promissory_notes.md`,
`R_relics.md`, `R_neighbors.md` (tirules2.com).

### 47.1 Reguła (zaimplementowana: `core/transaction.py`, `POST /transactions/resolve`)
- W swojej turze aktywny gracz może rozstrzygnąć **do jednej transakcji z każdym sąsiadem**
  (RULES.md 2 — sąsiedztwo z `neighbors_of`), w dowolnym momencie tury, także w trakcie walki
  → brak blokady oknem czasowym i brak wpływu na `took_action_this_turn` (to nie akcja).
- Gracz oddaje dowolną liczbę **trade goods i commodities** oraz maks. **jedną promissory note
  z ręki**; w zamian dostaje dowolną liczbę TG, commodities i **fragmentów reliktów** oraz
  maks. jedną promissory note. Transakcja nie musi być równa (można dawać za darmo).
- **Commodity oddana innemu graczowi staje się u odbiorcy trade goodem** (R_commodities).
- Promissory notes w strefie gracza (`promissory_notes_in_play`) nie podlegają wymianie;
  relikty same — też nie (tylko fragmenty).
- Utrata i ponowne uzyskanie sąsiedztwa w tej samej turze nie daje drugiej transakcji →
  `PlayerState.transacted_with` (lista partnerów), zerowana razem z `took_action_this_turn`.
- Pusta transakcja jest odrzucana (wybór projektowy — nic do wymiany, nie zużywa limitu).
- Po rozstrzygnięciu nie ma cofnięcia poza Undo silnika (zgodnie z „nie da się cofnąć").

### 47.2 Poza zakresem (jeszcze)
- ⚠️ **Hacan**: może wymieniać też karty akcji — hook w E7 (`rules_hooks`), nie `if faction`.
- ⚠️ Zwrot **pojmanych jednostek** w ramach transakcji (po wdrożeniu Capture).
- ⚠️ **Agenda**: transakcja z KAŻDYM graczem bez sąsiedztwa przy każdej agendzie (agendy
  jeszcze nie ruszamy). Funkcja `resolve_transaction` wymaga dziś fazy akcji + sąsiedztwa.
- ⚠️ Zgoda partnera nie jest modelowana: operator (hot-seat) składa obie strony umowy w jednym
  oknie; zgoda sieciowa/bota dojdzie z oknami czasowymi (RULES.md 29).

### 47.3 Żetony długu (debt) — ⚠️ NIEOFICJALNA ZASADA STOŁU (decyzja użytkownika)
Nie ma jej w regułach TI4. Gracze zwyczajowo oddają sobie małe żetony kontroli jako niewiążące
obietnice/długi (3 TG do zapłaty = 3 żetony wystawcy). Silnik tylko **zapamiętuje** kto ma czyje
żetony (`GameState.debt_tokens = {holder: {issuer: n}}`, `core/debt.py`,
`POST /debt/give`, `/debt/return`) — niczego nie egzekwuje. Działa **bez sąsiedztwa**,
w dowolnej fazie i turze. Wierzyciel zwraca żetony wystawcy, gdy dług spłacony/odpuszczony.
