import { useEffect, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import type { Tile } from "@/entities/game/types";
import { HEX_PATH, TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { Unit } from "@/shared/ui/Unit";
import { playBattleSound, preloadBattleSounds } from "@/domains/battle/battleSound";
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
  nova: 0, // własny rysunek: `NovaMark`
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
    case "seal":
      return (
        <>
          <circle className={classes.sealRing} r={120} />
          <circle className={classes.sealInner} r={86} />
        </>
      );
  }
}

/** Odłamki plazmy Nova Seed: kąt, zasięg (px), promień — stałe, bez losowania w renderze. */
const EMBERS = Array.from({ length: 28 }, (_, i) => ({
  angle: i * (360 / 28) + ((i * 37) % 11) - 5,
  dist: 170 + ((i * 53) % 150),
  r: 4 + (i % 3) * 2,
}));

/**
 * Nova Seed: gwiazda zapada się w sobie (pierścienie ściągają do środka, brzeg heksa żarzy się),
 * błysk zasłania wymianę kafla, potem cienka fala uderzeniowa, odłamki plazmy i poświata nowej
 * supernowej. Chwile zgodne z `revealAt` i dźwiękami przepisu `muaathero`.
 */
function NovaMark({ tile }: { tile: Tile }) {
  const cx = tile.properties.x + TILE_WIDTH / 2;
  const cy = tile.properties.y + TILE_HEIGHT / 2;
  return (
    <g className={classes.nova}>
      <path
        className={classes.novaRim}
        d={HEX_PATH}
        transform={`translate(${tile.properties.x} ${tile.properties.y})`}
      />
      <g transform={`translate(${cx} ${cy})`}>
        {[0, 1, 2].map((i) => (
          <circle key={i} className={classes.novaImplode} r={160} style={{ "--i": i } as CSSProperties} />
        ))}
        <circle className={classes.novaCore} r={26} fill="url(#fxNovaCore)" />
        <circle className={classes.novaAfterglow} r={200} fill="url(#fxNovaGlow)" />
        <circle className={classes.novaFlash} r={320} fill="url(#fxNovaFlash)" />
        <circle className={classes.novaShock} r={110} />
        <circle className={classes.novaShock} data-late r={110} />
        {EMBERS.map((e, i) => (
          <g key={i} style={{ rotate: `${e.angle}deg` }}>
            <circle
              className={classes.novaEmber}
              r={e.r}
              style={{ "--dist": `${-e.dist}px`, "--i": i } as CSSProperties}
            />
          </g>
        ))}
      </g>
    </g>
  );
}

/** Gradienty Nova Seed (kolor z `--tone` warstwy). */
function NovaDefs() {
  const tone = (a: number) => ({ stopColor: "rgb(var(--tone))", stopOpacity: a });
  return (
    <defs>
      <radialGradient id="fxNovaCore">
        <stop offset="0%" style={{ stopColor: "#fff" }} />
        <stop offset="55%" style={{ stopColor: "rgb(255 236 200)" }} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxNovaFlash">
        <stop offset="0%" style={{ stopColor: "#fff", stopOpacity: 1 }} />
        <stop offset="30%" style={{ stopColor: "rgb(255 240 210)", stopOpacity: 0.95 }} />
        <stop offset="60%" style={tone(0.55)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxNovaGlow">
        <stop offset="0%" style={tone(0.55)} />
        <stop offset="45%" style={tone(0.25)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
    </defs>
  );
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
  const uncover = useHeroFx((s) => s.uncover);
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);

  // Dźwięki przepisu i odsłonięcie wymienionego kafla (pod błyskiem) — raz na uruchomienie.
  useEffect(() => {
    if (!run) return;
    const timers: number[] = [];
    if (run.recipe.sounds?.length) preloadBattleSounds();
    for (const s of run.recipe.sounds ?? []) {
      timers.push(window.setTimeout(() => playBattleSound(s.name, { gain: s.gain }), s.at));
    }
    for (const r of run.replaced ?? []) {
      timers.push(window.setTimeout(() => uncover(r.position), run.recipe.revealAt ?? 0));
    }
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [run, uncover]);

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
        {recipe.mark === "nova" && <NovaDefs />}
        {targets.map((tile, index) =>
          recipe.mark === "nova" ? (
            <NovaMark key={tile.position} tile={tile} />
          ) : (
            <Mark key={tile.position} mark={recipe.mark} tile={tile} index={index} />
          ),
        )}
      </svg>
    </div>
  );
}
