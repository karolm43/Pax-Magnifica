import { describe, expect, it } from "vitest";
import type { BattleLogEntry } from "@/api/useBoardEditor";
import { battleTotals } from "./BattleSummary";

const entry = (over: Partial<BattleLogEntry>): BattleLogEntry => ({
  round: 1,
  phase: "COMBAT",
  rolls: {},
  hits: {},
  losses: {},
  sustained: {},
  retreat: null,
  ...over,
});

describe("battleTotals", () => {
  it("sumuje trafienia, Sustain Damage i straty z całej walki", () => {
    const log = [
      entry({ hits: { sol: 2, arborec: 1 }, losses: { arborec: { fighter: 2 } }, sustained: { sol: { dreadnought: 1 } } }),
      entry({ round: 2, hits: { sol: 1 }, losses: { arborec: { fighter: 1, carrier: 1 } } }),
    ];
    expect(battleTotals(log, "sol")).toEqual({ hits: 3, sustained: 1, losses: {} });
    expect(battleTotals(log, "arborec")).toEqual({
      hits: 1,
      sustained: 0,
      losses: { fighter: 3, carrier: 1 },
    });
  });
});
