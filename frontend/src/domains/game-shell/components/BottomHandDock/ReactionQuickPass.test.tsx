import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PlayerData } from "@/entities/data/types";
import { ReactionQuickPass } from "./ReactionQuickPass";

const prefs = vi.fn<(actor: string, change: unknown) => void>();
vi.mock("@/api/useActionCard", () => ({
  postReactionPrefs: (actor: string, change: unknown) => {
    prefs(actor, change);
    return Promise.resolve();
  },
}));

const me = (reactionPrefs: Partial<NonNullable<PlayerData["reactionPrefs"]>> = {}) =>
  ({
    discordId: "p1",
    reactionPrefs: {
      passes: {},
      onlyInvolved: false,
      mutedCards: [],
      mutedOffers: [],
      windowComponents: [{ key: "leaders:naaluagent", name: "Z'eu" }],
      ...reactionPrefs,
    },
  }) as unknown as PlayerData;

describe("ReactionQuickPass (RULES.md 54.12)", () => {
  beforeEach(() => prefs.mockReset());

  it("pass for this combat declares the combat scope and passes now", async () => {
    const onPassed = vi.fn();
    render(<ReactionQuickPass me={me()} category="combat" inCombat onPassed={onPassed} />);
    fireEvent.click(screen.getByRole("button", { name: "Pass this combat" }));
    expect(prefs).toHaveBeenCalledWith("p1", { declare: { combat: "combat" } });
    await waitFor(() => expect(onPassed).toHaveBeenCalled());
  });

  it("outside combat there is no combat button", () => {
    render(<ReactionQuickPass me={me()} category="agenda" inCombat={false} onPassed={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Pass this combat" })).toBeNull();
  });

  it("mutes an agent for the round", () => {
    render(<ReactionQuickPass me={me()} category={null} inCombat={false} onPassed={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Pass Z'eu this round" }));
    expect(prefs).toHaveBeenCalledWith("p1", { mute_components: { "leaders:naaluagent": "round" } });
  });

  it("toggles auto-pass uninvolved", () => {
    render(<ReactionQuickPass me={me()} category={null} inCombat={false} onPassed={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Auto-pass uninvolved/ }));
    expect(prefs).toHaveBeenCalledWith("p1", { only_involved: true });
  });
});
