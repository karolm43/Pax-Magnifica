# Warianty gry: fanowskie talie, erraty kart, własne komponenty

Jak dodać do gry fanowski zestaw (Absol, Black Spectrum…), erratę pojedynczej karty albo
własny komponent. Mechanizm: **moduły wariantów** — dane w `assets/config/variants.json`,
logika w `src/core/variants.py`. Kod nie zna żadnej konkretnej talii fanowskiej.

## Jak to działa

- Moduł = wpis w `assets/config/variants.json`. Wybiera się go **per gra** w Ustawieniach
  (General → Game variants). Lista przełączników powstaje z manifestu, więc nowy moduł
  nie wymaga zmian w UI. Wybór trafia do `/game/new` (`variants`), a stamtąd do
  `GameState.decks.variants`.
- `source` modułu to pole `source` kart w `assets/data/<kategoria>/*.json`. Źródło **nie**
  trafia do `enabled_sources.json`. Loader dociąga z niego tylko to, czego moduł potrzebuje
  (`variants.load_plan`), a reszta danych tego źródła (jednostki, technologie…) zostaje
  nieaktywna.
- Dwa rodzaje zmian:
  - `decks: {typ: alias}` — **cała talia** danego typu w grze to talia wariantu
    (`assets/data/decks/*.json`). Przykład: Absol relics → `relics_absol`.
  - `replaces: [typ]` — **errata pojedynczych kart**: karty źródła z polem
    `homebrewReplacesID` zastępują oficjalne karty w talii gry. Jedna karta może zastąpić
    kilka kopii (3× Shard of the Throne Absol za 1× `shard`). `promissory_note` podmienia
    wspólne notki przy rozdawaniu (`<color>_ps` → `absol_<color>_ps`).
- Typy talii: `agenda`, `action_card`, `relic`, `explore`, `secret_objective`,
  `public_stage_1_objective`, `public_stage_2_objective`, `promissory_note` (tylko
  `replaces`).
- Każda karta wariantu ma **własne id** (np. `absol_obsidian`), więc jej efekt to osobny
  hook (`core/hooks/`, `covers="relics:absol_obsidian"`). Bez hooka karta działa jak
  ręczna ewidencja, tak samo jak każda inna nieoprogramowana karta.

## Przepis: dodanie fanowskiej talii (np. Black Spectrum)

1. Sprawdź dane: karty w `assets/data/<kategoria>/<zrodlo>.json`, talia w
   `assets/data/decks/<zrodlo>.json` (alias i `type`).
2. Dopisz moduł do `assets/config/variants.json`:
   ```json
   {
     "id": "bsp_relics",
     "name": "Black Spectrum relics",
     "description": "Replaces the relic deck with the Black Spectrum one.",
     "source": "black_spectrum",
     "badge": "BSP",
     "decks": { "relic": "relics_bsp" }
   }
   ```
3. `uv run python scripts/gen_active_decks.py` (front: przełącznik + pula kart talii).
4. `uv run python -m src.audit --write-baseline` (nowe liczby kart w katalogu).
5. Testy: `uv run pytest -q tests/test_variants.py tests/test_components_real_data.py
   tests/test_active_decks_sync.py`. Dopisz test składu talii nowego modułu w
   `tests/test_variants.py`.
6. Efekty kart: hooki pod id kart wariantu, zgodnie z pipeline'em `ARCHITEKTURA_KODU.md` §3a.
7. Restart backendu (manifest wczytuje się przy starcie).

## Przepis: errata pojedynczej karty (własna albo fanowska)

1. Nowy wpis karty z własnym `source` (np. `pax_errata`) w pliku
   `assets/data/<kategoria>/pax_errata.json`, z **nowym** id i polem
   `"homebrewReplacesID": "<id oficjalnej karty>"`.
2. Moduł: `{"id": "pax_errata", "name": "…", "source": "pax_errata",
   "replaces": ["relic", "action_card"], "default": true}`. `default: true` włącza moduł
   w nowych grach od razu.
3. Kroki 3–7 z przepisu wyżej.

## Przepis: własny nowy komponent (karta)

Tak jak errata, tylko bez `homebrewReplacesID`. Karta musi trafić do talii, więc:
własna talia w `assets/data/decks/pax.json` (pełna lista kart, np. oficjalne + nowe) i
moduł z `decks`.

## Ograniczenia (stan na 2026-11-18)

- **Front pokazuje tylko karty, które zna.** Teksty kart we froncie pochodzą ze starszego
  eksportu AsyncTI4 (`frontend/src/entities/data/*.ts`). Absol tam jest, **Black Spectrum
  i własne karty nie**. Nowe źródło wymaga dopisania kart do tych plików. Docelowo front
  powinien czytać teksty z katalogu backendu.
- Pula talii eksploracji we froncie (`explorationPool`) nie uwzględnia modułów. Silnik
  uwzględnia.
- Technologie, jednostki, frakcje, liderzy, karty strategii, planety i systemy **nie są
  jeszcze objęte modułami**: rejestr ładuje je globalnie, a nie per gra. Dziś zmienia się
  je tylko przez `enabled_sources.json` (dla wszystkich gier). Liderzy z
  `homebrewReplacesID` z włączonego źródła zastępują starszych (`registry._apply_leader_replacements`).
- Fanowska talia z kartami spoza modelu silnika (np. „Resolution” w BSP Agenda Pack) się
  załaduje, ale takie karty nie zadziałają w fazie agendy.
