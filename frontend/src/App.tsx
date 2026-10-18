// Główny komponent: łączy się z backendem na starcie, renderuje mapę SVG oraz
// pasek stanu z informacją o rundzie/fazie i przyciskami Undo/Redo (God-Mode).

import { useEffect, useState } from "react";
import { HexMap } from "./HexMap";
import { SidePanel } from "./SidePanel";
import { useAppStore } from "./store";

const STATUS_LABEL: Record<string, string> = {
  idle: "bezczynny",
  connecting: "łączenie…",
  open: "połączono",
  closed: "rozłączono",
};

const EXAMPLE_MAP_STRING =
  "72 66 77 26 27 34 50 69 76 31 35 37 78 62 75 67 38 65 " +
  "0 28 79 0 48 64 0 44 29 0 25 47 0 39 49 0 41 40";

export function App() {
  const {
    map,
    gameState,
    history,
    status,
    error,
    connect,
    disconnect,
    undo,
    redo,
    loadMap,
    selectedPosition,
    selectTile,
  } = useAppStore();

  const [mapString, setMapString] = useState("");

  useEffect(() => {
    void connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return (
    <div className="flex h-full flex-col bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-4 py-2">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-semibold tracking-wide">Custodian Engine</h1>
          <span className="text-xs text-slate-400">
            Runda {gameState?.round_number ?? "—"} · Faza {gameState?.phase ?? "—"}
          </span>
          <span className="text-xs text-slate-500">WebSocket: {STATUS_LABEL[status]}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void undo()}
            disabled={!history?.can_undo}
            className="rounded border border-slate-700 px-2 py-1 text-xs disabled:opacity-40"
          >
            Undo
          </button>
          <button
            type="button"
            onClick={() => void redo()}
            disabled={!history?.can_redo}
            className="rounded border border-slate-700 px-2 py-1 text-xs disabled:opacity-40"
          >
            Redo
          </button>
          <span className="text-xs text-slate-500">
            historia: {history?.history_size ?? 0}
          </span>
        </div>
      </header>

      {/* Pasek wklejania map stringa */}
      <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900/60 px-4 py-2">
        <input
          type="text"
          value={mapString}
          onChange={(e) => setMapString(e.target.value)}
          placeholder="Wklej map string AsyncTI4, np. 72 66 77 26 ..."
          className="flex-1 rounded border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-xs text-slate-100 outline-none focus:border-sky-600"
          onKeyDown={(e) => {
            if (e.key === "Enter" && mapString.trim()) void loadMap(mapString.trim());
          }}
        />
        <button
          type="button"
          onClick={() => mapString.trim() && void loadMap(mapString.trim())}
          disabled={!mapString.trim()}
          className="rounded bg-sky-700 px-3 py-1.5 text-xs font-medium hover:bg-sky-600 disabled:opacity-40"
        >
          Załaduj mapę
        </button>
        <button
          type="button"
          onClick={() => setMapString(EXAMPLE_MAP_STRING)}
          className="rounded border border-slate-700 px-2 py-1.5 text-xs text-slate-400 hover:text-slate-200"
          title="Wstaw przykładowy map string"
        >
          Przykład
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <main className="relative flex-1 overflow-hidden bg-[radial-gradient(ellipse_at_center,#131c33_0%,#070b16_70%,#03050b_100%)]">
          {error && (
            <div className="absolute left-1/2 top-4 z-10 -translate-x-1/2 rounded bg-red-900/80 px-3 py-1 text-xs">
              {error}
            </div>
          )}
          <div className="pointer-events-none absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded bg-slate-900/70 px-3 py-1 text-[10px] text-slate-400">
            kółko = zoom · przeciągnij = przesuń · dwuklik = reset · klik kafelek = edycja
          </div>
          {map ? (
            <HexMap
              map={map}
              onSelectTile={selectTile}
              selectedPosition={selectedPosition}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              Ładowanie mapy…
            </div>
          )}
        </main>
        <SidePanel />
      </div>
    </div>
  );
}
