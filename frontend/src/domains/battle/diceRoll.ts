/** Jedna grupa kości jednego rzutu (np. jednostki tego samego typu) — wspólna dla wszystkich okien. */
export type DiceGroup = {
  dice: number[];
  modifier: number;
  hitsOn: number;
  /** Dokładne „trafiające" wyniki (np. Fracture: 1 i 10) - ma pierwszeństwo przed ``hitsOn``. */
  hitValues?: number[] | null;
};

/** Czy wynik ``value`` jest trafieniem w grupie ``group``. */
export function isHit(group: DiceGroup, value: number): boolean {
  return group.hitValues
    ? group.hitValues.includes(value)
    : value + group.modifier >= group.hitsOn;
}

/**
 * Plan fizycznego rzutu kośćmi (czysta prezentacja — wartości kości zawsze pochodzą z silnika).
 *
 * Kostki wpadają na stół z krawędzi pola bitwy albo — gdy gracz przytrzymał „Roll" — z puli
 * w środku; odbijają się trzy razy o podłoże (coraz niżej i krócej), obracają się w 3D i
 * układają ścianką z wynikiem do góry. Ten moduł liczy deterministyczny plan i stan kostki w
 * danej chwili; rysuje go ``DiceTray`` (pętla animacji) przy pomocy ``dieGeometry``.
 */

export type DieSide = "left" | "right";

/** Czas lotu jednej kostki od wejścia do spoczynku (ms) — rzut ma być czytelny, nie błyskawiczny. */
export const DIE_MS = 2300;
/** Chwile zderzeń z podłożem jako ułamek czasu lotu (ostatni punkt = spoczynek = 1). */
export const CONTACTS = [0.34, 0.6, 0.8] as const;
/** Pauza po lądowaniu ostatniej kostki, zanim ruszą strzały (ms) — czas na odczytanie rzutu. */
export const READ_MS = 700;
/** Ile kostek jednej strony faktycznie rysujemy (reszta tylko w tabeli salwy). */
export const MAX_DICE_PER_SIDE = 30;

export type Point = { x: number; y: number };

export type Die = {
  id: string;
  side: DieSide;
  /** Wartość z silnika (1–10). */
  value: number;
  hit: boolean;
  /** Opóźnienie rzutu względem początku salwy (ms). */
  delayMs: number;
  /** Bok kostki (px). */
  size: number;
  start: Point;
  /** Rzut z puli (przytrzymany Roll): start w miejscu kostki w puli, wyżej nad stołem. */
  fromPool: boolean;
  /** Trzy punkty zderzeń z podłożem. */
  hops: [Point, Point, Point];
  rest: Point;
  /** Początkowe obroty (stopnie) wokół osi X, Y, Z — maleją do 0 / ``restRz``. */
  rx: number;
  ry: number;
  rz: number;
  restRz: number;
};

/** Opóźnienie rzutu i-tej kostki strony: atakujący pierwszy, obrońca chwilę po nim. */
export function dieDelay(side: DieSide, index: number): number {
  return (side === "right" ? 450 : 0) + Math.min(index * 70, 700);
}

/** Moment (od początku salwy), w którym ostatnia kostka leży już nieruchomo. */
export function diceLandMs(left: number, right: number): number {
  const end = (side: DieSide, n: number) =>
    n > 0 ? dieDelay(side, Math.min(n, MAX_DICE_PER_SIDE) - 1) + DIE_MS : 0;
  return Math.max(end("left", left), end("right", right));
}

/** Kiedy po początku salwy mogą ruszyć pociski (kości leżą + chwila na odczyt). */
export function volleyStartMs(left: number, right: number): number {
  const land = diceLandMs(left, right);
  return land > 0 ? land + READ_MS : 0;
}

/** Liczba kostek w rzutach jednej strony. */
export function countDice(rolls: DiceGroup[]): number {
  return rolls.reduce((n, r) => n + r.dice.length, 0);
}

/** Generator deterministyczny (ten sam rzut = ten sam układ kostek). */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function lerp(a: Point, b: Point, f: number): Point {
  return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f };
}

type Area = { x: number; y: number; w: number; h: number };

/** Stół każdej strony: lewa połowa dla atakującego, prawa dla obrońcy. */
function tableArea(side: DieSide, W: number, H: number, solo = false): Area {
  // Rzut jednej strony (karta akcji, Fracture, Space Cannon): kostki leżą pośrodku stołu.
  if (solo) return { x: W * 0.28, y: H * 0.16, w: W * 0.44, h: H * 0.66 };
  return side === "left"
    ? { x: W * 0.18, y: H * 0.14, w: W * 0.31, h: H * 0.7 }
    : { x: W * 0.51, y: H * 0.14, w: W * 0.31, h: H * 0.7 };
}

/** Rozkłada ``n`` kostek na siatce w prostokącie ``area`` (kolejność komórek losowa). */
function slots(
  n: number,
  area: Area,
  rand: () => number,
): { points: Point[]; size: number } {
  const cols = Math.max(1, Math.ceil(Math.sqrt((n * area.w) / area.h)));
  const rows = Math.max(1, Math.ceil(n / cols));
  const cw = area.w / cols;
  const ch = area.h / rows;
  const size = Math.max(42, Math.min(84, Math.min(cw, ch) * 0.9));
  const cells = Array.from({ length: cols * rows }, (_, i) => i);
  for (let i = cells.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [cells[i], cells[j]] = [cells[j], cells[i]];
  }
  const points = cells.slice(0, n).map((cell) => {
    const cx = area.x + (cell % cols) * cw + cw / 2;
    const cy = area.y + Math.floor(cell / cols) * ch + ch / 2;
    const jx = Math.max(0, cw - size) * 0.35;
    const jy = Math.max(0, ch - size) * 0.35;
    return {
      x: cx + (rand() - 0.5) * 2 * jx,
      y: cy + (rand() - 0.5) * 2 * jy,
    };
  });
  return { points, size };
}

/** Pula przed rzutem: kostki strony ustawione wokół środka jej połowy stołu. */
export function poolLayout(
  side: DieSide,
  n: number,
  W: number,
  H: number,
  solo = false,
): { points: Point[]; size: number } {
  const t = tableArea(side, W, H, solo);
  // Pula jest ciaśniejsza niż stół: kostki „w garści" leżą blisko siebie.
  const area: Area = {
    x: t.x + t.w * 0.12,
    y: t.y + t.h * 0.12,
    w: t.w * 0.76,
    h: t.h * 0.76,
  };
  return slots(Math.max(0, n), area, rng(side === "left" ? 11 : 29));
}

/**
 * Plan rzutu: ``left``/``right`` to rzuty obu stron (kolejność jak w dzienniku silnika),
 * ``width``/``height`` wymiary pola, ``pool`` liczba kostek w puli (gdy rzut z puli).
 */
export function planDice(args: {
  left: DiceGroup[];
  right: DiceGroup[];
  width: number;
  height: number;
  seed: number;
  fromPool: boolean;
  pool: { left: number; right: number };
  /** Rzuca jedna strona (lewa) — kostki lądują pośrodku, nie w lewej połowie stołu. */
  solo?: boolean;
}): Die[] {
  const { width: W, height: H } = args;
  const rand = rng(args.seed);
  const dice: Die[] = [];
  const sides: [DieSide, DiceGroup[]][] = [
    ["left", args.left],
    ["right", args.right],
  ];
  for (const [side, rolls] of sides) {
    const flat = rolls
      .flatMap((roll) =>
        roll.dice.map((value) => ({
          value,
          hit: isHit(roll, value),
        })),
      )
      .slice(0, MAX_DICE_PER_SIDE);
    if (flat.length === 0) continue;
    const { points, size } = slots(flat.length, tableArea(side, W, H, args.solo), rand);
    const pool = args.fromPool
      ? poolLayout(side, args.pool[side], W, H, args.solo)
      : null;
    flat.forEach((die, i) => {
      const rest = points[i];
      const poolPoint =
        pool && pool.points.length > 0
          ? pool.points[i % pool.points.length]
          : null;
      const start: Point = poolPoint ?? {
        x: side === "left" ? -size * 2 : W + size * 2,
        y: H * (0.12 + rand() * 0.76),
      };
      const spin = () => (rand() < 0.5 ? -1 : 1) * (360 * (1.6 + rand() * 1.4));
      // Kolejne zderzenia leżą coraz bliżej miejsca spoczynku, z bocznym rozrzutem.
      const hop = (f: number, wobble: number): Point => {
        const p = lerp(start, rest, f);
        return { x: p.x, y: p.y + (rand() - 0.5) * 2 * wobble };
      };
      dice.push({
        id: `${side}-${i}`,
        side,
        value: die.value,
        hit: die.hit,
        delayMs: dieDelay(side, i),
        size,
        start,
        fromPool: poolPoint !== null,
        hops: [hop(0.58, 46), hop(0.86, 22), hop(0.96, 8)],
        rest,
        rx: spin(),
        ry: spin(),
        rz: (rand() - 0.5) * 720,
        restRz: (rand() - 0.5) * 60,
      });
    });
  }
  return dice;
}

/* --- Stan kostki w czasie (pętla animacji) --- */

const MOVE_AT = [0, ...CONTACTS, 1] as const;
const SPIN_LEFT = [1, 0.45, 0.15, 0.04, 0] as const;
/** Wysokość nad stołem (jednostki względne) w kolejnych chwilach; odbicia słabną. */
const LIFT_AT = [0, 0.34, 0.47, 0.6, 0.7, 0.8, 0.9, 1] as const;
const LIFT_Z = [1, 0, 0.38, 0, 0.14, 0, 0.04, 0] as const;

export type DiePose = {
  x: number;
  y: number;
  /** Wysokość nad stołem w px. */
  z: number;
  /** Obroty w radianach. */
  rx: number;
  ry: number;
  rz: number;
  settled: boolean;
};

/** Znajduje przedział ``[i, i+1]`` zawierający ``u`` i ułamek ``f`` w nim. */
function seg(times: readonly number[], u: number): [number, number] {
  for (let i = 0; i < times.length - 1; i++) {
    if (u <= times[i + 1]) {
      return [i, (u - times[i]) / (times[i + 1] - times[i] || 1)];
    }
  }
  return [times.length - 2, 1];
}

/** Stan kostki ``t`` ms po jej rzucie (t<0 = jeszcze czeka na starcie). */
export function dieState(die: Die, t: number): DiePose {
  const u = Math.min(1, Math.max(0, t / DIE_MS));
  const pts = [die.start, ...die.hops, die.rest];
  const [i, f] = seg(MOVE_AT, u);
  const p = lerp(pts[i], pts[i + 1], f);
  const [j, g] = seg(LIFT_AT, u);
  const falling = LIFT_Z[j + 1] < LIFT_Z[j];
  const e = falling ? g * g : 1 - (1 - g) * (1 - g);
  const top = die.fromPool ? 0.75 : 1;
  const z =
    (LIFT_Z[j] + (LIFT_Z[j + 1] - LIFT_Z[j]) * e) *
    (j === 0 ? top : 1) *
    (die.size * 1.7);
  const [k, h] = seg(MOVE_AT, u);
  const spin = SPIN_LEFT[k] + (SPIN_LEFT[k + 1] - SPIN_LEFT[k]) * h;
  const rad = Math.PI / 180;
  return {
    x: p.x,
    y: p.y,
    z,
    rx: die.rx * spin * rad,
    ry: die.ry * spin * rad,
    rz: (die.rz * spin + die.restRz * (1 - spin)) * rad,
    settled: u >= 1,
  };
}
