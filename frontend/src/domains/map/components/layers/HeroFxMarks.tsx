/**
 * Znaczniki bohaterów w systemach (RULES.md 64.4) — każdy bohater ma własny rysunek pasujący
 * do frakcji (przepisy: `HERO_BOARD_FX`). Rysunki w układzie środka systemu; czas i kolor
 * z CSS (`--tone`, `--fx-ms`, `--d` = opóźnienie kolejnego systemu). Supernowa Muaat ma własny
 * komponent (`NovaMark` w `HeroBoardFxLayer`).
 */
import type { CSSProperties, ReactNode } from "react";
import type { Tile } from "@/entities/game/types";
import { HEX_PATH, TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import type { FxMark } from "@/domains/game-shell/components/KeyMoments/heroBoardFx";
import base from "./HeroBoardFxLayer.module.css";
import fx from "./HeroFxMarks.module.css";

/** Stałe pseudolosowe (bez `Math.random` w renderze — ten sam wygląd u wszystkich graczy). */
const seq = <T,>(n: number, f: (i: number) => T): T[] => Array.from({ length: n }, (_, i) => f(i));
const vars = (v: Record<string, string | number>) => v as CSSProperties;

export const center = (t: Tile) => ({
  x: t.properties.x + TILE_WIDTH / 2,
  y: t.properties.y + TILE_HEIGHT / 2,
});

/** Heks o promieniu `r` (płaski u góry jak kafle), wokół (0, 0). */
const hex = (r: number) =>
  `${seq(6, (i) => {
    const a = (Math.PI / 3) * i;
    return `${i ? "L" : "M"} ${(r * Math.cos(a)).toFixed(1)} ${(r * Math.sin(a)).toFixed(1)}`;
  }).join(" ")} Z`;

/** Kilka kopii elementu obróconych równo wokół środka (`--i`, `--n` dla CSS). */
function Ring({ n, offset = 0, children }: { n: number; offset?: number; children: (i: number) => ReactNode }) {
  return (
    <>
      {seq(n, (i) => (
        <g key={i} transform={`rotate(${offset + (i * 360) / n})`} style={vars({ "--i": i, "--n": n })}>
          {children(i)}
        </g>
      ))}
    </>
  );
}

// --- Rysunki -------------------------------------------------------------------------------

/** Arborec — Overgrowth: pnącza z liśćmi i unoszące się zarodniki. */
function Bloom() {
  return (
    <>
      <Ring n={8} offset={12}>
        {() => (
          <g className={fx.vineArm}>
            <path className={fx.vine} d="M 0 0 C 18 -30 -12 -60 8 -96" pathLength={100} />
            <ellipse className={fx.leaf} cx={8} cy={-96} rx={9} ry={4} />
          </g>
        )}
      </Ring>
      {SPORES.map((s, i) => (
        <circle key={i} className={fx.spore} cx={s.x} cy={s.y} r={s.r} style={vars({ "--i": i })} />
      ))}
    </>
  );
}
const SPORES = seq(14, (i) => ({ x: ((i * 61) % 180) - 90, y: ((i * 37) % 120) - 40, r: 2 + (i % 3) }));

/** Sol — Twilight Directive: słup światła, którym żeton dowodzenia wraca w niebo. */
function Beam() {
  return (
    <>
      <rect className={base.beam} x={-26} y={-900} width={52} height={900} />
      <rect className={fx.beamCore} x={-6} y={-900} width={12} height={900} />
      <ellipse className={fx.beamFoot} rx={90} ry={26} />
      <g className={fx.lift}>
        <path className={fx.liftToken} d={hex(36)} />
        <circle className={fx.liftCore} r={12} />
      </g>
    </>
  );
}

/** Hacan — Sanction of the Quieron: deszcz trade goods. */
function Coins() {
  return (
    <>
      {seq(10, (i) => (
        <g key={i} style={vars({ "--i": i })}>
          <circle className={base.coin} r={9} />
        </g>
      ))}
    </>
  );
}

/** Sardakk N'orr — Brood Swarm: trzy cięcia szponów. */
function Slash() {
  return (
    <>
      {seq(3, (i) => (
        <g key={i} className={fx.clawRow} style={vars({ "--i": i })}>
          <path className={base.claw} d="M -70 -60 Q -10 -10 60 70" pathLength={100} />
        </g>
      ))}
    </>
  );
}

/** Winnu / Naaz-Rokha: pieczęć stempluje system i rozsyła falę. */
function Seal() {
  return (
    <>
      {seq(3, (i) => (
        <g key={i} style={vars({ "--i": i })}>
          <circle className={base.sealRing} r={120} />
          <circle className={base.sealInner} r={86} />
        </g>
      ))}
      <g className={fx.sealGlyph}>
        <Ring n={6}>{() => <path d="M 0 -70 L 9 -52 L -9 -52 Z" />}</Ring>
      </g>
    </>
  );
}

/** Xxcha — Aegis: warstwy kopuły tarczy. */
function Aegis() {
  return (
    <>
      {seq(3, (i) => (
        <g key={i} style={vars({ "--i": i })}>
          <path className={base.dome} d="M -92 18 A 92 92 0 0 1 92 18 Z" />
          <ellipse className={base.domeBase} cx={0} cy={18} rx={92} ry={22} />
        </g>
      ))}
      <path className={fx.domeHex} d="M -60 -20 L -30 -38 L 0 -20 L 30 -38 L 60 -20 M -30 -38 L -30 -70 M 30 -38 L 30 -70" />
    </>
  );
}

/** Letnev — Void Transference: celowniki zaciskają się na flocie, potem „lock”. */
function Reticle() {
  return (
    <g className={fx.reticle}>
      <Ring n={4} offset={45}>
        {() => <path className={fx.bracket} d="M -28 -120 L -28 -134 L 28 -134 L 28 -120" />}
      </Ring>
      <circle className={fx.reticleRing} r={78} />
      <path className={fx.crosshair} d="M -150 0 L -40 0 M 40 0 L 150 0 M 0 -150 L 0 -40 M 0 40 L 0 150" />
      <circle className={fx.lockDot} r={10} />
    </g>
  );
}

/** Jol-Nar — Brilliance of the Hylar: obwody rozrastają się z rdzenia danych. */
function Circuit() {
  return (
    <>
      <Ring n={8} offset={22.5}>
        {(i) => (
          <>
            <path
              className={fx.trace}
              d={i % 2 ? "M 0 -34 L 0 -70 L 26 -96 L 26 -140" : "M 0 -34 L 0 -88 L -22 -110 L -22 -128"}
              pathLength={100}
            />
            <circle className={fx.node} cx={i % 2 ? 26 : -22} cy={i % 2 ? -140 : -128} r={7} />
          </>
        )}
      </Ring>
      <rect className={fx.chip} x={-30} y={-30} width={60} height={60} rx={6} />
      <rect className={fx.chipCore} x={-12} y={-12} width={24} height={24} />
    </>
  );
}

/** Mentak — Sleeper Cell: haki abordażowe na łańcuchach wbijają się i ściągają łup. */
function Grapple() {
  return (
    <>
      <Ring n={5} offset={18}>
        {() => (
          <g className={fx.hookArm}>
            <path className={fx.chain} d="M 0 -460 L 0 -64" pathLength={100} />
            <path className={fx.hook} d="M -16 -78 Q -16 -54 0 -54 Q 16 -54 16 -78 M 0 -54 L 0 -92" />
            <circle className={fx.spark} cy={-60} r={18} />
          </g>
        )}
      </Ring>
      <circle className={fx.plunder} r={44} />
    </>
  );
}

/** Argent Flight — Helix Protocol: podwójna spirala, po której pną się skrzydła. */
function Helix() {
  const strand = (phase: number) =>
    `M 0 260 ${seq(26, (k) => {
      const y = 260 - k * 21;
      return `L ${(Math.sin(k * 0.55 + phase) * 52).toFixed(1)} ${y}`;
    }).join(" ")}`;
  return (
    <g className={fx.helix}>
      <path className={fx.strand} d={strand(0)} pathLength={100} />
      <path className={fx.strand} data-b d={strand(Math.PI)} pathLength={100} />
      {seq(4, (i) => (
        <path key={i} className={fx.chevron} d="M -22 10 L 0 -8 L 22 10" style={vars({ "--i": i })} />
      ))}
    </g>
  );
}

/** Yin — Quantum Dissemination: kapsuły z klonami spadają i uderzają w planety. */
function Drop() {
  return (
    <>
      {PODS.map((p, i) => (
        <g key={i} transform={`translate(${p.x} ${p.y})`} style={vars({ "--i": i })}>
          <g className={fx.pod}>
            <line className={fx.podTrail} x1={0} y1={-90} x2={0} y2={-8} />
            <ellipse className={fx.podBody} rx={6} ry={11} />
          </g>
          <ellipse className={fx.podImpact} rx={30} ry={11} />
        </g>
      ))}
      <circle className={fx.yinRing} r={40} />
      <path className={fx.yinYang} d="M 0 -40 A 40 40 0 0 1 0 40 A 20 20 0 0 1 0 0 A 20 20 0 0 0 0 -40 Z" />
    </>
  );
}
const PODS = seq(7, (i) => ({ x: ((i * 53) % 150) - 75, y: ((i * 41) % 100) - 50 }));

/** L1Z1X — Dark Space Navigation: siatka heksów materializuje okręty, zakłócenia obrazu. */
function Warp() {
  return (
    <>
      {seq(4, (i) => (
        <path key={i} className={fx.warpHex} d={hex(150)} style={vars({ "--i": i })} />
      ))}
      {seq(5, (i) => (
        <rect
          key={i}
          className={fx.glitch}
          x={-140 + ((i * 47) % 60)}
          y={-110 + i * 48}
          width={180 + ((i * 29) % 90)}
          height={6 + (i % 3) * 4}
          style={vars({ "--i": i })}
        />
      ))}
      <circle className={fx.harrowEye} r={16} />
    </>
  );
}

/** Saar — Armageddon Relay: fala uderzeniowa toczy się z doku na sąsiednie systemy. */
function Blast() {
  return (
    <>
      {seq(3, (i) => (
        <path key={i} className={fx.relay} d={hex(110 - i * 25)} style={vars({ "--i": i })} />
      ))}
      <circle className={fx.blastCore} r={70} />
      <circle className={fx.shock} r={120} />
      <circle className={fx.shock} data-late r={120} />
      <Ring n={14}>
        {(i) => <path className={fx.debris} d="M -4 0 L 0 -14 L 5 -2 Z" style={vars({ "--dist": `${-170 - ((i * 53) % 140)}px` })} />}
      </Ring>
    </>
  );
}

/** Naalu — C-Radium Geometry: oko psioniczne otwiera się, fale rozchodzą się w umysły rywali. */
function Psi() {
  return (
    <>
      {seq(4, (i) => (
        <circle key={i} className={fx.psiWave} r={70} style={vars({ "--i": i })} />
      ))}
      <g className={fx.eye}>
        <path className={fx.eyeLid} d="M -78 0 Q 0 -62 78 0 Q 0 62 -78 0 Z" />
        <circle className={fx.iris} r={24} />
        <ellipse className={fx.pupil} rx={5} ry={18} />
      </g>
    </>
  );
}

/** Cabal — Event Horizon: wir w doku, macki do sąsiednich systemów, okręty wciągane do środka. */
function Maw({ reach }: { reach: { dx: number; dy: number }[] }) {
  return (
    <>
      {reach.map((n, k) => {
        // Macka: łuk wygięty w bok (raz w lewo, raz w prawo), od wiru do środka sąsiada.
        const bend = k % 2 ? 0.28 : -0.28;
        const mx = n.dx / 2 - n.dy * bend;
        const my = n.dy / 2 + n.dx * bend;
        const d = `M 0 0 Q ${mx.toFixed(0)} ${my.toFixed(0)} ${n.dx} ${n.dy}`;
        return (
          <g key={k} style={vars({ "--k": k })}>
            <path
              className={fx.victimHex}
              d={HEX_PATH}
              transform={`translate(${n.dx - TILE_WIDTH / 2} ${n.dy - TILE_HEIGHT / 2})`}
            />
            <path className={fx.tendrilGlow} d={d} pathLength={100} />
            <path className={fx.tendril} d={d} pathLength={100} />
            {seq(4, (j) => (
              <circle
                key={j}
                className={fx.prey}
                r={5 - (j % 2) * 2}
                style={vars({ "--dx": `${n.dx * 0.92}px`, "--dy": `${n.dy * 0.92}px`, "--j": j })}
              />
            ))}
          </g>
        );
      })}
      <circle className={fx.mawHalo} r={150} fill="url(#fxMawHalo)" />
      <g className={fx.vortex}>
        <Ring n={6}>
          {() => <path className={fx.arm} d="M 0 -44 C 50 -60 96 -30 118 22" pathLength={100} />}
        </Ring>
      </g>
      <ellipse className={fx.accretion} rx={86} ry={30} />
      <circle className={fx.hole} r={46} />
      <circle className={fx.horizon} r={48} />
      <circle className={fx.snap} r={60} />
    </>
  );
}

/** Titans — Geoform: szczeliny magmy, rdzeń tytana w pancernych płytach, 3× SPACE CANNON. */
function Awaken() {
  return (
    <>
      {CRACKS.map((c, i) => (
        <path key={i} className={fx.crack} d={c} pathLength={100} style={vars({ "--i": i })} />
      ))}
      <circle className={fx.burst} r={110} />
      <circle className={fx.titanHalo} r={130} fill="url(#fxTitanHalo)" />
      <g className={fx.titan}>
        <Ring n={6}>{() => <path className={fx.plate} d="M -34 -58 L 34 -58 L 26 -92 L -26 -92 Z" />}</Ring>
        <circle className={fx.titanCore} r={42} fill="url(#fxTitanCore)" />
        <circle className={fx.titanEye} r={9} />
      </g>
      {[-22, 0, 22].map((a, i) => (
        <g key={i} transform={`rotate(${a})`}>
          <rect className={fx.lance} x={-5} y={-1000} width={10} height={950} style={vars({ "--i": i })} />
        </g>
      ))}
    </>
  );
}
const CRACKS = seq(8, (i) => {
  const a = (i * Math.PI * 2) / 8 + (i % 3) * 0.2;
  const pts = seq(5, (k) => {
    const r = 20 + k * 34;
    const wob = (k % 2 ? 1 : -1) * (8 + ((i * 7 + k * 13) % 14));
    return `${(Math.cos(a) * r - Math.sin(a) * wob).toFixed(0)} ${(Math.sin(a) * r + Math.cos(a) * wob).toFixed(0)}`;
  });
  return `M ${pts.join(" L ")}`;
});

/** Gradienty znaczników (kolor z `--tone` warstwy). */
export function MarkDefs() {
  const c = (color: string, opacity = 1) => ({ stopColor: color, stopOpacity: opacity });
  return (
    <defs>
      <radialGradient id="fxMawHalo">
        <stop offset="0%" style={c("rgb(0 0 0)", 0.95)} />
        <stop offset="40%" style={c("rgb(30 0 10)", 0.8)} />
        <stop offset="70%" style={c("rgb(var(--tone))", 0.35)} />
        <stop offset="100%" style={c("rgb(var(--tone))", 0)} />
      </radialGradient>
      <radialGradient id="fxTitanCore">
        <stop offset="0%" style={c("#fff")} />
        <stop offset="40%" style={c("rgb(255 200 225)")} />
        <stop offset="80%" style={c("rgb(var(--tone))")} />
        <stop offset="100%" style={c("rgb(120 20 70)")} />
      </radialGradient>
      <radialGradient id="fxTitanHalo">
        <stop offset="0%" style={c("rgb(var(--tone))", 0.6)} />
        <stop offset="60%" style={c("rgb(var(--tone))", 0.18)} />
        <stop offset="100%" style={c("rgb(var(--tone))", 0)} />
      </radialGradient>
    </defs>
  );
}

const DRAW: Record<Exclude<FxMark, "nova" | "maw">, () => ReactNode> = {
  bloom: Bloom,
  beam: Beam,
  coins: Coins,
  slash: Slash,
  seal: Seal,
  aegis: Aegis,
  reticle: Reticle,
  circuit: Circuit,
  grapple: Grapple,
  helix: Helix,
  drop: Drop,
  warp: Warp,
  blast: Blast,
  psi: Psi,
  awaken: Awaken,
};

/** Znacznik bohatera w jednym systemie: poświata heksu + rysunek frakcji. */
export function Mark({
  mark,
  tile,
  index,
  neighbors = [],
}: {
  mark: Exclude<FxMark, "nova">;
  tile: Tile;
  index: number;
  /** Sąsiednie kafle (Cabal: macki sięgają do nich). */
  neighbors?: Tile[];
}) {
  const c = center(tile);
  const Draw = mark === "maw" ? null : DRAW[mark];
  return (
    <g
      className={base.mark}
      data-mark={mark}
      // Kolejne systemy odpalają z lekkim przesunięciem — fala zamiast jednego błysku.
      style={vars({ "--d": `${Math.min(index, 12) * 90}ms` })}
    >
      <path className={base.hex} d={HEX_PATH} transform={`translate(${tile.properties.x} ${tile.properties.y})`} />
      <g transform={`translate(${c.x} ${c.y})`}>
        {Draw ? (
          <Draw />
        ) : (
          <Maw
            reach={neighbors.map((n) => {
              const nc = center(n);
              return { dx: nc.x - c.x, dy: nc.y - c.y };
            })}
          />
        )}
      </g>
    </g>
  );
}
