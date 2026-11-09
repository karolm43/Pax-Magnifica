import { describe, expect, it } from "vitest";
import { FACES, apply, faceOf, restMatrix } from "./dieGeometry";

describe("geometria kostki d10", () => {
  it("ma 10 ścianek z liczbami 1–10", () => {
    expect(FACES.map((f) => f.value).sort((a, b) => a - b)).toEqual([
      1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    ]);
  });

  it("przeciwległe ścianki są równoległe i sumują się do 11", () => {
    for (const f of FACES) {
      const opposite = FACES[faceOf(11 - f.value)];
      const d =
        f.normal[0] * opposite.normal[0] +
        f.normal[1] * opposite.normal[1] +
        f.normal[2] * opposite.normal[2];
      expect(d).toBeCloseTo(-1, 4);
    }
  });

  it("obrót spoczynkowy kładzie ściankę płasko do widza", () => {
    for (let i = 0; i < FACES.length; i++) {
      const [x, y, z] = apply(restMatrix(i), FACES[i].normal);
      expect(x).toBeCloseTo(0, 5);
      expect(y).toBeCloseTo(0, 5);
      expect(z).toBeCloseTo(1, 5);
    }
  });
});
