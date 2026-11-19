import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { OfferView } from "@/api/useOffers";
import { OfferCard } from "./OffersModal";

const calls: string[] = [];
const decline = vi.fn((player: string, id: string) => {
  calls.push(`decline:${player}:${id}`);
  return Promise.resolve();
});
const prefs = vi.fn((player: string, change: unknown) => {
  calls.push(`mute:${player}:${JSON.stringify(change)}`);
  return Promise.resolve();
});

vi.mock("@/api/useOffers", () => ({
  useOfferActions: () => ({ accept: vi.fn(), decline }),
  useOffers: () => ({ data: [] }),
}));
vi.mock("@/api/useActionCard", async (orig) => ({
  ...(await orig<typeof import("@/api/useActionCard")>()),
  postReactionPrefs: (player: string, change: unknown) => prefs(player, change),
}));
vi.mock("@/state/useGameContext", () => ({ useGameData: () => undefined }));
vi.mock("react-router-dom", () => ({ useParams: () => ({}) }));

const offer = (over: Partial<OfferView> = {}): OfferView => ({
  id: "of1",
  player_id: "p1",
  owner_id: "p1",
  name: "Magmus",
  label: "Magmus: gain 1 trade good",
  text: "After you spend a token from your strategy pool: You may gain 1 trade good.",
  source: "leaders:muaatcommander",
  mandatory: false,
  inputs: [],
  ...over,
});

describe("OfferCard: „Never ask” (RULES.md 54.12)", () => {
  it("wycisza oferty komponentu i odrzuca bieżącą", async () => {
    render(<OfferCard offer={offer()} queued={0} />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Never ask" }));
      await Promise.resolve();
    });
    expect(calls).toEqual([
      `mute:p1:${JSON.stringify({ mute_offers: { "leaders:muaatcommander": true } })}`,
      "decline:p1:of1",
    ]);
  });

  it("decyzji obowiązkowej nie można wyciszyć", () => {
    render(<OfferCard offer={offer({ mandatory: true })} queued={0} />);
    expect(screen.queryByRole("button", { name: "Never ask" })).toBeNull();
  });
});
