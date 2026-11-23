import { render, screen, within } from "@testing-library/react";
import { vi } from "vitest";
import type { BattleHistoryEntry } from "@/entities/data/types";
import { SystemBattleHistory } from "./SystemBattleHistory";

vi.mock("@/state/useGameContext", () => ({
  useGameData: () => ({
    playerData: [
      { discordId: "p1", faction: "sol" },
      { discordId: "p2", faction: "hacan" },
    ],
  }),
}));

const helpers = {
  displayName: (f: string) => (f === "sol" ? "Federation of Sol" : "Emirates of Hacan"),
} as never;

const battle = (over: Partial<BattleHistoryEntry>): BattleHistoryEntry => ({
  id: 0,
  round: 2,
  kind: "space",
  position: "101",
  planet: null,
  attacker: "p1",
  defender: "p2",
  winner: "p1",
  rounds: 2,
  losses: { p1: 0, p2: 5 },
  lostTypes: { p1: {}, p2: { fighter: 5 } },
  betrayal: false,
  ...over,
});

describe("SystemBattleHistory", () => {
  it("bez bitew w tym systemie nic nie renderuje", () => {
    const { container } = render(
      <SystemBattleHistory position="101" helpers={helpers} history={[battle({ position: "202" })]} />,
    );
    expect(container.textContent).toBe("");
  });

  it("pokazuje bitwy systemu, najnowsza na górze, z narracją", () => {
    render(
      <SystemBattleHistory
        position="101"
        helpers={helpers}
        history={[battle({ id: 0, round: 1 }), battle({ id: 1, round: 3, winner: null, losses: { p1: 2, p2: 2 } })]}
      />,
    );
    const items = within(screen.getByRole("region", { name: "Battle history" })).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toContain("Round 3");
    expect(items[1].textContent).toContain("Round 1");
    expect(items[0].textContent).not.toMatch(/\{\w+\}/);
  });
});
