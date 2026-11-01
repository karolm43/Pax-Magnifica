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
| 3 | [Ruch (Movement)](#3-ruch-movement---do-zrobienia-warstwa-logiki-ruchu-późniejsza-faza) | ⬜ | [Movement](rules_tirules/R_movement.md) |
| 3 (bis) | [Limity sztuk jednostek (supply caps)](#3-limity-sztuk-jednostek-plastic--supply-caps---zweryfikowane) | ✅ | [Reinforcements](rules_tirules/R_reinforcements.md) |
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
4. `startingTech`, `commodities` ustawiane na stanie gracza.

**Grafiki jednostek:** `assets/units/<kolor>_<asyncId>.png`. UWAGA: `asyncId` ≠ kod
`startingFleet` (np. cruiser: `asyncId=ca`, kod fleet=`cr`). Mapowanie przez `baseType`.

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

## 3. Limity sztuk jednostek (plastic / supply caps) — ✅ ZWERYFIKOWANE

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
  - **3–4 graczy → 2 karty/gracz** (gra przewiduje DRUGĄ rundę wyboru, patrz niżej),
  - **5–8 graczy → 1 karta/gracz**,
  - **liczba graczy < 3 lub > 8 → NIEOBSŁUGIWANA (błąd).** Silnik odrzuca ustalenie
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

Keleres (3 warianty) ma `startingTech=[]` i brak opcji — startuje bez technologii (celowo).
Implementacja: `faction_setup.resolve_starting_tech` (walidacja liczności i dozwolonych
opcji) + wybór przekazywany przez `starting_tech` w żądaniu setupu/nowej gry; UI pokazuje
menu wyboru N z listy, gdy `startingTechAmount > 0`.

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
Jednostkę naziemną/strukturę upuszczoną na orbitę front odrzuca (brak sensownej planety-celu).
Backend i tak waliduje twardo — to tylko wygodne mapowanie gestu na dozwoloną strefę.

Implementacja: `unit_catalog.placement_allows_zone`/`zone_is_space`, `board_edit.move_units`
(walidacja), frontend `useUnitDrag` (mapowanie statek→orbita, podświetlenie dozwolonego celu).


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

### 31.1. Aktywny gracz istnieje TYLKO w fazie akcji — ✅ ZWERYFIKOWANE

- „The active player is the player taking a turn during the action phase." Oraz wprost:
  „During the strategy, status and agenda phases, NO player is the active player."
- **Wniosek dla kodu (KORYGUJE wcześniejszy zamysł T4):** NIE wprowadzamy sztucznego
  „aktywnego gracza" w STATUS/AGENDA. `active_player_id` jest ustawiony tylko w ACTION
  (i chwilowo w STRATEGY jako „kto wybiera" — nasza konwencja, RULES.md 24). W STATUS/AGENDA
  `active_player_id` pozostaje `None`; kolejność czynności to KOLEJKA (patrz 31.3), nie „tura".

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
  (initiative albo speaker order) zamiast `active_player_id`. T4 kładzie tylko fundament:
  `active_player_id` pozostaje None w tych fazach, a `turn_flow` dostarcza `initiative_order`
  (= `turn_order`) jako kolejność dla statusu.

**Status wdrożenia:**
- ✅ T4: `active_player_id` None w STATUS/AGENDA (potwierdzone regułą); walidacja end_turn/pass_turn
  (faza, aktywny gracz, pas dopiero po akcji strategicznej); God-Mode omija.
- ⬜ Realne kroki statusu (punktowanie, odświeżanie) — etap E5, użyją initiative order.
- ⬜ Realne głosowanie agendy — etap E6, użyje speaker order (kolejka jak okno czasowe).

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

**Status:** ✅ T5 ruch statków z walidacją R1–R6 (pojedynczy stos). ⬜ transport/capacity,
⬜ wybór trasy pod gravity rift, ⬜ ruch zdolnościami — rozbudowa.

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
⬜ realne wydawanie zasobów (wyczerpanie planet/TG), ⬜ component limitations (rezerwy) — rozbudowa.
