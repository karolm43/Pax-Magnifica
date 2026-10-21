# Zweryfikowane reguły Twilight Imperium 4 (źródło prawdy dla kodu)

Ten plik jest **jedynym źródłem prawdy** dla reguł TI4 implementowanych w kodzie.
Zasada projektu (spec 5.1): żadna reguła ani statystyka nie jest kodowana z pamięci.
Każda reguła poniżej ma odniesienie do oficjalnego źródła.

Status weryfikacji każdej reguły:
- ✅ **ZWERYFIKOWANE** — potwierdzone w oficjalnym Living Rules Reference (LRR) / wiki.
- ⚠️ **ZAŁOŻENIE** — zakodowane tymczasowo, wymaga potwierdzenia przez znającego grę.
- ⬜ **DO ZROBIENIA** — reguła jeszcze niezaimplementowana.

**Główne źródła:**
- Living Rules Reference 2.0 (Prophecy of Kings), FFG, 09/2020 —
  [PDF](https://images-cdn.fantasyflightgames.com/filer_public/51/55/51552c7f-c05c-445b-84bf-4b073456d008/ti10_pok_living_rules_reference_20_web.pdf)
- TI Wiki (odzwierciedla LRR): https://twilight-imperium.fandom.com/wiki/Anomalies

> Uwaga: wszystkie reguły mogą być nadpisane przez karty i zdolności specjalne
> (frakcje, technologie, karty akcji). To obsługujemy przez `rules_hooks` (asymetria).

---

## 1. Anomalie (Anomalies)

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

- Systemy są sąsiednie, jeśli przylegają do siebie na mapie (6 krawędzi heksa).
- Systemy zawierające **wormhole tego samego typu** (Alpha, Beta, Gamma, Delta...)
  są traktowane jako **sąsiednie** wzajemnie.
- Hyperlanes (kafelki `hl_*`, pozycje `frac*`) tworzą nieliniowe połączenia —
  ⬜ DO ZROBIENIA (obecnie liczymy tylko geometrię + wormhole).
- Źródło: TI Wiki /wiki/Movement; `assets/positions/tileAdjacencies.properties`.

---

## 2a. Map string i pozycje planszy (AsyncTI4) — ✅ ZWERYFIKOWANE

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

Źródło (nie z pamięci): AsyncTI4 bot, `Player.java` wartości domyślne:
`private int tacticalCC = 3; private int fleetCC = 3; private int strategicCC = 2;`.
Czyli start gry: **3 taktyczne, 3 floty, 2 strategiczne** żetony na arkuszu.
Zakodowane w `src/core/game_state.py` → `PlayerState` (`tactical_cc`, `fleet_cc`,
`strategic_cc`). Zasilają panele gracza (CCPool) i heks stat-area (drugi heks).

⚠️ ZAŁOŻENIE: `cc_reinf = 8` (rezerwa w szkole dowodzenia). TI4 ma 16 żetonów łącznie,
8 na starcie na arkuszu → 8 w rezerwie. Do potwierdzenia dokładnej liczby/źródła.

## 6. Fazy gry — mapowanie na format frontendu — ✅ (format), ⬜ (logika)

Frontend (`GamePhase` w `entities/data/types.ts`) używa stringów małymi literami z
podfazami: `strategy`, `action`, `status.scoring`, `status.homework`, `agenda.*`,
`setup.*`, `finished`. Nasza enum `Phase` (STRATEGY/ACTION/STATUS/AGENDA) mapowana w
`web_data.py` → `_to_web_phase` (STATUS→`status.scoring`, AGENDA→`agenda.voting`).
`gameState.activePlayer` to KOLOR gracza (nie id) — frontend dopasowuje po kolorze.

Pełna LOGIKA faz (przejścia, akcje, timing) = Warstwa B (roadmapa M2–M6), port z
`TI4_map_generator_bot/src/main/java/ti4/service/{turn,strategycard,tactical,combat,agenda}`.

---

## 7. Ekonomia planet: optimal / flex — ✅ ZWERYFIKOWANE

Źródło (nie z pamięci): AsyncTI4 bot, `Planet.getOptimalResources/getOptimalInfluence/
getFlexResourcesOrInfluence`. Reguła per kontrolowana planeta:
- `optimalResources` = `resources`, gdy `resources > influence`, inaczej 0;
- `optimalInfluence` = `influence`, gdy `influence > resources`, inaczej 0;
- `flex` = wartość (res==inf), gdy `resources == influence`, inaczej 0.
Sumy po planetach gracza zasilają `playerData.optimalResources/optimalInfluence/flexValue`
(oraz `tot*`). `resources`/`influence`/`totResources`/`totInfluence` = sumy surowe.
Implementacja: `src/api/web_data.py` → `_planet_economy` / `_Economy`.

## 8. Liderzy frakcji (agent/commander/hero) — ✅ ZWERYFIKOWANE (dane)

Źródło: pole `leaders` w danych frakcji AsyncTI4 (np. Sol: `solagent, solcommander,
solhero`). Typ wyprowadzany z sufiksu id. Start: agent gotowy (odblokowany),
commander/hero zablokowani (odblokowują się przez warunki — logika w późniejszej fazie).
Model: `FactionDef.leaders`; emisja: `web_data._player_leaders` → `playerData.leaders`
(`{id,type,tgCount,exhausted,locked,active}`) + `leaderIDs`.

---

## 9. Kolejność tur fazy akcji i pas — ✅ ZWERYFIKOWANE

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
