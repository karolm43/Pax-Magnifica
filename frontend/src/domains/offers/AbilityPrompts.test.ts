import { describe, expect, it } from "vitest";
import { promptKey, pruneDismissed, waitingDecisions, type AvailableNow } from "./AbilityPrompts";

const row = (component_id: string): AvailableNow => ({
  player_id: "p1",
  kind: "leader",
  component_id,
  name: component_id,
  text: "",
});

describe("pruneDismissed", () => {
  it("„Not now” trzyma, dopóki zdolność jest dostępna", () => {
    const dismissed = new Set([promptKey(row("sardakkhero"))]);
    expect(pruneDismissed(dismissed, [row("sardakkhero")])).toBe(dismissed);
  });

  it("po zamknięciu okna zdolność może wyskoczyć znowu w następnym", () => {
    const dismissed = new Set([promptKey(row("sardakkhero"))]);
    expect(pruneDismissed(dismissed, [row("letnevagent")]).size).toBe(0);
  });
});

describe("waitingDecisions (pastylka „+N” przy oknie fazy, U3)", () => {
  it("liczy oferty, zdolności „Available now” i zaproszenia do stołu", () => {
    expect(waitingDecisions({ offers: 2, moments: 1, invites: 1 })).toBe(4);
  });

  it("bez decyzji zero - pastylka się nie pokazuje", () => {
    expect(waitingDecisions({ offers: 0, moments: 0, invites: 0 })).toBe(0);
  });
});
