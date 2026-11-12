import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { TILE_ART_WIDTH } from "@/entities/lookup/planetTileArt";
import type { InvasionLogEntry } from "./useInvasion";
import styles from "./InvasionOverlay.module.css";

/**
 * Efekty okna inwazji (czysto wizualne, bez wpływu na stan):
 * - ``PlanetStage``: okrągła planeta (grafika wycięta z kafelka; bez niej gradienty wg typu), nad
 *   nią orbita ze statkami; kopuła Planetary Shield otacza glob (stoi / zapada się pod war sunem);
 * - ``StrikeLayer``: bombardowanie = ładowanie działa na okręcie → plazmowy pocisk z warkoczem →
 *   trafienie NA powierzchni (kula ognia przycięta do globu, rozświetlenie planety, fala, żar)
 *   oraz iskry i dym nad nią; pudło spala się w atmosferze. War sun: jedna gruba lanca.
 *   Space Cannon Defense to szybkie wyładowania jonowe z ziemi w górę.
 * Każda salwa sprząta po sobie: po zakończeniu warstwa znika z DOM (żadnych pozostałości).
 */

/** Rodzaj powierzchni globu z typu planety (dane: CULTURAL/HAZARDOUS/INDUSTRIAL/FACTION…). */
export function surfaceOf(type: string | undefined): string {
  const t = (type ?? "").toLowerCase();
  if (t.includes("cultur")) return "cultural";
  if (t.includes("hazard")) return "hazardous";
  if (t.includes("industr")) return "industrial";
  if (t.includes("frontier")) return "frontier";
  if (t.includes("faction")) return "faction";
  return "neutral";
}

/** Maksymalny odstęp elementów na orbicie (px). */
export const SHIP_GAP = 74;

/** Przesunięcie (px) n-tego z `count` elementów względem środka globu (zagęszcza tłum). */
export function shipDx(n: number, count: number): number {
  const gap = count > 1 ? Math.min(SHIP_GAP, 250 / (count - 1)) : 0;
  return (n - (count - 1) / 2) * gap;
}

/** Element orbity: statek bombardujący albo mała jednostka desantu (kapsuła). */
export type OrbitItem = {
  node: ReactNode;
  /** Stan kapsuły: drop (zrzut), hold (zawieszona w locie), dead (zestrzelona), land (ląduje). */
  state?: "drop" | "hold" | "dead" | "land";
};

/** Grafika planety z kafelka (``getPlanetTileArt``). */
export type PlanetArt = {
  src: string;
  center: { x: number; y: number };
  radius: number;
};

/**
 * Kadr grafiki kafelka na globie: planeta lekko przepełnia koło (``ART_FILL``), żeby
 * etykiety i ikony zasobów leżące przy jej brzegu na kafelku zostały poza kadrem.
 */
const ART_FILL = 0.9;

export function artStyle(art: PlanetArt): CSSProperties {
  const k = GLOBE_R / (art.radius * ART_FILL);
  return {
    width: `${TILE_ART_WIDTH * k}px`,
    left: `${GLOBE_R - art.center.x * k}px`,
    top: `${GLOBE_R - art.center.y * k}px`,
  };
}

/**
 * Scena planety: orbita ze statkami (``children``), okrągły glob z kopułą tarczy i warstwa
 * salwy. Powierzchnia to grafika planety wycięta z jej kafelka; bez niej - gradienty CSS
 * dobierane po typie planety.
 */
export function PlanetStage({
  surface,
  art,
  shielded,
  collapsed,
  ships,
  children,
  strike,
}: {
  surface: string;
  art?: PlanetArt | null;
  shielded: boolean;
  collapsed: boolean;
  ships: OrbitItem[];
  children?: ReactNode;
  strike: ReactNode;
}) {
  return (
    <div className={styles.stage}>
      <div className={styles.orbitRow} aria-label="Ships in orbit">
        {ships.map((ship, n) => (
          <span
            key={n}
            className={styles.orbitShip}
            data-state={ship.state}
            style={
              {
                "--dx": `${shipDx(n, ships.length)}px`,
                "--k": n,
              } as CSSProperties
            }
          >
            {ship.node}
          </span>
        ))}
      </div>
      <div className={styles.globe} data-surface={surface}>
        <div className={styles.globeSurface} data-art={art ? true : undefined}>
          {art && (
            <img
              className={styles.globeArt}
              src={art.src}
              alt=""
              draggable={false}
              style={artStyle(art)}
            />
          )}
        </div>
        <div className={styles.globeShade} />
        {(shielded || collapsed) && (
          <div
            className={styles.dome}
            data-state={shielded ? "up" : "down"}
            aria-hidden="true"
          />
        )}
        {children}
      </div>
      {strike}
    </div>
  );
}

/** Pseudolosowa, ale stała wartość (0..1) z numeru pocisku. */
function spread(n: number, salt: number): number {
  const h = Math.sin(n * 12.9898 + salt * 78.233) * 43758.5453;
  return h - Math.floor(h);
}

/**
 * Strzał Space Cannon Defense: smuga leci z powierzchni PROSTO W SPADAJĄCĄ KAPSUŁĘ (kąt i długość
 * liczone od działa do kapsuły); trafienie kończy się błyskiem flaku na kapsule, pudło mija ją.
 */
function FlakShot({
  n,
  targetDx,
  shooterDx,
}: {
  n: number;
  targetDx: number;
  shooterDx: number;
}) {
  const vx = targetDx - shooterDx;
  const vy = IMPACT_Y - POD_Y;
  const len = Math.hypot(vx, vy);
  const angle = (Math.atan2(vx, vy) * 180) / Math.PI;
  return (
    <>
      <i
        className={styles.flak}
        style={
          {
            "--sx": `${shooterDx - targetDx}px`,
            "--sy": `${IMPACT_Y}px`,
            "--ang": `${angle}deg`,
            "--len": `${len}px`,
          } as CSSProperties
        }
      >
        <i />
      </i>
      <i
        className={styles.flakBurst}
        style={
          {
            "--by": `${POD_Y}px`,
            "--bx": `${(spread(n, 11) - 0.5) * 8}px`,
          } as CSSProperties
        }
      />
    </>
  );
}

/** Geometria globu na scenie (px od góry sceny): środek i promień. */
const GLOBE_CY = 248;
const GLOBE_R = 84;
/** Górna krawędź globu (px od góry sceny) - początek układu warstwy przyciętej do planety. */
const GLOBE_TOP = GLOBE_CY - GLOBE_R;
/** Wylot działa: dolny koniec pocisku w chwili wystrzału (tuż pod okrętem). */
const SHELL_TIP_Y = 74;
/** Wysokość atmosfery nad powierzchnią (px) - tu spala się pocisk, który spudłował. */
const ATMOSPHERE = 14;

/**
 * Tor pocisku bombardowania: z okrętu (przesunięcie `x` od środka sceny) PROSTO w punkt na
 * górnej połowie globu. Okręty poza obrysem globu celują w jego skraj, więc pocisk nigdy nie
 * przelatuje obok planety. `lift` > 0 kończy tor nad powierzchnią (pudło w atmosferze).
 * Zwraca przesunięcie (`tx`,`ty`), obrót (`ang`), punkt końca (`ax`,`iy`) i długość toru.
 */
export function shellPath(
  x: number,
  lift = 0,
): {
  tx: number;
  ty: number;
  ang: number;
  ax: number;
  iy: number;
  len: number;
} {
  const ax = Math.max(-GLOBE_R + 18, Math.min(GLOBE_R - 18, x));
  const r = GLOBE_R + lift;
  const iy = GLOBE_CY - Math.sqrt(r ** 2 - ax ** 2) + (lift > 0 ? 0 : 6);
  const tx = ax - x;
  const ty = iy - SHELL_TIP_Y;
  return {
    tx,
    ty,
    ax,
    iy,
    ang: -(Math.atan2(tx, ty) * 180) / Math.PI,
    len: Math.hypot(tx, ty),
  };
}

/** Odłamki nad trafieniem: kąty (stopnie, 0 = w górę) - rozprysk tylko od powierzchni. */
const DEBRIS_ANGLES = [-62, -34, -12, 14, 38, 66];

/** Lot pocisku: ładowanie działa + przelot do powierzchni (ms) - musi zgadzać się z CSS. */
const FLIGHT_MS = 760;
/** Pudło: pocisk gaśnie w atmosferze wcześniej, niż doleciałby do powierzchni. */
const FIZZLE_MS = 680;
/** War sun: wiązka sięga planety po tylu ms od startu (ładowanie kuli). */
const LANCE_MS = 420;

/** Najdłuższa animacja salwy (ms) - po tym czasie warstwa jest zdejmowana z DOM. */
const BOMBARD_MS = 3200;
const DEFENSE_MS = 2800;
/** Odstęp między kolejnymi strzałami salwy (ms): bombardowanie to seria, SCD rzadsze strzały. */
const STAGGER_ORBIT = 220;
const STAGGER_GROUND = 380;
/** Wysokość (px od góry sceny), na której pociski uderzają w glob / stoją kapsuły w locie. */
const IMPACT_Y = 205;
const POD_Y = 105;
/** Pociski w jednej serii ze statku: pierwszy pełny, drugi mniejszy (dobicie). */
const ROUNDS = 2;

/** Pojedynczy pocisk salwy z policzonym torem i chwilą wystrzału. */
type Round = {
  key: string;
  hit: boolean;
  sun: boolean;
  /** Okręt-źródło (px od środka sceny). */
  dx: number;
  /** Rozrzut wylotu względem okrętu (px). */
  rx: number;
  /** Chwila wystrzału (ms od startu warstwy). */
  t: number;
  /** Skala efektów trafienia (pierwszy pocisk serii 1, dobicie mniej). */
  size: number;
  path: ReturnType<typeof shellPath>;
};

function vars(v: Record<string, string | number>): CSSProperties {
  return v as CSSProperties;
}

/** Chwila, w której pocisk/wiązka dociera do celu (ms od startu warstwy). */
function arrival(r: Round): number {
  if (r.sun) return r.t + LANCE_MS;
  return r.t + (r.hit ? FLIGHT_MS : FIZZLE_MS);
}

/** Pocisk z okrętu: ładowanie i błysk wylotu na okręcie + plazmowy ładunek lecący po torze. */
function Shell({ r }: { r: Round }) {
  const p = r.path;
  return (
    <span
      className={styles.round}
      data-hit={r.hit || undefined}
      style={vars({
        "--dx": `${r.dx + r.rx}px`,
        "--t": `${r.t}ms`,
        "--tx": `${p.tx}px`,
        "--ty": `${p.ty}px`,
        "--ang": `${p.ang}deg`,
        "--k": r.size,
      })}
    >
      <i className={styles.charge} />
      <i className={styles.shell} />
    </span>
  );
}

/** Lanca war suna: kula ładowania na okręcie i gruba wiązka do punktu na planecie. */
function SunLance({ r }: { r: Round }) {
  const p = r.path;
  return (
    <span
      className={styles.round}
      data-hit={r.hit || undefined}
      data-sun
      style={vars({
        "--dx": `${r.dx}px`,
        "--t": `${r.t}ms`,
        "--ang": `${p.ang}deg`,
        "--len": `${p.len + (r.hit ? 4 : 0)}px`,
      })}
    >
      <i className={styles.sunCharge} />
      <i className={styles.sunBeam} />
    </span>
  );
}

/**
 * Skutek trafienia NA planecie (warstwa przycięta do globu): rozświetlenie półkuli,
 * kula ognia, płaska fala uderzeniowa i stygnący żar. Wszystko wygasa do zera.
 */
function SurfaceHit({ r }: { r: Round }) {
  return (
    <i
      className={styles.surfaceHit}
      data-sun={r.sun || undefined}
      style={vars({
        "--x": `${GLOBE_R + r.path.ax}px`,
        "--y": `${r.path.iy - GLOBE_TOP}px`,
        "--hit": `${arrival(r)}ms`,
        "--k": r.size,
      })}
    >
      <i className={styles.lightUp} />
      <i className={styles.scorch} />
      <i className={styles.shock} />
      <i className={styles.fireball} />
    </i>
  );
}

/** Skutek nad planetą: błysk, odłamki i dym (trafienie) albo rozbłysk w atmosferze (pudło). */
function AirFx({ r, n }: { r: Round; n: number }) {
  return (
    <i
      className={styles.airFx}
      data-hit={r.hit || undefined}
      data-sun={r.sun || undefined}
      style={vars({
        "--x": `${r.path.ax}px`,
        "--y": `${r.path.iy}px`,
        "--hit": `${arrival(r)}ms`,
        "--k": r.size,
        // Odłamki i dym odchylają się od pionu tak jak normalna powierzchni w punkcie trafienia.
        "--tilt": `${(Math.asin(r.path.ax / GLOBE_R) * 180) / Math.PI}deg`,
      })}
    >
      <i className={styles.flash} />
      {r.hit && (
        <>
          {DEBRIS_ANGLES.map((a, k) => (
            <i
              key={a}
              className={styles.debris}
              style={vars({
                "--a": `${a + (spread(n, 20 + k) - 0.5) * 16}deg`,
                "--d": `${(20 + spread(n, 30 + k) * 22) * (r.sun ? 1.6 : 1)}px`,
              })}
            />
          ))}
          <i className={styles.smoke} />
        </>
      )}
    </i>
  );
}

/**
 * Pokazuje salwę tylko dla wpisu dziennika, który POJAWIŁ SIĘ po zamontowaniu karty
 * (otwarcie okna nie odtwarza starych strzałów), a po jej końcu zdejmuje się sama.
 */
export function StrikeLayer({
  entry,
  entryId,
  from,
  shipCount,
  startMs,
}: {
  entry: InvasionLogEntry | undefined;
  /** Numer wpisu w dzienniku (rośnie z każdym rozstrzygnięciem). */
  entryId: number;
  /** Salwa rusza dopiero po tylu ms (czas na wylądowanie rzuconych kości). */
  startMs: number;
  from: "orbit" | "ground";
  /** Ile statków stoi na orbicie (źródła ostrzału); 0 = pociski z losowych punktów. */
  shipCount: number;
}) {
  const initial = useRef(entryId);
  const [finished, setFinished] = useState(-1);
  const fresh = !!entry && !entry.passed && entryId !== initial.current;
  // Opóźnienie salwy zamrażamy przy pierwszym renderze świeżego wpisu: późniejsze zmiany
  // propsa nie mogą przestawić trwających animacji.
  const frozen = useRef<{ id: number; ms: number } | null>(null);
  if (fresh && frozen.current?.id !== entryId) {
    frozen.current = { id: entryId, ms: startMs };
  }
  const lead = fresh && frozen.current ? frozen.current.ms : 0;
  const bolts = fresh
    ? entry.rolls.flatMap((r, ri) => {
        const offset = entry.rolls.slice(0, ri).reduce((n, x) => n + x.count, 0);
        return r.dice.map((d, di) => ({
          hit: d >= r.hitsOn,
          id: `${ri}-${di}`,
          sun: r.baseType === "warsun",
          ship: offset + (di % Math.max(1, r.count)),
        }));
      })
    : [];
  const stagger = from === "orbit" ? STAGGER_ORBIT : STAGGER_GROUND;
  const total =
    (from === "orbit" ? BOMBARD_MS : DEFENSE_MS) + bolts.length * stagger + lead;
  useEffect(() => {
    if (!fresh) return;
    const t = window.setTimeout(() => setFinished(entryId), total);
    return () => window.clearTimeout(t);
  }, [fresh, entryId, total]);

  if (!fresh || finished === entryId) return null;

  const sourceX = (ship: number, n: number) =>
    shipCount > 0 ? shipDx(ship, shipCount) : (spread(n, 1) - 0.5) * 120;

  if (from === "orbit") {
    const rounds = bolts.flatMap((b, n): Round[] => {
      const dx = sourceX(b.ship, n);
      const t0 = lead + n * stagger;
      const lift = b.hit ? 0 : ATMOSPHERE;
      if (b.sun) {
        return [
          { key: b.id, hit: b.hit, sun: true, dx, rx: 0, t: t0, size: 1, path: shellPath(dx, lift) },
        ];
      }
      return Array.from({ length: ROUNDS }, (_, r) => {
        const rx = (spread(n, 5 + r) - 0.5) * 30;
        return {
          key: `${b.id}-${r}`,
          hit: b.hit,
          sun: false,
          dx,
          rx,
          t: t0 + r * 150 + spread(n, 3 + r) * 60,
          size: r === 0 ? 1 : 0.6,
          path: shellPath(dx + rx * 1.8, lift),
        };
      });
    });
    return (
      <div
        className={styles.strikes}
        data-from="orbit"
        data-hits={bolts.some((b) => b.hit) || undefined}
        aria-hidden="true"
      >
        {rounds.map((r) =>
          r.sun ? <SunLance key={r.key} r={r} /> : <Shell key={r.key} r={r} />,
        )}
        <div className={styles.surfaceFx}>
          {rounds
            .filter((r) => r.hit)
            .map((r) => (
              <SurfaceHit key={r.key} r={r} />
            ))}
        </div>
        {rounds.map((r, n) => (
          <AirFx key={r.key} r={r} n={n} />
        ))}
      </div>
    );
  }

  return (
    <div
      className={styles.strikes}
      data-from="ground"
      data-hits={bolts.some((b) => b.hit) || undefined}
      aria-hidden="true"
    >
      {bolts.map((b, n) => {
        const dx = sourceX(n % Math.max(1, shipCount), n);
        return (
          <span
            key={b.id}
            className={styles.strike}
            data-hit={b.hit || undefined}
            style={vars({
              "--dx": `${dx}px`,
              "--delay": `${lead + n * stagger}ms`,
            })}
          >
            <FlakShot
              n={n}
              targetDx={dx}
              shooterDx={(spread(n, 9) - 0.5) * 150}
            />
          </span>
        );
      })}
    </div>
  );
}
