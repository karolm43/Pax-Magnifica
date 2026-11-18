import { act, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { StrategyCardTable } from "./StrategyCardTable";

const card = (initiative: number, name: string, pickedBy: string | null) => ({
  initiative,
  id: `pok${initiative}${name.toLowerCase()}`,
  name,
  primary_texts: [],
  secondary_texts: [],
  colour_hex_code: null,
  trade_goods: 0,
  picked_by: pickedBy,
  exhausted: false,
});

vi.mock("@/api/useGameState", () => ({
  useGameState: () => ({
    data: {
      phase: "strategy",
      activePlayer: "blue",
      speaker: "red",
      seatingOrder: ["red", "blue"],
      strategyPickCount: 1,
    },
  }),
}));
vi.mock("@/api/useBoardEditor", () => ({
  useStrategyCards: () => ({
    data: [card(1, "Leadership", "p-red"), card(2, "Diplomacy", null)],
  }),
  useBoardEditor: () => ({ pickStrategyCard: vi.fn(), nextPhase: vi.fn(), skipPhase: vi.fn() }),
}));
vi.mock("@/state/useGameContext", () => ({
  useGameData: () => ({
    playerData: [
      { discordId: "p-red", color: "red", faction: "sol", displayName: "Federation of Sol", scs: [1] },
      { discordId: "p-blue", color: "blue", faction: "hacan", displayName: "Emirates of Hacan", scs: [] },
    ],
  }),
}));

describe("StrategyCardTable - kto wybrał jaką kartę", () => {
  it("baner właściciela u góry karty i kolejka wyboru w nagłówku", () => {
    vi.useFakeTimers();
    render(
      <MemoryRouter>
        <StrategyCardTable />
      </MemoryRouter>,
    );
    act(() => {
      vi.advanceTimersByTime(600); // karty wchodzą po banerze
    });
    vi.useRealTimers();

    // Karta wybrana: plakietka frakcji nad nią; wolna karta - bez banera.
    const picked = screen.getByRole("img", { name: "Leadership" }).closest("button");
    expect(picked).toHaveAttribute("data-picked");
    expect(within(picked as HTMLElement).getByText("Federation of Sol")).toBeInTheDocument();
    const free = screen.getByRole("img", { name: "Diplomacy" }).closest("button");
    expect(within(free as HTMLElement).queryByText("Federation of Sol")).toBeNull();

    const order = screen.getByRole("list", { name: "Pick order" });
    const seats = within(order).getAllByRole("listitem");
    expect(seats.map((s) => s.textContent)).toEqual([
      expect.stringContaining("Federation of Sol1 Leadership"),
      expect.stringContaining("picking"),
    ]);
    expect(seats[1]).toHaveAttribute("data-now");
  });
});
