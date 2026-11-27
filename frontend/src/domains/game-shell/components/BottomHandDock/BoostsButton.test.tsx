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

  it("is not there when nothing can be asked for", () => {
    const { container } = render(<BoostsButton player={me} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("asks the owner, for free by default", () => {
    data = { ...data, available: [row] };
    render(<BoostsButton player={me} />);
    fireEvent.click(screen.getByRole("button", { name: "Boosts: 1 available" }));
    fireEvent.click(screen.getByRole("button", { name: "Ask for free" }));
    expect(request).toHaveBeenCalledWith("p2", "bo1", 0, 0);
  });

  it("a standing offer: Auto pays the price and takes it", () => {
    data = { ...data, available: [{ ...row, mode: "standing", price: 2 }] };
    render(<BoostsButton player={me} />);
    fireEvent.click(screen.getByRole("button", { name: /Boosts/ }));
    expect(screen.getByText(/standing offer: 2/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Take the offer" }));
    expect(request).toHaveBeenCalledWith("p2", "bo1", 2, 0);
  });

  it("no payment when the two cannot transact", () => {
    data = { ...data, available: [{ ...row, payable: false }] };
    render(<BoostsButton player={me} />);
    fireEvent.click(screen.getByRole("button", { name: /Boosts/ }));
    expect(screen.queryByRole("spinbutton")).toBeNull();
    expect(screen.getByText(/No payment possible now/)).toBeTruthy();
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
