import { describe, expect, it } from "vitest";
import type { BattleSide, BattleUnit } from "@/api/useBoardEditor";
import { expandShips, type ShipEntity } from "./battleAssign";
import { NO_INTENT, reconcileShips } from "./shipIdentity";

function side(units: Partial<BattleUnit>[]): BattleSide {
  return {
    units: units.map((u) => ({
      baseType: "cruiser",
      asyncId: "ca",
      name: "Cruiser",
      count: 1,
      damaged: 0,
      sustain: false,
      sustainable: 0,
      ...u,
    })),
  } as unknown as BattleSide;
}

const ids = (ships: ShipEntity[]) => ships.map((s) => s.id);

describe("stabilna tożsamość egzemplarzy", () => {
  it("ginie KLIKNIĘTY egzemplarz, nie ostatni z typu", () => {
    const before = expandShips(side([{ count: 3 }]));
    const after = reconcileShips(before, expandShips(side([{ count: 2 }])), {
      ...NO_INTENT,
      destroy: new Set(["cruiser-0"]),
    });
    expect(ids(after)).toEqual(["cruiser-1", "cruiser-2"]);
  });

  it("bez zamiaru (ruch innego gracza) znika ostatni — przewidywalnie", () => {
    const before = expandShips(side([{ count: 3 }]));
    const after = reconcileShips(before, expandShips(side([{ count: 2 }])));
    expect(ids(after)).toEqual(["cruiser-0", "cruiser-1"]);
  });

  it("Sustain Damage uszkadza KLIKNIĘTY egzemplarz", () => {
    const dn = { baseType: "dreadnought", asyncId: "dn", name: "Dreadnought", sustain: true, sustainable: 3 };
    const before = expandShips(side([{ ...dn, count: 3 }]));
    const after = reconcileShips(before, expandShips(side([{ ...dn, count: 3, damaged: 1 }])), {
      ...NO_INTENT,
      sustain: new Set(["dreadnought-2"]),
    });
    expect(after.find((s) => s.damaged)?.id).toBe("dreadnought-2");
    expect(after.filter((s) => s.canSustain).map((s) => s.id)).toEqual([
      "dreadnought-0",
      "dreadnought-1",
    ]);
  });

  it("zniszczenie uszkodzonego zabiera uszkodzony egzemplarz, choćby stał w środku", () => {
    const dn = { baseType: "dreadnought", asyncId: "dn", name: "Dreadnought", sustain: true, sustainable: 3 };
    const start = expandShips(side([{ ...dn, count: 3 }]));
    const hurt = reconcileShips(start, expandShips(side([{ ...dn, count: 3, damaged: 1 }])), {
      ...NO_INTENT,
      sustain: new Set(["dreadnought-1"]),
    });
    const after = reconcileShips(hurt, expandShips(side([{ ...dn, count: 2, damaged: 0 }])));
    expect(ids(after)).toEqual(["dreadnought-0", "dreadnought-2"]);
    expect(after.every((s) => !s.damaged)).toBe(true);
  });

  it("nowe egzemplarze dostają nowe id (nie przejmują id zniszczonych)", () => {
    const before = reconcileShips(
      expandShips(side([{ count: 2 }])),
      expandShips(side([{ count: 1 }])),
      { ...NO_INTENT, destroy: new Set(["cruiser-0"]) },
    );
    const after = reconcileShips(before, expandShips(side([{ count: 2 }])));
    expect(ids(after)).toEqual(["cruiser-1", "cruiser-2"]);
  });

  it("wskazany w decyzji (Assault Cannon) ginie pierwszy", () => {
    const before = expandShips(
      side([{ count: 2 }, { baseType: "destroyer", asyncId: "dd", name: "Destroyer", count: 2 }]),
    );
    const after = reconcileShips(
      before,
      expandShips(
        side([{ count: 1 }, { baseType: "destroyer", asyncId: "dd", name: "Destroyer", count: 2 }]),
      ),
      { ...NO_INTENT, prefer: new Set(["cruiser-0"]) },
    );
    expect(ids(after)).toEqual(["cruiser-1", "destroyer-0", "destroyer-1"]);
  });
});
