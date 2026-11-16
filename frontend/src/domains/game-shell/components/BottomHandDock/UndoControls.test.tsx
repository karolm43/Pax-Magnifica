import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PlayerUndoStatus } from "@/api/useActionCard";
import { UndoControls } from "./UndoControls";

const statusRef: { current: PlayerUndoStatus | undefined } = { current: undefined };
const post = vi.fn<(player: string) => Promise<string | null>>();

vi.mock("@/api/useActionCard", () => ({
  usePlayerUndo: () => ({ data: statusRef.current }),
  postPlayerUndo: (player: string) => post(player),
}));
vi.mock("@/api/useBoardEditor", () => ({ useActivityFeed: () => ({ data: undefined }) }));
vi.mock("@/domains/game-shell/components/ActivityPanel/useActivityContext", () => ({
  useActivityContext: () => ({}),
}));

const show = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <UndoControls playerId="p1" />
    </QueryClientProvider>,
  );

describe("UndoControls (RULES.md 44.7)", () => {
  beforeEach(() => {
    post.mockReset();
    post.mockResolvedValue(null);
  });

  it("niedostępne Undo jest wyłączone i mówi dlaczego", () => {
    statusRef.current = {
      available: false, reason: "Dice were rolled", label: null, undone_seq: null,
    };
    show();
    const button = screen.getByRole("button", { name: /undo/i });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toHaveAttribute("aria-description", "Undo is not possible: Dice were rolled");
    fireEvent.click(button);
    expect(post).not.toHaveBeenCalled();
  });

  it("dostępne Undo cofa krok gracza", async () => {
    statusRef.current = {
      available: true, reason: null, label: "tactical:activate:101", undone_seq: 2,
    };
    show();
    fireEvent.click(screen.getByRole("button", { name: /undo/i }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("p1"));
  });
});
