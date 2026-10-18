// Renderer mapy SVG. Rysuje krawędzie sąsiedztwa (linie między środkami heksów)
// oraz kafelki na podstawie współrzędnych kubicznych z backendu. Każdy kafelek to
// grafika (assets/tiles via /static), przycięta do heksa clipPath-em; przy braku
// grafiki używamy koloru zależnego od anomalii jako fallbacku. Wormhole i anomalie
// są oznaczane nakładką na wierzchu.

import { useCallback, useMemo, useRef, useState } from "react";
import { hexBounds, hexCorners, hexToPixel, type Point } from "./hex";
import type { MapView } from "./types";

const HEX_SIZE = 56;
const PADDING = 24;
const MIN_ZOOM = 0.3;
const MAX_ZOOM = 4;

// Kolory anomalii — fallback, gdy brak grafiki kafelka.
const ANOMALY_FILL: Record<string, string> = {
  SUPERNOVA: "#7f1d1d",
  NEBULA: "#4c1d95",
  GRAVITY_RIFT: "#1e293b",
  ASTEROID_FIELD: "#78350f",
};

function fallbackFill(anomalies: string[]): string {
  for (const anomaly of anomalies) {
    if (anomaly in ANOMALY_FILL) return ANOMALY_FILL[anomaly];
  }
  return "#0f172a";
}

// Barwy slotów domowych graczy (nazwa koloru z backendu → kolor render).
const PLAYER_COLORS: Record<string, string> = {
  red: "#dc2626",
  green: "#22c55e",
  blue: "#3b82f6",
  yellow: "#eab308",
  purple: "#a855f7",
  white: "#e5e7eb",
  orange: "#f97316",
  black: "#1f2937",
  pink: "#ec4899",
};

function playerColor(name: string | null): string {
  if (name && name in PLAYER_COLORS) return PLAYER_COLORS[name];
  return "#64748b";
}

interface UnitIcon {
  key: string;
  imageUrl: string | null;
  color: string | null;
  count: number;
}

interface Placed {
  position: string;
  center: Point;
  corners: string;
  fill: string;
  stroke: string;
  label: string;
  imageUrl: string | null;
  anomalies: string[];
  wormholes: string[];
  isHome: boolean;
  homeColor: string | null;
  units: UnitIcon[];
}

function collectUnitIcons(tile: MapView["tiles"][number]): UnitIcon[] {
  const icons: UnitIcon[] = [];
  for (const s of tile.space_units) {
    icons.push({
      key: `sp-${s.player_id}-${s.base_type}`,
      imageUrl: s.image_url,
      color: s.color,
      count: s.count,
    });
  }
  for (const p of tile.planet_units) {
    for (const s of p.stacks) {
      icons.push({
        key: `pl-${p.planet_id}-${s.player_id}-${s.base_type}`,
        imageUrl: s.image_url,
        color: s.color,
        count: s.count,
      });
    }
  }
  return icons;
}

export function HexMap({
  map,
  onSelectTile,
  selectedPosition,
}: {
  map: MapView;
  onSelectTile?: (position: string) => void;
  selectedPosition?: string | null;
}) {
  const { placed, viewBox, edgeLines } = useMemo(() => {
    const centers = new Map<string, Point>();
    const placedTiles: Placed[] = map.tiles.map((tile) => {
      const center = hexToPixel(tile.q, tile.r, HEX_SIZE);
      centers.set(tile.position, center);
      return {
        position: tile.position,
        center,
        corners: hexCorners(center, HEX_SIZE),
        fill: tile.is_home_slot
          ? playerColor(tile.home_color)
          : fallbackFill(tile.anomalies),
        stroke: tile.is_home_slot ? "#f8fafc" : "#334155",
        label: tile.name ?? tile.system_id,
        imageUrl: tile.is_home_slot ? null : tile.image_url,
        anomalies: tile.anomalies,
        wormholes: tile.wormholes,
        isHome: tile.is_home_slot,
        homeColor: tile.home_color,
        units: collectUnitIcons(tile),
      };
    });

    const lines = map.edges.flatMap((edge) => {
      const a = centers.get(edge.a);
      const b = centers.get(edge.b);
      if (!a || !b) return [];
      return [{ a, b, kind: edge.kind, key: `${edge.a}-${edge.b}-${edge.kind}` }];
    });

    const xs = placedTiles.map((p) => p.center.x);
    const ys = placedTiles.map((p) => p.center.y);
    const minX = Math.min(...xs) - HEX_SIZE - PADDING;
    const maxX = Math.max(...xs) + HEX_SIZE + PADDING;
    const minY = Math.min(...ys) - HEX_SIZE - PADDING;
    const maxY = Math.max(...ys) + HEX_SIZE + PADDING;

    return {
      placed: placedTiles,
      edgeLines: lines,
      viewBox: `${minX} ${minY} ${maxX - minX} ${maxY - minY}`,
    };
  }, [map]);

  const { width: tileW, height: tileH } = hexBounds(HEX_SIZE);

  // Zoom + pan: transformacja grupy SVG. Zoom kółkiem, pan przeciąganiem.
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number } | null>(null);

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => {
      const next = z * (e.deltaY < 0 ? 1.1 : 1 / 1.1);
      return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, next));
    });
  }, []);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    dragRef.current = { x: e.clientX, y: e.clientY };
    (e.target as Element).setPointerCapture?.(e.pointerId);
  }, []);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.x;
    const dy = e.clientY - dragRef.current.y;
    dragRef.current = { x: e.clientX, y: e.clientY };
    setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
  }, []);

  const onPointerUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  const resetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  // Render ikon jednostek na kafelku: siatka ikon z grafiką + licznik.
  const renderUnits = (tile: Placed) => {
    const icons = tile.units;
    if (icons.length === 0) return null;
    const ICON = HEX_SIZE * 0.38;
    const perRow = 3;
    const gap = ICON * 0.15;
    const rows = Math.ceil(icons.length / perRow);
    const startY = tile.center.y - ((rows - 1) * (ICON + gap)) / 2 + ICON * 0.1;
    return icons.map((u, i) => {
      const col = i % perRow;
      const row = Math.floor(i / perRow);
      const inRow = Math.min(perRow, icons.length - row * perRow);
      const startX = tile.center.x - ((inRow - 1) * (ICON + gap)) / 2;
      const x = startX + col * (ICON + gap);
      const y = startY + row * (ICON + gap);
      return (
        <g key={u.key}>
          {u.imageUrl ? (
            <image
              href={u.imageUrl}
              x={x - ICON / 2}
              y={y - ICON / 2}
              width={ICON}
              height={ICON}
              preserveAspectRatio="xMidYMid meet"
            />
          ) : (
            <circle cx={x} cy={y} r={ICON / 2} fill={u.color ?? "#94a3b8"} />
          )}
          {u.count > 1 && (
            <text
              x={x + ICON * 0.4}
              y={y + ICON * 0.5}
              textAnchor="middle"
              className="fill-white"
              fontSize={ICON * 0.5}
              style={{ paintOrder: "stroke", stroke: "#000", strokeWidth: 2 }}
            >
              {u.count}
            </text>
          )}
        </g>
      );
    });
  };

  return (
    <svg
      viewBox={viewBox}
      className="h-full w-full cursor-grab touch-none active:cursor-grabbing"
      role="img"
      aria-label="Mapa heksagonalna Twilight Imperium"
      onWheel={onWheel}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onDoubleClick={resetView}
    >
      <defs>
        {placed.map((tile) => (
          <clipPath key={`clip-${tile.position}`} id={`hex-${tile.position}`}>
            <polygon points={tile.corners} />
          </clipPath>
        ))}
      </defs>

      <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
      {/* Krawędzie sąsiedztwa pod kafelkami */}
      <g>
        {edgeLines.map((line) => (
          <line
            key={line.key}
            x1={line.a.x}
            y1={line.a.y}
            x2={line.b.x}
            y2={line.b.y}
            stroke={line.kind === "wormhole" ? "#38bdf8" : "#1e293b"}
            strokeWidth={line.kind === "wormhole" ? 2 : 1}
            strokeDasharray={line.kind === "wormhole" ? "4 3" : undefined}
          />
        ))}
      </g>

      {/* Kafelki */}
      <g>
        {placed.map((tile) => (
          <g
            key={tile.position}
            onClick={() => onSelectTile?.(tile.position)}
            style={{ cursor: onSelectTile ? "pointer" : undefined }}
          >
            {/* Tło/fallback pod grafiką (widoczne, jeśli obraz się nie załaduje) */}
            <polygon points={tile.corners} fill={tile.fill} />
            {tile.imageUrl && (
              <image
                href={tile.imageUrl}
                x={tile.center.x - tileW / 2}
                y={tile.center.y - tileH / 2}
                width={tileW}
                height={tileH}
                preserveAspectRatio="xMidYMid slice"
                clipPath={`url(#hex-${tile.position})`}
              />
            )}
            {/* Obrys heksa (grubszy dla slotu domowego/wybranego) */}
            <polygon
              points={tile.corners}
              fill="none"
              stroke={
                selectedPosition === tile.position
                  ? "#f59e0b"
                  : tile.stroke
              }
              strokeWidth={
                selectedPosition === tile.position ? 5 : tile.isHome ? 4 : 2
              }
            />
            {/* Etykieta pozycji (góra heksa) */}
            <text
              x={tile.center.x}
              y={tile.center.y - HEX_SIZE * 0.62}
              textAnchor="middle"
              className="fill-slate-100"
              fontSize={10}
              style={{ paintOrder: "stroke", stroke: "#000", strokeWidth: 3 }}
            >
              {tile.position}
            </text>

            {/* Jednostki — ikony z grafiką + licznik, w rzędzie na dole heksa */}
            {renderUnits(tile)}
          </g>
        ))}
      </g>
      </g>
    </svg>
  );
}
