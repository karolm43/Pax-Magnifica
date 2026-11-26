import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Activity } from "@/api/useBoardEditor";
import { describeActivity, type ActivityContext } from "./describeActivity";

const ctx: ActivityContext = {
  players: {
    p1: { faction: "ghost", color: "blue", display_name: "Riftwalker", is_bot: false },
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

function renderFacts(facts: Activity["facts"], actor = "p1") {
  const described = describeActivity(activity(facts, actor), ctx);
  render(<>{described.facts.map((f) => <div key={f.key}>{f.text}</div>)}</>);
  return described.facts;
}

describe("describeActivity — Ghosts of Creuss wormhole tokens (RULES.md 62.19)", () => {
  it("placed: token name from the data and the system", () => {
    renderFacts([
      { type: "faction_token", player_id: "p1", value: "creussalpha", detail: "space", position: "205" },
    ] as Activity["facts"]);
    expect(screen.getByText(/placed the Alpha wormhole token in/)).toBeTruthy();
    expect(screen.getByText("System 205")).toBeTruthy();
  });

  it("moved: ONE line from -> to (the removed half is not listed)", () => {
    const facts = renderFacts([
      { type: "faction_token", player_id: "p1", value: "creussbeta", detail: "space", position: "301" },
      { type: "faction_token_removed", player_id: "p1", value: "creussbeta", detail: "space", position: "205" },
    ] as Activity["facts"]);
    expect(facts).toHaveLength(1);
    expect(screen.getByText(/moved the Beta wormhole token from/)).toBeTruthy();
    expect(screen.getByText("System 205")).toBeTruthy();
    expect(screen.getByText("System 301")).toBeTruthy();
  });

  it("returned to reinforcements (Nova Seed, scar) and played by another player (Creuss IFF)", () => {
    renderFacts([
      { type: "faction_token_removed", player_id: "p1", value: "creussgamma", detail: "space", position: "104" },
    ] as Activity["facts"]);
    expect(screen.getByText(/Gamma wormhole token returned to reinforcements from/)).toBeTruthy();
  });

  it("IFF played by the rival: the token's owner (Creuss) is named", () => {
    renderFacts(
      [{ type: "faction_token", player_id: "p1", value: "creussalpha", detail: "space", position: "105" }] as Activity["facts"],
      "p2",
    );
    expect(screen.getByText(/placed the Alpha wormhole token in/)).toBeTruthy();
  });
});
