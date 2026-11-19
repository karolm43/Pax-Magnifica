# Architektura kodu — warstwy, konwencje, jak rozwijać bez chaosu

🟢 **ŻYWY.** Ten dokument odpowiada na pytanie: *„gdzie trafia nowa funkcja i jak nie
utopić projektu w złożoności, gdy dojdzie silnik taktyczny i AI?"*. Twilight to gra,
w której prawie wszystko łamie reguły bazowe (frakcje, technologie, karty) — architektura
MUSI to przewidywać. Stosuj te zasady przy każdej nowej mechanice.

---

## 1. Złota zasada: reguły w `core/`, HTTP w `api/`, decyzje w `engine/`

Trzy warstwy, ściśle rozdzielone. **Zależności idą tylko w jedną stronę:**

```
  api/  (HTTP/WS) ───►  engine/  (bot — src/engine/, plan: docs/bot/PLAN.md)
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
- **`engine/` (bot, `src/engine/`) woła wyłącznie `core/`** (nigdy `api/`; `api/` uruchamia bota).
  Instrukcje warstwy: `src/engine/CLAUDE.md`. Bot generuje akcję → `core/` ją waliduje
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
| Ładowanie danych | `core/registry.py` | `StaticDataRegistry`, `strategy_card_set()`, `catalog` |
| Źródła kanoniczne | `core/sources.py` | `SOURCE_PRIORITY`, `validate_enabled_sources` |
| **Katalog_Komponentów** | `core/components.py` | modele kategorii, `CATEGORY_SPECS`, `ComponentCatalog` |
| Ładowanie komponentów | `core/component_loader.py` | `select_entries`, `load_components`, `LoadReport` |
| Spójność referencji | `core/references.py` | `find_unresolved_references`, `ReferenceReport` |
| Specyfikacja_Czasowa | `core/timing_spec.py` | `parse_timing`, `TRIGGER_WINDOW_MAP` (D10) |
| Rejestr_Efektów | `core/effects_registry.py` | `EffectStatus`, `EffectRegistry`, `coverage` |
| Powiązania z regułami | `core/rules_links.py` | `RulesTopicIndex`, `match` (Zrzut_Reguł) |
| Tabele reguł jednostek | `core/unit_catalog.py` | umiejscowienie, asyncId, limity |
| **Reguły fazy/akcji** | `core/<faza>.py` | `turn_flow.py`, `strategy_phase.py`, `tactical.py`, `movement.py`, `combat.py`, `production.py`, `strategic_action.py` |
| Okna czasowe | `core/timing.py` | kolejka respondentów (RULES.md 29.2) |
| Setup / mapa | `core/faction_setup.py`, `core/map_string.py`, `core/hex_grid.py` | |
| Historia / Undo | `core/event_store.py` | |
| **Audytor_Danych / lokalność** | `src/audit/` | `locality.py`, `assets_manifest.py`, `frontend_data.py`, `diffs.py`, `report.py`, `sync_assets.py` (CLI `python -m src.audit`) |
| Serializacja do UI | `api/web_data.py` | `build_web_data` (kontrakt z frontem); części: `web_game` (stan rundy) → `web_tiles` (kafelki) → `web_player_units` → `web_players` (+ `web_agenda`, `web_objectives`, `web_points`, `web_setup`) |
| Endpointy HTTP/WS | `api/routers/<temat>.py` | (po refaktorze — patrz §4) |
| DTO żądań/odpowiedzi | pakiet `api/schemas/` (`common`, `setup`, `tactical`, `combat`, `cards`; import zawsze `src.api.schemas`), `api/schemas_components.py` | |
| Mutacja + broadcast | `api/state_service.py` | jedyne miejsce commitujące stan |
| Decyzje bota | `src/engine/` (plan: `docs/bot/PLAN.md`) | strategiczna → operacyjna → taktyczna |

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
  w jednym miejscu (`core/rules_hooks.py`, GOTOWE), które reguła bazowa odpytuje w
  zdefiniowanych **punktach zaczepienia** (ruch, walka, produkcja, płatność…).
- **Gdzie co leży:** rejestr i API (`forbidden` / `permits` / `modify`, kolejność REPLACE>FORBID>
  PERMIT>MODIFY>TRIGGER>PERSISTENT) w `core/rules_hooks.py`; same wyjątki tematycznie w pakiecie
  `core/hooks/` (`factions/<frakcja>.py`, `technologies.py`; kolejne dopisz i zaimportuj w
  `hooks/__init__.py`). Nazwy punktów to stałe `POINT_*` w `rules_hooks.py`. Hook działa tylko dla
  gracza, który posiada jego źródło (frakcja/technologia). `covers="<kategoria>:<id>"` oznacza
  komponent jako IMPLEMENTED w rejestrze efektów; raport: `docs/POKRYCIE_HOOKOW.md` (generowany:
  `uv run python -m src.audit.hook_coverage --write`).
- **Nowy wyjątek (przepis):** RULES.md (komponent + źródło) -> funkcja w `core/hooks/<temat>.py`
  z `@register(POINT_*, HookSource(...), HookKind.*, covers=...)` -> test w parze „bez/z
  wyjątkiem” (`rules_hooks.temporary_hooks()`) -> przegeneruj raport pokrycia.
- Hook dostaje kontekst (`state`, `player`, `system`) i zwraca modyfikator/decyzję. Nowa
  frakcja = nowy plik hooka + wpis w `RULES.md` + test. **Zero zmian w regule bazowej.**

> To jest architektoniczna odpowiedź na „Twilight łamie własne zasady". Reguła bazowa
> zostaje prosta i stabilna; cała asymetria żyje w izolowanych, testowalnych hookach.
> Szczegóły i lista 30 frakcji: `PLAN_PELNA_ROZGRYWKA.md` (sekcja „Frakcje").

---

## 3a. Karta od A do Z (obowiązujący przepis; cel: WSZYSTKIE karty gotowe)

Każda karta przechodzi ten sam potok, więc dodanie kolejnej to jeden wpis w każdej warstwie, bez ruszania reguł bazowych:

| Warstwa | Plik | Co robi |
|---|---|---|
| Dane | `assets/data/...` | tekst i okno karty (nigdy z pamięci); `timing_spec` klasyfikuje wyzwalacz |
| Reguła | `docs/RULES.md` (+ `rules_tirules/`) | wpis ze źródłem, ⚠ przy założeniach |
| Efekt | `core/hooks/action_cards*.py` → `@register_effect("action_cards:<id>")` | zmienia stan tylko przez punkty centralne |
| Wybory | `core/hooks/action_card_inputs.py` → `@register_effect_inputs(...)` | opis formularza: `choice` / `multi` / `number`, opcje liczy silnik |
| Zagrywalność | `core/action_cards.playability` | tura, faza, okno, jedna akcja, legalne cele |
| API | `api/routers/action_cards.py` | `GET /action-card/playable`, `GET /action-card/{id}/inputs`, `POST /action-card/play` |
| UI | `BottomHandDock` (przeciąganie), `ActionCardPlayModal` (formularz) | front nie zna kart, renderuje opis z silnika |
| Testy | `tests/test_action_cards.py` | para bez/z efektem, round-trip formularza, błędy |
| Raport | `docs/POKRYCIE_HOOKOW.md` | `uv run python -m src.audit.hook_coverage --write` |
| Reakcja (when/after/before/start/end) | `core/reaction_cards.py` + `core/hooks/reactions_*.py` | okno WYLICZANE ze stanu (`@window_provider`), adres z tekstu okna (`declare_reaction` nadpisuje), warunek karty; efekt jak wyżej, okno w `params["__window"]`; efekt trwały = `active_effects` + hook `card_effect_source`; karta reakcji nie zużywa akcji (RULES.md 53.5) |
| Kości | `dice.record_table_roll(...)` w efekcie | **KAŻDY rzut kością** (karta, relikt, przełom…) zapisuje się tym wywołaniem, a UI odtwarza go fizycznymi kośćmi (patrz 3a.1) |

**Zasada UX:** kartę zagrywa się przeciągając ją z ręki, a podnieść można tylko kartę, którą silnik pozwala zagrać
(`playability`). Inne rodzaje kart (reakcje, promissory notes) dostają ten sam standard — patrz „CEL PRODUKTOWY”
w `PLAN_PELNA_ROZGRYWKA.md`.

### 3a.1. Rzuty kośćmi: JEDNA fizyczna scena kości (obowiązuje wszędzie)

Kości w grze są fizyczne (d10, bryła 3D, odbicia, dźwięk), a wynik zawsze liczy silnik (`core/dice.py`, seedowalny
RNG); UI tylko odtwarza. **Nowy rzut kością NIE dostaje własnej animacji ani własnego „bannera z kostką"** — używa
wspólnej sceny:

| Sytuacja | Backend | Frontend |
|---|---|---|
| Rzut poza walką (karta akcji, relikt, przełom, Fracture) | po losowaniu `dice.record_table_roll(state, player_id, kind, label, wyniki, hits_on=… lub hit_values=…, summary=…)` | nic: `TableRollWatcher` (montowany w `GameMapPage`) sam rzuca kośćmi, a po wylądowaniu pokazuje `summary` |
| Okno z przyciskiem rzutu (Space Cannon, bombardowanie, SCD) | rzut w `core/` jak dotąd, wynik w dzienniku/`pending` | przycisk = `HoldRollButton` + `onHold={soloHold(liczba_kości, rgb)}` (pula po przytrzymaniu); nowy wynik → `useDiceStage.getState().throwDice({...})`, a zwrócone `pauseMs` = czas, do którego **nie zdradzamy wyniku** w UI |
| Walka (AFB / rzut rundy) | jak dotąd | wbudowany stół w `BattleOverlay` (`DiceTray`, `DicePool`) — nie używa sceny wspólnej |

Pliki: `frontend/src/domains/dice/` (`diceStage.ts`, `DiceStageHost.tsx`, `HoldRollButton.tsx`, `TableRollWatcher.tsx`),
`frontend/src/domains/battle/` (`diceRoll.ts` plan i fizyka, `dieGeometry.ts` bryła d10, `DieMesh.tsx`, `DiceTray.tsx`,
`DicePool.tsx`). Wszystko, co zależy od wyniku (trafienia, panel strat, salwy efektów), startuje po `pauseMs`.

---

## 3b. Hook zdarzeniowy (okna czasowe) — RULES.md 54

1. Znajdź okno komponentu w `docs/OKNA_CZASOWE.md` (zdarzenie + moment).
2. Zarejestruj: `@rules_hooks.on_event(GameEvent.X, Moment.WHEN, HookSource(...), kind=HookKind.TRIGGER|REPLACE, optional=True/False)` w `core/hooks/<temat>.py`.
3. Jeśli zdarzenie nie jest emitowane (`EVENT_INFO.emitted_by is None`) — dodaj `triggers.fire(...)` w odpowiedniej funkcji `core/` i uzupełnij `emitted_by` (test `test_emitted_by_zgadza_sie_z_kodem` pilnuje zgodności).
4. Efekt z czasem trwania: `active_effects.add_effect(state, key, scope, owner)`; wygasanie przez `triggers.EXPIRY`.
5. Karty z ręki nie są źródłami hooków (STOP, 43.4) — grane przez okno ACTION.

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
| `api/routers/components.py` | — | **tylko-odczyt** Katalog_Komponentów: `/components`, `/components/{kat}`, `/components/{kat}/{id}` (komponent + `TimingSpec` + status efektu + tematy reguł), `/components/factions/{id}/bundle`, `/timing-specs?trigger=&phase=`. Bez `broadcast`; 404 z kategorią i id. |
| `api/routers/history.py` | ~76 | patch God-Mode, PUT state, historia, undo/redo. |

> **Stan 2026-11-11:** tabela wyżej to stan z refaktoru; dziś routerów jest 32 — po jednym na temat:
> `tactical`, `battle`, `invasion`, `space_cannon`, `production`, `capacity`, `fleet_pool`, `status`, `agenda`,
> `action_cards`, `hold`, `window`, `offers`, `relics`, `exploration`, `frontier_cards`, `technology`, `decks`,
> `transactions`, `thunders_edge`, `epilogue`, `clock`, `network`, `setup`, `rules` (+ wymienione wyżej).
> Wzorzec routera bez zmian; dochodzi `actor: ActorId` albo `dependencies=[HostOnly]` (RULES.md 44.1a).

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

**Podział dużych modułów (2026-11-19):** warstwy zależą tylko w dół, a moduł bazowy eksportuje
nazwy dalej (`from x import n as n`, mypy strict), więc wywołania `battle.side_units` itp. się nie zmieniają.
`core/battle_units.py` → `battle.py` → `battle_rerolls.py` (przerzuty/zmiany kości po rzucie);
`core/invasion_common.py` → `invasion_bombard.py` / `invasion_defense.py` → `invasion.py`;
`core/movement_paths.py` → `movement.py`. Front: `api/boardQueries.ts` (zapytania tylko do odczytu,
eksportowane dalej przez `useBoardEditor.ts`), `battle/BattleVolley.tsx` i `BattleAssaultCannon.tsx`
(warstwy animacji `BattleOverlay`). Testy podmieniające funkcję (`monkeypatch.setattr(mod, ...)`)
muszą celować w moduł, który ją WYWOŁUJE.
Przy E3 dodajemy `core/tactical.py` + `api/routers/tactical.py`.

---

## 4a. Fundacja danych i Audytor_Danych (spec local-ti4-data-foundation)

Osobna warstwa, która KARMI `core/` kompletem danych TI4 i pilnuje lokalności. Trzyma się
tej samej zasady co reszta: logika to czyste funkcje, I/O cienkie, zero reguł z pamięci.

- **Katalog_Komponentów (`core/components.py`).** Jedno miejsce z typowanymi modelami
  WSZYSTKICH kategorii TI4 (karty akcji, agendy, cele, attachmenty, eksploracje, relikty,
  promissory, żetony, anomalie graniczne, wydarzenia, karty generyczne, talie + istniejące
  jednostki/planety/frakcje/techy/liderzy). Kształty JSON żyją TYLKO w `CATEGORY_SPECS` —
  zero zahardkodowanych komponentów. Pola spoza modelu lądują w `raw` (nic nie ginie, R5.7).
- **Wybór po `source` (`core/component_loader.py`, `core/sources.py`).** Filtr po POLU
  `source` (nie po nazwie pliku) wg `assets/enabled_sources.json`; kolizje `id` rozstrzyga
  priorytet źródła `thunders_edge > pok > codex4..1 > base` (D9, RULES.md 14). `LoadReport`
  liczy pominięte/bez źródła.
- **Specyfikacja_Czasowa (`core/timing_spec.py`).** `parse_timing` klasyfikuje frazę okna
  (`when/after/before/instead/...`) po prefiksie, zachowując oryginalny tekst; `TRIGGER_WINDOW_MAP`
  (D10, ⚠️ ZAŁOŻENIE w RULES.md) wiąże rodzaj z `WindowType` z `core/game_state.py`. Pod przyszłe
  reakcje when/after na modelu okien (RULES.md 29.2).
- **Rejestr_Efektów (`core/effects_registry.py`).** `id komponentu -> status` (`not_implemented`
  / `implemented` / `manual`), dane w `assets/config/effects_status.json`. Pod hooki z RULES.md 29;
  SAM w sobie nie koduje żadnego efektu karty (to przyszłe hooki, patrz §3).
- **Powiązania z regułami (`core/rules_links.py`).** Deterministyczne (równość znormalizowanej
  nazwy/aliasu, bez zgadywania) łączenie komponentu z tematami Zrzutu_Reguł (`docs/rules_tirules/`).
  Reguła + doprecyzowanie → Zrzut_Reguł; treść/parametry karty → JSON w `assets/data/`.
- **Audytor_Danych (`src/audit/`).** CLI `uv run python -m src.audit` (raport tekstowy; `--json`,
  `--write-baseline`, `--write-manifest`). Liczy wpisy per kategoria×źródło, wykrywa nierozwiązane
  referencje, `unclassified` timing, zewnętrzne URL-e, brakujące/nieużywane grafiki z manifestu.
  `locality.py` = Strażnik_Lokalności (żaden odczyt spoza `PROJECT_ROOT`, brak ścieżek do
  Źródeł_Referencyjnych w kodzie). Błąd krytyczny → niezerowy kod wyjścia.
- **Lokalność grafik/fontów (D1).** Grafiki i fonty są POZA repo; `audit/assets_manifest.json`
  (w repo) opisuje wymagany zestaw, a `src/audit/sync_assets.py --from <katalog>` kopiuje je
  lokalnie. Frontend bierze je przez Resolver_Zasobów (`frontend/src/shared/assets/resolveAsset.ts`,
  `assetManifest.json`) — zero CDN. Konfiguracja Audytora i baseline liczb są wersjonowane
  (`audit/*.json`, D1/D12 — patrz `.gitignore`).

---

## 5. Lista kontrolna przy każdej nowej funkcji (trzymaj się jej)

- [ ] Reguła TI4? → najpierw wpis w `RULES.md` ze źródłem, potem kod.
- [ ] Logika gry trafia do `core/` jako czysta funkcja (testowalna bez HTTP).
- [ ] Endpoint w `api/` tylko woła `core/` + commit/broadcast + mapuje błędy.
- [ ] Wyjątek domenowy (`ValueError`/własny) w `core/`, mapowany na HTTP w `api/`.
- [ ] Modyfikator frakcji/tech/karty = hook, nie `if` w regule bazowej.
- [ ] Nowa karta = pełny potok z sekcji 3a (efekt + formularz + zagrywalność + test + raport pokrycia).
- [ ] Nowy WIDOCZNY skutek (nowy zasób/komponent/stan gracza lub stołu)? → dopisz go do feedu
      „Activity" (panel historii): fakt w `core/activity.py` (`_facts` i podfunkcje, różnica stanów
      przed/po; ręce tylko jako LICZBY) + opis w `ActivityPanel/describeActivity.tsx` (`describeFact`)
      + test w `tests/test_activity.py`. Nowa akcja z własną etykietą commitu => też `_parse_*`.
- [ ] Test: jednostkowy dla `core/`, integracyjny (TestClient) dla endpointu.
- [ ] Plik obejmuje już różne tematy (zwykle > ~500 linii)? → rozważ podział na podmoduł tematyczny. Spójnego modułu nie dziel tylko dla liczby linii.
- [ ] QA zielone (pytest/ruff/mypy + frontend build) → commit po polsku.
