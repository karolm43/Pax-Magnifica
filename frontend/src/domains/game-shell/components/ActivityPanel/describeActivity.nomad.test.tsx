import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Activity } from "@/api/useBoardEditor";
import { describeActivity, type ActivityContext } from "./describeActivity";

const ctx: ActivityContext = {
  players: {
    p1: { faction: "nomad", color: "blue", display_name: "Siven", is_bot: false },
    p2: { faction: "sol", color: "red", display_name: "Jace", is_bot: false },
  },
  systemName: (pos) => `System ${pos}`,
  systemHint: () => "",
};

function activity(facts: Activity["facts"]): Activity {
  return {
    kind: "tactical",
    action: "offer.accept",
    actor_id: "p1",
    target_id: null,
    subject: null,
    detail: null,
    round: 1,
    phase: "action",
    facts,
  } as Activity;
}

function renderFacts(facts: Activity["facts"]) {
  const described = describeActivity(activity(facts), ctx);
  render(<>{described.facts.map((f) => <div key={f.key}>{f.text}</div>)}</>);
  return described.facts;
}

describe("describeActivity — the Nomad (RULES.md 62.21)", () => {
  it("Artuno the Betrayer: trade goods placed on the card", () => {
    renderFacts([
      { type: "leader_tg", player_id: "p1", value: "nomadagentartuno", delta: 3 },
    ] as Activity["facts"]);
    expect(screen.getByText(/placed 3 trade goods on/)).toBeTruthy();
  });

  it("Artuno readied: trade goods taken off the card", () => {
    renderFacts([
      { type: "leader_tg", player_id: "p1", value: "nomadagentartuno", delta: -1 },
    ] as Activity["facts"]);
    expect(screen.getByText(/took 1 trade good off/)).toBeTruthy();
  });

  it("Time Warp areas are not feed lines (board effect only)", () => {
    const facts = renderFacts([
      { type: "area", player_id: "p1", value: "101", detail: "time_warp" },
    ] as Activity["facts"]);
    expect(facts).toHaveLength(0);
  });
});
