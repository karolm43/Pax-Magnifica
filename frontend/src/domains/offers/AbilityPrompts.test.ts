import { describe, expect, it } from "vitest";
import { promptKey, pruneDismissed, type AvailableNow } from "./AbilityPrompts";

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
