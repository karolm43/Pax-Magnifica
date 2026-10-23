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

## 4. Struktura warstwy API (po refaktorze przed E3) — ✅ spłacone

`app.py` jest teraz CIENKĄ fabryką (montaż routerów + WebSocket + static, ~100 linii).
Endpointy pogrupowane tematycznie w `api/routers/`, logika God-Mode w `core/board_edit.py`.

| Plik | Linie | Rola |
|---|---|---|
| `core/board_edit.py` | ~300 | **Czyste funkcje God-Mode** (edycja jednostek/planet/kontroli/gracza). Bez HTTP — gotowe dla AI. |
| `api/app.py` | ~100 | Fabryka: montaż routerów, WebSocket `/ws`, static, CORS, lifespan. |
| `api/context.py` | ~45 | `AppContext` (service/manager/registry/current_grid) + `broadcast_map`; zależność `get_ctx`. |
| `api/serializers.py` | ~130 | `build_map_view` + stałe setupu (`DEFAULT_MAP_STRING`, `AUTO_SLOT_ORDER`). |
| `api/routers/game.py` | ~190 | stan, mapa, web-data, frakcje, nowa gra, load mapy, setup gracza. |
| `api/routers/board.py` | ~108 | jednostki w przestrzeni/na planetach, edycja, ruch (woła `core.board_edit`). |
| `api/routers/players.py` | ~34 | edycja gracza. |
| `api/routers/flow.py` | ~61 | tury/fazy/runda (E1). |
| `api/routers/strategy.py` | ~86 | pula kart, wybór, zagranie (E2). |
| `api/routers/history.py` | ~76 | patch God-Mode, PUT state, historia, undo/redo. |

**Wzorzec routera (trzymaj się go przy E3):**
```python
@router.post("/sciezka", response_model=...)
async def handler(request: XRequest, ctx: AppContext = Depends(get_ctx)) -> ...:
    try:
        new_state = core_module.funkcja(ctx.service.current_state(), ctx.current_grid, ...)
    except ValueError as exc:                 # błąd domenowy z core/
        raise HTTPException(422, str(exc)) from exc
    ctx.service.replace_state(new_state, label="...")   # commit → historia
    await ctx.service.broadcast(); await ctx.broadcast_map()
    return ctx.service.envelope()
```

**Pozostały dług (niski priorytet):** `web_data.py` (~885) — jeden temat (serializacja),
rośnie liniowo. Podzielić na podmoduły (`web_data/players.py`, `.../tiles.py`, `.../strategy.py`)
gdy przekroczy ~1000 linii. Przy E3 dodajemy `core/tactical.py` + `api/routers/tactical.py`.

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
