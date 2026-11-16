import type { Tile } from "@/entities/game/types";
import {
  HEX_PATH,
  TILE_HEIGHT,
  TILE_WIDTH,
} from "@/entities/geometry/tilePositioning";
import { linkTargets, useWormholeHoverStore } from "../../wormholeLinks";
import classes from "./WormholeLinkLayer.module.css";

type Point = { x: number; y: number };

/** Kolor linii wg rodzaju połączenia (CSS ``data-kind``); reszta typów = kolor domyślny. */
const KNOWN_KINDS = new Set(["ALPHA", "BETA", "GAMMA", "DELTA", "INGRESS", "EGRESS"]);

/** Łuk między środkami systemów: lekko wygięty, żeby linie do kilku celów się nie nakładały. */
function arc(a: Point, b: Point): string {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const bend = 0.18;
  return `M ${a.x} ${a.y} Q ${mx - dy * bend} ${my + dx * bend} ${b.x} ${b.y}`;
}

/**
 * Linie „dokąd prowadzi” rysowane NA MAPIE, gdy kursor stoi na wormhole albo portalu
 * ingress/egress (``useWormholeHoverStore``). Sama warstwa nie łapie wskaźnika.
 */
export function WormholeLinkLayer({
  tiles,
  contentSize,
}: {
  tiles: Tile[];
  contentSize: { width: number; height: number };
}) {
  const hovered = useWormholeHoverStore((s) => s.hovered);
  if (!hovered) return null;

  const byPosition = new Map(tiles.map((t) => [t.position, t]));
  const source = byPosition.get(hovered.position);
  if (!source) return null;
  const center = (t: Tile): Point => ({
    x: t.properties.x + TILE_WIDTH / 2,
    y: t.properties.y + TILE_HEIGHT / 2,
  });
  const from = center(source);

  const links = hovered.kinds.flatMap((kind) =>
    linkTargets(kind, hovered.position, tiles).flatMap((position) => {
      const target = byPosition.get(position);
      return target ? [{ kind, target }] : [];
    }),
  );

  return (
    <div
      className={classes.layer}
      style={{ width: contentSize.width, height: contentSize.height }}
    >
      <svg
        className={classes.svg}
        width={contentSize.width}
        height={contentSize.height}
        aria-hidden="true"
      >
        {links.map(({ kind, target }) => {
          const to = center(target);
          const d = arc(from, to);
          const dataKind = KNOWN_KINDS.has(kind) ? kind : undefined;
          return (
            <g key={`${kind}-${target.position}`} data-kind={dataKind}>
              <path
                className={classes.targetHex}
                d={HEX_PATH}
                transform={`translate(${target.properties.x} ${target.properties.y})`}
              />
              <path className={classes.shadow} d={d} />
              <path className={classes.line} d={d} pathLength={100} />
              <path className={classes.comet} d={d} pathLength={100} />
              <circle className={classes.pulse} cx={to.x} cy={to.y} r={40} />
              <circle className={classes.dot} cx={to.x} cy={to.y} r={14} />
            </g>
          );
        })}
        <circle
          className={classes.origin}
          data-kind={links[0] && KNOWN_KINDS.has(links[0].kind) ? links[0].kind : undefined}
          cx={from.x}
          cy={from.y}
          r={18}
        />
      </svg>
    </div>
  );
}
