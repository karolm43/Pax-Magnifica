import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Nombox } from "./Nombox";

const captureReturnOwn = vi.fn(async () => {});

vi.mock("@/domains/game-shell/components/TurnControls/useDeskPlayer", () => ({
  useDeskPlayer: () => ({ discordId: "p1", faction: "cabal", color: "red" }),
}));
vi.mock("@/api/useBoardEditor", () => ({ useBoardEditor: () => ({ captureReturnOwn }) }));
vi.mock("@/state/useGameContext", () => ({ useGameData: () => ({ playerData: [] }) }));
vi.mock("@/hooks/useFactionColors", () => ({ useFactionColors: () => ({}) }));

describe("Nombox", () => {
  it("own captured ship on my sheet can be returned to reinforcements (R_capture notes/5)", () => {
    render(
      <Nombox
        ownerFaction="cabal"
        capturedUnits={{ cabal: ["cruiser,2", "fighter,1"], sol: ["carrier,1"] }}
      />,
    );
    // Only the own ship is returnable: fighter is a supply token, the Sol carrier is not mine.
    expect(screen.getAllByRole("button", { name: /Return captured/ })).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Return captured Cruiser to reinforcements" }));
    fireEvent.click(screen.getByRole("button", { name: "Return 1 to reinforcements" }));
    expect(captureReturnOwn).toHaveBeenCalledWith("cabal", "cruiser", 1);
  });

  it("another player's sheet has no return buttons", () => {
    render(<Nombox ownerFaction="sol" capturedUnits={{ sol: ["cruiser,1"] }} />);
    expect(screen.queryByRole("button", { name: /Return captured/ })).toBeNull();
  });
});
