import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Activity } from "@/api/useBoardEditor";
import { describeActivity, type ActivityContext } from "./describeActivity";

const ctx: ActivityContext = {
  players: {
    p1: { faction: "yssaril", color: "green", display_name: "Kyver", is_bot: false },
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
    round: 2,
    phase: "action",
    facts,
  } as Activity;
}

function renderFacts(facts: Activity["facts"]) {
  const described = describeActivity(activity(facts), ctx);
  render(<>{described.facts.map((f) => <div key={f.key}>{f.text}</div>)}</>);
  return described.facts;
}

describe("describeActivity — the Yssaril (RULES.md 62.22)", () => {
  it("So Ata: the look is named by the commander's full name, never the cards", () => {
    renderFacts([
      {
        type: "ability_used",
        player_id: "p1",
        value: "leaders:yssarilcommander",
        detail: "looks at Jace's action cards",
      },
    ] as Activity["facts"]);
    expect(screen.getByText("So Ata")).toBeTruthy();
    expect(screen.getByText(/looks at Jace's action cards/)).toBeTruthy();
  });

  it("Mageon Implants and Deepgloom Executable use their names from the data", () => {
    renderFacts([
      { type: "ability_used", player_id: "p1", value: "technologies:mi", detail: "looks at Jace's action cards" },
      {
        type: "ability_used",
        player_id: "p2",
        value: "breakthroughs:yssarilbt",
        detail: "Stall Tactics used; may make a transaction with Kyver",
      },
    ] as Activity["facts"]);
    expect(screen.getByText("Mageon Implants")).toBeTruthy();
    expect(screen.getByText("Deepgloom Executable")).toBeTruthy();
  });

  it("Kyver's rival-home areas are not feed lines (board effect only)", () => {
    const facts = renderFacts([
      { type: "area", player_id: "p1", value: "104", detail: "kyver" },
    ] as Activity["facts"]);
    expect(facts).toHaveLength(0);
  });
});
