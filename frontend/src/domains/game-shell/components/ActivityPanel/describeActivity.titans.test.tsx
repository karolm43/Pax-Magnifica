import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Activity } from "@/api/useBoardEditor";
import { describeActivity, type ActivityContext } from "./describeActivity";

const ctx: ActivityContext = {
  players: { p1: { faction: "titans", color: "red", display_name: "Ula", is_bot: false } },
  systemName: (pos) => pos,
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
}

describe("describeActivity — Titans of Ul (RULES.md 61.6, 62.18)", () => {
  it("żeton sleeper położony i zdjęty — pełna nazwa planety", () => {
    renderFacts([
      { type: "faction_token", player_id: "p1", value: "sleeper", detail: "wellon" },
      { type: "faction_token_removed", player_id: "p1", value: "sleeper", detail: "wellon" },
    ] as Activity["facts"]);
    expect(screen.getByText(/placed a Sleeper token on/)).toBeTruthy();
    expect(screen.getByText(/Sleeper token removed from/)).toBeTruthy();
    expect(screen.getAllByText("Wellon").length).toBe(2);
  });

  it("Terraform i Geoform przy planecie — nazwy notki i bohatera z danych", () => {
    renderFacts([
      { type: "attached", player_id: null, value: "terraform", detail: "thibah" },
      { type: "attached", player_id: null, value: "titanshero", detail: "elysium" },
    ] as Activity["facts"]);
    expect(screen.getByText("Terraform")).toBeTruthy();
    expect(screen.getByText("Ul the Progenitor")).toBeTruthy();
  });
});
