# Game Variants: Fan Sets, Component Errata, Custom Components

How to plug in a fan set (Absol, Black Spectrum…), errata for any component, a custom
component, or setup parameter changes. The mechanism is **variant modules**: data in
`assets/config/variants.json`, logic in `src/core/variants.py`. The code knows nothing about any
specific fan set.

## How It Works

- **Per-game selection.** Modules are enabled in Settings (General → Game variants). The toggle
  list is generated from the manifest. Selection goes to `/game/new` (`variants`) and into
  `GameState.decks.variants`.
- **Per-game data registry.** `StaticDataRegistry(variant_ids=...)` overlays modules onto
  active sources' data. `AppContext.registry` returns the current game's registry (built once per
  module set) and attaches it to hooks. Registry without modules = pure official data.
- **In-place errata (`replaces`).** A module source entry with a `homebrewReplacesID` field
  overrides the official component's content: text, numbers, prerequisites, ability. The component
  **keeps its official id**. Therefore the rest of the engine (faction techs, prerequisites, unit
  stats, decks, player hands) immediately uses the new version. References inside variant data
  (e.g. `requiredTechId: "bsp_inf2"`) are remapped to official ids (`inf2`).
  This covers every category: technologies, units (including mechs and flagships), factions,
  abilities, leaders, breakthroughs, planets, strategy cards, action cards, agendas, relics,
  explorations, promissory notes, objectives, and generic cards (e.g. Firmament/Obsidian plots).
- **New components (`adds`).** Source entries without `homebrewReplacesID` enter under their own
  ids.
- **Full decks (`decks`).** A deck of a given type in the game becomes the module's deck from `assets/data/decks`.
  Two modules touching the same deck are mutually exclusive.
- **Rule and setup parameters (`rules`).** Values read by code via
  `variants.rule_value(registry, key, default)`. Today:
  - `fracture.roll_success` (d10 results introducing the Fracture, default `[1, 10]`),
  - `fracture.ingress_per_synergy_color` (3),
  - `fracture.ingress_per_color_no_synergy` (1),
  - `fracture.neutral_setup` (neutral units on Fracture tiles).

  New parameter = constant in code replaced with `rule_value(...)` using that constant as default.
- **Ordering.** When two modules patch the same component, the earlier-selected module wins.

## Mechanics of an Errata'd Component

Hooks are bound to component id (`covers="technologies:st"` or hook source).

- When a module replaces a component, **official hooks for that component are disabled**
  (`rules_hooks.variant_active`, `effect_for`, `inputs_for`, `ability_for`). The old
  mechanic does not run under the new text.
- Variant hooks run instead: the same decorator with `variant="<source>"`:
  ```python
  @register(POINT_PRODUCTION_COST, HookSource(SOURCE_TECHNOLOGY, "st"), HookKind.MODIFY,
            covers="technologies:st", variant="black_spectrum")
  def bsp_sarween(state, player_id, ctx): ...

  @register_effect("action_cards:sabotage", variant="black_spectrum")
  def bsp_sabotage(state, registry, player_id, params): ...
  ```
  Same for `on_event(..., variant=...)`, `register_effect_inputs`, `register_ability`.
- Without a variant hook, the component acts as manual tracking, just like any unscripted
  card.
- Data numbers (cost, combat, move, unit capacity…) update automatically because the engine
  reads them from the game registry.

## Text in UI

- Backend: `/api/public/game/{id}/variant-data` returns entries modified and added by the
  game's modules (`entries`), badges (`badges`), and fully replaced decks (`decks`).
- Frontend: `entities/lookup/variantData.ts`. Fetches data once per module set (alongside
  web-data). Every lookup function (`getTechData`, `getRelicData`, `getUnitData`,
  `getLeaderById`, `getAgenda`, `getActionCard`, `getExploration`, objectives, PNs, breakthroughs,
  abilities, strategy cards) overlays errata onto static data. Card pools get new cards
  via `withVariantList`. Thus the frontend also displays cards missing from its
  static data (Black Spectrum, custom components).

## Recipe: Adding a Fan Set

1. Check the data: entries in `assets/data/<category>/<source>.json` (do they have
   `homebrewReplacesID`?) and decks in `assets/data/decks/<source>.json`.
2. Add the module to `assets/config/variants.json`, e.g.:
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
3. `uv run python scripts/gen_active_decks.py` (toggle in Settings).
4. Composition/text test in `tests/test_variants.py` (e.g. `StaticDataRegistry(variant_ids=[...])`).
5. Mechanics: hooks with `variant="<source>"` for components whose effect changed.
   Rulings for fan versions go into tests as usual.
6. Restart backend (manifest is loaded on startup).

## Recipe: Custom Errata or New Component

1. File `assets/data/<category>/pax_errata.json` with entries using your own `source`
   (e.g. `pax_errata`):
   - errata: new id + `"homebrewReplacesID": "<official id>"` + changed fields,
   - new component: new id without `homebrewReplacesID` (a card must also be in a deck: custom
     deck in `assets/data/decks/` + `decks` in module).
2. Module: `{"id": "pax_errata", "name": "…", "source": "pax_errata", "replaces": "all",
   "adds": "all", "default": true}`. `default: true` enables the module in new games.
3. Steps 3–6 from the recipe above.

## Modules in Manifest (2026-11-18)

| Module | What it does |
|---|---|
| `absol_agendas` | Absol agenda deck + Absol's Political Secret (errata `<color>_ps`) |
| `absol_relics` | Absol relic deck (20) |
| `absol_tech` | Absol technologies and units (errata + new) |
| `bsp_factions` | Black Spectrum technologies, units, leaders, breakthroughs, promissory notes |
| `bsp_firmament_plots` | Black Spectrum Firmament/Obsidian plots |
| `bsp_objectives` | Black Spectrum public and secret objectives |
| `bsp_cards` | Black Spectrum action, exploration, and relic decks |
| `bsp_agendas` | Black Spectrum agenda deck (50) |

Fan-version hooks do not exist yet. Errata'd components have the new text and data, and
their effects are tracked manually until someone writes a hook with `variant=`.

## Limitations

- Card images: errata removes the official `imageURL` (it would show old text). The UI shows
  text instead.
- Fracture setup: modules can change parameters from the list above. Other setup steps (e.g.
  different tiles) require a new `rule_value` parameter or hook.
- Game wizard (faction picker) shows BSP plots when a module replacing `genericcards` with the
  Black Spectrum source is selected in Settings. Other texts in the wizard are
  official, because before game start there is no module-aware registry yet.
- A fan deck with cards outside the engine's model (e.g. "Resolution" in BSP Agenda Pack) will
  load, but such cards will not work in the agenda phase.
