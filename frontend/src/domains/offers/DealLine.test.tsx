import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DealLine } from "./OffersModal";

vi.mock("@/shared/ui/PlayerTag", () => ({
  PlayerTag: ({ playerId }: { playerId: string }) => <span>{playerId}</span>,
}));

const deal = { requester: "p2", owner: "p1", tradeGoods: 2, commodities: 1, accepted: false, at: 0 };

describe("DealLine - binding deal terms on the offer card (RULES.md 54.15)", () => {
  it("the owner sees who asks and what they pay", () => {
    render(<DealLine deal={deal} decider="p1" />);
    expect(screen.getByTestId("deal-line")).toHaveTextContent(
      "p2 asks you to use this, paying 2 trade goods + 1 commodity. Paid only if you accept.",
    );
  });

  it("the requester of an accepted standing offer sees the price", () => {
    render(<DealLine deal={{ ...deal, accepted: true, commodities: 0 }} decider="p2" />);
    expect(screen.getByTestId("deal-line")).toHaveTextContent(
      "p1 agreed - you pay 2 trade goods when you use it.",
    );
  });

  it("a free request", () => {
    render(<DealLine deal={{ ...deal, tradeGoods: 0, commodities: 0 }} decider="p1" />);
    expect(screen.getByTestId("deal-line")).toHaveTextContent("p2 asks you to use this, for free.");
  });
});
