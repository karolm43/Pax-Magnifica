# DOKUMENTACJA ARCHITEKTONICZNA I SPECYFIKACJA TECHNICZNA
**Projekt:** CUSTODIAN ENGINE (TI4 AI Opponent & Tabletop Companion)  
**Typ systemu:** Local-First Client-Server / Hierarchical Decision Engine  
**Wersja dokumentu:** 2.1.0 (Zaktualizowana pod kątem pracy z Claude i optymalizacji Numba/NumPy)  
**Przeznaczenie:** Specyfikacja wykonawcza dla zespołu deweloperskiego i agentów kodujących (VS Code / Claude)

---

## 1. Przegląd Systemu (System Overview)

### 1.1. Cel biznesowy i funkcjonalny
**Custodian Engine** to niezależny system sztucznej inteligencji pełniący rolę autonomicznego przeciwnika przy stole oraz asystenta stanu gry dla fizycznych rozgrywek *Twilight Imperium: 4th Edition* (wspierający zarówno grę podstawową, jak i rozszerzenie *Prophecy of Kings* poprzez zewnętrzne pliki definicji danych). System zastępuje jednego lub więcej graczy ludzkich pełnoprawnym agentem podejmującym decyzje strategiczne, operacyjne, taktyczne oraz dyplomatyczne.

### 1.2. Założenia operacyjne
1. **Model Human-in-the-Loop:** Fizyczna plansza stanowi nadrzędne źródło prawdy. Gracze wprowadzają zmiany stanu planszy za pośrednictwem interfejsu webowego (wspieranego przez zagregowane kreatory akcji *Wizards* oraz komendy głosowe), a system wylicza i komunikuje akcje bota.
2. **Krokowa Maszyna Stanów (Timing Windows FSM):** Pojedyncza akcja taktyczna nie jest wykonywana jako niepodzielny blok. Silnik przechodzi krokowo przez fazy: `ACTIVATION` $\rightarrow$ `MOVEMENT` $\rightarrow$ `SPACE_CANNON_OFFENSE` $\rightarrow$ `SPACE_COMBAT` $\rightarrow$ `INVASION` $\rightarrow$ `PRODUCTION`. Pozwala to graczom ludzkim przy stole na reagowanie w odpowiednich oknach czasowych (np. zagrywanie Kart Akcji, używanie zdolności agentów lub technologii).
3. **Odporność na niepełny model reguł (Manual Override / God-Mode):** Silnik umożliwia natychmiastową, ręczną modyfikację dowolnego parametru gry (pozycji jednostek, zasobów, właścicieli planet, punktów zwycięstwa) w dowolnym momencie tury bez utraty spójności procesu decyzyjnego.
4. **Asymetria przez potok reguł (Rules Pipeline / Hooks):** Od pierwszego kamienia milowego architektura uwzględnia punkty rozszerzeń (hooki) modyfikujące ruch, walkę i produkcję, co pozwala na bezinwazyjne wprowadzanie zdolności frakcyjnych i technologii.
5. **Deterministyczny czas odpowiedzi (SLA):** Czas wygenerowania pojedynczej decyzji operacyjnej nie może przekraczać $2000\text{ ms}$, symulacji taktycznej starcia (10 000 iteracji) $100\text{ ms}$, a sklonowania numerycznego stanu gry w pętli symulacyjnej $0.5\text{ ms}$.

---

## 2. Stos Technologiczny (Technology Stack)

### 2.1. Backend & AI Core
* **Język programowania:** `Python 3.12+` (ścisłe typowanie statyczne weryfikowane przez `mypy --strict`).
* **Zarządzanie pakietami i środowiskiem:** `uv`.
* **Walidacja i serializacja danych (Warstwa API/DB):** `Pydantic v2` (kontrakty danych, wczytywanie assetów JSON, walidacja stanu `GameState`).
* **Obliczenia numeryczne i symulacje (Warstwa AI):** `NumPy` + `Numba` (`@njit` – kompilacja JIT dla wektoryzowanych symulacji Monte Carlo oraz płaskiej reprezentacji stanu `FastState`).
* **Silnik grafowy (Mapa i Topologia):** `rustworkx` lub `NetworkX` (graf skierowany z dynamicznymi wagami krawędzi i obsługą anomalii).
* **Optymalizacja kombinatoryczna (Solvery):** Deterministyczne algorytmy *Branch and Bound* oraz zachłanne heurystyki w `NumPy` (czas wykonania $< 1\text{ ms}$ dla alokacji planet i produkcji), opcjonalnie wspierane przez `Google OR-Tools (CP-SAT)` ze skalowaniem całkowitoliczbowym.
* **Warstwa API:** `FastAPI` + `Uvicorn` (komunikacja REST oraz strumieniowanie stanu przez `WebSockets`).
* **Trwałość danych (Persistence):** `SQLite 3` w architekturze **Snapshot Stack (Memento)** – zapis pełnych, lekkich migawek JSON stanu gry wraz z metadanymi akcji, gwarantujący natychmiastowe działanie `Undo`, `Redo` oraz `God-Mode Override`.

### 2.2. Frontend (Tabletop UI)
* **Framework:** `React 19` + `TypeScript 5.x` + `Vite`.
* **Zarządzanie stanem:** `Zustand` (synchronizacja z backendem przez WebSocket).
* **Warstwa wizualna:** `Tailwind CSS` + komponenty `shadcn/ui`.
* **Silnik renderowania mapy:** Interaktywny komponent `SVG` oparty na układzie współrzędnych kubicznych z kreatorami szybkiego wprowadzania ruchów (*Action Wizards*).

### 2.3. Narzędzia jakości kodu (QA & Tooling)
* **Testy jednostkowe i integracyjne:** `pytest` + `pytest-cov` + `hypothesis` (property-based testing dla symulatorów walki i solverów).
* **Linter i formater:** `Ruff`.

---

## 3. Architektura Systemu i Przepływ Danych

System wykorzystuje architekturę warstwową z wyraźną separacją pomiędzy danymi statycznymi (`StaticDataRegistry`), walidowanym stanem gry (`GameState`), numerycznym stanem symulacyjnym (`FastState`) a silnikiem decyzyjnym (`AI Engine Layer`).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WARSTWA PREZENTACJI (Web UI)                     │
│  [ HexGrid SVG + Wizards ]  [ Panel Dyplomacji ]  [ Moduł God-Mode ]    │
└───────────────────┬─────────────────────────────────────▲───────────────┘
                    │ REST / WebSocket (JSON)             │ Krok Akcji AI
                    ▼                                     │ & Stan Gry
┌─────────────────────────────────────────────────────────┴───────────────┐
│                     WARSTWA ZARZĄDZANIA STANEM (Core)                   │
│  [ FastAPI ] ──► [ GameState (Pydantic) + Timing FSM ] ──► [ SQLite ]   │
│                                     │                      (Snapshots)  │
│  [ StaticDataRegistry (Assety) ] ───┼──► Konwersja do tablic NumPy      │
└─────────────────────────────────────┼───────────────────────────────────┘
                                      │ FastState (.clone() < 0.5 ms)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SILNIK DECYZYJNY AI (Engine)                     │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ 1. WARSTWA STRATEGICZNA (engine.strategic)                        │  │
│  │    • Objective Evaluator   • Planet Exhaustion Solver (B&B/NumPy) │  │
│  └─────────────────────────────────┬─────────────────────────────────┘  │
│                                    │ Warunki brzegowe i priorytety VP   │
│                                    ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ 2. WARSTWA OPERACYJNA (engine.operational)                        │  │
│  │    • Influence/Threat Maps • Macro-Action Generator               │  │
│  │    • Utility AI Scorer     • Sequence Planner (1-Step + Urgency)  │  │
│  └─────────────────────────────────┬─────────────────────────────────┘  │
│                                    │ Wybrana Makro-Akcja                │
│                                    ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ 3. WARSTWA TAKTYCZNA (engine.tactical)                            │  │
│  │    • Vectorized Combat Sim • Production Knapsack Solver           │  │
│  │    • Fleet & Transport Logistics Planner (z obsługą podnoszenia)  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Specyfikacja Modułów (Core & Engine Modules)

### 4.1. Moduł Stanu, Rejestru i Topologii (`src/core/`)
Odpowiada za wczytanie zewnętrznych assetów, matematyczną reprezentację planszy, maszynę stanów tury oraz historię zmian.

* **`registry.py` (`StaticDataRegistry`):** Niemutowalny rejestr wczytujący definicje kafelków, planet, jednostek, technologii i celów ze ścieżek zdefiniowanych w `src/config.py`. Mapuje identyfikatory tekstowe (`str`) na gęste indeksy całkowitoliczbowe (`int`) używane przez `FastState`.
* **`models.py`:** Modele domenowe `Pydantic v2` dla encji statycznych i dynamicznych.
* **`hex_grid.py`:** Implementacja siatki heksagonalnej w układzie współrzędnych kubicznych $(q, r, s)$, gdzie spełniony jest warunek:
  $$q + r + s = 0$$
  Odległość bazowa pomiędzy dwoma systemami $A$ i $B$ wyraża się wzorem:
  $$d(A, B) = \frac{|q_A - q_B| + |r_A - r_B| + |s_A - s_B|}{2}$$
  Graf rozszerza siatkę geometryczną o krawędzie nieliniowe (tunele czasoprzestrzenne *Wormhole* $\alpha, \beta, \gamma$) oraz modyfikatory wag i blokady wynikające z anomalii (*Asteroid Field*, *Nebula*, *Supernova*, *Gravity Rift*) oraz aktywnych modyfikatorów z `rules_hooks.py`.
* **`game_state.py`:** Główny model danych `GameState` (`Pydantic v2`) wraz z maszyną stanów okna akcji (*Timing Windows FSM*). Obsługuje walidację na styku z API oraz serializację.
* **`fast_state.py`:** Płaska, wektorowa reprezentacja stanu gry oparta na prealokowanych tablicach `NumPy` (jednostki w systemach, stany planet, zasoby i technologie graczy). Udostępnia metodę `.clone()` opartą na `np.copy()`, gwarantującą czas kopiowania znacznie poniżej $0.5\text{ ms}$ oraz pełną kompatybilność z kompilatorem `Numba`.
* **`rules_hooks.py`:** Rejestr funkcji zwrotnych (hooków) modyfikujących parametry bazowe (np. zasięg ruchu statków, modyfikatory rzutów kośćmi, pojemność stoczni) na podstawie frakcji i posiadanych technologii.
* **`event_store.py`:** Implementacja wzorca **Snapshot Stack (Memento)** w bazie `SQLite 3`. Każda zatwierdzona zmiana stanu zapisuje zserializowany obiekt `GameState` (ok. $20\text{--}50\text{ KB}$), zapewniając bezbłędną obsługę `Undo`, `Redo` oraz ręcznych korekt `God-Mode`.

### 4.2. Warstwa Strategiczna (`src/engine/strategic/`)
Odpowiada za długoterminowe tempo zdobywania punktów zwycięstwa (*VP Pacing*) i alokację makroekonomiczną na początku rundy.

* **`objective_evaluator.py`:** Kodyfikuje warunki celów publicznych (Stage I, Stage II) oraz celów sekretnych bota. Dla każdego celu oblicza dystans zasobowy i pozycyjny dzielący bota od spełnienia warunku w skali znormalizowanej $[0.0, 1.0]$.
* **`resource_solver.py`:** Szybki solver oparty na algorytmie *Branch and Bound* (lub zachłannej heurystyce z korektą) wyliczający w czasie $< 1\text{ ms}$ optymalny plan wykorzystania kontrolowanych planet w bieżącej rundzie. Dzieli planety na 3 zbiory rozłączne:
  1. Planety wyczerpywane na surowce produkcyjne ($R$),
  2. Planety wyczerpywane na wpływy / żetony dowodzenia ($I$),
  3. Planety rezerwowane pod realizację celów w fazie statusu lub obronę ($O$).
* **`strategy_selector.py`:** Wybiera optymalną Kartę Strategii w Fazie Strategii oraz podejmuje decyzje o aktywacji zdolności drugorzędnych (*Secondary Abilities*) kart graczy przy stole.

### 4.3. Warstwa Operacyjna (`src/engine/operational/`)
Odpowiada za manewrowanie na mapie, ocenę zagrożenia i kolejkowanie ruchów w Fazie Akcji.

* **`influence_maps.py`:** Generuje macierze wpływu i zagrożenia dla każdego heksa na mapie. Dla każdego systemu $h$ i gracza $p$ wylicza zagregowaną siłę bojową $F(p, h)$, jaka może dotrzeć do systemu $h$ w pojedynczej akcji taktycznej.
* **`macro_actions.py`:** Redukuje przestrzeń kombinatoryczną gry do skończonego zbioru $K$ ($K \in [8, 20]$) wysokopoziomowych intencji operacyjnych (np. `CAPTURE_SYSTEM`, `REINFORCE_SYSTEM`, `PRODUCE_AT_DOCK`, `PLAY_STRATEGY_CARD`, `STALL_ACTION`, `PASS`).
* **`utility_scorer.py`:** Ocenia każdą wygenerowaną Makro-Akcję $a$ za pomocą wielokryterialnej funkcji użyteczności uwzględniającej współczynnik pilności (*Urgency*):
  $$U(a) = w_{\text{VP}} \cdot S_{\text{VP}}(a) + w_{\text{econ}} \cdot S_{\text{econ}}(a) + w_{\text{pos}} \cdot S_{\text{pos}}(a) - w_{\text{risk}} \cdot S_{\text{risk}}(a) + w_{\text{urg}} \cdot S_{\text{urg}}(a)$$
  gdzie poszczególne składowe $S \in [0, 1]$ są przekształcane przez funkcje odpowiedzi, a $S_{\text{urg}}(a)$ określa ryzyko zablokowania danej akcji przez sąsiadów w bieżącej rundzie.
* **`sequence_planner.py`:** Planista kolejności ruchów wykorzystujący podejście **1-Step Lookahead + Urgency Heuristics**. Priorytetyzuje akcje zagrożone zablokowaniem przez rywali, a bezpieczne akcje wewnętrzne (niskie $S_{\text{urg}}$) odkłada na koniec rundy jako naturalne akcje opóźniające (*Stalling*).

### 4.4. Warstwa Taktyczna (`src/engine/tactical/`)
Odpowiada za wykonanie konkretnej Makro-Akcji z maksymalną wydajnością matematyczną.

* **`combat_simulator.py`:** Wektoryzowany symulator Monte Carlo (`NumPy` + `Numba` `@njit`) rozstrzygający bitwy kosmiczne i naziemne. Uwzględnia pełną sekwencję: *Space Cannon Offense*, *Anti-Fighter Barrage*, rundy rzutów kośćmi $k10$, alokację trafień z uwzględnieniem *Sustain Damage*, *Bombardment*, *Space Cannon Defense* oraz walkę piechoty i mechów. Zwraca rozkład prawdopodobieństwa wygranej $P(\text{win})$ oraz oczekiwaną wartość strat zasobowych $\mathbb{E}[\text{loss}]$.
* **`production_solver.py`:** Rozwiązuje problem plecakowy podczas produkcji w *Space Docku* (metodą *Branch and Bound* w `NumPy` lub w `CP-SAT` ze skalowaniem całkowitoliczbowym). Aby obsłużyć ułamkowe koszty myśliwców (*Fighters*) i piechoty (*Infantry*) wynoszące $0.5$ zasobu za sztukę, koszty i dostępne zasoby są skalowane przez mnożnik $2$ ($c'_u = 2 \cdot c_u \in \mathbb{Z}^+$, $R'_{\text{avail}} = 2 \cdot R_{\text{avail}}$):
  $$\max \sum_{u \in U} v_u \cdot x_u$$
  przy ograniczeniach:
  $$\sum_{u \in U} c'_u \cdot x_u \le R'_{\text{avail}} \quad \text{(limit zasobów przeskalowany }\times 2\text{)}$$
  $$\sum_{u \in U} x_u \le P_{\text{limit}} \quad \text{(limit produkcyjny stoczni)}$$
  $$F_{\text{existing}} + \sum_{u \in U_{\text{cap\_ship}}} x_u \le F_{\text{supply}} \quad \text{(limit żetonów floty dla statków nieliniowych)}$$
  $$N_{F,\text{existing}} + x_F \le C_{\text{existing}} + 3 \cdot N_{\text{docks}} + \sum_{u \in U_{\text{ship}}} \text{cap}_u \cdot x_u \quad \text{(pojemność dla myśliwców w przestrzeni)}$$
  *(Uwaga domenowa: piechota $x_I$ produkowana w układzie ze stocznią ląduje bezpośrednio na planecie i nie obciąża limitu pojemności floty w przestrzeni).*
* **`logistics_planner.py`:** Algorytm dobierający jednostki z sąsiednich układów do wykonania ruchu taktycznego. Obsługuje zbieranie sił z wielu nieaktywowanych systemów, podnoszenie piechoty i myśliwców z mijanych układów na trasie przelotu transportowców oraz minimalizację osłabienia granic własnej strefy (*Slice*).

### 4.5. Warstwa Dyplomacji i Polityki (`src/engine/diplomacy/`)
* **`threat_assessment.py`:** Wylicza współczynnik zagrożenia $T_p$ dla każdego gracza na podstawie liczby posiadanych punktów VP, potencjału punktowego w bieżącej rundzie oraz agresji terytorialnej. Implementuje logikę blokowania lidera (*Winslaying*).
* **`trade_evaluator.py`:** Silnik wyceny transakcji handlowych (*Trade Goods*, *Commodities*, umowy o nieagresję). Transakcja jest akceptowana wtedy i tylko wtedy, gdy:
  $$\Delta U = U_{\text{self}}(\text{oferta}) - T_p \cdot U_{\text{opponent}}(\text{oferta}) > \theta$$
* **`agenda_voter.py`:** Moduł wyceniający wpływ poszczególnych rozstrzygnięć kart Agendy na wektor stanu bota oraz lidera i alokujący dostępną pulę głosów.

---



## 5. Standardy Inżynieryjne i Zarządzanie Assetami (Engineering Standards)

1. **Zarządzanie Assetami Użytkownika i Zakaz Hardkodowania:**
   * Żadne statystyki jednostek, parametry planet ani opisy technologii nie mogą być zaszyte bezpośrednio w kodzie algorytmów.
   * Wszystkie ścieżki do plików danych muszą być zdefiniowane jako stałe w pliku `src/config.py` (np. `TILES_DATA_PATH`, `UNITS_DATA_PATH`), co pozwala użytkownikowi na łatwe podpięcie własnych plików JSON w katalogu `assets/game_data/`.
   * Agenty kodujące (Claude) mają bezwzględny zakaz generowania pełnych plików bazodanowych JSON z pamięci – do testów jednostkowych w `tests/conftest.py` należy tworzyć wyłącznie minimalne, syntetyczne fikstury (np. 2 kafelki, 3 typy jednostek).
2. **Dwuwarstwowość i Niemutowalność w Symulacjach:**
   * Warstwa API i bazy danych operuje na obiekcie `GameState` (`Pydantic v2`).
   * Warstwa `src/engine/` operuje wyłącznie na obiekcie `FastState` (`NumPy`) oraz indeksach z `StaticDataRegistry`. Klonowanie stanu metodą `FastState.clone()` musi wykonywać się w czasie $< 0.5\text{ ms}$ bez użycia `copy.deepcopy`.
3. **Pokrycie testami i Jakość Kodu:**
   * Każdy moduł w katalogach `src/core/` oraz `src/engine/` wymaga pokrycia testami jednostkowymi na poziomie minimum $85\%$ (`pytest --cov=src`) oraz przejścia rygorystycznej analizy typów (`mypy src tests --strict`).

---

## 7. Plan Realizacji Projektu (Delivery Roadmap)

### Kamień Milowy 1 (M1): Rdzeń Stanu (Headless Core), Topologia i Assety
* **Zakres prac:**
  * Konfiguracja `pyproject.toml`, `src/config.py` (ścieżki do assetów) oraz implementacja `StaticDataRegistry` (`registry.py`) i modeli `Pydantic v2` (`models.py`).
  * Implementacja klasy `HexGrid` na współrzędnych kubicznych z obsługą tuneli czasoprzestrzennych, anomalii oraz szkieletu `rules_hooks.py`.
  * Wdrożenie `GameState`, konwertera do `FastState` (`NumPy`) oraz `EventStore` (Snapshot Stack w `SQLite` z obsługą `Undo/Redo` i `God-Mode`).
* **Kryterium akceptacji (DoD):** Pełne wczytywanie assetów użytkownika, klonowanie `FastState` w czasie $< 0.5\text{ ms}$ oraz pokrycie testami warstwy `core` $\ge 85\%$.

### Kamień Milowy 2 (M2): Warstwa Taktyczna (Walka, Produkcja, Logistyka) i Podstawowy UI
* **Zakres prac:**
  * Implementacja wektoryzowanego symulatora walk kosmicznych i naziemnych w `NumPy` + `Numba` (`combat_simulator.py`).
  * Implementacja solvera produkcji (`production_solver.py`) oraz logistyki floty z podnoszeniem desantu po drodze (`logistics_planner.py`).
  * Wystawienie endpointów `FastAPI` oraz budowa interfejsu webowego (mapa SVG, kreator szybkiego przesuwania flot *Action Wizard* oraz panel `God-Mode`).
* **Kryterium akceptacji (DoD):** Czas wykonania 10 000 iteracji Monte Carlo dla pojedynczej bitwy $< 100\text{ ms}$; wyznaczenie optymalnego koszyka produkcji w czasie $< 5\text{ ms}$; szybka aktualizacja stanu tury na mapie SVG.

### Kamień Milowy 3 (M3): Warstwa Strategiczna i Ekonomia Punktowa
* **Zakres prac:**
  * Implementacja ewaluatora celów publicznych i sekretnych (`objective_evaluator.py`).
  * Wdrożenie solvera alokacji planet pomiędzy zasoby, wpływy a wymagania punktowe (`resource_solver.py`).
  * Implementacja modułu wyboru Kart Strategii oraz obsługi ich zdolności drugorzędnych (`strategy_selector.py`).
* **Kryterium akceptacji (DoD):** Silnik samodzielnie wyznacza główny cel rundy, zarządza pulą żetonów dowodzenia i realizuje cele ekonomiczne oraz technologiczne.

### Kamień Milowy 4 (M4): Warstwa Operacyjna i Krokowa Autonomia Ruchowa
* **Zakres prac:**
  * Implementacja kalkulatora map wpływów i zagrożeń (`influence_maps.py`).
  * Budowa generatora Makro-Akcji (`macro_actions.py`) i systemu krzywych użyteczności z wagą pilności (`utility_scorer.py`).
  * Implementacja planisty `sequence_planner.py` (1-Step Lookahead + Urgency Heuristics) zintegrowanego z maszyną stanów *Timing Windows FSM*.
* **Kryterium akceptacji (DoD):** Agent samodzielnie rozgrywa pełną rundę taktyczną krok po kroku (pozwalając ludziom na reakcje między fazami ruchu, walki i produkcji), broni układu macierzystego i stosuje taktykę opóźniania akcji (*Stalling*).

### Kamień Milowy 5 (M5): Silnik Dyplomatyczny i Kontrola Lidera
* **Zakres prac:**
  * Implementacja modułu oceny zagrożenia graczy i detekcji lidera (`threat_assessment.py`).
  * Wdrożenie kalkulatora użyteczności ofert handlowych (`trade_evaluator.py`) oraz modułu głosowania w Fazie Agendy (`agenda_voter.py`).
  * Rozbudowa UI o panel składania ofert handlowych i dyplomatycznych botowi.
* **Kryterium akceptacji (DoD):** Bot dynamicznie modyfikuje wagi agresji przeciwko liderowi stołu (*Winslaying*) oraz autonomicznie zawiera lub odrzuca transakcje handlowe.

### Kamień Milowy 6 (M6): Rozbudowa Asymetrii Frakcyjnej i Integracja Głosowa
* **Zakres prac:**
  * Implementacja konkretnych reguł frakcyjnych w `rules_hooks.py` oraz matryc wag dla poszczególnych frakcji z assetów.
  * Integracja parsera języka naturalnego (Voice-to-State) tłumaczącego komendy głosowe graczy przy stole na wywołania API aktualizujące `GameState`.
* **Kryterium akceptacji (DoD):** Pełna obsługa asymetrii wybranych frakcji oraz możliwość bezdotykowego aktualizowania stanu planszy.