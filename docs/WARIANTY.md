# Warianty gry: fanowskie zestawy, erraty komponentów, własne komponenty

Jak wpiąć fanowski zestaw (Absol, Black Spectrum…), erratę dowolnego komponentu, własny
komponent albo zmianę parametrów setupu. Mechanizm to **moduły wariantów**: dane w
`assets/config/variants.json`, logika w `src/core/variants.py`. Kod nie zna żadnego
konkretnego zestawu fanowskiego.

## Jak to działa

- **Wybór per gra.** Moduły włącza się w Ustawieniach (General → Game variants). Lista
  przełączników powstaje z manifestu. Wybór trafia do `/game/new` (`variants`) i do
  `GameState.decks.variants`.
- **Rejestr danych per gra.** `StaticDataRegistry(variant_ids=...)` nakłada moduły na dane
  aktywnych źródeł. `AppContext.registry` zwraca rejestr bieżącej gry (budowany raz na
  zestaw modułów) i podpina go do hooków. Rejestr bez modułów = czyste dane oficjalne.
- **Errata w miejscu (`replaces`).** Wpis źródła modułu z polem `homebrewReplacesID`
  nadpisuje treść oficjalnego komponentu: tekst, liczby, wymagania, zdolność. Komponent
  **zachowuje oficjalne id**. Dlatego reszta silnika (techy frakcji, wymagania, statystyki
  jednostek, talie, ręce graczy) od razu używa nowej wersji. Odwołania wewnątrz danych
  wariantu (np. `requiredTechId: "bsp_inf2"`) są przemapowane na id oficjalne (`inf2`).
  Obejmuje to każdą kategorię: technologie, jednostki (także mechy i flagowce), frakcje,
  zdolności, liderów, przełomy, planety, karty strategii, karty akcji, agendy, relikty,
  eksploracje, notki, cele i karty ogólne (np. ploty Firmament/Obsidian).
- **Nowe komponenty (`adds`).** Wpisy źródła bez `homebrewReplacesID` wchodzą pod własnymi
  id.
- **Całe talie (`decks`).** Talia danego typu w grze to talia modułu z `assets/data/decks`.
  Dwa moduły tej samej talii się wykluczają.
- **Parametry reguł i setupu (`rules`).** Wartości, które kod czyta przez
  `variants.rule_value(registry, klucz, domyślna)`. Dziś:
  - `fracture.roll_success` (wyniki d10 wprowadzające Fracture, domyślnie `[1, 10]`),
  - `fracture.ingress_per_synergy_color` (3),
  - `fracture.ingress_per_color_no_synergy` (1),
  - `fracture.neutral_setup` (jednostki neutralne na kaflach Fracture).

  Nowy parametr = stała w kodzie zamieniona na `rule_value(...)` z tą stałą jako domyślną.
- **Kolejność.** Gdy dwa moduły poprawiają ten sam komponent, wygrywa moduł wybrany
  wcześniej.

## Mechanika komponentu z erratą

Hooki są przypisane do id komponentu (`covers="technologies:st"` albo źródło hooka).

- Gdy moduł podmienił komponent, **oficjalne hooki tego komponentu się wyłączają**
  (`rules_hooks.variant_active`, `effect_for`, `inputs_for`, `ability_for`). Stara
  mechanika nie działa pod nowym tekstem.
- Działają hooki wersji wariantu: ten sam dekorator z `variant="<source>"`:
  ```python
  @register(POINT_PRODUCTION_COST, HookSource(SOURCE_TECHNOLOGY, "st"), HookKind.MODIFY,
            covers="technologies:st", variant="black_spectrum")
  def bsp_sarween(state, player_id, ctx): ...

  @register_effect("action_cards:sabotage", variant="black_spectrum")
  def bsp_sabotage(state, registry, player_id, params): ...
  ```
  Tak samo `on_event(..., variant=...)`, `register_effect_inputs`, `register_ability`.
- Bez hooka wariantu komponent działa jak ręczna ewidencja, tak jak każda nieoprogramowana
  karta.
- Liczby z danych (koszt, walka, ruch, pojemność jednostek…) zmieniają się same, bo silnik
  czyta je z rejestru gry.

## Tekst w UI

- Backend: `/api/public/game/{id}/variant-data` zwraca wpisy zmienione i dodane przez
  moduły gry (`entries`), plakietki (`badges`) i talie zastąpione w całości (`decks`).
- Front: `entities/lookup/variantData.ts`. Pobiera dane raz na zestaw modułów (razem z
  web-data). Każda funkcja wyszukująca (`getTechData`, `getRelicData`, `getUnitData`,
  `getLeaderById`, `getAgenda`, `getActionCard`, `getExploration`, cele, notki, przełomy,
  zdolności, karty strategii) nakłada errata na dane statyczne. Pule kart dostają nowe karty
  przez `withVariantList`. Dzięki temu front pokazuje także karty, których nie ma w jego
  statycznych danych (Black Spectrum, własne komponenty).

## Przepis: dodanie fanowskiego zestawu

1. Sprawdź dane: wpisy w `assets/data/<kategoria>/<zrodlo>.json` (czy mają
   `homebrewReplacesID`?) i talie w `assets/data/decks/<zrodlo>.json`.
2. Dopisz moduł do `assets/config/variants.json`, np.:
   ```json
   {
     "id": "bsp_factions",
     "name": "Black Spectrum faction errata",
     "description": "Black Spectrum rewrites of technologies, units, leaders…",
     "source": "black_spectrum",
     "badge": "BSP",
     "replaces": ["technologies", "units", "leaders", "breakthroughs", "promissory_notes"]
   }
   ```
3. `uv run python scripts/gen_active_decks.py` (przełącznik w Ustawieniach).
4. Test składu/tekstu w `tests/test_variants.py` (np. `StaticDataRegistry(variant_ids=[...])`).
5. Mechanika: hooki z `variant="<source>"` dla komponentów, których efekt się zmienił.
   Rulingi do wersji fanowskich trafiają do testów jak zwykle.
6. Restart backendu (manifest wczytuje się przy starcie).

## Przepis: własna errata albo nowy komponent

1. Plik `assets/data/<kategoria>/pax_errata.json` z wpisami o własnym `source`
   (np. `pax_errata`):
   - errata: nowe id + `"homebrewReplacesID": "<id oficjalne>"` + zmienione pola,
   - nowy komponent: nowe id bez `homebrewReplacesID` (karta musi też trafić do talii: własna
     talia w `assets/data/decks/` + `decks` w module).
2. Moduł: `{"id": "pax_errata", "name": "…", "source": "pax_errata", "replaces": "all",
   "adds": "all", "default": true}`. `default: true` włącza moduł w nowych grach.
3. Kroki 3–6 z przepisu wyżej.

## Moduły w manifeście (2026-11-18)

| Moduł | Co robi |
|---|---|
| `absol_agendas` | talia agend Absol + Absol's Political Secret (errata `<color>_ps`) |
| `absol_relics` | talia reliktów Absol (20) |
| `absol_tech` | technologie i jednostki Absol (errata + nowe) |
| `bsp_factions` | technologie, jednostki, liderzy, przełomy, notki Black Spectrum |
| `bsp_firmament_plots` | ploty Firmament/Obsidian Black Spectrum |
| `bsp_objectives` | cele publiczne i tajne Black Spectrum |
| `bsp_cards` | talie kart akcji, eksploracji i reliktów Black Spectrum |
| `bsp_agendas` | talia agend Black Spectrum (50) |

Hooków wersji fanowskich jeszcze nie ma. Komponenty z erratą mają nowy tekst i dane, a
ich efekty są ręczną ewidencją, dopóki ktoś nie dopisze hooka z `variant=`.

## Ograniczenia

- Obrazki kart: errata usuwa oficjalny `imageURL` (pokazywałby stary tekst). UI pokazuje
  wtedy tekst.
- Setup Fracture: modułami da się zmienić parametry z listy wyżej. Inne kroki setupu (np.
  inne kafle) wymagają nowego parametru `rule_value` albo hooka.
- Kreator gry (wybór frakcji) pokazuje ploty BSP, gdy w Ustawieniach wybrano moduł
  podmieniający `genericcards` źródłem Black Spectrum. Pozostałe teksty w kreatorze są
  oficjalne, bo przed startem gry nie ma jeszcze rejestru z modułami.
- Fanowska talia z kartami spoza modelu silnika (np. „Resolution” w BSP Agenda Pack) się
  załaduje, ale takie karty nie zadziałają w fazie agendy.
