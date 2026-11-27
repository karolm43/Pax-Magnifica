/*
 * Status tury (RULES.md 44.5): wybór i grupowanie `waitReasons` z web-data.
 */
import { describe, expect, it } from "vitest";
import type { WaitReason } from "@/entities/data/types";
import { waitStatus, waitText } from "./waitReasons";

const reason = (playerId: string, summary: string, reasonCode = "turn", blocking = true) =>
  ({ playerId, summary, reasonCode, blocking }) satisfies WaitReason;

const names: Record<string, string> = { p1: "Sol", p2: "Hacan", p3: "Arborec" };
const nameOf = (id: string) => names[id] ?? id;

const react = [
  reason("p2", "may react: an agenda is revealed", "react"),
  reason("p3", "may react: an agenda is revealed", "react"),
];

describe("waitStatus", () => {
  it("my own wait takes precedence", () => {
    const status = waitStatus([reason("p2", "voting on the agenda"), reason("p1", "taking a turn")], "p1");
    expect(status.mine).toBe(true);
    expect(waitText(status, nameOf)).toBe("Your move - taking a turn");
  });

  it("groups other players sharing a reason", () => {
    const status = waitStatus(react, "p1");
    expect(status.groups).toEqual([
      { summary: "may react: an agenda is revealed", playerIds: ["p2", "p3"] },
    ]);
    expect(waitText(status, nameOf)).toBe("Waiting for - Hacan, Arborec: may react: an agenda is revealed");
  });

  it("ignores players who only answer later", () => {
    const status = waitStatus(
      [
        reason("p2", "following Strategy Card 7 (Technology)", "secondary"),
        reason("p1", "yet to answer Strategy Card 7 (Technology)", "secondary", false),
      ],
      "p1",
    );
    expect(status.mine).toBe(false);
    expect(waitText(status, nameOf)).toBe("Waiting for - Hacan: following Strategy Card 7 (Technology)");
  });

  it("a reaction window I passed in is no longer my move", () => {
    expect(waitStatus(react, "p2").mine).toBe(true);
    expect(waitStatus(react, "p2", { passed: true }).mine).toBe(false);
  });

  it("host test mode: every decision is mine, still named per player", () => {
    const status = waitStatus([reason("p1", "taking a turn")], null, { controlAll: true });
    expect(waitText(status, nameOf, true)).toBe("Your move - Sol: taking a turn");
  });

  it("nothing awaited = no chip", () => {
    expect(waitText(waitStatus([], "p1"), nameOf)).toBe("");
  });
});
