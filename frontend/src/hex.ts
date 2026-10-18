// Konwersja współrzędnych kubicznych (q, r, s) na piksele dla układu
// "flat-top" (płaska krawędź u góry). Grafiki kafelków AsyncTI4 są rysowane
// jako heksy flat-top, więc siatka używa tego samego orientowania, aby obrazy
// pokrywały się z komórkami. Źródło matematyki: standardowy wzór layoutu heksów.
//
// Dla flat-top:
//   x = size * 3/2 * q
//   y = size * sqrt(3) * (r + q/2)
// gdzie size to promień heksa (środek → wierzchołek).

export interface Point {
  x: number;
  y: number;
}

const SQRT3 = Math.sqrt(3);

/** Środek heksa w pikselach dla danych współrzędnych kubicznych (flat-top).
 *
 * Oś Y jest ODWRÓCONA względem wzoru matematycznego: w SVG Y rośnie w dół, a w
 * układzie AsyncTI4 współrzędna `r` rośnie "ku górze" planszy (pozycja 301 z r=+3
 * jest na górze mapy). Negacja Y ustawia planszę właściwą stroną. */
export function hexToPixel(q: number, r: number, size: number): Point {
  return {
    x: size * (3 / 2) * q,
    y: -size * SQRT3 * (r + q / 2),
  };
}

/** Sześć wierzchołków heksa (flat-top) wokół środka, jako atrybut `points`. */
export function hexCorners(center: Point, size: number): string {
  const corners: string[] = [];
  for (let i = 0; i < 6; i++) {
    // Flat-top: wierzchołki co 60° zaczynając od 0° (prawo).
    const angle = (Math.PI / 180) * (60 * i);
    const x = center.x + size * Math.cos(angle);
    const y = center.y + size * Math.sin(angle);
    corners.push(`${x.toFixed(3)},${y.toFixed(3)}`);
  }
  return corners.join(" ");
}

/** Szerokość i wysokość prostokąta opisanego na heksie flat-top. */
export function hexBounds(size: number): { width: number; height: number } {
  return { width: size * 2, height: size * SQRT3 };
}
