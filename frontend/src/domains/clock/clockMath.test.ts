import { describe, expect, it } from "vitest";
import type { ChessClockPlayer } from "@/entities/data/types";
import { formatClock, formatElapsed, isLow, livePlayer } from "./clockMath";

const player = (over: Partial<ChessClockPlayer> = {}): ChessClockPlayer => ({
  playerId: "p1",
  faction: "sol",
  color: "red",
  name: "Sol",
  remainingMs: 600_000,
  turnMs: 0,
  running: true,
  ...over,
});

describe("formatClock", () => {
  it("formats minutes and hours", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(59_001)).toBe("1:00");
    expect(formatClock(605_000)).toBe("10:05");
    expect(formatClock(2 * 3600_000 + 61_000)).toBe("2:01:01");
  });

  it("marks overtime with a minus", () => {
    expect(formatClock(-12_000)).toBe("−0:12");
    expect(formatClock(-0.4)).toBe("−0:01");
  });

  it("counts turn time down to whole seconds", () => {
    expect(formatElapsed(59_999)).toBe("0:59");
    expect(formatElapsed(-5)).toBe("0:00");
  });
});

describe("livePlayer", () => {
  it("only the running player loses time", () => {
    expect(livePlayer(player(), 3_000)).toMatchObject({ remainingMs: 597_000, turnMs: 3_000 });
    const idle = player({ running: false });
    expect(livePlayer(idle, 3_000)).toBe(idle);
  });
});

describe("isLow", () => {
  it("warns under a minute or 10% of the bank", () => {
    expect(isLow(player({ remainingMs: 59_000 }), 600_000)).toBe(true);
    expect(isLow(player({ remainingMs: 61_000 }), 600_000)).toBe(false);
    expect(isLow(player({ remainingMs: 700_000 }), 7_200_000)).toBe(true);
  });
});
