import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { PlayerData } from "@/entities/data/types";
import { ReactionAutoPassToggle } from "./ReactionAutoPassToggle";

const post = vi.fn<(actor: string, enabled: boolean) => Promise<void>>();
const desk: { current: Partial<PlayerData> | undefined } = { current: undefined };

vi.mock("@/api/useActionCard", () => ({
  postAutoPass: (actor: string, enabled: boolean) => post(actor, enabled),
}));
vi.mock("@/domains/game-shell/components/TurnControls/useDeskPlayer", () => ({
  useDeskPlayer: () => desk.current,
}));

const player = (over: Partial<PlayerData> = {}) =>
  ({ discordId: "p1", autoPassReactions: false, ...over }) as PlayerData;

describe("ReactionAutoPassToggle (RULES.md 54.11)", () => {
  beforeAll(() => {
    // jsdom nie ma PointerEvent, a Base UI Switch tworzy go przy kliknięciu.
    window.PointerEvent ??= MouseEvent as unknown as typeof PointerEvent;
  });
  beforeEach(() => {
    post.mockReset();
    post.mockResolvedValue(undefined);
    desk.current = { discordId: "p1" };
  });

  it("na cudzym wierszu nic nie pokazuje", () => {
    render(<ReactionAutoPassToggle player={player({ discordId: "p2" })} />);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("wyłączony: cicha ikona; w dymku opis i przełącznik", async () => {
    render(<ReactionAutoPassToggle player={player()} />);
    const trigger = screen.getByRole("button", { name: "Skip all reactions: off" });
    expect(trigger).not.toHaveTextContent("Auto-pass");
    fireEvent.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: "Skip all reactions" });
    expect(dialog).toHaveTextContent("even when you hold a card you could play");
    expect(dialog).toHaveTextContent("You may miss a chance to react");
    fireEvent.click(screen.getByRole("switch"));
    expect(post).toHaveBeenCalledWith("p1", true);
  });

  it("włączony: widoczna pigułka Auto-pass", () => {
    render(<ReactionAutoPassToggle player={player({ autoPassReactions: true })} />);
    expect(screen.getByRole("button", { name: "Skip all reactions: on" })).toHaveTextContent(
      "Auto-pass",
    );
  });
});
