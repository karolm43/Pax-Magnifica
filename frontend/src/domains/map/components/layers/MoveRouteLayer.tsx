import type { CSSProperties } from "react";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { lookupUnit } from "@/entities/lookup/units";
import { getColorAlias } from "@/entities/lookup/colors";
import { getPlanetData } from "@/entities/lookup/planets";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import { RouteUnitChip } from "@/domains/movement/RouteUnitChip";
import {
  asyncOfBase,
  pickKey,
  type PickTarget,
} from "@/domains/movement/routeTypes";
import type { Tile } from "@/entities/game/types";
import { legCargoCount, legShipCount } from "@/domains/movement/flightPlan";
import { TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import classes from "./MoveRouteLayer.module.css";

type Point = { x: number; y: number };

/**
 * Trasa ruchu rysowana NA MAPIE (krok MOVEMENT): linia od systemu źródłowego do aktywnego,
 * strzałki kierunku, alternatywne trasy (przerywane) i - na trasie - ładunek do zabrania
 * (klik +1, prawy przycisk −1). Dane z ``moveDraft`` (podgląd trasy z backendu), współrzędne
 * z ``tile.properties`` (kontener mapy jest skalowany, więc nie liczymy zoomu).
 */
export function MoveRouteLayer({
  tiles,
  contentSize,
}: {
  tiles: Tile[];
  contentSize: { width: number; height: number };
}) {
  const draft = useAppStore((s) => s.moveDraft);
  const bumpDraftPick = useAppStore((s) => s.bumpDraftPick);
  const gameData = useGameData();
  const look = usePlayerLook();
  const route = draft?.route ?? null;
  if (!draft || !route) return null;

  const centers = new Map<string, Point>(
    tiles.map((t) => [
      t.position,
      { x: t.properties.x + TILE_WIDTH / 2, y: t.properties.y + TILE_HEIGHT / 2 },
    ]),
  );
  const toPoints = (path: string[]): Point[] =>
    path.flatMap((p) => {
      const c = centers.get(p);
      return c ? [c] : [];
    });
  const line = (pts: Point[]) => pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  const main = route.route ? toPoints(route.route) : [];
  const others = route.alternatives
    .filter((a) => route.route === null || a.join("|") !== route.route.join("|"))
    .map(toPoints)
    .filter((pts) => pts.length > 1);

  const player = gameData?.playerData?.find((p) => p.faction === draft.faction);
  const colorAlias = getColorAlias(player?.color);
  const rgb = look(draft.faction).rgb.split(" ").join(",");
  const style = { "--route-rgb": rgb } as CSSProperties;

  return (
    <div
      className={classes.layer}
      style={{ ...style, width: contentSize.width, height: contentSize.height }}
    >
      <svg
        className={classes.svg}
        width={contentSize.width}
        height={contentSize.height}
        aria-hidden="true"
      >
        {others.map((pts) => (
          <path key={line(pts)} d={line(pts)} className={classes.alt} />
        ))}
        {main.length > 1 && (
          <>
            <path d={line(main)} className={classes.shadow} />
            <path d={line(main)} className={classes.main} />
            {main.slice(0, -1).map((a, i) => {
              const b = main[i + 1];
              const angle = (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI;
              return (
                <polygon
                  key={`arrow-${i}`}
                  className={classes.arrow}
                  points="-26,-22 26,0 -26,22"
                  transform={`translate(${(a.x + b.x) / 2} ${(a.y + b.y) / 2}) rotate(${angle})`}
                />
              );
            })}
            {main.map((p, i) => {
              const position = route.route?.[i] ?? "";
              const isRift = route.riftNodes.includes(position);
              const kind = isRift
                ? "rift"
                : i === 0
                  ? "start"
                  : i === main.length - 1
                    ? "end"
                    : draft.via.includes(position)
                      ? "via"
                      : "pass";
              return (
                <circle
                  key={`node-${position}`}
                  className={classes.node}
                  data-kind={kind}
                  cx={p.x}
                  cy={p.y}
                  r={kind === "pass" ? 18 : kind === "rift" ? 32 : 26}
                />
              );
            })}
          </>
        )}
      </svg>

      {(route.route ?? []).map((position) => {
        const at = centers.get(position);
        const entries = route.cargo.filter((c) => c.position === position);
        if (!at || entries.length === 0) return null;
        return (
          <div
            key={`cargo-${position}`}
            className={classes.cargo}
            style={{ left: at.x, top: at.y + 40 }}
          >
            {entries.map((c) => {
              const target: PickTarget = {
                kind: "cargo",
                position: c.position,
                zone: c.zone,
                baseType: c.baseType,
                max: c.count,
              };
              const asyncId = asyncOfBase(c.baseType);
              const name = lookupUnit(asyncId, draft.faction, player)?.name ?? asyncId.toUpperCase();
              const zone = c.zone === "space" ? "space" : (getPlanetData(c.zone)?.name ?? c.zone);
              return (
                <RouteUnitChip
                  key={pickKey(target)}
                  variant="badge"
                  asyncId={asyncId}
                  colorAlias={colorAlias}
                  faction={draft.faction}
                  name={name}
                  caption={zone}
                  title={`${name} (${zone}): click +1, right-click −1, Shift = all`}
                  picked={draft.picks[pickKey(target)]?.count ?? 0}
                  max={c.count}
                  onChange={(delta) => bumpDraftPick(target, delta)}
                />
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

/**
 * Ruchy zaplanowane w oknie ruchu z EFEKTU (``UnitMovesField``: bohater, przełom, karta) -
 * ta sama linia ze strzałką co trasa kroku MOVEMENT, prosto ze źródła do celu (efekty
 * przenoszą „prosto”, bez trasy), z liczbą jednostek przy celu.
 */
export function EffectMoveLayer({
  tiles,
  contentSize,
}: {
  tiles: Tile[];
  contentSize: { width: number; height: number };
}) {
  const effect = useAppStore((s) => s.effectMove);
  const look = usePlayerLook();
  if (!effect || effect.lines.length === 0) return null;
  const centers = new Map<string, Point>(
    tiles.map((t) => [
      t.position,
      { x: t.properties.x + TILE_WIDTH / 2, y: t.properties.y + TILE_HEIGHT / 2 },
    ]),
  );
  const rgb = look(effect.faction).rgb.split(" ").join(",");
  return (
    <div
      className={classes.layer}
      style={
        { "--route-rgb": rgb, width: contentSize.width, height: contentSize.height } as CSSProperties
      }
    >
      <svg
        className={classes.svg}
        width={contentSize.width}
        height={contentSize.height}
        aria-hidden="true"
      >
        {effect.lines.map(({ from, to, count }) => {
          const a = centers.get(from);
          const b = centers.get(to);
          if (!a || !b) return null;
          const d = `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
          const angle = (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI;
          return (
            <g key={`${from}>${to}`}>
              <path d={d} className={classes.shadow} />
              <path d={d} className={classes.main} />
              <polygon
                className={classes.arrow}
                points="-26,-22 26,0 -26,22"
                transform={`translate(${(a.x + b.x) / 2} ${(a.y + b.y) / 2}) rotate(${angle})`}
              />
              <circle className={classes.node} data-kind="start" cx={a.x} cy={a.y} r={26} />
              <circle className={classes.node} data-kind="end" cx={b.x} cy={b.y} r={34} />
              <text className={classes.count} x={b.x} y={b.y}>
                {count}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/**
 * Staged legs of the flight plan (Move Ships step, RULES.md 32.4): every leg's route stays on
 * the map while the next one is picked - calmer line than the leg being edited, with the
 * number of ships (+ cargo) flying from each source. The leg open in the editor is drawn by
 * ``MoveRouteLayer`` instead.
 */
export function FlightPlanLayer({
  tiles,
  contentSize,
}: {
  tiles: Tile[];
  contentSize: { width: number; height: number };
}) {
  const plan = useAppStore((s) => s.movePlan);
  const editing = useAppStore((s) => s.moveDraft?.legId);
  const look = usePlayerLook();
  const legs = plan.filter((leg) => leg.id !== editing && (leg.route.route?.length ?? 0) > 1);
  if (legs.length === 0) return null;
  const centers = new Map<string, Point>(
    tiles.map((t) => [
      t.position,
      { x: t.properties.x + TILE_WIDTH / 2, y: t.properties.y + TILE_HEIGHT / 2 },
    ]),
  );
  const rgb = look(legs[0].faction).rgb.split(" ").join(",");
  return (
    <div
      className={classes.layer}
      style={
        { "--route-rgb": rgb, width: contentSize.width, height: contentSize.height } as CSSProperties
      }
    >
      <svg
        className={classes.svg}
        width={contentSize.width}
        height={contentSize.height}
        aria-hidden="true"
      >
        {legs.map((leg) => {
          const pts = (leg.route.route ?? []).flatMap((p) => {
            const c = centers.get(p);
            return c ? [c] : [];
          });
          if (pts.length < 2) return null;
          const d = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
          const ships = legShipCount(leg.picks);
          const cargo = legCargoCount(leg.picks);
          const start = pts[0];
          return (
            <g key={leg.id}>
              <path d={d} className={classes.shadow} />
              <path d={d} className={classes.staged} />
              {pts.slice(0, -1).map((a, i) => {
                const b = pts[i + 1];
                const angle = (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI;
                return (
                  <polygon
                    key={`arrow-${i}`}
                    className={classes.arrow}
                    points="-26,-22 26,0 -26,22"
                    transform={`translate(${(a.x + b.x) / 2} ${(a.y + b.y) / 2}) rotate(${angle})`}
                  />
                );
              })}
              <circle className={classes.node} data-kind="start" cx={start.x} cy={start.y} r={34} />
              <text className={classes.count} x={start.x} y={start.y}>
                {cargo > 0 ? `${ships}+${cargo}` : ships}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
