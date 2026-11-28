import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HelpPopover } from "./HelpPopover";
import { MICRO_HELPS } from "./microHelps";
import { useTutorialStore } from "./tutorialStore";

afterEach(() => act(() => useTutorialStore.getState().closeGuide()));

describe("HelpPopover", () => {
  it("opens on click and shows the title and lines", async () => {
    const user = userEvent.setup();
    render(<HelpPopover help="battle" />);
    expect(screen.queryByRole("heading", { name: MICRO_HELPS.battle.title })).toBeNull();

    await user.click(screen.getByRole("button", { name: "Help: Combat" }));
    expect(await screen.findByRole("heading", { name: MICRO_HELPS.battle.title })).toBeInTheDocument();
    expect(screen.getByText(MICRO_HELPS.battle.lines[0])).toBeInTheDocument();
  });

  it("Learn more opens the How to play chapter and closes the popover", async () => {
    const user = userEvent.setup();
    render(<HelpPopover help="commandPools" />);
    await user.click(screen.getByRole("button", { name: "Help: Command tokens" }));
    await user.click(await screen.findByRole("button", { name: "Learn more" }));
    expect(useTutorialStore.getState().chapter).toBe("economy");
    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: MICRO_HELPS.commandPools.title })).toBeNull(),
    );
  });

  it("Escape closes the popover", async () => {
    const user = userEvent.setup();
    render(<HelpPopover help="secondary" />);
    await user.click(screen.getByRole("button", { name: "Help: Strategy Card secondary" }));
    expect(await screen.findByRole("heading", { name: MICRO_HELPS.secondary.title })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: MICRO_HELPS.secondary.title })).toBeNull(),
    );
  });

  it("does not let the click or pointer press reach parent handlers", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const onPointerDown = vi.fn();
    const onMouseDown = vi.fn();
    render(
      <div onClick={onClick} onPointerDown={onPointerDown} onMouseDown={onMouseDown}>
        <HelpPopover help={{ topic: "Inline", title: "Inline help", lines: ["One line."] }} />
      </div>,
    );
    const button = screen.getByRole("button", { name: "Help: Inline" });
    fireEvent.pointerDown(button);
    await user.click(button);
    expect(await screen.findByRole("heading", { name: "Inline help" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Learn more" })).toBeNull();
    expect(onClick).not.toHaveBeenCalled();
    expect(onPointerDown).not.toHaveBeenCalled();
    expect(onMouseDown).not.toHaveBeenCalled();
  });
});
