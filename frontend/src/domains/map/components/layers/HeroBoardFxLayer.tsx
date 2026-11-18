import type { CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import type { Tile } from "@/entities/game/types";
import { HEX_PATH, TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { Unit } from "@/shared/ui/Unit";
import {
  fxTargets,
  useHeroFx,
  type FxMark,
} from "@/domains/game-shell/components/KeyMoments/heroBoardFx";
import classes from "./HeroBoardFxLayer.module.css";

/** Elementy jednego znacznika w systemie (liczba odłamków/monet/pnączy). */
const PARTS: Record<FxMark, number> = {
  bloom: 8,
  beam: 1,
  coins: 10,
  ripple: 3,
  slash: 3,
  seal: 3,
  pulse: 2,
  aegis: 3,
  nova: 8,
};

function Mark({ mark, tile, index }: { mark: FxMark; tile: Tile; index: number }) {
  const cx = tile.properties.x + TILE_WIDTH / 2;
  const cy = tile.properties.y + TILE_HEIGHT / 2;
  return (
    <g
      className={classes.mark}
      data-mark={mark}
      // Kolejne systemy odpalają z lekkim przesunięciem — fala zamiast jednego błysku.
      style={{ "--d": `${Math.min(index, 12) * 90}ms` } as CSSProperties}
    >
      <path
        className={classes.hex}
        d={HEX_PATH}
        transform={`translate(${tile.properties.x} ${tile.properties.y})`}
      />
      <g transform={`translate(${cx} ${cy})`}>
        {Array.from({ length: PARTS[mark] }, (_, i) => (
          <g key={i} className={classes.part} style={{ "--i": i, "--n": PARTS[mark] } as CSSProperties}>
            <MarkPart mark={mark} />
          </g>
        ))}
      </g>
    </g>
  );
}

/** Kształt jednego elementu znacznika (w układzie środka systemu). */
function MarkPart({ mark }: { mark: FxMark }) {
  switch (mark) {
    case "bloom":
      // Pnącze: zakrzywiona łodyga z liściem na końcu.
      return (
        <>
          <path className={classes.vine} d="M 0 0 C 18 -30 -12 -60 8 -96" pathLength={100} />
          <ellipse className={classes.leaf} cx={8} cy={-96} rx={9} ry={4} />
        </>
      );
    case "beam":
      return <rect className={classes.beam} x={-26} y={-900} width={52} height={900} />;
    case "coins":
      return <circle className={classes.coin} r={9} />;
    case "ripple":
    case "pulse":
      return <circle className={classes.ring} r={60} />;
    case "slash":
      return <path className={classes.claw} d="M -70 -60 Q -10 -10 60 70" pathLength={100} />;
    case "aegis":
      // Kopuła tarczy: półkula nad środkiem systemu + pierścień u podstawy.
      return (
        <>
          <path className={classes.dome} d="M -92 18 A 92 92 0 0 1 92 18 Z" />
          <ellipse className={classes.domeBase} cx={0} cy={18} rx={92} ry={22} />
        </>
      );
    case "nova":
      // Supernowa: rdzeń i fala uderzeniowa (raz, w pierwszym elemencie) + promień wyrzutu plazmy.
      return (
        <>
          <circle className={classes.novaCore} r={70} />
          <circle className={classes.novaShock} r={80} />
          <path className={classes.novaRay} d="M 0 -40 L 10 -150 L 0 -230 L -10 -150 Z" />
        </>
      );
    case "seal":
      return (
        <>
          <circle className={classes.sealRing} r={120} />
          <circle className={classes.sealInner} r={86} />
        </>
      );
  }
}

/**
 * Efekt bohatera na planszy (RULES.md 64.4): przyciemnienie, fala przez mapę, cienie okrętów
 * i znaczniki w systemach — wg przepisu z `HERO_BOARD_FX`. Uruchamia go `KeyMomentStage` po
 * scenie bohatera (`useHeroFx`); warstwa leży w treści mapy (idzie za zoomem), nie łapie wskaźnika.
 */
export function HeroBoardFxLayer({
  tiles,
  contentSize,
}: {
  tiles: Tile[];
  contentSize: { width: number; height: number };
}) {
  const run = useHeroFx((s) => s.run);
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  if (!run) return null;
  const { recipe } = run;
  const rgb = run.color ? resolvePrimaryRgb(run.color) : undefined;
  const tone = recipe.tone ?? (rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "255 211 74");
  const byPosition = new Map(tiles.map((t) => [t.position, t]));
  const targets = fxTargets(recipe, tiles, run, gameState?.activeSystem ?? null)
    .map((p) => byPosition.get(p))
    .filter((t): t is Tile => !!t);

  return (
    <div
      key={run.id}
      className={classes.layer}
      style={
        {
          width: contentSize.width,
          height: contentSize.height,
          "--tone": tone,
          "--fx-ms": `${recipe.ms}ms`,
          "--dim": recipe.dim ?? 0,
        } as CSSProperties
      }
      aria-hidden="true"
    >
      {recipe.dim ? <div className={classes.dim} /> : null}
      {recipe.sweep && <div className={classes.sweep} data-sweep={recipe.sweep} />}
      {recipe.shadows && run.color && (
        <div className={classes.shadows}>
          {recipe.shadows.map((unit, i) => (
            <span key={i} className={classes.shadow} style={{ "--i": i } as CSSProperties}>
              <Unit unitType={unit} colorAlias={run.color ?? ""} faction={run.faction ?? undefined} scaleSprite />
            </span>
          ))}
        </div>
      )}
      <svg className={classes.svg} width={contentSize.width} height={contentSize.height}>
        {targets.map((tile, index) => (
          <Mark key={tile.position} mark={recipe.mark} tile={tile} index={index} />
        ))}
      </svg>
    </div>
  );
}
