import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { BattleLogEntry, BattleView } from "@/api/useBoardEditor";
import { useVolley } from "./useBattleFx";

const roll = { baseType: "cruiser", dice: [7, 3], modifier: 0, hitsOn: 7 };

function entry(round: number): BattleLogEntry {
  return {
    round,
    phase: "COMBAT",
    rolls: { a: [roll], d: [roll] },
    hits: {},
    losses: {},
    sustained: {},
  } as unknown as BattleLogEntry;
}

function view(log: BattleLogEntry[], round: number): BattleView {
  return {
    attacker: { faction: "a" },
    defender: { faction: "d" },
    round,
    log,
    sideRolls: {},
  } as unknown as BattleView;
}

describe("useVolley - rounds never merge on screen", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("two rounds arriving in one update play one after the other", () => {
    const { result, rerender } = renderHook(({ v }) => useVolley(v), {
      initialProps: { v: view([], 1) },
    });
    rerender({ v: view([entry(1), entry(2)], 3) });
    // Round 1 starts at once; round 2 waits until round 1 has finished.
    expect(result.current).toHaveLength(1);
    // Round 1 keeps the table until its dice land, are read and its shots fly (~5 s).
    act(() => {
      vi.advanceTimersByTime(4900);
    });
    expect(result.current).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current).toHaveLength(2);
  });

  it("the other side's roll of the same round is not delayed", () => {
    const sideOnly = (rolled: Record<string, (typeof roll)[]>) =>
      ({ ...view([], 1), sideRolls: rolled }) as BattleView;
    const { result, rerender } = renderHook(({ v }) => useVolley(v), {
      initialProps: { v: view([], 1) },
    });
    rerender({ v: sideOnly({ a: [roll] }) });
    rerender({ v: sideOnly({ a: [roll], d: [roll] }) });
    expect(result.current).toHaveLength(2);
  });
});
