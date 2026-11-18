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

/** Stałe pseudolosowe (bez `Math.random` w renderze — ten sam wygląd u wszystkich). */
const seq = (n: number, f: (i: number) => object) => Array.from({ length: n }, (_, i) => f(i));
/** Wyrzuty plazmy po wybuchu: kąt, zasięg (px), promień, opóźnienie. */
const EJECTA = seq(40, (i) => ({
  angle: i * 9 + ((i * 37) % 13) - 6,
  dist: 260 + ((i * 71) % 340),
  r: 3 + (i % 4) * 1.6,
  lag: (i * 29) % 260,
})) as { angle: number; dist: number; r: number; lag: number }[];
/** Materia wsysana w zapadającą się gwiazdę. */
const INFALL = seq(24, (i) => ({
  angle: i * 15 + ((i * 23) % 9),
  dist: 170 + ((i * 47) % 120),
  lag: (i * 53) % 700,
})) as { angle: number; dist: number; lag: number }[];
/** Protuberancje korony (długość, grubość). */
const FLARES = seq(14, (i) => ({ len: 46 + ((i * 31) % 40), w: 9 + (i % 3) * 4 })) as {
  len: number;
  w: number;
}[];

/**
 * Nova Seed — supernowa w systemie (9 s, chwile zgodne z przepisem `muaathero`):
 * 0–1,6 s gwiazda z koroną puchnie i drga; 1,6–2,85 s korona i gwiazda zapadają się w punkt
 * (pierścienie i materia wsysane do środka); 2,85 s błysk + promienie dyfrakcyjne, pod nim
 * nowy kafel; potem rozszerzająca się, poszarpana powłoka gazu, fale uderzeniowe i ejekta;
 * na koniec pulsująca mgławica z gwiazdą neutronową, która powoli gaśnie.
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
        {/* Mgławica-pozostałość (pod wszystkim, pojawia się po wybuchu). */}
        <g className={classes.novaRemnant} filter="url(#fxNovaWisp)">
          <circle r={210} fill="url(#fxNovaNebulaA)" />
          <circle r={170} cx={40} cy={-25} fill="url(#fxNovaNebulaB)" />
          <circle r={150} cx={-45} cy={30} fill="url(#fxNovaNebulaA)" />
        </g>
        <circle className={classes.novaPulsar} r={10} fill="url(#fxNovaCore)" />
        {/* Gwiazda i korona przed wybuchem. */}
        <g className={classes.novaStar}>
          <circle r={190} fill="url(#fxNovaGlow)" />
          <g className={classes.novaCorona}>
            {FLARES.map((f, i) => (
              // Obrót w <g> (początek = środek gwiazdy); ścieżka migocze wokół własnej podstawy.
              <g key={i} transform={`rotate(${(i * 360) / FLARES.length})`}>
                <path
                  className={classes.novaFlare}
                  d={`M ${-f.w / 2} -78 Q 0 ${-78 - f.len * 1.6} ${f.w / 2} -78 Z`}
                  style={{ "--i": i } as CSSProperties}
                />
              </g>
            ))}
          </g>
          <circle r={84} fill="url(#fxNovaStar)" />
        </g>
        {[0, 1, 2, 3].map((i) => (
          <circle key={i} className={classes.novaImplode} r={230} style={{ "--i": i } as CSSProperties} />
        ))}
        {INFALL.map((e, i) => (
          <g key={i} style={{ rotate: `${e.angle}deg` }}>
            <circle
              className={classes.novaInfall}
              r={3}
              style={{ "--dist": `${-e.dist}px`, "--lag": `${e.lag}ms` } as CSSProperties}
            />
          </g>
        ))}
        {/* Wybuch: błysk, promienie, powłoka, fale, ejekta. */}
        <circle className={classes.novaFlash} r={520} fill="url(#fxNovaFlash)" />
        <g className={classes.novaSpikes}>
          <rect x={-900} y={-3} width={1800} height={6} fill="url(#fxNovaSpikeH)" />
          <rect x={-3} y={-900} width={6} height={1800} fill="url(#fxNovaSpikeV)" />
          <rect x={-520} y={-2} width={1040} height={4} fill="url(#fxNovaSpikeH)" transform="rotate(45)" />
          <rect x={-520} y={-2} width={1040} height={4} fill="url(#fxNovaSpikeH)" transform="rotate(-45)" />
        </g>
        <circle className={classes.novaShell} r={150} fill="url(#fxNovaShell)" filter="url(#fxNovaWisp)" />
        <circle className={classes.novaShell} data-late r={150} fill="url(#fxNovaShellB)" filter="url(#fxNovaWisp)" />
        <circle className={classes.novaShock} r={110} />
        <circle className={classes.novaShock} data-late r={110} />
        {EJECTA.map((e, i) => (
          <g key={i} style={{ rotate: `${e.angle}deg` }}>
            <circle
              className={classes.novaEmber}
              r={e.r}
              style={{ "--dist": `${-e.dist}px`, "--lag": `${e.lag}ms` } as CSSProperties}
            />
          </g>
        ))}
      </g>
    </g>
  );
}

/** Gradienty i filtr Nova Seed (kolor z `--tone` warstwy). */
function NovaDefs() {
  const c = (color: string, opacity = 1) => ({ stopColor: color, stopOpacity: opacity });
  const tone = (a: number) => c("rgb(var(--tone))", a);
  return (
    <defs>
      <radialGradient id="fxNovaStar">
        <stop offset="0%" style={c("#fff")} />
        <stop offset="35%" style={c("rgb(255 244 200)")} />
        <stop offset="70%" style={c("rgb(255 170 60)")} />
        <stop offset="92%" style={c("rgb(220 60 20)")} />
        <stop offset="100%" style={c("rgb(160 20 10)", 0)} />
      </radialGradient>
      <radialGradient id="fxNovaCore">
        <stop offset="0%" style={c("#fff")} />
        <stop offset="50%" style={c("rgb(200 230 255)")} />
        <stop offset="100%" style={c("rgb(120 180 255)", 0)} />
      </radialGradient>
      <radialGradient id="fxNovaGlow">
        <stop offset="0%" style={tone(0.7)} />
        <stop offset="45%" style={tone(0.3)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxNovaFlash">
        <stop offset="0%" style={c("#fff")} />
        <stop offset="25%" style={c("rgb(255 248 230)", 0.95)} />
        <stop offset="55%" style={tone(0.6)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxNovaShell">
        <stop offset="0%" style={tone(0)} />
        <stop offset="55%" style={tone(0)} />
        <stop offset="72%" style={c("rgb(255 200 120)", 0.85)} />
        <stop offset="80%" style={c("rgb(255 250 235)", 0.9)} />
        <stop offset="88%" style={c("rgb(230 70 40)", 0.6)} />
        <stop offset="100%" style={c("rgb(120 20 60)", 0)} />
      </radialGradient>
      <radialGradient id="fxNovaShellB">
        <stop offset="0%" style={tone(0)} />
        <stop offset="62%" style={tone(0)} />
        <stop offset="78%" style={c("rgb(255 120 170)", 0.55)} />
        <stop offset="90%" style={c("rgb(140 90 255)", 0.4)} />
        <stop offset="100%" style={c("rgb(60 40 160)", 0)} />
      </radialGradient>
      <radialGradient id="fxNovaNebulaA">
        <stop offset="0%" style={c("rgb(255 210 140)", 0.7)} />
        <stop offset="40%" style={c("rgb(240 90 50)", 0.45)} />
        <stop offset="75%" style={c("rgb(150 40 110)", 0.25)} />
        <stop offset="100%" style={c("rgb(60 20 90)", 0)} />
      </radialGradient>
      <radialGradient id="fxNovaNebulaB">
        <stop offset="0%" style={c("rgb(140 200 255)", 0.45)} />
        <stop offset="50%" style={c("rgb(120 80 220)", 0.3)} />
        <stop offset="100%" style={c("rgb(40 20 120)", 0)} />
      </radialGradient>
      <linearGradient id="fxNovaSpikeH">
        <stop offset="0%" style={c("#fff", 0)} />
        <stop offset="50%" style={c("#fff")} />
        <stop offset="100%" style={c("#fff", 0)} />
      </linearGradient>
      <linearGradient id="fxNovaSpikeV" x2="0" y2="1">
        <stop offset="0%" style={c("#fff", 0)} />
        <stop offset="50%" style={c("#fff")} />
        <stop offset="100%" style={c("#fff", 0)} />
      </linearGradient>
      {/* Poszarpane brzegi gazu (powłoka, mgławica). */}
      <filter id="fxNovaWisp" x="-60%" y="-60%" width="220%" height="220%">
        <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="3" seed="7" />
        <feDisplacementMap in="SourceGraphic" scale="70" xChannelSelector="R" yChannelSelector="G" />
      </filter>
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
      const { at, name, ...opts } = s;
      timers.push(window.setTimeout(() => playBattleSound(name, opts), at));
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
      {recipe.flashAt !== undefined && (
        <div
          className={classes.flash}
          style={{ "--flash-at": `${recipe.flashAt}ms` } as CSSProperties}
        />
      )}
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
