# Dokumentacja Custodian Engine — indeks

Ten plik to **brama do dokumentacji**: po co ten projekt, gdzie co leży, który dokument
do czego służy i w jakiej kolejności czytać. Zaczynaj tutaj.

---

## 1. Cel projektu (jedno zdanie)

**Custodian Engine to lokalny silnik do gry w Twilight Imperium 4 w trybie solo —
docelowo autonomiczny BOT-przeciwnik**, który prowadzi własne frakcje: wybiera strategie,
rusza flotami, walczy, głosuje na agendzie i punktuje cele, tak by człowiek mógł rozegrać
pełną partię przeciw komputerowi (lub z komputerem dopełniającym stół).

### Co to znaczy w praktyce (etapy dojrzałości)
1. **Cyfrowa plansza + God-Mode** (gotowe) — aplikacja odwzorowuje stan fizycznej/cyfrowej
   planszy, pozwala go edytować i cofać (Undo). Fundament pod resztę.
2. **Silnik rozgrywki** (w toku) — realne fazy, tury, karty strategii, akcja taktyczna,
   walka, status, agenda. Gra EGZEKWUJE reguły (silnik-sędzia) i prowadzi przebieg rundy
   przez OKNA CZASOWE (np. secondary kart strategii dla wszystkich graczy po kolei). God-Mode
   zostaje jako wentyl ręcznej korekty. Zmiana kierunku i model okien: `RULES.md` 29, etap E8
   w `PLAN_PELNA_ROZGRYWKA.md`.
3. **Bot AI** (cel końcowy) — warstwa decyzyjna (strategiczna → operacyjna → taktyczna),
   która gra frakcją samodzielnie. Silnik z etapu 2 jest jej „regułami świata".

Pełna wizja i architektura docelowa: [`specyfikacja_techniczna_i_architektura_systemu.md`](specyfikacja_techniczna_i_architektura_systemu.md).

---

## 2. Mapa dokumentów (co czytać do czego)

| Dokument | Rola | Aktualność |
|---|---|---|
| **`README.md`** (ten plik) | Indeks: cel, struktura, konwencje, kolejność czytania. | 🟢 żywy |
| **`PROGRESS.md`** | Stan prac: status etapów + ostatnie bloki (odchudzony). Czytaj na start sesji. | 🟢 żywy |
| **`PROGRESS_ARCHIWUM.md`** | Pełna historia ukończonych bloków (Faza 1 → E4·UI²). Sięgaj po szczegół. | 🟤 archiwalny |
| **`RULES.md`** | **Źródło prawdy dla mechanik TI4.** Każda reguła ma źródło (LRR / bot). | 🟢 żywy |
| **`rules_tirules/`** | **Offline zrzut reguł z tirules2.com** (149 tematów MD + `tirules.json`). Sprawdzaj reguły tutaj najpierw. Start: `rules_tirules/INDEX.md`. | 🟢 żywy |
| **`PLAN_PELNA_ROZGRYWKA.md`** | **Główny plan silnika** (etapy E1–E8, fazy C/H/N), lista frakcji i gimmicków oraz **CEL PRODUKTOWY: wszystkie karty gotowe + zagrywanie przeciąganiem z ręki**. | 🟢 żywy |
| **`ARCHITEKTURA_KODU.md`** | **Warstwy (core/api/ai), konwencje rozwoju, wzorzec hooków, dług techniczny.** Czytaj przed dodaniem nowej mechaniki. | 🟢 żywy |
| **`POKRYCIE_HOOKOW.md`** | **GENEROWANY raport pokrycia hooków** (zarejestrowane hooki, % komponentów z hookiem, obszary reguł do domknięcia). Nie edytuj; odśwież: `uv run python -m src.audit.hook_coverage --write`. | 🟢 generowany |
| **`UI_WYBOR_FRAKCJI.md`** | **Scena wyboru frakcji + krok „Gracze" kreatora**: układ, pliki, format treści (portrety/cytaty/lore), animacje, Obsidian (pismo + groza), gotchas. Czytaj przed zmianą UI setupu. | 🟢 żywy |
| **`ARCHITEKTURA_PO_MIGRACJI.md`** | Mapa kodu: backend/frontend, kontrakt `web-data`, endpointy. | 🟡 referencyjny |
| **`specyfikacja_techniczna_i_architektura_systemu.md`** | Wizja docelowa + architektura warstw AI. | 🟡 referencyjny |
| **`PORT_ASYNCTI4_PLAN.md`** | Werdykt: jak przenosimy funkcje AsyncTI4 (warstwa A/B). | 🟤 archiwalny¹ |
| **`plan_faza1_interaktywna_mapa.md`** | Plan Fazy 1 (cyfrowa plansza) — zrealizowany. | 🟤 archiwalny² |

¹ Treść wchłonięta przez `PLAN_PELNA_ROZGRYWKA.md`; trzymany dla kontekstu decyzji.
² Faza 1 ukończona (God-Mode działa); trzymany jako zapis DoD i ustaleń z danych.

> **Zasada aktualności:** gdy dokument i KOD się nie zgadzają — **kod wygrywa**. Dokumenty
> referencyjne (🟡) i archiwalne (🟤) mogą zawierać nieaktualne szczegóły; żywe (🟢)
> aktualizujemy na bieżąco. Zawsze weryfikuj względem `src/` i testów.

---

## 3. Struktura repozytorium (gdzie co jest)

```
Pax Magnifica/
├── README.md                     # instrukcja instalacji/uruchomienia (dla człowieka)
├── docs/                         # DOKUMENTACJA (ten katalog) — patrz tabela wyżej
├── src/                          # BACKEND (Python / FastAPI) — źródło prawdy o stanie
│   ├── core/                     #   rdzeń: stan, rejestr danych, mapa, silnik reguł
│   │   ├── registry.py           #     StaticDataRegistry — ładuje dane z assets/ po `source` (+ catalog)
│   │   ├── models.py             #     modele statyczne (UnitDef, PlanetDef, FactionDef, ...)
│   │   ├── sources.py            #     priorytet i walidacja źródeł kanonicznych (SOURCE_PRIORITY)
│   │   ├── components.py         #     Katalog_Komponentów: modele kategorii + CATEGORY_SPECS + ComponentCatalog
│   │   ├── component_loader.py   #     ładowanie/wybór wpisów po `source` (select_entries, LoadReport)
│   │   ├── references.py         #     spójność referencji (frakcje, talie, attachmenty)
│   │   ├── timing_spec.py        #     Specyfikacja_Czasowa: parse_timing + TRIGGER_WINDOW_MAP (D10)
│   │   ├── effects_registry.py   #     Rejestr_Efektów: id komponentu -> status (not/impl/manual)
│   │   ├── rules_links.py        #     powiązania komponentów z tematami Zrzutu_Reguł (INDEX)
│   │   ├── game_state.py         #     GameState / PlayerState / SystemState (+ clone)
│   │   ├── hex_grid.py           #     siatka heksów (q,r,s), sąsiedztwo, wormhole, anomalie
│   │   ├── map_string.py         #     parser map stringa AsyncTI4 -> HexGrid
│   │   ├── positions.py          #     pozycje RPP (101, 201, ...) -> współrzędne
│   │   ├── unit_catalog.py       #     jawne tabele reguł jednostek (umiejscowienie, asyncId, limity)
│   │   ├── faction_setup.py      #     setup frakcji (parser startingFleet, rozstawienie)
│   │   ├── turn_flow.py          #     E1: fazy + kolejność tur (czyste funkcje)
│   │   ├── strategy_phase.py     #     E2: faza strategii (wybór kart, trade goods)
│   │   ├── timing.py             #     okna czasowe (kolejka respondentów) — RULES.md 29.2
│   │   ├── event_store.py        #     EventStore (SQLite) — Undo/Redo/God-Mode
│   │   ├── economy.py, command_tokens.py, exhaust.py, control.py, unit_ops.py  # punkty centralne (RULES.md 43.1a)
│   │   ├── secret_objectives.py, promissory_notes.py, relic_fragments.py, card_draw.py  # karty/zasoby (C9)
│   │   ├── rules_hooks.py        #     rejestr hooków, efektów kart i opisów wyborów (RULES.md 43)
│   │   ├── hooks/                #     wyjątki tematycznie: frakcje, technologie, efekty kart akcji + formularze
│   │   ├── action_cards.py       #     zagrywanie kart akcji: formularz, zagrywalność, efekt (RULES.md 53)
│   │   └── agenda_phase.py       #     faza agendy: głosowanie, remis, prawa (RULES.md 51)
│   ├── audit/                    #   AUDYTOR_DANYCH (CLI: `uv run python -m src.audit`)
│   │   ├── locality.py           #     Strażnik_Lokalności: ścieżki referencyjne, odczyty spoza repo, URL-e
│   │   ├── assets_manifest.py    #     manifest grafik/fontów (path+size+sha256), diff z dyskiem
│   │   ├── frontend_data.py      #     diff id wbudowanych danych frontu vs Katalog (R11.5)
│   │   ├── diffs.py              #     różnice liczb/zbiorów, luki źródeł kanonicznych (expected_gaps)
│   │   ├── report.py             #     AuditReport / build_report / render_text / exit_code
│   │   └── sync_assets.py        #     kopiowanie brakujących grafik z manifestu (`--from <katalog>`)
│   └── api/                      #   warstwa HTTP/WS
│       ├── app.py                #     fabryka FastAPI (montaż routerów) + WebSocket
│       ├── routers/              #     cienkie endpointy tematyczne (game, board, components, ...)
│       │   └── components.py     #       /components, /components/{kat}/{id}, /timing-specs, bundle frakcji
│       ├── web_data.py           #     build_web_data: GameState -> dokument dla frontu (KONTRAKT UI)
│       ├── schemas.py            #     DTO żądań/odpowiedzi (Pydantic)
│       └── state_service.py      #     jedyne miejsce mutujące stan (commit + broadcast)
├── frontend/                     # FRONTEND (React/Vite) — viewer planszy (bazuje na ti4_web)
│   └── src/
│       ├── api/                  #   hooki danych (useBoardEditor, useNewGame, ...)
│       ├── domains/              #   funkcjonalne obszary UI (map, player, game-shell, cards, ...)
│       ├── entities/             #   WBUDOWANE statyczne dane (jednostki/planety/techy) + lookupy
│       ├── shared/assets/        #   Resolver_Zasobów (assetUrl/sheetUrl) + assetManifest.json (lokalne URL)
│       ├── state/                #   store (Zustand) + kontekst gry
│       └── ds/                   #   design system (komponenty bazowe)
├── tests/                        # TESTY backendu (pytest) — jeden plik per moduł core/api/audit
├── audit/                        # KONFIG AUDYTORA (w repo — D1/D12): manifest grafik, baseline liczb,
│   │                             #   wyjątki luk, allowlist URL, nieużywane katalogi assets/
│   ├── assets_manifest.json      #   manifest wymaganych grafik/fontów (grafiki poza repo — D1)
│   └── baseline_counts.json      #   wartości referencyjne liczb wpisów (test regresji)
├── assets/                       # DANE GRY (AsyncTI4): JSON w repo (~5 MB), grafiki POZA repo (D1)
│   ├── enabled_sources.json      #   aktywne źródła danych (base, pok, codex1-4, thunders_edge)
│   ├── config/effects_status.json #  Rejestr_Efektów (w repo); engine_config.json; reszta ignorowana
│   ├── data/ systems/ planets/ alias/   # dane silnika (wersjonowane)
│   └── ... (grafiki/fonty — poza repo, lokalnie przez manifest + sync_assets; patrz .gitignore)
└── TI4_map_generator_bot/        # ŹRÓDŁO REFERENCYJNE (Java, poza repo) — czytamy, nie linkujemy
```

---

## 4. Jak pracujemy (konwencje — skrót; pełne zasady w steering)

- **Zero reguł TI4 z pamięci.** Dane liczbowe z `assets/` przez `StaticDataRegistry`.
  Reguły mechaniczne najpierw do `RULES.md` ze źródłem (LRR / bot AsyncTI4), potem kod.
- **Praca blokami.** Jeden blok = jeden spójny, testowalny krok = commit po polsku.
- **QA po każdej zmianie — wszystko zielone przed commitem:**
  - backend: `uv run pytest -q` ; `uv run ruff check src tests` ; `uv run mypy src tests`
  - frontend: `npm run type-check` ; `npm run lint` ; `npm run build` (w `frontend/`)
- **Dokumentacja i komentarze po polsku.** Staguj konkretne pliki (nie `git add .`).
  Nie pushuj (`git push`) bez zgody.
- **Wszystko lokalne (offline).** Frontend ładuje grafiki i fonty wyłącznie lokalnie
  (Resolver_Zasobów `frontend/src/shared/assets/resolveAsset.ts`, fonty `@fontsource/*`) —
  żadnego CDN. Grafiki/fonty są POZA repo (D1); manifest `audit/assets_manifest.json`
  opisuje wymagany zestaw, a `uv run python -m src.audit sync_assets --from <katalog>`
  kopiuje je lokalnie. Spójność danych i lokalność sprawdza Audytor_Danych:
  `uv run python -m src.audit` (liczby wpisów, referencje, zewnętrzne URL-e, brakujące pliki).
- **Kod > dokument.** Przy wątpliwości sprawdzaj `src/` i testy, nie pamięć ani opis.

---

## 4a. Jak korzystać z Katalogu_Komponentów (dla następnych sesji)

Potrzebujesz karty akcji, agendy, celu, żetonu, talii, promissory note itd.?
**Czytaj z `registry.catalog` (`ComponentCatalog`) — NIE pisz własnego parsera JSON
i NIE hardkoduj list.** Katalog jest już zbudowany w `StaticDataRegistry` (filtr po
polu `source`, deduplikacja wg priorytetu źródeł).

```python
from src.core.components import ComponentCategory, ComponentRef

catalog = registry.catalog
cards = catalog.all(ComponentCategory.ACTION_CARD)      # słownik id -> model
agenda = catalog.get(ComponentCategory.AGENDA, "censure")  # pojedynczy model albo None
bundle = catalog.faction_bundle("arborec")               # liderzy/tech/promissory/… frakcji
refs = catalog.query_timing(trigger, phase)              # komponenty wg okna czasowego
```

- **Źródła kanoniczne (oficjalne)** definiuje WYŁĄCZNIE `src/core/sources.py`
  (`SOURCE_PRIORITY`). Importuj stamtąd — nie przeklejaj listy `base/pok/codex1-4/thunders_edge`.
- **Przez API (tylko odczyt):** `GET /components`, `/components/{kategoria}`,
  `/components/{kategoria}/{id}`, `/components/factions/{id}/bundle`, `/timing-specs`.
- **Gwarancje:** filtr po polu `source` (tylko aktywne/oficjalne źródła, nie po nazwie
  pliku); test regresji liczb (`audit/baseline_counts.json`); test anty-hardkodowania
  (`tests/test_no_hardcoded_data_guard.py`) — pilnuje, by nikt nie obchodził rejestru
  własnym loaderem ani nie duplikował listy źródeł.

---

## 5. Kolejność czytania na start sesji

1. Ten `README.md` — orientacja (cel + gdzie co jest).
2. `PROGRESS.md` — co ostatnio zrobione i co następne.
3. `PLAN_PELNA_ROZGRYWKA.md` — który etap silnika robimy teraz.
4. `RULES.md` — zanim dotkniesz mechaniki, sprawdź/zapisz regułę.
5. Realny kod w `src/` + testy — nadrzędne źródło prawdy o stanie.
