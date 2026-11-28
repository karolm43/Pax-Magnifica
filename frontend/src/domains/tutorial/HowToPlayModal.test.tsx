import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { HowToPlayModal } from "./HowToPlayModal";
import { CHAPTERS } from "./tutorialContent";
import { useTutorialStore } from "./tutorialStore";

afterEach(() =>
  act(() => {
    useTutorialStore.getState().closeGuide();
    useTutorialStore.getState().endTour();
  }),
);

describe("HowToPlayModal", () => {
  it("is closed until a chapter is opened", () => {
    render(<HowToPlayModal />);
    expect(screen.queryByRole("heading", { name: CHAPTERS[0].title })).toBeNull();
  });

  it("opens on the requested chapter and walks with Next / Previous", async () => {
    const user = userEvent.setup();
    act(() => useTutorialStore.getState().openGuide("strategy"));
    render(<HowToPlayModal />);
    expect(screen.getByRole("heading", { name: "Strategy phase" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^Next: Action phase/ }));
    expect(screen.getByRole("heading", { name: "Action phase" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Previous/ }));
    expect(screen.getByRole("heading", { name: "Strategy phase" })).toBeInTheDocument();
  });

  it("chapter list jumps straight to a chapter", async () => {
    const user = userEvent.setup();
    act(() => useTutorialStore.getState().openGuide());
    render(<HowToPlayModal />);
    const toc = screen.getByRole("navigation", { name: "Chapters" });
    await user.click(within(toc).getByRole("button", { name: /Combat/ }));
    expect(screen.getByRole("heading", { name: "Combat" })).toBeInTheDocument();
  });

  it("Restart tour closes the guide and starts the screen tour at step 1", async () => {
    const user = userEvent.setup();
    act(() => useTutorialStore.getState().openGuide("combat"));
    render(<HowToPlayModal />);
    await user.click(screen.getByRole("button", { name: /Restart tour/ }));
    expect(useTutorialStore.getState().chapter).toBeNull();
    expect(useTutorialStore.getState().tourStep).toBe(0);
  });
});
