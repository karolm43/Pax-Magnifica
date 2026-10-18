// Panel boczny — edycja wybranego kafelka: setup frakcji (sloty domowe) oraz
// zmiana jednostek w przestrzeni i na planetach. Zmiany idą przez store do API.

import { useMemo, useState } from "react";
import { useAppStore } from "./store";
import type { MapTile } from "./types";

// Typy jednostek wg umiejscowienia (zgodne z asyncId grafik i RULES.md 2b).
const SPACE_TYPES = [
  "fighter",
  "destroyer",
  "cruiser",
  "carrier",
  "dreadnought",
  "flagship",
  "warsun",
];
const PLANET_TYPES = ["infantry", "mech", "pds", "spacedock"];

const PLAYER_COLOR_OPTIONS = [
  "red",
  "blu",
  "grn",
  "ylw",
  "ppl",
  "org",
  "pnk",
  "blk",
];

function unitCount(
  stacks: { base_type: string; count: number; player_id: string }[],
  baseType: string,
  playerId: string,
): number {
  const s = stacks.find(
    (x) => x.base_type === baseType && x.player_id === playerId,
  );
  return s?.count ?? 0;
}

export function SidePanel() {
  const {
    map,
    selectedPosition,
    selectTile,
    factions,
    setupPlayerFaction,
    updateSpaceUnits,
    updatePlanetUnits,
  } = useAppStore();

  const tile: MapTile | undefined = useMemo(
    () => map?.tiles.find((t) => t.position === selectedPosition),
    [map, selectedPosition],
  );

  // Aktywny gracz do edycji jednostek (kolor jako player_id — spójne z setupem).
  const [activePlayer, setActivePlayer] = useState("red");
  // Formularz setupu frakcji.
  const [factionId, setFactionId] = useState("");
  const [setupColor, setSetupColor] = useState("red");

  if (!tile) {
    return (
      <aside className="w-80 shrink-0 border-l border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-400">
        Kliknij kafelek, aby edytować jego zawartość.
      </aside>
    );
  }

  const isHome = tile.is_home_slot;

  return (
    <aside className="flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-200">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">
          Pozycja {tile.position}
          {tile.name ? ` · ${tile.name}` : ""}
        </h2>
        <button
          type="button"
          onClick={() => selectTile(null)}
          className="text-xs text-slate-500 hover:text-slate-200"
        >
          ✕
        </button>
      </div>

      {/* Setup frakcji na slocie domowym */}
      {isHome && (
        <section className="rounded border border-slate-700 p-3">
          <h3 className="mb-2 text-xs font-semibold uppercase text-slate-400">
            Setup gracza (slot domowy {tile.home_color})
          </h3>
          <label className="mb-1 block text-xs text-slate-400">Frakcja</label>
          <select
            value={factionId}
            onChange={(e) => setFactionId(e.target.value)}
            className="mb-2 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs"
          >
            <option value="">— wybierz —</option>
            {factions.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
          <label className="mb-1 block text-xs text-slate-400">Kolor</label>
          <select
            value={setupColor}
            onChange={(e) => setSetupColor(e.target.value)}
            className="mb-3 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs"
          >
            {PLAYER_COLOR_OPTIONS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={!factionId}
            onClick={() =>
              void setupPlayerFaction({
                player_id: setupColor,
                faction_id: factionId,
                color: setupColor,
                home_position: tile.position,
              })
            }
            className="w-full rounded bg-sky-700 px-3 py-1.5 text-xs font-medium hover:bg-sky-600 disabled:opacity-40"
          >
            Ustaw frakcję + flotę startową
          </button>
        </section>
      )}

      {/* Aktywny gracz dla edycji jednostek */}
      <section className="rounded border border-slate-700 p-3">
        <label className="mb-1 block text-xs text-slate-400">
          Edytuj jako gracz (kolor)
        </label>
        <select
          value={activePlayer}
          onChange={(e) => setActivePlayer(e.target.value)}
          className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs"
        >
          {PLAYER_COLOR_OPTIONS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </section>

      {/* Jednostki w przestrzeni */}
      {!isHome && (
        <section className="rounded border border-slate-700 p-3">
          <h3 className="mb-2 text-xs font-semibold uppercase text-slate-400">
            Przestrzeń (statki)
          </h3>
          <div className="flex flex-col gap-1">
            {SPACE_TYPES.map((bt) => {
              const count = unitCount(tile.space_units, bt, activePlayer);
              return (
                <UnitRow
                  key={bt}
                  label={bt}
                  count={count}
                  onChange={(next) =>
                    void updateSpaceUnits(tile.position, [
                      { player_id: activePlayer, base_type: bt, count: next },
                    ])
                  }
                />
              );
            })}
          </div>
        </section>
      )}

      {/* Jednostki na planetach */}
      {tile.planets.length > 0 && (
        <section className="rounded border border-slate-700 p-3">
          <h3 className="mb-2 text-xs font-semibold uppercase text-slate-400">
            Planety (naziemne / struktury)
          </h3>
          {tile.planets.map((planet) => {
            const pu = tile.planet_units.find((p) => p.planet_id === planet);
            const stacks = pu?.stacks ?? [];
            return (
              <div key={planet} className="mb-3">
                <div className="mb-1 text-xs font-medium text-slate-300">
                  {planet}
                  {pu?.owner_id ? ` · właściciel: ${pu.owner_id}` : ""}
                </div>
                <div className="flex flex-col gap-1">
                  {PLANET_TYPES.map((bt) => {
                    const count = unitCount(stacks, bt, activePlayer);
                    return (
                      <UnitRow
                        key={bt}
                        label={bt}
                        count={count}
                        onChange={(next) =>
                          void updatePlanetUnits(
                            tile.position,
                            planet,
                            [
                              {
                                player_id: activePlayer,
                                base_type: bt,
                                count: next,
                              },
                            ],
                            activePlayer,
                          )
                        }
                      />
                    );
                  })}
                </div>
              </div>
            );
          })}
        </section>
      )}
    </aside>
  );
}

function UnitRow({
  label,
  count,
  onChange,
}: {
  label: string;
  count: number;
  onChange: (next: number) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs capitalize">{label}</span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onChange(Math.max(0, count - 1))}
          className="h-5 w-5 rounded border border-slate-700 text-xs hover:bg-slate-800"
        >
          −
        </button>
        <span className="w-5 text-center text-xs tabular-nums">{count}</span>
        <button
          type="button"
          onClick={() => onChange(count + 1)}
          className="h-5 w-5 rounded border border-slate-700 text-xs hover:bg-slate-800"
        >
          +
        </button>
      </div>
    </div>
  );
}
