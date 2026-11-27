import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Activity } from "@/api/useBoardEditor";
import { describeActivity, type ActivityContext } from "./describeActivity";

const ctx: ActivityContext = {
  players: {
    p1: { faction: "mahact", color: "purple", display_name: "Airo", is_bot: false },
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

describe("describeActivity — the Mahact (RULES.md 62.23)", () => {
  it("Edict and Il Na Viroset are named from the data", () => {
    renderFacts([
      { type: "ability_used", player_id: "p1", value: "abilities:edict", detail: "Jace's command token joins the fleet pool" },
      {
        type: "ability_used",
        player_id: "p1",
        value: "leaders:mahactcommander",
        detail: "activates system 102 again: both command tokens return, the turn ends",
      },
    ] as Activity["facts"]);
    expect(screen.getByText("Edict")).toBeTruthy();
    expect(screen.getByText(/joins the fleet pool/)).toBeTruthy();
    expect(screen.getByText("Il Na Viroset")).toBeTruthy();
  });

  it("Crimson Legionnaire: the unit's full name, never the raw id", () => {
    renderFacts([
      { type: "ability_used", player_id: "p1", value: "units:mahact_infantry", detail: "gains 1 commodity" },
    ] as Activity["facts"]);
    expect(screen.getByText("Crimson Legionnaire I")).toBeTruthy();
    expect(screen.queryByText(/mahact_infantry/)).toBeNull();
  });

  it("Benediction's origin and combat areas are not feed lines (board effect only)", () => {
    const facts = renderFacts([
      { type: "area", player_id: "p1", value: "102", detail: "benediction_origin" },
      { type: "area", player_id: "p1", value: "103", detail: "benediction" },
    ] as Activity["facts"]);
    expect(facts).toHaveLength(0);
  });
});
