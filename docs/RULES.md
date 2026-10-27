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

---

## 10. Posiadane jednostki i ulepszenia (unitsOwned) — ✅ ZWERYFIKOWANE (dane)

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

Źródło (nie z pamięci): dane kart `assets/data/strategy_cards/pok.json` +
`assets/data/strategy_card_sets/strategyCardSets.json`; logika z AsyncTI4 bot:
`StrategyCardManager.incrementTradeGoods`, `PickStrategyCardButtonHandler` (grant TG przy
wyborze), `PlayStrategyCardService`. Zweryfikowane 2026-10 na kodzie bota.

**Zestaw kart (domyślny PoK, 8 kart):** każda ma `initiative` (1–8) i `name`:
1 Leadership, 2 Diplomacy, 3 Politics, 4 Construction, 5 Trade, 6 Warfare,
7 Technology, 8 Imperial. Inicjatywa = numer karty. Dane czytane z rejestru po
`enabled_sources.json` (zestaw `pok`). Zero hardkodowania nazw/numerów.

**Reguła wyboru (pick):**
- W fazie strategii każdy gracz wybiera 1 kartę (przy ≤4 graczach warianty biorą 2 —
  tu wspieramy 1 kartę/gracz, zgodnie z 5–6 osobową grą; wielokrotny wybór dołożymy przy
  wariantach 3–4 graczy). Kolejność wyboru: od mówcy (speaker) zgodnie z ruchem zegara.
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

## 15. Typ planety: pole `planetTypes` (lista) vs `planetType` — ✅ ZWERYFIKOWANE (dane)

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
