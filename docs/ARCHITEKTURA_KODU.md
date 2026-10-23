# Architektura kodu — warstwy, konwencje, jak rozwijać bez chaosu

🟢 **ŻYWY.** Ten dokument odpowiada na pytanie: *„gdzie trafia nowa funkcja i jak nie
utopić projektu w złożoności, gdy dojdzie silnik taktyczny i AI?"*. Twilight to gra,
w której prawie wszystko łamie reguły bazowe (frakcje, technologie, karty) — architektura
MUSI to przewidywać. Stosuj te zasady przy każdej nowej mechanice.

---

## 1. Złota zasada: reguły w `core/`, HTTP w `api/`, decyzje w `ai/`

Trzy warstwy, ściśle rozdzielone. **Zależności idą tylko w jedną stronę:**

```
  api/  (HTTP/WS)        ai/  (bot — przyszłość)
     \                   /
      \                 /
       ▼               ▼
         core/  (reguły gry — czyste funkcje nad GameState)
                         │
                         ▼
              registry / assets  (dane, zero reguł)
```

- **`core/` NIE WIE, że istnieje HTTP.** Żadnych importów FastAPI, żadnych `HTTPException`,
  żadnych requestów. Czyste funkcje: `state -> nowy state` (lub wynik/wyjątek domenowy).
- **`api/` jest cienkie.** Endpoint = (1) odczyt stanu, (2) wywołanie funkcji z `core/`,
  (3) commit + broadcast, (4) mapowanie błędów domenowych na HTTP. **Zero reguł gry w endpointcie.**
- **`ai/` (przyszłość) woła wyłącznie `core/`.** Bot generuje akcję → `core/` ją waliduje
  i stosuje. Dokładnie te same funkcje, których używa `api/`. Dzięki temu bot i człowiek
  grają przez jedną ścieżkę reguł — nie da się ich rozjechać.

> **Test papierka lakmusowego:** jeśli nową regułę TI4 (ruch, walka, zdolność frakcji)
> da się przetestować TYLKO przez `TestClient`/HTTP — jest w złym miejscu. Reguła musi
> być testowalna jako `funkcja(state, args) -> state` bez sieci.

---

## 2. Mapa: gdzie trafia jaka funkcja

| Rodzaj kodu | Katalog / plik | Przykłady |
|---|---|---|
| Stan gry (model) | `core/game_state.py` | `GameState`, `PlayerState`, `SystemState` |
| Dane statyczne (model) | `core/models.py` | `UnitDef`, `FactionDef`, `StrategyCardDef` |
| Ładowanie danych | `core/registry.py` | `StaticDataRegistry`, `strategy_card_set()` |
| Tabele reguł jednostek | `core/unit_catalog.py` | umiejscowienie, asyncId, limity |
| **Reguły fazy/akcji** | `core/<faza>.py` | `turn_flow.py`, `strategy_phase.py`, (przyszłe: `tactical.py`, `combat.py`, `status.py`, `agenda.py`) |
| Setup / mapa | `core/faction_setup.py`, `core/map_string.py`, `core/hex_grid.py` | |
| Historia / Undo | `core/event_store.py` | |
| Serializacja do UI | `api/web_data.py` | `build_web_data` (kontrakt z frontem) |
| Endpointy HTTP/WS | `api/routers/<temat>.py` | (po refaktorze — patrz §4) |
| DTO żądań/odpowiedzi | `api/schemas.py` | |
| Mutacja + broadcast | `api/state_service.py` | jedyne miejsce commitujące stan |
| Decyzje bota (przyszłość) | `ai/` | strategiczna → operacyjna → taktyczna |

**Reguła dodawania nowej mechaniki (np. faza taktyczna E3):**
1. Regułę spisz do `docs/RULES.md` ze źródłem (LRR / bot AsyncTI4).
2. Zaimplementuj jako czyste funkcje w `core/tactical.py` (+ test jednostkowy bez HTTP).
3. Dodaj cienki endpoint w `api/routers/tactical.py`, który woła te funkcje.
4. Jeśli trzeba — dołóż pola do web-data w `api/web_data.py`.
5. QA + commit.

---

## 3. Jak Twilight „łamie zasady" — wzorzec hooków (kluczowe dla frakcji/tech/kart)

Prawie każda frakcja, technologia i karta modyfikuje reguły bazowe (inny ruch, dodatkowe
trafienia, darmowe produkcje…). Gdybyśmy wpletli te wyjątki w `if faction == ...` w kodzie
reguł, `core/` stałby się nieczytelny po 10 frakcjach. Dlatego:

- **Reguła bazowa** w `core/` liczy wynik „gołej" gry (np. wartość ruchu, liczba trafień).
- **Modyfikatory** (zdolności frakcji, technologie, karty, prawa) to **hooki** rejestrowane
  w jednym miejscu (`core/rules_hooks.py` — do utworzenia przy E7), które reguła bazowa
  odpytuje w zdefiniowanych **oknach** (przed ruchem, po rzucie na trafienia, przy produkcji…).
- Hook dostaje kontekst (`state`, `player`, `system`) i zwraca modyfikator/decyzję. Nowa
  frakcja = nowy plik hooka + wpis w `RULES.md` + test. **Zero zmian w regule bazowej.**

> To jest architektoniczna odpowiedź na „Twilight łamie własne zasady". Reguła bazowa
> zostaje prosta i stabilna; cała asymetria żyje w izolowanych, testowalnych hookach.
> Szczegóły i lista 30 frakcji: `PLAN_PELNA_ROZGRYWKA.md` (sekcja „Frakcje").

---

## 4. Dług techniczny do spłaty PRZED E3 (żeby nie urosło w chaos)

Stan na teraz (zmierzony):

| Plik | Linie | Ryzyko |
|---|---|---|
| `api/web_data.py` | ~885 | 🟡 duży, ale jeden temat (serializacja) — rośnie liniowo |
| `api/app.py` | ~849 | 🔴 **27 endpointów + 37 funkcji w jednej `create_app`; ~44 miejsca mutują stan W ENDPOINTCIE** |
| `core/*` | < 270 każdy | 🟢 zdrowe — czyste funkcje, dobrze podzielone |

**Problem `app.py`:** część logiki God-Mode (np. `_sync_controlled_planets`, `_zone_bucket`,
`_resolve_player_id`, przesuwanie jednostek) żyje w warstwie HTTP — AI jej nie wywoła, a plik
przy E3 urośnie do ~1500 linii. **Refaktor zalecany PRZED E3:**

1. **Wyciągnąć logikę God-Mode do `core/board_edit.py`** — czyste funkcje edycji jednostek/
   planet/kontroli (to, co dziś jest w `_zone_bucket`, `_sync_controlled_planets` itd.).
   Endpointy stają się cienkie.
2. **Rozbić `app.py` na routery** (`api/routers/`): `board.py` (mapa/jednostki/God-Mode),
   `players.py`, `flow.py` (tury/fazy), `strategy.py`, `history.py`, `game.py` (new/state/web-data).
   `create_app` tylko montuje routery.
3. **Opcjonalnie podzielić `web_data.py`** na podmoduły (`web_data/players.py`, `.../tiles.py`,
   `.../strategy.py`) gdy przekroczy ~1000 linii.

Efekt: każdy temat w swoim pliku < ~300 linii, reguły w `core/` (testowalne i gotowe dla AI),
`api/` cienkie. To jest warunek, żeby E3 + AI nie utopiły projektu.

---

## 5. Lista kontrolna przy każdej nowej funkcji (trzymaj się jej)

- [ ] Reguła TI4? → najpierw wpis w `RULES.md` ze źródłem, potem kod.
- [ ] Logika gry trafia do `core/` jako czysta funkcja (testowalna bez HTTP).
- [ ] Endpoint w `api/` tylko woła `core/` + commit/broadcast + mapuje błędy.
- [ ] Wyjątek domenowy (`ValueError`/własny) w `core/`, mapowany na HTTP w `api/`.
- [ ] Modyfikator frakcji/tech/karty = hook, nie `if` w regule bazowej.
- [ ] Test: jednostkowy dla `core/`, integracyjny (TestClient) dla endpointu.
- [ ] Plik > ~300 linii? → rozważ podział na podmoduł tematyczny.
- [ ] QA zielone (pytest/ruff/mypy + frontend build) → commit po polsku.
