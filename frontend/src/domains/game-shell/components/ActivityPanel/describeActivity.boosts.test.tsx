import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Activity } from "@/api/useBoardEditor";
import { describeActivity, type ActivityContext } from "./describeActivity";

const ctx: ActivityContext = {
  players: {
    p1: { faction: "saar", color: "orange", display_name: "Saar", is_bot: false },
    p2: { faction: "sol", color: "blue", display_name: "Jace", is_bot: false },
  },
  systemName: (pos) => `System ${pos}`,
  systemHint: () => "",
};

function request(detail: string): Activity {
  return {
    kind: "turn",
    action: "boost.request",
    actor_id: "p2",
    target_id: "p1",
    subject: "saaragent",
    detail,
    round: 1,
    phase: "action",
    facts: [],
  } as unknown as Activity;
}

describe("describeActivity - cooperative boosts (RULES.md 54.15)", () => {
  it("names who asked whom for which agent and the payment", () => {
    render(<div>{describeActivity(request("2"), ctx).headline}</div>);
    expect(screen.getByText(/asked/)).toHaveTextContent("Jace asked Saar for Captain Mendosa, offering 2");
  });

  it("a free request", () => {
    render(<div>{describeActivity(request("0"), ctx).headline}</div>);
    expect(screen.getByText(/asked/)).toHaveTextContent(/for free$/);
  });
});
