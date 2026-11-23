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

describe("describeAwaiting — tryb testowy hosta (steruje wszystkimi)", () => {
  it("decyzja gracza, którym steruję, to mój ruch, nie „Waiting for”", () => {
    const res = describeAwaiting([hacan, sol], null, true);
    expect(res.mine).toBe(true);
    expect(res.text).toBe("Your move - Hacan: respond in the timing window, Sol: take a turn");
  });
});

describe("describeAwaiting — powody wg fazy (U5/Z13)", () => {
  it("status i agenda nie mówią „take a turn”", () => {
    expect(describeAwaiting([{ ...sol, reason: "score" }], "p1").text).toBe("Your move - score objectives");
    expect(describeAwaiting([{ ...sol, reason: "redistribute" }], "p1").text).toBe(
      "Your move - place command tokens",
    );
    expect(describeAwaiting([{ ...hacan, reason: "vote" }], "p1").text).toBe(
      "Waiting for Hacan (vote on the agenda)",
    );
  });
});
