import type { BattleRoll } from "@/api/useBoardEditor";

/**
 * Plan fizycznego rzutu kośćmi (czysta prezentacja — wartości kości zawsze pochodzą z silnika).
 *
 * Kostki wlatują na stół z krawędzi pola bitwy (atakujący z lewej, obrońca z prawej), odbijają
 * się trzy razy o podłoże (z coraz mniejszą wysokością i prędkością), tocząc się w locie i
 * wytracając obroty, aż ułożą się płasko na wyznaczonym miejscu. Ten moduł liczy tylko
 * deterministyczny plan (pozycje, kąty, czasy); animację wykonuje ``DiceTray``.
 */

export type DieSide = "left" | "right";

/** Czas lotu jednej kostki od wejścia do spoczynku (ms). */
export const DIE_MS = 1500;
/** Chwile zderzeń z podłożem jako ułamek czasu lotu (ostatni punkt = spoczynek = 1). */
export const CONTACTS = [0.34, 0.6, 0.8] as const;
/** Pauza po lądowaniu ostatniej kostki, zanim ruszą strzały (ms) — czas na odczytanie rzutu. */
export const READ_MS = 450;
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
  return (side === "right" ? 380 : 0) + Math.min(index * 55, 600);
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
export function countDice(rolls: BattleRoll[]): number {
  return rolls.reduce((n, r) => n + r.dice.length, 0);
}

/** Generator deterministyczny (ten sam rzut = ten sam układ kostek). */
function rng(seed: number): () => number {
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

/** Rozkłada ``n`` kostek na siatce w prostokącie ``area`` (kolejność komórek losowa). */
function slots(
  n: number,
  area: { x: number; y: number; w: number; h: number },
  rand: () => number,
): { points: Point[]; size: number } {
  const cols = Math.max(1, Math.ceil(Math.sqrt((n * area.w) / area.h)));
  const rows = Math.max(1, Math.ceil(n / cols));
  const cw = area.w / cols;
  const ch = area.h / rows;
  const size = Math.max(22, Math.min(40, Math.min(cw, ch) * 0.92));
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

/**
 * Plan rzutu: ``left``/``right`` to rzuty obu stron (kolejność jak w dzienniku silnika),
 * ``width``/``height`` wymiary pola, na którym toczą się kostki.
 */
export function planDice(args: {
  left: BattleRoll[];
  right: BattleRoll[];
  width: number;
  height: number;
  seed: number;
}): Die[] {
  const { width: W, height: H } = args;
  const rand = rng(args.seed);
  const dice: Die[] = [];
  const sides: [DieSide, BattleRoll[]][] = [
    ["left", args.left],
    ["right", args.right],
  ];
  for (const [side, rolls] of sides) {
    const flat = rolls
      .flatMap((roll) =>
        roll.dice.map((value) => ({
          value,
          hit: value + roll.modifier >= roll.hitsOn,
        })),
      )
      .slice(0, MAX_DICE_PER_SIDE);
    if (flat.length === 0) continue;
    // Stół: lewa połowa dla atakującego, prawa dla obrońcy (wokół środkowego panelu).
    const area =
      side === "left"
        ? { x: W * 0.25, y: H * 0.22, w: W * 0.24, h: H * 0.56 }
        : { x: W * 0.51, y: H * 0.22, w: W * 0.24, h: H * 0.56 };
    const { points, size } = slots(flat.length, area, rand);
    flat.forEach((die, i) => {
      const rest = points[i];
      const start: Point = {
        x: side === "left" ? -size * 2 : W + size * 2,
        y: H * (0.12 + rand() * 0.76),
      };
      const spin = () => (rand() < 0.5 ? -1 : 1) * (360 * (2 + rand() * 1.5));
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
        hops: [hop(0.58, 46), hop(0.86, 22), hop(0.96, 8)],
        rest,
        rx: spin(),
        ry: spin(),
        rz: (rand() - 0.5) * 720,
        restRz: (rand() - 0.5) * 70,
      });
    });
  }
  return dice;
}
