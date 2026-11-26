import { describe, expect, it } from "vitest";
import { boardGeometry } from "./PannableMapView";

describe("boardGeometry", () => {
  it("centers the painted tile bounds rather than the asymmetric wrapper box", () => {
    const geom = boardGeometry(
      {
        width: 2565,
        height: 2500,
        bleed: { top: 0, right: 0, bottom: 0, left: 0 },
        bounds: { left: 200, right: 2625, top: 100, bottom: 2400 },
      },
      2965,
      0.4,
    );

    expect(geom.paintedWidth).toBe(2425);
    // paintedLeft = 80, paintedRight = 1050 => sum = 1130, clearance = 20 - 80 = -60
    expect(geom.margins.marginLeft).toBe(
      "max(-60px, calc((100% - 1130px) / 2))",
    );
  });

  it("keeps the leftmost painted edge at BOARD_CLEARANCE when left-bleeding tiles overflow", () => {
    const geom = boardGeometry(
      {
        width: 2565,
        height: 2500,
        bleed: { top: 0, right: 0, bottom: 0, left: 398 },
        bounds: { left: -398, right: 2625, top: 100, bottom: 2400 },
      },
      2965,
      0.5,
    );

    expect(geom.paintedWidth).toBe(3023);
    // paintedLeft = -199, paintedRight = 1312.5 => sum = 1113.5, clearance = 20 - (-199) = 219
    expect(geom.margins.marginLeft).toBe(
      "max(219px, calc((100% - 1113.5px) / 2))",
    );
  });
});
