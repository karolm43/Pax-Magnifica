import type { Tile } from "@/entities/game/types";
import { tileOutline } from "@/entities/geometry/tileOutline";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { kindsToShow, linkTargets, playerLinkTargets, useWormholeHoverStore } from "../../wormholeLinks";
import classes from "./WormholeLinkLayer.module.css";

type Point = { x: number; y: number };

/** Kolor linii wg rodzaju połączenia (CSS ``data-kind``); reszta typów = kolor domyślny. */
const KNOWN_KINDS = new Set(["ALPHA", "BETA", "GAMMA", "DELTA", "INGRESS", "EGRESS"]);

/** Łuk między środkami systemów: lekko wygięty, żeby linie do kilku celów się nie nakładały. */
function arc(a: Point, b: Point, bend: number): string {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
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
  const viewer = useDeskPlayer();
  if (!hovered) return null;

  const byPosition = new Map(tiles.map((t) => [t.position, t]));
  const source = byPosition.get(hovered.position);
  if (!source) return null;
  /* Środek KSZTAŁTU kafla — dla Creuss/Mallice (grafika większa od heksa) to nie jest
     środek heksa 345x299. */
  const center = (t: Tile): Point => {
    const { center: c } = tileOutline(t.systemId);
    return { x: t.properties.x + c.x, y: t.properties.y + c.y };
  };
  const from = center(source);

  const printed = kindsToShow(source, hovered.kinds).flatMap((kind) =>
    linkTargets(kind, hovered.position, tiles).map((position) => ({ kind, position })),
  );
  // Links only one player has (Quantum Entanglement: alpha <-> beta for Creuss) look like any
  // other wormhole connection in the colour of the DESTINATION wormhole (from a beta: green lines
  // to betas, orange to alphas), and are shown ONLY to that player (the desk: my seat online).
  const alphas = new Set(linkTargets("ALPHA", hovered.position, tiles));
  const betas = new Set(linkTargets("BETA", hovered.position, tiles));
  const common = new Set(printed.map((l) => l.position));
  const own = playerLinkTargets(hovered.position, viewer, common).map((position) => ({
    kind: alphas.has(position) ? "ALPHA" : betas.has(position) ? "BETA" : hovered.kinds[0],
    position,
  }));
  const links = [...printed, ...own].flatMap(({ kind, position }) => {
    const target = byPosition.get(position);
    return target ? [{ kind, target }] : [];
  });
  if (links.length === 0) return null;

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
        {links.map(({ kind, target }, index) => {
          const to = center(target);
          // A target reached by two wormhole kinds gets two arcs with different bends.
          const repeat = links.slice(0, index).filter((l) => l.target === target).length;
          const d = arc(from, to, 0.18 + 0.14 * repeat);
          const dataKind = KNOWN_KINDS.has(kind) ? kind : undefined;
          return (
            <g key={`${kind}-${target.position}`} data-kind={dataKind}>
              <path
                className={classes.targetHex}
                d={tileOutline(target.systemId).path}
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
          data-kind={hovered.kinds.find((k) => KNOWN_KINDS.has(k))}
          cx={from.x}
          cy={from.y}
          r={18}
        />
      </svg>
    </div>
  );
}
