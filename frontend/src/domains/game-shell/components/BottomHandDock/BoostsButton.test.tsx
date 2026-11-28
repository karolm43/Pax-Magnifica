import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PlayerData } from "@/entities/data/types";
import type { BoostsData } from "@/api/useBoosts";
import { BoostsButton } from "./BoostsButton";

const request = vi.fn(async () => {});
const withdraw = vi.fn(async () => {});
let data: BoostsData;

vi.mock("@/api/useBoosts", () => ({
  useBoosts: () => ({ data }),
  useBoostActions: () => ({ request, withdraw, configure: vi.fn(), watch: vi.fn() }),
}));
vi.mock("@/shared/ui/PlayerTag", () => ({
  PlayerTag: ({ playerId }: { playerId: string }) => <span>{playerId}</span>,
}));
vi.mock("@/domains/player/components/Leader/LeaderChip", () => ({ LeaderChip: () => null }));

const me = { discordId: "p2", tg: 5, commodities: 1 } as PlayerData;
const row = {
  id: "bo1", owner: "p1", source: "leaders:saaragent", name: "Captain Mendosa", text: "",
  kind: "Agent", mode: "ask" as const, price: null, free: false, payable: true, pending: null,
};

describe("BoostsButton (RULES.md 54.15)", () => {
  beforeEach(() => {
    request.mockClear();
    withdraw.mockClear();
    data = { available: [], outgoing: [], owned: [], watch: null };
  });

  it("stays visible but greyed out when nothing can be asked for", () => {
    render(<BoostsButton player={me} />);
    const button = screen.getByRole("button", { name: "Boosts: 0 available" });
    expect(button.getAttribute("aria-disabled")).toBe("true");
    fireEvent.click(button);
    expect(screen.queryByRole("complementary", { name: "Available boosts" })).toBeNull();
  });

  it("asks the owner, for free by default", () => {
    data = { ...data, available: [row] };
    render(<BoostsButton player={me} />);
    fireEvent.click(screen.getByRole("button", { name: "Boosts: 1 available" }));
    fireEvent.click(screen.getByRole("button", { name: "Ask for free" }));
    expect(request).toHaveBeenCalledWith("p2", "bo1", 0, 0, 0);
  });

  it("a standing offer: no Auto - the price is typed, then taken", () => {
    data = { ...data, available: [{ ...row, mode: "standing", price: 2 }] };
    render(<BoostsButton player={me} />);
    fireEvent.click(screen.getByRole("button", { name: /Boosts/ }));
    expect(screen.getByText(/standing offer: 2/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
    fireEvent.change(screen.getByRole("textbox", { name: "Trade goods" }), {
      target: { value: "2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Take the offer" }));
    expect(request).toHaveBeenCalledWith("p2", "bo1", 2, 0, 0);
  });

  it("debt tokens even when the two cannot transact", () => {
    data = { ...data, available: [{ ...row, payable: false }] };
    render(<BoostsButton player={me} />);
    fireEvent.click(screen.getByRole("button", { name: /Boosts/ }));
    expect(screen.queryByRole("textbox", { name: "Trade goods" })).toBeNull();
    expect(screen.getByText(/debt tokens are always possible/)).toBeTruthy();
    fireEvent.change(screen.getByRole("textbox", { name: "Debt tokens" }), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask, paying 3" }));
    expect(request).toHaveBeenCalledWith("p2", "bo1", 0, 0, 3);
  });

  it("an open request can be withdrawn", () => {
    data = {
      ...data,
      outgoing: [{ offerId: "of9", name: "Captain Mendosa", requester: "p2", owner: "p1",
        tradeGoods: 1, commodities: 0, accepted: false, at: 0 }],
    };
    render(<BoostsButton player={me} />);
    fireEvent.click(screen.getByRole("button", { name: /Boosts/ }));
    fireEvent.click(screen.getByRole("button", { name: "Withdraw" }));
    expect(withdraw).toHaveBeenCalledWith("p2", "of9");
  });
});
