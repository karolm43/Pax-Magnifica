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
   walka, status, agenda. Gra „wie", co wolno i prowadzi przebieg rundy.
3. **Bot AI** (cel końcowy) — warstwa decyzyjna (strategiczna → operacyjna → taktyczna),
   która gra frakcją samodzielnie. Silnik z etapu 2 jest jej „regułami świata".

Pełna wizja i architektura docelowa: [`specyfikacja_techniczna_i_architektura_systemu.md`](specyfikacja_techniczna_i_architektura_systemu.md).

---

## 2. Mapa dokumentów (co czytać do czego)

| Dokument | Rola | Aktualność |
|---|---|---|
| **`README.md`** (ten plik) | Indeks: cel, struktura, konwencje, kolejność czytania. | 🟢 żywy |
| **`PROGRESS.md`** | Dziennik bloków pracy: co zrobione, decyzje, QA. Czytaj na start sesji. | 🟢 żywy |
| **`RULES.md`** | **Źródło prawdy dla mechanik TI4.** Każda reguła ma źródło (LRR / bot). | 🟢 żywy |
| **`PLAN_PELNA_ROZGRYWKA.md`** | **Główny plan silnika** (etapy E1–E7) + lista frakcji i gimmicków. | 🟢 żywy |
| **`ARCHITEKTURA_KODU.md`** | **Warstwy (core/api/ai), konwencje rozwoju, wzorzec hooków, dług techniczny.** Czytaj przed dodaniem nowej mechaniki. | 🟢 żywy |
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
│   │   ├── registry.py           #     StaticDataRegistry — ładuje dane z assets/ po `source`
│   │   ├── models.py             #     modele statyczne (UnitDef, PlanetDef, FactionDef, ...)
│   │   ├── game_state.py         #     GameState / PlayerState / SystemState (+ clone)
│   │   ├── hex_grid.py           #     siatka heksów (q,r,s), sąsiedztwo, wormhole, anomalie
│   │   ├── map_string.py         #     parser map stringa AsyncTI4 -> HexGrid
│   │   ├── positions.py          #     pozycje RPP (101, 201, ...) -> współrzędne
│   │   ├── unit_catalog.py       #     jawne tabele reguł jednostek (umiejscowienie, asyncId, limity)
│   │   ├── faction_setup.py      #     setup frakcji (parser startingFleet, rozstawienie)
│   │   ├── turn_flow.py          #     E1: fazy + kolejność tur (czyste funkcje)
│   │   ├── strategy_phase.py     #     E2: faza strategii (wybór kart, trade goods)
│   │   └── event_store.py        #     EventStore (SQLite) — Undo/Redo/God-Mode
│   └── api/                      #   warstwa HTTP/WS
│       ├── app.py                #     fabryka FastAPI + wszystkie endpointy + WebSocket
│       ├── web_data.py           #     build_web_data: GameState -> dokument dla frontu (KONTRAKT UI)
│       ├── schemas.py            #     DTO żądań/odpowiedzi (Pydantic)
│       └── state_service.py      #     jedyne miejsce mutujące stan (commit + broadcast)
├── frontend/                     # FRONTEND (React/Vite) — viewer planszy (bazuje na ti4_web)
│   └── src/
│       ├── api/                  #   hooki danych (useBoardEditor, useNewGame, ...)
│       ├── domains/              #   funkcjonalne obszary UI (map, player, game-shell, cards, ...)
│       ├── entities/             #   WBUDOWANE statyczne dane (jednostki/planety/techy) + lookupy
│       ├── state/                #   store (Zustand) + kontekst gry
│       └── ds/                   #   design system (komponenty bazowe)
├── tests/                        # TESTY backendu (pytest) — jeden plik per moduł core/api
├── assets/                       # DANE GRY (AsyncTI4): JSON w repo (~5 MB), grafiki z CDN
│   ├── enabled_sources.json      #   aktywne źródła danych (base, pok, codex1-4, thunders_edge)
│   ├── data/ systems/ planets/ alias/   # dane silnika (wersjonowane)
│   └── ... (grafiki/fonty — ignorowane przez .gitignore)
└── TI4_map_generator_bot/        # ŹRÓDŁO REGUŁ (Java, poza repo) — czytamy, nie linkujemy
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
- **Kod > dokument.** Przy wątpliwości sprawdzaj `src/` i testy, nie pamięć ani opis.

---

## 5. Kolejność czytania na start sesji

1. Ten `README.md` — orientacja (cel + gdzie co jest).
2. `PROGRESS.md` — co ostatnio zrobione i co następne.
3. `PLAN_PELNA_ROZGRYWKA.md` — który etap silnika robimy teraz.
4. `RULES.md` — zanim dotkniesz mechaniki, sprawdź/zapisz regułę.
5. Realny kod w `src/` + testy — nadrzędne źródło prawdy o stanie.
