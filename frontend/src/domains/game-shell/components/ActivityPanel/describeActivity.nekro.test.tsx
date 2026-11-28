import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Activity } from "@/api/useBoardEditor";
import { describeActivity, type ActivityContext } from "./describeActivity";

const ctx: ActivityContext = {
  players: {
    p1: { faction: "nekro", color: "red", display_name: "Flayesh", is_bot: false },
    p2: { faction: "sol", color: "blue", display_name: "Jace", is_bot: false },
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

describe("describeActivity — the Nekro Virus (RULES.md 62.24)", () => {
  it("abilities, Valefar copies and the agent are named from the data", () => {
    renderFacts([
      {
        type: "ability_used",
        player_id: "p1",
        value: "abilities:propagation",
        detail: "gains 3 command token(s) instead of researching Neural Motivator",
      },
      { type: "ability_used", player_id: "p1", value: "technologies:vax", detail: "copies Advanced Carrier II (Jace)" },
      {
        type: "ability_used",
        player_id: "p1",
        value: "abilities:technological_singularity",
        detail: "gains Neural Motivator from Jace",
      },
      { type: "ability_used", player_id: "p1", value: "leaders:nekroagent", detail: "chooses Jace" },
    ] as Activity["facts"]);
    expect(screen.getByText("Propagation")).toBeTruthy();
    expect(screen.getByText("Valefar Assimilator X")).toBeTruthy();
    expect(screen.getByText("Technological Singularity")).toBeTruthy();
    expect(screen.getByText("Nekro Malleon")).toBeTruthy();
    expect(screen.queryByText(/nekroagent|technologies:vax/)).toBeNull();
  });

  it("The Alastor: the unit's full name, never the raw id", () => {
    renderFacts([
      { type: "ability_used", player_id: "p1", value: "units:nekro_flagship", detail: "2 infantry fight as ships" },
    ] as Activity["facts"]);
    expect(screen.getByText("The Alastor")).toBeTruthy();
    expect(screen.queryByText(/nekro_flagship/)).toBeNull();
  });

  it("Devour World's area and planet are not feed lines (board effect only)", () => {
    const facts = renderFacts([
      { type: "area", player_id: "p1", value: "105", detail: "nekro_devour" },
      { type: "hero_planet", player_id: "p1", value: "wellon" },
    ] as Activity["facts"]);
    expect(facts).toHaveLength(0);
  });
});
