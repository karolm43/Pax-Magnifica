import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Activity } from "@/api/useBoardEditor";
import { describeActivity, type ActivityContext } from "./describeActivity";

const ctx: ActivityContext = {
  players: {
    p1: { faction: "empyrean", color: "purple", display_name: "Procyon", is_bot: false },
    p2: { faction: "sol", color: "red", display_name: "Jace", is_bot: false },
  },
  systemName: (pos) => `System ${pos}`,
  systemHint: () => "",
};

function activity(facts: Activity["facts"], actor = "p1"): Activity {
  return {
    kind: "tactical",
    action: "component.use",
    actor_id: actor,
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

describe("describeActivity — the Empyrean (RULES.md 62.20)", () => {
  it("Void Tether placed: the two systems of the border", () => {
    renderFacts([
      { type: "faction_token", player_id: "p1", value: "voidtether", detail: "border:105", position: "104" },
    ] as Activity["facts"]);
    expect(screen.getByText(/placed a Void Tether on the border of/)).toBeTruthy();
    expect(screen.getByText("System 104")).toBeTruthy();
    expect(screen.getByText("System 105")).toBeTruthy();
  });

  it("Void Tether moved: ONE line from the old border to the new one", () => {
    const facts = renderFacts([
      { type: "faction_token", player_id: "p1", value: "voidtether", detail: "border:202", position: "101" },
      { type: "faction_token_removed", player_id: "p1", value: "voidtether", detail: "border:105", position: "104" },
    ] as Activity["facts"]);
    expect(facts).toHaveLength(1);
    expect(screen.getByText(/moved the Void Tether from the border of/)).toBeTruthy();
    expect(screen.getByText("System 202")).toBeTruthy();
    expect(screen.getByText("System 104")).toBeTruthy();
  });

  it("frontier tokens placed by Multiverse Shift: one counted line", () => {
    const facts = renderFacts([{ type: "frontier_tokens", player_id: null, delta: 4 }] as Activity["facts"]);
    expect(facts).toHaveLength(1);
    expect(screen.getByText(/4 frontier tokens placed/)).toBeTruthy();
  });
});
