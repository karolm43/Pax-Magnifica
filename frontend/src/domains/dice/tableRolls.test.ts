import { describe, expect, it } from "vitest";
import type { TableRoll } from "@/entities/data/types";
import { latestTableRollSeq, pendingTableRolls } from "./tableRolls";

const roll = (seq: number, playerId: string): TableRoll => ({
  seq,
  kind: "dimensional_anchor",
  playerId,
  label: "Dimensional Anchor",
  dice: [2, 7],
  hitsOn: null,
  hitValues: [1, 2, 3],
  summary: "",
});

describe("pendingTableRolls", () => {
  it("odtwarza WSZYSTKIE nowe rzuty po kolei, nie tylko ostatni (kilku graczy)", () => {
    const state = {
      tableRoll: roll(7, "p4"),
      tableRolls: [roll(4, "p1"), roll(5, "p2"), roll(6, "p3"), roll(7, "p4")],
    };
    expect(pendingTableRolls(state, 4).map((r) => r.playerId)).toEqual([
      "p2",
      "p3",
      "p4",
    ]);
    expect(latestTableRollSeq(state)).toBe(7);
  });

  it("bez listy (starszy backend) bierze sam ostatni rzut", () => {
    const state = { tableRoll: roll(3, "p2") };
    expect(pendingTableRolls(state, 2).map((r) => r.seq)).toEqual([3]);
    expect(latestTableRollSeq(undefined)).toBe(0);
  });
});
