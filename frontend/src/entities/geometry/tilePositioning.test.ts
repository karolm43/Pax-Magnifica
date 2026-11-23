import { describe, expect, it } from "vitest";
import { tileOutline } from "./tileOutline";
import {
  TILE_HEIGHT,
  TILE_WIDTH,
  calculateTilePositions,
  type TilePosition,
} from "./tilePositioning";

/** Mapa 6p (3 pierścienie) z gry testowej: plansza, Creuss w rogu, Fracture i Mallice. */
const BOARD = [
  "000:18", "101:29", "102:33", "103:72", "104:117", "105:46", "106:76",
  "201:49", "202:115", "203:59", "204:116", "205:35", "206:80", "207:69", "208:25",
  "209:110", "210:105", "211:36", "212:79", "301:08", "302:39", "303:45", "304:54",
  "305:64", "306:60", "307:53", "308:47", "309:100", "310:17", "311:43", "312:24",
  "313:96a", "314:78", "315:67", "316:95", "317:23", "318:102", "br:51", "tl:82a",
];
const FRACTURE = [1, 2, 3, 4, 5, 6, 7].map((n) => `frac${n}:fracture${n}`);
/** Pola graczy 1..6 (stat tiles), kolejno od gracza 1 u góry. */
const STATS = [
  "401", "402", "424", "405", "404", "406", "409", "408", "410",
  "413", "412", "414", "417", "416", "418", "421", "420", "422",
].map((p) => `${p}:stat_${p}`);

/** Sąsiednie komórki siatki heksów są w odległości 300 (pion i skos). */
const ADJACENT = 300;
const dist = (a: TilePosition, b: TilePosition) => Math.hypot(a.x - b.x, a.y - b.y);
const byPos = (all: TilePosition[], pos: string) => all.find((t) => t.ringPosition === pos)!;

function layout(withFracture: boolean) {
  const all = calculateTilePositions([...BOARD, ...(withFracture ? FRACTURE : []), ...STATS], 3);
  return all;
}

describe("układ Fracture i Mallice", () => {
  it.each([true, false])("żaden kafel nie nachodzi na inny (Fracture: %s)", (withFracture) => {
    const all = layout(withFracture);
    for (let i = 0; i < all.length; i++) {
      for (let j = i + 1; j < all.length; j++) {
        expect(dist(all[i], all[j]), `${all[i].ringPosition} vs ${all[j].ringPosition}`)
          .toBeGreaterThanOrEqual(ADJACENT - 1);
      }
    }
  });

  it("Fracture przylega do pola gracza 1 bez przerwy", () => {
    const all = layout(true);
    expect(byPos(all, "401").y - byPos(all, "frac4").y).toBe(ADJACENT);
    expect(byPos(all, "401").x).toBe(byPos(all, "frac4").x);
    expect(dist(byPos(all, "frac3"), byPos(all, "424"))).toBe(ADJACENT);
    expect(dist(byPos(all, "frac5"), byPos(all, "402"))).toBe(ADJACENT);
  });

  it.each([true, false])("kształt Mallice nie nachodzi na kafle (Fracture: %s)", (withFracture) => {
    const all = layout(withFracture);
    const mallice = byPos(all, "tl");
    const outline = tileOutline("82a");
    const shape = { x: mallice.x + outline.center.x, y: mallice.y + outline.center.y };
    for (const t of all.filter((t) => t.ringPosition !== "tl")) {
      const hex = { x: t.x + TILE_WIDTH / 2, y: t.y + TILE_HEIGHT / 2 };
      // promień kształtu spirali ~200 + promień wpisany heksa ~150
      expect(Math.hypot(hex.x - shape.x, hex.y - shape.y), t.ringPosition).toBeGreaterThan(350);
    }
  });

  it("z Fracture Mallice leży niżej niż bez niego, obok frac1", () => {
    const withF = byPos(layout(true), "tl");
    const frac1 = byPos(layout(true), "frac1");
    expect(withF.y).toBeGreaterThan(byPos(layout(false), "tl").y);
    expect(withF.y).toBeGreaterThan(frac1.y);
    expect(withF.x).toBeLessThan(frac1.x);
  });
});
