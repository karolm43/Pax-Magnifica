/**
 * Geometria prawdziwej kostki d10 (pięciokątny trapezościan): 10 ścianek-latawców, dwa
 * wierzchołki biegunowe i zygzakowaty „równik". Liczone raz, w układzie CSS (X w prawo,
 * Y w dół, Z do widza); ścianki to płaskie ``div`` ustawione macierzą 3D.
 *
 * Planarność latawca wymusza wysokość bieguna: h = a·(1 + cos36°)/(1 − cos36°).
 * Przeciwległe ścianki sumują się do 11 (jak na prawdziwej kostce 1–10).
 */

export type Vec = [number, number, number];
/** Macierz 3×3 w układzie wierszowym. */
export type Mat = [number, number, number, number, number, number, number, number, number];

/** Skala geometrii: 1 jednostka = tyle px w kostce 100×100. */
export const UNIT = 50;
/** Rozmiar pudełka kostki (px) — kostkę skaluje się transformacją rodzica. */
export const BOX = 100;

const A = 0.1056;
const COS36 = Math.cos(Math.PI / 5);
const H = (A * (1 + COS36)) / (1 - COS36);

const sub = (a: Vec, b: Vec): Vec => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a: Vec, b: Vec) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a: Vec, b: Vec): Vec => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const unit = (a: Vec): Vec => {
  const l = Math.hypot(...a) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};
const neg = (a: Vec): Vec => [-a[0], -a[1], -a[2]];

const ring = (deg: number, y: number): Vec => [
  Math.cos((deg * Math.PI) / 180),
  y,
  Math.sin((deg * Math.PI) / 180),
];

const T: Vec = [0, -H, 0];
const B: Vec = [0, H, 0];
const U = (k: number): Vec => ring(72 * (((k % 5) + 5) % 5), -A);
const L = (k: number): Vec => ring(72 * (((k % 5) + 5) % 5) + 36, A);

/** Liczby na ściankach górnych (k = 0..4); dolne są przeciwległe (suma 11). */
const TOP_VALUES = [10, 2, 8, 4, 6];

export type Face = {
  value: number;
  /** Normalna na zewnątrz (układ kostki). */
  normal: Vec;
  /** Wiersze macierzy obrotu, która kładzie tę ściankę płasko do widza. */
  rows: [Vec, Vec, Vec];
  /** CSS ``matrix3d`` ustawiający ściankę w pudełku kostki. */
  matrix: string;
  width: number;
  height: number;
  /** Zewnętrzny obrys (ciemna krawędź) i wewnętrzna wypełniona powierzchnia. */
  outer: string;
  inner: string;
  /** Środek ścianki w px (miejsce numeru). */
  cx: number;
  cy: number;
};

function buildFace(verts: [Vec, Vec, Vec, Vec], value: number): Face {
  const [apex, s0, far, s1] = verts;
  const ey = unit(sub(far, apex));
  let ex = unit(sub(s1, s0));
  let n = unit(cross(ex, ey));
  const center: Vec = [
    (apex[0] + s0[0] + far[0] + s1[0]) / 4,
    (apex[1] + s0[1] + far[1] + s1[1]) / 4,
    (apex[2] + s0[2] + far[2] + s1[2]) / 4,
  ];
  if (dot(n, center) < 0) {
    ex = neg(ex);
    n = neg(n);
  }
  const local = verts.map((v) => {
    const d = sub(v, apex);
    return [dot(d, ex), dot(d, ey)] as [number, number];
  });
  const umin = Math.min(...local.map((p) => p[0]));
  const umax = Math.max(...local.map((p) => p[0]));
  const wmax = Math.max(...local.map((p) => p[1]));
  const px = local.map(
    ([u, w]) => [(u - umin) * UNIT, w * UNIT] as [number, number],
  );
  // Środek wagi czworokąta (wielokąt wypukły w kolejności apex, s0, far, s1).
  let area = 0;
  let cx = 0;
  let cy = 0;
  for (let i = 0; i < 4; i++) {
    const [x0, y0] = px[i];
    const [x1, y1] = px[(i + 1) % 4];
    const c = x0 * y1 - x1 * y0;
    area += c;
    cx += (x0 + x1) * c;
    cy += (y0 + y1) * c;
  }
  cx /= 3 * area;
  cy /= 3 * area;
  const poly = (k: number) =>
    `polygon(${px
      .map(
        ([x, y]) =>
          `${(cx + (x - cx) * k).toFixed(2)}px ${(cy + (y - cy) * k).toFixed(2)}px`,
      )
      .join(", ")})`;
  const t: Vec = [
    UNIT * apex[0] + ex[0] * umin * UNIT + BOX / 2,
    UNIT * apex[1] + ex[1] * umin * UNIT + BOX / 2,
    UNIT * apex[2] + ex[2] * umin * UNIT,
  ];
  const matrix = `matrix3d(${[
    ex[0], ex[1], ex[2], 0,
    ey[0], ey[1], ey[2], 0,
    n[0], n[1], n[2], 0,
    t[0], t[1], t[2], 1,
  ]
    .map((x) => x.toFixed(5))
    .join(",")})`;
  return {
    value,
    normal: n,
    rows: [ex, ey, n],
    matrix,
    width: (umax - umin) * UNIT,
    height: wmax * UNIT,
    outer: poly(1),
    inner: poly(0.93),
    cx,
    cy,
  };
}

/** 10 ścianek: 5 górnych (przy biegunie T), potem 5 dolnych (przy B). */
export const FACES: Face[] = [
  ...[0, 1, 2, 3, 4].map((k) =>
    buildFace([T, U(k), L(k), U(k + 1)], TOP_VALUES[k]),
  ),
  ...[0, 1, 2, 3, 4].map((j) =>
    buildFace([B, L(j), U(j + 1), L(j + 1)], 11 - TOP_VALUES[(j + 3) % 5]),
  ),
];

/** Indeks ścianki z daną liczbą (1–10). */
export function faceOf(value: number): number {
  const i = FACES.findIndex((f) => f.value === value);
  return i >= 0 ? i : 0;
}

export function mul(a: Mat, b: Mat): Mat {
  const r = new Array<number>(9).fill(0);
  for (let i = 0; i < 3; i++)
    for (let j = 0; j < 3; j++)
      for (let k = 0; k < 3; k++) r[i * 3 + j] += a[i * 3 + k] * b[k * 3 + j];
  return r as Mat;
}

export const rotX = (a: number): Mat => {
  const c = Math.cos(a);
  const s = Math.sin(a);
  return [1, 0, 0, 0, c, -s, 0, s, c];
};
export const rotY = (a: number): Mat => {
  const c = Math.cos(a);
  const s = Math.sin(a);
  return [c, 0, s, 0, 1, 0, -s, 0, c];
};
export const rotZ = (a: number): Mat => {
  const c = Math.cos(a);
  const s = Math.sin(a);
  return [c, -s, 0, s, c, 0, 0, 0, 1];
};

/** Macierz kładąca ściankę ``face`` płasko do widza (numer czytelny, biegun u góry). */
export function restMatrix(face: number): Mat {
  const [x, y, z] = FACES[face].rows;
  return [...x, ...y, ...z] as Mat;
}

export function toMatrix3d(m: Mat): string {
  return `matrix3d(${[
    m[0], m[3], m[6], 0,
    m[1], m[4], m[7], 0,
    m[2], m[5], m[8], 0,
    0, 0, 0, 1,
  ]
    .map((v) => v.toFixed(5))
    .join(",")})`;
}

export function apply(m: Mat, v: Vec): Vec {
  return [
    m[0] * v[0] + m[1] * v[1] + m[2] * v[2],
    m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
    m[6] * v[0] + m[7] * v[1] + m[8] * v[2],
  ];
}

/** Kierunek światła (do widza, z lewej-góry) — jasność ścianek w locie. */
const LIGHT = unit([-0.4, -0.6, 0.7]);

/** Jasność ścianki o normalnej ``n`` (już w układzie świata); <0.5 = w cieniu. */
export function shade(n: Vec): number {
  return 0.5 + 0.75 * Math.max(0, dot(n, LIGHT));
}
