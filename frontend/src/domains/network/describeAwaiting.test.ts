/*
 * Pasek „Your move / Waiting for X" (RULES.md 44.5): tekst z listy `awaiting` z web-data.
 */
import { describe, expect, it } from "vitest";
import { describeAwaiting } from "./NetworkPanel";

const sol = { playerId: "p1", name: "Sol", faction: "sol", color: "blue", reason: "turn" };
const hacan = { playerId: "p2", name: "Hacan", faction: "hacan", color: "yellow", reason: "respond" };

describe("describeAwaiting", () => {
  it("mój ruch ma pierwszeństwo", () => {
    expect(describeAwaiting([hacan, sol], "p1")).toEqual({ mine: true, text: "Your move - take a turn" });
  });

  it("czekamy na innych", () => {
    const res = describeAwaiting([hacan], "p1");
    expect(res.mine).toBe(false);
    expect(res.text).toBe("Waiting for Hacan (respond in the timing window)");
  });

  it("pusta lista = brak paska", () => {
    expect(describeAwaiting([], "p1").text).toBe("");
  });
});
