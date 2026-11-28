import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CoachContext } from "./coachHint";
import { BASE_COACH_CONTEXT } from "./coachContext.fixture";
import { CoachSection } from "./CoachSection";
import { useTutorialStore } from "./tutorialStore";

/** My Strategy Card pick is due. */
const base: CoachContext = { ...BASE_COACH_CONTEXT, phase: "strategy", myCardPicked: false };

let context: CoachContext | null = base;
vi.mock("./useCoachContext", () => ({ useCoachContext: () => context }));

beforeEach(() => {
  context = base;
  act(() => useTutorialStore.setState({ coachOpen: true, pulseTarget: null }));
});

describe("CoachSection", () => {
  it("Show me pulses the region the hint talks about", async () => {
    const user = userEvent.setup();
    render(<CoachSection />);
    expect(screen.getByText("Pick a Strategy Card")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show me" }));
    expect(useTutorialStore.getState().pulseTarget).toBe("strategy-cards");
  });

  it("no Show me when the hint has nothing to point at", () => {
    context = { ...base, winner: true };
    render(<CoachSection />);
    expect(screen.getByRole("button", { name: /Learn more/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show me" })).toBeNull();
  });
});
